# Local Voice Stack

This workspace now supports a local-first speech path alongside the existing OpenAI and ElevenLabs path.

## What Changed

JARVIS now has provider-based speech routing for both text-to-speech and speech-to-text:

- `Piper` via local binary execution for CPU-only, offline-style British voice output
- `LocalAI` for OpenAI-compatible local speech APIs
- `ElevenLabs` still available as a premium fallback
- browser and macOS speech remain the final safety net

## Provider Order

By default, the stack is now configured for hybrid local-first behavior:

```env
JARVIS_TTS_PROVIDER=auto
JARVIS_TTS_FALLBACKS=piper,localai,elevenlabs,system
JARVIS_STT_PROVIDER=auto
JARVIS_STT_FALLBACKS=localai,openai
```

That means:

1. Try local `Piper` for TTS if a model path is configured
2. Try `LocalAI` if it is running
3. Fall back to `ElevenLabs`
4. Fall back to local system voice if nothing else works

For transcription:

1. Try `LocalAI` Whisper-compatible transcription
2. Fall back to OpenAI transcription

## Check Current Readiness

```bash
source /Users/chris/Desktop/CODE/JARVIS/.venv/bin/activate
python -m jarvis voice-stack
```

## Piper Setup

Point JARVIS directly at a Piper model:

```env
PIPER_BINARY=piper
PIPER_MODEL_PATH=/share/piper/en_GB-alan-medium.onnx
PIPER_SPEAKER=
```

Notes:

- `PIPER_MODEL_PATH` should point to the actual `.onnx` voice model file.
- The matching `.onnx.json` config should live beside it.
- If you are using Home Assistant add-ons, `/share/piper` is a good stable target.
- If you are hosting on the Mac mini directly, a host path like `/Users/chris/JARVIS/piper/en_GB-alan-medium.onnx` is equally valid.

## LocalAI Setup

Start LocalAI:

```bash
docker compose -f /Users/chris/Desktop/CODE/JARVIS/infra/docker-compose.local-voice.yml up -d
```

Model stubs live in:

- [/Users/chris/Desktop/CODE/JARVIS/infra/localai/models/whisper-1.yaml](/Users/chris/Desktop/CODE/JARVIS/infra/localai/models/whisper-1.yaml)
- [/Users/chris/Desktop/CODE/JARVIS/infra/localai/models/jarvis-piper.yaml](/Users/chris/Desktop/CODE/JARVIS/infra/localai/models/jarvis-piper.yaml)

Suggested env:

```env
LOCALAI_BASE_URL=http://127.0.0.1:8080
LOCALAI_TTS_MODEL=jarvis-piper
LOCALAI_TTS_BACKEND=piper
LOCALAI_STT_MODEL=whisper-1
```

## Recommended Personal Hosting Shape

For your house, the cleanest deployment path is:

1. Mac mini runs JARVIS
2. LocalAI runs in Docker on the same host
3. Piper models live in a stable shared folder
4. Home Assistant consumes Piper through Wyoming where useful
5. JARVIS prefers local speech, then cloud fallback

## LiveKit

LiveKit is best treated as the realtime transport and orchestration layer once you want:

- full duplex voice
- room-to-agent sessions
- interruptible speech at a higher quality bar
- multi-device voice ingress beyond the browser shell

It is not required for the local-first speech stack to work today.
The right migration order is:

1. local TTS and STT
2. stable house-facing voice behavior
3. LiveKit as the richer transport layer
