# Contributing to HYDRA-UMC-VOICE-UI 🦾

We welcome contributions to the local voice interaction layer of the HYDRA-UMC platform.

## Technology Stack
- **Language**: Python >= 3.10 (see `pyproject.toml`).
- **Hardware target**: Hailo-10 M.2 AI Accelerator (40 TOPS).
- **What's real today**: stdlib-only WAV loading + energy-gate VAD (`audio.py`), a rule-based intent/entity parser (`intent.py`), and a stdlib HTTP voice-turn gateway (`gateway.py`/`http_service.py`). See the README's Key Features for what's implemented versus planned.
- **Planned models** (not yet implemented): Whisper (quantized STT), a TTS engine for spoken responses.

## Guidelines
1. **Model Quantization**: once a real Whisper dependency lands, all variants must be quantized for Hailo-10 to keep sub-second transcription.
2. **Noise Robustness**: All STT improvements must be tested against industrial ambient noise recordings.
3. **Privacy**: Never include a cloud-based STT/TTS fallback. All processing must be 100% offline.
4. **Vocabulary Updates**: When adding new voice commands, extend the real rule table in `intent.py` (the `(name, re.compile(...))` pairs) and add matching cases to `tests/test_intent.py` — there is no separate `dictionary/` file; the vocabulary lives in code.
