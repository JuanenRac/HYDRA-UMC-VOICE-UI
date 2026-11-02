# =============================================================================
# HYDRA-UMC-VOICE-UI - Local authenticated Watch voice HTTP service
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Small stdlib HTTP boundary for the Watch-to-cognitive voice path."""
from __future__ import annotations

import hmac
import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Final
from urllib.parse import parse_qs, urlparse

from . import __version__
from .alerts import AlertError, AlertSpeaker
from .audit import AuditLog
from .gateway import AssistantReply, VoiceTurn, VoiceTurnValidationError, confirm_pending_action, process_voice_turn
from .metrics import Metrics
from .ratelimit import DEFAULT_REQUESTS_PER_MINUTE, ClientRateLimiter
from .speaker import SpeakerError, SpeakerStore
from .voice_config import load_voice_config

# room for a voice vector (up to 512 numbers) next to the text of a turn
MAX_BODY_BYTES: Final = 16 * 1024


def is_loopback_host(host: str) -> bool:
    return host in {"127.0.0.1", "::1", "localhost"}


class VoiceGatewayServer(ThreadingHTTPServer):
    """HTTP server carrying immutable runtime security configuration."""

    def __init__(self, address: tuple[str, int], token: str | None, requests_per_minute: int | None = None) -> None:
        super().__init__(address, VoiceGatewayHandler)
        self.token = token
        if requests_per_minute is None:
            requests_per_minute = _configured_rate()
        self.limiter = ClientRateLimiter(requests_per_minute)
        self.metrics = Metrics()
        # the optional voice features read their settings from the configuration file (voice_config.py); all of them are off by default
        config = load_voice_config()
        self.audit = AuditLog(config.audit)
        self.alerts = AlertSpeaker(config.alerts)
        self.config_problems = config.problems

    def speaker_store(self) -> SpeakerStore:
        speaker = load_voice_config().speaker
        return SpeakerStore(speaker.store_file, threshold=speaker.threshold, margin=speaker.margin, max_speakers=speaker.max_speakers)


def audit_outcome(reply: AssistantReply) -> str:
    """The short code the audit log keeps for what a turn came to."""
    if reply.requires_confirmation:
        return "confirmation_required"
    code = reply.message_code or ""
    return {"status": "acknowledged", "query_answer": "query_answered"}.get(code, code)


def _configured_rate() -> int:
    """HYDRA_UMC_VOICE_UI_RATE_PER_MINUTE: requests one client address may make a minute; 0 turns the limit off."""
    raw = os.environ.get("HYDRA_UMC_VOICE_UI_RATE_PER_MINUTE", "")
    if not raw:
        return DEFAULT_REQUESTS_PER_MINUTE
    try:
        value = int(raw)
    except ValueError as error:
        raise ValueError("HYDRA_UMC_VOICE_UI_RATE_PER_MINUTE must be a whole number (0 turns the limit off)") from error
    if value < 0:
        raise ValueError("HYDRA_UMC_VOICE_UI_RATE_PER_MINUTE must not be negative")
    return value


class VoiceGatewayHandler(BaseHTTPRequestHandler):
    server: VoiceGatewayServer

    # Seconds a client may stay silent on its connection before the server
    # drops it, so a client that connects and sends nothing cannot hold a
    # handler thread forever. Socket I/O only.
    timeout = 15.0

    def log_message(self, format: str, *args: object) -> None:
        # Quiet by default, like the rest of the family: neither the transcript
        # nor the Authorization header may end up in a log.
        pass

    def _write_json(self, status: HTTPStatus, payload: dict[str, object]) -> None:
        raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def _is_authorized(self) -> bool:
        expected = self.server.token
        if not expected:
            return True
        received = self.headers.get("Authorization", "")
        return hmac.compare_digest(received, f"Bearer {expected}")

    def _write_text(self, status: HTTPStatus, text: str) -> None:
        raw = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API name
        if self.path == "/metrics":
            # the counters in the text format of Prometheus: behind the token when there is one (/health stays open for the service registry)
            if not self._is_authorized():
                self.server.metrics.refused("unauthorized")
                self._write_json(HTTPStatus.UNAUTHORIZED, {"error": "valid bearer token required"})
                return
            self._write_text(HTTPStatus.OK, self.server.metrics.render(self.server.audit.status()))
            return
        if urlparse(self.path).path == "/v1/voice/audit":
            # the most recent audit records, for the server to collect; behind the token, and refused when there is no token to check
            if not self.server.token:
                self._write_json(HTTPStatus.FORBIDDEN, {"error": "reading the audit log needs a bearer token"})
                return
            if not self._is_authorized():
                self.server.metrics.refused("unauthorized")
                self._write_json(HTTPStatus.UNAUTHORIZED, {"error": "valid bearer token required"})
                return
            if not self.server.audit.config.enabled:
                self._write_json(HTTPStatus.CONFLICT, {"error": "the audit log is switched off (audit.enabled)"})
                return
            try:
                limit = int(parse_qs(urlparse(self.path).query).get("limit", ["50"])[0])
            except ValueError:
                limit = 50
            self._write_json(HTTPStatus.OK, {"records": self.server.audit.tail(limit)})
            return
        if self.path != "/health":
            self._write_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        self._write_json(HTTPStatus.OK, {
            "product": "HYDRA-UMC-VOICE-UI",
            "version": __version__,
            "voiceTurnEndpoint": "/v1/voice/turn",
            "voiceConfirmEndpoint": "/v1/voice/confirm",
            "authRequired": bool(self.server.token),
            "audit": self.server.audit.status(),
        })

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API name
        if self.path not in ("/v1/voice/turn", "/v1/voice/confirm", "/v1/voice/alert", "/v1/voice/speaker/enroll", "/v1/voice/speaker/forget"):
            self._write_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        allowed, wait = self.server.limiter.allow(self.client_address[0])
        if not allowed:
            self.server.metrics.refused("rate_limited")
            self._write_json(HTTPStatus.TOO_MANY_REQUESTS, {"error": "too many requests from this address", "retryAfterSeconds": round(wait, 1)})
            return
        if not self._is_authorized():
            self.server.metrics.refused("unauthorized")
            self._write_json(HTTPStatus.UNAUTHORIZED, {"error": "valid bearer token required"})
            return
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            self.server.metrics.refused("bad_request")
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": "valid Content-Length required"})
            return
        if not 0 < length <= MAX_BODY_BYTES:
            self.server.metrics.refused("too_large")
            self._write_json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": f"body must contain 1-{MAX_BODY_BYTES} bytes"})
            return
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            self.server.metrics.refused("bad_request")
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
            return

        if self.path == "/v1/voice/alert":
            try:
                alert = self.server.alerts.compose(payload)
            except AlertError as error:
                self.server.metrics.refused("bad_request")
                self._write_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
                return
            self._write_json(HTTPStatus.OK, alert.to_payload())
            return

        if self.path.startswith("/v1/voice/speaker/"):
            self._handle_speaker(payload)
            return

        if self.path == "/v1/voice/confirm":
            # a real, separate result from the original turn's own
            # reply - never re-actuates anything, only ever reports
            # whether a specific pending confirmation is still genuine
            # and within its own real validity window.
            token = payload.get("confirmationToken") if isinstance(payload, dict) else None
            asking = payload.get("subject") if isinstance(payload, dict) else None
            result = confirm_pending_action(token, subject=asking)
            self.server.metrics.confirmation()
            self.server.audit.record(
                "confirm", request_id=result.request_id, intent=result.intent_name, outcome=result.status,
                subject=result.subject or (asking if isinstance(asking, str) else ""), confirmation=result.status,
            )
            self._write_json(HTTPStatus.OK, result.to_payload())
            return

        try:
            reply = process_voice_turn(VoiceTurn.from_payload(payload))
        except VoiceTurnValidationError as error:
            self.server.metrics.refused("bad_request")
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
            return
        self.server.metrics.turn(reply.intent.name if reply.intent else None, needs_confirmation=reply.requires_confirmation)
        subject = payload.get("subject") if isinstance(payload, dict) else ""
        self.server.audit.record(
            "turn", request_id=reply.request_id, intent=reply.intent.name if reply.intent else None, outcome=audit_outcome(reply),
            subject=subject if isinstance(subject, str) else "", confirmation="required" if reply.requires_confirmation else "none",
            speaker=reply.speaker or "off",
        )
        self._write_json(HTTPStatus.OK, reply.to_payload())

    def _handle_speaker(self, payload: object) -> None:
        """Enrolling and forgetting an operator's voice vector: only with speaker identification on and a bearer token configured."""
        config = load_voice_config()
        if not config.speaker.enabled:
            self._write_json(HTTPStatus.CONFLICT, {"error": "speaker identification is switched off (speaker.enabled)"})
            return
        if not self.server.token:
            self._write_json(HTTPStatus.FORBIDDEN, {"error": "enrolling or forgetting a voice needs a bearer token"})
            return
        if not isinstance(payload, dict):
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": "request body must be a JSON object"})
            return
        store = self.server.speaker_store()
        alias = payload.get("subject")
        try:
            if self.path.endswith("/enroll"):
                store.enroll(alias, payload.get("vector"))  # type: ignore[arg-type]
                self._write_json(HTTPStatus.OK, {"enrolled": True, "operators": len(store.aliases())})
            else:
                if not isinstance(alias, str):
                    raise SpeakerError("subject must be text")
                self._write_json(HTTPStatus.OK, {"forgotten": store.forget(alias), "operators": len(store.aliases())})
        except SpeakerError as error:
            self.server.metrics.refused("bad_request")
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
        except OSError:
            self._write_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "the voice store could not be written"})


def create_voice_gateway(host: str, port: int, token: str | None = None) -> VoiceGatewayServer:
    """Create a gateway, enforcing a bearer token for non-loopback binds."""
    resolved_token = token if token is not None else os.environ.get("HYDRA_UMC_VOICE_UI_TOKEN")
    if not is_loopback_host(host) and not resolved_token:
        raise ValueError("HYDRA_UMC_VOICE_UI_TOKEN is required when binding beyond loopback")
    return VoiceGatewayServer((host, port), resolved_token)
