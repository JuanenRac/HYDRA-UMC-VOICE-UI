# =============================================================================
# HYDRA-UMC-VOICE-UI - A confirmation is for the person who asked, and a confirmed result can be verified
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
from __future__ import annotations

import json
from datetime import datetime, timezone
from threading import Thread
from urllib.request import Request, urlopen

import pytest

from hydra_umc_voice_ui.gateway import (
    PendingConfirmation,
    VoiceTurn,
    VoiceTurnValidationError,
    confirm_pending_action,
    process_voice_turn,
    sign_result,
)
from hydra_umc_voice_ui.http_service import create_voice_gateway

NOW = datetime(2026, 1, 5, 10, 0, 0, tzinfo=timezone.utc)
KEY = b"result-key-shared-with-the-server"


def _turn(subject: str | None = None, request_id: str = "req-subject-1") -> VoiceTurn:
    payload = {"requestId": request_id, "transcript": "start mission alpha", "locale": "en-US"}
    if subject is not None:
        payload["subject"] = subject
    return VoiceTurn.from_payload(payload)


def _token(subject: str | None) -> str:
    reply = process_voice_turn(_turn(subject), now=NOW)
    assert reply.pending_confirmation is not None
    return reply.pending_confirmation.encode()


def test_the_subject_is_inside_the_signed_token() -> None:
    token = _token("alice")
    assert PendingConfirmation.decode(token).subject == "alice"
    assert PendingConfirmation.decode(_token(None)).subject == ""


def test_a_confirmation_is_for_the_subject_it_was_issued_to() -> None:
    token = _token("alice")
    wrong = confirm_pending_action(token, subject="mallory", now=NOW)
    assert wrong.status == "invalid"
    assert "someone else" in wrong.reason
    none_named = confirm_pending_action(token, now=NOW)
    assert none_named.status == "invalid"
    # a refusal does not use the token up: alice can still confirm it
    right = confirm_pending_action(token, subject="alice", now=NOW)
    assert right.status == "confirmed"
    assert right.subject == "alice"
    assert right.to_payload()["subject"] == "alice"


def test_a_token_that_names_nobody_still_confirms_by_default_and_not_when_a_subject_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    assert confirm_pending_action(_token(None), now=NOW).status == "confirmed"
    monkeypatch.setenv("HYDRA_UMC_VOICE_UI_REQUIRE_SUBJECT", "1")
    refused = confirm_pending_action(_token_without_env_check(), now=NOW)
    assert refused.status == "invalid"
    with pytest.raises(VoiceTurnValidationError):
        _turn(None)
    assert confirm_pending_action(_token("bob"), subject="bob", now=NOW).status == "confirmed"


def _token_without_env_check() -> str:
    # issued directly: with the setting on, a turn without a subject is refused before a token exists
    intent = process_voice_turn(_turn("x"), now=NOW).intent
    assert intent is not None
    return PendingConfirmation.issue("req-legacy-1", intent, NOW).encode()


def test_a_subject_with_odd_characters_is_refused() -> None:
    for bad in ("", " ", "a b", "x" * 129, "line\nbreak", '"quoted"', 7):
        payload = {"requestId": "req-1", "transcript": "stop", "locale": "en-US", "subject": bad}
        if bad == "":
            VoiceTurn.from_payload(payload)  # empty means nobody was named
            continue
        with pytest.raises(VoiceTurnValidationError):
            VoiceTurn.from_payload(payload)
    assert confirm_pending_action(_token("alice"), subject="a b", now=NOW).status == "invalid"


def test_a_confirmed_result_carries_what_the_server_needs_and_no_signature_without_a_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HYDRA_UMC_VOICE_UI_RESULT_KEY", raising=False)
    payload = confirm_pending_action(_token("alice"), subject="alice", now=NOW).to_payload()
    assert payload["status"] == "confirmed"
    assert payload["confirmedAtUtc"] == NOW.isoformat()
    assert isinstance(payload["nonce"], str) and payload["nonce"]
    assert "signature" not in payload


def test_a_confirmed_result_is_signed_with_the_result_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HYDRA_UMC_VOICE_UI_RESULT_KEY", KEY.decode())
    payload = confirm_pending_action(_token("alice"), subject="alice", now=NOW).to_payload()
    assert payload["signature"] == sign_result(payload, KEY)
    assert len(str(payload["signature"])) == 64
    # changing anything that states the confirmation changes the signature
    for name, value in (("subject", "mallory"), ("requestId", "other"), ("nonce", "0" * 16), ("confirmedAtUtc", "2030-01-01T00:00:00+00:00")):
        altered = dict(payload)
        altered[name] = value
        assert sign_result(altered, KEY) != payload["signature"], name
    altered = dict(payload)
    altered["intent"] = {"name": "go_home", "entities": {}}
    assert sign_result(altered, KEY) != payload["signature"]
    # the free text and the age are not signed
    free = dict(payload)
    free["reason"] = "anything"
    free["ageSeconds"] = 9.9
    assert sign_result(free, KEY) == payload["signature"]


def test_the_signature_has_a_fixed_value_a_verifier_in_another_language_can_check() -> None:
    payload = {
        "type": "confirmation_result",
        "status": "confirmed",
        "requestId": "req-vector-1",
        "intent": {"name": "start_mission", "entities": {"mission_id": "alpha"}},
        "subject": "alice",
        "confirmedAtUtc": "2026-01-05T10:00:00+00:00",
        "nonce": "0123456789abcdef",
    }
    # the same vector is checked by HYDRA-UMC-SERVER (tests/voiceConfirm.test.ts)
    assert sign_result(payload, KEY) == "18cc5ac19df813f96a4412eba10d979b3e9fe440e83d672544db5c9cecb6c4f7"


def test_a_result_key_that_is_too_short_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HYDRA_UMC_VOICE_UI_RESULT_KEY", "short")
    with pytest.raises(ValueError):
        confirm_pending_action(_token("alice"), subject="alice", now=NOW).to_payload()


def test_the_http_service_passes_the_subject_through_the_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HYDRA_UMC_VOICE_UI_RESULT_KEY", KEY.decode())
    server = create_voice_gateway("127.0.0.1", 0, token="gateway-token")
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    headers = {"Content-Type": "application/json", "Authorization": "Bearer gateway-token"}

    def post(path: str, body: dict[str, object]) -> dict[str, object]:
        request = Request(base + path, data=json.dumps(body).encode(), headers=headers, method="POST")
        with urlopen(request, timeout=5) as response:
            return json.loads(response.read())

    try:
        turn = post("/v1/voice/turn", {"requestId": "req-http-1", "transcript": "go home", "locale": "en-US", "subject": "alice"})
        token = turn["confirmationToken"]
        other = post("/v1/voice/confirm", {"confirmationToken": token, "subject": "mallory"})
        assert other["status"] == "invalid"
        mine = post("/v1/voice/confirm", {"confirmationToken": token, "subject": "alice"})
        assert mine["status"] == "confirmed"
        assert mine["subject"] == "alice"
        assert mine["signature"] == sign_result(mine, KEY)
    finally:
        server.shutdown()
        server.server_close()
