"""
JARVIS Tool: memory
===================
Persist and retrieve agent facts across conversations.
Facts are stored as a JSON list in ~/.jarvis/agent_facts.json.
"""
from __future__ import annotations

import json
import pathlib
from datetime import datetime, timezone

from .base import ApprovalFlag, ToolResult
from ..persistence import append_jsonl, atomic_write_json

# ---------------------------------------------------------------------------
# Anthropic tool schema
# ---------------------------------------------------------------------------

DEFINITION: dict = {
    "name": "memory",
    "description": (
        "Read, write, or search persistent memory facts that survive across conversations. "
        "Use 'write' to record a new fact, 'read' to list all stored facts, "
        "and 'search' to find facts that match a keyword or phrase."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["read", "write", "search"],
                "description": "Memory operation to perform.",
            },
            "content": {
                "type": "string",
                "description": "The fact to save (used with 'write').",
            },
            "query": {
                "type": "string",
                "description": "Search term to filter facts (used with 'search').",
            },
        },
        "required": ["operation"],
    },
}

_FACTS_PATH = pathlib.Path.home() / ".jarvis" / "agent_facts.json"
_FACTS_LOG_PATH = _FACTS_PATH.with_name("agent_facts_log.jsonl")
_FACTS_STATE_LOG_PATH = _FACTS_PATH.with_name("agent_facts_state_log.jsonl")


# ---------------------------------------------------------------------------
# Approval logic
# ---------------------------------------------------------------------------

def needs_approval(inputs: dict) -> ApprovalFlag:  # noqa: ARG001
    """Memory operations are low-risk; no approval required."""
    return ApprovalFlag.NONE


# ---------------------------------------------------------------------------
# Storage helpers
# ---------------------------------------------------------------------------

def _load_facts() -> list[dict]:
    """Load facts from disk; return empty list if file is missing or corrupt."""
    if not _FACTS_PATH.exists():
        facts = _load_facts_from_state_log()
        if facts:
            return facts
        return _load_facts_from_log()
    try:
        raw = _FACTS_PATH.read_text(encoding="utf-8")
        data = json.loads(raw)
        if isinstance(data, list) and data:
            return data
        facts = _load_facts_from_state_log()
        if facts:
            return facts
        return []
    except (json.JSONDecodeError, OSError):
        facts = _load_facts_from_state_log()
        if facts:
            return facts
        return _load_facts_from_log()


def _save_facts(facts: list[dict]) -> None:
    """Persist facts list to disk, creating parent directories as needed."""
    _FACTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    append_jsonl(
        _FACTS_LOG_PATH,
        {
            "saved_at": datetime.now(tz=timezone.utc).isoformat(timespec="seconds"),
            "facts": facts,
        },
    )
    append_jsonl(
        _FACTS_STATE_LOG_PATH,
        {
            "saved_at": datetime.now(tz=timezone.utc).isoformat(timespec="seconds"),
            "facts": facts,
        },
    )
    atomic_write_json(_FACTS_PATH, facts, ensure_ascii=False)


def _load_facts_from_log() -> list[dict]:
    if not _FACTS_LOG_PATH.exists():
        return []
    latest: list[dict] = []
    try:
        for line in _FACTS_LOG_PATH.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            facts = payload.get("facts")
            if isinstance(facts, list):
                latest = [dict(item) for item in facts if isinstance(item, dict)]
    except (json.JSONDecodeError, OSError):
        return []
    return latest


def _load_facts_from_state_log() -> list[dict]:
    if not _FACTS_STATE_LOG_PATH.exists():
        return []
    latest: list[dict] = []
    try:
        for line in _FACTS_STATE_LOG_PATH.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            facts = payload.get("facts")
            if isinstance(facts, list):
                latest = [dict(item) for item in facts if isinstance(item, dict)]
    except (json.JSONDecodeError, OSError):
        return []
    return latest


def _format_facts(facts: list[dict]) -> str:
    """Format a list of fact dicts as a human-readable numbered list."""
    if not facts:
        return "(no facts stored)"
    lines: list[str] = []
    for i, entry in enumerate(facts, start=1):
        fact = entry.get("fact", "")
        saved_at = entry.get("saved_at", "unknown time")
        lines.append(f"{i}. {fact}\n   [saved: {saved_at}]")
    return "\n\n".join(lines)


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

async def run(
    operation: str,
    content: str = "",
    query: str = "",
) -> ToolResult:
    """Perform the requested memory operation and return a ToolResult."""

    # ------------------------------------------------------------------
    # WRITE
    # ------------------------------------------------------------------
    if operation == "write":
        if not content.strip():
            return ToolResult(
                output="'content' is required to save a fact.", error=True
            )
        facts = _load_facts()
        entry = {
            "fact": content.strip(),
            "saved_at": datetime.now(tz=timezone.utc).isoformat(timespec="seconds"),
        }
        facts.append(entry)
        try:
            _save_facts(facts)
        except Exception as exc:  # noqa: BLE001
            return ToolResult(
                output=f"Failed to save fact: {exc}", error=True
            )
        return ToolResult(
            output=f"Fact saved ({len(facts)} total facts stored):\n\n  {content.strip()}",
            error=False,
            metadata={"total_facts": len(facts), "path": str(_FACTS_PATH)},
        )

    # ------------------------------------------------------------------
    # READ
    # ------------------------------------------------------------------
    if operation == "read":
        facts = _load_facts()
        formatted = _format_facts(facts)
        return ToolResult(
            output=f"All stored facts ({len(facts)}):\n\n{formatted}",
            error=False,
            metadata={"total_facts": len(facts), "path": str(_FACTS_PATH)},
        )

    # ------------------------------------------------------------------
    # SEARCH
    # ------------------------------------------------------------------
    if operation == "search":
        if not query.strip():
            return ToolResult(
                output="'query' is required for the search operation.", error=True
            )
        facts = _load_facts()
        needle = query.strip().lower()
        matches = [f for f in facts if needle in f.get("fact", "").lower()]
        formatted = _format_facts(matches)
        return ToolResult(
            output=(
                f"Facts matching '{query}' ({len(matches)} of {len(facts)}):\n\n{formatted}"
            ),
            error=False,
            metadata={
                "query": query,
                "matches": len(matches),
                "total_facts": len(facts),
            },
        )

    # ------------------------------------------------------------------
    # Unknown operation
    # ------------------------------------------------------------------
    return ToolResult(
        output=f"Unknown operation: '{operation}'. Must be one of: read, write, search.",
        error=True,
    )
