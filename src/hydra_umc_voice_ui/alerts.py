# =============================================================================
# HYDRA-UMC-VOICE-UI - src/hydra_umc_voice_ui/alerts.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Alerts read aloud: the `speak` text of the system status and the verdicts of the anomaly detector.

The server hands an alert to `POST /v1/voice/alert`; the answer says what to say, in the language of the client, and whether to say it now. The
sentence is composed here (the verdicts have fixed sentences in the eight languages; the text of a system status is the text the server wrote,
cleaned and cut to a length). Producing the sound is the job of the device (the text-to-speech of the watch or the phone), as for every reply.

Three things keep it from being a nuisance: it is off by default (`alerts.enabled`), an alert below `minSeverity` is not spoken, and the same
alert is not spoken again inside `repeatSeconds` (a critical one repeats after the shorter `criticalRepeatSeconds`). Memory is bounded.
"""
from __future__ import annotations

import re
import threading
import time
from dataclasses import dataclass

from .messages import language_of, message
from .voice_config import SEVERITIES, AlertConfig

ALERT_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
NODE_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
SOURCES = ("system-status", "anomaly")
VERDICTS = ("normal", "suspect", "anomalous")
MAX_REMEMBERED = 256
_CONTROL = re.compile(r"[\x00-\x1f\x7f-\x9f]+")


class AlertError(ValueError):
    """The alert request is not valid."""


@dataclass(frozen=True)
class AlertReply:
    alert_id: str
    text: str
    level: str
    speak: bool
    reason: str
    message_code: str
    text_language: str

    def to_payload(self) -> dict[str, object]:
        return {
            "type": "assistant_alert",
            "alertId": self.alert_id,
            "text": self.text,
            "level": self.level,
            "speak": self.speak,
            "reason": self.reason,
            "messageCode": self.message_code,
            "textLanguage": self.text_language,
        }


class AlertSpeaker:
    """Decides what to say for an alert and whether to say it now; safe to use from the threads of the HTTP server."""

    def __init__(self, config: AlertConfig) -> None:
        self.config = config
        self._last: dict[str, float] = {}
        self._lock = threading.Lock()

    def _repeated(self, key: str, severity: str, now: float) -> bool:
        window = self.config.critical_repeat_seconds if severity == "critical" else self.config.repeat_seconds
        with self._lock:
            previous = self._last.get(key)
            if previous is not None and now - previous < window:
                return True
            if len(self._last) >= MAX_REMEMBERED:
                self._last.pop(min(self._last, key=self._last.__getitem__))
            self._last[key] = now
            return False

    def compose(self, payload: object, *, now: float | None = None) -> AlertReply:
        if not isinstance(payload, dict):
            raise AlertError("request body must be a JSON object")
        alert_id = payload.get("alertId")
        if not isinstance(alert_id, str) or not ALERT_ID_PATTERN.fullmatch(alert_id):
            raise AlertError("alertId must contain 1-64 letters, digits, _ or -")
        source = payload.get("source")
        if source not in SOURCES:
            raise AlertError(f"source must be one of {', '.join(SOURCES)}")
        severity = payload.get("severity", "warning")
        if severity not in SEVERITIES:
            raise AlertError(f"severity must be one of {', '.join(SEVERITIES)}")
        locale = payload.get("locale")
        if not isinstance(locale, str) or not 2 <= len(locale) <= 35:
            raise AlertError("locale must contain 2-35 characters")
        language = language_of(locale)

        if source == "anomaly":
            verdict = payload.get("verdict")
            node = payload.get("node")
            if verdict not in VERDICTS:
                raise AlertError(f"verdict must be one of {', '.join(VERDICTS)}")
            if not isinstance(node, str) or not NODE_PATTERN.fullmatch(node):
                raise AlertError("node must contain 1-64 letters, digits, . _ or -")
            code = f"alert_anomaly_{verdict}"
            text = message(code, locale, node=node) if verdict != "normal" else ""
            key = f"anomaly:{node}:{verdict}"
            if verdict == "normal":  # a good verdict is not an alert
                return AlertReply(alert_id, "", "ATTENTION", False, "normal", code, language)
        else:
            raw = payload.get("text")
            if not isinstance(raw, str):
                raise AlertError("text must be the speak text of the system status")
            text = _CONTROL.sub(" ", raw).strip()
            if not text:
                raise AlertError("text must not be empty")
            if len(text) > self.config.max_chars:
                text = text[: self.config.max_chars - 3].rstrip() + "..."
            code = "alert_system_status"
            key = f"system:{text}"

        level = "WARNING" if severity in ("warning", "critical") else "ATTENTION"
        if not self.config.enabled:
            return AlertReply(alert_id, text, level, False, "alerts_off", code, language)
        if SEVERITIES.index(severity) < SEVERITIES.index(self.config.min_severity):
            return AlertReply(alert_id, text, level, False, "below_threshold", code, language)
        if self._repeated(key, severity, time.monotonic() if now is None else now):
            return AlertReply(alert_id, text, level, False, "repeated", code, language)
        return AlertReply(alert_id, text, level, True, "spoken", code, language)
