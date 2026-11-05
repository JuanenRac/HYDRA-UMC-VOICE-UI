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
HYDRA-UMC-SERVER -> loopback Voice UI. (Today the Server relays only
`/v1/voice/turn`; relaying `/v1/voice/confirm` is still pending there, so a
confirmation token cannot yet complete a round trip in production.) The Watch must not store this token or
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
robot-health or motion-state claim. The `text` is made in the language of the
`locale` of the request (English, Spanish, German, French, Italian, Japanese,
Chinese or Portuguese; any other locale gets English); the reply also carries
`messageCode`, `messageParams` and `textLanguage`, so a client can compose the
sentence itself in its own language. A recognised motion request is labelled
`requiresConfirmation: true`; this v0 service does not dispatch robot commands.

### Confirming a motion request

The Server relays the round trip (`POST /api/voice/turn` and `POST /api/voice/confirm`, with the
session of the signed-in user as the subject), and the intent rules understand English only:
the `locale` field is validated but not used to pick rules. A request that
contains a negation ("do not start the mission") is answered with a request to
rephrase and no confirmation token.

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

The request may also name who is asking, which the relaying Server fills in from the signed-in session and never from the client:

```json
{"confirmationToken": "<the exact string from the earlier reply>", "subject": "alice"}
```

A turn that named a `subject` (`"subject": "alice"` next to `requestId`) gets a token that carries it, and that token confirms only for
the same subject; asking with another subject, or with none, is `invalid` and does not use the token up. A token that names nobody
confirms as before unless `HYDRA_UMC_VOICE_UI_REQUIRE_SUBJECT=1`, which also refuses a turn that names nobody.

A confirmed result also has `subject`, `confirmedAtUtc` and `nonce`; when `HYDRA_UMC_VOICE_UI_RESULT_KEY` (16 characters or more, the
same value the Server holds) is set it has a `signature` too: HMAC-SHA256, in hexadecimal, over the canonical JSON (keys sorted, no
spaces, UTF-8) of the fields `type`, `status`, `requestId`, `intent`, `subject`, `confirmedAtUtc` and `nonce`. The text of `reason` and
the age are not signed. The Server checks it before it believes a confirmed result.

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
* `invalid` - the token is malformed, tampered with, signed with another
  key, was never a real `confirmationToken` string at all, or was already
  used (a token is accepted once).

This gateway keeps no server-side session: `confirmationToken` is a
self-describing capsule naming exactly the intent and entities it was issued
for, signed with HMAC-SHA256 under a server key and carrying a random nonce.
Only this gateway can mint one - knowing the format, or having seen a token,
does not let anyone build a valid token for another intent - and each nonce is
accepted once, so a token that was confirmed cannot be replayed during its 30
seconds. The key is `HYDRA_UMC_VOICE_UI_CONFIRM_SECRET` (at least 16
characters; the OS installer generates it with the other device secrets).
Without it a random key is made per process, which is enough for a 30 second
token: a restart only makes a pending confirmation ask to be repeated. The list
of used nonces lives in memory and is bounded (16384, about 100 bytes each); when it is full the gateway
refuses new confirmations instead of forgetting old ones. So that one client cannot fill it, the HTTP service
limits how many requests an address may make a minute (120 by default, `HYDRA_UMC_VOICE_UI_RATE_PER_MINUTE`,
0 turns the limit off): past it the answer is `429` with `retryAfterSeconds`. A confirmation can therefore never be replayed to
authorize a *different*, later request - a changed parameter (a different
mission, a different robot) always mints its own new, distinct token; the
old one, if ever confirmed, still only ever confirms its own original,
now-outdated action.

## The transcript in a reply

A reply's `interpretation` holds `matchedRules` and, only when the server sets `HYDRA_UMC_VOICE_UI_INCLUDE_HEARD_TEXT=1`, `heardText` (the transcript as received) and `normalizedText`. The transcript is personal data, so it is off by default.

## Limits

The rules understand English only. The `locale` of a turn must be 2-35 characters long but is not used to choose rules.

## Confidence of the recognizer

A turn may carry `"confidence"`, a number from 0 to 1 that says how sure the speech recognizer was of the transcript (a number outside that range, or anything that is not a number, is refused with a 400). A request that starts a movement (a mission or going home) heard with a confidence below the server's minimum is not accepted: the reply asks to say it again, has no intent and no confirmation token, and says that nothing was started. A stop and a status request are never held back by it, and a turn without `confidence` behaves as before. The minimum is `HYDRA_UMC_VOICE_UI_MIN_CONFIDENCE` (default 0.6; 0 switches the check off; a value that is not a number from 0 to 1 is ignored and the default stays).

## Options sent by the Server

Both settings above can also be set by an administrator from the Server Admin screen of the control app. The Server saves them in its configuration and sends them with every turn it relays, as an object `options` in the body of `POST /v1/voice/turn`:

```json
{ "type": "voice_turn", "requestId": "r-1", "transcript": "start mission demo", "locale": "en-US",
  "options": { "includeHeardText": false, "minConfidence": 0.6 } }
```

Both fields are optional. `includeHeardText` must be true or false and `minConfidence` a number from 0 to 1; anything else (or an `options` that is not an object) is refused with a 400 and a message that names the field. The order is always the same: the environment of this service (`HYDRA_UMC_VOICE_UI_INCLUDE_HEARD_TEXT`, `HYDRA_UMC_VOICE_UI_MIN_CONFIDENCE`) wins when it is set, then the `options` of the turn, then the built-in default (transcript off, 0.6), which is what a turn without `options` gets. The Server replaces any `options` a client sends with its own, so a phone cannot change them. The options are read from the body of the request, so the service token (`HYDRA_UMC_VOICE_UI_TOKEN`) is what keeps other callers from setting them; on a loopback bind without a token any local process can.

## Optional voice features (all off by default)

Everything in this section is switched on from one configuration file, `HYDRA_UMC_VOICE_UI_CONFIG` (default `/etc/hydra-umc/voice-ui.json`, example in `deploy/voice-ui.json.example`). A value that is not valid is ignored and the default stays; a missing or broken file leaves every feature off. Raw audio is never stored by any of them.

### Wake word and push-to-talk

With `wake.enabled` a turn is acted on only when it was started on purpose: the turn carries `"activation": "push_to_talk"` (the button; refused when `wake.allowPushToTalk` is false) or `"activation": "wake_word"` (the device heard the wake word itself), or the transcript begins with one of `wake.phrases`, which is then taken off before the command is read. Otherwise the reply is `not_activated` and nothing happens. A spoken stop does not need the wake word unless `wake.stopNeedsWake` is true.

### Who is speaking

With `speaker.enabled` a request that starts a movement (a mission, going home) is accepted only for an enrolled operator. The turn carries `"speakerVector"`, a list of 8 to 512 numbers made on the device from the voice (never audio); it is compared by cosine similarity with the vectors in `speaker.storeFile` and must reach `speaker.threshold` and beat the second best by `speaker.margin`. The operator found becomes the subject of the confirmation token; when the turn also names a `subject` (the signed-in user) it must be the same, or the reply is `speaker_not_authorised` with no token. The confirmation of the primary device is still required, and a stop, a status request and a question are never held back by this check. The vector is never repeated in a reply, a log or the audit log; the reply only says `speaker: {checked, verified}`.

Enrolment needs the service token (a service with no token refuses it) and speaker identification on: `POST /v1/voice/speaker/enroll` with `{"subject": "ana", "vector": [...]}` and `POST /v1/voice/speaker/forget` with `{"subject": "ana"}`, which removes the vector from the file at once. The subject of an enrolment must be the same name the Server uses for that user.

### Questions about error codes

"What does error 0x05 mean" (and the same in the other seven languages) is a read-only question. With `queries.enabled` it is answered from HYDRA-UMC-DOCS-QA (`GET /error?code=`) at `queries.docsQaUrl`, with `queries.tokenFile` for its bearer token, and the reply carries the citations in `sources`. A code the documentation does not define is answered as not found; an assistant that does not answer is answered as unavailable. With the feature off the reply says so. The documentation is English, so the definition is read out as written.

### Questions about a node or a motor

"How is motor 3" (and the same in the other seven languages: "cómo está el motor 3", "wie ist der Knoten A7", "comment va le nœud A7", "come sta il motore 3", "como está o nó A7", "モーター3の状態", "节点A7的状态") is a read-only question with the intent `query_node` and the entity `node`: the name as it was said after the word for node, or `motor` and its number written together (`motor3`), in lowercase without spaces or dashes so that it can be compared with the name of a series. A sentence that does not name a node or a motor is not one, and the word "status" inside the question does not make it a request for the status of the robot. The service itself only answers that the server reads the state (`messageCode: "node_query"`); HYDRA-UMC-SERVER, which holds the verdicts of the anomaly detector, replaces the text with the state of that node (`node_state`). The level is `informative` like the other questions; a risk file can raise it to a confirmation but never lower it.

### Audit log

The audit log is on by default (`audit.enabled`, switch it off with `"enabled": false`); every turn and every confirmation adds one line to `audit.file`: time, request id, kind of event, intent, outcome (a short code), how the confirmation went, whether the voice was verified, and the person. The person is a keyed hash (the key is a random file kept beside the log), or the name itself with `audit.storeSubjectPlain`. The transcript, the locale, audio, the voice vector and addresses are never written. A file grows to `audit.maxBytes`, then it is rotated to `.1`, `.2`... up to `audit.maxFiles` files and the oldest is dropped. The server collects the last records with `GET /v1/voice/audit?limit=N` (needs the service token). A record that cannot be written never stops a command (a stop above all); the service keeps working and says so in `GET /health` (`audit.writable`, `audit.writeErrors`) and in `GET /metrics` (`hydra_umc_voice_ui_audit_writable`, `hydra_umc_voice_ui_audit_write_errors_total`). The key of the person hash is created the first time as `<audit.file>.key`, outside the repository, readable only by its owner.

**Signature of every line (`audit.transcriptHmac`, on by default).** Each record carries `kid` (the first eight hex digits of the SHA-256 of the key) and `sig` (the HMAC-SHA256, in hex, of the record written with sorted keys and no spaces and without `sig`). The key is a file outside the repository named by `audit.hmacKeyFile` (empty: `<audit.file>.hmac.key`); it is created with permissions `0600` when it is missing, is never printed, logged or returned by any endpoint, and a damaged key file is never overwritten. If the switch is on and the key cannot be had (it cannot be created, is unreadable or is damaged) the audit goes on but every record carries `unsigned` with the reason (`key_cannot_be_created`, `key_unreadable`, `key_invalid`, `key_unavailable`) and the service says so: `GET /health` has `audit.signing` (`ok`, `off` or the reason) and `audit.unsignedRecords`, and `GET /metrics` has `hydra_umc_voice_ui_audit_signing` (1 signed, 0 key missing, -1 off) and `hydra_umc_voice_ui_audit_unsigned_records_total`; it never switches itself off. Check a log with `python -m hydra_umc_voice_ui.audit [FILE...] [--config voice-ui.json] [--key-file KEY]...` (exit code 0 all good, 1 a changed, forged, damaged or foreign-key line, 2 only unsigned lines). A replaced key is kept in a file and given with `--key-file`: the `kid` of each line picks the right one. The signature detects a changed or forged line; it does not detect a whole line that was deleted. Keep the key file in a folder the service can read and other accounts cannot. Studio: the switch is the setting `audit.enabled` and the path `audit.file` of the voice configuration file (the Studio control is pending, and so are `audit.transcriptHmac` and `audit.hmacKeyFile`).

### Alerts read aloud

`POST /v1/voice/alert` takes `{"alertId", "source": "system-status" | "anomaly", "severity": "info" | "warning" | "critical", "locale", ...}` and answers with the sentence to say and `speak` (whether to say it now). For `anomaly` the body also has `node` and `verdict` (`normal`, `suspect`, `anomalous`) and the sentence is a fixed one in the eight languages; a `normal` verdict is never spoken. For `system-status` it has `text`, the `speak` text the Server wrote, cleaned and cut to `alerts.maxChars`. With `alerts.enabled` off nothing is to be spoken (`reason: alerts_off`); an alert below `alerts.minSeverity` is not (`below_threshold`), and the same alert is not repeated inside `alerts.repeatSeconds` (`alerts.criticalRepeatSeconds` for a critical one). The device produces the sound.
