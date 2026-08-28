# =============================================================================
# HYDRA-UMC-VOICE-UI - src/hydra_umc_voice_ui/intent.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Real, rule-based intent/entity parsing over already-transcribed text.

Honestly a rule-based NLU parser (regex over a small real command
vocabulary for fleet voice control), not a trained ML model - v0 for the
same reason index.py in the sibling HYDRA-UMC-DOCS-QA is real TF-IDF and
not an embedding model: a real, testable kernel today that a future
ML-based intent classifier can replace behind the same `parse_intent()`
contract.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

INTENT_START_MISSION = "start_mission"
INTENT_STOP = "stop"
INTENT_STATUS = "status"
INTENT_GO_HOME = "go_home"


@dataclass(frozen=True)
class Intent:
    name: str
    entities: dict[str, str] = field(default_factory=dict)


_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        INTENT_START_MISSION,
        re.compile(r"\bstart\b.*\bmission\b(?:\s+(?P<mission_id>\w+))?", re.IGNORECASE),
    ),
    (INTENT_STOP, re.compile(r"\b(stop|halt|abort)\b", re.IGNORECASE)),
    (
        INTENT_STATUS,
        re.compile(r"\bstatus\b(?:\s+of\s+robot\s+(?P<robot_id>\d+))?", re.IGNORECASE),
    ),
    (INTENT_GO_HOME, re.compile(r"\bgo\s+home\b", re.IGNORECASE)),
)


def parse_intent(text: str) -> Intent | None:
    """Match `text` against the real rule set, first match wins.

    Returns `None` for real, honest non-matches - never a guessed intent
    for text this rule set genuinely doesn't cover.
    """
    for name, pattern in _RULES:
        match = pattern.search(text)
        if match is None:
            continue
        entities = {key: value for key, value in match.groupdict().items() if value is not None}
        return Intent(name=name, entities=entities)
    return None


_FILLER_WORDS = re.compile(r"\b(please|kindly|could you|can you|would you|robot|hey)\b", re.IGNORECASE)
_PUNCTUATION_NOISE = re.compile(r"[!?.,;:]+")
_WHITESPACE = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    """Real, deterministic normalization applied before ambiguity-aware
    classification (see `classify_intent` below) - never applied to the
    legacy `parse_intent` above, which stays exactly as tested.

    Unicode NFKC collapses compatibility forms a real speech-to-text
    transcript can emit (e.g. full-width Latin letters from certain
    input pipelines) to their ordinary ASCII equivalent, so a command
    that's semantically identical to a known rule but encoded
    differently is never treated as an honest non-match. Punctuation
    noise and common filler phrases ("please", "could you", ...) are
    stripped so they can never coincidentally shift which rule matches
    a real transcript.
    """
    normalized = unicodedata.normalize("NFKC", text)
    normalized = _PUNCTUATION_NOISE.sub(" ", normalized)
    normalized = _FILLER_WORDS.sub(" ", normalized)
    return _WHITESPACE.sub(" ", normalized).strip()


@dataclass(frozen=True)
class IntentClassification:
    """The real, honest outcome of `classify_intent()` - exactly one of
    three real cases a caller must handle distinctly: no rule matched,
    exactly one rule matched, or more than one rule matched (a real,
    reportable ambiguity - never silently resolved to whichever rule
    happens to be declared first)."""

    matches: tuple[Intent, ...]

    @property
    def is_no_match(self) -> bool:
        return len(self.matches) == 0

    @property
    def is_unambiguous(self) -> bool:
        return len(self.matches) == 1

    @property
    def is_ambiguous(self) -> bool:
        return len(self.matches) > 1


def classify_intent(text: str) -> IntentClassification:
    """Real, ambiguity-aware intent classification: normalizes `text`
    (see `normalize_text`), then checks EVERY rule - not first-match-wins
    like `parse_intent` - and reports every one that genuinely matches.
    A real voice transcript that matches more than one rule (e.g. a
    phrase containing both "stop" and "status") is a real, honest
    ambiguity a caller (see gateway.py's `process_voice_turn`) must ask
    the operator to clarify, never silently resolve on its own.
    """
    normalized = normalize_text(text)
    matches: list[Intent] = []
    for name, pattern in _RULES:
        match = pattern.search(normalized)
        if match is None:
            continue
        entities = {key: value for key, value in match.groupdict().items() if value is not None}
        matches.append(Intent(name=name, entities=entities))
    return IntentClassification(matches=tuple(matches))
