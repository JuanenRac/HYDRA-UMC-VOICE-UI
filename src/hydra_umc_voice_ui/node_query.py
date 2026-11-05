# =============================================================================
# HYDRA-UMC-VOICE-UI - src/hydra_umc_voice_ui/node_query.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Questions about how a node or a motor is doing ("how is motor 3?"), in the eight languages.

Only the question is understood here, and only as far as the name of the node: the answer is the server's (HYDRA-UMC-SERVER fills the text of the
reply from the latest verdict of the anomaly detector, as it does for the status). A question is read-only by construction: it moves nothing,
needs no confirmation, and a sentence that does not name a node or a motor ("how is the weather") is not a question about one.

The name is what the person said after the word for node (`node 7` is `7`) or, for a motor, the word and the number together (`motor 3` is
`motor3`), so that it can be compared with a series name without caring about spaces or dashes.
"""
from __future__ import annotations

import re

_I = re.IGNORECASE
_ID = r"[a-z0-9][a-z0-9_.-]{0,39}"
# the name after the word for node, or the word "motor" and its number; the same words in every language that writes the name in Latin letters
_THING = rf"(?:(?:node|nodo|knoten|n(?:œ|oe)ud|nó)\s+(?P<node>{_ID})|(?P<motor>motore|motor)\s*(?P<number>{_ID}))"

_RULES: tuple[re.Pattern[str], ...] = (
    re.compile(rf"\bhow(?:\s+is|\s+are|'s)\s+(?:the\s+)?{_THING}", _I),
    re.compile(rf"\bc[oó]mo\s+(?:est[aá]|va)\s+(?:el\s+|la\s+)?{_THING}", _I),
    re.compile(rf"\bwie\s+(?:ist|geht\s+es)\s+(?:der\s+|die\s+|das\s+|dem\s+)?{_THING}", _I),
    re.compile(rf"\bcomment\s+(?:va|est|vont)\s+(?:le\s+|la\s+)?{_THING}", _I),
    re.compile(rf"\bcome\s+(?:sta|stanno)\s+(?:il\s+|la\s+)?{_THING}", _I),
    re.compile(rf"\bcomo\s+(?:est[aá]|vai)\s+(?:o\s+|a\s+)?{_THING}", _I),
    re.compile(rf"(?:(?P<jnode>ノード)|(?P<jmotor>モーター))\s*(?P<jid>{_ID})\s*(?:の状態|の調子|はどう)", _I),
    re.compile(rf"(?:(?P<znode>节点)|(?P<zmotor>电机))\s*(?P<zid>{_ID})\s*(?:的状态|怎么样|情况如何)", _I),
)


def _compact(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def node_query_matches(text: str) -> dict[str, str] | None:
    """The entity (`node`) of a question about a node or a motor, or None when the sentence is not one."""
    for rule in _RULES:
        match = rule.search(text)
        if match is None:
            continue
        g = match.groupdict()
        if g.get("node"):
            node = g["node"]
        elif g.get("jnode"):
            node = g["jid"]
        elif g.get("znode"):
            node = g["zid"]
        elif g.get("motor"):
            node = f"motor{g['number']}"
        elif g.get("jmotor"):
            node = f"motor{g['jid']}"
        else:
            node = f"motor{g['zid']}"
        if _compact(node):
            return {"node": _compact(node)}
    return None
