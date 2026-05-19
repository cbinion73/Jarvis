"""
mcp_server.py — JARVIS MCP server via FastMCP.

Exposes JARVIS tools over the Model Context Protocol so Claude Desktop,
Cursor, and other MCP clients can talk directly to JARVIS.

Run standalone (SSE transport on port 8788):
    python -m jarvis.mcp_server

Or mount into the FastAPI app (stdio transport for Claude Desktop):
    See jarvis/service.py — the /mcp route is added automatically.

Tools exposed:
    • jarvis_ask          — Send a question/request to JARVIS (full converse)
    • jarvis_briefing     — Get the morning briefing (with live RSS news)
    • jarvis_status       — Get service health + agent status
    • jarvis_reminders    — List pending reminders
    • jarvis_add_reminder — Add a new reminder
    • jarvis_weather      — Get current weather
    • jarvis_calendar     — Get today's calendar events
    • jarvis_chronicle    — Get recent chronicle entries
    • jarvis_approvals    — Get items waiting for approval
"""
from __future__ import annotations

import os
import json
import httpx
from typing import Any

from fastmcp import FastMCP

# ---------------------------------------------------------------------------
# MCP instance
# ---------------------------------------------------------------------------
mcp = FastMCP(
    name="JARVIS",
    instructions=(
        "You are connected to JARVIS — a personal AI operating system built on "
        "the Marvel S.H.I.E.L.D. aesthetic. Use jarvis_ask for general requests. "
        "Use the specialised tools for fast lookups (weather, calendar, briefing). "
        "JARVIS is running at the base URL configured in JARVIS_MCP_BASE_URL "
        "(default: http://127.0.0.1:8787)."
    ),
)

# Base URL for the JARVIS HTTP API
_BASE = os.environ.get("JARVIS_MCP_BASE_URL", "http://127.0.0.1:8787").rstrip("/")
_ACTOR = os.environ.get("JARVIS_MCP_ACTOR", "Chris")

# Shared async client (FastMCP handles the event loop)
_CLIENT: httpx.AsyncClient | None = None


def _client() -> httpx.AsyncClient:
    global _CLIENT
    if _CLIENT is None or _CLIENT.is_closed:
        _CLIENT = httpx.AsyncClient(base_url=_BASE, timeout=30.0)
    return _CLIENT


async def _get(path: str, **params: Any) -> dict:
    resp = await _client().get(path, params=params)
    resp.raise_for_status()
    return resp.json()


async def _post(path: str, body: dict) -> dict:
    resp = await _client().post(path, json=body)
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool()
async def jarvis_ask(request: str, room: str = "office") -> str:
    """
    Send any question or request to JARVIS and get a full response.

    This is the general-purpose tool. Use it for anything not covered
    by the more specific tools below.

    Args:
        request: What you want JARVIS to do or answer.
        room: Context room (default 'office'). Options: office, home, mobile.
    """
    result = await _post("/api/respond", {
        "actor": _ACTOR,
        "room": room,
        "request": request,
        "source": "mcp",
    })
    # The respond endpoint returns various shapes — normalise to a string
    if isinstance(result, dict):
        return (
            result.get("response")
            or result.get("text")
            or result.get("message")
            or json.dumps(result, indent=2)
        )
    return str(result)


@mcp.tool()
async def jarvis_briefing(actor: str = _ACTOR) -> str:
    """
    Get the JARVIS morning briefing — includes live RSS news headlines,
    weather, calendar summary, and JARVIS's narrative summary of the day.

    Args:
        actor: Name of the person to greet (default: Chris).
    """
    data = await _get("/api/briefing", actor=actor)
    briefing = data.get("briefing", "")
    sources = data.get("rss_sources", [])
    total = data.get("rss_articles", 0)
    header = f"[Live news: {total} articles from {', '.join(sources)}]\n\n" if sources else ""
    return header + briefing


@mcp.tool()
async def jarvis_status() -> str:
    """
    Get the current JARVIS system status — which services are up, LLM
    gateway health, agent activity, and bridge connections.
    """
    data = await _get("/api/status")
    if isinstance(data, list):
        lines = []
        for svc in data:
            icon = "✅" if svc.get("ok") else "❌"
            lines.append(f"{icon} {svc.get('name','?')}: {svc.get('detail','')}")
        return "\n".join(lines)
    return json.dumps(data, indent=2)


@mcp.tool()
async def jarvis_reminders() -> str:
    """
    List all pending (non-done) reminders stored in JARVIS.
    Returns a formatted list with priority indicators.
    """
    data = await _get("/api/reminders")
    items = data.get("reminders", [])
    if not items:
        return "No pending reminders."
    lines = []
    for r in items:
        pri_icon = "🔴" if r.get("priority") == "high" else "🔵" if r.get("priority") == "low" else "⚪"
        due = f" (due {r['due'][:10]})" if r.get("due") else ""
        lines.append(f"{pri_icon} [{r['id']}] {r['text']}{due}")
    return "\n".join(lines)


@mcp.tool()
async def jarvis_add_reminder(text: str, due: str = "", priority: str = "normal") -> str:
    """
    Add a new persistent reminder to JARVIS.

    Args:
        text: The reminder text (required).
        due: Optional ISO 8601 due date/time, e.g. '2026-05-20T09:00:00Z'.
        priority: 'high', 'normal', or 'low' (default: normal).
    """
    body: dict[str, Any] = {"text": text, "priority": priority}
    if due:
        body["due"] = due
    result = await _post("/api/reminders", body)
    r = result.get("reminder", {})
    return f"✅ Reminder added: [{r.get('id','')}] {r.get('text',text)}"


@mcp.tool()
async def jarvis_weather() -> str:
    """
    Get the current weather conditions and forecast from JARVIS.
    Uses the configured OpenWeather location (default: Alexandria, VA).
    """
    try:
        data = await _get("/api/weather")
        if isinstance(data, dict):
            current = data.get("current", data)
            desc = current.get("description", current.get("condition", ""))
            temp = current.get("temp_f", current.get("temperature", ""))
            feels = current.get("feels_like_f", "")
            humidity = current.get("humidity", "")
            wind = current.get("wind_mph", current.get("wind_speed", ""))
            parts = [f"{desc}", f"{temp}°F" if temp else ""]
            if feels:
                parts.append(f"feels like {feels}°F")
            if humidity:
                parts.append(f"humidity {humidity}%")
            if wind:
                parts.append(f"wind {wind} mph")
            return ", ".join(p for p in parts if p)
        return json.dumps(data, indent=2)
    except Exception as e:
        return f"Weather unavailable: {e}"


@mcp.tool()
async def jarvis_calendar(days: int = 1) -> str:
    """
    Get calendar events for today (or the next N days) from JARVIS.

    Args:
        days: Number of days to look ahead (1 = today only, 7 = week).
    """
    try:
        if days <= 1:
            data = await _get("/api/home/calendar/today")
            events = data.get("events", [])
            label = data.get("date", "Today")
        else:
            data = await _get("/api/home/calendar/upcoming", days=days)
            events = data.get("events", [])
            label = f"Next {days} days"

        if not events:
            return f"{label}: No events found."

        lines = [f"📅 {label} ({len(events)} events):"]
        for ev in events:
            time_str = ev.get("time") or ev.get("start_time") or ev.get("start", "")
            title = ev.get("title") or ev.get("summary", "Untitled")
            lines.append(f"  • {time_str} — {title}")
        return "\n".join(lines)
    except Exception as e:
        return f"Calendar unavailable: {e}"


@mcp.tool()
async def jarvis_chronicle(limit: int = 10) -> str:
    """
    Retrieve recent entries from the JARVIS Chronicle — the persistent
    memory log of significant events, decisions, and notes.

    Args:
        limit: Number of recent entries to return (default: 10, max: 50).
    """
    data = await _get("/api/chronicle/recent")
    entries = data.get("entries", [])[:min(limit, 50)]
    if not entries:
        return "No chronicle entries found."
    lines = [f"📖 Chronicle ({len(entries)} entries):"]
    for e in entries:
        ts = (e.get("ts") or e.get("created_at") or "")[:10]
        text = (e.get("content") or e.get("text") or "")[:200]
        lines.append(f"  [{ts}] {text}")
    return "\n".join(lines)


@mcp.tool()
async def jarvis_approvals() -> str:
    """
    List items currently waiting for your approval in JARVIS —
    agent decisions, purchases, published content, etc.
    """
    data = await _get("/api/approvals")
    items = data if isinstance(data, list) else data.get("approvals", data.get("items", []))
    if not items:
        return "No pending approvals. ✅"
    lines = [f"⚠ {len(items)} item(s) need your approval:"]
    for item in items:
        title = item.get("title") or item.get("description") or item.get("name") or str(item)
        agent = item.get("agent") or item.get("agent_id") or ""
        lines.append(f"  • {title}" + (f" [{agent}]" if agent else ""))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point — SSE transport for network access
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="JARVIS MCP Server")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8788, help="Port (default: 8788)")
    parser.add_argument(
        "--transport",
        choices=["sse", "streamable-http", "stdio"],
        default="sse",
        help="MCP transport (default: sse)",
    )
    args = parser.parse_args()

    print(f"🛡  JARVIS MCP Server starting on {args.transport}://{args.host}:{args.port}")
    print(f"    JARVIS API base: {_BASE}")
    print(f"    Actor: {_ACTOR}")
    print()

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.run(transport=args.transport, host=args.host, port=args.port)
