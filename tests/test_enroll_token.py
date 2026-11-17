# =============================================================================
# HYDRA-UMC-VOICE-UI - tests/test_enroll_token.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Enrolling and forgetting voices can have a bearer token of their own."""
from __future__ import annotations

import json
import math
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from hydra_umc_voice_ui.http_service import ENROLL_TOKEN_ENV, VoiceGatewayServer

TURNS = "t" * 20
ENROL = "e" * 20


def _call(url: str, body: dict, token: str | None) -> tuple[int, dict]:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST", headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


def _serve(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, enroll_token: str | None):
    path = tmp_path / "voice-ui.json"
    path.write_text(json.dumps({"speaker": {"enabled": True, "storeFile": str(tmp_path / "sp.json")}, "audit": {"enabled": False}}), encoding="utf-8")
    monkeypatch.setenv("HYDRA_UMC_VOICE_UI_CONFIG", str(path))
    if enroll_token:
        monkeypatch.setenv(ENROLL_TOKEN_ENV, enroll_token)
    else:
        monkeypatch.delenv(ENROLL_TOKEN_ENV, raising=False)
    server = VoiceGatewayServer(("127.0.0.1", 0), TURNS)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread, f"http://127.0.0.1:{server.server_address[1]}"


def _stop(server: VoiceGatewayServer, thread: threading.Thread) -> None:
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


VECTOR = [math.sin(i + 1) for i in range(32)]


def test_with_an_enrol_token_only_that_token_enrols_and_forgets(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    server, thread, base = _serve(monkeypatch, tmp_path, ENROL)
    try:
        body = {"subject": "ana", "vector": VECTOR}
        assert _call(f"{base}/v1/voice/speaker/enroll", body, TURNS)[0] == 401      # the token of the turns is not the one for voices
        assert _call(f"{base}/v1/voice/speaker/enroll", body, None)[0] == 401
        assert _call(f"{base}/v1/voice/speaker/enroll", body, ENROL) == (200, {"enrolled": True, "operators": 1})
        assert _call(f"{base}/v1/voice/speaker/forget", {"subject": "ana"}, TURNS)[0] == 401
        assert _call(f"{base}/v1/voice/speaker/forget", {"subject": "ana"}, ENROL) == (200, {"forgotten": True, "operators": 0})
        # the other routes keep the token of the turns, and the enrol token does not open them
        turn = {"requestId": "r-1", "transcript": "status", "locale": "en"}
        assert _call(f"{base}/v1/voice/turn", turn, TURNS)[0] == 200
        assert _call(f"{base}/v1/voice/turn", turn, ENROL)[0] == 401
    finally:
        _stop(server, thread)


def test_without_the_variable_the_service_token_still_enrols(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    server, thread, base = _serve(monkeypatch, tmp_path, None)
    try:
        assert _call(f"{base}/v1/voice/speaker/enroll", {"subject": "ana", "vector": VECTOR}, TURNS)[0] == 200
        assert _call(f"{base}/v1/voice/speaker/enroll", {"subject": "ana", "vector": VECTOR}, ENROL)[0] == 401
    finally:
        _stop(server, thread)
