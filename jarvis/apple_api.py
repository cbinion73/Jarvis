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
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast
from urllib.parse import quote

from fastapi import FastAPI, HTTPException

from .audit import AuditLog, ProgressFocusStore, RecoveryActionStore
from .chronicle_reviews import ChronicleReviewStore
from .health_checkins import HealthCheckInStore
from .nav_bridge import NavBridge, haversine, min_distance_to_route, sample_route_points
from .persistence import append_jsonl as persistence_append_jsonl, atomic_write_json
from .publish_history import PublishHistoryStore
from .recovery_cases import RecoveryCaseStore
from .settings import LOCATION_SETTINGS_PATH, VoiceSettingsStore

logger = logging.getLogger(__name__)
_NAVIGATION_STATE_PATH = Path("data/settings/navigation_state.json")
_NAVIGATION_STATE_LOG_PATH = _NAVIGATION_STATE_PATH.with_name("navigation_state_log.jsonl")
_EVENT_LOG_PATH = Path("data/state/event_log.jsonl")
_NOTIFICATION_CENTER_PATH = Path("data/state/notification_center.json")
_NOTIFICATION_CENTER_LOG_PATH = _NOTIFICATION_CENTER_PATH.with_name("notification_center_log.jsonl")
_STEWARDSHIP_REVIEW_QUEUE_PATH = Path("data/state/stewardship_reviews.json")
_STEWARDSHIP_REVIEW_QUEUE_LOG_PATH = _STEWARDSHIP_REVIEW_QUEUE_PATH.with_name("stewardship_reviews_log.jsonl")
_SIGNAL_RESOLUTIONS_PATH = Path("data/state/signal_resolutions.json")
_SIGNAL_RESOLUTIONS_LOG_PATH = _SIGNAL_RESOLUTIONS_PATH.with_name("signal_resolutions_log.jsonl")
_FOCUS_STATE_PATH = Path("data/apple/focus_state.json")
_FOCUS_STATE_LOG_PATH = _FOCUS_STATE_PATH.with_name("focus_state_log.jsonl")
_APPLE_REMINDERS_PATH = Path("data/apple/reminders.json")
_APPLE_REMINDERS_LOG_PATH = _APPLE_REMINDERS_PATH.with_name("reminders_log.jsonl")
_APPLE_CALENDAR_PATH = Path("data/apple/calendar_events.json")
_APPLE_CALENDAR_LOG_PATH = _APPLE_CALENDAR_PATH.with_name("calendar_events_log.jsonl")
_APPLE_NOW_PLAYING_PATH = Path("data/apple/now_playing.json")
_APPLE_NOW_PLAYING_LOG_PATH = _APPLE_NOW_PLAYING_PATH.with_name("now_playing_log.jsonl")
_CHRONICLE_PRAYER_ACTIVITY_PATH = Path.home() / ".jarvis" / "chronicle" / "prayer_activity.json"
_CHRONICLE_PRAYER_ACTIVITY_LOG_PATH = _CHRONICLE_PRAYER_ACTIVITY_PATH.with_name("prayer_activity_log.jsonl")
_CHRONICLE_ANSWERED_PRAYERS_PATH = Path.home() / ".jarvis" / "chronicle" / "answered_prayers.jsonl"
_ACTIVITY_AUDIT_ROOT = Path("data/logs")
_CARPLAY_OPS_FOCUS_CANDIDATES = [
    {"module": "Progress", "route": "/progress-center", "label": "Progress Focus"},
    {"module": "Recovery", "route": "/recovery-center", "label": "Recovery Loop"},
    {"module": "Approval Queue", "route": "/approval-queue", "label": "Approvals"},
    {"module": "Mission Board", "route": "/mission-board", "label": "Mission Pressure"},
    {"module": "Agent Ops", "route": "/agent-ops-center", "label": "Agent Operations"},
]
_CATALYST_OPS_FOCUS_CANDIDATES = [
    {"module": "Progress", "route": "/progress-center", "label": "Progress Studio"},
    {"module": "Recovery", "route": "/recovery-center", "label": "Recovery Studio"},
    {"module": "Approval Queue", "route": "/approval-queue", "label": "Approval Lane"},
    {"module": "Mission Board", "route": "/mission-board", "label": "Mission Board"},
    {"module": "Activity Feed", "route": "/activity-center", "label": "Activity Feed"},
    {"module": "Supervision", "route": "/supervision-snapshot", "label": "Supervision"},
]

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


def _save_apple_settings_profile(
    runtime,
    payload: dict[str, Any],
    *,
    actor_name: str = "chris",
) -> dict[str, Any]:
    from .user_profile import load_profile, save_profile

    actor_name = str(actor_name or "chris").strip() or "chris"
    actor_display = actor_name.capitalize() if actor_name.islower() else actor_name
    actor = runtime.get_actor(actor_display)
    subject_user_id = str(payload.get("subject_user_id") or actor.user_id or "chris").strip() or "chris"
    updates: dict[str, Any] = {}
    for key in ("notifications", "privacy", "dashboard"):
        value = payload.get(key)
        if isinstance(value, dict):
            updates[key] = value
    if not updates:
        raise ValueError("No settings profile updates were provided.")

    saved = save_profile(subject_user_id, updates)
    latest = load_profile(subject_user_id)
    notifications = latest.get("notifications") if isinstance(latest.get("notifications"), dict) else {}
    privacy = latest.get("privacy") if isinstance(latest.get("privacy"), dict) else {}
    detail = (
        f"Notifications: approvals {'on' if bool(notifications.get('approvals')) else 'off'}, "
        f"health {'on' if bool(notifications.get('health_alerts')) else 'off'}; "
        f"privacy: chronicle {'private' if bool(privacy.get('private_chronicle')) else 'shareable'}."
    )
    if hasattr(runtime, "_invalidate_snapshot_cache"):
        try:
            runtime._invalidate_snapshot_cache(
                actor_display,
                surfaces=("dashboard", "today_board", "cognitive", "shell_state", "proactive_state"),
            )
        except Exception:
            pass
    AuditLog(_ACTIVITY_AUDIT_ROOT).log_event(
        "operator-action",
        {
            "actor": actor_display,
            "domain": "settings",
            "action": "Save Apple Profile Defaults",
            "title": subject_user_id,
            "detail": f"Apple Systems updated profile defaults for {subject_user_id}. {detail}",
            "why_now": "The iPhone Systems surface updated real Settings defaults and fed that posture back into shared continuity.",
            "result_summary": "Apple settings profile defaults saved.",
            "related_route": "/settings-center",
            "route_label": "Open Settings",
            "related_kind": "profile-settings",
            "related_label": subject_user_id,
            "succeeded": True,
            "source_kind": "operator-action",
        },
    )
    focus = ProgressFocusStore(_ACTIVITY_AUDIT_ROOT).save_focus(
        module="Settings",
        reason=f"Apple Systems updated profile defaults for {subject_user_id}.",
        route="/settings-center",
        actor=actor_name,
    )
    return {
        "message": "Profile defaults updated.",
        "settings": {
            "subject_user_id": subject_user_id,
            "notifications": dict(latest.get("notifications") or {}),
            "privacy": dict(latest.get("privacy") or {}),
            "dashboard": dict(latest.get("dashboard") or {}),
            "updated_at": str(saved.get("updated_at") or latest.get("updated_at") or ""),
        },
        "focus": focus,
    }


def _save_apple_settings_account(
    runtime,
    account_id: str,
    payload: dict[str, Any],
    *,
    actor_name: str = "chris",
) -> dict[str, Any]:
    actor_name = str(actor_name or "chris").strip() or "chris"
    updates = {
        key: payload.get(key)
        for key in ("label", "login_hint", "status", "notes")
        if key in payload
    }
    if not updates:
        raise ValueError("No account updates were provided.")
    try:
        result = runtime.update_personal_account(account_id, updates)
    except KeyError as exc:
        raise ValueError("Account not found.") from exc
    account = dict(result.get("account") or {})
    label = str(account.get("label") or account_id).strip() or account_id
    provider = str(account.get("provider") or "account").strip() or "account"
    status = str(account.get("status") or "planned").strip() or "planned"
    login_hint = str(account.get("login_hint") or "").strip()
    detail = f"{provider.title()} account saved as {status.replace('_', ' ')}."
    if login_hint:
        detail += f" Login hint: {login_hint}."
    _record_operator_action(
        actor=actor_name,
        domain="settings",
        action="Save Apple Account Controls",
        detail=f"Apple Systems updated {label}. {detail}",
        why_now="The iPhone Systems surface updated live account posture and fed that continuity back into Settings.",
        result_summary=f"Apple account controls saved for {label}.",
        route="/settings-center",
        route_label="Open Settings",
        related_kind="settings-account",
        related_label=label,
        succeeded=True,
    )
    focus = ProgressFocusStore(_ACTIVITY_AUDIT_ROOT).save_focus(
        module="Settings",
        reason=f"Apple Systems updated the {label} account.",
        route="/settings-center",
        actor=actor_name,
    )
    return {
        "message": result.get("message") or f"Updated account '{label}'.",
        "account": {
            "id": str(account.get("account_id") or account_id),
            "label": label,
            "provider": provider,
            "status": status,
            "login_hint": login_hint,
            "service_scope": str(account.get("service_scope") or "mail_calendar"),
            "notes": str(account.get("notes") or ""),
            "connection_status": str(account.get("connection") or status),
            "detail": str(account.get("notes") or account.get("service_scope") or login_hint or "Awaiting configuration"),
        },
        "focus": focus,
    }


def _save_apple_settings_connector(
    runtime,
    account_id: str,
    payload: dict[str, Any],
    *,
    actor_name: str = "chris",
) -> dict[str, Any]:
    actor_name = str(actor_name or "chris").strip() or "chris"
    updates = {
        key: payload.get(key)
        for key in ("service_scope", "status", "notes")
        if key in payload
    }
    if not updates:
        raise ValueError("No connector updates were provided.")
    try:
        result = runtime.update_personal_account(account_id, updates)
    except KeyError as exc:
        raise ValueError("Account not found.") from exc
    account = dict(result.get("account") or {})
    label = str(account.get("label") or account_id).strip() or account_id
    provider = str(account.get("provider") or "account").strip() or "account"
    service_scope = str(account.get("service_scope") or "mail_calendar").strip() or "mail_calendar"
    status = str(account.get("status") or "planned").strip() or "planned"
    notes = str(account.get("notes") or "").strip()
    detail = f"{provider.title()} connector saved as {service_scope.replace('_', ' / ')} with {status.replace('_', ' ')} posture."
    if notes:
        detail += f" {notes}"
    _record_operator_action(
        actor=actor_name,
        domain="settings",
        action="Save Apple Connector Controls",
        detail=f"Apple Systems updated {label}. {detail}",
        why_now="The iPhone Systems surface refined live connector scope and stabilization posture from native controls.",
        result_summary=f"Apple connector controls saved for {label}.",
        route="/settings-center",
        route_label="Open Settings",
        related_kind="settings-connector",
        related_label=label,
        succeeded=True,
    )
    focus = ProgressFocusStore(_ACTIVITY_AUDIT_ROOT).save_focus(
        module="Settings",
        reason=f"Apple Systems updated connector controls for {label}.",
        route="/settings-center",
        actor=actor_name,
    )
    return {
        "message": result.get("message") or f"Updated connector controls for '{label}'.",
        "account": {
            "id": str(account.get("account_id") or account_id),
            "label": label,
            "provider": provider,
            "status": status,
            "login_hint": str(account.get("login_hint") or ""),
            "service_scope": service_scope,
            "notes": notes,
            "connection_status": str(account.get("connection") or status),
            "detail": notes or service_scope or "Awaiting configuration",
        },
        "focus": focus,
    }


def _save_apple_settings_family_member(
    runtime,
    user_id: str,
    payload: dict[str, Any],
    *,
    actor_name: str = "chris",
) -> dict[str, Any]:
    actor_name = str(actor_name or "chris").strip() or "chris"
    updates = {
        "user_id": user_id,
        **{
            key: payload.get(key)
            for key in ("role", "permissions", "trust_level", "preferred_tone", "privacy_boundary", "notes")
            if key in payload
        },
    }
    if len(updates) <= 1:
        raise ValueError("No family identity updates were provided.")
    try:
        result = runtime.save_identity_member(updates)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc
    member = dict(result.get("member") or {})
    label = str(member.get("display_name") or user_id).strip() or user_id
    role = str(member.get("role") or "member").strip() or "member"
    permissions = str(member.get("permissions") or "member").strip() or "member"
    trust_level = str(member.get("trust_level") or "standard").strip() or "standard"
    preferred_tone = str(member.get("preferred_tone") or "").strip()
    detail = f"{label} is now staged as {role.replace('_', ' ')} with {permissions.replace('_', ' ')} permissions and {trust_level.replace('_', ' ')} trust."
    if preferred_tone:
        detail += f" Tone: {preferred_tone}."
    notes = str(member.get("notes") or "").strip()
    if notes:
        detail += f" {notes}"
    _record_operator_action(
        actor=actor_name,
        domain="settings",
        action="Save Apple Family Identity",
        detail=f"Apple Systems updated {label}. {detail}",
        why_now="The iPhone Systems surface refined live family identity posture so role, tone, and permissions stay aligned across JARVIS.",
        result_summary=f"Apple family identity saved for {label}.",
        route="/settings-center",
        route_label="Open Settings",
        related_kind="settings-family-identity",
        related_label=label,
        succeeded=True,
    )
    focus = ProgressFocusStore(_ACTIVITY_AUDIT_ROOT).save_focus(
        module="Settings",
        reason=f"Apple Systems updated family identity for {label}.",
        route="/settings-center",
        actor=actor_name,
    )
    return {
        "message": f"Saved family identity for {label}.",
        "member": {
            "id": str(member.get("user_id") or user_id),
            "display_name": label,
            "role": role,
            "permissions": permissions,
            "trust_level": trust_level,
            "preferred_tone": preferred_tone,
            "privacy_boundary": str(member.get("privacy_boundary") or "personal"),
            "notes": notes,
            "device_count": int(len(member.get("device_ids") or [])),
            "online_device_count": int(member.get("online_device_count") or 0),
            "status": str(member.get("status") or ("Active" if member.get("active", True) else "Inactive")),
        },
        "focus": focus,
    }


def _disconnect_apple_settings_account(
    runtime,
    account_id: str,
    *,
    actor_name: str = "chris",
) -> dict[str, Any]:
    actor_name = str(actor_name or "chris").strip() or "chris"
    result = runtime.disconnect_account(account_id)
    if not bool(result.get("ok", False)):
        raise ValueError(str(result.get("message") or "Account disconnect failed."))
    account = dict(result.get("account") or {})
    label = str(account.get("label") or account_id).strip() or account_id
    provider = str(account.get("provider") or "account").strip() or "account"
    _record_operator_action(
        actor=actor_name,
        domain="settings",
        action="Disconnect Apple Account",
        detail=f"Apple Systems disconnected the {provider.title()} account {label} and returned it to planned posture.",
        why_now="The iPhone Systems surface needed to pause or reset a connector from native controls.",
        result_summary=f"Apple disconnected {label}.",
        route="/settings-center",
        route_label="Open Settings",
        related_kind="settings-account",
        related_label=label,
        succeeded=True,
    )
    focus = ProgressFocusStore(_ACTIVITY_AUDIT_ROOT).save_focus(
        module="Settings",
        reason=f"Apple Systems disconnected the {label} account.",
        route="/settings-center",
        actor=actor_name,
    )
    return {
        "message": result.get("message") or f"Disconnected {label}.",
        "account": {
            "id": str(account.get("account_id") or account_id),
            "label": label,
            "provider": provider,
            "status": str(account.get("status") or "planned"),
            "login_hint": str(account.get("login_hint") or ""),
            "service_scope": str(account.get("service_scope") or "mail_calendar"),
            "notes": str(account.get("notes") or ""),
            "connection_status": str(account.get("connection") or "planned"),
            "detail": str(account.get("notes") or account.get("service_scope") or "Disconnected"),
        },
        "focus": focus,
    }


def _record_operator_action(
    *,
    actor: str,
    domain: str,
    action: str,
    detail: str,
    why_now: str,
    result_summary: str,
    route: str,
    route_label: str,
    related_kind: str = "",
    related_label: str = "",
    succeeded: bool = True,
) -> None:
    try:
        AuditLog(_ACTIVITY_AUDIT_ROOT).log_event(
            "operator-action",
            {
                "actor": actor,
                "domain": domain,
                "action": action,
                "detail": detail,
                "why_now": why_now,
                "result_summary": result_summary,
                "related_route": route,
                "route_label": route_label,
                "related_kind": related_kind,
                "related_label": related_label,
                "source_kind": "operator-action",
                "succeeded": bool(succeeded),
            },
        )
    except Exception as exc:
        logger.warning("apple_api operator action log failed: %s", exc)


def _build_carplay_ops_overview(runtime: Any) -> dict[str, Any]:
    from .command_center_index import _agent_ops_roster
    from .dossier import get_dossier_store
    from .ideas import list_ideas, stats as idea_stats
    from .party_mode import get_party_controller
    from .standup import collect_all_standups
    from .supervision_snapshot import build_supervision_snapshot

    focus_summary = ProgressFocusStore(_ACTIVITY_AUDIT_ROOT).summary(limit=5)
    recovery_cases = RecoveryCaseStore(_ACTIVITY_AUDIT_ROOT).list_cases()
    recovery_actions = RecoveryActionStore(_ACTIVITY_AUDIT_ROOT).summary(limit=4)
    approvals = list(runtime.list_pending_approvals() or [])
    activity = AuditLog(_ACTIVITY_AUDIT_ROOT).list_recent(limit=6)
    mission_snapshot = runtime.mission_control_snapshot("Chris")
    agent_snapshot = runtime.background_agent_status(recent_activity=activity)
    agent_roster = _agent_ops_roster()
    supervision_snapshot = build_supervision_snapshot()

    latest_focus = dict(focus_summary.get("latest") or {})
    active_missions = list(mission_snapshot.get("active_missions") or [])
    agent_statuses = list(agent_snapshot.get("statuses") or [])
    agent_items = [dict(item) for item in list(agent_roster.get("items") or []) if isinstance(item, dict)]
    supervision_items = [
        dict(item)
        for item in list(supervision_snapshot.get("attention_queue") or [])
        if isinstance(item, dict)
    ]
    try:
        huddle_packet = asdict(collect_all_standups(None, runtime, False))
    except Exception:
        huddle_packet = {}
    huddle_reports = [dict(item) for item in list(huddle_packet.get("agent_reports") or []) if isinstance(item, dict)]
    huddle_blockers = [str(item) for item in list(huddle_packet.get("blockers") or []) if str(item).strip()]
    huddle_approvals = [dict(item) for item in list(huddle_packet.get("approvals_needed") or []) if isinstance(item, dict)]
    try:
        party_status = get_party_controller(runtime).get_status()
    except Exception:
        party_status = {}
    try:
        ready_dossiers = [
            dossier
            for dossier in get_dossier_store().get_all()
            if str(getattr(dossier, "status", "") or "").strip().lower() != "presented"
        ]
    except Exception:
        ready_dossiers = []
    try:
        idea_summary = idea_stats()
        idea_items = [dict(item) for item in list_ideas() if isinstance(item, dict)]
    except Exception:
        idea_summary = {}
        idea_items = []
    chronicle_reviews = ChronicleReviewStore().review_summary(actor_id="chris", limit=4)
    chronicle_entries = _safe_read_jsonl(Path("data/chronicle/entries.jsonl"))
    chronicle_context = _chronicle_fallback_context(chronicle_entries, "chris")
    chronicle_latest = _chronicle_fallback_entries(chronicle_entries, "chris")
    idea_counts = dict(idea_summary.get("by_status") or {})
    queued_idea_count = int(idea_counts.get("queued") or 0) + int(idea_counts.get("captured") or 0)

    return {
        "generated_at": _ts(),
        "current_focus": {
            "module": str(latest_focus.get("module") or "Progress").strip() or "Progress",
            "reason": str(latest_focus.get("reason") or "No shared focus recorded yet.").strip() or "No shared focus recorded yet.",
            "route": str(latest_focus.get("route") or "/progress-center").strip() or "/progress-center",
            "saved_at": str(latest_focus.get("saved_at") or "").strip(),
        },
        "focus_candidates": deepcopy(_CARPLAY_OPS_FOCUS_CANDIDATES),
        "approvals": [
            {
                "request_id": str(item.get("request_id") or "").strip(),
                "title": str(item.get("request") or item.get("title") or "Approval").strip() or "Approval",
                "agent": str(item.get("agent") or item.get("agent_label") or "Unknown agent").strip() or "Unknown agent",
                "risk": str(item.get("risk_tier") or item.get("risk") or "medium").strip() or "medium",
                "action_class": str(item.get("action_class") or "").strip(),
            }
            for item in approvals[:5]
            if isinstance(item, dict)
        ],
        "recovery_cases": [
            {
                "case_id": str(item.get("case_id") or "").strip(),
                "title": str(item.get("title") or "Recovery case").strip() or "Recovery case",
                "status_label": str(item.get("status_label") or item.get("status") or "Open").strip() or "Open",
                "detail": str(item.get("detail") or "").strip(),
                "execution_count": int(item.get("execution_count", 0) or 0),
                "related_route": str(item.get("related_route") or "/recovery-center").strip() or "/recovery-center",
            }
            for item in recovery_cases[:5]
            if isinstance(item, dict)
        ],
        "agent_ops": [
            {
                "agent_id": str(item.get("agent_id") or "").strip(),
                "name": str(item.get("name") or item.get("agent_id") or "Agent").strip() or "Agent",
                "status": str(item.get("status") or "unknown").strip() or "unknown",
                "assignment": str(item.get("assignment") or "unassigned").strip() or "unassigned",
                "purpose": str(item.get("purpose") or "No purpose recorded.").strip() or "No purpose recorded.",
                "attention_reason": str(item.get("attention_reason") or "").strip(),
                "queue_action_label": "Queue Run",
            }
            for item in agent_items[:4]
            if str(item.get("agent_id") or "").strip()
        ],
        "supervision_items": [
            {
                "request_id": str(item.get("request_id") or "").strip(),
                "title": str(item.get("title") or "Supervision review").strip() or "Supervision review",
                "agent": str(item.get("agent_label") or item.get("actor_id") or "Unknown agent").strip() or "Unknown agent",
                "risk": str(item.get("risk_tier") or "medium").strip() or "medium",
                "detail": str(item.get("why_now") or "Needs supervision review.").strip() or "Needs supervision review.",
                "approve_label": "Approve",
                "reject_label": "Reject",
            }
            for item in supervision_items[:4]
            if str(item.get("request_id") or "").strip()
        ],
        "huddle_summary": {
            "reports_count": len(huddle_reports),
            "blockers_count": len(huddle_blockers),
            "approvals_count": len(huddle_approvals),
            "ready_dossier_count": len(ready_dossiers),
            "queued_idea_count": queued_idea_count,
            "party_mode_status": str(party_status.get("status") or "idle").strip() or "idle",
            "headline": (
                f"{len(huddle_reports)} standup reports, {len(huddle_approvals)} approvals, and {queued_idea_count} queued idea(s) are ready."
                if huddle_reports or huddle_approvals or queued_idea_count
                else "Huddle is steady. Wake agents or triage a queued idea from the in-car lane."
            ),
        },
        "huddle_ideas": [
            {
                "id": str(item.get("id") or "").strip(),
                "text": str(item.get("text") or "Idea").strip() or "Idea",
                "status": str(item.get("status") or "captured").strip() or "captured",
                "domain": str(item.get("domain") or "general").strip() or "general",
                "created_at": str(item.get("created_at") or "").strip(),
            }
            for item in idea_items[:4]
            if str(item.get("id") or "").strip()
        ],
        "chronicle_summary": {
            "latest_title": str((chronicle_latest[0] if chronicle_latest else {}).get("title") or "No Chronicle entry yet").strip() or "No Chronicle entry yet",
            "active_prayer_count": int((chronicle_context or {}).get("active_prayer_count") or 0),
            "study_title": str(((chronicle_context or {}).get("study") or {}).get("title") or ((chronicle_context or {}).get("study") or {}).get("passage") or "").strip(),
            "review_count": int(chronicle_reviews.get("count", 0) or 0),
            "headline": (
                f"{int(chronicle_reviews.get('count', 0) or 0)} Chronicle review thread(s) and {int((chronicle_context or {}).get('active_prayer_count') or 0)} active prayer(s) are ready."
                if int(chronicle_reviews.get("count", 0) or 0) or int((chronicle_context or {}).get("active_prayer_count") or 0)
                else "Chronicle memory lane is steady. Capture or review story threads from the phone."
            ),
        },
        "chronicle_reviews": [
            {
                "entry_id": str(item.get("entry_id") or "").strip(),
                "entry_title": str(item.get("entry_title") or "Chronicle entry").strip() or "Chronicle entry",
                "entry_type": str(item.get("entry_type") or "reflection").strip() or "reflection",
                "review_status": str(item.get("review_status") or "").strip(),
                "review_status_label": str(item.get("review_status_label") or "Review recorded").strip() or "Review recorded",
            }
            for item in list(chronicle_reviews.get("items") or [])[:4]
            if str(item.get("entry_id") or "").strip()
        ],
        "recent_activity": [
            {
                "title": str(item.get("action") or item.get("entry_type") or "Activity").strip() or "Activity",
                "detail": str(item.get("detail") or item.get("result_summary") or "").strip(),
                "route_label": str(item.get("route_label") or item.get("related_route") or "").strip(),
                "actor": str(item.get("actor") or "").strip(),
            }
            for item in activity[:6]
            if isinstance(item, dict)
        ],
        "mission_summary": {
            "active_count": len(active_missions),
            "pending_approvals": len(list(mission_snapshot.get("pending_approvals") or [])),
            "headline": str(mission_snapshot.get("summary", {}).get("headline") or "").strip(),
        },
        "agent_summary": {
            "awake_count": len([item for item in agent_statuses if str(item.get("status") or "").strip().lower() == "awake"]),
            "blocked_count": len([item for item in agent_statuses if str(item.get("status") or "").strip().lower() == "blocked"]),
            "total_count": len(agent_statuses),
        },
        "counts": {
            "approval_count": len(approvals),
            "recovery_case_count": len(recovery_cases),
            "recent_activity_count": len(activity),
            "recovery_action_count": int(recovery_actions.get("count", 0) or 0),
            "agent_ops_count": len(agent_items),
            "supervision_count": len(supervision_items),
            "huddle_idea_count": len(idea_items),
            "chronicle_review_count": int(chronicle_reviews.get("count", 0) or 0),
        },
    }


def _save_carplay_ops_focus(*, module: str, route: str, actor: str, reason: str) -> dict[str, Any]:
    entry = ProgressFocusStore(_ACTIVITY_AUDIT_ROOT).save_focus(
        module=module,
        reason=reason,
        route=route,
        actor=actor,
    )
    _record_operator_action(
        actor=actor,
        domain="carplay",
        action="Set CarPlay Ops Focus",
        detail=f"CarPlay promoted {module} into the shared progress focus lane.",
        why_now="A CarPlay operational selection raised the next Level 3 focus directly from the dashboard.",
        result_summary=f"Shared progress focus now points at {module}.",
        route=route,
        route_label=f"Open {module}",
        related_kind="progress-focus",
        related_label=module,
        succeeded=True,
    )
    return entry


def _queue_carplay_agent_run(*, agent_id: str, actor: str) -> dict[str, Any]:
    from .scheduler import get_scheduler

    scheduler = get_scheduler()
    if scheduler is None:
        raise RuntimeError("Scheduler not initialised")
    item = scheduler.force_run(agent_id)
    if item is None:
        raise KeyError("Unknown agent")

    detail = f"CarPlay queued agent {agent_id} from the ops lane."
    _record_operator_action(
        actor=actor,
        domain="carplay",
        action="Queue CarPlay Agent Run",
        detail=detail,
        why_now="A CarPlay operational selection elevated an agent run without leaving the in-car surface.",
        result_summary=f"{agent_id} is queued for execution.",
        route="/agent-ops-center",
        route_label="Open Agent Ops",
        related_kind="agent-run",
        related_label=agent_id,
        succeeded=True,
    )
    focus = ProgressFocusStore(_ACTIVITY_AUDIT_ROOT).save_focus(
        module="Agent Ops",
        reason=detail,
        route="/agent-ops-center",
        actor=actor,
    )
    return {
        "status": "queued",
        "agent_id": agent_id,
        "item_id": str(getattr(item, "item_id", "") or ""),
        "focus": focus,
    }


def _resolve_carplay_supervision_item(
    runtime: Any,
    *,
    request_id: str,
    action: str,
    actor: str,
    reason: str = "",
) -> dict[str, Any]:
    action_key = str(action or "").strip().lower()
    if action_key not in {"approve", "reject"}:
        raise ValueError("Unsupported supervision action.")

    from .supervision_snapshot import build_supervision_snapshot

    supervision_snapshot = build_supervision_snapshot()
    attention_items = [
        dict(item)
        for item in list(supervision_snapshot.get("attention_queue") or [])
        if isinstance(item, dict)
    ]
    target = next((item for item in attention_items if str(item.get("request_id") or "").strip() == request_id.strip()), None)
    status = "approved" if action_key == "approve" else "rejected"
    updated = runtime.approval_store.update_status(request_id, status)
    if updated is None:
        raise KeyError("Supervision request not found.")

    title = str((target or {}).get("title") or updated.get("request") or updated.get("title") or request_id).strip() or request_id
    detail = reason or (
        f"CarPlay approved {title} from the supervision lane."
        if action_key == "approve"
        else f"CarPlay rejected {title} from the supervision lane."
    )
    _record_operator_action(
        actor=actor,
        domain="carplay",
        action="Approve CarPlay Supervision Review" if action_key == "approve" else "Reject CarPlay Supervision Review",
        detail=detail,
        why_now="The CarPlay supervision lane resolved a bounded-autonomy review item in the vehicle surface.",
        result_summary=f"Supervision review moved to {status}.",
        route="/supervision-snapshot",
        route_label="Open Supervision",
        related_kind="supervision-review",
        related_label=title,
        succeeded=True,
    )
    focus = ProgressFocusStore(_ACTIVITY_AUDIT_ROOT).save_focus(
        module="Supervision",
        reason=detail,
        route="/supervision-snapshot",
        actor=actor,
    )
    return {
        "status": status,
        "request_id": request_id,
        "title": title,
        "focus": focus,
        "request": updated,
    }


def _record_carplay_huddle_focus(
    *,
    actor: str,
    action: str,
    detail: str,
    why_now: str,
    result_summary: str,
    related_kind: str,
    related_label: str,
) -> dict[str, Any]:
    _record_operator_action(
        actor=actor,
        domain="carplay",
        action=action,
        detail=detail,
        why_now=why_now,
        result_summary=result_summary,
        route="/huddle-center",
        route_label="Open Huddle",
        related_kind=related_kind,
        related_label=related_label,
        succeeded=True,
    )
    return ProgressFocusStore(_ACTIVITY_AUDIT_ROOT).save_focus(
        module="Huddle",
        reason=detail,
        route="/huddle-center",
        actor=actor,
    )


def _start_carplay_huddle_party_mode(runtime: Any, *, actor: str) -> dict[str, Any]:
    from .party_mode import get_party_controller

    controller = get_party_controller(runtime)
    status = controller.get_status()
    if str(status.get("status") or "").strip().lower() == "running":
        focus = _record_carplay_huddle_focus(
            actor=actor,
            action="Start CarPlay Huddle Party Mode",
            detail="CarPlay confirmed the overnight research lane is already running.",
            why_now="The in-car Huddle lane checked the overnight agents before creating duplicate work.",
            result_summary="Party mode was already running from CarPlay.",
            related_kind="party-mode",
            related_label="Overnight Orchestration",
        )
        return {"status": "already_running", "focus": focus}

    controller.start(True)
    focus = _record_carplay_huddle_focus(
        actor=actor,
        action="Start CarPlay Huddle Party Mode",
        detail="CarPlay launched the overnight research cycle from the Huddle lane.",
        why_now="The in-car Huddle lane escalated the overnight research loop without leaving the vehicle surface.",
        result_summary="Party mode started from CarPlay.",
        related_kind="party-mode",
        related_label="Overnight Orchestration",
    )
    return {"status": "started", "focus": focus}


def _queue_carplay_huddle_idea(*, idea_id: str, actor: str) -> dict[str, Any]:
    from .ideas import queue_idea

    idea = queue_idea(idea_id)
    if idea is None:
        raise KeyError("Idea not found.")
    focus = _record_carplay_huddle_focus(
        actor=actor,
        action="Queue CarPlay Huddle Idea",
        detail=f"CarPlay queued {str(idea.get('text') or idea_id).strip() or idea_id} for background research.",
        why_now="The in-car Huddle lane promoted a captured idea into the queued research stack.",
        result_summary="Huddle idea queued from CarPlay.",
        related_kind="idea",
        related_label=str(idea.get("text") or idea.get("id") or idea_id),
    )
    return {"status": "queued", "idea": idea, "focus": focus}


def _pass_carplay_huddle_idea(*, idea_id: str, actor: str) -> dict[str, Any]:
    from .ideas import pass_idea

    idea = pass_idea(idea_id)
    if idea is None:
        raise KeyError("Idea not found.")
    focus = _record_carplay_huddle_focus(
        actor=actor,
        action="Pass CarPlay Huddle Idea",
        detail=f"CarPlay passed on {str(idea.get('text') or idea_id).strip() or idea_id} after review.",
        why_now="The in-car Huddle lane intentionally dismissed a low-leverage idea instead of leaving it stalled.",
        result_summary="Huddle idea passed from CarPlay.",
        related_kind="idea",
        related_label=str(idea.get("text") or idea.get("id") or idea_id),
    )
    return {"status": "passed", "idea": idea, "focus": focus}


def _research_carplay_huddle_idea_now(*, idea_id: str, actor: str) -> dict[str, Any]:
    from .agent_work import get_work_store
    from .ideas import get_idea, mark_researching, queue_idea
    from .llm_gateway import get_gateway

    idea = get_idea(idea_id)
    if idea is None:
        raise KeyError("Idea not found.")
    if idea.get("status") == "researching":
        focus = _record_carplay_huddle_focus(
            actor=actor,
            action="Research CarPlay Huddle Idea Now",
            detail=f"CarPlay confirmed {str(idea.get('text') or idea_id).strip() or idea_id} is already researching.",
            why_now="The in-car Huddle lane checked whether a queued idea was already moving.",
            result_summary="Huddle idea was already researching from CarPlay.",
            related_kind="idea",
            related_label=str(idea.get("text") or idea.get("id") or idea_id),
        )
        return {"status": "already_researching", "idea": idea, "work_id": str(idea.get("work_id") or ""), "focus": focus}

    if idea.get("status") == "captured":
        queue_idea(idea_id)

    gw = get_gateway()
    if gw is None:
        raise ValueError("LLM gateway not available")

    store = get_work_store("catalyst-personal")
    work_item = store.dream_idea(
        idea["text"][:80],
        idea["text"],
        idea.get("domain", "passive-income"),
        idea.get("tags", []),
    )
    work_id = work_item.work_id
    mark_researching(idea_id, work_id)
    refreshed = get_idea(idea_id) or idea
    focus = _record_carplay_huddle_focus(
        actor=actor,
        action="Research CarPlay Huddle Idea Now",
        detail=f"CarPlay launched live dossier research for {str(refreshed.get('text') or idea_id).strip() or idea_id}.",
        why_now="The in-car Huddle lane escalated a live idea directly into research instead of waiting for a later sweep.",
        result_summary="Huddle idea research started from CarPlay.",
        related_kind="idea",
        related_label=str(refreshed.get("text") or refreshed.get("id") or idea_id),
    )
    return {
        "queued": True,
        "work_id": work_id,
        "message": "Research started - check /api/dossiers for results.",
        "idea": refreshed,
        "focus": focus,
    }


def _build_catalyst_ops_overview(runtime: Any) -> dict[str, Any]:
    from .command_center_index import _agent_ops_roster
    from .supervision_snapshot import build_supervision_snapshot

    focus_summary = ProgressFocusStore(_ACTIVITY_AUDIT_ROOT).summary(limit=6)
    recovery_cases = RecoveryCaseStore(_ACTIVITY_AUDIT_ROOT).list_cases()
    approvals = list(runtime.list_pending_approvals() or [])
    activity = AuditLog(_ACTIVITY_AUDIT_ROOT).list_recent(limit=8)
    mission_snapshot = runtime.mission_control_snapshot("Chris")
    active_missions = list(mission_snapshot.get("active_missions") or [])
    agent_roster = _agent_ops_roster()
    supervision_snapshot = build_supervision_snapshot()
    agent_items = [dict(item) for item in list(agent_roster.get("items") or []) if isinstance(item, dict)]
    supervision_items = [
        dict(item)
        for item in list(supervision_snapshot.get("attention_queue") or [])
        if isinstance(item, dict)
    ]

    latest_focus = dict(focus_summary.get("latest") or {})
    current_focus = {
        "module": str(latest_focus.get("module") or "Progress").strip() or "Progress",
        "reason": str(latest_focus.get("reason") or "No shared focus recorded yet.").strip() or "No shared focus recorded yet.",
        "route": str(latest_focus.get("route") or "/progress-center").strip() or "/progress-center",
        "saved_at": str(latest_focus.get("saved_at") or "").strip(),
    }

    return {
        "generated_at": _ts(),
        "current_focus": current_focus,
        "focus_candidates": deepcopy(_CATALYST_OPS_FOCUS_CANDIDATES),
        "approvals": [
            {
                "request_id": str(item.get("request_id") or "").strip(),
                "title": str(item.get("request") or item.get("title") or "Approval").strip() or "Approval",
                "agent": str(item.get("agent") or item.get("agent_label") or "Unknown agent").strip() or "Unknown agent",
                "risk": str(item.get("risk_tier") or item.get("risk") or "medium").strip() or "medium",
                "detail": str(item.get("summary") or item.get("detail") or item.get("action_class") or "Pending review").strip() or "Pending review",
                "related_route": "/approval-queue",
            }
            for item in approvals[:4]
            if isinstance(item, dict)
        ],
        "recovery_cases": [
            {
                "case_id": str(item.get("case_id") or "").strip(),
                "title": str(item.get("title") or "Recovery case").strip() or "Recovery case",
                "status": str(item.get("status") or "open").strip() or "open",
                "status_label": str(item.get("status_label") or item.get("status") or "Open").strip() or "Open",
                "detail": str(item.get("detail") or "").strip() or "Recovery case needs review.",
                "execution_count": int(item.get("execution_count", 0) or 0),
                "remediation_status": str(item.get("remediation_status") or "available").strip() or "available",
                "remediation_status_label": str(item.get("remediation_status_label") or "Available").strip() or "Available",
                "remediation_count": int(item.get("remediation_count", 0) or 0),
                "remediation_plan_status": str(item.get("remediation_plan_status") or "unplanned").strip() or "unplanned",
                "remediation_plan_status_label": str(item.get("remediation_plan_status_label") or "Unplanned").strip() or "Unplanned",
                "remediation_plan_count": int(item.get("remediation_plan_count", 0) or 0),
                "remediation_plan_completed_count": int(item.get("remediation_plan_completed_count", 0) or 0),
                "next_plan_step_label": str(item.get("next_plan_step_label") or "").strip(),
                "related_route": str(item.get("related_route") or "/recovery-center").strip() or "/recovery-center",
                "next_action_type": "retry" if str(item.get("status") or "").strip().lower() not in {"watch", "resolved"} else "stabilize",
                "next_action_label": (
                    "Execute Retry Loop"
                    if str(item.get("status") or "").strip().lower() not in {"watch", "resolved"}
                    else "Stabilize Watch"
                ),
                "remediation_action_type": (
                    "execute"
                    if str(item.get("remediation_status") or "").strip().lower() in {"staged", "available"}
                    else "stage"
                ),
                "remediation_action_label": (
                    "Execute Auto-Remediation"
                    if str(item.get("remediation_status") or "").strip().lower() in {"staged", "available"}
                    else "Restage Auto-Remediation"
                ),
                "plan_action_label": (
                    "Execute Next Healing Step"
                    if int(item.get("remediation_plan_count", 0) or 0) > 0 and str(item.get("remediation_plan_status") or "").strip().lower() != "completed"
                    else "Prepare Healing Plan"
                ),
            }
            for item in recovery_cases[:4]
            if isinstance(item, dict)
        ],
        "agent_ops": [
            {
                "agent_id": str(item.get("agent_id") or "").strip(),
                "name": str(item.get("name") or item.get("agent_id") or "Agent").strip() or "Agent",
                "status": str(item.get("status") or "unknown").strip() or "unknown",
                "status_class": str(item.get("status_class") or "steady").strip() or "steady",
                "assignment": str(item.get("assignment") or "unassigned").strip() or "unassigned",
                "purpose": str(item.get("purpose") or "No purpose recorded.").strip() or "No purpose recorded.",
                "module": str(item.get("module") or item.get("domain") or "general").strip() or "general",
                "is_task_agent": bool(item.get("is_task_agent")),
                "mission_id": str(item.get("mission_id") or "").strip(),
                "mission_roles": [str(role).strip() for role in list(item.get("mission_roles") or []) if str(role).strip()],
                "policy_assignment": str(item.get("policy_assignment") or "").strip(),
                "attention_reason": str(item.get("attention_reason") or "").strip(),
                "last_activity": str(item.get("last_activity") or "not recorded").strip() or "not recorded",
                "related_route": "/agent-ops-center",
                "queue_action_label": "Queue Run",
                "assignment_action_label": "Save Assignment",
            }
            for item in agent_items[:4]
            if str(item.get("agent_id") or "").strip()
        ],
        "supervision_items": [
            {
                "request_id": str(item.get("request_id") or "").strip(),
                "title": str(item.get("title") or "Supervision review").strip() or "Supervision review",
                "agent": str(item.get("agent_label") or item.get("actor_id") or "Unknown agent").strip() or "Unknown agent",
                "risk": str(item.get("risk_tier") or "medium").strip() or "medium",
                "detail": str(item.get("why_now") or "Needs supervision review.").strip() or "Needs supervision review.",
                "action_type": str(item.get("action_type") or "").strip(),
                "related_route": "/supervision-snapshot",
                "approve_label": "Approve",
                "reject_label": "Reject",
            }
            for item in supervision_items[:4]
            if str(item.get("request_id") or "").strip()
        ],
        "recent_activity": [
            {
                "title": str(item.get("action") or item.get("entry_type") or "Activity").strip() or "Activity",
                "detail": str(item.get("detail") or item.get("result_summary") or "").strip(),
                "route_label": str(item.get("route_label") or item.get("related_route") or "").strip(),
                "actor": str(item.get("actor") or "").strip(),
                "related_route": str(item.get("related_route") or item.get("route") or "/command-center").strip() or "/command-center",
                "related_kind": str(item.get("related_kind") or item.get("entry_type") or "").strip(),
            }
            for item in activity[:6]
            if isinstance(item, dict)
        ],
        "missions": [
            {
                "mission_id": str(item.get("mission_id") or "").strip(),
                "title": str(item.get("title") or item.get("request") or "Mission").strip() or "Mission",
                "brief": str(item.get("brief") or item.get("request") or "No mission brief captured yet.").strip() or "No mission brief captured yet.",
                "status": str(item.get("status") or "active").strip() or "active",
                "lane": str(item.get("lane") or "").strip() or (
                    "completed"
                    if str(item.get("status") or "").strip().lower() == "completed"
                    else "now"
                ),
                "next_step": str(item.get("next_step") or "Review mission brief").strip() or "Review mission brief",
                "route": "/mission-board",
            }
            for item in active_missions[:3]
            if isinstance(item, dict)
        ],
        "counts": {
            "approval_count": len(approvals),
            "recovery_case_count": len(recovery_cases),
            "recent_activity_count": len(activity),
            "focus_history_count": int(focus_summary.get("history_count", 0) or 0),
            "mission_count": len(active_missions),
            "agent_ops_count": len(agent_items),
            "supervision_count": len(supervision_items),
        },
    }


def _save_catalyst_progress_focus(*, module: str, route: str, actor: str, reason: str) -> dict[str, Any]:
    entry = ProgressFocusStore(_ACTIVITY_AUDIT_ROOT).save_focus(
        module=module,
        reason=reason,
        route=route,
        actor=actor,
    )
    _record_operator_action(
        actor=actor,
        domain="catalyst",
        action="Set Catalyst Focus",
        detail=f"Catalyst moved the shared progress focus to {module}.",
        why_now="The iPhone ops studio elevated a new Level 3 closure target.",
        result_summary=f"Shared progress focus now points at {module}.",
        route=route,
        route_label=f"Open {module}",
        related_kind="progress-focus",
        related_label=module,
        succeeded=True,
    )
    return entry


def _approve_catalyst_approval(runtime: Any, *, request_id: str, actor: str) -> dict[str, Any]:
    approvals = [dict(item) for item in list(runtime.list_pending_approvals() or []) if isinstance(item, dict)]
    target = next((item for item in approvals if str(item.get("request_id") or "").strip() == request_id.strip()), None)
    updated = runtime.approval_store.update_status(request_id, "approved")
    if updated is None:
        raise KeyError("Pending approval request not found.")

    title = str((target or {}).get("request") or (target or {}).get("title") or request_id).strip() or request_id
    focus = ProgressFocusStore(_ACTIVITY_AUDIT_ROOT).save_focus(
        module="Approval Queue",
        reason=f"Catalyst approved {title} from the native ops studio.",
        route="/approval-queue",
        actor=actor,
    )
    _record_operator_action(
        actor=actor,
        domain="catalyst",
        action="Approve Catalyst Approval",
        detail=f"Catalyst approved {title}.",
        why_now="A pending approval was cleared from the native iPhone ops lane.",
        result_summary="Approval queue advanced from Catalyst.",
        route="/approval-queue",
        route_label="Open Approval Queue",
        related_kind="approval",
        related_label=title,
        succeeded=True,
    )
    return {
        "status": "approved",
        "request_id": request_id,
        "title": title,
        "focus": focus,
        "request": updated,
    }


def _execute_catalyst_recovery_case(*, case_id: str, actor: str, action_type: str, note: str = "") -> dict[str, Any]:
    store = RecoveryCaseStore(_ACTIVITY_AUDIT_ROOT)
    case = store.record_execution(case_id, actor=actor, action_type=action_type, note=note)
    detail = note or (
        f"Recovery retry loop executed for {str(case.get('title') or case_id).strip()}."
        if action_type == "retry"
        else f"Recovery stabilization loop executed for {str(case.get('title') or case_id).strip()}."
    )
    action_entry = RecoveryActionStore(_ACTIVITY_AUDIT_ROOT).record_action(
        action_type=action_type,
        target_kind="recovery-case",
        target_label=str(case.get("title") or "Recovery case").strip() or "Recovery case",
        target_id=str(case.get("case_id") or case_id).strip(),
        detail=detail,
        route="/recovery-center",
        status="executed" if action_type == "retry" else "stabilized",
    )
    _record_operator_action(
        actor=actor,
        domain="catalyst",
        action="Execute Catalyst Recovery Loop" if action_type == "retry" else "Stabilize Catalyst Recovery Loop",
        detail=detail,
        why_now="The native iPhone ops studio advanced a durable recovery case directly from the phone surface.",
        result_summary=f"Recovery case moved to {str(case.get('status_label') or case.get('status') or 'Investigating').strip()}",
        route=str(case.get("related_route") or "/recovery-center").strip() or "/recovery-center",
        route_label="Open Recovery Center",
        related_kind="recovery-case",
        related_label=str(case.get("case_id") or case_id).strip(),
        succeeded=True,
    )
    focus = ProgressFocusStore(_ACTIVITY_AUDIT_ROOT).save_focus(
        module="Recovery",
        reason=detail,
        route="/recovery-center",
        actor=actor,
    )
    return {"status": "recorded", "case": case, "action": action_entry, "focus": focus}


def _remediate_catalyst_recovery_case(*, case_id: str, actor: str, action_type: str, note: str = "") -> dict[str, Any]:
    store = RecoveryCaseStore(_ACTIVITY_AUDIT_ROOT)
    case = store.record_remediation(case_id, actor=actor, action_type=action_type, note=note)
    detail = note or (
        f"Auto-remediation staged for {str(case.get('title') or case_id).strip()}."
        if action_type == "stage"
        else f"Auto-remediation executed for {str(case.get('title') or case_id).strip()}."
    )
    action_entry = RecoveryActionStore(_ACTIVITY_AUDIT_ROOT).record_action(
        action_type=f"remediation-{action_type}",
        target_kind="recovery-case",
        target_label=str(case.get("title") or "Recovery case").strip() or "Recovery case",
        target_id=str(case.get("case_id") or case_id).strip(),
        detail=detail,
        route="/recovery-center",
        status="staged" if action_type == "stage" else "executed",
    )
    _record_operator_action(
        actor=actor,
        domain="catalyst",
        action="Stage Catalyst Recovery Auto-Remediation" if action_type == "stage" else "Execute Catalyst Recovery Auto-Remediation",
        detail=detail,
        why_now="The native iPhone ops studio advanced a durable auto-remediation plan directly from the phone surface.",
        result_summary=(
            f"Recovery remediation now {str(case.get('remediation_status_label') or case.get('remediation_status') or 'Staged').strip()}"
        ),
        route=str(case.get("related_route") or "/recovery-center").strip() or "/recovery-center",
        route_label="Open Recovery Center",
        related_kind="recovery-case",
        related_label=str(case.get("case_id") or case_id).strip(),
        succeeded=True,
    )
    focus = ProgressFocusStore(_ACTIVITY_AUDIT_ROOT).save_focus(
        module="Recovery",
        reason=detail,
        route="/recovery-center",
        actor=actor,
    )
    return {"status": "recorded", "case": case, "action": action_entry, "focus": focus}


def _advance_catalyst_recovery_plan(*, case_id: str, actor: str, note: str = "") -> dict[str, Any]:
    store = RecoveryCaseStore(_ACTIVITY_AUDIT_ROOT)
    case, step = store.execute_next_plan_step(case_id, actor=actor, note=note)
    detail = note or f"Catalyst completed the healing step {str(step.get('label') or 'Recovery step').strip()}."
    action_entry = RecoveryActionStore(_ACTIVITY_AUDIT_ROOT).record_action(
        action_type="remediation-plan-step",
        target_kind="recovery-case",
        target_label=str(case.get("title") or "Recovery case").strip() or "Recovery case",
        target_id=str(case.get("case_id") or case_id).strip(),
        detail=detail,
        route="/recovery-center",
        status=str(case.get("remediation_plan_status") or "in_progress").strip() or "in_progress",
    )
    _record_operator_action(
        actor=actor,
        domain="catalyst",
        action="Execute Catalyst Recovery Healing Step",
        detail=detail,
        why_now="The native iPhone ops studio advanced the next durable healing step from the phone surface.",
        result_summary=(
            f"Recovery plan is now {str(case.get('remediation_plan_status_label') or case.get('remediation_plan_status') or 'In Progress').strip()}"
        ),
        route=str(case.get("related_route") or "/recovery-center").strip() or "/recovery-center",
        route_label="Open Recovery Center",
        related_kind="recovery-case",
        related_label=str(case.get("case_id") or case_id).strip(),
        succeeded=True,
    )
    focus = ProgressFocusStore(_ACTIVITY_AUDIT_ROOT).save_focus(
        module="Recovery",
        reason=detail,
        route="/recovery-center",
        actor=actor,
    )
    return {"status": "recorded", "case": case, "step": step, "action": action_entry, "focus": focus}


def _update_catalyst_mission_status(runtime: Any, *, mission_id: str, status: str, actor: str, note: str = "") -> dict[str, Any]:
    updated = runtime.update_mission_status(mission_id, status, note=note)
    title = str(updated.get("title") or updated.get("request") or mission_id).strip() or mission_id
    _record_operator_action(
        actor=actor,
        domain="catalyst",
        action="Move Catalyst Mission to Now" if status == "active" else "Complete Catalyst Mission",
        detail=note or f"Catalyst updated mission {title} to {status}.",
        why_now="The native iPhone ops studio moved mission board state without dropping into the hosted route.",
        result_summary=f"Mission board status now {status}.",
        route="/mission-board",
        route_label="Open Mission Board",
        related_kind="mission",
        related_label=title,
        succeeded=True,
    )
    focus = ProgressFocusStore(_ACTIVITY_AUDIT_ROOT).save_focus(
        module="Mission Board",
        reason=note or f"Catalyst advanced mission board status for {title}.",
        route="/mission-board",
        actor=actor,
    )
    return {"status": "recorded", "mission": updated, "focus": focus}


def _queue_catalyst_agent_run(*, agent_id: str, actor: str) -> dict[str, Any]:
    from .scheduler import get_scheduler

    scheduler = get_scheduler()
    if scheduler is None:
        raise RuntimeError("Scheduler not initialised")
    item = scheduler.force_run(agent_id)
    if item is None:
        raise KeyError("Unknown agent")

    detail = f"Catalyst queued agent {agent_id} from the native ops studio."
    _record_operator_action(
        actor=actor,
        domain="catalyst",
        action="Queue Catalyst Agent Run",
        detail=detail,
        why_now="The native iPhone ops studio elevated an agent run without leaving the phone workflow.",
        result_summary=f"{agent_id} is queued for execution.",
        route="/agent-ops-center",
        route_label="Open Agent Ops",
        related_kind="agent-run",
        related_label=agent_id,
        succeeded=True,
    )
    focus = ProgressFocusStore(_ACTIVITY_AUDIT_ROOT).save_focus(
        module="Agent Ops",
        reason=detail,
        route="/agent-ops-center",
        actor=actor,
    )
    return {
        "status": "queued",
        "agent_id": agent_id,
        "item_id": str(getattr(item, "item_id", "") or ""),
        "focus": focus,
    }


def _save_catalyst_agent_assignment(
    runtime: Any,
    *,
    agent_id: str,
    mission_id: str,
    actor: str,
    policy_assignment: str = "",
    purpose: str = "",
) -> dict[str, Any]:
    updated = runtime.update_task_agent_assignment(
        agent_id,
        mission_id=mission_id,
        mission_roles=[],
        policy_assignment=policy_assignment,
        purpose=purpose,
    )
    title = str(updated.get("name") or updated.get("agent_id") or agent_id).strip() or agent_id
    target = str(updated.get("mission_id") or mission_id).strip()
    detail = (
        f"Catalyst updated {title} to mission {target} from the native ops studio."
        if target
        else f"Catalyst cleared the mission assignment for {title} from the native ops studio."
    )
    _record_operator_action(
        actor=actor,
        domain="catalyst",
        action="Save Catalyst Agent Assignment",
        detail=detail,
        why_now="The native iPhone ops studio updated a task-agent assignment without falling back to the hosted route.",
        result_summary=f"{title} now points at {target or 'an unassigned lane'}.",
        route="/agent-ops-center",
        route_label="Open Agent Ops",
        related_kind="agent-assignment",
        related_label=title,
        succeeded=True,
    )
    focus = ProgressFocusStore(_ACTIVITY_AUDIT_ROOT).save_focus(
        module="Agent Ops",
        reason=detail,
        route="/agent-ops-center",
        actor=actor,
    )
    return {
        "status": "recorded",
        "agent": updated,
        "focus": focus,
    }


def _resolve_catalyst_supervision_item(
    runtime: Any,
    *,
    request_id: str,
    action: str,
    actor: str,
    reason: str = "",
) -> dict[str, Any]:
    action_key = str(action or "").strip().lower()
    if action_key not in {"approve", "reject"}:
        raise ValueError("Unsupported supervision action.")

    from .supervision_snapshot import build_supervision_snapshot

    supervision_snapshot = build_supervision_snapshot()
    attention_items = [
        dict(item)
        for item in list(supervision_snapshot.get("attention_queue") or [])
        if isinstance(item, dict)
    ]
    target = next((item for item in attention_items if str(item.get("request_id") or "").strip() == request_id.strip()), None)
    status = "approved" if action_key == "approve" else "rejected"
    updated = runtime.approval_store.update_status(request_id, status)
    if updated is None:
        raise KeyError("Supervision request not found.")

    title = str((target or {}).get("title") or updated.get("request") or updated.get("title") or request_id).strip() or request_id
    detail = reason or (
        f"Catalyst approved {title} from the native supervision lane."
        if action_key == "approve"
        else f"Catalyst rejected {title} from the native supervision lane."
    )
    _record_operator_action(
        actor=actor,
        domain="catalyst",
        action="Approve Catalyst Supervision Review" if action_key == "approve" else "Reject Catalyst Supervision Review",
        detail=detail,
        why_now="The native iPhone supervision lane resolved a bounded-autonomy review item.",
        result_summary=f"Supervision review moved to {status}.",
        route="/supervision-snapshot",
        route_label="Open Supervision",
        related_kind="supervision-review",
        related_label=title,
        succeeded=True,
    )
    focus = ProgressFocusStore(_ACTIVITY_AUDIT_ROOT).save_focus(
        module="Supervision",
        reason=detail,
        route="/supervision-snapshot",
        actor=actor,
    )
    return {
        "status": status,
        "request_id": request_id,
        "title": title,
        "focus": focus,
        "request": updated,
    }


def _record_chronicle_progress_focus(
    *,
    actor: str,
    action: str,
    detail: str,
    why_now: str,
    result_summary: str,
    related_kind: str,
    related_label: str,
) -> dict[str, Any]:
    _record_operator_action(
        actor=actor,
        domain="chronicle",
        action=action,
        detail=detail,
        why_now=why_now,
        result_summary=result_summary,
        route="/chronicle-center",
        route_label="Open Chronicle",
        related_kind=related_kind,
        related_label=related_label,
        succeeded=True,
    )
    return ProgressFocusStore(_ACTIVITY_AUDIT_ROOT).save_focus(
        module="Chronicle",
        reason=detail,
        route="/chronicle-center",
        actor=actor,
    )


def _capture_chronicle_entry(*, entry_type: str, note: str, actor: str) -> dict[str, Any]:
    trimmed_note = str(note or "").strip()
    if not trimmed_note:
        return {"captured": False, "reason": "empty", "entry_id": "", "focus": None}

    entry = {
        "entry_id": str(uuid.uuid4()),
        "entry_type": str(entry_type or "reflection").strip() or "reflection",
        "title": trimmed_note[:50],
        "body": trimmed_note,
        "note": trimmed_note,
        "actor": actor,
        "timestamp": _ts(),
        "created_at": _ts(),
        "source": "apple_phone",
    }
    entries_path = Path("data/chronicle/entries.jsonl")
    entries_path.parent.mkdir(parents=True, exist_ok=True)
    with entries_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")

    focus = _record_chronicle_progress_focus(
        actor=actor,
        action="Capture Chronicle Note",
        detail=f"Chronicle captured a {entry['entry_type']} note from JarvisPhone.",
        why_now="The native Chronicle screen captured a real reflection and fed shared continuity back into the product.",
        result_summary="Chronicle timeline advanced from the iPhone capture flow.",
        related_kind="chronicle-entry",
        related_label=str(entry.get("title") or "Chronicle note"),
    )
    return {"captured": True, "entry_id": entry["entry_id"], "focus": focus}


def _mark_chronicle_prayer_prayed(*, prayer_id: str, actor: str, note: str = "") -> dict[str, Any]:
    today = datetime.now(timezone.utc).date().isoformat()
    activity = _load_chronicle_prayer_activity()
    state = activity.get(prayer_id, {"times_prayed": 0, "last_prayed_at": ""})
    state["times_prayed"] = int(state.get("times_prayed") or 0) + 1
    state["last_prayed_at"] = today
    activity[prayer_id] = state
    _persist_chronicle_prayer_activity(activity)

    if note:
        entry = {
            "entry_id": str(uuid.uuid4()),
            "entry_type": "prayer",
            "title": "Prayer note",
            "body": note,
            "note": note,
            "actor": actor,
            "timestamp": _ts(),
            "created_at": _ts(),
            "source": "apple_chronicle_prayer",
        }
        entries_path = Path("data/chronicle/entries.jsonl")
        entries_path.parent.mkdir(parents=True, exist_ok=True)
        with entries_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")

    focus = _record_chronicle_progress_focus(
        actor=actor,
        action="Log Chronicle Prayer",
        detail="Chronicle logged a lived prayer moment from the iPhone reflection flow.",
        why_now="The native Chronicle prayer lane advanced shared formation continuity.",
        result_summary=f"Prayer activity count is now {int(state.get('times_prayed') or 0)}.",
        related_kind="chronicle-prayer",
        related_label=prayer_id,
    )
    return {
        "status": "prayed",
        "prayer_id": prayer_id,
        "times_prayed": int(state.get("times_prayed") or 0),
        "last_prayed_at": str(state.get("last_prayed_at") or ""),
        "focus": focus,
    }


def _mark_chronicle_prayer_answered(*, prayer_id: str, actor: str, note: str = "") -> dict[str, Any]:
    answered_at = _ts()
    _append_jsonl(
        _CHRONICLE_ANSWERED_PRAYERS_PATH,
        {
            "id": prayer_id,
            "actor_id": actor,
            "answerSummary": note or "Marked answered from JarvisPhone.",
            "answered_at": answered_at,
            "received_at": answered_at,
            "surfaced": False,
        },
    )
    if note:
        entry = {
            "entry_id": str(uuid.uuid4()),
            "entry_type": "milestone",
            "title": "Answered prayer",
            "body": note,
            "note": note,
            "actor": actor,
            "timestamp": answered_at,
            "created_at": answered_at,
            "source": "apple_chronicle_answered_prayer",
        }
        entries_path = Path("data/chronicle/entries.jsonl")
        entries_path.parent.mkdir(parents=True, exist_ok=True)
        with entries_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")

    focus = _record_chronicle_progress_focus(
        actor=actor,
        action="Mark Chronicle Prayer Answered",
        detail="Chronicle recorded an answered prayer from the iPhone follow-up flow.",
        why_now="The native Chronicle prayer lane closed a reflection loop and promoted that continuity into shared progress state.",
        result_summary="Chronicle answered-prayer continuity was updated.",
        related_kind="chronicle-prayer",
        related_label=prayer_id,
    )
    return {
        "status": "answered",
        "prayer_id": prayer_id,
        "answered_at": answered_at,
        "focus": focus,
    }


def _save_chronicle_study_entry(*, actor: str, title: str, passage: str, notes: str) -> dict[str, Any]:
    trimmed_notes = str(notes or "").strip()
    if not trimmed_notes:
        return {"captured": False, "entry_id": "", "focus": None}

    entry_id = str(uuid.uuid4())
    entry = {
        "entry_id": entry_id,
        "entry_type": "study",
        "title": str(title or "").strip() or (f"Bible Study — {passage}" if passage else "Bible Study"),
        "body": trimmed_notes,
        "note": trimmed_notes,
        "actor": actor,
        "timestamp": _ts(),
        "created_at": _ts(),
        "source": "apple_chronicle_study",
    }
    if passage:
        entry["passage"] = passage
        entry["scripture_ref"] = passage
    entries_path = Path("data/chronicle/entries.jsonl")
    entries_path.parent.mkdir(parents=True, exist_ok=True)
    with entries_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")

    focus = _record_chronicle_progress_focus(
        actor=actor,
        action="Save Chronicle Study",
        detail="Chronicle saved a study reflection from the native study workspace.",
        why_now="The iPhone Chronicle study lane turned a live reflection into shared continuity and progress focus.",
        result_summary="Chronicle study notes were saved into the live timeline.",
        related_kind="chronicle-study",
        related_label=str(entry.get("title") or "Bible Study"),
    )
    return {"captured": True, "entry_id": entry_id, "focus": focus}


def _review_chronicle_entry(
    *,
    entry_id: str,
    actor: str,
    title: str,
    entry_type: str,
    status: str,
    note: str = "",
) -> dict[str, Any]:
    review = ChronicleReviewStore().review_entry(
        entry_id=entry_id,
        actor_id=actor,
        title=title,
        entry_type=entry_type,
        status=status,
        note=note,
        route="/chronicle-center",
    )
    focus = _record_chronicle_progress_focus(
        actor=actor,
        action=review["review_status_label"],
        detail=f"Chronicle moved '{review['entry_title']}' into {review['review_status_label'].lower()} from the native review lane.",
        why_now="The iPhone Chronicle screen pushed a live memory thread into study, family handoff, or resolution continuity.",
        result_summary=f"Chronicle review status is now {review['review_status_label'].lower()}.",
        related_kind="chronicle-review",
        related_label=str(review.get("entry_title") or "Chronicle entry"),
    )
    return {"status": "recorded", "review": review, "focus": focus}


def _record_huddle_progress_focus(
    *,
    actor: str,
    action: str,
    detail: str,
    why_now: str,
    result_summary: str,
    related_kind: str,
    related_label: str,
) -> dict[str, Any]:
    _record_operator_action(
        actor=actor,
        domain="huddle",
        action=action,
        detail=detail,
        why_now=why_now,
        result_summary=result_summary,
        route="/huddle-center",
        route_label="Open Huddle",
        related_kind=related_kind,
        related_label=related_label,
        succeeded=True,
    )
    return ProgressFocusStore(_ACTIVITY_AUDIT_ROOT).save_focus(
        module="Huddle",
        reason=detail,
        route="/huddle-center",
        actor=actor,
    )


def _serialize_huddle_work_item(item: Any) -> dict[str, Any]:
    from dataclasses import asdict, is_dataclass

    if isinstance(item, dict):
        return dict(item)
    if is_dataclass(item):
        return asdict(item)
    payload = {}
    for key in ("work_id", "title", "request", "status", "priority", "created_at", "updated_at"):
        value = getattr(item, key, None)
        if value is not None:
            payload[key] = value
    if payload:
        return payload
    if hasattr(item, "__dict__"):
        return dict(vars(item))
    return {"value": str(item)}


def _resolve_huddle_approval(*, work_id: str, action: str, actor: str, note: str = "") -> dict[str, Any]:
    from .agent_work import get_all_stores

    action_key = str(action or "").strip().lower()
    if action_key not in {"approve", "reject"}:
        raise ValueError("Unsupported huddle approval action.")

    updated_item: Any | None = None
    for store in get_all_stores().values():
        item = store.get(work_id)
        if item is None:
            continue
        if action_key == "approve":
            store.mark_approved(work_id, approved_by="Chris")
        else:
            store.mark_rejected(work_id, reason=note or "Declined from JarvisPhone Huddle.")
        updated_item = store.get(work_id)
        break

    if updated_item is None:
        raise KeyError("Huddle approval work item not found.")

    updated = _serialize_huddle_work_item(updated_item)
    title = str(updated.get("title") or updated.get("request") or work_id).strip() or work_id
    status = str(updated.get("status") or ("approved" if action_key == "approve" else "rejected")).strip() or (
        "approved" if action_key == "approve" else "rejected"
    )
    detail = note or (
        f"Huddle approved {title} from the native alignment lane."
        if action_key == "approve"
        else f"Huddle rejected {title} from the native alignment lane."
    )
    focus = _record_huddle_progress_focus(
        actor=actor,
        action="Approve Huddle Decision" if action_key == "approve" else "Reject Huddle Decision",
        detail=detail,
        why_now="The native Huddle screen resolved a live approval item without dropping back to the web route.",
        result_summary=f"Huddle approval moved to {status}.",
        related_kind="huddle-approval",
        related_label=title,
    )
    return {
        "status": status,
        "work_id": work_id,
        "title": title,
        "focus": focus,
        "item": updated,
    }


def _capture_huddle_idea(*, text: str, actor: str, domain: str = "passive-income", notes: str = "") -> dict[str, Any]:
    from .ideas import add_idea

    cleaned = str(text or "").strip()
    if not cleaned:
        raise ValueError("text is required")
    domain = str(domain or "passive-income").strip() or "passive-income"
    idea = add_idea(cleaned, "user", str(notes or ""), domain, [])
    focus = _record_huddle_progress_focus(
        actor=actor,
        action="Capture Huddle Idea",
        detail=f"Huddle captured a live idea in the {domain} lane.",
        why_now="The iPhone Huddle screen pushed a live idea into the shared research inbox.",
        result_summary="Huddle idea captured.",
        related_kind="idea",
        related_label=str(idea.get("text") or idea.get("id") or "Idea"),
    )
    return {"status": "captured", "idea": idea, "focus": focus}


def _queue_huddle_idea(*, idea_id: str, actor: str) -> dict[str, Any]:
    from .ideas import queue_idea

    idea = queue_idea(idea_id)
    if idea is None:
        raise KeyError("Idea not found.")
    focus = _record_huddle_progress_focus(
        actor=actor,
        action="Queue Huddle Idea",
        detail=f"Huddle queued {str(idea.get('text') or idea_id).strip() or idea_id} for background research.",
        why_now="The iPhone Huddle screen promoted a captured idea into the queued research lane.",
        result_summary="Huddle idea queued.",
        related_kind="idea",
        related_label=str(idea.get("text") or idea.get("id") or idea_id),
    )
    return {"status": "queued", "idea": idea, "focus": focus}


def _pass_huddle_idea(*, idea_id: str, actor: str) -> dict[str, Any]:
    from .ideas import pass_idea

    idea = pass_idea(idea_id)
    if idea is None:
        raise KeyError("Idea not found.")
    focus = _record_huddle_progress_focus(
        actor=actor,
        action="Pass Huddle Idea",
        detail=f"Huddle passed on {str(idea.get('text') or idea_id).strip() or idea_id} after review.",
        why_now="The iPhone Huddle screen intentionally dismissed a live idea instead of leaving it stalled in the inbox.",
        result_summary="Huddle idea passed.",
        related_kind="idea",
        related_label=str(idea.get("text") or idea.get("id") or idea_id),
    )
    return {"status": "passed", "idea": idea, "focus": focus}


def _research_huddle_idea_now(*, idea_id: str, actor: str) -> dict[str, Any]:
    from .agent_work import get_work_store
    from .ideas import get_idea, mark_researching, queue_idea
    from .llm_gateway import get_gateway

    idea = get_idea(idea_id)
    if idea is None:
        raise KeyError("Idea not found.")
    if idea.get("status") == "researching":
        focus = _record_huddle_progress_focus(
            actor=actor,
            action="Research Huddle Idea Now",
            detail=f"Huddle confirmed {str(idea.get('text') or idea_id).strip() or idea_id} is already researching.",
            why_now="The iPhone Huddle screen checked a live idea that was already in research.",
            result_summary="Huddle idea was already researching.",
            related_kind="idea",
            related_label=str(idea.get("text") or idea.get("id") or idea_id),
        )
        return {"status": "already_researching", "idea": idea, "work_id": str(idea.get("work_id") or ""), "focus": focus}

    if idea.get("status") == "captured":
        queue_idea(idea_id)
        idea = get_idea(idea_id) or idea

    gw = get_gateway()
    if gw is None:
        raise ValueError("LLM gateway not available")

    pi_store = get_work_store("catalyst-personal")
    work_item = pi_store.dream_idea(
        str(idea.get("text") or "")[:80],
        str(idea.get("text") or ""),
        str(idea.get("domain") or "passive-income"),
        list(idea.get("tags") or []),
    )
    work_id = work_item.work_id
    mark_researching(idea_id, work_id)
    refreshed = get_idea(idea_id) or idea
    focus = _record_huddle_progress_focus(
        actor=actor,
        action="Research Huddle Idea Now",
        detail=f"Huddle launched live dossier research for {str(refreshed.get('text') or idea_id).strip() or idea_id}.",
        why_now="The iPhone Huddle screen escalated an idea directly into live research instead of waiting for a later queue sweep.",
        result_summary="Huddle idea research started.",
        related_kind="idea",
        related_label=str(refreshed.get("text") or refreshed.get("id") or idea_id),
    )
    return {"status": "researching", "idea": refreshed, "work_id": work_id, "focus": focus}


async def _timeboxed_to_thread(
    func: Any,
    *args: Any,
    timeout: float = 0.75,
    default: Any = None,
    label: str = "",
) -> Any:
    try:
        return await asyncio.wait_for(asyncio.to_thread(func, *args), timeout=timeout)
    except asyncio.TimeoutError:
        if label:
            logger.warning("apple_api timeout in %s after %.2fs", label, timeout)
        return default
    except Exception as exc:
        if label:
            logger.warning("apple_api best-effort failure in %s: %s", label, exc)
        return default


def _boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "ready", "connected", "available", "ok"}
    return False


def _is_recent_timestamp(value: Any, minutes: int = 5) -> bool:
    raw = str(value or "").strip()
    if not raw:
        return False
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return False
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    delta = datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)
    return delta.total_seconds() <= max(0, minutes) * 60


def _slugify_label(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", str(value or "").strip().lower()).strip("-")
    return slug


def _publishing_platform_focus(platform: str, project_type: str) -> str:
    normalized_platform = str(platform or "").strip().lower()
    normalized_type = str(project_type or "").strip().lower()
    if "kdp" in normalized_platform or "amazon" in normalized_platform:
        return "KDP metadata, proof review, and marketplace copy readiness."
    if "gumroad" in normalized_platform:
        return "Landing page, checkout assets, and bonus delivery readiness."
    if "udemy" in normalized_platform or "coursera" in normalized_platform:
        return "Curriculum packaging, preview lessons, and platform listing readiness."
    if "wordpress" in normalized_platform or "substack" in normalized_platform:
        return "Web publishing flow, distribution copy, and traffic handoff readiness."
    if normalized_type == "course":
        return "Course resources, preview assets, and launch copy readiness."
    if normalized_type == "book":
        return "Manuscript packaging, metadata, and launch asset readiness."
    return "Platform handoff, review queue, and launch materials readiness."


def _publishing_launch_slug_candidates(project: dict[str, Any] | None, strategy: dict[str, Any] | None) -> list[str]:
    candidates: list[str] = []
    if isinstance(project, dict):
        for raw in (
            project.get("project_id"),
            project.get("title"),
            project.get("url"),
            project.get("notes"),
        ):
            text = str(raw or "").strip()
            if not text:
                continue
            candidates.append(text)
            if "/" in text:
                candidates.extend(segment for segment in text.split("/") if segment)
    if isinstance(strategy, dict):
        for raw in (
            strategy.get("slug"),
            strategy.get("book_slug"),
            strategy.get("project_slug"),
            strategy.get("book_title"),
        ):
            text = str(raw or "").strip()
            if text:
                candidates.append(text)

    ordered: list[str] = []
    seen: set[str] = set()
    for value in candidates:
        for candidate in (value, _slugify_label(value)):
            normalized = str(candidate or "").strip().strip("/")
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            ordered.append(normalized)
    return ordered


def _publishing_asset_summary(launch_assets: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(launch_assets, dict):
        return []
    assets = launch_assets.get("assets")
    if not isinstance(assets, dict):
        return []

    twitter = assets.get("twitter") if isinstance(assets.get("twitter"), list) else []
    linkedin = assets.get("linkedin") if isinstance(assets.get("linkedin"), list) else []
    emails = assets.get("emails") if isinstance(assets.get("emails"), list) else []
    amazon_copy = assets.get("amazon_copy") if isinstance(assets.get("amazon_copy"), dict) else {}
    podcast_points = assets.get("podcast_talking_points") if isinstance(assets.get("podcast_talking_points"), list) else []

    amazon_items = 0
    if str(amazon_copy.get("description") or "").strip():
        amazon_items += 1
    subtitles = amazon_copy.get("subtitles")
    if isinstance(subtitles, list):
        amazon_items += len([item for item in subtitles if str(item or "").strip()])
    keywords = amazon_copy.get("keywords")
    if isinstance(keywords, list):
        amazon_items += len([item for item in keywords if str(item or "").strip()])

    outreach_count = 0
    for key in ("press_release", "goodreads", "podcast_pitch", "newsletter_blurb", "review_request"):
        if str(assets.get(key) or "").strip():
            outreach_count += 1
    outreach_count += len(podcast_points)

    bundles = [
        {
            "key": "social",
            "title": "Social Launch Series",
            "status": "ready" if (len(twitter) + len(linkedin)) > 0 else "missing",
            "item_count": len(twitter) + len(linkedin),
            "detail": f"{len(twitter)} X posts and {len(linkedin)} LinkedIn posts generated.",
        },
        {
            "key": "email",
            "title": "Email Sequence",
            "status": "ready" if emails else "missing",
            "item_count": len(emails),
            "detail": f"{len(emails)} launch emails staged for pre-launch, launch day, and follow-up.",
        },
        {
            "key": "marketplace",
            "title": "KDP / Marketplace Copy",
            "status": "ready" if amazon_items else "missing",
            "item_count": amazon_items,
            "detail": f"{len(subtitles) if isinstance(subtitles, list) else 0} subtitle options and {len(keywords) if isinstance(keywords, list) else 0} keyword phrases prepared.",
        },
        {
            "key": "outreach",
            "title": "Press And Outreach",
            "status": "ready" if outreach_count else "missing",
            "item_count": outreach_count,
            "detail": "Press release, newsletter, podcast, and review-request assets are packaged together.",
        },
    ]

    status = str(launch_assets.get("status") or "").strip().lower()
    if status == "partial":
        for bundle in bundles:
            if bundle["status"] == "missing":
                bundle["status"] = "partial"
    return bundles


def _publishing_launch_workspace(
    *,
    project: dict[str, Any] | None,
    strategy: dict[str, Any] | None,
    checklist: list[dict[str, Any]],
) -> dict[str, Any] | None:
    candidates = _publishing_launch_slug_candidates(project, strategy)
    assets_blob = None
    launch_slug = ""
    if candidates:
        from .book_launch import load_assets

        for candidate in candidates:
            loaded = load_assets(candidate)
            if isinstance(loaded, dict):
                assets_blob = loaded
                launch_slug = candidate
                break

    assets = _publishing_asset_summary(assets_blob)
    checklist_items = [item for item in checklist if isinstance(item, dict)]
    completed_steps = sum(1 for item in checklist_items if _boolish(item.get("completed")))
    total_steps = len(checklist_items)
    checklist_progress = f"{completed_steps}/{total_steps}" if total_steps else ""
    checklist_percent = round((completed_steps / total_steps) * 100) if total_steps else 0
    next_step = next((str(item.get("label") or "") for item in checklist_items if not _boolish(item.get("completed"))), "")

    if not checklist_items and not assets:
        return None

    platform = str((project or {}).get("platform") or "")
    project_type = str((project or {}).get("project_type") or "")
    title = str((project or {}).get("title") or (strategy or {}).get("book_title") or launch_slug or "")

    return {
        "project_id": str((project or {}).get("project_id") or ""),
        "title": title,
        "platform": platform,
        "platform_focus": _publishing_platform_focus(platform, project_type),
        "checklist_progress": checklist_progress,
        "checklist_percent": checklist_percent,
        "next_checklist_step": next_step,
        "launch_slug": launch_slug,
        "asset_status": str((assets_blob or {}).get("status") or ("ready" if assets else "missing")),
        "generated_at": str((assets_blob or {}).get("generated_at") or ""),
        "checklist": checklist_items,
        "assets": assets,
    }


def _apple_voice_should_speak(text: str) -> bool:
    normalized = str(text or "").strip()
    if not normalized:
        return False
    try:
        from .voice_pipeline import get_pipeline

        pipeline = get_pipeline()
        if pipeline is not None:
            return bool(pipeline.should_speak(normalized, {"surface": "apple_voice"}))
    except Exception as exc:
        logger.debug("apple_voice_should_speak fallback: %s", exc)

    if normalized.startswith("```"):
        return False
    if len(normalized) > 3000:
        return False
    return True


def _build_apple_voice_payload(*, response_text: str, agent_name: str) -> dict[str, Any]:
    display_text = str(response_text or "").strip() or "Understood."
    spoken_text = " ".join(display_text.split())
    speak = _apple_voice_should_speak(spoken_text)
    presentation_mode = "spoken_reply" if speak else "text_only"
    return {
        "response": display_text,
        "agent": str(agent_name or "JARVIS").strip() or "JARVIS",
        "speak": speak,
        "display_text": display_text,
        "spoken_text": spoken_text,
        "presentation_mode": presentation_mode,
        "surface": "apple_voice",
    }


def _build_apple_voice_followups(text: str) -> list[str]:
    normalized = str(text or "").strip().lower()
    if not normalized:
        return [
            "Summarize what matters this morning",
            "What needs my approval right now?",
            "Walk me through today's calendar",
        ]
    if "calendar" in normalized or "meeting" in normalized or "today" in normalized:
        return [
            "Stage prep for my next event",
            "What should I leave for now?",
            "Any route-sensitive meetings today?",
        ]
    if "home" in normalized or "lights" in normalized or "door" in normalized:
        return [
            "Review home alerts",
            "What does the house need right now?",
            "Stage the next home action",
        ]
    if "approval" in normalized or "need" in normalized:
        return [
            "Show the highest-priority request",
            "What happens if I wait?",
            "Summarize the queue in one sentence",
        ]
    return [
        "What should I handle next?",
        "Give me the short version",
        "Turn this into an action plan",
    ]


def _build_apple_voice_state(actor_id: str = "chris", conversation_id: str = "") -> dict[str, Any]:
    snapshot = runtime.chat_state_snapshot(actor_id, conversation_id, "office")
    active = snapshot.get("active_conversation") if isinstance(snapshot, dict) else {}
    if not isinstance(active, dict):
        active = {}

    turns = [item for item in active.get("turns", []) if isinstance(item, dict)]
    recent_turns: list[dict[str, Any]] = []
    for turn in turns[-6:]:
        role = str(turn.get("role") or "").strip() or "assistant"
        text = str(turn.get("text") or "").strip()
        if not text:
            continue
        metadata = turn.get("metadata") if isinstance(turn.get("metadata"), dict) else {}
        recent_turns.append(
            {
                "role": role,
                "text": text,
                "created_at": str(turn.get("created_at") or ""),
                "agent": str(metadata.get("provider") or "JARVIS") if role == "assistant" else str(turn.get("actor") or actor_id),
            }
        )

    memory_overview = snapshot.get("memory_overview") if isinstance(snapshot, dict) else {}
    if not isinstance(memory_overview, dict):
        memory_overview = {}
    try:
        viewer = runtime.get_actor(actor_id)
        learning_snapshot = runtime.learning_review_snapshot(viewer.display_name, viewer.user_id) or {}
        memory_graph = runtime.durable_memory_graph_snapshot(viewer.display_name, viewer.user_id) or {}
    except Exception:
        learning_snapshot = {}
        memory_graph = {}
    if not isinstance(learning_snapshot, dict):
        learning_snapshot = {}
    if not isinstance(memory_graph, dict):
        memory_graph = {}
    learning_profile = learning_snapshot.get("profile") if isinstance(learning_snapshot.get("profile"), dict) else {}
    learning_personalization = learning_snapshot.get("personalization") if isinstance(learning_snapshot.get("personalization"), dict) else {}
    learning_facts = learning_snapshot.get("profile_facts") if isinstance(learning_snapshot.get("profile_facts"), list) else []
    learning_first_light = learning_snapshot.get("first_light_history") if isinstance(learning_snapshot.get("first_light_history"), list) else []

    guidance_lines: list[str] = []
    for line in learning_personalization.get("rhythms", []) if isinstance(learning_personalization.get("rhythms"), list) else []:
        cleaned = str(line).strip()
        if cleaned and cleaned not in guidance_lines:
            guidance_lines.append(cleaned)
    for line in learning_personalization.get("learned_preferences", []) if isinstance(learning_personalization.get("learned_preferences"), list) else []:
        cleaned = str(line).strip()
        if cleaned and cleaned not in guidance_lines:
            guidance_lines.append(cleaned)

    recent_profile_facts: list[dict[str, Any]] = []
    for item in learning_facts[:3]:
        if not isinstance(item, dict):
            continue
        recent_profile_facts.append(
            {
                "id": str(item.get("fact_id") or item.get("id") or ""),
                "title": str(item.get("title") or item.get("summary") or "Voice continuity fact"),
                "summary": str(item.get("summary") or ""),
            }
        )

    recent_first_light: list[dict[str, Any]] = []
    for index, item in enumerate(list(reversed(learning_first_light))[:3]):
        if not isinstance(item, dict):
            continue
        first_20 = item.get("first_20_minutes") if isinstance(item.get("first_20_minutes"), list) else []
        summary = str(item.get("watch_line") or "").strip()
        if not summary and first_20:
            summary = "; ".join(str(step).strip() for step in first_20[:2] if str(step).strip())
        if not summary:
            summary = "First Light continuity packet recorded."
        recent_first_light.append(
            {
                "id": str(item.get("packet_id") or item.get("date") or item.get("local_time") or f"voice-fl-{index}"),
                "label": str(item.get("date") or item.get("local_time") or "Recent First Light"),
                "summary": summary,
            }
        )

    recent_threads = snapshot.get("recent_conversations") if isinstance(snapshot, dict) else []
    if not isinstance(recent_threads, list):
        recent_threads = []
    recent_conversations: list[dict[str, Any]] = []
    for thread in recent_threads[:5]:
        if not isinstance(thread, dict):
            continue
        recent_conversations.append(
            {
                "conversation_id": str(thread.get("conversation_id") or ""),
                "title": str(thread.get("title") or "Conversation"),
                "updated_at": str(thread.get("updated_at") or thread.get("last_activity_at") or ""),
                "turn_count": int(thread.get("turn_count") or 0),
            }
        )

    voice_store = VoiceSettingsStore(runtime.config)
    voice_settings = voice_store.describe()
    stack_status = voice_settings.get("stack_status") if isinstance(voice_settings, dict) else {}
    if not isinstance(stack_status, dict):
        stack_status = {}
    selected_voice_label = str(
        voice_settings.get("selected_elevenlabs_label")
        or voice_settings.get("selected_piper_label")
        or voice_settings.get("tts_provider")
        or "Auto"
    )
    local_ready = any(
        _boolish(stack_status.get(key))
        for key in ("ollama_available", "piper_ready", "system_voice_available", "localai_available")
    )
    cloud_ready = any(
        _boolish(stack_status.get(key))
        for key in ("elevenlabs_ready", "openai_ready", "azure_ready")
    )

    latest_user_text = str(active.get("latest_user_text") or "").strip()

    return {
        "conversation": {
            "conversation_id": str(active.get("conversation_id") or ""),
            "title": str(active.get("title") or "Voice Session"),
            "updated_at": str(active.get("updated_at") or active.get("last_activity_at") or ""),
            "turn_count": int(active.get("turn_count") or len(turns)),
            "latest_user_text": latest_user_text,
            "latest_assistant_text": str(active.get("latest_assistant_text") or "").strip(),
            "recent_turns": recent_turns,
        },
        "recent_conversations": recent_conversations,
        "memory_overview": {
            "profile_fact_count": int(memory_overview.get("profile_fact_count") or 0),
            "pending_proposals": int(memory_overview.get("pending_proposals") or 0),
            "preferred_voice": str(learning_profile.get("preferred_voice") or ""),
            "briefing_style": str(learning_profile.get("briefing_style") or ""),
            "guidance_lines": guidance_lines[:4],
            "recent_profile_facts": recent_profile_facts,
            "recent_first_light": recent_first_light,
            "long_horizon_lines": _memory_graph_long_horizon_lines(memory_graph),
            "active_threads": _memory_graph_thread_titles(memory_graph),
        },
        "voice_stack": {
            "provider": str(voice_settings.get("tts_provider") or "auto"),
            "provider_label": str(voice_settings.get("selected_provider_label") or "Auto"),
            "voice_label": selected_voice_label,
            "local_ready": local_ready,
            "cloud_ready": cloud_ready,
            "detail": (
                f"{selected_voice_label} · "
                f"{'local ready' if local_ready else 'local idle'} · "
                f"{'cloud ready' if cloud_ready else 'cloud idle'}"
            ),
        },
        "quick_commands": _build_apple_voice_followups(latest_user_text),
    }


def _apple_voice_extract_text(result: Any) -> str:
    if result is None:
        return ""
    if isinstance(result, dict):
        return str(
            result.get("output_text")
            or result.get("response")
            or result.get("text")
            or ""
        ).strip()

    for attr in ("output_text", "response", "text"):
        value = getattr(result, attr, "")
        if value:
            return str(value).strip()
    return str(result).strip()


def _apple_voice_extract_agent(result: Any, default: str = "JARVIS") -> str:
    if isinstance(result, dict):
        return str(result.get("agent") or result.get("actor") or default).strip() or default
    return str(getattr(result, "agent", default) or default).strip() or default


_APPLE_VOICE_CALENDAR_RE = re.compile(
    r"\b(schedule|calendar|agenda|events?)\b",
    re.IGNORECASE,
)
_APPLE_VOICE_TODAY_RE = re.compile(r"\b(today|this\s+(morning|afternoon|evening))\b", re.IGNORECASE)


def _apple_voice_local_schedule_summary(runtime: Any = None, actor_id: str = "chris") -> str:
    try:
        from .unified_inbox import get_unified_inbox

        inbox = get_unified_inbox()
        if inbox is not None:
            agenda = inbox.get_todays_agenda()
            events = agenda.get("events") or []
            if events:
                return _apple_voice_format_schedule_events(events)

        if runtime is not None:
            actor = runtime.get_actor(actor_id)
            events = runtime._actor_calendar_events(actor, limit=8)
            if events:
                return _apple_voice_format_schedule_events(events)
        return "You have nothing on your schedule today."
    except Exception as exc:
        logger.warning("apple_voice_local_schedule_summary failed: %s", exc)
        return ""


def _apple_voice_format_schedule_events(events: list[dict[str, Any]]) -> str:
    if not events:
        return "You have nothing on your schedule today."

    summaries: list[str] = []
    for event in events[:3]:
        title = str(event.get("title") or event.get("summary") or "an event").strip()
        start_raw = str(event.get("start_time") or event.get("start") or "").strip()
        if start_raw:
            try:
                start_dt = datetime.fromisoformat(start_raw.replace("Z", "+00:00"))
                time_label = start_dt.astimezone().strftime("%-I:%M %p")
                summaries.append(f"{title} at {time_label}")
            except Exception:
                summaries.append(title)
        else:
            summaries.append(title)

    opening = "You have 1 thing on your schedule today: " if len(events) == 1 else f"You have {len(events)} things on your schedule today. "
    if len(events) == 1:
        return opening + summaries[0] + "."

    spoken = opening + "; ".join(summaries)
    if len(events) > 3:
        spoken += f"; plus {len(events) - 3} more"
    return spoken + "."


def _apple_voice_try_local_handler(runtime: Any, text: str, actor_id: str = "chris") -> tuple[str, str] | None:
    try:
        for handler_name in ("_try_handle_reminder", "_try_handle_task_creation", "_try_handle_calendar_event"):
            handler = getattr(runtime, handler_name, None)
            if callable(handler):
                result = handler(text)
                response_text = _apple_voice_extract_text(result)
                if response_text:
                    return response_text, _apple_voice_extract_agent(result)
    except Exception as exc:
        logger.warning("apple_voice_local_handler failed: %s", exc)

    normalized = text.strip().lower()
    if _APPLE_VOICE_CALENDAR_RE.search(normalized) and _APPLE_VOICE_TODAY_RE.search(normalized):
        response_text = _apple_voice_local_schedule_summary(runtime, actor_id)
        if response_text:
            return response_text, "JARVIS"
    return None


def _apple_voice_local_llm(runtime: Any, *, actor_id: str, text: str) -> tuple[str, str]:
    try:
        from .llm_gateway import LLMMessage, get_gateway, init_gateway
    except Exception as exc:
        logger.warning("apple_voice_local_llm import failed: %s", exc)
        return (
            "The local reasoning system is not ready right now. If you want, I can escalate to a non-local model after you approve it.",
            "JARVIS",
        )

    gateway = get_gateway() or init_gateway()
    if gateway is None:
        return (
            "The local reasoning system is not initialized right now. If you want, I can escalate to a non-local model after you approve it.",
            "JARVIS",
        )

    gateway_status = gateway.get_status()
    if not gateway_status.get("ollama_available"):
        return (
            "My local models are unavailable right now. I can use a non-local model if you approve it.",
            "JARVIS",
        )

    system_prompt = (
        "You are JARVIS speaking on Apple voice surfaces. "
        "Prefer short, direct spoken answers. "
        "Do not mention tokens, providers, models, or internal routing."
    )
    response = gateway.complete(
        [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=text),
        ],
        task_type="converse",
        agent_id="jarvis-apple-voice",
        actor_id=actor_id,
        allow_escalation=False,
    )

    if response.backend != "ollama":
        logger.warning(
            "apple_voice_local_llm blocked non-local backend=%s model=%s",
            response.backend,
            response.model_used,
        )
        return (
            "This request would need a non-local model. I can do that after you approve it.",
            "JARVIS",
        )

    if response.error:
        logger.warning("apple_voice_local_llm local error: %s", response.error)
        return (
            "My local models could not finish that request right now. I can use a non-local model if you approve it.",
            "JARVIS",
        )

    response_text = str(response.text or "").strip()
    if not response_text:
        return ("I don't have a local answer for that yet.", "JARVIS")
    return response_text, "JARVIS"


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
    log_path = _json_log_path(path)
    if log_path is not None and log_path.exists():
        try:
            last: Any = None
            for line in log_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                last = json.loads(line)
            if last is not None:
                atomic_write_json(path, last)
                return last
        except Exception as exc:
            logger.warning("apple_api.safe_read_json replay %s: %s", log_path, exc)
    return default


def _safe_write_json(path: Path, payload: Any) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        log_path = _json_log_path(path)
        if log_path is not None:
            persistence_append_jsonl(log_path, payload)
            atomic_write_json(path, payload)
        else:
            path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except Exception as exc:
        logger.warning("apple_api.safe_write_json %s: %s", path, exc)


def _json_log_path(path: Path) -> Path | None:
    if path == _NAVIGATION_STATE_PATH:
        return _NAVIGATION_STATE_LOG_PATH
    if path == _NOTIFICATION_CENTER_PATH:
        return _NOTIFICATION_CENTER_LOG_PATH
    if path == _STEWARDSHIP_REVIEW_QUEUE_PATH:
        return _STEWARDSHIP_REVIEW_QUEUE_LOG_PATH
    if path == _SIGNAL_RESOLUTIONS_PATH:
        return _SIGNAL_RESOLUTIONS_LOG_PATH
    if path == _CHRONICLE_PRAYER_ACTIVITY_PATH:
        return _CHRONICLE_PRAYER_ACTIVITY_LOG_PATH
    if path == _FOCUS_STATE_PATH:
        return _FOCUS_STATE_LOG_PATH
    if path == _APPLE_REMINDERS_PATH:
        return _APPLE_REMINDERS_LOG_PATH
    if path == _APPLE_CALENDAR_PATH:
        return _APPLE_CALENDAR_LOG_PATH
    if path == _APPLE_NOW_PLAYING_PATH:
        return _APPLE_NOW_PLAYING_LOG_PATH
    return None


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


def _load_signal_resolutions() -> dict[str, dict[str, str]]:
    payload = _safe_read_json(_SIGNAL_RESOLUTIONS_PATH, {})
    if not isinstance(payload, dict):
        return {"sound": {}, "vision": {}}
    result: dict[str, dict[str, str]] = {}
    for domain in ("sound", "vision"):
        raw = payload.get(domain)
        if isinstance(raw, dict):
            result[domain] = {str(key): str(value) for key, value in raw.items() if str(key).strip()}
        else:
            result[domain] = {}
    return result


def _mark_signal_resolved(domain: str, item_id: str) -> str:
    key = str(item_id or "").strip()
    if not key:
        raise ValueError("signal resolution requires a non-empty id")
    payload = _load_signal_resolutions()
    resolved_at = _ts()
    bucket = payload.setdefault(domain, {})
    bucket[key] = resolved_at
    _safe_write_json(_SIGNAL_RESOLUTIONS_PATH, payload)
    return resolved_at


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


def _iso_minutes_away(value: str) -> int | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        target = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        return int((target - now).total_seconds() // 60)
    except ValueError:
        return None


def _is_recent_iso(value: str, *, minutes: int) -> bool:
    raw = str(value or "").strip()
    if not raw:
        return False
    try:
        target = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        delta = abs((now - target).total_seconds())
        return delta <= minutes * 60
    except ValueError:
        return False


def _iso_after_minutes(minutes: int) -> str:
    return datetime.now(timezone.utc).fromtimestamp(
        datetime.now(timezone.utc).timestamp() + minutes * 60
    ).isoformat()


def _local_hour() -> int:
    return datetime.now().astimezone().hour


def _compute_interruption_posture(
    *,
    watch_status: dict[str, Any],
    home_state: dict[str, Any],
    focus_payload: dict[str, Any],
) -> dict[str, Any]:
    focus_active = bool(focus_payload.get("focus_active"))
    quiet_hours = _local_hour() < 7 or _local_hour() >= 21
    alerts = home_state.get("alerts") if isinstance(home_state.get("alerts"), list) else []
    present_members = [
        str(member).strip()
        for member in (home_state.get("present_members") or [])
        if str(member).strip()
    ]
    alert_count = len(alerts)
    needs_count = int(watch_status.get("needs_count") or 0)

    mode = "active_hours"
    label = "Active hours"
    reason = "JARVIS can surface normal household attention during active hours."
    recommended_delivery = "badge_only"

    if alert_count > 0:
        mode = "household_alert"
        label = "Household alert override"
        reason = "An active home alert overrides quieter delivery modes."
        recommended_delivery = "deliver_now"
    elif focus_active:
        mode = "focus_active"
        label = "Focus active"
        reason = "Focus is active on the phone, so JARVIS should keep interruptions quieter."
        recommended_delivery = "quiet_store"
    elif quiet_hours and needs_count > 0:
        mode = "quiet_hours_attention"
        label = "Quiet hours with active attention"
        reason = "Quiet hours are active, but pending approvals should remain visible without breaking the household."
        recommended_delivery = "badge_only"
    elif quiet_hours:
        mode = "quiet_hours"
        label = "Quiet hours"
        reason = "It is outside normal household hours, so lower-priority items should wait for Brief."
        recommended_delivery = "hold_for_brief"

    return {
        "mode": mode,
        "label": label,
        "reason": reason,
        "recommended_delivery": recommended_delivery,
        "focus_active": focus_active,
        "quiet_hours": quiet_hours,
        "hour_local": _local_hour(),
        "needs_count": needs_count,
        "alert_count": alert_count,
        "present_members": present_members,
        "updated_at": _ts(),
    }


def _choose_delivery_mode(
    *,
    default_mode: str,
    severity: str,
    category: str,
    posture: dict[str, Any],
) -> tuple[str, str]:
    posture_mode = str(posture.get("mode") or "active_hours")
    posture_reason = str(posture.get("reason") or "")
    normalized_severity = str(severity or "low").lower()
    normalized_category = str(category or "system").lower()

    if posture_mode == "household_alert":
        return "deliver_now", posture_reason

    if posture_mode == "focus_active":
        if normalized_severity in {"high", "critical"} or normalized_category in {"approval", "household"}:
            return "badge_only", "Focus is active, but this item stays visible because it affects live household flow."
        return "quiet_store", posture_reason

    if posture_mode in {"quiet_hours", "quiet_hours_attention"}:
        if normalized_severity in {"high", "critical"}:
            return "badge_only", "Quiet hours are active, but higher-severity items remain visible."
        if normalized_category == "approval":
            return "badge_only", "Quiet hours are active, but approvals remain visible for morning command flow."
        return "hold_for_brief", posture_reason

    if normalized_severity == "critical":
        return "deliver_now", "Critical items should break through during active hours."

    return str(default_mode or "badge_only"), posture_reason or "Normal household hours allow standard delivery."


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


def _chronicle_entry_id(entry: dict[str, Any]) -> str:
    return str(entry.get("entry_id") or entry.get("id") or uuid.uuid4())


def _chronicle_bridge_entry_to_apple(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": _chronicle_entry_id(entry),
        "type": str(entry.get("entry_type") or entry.get("type") or entry.get("theme") or "reflection"),
        "title": _truncate(str(entry.get("title") or entry.get("theme") or "Reflection"), 50),
        "body": _truncate(str(entry.get("body") or entry.get("note") or entry.get("reflection") or ""), 200),
        "scripture": entry.get("scripture_ref") or entry.get("passage") or None,
        "timestamp": str(entry.get("created_at") or entry.get("timestamp") or entry.get("date") or ""),
    }


def _load_chronicle_prayer_activity() -> dict[str, dict[str, Any]]:
    payload = _safe_read_json(_CHRONICLE_PRAYER_ACTIVITY_PATH, {})
    if not isinstance(payload, dict):
        return {}
    normalized: dict[str, dict[str, Any]] = {}
    for key, value in payload.items():
        if not str(key).strip() or not isinstance(value, dict):
            continue
        normalized[str(key)] = {
            "times_prayed": int(value.get("times_prayed") or 0),
            "last_prayed_at": str(value.get("last_prayed_at") or ""),
        }
    return normalized


def _persist_chronicle_prayer_activity(payload: dict[str, dict[str, Any]]) -> None:
    _safe_write_json(_CHRONICLE_PRAYER_ACTIVITY_PATH, payload)


def _load_chronicle_answered_prayers() -> dict[str, dict[str, Any]]:
    items = _safe_read_jsonl(_CHRONICLE_ANSWERED_PRAYERS_PATH)
    answered: dict[str, dict[str, Any]] = {}
    for item in items:
        prayer_id = str(item.get("id") or item.get("entry_id") or "").strip()
        if prayer_id:
            answered[prayer_id] = item
    return answered


def _enrich_chronicle_prayers(prayers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    activity = _load_chronicle_prayer_activity()
    answered = _load_chronicle_answered_prayers()
    enriched: list[dict[str, Any]] = []
    for prayer in prayers:
        if not isinstance(prayer, dict):
            continue
        prayer_id = str(prayer.get("id") or uuid.uuid4())
        activity_state = activity.get(prayer_id, {})
        answered_state = answered.get(prayer_id, {})
        enriched.append(
            {
                "id": prayer_id,
                "text": str(prayer.get("text") or "").strip(),
                "category": str(prayer.get("category") or "Prayer"),
                "times_prayed": int(activity_state.get("times_prayed") or 0),
                "last_prayed_at": str(activity_state.get("last_prayed_at") or ""),
                "answered": True if answered_state else _boolish(prayer.get("answered")),
                "answer_summary": str(answered_state.get("answerSummary") or answered_state.get("answer_summary") or ""),
            }
        )
    return enriched


def _chronicle_study_workspace(context: dict[str, Any]) -> dict[str, Any] | None:
    study = context.get("study")
    if not isinstance(study, dict):
        return None
    passage = str(study.get("passage") or "").strip()
    title = str(study.get("title") or "").strip()
    date = str(study.get("date") or "").strip()
    top_themes = context.get("top_themes") if isinstance(context.get("top_themes"), list) else []
    rhythm = context.get("todays_rhythm") if isinstance(context.get("todays_rhythm"), dict) else {}
    focus_summary = str(rhythm.get("description") or "").strip()
    theme_hint = str(top_themes[0] if top_themes else "today's formation")
    prompts = [
        f"What word or phrase stands out in {passage or 'this passage'}?",
        f"How does this speak into {theme_hint}?",
        "What is one faithful response you can carry into today?",
    ]
    return {
        "passage": passage,
        "title": title or passage or "Current Study",
        "date": date,
        "focus_summary": focus_summary,
        "prompts": prompts,
    }


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
        "active_prayers": _enrich_chronicle_prayers(active_prayers),
        "todays_rhythm": None,
        "top_themes": top_themes,
        "total_entries": len(actor_entries),
        "active_prayer_count": sum(1 for prayer in _enrich_chronicle_prayers(active_prayers) if not prayer.get("answered")),
        "answered_prayer_count": sum(1 for prayer in _enrich_chronicle_prayers(active_prayers) if prayer.get("answered")),
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


def _chronicle_continuity_signal_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


_CHRONICLE_SITUATION_CATALOG: list[dict[str, Any]] = [
    {
        "id": "stress",
        "label": "Pressure And Stress",
        "keywords": {"pressure", "stress", "anxiety", "calm", "overwhelm", "steady", "meeting", "deadline"},
    },
    {
        "id": "decision",
        "label": "Discernment And Decisions",
        "keywords": {"decision", "discernment", "wisdom", "clarity", "direction", "choose", "judgment"},
    },
    {
        "id": "formation",
        "label": "Formation And Prayer",
        "keywords": {"prayer", "scripture", "formation", "study", "devotional", "faith", "intercession"},
    },
    {
        "id": "health",
        "label": "Health And Recovery",
        "keywords": {"health", "recovery", "sleep", "energy", "rest", "wellness", "body"},
    },
    {
        "id": "family",
        "label": "Family And Stewardship",
        "keywords": {"family", "household", "stewardship", "kids", "marriage", "home", "father"},
    },
]


def _chronicle_detect_situations(
    top_themes: list[str],
    actor_entries: list[dict[str, Any]],
    relevant_facts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    recent_entries = list(reversed(actor_entries))[:6]
    signal_source = " ".join(
        [
            *top_themes,
            *[str(entry.get("title") or "") for entry in recent_entries],
            *[str(entry.get("theme") or "") for entry in recent_entries],
            *[str(entry.get("body") or entry.get("note") or entry.get("reflection") or "") for entry in recent_entries],
            *[str(fact.get("title") or "") for fact in relevant_facts],
            *[str(fact.get("summary") or "") for fact in relevant_facts],
            *[" ".join(str(tag) for tag in (fact.get("tags") or [])) for fact in relevant_facts],
        ]
    )
    signal_key = _chronicle_continuity_signal_key(signal_source)
    situations: list[dict[str, Any]] = []
    for situation in _CHRONICLE_SITUATION_CATALOG:
        keywords = {str(keyword).strip().lower() for keyword in (situation.get("keywords") or set()) if str(keyword).strip()}
        hits = [keyword for keyword in sorted(keywords) if keyword in signal_key]
        if not hits:
            continue
        supporting_facts = [
            fact
            for fact in relevant_facts
            if any(
                keyword in _chronicle_continuity_signal_key(
                    " ".join(
                        [
                            str(fact.get("title") or ""),
                            str(fact.get("summary") or ""),
                            " ".join(str(tag) for tag in (fact.get("tags") or [])),
                        ]
                    )
                )
                for keyword in hits
            )
        ]
        situations.append(
            {
                "id": str(situation.get("id") or ""),
                "label": str(situation.get("label") or "Situation"),
                "summary": (
                    f"JARVIS sees this as a {str(situation.get('label') or 'situation').lower()} moment"
                    f" based on signals like {', '.join(hits[:3])}."
                ),
                "signals": hits[:4],
                "matched_fact_count": len(supporting_facts),
            }
        )
    situations.sort(key=lambda item: (-int(item.get("matched_fact_count") or 0), -len(item.get("signals") or []), str(item.get("label") or "")))
    return situations[:3]


def _chronicle_continuity_packet(
    actor: str,
    raw_entries: list[dict[str, Any]],
    context: dict[str, Any] | None,
) -> dict[str, Any]:
    try:
        viewer = runtime.get_actor(actor)
        facts = runtime.memory_support.profile_facts(viewer, subject_user_id=viewer.user_id)
    except Exception:
        facts = []

    top_themes = []
    if isinstance(context, dict):
        top_themes = [str(item).strip().lower() for item in (context.get("top_themes") or []) if str(item).strip()]
    actor_entries = [entry for entry in raw_entries if _chronicle_actor_matches(entry, actor)]
    recent_entries = list(reversed(actor_entries))[:6]
    token_source = " ".join(
        [
            *top_themes,
            *[str(entry.get("title") or "") for entry in recent_entries],
            *[str(entry.get("theme") or "") for entry in recent_entries],
            *[str(entry.get("scripture_ref") or entry.get("passage") or "") for entry in recent_entries],
        ]
    )
    tokens = {
        token
        for token in re.findall(r"[a-z0-9]{4,}", token_source.lower())
        if token not in {"that", "with", "have", "this", "from", "your", "what", "when", "into", "today", "over"}
    }

    scored_facts: list[tuple[int, dict[str, Any]]] = []
    for item in facts:
        summary = str(item.get("summary") or "").strip()
        if not summary:
            continue
        haystack = _chronicle_continuity_signal_key(
            " ".join(
                [
                    summary,
                    str(item.get("title") or ""),
                    " ".join(str(tag) for tag in (item.get("tags") or [])),
                ]
            )
        )
        score = sum(1 for token in tokens if token in haystack)
        if top_themes and str(item.get("lane") or "") == "personal":
            score += 1
        if score:
            scored_facts.append((score, item))
    scored_facts.sort(key=lambda pair: (-pair[0], str(pair[1].get("updated_at") or "")))
    relevant_facts = [
        {
            "fact_id": str(item.get("fact_id") or ""),
            "title": str(item.get("title") or item.get("summary") or "Continuity fact"),
            "summary": str(item.get("summary") or ""),
            "lane": str(item.get("lane") or ""),
            "updated_at": str(item.get("updated_at") or ""),
            "tags": [str(tag) for tag in (item.get("tags") or [])[:4]],
        }
        for _, item in scored_facts[:4]
    ]

    matching_entries: list[dict[str, Any]] = []
    for entry in reversed(actor_entries):
        theme = str(entry.get("theme") or "").strip().lower()
        title = str(entry.get("title") or "").strip()
        body = str(entry.get("body") or entry.get("note") or entry.get("reflection") or "").strip()
        scripture = str(entry.get("scripture_ref") or entry.get("passage") or "").strip()
        haystack = _chronicle_continuity_signal_key(" ".join([theme, title, body, scripture]))
        score = sum(1 for token in tokens if token in haystack)
        if theme and theme in top_themes:
            score += 2
        if score <= 0:
            continue
        matching_entries.append(
            {
                "score": score,
                "entry": {
                    "id": str(entry.get("entry_id") or entry.get("id") or uuid.uuid4()),
                    "type": str(entry.get("entry_type") or entry.get("type") or entry.get("theme") or "reflection"),
                    "title": _truncate(title or entry.get("theme") or "Reflection", 50),
                    "body": _truncate(body, 200),
                    "scripture": scripture or None,
                    "timestamp": str(entry.get("created_at") or entry.get("timestamp") or ""),
                },
            }
        )
    matching_entries.sort(key=lambda item: (-int(item.get("score") or 0), str(item["entry"].get("timestamp") or "")))
    similar_entries = [item["entry"] for item in matching_entries[:3]]
    situations = _chronicle_detect_situations(top_themes, actor_entries, relevant_facts)

    prompt_bits = []
    if top_themes:
        prompt_bits.append(f"Recall how {actor.title()} has been walking through {top_themes[0]}.")
    if situations:
        prompt_bits.append(f"This looks most like a {str(situations[0].get('label') or 'continuity').lower()} moment.")
    if relevant_facts:
        prompt_bits.append(f"Carry forward: {relevant_facts[0]['summary']}")
    if similar_entries:
        prompt_bits.append(f"Similar prior entry: {similar_entries[0]['title']}")

    return {
        "relevant_facts": relevant_facts,
        "similar_entries": similar_entries,
        "situations": situations,
        "recall_prompt": " ".join(prompt_bits).strip(),
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


def _build_home_ops_summary() -> dict[str, Any]:
    summary: dict[str, Any] = {
        "email": {
            "gmail_unread": 0,
            "outlook_unread": 0,
            "total_unread": 0,
            "flagged_total": 0,
        },
        "tasks": {
            "open_count": 0,
            "overdue_count": 0,
            "due_today_count": 0,
            "due_this_week_count": 0,
            "top_titles": [],
        },
        "calendar": {
            "today_count": 0,
            "upcoming_count": 0,
            "next_title": "",
            "next_start": "",
            "next_location": "",
        },
        "projects": {
            "active_count": 0,
            "stalled_count": 0,
            "total_count": 0,
            "top_titles": [],
            "unclassified_signal_count": 0,
        },
        "sync": {
            "connected_sources": [],
            "attention_sources": [],
        },
    }

    try:
        from .home_projects import get_home_db

        db = get_home_db()
        if db is None:
            return summary

        dashboard = db.get_dashboard_data() or {}
        email_stats = db.get_email_stats() or {}
        today_tasks = db.get_tasks_due_today() or []
        overdue_tasks = db.get_overdue_tasks() or []
        upcoming_events = db.get_upcoming_events(7) or []
        active_projects = db.list_projects(status="active") or []
        sync_states = db.get_all_sync_states() or []

        gmail_stats = email_stats.get("gmail") if isinstance(email_stats, dict) else {}
        outlook_stats = email_stats.get("outlook") if isinstance(email_stats, dict) else {}
        dashboard_tasks = dashboard.get("tasks") if isinstance(dashboard, dict) else {}
        dashboard_calendar = dashboard.get("calendar") if isinstance(dashboard, dict) else {}
        dashboard_projects = dashboard.get("projects") if isinstance(dashboard, dict) else {}
        dashboard_signals = dashboard.get("signals") if isinstance(dashboard, dict) else {}

        summary["email"] = {
            "gmail_unread": int((gmail_stats or {}).get("unread") or 0),
            "outlook_unread": int((outlook_stats or {}).get("unread") or 0),
            "total_unread": int(((gmail_stats or {}).get("unread") or 0) + ((outlook_stats or {}).get("unread") or 0)),
            "flagged_total": int(((gmail_stats or {}).get("flagged") or 0) + ((outlook_stats or {}).get("flagged") or 0)),
        }
        summary["tasks"] = {
            "open_count": int((dashboard_tasks or {}).get("total_open") or 0),
            "overdue_count": int((dashboard_tasks or {}).get("overdue") or 0),
            "due_today_count": int((dashboard_tasks or {}).get("due_today") or 0),
            "due_this_week_count": int((dashboard_tasks or {}).get("due_this_week") or 0),
            "top_titles": [
                str(task.get("title") or "").strip()
                for task in (today_tasks[:2] + overdue_tasks[:2])
                if isinstance(task, dict) and str(task.get("title") or "").strip()
            ][:4],
        }
        next_event = next((event for event in upcoming_events if isinstance(event, dict)), {})
        summary["calendar"] = {
            "today_count": int((dashboard_calendar or {}).get("today_count") or 0),
            "upcoming_count": len([event for event in upcoming_events if isinstance(event, dict)]),
            "next_title": str(next_event.get("title") or ""),
            "next_start": str(next_event.get("start_time") or next_event.get("start") or ""),
            "next_location": str(next_event.get("location") or ""),
        }
        summary["projects"] = {
            "active_count": int((dashboard_projects or {}).get("active") or 0),
            "stalled_count": int((dashboard_projects or {}).get("stalled") or 0),
            "total_count": int((dashboard_projects or {}).get("total") or 0),
            "top_titles": [
                str(project.get("title") or "").strip()
                for project in active_projects[:4]
                if isinstance(project, dict) and str(project.get("title") or "").strip()
            ],
            "unclassified_signal_count": int((dashboard_signals or {}).get("unclassified_count") or 0),
        }
        summary["sync"] = {
            "connected_sources": [
                str(item.get("source") or "").strip()
                for item in sync_states
                if isinstance(item, dict) and str(item.get("status") or "").strip().lower() == "ok" and str(item.get("source") or "").strip()
            ][:4],
            "attention_sources": [
                str(item.get("source") or "").strip()
                for item in sync_states
                if isinstance(item, dict) and str(item.get("status") or "").strip().lower() not in {"", "ok"} and str(item.get("source") or "").strip()
            ][:4],
        }
    except Exception as exc:
        logger.warning("apple_api.build_home_ops_summary: %s", exc)

    return summary


def _apple_calendar_events(payload: dict[str, Any]) -> list[dict[str, Any]]:
    events = payload.get("events") if isinstance(payload, dict) else []
    if not isinstance(events, list):
        return []
    normalized = [event for event in events if isinstance(event, dict)]
    normalized.sort(key=lambda item: str(item.get("start") or ""))
    return normalized


def _apple_calendar_event_id(event: dict[str, Any]) -> str:
    explicit = str(event.get("id") or "").strip()
    if explicit:
        return explicit
    title = str(event.get("title") or "").strip()
    start = str(event.get("start") or "").strip()
    location = str(event.get("location") or "").strip()
    return f"{title}|{start}|{location}"


def _apple_calendar_event_record(event: dict[str, Any]) -> dict[str, Any]:
    start = str(event.get("start") or "").strip()
    minutes_away = _iso_minutes_away(start)
    return {
        "id": _apple_calendar_event_id(event),
        "title": str(event.get("title") or "").strip(),
        "start": start,
        "end": str(event.get("end") or "").strip(),
        "location": str(event.get("location") or "").strip(),
        "calendar": str(event.get("calendar") or "").strip(),
        "notes": str(event.get("notes") or "").strip(),
        "url": str(event.get("url") or "").strip(),
        "all_day": bool(event.get("all_day")),
        "minutes_away": minutes_away,
        "prep_window_open": minutes_away is not None and -60 <= minutes_away <= 24 * 60,
        "route_ready": bool(str(event.get("location") or "").strip()),
    }


def _apple_find_calendar_event(payload: dict[str, Any], event_id: str) -> dict[str, Any] | None:
    target = str(event_id or "").strip()
    if not target:
        return None
    for event in _apple_calendar_events(payload):
        if _apple_calendar_event_id(event) == target:
            return event
    return None


def _build_apple_calendar_state(payload: dict[str, Any]) -> dict[str, Any]:
    events = _apple_calendar_events(payload)
    next_events = [_apple_calendar_event_record(event) for event in events[:5]]
    today_events = [
        _apple_calendar_event_record(event)
        for event in events
        if (_iso_date_days_away(str(event.get("start") or "").strip()) or 0) == 0
    ][:6]

    route_sensitive_events = [
        record for record in next_events
        if record["route_ready"] and record["minutes_away"] is not None and -60 <= int(record["minutes_away"]) <= 24 * 60
    ][:4]

    preparation_cues: list[dict[str, Any]] = []
    attention_flags: list[dict[str, Any]] = []
    for record in next_events:
        title = str(record.get("title") or "Upcoming event")
        start = str(record.get("start") or "")
        location = str(record.get("location") or "")
        minutes_away = record.get("minutes_away")
        if minutes_away is None:
            continue
        if -60 <= int(minutes_away) <= 180:
            preparation_cues.append(
                {
                    "event_id": record["id"],
                    "title": title,
                    "detail": f"Prep for {title}" + (f" at {location}" if location else ""),
                    "action": "prepare",
                    "start": start,
                    "location": location,
                }
            )
            attention_flags.append(
                {
                    "id": f"prep:{record['id']}",
                    "event_id": record["id"],
                    "kind": "prep_window",
                    "severity": "medium" if int(minutes_away) <= 120 else "low",
                    "title": f"Prep window open for {title}",
                    "detail": "This event is close enough that JARVIS can stage preparation now.",
                }
            )
        if location and -30 <= int(minutes_away) <= 6 * 60:
            attention_flags.append(
                {
                    "id": f"route:{record['id']}",
                    "event_id": record["id"],
                    "kind": "route_ready",
                    "severity": "medium",
                    "title": f"Route planning ready for {title}",
                    "detail": "This event has a location and is within the route-planning window.",
                }
            )

    return {
        "synced": bool(payload),
        "synced_at": str(payload.get("synced_at") or "") if isinstance(payload, dict) else "",
        "count": int(payload.get("count") or len(events)) if isinstance(payload, dict) else len(events),
        "next_events": next_events,
        "today_events": today_events,
        "route_sensitive_events": route_sensitive_events,
        "preparation_cues": preparation_cues[:5],
        "attention_flags": attention_flags[:6],
    }


def _apple_reminder_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    reminders = payload.get("reminders") if isinstance(payload, dict) else []
    if not isinstance(reminders, list):
        return []
    open_items = [
        reminder for reminder in reminders
        if isinstance(reminder, dict) and not bool(reminder.get("completed"))
    ]
    open_items.sort(
        key=lambda item: (
            _iso_minutes_away(str(item.get("due") or "").strip()) is None,
            _iso_minutes_away(str(item.get("due") or "").strip()) or 0,
            -_coerce_int(item.get("priority"), 0),
            str(item.get("title") or ""),
        )
    )
    return open_items


def _apple_reminder_record(reminder: dict[str, Any]) -> dict[str, Any]:
    due = str(reminder.get("due") or "").strip()
    minutes_away = _iso_minutes_away(due)
    priority = _coerce_int(reminder.get("priority"), 0)
    if priority >= 8:
        priority_label = "high"
    elif priority <= 2:
        priority_label = "low"
    else:
        priority_label = "normal"
    return {
        "id": str(reminder.get("id") or "").strip(),
        "title": str(reminder.get("title") or "").strip(),
        "due": due,
        "list": str(reminder.get("list") or "").strip(),
        "priority": priority,
        "priority_label": priority_label,
        "notes": str(reminder.get("notes") or "").strip(),
        "minutes_away": minutes_away,
        "overdue": minutes_away is not None and minutes_away < 0,
        "due_soon": minutes_away is not None and 0 <= minutes_away <= 4 * 60,
        "completed": bool(reminder.get("completed")),
        "available_actions": ["complete", "snooze_1h"],
    }


def _build_apple_reminders_state(payload: dict[str, Any]) -> dict[str, Any]:
    reminders = _apple_reminder_items(payload)
    records = [_apple_reminder_record(reminder) for reminder in reminders]
    overdue_items = [record for record in records if record["overdue"]][:6]
    due_soon_items = [record for record in records if record["due_soon"]][:6]
    priority_items = [record for record in records if record["priority"] >= 7][:6]
    no_due_date_count = sum(1 for record in records if not str(record.get("due") or "").strip())

    list_buckets: dict[str, dict[str, Any]] = {}
    for record in records:
        list_title = str(record.get("list") or "").strip() or "General"
        bucket = list_buckets.setdefault(
            list_title.lower(),
            {
                "id": list_title.lower().replace(" ", "-"),
                "title": list_title,
                "count": 0,
                "overdue_count": 0,
                "due_soon_count": 0,
                "priority_count": 0,
            },
        )
        bucket["count"] += 1
        if record["overdue"]:
            bucket["overdue_count"] += 1
        if record["due_soon"]:
            bucket["due_soon_count"] += 1
        if record["priority"] >= 7:
            bucket["priority_count"] += 1
    list_summaries = sorted(
        list_buckets.values(),
        key=lambda item: (
            -int(item.get("overdue_count") or 0),
            -int(item.get("due_soon_count") or 0),
            -int(item.get("priority_count") or 0),
            -int(item.get("count") or 0),
            str(item.get("title") or ""),
        ),
    )[:6]

    attention_flags: list[dict[str, Any]] = []
    if overdue_items:
        first = overdue_items[0]
        attention_flags.append(
            {
                "id": f"overdue:{first['id']}",
                "reminder_id": first["id"],
                "kind": "overdue",
                "severity": "high",
                "title": f"Overdue reminder: {first['title'] or 'Reminder'}",
                "detail": "This reminder is already overdue and should be resolved or deferred.",
            }
        )
    if due_soon_items:
        first = due_soon_items[0]
        attention_flags.append(
            {
                "id": f"due_soon:{first['id']}",
                "reminder_id": first["id"],
                "kind": "due_soon",
                "severity": "medium",
                "title": f"Due soon: {first['title'] or 'Reminder'}",
                "detail": "This reminder is inside the active household window.",
            }
        )
    if len(priority_items) >= 2:
        attention_flags.append(
            {
                "id": "priority-bundle",
                "reminder_id": "",
                "kind": "priority_load",
                "severity": "medium",
                "title": f"{len(priority_items)} high-priority reminders are open",
                "detail": "Priority reminder load is high enough to surface in command surfaces.",
            }
        )

    return {
        "synced": bool(payload),
        "synced_at": str(payload.get("synced_at") or "") if isinstance(payload, dict) else "",
        "count": int(payload.get("count") or len(reminders)) if isinstance(payload, dict) else len(reminders),
        "summary": {
            "open_count": len(records),
            "overdue_count": len(overdue_items),
            "due_soon_count": len(due_soon_items),
            "priority_count": len(priority_items),
            "no_due_date_count": no_due_date_count,
        },
        "list_summaries": list_summaries,
        "open_items": records[:8],
        "overdue_items": overdue_items,
        "due_soon_items": due_soon_items,
        "priority_items": priority_items,
        "attention_flags": attention_flags[:6],
    }


def _build_apple_focus_state(
    *,
    focus_payload: dict[str, Any],
    posture: dict[str, Any],
) -> dict[str, Any]:
    focus_active = bool(focus_payload.get("focus_active"))
    source = str(focus_payload.get("source") or "")
    updated_at = str(focus_payload.get("updated_at") or "")
    jarvis_mode = str(focus_payload.get("jarvis_mode") or "morning_brief")
    hold_approvals = bool(focus_payload.get("hold_approvals"))
    silence_briefings = bool(focus_payload.get("silence_briefings"))
    recommended_delivery = str(posture.get("recommended_delivery") or "")
    posture_label = str(posture.get("label") or "")
    suppression_rules = [
        {
            "id": "focus_active_quiet_store",
            "title": "Focus reduces proactive interruptions",
            "detail": "Non-urgent notifications should stay quiet while Focus is active.",
            "active": focus_active and recommended_delivery == "quiet_store",
        },
        {
            "id": "quiet_hours_hold_for_brief",
            "title": "Quiet hours hold lower-priority items for Brief",
            "detail": "During quiet hours, lower-priority items should wait for the next command surface.",
            "active": bool(posture.get("quiet_hours")) and recommended_delivery == "hold_for_brief",
        },
        {
            "id": "household_alert_override",
            "title": "Household alerts can break through",
            "detail": "Live household alerts override quieter delivery modes.",
            "active": str(posture.get("mode") or "") == "household_alert",
        },
        {
            "id": "approvals_badge_only",
            "title": "Approvals stay visible without becoming noisy",
            "detail": "Approvals remain visible even when JARVIS is being quieter.",
            "active": recommended_delivery in {"badge_only", "quiet_store", "hold_for_brief"},
        },
    ]
    routing_lanes = [
        {
            "id": "approvals_lane",
            "title": "Approvals",
            "detail": (
                "Approvals stay visible without buzzing during focus."
                if hold_approvals or recommended_delivery in {"badge_only", "quiet_store", "hold_for_brief"}
                else "Approvals can flow normally during active hours."
            ),
            "delivery_mode": "badge_only" if hold_approvals or focus_active else recommended_delivery or "badge_only",
            "active": hold_approvals or focus_active or bool(posture.get("quiet_hours")),
        },
        {
            "id": "briefings_lane",
            "title": "Briefings",
            "detail": (
                "Proactive briefings stay held for a calmer command surface."
                if silence_briefings or bool(posture.get("quiet_hours"))
                else "Briefings can surface normally."
            ),
            "delivery_mode": "hold_for_brief" if silence_briefings or bool(posture.get("quiet_hours")) else recommended_delivery or "badge_only",
            "active": silence_briefings or bool(posture.get("quiet_hours")),
        },
        {
            "id": "routine_lane",
            "title": "Routine Notifications",
            "detail": (
                "Routine household items stay quiet while focus is active."
                if focus_active
                else "Routine household items follow the current household posture."
            ),
            "delivery_mode": recommended_delivery or "badge_only",
            "active": True,
        },
        {
            "id": "household_alert_lane",
            "title": "Household Alerts",
            "detail": "Urgent household alerts can break through quieter modes when needed.",
            "delivery_mode": "deliver_now" if str(posture.get("mode") or "") == "household_alert" else "badge_only",
            "active": True,
        },
    ]
    presets = [
        {
            "id": "open_household",
            "title": "Open Household",
            "detail": "Normal delivery with no quieting overrides.",
            "focus_active": False,
            "jarvis_mode": "morning_brief",
            "hold_approvals": False,
            "silence_briefings": False,
            "active": not focus_active and not hold_approvals and not silence_briefings,
        },
        {
            "id": "work_focus",
            "title": "Work Focus",
            "detail": "Keep routine traffic quiet, but leave approvals visible.",
            "focus_active": True,
            "jarvis_mode": "work",
            "hold_approvals": True,
            "silence_briefings": False,
            "active": focus_active and jarvis_mode == "work" and hold_approvals and not silence_briefings,
        },
        {
            "id": "meeting_quiet",
            "title": "Meeting Quiet",
            "detail": "Hold approvals and proactive briefings during heads-down time.",
            "focus_active": True,
            "jarvis_mode": "personal",
            "hold_approvals": True,
            "silence_briefings": True,
            "active": focus_active and jarvis_mode == "personal" and hold_approvals and silence_briefings,
        },
        {
            "id": "sleep_guard",
            "title": "Sleep Guard",
            "detail": "Reserve interruptions for the household path only.",
            "focus_active": True,
            "jarvis_mode": "sleep",
            "hold_approvals": True,
            "silence_briefings": True,
            "active": focus_active and jarvis_mode == "sleep" and hold_approvals and silence_briefings,
        },
    ]
    return {
        "focus_active": focus_active,
        "updated_at": updated_at,
        "source": source,
        "source_fresh": _is_recent_timestamp(updated_at, minutes=180),
        "interruption_posture": posture,
        "suppression_rules": suppression_rules,
        "filter": {
            "jarvis_mode": jarvis_mode,
            "hold_approvals": hold_approvals,
            "silence_briefings": silence_briefings,
            "source": source or "device",
        },
        "routing_lanes": routing_lanes,
        "presets": presets,
        "summary": {
            "label": posture_label or ("Focus active" if focus_active else "Focus inactive"),
            "detail": (
                str(posture.get("reason") or "")
                or "JARVIS is using the current device posture to route interruptions."
            ),
            "recommended_delivery": recommended_delivery,
        },
    }


def _build_apple_sound_state(rows: list[dict[str, Any]]) -> dict[str, Any]:
    resolved = _load_signal_resolutions().get("sound", {})
    recent_rows = [row for row in rows if isinstance(row, dict)]
    recent_rows.sort(key=lambda item: str(item.get("received_at") or ""), reverse=True)
    recent_items = [
        {
            "id": str(row.get("received_at") or row.get("timestamp") or f"sound-{index}"),
            "label": str(row.get("classification") or row.get("label") or row.get("sound") or "").strip(),
            "detail": str(row.get("detail") or row.get("summary") or "").strip(),
            "source": str(row.get("source") or "").strip(),
            "confidence": _coerce_float(row.get("confidence"), 0.0),
            "received_at": str(row.get("received_at") or ""),
            "resolved": str(row.get("received_at") or row.get("timestamp") or f"sound-{index}") in resolved,
            "resolved_at": resolved.get(str(row.get("received_at") or row.get("timestamp") or f"sound-{index}"), ""),
        }
        for index, row in enumerate(recent_rows[:12])
    ]
    high_confidence_items = [
        item for item in recent_items
        if _coerce_float(item.get("confidence"), 0.0) >= 0.7 and not bool(item.get("resolved"))
    ][:6]
    attention_flags: list[dict[str, Any]] = []
    if high_confidence_items:
        first = high_confidence_items[0]
        attention_flags.append(
            {
                "id": f"sound:{first['id']}",
                "kind": "high_confidence",
                "severity": "medium",
                "title": first["label"] or "Sound alert",
                "detail": first["detail"] or "High-confidence sound activity was captured.",
            }
        )
    primary_label = str((high_confidence_items[0]["label"] if high_confidence_items else "") or "").lower()
    primary_source = str((high_confidence_items[0]["source"] if high_confidence_items else "") or "").strip()
    is_security_signal = any(token in primary_label for token in ("doorbell", "knock", "glass", "alarm", "siren", "smoke"))
    is_household_signal = any(token in primary_label for token in ("baby", "cry", "dog"))
    policy_rules = [
        {
            "id": "high_confidence_security_triage",
            "title": "High-confidence security sounds stay visible",
            "detail": "Door, glass, alarm, and siren detections should route into the security lane even during quieter command posture.",
            "delivery_mode": "deliver_now" if is_security_signal else "badge_only",
            "active": is_security_signal,
        },
        {
            "id": "routine_sound_review_queue",
            "title": "Routine sounds queue for review",
            "detail": "Lower-risk sounds should be captured, tagged, and reviewed without creating unnecessary interruption noise.",
            "delivery_mode": "badge_only",
            "active": any(not bool(item.get("resolved")) for item in recent_items),
        },
        {
            "id": "resolved_sounds_drop_out",
            "title": "Resolved sounds drop out of the active queue",
            "detail": "Once acknowledged, sound alerts stay visible in history but stop contributing to the active attention stack.",
            "delivery_mode": "quiet_store",
            "active": any(bool(item.get("resolved")) for item in recent_items),
        },
    ]
    response_plans = [
        {
            "id": "sound-plan-security",
            "title": "Security Follow-up",
            "detail": (
                f"Route this sound through security review and camera context for {primary_source or 'the affected zone'}."
                if is_security_signal
                else "Keep the next security-related sound ready for camera or lock review if confidence stays high."
            ),
            "target": "security",
            "priority": "high" if is_security_signal else "medium",
            "active": is_security_signal,
        },
        {
            "id": "sound-plan-household",
            "title": "Household Follow-up",
            "detail": (
                "Treat the current sound as a household support event and keep it visible without escalating to an alarm posture."
                if is_household_signal
                else "Use the household lane for comfort, child, or pet-related sounds when they appear."
            ),
            "target": "household",
            "priority": "medium",
            "active": is_household_signal,
        },
        {
            "id": "sound-plan-review-brief",
            "title": "Brief Queue Review",
            "detail": "Any unresolved sound should stay in the next command review until it is either resolved or escalated.",
            "target": "brief",
            "priority": "medium" if high_confidence_items else "low",
            "active": any(not bool(item.get("resolved")) for item in recent_items),
        },
    ]
    return {
        "count": len(recent_rows),
        "recent_items": recent_items,
        "high_confidence_items": high_confidence_items,
        "attention_flags": attention_flags,
        "policy_rules": policy_rules,
        "response_plans": response_plans,
    }


def _build_apple_vision_state(rows: list[dict[str, Any]]) -> dict[str, Any]:
    resolved = _load_signal_resolutions().get("vision", {})
    recent_rows = [row for row in rows if isinstance(row, dict)]
    recent_rows.sort(key=lambda item: str(item.get("received_at") or ""), reverse=True)
    recent_items = [
        {
            "id": str(row.get("received_at") or f"vision-{index}"),
            "context": str(row.get("context") or "").strip(),
            "source": str(row.get("source") or "").strip(),
            "text_preview": str(row.get("text") or "")[:180],
            "received_at": str(row.get("received_at") or ""),
            "resolved": str(row.get("received_at") or f"vision-{index}") in resolved,
            "resolved_at": resolved.get(str(row.get("received_at") or f"vision-{index}"), ""),
        }
        for index, row in enumerate(recent_rows[:12])
    ]
    contexts = []
    for item in recent_items:
        context = item["context"] or "Scan"
        if context not in contexts:
            contexts.append(context)
    attention_flags: list[dict[str, Any]] = []
    unresolved_items = [item for item in recent_items if not bool(item.get("resolved"))]
    if unresolved_items:
        first = unresolved_items[0]
        attention_flags.append(
            {
                "id": f"vision:{first['id']}",
                "kind": "recent_capture",
                "severity": "low",
                "title": first["context"] or "Vision scan",
                "detail": first["text_preview"] or "A new vision scan was captured.",
            }
        )
    primary_context = str((unresolved_items[0]["context"] if unresolved_items else "") or "").lower()
    primary_source = str((unresolved_items[0]["source"] if unresolved_items else "") or "").strip()
    preview_text = str((unresolved_items[0]["text_preview"] if unresolved_items else "") or "").lower()
    is_entryway_context = any(token in primary_context for token in ("porch", "door", "entry", "garage", "driveway"))
    is_package_signal = "package" in preview_text
    is_document_signal = any(token in preview_text for token in ("invoice", "label", "receipt", "bill", "tracking"))
    policy_rules = [
        {
            "id": "entryway_captures_escalate",
            "title": "Entryway captures stay reviewable",
            "detail": "Porch, door, garage, and driveway captures should stay visible until someone reviews or resolves them.",
            "delivery_mode": "badge_only",
            "active": is_entryway_context,
        },
        {
            "id": "package_context_routes_household",
            "title": "Package context routes into household follow-up",
            "detail": "Package-like captures should route into the household lane so delivery context is easy to review.",
            "delivery_mode": "hold_for_brief" if is_package_signal else "badge_only",
            "active": is_package_signal,
        },
        {
            "id": "document_text_routes_review",
            "title": "Readable document captures queue for review",
            "detail": "OCR-like captures with labels, receipts, or bills should stay queued for a later command review.",
            "delivery_mode": "hold_for_brief",
            "active": is_document_signal,
        },
    ]
    response_plans = [
        {
            "id": "vision-plan-security",
            "title": "Security Follow-up",
            "detail": (
                f"Keep {primary_source or 'this camera'} visible in the security lane until the entryway capture is reviewed."
                if is_entryway_context
                else "Use the security lane for porch, driveway, or entry captures when they appear."
            ),
            "target": "security",
            "priority": "high" if is_entryway_context else "medium",
            "active": is_entryway_context,
        },
        {
            "id": "vision-plan-household",
            "title": "Household Follow-up",
            "detail": (
                "Treat this as a household delivery capture and keep it visible in the next brief until someone acknowledges it."
                if is_package_signal
                else "Use the household lane for delivery-style captures and home context reviews."
            ),
            "target": "household",
            "priority": "medium",
            "active": is_package_signal,
        },
        {
            "id": "vision-plan-review-brief",
            "title": "Review Queue",
            "detail": "Any unresolved vision capture should stay available in the next command review until it is resolved or promoted.",
            "target": "brief",
            "priority": "medium" if unresolved_items else "low",
            "active": bool(unresolved_items),
        },
    ]
    return {
        "count": len(recent_rows),
        "recent_items": recent_items,
        "recent_contexts": contexts[:6],
        "attention_flags": attention_flags,
        "policy_rules": policy_rules,
        "response_plans": response_plans,
    }


def _build_apple_now_playing_state(
    payload: dict[str, Any],
    recent_events: list[dict[str, Any]],
    *,
    posture: dict[str, Any],
    focus_payload: dict[str, Any],
) -> dict[str, Any]:
    rows = [row for row in recent_events if isinstance(row, dict)]
    normalized_payload = payload if isinstance(payload, dict) else {}
    title = str(normalized_payload.get("title") or "").strip()
    artist = str(normalized_payload.get("artist") or "").strip()
    album = str(normalized_payload.get("album") or "").strip()
    is_playing = bool(normalized_payload.get("is_playing"))
    updated_at = str(normalized_payload.get("updated_at") or "")
    combined = " ".join(part for part in (title, artist, album) if part).lower()
    focus_active = bool((focus_payload or {}).get("focus_active"))
    quiet_hours = bool(posture.get("quiet_hours"))
    posture_mode = str(posture.get("mode") or "active_hours")
    jarvis_mode = str((focus_payload or {}).get("jarvis_mode") or "")
    looks_ambient = any(
        token in combined
        for token in ("ambient", "focus", "lofi", "instrumental", "sleep", "calm", "brown noise", "white noise", "rain")
    )
    looks_spoken = any(
        token in combined
        for token in ("podcast", "audiobook", "news", "talk", "brief")
    )
    recent_items = [
        {
            "id": str(row.get("id") or f"media-{index}"),
            "title": str(row.get("title") or "").strip(),
            "detail": str(row.get("detail") or "").strip(),
            "ts": str(row.get("ts") or ""),
            "is_playing": bool((row.get("metadata") or {}).get("is_playing")),
            "artist": str((row.get("metadata") or {}).get("artist") or "").strip(),
            "album": str((row.get("metadata") or {}).get("album") or "").strip(),
        }
        for index, row in enumerate(rows[:10])
    ]
    routing_rules = [
        {
            "id": "focus_media_quiet_lane",
            "title": "Focus media stays non-disruptive",
            "detail": (
                "When focus is active, ambient or instrumental playback should stay steady while spoken interruptions route elsewhere."
                if is_playing
                else "When focus is active, new spoken media should wait until JARVIS leaves heads-down mode."
            ),
            "delivery_mode": "quiet_store" if focus_active else "badge_only",
            "active": focus_active,
        },
        {
            "id": "quiet_hours_media_hold",
            "title": "Quiet-hours playback should stay gentle",
            "detail": (
                "Quiet-hours playback should favor calm, low-interruption media and keep louder follow-ups for the next Brief."
                if quiet_hours
                else "Outside quiet hours, media can follow the normal household pace."
            ),
            "delivery_mode": "hold_for_brief" if quiet_hours else "badge_only",
            "active": quiet_hours,
        },
        {
            "id": "household_alert_media_duck",
            "title": "Household alerts can override media",
            "detail": "If the home enters an alert posture, media should duck behind the household alert lane until the alert clears.",
            "delivery_mode": "deliver_now" if posture_mode == "household_alert" else "badge_only",
            "active": posture_mode == "household_alert",
        },
    ]
    response_plans = [
        {
            "id": "media-plan-preserve-focus",
            "title": "Preserve Focus Session",
            "detail": (
                "Keep the current ambient session running as the backdrop for focus work."
                if is_playing and looks_ambient
                else "When focus is active, prefer resuming an ambient or instrumental session instead of spoken media."
            ),
            "target": "focus",
            "priority": "high" if focus_active and (is_playing or looks_ambient) else "medium",
            "active": focus_active,
        },
        {
            "id": "media-plan-brief-handoff",
            "title": "Brief Handoff",
            "detail": (
                "Queue media changes and spoken updates for the next Brief so they do not fragment the current household posture."
                if quiet_hours or looks_spoken
                else "Keep the next Brief aware of meaningful media changes so JARVIS can resume context cleanly."
            ),
            "target": "brief",
            "priority": "medium",
            "active": quiet_hours or looks_spoken or not is_playing,
        },
        {
            "id": "media-plan-household-scene",
            "title": "Household Scene",
            "detail": (
                "Route this playback into the broader household scene so active rooms and routines stay coordinated."
                if is_playing
                else "Use household scene routing when media returns so rooms and routines stay coordinated."
            ),
            "target": "household",
            "priority": "medium" if is_playing else "low",
            "active": is_playing or posture_mode == "household_alert",
        },
    ]
    suggested_controls = [
        {
            "id": "control-keep-session",
            "title": "Keep Session Running" if is_playing else "Resume Ambient Session",
            "detail": (
                "Maintain the current playback as the active focus bed."
                if is_playing
                else "Resume a calm ambient session when you want the room to come back online."
            ),
            "style": "primary" if is_playing else "secondary",
            "active": is_playing or looks_ambient or focus_active,
        },
        {
            "id": "control-shift-to-quiet",
            "title": "Shift to Quiet Mix",
            "detail": "Favor a calmer, lower-interruption mix during quiet hours or meeting posture.",
            "style": "secondary",
            "active": quiet_hours or jarvis_mode in {"sleep", "personal"},
        },
        {
            "id": "control-open-brief",
            "title": "Open Media Brief",
            "detail": "Use Brief to review media changes, spoken context, and what JARVIS should restore next.",
            "style": "supporting",
            "active": not is_playing or looks_spoken,
        },
    ]
    return {
        "title": title,
        "artist": artist,
        "album": album,
        "is_playing": is_playing,
        "updated_at": updated_at,
        "artwork_available": Path("data/apple/now_playing_artwork.jpg").exists(),
        "summary": {
            "label": (
                "Focus session active"
                if focus_active and is_playing
                else "Quiet-hours media posture"
                if quiet_hours
                else "Playback active"
                if is_playing
                else "Media idle"
            ),
            "detail": (
                "JARVIS is treating current playback as part of the active focus environment."
                if focus_active and is_playing
                else "JARVIS is keeping media in a quieter household lane until active hours return."
                if quiet_hours
                else "Media is live and available to household orchestration."
                if is_playing
                else "No active playback is live, so JARVIS is holding continuity through recent media state."
            ),
        },
        "routing_rules": routing_rules,
        "response_plans": response_plans,
        "suggested_controls": suggested_controls,
        "recent_items": recent_items,
    }


def _control_plane_freshness_item(
    *,
    key: str,
    label: str,
    updated_at: str,
    synced: bool,
    fresh_minutes: int,
    detail: str = "",
) -> dict[str, Any]:
    normalized_updated = str(updated_at or "").strip()
    is_fresh = _is_recent_iso(normalized_updated, minutes=fresh_minutes)
    if not synced:
        status = "not_synced"
    elif is_fresh:
        status = "fresh"
    else:
        status = "stale"
    return {
        "id": key,
        "label": label,
        "synced": synced,
        "updated_at": normalized_updated,
        "status": status,
        "detail": detail,
    }


def _build_apple_control_plane_state(*, now_playing_payload: dict[str, Any]) -> dict[str, Any]:
    data_root = Path("data/apple")
    notifications = _notification_center.list(limit=0)
    events = _event_log.recent(limit=100)
    recent_items = [
        {
            "id": str(item.get("id") or f"event-{index}"),
            "title": str(item.get("title") or "").strip(),
            "detail": str(item.get("detail") or "").strip(),
            "domain": str(item.get("domain") or "").strip(),
            "severity": str(item.get("severity") or "").strip(),
            "ts": str(item.get("ts") or "").strip(),
        }
        for index, item in enumerate(events[:8])
        if isinstance(item, dict)
    ]
    status_counts = Counter(str(item.get("status") or "unknown") for item in notifications if isinstance(item, dict))
    category_counts = Counter(str(item.get("category") or "unknown") for item in notifications if isinstance(item, dict))
    domain_counts = Counter(str(item.get("domain") or "unknown") for item in events if isinstance(item, dict))
    severity_counts = Counter(str(item.get("severity") or "unknown") for item in events if isinstance(item, dict))
    last_notification_at = str(notifications[0].get("updated_at") or notifications[0].get("created_at") or "") if notifications else ""
    last_event_at = str(events[0].get("ts") or "") if events else ""
    calendar_payload = _safe_read_json(data_root / "calendar_events.json", {})
    reminders_payload = _safe_read_json(data_root / "reminders.json", {})
    focus_payload = _safe_read_json(data_root / "focus_state.json", {})
    latest_sound = (_safe_read_jsonl_tail(data_root / "sound_alerts.jsonl", limit=1) or [{}])[0]
    latest_scan = (_safe_read_jsonl_tail(data_root / "vision_scans.jsonl", limit=1) or [{}])[0]
    freshness = [
        _control_plane_freshness_item(
            key="calendar",
            label="Calendar",
            updated_at=str(calendar_payload.get("synced_at") or ""),
            synced=bool(calendar_payload),
            fresh_minutes=24 * 60,
            detail=f"{int(calendar_payload.get('count') or 0)} events mirrored" if isinstance(calendar_payload, dict) else "",
        ),
        _control_plane_freshness_item(
            key="reminders",
            label="Reminders",
            updated_at=str(reminders_payload.get("synced_at") or ""),
            synced=bool(reminders_payload),
            fresh_minutes=24 * 60,
            detail=f"{int(reminders_payload.get('count') or 0)} reminders mirrored" if isinstance(reminders_payload, dict) else "",
        ),
        _control_plane_freshness_item(
            key="focus",
            label="Focus",
            updated_at=str(focus_payload.get("updated_at") or ""),
            synced=bool(focus_payload),
            fresh_minutes=12 * 60,
            detail=str(focus_payload.get("source") or "").strip(),
        ),
        _control_plane_freshness_item(
            key="now_playing",
            label="Now Playing",
            updated_at=str(now_playing_payload.get("updated_at") or "") if isinstance(now_playing_payload, dict) else "",
            synced=bool(now_playing_payload),
            fresh_minutes=12 * 60,
            detail=str(now_playing_payload.get("title") or "").strip() if isinstance(now_playing_payload, dict) else "",
        ),
        _control_plane_freshness_item(
            key="sound_alert",
            label="Sound",
            updated_at=str(latest_sound.get("received_at") or ""),
            synced=bool(latest_sound),
            fresh_minutes=24 * 60,
            detail=str(latest_sound.get("label") or "").strip(),
        ),
        _control_plane_freshness_item(
            key="vision_scan",
            label="Vision",
            updated_at=str(latest_scan.get("received_at") or ""),
            synced=bool(latest_scan),
            fresh_minutes=24 * 60,
            detail=str(latest_scan.get("context") or "").strip(),
        ),
        _control_plane_freshness_item(
            key="notifications",
            label="Notifications",
            updated_at=last_notification_at,
            synced=bool(notifications),
            fresh_minutes=24 * 60,
            detail=f"{len(notifications)} inbox items",
        ),
        _control_plane_freshness_item(
            key="events",
            label="Event Spine",
            updated_at=last_event_at,
            synced=bool(events),
            fresh_minutes=24 * 60,
            detail=f"{len(events)} recent events",
        ),
    ]
    return {
        "notifications": {
            "total": len(notifications),
            "pending": status_counts.get("pending", 0),
            "seen": status_counts.get("seen", 0),
            "snoozed": status_counts.get("snoozed", 0),
            "resolved": status_counts.get("resolved", 0),
            "dismissed": status_counts.get("dismissed", 0),
            "categories": dict(category_counts),
            "last_updated_at": last_notification_at,
        },
        "events": {
            "recent_count": len(events),
            "domains": dict(domain_counts),
            "severities": dict(severity_counts),
            "last_event_at": last_event_at,
            "recent_items": recent_items,
        },
        "media": {
            "synced": bool(now_playing_payload),
            "updated_at": str(now_playing_payload.get("updated_at") or "") if isinstance(now_playing_payload, dict) else "",
            "title": str(now_playing_payload.get("title") or "") if isinstance(now_playing_payload, dict) else "",
            "is_playing": bool(now_playing_payload.get("is_playing")) if isinstance(now_playing_payload, dict) else False,
        },
        "freshness": freshness,
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


def _memory_graph_long_horizon_lines(graph: dict[str, Any], limit: int = 3) -> list[str]:
    lines: list[str] = []
    horizons = graph.get("horizons") if isinstance(graph.get("horizons"), list) else []
    for item in horizons[:2]:
        if not isinstance(item, dict):
            continue
        summary = str(item.get("summary") or "").strip()
        if summary and summary not in lines:
            lines.append(summary)
    threads = graph.get("active_threads") if isinstance(graph.get("active_threads"), list) else []
    if threads:
        first = threads[0] if isinstance(threads[0], dict) else {}
        title = str(first.get("title") or "").strip()
        signal_count = int(first.get("signal_count") or 0)
        if title:
            lines.append(f"Strongest durable thread: {title} ({signal_count} signals).")
    return lines[:limit]


def _memory_graph_thread_titles(graph: dict[str, Any], limit: int = 3) -> list[str]:
    threads = graph.get("active_threads") if isinstance(graph.get("active_threads"), list) else []
    titles: list[str] = []
    for item in threads[:limit]:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        if title and title not in titles:
            titles.append(title)
    return titles[:limit]


def _build_briefing_continuity(actor: str) -> dict[str, Any]:
    try:
        viewer = runtime.get_actor(actor)
        snapshot = runtime.learning_review_snapshot(viewer.display_name, viewer.user_id) or {}
        memory_graph = runtime.durable_memory_graph_snapshot(viewer.display_name, viewer.user_id) or {}
    except Exception:
        viewer = None
        snapshot = {}
        memory_graph = {}
    if not isinstance(snapshot, dict):
        snapshot = {}
    if not isinstance(memory_graph, dict):
        memory_graph = {}

    profile = snapshot.get("profile") if isinstance(snapshot.get("profile"), dict) else {}
    personalization = snapshot.get("personalization") if isinstance(snapshot.get("personalization"), dict) else {}
    facts = snapshot.get("profile_facts") if isinstance(snapshot.get("profile_facts"), list) else []
    proposals = snapshot.get("pending_proposals") if isinstance(snapshot.get("pending_proposals"), list) else []
    first_light_history = snapshot.get("first_light_history") if isinstance(snapshot.get("first_light_history"), list) else []
    persona_snapshot = snapshot.get("persona_snapshot") if isinstance(snapshot.get("persona_snapshot"), dict) else {}
    digital_twin = persona_snapshot.get("digital_twin") if isinstance(persona_snapshot.get("digital_twin"), dict) else {}

    guidance_lines: list[str] = []
    for line in personalization.get("rhythms", []) if isinstance(personalization.get("rhythms"), list) else []:
        cleaned = str(line).strip()
        if cleaned:
            guidance_lines.append(cleaned)
    for line in personalization.get("learned_preferences", []) if isinstance(personalization.get("learned_preferences"), list) else []:
        cleaned = str(line).strip()
        if cleaned and cleaned not in guidance_lines:
            guidance_lines.append(cleaned)
    for line in digital_twin.get("likely_next_needs", []) if isinstance(digital_twin.get("likely_next_needs"), list) else []:
        cleaned = str(line).strip()
        if cleaned and cleaned not in guidance_lines:
            guidance_lines.append(cleaned)

    fact_rows = []
    for item in facts[:3]:
        if not isinstance(item, dict):
            continue
        fact_rows.append(
            {
                "id": str(item.get("fact_id") or item.get("id") or ""),
                "title": str(item.get("title") or item.get("summary") or "Continuity fact"),
                "summary": str(item.get("summary") or ""),
            }
        )

    first_light_rows = []
    for index, item in enumerate(list(reversed(first_light_history))[:3]):
        if not isinstance(item, dict):
            continue
        first_20 = item.get("first_20_minutes") if isinstance(item.get("first_20_minutes"), list) else []
        summary = str(item.get("watch_line") or "").strip()
        if not summary and first_20:
            summary = "; ".join(str(step).strip() for step in first_20[:2] if str(step).strip())
        if not summary:
            summary = "First Light continuity packet recorded."
        first_light_rows.append(
            {
                "id": str(item.get("packet_id") or item.get("date") or item.get("local_time") or f"fl-{index}"),
                "label": str(item.get("date") or item.get("local_time") or "Recent First Light"),
                "summary": summary,
            }
        )

    subject_name = str(snapshot.get("subject_display_name") or (viewer.display_name if viewer else "Chris"))
    return {
        "subject_display_name": subject_name,
        "preferred_tone": str(profile.get("preferred_tone") or ""),
        "briefing_style": str(profile.get("briefing_style") or ""),
        "profile_fact_count": len(facts),
        "pending_proposal_count": len(proposals),
        "first_light_history_count": len(first_light_history),
        "guidance_lines": guidance_lines[:4],
        "recent_profile_facts": fact_rows,
        "recent_first_light": first_light_rows,
        "long_horizon_lines": _memory_graph_long_horizon_lines(memory_graph),
        "active_threads": _memory_graph_thread_titles(memory_graph),
    }


def _build_while_you_were_away(actor: str) -> dict[str, Any]:
    try:
        report = runtime.while_you_were_away_snapshot(actor) or {}
    except Exception:
        report = {}
    if not isinstance(report, dict):
        report = {}

    def _rows(value: object) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []
        rows: list[dict[str, Any]] = []
        for item in value:
            if not isinstance(item, dict):
                continue
            rows.append(
                {
                    "id": str(item.get("id") or ""),
                    "lane": str(item.get("lane") or ""),
                    "agent": str(item.get("agent") or ""),
                    "title": str(item.get("title") or ""),
                    "summary": str(item.get("summary") or ""),
                    "timestamp": str(item.get("timestamp") or ""),
                    "status": str(item.get("status") or ""),
                }
            )
        return rows

    def _stewardship_lanes(value: object) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []
        lanes: list[dict[str, Any]] = []
        for item in value:
            if not isinstance(item, dict):
                continue
            execution = item.get("execution_primitive") if isinstance(item.get("execution_primitive"), dict) else {}
            lanes.append(
                {
                    "id": str(item.get("id") or ""),
                    "title": str(item.get("title") or ""),
                    "summary": str(item.get("summary") or ""),
                    "report_summaries": _rows(item.get("report_summaries")),
                    "prepared_work": _rows(item.get("prepared_work")),
                    "decision_cards": _rows(item.get("decision_cards")),
                    "drift_cards": _rows(item.get("drift_cards")),
                    "quiet_completions": _rows(item.get("quiet_completions")),
                    "blocked_work": _rows(item.get("blocked_work")),
                    "execution_primitive": {
                        "packet_target": str(execution.get("packet_target") or ""),
                        "review_surface": str(execution.get("review_surface") or ""),
                        "navigation_target": str(execution.get("navigation_target") or ""),
                        "action_label": str(execution.get("action_label") or ""),
                        "action_detail": str(execution.get("action_detail") or ""),
                        "route_summary": str(execution.get("route_summary") or ""),
                        "lane_status": str(execution.get("lane_status") or ""),
                        "trust_zone": str(execution.get("trust_zone") or ""),
                        "authority_stage": str(execution.get("authority_stage") or ""),
                        "arena_status": str(execution.get("arena_status") or ""),
                        "approval_mode": str(execution.get("approval_mode") or ""),
                        "boundary_decision": str(execution.get("boundary_decision") or ""),
                        "boundary_reason": str(execution.get("boundary_reason") or ""),
                    },
                }
            )
        return lanes

    lane_reports = []
    for item in report.get("lane_reports", []) if isinstance(report.get("lane_reports"), list) else []:
        if not isinstance(item, dict):
            continue
        lane_reports.append(
            {
                "id": str(item.get("id") or ""),
                "title": str(item.get("title") or ""),
                "summary": str(item.get("summary") or ""),
            }
        )

    recommendation = report.get("recommendation") if isinstance(report.get("recommendation"), dict) else {}
    return {
        "headline": str(report.get("headline") or "While you were away, JARVIS kept the board moving."),
        "summary": str(report.get("summary") or "JARVIS tracked quiet completions, blocked work, prepared next steps, and the most useful next move."),
        "window_hours": int(report.get("window_hours") or 18),
        "generated_at": str(report.get("generated_at") or _ts()),
        "stewardship_lanes": _stewardship_lanes(report.get("stewardship_lanes")),
        "lane_reports": lane_reports,
        "quiet_completions": _rows(report.get("quiet_completions")),
        "blocked_work": _rows(report.get("blocked_work")),
        "prepared_work": _rows(report.get("prepared_work")),
        "decision_cards": _rows(report.get("decision_cards")),
        "drift_signals": _rows(report.get("drift_signals")),
        "recommendation": {
            "title": str(recommendation.get("title") or "Stay with the quiet work"),
            "summary": str(recommendation.get("summary") or "No hard interruption is waiting."),
            "action": str(recommendation.get("action") or "Start with the first prepared item."),
        },
    }


def _build_home_continuity(actor: str) -> dict[str, Any]:
    try:
        viewer = runtime.get_actor(actor)
        snapshot = runtime.learning_review_snapshot(viewer.display_name, viewer.user_id) or {}
        memory_graph = runtime.durable_memory_graph_snapshot(viewer.display_name, viewer.user_id) or {}
    except Exception:
        viewer = None
        snapshot = {}
        memory_graph = {}
    if not isinstance(snapshot, dict):
        snapshot = {}
    if not isinstance(memory_graph, dict):
        memory_graph = {}

    profile = snapshot.get("profile") if isinstance(snapshot.get("profile"), dict) else {}
    personalization = snapshot.get("personalization") if isinstance(snapshot.get("personalization"), dict) else {}
    facts = snapshot.get("profile_facts") if isinstance(snapshot.get("profile_facts"), list) else []
    first_light_history = snapshot.get("first_light_history") if isinstance(snapshot.get("first_light_history"), list) else []
    persona_snapshot = snapshot.get("persona_snapshot") if isinstance(snapshot.get("persona_snapshot"), dict) else {}
    digital_twin = persona_snapshot.get("digital_twin") if isinstance(persona_snapshot.get("digital_twin"), dict) else {}

    carry_forward_lines: list[str] = []
    for line in personalization.get("rhythms", []) if isinstance(personalization.get("rhythms"), list) else []:
        cleaned = str(line).strip()
        if cleaned and cleaned not in carry_forward_lines:
            carry_forward_lines.append(cleaned)
    for line in digital_twin.get("likely_next_needs", []) if isinstance(digital_twin.get("likely_next_needs"), list) else []:
        cleaned = str(line).strip()
        if cleaned and cleaned not in carry_forward_lines:
            carry_forward_lines.append(cleaned)

    recent_facts = []
    for item in facts[:3]:
        if not isinstance(item, dict):
            continue
        recent_facts.append(
            {
                "id": str(item.get("fact_id") or item.get("id") or ""),
                "title": str(item.get("title") or item.get("summary") or "Continuity fact"),
                "summary": str(item.get("summary") or ""),
            }
        )

    recent_first_light = []
    for index, item in enumerate(list(reversed(first_light_history))[:3]):
        if not isinstance(item, dict):
            continue
        first_20 = item.get("first_20_minutes") if isinstance(item.get("first_20_minutes"), list) else []
        summary = str(item.get("watch_line") or "").strip()
        if not summary and first_20:
            summary = "; ".join(str(step).strip() for step in first_20[:2] if str(step).strip())
        if not summary:
            summary = "First Light continuity packet recorded."
        recent_first_light.append(
            {
                "id": str(item.get("packet_id") or item.get("date") or item.get("local_time") or f"home-fl-{index}"),
                "label": str(item.get("date") or item.get("local_time") or "Recent First Light"),
                "summary": summary,
            }
        )

    subject_name = str(snapshot.get("subject_display_name") or (viewer.display_name if viewer else "Chris"))
    return {
        "subject_display_name": subject_name,
        "morning_room": str(profile.get("morning_room") or ""),
        "active_mode": str(personalization.get("active_mode") or ""),
        "primary_rooms": [str(item).strip() for item in (profile.get("primary_rooms") or []) if str(item).strip()],
        "guidance_lines": carry_forward_lines[:4],
        "profile_fact_count": len(facts),
        "recent_profile_facts": recent_facts,
        "recent_first_light": recent_first_light,
        "long_horizon_lines": _memory_graph_long_horizon_lines(memory_graph),
        "active_threads": _memory_graph_thread_titles(memory_graph),
    }


def _build_catalyst_continuity(
    actor: str,
    *,
    active_work: list[dict[str, Any]],
    workflow_counts: dict[str, int],
) -> dict[str, Any]:
    try:
        viewer = runtime.get_actor(actor)
        snapshot = runtime.learning_review_snapshot(viewer.display_name, viewer.user_id) or {}
    except Exception:
        viewer = None
        snapshot = {}
    if not isinstance(snapshot, dict):
        snapshot = {}

    profile = snapshot.get("profile") if isinstance(snapshot.get("profile"), dict) else {}
    personalization = snapshot.get("personalization") if isinstance(snapshot.get("personalization"), dict) else {}
    facts = snapshot.get("profile_facts") if isinstance(snapshot.get("profile_facts"), list) else []
    first_light_history = snapshot.get("first_light_history") if isinstance(snapshot.get("first_light_history"), list) else []

    guidance_lines: list[str] = []
    for line in personalization.get("rhythms", []) if isinstance(personalization.get("rhythms"), list) else []:
        cleaned = str(line).strip()
        if cleaned and cleaned not in guidance_lines:
            guidance_lines.append(cleaned)
    for line in personalization.get("learned_preferences", []) if isinstance(personalization.get("learned_preferences"), list) else []:
        cleaned = str(line).strip()
        if cleaned and cleaned not in guidance_lines:
            guidance_lines.append(cleaned)

    active_domains: list[str] = []
    for item in active_work:
        if not isinstance(item, dict):
            continue
        domain = str(item.get("domain") or "").strip()
        if domain and domain not in active_domains:
            active_domains.append(domain)

    recent_profile_facts = []
    for item in facts[:3]:
        if not isinstance(item, dict):
            continue
        recent_profile_facts.append(
            {
                "id": str(item.get("fact_id") or item.get("id") or ""),
                "title": str(item.get("title") or item.get("summary") or "Catalyst continuity fact"),
                "summary": str(item.get("summary") or ""),
            }
        )

    recent_first_light = []
    for index, item in enumerate(list(reversed(first_light_history))[:3]):
        if not isinstance(item, dict):
            continue
        first_20 = item.get("first_20_minutes") if isinstance(item.get("first_20_minutes"), list) else []
        summary = str(item.get("watch_line") or "").strip()
        if not summary and first_20:
            summary = "; ".join(str(step).strip() for step in first_20[:2] if str(step).strip())
        if not summary:
            summary = "First Light continuity packet recorded."
        recent_first_light.append(
            {
                "id": str(item.get("packet_id") or item.get("date") or item.get("local_time") or f"catalyst-fl-{index}"),
                "label": str(item.get("date") or item.get("local_time") or "Recent First Light"),
                "summary": summary,
            }
        )

    hottest_workflow = ""
    if workflow_counts and any(workflow_counts.values()):
        hottest_workflow = max(workflow_counts.items(), key=lambda item: item[1])[0]

    return {
        "subject_display_name": str(snapshot.get("subject_display_name") or (viewer.display_name if viewer else "Chris")),
        "briefing_style": str(profile.get("briefing_style") or ""),
        "active_domains": active_domains[:4],
        "guidance_lines": guidance_lines[:4],
        "profile_fact_count": len(facts),
        "hottest_workflow": hottest_workflow,
        "recent_profile_facts": recent_profile_facts,
        "recent_first_light": recent_first_light,
    }


def _build_health_continuity(
    actor: str,
    *,
    readiness: str,
    readiness_factors: list[dict[str, Any]],
    watchlist: list[dict[str, Any]],
    next_actions: list[str],
) -> dict[str, Any]:
    try:
        viewer = runtime.get_actor(actor)
        snapshot = runtime.learning_review_snapshot(viewer.display_name, viewer.user_id) or {}
    except Exception:
        viewer = None
        snapshot = {}
    if not isinstance(snapshot, dict):
        snapshot = {}

    personalization = snapshot.get("personalization") if isinstance(snapshot.get("personalization"), dict) else {}
    facts = snapshot.get("profile_facts") if isinstance(snapshot.get("profile_facts"), list) else []
    first_light_history = snapshot.get("first_light_history") if isinstance(snapshot.get("first_light_history"), list) else []
    persona_snapshot = snapshot.get("persona_snapshot") if isinstance(snapshot.get("persona_snapshot"), dict) else {}
    digital_twin = persona_snapshot.get("digital_twin") if isinstance(persona_snapshot.get("digital_twin"), dict) else {}

    guidance_lines: list[str] = []
    for line in personalization.get("rhythms", []) if isinstance(personalization.get("rhythms"), list) else []:
        cleaned = str(line).strip()
        if cleaned and cleaned not in guidance_lines:
            guidance_lines.append(cleaned)
    for line in digital_twin.get("likely_next_needs", []) if isinstance(digital_twin.get("likely_next_needs"), list) else []:
        cleaned = str(line).strip()
        if cleaned and cleaned not in guidance_lines:
            guidance_lines.append(cleaned)
    for line in next_actions:
        cleaned = str(line).strip()
        if cleaned and cleaned not in guidance_lines:
            guidance_lines.append(cleaned)

    active_conditions: list[str] = []
    for item in watchlist:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        if title and title not in active_conditions:
            active_conditions.append(title)

    recovery_focus = ""
    weakest_score: float | None = None
    for factor in readiness_factors:
        if not isinstance(factor, dict):
            continue
        label = str(factor.get("label") or factor.get("metric") or "").strip()
        if not label:
            continue
        if bool(factor.get("missing")):
            recovery_focus = label
            weakest_score = -1
            break
        score = factor.get("score")
        if isinstance(score, (int, float)):
            value = float(score)
            if weakest_score is None or value < weakest_score:
                weakest_score = value
                recovery_focus = label

    recent_profile_facts = []
    for item in facts[:3]:
        if not isinstance(item, dict):
            continue
        recent_profile_facts.append(
            {
                "id": str(item.get("fact_id") or item.get("id") or ""),
                "title": str(item.get("title") or item.get("summary") or "Health continuity fact"),
                "summary": str(item.get("summary") or ""),
            }
        )

    recent_first_light = []
    for index, item in enumerate(list(reversed(first_light_history))[:3]):
        if not isinstance(item, dict):
            continue
        first_20 = item.get("first_20_minutes") if isinstance(item.get("first_20_minutes"), list) else []
        summary = str(item.get("watch_line") or "").strip()
        if not summary and first_20:
            summary = "; ".join(str(step).strip() for step in first_20[:2] if str(step).strip())
        if not summary:
            summary = "First Light continuity packet recorded."
        recent_first_light.append(
            {
                "id": str(item.get("packet_id") or item.get("date") or item.get("local_time") or f"health-fl-{index}"),
                "label": str(item.get("date") or item.get("local_time") or "Recent First Light"),
                "summary": summary,
            }
        )

    return {
        "subject_display_name": str(snapshot.get("subject_display_name") or (viewer.display_name if viewer else "Chris")),
        "readiness_lane": str(readiness or ""),
        "recovery_focus": recovery_focus,
        "active_conditions": active_conditions[:4],
        "guidance_lines": guidance_lines[:4],
        "profile_fact_count": len(facts),
        "recent_profile_facts": recent_profile_facts,
        "recent_first_light": recent_first_light,
    }


def _build_publishing_continuity(
    actor: str,
    *,
    projects: list[dict[str, Any]],
    pending_reviews: list[dict[str, Any]],
    action_items: list[dict[str, Any]],
    launch_workspace: dict[str, Any] | None,
) -> dict[str, Any]:
    try:
        viewer = runtime.get_actor(actor)
        snapshot = runtime.learning_review_snapshot(viewer.display_name, viewer.user_id) or {}
    except Exception:
        viewer = None
        snapshot = {}
    if not isinstance(snapshot, dict):
        snapshot = {}

    profile = snapshot.get("profile") if isinstance(snapshot.get("profile"), dict) else {}
    personalization = snapshot.get("personalization") if isinstance(snapshot.get("personalization"), dict) else {}
    facts = snapshot.get("profile_facts") if isinstance(snapshot.get("profile_facts"), list) else []
    first_light_history = snapshot.get("first_light_history") if isinstance(snapshot.get("first_light_history"), list) else []

    guidance_lines: list[str] = []
    for line in personalization.get("learned_preferences", []) if isinstance(personalization.get("learned_preferences"), list) else []:
        cleaned = str(line).strip()
        if cleaned and cleaned not in guidance_lines:
            guidance_lines.append(cleaned)
    for line in personalization.get("rhythms", []) if isinstance(personalization.get("rhythms"), list) else []:
        cleaned = str(line).strip()
        if cleaned and cleaned not in guidance_lines:
            guidance_lines.append(cleaned)
    for item in action_items[:2]:
        if not isinstance(item, dict):
            continue
        detail = str(item.get("detail") or "").strip()
        if detail and detail not in guidance_lines:
            guidance_lines.append(detail)

    active_platforms: list[str] = []
    for project in projects:
        if not isinstance(project, dict):
            continue
        platform = str(project.get("platform") or "").strip()
        if platform and platform not in active_platforms:
            active_platforms.append(platform)

    launch_focus = ""
    if isinstance(launch_workspace, dict):
        launch_focus = str(launch_workspace.get("platform_focus") or "").strip()
    if not launch_focus and projects:
        launch_focus = str(projects[0].get("platform_focus") or "").strip()

    recent_profile_facts = []
    for item in facts[:3]:
        if not isinstance(item, dict):
            continue
        recent_profile_facts.append(
            {
                "id": str(item.get("fact_id") or item.get("id") or ""),
                "title": str(item.get("title") or item.get("summary") or "Publishing continuity fact"),
                "summary": str(item.get("summary") or ""),
            }
        )

    recent_first_light = []
    for index, item in enumerate(list(reversed(first_light_history))[:3]):
        if not isinstance(item, dict):
            continue
        first_20 = item.get("first_20_minutes") if isinstance(item.get("first_20_minutes"), list) else []
        summary = str(item.get("watch_line") or "").strip()
        if not summary and first_20:
            summary = "; ".join(str(step).strip() for step in first_20[:2] if str(step).strip())
        if not summary:
            summary = "First Light continuity packet recorded."
        recent_first_light.append(
            {
                "id": str(item.get("packet_id") or item.get("date") or item.get("local_time") or f"publishing-fl-{index}"),
                "label": str(item.get("date") or item.get("local_time") or "Recent First Light"),
                "summary": summary,
            }
        )

    return {
        "subject_display_name": str(snapshot.get("subject_display_name") or (viewer.display_name if viewer else "Chris")),
        "briefing_style": str(profile.get("briefing_style") or ""),
        "launch_focus": launch_focus,
        "active_platforms": active_platforms[:4],
        "pending_review_pressure": len(pending_reviews),
        "profile_fact_count": len(facts),
        "guidance_lines": guidance_lines[:4],
        "recent_profile_facts": recent_profile_facts,
        "recent_first_light": recent_first_light,
    }


def _build_faith_continuity(
    actor: str,
    *,
    morning_context: dict[str, Any],
    formation_prompts: list[str],
    agents: list[dict[str, Any]],
    daily_word: dict[str, Any],
) -> dict[str, Any]:
    try:
        viewer = runtime.get_actor(actor)
        snapshot = runtime.learning_review_snapshot(viewer.display_name, viewer.user_id) or {}
    except Exception:
        viewer = None
        snapshot = {}
    if not isinstance(snapshot, dict):
        snapshot = {}

    personalization = snapshot.get("personalization") if isinstance(snapshot.get("personalization"), dict) else {}
    facts = snapshot.get("profile_facts") if isinstance(snapshot.get("profile_facts"), list) else []
    first_light_history = snapshot.get("first_light_history") if isinstance(snapshot.get("first_light_history"), list) else []

    guidance_lines: list[str] = []
    for line in personalization.get("rhythms", []) if isinstance(personalization.get("rhythms"), list) else []:
        cleaned = str(line).strip()
        if cleaned and cleaned not in guidance_lines:
            guidance_lines.append(cleaned)
    for prompt in formation_prompts[:2]:
        cleaned = str(prompt).strip()
        if cleaned and cleaned not in guidance_lines:
            guidance_lines.append(cleaned)

    council_domains: list[str] = []
    for item in agents:
        if not isinstance(item, dict):
            continue
        domain = str(item.get("domain") or "").strip()
        if domain and domain not in council_domains:
            council_domains.append(domain)

    recent_profile_facts = []
    for item in facts[:3]:
        if not isinstance(item, dict):
            continue
        recent_profile_facts.append(
            {
                "id": str(item.get("fact_id") or item.get("id") or ""),
                "title": str(item.get("title") or item.get("summary") or "Faith continuity fact"),
                "summary": str(item.get("summary") or ""),
            }
        )

    recent_first_light = []
    for index, item in enumerate(list(reversed(first_light_history))[:3]):
        if not isinstance(item, dict):
            continue
        first_20 = item.get("first_20_minutes") if isinstance(item.get("first_20_minutes"), list) else []
        summary = str(item.get("watch_line") or "").strip()
        if not summary and first_20:
            summary = "; ".join(str(step).strip() for step in first_20[:2] if str(step).strip())
        if not summary:
            summary = "First Light continuity packet recorded."
        recent_first_light.append(
            {
                "id": str(item.get("packet_id") or item.get("date") or item.get("local_time") or f"faith-fl-{index}"),
                "label": str(item.get("date") or item.get("local_time") or "Recent First Light"),
                "summary": summary,
            }
        )

    return {
        "subject_display_name": str(snapshot.get("subject_display_name") or (viewer.display_name if viewer else "Chris")),
        "theme": str(morning_context.get("theme") or ""),
        "focus": str(morning_context.get("focus") or ""),
        "passage": str(daily_word.get("passage") or ""),
        "council_domains": council_domains[:4],
        "guidance_lines": guidance_lines[:4],
        "profile_fact_count": len(facts),
        "recent_profile_facts": recent_profile_facts,
        "recent_first_light": recent_first_light,
    }


def _build_forge_continuity(
    actor: str,
    *,
    active_project: dict[str, Any] | None,
    projects: list[dict[str, Any]],
    recent_jobs: list[dict[str, Any]],
) -> dict[str, Any]:
    try:
        viewer = runtime.get_actor(actor)
        snapshot = runtime.learning_review_snapshot(viewer.display_name, viewer.user_id) or {}
    except Exception:
        viewer = None
        snapshot = {}
    if not isinstance(snapshot, dict):
        snapshot = {}

    personalization = snapshot.get("personalization") if isinstance(snapshot.get("personalization"), dict) else {}
    facts = snapshot.get("profile_facts") if isinstance(snapshot.get("profile_facts"), list) else []
    first_light_history = snapshot.get("first_light_history") if isinstance(snapshot.get("first_light_history"), list) else []

    guidance_lines: list[str] = []
    for line in personalization.get("learned_preferences", []) if isinstance(personalization.get("learned_preferences"), list) else []:
        cleaned = str(line).strip()
        if cleaned and cleaned not in guidance_lines:
            guidance_lines.append(cleaned)
    for line in personalization.get("rhythms", []) if isinstance(personalization.get("rhythms"), list) else []:
        cleaned = str(line).strip()
        if cleaned and cleaned not in guidance_lines:
            guidance_lines.append(cleaned)

    active_workshop_lanes: list[str] = []
    for project in projects:
        if not isinstance(project, dict):
            continue
        intake_type = str(project.get("intake_type") or "").strip()
        if intake_type and intake_type not in active_workshop_lanes:
            active_workshop_lanes.append(intake_type)

    workshop_focus = ""
    if isinstance(active_project, dict):
        workshop_focus = str(active_project.get("notes") or "").strip()
        if not workshop_focus:
            missing = active_project.get("missing_views") if isinstance(active_project.get("missing_views"), list) else []
            if missing:
                workshop_focus = "Missing views: " + ", ".join(str(item).strip() for item in missing if str(item).strip())

    if recent_jobs:
        next_job = recent_jobs[0]
        detail = f"Recent job: {str(next_job.get('name') or 'Forge job')} is {str(next_job.get('status') or 'active')}."
        if detail not in guidance_lines:
            guidance_lines.append(detail)

    recent_profile_facts = []
    for item in facts[:3]:
        if not isinstance(item, dict):
            continue
        recent_profile_facts.append(
            {
                "id": str(item.get("fact_id") or item.get("id") or ""),
                "title": str(item.get("title") or item.get("summary") or "Forge continuity fact"),
                "summary": str(item.get("summary") or ""),
            }
        )

    recent_first_light = []
    for index, item in enumerate(list(reversed(first_light_history))[:3]):
        if not isinstance(item, dict):
            continue
        first_20 = item.get("first_20_minutes") if isinstance(item.get("first_20_minutes"), list) else []
        summary = str(item.get("watch_line") or "").strip()
        if not summary and first_20:
            summary = "; ".join(str(step).strip() for step in first_20[:2] if str(step).strip())
        if not summary:
            summary = "First Light continuity packet recorded."
        recent_first_light.append(
            {
                "id": str(item.get("packet_id") or item.get("date") or item.get("local_time") or f"forge-fl-{index}"),
                "label": str(item.get("date") or item.get("local_time") or "Recent First Light"),
                "summary": summary,
            }
        )

    return {
        "subject_display_name": str(snapshot.get("subject_display_name") or (viewer.display_name if viewer else "Chris")),
        "workshop_focus": workshop_focus,
        "active_workshop_lanes": active_workshop_lanes[:4],
        "queued_job_count": len(recent_jobs),
        "profile_fact_count": len(facts),
        "guidance_lines": guidance_lines[:4],
        "recent_profile_facts": recent_profile_facts,
        "recent_first_light": recent_first_light,
    }


def _build_huddle_continuity(
    actor: str,
    *,
    reports: list[dict[str, Any]],
    blockers: list[str],
    party_status: dict[str, Any],
    dossiers: list[dict[str, Any]],
) -> dict[str, Any]:
    try:
        viewer = runtime.get_actor(actor)
        snapshot = runtime.learning_review_snapshot(viewer.display_name, viewer.user_id) or {}
    except Exception:
        viewer = None
        snapshot = {}
    if not isinstance(snapshot, dict):
        snapshot = {}

    personalization = snapshot.get("personalization") if isinstance(snapshot.get("personalization"), dict) else {}
    facts = snapshot.get("profile_facts") if isinstance(snapshot.get("profile_facts"), list) else []
    first_light_history = snapshot.get("first_light_history") if isinstance(snapshot.get("first_light_history"), list) else []

    guidance_lines: list[str] = []
    for line in personalization.get("rhythms", []) if isinstance(personalization.get("rhythms"), list) else []:
        cleaned = str(line).strip()
        if cleaned and cleaned not in guidance_lines:
            guidance_lines.append(cleaned)
    for line in personalization.get("learned_preferences", []) if isinstance(personalization.get("learned_preferences"), list) else []:
        cleaned = str(line).strip()
        if cleaned and cleaned not in guidance_lines:
            guidance_lines.append(cleaned)

    active_domains: list[str] = []
    for report in reports:
        if not isinstance(report, dict):
            continue
        domain = str(report.get("domain") or "").strip()
        if domain and domain not in active_domains:
            active_domains.append(domain)

    council_focus = ""
    if blockers:
        council_focus = str(blockers[0]).strip()
    if not council_focus:
        last_log = str(party_status.get("last_log") or "").strip()
        if last_log:
            council_focus = last_log
    if not council_focus and dossiers:
        first_dossier = dossiers[0] if isinstance(dossiers[0], dict) else {}
        council_focus = str(first_dossier.get("executive_summary") or first_dossier.get("first_action") or "").strip()

    if dossiers:
        dossier_line = f"{len(dossiers)} ready dossiers are waiting for the next council pass."
        if dossier_line not in guidance_lines:
            guidance_lines.append(dossier_line)
    if party_status:
        session_state = str(party_status.get("status") or "").strip()
        if session_state:
            session_line = f"Party mode is currently {session_state.replace('_', ' ')}."
            if session_line not in guidance_lines:
                guidance_lines.append(session_line)

    recent_profile_facts = []
    for item in facts[:3]:
        if not isinstance(item, dict):
            continue
        recent_profile_facts.append(
            {
                "id": str(item.get("fact_id") or item.get("id") or ""),
                "title": str(item.get("title") or item.get("summary") or "Huddle continuity fact"),
                "summary": str(item.get("summary") or ""),
            }
        )

    recent_first_light = []
    for index, item in enumerate(list(reversed(first_light_history))[:3]):
        if not isinstance(item, dict):
            continue
        first_20 = item.get("first_20_minutes") if isinstance(item.get("first_20_minutes"), list) else []
        summary = str(item.get("watch_line") or "").strip()
        if not summary and first_20:
            summary = "; ".join(str(step).strip() for step in first_20[:2] if str(step).strip())
        if not summary:
            summary = "First Light continuity packet recorded."
        recent_first_light.append(
            {
                "id": str(item.get("packet_id") or item.get("date") or item.get("local_time") or f"huddle-fl-{index}"),
                "label": str(item.get("date") or item.get("local_time") or "Recent First Light"),
                "summary": summary,
            }
        )

    return {
        "subject_display_name": str(snapshot.get("subject_display_name") or (viewer.display_name if viewer else "Chris")),
        "council_focus": council_focus,
        "active_domains": active_domains[:5],
        "ready_dossier_count": len(dossiers),
        "profile_fact_count": len(facts),
        "guidance_lines": guidance_lines[:4],
        "recent_profile_facts": recent_profile_facts,
        "recent_first_light": recent_first_light,
    }


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
        "route_history": [],
        "active_stop_category_ids": ["food", "starbucks", "parks", "historic", "family"],
        "parks_historic_radius_miles": 25,
        "selected_origin_mode": "home",
        "selected_saved_location_id": "",
        "last_route": {
            "origin": "",
            "destination": "",
        },
    }


def _normalize_navigation_route_history_entry(item: Any) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    origin = str(item.get("origin") or "").strip()
    destination = str(item.get("destination") or "").strip()
    if not origin or not destination:
        return None
    route_id = str(item.get("route_id") or uuid.uuid5(uuid.NAMESPACE_URL, f"jarvis-route:{origin.lower()}::{destination.lower()}")).strip()
    saved_at = str(item.get("saved_at") or item.get("last_previewed_at") or _ts()).strip() or _ts()
    last_previewed_at = str(item.get("last_previewed_at") or saved_at).strip() or saved_at
    last_resumed_at = str(item.get("last_resumed_at") or "").strip()
    source_label = str(item.get("source_label") or "Navigation route preview").strip() or "Navigation route preview"
    origin_mode = str(item.get("origin_mode") or "home").strip() or "home"
    saved_location_id = str(item.get("saved_location_id") or "").strip()
    try:
        preview_count = max(1, int(item.get("preview_count", 1) or 1))
    except Exception:
        preview_count = 1
    try:
        resume_count = max(0, int(item.get("resume_count", 0) or 0))
    except Exception:
        resume_count = 0
    return {
        "route_id": route_id,
        "origin": origin,
        "destination": destination,
        "origin_mode": origin_mode,
        "saved_location_id": saved_location_id,
        "source_label": source_label,
        "saved_at": saved_at,
        "last_previewed_at": last_previewed_at,
        "last_resumed_at": last_resumed_at,
        "preview_count": preview_count,
        "resume_count": resume_count,
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
    route_history: list[dict[str, Any]] = []
    for item in (merged.get("route_history") or []):
        normalized = _normalize_navigation_route_history_entry(item)
        if normalized:
            route_history.append(normalized)
    route_history.sort(
        key=lambda item: str(item.get("last_previewed_at") or item.get("saved_at") or ""),
        reverse=True,
    )
    merged["route_history"] = route_history[:8]
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
    route_history: list[dict[str, Any]] = []
    for item in (cleaned.get("route_history") or []):
        normalized = _normalize_navigation_route_history_entry(item)
        if normalized:
            route_history.append(normalized)
    route_history.sort(
        key=lambda item: str(item.get("last_previewed_at") or item.get("saved_at") or ""),
        reverse=True,
    )
    cleaned["route_history"] = route_history[:8]
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
    _safe_write_json(_NAVIGATION_STATE_PATH, cleaned)
    return cleaned


def _record_navigation_route_history(
    *,
    origin: str,
    destination: str,
    origin_mode: str,
    saved_location_id: str = "",
    parks_historic_radius_miles: int | None = None,
    source_label: str = "Navigation route preview",
) -> tuple[dict[str, Any], dict[str, Any]]:
    current = _load_navigation_state()
    route_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"jarvis-route:{origin.lower()}::{destination.lower()}"))
    now = _ts()
    existing_history = list(current.get("route_history") or [])
    next_history: list[dict[str, Any]] = []
    matched_entry: dict[str, Any] | None = None
    for item in existing_history:
        normalized = _normalize_navigation_route_history_entry(item)
        if not normalized:
            continue
        if normalized["route_id"] == route_id:
            normalized["origin_mode"] = origin_mode
            normalized["saved_location_id"] = saved_location_id
            normalized["source_label"] = source_label
            normalized["last_previewed_at"] = now
            normalized["preview_count"] = int(normalized.get("preview_count", 1) or 1) + 1
            matched_entry = normalized
        next_history.append(normalized)
    if matched_entry is None:
        matched_entry = {
            "route_id": route_id,
            "origin": origin,
            "destination": destination,
            "origin_mode": origin_mode,
            "saved_location_id": saved_location_id,
            "source_label": source_label,
            "saved_at": now,
            "last_previewed_at": now,
            "last_resumed_at": "",
            "preview_count": 1,
            "resume_count": 0,
        }
        next_history.append(matched_entry)
    next_recent = [destination] + [
        str(item).strip()
        for item in (current.get("recent_destinations") or [])
        if str(item).strip() and str(item).strip().lower() != destination.lower()
    ]
    saved = _save_navigation_state(
        {
            "selected_origin_mode": origin_mode,
            "selected_saved_location_id": saved_location_id,
            "parks_historic_radius_miles": parks_historic_radius_miles if parks_historic_radius_miles is not None else current.get("parks_historic_radius_miles"),
            "last_route": {"origin": origin, "destination": destination},
            "recent_destinations": next_recent[:8],
            "route_history": next_history,
        }
    )
    normalized_saved = next(
        (
            item for item in (saved.get("route_history") or [])
            if str(item.get("route_id") or "").strip() == route_id
        ),
        matched_entry,
    )
    return saved, normalized_saved


def _resume_navigation_route_history(
    *,
    route_id: str,
    actor: str = "chris",
    source_label: str = "Navigation route history",
) -> dict[str, Any]:
    current = _load_navigation_state()
    history = list(current.get("route_history") or [])
    target: dict[str, Any] | None = None
    next_history: list[dict[str, Any]] = []
    now = _ts()
    for item in history:
        normalized = _normalize_navigation_route_history_entry(item)
        if not normalized:
            continue
        if normalized["route_id"] == route_id:
            normalized["last_resumed_at"] = now
            normalized["resume_count"] = int(normalized.get("resume_count", 0) or 0) + 1
            target = normalized
        next_history.append(normalized)
    if target is None:
        raise KeyError("Navigation route history entry not found.")
    destination = str(target.get("destination") or "").strip()
    saved = _save_navigation_state(
        {
            "selected_origin_mode": str(target.get("origin_mode") or current.get("selected_origin_mode") or "home").strip() or "home",
            "selected_saved_location_id": str(target.get("saved_location_id") or current.get("selected_saved_location_id") or "").strip(),
            "last_route": {
                "origin": str(target.get("origin") or "").strip(),
                "destination": destination,
            },
            "recent_destinations": [destination]
            + [
                str(item).strip()
                for item in (current.get("recent_destinations") or [])
                if str(item).strip() and str(item).strip().lower() != destination.lower()
            ][:7],
            "route_history": next_history,
        }
    )
    restored = next(
        (
            item for item in (saved.get("route_history") or [])
            if str(item.get("route_id") or "").strip() == route_id
        ),
        target,
    )
    title = f"{str(restored.get('origin') or '').strip()} -> {destination}"
    _record_operator_action(
        actor=actor,
        domain="navigation",
        action="Resume Navigation Route",
        detail=f"{source_label} resumed {title}.",
        why_now="A stored route was restored so travel continuity can move cleanly across desktop, iPhone, and CarPlay.",
        result_summary=f"Navigation focus restored for {title}.",
        route="/navigation-center",
        route_label="Open Navigation",
        related_kind="route-history",
        related_label=title,
        succeeded=True,
    )
    focus = ProgressFocusStore(_ACTIVITY_AUDIT_ROOT).save_focus(
        module="Navigation",
        reason=f"Resumed stored route {title}.",
        route="/navigation-center",
        actor=actor,
    )
    return {"state": saved, "route": restored, "focus": focus}


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


class _StewardshipReviewStore:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._log_path = path.with_name(f"{path.stem}_log.jsonl")

    def _load(self) -> dict[str, Any]:
        payload = _safe_read_json(self._path, {})
        if not payload and self._log_path.exists():
            try:
                last: Any = None
                for line in self._log_path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    last = json.loads(line)
                if isinstance(last, dict):
                    atomic_write_json(self._path, last)
                    payload = last
            except Exception as exc:
                logger.warning("apple_api.stewardship_review_store replay %s: %s", self._log_path, exc)
        reviews = payload.get("reviews") if isinstance(payload, dict) else []
        if not isinstance(reviews, list):
            reviews = []
        return {"reviews": [item for item in reviews if isinstance(item, dict)]}

    def _save(self, payload: dict[str, Any]) -> None:
        persistence_append_jsonl(self._log_path, payload)
        atomic_write_json(self._path, payload)

    def upsert(
        self,
        *,
        lane_id: str,
        lane_title: str,
        review_surface: str,
        packet_target: str,
        boundary_decision: str,
        boundary_reason: str,
        trust_zone: str,
        authority_stage: str,
        arena_status: str,
        approval_mode: str,
        actor: str,
        note: str = "",
        event_id: str = "",
        notification_id: str = "",
        approval_request_id: str = "",
        supervision_decision: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        store = self._load()
        now = _ts()
        for item in store["reviews"]:
            if str(item.get("lane_id") or "") != lane_id:
                continue
            if str(item.get("status") or "") in {"approved", "retired"}:
                continue
            item.update(
                {
                    "lane_title": lane_title,
                    "review_surface": review_surface,
                    "packet_target": packet_target,
                    "boundary_decision": boundary_decision,
                    "boundary_reason": boundary_reason,
                    "trust_zone": trust_zone,
                    "authority_stage": authority_stage,
                    "arena_status": arena_status,
                    "approval_mode": approval_mode,
                    "status": "blocked_by_boundary" if boundary_decision == "deny" else "review_staged",
                    "updated_at": now,
                    "last_actor": actor,
                    "note": note,
                    "event_id": event_id or str(item.get("event_id") or ""),
                    "notification_id": notification_id or str(item.get("notification_id") or ""),
                    "approval_request_id": approval_request_id or str(item.get("approval_request_id") or ""),
                    "supervision_decision": dict(supervision_decision or item.get("supervision_decision") or {}),
                }
            )
            self._save(store)
            return deepcopy(item)

        review = {
            "id": f"stewardship-review::{lane_id}::{uuid.uuid4()}",
            "lane_id": lane_id,
            "lane_title": lane_title,
            "review_surface": review_surface,
            "packet_target": packet_target,
            "boundary_decision": boundary_decision,
            "boundary_reason": boundary_reason,
            "trust_zone": trust_zone,
            "authority_stage": authority_stage,
            "arena_status": arena_status,
            "approval_mode": approval_mode,
            "status": "blocked_by_boundary" if boundary_decision == "deny" else "review_staged",
            "created_at": now,
            "updated_at": now,
            "last_actor": actor,
            "note": note,
            "event_id": event_id,
            "notification_id": notification_id,
            "approval_request_id": approval_request_id,
            "supervision_decision": dict(supervision_decision or {}),
        }
        store["reviews"].append(review)
        self._save(store)
        return deepcopy(review)

    def list(self, *, include_closed: bool = False, limit: int = 0) -> list[dict[str, Any]]:
        items = self._load()["reviews"]
        if not include_closed:
            items = [
                item for item in items
                if str(item.get("status") or "") not in {"approved", "retired"}
            ]
        items.sort(key=lambda item: str(item.get("updated_at") or item.get("created_at") or ""), reverse=True)
        if limit > 0:
            items = items[:limit]
        return deepcopy(items)

    def get(self, review_id: str) -> dict[str, Any] | None:
        for item in self._load()["reviews"]:
            if str(item.get("id") or "") == review_id:
                return deepcopy(item)
        return None

    def update(self, review_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        store = self._load()
        for item in store["reviews"]:
            if str(item.get("id") or "") != review_id:
                continue
            item.update({key: value for key, value in updates.items()})
            item["updated_at"] = _ts()
            self._save(store)
            return deepcopy(item)
        return None


class _NotificationCenterStore:
    def __init__(self, path: Path, event_log: _EventLogStore) -> None:
        self._path = path
        self._log_path = path.with_name(f"{path.stem}_log.jsonl")
        self._event_log = event_log

    def _load(self) -> dict[str, Any]:
        data = _safe_read_json(self._path, {})
        if not data and self._log_path.exists():
            try:
                last: Any = None
                for line in self._log_path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    last = json.loads(line)
                if isinstance(last, dict):
                    atomic_write_json(self._path, last)
                    data = last
            except Exception as exc:
                logger.warning("apple_api.notification_center_store replay %s: %s", self._log_path, exc)
        items = data.get("items") if isinstance(data, dict) else []
        if not isinstance(items, list):
            items = []
        return {"items": [item for item in items if isinstance(item, dict)]}

    def _save(self, payload: dict[str, Any]) -> None:
        persistence_append_jsonl(self._log_path, payload)
        atomic_write_json(self._path, payload)

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
        decision_reason: str = "",
        posture_snapshot: dict[str, Any] | None = None,
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
            "decision_reason": str(decision_reason or ""),
            "source_summary": str(source_summary or ""),
            "posture_snapshot": posture_snapshot if isinstance(posture_snapshot, dict) else {},
            "badge": 0,
            "metadata": metadata if isinstance(metadata, dict) else {},
        }
        store["items"].append(notification)
        self._save(store)
        return notification

    def upsert(
        self,
        *,
        source_key: str,
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
        decision_reason: str = "",
        posture_snapshot: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        store = self._load()
        key = str(source_key or "").strip()
        now = _ts()
        merged_metadata = metadata if isinstance(metadata, dict) else {}
        merged_metadata = {**merged_metadata, "source_key": key}
        for item in store["items"]:
            item_key = str((item.get("metadata") or {}).get("source_key") or "")
            if key and item_key == key and str(item.get("status") or "") not in {"resolved", "dismissed"}:
                item.update({
                    "event_id": str((event or {}).get("id") or item.get("event_id") or ""),
                    "category": str(category or item.get("category") or "system"),
                    "title": str(title or item.get("title") or "JARVIS Alert"),
                    "detail": str(detail or item.get("detail") or ""),
                    "body": str(detail or item.get("body") or ""),
                    "severity": str(severity or item.get("severity") or "low"),
                    "updated_at": now,
                    "expires_at": str(expires_at or item.get("expires_at") or ""),
                    "audience": str(audience or item.get("audience") or "household"),
                    "delivery_mode": str(delivery_mode or item.get("delivery_mode") or "badge_only"),
                    "navigation_target": str(navigation_target or item.get("navigation_target") or ""),
                    "available_actions": [str(action) for action in (available_actions or item.get("available_actions") or ["open", "dismiss"]) if str(action or "").strip()],
                    "why_now": str(why_now or item.get("why_now") or ""),
                    "decision_reason": str(decision_reason or item.get("decision_reason") or ""),
                    "source_summary": str(source_summary or item.get("source_summary") or ""),
                    "posture_snapshot": posture_snapshot if isinstance(posture_snapshot, dict) else (item.get("posture_snapshot") or {}),
                    "metadata": {**(item.get("metadata") or {}), **merged_metadata},
                })
                self._save(store)
                return deepcopy(item)
        notification = self.create(
            category=category,
            title=title,
            detail=detail,
            severity=severity,
            audience=audience,
            delivery_mode=delivery_mode,
            navigation_target=navigation_target,
            available_actions=available_actions,
            why_now=why_now,
            source_summary=source_summary,
            event=event,
            expires_at=expires_at,
            metadata=merged_metadata,
            decision_reason=decision_reason,
            posture_snapshot=posture_snapshot,
        )
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

    def get(self, notification_id: str) -> dict[str, Any] | None:
        for item in self._load()["items"]:
            if str(item.get("id") or "") == notification_id:
                return deepcopy(item)
        return None

    def update_item(self, notification_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        store = self._load()
        for item in store["items"]:
            if str(item.get("id") or "") != notification_id:
                continue
            item.update(updates)
            item["updated_at"] = _ts()
            self._save(store)
            return deepcopy(item)
        return None

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
_stewardship_reviews = _StewardshipReviewStore(_STEWARDSHIP_REVIEW_QUEUE_PATH)
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


def _sync_mirrored_reminder(
    reminder_id: str,
    *,
    completed: bool | None = None,
    due: str | None = None,
) -> None:
    path = _APPLE_REMINDERS_PATH
    payload = _safe_read_json(path, {})
    reminders = payload.get("reminders") if isinstance(payload, dict) else []
    if not isinstance(reminders, list):
        return
    changed = False
    for reminder in reminders:
        if not isinstance(reminder, dict):
            continue
        if str(reminder.get("id") or "") != reminder_id:
            continue
        if completed is not None:
            reminder["completed"] = bool(completed)
            changed = True
        if due is not None:
            reminder["due"] = due
            changed = True
    if not changed:
        return
    active_count = sum(
        1 for reminder in reminders
        if isinstance(reminder, dict) and not bool(reminder.get("completed"))
    )
    payload["reminders"] = reminders
    payload["count"] = active_count
    payload["synced_at"] = _ts()
    _safe_write_json(path, payload)


def _perform_notification_action(notification_id: str, action: str) -> dict[str, Any]:
    item = _notification_center.get(notification_id)
    if not item:
        raise HTTPException(status_code=404, detail="Notification not found")

    action_name = str(action or "").strip().lower()
    allowed = [str(name).strip().lower() for name in (item.get("available_actions") or [])]
    if action_name not in allowed:
        raise HTTPException(status_code=400, detail=f"Action '{action_name}' is not allowed for this notification")

    metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
    title = str(item.get("title") or "Notification")
    category = str(item.get("category") or "system")

    if action_name == "complete_reminder":
        from .reminders import complete_reminder

        reminder_id = str(metadata.get("reminder_id") or "").strip()
        if not reminder_id:
            raise HTTPException(status_code=400, detail="Reminder notification missing reminder_id")
        ok = complete_reminder(reminder_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Reminder not found")
        _sync_mirrored_reminder(reminder_id, completed=True)
        updated = _notification_center.update_status(
            notification_id,
            "resolved",
            reason="Reminder was completed from Notification Center.",
        )
        _record_shared_event(
            domain="reminders",
            kind="resolved",
            title="Reminder completed",
            detail=title,
            severity="low",
            source="apple.notification_center",
            source_id=reminder_id,
            navigation_target="workshop",
            actions=["open"],
            trust_zone="household_schedule",
            authority_stage="live",
            why_now="A reminder was completed directly from the notification workflow.",
            metadata={"notification_id": notification_id, "action": action_name},
        )
        return {"ok": True, "status": str((updated or {}).get("status") or "resolved"), "notification": updated, "performed_action": action_name}

    if action_name == "snooze_reminder":
        from .reminders import snooze_reminder

        reminder_id = str(metadata.get("reminder_id") or "").strip()
        if not reminder_id:
            raise HTTPException(status_code=400, detail="Reminder notification missing reminder_id")
        new_due = _iso_after_minutes(60)
        ok = snooze_reminder(reminder_id, new_due)
        if not ok:
            raise HTTPException(status_code=404, detail="Reminder not found")
        _sync_mirrored_reminder(reminder_id, completed=False, due=new_due)
        updated = _notification_center.update_status(
            notification_id,
            "snoozed",
            reason="Reminder was snoozed for one hour from Notification Center.",
        )
        _record_shared_event(
            domain="reminders",
            kind="info",
            title="Reminder snoozed",
            detail=f"{title} until {new_due}",
            severity="low",
            source="apple.notification_center",
            source_id=reminder_id,
            navigation_target="workshop",
            actions=["open"],
            trust_zone="household_schedule",
            authority_stage="live",
            why_now="A reminder was deferred from the shared notification workflow.",
            metadata={"notification_id": notification_id, "action": action_name, "due": new_due},
        )
        return {"ok": True, "status": str((updated or {}).get("status") or "snoozed"), "notification": updated, "performed_action": action_name, "due": new_due}

    if action_name == "stage_prep":
        event_title = str(metadata.get("title") or title).strip()
        event_start = str(metadata.get("start") or "").strip()
        updated = _notification_center.update_status(
            notification_id,
            "resolved",
            reason="Calendar preparation was staged from Notification Center.",
        )
        _record_shared_event(
            domain="calendar",
            kind="stage_ready",
            title="Calendar preparation staged",
            detail=f"{event_title}" + (f" at {event_start}" if event_start else ""),
            severity="low",
            source="apple.notification_center",
            source_id=notification_id,
            navigation_target="calendar",
            actions=["open"],
            trust_zone="household_schedule",
            authority_stage="staged",
            why_now="The household asked JARVIS to stage prep for an upcoming event.",
            metadata={"notification_id": notification_id, "action": action_name, "category": category},
        )
        return {"ok": True, "status": str((updated or {}).get("status") or "resolved"), "notification": updated, "performed_action": action_name}

    if action_name == "open":
        updated = _notification_center.update_status(
            notification_id,
            "seen",
            reason="Notification was opened from Notification Center.",
        )
        return {"ok": True, "status": str((updated or {}).get("status") or "seen"), "notification": updated, "performed_action": action_name}

    raise HTTPException(status_code=400, detail=f"Unhandled notification action '{action_name}'")


def _apple_complete_reminder(reminder_id: str) -> dict[str, Any]:
    from .reminders import complete_reminder

    ok = complete_reminder(reminder_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Reminder not found")
    _sync_mirrored_reminder(reminder_id, completed=True)
    _record_shared_event(
        domain="reminders",
        kind="resolved",
        title="Reminder completed",
        detail=reminder_id,
        severity="low",
        source="apple.reminders",
        source_id=reminder_id,
        navigation_target="workshop",
        actions=["open"],
        trust_zone="household_schedule",
        authority_stage="live",
        why_now="A reminder was completed from the Apple workflow.",
        metadata={"reminder_id": reminder_id},
    )
    return {"ok": True, "reminder_id": reminder_id, "status": "completed"}


def _apple_snooze_reminder(reminder_id: str, *, minutes: int = 60) -> dict[str, Any]:
    from .reminders import snooze_reminder

    new_due = _iso_after_minutes(minutes)
    ok = snooze_reminder(reminder_id, new_due)
    if not ok:
        raise HTTPException(status_code=404, detail="Reminder not found")
    _sync_mirrored_reminder(reminder_id, completed=False, due=new_due)
    _record_shared_event(
        domain="reminders",
        kind="info",
        title="Reminder snoozed",
        detail=f"{reminder_id} until {new_due}",
        severity="low",
        source="apple.reminders",
        source_id=reminder_id,
        navigation_target="workshop",
        actions=["open"],
        trust_zone="household_schedule",
        authority_stage="live",
        why_now="A reminder was deferred from the Apple workflow.",
        metadata={"reminder_id": reminder_id, "due": new_due, "minutes": minutes},
    )
    return {"ok": True, "reminder_id": reminder_id, "status": "snoozed", "due": new_due}


def _current_apple_reminder_item(reminder_id: str) -> dict[str, Any] | None:
    state = _build_apple_reminders_state(_payload_store.apple_state())
    for item in state.get("open_items") or []:
        if isinstance(item, dict) and str(item.get("id") or "") == reminder_id:
            return item
    for lane in ("overdue_items", "due_soon_items", "priority_items"):
        for item in state.get(lane) or []:
            if isinstance(item, dict) and str(item.get("id") or "") == reminder_id:
                return item
    return None


def _governed_reminder_mutation(reminder_id: str, *, action_label: str, minutes: int = 60) -> dict[str, Any]:
    item = _current_apple_reminder_item(reminder_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Reminder not found")
    request_id = str(uuid.uuid4())
    boundary = runtime.assess_action_boundary(
        zone_id="household_tasks",
        arena_id="household.tasks.workflow",
        action_type="reminder_workflow",
        requested_stage="sandbox_live",
    )
    boundary_decision = str(boundary.get("decision") or "stage")
    boundary_reason = str(boundary.get("reason") or "")
    trust_zone = str(boundary.get("trust_zone") or "household_tasks")
    authority_stage = str(boundary.get("authority_stage") or "stage_alert")
    approval_mode = str(boundary.get("approval_mode") or "stage_and_alert")
    arena_status = str(boundary.get("arena_status") or "active")

    if boundary_decision == "deny":
        return {
            "request_id": request_id,
            "status": "blocked_by_boundary",
            "reminder": item,
            "performed_action": action_label,
            "boundary_decision": boundary_decision,
            "boundary_reason": boundary_reason,
            "trust_zone": trust_zone,
            "authority_stage": authority_stage,
            "arena_status": arena_status,
            "approval_mode": approval_mode,
        }

    if boundary_decision != "allow":
        from .models import StagedActionQueueItem

        runtime.trust_support.enqueue_stage_action(
            StagedActionQueueItem(
                request_id=request_id,
                arena_id="household.tasks.workflow",
                action_type=f"reminder_{action_label}_review",
                status="awaiting_principal_review",
                created_at=_ts(),
                principal_id="chris",
            )
        )
        staged_item = dict(item)
        staged_item["decision_reason"] = boundary_reason
        return {
            "request_id": request_id,
            "status": "staged_for_review",
            "reminder": staged_item,
            "performed_action": action_label,
            "boundary_decision": boundary_decision,
            "boundary_reason": boundary_reason,
            "trust_zone": trust_zone,
            "authority_stage": authority_stage,
            "arena_status": arena_status,
            "approval_mode": approval_mode,
        }

    if action_label == "complete":
        result = _apple_complete_reminder(reminder_id)
    else:
        result = _apple_snooze_reminder(reminder_id, minutes=minutes)
    updated_item = _current_apple_reminder_item(reminder_id) or item
    status = str(result.get("status") or action_label)
    if action_label == "complete":
        updated_item = dict(updated_item)
        updated_item["completed"] = True
    return {
        "request_id": request_id,
        "status": status,
        "reminder": updated_item,
        "performed_action": action_label,
        "boundary_decision": boundary_decision,
        "boundary_reason": boundary_reason,
        "trust_zone": trust_zone,
        "authority_stage": authority_stage,
        "arena_status": arena_status,
        "approval_mode": approval_mode,
    }


def _apply_focus_record(payload: dict[str, Any]) -> dict[str, Any]:
    out_path = _FOCUS_STATE_PATH
    record = {**payload, "updated_at": _ts()}
    _safe_write_json(out_path, record)

    try:
        from .service import broadcast_event

        broadcast_event("apple.focus", record)
    except Exception:
        pass

    _record_shared_event(
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
        trust_zone="household_focus",
        authority_stage="live",
        why_now="Focus posture affects interruption behavior.",
        metadata=record,
    )
    return record


def _governed_focus_mutation(payload: dict[str, Any]) -> dict[str, Any]:
    request_id = str(uuid.uuid4())
    boundary = runtime.assess_action_boundary(
        zone_id="household_focus",
        arena_id="household.focus.workflow",
        action_type="focus_workflow",
        requested_stage="sandbox_live",
    )
    boundary_decision = str(boundary.get("decision") or "stage")
    boundary_reason = str(boundary.get("reason") or "")
    trust_zone = str(boundary.get("trust_zone") or "household_focus")
    authority_stage = str(boundary.get("authority_stage") or "stage_alert")
    approval_mode = str(boundary.get("approval_mode") or "stage_and_alert")
    arena_status = str(boundary.get("arena_status") or "active")
    focus_active = bool(payload.get("focus_active"))

    if boundary_decision == "deny":
        return {
            "request_id": request_id,
            "status": "blocked_by_boundary",
            "stored": False,
            "focus_active": focus_active,
            "performed_action": "apply_preset",
            "boundary_decision": boundary_decision,
            "boundary_reason": boundary_reason,
            "trust_zone": trust_zone,
            "authority_stage": authority_stage,
            "arena_status": arena_status,
            "approval_mode": approval_mode,
        }

    if boundary_decision != "allow":
        from .models import StagedActionQueueItem

        runtime.trust_support.enqueue_stage_action(
            StagedActionQueueItem(
                request_id=request_id,
                arena_id="household.focus.workflow",
                action_type="focus_apply_preset_review",
                status="awaiting_principal_review",
                created_at=_ts(),
                principal_id="chris",
            )
        )
        return {
            "request_id": request_id,
            "status": "staged_for_review",
            "stored": False,
            "focus_active": focus_active,
            "performed_action": "apply_preset",
            "boundary_decision": boundary_decision,
            "boundary_reason": boundary_reason,
            "trust_zone": trust_zone,
            "authority_stage": authority_stage,
            "arena_status": arena_status,
            "approval_mode": approval_mode,
        }

    _apply_focus_record(payload)
    return {
        "request_id": request_id,
        "status": "stored",
        "stored": True,
        "focus_active": focus_active,
        "performed_action": "apply_preset",
        "boundary_decision": boundary_decision,
        "boundary_reason": boundary_reason,
        "trust_zone": trust_zone,
        "authority_stage": authority_stage,
        "arena_status": arena_status,
        "approval_mode": approval_mode,
    }


def _apple_stage_calendar_prep(title: str, *, start: str = "", location: str = "") -> dict[str, Any]:
    event_title = title.strip() or "Upcoming event"
    event_start = start.strip()
    event_location = location.strip()
    detail_parts = [event_title]
    if event_start:
        detail_parts.append(event_start)
    if event_location:
        detail_parts.append(event_location)
    _record_shared_event(
        domain="calendar",
        kind="stage_ready",
        title="Calendar preparation staged",
        detail=" at ".join(detail_parts[:2]) if len(detail_parts) >= 2 else event_title,
        severity="low",
        source="apple.calendar",
        source_id=f"{event_title}:{event_start}:{event_location}",
        navigation_target="calendar",
        actions=["open"],
        trust_zone="household_schedule",
        authority_stage="staged",
        why_now="The household asked JARVIS to stage prep for an upcoming event from Brief.",
        metadata={"title": event_title, "start": event_start, "location": event_location},
    )
    return {
        "ok": True,
        "status": "staged",
        "title": event_title,
        "start": event_start,
        "location": event_location,
    }


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


def _serialize_stewardship_review(item: dict[str, Any]) -> dict[str, Any]:
    review_id = str(item.get("id") or "")
    return {
        "id": review_id,
        "lane_id": str(item.get("lane_id") or ""),
        "lane_title": str(item.get("lane_title") or ""),
        "status": str(item.get("status") or ""),
        "review_surface": str(item.get("review_surface") or ""),
        "packet_target": str(item.get("packet_target") or ""),
        "boundary_decision": str(item.get("boundary_decision") or ""),
        "boundary_reason": str(item.get("boundary_reason") or ""),
        "approval_mode": str(item.get("approval_mode") or ""),
        "approval_request_id": str(item.get("approval_request_id") or ""),
        "supervision_decision": dict(item.get("supervision_decision") or {}),
        "sandbox_job_id": f"stewardship-review:{review_id}" if review_id else "",
        "timestamp": str(item.get("updated_at") or item.get("created_at") or ""),
    }


def _serialize_calendar_route_job(item: dict[str, Any]) -> dict[str, Any]:
    event_id = str(item.get("event_id") or "").strip()
    job_id = str(item.get("job_id") or f"calendar-route:{event_id}" if event_id else "").strip()
    return {
        "id": event_id or job_id,
        "event_id": event_id,
        "title": str(item.get("title") or ""),
        "status": str(item.get("status") or ""),
        "location": str(item.get("target") or item.get("location") or ""),
        "review_level": str(item.get("review_level") or ""),
        "summary": str(item.get("summary") or ""),
        "sandbox_job_id": job_id,
        "timestamp": str(item.get("updated_at") or item.get("timestamp") or ""),
    }


def _stewardship_primary_agent_id(lane: dict[str, Any]) -> str:
    agents = lane.get("primary_agents") if isinstance(lane.get("primary_agents"), list) else []
    for candidate in agents:
        value = str(candidate or "").strip()
        if value:
            return value
    return "system-steward"


def _stage_stewardship_review_governed_approval(
    *,
    lane: dict[str, Any],
    review: dict[str, Any],
    actor: str,
    detail: str,
) -> tuple[str, dict[str, Any]]:
    try:
        from .approvals import get_approval_guard, get_approval_queue

        guard = get_approval_guard()
        if guard is None:
            return "", {}
        request_id = guard.request_approval(
            agent_id=_stewardship_primary_agent_id(lane),
            agent_label=str(lane.get("name") or lane.get("title") or "Stewardship Lane").strip() or "Stewardship Lane",
            action_type="stage",
            title=f"Stage stewardship review: {str(review.get('lane_title') or lane.get('name') or 'Lane').strip()}",
            description=detail,
            payload={
                "review_id": str(review.get("id") or ""),
                "lane_id": str(review.get("lane_id") or ""),
                "review_surface": str(review.get("review_surface") or ""),
                "packet_target": str(review.get("packet_target") or ""),
                "_sandbox_job_id": f"stewardship-review:{str(review.get('id') or '').strip()}",
            },
            actor_id=actor,
            priority=4,
            tags=["stewardship", "systems", str(review.get("lane_id") or "").strip() or "lane"],
            context={
                "trust_zone_id": str(review.get("trust_zone") or ""),
                "lane_id": str(review.get("lane_id") or ""),
                "requested_outcome": (
                    f"Stage stewardship review for "
                    f"{str(review.get('lane_title') or lane.get('name') or 'lane').strip()} "
                    f"inside {str(review.get('review_surface') or 'systems').strip()}."
                ),
                "touches_external_state": False,
                "reversible": True,
            },
        )
        queue = get_approval_queue()
        item = queue.get_by_id(request_id) if queue is not None else None
        return request_id, dict(getattr(item, "supervision_decision", {}) or {})
    except Exception:
        logger.warning("Failed to create governed stewardship approval", exc_info=True)
        return "", {}


def _stage_calendar_route_governed_approval(
    *,
    actor: str,
    event_id: str,
    title: str,
    location: str,
    maps_url: str,
    trust_zone: str,
    boundary_reason: str,
) -> tuple[str, dict[str, Any]]:
    try:
        from .approvals import get_approval_guard, get_approval_queue

        guard = get_approval_guard()
        if guard is None:
            return "", {}
        request_id = guard.request_approval(
            agent_id="herald",
            agent_label="Herald",
            action_type="calendar_route",
            title=f"Route to {title}",
            description=(
                f"Prepare a bounded calendar route handoff for {title}.\n\n"
                f"Location: {location}\n"
                f"Boundary: {boundary_reason or 'Schedule routing remains governed.'}"
            ),
            payload={
                "event_id": event_id,
                "title": title,
                "location": location,
                "maps_url": maps_url,
                "_sandbox_job_id": f"calendar-route:{event_id}",
            },
            actor_id=actor,
            priority=4,
            tags=["calendar", "route", "systems"],
            context={
                "trust_zone_id": trust_zone,
                "lane_id": "executive-calendar",
                "arena_id": "household.schedule.routing",
                "requested_outcome": f"Prepare a governed route handoff for {title} at {location}",
                "touches_external_state": True,
                "reversible": True,
            },
        )
        queue = get_approval_queue()
        item = queue.get_by_id(request_id) if queue is not None else None
        return request_id, dict(getattr(item, "supervision_decision", {}) or {})
    except Exception:
        logger.warning("Failed to create governed calendar route approval", exc_info=True)
        return "", {}


def _governance_proposal_domains(lane_id: str, packet_targets: list[str], review_surfaces: list[str]) -> list[str]:
    values = [str(lane_id).strip().lower(), *[str(item).strip().lower() for item in packet_targets], *[str(item).strip().lower() for item in review_surfaces]]
    domains: list[str] = []
    for value in values:
        if not value:
            continue
        if "family" in value or "home" in value:
            domain = "family"
        elif "executive" in value or "brief" in value:
            domain = "growth"
        elif "system" in value or "admin" in value:
            domain = "approvals"
        else:
            domain = value.split("-")[0]
        if domain and domain not in domains:
            domains.append(domain)
    return domains or ["approvals"]


def _build_governance_proposal_rows(reviews: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def _dominant_value(counts: dict[str, int]) -> str:
        ranked = [
            (value, int(total or 0))
            for value, total in counts.items()
            if str(value).strip() and int(total or 0) > 0
        ]
        if not ranked:
            return ""
        ranked.sort(key=lambda item: (item[1], item[0]), reverse=True)
        return str(ranked[0][0]).strip()

    groups: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(reviews):
        if not isinstance(item, dict):
            continue
        status = str(item.get("status") or "").strip().lower()
        if status not in {"approved", "retired", "rerouted"}:
            continue
        lane_id = str(item.get("lane_id") or "").strip() or f"lane-{index}"
        lane_title = str(item.get("lane_title") or "Stewardship Lane").strip() or "Stewardship Lane"
        group = groups.setdefault(
            lane_id,
            {
                "lane_id": lane_id,
                "lane_title": lane_title,
                "approved": 0,
                "retired": 0,
                "rerouted": 0,
                "review_surface_counts": {},
                "packet_target_counts": {},
                "latest_timestamp": "",
            },
        )
        group[status] = int(group.get(status) or 0) + 1
        review_surface = str(item.get("review_surface") or "").strip()
        if review_surface:
            counts = cast(dict[str, int], group["review_surface_counts"])
            counts[review_surface] = int(counts.get(review_surface) or 0) + 1
        packet_target = str(item.get("packet_target") or "").strip()
        if packet_target:
            counts = cast(dict[str, int], group["packet_target_counts"])
            counts[packet_target] = int(counts.get(packet_target) or 0) + 1
        timestamp = str(item.get("updated_at") or item.get("created_at") or "").strip()
        if timestamp and timestamp > str(group.get("latest_timestamp") or ""):
            group["latest_timestamp"] = timestamp

    rows: list[dict[str, Any]] = []
    ranked_groups = sorted(
        groups.values(),
        key=lambda item: (
            int(item.get("approved") or 0) + int(item.get("retired") or 0) + int(item.get("rerouted") or 0),
            str(item.get("latest_timestamp") or ""),
        ),
        reverse=True,
    )
    for index, group in enumerate(ranked_groups[:3]):
        lane_id = str(group.get("lane_id") or f"lane-{index}")
        lane_title = str(group.get("lane_title") or "Stewardship Lane").strip() or "Stewardship Lane"
        approved = int(group.get("approved") or 0)
        retired = int(group.get("retired") or 0)
        rerouted = int(group.get("rerouted") or 0)
        total = approved + retired + rerouted
        if total <= 0:
            continue
        review_surface = _dominant_value(cast(dict[str, int], group.get("review_surface_counts") or {}))
        packet_target = _dominant_value(cast(dict[str, int], group.get("packet_target_counts") or {}))
        domains = _governance_proposal_domains(
            lane_id,
            [packet_target] if packet_target else [],
            [review_surface] if review_surface else [],
        )
        if (rerouted + retired) > approved:
            summary = (
                f"{lane_title} has been rerouted or retired {rerouted + retired} of {total} reviewed times, "
                f"which suggests its rollout posture is still narrower than a live lane."
            )
            recommendation = (
                f"Keep {lane_title} staged through "
                f"{review_surface.title() if review_surface else 'review surfaces'} "
                f"until a cleaner approval pattern emerges."
            )
            confidence = "high" if total >= 3 else "emerging"
            policy_effects: dict[str, Any] = {
                "queue_bias": 1,
                "require_explicit_approval": True,
                "preferred_review_surface": review_surface or "briefing",
                "preferred_packet_target": packet_target or "review",
                "boundary_decision_override": "stage",
                "approval_mode_override": "stage_and_alert",
            }
        elif approved >= 2:
            summary = (
                f"{lane_title} has been approved {approved} of {total} reviewed times into "
                f"{packet_target or 'shared'} without repeated fallback."
            )
            recommendation = (
                f"Shape the next governance proposal around promoting {lane_title} toward a lighter review posture "
                f"for {packet_target or 'the current target lane'}."
            )
            confidence = "high" if approved >= 3 else "medium"
            policy_effects = {
                "queue_bias": 0,
                "require_explicit_approval": False,
                "preferred_review_surface": review_surface or "briefing",
                "preferred_packet_target": packet_target or "briefing",
                "boundary_decision_override": "allow",
                "approval_mode_override": "notify_only",
            }
        else:
            summary = (
                f"{lane_title} shows a mixed review pattern across {total} decisions, so JARVIS should keep "
                f"learning from how you route and retire this lane."
            )
            recommendation = (
                f"Keep {lane_title} under review and watch whether "
                f"{packet_target or 'the target lane'} becomes consistently approvable."
            )
            confidence = "emerging"
            policy_effects = {
                "queue_bias": 0,
                "require_explicit_approval": False,
                "preferred_review_surface": review_surface or "briefing",
                "preferred_packet_target": packet_target or "briefing",
                "boundary_decision_override": "stage",
                "approval_mode_override": "review_as_needed",
            }
        rows.append(
            {
                "id": f"governance-{lane_id}",
                "title": f"{lane_title} rollout posture should be codified",
                "kind": "rollout-posture",
                "status": "trusted" if confidence in {"high", "medium"} else "candidate",
                "summary": summary,
                "promotion_reason": recommendation,
                "confidence": confidence,
                "lane_id": lane_id,
                "lane_title": lane_title,
                "review_surface": review_surface,
                "packet_target": packet_target,
                "domains": domains,
                "policy_effects": policy_effects,
            }
        )
    return rows


def _reconcile_shared_notifications(
    *,
    watch_status: dict[str, Any],
    home_state: dict[str, Any],
    calendar_payload: dict[str, Any],
    reminders_payload: dict[str, Any],
    focus_payload: dict[str, Any],
    latest_sound: dict[str, Any],
    latest_scan: dict[str, Any],
) -> None:
    posture = _compute_interruption_posture(
        watch_status=watch_status,
        home_state=home_state,
        focus_payload=focus_payload,
    )

    needs_count = int(watch_status.get("needs_count") or 0)
    if needs_count > 0:
        delivery_mode, decision_reason = _choose_delivery_mode(
            default_mode="badge_only",
            severity="high" if needs_count >= 3 else "medium",
            category="approval",
            posture=posture,
        )
        _notification_center.upsert(
            source_key="needs:pending",
            category="approval",
            title="Approvals waiting",
            detail=f"{needs_count} approval request" + ("s are" if needs_count != 1 else " is") + " waiting for attention.",
            severity="high" if needs_count >= 3 else "medium",
            delivery_mode=delivery_mode,
            navigation_target="needs",
            available_actions=["open", "dismiss"],
            why_now="Pending approvals are part of the current household attention load.",
            decision_reason=decision_reason,
            posture_snapshot=posture,
            source_summary="Approval queue",
            metadata={"needs_count": needs_count},
        )

    next_event = {}
    calendar_events = calendar_payload.get("events") if isinstance(calendar_payload, dict) else []
    if isinstance(calendar_events, list):
        ordered = [event for event in calendar_events if isinstance(event, dict)]
        ordered.sort(key=lambda item: str(item.get("start") or ""))
        next_event = ordered[0] if ordered else {}
    event_title = str(next_event.get("title") or "").strip()
    event_start = str(next_event.get("start") or "").strip()
    minutes_away = _iso_minutes_away(event_start)
    if event_title and minutes_away is not None and -60 <= minutes_away <= 24 * 60:
        default_mode = "hold_for_brief" if minutes_away > 60 else "badge_only"
        delivery_mode, decision_reason = _choose_delivery_mode(
            default_mode=default_mode,
            severity="medium" if minutes_away <= 120 else "low",
            category="household",
            posture=posture,
        )
        _notification_center.upsert(
            source_key=f"calendar:{event_title}:{event_start}",
            category="household",
            title=f"Prepare for {event_title}",
            detail=f"Next event starts {('in ' + str(minutes_away) + ' min') if minutes_away >= 0 else 'soon'}" + (f" at {event_start}" if event_start else "."),
            severity="medium" if minutes_away <= 120 else "low",
            delivery_mode=delivery_mode,
            navigation_target="calendar",
            available_actions=["open", "stage_prep", "dismiss"],
            why_now="The next calendar event is within the household planning window.",
            decision_reason=decision_reason,
            posture_snapshot=posture,
            source_summary="Calendar",
            metadata={"title": event_title, "start": event_start},
        )

    reminders = reminders_payload.get("reminders") if isinstance(reminders_payload, dict) else []
    if isinstance(reminders, list):
        open_reminders = [
            reminder for reminder in reminders
            if isinstance(reminder, dict) and not bool(reminder.get("completed"))
        ]
    else:
        open_reminders = []
    if open_reminders:
        top = open_reminders[0]
        reminder_id = str(top.get("id") or "").strip()
        delivery_mode, decision_reason = _choose_delivery_mode(
            default_mode="hold_for_brief",
            severity="medium" if len(open_reminders) >= 3 else "low",
            category="household",
            posture=posture,
        )
        _notification_center.upsert(
            source_key=f"reminders:{len(open_reminders)}",
            category="household",
            title="Reminders need attention",
            detail=str(top.get("title") or "Outstanding reminders are waiting."),
            severity="medium" if len(open_reminders) >= 3 else "low",
            delivery_mode=delivery_mode,
            navigation_target="workshop",
            available_actions=["open", "complete_reminder", "snooze_reminder", "dismiss"],
            why_now="Open reminders are part of today's active load.",
            decision_reason=decision_reason,
            posture_snapshot=posture,
            source_summary="Reminders",
            metadata={
                "count": len(open_reminders),
                "reminder_id": reminder_id,
                "reminder_title": str(top.get("title") or ""),
                "due": str(top.get("due") or ""),
            },
        )

    alerts = home_state.get("alerts") or []
    if isinstance(alerts, list) and alerts:
        first_alert = alerts[0]
        delivery_mode, decision_reason = _choose_delivery_mode(
            default_mode="deliver_now",
            severity="high",
            category="household",
            posture=posture,
        )
        _notification_center.upsert(
            source_key=f"home-alert:{str(first_alert)}",
            category="household",
            title="Household alert",
            detail=str(first_alert),
            severity="high",
            delivery_mode=delivery_mode,
            navigation_target="home",
            available_actions=["open", "resolve"],
            why_now="The home surface is reporting an active alert.",
            decision_reason=decision_reason,
            posture_snapshot=posture,
            source_summary="Home state",
        )

    if bool(focus_payload.get("focus_active")):
        delivery_mode, decision_reason = _choose_delivery_mode(
            default_mode="quiet_store",
            severity="low",
            category="system",
            posture=posture,
        )
        _notification_center.upsert(
            source_key="focus:active",
            category="system",
            title="Focus is active",
            detail="JARVIS should keep interruptions quieter right now.",
            severity="low",
            delivery_mode=delivery_mode,
            navigation_target="systems",
            available_actions=["open", "dismiss"],
            why_now="Current focus state changes how notifications should be delivered.",
            decision_reason=decision_reason,
            posture_snapshot=posture,
            source_summary="Focus",
            metadata={"source": focus_payload.get("source")},
        )

    sound_label = str(latest_sound.get("classification") or latest_sound.get("label") or latest_sound.get("sound") or "").strip()
    if sound_label and _is_recent_iso(str(latest_sound.get("received_at") or ""), minutes=120):
        sound_severity = "medium" if _coerce_float(latest_sound.get("confidence"), 0.0) >= 0.7 else "low"
        delivery_mode, decision_reason = _choose_delivery_mode(
            default_mode="badge_only",
            severity=sound_severity,
            category="household",
            posture=posture,
        )
        _notification_center.upsert(
            source_key=f"sound:{sound_label}:{str(latest_sound.get('received_at') or '')}",
            category="household",
            title=f"Sound detected: {sound_label}",
            detail=str(latest_sound.get("detail") or "Recent sound analysis detected a notable event."),
            severity=sound_severity,
            delivery_mode=delivery_mode,
            navigation_target="vision",
            available_actions=["open", "resolve", "dismiss"],
            why_now="A recent sound alert may matter to the household.",
            decision_reason=decision_reason,
            posture_snapshot=posture,
            source_summary="Sound Analysis",
            metadata={"confidence": latest_sound.get("confidence")},
        )

    scan_context = str(latest_scan.get("context") or "").strip()
    scan_text = str(latest_scan.get("text") or "").strip()
    if (scan_context or scan_text) and _is_recent_iso(str(latest_scan.get("received_at") or ""), minutes=120):
        delivery_mode, decision_reason = _choose_delivery_mode(
            default_mode="quiet_store",
            severity="low",
            category="system",
            posture=posture,
        )
        _notification_center.upsert(
            source_key=f"vision:{scan_context}:{str(latest_scan.get('received_at') or '')}",
            category="system",
            title=scan_context or "Vision scan captured",
            detail=scan_text[:180] or "A recent scan is available for review.",
            severity="low",
            delivery_mode=delivery_mode,
            navigation_target="vision",
            available_actions=["open", "dismiss"],
            why_now="Recent vision captures are available for inspection.",
            decision_reason=decision_reason,
            posture_snapshot=posture,
            source_summary="Vision",
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
        actor_id = str(payload.get("actor_id") or payload.get("actor") or "chris").strip()
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

        while_you_were_away = _build_while_you_were_away(actor)
        home_aggregate = runtime.chamber_home_aggregate(
            actor,
            chamber_packet=packet if isinstance(packet, dict) else {},
            home_state=home_state if isinstance(home_state, dict) else {},
            home_context=home_context if isinstance(home_context, dict) else {},
            watch_status=watch_status if isinstance(watch_status, dict) else {},
            while_you_were_away=while_you_were_away,
        )

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
            "continuity":     _build_briefing_continuity(actor),
            "while_you_were_away": while_you_were_away,
            "command_items":  list(home_aggregate.get("command_items") or []) or _build_briefing_command_items(
                home_context=home_context,
                home_state=home_state,
                watch_status=watch_status,
            ),
            "home_aggregate": home_aggregate,
        }
        return _ok(data)

    @app.get("/api/apple/carplay/ops")
    async def apple_carplay_ops():
        overview = await asyncio.to_thread(_build_carplay_ops_overview, runtime)
        return _ok(overview)

    @app.post("/api/apple/carplay/ops/focus")
    async def apple_carplay_ops_focus(payload: dict):
        module = str(payload.get("module") or "").strip()
        route = str(payload.get("route") or "").strip()
        actor = str(payload.get("actor") or "chris").strip() or "chris"
        reason = str(payload.get("reason") or "").strip()
        if not module:
            raise HTTPException(status_code=400, detail="module is required")
        if not route:
            raise HTTPException(status_code=400, detail="route is required")
        if not reason:
            reason = f"CarPlay promoted {module} into the shared progress focus lane."
        entry = await asyncio.to_thread(
            _save_carplay_ops_focus,
            module=module,
            route=route,
            actor=actor,
            reason=reason,
        )
        return _ok(entry)

    @app.post("/api/apple/carplay/agents/{agent_id}/queue-run")
    async def apple_carplay_agent_queue(agent_id: str, payload: dict | None = None):
        payload = payload if isinstance(payload, dict) else {}
        actor = str(payload.get("actor") or "chris").strip() or "chris"
        try:
            result = await asyncio.to_thread(
                _queue_carplay_agent_run,
                agent_id=agent_id,
                actor=actor,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return _ok(result)

    @app.post("/api/apple/carplay/supervision/{request_id}/{action}")
    async def apple_carplay_supervision_action(request_id: str, action: str, payload: dict | None = None):
        payload = payload if isinstance(payload, dict) else {}
        actor = str(payload.get("actor") or "chris").strip() or "chris"
        reason = str(payload.get("reason") or "").strip()
        try:
            result = await asyncio.to_thread(
                _resolve_carplay_supervision_item,
                runtime,
                request_id=request_id,
                action=action,
                actor=actor,
                reason=reason,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _ok(result)

    @app.post("/api/apple/carplay/huddle/party-mode/start")
    async def apple_carplay_huddle_start(payload: dict | None = None):
        payload = payload if isinstance(payload, dict) else {}
        actor = str(payload.get("actor") or "chris").strip() or "chris"
        result = await asyncio.to_thread(_start_carplay_huddle_party_mode, runtime, actor=actor)
        return _ok(result)

    @app.post("/api/apple/carplay/huddle/ideas/{idea_id}/queue")
    async def apple_carplay_huddle_queue(idea_id: str, payload: dict | None = None):
        payload = payload if isinstance(payload, dict) else {}
        actor = str(payload.get("actor") or "chris").strip() or "chris"
        try:
            result = await asyncio.to_thread(_queue_carplay_huddle_idea, idea_id=idea_id, actor=actor)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return _ok(result)

    @app.post("/api/apple/carplay/huddle/ideas/{idea_id}/pass")
    async def apple_carplay_huddle_pass(idea_id: str, payload: dict | None = None):
        payload = payload if isinstance(payload, dict) else {}
        actor = str(payload.get("actor") or "chris").strip() or "chris"
        try:
            result = await asyncio.to_thread(_pass_carplay_huddle_idea, idea_id=idea_id, actor=actor)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return _ok(result)

    @app.post("/api/apple/carplay/huddle/ideas/{idea_id}/research-now")
    async def apple_carplay_huddle_research(idea_id: str, payload: dict | None = None):
        payload = payload if isinstance(payload, dict) else {}
        actor = str(payload.get("actor") or "chris").strip() or "chris"
        try:
            result = await asyncio.to_thread(_research_carplay_huddle_idea_now, idea_id=idea_id, actor=actor)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return _ok(result)

    @app.get("/api/apple/while-you-were-away")
    async def apple_while_you_were_away(actor: str = "chris"):
        return _ok(_build_while_you_were_away(actor))

    @app.post("/api/apple/stewardship-lanes/{lane_id}/stage-review")
    async def apple_stage_stewardship_lane_review(lane_id: str, payload: dict | None = None):
        payload = payload if isinstance(payload, dict) else {}
        actor = str(payload.get("actor") or "chris").strip() or "chris"
        note = str(payload.get("note") or "").strip()

        lane_contracts = runtime.stewardship_lane_contracts(actor)
        lane = next((item for item in lane_contracts if str(item.get("id") or "").strip() == lane_id), None)
        if lane is None:
            raise HTTPException(status_code=404, detail="Stewardship lane not found")

        primitive = lane.get("execution_primitive") if isinstance(lane.get("execution_primitive"), dict) else {}
        request_id = f"lane-review::{lane_id}::{uuid.uuid4()}"
        boundary_decision = str(primitive.get("boundary_decision") or "stage")
        boundary_reason = str(primitive.get("boundary_reason") or "This lane should be surfaced as a deliberate review before execution widens.")
        trust_zone = str(primitive.get("trust_zone") or "household_attention")
        authority_stage = str(primitive.get("authority_stage") or "draft")
        arena_status = str(primitive.get("arena_status") or "active")
        approval_mode = str(primitive.get("approval_mode") or "stage_and_alert")
        review_surface = str(primitive.get("review_surface") or "briefing")
        packet_target = str(primitive.get("packet_target") or "briefing")
        lane_title = str(lane.get("title") or "Stewardship Lane").strip() or "Stewardship Lane"
        lane_summary = str(primitive.get("route_summary") or lane.get("summary") or "").strip()

        detail = lane_summary or f"{lane_title} is ready to return for deliberate review."
        if note:
            detail = f"{detail} Note: {note}"

        event = _record_shared_event(
            domain="stewardship",
            kind="review_stage",
            title=f"{lane_title} review staged",
            detail=detail,
            severity="medium" if boundary_decision != "deny" else "high",
            actor=actor,
            source="apple.stewardship_lane",
            source_id=request_id,
            navigation_target=review_surface,
            actions=["open", "dismiss"],
            trust_zone=trust_zone,
            authority_stage=authority_stage,
            why_now=f"The {lane_title} lane was deliberately staged for review from the Apple client.",
            metadata={
                "lane_id": lane_id,
                "packet_target": packet_target,
                "review_surface": review_surface,
                "boundary_decision": boundary_decision,
                "boundary_reason": boundary_reason,
                "approval_mode": approval_mode,
                "note": note,
            },
        )
        notification = _create_notification_from_event(
            event,
            category="assistant",
            delivery_mode="badge_only",
            available_actions=["open", "dismiss", "resolve"],
            source_summary="Stewardship lane review",
        )
        review = _stewardship_reviews.upsert(
            lane_id=lane_id,
            lane_title=lane_title,
            review_surface=review_surface,
            packet_target=packet_target,
            boundary_decision=boundary_decision,
            boundary_reason=boundary_reason,
            trust_zone=trust_zone,
            authority_stage=authority_stage,
            arena_status=arena_status,
            approval_mode=approval_mode,
            actor=actor,
            note=note,
            event_id=str(event.get("id") or ""),
            notification_id=str(notification.get("id") or ""),
        )
        approval_request_id, supervision_decision = _stage_stewardship_review_governed_approval(
            lane=lane,
            review=review,
            actor=actor,
            detail=detail,
        )
        if approval_request_id:
            refreshed = _stewardship_reviews.update(
                str(review.get("id") or ""),
                {
                    "approval_request_id": approval_request_id,
                    "supervision_decision": supervision_decision,
                },
            )
            if refreshed is not None:
                review = refreshed

        return _ok(
            {
                "request_id": request_id,
                "review_id": str(review.get("id") or ""),
                "approval_request_id": str(review.get("approval_request_id") or ""),
                "supervision_decision": dict(review.get("supervision_decision") or {}),
                "sandbox_job_id": f"stewardship-review:{str(review.get('id') or '').strip()}" if str(review.get("id") or "").strip() else "",
                "status": "review_staged" if boundary_decision != "deny" else "blocked_by_boundary",
                "performed_action": "stage_lane_review",
                "lane_id": lane_id,
                "lane_title": lane_title,
                "review_surface": review_surface,
                "packet_target": packet_target,
                "boundary_decision": boundary_decision,
                "boundary_reason": boundary_reason,
                "trust_zone": trust_zone,
                "authority_stage": authority_stage,
                "arena_status": arena_status,
                "approval_mode": approval_mode,
            }
        )

    @app.post("/api/apple/stewardship-reviews/{review_id}/sandbox-execute")
    async def apple_execute_stewardship_review_sandbox(review_id: str, payload: dict | None = None):
        payload = payload if isinstance(payload, dict) else {}
        actor = str(payload.get("actor") or "chris").strip() or "chris"
        triggered_by = str(payload.get("triggered_by") or "apple-stewardship-review").strip() or "apple-stewardship-review"
        review = _stewardship_reviews.get(review_id)
        if review is None:
            raise HTTPException(status_code=404, detail="Stewardship review not found")
        sandbox_job_id = f"stewardship-review:{review_id}"
        try:
            result = runtime.execute_sandbox_job(actor, sandbox_job_id, triggered_by=triggered_by)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        job = result.get("job") if isinstance(result.get("job"), dict) else {}
        active_run = result.get("active_run") if isinstance(result.get("active_run"), dict) else {}
        queue = result.get("queue") if isinstance(result.get("queue"), dict) else {}
        return _ok(
            {
                "ok": bool(result.get("ok")),
                "accepted": bool(result.get("accepted")),
                "review_id": review_id,
                "sandbox_job_id": sandbox_job_id,
                "status": str(job.get("status") or ""),
                "message": str(result.get("message") or ""),
                "active_run_id": str(active_run.get("run_id") or ""),
                "queue_active_count": int(queue.get("active_count") or 0),
            }
        )

    @app.post("/api/apple/stewardship-reviews/{review_id}/approve")
    async def apple_approve_stewardship_review(review_id: str, payload: dict | None = None):
        payload = payload if isinstance(payload, dict) else {}
        actor = str(payload.get("actor") or "chris").strip() or "chris"
        review = _stewardship_reviews.get(review_id)
        if review is None:
            raise HTTPException(status_code=404, detail="Stewardship review not found")
        approval_request_id = str(review.get("approval_request_id") or "").strip()
        execution_result: dict[str, Any] = {}
        if approval_request_id:
            try:
                from .approvals import get_approval_guard, get_approval_queue

                queue = get_approval_queue()
                guard = get_approval_guard()
                if queue is not None and guard is not None:
                    approved_item = queue.approve(approval_request_id, approved_by=actor)
                    if approved_item is None:
                        raise HTTPException(status_code=409, detail="Stewardship review approval is not pending")
                    execution_result = dict(guard.execute_approved(approval_request_id) or {})
                    if str(execution_result.get("status") or "").strip().lower() == "error":
                        raise HTTPException(status_code=400, detail=str(execution_result.get("detail") or "Governed execution failed"))
            except HTTPException:
                raise
            except Exception as exc:
                raise HTTPException(status_code=500, detail=f"Governed approval execution failed: {exc}") from exc

        updated = _stewardship_reviews.update(
            review_id,
            {
                "status": "approved",
                "last_actor": actor,
                "supervision_decision": dict(execution_result.get("supervision_decision") or review.get("supervision_decision") or {}),
            },
        )
        if updated is None:
            raise HTTPException(status_code=404, detail="Stewardship review not found")
        notification_id = str(updated.get("notification_id") or "")
        if notification_id:
            _notification_center.update_status(
                notification_id,
                "resolved",
                reason="Stewardship review was approved from Systems/Admin.",
            )
        event = _record_shared_event(
            domain="stewardship",
            kind="resolved",
            title=f"{str(updated.get('lane_title') or 'Stewardship lane')} approved",
            detail=str(updated.get("boundary_reason") or ""),
            severity="medium",
            actor=actor,
            source="apple.stewardship_review.approve",
            source_id=review_id,
            navigation_target=str(updated.get("review_surface") or ""),
            actions=["open"],
            trust_zone=str(updated.get("trust_zone") or "household_attention"),
            authority_stage=str(updated.get("authority_stage") or "live"),
            why_now="A staged stewardship review was approved from Systems/Admin.",
            metadata={"review_id": review_id, "lane_id": str(updated.get("lane_id") or ""), "status": "approved"},
        )
        _create_notification_from_event(
            event,
            category="assistant",
            delivery_mode="badge_only",
            available_actions=["open", "resolve"],
            source_summary="Stewardship lane rollout",
        )
        return _ok(
            {
                "request_id": review_id,
                "review_id": review_id,
                "status": "approved",
                "performed_action": "approve_stewardship_review",
                "approval_request_id": approval_request_id,
                "supervision_decision": dict(updated.get("supervision_decision") or {}),
                "execution_status": str(execution_result.get("status") or ""),
                "lane_id": str(updated.get("lane_id") or ""),
                "lane_title": str(updated.get("lane_title") or ""),
                "review_surface": str(updated.get("review_surface") or ""),
                "packet_target": str(updated.get("packet_target") or ""),
                "boundary_decision": str(updated.get("boundary_decision") or ""),
                "boundary_reason": str(updated.get("boundary_reason") or ""),
                "approval_mode": str(updated.get("approval_mode") or ""),
            }
        )

    @app.post("/api/apple/stewardship-reviews/{review_id}/route")
    async def apple_route_stewardship_review(review_id: str, payload: dict | None = None):
        payload = payload if isinstance(payload, dict) else {}
        actor = str(payload.get("actor") or "chris").strip() or "chris"
        review_surface = str(payload.get("review_surface") or "").strip().lower()
        packet_target = str(payload.get("packet_target") or "").strip().lower()
        review = _stewardship_reviews.get(review_id)
        if review is None:
            raise HTTPException(status_code=404, detail="Stewardship review not found")

        current_surface = str(review.get("review_surface") or "brief")
        current_target = str(review.get("packet_target") or "briefing")
        next_surface = review_surface or ("home" if current_surface == "brief" else "brief")
        next_target = packet_target or ("family" if next_surface == "home" else "executive")
        updated = _stewardship_reviews.update(
            review_id,
            {
                "review_surface": next_surface,
                "packet_target": next_target,
                "status": "review_staged",
                "last_actor": actor,
            },
        )
        if updated is None:
            raise HTTPException(status_code=404, detail="Stewardship review not found")
        event = _record_shared_event(
            domain="stewardship",
            kind="routed",
            title=f"{str(updated.get('lane_title') or 'Stewardship lane')} rerouted",
            detail=f"Review rerouted to {next_surface}.",
            severity="low",
            actor=actor,
            source="apple.stewardship_review.route",
            source_id=review_id,
            navigation_target=next_surface,
            actions=["open"],
            trust_zone=str(updated.get("trust_zone") or "household_attention"),
            authority_stage=str(updated.get("authority_stage") or "draft"),
            why_now="A staged stewardship review was rerouted from Systems/Admin.",
            metadata={"review_id": review_id, "lane_id": str(updated.get("lane_id") or ""), "review_surface": next_surface, "packet_target": next_target},
        )
        _create_notification_from_event(
            event,
            category="assistant",
            delivery_mode="badge_only",
            available_actions=["open", "dismiss"],
            source_summary="Stewardship lane reroute",
        )
        return _ok(
            {
                "request_id": review_id,
                "review_id": review_id,
                "status": "rerouted",
                "performed_action": "route_stewardship_review",
                "lane_id": str(updated.get("lane_id") or ""),
                "lane_title": str(updated.get("lane_title") or ""),
                "review_surface": str(updated.get("review_surface") or ""),
                "packet_target": str(updated.get("packet_target") or ""),
                "boundary_decision": str(updated.get("boundary_decision") or ""),
                "boundary_reason": str(updated.get("boundary_reason") or ""),
                "approval_mode": str(updated.get("approval_mode") or ""),
            }
        )

    @app.post("/api/apple/stewardship-reviews/{review_id}/retire")
    async def apple_retire_stewardship_review(review_id: str, payload: dict | None = None):
        payload = payload if isinstance(payload, dict) else {}
        actor = str(payload.get("actor") or "chris").strip() or "chris"
        reason = str(payload.get("reason") or "Stewardship review retired from Systems/Admin.").strip()
        review = _stewardship_reviews.get(review_id)
        if review is None:
            raise HTTPException(status_code=404, detail="Stewardship review not found")
        approval_request_id = str(review.get("approval_request_id") or "").strip()
        if approval_request_id:
            try:
                from .approvals import get_approval_queue

                queue = get_approval_queue()
                if queue is not None:
                    queue.cancel(approval_request_id)
            except Exception:
                logger.warning("Failed to cancel governed stewardship approval %s", approval_request_id, exc_info=True)

        updated = _stewardship_reviews.update(
            review_id,
            {
                "status": "retired",
                "last_actor": actor,
                "boundary_reason": reason or str(review.get("boundary_reason") or ""),
            },
        )
        if updated is None:
            raise HTTPException(status_code=404, detail="Stewardship review not found")
        notification_id = str(updated.get("notification_id") or "")
        if notification_id:
            _notification_center.update_status(
                notification_id,
                "dismissed",
                reason="Stewardship review was retired from Systems/Admin.",
            )
        event = _record_shared_event(
            domain="stewardship",
            kind="retired",
            title=f"{str(updated.get('lane_title') or 'Stewardship lane')} retired",
            detail=reason,
            severity="low",
            actor=actor,
            source="apple.stewardship_review.retire",
            source_id=review_id,
            navigation_target=str(updated.get("review_surface") or ""),
            actions=["open"],
            trust_zone=str(updated.get("trust_zone") or "household_attention"),
            authority_stage=str(updated.get("authority_stage") or "draft"),
            why_now="A staged stewardship review was retired from Systems/Admin.",
            metadata={"review_id": review_id, "lane_id": str(updated.get("lane_id") or ""), "status": "retired"},
        )
        return _ok(
            {
                "request_id": review_id,
                "review_id": review_id,
                "status": "retired",
                "performed_action": "retire_stewardship_review",
                "approval_request_id": approval_request_id,
                "lane_id": str(updated.get("lane_id") or ""),
                "lane_title": str(updated.get("lane_title") or ""),
                "review_surface": str(updated.get("review_surface") or ""),
                "packet_target": str(updated.get("packet_target") or ""),
                "boundary_decision": str(updated.get("boundary_decision") or ""),
                "boundary_reason": str(updated.get("boundary_reason") or ""),
                "approval_mode": str(updated.get("approval_mode") or ""),
            }
        )

    @app.post("/api/apple/governance-proposals/{proposal_id}/promote")
    async def apple_promote_governance_proposal(proposal_id: str, payload: dict | None = None):
        payload = payload if isinstance(payload, dict) else {}
        actor = str(payload.get("actor") or "chris").strip() or "chris"
        basis_override = str(payload.get("basis") or "").strip()

        reviews = _stewardship_reviews.list(include_closed=True, limit=0)
        proposal = next(
            (
                dict(item)
                for item in _build_governance_proposal_rows(reviews)
                if str(item.get("id") or "").strip() == proposal_id
            ),
            None,
        )
        if proposal is None:
            raise HTTPException(status_code=404, detail="Governance proposal not found")

        lane_id = str(proposal.get("lane_id") or "").strip()
        lane_title = str(proposal.get("lane_title") or "Governance Proposal").strip()
        domains = [str(item).strip() for item in list(proposal.get("domains", [])) if str(item).strip()]
        domain = domains[0] if domains else _governance_proposal_domains(
            lane_id,
            [str(proposal.get("packet_target") or "").strip()],
            [str(proposal.get("review_surface") or "").strip()],
        )[0]
        candidate = {
            "candidate_id": proposal_id,
            "rule_id": f"rule-{proposal_id}",
            "title": str(proposal.get("title") or f"{lane_title} rollout posture should be codified").strip(),
            "summary": str(proposal.get("summary") or f"{lane_title} has enough reviewed history to shape a reusable rollout rule.").strip(),
            "kind": "rollout-posture",
            "status": "candidate",
            "domains": domains or _governance_proposal_domains(
                lane_id,
                [str(proposal.get("packet_target") or "").strip()],
                [str(proposal.get("review_surface") or "").strip()],
            ),
            "actors": ["Chris"],
            "agent_ids": runtime._agent_ids_for_domain(domain),
            "evidence": {
                "source": "governance-learning",
                "lane_id": lane_id,
                "review_surface": str(proposal.get("review_surface") or ""),
                "packet_target": str(proposal.get("packet_target") or ""),
            },
            "policy_effects": dict(proposal.get("policy_effects") or {}),
            "promotion_reason": basis_override or f"Codify the learned rollout posture for {lane_title}.",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        doctrine_state = runtime.doctrine_store.load()
        candidates = [dict(item) for item in list(doctrine_state.get("candidates", [])) if isinstance(item, dict)]
        existing_index = next((index for index, item in enumerate(candidates) if str(item.get("candidate_id") or "").strip() == proposal_id), None)
        if existing_index is None:
            candidates.append(candidate)
        else:
            candidates[existing_index] = {**candidates[existing_index], **candidate}
        doctrine_state["candidates"] = candidates
        runtime.doctrine_store.save(doctrine_state)
        promoted = runtime.promote_doctrine_candidate(
            proposal_id,
            promoted_by=actor,
            basis=basis_override or candidate["promotion_reason"],
        )
        return _ok(
            {
                "proposal_id": proposal_id,
                "candidate_id": proposal_id,
                "title": candidate["title"],
                "status": "promoted",
                "performed_action": "promote_governance_proposal",
                "message": f"{lane_title} was promoted into shared doctrine.",
                "rule_id": str(((promoted.get("rule") or {}) if isinstance(promoted, dict) else {}).get("rule_id") or ""),
            }
        )

    @app.post("/api/apple/governance-proposals/{proposal_id}/dismiss")
    async def apple_dismiss_governance_proposal(proposal_id: str, payload: dict | None = None):
        payload = payload if isinstance(payload, dict) else {}
        actor = str(payload.get("actor") or "chris").strip() or "chris"
        reason = str(payload.get("reason") or "Dismissed from Systems/Admin.").strip()

        reviews = _stewardship_reviews.list(include_closed=True, limit=0)
        proposal = next(
            (
                dict(item)
                for item in _build_governance_proposal_rows(reviews)
                if str(item.get("id") or "").strip() == proposal_id
            ),
            None,
        )
        if proposal is None:
            raise HTTPException(status_code=404, detail="Governance proposal not found")

        lane_id = str(proposal.get("lane_id") or "").strip()
        lane_title = str(proposal.get("lane_title") or "Governance Proposal").strip()
        domains = [str(item).strip() for item in list(proposal.get("domains", [])) if str(item).strip()]
        domain = domains[0] if domains else _governance_proposal_domains(
            lane_id,
            [str(proposal.get("packet_target") or "").strip()],
            [str(proposal.get("review_surface") or "").strip()],
        )[0]
        candidate = {
            "candidate_id": proposal_id,
            "rule_id": f"rule-{proposal_id}",
            "title": str(proposal.get("title") or f"{lane_title} rollout posture should be codified").strip(),
            "summary": str(proposal.get("summary") or f"{lane_title} has enough reviewed history to shape a reusable rollout rule.").strip(),
            "kind": "rollout-posture",
            "status": "candidate",
            "domains": domains or _governance_proposal_domains(
                lane_id,
                [str(proposal.get("packet_target") or "").strip()],
                [str(proposal.get("review_surface") or "").strip()],
            ),
            "actors": ["Chris"],
            "agent_ids": runtime._agent_ids_for_domain(domain),
            "evidence": {
                "source": "governance-learning",
                "lane_id": lane_id,
                "review_surface": str(proposal.get("review_surface") or ""),
                "packet_target": str(proposal.get("packet_target") or ""),
            },
            "policy_effects": dict(proposal.get("policy_effects") or {}),
            "promotion_reason": reason or f"Codify the learned rollout posture for {lane_title}.",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        doctrine_state = runtime.doctrine_store.load()
        candidates = [dict(item) for item in list(doctrine_state.get("candidates", [])) if isinstance(item, dict)]
        existing_index = next((index for index, item in enumerate(candidates) if str(item.get("candidate_id") or "").strip() == proposal_id), None)
        if existing_index is None:
            candidates.append(candidate)
        else:
            candidates[existing_index] = {**candidates[existing_index], **candidate}
        doctrine_state["candidates"] = candidates
        runtime.doctrine_store.save(doctrine_state)
        dismissed = runtime.dismiss_doctrine_candidate(
            proposal_id,
            dismissed_by=actor,
            reason=reason or f"{lane_title} does not need a rollout rule yet.",
        )
        candidate_row = ((dismissed.get("candidate") or {}) if isinstance(dismissed, dict) else {})
        return _ok(
            {
                "proposal_id": proposal_id,
                "candidate_id": proposal_id,
                "title": candidate["title"],
                "status": "dismissed",
                "performed_action": "dismiss_governance_proposal",
                "message": f"{lane_title} governance proposal was dismissed.",
                "rule_id": str(candidate_row.get("rule_id") or ""),
            }
        )

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

        # Keep the quick-status contract fast and lightweight.
        weather = str(status.get("weather") or status.get("weather_summary") or "")
        drift = bool(status.get("drift") or status.get("drift_detected"))

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
        _reconcile_shared_notifications(
            watch_status=watch_status,
            home_state=home_state,
            calendar_payload=calendar_payload if isinstance(calendar_payload, dict) else {},
            reminders_payload=reminders_payload if isinstance(reminders_payload, dict) else {},
            focus_payload=focus_payload if isinstance(focus_payload, dict) else {},
            latest_sound=latest_sound if isinstance(latest_sound, dict) else {},
            latest_scan=latest_scan if isinstance(latest_scan, dict) else {},
        )
        posture = _compute_interruption_posture(
            watch_status=watch_status,
            home_state=home_state,
            focus_payload=focus_payload if isinstance(focus_payload, dict) else {},
        )

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
                        "id": str(reminder.get("id") or ""),
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
                "posture_mode": str(posture.get("mode") or ""),
                "posture_label": str(posture.get("label") or ""),
                "posture_reason": str(posture.get("reason") or ""),
                "recommended_delivery": str(posture.get("recommended_delivery") or ""),
                "quiet_hours": bool(posture.get("quiet_hours")),
                "hour_local": int(posture.get("hour_local") or 0),
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
    # GET /api/apple/focus-state
    # ------------------------------------------------------------------
    @app.get("/api/apple/focus-state")
    async def apple_focus_state():
        data_root = Path("data/apple")
        focus_payload = _safe_read_json(data_root / "focus_state.json", {})
        watch_status = (await apple_status()).get("data") or {}
        home_state = (await apple_home_state()).get("data") or {}
        posture = _compute_interruption_posture(
            watch_status=watch_status,
            home_state=home_state,
            focus_payload=focus_payload if isinstance(focus_payload, dict) else {},
        )
        return _ok(_build_apple_focus_state(
            focus_payload=focus_payload if isinstance(focus_payload, dict) else {},
            posture=posture,
        ))

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
        daily = snapshot.get("daily") if isinstance(snapshot, dict) else []
        daily = daily if isinstance(daily, list) else []
        near_term = snapshot.get("near_term") if isinstance(snapshot, dict) else {}
        near_term = near_term if isinstance(near_term, dict) else {}
        radar = snapshot.get("radar") if isinstance(snapshot, dict) else {}
        radar = radar if isinstance(radar, dict) else {}
        alerts = snapshot.get("alerts") if isinstance(snapshot, dict) else []
        alerts = alerts if isinstance(alerts, list) else []

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
            "daily": [
                {
                    "name": str(item.get("name") or ""),
                    "icon": str(item.get("icon") or ""),
                    "high": item.get("high"),
                    "low": item.get("low"),
                    "rain_pct": item.get("rain_pct"),
                    "forecast": str(item.get("forecast") or ""),
                }
                for item in daily[:7]
                if isinstance(item, dict)
            ],
            "near_term": {
                "window_minutes": int(near_term.get("window_minutes") or 15),
                "summary": str(near_term.get("summary") or ""),
                "hazard_active": bool(near_term.get("hazard_active")),
                "rain_risk_pct": int(near_term.get("rain_risk_pct") or 0),
            },
            "radar": {
                "available": bool(radar.get("available")),
                "source": str(radar.get("source") or ""),
                "station": str(radar.get("station") or ""),
                "viewer_url": str(radar.get("viewer_url") or ""),
                "loop_image_url": str(radar.get("loop_image_url") or ""),
                "base_velocity_loop_url": str(radar.get("base_velocity_loop_url") or ""),
                "posture": {
                    "mode": str(((radar.get("posture") or {}).get("mode")) or ""),
                    "summary": str(((radar.get("posture") or {}).get("summary")) or ""),
                    "should_open": bool(((radar.get("posture") or {}).get("should_open"))),
                } if isinstance(radar.get("posture"), dict) else None,
            },
            "alerts": [
                {
                    "event": str(item.get("event") or ""),
                    "severity": str(item.get("severity") or ""),
                    "headline": str(item.get("headline") or ""),
                    "description": str(item.get("description") or ""),
                }
                for item in alerts[:4]
                if isinstance(item, dict)
            ],
            "alerts_count": len(alerts),
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
        saved = _save_navigation_state(payload)
        last_route = saved.get("last_route") if isinstance(saved.get("last_route"), dict) else {}
        origin = str((last_route or {}).get("origin") or "").strip()
        destination = str((last_route or {}).get("destination") or "").strip()
        if origin and destination:
            saved, _ = _record_navigation_route_history(
                origin=origin,
                destination=destination,
                origin_mode=str(saved.get("selected_origin_mode") or "home").strip() or "home",
                saved_location_id=str(saved.get("selected_saved_location_id") or "").strip(),
                parks_historic_radius_miles=int(saved.get("parks_historic_radius_miles") or 25),
                source_label="Apple navigation state update",
            )
            _record_operator_action(
                actor="Chris",
                domain="navigation",
                action="Update Apple Navigation State",
                detail=f"Persisted route from {origin} to {destination}.",
                why_now="Apple surface selected or refreshed a route destination.",
                result_summary="Navigation continuity updated from Apple route state.",
                route="/navigation-center",
                route_label="Open Navigation",
                related_kind="route-preview",
                related_label=destination,
            )
        return _ok(saved)

    @app.post("/api/apple/navigation/history/{route_id}/resume")
    async def apple_navigation_resume_history(route_id: str):
        route_id = str(route_id or "").strip()
        if not route_id:
            raise HTTPException(status_code=400, detail="route_id is required")
        try:
            resumed = _resume_navigation_route_history(
                route_id=route_id,
                actor="Chris",
                source_label="Apple navigation route history",
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return _ok(
            {
                "status": "resumed",
                "navigation_state": resumed.get("state") or {},
                "route": resumed.get("route") or {},
                "focus": resumed.get("focus") or {},
            }
        )

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
                    payload = item.get("payload") if isinstance(item.get("payload"), dict) else {}
                    context_lines = _approval_context_lines(payload if isinstance(payload, dict) else {})
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
                        "priority": int(item.get("priority") or 5),
                        "tags": item.get("tags") if isinstance(item.get("tags"), list) else [],
                        "requires_confirmation": bool(item.get("requires_confirmation")),
                        "confirmation_phrase": str(item.get("confirmation_phrase") or ""),
                        "target_summary": _approval_target_summary(payload if isinstance(payload, dict) else {}),
                        "context_lines": context_lines,
                    })
            else:
                pending = runtime.list_pending_approvals()
                raw = pending if isinstance(pending, list) else pending.get("items", [])
                for item in raw:
                    if not isinstance(item, dict):
                        continue
                    payload = item.get("payload") if isinstance(item.get("payload"), dict) else {}
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
                        "priority": int(item.get("priority") or 5),
                        "tags": item.get("tags") if isinstance(item.get("tags"), list) else [],
                        "requires_confirmation": bool(item.get("requires_confirmation")),
                        "confirmation_phrase": str(item.get("confirmation_phrase") or ""),
                        "target_summary": _approval_target_summary(payload if isinstance(payload, dict) else {}),
                        "context_lines": _approval_context_lines(payload if isinstance(payload, dict) else {}),
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
        Route a text command from Phone / Siri through local-first JARVIS voice handling.
        Apple surfaces own capture and playback; JARVIS returns the decision payload.
        """
        text = str(payload.get("text") or "").strip()
        actor_id = str(payload.get("actor_id") or payload.get("actor") or "chris").strip()
        conversation_id = str(payload.get("conversation_id") or "").strip()
        if not text:
            raise HTTPException(status_code=400, detail="text is required")

        agent_name = "JARVIS"
        response_text = ""

        try:
            local_handler_result = _apple_voice_try_local_handler(runtime, text, actor_id)
            if local_handler_result is not None:
                response_text, agent_name = local_handler_result
            else:
                response_text, agent_name = _apple_voice_local_llm(
                    runtime,
                    actor_id=actor_id,
                    text=text,
                )
        except Exception as exc:
            logger.warning("apple_speak local-first flow failed: %s", exc)
            response_text = (
                "The local voice path hit a problem. If you want, I can use a non-local model after you approve it."
            )

        resolved_conversation_id = conversation_id
        try:
            thread = runtime.conversation_store.ensure(actor_id, "office", conversation_id, source="apple_voice")
            resolved_conversation_id = str(thread.get("conversation_id") or resolved_conversation_id)
            runtime.conversation_store.append_turn(
                resolved_conversation_id,
                role="user",
                text=text,
                actor=actor_id,
                room="office",
                source="apple_voice",
            )
            runtime.conversation_store.append_turn(
                resolved_conversation_id,
                role="assistant",
                text=response_text,
                actor=actor_id,
                room="office",
                source="apple_voice",
                metadata={"provider": "apple_voice", "model": "local-first"},
            )
            runtime._invalidate_snapshot_cache(actor_id, surfaces=("chat_state",))
        except Exception as exc:
            logger.warning("apple_speak conversation capture failed: %s", exc)

        response_payload = _build_apple_voice_payload(response_text=response_text, agent_name=agent_name)
        response_payload["conversation_id"] = resolved_conversation_id
        response_payload["follow_up_suggestions"] = _build_apple_voice_followups(text)
        return _ok(response_payload)

    # ------------------------------------------------------------------
    # GET /api/apple/voice/state
    # ------------------------------------------------------------------
    @app.get("/api/apple/voice/state")
    async def apple_voice_state(actor: str = "chris", conversation_id: str = ""):
        return _ok(_build_apple_voice_state(actor, conversation_id))

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
        readiness_factors: list[dict[str, Any]] = []
        thor_snapshot: dict[str, Any] | None = None
        completeness_summary: dict[str, Any] | None = None
        watchlist: list[dict[str, Any]] = []
        protocol_items: list[dict[str, Any]] = []
        alerts: list[dict[str, Any]] = []
        next_actions: list[str] = []

        try:
            from .growth_intelligence import GrowthIntelligenceOrchestrator, GrowthStore

            thor_snapshot = GrowthIntelligenceOrchestrator(GrowthStore()).thor.get_health_snapshot(actor)
            thor_note = str(thor_snapshot.get("thor_note") or thor_note)
        except Exception:
            pass

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
            readiness_factors = [
                {
                    "metric": str(factor.get("metric") or ""),
                    "label": str(factor.get("label") or factor.get("metric") or "Metric"),
                    "value": factor.get("value"),
                    "score": int(factor.get("score")) if isinstance(factor.get("score"), (int, float)) else None,
                    "missing": bool(factor.get("missing")),
                }
                for factor in (readiness_detail.get("factors") or [])
                if isinstance(factor, dict)
            ]

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
            completeness_summary = {
                "total_score": int(round(float(total_score))) if isinstance(total_score, (int, float)) else 0,
                "grade": str(grade or ""),
                "critical_gaps": [str(gap) for gap in (completeness.get("critical_gaps") or [])[:4] if gap],
                "quick_wins": [str(item) for item in (completeness.get("quick_wins") or [])[:4] if item],
            }
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
                if key_finding:
                    watchlist.append({
                        "kind": "condition",
                        "title": str(condition.get("name") or "Condition"),
                        "detail": key_finding,
                        "severity": "high" if isinstance(risk_score, (int, float)) and float(risk_score) >= 85 else "medium",
                    })
            meds = ((health_state.get("current_care_state") or {}).get("medications") or [])[:8]
            for med in meds:
                if not isinstance(med, dict):
                    continue
                if med.get("high_risk"):
                    monitoring = str(med.get("monitoring") or "").strip()
                    if monitoring:
                        protocol_items.append({
                            "title": f"Monitor {med.get('name') or 'medication'}",
                            "detail": monitoring,
                            "emphasis": "medium",
                        })
                notes = str(med.get("notes") or "").strip()
                if notes:
                    watchlist.append({
                        "kind": "medication",
                        "title": str(med.get("name") or "Medication"),
                        "detail": notes,
                        "severity": "medium" if med.get("high_risk") else "low",
                    })

        protocol_items = protocol_items[:4]
        next_actions = next_actions[:4]
        alerts = alerts[:4]
        watchlist = watchlist[:6]
        readiness_factors = readiness_factors[:4]

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
            "readiness_factors": readiness_factors,
            "thor_snapshot": thor_snapshot,
            "completeness": completeness_summary,
            "watchlist": watchlist,
            "protocol_items": protocol_items,
            "alerts": alerts,
            "next_actions": next_actions,
            "continuity": _build_health_continuity(
                actor,
                readiness=readiness,
                readiness_factors=readiness_factors,
                watchlist=watchlist,
                next_actions=next_actions,
            ),
            "manual_checkin_count": len(HealthCheckInStore().list_checkins(actor, limit=12)),
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

    @app.get("/api/apple/health/checkins")
    async def apple_health_checkins(actor: str = "chris"):
        store = HealthCheckInStore()
        entries = store.list_checkins(actor, limit=8)
        review_summary = store.review_summary(actor, limit=8)
        return _ok(
            {
                "entries": entries,
                "count": len(entries),
                "review_lane": list(review_summary.get("items") or []),
                "review_count": int(review_summary.get("count") or 0),
                "review_status_counts": dict(review_summary.get("counts") or {}),
            }
        )

    @app.post("/api/apple/health/checkins")
    async def apple_health_checkins_post(payload: dict):
        actor = str(payload.get("actor") or "chris").strip() or "chris"
        actor_id = str(payload.get("actor_id") or actor).strip().lower() or "chris"
        entry = HealthCheckInStore().save_checkin(
            actor_id=actor_id,
            symptoms=str(payload.get("symptoms") or "").strip(),
            note=str(payload.get("note") or "").strip(),
            energy_level=payload.get("energy_level"),
            sleep_hours=payload.get("sleep_hours"),
            stress_level=payload.get("stress_level"),
            source=str(payload.get("source") or "apple-health").strip() or "apple-health",
        )
        _record_operator_action(
            actor=actor,
            domain="health",
            action="Save Apple Health Check-In",
            detail=str(entry.get("note") or "Health manual check-in saved from the iPhone.").strip() or "Health manual check-in saved from the iPhone.",
            why_now="The iPhone health surface captured a manual check-in directly into the shared health continuity lane.",
            result_summary="Manual health check-in saved from Apple surface.",
            route="/health-center",
            route_label="Open Health",
            related_kind="health-checkin",
            related_label=str(entry.get("checkin_id") or "").strip(),
            succeeded=True,
        )
        focus = ProgressFocusStore(_ACTIVITY_AUDIT_ROOT).save_focus(
            module="Health",
            reason=str(entry.get("note") or "Manual health check-in updated the shared health lane.").strip(),
            route="/health-center",
            actor=actor,
        )
        return _ok({"status": "recorded", "checkin": entry, "focus": focus})

    @app.post("/api/apple/health/checkins/{checkin_id}/review")
    async def apple_health_checkins_review(checkin_id: str, payload: dict):
        actor = str(payload.get("actor") or "chris").strip() or "chris"
        review_note = str(payload.get("note") or "").strip()
        try:
            entry = HealthCheckInStore().review_checkin(
                checkin_id=checkin_id,
                status=str(payload.get("status") or "").strip(),
                note=review_note,
            )
        except KeyError:
            raise HTTPException(status_code=404, detail="Health check-in not found.")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        _record_operator_action(
            actor=actor,
            domain="health",
            action="Review Apple Health Check-In",
            detail=f"Apple Health marked {str(entry.get('symptoms') or 'health check-in').strip() or 'health check-in'} as {str(entry.get('review_status_label') or 'reviewed').lower()}.",
            why_now=review_note or "The iPhone health surface reviewed a manual check-in and promoted it into longitudinal continuity.",
            result_summary=f"Apple health review set {str(entry.get('review_status_label') or 'reviewed').lower()}.",
            route="/health-center",
            route_label="Open Health",
            related_kind="health-checkin-review",
            related_label=str(entry.get("checkin_id") or "").strip(),
            succeeded=True,
        )
        focus = ProgressFocusStore(_ACTIVITY_AUDIT_ROOT).save_focus(
            module="Health",
            reason=review_note or f"Apple health review moved a check-in to {str(entry.get('review_status_label') or 'reviewed').lower()}.",
            route="/health-center",
            actor=actor,
        )
        return _ok({"status": "recorded", "checkin": entry, "focus": focus})

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
            while_you_were_away = _build_while_you_were_away("chris")
            home_aggregate = runtime.chamber_home_aggregate(
                "chris",
                home_state=state,
                home_context=home_context,
                watch_status=status if isinstance(status, dict) else {},
                while_you_were_away=while_you_were_away,
            )
            state["home_context"] = home_context
            state["home_ops"] = _build_home_ops_summary()
            state["continuity"] = _build_home_continuity("chris")
            state["while_you_were_away"] = while_you_were_away
            state["action_items"] = list(home_aggregate.get("action_items") or []) or _build_home_action_items(
                state=state,
                home_context=home_context,
                needs_count=needs_count,
            )
            state["home_aggregate"] = home_aggregate
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
        boundary = runtime.assess_action_boundary(
            zone_id="household_home",
            arena_id="household.home.manual",
            action_type="home_control",
            requested_stage="sandbox_live",
        )
        boundary_decision = str(boundary.get("decision") or "stage")
        boundary_reason = str(boundary.get("reason") or "")
        trust_zone = str(boundary.get("trust_zone") or "household_home")
        authority_stage = str(boundary.get("authority_stage") or "draft")
        approval_mode = str(boundary.get("approval_mode") or "stage_and_alert")
        arena_status = str(boundary.get("arena_status") or "active")

        if boundary_decision == "deny":
            event = _record_shared_event(
                domain="home",
                kind="blocked",
                title=command,
                detail=f"Home command blocked by boundary: {boundary_reason}",
                severity="high",
                actor="chris",
                source="apple.home_command",
                source_id=request_id,
                navigation_target="systems",
                actions=["open"],
                trust_zone=trust_zone,
                authority_stage=authority_stage,
                why_now="A home command hit a trust boundary and was denied before execution.",
                metadata={
                    "command": command,
                    "entity_id": entity_id,
                    "service": service,
                    "boundary_decision": boundary_decision,
                    "arena_status": arena_status,
                },
            )
            _create_notification_from_event(
                event,
                category="household",
                delivery_mode="badge_only",
                available_actions=["open", "resolve"],
                source_summary="Blocked home command",
            )
            return _ok(
                {
                    "request_id": request_id,
                    "status": "blocked_by_boundary",
                    "boundary_decision": boundary_decision,
                    "boundary_reason": boundary_reason,
                    "trust_zone": trust_zone,
                    "authority_stage": authority_stage,
                    "arena_status": arena_status,
                    "approval_mode": approval_mode,
                }
            )

        if boundary_decision == "allow":
            executed = False
            try:
                from .data_connectors import get_ha
                ha = get_ha()
                if ha is not None and service and entity_id:
                    executed = bool(ha.call_service(service, command, entity_id))
            except Exception as exc:
                logger.warning("apple_home_command: live execution failed: %s", exc)
                executed = False

            if executed:
                event = _record_shared_event(
                    domain="home",
                    kind="executed",
                    title=command,
                    detail=f"Home command executed live: {service or 'service'} on {entity_id or 'target'}.",
                    severity="medium",
                    actor="chris",
                    source="apple.home_command",
                    source_id=request_id,
                    navigation_target="home",
                    actions=["open", "resolve"],
                    trust_zone=trust_zone,
                    authority_stage=authority_stage,
                    why_now="A home command was cleared by the trust boundary and executed live.",
                    metadata={"command": command, "entity_id": entity_id, "service": service},
                )
                _create_notification_from_event(
                    event,
                    category="household",
                    delivery_mode="badge_only",
                    available_actions=["open", "resolve"],
                    source_summary="Executed home command",
                )
                return _ok(
                    {
                        "request_id": request_id,
                        "status": "executed_live",
                        "boundary_decision": boundary_decision,
                        "boundary_reason": boundary_reason,
                        "trust_zone": trust_zone,
                        "authority_stage": authority_stage,
                        "arena_status": arena_status,
                        "approval_mode": approval_mode,
                    }
                )

        try:
            from .approvals import get_approval_guard
            guard = get_approval_guard()
            if guard is not None:
                request_id = guard.request_approval(
                    agent_id="apple-home",
                    agent_label="Apple Home",
                    title=command,
                    description=f"Home command: {service} on {entity_id}",
                    action_type="home_control",
                    payload={"command": command, "entity_id": entity_id, "service": service},
                    context={
                        "trust_zone_id": trust_zone,
                        "requested_outcome": f"Execute home command '{command}' via {service} on {entity_id}",
                        "touches_external_state": True,
                        "reversible": False,
                        "approval_mode": approval_mode,
                    },
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
            trust_zone=trust_zone,
            authority_stage=authority_stage,
            why_now="A home command was requested from the Apple client and now awaits approval.",
            metadata={
                "command": command,
                "entity_id": entity_id,
                "service": service,
                "boundary_decision": boundary_decision,
                "approval_mode": approval_mode,
            },
        )
        _create_notification_from_event(
            event,
            category="household",
            delivery_mode="badge_only",
            available_actions=["open", "dismiss", "resolve"],
            source_summary="Staged home command",
        )

        return _ok(
            {
                "request_id": request_id,
                "status": "pending_approval",
                "boundary_decision": boundary_decision,
                "boundary_reason": boundary_reason,
                "trust_zone": trust_zone,
                "authority_stage": authority_stage,
                "arena_status": arena_status,
                "approval_mode": approval_mode,
            }
        )

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

    @app.get("/api/apple/control-plane/state")
    async def apple_control_plane_state():
        data_root = Path("data/apple")
        now_playing_payload = _safe_read_json(data_root / "now_playing.json", {})
        return _ok(_build_apple_control_plane_state(
            now_playing_payload=now_playing_payload if isinstance(now_playing_payload, dict) else {},
        ))

    @app.get("/api/apple/systems/admin-summary")
    @app.post("/api/apple/systems/admin-summary")
    async def apple_systems_admin_summary():
        from .llm_gateway import usage_summary

        voice_store = VoiceSettingsStore(runtime.config)
        voice_settings = voice_store.describe()
        stack_status = voice_settings.get("stack_status") if isinstance(voice_settings, dict) else {}
        if not isinstance(stack_status, dict):
            stack_status = {}

        identity = runtime.identity_overview() or {}
        account_snapshot = runtime.account_registry_snapshot() or {}
        devices_snapshot = runtime.connected_devices_snapshot() or {}
        service_status = runtime.runtime_service_status() or {}
        google_summary = runtime.google_workspace_summary() or {}
        microsoft_summary = runtime.microsoft_graph_summary() or {}

        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        window_hours = max(1, int((now - month_start).total_seconds() // 3600) + 1)
        llm_costs = usage_summary(hours=window_hours)

        accounts = account_snapshot.get("accounts") if isinstance(account_snapshot, dict) else []
        if not isinstance(accounts, list):
            accounts = []
        account_items: list[dict[str, Any]] = []
        connected_accounts = 0
        planned_accounts = 0
        for item in accounts:
            if not isinstance(item, dict):
                continue
            status = str(item.get("status") or item.get("auth_status") or "planned").strip().lower()
            if status in {"connected", "ready", "active"}:
                connected_accounts += 1
            else:
                planned_accounts += 1
            account_items.append(
                {
                    "id": str(item.get("account_id") or item.get("id") or ""),
                    "label": str(item.get("label") or item.get("owner_display_name") or item.get("account_id") or "Account"),
                    "provider": str(item.get("provider") or "unknown"),
                    "status": status or "planned",
                    "login_hint": str(item.get("login_hint") or ""),
                    "service_scope": str(item.get("service_scope") or "mail_calendar"),
                    "notes": str(item.get("notes") or ""),
                    "connection_status": str(item.get("connection") or status or "planned"),
                    "detail": str(item.get("notes") or item.get("service_scope") or item.get("login_hint") or "Awaiting configuration"),
                }
            )

        raw_members = identity.get("members") if isinstance(identity, dict) else []
        if not isinstance(raw_members, list):
            raw_members = []
        raw_devices = devices_snapshot.get("devices") if isinstance(devices_snapshot, dict) else []
        if not isinstance(raw_devices, list):
            raw_devices = []
        member_rows: list[dict[str, Any]] = []
        online_members = 0
        for member in raw_members:
            if not isinstance(member, dict):
                continue
            member_id = str(member.get("user_id") or member.get("id") or "").strip().lower()
            member_devices = [
                device for device in raw_devices
                if isinstance(device, dict) and str(device.get("owner_user_id") or "").strip().lower() == member_id
            ]
            online_device_count = sum(1 for device in member_devices if _boolish(device.get("online")))
            if online_device_count:
                online_members += 1
            member_rows.append(
                {
                    "id": member_id or str(member.get("display_name") or "member").lower(),
                    "display_name": str(member.get("display_name") or member.get("name") or member_id or "Member"),
                    "role": str(member.get("role") or ""),
                    "permissions": str(member.get("permissions") or ""),
                    "trust_level": str(member.get("trust_level") or "standard"),
                    "preferred_tone": str(member.get("preferred_tone") or ""),
                    "privacy_boundary": str(member.get("privacy_boundary") or "personal"),
                    "notes": str(member.get("notes") or ""),
                    "device_count": len(member_devices),
                    "online_device_count": online_device_count,
                    "status": "Online" if online_device_count else ("Offline" if member_devices else "No Device"),
                }
            )

        device_rows: list[dict[str, Any]] = []
        for device in raw_devices:
            if not isinstance(device, dict):
                continue
            device_rows.append(
                {
                    "id": str(device.get("device_id") or device.get("id") or ""),
                    "label": str(device.get("label") or device.get("device_name") or device.get("device_id") or "Device"),
                    "owner_name": str(device.get("owner_display_name") or device.get("owner_user_id") or "Unclaimed"),
                    "last_seen_at": str(device.get("last_seen_at") or ""),
                    "mapped": bool(device.get("mapped")),
                    "shared": bool(device.get("shared")),
                    "status": "Online" if _boolish(device.get("online")) else ("Mapped" if device.get("mapped") else "Unclaimed"),
                }
            )

        selected_voice_label = str(
            voice_settings.get("selected_elevenlabs_label")
            or voice_settings.get("selected_piper_label")
            or voice_settings.get("tts_provider")
            or "Default"
        )
        local_ready = any(
            _boolish(stack_status.get(key))
            for key in ("ollama_available", "piper_ready", "system_voice_available", "localai_available")
        )
        cloud_ready = any(
            _boolish(stack_status.get(key))
            for key in ("elevenlabs_ready", "openai_ready")
        )

        google_accounts = google_summary.get("accounts") if isinstance(google_summary, dict) else []
        if not isinstance(google_accounts, list):
            google_accounts = []
        microsoft_accounts = microsoft_summary.get("accounts") if isinstance(microsoft_summary, dict) else []
        if not isinstance(microsoft_accounts, list):
            microsoft_accounts = []

        def _connected_count(items: list[Any]) -> int:
            total = 0
            for item in items:
                if not isinstance(item, dict):
                    continue
                status = item.get("status")
                if isinstance(status, dict):
                    if _boolish(status.get("connected")) or str(status.get("state") or "").lower() == "connected":
                        total += 1
                elif str(status or "").lower() == "connected":
                    total += 1
            return total

        by_model = llm_costs.get("by_model") if isinstance(llm_costs, dict) else {}
        if not isinstance(by_model, dict):
            by_model = {}
        model_rows = []
        for model_name, info in sorted(by_model.items(), key=lambda item: float(item[1].get("cost_usd", 0.0)), reverse=True)[:3]:
            if not isinstance(info, dict):
                continue
            model_rows.append(
                {
                    "id": str(model_name),
                    "name": str(model_name),
                    "backend": str(info.get("backend") or ""),
                    "calls": int(info.get("calls") or 0),
                    "cost_usd": round(float(info.get("cost_usd") or 0.0), 4),
                }
            )

        trust_zones = runtime.list_trust_zones() or []
        if not isinstance(trust_zones, list):
            trust_zones = []
        resource_arenas = runtime.list_resource_arenas() or []
        if not isinstance(resource_arenas, list):
            resource_arenas = []
        authority_stages = runtime.list_authority_stages() or []
        if not isinstance(authority_stages, list):
            authority_stages = []
        stage_queue = runtime.list_stage_queue(limit=8) or []
        if not isinstance(stage_queue, list):
            stage_queue = []
        promotion_records = runtime.list_promotion_records(limit=8) or []
        if not isinstance(promotion_records, list):
            promotion_records = []
        promotion_recommendations = runtime.list_promotion_recommendations(limit=6) or []
        if not isinstance(promotion_recommendations, list):
            promotion_recommendations = []

        governance_zones = []
        active_zone_count = 0
        for zone in trust_zones[:4]:
            if not isinstance(zone, dict):
                continue
            status = str(zone.get("status") or "unknown")
            if status.strip().lower() == "active":
                active_zone_count += 1
            allowed_actions = zone.get("allowed_actions") if isinstance(zone.get("allowed_actions"), list) else []
            governance_zones.append(
                {
                    "id": str(zone.get("zone_id") or ""),
                    "name": str(zone.get("name") or zone.get("zone_id") or "Zone"),
                    "zone_type": str(zone.get("zone_type") or ""),
                    "authority_stage": str(zone.get("authority_stage") or "observe"),
                    "approval_mode": str(zone.get("approval_mode") or ""),
                    "status": status,
                    "action_count": len([item for item in allowed_actions if str(item).strip()]),
                }
            )

        governance_arenas = []
        active_arena_count = 0
        for arena in resource_arenas[:4]:
            if not isinstance(arena, dict):
                continue
            status = str(arena.get("status") or "unknown")
            if status.strip().lower() == "active":
                active_arena_count += 1
            governance_arenas.append(
                {
                    "id": str(arena.get("arena_id") or ""),
                    "name": str(arena.get("name") or arena.get("arena_id") or "Arena"),
                    "resource_type": str(arena.get("resource_type") or ""),
                    "linked_zone_id": str(arena.get("linked_zone_id") or ""),
                    "risk_class": str(arena.get("risk_class") or ""),
                    "status": status,
                }
            )

        governance_stages = []
        for stage in sorted(
            [item for item in authority_stages if isinstance(item, dict)],
            key=lambda item: int(item.get("sequence") or 0),
        )[:5]:
            requirements = stage.get("approval_requirements") if isinstance(stage.get("approval_requirements"), dict) else {}
            actions = stage.get("allowed_action_types") if isinstance(stage.get("allowed_action_types"), list) else []
            governance_stages.append(
                {
                    "id": str(stage.get("stage_id") or ""),
                    "name": str(stage.get("name") or stage.get("stage_id") or "Stage"),
                    "sequence": int(stage.get("sequence") or 0),
                    "status": str(stage.get("status") or ""),
                    "action_type_count": len([item for item in actions if str(item).strip()]),
                    "boundary_mode": str(requirements.get("boundary_crossing") or requirements.get("pre_action") or ""),
                }
            )

        queue_rows = []
        pending_queue_count = 0
        for item in stage_queue:
            if not isinstance(item, dict):
                continue
            status = str(item.get("status") or "queued")
            if status.strip().lower() in {"queued", "pending", "staged", "ready_for_review"}:
                pending_queue_count += 1
            queue_rows.append(
                {
                    "id": str(item.get("request_id") or item.get("draft_id") or ""),
                    "arena_id": str(item.get("arena_id") or ""),
                    "action_type": str(item.get("action_type") or ""),
                    "status": status,
                    "created_at": str(item.get("created_at") or ""),
                    "principal_id": str(item.get("principal_id") or ""),
                    "draft_id": str(item.get("draft_id") or ""),
                }
            )

        promotion_rows = []
        promotion_record_count = 0
        for item in promotion_records:
            if not isinstance(item, dict):
                continue
            promotion_record_count += 1
            promotion_rows.append(
                {
                    "id": str(item.get("record_id") or item.get("id") or ""),
                    "event_type": str(item.get("event_type") or ""),
                    "subject_kind": str(item.get("subject_kind") or ""),
                    "subject_id": str(item.get("subject_id") or ""),
                    "status": str(item.get("status") or ""),
                    "actor": str(item.get("actor") or ""),
                    "basis": str(item.get("basis") or ""),
                    "trust_zone": str(item.get("trust_zone") or ""),
                    "arena_id": str(item.get("arena_id") or ""),
                    "authority_stage": str(item.get("authority_stage") or ""),
                    "created_at": str(item.get("created_at") or ""),
                }
            )

        promotion_recommendation_rows = []
        pending_consent_count = 0
        ready_to_promote_count = 0
        hold_count = 0
        for item in promotion_recommendations:
            if not isinstance(item, dict):
                continue
            decision = str(item.get("decision") or "")
            if decision == "pending_consent":
                pending_consent_count += 1
            elif decision == "promote":
                ready_to_promote_count += 1
            elif decision == "hold":
                hold_count += 1
            promotion_recommendation_rows.append(
                {
                    "id": str(item.get("id") or ""),
                    "title": str(item.get("title") or item.get("subject_id") or "Promotion recommendation"),
                    "subject_kind": str(item.get("subject_kind") or ""),
                    "subject_id": str(item.get("subject_id") or ""),
                    "decision": decision,
                    "current_stage": str(item.get("current_stage") or ""),
                    "target_stage": str(item.get("target_stage") or ""),
                    "summary": str(item.get("summary") or ""),
                    "reason": str(item.get("reason") or ""),
                    "trust_zone": str(item.get("trust_zone") or ""),
                    "arena_id": str(item.get("arena_id") or ""),
                    "human_consent_required": bool(item.get("human_consent_required", False)),
                }
            )

        stewardship_review_history = _stewardship_reviews.list(include_closed=True, limit=0)
        for index, item in enumerate(stewardship_review_history):
            if not isinstance(item, dict):
                continue
            status = str(item.get("status") or "").strip().lower()
            if status not in {"approved", "retired", "rerouted"}:
                continue
            promotion_record_count += 1
            promotion_rows.append(
                {
                    "id": str(item.get("id") or f"stewardship-history-{index}"),
                    "event_type": {
                        "approved": "stewardship_review_approved",
                        "retired": "stewardship_review_retired",
                    }.get(status, "stewardship_review_rerouted"),
                    "subject_kind": "stewardship_review",
                    "subject_id": str(item.get("lane_id") or ""),
                    "status": status,
                    "actor": str(item.get("last_actor") or "system"),
                    "basis": str(item.get("boundary_reason") or item.get("note") or item.get("lane_title") or ""),
                    "trust_zone": str(item.get("trust_zone") or ""),
                    "arena_id": str(item.get("packet_target") or ""),
                    "authority_stage": str(item.get("authority_stage") or ""),
                    "created_at": str(item.get("updated_at") or item.get("created_at") or ""),
                }
            )

        approvals = runtime.approval_history() or []
        if not isinstance(approvals, list):
            approvals = []
        pending_approvals = []
        pending_approval_count = 0
        rejected_approval_count = 0
        for index, item in enumerate(approvals):
            if not isinstance(item, dict):
                continue
            status = str(item.get("status") or "").strip().lower()
            if status == "pending":
                pending_approval_count += 1
                if len(pending_approvals) < 4:
                    pending_approvals.append(
                        {
                            "id": str(item.get("request_id") or item.get("id") or f"approval-{index}"),
                            "actor": str(item.get("actor") or ""),
                            "request": str(item.get("request") or ""),
                            "status": str(item.get("status") or "pending"),
                            "rationale": str(item.get("rationale") or ""),
                            "timestamp": str(item.get("timestamp") or item.get("created_at") or ""),
                        }
                    )
            elif status in {"rejected", "denied"}:
                rejected_approval_count += 1

        explainability = runtime.explainability_snapshot("Chris") or {}
        if not isinstance(explainability, dict):
            explainability = {}
        action_summary = explainability.get("assistant_action_summary") if isinstance(explainability.get("assistant_action_summary"), dict) else {}
        assistant_actions = explainability.get("assistant_actions") if isinstance(explainability.get("assistant_actions"), list) else []
        recent_actions = []
        for index, item in enumerate(assistant_actions[:4]):
            if not isinstance(item, dict):
                continue
            recent_actions.append(
                {
                    "id": str(item.get("item_id") or f"action-{index}"),
                    "domain": str(item.get("domain") or ""),
                    "action": str(item.get("action") or ""),
                    "decision": str(item.get("decision") or ""),
                    "mode": str(item.get("mode") or ""),
                    "succeeded": bool(item.get("succeeded")),
                    "caused_friction": bool(item.get("caused_friction")),
                    "why_now": str(item.get("why_now") or ""),
                    "timestamp": str(item.get("timestamp") or ""),
                }
            )

        stewardship_reviews = _stewardship_reviews.list(limit=0)
        recent_stewardship_reviews = [_serialize_stewardship_review(item) for item in stewardship_reviews[:4]]
        staged_stewardship_review_count = len(stewardship_reviews)

        doctrine_state = runtime.shared_doctrine_snapshot(actor_name="Chris", refresh=False) or {}
        if not isinstance(doctrine_state, dict):
            doctrine_state = {}
        if not str(doctrine_state.get("generated_at") or "").strip():
            doctrine_state = runtime.synthesize_shared_doctrine(auto_promote=False, promoted_by="system") or {}
            if not isinstance(doctrine_state, dict):
                doctrine_state = {}
            doctrine_state = runtime.shared_doctrine_snapshot(actor_name="Chris", refresh=False) or {}
            if not isinstance(doctrine_state, dict):
                doctrine_state = {}
        if not promotion_rows:
            doctrine_history = doctrine_state.get("history") if isinstance(doctrine_state.get("history"), list) else []
            for index, item in enumerate(reversed(doctrine_history[-4:])):
                if not isinstance(item, dict):
                    continue
                promotion_rows.append(
                    {
                        "id": str(item.get("id") or item.get("candidate_id") or f"history-{index}"),
                        "event_type": str(item.get("event") or "history"),
                        "subject_kind": "doctrine_candidate" if str(item.get("candidate_id") or "").strip() else "doctrine_rule",
                        "subject_id": str(item.get("candidate_id") or item.get("rule_id") or ""),
                        "status": str(item.get("status") or ""),
                        "actor": str(item.get("actor") or item.get("promoted_by") or item.get("dismissed_by") or "system"),
                        "basis": str(item.get("basis") or item.get("reason") or item.get("event") or ""),
                        "trust_zone": "shared-doctrine",
                        "arena_id": "",
                        "authority_stage": "policy",
                        "created_at": str(item.get("timestamp") or item.get("created_at") or ""),
                    }
                )
            promotion_record_count = len(promotion_rows)
        doctrine_candidates = doctrine_state.get("candidates") if isinstance(doctrine_state.get("candidates"), list) else []
        doctrine_summary = doctrine_state.get("summary") if isinstance(doctrine_state.get("summary"), dict) else {}
        candidate_rows = []
        for index, item in enumerate(doctrine_candidates[:4]):
            if not isinstance(item, dict):
                continue
            candidate_rows.append(
                {
                    "id": str(item.get("candidate_id") or f"candidate-{index}"),
                    "title": str(item.get("title") or ""),
                    "kind": str(item.get("kind") or ""),
                    "status": str(item.get("status") or ""),
                    "summary": str(item.get("summary") or ""),
                    "promotion_reason": str(item.get("promotion_reason") or ""),
                }
            )

        sandbox_overview = runtime.sandbox_operations_overview() or {}
        if not isinstance(sandbox_overview, dict):
            sandbox_overview = {}
        sandbox_queue = sandbox_overview.get("queue") if isinstance(sandbox_overview.get("queue"), dict) else {}
        sandbox_job_rows = sandbox_overview.get("jobs") if isinstance(sandbox_overview.get("jobs"), list) else []
        sandbox_active_run_rows = sandbox_overview.get("active_runs") if isinstance(sandbox_overview.get("active_runs"), list) else []
        sandbox_recent_run_rows = sandbox_overview.get("recent_runs") if isinstance(sandbox_overview.get("recent_runs"), list) else []
        sandbox_lane_rows = sandbox_overview.get("lane_summaries") if isinstance(sandbox_overview.get("lane_summaries"), list) else []
        calendar_route_jobs = runtime.calendar_route_sandbox_jobs(limit=0)
        recent_calendar_routes = [_serialize_calendar_route_job(item) for item in calendar_route_jobs[:4] if isinstance(item, dict)]
        staged_calendar_route_count = len(calendar_route_jobs)

        reflective_snapshot = runtime.learning_review_snapshot("Chris") or {}
        if not isinstance(reflective_snapshot, dict):
            reflective_snapshot = {}
        reflective_memory_graph = runtime.durable_memory_graph_snapshot("Chris") or {}
        if not isinstance(reflective_memory_graph, dict):
            reflective_memory_graph = {}
        reflective_profile = reflective_snapshot.get("profile") if isinstance(reflective_snapshot.get("profile"), dict) else {}
        reflective_personalization = (
            reflective_snapshot.get("personalization")
            if isinstance(reflective_snapshot.get("personalization"), dict)
            else {}
        )
        reflective_facts = (
            reflective_snapshot.get("profile_facts")
            if isinstance(reflective_snapshot.get("profile_facts"), list)
            else []
        )
        reflective_proposals = (
            reflective_snapshot.get("pending_proposals")
            if isinstance(reflective_snapshot.get("pending_proposals"), list)
            else []
        )
        reflective_first_light = (
            reflective_snapshot.get("first_light_history")
            if isinstance(reflective_snapshot.get("first_light_history"), list)
            else []
        )
        reflective_profile_fact_rows = []
        for item in reflective_facts[:3]:
            if not isinstance(item, dict):
                continue
            reflective_profile_fact_rows.append(
                {
                    "id": str(item.get("fact_id") or item.get("id") or ""),
                    "title": str(item.get("title") or item.get("summary") or "Profile fact"),
                    "summary": str(item.get("summary") or ""),
                    "tags": [str(tag) for tag in (item.get("tags") or [])[:4]],
                    "updated_at": str(item.get("updated_at") or ""),
                }
            )

        reflective_proposal_rows = []
        for item in reflective_proposals[:3]:
            if not isinstance(item, dict):
                continue
            reflective_proposal_rows.append(
                {
                    "id": str(item.get("proposal_id") or item.get("id") or ""),
                    "title": str(item.get("title") or item.get("summary") or "Memory proposal"),
                    "summary": str(item.get("summary") or ""),
                    "status": str(item.get("status") or "pending"),
                    "memory_type": str(item.get("memory_type") or ""),
                    "confidence": str(item.get("confidence") or "confirmed"),
                }
            )

        recent_first_light_rows = []
        for index, item in enumerate(list(reversed(reflective_first_light))[:3]):
            if not isinstance(item, dict):
                continue
            first_20 = item.get("first_20_minutes") if isinstance(item.get("first_20_minutes"), list) else []
            summary = str(item.get("watch_line") or "").strip()
            if not summary and first_20:
                summary = "; ".join(str(step).strip() for step in first_20[:2] if str(step).strip())
            if not summary:
                summary = "First Light continuity packet recorded."
            recent_first_light_rows.append(
                {
                    "id": str(item.get("packet_id") or item.get("date") or item.get("local_time") or f"first-light-{index}"),
                    "label": str(item.get("date") or item.get("local_time") or "Recent First Light"),
                    "summary": summary,
                }
            )

        reflective_insights = (
            reflective_personalization.get("insights")
            if isinstance(reflective_personalization.get("insights"), list)
            else []
        )
        active_insight_count = len(
            [
                item for item in reflective_insights
                if isinstance(item, dict) and str(item.get("status") or "").strip().lower() == "active"
            ]
        )
        guidance_lines: list[str] = []
        for line in reflective_personalization.get("rhythms", []) if isinstance(reflective_personalization.get("rhythms"), list) else []:
            cleaned = str(line).strip()
            if cleaned:
                guidance_lines.append(cleaned)
        for line in reflective_personalization.get("learned_preferences", []) if isinstance(reflective_personalization.get("learned_preferences"), list) else []:
            cleaned = str(line).strip()
            if cleaned and cleaned not in guidance_lines:
                guidance_lines.append(cleaned)
        digital_twin = reflective_snapshot.get("persona_snapshot") if isinstance(reflective_snapshot.get("persona_snapshot"), dict) else {}
        digital_twin_block = digital_twin.get("digital_twin") if isinstance(digital_twin.get("digital_twin"), dict) else {}
        for line in digital_twin_block.get("likely_next_needs", []) if isinstance(digital_twin_block.get("likely_next_needs"), list) else []:
            cleaned = str(line).strip()
            if cleaned and cleaned not in guidance_lines:
                guidance_lines.append(cleaned)
        for line in reflective_memory_graph.get("guidance_lines", []) if isinstance(reflective_memory_graph.get("guidance_lines"), list) else []:
            cleaned = str(line).strip()
            if cleaned and cleaned not in guidance_lines:
                guidance_lines.append(cleaned)

        stewardship_decision_rows = []
        stewardship_decision_count = 0
        stewardship_decision_groups: dict[str, dict[str, Any]] = {}
        for index, item in enumerate(stewardship_review_history):
            if not isinstance(item, dict):
                continue
            status = str(item.get("status") or "").strip().lower()
            if status not in {"approved", "retired", "rerouted"}:
                continue
            stewardship_decision_count += 1
            lane_id = str(item.get("lane_id") or "").strip() or f"lane-{index}"
            lane_title = str(item.get("lane_title") or "Stewardship Lane")
            group = stewardship_decision_groups.setdefault(
                lane_id,
                {
                    "lane_id": lane_id,
                    "lane_title": lane_title,
                    "approved": 0,
                    "retired": 0,
                    "rerouted": 0,
                    "review_surfaces": set(),
                    "packet_targets": set(),
                    "latest_timestamp": "",
                },
            )
            group[status] = int(group.get(status) or 0) + 1
            review_surface = str(item.get("review_surface") or "").strip()
            if review_surface:
                cast(set[str], group["review_surfaces"]).add(review_surface)
            packet_target = str(item.get("packet_target") or "").strip()
            if packet_target:
                cast(set[str], group["packet_targets"]).add(packet_target)
            timestamp = str(item.get("updated_at") or item.get("created_at") or "").strip()
            if timestamp and timestamp > str(group.get("latest_timestamp") or ""):
                group["latest_timestamp"] = timestamp
            if len(stewardship_decision_rows) >= 3:
                continue
            review_surface = str(item.get("review_surface") or "")
            packet_target = str(item.get("packet_target") or "")
            summary = str(item.get("boundary_reason") or "").strip()
            if not summary:
                if status == "approved":
                    summary = f"{lane_title} was approved into the {packet_target or 'shared'} lane."
                elif status == "retired":
                    summary = f"{lane_title} was retired instead of widening into the live flow."
                else:
                    summary = f"{lane_title} was rerouted to {review_surface or 'another'} review surface."
            stewardship_decision_rows.append(
                {
                    "id": str(item.get("id") or f"stewardship-decision-{index}"),
                    "label": lane_title,
                    "summary": summary,
                }
            )
        governance_learning_rows = []
        governance_proposal_rows = []
        governance_learning_groups = sorted(
            stewardship_decision_groups.values(),
            key=lambda item: (
                int(item.get("approved") or 0) + int(item.get("retired") or 0) + int(item.get("rerouted") or 0),
                str(item.get("latest_timestamp") or ""),
            ),
            reverse=True,
        )
        for index, group in enumerate(governance_learning_groups[:3]):
            lane_title = str(group.get("lane_title") or "Stewardship Lane")
            approved = int(group.get("approved") or 0)
            retired = int(group.get("retired") or 0)
            rerouted = int(group.get("rerouted") or 0)
            total = approved + retired + rerouted
            review_surfaces = sorted(str(item) for item in cast(set[str], group.get("review_surfaces") or set()) if str(item).strip())
            packet_targets = sorted(str(item) for item in cast(set[str], group.get("packet_targets") or set()) if str(item).strip())
            if total <= 0:
                continue
            if (rerouted + retired) > approved:
                title = f"{lane_title} still prefers bounded review"
                summary = (
                    f"{lane_title} has been rerouted or retired {rerouted + retired} of {total} reviewed times, "
                    f"which suggests its rollout posture is still narrower than a live lane."
                )
                recommendation = (
                    f"Keep {lane_title} staged through "
                    f"{', '.join(surface.title() for surface in review_surfaces) or 'review surfaces'} "
                    f"until a cleaner approval pattern emerges."
                )
                confidence = "high" if total >= 3 else "emerging"
            elif approved >= 2:
                title = f"{lane_title} is forming a stable approval pattern"
                summary = (
                    f"{lane_title} has been approved {approved} of {total} reviewed times into "
                    f"{', '.join(packet_targets) or 'shared'} without repeated fallback."
                )
                recommendation = (
                    f"Shape the next governance proposal around promoting {lane_title} toward a lighter review posture "
                    f"for {', '.join(packet_targets) or 'the current target lane'}."
                )
                confidence = "high" if approved >= 3 else "medium"
            else:
                title = f"{lane_title} is still teaching the control plane"
                summary = (
                    f"{lane_title} shows a mixed review pattern across {total} decisions, so JARVIS should keep "
                    f"learning from how you route and retire this lane."
                )
                recommendation = (
                    f"Keep {lane_title} under review and watch whether "
                    f"{', '.join(packet_targets) or 'the target lane'} becomes consistently approvable."
                )
                confidence = "emerging"
            governance_learning_rows.append(
                {
                    "id": str(group.get("lane_id") or f"governance-learning-{index}"),
                    "title": title,
                    "summary": summary,
                    "recommendation": recommendation,
                    "confidence": confidence,
                }
            )
        governance_proposal_rows = _build_governance_proposal_rows(stewardship_review_history)
        if stewardship_decision_count:
            decision_line = f"{stewardship_decision_count} stewardship rollout decision" + ("s are" if stewardship_decision_count != 1 else " is") + " now part of the learning record."
            if decision_line not in guidance_lines:
                guidance_lines.append(decision_line)
        for item in governance_learning_rows[:2]:
            recommendation = str(item.get("recommendation") or "").strip()
            if recommendation and recommendation not in guidance_lines:
                guidance_lines.append(recommendation)

        return _ok(
            {
                "accounts": {
                    "total": len(account_items),
                    "connected": connected_accounts,
                    "planned": planned_accounts,
                    "items": account_items,
                },
                "family": {
                    "member_count": len(member_rows),
                    "online_count": online_members,
                    "members": member_rows,
                },
                "devices": {
                    "total": len(device_rows),
                    "mapped_count": int(devices_snapshot.get("mapped_count") or 0),
                    "shared_count": int(devices_snapshot.get("shared_count") or 0),
                    "items": device_rows[:6],
                },
                "voice": {
                    "provider": str(voice_settings.get("tts_provider") or "auto"),
                    "provider_label": str(voice_settings.get("selected_provider_label") or "Auto"),
                    "voice_label": selected_voice_label,
                    "local_ready": local_ready,
                    "cloud_ready": cloud_ready,
                    "detail": (
                        f"{selected_voice_label} · "
                        f"{'local ready' if local_ready else 'local idle'} · "
                        f"{'cloud ready' if cloud_ready else 'cloud idle'}"
                    ),
                },
                "service": {
                    "hostname": str(service_status.get("hostname") or "jarvis.local"),
                    "lan_url": str(service_status.get("lan_url") or ""),
                    "deployment_mode": str(service_status.get("deployment_mode") or "hybrid"),
                    "mode_label": str(service_status.get("mode_label") or ""),
                    "hosted_base_url": str(service_status.get("hosted_base_url") or ""),
                    "hosted_provider": str(service_status.get("hosted_provider") or "Hetzner"),
                    "edge_provider": str(service_status.get("edge_provider") or "Cloudflare Tunnel"),
                    "remote_admin_host": str(service_status.get("remote_admin_host") or ""),
                    "cloudflare_access_enabled": bool(service_status.get("cloudflare_access_enabled", True)),
                    "tunnel_enabled": bool(service_status.get("tunnel_enabled", True)),
                    "public_route_count": len(service_status.get("public_routes") or []),
                    "compose_service_count": len(service_status.get("compose_services") or []),
                    "runtime_loaded": bool(service_status.get("runtime", {}).get("loaded")),
                    "openviking_loaded": bool(service_status.get("openviking", {}).get("loaded")),
                    "assistant_loaded": bool(service_status.get("assistant_autonomy", {}).get("loaded")),
                },
                "integrations": {
                    "google_ready": bool(google_summary.get("client_secret", {}).get("present")),
                    "google_connected_count": _connected_count(google_accounts),
                    "google_client_secret_present": bool(google_summary.get("client_secret", {}).get("present")),
                    "microsoft_ready": bool(microsoft_summary.get("config", {}).get("client_id_present")),
                    "microsoft_connected_count": _connected_count(microsoft_accounts),
                },
                "costs": {
                    "window_hours": window_hours,
                    "month_total_usd": round(float(llm_costs.get("estimated_cost_usd") or 0.0), 4),
                    "total_calls": int(llm_costs.get("total_calls") or 0),
                    "paid_calls": int(llm_costs.get("paid_calls") or 0),
                    "prompt_tokens": int(llm_costs.get("prompt_tokens") or 0),
                    "completion_tokens": int(llm_costs.get("completion_tokens") or 0),
                    "models": model_rows,
                },
                "governance": {
                    "zone_count": len([item for item in trust_zones if isinstance(item, dict)]),
                    "active_zone_count": active_zone_count,
                    "arena_count": len([item for item in resource_arenas if isinstance(item, dict)]),
                    "active_arena_count": active_arena_count,
                    "stage_count": len([item for item in authority_stages if isinstance(item, dict)]),
                    "pending_queue_count": pending_queue_count,
                    "promotion_record_count": promotion_record_count,
                    "promotion_recommendation_count": len(promotion_recommendation_rows),
                    "pending_consent_count": pending_consent_count,
                    "ready_to_promote_count": ready_to_promote_count,
                    "hold_recommendation_count": hold_count,
                    "zones": governance_zones,
                    "arenas": governance_arenas,
                    "stages": governance_stages,
                    "queue": queue_rows[:5],
                    "promotion_records": promotion_rows[:5],
                    "promotion_recommendations": promotion_recommendation_rows[:5],
                },
                "sandbox_operations": {
                    "queue": {
                        "active_count": int(sandbox_queue.get("active_count") or 0),
                        "queued_job_count": int(sandbox_queue.get("queued_job_count") or 0),
                        "review_ready_count": int(sandbox_queue.get("review_ready_count") or 0),
                        "failed_run_count": int(sandbox_queue.get("failed_run_count") or 0),
                        "active_jobs": [
                            str(item) for item in sandbox_queue.get("active_jobs", [])
                            if str(item).strip()
                        ],
                        "lane_count": int(sandbox_queue.get("lane_count") or 0),
                    },
                    "jobs": sandbox_job_rows,
                    "active_runs": sandbox_active_run_rows,
                    "recent_runs": sandbox_recent_run_rows,
                    "lane_summaries": sandbox_lane_rows,
                },
                "reflective_memory": {
                    "subject_display_name": str(reflective_snapshot.get("subject_display_name") or "Chris"),
                    "profile_fact_count": len(reflective_facts),
                    "pending_proposal_count": len(reflective_proposals),
                    "first_light_history_count": len(reflective_first_light),
                    "insight_count": len(reflective_insights),
                    "active_insight_count": active_insight_count,
                    "stewardship_decision_count": stewardship_decision_count,
                    "governance_learning_count": len(governance_learning_rows),
                    "preferred_tone": str(reflective_profile.get("preferred_tone") or ""),
                    "briefing_style": str(reflective_profile.get("briefing_style") or ""),
                    "preferred_voice": str(reflective_profile.get("preferred_voice") or ""),
                    "guidance_lines": guidance_lines[:5],
                    "profile_facts": reflective_profile_fact_rows,
                    "pending_proposals": reflective_proposal_rows,
                    "recent_first_light": recent_first_light_rows,
                    "recent_stewardship_decisions": stewardship_decision_rows,
                    "governance_learning": governance_learning_rows,
                    "memory_graph": reflective_memory_graph,
                },
                "governed_workflows": {
                    "pending_approval_count": pending_approval_count,
                    "rejected_approval_count": rejected_approval_count,
                    "automatic_action_count": int(action_summary.get("automatic") or 0),
                    "friction_action_count": int(action_summary.get("friction") or 0),
                    "doctrine_candidate_count": int(doctrine_summary.get("candidate_count") or len(doctrine_candidates)),
                    "governance_proposal_count": len(governance_proposal_rows),
                    "active_rule_count": int(doctrine_summary.get("active_rule_count") or 0),
                    "staged_stewardship_review_count": staged_stewardship_review_count,
                    "staged_calendar_route_count": staged_calendar_route_count,
                    "pending_approvals": pending_approvals,
                    "recent_actions": recent_actions,
                    "recent_stewardship_reviews": recent_stewardship_reviews,
                    "recent_calendar_routes": recent_calendar_routes,
                    "governance_proposals": governance_proposal_rows,
                    "doctrine_candidates": candidate_rows,
                },
            }
        )

    @app.get("/api/apple/systems/profile-settings")
    async def apple_systems_profile_settings():
        from .user_profile import load_profile

        actor = runtime.get_actor("Chris")
        profile = load_profile(actor.user_id)
        return _ok(
            {
                "subject_user_id": actor.user_id,
                "notifications": dict(profile.get("notifications") or {}),
                "privacy": dict(profile.get("privacy") or {}),
                "dashboard": dict(profile.get("dashboard") or {}),
                "updated_at": str(profile.get("updated_at") or ""),
            }
        )

    @app.post("/api/apple/systems/profile-settings")
    async def apple_save_systems_profile_settings(payload: dict[str, Any]):
        actor_name = str(payload.get("actor") or payload.get("actor_id") or "chris").strip() or "chris"
        try:
            result = _save_apple_settings_profile(runtime, payload, actor_name=actor_name)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _ok(result)

    @app.post("/api/apple/systems/accounts/{account_id}")
    async def apple_save_systems_account(account_id: str, payload: dict[str, Any]):
        actor_name = str(payload.get("actor") or payload.get("actor_id") or "chris").strip() or "chris"
        try:
            result = _save_apple_settings_account(runtime, account_id, payload, actor_name=actor_name)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _ok(result)

    @app.post("/api/apple/systems/accounts/{account_id}/connector")
    async def apple_save_systems_connector(account_id: str, payload: dict[str, Any]):
        actor_name = str(payload.get("actor") or payload.get("actor_id") or "chris").strip() or "chris"
        try:
            result = _save_apple_settings_connector(runtime, account_id, payload, actor_name=actor_name)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _ok(result)

    @app.post("/api/apple/systems/accounts/{account_id}/disconnect")
    async def apple_disconnect_systems_account(account_id: str, payload: dict[str, Any] | None = None):
        payload = payload or {}
        actor_name = str(payload.get("actor") or payload.get("actor_id") or "chris").strip() or "chris"
        try:
            result = _disconnect_apple_settings_account(runtime, account_id, actor_name=actor_name)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _ok(result)

    @app.post("/api/apple/systems/family/{user_id}")
    async def apple_save_systems_family_member(user_id: str, payload: dict[str, Any]):
        actor_name = str(payload.get("actor") or payload.get("actor_id") or "chris").strip() or "chris"
        try:
            result = _save_apple_settings_family_member(runtime, user_id, payload, actor_name=actor_name)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _ok(result)

    @app.post("/api/apple/systems/self-improvement/jobs/{job_id}/sandbox-execute")
    async def apple_execute_sandbox_job(job_id: str, payload: dict = {}):
        actor = str(payload.get("actor") or "chris").strip() or "chris"
        triggered_by = str(payload.get("triggered_by") or "apple-systems").strip() or "apple-systems"
        try:
            result = runtime.execute_sandbox_job(actor, job_id, triggered_by=triggered_by)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        job = result.get("job") if isinstance(result.get("job"), dict) else {}
        active_run = result.get("active_run") if isinstance(result.get("active_run"), dict) else {}
        queue = result.get("queue") if isinstance(result.get("queue"), dict) else {}
        return _ok(
            {
                "ok": bool(result.get("ok")),
                "accepted": bool(result.get("accepted")),
                "job_id": str(job.get("job_id") or job_id),
                "status": str(job.get("status") or ""),
                "message": str(result.get("message") or ""),
                "active_run_id": str(active_run.get("run_id") or ""),
                "queue_active_count": int(queue.get("active_count") or 0),
            }
        )

    @app.post("/api/apple/systems/self-improvement/jobs/{job_id}/sandbox-cancel")
    async def apple_cancel_sandbox_job(job_id: str, payload: dict = {}):
        actor = str(payload.get("actor") or "chris").strip() or "chris"
        reason = str(payload.get("reason") or "manual stop from Apple Systems").strip() or "manual stop from Apple Systems"
        try:
            result = runtime.cancel_sandbox_job(actor, job_id, reason=reason)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        job = result.get("job") if isinstance(result.get("job"), dict) else {}
        active_run = result.get("active_run") if isinstance(result.get("active_run"), dict) else {}
        queue = result.get("queue") if isinstance(result.get("queue"), dict) else {}
        return _ok(
            {
                "ok": bool(result.get("ok")),
                "accepted": bool(result.get("accepted")),
                "mode": str(result.get("mode") or ""),
                "job_id": str(job.get("job_id") or job_id),
                "status": str(job.get("status") or ""),
                "message": str(result.get("message") or ""),
                "active_run_id": str(active_run.get("run_id") or ""),
                "queue_active_count": int(queue.get("active_count") or 0),
            }
        )

    @app.post("/api/apple/systems/self-improvement/jobs/{job_id}/sandbox-recover")
    async def apple_recover_sandbox_job(job_id: str, payload: dict = {}):
        actor = str(payload.get("actor") or "chris").strip() or "chris"
        reason = str(payload.get("reason") or "manual recovery reset from Apple Systems").strip() or "manual recovery reset from Apple Systems"
        try:
            result = runtime.recover_sandbox_job(actor, job_id, reason=reason)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        job = result.get("job") if isinstance(result.get("job"), dict) else {}
        queue = result.get("queue") if isinstance(result.get("queue"), dict) else {}
        return _ok(
            {
                "ok": bool(result.get("ok")),
                "accepted": bool(result.get("accepted")),
                "mode": str(result.get("mode") or ""),
                "job_id": str(job.get("job_id") or job_id),
                "status": str(job.get("status") or ""),
                "message": str(result.get("message") or ""),
                "active_run_id": "",
                "queue_active_count": int(queue.get("active_count") or 0),
            }
        )

    @app.post("/api/apple/systems/trust-zones/{zone_id}/promote")
    async def apple_promote_trust_zone(zone_id: str, payload: dict = {}):
        actor = str(payload.get("actor") or "chris").strip() or "chris"
        basis = str(payload.get("basis") or "manual promotion from Apple Systems").strip()
        try:
            updated = runtime.promote_trust_zone(zone_id, actor=actor, basis=basis)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return _ok(
            {
                "status": "promoted",
                "zone_id": str(updated.get("zone_id") or zone_id),
                "authority_stage": str(updated.get("authority_stage") or ""),
                "approval_mode": str(updated.get("approval_mode") or ""),
            }
        )

    @app.post("/api/apple/systems/trust-zones/{zone_id}/demote")
    async def apple_demote_trust_zone(zone_id: str, payload: dict = {}):
        actor = str(payload.get("actor") or "chris").strip() or "chris"
        reason = str(payload.get("reason") or "manual demotion from Apple Systems").strip()
        try:
            updated = runtime.demote_trust_zone(zone_id, actor=actor, reason=reason)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return _ok(
            {
                "status": "demoted",
                "zone_id": str(updated.get("zone_id") or zone_id),
                "authority_stage": str(updated.get("authority_stage") or ""),
                "approval_mode": str(updated.get("approval_mode") or ""),
            }
        )

    @app.post("/api/apple/systems/resource-arenas/{arena_id}/suspend")
    async def apple_suspend_resource_arena(arena_id: str, payload: dict = {}):
        actor = str(payload.get("actor") or "chris").strip() or "chris"
        reason = str(payload.get("reason") or "manual suspension from Apple Systems").strip()
        try:
            updated = runtime.suspend_resource_arena(arena_id, actor=actor, reason=reason)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return _ok(
            {
                "status": str(updated.get("status") or "suspended"),
                "arena_id": str(updated.get("arena_id") or arena_id),
                "linked_zone_id": str(updated.get("linked_zone_id") or ""),
            }
        )

    @app.post("/api/apple/systems/resource-arenas/{arena_id}/resume")
    async def apple_resume_resource_arena(arena_id: str, payload: dict = {}):
        actor = str(payload.get("actor") or "chris").strip() or "chris"
        reason = str(payload.get("reason") or "manual resume from Apple Systems").strip()
        try:
            updated = runtime.resume_resource_arena(arena_id, actor=actor, reason=reason)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return _ok(
            {
                "status": str(updated.get("status") or "active"),
                "arena_id": str(updated.get("arena_id") or arena_id),
                "linked_zone_id": str(updated.get("linked_zone_id") or ""),
            }
        )

    @app.post("/api/apple/systems/promotion/apply")
    async def apple_apply_promotion(payload: dict = {}):
        actor = str(payload.get("actor") or "chris").strip() or "chris"
        basis = str(payload.get("basis") or "promotion application from Apple Systems").strip()
        try:
            result = runtime.apply_promotion_decision(
                subject_kind=str(payload.get("subject_kind") or ""),
                subject_id=str(payload.get("subject_id") or ""),
                target_stage=str(payload.get("target_stage") or ""),
                actor=actor,
                basis=basis,
                human_consent=bool(payload.get("human_consent", False)),
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return _ok(result)

    @app.post("/api/apple/systems/promotion/apply-recommendations")
    async def apple_apply_promotion_recommendations(payload: dict = {}):
        actor = str(payload.get("actor") or "system-steward").strip() or "system-steward"
        basis = str(payload.get("basis") or "auto-apply-promotion-recommendations").strip()
        result = runtime.apply_promotion_recommendations(
            actor=actor,
            basis=basis,
            limit=int(payload.get("limit") or 12),
        )
        return _ok(result)

    def _build_apple_notification_center_overview(
        *,
        notifications: list[dict[str, Any]],
        all_notifications: list[dict[str, Any]],
        events: list[dict[str, Any]],
        posture: dict[str, Any],
    ) -> dict[str, Any]:
        status_counts = Counter(
            str(item.get("status") or "unknown")
            for item in all_notifications
            if isinstance(item, dict)
        )
        category_counts = Counter(
            str(item.get("category") or "unknown")
            for item in all_notifications
            if isinstance(item, dict)
        )
        domain_counts = Counter(
            str(item.get("domain") or "unknown")
            for item in events
            if isinstance(item, dict)
        )
        severity_counts = Counter(
            str(item.get("severity") or "unknown")
            for item in events
            if isinstance(item, dict)
        )
        last_notification_at = (
            str(all_notifications[0].get("updated_at") or all_notifications[0].get("created_at") or "")
            if all_notifications
            else ""
        )
        last_event_at = str(events[0].get("ts") or "") if events else ""
        recommended_delivery = str(posture.get("recommended_delivery") or "badge_only")
        routing_mode = str(posture.get("mode") or "active_hours")
        routing_lanes = [
            {
                "id": "household_alert_override",
                "title": "Household alert override",
                "detail": "Live household alerts can break through quieter delivery modes.",
                "active": routing_mode == "household_alert",
            },
            {
                "id": "focus_quiet_store",
                "title": "Focus routes non-urgent items quietly",
                "detail": "When Focus is active, lower-priority notifications stay quiet instead of interrupting.",
                "active": bool(posture.get("focus_active")) and recommended_delivery == "quiet_store",
            },
            {
                "id": "quiet_hours_hold_for_brief",
                "title": "Quiet hours hold lower-priority items for Brief",
                "detail": "Overnight and quiet-hour delivery should wait for the next command surface unless urgency rises.",
                "active": bool(posture.get("quiet_hours")) and recommended_delivery == "hold_for_brief",
            },
            {
                "id": "approvals_stay_visible",
                "title": "Approvals remain visible in quieter modes",
                "detail": "Needs and approvals stay visible even when JARVIS is suppressing noisier interruptions.",
                "active": recommended_delivery in {"badge_only", "quiet_store", "hold_for_brief"},
            },
        ]
        return {
            "notifications": notifications,
            "summary": {
                "total": len(all_notifications),
                "pending": status_counts.get("pending", 0),
                "seen": status_counts.get("seen", 0),
                "snoozed": status_counts.get("snoozed", 0),
                "resolved": status_counts.get("resolved", 0),
                "dismissed": status_counts.get("dismissed", 0),
                "categories": dict(category_counts),
                "last_updated_at": last_notification_at,
            },
            "routing": {
                "mode": routing_mode,
                "label": str(posture.get("label") or "Active hours"),
                "reason": str(posture.get("reason") or ""),
                "recommended_delivery": recommended_delivery,
                "focus_active": bool(posture.get("focus_active")),
                "quiet_hours": bool(posture.get("quiet_hours")),
                "hour_local": int(posture.get("hour_local") or 0),
                "needs_count": int(posture.get("needs_count") or 0),
                "alert_count": int(posture.get("alert_count") or 0),
                "present_members": [
                    str(member).strip()
                    for member in (posture.get("present_members") or [])
                    if str(member).strip()
                ],
                "updated_at": str(posture.get("updated_at") or ""),
                "lanes": routing_lanes,
            },
            "event_summary": {
                "recent_count": len(events),
                "domains": dict(domain_counts),
                "severities": dict(severity_counts),
                "last_event_at": last_event_at,
            },
        }

    # ------------------------------------------------------------------
    # GET /api/apple/notifications
    # ------------------------------------------------------------------
    @app.get("/api/apple/notifications")
    async def apple_notifications(status: str = "", category: str = "", limit: int = 50):
        data_root = Path("data/apple")
        watch_status = (await apple_status()).get("data") or {}
        home_state = (await apple_home_state()).get("data") or {}
        focus_payload = _safe_read_json(data_root / "focus_state.json", {})
        _reconcile_shared_notifications(
            watch_status=watch_status,
            home_state=home_state,
            calendar_payload=_safe_read_json(data_root / "calendar_events.json", {}),
            reminders_payload=_safe_read_json(data_root / "reminders.json", {}),
            focus_payload=focus_payload,
            latest_sound=((_safe_read_jsonl_tail(data_root / "sound_alerts.jsonl", limit=1) or [{}])[0]),
            latest_scan=((_safe_read_jsonl_tail(data_root / "vision_scans.jsonl", limit=1) or [{}])[0]),
        )
        posture = _compute_interruption_posture(
            watch_status=watch_status if isinstance(watch_status, dict) else {},
            home_state=home_state if isinstance(home_state, dict) else {},
            focus_payload=focus_payload if isinstance(focus_payload, dict) else {},
        )
        notifications = _notification_center.list(
            status=status or None,
            category=category or None,
            limit=max(1, min(limit, 200)),
        )
        all_notifications = _notification_center.list(limit=0)
        recent_events = _event_log.recent(limit=50)
        return _ok(
            _build_apple_notification_center_overview(
                notifications=notifications,
                all_notifications=all_notifications,
                events=recent_events,
                posture=posture,
            )
        )

    async def _notification_action(notification_id: str, status: str, reason: str) -> dict:
        item = _notification_center.update_status(notification_id, status, reason=reason)
        if item is None:
            raise HTTPException(status_code=404, detail="Notification not found")
        return _ok({"notification": item, "status": status})

    async def _governed_notification_mutation(notification_id: str, *, target_status: str, reason: str, action_label: str) -> dict:
        item = _notification_center.get(notification_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Notification not found")
        request_id = str(uuid.uuid4())
        boundary = runtime.assess_action_boundary(
            zone_id="household_attention",
            arena_id="household.attention.workflow",
            action_type="notification_workflow",
            requested_stage="sandbox_live",
        )
        boundary_decision = str(boundary.get("decision") or "stage")
        boundary_reason = str(boundary.get("reason") or "")
        trust_zone = str(boundary.get("trust_zone") or "household_attention")
        authority_stage = str(boundary.get("authority_stage") or "stage_alert")
        approval_mode = str(boundary.get("approval_mode") or "stage_and_alert")
        arena_status = str(boundary.get("arena_status") or "active")

        if boundary_decision == "deny":
            return _ok(
                {
                    "request_id": request_id,
                    "status": "blocked_by_boundary",
                    "notification": item,
                    "performed_action": action_label,
                    "boundary_decision": boundary_decision,
                    "boundary_reason": boundary_reason,
                    "trust_zone": trust_zone,
                    "authority_stage": authority_stage,
                    "arena_status": arena_status,
                    "approval_mode": approval_mode,
                }
            )

        if boundary_decision != "allow":
            from .models import StagedActionQueueItem
            runtime.trust_support.enqueue_stage_action(
                StagedActionQueueItem(
                    request_id=request_id,
                    arena_id="household.attention.workflow",
                    action_type=f"notification_{action_label}_review",
                    status="awaiting_principal_review",
                    created_at=_ts(),
                    principal_id="chris",
                )
            )
            staged_item = dict(item)
            staged_item["decision_reason"] = boundary_reason
            return _ok(
                {
                    "request_id": request_id,
                    "status": "staged_for_review",
                    "notification": staged_item,
                    "performed_action": action_label,
                    "boundary_decision": boundary_decision,
                    "boundary_reason": boundary_reason,
                    "trust_zone": trust_zone,
                    "authority_stage": authority_stage,
                    "arena_status": arena_status,
                    "approval_mode": approval_mode,
                }
            )

        updated = _notification_center.update_status(notification_id, target_status, reason=reason)
        if updated is None:
            raise HTTPException(status_code=404, detail="Notification not found")
        return _ok(
            {
                "request_id": request_id,
                "status": target_status,
                "notification": updated,
                "performed_action": action_label,
                "boundary_decision": boundary_decision,
                "boundary_reason": boundary_reason,
                "trust_zone": trust_zone,
                "authority_stage": authority_stage,
                "arena_status": arena_status,
                "approval_mode": approval_mode,
            }
        )

    @app.post("/api/apple/notifications/{notification_id}/seen")
    async def apple_notification_seen(notification_id: str):
        return await _notification_action(notification_id, "seen", "Marked seen from Apple client.")

    @app.post("/api/apple/notifications/{notification_id}/dismiss")
    async def apple_notification_dismiss(notification_id: str):
        return await _notification_action(notification_id, "dismissed", "Dismissed from Apple client.")

    @app.post("/api/apple/notifications/{notification_id}/resolve")
    async def apple_notification_resolve(notification_id: str):
        return await _governed_notification_mutation(
            notification_id,
            target_status="resolved",
            reason="Resolved from Apple client.",
            action_label="resolve",
        )

    @app.post("/api/apple/notifications/{notification_id}/snooze")
    async def apple_notification_snooze(notification_id: str):
        return await _governed_notification_mutation(
            notification_id,
            target_status="snoozed",
            reason="Snoozed from Apple client.",
            action_label="snooze",
        )

    @app.post("/api/apple/notifications/{notification_id}/action")
    async def apple_notification_workflow_action(notification_id: str, payload: dict):
        action = str(payload.get("action") or "").strip()
        if not action:
            raise HTTPException(status_code=400, detail="action required")
        return _ok(_perform_notification_action(notification_id, action))

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
        from .approvals import get_approval_guard, get_approval_queue
        queue = get_approval_queue()
        if queue is None:
            raise HTTPException(status_code=503, detail="Approval system not initialised")
        guard = get_approval_guard()
        if guard is None:
            raise HTTPException(status_code=503, detail="Approval guard not initialised")

        approved_by = str(payload.get("approved_by") or "chris")
        from dataclasses import asdict as _asdict
        item = queue.approve(request_id, approved_by=approved_by)
        if item is None:
            raise HTTPException(status_code=404, detail="Pending approval request not found")
        execution_result = guard.execute_approved(request_id)
        if str(execution_result.get("status") or "").strip().lower() == "error":
            raise HTTPException(status_code=400, detail=str(execution_result.get("detail") or "Governed approval execution failed"))

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

        return _ok(
            {
                "status": "approved",
                "request": item_dict,
                "execution_status": str(execution_result.get("status") or ""),
                "supervision_decision": dict(execution_result.get("supervision_decision", {}) or {}),
                "sandbox_job_id": str(execution_result.get("sandbox_job_id") or ""),
                "sandbox_result": dict(execution_result.get("sandbox_result", {}) or {}),
            }
        )

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

    @app.get("/api/apple/calendar/state")
    async def apple_calendar_state():
        payload = _safe_read_json(_APPLE_CALENDAR_PATH, {})
        return _ok(_build_apple_calendar_state(payload if isinstance(payload, dict) else {}))

    @app.post("/api/apple/calendar")
    async def apple_calendar(payload: dict):
        """Receives Calendar events from EventKit on the iPhone.
        Writes to data/apple/calendar_events.json for the runtime to consume."""
        events = payload.get("events", [])
        out_path = _APPLE_CALENDAR_PATH
        _safe_write_json(out_path, {
            "events": events,
            "count":  len(events),
            "source": "eventkit",
            "synced_at": _ts(),
        })
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

    @app.post("/api/apple/calendar/stage-prep")
    async def apple_calendar_stage_prep(payload: dict | None = None):
        body = payload or {}
        title = str(body.get("title") or "").strip()
        start = str(body.get("start") or "").strip()
        location = str(body.get("location") or "").strip()
        return _ok(_apple_stage_calendar_prep(title, start=start, location=location))

    @app.post("/api/apple/calendar/events/{event_id}/prepare")
    async def apple_calendar_event_prepare(event_id: str):
        payload = _safe_read_json(_APPLE_CALENDAR_PATH, {})
        event = _apple_find_calendar_event(payload if isinstance(payload, dict) else {}, event_id)
        if event is None:
            raise HTTPException(status_code=404, detail="Calendar event not found")
        return _ok(
            _apple_stage_calendar_prep(
                str(event.get("title") or ""),
                start=str(event.get("start") or ""),
                location=str(event.get("location") or ""),
            )
        )

    @app.post("/api/apple/calendar/events/{event_id}/route")
    async def apple_calendar_event_route(event_id: str):
        payload = _safe_read_json(_APPLE_CALENDAR_PATH, {})
        event = _apple_find_calendar_event(payload if isinstance(payload, dict) else {}, event_id)
        if event is None:
            raise HTTPException(status_code=404, detail="Calendar event not found")
        request_id = str(uuid.uuid4())
        title = str(event.get("title") or "").strip() or "Upcoming event"
        location = str(event.get("location") or "").strip()
        if not location:
            raise HTTPException(status_code=400, detail="Calendar event has no location")
        boundary = runtime.assess_action_boundary(
            zone_id="household_schedule",
            arena_id="household.schedule.routing",
            action_type="calendar_route",
            requested_stage="sandbox_live",
        )
        boundary_decision = str(boundary.get("decision") or "stage")
        boundary_reason = str(boundary.get("reason") or "")
        trust_zone = str(boundary.get("trust_zone") or "household_schedule")
        authority_stage = str(boundary.get("authority_stage") or "stage_alert")
        approval_mode = str(boundary.get("approval_mode") or "stage_and_alert")
        arena_status = str(boundary.get("arena_status") or "active")
        query = quote(location, safe="")
        maps_url = f"http://maps.apple.com/?daddr={query}&dirflg=d"

        if boundary_decision == "deny":
            event_payload = _record_shared_event(
                domain="calendar",
                kind="blocked",
                title="Calendar route blocked",
                detail=f"Route for {title} was blocked by boundary: {boundary_reason}",
                severity="medium",
                actor="chris",
                source="apple.calendar.route",
                source_id=request_id,
                navigation_target="systems",
                actions=["open"],
                trust_zone=trust_zone,
                authority_stage=authority_stage,
                why_now="A schedule routing request hit a trust boundary before a live Maps handoff.",
                metadata={"event_id": event_id, "location": location, "maps_url": maps_url, "arena_status": arena_status},
            )
            _create_notification_from_event(
                event_payload,
                category="calendar",
                delivery_mode="badge_only",
                available_actions=["open", "resolve"],
                source_summary="Blocked route handoff",
            )
            return _ok(
                {
                    "request_id": request_id,
                    "status": "blocked_by_boundary",
                    "event_id": event_id,
                    "title": title,
                    "location": location,
                    "maps_url": "",
                    "boundary_decision": boundary_decision,
                    "boundary_reason": boundary_reason,
                    "trust_zone": trust_zone,
                    "authority_stage": authority_stage,
                    "arena_status": arena_status,
                    "approval_mode": approval_mode,
                }
            )

        approval_request_id = ""
        supervision_decision: dict[str, Any] = {}
        if boundary_decision != "deny":
            approval_request_id, supervision_decision = _stage_calendar_route_governed_approval(
                actor="chris",
                event_id=event_id,
                title=title,
                location=location,
                maps_url=maps_url,
                trust_zone=trust_zone,
                boundary_reason=boundary_reason,
            )

        if approval_request_id:
            event_payload = _record_shared_event(
                domain="calendar",
                kind="stage_ready",
                title="Calendar route staged",
                detail=f"Route for {title} was staged for governed review before a live Maps handoff.",
                severity="low",
                actor="chris",
                source="apple.calendar.route",
                source_id=approval_request_id,
                navigation_target="needs",
                actions=["open", "stage"],
                trust_zone=trust_zone,
                authority_stage=authority_stage,
                why_now="A schedule routing request entered the governed review and sandbox path.",
                metadata={
                    "event_id": event_id,
                    "location": location,
                    "maps_url": maps_url,
                    "approval_mode": approval_mode,
                    "approval_request_id": approval_request_id,
                },
            )
            _create_notification_from_event(
                event_payload,
                category="calendar",
                delivery_mode="badge_only",
                available_actions=["open", "dismiss"],
                source_summary="Governed route handoff",
            )
            return _ok(
                {
                    "request_id": approval_request_id,
                    "approval_request_id": approval_request_id,
                    "status": "staged_for_review",
                    "event_id": event_id,
                    "title": title,
                    "location": location,
                    "maps_url": maps_url,
                    "sandbox_job_id": f"calendar-route:{event_id}",
                    "boundary_decision": boundary_decision,
                    "boundary_reason": boundary_reason,
                    "trust_zone": trust_zone,
                    "authority_stage": authority_stage,
                    "arena_status": arena_status,
                    "approval_mode": approval_mode,
                    "supervision_decision": supervision_decision,
                }
            )

        if boundary_decision != "allow":
            from .models import StagedActionQueueItem
            runtime.trust_support.enqueue_stage_action(
                StagedActionQueueItem(
                    request_id=request_id,
                    arena_id="household.schedule.routing",
                    action_type="calendar_route_review",
                    status="awaiting_principal_review",
                    created_at=_ts(),
                    principal_id="chris",
                )
            )
            event_payload = _record_shared_event(
                domain="calendar",
                kind="stage_ready",
                title="Calendar route staged",
                detail=f"Route for {title} was staged for review before a live Maps handoff.",
                severity="low",
                actor="chris",
                source="apple.calendar.route",
                source_id=request_id,
                navigation_target="systems",
                actions=["open", "stage"],
                trust_zone=trust_zone,
                authority_stage=authority_stage,
                why_now="A schedule routing request requires review before leaving the sandbox lane.",
                metadata={"event_id": event_id, "location": location, "maps_url": maps_url, "approval_mode": approval_mode},
            )
            _create_notification_from_event(
                event_payload,
                category="calendar",
                delivery_mode="badge_only",
                available_actions=["open", "dismiss"],
                source_summary="Staged route handoff",
            )
            return _ok(
                {
                    "request_id": request_id,
                    "status": "staged_for_review",
                    "event_id": event_id,
                    "title": title,
                    "location": location,
                    "maps_url": maps_url,
                    "boundary_decision": boundary_decision,
                    "boundary_reason": boundary_reason,
                    "trust_zone": trust_zone,
                    "authority_stage": authority_stage,
                    "arena_status": arena_status,
                    "approval_mode": approval_mode,
                    "supervision_decision": supervision_decision,
                }
            )

        _record_shared_event(
            domain="calendar",
            kind="info",
            title="Calendar route handed off",
            detail=f"Route prepared for {title}",
            severity="low",
            source="apple.calendar",
            source_id=request_id,
            navigation_target="navigate",
            actions=["open"],
            trust_zone=trust_zone,
            authority_stage=authority_stage,
            why_now="The household asked JARVIS to route to a calendar event location and the trust lane allowed a live handoff.",
            metadata={"event_id": event_id, "location": location, "maps_url": maps_url, "boundary_decision": boundary_decision},
        )
        return _ok(
            {
                "request_id": request_id,
                "status": "ready",
                "event_id": event_id,
                "title": title,
                "location": location,
                "maps_url": maps_url,
                "boundary_decision": boundary_decision,
                "boundary_reason": boundary_reason,
                "trust_zone": trust_zone,
                "authority_stage": authority_stage,
                "arena_status": arena_status,
                "approval_mode": approval_mode,
            }
        )

    # ── EventKit: Reminders ───────────────────────────────────────────────────

    @app.get("/api/apple/reminders/state")
    async def apple_reminders_state():
        payload = _safe_read_json(_APPLE_REMINDERS_PATH, {})
        return _ok(_build_apple_reminders_state(payload if isinstance(payload, dict) else {}))

    @app.post("/api/apple/reminders")
    async def apple_reminders(payload: dict):
        """Receives Reminders from EventKit on the iPhone.
        Writes to data/apple/reminders.json."""
        reminders = payload.get("reminders", [])
        out_path = _APPLE_REMINDERS_PATH
        _safe_write_json(out_path, {
            "reminders": reminders,
            "count":     len(reminders),
            "source":    "eventkit",
            "synced_at": _ts(),
        })
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

    @app.post("/api/apple/reminders/{reminder_id}/complete")
    async def apple_reminder_complete(reminder_id: str):
        return _ok(_governed_reminder_mutation(reminder_id, action_label="complete"))

    @app.post("/api/apple/reminders/{reminder_id}/snooze")
    async def apple_reminder_snooze(reminder_id: str, payload: dict | None = None):
        minutes = _coerce_int((payload or {}).get("minutes"), 60)
        if minutes <= 0:
            minutes = 60
        return _ok(_governed_reminder_mutation(reminder_id, action_label="snooze", minutes=minutes))

    # ── Focus Filter ─────────────────────────────────────────────────────────

    @app.post("/api/apple/focus")
    async def apple_focus(payload: dict):
        """Receives iOS Focus Filter state so JARVIS can adjust notification behavior."""
        return _ok(_governed_focus_mutation(payload))

    # ── Sound Analysis ───────────────────────────────────────────────────────

    @app.get("/api/apple/sound-alerts")
    async def apple_sound_alerts(limit: int = 12):
        rows = _safe_read_jsonl_tail(Path("data/apple/sound_alerts.jsonl"), limit=max(1, min(limit, 50)))
        return _ok(_build_apple_sound_state(rows))

    @app.post("/api/apple/sound-alerts/{alert_id}/resolve")
    async def apple_sound_alert_resolve(alert_id: str):
        rows = _safe_read_jsonl(Path("data/apple/sound_alerts.jsonl"))
        target = next(
            (
                row for row in rows
                if str(row.get("received_at") or row.get("timestamp") or "").strip() == str(alert_id or "").strip()
            ),
            None,
        )
        if target is None:
            raise HTTPException(status_code=404, detail="Sound alert not found")
        request_id = str(uuid.uuid4())
        boundary = runtime.assess_action_boundary(
            zone_id="household_safety",
            arena_id="household.safety.signal-resolution",
            action_type="signal_resolution",
            requested_stage="sandbox_live",
        )
        boundary_decision = str(boundary.get("decision") or "stage")
        boundary_reason = str(boundary.get("reason") or "")
        trust_zone = str(boundary.get("trust_zone") or "household_safety")
        authority_stage = str(boundary.get("authority_stage") or "stage_alert")
        approval_mode = str(boundary.get("approval_mode") or "stage_and_alert")
        arena_status = str(boundary.get("arena_status") or "active")

        if boundary_decision == "deny":
            event = _record_shared_event(
                domain="sound",
                kind="blocked",
                title=str(target.get("classification") or target.get("label") or "Sound alert blocked"),
                detail=f"Sound alert resolution blocked by boundary: {boundary_reason}",
                severity="medium",
                actor="jarvis",
                source="apple.sound_alert.resolve",
                source_id=request_id,
                navigation_target="systems",
                actions=["open"],
                trust_zone=trust_zone,
                authority_stage=authority_stage,
                why_now="A household sound alert resolution hit a trust boundary before it could execute live.",
                metadata={"alert_id": alert_id, "arena_status": arena_status},
            )
            _create_notification_from_event(
                event,
                category="household",
                delivery_mode="badge_only",
                available_actions=["open", "resolve"],
                source_summary="Blocked sound resolution",
            )
            return _ok(
                {
                    "request_id": request_id,
                    "status": "blocked_by_boundary",
                    "id": str(alert_id),
                    "resolved_at": "",
                    "boundary_decision": boundary_decision,
                    "boundary_reason": boundary_reason,
                    "trust_zone": trust_zone,
                    "authority_stage": authority_stage,
                    "arena_status": arena_status,
                    "approval_mode": approval_mode,
                }
            )

        if boundary_decision != "allow":
            from .models import StagedActionQueueItem
            runtime.trust_support.enqueue_stage_action(
                StagedActionQueueItem(
                    request_id=request_id,
                    arena_id="household.safety.signal-resolution",
                    action_type="sound_resolution_review",
                    status="awaiting_principal_review",
                    created_at=_ts(),
                    principal_id="chris",
                )
            )
            event = _record_shared_event(
                domain="sound",
                kind="stage_ready",
                title=str(target.get("classification") or target.get("label") or "Sound alert staged"),
                detail="Sound alert resolution staged for review before marking it resolved.",
                severity="low",
                actor="jarvis",
                source="apple.sound_alert.resolve",
                source_id=request_id,
                navigation_target="systems",
                actions=["open", "stage"],
                trust_zone=trust_zone,
                authority_stage=authority_stage,
                why_now="A household sound alert resolution requires review before leaving the sandbox lane.",
                metadata={"alert_id": alert_id, "approval_mode": approval_mode},
            )
            _create_notification_from_event(
                event,
                category="household",
                delivery_mode="badge_only",
                available_actions=["open", "dismiss"],
                source_summary="Staged sound resolution",
            )
            return _ok(
                {
                    "request_id": request_id,
                    "status": "staged_for_review",
                    "id": str(alert_id),
                    "resolved_at": "",
                    "boundary_decision": boundary_decision,
                    "boundary_reason": boundary_reason,
                    "trust_zone": trust_zone,
                    "authority_stage": authority_stage,
                    "arena_status": arena_status,
                    "approval_mode": approval_mode,
                }
            )

        resolved_at = _mark_signal_resolved("sound", alert_id)
        _record_shared_event(
            domain="sound",
            kind="resolved",
            title=str(target.get("classification") or target.get("label") or "Sound alert resolved"),
            detail=str(target.get("detail") or target.get("summary") or "A sound alert was resolved from Apple Systems."),
            severity="low",
            actor="jarvis",
            source="apple.sound_alert.resolve",
            source_id=request_id,
            navigation_target="systems",
            actions=["open"],
            trust_zone=trust_zone,
            authority_stage=authority_stage,
            why_now="A household sound alert was resolved from the Apple client.",
            metadata={"resolved_at": resolved_at, "boundary_decision": boundary_decision},
        )
        return _ok(
            {
                "request_id": request_id,
                "status": "resolved",
                "id": str(alert_id),
                "resolved_at": resolved_at,
                "boundary_decision": boundary_decision,
                "boundary_reason": boundary_reason,
                "trust_zone": trust_zone,
                "authority_stage": authority_stage,
                "arena_status": arena_status,
                "approval_mode": approval_mode,
            }
        )

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

    @app.get("/api/apple/vision/scans")
    async def apple_vision_scans(limit: int = 12):
        rows = _safe_read_jsonl_tail(Path("data/apple/vision_scans.jsonl"), limit=max(1, min(limit, 50)))
        return _ok(_build_apple_vision_state(rows))

    @app.post("/api/apple/vision/scans/{scan_id}/resolve")
    async def apple_vision_scan_resolve(scan_id: str):
        rows = _safe_read_jsonl(Path("data/apple/vision_scans.jsonl"))
        target = next(
            (
                row for row in rows
                if str(row.get("received_at") or "").strip() == str(scan_id or "").strip()
            ),
            None,
        )
        if target is None:
            raise HTTPException(status_code=404, detail="Vision scan not found")
        request_id = str(uuid.uuid4())
        boundary = runtime.assess_action_boundary(
            zone_id="household_perception",
            arena_id="household.perception.signal-resolution",
            action_type="signal_resolution",
            requested_stage="sandbox_live",
        )
        boundary_decision = str(boundary.get("decision") or "stage")
        boundary_reason = str(boundary.get("reason") or "")
        trust_zone = str(boundary.get("trust_zone") or "household_perception")
        authority_stage = str(boundary.get("authority_stage") or "sandbox_live")
        approval_mode = str(boundary.get("approval_mode") or "stage_and_alert")
        arena_status = str(boundary.get("arena_status") or "active")

        if boundary_decision == "deny":
            event = _record_shared_event(
                domain="vision",
                kind="blocked",
                title=str(target.get("context") or "Vision scan blocked"),
                detail=f"Vision scan resolution blocked by boundary: {boundary_reason}",
                severity="medium",
                actor="jarvis",
                source="apple.vision_scan.resolve",
                source_id=request_id,
                navigation_target="systems",
                actions=["open"],
                trust_zone=trust_zone,
                authority_stage=authority_stage,
                why_now="A household vision resolution hit a trust boundary before it could execute live.",
                metadata={"scan_id": scan_id, "arena_status": arena_status},
            )
            _create_notification_from_event(
                event,
                category="household",
                delivery_mode="badge_only",
                available_actions=["open", "resolve"],
                source_summary="Blocked vision resolution",
            )
            return _ok(
                {
                    "request_id": request_id,
                    "status": "blocked_by_boundary",
                    "id": str(scan_id),
                    "resolved_at": "",
                    "boundary_decision": boundary_decision,
                    "boundary_reason": boundary_reason,
                    "trust_zone": trust_zone,
                    "authority_stage": authority_stage,
                    "arena_status": arena_status,
                    "approval_mode": approval_mode,
                }
            )

        if boundary_decision != "allow":
            from .models import StagedActionQueueItem
            runtime.trust_support.enqueue_stage_action(
                StagedActionQueueItem(
                    request_id=request_id,
                    arena_id="household.perception.signal-resolution",
                    action_type="vision_resolution_review",
                    status="awaiting_principal_review",
                    created_at=_ts(),
                    principal_id="chris",
                )
            )
            event = _record_shared_event(
                domain="vision",
                kind="stage_ready",
                title=str(target.get("context") or "Vision scan staged"),
                detail="Vision scan resolution staged for review before marking it resolved.",
                severity="low",
                actor="jarvis",
                source="apple.vision_scan.resolve",
                source_id=request_id,
                navigation_target="systems",
                actions=["open", "stage"],
                trust_zone=trust_zone,
                authority_stage=authority_stage,
                why_now="A household vision resolution requires review before leaving the sandbox lane.",
                metadata={"scan_id": scan_id, "approval_mode": approval_mode},
            )
            _create_notification_from_event(
                event,
                category="household",
                delivery_mode="badge_only",
                available_actions=["open", "dismiss"],
                source_summary="Staged vision resolution",
            )
            return _ok(
                {
                    "request_id": request_id,
                    "status": "staged_for_review",
                    "id": str(scan_id),
                    "resolved_at": "",
                    "boundary_decision": boundary_decision,
                    "boundary_reason": boundary_reason,
                    "trust_zone": trust_zone,
                    "authority_stage": authority_stage,
                    "arena_status": arena_status,
                    "approval_mode": approval_mode,
                }
            )

        resolved_at = _mark_signal_resolved("vision", scan_id)
        _record_shared_event(
            domain="vision",
            kind="resolved",
            title=str(target.get("context") or "Vision scan resolved"),
            detail=str(target.get("text") or "")[:200] or "A vision scan was resolved from Apple Systems.",
            severity="low",
            actor="jarvis",
            source="apple.vision_scan.resolve",
            source_id=request_id,
            navigation_target="systems",
            actions=["open"],
            trust_zone=trust_zone,
            authority_stage=authority_stage,
            why_now="A household vision scan was resolved from the Apple client.",
            metadata={"resolved_at": resolved_at, "boundary_decision": boundary_decision},
        )
        return _ok(
            {
                "request_id": request_id,
                "status": "resolved",
                "id": str(scan_id),
                "resolved_at": resolved_at,
                "boundary_decision": boundary_decision,
                "boundary_reason": boundary_reason,
                "trust_zone": trust_zone,
                "authority_stage": authority_stage,
                "arena_status": arena_status,
                "approval_mode": approval_mode,
            }
        )

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

    @app.get("/api/apple/now-playing/state")
    async def apple_now_playing_state():
        data_root = Path("data/apple")
        payload = _safe_read_json(_APPLE_NOW_PLAYING_PATH, {})
        focus_payload = _safe_read_json(data_root / "focus_state.json", {})
        watch_status = (await apple_status()).get("data") or {}
        home_state = (await apple_home_state()).get("data") or {}
        posture = _compute_interruption_posture(
            watch_status=watch_status if isinstance(watch_status, dict) else {},
            home_state=home_state if isinstance(home_state, dict) else {},
            focus_payload=focus_payload if isinstance(focus_payload, dict) else {},
        )
        events = _event_log.recent(limit=20, domain="media")
        return _ok(_build_apple_now_playing_state(
            payload if isinstance(payload, dict) else {},
            events,
            posture=posture,
            focus_payload=focus_payload if isinstance(focus_payload, dict) else {},
        ))

    @app.post("/api/apple/now-playing")
    async def apple_now_playing(payload: dict):
        """Receives Now Playing info from MediaPlayer on the iPhone."""
        out_path = _APPLE_NOW_PLAYING_PATH
        _safe_write_json(out_path, {
            **{k: v for k, v in payload.items() if k != "artwork_b64"},
            "updated_at": _ts(),
        })
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

    @app.post("/api/apple/speak/push")
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
            overview = runtime.catalyst_overview()

            data_root = Path("data/catalyst")
            wl_path = data_root / "work_lifecycle.json"
            wl_raw = json.loads(wl_path.read_text()) if wl_path.exists() else {}
            wl_items = list(wl_raw.values()) if isinstance(wl_raw, dict) else wl_raw
            active_work = [
                {
                    "work_id":  str(i.get("work_id") or ""),
                    "title":    _truncate(str(i.get("title") or ""), 60),
                    "domain":   str(i.get("domain") or ""),
                    "lane":     str(i.get("lane") or ""),
                    "stage":    str(i.get("current_stage") or i.get("status") or ""),
                    "updated":  str(i.get("updated_at") or i.get("created_at") or ""),
                }
                for i in wl_items
                if str(i.get("status") or "").lower() not in ("done", "archived", "cancelled")
            ][:10]

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

            portfolio = dict(overview.get("live_workspace", {}).get("portfolio") or {})
            if not portfolio:
                pipeline_path = data_root / "pipeline_state.json"
                if pipeline_path.exists():
                    ps = json.loads(pipeline_path.read_text())
                    portfolio = ps.get("portfolio") or {}

            lanes = [
                {
                    "id": str(item.get("id") or ""),
                    "label": str(item.get("label") or item.get("title") or ""),
                    "description": str(item.get("description") or ""),
                    "status": str(item.get("status") or ""),
                }
                for item in (overview.get("portfolio_lanes") or [])
                if isinstance(item, dict)
            ]
            connectors = [
                {
                    "id": str(item.get("id") or ""),
                    "label": str(item.get("label") or ""),
                    "status": str(item.get("status") or ""),
                    "notes": str(item.get("notes") or ""),
                }
                for item in (overview.get("connectors") or [])
                if isinstance(item, dict)
            ]
            counts = overview.get("counts") if isinstance(overview.get("counts"), dict) else {}
            workflow_counts = {
                key: int(counts.get(key) or 0)
                for key in (
                    "signals",
                    "email_triage",
                    "meeting_extractions",
                    "briefings",
                    "drafts",
                    "project_briefs",
                    "implementation_plans",
                    "hypotheses",
                )
            }
            live_workspace = overview.get("live_workspace") if isinstance(overview.get("live_workspace"), dict) else {}
            catalyst_live = {
                "available": bool(live_workspace.get("available")),
                "live": bool(live_workspace.get("live")),
                "projects_count": len((live_workspace.get("projects") or {}).get("items") or []),
                "tasks_count": len((live_workspace.get("tasks") or {}).get("items") or []),
                "calendar_count": len((live_workspace.get("calendar") or {}).get("items") or []),
                "email_count": len((live_workspace.get("email") or {}).get("items") or []),
                "retrieved_at": str(live_workspace.get("retrievedAt") or ""),
            }
            recent_runs = overview.get("latest_runs") if isinstance(overview.get("latest_runs"), dict) else {}
            latest_runs = []
            for key, label in (
                ("briefing", "Briefing"),
                ("project_brief", "Project Brief"),
                ("hypothesis", "Hypothesis"),
                ("meeting_extraction", "Meeting Extraction"),
                ("email_triage", "Email Triage"),
            ):
                item = recent_runs.get(key)
                if not isinstance(item, dict) or not item:
                    continue
                latest_runs.append(
                    {
                        "id": str(item.get("run_id") or item.get("id") or key),
                        "label": label,
                        "title": _truncate(str(item.get("title") or item.get("opportunity") or item.get("recommendation") or item.get("summary") or label), 60),
                        "timestamp": str(item.get("timestamp") or item.get("created_at") or item.get("updated_at") or ""),
                    }
                )

            return _ok({
                "active_work": active_work,
                "signals":     signals,
                "portfolio":   portfolio,
                "lanes":       lanes,
                "connectors":  connectors,
                "workflow_counts": workflow_counts,
                "live_workspace": catalyst_live,
                "latest_runs": latest_runs,
                "continuity": _build_catalyst_continuity(
                    "chris",
                    active_work=active_work,
                    workflow_counts=workflow_counts,
                ),
                "updated_at":  _ts(),
            })
        except Exception as exc:
            logger.exception("apple_catalyst failed: %s", exc)
            return _ok({
                "active_work": [],
                "signals": [],
                "portfolio": {},
                "lanes": [],
                "connectors": [],
                "workflow_counts": {},
                "live_workspace": {
                    "available": False,
                    "live": False,
                    "projects_count": 0,
                    "tasks_count": 0,
                    "calendar_count": 0,
                    "email_count": 0,
                    "retrieved_at": "",
                },
                "latest_runs": [],
                "continuity": {
                    "subject_display_name": "Chris",
                    "briefing_style": "",
                    "active_domains": [],
                    "guidance_lines": [],
                    "profile_fact_count": 0,
                    "hottest_workflow": "",
                    "recent_profile_facts": [],
                    "recent_first_light": [],
                },
                "updated_at": _ts(),
            })

    @app.get("/api/apple/catalyst/ops")
    async def apple_catalyst_ops():
        overview = await asyncio.to_thread(_build_catalyst_ops_overview, runtime)
        return _ok(overview)

    @app.post("/api/apple/catalyst/progress-focus")
    async def apple_catalyst_progress_focus(payload: dict):
        module = str(payload.get("module") or "").strip()
        route = str(payload.get("route") or "/progress-center").strip() or "/progress-center"
        actor = str(payload.get("actor") or "chris").strip() or "chris"
        reason = str(payload.get("reason") or "").strip()
        if not module:
            raise HTTPException(status_code=400, detail="module is required")
        if not reason:
            reason = f"Catalyst moved the shared progress focus to {module}."
        entry = await asyncio.to_thread(
            _save_catalyst_progress_focus,
            module=module,
            route=route,
            actor=actor,
            reason=reason,
        )
        return _ok(entry)

    @app.post("/api/apple/catalyst/approvals/{request_id}/approve")
    async def apple_catalyst_approve(request_id: str, payload: dict | None = None):
        payload = payload if isinstance(payload, dict) else {}
        actor = str(payload.get("actor") or "chris").strip() or "chris"
        try:
            result = await asyncio.to_thread(_approve_catalyst_approval, runtime, request_id=request_id, actor=actor)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return _ok(result)

    @app.post("/api/apple/catalyst/recovery-cases/{case_id}/execute")
    async def apple_catalyst_recovery_execute(case_id: str, payload: dict | None = None):
        payload = payload if isinstance(payload, dict) else {}
        actor = str(payload.get("actor") or "chris").strip() or "chris"
        action_type = str(payload.get("action_type") or "retry").strip().lower() or "retry"
        note = str(payload.get("note") or "").strip()
        try:
            result = await asyncio.to_thread(
                _execute_catalyst_recovery_case,
                case_id=case_id,
                actor=actor,
                action_type=action_type,
                note=note,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _ok(result)

    @app.post("/api/apple/catalyst/recovery-cases/{case_id}/remediation")
    async def apple_catalyst_recovery_remediation(case_id: str, payload: dict | None = None):
        payload = payload if isinstance(payload, dict) else {}
        actor = str(payload.get("actor") or "chris").strip() or "chris"
        action_type = str(payload.get("action_type") or "stage").strip().lower() or "stage"
        note = str(payload.get("note") or "").strip()
        try:
            result = await asyncio.to_thread(
                _remediate_catalyst_recovery_case,
                case_id=case_id,
                actor=actor,
                action_type=action_type,
                note=note,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _ok(result)

    @app.post("/api/apple/catalyst/recovery-cases/{case_id}/plan/execute-next")
    async def apple_catalyst_recovery_plan_execute_next(case_id: str, payload: dict | None = None):
        payload = payload if isinstance(payload, dict) else {}
        actor = str(payload.get("actor") or "chris").strip() or "chris"
        note = str(payload.get("note") or "").strip()
        try:
            result = await asyncio.to_thread(
                _advance_catalyst_recovery_plan,
                case_id=case_id,
                actor=actor,
                note=note,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _ok(result)

    @app.post("/api/apple/catalyst/agents/{agent_id}/queue-run")
    async def apple_catalyst_agent_queue(agent_id: str, payload: dict | None = None):
        payload = payload if isinstance(payload, dict) else {}
        actor = str(payload.get("actor") or "chris").strip() or "chris"
        try:
            result = await asyncio.to_thread(
                _queue_catalyst_agent_run,
                agent_id=agent_id,
                actor=actor,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return _ok(result)

    @app.post("/api/apple/catalyst/agents/{agent_id}/assignment")
    async def apple_catalyst_agent_assignment(agent_id: str, payload: dict | None = None):
        payload = payload if isinstance(payload, dict) else {}
        actor = str(payload.get("actor") or "chris").strip() or "chris"
        mission_id = str(payload.get("mission_id") or "").strip()
        policy_assignment = str(payload.get("policy_assignment") or "").strip()
        purpose = str(payload.get("purpose") or "").strip()
        try:
            result = await asyncio.to_thread(
                _save_catalyst_agent_assignment,
                runtime,
                agent_id=agent_id,
                mission_id=mission_id,
                actor=actor,
                policy_assignment=policy_assignment,
                purpose=purpose,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _ok(result)

    @app.post("/api/apple/catalyst/supervision/{request_id}/{action}")
    async def apple_catalyst_supervision_action(request_id: str, action: str, payload: dict | None = None):
        payload = payload if isinstance(payload, dict) else {}
        actor = str(payload.get("actor") or "chris").strip() or "chris"
        reason = str(payload.get("reason") or "").strip()
        try:
            result = await asyncio.to_thread(
                _resolve_catalyst_supervision_item,
                runtime,
                request_id=request_id,
                action=action,
                actor=actor,
                reason=reason,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _ok(result)

    @app.post("/api/apple/catalyst/missions/{mission_id}/status")
    async def apple_catalyst_mission_status(mission_id: str, payload: dict | None = None):
        payload = payload if isinstance(payload, dict) else {}
        actor = str(payload.get("actor") or "chris").strip() or "chris"
        status = str(payload.get("status") or "active").strip() or "active"
        note = str(payload.get("note") or "").strip()
        try:
            result = await asyncio.to_thread(
                _update_catalyst_mission_status,
                runtime,
                mission_id=mission_id,
                status=status,
                actor=actor,
                note=note,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return _ok(result)

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
                    bridge_entries = await asyncio.to_thread(
                        lambda: [entry.to_dict() for entry in bridge.get_recent_entries(limit=12)]
                    )
                    merged_entries: list[dict[str, Any]] = []
                    seen_entry_ids: set[str] = set()
                    for source_entry in list(bridge_entries) + list(raw_entries):
                        if not isinstance(source_entry, dict):
                            continue
                        entry_id = _chronicle_entry_id(source_entry)
                        if entry_id in seen_entry_ids:
                            continue
                        seen_entry_ids.add(entry_id)
                        merged_entries.append(source_entry)
                    entries = [_chronicle_bridge_entry_to_apple(entry) for entry in merged_entries[:12] if _chronicle_actor_matches(entry, actor)]

                    bridge_context = await asyncio.to_thread(bridge.get_context)
                    if isinstance(bridge_context, dict) and bridge_context.get("ok"):
                        enriched_prayers = _enrich_chronicle_prayers(bridge_context.get("active_prayers") or [])
                        context = {
                            "study": bridge_context.get("study"),
                            "active_prayers": enriched_prayers,
                            "todays_rhythm": bridge_context.get("todays_rhythm"),
                            "top_themes": bridge_context.get("top_themes") or [],
                            "total_entries": int(bridge_context.get("total_entries") or len(entries)),
                            "active_prayer_count": sum(1 for prayer in enriched_prayers if not prayer.get("answered")),
                            "answered_prayer_count": int(bridge_context.get("answered_prayer_count") or 0) + sum(
                                1 for prayer in enriched_prayers if prayer.get("answered")
                            ),
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

            review_summary = ChronicleReviewStore().review_summary(actor_id=actor, limit=6)

            return _ok({
                "entries": entries,
                "context": context,
                "patterns": patterns,
                "continuity": _chronicle_continuity_packet(actor, raw_entries, context if isinstance(context, dict) else {}),
                "study_workspace": _chronicle_study_workspace(context if isinstance(context, dict) else {}),
                "review_lane": list(review_summary.get("items") or []),
                "review_count": int(review_summary.get("count", 0) or 0),
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
                "continuity": {
                    "relevant_facts": [],
                    "similar_entries": [],
                    "recall_prompt": "",
                },
                "study_workspace": None,
                "review_lane": [],
                "review_count": 0,
                "updated_at": _ts(),
            })

    @app.post("/api/apple/chronicle/capture")
    async def apple_chronicle_capture(payload: dict):
        """Capture a quick reflection or prayer from the phone."""
        try:
            entry_type = str(payload.get("type") or "reflection")
            note = str(payload.get("note") or "").strip()
            actor = str(payload.get("actor_id") or "chris")
            return _ok(_capture_chronicle_entry(entry_type=entry_type, note=note, actor=actor))
        except Exception as exc:
            return _ok({"captured": False, "reason": str(exc)})

    @app.post("/api/apple/chronicle/prayers/{prayer_id}/pray")
    async def apple_chronicle_prayer_prayed(prayer_id: str, payload: dict):
        actor = str(payload.get("actor_id") or "chris").strip() or "chris"
        note = str(payload.get("note") or "").strip()
        return _ok(_mark_chronicle_prayer_prayed(prayer_id=prayer_id, actor=actor, note=note))

    @app.post("/api/apple/chronicle/prayers/{prayer_id}/answer")
    async def apple_chronicle_prayer_answered(prayer_id: str, payload: dict):
        actor = str(payload.get("actor_id") or "chris").strip() or "chris"
        note = str(payload.get("note") or "").strip()
        return _ok(_mark_chronicle_prayer_answered(prayer_id=prayer_id, actor=actor, note=note))

    @app.post("/api/apple/chronicle/study/save")
    async def apple_chronicle_study_save(payload: dict):
        actor = str(payload.get("actor_id") or "chris").strip() or "chris"
        title = str(payload.get("title") or "").strip()
        passage = str(payload.get("passage") or "").strip()
        notes = str(payload.get("notes") or "").strip()
        return _ok(_save_chronicle_study_entry(actor=actor, title=title, passage=passage, notes=notes))

    @app.post("/api/apple/chronicle/entries/{entry_id}/review")
    async def apple_chronicle_review(entry_id: str, payload: dict):
        actor = str(payload.get("actor_id") or payload.get("actor") or "chris").strip() or "chris"
        status = str(payload.get("status") or "").strip().lower()
        note = str(payload.get("note") or "").strip()
        title = str(payload.get("title") or "Chronicle entry").strip() or "Chronicle entry"
        entry_type = str(payload.get("entry_type") or "reflection").strip() or "reflection"
        try:
            return _ok(
                _review_chronicle_entry(
                    entry_id=entry_id,
                    actor=actor,
                    title=title,
                    entry_type=entry_type,
                    status=status,
                    note=note,
                )
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

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

            agents: list[dict] = []
            try:
                from .faith_agents import get_agents
                agents = await asyncio.to_thread(get_agents)
            except Exception:
                pass

            passage_prompt = str(fw.get("passage") or "today's passage")
            theme_prompt = str(morning_context.get("theme") or "the next faithful step")
            focus_prompt = str(morning_context.get("focus") or "what God is forming today")
            formation_prompts = [
                f"Ask about {passage_prompt} with the faith council.",
                f"Pray into {theme_prompt}.",
                f"Seek counsel on {focus_prompt}.",
            ]

            daily_word = {
                "agent":      str(fw.get("agent_name") or "JARVIS"),
                "agent_title": str(fw.get("agent_title") or ""),
                "word":       str(fw.get("word") or ""),
                "passage":    str(fw.get("passage") or ""),
                "domain":     str(fw.get("domain") or ""),
                "generated_at": str(fw.get("generated_at") or ""),
            }

            return _ok({
                "daily_word": daily_word,
                "morning_context": morning_context,
                "agents": agents,
                "formation_prompts": formation_prompts,
                "continuity": _build_faith_continuity(
                    actor,
                    morning_context=morning_context if isinstance(morning_context, dict) else {},
                    formation_prompts=formation_prompts,
                    agents=agents,
                    daily_word=daily_word,
                ),
                "updated_at": _ts(),
            })
        except Exception as exc:
            logger.exception("apple_faith failed: %s", exc)
            return _ok({"daily_word": {"agent": "JARVIS", "word": "", "passage": "", "domain": "", "agent_title": "", "generated_at": ""}, "morning_context": {}, "agents": [], "formation_prompts": [], "continuity": {"subject_display_name": "Chris", "theme": "", "focus": "", "passage": "", "council_domains": [], "guidance_lines": [], "profile_fact_count": 0, "recent_profile_facts": [], "recent_first_light": []}, "updated_at": _ts()})

    @app.post("/api/apple/faith/chat")
    async def apple_faith_chat(payload: dict):
        """Agent chat for the iPhone Faith tab."""
        try:
            from .faith_agents import chat as faith_chat, get_agent

            agent_id = str(payload.get("agent_id") or "").strip().lower()
            messages = payload.get("messages") or []
            passage = str(payload.get("passage") or "").strip()
            if not agent_id:
                raise HTTPException(status_code=400, detail="agent_id is required")
            if not isinstance(messages, list) or not messages:
                raise HTTPException(status_code=400, detail="messages are required")

            reply = await faith_chat(agent_id=agent_id, messages=messages, runtime=runtime, passage=passage)
            agent = get_agent(agent_id) or {}
            return _ok({
                "reply": str(reply or ""),
                "agent_id": agent_id,
                "agent_name": str(agent.get("name") or agent_id.title()),
            })
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("apple_faith_chat failed: %s", exc)
            raise HTTPException(status_code=500, detail="Faith chat unavailable") from exc

    # ── Publishing dashboard ──────────────────────────────────────────────────

    @app.get("/api/apple/publishing")
    async def apple_publishing():
        """Publishing overview for the iPhone Publish tab."""
        try:
            from .publishing_suite import PublishingStore, RobbieRobertsonAgent

            pub_root = Path.home() / ".jarvis" / "publishing"
            publishing_store = PublishingStore(root=pub_root)
            publishing_agent = RobbieRobertsonAgent(publishing_store)

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
            projects: list[dict[str, Any]] = []
            for p in active_projects[:8]:
                project_id = str(p.get("project_id") or "")
                project_model = publishing_store.get_project(project_id) if project_id else None
                checklist = publishing_agent.get_publishing_checklist(project_model) if project_model else []
                checklist_items = [item for item in checklist if isinstance(item, dict)]
                completed_steps = sum(1 for item in checklist_items if _boolish(item.get("completed")))
                total_steps = len(checklist_items)
                checklist_progress = f"{completed_steps}/{total_steps}" if total_steps else ""
                checklist_percent = round((completed_steps / total_steps) * 100) if total_steps else 0

                projects.append(
                    {
                        "project_id": project_id,
                        "title": str(p.get("title") or ""),
                        "type": str(p.get("project_type") or ""),
                        "status": str(p.get("status") or ""),
                        "platform": str(p.get("platform") or ""),
                        "url": p.get("url") or None,
                        "description": str(p.get("description") or ""),
                        "notes": str(p.get("notes") or ""),
                        "checklist_progress": checklist_progress,
                        "checklist_percent": checklist_percent,
                        "platform_focus": _publishing_platform_focus(
                            str(p.get("platform") or ""),
                            str(p.get("project_type") or ""),
                        ),
                        "updated_at": str(p.get("updated_at") or p.get("created_at") or ""),
                    }
                )
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
            active_project_model = publishing_store.get_project(active_project_id) if active_project_id else None
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

            launch_workspace = _publishing_launch_workspace(
                project=active_project_raw,
                strategy=strategy if isinstance(strategy, dict) else None,
                checklist=publishing_agent.get_publishing_checklist(active_project_model) if active_project_model else [],
            )

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
            launch_history = PublishHistoryStore().summary(actor_id="chris", limit=6)

            return _ok({
                "projects":        projects,
                "revenue_summary": revenue_summary,
                "upcoming":        upcoming,
                "pending_reviews": pending_reviews,
                "pending_reviews_count": len(pending_reviews),
                "launch_control": active_project,
                "launch_workspace": launch_workspace,
                "launch_history": launch_history,
                "history_count": int(launch_history.get("count") or 0),
                "action_items": action_items,
                "continuity": _build_publishing_continuity(
                    "chris",
                    projects=projects,
                    pending_reviews=pending_reviews,
                    action_items=action_items,
                    launch_workspace=launch_workspace if isinstance(launch_workspace, dict) else None,
                ),
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
                "launch_workspace": None,
                "launch_history": {"count": 0, "counts": {}, "items": []},
                "history_count": 0,
                "action_items": [],
                "continuity": {
                    "subject_display_name": "Chris",
                    "briefing_style": "",
                    "launch_focus": "",
                    "active_platforms": [],
                    "pending_review_pressure": 0,
                    "profile_fact_count": 0,
                    "guidance_lines": [],
                    "recent_profile_facts": [],
                    "recent_first_light": [],
                },
                "updated_at": _ts(),
            })

    def _review_record(row: dict[str, Any]) -> dict[str, Any]:
        return {
            "review_id": str(row.get("review_id") or ""),
            "title": str(row.get("title") or ""),
            "slug": str(row.get("slug") or ""),
            "stage_key": str(row.get("stage_key") or ""),
            "stage_display": str(row.get("stage_display") or ""),
            "content_preview": str(row.get("content_preview") or ""),
            "word_count": _coerce_int(row.get("word_count")),
            "ready_since": str(row.get("ready_since") or ""),
            "approval_id": str(row.get("approval_id") or ""),
        }

    def _governed_publication_review_mutation(
        review_id: str,
        *,
        target_status: str,
        action_label: str,
        feedback: str = "",
    ) -> dict[str, Any]:
        pub_root = Path.home() / ".jarvis" / "publishing"
        reviews_path = pub_root / "ghostwritr_reviews.jsonl"
        rows = _safe_read_jsonl(reviews_path)
        selected_row = next((row for row in rows if str(row.get("review_id") or "") == review_id), None)
        if not isinstance(selected_row, dict):
            raise HTTPException(status_code=404, detail=f"Review {review_id} not found")
        review = _review_record(selected_row)
        request_id = str(uuid.uuid4())
        boundary = runtime.assess_action_boundary(
            zone_id="publication_review",
            arena_id="publication.review.workflow",
            action_type="publishing_review",
            requested_stage="sandbox_live",
        )
        boundary_decision = str(boundary.get("decision") or "stage")
        boundary_reason = str(boundary.get("reason") or "")
        trust_zone = str(boundary.get("trust_zone") or "publication_review")
        authority_stage = str(boundary.get("authority_stage") or "stage_alert")
        approval_mode = str(boundary.get("approval_mode") or "stage_and_alert")
        arena_status = str(boundary.get("arena_status") or "active")

        if boundary_decision == "deny":
            return {
                "request_id": request_id,
                "status": "blocked_by_boundary",
                "review": review,
                "performed_action": action_label,
                "boundary_decision": boundary_decision,
                "boundary_reason": boundary_reason,
                "trust_zone": trust_zone,
                "authority_stage": authority_stage,
                "arena_status": arena_status,
                "approval_mode": approval_mode,
                "feedback": feedback,
            }

        if boundary_decision != "allow":
            from .models import StagedActionQueueItem

            runtime.trust_support.enqueue_stage_action(
                StagedActionQueueItem(
                    request_id=request_id,
                    arena_id="publication.review.workflow",
                    action_type=f"publishing_{action_label}_review",
                    status="awaiting_principal_review",
                    created_at=_ts(),
                    principal_id="chris",
                )
            )
            staged_review = dict(review)
            staged_review["decision_reason"] = boundary_reason
            return {
                "request_id": request_id,
                "status": "staged_for_review",
                "review": staged_review,
                "performed_action": action_label,
                "boundary_decision": boundary_decision,
                "boundary_reason": boundary_reason,
                "trust_zone": trust_zone,
                "authority_stage": authority_stage,
                "arena_status": arena_status,
                "approval_mode": approval_mode,
                "feedback": feedback,
            }

        now = _ts()
        for row in rows:
            if str(row.get("review_id") or "") == review_id:
                row["jarvis_status"] = target_status
                row["feedback"] = feedback if action_label == "revise" else str(row.get("feedback") or "")
                row["reviewed_at"] = now
                break
        reviews_path.write_text(
            "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + ("\n" if rows else ""),
            encoding="utf-8",
        )
        updated_row = next((row for row in rows if str(row.get("review_id") or "") == review_id), selected_row)
        return {
            "request_id": request_id,
            "status": "approved" if action_label == "approve" else "needs_revision",
            "review": _review_record(updated_row),
            "performed_action": action_label,
            "boundary_decision": boundary_decision,
            "boundary_reason": boundary_reason,
            "trust_zone": trust_zone,
            "authority_stage": authority_stage,
            "arena_status": arena_status,
            "approval_mode": approval_mode,
            "feedback": feedback,
        }

    def _publishing_checklist_action_result(
        *,
        project_dict: dict[str, Any],
        strategy: dict[str, Any] | None,
        agent: Any,
        mutation: dict[str, Any],
        step_label: str,
        completed: bool,
        actor: str,
    ) -> dict[str, Any]:
        project_id = str(project_dict.get("project_id") or "")
        checklist = agent.get_publishing_checklist(agent._store.get_project(project_id)) if project_id else []
        workspace = _publishing_launch_workspace(
            project=project_dict,
            strategy=strategy if isinstance(strategy, dict) else None,
            checklist=checklist,
        )
        action = "Complete Publish Checklist Step" if completed else "Reopen Publish Checklist Step"
        detail = (
            f"{step_label} marked complete for {str(project_dict.get('title') or project_id).strip() or project_id}."
            if completed
            else f"{step_label} reopened for {str(project_dict.get('title') or project_id).strip() or project_id}."
        )
        _record_operator_action(
            actor=actor,
            domain="publish",
            action=action,
            detail=detail,
            why_now="Apple publish surfaces advanced a real launch checklist step instead of only observing the queue.",
            result_summary=f"Publish checklist now at {mutation.get('progress') or 'updated'}.",
            route="/publish",
            route_label="Open Publish",
            related_kind="publishing-checklist",
            related_label=str(project_dict.get("title") or project_id).strip() or project_id,
        )
        focus = ProgressFocusStore(_ACTIVITY_AUDIT_ROOT).save_focus(
            module="Publish",
            reason=detail,
            route="/publish",
            actor=actor,
        )
        history_entry = _record_publish_history(
            actor_id=actor,
            event_type="checklist-completed" if completed else "checklist-reopened",
            title=action,
            detail=detail,
            status_label="Completed" if completed else "Reopened",
            related_label=str(project_dict.get("title") or project_id).strip() or project_id,
            project_id=project_id,
            step=str(mutation.get("step") or ""),
        )
        return {
            "status": "completed" if completed else "reopened",
            "project_id": project_id,
            "step": str(mutation.get("step") or ""),
            "label": step_label,
            "completed": completed,
            "progress": str(mutation.get("progress") or ""),
            "percent": int(mutation.get("percent") or 0),
            "workspace": workspace,
            "focus": focus,
            "history_entry": history_entry,
        }

    def _record_publish_history(
        *,
        actor_id: str,
        event_type: str,
        title: str,
        detail: str,
        status_label: str,
        related_label: str = "",
        project_id: str = "",
        review_id: str = "",
        step: str = "",
    ) -> dict[str, Any]:
        return PublishHistoryStore().record_event(
            actor_id=actor_id,
            event_type=event_type,
            title=title,
            detail=detail,
            status_label=status_label,
            route="/publish",
            related_label=related_label,
            project_id=project_id,
            review_id=review_id,
            step=step,
        )

    @app.post("/api/apple/publishing/reviews/{review_id}/approve")
    async def apple_publishing_approve_review(review_id: str):
        pub_root = Path.home() / ".jarvis" / "publishing"
        reviews_path = pub_root / "ghostwritr_reviews.jsonl"
        rows = _safe_read_jsonl(reviews_path)
        if not any(str(row.get("review_id") or "") == review_id for row in rows):
            raise HTTPException(status_code=404, detail=f"Review {review_id} not found")
        result = _governed_publication_review_mutation(
                review_id,
                target_status="approved",
                action_label="approve",
            )
        _record_operator_action(
            actor="Chris",
            domain="publish",
            action="Approve Publishing Review",
            detail=f"Approved publishing review {result.get('review', {}).get('title') or review_id}.",
            why_now="Apple publish surface cleared a pending editorial review.",
            result_summary=f"Publishing review status: {result.get('status') or 'approved'}",
            route="/publish",
            route_label="Open Publish",
            related_kind="publishing-review",
            related_label=str(result.get("review", {}).get("title") or review_id),
        )
        focus = ProgressFocusStore(_ACTIVITY_AUDIT_ROOT).save_focus(
            module="Publish",
            reason=f"Apple publish surface approved {str(result.get('review', {}).get('title') or review_id).strip() or review_id}.",
            route="/publish",
            actor="Chris",
        )
        result["focus"] = focus
        result["history_entry"] = _record_publish_history(
            actor_id="Chris",
            event_type="review-approved",
            title="Approve Publish Review",
            detail=f"Approved publishing review {str(result.get('review', {}).get('title') or review_id).strip() or review_id}.",
            status_label="Approved",
            related_label=str(result.get("review", {}).get("title") or review_id).strip() or review_id,
            review_id=review_id,
        )
        return _ok(result)

    @app.post("/api/apple/publishing/reviews/{review_id}/revise")
    async def apple_publishing_revise_review(review_id: str, payload: dict[str, Any]):
        pub_root = Path.home() / ".jarvis" / "publishing"
        reviews_path = pub_root / "ghostwritr_reviews.jsonl"
        rows = _safe_read_jsonl(reviews_path)
        feedback = str(payload.get("feedback") or "").strip() or "Needs revision from JarvisPhone."
        if not any(str(row.get("review_id") or "") == review_id for row in rows):
            raise HTTPException(status_code=404, detail=f"Review {review_id} not found")
        result = _governed_publication_review_mutation(
                review_id,
                target_status="needs_revision",
                action_label="revise",
                feedback=feedback,
            )
        _record_operator_action(
            actor="Chris",
            domain="publish",
            action="Request Publishing Revision",
            detail=f"Requested revision for publishing review {result.get('review', {}).get('title') or review_id}.",
            why_now="Apple publish surface sent editorial feedback back into the launch pipeline.",
            result_summary=f"Publishing review status: {result.get('status') or 'needs_revision'}",
            route="/publish",
            route_label="Open Publish",
            related_kind="publishing-review",
            related_label=str(result.get("review", {}).get("title") or review_id),
        )
        focus = ProgressFocusStore(_ACTIVITY_AUDIT_ROOT).save_focus(
            module="Publish",
            reason=f"Apple publish surface requested revision for {str(result.get('review', {}).get('title') or review_id).strip() or review_id}.",
            route="/publish",
            actor="Chris",
        )
        result["focus"] = focus
        result["history_entry"] = _record_publish_history(
            actor_id="Chris",
            event_type="review-revision",
            title="Request Publish Revision",
            detail=f"Requested revision for publishing review {str(result.get('review', {}).get('title') or review_id).strip() or review_id}.",
            status_label="Revision Requested",
            related_label=str(result.get("review", {}).get("title") or review_id).strip() or review_id,
            review_id=review_id,
        )
        return _ok(result)

    @app.post("/api/apple/publishing/checklist/{project_id}/{step}")
    async def apple_publishing_checklist_step(project_id: str, step: str, payload: dict[str, Any] | None = None):
        from .publishing_suite import PublishingStore, RobbieRobertsonAgent

        body = payload or {}
        completed = bool(body.get("completed", True))
        actor = str(body.get("actor") or "Chris").strip() or "Chris"

        pub_root = Path.home() / ".jarvis" / "publishing"
        store = PublishingStore(root=pub_root)
        agent = RobbieRobertsonAgent(store)
        project = store.get_project(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail=f"Publishing project not found: {project_id}")

        checklist = list(agent.get_publishing_checklist(project))
        matched = next((item for item in checklist if str(item.get("step") or "").strip() == step), None)
        if matched is None:
            raise HTTPException(status_code=404, detail=f"Checklist step not found: {step}")

        strategy = _safe_read_json(pub_root / "launch_strategies.json", {}).get(project_id)
        mutation = agent.track_kdp_checklist(project_id, step, completed)
        return _ok(
            _publishing_checklist_action_result(
                project_dict=project.to_dict(),
                strategy=strategy if isinstance(strategy, dict) else None,
                agent=agent,
                mutation=mutation,
                step_label=str(matched.get("label") or step).strip() or step,
                completed=completed,
                actor=actor,
            )
        )

    # ── Huddle ────────────────────────────────────────────────────────────────

    @app.get("/api/apple/huddle")
    async def apple_huddle():
        """Agent standup huddle for the iPhone Huddle tab."""
        try:
            from .dossier import get_dossier_store
            from .party_mode import get_party_controller
            from .standup import collect_all_standups
            from dataclasses import asdict

            runtime_snapshot = runtime.background_agent_status()
            party_controller = get_party_controller(runtime)
            party_status = party_controller.get_status()
            dossier_store = get_dossier_store()
            ready_dossiers = [
                item for item in dossier_store.get_all()
                if str(getattr(item, "status", "") or "").strip().lower() != "presented"
            ]
            ready_dossiers.sort(key=lambda item: str(getattr(item, "updated_at", "") or ""), reverse=True)

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
            runtime_statuses = []
            for item in (runtime_snapshot.get("statuses") or [])[:6]:
                if not isinstance(item, dict):
                    continue
                runtime_statuses.append({
                    "agent_id": str(item.get("agent_id") or ""),
                    "label": str(item.get("label") or item.get("agent_id") or ""),
                    "state": str(item.get("state") or "idle"),
                    "reason": _truncate(str(item.get("reason") or ""), 120),
                    "last_run_at": str(item.get("last_run_at") or ""),
                    "next_run_at": str(item.get("next_run_at") or ""),
                    "due_now": bool(item.get("due_now")),
                    "priority": int(item.get("priority") or 0),
                })
            dossiers = []
            for dossier in ready_dossiers[:4]:
                dossiers.append({
                    "dossier_id": str(getattr(dossier, "dossier_id", "") or ""),
                    "title": _truncate(str(getattr(dossier, "title", "") or "Untitled"), 80),
                    "status": str(getattr(dossier, "status", "") or ""),
                    "executive_summary": _truncate(str(getattr(dossier, "executive_summary", "") or getattr(dossier, "market_opportunity", "") or ""), 160),
                    "first_action": _truncate(str(getattr(dossier, "first_action", "") or ""), 120),
                    "confidence_score": float(getattr(dossier, "confidence_score", 0.0) or 0.0),
                    "revenue_estimate_low": int(getattr(dossier, "revenue_estimate_low", 0) or 0),
                    "revenue_estimate_high": int(getattr(dossier, "revenue_estimate_high", 0) or 0),
                    "effort_hours": int(getattr(dossier, "effort_hours", 0) or 0),
                    "updated_at": str(getattr(dossier, "updated_at", "") or getattr(dossier, "created_at", "") or ""),
                })
            try:
                from .ideas import list_ideas, stats as idea_stats

                summary = idea_stats()
                ideas = list_ideas()
                by_status = dict(summary.get("by_status") or {})
                idea_inbox = {
                    "total": int(summary.get("total") or 0),
                    "captured_count": int(by_status.get("captured") or 0),
                    "queued_count": int(by_status.get("queued") or 0),
                    "recent": [
                        {
                            "id": str(item.get("id") or ""),
                            "text": _truncate(str(item.get("text") or ""), 100),
                            "status": str(item.get("status") or ""),
                            "domain": str(item.get("domain") or ""),
                            "created_at": str(item.get("created_at") or ""),
                        }
                        for item in ideas[:6]
                        if isinstance(item, dict)
                    ],
                }
            except Exception:
                idea_inbox = {"total": 0, "captured_count": 0, "queued_count": 0, "recent": []}
            return _ok({
                "reports": reports[:15],
                "blockers": [str(b)[:80] for b in (h.get("blockers") or [])[:5]],
                "highlights": [str(hl)[:80] for hl in (h.get("highlights") or [])[:5]],
                "approvals": approvals[:8],
                "approvals_count": int(len(h.get("approvals_needed") or [])),
                "total_active_work": int(h.get("total_active_work") or 0),
                "runtime": {
                    "active_mode": str(runtime_snapshot.get("active_mode") or ""),
                    "quiet_hours_active": bool(runtime_snapshot.get("quiet_hours_active")),
                    "awake_count": int(runtime_snapshot.get("awake_count") or 0),
                    "idle_count": int(runtime_snapshot.get("idle_count") or 0),
                    "blocked_count": int(runtime_snapshot.get("blocked_count") or 0),
                    "last_tick_at": str(runtime_snapshot.get("last_tick_at") or ""),
                    "statuses": runtime_statuses,
                },
                "party_mode": {
                    "status": str(party_status.get("status") or "idle"),
                    "triggered_by": str(party_status.get("triggered_by") or ""),
                    "dossiers_built_count": len(party_status.get("dossiers_built") or []),
                    "dossiers_attempted": int(party_status.get("dossiers_attempted") or 0),
                    "items_dreamed": int(party_status.get("items_dreamed") or 0),
                    "items_researched": int(party_status.get("items_researched") or 0),
                    "last_log": _truncate(str(party_status.get("last_log") or ""), 140),
                    "started_at": str(party_status.get("started_at") or ""),
                    "ended_at": str(party_status.get("ended_at") or ""),
                },
                "dossiers": dossiers,
                "idea_inbox": idea_inbox,
                "continuity": _build_huddle_continuity(
                    "chris",
                    reports=reports[:15],
                    blockers=[str(b)[:80] for b in (h.get("blockers") or [])[:5]],
                    party_status=party_status if isinstance(party_status, dict) else {},
                    dossiers=dossiers,
                ),
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
                "runtime": None,
                "party_mode": None,
                "dossiers": [],
                "idea_inbox": {"total": 0, "captured_count": 0, "queued_count": 0, "recent": []},
                "continuity": {
                    "subject_display_name": "Chris",
                    "council_focus": "",
                    "active_domains": [],
                    "ready_dossier_count": 0,
                    "profile_fact_count": 0,
                    "guidance_lines": [],
                    "recent_profile_facts": [],
                    "recent_first_light": [],
                },
                "updated_at": _ts(),
            })

    @app.post("/api/apple/huddle/party-mode/start")
    async def apple_huddle_start_party_mode():
        from .party_mode import get_party_controller

        ctrl = get_party_controller(runtime)
        status = ctrl.get_status()
        if status.get("status") == "running":
            focus = _record_huddle_progress_focus(
                actor="chris",
                action="Start Huddle Party Mode",
                detail="Huddle confirmed the overnight research lane is already running.",
                why_now="The native Huddle screen checked and reaffirmed the live overnight orchestration lane.",
                result_summary="Party mode was already running.",
                related_kind="party-mode",
                related_label="Overnight Orchestration",
            )
            return _ok(
                {
                    "status": "already_running",
                    "request_id": "",
                    "performed_action": "start_party_mode",
                    "boundary_decision": "allow",
                    "boundary_reason": "Party mode is already running.",
                    "trust_zone": "household_huddle",
                    "authority_stage": "sandbox_live",
                    "arena_status": "active",
                    "approval_mode": "stage_and_alert",
                    "focus": focus,
                }
            )
        request_id = str(uuid.uuid4())
        boundary = runtime.assess_action_boundary(
            zone_id="household_huddle",
            arena_id="household.huddle.workflow",
            action_type="huddle_workflow",
            requested_stage="sandbox_live",
        )
        boundary_decision = str(boundary.get("decision") or "stage")
        boundary_reason = str(boundary.get("reason") or "")
        trust_zone = str(boundary.get("trust_zone") or "household_huddle")
        authority_stage = str(boundary.get("authority_stage") or "stage_alert")
        approval_mode = str(boundary.get("approval_mode") or "stage_and_alert")
        arena_status = str(boundary.get("arena_status") or "active")

        if boundary_decision == "deny":
            return _ok(
                {
                    "request_id": request_id,
                    "status": "blocked_by_boundary",
                    "performed_action": "start_party_mode",
                    "boundary_decision": boundary_decision,
                    "boundary_reason": boundary_reason,
                    "trust_zone": trust_zone,
                    "authority_stage": authority_stage,
                    "arena_status": arena_status,
                    "approval_mode": approval_mode,
                }
            )

        if boundary_decision != "allow":
            from .models import StagedActionQueueItem

            runtime.trust_support.enqueue_stage_action(
                StagedActionQueueItem(
                    request_id=request_id,
                    arena_id="household.huddle.workflow",
                    action_type="huddle_start_party_mode_review",
                    status="awaiting_principal_review",
                    created_at=_ts(),
                    principal_id="chris",
                )
            )
            return _ok(
                {
                    "request_id": request_id,
                    "status": "staged_for_review",
                    "performed_action": "start_party_mode",
                    "boundary_decision": boundary_decision,
                    "boundary_reason": boundary_reason,
                    "trust_zone": trust_zone,
                    "authority_stage": authority_stage,
                    "arena_status": arena_status,
                    "approval_mode": approval_mode,
                }
            )

        await asyncio.to_thread(ctrl.start, True)
        focus = _record_huddle_progress_focus(
            actor="chris",
            action="Start Huddle Party Mode",
            detail="Huddle launched the overnight research cycle from the native alignment lane.",
            why_now="The iPhone Huddle screen started a real overnight orchestration loop and promoted that work into shared continuity.",
            result_summary="Party mode started from the phone Huddle lane.",
            related_kind="party-mode",
            related_label="Overnight Orchestration",
        )
        return _ok(
            {
                "request_id": request_id,
                "status": "started",
                "performed_action": "start_party_mode",
                "boundary_decision": boundary_decision,
                "boundary_reason": boundary_reason,
                "trust_zone": trust_zone,
                "authority_stage": authority_stage,
                "arena_status": arena_status,
                "approval_mode": approval_mode,
                "focus": focus,
            }
        )

    @app.post("/api/apple/huddle/approvals/{work_id}/approve")
    async def apple_huddle_approve(work_id: str, payload: dict[str, Any]):
        actor = str(payload.get("actor") or payload.get("actor_id") or "chris").strip() or "chris"
        note = str(payload.get("note") or "").strip()
        return _ok(_resolve_huddle_approval(work_id=work_id, action="approve", actor=actor, note=note))

    @app.post("/api/apple/huddle/approvals/{work_id}/reject")
    async def apple_huddle_reject(work_id: str, payload: dict[str, Any]):
        actor = str(payload.get("actor") or payload.get("actor_id") or "chris").strip() or "chris"
        note = str(payload.get("note") or "").strip()
        return _ok(_resolve_huddle_approval(work_id=work_id, action="reject", actor=actor, note=note))

    @app.post("/api/apple/huddle/ideas")
    async def apple_huddle_capture_idea(payload: dict[str, Any]):
        actor = str(payload.get("actor") or payload.get("actor_id") or "chris").strip() or "chris"
        text = str(payload.get("text") or "").strip()
        domain = str(payload.get("domain") or "passive-income").strip() or "passive-income"
        notes = str(payload.get("notes") or "").strip()
        try:
            return _ok(_capture_huddle_idea(text=text, actor=actor, domain=domain, notes=notes))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/apple/huddle/ideas/{idea_id}/queue")
    async def apple_huddle_queue_idea(idea_id: str, payload: dict[str, Any]):
        actor = str(payload.get("actor") or payload.get("actor_id") or "chris").strip() or "chris"
        try:
            return _ok(_queue_huddle_idea(idea_id=idea_id, actor=actor))
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/api/apple/huddle/ideas/{idea_id}/pass")
    async def apple_huddle_pass_idea(idea_id: str, payload: dict[str, Any]):
        actor = str(payload.get("actor") or payload.get("actor_id") or "chris").strip() or "chris"
        try:
            return _ok(_pass_huddle_idea(idea_id=idea_id, actor=actor))
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/api/apple/huddle/ideas/{idea_id}/research-now")
    async def apple_huddle_research_idea_now(idea_id: str, payload: dict[str, Any]):
        actor = str(payload.get("actor") or payload.get("actor_id") or "chris").strip() or "chris"
        try:
            return _ok(_research_huddle_idea_now(idea_id=idea_id, actor=actor))
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    # ── Forge 3-D models ──────────────────────────────────────────────────────

    _FORGE_DB = Path("data/forge/models.jsonl")

    def _load_forge_model_records() -> list[dict]:
        records: list[dict] = []
        if _FORGE_DB.exists():
            for line in _FORGE_DB.read_text().splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except Exception:
                    continue
        return list(reversed(records[-20:]))

    def _load_forge_queue_records() -> list[dict]:
        queue_path = Path("data/forge/queue.jsonl")
        queue_records: list[dict] = []
        if queue_path.exists():
            for line in queue_path.read_text().splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    queue_records.append(json.loads(line))
                except Exception:
                    continue
        return list(reversed(queue_records[-10:]))

    def _forge_missing_views(capture_session: dict | None) -> list[str]:
        if not isinstance(capture_session, dict):
            return []
        frames = capture_session.get("frames") or []
        seen = {
            str(frame.get("view_type", "")).strip().lower()
            for frame in frames
            if isinstance(frame, dict)
        }
        expected = ["front", "back", "left", "right", "top"]
        return [view for view in expected if view not in seen]

    def _forge_project_summary(project: dict) -> dict:
        capture_sessions = project.get("capture_sessions") or []
        latest_capture = capture_sessions[-1] if capture_sessions else {}
        confidence = latest_capture.get("confidence") if isinstance(latest_capture, dict) else {}
        generated_models = project.get("generated_models") or []
        latest_model = generated_models[-1] if generated_models else {}
        return {
            "id": str(project.get("id") or ""),
            "title": str(project.get("title") or "Untitled project"),
            "status": str(project.get("status") or "idea"),
            "intake_type": str(project.get("intake_type") or "file_upload"),
            "updated_at": str(project.get("updated_at") or project.get("created_at") or _ts()),
            "source_file_count": len(project.get("source_files") or []),
            "capture_frame_count": sum(
                len(session.get("frames") or [])
                for session in capture_sessions
                if isinstance(session, dict)
            ),
            "measurement_count": len(project.get("measurements") or []),
            "generated_model_count": len(generated_models),
            "approval_count": len(project.get("approvals") or []),
            "latest_capture_status": str(latest_capture.get("status") or "") or None,
            "print_readiness": str(confidence.get("print_readiness") or "") or None,
            "latest_model_name": str(latest_model.get("title") or latest_model.get("filename") or "") or None,
        }

    def _forge_project_detail(project: dict) -> dict:
        summary = _forge_project_summary(project)
        capture_sessions = project.get("capture_sessions") or []
        latest_capture = capture_sessions[-1] if capture_sessions else {}
        confidence = latest_capture.get("confidence") if isinstance(latest_capture, dict) else None
        generated_models = project.get("generated_models") or []
        return {
            **summary,
            "description": str(project.get("description") or ""),
            "notes": str(project.get("notes") or ""),
            "capture_confidence": confidence if isinstance(confidence, dict) else None,
            "missing_views": _forge_missing_views(latest_capture),
            "generated_models": [
                {
                    "model_id": str(model.get("model_id") or ""),
                    "title": str(model.get("title") or model.get("filename") or "Generated model"),
                    "format": str(model.get("format") or ""),
                    "created_at": str(model.get("created_at") or project.get("updated_at") or _ts()),
                    "source_image": model.get("source_image"),
                    "notes": str(model.get("notes") or ""),
                }
                for model in generated_models[-3:]
                if isinstance(model, dict)
            ],
        }

    @app.get("/api/apple/forge")
    async def apple_forge():
        """Return workshop, project, and photogrammetry state for the Forge tab."""
        try:
            records = _load_forge_model_records()
            queue_records = _load_forge_queue_records()

            project_details: list[dict] = []
            try:
                from .forge import ForgeStore

                store = ForgeStore()
                index = await asyncio.to_thread(store.list_projects, False)
                index = sorted(
                    index,
                    key=lambda item: str(item.get("updated_at") or item.get("created_at") or ""),
                    reverse=True,
                )
                for entry in index[:12]:
                    project_id = str(entry.get("id") or "")
                    if not project_id:
                        continue
                    project = await asyncio.to_thread(store.get_project, project_id)
                    if isinstance(project, dict):
                        project_details.append(project)
            except Exception:
                logger.exception("apple_forge project summary load failed")

            projects = [_forge_project_summary(project) for project in project_details]
            active_project = _forge_project_detail(project_details[0]) if project_details else None
            statuses = [str(project.get("status") or "") for project in project_details]
            summary = {
                "total_projects": len(project_details),
                "active_projects": sum(
                    1
                    for status in statuses
                    if status not in {"completed", "failed", "archived"}
                ),
                "capture_projects": sum(
                    1
                    for status in statuses
                    if status in {"reference_uploaded", "capture_in_progress", "needs_more_views", "needs_measurements"}
                ),
                "ready_models": sum(
                    1
                    for project in project_details
                    if (project.get("generated_models") or [])
                    or str(project.get("status") or "") in {"model_ready", "print_ready", "slice_ready", "approval_required", "sent_to_printer", "printing", "completed"}
                ),
                "approval_queue": sum(len(project.get("approvals") or []) for project in project_details),
                "queued_jobs": sum(1 for job in queue_records if str(job.get("status") or "") == "queued"),
            }
            recent_jobs = [
                {
                    "job_id": str(job.get("job_id") or ""),
                    "name": str(job.get("name") or "Model"),
                    "status": str(job.get("status") or "queued"),
                    "photo_count": int(job.get("photo_count") or 0),
                    "created_at": str(job.get("created_at") or _ts()),
                }
                for job in queue_records
                if isinstance(job, dict)
            ]
            return _ok(
                {
                    "summary": summary,
                    "active_project": active_project,
                    "projects": projects,
                    "models": records,
                    "recent_jobs": recent_jobs,
                    "continuity": _build_forge_continuity(
                        "chris",
                        active_project=active_project if isinstance(active_project, dict) else None,
                        projects=projects,
                        recent_jobs=recent_jobs,
                    ),
                }
            )
        except Exception as exc:
            logger.exception("apple_forge failed: %s", exc)
            return _ok(
                {
                    "summary": {
                        "total_projects": 0,
                        "active_projects": 0,
                        "capture_projects": 0,
                        "ready_models": 0,
                        "approval_queue": 0,
                        "queued_jobs": 0,
                    },
                    "active_project": None,
                    "projects": [],
                    "models": [],
                    "recent_jobs": [],
                    "continuity": {
                        "subject_display_name": "Chris",
                        "workshop_focus": "",
                        "active_workshop_lanes": [],
                        "queued_job_count": 0,
                        "profile_fact_count": 0,
                        "guidance_lines": [],
                        "recent_profile_facts": [],
                        "recent_first_light": [],
                    },
                }
            )

    @app.post("/api/apple/forge/projects")
    async def apple_forge_create_project(payload: dict):
        """Create a Forge workshop project from the phone."""
        title = str(payload.get("title") or "").strip()
        if not title:
            raise HTTPException(status_code=400, detail="title is required")
        description = str(payload.get("description") or "").strip()
        try:
            from .forge import ForgeStore

            store = ForgeStore()
            project = await asyncio.to_thread(
                store.create_project,
                title,
                description,
                "phone_capture",
            )
            return _ok(_forge_project_detail(project))
        except Exception as exc:
            logger.exception("apple_forge_create_project failed: %s", exc)
            raise HTTPException(status_code=500, detail="Failed to create Forge project") from exc

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


def _approval_target_summary(payload: dict[str, Any]) -> str:
    ordered_keys = (
        "entity_id",
        "recipient",
        "to",
        "location",
        "title",
        "event_title",
        "document_title",
        "filename",
        "path",
        "url",
        "target",
        "vendor",
    )
    parts: list[str] = []
    for key in ordered_keys:
        value = str(payload.get(key) or "").strip()
        if value:
            parts.append(value)
        if len(parts) >= 2:
            break
    return " · ".join(parts)


def _approval_context_lines(payload: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    field_pairs = [
        ("channel", "Channel"),
        ("service", "Service"),
        ("ha_service", "Action"),
        ("amount_usd", "Amount"),
        ("start", "Start"),
        ("end", "End"),
        ("location", "Location"),
        ("subject", "Subject"),
        ("body", "Body"),
        ("description", "Description"),
    ]
    for key, label in field_pairs:
        value = payload.get(key)
        if value in (None, "", [], {}):
            continue
        text = str(value).strip()
        if not text:
            continue
        if key == "amount_usd":
            try:
                text = f"${float(value):.2f}"
            except (TypeError, ValueError):
                text = str(value)
        if key in {"body", "description"}:
            text = _truncate(" ".join(text.split()), 88)
        lines.append(f"{label}: {text}")
        if len(lines) >= 3:
            break
    return lines


def _mock_home_state() -> dict:
    """Stub home state returned when HomeAssistant is not configured."""
    return {
        "present_members": [],
        "doors": {"front": "locked", "garage": "closed"},
        "temperature": {"inside": 70.0, "target": 72.0, "mode": "cool"},
        "lights_on": [],
        "alerts": [],
        "home_ops": _build_home_ops_summary(),
        "source": "mock",
    }
