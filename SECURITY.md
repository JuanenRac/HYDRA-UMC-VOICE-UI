# Security Policy 🔒 (HYDRA-UMC-VOICE-UI)

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.x.x  | ✅ Yes             |

## Reporting a Vulnerability

**CRITICAL: Do not report safety-critical vulnerabilities through public GitHub issues.**

In a voice-controlled industrial system, a security flaw can lead to unauthorized mission activation. This project's real security surface today is the `serve` HTTP gateway (`http_service.py`/`gateway.py`) — its bearer-token check on non-loopback binds, its request-size/JSON validation, and its refusal to actuate any robot from a voice turn. STT command injection, TTS spoofing, and microphone hijacking are relevant to the planned Whisper STT/TTS pipeline once it exists, not to the real code today. If you discover a vulnerability affecting the **voice-turn gateway's authentication or input validation**, a future **STT command injection**, **TTS spoofing**, or **microphone hijacking**:

1. **Email**: Send a detailed report to `electrohobby3d@gmail.com`.
2. **Impact**: Describe if the bug allows bypassing voice authentication, triggering unintended robot actions via audio, or leaking audio data.
3. **Response**: Initial acknowledgment within 48 hours.

We follow a coordinated disclosure policy to ensure hardware safety before public release.
