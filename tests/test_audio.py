# =============================================================================
# HYDRA-UMC-VOICE-UI - tests/test_audio.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
from __future__ import annotations

import math
import wave
from pathlib import Path

import pytest

from hydra_umc_voice_ui.audio import detect_voice_segments, estimate_noise_floor, load_wav, rms_energy

SAMPLE_RATE = 8000


def _write_wav(path: Path, samples: list[int], *, channels: int = 1) -> None:
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(2)
        wav_file.setframerate(SAMPLE_RATE)
        wav_file.writeframes(_pack_int16(samples))


def _pack_int16(samples: list[int]) -> bytes:
    import array

    buffer = array.array("h", samples)
    return buffer.tobytes()


def _silence(num_frames: int) -> list[int]:
    return [0] * num_frames


def _tone(num_frames: int, *, amplitude: int = 10000, frequency: float = 440.0) -> list[int]:
    return [
        int(amplitude * math.sin(2 * math.pi * frequency * i / SAMPLE_RATE))
        for i in range(num_frames)
    ]


def test_load_wav_reads_real_file(tmp_path: Path) -> None:
    path = tmp_path / "clip.wav"
    _write_wav(path, _silence(SAMPLE_RATE))  # 1 second of silence

    clip = load_wav(path)

    assert clip.sample_rate == SAMPLE_RATE
    assert clip.channels == 1
    assert clip.frame_count == SAMPLE_RATE
    assert clip.duration_seconds == 1.0


def test_load_wav_rejects_declared_pcm_larger_than_limit(tmp_path: Path) -> None:
    path = tmp_path / "clip.wav"
    _write_wav(path, _silence(SAMPLE_RATE))

    with pytest.raises(ValueError, match="decoded PCM exceeds 8 bytes"):
        load_wav(path, max_bytes=8)


def test_load_wav_rejects_duration_larger_than_limit(tmp_path: Path) -> None:
    path = tmp_path / "clip.wav"
    _write_wav(path, _silence(SAMPLE_RATE))

    with pytest.raises(ValueError, match="duration exceeds 0.5 seconds"):
        load_wav(path, max_duration_seconds=0.5)


def test_load_wav_rejects_invalid_limits_before_opening_file(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing.wav"
    with pytest.raises(ValueError, match="max_bytes"):
        load_wav(missing_path, max_bytes=0)
    with pytest.raises(ValueError, match="max_duration_seconds"):
        load_wav(missing_path, max_duration_seconds=0)


def test_rms_energy_of_silence_is_zero() -> None:
    assert rms_energy((0, 0, 0, 0)) == 0.0


def test_rms_energy_of_loud_samples_is_high() -> None:
    assert rms_energy((10000, -10000, 10000, -10000)) == 10000.0


def test_detect_voice_segments_finds_real_tone_between_silence(tmp_path: Path) -> None:
    silence_frames = SAMPLE_RATE // 2  # 0.5s
    tone_frames = SAMPLE_RATE  # 1.0s
    samples = _silence(silence_frames) + _tone(tone_frames) + _silence(silence_frames)

    path = tmp_path / "clip.wav"
    _write_wav(path, samples)
    clip = load_wav(path)

    segments = detect_voice_segments(clip, threshold=1000.0)

    assert len(segments) == 1
    segment = segments[0]
    # The tone starts at 0.5s and runs for 1.0s - allow one frame_ms of slack.
    assert 0.45 <= segment.start_seconds <= 0.55
    assert 1.4 <= segment.end_seconds <= 1.6


def test_detect_voice_segments_on_pure_silence_is_empty(tmp_path: Path) -> None:
    path = tmp_path / "silent.wav"
    _write_wav(path, _silence(SAMPLE_RATE))
    clip = load_wav(path)

    assert detect_voice_segments(clip, threshold=1000.0) == []


def _hum(num_frames: int, *, amplitude: int = 800) -> list[int]:
    return _tone(num_frames, amplitude=amplitude, frequency=50.0)


def test_a_constant_hum_above_the_fixed_gate_reads_as_voice_from_start_to_end(tmp_path: Path) -> None:
    hum = _hum(SAMPLE_RATE * 2)
    _write_wav(tmp_path / "hum.wav", hum)
    clip = load_wav(tmp_path / "hum.wav")
    fixed = detect_voice_segments(clip, threshold=500.0)
    assert len(fixed) == 1 and fixed[0].end_seconds - fixed[0].start_seconds > 1.9


def test_a_gate_relative_to_the_noise_ignores_the_hum_and_keeps_the_speech(tmp_path: Path) -> None:
    samples = _hum(SAMPLE_RATE // 2) + _tone(SAMPLE_RATE, amplitude=9000) + _hum(SAMPLE_RATE // 2)
    _write_wav(tmp_path / "speech.wav", samples)
    clip = load_wav(tmp_path / "speech.wav")
    assert estimate_noise_floor(clip) > 400.0
    segments = detect_voice_segments(clip, noise_ratio=3.0)
    assert len(segments) == 1
    assert 0.45 <= segments[0].start_seconds <= 0.55
    assert 1.4 <= segments[0].end_seconds <= 1.6


def test_the_relative_gate_never_falls_below_one_so_silence_is_not_voice(tmp_path: Path) -> None:
    _write_wav(tmp_path / "quiet.wav", _silence(SAMPLE_RATE))
    assert detect_voice_segments(load_wav(tmp_path / "quiet.wav"), noise_ratio=2.0) == []


def test_a_noise_ratio_that_is_not_positive_is_refused(tmp_path: Path) -> None:
    _write_wav(tmp_path / "a.wav", _tone(SAMPLE_RATE // 10))
    with pytest.raises(ValueError):
        detect_voice_segments(load_wav(tmp_path / "a.wav"), noise_ratio=0.0)


# -- block by block ------------------------------------------------------------------------------

from hydra_umc_voice_ui.audio import AudioClip, StreamingVad, detect_voice_segments_streaming, iter_wav_blocks  # noqa: E402


def _speech_pattern() -> list[int]:
    return _silence(2000) + _tone(1500) + _silence(900) + _tone(777) + _silence(333)


@pytest.mark.parametrize("block", [1, 7, 240, 241, 1000, 99999])
def test_streaming_vad_finds_the_same_segments_whatever_the_block_size(block: int) -> None:
    samples = _speech_pattern()
    whole = detect_voice_segments(AudioClip(samples=samples, sample_rate=SAMPLE_RATE, channels=1))
    vad = StreamingVad(SAMPLE_RATE, 1)
    found = []
    for start in range(0, len(samples), block):
        found.extend(vad.feed(samples[start:start + block]))
    found.extend(vad.finish())
    assert found == whole
    assert len(found) == 2


def test_streaming_vad_gives_a_segment_back_as_soon_as_it_ends_and_closes_the_open_one_at_finish() -> None:
    vad = StreamingVad(SAMPLE_RATE, 1)
    assert vad.feed(_silence(2000) + _tone(1500)) == []  # still speaking
    ended = vad.feed(_silence(1000))
    assert len(ended) == 1 and ended[0].start_seconds == pytest.approx(0.25, abs=0.04)
    assert vad.feed(_tone(400)) == []
    tail = vad.finish()
    assert len(tail) == 1 and tail[0].end_seconds == pytest.approx((2000 + 1500 + 1000 + 400) / SAMPLE_RATE)
    assert vad.finish() == []  # started over


def test_streaming_vad_handles_two_channels() -> None:
    mono = _speech_pattern()
    stereo = [value for sample in mono for value in (sample, sample)]
    whole = detect_voice_segments(AudioClip(samples=stereo, sample_rate=SAMPLE_RATE, channels=2))
    vad = StreamingVad(SAMPLE_RATE, 2)
    found = []
    for start in range(0, len(stereo), 501):  # a block that cuts a frame in the middle
        found.extend(vad.feed(stereo[start:start + 501]))
    found.extend(vad.finish())
    assert found == whole


def test_streaming_vad_with_a_noise_ratio_ignores_a_constant_hum() -> None:
    hum = _tone(SAMPLE_RATE * 2, amplitude=900, frequency=50.0)
    plain = StreamingVad(SAMPLE_RATE, 1)
    assert plain.feed(hum) == [] and len(plain.finish()) == 1  # a fixed gate of 500 reads the hum as speech
    relative = StreamingVad(SAMPLE_RATE, 1, noise_ratio=3.0)
    assert relative.feed(hum) + relative.finish() == []
    spoken = StreamingVad(SAMPLE_RATE, 1, noise_ratio=3.0)
    found = spoken.feed(hum + _tone(SAMPLE_RATE, amplitude=9000, frequency=300.0) + hum) + spoken.finish()
    assert len(found) == 1


def test_streaming_vad_rejects_bad_settings() -> None:
    for kwargs in ({"sample_rate": 0}, {"sample_rate": 8000, "channels": 0}, {"sample_rate": 8000, "noise_ratio": 0}):
        with pytest.raises(ValueError):
            StreamingVad(**kwargs)
    with pytest.raises(ValueError):
        StreamingVad(8000, floor_rise=0)


def test_a_wav_file_is_gated_block_by_block_with_the_same_result(tmp_path: Path) -> None:
    path = tmp_path / "speech.wav"
    samples = _speech_pattern()
    _write_wav(path, samples)
    assert detect_voice_segments_streaming(path, block_frames=333) == detect_voice_segments(load_wav(path))
    blocks = list(iter_wav_blocks(path, block_frames=1000))
    assert max(len(block[2]) for block in blocks) <= 1000
    assert sum(len(block[2]) for block in blocks) == len(samples)


def test_iter_wav_blocks_keeps_the_limits_of_load_wav(tmp_path: Path) -> None:
    path = tmp_path / "clip.wav"
    _write_wav(path, _silence(SAMPLE_RATE))
    with pytest.raises(ValueError):
        list(iter_wav_blocks(path, max_bytes=10))
    with pytest.raises(ValueError):
        list(iter_wav_blocks(path, max_duration_seconds=0.5))
    with pytest.raises(ValueError):
        list(iter_wav_blocks(path, block_frames=0))
