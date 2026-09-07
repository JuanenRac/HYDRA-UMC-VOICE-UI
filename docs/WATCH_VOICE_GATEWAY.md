<!-- =============================================================================
HYDRA-UMC-VOICE-UI - Watch voice gateway deployment contract
Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0 - see LICENSE
============================================================================= -->

# Watch voice gateway

`HYDRA-UMC-VOICE-UI` now exposes a small local HTTP gateway for the typed
`voice_turn` messages used by HYDRA-UMC-WATCH. It accepts recognised text,
uses the existing rule-based intent parser and returns an `assistant_reply`.
It never accepts raw microphone audio and never actuates a robot.

## Start safely

For a local development check only:

```text
hydra-umc-voice-ui serve
```

For the CM5 deployment, keep the service on loopback and set a long random
secret in its systemd environment. HYDRA-UMC-SERVER is the sole caller and
forwards a normal authenticated client request using that internal secret:

```text
HYDRA_UMC_VOICE_UI_TOKEN=<long-random-secret>
hydra-umc-voice-ui serve --host 127.0.0.1 --port 8091
```

The production path is Watch -> paired Android transport -> authenticated
HYDRA-UMC-SERVER -> loopback Voice UI. The Watch must not store this token or
contact Voice UI directly. The physical Wear transport remains a separate
hardware integration; the Server-to-Voice UI relay is implemented and tested.

## API

`POST /v1/voice/turn` with `Authorization: Bearer <token>` when the token is
configured:

```json
{
  "type": "voice_turn",
  "requestId": "watch-voice-001",
  "transcript": "status of robot 3",
  "locale": "en-US"
}
```

The response is an `assistant_reply` compatible with the Watch protocol. Its
additive `visualState` is a bounded UI hint (`acknowledged`, `clarification`,
`confirmation-required` or `warning`) for the Watch display; it is not a live
robot-health or motion-state claim. A recognised motion request is labelled
`requiresConfirmation: true`; this v0 service does not dispatch robot commands.
