"""
llm_gateway.py — JARVIS Unified LLM Gateway

Single entry point for all language-model calls. Routes to:
  - phi3.5 (Ollama)       — ultra-fast: routing, classification, tagging
  - gpt-oss-20b (Ollama)  — workhorse: background agent reasoning, conversation
  - gpt-5.4-mini (OpenAI) — escalation: uncertainty, high-stakes, cloud fallback

Thread-safe. Uses only stdlib HTTP (urllib.request). Never raises.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import urllib.error
import urllib.request
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

_log = logging.getLogger("jarvis.llm_gateway")

# ---------------------------------------------------------------------------
# Usage / cost tracking
# ---------------------------------------------------------------------------

_USAGE_LOG_PATH = Path(__file__).parent.parent / "data" / "logs" / "llm_usage.jsonl"
_usage_write_lock = threading.Lock()

# Approximate cost per 1M tokens (input, output) in USD — update as pricing changes.
# Ollama / local = free.  Groq free tier = $0.  Paid tiers listed below.
_TOKEN_COST_PER_1M: dict[str, tuple[float, float]] = {
    "gpt-5.5":           (75.00, 300.00),
    "gpt-5.5-thinking":  (75.00, 300.00),
    "gpt-5.4":           ( 2.50,  10.00),
    "gpt-5.4-thinking":  ( 2.50,  10.00),
    "gpt-5.4-mini":      ( 0.15,   0.60),
    "gpt-4o":            ( 2.50,  10.00),
    "gpt-4o-mini":       ( 0.15,   0.60),
    # Groq free tier — $0 (rate-limited but no charge)
    "llama-3.3-70b":     ( 0.0,    0.0),
    "llama-3.1-8b":      ( 0.0,    0.0),
    "openai/gpt-oss":    ( 0.0,    0.0),
}


def _estimate_cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Estimate USD cost for one call. Returns 0.0 for free/local models."""
    for prefix, (inp_rate, out_rate) in _TOKEN_COST_PER_1M.items():
        if model.startswith(prefix) or prefix in model:
            return round(
                (prompt_tokens * inp_rate + completion_tokens * out_rate) / 1_000_000, 8
            )
    return 0.0


def _record_usage(entry: dict) -> None:
    """Append one usage record to llm_usage.jsonl. Thread-safe. Never raises."""
    try:
        _USAGE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(entry, separators=(",", ":")) + "\n"
        with _usage_write_lock:
            with _USAGE_LOG_PATH.open("a", encoding="utf-8") as fh:
                fh.write(line)
    except Exception as exc:
        _log.debug("Usage tracking write failed: %s", exc)


def usage_summary(hours: int = 24) -> dict:
    """
    Return token and cost totals for the past N hours from llm_usage.jsonl.

    Returns::

        {
          "window_hours": 24,
          "total_calls": 47,
          "paid_calls": 3,
          "prompt_tokens": 12450,
          "completion_tokens": 3201,
          "total_tokens": 15651,
          "estimated_cost_usd": 0.0034,
          "by_model":   { "<model>":   { calls, prompt_tokens, completion_tokens, cost_usd } },
          "by_backend": { "<backend>": { calls, prompt_tokens, completion_tokens, cost_usd } },
        }
    """
    cutoff_ts = (datetime.now(timezone.utc) - timedelta(hours=hours)).timestamp()

    result: dict = {
        "window_hours": hours,
        "total_calls": 0,
        "paid_calls": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "estimated_cost_usd": 0.0,
        "by_model": {},
        "by_backend": {},
    }

    if not _USAGE_LOG_PATH.exists():
        return result

    try:
        with _usage_write_lock:
            lines = _USAGE_LOG_PATH.read_text(encoding="utf-8").splitlines()
    except Exception:
        return result

    for raw in lines:
        raw = raw.strip()
        if not raw:
            continue
        try:
            rec = json.loads(raw)
        except Exception:
            continue
        if rec.get("ts", 0) < cutoff_ts:
            continue

        pt      = int(rec.get("prompt_tokens", 0))
        ct      = int(rec.get("completion_tokens", 0))
        model   = rec.get("model_used", "unknown")
        backend = rec.get("backend", "unknown")
        cost    = float(rec.get("estimated_cost_usd", 0.0))

        result["total_calls"] += 1
        if backend in ("openai", "groq") and (pt + ct) > 0:
            result["paid_calls"] += 1
        result["prompt_tokens"]    += pt
        result["completion_tokens"] += ct
        result["total_tokens"]      += pt + ct
        result["estimated_cost_usd"] += cost

        for bucket_key, bucket_val in ((model, "by_model"), (backend, "by_backend")):
            b = result[bucket_val].setdefault(bucket_key, {
                "calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "cost_usd": 0.0,
            })
            b["calls"]             += 1
            b["prompt_tokens"]     += pt
            b["completion_tokens"] += ct
            b["cost_usd"]          += cost

    result["estimated_cost_usd"] = round(result["estimated_cost_usd"], 6)
    return result

# ---------------------------------------------------------------------------
# Model configuration (all overridable via env vars)
# ---------------------------------------------------------------------------

_FAST_MODEL              = lambda: os.getenv("JARVIS_OLLAMA_FAST_MODEL",        "phi3.5")
_SUBSTANTIVE_MODEL       = lambda: os.getenv("JARVIS_OLLAMA_SUBSTANTIVE_MODEL", "qwen2.5:14b")
_BACKGROUND_MODEL        = lambda: os.getenv("JARVIS_OLLAMA_BACKGROUND_MODEL",  "qwen2.5:7b")
_REASONING_MODEL         = lambda: os.getenv("JARVIS_OLLAMA_REASONING_MODEL",   "qwen2.5:14b")
_OPENAI_MODEL            = lambda: os.getenv("JARVIS_OPENAI_MODEL",             "gpt-5.4-mini")
_THINKING_MODEL          = lambda: os.getenv("JARVIS_THINKING_MODEL",           "gpt-5.4")
_MAX_THINKING_MODEL      = lambda: os.getenv("JARVIS_MAX_THINKING_MODEL",       "gpt-5.5")
_GROQ_MODEL              = lambda: os.getenv("JARVIS_GROQ_MODEL",               "llama-3.3-70b-versatile")
_GROQ_REASONING_MODEL    = lambda: os.getenv("JARVIS_GROQ_REASONING_MODEL",     "openai/gpt-oss-120b")

# ---------------------------------------------------------------------------
# Task routing tables
# ---------------------------------------------------------------------------

TASK_MODEL_MAP: dict[str, str] = {
    # phi3.5: instant classification (2.2 GB, ~100ms)
    "classify":    "phi3.5",
    "route":       "phi3.5",
    "tag":         "phi3.5",
    "detect":      "phi3.5",
    "check":       "phi3.5",
    # qwen2.5:14b: substantive local work — planning, drafting, reasoning (9 GB, M4 local)
    "agent_work":  "substantive",
    "converse":    "substantive",
    "reason":      "substantive",
    "draft":       "substantive",
    "analyze":     "substantive",
    "plan":        "substantive",
    # qwen2.5:7b: background / lightweight tasks (4.7 GB)
    "summarize":   "background",
    "extract":     "background",
    "format":      "background",
    "briefing":    "background",
    # Groq gpt-oss-120b: heavy reasoning — free, 120B, 131k ctx
    "reason_deep": "groq-reasoning",
    # Groq llama-3.3-70b: live voice — fast LPU, much smarter than 8b
    "voice":           "groq",
    "voice_quick":     "groq",
    # OpenAI tier 1: strategy / cloud drafts
    "strategy":        "gpt-5.4-mini",
    "voice_draft":     "gpt-5.4-mini",
    # OpenAI tier 2: extended thinking
    "high_stakes":     "gpt-5.4-thinking",
    "deep_reason":     "gpt-5.4-thinking",
    "legal":           "gpt-5.4-thinking",
    "financial_plan":  "gpt-5.4-thinking",
    # OpenAI tier 3: max thinking — requires Chris's approval before calling
    "critical":        "gpt-5.5-thinking",
    "life_decision":   "gpt-5.5-thinking",
}

TASK_TEMPERATURE_MAP: dict[str, float] = {
    "classify":    0.0,
    "route":       0.0,
    "tag":         0.0,
    "detect":      0.0,
    "check":       0.0,
    "agent_work":  0.4,
    "summarize":   0.3,
    "converse":    0.7,
    "reason":      0.2,
    "draft":       0.6,
    "analyze":     0.2,
    "plan":        0.3,
    "briefing":        0.5,
    "voice":           0.7,
    "voice_quick":     0.6,
    "strategy":        0.4,
    "voice_draft":     0.6,
    "high_stakes":     0.2,
    "deep_reason":     0.1,
    "legal":           0.1,
    "financial_plan":  0.2,
    "critical":        0.0,
    "life_decision":   0.0,
}

ESCALATION_THRESHOLD = 0.68

# ---------------------------------------------------------------------------
# Five-tier escalation ladder
# ---------------------------------------------------------------------------
# Tier 1  phi3.5                  — local, ~100ms,  classify/route/tag
# Tier 2a qwen2.5:14b (substantive) — local, ~2s,   converse/plan/draft/reason
# Tier 2b qwen2.5:7b  (background)  — local, ~1s,   summarize/extract/format
# Tier 2c openai/gpt-oss-120b (Groq) — cloud free, 120B, deep reasoning
# Tier 3  gpt-5.4-mini            — cloud, fast,    strategy / drafts
# Tier 4  gpt-5.4-thinking        — cloud, slow,    high-stakes + extended thinking
# Tier 5  gpt-5.5-thinking        — cloud, slowest, critical decisions — APPROVAL REQUIRED
# ---------------------------------------------------------------------------

ESCALATION_PATH: dict[str, str] = {
    "phi3.5":            "qwen2.5:14b",      # phi3.5 → substantive local
    "qwen2.5:14b":       "gpt-5.4-mini",     # substantive local → cloud
    "qwen2.5:7b":        "qwen2.5:14b",      # background → substantive
    "qwen2.5":           "gpt-5.4-mini",     # legacy alias
    "gpt-oss:20b":       "gpt-5.4-mini",     # legacy alias (broken local)
    "gpt-5.4-mini":      "gpt-5.4-thinking",
    "gpt-5.4-thinking":  "gpt-5.5-thinking", # approval gate fires here
    "gpt-5.5-thinking":  "gpt-5.5-thinking", # already at top
}

# Models that use OpenAI's reasoning/thinking mode (reasoning_effort=high)
THINKING_MODELS: frozenset[str] = frozenset({"gpt-5.4-thinking", "gpt-5.5-thinking"})

# Tier 5 requires explicit approval before the API call is made
APPROVAL_REQUIRED_MODELS: frozenset[str] = frozenset({"gpt-5.5-thinking"})

FALLBACK_MESSAGES: dict[str, str] = {
    "agent_work": "Agent check complete. Intelligence layer offline — reconnect Ollama for full reasoning.",
    "converse":   "I'm here, but my reasoning layer is offline. Check Ollama status.",
    "summarize":  "Summary unavailable — intelligence layer offline.",
}

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class LLMMessage:
    role: str     # "system" | "user" | "assistant"
    content: str


@dataclass
class LLMResponse:
    text: str
    model_used: str
    backend: str           # "ollama" | "openai"
    task_type: str
    latency_ms: int
    prompt_tokens: int
    completion_tokens: int
    confidence: float      # 0.0–1.0 estimated from response content
    escalated: bool        # True if routed to higher tier than originally planned
    error: str             # non-empty if degraded/fallback response


@dataclass
class GatewayRequest:
    messages: list[LLMMessage]
    task_type: str = "converse"
    agent_id: str = "jarvis"
    actor_id: str = "chris"
    temperature: float = 0.7
    max_tokens: int = 1024
    stream: bool = False
    force_model: str = ""
    context: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Confidence estimation
# ---------------------------------------------------------------------------

LOW_CONFIDENCE_PHRASES = [
    "i'm not sure", "i don't know", "i cannot", "i can't", "i don't have",
    "i'm unable", "unclear", "uncertain", "not enough information",
    "i apologize", "i don't have access", "as an ai", "i don't have the ability",
    "i'm not able to", "i lack", "without more context",
]


def _estimate_confidence(text: str) -> float:
    """
    Estimate model confidence from response text.
    Returns 0.0–1.0. Default 0.85 if no low-confidence signals are detected.
    """
    text_lower = text.lower()
    matches = sum(1 for p in LOW_CONFIDENCE_PHRASES if p in text_lower)
    if matches == 0:
        return 0.85
    if matches == 1:
        return 0.60
    return max(0.2, 0.85 - (matches * 0.15))


# ---------------------------------------------------------------------------
# OllamaBackend
# ---------------------------------------------------------------------------

class OllamaBackend:
    """
    Connects to the local Ollama server via its OpenAI-compatible API.
    Uses urllib.request — no extra dependencies.
    """

    DEFAULT_BASE_URL = "http://localhost:11434/v1"
    _HEALTH_URL_TEMPLATE = "http://{host}:{port}/api/tags"
    _CACHE_TTL_S = 60

    def __init__(self, base_url: str | None = None) -> None:
        self._base_url = (
            base_url or os.getenv("OLLAMA_BASE_URL", self.DEFAULT_BASE_URL)
        ).rstrip("/")
        self._available: bool | None = None
        self._last_check: float = 0.0
        self._lock = threading.Lock()

    def _health_url(self) -> str:
        # Derive host/port from base_url so we can hit the health endpoint
        # even when base_url points to /v1.
        url = self._base_url
        # Strip /v1 suffix if present
        if url.endswith("/v1"):
            url = url[:-3]
        return f"{url}/api/tags"

    def is_available(self) -> bool:
        """Ping Ollama health endpoint.  Result cached for 60 s."""
        with self._lock:
            now = time.monotonic()
            if self._available is not None and (now - self._last_check) < self._CACHE_TTL_S:
                return self._available
            try:
                req = urllib.request.Request(
                    self._health_url(),
                    headers={"Accept": "application/json"},
                )
                with urllib.request.urlopen(req, timeout=3) as resp:
                    self._available = resp.status == 200
            except Exception:
                self._available = False
            self._last_check = now
            return self._available  # type: ignore[return-value]

    def complete(
        self,
        messages: list[LLMMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        stream: bool = False,
    ) -> LLMResponse:
        """Call Ollama via its OpenAI-compatible /v1/chat/completions endpoint."""
        # Resolve model aliases using current env-var values
        if model == "phi3.5":
            model = _FAST_MODEL()
        elif model in ("gpt-oss-20b", "gpt-oss:20b"):
            model = _REASONING_MODEL()
        elif model in ("qwen2.5", "qwen"):
            model = "qwen2.5:7b"

        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,  # streaming not implemented over urllib
        }
        body = json.dumps(payload).encode("utf-8")
        url = f"{self._base_url}/chat/completions"
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer ollama",
            },
            method="POST",
        )
        t0 = time.monotonic()
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                raw = resp.read().decode("utf-8")
            elapsed = int((time.monotonic() - t0) * 1000)
            data = json.loads(raw)
            choice = data["choices"][0]
            text = choice["message"]["content"]
            usage = data.get("usage", {})
            return LLMResponse(
                text=text,
                model_used=model,
                backend="ollama",
                task_type="",
                latency_ms=elapsed,
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                confidence=_estimate_confidence(text),
                escalated=False,
                error="",
            )
        except urllib.error.URLError as exc:
            elapsed = int((time.monotonic() - t0) * 1000)
            return LLMResponse(
                text="",
                model_used=model,
                backend="ollama",
                task_type="",
                latency_ms=elapsed,
                prompt_tokens=0,
                completion_tokens=0,
                confidence=0.0,
                escalated=False,
                error=f"Ollama URLError: {exc}",
            )
        except Exception as exc:
            elapsed = int((time.monotonic() - t0) * 1000)
            return LLMResponse(
                text="",
                model_used=model,
                backend="ollama",
                task_type="",
                latency_ms=elapsed,
                prompt_tokens=0,
                completion_tokens=0,
                confidence=0.0,
                escalated=False,
                error=f"Ollama error: {exc}",
            )

    def list_models(self) -> list[str]:
        """List available Ollama models."""
        url = self._health_url()  # /api/tags returns model list
        req = urllib.request.Request(
            url,
            headers={"Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return [m["name"] for m in data.get("models", [])]
        except Exception:
            return []


# ---------------------------------------------------------------------------
# OpenAIBackend
# ---------------------------------------------------------------------------

class OpenAIBackend:
    """
    Connects to the OpenAI API using urllib.request — no SDK dependency.
    """

    BASE_URL = "https://api.openai.com/v1/chat/completions"

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or os.getenv("OPENAI_API_KEY", "")

    def is_available(self) -> bool:
        return bool(self._api_key)

    def complete(
        self,
        messages: list[LLMMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False,
    ) -> LLMResponse:
        """Call OpenAI chat completions.  Timeout: 120 s for thinking models."""
        # Resolve canonical model names
        model_map = {
            "gpt-5.4-mini":     _OPENAI_MODEL(),
            "gpt-5.4-thinking": _THINKING_MODEL(),
            "gpt-5.5-thinking": _MAX_THINKING_MODEL(),
        }
        resolved = model_map.get(model, model)
        thinking = model in THINKING_MODELS

        if not self._api_key:
            return LLMResponse(
                text="",
                model_used=resolved,
                backend="openai",
                task_type="",
                latency_ms=0,
                prompt_tokens=0,
                completion_tokens=0,
                confidence=0.0,
                escalated=False,
                error="OpenAI API key not configured",
            )

        payload: dict = {
            "model": resolved,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
        }
        # gpt-5.x models require max_completion_tokens; older models use max_tokens
        _NEW_API_MODELS = ("gpt-5", "o1", "o3")
        use_new_token_param = any(resolved.startswith(p) for p in _NEW_API_MODELS)
        if thinking:
            # Extended thinking: suppress temperature, use reasoning_effort
            payload["reasoning_effort"] = "high"
            payload["max_completion_tokens"] = max(max_tokens, 8192)
        elif use_new_token_param:
            payload["max_completion_tokens"] = max_tokens
        else:
            payload["temperature"] = temperature
            payload["max_tokens"] = max_tokens
        if not thinking and not use_new_token_param:
            pass  # temperature already set above
        elif not thinking:
            payload["temperature"] = temperature
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.BASE_URL,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            },
            method="POST",
        )
        t0 = time.monotonic()
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read().decode("utf-8")
            elapsed = int((time.monotonic() - t0) * 1000)
            data = json.loads(raw)
            choice = data["choices"][0]
            text = choice["message"]["content"]
            usage = data.get("usage", {})
            return LLMResponse(
                text=text,
                model_used=model,
                backend="openai",
                task_type="",
                latency_ms=elapsed,
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                confidence=_estimate_confidence(text),
                escalated=False,
                error="",
            )
        except urllib.error.HTTPError as exc:
            elapsed = int((time.monotonic() - t0) * 1000)
            try:
                err_body = exc.read().decode("utf-8")
            except Exception:
                err_body = str(exc)
            return LLMResponse(
                text="",
                model_used=model,
                backend="openai",
                task_type="",
                latency_ms=elapsed,
                prompt_tokens=0,
                completion_tokens=0,
                confidence=0.0,
                escalated=False,
                error=f"OpenAI HTTP {exc.code}: {err_body[:200]}",
            )
        except Exception as exc:
            elapsed = int((time.monotonic() - t0) * 1000)
            return LLMResponse(
                text="",
                model_used=model,
                backend="openai",
                task_type="",
                latency_ms=elapsed,
                prompt_tokens=0,
                completion_tokens=0,
                confidence=0.0,
                escalated=False,
                error=f"OpenAI error: {exc}",
            )


# ---------------------------------------------------------------------------
# GroqBackend
# ---------------------------------------------------------------------------

class GroqBackend:
    """
    Groq cloud inference — LPU hardware, 840-1000 tokens/sec.
    OpenAI-compatible API. Free tier sufficient for personal voice use.
    """

    BASE_URL = "https://api.groq.com/openai/v1/chat/completions"
    DEFAULT_MODEL = "llama-3.1-8b-instant"  # 840 tok/s, 131k context, free tier

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or os.getenv("GROQ_API_KEY", "")

    def is_available(self) -> bool:
        return bool(self._api_key)

    def complete(
        self,
        messages: list[LLMMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        stream: bool = False,
    ) -> LLMResponse:
        """Call Groq chat completions via its OpenAI-compatible endpoint."""
        # Resolve "groq" alias to the configured default model
        if model == "groq":
            model = _GROQ_MODEL()

        if not self._api_key:
            return LLMResponse(
                text="",
                model_used=model,
                backend="groq",
                task_type="",
                latency_ms=0,
                prompt_tokens=0,
                completion_tokens=0,
                confidence=0.0,
                escalated=False,
                error="Groq API key not configured",
            )

        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.BASE_URL,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
                "User-Agent": "JARVIS/2.0 (personal-assistant)",
            },
            method="POST",
        )
        t0 = time.monotonic()
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8")
            elapsed = int((time.monotonic() - t0) * 1000)
            data = json.loads(raw)
            choice = data["choices"][0]
            text = choice["message"]["content"]
            usage = data.get("usage", {})
            return LLMResponse(
                text=text,
                model_used=model,
                backend="groq",
                task_type="",
                latency_ms=elapsed,
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                confidence=_estimate_confidence(text),
                escalated=False,
                error="",
            )
        except urllib.error.HTTPError as exc:
            elapsed = int((time.monotonic() - t0) * 1000)
            try:
                err_body = exc.read().decode("utf-8")
            except Exception:
                err_body = str(exc)
            return LLMResponse(
                text="",
                model_used=model,
                backend="groq",
                task_type="",
                latency_ms=elapsed,
                prompt_tokens=0,
                completion_tokens=0,
                confidence=0.0,
                escalated=False,
                error=f"Groq HTTP {exc.code}: {err_body[:200]}",
            )
        except Exception as exc:
            elapsed = int((time.monotonic() - t0) * 1000)
            return LLMResponse(
                text="",
                model_used=model,
                backend="groq",
                task_type="",
                latency_ms=elapsed,
                prompt_tokens=0,
                completion_tokens=0,
                confidence=0.0,
                escalated=False,
                error=f"Groq error: {exc}",
            )


# ---------------------------------------------------------------------------
# OpenViking context helper
# ---------------------------------------------------------------------------

def _query_openviking(agent_id: str, data: dict) -> str:
    """
    Pull relevant long-term context from OpenViking for this agent call.
    Returns a formatted string to inject into the system prompt, or "" if
    OpenViking is disabled / unreachable.  Never raises.
    """
    try:
        from .config import AppConfig
        from .openviking_context import OpenVikingSupport
        config = AppConfig.from_env()
        ov = OpenVikingSupport(config=config)
        if not ov.enabled:
            return ""
        # Build a natural-language query from the agent and the snapshot keys
        keys_hint = ", ".join(list(data.keys())[:6]) if data else "general"
        query = f"agent:{agent_id} context about {keys_hint}"
        ctx = ov.party_mode_context(query, limit=4)
        return ctx
    except Exception as exc:
        _log.debug("OpenViking context query skipped: %s", exc)
        return ""


# ---------------------------------------------------------------------------
# LLMGateway
# ---------------------------------------------------------------------------

class LLMGateway:
    """
    The single entry point for all LLM calls in JARVIS.

    Routes to the correct model tier based on task_type, estimates confidence,
    escalates to the next tier when confidence is low, and falls back gracefully
    if backends are offline.  Thread-safe.
    """

    def __init__(self, ollama: OllamaBackend, openai: OpenAIBackend, groq: GroqBackend | None = None) -> None:
        self._ollama = ollama
        self._openai = openai
        self._groq = groq or GroqBackend()
        self._call_log: deque[dict] = deque(maxlen=100)
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_model(self, task_type: str, force_model: str = "") -> str:
        """Return the canonical model name for a given task type."""
        if force_model:
            return force_model
        raw = TASK_MODEL_MAP.get(task_type, "substantive")
        if raw == "phi3.5":
            return _FAST_MODEL()
        if raw == "substantive":
            return _SUBSTANTIVE_MODEL()
        if raw == "background":
            return _BACKGROUND_MODEL()
        if raw in ("gpt-oss-20b", "gpt-oss:20b"):
            return _REASONING_MODEL()
        if raw == "groq-reasoning":
            return _GROQ_REASONING_MODEL()
        if raw == "gpt-5.4-mini":
            return _OPENAI_MODEL()
        if raw == "groq":
            return _GROQ_MODEL()
        # Tier 4 / 5 — keep as-is; OpenAIBackend resolves them internally
        if raw in ("gpt-5.4-thinking", "gpt-5.5-thinking"):
            return raw
        return raw

    def _backend_for(self, model: str) -> str:
        """Determine which backend handles a given model string."""
        if model in THINKING_MODELS:
            return "openai"
        openai_model = _OPENAI_MODEL()
        if model == openai_model:
            return "openai"
        # Groq: voice alias, llama-* families, groq-* prefixed, openai/* OSS models on Groq
        if (model == "groq"
                or model.startswith("llama")
                or model.startswith("groq-")
                or model.startswith("openai/")
                or model.startswith("meta-llama/")
                or model.startswith("qwen/")):
            return "groq"
        # Ollama handles local models (qwen2.5:*, phi3.5, etc.)
        return "ollama"

    def _escalate_model(self, model: str) -> str | None:
        """Return the next-tier model, or None if already at the top."""
        fast = _FAST_MODEL()
        substantive = _SUBSTANTIVE_MODEL()
        background = _BACKGROUND_MODEL()
        openai_m = _OPENAI_MODEL()

        if model == fast:          return substantive
        if model == background:    return substantive
        if model == substantive:   return openai_m
        if model == openai_m:      return "gpt-5.4-thinking"
        if model == "gpt-5.4-thinking": return "gpt-5.5-thinking"
        return None   # already at top

    def _check_tier5_approval(
        self, agent_id: str, task_type: str, messages: list[LLMMessage]
    ) -> bool:
        """
        Check whether Chris has pre-approved a gpt-5.5-thinking call for this
        agent+task.  If no approval exists, submits one to the approval queue
        and returns False (the call is held).  Returns True if already approved.
        Never raises.
        """
        try:
            from .approvals import get_approval_queue, RiskTier, ApprovalRequest
            import uuid as _uuid
            queue = get_approval_queue()
            if queue is None:
                return False

            approval_key = f"tier5:{agent_id}:{task_type}"

            # Check for an existing approved entry
            for req in queue.get_pending():
                if req.action_type == "llm_tier5" and req.metadata.get("key") == approval_key:
                    if req.status == "approved":
                        return True
                    return False   # still pending

            # No existing request — submit one and hold
            preview = messages[-1].content[:200] if messages else ""
            req = ApprovalRequest(
                request_id=str(_uuid.uuid4()),
                action_type="llm_tier5",
                risk_tier=RiskTier.HIGH,
                agent_id=agent_id,
                actor_id="chris",
                description=(
                    f"JARVIS wants to use gpt-5.5 (extended thinking) for a '{task_type}' task.\n"
                    f"Query preview: {preview}…\n\n"
                    f"This is the highest reasoning tier — slower and more expensive. Approve to proceed."
                ),
                action_payload={"model": "gpt-5.5-thinking", "task_type": task_type},
                metadata={"key": approval_key, "agent_id": agent_id},
            )
            queue.submit(req)
            _log.info(
                "Tier-5 approval requested for agent=%s task=%s (request_id=%s)",
                agent_id, task_type, req.request_id,
            )
            return False
        except Exception as exc:
            _log.debug("Tier-5 approval check failed: %s", exc)
            return False

    def _call_backend(
        self,
        messages: list[LLMMessage],
        model: str,
        temperature: float,
        max_tokens: int,
        stream: bool,
    ) -> LLMResponse:
        """Dispatch to the appropriate backend."""
        backend = self._backend_for(model)
        if backend == "openai":
            return self._openai.complete(
                messages, model, temperature=temperature,
                max_tokens=max_tokens, stream=stream,
            )
        if backend == "groq":
            return self._groq.complete(
                messages, model, temperature=temperature,
                max_tokens=max_tokens, stream=stream,
            )
        return self._ollama.complete(
            messages, model, temperature=temperature,
            max_tokens=max_tokens, stream=stream,
        )

    def _escalate_model(self, model: str) -> str | None:
        """Return the next-tier model, or None if already at the top."""
        # Normalise to canonical names for lookup
        fast = _FAST_MODEL()
        reasoning = _REASONING_MODEL()
        openai_m = _OPENAI_MODEL()

        if model == fast:
            return reasoning
        if model == reasoning:
            return openai_m
        # Already at OpenAI tier or unknown — no escalation
        if model == openai_m:
            return None
        return None

    def _log_call(self, entry: dict) -> None:
        with self._lock:
            self._call_log.append(entry)
        _record_usage(entry)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def complete(
        self,
        messages: list[LLMMessage],
        task_type: str = "converse",
        agent_id: str = "jarvis",
        actor_id: str = "chris",
        temperature: float | None = None,
        max_tokens: int | None = None,
        stream: bool = False,
        force_model: str = "",
        allow_escalation: bool = True,
        tools: list[dict] | None = None,
    ) -> LLMResponse:
        """
        Main entry point.  Routes, calls, checks confidence, escalates if needed.
        Never raises — returns an LLMResponse with error set on failure.

        tools: optional list of OpenAI-style tool dicts. For voice task_types,
               the voice allowlist is applied automatically before the backend call.
        """
        if temperature is None:
            temperature = TASK_TEMPERATURE_MAP.get(task_type, 0.7)
        if max_tokens is None:
            max_tokens = 16384 if task_type in ("critical", "life_decision", "high_stakes", "deep_reason", "legal", "financial_plan") else \
                         4096  if task_type in ("strategy", "voice_draft") else 1024

        model = self._resolve_model(task_type, force_model)
        original_model = model
        escalated = False

        # If Ollama is offline, immediately escalate Ollama-bound tasks.
        # Voice tasks prefer Groq (fast LPU); other tasks escalate to OpenAI.
        if not self._ollama.is_available() and self._backend_for(model) == "ollama":
            if task_type in ("voice", "voice_quick") and self._groq.is_available():
                _log.info(
                    "Ollama offline, escalating voice task %s/%s to Groq", task_type, model
                )
                model = _GROQ_MODEL()
                escalated = True
            elif self._openai.is_available():
                _log.info(
                    "Ollama offline, escalating %s/%s to OpenAI", task_type, model
                )
                model = _OPENAI_MODEL()
                escalated = True
            else:
                # Both backends offline — return degraded fallback
                fallback_text = FALLBACK_MESSAGES.get(
                    task_type,
                    "Intelligence layer offline — both Ollama and OpenAI are unavailable.",
                )
                entry = {
                    "ts": time.time(),
                    "agent_id": agent_id,
                    "actor_id": actor_id,
                    "task_type": task_type,
                    "model_used": model,
                    "backend": "none",
                    "latency_ms": 0,
                    "confidence": 0.0,
                    "escalated": False,
                    "error": "both_offline",
                }
                self._log_call(entry)
                return LLMResponse(
                    text=fallback_text,
                    model_used=model,
                    backend="none",
                    task_type=task_type,
                    latency_ms=0,
                    prompt_tokens=0,
                    completion_tokens=0,
                    confidence=0.0,
                    escalated=False,
                    error="Both Ollama and OpenAI are offline.",
                )

        # Apply voice tool allowlist to keep prefill fast
        if task_type in ("voice", "voice_quick") and tools:
            try:
                from .voice_pipeline import filter_tools_for_voice
                tools = filter_tools_for_voice(tools)
            except ImportError:
                pass

        t_start = time.monotonic()
        response = self._call_backend(messages, model, temperature, max_tokens, stream)
        response.task_type = task_type
        response.escalated = escalated

        # Escalate if confidence is low and we're allowed to
        if (
            allow_escalation
            and not escalated
            and not force_model
            and response.error == ""
            and response.confidence < ESCALATION_THRESHOLD
        ):
            next_model = self._escalate_model(model)
            if next_model and next_model != model:
                _log.info(
                    "Confidence %.2f < %.2f for %s/%s — escalating to %s",
                    response.confidence, ESCALATION_THRESHOLD,
                    task_type, model, next_model,
                )
                # Tier 5 (gpt-5.5-thinking) requires Chris's approval before firing
                if next_model in APPROVAL_REQUIRED_MODELS:
                    approved = self._check_tier5_approval(agent_id, task_type, messages)
                    if not approved:
                        _log.info(
                            "Tier-5 escalation to %s blocked — approval pending for agent=%s task=%s",
                            next_model, agent_id, task_type,
                        )
                        response.error = "tier5_approval_pending"
                        return response
                esc_response = self._call_backend(
                    messages, next_model, temperature, max_tokens, stream,
                )
                if not esc_response.error:
                    esc_response.task_type = task_type
                    esc_response.escalated = True
                    response = esc_response

        # If primary call errored and we haven't escalated yet, try Groq (voice) or OpenAI
        if response.error and self._backend_for(model) == "groq" and self._openai.is_available() and allow_escalation:
            _log.warning(
                "Groq error for %s/%s: %s — falling back to OpenAI",
                task_type, model, response.error,
            )
            fallback = self._openai.complete(
                messages, _OPENAI_MODEL(),
                temperature=temperature, max_tokens=max_tokens, stream=stream,
            )
            if not fallback.error:
                fallback.task_type = task_type
                fallback.escalated = True
                response = fallback

        if response.error and self._backend_for(model) == "ollama" and self._openai.is_available() and allow_escalation:
            _log.warning(
                "Ollama error for %s/%s: %s — falling back to OpenAI",
                task_type, model, response.error,
            )
            fallback = self._openai.complete(
                messages, _OPENAI_MODEL(),
                temperature=temperature, max_tokens=max_tokens, stream=stream,
            )
            if not fallback.error:
                fallback.task_type = task_type
                fallback.escalated = True
                response = fallback

        total_ms = int((time.monotonic() - t_start) * 1000)

        entry = {
            "ts": time.time(),
            "agent_id": agent_id,
            "actor_id": actor_id,
            "task_type": task_type,
            "model_used": response.model_used,
            "backend": response.backend,
            "latency_ms": total_ms,
            "prompt_tokens": response.prompt_tokens,
            "completion_tokens": response.completion_tokens,
            "estimated_cost_usd": _estimate_cost_usd(
                response.model_used, response.prompt_tokens, response.completion_tokens
            ),
            "confidence": response.confidence,
            "escalated": response.escalated,
            "error": response.error,
        }
        self._log_call(entry)

        _log.debug(
            "[gateway] agent=%s task=%s model=%s latency=%dms confidence=%.2f escalated=%s error=%r",
            agent_id, task_type, response.model_used, total_ms,
            response.confidence, response.escalated, response.error or None,
        )

        return response

    def classify(self, text: str, categories: list[str], context: str = "") -> str:
        """
        Fast classification using phi3.5.
        Returns the best matching category from the list.
        """
        cats_str = ", ".join(categories)
        system_msg = (
            "You are a fast classifier. Given a text and a list of categories, "
            "respond with ONLY the single best matching category name from the list. "
            "No explanation. No punctuation. Just the category name exactly as given."
        )
        user_content = f"Categories: {cats_str}\n\nText: {text}"
        if context:
            user_content = f"Context: {context}\n\n{user_content}"

        response = self.complete(
            messages=[
                LLMMessage("system", system_msg),
                LLMMessage("user", user_content),
            ],
            task_type="classify",
            allow_escalation=False,
        )
        result = response.text.strip().strip(".,;:\"'").strip()
        # Validate against known categories (case-insensitive)
        for cat in categories:
            if cat.lower() == result.lower():
                return cat
        # Fuzzy fallback: return first category that appears in the response
        result_lower = result.lower()
        for cat in categories:
            if cat.lower() in result_lower:
                return cat
        # Default to first category if nothing matched
        return categories[0] if categories else result

    def agent_think(
        self,
        agent_id: str,
        data: dict,
        memory_context: str = "",
    ) -> LLMResponse:
        """
        Convenience method for background agent reasoning.
        Automatically injects Marvel persona + memory context + OpenViking
        context (if enabled) and routes to gpt-oss-20b.
        """
        from .persona import build_agent_system_prompt

        system = build_agent_system_prompt(agent_id)
        if memory_context:
            system += f"\n\n[KNOWN CONTEXT]\n{memory_context}"

        # Augment with OpenViking long-term context (non-blocking, best-effort)
        ov_context = _query_openviking(agent_id, data)
        if ov_context:
            system += f"\n\n[LONG-TERM MEMORY — OpenViking]\n{ov_context}"

        user_content = (
            f"Here is your current data and context:\n"
            f"{json.dumps(data, indent=2)}\n\n"
            f"Based on this data, provide your assessment. "
            f"Be specific, actionable, and speak in your character's voice. "
            f"Format your response as: "
            f"SUMMARY: [1-2 sentences]\n"
            f"ITEMS: [bullet points of notable items, if any]\n"
            f"ACTION: [yes/no - does anything require Chris's attention?]\n"
            f"NOTE: [optional: one thing worth highlighting]"
        )

        return self.complete(
            messages=[
                LLMMessage("system", system),
                LLMMessage("user", user_content),
            ],
            task_type="agent_work",
            agent_id=agent_id,
        )

    def parse_agent_response(self, response: LLMResponse) -> dict:
        """
        Parse the structured SUMMARY/ITEMS/ACTION/NOTE format from agent_think.
        Returns: {summary, items, action_required, note, confidence}

        Degrades gracefully if the model didn't follow the format perfectly.
        """
        text = response.text or ""
        result: dict = {
            "summary": "",
            "items": [],
            "action_required": False,
            "note": "",
            "confidence": response.confidence,
        }

        if not text:
            return result

        # Extract each section using a simple line-scan approach
        current_section: str | None = None
        item_lines: list[str] = []

        for line in text.splitlines():
            stripped = line.strip()
            upper = stripped.upper()

            if upper.startswith("SUMMARY:"):
                current_section = "summary"
                val = stripped[len("SUMMARY:"):].strip()
                if val:
                    result["summary"] = val
                continue
            if upper.startswith("ITEMS:"):
                current_section = "items"
                val = stripped[len("ITEMS:"):].strip()
                if val and val not in ("-", "–", "—", "none", "None", "N/A"):
                    item_lines.append(val)
                continue
            if upper.startswith("ACTION:"):
                current_section = "action"
                val = stripped[len("ACTION:"):].strip().lower()
                result["action_required"] = val.startswith("yes")
                continue
            if upper.startswith("NOTE:"):
                current_section = "note"
                val = stripped[len("NOTE:"):].strip()
                if val:
                    result["note"] = val
                continue

            # Continuation lines
            if not stripped:
                continue
            if current_section == "summary" and not result["summary"]:
                result["summary"] = stripped
            elif current_section == "items":
                clean = stripped.lstrip("-•*·▸▹►>").strip()
                if clean:
                    item_lines.append(clean)
            elif current_section == "note" and not result["note"]:
                result["note"] = stripped

        result["items"] = item_lines

        # Last-resort fallback: if no SUMMARY found, use first non-empty line
        if not result["summary"] and text.strip():
            for line in text.splitlines():
                if line.strip():
                    result["summary"] = line.strip()
                    break

        return result

    def simple_complete(self, prompt: str, max_tokens: int = 512, task_type: str = "converse") -> str:
        """Convenience wrapper: single user-turn prompt → response text string."""
        messages = [LLMMessage(role="user", content=prompt)]
        response = self.complete(messages, task_type=task_type, max_tokens=max_tokens)
        return response.text

    def get_status(self) -> dict:
        """Health and diagnostics status."""
        with self._lock:
            recent = list(self._call_log)[-10:]
        return {
            "ollama_available": self._ollama.is_available(),
            "openai_available": self._openai.is_available(),
            "groq_available": self._groq.is_available(),
            "ollama_url": self._ollama._base_url,
            "recent_calls": recent,
            "models": {
                "fast": _FAST_MODEL(),
                "reasoning": _REASONING_MODEL(),
                "escalation": _OPENAI_MODEL(),
                "groq": _GROQ_MODEL(),
            },
        }


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_gateway: LLMGateway | None = None
_gateway_lock = threading.Lock()


def init_gateway(config=None) -> LLMGateway:
    """Initialize and return the gateway singleton."""
    global _gateway
    with _gateway_lock:
        ollama_url = os.getenv("OLLAMA_BASE_URL", OllamaBackend.DEFAULT_BASE_URL)
        # Ensure url ends with /v1 for the completions endpoint
        if not ollama_url.endswith("/v1"):
            ollama_url_v1 = ollama_url.rstrip("/") + "/v1"
        else:
            ollama_url_v1 = ollama_url

        api_key = os.getenv("OPENAI_API_KEY", "")
        if config:
            api_key = api_key or getattr(config, "openai_api_key", "")
        groq_key = os.getenv("GROQ_API_KEY", "")

        _gateway = LLMGateway(
            ollama=OllamaBackend(base_url=ollama_url_v1),
            openai=OpenAIBackend(api_key=api_key),
            groq=GroqBackend(api_key=groq_key),
        )
        _log.info(
            "LLM Gateway initialised — fast=%s substantive=%s background=%s groq-voice=%s groq-reasoning=%s openai=%s",
            _FAST_MODEL(), _SUBSTANTIVE_MODEL(), _BACKGROUND_MODEL(),
            _GROQ_MODEL(), _GROQ_REASONING_MODEL(), _OPENAI_MODEL(),
        )
        return _gateway


def get_gateway() -> LLMGateway | None:
    """Return the current gateway singleton (None if not yet initialised)."""
    return _gateway
