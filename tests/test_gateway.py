# =============================================================================
# HYDRA-UMC-VOICE-UI - Watch voice gateway contract tests
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from hydra_umc_voice_ui.gateway import (
    CONFIRMATION_VALIDITY_SECONDS,
    ConfirmationError,
    PendingConfirmation,
    VoiceTurn,
    VoiceTurnValidationError,
    confirm_pending_action,
    process_voice_turn,
)
from hydra_umc_voice_ui.http_service import create_voice_gateway

NOW = datetime(2026, 1, 5, 10, 0, 0, tzinfo=timezone.utc)


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
    assert reply.intent.entities == {"robot_id": "3"}
    assert reply.requires_confirmation is False
    assert "Live telemetry will be supplied" in reply.text
    assert "for robot 3" in reply.text
    assert reply.to_payload()["visualState"] == "acknowledged"


def test_motion_related_turn_requires_primary_confirmation() -> None:
    reply = process_voice_turn(VoiceTurn.from_payload({
        "requestId": "watch-voice-002",
        "transcript": "start mission alpha",
        "locale": "en-US",
    }), now=NOW)

    assert reply.intent is not None
    assert reply.intent.name == "start_mission"
    assert reply.requires_confirmation is True
    assert "No motion is executed" in reply.text
    assert reply.to_payload()["visualState"] == "confirmation-required"
    # a real, bounded pending confirmation rides along with the
    # reply - not just a bare boolean.
    assert reply.pending_confirmation is not None
    payload = reply.to_payload()
    assert "confirmationToken" in payload
    assert payload["confirmationValiditySeconds"] == CONFIRMATION_VALIDITY_SECONDS


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


# =============================================================================
# ("Diálogo de confirmación con vigencia y resultado separado")
# =============================================================================


def test_pending_confirmation_round_trips_through_its_own_token() -> None:
    reply = process_voice_turn(VoiceTurn.from_payload({
        "requestId": "watch-voice-010", "transcript": "go home", "locale": "en-US",
    }), now=NOW)
    token = reply.to_payload()["confirmationToken"]

    result = confirm_pending_action(token, now=NOW + timedelta(seconds=5))

    assert result.status == "confirmed"
    assert result.request_id == "watch-voice-010"
    assert result.intent_name == "go_home"
    assert result.age_seconds == pytest.approx(5.0)


def test_confirmation_exactly_at_the_boundary_is_still_valid() -> None:
    # Prueba de limites: the validity window is inclusive - exactly
    # CONFIRMATION_VALIDITY_SECONDS old is still trusted, one second
    # older is not.
    reply = process_voice_turn(VoiceTurn.from_payload({
        "requestId": "watch-voice-011", "transcript": "stop", "locale": "en-US",
    }), now=NOW)
    token = reply.to_payload()["confirmationToken"]

    at_boundary = confirm_pending_action(token, now=NOW + timedelta(seconds=CONFIRMATION_VALIDITY_SECONDS))
    assert at_boundary.status == "confirmed"

    past_boundary = confirm_pending_action(token, now=NOW + timedelta(seconds=CONFIRMATION_VALIDITY_SECONDS + 1))
    assert past_boundary.status == "expired"


def test_a_late_replayed_confirmation_never_confirms_the_action() -> None:
    # this project's own literal acceptance test: a late response does not confirm
    # the action - it names the real age and the original intent, never
    # a bare "no".
    reply = process_voice_turn(VoiceTurn.from_payload({
        "requestId": "watch-voice-012", "transcript": "start mission alpha", "locale": "en-US",
    }), now=NOW)
    token = reply.to_payload()["confirmationToken"]

    result = confirm_pending_action(token, now=NOW + timedelta(minutes=10))

    assert result.status == "expired"
    assert result.intent_name == "start_mission"
    assert "600.0s old" in result.reason


def test_a_future_timestamped_confirmation_is_never_trusted_as_extra_fresh() -> None:
    # Clock skew must fail safe, exactly like calibration/observation
    # freshness checks elsewhere in this ecosystem.
    forged = PendingConfirmation(
        request_id="r1", intent_name="stop", entities=(), issued_at=NOW + timedelta(seconds=10),
    )
    result = confirm_pending_action(forged.encode(), now=NOW)
    assert result.status == "expired"
    assert "future" in result.reason


def test_a_tampered_token_is_rejected_as_invalid_not_confirmed() -> None:
    reply = process_voice_turn(VoiceTurn.from_payload({
        "requestId": "watch-voice-013", "transcript": "stop", "locale": "en-US",
    }), now=NOW)
    token = reply.to_payload()["confirmationToken"]
    body, _, checksum = token.rpartition(".")
    tampered = f"{body}x.{checksum}"

    result = confirm_pending_action(tampered, now=NOW)

    assert result.status == "invalid"
    assert result.request_id is None


def test_a_malformed_token_is_rejected_as_invalid() -> None:
    result = confirm_pending_action("not-a-real-token", now=NOW)
    assert result.status == "invalid"


def test_a_non_string_confirmation_token_is_rejected() -> None:
    result = confirm_pending_action(None, now=NOW)
    assert result.status == "invalid"
    result = confirm_pending_action(42, now=NOW)
    assert result.status == "invalid"


def test_a_changed_parameter_produces_a_different_token_never_reusable_for_the_new_action() -> None:
    # this project's own "un cambio de parametros invalida la confirmacion previa":
    # by construction, a token names the EXACT parameters it was issued
    # for - a prior token for mission "alpha" can never be replayed to
    # confirm a fresh request for mission "beta", because that fresh
    # request always mints its own, different token.
    first = process_voice_turn(VoiceTurn.from_payload({
        "requestId": "watch-voice-014", "transcript": "start mission alpha", "locale": "en-US",
    }), now=NOW)
    second = process_voice_turn(VoiceTurn.from_payload({
        "requestId": "watch-voice-015", "transcript": "start mission beta", "locale": "en-US",
    }), now=NOW)

    token_a = first.to_payload()["confirmationToken"]
    token_b = second.to_payload()["confirmationToken"]
    assert token_a != token_b

    result_a = confirm_pending_action(token_a, now=NOW)
    result_b = confirm_pending_action(token_b, now=NOW)
    assert result_a.entities == {"mission_id": "alpha"}
    assert result_b.entities == {"mission_id": "beta"}


def test_pending_confirmation_decode_rejects_a_missing_separator() -> None:
    with pytest.raises(ConfirmationError):
        PendingConfirmation.decode("no-dot-here")


def test_status_turn_never_carries_a_pending_confirmation() -> None:
    # Status is never an actionable intent - nothing to confirm.
    reply = process_voice_turn(VoiceTurn.from_payload({
        "requestId": "watch-voice-016", "transcript": "status", "locale": "en-US",
    }))
    assert reply.pending_confirmation is None
    assert "confirmationToken" not in reply.to_payload()


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


def _turn(text: str) -> VoiceTurn:
    return VoiceTurn(request_id="r1", transcript=text, locale="en-US")


def test_every_reply_says_what_was_heard_and_which_rules_matched() -> None:
    reply = process_voice_turn(_turn("Please, go home!"))
    assert reply.interpretation == {
        "heardText": "Please, go home!",
        "normalizedText": "go home",
        "matchedRules": ["go_home"],
    }
    assert reply.to_payload()["interpretation"] == reply.interpretation


def test_a_request_that_matched_nothing_or_several_rules_still_records_how_it_was_read() -> None:
    nothing = process_voice_turn(_turn("play some music"))
    assert nothing.interpretation["matchedRules"] == []
    several = process_voice_turn(_turn("stop and give me the status"))
    assert several.interpretation["matchedRules"] == ["status", "stop"]
    assert several.intent is None and not several.requires_confirmation


def test_interpreting_a_request_never_authorizes_it() -> None:
    reply = process_voice_turn(_turn("start mission alpha"))
    assert reply.requires_confirmation and reply.pending_confirmation is not None
    assert reply.interpretation["matchedRules"] == ["start_mission"]
    assert "authenticated primary control" in reply.text

