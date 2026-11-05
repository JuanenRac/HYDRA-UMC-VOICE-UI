# =============================================================================
# HYDRA-UMC-VOICE-UI - tests/test_node_query.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""A question about how a node or a motor is doing is understood in the eight languages, is read only, and is not the status of the robot."""
from __future__ import annotations

import pytest

from hydra_umc_voice_ui.gateway import VoiceTurn, process_voice_turn
from hydra_umc_voice_ui.intent import classify_intent
from hydra_umc_voice_ui.messages import LANGUAGES, MESSAGES
from hydra_umc_voice_ui.node_query import node_query_matches
from hydra_umc_voice_ui.risk import RiskTable

QUESTIONS = {
    "en": ("how is motor 3", "motor3"),
    "es": ("cómo está el motor 3", "motor3"),
    "de": ("wie ist der Knoten spindle-1", "spindle1"),
    "fr": ("comment va le nœud A7", "a7"),
    "it": ("come sta il motore 3", "motor3"),
    "pt": ("como está o nó casa2", "casa2"),
    "ja": ("モーター3の状態", "motor3"),
    "zh": ("节点B2的状态", "b2"),
}


@pytest.mark.parametrize("language", sorted(QUESTIONS))
def test_a_question_about_a_node_is_understood_in_every_language(language: str) -> None:
    text, node = QUESTIONS[language]
    assert node_query_matches(text) == {"node": node}
    assert [m.name for m in classify_intent(text).matches] == ["query_node"], language


def test_the_name_is_compared_without_spaces_or_dashes_and_ordinary_sentences_are_not_questions() -> None:
    assert node_query_matches("how is node Motor-3") == {"node": "motor3"}
    assert node_query_matches("how is the weather") is None
    assert node_query_matches("how is the robot doing") is None
    assert node_query_matches("what is the status of robot 3") is None
    assert node_query_matches("x" * 500 + " how is motor") is None


def test_it_is_not_taken_for_the_status_of_the_robot() -> None:
    assert [m.name for m in classify_intent("how is motor 3 status").matches] == ["query_node"]
    assert [m.name for m in classify_intent("status").matches] == ["status"]


def test_the_reply_names_the_node_needs_no_confirmation_and_moves_nothing() -> None:
    reply = process_voice_turn(VoiceTurn.from_payload({"requestId": "r-9", "transcript": "how is motor 3", "locale": "es"}))
    assert reply.intent is not None and reply.intent.name == "query_node"
    assert reply.requires_confirmation is False and reply.message_code == "node_query"
    assert reply.message_params == {"node": "motor3"} and "motor3" in reply.text


def test_a_deployment_can_raise_it_to_a_confirmation_but_never_lower_it() -> None:
    assert RiskTable().level_of("query_node") == "informative"
    assert RiskTable().raised("query_node", "movement").requires_confirmation("query_node") is True


def test_the_sentence_exists_in_the_eight_languages_with_the_node() -> None:
    assert set(MESSAGES["node_query"]) == set(LANGUAGES)
    assert all("{node}" in text for text in MESSAGES["node_query"].values())
