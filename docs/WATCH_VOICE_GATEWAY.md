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

### Confirming a motion request

A reply with `requiresConfirmation: true` also carries a real, bounded
`confirmationToken` and `confirmationValiditySeconds` (30s by default) - the
Watch client holds onto this token verbatim and echoes it back on
`POST /v1/voice/confirm` (same `Authorization` requirement as `/v1/voice/turn`)
once the human actually confirms:

```json
{"confirmationToken": "<the exact string from the earlier reply>"}
```

```json
{"type": "confirmation_result", "status": "confirmed", "reason": "start_mission confirmed 4.0s after being requested - execution still requires the authenticated primary control", "requestId": "watch-voice-002", "intent": {"name": "start_mission", "entities": {"mission_id": "alpha"}}, "ageSeconds": 4.0}
```

`status` is one of:

* `confirmed` - the token is genuine and still within its real validity
  window. This still only ever *reports* a confirmed intent; the caller
  (HYDRA-UMC-SERVER/OPS-AGENT) decides whether it matches what it is about
  to actually do before acting on it.
* `expired` - the token is genuine but past `confirmationValiditySeconds`
  (or, symmetrically, timestamped in the future - clock skew is never
  treated as extra-fresh). `reason` names the real age; the client must
  repeat the original request and confirm the new one, never retry the
  stale token.
* `invalid` - the token is malformed, tampered with, or was never a real
  `confirmationToken` string at all.

This gateway keeps no server-side session store: `confirmationToken` is a
self-describing, checksummed capsule naming exactly the intent and entities
it was issued for. A confirmation can therefore never be replayed to
authorize a *different*, later request - a changed parameter (a different
mission, a different robot) always mints its own new, distinct token; the
old one, if ever confirmed, still only ever confirms its own original,
now-outdated action.
