# =============================================================================
# HYDRA-UMC-VOICE-UI - tests/test_stop_wins.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""A spoken stop wins over a negation that is not next to it and over an ambiguity; a negation next to it still cancels it."""
from __future__ import annotations

import pytest

from hydra_umc_voice_ui.gateway import STOP_CONFIRMATION_ENV, VoiceTurn, process_voice_turn
from hydra_umc_voice_ui.intent import INTENT_STOP, classify_intent
from hydra_umc_voice_ui.voice_config import VoiceConfig, WakeConfig, parse_voice_config

STOPS = [
    "stop, no, stop", "stop the mission status", "halt, I said do not wait",
    "alto, no esperes", "arrête, ne bouge pas", "ferma, non aspettare", "pare, não esperes",
    "停止、待たないで", "停止，我说过了，不要等",
]
CANCELLED = [
    "don't stop", "do not stop", "never stop", "no pares ahora detener", "nicht stopp", "ne t'arrête pas", "non fermarti", "não pare",
    "止めないで", "不要停止",
]


def _turn(text: str) -> VoiceTurn:
    return VoiceTurn.from_payload({"requestId": "r-stopwins", "transcript": text, "locale": "en-US"})


@pytest.mark.parametrize("phrase", STOPS)
def test_a_stop_that_no_negation_is_next_to_is_requested(phrase: str) -> None:
    assert classify_intent(phrase).stop_requested is True, phrase


@pytest.mark.parametrize("phrase", [p for p in CANCELLED if p != "no pares ahora detener"])
def test_a_stop_with_a_negation_next_to_it_is_not_requested(phrase: str) -> None:
    result = classify_intent(phrase)
    assert result.negated is True and result.stop_requested is False, phrase


def test_the_gateway_stops_when_the_stop_wins_and_asks_again_when_it_is_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(STOP_CONFIRMATION_ENV, raising=False)
    on_config = VoiceConfig(wake=WakeConfig(stop_wins=True))
    on = process_voice_turn(_turn("stop, no, stop"), voice_config=on_config)
    assert on.intent is not None and on.intent.name == INTENT_STOP
    assert on.to_payload()["priority"] == "safety-stop"
    assert on.interpretation["stopWins"] is True
    ambiguous = process_voice_turn(_turn("stop the mission status"), voice_config=on_config)
    assert ambiguous.intent is not None and ambiguous.intent.name == INTENT_STOP
    default = process_voice_turn(_turn("stop, no, stop"), voice_config=VoiceConfig())   # on by default
    assert default.intent is not None and default.intent.name == INTENT_STOP
    for off in (VoiceConfig(wake=WakeConfig(stop_wins=False)),):
        assert process_voice_turn(_turn("stop, no, stop"), voice_config=off).intent is None
        assert process_voice_turn(_turn("stop the mission status"), voice_config=off).intent is None


def test_a_negation_next_to_the_stop_is_still_answered_as_negated() -> None:
    reply = process_voice_turn(_turn("don't stop"), voice_config=VoiceConfig(wake=WakeConfig(stop_wins=True)))
    assert reply.intent is None and reply.message_code == "negation"


def test_the_setting_is_read_from_the_file_and_is_on_by_default() -> None:
    assert VoiceConfig().wake.stop_wins is True
    assert parse_voice_config({"wake": {"stopWins": False}}).wake.stop_wins is False
    assert parse_voice_config({"wake": {"stopWins": True}}).wake.stop_wins is True
    assert "stopWins" not in " ".join(parse_voice_config({"wake": {"stopWins": True}}).problems)
    assert parse_voice_config({"wake": {"stopWins": "yes"}}).wake.stop_wins is True  # not a true or false: ignored, the default stays
