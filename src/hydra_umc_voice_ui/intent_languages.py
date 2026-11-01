# =============================================================================
# HYDRA-UMC-VOICE-UI - src/hydra_umc_voice_ui/intent_languages.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""The four spoken commands in the other seven languages of the project.

The English rules of `intent.py` stay as they are; the phrases here are an addition that `classify_intent` checks too, whatever the locale of
the turn is (a recognizer may hear another language than the one the person chose for the replies). Two things keep it safe:

* a phrase is only a command when it says the whole command (a verb that starts a mission *and* the word for mission; a verb of going *and*
  "home"), and words that are also small everyday words in a language ("para" in Spanish and Portuguese is a preposition) are never a stop
  by themselves, so an ordinary sentence is not read as an order;
* every language has its words of negation, and a command that is negated ("no pares", "ne t'arrête pas", "止めないで") is reported as
  negated, which the gateway answers with a request to say it again and never as the command it denies.

A stop that is read wrongly is a spoken stop and costs nothing; a movement that is read wrongly is not executed anyway, because starting a
mission and going home always need the confirmation of the primary device. What is added here changes only what is *understood*.
"""
from __future__ import annotations

import re

from .intent import (
    INTENT_GO_HOME,
    INTENT_START_MISSION,
    INTENT_STATUS,
    INTENT_STOP,
)

_I = re.IGNORECASE

# A mission id that is a real name or number and not one of the small words that follow "start the mission".
_ID = r"(?:\s+(?!(?:{skip})\b)(?P<mission_id>\w+))?"

LANGUAGE_RULES: dict[str, tuple[tuple[str, re.Pattern[str]], ...]] = {
    "es": (
        (INTENT_START_MISSION, re.compile(r"\b(?:inicia|inicies|iniciar|empieza|empieces|empezar|comienza|comiences|comenzar|arranca|arrancar)\b(?:\s+\w+){0,3}?\s+misi[oó]n\b" + _ID.format(skip="ahora|para|la|una|por|de|con|y|otra|vez"), _I)),
        (INTENT_STOP, re.compile(r"\b(?:detente|det[eé]n|detener|alto|frena|frenar|parar|par[aá]\s+(?:el\s+robot|ya|ahora))\b", _I)),
        (INTENT_STATUS, re.compile(r"\b(?:estado|situaci[oó]n)\b(?:\s+del\s+robot\s+(?P<robot_id>\d+))?", _I)),
        (INTENT_GO_HOME, re.compile(r"\b(?:vuelve|vuelvas|volver|regresa|regreses|regresar|ve|vayas|ir|vete)\s+(?:\w+\s+)?a\s+casa\b", _I)),
    ),
    "de": (
        (INTENT_START_MISSION, re.compile(r"\b(?:starte|starten|beginne|beginnen)\b(?:\s+\w+){0,3}?\s+(?:mission|auftrag)\b" + _ID.format(skip="jetzt|f[uü]r|die|eine|den|bitte|und|dann|noch|mal"), _I)),
        (INTENT_STOP, re.compile(r"\b(?:stopp|stop|halt|anhalten|abbrechen|brich\s+ab)\b", _I)),
        (INTENT_STATUS, re.compile(r"\b(?:status|zustand)\b(?:\s+von\s+roboter\s+(?P<robot_id>\d+))?", _I)),
        (INTENT_GO_HOME, re.compile(r"\b(?:fahr|fahre|fahren|geh|gehe|gehen|kehre|kehr|komm|kommen)\b(?:\s+\w+){0,2}?\s+(?:nach\s+hause|heim)\b|\b(?:nach\s+hause|heim)\s+(?:\w+\s+)?(?:fahr|fahre|fahren|geh|gehe|gehen|kommen)\b", _I)),
    ),
    "fr": (
        (INTENT_START_MISSION, re.compile(r"\b(?:d[eé]marre|d[eé]marrer|lance|lancer|commence|commencer)\b(?:\s+\w+){0,3}?\s+mission\b" + _ID.format(skip="maintenant|pour|la|une|s'il|et|puis|encore"), _I)),
        (INTENT_STOP, re.compile(r"\b(?:arr[eê]te|arr[eê]ter|arr[eê]tez|stop|halte)\b", _I)),
        (INTENT_STATUS, re.compile(r"\b(?:[eé]tat|statut)\b(?:\s+du\s+robot\s+(?P<robot_id>\d+))?", _I)),
        (INTENT_GO_HOME, re.compile(r"\b(?:rentre|rentrer|retourne|retourner|va|aller)\b(?:\s+\w+){0,2}?\s+(?:[àa]\s+la\s+maison)\b", _I)),
    ),
    "it": (
        (INTENT_START_MISSION, re.compile(r"\b(?:avvia|avviare|inizia|iniziare|comincia|cominciare)\b(?:\s+\w+){0,3}?\s+missione\b" + _ID.format(skip="ora|per|la|una|e|poi|ancora|adesso"), _I)),
        (INTENT_STOP, re.compile(r"\b(?:ferma|fermati|fermarti|fermare|stop|arresta|arrestati)\b", _I)),
        (INTENT_STATUS, re.compile(r"\b(?:stato|situazione)\b(?:\s+del\s+robot\s+(?P<robot_id>\d+))?", _I)),
        (INTENT_GO_HOME, re.compile(r"\b(?:torna|tornare|vai|andare|rientra|rientrare)\b(?:\s+\w+){0,2}?\s+a\s+casa\b", _I)),
    ),
    "pt": (
        (INTENT_START_MISSION, re.compile(r"\b(?:inicia|inicies|iniciar|come[cç]a|comeces|come[cç]ar|arranca|arrancar)\b(?:\s+\w+){0,3}?\s+miss[aã]o\b" + _ID.format(skip="agora|para|a|uma|e|depois|outra|vez"), _I)),
        (INTENT_STOP, re.compile(r"\b(?:pare|pares|parar|interrompe|interromper|stop|p[aá]ra\s+(?:o\s+rob[oô]|j[aá]|agora))\b", _I)),
        (INTENT_STATUS, re.compile(r"\b(?:estado|situa[cç][aã]o)\b(?:\s+do\s+rob[oô]\s+(?P<robot_id>\d+))?", _I)),
        (INTENT_GO_HOME, re.compile(r"\b(?:volta|voltes|voltar|regressa|regresses|regressar|vai|vás|ir)\b(?:\s+\w+){0,2}?\s+(?:[àa]\s+casa|para\s+casa)\b", _I)),
    ),
    # Japanese and Chinese are written without spaces, so their phrases are looked for as they are.
    "ja": (
        (INTENT_START_MISSION, re.compile(r"(?:ミッション.{0,3}?(?:開始|スタート|始め)|(?:開始|スタート).{0,3}?ミッション)(?:\s*(?P<mission_id>[A-Za-z0-9]+))?")),
        (INTENT_STOP, re.compile(r"(?:止まれ|止まって|止めて|止めない|止まら|停止|ストップ|中止)")),
        (INTENT_STATUS, re.compile(r"(?:状態|ステータス)(?:.{0,6}?ロボット\s*(?P<robot_id>\d+))?")),
        (INTENT_GO_HOME, re.compile(r"(?:ホーム|家|基地)(?:に|へ)(?:帰|戻)|(?:帰|戻)(?:って|れ|る).{0,3}?(?:ホーム|家)")),
    ),
    "zh": (
        (INTENT_START_MISSION, re.compile(r"(?:开始|启动|执行).{0,4}?任务(?:\s*(?P<mission_id>[A-Za-z0-9]+))?")),
        (INTENT_STOP, re.compile(r"(?:停止|停下|急停|立即停)")),
        (INTENT_STATUS, re.compile(r"(?:状态|情况)(?:.{0,4}?机器人\s*(?P<robot_id>\d+))?")),
        (INTENT_GO_HOME, re.compile(r"(?:回家|返回(?:基地|家)|回到(?:基地|家)|回基地)")),
    ),
}

# The words of negation of each language, found in the whole sentence (a command with one of them is never run as it was said).
NEGATIONS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(?:no|nunca|jam[aá]s|sin)\b", _I),                            # Spanish
    re.compile(r"\b(?:nicht|nie|niemals|kein|keine|ohne)\b", _I),                # German
    re.compile(r"\b(?:ne|pas|jamais|sans)\b|\bn'", _I),                          # French ("ne", and "n'" once the apostrophe is a plain one)
    re.compile(r"\b(?:non|mai|senza)\b", _I),                                    # Italian
    re.compile(r"\b(?:n[aã]o|nunca|sem)\b", _I),                                 # Portuguese
    re.compile(r"(?:ないで|ません|しない|なくて|やめて|やめろ|不要)"),               # Japanese
    re.compile(r"(?:不要|别|不能|不可以|没有|不)"),                                # Chinese
)


def language_matches(text: str) -> list[tuple[str, dict[str, str]]]:
    """The intents of `text` in the seven added languages, as (name, entities), each name once (the phrase that says it with the most detail)."""
    found: dict[str, dict[str, str]] = {}
    for rules in LANGUAGE_RULES.values():
        for name, pattern in rules:
            match = pattern.search(text)
            if match is None:
                continue
            entities = {key: value for key, value in match.groupdict().items() if value is not None}
            if name not in found or len(entities) > len(found[name]):
                found[name] = entities
    return list(found.items())


def is_negated(text: str) -> bool:
    """Whether the sentence carries a word of negation of any of the added languages."""
    return any(pattern.search(text) is not None for pattern in NEGATIONS)
