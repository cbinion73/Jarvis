"""
JARVIS Morning Brief Pipeline — Magic Moment 1

Generates the companion-style Morning Brief: "JARVIS understands the state of
your life better than you do right now."

Pulls from live sources only. If a source is unavailable, says so honestly.
Never presents inferred or cached data as live.

Sections:
  1. What Changed Since Yesterday
  2. What Matters Today
  3. What Is Waiting
  4. What JARVIS Did While You Were Away
  5. What May Have Been Forgotten
  6. What JARVIS Prepared
  7. Single Recommendation
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode

from .accounts import AccountRegistry
from .artifact_outcomes import ArtifactOutcomeStore
from .audit import AuditLog
from .autonomy_state import AutonomyStateStore
from .config import AppConfig
from .family_calendar import FamilyCalendarSupport
from .google_workspace import GoogleWorkspaceSupport
from .obsidian_context import ObsidianVaultSupport
from .research_tasks import ResearchTaskStore


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
    waiting_on_you = 0
    needs_revisit = 0
    # Approvals
    approvals_path = _DATA_ROOT / "workstreams" / "approvals.json"
    raw = _load_json(approvals_path, [])
    for item in (raw if isinstance(raw, list) else []):
        if str(item.get("status", "")).lower() in ("pending", ""):
            waiting_on_you += 1
            loops.append({
                "title": str(item.get("request", item.get("title", "Pending approval"))),
                "domain": "approvals",
                "kind": "approval",
            })
    # Mission/catalyst signals
    signals_path = _DATA_ROOT / "catalyst" / "signals.json"
    raw = _load_json(signals_path, [])
    for s in (raw if isinstance(raw, list) else [])[:3]:
        needs_revisit += 1
        loops.append({
            "title": str(s.get("title", s.get("signal", ""))),
            "domain": "catalyst",
            "kind": "signal",
        })
    return {
        "available": True,
        "loops": loops[:8],
        "count": len(loops),
        "summary": {
            "total": len(loops),
            "waiting_on_you": waiting_on_you,
            "needs_revisit": needs_revisit,
        },
    }


def _gather_catalyst_briefing_runs() -> dict:
    """Check if any catalyst briefing runs completed recently."""
    path = _DATA_ROOT / "catalyst" / "briefing_runs.json"
    raw = _load_json(path, [])
    runs = raw if isinstance(raw, list) else []
    recent = [r for r in runs if r.get("status") in ("complete", "done")][-3:]
    return {"available": bool(path.exists()), "recent_runs": recent, "count": len(recent)}


def _load_mission_dossiers() -> list[dict[str, Any]]:
    raw = _load_json(_DATA_ROOT / "missions" / "dossiers.json", [])
    if isinstance(raw, dict):
        records = raw.get("dossiers", [])
    else:
        records = raw
    return [dict(item) for item in list(records or []) if isinstance(item, dict)]


def _is_recent_iso(iso_str: str, *, since_hours: int = 24) -> bool:
    hours = _hours_since(str(iso_str or "").strip())
    return hours is not None and hours <= float(since_hours)


def _gather_assistant_activity_traces(since_hours: int = 24) -> dict[str, Any]:
    try:
        log = AuditLog(_DATA_ROOT / "logs", read_only=True)
        recent = [
            dict(item)
            for item in log.list_recent(limit=40, entry_type="assistant-action")
            if _is_recent_iso(str(item.get("timestamp") or ""), since_hours=since_hours)
        ]
        return {
            "available": True,
            "recent_count": len(recent),
            "recent": recent[:6],
        }
    except Exception as exc:
        return {"available": False, "error": str(exc), "recent_count": 0, "recent": []}


def _gather_mission_catch_up(since_hours: int = 24) -> dict[str, Any]:
    try:
        dossiers = _load_mission_dossiers()
        recent_dossiers = [item for item in dossiers if _is_recent_iso(str(item.get("updated_at") or ""), since_hours=since_hours)]
        recent_reports: list[dict[str, Any]] = []
        staged_missions: list[dict[str, Any]] = []
        for dossier in recent_dossiers:
            mission_id = str(dossier.get("mission_id") or "").strip()
            title = str(dossier.get("title") or dossier.get("brief") or "Mission").strip()
            for report in [dict(item) for item in list(dossier.get("delegation_reports") or []) if isinstance(item, dict)]:
                created_at = str(report.get("created_at") or dossier.get("updated_at") or "").strip()
                if _is_recent_iso(created_at, since_hours=since_hours):
                    recent_reports.append(
                        {
                            **report,
                            "mission_id": mission_id,
                            "mission_title": title,
                        }
                    )
            prepared_outputs = [
                dict(item)
                for item in list(dossier.get("outputs") or [])
                if isinstance(item, dict)
                and str(item.get("kind", "")).strip() == "background-prepared"
                and str(item.get("status", "")).strip() == "prepared"
            ]
            if prepared_outputs:
                staged_missions.append({"title": title, "prepared_count": len(prepared_outputs)})
        return {
            "available": True,
            "recent_dossier_count": len(recent_dossiers),
            "recent_report_count": len(recent_reports),
            "recent_reports": recent_reports[:6],
            "staged_mission_count": len(staged_missions),
            "staged_missions": staged_missions[:6],
        }
    except Exception as exc:
        return {
            "available": False,
            "error": str(exc),
            "recent_dossier_count": 0,
            "recent_report_count": 0,
            "recent_reports": [],
            "staged_mission_count": 0,
            "staged_missions": [],
        }


def _gather_research_catch_up(since_hours: int = 24) -> dict[str, Any]:
    try:
        store = ResearchTaskStore(_DATA_ROOT / "research_tasks", read_only=True)
        tasks = store.list_tasks()
        recent_tasks = [item for item in tasks if _is_recent_iso(str(item.get("updated_at") or item.get("created_at") or ""), since_hours=since_hours)]
        synthesis_tasks = [item for item in recent_tasks if isinstance(item.get("synthesis"), dict) and item.get("synthesis")]
        evidence_only_tasks = [
            item for item in recent_tasks
            if list(item.get("evidence_items") or []) and not (isinstance(item.get("synthesis"), dict) and item.get("synthesis"))
        ]
        return {
            "available": True,
            "recent_task_count": len(recent_tasks),
            "recent_synthesis_count": len(synthesis_tasks),
            "recent_evidence_only_count": len(evidence_only_tasks),
            "recent_tasks": recent_tasks[:6],
        }
    except Exception as exc:
        return {
            "available": False,
            "error": str(exc),
            "recent_task_count": 0,
            "recent_synthesis_count": 0,
            "recent_evidence_only_count": 0,
            "recent_tasks": [],
        }


def _gather_outcome_catch_up(since_hours: int = 24) -> dict[str, Any]:
    try:
        store = ArtifactOutcomeStore(_DATA_ROOT / "outcomes", read_only=True)
        records = [dict(item) for item in list(store.all_outcomes()) if isinstance(item, dict)]
        recent = [item for item in records if _is_recent_iso(str(item.get("recorded_at") or ""), since_hours=since_hours)]
        return {
            "available": True,
            "recent_count": len(recent),
            "recent": recent[:6],
        }
    except Exception as exc:
        return {"available": False, "error": str(exc), "recent_count": 0, "recent": []}


def _gather_autonomy_catch_up(since_hours: int = 24) -> dict[str, Any]:
    try:
        store = AutonomyStateStore(_DATA_ROOT / "autonomy_states", read_only=True)
        states = store.list_states()
        recent_states = [item for item in states if _is_recent_iso(str(item.get("updated_at") or item.get("created_at") or ""), since_hours=since_hours)]
        local_proofs = [
            item for item in recent_states
            if str(item.get("local_follow_through_status", "")).strip() == "local_proof_created"
        ]
        planned_only = [
            item for item in recent_states
            if str(item.get("local_follow_through_status", "")).strip() != "local_proof_created"
            and (
                bool(item.get("has_proposed_plan"))
                or str(item.get("readiness_state", "")).strip() not in {"", "not_ready"}
                or str(item.get("status", "")).strip() in {"queued", "in_progress", "blocked"}
            )
        ]
        return {
            "available": True,
            "recent_state_count": len(recent_states),
            "local_proof_count": len(local_proofs),
            "planned_only_count": len(planned_only),
            "recent_states": recent_states[:6],
        }
    except Exception as exc:
        return {
            "available": False,
            "error": str(exc),
            "recent_state_count": 0,
            "local_proof_count": 0,
            "planned_only_count": 0,
            "recent_states": [],
        }


def _gather_google_workspace_support(actor_id: str = "chris") -> dict:
    try:
        config = AppConfig.from_env()
        support = GoogleWorkspaceSupport(config)
        default_status = support.status().to_dict()
        client_secret = support.client_secret_summary()
        try:
            household = config.load_household()
            registry = AccountRegistry(household)
            google_accounts = [
                account
                for account in registry.list_accounts()
                if account.provider == "google" and (not actor_id or account.owner_user_id == actor_id)
            ]
        except Exception:
            google_accounts = []

        recorded_connected = [account for account in google_accounts if str(account.status).strip().lower() == "connected"]
        account_summaries: list[dict[str, Any]] = []
        for account in google_accounts[:4]:
            summary = support.summary(account)
            summary["account"] = account.to_dict()
            account_summaries.append(summary)
        usable_accounts = [entry for entry in account_summaries if bool((entry.get("status") or {}).get("connected"))]
        gmail_errors = [str(entry.get("gmail_error") or "").strip() for entry in usable_accounts if str(entry.get("gmail_error") or "").strip()]
        calendar_errors = [str(entry.get("calendar_error") or "").strip() for entry in usable_accounts if str(entry.get("calendar_error") or "").strip()]
        return {
            "available": True,
            "default_status": default_status,
            "client_secret": client_secret,
            "account_count": len(google_accounts),
            "recorded_connected_count": len(recorded_connected),
            "usable_connected_count": len(usable_accounts),
            "gmail_error_count": len(gmail_errors),
            "calendar_error_count": len(calendar_errors),
            "unread_email_count": sum(int((entry.get("counts") or {}).get("unread_emails") or 0) for entry in usable_accounts),
            "upcoming_event_count": sum(int((entry.get("counts") or {}).get("upcoming_events") or 0) for entry in usable_accounts),
            "accounts": [account.to_dict() for account in google_accounts],
            "usable_accounts": usable_accounts,
            "gmail_errors": gmail_errors,
            "calendar_errors": calendar_errors,
        }
    except Exception as exc:
        return {
            "available": False,
            "error": str(exc),
            "default_status": {},
            "client_secret": {"present": False, "path": "config/google_client_secret.json"},
            "account_count": 0,
            "recorded_connected_count": 0,
            "usable_connected_count": 0,
            "gmail_error_count": 0,
            "calendar_error_count": 0,
            "unread_email_count": 0,
            "upcoming_event_count": 0,
            "accounts": [],
            "usable_accounts": [],
            "gmail_errors": [],
            "calendar_errors": [],
        }


def _gather_family_calendar_support() -> dict:
    try:
        summary = FamilyCalendarSupport().summary()
        return {
            "available": True,
            "summary": summary,
            "connected": bool(summary.get("configured")) and not bool(summary.get("error")),
            "event_count": int((summary.get("counts") or {}).get("upcoming_events") or 0),
        }
    except Exception as exc:
        return {
            "available": False,
            "error": str(exc),
            "summary": {},
            "connected": False,
            "event_count": 0,
        }


def _gather_obsidian_support() -> dict:
    try:
        config = AppConfig.from_env()
        status = ObsidianVaultSupport(config.obsidian_vault_path, config.obsidian_index_path).status()
        return {
            "available": True,
            "status": status,
            "enabled": bool(status.get("enabled")),
        }
    except Exception as exc:
        return {
            "available": False,
            "error": str(exc),
            "status": {},
            "enabled": False,
        }


def _email_truth_label(google_support: dict[str, Any]) -> str:
    default = google_support.get("default_status") or {}
    if not google_support.get("available", False):
        return "degraded — Google Workspace support could not be inspected"
    if not bool(default.get("libraries_ready")):
        return "unavailable — Google bridge libraries are not installed"
    if not bool(default.get("credentials_file_present")):
        return "degraded — Google bridge is ready but config/google_client_secret.json is missing"
    if google_support.get("usable_connected_count", 0) > 0:
        if google_support.get("gmail_error_count", 0) > 0:
            return "degraded — Gmail is connected but unread inbox could not be retrieved"
        unread = int(google_support.get("unread_email_count") or 0)
        if unread > 0:
            return f"live — Gmail returned {unread} unread item{'s' if unread != 1 else ''}"
        return "connected-but-empty — Gmail is connected but no unread inbox items were retrieved"
    if bool(default.get("token_present")):
        return "degraded — Google token exists but is not currently valid"
    if google_support.get("recorded_connected_count", 0) > 0:
        return "degraded — Google account records exist but none are usable in this runtime"
    if google_support.get("account_count", 0) > 0:
        return "support-ready — Google bridge is configured but no mailbox token is connected"
    return "support-ready — Google bridge is configured but no Google mailbox account has been connected"


def _calendar_truth_label(google_support: dict[str, Any], family_calendar: dict[str, Any]) -> str:
    default = google_support.get("default_status") or {}
    family_summary = family_calendar.get("summary") or {}
    family_events = int(family_calendar.get("event_count") or 0)
    family_connected = bool(family_calendar.get("connected"))
    if not google_support.get("available", False) and not family_calendar.get("available", False):
        return "degraded — calendar support could not be inspected"
    if google_support.get("usable_connected_count", 0) > 0:
        if google_support.get("calendar_error_count", 0) > 0:
            if family_connected and family_events > 0:
                return f"live — family shared calendar returned {family_events} upcoming event{'s' if family_events != 1 else ''}; Google Calendar retrieval degraded"
            return "degraded — Google Calendar is connected but events could not be retrieved"
        google_events = int(google_support.get("upcoming_event_count") or 0)
        if google_events > 0:
            return f"live — Google Calendar returned {google_events} upcoming event{'s' if google_events != 1 else ''}"
        if family_connected and family_events > 0:
            return f"live — family shared calendar returned {family_events} upcoming event{'s' if family_events != 1 else ''}"
        return "connected-but-empty — calendar support is connected but no upcoming events were retrieved"
    if family_connected and family_events > 0:
        return f"live — family shared calendar returned {family_events} upcoming event{'s' if family_events != 1 else ''}"
    if family_connected:
        return "connected-but-empty — family shared calendar is connected but no upcoming events were retrieved"
    if not bool(default.get("libraries_ready")):
        return "unavailable — Google bridge libraries are not installed"
    if not bool(default.get("credentials_file_present")):
        return "degraded — calendar support is ready but config/google_client_secret.json is missing"
    if bool(default.get("token_present")):
        return "degraded — Google token exists but is not currently valid for calendar support"
    if google_support.get("account_count", 0) > 0:
        return "support-ready — calendar support is configured but no account token is connected"
    family_detail = str(family_summary.get("detail") or "").strip()
    if family_detail:
        return f"unavailable — {family_detail}"
    return "support-ready — calendar support exists but no live calendar source is connected"


def _obsidian_truth_label(obsidian_support: dict[str, Any]) -> str:
    status = obsidian_support.get("status") or {}
    if not obsidian_support.get("available", False):
        return "degraded — Obsidian support could not be inspected"
    if bool(status.get("enabled")):
        return "local — Obsidian vault is available for local retrieval"
    detail = str(status.get("detail") or "").strip()
    return f"unavailable — {detail}" if detail else "unavailable — Obsidian vault is not available"


def _google_recovery_recommendation(google_support: dict[str, Any]) -> str:
    default = google_support.get("default_status") or {}
    client_secret = google_support.get("client_secret") or {}
    credentials_path = str(client_secret.get("path") or "config/google_client_secret.json")
    if not google_support.get("available", False):
        return "Verify the Google Workspace support seam before relying on inbox or calendar signals in the Morning Brief."
    if not bool(default.get("libraries_ready")):
        return "Install the Google bridge libraries so JARVIS can inspect Gmail and Calendar support honestly in the Morning Brief."
    if not bool(default.get("credentials_file_present")):
        return f"Restore the Google OAuth client file at {credentials_path} so JARVIS can inspect Gmail and Calendar support honestly."
    if bool(default.get("token_present")) and google_support.get("usable_connected_count", 0) == 0:
        return "Refresh the Google connection token so JARVIS can truthfully read inbox and calendar signals again."
    if google_support.get("account_count", 0) > 0:
        return "Reconnect a usable Google mailbox/calendar account so JARVIS can pull live day signals instead of only support posture."
    return "Connect a Google mailbox/calendar account if you want the Morning Brief to include live inbox and calendar signals."


def _trace_truth_label(*, available: bool, has_recorded: bool, has_planned_only: bool = False, empty_detail: str) -> str:
    if not available:
        return f"degraded — {empty_detail}"
    if has_recorded:
        return "recorded"
    if has_planned_only:
        return "planned-only"
    return f"empty — {empty_detail}"


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
    what_is_waiting: list[str] = field(default_factory=list)
    while_you_were_away: list[str] = field(default_factory=list)
    may_have_forgotten: list[str] = field(default_factory=list)
    jarvis_prepared: list[str] = field(default_factory=list)
    recommendation: str = ""
    recommendation_action: dict[str, Any] = field(default_factory=dict)
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


def _what_is_waiting_lines(open_loops: dict[str, Any], google_workspace: dict[str, Any], email_truth: str) -> list[str]:
    waiting: list[str] = []

    unread_count = int(google_workspace.get("unread_email_count") or 0)
    if email_truth.startswith("live"):
        waiting.append(
            f"Inbox pressure: connected Gmail returned {unread_count} unread item{'s' if unread_count != 1 else ''}. This is waiting pressure, not thread understanding."
        )
    elif email_truth.startswith("connected-but-empty"):
        waiting.append("Inbox pressure: connected Gmail did not return unread items for this brief.")
    else:
        waiting.append(f"Inbox pressure is limited: {email_truth}.")

    if open_loops.get("available"):
        summary = dict(open_loops.get("summary") or {})
        loop_count = int(summary.get("total") or open_loops.get("count") or 0)
        waiting_count = int(summary.get("waiting_on_you") or 0)
        revisit_count = int(summary.get("needs_revisit") or 0)
        loops = list(open_loops.get("loops") or [])
        if loop_count > 0:
            top_title = str((loops[0] or {}).get("title") or "").strip() if loops else ""
            if waiting_count > 0 and revisit_count > 0:
                pressure_detail = (
                    f"{waiting_count} waiting on you and {revisit_count} due for revisit"
                )
            elif waiting_count > 0:
                pressure_detail = f"{waiting_count} waiting on you"
            elif revisit_count > 0:
                pressure_detail = f"{revisit_count} due for revisit"
            else:
                pressure_detail = ""
            if top_title:
                waiting.append(
                    (
                        f"System pressure: {loop_count} recorded open loop{'s' if loop_count != 1 else ''} need follow-through"
                        f"{' — ' + pressure_detail if pressure_detail else ''}. Top recorded item: \"{top_title}\"."
                    )
                )
            else:
                waiting.append(
                    (
                        f"System pressure: {loop_count} recorded open loop{'s' if loop_count != 1 else ''} need follow-through"
                        f"{' — ' + pressure_detail if pressure_detail else ''}."
                    )
                )
        else:
            waiting.append("System pressure: no recorded open loops are currently waiting in the local queue.")
    else:
        waiting.append("System pressure is limited: local open-loop state could not be inspected.")

    return waiting[:4]


def _recommendation_action(
    action_kind: str,
    *,
    title: str,
    detail: str,
    route: str = "",
    route_label: str = "",
    truth_note: str = "",
) -> dict[str, Any]:
    payload = {
        "action_kind": str(action_kind or "narrative_only").strip() or "narrative_only",
        "title": str(title or "").strip(),
        "detail": str(detail or "").strip(),
        "truth_note": str(truth_note or "").strip(),
    }
    cleaned_route = str(route or "").strip()
    cleaned_label = str(route_label or "").strip()
    if cleaned_route:
        payload["route"] = cleaned_route
    if cleaned_label:
        payload["route_label"] = cleaned_label
    return payload


def _object_specific_catch_up_action(
    mission_catch_up: dict[str, Any],
    research_catch_up: dict[str, Any],
    outcome_catch_up: dict[str, Any],
    autonomy_catch_up: dict[str, Any],
) -> dict[str, Any] | None:
    return_to = "/briefing-center"

    for report in [dict(item) for item in list(mission_catch_up.get("recent_reports") or []) if isinstance(item, dict)]:
        mission_id = str(report.get("mission_id") or "").strip()
        report_id = str(report.get("report_id") or "").strip()
        if mission_id and report_id:
            report_title = str(report.get("title") or "Delegation report").strip() or "Delegation report"
            route = (
                f"/mission-board/delegation-report/{quote(mission_id, safe='')}/{quote(report_id, safe='')}"
                f"?{urlencode({'return_to': return_to})}"
            )
            return _recommendation_action(
                "direct_route",
                title="Inspect latest delegation report",
                detail=f"{report_title} is a real completed delegation output and can be opened directly.",
                route=route,
                route_label="Open Delegation Report",
                truth_note="This opens a recorded delegation report. It does not imply any new delegated work ran beyond the stored output.",
            )

    for task in [dict(item) for item in list(research_catch_up.get("recent_tasks") or []) if isinstance(item, dict)]:
        task_id = str(task.get("task_id") or "").strip()
        synthesis = dict(task.get("synthesis") or {})
        if task_id and synthesis:
            task_title = str(task.get("title") or task.get("question") or "Research task").strip() or "Research task"
            route = (
                f"/mission-board/research-tasks/{quote(task_id, safe='')}"
                f"?{urlencode({'return_to': return_to})}"
            )
            return _recommendation_action(
                "direct_route",
                title="Inspect latest research synthesis",
                detail=f"{task_title} already has attached-evidence synthesis available for review.",
                route=route,
                route_label="Open Research Task",
                truth_note="This opens a recorded research task review. It does not imply broader source discovery beyond the attached evidence set.",
            )

    for outcome in [dict(item) for item in list(outcome_catch_up.get("recent") or []) if isinstance(item, dict)]:
        target_kind = str(outcome.get("target_kind") or "").strip()
        target_id = str(outcome.get("target_id") or "").strip()
        mission_id = str(outcome.get("mission_id") or "").strip()
        if target_kind and target_id:
            query: dict[str, str] = {"return_to": return_to}
            if mission_id:
                query["mission_id"] = mission_id
            route = (
                f"/mission-board/artifact-outcome/{quote(target_kind, safe='')}/{quote(target_id, safe='')}"
                f"?{urlencode(query)}"
            )
            return _recommendation_action(
                "direct_route",
                title="Inspect latest recorded outcome",
                detail="A recorded artifact outcome already exists and can be reviewed directly.",
                route=route,
                route_label="Open Outcome Review",
                truth_note="This opens a recorded outcome review. It does not imply automatic learning or behavior change occurred.",
            )

    for state in [dict(item) for item in list(autonomy_catch_up.get("recent_states") or []) if isinstance(item, dict)]:
        autonomy_id = str(state.get("autonomy_id") or "").strip()
        if autonomy_id and str(state.get("local_follow_through_status") or "").strip() == "local_proof_created":
            state_title = str(state.get("title") or state.get("objective") or "Autonomy state").strip() or "Autonomy state"
            route = (
                f"/mission-board/autonomy-states/{quote(autonomy_id, safe='')}"
                f"?{urlencode({'return_to': return_to})}"
            )
            return _recommendation_action(
                "direct_route",
                title="Inspect latest autonomy proof",
                detail=f"{state_title} has a recorded local follow-through proof available for direct review.",
                route=route,
                route_label="Open Autonomy State",
                truth_note="This opens a local proof record only. It does not imply broad autonomous execution or hidden follow-through.",
            )

    return None


def _while_you_were_away_lines(
    assistant_activity: dict[str, Any],
    mission_catch_up: dict[str, Any],
    research_catch_up: dict[str, Any],
    outcome_catch_up: dict[str, Any],
    autonomy_catch_up: dict[str, Any],
) -> list[str]:
    lines: list[str] = []

    recent_reports = int(mission_catch_up.get("recent_report_count") or 0)
    staged_missions = int(mission_catch_up.get("staged_mission_count") or 0)
    if recent_reports > 0:
        lines.append(
            f"Delegation catch-up: {recent_reports} delegation report"
            f"{'' if recent_reports == 1 else 's'} completed with inspectable output."
        )
    elif staged_missions > 0:
        lines.append(
            f"Mission staging: {staged_missions} mission workspace"
            f"{'' if staged_missions == 1 else 's'} refreshed with prepared next steps. This is staged work, not completed execution."
        )

    research_synthesis = int(research_catch_up.get("recent_synthesis_count") or 0)
    research_evidence_only = int(research_catch_up.get("recent_evidence_only_count") or 0)
    if research_synthesis > 0:
        lines.append(
            f"Research catch-up: {research_synthesis} task synthesis update"
            f"{'' if research_synthesis == 1 else 's'} recorded from attached evidence only."
        )
    elif research_evidence_only > 0:
        lines.append(
            f"Research catch-up: {research_evidence_only} task"
            f"{'' if research_evidence_only == 1 else 's'} gained attached evidence, but no synthesis was completed."
        )

    recent_outcomes = int(outcome_catch_up.get("recent_count") or 0)
    if recent_outcomes > 0:
        lines.append(
            f"Outcome review: {recent_outcomes} explicit artifact outcome record"
            f"{'' if recent_outcomes == 1 else 's'} captured."
        )

    autonomy_proofs = int(autonomy_catch_up.get("local_proof_count") or 0)
    autonomy_planned = int(autonomy_catch_up.get("planned_only_count") or 0)
    if autonomy_proofs > 0:
        lines.append(
            f"Autonomy proof: {autonomy_proofs} local follow-through proof packet"
            f"{'' if autonomy_proofs == 1 else 's'} recorded. This is local proof only, not broad autonomous execution."
        )
    elif autonomy_planned > 0:
        lines.append(
            f"Autonomy posture: {autonomy_planned} record"
            f"{'' if autonomy_planned == 1 else 's'} changed planning or readiness state only. No local follow-through proof was recorded."
        )

    recent_assistant_actions = int(assistant_activity.get("recent_count") or 0)
    if recent_assistant_actions > 0 and len(lines) < 4:
        latest = dict((assistant_activity.get("recent") or [None])[0] or {})
        latest_summary = str(latest.get("result_summary") or latest.get("detail") or "").strip()
        if latest_summary:
            lines.append(
                f"Recorded assistant activity: {recent_assistant_actions} assistant action"
                f"{'' if recent_assistant_actions == 1 else 's'} logged. Latest: {latest_summary}"
            )
        else:
            lines.append(
                f"Recorded assistant activity: {recent_assistant_actions} assistant action"
                f"{'' if recent_assistant_actions == 1 else 's'} logged in this runtime."
            )

    if not any(
        [
            recent_reports,
            research_synthesis,
            research_evidence_only,
            recent_outcomes,
            autonomy_proofs,
            autonomy_planned,
        ]
    ):
        lines.append(
            "No inspectable delegation, research, outcome, or autonomy traces were recorded in this runtime. "
            "Current catch-up is limited to staged mission state and other explicitly logged surfaces."
        )

    if not lines:
        lines.append("No recorded catch-up traces were visible in this runtime path.")

    return lines[:4]


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
    google_workspace = _gather_google_workspace_support(actor_id)
    family_calendar = _gather_family_calendar_support()
    obsidian = _gather_obsidian_support()
    assistant_activity = _gather_assistant_activity_traces()
    mission_catch_up = _gather_mission_catch_up()
    research_catch_up = _gather_research_catch_up()
    outcome_catch_up = _gather_outcome_catch_up()
    autonomy_catch_up = _gather_autonomy_catch_up()

    result.raw_signals = {
        "git": git,
        "memory": memory,
        "profile": profile,
        "workstreams": workstreams,
        "agents": agents,
        "open_loops": open_loops,
        "catalyst": catalyst,
        "google_workspace": google_workspace,
        "family_calendar": family_calendar,
        "obsidian": obsidian,
        "assistant_activity": assistant_activity,
        "mission_catch_up": mission_catch_up,
        "research_catch_up": research_catch_up,
        "outcome_catch_up": outcome_catch_up,
        "autonomy_catch_up": autonomy_catch_up,
    }

    # ---- Truth labels ----
    result.truth_labels = {
        "git_activity": "live" if git["available"] else "unavailable",
        "memory": "live" if memory["available"] else "unavailable",
        "profile_facts": "live" if profile["available"] else "unavailable",
        "workstreams": "live" if workstreams["available"] else "unavailable",
        "agents": "live" if agents["available"] else "unavailable",
        "open_loops": "live" if open_loops["available"] else "unavailable",
        "health_data": "unavailable — health DB not connected locally",
        "calendar": _calendar_truth_label(google_workspace, family_calendar),
        "email": _email_truth_label(google_workspace),
        "obsidian_context": _obsidian_truth_label(obsidian),
        "activity_trace": _trace_truth_label(
            available=bool(assistant_activity.get("available")),
            has_recorded=int(assistant_activity.get("recent_count") or 0) > 0,
            empty_detail="no recent assistant-action traces are visible",
        ),
        "delegation_trace": _trace_truth_label(
            available=bool(mission_catch_up.get("available")),
            has_recorded=int(mission_catch_up.get("recent_report_count") or 0) > 0,
            has_planned_only=int(mission_catch_up.get("staged_mission_count") or 0) > 0,
            empty_detail="no recent delegation reports are visible",
        ),
        "research_trace": _trace_truth_label(
            available=bool(research_catch_up.get("available")),
            has_recorded=int(research_catch_up.get("recent_synthesis_count") or 0) > 0,
            has_planned_only=int(research_catch_up.get("recent_evidence_only_count") or 0) > 0,
            empty_detail="no recent research-task traces are visible",
        ),
        "outcome_trace": _trace_truth_label(
            available=bool(outcome_catch_up.get("available")),
            has_recorded=int(outcome_catch_up.get("recent_count") or 0) > 0,
            empty_detail="no recent artifact outcome traces are visible",
        ),
        "autonomy_trace": _trace_truth_label(
            available=bool(autonomy_catch_up.get("available")),
            has_recorded=int(autonomy_catch_up.get("local_proof_count") or 0) > 0,
            has_planned_only=int(autonomy_catch_up.get("planned_only_count") or 0) > 0,
            empty_detail="no recent autonomy traces are visible",
        ),
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

    open_loop_summary = dict(open_loops.get("summary") or {})
    open_loop_total = int(open_loop_summary.get("total") or open_loops.get("count") or 0)
    open_loop_waiting = int(open_loop_summary.get("waiting_on_you") or 0)
    open_loop_revisit = int(open_loop_summary.get("needs_revisit") or 0)
    if open_loop_total > 0:
        if open_loop_waiting > 0 and open_loop_revisit > 0:
            waiting_phrase = (
                f"{open_loop_waiting} open loop{'s' if open_loop_waiting != 1 else ''} {'are' if open_loop_waiting != 1 else 'is'} waiting on you"
            )
            revisit_phrase = (
                f"{open_loop_revisit} {'need' if open_loop_revisit != 1 else 'needs'} a revisit"
            )
            matters.append(
                f"{waiting_phrase}, and {revisit_phrase}."
            )
        elif open_loop_waiting > 0:
            matters.append(
                f"{open_loop_waiting} open loop{'s' if open_loop_waiting != 1 else ''} are waiting on you."
            )
        elif open_loop_revisit > 0:
            matters.append(
                f"{open_loop_revisit} open loop{'s' if open_loop_revisit != 1 else ''} need a revisit."
            )
        else:
            matters.append(f"{open_loop_total} open loop{'s' if open_loop_total != 1 else ''} need resolution.")

    google_event_count = int(google_workspace.get("upcoming_event_count") or 0)
    family_event_count = int(family_calendar.get("event_count") or 0)
    if google_event_count > 0:
        matters.append(
            f"Calendar pressure: connected Google Calendar returned {google_event_count} upcoming event"
            f"{'s' if google_event_count != 1 else ''} for planning. This is count-level context, not event interpretation."
        )
    elif family_event_count > 0:
        matters.append(
            f"Family calendar has {family_event_count} upcoming event{'s' if family_event_count != 1 else ''} loaded for planning."
        )

    # Always surface the core missions
    matters.append("JARVIS build progress — review overnight commits before making roadmap decisions.")
    matters.append("Health systems are not reporting. Manual check-in recommended.")

    if catalyst["count"] > 0:
        matters.append(f"Catalyst pipeline has {catalyst['count']} completed briefing run{'s' if catalyst['count'] != 1 else ''}.")

    result.what_matters = matters[:6]

    # ---- Section 2.5: What Is Waiting ----
    result.what_is_waiting = _what_is_waiting_lines(
        open_loops=open_loops,
        google_workspace=google_workspace,
        email_truth=result.truth_labels["email"],
    )

    # ---- Section 3.5: What JARVIS Did While You Were Away ----
    result.while_you_were_away = _while_you_were_away_lines(
        assistant_activity=assistant_activity,
        mission_catch_up=mission_catch_up,
        research_catch_up=research_catch_up,
        outcome_catch_up=outcome_catch_up,
        autonomy_catch_up=autonomy_catch_up,
    )

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
    calendar_truth = result.truth_labels["calendar"]
    if calendar_truth.startswith("live"):
        forgotten.append(f"Calendar context is loaded for this brief: {calendar_truth}.")
    elif calendar_truth.startswith("connected-but-empty"):
        forgotten.append("Calendar support is connected, but this brief did not retrieve any upcoming events.")
    else:
        forgotten.append(f"Calendar context is still limited: {calendar_truth}.")

    open_loop_summary = dict(open_loops.get("summary") or {})
    open_loop_total = int(open_loop_summary.get("total") or open_loops.get("count") or 0)
    recorded_catch_up_total = (
        int(mission_catch_up.get("recent_report_count") or 0)
        + int(research_catch_up.get("recent_synthesis_count") or 0)
        + int(outcome_catch_up.get("recent_count") or 0)
        + int(autonomy_catch_up.get("local_proof_count") or 0)
    )
    obsidian_truth = result.truth_labels["obsidian_context"]
    if obsidian_truth.startswith("local"):
        if open_loop_total > 0 or recorded_catch_up_total > 0:
            forgotten.append(
                "Obsidian local context is available if you want to ground today's follow-through in prior notes. "
                "This brief did not open or recall any specific note."
            )
        else:
            forgotten.append(
                "Obsidian local context is available if you want prior notes for grounding. "
                "This brief did not open or recall any specific note."
            )

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
    open_loop_summary = dict(open_loops.get("summary") or {})
    open_loop_total = int(open_loop_summary.get("total") or open_loops.get("count") or 0)
    open_loop_waiting = int(open_loop_summary.get("waiting_on_you") or 0)
    unread_count = int(google_workspace.get("unread_email_count") or 0)
    google_calendar_count = int(google_workspace.get("upcoming_event_count") or 0)
    family_calendar_count = int(family_calendar.get("event_count") or 0)
    live_calendar_count = google_calendar_count if google_calendar_count > 0 else family_calendar_count
    if agents["degraded_count"] > 0 and any(a.get("attention") for a in agents["degraded"]):
        result.recommendation = (
            f"Start by reviewing the {agents['degraded_count']} degraded agent{'s' if agents['degraded_count'] != 1 else ''} "
            "— they may be blocking overnight work."
        )
        result.recommendation_action = _recommendation_action(
            "direct_route",
            title="Review degraded agent work",
            detail="Agent Ops is the current live surface for degraded agent posture and required attention.",
            route="/agent-ops-center",
            route_label="Open Agent Ops",
            truth_note="This opens the current review surface. It does not resolve degraded work by itself.",
        )
    elif git["count"] > 3:
        result.recommendation = (
            f"You have {git['count']} commits from the last 24 hours. "
            "Spend 20 minutes reviewing what changed before making any new roadmap decisions."
        )
        result.recommendation_action = _recommendation_action(
            "direct_route",
            title="Review recent repo movement",
            detail="Progress Center is the current real surface for recent JARVIS code and slice posture.",
            route="/progress-center",
            route_label="Open Progress Center",
            truth_note="This opens the current progress surface. It does not mean the changes have already been reviewed.",
        )
    elif unread_count >= 5 and live_calendar_count > 0 and open_loop_total > 0:
        waiting_or_total = open_loop_waiting if open_loop_waiting > 0 else open_loop_total
        result.recommendation = (
            f"Connected Gmail shows {unread_count} unread item{'s' if unread_count != 1 else ''}, your calendar already has "
            f"{live_calendar_count} upcoming event{'s' if live_calendar_count != 1 else ''}, and {waiting_or_total} open loop"
            f"{'s' if waiting_or_total != 1 else ''} {'are' if waiting_or_total != 1 else 'is'} already waiting on you. "
            "Start with inbox pressure before staging more follow-through."
        )
        result.recommendation_action = _recommendation_action(
            "direct_route",
            title="Review stacked inbox pressure first",
            detail="Email Center is the most precise current first surface when inbox, calendar, and open-loop pressure are all active at once.",
            route="/email-center",
            route_label="Open Email Center",
            truth_note="This opens the inbox surface first. It does not interpret thread meaning or resolve calendar and open-loop pressure by itself.",
        )
    elif open_loop_total > 3:
        result.recommendation = (
            f"Clear {open_loop_total} open loops before starting new work. "
            "Resolution rate matters more than throughput."
        )
        result.recommendation_action = _recommendation_action(
            "bounded_request",
            title="Stage follow-through in Mission Board",
            detail="Mission Board is the current bounded review and intake surface for recorded follow-through pressure.",
            route="/mission-board",
            route_label="Open Mission Board",
            truth_note="This is a bounded handoff into the review surface, not direct completion of those open loops.",
        )
    elif (
        int(mission_catch_up.get("recent_report_count") or 0) > 0
        or int(research_catch_up.get("recent_synthesis_count") or 0) > 0
        or int(outcome_catch_up.get("recent_count") or 0) > 0
        or int(autonomy_catch_up.get("local_proof_count") or 0) > 0
    ):
        result.recommendation = (
            "Review the recorded catch-up outputs before opening new work. "
            "They represent inspectable completed state, not just staged plans."
        )
        result.recommendation_action = (
            _object_specific_catch_up_action(
                mission_catch_up,
                research_catch_up,
                outcome_catch_up,
                autonomy_catch_up,
            )
            or _recommendation_action(
                "direct_route",
                title="Review recorded catch-up",
                detail="Activity Center is the shared readable surface for recent recorded continuity across delegation, outcomes, research, and autonomy traces.",
                route="/activity-center",
                route_label="Open Activity Center",
                truth_note="This opens recorded continuity. Planned-only state still remains distinct from completed work.",
            )
        )
    elif unread_count >= 5:
        result.recommendation = (
            f"Connected Gmail shows {unread_count} unread item{'s' if unread_count != 1 else ''}. "
            "Clear inbox pressure before opening new work."
        )
        result.recommendation_action = _recommendation_action(
            "direct_route",
            title="Review inbox pressure",
            detail="Email Center is the current live inbox surface for unread, waiting, and draft-safe follow-through.",
            route="/email-center",
            route_label="Open Email Center",
            truth_note="This opens the current inbox surface. It does not mean replies were drafted or sent.",
        )
    else:
        email_truth = result.truth_labels["email"]
        calendar_truth = result.truth_labels["calendar"]
        if email_truth.startswith("live") or calendar_truth.startswith("live") or calendar_truth.startswith("connected-but-empty"):
            result.recommendation = (
                "Use the live brief signals you already have before expanding scope. "
                "Resolve the top open loop, then check whether the connected calendar context changes today's priorities."
            )
            result.recommendation_action = _recommendation_action(
                "narrative_only",
                title="No single next surface is staged",
                detail="This recommendation combines brief signals, so JARVIS is staying narrative instead of pretending there is one precise handoff target.",
                truth_note="No direct route or saved object was staged for this recommendation in the current runtime path.",
            )
        else:
            result.recommendation = _google_recovery_recommendation(google_workspace)
            result.recommendation_action = _recommendation_action(
                "direct_route",
                title="Review Google signal posture",
                detail="Settings Center shows the current Google Workspace credential posture and the next recovery seam.",
                route="/settings-center",
                route_label="Open Settings Center",
                truth_note="This opens the current settings surface. It does not connect Gmail or Calendar by itself.",
            )

    return result


async def generate_morning_brief_async(actor_name: str = "Chris") -> MorningBriefResult:
    """Async wrapper — runs generation in a thread to avoid blocking the event loop."""
    import asyncio
    return await asyncio.to_thread(generate_morning_brief, actor_name)
