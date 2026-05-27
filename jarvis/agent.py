"""
jarvis/agent.py — JARVIS Agentic Loop
======================================
Streaming agent that uses OpenAI with function calling to build,
troubleshoot, and run code. The loop yields StreamEvent objects that
the SSE endpoint forwards to the browser as Server-Sent Events.

Usage (in service.py):
    from jarvis.agent import run_agent, resolve_approval

    async for event in run_agent(messages, context):
        yield event  # send as SSE

    resolve_approval(approval_id, approved=True)
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from dataclasses import dataclass, field
from typing import AsyncIterator

from openai import AsyncOpenAI

from .tools import TOOL_REGISTRY
from .tools.base import ApprovalFlag, ToolResult

# ── Model configuration ────────────────────────────────────────────────────
# Priority: 1) Local Ollama  2) Groq (llama)  3) OpenAI fallback
_OLLAMA_BASE   = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/") + "/v1"
_OLLAMA_MODEL  = os.environ.get("AGENT_OLLAMA_MODEL", "qwen2.5:14b")
_GROQ_BASE     = "https://api.groq.com/openai/v1"
_GROQ_MODEL    = os.environ.get("AGENT_GROQ_MODEL", os.environ.get("JARVIS_GROQ_MODEL", "llama-3.3-70b-versatile"))
_GROQ_KEY      = os.environ.get("GROQ_API_KEY", "")
_OPENAI_MODEL  = os.environ.get("AGENT_MODEL", os.environ.get("OPENAI_MODEL", "gpt-4o"))
MAX_TURNS      = int(os.environ.get("AGENT_MAX_TURNS", "30"))


def _make_client() -> tuple["AsyncOpenAI", str]:
    """Return (AsyncOpenAI client, model_name) using the best available LLM backend.

    Priority:
      1. Local Ollama (qwen2.5:14b) — used when running on the home Mac
      2. Groq (llama-3.3-70b-versatile) — used in cloud/Docker where Ollama isn't present
      3. OpenAI — last resort fallback
    """
    import httpx as _httpx

    # 1 — Try local Ollama
    try:
        ollama_health_url = _OLLAMA_BASE.replace("/v1", "") + "/api/tags"
        r = _httpx.get(ollama_health_url, timeout=1.5)
        if r.status_code == 200:
            return (
                AsyncOpenAI(base_url=_OLLAMA_BASE, api_key="ollama"),
                _OLLAMA_MODEL,
            )
    except Exception:
        pass

    # 2 — Try Groq (fast external inference, no OpenAI dependency)
    if _GROQ_KEY:
        return (
            AsyncOpenAI(base_url=_GROQ_BASE, api_key=_GROQ_KEY),
            _GROQ_MODEL,
        )

    # 3 — OpenAI fallback
    return AsyncOpenAI(), _OPENAI_MODEL

# ── Approval gate state (module-level, shared across requests) ─────────────
_pending_approvals: dict[str, asyncio.Event] = {}
_approval_decisions: dict[str, bool]         = {}

# ── System prompt ─────────────────────────────────────────────────────────
AGENT_SYSTEM_PROMPT = """You are JARVIS, an agentic AI assistant for Chris Binion.

You have tools that let you build, troubleshoot, run code, read/write files, search the
web, call internal JARVIS API endpoints, manage git, and persist facts across sessions.

IDENTITY & MISSION
You are the central intelligence of the JARVIS project — a personal AI operating system.
You have full access to the JARVIS codebase and its connected projects (Ghostwritr, etc.).
Your job is to help Chris build, debug, and maintain this system as a capable co-developer.

TOOL USAGE PRINCIPLES
- When modifying code: read the file first, make surgical edits, then verify by running it.
- Prefer targeted edits over full rewrites.
- For destructive operations (deletes, resets, force pushes): explain what you're about
  to do and why before proceeding. Wait for approval when the gate fires.
- For bash: prefer explicit, readable commands. Always review stdout and stderr.
- For web searches: use specific queries. Refine if the first result is poor.

COMMUNICATION STYLE
- Be concise in tool calls: minimal inputs, no over-explanation.
- Be thorough in summaries: synthesize tool output into human-readable prose.
- Narrate multi-step plans before starting so Chris can redirect early.
- End each completed task with a brief summary of what changed and which files were touched.

ERROR HANDLING
- Diagnose before retrying. Don't blindly retry a failing command.
- If stuck after two attempts, describe the obstacle and ask Chris for guidance.

MEMORY
- Use the memory tool to record facts that will matter in future sessions.
- At session start, recall relevant stored facts before acting.
"""

# ── Convert Anthropic-format TOOL_DEFINITIONS to OpenAI function-calling ──

def _to_openai_tools() -> list[dict]:
    """Convert Anthropic tool schema dicts to OpenAI function-calling format."""
    result = []
    for module in TOOL_REGISTRY.values():
        defn = module.DEFINITION
        # Anthropic uses "input_schema", OpenAI uses "parameters" inside "function"
        parameters = defn.get("input_schema", {"type": "object", "properties": {}})
        result.append({
            "type": "function",
            "function": {
                "name": defn["name"],
                "description": defn.get("description", ""),
                "parameters": parameters,
            },
        })
    return result


OPENAI_TOOL_DEFINITIONS = _to_openai_tools()


# ── Event types ───────────────────────────────────────────────────────────

@dataclass
class StreamEvent:
    type: str
    data: dict = field(default_factory=dict)

    def to_sse(self) -> str:
        """Format as a Server-Sent Event data line."""
        return f"data: {json.dumps({'type': self.type, **self.data})}\n\n"


# ── Approval resolution ───────────────────────────────────────────────────

def resolve_approval(approval_id: str, approved: bool) -> bool:
    """
    Resolve a pending approval gate (called by the /api/agent/approve endpoint).

    Returns True if the approval_id was found and resolved, False if unknown.
    """
    if approval_id not in _pending_approvals:
        return False
    _approval_decisions[approval_id] = approved
    _pending_approvals[approval_id].set()
    return True


# ── Tool execution ─────────────────────────────────────────────────────────

async def _execute_tool(tool_name: str, tool_input: dict) -> ToolResult:
    """Dispatch to the right tool module. Exceptions become error ToolResults."""
    tool_module = TOOL_REGISTRY.get(tool_name)
    if tool_module is None:
        return ToolResult(
            output=f"Unknown tool: '{tool_name}'. Available: {list(TOOL_REGISTRY.keys())}",
            error=True,
        )
    try:
        return await tool_module.run(**tool_input)
    except Exception as exc:  # noqa: BLE001
        return ToolResult(
            output=f"Tool '{tool_name}' raised {type(exc).__name__}: {exc}",
            error=True,
        )


# ── Main agent loop ────────────────────────────────────────────────────────

async def run_agent(
    messages: list[dict],
    system_context: str = "",
    conversation_id: str = "",
) -> AsyncIterator[StreamEvent]:
    """
    Async generator: run the JARVIS agentic loop and yield StreamEvent objects.

    Args:
        messages:        Conversation history in OpenAI message format
                         [{"role": "user", "content": "..."}, ...]
        system_context:  Extra context appended to the system prompt
                         (from context_builder.build_context())
        conversation_id: Optional ID for session memory / logging

    Yields:
        StreamEvent with types: text_delta | tool_call | approval_needed |
                                tool_skipped | tool_result | done | error | max_turns
    """
    client, active_model = _make_client()

    # Build system message
    system_parts = [AGENT_SYSTEM_PROMPT]
    if system_context:
        system_parts.append(system_context)
    system_content = "\n\n".join(system_parts)

    # Build the working message list (system + history)
    working_messages: list[dict] = [
        {"role": "system", "content": system_content},
        *messages,
    ]

    try:
        for turn in range(MAX_TURNS):
            full_text = ""
            # Accumulate tool call chunks: {index: {id, name, args_so_far}}
            tool_call_accum: dict[int, dict] = {}
            finish_reason: str = "stop"

            # ── Streaming API call ─────────────────────────────────────────
            try:
                stream = await client.chat.completions.create(
                    model=active_model,
                    messages=working_messages,
                    tools=OPENAI_TOOL_DEFINITIONS,
                    tool_choice="auto",
                    max_completion_tokens=8192,
                    stream=True,
                )
            except Exception as exc:
                yield StreamEvent(type="error", data={"message": f"LLM API error: {exc}"})
                return

            async for chunk in stream:
                choice = chunk.choices[0] if chunk.choices else None
                if choice is None:
                    continue

                delta = choice.delta
                if delta.content:
                    full_text += delta.content
                    yield StreamEvent(type="text_delta", data={"delta": delta.content})

                # Accumulate tool call argument chunks
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index
                        if idx not in tool_call_accum:
                            tool_call_accum[idx] = {
                                "id":   tc.id or "",
                                "name": tc.function.name if tc.function and tc.function.name else "",
                                "args": "",
                            }
                        if tc.function and tc.function.arguments:
                            tool_call_accum[idx]["args"] += tc.function.arguments
                        # id / name may arrive on later chunks
                        if tc.id:
                            tool_call_accum[idx]["id"] = tc.id
                        if tc.function and tc.function.name:
                            tool_call_accum[idx]["name"] = tc.function.name

                if choice.finish_reason:
                    finish_reason = choice.finish_reason

            # ── End turn ────────────────────────────────────────────────────
            if finish_reason in ("stop", "end_turn") or not tool_call_accum:
                yield StreamEvent(
                    type="done",
                    data={
                        "text": full_text,
                        "conversation_id": conversation_id,
                        "turns": turn + 1,
                        "model": active_model,
                    },
                )
                return

            # ── Tool calls ──────────────────────────────────────────────────
            # Build the assistant message with tool_calls
            oai_tool_calls = []
            for idx in sorted(tool_call_accum.keys()):
                tc = tool_call_accum[idx]
                oai_tool_calls.append({
                    "id":       tc["id"],
                    "type":     "function",
                    "function": {
                        "name":      tc["name"],
                        "arguments": tc["args"],
                    },
                })

            working_messages.append({
                "role":       "assistant",
                "content":    full_text or None,
                "tool_calls": oai_tool_calls,
            })

            tool_result_messages: list[dict] = []

            for tc in oai_tool_calls:
                tool_name    = tc["function"]["name"]
                tool_call_id = tc["id"]

                # Parse arguments JSON
                try:
                    tool_input_dict: dict = json.loads(tc["function"]["arguments"] or "{}")
                except json.JSONDecodeError:
                    tool_input_dict = {}

                yield StreamEvent(
                    type="tool_call",
                    data={
                        "tool":        tool_name,
                        "input":       tool_input_dict,
                        "tool_use_id": tool_call_id,
                    },
                )

                # ── Approval gate ──────────────────────────────────────────
                tool_module = TOOL_REGISTRY.get(tool_name)
                approval_flag = ApprovalFlag.NONE
                if tool_module is not None:
                    try:
                        approval_flag = tool_module.needs_approval(tool_input_dict)
                    except Exception:  # noqa: BLE001
                        approval_flag = ApprovalFlag.NONE

                if approval_flag == ApprovalFlag.REQUIRED:
                    approval_id = str(uuid.uuid4())
                    event = asyncio.Event()
                    _pending_approvals[approval_id] = event

                    yield StreamEvent(
                        type="approval_needed",
                        data={
                            "approval_id": approval_id,
                            "tool":        tool_name,
                            "input":       tool_input_dict,
                            "tool_use_id": tool_call_id,
                        },
                    )

                    # Wait up to 120 s for the user to decide
                    try:
                        await asyncio.wait_for(event.wait(), timeout=120.0)
                    except asyncio.TimeoutError:
                        _pending_approvals.pop(approval_id, None)
                        _approval_decisions.pop(approval_id, None)
                        tool_result_messages.append({
                            "role":         "tool",
                            "tool_call_id": tool_call_id,
                            "content":      "Approval timed out. Tool not executed.",
                        })
                        yield StreamEvent(
                            type="tool_skipped",
                            data={"tool": tool_name, "reason": "approval_timeout"},
                        )
                        continue

                    approved = _approval_decisions.get(approval_id, False)
                    _pending_approvals.pop(approval_id, None)
                    _approval_decisions.pop(approval_id, None)

                    if not approved:
                        tool_result_messages.append({
                            "role":         "tool",
                            "tool_call_id": tool_call_id,
                            "content":      "User declined. Do not retry without asking.",
                        })
                        yield StreamEvent(
                            type="tool_skipped",
                            data={"tool": tool_name, "reason": "user_denied"},
                        )
                        continue

                # ── Execute the tool ───────────────────────────────────────
                result: ToolResult = await _execute_tool(tool_name, tool_input_dict)

                yield StreamEvent(
                    type="tool_result",
                    data={
                        "tool":        tool_name,
                        "output":      result.output,
                        "error":       result.error,
                        "tool_use_id": tool_call_id,
                    },
                )

                tool_result_messages.append({
                    "role":         "tool",
                    "tool_call_id": tool_call_id,
                    "content":      result.output,
                })

            # Append all tool results to the conversation and loop
            working_messages.extend(tool_result_messages)

        # Exhausted MAX_TURNS
        yield StreamEvent(
            type="max_turns",
            data={
                "message": f"Reached {MAX_TURNS}-turn limit without completing.",
                "turns":   MAX_TURNS,
            },
        )

    except Exception as exc:  # noqa: BLE001
        yield StreamEvent(
            type="error",
            data={"message": f"Agent loop error: {type(exc).__name__}: {exc}"},
        )
