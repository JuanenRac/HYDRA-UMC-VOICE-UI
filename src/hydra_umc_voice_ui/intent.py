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
