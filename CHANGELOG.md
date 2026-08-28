# Changelog: HYDRA-UMC-VOICE-UI 🎙️

All notable changes to this project will be documented in this file. The
version number follows this ecosystem's "odometer" scheme: PATCH +1 on
every real build, rolling into MINOR past 9 (`0.0.9` -> `0.1.0`); MAJOR is
bumped manually only. See `bump_version.py`.

## [Unreleased]
### Added
- `systemd/hydra-umc-voice-ui.service` and `deploy/voice-ui.env.example` - a
  loopback-only CM5 service boundary. HYDRA-UMC-SERVER owns the matching token
  and is the only production caller; the gateway still receives recognised
  text only and never actuates a robot.
- `gateway.py` - bounded `voice_turn` validation and a deterministic,
  non-actuating policy that translates the existing intent parser output into
  Watch-compatible `assistant_reply` messages. Motion-related requests are
  explicitly marked `requiresConfirmation`; no request controls a robot.
- `http_service.py` and `serve` - a stdlib HTTP gateway with `GET /health`
  and authenticated `POST /v1/voice/turn`. Binding beyond localhost refuses
  to start unless `HYDRA_UMC_VOICE_UI_TOKEN` is provided.
- `docs/WATCH_VOICE_GATEWAY.md` and gateway contract tests, including a real
  local HTTP request that proves an absent Bearer token is rejected.

## [0.0.5] - Real v0 audio front-end + rule-based intent parsing
### Added
- `audio.py` - real, stdlib-only 16-bit PCM WAV loading (`wave` + `array`,
  no numpy) and energy-gate voice-activity detection
  (`detect_voice_segments()`): splits a clip into real frames, computes
  each frame's real RMS energy, and merges consecutive frames above a
  threshold into voice segments. A real signal-processing primitive a
  future Whisper/Hailo-10 STT step would consume - not transcription
  itself.
- `intent.py` - a real, rule-based intent/entity parser
  (`parse_intent()`) over a small real voice-command vocabulary
  (`start mission [<id>]`, `stop`/`halt`/`abort`, `status [of robot
  <id>]`, `go home`). Honestly rule-based, not a trained NLU model - the
  same reasoning as the sibling HYDRA-UMC-DOCS-QA's real TF-IDF index
  instead of an embedding model: a real, testable kernel today that a
  future ML-based classifier can replace behind the same
  `parse_intent()` contract. Text outside the rule set returns `None`,
  an honest miss, never a guessed intent.
- `main.py` - two new subcommands: `analyze-audio <file.wav>` (prints
  real sample rate/channels/duration/RMS energy/detected voice
  segments) and `parse-intent "<text>"` (prints the real matched intent
  + entities, or an honest no-match). Bare invocation is unchanged:
  identity/version/role.
- 16 new real tests (`tests/`) - real WAV fixtures written via `wave`
  (silence and a real sine tone), VAD correctness (a tone between two
  silent spans is detected as exactly one segment, pure silence detects
  none), intent-parsing coverage for every rule plus an unmatched-text
  case, and a real end-to-end CLI round-trip for both subcommands.

### Fixed
- Proactively reconfigures `stdout`/`stderr` to UTF-8 with a safe
  replace-on-error fallback in `main()`, before printing anything -
  applied up front after the same real bug (`UnicodeEncodeError` on a
  Windows `cp1252` console) was found and fixed live in the sibling
  HYDRA-UMC-DOCS-QA this same session.

## [0.0.3]
### Added
- Copyright/license header on every source file and build/run script.
- `CHANGELOG.md` (this file).
- Extended documentation across `README.md` and its 4 translations:
  advanced technical/architecture section, detailed build/run
  troubleshooting, and a full "Related Projects" section.

### Changed
- Inline comments explaining the *why* behind non-obvious decisions
  (versioning scheme, src-layout, why this child has no hardware/
  firmware/os/models of its own).

## [0.0.0]
### Added
- Initial Python scaffolding: `pyproject.toml` (setuptools, src-layout),
  `src/hydra_umc_voice_ui/__init__.py` + `main.py` (real entry point -
  prints identity/version/role, exits 0).
- `bump_version.py` - odometer-style version bump applied to
  `pyproject.toml` and mirrored into `__init__.py`.
- `build.sh` / `build.bat` - create/activate a venv, install the package
  editable, verify it compiles and imports.
- `run.sh` / `run.bat` - run the entry point.
