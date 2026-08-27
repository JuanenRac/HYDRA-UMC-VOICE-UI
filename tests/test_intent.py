# =============================================================================
# HYDRA-UMC-VOICE-UI - tests/test_intent.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
from __future__ import annotations

from hydra_umc_voice_ui.intent import (
    INTENT_GO_HOME,
    INTENT_START_MISSION,
    INTENT_STATUS,
    INTENT_STOP,
    parse_intent,
)


def test_start_mission_with_id() -> None:
    intent = parse_intent("please start mission alpha now")

    assert intent is not None
    assert intent.name == INTENT_START_MISSION
    assert intent.entities == {"mission_id": "alpha"}


def test_start_mission_without_id() -> None:
    intent = parse_intent("start the mission")

    assert intent is not None
    assert intent.name == INTENT_START_MISSION
    assert intent.entities == {}


def test_stop_matches_synonyms() -> None:
    for phrase in ("stop", "please halt", "abort now"):
        intent = parse_intent(phrase)
        assert intent is not None
        assert intent.name == INTENT_STOP


def test_status_with_robot_id() -> None:
    intent = parse_intent("what is the status of robot 3")

    assert intent is not None
    assert intent.name == INTENT_STATUS
    assert intent.entities == {"robot_id": "3"}


def test_go_home() -> None:
    intent = parse_intent("robot, go home")

    assert intent is not None
    assert intent.name == INTENT_GO_HOME


def test_unmatched_text_returns_none() -> None:
    assert parse_intent("what is the weather today") is None
