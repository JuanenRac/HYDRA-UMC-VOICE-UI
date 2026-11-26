# =============================================================================
# HYDRA-UMC-VOICE-UI - tests/test_confirmation_proof.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The ConfirmationProof of the SDK: the same bytes, signed when a key is given and asked for only when switched on."""

import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from hydra_umc_voice_ui.confirmation_proof import proof_identifier, sign_proof, verify_proof
from hydra_umc_voice_ui.gateway import PROOF_KEY_ENV, confirmation_proof_of

KEY = b"vector-key-" + b"0123456789abcdef" * 2


class Proof(unittest.TestCase):
    def test_the_proof_is_the_one_of_the_sdk(self):
        for (kind, action, subject, operator, identity), signature in (
            (("approval", "f" * 64, "robot-1", "ana", "a" * 32), "40455c91e510cecef1a7f2705b206587cb7211b464862ce8a35c1fe500048477"),
            (("voice", "turn-42", "installation", proof_identifier("ana@example.com"), "b" * 32), "6d353d430780ae4a8d56cc6e062cd934998f0813b870e69887059f49fda5a281"),
        ):
            proof = sign_proof(KEY, kind=kind, action_id=action, subject_id=subject, operator=operator, approved_at_ms=1700000000000,
                               expires_at_ms=1700000010000, approval_id=identity)
            self.assertEqual(proof["signature"], signature)
            self.assertEqual(verify_proof(KEY, proof, expected_action_id=action, expected_subject_id=subject, now_ms=1700000000500), (True, ""))
            self.assertFalse(verify_proof(KEY, proof, expected_action_id=action, expected_subject_id="robot-2", now_ms=1700000000500)[0])
            self.assertFalse(verify_proof(KEY, proof, expected_action_id=action, expected_subject_id=subject, now_ms=1700000010000)[0])
            self.assertFalse(verify_proof(b"x" * 32, proof, expected_action_id=action, expected_subject_id=subject, now_ms=1700000000500)[0])

    def test_a_spoken_confirmation_carries_a_proof_only_with_a_key_file(self):
        now = datetime.now(timezone.utc)
        self.assertIsNone(confirmation_proof_of("turn-1", {}, "ana", now, {}))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "voice.key"
            path.write_bytes(KEY)
            os.chmod(path, 0o600)
            named = confirmation_proof_of("turn-1", {"robotId": "robot-1"}, "ana", now, {PROOF_KEY_ENV: str(path)})
            unnamed = confirmation_proof_of("turn-1", {}, "", now, {PROOF_KEY_ENV: str(path)})
            self.assertEqual(verify_proof(KEY, named, expected_action_id="turn-1", expected_subject_id="robot-1"), (True, ""))
            self.assertEqual(unnamed["subject_id"], "installation")
            with self.assertRaises(ValueError):
                confirmation_proof_of("turn-1", {}, "ana", now, {PROOF_KEY_ENV: str(path) + ".missing"})


if __name__ == "__main__":
    unittest.main()
