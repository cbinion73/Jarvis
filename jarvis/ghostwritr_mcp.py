"""
ghostwritr_mcp.py — Ghostwritr MCP Bridge
==========================================
Exposes Ghostwritr book data as MCP tools so Claude and JARVIS agents
can read/write Ghostwritr content directly.

Registered in ~/.claude/settings.json as a stdio MCP server.

Tools:
    • ghostwritr_list_books     — list all books with status
    • ghostwritr_get_book       — full book details + stages
    • ghostwritr_get_manuscript — chapter text content
    • ghostwritr_get_promise    — book's core promise / pitch
    • ghostwritr_get_stages     — all writing stages + progress
    • ghostwritr_update_stage   — mark a stage done/in-progress/etc.
    • ghostwritr_send_to_jarvis — push a book event to JARVIS
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

# ---------------------------------------------------------------------------
# MCP instance
# ---------------------------------------------------------------------------
mcp = FastMCP(
    name="Ghostwritr",
    instructions=(
        "You are connected to Ghostwritr — a creative writing assistant app. "
        "Use ghostwritr_list_books to discover books, then ghostwritr_get_book, "
        "ghostwritr_get_promise, ghostwritr_get_manuscript for details. "
        "Use ghostwritr_send_to_jarvis to trigger JARVIS actions (launch, tasks, ideas)."
    ),
)

# ---------------------------------------------------------------------------
# Bridge initialisation (lazy singleton)
# ---------------------------------------------------------------------------
_bridge = None

def _get_bridge():
    global _bridge
    if _bridge is not None:
        return _bridge
    # Add jarvis package to path when running as stdio subprocess
    jarvis_root = Path(__file__).parent.parent
    if str(jarvis_root) not in sys.path:
        sys.path.insert(0, str(jarvis_root))
    try:
        from jarvis.ghostwritr_bridge import GhostwritrBridge
        _bridge = GhostwritrBridge()
    except ImportError:
        try:
            from ghostwritr_bridge import GhostwritrBridge
            _bridge = GhostwritrBridge()
        except Exception as exc:
            raise RuntimeError(f"Cannot import GhostwritrBridge: {exc}") from exc
    return _bridge


def _fmt_stage(s: dict) -> str:
    status_icon = {
        "COMMITTED": "✅", "READY_FOR_REVIEW": "👁", "IN_PROGRESS": "⏳",
        "PENDING": "⬜", "SKIPPED": "⏭",
    }.get(s.get("status", ""), "•")
    return f"{status_icon} {s.get('stageKey', s.get('stage_key', '?'))} [{s.get('status', '?')}]"


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def ghostwritr_list_books(status_filter: str = "") -> str:
    """
    List all books in Ghostwritr with their status and stage progress.

    Args:
        status_filter: Optional filter — 'DRAFT', 'EDITING', 'PUBLISHED'. Empty = all.
    """
    bridge = _get_bridge()
    try:
        books = bridge.get_active_books()
    except Exception as exc:
        return f"Error loading books: {exc}"
    if status_filter:
        books = [b for b in books if b.book_status.upper() == status_filter.upper()]
    if not books:
        return "No books found."
    lines = [f"📚 {len(books)} book(s) in Ghostwritr:"]
    for b in books:
        progress = f"{b.stages_complete}/{b.total_stages} stages"
        lines.append(f"  • [{b.slug}] {b.title} — {b.book_status} | {progress} | stage: {b.current_stage}")
    return "\n".join(lines)


@mcp.tool()
def ghostwritr_get_book(slug: str) -> str:
    """
    Get full details for a Ghostwritr book including all stages.

    Args:
        slug: The book slug (e.g. 'the-thinking-partner').
    """
    bridge = _get_bridge()
    try:
        pairs = bridge._list_books_with_stages()
    except Exception as exc:
        return f"Error: {exc}"
    for book_row, stages in pairs:
        if book_row.get("slug") == slug:
            lines = [
                f"📖 {book_row.get('titleWorking') or 'Untitled'} ({slug})",
                f"  Status: {book_row.get('status', '?')}",
                f"  Workflow: {book_row.get('workflowType', '?')}",
                f"  Subtitle: {book_row.get('subtitle') or '—'}",
                f"  Updated: {str(book_row.get('updatedAt', ''))[:10]}",
                f"\n  Stages ({len(stages)}):",
            ]
            for s in stages:
                lines.append(f"    {_fmt_stage(s)}")
            return "\n".join(lines)
    return f"Book '{slug}' not found."


@mcp.tool()
def ghostwritr_get_stages(slug: str) -> str:
    """
    Get the writing stage progress for a book — which stages are done,
    in progress, or pending.

    Args:
        slug: The book slug.
    """
    bridge = _get_bridge()
    try:
        pairs = bridge._list_books_with_stages()
    except Exception as exc:
        return f"Error: {exc}"
    for book_row, stages in pairs:
        if book_row.get("slug") == slug:
            committed = [s for s in stages if s.get("status") == "COMMITTED"]
            in_prog   = [s for s in stages if s.get("status") == "IN_PROGRESS"]
            review    = [s for s in stages if s.get("status") == "READY_FOR_REVIEW"]
            pending   = [s for s in stages if s.get("status") == "PENDING"]
            lines = [
                f"Stage progress for '{slug}' ({len(committed)}/{len(stages)} complete):",
                f"  ✅ Done ({len(committed)}): {', '.join(s.get('stageKey','?') for s in committed) or 'none'}",
                f"  ⏳ In progress ({len(in_prog)}): {', '.join(s.get('stageKey','?') for s in in_prog) or 'none'}",
                f"  👁 Ready for review ({len(review)}): {', '.join(s.get('stageKey','?') for s in review) or 'none'}",
                f"  ⬜ Pending ({len(pending)}): {', '.join(s.get('stageKey','?') for s in pending) or 'none'}",
            ]
            return "\n".join(lines)
    return f"Book '{slug}' not found."


@mcp.tool()
def ghostwritr_get_promise(slug: str) -> str:
    """
    Get the book's core promise / elevator pitch — the foundational
    statement of what the book delivers to readers.

    Args:
        slug: The book slug.
    """
    bridge = _get_bridge()
    try:
        promise = bridge.get_promise(slug) if hasattr(bridge, "get_promise") else None
        if promise:
            if isinstance(promise, dict):
                text = promise.get("content") or promise.get("text") or json.dumps(promise, indent=2)
            else:
                text = str(promise)
            return f"📝 Promise for '{slug}':\n\n{text}"
        # Fallback: get artifact directly from DB
        if hasattr(bridge, "_db") and bridge._db:
            artifacts = bridge._db.get_book_artifacts(slug, artifact_type="promise") if hasattr(bridge._db, "get_book_artifacts") else []
            if artifacts:
                return f"📝 Promise for '{slug}':\n\n{artifacts[0].get('content','(empty)')}"
        return f"No promise found for '{slug}'."
    except Exception as exc:
        return f"Error: {exc}"


@mcp.tool()
def ghostwritr_get_manuscript(slug: str, max_chars: int = 8000) -> str:
    """
    Get the manuscript content for a book — useful for generating
    launch assets, summaries, and marketing copy.

    Args:
        slug: The book slug.
        max_chars: Maximum characters to return (default 8000 to fit context).
    """
    bridge = _get_bridge()
    try:
        manuscript = bridge.get_manuscript(slug) if hasattr(bridge, "get_manuscript") else None
        if manuscript:
            if isinstance(manuscript, dict):
                content = manuscript.get("content") or manuscript.get("text") or json.dumps(manuscript)
            else:
                content = str(manuscript)
            if len(content) > max_chars:
                content = content[:max_chars] + f"\n\n[...truncated at {max_chars} chars]"
            return f"📄 Manuscript for '{slug}':\n\n{content}"
        return f"No manuscript content found for '{slug}'."
    except Exception as exc:
        return f"Error: {exc}"


@mcp.tool()
def ghostwritr_send_to_jarvis(
    event_type: str,
    slug: str,
    payload: str = "{}",
) -> str:
    """
    Send an event from Ghostwritr to JARVIS — trigger launch pipeline,
    create tasks, push ideas, etc.

    Args:
        event_type: One of: 'trigger_launch', 'add_idea', 'create_task', 'stage_changed'.
        slug: The book slug this event relates to.
        payload: Optional JSON string with extra data for the event.
    """
    import httpx
    base = os.environ.get("JARVIS_MCP_BASE_URL", "http://127.0.0.1:8787").rstrip("/")
    try:
        data = json.loads(payload) if payload and payload != "{}" else {}
    except json.JSONDecodeError:
        data = {"raw": payload}

    body = {"event_type": event_type, "slug": slug, "source": "ghostwritr", **data}
    try:
        resp = httpx.post(f"{base}/api/webhooks/ghostwritr", json=body, timeout=10)
        resp.raise_for_status()
        result = resp.json()
        return f"✅ Event '{event_type}' sent to JARVIS: {result.get('message', 'ok')}"
    except Exception as exc:
        return f"❌ Failed to send to JARVIS: {exc}"


# ---------------------------------------------------------------------------
# Entry point — stdio for Claude Code registration
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    mcp.run(transport="stdio")
