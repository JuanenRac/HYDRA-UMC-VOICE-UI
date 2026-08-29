# =============================================================================
# HYDRA-UMC-VOICE-UI - src/hydra_umc_voice_ui/main.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Entry point for HYDRA-UMC-VOICE-UI.

Bare invocation prints identity/version/role, unchanged from the
scaffolding stage. The real v0 work lives behind two subcommands: real
WAV audio analysis + voice-activity detection (see audio.py), and real
rule-based intent/entity parsing over already-transcribed text (see
intent.py). Neither is the Whisper STT / neural TTS pipeline the
README's own roadmap describes - those need a real model dependency and
stay future work.
"""
from __future__ import annotations

import argparse
import sys
import wave
from pathlib import Path

from . import __version__
from .audio import detect_voice_segments, load_wav, rms_energy
from .http_service import create_voice_gateway
from .intent import parse_intent

PROJECT_NAME = "HYDRA-UMC-VOICE-UI"
ROLE = (
    "Voice UI (Hailo-10) - local STT/TTS pipeline for hands-free "
    "robotic mission control."
)


def _print_identity() -> None:
    print(f"{PROJECT_NAME} v{__version__}")
    print(ROLE)


def _run_analyze_audio(path: Path) -> int:
    if not path.is_file():
        print(f"ERROR: file not found: {path}")
        return 1

    try:
        clip = load_wav(path)
    except (wave.Error, EOFError) as error:
        print(f"ERROR: not a valid PCM WAV file: {path} ({error})")
        return 1
    print(f"File: {path.name}")
    print(f"Sample rate: {clip.sample_rate} Hz")
    print(f"Channels: {clip.channels}")
    print(f"Duration: {clip.duration_seconds:.3f} s")
    print(f"RMS energy: {rms_energy(clip.samples):.1f}")

    segments = detect_voice_segments(clip)
    if not segments:
        print("Voice segments: none detected (v0 energy-gate VAD)")
        return 0

    print(f"Voice segments: {len(segments)} detected (v0 energy-gate VAD)")
    for index, segment in enumerate(segments, start=1):
        print(f"  {index}. {segment.start_seconds:.3f}s -> {segment.end_seconds:.3f}s")
    return 0


def _run_parse_intent(text: str) -> int:
    intent = parse_intent(text)
    if intent is None:
        print(f'No matching intent for: "{text}"')
        print("(v0 is a real rule-based parser over a small command vocabulary - an honest miss, not a guess.)")
        return 0

    print(f'Intent: {intent.name}')
    if intent.entities:
        for key, value in intent.entities.items():
            print(f"  {key}: {value}")
    return 0


def _run_serve(host: str, port: int) -> int:
    try:
        gateway = create_voice_gateway(host, port)
    except ValueError as error:
        print(f"ERROR: {error}")
        return 1
    except OSError as error:
        # ThreadingHTTPServer.__init__ does the real bind()/listen() and
        # raises a plain OSError (e.g. the port is already in use) - a
        # real, expected CM5 deployment failure mode, not a bug to trace.
        print(f"ERROR: cannot bind {host}:{port} ({error})")
        return 1
    print(f"{PROJECT_NAME} voice gateway listening on http://{host}:{port}")
    print("POST /v1/voice/turn accepts bounded text only; it never actuates robots.")
    try:
        gateway.serve_forever()
    except KeyboardInterrupt:
        print("Voice gateway stopped.")
    finally:
        gateway.server_close()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hydra-umc-voice-ui", description=ROLE)
    subparsers = parser.add_subparsers(dest="command")

    audio_parser = subparsers.add_parser(
        "analyze-audio", help="Real WAV loading + energy-gate voice-activity detection."
    )
    audio_parser.add_argument("wav_file", type=Path, help="Path to a 16-bit PCM WAV file.")

    intent_parser = subparsers.add_parser(
        "parse-intent", help="Real rule-based intent/entity parsing over transcribed text."
    )
    intent_parser.add_argument("text", help="Already-transcribed text to parse.")

    serve_parser = subparsers.add_parser(
        "serve", help="Run the local authenticated Watch voice-turn gateway.")
    serve_parser.add_argument("--host", default="127.0.0.1", help="Bind host (non-loopback requires HYDRA_UMC_VOICE_UI_TOKEN).")
    serve_parser.add_argument("--port", type=int, default=8090, help="Bind TCP port (default: 8090).")

    return parser


def main(argv: list[str] | None = None) -> int:
    # Real ingested/transcribed content can carry non-ASCII text - the
    # default Windows console codepage (cp1252) can't encode all of it,
    # so reconfigure to UTF-8 with a safe fallback instead of crashing.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "analyze-audio":
        return _run_analyze_audio(args.wav_file)
    if args.command == "parse-intent":
        return _run_parse_intent(args.text)
    if args.command == "serve":
        return _run_serve(args.host, args.port)

    _print_identity()
    return 0


if __name__ == "__main__":
    sys.exit(main())
