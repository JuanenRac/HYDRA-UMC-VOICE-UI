# =============================================================================
# HYDRA-UMC-VOICE-UI - src/hydra_umc_voice_ui/voice_config.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The settings of the optional voice features, read from one configuration file.

Everything here is a switch or a value that can be tuned, so it lives in a file and not in the code. The file is
`HYDRA_UMC_VOICE_UI_CONFIG` (default `/etc/hydra-umc/voice-ui.json`); a missing file means the defaults. Example in `deploy/voice-ui.json.example`.

Every optional feature is OFF in the defaults: the service behaves as it always did until somebody turns one on.

    {
      "wake":    {"enabled": false, "phrases": ["hydra"], "allowPushToTalk": true, "stopNeedsWake": false},
      "speaker": {"enabled": false, "storeFile": "/var/lib/hydra-umc/voice-ui-speakers.json", "threshold": 0.85, "margin": 0.05, "maxSpeakers": 16},
      "queries": {"enabled": false, "docsQaUrl": "http://127.0.0.1:8110", "tokenFile": "", "timeoutSeconds": 3.0, "maxAnswerChars": 400},
      "audit":   {"enabled": false, "file": "/var/lib/hydra-umc/voice-ui-audit.jsonl", "maxBytes": 1048576, "maxFiles": 5, "storeSubjectPlain": false},
      "alerts":  {"enabled": false, "minSeverity": "warning", "repeatSeconds": 60, "criticalRepeatSeconds": 10, "maxChars": 200}
    }

A value that is not valid is ignored and reported in `problems`, and the default for that value stays; a whole file that cannot be read leaves
every default. Raw audio is never stored by any of these features.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

CONFIG_ENV = "HYDRA_UMC_VOICE_UI_CONFIG"
DEFAULT_CONFIG_FILE = "/etc/hydra-umc/voice-ui.json"
MAX_CONFIG_BYTES = 64 * 1024

SEVERITIES = ("info", "warning", "critical")


@dataclass(frozen=True)
class WakeConfig:
    enabled: bool = False
    phrases: tuple[str, ...] = ("hydra",)
    allow_push_to_talk: bool = True
    # a spoken stop is accepted without the wake word (a stop read wrongly costs nothing); true asks for it too
    stop_needs_wake: bool = False


@dataclass(frozen=True)
class SpeakerConfig:
    enabled: bool = False
    store_file: str = "/var/lib/hydra-umc/voice-ui-speakers.json"
    threshold: float = 0.85
    margin: float = 0.05
    max_speakers: int = 16


@dataclass(frozen=True)
class QueryConfig:
    enabled: bool = False
    docs_qa_url: str = "http://127.0.0.1:8110"
    token_file: str = ""
    timeout_seconds: float = 3.0
    max_answer_chars: int = 400


@dataclass(frozen=True)
class AuditConfig:
    enabled: bool = False
    file: str = "/var/lib/hydra-umc/voice-ui-audit.jsonl"
    max_bytes: int = 1024 * 1024
    max_files: int = 5
    store_subject_plain: bool = False


@dataclass(frozen=True)
class AlertConfig:
    enabled: bool = False
    min_severity: str = "warning"
    repeat_seconds: float = 60.0
    critical_repeat_seconds: float = 10.0
    max_chars: int = 200


@dataclass(frozen=True)
class VoiceConfig:
    wake: WakeConfig = field(default_factory=WakeConfig)
    speaker: SpeakerConfig = field(default_factory=SpeakerConfig)
    queries: QueryConfig = field(default_factory=QueryConfig)
    audit: AuditConfig = field(default_factory=AuditConfig)
    alerts: AlertConfig = field(default_factory=AlertConfig)
    # what was ignored when the file was read
    problems: tuple[str, ...] = ()


def _bool(section: dict, key: str, default: bool, problems: list[str], where: str) -> bool:
    if key not in section:
        return default
    value = section[key]
    if isinstance(value, bool):
        return value
    problems.append(f"{where}.{key} must be true or false; the default stays")
    return default


def _number(section: dict, key: str, default: float, low: float, high: float, problems: list[str], where: str, whole: bool = False) -> float:
    if key not in section:
        return default
    value = section[key]
    ok = isinstance(value, (int, float)) and not isinstance(value, bool) and value == value and low <= value <= high
    if ok and whole and int(value) != value:
        ok = False
    if not ok:
        problems.append(f"{where}.{key} must be {'a whole number' if whole else 'a number'} from {low:g} to {high:g}; the default stays")
        return default
    return int(value) if whole else float(value)


def _text(section: dict, key: str, default: str, problems: list[str], where: str, maxlen: int = 512) -> str:
    if key not in section:
        return default
    value = section[key]
    if isinstance(value, str) and len(value) <= maxlen and "\x00" not in value:
        return value
    problems.append(f"{where}.{key} must be text of at most {maxlen} characters; the default stays")
    return default


def _section(raw: dict, name: str, problems: list[str]) -> dict:
    value = raw.get(name, {})
    if isinstance(value, dict):
        return value
    problems.append(f"{name} must be an object; the defaults stay")
    return {}


def _unknown(section: dict, known: tuple[str, ...], where: str, problems: list[str]) -> None:
    for key in section:
        if key not in known:
            problems.append(f"{where}.{key} is not a known setting and was ignored")


def parse_voice_config(raw: object) -> VoiceConfig:
    """The configuration from the decoded content of the file."""
    if not isinstance(raw, dict):
        return VoiceConfig(problems=("the file must be a JSON object; the defaults stay",))
    problems: list[str] = []
    for name in raw:
        if name not in ("wake", "speaker", "queries", "audit", "alerts"):
            problems.append(f"{name!r} is not a known section and was ignored")

    s = _section(raw, "wake", problems)
    _unknown(s, ("enabled", "phrases", "allowPushToTalk", "stopNeedsWake"), "wake", problems)
    d = WakeConfig()
    phrases = d.phrases
    if "phrases" in s:
        listed = s["phrases"]
        if isinstance(listed, list) and listed and len(listed) <= 8 and all(isinstance(p, str) and 2 <= len(p.strip()) <= 40 for p in listed):
            phrases = tuple(p.strip().lower() for p in listed)
        else:
            problems.append("wake.phrases must be a list of 1 to 8 phrases of 2 to 40 characters; the default stays")
    wake = WakeConfig(
        enabled=_bool(s, "enabled", d.enabled, problems, "wake"),
        phrases=phrases,
        allow_push_to_talk=_bool(s, "allowPushToTalk", d.allow_push_to_talk, problems, "wake"),
        stop_needs_wake=_bool(s, "stopNeedsWake", d.stop_needs_wake, problems, "wake"),
    )

    s = _section(raw, "speaker", problems)
    _unknown(s, ("enabled", "storeFile", "threshold", "margin", "maxSpeakers"), "speaker", problems)
    d2 = SpeakerConfig()
    speaker = SpeakerConfig(
        enabled=_bool(s, "enabled", d2.enabled, problems, "speaker"),
        store_file=_text(s, "storeFile", d2.store_file, problems, "speaker"),
        threshold=_number(s, "threshold", d2.threshold, 0.5, 1.0, problems, "speaker"),
        margin=_number(s, "margin", d2.margin, 0.0, 0.5, problems, "speaker"),
        max_speakers=int(_number(s, "maxSpeakers", d2.max_speakers, 1, 256, problems, "speaker", whole=True)),
    )

    s = _section(raw, "queries", problems)
    _unknown(s, ("enabled", "docsQaUrl", "tokenFile", "timeoutSeconds", "maxAnswerChars"), "queries", problems)
    d3 = QueryConfig()
    url = _text(s, "docsQaUrl", d3.docs_qa_url, problems, "queries", 256)
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        problems.append("queries.docsQaUrl must be an http or https address without credentials; the default stays")
        url = d3.docs_qa_url
    queries = QueryConfig(
        enabled=_bool(s, "enabled", d3.enabled, problems, "queries"),
        docs_qa_url=url.rstrip("/"),
        token_file=_text(s, "tokenFile", d3.token_file, problems, "queries"),
        timeout_seconds=_number(s, "timeoutSeconds", d3.timeout_seconds, 0.2, 30.0, problems, "queries"),
        max_answer_chars=int(_number(s, "maxAnswerChars", d3.max_answer_chars, 40, 2000, problems, "queries", whole=True)),
    )

    s = _section(raw, "audit", problems)
    _unknown(s, ("enabled", "file", "maxBytes", "maxFiles", "storeSubjectPlain"), "audit", problems)
    d4 = AuditConfig()
    audit = AuditConfig(
        enabled=_bool(s, "enabled", d4.enabled, problems, "audit"),
        file=_text(s, "file", d4.file, problems, "audit"),
        max_bytes=int(_number(s, "maxBytes", d4.max_bytes, 4096, 256 * 1024 * 1024, problems, "audit", whole=True)),
        max_files=int(_number(s, "maxFiles", d4.max_files, 1, 100, problems, "audit", whole=True)),
        store_subject_plain=_bool(s, "storeSubjectPlain", d4.store_subject_plain, problems, "audit"),
    )

    s = _section(raw, "alerts", problems)
    _unknown(s, ("enabled", "minSeverity", "repeatSeconds", "criticalRepeatSeconds", "maxChars"), "alerts", problems)
    d5 = AlertConfig()
    severity = _text(s, "minSeverity", d5.min_severity, problems, "alerts", 16)
    if severity not in SEVERITIES:
        problems.append(f"alerts.minSeverity must be one of {', '.join(SEVERITIES)}; the default stays")
        severity = d5.min_severity
    alerts = AlertConfig(
        enabled=_bool(s, "enabled", d5.enabled, problems, "alerts"),
        min_severity=severity,
        repeat_seconds=_number(s, "repeatSeconds", d5.repeat_seconds, 0.0, 86400.0, problems, "alerts"),
        critical_repeat_seconds=_number(s, "criticalRepeatSeconds", d5.critical_repeat_seconds, 0.0, 86400.0, problems, "alerts"),
        max_chars=int(_number(s, "maxChars", d5.max_chars, 20, 1000, problems, "alerts", whole=True)),
    )
    return VoiceConfig(wake=wake, speaker=speaker, queries=queries, audit=audit, alerts=alerts, problems=tuple(problems))


_cache: dict[str, tuple[tuple[int, int], VoiceConfig]] = {}


def load_voice_config(environ: dict[str, str] | None = None) -> VoiceConfig:
    """The configuration of this service: the file named by HYDRA_UMC_VOICE_UI_CONFIG, else /etc/hydra-umc/voice-ui.json when it exists,
    else the defaults (everything optional off). Read again only when the file changes."""
    env = os.environ if environ is None else environ
    named = env.get(CONFIG_ENV, "").strip()
    path = Path(named) if named else Path(DEFAULT_CONFIG_FILE)
    try:
        stat = path.stat()
    except OSError:
        if named:
            return VoiceConfig(problems=(f"{named}: the file does not exist; the defaults stay",))
        return VoiceConfig()
    stamp = (stat.st_mtime_ns, stat.st_size)
    cached = _cache.get(str(path))
    if cached is not None and cached[0] == stamp:
        return cached[1]
    if stat.st_size > MAX_CONFIG_BYTES:
        return VoiceConfig(problems=(f"{path}: larger than {MAX_CONFIG_BYTES} bytes; the defaults stay",))
    try:
        config = parse_voice_config(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError) as exc:
        return VoiceConfig(problems=(f"{path}: cannot be read ({exc.__class__.__name__}); the defaults stay",))
    _cache[str(path)] = (stamp, config)
    return config
