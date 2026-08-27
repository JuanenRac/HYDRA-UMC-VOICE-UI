# Contributing to HYDRA-UMC-VOICE-UI 🦾

We welcome contributions to the local voice interaction layer of the HYDRA-UMC platform.

## Technology Stack
- **Language**: Python 3.12.
- **Hardware**: Hailo-10 M.2 AI Accelerator (40 TOPS).
- **Models**: Whisper (Quantized STT), FastSpeech/Tacotron (TTS).
- **Audio**: PyAudio, ALSA.

## Guidelines
1. **Model Quantization**: Ensure all Whisper variants are quantized for Hailo-10 to maintain sub-second transcription.
2. **Noise Robustness**: All STT improvements must be tested against industrial ambient noise recordings.
3. **Privacy**: Never include cloud-based STT/TTS fallback. All processing must be 100% offline.
4. **Dictionary Updates**: When adding new commands, update the `dictionary/` JSON files with appropriate synonyms.
