# =============================================================================
# HYDRA-UMC-VOICE-UI - src/hydra_umc_voice_ui/risk.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The risk level of each spoken action, read from a configuration file.

Three levels, from the least to the most risky:

* `informative` - asks for information (status). Answered at once.
* `stop` - stops motion. Answered at once, without a confirmation, because a stop
  that waits for a second answer can arrive too late.
* `movement` - starts or changes a movement (start a mission, go home). It is
  never carried out on the word alone: it needs a confirmation by the person.

The built-in table is the restrictive default. A file can only make it stricter:
an action may be moved UP to a more risky level (for example `status` to
`movement`, so a deployment asks to confirm even a status request, or `stop` to
`movement`), never down. An entry that would lower an action, name an unknown
action or level, or that is not text is ignored and reported, and the built-in
level stays. A missing, unreadable or malformed file leaves the whole default.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from .intent import INTENT_GO_HOME, INTENT_START_MISSION, INTENT_STATUS, INTENT_STOP

LEVEL_INFORMATIVE = "informative"
LEVEL_STOP = "stop"
LEVEL_MOVEMENT = "movement"

# from the least to the most risky
LEVELS: tuple[str, ...] = (LEVEL_INFORMATIVE, LEVEL_STOP, LEVEL_MOVEMENT)

# the restrictive default, and the floor under which a file cannot go
DEFAULT_LEVELS: dict[str, str] = {
    INTENT_STATUS: LEVEL_INFORMATIVE,
    INTENT_STOP: LEVEL_STOP,
    INTENT_START_MISSION: LEVEL_MOVEMENT,
    INTENT_GO_HOME: LEVEL_MOVEMENT,
}

RISK_FILE_ENV = "HYDRA_UMC_VOICE_UI_RISK_FILE"
DEFAULT_RISK_FILE = "/etc/hydra-umc/voice-ui-risk.json"


@dataclass(frozen=True)
class RiskTable:
    levels: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_LEVELS))
    # what was ignored when the file was read (empty for the default table)
    problems: tuple[str, ...] = ()

    def level_of(self, intent_name: str) -> str:
        """The level of an action; an action this table does not know is a movement (the most careful)."""
        return self.levels.get(intent_name, LEVEL_MOVEMENT)

    def requires_confirmation(self, intent_name: str) -> bool:
        """Only a movement is held until the person confirms it."""
        return self.level_of(intent_name) == LEVEL_MOVEMENT

    def raised(self, intent_name: str, level: str) -> "RiskTable":
        """The same table with one action moved up to `level` (never down)."""
        if intent_name not in DEFAULT_LEVELS or level not in LEVELS:
            return self
        if LEVELS.index(level) <= LEVELS.index(self.level_of(intent_name)):
            return self
        levels = dict(self.levels)
        levels[intent_name] = level
        return RiskTable(levels=levels, problems=self.problems)


def parse_risk_table(raw: object) -> RiskTable:
    """Builds the table from the decoded content of the file: an object with a "levels" object, for example
    {"levels": {"status": "informative", "stop": "stop", "start_mission": "movement", "go_home": "movement"}}."""
    problems: list[str] = []
    levels = dict(DEFAULT_LEVELS)
    entries = raw.get("levels") if isinstance(raw, dict) else None
    if not isinstance(entries, dict):
        return RiskTable(problems=('the file must be an object with a "levels" object; the default table stays',))
    for name, level in entries.items():
        if name not in DEFAULT_LEVELS:
            problems.append(f"{name!r} is not a known action and was ignored")
        elif not isinstance(level, str) or level not in LEVELS:
            problems.append(f"{name}: {level!r} is not one of {', '.join(LEVELS)} and was ignored")
        elif LEVELS.index(level) < LEVELS.index(DEFAULT_LEVELS[name]):
            problems.append(f"{name}: {level} is less careful than the built-in {DEFAULT_LEVELS[name]} and was ignored")
        else:
            levels[name] = level
    return RiskTable(levels=levels, problems=tuple(problems))


def load_risk_table(environ: dict[str, str] | None = None) -> RiskTable:
    """The table of this service: the file named by HYDRA_UMC_VOICE_UI_RISK_FILE, else /etc/hydra-umc/voice-ui-risk.json when it
    exists, else the restrictive default. A file that cannot be read or decoded leaves the default."""
    env = os.environ if environ is None else environ
    named = env.get(RISK_FILE_ENV, "").strip()
    path = Path(named) if named else Path(DEFAULT_RISK_FILE)
    if not path.is_file():
        if named:
            return RiskTable(problems=(f"{named}: the file does not exist; the default table stays",))
        return RiskTable()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return RiskTable(problems=(f"{path}: cannot be read ({exc.__class__.__name__}); the default table stays",))
    return parse_risk_table(raw)
