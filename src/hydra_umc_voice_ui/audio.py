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
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

DEFAULT_MAX_WAV_BYTES = 16 * 1024 * 1024
DEFAULT_MAX_WAV_DURATION_SECONDS = 300.0


@dataclass(frozen=True)
class AudioClip:
    """Real decoded PCM audio: one int16 sample per channel-interleaved frame."""

    samples: Sequence[int]
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
    return AudioClip(samples=samples, sample_rate=sample_rate, channels=channels)


def rms_energy(samples: Sequence[int]) -> float:
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


def _frame_energies(clip: AudioClip, frame_size: int) -> list[float]:
    energies: list[float] = []
    for frame_index in range(0, clip.frame_count, frame_size):
        start_sample = frame_index * clip.channels
        end_sample = min((frame_index + frame_size) * clip.channels, len(clip.samples))
        energies.append(rms_energy(clip.samples[start_sample:end_sample]))
    return energies


def estimate_noise_floor(clip: AudioClip, *, frame_ms: float = 30.0, percentile: float = 0.1) -> float:
    """The energy below which only `percentile` of the frames of the clip fall: the background noise of the recording."""
    if clip.channels == 0 or clip.sample_rate == 0 or clip.frame_count == 0:
        return 0.0
    energies = sorted(_frame_energies(clip, max(1, int(clip.sample_rate * frame_ms / 1000))))
    return energies[min(len(energies) - 1, int(len(energies) * percentile))]


def detect_voice_segments(
    clip: AudioClip, *, threshold: float = 500.0, frame_ms: float = 30.0, noise_ratio: float | None = None
) -> list[VoiceSegment]:
    """Real energy-gate voice activity detection over mono-summed frames.

    Splits the clip into `frame_ms` windows, computes each window's real
    RMS energy across all channels, and merges consecutive windows above
    the gate into one segment. The gate is the fixed `threshold`, or, when
    `noise_ratio` is given, that many times the background noise of the clip
    (`estimate_noise_floor`) but never less than 1, so a recording with a
    constant hum does not read as speech from start to end. This is a real,
    simple VAD primitive - not the neural VAD a production Whisper pipeline
    would eventually use, but a genuine signal-processing step a real STT
    front-end needs before any transcription can happen.
    """
    if clip.channels == 0 or clip.sample_rate == 0 or clip.frame_count == 0:
        return []
    if noise_ratio is not None:
        if noise_ratio <= 0:
            raise ValueError("noise_ratio must be greater than zero")
        threshold = max(1.0, estimate_noise_floor(clip, frame_ms=frame_ms) * noise_ratio)

    frame_size = max(1, int(clip.sample_rate * frame_ms / 1000))
    segments: list[VoiceSegment] = []
    active_start: float | None = None

    for position, energy in enumerate(_frame_energies(clip, frame_size)):
        window_start_s = position * frame_size / clip.sample_rate
        is_active = energy >= threshold

        if is_active and active_start is None:
            active_start = window_start_s
        elif not is_active and active_start is not None:
            segments.append(VoiceSegment(start_seconds=active_start, end_seconds=window_start_s))
            active_start = None

    if active_start is not None:
        segments.append(VoiceSegment(start_seconds=active_start, end_seconds=clip.duration_seconds))

    return segments


def iter_wav_blocks(path: Path, *, block_frames: int = 4096, max_bytes: int = DEFAULT_MAX_WAV_BYTES,
                    max_duration_seconds: float = DEFAULT_MAX_WAV_DURATION_SECONDS):
    """Yields `(sample_rate, channels, samples)` for a bounded 16-bit PCM WAV, one block of `block_frames` frames at a time.

    The same limits and checks as `load_wav`, but only one block is in memory at once, so a long
    recording can be gated by `StreamingVad` without holding all its samples.
    """
    if block_frames <= 0:
        raise ValueError("block_frames must be positive")
    with wave.open(str(path), "rb") as wav_file:
        channels = wav_file.getnchannels()
        sample_rate = wav_file.getframerate()
        sample_width = wav_file.getsampwidth()
        frame_count = wav_file.getnframes()
        if sample_width != 2:
            raise ValueError(f"only 16-bit PCM WAV is supported (got {sample_width * 8}-bit): {path}")
        if channels <= 0 or sample_rate <= 0:
            raise ValueError(f"invalid WAV channel/sample rate metadata: {path}")
        if frame_count * channels * sample_width > max_bytes:
            raise ValueError(f"WAV decoded PCM exceeds {max_bytes} bytes: {path}")
        if frame_count / sample_rate > max_duration_seconds:
            raise ValueError(f"WAV duration exceeds {max_duration_seconds:g} seconds: {path}")
        while True:
            raw = wav_file.readframes(block_frames)
            if not raw:
                return
            samples = array.array("h")
            samples.frombytes(raw)
            yield sample_rate, channels, samples


class StreamingVad:
    """The energy-gate voice detector of `detect_voice_segments`, fed block by block.

    `feed(samples)` takes any number of interleaved int16 samples (a block does not have to hold a
    whole number of frames) and returns the segments that ended inside it; `finish()` closes the
    segment still open at the end of the audio. With a fixed threshold the segments are exactly those
    `detect_voice_segments` finds over the whole clip, whatever the block sizes. With `noise_ratio` the
    gate is that many times a running estimate of the background (it follows a quieter frame down at
    once and a louder one up slowly), so a constant hum does not read as speech, but the result can
    differ from the whole-clip estimate, which looks at the entire recording.
    """

    def __init__(self, sample_rate: int, channels: int = 1, *, threshold: float = 500.0, frame_ms: float = 30.0,
                 noise_ratio: float | None = None, floor_rise: float = 0.01) -> None:
        if sample_rate <= 0 or channels <= 0:
            raise ValueError("sample_rate and channels must be positive")
        if noise_ratio is not None and noise_ratio <= 0:
            raise ValueError("noise_ratio must be greater than zero")
        if not 0 < floor_rise <= 1:
            raise ValueError("floor_rise must be in (0, 1]")
        self.sample_rate = sample_rate
        self.channels = channels
        self.threshold = threshold
        self.noise_ratio = noise_ratio
        self._floor_rise = floor_rise
        self._frame_size = max(1, int(sample_rate * frame_ms / 1000))
        self._samples_per_frame = self._frame_size * channels
        self._pending = array.array("h")
        self._frames_seen = 0
        self._total_samples = 0
        self._floor: float | None = None
        self._active_start: float | None = None

    @property
    def duration_seconds(self) -> float:
        return (self._total_samples // self.channels) / self.sample_rate

    def _gate(self, energy: float) -> float:
        if self.noise_ratio is None:
            return self.threshold
        if self._floor is None or energy < self._floor:
            self._floor = energy
        else:
            self._floor += (energy - self._floor) * self._floor_rise
        return max(1.0, self._floor * self.noise_ratio)

    def _frame(self, energy: float, out: list[VoiceSegment]) -> None:
        start = self._frames_seen * self._frame_size / self.sample_rate
        self._frames_seen += 1
        active = energy >= self._gate(energy)
        if active and self._active_start is None:
            self._active_start = start
        elif not active and self._active_start is not None:
            out.append(VoiceSegment(start_seconds=self._active_start, end_seconds=start))
            self._active_start = None

    def feed(self, samples: Sequence[int]) -> list[VoiceSegment]:
        out: list[VoiceSegment] = []
        self._pending.extend(samples)
        self._total_samples += len(samples)
        size = self._samples_per_frame
        offset = 0
        while len(self._pending) - offset >= size:
            self._frame(rms_energy(self._pending[offset:offset + size]), out)
            offset += size
        if offset:
            del self._pending[:offset]
        return out

    def finish(self) -> list[VoiceSegment]:
        """Judges the last, shorter frame, closes the open segment at the end of the audio and starts over."""
        out: list[VoiceSegment] = []
        if self._pending:
            self._frame(rms_energy(self._pending), out)
            self._pending = array.array("h")
        if self._active_start is not None:
            out.append(VoiceSegment(start_seconds=self._active_start, end_seconds=self.duration_seconds))
            self._active_start = None
        self._frames_seen = 0
        self._total_samples = 0
        self._floor = None
        return out


def detect_voice_segments_streaming(path: Path, *, threshold: float = 500.0, frame_ms: float = 30.0,
                                    noise_ratio: float | None = None, block_frames: int = 4096) -> list[VoiceSegment]:
    """`detect_voice_segments` over a WAV file read block by block (memory stays one block, not the clip)."""
    vad: StreamingVad | None = None
    segments: list[VoiceSegment] = []
    for sample_rate, channels, samples in iter_wav_blocks(path, block_frames=block_frames):
        if vad is None:
            vad = StreamingVad(sample_rate, channels, threshold=threshold, frame_ms=frame_ms, noise_ratio=noise_ratio)
        segments.extend(vad.feed(samples))
    if vad is not None:
        segments.extend(vad.finish())
    return segments
