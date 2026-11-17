# =============================================================================
# HYDRA-UMC-VOICE-UI - tests/test_enroll_audit.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Enrolling and forgetting an operator's voice leave a record in the audit log, without the voice vector or the name."""
from __future__ import annotations

import json
import math
import threading
import urllib.request
from pathlib import Path

import pytest

from hydra_umc_voice_ui.http_service import ENROLL_TOKEN_ENV, VoiceGatewayServer

TURNS = "t" * 20
VECTOR = [math.sin(i + 1) for i in range(32)]


def _post(url: str, body: dict) -> int:
    request = urllib.request.Request(
        url, data=json.dumps(body).encode(), method="POST", headers={"Content-Type": "application/json", "Authorization": f"Bearer {TURNS}"}
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        return response.status


def test_enrolling_and_forgetting_a_voice_are_audited(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    log = tmp_path / "audit.jsonl"
    path = tmp_path / "voice-ui.json"
    path.write_text(
        json.dumps({"speaker": {"enabled": True, "storeFile": str(tmp_path / "sp.json")}, "audit": {"enabled": True, "file": str(log)}}),
        encoding="utf-8",
    )
    monkeypatch.setenv("HYDRA_UMC_VOICE_UI_CONFIG", str(path))
    monkeypatch.delenv(ENROLL_TOKEN_ENV, raising=False)
    server = VoiceGatewayServer(("127.0.0.1", 0), TURNS)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        assert _post(f"{base}/v1/voice/speaker/enroll", {"subject": "ana", "vector": VECTOR}) == 200
        assert _post(f"{base}/v1/voice/speaker/forget", {"subject": "ana"}) == 200
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
    records = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
    assert [(r["event"], r["outcome"]) for r in records] == [("enroll", "enrolled"), ("forget", "forgotten")]
    assert records[0]["subject"] == records[1]["subject"] != ""
    text = log.read_text(encoding="utf-8")
    assert "ana" not in text and "vector" not in text
