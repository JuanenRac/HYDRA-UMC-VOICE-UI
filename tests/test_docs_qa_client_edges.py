# =============================================================================
# HYDRA-UMC-VOICE-UI - tests/test_docs_qa_client_edges.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The client of the documentation service at its edges, against a small HTTP stand-in that answers the way a service does when it is well, when it knows nothing,
when it answers rubbish, when it answers too much and when it is not there: what the person is told in each case, and that the token is sent only when there is one."""
from __future__ import annotations

import json
import socket
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from hydra_umc_voice_ui.queries import DocsQaClient
from hydra_umc_voice_ui.voice_config import QueryConfig


class _Handler(BaseHTTPRequestHandler):
    server: "_Server"

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        pass

    def do_GET(self) -> None:  # noqa: N802
        self.server.requests.append((self.path, self.headers.get("Authorization")))
        status, body = self.server.respond()
        self.send_response(status)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class _Server(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self) -> None:
        super().__init__(("127.0.0.1", 0), _Handler)
        self.requests: list[tuple[str, str | None]] = []
        self.respond: Callable[[], tuple[int, bytes]] = lambda: (200, b"{}")


@contextmanager
def _service() -> Iterator[tuple[_Server, str]]:
    server = _Server()
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield server, f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


def _client(url: str, **over) -> DocsQaClient:
    return DocsQaClient(QueryConfig(enabled=True, docs_qa_url=url, timeout_seconds=2.0, **over))


def _json(payload: object, status: int = 200) -> Callable[[], tuple[int, bytes]]:
    return lambda: (status, json.dumps(payload).encode("utf-8"))


def test_a_definition_is_returned_with_its_value_and_its_citation_and_the_kind_line_is_dropped():
    match = {"name": "STATUS_VERIFY_FAIL", "value": 5, "text": "Kind: status code\nThe image did not verify.\nUpdate it again.", "citation": "docs/ERRORS.md#verify"}
    with _service() as (server, url):
        server.respond = _json({"matches": [match]})
        answer = _client(url).ask("0x05")
        assert answer.status == "answered" and answer.sources == ("docs/ERRORS.md#verify",)
        assert answer.text == "STATUS_VERIFY_FAIL (0x05): The image did not verify. Update it again."
        assert server.requests == [("/error?code=0x05", None)]


def test_only_the_first_three_matches_are_read_and_the_answer_is_cut_to_the_limit():
    matches = [{"name": f"E{n}", "text": "word " * 60, "citation": f"c{n}"} for n in range(5)]
    with _service() as (server, url):
        server.respond = _json({"matches": matches})
        answer = _client(url, max_answer_chars=100).ask("E1")
        assert answer.status == "answered" and len(answer.text) <= 100 and answer.text.endswith("...")
        assert answer.sources == ("c0", "c1", "c2")


def test_a_code_that_is_not_in_the_documentation_is_not_found_and_never_a_guess():
    with _service() as (server, url):
        server.respond = _json({"matches": []})
        answer = _client(url).ask("0x7F")
        assert (answer.status, answer.text, answer.sources) == ("not_found", "", ())


@pytest.mark.parametrize("payload", [{}, {"matches": "none"}, {"matches": None}, [], "text", 3, {"matches": [{"name": 1, "text": "x"}]}, {"matches": [{"name": "A"}]},
                                     {"matches": ["a", 3, None]}])
def test_an_answer_that_is_not_a_list_of_definitions_is_unavailable(payload):
    with _service() as (server, url):
        server.respond = _json(payload)
        assert _client(url).ask("5").status == "unavailable"


def test_a_value_that_is_not_a_number_is_left_out_of_the_name_and_a_bad_citation_is_left_out_of_the_sources():
    items = [{"name": "A", "value": True, "text": "one", "citation": 5}, {"name": "B", "value": "5", "text": "two", "citation": "ok"}, {"name": "C", "value": 255, "text": "three"}]
    with _service() as (server, url):
        server.respond = _json({"matches": items})
        answer = _client(url).ask("A")
        assert answer.text == "A: one / B: two / C (0xFF): three" and answer.sources == ("ok",)


def test_a_citation_is_cut_to_three_hundred_characters():
    with _service() as (server, url):
        server.respond = _json({"matches": [{"name": "A", "text": "x", "citation": "c" * 900}]})
        assert len(_client(url).ask("A").sources[0]) == 300


@pytest.mark.parametrize("status", [400, 401, 403, 404, 500, 503])
def test_an_error_status_is_unavailable(status):
    with _service() as (server, url):
        server.respond = _json({"matches": [{"name": "A", "text": "x"}]}, status)
        assert _client(url).ask("A").status == "unavailable"


def test_rubbish_and_an_answer_over_the_limit_are_unavailable():
    with _service() as (server, url):
        for body in (b"not json", b"\xff\xfe\x00", b"", b'{"matches": [' + b" " * (DocsQaClient.MAX_RESPONSE_BYTES + 5) + b"]}"):
            server.respond = lambda body=body: (200, body)
            assert _client(url).ask("A").status == "unavailable"


def test_a_service_that_is_not_there_is_unavailable_and_not_an_exception():
    with socket.socket() as holder:
        holder.bind(("127.0.0.1", 0))
        dead = f"http://127.0.0.1:{holder.getsockname()[1]}"
    assert _client(dead).ask("A").status == "unavailable"


def test_the_token_is_sent_only_when_there_is_a_readable_one(tmp_path: Path):
    token = tmp_path / "token"
    token.write_text("  secret-token\n", encoding="utf-8")
    with _service() as (server, url):
        server.respond = _json({"matches": []})
        _client(url, token_file=str(token)).ask("A")
        _client(url, token_file=str(tmp_path / "missing")).ask("A")
        binary = tmp_path / "binary"
        binary.write_bytes(b"\xff\xfe\x00")
        _client(url, token_file=str(binary)).ask("A")
        _client(url).ask("A")
        assert [auth for _, auth in server.requests] == ["Bearer secret-token", None, None, None]


def test_a_code_with_characters_that_mean_something_in_a_url_is_encoded():
    with _service() as (server, url):
        server.respond = _json({"matches": []})
        _client(url).ask("a&b=c d")
        assert server.requests[0][0] == "/error?code=a%26b%3Dc+d"
