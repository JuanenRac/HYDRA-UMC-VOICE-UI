# =============================================================================
# HYDRA-UMC-VOICE-UI - tests/test_edge_cases.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Hostile and borderline input: negation spellings that a speech recognizer
really produces, malformed HTTP bodies, odd WAV layouts and the serve command."""
from __future__ import annotations

import array
import json
import threading
import urllib.error
import urllib.request

import pytest

from hydra_umc_voice_ui import main as main_module
from hydra_umc_voice_ui.audio import AudioClip, detect_voice_segments, rms_energy
from hydra_umc_voice_ui.gateway import (
    VoiceTurn,
    VoiceTurnValidationError,
    confirm_pending_action,
    process_voice_turn,
)
from hydra_umc_voice_ui.http_service import VoiceGatewayServer
from hydra_umc_voice_ui.intent import classify_intent, normalize_text, parse_intent


# ----------------------------------------------------------------- negation


@pytest.mark.parametrize(
    "text",
    [
        "don’t start mission alpha",  # typographic apostrophe from a phone keyboard or recognizer
        "donʼt stop",  # modifier-letter apostrophe
        "don`t stop",  # grave accent used as an apostrophe
        "shouldn't stop",
        "wouldn't go home",
        "won't start mission alpha",
        "isn't stop",
        "no stop",
        "no, go home",
        "DO NOT STOP",
        "ｄｏ ｎｏｔ stop",  # full-width "do not"
    ],
)
def test_every_spelling_of_a_negation_is_flagged(text: str) -> None:
    classification = classify_intent(text)
    assert classification.matches, text
    assert classification.negated, text


@pytest.mark.parametrize(
    "text",
    [
        "start mission alpha",
        "status of robot 3",
        "stop",
        "go home",
        "note: stop",  # "note" is not "not"
        "know the status",  # "know" is not "no"
    ],
)
def test_plain_commands_are_not_flagged_as_negated(text: str) -> None:
    assert not classify_intent(text).negated, text


def test_a_negated_curly_apostrophe_request_gets_no_confirmation_token() -> None:
    reply = process_voice_turn(
        VoiceTurn(request_id="r1", transcript="don’t start mission alpha", locale="en-US")
    )
    assert reply.pending_confirmation is None
    assert reply.requires_confirmation is False
    assert reply.intent is None
    assert "confirmationToken" not in reply.to_payload()


def test_a_negation_without_any_command_is_just_an_honest_non_match() -> None:
    classification = classify_intent("do not worry")
    assert classification.is_no_match
    assert not classification.negated


# ------------------------------------------------------------- intent edges


def test_empty_and_whitespace_text_never_match() -> None:
    for text in ("", "   ", "\n\t", "!?.,;:"):
        assert parse_intent(text) is None
        assert classify_intent(text).is_no_match


def test_a_very_long_transcript_is_still_classified() -> None:
    text = "stop " + "word " * 5000
    assert classify_intent(text).is_unambiguous


def test_stop_inside_another_word_is_not_a_stop() -> None:
    for text in ("bus stopper", "unstoppable", "abortion"):
        assert parse_intent(text) is None, text


def test_normalize_text_is_idempotent() -> None:
    once = normalize_text("Could you PLEASE, stop!!!")
    assert normalize_text(once) == once


# ----------------------------------------------------------- gateway payload


@pytest.mark.parametrize(
    "payload",
    [
        None,
        [],
        "text",
        {"requestId": "r", "transcript": "stop"},  # no locale
        {"requestId": "r", "transcript": "stop", "locale": "e"},  # locale too short
        {"requestId": "r", "transcript": "stop", "locale": "x" * 36},
        {"requestId": "", "transcript": "stop", "locale": "en"},
        {"requestId": "a b", "transcript": "stop", "locale": "en"},
        {"requestId": "a\n", "transcript": "stop", "locale": "en"},
        {"requestId": "x" * 65, "transcript": "stop", "locale": "en"},
        {"requestId": 5, "transcript": "stop", "locale": "en"},
        {"requestId": "r", "transcript": 5, "locale": "en"},
        {"requestId": "r", "transcript": "   ", "locale": "en"},
        {"requestId": "r", "transcript": "x" * 501, "locale": "en"},
        {"type": "other", "requestId": "r", "transcript": "stop", "locale": "en"},
    ],
)
def test_voice_turn_rejects_hostile_payloads(payload: object) -> None:
    with pytest.raises(VoiceTurnValidationError):
        VoiceTurn.from_payload(payload)


def test_voice_turn_accepts_the_exact_limits() -> None:
    turn = VoiceTurn.from_payload(
        {"requestId": "x" * 64, "transcript": "s" * 500, "locale": "en"}
    )
    assert len(turn.request_id) == 64 and len(turn.transcript) == 500


@pytest.mark.parametrize("token", [None, 5, [], {}, "", "no-dot", "a.b", "...", "!!!.sig", "e30.sig"])
def test_confirm_never_confirms_a_junk_token(token: object) -> None:
    assert confirm_pending_action(token).status == "invalid"


# ---------------------------------------------------------------- HTTP edges


def _request(url: str, *, method: str = "GET", body: bytes | None = None, headers: dict[str, str] | None = None):
    request = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


@pytest.fixture()
def server():
    instance = VoiceGatewayServer(("127.0.0.1", 0), "s3cret-token")
    thread = threading.Thread(target=instance.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{instance.server_address[1]}"
    instance.shutdown()
    instance.server_close()
    thread.join(timeout=2)


def _post(base: str, path: str, body: bytes, token: str | None = "s3cret-token"):
    headers = {"Content-Type": "application/json"}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    return _request(base + path, method="POST", body=body, headers=headers)


@pytest.mark.parametrize(
    "header",
    ["s3cret-token", "Basic s3cret-token", "bearer s3cret-token", "Bearer  s3cret-token", "Bearer s3cret-token "],
)
def test_only_the_exact_bearer_form_is_accepted(server: str, header: str) -> None:
    status, _ = _request(
        server + "/v1/voice/turn",
        method="POST",
        body=b"{}",
        headers={"Authorization": header, "Content-Type": "application/json"},
    )
    assert status == 401


def test_a_non_utf8_body_is_a_400_not_a_crash(server: str) -> None:
    status, payload = _post(server, "/v1/voice/turn", b"\xff\xfe\xfa")
    assert status == 400 and "error" in payload


@pytest.mark.parametrize("body", [b"[]", b"null", b"5", b'"stop"', b"{"])
def test_a_turn_whose_json_is_not_an_object_is_a_400(server: str, body: bytes) -> None:
    status, _ = _post(server, "/v1/voice/turn", body)
    assert status == 400


@pytest.mark.parametrize("body", [b"[]", b"null", b"5", b"{}", b'{"confirmationToken": 7}'])
def test_confirm_with_a_hostile_body_reports_invalid_with_200(server: str, body: bytes) -> None:
    status, payload = _post(server, "/v1/voice/confirm", body)
    assert status == 200
    assert payload["status"] == "invalid"


def test_confirm_with_malformed_json_is_a_400(server: str) -> None:
    status, _ = _post(server, "/v1/voice/confirm", b"{not json")
    assert status == 400


def test_unauthenticated_unknown_path_does_not_reveal_auth_state(server: str) -> None:
    status, _ = _post(server, "/v1/voice/nothing", b"{}", token=None)
    assert status == 404


def test_health_with_a_query_string_is_not_a_known_path(server: str) -> None:
    status, _ = _request(server + "/health?x=1")
    assert status == 404


def test_a_full_turn_then_confirm_then_replay(server: str) -> None:
    status, reply = _post(
        server,
        "/v1/voice/turn",
        json.dumps({"requestId": "abc", "transcript": "go home", "locale": "en-US"}).encode(),
    )
    assert status == 200 and reply["requiresConfirmation"] is True
    body = json.dumps({"confirmationToken": reply["confirmationToken"]}).encode()
    assert _post(server, "/v1/voice/confirm", body)[1]["status"] == "confirmed"
    assert _post(server, "/v1/voice/confirm", body)[1]["status"] == "invalid"


# ----------------------------------------------------------------------- audio


def test_a_stereo_clip_uses_both_channels_for_the_energy_gate() -> None:
    quiet = [0] * 2 * 480
    loud = [8000, -8000] * 480
    clip = AudioClip(array.array("h", quiet + loud + quiet), 16000, 2)
    segments = detect_voice_segments(clip)
    assert len(segments) == 1
    assert segments[0].start_seconds == pytest.approx(0.03, abs=0.001)
    assert segments[0].end_seconds == pytest.approx(0.06, abs=0.001)


def test_degenerate_clips_have_no_segments() -> None:
    assert detect_voice_segments(AudioClip(array.array("h"), 16000, 1)) == []
    assert detect_voice_segments(AudioClip(array.array("h", [9000] * 10), 0, 1)) == []
    assert detect_voice_segments(AudioClip(array.array("h", [9000] * 10), 16000, 0)) == []
    assert AudioClip(array.array("h"), 0, 1).duration_seconds == 0.0


def test_a_clip_that_ends_while_loud_closes_its_segment_at_the_clip_end() -> None:
    clip = AudioClip(array.array("h", [9000] * 800), 16000, 1)
    segments = detect_voice_segments(clip)
    assert len(segments) == 1
    assert segments[0].end_seconds == pytest.approx(0.05)


def test_rms_of_an_empty_block_is_zero_and_of_a_constant_is_that_constant() -> None:
    assert rms_energy([]) == 0.0
    assert rms_energy([-300, -300, -300]) == pytest.approx(300.0)


# ------------------------------------------------------------------ serve/cli


def test_serve_beyond_loopback_without_a_token_is_refused(monkeypatch, capsys) -> None:
    monkeypatch.delenv("HYDRA_UMC_VOICE_UI_TOKEN", raising=False)
    assert main_module.main(["serve", "--host", "0.0.0.0", "--port", "0"]) == 1
    assert "HYDRA_UMC_VOICE_UI_TOKEN" in capsys.readouterr().out


def test_serve_stops_cleanly_on_ctrl_c(monkeypatch, capsys) -> None:
    closed = []

    class FakeGateway:
        def serve_forever(self) -> None:
            raise KeyboardInterrupt

        def server_close(self) -> None:
            closed.append(True)

    monkeypatch.setattr(main_module, "create_voice_gateway", lambda host, port: FakeGateway())
    assert main_module.main(["serve", "--port", "8099"]) == 0
    assert closed == [True]
    assert "stopped" in capsys.readouterr().out


def test_parse_intent_command_lists_entities(capsys) -> None:
    assert main_module.main(["parse-intent", "status of robot 12"]) == 0
    output = capsys.readouterr().out
    assert "Intent: status" in output and "robot_id: 12" in output
