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

from . import __version__
from .gateway import VoiceTurn, VoiceTurnValidationError, confirm_pending_action, process_voice_turn
from .ratelimit import DEFAULT_REQUESTS_PER_MINUTE, ClientRateLimiter

MAX_BODY_BYTES: Final = 4 * 1024


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

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API name
        if self.path != "/health":
            self._write_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        self._write_json(HTTPStatus.OK, {
            "product": "HYDRA-UMC-VOICE-UI",
            "version": __version__,
            "voiceTurnEndpoint": "/v1/voice/turn",
            "voiceConfirmEndpoint": "/v1/voice/confirm",
            "authRequired": bool(self.server.token),
        })

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API name
        if self.path not in ("/v1/voice/turn", "/v1/voice/confirm"):
            self._write_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        allowed, wait = self.server.limiter.allow(self.client_address[0])
        if not allowed:
            self._write_json(HTTPStatus.TOO_MANY_REQUESTS, {"error": "too many requests from this address", "retryAfterSeconds": round(wait, 1)})
            return
        if not self._is_authorized():
            self._write_json(HTTPStatus.UNAUTHORIZED, {"error": "valid bearer token required"})
            return
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": "valid Content-Length required"})
            return
        if not 0 < length <= MAX_BODY_BYTES:
            self._write_json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": f"body must contain 1-{MAX_BODY_BYTES} bytes"})
            return
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
            return

        if self.path == "/v1/voice/confirm":
            # a real, separate result from the original turn's own
            # reply - never re-actuates anything, only ever reports
            # whether a specific pending confirmation is still genuine
            # and within its own real validity window.
            token = payload.get("confirmationToken") if isinstance(payload, dict) else None
            result = confirm_pending_action(token)
            self._write_json(HTTPStatus.OK, result.to_payload())
            return

        try:
            reply = process_voice_turn(VoiceTurn.from_payload(payload))
        except VoiceTurnValidationError as error:
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
            return
        self._write_json(HTTPStatus.OK, reply.to_payload())


def create_voice_gateway(host: str, port: int, token: str | None = None) -> VoiceGatewayServer:
    """Create a gateway, enforcing a bearer token for non-loopback binds."""
    resolved_token = token if token is not None else os.environ.get("HYDRA_UMC_VOICE_UI_TOKEN")
    if not is_loopback_host(host) and not resolved_token:
        raise ValueError("HYDRA_UMC_VOICE_UI_TOKEN is required when binding beyond loopback")
    return VoiceGatewayServer((host, port), resolved_token)
