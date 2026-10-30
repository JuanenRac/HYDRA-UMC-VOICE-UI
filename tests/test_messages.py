# =============================================================================
# HYDRA-UMC-VOICE-UI - tests/test_messages.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
from __future__ import annotations

import re
import string

import pytest

from hydra_umc_voice_ui.gateway import VoiceTurn, process_voice_turn
from hydra_umc_voice_ui.messages import DEFAULT_LANGUAGE, LANGUAGES, MESSAGES, language_of, message


def _fields(text: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(text) if name}


def test_every_sentence_exists_in_the_eight_languages_with_the_same_placeholders() -> None:
    for code, catalog in MESSAGES.items():
        assert set(catalog) == set(LANGUAGES), code
        for language in LANGUAGES:
            assert catalog[language].strip(), (code, language)
            assert _fields(catalog[language]) == _fields(catalog["en"]), (code, language)


@pytest.mark.parametrize(
    "locale,language",
    [("en-US", "en"), ("es-ES", "es"), ("de", "de"), ("fr_CA", "fr"), ("it-IT", "it"), ("ja-JP", "ja"), ("zh-Hant-TW", "zh"), ("pt-PT", "pt"), ("sv-SE", "en"), ("", "en"), (None, "en")],
)
def test_the_language_follows_the_locale_of_the_client(locale, language) -> None:
    assert language_of(locale) == language


def _turn(transcript: str, locale: str) -> VoiceTurn:
    return VoiceTurn(request_id="r1", transcript=transcript, locale=locale)


def test_a_reply_is_made_in_the_language_of_the_watch_and_names_its_code() -> None:
    reply = process_voice_turn(_turn("go home", "es-ES")).to_payload()
    assert reply["text"] == message("go_home", "es")
    assert reply["messageCode"] == "go_home" and reply["textLanguage"] == "es"
    english = process_voice_turn(_turn("go home", "en-GB")).to_payload()
    assert english["text"].startswith("Go-home request understood")
    assert english["messageCode"] == "go_home" and english["textLanguage"] == "en"


def test_the_parameters_are_filled_in_every_language() -> None:
    for language in LANGUAGES:
        text = process_voice_turn(_turn("start mission m7", language)).to_payload()["text"]
        assert "m7" in text and "{" not in text


def test_an_unknown_locale_gets_english() -> None:
    reply = process_voice_turn(_turn("blah blah blah", "sv-SE")).to_payload()
    assert reply["textLanguage"] == DEFAULT_LANGUAGE and reply["text"] == message("no_match", "en")


def test_the_safety_sentence_of_a_stop_is_not_lost_in_any_language() -> None:
    for language in LANGUAGES:
        reply = process_voice_turn(_turn("stop the robot", language), stop_requires_confirmation=False).to_payload()
        assert reply["priority"] == "safety-stop" and reply["text"] == message("stop_now", language)
