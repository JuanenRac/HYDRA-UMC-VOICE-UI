# =============================================================================
# HYDRA-UMC-VOICE-UI - tests/test_http_service.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Real end-to-end HTTP tests for the authenticated Watch voice gateway
(http_service.py) - found in an ecosystem-wide software-improvements
audit: this module (bearer-token check, body-size limiting, error
mapping) had zero dedicated test coverage, unlike every other module in
this repo, and the one related CLI test only covered "port already in
use", not real request/response behavior. A real VoiceGatewayServer
(ThreadingHTTPServer) on an OS-assigned loopback port, hit with real
urllib requests - same convention as this ecosystem's other api.py test
suites.
"""
from __future__ import annotations

import json
import socket
import threading
import urllib.error
import urllib.request
from collections.abc import Iterator
from contextlib import contextmanager

import pytest

from hydra_umc_voice_ui.http_service import (
    MAX_BODY_BYTES,
    VoiceGatewayServer,
    create_voice_gateway,
    is_loopback_host,
)


@contextmanager
def running_server(token: str | None = None) -> Iterator[str]:
    server = VoiceGatewayServer(("127.0.0.1", 0), token)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def _get(url: str, headers: dict[str, str] | None = None) -> tuple[int, dict]:
    request = urllib.request.Request(url, headers=headers or {}, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=5) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def _post(url: str, body: bytes, headers: dict[str, str] | None = None) -> tuple[int, dict]:
    merged = {"Content-Type": "application/json", **(headers or {})}
    request = urllib.request.Request(url, data=body, headers=merged, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=5) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def _turn(request_id: str = "req-1", transcript: str = "status of robot 3", locale: str = "en-US") -> bytes:
    return json.dumps({"requestId": request_id, "transcript": transcript, "locale": locale}).encode("utf-8")


# ---------------------------------------------------------------------------
# is_loopback_host() / create_voice_gateway()
# ---------------------------------------------------------------------------


def test_is_loopback_host_recognizes_every_real_loopback_form() -> None:
    assert is_loopback_host("127.0.0.1")
    assert is_loopback_host("::1")
    assert is_loopback_host("localhost")
    assert not is_loopback_host("0.0.0.0")
    assert not is_loopback_host("192.168.0.203")


def test_create_voice_gateway_refuses_non_loopback_without_a_token() -> None:
    with pytest.raises(ValueError, match="HYDRA_UMC_VOICE_UI_TOKEN"):
        create_voice_gateway("0.0.0.0", 0)


def test_create_voice_gateway_allows_non_loopback_with_a_token() -> None:
    server = create_voice_gateway("0.0.0.0", 0, token="a-real-secret")
    try:
        assert server.token == "a-real-secret"
    finally:
        server.server_close()


def test_create_voice_gateway_allows_loopback_without_a_token() -> None:
    server = create_voice_gateway("127.0.0.1", 0)
    try:
        assert server.token is None
    finally:
        server.server_close()


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------


def test_health_reports_no_auth_required_without_a_token() -> None:
    with running_server() as base:
        status, body = _get(f"{base}/health")
        assert status == 200
        assert body["authRequired"] is False
        assert body["voiceTurnEndpoint"] == "/v1/voice/turn"


def test_health_reports_auth_required_with_a_token_configured() -> None:
    with running_server(token="secret") as base:
        status, body = _get(f"{base}/health")
        assert status == 200
        assert body["authRequired"] is True


def test_health_never_requires_a_token_itself() -> None:
    # Only POST /v1/voice/turn is gated - a real Watch client (or a load
    # balancer) must always be able to check liveness.
    with running_server(token="secret") as base:
        status, _ = _get(f"{base}/health")
        assert status == 200


def test_unknown_get_path_is_404() -> None:
    with running_server() as base:
        status, body = _get(f"{base}/nope")
        assert status == 404


# ---------------------------------------------------------------------------
# POST /v1/voice/turn - authorization
# ---------------------------------------------------------------------------


def test_turn_succeeds_without_a_token_when_none_is_configured() -> None:
    with running_server() as base:
        status, body = _post(f"{base}/v1/voice/turn", _turn())
        assert status == 200
        assert body["type"] == "assistant_reply"


def test_turn_rejects_a_missing_authorization_header_when_a_token_is_configured() -> None:
    with running_server(token="secret") as base:
        status, body = _post(f"{base}/v1/voice/turn", _turn())
        assert status == 401
        assert "error" in body


def test_turn_rejects_a_wrong_token() -> None:
    with running_server(token="secret") as base:
        status, _ = _post(f"{base}/v1/voice/turn", _turn(), headers={"Authorization": "Bearer wrong"})
        assert status == 401


def test_turn_accepts_the_real_configured_token() -> None:
    with running_server(token="secret") as base:
        status, body = _post(f"{base}/v1/voice/turn", _turn(), headers={"Authorization": "Bearer secret"})
        assert status == 200
        assert body["type"] == "assistant_reply"


def test_unknown_post_path_is_404_even_with_a_valid_token() -> None:
    with running_server(token="secret") as base:
        status, _ = _post(f"{base}/nope", _turn(), headers={"Authorization": "Bearer secret"})
        assert status == 404


# ---------------------------------------------------------------------------
# POST /v1/voice/turn - real request/response behavior
# ---------------------------------------------------------------------------


def test_turn_real_round_trip_reaches_the_real_intent_classifier() -> None:
    with running_server() as base:
        status, body = _post(f"{base}/v1/voice/turn", _turn(transcript="status of robot 3"))
        assert status == 200
        assert body["requestId"] == "req-1"
        assert "intent" in body


def test_turn_rejects_a_malformed_json_body() -> None:
    with running_server() as base:
        status, body = _post(f"{base}/v1/voice/turn", b"{not json")
        assert status == 400
        assert "error" in body


def test_turn_rejects_an_invalid_voice_turn_shape() -> None:
    with running_server() as base:
        status, body = _post(f"{base}/v1/voice/turn", json.dumps({"requestId": "x"}).encode())
        assert status == 400
        assert "error" in body


def test_turn_rejects_a_missing_content_length() -> None:
    # urllib always sends a real Content-Length for a real body - the
    # only way to genuinely omit it is a raw socket.
    with running_server() as base:
        host_port = base.removeprefix("http://")
        host, port = host_port.split(":")
        with socket.create_connection((host, int(port)), timeout=5) as sock:
            sock.sendall(
                b"POST /v1/voice/turn HTTP/1.1\r\n"
                b"Host: " + host_port.encode() + b"\r\n"
                b"Connection: close\r\n"
                b"\r\n"
            )
            raw = b""
            while chunk := sock.recv(4096):
                raw += chunk
        status_line = raw.split(b"\r\n", 1)[0].decode()
        assert " 400 " in status_line


def test_turn_rejects_a_body_over_the_real_size_limit() -> None:
    with running_server() as base:
        oversized = _turn(transcript="x" * MAX_BODY_BYTES)
        status, body = _post(f"{base}/v1/voice/turn", oversized)
        assert status == 413
        assert "error" in body
