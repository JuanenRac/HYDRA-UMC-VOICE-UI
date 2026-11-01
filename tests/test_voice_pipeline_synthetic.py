# =============================================================================
# HYDRA-UMC-VOICE-UI - tests/test_voice_pipeline_synthetic.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""The whole chain without a microphone or a recognizer: a recording made of synthetic audio (tones for speech, silence, a constant hum), the
voice detector that cuts it into utterances, a stand-in recognizer that says what each utterance was, and the gateway that answers each one.
What is not tested here is a real speech recognizer: that needs real speech and a model."""
from __future__ import annotations

import array
import math
import wave
from datetime import datetime, timezone
from pathlib import Path

import pytest

from hydra_umc_voice_ui.audio import detect_voice_segments, load_wav
from hydra_umc_voice_ui.gateway import VoiceTurn, process_voice_turn

RATE = 8000
NOW = datetime(2026, 1, 5, 10, 0, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def _default_stop(monkeypatch: pytest.MonkeyPatch) -> None:
    """The shared fixture asks to confirm a stop; here the chain runs with the default of a deployment (a stop is answered at once)."""
    monkeypatch.delenv("HYDRA_UMC_VOICE_UI_STOP_REQUIRES_CONFIRMATION", raising=False)


def _tone(seconds: float, amplitude: int = 9000, frequency: float = 300.0) -> list[int]:
    return [int(amplitude * math.sin(2 * math.pi * frequency * i / RATE)) for i in range(int(seconds * RATE))]


def _silence(seconds: float) -> list[int]:
    return [0] * int(seconds * RATE)


def _hum(seconds: float, amplitude: int = 1500) -> list[int]:
    return [int(amplitude * math.sin(2 * math.pi * 50.0 * i / RATE)) for i in range(int(seconds * RATE))]


def _write(path: Path, samples: list[int]) -> Path:
    with wave.open(str(path), "wb") as clip:
        clip.setnchannels(1)
        clip.setsampwidth(2)
        clip.setframerate(RATE)
        clip.writeframes(array.array("h", samples).tobytes())
    return path


def _recording(utterances: int, *, gap: float = 0.8, burst: float = 0.7, floor: float = 0.0) -> list[int]:
    """`utterances` bursts of tone, each between stretches of silence (or of a hum when `floor` is set)."""
    quiet = (lambda seconds: _hum(seconds)) if floor else _silence
    samples = quiet(gap)
    for _ in range(utterances):
        samples += _tone(burst) + quiet(gap)
    return samples


def _turn(index: int, transcript: str, *, locale: str = "en-US", confidence: float | None = None) -> VoiceTurn:
    payload: dict[str, object] = {"requestId": f"synthetic-{index}", "transcript": transcript, "locale": locale}
    if confidence is not None:
        payload["confidence"] = confidence
    return VoiceTurn.from_payload(payload)


def test_each_burst_of_the_recording_becomes_one_turn_and_each_turn_gets_the_right_answer(tmp_path: Path) -> None:
    said = [("status of robot 2", "en-US"), ("stop", "en-US"), ("start mission alpha", "en-US"), ("vuelve a casa", "es-ES")]
    clip = load_wav(_write(tmp_path / "talk.wav", _recording(len(said))))
    segments = detect_voice_segments(clip, threshold=1000.0)
    assert len(segments) == len(said), "the detector cut the recording in a different number of utterances"
    replies = [process_voice_turn(_turn(index, text, locale=locale), now=NOW) for index, (text, locale) in enumerate(said)]
    names = [reply.intent.name if reply.intent else None for reply in replies]
    assert names == ["status", "stop", "start_mission", "go_home"]
    assert [reply.requires_confirmation for reply in replies] == [False, False, True, True]
    assert replies[1].priority == "safety-stop"
    assert replies[3].text, "the reply to a spoken command in Spanish is written"
    assert [reply.request_id for reply in replies] == [f"synthetic-{index}" for index in range(4)]


def test_a_constant_hum_is_not_taken_for_a_command_and_the_speech_over_it_is_found(tmp_path: Path) -> None:
    clip = load_wav(_write(tmp_path / "hum.wav", _recording(2, floor=1.0)))
    # the fixed gate reads the hum as speech from start to end; the gate relative to the noise finds the two bursts only
    assert len(detect_voice_segments(clip, threshold=500.0)) == 1
    assert len(detect_voice_segments(clip, noise_ratio=3.0)) == 2


def test_silence_gives_no_turn_at_all(tmp_path: Path) -> None:
    clip = load_wav(_write(tmp_path / "silence.wav", _silence(3.0)))
    assert detect_voice_segments(clip, threshold=1000.0) == []


def test_a_movement_heard_with_low_confidence_is_asked_again_and_a_stop_never_is() -> None:
    held = process_voice_turn(_turn(1, "go home", confidence=0.2), now=NOW, min_confidence=0.6)
    assert held.intent is None and held.requires_confirmation is False
    assert held.pending_confirmation is None
    stop = process_voice_turn(_turn(2, "stop", confidence=0.05), now=NOW, min_confidence=0.6)
    assert stop.intent is not None and stop.intent.name == "stop" and stop.priority == "safety-stop"


def test_a_negated_command_in_any_language_is_never_run(tmp_path: Path) -> None:
    for index, (text, locale) in enumerate([("do not stop", "en-US"), ("no pares", "es-ES"), ("nicht stopp", "de-DE"), ("止めないで", "ja-JP"), ("不要回家", "zh-CN")]):
        reply = process_voice_turn(_turn(index, text, locale=locale), now=NOW)
        assert reply.intent is None and reply.requires_confirmation is False and reply.priority is None, text
        assert reply.text, text


def test_two_commands_in_one_utterance_are_asked_to_be_said_one_at_a_time() -> None:
    reply = process_voice_turn(_turn(1, "stopp und status", locale="de-DE"), now=NOW)
    assert reply.intent is None and reply.requires_confirmation is False


def test_a_movement_waits_for_the_confirmation_of_the_primary_device_in_every_language() -> None:
    for index, (text, locale) in enumerate([("start mission alpha", "en-US"), ("inicia la misión alfa", "es-ES"), ("démarre la mission alpha", "fr-FR"), ("ミッション開始 alpha", "ja-JP"), ("开始任务 alpha", "zh-CN")]):
        reply = process_voice_turn(_turn(index, text, locale=locale), now=NOW)
        assert reply.intent is not None and reply.intent.name == "start_mission", text
        assert reply.requires_confirmation is True and reply.pending_confirmation is not None, text
