# =============================================================================
# HYDRA-UMC-VOICE-UI - Watch voice gateway contract tests
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
from __future__ import annotations

import json
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from hydra_umc_voice_ui.gateway import VoiceTurn, VoiceTurnValidationError, process_voice_turn
from hydra_umc_voice_ui.http_service import create_voice_gateway


def test_status_turn_preserves_request_id_and_never_claims_live_data() -> None:
    reply = process_voice_turn(VoiceTurn.from_payload({
        "type": "voice_turn",
        "requestId": "watch-voice-001",
        "transcript": "status of robot 3",
        "locale": "en-US",
    }))

    assert reply.request_id == "watch-voice-001"
    assert reply.intent is not None
    assert reply.intent.name == "status"
    assert reply.requires_confirmation is False
    assert "Live telemetry will be supplied" in reply.text
    assert reply.to_payload()["visualState"] == "acknowledged"


def test_motion_related_turn_requires_primary_confirmation() -> None:
    reply = process_voice_turn(VoiceTurn.from_payload({
        "requestId": "watch-voice-002",
        "transcript": "start mission alpha",
        "locale": "en-US",
    }))

    assert reply.intent is not None
    assert reply.intent.name == "start_mission"
    assert reply.requires_confirmation is True
    assert "No motion is executed" in reply.text
    assert reply.to_payload()["visualState"] == "confirmation-required"


def test_ambiguous_turn_is_rejected_not_silently_guessed() -> None:
    # A real transcript that genuinely matches more than one known
    # command (both "stop" and "status" here) must never be silently
    # resolved to one interpretation - it gets a real, distinct
    # clarification request instead, and never requires confirmation
    # (there is no single action to confirm).
    reply = process_voice_turn(VoiceTurn.from_payload({
        "requestId": "watch-voice-003",
        "transcript": "stop the status check",
        "locale": "en-US",
    }))

    assert reply.intent is None
    assert reply.requires_confirmation is False
    assert "more than one action" in reply.text
    assert "status" in reply.text and "stop" in reply.text
    assert reply.to_payload()["visualState"] == "clarification"


def test_stop_reply_has_warning_visual_state_without_claiming_execution() -> None:
    reply = process_voice_turn(VoiceTurn.from_payload({
        "requestId": "watch-voice-004",
        "transcript": "stop",
        "locale": "en-US",
    }))
    assert reply.to_payload()["visualState"] == "warning"
    assert reply.requires_confirmation is True


def test_invalid_or_oversized_turn_is_rejected() -> None:
    with pytest.raises(VoiceTurnValidationError):
        VoiceTurn.from_payload({"requestId": "bad id", "transcript": "status", "locale": "en"})
    with pytest.raises(VoiceTurnValidationError):
        VoiceTurn.from_payload({"requestId": "valid", "transcript": "x" * 501, "locale": "en"})


def test_network_bind_requires_a_private_token() -> None:
    with pytest.raises(ValueError, match="HYDRA_UMC_VOICE_UI_TOKEN"):
        create_voice_gateway("0.0.0.0", 0, token=None)


def test_loopback_gateway_can_be_created_for_local_contract_tests() -> None:
    gateway = create_voice_gateway("127.0.0.1", 0, token=None)
    try:
        assert gateway.server_address[1] > 0
    finally:
        gateway.server_close()


def test_http_gateway_requires_token_and_returns_watch_reply() -> None:
    gateway = create_voice_gateway("127.0.0.1", 0, token="test-secret")
    worker = Thread(target=gateway.serve_forever, daemon=True)
    worker.start()
    url = f"http://127.0.0.1:{gateway.server_address[1]}/v1/voice/turn"
    body = json.dumps({
        "type": "voice_turn",
        "requestId": "watch-http-001",
        "transcript": "status of robot 3",
        "locale": "en-US",
    }).encode("utf-8")
    try:
        with pytest.raises(HTTPError) as denied:
            urlopen(Request(url, data=body, method="POST"))
        assert denied.value.code == 401

        request = Request(
            url,
            data=body,
            headers={"Authorization": "Bearer test-secret", "Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request) as response:
            payload = json.loads(response.read().decode("utf-8"))
        assert payload["type"] == "assistant_reply"
        assert payload["requestId"] == "watch-http-001"
        assert payload["intent"]["name"] == "status"
    finally:
        gateway.shutdown()
        gateway.server_close()
        worker.join(timeout=2)
