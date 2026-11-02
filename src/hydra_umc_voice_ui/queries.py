# =============================================================================
# HYDRA-UMC-VOICE-UI - src/hydra_umc_voice_ui/queries.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Questions about an error code ("what does error 0x05 mean?"), answered from the documentation.

Two parts. The phrases that make a sentence a question about a code, in the eight languages (`query_matches`), and the client that asks
HYDRA-UMC-DOCS-QA for the exact definition (`DocsQaClient`). A question is read-only by construction: it never moves anything, it needs no
confirmation, and the answer is a piece of the documentation with its citation, never generated text. When DOCS-QA does not know the code
the answer is that nothing was found, not a guess.

The code is taken as the speech recogniser wrote it: a hexadecimal number (`0x05`), a number (`5`, `E42`) or a name with underscores
(`STATUS_VERIFY_FAIL`). A phrase that does not carry such a code is not a question about a code.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from .voice_config import QueryConfig

_I = re.IGNORECASE
_CODE = r"(?P<code>0x[0-9a-f]{1,4}\b|[a-z]?\d{1,5}\b|[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b)"

# (a word for "means", the words for "error" / "code" followed by the code) per language; the order of the words may vary, so the meaning
# word is checked ahead and the code is the token after "error" or "code"
_QUERY_RULES: tuple[re.Pattern[str], ...] = (
    re.compile(r"^(?=.*\b(?:mean|means|meaning|stands\s+for)\b).*?\b(?:error|fault|code)\s+(?:code\s+|number\s+)?" + _CODE, _I),
    re.compile(r"^(?=.*\b(?:significa|quiere\s+decir)\b).*?\b(?:error|fallo|c[oó]digo)\s+(?:de\s+error\s+|n[uú]mero\s+)?" + _CODE, _I),
    re.compile(r"^(?=.*\b(?:bedeutet|hei[sß]t)\b).*?\b(?:fehler|fehlercode|code)\s+(?:nummer\s+)?" + _CODE, _I),
    re.compile(r"^(?=.*\b(?:signifie|veut\s+dire)\b).*?\b(?:erreur|code)\s+(?:d'erreur\s+|num[eé]ro\s+)?" + _CODE, _I),
    re.compile(r"^(?=.*\b(?:significa|vuol\s+dire)\b).*?\b(?:errore|codice)\s+(?:di\s+errore\s+|numero\s+)?" + _CODE, _I),
    re.compile(r"^(?=.*\b(?:significa|quer\s+dizer)\b).*?\b(?:erro|c[oó]digo)\s+(?:de\s+erro\s+|n[uú]mero\s+)?" + _CODE, _I),
    re.compile(r"エラー(?:コード)?\s*" + _CODE + r".{0,6}?(?:とは|の意味|って何|はどういう)", _I),
    re.compile(r"错误(?:代码|码)?\s*" + _CODE + r".{0,6}?(?:是什么|什么意思|的意思|含义)", _I),
)


def query_matches(text: str) -> dict[str, str] | None:
    """The entities (`code`) of a question about an error code, or None when the sentence is not one."""
    for rule in _QUERY_RULES:
        match = rule.search(text)
        if match is not None:
            return {"code": match.group("code")}
    return None


@dataclass(frozen=True)
class QueryAnswer:
    status: str  # "answered" | "not_found" | "unavailable"
    text: str = ""
    sources: tuple[str, ...] = ()


def _first_meaning(text: str) -> str:
    """The definition without the line that names the kind (`Kind: ...`)."""
    lines = [line.strip() for line in text.splitlines() if line.strip() and not line.startswith("Kind:")]
    return " ".join(lines)


class DocsQaClient:
    """Asks HYDRA-UMC-DOCS-QA (`GET /error?code=`) for the definition of a code. Only the configured address is ever contacted."""

    MAX_RESPONSE_BYTES = 64 * 1024

    def __init__(self, config: QueryConfig) -> None:
        self.config = config

    def _token(self) -> str:
        if not self.config.token_file:
            return ""
        try:
            return Path(self.config.token_file).read_text(encoding="utf-8").strip()
        except (OSError, UnicodeDecodeError):
            return ""

    def ask(self, code: str) -> QueryAnswer:
        url = f"{self.config.docs_qa_url}/error?{urllib.parse.urlencode({'code': code})}"
        request = urllib.request.Request(url, headers={"Accept": "application/json"})
        token = self._token()
        if token:
            request.add_header("Authorization", f"Bearer {token}")
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:  # noqa: S310 - the scheme is checked in the config
                raw = response.read(self.MAX_RESPONSE_BYTES + 1)
            if len(raw) > self.MAX_RESPONSE_BYTES:
                return QueryAnswer("unavailable")
            data = json.loads(raw.decode("utf-8"))
        except (urllib.error.URLError, OSError, ValueError):
            return QueryAnswer("unavailable")
        matches = data.get("matches") if isinstance(data, dict) else None
        if not isinstance(matches, list):
            return QueryAnswer("unavailable")
        if not matches:
            return QueryAnswer("not_found")
        parts: list[str] = []
        sources: list[str] = []
        for item in matches[:3]:
            if not isinstance(item, dict) or not isinstance(item.get("name"), str) or not isinstance(item.get("text"), str):
                continue
            value = item.get("value")
            label = f"{item['name']} (0x{value:02X})" if isinstance(value, int) and not isinstance(value, bool) else item["name"]
            parts.append(f"{label}: {_first_meaning(item['text'])}")
            if isinstance(item.get("citation"), str):
                sources.append(item["citation"][:300])
        if not parts:
            return QueryAnswer("unavailable")
        text = " / ".join(parts)
        limit = self.config.max_answer_chars
        if len(text) > limit:
            text = text[: limit - 3].rstrip() + "..."
        return QueryAnswer("answered", text, tuple(sources))
