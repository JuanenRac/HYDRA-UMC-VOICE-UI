# =============================================================================
# HYDRA-UMC-VOICE-UI - tests/test_fake_audio_devices.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""A fake microphone, a fake wake word and speech recognizer, and a fake speaker, around the real voice detector, gateway and alert composer (evidence: simulator).

The microphone hands out a recording in blocks of a few milliseconds, like a sound card; the recognizer says what each utterance was from its pitch (a stand-in for
Whisper) and also whether the wake phrase came first; the speaker records what it was told to say. The detector, the gateway and the alert composer are the real ones.
Nothing here has run with a real microphone, a real wake word model, a real speech recognizer or a real loudspeaker.
"""
from __future__ import annotations

import math
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timezone

import pytest

from hydra_umc_voice_ui.alerts import AlertReply, AlertSpeaker
from hydra_umc_voice_ui.audio import StreamingVad
from hydra_umc_voice_ui.gateway import VoiceTurn, process_voice_turn
from hydra_umc_voice_ui.voice_config import AlertConfig, VoiceConfig, WakeConfig

RATE = 16000
NOW = datetime(2026, 1, 5, 10, 0, 0, tzinfo=timezone.utc)

# what each pitch "says" (the stand-in recognizer reads the pitch, a real one reads speech)
PITCHES = {300.0: "hydra status of robot 2", 500.0: "hydra stop", 700.0: "start mission alpha", 900.0: "stop"}


@pytest.fixture(autouse=True)
def _default_stop(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HYDRA_UMC_VOICE_UI_STOP_REQUIRES_CONFIRMATION", raising=False)


def _tone(seconds: float, frequency: float, amplitude: int = 9000) -> list[int]:
    return [int(amplitude * math.sin(2 * math.pi * frequency * i / RATE)) for i in range(int(seconds * RATE))]


def recording(pitches: list[float], gap: float = 0.6, burst: float = 0.5) -> list[int]:
    samples = [0] * int(gap * RATE)
    for pitch in pitches:
        samples += _tone(burst, pitch) + [0] * int(gap * RATE)
    return samples


class FakeMicrophone:
    """Hands out `samples` in blocks of `block` samples, the way a sound card driver does."""

    def __init__(self, samples: list[int], block: int) -> None:
        self.samples, self.block = samples, block

    def blocks(self) -> Iterator[list[int]]:
        for start in range(0, len(self.samples), self.block):
            yield self.samples[start : start + self.block]


class FakeRecognizer:
    """Says what an utterance was from its pitch (zero crossings per second)."""

    def hear(self, samples: list[int]) -> tuple[str, float]:
        crossings = sum(1 for a, b in zip(samples, samples[1:], strict=False) if (a < 0) != (b < 0))
        pitch = crossings / 2 / (len(samples) / RATE)
        nearest = min(PITCHES, key=lambda candidate: abs(candidate - pitch))
        return PITCHES[nearest], 0.9 if abs(nearest - pitch) < 40 else 0.3


def listen(samples: list[int], block: int) -> list[VoiceTurn]:
    """The whole listening loop: microphone blocks into the detector, each finished utterance into the recognizer, each transcript into a turn."""
    vad = StreamingVad(RATE, threshold=1000.0)
    microphone, recognizer = FakeMicrophone(samples, block), FakeRecognizer()
    turns: list[VoiceTurn] = []
    consumed = 0

    def take(segments) -> None:  # noqa: ANN001
        for segment in segments:
            utterance = samples[int(segment.start_seconds * RATE) : int(segment.end_seconds * RATE)]
            transcript, confidence = recognizer.hear(utterance)
            turns.append(VoiceTurn.from_payload({"requestId": f"mic-{len(turns)}", "transcript": transcript, "locale": "en-US", "confidence": confidence}))

    for chunk in microphone.blocks():
        consumed += len(chunk)
        take(vad.feed(chunk))
    take(vad.finish())
    assert consumed == len(samples)
    return turns


def test_the_blocks_of_the_microphone_become_one_turn_per_utterance_whatever_their_size() -> None:
    samples = recording([300.0, 900.0, 700.0])
    expected = [PITCHES[300.0], PITCHES[900.0], PITCHES[700.0]]
    for block in (7, 160, 480, 4096):
        assert [turn.transcript for turn in listen(samples, block)] == expected, block


def test_the_turns_of_a_listening_session_get_the_right_answers_with_the_wake_word_on() -> None:
    config = VoiceConfig(wake=WakeConfig(enabled=True))
    replies = [process_voice_turn(turn, now=NOW, voice_config=config) for turn in listen(recording([300.0, 500.0, 700.0, 900.0]), 320)]
    names = [reply.intent.name if reply.intent else None for reply in replies]
    # the status needs the wake word (said), a movement without it is not started, a stop is accepted with or without it
    assert names == ["status", "stop", None, "stop"]
    assert replies[1].priority == "safety-stop" and replies[3].priority == "safety-stop"
    assert replies[2].requires_confirmation is False and replies[2].pending_confirmation is None


def test_a_movement_said_with_the_wake_word_waits_for_the_confirmation_of_the_primary_device() -> None:
    config = VoiceConfig(wake=WakeConfig(enabled=True))
    turn = VoiceTurn.from_payload({"requestId": "mic-w", "transcript": "hydra start mission alpha", "locale": "en-US", "confidence": 0.9})
    reply = process_voice_turn(turn, now=NOW, voice_config=config)
    assert reply.intent is not None and reply.intent.name == "start_mission"
    assert reply.requires_confirmation is True and reply.pending_confirmation is not None


def test_an_utterance_the_recognizer_is_unsure_of_does_not_move_anything() -> None:
    recognizer = FakeRecognizer()
    transcript, confidence = recognizer.hear(_tone(0.5, 560.0))  # between two known pitches
    assert confidence < 0.6
    turn = VoiceTurn.from_payload({"requestId": "mic-u", "transcript": "hydra go home", "locale": "en-US", "confidence": confidence})
    reply = process_voice_turn(turn, now=NOW, min_confidence=0.6, voice_config=VoiceConfig(wake=WakeConfig(enabled=True)))
    assert reply.intent is None and reply.requires_confirmation is False and transcript


@dataclass
class FakeSpeaker:
    """Records what it was told to say; a real one would give the text to a text-to-speech engine."""

    spoken: list[AlertReply]

    def play(self, reply: AlertReply) -> None:
        if reply.speak:
            self.spoken.append(reply)


LOCALES = ["en-US", "es-ES", "de-DE", "fr-FR", "it-IT", "ja-JP", "zh-CN", "pt-PT"]


def test_a_verdict_is_spoken_once_per_window_in_each_of_the_eight_languages() -> None:
    for locale in LOCALES:
        speaker, fake = AlertSpeaker(AlertConfig(enabled=True, repeat_seconds=60.0, critical_repeat_seconds=10.0)), FakeSpeaker([])
        events = [
            (0.0, "suspect", "warning"), (5.0, "suspect", "warning"),  # the same verdict inside the window is not repeated
            (6.0, "anomalous", "critical"), (9.0, "anomalous", "critical"),  # a critical one repeats after the shorter window only
            (20.0, "anomalous", "critical"), (30.0, "normal", "info"),  # a good verdict is not an alert
        ]
        for index, (at, verdict, severity) in enumerate(events):
            payload = {"alertId": f"a{index}", "source": "anomaly", "verdict": verdict, "node": "pump-1", "severity": severity, "locale": locale}
            fake.play(speaker.compose(payload, now=at))
        assert [reply.alert_id for reply in fake.spoken] == ["a0", "a2", "a4"], locale
        assert all(reply.text and "pump-1" in reply.text for reply in fake.spoken), locale
        assert {reply.text_language for reply in fake.spoken} == {locale.split("-")[0]}, locale


def test_the_texts_of_one_verdict_differ_between_the_eight_languages() -> None:
    texts = set()
    for locale in LOCALES:
        reply = AlertSpeaker(AlertConfig(enabled=True)).compose({"alertId": "x", "source": "anomaly", "verdict": "anomalous", "node": "n1", "severity": "critical", "locale": locale}, now=0.0)
        texts.add(reply.text)
    assert len(texts) == len(LOCALES)


def test_alerts_off_by_default_say_nothing_and_a_low_severity_is_below_the_threshold() -> None:
    payload = {"alertId": "x", "source": "anomaly", "verdict": "suspect", "node": "n1", "severity": "info", "locale": "en-US"}
    fake = FakeSpeaker([])
    fake.play(AlertSpeaker(AlertConfig()).compose(payload, now=0.0))
    assert fake.spoken == []
    reply = AlertSpeaker(AlertConfig(enabled=True, min_severity="warning")).compose(payload, now=0.0)
    assert reply.speak is False and reply.reason == "below_threshold"
