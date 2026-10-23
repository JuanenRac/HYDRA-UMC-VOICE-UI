# =============================================================================
# HYDRA-UMC-VOICE-UI - tests/test_ratelimit.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""The per-client request limit, and what it means for the used-confirmation list of the gateway."""
from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

import pytest

from hydra_umc_voice_ui import gateway
from hydra_umc_voice_ui.http_service import VoiceGatewayServer
from hydra_umc_voice_ui.ratelimit import ClientRateLimiter


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def test_a_client_over_the_limit_waits_and_then_goes_on() -> None:
    clock = Clock()
    limiter = ClientRateLimiter(3, window=60.0, clock=clock)
    assert [limiter.allow("a")[0] for _ in range(3)] == [True, True, True]
    allowed, wait = limiter.allow("a")
    assert not allowed and 0 < wait <= 60.0
    clock.now += 61.0
    assert limiter.allow("a")[0]


def test_one_client_does_not_use_up_the_turn_of_another() -> None:
    limiter = ClientRateLimiter(1, clock=Clock())
    assert limiter.allow("a")[0] and not limiter.allow("a")[0]
    assert limiter.allow("b")[0]


def test_zero_turns_the_limit_off_and_a_negative_limit_is_refused() -> None:
    limiter = ClientRateLimiter(0, clock=Clock())
    assert all(limiter.allow("a")[0] for _ in range(1000))
    with pytest.raises(ValueError):
        ClientRateLimiter(-1)


def test_the_number_of_clients_remembered_is_bounded() -> None:
    limiter = ClientRateLimiter(1, max_clients=3, clock=Clock())
    for client in "abcde":
        limiter.allow(client)
    assert len(limiter._seen) == 3
    assert limiter.allow("a")[0], "the oldest were forgotten, not kept for ever"


def _post(url: str, body: dict) -> tuple[int, dict]:
    request = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=5) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


def test_the_http_service_answers_429_past_the_limit_and_keeps_serving_others() -> None:
    server = VoiceGatewayServer(("127.0.0.1", 0), None, requests_per_minute=2)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_address[1]}/v1/voice/turn"
        turn = {"requestId": "r-1", "transcript": "status of robot 2", "locale": "en-US"}
        assert _post(url, turn)[0] == 200
        assert _post(url, turn)[0] == 200
        status, body = _post(url, turn)
        assert status == 429 and body["retryAfterSeconds"] > 0
        # another address is not held up (the limiter keys on the address)
        assert server.limiter.allow("10.9.9.9")[0]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_the_limit_comes_from_the_environment_and_a_bad_value_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HYDRA_UMC_VOICE_UI_RATE_PER_MINUTE", "7")
    server = VoiceGatewayServer(("127.0.0.1", 0), None)
    try:
        assert server.limiter.limit == 7
    finally:
        server.server_close()
    for bad in ("many", "-3"):
        monkeypatch.setenv("HYDRA_UMC_VOICE_UI_RATE_PER_MINUTE", bad)
        with pytest.raises(ValueError):
            VoiceGatewayServer(("127.0.0.1", 0), None)


def test_a_full_used_list_still_refuses_in_a_moment_but_holds_far_more_than_before() -> None:
    assert gateway.MAX_USED_CONFIRMATIONS >= 16384
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    with gateway._used_lock:
        gateway._used_confirmations.clear()
    try:
        for index in range(gateway.MAX_USED_CONFIRMATIONS):
            pending = gateway.PendingConfirmation(
                request_id=f"r{index}", intent_name="stop", entities=(), issued_at=now, nonce=f"n{index:08d}",
            )
            assert gateway._consume_confirmation(pending, now) is None
        extra = gateway.PendingConfirmation(request_id="x", intent_name="stop", entities=(), issued_at=now, nonce="extra")
        assert "too many confirmations" in (gateway._consume_confirmation(extra, now) or "")
        later = now + timedelta(seconds=gateway.CONFIRMATION_VALIDITY_SECONDS + 1)
        fresh = gateway.PendingConfirmation(request_id="y", intent_name="stop", entities=(), issued_at=later, nonce="fresh")
        assert gateway._consume_confirmation(fresh, later) is None, "the expired ones make room"
    finally:
        with gateway._used_lock:
            gateway._used_confirmations.clear()
