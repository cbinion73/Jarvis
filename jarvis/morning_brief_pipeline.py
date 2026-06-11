"""
JARVIS Morning Brief Pipeline — Magic Moment 1

Generates the companion-style Morning Brief: "JARVIS understands the state of
your life better than you do right now."

Pulls from live sources only. If a source is unavailable, says so honestly.
Never presents inferred or cached data as live.

Sections:
  1. What Changed Since Yesterday
  2. What Matters Today
  3. What May Have Been Forgotten
  4. What JARVIS Prepared
  5. Single Recommendation
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Data root
# ---------------------------------------------------------------------------

_DATA_ROOT = Path("data")


def _load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


# ---------------------------------------------------------------------------
# Signal gatherers
# ---------------------------------------------------------------------------


def _gather_git_activity(since_hours: int = 24) -> dict:
    """Pull recent git commits as a signal for 'What JARVIS did'."""
    try:
        since = f"{since_hours} hours ago"
        result = subprocess.run(
            ["git", "log", f"--since={since}", "--format=%h|%ci|%s", "--no-merges"],
            capture_output=True,
            text=True,
            timeout=8,
            cwd=Path("."),
        )
        lines = [l.strip() for l in result.stdout.splitlines() if l.strip()]
        commits = []
        for line in lines:
            parts = line.split("|", 2)
            if len(parts) == 3:
                commits.append({"hash": parts[0], "timestamp": parts[1], "message": parts[2]})
        return {"available": True, "commits": commits, "count": len(commits)}
    except Exception as exc:
        return {"available": False, "error": str(exc), "commits": [], "count": 0}


def _gather_memory_entries(actor_id: str = "chris") -> dict:
    """Load recent memory entries — titles and summaries only (no encrypted payloads)."""
    path = _DATA_ROOT / "memory" / "entries.json"
    raw = _load_json(path, [])
    entries = raw if isinstance(raw, list) else []
    actor_entries = [
        e for e in entries
        if str(e.get("subject_user_id", "")).lower() == actor_id
        or str(e.get("owner", "")).lower() == actor_id
    ]
    # Sort by created_at descending
    actor_entries.sort(key=lambda e: str(e.get("created_at", "")), reverse=True)
    recent = actor_entries[:10]
    return {
        "available": bool(path.exists()),
        "total_count": len(actor_entries),
        "recent": [
            {"title": e.get("title", ""), "summary": e.get("summary", ""), "created_at": e.get("created_at", ""), "memory_type": e.get("memory_type", "")}
            for e in recent
        ],
    }


def _gather_profile_facts(actor_id: str = "chris") -> dict:
    """Load profile facts for the actor."""
    path = _DATA_ROOT / "memory" / "profile_facts.json"
    raw = _load_json(path, [])
    facts = raw if isinstance(raw, list) else []
    actor_facts = [f for f in facts if str(f.get("subject_user_id", "")).lower() == actor_id]
    return {
        "available": bool(path.exists()),
        "count": len(actor_facts),
        "facts": [
            {"title": f.get("title", ""), "summary": f.get("summary", ""), "lane": f.get("lane", "")}
            for f in actor_facts[:8]
        ],
    }


def _gather_workstreams() -> dict:
    """Load workstream items and their status distribution."""
    path = _DATA_ROOT / "workstreams" / "items.json"
    raw = _load_json(path, [])
    items = raw if isinstance(raw, list) else []
    statuses: dict[str, int] = {}
    for item in items:
        s = str(item.get("status", "unknown"))
        statuses[s] = statuses.get(s, 0) + 1
    stalled = [
        {"title": i.get("title", i.get("label", "")), "status": i.get("status", ""), "lane_id": i.get("lane_id", "")}
        for i in items
        if str(i.get("status", "")).lower() in ("blocked", "paused", "stalled", "discovered")
    ][:5]
    active = [
        {"title": i.get("title", i.get("label", "")), "status": i.get("status", ""), "lane_id": i.get("lane_id", "")}
        for i in items
        if str(i.get("status", "")).lower() in ("researching", "experiment_planned", "screened")
    ][:5]
    return {
        "available": bool(path.exists()),
        "total": len(items),
        "statuses": statuses,
        "stalled": stalled,
        "active": active,
    }


def _gather_agent_health() -> dict:
    """Load agent background state."""
    path = _DATA_ROOT / "agents" / "background_state.json"
    raw = _load_json(path, {})
    if not raw:
        return {"available": False, "agents": {}, "degraded": [], "blocked": [], "active_mode": ""}
    agents = raw.get("agents", {})
    degraded = [
        {"name": name, "state": info.get("state", ""), "health": info.get("health_status", ""), "attention": info.get("attention_required", False)}
        for name, info in agents.items()
        if info.get("health_status") in ("degraded", "blocked", "missed", "error")
    ]
    running = [name for name, info in agents.items() if info.get("state") == "running"]
    return {
        "available": True,
        "active_mode": str(raw.get("active_mode", "")),
        "last_tick_at": str(raw.get("last_tick_at", "")),
        "total_agents": len(agents),
        "running_count": len(running),
        "degraded": degraded,
        "degraded_count": len(degraded),
        "quiet_hours_active": bool(raw.get("quiet_hours_active", False)),
    }


def _gather_open_loops_raw() -> dict:
    """Read open loop signals directly from workstream + approvals data."""
    loops = []
    # Approvals
    approvals_path = _DATA_ROOT / "workstreams" / "approvals.json"
    raw = _load_json(approvals_path, [])
    for item in (raw if isinstance(raw, list) else []):
        if str(item.get("status", "")).lower() in ("pending", ""):
            loops.append({
                "title": str(item.get("request", item.get("title", "Pending approval"))),
                "domain": "approvals",
                "kind": "approval",
            })
    # Mission/catalyst signals
    signals_path = _DATA_ROOT / "catalyst" / "signals.json"
    raw = _load_json(signals_path, [])
    for s in (raw if isinstance(raw, list) else [])[:3]:
        loops.append({
            "title": str(s.get("title", s.get("signal", ""))),
            "domain": "catalyst",
            "kind": "signal",
        })
    return {"available": True, "loops": loops[:8], "count": len(loops)}


def _gather_catalyst_briefing_runs() -> dict:
    """Check if any catalyst briefing runs completed recently."""
    path = _DATA_ROOT / "catalyst" / "briefing_runs.json"
    raw = _load_json(path, [])
    runs = raw if isinstance(raw, list) else []
    recent = [r for r in runs if r.get("status") in ("complete", "done")][-3:]
    return {"available": bool(path.exists()), "recent_runs": recent, "count": len(recent)}


# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------


def _hours_since(iso_str: str) -> float | None:
    if not iso_str:
        return None
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - dt
        return delta.total_seconds() / 3600
    except Exception:
        return None


def _friendly_elapsed(hours: float | None) -> str:
    if hours is None:
        return "unknown"
    if hours < 1:
        return "less than an hour ago"
    if hours < 24:
        h = int(hours)
        return f"{h} hour{'s' if h != 1 else ''} ago"
    days = int(hours / 24)
    return f"{days} day{'s' if days != 1 else ''} ago"


# ---------------------------------------------------------------------------
# Synthesis — build the brief in companion voice
# ---------------------------------------------------------------------------


@dataclass
class MorningBriefResult:
    generated_at: str
    actor: str
    greeting: str
    what_changed: list[str] = field(default_factory=list)
    what_matters: list[str] = field(default_factory=list)
    may_have_forgotten: list[str] = field(default_factory=list)
    jarvis_prepared: list[str] = field(default_factory=list)
    recommendation: str = ""
    truth_labels: dict = field(default_factory=dict)
    raw_signals: dict = field(default_factory=dict)
    generated_ok: bool = True
    error: str = ""


def _greeting(actor: str) -> str:
    now = datetime.now()
    hour = now.hour
    if hour < 12:
        period = "Morning"
    elif hour < 17:
        period = "Afternoon"
    else:
        period = "Evening"
    day = now.strftime("%A, %B %-d")
    return f"Good {period}, {actor}. It's {day}. I've been paying attention."


def generate_morning_brief(actor_name: str = "Chris") -> MorningBriefResult:
    """
    Synchronous Morning Brief generation. Pulls from live data files.
    Call from an async context via asyncio.to_thread().
    """
    actor_id = actor_name.lower()
    now_iso = datetime.now(timezone.utc).isoformat()

    result = MorningBriefResult(
        generated_at=now_iso,
        actor=actor_name,
        greeting=_greeting(actor_name),
    )

    # ---- Gather all signals ----
    git = _gather_git_activity(24)
    memory = _gather_memory_entries(actor_id)
    profile = _gather_profile_facts(actor_id)
    workstreams = _gather_workstreams()
    agents = _gather_agent_health()
    open_loops = _gather_open_loops_raw()
    catalyst = _gather_catalyst_briefing_runs()

    result.raw_signals = {
        "git": git,
        "memory": memory,
        "profile": profile,
        "workstreams": workstreams,
        "agents": agents,
        "open_loops": open_loops,
        "catalyst": catalyst,
    }

    # ---- Truth labels ----
    result.truth_labels = {
        "git_activity": "live" if git["available"] else "unavailable",
        "memory": "live" if memory["available"] else "unavailable",
        "profile_facts": "live" if profile["available"] else "unavailable",
        "workstreams": "live" if workstreams["available"] else "unavailable",
        "agents": "live" if agents["available"] else "unavailable",
        "health_data": "unavailable — health DB not connected locally",
        "calendar": "unavailable — Google Calendar not configured",
        "email": "unavailable — Gmail not configured",
    }

    # ---- Section 1: What Changed Since Yesterday ----
    changed: list[str] = []
    if git["available"] and git["count"] > 0:
        n = git["count"]
        msgs = [c["message"] for c in git["commits"][:3]]
        changed.append(f"{n} JARVIS commit{'s' if n != 1 else ''} landed in the last 24 hours.")
        for msg in msgs:
            changed.append(f"  · {msg}")
    elif git["available"]:
        changed.append("No new JARVIS commits in the last 24 hours.")

    if agents["available"]:
        if agents["degraded_count"] > 0:
            names = [a["name"] for a in agents["degraded"][:3]]
            changed.append(
                f"{agents['degraded_count']} agent{'s' if agents['degraded_count'] != 1 else ''} showing degraded or blocked health: {', '.join(names)}."
            )
        mode = agents.get("active_mode", "")
        if mode:
            changed.append(f"System running in {mode} mode.")
        last_tick = agents.get("last_tick_at", "")
        hours = _hours_since(last_tick)
        if hours is not None and hours > 2:
            changed.append(f"Last scheduler tick was {_friendly_elapsed(hours)} — may need attention.")

    if memory["available"] and memory["recent"]:
        newest = memory["recent"][0]
        created = newest.get("created_at", "")
        hours = _hours_since(created)
        if hours is not None and hours < 48:
            changed.append(f"A new memory was recorded {_friendly_elapsed(hours)}: \"{newest.get('title', '')}\"")

    if workstreams["available"]:
        statuses = workstreams.get("statuses", {})
        researching = statuses.get("researching", 0)
        if researching > 0:
            changed.append(f"{researching} workstream items currently in research phase.")

    if not changed:
        changed.append("Signal sources are limited locally — full change detection requires a live server.")

    result.what_changed = changed

    # ---- Section 2: What Matters Today ----
    matters: list[str] = []

    if agents["degraded"]:
        attn = [a for a in agents["degraded"] if a.get("attention")]
        if attn:
            matters.append(f"Review {len(attn)} agent{'s' if len(attn) != 1 else ''} flagged for attention ({', '.join(a['name'] for a in attn[:2])}).")

    if workstreams["available"]:
        active = workstreams.get("active", [])
        if active:
            matters.append(f"Active workstreams: {len(active)} items in motion. Top: \"{active[0]['title'][:60]}\"")

    if open_loops["count"] > 0:
        matters.append(f"{open_loops['count']} open loop{'s' if open_loops['count'] != 1 else ''} need resolution.")

    # Always surface the core missions
    matters.append("JARVIS build progress — review overnight commits before making roadmap decisions.")
    matters.append("Health systems are not reporting. Manual check-in recommended.")

    if catalyst["count"] > 0:
        matters.append(f"Catalyst pipeline has {catalyst['count']} completed briefing run{'s' if catalyst['count'] != 1 else ''}.")

    result.what_matters = matters[:6]

    # ---- Section 3: What May Have Been Forgotten ----
    forgotten: list[str] = []

    if memory["available"] and memory["total_count"] > 0:
        forgotten.append(
            f"You have {memory['total_count']} memory entries. Most recent: \"{memory['recent'][0]['title'] if memory['recent'] else 'unknown'}\"."
        )

    if profile["available"] and profile["count"] > 0:
        forgotten.append(
            f"JARVIS has {profile['count']} profile facts about you — these shape every brief and response."
        )

    if workstreams["available"]:
        stalled = workstreams.get("stalled", [])
        if stalled:
            forgotten.append(f"{len(stalled)} workstream item{'s' if len(stalled) != 1 else ''} in discovered/stalled state — not yet in motion.")

    forgotten.append("Health logging: no data from Dexcom, Apple Health, or BP readings in this session.")
    forgotten.append("Calendar context: Google Calendar not connected — deadlines and appointments are not visible.")

    result.may_have_forgotten = forgotten[:6]

    # ---- Section 4: What JARVIS Prepared ----
    prepared: list[str] = []

    if git["available"] and git["count"] > 0:
        prepared.append(f"Built and committed {git['count']} code change{'s' if git['count'] != 1 else ''} to the JARVIS codebase.")
        # Show specific commits
        for c in git["commits"][:4]:
            prepared.append(f"  · {c['message']}")

    if agents["available"]:
        running_count = agents.get("running_count", 0)
        total = agents.get("total_agents", 0)
        prepared.append(f"Maintained {running_count} of {total} background agents.")

    if memory["available"]:
        prepared.append(f"Memory system is live with {memory['total_count']} entries and {profile['count']} profile facts.")

    if not prepared:
        prepared.append("No verified JARVIS activity to report in the last 24 hours.")
        prepared.append("Local data sources are available; live server signals require deployment.")

    result.jarvis_prepared = prepared[:8]

    # ---- Section 5: Single Recommendation ----
    if agents["degraded_count"] > 0 and any(a.get("attention") for a in agents["degraded"]):
        result.recommendation = (
            f"Start by reviewing the {agents['degraded_count']} degraded agent{'s' if agents['degraded_count'] != 1 else ''} "
            "— they may be blocking overnight work."
        )
    elif git["count"] > 3:
        result.recommendation = (
            f"You have {git['count']} commits from the last 24 hours. "
            "Spend 20 minutes reviewing what changed before making any new roadmap decisions."
        )
    elif open_loops["count"] > 3:
        result.recommendation = (
            f"Clear {open_loops['count']} open loops before starting new work. "
            "Resolution rate matters more than throughput."
        )
    else:
        result.recommendation = (
            "Connect Google Calendar and Gmail to unlock the full operating picture. "
            "That is the single highest-leverage action to make JARVIS aware of your actual day."
        )

    return result


async def generate_morning_brief_async(actor_name: str = "Chris") -> MorningBriefResult:
    """Async wrapper — runs generation in a thread to avoid blocking the event loop."""
    import asyncio
    return await asyncio.to_thread(generate_morning_brief, actor_name)
