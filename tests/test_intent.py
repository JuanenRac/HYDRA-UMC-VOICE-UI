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
    classify_intent,
    normalize_text,
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


def test_normalize_strips_filler_words() -> None:
    assert normalize_text("could you please stop") == "stop"


def test_normalize_collapses_punctuation_and_whitespace() -> None:
    assert normalize_text("Stop!!!   now,,,  please") == "Stop now"


def test_normalize_collapses_full_width_unicode_to_ascii() -> None:
    # A real, concrete case NFKC normalization exists to catch: some
    # speech-to-text pipelines emit full-width Latin letters (distinct
    # Unicode code points from ordinary ASCII) - semantically identical
    # to "STOP" but byte-different, and would never match \bstop\b
    # without this normalization step.
    assert normalize_text("ＳＴＯＰ") == "STOP"


def test_classify_unambiguous_matches_a_single_intent() -> None:
    classification = classify_intent("start mission alpha")

    assert classification.is_unambiguous
    assert not classification.is_ambiguous
    assert not classification.is_no_match
    assert classification.matches[0].name == INTENT_START_MISSION


def test_classify_no_match_for_unrelated_text() -> None:
    classification = classify_intent("what is the weather today")

    assert classification.is_no_match
    assert classification.matches == ()


def test_classify_detects_a_real_ambiguous_transcript() -> None:
    # A real, concrete ambiguity: this phrase genuinely matches both the
    # STOP rule ("stop") and the STATUS rule ("status") - the exact
    # class of transcript classify_intent() exists to catch rather than
    # silently resolving to whichever rule is declared first.
    classification = classify_intent("stop the status check")

    assert classification.is_ambiguous
    matched_names = {match.name for match in classification.matches}
    assert matched_names == {INTENT_STOP, INTENT_STATUS}


def test_classify_normalizes_before_matching() -> None:
    classification = classify_intent("could you please, STOP!!!")

    assert classification.is_unambiguous
    assert classification.matches[0].name == INTENT_STOP


def test_classify_status_preserves_robot_id_entity() -> None:
    # Real regression: normalize_text() used to strip "robot" as a filler
    # word, so classify_intent (the ambiguity-aware path gateway.py's
    # process_voice_turn actually calls) silently dropped the robot_id
    # entity that parse_intent() still captured correctly - "status of
    # robot 42" was recognized as STATUS but the caller could no longer
    # tell which robot was asked about.
    classification = classify_intent("what is the status of robot 42")

    assert classification.is_unambiguous
    assert classification.matches[0].name == INTENT_STATUS
    assert classification.matches[0].entities == {"robot_id": "42"}


def test_classify_still_matches_vocative_robot_address() -> None:
    # "robot" used as an address ("hey robot, ...") never needed stripping
    # to match - every rule pattern already searches rather than requires
    # an exact match, so leaving "robot" unstripped changes nothing here.
    classification = classify_intent("hey robot, could you stop")

    assert classification.is_unambiguous
    assert classification.matches[0].name == INTENT_STOP
