# =============================================================================
# HYDRA-UMC-VOICE-UI - tests/test_intent_languages.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""The four spoken commands in the eight languages, what negates them, and what an ordinary sentence must not become."""
from __future__ import annotations

import pytest

from hydra_umc_voice_ui.intent import (
    INTENT_GO_HOME,
    INTENT_START_MISSION,
    INTENT_STATUS,
    INTENT_STOP,
    classify_intent,
)

# (language, phrase, intent, entities)
SAYINGS = [
    ("en", "start mission alpha", INTENT_START_MISSION, {"mission_id": "alpha"}),
    ("en", "stop", INTENT_STOP, {}),
    ("en", "status of robot 3", INTENT_STATUS, {"robot_id": "3"}),
    ("en", "go home", INTENT_GO_HOME, {}),
    ("es", "inicia la misión alfa", INTENT_START_MISSION, {"mission_id": "alfa"}),
    ("es", "detente", INTENT_STOP, {}),
    ("es", "estado del robot 3", INTENT_STATUS, {"robot_id": "3"}),
    ("es", "vuelve a casa", INTENT_GO_HOME, {}),
    ("de", "starte Mission Alpha", INTENT_START_MISSION, {"mission_id": "Alpha"}),
    ("de", "stopp", INTENT_STOP, {}),
    ("de", "Status von Roboter 3", INTENT_STATUS, {"robot_id": "3"}),
    ("de", "fahr nach Hause", INTENT_GO_HOME, {}),
    ("fr", "démarre la mission alpha", INTENT_START_MISSION, {"mission_id": "alpha"}),
    ("fr", "arrête", INTENT_STOP, {}),
    ("fr", "état du robot 3", INTENT_STATUS, {"robot_id": "3"}),
    ("fr", "rentre à la maison", INTENT_GO_HOME, {}),
    ("it", "avvia la missione alfa", INTENT_START_MISSION, {"mission_id": "alfa"}),
    ("it", "fermati", INTENT_STOP, {}),
    ("it", "stato del robot 3", INTENT_STATUS, {"robot_id": "3"}),
    ("it", "torna a casa", INTENT_GO_HOME, {}),
    ("pt", "inicia a missão alfa", INTENT_START_MISSION, {"mission_id": "alfa"}),
    ("pt", "pare", INTENT_STOP, {}),
    ("pt", "estado do robô 3", INTENT_STATUS, {"robot_id": "3"}),
    ("pt", "volta para casa", INTENT_GO_HOME, {}),
    ("ja", "ミッション開始 alpha", INTENT_START_MISSION, {"mission_id": "alpha"}),
    ("ja", "止まれ", INTENT_STOP, {}),
    ("ja", "ロボット 3 の状態", INTENT_STATUS, {}),
    ("ja", "家に帰って", INTENT_GO_HOME, {}),
    ("zh", "开始任务 alpha", INTENT_START_MISSION, {"mission_id": "alpha"}),
    ("zh", "停止", INTENT_STOP, {}),
    ("zh", "状态", INTENT_STATUS, {}),
    ("zh", "回家", INTENT_GO_HOME, {}),
]


@pytest.mark.parametrize(("language", "phrase", "intent", "entities"), SAYINGS)
def test_every_command_is_understood_in_every_language(language: str, phrase: str, intent: str, entities: dict[str, str]) -> None:
    result = classify_intent(phrase)
    assert [match.name for match in result.matches] == [intent], f"{language}: {phrase!r}"
    assert result.negated is False
    assert result.matches[0].entities == entities


def test_the_eight_languages_each_have_the_four_commands() -> None:
    by_language: dict[str, set[str]] = {}
    for language, _phrase, intent, _entities in SAYINGS:
        by_language.setdefault(language, set()).add(intent)
    assert set(by_language) == {"en", "es", "de", "fr", "it", "pt", "ja", "zh"}
    assert all(len(intents) == 4 for intents in by_language.values())


NEGATED = [
    "no pares", "no inicies la misión alfa", "nunca vuelvas a casa",
    "nicht stopp", "starte die Mission Alpha nicht", "niemals nach Hause fahren",
    "ne t'arrête pas", "ne démarre pas la mission alpha", "jamais rentrer à la maison",
    "non fermarti", "non avviare la missione alfa", "mai tornare a casa",
    "não pare", "nunca inicies a missão alfa", "não voltes para casa",
    "止めないで", "ミッションを開始しないで", "家に帰らないで",
    "不要停止", "别开始任务", "不要回家",
]


@pytest.mark.parametrize("phrase", NEGATED)
def test_a_negated_command_is_reported_as_negated_in_every_language(phrase: str) -> None:
    result = classify_intent(phrase)
    assert result.matches, f"{phrase!r} was not read as a command at all"
    assert result.negated is True, phrase


ORDINARY = [
    "para qué sirve esto", "la casa de mi madre está lejos", "alto nivel de batería", "la misión de ayer fue larga",
    "ich habe heute Zeit", "das ist ein Auftrag", "la mission du jour", "la casa è bella",
    "esta casa é grande", "今日はいい天気です", "今天天气很好", "good morning everyone",
]


@pytest.mark.parametrize("phrase", ORDINARY)
def test_an_ordinary_sentence_is_never_read_as_a_movement(phrase: str) -> None:
    result = classify_intent(phrase)
    assert not any(match.name in (INTENT_START_MISSION, INTENT_GO_HOME) for match in result.matches), phrase


def test_a_phrase_that_says_two_commands_is_ambiguous_in_any_language() -> None:
    for phrase in ("detente y dime el estado", "stopp und Status", "arrête et dis l'état", "ferma e dimmi lo stato", "pare e diz o estado", "止まれ 状態", "停止 状态"):
        assert classify_intent(phrase).is_ambiguous, phrase


def test_the_english_rules_are_unchanged_by_the_other_languages() -> None:
    assert [m.name for m in classify_intent("please stop now").matches] == [INTENT_STOP]
    assert classify_intent("what a nice day").is_no_match
    assert classify_intent("do not start mission alpha").negated is True
