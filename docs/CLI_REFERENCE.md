# HYDRA-UMC-VOICE-UI — CLI Reference

`hydra-umc-voice-ui` is a Python console script
(`src/hydra_umc_voice_ui/main.py`, installed as an entry point via
`pyproject.toml`). What's real in v0: WAV audio loading + energy-gate
voice-activity detection (`audio.py`), rule-based intent/entity parsing
over already-transcribed text (`intent.py`), and a local authenticated
HTTP gateway for bounded voice-turn text (`http_service.py`/`gateway.py`
— see `docs/WATCH_VOICE_GATEWAY.md` for the wire protocol, which is out
of scope for this page). None of this is the Whisper STT / neural TTS
pipeline the project README's own roadmap describes — that needs a real
model dependency and stays future work. Every example below was
captured from a real run of the installed CLI — not written from memory.

## Usage

```
$ hydra-umc-voice-ui -h
usage: hydra-umc-voice-ui [-h] {analyze-audio,parse-intent,serve} ...

Voice UI (Hailo-10) - local STT/TTS pipeline for hands-free robotic mission
control.

positional arguments:
  {analyze-audio,parse-intent,serve}
    analyze-audio       Real WAV loading + energy-gate voice-activity
                        detection.
    parse-intent        Real rule-based intent/entity parsing over transcribed
                        text.
    serve               Run the local authenticated Watch voice-turn gateway.

options:
  -h, --help            show this help message and exit
```

Bare invocation (no subcommand) prints identity/version/role and exits `0`:

```
$ hydra-umc-voice-ui
HYDRA-UMC-VOICE-UI v0.0.5
Voice UI (Hailo-10) - local STT/TTS pipeline for hands-free robotic mission control.
```

## Commands

### `analyze-audio <wav_file>`

```
$ hydra-umc-voice-ui analyze-audio -h
usage: hydra-umc-voice-ui analyze-audio [-h] wav_file

positional arguments:
  wav_file    Path to a 16-bit PCM WAV file.

options:
  -h, --help  show this help message and exit
```

Real WAV loading (sample rate, channels, duration, RMS energy) plus a v0
energy-gate voice-activity detector. The fixtures below are built with
the same real WAV-writing approach `tests/test_audio.py` uses for its own
fixtures — the stdlib `wave` module, one clip of 0.5s silence + 1.0s of a
440Hz tone + 0.5s silence, and one clip of pure silence:

```python
import wave, math, array

def tone(n, amplitude=10000, frequency=440.0, rate=8000):
    return [int(amplitude * math.sin(2 * math.pi * frequency * i / rate)) for i in range(n)]

# clip_with_voice.wav: 0.5s silence + 1.0s tone + 0.5s silence, 8kHz mono 16-bit PCM
# clip_silence.wav: 1.0s silence, 8kHz mono 16-bit PCM
```

A clip with a real detected voice segment:

```
$ hydra-umc-voice-ui analyze-audio clip_with_voice.wav
File: clip_with_voice.wav
Sample rate: 8000 Hz
Channels: 1
Duration: 2.000 s
RMS energy: 4999.7
Voice segments: 1 detected (v0 energy-gate VAD)
  1. 0.480s -> 1.500s
$ echo $?
0
```

The detected segment's boundaries land right where the real tone starts
and ends (0.5s–1.5s), within one VAD frame's worth of slack.

A pure-silence clip — the honest "nothing detected" case, still exit `0`:

```
$ hydra-umc-voice-ui analyze-audio clip_silence.wav
File: clip_silence.wav
Sample rate: 8000 Hz
Channels: 1
Duration: 1.000 s
RMS energy: 0.0
Voice segments: none detected (v0 energy-gate VAD)
$ echo $?
0
```

A missing file (real, honest check before ever touching `wave.open`):

```
$ hydra-umc-voice-ui analyze-audio does_not_exist.wav
ERROR: file not found: does_not_exist.wav
$ echo $?
1
```

### `parse-intent <text>`

```
$ hydra-umc-voice-ui parse-intent -h
usage: hydra-umc-voice-ui parse-intent [-h] text

positional arguments:
  text        Already-transcribed text to parse.

options:
  -h, --help  show this help message and exit
```

Real rule-based intent/entity parsing over a small, fixed command
vocabulary (mission control commands only — this never does STT itself,
it parses text already transcribed elsewhere):

```
$ hydra-umc-voice-ui parse-intent "please start mission alpha now"
Intent: start_mission
  mission_id: alpha
$ echo $?
0
```

```
$ hydra-umc-voice-ui parse-intent "please halt"
Intent: stop
$ echo $?
0
```

```
$ hydra-umc-voice-ui parse-intent "what is the status of robot 3"
Intent: status
  robot_id: 3
$ echo $?
0
```

```
$ hydra-umc-voice-ui parse-intent "robot, go home"
Intent: go_home
$ echo $?
0
```

An honest miss — text outside the recognized vocabulary is not forced
into a guess, and this is still exit `0` (parsing "nothing matched" is a
normal, successful outcome, not a failure):

```
$ hydra-umc-voice-ui parse-intent "what is the weather today"
No matching intent for: "what is the weather today"
(v0 is a real rule-based parser over a small command vocabulary - an honest miss, not a guess.)
$ echo $?
0
```

### `serve [--host HOST] [--port PORT]`

```
$ hydra-umc-voice-ui serve -h
usage: hydra-umc-voice-ui serve [-h] [--host HOST] [--port PORT]

options:
  -h, --help   show this help message and exit
  --host HOST  Bind host (non-loopback requires HYDRA_UMC_VOICE_UI_TOKEN).
  --port PORT  Bind TCP port (default: 8090).
```

Runs the real local Watch voice-turn HTTP gateway (stdlib
`ThreadingHTTPServer`, no external web framework). Started here for real
on the default loopback host, confirmed live with a real `GET /health`,
then stopped — the full websocket-style voice-turn protocol itself is
documented separately in `docs/WATCH_VOICE_GATEWAY.md` and is out of
scope for this CLI reference:

```
$ hydra-umc-voice-ui serve --port 8099
HYDRA-UMC-VOICE-UI voice gateway listening on http://127.0.0.1:8099
POST /v1/voice/turn accepts bounded text only; it never actuates robots.
```

```
$ curl -s http://127.0.0.1:8099/health
{"product":"HYDRA-UMC-VOICE-UI","version":"0.0.5","voiceTurnEndpoint":"/v1/voice/turn","authRequired":false}
```

(stopped with Ctrl+C / SIGINT once confirmed — `serve` prints
`Voice gateway stopped.` and exits `0` on a clean interrupt.)

Binding beyond loopback without a real bearer token is refused honestly
rather than silently serving unauthenticated on a non-local interface:

```
$ hydra-umc-voice-ui serve --host 0.0.0.0 --port 8099
ERROR: HYDRA_UMC_VOICE_UI_TOKEN is required when binding beyond loopback
$ echo $?
1
```

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | ok — including an honest "no voice segments"/"no matching intent" miss, and a clean `serve` shutdown |
| `1` | a real, reported failure: `analyze-audio` given a missing file, or `serve` refusing to bind beyond loopback without a real token |

## Out of scope for this CLI

Real Whisper-based STT and neural TTS — the actual speech-to-text and
text-to-speech steps the project README's own roadmap describes — are
not implemented yet; they need a real model dependency this environment
does not run. `analyze-audio` and `parse-intent` are the real,
hardware-independent pieces already in place: energy-gate VAD over a raw
WAV file, and rule-based parsing over text some other component already
transcribed. The `serve` gateway's own wire protocol (voice-turn request/
response shape, auth, streaming) is documented separately in
`docs/WATCH_VOICE_GATEWAY.md`.
