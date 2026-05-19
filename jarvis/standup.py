from __future__ import annotations

"""
JARVIS Daily Standup Engine — Epic 2 (Autonomous Loop)
=======================================================
Generates per-agent standup reports and aggregates them into the morning huddle.

Each agent reports:
  - Yesterday: what I did / what advanced
  - Today:     my plan and what I'm working on
  - Needs:     blockers / approvals needed from Chris

The huddle aggregator collects all reports and returns a single morning briefing
structured for the HUDDLE dashboard view.
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("jarvis.standup")

# All runtime agents that participate in standup
STANDUP_AGENTS = [
    "nick-fury",
    "catalyst-personal",
    "executive-watch",
    "memory-curator",
    "chronicle-curator",
    "system-steward",
    "kang",
    "natasha",
    "pepper",
    "ultron",
    "watcher",
]

# Friendly Marvel names for display
AGENT_NAMES: dict[str, str] = {
    "nick-fury":        "Nick Fury",
    "catalyst-personal":"Mantis",
    "executive-watch":  "Agent Coulson",
    "memory-curator":   "Wong",
    "chronicle-curator":"Disciple",
    "system-steward":   "HERBIE",
    "kang":             "Kang",
    "natasha":          "Black Widow",
    "pepper":           "Pepper Potts",
    "ultron":           "Ultron",
    "watcher":          "The Watcher",
    "storm":            "Storm",
    "fisk":             "Fisk",
    "howard-stark":     "Howard Stark",
    "thor":             "Thor",
    "gamora":           "Gamora",
    "nova":             "Nova",
    "agatha":           "Agatha",
    "spider-man":       "Spider-Man",
    "stan-lee":         "Stan Lee",
    "workshop-foreman": "Tony Stark",
}

AGENT_DOMAINS: dict[str, str] = {
    "nick-fury":        "command",
    "catalyst-personal":"opportunities & passive income",
    "executive-watch":  "executive support & research",
    "memory-curator":   "memory & knowledge",
    "chronicle-curator":"faith & journaling",
    "system-steward":   "system health",
    "kang":             "schedule & time",
    "natasha":          "communications",
    "pepper":           "household",
    "ultron":           "security",
    "watcher":          "archival & observation",
    "storm":            "weather",
    "fisk":             "finance",
    "howard-stark":     "passive income tracking",
    "thor":             "health & fitness",
    "gamora":           "relationships",
    "nova":             "learning",
    "agatha":           "occasions & gifting",
    "spider-man":       "signals & news",
    "stan-lee":         "publishing",
    "workshop-foreman": "maker & workshop",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# StandupReport dataclass
# ---------------------------------------------------------------------------

@dataclass
class StandupReport:
    agent_id: str
    agent_name: str
    domain: str
    generated_at: str = field(default_factory=_now_iso)
    date: str = field(default_factory=_today)

    # Core standup fields
    yesterday: str = ""    # What I did / accomplished
    today: str = ""        # What I plan to do
    needs: str = ""        # What I need from Chris (blockers, approvals)

    # Supporting data
    active_work_count: int = 0
    proposed_items: list[dict] = field(default_factory=list)   # awaiting approval
    recent_results: list[dict] = field(default_factory=list)   # recently completed
    highlights: list[str] = field(default_factory=list)        # bullet points

    # Status
    source: str = "generated"   # "llm" | "stub" | "generated"
    error: str = ""


# ---------------------------------------------------------------------------
# LLM standup generation
# ---------------------------------------------------------------------------

def _build_standup_prompt(
    agent_id: str,
    agent_name: str,
    domain: str,
    work_summary: dict,
    recent_scheduler_work: list[dict],
) -> str:
    """Build a prompt for the LLM to generate a standup report."""

    active_count = work_summary.get("active_count", 0)
    needs_approval = work_summary.get("needs_approval", [])
    recently_advanced = work_summary.get("recently_advanced", [])
    status_counts = work_summary.get("status_counts", {})

    approval_text = ""
    if needs_approval:
        approval_text = "\n\nProposals awaiting Chris's approval:\n" + "\n".join(
            f"  - [{i['domain']}] {i['title']}: {i['proposal'][:100]}"
            for i in needs_approval[:3]
        )

    advanced_text = ""
    if recently_advanced:
        advanced_text = "\n\nItems that advanced in the last 24 hours:\n" + "\n".join(
            f"  - {i['title']} → {i['status']}"
            for i in recently_advanced[:5]
        )

    recent_work_text = ""
    if recent_scheduler_work:
        recent_work_text = "\n\nRecent scheduled work results:\n" + "\n".join(
            f"  - {w.get('result_text', '')[:120]}"
            for w in recent_scheduler_work[:3]
            if w.get("result_text")
        )

    status_text = ""
    if status_counts:
        parts = [f"{v} {k}" for k, v in status_counts.items() if v > 0]
        status_text = f"\nWork pipeline: {', '.join(parts)}"

    return f"""You are {agent_name}, a JARVIS agent responsible for: {domain}.

Prepare your daily standup report for Chris. Be concise, direct, and specific.
Use first-person voice (I did, I plan to, I need).
Each section should be 1-3 sentences maximum.

Your current work context:
- Active work items: {active_count}{status_text}{approval_text}{advanced_text}{recent_work_text}

Generate the standup in this exact JSON format:
{{
  "yesterday": "What I did / accomplished since last standup",
  "today": "My specific plan and focus for today",
  "needs": "What I need from Chris — be specific about approvals, decisions, or blockers. Say 'Nothing needed today' if clear.",
  "highlights": ["bullet 1", "bullet 2"]
}}

Be specific and honest. If no work was done, say so plainly. If you have proposals pending, call them out in 'needs'.
Return ONLY the JSON object, no other text."""


def _parse_llm_standup(raw: str) -> dict[str, Any]:
    """Parse LLM response into standup fields."""
    raw = raw.strip()
    # Strip markdown fences
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    try:
        return json.loads(raw)
    except Exception:
        # Try to find a JSON object
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(raw[start:end])
            except Exception:
                pass
    return {}


def _stub_standup(
    agent_id: str,
    agent_name: str,
    domain: str,
    work_summary: dict,
    recent_scheduler_work: list[dict],
) -> dict[str, Any]:
    """Generate a standup without LLM — data-driven stub."""
    active_count = work_summary.get("active_count", 0)
    needs_approval = work_summary.get("needs_approval", [])
    recently_advanced = work_summary.get("recently_advanced", [])
    status_counts = work_summary.get("status_counts", {})

    # Yesterday
    if recently_advanced:
        yesterday = f"Advanced {len(recently_advanced)} work item(s): " + ", ".join(
            f"'{i['title'][:40]}' → {i['status']}" for i in recently_advanced[:2]
        )
    elif recent_scheduler_work:
        first = recent_scheduler_work[0]
        rt = first.get("result_text", "")
        yesterday = rt[:140] + "…" if len(rt) > 140 else rt or f"Completed scheduled {domain} check."
    else:
        yesterday = f"Completed routine {domain} monitoring. No new work items advanced."

    # Today
    if active_count > 0:
        today = f"Continuing work on {active_count} active item(s) in my {domain} pipeline."
    else:
        today = f"Scanning {domain} domain for new opportunities and signals to dream up."

    # Needs
    if needs_approval:
        titles = ", ".join(f"'{i['title'][:30]}'" for i in needs_approval[:2])
        needs = f"Approval needed on {len(needs_approval)} proposal(s): {titles}."
    else:
        needs = "Nothing needed today — running independently."

    # Highlights
    highlights: list[str] = []
    for item in recently_advanced[:3]:
        highlights.append(f"{item['title'][:50]} moved to {item['status']}")
    if status_counts:
        dreamed = status_counts.get("dreamed", 0)
        proposed = status_counts.get("proposed", 0)
        tracking = status_counts.get("tracking", 0)
        if dreamed:
            highlights.append(f"{dreamed} idea(s) in dream stage")
        if proposed:
            highlights.append(f"{proposed} proposal(s) awaiting review")
        if tracking:
            highlights.append(f"{tracking} item(s) being tracked for effectiveness")

    return {
        "yesterday": yesterday,
        "today": today,
        "needs": needs,
        "highlights": highlights,
    }


def generate_standup(
    agent_id: str,
    runtime: Any | None = None,
    use_llm: bool = True,
) -> StandupReport:
    """
    Generate a standup report for a single agent.

    Pulls work store data + recent scheduler results, then either calls
    the LLM gateway for synthesis or falls back to a data-driven stub.
    """
    from .agent_work import get_work_store

    agent_name = AGENT_NAMES.get(agent_id, agent_id)
    domain = AGENT_DOMAINS.get(agent_id, "general operations")

    report = StandupReport(
        agent_id=agent_id,
        agent_name=agent_name,
        domain=domain,
    )

    # Get work store summary
    try:
        store = get_work_store(agent_id)
        work_summary = store.get_standup_summary()
        report.active_work_count = work_summary.get("active_count", 0)
        report.proposed_items = work_summary.get("needs_approval", [])
        report.recent_results = work_summary.get("recently_advanced", [])
    except Exception as exc:
        logger.warning("[%s] Work store error: %s", agent_id, exc)
        work_summary = {}

    # Get recent scheduler work items for this agent
    recent_scheduler_work: list[dict] = []
    try:
        from .scheduler import _get_runtime
        rt = runtime or _get_runtime()
        if rt is not None and hasattr(rt, "scheduler") and rt.scheduler is not None:
            sched_items = rt.scheduler._queue.get_by_agent(agent_id)
            recent_completed = [
                {"result_text": i.result_text, "completed_at": i.completed_at}
                for i in sched_items
                if i.status == "completed"
            ]
            recent_completed.sort(key=lambda x: x.get("completed_at", ""), reverse=True)
            recent_scheduler_work = recent_completed[:5]
    except Exception as exc:
        logger.debug("[%s] Scheduler history unavailable: %s", agent_id, exc)

    # Try LLM synthesis
    if use_llm:
        try:
            from .llm_gateway import get_gateway
            gateway = get_gateway()
            if gateway is not None:
                prompt = _build_standup_prompt(
                    agent_id, agent_name, domain, work_summary, recent_scheduler_work
                )
                response_text = gateway.simple_complete(prompt, max_tokens=400)
                parsed = _parse_llm_standup(response_text)
                if parsed.get("yesterday") and parsed.get("today"):
                    report.yesterday = parsed.get("yesterday", "")
                    report.today = parsed.get("today", "")
                    report.needs = parsed.get("needs", "Nothing needed today.")
                    report.highlights = parsed.get("highlights", [])
                    report.source = "llm"
                    return report
        except Exception as exc:
            logger.debug("[%s] LLM standup failed: %s", agent_id, exc)

    # Fallback to stub
    stub = _stub_standup(agent_id, agent_name, domain, work_summary, recent_scheduler_work)
    report.yesterday = stub["yesterday"]
    report.today = stub["today"]
    report.needs = stub["needs"]
    report.highlights = stub["highlights"]
    report.source = "stub"
    return report


# ---------------------------------------------------------------------------
# Huddle aggregator
# ---------------------------------------------------------------------------

@dataclass
class HuddleReport:
    date: str
    generated_at: str
    agent_reports: list[dict]       # list of StandupReport dicts
    approvals_needed: list[dict]    # cross-agent proposals pending
    highlights: list[str]           # top cross-agent highlights
    blockers: list[str]             # items needing Chris's action
    total_active_work: int = 0


def collect_all_standups(
    agent_ids: list[str] | None = None,
    runtime: Any | None = None,
    use_llm: bool = True,
) -> HuddleReport:
    """
    Run standup generation for all agents and aggregate into a HuddleReport.
    """
    from .agent_work import get_work_store

    ids = agent_ids or STANDUP_AGENTS
    reports: list[StandupReport] = []

    for agent_id in ids:
        try:
            rep = generate_standup(agent_id, runtime=runtime, use_llm=use_llm)
            reports.append(rep)
        except Exception as exc:
            logger.warning("[huddle] Failed to get standup for %s: %s", agent_id, exc)

    # Aggregate cross-agent data
    all_approvals: list[dict] = []
    all_highlights: list[str] = []
    blockers: list[str] = []
    total_active = 0

    for rep in reports:
        for pa in rep.proposed_items:
            all_approvals.append({
                "agent": rep.agent_name,
                "agent_id": rep.agent_id,
                **pa,
            })
        all_highlights.extend(
            f"[{rep.agent_name}] {h}" for h in rep.highlights[:2]
        )
        if rep.needs and "nothing needed" not in rep.needs.lower():
            blockers.append(f"{rep.agent_name}: {rep.needs}")
        total_active += rep.active_work_count

    return HuddleReport(
        date=_today(),
        generated_at=_now_iso(),
        agent_reports=[asdict(r) for r in reports],
        approvals_needed=all_approvals[:10],
        highlights=all_highlights[:12],
        blockers=blockers[:8],
        total_active_work=total_active,
    )


# ---------------------------------------------------------------------------
# Simple gateway helper (avoids circular import)
# ---------------------------------------------------------------------------

def _simple_complete_via_gateway(prompt: str, max_tokens: int = 400) -> str | None:
    """Call the LLM gateway with a simple prompt. Returns text or None."""
    try:
        from .llm_gateway import get_gateway
        gateway = get_gateway()
        if gateway is None:
            return None
        return gateway.simple_complete(prompt, max_tokens=max_tokens)
    except Exception:
        return None
