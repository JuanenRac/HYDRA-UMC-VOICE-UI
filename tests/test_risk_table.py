# =============================================================================
# HYDRA-UMC-VOICE-UI - tests/test_risk_table.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The risk level of each spoken action comes from a file, with a restrictive default that a file can only tighten."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from hydra_umc_voice_ui.gateway import VoiceTurn, process_voice_turn
from hydra_umc_voice_ui.risk import (
    DEFAULT_LEVELS,
    LEVEL_INFORMATIVE,
    LEVEL_MOVEMENT,
    LEVEL_STOP,
    RISK_FILE_ENV,
    RiskTable,
    load_risk_table,
    parse_risk_table,
)


def _turn(transcript: str) -> VoiceTurn:
    return VoiceTurn.from_payload({"requestId": "r-risk-1", "transcript": transcript, "locale": "en-US"})


def test_the_default_table_is_restrictive() -> None:
    table = RiskTable()
    assert table.level_of("status") == LEVEL_INFORMATIVE
    assert table.level_of("stop") == LEVEL_STOP
    assert table.level_of("start_mission") == LEVEL_MOVEMENT
    assert table.level_of("go_home") == LEVEL_MOVEMENT
    assert [name for name in DEFAULT_LEVELS if table.requires_confirmation(name)] == ["start_mission", "go_home"]


def test_an_action_the_table_does_not_know_is_a_movement() -> None:
    assert RiskTable().requires_confirmation("jog_axis") is True


def test_a_file_can_raise_an_action_but_never_lower_it() -> None:
    table = parse_risk_table({"levels": {"status": "movement", "start_mission": "informative", "go_home": "stop"}})
    assert table.level_of("status") == LEVEL_MOVEMENT
    assert table.level_of("start_mission") == LEVEL_MOVEMENT
    assert table.level_of("go_home") == LEVEL_MOVEMENT
    assert len(table.problems) == 2


@pytest.mark.parametrize("raw", [None, [], "x", {}, {"levels": []}, {"levels": "movement"}])
def test_a_malformed_table_leaves_the_default(raw: object) -> None:
    table = parse_risk_table(raw)
    assert table.levels == DEFAULT_LEVELS
    assert table.problems


def test_unknown_names_and_levels_are_ignored_and_reported() -> None:
    table = parse_risk_table({"levels": {"dance": "movement", "stop": "whenever", "status": 3}})
    assert table.levels == DEFAULT_LEVELS
    assert len(table.problems) == 3


def test_the_table_is_read_from_the_named_file(tmp_path: Path) -> None:
    path = tmp_path / "risk.json"
    path.write_text(json.dumps({"levels": {"stop": "movement"}}), encoding="utf-8")
    table = load_risk_table({RISK_FILE_ENV: str(path)})
    assert table.requires_confirmation("stop") is True
    assert table.problems == ()


def test_a_missing_or_broken_file_leaves_the_default(tmp_path: Path) -> None:
    missing = load_risk_table({RISK_FILE_ENV: str(tmp_path / "nope.json")})
    assert missing.levels == DEFAULT_LEVELS and missing.problems
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    result = load_risk_table({RISK_FILE_ENV: str(broken)})
    assert result.levels == DEFAULT_LEVELS and result.problems


def test_by_default_status_and_stop_are_answered_at_once_and_movement_is_held() -> None:
    table = RiskTable()
    assert process_voice_turn(_turn("status of robot 3"), risk_table=table, stop_requires_confirmation=False).requires_confirmation is False
    stop = process_voice_turn(_turn("stop"), risk_table=table, stop_requires_confirmation=False)
    assert stop.requires_confirmation is False and stop.priority == "safety-stop"
    for phrase in ("start mission alpha", "go home"):
        reply = process_voice_turn(_turn(phrase), risk_table=table, stop_requires_confirmation=False)
        assert reply.requires_confirmation is True and reply.pending_confirmation is not None


def test_a_table_that_raises_status_makes_it_ask_for_a_confirmation() -> None:
    table = RiskTable().raised("status", LEVEL_MOVEMENT)
    reply = process_voice_turn(_turn("status of robot 3"), risk_table=table, stop_requires_confirmation=False)
    assert reply.requires_confirmation is True
    assert reply.pending_confirmation is not None


def test_a_table_that_raises_stop_holds_the_stop() -> None:
    table = RiskTable().raised("stop", LEVEL_MOVEMENT)
    reply = process_voice_turn(_turn("stop"), risk_table=table, stop_requires_confirmation=False)
    assert reply.requires_confirmation is True
    assert reply.priority != "safety-stop"


def test_the_older_stop_setting_still_raises_the_stop() -> None:
    reply = process_voice_turn(_turn("stop"), risk_table=RiskTable(), stop_requires_confirmation=True)
    assert reply.requires_confirmation is True
