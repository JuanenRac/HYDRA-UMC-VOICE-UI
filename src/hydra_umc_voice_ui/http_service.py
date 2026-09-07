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
from .gateway import VoiceTurn, VoiceTurnValidationError, process_voice_turn

MAX_BODY_BYTES: Final = 4 * 1024


def is_loopback_host(host: str) -> bool:
    return host in {"127.0.0.1", "::1", "localhost"}


class VoiceGatewayServer(ThreadingHTTPServer):
    """HTTP server carrying immutable runtime security configuration."""

    def __init__(self, address: tuple[str, int], token: str | None) -> None:
        super().__init__(address, VoiceGatewayHandler)
        self.token = token


class VoiceGatewayHandler(BaseHTTPRequestHandler):
    server: VoiceGatewayServer

    def log_message(self, format: str, *args: object) -> None:
        # Keep normal request logging concise and do not log Authorization.
        print("[voice-gateway] " + (format % args))

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
            "authRequired": bool(self.server.token),
        })

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API name
        if self.path != "/v1/voice/turn":
            self._write_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
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
            reply = process_voice_turn(VoiceTurn.from_payload(payload))
        except (UnicodeDecodeError, json.JSONDecodeError, VoiceTurnValidationError) as error:
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
            return
        self._write_json(HTTPStatus.OK, reply.to_payload())


def create_voice_gateway(host: str, port: int, token: str | None = None) -> VoiceGatewayServer:
    """Create a gateway, enforcing a bearer token for non-loopback binds."""
    resolved_token = token if token is not None else os.environ.get("HYDRA_UMC_VOICE_UI_TOKEN")
    if not is_loopback_host(host) and not resolved_token:
        raise ValueError("HYDRA_UMC_VOICE_UI_TOKEN is required when binding beyond loopback")
    return VoiceGatewayServer((host, port), resolved_token)
