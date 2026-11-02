# =============================================================================
# HYDRA-UMC-VOICE-UI - tests/test_voice_features.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The optional voice features: wake word and push-to-talk, speaker identification, questions about error codes, the audit log and the
alerts read aloud. Every one of them is off by default and is switched on from the configuration file."""
from __future__ import annotations

import json
import math
import threading
import urllib.error
import urllib.request
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from hydra_umc_voice_ui.alerts import AlertError, AlertSpeaker
from hydra_umc_voice_ui.audit import AuditLog
from hydra_umc_voice_ui.gateway import VoiceTurn, VoiceTurnValidationError, confirm_pending_action, process_voice_turn
from hydra_umc_voice_ui.http_service import VoiceGatewayServer
from hydra_umc_voice_ui.intent import classify_intent
from hydra_umc_voice_ui.messages import LANGUAGES, MESSAGES
from hydra_umc_voice_ui.queries import DocsQaClient, QueryAnswer, query_matches
from hydra_umc_voice_ui.speaker import SpeakerError, SpeakerStore, clean_vector
from hydra_umc_voice_ui.voice_config import (
    AlertConfig,
    AuditConfig,
    QueryConfig,
    SpeakerConfig,
    VoiceConfig,
    WakeConfig,
    load_voice_config,
    parse_voice_config,
)


def _turn(text: str, **extra: object) -> VoiceTurn:
    payload = {"requestId": "r-1", "transcript": text, "locale": "en-US", **extra}
    return VoiceTurn.from_payload(payload)


def _voice(n: int, seed: int = 1) -> list[float]:
    return [math.sin(seed * (i + 1)) for i in range(n)]


# ---------------------------------------------------------------- configuration


def test_defaults_have_every_optional_feature_off() -> None:
    config = parse_voice_config({})
    assert not (config.wake.enabled or config.speaker.enabled or config.queries.enabled or config.audit.enabled or config.alerts.enabled)
    assert config.problems == ()


def test_invalid_values_are_ignored_and_reported() -> None:
    config = parse_voice_config({
        "wake": {"enabled": "yes", "phrases": [], "extra": 1},
        "speaker": {"threshold": 7},
        "queries": {"docsQaUrl": "file:///etc/passwd"},
        "alerts": {"minSeverity": "loud"},
        "mystery": {},
    })
    assert config.wake == WakeConfig() and config.speaker == SpeakerConfig() and config.queries == QueryConfig() and config.alerts == AlertConfig()
    assert len(config.problems) == 7


def test_config_file_is_read_from_the_environment_and_a_broken_one_leaves_defaults(tmp_path: Path) -> None:
    path = tmp_path / "voice-ui.json"
    path.write_text(json.dumps({"wake": {"enabled": True, "phrases": ["Hydra", "Hey Robot"]}}), encoding="utf-8")
    config = load_voice_config({"HYDRA_UMC_VOICE_UI_CONFIG": str(path)})
    assert config.wake.enabled and config.wake.phrases == ("hydra", "hey robot")
    path.write_text("{ not json", encoding="utf-8")
    broken = load_voice_config({"HYDRA_UMC_VOICE_UI_CONFIG": str(path)})
    assert not broken.wake.enabled and broken.problems
    assert load_voice_config({"HYDRA_UMC_VOICE_UI_CONFIG": str(tmp_path / "none.json")}).problems


# ---------------------------------------------------------------- wake word and push to talk


WAKE = VoiceConfig(wake=WakeConfig(enabled=True, phrases=("hydra",)))


def test_nothing_changes_while_the_wake_word_is_off() -> None:
    reply = process_voice_turn(_turn("status of robot 3"), voice_config=VoiceConfig())
    assert reply.message_code == "status"


def test_without_the_wake_word_nothing_is_done() -> None:
    reply = process_voice_turn(_turn("start mission alpha"), voice_config=WAKE)
    assert reply.message_code == "not_activated" and reply.intent is None and reply.pending_confirmation is None


def test_wake_phrase_is_taken_off_and_the_command_goes_on() -> None:
    reply = process_voice_turn(_turn("Hydra, start mission alpha"), voice_config=WAKE)
    assert reply.intent is not None and reply.intent.name == "start_mission" and reply.requires_confirmation
    assert process_voice_turn(_turn("hydraulic start mission alpha"), voice_config=WAKE).message_code == "not_activated"


def test_push_to_talk_and_device_wake_word_start_a_turn() -> None:
    for mode in ("push_to_talk", "wake_word"):
        reply = process_voice_turn(_turn("status of robot 3", activation=mode), voice_config=WAKE)
        assert reply.message_code == "status"
    # push to talk can be refused by the site
    no_button = VoiceConfig(wake=WakeConfig(enabled=True, allow_push_to_talk=False))
    assert process_voice_turn(_turn("status", activation="push_to_talk"), voice_config=no_button).message_code == "not_activated"


def test_a_spoken_stop_needs_no_wake_word_unless_the_site_says_so() -> None:
    reply = process_voice_turn(_turn("stop"), voice_config=WAKE, stop_requires_confirmation=False)
    assert reply.message_code == "stop_now"
    strict = VoiceConfig(wake=WakeConfig(enabled=True, stop_needs_wake=True))
    assert process_voice_turn(_turn("stop"), voice_config=strict).message_code == "not_activated"


def test_a_bad_activation_or_vector_is_refused() -> None:
    with pytest.raises(VoiceTurnValidationError):
        _turn("status", activation="shout")
    with pytest.raises(VoiceTurnValidationError):
        _turn("status", speakerVector="abc")
    with pytest.raises(VoiceTurnValidationError):
        _turn("status", speakerVector=[1.0] * 600)


# ---------------------------------------------------------------- speaker identification


def _store(tmp_path: Path) -> SpeakerStore:
    return SpeakerStore(tmp_path / "speakers.json", threshold=0.9, margin=0.05, max_speakers=3)


SPEAKER_ON = VoiceConfig(speaker=SpeakerConfig(enabled=True))


def test_enrolled_voice_is_recognised_and_a_stranger_is_not(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.enroll("ana", _voice(32, 1))
    store.enroll("luis", _voice(32, 5))
    assert store.identify([v * 3 for v in _voice(32, 1)]) == "ana"
    assert store.identify(_voice(32, 11)) is None
    assert store.identify(_voice(16, 1)) is None  # another number of dimensions
    assert store.identify([0.0] * 32) is None and store.identify("x") is None


def test_two_voices_too_close_are_not_told_apart(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.enroll("ana", _voice(32, 1))
    near = [v + 0.001 * (i % 3) for i, v in enumerate(_voice(32, 1))]
    store.enroll("twin", near)
    assert store.identify(_voice(32, 1)) is None


def test_forgetting_removes_the_vector_from_the_file(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.enroll("ana", _voice(32, 1))
    assert store.forget("ana") and not store.forget("ana")
    assert "ana" not in (tmp_path / "speakers.json").read_text(encoding="utf-8")
    assert store.identify(_voice(32, 1)) is None


def test_store_limits_and_bad_vectors(tmp_path: Path) -> None:
    store = _store(tmp_path)
    for name in ("a", "b", "c"):
        store.enroll(name, _voice(32, ord(name)))
    with pytest.raises(SpeakerError):
        store.enroll("d", _voice(32, 9))
    store.enroll("a", _voice(32, 2))  # replacing one that exists is fine
    for bad in ([1.0] * 4, [0.0] * 16, [float("nan")] * 16, "abc", [True] * 16):
        with pytest.raises(SpeakerError):
            clean_vector(bad)
    with pytest.raises(SpeakerError):
        store.enroll("bad name", _voice(32, 1))


def test_a_movement_is_only_requested_for_an_enrolled_operator(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.enroll("ana", _voice(32, 1))
    ok = process_voice_turn(_turn("start mission alpha", speakerVector=_voice(32, 1)), voice_config=SPEAKER_ON, speakers=store)
    assert ok.requires_confirmation and ok.speaker == "verified"
    payload = ok.to_payload()
    assert payload["speaker"] == {"checked": True, "verified": True}
    assert "speakerVector" not in json.dumps(payload) and "ana" not in json.dumps(payload["speaker"])
    # the token belongs to the identified operator: nobody else can confirm it, the two-step confirmation stays
    token = payload["confirmationToken"]
    assert confirm_pending_action(token, subject="luis").status == "invalid"
    assert confirm_pending_action(token, subject="ana").status == "confirmed"
    for turn in (_turn("start mission alpha"), _turn("start mission alpha", speakerVector=_voice(32, 11))):
        reply = process_voice_turn(turn, voice_config=SPEAKER_ON, speakers=store)
        assert reply.message_code == "speaker_not_authorised" and reply.pending_confirmation is None and reply.speaker == "unknown"


def test_a_voice_that_is_not_the_signed_in_user_is_refused(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.enroll("ana", _voice(32, 1))
    reply = process_voice_turn(_turn("go home", subject="luis", speakerVector=_voice(32, 1)), voice_config=SPEAKER_ON, speakers=store)
    assert reply.message_code == "speaker_not_authorised"
    same = process_voice_turn(_turn("go home", subject="ana", speakerVector=_voice(32, 1)), voice_config=SPEAKER_ON, speakers=store)
    assert same.requires_confirmation


def test_stop_status_and_questions_never_need_the_voice(tmp_path: Path) -> None:
    store = _store(tmp_path)
    assert process_voice_turn(_turn("stop"), voice_config=SPEAKER_ON, speakers=store, stop_requires_confirmation=False).message_code == "stop_now"
    # even when a site asks to confirm a stop, the voice check does not hold it back
    held = process_voice_turn(_turn("stop"), voice_config=SPEAKER_ON, speakers=store, stop_requires_confirmation=True)
    assert held.message_code == "stop_confirm"
    assert process_voice_turn(_turn("status of robot 3"), voice_config=SPEAKER_ON, speakers=store).message_code == "status"


def test_voice_vector_is_not_in_the_text_form_of_a_turn() -> None:
    assert "0.84" not in repr(_turn("status", speakerVector=[0.8414709848] * 16))


# ---------------------------------------------------------------- questions about error codes


QUESTIONS = {
    "en": "what does error 0x05 mean",
    "es": "qué significa el error 0x05",
    "de": "was bedeutet der Fehler 0x05",
    "fr": "que signifie l'erreur 0x05",
    "it": "cosa significa l'errore 0x05",
    "pt": "o que significa o erro 0x05",
    "ja": "エラー 0x05 とは",
    "zh": "错误 0x05 是什么意思",
}


@pytest.mark.parametrize("language", sorted(QUESTIONS))
def test_a_question_about_a_code_is_understood_in_every_language(language: str) -> None:
    assert query_matches(QUESTIONS[language]) == {"code": "0x05"}
    classification = classify_intent(QUESTIONS[language])
    assert [m.name for m in classification.matches] == ["query_error"], language


def test_names_and_other_codes_and_ordinary_sentences() -> None:
    assert query_matches("what does the error STATUS_VERIFY_FAIL mean") == {"code": "STATUS_VERIFY_FAIL"}
    assert query_matches("what does error E42 mean") == {"code": "E42"}
    assert query_matches("what does the status of robot 3 mean") is None
    assert query_matches("error") is None
    assert [m.name for m in classify_intent("what does the status code 5 mean").matches] == ["query_error"]
    assert query_matches("x" * 500 + " mean error") is None


class _FakeDocsQa(BaseHTTPRequestHandler):
    seen: list[str] = []

    def do_GET(self) -> None:  # noqa: N802
        self.seen.append(self.path)
        code = self.path.split("code=")[-1]
        if code == "0x05":
            body = {"matches": [{"name": "STATUS_VERIFY_FAIL", "value": 5, "text": "Kind: controller bootloader status.\n\nThe image failed a check.", "citation": "mcu.md#4@abc"}]}
        else:
            body = {"matches": []}
        raw = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *args: object) -> None:
        pass


@contextmanager
def _docs_qa() -> Iterator[str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FakeDocsQa)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


def test_question_is_answered_from_the_documentation_with_its_source() -> None:
    with _docs_qa() as url:
        config = VoiceConfig(queries=QueryConfig(enabled=True, docs_qa_url=url))
        reply = process_voice_turn(_turn("what does error 0x05 mean"), voice_config=config)
        assert reply.message_code == "query_answer" and not reply.requires_confirmation and reply.pending_confirmation is None
        assert "STATUS_VERIFY_FAIL (0x05): The image failed a check." in reply.text and "Kind:" not in reply.text
        assert reply.to_payload()["sources"] == ["mcu.md#4@abc"]
        missing = process_voice_turn(_turn("what does error 0x77 mean"), voice_config=config)
        assert missing.message_code == "query_not_found"


def test_question_when_off_or_unreachable_says_so() -> None:
    assert process_voice_turn(_turn("what does error 0x05 mean"), voice_config=VoiceConfig()).message_code == "query_off"
    dead = VoiceConfig(queries=QueryConfig(enabled=True, docs_qa_url="http://127.0.0.1:9", timeout_seconds=0.5))
    assert process_voice_turn(_turn("what does error 0x05 mean"), voice_config=dead).message_code == "query_unavailable"


def test_answer_is_cut_and_a_stub_client_can_be_used() -> None:
    class Stub(DocsQaClient):
        def ask(self, code: str) -> QueryAnswer:
            return QueryAnswer("answered", "text", ("s#1@h",))

    reply = process_voice_turn(_turn("what does error 5 mean"), voice_config=VoiceConfig(queries=QueryConfig(enabled=True)), query_client=Stub(QueryConfig()))
    assert reply.text.endswith("text") and reply.sources == ("s#1@h",)


def test_a_question_can_be_made_to_need_confirmation_by_the_risk_file() -> None:
    from hydra_umc_voice_ui.risk import RiskTable

    table = RiskTable().raised("query_error", "movement")
    reply = process_voice_turn(_turn("what does error 5 mean"), voice_config=VoiceConfig(queries=QueryConfig(enabled=True)), risk_table=table)
    assert reply.requires_confirmation


# ---------------------------------------------------------------- audit log


def _audit(tmp_path: Path, **kw: object) -> AuditLog:
    return AuditLog(AuditConfig(enabled=True, file=str(tmp_path / "audit.jsonl"), **kw))  # type: ignore[arg-type]


def test_audit_is_off_by_default_and_writes_nothing(tmp_path: Path) -> None:
    log = AuditLog(AuditConfig(file=str(tmp_path / "audit.jsonl")))
    assert log.record("turn", request_id="r", intent="stop", outcome="stop_now") is False
    assert not list(tmp_path.iterdir())


def test_a_record_has_no_text_and_names_the_person_by_a_keyed_hash(tmp_path: Path) -> None:
    log = _audit(tmp_path)
    log.record("turn", request_id="req-9", intent="start_mission", outcome="confirmation_required", subject="ana", confirmation="required", speaker="verified")
    log.record("confirm", request_id="req-9", intent="start_mission", outcome="confirmed", subject="ana", confirmation="confirmed")
    log.record("turn", request_id="req-10", intent=None, outcome="something odd", subject="luis")
    raw = (tmp_path / "audit.jsonl").read_text(encoding="utf-8")
    assert "ana" not in raw and "luis" not in raw and "transcript" not in raw
    records = log.tail()
    assert records[0]["subject"] == records[1]["subject"] != records[2]["subject"] and len(str(records[0]["subject"])) == 16
    assert records[2]["outcome"] == "other" and records[0]["speaker"] == "verified"
    assert set(records[0]) == {"ts", "event", "requestId", "intent", "outcome", "confirmation", "speaker", "subject"}
    # the same name on another machine (another key) gives another hash
    other = AuditLog(AuditConfig(enabled=True, file=str(tmp_path / "other" / "audit.jsonl")))
    assert other.person("ana") != log.person("ana")


def test_plain_names_only_when_the_site_asks_for_them(tmp_path: Path) -> None:
    log = _audit(tmp_path, store_subject_plain=True)
    log.record("turn", request_id="r", intent="stop", outcome="stop_now", subject="ana")
    assert log.tail()[0]["subject"] == "ana"


def test_audit_has_a_ceiling_and_rotates(tmp_path: Path) -> None:
    log = _audit(tmp_path, max_bytes=4096, max_files=3)
    for number in range(200):
        log.record("turn", request_id=f"r-{number}", intent="status", outcome="acknowledged")
    names = sorted(p.name for p in tmp_path.iterdir() if p.name.startswith("audit.jsonl") and not p.name.endswith(".key"))
    assert names == ["audit.jsonl", "audit.jsonl.1", "audit.jsonl.2"]
    assert all(p.stat().st_size <= 4096 for p in tmp_path.glob("audit.jsonl*") if not p.name.endswith(".key"))
    assert log.tail(5)[-1]["requestId"] == "r-199"
    single = _audit(tmp_path / "one", max_bytes=4096, max_files=1)
    for number in range(200):
        single.record("turn", request_id=f"r-{number}", intent="status", outcome="acknowledged")
    assert [p.name for p in (tmp_path / "one").glob("audit.jsonl*") if not p.name.endswith(".key")] == ["audit.jsonl"]


def test_a_log_that_cannot_be_written_never_stops_a_command(tmp_path: Path) -> None:
    blocker = tmp_path / "file"
    blocker.write_text("x", encoding="utf-8")
    log = AuditLog(AuditConfig(enabled=True, file=str(blocker / "sub" / "audit.jsonl")))
    assert log.record("turn", request_id="r", intent=None, outcome="no_match") is False and log.write_errors == 1


# ---------------------------------------------------------------- alerts read aloud


def _alert(**kw: object) -> dict[str, object]:
    return {"alertId": "a-1", "source": "anomaly", "severity": "warning", "locale": "es", "verdict": "anomalous", "node": "motor-3", **kw}


def test_alerts_are_off_by_default_but_still_return_the_text() -> None:
    reply = AlertSpeaker(AlertConfig()).compose(_alert())
    assert reply.speak is False and reply.reason == "alerts_off" and "motor-3" in reply.text


@pytest.mark.parametrize("language", LANGUAGES)
def test_anomaly_verdicts_have_a_sentence_in_every_language(language: str) -> None:
    speaker = AlertSpeaker(AlertConfig(enabled=True, repeat_seconds=0))
    for verdict in ("suspect", "anomalous"):
        reply = speaker.compose(_alert(locale=language, verdict=verdict), now=1.0)
        assert reply.speak and reply.text_language == language and "motor-3" in reply.text
        assert MESSAGES[f"alert_anomaly_{verdict}"][language]


def test_severity_threshold_and_repeats() -> None:
    speaker = AlertSpeaker(AlertConfig(enabled=True, min_severity="warning", repeat_seconds=60, critical_repeat_seconds=10))
    assert speaker.compose(_alert(severity="info"), now=0).reason == "below_threshold"
    assert speaker.compose(_alert(), now=100).speak
    assert speaker.compose(_alert(), now=130).reason == "repeated"
    assert speaker.compose(_alert(), now=161).speak
    assert speaker.compose(_alert(severity="critical", node="x1"), now=200).speak
    assert speaker.compose(_alert(severity="critical", node="x1"), now=205).reason == "repeated"
    assert speaker.compose(_alert(severity="critical", node="x1"), now=211).speak


def test_a_normal_verdict_is_not_an_alert() -> None:
    reply = AlertSpeaker(AlertConfig(enabled=True)).compose(_alert(verdict="normal"))
    assert reply.speak is False and reply.reason == "normal"


def test_system_status_text_is_cleaned_and_cut() -> None:
    speaker = AlertSpeaker(AlertConfig(enabled=True, max_chars=40))
    reply = speaker.compose({"alertId": "s-1", "source": "system-status", "severity": "critical", "locale": "en", "text": "Battery\x00 low\n" + "z" * 100})
    assert "\x00" not in reply.text and "\n" not in reply.text and len(reply.text) <= 40 and reply.speak


@pytest.mark.parametrize("bad", [
    "x", {"alertId": "bad id"}, _alert(source="mail"), _alert(severity="loud"), _alert(locale="x"), _alert(verdict="odd"),
    _alert(node="a b"), {"alertId": "a", "source": "system-status", "locale": "en", "text": "  "},
])
def test_invalid_alerts_are_refused(bad: object) -> None:
    with pytest.raises(AlertError):
        AlertSpeaker(AlertConfig(enabled=True)).compose(bad)


def test_every_new_message_exists_in_the_eight_languages() -> None:
    for code in ("not_activated", "speaker_not_authorised", "query_off", "query_not_found", "query_unavailable", "query_answer",
                 "alert_anomaly_suspect", "alert_anomaly_anomalous"):
        assert set(MESSAGES[code]) == set(LANGUAGES), code


# ---------------------------------------------------------------- HTTP


def _call(url: str, body: object | None = None, token: str | None = None, method: str | None = None) -> tuple[int, dict]:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method=method or ("POST" if data is not None else "GET"))
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


@contextmanager
def _server(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, config: dict, token: str | None = "t" * 20) -> Iterator[str]:
    path = tmp_path / "voice-ui.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    monkeypatch.setenv("HYDRA_UMC_VOICE_UI_CONFIG", str(path))
    server = VoiceGatewayServer(("127.0.0.1", 0), token)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_http_enrol_identify_forget_and_audit(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config = {
        "speaker": {"enabled": True, "storeFile": str(tmp_path / "sp.json")},
        "audit": {"enabled": True, "file": str(tmp_path / "audit.jsonl")},
    }
    with _server(monkeypatch, tmp_path, config) as base:
        token = "t" * 20
        vector = _voice(32, 1)
        assert _call(f"{base}/v1/voice/speaker/enroll", {"subject": "ana", "vector": vector})[0] == 401
        assert _call(f"{base}/v1/voice/speaker/enroll", {"subject": "ana", "vector": vector}, token) == (200, {"enrolled": True, "operators": 1})
        assert _call(f"{base}/v1/voice/speaker/enroll", {"subject": "ana", "vector": [1, 2]}, token)[0] == 400
        turn = {"requestId": "w-1", "transcript": "start mission alpha", "locale": "en", "subject": "ana", "speakerVector": vector}
        status, reply = _call(f"{base}/v1/voice/turn", turn, token)
        assert status == 200 and reply["requiresConfirmation"] and reply["speaker"] == {"checked": True, "verified": True}
        status, result = _call(f"{base}/v1/voice/confirm", {"confirmationToken": reply["confirmationToken"], "subject": "ana"}, token)
        assert result["status"] == "confirmed"
        stranger = {**turn, "requestId": "w-2", "speakerVector": _voice(32, 11)}
        assert _call(f"{base}/v1/voice/turn", stranger, token)[1]["messageCode"] == "speaker_not_authorised"
        records = _call(f"{base}/v1/voice/audit?limit=10", token=token)[1]["records"]
        assert [(r["event"], r["outcome"]) for r in records] == [
            ("turn", "confirmation_required"), ("confirm", "confirmed"), ("turn", "speaker_not_authorised"),
        ]
        assert "ana" not in json.dumps(records) and "alpha" not in json.dumps(records)
        assert _call(f"{base}/v1/voice/audit", token=None)[0] == 401
        assert _call(f"{base}/v1/voice/speaker/forget", {"subject": "ana"}, token) == (200, {"forgotten": True, "operators": 0})
        assert _call(f"{base}/v1/voice/turn", turn, token)[1]["messageCode"] == "speaker_not_authorised"


def test_http_features_off_by_default(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    with _server(monkeypatch, tmp_path, {}) as base:
        token = "t" * 20
        assert _call(f"{base}/v1/voice/speaker/enroll", {"subject": "ana", "vector": _voice(32, 1)}, token)[0] == 409
        assert _call(f"{base}/v1/voice/audit", token=token)[0] == 409
        status, reply = _call(f"{base}/v1/voice/alert", _alert(), token)
        assert status == 200 and reply["speak"] is False and reply["reason"] == "alerts_off" and reply["type"] == "assistant_alert"
        assert _call(f"{base}/v1/voice/alert", {"alertId": "x"}, token)[0] == 400
        assert not list(tmp_path.glob("*.jsonl"))


def test_http_alerts_and_no_token_means_no_enrolment_or_audit_reading(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config = {"alerts": {"enabled": True}, "speaker": {"enabled": True, "storeFile": str(tmp_path / "sp.json")}, "audit": {"enabled": True, "file": str(tmp_path / "a.jsonl")}}
    with _server(monkeypatch, tmp_path, config, token=None) as base:
        assert _call(f"{base}/v1/voice/alert", _alert(locale="de"))[1]["speak"] is True
        assert _call(f"{base}/v1/voice/speaker/enroll", {"subject": "ana", "vector": _voice(32, 1)})[0] == 403
        assert _call(f"{base}/v1/voice/audit")[0] == 403


def test_the_example_configuration_is_valid_and_everything_in_it_is_off() -> None:
    example = Path(__file__).resolve().parents[1] / "deploy" / "voice-ui.json.example"
    config = parse_voice_config(json.loads(example.read_text(encoding="utf-8")))
    assert config.problems == ()
    assert config == VoiceConfig()
