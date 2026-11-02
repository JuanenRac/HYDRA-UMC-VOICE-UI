# =============================================================================
# HYDRA-UMC-VOICE-UI - src/hydra_umc_voice_ui/audit.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The audit log of the voice commands: who asked for what, and what came of it.

For traceability, not for surveillance. A record holds the request id, the kind of event, the intent that was understood, the outcome (a short
code from a closed list), whether a confirmation was asked and how it ended, and who it was for. It never holds the transcript, the audio,
a voice vector, the locale or an address.

The person is written as a short keyed hash (`subject`), so the log shows that the same operator did two things without saying who they are;
`storeSubjectPlain` writes the name instead, for a site that wants it. The log has a ceiling: one file grows to `maxBytes`, then it is rotated
(`.1`, `.2`, ... up to `maxFiles` files in all) and the oldest is dropped, so the disk can never fill because of it. It is off by default
(`audit.enabled`). A record that cannot be written never stops a voice command.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import threading
from datetime import datetime, timezone
from pathlib import Path

from .voice_config import AuditConfig

MAX_READ = 200
OUTCOMES = frozenset({
    "acknowledged", "confirmation_required", "stop_now", "negation", "no_match", "ambiguous", "not_sure", "not_activated",
    "speaker_not_authorised", "query_answered", "query_not_found", "query_unavailable", "query_off",
    "confirmed", "expired", "invalid",
})


class AuditLog:
    def __init__(self, config: AuditConfig) -> None:
        self.config = config
        self.path = Path(config.file)
        self._lock = threading.Lock()
        self._salt: bytes | None = None
        self.write_errors = 0

    # a random key kept beside the log, so the same name gives the same short hash on this machine and on no other
    def _key(self) -> bytes:
        if self._salt is None:
            keyfile = self.path.with_name(self.path.name + ".key")
            try:
                self._salt = bytes.fromhex(keyfile.read_text(encoding="ascii").strip())
            except (OSError, ValueError):
                self._salt = secrets.token_bytes(32)
                keyfile.parent.mkdir(parents=True, exist_ok=True)
                descriptor = os.open(keyfile, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
                with os.fdopen(descriptor, "w", encoding="ascii") as stream:
                    stream.write(self._salt.hex())
        return self._salt

    def person(self, subject: str) -> str:
        """How the log names a person: the keyed hash (16 hex characters), or the name itself when the site asked for that."""
        if not subject:
            return ""
        if self.config.store_subject_plain:
            return subject
        return hmac.new(self._key(), subject.encode("utf-8"), hashlib.sha256).hexdigest()[:16]

    def _rotate(self) -> None:
        # path.(max-1) is dropped, the others move up one, the current file becomes .1
        for number in range(self.config.max_files - 1, 0, -1):
            source = self.path if number == 1 else self.path.with_name(f"{self.path.name}.{number - 1}")
            target = self.path.with_name(f"{self.path.name}.{number}")
            if source.exists():
                os.replace(source, target)
        if self.config.max_files == 1 and self.path.exists():
            self.path.unlink()  # a single file: the log restarts when it is full

    def record(
        self,
        event: str,
        *,
        request_id: str | None,
        intent: str | None,
        outcome: str,
        subject: str = "",
        confirmation: str = "none",
        speaker: str = "off",
        now: datetime | None = None,
    ) -> bool:
        """Appends one record. Returns False when auditing is off or the record could not be written (it never raises)."""
        if not self.config.enabled:
            return False
        stamp = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat(timespec="seconds")
        try:
            record = {
                "ts": stamp,
                "event": event if event in ("turn", "confirm") else "turn",
                "requestId": request_id or "",
                "intent": intent or "",
                "outcome": outcome if outcome in OUTCOMES else "other",
                "confirmation": confirmation if confirmation in ("none", "required", "confirmed", "expired", "invalid") else "none",
                "speaker": speaker if speaker in ("off", "verified", "unknown") else "off",
                "subject": self.person(subject),
            }
            line = (json.dumps(record, separators=(",", ":")) + "\n").encode("utf-8")
            with self._lock:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                if self.path.exists() and self.path.stat().st_size + len(line) > self.config.max_bytes:
                    self._rotate()
                flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
                descriptor = os.open(self.path, flags, 0o600)
                with os.fdopen(descriptor, "ab") as stream:
                    stream.write(line)
            return True
        except OSError:
            self.write_errors += 1
            return False

    def tail(self, limit: int = 50) -> list[dict[str, object]]:
        """The most recent records (newest last), at most MAX_READ, for the server to collect."""
        limit = max(1, min(int(limit), MAX_READ))
        with self._lock:
            files = [self.path] + [self.path.with_name(f"{self.path.name}.{n}") for n in range(1, self.config.max_files)]
            lines: list[str] = []
            for file in files:  # newest file first; stop when there are enough
                try:
                    lines = file.read_text(encoding="utf-8").splitlines() + lines
                except OSError:
                    continue
                if len(lines) >= limit:
                    break
        records = []
        for line in lines[-limit:]:
            try:
                item = json.loads(line)
            except ValueError:
                continue
            if isinstance(item, dict):
                records.append(item)
        return records
