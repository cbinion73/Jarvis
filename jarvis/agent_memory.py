"""
jarvis/agent_memory.py — Session memory for the JARVIS agent
=============================================================
Saves a summary at the end of each agent session.
Loads recent session summaries at the start of new sessions.
Shares the ~/.jarvis/agent_facts.json store with tools/memory.py.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

# ── Directory ──────────────────────────────────────────────────────────────

def get_memory_dir() -> Path:
    """
    Return (and create if needed) the directory where session summaries live.

    Returns:
        ~/.jarvis/agent_sessions/
    """
    memory_dir = Path.home() / ".jarvis" / "agent_sessions"
    memory_dir.mkdir(parents=True, exist_ok=True)
    return memory_dir


# ── Session summaries ──────────────────────────────────────────────────────

def save_session_summary(
    conversation_id: str,
    messages: list[dict],
    final_response: str,
) -> Path:
    """
    Persist a Markdown summary of the completed agent session to disk.

    The file is named ``{date}-{conversation_id[:8]}.md`` so sessions sort
    chronologically by filename and are human-readable in a file browser.

    Args:
        conversation_id:  UUID (or other string) identifying this session.
        messages:         Full conversation message list in Anthropic format.
        final_response:   The agent's last text response.

    Returns:
        The Path of the written summary file.
    """
    memory_dir = get_memory_dir()
    date_str = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    short_id = conversation_id[:8] if conversation_id else "unknown"
    filename = f"{date_str}-{short_id}.md"
    summary_path = memory_dir / filename

    # Extract user turns for the summary
    user_turns: list[str] = []
    for msg in messages:
        if msg.get("role") != "user":
            continue
        content = msg.get("content", "")
        if isinstance(content, str):
            user_turns.append(content.strip())
        elif isinstance(content, list):
            # Content blocks — pull text items only
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text = block.get("text", "").strip()
                    if text:
                        user_turns.append(text)

    # Build Markdown
    now_iso = datetime.now(tz=timezone.utc).isoformat(timespec="seconds")
    lines: list[str] = [
        f"# JARVIS Session Summary",
        f"",
        f"**Date:** {now_iso}",
        f"**Conversation ID:** {conversation_id}",
        f"",
        f"## User Requests",
        f"",
    ]

    if user_turns:
        for i, turn in enumerate(user_turns, start=1):
            # Indent multi-line turns so they read as a block quote
            indented = "\n> ".join(turn.splitlines())
            lines.append(f"{i}. > {indented}")
            lines.append("")
    else:
        lines.append("*(no user messages)*")
        lines.append("")

    lines += [
        f"## Final Agent Response",
        f"",
        final_response.strip() if final_response.strip() else "*(no response)*",
        f"",
    ]

    summary_path.write_text("\n".join(lines), encoding="utf-8")
    return summary_path


def load_recent_summaries(n: int = 3) -> str:
    """
    Load the *n* most recent session summary files and return them concatenated.

    Files are sorted by modification time (newest last, so the most recent
    session appears at the end of the returned string — closest to the model's
    attention when prepended to a system prompt).

    Returns:
        Concatenated Markdown content, or "" if no sessions exist yet.
    """
    memory_dir = get_memory_dir()
    md_files = list(memory_dir.glob("*.md"))

    if not md_files:
        return ""

    # Sort by mtime ascending so the most recent is last
    md_files.sort(key=lambda p: p.stat().st_mtime)
    recent = md_files[-n:]

    parts: list[str] = []
    for path in recent:
        try:
            content = path.read_text(encoding="utf-8")
            parts.append(content)
        except OSError:
            continue

    return "\n\n---\n\n".join(parts)


# ── Persistent facts ───────────────────────────────────────────────────────
# These functions share the same JSON store used by tools/memory.py so facts
# written by either path are visible to both.

_FACTS_PATH = Path.home() / ".jarvis" / "agent_facts.json"


def _load_facts_raw() -> list[dict]:
    """Load the raw facts list from disk; return [] on any error."""
    if not _FACTS_PATH.exists():
        return []
    try:
        data = json.loads(_FACTS_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _save_facts_raw(facts: list[dict]) -> None:
    """Persist facts list to disk, creating parent dirs as needed."""
    _FACTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _FACTS_PATH.write_text(
        json.dumps(facts, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )


def append_fact(fact: str) -> None:
    """
    Append a new fact to the shared ~/.jarvis/agent_facts.json store.

    Args:
        fact: Plain-text string to persist.
    """
    fact = fact.strip()
    if not fact:
        return
    facts = _load_facts_raw()
    facts.append({
        "fact": fact,
        "saved_at": datetime.now(tz=timezone.utc).isoformat(timespec="seconds"),
    })
    _save_facts_raw(facts)


def load_facts() -> str:
    """
    Return all stored facts as a formatted string suitable for inclusion in a
    system prompt or context block.

    Returns:
        A numbered list of facts with timestamps, or "" if none are stored.
    """
    facts = _load_facts_raw()
    if not facts:
        return ""

    lines: list[str] = ["=== STORED FACTS ===", ""]
    for i, entry in enumerate(facts, start=1):
        fact_text = entry.get("fact", "")
        saved_at = entry.get("saved_at", "unknown")
        lines.append(f"{i}. {fact_text}")
        lines.append(f"   [saved: {saved_at}]")
        lines.append("")

    lines.append("=== END FACTS ===")
    return "\n".join(lines)
