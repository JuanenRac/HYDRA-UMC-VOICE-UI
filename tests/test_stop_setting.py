# =============================================================================
# HYDRA-UMC-VOICE-UI - tests/test_stop_setting.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""A spoken stop is never held back by default; confirming it is a server setting."""
from __future__ import annotations

import pytest

from hydra_umc_voice_ui.gateway import (
    STOP_CONFIRMATION_ENV,
    VoiceTurn,
    process_voice_turn,
    stop_requires_confirmation_default,
)


def _turn(transcript: str) -> VoiceTurn:
    return VoiceTurn.from_payload({"requestId": "r-stop-1", "transcript": transcript, "locale": "en-US"})


def test_the_default_is_no_confirmation() -> None:
    assert stop_requires_confirmation_default({}) is False
    assert stop_requires_confirmation_default({STOP_CONFIRMATION_ENV: "0"}) is False
    assert stop_requires_confirmation_default({STOP_CONFIRMATION_ENV: "true"}) is False
    assert stop_requires_confirmation_default({STOP_CONFIRMATION_ENV: "1"}) is True


def test_a_stop_is_answered_at_once_without_a_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(STOP_CONFIRMATION_ENV)
    reply = process_voice_turn(_turn("stop"))
    assert reply.requires_confirmation is False
    assert reply.pending_confirmation is None
    assert reply.level == "WARNING"
    assert reply.visual_state == "warning"
    payload = reply.to_payload()
    assert payload["requiresConfirmation"] is False
    assert payload["priority"] == "safety-stop"
    assert "confirmationToken" not in payload
    assert payload["intent"]["name"] == "stop"


def test_the_setting_brings_the_confirmation_back(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(STOP_CONFIRMATION_ENV, "1")
    reply = process_voice_turn(_turn("stop"))
    assert reply.requires_confirmation is True
    assert reply.pending_confirmation is not None
    assert "priority" not in reply.to_payload()


def test_the_argument_wins_over_the_setting(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(STOP_CONFIRMATION_ENV, "1")
    assert process_voice_turn(_turn("stop"), stop_requires_confirmation=False).requires_confirmation is False
    monkeypatch.delenv(STOP_CONFIRMATION_ENV)
    assert process_voice_turn(_turn("stop"), stop_requires_confirmation=True).requires_confirmation is True


def test_starting_a_movement_is_still_confirmed_whatever_the_setting(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(STOP_CONFIRMATION_ENV)
    for transcript in ("go home", "start mission alpha"):
        reply = process_voice_turn(_turn(transcript))
        assert reply.requires_confirmation is True, transcript
        assert reply.pending_confirmation is not None
        assert "priority" not in reply.to_payload()
