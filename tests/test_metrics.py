# =============================================================================
# HYDRA-UMC-VOICE-UI - tests/test_metrics.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""`GET /metrics`: Prometheus text with the counters of the gateway, behind the token, and never a word of what was said."""
from __future__ import annotations

import json
import re
import threading
import urllib.error
import urllib.request
from collections.abc import Iterator
from contextlib import contextmanager

import pytest

from hydra_umc_voice_ui.metrics import INTENT_LABELS, Metrics
from hydra_umc_voice_ui.http_service import VoiceGatewayServer


@contextmanager
def running_server(token: str | None = None) -> Iterator[str]:
    server = VoiceGatewayServer(("127.0.0.1", 0), token)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def _get_text(url: str, headers: dict[str, str] | None = None) -> tuple[int, str, str]:
    request = urllib.request.Request(url, headers=headers or {}, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=5) as resp:
            return resp.status, resp.read().decode(), resp.headers.get("Content-Type", "")
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode(), error.headers.get("Content-Type", "")


def _post(url: str, payload: object, headers: dict[str, str] | None = None) -> int:
    request = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json", **(headers or {})}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=5) as resp:
            return resp.status
    except urllib.error.HTTPError as error:
        return error.code


def _value(text: str, series: str) -> float:
    match = re.search(rf"^{re.escape(series)} (\S+)$", text, re.MULTILINE)
    assert match, f"{series} is not in the metrics"
    return float(match.group(1))


def _assert_exposition(text: str) -> None:
    declared: set[str] = set()
    for line in text.splitlines():
        if line.startswith("# TYPE "):
            declared.add(line.split()[2])
        elif line.startswith("# HELP ") or not line:
            continue
        else:
            name = line.split("{")[0].split(" ")[0]
            assert name in declared, f"{name} used before its TYPE"
            float(line.rsplit(" ", 1)[1])


def test_the_metrics_are_prometheus_text_and_follow_the_turns() -> None:
    with running_server() as base:
        status, first, content_type = _get_text(f"{base}/metrics")
        assert status == 200 and content_type.startswith("text/plain; version=0.0.4")
        _assert_exposition(first)
        assert _value(first, 'hydra_umc_voice_ui_turns_total{intent="stop"}') == 0

        turn = {"requestId": "r-1", "transcript": "stop", "locale": "en-US"}
        assert _post(f"{base}/v1/voice/turn", {**turn, "transcript": "stop"}) == 200
        assert _post(f"{base}/v1/voice/turn", {**turn, "transcript": "inicia la misión alfa", "locale": "es-ES"}) == 200
        assert _post(f"{base}/v1/voice/turn", {**turn, "transcript": "what a nice day"}) == 200
        assert _post(f"{base}/v1/voice/turn", {"nonsense": True}) == 400
        _, second, _ = _get_text(f"{base}/metrics")
        _assert_exposition(second)
        assert _value(second, 'hydra_umc_voice_ui_turns_total{intent="stop"}') == 1
        assert _value(second, 'hydra_umc_voice_ui_turns_total{intent="start_mission"}') == 1
        assert _value(second, 'hydra_umc_voice_ui_turns_total{intent="none"}') == 1
        assert _value(second, "hydra_umc_voice_ui_confirmations_requested_total") >= 1
        assert _value(second, 'hydra_umc_voice_ui_refused_total{reason="bad_request"}') == 1


def test_what_was_said_never_reaches_a_metric() -> None:
    with running_server() as base:
        secret_words = "open the garage of Maple Street 12"
        _post(f"{base}/v1/voice/turn", {"requestId": "request-private-7", "transcript": secret_words, "locale": "en-US", "subject": "alice@example.org"})
        _, text, _ = _get_text(f"{base}/metrics")
    for private in ("garage", "Maple", "request-private-7", "alice", "example.org"):
        assert private not in text


def test_with_a_token_the_metrics_need_it_and_the_health_path_stays_open() -> None:
    token = "t" * 32
    with running_server(token) as base:
        assert _get_text(f"{base}/health")[0] == 200
        assert _get_text(f"{base}/metrics")[0] == 401
        assert _get_text(f"{base}/metrics", {"Authorization": "Bearer wrong"})[0] == 401
        status, text, _ = _get_text(f"{base}/metrics", {"Authorization": f"Bearer {token}"})
        assert status == 200
        assert _value(text, 'hydra_umc_voice_ui_refused_total{reason="unauthorized"}') == 2
        assert token not in text


def test_a_label_can_only_take_a_value_of_the_closed_list() -> None:
    metrics = Metrics()
    metrics.turn("drop table", needs_confirmation=False)
    metrics.turn(None, needs_confirmation=False)
    metrics.refused("a reason nobody listed")
    text = metrics.render()
    assert _value(text, 'hydra_umc_voice_ui_turns_total{intent="none"}') == 2
    assert _value(text, 'hydra_umc_voice_ui_refused_total{reason="bad_request"}') == 1
    assert "drop table" not in text and "nobody listed" not in text
    assert set(re.findall(r'intent="([^"]+)"', text)) == set(INTENT_LABELS)


@pytest.mark.parametrize("path", ["/metrics/", "/metrics?x=1", "/Metrics"])
def test_only_the_exact_path_is_the_metrics_route(path: str) -> None:
    with running_server() as base:
        assert _get_text(f"{base}{path}")[0] == 404
