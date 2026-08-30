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

## [0.0.9] - Fixed a real version-mirror drift

- **`src/hydra_umc_voice_ui/__init__.py`**'s `__version__` had fallen one
  real build behind `pyproject.toml`/the manifest - running only
  `bump_manifest_version.py` (which only touches its declared
  `native_version.file`, pyproject.toml) without this repo's separate
  `bump_version.py` (the one that keeps `__init__.py` mirrored) leaves
  the two drifting apart. Fixed via the real, intended sequence
  (`bump_version.py` then `bump_manifest_version.py --sync`).

## [0.0.8] - Real ecosystem live-status opt-in

- **`hydra-umc.project.json`** declares its real `service.port` (8090)
  and `health_path` (`/health`) - HYDRA-UMC-SERVER's ecosystem status
  endpoint now does a real HTTP GET against it (expecting 2xx) instead
  of only reporting static manifest metadata. Honest note surfaced while
  doing this across the ecosystem: this default port (8090) is identical
  to HYDRA-UMC-JOB-DISPATCHER's own default - not evaluated here whether
  both are ever expected to run on the same host; flagging it as a real
  fact worth checking before both are deployed together, not fixing it
  as part of this manifest-only change.

## [0.0.7] - Clean CLI errors for two unhandled real-input failures

### Fixed
- **`analyze-audio` on a corrupt/invalid WAV file** (`main.py`'s
  `_run_analyze_audio()`) - `audio.py`'s `load_wav()` opens the file with
  the stdlib `wave` module, which raises `wave.Error` (or `EOFError` on a
  truncated header) for anything that isn't a valid PCM WAV. Neither is an
  `OSError` subclass, so neither was caught anywhere in the call chain -
  a real corrupt recording (once a real microphone starts producing
  files, not just this repo's own hand-written test fixtures) surfaced as
  a raw traceback instead of the same clean `ERROR: ...` + exit code 1
  this function already used for a missing file.
- **`serve` on a port already in use** (`main.py`'s `_run_serve()`) - only
  `ValueError` (the missing-token-on-non-loopback-bind case) was caught
  around `create_voice_gateway()`. `ThreadingHTTPServer.__init__` does the
  real `bind()`/`listen()` and raises a plain `OSError` when the port is
  already taken; unhandled, that showed up as a raw Python traceback in
  the CM5 systemd (`Restart=on-failure`) logs instead of a diagnosable
  error. Now caught alongside the existing `ValueError` handling and
  reported the same way.
- Both were found in a live ecosystem bug audit, not from a user report.

### Added
- 2 new regression tests (`test_cli.py`) = 32 total: `analyze-audio`
  against a real invalid WAV file (plain text saved with a `.wav`
  extension) asserting a clean error and exit code 1 instead of a
  traceback, and `serve` started against a port a raw socket already has
  bound and listening, asserting the same clean failure instead of one.

## [0.0.6] - Ambiguity-aware intent classification, real text normalization

### Added

- **Real intent normalization** (`intent.py`'s `normalize_text()`) - Unicode NFKC (collapses compatibility forms a real speech-to-text transcript can emit, e.g. full-width Latin letters, to their ordinary ASCII equivalent), punctuation-noise stripping, and common filler-phrase removal ("please", "could you", ...), applied before classification so a transcript that's semantically identical to a known command is never treated as an honest non-match just because of how it was encoded or phrased.
- **Real ambiguous-command detection** (`intent.py`'s `classify_intent()`/`IntentClassification`, new) - checks every rule (not first-match-wins like the existing `parse_intent()`, left untouched) and reports every one that genuinely matches. `gateway.py`'s `process_voice_turn()` now uses it: a real transcript matching more than one known command (e.g. one containing both "stop" and "status") gets a real, distinct clarification reply instead of being silently resolved to whichever rule happens to be declared first - the exact failure mode this gateway exists to prevent for a real motion command.
- 10 new tests (`test_intent.py`, `test_gateway.py`) = 30 total, including a concrete ambiguous transcript, real NFKC full-width-Unicode normalization, and the gateway's new end-to-end ambiguous-turn rejection. `parse_intent()` and the existing motion-confirmation policy (`requiresConfirmation`, already real) are unchanged - this is a purely additive safety improvement.

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
