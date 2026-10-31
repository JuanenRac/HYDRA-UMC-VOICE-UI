<!-- =============================================================================
HYDRA-UMC-VOICE-UI - Local speech-to-action front end
Copyright (C) JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE
============================================================================= -->

<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-VOICE-UI banner" width="100%">
</p>

# 🎙️ HYDRA-UMC-VOICE-UI

<p align="center">🇺🇸 <b>English</b> | <a href="README_spa.md">🇪🇸 Español</a> | <a href="README_fra.md">🇫🇷 Français</a> | <a href="README_ita.md">🇮🇹 Italiano</a> | <a href="README_deu.md">🇩🇪 Deutsch</a> | <a href="README_zho.md">🇨🇳 简体中文</a> | <a href="README_jpn.md">🇯🇵 日本語</a> | <a href="README_por.md">🇵🇹 Português</a></p>

### 🔊 Local Hardware-Accelerated Speech-to-Action Pipeline

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL 3.0 or later">
  <img src="https://img.shields.io/badge/STT-Whisper%20Local-FF6F00.svg" alt="STT">
  <img src="https://img.shields.io/badge/Platform-Hailo--10-green.svg" alt="Platform">
  <img src="https://img.shields.io/badge/Tests-255%20passing-2ea44f.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Version-0.2.0-0f6cbd.svg" alt="Version">
  <img src="https://img.shields.io/badge/Maturity-functional-0F6CBD.svg" alt="Maturity">
</p>

---

> **Safety and security status:** this ecosystem is not a certified safety system. There is no hardware E-STOP path, no firmware-enforced limits or interlocks and no verified motion command yet; firmware images are checked with CRC-32 and an Ed25519 signature, and a release build refuses the published development keys (the tool heads and expansion boards behind the relay still run URTC bootloaders, which take a shared-key HMAC-SHA256 instead of a signature); TLS and mutual TLS are optional and off by default; no custom board has been populated or tested yet. Read the [security baseline](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/SECURITY_BASELINE.md) and the [threat model](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/THREAT_MODEL.md) before relying on any statement here for the safety of a person.

---

## 📋 At a glance

| | |
|---|---|
| Version | `0.2.0` |
| Maturity | Functional |
| Tests | 255 (`python -m pytest -q tests`) |
| Stack | Python / Rule-based intent parser / Energy-gate VAD |
| Target | The Raspberry Pi CM5 of a HYDRA-UMC cell |
| On real hardware | Not yet: no run on real hardware is recorded for this version |

**Jump to:** [Overview](#-overview) · [Architecture](#-architecture) · [Quick start](#-quick-start) · [Testing](#-testing) · [Repository Structure](#-repository-structure) · [Related Projects](#-related-projects)

## 🚦 Project status

Each line is one part of this repository and the light says how far it is today. It is written from what the repository can show (tests, builds, runs), not from what is planned.

🟢 Done and verified · 🟡 Works, with known limits · 🟠 Partly done or not verified yet · 🔴 Not done or not working

| Area | State | What it means here |
|---|---|---|
| Software | 🟡 | Works for its main purpose; the honesty check above lists what is still missing |
| Tests | 🟢 | 255 automated tests, run on every change |
| Real hardware | 🔴 | Not yet: no run on real hardware is recorded for this version |
| Documentation | 🟢 | README in eight languages, checked against the manifest on every change |

## 🎯 Overview

**HYDRA-UMC-VOICE-UI** is the local voice interaction layer for the HYDRA-UMC ecosystem. It provides a high-performance STT (Speech-to-Text) and TTS (Text-to-Speech) pipeline accelerated by the Hailo-10 NPU.

It allows operators to control robotic missions, query system status, and receive audio feedback without any cloud connectivity, ensuring maximum privacy and zero latency.

### Key Features:
* 🎧 **Audio Front-End (v0):** Real, stdlib-only WAV loading and energy-gate voice-activity detection. *(implemented as a real signal-processing primitive - not transcription itself; see Build & Release below)*
* 🎙️ **Edge STT:** Quantized Whisper models for near-instant speech transcription. *(planned - needs a real model dependency)*
* 📢 **Natural TTS:** High-quality voice synthesis for system alerts and status reports. *(planned)*
* 🧠 **NLU Parser (v0):** Real rule-based intent/entity extraction from recognized text for the Semantic Planner. *(implemented as regex rules over a small real command vocabulary - not a trained ML model; see Build & Release below)*
* 🔀 **Ambiguity-Aware Classification:** `classify_intent()` normalizes text (Unicode NFKC, filler/punctuation stripping) and rejects a transcript that genuinely matches more than one known command instead of silently guessing one. *(implemented; used by the Watch voice gateway below)*
* 🔏 **Signed, single-use confirmations (v0):** the `confirmationToken` that confirms a stop, a mission start or a go-home is signed with HMAC-SHA256 under a server key (`HYDRA_UMC_VOICE_UI_CONFIRM_SECRET`, at least 16 characters; without it a random key is made per process), carries a random nonce, and is accepted once: a second use of the same token, a token for another intent assembled by hand, or one signed with another key is refused as `invalid`. Before, the token was a SHA-256 prefix of its own content with no secret, so anyone who knew the format could build a valid confirmation, and a valid one could be replayed during its 30 seconds. The OS installer generates the key with the other device secrets. *(implemented)*
* 🛑 **A spoken stop is never held back (server setting):** by default a stop request is answered at once, with no confirmation token and `priority: safety-stop` so a consumer can turn it into a controlled stop (it never replaces the physical E-STOP); starting a movement is still confirmed. `HYDRA_UMC_VOICE_UI_STOP_REQUIRES_CONFIRMATION=1` brings the confirmation of a stop back. *(implemented)*
* 🎚️ **Risk level of each spoken action (a file):** a status request is informative and a stop is answered at once; starting a mission and going home are movements and always need a confirmation. The table is read from `HYDRA_UMC_VOICE_UI_RISK_FILE` (default `/etc/hydra-umc/voice-ui-risk.json`, example in `deploy/voice-ui-risk.json.example`) and can only make the default stricter: an entry that lowers an action is ignored, and a missing or broken file leaves the default.
* 🔏 **A confirmation is for the person who asked, and a confirmed result can be verified:** a turn may name its `subject` (the signed-in user that HYDRA-UMC-SERVER relays it for); the signed confirmation token carries it and confirms only for that same subject (a refusal does not use the token up). A confirmed result also carries `subject`, `confirmedAtUtc` and the one-use `nonce`, and, when `HYDRA_UMC_VOICE_UI_RESULT_KEY` (16 characters or more, the same value HYDRA-UMC-SERVER holds) is set, an HMAC-SHA256 `signature` the server checks before it believes the result. `HYDRA_UMC_VOICE_UI_REQUIRE_SUBJECT=1` also refuses a turn or a confirmation that names nobody (off by default). *(implemented)*
* 🙈 **The reply does not repeat what was said (server setting):** by default the interpretation of a reply lists only the rules that matched; `HYDRA_UMC_VOICE_UI_INCLUDE_HEARD_TEXT=1` adds the transcript (`heardText`, `normalizedText`), which is personal data. Limits: the rules understand English only, and the `locale` of a turn is checked but not used. The Server can also set it (and the minimum confidence) for every turn from its Server Admin screen; the environment of this service wins over the Server.
* 🛡️ **Noise Cancellation:** Optimized for industrial environments with high ambient noise. *(planned)*
* 👨‍👩‍👧 **Cognitive AI Node Child:** Runs as one of four sibling services
  under [HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)
  (alongside VLA-Engine, Semantic-Planner and Docs-QA), sharing its
  parent's HydraOS image and model weights instead of keeping its own
  copies.

## 🧩 Role in HYDRA-UMC

**HYDRA-UMC-VOICE-UI** is the voice front end of the cognitive node: it detects voice in a WAV file, parses already-recognised text into an intent with rules, and offers a bounded HTTP gateway for the watch flow that asks for a confirmation before anything is handed on. It does not recognise speech yet and never sends a physical command.

## 🏛️ Architecture

<p align="center">
  <img src="images/architecture.svg" alt="HYDRA-UMC-VOICE-UI architecture" width="100%">
</p>

<details>
<summary>Text version of the diagram (Mermaid)</summary>

```mermaid
flowchart LR
    MIC["Microphone Input"] --> STT["Whisper STT (Hailo-10)"]
    STT --> NLU["Semantic Intent Parser"]
    NLU --> LOGIC["Cognitive Node Logic"]
    LOGIC --> TTS["TTS Engine"]
    TTS --> SPK["Speaker Output"]
```

</details>

### ARCHITECTURE & DESIGN DECISIONS

This repository is a **child** of the Cognitive AI Node family - its
parent, [HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE),
owns the shared HydraOS image and quantized model weights, and wires this
service into `docker-compose.yml` alongside its three siblings
(VLA-Engine, Semantic-Planner, Docs-QA):

* **Why this child has no hardware/firmware/`os/`/`models/` of its
  own.** It runs entirely on the CM5 + Hailo-10 M.2 module already owned
  by the parent - keeping model weights and the HydraOS image
  centralized in one place avoids four divergent multi-gigabyte copies
  across the family.
* **Why a `src/` layout.** Keeps the installable package
  (`hydra_umc_voice_ui`) separate from repo-root tooling
  (`bump_version.py`), matching the layout used by every other Python
  project across the ecosystem.
* **Why bare invocation only prints identity/version/role.** That stays
  a thin, unchanged scaffolding check; the real v0 work lives behind its
  subcommands instead - `analyze-audio` (real WAV loading + energy-gate
  VAD, `audio.py`), `parse-intent` (real rule-based intent/entity
  parsing, `intent.py`), and `serve` (the real authenticated Watch
  voice-turn gateway, `http_service.py`/`gateway.py`). None of that is
  the Whisper STT / neural TTS pipeline this README's own roadmap
  describes - that still needs a real model dependency this environment
  doesn't have.
* **How this fits the rest of the ecosystem.** This service is the
  hands-free entry point into the whole Cognitive AI Node: recognized
  intent flows to its sibling HYDRA-UMC-SEMANTIC-PLANNER, and it acts as
  a voice-control surface alongside HYDRA-UMC-STUDIO and HYDRA-UMC-DSI.
* **Why `audio.py` uses `wave`/`array` instead of numpy.** 16-bit PCM
  decoding and a real energy-gate VAD need nothing beyond what the
  standard library already provides - keeping v0 dependency-free means
  the real audio front-end works anywhere Python does, before any
  Hailo-10-specific STT dependency is even installed.
* **Why `intent.py` is real regex rules, not a trained NLU model.**
  A small, real command vocabulary (start/stop/status/go home) is fully
  and honestly covered by rules today - the same reasoning as the
  sibling HYDRA-UMC-DOCS-QA's real TF-IDF index instead of an embedding
  model: a real, testable kernel now that a future ML-based classifier
  can replace behind the same `parse_intent()` contract, once recognized
  speech needs to cover more than this v0 vocabulary.
* **Why unmatched audio/text returns an honest miss, not a guess.**
  `detect_voice_segments()` returns an empty list for silence, and
  `parse_intent()` returns `None` for text outside its rule set - v0 has
  no model to fall back on, so it never fabricates a segment or an
  intent it didn't actually detect.
* **Why the Watch gateway uses `classify_intent()`, not the legacy
  `parse_intent()`.** `parse_intent()` stays first-match-wins (unchanged,
  still tested as-is) for existing callers, but a real transcript that
  genuinely matches more than one known command (e.g. containing both
  "stop" and "status") is a real, safety-relevant ambiguity for a
  gateway whose whole job is deciding whether a motion command needs
  confirmation - `classify_intent()` checks every rule and reports a
  real, distinct ambiguous case instead of silently resolving to
  whichever rule happens to be declared first.
* **Why `normalize_text()` applies Unicode NFKC before matching.** Some
  speech-to-text pipelines emit full-width Latin letters and other
  compatibility Unicode forms - distinct code points from ordinary
  ASCII, and therefore not "the word" as far as a `\b...\b` regex is
  concerned. NFKC collapses them to their ordinary equivalent first, so
  a command that's semantically identical to a known rule is never
  treated as an honest non-match just because of how it was encoded.

### WATCH VOICE GATEWAY (v0)

`python -m hydra_umc_voice_ui.main serve` exposes a deliberately bounded local HTTP gateway for a paired HYDRA-UMC-WATCH integration: `GET /health`, `POST /v1/voice/turn` and `POST /v1/voice/confirm`. The gateway validates the typed `voice_turn` payload, uses the existing deterministic intent parser and returns an `assistant_reply`; it does not control robot hardware.

Loopback development may run without a token. A non-loopback bind requires `HYDRA_UMC_VOICE_UI_TOKEN` and a matching `Authorization: Bearer` header. Raw audio is never sent through this API, and motion-related intents always return `requiresConfirmation: true` along with a real, bounded `confirmationToken` - the Watch client echoes it back to `POST /v1/voice/confirm`, which reports `confirmed`/`expired`/`invalid` (never a bare boolean) without itself dispatching anything. See the confirmation section of [WATCH_VOICE_GATEWAY.md](docs/WATCH_VOICE_GATEWAY.md) below for the full contract.

A transcript that genuinely matches more than one known command is rejected with a real, distinct reply instead of being silently resolved to one interpretation:

```json
// POST /v1/voice/turn
{"type": "voice_turn", "requestId": "watch-voice-001", "transcript": "stop the status check", "locale": "en-US"}

// -> {"type":"assistant_reply","requestId":"watch-voice-001","text":"That request matched more than one action (status, stop). Please rephrase it more specifically.","level":"ATTENTION","speak":true,"requiresConfirmation":false,"visualState":"clarification","interpretation":{"heardText":"stop the status check","normalizedText":"stop the status check","matchedRules":["status","stop"]}}
```

See [WATCH_VOICE_GATEWAY.md](docs/WATCH_VOICE_GATEWAY.md) for the full request contract and deployment boundary, and [CLI_REFERENCE.md](docs/CLI_REFERENCE.md) for every real `analyze-audio`/`parse-intent`/`serve` example captured from the installed CLI.

## 🚀 Quick start

Requires Python 3.10 or newer.

```bash
./build.sh  # Linux, macOS (build.bat on Windows)
./run.sh analyze-audio clip.wav
./run.sh parse-intent "stop robot one"
./run.sh serve --port 8091
```

## 🧪 Testing

255 automated tests run with `python -m pytest -q tests`. They need no hardware and nothing outside this machine.

The CI runs `HYDRA_UMC_CI=1 python tools/ci_validate.py`, which checks the manifest, the documents, the eight READMEs and the pictures.

## 🏗️ Build & Release

Requires Python >= 3.10.

```bash
# Linux / macOS / Git Bash
./build.sh   # creates .venv, installs the package (editable), verifies import
./run.sh     # runs the entry point

# Windows (cmd)
build.bat
run.bat
```

`build.sh`/`build.bat` never change the version (only `python tools/hydra_project_tool.py bump` raises it), and run the real test suite
(`pytest tests/`). Expected output of a bare `run.sh`:

```text
HYDRA-UMC-VOICE-UI v0.2.0
Voice UI (Hailo-10) - local STT/TTS pipeline for hands-free robotic mission control.
```

The real subcommands analyze a WAV file or parse already-transcribed
text:

```bash
./run.sh analyze-audio recordings/command.wav
./run.sh parse-intent "start mission alpha"

# Windows
run.bat analyze-audio recordings\command.wav
run.bat parse-intent "status of robot 3"
```

### 🩺 Troubleshooting

* **`python: command not found` / build fails at step 1.** Requires
  Python >= 3.10 on `PATH`. On Windows, install from
  [python.org](https://python.org) and make sure "Add to PATH" was
  checked during setup; `python3` is the usual name on Linux/macOS.
* **`build.sh` fails to activate the venv.** `python3 -m venv .venv`
  lays out the activate script differently per platform:
  `.venv/bin/activate` on Linux/macOS, `.venv/Scripts/activate` on
  Windows (also true for a Windows Python venv used from Git Bash).
  `build.sh` already checks both paths - if it still fails, delete
  `.venv/` and re-run `./build.sh` to rebuild it from scratch.
* **`pip install -e .` fails.** Usually a stale `.venv/`. Delete the
  `.venv/` folder and re-run `./build.sh`/`build.bat` to recreate it.
* **`import OK` never prints.** Means `python -c "import
  hydra_umc_voice_ui"` itself failed - re-run with the venv active to
  see the real traceback.

## 📂 Repository Structure

<p align="center">
  <img src="images/repository-structure.svg" alt="Repository structure of HYDRA-UMC-VOICE-UI" width="100%">
</p>

<details>
<summary>Text version of the tree</summary>

```text
HYDRA-UMC-VOICE-UI/
├── src/hydra_umc_voice_ui/          source code
│   ├── __init__.py                  Package description and version
│   ├── audio.py                     Real WAV loading + energy-gate voice-activity detection
│   ├── intent.py                    Real rule-based intent/entity parser + ambiguity-aware classify_intent()
│   ├── gateway.py                   Bounded text-to-intent gateway shared by the Watch cognitive flow
│   ├── http_service.py              Small stdlib HTTP boundary for the Watch-to-cognitive voice path
│   ├── main.py                      Entry point + real `analyze-audio`/`parse-intent` subcommands
│   └── ratelimit.py                 A sliding-window limit of requests per client address (so one client cannot fill the confirmation list)
├── tests/                           Real tests: WAV fixtures, VAD, intent rules, gateway, end-to-end CLI
├── docs/                            Documentation and command catalog
├── images/                          Media and diagrams
├── deploy/
├── systemd/                         service unit
├── tools/                           project tools and CI checks
├── .github/                         CI workflow and issue templates
├── Dockerfile                       Minimal container image for the authenticated HTTP gateway (non-root)
├── pyproject.toml                   Package metadata (version raised only by the explicit bump command)
├── bump_version.py                  explicit version bump
├── bump_manifest_version.py         Syncs hydra-umc.project.json's version to the native one (--sync)
├── build.sh / build.bat             Create venv, install (with dev extras), verify import, run tests
├── build-test.sh / build-test.bat   Non-mutating wrapper for tools/build_test.py (no version/manifest/CHANGELOG changes)
├── run.sh / run.bat                 Run the entry point (forwards args, e.g. `analyze-audio`)
├── CHANGELOG.md                     what changed in each version
├── hydra-umc.project.json           manifest: version, maturity, family
└── test.sh                          runs the tests
```

</details>

## 🗺️ Roadmap & Known limits

**Known limits today**

* **Phase 1:** VLA engine deployment and multi-modal input processing on Hailo-10.
* **Phase 2:** Semantic planner integration with swarm behavioral models and long-term memory.
* **Phase 3:** Voice UI low-latency local execution and industrial noise cancellation.
* **Phase 4:** Multi-lingual support (English, Spanish, German, French) and full integration with Dashboard AI.

## 🌍 Languages

This README and the documents of the repository exist in eight languages: English, Spanish, German, French, Italian, Japanese, Chinese and Portuguese (Portugal). They are written together and checked in the CI so that the eight files have the same sections and the same links. This repository has no screen or message catalogue of its own, so there are no interface strings to translate.

## 🔗 Related Projects

This project is part of the HYDRA-UMC robotics ecosystem by the same author (JuanenRac / Electro Hobby 3D). Worth knowing about, since a request might actually be about one of these rather than this repository.

**Parent Project**
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — integration hub for the Hailo-10 cognitive pipeline (LLM/VLA/voice orchestration); the parent this repo is one specific stage or consumer of, within its own cognitive pipeline.

**Sibling Projects** — the other stages/consumers of HYDRA-UMC-COGNITIVE-NODE's own Hailo-10 cognitive pipeline
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — real rule-based task decomposition and semantic error recovery over MCU error codes.
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — real action-token encoding/decoding and trajectory generation for a Vision-Language-Action model.
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — real stdlib-only TF-IDF document search over this ecosystem's own Markdown docs.
- **[HYDRA-UMC-LOCAL-TECHNICIAN](https://github.com/JuanenRac/HYDRA-UMC-LOCAL-TECHNICIAN)** — local, policy-gated AI maintenance technician for the ecosystem itself - observes, diagnoses and proposes fixes; the two highest risk levels are deliberately not implemented yet.

**Directly Related**
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — web control dashboard with real-time multi-robot 3D visualization; another voice-control surface for the ecosystem, alongside this service.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — native touch UI for the onboard 7" DSI touchscreen, embedded on the CM5 itself; another voice-control surface for the ecosystem, alongside this service.

**Also Part of the Ecosystem**

*Core Hardware & Platform*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — the robot-arm motherboard design: CM5 host + dual-core STM32H745, meant to orchestrate up to 8 tool arms over CAN-OTA/SPI-OTA (firmware at an early stage; no populated board yet).
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — reproducible Raspberry Pi OS product layer for the CM5: read-only agent, validated config/profiles, WiFi first-contact provisioning.
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — the shared JSON-Schema contract and software job-gate boundary every bridge validates its commands against (not a certified safety function).
- **[HYDRA-UMC-CONNECTOR-HUB](https://github.com/JuanenRac/HYDRA-UMC-CONNECTOR-HUB)** — declarative adapter-manifest registry and validator for external-machine connectors; extends the SDK's own contract idea to external machines without replacing the industrial-gateway projects.

*Core Backend & Clients*
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — the real headless backend (REST/WebSocket) every control client actually talks to.
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — desktop (PySide6) swarm command center for multiple servers at once, packaged as a standalone executable.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — native Android control app with biometric login and a paired Wear OS companion.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — iOS/iPadOS control app (Flutter) with real-time WebSocket sync.
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — desktop graphical URDF creator/editor that pushes finished models into STUDIO's own catalog.
- **[HYDRA-UMC-EDITOR-STL](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-STL)** — desktop STL model editor, transforming/replacing/removing/adding real parts in the same model catalog HYDRA-UMC-EDITOR-URDF also edits.
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — coordination boundary for AGV/AMR fleets via a VDA 5050 MQTT publisher (tested against an emulated fleet only).
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — high-level CNC-cell coordinator with GRBL status/control-byte access (tested against an emulator only).
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — coordination boundary for legged/humanoid droids, with a Boston Dynamics Spot command sender (tested against an emulator only).
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — laser-cell coordinator reading 3 key/enclosure/interlock GPIO signals (tested against a fake chip only; it cannot arm or fire a laser).
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — safe high-level board-flow coordinator for OpenPnP pick-and-place.
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — safe coordination boundary for Moonraker/Klipper 3D printers, with real gated job commands.
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — coordinator with a lazily imported rclpy ROS 2 transport (not yet run against a ROS 2 installation).
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — coordination boundary for camera-equipped UAVs, with a MAVLink command sender (tested against an emulator only).

*URTC Tool Platform*
- **[URTC](https://github.com/JuanenRac/URTC)** — firmware for the physical Universal Robot Tool Controller PCB, 25+ tool profiles over CAN bus.
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — desktop GUI flashing tool for URTC boards, CAN-OTA plus full-chip SWD/JTAG.
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** — desktop live CAN-bus diagnostic tool for URTC boards, one panel per tool profile.
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — browser-based alternative to URTC-TESTER via the Web Serial API, no local install needed.
- **[URTC-GATEWAY](https://github.com/JuanenRac/URTC-GATEWAY)** — gateway in front of the URTC CAN bus: an allowed list of identifiers, a rate limit and a session key; software tested on a computer, not yet on a real bus.

*Vision AI Node (Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — integration hub for the Hailo-8 vision pipeline, with a real per-stage hardware-readiness check.
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — real compiled-model registry with Hailo-architecture/checksum safe-load verification.
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — real GStreamer pipeline + MediaMTX config generator with a real HailoRT integration boundary.
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — Position-Based Visual Servoing correction law with authorisation gated on the zone state; no camera pose estimation yet.
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — v0 zone-breach, calibration-freshness and E-STOP-request logic that takes object positions from a file; no detector feeds it and no physical E-STOP is wired to it yet.

*Orchestration & Swarm*
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — integration hub with a real gRPC/Protobuf health-report contract and mission state machine.
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — real priority-based job queue with deduplication, over a real HTTP API.
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — real gRPC-based fleet health watchdog with retry/backoff and identity-mismatch detection.
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — real RRT-based 3D path planner with real obstacle/workspace collision validation.
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — real CRDT LWW-Element-Map state sync, property-tested for multi-cell convergence.

*Digital Twin & Simulation*
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — integration hub for the digital-twin engine, with a real version-compatibility sync contract.
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — hardware-in-the-loop router with a software collision interlock between simulation and real hardware (tested without real hardware).
- **[HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)** — real forward kinematics and joint-limit validation over a real URDF subset.
- **[HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)** — real procedural 2D scene generator with YOLO/COCO annotation export.

*Data & Analytics*
- **[HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE)** — real sqlite3-backed time-series store with a real ingest/query HTTP API.
- **[HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR)** — real FFT + statistical baseline anomaly detector with drift monitoring.
- **[HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)** — real OEE/availability calculation over DATALAKE history, with reproducible CSV export.
- **[HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR)** — real CAN/WebSocket ingestion pipeline into DATALAKE, with sequence deduplication.

*Industrial Gateway*
- **[HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)** — integration hub relaying to industrial protocols, with a real command allowlist/backpressure layer.
- **[HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER)** — real OPC-UA address space, verified with a real binary-protocol client session.
- **[HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER)** — real MQTT broker with optional per-client authentication and topic ACLs.
- **[HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)** — real MTConnect `/probe` and `/current` XML endpoints with degraded-mode output.

*Complementary Tools & Ecosystem Operations*
- **[HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)** — Smart Summaries and Anomaly Highlighting panels over DATALAKE/ANOMALY-DETECTOR, with an honest statistical fallback.
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — fleet CLI with a real, stable exit-code contract, a genuine live client of HYDRA-UMC-SERVER's own API.
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — WearOS companion app with haptic alert patterns and a paired-phone voice relay (not yet run on a physical watch).
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — firmware for a board-mounting rack with real tool-ID decoding and Smart Idle pre-heating logic.
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — firmware plus a real Python vision companion for a thermal/RGB inspection tool head.
- **[HYDRA-UMC-UPDATER](https://github.com/JuanenRac/HYDRA-UMC-UPDATER)** — administrative desktop tool that discovers, clones and updates every repo in this ecosystem.
- **[HYDRA-UMC-OS-REBUILDER](https://github.com/JuanenRac/HYDRA-UMC-OS-REBUILDER)** — Windows/Linux desktop tool that builds a ready-to-flash CM5 image pre-loaded with the ecosystem's most current versions, with Raspberry-Pi-Imager-style first-boot Wi-Fi/user/SSH configuration.
- **[HYDRA-UMC-OPS-AGENT](https://github.com/JuanenRac/HYDRA-UMC-OPS-AGENT)** — maintenance-incident coordinator: a low-privilege edge role collects a sanitized inventory/health snapshot, a control-plane role renders it read-only and asks an AI provider to suggest a diagnosis - never applies a patch or deploys anything.
- **[HYDRA-UMC-DEV-SERVER](https://github.com/JuanenRac/HYDRA-UMC-DEV-SERVER)** — reproducible development host (Raspberry Pi 5 / CM5) that stores the ecosystem's source and runs bounded build/test tasks under a durable queue; a dedicated dev role, explicitly not an operational CM5.

## 📚 Documentation

Where to read more:

* [Security baseline of the ecosystem](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/SECURITY_BASELINE.md)
* [Threat model of the ecosystem](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/THREAT_MODEL.md)
* [Changelog of this repository](CHANGELOG.md)
* [License of this repository](LICENSE.md)

## 🤝 Contributing & Community

* Before a pull request run `HYDRA_UMC_CI=1 py -3 tools/ci_validate.py` (or `HYDRA_UMC_CI=1 python3 tools/ci_validate.py`): it must print `CI_VALIDATION=PASS`. Do not run `build.sh` or `build.bat` for this check; building is not a check.
* The eight READMEs are written from one source in HYDRA-UMC-DOCS; do not edit them by hand. Change the source and write them again with `tools/make_readmes.py`.
* Do not state in a README what has not run: say "simulated" or "not tried on hardware" where that is the truth.
* See [CONTRIBUTING.md](CONTRIBUTING.md), the [code of conduct](CODE_OF_CONDUCT.md), [SECURITY.md](SECURITY.md) and [SUPPORT.md](SUPPORT.md).

## 👤 AUTHOR

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 LICENSE

GPL-3.0-or-later - [LICENSE](LICENSE).
