# =============================================================================
# HYDRA-UMC-VOICE-UI - tests/test_cognitive_node_gate.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""A confirmed spoken request asks the cognitive node, with the subject and the proof, and is honoured only when the node allows it."""

import json
import os
import tempfile
import threading
import unittest
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from hydra_umc_voice_ui.confirmation_proof import verify_proof
from hydra_umc_voice_ui.gateway import COGNITIVE_TOKEN_FILE_ENV, COGNITIVE_URL_ENV, PROOF_KEY_ENV, cognitive_node_refusal, confirmation_proof_of

KEY = b"vector-key-" + b"0123456789abcdef" * 2
NODE_TOKEN = "node-bearer-" + "x" * 8


class FakeNode:
    """A cognitive node on the loopback address: it records each question and answers what it is told to."""

    def __init__(self, decision="allow", reason="confirmed", status=200):
        self.asked = []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                outer.asked.append((self.path, self.headers.get("Authorization"), body))
                payload = json.dumps({"decision": decision, "reason": reason}).encode()
                self.send_response(status)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.server.shutdown()
        self.server.server_close()


class Gate(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.key = Path(self.folder.name) / "voice.key"
        self.key.write_bytes(KEY)
        os.chmod(self.key, 0o600)

    def ask(self, node_url, entities, **extra):
        env = {PROOF_KEY_ENV: str(self.key), COGNITIVE_URL_ENV: node_url, **extra}
        proof = confirmation_proof_of("turn-1", entities, "ana", datetime.now(timezone.utc), env)
        return proof, cognitive_node_refusal("turn-1", entities, proof, env)

    def test_without_a_node_nothing_is_asked(self):
        self.assertIsNone(cognitive_node_refusal("turn-1", {}, None, {}))

    def test_the_subject_is_the_robot_or_the_installation_and_the_proof_goes_with_it(self):
        token_file = Path(self.folder.name) / "node.token"
        token_file.write_text(NODE_TOKEN, encoding="utf-8")
        for entities, subject in (({"robotId": "robot-1"}, "robot-1"), ({}, "installation")):
            with FakeNode() as node:
                proof, refusal = self.ask(node.url, entities, **{COGNITIVE_TOKEN_FILE_ENV: str(token_file)})
            self.assertIsNone(refusal)
            path, authorization, question = node.asked[0]
            self.assertEqual((path, authorization), ("/autonomy/evaluate", "Bearer " + NODE_TOKEN))
            self.assertEqual((question["source"], question["level"], question["subjectId"], question["actionId"]), ("voice-ui", "execute_with_confirmation", subject, "turn-1"))
            self.assertEqual(question["confirmationProof"], proof)
            self.assertEqual(verify_proof(KEY, proof, expected_action_id="turn-1", expected_subject_id=subject), (True, ""))

    def test_a_refusal_or_no_answer_is_not_honoured(self):
        with FakeNode(decision="deny", reason="proof_invalid") as node:
            self.assertIn("proof_invalid", self.ask(node.url, {})[1])
            url = node.url
        self.assertIsNotNone(self.ask(url, {})[1])
        self.assertIsNotNone(self.ask("ftp://node", {})[1])
        self.assertIsNotNone(self.ask(url, {}, **{COGNITIVE_TOKEN_FILE_ENV: self.folder.name + "/missing"})[1])


if __name__ == "__main__":
    unittest.main()
