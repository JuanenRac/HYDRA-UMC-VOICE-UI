# =============================================================================
# HYDRA-UMC-VOICE-UI - tests/test_secret_file_encodings.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""A secret file saved by an editor of Windows with a byte order mark holds the same secret; a file in another encoding is refused, never guessed."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from hydra_umc_voice_ui.confirmation_proof import load_node_token
from hydra_umc_voice_ui.queries import DocsQaClient

SAMPLE = "sample-0123456789-abcdefghij-0123456789"


class SecretFileEncodingTests(unittest.TestCase):
    def setUp(self) -> None:
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.bom = Path(folder.name, "bom.token")
        self.bom.write_bytes(b"\xef\xbb\xbf" + SAMPLE.encode("ascii") + b"\r\n")  # what Notepad calls "UTF-8 with BOM"
        self.utf16 = Path(folder.name, "utf16.token")
        self.utf16.write_bytes((SAMPLE + "\r\n").encode("utf-16"))  # what `>` of Windows PowerShell writes

    def test_the_node_token_ignores_a_byte_order_mark(self) -> None:
        self.assertEqual(load_node_token(str(self.bom)), SAMPLE)

    def test_the_node_token_refuses_another_encoding(self) -> None:
        with self.assertRaises(ValueError):
            load_node_token(str(self.utf16))

    def test_the_token_of_the_documentation_ignores_a_byte_order_mark(self) -> None:
        self.assertEqual(DocsQaClient(SimpleNamespace(token_file=str(self.bom)))._token(), SAMPLE)

    def test_the_token_of_the_documentation_does_not_use_another_encoding(self) -> None:
        self.assertEqual(DocsQaClient(SimpleNamespace(token_file=str(self.utf16)))._token(), "")


if __name__ == "__main__":
    unittest.main()
