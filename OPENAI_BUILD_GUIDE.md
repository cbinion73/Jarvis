# APEX Build Guide, OpenAI Edition

This is the same first-win path from `apex_build_guide_v1.pdf`, with Claude/Anthropic replaced by OpenAI.

## System Stack

| Layer | Tooling |
| --- | --- |
| Runtime | Python 3.11+ |
| Voice engine | ElevenLabs API |
| Brain | OpenAI API |
| Interface | HTML5 / PWA later |
| Trigger modes | Wake phrases + double-clap later |

## 1. Create Accounts

- OpenAI: create an API key for the brain layer.
- ElevenLabs: create an API key for voice output.
- n8n: optional automation layer, skip for the first local win.

## 2. Install Python

```bash
python3 --version
```

You need Python 3.11 or newer.

On macOS:

```bash
brew install python@3.11
brew install portaudio
```

## 3. Install Dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

If `pyaudio` fails on macOS, run:

```bash
brew install portaudio
pip install pyaudio
```

## 4. Create `.env`

```bash
cp .env.example .env
```

Then edit `.env`:

```bash
OPENAI_API_KEY=sk-proj-YOUR-KEY-HERE
ELEVENLABS_API_KEY=YOUR-ELEVENLABS-KEY-HERE
OPENAI_MODEL=gpt-5.2
YOUR_NAME=Chris
ELEVENLABS_VOICE=Adam
```

No quotes around keys. No spaces around `=`.

## 5. Run The First Script

```bash
python apex_hello.py
```

Expected result:

- The OpenAI API generates a short greeting.
- The greeting prints as `APEX: ...`.
- ElevenLabs speaks the greeting.

## Claude To OpenAI Code Swap

Original guide:

```python
import anthropic

brain = anthropic.Anthropic()
response = brain.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=80,
    messages=[{
        "role": "user",
        "content": f"Say a short greeting to {YOUR_NAME}. Be direct.",
    }],
)
text = response.content[0].text
```

OpenAI version:

```python
from openai import OpenAI

brain = OpenAI()
response = brain.responses.create(
    model="gpt-5.2",
    max_output_tokens=80,
    input=f"Say a short greeting to {YOUR_NAME}. Be direct.",
)
text = response.output_text
```

## Troubleshooting

No audio:

```bash
python -c "import sounddevice; print(sounddevice.query_devices())"
```

OpenAI API error:

- Confirm `.env` has `OPENAI_API_KEY`.
- Confirm the key has no spaces around `=`.
- Confirm your virtual environment is active.

ElevenLabs error:

- Confirm `.env` has `ELEVENLABS_API_KEY`.
- Try a different voice name if your account does not have access to `Adam`.

