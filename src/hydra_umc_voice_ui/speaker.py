# =============================================================================
# HYDRA-UMC-VOICE-UI - src/hydra_umc_voice_ui/speaker.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Who is speaking: matching a voice vector against the operators who enrolled one.

This is optional (`speaker.enabled`, off by default) and local. The service never receives audio for it: the device (or the speech stack of
the CM5) turns the voice into a vector of numbers and sends the vector with the turn; here it is only compared with the vectors of the
enrolled operators, by cosine similarity. The vectors live in one file on this machine, written for the owner only, and never leave it: no
reply, log, metric or audit record contains a vector.

An operator is recognised when the best match reaches `threshold` and beats the second best by `margin`, so two similar voices are not told
apart by luck. A person is forgotten with `forget`, which removes the vector from the file at once.
"""
from __future__ import annotations

import json
import math
import os
import re
import threading
from pathlib import Path

ALIAS_PATTERN = re.compile(r"^[A-Za-z0-9_.@:+-]{1,128}$")
MIN_DIMENSIONS = 8
MAX_DIMENSIONS = 512
MAX_STORE_BYTES = 4 * 1024 * 1024


class SpeakerError(ValueError):
    """The vector or the alias is not acceptable, or the store cannot take another operator."""


def clean_vector(raw: object) -> list[float]:
    """A voice vector from a decoded request: 8 to 512 finite numbers, not all zero. Raises SpeakerError otherwise."""
    if not isinstance(raw, list) or not MIN_DIMENSIONS <= len(raw) <= MAX_DIMENSIONS:
        raise SpeakerError(f"the voice vector must be a list of {MIN_DIMENSIONS} to {MAX_DIMENSIONS} numbers")
    values: list[float] = []
    for item in raw:
        if isinstance(item, bool) or not isinstance(item, (int, float)) or not math.isfinite(item):
            raise SpeakerError("the voice vector must hold finite numbers only")
        values.append(float(item))
    norm = math.sqrt(sum(v * v for v in values))
    if norm == 0.0:
        raise SpeakerError("the voice vector must not be all zero")
    return [v / norm for v in values]


def _cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


class SpeakerStore:
    """The enrolled operators of this machine, kept in one JSON file."""

    def __init__(self, path: str | Path, *, threshold: float = 0.85, margin: float = 0.05, max_speakers: int = 16) -> None:
        self.path = Path(path)
        self.threshold = threshold
        self.margin = margin
        self.max_speakers = max_speakers
        self._lock = threading.Lock()

    def _read(self) -> dict[str, list[float]]:
        try:
            if self.path.stat().st_size > MAX_STORE_BYTES:
                return {}
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        speakers = data.get("speakers") if isinstance(data, dict) else None
        if not isinstance(speakers, dict):
            return {}
        clean: dict[str, list[float]] = {}
        for alias, vector in speakers.items():
            try:
                if ALIAS_PATTERN.fullmatch(alias):
                    clean[alias] = clean_vector(vector)
            except SpeakerError:
                continue  # an entry that is not a valid vector is not an operator
        return clean

    def _write(self, speakers: dict[str, list[float]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(self.path.name + ".tmp")
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        descriptor = os.open(temporary, flags, 0o600)  # owner only where the system has permissions
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump({"version": 1, "speakers": speakers}, stream, separators=(",", ":"))
        os.replace(temporary, self.path)

    def aliases(self) -> list[str]:
        with self._lock:
            return sorted(self._read())

    def enroll(self, alias: str, vector: object) -> None:
        """Adds an operator, or replaces the vector of one that is already enrolled."""
        if not isinstance(alias, str) or not ALIAS_PATTERN.fullmatch(alias):
            raise SpeakerError("the alias must contain 1-128 letters, digits or . _ @ : + -")
        cleaned = clean_vector(vector)
        with self._lock:
            speakers = self._read()
            if alias not in speakers and len(speakers) >= self.max_speakers:
                raise SpeakerError(f"{self.max_speakers} operators are enrolled already; forget one first")
            if speakers and len(next(iter(speakers.values()))) != len(cleaned):
                raise SpeakerError("the vector has another number of dimensions than the enrolled ones")
            speakers[alias] = cleaned
            self._write(speakers)

    def forget(self, alias: str) -> bool:
        """Removes an operator and their vector from the file. False when that alias was not enrolled."""
        with self._lock:
            speakers = self._read()
            if alias not in speakers:
                return False
            del speakers[alias]
            self._write(speakers)
            return True

    def identify(self, vector: object) -> str | None:
        """The alias of the enrolled operator this voice vector belongs to, or None (nobody enrolled, a vector that does not fit, a weak
        match, or two operators too close to tell apart)."""
        try:
            probe = clean_vector(vector)
        except SpeakerError:
            return None
        with self._lock:
            speakers = self._read()
        scores = sorted(
            ((_cosine(probe, enrolled), alias) for alias, enrolled in speakers.items() if len(enrolled) == len(probe)),
            reverse=True,
        )
        if not scores or scores[0][0] < self.threshold:
            return None
        if len(scores) > 1 and scores[0][0] - scores[1][0] < self.margin:
            return None
        return scores[0][1]
