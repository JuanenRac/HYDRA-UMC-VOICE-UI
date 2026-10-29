# =============================================================================
# HYDRA-UMC-VOICE-UI - tests/test_server_options.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The options the Server sends with a turn (transcript in the reply, minimum confidence).

Order: the environment of this service wins, then what the Server asked of the turn, then the built-in default.
"""
from __future__ import annotations

import pytest

from hydra_umc_voice_ui.gateway import (
    HEARD_TEXT_ENV,
    MIN_CONFIDENCE_ENV,
    VoiceTurn,
    VoiceTurnValidationError,
    process_voice_turn,
)


def _payload(transcript: str = "start mission demo", **extra: object) -> dict[str, object]:
    return {"requestId": "r-opt-1", "transcript": transcript, "locale": "en-US", **extra}


@pytest.fixture(autouse=True)
def _clean_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(HEARD_TEXT_ENV, raising=False)
    monkeypatch.delenv(MIN_CONFIDENCE_ENV, raising=False)


def test_a_turn_without_options_keeps_the_defaults() -> None:
    turn = VoiceTurn.from_payload(_payload())
    assert turn.include_heard_text is None and turn.min_confidence is None
    reply = process_voice_turn(turn)
    assert "heardText" not in reply.interpretation


def test_the_server_can_ask_for_the_transcript() -> None:
    turn = VoiceTurn.from_payload(_payload(options={"includeHeardText": True}))
    assert process_voice_turn(turn).interpretation["heardText"] == "start mission demo"
    off = VoiceTurn.from_payload(_payload(options={"includeHeardText": False}))
    assert "heardText" not in process_voice_turn(off).interpretation


def test_the_environment_of_this_service_wins_over_the_server(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(HEARD_TEXT_ENV, "0")
    turn = VoiceTurn.from_payload(_payload(options={"includeHeardText": True}))
    assert "heardText" not in process_voice_turn(turn).interpretation
    monkeypatch.setenv(HEARD_TEXT_ENV, "1")
    turn = VoiceTurn.from_payload(_payload(options={"includeHeardText": False}))
    assert "heardText" in process_voice_turn(turn).interpretation


def test_the_server_can_raise_lower_or_switch_off_the_minimum_confidence() -> None:
    sure_enough_for_default = VoiceTurn.from_payload(_payload(confidence=0.7))
    assert process_voice_turn(sure_enough_for_default).intent is not None
    stricter = VoiceTurn.from_payload(_payload(confidence=0.7, options={"minConfidence": 0.9}))
    assert process_voice_turn(stricter).intent is None
    unsure = VoiceTurn.from_payload(_payload(confidence=0.1, options={"minConfidence": 0}))
    assert process_voice_turn(unsure).intent is not None


def test_the_environment_minimum_confidence_wins_over_the_server(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(MIN_CONFIDENCE_ENV, "0.95")
    turn = VoiceTurn.from_payload(_payload(confidence=0.7, options={"minConfidence": 0}))
    assert process_voice_turn(turn).intent is None


def test_a_stop_is_never_held_back_by_the_server_minimum() -> None:
    turn = VoiceTurn.from_payload(_payload("stop", confidence=0.1, options={"minConfidence": 1}))
    assert process_voice_turn(turn).intent is not None


@pytest.mark.parametrize(
    "options",
    ["x", [], {"includeHeardText": "yes"}, {"includeHeardText": 1}, {"minConfidence": -0.1}, {"minConfidence": 1.5}, {"minConfidence": "0.5"}, {"minConfidence": True}],
)
def test_bad_options_are_refused_with_a_clear_error(options: object) -> None:
    with pytest.raises(VoiceTurnValidationError, match="options"):
        VoiceTurn.from_payload(_payload(options=options))
