# Simulation bench

The voice chain can run without a microphone, a speaker or a speech recognizer. The simulated path is a recording made of synthetic audio (tones that stand for
speech, silence, a constant hum), the voice detector that cuts it into utterances, a stand-in recognizer that says what each utterance was, and the gateway that
answers each one. It proves that the detector, the intent parser (eight languages), the confirmation rules and the stop priority work together; it says nothing
about how well a real recognizer hears real speech.

## Run it

```
python -m pytest -q tests/test_voice_pipeline_synthetic.py
```

A recording of your own can be cut with the same detector: `hydra-umc-voice-ui analyze-audio clip.wav --noise-ratio 3.0`. Text that a recognizer would have produced can be
parsed with `hydra-umc-voice-ui parse-intent "status of robot 2"`.

## What the checks run

The test files below run on every change in the normal checks and again in the workflow named "Simulation bench", so the simulated path has its own visible job:

| File | What it exercises |
|------|-------------------|
| `tests/test_voice_pipeline_synthetic.py` | a synthetic recording cut into utterances, each answered by the gateway; a hum is not a command; silence gives no turn; a low-confidence movement is asked again and a stop never is; negations and double commands in several languages; a movement waits for confirmation |
| `tests/test_audio.py` | WAV loading and the energy gate, whole clip and streamed |
| `tests/test_gateway.py`, `tests/test_http_service.py` | the voice turn through the gateway and over HTTP |
| `tests/test_intent.py`, `tests/test_intent_languages.py` | the intent parser, including every supported language |
| `tests/test_risk_table.py`, `tests/test_stop_setting.py` | which commands move something and the stop setting |

## What it cannot show

A real microphone, a real speech recognizer or text-to-speech model, the latency of either, and speech in a noisy room still need the hardware and the models.
The status of the repository therefore stays at "simulated" for the hardware row until a person has run the node on the bench.
