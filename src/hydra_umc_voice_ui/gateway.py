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
is instead a self-describing, HMAC-signed, single-use token the client
(Watch) holds onto and echoes back on the confirming turn, exactly the same "the client
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
import hmac
import json
import os
import secrets
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import re

from .intent import (
    INTENT_GO_HOME,
    INTENT_START_MISSION,
    INTENT_STATUS,
    INTENT_STOP,
    Intent,
    classify_intent,
    normalize_text,
)

MAX_TRANSCRIPT_LENGTH = 500
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

# how long a real pending confirmation stays valid after being
# issued. Long enough for a human to actually hear the prompt and
# respond, short enough that a stale/replayed confirmation response
# arriving much later can never authorize a now-outdated action.
CONFIRMATION_VALIDITY_SECONDS = 30.0

MIN_CONFIRMATION_SECRET_LENGTH = 16
# a token is accepted once; this bounds the memory the used-token list may take (about 100 bytes each). One client
# cannot fill it: the HTTP service limits how many requests an address may make a minute (ratelimit.py).
MAX_USED_CONFIRMATIONS = 16384


STOP_CONFIRMATION_ENV = "HYDRA_UMC_VOICE_UI_STOP_REQUIRES_CONFIRMATION"


def stop_requires_confirmation_default(environ: dict[str, str] | None = None) -> bool:
    """Whether a spoken stop must be confirmed (server setting; off unless the variable is exactly "1").

    A stop is never held back by default: confirming is for starting a movement, and a command to stop that waits for a second
    answer can arrive too late. A deployment that prefers to confirm it can switch it on."""
    env = os.environ if environ is None else environ
    return env.get(STOP_CONFIRMATION_ENV, "").strip() == "1"


MIN_CONFIDENCE_ENV = "HYDRA_UMC_VOICE_UI_MIN_CONFIDENCE"
DEFAULT_MIN_CONFIDENCE = 0.6


def min_confidence_default(environ: dict[str, str] | None = None) -> float:
    """How sure the speech recognizer must be before a request that starts a movement is accepted (server setting).

    Only a turn that carries a `confidence` is checked, and a stop is never held back by it. The value is a number from
    0 to 1; 0 switches the check off. A value that is not a number from 0 to 1 is ignored and the default (0.6) stays,
    so a typing mistake never silently opens the check."""
    env = os.environ if environ is None else environ
    raw = env.get(MIN_CONFIDENCE_ENV, "").strip()
    if not raw:
        return DEFAULT_MIN_CONFIDENCE
    try:
        value = float(raw)
    except ValueError:
        return DEFAULT_MIN_CONFIDENCE
    return value if 0.0 <= value <= 1.0 else DEFAULT_MIN_CONFIDENCE


HEARD_TEXT_ENV = "HYDRA_UMC_VOICE_UI_INCLUDE_HEARD_TEXT"


def include_heard_text_default(environ: dict[str, str] | None = None) -> bool:
    """Does a reply carry the transcript it was made from (server setting; off unless the variable is exactly "1")?

    What a person said is personal data, and a reply travels through proxies and phone logs that have no need of it. By default
    the interpretation of a reply lists only the rules that matched; a deployment that wants the transcript in the reply (to show
    "I heard ...") can switch it on."""
    env = os.environ if environ is None else environ
    return env.get(HEARD_TEXT_ENV, "").strip() == "1"


SUBJECT_PATTERN = re.compile(r"^[A-Za-z0-9_.@:+-]{1,128}$")
REQUIRE_SUBJECT_ENV = "HYDRA_UMC_VOICE_UI_REQUIRE_SUBJECT"
RESULT_KEY_ENV = "HYDRA_UMC_VOICE_UI_RESULT_KEY"
MIN_RESULT_KEY_LENGTH = 16


def require_subject_default(environ: dict[str, str] | None = None) -> bool:
    """Must every turn and every confirmation name who asked (server setting; off unless the variable is exactly "1")?

    When a turn names its subject (the server that relays it passes the signed-in user) the confirmation is bound to that subject
    whatever this says. Switching this on also refuses a turn or a confirmation that names nobody."""
    env = os.environ if environ is None else environ
    return env.get(REQUIRE_SUBJECT_ENV, "").strip() == "1"


def result_key(environ: dict[str, str] | None = None) -> bytes | None:
    """The key that signs a confirmed result so the server that relays it can check it (None: results are not signed).

    HYDRA_UMC_VOICE_UI_RESULT_KEY, 16 characters or more, the same value the relaying server holds. It is not the key of the
    confirmation tokens, which never leaves this process."""
    env = os.environ if environ is None else environ
    configured = env.get(RESULT_KEY_ENV, "")
    if not configured:
        return None
    if len(configured) < MIN_RESULT_KEY_LENGTH:
        raise ValueError(f"{RESULT_KEY_ENV} must be at least {MIN_RESULT_KEY_LENGTH} characters")
    return configured.encode("utf-8")


SIGNED_FIELDS = ("type", "status", "requestId", "intent", "subject", "confirmedAtUtc", "nonce")


def sign_result(payload: dict[str, object], key: bytes) -> str:
    """HMAC-SHA256 (hex) over the canonical JSON (keys sorted, no spaces, UTF-8) of the fields in SIGNED_FIELDS.

    Only what states the confirmation is signed, never the free text of the reason or the age, so a verifier in another language
    rebuilds exactly the same bytes."""
    body = {name: payload[name] for name in SIGNED_FIELDS if name in payload}
    raw = json.dumps(body, separators=(",", ":"), sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hmac.new(key, raw, hashlib.sha256).hexdigest()


def _load_confirmation_secret() -> bytes:
    """The key that signs confirmation tokens. `HYDRA_UMC_VOICE_UI_CONFIRM_SECRET`
    pins it (so tokens survive a restart or a second worker); without it a random
    key is made per process, which is enough for a 30 second token - a restart only
    makes a pending confirmation ask to be repeated."""
    configured = os.environ.get("HYDRA_UMC_VOICE_UI_CONFIRM_SECRET", "")
    if not configured:
        return secrets.token_bytes(32)
    if len(configured) < MIN_CONFIRMATION_SECRET_LENGTH:
        raise ValueError(
            f"HYDRA_UMC_VOICE_UI_CONFIRM_SECRET must be at least {MIN_CONFIRMATION_SECRET_LENGTH} characters"
        )
    return configured.encode("utf-8")


_confirmation_secret = _load_confirmation_secret()
_used_confirmations: dict[str, datetime] = {}
_used_lock = threading.Lock()


def set_confirmation_secret(secret: bytes | None) -> None:
    """Replace the signing key (tests, or a host that manages the key itself);
    `None` makes a fresh random one. Tokens signed with the old key stop verifying."""
    global _confirmation_secret
    _confirmation_secret = secret if secret else secrets.token_bytes(32)


def _sign(raw: bytes) -> str:
    return hmac.new(_confirmation_secret, raw, hashlib.sha256).hexdigest()[:32]


def _consume_confirmation(pending: "PendingConfirmation", now: datetime) -> str | None:
    """Marks a confirmation as used. Returns why it cannot be used, or None when
    this is its first and only use."""
    with _used_lock:
        for nonce, expires in list(_used_confirmations.items()):
            if expires < now:
                del _used_confirmations[nonce]
        if pending.nonce in _used_confirmations:
            return "this confirmation was already used - repeat the original request to get a new one"
        if len(_used_confirmations) >= MAX_USED_CONFIRMATIONS:
            return "too many confirmations in flight - repeat the request in a moment"
        _used_confirmations[pending.nonce] = pending.issued_at + timedelta(seconds=CONFIRMATION_VALIDITY_SECONDS)
    return None


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
    nonce: str = field(default_factory=lambda: secrets.token_hex(8))
    # who asked (the signed-in user the relaying server named); empty when nobody was named. A confirmation with a subject
    # confirms only for that same subject.
    subject: str = ""

    @classmethod
    def issue(cls, request_id: str, intent: Intent, now: datetime, subject: str = "") -> "PendingConfirmation":
        return cls(
            request_id=request_id,
            intent_name=intent.name,
            entities=tuple(sorted(intent.entities.items())),
            issued_at=now,
            subject=subject,
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
        """A self-describing token signed with HMAC-SHA256 under a server key, so
        only this gateway can mint one: knowing the format (or having seen one)
        is not enough to forge a token for another intent. It carries a random
        nonce, and `confirm_pending_action` accepts each nonce once. Transport
        bearer auth (http_service.py) still decides who may talk to the gateway."""
        payload = {
            "nonce": self.nonce,
            "requestId": self.request_id,
            "intent": self.intent_name,
            "entities": [list(pair) for pair in self.entities],
            "issuedAtUtc": self.issued_at.astimezone(timezone.utc).isoformat(),
        }
        if self.subject:
            payload["subject"] = self.subject
        raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        body = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
        return f"{body}.{_sign(raw)}"

    @classmethod
    def decode(cls, token: str) -> "PendingConfirmation":
        if not isinstance(token, str) or "." not in token:
            raise ConfirmationError("malformed confirmation token")
        body, _, signature = token.rpartition(".")
        try:
            padding = "=" * (-len(body) % 4)
            raw = base64.urlsafe_b64decode(body + padding)
        except (binascii.Error, ValueError) as exc:
            raise ConfirmationError("malformed confirmation token") from exc
        if not hmac.compare_digest(_sign(raw), signature):
            raise ConfirmationError("confirmation token failed its own integrity check")
        try:
            decoded = json.loads(raw)
            return cls(
                request_id=decoded["requestId"],
                intent_name=decoded["intent"],
                entities=tuple((pair[0], pair[1]) for pair in decoded["entities"]),
                issued_at=datetime.fromisoformat(decoded["issuedAtUtc"]),
                nonce=str(decoded["nonce"]),
                subject=str(decoded.get("subject", "")),
            )
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            raise ConfirmationError("malformed confirmation token") from exc


@dataclass(frozen=True)
class VoiceTurn:
    request_id: str
    transcript: str
    locale: str
    subject: str = ""
    # how sure the speech recognizer was of the transcript, from 0 to 1; None when the client does not say
    confidence: float | None = None

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
        subject = payload.get("subject", "")
        if subject is None:
            subject = ""
        if not isinstance(subject, str) or (subject and not SUBJECT_PATTERN.fullmatch(subject)):
            raise VoiceTurnValidationError("subject must contain 1-128 letters, digits or . _ @ : + -")
        if not subject and require_subject_default():
            raise VoiceTurnValidationError(f"subject is required ({REQUIRE_SUBJECT_ENV} is on)")
        confidence = payload.get("confidence")
        if confidence is not None and (
            isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0.0 <= confidence <= 1.0
        ):
            raise VoiceTurnValidationError("confidence must be a number from 0 to 1")
        return cls(
            request_id=request_id,
            transcript=transcript.strip(),
            locale=locale,
            subject=subject,
            confidence=None if confidence is None else float(confidence),
        )


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
    # Set to "safety-stop" on a stop request answered without a confirmation, so a consumer can give it priority
    # and translate it into a controlled stop (it never replaces the physical E-STOP).
    priority: str | None = None
    # How the reply was reached, so what happens next can be traced back to
    # what was heard: the text as received, the text the rules actually saw
    # after normalization, and the name of every rule that matched. Present
    # on every reply produced by process_voice_turn().
    interpretation: dict[str, object] | None = None

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
        if self.priority is not None:
            payload["priority"] = self.priority
        if self.intent is not None:
            payload["intent"] = {"name": self.intent.name, "entities": self.intent.entities}
        if self.interpretation is not None:
            payload["interpretation"] = self.interpretation
        if self.pending_confirmation is not None:
            payload["confirmationToken"] = self.pending_confirmation.encode()
            payload["confirmationValiditySeconds"] = CONFIRMATION_VALIDITY_SECONDS
        return payload


def process_voice_turn(
    turn: VoiceTurn,
    *,
    now: datetime | None = None,
    stop_requires_confirmation: bool | None = None,
    include_heard_text: bool | None = None,
    min_confidence: float | None = None,
) -> AssistantReply:
    """Parse one Watch request and return an honest, non-actuating reply.

    Uses the ambiguity-aware `classify_intent()` rather than the legacy
    first-match-wins `parse_intent()`: a real transcript that genuinely
    matches more than one known command is a real safety-relevant
    ambiguity - it is never silently resolved to whichever rule happens
    to be declared first, since guessing wrong on a motion command is
    exactly the failure mode this gateway exists to prevent.

    `now` defaults to the real current UTC time - overridable so a test
    can issue a `PendingConfirmation` at a known instant.

    A stop is answered without a confirmation unless `stop_requires_confirmation`
    (default: the HYDRA_UMC_VOICE_UI_STOP_REQUIRES_CONFIRMATION server setting, off)
    says otherwise: only starting a movement has to be confirmed.

    The interpretation carries the transcript (`heardText`, `normalizedText`) only when `include_heard_text`
    (default: the HYDRA_UMC_VOICE_UI_INCLUDE_HEARD_TEXT server setting, off) says so.

    A request that starts a movement is not accepted when the turn says how sure the recognizer was (`confidence`)
    and that is below `min_confidence` (default: the HYDRA_UMC_VOICE_UI_MIN_CONFIDENCE server setting, 0.6); a stop and
    a status request are never held back by it.
    """
    if stop_requires_confirmation is None:
        stop_requires_confirmation = stop_requires_confirmation_default()
    if include_heard_text is None:
        include_heard_text = include_heard_text_default()
    if min_confidence is None:
        min_confidence = min_confidence_default()
    now = now if now is not None else datetime.now(timezone.utc)
    classification = classify_intent(turn.transcript)
    interpretation: dict[str, object] = {}
    if include_heard_text:
        interpretation["heardText"] = turn.transcript
        interpretation["normalizedText"] = normalize_text(turn.transcript)
    interpretation["matchedRules"] = sorted({match.name for match in classification.matches})
    if classification.negated:
        return AssistantReply(
            request_id=turn.request_id,
            text="That request contains a negation, so no action was taken. Please say what you want done, without \"not\" or \"never\".",
            level="ATTENTION",
            speak=True,
            requires_confirmation=False,
            intent=None,
            interpretation=interpretation,
        )
    if classification.is_no_match:
        return AssistantReply(
            request_id=turn.request_id,
            text="I did not understand that safely. Ask for status, start a mission, stop, or go home.",
            level="ATTENTION",
            speak=True,
            requires_confirmation=False,
            intent=None,
            interpretation=interpretation,
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
            interpretation=interpretation,
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
            interpretation=interpretation,
        )

    if intent.name in (INTENT_START_MISSION, INTENT_GO_HOME) and turn.confidence is not None and turn.confidence < min_confidence:
        return AssistantReply(
            request_id=turn.request_id,
            text="I am not sure I heard that correctly, so nothing was started. Please say it again.",
            level="ATTENTION",
            speak=True,
            requires_confirmation=False,
            intent=None,
            interpretation=interpretation,
        )

    if intent.name == INTENT_START_MISSION:
        mission = intent.entities.get("mission_id", "the requested mission")
        text = f"Start request for {mission} understood. No motion is executed until an authenticated primary control confirms it."
    elif intent.name == INTENT_GO_HOME:
        text = "Go-home request understood. No motion is executed until an authenticated primary control confirms it."
    elif intent.name == INTENT_STOP:
        if not stop_requires_confirmation:
            # Not held back: a stop that waits for a second answer can arrive too late.
            return AssistantReply(
                request_id=turn.request_id,
                text="Stop request understood and sent without waiting for a confirmation. The physical E-STOP remains the immediate safety action.",
                level="WARNING",
                speak=True,
                requires_confirmation=False,
                intent=intent,
                priority="safety-stop",
                interpretation=interpretation,
            )
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
        pending_confirmation=PendingConfirmation.issue(turn.request_id, intent, now, turn.subject),
        interpretation=interpretation,
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
    # Only on a confirmed result: who it was confirmed for, when, the one-use nonce of the token and, when a result key is
    # configured, the signature the relaying server checks (see sign_result).
    subject: str | None = None
    confirmed_at: str | None = None
    nonce: str | None = None

    def to_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {"type": "confirmation_result", "status": self.status, "reason": self.reason}
        if self.request_id is not None:
            payload["requestId"] = self.request_id
        if self.intent_name is not None:
            payload["intent"] = {"name": self.intent_name, "entities": self.entities}
        if self.age_seconds is not None:
            payload["ageSeconds"] = self.age_seconds
        if self.status == "confirmed":
            payload["subject"] = self.subject or ""
            if self.confirmed_at is not None:
                payload["confirmedAtUtc"] = self.confirmed_at
            if self.nonce is not None:
                payload["nonce"] = self.nonce
            key = result_key()
            if key is not None:
                payload["signature"] = sign_result(payload, key)
        return payload


def confirm_pending_action(confirmation_token: object, *, subject: object = None, now: datetime | None = None) -> ConfirmationResult:
    """this project's own literal acceptance test: a repeated/replayed confirmation
    token past its own real validity window - or one that never named a
    real pending action at all - must never confirm anything. Only a
    token that is both structurally genuine AND still within
    CONFIRMATION_VALIDITY_SECONDS of when it was issued resolves to
    "confirmed", naming exactly the intent/entities it was issued for
    (read back from the token itself, never re-guessed) - the real
    caller (SERVER/OPS-AGENT) still decides whether that matches what it
    is about to actually do.

    A token issued for a subject confirms only for that same subject (`subject` is who the relaying server says is asking, never
    something the client chose); a token that names nobody is confirmed as before unless HYDRA_UMC_VOICE_UI_REQUIRE_SUBJECT is on.
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
    asking = subject if isinstance(subject, str) else ""
    if asking and not SUBJECT_PATTERN.fullmatch(asking):
        return ConfirmationResult(
            status="invalid", request_id=None, intent_name=None, entities=None, age_seconds=None,
            reason="subject must contain 1-128 letters, digits or . _ @ : + -",
        )
    if pending.subject and asking != pending.subject:
        # not used up: the person it was issued for can still confirm it
        return ConfirmationResult(
            status="invalid", request_id=None, intent_name=None, entities=None, age_seconds=None,
            reason="this confirmation was issued for someone else" if asking else "this confirmation belongs to a subject and none was named",
        )
    if not pending.subject and require_subject_default():
        return ConfirmationResult(
            status="invalid", request_id=None, intent_name=None, entities=None, age_seconds=None,
            reason=f"this confirmation names nobody and {REQUIRE_SUBJECT_ENV} is on - repeat the request with a subject",
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
    already_used = _consume_confirmation(pending, now)
    if already_used is not None:
        return ConfirmationResult(
            status="invalid", request_id=None, intent_name=None, entities=None, age_seconds=None,
            reason=already_used,
        )
    return ConfirmationResult(
        status="confirmed", request_id=pending.request_id, intent_name=pending.intent_name,
        entities=dict(pending.entities), age_seconds=age,
        reason=f"{pending.intent_name} confirmed {age:.1f}s after being requested - execution still requires the authenticated primary control",
        subject=pending.subject, confirmed_at=now.astimezone(timezone.utc).isoformat(), nonce=pending.nonce,
    )
