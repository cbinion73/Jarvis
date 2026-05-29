"""
JARVIS Apple API — Epic 14
===========================
Provides the REST endpoints consumed by JarvisPhone, JarvisWatch, and JarvisMac.

All responses use a consistent envelope:
  {"ok": bool, "data": {...}, "error": str, "ts": str}

Endpoints
---------
GET  /api/apple/briefing                    Chamber home-screen packet (5 zones)
GET  /api/apple/status                      Quick status for Watch complications
GET  /api/apple/needs                       Approval queue (Needs You zone)
POST /api/apple/speak                       Text command → agent response
GET  /api/apple/health/summary              Health summary for HealthKit display
POST /api/apple/health/log                  Log HealthKit samples from iPhone
GET  /api/apple/home/state                  House state for Home tab
POST /api/apple/home/command                Issue a home command (staged for approval)
GET  /api/apple/notifications/pending       Pending notifications for APNs delivery
POST /api/apple/presence                    Phone reports user presence / location
GET  /api/apple/voice/greeting              Voice greeting for wake
POST /api/apple/approvals/{id}/approve      One-tap approval from Watch / Phone
POST /api/apple/focus                       Focus Filter state from iPhone
POST /api/apple/sound-alert                 On-device sound classification alert
POST /api/apple/vision/scan                 On-device OCR / barcode scan result
"""

from __future__ import annotations

import asyncio
from collections import Counter
from copy import deepcopy
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException

from .nav_bridge import NavBridge, haversine, min_distance_to_route, sample_route_points
from .settings import LOCATION_SETTINGS_PATH

logger = logging.getLogger(__name__)
_NAVIGATION_STATE_PATH = Path("data/settings/navigation_state.json")
_EVENT_LOG_PATH = Path("data/state/event_log.jsonl")
_NOTIFICATION_CENTER_PATH = Path("data/state/notification_center.json")

_NAV_STOP_LABELS = {
    "food": "Food",
    "starbucks": "Starbucks",
    "parks": "Parks",
    "historic": "Historic",
    "family": "Family",
    "gas": "Gas",
}

_US_STATE_CODES = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR", "california": "CA",
    "colorado": "CO", "connecticut": "CT", "delaware": "DE", "florida": "FL", "georgia": "GA",
    "hawaii": "HI", "idaho": "ID", "illinois": "IL", "indiana": "IN", "iowa": "IA",
    "kansas": "KS", "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "mississippi": "MS", "missouri": "MO",
    "montana": "MT", "nebraska": "NE", "nevada": "NV", "new hampshire": "NH", "new jersey": "NJ",
    "new mexico": "NM", "new york": "NY", "north carolina": "NC", "north dakota": "ND", "ohio": "OH",
    "oklahoma": "OK", "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC",
    "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT", "vermont": "VT",
    "virginia": "VA", "washington": "WA", "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ok(data: Any) -> dict:
    return {"ok": True, "data": data, "error": None, "ts": _ts()}


def _err(message: str, status: int = 400) -> tuple[dict, int]:
    return {"ok": False, "data": None, "error": message, "ts": _ts()}, status


def _nav_bridge() -> NavBridge:
    return NavBridge(
        os.getenv("GOOGLE_MAPS_API_KEY", ""),
        os.getenv("NPS_API_KEY", ""),
    )


def _safe_read_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("apple_api.safe_read_json %s: %s", path, exc)
    return default


def _safe_write_json(path: Path, payload: Any) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except Exception as exc:
        logger.warning("apple_api.safe_write_json %s: %s", path, exc)


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload) + "\n")
    except Exception as exc:
        logger.warning("apple_api.append_jsonl %s: %s", path, exc)


def _safe_read_jsonl_tail(path: Path, limit: int = 1) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(item, dict):
                    rows.append(item)
    except Exception as exc:
        logger.warning("apple_api.safe_read_jsonl_tail %s: %s", path, exc)
        return []
    if limit <= 0:
        return rows
    return rows[-limit:]


def _safe_read_jsonl(path: Path) -> list[dict[str, Any]]:
    return _safe_read_jsonl_tail(path, limit=0)


def _coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _coerce_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _iso_date_days_away(value: str) -> int | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        target = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        return (target.date() - now.date()).days
    except ValueError:
        return None


def _chronicle_actor_matches(entry: dict[str, Any], actor: str) -> bool:
    entry_actor = str(entry.get("actor") or entry.get("actor_id") or "").strip().lower()
    if not entry_actor:
        return True
    return entry_actor == actor.strip().lower()


def _chronicle_entry_date(entry: dict[str, Any]) -> str:
    for key in ("date", "created_at", "timestamp"):
        raw = str(entry.get(key) or "").strip()
        if raw:
            return raw[:10]
    return ""


def _chronicle_fallback_entries(raw_entries: list[dict[str, Any]], actor: str) -> list[dict[str, Any]]:
    return [
        {
            "id": str(e.get("entry_id") or e.get("id") or uuid.uuid4()),
            "type": str(e.get("entry_type") or e.get("type") or e.get("theme") or "reflection"),
            "title": _truncate(str(e.get("title") or e.get("theme") or "Reflection"), 50),
            "body": _truncate(str(e.get("body") or e.get("note") or e.get("reflection") or ""), 200),
            "scripture": e.get("scripture_ref") or e.get("passage") or None,
            "timestamp": str(e.get("created_at") or e.get("timestamp") or ""),
        }
        for e in reversed(raw_entries)
        if _chronicle_actor_matches(e, actor)
    ][:12]


def _chronicle_fallback_context(raw_entries: list[dict[str, Any]], actor: str) -> dict[str, Any]:
    actor_entries = [entry for entry in raw_entries if _chronicle_actor_matches(entry, actor)]
    study_entry = next(
        (
            entry
            for entry in reversed(actor_entries)
            if str(entry.get("scripture_ref") or entry.get("passage") or "").strip()
        ),
        None,
    )
    active_prayers = [
        {
            "id": str(entry.get("entry_id") or entry.get("id") or uuid.uuid4()),
            "text": str(entry.get("note") or entry.get("body") or entry.get("reflection") or "").strip(),
            "category": str(entry.get("theme") or "Prayer"),
        }
        for entry in reversed(actor_entries)
        if str(entry.get("entry_type") or entry.get("type") or "").strip().lower() == "prayer"
    ][:3]
    top_themes = [
        theme
        for theme, _count in Counter(
            str(entry.get("theme") or "").strip()
            for entry in actor_entries
            if str(entry.get("theme") or "").strip()
        ).most_common(5)
    ]
    return {
        "study": {
            "passage": str(study_entry.get("scripture_ref") or study_entry.get("passage") or ""),
            "title": str(study_entry.get("title") or study_entry.get("theme") or ""),
            "date": _chronicle_entry_date(study_entry),
        } if study_entry else None,
        "active_prayers": active_prayers,
        "todays_rhythm": None,
        "top_themes": top_themes,
        "total_entries": len(actor_entries),
        "active_prayer_count": len(active_prayers),
        "answered_prayer_count": 0,
    }


def _chronicle_fallback_patterns(raw_entries: list[dict[str, Any]], actor: str) -> dict[str, Any]:
    actor_entries = [entry for entry in raw_entries if _chronicle_actor_matches(entry, actor)]
    today = datetime.now(timezone.utc).date()
    cutoff = today.fromordinal(today.toordinal() - 30)
    recent = [
        entry
        for entry in actor_entries
        if (date_str := _chronicle_entry_date(entry)) and date_str >= cutoff.isoformat()
    ]
    type_counts = Counter(
        str(entry.get("entry_type") or entry.get("type") or "reflection")
        for entry in recent
    )
    theme_counts = Counter(
        str(entry.get("theme") or "").strip()
        for entry in recent
        if str(entry.get("theme") or "").strip()
    )

    dates = sorted({_chronicle_entry_date(entry) for entry in actor_entries if _chronicle_entry_date(entry)}, reverse=True)
    streak = 0
    check = today
    for date_str in dates:
        if date_str == check.isoformat():
            streak += 1
            check = check.fromordinal(check.toordinal() - 1)
            continue
        if streak == 0 and date_str == check.fromordinal(check.toordinal() - 1).isoformat():
            streak += 1
            check = check.fromordinal(check.toordinal() - 2)
            continue
        break

    prayer_count = sum(
        1 for entry in actor_entries
        if str(entry.get("entry_type") or entry.get("type") or "").strip().lower() == "prayer"
    )
    return {
        "window_days": 30,
        "total_recent_entries": len(recent),
        "entry_type_breakdown": dict(type_counts),
        "recurring_themes": [
            {"theme": theme, "count": count}
            for theme, count in theme_counts.most_common(8)
        ],
        "prayer_arc": {
            "total_active": prayer_count,
            "answered_total": 0,
            "answered_recent": 0,
        },
        "writing_streak_days": streak,
    }


def _build_home_context(*, needs_count: int = 0) -> dict[str, Any]:
    data_root = Path("data/apple")
    calendar_payload = _safe_read_json(data_root / "calendar_events.json", {})
    reminders_payload = _safe_read_json(data_root / "reminders.json", {})
    focus_payload = _safe_read_json(data_root / "focus_state.json", {})

    calendar_events = calendar_payload.get("events") if isinstance(calendar_payload, dict) else []
    if not isinstance(calendar_events, list):
        calendar_events = []
    calendar_events = [event for event in calendar_events if isinstance(event, dict)]
    calendar_events.sort(key=lambda item: str(item.get("start") or ""))

    reminder_items = reminders_payload.get("reminders") if isinstance(reminders_payload, dict) else []
    if not isinstance(reminder_items, list):
        reminder_items = []
    reminder_items = [
        reminder for reminder in reminder_items
        if isinstance(reminder, dict) and not bool(reminder.get("completed"))
    ]
    reminder_items.sort(key=lambda item: str(item.get("due") or "9999"))

    unread_email_count = 0
    try:
        from .unified_inbox import get_unified_inbox

        inbox = get_unified_inbox()
        if inbox is not None:
            unread_email_count = int((inbox.get_email_stats() or {}).get("total_unread") or 0)
    except Exception as exc:
        logger.warning("apple_api.build_home_context inbox: %s", exc)

    publishing_count = 0
    project_titles: list[str] = []
    try:
        from .publishing_suite import PublishingStore

        projects = PublishingStore().list_projects()
        publishing_count = len(projects)
        project_titles.extend([str(project.title).strip() for project in projects[:3] if str(project.title).strip()])
    except Exception as exc:
        logger.warning("apple_api.build_home_context publishing: %s", exc)

    active_work_items_count = 0
    try:
        from .catalyst import CatalystStore

        work_items = CatalystStore(Path.home() / ".jarvis" / "catalyst").work_lifecycle()
        active_statuses = {"queued", "active", "review", "draft", "planned", "ready"}
        active_work_items_count = sum(
            1 for item in work_items
            if str(item.get("status") or "").strip().lower() in active_statuses
        )
        for item in work_items[:3]:
            title = str(item.get("title") or "").strip()
            if title and title not in project_titles:
                project_titles.append(title)
    except Exception as exc:
        logger.warning("apple_api.build_home_context catalyst: %s", exc)

    next_event = calendar_events[0] if calendar_events else {}

    return {
        "agenda": {
            "today_event_count": int(calendar_payload.get("count") or len(calendar_events)) if isinstance(calendar_payload, dict) else len(calendar_events),
            "next_event_title": str(next_event.get("title") or ""),
            "next_event_start": str(next_event.get("start") or ""),
            "next_event_location": str(next_event.get("location") or ""),
        },
        "attention": {
            "reminder_count": int(reminders_payload.get("count") or len(reminder_items)) if isinstance(reminders_payload, dict) else len(reminder_items),
            "notification_count": _notification_store.count(),
            "unread_email_count": unread_email_count,
            "needs_count": int(needs_count or 0),
            "focus_active": bool(focus_payload.get("focus_active")) if isinstance(focus_payload, dict) else False,
        },
        "projects": {
            "publishing_project_count": publishing_count,
            "active_work_items_count": active_work_items_count,
            "top_titles": project_titles[:3],
        },
    }


def _build_briefing_command_items(
    *,
    home_context: dict[str, Any],
    home_state: dict[str, Any],
    watch_status: dict[str, Any],
) -> list[dict[str, Any]]:
    agenda = home_context.get("agenda") if isinstance(home_context, dict) else {}
    agenda = agenda if isinstance(agenda, dict) else {}
    attention = home_context.get("attention") if isinstance(home_context, dict) else {}
    attention = attention if isinstance(attention, dict) else {}
    projects = home_context.get("projects") if isinstance(home_context, dict) else {}
    projects = projects if isinstance(projects, dict) else {}

    present_members = [str(name).strip() for name in (home_state.get("present_members") or []) if str(name).strip()]
    alerts = home_state.get("alerts") if isinstance(home_state.get("alerts"), list) else []
    alerts = [alert for alert in alerts if isinstance(alert, dict)]

    needs_count = int(watch_status.get("needs_count") or 0)
    reminder_count = int(attention.get("reminder_count") or 0)
    notification_count = int(attention.get("notification_count") or 0)
    unread_email_count = int(attention.get("unread_email_count") or 0)
    active_work_items_count = int(projects.get("active_work_items_count") or 0)
    publishing_project_count = int(projects.get("publishing_project_count") or 0)
    next_event_title = str(agenda.get("next_event_title") or "").strip()
    next_event_start = str(agenda.get("next_event_start") or "").strip()
    next_event_location = str(agenda.get("next_event_location") or "").strip()
    focus_active = bool(attention.get("focus_active"))
    drift_active = bool(watch_status.get("drift"))
    weather_summary = str(watch_status.get("weather") or "").strip()

    items: list[dict[str, Any]] = []

    if needs_count > 0:
        items.append({
            "id": "command-needs",
            "title": f"Resolve {needs_count} pending decision" + ("s" if needs_count != 1 else ""),
            "detail": "JARVIS is waiting on approvals before it can move the household forward.",
            "priority": "high",
            "kind": "needs",
        })

    if alerts:
        first_alert = alerts[0]
        items.append({
            "id": "command-home-alerts",
            "title": f"Review {len(alerts)} home alert" + ("s" if len(alerts) != 1 else ""),
            "detail": str(first_alert.get("message") or "The home stack surfaced a live alert."),
            "priority": "high",
            "kind": "home",
        })

    if next_event_title:
        detail_parts = [part for part in [next_event_start, next_event_location] if part]
        items.append({
            "id": "command-next-event",
            "title": f"Prepare for {next_event_title}",
            "detail": " · ".join(detail_parts) if detail_parts else "Your next calendar event is already on the board.",
            "priority": "high" if not present_members else "normal",
            "kind": "calendar",
        })

    if reminder_count > 0:
        items.append({
            "id": "command-reminders",
            "title": f"Clear {reminder_count} active reminder" + ("s" if reminder_count != 1 else ""),
            "detail": "Outstanding reminders are part of today's attention load.",
            "priority": "normal",
            "kind": "reminders",
        })

    if notification_count > 0 or unread_email_count > 0:
        detail_parts = []
        if notification_count > 0:
            detail_parts.append(f"{notification_count} notification" + ("s" if notification_count != 1 else ""))
        if unread_email_count > 0:
            detail_parts.append(f"{unread_email_count} unread email" + ("s" if unread_email_count != 1 else ""))
        items.append({
            "id": "command-attention",
            "title": "Triage incoming attention",
            "detail": " · ".join(detail_parts),
            "priority": "normal",
            "kind": "attention",
        })

    if active_work_items_count > 0 or publishing_project_count > 0:
        detail_parts = []
        if active_work_items_count > 0:
            detail_parts.append(f"{active_work_items_count} active work item" + ("s" if active_work_items_count != 1 else ""))
        if publishing_project_count > 0:
            detail_parts.append(f"{publishing_project_count} publishing project" + ("s" if publishing_project_count != 1 else ""))
        top_titles = [str(title).strip() for title in (projects.get("top_titles") or []) if str(title).strip()]
        detail = " · ".join(detail_parts)
        if top_titles:
            detail = f"{detail} · {', '.join(top_titles[:2])}" if detail else ", ".join(top_titles[:2])
        items.append({
            "id": "command-projects",
            "title": "Keep active projects moving",
            "detail": detail or "JARVIS sees active work in motion.",
            "priority": "normal",
            "kind": "projects",
        })

    if focus_active or drift_active or weather_summary:
        detail_parts = []
        if focus_active:
            detail_parts.append("Focus mode is active")
        if drift_active:
            detail_parts.append("Drift signals are live")
        if weather_summary:
            detail_parts.append(weather_summary)
        items.append({
            "id": "command-posture",
            "title": "Set the household posture",
            "detail": " · ".join(detail_parts),
            "priority": "normal",
            "kind": "posture",
        })

    if present_members:
        items.append({
            "id": "command-presence",
            "title": "Household presence is live",
            "detail": ", ".join(present_members[:3]),
            "priority": "normal",
            "kind": "presence",
        })

    if not items:
        items.append({
            "id": "command-clear",
            "title": "Household is clear",
            "detail": "No urgent actions are blocking JARVIS right now. Start with Brief, Home, or Navigate to shape the day.",
            "priority": "normal",
            "kind": "clear",
        })

    return items[:5]


def _build_home_action_items(*, state: dict[str, Any], home_context: dict[str, Any], needs_count: int) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    lights_on = [str(name).strip() for name in (state.get("lights_on") or []) if str(name).strip()]
    alerts = state.get("alerts") if isinstance(state.get("alerts"), list) else []
    alerts = [alert for alert in alerts if isinstance(alert, dict)]
    present_members = [str(name).strip() for name in (state.get("present_members") or []) if str(name).strip()]
    doors = state.get("doors") if isinstance(state.get("doors"), dict) else {}

    attention = home_context.get("attention") if isinstance(home_context, dict) else {}
    attention = attention if isinstance(attention, dict) else {}
    agenda = home_context.get("agenda") if isinstance(home_context, dict) else {}
    agenda = agenda if isinstance(agenda, dict) else {}

    if alerts:
        first_alert = alerts[0]
        actions.append({
            "id": "home-action-alert",
            "title": "Stage a response to live home alerts",
            "detail": str(first_alert.get("message") or "JARVIS detected a live home alert."),
            "command": "Review and resolve live home alerts",
            "entity_id": "",
            "service": "jarvis.review_home_alerts",
            "emphasis": "high",
        })

    if lights_on:
        actions.append({
            "id": "home-action-lights",
            "title": "Stage all lights off",
            "detail": f"{len(lights_on)} light" + ("s are" if len(lights_on) != 1 else " is") + " currently on.",
            "command": "Turn all lights off",
            "entity_id": "",
            "service": "jarvis.all_lights_off",
            "emphasis": "medium",
        })

    open_doors = [name for name, value in doors.items() if str(value).strip().lower() not in {"closed", "locked", "secure"}]
    if open_doors:
        actions.append({
            "id": "home-action-secure",
            "title": "Stage a home security sweep",
            "detail": ", ".join(open_doors[:3]),
            "command": "Secure the home",
            "entity_id": "",
            "service": "jarvis.secure_home",
            "emphasis": "high",
        })

    if int(attention.get("notification_count") or 0) > 0 or needs_count > 0:
        actions.append({
            "id": "home-action-attention",
            "title": "Stage household attention review",
            "detail": f"{needs_count} needs · {int(attention.get('notification_count') or 0)} alerts",
            "command": "Review household attention queue",
            "entity_id": "",
            "service": "jarvis.review_attention",
            "emphasis": "medium",
        })

    if str(agenda.get("next_event_title") or "").strip():
        actions.append({
            "id": "home-action-agenda",
            "title": "Stage next-event preparation",
            "detail": str(agenda.get("next_event_title") or ""),
            "command": f"Prepare the household for {str(agenda.get('next_event_title') or '').strip()}",
            "entity_id": "",
            "service": "jarvis.prepare_next_event",
            "emphasis": "medium",
        })

    if present_members:
        actions.append({
            "id": "home-action-presence",
            "title": "Stage a household status check",
            "detail": ", ".join(present_members[:3]),
            "command": "Review household presence and home posture",
            "entity_id": "",
            "service": "jarvis.review_presence",
            "emphasis": "low",
        })

    if not actions:
        actions.append({
            "id": "home-action-clear",
            "title": "Home is steady",
            "detail": "No urgent household actions are waiting right now.",
            "command": "Review household posture",
            "entity_id": "",
            "service": "jarvis.review_home_posture",
            "emphasis": "low",
        })

    return actions[:4]


def _default_navigation_state() -> dict[str, Any]:
    return {
        "favorite_destinations": [],
        "recent_destinations": [],
        "active_stop_category_ids": ["food", "starbucks", "parks", "historic", "family"],
        "parks_historic_radius_miles": 25,
        "selected_origin_mode": "home",
        "selected_saved_location_id": "",
        "last_route": {
            "origin": "",
            "destination": "",
        },
    }


def _load_navigation_state() -> dict[str, Any]:
    payload = _safe_read_json(_NAVIGATION_STATE_PATH, _default_navigation_state())
    if not isinstance(payload, dict):
        payload = {}
    merged = dict(_default_navigation_state())
    merged.update(payload)
    merged["favorite_destinations"] = [
        str(item).strip()
        for item in (merged.get("favorite_destinations") or [])
        if str(item).strip()
    ][:8]
    merged["recent_destinations"] = [
        str(item).strip()
        for item in (merged.get("recent_destinations") or [])
        if str(item).strip()
    ][:8]
    merged["active_stop_category_ids"] = [
        str(item).strip()
        for item in (merged.get("active_stop_category_ids") or [])
        if str(item).strip()
    ] or list(_default_navigation_state()["active_stop_category_ids"])
    try:
        merged["parks_historic_radius_miles"] = max(
            5,
            min(100, int(float(merged.get("parks_historic_radius_miles") or 25))),
        )
    except Exception:
        merged["parks_historic_radius_miles"] = 25
    merged["selected_origin_mode"] = str(merged.get("selected_origin_mode") or "home").strip() or "home"
    merged["selected_saved_location_id"] = str(merged.get("selected_saved_location_id") or "").strip()
    last_route = merged.get("last_route") if isinstance(merged.get("last_route"), dict) else {}
    merged["last_route"] = {
        "origin": str((last_route or {}).get("origin") or "").strip(),
        "destination": str((last_route or {}).get("destination") or "").strip(),
    }
    return merged


def _save_navigation_state(patch: dict[str, Any]) -> dict[str, Any]:
    current = _load_navigation_state()
    merged = dict(current)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(current.get(key), dict):
            next_value = dict(current.get(key) or {})
            next_value.update(value)
            merged[key] = next_value
        else:
            merged[key] = value
    cleaned = dict(_default_navigation_state())
    cleaned.update(merged)
    cleaned["favorite_destinations"] = [
        str(item).strip()
        for item in (cleaned.get("favorite_destinations") or [])
        if str(item).strip()
    ][:8]
    cleaned["recent_destinations"] = [
        str(item).strip()
        for item in (cleaned.get("recent_destinations") or [])
        if str(item).strip()
    ][:8]
    cleaned["active_stop_category_ids"] = [
        str(item).strip()
        for item in (cleaned.get("active_stop_category_ids") or [])
        if str(item).strip()
    ] or list(_default_navigation_state()["active_stop_category_ids"])
    try:
        cleaned["parks_historic_radius_miles"] = max(
            5,
            min(100, int(float(cleaned.get("parks_historic_radius_miles") or 25))),
        )
    except Exception:
        cleaned["parks_historic_radius_miles"] = 25
    cleaned["selected_origin_mode"] = str(cleaned.get("selected_origin_mode") or "home").strip() or "home"
    cleaned["selected_saved_location_id"] = str(cleaned.get("selected_saved_location_id") or "").strip()
    last_route = cleaned.get("last_route") if isinstance(cleaned.get("last_route"), dict) else {}
    cleaned["last_route"] = {
        "origin": str((last_route or {}).get("origin") or "").strip(),
        "destination": str((last_route or {}).get("destination") or "").strip(),
    }
    _NAVIGATION_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _NAVIGATION_STATE_PATH.write_text(json.dumps(cleaned, indent=2) + "\n", encoding="utf-8")
    return cleaned


def _nav_route_points(route_info: dict[str, Any]) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for pair in list(route_info.get("coordinates") or []):
        if isinstance(pair, list) and len(pair) == 2:
            try:
                points.append((float(pair[1]), float(pair[0])))
            except (TypeError, ValueError):
                continue
    return points


def _nav_state_codes(*labels: str) -> list[str]:
    found: list[str] = []
    for label in labels:
        lowered = str(label or "").lower()
        for state_name, code in _US_STATE_CODES.items():
            if state_name in lowered and code not in found:
                found.append(code)
    return found


def _nav_nps_along_route(
    bridge: NavBridge,
    route_points: list[tuple[float, float]],
    states: list[str],
    max_distance_miles: float = 25.0,
) -> list[dict[str, Any]]:
    parks = bridge.search_nps_by_states(states)
    if not parks or not route_points:
        return []

    filtered: list[dict[str, Any]] = []
    for park in parks:
        try:
            plat = float(park.get("latitude") or 0)
            plng = float(park.get("longitude") or 0)
        except (TypeError, ValueError):
            continue
        if plat == 0 and plng == 0:
            continue
        dist = min_distance_to_route(plat, plng, route_points)
        if dist > max_distance_miles:
            continue
        closest_idx = min(
            range(len(route_points)),
            key=lambda i: haversine(plat, plng, route_points[i][0], route_points[i][1]),
        )
        cumulative = 0.0
        for idx in range(1, closest_idx + 1):
            cumulative += haversine(
                route_points[idx - 1][0], route_points[idx - 1][1],
                route_points[idx][0], route_points[idx][1],
            )
        filtered.append(
            {
                "name": str(park.get("fullName") or ""),
                "address": str(park.get("states") or ""),
                "description": str(park.get("description") or ""),
                "url": str(park.get("url") or ""),
                "lat": plat,
                "lng": plng,
                "route_mile_marker": round(cumulative, 1),
                "distance_from_route": round(dist, 1),
                "rating": None,
            }
        )
    filtered.sort(key=lambda item: item.get("route_mile_marker") or 0)
    return filtered


# ---------------------------------------------------------------------------
# HealthSampleStore
# ---------------------------------------------------------------------------

class HealthSampleStore:
    """
    Lightweight append-only store for raw HealthKit samples.
    Samples are written as newline-delimited JSON (JSONL) to
    ~/.jarvis/health/samples.jsonl so they can be replayed or aggregated.
    """

    ROOT = Path.home() / ".jarvis" / "health"

    def _samples_path(self, actor_id: str) -> Path:
        return self.ROOT / actor_id / "samples.jsonl"

    def log_samples(self, actor_id: str, samples: list[dict]) -> int:
        """
        Append raw samples to JSONL.  Returns the number of records logged.
        Each record is enriched with a server-side received_at timestamp.
        """
        if not samples:
            return 0
        path = self._samples_path(actor_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        received_at = _ts()
        with path.open("a", encoding="utf-8") as fh:
            for sample in samples:
                row = dict(sample)
                row["received_at"] = received_at
                fh.write(json.dumps(row, default=str) + "\n")
        return len(samples)

    def _read_samples(self, actor_id: str) -> list[dict]:
        path = self._samples_path(actor_id)
        if not path.exists():
            return []
        rows: list[dict] = []
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        rows.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        return rows

    def get_summary(self, actor_id: str, date: str | None = None) -> dict:
        """
        Aggregate samples for a given date (default today, YYYY-MM-DD).
        Returns a dict with keys:
          steps, heart_rate_avg, sleep_hours, active_calories, stand_hours, hrv, last_sync
        """
        target_date = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        samples = self._read_samples(actor_id)

        steps = 0
        hr_values: list[float] = []
        sleep_hours = 0.0
        active_calories = 0
        stand_hours = 0
        hrv_values: list[float] = []
        last_sync: str | None = None

        for s in samples:
            # Match by date prefix (handles both date-only and datetime strings)
            sample_date = str(s.get("date", ""))[:10]
            if sample_date != target_date:
                continue
            sample_type = str(s.get("type", "")).lower()
            value = float(s.get("value", 0) or 0)
            if sample_type == "steps":
                steps = max(steps, int(value))
            elif sample_type in ("heart_rate", "resting_heart_rate"):
                hr_values.append(value)
            elif sample_type == "sleep":
                sleep_hours = max(sleep_hours, value)
            elif sample_type in ("active_calories", "active_energy"):
                active_calories = max(active_calories, int(value))
            elif sample_type == "stand_hours":
                stand_hours = max(stand_hours, int(value))
            elif sample_type == "hrv":
                hrv_values.append(value)
            received = s.get("received_at")
            if received and (last_sync is None or received > last_sync):
                last_sync = received

        return {
            "steps": steps,
            "heart_rate_avg": int(sum(hr_values) / len(hr_values)) if hr_values else 0,
            "sleep_hours": round(sleep_hours, 1),
            "active_calories": active_calories,
            "stand_hours": stand_hours,
            "hrv": int(sum(hrv_values) / len(hrv_values)) if hrv_values else 0,
            "last_sync": last_sync or "",
        }

    def get_recent(self, actor_id: str, sample_type: str, days: int = 7) -> list[dict]:
        """Recent samples of a given type, newest first, limited to *days* days back."""
        from datetime import timedelta
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
        samples = self._read_samples(actor_id)
        result = [
            s for s in samples
            if str(s.get("type", "")).lower() == sample_type.lower()
            and str(s.get("date", ""))[:10] >= cutoff
        ]
        # newest first
        result.sort(key=lambda s: str(s.get("date", "")), reverse=True)
        return result


# ---------------------------------------------------------------------------
# Pending-notification store (in-memory, cleared on delivery)
# ---------------------------------------------------------------------------

class _NotificationStore:
    def __init__(self) -> None:
        self._pending: list[dict] = []

    def push(self, title: str, body: str, category: str = "general", badge: int = 0) -> str:
        nid = str(uuid.uuid4())
        self._pending.append({
            "id": nid,
            "title": title,
            "body": body,
            "category": category,
            "badge": badge,
            "created_at": _ts(),
        })
        return nid

    def drain(self) -> list[dict]:
        items = list(self._pending)
        self._pending.clear()
        return items

    def peek(self, limit: int = 5) -> list[dict]:
        if limit <= 0:
            return list(self._pending)
        return list(self._pending[-limit:])

    def count(self) -> int:
        return len(self._pending)


class _EventLogStore:
    def __init__(self, path: Path) -> None:
        self._path = path

    def record(
        self,
        *,
        domain: str,
        kind: str,
        title: str,
        detail: str = "",
        severity: str = "low",
        actor: str = "jarvis",
        surface: str = "server",
        status: str = "new",
        source: str = "",
        source_id: str = "",
        thread_id: str = "",
        navigation_target: str = "",
        actions: list[str] | None = None,
        trust_zone: str = "household_operations",
        authority_stage: str = "live",
        why_now: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        event = {
            "id": f"evt_{uuid.uuid4().hex}",
            "ts": _ts(),
            "actor": str(actor or "jarvis"),
            "surface": str(surface or "server"),
            "domain": str(domain or "system"),
            "kind": str(kind or "info"),
            "severity": str(severity or "low"),
            "title": str(title or "JARVIS event"),
            "detail": str(detail or ""),
            "status": str(status or "new"),
            "source": str(source or ""),
            "source_id": str(source_id or ""),
            "thread_id": str(thread_id or ""),
            "navigation_target": str(navigation_target or ""),
            "actions": [str(action) for action in (actions or []) if str(action or "").strip()],
            "trust_zone": str(trust_zone or "household_operations"),
            "authority_stage": str(authority_stage or "live"),
            "why_now": str(why_now or ""),
            "metadata": metadata if isinstance(metadata, dict) else {},
        }
        _append_jsonl(self._path, event)
        return event

    def recent(
        self,
        *,
        limit: int = 25,
        domain: str | None = None,
        status: str | None = None,
        severity: str | None = None,
    ) -> list[dict[str, Any]]:
        rows = _safe_read_jsonl_tail(self._path, limit=0)
        if domain:
            rows = [row for row in rows if str(row.get("domain") or "") == domain]
        if status:
            rows = [row for row in rows if str(row.get("status") or "") == status]
        if severity:
            rows = [row for row in rows if str(row.get("severity") or "") == severity]
        if limit > 0:
            rows = rows[-limit:]
        rows.reverse()
        return rows


class _NotificationCenterStore:
    def __init__(self, path: Path, event_log: _EventLogStore) -> None:
        self._path = path
        self._event_log = event_log

    def _load(self) -> dict[str, Any]:
        data = _safe_read_json(self._path, {})
        items = data.get("items") if isinstance(data, dict) else []
        if not isinstance(items, list):
            items = []
        return {"items": [item for item in items if isinstance(item, dict)]}

    def _save(self, payload: dict[str, Any]) -> None:
        _safe_write_json(self._path, payload)

    def create(
        self,
        *,
        category: str,
        title: str,
        detail: str = "",
        severity: str = "low",
        audience: str = "household",
        delivery_mode: str = "badge_only",
        navigation_target: str = "",
        available_actions: list[str] | None = None,
        why_now: str = "",
        source_summary: str = "",
        event: dict[str, Any] | None = None,
        expires_at: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        store = self._load()
        notification = {
            "id": f"notif_{uuid.uuid4().hex}",
            "event_id": str((event or {}).get("id") or ""),
            "category": str(category or "system"),
            "title": str(title or "JARVIS Alert"),
            "detail": str(detail or ""),
            "body": str(detail or ""),
            "severity": str(severity or "low"),
            "status": "pending",
            "created_at": _ts(),
            "updated_at": _ts(),
            "expires_at": str(expires_at or ""),
            "audience": str(audience or "household"),
            "delivery_mode": str(delivery_mode or "badge_only"),
            "navigation_target": str(navigation_target or ""),
            "available_actions": [str(action) for action in (available_actions or ["open", "dismiss"]) if str(action or "").strip()],
            "why_now": str(why_now or ""),
            "source_summary": str(source_summary or ""),
            "badge": 0,
            "metadata": metadata if isinstance(metadata, dict) else {},
        }
        store["items"].append(notification)
        self._save(store)
        return notification

    def list(
        self,
        *,
        status: str | None = None,
        limit: int = 50,
        category: str | None = None,
    ) -> list[dict[str, Any]]:
        items = self._load()["items"]
        if status:
            items = [item for item in items if str(item.get("status") or "") == status]
        if category:
            items = [item for item in items if str(item.get("category") or "") == category]
        items.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
        if limit > 0:
            items = items[:limit]
        return items

    def count(self, *, status: str = "pending") -> int:
        return len(self.list(status=status, limit=0))

    def recent(self, limit: int = 5) -> list[dict[str, Any]]:
        return self.list(limit=limit)

    def update_status(self, notification_id: str, status: str, *, reason: str = "") -> dict[str, Any] | None:
        store = self._load()
        for item in store["items"]:
            if str(item.get("id") or "") != notification_id:
                continue
            item["status"] = status
            item["updated_at"] = _ts()
            self._save(store)
            self._event_log.record(
                domain="system",
                kind="resolved" if status in {"resolved", "dismissed"} else "info",
                title=f"Notification {status}",
                detail=str(item.get("title") or ""),
                severity=str(item.get("severity") or "low"),
                source="apple.notification_center",
                source_id=notification_id,
                navigation_target=str(item.get("navigation_target") or ""),
                actions=["open"],
                trust_zone="household_operations",
                authority_stage="live",
                why_now=reason or f"Notification status changed to {status}.",
                metadata={"notification_id": notification_id, "status": status},
            )
            return deepcopy(item)
        return None


_event_log = _EventLogStore(_EVENT_LOG_PATH)
_notification_center = _NotificationCenterStore(_NOTIFICATION_CENTER_PATH, _event_log)
_notification_store = _NotificationStore()
_health_store = HealthSampleStore()


# ---------------------------------------------------------------------------
# Greeting helpers
# ---------------------------------------------------------------------------

def _time_of_day_greeting() -> tuple[str, str]:
    """Return (greeting, mode) based on local hour."""
    hour = datetime.now().hour
    if hour < 12:
        return "Good morning, Sir.", "morning"
    elif hour < 17:
        return "Good afternoon, Sir.", "afternoon"
    elif hour < 21:
        return "Good evening, Sir.", "evening"
    return "Good night, Sir.", "night"


def _record_shared_event(
    *,
    domain: str,
    kind: str,
    title: str,
    detail: str = "",
    severity: str = "low",
    actor: str = "jarvis",
    source: str = "",
    source_id: str = "",
    navigation_target: str = "",
    actions: list[str] | None = None,
    trust_zone: str = "household_operations",
    authority_stage: str = "live",
    why_now: str = "",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _event_log.record(
        domain=domain,
        kind=kind,
        title=title,
        detail=detail,
        severity=severity,
        actor=actor,
        surface="apple_api",
        status="new",
        source=source,
        source_id=source_id,
        navigation_target=navigation_target,
        actions=actions or [],
        trust_zone=trust_zone,
        authority_stage=authority_stage,
        why_now=why_now,
        metadata=metadata or {},
    )


def _create_notification_from_event(
    event: dict[str, Any],
    *,
    category: str,
    delivery_mode: str = "badge_only",
    audience: str = "household",
    available_actions: list[str] | None = None,
    source_summary: str = "",
) -> dict[str, Any]:
    return _notification_center.create(
        category=category,
        title=str(event.get("title") or "JARVIS Alert"),
        detail=str(event.get("detail") or ""),
        severity=str(event.get("severity") or "low"),
        audience=audience,
        delivery_mode=delivery_mode,
        navigation_target=str(event.get("navigation_target") or ""),
        available_actions=available_actions or list(event.get("actions") or ["open", "dismiss"]),
        why_now=str(event.get("why_now") or ""),
        source_summary=source_summary or str(event.get("source") or ""),
        event=event,
        metadata={"event_id": str(event.get("id") or "")},
    )


# ---------------------------------------------------------------------------
# Route registration
# ---------------------------------------------------------------------------

def _register_apple_api(app: FastAPI, runtime: Any) -> None:  # noqa: C901
    """Register all /api/apple/* routes onto *app*."""

    # ------------------------------------------------------------------
    # POST /api/apple/device/register  — store APNs device token
    # ------------------------------------------------------------------
    @app.post("/api/apple/device/register")
    async def apple_device_register(payload: dict):
        """Store an APNs device token for push notification delivery."""
        actor_id = str(payload.get("actor_id") or "chris").strip()
        token    = str(payload.get("token")    or "").strip()
        platform = str(payload.get("platform") or "ios").strip()
        if not token:
            raise HTTPException(status_code=400, detail="token is required")
        try:
            from .apns_sender import register_device_token
            register_device_token(actor_id, token, platform)
        except Exception as exc:
            logger.warning("device_register: %s", exc)
        return _ok({"registered": True})

    # ------------------------------------------------------------------
    # GET /api/apple/briefing
    # ------------------------------------------------------------------
    @app.get("/api/apple/briefing")
    async def apple_briefing(actor: str = "chris"):
        """
        Return the full 5-zone Chamber home-screen packet.
        Tries the BriefingBuilder cache first; falls back to chamber_home_snapshot.
        """
        try:
            from .scheduler import get_briefing_builder
            builder = get_briefing_builder()
        except Exception:
            builder = None

        greeting, mode = _time_of_day_greeting()
        watch_status = (await apple_status()).get("data") or {}
        home_state = (await apple_home_state()).get("data") or {}
        needs_count = int(watch_status.get("needs_count") or 0)
        home_context = _build_home_context(needs_count=needs_count)

        # Attempt live briefing
        packet: dict | None = None
        if builder is not None:
            try:
                import asyncio
                cached = await asyncio.to_thread(builder.get_cached)
                if cached:
                    packet = cached
                else:
                    packet = await asyncio.to_thread(builder.build, actor)
            except Exception as exc:
                logger.warning("apple_briefing: briefing builder failed: %s", exc)

        # Fallback: chamber_home_snapshot
        if packet is None:
            try:
                import asyncio
                packet = await asyncio.to_thread(runtime.chamber_home_snapshot, actor)
            except Exception as exc:
                logger.warning("apple_briefing: chamber_home_snapshot failed: %s", exc)
                packet = {}

        # Normalise into the Apple briefing shape expected by Swift BriefingModels
        raw_briefing  = packet.get("briefing_items")  or packet.get("feed",        [])
        raw_working   = packet.get("working_items")   or packet.get("in_progress", [])
        raw_needs     = packet.get("needs_items")     or packet.get("needs_you",   [])
        raw_drift     = packet.get("drift_items")     or packet.get("drift",       [])

        data = {
            "briefing_items": [
                _normalise_briefing_item(i)
                for i in raw_briefing
                if isinstance(i, dict) and _is_live_apple_item(i, zone="briefing")
            ],
            "working_items":  [
                _normalise_working_item(i)
                for i in raw_working
                if isinstance(i, dict) and _is_live_apple_item(i, zone="working")
            ],
            "needs_items":    [
                _normalise_needs_item(i)
                for i in raw_needs
                if isinstance(i, dict) and _is_live_apple_item(i, zone="needs")
            ],
            "drift_items":    [
                _normalise_drift_item(i)
                for i in raw_drift
                if isinstance(i, dict) and _is_live_apple_item(i, zone="drift")
            ],
            "greeting":       packet.get("greeting") or greeting,
            "mode":           packet.get("mode")     or mode,
            "generated_at":   packet.get("generated_at") or _ts(),
            "command_items":  _build_briefing_command_items(
                home_context=home_context,
                home_state=home_state,
                watch_status=watch_status,
            ),
        }
        return _ok(data)

    # ------------------------------------------------------------------
    # GET /api/apple/status  (Watch complication data)
    # ------------------------------------------------------------------
    @app.get("/api/apple/status")
    async def apple_status():
        """Lightweight status payload for Apple Watch complications."""
        try:
            status = runtime.status()
        except Exception:
            status = {}

        if not isinstance(status, dict):
            status = {}

        # Attempt to read pending-approval count
        needs_count = 0
        try:
            from .approvals import get_approval_queue
            queue = get_approval_queue()
            if queue is not None:
                needs_count = len(queue.list_pending())
        except Exception:
            pass

        # Attempt to read current mode from status
        mode = status.get("mode") or status.get("current_mode") or "home"

        # Weather — best-effort from runtime
        weather = ""
        try:
            world = runtime.world_state_view("chris")
            weather = world.get("weather", {}).get("summary") or ""
        except Exception:
            pass

        # Drift flag
        drift = False
        try:
            snap = runtime.chamber_home_snapshot("chris")
            drift = bool(snap.get("drift_items") or snap.get("drift"))
        except Exception:
            pass

        data = {
            "needs_count": needs_count,
            "mode": str(mode),
            "weather": str(weather),
            "drift": drift,
            "ts": _ts(),
        }
        return _ok(data)

    # ------------------------------------------------------------------
    # GET /api/apple/app-state
    # ------------------------------------------------------------------
    @app.get("/api/apple/app-state")
    async def apple_app_state(actor: str = "chris"):
        """Aggregate production and device-fed state for phone-wide sync truth."""
        data_root = Path("data/apple")
        calendar_payload = _safe_read_json(data_root / "calendar_events.json", {})
        reminders_payload = _safe_read_json(data_root / "reminders.json", {})
        focus_payload = _safe_read_json(data_root / "focus_state.json", {})
        now_playing_payload = _safe_read_json(data_root / "now_playing.json", {})
        latest_sound = (_safe_read_jsonl_tail(data_root / "sound_alerts.jsonl", limit=1) or [{}])[0]
        latest_scan = (_safe_read_jsonl_tail(data_root / "vision_scans.jsonl", limit=1) or [{}])[0]

        watch_status = (await apple_status()).get("data") or {}
        home_state = (await apple_home_state()).get("data") or {}

        calendar_events = calendar_payload.get("events") if isinstance(calendar_payload, dict) else []
        if not isinstance(calendar_events, list):
            calendar_events = []
        calendar_events = [event for event in calendar_events if isinstance(event, dict)]
        calendar_events.sort(key=lambda item: str(item.get("start") or ""))

        reminder_items = reminders_payload.get("reminders") if isinstance(reminders_payload, dict) else []
        if not isinstance(reminder_items, list):
            reminder_items = []
        reminder_items = [
            reminder for reminder in reminder_items
            if isinstance(reminder, dict) and not bool(reminder.get("completed"))
        ]
        reminder_items.sort(key=lambda item: str(item.get("due") or "9999"))

        notifications_recent = _notification_center.recent(limit=5)
        for item in notifications_recent:
            item.setdefault("created_at", _ts())

        sync_health = {
            "calendar": {
                "synced": bool(calendar_payload),
                "synced_at": calendar_payload.get("synced_at") if isinstance(calendar_payload, dict) else "",
            },
            "reminders": {
                "synced": bool(reminders_payload),
                "synced_at": reminders_payload.get("synced_at") if isinstance(reminders_payload, dict) else "",
            },
            "focus": {
                "synced": bool(focus_payload),
                "synced_at": focus_payload.get("updated_at") if isinstance(focus_payload, dict) else "",
            },
            "now_playing": {
                "synced": bool(now_playing_payload),
                "synced_at": now_playing_payload.get("updated_at") if isinstance(now_playing_payload, dict) else "",
            },
            "sound_alert": {
                "synced": bool(latest_sound),
                "synced_at": latest_sound.get("received_at") if isinstance(latest_sound, dict) else "",
            },
            "vision_scan": {
                "synced": bool(latest_scan),
                "synced_at": latest_scan.get("received_at") if isinstance(latest_scan, dict) else "",
            },
        }

        aggregated = {
            "server": {
                "mode": str(watch_status.get("mode") or ""),
                "needs_count": int(watch_status.get("needs_count") or 0),
                "drift": bool(watch_status.get("drift")),
                "weather": str(watch_status.get("weather") or ""),
                "ts": str(watch_status.get("ts") or _ts()),
            },
            "calendar": {
                "synced": bool(calendar_payload),
                "count": int(calendar_payload.get("count") or len(calendar_events)) if isinstance(calendar_payload, dict) else len(calendar_events),
                "synced_at": str(calendar_payload.get("synced_at") or "") if isinstance(calendar_payload, dict) else "",
                "next_items": [
                    {
                        "title": str(event.get("title") or ""),
                        "start": str(event.get("start") or ""),
                        "end": str(event.get("end") or ""),
                        "location": str(event.get("location") or ""),
                        "calendar": str(event.get("calendar") or ""),
                    }
                    for event in calendar_events[:3]
                ],
            },
            "reminders": {
                "synced": bool(reminders_payload),
                "count": int(reminders_payload.get("count") or len(reminder_items)) if isinstance(reminders_payload, dict) else len(reminder_items),
                "synced_at": str(reminders_payload.get("synced_at") or "") if isinstance(reminders_payload, dict) else "",
                "top_items": [
                    {
                        "title": str(reminder.get("title") or ""),
                        "due": str(reminder.get("due") or ""),
                        "list": str(reminder.get("list") or ""),
                        "priority": int(reminder.get("priority") or 0),
                    }
                    for reminder in reminder_items[:3]
                ],
            },
            "focus": {
                "focus_active": bool(focus_payload.get("focus_active")) if isinstance(focus_payload, dict) else False,
                "updated_at": str(focus_payload.get("updated_at") or "") if isinstance(focus_payload, dict) else "",
                "source": str(focus_payload.get("source") or "") if isinstance(focus_payload, dict) else "",
            },
            "notifications": {
                "pending_count": _notification_center.count(status="pending"),
                "recent": notifications_recent,
            },
            "now_playing": {
                "title": str(now_playing_payload.get("title") or "") if isinstance(now_playing_payload, dict) else "",
                "artist": str(now_playing_payload.get("artist") or "") if isinstance(now_playing_payload, dict) else "",
                "album": str(now_playing_payload.get("album") or "") if isinstance(now_playing_payload, dict) else "",
                "is_playing": bool(now_playing_payload.get("is_playing")) if isinstance(now_playing_payload, dict) else False,
                "updated_at": str(now_playing_payload.get("updated_at") or "") if isinstance(now_playing_payload, dict) else "",
            },
            "sound_alert": {
                "label": str(latest_sound.get("classification") or latest_sound.get("label") or latest_sound.get("sound") or "") if isinstance(latest_sound, dict) else "",
                "confidence": latest_sound.get("confidence") if isinstance(latest_sound, dict) else None,
                "source": str(latest_sound.get("source") or "") if isinstance(latest_sound, dict) else "",
                "received_at": str(latest_sound.get("received_at") or "") if isinstance(latest_sound, dict) else "",
            },
            "vision_scan": {
                "context": str(latest_scan.get("context") or "") if isinstance(latest_scan, dict) else "",
                "source": str(latest_scan.get("source") or "") if isinstance(latest_scan, dict) else "",
                "text_preview": str(latest_scan.get("text") or "")[:180] if isinstance(latest_scan, dict) else "",
                "received_at": str(latest_scan.get("received_at") or "") if isinstance(latest_scan, dict) else "",
            },
            "presence": {
                "present_members": [str(name) for name in (home_state.get("present_members") or [])],
                "lights_on_count": len(home_state.get("lights_on") or []),
                "alert_count": len(home_state.get("alerts") or []),
            },
            "sync_health": sync_health,
        }
        return _ok(aggregated)

    # ------------------------------------------------------------------
    # GET /api/apple/weather
    # ------------------------------------------------------------------
    @app.get("/api/apple/weather")
    async def apple_weather():
        """Compact live Storm weather snapshot for Apple clients."""
        try:
            snapshot = runtime.storm_weather_snapshot(force=False)
        except Exception as exc:
            logger.warning("apple_weather: %s", exc)
            snapshot = {}

        current = snapshot.get("current") if isinstance(snapshot, dict) else {}
        current = current if isinstance(current, dict) else {}
        hourly = snapshot.get("hourly") if isinstance(snapshot, dict) else []
        hourly = hourly if isinstance(hourly, list) else []

        data = {
            "available": bool(snapshot.get("available")) if isinstance(snapshot, dict) else False,
            "live": bool(snapshot.get("live")) if isinstance(snapshot, dict) else False,
            "stale": bool(snapshot.get("stale")) if isinstance(snapshot, dict) else False,
            "location": str(snapshot.get("location") or current.get("location") or ""),
            "summary": str(snapshot.get("summary") or current.get("condition") or ""),
            "source": str(snapshot.get("source") or "weather.gov"),
            "fetched_at": str(snapshot.get("fetched_at") or _ts()),
            "current": {
                "temperature_f": current.get("temperature_f"),
                "feels_like_f": current.get("feels_like_f"),
                "condition": str(current.get("condition") or ""),
                "icon": str(current.get("icon") or ""),
                "wind": str(current.get("wind") or ""),
                "humidity_pct": current.get("humidity_pct"),
                "visibility_miles": current.get("visibility_miles"),
                "pressure_hpa": current.get("pressure_hpa"),
                "visual_key": str(current.get("visual_key") or ""),
                "moon_phase": str(current.get("moon_phase") or ""),
                "moon_phase_label": str(current.get("moon_phase_label") or ""),
                "using_forecast_fallback": bool(current.get("using_forecast_fallback")),
            },
            "hourly": [
                {
                    "time": str(item.get("time") or ""),
                    "temperature_f": item.get("temperature_f"),
                    "rain_pct": item.get("rain_pct"),
                    "forecast": str(item.get("forecast") or ""),
                    "icon": str(item.get("icon") or ""),
                }
                for item in hourly[:8]
                if isinstance(item, dict)
            ],
            "alerts_count": len(snapshot.get("alerts") or []) if isinstance(snapshot, dict) else 0,
        }
        return _ok(data)

    # ------------------------------------------------------------------
    # GET /api/apple/navigation/locations
    # ------------------------------------------------------------------
    @app.get("/api/apple/navigation/locations")
    async def apple_navigation_locations():
        """Saved family locations for Navigation quick actions."""
        payload = {"preferred_location_id": None, "saved_locations": [], "navigation_state": _load_navigation_state()}
        try:
            if LOCATION_SETTINGS_PATH.exists():
                raw = json.loads(LOCATION_SETTINGS_PATH.read_text(encoding="utf-8"))
                saved = raw.get("saved_locations") if isinstance(raw, dict) else []
                payload = {
                    "preferred_location_id": str((raw or {}).get("preferred_location_id") or "") or None,
                    "saved_locations": [
                        {
                            "id": str(item.get("id") or ""),
                            "label": str(item.get("label") or ""),
                            "address": str(item.get("address") or ""),
                            "geography": str(item.get("geography") or ""),
                            "latitude": item.get("latitude"),
                            "longitude": item.get("longitude"),
                            "source": str(item.get("source") or ""),
                            "notes": str(item.get("notes") or ""),
                        }
                        for item in saved
                        if isinstance(item, dict)
                    ],
                    "navigation_state": _load_navigation_state(),
                }
        except Exception as exc:
            logger.warning("apple_navigation_locations: %s", exc)
        return _ok(payload)

    @app.get("/api/apple/navigation/state")
    async def apple_navigation_state():
        return _ok(_load_navigation_state())

    @app.post("/api/apple/navigation/state")
    async def apple_navigation_state_update(payload: dict):
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="payload must be an object")
        return _ok(_save_navigation_state(payload))

    # ------------------------------------------------------------------
    # GET /api/apple/navigation/route
    # ------------------------------------------------------------------
    @app.get("/api/apple/navigation/route")
    async def apple_navigation_route(origin: str, destination: str):
        """Route weather summary for the iPhone Navigation tab."""
        origin = str(origin or "").strip()
        destination = str(destination or "").strip()
        if not origin or not destination:
            raise HTTPException(status_code=400, detail="origin and destination are required")
        try:
            route = runtime.storm_route_weather(origin, destination)
        except Exception as exc:
            logger.warning("apple_navigation_route: %s", exc)
            raise HTTPException(status_code=502, detail=str(exc))

        route_info = route.get("route") if isinstance(route, dict) else {}
        samples = route.get("samples") if isinstance(route, dict) else []
        payload = {
            "origin": route.get("origin") or {},
            "destination": route.get("destination") or {},
            "summary": str(route.get("summary") or ""),
            "hazard_active": bool(route.get("hazard_active")),
            "route": {
                "distance_miles": route_info.get("distance_miles"),
                "duration_minutes": route_info.get("duration_minutes"),
                "coordinates": route_info.get("coordinates") if isinstance(route_info.get("coordinates"), list) else [],
                "steps": [
                    {
                        "sequence": int(step.get("sequence") or 0),
                        "instruction": str(step.get("instruction") or ""),
                        "distance_miles": step.get("distance_miles"),
                        "duration_minutes": step.get("duration_minutes"),
                        "maneuver": str(step.get("maneuver") or ""),
                        "modifier": str(step.get("modifier") or ""),
                        "name": str(step.get("name") or ""),
                    }
                    for step in (route_info.get("steps") or [])
                    if isinstance(step, dict)
                ],
            },
            "samples": [
                {
                    "lat": item.get("lat"),
                    "lon": item.get("lon"),
                    "condition": str(item.get("condition") or ""),
                    "temperature_f": item.get("temperature_f"),
                    "rain_pct": item.get("rain_pct"),
                    "wind": str(item.get("wind") or ""),
                    "alerts": [str(alert) for alert in (item.get("alerts") or [])],
                }
                for item in samples
                if isinstance(item, dict)
            ],
        }
        return _ok(payload)

    # ------------------------------------------------------------------
    # GET /api/apple/navigation/stops
    # ------------------------------------------------------------------
    @app.get("/api/apple/navigation/stops")
    async def apple_navigation_stops(
        origin: str,
        destination: str,
        parks_radius_miles: float = 25.0,
    ):
        """Along-route stop suggestions for the Navigation tab."""
        origin = str(origin or "").strip()
        destination = str(destination or "").strip()
        if not origin or not destination:
            raise HTTPException(status_code=400, detail="origin and destination are required")
        parks_radius_miles = max(5.0, min(float(parks_radius_miles or 25.0), 100.0))

        try:
            route_packet = runtime.storm_route_weather(origin, destination)
        except Exception as exc:
            logger.warning("apple_navigation_stops.route: %s", exc)
            raise HTTPException(status_code=502, detail=str(exc))

        route_info = route_packet.get("route") if isinstance(route_packet, dict) else {}
        route_points = _nav_route_points(route_info if isinstance(route_info, dict) else {})
        total_miles = float(route_info.get("distance_miles") or 0) if isinstance(route_info, dict) else 0.0
        if not route_points:
            return _ok({"sections": []})

        bridge = _nav_bridge()
        interval = 12.0
        if total_miles > 0 and total_miles < 24:
            interval = max(5.0, total_miles / 3)
        samples = sample_route_points(route_points, interval_miles=interval)

        # Approximate mile markers aligned to the sampled points.
        mile_markers: list[float] = []
        cumulative = 0.0
        next_threshold = interval
        mile_markers.append(0.0)
        for idx in range(1, len(route_points)):
            cumulative += haversine(
                route_points[idx - 1][0], route_points[idx - 1][1],
                route_points[idx][0], route_points[idx][1],
            )
            if cumulative >= next_threshold:
                mile_markers.append(round(cumulative, 1))
                next_threshold += interval
        while len(mile_markers) < len(samples):
            mile_markers.append(round(total_miles, 1))

        sections: list[dict[str, Any]] = []
        seen_by_category: dict[str, set[str]] = {}
        categories = ["food", "starbucks", "parks", "historic", "family", "gas"]

        try:
            for category in categories:
                seen_by_category[category] = set()
                radius_m = min(int(parks_radius_miles * 1609.34), 50_000) if category in {"parks", "historic"} else 2400
                items: list[dict[str, Any]] = []
                for sample_idx, (slat, slng) in enumerate(samples):
                    marker = mile_markers[sample_idx] if sample_idx < len(mile_markers) else round(total_miles, 1)
                    for poi in bridge.search_places_near(slat, slng, category, radius_m=radius_m):
                        key = str(poi.get("place_id") or poi.get("name") or "")
                        if not key or key in seen_by_category[category]:
                            continue
                        seen_by_category[category].add(key)
                        items.append(
                            {
                                "name": str(poi.get("name") or ""),
                                "address": str(poi.get("address") or ""),
                                "description": "",
                                "url": "",
                                "lat": poi.get("lat"),
                                "lng": poi.get("lng"),
                                "rating": poi.get("rating"),
                                "route_mile_marker": marker,
                                "distance_from_route": None,
                            }
                        )
                items.sort(key=lambda item: item.get("route_mile_marker") or 0)

                # Blend in official NPS parks/sites for the parks category when possible.
                if category == "parks":
                    states = _nav_state_codes(
                        str((route_packet.get("origin") or {}).get("label") or ""),
                        str((route_packet.get("destination") or {}).get("label") or ""),
                    )
                    if states:
                        for park in _nav_nps_along_route(bridge, route_points, states, max_distance_miles=parks_radius_miles):
                            key = f"nps:{park.get('name')}"
                            if key in seen_by_category[category]:
                                continue
                            seen_by_category[category].add(key)
                            items.append(park)
                        items.sort(key=lambda item: item.get("route_mile_marker") or 0)

                sections.append(
                    {
                        "id": category,
                        "label": _NAV_STOP_LABELS.get(category, category.title()),
                        "items": items[:8],
                    }
                )
        except Exception as exc:
            logger.warning("apple_navigation_stops.poi: %s", exc)

        return _ok({"sections": sections})

    # ------------------------------------------------------------------
    # GET /api/apple/needs
    # ------------------------------------------------------------------
    @app.get("/api/apple/needs")
    async def apple_needs():
        """
        Return the Needs You items formatted for Watch display:
        shorter text, action buttons included.
        """
        items: list[dict] = []
        try:
            from .approvals import get_approval_guard
            guard = get_approval_guard()
            if guard is not None:
                for item in guard.get_pending_for_ui(actor_id="chris"):
                    if not isinstance(item, dict):
                        continue
                    risk = str(item.get("risk") or item.get("risk_tier") or "medium")
                    actions = ["approve"]
                    if risk in {"medium", "high", "critical"}:
                        actions.append("reject")
                    actions.append("cancel")
                    items.append({
                        "id": str(item.get("id") or item.get("request_id") or uuid.uuid4()),
                        "text": _truncate(str(item.get("text") or item.get("title") or ""), 80),
                        "detail": str(item.get("sub") or item.get("description") or ""),
                        "agent": str(item.get("agent") or item.get("requester") or "JARVIS"),
                        "risk": risk,
                        "expires_in": item.get("expires_in"),
                        "created_at": str(item.get("requested_at") or ""),
                        "status": "pending",
                        "allowed_actions": actions,
                        "request_type": str(item.get("action_type") or ""),
                    })
            else:
                pending = runtime.list_pending_approvals()
                raw = pending if isinstance(pending, list) else pending.get("items", [])
                for item in raw:
                    if not isinstance(item, dict):
                        continue
                    items.append({
                        "id": str(item.get("id") or item.get("request_id") or uuid.uuid4()),
                        "text": _truncate(str(item.get("title") or item.get("text") or ""), 80),
                        "detail": str(item.get("description") or item.get("sub") or ""),
                        "agent": str(item.get("agent") or item.get("requester") or "JARVIS"),
                        "risk": str(item.get("risk") or item.get("risk_tier") or "medium"),
                        "expires_in": item.get("expires_in"),
                        "created_at": str(item.get("requested_at") or ""),
                        "status": str(item.get("status") or "pending"),
                        "allowed_actions": ["approve", "reject", "cancel"],
                        "request_type": str(item.get("action_type") or ""),
                    })
        except Exception as exc:
            logger.warning("apple_needs: %s", exc)
        return _ok(items)

    # ------------------------------------------------------------------
    # POST /api/apple/speak
    # ------------------------------------------------------------------
    @app.post("/api/apple/speak")
    async def apple_speak(payload: dict):
        """
        Route a text command from Phone / Siri through the JARVIS agent router.
        """
        text = str(payload.get("text") or "").strip()
        actor_id = str(payload.get("actor_id") or "chris").strip()
        if not text:
            raise HTTPException(status_code=400, detail="text is required")

        response_text = ""
        agent_name = "JARVIS"
        speak = True

        # Try the main respond path
        try:
            result = runtime.respond(actor_id, "apple", text)
            if isinstance(result, dict):
                response_text = str(
                    result.get("output_text")
                    or result.get("response")
                    or result.get("text")
                    or ""
                )
                agent_name = str(result.get("agent") or result.get("actor") or "JARVIS")
            else:
                response_text = str(result)
        except Exception as exc:
            logger.warning("apple_speak: respond failed: %s", exc)
            response_text = "I'm working on that for you, Sir."

        return _ok({
            "response": response_text or "Understood.",
            "agent": agent_name,
            "speak": speak,
        })

    # ------------------------------------------------------------------
    # GET /api/apple/health/summary
    # ------------------------------------------------------------------
    @app.get("/api/apple/health/summary")
    async def apple_health_summary(actor: str = "chris"):
        """Health summary for HealthKit display and Watch complication."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        agg = _health_store.get_summary(actor, today)

        # Thor note — best effort
        thor_note = "Keep it up today."
        try:
            snap = runtime.chamber_home_snapshot(actor)
            health_cards = [
                item for item in (snap.get("briefing_items") or snap.get("feed") or [])
                if isinstance(item, dict) and "health" in str(item.get("domain", "")).lower()
            ]
            if health_cards:
                thor_note = str(health_cards[0].get("text") or health_cards[0].get("sub") or thor_note)
        except Exception:
            pass

        # Readiness heuristic
        steps = agg.get("steps", 0)
        sleep = agg.get("sleep_hours", 0.0)
        hr = agg.get("heart_rate_avg", 0)
        if sleep >= 7 and steps >= 3000:
            readiness = "good"
        elif sleep >= 5:
            readiness = "moderate"
        else:
            readiness = "low"

        daily_score: dict[str, Any] | None = None
        protocol_items: list[dict[str, Any]] = []
        alerts: list[dict[str, Any]] = []
        next_actions: list[str] = []

        try:
            from .health_bridge import compute_readiness, get_latest

            readiness_detail = compute_readiness(get_latest())
            if readiness_detail.get("score") is not None:
                daily_score = {
                    "value": int(readiness_detail.get("score") or 0),
                    "grade": str(readiness_detail.get("grade") or readiness.title()),
                    "message": str(readiness_detail.get("message") or ""),
                    "estimated": bool(readiness_detail.get("data_incomplete")),
                }

            for factor in readiness_detail.get("factors") or []:
                if not isinstance(factor, dict):
                    continue
                label = str(factor.get("label") or factor.get("metric") or "Metric")
                score = factor.get("score")
                missing = bool(factor.get("missing"))
                if missing:
                    protocol_items.append({
                        "title": f"Fill {label} gap",
                        "detail": f"Capture {label.lower()} again so JARVIS can score your recovery accurately.",
                        "emphasis": "medium",
                    })
                elif isinstance(score, (int, float)) and float(score) < 60:
                    protocol_items.append({
                        "title": f"Support {label}",
                        "detail": f"{label} is trailing today. Favor hydration, recovery, and a lighter load.",
                        "emphasis": "high",
                    })
        except Exception:
            pass

        completeness = _safe_read_json(Path.home() / ".jarvis" / "health" / "completeness_score.json", {})
        if isinstance(completeness, dict):
            total_score = completeness.get("total_score")
            grade = completeness.get("grade")
            if daily_score is None and isinstance(total_score, (int, float)):
                daily_score = {
                    "value": int(round(float(total_score))),
                    "grade": str(grade or readiness.title()),
                    "message": "Health file completeness score from JARVIS baseline review.",
                    "estimated": False,
                }
            for gap in (completeness.get("critical_gaps") or [])[:3]:
                if gap:
                    alerts.append({
                        "title": str(gap),
                        "severity": "high",
                    })
            for quick_win in (completeness.get("quick_wins") or [])[:3]:
                if quick_win:
                    next_actions.append(str(quick_win))

        health_state = _safe_read_json(Path.home() / ".jarvis" / "health" / "chris_health_state.json", {})
        if isinstance(health_state, dict):
            conditions = ((health_state.get("medical_history") or {}).get("known_conditions") or [])[:8]
            for condition in conditions:
                if not isinstance(condition, dict):
                    continue
                risk_score = condition.get("risk_score")
                key_finding = str(condition.get("key_finding") or "").strip()
                if isinstance(risk_score, (int, float)) and float(risk_score) >= 85 and key_finding:
                    alerts.append({
                        "title": str(condition.get("name") or "High-risk condition"),
                        "detail": key_finding,
                        "severity": "high",
                    })
            meds = ((health_state.get("current_care_state") or {}).get("medications") or [])[:8]
            for med in meds:
                if not isinstance(med, dict) or not med.get("high_risk"):
                    continue
                monitoring = str(med.get("monitoring") or "").strip()
                if monitoring:
                    protocol_items.append({
                        "title": f"Monitor {med.get('name') or 'medication'}",
                        "detail": monitoring,
                        "emphasis": "medium",
                    })

        protocol_items = protocol_items[:4]
        next_actions = next_actions[:4]
        alerts = alerts[:4]

        data = {
            "steps_today": agg["steps"],
            "heart_rate_avg": agg["heart_rate_avg"],
            "sleep_hours": agg["sleep_hours"],
            "active_calories": agg["active_calories"],
            "stand_hours": agg["stand_hours"],
            "hrv": agg["hrv"],
            "readiness": readiness,
            "thor_note": thor_note,
            "last_sync": agg["last_sync"],
            "daily_score": daily_score,
            "protocol_items": protocol_items,
            "alerts": alerts,
            "next_actions": next_actions,
        }
        return _ok(data)

    # ------------------------------------------------------------------
    # POST /api/apple/health/log
    # ------------------------------------------------------------------
    @app.post("/api/apple/health/log")
    async def apple_health_log(payload: dict):
        """
        Receive HealthKit samples pushed from iPhone and persist them.
        Body: {"actor_id": str, "samples": [{type, value, date, source}]}
        """
        actor_id = str(payload.get("actor_id") or "chris").strip()
        samples = payload.get("samples") or []
        if not isinstance(samples, list):
            raise HTTPException(status_code=400, detail="samples must be a list")

        logged = _health_store.log_samples(actor_id, samples)
        return _ok({"logged": logged})

    # ------------------------------------------------------------------
    # GET /api/apple/home/state
    # ------------------------------------------------------------------
    @app.get("/api/apple/home/state")
    async def apple_home_state():
        """Return current house state via HomeAssistantConnector."""
        needs_count = 0
        try:
            status = (await apple_status()).get("data") or {}
            needs_count = int(status.get("needs_count") or 0)
        except Exception:
            needs_count = 0
        try:
            from .data_connectors import get_ha
            ha = get_ha()
            if ha is not None:
                state = ha.get_house_state()
            else:
                state = _mock_home_state()
        except Exception as exc:
            logger.warning("apple_home_state: %s", exc)
            state = _mock_home_state()
        if isinstance(state, dict):
            state = dict(state)
            home_context = _build_home_context(needs_count=needs_count)
            state["home_context"] = home_context
            state["action_items"] = _build_home_action_items(
                state=state,
                home_context=home_context,
                needs_count=needs_count,
            )
        return _ok(state)

    # ------------------------------------------------------------------
    # POST /api/apple/home/command
    # ------------------------------------------------------------------
    @app.post("/api/apple/home/command")
    async def apple_home_command(payload: dict):
        """
        Stage a home command for approval before execution.
        Body: {"command": str, "entity_id": str, "service": str}
        """
        command = str(payload.get("command") or "").strip()
        entity_id = str(payload.get("entity_id") or "").strip()
        service = str(payload.get("service") or "").strip()
        if not command:
            raise HTTPException(status_code=400, detail="command is required")

        request_id = str(uuid.uuid4())
        try:
            from .approvals import get_approval_guard
            guard = get_approval_guard()
            if guard is not None:
                request_id = guard.request_approval(
                    title=command,
                    description=f"Home command: {service} on {entity_id}",
                    action_type="home_control",
                    payload={"command": command, "entity_id": entity_id, "service": service},
                )
        except Exception as exc:
            logger.warning("apple_home_command: approval guard failed: %s", exc)

        event = _record_shared_event(
            domain="home",
            kind="stage_ready",
            title=command,
            detail=f"Home command staged: {service or 'service'} on {entity_id or 'target'}.",
            severity="medium",
            actor="chris",
            source="apple.home_command",
            source_id=request_id,
            navigation_target="home",
            actions=["open", "stage", "dismiss"],
            trust_zone="household_home",
            authority_stage="draft",
            why_now="A home command was requested from the Apple client and now awaits approval.",
            metadata={"command": command, "entity_id": entity_id, "service": service},
        )
        _create_notification_from_event(
            event,
            category="household",
            delivery_mode="badge_only",
            available_actions=["open", "dismiss", "resolve"],
            source_summary="Staged home command",
        )

        return _ok({"request_id": request_id, "status": "pending_approval"})

    # ------------------------------------------------------------------
    # POST /api/apple/presence
    # ------------------------------------------------------------------
    @app.post("/api/apple/presence")
    async def apple_presence(payload: dict):
        """
        Phone reports presence events (arrived_home / left_home).
        Fires the matching scheduler event so Home Assistant agents react.
        """
        actor_id = str(payload.get("actor_id") or "chris").strip()
        event = str(payload.get("event") or "").strip()
        lat = float(payload.get("lat") or 0)
        lon = float(payload.get("lon") or 0)

        if event not in ("arrived_home", "left_home"):
            raise HTTPException(status_code=400, detail="event must be arrived_home or left_home")

        # Fire scheduler event (non-fatal if scheduler unavailable)
        try:
            from .scheduler import get_scheduler, EVENT_HOME_ARRIVAL, EVENT_HOME_DEPARTURE
            scheduler = get_scheduler()
            if scheduler is not None:
                event_type = EVENT_HOME_ARRIVAL if event == "arrived_home" else EVENT_HOME_DEPARTURE
                scheduler.fire_event(event_type, {"actor": actor_id, "lat": lat, "lon": lon})
        except Exception as exc:
            logger.warning("apple_presence: scheduler fire_event failed: %s", exc)

        # Also call runtime presence update for immediate effect
        try:
            runtime.phone_presence_update(actor_id, event, lat=lat, lon=lon)
        except Exception:
            try:
                runtime.presence_update(actor_id, event)
            except Exception as exc2:
                logger.warning("apple_presence: runtime presence update failed: %s", exc2)

        _record_shared_event(
            domain="home",
            kind="info",
            title=f"{actor_id.capitalize()} {event.replace('_', ' ')}",
            detail=f"Presence update received from iPhone at {lat:.4f}, {lon:.4f}.",
            severity="low",
            actor=actor_id,
            source="apple.presence",
            source_id=event,
            navigation_target="home",
            actions=["open"],
            trust_zone="household_presence",
            authority_stage="live",
            why_now="Presence changes update the live household state.",
            metadata={"lat": lat, "lon": lon, "event": event},
        )

        return _ok({"event": event, "actor_id": actor_id, "ts": _ts()})

    # ------------------------------------------------------------------
    # GET /api/apple/notifications/pending
    # ------------------------------------------------------------------
    @app.get("/api/apple/notifications/pending")
    async def apple_notifications_pending():
        """
        Pull-based notification delivery.
        Returns any queued notifications and clears them so they are not
        delivered twice.
        """
        notifications = _notification_store.drain()
        return _ok({"notifications": notifications})

    # ------------------------------------------------------------------
    # GET /api/apple/events/recent
    # ------------------------------------------------------------------
    @app.get("/api/apple/events/recent")
    async def apple_events_recent(limit: int = 25, domain: str = "", status: str = "", severity: str = ""):
        return _ok(
            {
                "events": _event_log.recent(
                    limit=max(1, min(limit, 100)),
                    domain=domain or None,
                    status=status or None,
                    severity=severity or None,
                )
            }
        )

    # ------------------------------------------------------------------
    # GET /api/apple/notifications
    # ------------------------------------------------------------------
    @app.get("/api/apple/notifications")
    async def apple_notifications(status: str = "", category: str = "", limit: int = 50):
        return _ok(
            {
                "notifications": _notification_center.list(
                    status=status or None,
                    category=category or None,
                    limit=max(1, min(limit, 200)),
                )
            }
        )

    async def _notification_action(notification_id: str, status: str, reason: str) -> dict:
        item = _notification_center.update_status(notification_id, status, reason=reason)
        if item is None:
            raise HTTPException(status_code=404, detail="Notification not found")
        return _ok({"notification": item, "status": status})

    @app.post("/api/apple/notifications/{notification_id}/seen")
    async def apple_notification_seen(notification_id: str):
        return await _notification_action(notification_id, "seen", "Marked seen from Apple client.")

    @app.post("/api/apple/notifications/{notification_id}/dismiss")
    async def apple_notification_dismiss(notification_id: str):
        return await _notification_action(notification_id, "dismissed", "Dismissed from Apple client.")

    @app.post("/api/apple/notifications/{notification_id}/resolve")
    async def apple_notification_resolve(notification_id: str):
        return await _notification_action(notification_id, "resolved", "Resolved from Apple client.")

    @app.post("/api/apple/notifications/{notification_id}/snooze")
    async def apple_notification_snooze(notification_id: str):
        return await _notification_action(notification_id, "snoozed", "Snoozed from Apple client.")

    # ------------------------------------------------------------------
    # GET /api/apple/voice/greeting
    # ------------------------------------------------------------------
    @app.get("/api/apple/voice/greeting")
    async def apple_voice_greeting(actor: str = "chris"):
        """Return a voice greeting suitable for wake-word or app launch."""
        greeting, mode = _time_of_day_greeting()
        return _ok({"greeting": greeting, "mode": mode})

    # ------------------------------------------------------------------
    # POST /api/apple/approvals/{request_id}/approve
    # ------------------------------------------------------------------
    @app.post("/api/apple/approvals/{request_id}/approve")
    async def apple_approve(request_id: str, payload: dict = {}):
        """One-tap approval from Watch or Phone."""
        from .approvals import get_approval_queue
        queue = get_approval_queue()
        if queue is None:
            raise HTTPException(status_code=503, detail="Approval system not initialised")

        approved_by = str(payload.get("approved_by") or "chris")
        from dataclasses import asdict as _asdict
        item = queue.approve(request_id, approved_by=approved_by)
        if item is None:
            raise HTTPException(status_code=404, detail="Pending approval request not found")

        try:
            item_dict = _asdict(item)
        except Exception:
            item_dict = dict(item) if hasattr(item, "__dict__") else {}

        # Push a confirmation to the approver's phone
        try:
            from .apns_sender import send_push
            title_text = item_dict.get("title") or "Request"
            import asyncio
            asyncio.get_event_loop().run_in_executor(
                None,
                lambda: send_push(
                    approved_by,
                    title="✅ Approved",
                    body=str(title_text)[:100],
                    category="approval",
                )
            )
        except Exception:
            pass

        event = _record_shared_event(
            domain="approvals",
            kind="resolved",
            title="Approval granted",
            detail=str(item_dict.get("title") or request_id),
            severity="medium",
            actor=approved_by,
            source="apple.approvals.approve",
            source_id=request_id,
            navigation_target="needs",
            actions=["open"],
            trust_zone="household_approvals",
            authority_stage="live",
            why_now="A pending approval was resolved from the Apple client.",
            metadata={"request_id": request_id, "status": "approved"},
        )
        _create_notification_from_event(
            event,
            category="approval",
            delivery_mode="badge_only",
            available_actions=["open", "resolve"],
            source_summary="Approval workflow",
        )

        return _ok({"status": "approved", "request": item_dict})

    @app.post("/api/apple/approvals/{request_id}/reject")
    async def apple_reject(request_id: str, payload: dict = {}):
        """Reject a pending request from Phone or Watch."""
        from .approvals import get_approval_queue
        queue = get_approval_queue()
        if queue is None:
            raise HTTPException(status_code=503, detail="Approval system not initialised")

        reason = str(payload.get("reason") or "").strip()
        rejected_by = str(payload.get("rejected_by") or "chris").strip()
        ok = queue.reject(request_id, reason=reason, rejected_by=rejected_by)
        if not ok:
            raise HTTPException(status_code=404, detail="Pending approval request not found")
        _record_shared_event(
            domain="approvals",
            kind="resolved",
            title="Approval rejected",
            detail=reason or request_id,
            severity="medium",
            actor=rejected_by,
            source="apple.approvals.reject",
            source_id=request_id,
            navigation_target="needs",
            actions=["open"],
            trust_zone="household_approvals",
            authority_stage="live",
            why_now="A pending approval was rejected from the Apple client.",
            metadata={"request_id": request_id, "status": "rejected", "reason": reason},
        )
        return _ok({"status": "rejected", "request_id": request_id, "reason": reason})

    @app.post("/api/apple/approvals/{request_id}/cancel")
    async def apple_cancel(request_id: str):
        """Cancel a pending request from Phone or Watch."""
        from .approvals import get_approval_queue
        queue = get_approval_queue()
        if queue is None:
            raise HTTPException(status_code=503, detail="Approval system not initialised")

        ok = queue.cancel(request_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Pending approval request not found")
        _record_shared_event(
            domain="approvals",
            kind="resolved",
            title="Approval cancelled",
            detail=request_id,
            severity="low",
            actor="chris",
            source="apple.approvals.cancel",
            source_id=request_id,
            navigation_target="needs",
            actions=["open"],
            trust_zone="household_approvals",
            authority_stage="live",
            why_now="A pending approval was cancelled from the Apple client.",
            metadata={"request_id": request_id, "status": "cancelled"},
        )
        return _ok({"status": "cancelled", "request_id": request_id})

    # ── EventKit: Calendar ────────────────────────────────────────────────────

    @app.post("/api/apple/calendar")
    async def apple_calendar(payload: dict):
        """Receives Calendar events from EventKit on the iPhone.
        Writes to data/apple/calendar_events.json for the runtime to consume."""
        events = payload.get("events", [])
        out_path = Path("data/apple/calendar_events.json")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps({
            "events": events,
            "count":  len(events),
            "source": "eventkit",
            "synced_at": _ts(),
        }, indent=2))
        logger.info("EventKit calendar: stored %d events", len(events))
        _record_shared_event(
            domain="calendar",
            kind="info",
            title="Calendar synced",
            detail=f"Stored {len(events)} calendar events from EventKit.",
            severity="low",
            actor="iphone",
            source="apple.calendar",
            source_id="eventkit",
            navigation_target="brief",
            actions=["open"],
            trust_zone="household_schedule",
            authority_stage="live",
            why_now="The iPhone mirrored calendar state into JARVIS.",
            metadata={"count": len(events)},
        )
        return _ok({"stored": len(events)})

    # ── EventKit: Reminders ───────────────────────────────────────────────────

    @app.post("/api/apple/reminders")
    async def apple_reminders(payload: dict):
        """Receives Reminders from EventKit on the iPhone.
        Writes to data/apple/reminders.json."""
        reminders = payload.get("reminders", [])
        out_path = Path("data/apple/reminders.json")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps({
            "reminders": reminders,
            "count":     len(reminders),
            "source":    "eventkit",
            "synced_at": _ts(),
        }, indent=2))
        logger.info("EventKit reminders: stored %d items", len(reminders))
        _record_shared_event(
            domain="reminders",
            kind="info",
            title="Reminders synced",
            detail=f"Stored {len(reminders)} reminders from EventKit.",
            severity="low",
            actor="iphone",
            source="apple.reminders",
            source_id="eventkit",
            navigation_target="brief",
            actions=["open"],
            trust_zone="household_schedule",
            authority_stage="live",
            why_now="The iPhone mirrored reminder state into JARVIS.",
            metadata={"count": len(reminders)},
        )
        return _ok({"stored": len(reminders)})

    # ── Focus Filter ─────────────────────────────────────────────────────────

    @app.post("/api/apple/focus")
    async def apple_focus(payload: dict):
        """Receives iOS Focus Filter state so JARVIS can adjust notification behavior."""
        out_path = Path("data/apple/focus_state.json")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        record = {**payload, "updated_at": _ts()}
        out_path.write_text(json.dumps(record, indent=2))

        try:
            from .service import broadcast_event
            broadcast_event("apple.focus", record)
        except Exception:
            pass

        event = _record_shared_event(
            domain="system",
            kind="info",
            title="Focus state updated",
            detail=f"Focus is {'active' if bool(payload.get('focus_active')) else 'inactive'}.",
            severity="low",
            actor=str(payload.get("actor_id") or "iphone"),
            source="apple.focus",
            source_id=str(payload.get("source") or "focus"),
            navigation_target="systems",
            actions=["open"],
            trust_zone="household_attention",
            authority_stage="live",
            why_now="Focus posture affects interruption behavior.",
            metadata=record,
        )
        return _ok({"stored": True, "focus_active": bool(payload.get("focus_active"))})

    # ── Sound Analysis ───────────────────────────────────────────────────────

    @app.post("/api/apple/sound-alert")
    async def apple_sound_alert(payload: dict):
        """Receives on-device SoundAnalysis alerts from the iPhone."""
        out_path = Path("data/apple/sound_alerts.jsonl")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        record = {**payload, "received_at": _ts()}
        with out_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")

        try:
            from .service import broadcast_event
            broadcast_event("apple.sound_alert", record)
        except Exception:
            pass

        event = _record_shared_event(
            domain="sound",
            kind="warning",
            title=str(payload.get("classification") or payload.get("label") or "Sound alert"),
            detail=str(payload.get("detail") or payload.get("summary") or "On-device sound analysis captured an alert."),
            severity="medium" if _coerce_float(payload.get("confidence"), 0.0) >= 0.7 else "low",
            actor=str(payload.get("actor_id") or "iphone"),
            source="apple.sound_alert",
            source_id=str(record.get("received_at") or ""),
            navigation_target="systems",
            actions=["open", "dismiss"],
            trust_zone="household_safety",
            authority_stage="live",
            why_now="A new sound alert was captured on-device.",
            metadata=record,
        )
        _create_notification_from_event(
            event,
            category="household",
            delivery_mode="badge_only",
            available_actions=["open", "dismiss", "resolve"],
            source_summary="Sound alert",
        )

        return _ok({"stored": True})

    # ── Vision Scan ──────────────────────────────────────────────────────────

    @app.post("/api/apple/vision/scan")
    async def apple_vision_scan(payload: dict):
        """Receives OCR/barcode scan text produced on-device by Vision."""
        out_path = Path("data/apple/vision_scans.jsonl")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        record = {**payload, "received_at": _ts()}
        with out_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")

        try:
            from .service import broadcast_event
            broadcast_event("apple.vision_scan", {
                "context": payload.get("context"),
                "source": payload.get("source"),
                "text_preview": str(payload.get("text") or "")[:200],
            })
        except Exception:
            pass

        event = _record_shared_event(
            domain="vision",
            kind="info",
            title=str(payload.get("context") or "Vision scan"),
            detail=str(payload.get("text") or "")[:200] or "A new on-device scan was captured.",
            severity="low",
            actor=str(payload.get("actor_id") or "iphone"),
            source="apple.vision_scan",
            source_id=str(record.get("received_at") or ""),
            navigation_target="systems",
            actions=["open", "dismiss"],
            trust_zone="household_perception",
            authority_stage="live",
            why_now="A new scan was captured on-device.",
            metadata={"source": payload.get("source"), "context": payload.get("context")},
        )
        return _ok({"stored": True})

    # ── MusicKit: Now Playing ─────────────────────────────────────────────────

    @app.post("/api/apple/now-playing")
    async def apple_now_playing(payload: dict):
        """Receives Now Playing info from MediaPlayer on the iPhone."""
        out_path = Path("data/apple/now_playing.json")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps({
            **{k: v for k, v in payload.items() if k != "artwork_b64"},
            "updated_at": _ts(),
        }, indent=2))
        # Persist artwork separately as a JPEG
        if artwork_b64 := payload.get("artwork_b64"):
            import base64
            artwork_path = Path("data/apple/now_playing_artwork.jpg")
            try:
                artwork_path.write_bytes(base64.b64decode(artwork_b64))
            except Exception:
                pass
        # Broadcast to web UI via SSE
        try:
            from .service import broadcast_event
            broadcast_event("apple.now_playing", {
                "title":  payload.get("title"),
                "artist": payload.get("artist"),
                "album":  payload.get("album"),
                "playing": payload.get("is_playing"),
            })
        except Exception:
            pass
        _record_shared_event(
            domain="media",
            kind="info",
            title=str(payload.get("title") or "Now playing updated"),
            detail=str(payload.get("artist") or ""),
            severity="low",
            actor="iphone",
            source="apple.now_playing",
            source_id=str(payload.get("title") or ""),
            navigation_target="brief",
            actions=["open"],
            trust_zone="household_media",
            authority_stage="live",
            why_now="Now playing state changed on the iPhone.",
            metadata={"is_playing": bool(payload.get("is_playing")), "artist": payload.get("artist"), "album": payload.get("album")},
        )
        return _ok({"stored": True})

    # ── TTS via iOS (replaces ElevenLabs) ────────────────────────────────────

    @app.post("/api/apple/speak")
    async def apple_speak_push(payload: dict):
        """Push a 'speak this text' silent notification to the user's iPhone.
        The iOS app speaks it using AVSpeechSynthesizer (free, on-device)."""
        text   = str(payload.get("text") or "").strip()
        actor  = str(payload.get("actor") or "chris")
        if not text:
            return _ok({"sent": False, "reason": "empty text"})
        try:
            from .apns_sender import send_push
            send_push(
                actor,
                title="",
                body=text,
                category="speak",
                extra={"speak": text},
                content_available=True,
            )
            return _ok({"sent": True, "chars": len(text)})
        except Exception as exc:
            return _ok({"sent": False, "reason": str(exc)})


# ── Catalyst overview ────────────────────────────────────────────────────────

    @app.get("/api/apple/catalyst")
    async def apple_catalyst():
        """Lightweight Catalyst workspace overview for the iPhone Catalyst tab."""
        try:
            data_root = Path("data/catalyst")
            # Work lifecycle — active / in-review items
            wl_path = data_root / "work_lifecycle.json"
            wl_raw = json.loads(wl_path.read_text()) if wl_path.exists() else {}
            wl_items = list(wl_raw.values()) if isinstance(wl_raw, dict) else wl_raw
            active_work = [
                {
                    "work_id":  str(i.get("work_id") or ""),
                    "title":    _truncate(str(i.get("title") or ""), 60),
                    "domain":   str(i.get("domain") or ""),
                    "stage":    str(i.get("current_stage") or i.get("status") or ""),
                    "updated":  str(i.get("updated_at") or i.get("created_at") or ""),
                }
                for i in wl_items
                if str(i.get("status") or "").lower() not in ("done", "archived", "cancelled")
            ][:10]

            # Recent signals
            sig_path = data_root / "signals.json"
            sig_raw = json.loads(sig_path.read_text()) if sig_path.exists() else {}
            sig_items = list(sig_raw.values()) if isinstance(sig_raw, dict) else sig_raw
            signals = [
                {
                    "signal_id": str(s.get("signal_id") or ""),
                    "title":     _truncate(str(s.get("title") or s.get("content") or ""), 60),
                    "source":    str(s.get("source") or ""),
                    "tags":      s.get("tags") or [],
                    "timestamp": str(s.get("timestamp") or ""),
                }
                for s in (sig_items[-8:] if sig_items else [])
            ]

            # Pipeline portfolio summary
            pipeline_path = data_root / "pipeline_state.json"
            portfolio = {}
            if pipeline_path.exists():
                ps = json.loads(pipeline_path.read_text())
                portfolio = ps.get("portfolio") or {}

            return _ok({
                "active_work": active_work,
                "signals":     signals,
                "portfolio":   portfolio,
                "updated_at":  _ts(),
            })
        except Exception as exc:
            logger.exception("apple_catalyst failed: %s", exc)
            return _ok({"active_work": [], "signals": [], "portfolio": {}, "updated_at": _ts()})

    # ── Chronicle overview ────────────────────────────────────────────────────

    @app.get("/api/apple/chronicle")
    async def apple_chronicle(actor: str = "chris"):
        """Recent Chronicle entries and insights for the iPhone Chronicle tab."""
        try:
            entries_path = Path("data/chronicle/entries.jsonl")
            raw_entries = []
            if entries_path.exists():
                for line in entries_path.read_text().splitlines():
                    line = line.strip()
                    if line:
                        try:
                            raw_entries.append(json.loads(line))
                        except Exception:
                            pass

            entries = _chronicle_fallback_entries(raw_entries, actor)
            context = _chronicle_fallback_context(raw_entries, actor)
            patterns = _chronicle_fallback_patterns(raw_entries, actor)

            try:
                from .chronicle_bridge import get_chronicle_bridge

                bridge = get_chronicle_bridge()
                if bridge is not None:
                    bridge_context = await asyncio.to_thread(bridge.get_context)
                    if isinstance(bridge_context, dict) and bridge_context.get("ok"):
                        context = {
                            "study": bridge_context.get("study"),
                            "active_prayers": bridge_context.get("active_prayers") or [],
                            "todays_rhythm": bridge_context.get("todays_rhythm"),
                            "top_themes": bridge_context.get("top_themes") or [],
                            "total_entries": int(bridge_context.get("total_entries") or len(entries)),
                            "active_prayer_count": int(bridge_context.get("active_prayer_count") or 0),
                            "answered_prayer_count": int(bridge_context.get("answered_prayer_count") or 0),
                        }
                    bridge_patterns = await asyncio.to_thread(bridge.get_patterns)
                    if isinstance(bridge_patterns, dict) and bridge_patterns.get("ok"):
                        patterns = {
                            "window_days": int(bridge_patterns.get("window_days") or 30),
                            "total_recent_entries": int(bridge_patterns.get("total_recent_entries") or 0),
                            "entry_type_breakdown": bridge_patterns.get("entry_type_breakdown") or {},
                            "recurring_themes": bridge_patterns.get("recurring_themes") or [],
                            "prayer_arc": bridge_patterns.get("prayer_arc") or {
                                "total_active": 0,
                                "answered_total": 0,
                                "answered_recent": 0,
                            },
                            "writing_streak_days": int(bridge_patterns.get("writing_streak_days") or 0),
                        }
            except Exception as exc:
                logger.warning("apple_chronicle bridge context fallback: %s", exc)

            return _ok({
                "entries": entries,
                "context": context,
                "patterns": patterns,
                "updated_at": _ts(),
            })
        except Exception as exc:
            logger.exception("apple_chronicle failed: %s", exc)
            return _ok({
                "entries": [],
                "context": {
                    "study": None,
                    "active_prayers": [],
                    "todays_rhythm": None,
                    "top_themes": [],
                    "total_entries": 0,
                    "active_prayer_count": 0,
                    "answered_prayer_count": 0,
                },
                "patterns": {
                    "window_days": 30,
                    "total_recent_entries": 0,
                    "entry_type_breakdown": {},
                    "recurring_themes": [],
                    "prayer_arc": {"total_active": 0, "answered_total": 0, "answered_recent": 0},
                    "writing_streak_days": 0,
                },
                "updated_at": _ts(),
            })

    @app.post("/api/apple/chronicle/capture")
    async def apple_chronicle_capture(payload: dict):
        """Capture a quick reflection or prayer from the phone."""
        try:
            entry_type = str(payload.get("type") or "reflection")
            note       = str(payload.get("note") or "").strip()
            actor      = str(payload.get("actor_id") or "chris")
            if not note:
                return _ok({"captured": False, "reason": "empty"})
            entry = {
                "entry_id":   str(uuid.uuid4()),
                "entry_type": entry_type,
                "title":      note[:50],
                "body":       note,
                "note":       note,
                "actor":      actor,
                "timestamp":  _ts(),
                "created_at": _ts(),
                "source":     "apple_phone",
            }
            entries_path = Path("data/chronicle/entries.jsonl")
            entries_path.parent.mkdir(parents=True, exist_ok=True)
            with entries_path.open("a") as f:
                f.write(json.dumps(entry) + "\n")
            return _ok({"captured": True, "entry_id": entry["entry_id"]})
        except Exception as exc:
            return _ok({"captured": False, "reason": str(exc)})

    # ── Faith daily word ──────────────────────────────────────────────────────

    @app.get("/api/apple/faith")
    async def apple_faith(actor: str = "chris"):
        """Daily word and faith formation context for the iPhone Faith tab."""
        try:
            fw_path = Path("data/settings/faith_daily_word.json")
            fw = {}
            if fw_path.exists():
                fw = json.loads(fw_path.read_text())

            # Morning spiritual context from chronicle bridge
            morning_context = {}
            try:
                from .chronicle_bridge import get_morning_context
                morning_context = await asyncio.to_thread(get_morning_context, actor)
            except Exception:
                pass

            return _ok({
                "daily_word": {
                    "agent":      str(fw.get("agent_name") or "JARVIS"),
                    "agent_title": str(fw.get("agent_title") or ""),
                    "word":       str(fw.get("word") or ""),
                    "passage":    str(fw.get("passage") or ""),
                    "domain":     str(fw.get("domain") or ""),
                    "generated_at": str(fw.get("generated_at") or ""),
                },
                "morning_context": morning_context,
                "updated_at": _ts(),
            })
        except Exception as exc:
            logger.exception("apple_faith failed: %s", exc)
            return _ok({"daily_word": {"agent": "JARVIS", "word": "", "passage": "", "domain": "", "agent_title": "", "generated_at": ""}, "morning_context": {}, "updated_at": _ts()})

    # ── Publishing dashboard ──────────────────────────────────────────────────

    @app.get("/api/apple/publishing")
    async def apple_publishing():
        """Publishing overview for the iPhone Publish tab."""
        try:
            pub_root = Path.home() / ".jarvis" / "publishing"

            # Projects
            proj_path = pub_root / "projects.json"
            proj_raw  = json.loads(proj_path.read_text()) if proj_path.exists() else {}
            proj_list = list(proj_raw.values()) if isinstance(proj_raw, dict) else proj_raw
            active_projects = [
                p for p in proj_list
                if str(p.get("status") or "").lower() != "archived"
            ]
            active_projects.sort(
                key=lambda project: str(project.get("updated_at") or project.get("created_at") or ""),
                reverse=True,
            )
            projects  = [
                {
                    "project_id": str(p.get("project_id") or ""),
                    "title":      str(p.get("title") or ""),
                    "type":       str(p.get("project_type") or ""),
                    "status":     str(p.get("status") or ""),
                    "platform":   str(p.get("platform") or ""),
                    "url":        p.get("url") or None,
                    "description": str(p.get("description") or ""),
                    "notes": str(p.get("notes") or ""),
                    "updated_at": str(p.get("updated_at") or p.get("created_at") or ""),
                }
                for p in active_projects[:8]
            ]
            project_lookup = {
                str(project.get("project_id") or ""): project
                for project in active_projects
                if str(project.get("project_id") or "")
            }

            # Revenue streams total
            rev_path = pub_root / "revenue_streams.json"
            rev_raw  = json.loads(rev_path.read_text()) if rev_path.exists() else {}
            rev_list = list(rev_raw.values()) if isinstance(rev_raw, dict) else rev_raw
            active_rev  = [s for s in rev_list if s.get("active")]
            monthly_est = sum(float(s.get("monthly_estimate") or 0) for s in active_rev)
            revenue_summary = {
                "monthly_estimate": round(monthly_est, 2),
                "stream_count":     len(active_rev),
                "streams": [
                    {
                        "stream_id":   str(s.get("stream_id") or ""),
                        "type":        str(s.get("stream_type") or ""),
                        "source":      str(s.get("source") or ""),
                        "monthly_est": float(s.get("monthly_estimate") or 0),
                    }
                    for s in active_rev[:5]
                ],
            }

            # Upcoming calendar items
            cal_path  = pub_root / "content_calendar.jsonl"
            cal_items = []
            if cal_path.exists():
                for line in cal_path.read_text().splitlines():
                    if line.strip():
                        try:
                            cal_items.append(json.loads(line))
                        except Exception:
                            pass
            upcoming = [
                {
                    "item_id":      str(c.get("item_id") or ""),
                    "title":        _truncate(str(c.get("title") or ""), 50),
                    "content_type": str(c.get("content_type") or ""),
                    "platform":     str(c.get("platform") or ""),
                    "planned_date": str(c.get("planned_date") or ""),
                    "status":       str(c.get("status") or ""),
                }
                for c in cal_items
                if str(c.get("status") or "") not in ("published", "archived")
            ][-6:]

            review_rows = [
                row for row in _safe_read_jsonl(pub_root / "ghostwritr_reviews.jsonl")
                if str(row.get("jarvis_status") or "").lower() == "pending"
            ]
            review_rows.sort(key=lambda row: str(row.get("ready_since") or ""))
            pending_reviews = [
                {
                    "review_id": str(review.get("review_id") or ""),
                    "title": str(review.get("title") or ""),
                    "slug": str(review.get("slug") or ""),
                    "stage_key": str(review.get("stage_key") or ""),
                    "stage_display": str(review.get("stage_display") or ""),
                    "content_preview": str(review.get("content_preview") or ""),
                    "word_count": _coerce_int(review.get("word_count")),
                    "ready_since": str(review.get("ready_since") or ""),
                    "approval_id": str(review.get("approval_id") or ""),
                }
                for review in review_rows[:6]
            ]

            launch_strategies_raw = _safe_read_json(pub_root / "launch_strategies.json", {})
            launch_strategies = launch_strategies_raw if isinstance(launch_strategies_raw, dict) else {}
            schedules = [
                row for row in _safe_read_jsonl(pub_root / "schedules.jsonl")
                if str(row.get("status") or "").lower() == "active"
            ]
            schedules.sort(key=lambda row: str(row.get("start_date") or ""), reverse=True)
            posts = _safe_read_jsonl(pub_root / "posts.jsonl")
            posts_by_project: dict[str, list[dict[str, Any]]] = {}
            for post in posts:
                project_id = str(post.get("project_id") or "").strip()
                if project_id:
                    posts_by_project.setdefault(project_id, []).append(post)

            active_schedule = schedules[0] if schedules else None
            launch_project_id = str(active_schedule.get("project_id") or "") if isinstance(active_schedule, dict) else ""
            strategy = launch_strategies.get(launch_project_id) if launch_project_id else None
            active_project_raw = project_lookup.get(launch_project_id)
            if active_project_raw is None and active_projects:
                active_project_raw = active_projects[0]

            active_project_id = str((active_project_raw or {}).get("project_id") or launch_project_id or "")
            launch_posts = posts_by_project.get(launch_project_id) if launch_project_id else []
            scheduled_posts = [post for post in launch_posts if str(post.get("scheduled_at") or "").strip()]
            draft_posts = [post for post in launch_posts if str(post.get("status") or "").lower() == "draft"]

            launch_days = None
            if isinstance(strategy, dict):
                launch_days = _iso_date_days_away(str(strategy.get("launch_date") or ""))
            if launch_days is None and isinstance(active_schedule, dict):
                launch_days = _iso_date_days_away(str(active_schedule.get("start_date") or ""))

            active_project = None
            if active_project_raw or strategy or active_schedule:
                active_project = {
                    "project_id": active_project_id,
                    "title": str(
                        (active_project_raw or {}).get("title")
                        or (strategy or {}).get("book_title")
                        or active_project_id
                    ),
                    "platform": str((active_project_raw or {}).get("platform") or ""),
                    "status": str((active_project_raw or {}).get("status") or (active_schedule or {}).get("status") or ""),
                    "phase": str((active_schedule or {}).get("phase") or "pre_launch"),
                    "days_to_launch": launch_days,
                    "posts_scheduled": len(scheduled_posts),
                    "posts_pending_approval": len(draft_posts),
                    "launch_date": str((strategy or {}).get("launch_date") or ""),
                    "next_action": (
                        f"Review {len(pending_reviews)} pending draft" + ("s" if len(pending_reviews) != 1 else "")
                        if pending_reviews else
                        f"Approve {len(draft_posts)} launch post" + ("s" if len(draft_posts) != 1 else "")
                        if draft_posts else
                        f"Prepare {str((active_schedule or {}).get('phase') or 'launch').replace('_', ' ')} queue"
                        if active_schedule else
                        "Keep the publishing pipeline moving"
                    ),
                }

            action_items: list[dict[str, Any]] = []
            if pending_reviews:
                top_review = pending_reviews[0]
                action_items.append({
                    "title": f"Review {top_review['title']}",
                    "detail": f"{top_review['stage_display'] or top_review['stage_key']} is ready for approval.",
                    "kind": "review",
                    "priority": "high",
                })
            if active_project and active_project.get("posts_pending_approval"):
                posts_pending_approval = int(active_project["posts_pending_approval"])
                action_items.append({
                    "title": f"Approve {posts_pending_approval} launch post" + ("s" if posts_pending_approval != 1 else ""),
                    "detail": f"{active_project.get('title') or 'Active launch'} has social copy waiting in the queue.",
                    "kind": "launch",
                    "priority": "medium",
                })
            if upcoming:
                next_upcoming = upcoming[0]
                action_items.append({
                    "title": f"Prepare {next_upcoming['title']}",
                    "detail": f"{next_upcoming['platform'] or 'Publishing'} is scheduled for {next_upcoming['planned_date'] or 'soon'}.",
                    "kind": "calendar",
                    "priority": "medium",
                })

            return _ok({
                "projects":        projects,
                "revenue_summary": revenue_summary,
                "upcoming":        upcoming,
                "pending_reviews": pending_reviews,
                "pending_reviews_count": len(pending_reviews),
                "launch_control": active_project,
                "action_items": action_items,
                "updated_at":      _ts(),
            })
        except Exception as exc:
            logger.exception("apple_publishing failed: %s", exc)
            return _ok({
                "projects": [],
                "revenue_summary": {"monthly_estimate": 0.0, "stream_count": 0, "streams": []},
                "upcoming": [],
                "pending_reviews": [],
                "pending_reviews_count": 0,
                "launch_control": None,
                "action_items": [],
                "updated_at": _ts(),
            })

    @app.post("/api/apple/publishing/reviews/{review_id}/approve")
    async def apple_publishing_approve_review(review_id: str):
        pub_root = Path.home() / ".jarvis" / "publishing"
        reviews_path = pub_root / "ghostwritr_reviews.jsonl"
        rows = _safe_read_jsonl(reviews_path)
        updated = False
        now = _ts()
        for row in rows:
            if str(row.get("review_id") or "") == review_id:
                row["jarvis_status"] = "approved"
                row["feedback"] = str(row.get("feedback") or "")
                row["reviewed_at"] = now
                updated = True
                break
        if not updated:
            raise HTTPException(status_code=404, detail=f"Review {review_id} not found")
        reviews_path.write_text(
            "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + ("\n" if rows else ""),
            encoding="utf-8",
        )
        return _ok({"status": "approved", "review_id": review_id})

    @app.post("/api/apple/publishing/reviews/{review_id}/revise")
    async def apple_publishing_revise_review(review_id: str, payload: dict[str, Any]):
        pub_root = Path.home() / ".jarvis" / "publishing"
        reviews_path = pub_root / "ghostwritr_reviews.jsonl"
        rows = _safe_read_jsonl(reviews_path)
        feedback = str(payload.get("feedback") or "").strip() or "Needs revision from JarvisPhone."
        updated = False
        now = _ts()
        for row in rows:
            if str(row.get("review_id") or "") == review_id:
                row["jarvis_status"] = "needs_revision"
                row["feedback"] = feedback
                row["reviewed_at"] = now
                updated = True
                break
        if not updated:
            raise HTTPException(status_code=404, detail=f"Review {review_id} not found")
        reviews_path.write_text(
            "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + ("\n" if rows else ""),
            encoding="utf-8",
        )
        return _ok({"status": "needs_revision", "review_id": review_id, "feedback": feedback})

    # ── Huddle ────────────────────────────────────────────────────────────────

    @app.get("/api/apple/huddle")
    async def apple_huddle():
        """Agent standup huddle for the iPhone Huddle tab."""
        try:
            from .standup import collect_all_standups
            from dataclasses import asdict
            huddle = await asyncio.to_thread(
                collect_all_standups,
                None,
                runtime,
                False,
            )
            h = asdict(huddle)
            # Flatten to phone-friendly shape
            reports = []
            for r in (h.get("agent_reports") or []):
                reports.append({
                    "agent_id":   str(r.get("agent_id") or ""),
                    "agent_name": str(r.get("agent_name") or r.get("agent_id") or ""),
                    "domain":     str(r.get("domain") or ""),
                    "status":     str(r.get("status") or "ok"),
                    "summary":    _truncate(str(r.get("summary") or r.get("headline") or ""), 80),
                    "blockers":   [str(b)[:60] for b in (r.get("blockers") or [])[:2]],
                    "yesterday":  _truncate(str(r.get("yesterday") or ""), 140),
                    "today":      _truncate(str(r.get("today") or ""), 140),
                    "needs":      _truncate(str(r.get("needs") or ""), 140),
                    "highlights": [str(item)[:50] for item in (r.get("highlights") or [])[:4]],
                    "source":     str(r.get("source") or "generated"),
                    "active_work_count": int(r.get("active_work_count") or 0),
                })
            approvals = []
            for item in (h.get("approvals_needed") or []):
                approvals.append({
                    "work_id": str(item.get("work_id") or ""),
                    "title": _truncate(str(item.get("title") or "Untitled"), 80),
                    "agent": str(item.get("agent") or item.get("agent_id") or ""),
                    "proposal": _truncate(str(item.get("proposal") or item.get("idea") or ""), 160),
                    "domain": str(item.get("domain") or ""),
                })
            return _ok({
                "reports": reports[:15],
                "blockers": [str(b)[:80] for b in (h.get("blockers") or [])[:5]],
                "highlights": [str(hl)[:80] for hl in (h.get("highlights") or [])[:5]],
                "approvals": approvals[:8],
                "approvals_count": int(len(h.get("approvals_needed") or [])),
                "total_active_work": int(h.get("total_active_work") or 0),
                "updated_at": _ts(),
            })
        except Exception as exc:
            logger.exception("apple_huddle failed: %s", exc)
            return _ok({
                "reports": [],
                "blockers": [],
                "highlights": [],
                "approvals": [],
                "approvals_count": 0,
                "total_active_work": 0,
                "updated_at": _ts(),
            })

    # ── Forge 3-D models ──────────────────────────────────────────────────────

    _FORGE_DB = Path("data/forge/models.jsonl")

    @app.get("/api/apple/forge")
    async def apple_forge():
        """Return saved photogrammetry model records for the Forge tab."""
        try:
            records = []
            if _FORGE_DB.exists():
                for line in _FORGE_DB.read_text().splitlines():
                    line = line.strip()
                    if line:
                        try:
                            records.append(json.loads(line))
                        except Exception:
                            pass
            return _ok({"models": list(reversed(records[-20:]))})
        except Exception as exc:
            logger.exception("apple_forge failed: %s", exc)
            return _ok({"models": []})

    @app.post("/api/apple/forge/submit")
    async def apple_forge_submit(payload: dict):
        """Receive photos from the phone and queue a photogrammetry job."""
        try:
            import base64
            job_id   = str(uuid.uuid4())
            name     = str(payload.get("name") or "Model")
            photos   = payload.get("photos") or []
            job_dir  = Path(f"data/forge/jobs/{job_id}")
            job_dir.mkdir(parents=True, exist_ok=True)

            # Write photos to disk
            saved = 0
            for photo in photos:
                try:
                    data     = base64.b64decode(photo["data"])
                    filename = photo.get("filename") or f"photo_{photo.get('index',saved):04d}.jpg"
                    (job_dir / filename).write_bytes(data)
                    saved += 1
                except Exception:
                    pass

            # Write job manifest
            manifest = {
                "job_id":      job_id,
                "name":        name,
                "photo_count": saved,
                "status":      "queued",
                "created_at":  _ts(),
                "job_dir":     str(job_dir),
            }
            (job_dir / "manifest.json").write_text(json.dumps(manifest))

            # Append to global job queue
            queue_path = Path("data/forge/queue.jsonl")
            queue_path.parent.mkdir(parents=True, exist_ok=True)
            with queue_path.open("a") as f:
                f.write(json.dumps(manifest) + "\n")

            return _ok({"queued": True, "job_id": job_id, "photo_count": saved})
        except Exception as exc:
            logger.exception("apple_forge_submit failed: %s", exc)
            return _ok({"queued": False, "job_id": "", "reason": str(exc)})

    @app.post("/api/apple/forge/save")
    async def apple_forge_save(payload: dict):
        """Persist a completed forge model record from the phone."""
        try:
            record = {
                "id":          str(payload.get("id") or uuid.uuid4()),
                "name":        str(payload.get("name") or "Model"),
                "photo_count": int(payload.get("photo_count") or payload.get("photoCount") or 0),
                "created_at":  str(payload.get("created_at") or payload.get("createdAt") or _ts()),
                "usdz_path":   payload.get("usdz_path") or payload.get("usdzPath"),
                "saved_at":    _ts(),
            }
            _FORGE_DB.parent.mkdir(parents=True, exist_ok=True)
            with _FORGE_DB.open("a") as f:
                f.write(json.dumps(record) + "\n")
            return _ok({"saved": True, "id": record["id"]})
        except Exception as exc:
            return _ok({"saved": False, "reason": str(exc)})


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _normalise_briefing_item(raw: dict) -> dict:
    """Convert any internal feed-item shape → Swift BriefingItem fields."""
    kind = str(raw.get("kind") or raw.get("priority") or "normal").lower()
    priority = "high" if kind in ("priority", "high", "urgent", "critical") else "normal"
    sub = raw.get("sub") or raw.get("body") or None
    if isinstance(sub, list):
        sub = "\n".join(str(item) for item in sub if str(item).strip()) or None
    elif sub is not None:
        sub = str(sub)
    return {
        "id":        str(raw.get("id") or uuid.uuid4()),
        "text":      str(raw.get("text") or raw.get("title") or ""),
        "sub":       sub,
        "priority":  priority,
        "agent":     str(raw.get("agent") or raw.get("source") or "JARVIS"),
        "timestamp": str(raw.get("timestamp") or raw.get("ts") or _ts()),
    }


def _normalise_working_item(raw: dict) -> dict:
    """Convert any internal working-item shape → Swift WorkingItem fields."""
    return {
        "id":        str(raw.get("id") or uuid.uuid4()),
        "agent":     str(raw.get("agent") or raw.get("source") or raw.get("title") or "JARVIS"),
        "action":    str(raw.get("action") or raw.get("body") or raw.get("text") or "Working…"),
        "timestamp": str(raw.get("timestamp") or raw.get("ts") or _ts()),
    }


def _normalise_needs_item(raw: dict) -> dict:
    """Convert any internal needs-item shape → Swift NeedsItem fields."""
    risk = str(raw.get("risk") or raw.get("risk_tier") or raw.get("kind") or "medium").lower()
    if risk not in ("low", "medium", "high"):
        risk = "medium"
    return {
        "id":         str(raw.get("id") or raw.get("request_id") or uuid.uuid4()),
        "text":       _truncate(str(raw.get("text") or raw.get("title") or ""), 80),
        "agent":      str(raw.get("agent") or raw.get("requester") or "JARVIS"),
        "risk":       risk,
        "expires_in": raw.get("expires_in"),
    }


def _normalise_drift_item(raw: dict) -> dict:
    """Convert any internal drift-item shape → Swift DriftItem fields."""
    kind = str(raw.get("severity") or raw.get("kind") or "gentle").lower()
    severity = kind if kind in ("gentle", "moderate", "significant") else "gentle"
    return {
        "id":       str(raw.get("id") or uuid.uuid4()),
        "text":     str(raw.get("text") or raw.get("title") or ""),
        "severity": severity,
        "agent":    str(raw.get("agent") or raw.get("source") or "JARVIS"),
    }


def _is_live_apple_item(raw: dict, *, zone: str) -> bool:
    """Keep mock/demo/seeded material out of the iPhone app's truth surfaces."""
    source = str(raw.get("source") or raw.get("source_type") or "").strip().lower()
    if source in {"mock", "fallback", "demo", "sample", "fixture", "test"}:
        return False

    agent = str(raw.get("agent") or raw.get("source") or raw.get("requester") or "").strip().lower()
    text = " ".join(
        str(raw.get(key) or "")
        for key in ("text", "title", "body", "summary")
    ).strip().lower()

    if "partly cloudy, 72.0" in text and agent == "storm":
        return False
    if "no activity logged yet" in text:
        return False
    if "last contact: never" in text:
        return False

    seeded_growth_agents = {"agatha", "gamora", "thor", "spider-man", "spiderman"}
    evidence_keys = {
        "id",
        "request_id",
        "source_signal_id",
        "work_id",
        "drift_id",
        "approval_id",
        "created_at",
        "completed_at",
    }
    if zone in {"briefing", "drift"} and agent in seeded_growth_agents:
        has_evidence = any(str(raw.get(key) or "").strip() for key in evidence_keys)
        if not has_evidence:
            return False

    return True


def _truncate(text: str, max_len: int) -> str:
    return text if len(text) <= max_len else text[: max_len - 1] + "…"


def _mock_home_state() -> dict:
    """Stub home state returned when HomeAssistant is not configured."""
    return {
        "present_members": [],
        "doors": {"front": "locked", "garage": "closed"},
        "temperature": {"inside": 70.0, "target": 72.0, "mode": "cool"},
        "lights_on": [],
        "alerts": [],
        "source": "mock",
    }
