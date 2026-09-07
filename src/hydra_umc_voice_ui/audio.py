# =============================================================================
# HYDRA-UMC-VOICE-UI - src/hydra_umc_voice_ui/audio.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Real, stdlib-only WAV audio loading and energy-based voice detection.

This is the real audio front-end a future Whisper/Hailo-10 STT step would
consume - PCM decoding and voice-activity detection, not transcription
itself. No numpy/scipy dependency: `wave` + `array` are both stdlib and
sufficient for 16-bit PCM, the format every real recording in this
ecosystem's own test fixtures uses.
"""
from __future__ import annotations

import array
import wave
from dataclasses import dataclass
from pathlib import Path

DEFAULT_MAX_WAV_BYTES = 16 * 1024 * 1024
DEFAULT_MAX_WAV_DURATION_SECONDS = 300.0


@dataclass(frozen=True)
class AudioClip:
    """Real decoded PCM audio: one int16 sample per channel-interleaved frame."""

    samples: tuple[int, ...]
    sample_rate: int
    channels: int

    @property
    def frame_count(self) -> int:
        return len(self.samples) // self.channels if self.channels else 0

    @property
    def duration_seconds(self) -> float:
        if self.sample_rate == 0:
            return 0.0
        return self.frame_count / self.sample_rate


def load_wav(
    path: Path,
    *,
    max_bytes: int = DEFAULT_MAX_WAV_BYTES,
    max_duration_seconds: float = DEFAULT_MAX_WAV_DURATION_SECONDS,
) -> AudioClip:
    """Load a bounded 16-bit PCM WAV file from disk.

    The v0 front-end deliberately returns an in-memory clip because the VAD
    operates over it.  Validate its decoded size and duration from the WAV
    header before reading frames so an accidental recording cannot exhaust a
    constrained CM5 process.  A future streaming STT front-end can replace
    this bounded adapter without weakening the input boundary.
    """
    if max_bytes <= 0:
        raise ValueError("max_bytes must be positive")
    if max_duration_seconds <= 0:
        raise ValueError("max_duration_seconds must be positive")
    with wave.open(str(path), "rb") as wav_file:
        channels = wav_file.getnchannels()
        sample_rate = wav_file.getframerate()
        sample_width = wav_file.getsampwidth()
        frame_count = wav_file.getnframes()

    if sample_width != 2:
        raise ValueError(
            f"only 16-bit PCM WAV is supported (got {sample_width * 8}-bit): {path}"
        )
    if channels <= 0 or sample_rate <= 0:
        raise ValueError(f"invalid WAV channel/sample rate metadata: {path}")

    duration_seconds = frame_count / sample_rate
    decoded_bytes = frame_count * channels * sample_width
    if decoded_bytes > max_bytes:
        raise ValueError(f"WAV decoded PCM exceeds {max_bytes} bytes: {path}")
    if duration_seconds > max_duration_seconds:
        raise ValueError(f"WAV duration exceeds {max_duration_seconds:g} seconds: {path}")

    with wave.open(str(path), "rb") as wav_file:
        raw = wav_file.readframes(frame_count)

    samples = array.array("h")
    samples.frombytes(raw)
    return AudioClip(samples=tuple(samples), sample_rate=sample_rate, channels=channels)


def rms_energy(samples: tuple[int, ...]) -> float:
    """Real root-mean-square energy of a block of int16 samples."""
    if not samples:
        return 0.0
    mean_square = sum(sample * sample for sample in samples) / len(samples)
    return mean_square**0.5


@dataclass(frozen=True)
class VoiceSegment:
    """A real contiguous span of the clip whose energy exceeded the threshold."""

    start_seconds: float
    end_seconds: float


def detect_voice_segments(
    clip: AudioClip, *, threshold: float = 500.0, frame_ms: float = 30.0
) -> list[VoiceSegment]:
    """Real energy-gate voice activity detection over mono-summed frames.

    Splits the clip into `frame_ms` windows, computes each window's real
    RMS energy across all channels, and merges consecutive windows above
    `threshold` into one segment. This is a real, simple VAD primitive -
    not the neural VAD a production Whisper pipeline would eventually use,
    but a genuine signal-processing step a real STT front-end needs before
    any transcription can happen.
    """
    if clip.channels == 0 or clip.sample_rate == 0 or clip.frame_count == 0:
        return []

    frame_size = max(1, int(clip.sample_rate * frame_ms / 1000))
    segments: list[VoiceSegment] = []
    active_start: float | None = None

    for frame_index in range(0, clip.frame_count, frame_size):
        start_sample = frame_index * clip.channels
        end_sample = min((frame_index + frame_size) * clip.channels, len(clip.samples))
        window = clip.samples[start_sample:end_sample]
        is_active = rms_energy(window) >= threshold
        window_start_s = frame_index / clip.sample_rate

        if is_active and active_start is None:
            active_start = window_start_s
        elif not is_active and active_start is not None:
            segments.append(VoiceSegment(start_seconds=active_start, end_seconds=window_start_s))
            active_start = None

    if active_start is not None:
        segments.append(VoiceSegment(start_seconds=active_start, end_seconds=clip.duration_seconds))

    return segments
