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
"""
from __future__ import annotations

from dataclasses import dataclass
import re

from .intent import INTENT_GO_HOME, INTENT_START_MISSION, INTENT_STATUS, INTENT_STOP, Intent, classify_intent

MAX_TRANSCRIPT_LENGTH = 500
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class VoiceTurnValidationError(ValueError):
    """Raised when untrusted Watch input fails the public wire contract."""


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
        return payload


def process_voice_turn(turn: VoiceTurn) -> AssistantReply:
    """Parse one Watch request and return an honest, non-actuating reply.

    Uses the ambiguity-aware `classify_intent()` rather than the legacy
    first-match-wins `parse_intent()`: a real transcript that genuinely
    matches more than one known command is a real safety-relevant
    ambiguity - it is never silently resolved to whichever rule happens
    to be declared first, since guessing wrong on a motion command is
    exactly the failure mode this gateway exists to prevent.
    """
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
    )
