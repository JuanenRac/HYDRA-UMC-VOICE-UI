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
(`.1`, `.2`, ... up to `maxFiles` files in all) and the oldest is dropped, so the disk can never fill because of it. It is ON by default
(`audit.enabled` switches it off). A record that cannot be written never stops a voice command: the failure is counted and shown in
`/health` and `/metrics` instead.

Each record is also signed (`audit.transcriptHmac`, ON by default): `sig` is the HMAC-SHA256, in hex, of the record written with sorted keys and
no spaces, and `kid` is the first eight hex digits of the SHA-256 of the key, so a record says which key signed it (a key that was replaced can
still be given to the verifier). The key is a file outside the repository (`audit.hmacKeyFile`, by default `<file>.hmac.key`), created with
permissions `0600` when it is missing and never printed or logged. When the switch is on and the key cannot be had (it cannot be created, or the
file is damaged and is NOT overwritten) the log goes on, but every record carries `unsigned` with the reason, and `/health`, `/metrics` and
`status()` say so: it never fails silently and never switches itself off. Check a log with
`python -m hydra_umc_voice_ui.audit FILE... [--config voice-ui.json | --key-file KEY]...`; the signature detects a changed or forged line, not a
deleted whole line.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sys
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


def canonical(record: dict[str, object]) -> bytes:
    """The bytes that are signed: the record without `sig`, with sorted keys and no spaces."""
    return json.dumps({k: v for k, v in record.items() if k != "sig"}, sort_keys=True, separators=(",", ":")).encode("utf-8")


def key_id(key: bytes) -> str:
    return hashlib.sha256(key).hexdigest()[:8]


def read_key_file(path: str | Path) -> bytes | None:
    """A key from a file (hex), or None when it is missing or not a key. Used by the verifier; the key is never shown."""
    try:
        key = bytes.fromhex(Path(path).read_text(encoding="ascii").strip())
    except (OSError, ValueError):
        return None
    return key if len(key) >= 16 else None


def verify_lines(lines: list[str], keys: dict[str, bytes]) -> dict[str, object]:
    """Checks the signature of every line. `keys` maps a key id to a key. Returns the count of good lines and the 1-based numbers of the others."""
    ok = 0
    bad: list[int] = []
    unsigned: list[int] = []
    unknown_key: list[int] = []
    malformed: list[int] = []
    reasons: dict[str, int] = {}
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except ValueError:
            item = None
        if not isinstance(item, dict):
            malformed.append(number)
            continue
        sig, kid = item.get("sig"), item.get("kid")
        if not isinstance(sig, str) or not isinstance(kid, str):
            unsigned.append(number)
            reason = str(item.get("unsigned", "no_signature"))[:40]
            reasons[reason] = reasons.get(reason, 0) + 1
            continue
        key = keys.get(kid)
        if key is None:
            unknown_key.append(number)
        elif hmac.compare_digest(hmac.new(key, canonical(item), hashlib.sha256).hexdigest(), sig):
            ok += 1
        else:
            bad.append(number)
    return {"ok": ok, "bad": bad, "unsigned": unsigned, "unknownKey": unknown_key, "malformed": malformed, "unsignedReasons": reasons}


class AuditLog:
    def __init__(self, config: AuditConfig) -> None:
        self.config = config
        self.path = Path(config.file)
        self._lock = threading.Lock()
        self._salt: bytes | None = None
        self._sign_key: bytes | None = None
        self._sign_problem = ""  # why the records are not signed right now ("" when they are, or when signing is off)
        self.unsigned_records = 0
        self.write_errors = 0
        self.writable = True  # False after a failed write, True again after the next one that works
        if config.enabled and config.transcript_hmac:
            self._signing_key()  # made now if it is missing, so /health tells the truth from the start

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

    def hmac_path(self) -> Path:
        return Path(self.config.hmac_key_file) if self.config.hmac_key_file else self.path.with_name(self.path.name + ".hmac.key")

    def _signing_key(self) -> bytes | None:
        """The key that signs the records, or None (and `_sign_problem` says why). A missing file is created with 0600; a damaged one is left alone."""
        if self._sign_key is not None:
            return self._sign_key
        keyfile = self.hmac_path()
        try:
            text = keyfile.read_text(encoding="ascii").strip()
        except (FileNotFoundError, NotADirectoryError):
            try:
                keyfile.parent.mkdir(parents=True, exist_ok=True)
                key = secrets.token_bytes(32)
                try:
                    descriptor = os.open(keyfile, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                except FileExistsError:  # another process made it first: its key is read on the next record
                    self._sign_problem = "key_unavailable"
                    return None
                with os.fdopen(descriptor, "w", encoding="ascii") as stream:
                    stream.write(key.hex())
            except OSError:
                self._sign_problem = "key_cannot_be_created"
                return None
            self._sign_key = key
            self._sign_problem = ""
            return key
        except (OSError, UnicodeDecodeError):
            self._sign_problem = "key_unreadable"
            return None
        try:
            key = bytes.fromhex(text)
        except ValueError:
            key = b""
        if len(key) < 16:
            self._sign_problem = "key_invalid"
            return None
        self._sign_key = key
        self._sign_problem = ""
        return key

    def _sign(self, record: dict[str, object]) -> dict[str, object]:
        """The record with its signature, or with `unsigned` and the reason when the key cannot be had. Does nothing when the switch is off."""
        if not self.config.transcript_hmac:
            return record
        key = self._signing_key()
        if key is None:
            self.unsigned_records += 1
            return {**record, "unsigned": self._sign_problem or "key_unavailable"}
        signed = {**record, "kid": key_id(key)}
        return {**signed, "sig": hmac.new(key, canonical(signed), hashlib.sha256).hexdigest()}

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
            with self._lock:
                line = (json.dumps(self._sign(record), separators=(",", ":")) + "\n").encode("utf-8")
                self.path.parent.mkdir(parents=True, exist_ok=True)
                if self.path.exists() and self.path.stat().st_size + len(line) > self.config.max_bytes:
                    self._rotate()
                flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
                descriptor = os.open(self.path, flags, 0o600)
                with os.fdopen(descriptor, "ab") as stream:
                    stream.write(line)
            self.writable = True
            return True
        except Exception:  # noqa: BLE001 - whatever goes wrong, the voice command (a stop above all) must go on
            self.write_errors += 1
            self.writable = False
            return False

    def status(self) -> dict[str, object]:
        """What the service says about its own audit log (no path, no content): switched on or off, whether the last write worked, errors so far."""
        signing = "off" if not (self.config.enabled and self.config.transcript_hmac) else (self._sign_problem or "ok")
        return {
            "enabled": self.config.enabled,
            "writable": self.writable if self.config.enabled else None,
            "writeErrors": self.write_errors,
            "signing": signing,
            "unsignedRecords": self.unsigned_records,
        }

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


def main(argv: list[str] | None = None) -> int:
    """Check the signatures of audit files: python -m hydra_umc_voice_ui.audit [FILE...] [--config voice-ui.json] [--key-file KEY]...

    Without FILE the log of the configuration and its rotated copies are read. Exit code 0 when every line is signed and good, 1 when a line was
    changed, forged, damaged or signed with a key that was not given, 2 when nothing is wrong but some lines are unsigned (the report says why).
    The key is never printed.
    """
    import argparse

    from .voice_config import CONFIG_ENV, load_voice_config

    parser = argparse.ArgumentParser(prog="python -m hydra_umc_voice_ui.audit", description="Check the signatures of the voice audit log.")
    parser.add_argument("files", nargs="*", help="audit files (default: the file of the configuration and its rotated copies)")
    parser.add_argument("--config", default=None, help="configuration file (default: HYDRA_UMC_VOICE_UI_CONFIG or /etc/hydra-umc/voice-ui.json)")
    parser.add_argument("--key-file", action="append", default=[], help="a key file to try; repeat it for keys that were replaced")
    args = parser.parse_args(argv)
    audit = load_voice_config({CONFIG_ENV: args.config} if args.config else None).audit
    key_paths = [*args.key_file, str(AuditLog(audit).hmac_path())]
    keys: dict[str, bytes] = {}
    for path in key_paths:
        key = read_key_file(path)
        if key is not None:
            keys[key_id(key)] = key
    files = [Path(f) for f in args.files]
    if not files:
        base = Path(audit.file)
        files = [base.with_name(f"{base.name}.{n}") for n in range(audit.max_files - 1, 0, -1)] + [base]
    worst = 0
    for file in files:
        try:
            lines = file.read_text(encoding="utf-8").splitlines()
        except OSError:
            if args.files:
                print(f"{file}: cannot be read")
                worst = 1
            continue
        report = verify_lines(lines, keys)
        print(f"{file}: ok={report['ok']} bad={report['bad']} unknownKey={report['unknownKey']} malformed={report['malformed']} "
              f"unsigned={len(report['unsigned'])} {report['unsignedReasons']}")  # type: ignore[arg-type]
        if report["bad"] or report["unknownKey"] or report["malformed"]:
            worst = 1
        elif report["unsigned"]:
            worst = max(worst, 2)
    if not keys:
        print("no key could be read: nothing can be verified")
        worst = 1
    return worst


if __name__ == "__main__":
    sys.exit(main())
