# =============================================================================
# HYDRA-UMC-VOICE-UI - src/hydra_umc_voice_ui/metrics.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""What the gateway counts about itself, in the text format of Prometheus (`GET /metrics`, version 0.0.4 of the exposition format).

Only numbers about the service are published. What a person said is personal data and is never a metric: not the transcript, not the request
id, not the subject, not an address. The only label that comes from a turn is the name of the intent, which belongs to a closed list (the four
commands, or "none" for a sentence that was not understood, negated or ambiguous).
"""
from __future__ import annotations

import threading
import time
from collections import Counter

from . import __version__

# the closed list of values a label may take, so a turn can never put free text in a metric
INTENT_LABELS = ("start_mission", "stop", "status", "go_home", "query_error", "none")
REFUSALS = ("unauthorized", "rate_limited", "bad_request", "too_large")


class Metrics:
    """Counters of the gateway; safe to use from the threads of the HTTP server."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._started = time.monotonic()
        self._turns: Counter[str] = Counter()
        self._refusals: Counter[str] = Counter()
        self._confirmations = 0
        self._confirmation_requests = 0

    def turn(self, intent: str | None, *, needs_confirmation: bool) -> None:
        label = intent if intent in INTENT_LABELS else "none"
        with self._lock:
            self._turns[label] += 1
            if needs_confirmation:
                self._confirmation_requests += 1

    def confirmation(self) -> None:
        with self._lock:
            self._confirmations += 1

    def refused(self, reason: str) -> None:
        with self._lock:
            self._refusals[reason if reason in REFUSALS else "bad_request"] += 1

    def render(self, audit: dict[str, object] | None = None) -> str:
        with self._lock:
            turns, refusals = dict(self._turns), dict(self._refusals)
            confirmations, requests = self._confirmations, self._confirmation_requests
        lines = [
            "# HELP hydra_umc_voice_ui_info The version of the running service.",
            "# TYPE hydra_umc_voice_ui_info gauge",
            f'hydra_umc_voice_ui_info{{version="{__version__}"}} 1',
            "# HELP hydra_umc_voice_ui_uptime_seconds Seconds since the gateway started.",
            "# TYPE hydra_umc_voice_ui_uptime_seconds gauge",
            f"hydra_umc_voice_ui_uptime_seconds {int(time.monotonic() - self._started)}",
            "# HELP hydra_umc_voice_ui_turns_total Voice turns answered, by the intent that was understood.",
            "# TYPE hydra_umc_voice_ui_turns_total counter",
        ]
        lines += [f'hydra_umc_voice_ui_turns_total{{intent="{label}"}} {turns.get(label, 0)}' for label in INTENT_LABELS]
        lines += [
            "# HELP hydra_umc_voice_ui_confirmations_requested_total Turns that asked for the confirmation of the primary device.",
            "# TYPE hydra_umc_voice_ui_confirmations_requested_total counter",
            f"hydra_umc_voice_ui_confirmations_requested_total {requests}",
            "# HELP hydra_umc_voice_ui_confirmations_checked_total Confirmation tokens that were checked.",
            "# TYPE hydra_umc_voice_ui_confirmations_checked_total counter",
            f"hydra_umc_voice_ui_confirmations_checked_total {confirmations}",
            "# HELP hydra_umc_voice_ui_refused_total Requests refused before they reached the gateway logic, by the reason.",
            "# TYPE hydra_umc_voice_ui_refused_total counter",
        ]
        lines += [f'hydra_umc_voice_ui_refused_total{{reason="{reason}"}} {refusals.get(reason, 0)}' for reason in REFUSALS]
        if audit is not None:
            enabled = bool(audit.get("enabled"))
            writable = 1 if not enabled else int(bool(audit.get("writable")))
            errors = audit.get("writeErrors")
            lines += [
                "# HELP hydra_umc_voice_ui_audit_enabled 1 when the voice audit log is switched on.",
                "# TYPE hydra_umc_voice_ui_audit_enabled gauge",
                f"hydra_umc_voice_ui_audit_enabled {int(enabled)}",
                "# HELP hydra_umc_voice_ui_audit_writable 1 when the last audit record was written (or none was tried yet), 0 when it could not be.",
                "# TYPE hydra_umc_voice_ui_audit_writable gauge",
                f"hydra_umc_voice_ui_audit_writable {writable}",
                "# HELP hydra_umc_voice_ui_audit_write_errors_total Audit records that could not be written.",
                "# TYPE hydra_umc_voice_ui_audit_write_errors_total counter",
                f"hydra_umc_voice_ui_audit_write_errors_total {errors if isinstance(errors, int) else 0}",
            ]
        return "\n".join(lines) + "\n"
