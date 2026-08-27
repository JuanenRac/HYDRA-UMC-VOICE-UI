# =============================================================================
# HYDRA-UMC-VOICE-UI - tests/test_cli.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
from __future__ import annotations

import wave
from array import array
from pathlib import Path

import pytest

from hydra_umc_voice_ui.main import main

SAMPLE_RATE = 8000


def _write_silent_wav(path: Path, seconds: float = 0.5) -> None:
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(SAMPLE_RATE)
        wav_file.writeframes(array("h", [0] * int(SAMPLE_RATE * seconds)).tobytes())


def test_bare_invocation_prints_identity(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main([])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "HYDRA-UMC-VOICE-UI v" in captured.out
    assert "Voice UI" in captured.out


def test_analyze_audio_on_real_wav_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    wav_path = tmp_path / "clip.wav"
    _write_silent_wav(wav_path)

    exit_code = main(["analyze-audio", str(wav_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Sample rate: 8000 Hz" in captured.out
    assert "Duration: 0.500 s" in captured.out


def test_analyze_audio_missing_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["analyze-audio", str(tmp_path / "missing.wav")])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "file not found" in captured.out


def test_parse_intent_matches(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["parse-intent", "status of robot 5"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Intent: status" in captured.out
    assert "robot_id: 5" in captured.out


def test_parse_intent_no_match(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["parse-intent", "what time is it"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "No matching intent" in captured.out
