# =============================================================================
# HYDRA-UMC-VOICE-UI - Safe Watch voice-turn gateway contract
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Bounded text-to-intent gateway shared by the Watch cognitive flow.

This v0 endpoint deliberately accepts already-recognized text, not raw audio,
and never sends a physical command. It is a real, deterministic hand-off from
the watch contract to the existing intent parser; an authenticated Server /
Semantic Planner integration can replace the response policy without changing
the wire shape.

("Diálogo de confirmación con vigencia y resultado separado"): a real
confirmation gains its own bounded validity window (`PendingConfirmation`),
not just a boolean `requires_confirmation` flag. This gateway stays
deliberately stateless (no server-side session store) - `PendingConfirmation`
is instead a self-describing, checksummed token the client (Watch) holds
onto and echoes back on the confirming turn, exactly the same "the client
carries correlation" shape `to_payload()` already uses elsewhere. Solves
this project's own literal acceptance test: a late/replayed confirmation response
can only ever confirm the EXACT action (intent + entities) it was issued
for, at the moment it was issued for it - never "whatever is currently
pending" (there is no such shared, mutable state to accidentally target),
and never past its own real expiry.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
import re

from .intent import INTENT_GO_HOME, INTENT_START_MISSION, INTENT_STATUS, INTENT_STOP, Intent, classify_intent

MAX_TRANSCRIPT_LENGTH = 500
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

# how long a real pending confirmation stays valid after being
# issued. Long enough for a human to actually hear the prompt and
# respond, short enough that a stale/replayed confirmation response
# arriving much later can never authorize a now-outdated action.
CONFIRMATION_VALIDITY_SECONDS = 30.0


class VoiceTurnValidationError(ValueError):
    """Raised when untrusted Watch input fails the public wire contract."""


class ConfirmationError(ValueError):
    """raised when a confirmation token is malformed, tampered with,
    or otherwise cannot be trusted enough to even check its expiry."""


@dataclass(frozen=True)
class PendingConfirmation:
    """this project's own real, bounded confirmation record. `entities` is stored
    as a sorted tuple of pairs (not a dict) so equality/encoding stay
    deterministic regardless of the source dict's own insertion order.
    """

    request_id: str
    intent_name: str
    entities: tuple[tuple[str, str], ...]
    issued_at: datetime

    @classmethod
    def issue(cls, request_id: str, intent: Intent, now: datetime) -> "PendingConfirmation":
        return cls(
            request_id=request_id,
            intent_name=intent.name,
            entities=tuple(sorted(intent.entities.items())),
            issued_at=now,
        )

    def is_expired(self, now: datetime) -> bool:
        """Mirrors this ecosystem's own established freshness convention
        (HYDRA-UMC-SAFETY-ZONES' calibration.py/observation.py): a
        confirmation timestamped in the future (clock skew) is treated
        as untrustworthy too, never as extra-fresh."""
        age = (now - self.issued_at).total_seconds()
        return age < 0 or age > CONFIRMATION_VALIDITY_SECONDS

    def age_seconds(self, now: datetime) -> float:
        return (now - self.issued_at).total_seconds()

    def encode(self) -> str:
        """A self-describing, checksummed token - not a secret, and not
        meant to defend against a hostile holder (transport-level bearer
        auth already covers that, see http_service.py); its only real
        job is tamper-evidence against ACCIDENTAL corruption and a
        reliable way to decode a specific pending action back out with
        no server-side session store to consult."""
        payload = {
            "requestId": self.request_id,
            "intent": self.intent_name,
            "entities": [list(pair) for pair in self.entities],
            "issuedAtUtc": self.issued_at.astimezone(timezone.utc).isoformat(),
        }
        raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        body = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
        checksum = hashlib.sha256(raw).hexdigest()[:16]
        return f"{body}.{checksum}"

    @classmethod
    def decode(cls, token: str) -> "PendingConfirmation":
        if not isinstance(token, str) or "." not in token:
            raise ConfirmationError("malformed confirmation token")
        body, _, checksum = token.rpartition(".")
        try:
            padding = "=" * (-len(body) % 4)
            raw = base64.urlsafe_b64decode(body + padding)
        except (binascii.Error, ValueError) as exc:
            raise ConfirmationError("malformed confirmation token") from exc
        if hashlib.sha256(raw).hexdigest()[:16] != checksum:
            raise ConfirmationError("confirmation token failed its own integrity check")
        try:
            decoded = json.loads(raw)
            return cls(
                request_id=decoded["requestId"],
                intent_name=decoded["intent"],
                entities=tuple((pair[0], pair[1]) for pair in decoded["entities"]),
                issued_at=datetime.fromisoformat(decoded["issuedAtUtc"]),
            )
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            raise ConfirmationError("malformed confirmation token") from exc


@dataclass(frozen=True)
class VoiceTurn:
    request_id: str
    transcript: str
    locale: str

    @classmethod
    def from_payload(cls, payload: object) -> "VoiceTurn":
        if not isinstance(payload, dict):
            raise VoiceTurnValidationError("request body must be a JSON object")
        if payload.get("type") not in (None, "voice_turn"):
            raise VoiceTurnValidationError("request type must be voice_turn")
        request_id = payload.get("requestId")
        transcript = payload.get("transcript")
        locale = payload.get("locale")
        if not isinstance(request_id, str) or not REQUEST_ID_PATTERN.fullmatch(request_id):
            raise VoiceTurnValidationError("requestId must contain 1-64 letters, digits, _ or -")
        if not isinstance(transcript, str) or not transcript.strip() or len(transcript) > MAX_TRANSCRIPT_LENGTH:
            raise VoiceTurnValidationError(f"transcript must contain 1-{MAX_TRANSCRIPT_LENGTH} characters")
        if not isinstance(locale, str) or not 2 <= len(locale) <= 35:
            raise VoiceTurnValidationError("locale must contain 2-35 characters")
        return cls(request_id=request_id, transcript=transcript.strip(), locale=locale)


@dataclass(frozen=True)
class AssistantReply:
    request_id: str
    text: str
    level: str
    speak: bool
    requires_confirmation: bool
    intent: Intent | None
    # only ever set alongside requires_confirmation=True - the real,
    # bounded pending confirmation the Watch client must echo back
    # (as `confirmationToken`) on the turn that confirms this specific
    # action.
    pending_confirmation: PendingConfirmation | None = None

    @property
    def visual_state(self) -> str:
        """Return a bounded Watch UI hint; it is never a robot-state claim."""

        if self.level == "WARNING":
            return "warning"
        if self.intent is None:
            return "clarification"
        if self.requires_confirmation:
            return "confirmation-required"
        return "acknowledged"

    def to_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "type": "assistant_reply",
            "requestId": self.request_id,
            "text": self.text,
            "level": self.level,
            "speak": self.speak,
            "requiresConfirmation": self.requires_confirmation,
            "visualState": self.visual_state,
        }
        if self.intent is not None:
            payload["intent"] = {"name": self.intent.name, "entities": self.intent.entities}
        if self.pending_confirmation is not None:
            payload["confirmationToken"] = self.pending_confirmation.encode()
            payload["confirmationValiditySeconds"] = CONFIRMATION_VALIDITY_SECONDS
        return payload


def process_voice_turn(turn: VoiceTurn, *, now: datetime | None = None) -> AssistantReply:
    """Parse one Watch request and return an honest, non-actuating reply.

    Uses the ambiguity-aware `classify_intent()` rather than the legacy
    first-match-wins `parse_intent()`: a real transcript that genuinely
    matches more than one known command is a real safety-relevant
    ambiguity - it is never silently resolved to whichever rule happens
    to be declared first, since guessing wrong on a motion command is
    exactly the failure mode this gateway exists to prevent.

    `now` defaults to the real current UTC time - overridable so a test
    can issue a `PendingConfirmation` at a known instant.
    """
    now = now if now is not None else datetime.now(timezone.utc)
    classification = classify_intent(turn.transcript)
    if classification.is_no_match:
        return AssistantReply(
            request_id=turn.request_id,
            text="I did not understand that safely. Ask for status, start a mission, stop, or go home.",
            level="ATTENTION",
            speak=True,
            requires_confirmation=False,
            intent=None,
        )
    if classification.is_ambiguous:
        names = ", ".join(sorted({match.name for match in classification.matches}))
        return AssistantReply(
            request_id=turn.request_id,
            text=f"That request matched more than one action ({names}). Please rephrase it more specifically.",
            level="ATTENTION",
            speak=True,
            requires_confirmation=False,
            intent=None,
        )
    intent = classification.matches[0]

    if intent.name == INTENT_STATUS:
        robot = intent.entities.get("robot_id")
        target = f" for robot {robot}" if robot else ""
        return AssistantReply(
            request_id=turn.request_id,
            text=f"Status request{target} understood. Live telemetry will be supplied by the authenticated HYDRA-UMC gateway.",
            level="ATTENTION",
            speak=True,
            requires_confirmation=False,
            intent=intent,
        )

    if intent.name == INTENT_START_MISSION:
        mission = intent.entities.get("mission_id", "the requested mission")
        text = f"Start request for {mission} understood. No motion is executed until an authenticated primary control confirms it."
    elif intent.name == INTENT_GO_HOME:
        text = "Go-home request understood. No motion is executed until an authenticated primary control confirms it."
    elif intent.name == INTENT_STOP:
        text = "Stop request understood. Use the physical E-STOP or authenticated primary control for immediate safety action."
    else:  # Defensive: parse_intent may gain a new rule before this policy does.
        text = "The request was recognized but needs an updated safety policy before it can be handled."

    return AssistantReply(
        request_id=turn.request_id,
        text=text,
        level="WARNING" if intent.name == INTENT_STOP else "ATTENTION",
        speak=True,
        requires_confirmation=True,
        intent=intent,
        pending_confirmation=PendingConfirmation.issue(turn.request_id, intent, now),
    )


@dataclass(frozen=True)
class ConfirmationResult:
    """this project's own literal design point: confirmation is a real, separate
    result from the original turn's own reply - never folded back into
    a generic AssistantReply with a reused vocabulary. `status` is one
    of "confirmed" / "expired" / "invalid" - never a bare boolean, so a
    caller can tell "too late" apart from "not a real token at all"."""

    status: str
    request_id: str | None
    intent_name: str | None
    entities: dict[str, str] | None
    age_seconds: float | None
    reason: str

    def to_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {"type": "confirmation_result", "status": self.status, "reason": self.reason}
        if self.request_id is not None:
            payload["requestId"] = self.request_id
        if self.intent_name is not None:
            payload["intent"] = {"name": self.intent_name, "entities": self.entities}
        if self.age_seconds is not None:
            payload["ageSeconds"] = self.age_seconds
        return payload


def confirm_pending_action(confirmation_token: object, *, now: datetime | None = None) -> ConfirmationResult:
    """this project's own literal acceptance test: a repeated/replayed confirmation
    token past its own real validity window - or one that never named a
    real pending action at all - must never confirm anything. Only a
    token that is both structurally genuine AND still within
    CONFIRMATION_VALIDITY_SECONDS of when it was issued resolves to
    "confirmed", naming exactly the intent/entities it was issued for
    (read back from the token itself, never re-guessed) - the real
    caller (SERVER/OPS-AGENT) still decides whether that matches what it
    is about to actually do.
    """
    now = now if now is not None else datetime.now(timezone.utc)
    if not isinstance(confirmation_token, str) or not confirmation_token:
        return ConfirmationResult(
            status="invalid", request_id=None, intent_name=None, entities=None, age_seconds=None,
            reason="confirmationToken must be a non-empty string",
        )
    try:
        pending = PendingConfirmation.decode(confirmation_token)
    except ConfirmationError as exc:
        return ConfirmationResult(
            status="invalid", request_id=None, intent_name=None, entities=None, age_seconds=None, reason=str(exc),
        )
    age = pending.age_seconds(now)
    if pending.is_expired(now):
        reason = (
            f"confirmation is {age:.1f}s old, exceeds the {CONFIRMATION_VALIDITY_SECONDS:.0f}s validity window - "
            "repeat the original request and confirm the new one"
            if age >= 0
            else f"confirmation is timestamped {abs(age):.1f}s in the future - refusing to trust it"
        )
        return ConfirmationResult(
            status="expired", request_id=pending.request_id, intent_name=pending.intent_name,
            entities=dict(pending.entities), age_seconds=age, reason=reason,
        )
    return ConfirmationResult(
        status="confirmed", request_id=pending.request_id, intent_name=pending.intent_name,
        entities=dict(pending.entities), age_seconds=age,
        reason=f"{pending.intent_name} confirmed {age:.1f}s after being requested - execution still requires the authenticated primary control",
    )
