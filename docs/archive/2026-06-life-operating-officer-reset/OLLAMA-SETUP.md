# Ollama Setup — JARVIS Local Model Stack

Tested on M4 Mac Mini (24GB RAM). Takes ~10 minutes end-to-end.

---

## Install Ollama

```bash
brew install ollama
brew services start ollama
```

Ollama runs a local inference server at `http://localhost:11434`. It stays running in the background via launchd.

---

## Pull Models

### phi3.5 — fast classifier (~2.2GB)

```bash
ollama pull phi3.5
```

Used for routing and intent classification. Extremely fast (~200ms on M4), handles task-type decisions before handing off to a heavier model. This is the model that decides whether a request goes to a local model or a cloud provider.

### Reasoning model (~9–16GB)

The intended model is `gpt-oss-20b` — OpenAI's open-weight MoE model (21B total params, ~3.6B active per token, matches o3-mini quality, Apache 2.0 license). As of May 2026, check if it's available in Ollama's registry:

```bash
ollama pull gpt-oss-20b
```

**If not yet available**, use `qwen2.5:14b` as the primary stand-in — strong reasoning, 9GB, handles complex agent work well:

```bash
ollama pull qwen2.5:14b
```

`mistral:latest` (~4GB) is an option if you need a lighter footprint temporarily, but reasoning quality is noticeably lower.

> When `gpt-oss-20b` lands in Ollama's registry, update `JARVIS_OLLAMA_REASONING_MODEL` in `.env` and re-pull.

### nomic-embed-text — embeddings (274MB)

```bash
ollama pull nomic-embed-text
```

Used for semantic memory search, similarity scoring, and context retrieval across the JARVIS memory core. Small and fast.

---

## Verify

```bash
ollama list
curl http://localhost:11434/v1/models
```

Expected output from `ollama list` shows at minimum: `phi3.5`, your reasoning model, and `nomic-embed-text`.

---

## Test the Gateway

After JARVIS is running (`python -m jarvis serve`):

```bash
curl -X POST http://localhost:8787/api/gateway/test \
  -H "Content-Type: application/json" \
  -d '{"message": "Good morning", "task_type": "agent_work"}'
```

A successful response confirms routing from the JARVIS gateway through Ollama.

---

## Environment Variables

These three vars in `.env` control which local models JARVIS uses:

| Variable | Default | Purpose |
|---|---|---|
| `JARVIS_SECOND_BRAIN_MODEL` | `qwen2.5:7b` | Primary local reasoning model |
| `JARVIS_OLLAMA_SUMMARIZE_MODEL` | `qwen2.5:7b` | Summarization tasks |
| `JARVIS_OLLAMA_BACKGROUND_MODEL` | `qwen2.5:7b` | Background / async tasks |

Update these to `gpt-oss-20b` or `qwen2.5:14b` once you've confirmed the pull.

The Ollama base URL is set via `OLLAMA_BASE_URL=http://127.0.0.1:11434`.

---

## RAM Usage

| Model | VRAM / RAM | Notes |
|---|---|---|
| phi3.5 | ~3GB | Always loaded; classification |
| qwen2.5:14b | ~9GB | Recommended stand-in for gpt-oss-20b |
| gpt-oss-20b | ~16GB | Target model when available |
| nomic-embed-text | <1GB | Embeddings, minimal footprint |

On a 24GB M4 Mac Mini: `phi3.5` + `qwen2.5:14b` together use ~12GB, leaving ~12GB for macOS, the JARVIS Python process, and headroom. With `gpt-oss-20b` (~16GB) + `phi3.5` (~3GB) you're at ~19GB — still within budget but tight. macOS will use unified memory efficiently.

---

## Troubleshooting

**Ollama not responding**
```bash
brew services restart ollama
curl http://localhost:11434/
```

**Model not found**
```bash
ollama list          # confirm the model name exactly
ollama pull <model>  # re-pull if missing
```

**Out of memory / model swap thrashing**
Unload unused models: `ollama stop <model>`. If running `gpt-oss-20b`, close other memory-heavy apps. Stick to `qwen2.5:14b` if you're seeing degraded performance.

**Port conflict**
Ollama defaults to port 11434. If something else is on that port:
```bash
OLLAMA_HOST=127.0.0.1:11435 ollama serve
```
Then update `OLLAMA_BASE_URL` in `.env` to match.
