#!/usr/bin/env python3
"""
Fetch live /api/apple payloads and validate they decode through JarvisKit.

Usage examples:

  python3 scripts/verify_apple_contracts.py --base-url http://127.0.0.1:8787

  python3 scripts/verify_apple_contracts.py \
    --ssh-host root@5.78.212.15 \
    --container jarvis-family-jarvis-1
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

REPO_ROOT = Path(__file__).resolve().parents[1]
JARVIS_APPLE_DIR = REPO_ROOT / "JarvisApple"

ENDPOINTS: list[tuple[str, str]] = [
    ("/api/apple/status", "/api/apple/status"),
    ("/api/apple/app-state", "/api/apple/app-state"),
    ("/api/apple/voice/greeting?actor=chris", "/api/apple/voice/greeting?actor=chris"),
    ("/api/apple/voice/state?actor=chris&conversation_id=", "/api/apple/voice/state?actor=chris&conversation_id="),
    ("/api/apple/calendar/state", "/api/apple/calendar/state"),
    ("/api/apple/reminders/state", "/api/apple/reminders/state"),
    ("/api/apple/focus-state", "/api/apple/focus-state"),
    ("/api/apple/sound-alerts", "/api/apple/sound-alerts"),
    ("/api/apple/vision/scans", "/api/apple/vision/scans"),
    ("/api/apple/now-playing/state", "/api/apple/now-playing/state"),
    ("/api/apple/control-plane/state", "/api/apple/control-plane/state"),
    ("/api/apple/systems/admin-summary", "/api/apple/systems/admin-summary"),
    ("/api/apple/notifications", "/api/apple/notifications"),
    ("/api/apple/events/recent", "/api/apple/events/recent"),
    ("/api/apple/weather", "/api/apple/weather"),
    ("/api/apple/navigation/locations", "/api/apple/navigation/locations"),
    ("/api/apple/navigation/state", "/api/apple/navigation/state"),
    (
        "/api/apple/navigation/route?origin=8384%20Riley%20Rd%2C%20Alexandria%2C%20KY%2041001&destination=Cincinnati%2C%20OH",
        "/api/apple/navigation/route?origin=8384%20Riley%20Rd%2C%20Alexandria%2C%20KY%2041001&destination=Cincinnati%2C%20OH",
    ),
    (
        "/api/apple/navigation/stops?origin=8384%20Riley%20Rd%2C%20Alexandria%2C%20KY%2041001&destination=Cincinnati%2C%20OH&parks_radius_miles=25",
        "/api/apple/navigation/stops?origin=8384%20Riley%20Rd%2C%20Alexandria%2C%20KY%2041001&destination=Cincinnati%2C%20OH&parks_radius_miles=25",
    ),
    ("/api/apple/briefing?actor=chris", "/api/apple/briefing?actor=chris"),
    ("/api/apple/while-you-were-away?actor=chris", "/api/apple/while-you-were-away?actor=chris"),
    ("/api/apple/needs", "/api/apple/needs"),
    ("/api/apple/health/summary?actor=chris", "/api/apple/health/summary?actor=chris"),
    ("/api/apple/home/state", "/api/apple/home/state"),
    ("/api/apple/catalyst", "/api/apple/catalyst"),
    ("/api/apple/chronicle", "/api/apple/chronicle"),
    ("/api/apple/faith?actor=chris", "/api/apple/faith?actor=chris"),
    ("/api/apple/publishing", "/api/apple/publishing"),
    ("/api/apple/huddle", "/api/apple/huddle"),
    ("/api/apple/forge", "/api/apple/forge"),
    ("/api/apple/notifications/pending", "/api/apple/notifications/pending"),
]

ACTION_ENDPOINTS: list[tuple[str, str, dict]] = [
    ("/api/apple/speak", "/api/apple/speak", {"text": "Status check", "actor_id": "chris"}),
    ("/api/apple/device/register", "/api/apple/device/register", {"actor_id": "chris", "token": "test-token", "platform": "ios"}),
    ("/api/apple/home/command", "/api/apple/home/command", {"command": "turn_on", "entity_id": "light.office", "service": "light"}),
    ("/api/apple/presence", "/api/apple/presence", {"actor_id": "chris", "event": "arrived_home", "lat": 38.96, "lon": -84.39}),
    ("/api/apple/approvals/req-1/approve", "/api/apple/approvals/req-1/approve", {"approved_by": "chris"}),
    ("/api/apple/approvals/req-1/reject", "/api/apple/approvals/req-1/reject", {"reason": "Not now", "rejected_by": "chris"}),
    ("/api/apple/approvals/req-1/cancel", "/api/apple/approvals/req-1/cancel", {}),
    ("/api/apple/calendar", "/api/apple/calendar", {"events": []}),
    ("/api/apple/calendar/stage-prep", "/api/apple/calendar/stage-prep", {"title": "Planning", "start": "2026-06-01T09:00:00Z", "location": "Office"}),
    ("/api/apple/calendar/events/cal-1/prepare", "/api/apple/calendar/events/cal-1/prepare", {}),
    ("/api/apple/calendar/events/cal-1/route", "/api/apple/calendar/events/cal-1/route", {}),
    ("/api/apple/reminders", "/api/apple/reminders", {"reminders": []}),
    ("/api/apple/reminders/r1/complete", "/api/apple/reminders/r1/complete", {}),
    ("/api/apple/reminders/r1/snooze", "/api/apple/reminders/r1/snooze", {"minutes": 30}),
    ("/api/apple/focus", "/api/apple/focus", {"actor_id": "chris", "focus_active": True, "source": "device"}),
    ("/api/apple/sound-alert", "/api/apple/sound-alert", {"actor_id": "chris", "classification": "doorbell", "detail": "Front door chime", "confidence": 0.98}),
    ("/api/apple/sound-alerts/sa-1/resolve", "/api/apple/sound-alerts/sa-1/resolve", {}),
    ("/api/apple/vision/scan", "/api/apple/vision/scan", {"actor_id": "chris", "context": "porch", "source": "front_cam", "text": "Package at door"}),
    ("/api/apple/vision/scans/vs-1/resolve", "/api/apple/vision/scans/vs-1/resolve", {}),
    ("/api/apple/now-playing", "/api/apple/now-playing", {"title": "Ambient Focus", "artist": "JARVIS", "album": "Morning Loop", "is_playing": True}),
    ("/api/apple/speak/push", "/api/apple/speak/push", {"text": "Heads up", "actor": "chris"}),
    ("/api/apple/health/log", "/api/apple/health/log", {"actor_id": "chris", "samples": [{"type": "steps", "value": 1200, "date": "2026-06-01T08:00:00Z", "source": "iPhone"}]}),
    ("/api/apple/chronicle/capture", "/api/apple/chronicle/capture", {"type": "reflection", "note": "Quick capture", "actor_id": "chris"}),
    ("/api/apple/chronicle/prayers/cp-1/pray", "/api/apple/chronicle/prayers/cp-1/pray", {"actor_id": "chris", "note": "Covered this before the meeting."}),
    ("/api/apple/chronicle/prayers/cp-1/answer", "/api/apple/chronicle/prayers/cp-1/answer", {"actor_id": "chris", "note": "God gave clarity before the day started."}),
    ("/api/apple/chronicle/study/save", "/api/apple/chronicle/study/save", {"actor_id": "chris", "title": "Bible Study - Proverbs 3", "passage": "Proverbs 3", "notes": "Trusting God over my own pace today."}),
    ("/api/apple/faith/chat", "/api/apple/faith/chat", {"agent_id": "ezra", "passage": "Philippians 4:6-7", "messages": [{"role": "user", "content": "Help me pray through this."}]}),
    ("/api/apple/stewardship-lanes/family-stewardship/stage-review", "/api/apple/stewardship-lanes/family-stewardship/stage-review", {"actor": "chris", "note": "Bring this back in the next household review."}),
    ("/api/apple/stewardship-reviews/stewardship-review-1/approve", "/api/apple/stewardship-reviews/stewardship-review-1/approve", {"actor": "chris"}),
    ("/api/apple/stewardship-reviews/stewardship-review-1/route", "/api/apple/stewardship-reviews/stewardship-review-1/route", {"actor": "chris", "review_surface": "brief", "packet_target": "executive"}),
    ("/api/apple/stewardship-reviews/stewardship-review-1/retire", "/api/apple/stewardship-reviews/stewardship-review-1/retire", {"actor": "chris", "reason": "Family Stewardship was retired from Systems/Admin."}),
    ("/api/apple/governance-proposals/governance-family-stewardship/promote", "/api/apple/governance-proposals/governance-family-stewardship/promote", {"actor": "chris", "basis": "Promoted from Systems/Admin."}),
    ("/api/apple/governance-proposals/governance-family-stewardship/dismiss", "/api/apple/governance-proposals/governance-family-stewardship/dismiss", {"actor": "chris", "reason": "Dismissed from Systems/Admin."}),
    ("/api/apple/publishing/reviews/rev-1/approve", "/api/apple/publishing/reviews/rev-1/approve", {}),
    ("/api/apple/publishing/reviews/rev-1/revise", "/api/apple/publishing/reviews/rev-1/revise", {"feedback": "Please tighten section two."}),
    ("/api/apple/huddle/party-mode/start", "/api/apple/huddle/party-mode/start", {}),
    ("/api/apple/forge/projects", "/api/apple/forge/projects", {"title": "Desk Scan", "description": "Bracket concept from phone capture"}),
    ("/api/apple/forge/save", "/api/apple/forge/save", {"id": "fm-1", "name": "Desk Scan", "photo_count": 12, "created_at": "2026-06-01T08:00:00Z", "usdz_path": "/models/desk.usdz"}),
    ("/api/apple/forge/submit", "/api/apple/forge/submit", {"name": "Desk Scan", "photos": [{"index": 0, "filename": "desk.jpg", "data": "aGVsbG8="}]}),
    ("/api/apple/systems/trust-zones/shared-email.stage/promote", "/api/apple/systems/trust-zones/shared-email.stage/promote", {"actor": "chris", "basis": "manual promotion from tests"}),
    ("/api/apple/systems/trust-zones/shared-email.stage/demote", "/api/apple/systems/trust-zones/shared-email.stage/demote", {"actor": "chris", "reason": "manual demotion from tests"}),
    ("/api/apple/systems/resource-arenas/gmail.shared.drafts/suspend", "/api/apple/systems/resource-arenas/gmail.shared.drafts/suspend", {"actor": "chris", "reason": "manual suspension from tests"}),
    ("/api/apple/systems/resource-arenas/gmail.shared.drafts/resume", "/api/apple/systems/resource-arenas/gmail.shared.drafts/resume", {"actor": "chris", "reason": "manual resume from tests"}),
    ("/api/apple/systems/self-improvement/jobs/sj-1/sandbox-execute", "/api/apple/systems/self-improvement/jobs/sj-1/sandbox-execute", {"actor": "chris", "triggered_by": "tests"}),
    ("/api/apple/systems/self-improvement/jobs/sj-1/sandbox-cancel", "/api/apple/systems/self-improvement/jobs/sj-1/sandbox-cancel", {"actor": "chris", "reason": "tests requested stop"}),
    ("/api/apple/systems/self-improvement/jobs/sj-1/sandbox-recover", "/api/apple/systems/self-improvement/jobs/sj-1/sandbox-recover", {"actor": "chris", "reason": "tests reset the lane"}),
    ("/api/apple/systems/self-improvement/jobs/vendor-prep:vp-1/sandbox-execute", "/api/apple/systems/self-improvement/jobs/vendor-prep:vp-1/sandbox-execute", {"actor": "chris", "triggered_by": "tests"}),
    ("/api/apple/systems/self-improvement/jobs/vendor-prep:vp-1/sandbox-cancel", "/api/apple/systems/self-improvement/jobs/vendor-prep:vp-1/sandbox-cancel", {"actor": "chris", "reason": "tests requested stop"}),
    ("/api/apple/systems/self-improvement/jobs/vendor-prep:vp-1/sandbox-recover", "/api/apple/systems/self-improvement/jobs/vendor-prep:vp-1/sandbox-recover", {"actor": "chris", "reason": "tests reset the lane"}),
    ("/api/apple/systems/self-improvement/jobs/stewardship-review:stewardship-review-1/sandbox-execute", "/api/apple/systems/self-improvement/jobs/stewardship-review:stewardship-review-1/sandbox-execute", {"actor": "chris", "triggered_by": "tests"}),
    ("/api/apple/systems/self-improvement/jobs/stewardship-review:stewardship-review-1/sandbox-cancel", "/api/apple/systems/self-improvement/jobs/stewardship-review:stewardship-review-1/sandbox-cancel", {"actor": "chris", "reason": "tests requested stop"}),
    ("/api/apple/systems/self-improvement/jobs/stewardship-review:stewardship-review-1/sandbox-recover", "/api/apple/systems/self-improvement/jobs/stewardship-review:stewardship-review-1/sandbox-recover", {"actor": "chris", "reason": "tests reset the lane"}),
    ("/api/apple/notifications/n1/seen", "/api/apple/notifications/n1/seen", {}),
    ("/api/apple/notifications/n1/dismiss", "/api/apple/notifications/n1/dismiss", {}),
    ("/api/apple/notifications/n1/resolve", "/api/apple/notifications/n1/resolve", {}),
    ("/api/apple/notifications/n1/snooze", "/api/apple/notifications/n1/snooze", {}),
    ("/api/apple/notifications/n1/action", "/api/apple/notifications/n1/action", {"action": "open"}),
]


def require_mapping(payloads: dict[str, dict], path: str) -> dict:
    try:
        payload = payloads[path]
    except KeyError as exc:
        raise RuntimeError(f"missing payload for {path}") from exc
    data = payload.get("data")
    if not isinstance(data, dict):
        raise RuntimeError(f"{path} returned non-object data payload")
    return data


def require_data(payloads: dict[str, dict], path: str):
    try:
        payload = payloads[path]
    except KeyError as exc:
        raise RuntimeError(f"missing payload for {path}") from exc
    if "data" not in payload:
        raise RuntimeError(f"{path} missing 'data' field")
    return payload["data"]


def require_list(data: dict, path: str, field: str) -> list:
    value = data.get(field)
    if not isinstance(value, list):
        raise RuntimeError(f"{path} missing list field '{field}'")
    return value


def require_bool(data: dict, path: str, field: str) -> bool:
    value = data.get(field)
    if not isinstance(value, bool):
        raise RuntimeError(f"{path} missing bool field '{field}'")
    return value


def verify_while_you_were_away(packet: object, prefix: str) -> None:
    if not isinstance(packet, dict):
        raise RuntimeError(f"{prefix} is not an object")
    for key in (
        "headline",
        "summary",
        "window_hours",
        "generated_at",
        "stewardship_lanes",
        "lane_reports",
        "quiet_completions",
        "blocked_work",
        "prepared_work",
        "decision_cards",
        "drift_signals",
        "recommendation",
    ):
        if key not in packet:
            raise RuntimeError(f"{prefix} missing '{key}'")
    recommendation = packet.get("recommendation")
    if not isinstance(recommendation, dict):
        raise RuntimeError(f"{prefix} recommendation is not an object")
    for key in ("title", "summary", "action"):
        if key not in recommendation:
            raise RuntimeError(f"{prefix} recommendation missing '{key}'")
    for field_name in (
        "stewardship_lanes",
        "lane_reports",
        "quiet_completions",
        "blocked_work",
        "prepared_work",
        "decision_cards",
        "drift_signals",
    ):
        if not isinstance(packet.get(field_name), list):
            raise RuntimeError(f"{prefix} {field_name} is not a list")
    for index, item in enumerate((packet.get("lane_reports") or [])[:4]):
        if not isinstance(item, dict):
            raise RuntimeError(f"{prefix} lane_reports[{index}] is not an object")
        for key in ("id", "title", "summary"):
            if key not in item:
                raise RuntimeError(f"{prefix} lane_reports[{index}] missing '{key}'")
    for index, item in enumerate((packet.get("stewardship_lanes") or [])[:4]):
        if not isinstance(item, dict):
            raise RuntimeError(f"{prefix} stewardship_lanes[{index}] is not an object")
        for key in ("id", "title", "summary", "report_summaries", "prepared_work", "decision_cards", "drift_cards", "quiet_completions", "blocked_work"):
            if key not in item:
                raise RuntimeError(f"{prefix} stewardship_lanes[{index}] missing '{key}'")
        primitive = item.get("execution_primitive")
        if not isinstance(primitive, dict):
            raise RuntimeError(f"{prefix} stewardship_lanes[{index}] execution_primitive is not an object")
        for key in (
            "packet_target",
            "review_surface",
            "navigation_target",
            "action_label",
            "action_detail",
            "route_summary",
            "lane_status",
            "trust_zone",
            "authority_stage",
            "arena_status",
            "approval_mode",
            "boundary_decision",
            "boundary_reason",
        ):
            if key not in primitive:
                raise RuntimeError(f"{prefix} stewardship_lanes[{index}] execution_primitive missing '{key}'")
        for collection_name in ("report_summaries", "prepared_work", "decision_cards", "drift_cards", "quiet_completions", "blocked_work"):
            if not isinstance(item.get(collection_name), list):
                raise RuntimeError(f"{prefix} stewardship_lanes[{index}] {collection_name} is not a list")
            for row_index, row in enumerate((item.get(collection_name) or [])[:3]):
                if not isinstance(row, dict):
                    raise RuntimeError(f"{prefix} stewardship_lanes[{index}] {collection_name}[{row_index}] is not an object")
                for key in ("id", "lane", "agent", "title", "summary", "timestamp", "status"):
                    if key not in row:
                        raise RuntimeError(f"{prefix} stewardship_lanes[{index}] {collection_name}[{row_index}] missing '{key}'")
    for collection_name in ("quiet_completions", "blocked_work", "prepared_work", "decision_cards", "drift_signals"):
        for index, item in enumerate((packet.get(collection_name) or [])[:4]):
            if not isinstance(item, dict):
                raise RuntimeError(f"{prefix} {collection_name}[{index}] is not an object")
            for key in ("id", "lane", "agent", "title", "summary", "timestamp", "status"):
                if key not in item:
                    raise RuntimeError(f"{prefix} {collection_name}[{index}] missing '{key}'")


def validate_phase_one_contracts(payloads: dict[str, dict]) -> None:
    greeting = require_mapping(payloads, "/api/apple/voice/greeting?actor=chris")
    for key in ("greeting", "mode"):
        if key not in greeting:
            raise RuntimeError(f"/api/apple/voice/greeting?actor=chris missing '{key}'")

    voice_state = require_mapping(payloads, "/api/apple/voice/state?actor=chris&conversation_id=")
    for key in ("conversation", "recent_conversations", "memory_overview", "voice_stack", "quick_commands"):
        if key not in voice_state:
            raise RuntimeError(f"/api/apple/voice/state?actor=chris&conversation_id= missing '{key}'")
    voice_memory = voice_state.get("memory_overview")
    if not isinstance(voice_memory, dict):
        raise RuntimeError("/api/apple/voice/state?actor=chris&conversation_id= memory_overview is not an object")
    for key in ("profile_fact_count", "pending_proposals", "preferred_voice", "briefing_style", "guidance_lines", "recent_profile_facts", "recent_first_light", "long_horizon_lines", "active_threads"):
        if key not in voice_memory:
            raise RuntimeError(f"/api/apple/voice/state?actor=chris&conversation_id= memory_overview missing '{key}'")
    for field_name in ("guidance_lines", "recent_profile_facts", "recent_first_light", "long_horizon_lines", "active_threads"):
        if not isinstance(voice_memory.get(field_name), list):
            raise RuntimeError(f"/api/apple/voice/state?actor=chris&conversation_id= memory_overview {field_name} is not a list")
    for index, item in enumerate((voice_memory.get("recent_profile_facts") or [])[:4]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/voice/state?actor=chris&conversation_id= memory_overview recent_profile_facts[{index}] is not an object")
        for key in ("id", "title", "summary"):
            if key not in item:
                raise RuntimeError(f"/api/apple/voice/state?actor=chris&conversation_id= memory_overview recent_profile_facts[{index}] missing '{key}'")
    for index, item in enumerate((voice_memory.get("recent_first_light") or [])[:4]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/voice/state?actor=chris&conversation_id= memory_overview recent_first_light[{index}] is not an object")
        for key in ("id", "label", "summary"):
            if key not in item:
                raise RuntimeError(f"/api/apple/voice/state?actor=chris&conversation_id= memory_overview recent_first_light[{index}] missing '{key}'")

    briefing = require_mapping(payloads, "/api/apple/briefing?actor=chris")
    continuity = briefing.get("continuity")
    if not isinstance(continuity, dict):
        raise RuntimeError("/api/apple/briefing?actor=chris continuity is not an object")
    for key in ("subject_display_name", "preferred_tone", "briefing_style", "profile_fact_count", "pending_proposal_count", "first_light_history_count", "guidance_lines", "recent_profile_facts", "recent_first_light", "long_horizon_lines", "active_threads"):
        if key not in continuity:
            raise RuntimeError(f"/api/apple/briefing?actor=chris continuity missing '{key}'")
    for field_name in ("guidance_lines", "recent_profile_facts", "recent_first_light", "long_horizon_lines", "active_threads"):
        if not isinstance(continuity.get(field_name), list):
            raise RuntimeError(f"/api/apple/briefing?actor=chris continuity {field_name} is not a list")
    recent_profile_facts = continuity.get("recent_profile_facts")
    if not isinstance(recent_profile_facts, list):
        raise RuntimeError("/api/apple/briefing?actor=chris continuity recent_profile_facts is not a list")
    for index, item in enumerate(recent_profile_facts[:4]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/briefing?actor=chris continuity recent_profile_facts[{index}] is not an object")
        for key in ("id", "title", "summary"):
            if key not in item:
                raise RuntimeError(f"/api/apple/briefing?actor=chris continuity recent_profile_facts[{index}] missing '{key}'")
    recent_first_light = continuity.get("recent_first_light")
    if not isinstance(recent_first_light, list):
        raise RuntimeError("/api/apple/briefing?actor=chris continuity recent_first_light is not a list")
    for index, item in enumerate(recent_first_light[:4]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/briefing?actor=chris continuity recent_first_light[{index}] is not an object")
        for key in ("id", "label", "summary"):
            if key not in item:
                raise RuntimeError(f"/api/apple/briefing?actor=chris continuity recent_first_light[{index}] missing '{key}'")
    command_items = require_list(briefing, "/api/apple/briefing?actor=chris", "command_items")
    for index, item in enumerate(command_items):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/briefing?actor=chris command_items[{index}] is not an object")
        for key in ("id", "title", "detail", "priority", "kind"):
            if key not in item:
                raise RuntimeError(f"/api/apple/briefing?actor=chris command_items[{index}] missing '{key}'")
    verify_while_you_were_away(briefing.get("while_you_were_away"), "/api/apple/briefing?actor=chris while_you_were_away")

    while_away_endpoint = require_mapping(payloads, "/api/apple/while-you-were-away?actor=chris")
    verify_while_you_were_away(while_away_endpoint, "/api/apple/while-you-were-away?actor=chris")

    home_state = require_mapping(payloads, "/api/apple/home/state")
    action_items = require_list(home_state, "/api/apple/home/state", "action_items")
    home_context = home_state.get("home_context")
    if not isinstance(home_context, dict):
        raise RuntimeError("/api/apple/home/state missing object field 'home_context'")
    for key in ("agenda", "attention", "projects"):
        if key not in home_context:
            raise RuntimeError(f"/api/apple/home/state home_context missing '{key}'")
    home_ops = home_state.get("home_ops")
    if not isinstance(home_ops, dict):
        raise RuntimeError("/api/apple/home/state missing object field 'home_ops'")
    for key in ("email", "tasks", "calendar", "projects", "sync"):
        if key not in home_ops:
            raise RuntimeError(f"/api/apple/home/state home_ops missing '{key}'")
    continuity = home_state.get("continuity")
    if not isinstance(continuity, dict):
        raise RuntimeError("/api/apple/home/state missing object field 'continuity'")
    for key in ("subject_display_name", "morning_room", "active_mode", "primary_rooms", "guidance_lines", "profile_fact_count", "recent_profile_facts", "recent_first_light", "long_horizon_lines", "active_threads"):
        if key not in continuity:
            raise RuntimeError(f"/api/apple/home/state continuity missing '{key}'")
    for field_name in ("primary_rooms", "guidance_lines", "recent_profile_facts", "recent_first_light", "long_horizon_lines", "active_threads"):
        if not isinstance(continuity.get(field_name), list):
            raise RuntimeError(f"/api/apple/home/state continuity {field_name} is not a list")
    for index, item in enumerate((continuity.get("recent_profile_facts") or [])[:4]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/home/state continuity recent_profile_facts[{index}] is not an object")
        for key in ("id", "title", "summary"):
            if key not in item:
                raise RuntimeError(f"/api/apple/home/state continuity recent_profile_facts[{index}] missing '{key}'")
    for index, item in enumerate((continuity.get("recent_first_light") or [])[:4]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/home/state continuity recent_first_light[{index}] is not an object")
        for key in ("id", "label", "summary"):
            if key not in item:
                raise RuntimeError(f"/api/apple/home/state continuity recent_first_light[{index}] missing '{key}'")
    verify_while_you_were_away(home_state.get("while_you_were_away"), "/api/apple/home/state while_you_were_away")
    for index, item in enumerate(action_items):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/home/state action_items[{index}] is not an object")
        for key in ("id", "title", "detail", "command", "service", "emphasis"):
            if key not in item:
                raise RuntimeError(f"/api/apple/home/state action_items[{index}] missing '{key}'")

    catalyst = require_mapping(payloads, "/api/apple/catalyst")
    for key in ("active_work", "signals", "portfolio", "lanes", "connectors", "workflow_counts", "live_workspace", "latest_runs", "continuity"):
        if key not in catalyst:
            raise RuntimeError(f"/api/apple/catalyst missing '{key}'")
    continuity = catalyst.get("continuity")
    if not isinstance(continuity, dict):
        raise RuntimeError("/api/apple/catalyst continuity is not an object")
    for key in ("subject_display_name", "briefing_style", "active_domains", "guidance_lines", "profile_fact_count", "hottest_workflow", "recent_profile_facts", "recent_first_light"):
        if key not in continuity:
            raise RuntimeError(f"/api/apple/catalyst continuity missing '{key}'")
    for field_name in ("active_domains", "guidance_lines", "recent_profile_facts", "recent_first_light"):
        if not isinstance(continuity.get(field_name), list):
            raise RuntimeError(f"/api/apple/catalyst continuity {field_name} is not a list")
    for index, item in enumerate((continuity.get("recent_profile_facts") or [])[:4]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/catalyst continuity recent_profile_facts[{index}] is not an object")
        for key in ("id", "title", "summary"):
            if key not in item:
                raise RuntimeError(f"/api/apple/catalyst continuity recent_profile_facts[{index}] missing '{key}'")
    for index, item in enumerate((continuity.get("recent_first_light") or [])[:4]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/catalyst continuity recent_first_light[{index}] is not an object")
        for key in ("id", "label", "summary"):
            if key not in item:
                raise RuntimeError(f"/api/apple/catalyst continuity recent_first_light[{index}] missing '{key}'")

    faith = require_mapping(payloads, "/api/apple/faith?actor=chris")
    for key in ("daily_word", "morning_context", "agents", "formation_prompts", "continuity", "updated_at"):
        if key not in faith:
            raise RuntimeError(f"/api/apple/faith?actor=chris missing '{key}'")
    agents = faith.get("agents")
    if not isinstance(agents, list):
        raise RuntimeError("/api/apple/faith?actor=chris agents is not a list")
    for index, item in enumerate(agents[:3]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/faith?actor=chris agents[{index}] is not an object")
        for key in ("id", "name", "title", "domain", "color", "initials", "description"):
            if key not in item:
                raise RuntimeError(f"/api/apple/faith?actor=chris agents[{index}] missing '{key}'")
    prompts = faith.get("formation_prompts")
    if not isinstance(prompts, list):
        raise RuntimeError("/api/apple/faith?actor=chris formation_prompts is not a list")
    continuity = faith.get("continuity")
    if not isinstance(continuity, dict):
        raise RuntimeError("/api/apple/faith?actor=chris continuity is not an object")
    for key in (
        "subject_display_name",
        "theme",
        "focus",
        "passage",
        "council_domains",
        "guidance_lines",
        "profile_fact_count",
        "recent_profile_facts",
        "recent_first_light",
    ):
        if key not in continuity:
            raise RuntimeError(f"/api/apple/faith?actor=chris continuity missing '{key}'")
    if not isinstance(continuity.get("council_domains"), list):
        raise RuntimeError("/api/apple/faith?actor=chris continuity council_domains is not a list")
    if not isinstance(continuity.get("guidance_lines"), list):
        raise RuntimeError("/api/apple/faith?actor=chris continuity guidance_lines is not a list")
    recent_profile_facts = continuity.get("recent_profile_facts")
    if not isinstance(recent_profile_facts, list):
        raise RuntimeError("/api/apple/faith?actor=chris continuity recent_profile_facts is not a list")
    for index, fact in enumerate(recent_profile_facts[:4]):
        if not isinstance(fact, dict):
            raise RuntimeError(f"/api/apple/faith?actor=chris continuity recent_profile_facts[{index}] is not an object")
        for key in ("id", "title", "summary"):
            if key not in fact:
                raise RuntimeError(f"/api/apple/faith?actor=chris continuity recent_profile_facts[{index}] missing '{key}'")
    recent_first_light = continuity.get("recent_first_light")
    if not isinstance(recent_first_light, list):
        raise RuntimeError("/api/apple/faith?actor=chris continuity recent_first_light is not a list")
    for index, moment in enumerate(recent_first_light[:4]):
        if not isinstance(moment, dict):
            raise RuntimeError(f"/api/apple/faith?actor=chris continuity recent_first_light[{index}] is not an object")
        for key in ("id", "label", "summary"):
            if key not in moment:
                raise RuntimeError(f"/api/apple/faith?actor=chris continuity recent_first_light[{index}] missing '{key}'")

    forge = require_mapping(payloads, "/api/apple/forge")
    for key in ("summary", "projects", "models", "recent_jobs", "continuity"):
        if key not in forge:
            raise RuntimeError(f"/api/apple/forge missing '{key}'")
    summary = forge.get("summary")
    if not isinstance(summary, dict):
        raise RuntimeError("/api/apple/forge summary is not an object")
    for key in ("total_projects", "active_projects", "capture_projects", "ready_models", "approval_queue", "queued_jobs"):
        if key not in summary:
            raise RuntimeError(f"/api/apple/forge summary missing '{key}'")
    projects = forge.get("projects")
    if not isinstance(projects, list):
        raise RuntimeError("/api/apple/forge projects is not a list")
    for index, item in enumerate(projects[:3]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/forge projects[{index}] is not an object")
        for key in ("id", "title", "status", "intake_type", "updated_at", "source_file_count", "capture_frame_count", "generated_model_count"):
            if key not in item:
                raise RuntimeError(f"/api/apple/forge projects[{index}] missing '{key}'")
    active_project = forge.get("active_project")
    if active_project is not None:
        if not isinstance(active_project, dict):
            raise RuntimeError("/api/apple/forge active_project is not an object")
        for key in ("id", "title", "status", "capture_confidence", "generated_models", "missing_views"):
            if key not in active_project:
                raise RuntimeError(f"/api/apple/forge active_project missing '{key}'")
    continuity = forge.get("continuity")
    if not isinstance(continuity, dict):
        raise RuntimeError("/api/apple/forge continuity is not an object")
    for key in (
        "subject_display_name",
        "workshop_focus",
        "active_workshop_lanes",
        "queued_job_count",
        "profile_fact_count",
        "guidance_lines",
        "recent_profile_facts",
        "recent_first_light",
    ):
        if key not in continuity:
            raise RuntimeError(f"/api/apple/forge continuity missing '{key}'")
    if not isinstance(continuity.get("active_workshop_lanes"), list):
        raise RuntimeError("/api/apple/forge continuity active_workshop_lanes is not a list")
    if not isinstance(continuity.get("guidance_lines"), list):
        raise RuntimeError("/api/apple/forge continuity guidance_lines is not a list")
    recent_profile_facts = continuity.get("recent_profile_facts")
    if not isinstance(recent_profile_facts, list):
        raise RuntimeError("/api/apple/forge continuity recent_profile_facts is not a list")
    for index, fact in enumerate(recent_profile_facts[:4]):
        if not isinstance(fact, dict):
            raise RuntimeError(f"/api/apple/forge continuity recent_profile_facts[{index}] is not an object")
        for key in ("id", "title", "summary"):
            if key not in fact:
                raise RuntimeError(f"/api/apple/forge continuity recent_profile_facts[{index}] missing '{key}'")
    recent_first_light = continuity.get("recent_first_light")
    if not isinstance(recent_first_light, list):
        raise RuntimeError("/api/apple/forge continuity recent_first_light is not a list")
    for index, moment in enumerate(recent_first_light[:4]):
        if not isinstance(moment, dict):
            raise RuntimeError(f"/api/apple/forge continuity recent_first_light[{index}] is not an object")
        for key in ("id", "label", "summary"):
            if key not in moment:
                raise RuntimeError(f"/api/apple/forge continuity recent_first_light[{index}] missing '{key}'")

    app_state = require_mapping(payloads, "/api/apple/app-state")
    for key in (
        "server",
        "calendar",
        "reminders",
        "focus",
        "notifications",
        "now_playing",
        "sound_alert",
        "vision_scan",
        "presence",
        "sync_health",
    ):
        if key not in app_state:
            raise RuntimeError(f"/api/apple/app-state missing '{key}'")
    calendar = app_state.get("calendar")
    if not isinstance(calendar, dict):
        raise RuntimeError("/api/apple/app-state calendar is not an object")
    next_items = calendar.get("next_items")
    if not isinstance(next_items, list):
        raise RuntimeError("/api/apple/app-state calendar missing list field 'next_items'")
    for index, item in enumerate(next_items[:3]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/app-state calendar next_items[{index}] is not an object")
        for key in ("title", "start", "end", "location", "calendar"):
            if key not in item:
                raise RuntimeError(f"/api/apple/app-state calendar next_items[{index}] missing '{key}'")

    calendar_state = require_mapping(payloads, "/api/apple/calendar/state")
    for key in ("synced", "synced_at", "count", "next_events", "today_events", "route_sensitive_events", "preparation_cues", "attention_flags"):
        if key not in calendar_state:
            raise RuntimeError(f"/api/apple/calendar/state missing '{key}'")
    for field in ("next_events", "today_events", "route_sensitive_events"):
        events = calendar_state.get(field)
        if not isinstance(events, list):
            raise RuntimeError(f"/api/apple/calendar/state {field} is not a list")
        for index, item in enumerate(events[:3]):
            if not isinstance(item, dict):
                raise RuntimeError(f"/api/apple/calendar/state {field}[{index}] is not an object")
            for key in ("id", "title", "start", "end", "location", "calendar", "notes", "url", "all_day", "prep_window_open", "route_ready"):
                if key not in item:
                    raise RuntimeError(f"/api/apple/calendar/state {field}[{index}] missing '{key}'")
    cues = calendar_state.get("preparation_cues")
    if not isinstance(cues, list):
        raise RuntimeError("/api/apple/calendar/state preparation_cues is not a list")
    for index, item in enumerate(cues[:3]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/calendar/state preparation_cues[{index}] is not an object")
        for key in ("event_id", "title", "detail", "action", "start", "location"):
            if key not in item:
                raise RuntimeError(f"/api/apple/calendar/state preparation_cues[{index}] missing '{key}'")
    flags = calendar_state.get("attention_flags")
    if not isinstance(flags, list):
        raise RuntimeError("/api/apple/calendar/state attention_flags is not a list")
    for index, item in enumerate(flags[:3]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/calendar/state attention_flags[{index}] is not an object")
        for key in ("id", "event_id", "kind", "severity", "title", "detail"):
            if key not in item:
                raise RuntimeError(f"/api/apple/calendar/state attention_flags[{index}] missing '{key}'")
    focus = app_state.get("focus")
    if not isinstance(focus, dict):
        raise RuntimeError("/api/apple/app-state focus is not an object")
    for key in ("focus_active", "updated_at", "source", "posture_mode", "posture_label", "posture_reason", "recommended_delivery", "quiet_hours", "hour_local"):
        if key not in focus:
            raise RuntimeError(f"/api/apple/app-state focus missing '{key}'")

    focus_state = require_mapping(payloads, "/api/apple/focus-state")
    for key in ("focus_active", "updated_at", "source", "source_fresh", "interruption_posture", "suppression_rules", "filter", "routing_lanes", "presets", "summary"):
        if key not in focus_state:
            raise RuntimeError(f"/api/apple/focus-state missing '{key}'")
    posture = focus_state.get("interruption_posture")
    if not isinstance(posture, dict):
        raise RuntimeError("/api/apple/focus-state missing object field 'interruption_posture'")
    for key in ("mode", "label", "reason", "recommended_delivery", "quiet_hours", "hour_local"):
        if key not in posture:
            raise RuntimeError(f"/api/apple/focus-state interruption_posture missing '{key}'")
    rules = focus_state.get("suppression_rules")
    if not isinstance(rules, list):
        raise RuntimeError("/api/apple/focus-state missing list field 'suppression_rules'")
    for index, item in enumerate(rules[:4]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/focus-state suppression_rules[{index}] is not an object")
        for key in ("id", "title", "detail", "active"):
            if key not in item:
                raise RuntimeError(f"/api/apple/focus-state suppression_rules[{index}] missing '{key}'")
    focus_filter = focus_state.get("filter")
    if not isinstance(focus_filter, dict):
        raise RuntimeError("/api/apple/focus-state missing object field 'filter'")
    for key in ("jarvis_mode", "hold_approvals", "silence_briefings", "source"):
        if key not in focus_filter:
            raise RuntimeError(f"/api/apple/focus-state filter missing '{key}'")
    lanes = focus_state.get("routing_lanes")
    if not isinstance(lanes, list):
        raise RuntimeError("/api/apple/focus-state missing list field 'routing_lanes'")
    for index, item in enumerate(lanes[:4]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/focus-state routing_lanes[{index}] is not an object")
        for key in ("id", "title", "detail", "delivery_mode", "active"):
            if key not in item:
                raise RuntimeError(f"/api/apple/focus-state routing_lanes[{index}] missing '{key}'")
    presets = focus_state.get("presets")
    if not isinstance(presets, list):
        raise RuntimeError("/api/apple/focus-state missing list field 'presets'")
    for index, item in enumerate(presets[:4]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/focus-state presets[{index}] is not an object")
        for key in ("id", "title", "detail", "focus_active", "jarvis_mode", "hold_approvals", "silence_briefings", "active"):
            if key not in item:
                raise RuntimeError(f"/api/apple/focus-state presets[{index}] missing '{key}'")
    summary = focus_state.get("summary")
    if not isinstance(summary, dict):
        raise RuntimeError("/api/apple/focus-state missing object field 'summary'")
    for key in ("label", "detail", "recommended_delivery"):
        if key not in summary:
            raise RuntimeError(f"/api/apple/focus-state summary missing '{key}'")

    admin_summary = require_mapping(payloads, "/api/apple/systems/admin-summary")
    for key in ("accounts", "family", "devices", "voice", "service", "integrations", "costs", "governance", "reflective_memory", "governed_workflows"):
        if key not in admin_summary:
            raise RuntimeError(f"/api/apple/systems/admin-summary missing '{key}'")
    accounts = admin_summary.get("accounts")
    if not isinstance(accounts, dict):
        raise RuntimeError("/api/apple/systems/admin-summary accounts is not an object")
    account_items = accounts.get("items")
    if not isinstance(account_items, list):
        raise RuntimeError("/api/apple/systems/admin-summary accounts.items is not a list")
    for index, item in enumerate(account_items[:3]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/systems/admin-summary accounts.items[{index}] is not an object")
        for key in ("id", "label", "provider", "status", "login_hint", "detail"):
            if key not in item:
                raise RuntimeError(f"/api/apple/systems/admin-summary accounts.items[{index}] missing '{key}'")
    family = admin_summary.get("family")
    if not isinstance(family, dict):
        raise RuntimeError("/api/apple/systems/admin-summary family is not an object")
    members = family.get("members")
    if not isinstance(members, list):
        raise RuntimeError("/api/apple/systems/admin-summary family.members is not a list")
    devices = admin_summary.get("devices")
    if not isinstance(devices, dict):
        raise RuntimeError("/api/apple/systems/admin-summary devices is not an object")
    voice = admin_summary.get("voice")
    if not isinstance(voice, dict):
        raise RuntimeError("/api/apple/systems/admin-summary voice is not an object")
    for key in ("provider", "provider_label", "voice_label", "local_ready", "cloud_ready", "detail"):
        if key not in voice:
            raise RuntimeError(f"/api/apple/systems/admin-summary voice missing '{key}'")
    service = admin_summary.get("service")
    if not isinstance(service, dict):
        raise RuntimeError("/api/apple/systems/admin-summary service is not an object")
    for key in (
        "hostname",
        "lan_url",
        "deployment_mode",
        "mode_label",
        "hosted_base_url",
        "hosted_provider",
        "edge_provider",
        "remote_admin_host",
        "cloudflare_access_enabled",
        "tunnel_enabled",
        "public_route_count",
        "compose_service_count",
        "runtime_loaded",
        "openviking_loaded",
        "assistant_loaded",
    ):
        if key not in service:
            raise RuntimeError(f"/api/apple/systems/admin-summary service missing '{key}'")
    integrations = admin_summary.get("integrations")
    if not isinstance(integrations, dict):
        raise RuntimeError("/api/apple/systems/admin-summary integrations is not an object")
    costs = admin_summary.get("costs")
    if not isinstance(costs, dict):
        raise RuntimeError("/api/apple/systems/admin-summary costs is not an object")
    for key in ("window_hours", "month_total_usd", "total_calls", "paid_calls", "prompt_tokens", "completion_tokens", "models"):
        if key not in costs:
            raise RuntimeError(f"/api/apple/systems/admin-summary costs missing '{key}'")
    governance = admin_summary.get("governance")
    if not isinstance(governance, dict):
        raise RuntimeError("/api/apple/systems/admin-summary governance is not an object")
    for key in ("zone_count", "active_zone_count", "arena_count", "active_arena_count", "stage_count", "pending_queue_count", "promotion_record_count", "zones", "arenas", "stages", "queue", "promotion_records"):
        if key not in governance:
            raise RuntimeError(f"/api/apple/systems/admin-summary governance missing '{key}'")
    zones = governance.get("zones")
    if not isinstance(zones, list):
        raise RuntimeError("/api/apple/systems/admin-summary governance.zones is not a list")
    for index, item in enumerate(zones[:4]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/systems/admin-summary governance.zones[{index}] is not an object")
        for key in ("id", "name", "zone_type", "authority_stage", "approval_mode", "status", "action_count"):
            if key not in item:
                raise RuntimeError(f"/api/apple/systems/admin-summary governance.zones[{index}] missing '{key}'")
    arenas = governance.get("arenas")
    if not isinstance(arenas, list):
        raise RuntimeError("/api/apple/systems/admin-summary governance.arenas is not a list")
    for index, item in enumerate(arenas[:4]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/systems/admin-summary governance.arenas[{index}] is not an object")
        for key in ("id", "name", "resource_type", "linked_zone_id", "risk_class", "status"):
            if key not in item:
                raise RuntimeError(f"/api/apple/systems/admin-summary governance.arenas[{index}] missing '{key}'")
    stages = governance.get("stages")
    if not isinstance(stages, list):
        raise RuntimeError("/api/apple/systems/admin-summary governance.stages is not a list")
    for index, item in enumerate(stages[:6]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/systems/admin-summary governance.stages[{index}] is not an object")
        for key in ("id", "name", "sequence", "status", "action_type_count", "boundary_mode"):
            if key not in item:
                raise RuntimeError(f"/api/apple/systems/admin-summary governance.stages[{index}] missing '{key}'")
    queue = governance.get("queue")
    if not isinstance(queue, list):
        raise RuntimeError("/api/apple/systems/admin-summary governance.queue is not a list")
    for index, item in enumerate(queue[:4]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/systems/admin-summary governance.queue[{index}] is not an object")
        for key in ("id", "arena_id", "action_type", "status", "created_at", "principal_id", "draft_id"):
            if key not in item:
                raise RuntimeError(f"/api/apple/systems/admin-summary governance.queue[{index}] missing '{key}'")
    promotion_records = governance.get("promotion_records")
    if not isinstance(promotion_records, list):
        raise RuntimeError("/api/apple/systems/admin-summary governance.promotion_records is not a list")
    for index, item in enumerate(promotion_records[:5]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/systems/admin-summary governance.promotion_records[{index}] is not an object")
        for key in ("id", "event_type", "subject_kind", "subject_id", "status", "actor", "basis", "trust_zone", "arena_id", "authority_stage", "created_at"):
            if key not in item:
                raise RuntimeError(f"/api/apple/systems/admin-summary governance.promotion_records[{index}] missing '{key}'")
    governed_workflows = admin_summary.get("governed_workflows")
    if not isinstance(governed_workflows, dict):
        raise RuntimeError("/api/apple/systems/admin-summary governed_workflows is not an object")
    for key in (
        "pending_approval_count",
        "rejected_approval_count",
        "automatic_action_count",
        "friction_action_count",
        "doctrine_candidate_count",
        "governance_proposal_count",
        "active_rule_count",
        "staged_stewardship_review_count",
        "pending_approvals",
        "recent_actions",
        "recent_stewardship_reviews",
        "governance_proposals",
        "doctrine_candidates",
    ):
        if key not in governed_workflows:
            raise RuntimeError(f"/api/apple/systems/admin-summary governed_workflows missing '{key}'")
    pending_approvals = governed_workflows.get("pending_approvals")
    if not isinstance(pending_approvals, list):
        raise RuntimeError("/api/apple/systems/admin-summary governed_workflows.pending_approvals is not a list")
    for index, item in enumerate(pending_approvals[:4]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/systems/admin-summary governed_workflows.pending_approvals[{index}] is not an object")
        for key in ("id", "actor", "request", "status", "rationale", "timestamp"):
            if key not in item:
                raise RuntimeError(f"/api/apple/systems/admin-summary governed_workflows.pending_approvals[{index}] missing '{key}'")
    recent_actions = governed_workflows.get("recent_actions")
    if not isinstance(recent_actions, list):
        raise RuntimeError("/api/apple/systems/admin-summary governed_workflows.recent_actions is not a list")
    for index, item in enumerate(recent_actions[:4]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/systems/admin-summary governed_workflows.recent_actions[{index}] is not an object")
        for key in ("id", "domain", "action", "decision", "mode", "succeeded", "caused_friction", "why_now", "timestamp"):
            if key not in item:
                raise RuntimeError(f"/api/apple/systems/admin-summary governed_workflows.recent_actions[{index}] missing '{key}'")
    recent_stewardship_reviews = governed_workflows.get("recent_stewardship_reviews")
    if not isinstance(recent_stewardship_reviews, list):
        raise RuntimeError("/api/apple/systems/admin-summary governed_workflows.recent_stewardship_reviews is not a list")
    for index, item in enumerate(recent_stewardship_reviews[:4]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/systems/admin-summary governed_workflows.recent_stewardship_reviews[{index}] is not an object")
        for key in ("id", "lane_id", "lane_title", "status", "review_surface", "packet_target", "boundary_decision", "boundary_reason", "approval_mode", "timestamp"):
            if key not in item:
                raise RuntimeError(f"/api/apple/systems/admin-summary governed_workflows.recent_stewardship_reviews[{index}] missing '{key}'")
    governance_proposals = governed_workflows.get("governance_proposals")
    if not isinstance(governance_proposals, list):
        raise RuntimeError("/api/apple/systems/admin-summary governed_workflows.governance_proposals is not a list")
    for index, item in enumerate(governance_proposals[:4]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/systems/admin-summary governed_workflows.governance_proposals[{index}] is not an object")
        for key in ("id", "title", "kind", "status", "summary", "promotion_reason"):
            if key not in item:
                raise RuntimeError(f"/api/apple/systems/admin-summary governed_workflows.governance_proposals[{index}] missing '{key}'")
    doctrine_candidates = governed_workflows.get("doctrine_candidates")
    if not isinstance(doctrine_candidates, list):
        raise RuntimeError("/api/apple/systems/admin-summary governed_workflows.doctrine_candidates is not a list")
    for index, item in enumerate(doctrine_candidates[:4]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/systems/admin-summary governed_workflows.doctrine_candidates[{index}] is not an object")
        for key in ("id", "title", "kind", "status", "summary", "promotion_reason"):
            if key not in item:
                raise RuntimeError(f"/api/apple/systems/admin-summary governed_workflows.doctrine_candidates[{index}] missing '{key}'")

    sandbox_operations = admin_summary.get("sandbox_operations")
    if not isinstance(sandbox_operations, dict):
        raise RuntimeError("/api/apple/systems/admin-summary sandbox_operations is not an object")
    sandbox_queue = sandbox_operations.get("queue")
    if not isinstance(sandbox_queue, dict):
        raise RuntimeError("/api/apple/systems/admin-summary sandbox_operations.queue is not an object")
    for key in ("active_count", "queued_job_count", "review_ready_count", "failed_run_count", "active_jobs", "lane_count"):
        if key not in sandbox_queue:
            raise RuntimeError(f"/api/apple/systems/admin-summary sandbox_operations.queue missing '{key}'")
    jobs = sandbox_operations.get("jobs")
    if not isinstance(jobs, list):
        raise RuntimeError("/api/apple/systems/admin-summary sandbox_operations.jobs is not a list")
    for index, item in enumerate(jobs[:4]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/systems/admin-summary sandbox_operations.jobs[{index}] is not an object")
        for key in ("id", "title", "status", "job_type", "target", "review_level", "summary", "auto_allowed", "updated_at", "last_sandbox_run_id"):
            if key not in item:
                raise RuntimeError(f"/api/apple/systems/admin-summary sandbox_operations.jobs[{index}] missing '{key}'")
    active_runs = sandbox_operations.get("active_runs")
    if not isinstance(active_runs, list):
        raise RuntimeError("/api/apple/systems/admin-summary sandbox_operations.active_runs is not a list")
    for index, item in enumerate(active_runs[:4]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/systems/admin-summary sandbox_operations.active_runs[{index}] is not an object")
        for key in ("id", "job_id", "title", "status", "current_step", "message", "updated_at", "worktree_path"):
            if key not in item:
                raise RuntimeError(f"/api/apple/systems/admin-summary sandbox_operations.active_runs[{index}] missing '{key}'")
    recent_runs = sandbox_operations.get("recent_runs")
    if not isinstance(recent_runs, list):
        raise RuntimeError("/api/apple/systems/admin-summary sandbox_operations.recent_runs is not a list")
    for index, item in enumerate(recent_runs[:4]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/systems/admin-summary sandbox_operations.recent_runs[{index}] is not an object")
        for key in ("id", "job_id", "title", "generated_at", "mode", "compile_ok", "tests_ok", "report_path", "patch_bundle_path"):
            if key not in item:
                raise RuntimeError(f"/api/apple/systems/admin-summary sandbox_operations.recent_runs[{index}] missing '{key}'")
    lane_summaries = sandbox_operations.get("lane_summaries")
    if not isinstance(lane_summaries, list):
        raise RuntimeError("/api/apple/systems/admin-summary sandbox_operations.lane_summaries is not a list")
    for index, item in enumerate(lane_summaries[:4]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/systems/admin-summary sandbox_operations.lane_summaries[{index}] is not an object")
        for key in ("id", "title", "queued_count", "active_run_count", "review_ready_count", "failed_run_count", "last_job_id", "status", "detail"):
            if key not in item:
                raise RuntimeError(f"/api/apple/systems/admin-summary sandbox_operations.lane_summaries[{index}] missing '{key}'")

    reflective_memory = admin_summary.get("reflective_memory")
    if not isinstance(reflective_memory, dict):
        raise RuntimeError("/api/apple/systems/admin-summary reflective_memory is not an object")
    for key in (
        "subject_display_name",
        "profile_fact_count",
        "pending_proposal_count",
        "first_light_history_count",
        "insight_count",
        "active_insight_count",
        "stewardship_decision_count",
        "governance_learning_count",
        "preferred_tone",
        "briefing_style",
        "preferred_voice",
        "guidance_lines",
        "profile_facts",
        "pending_proposals",
        "recent_first_light",
        "recent_stewardship_decisions",
        "governance_learning",
        "memory_graph",
    ):
        if key not in reflective_memory:
            raise RuntimeError(f"/api/apple/systems/admin-summary reflective_memory missing '{key}'")
    profile_facts = reflective_memory.get("profile_facts")
    if not isinstance(profile_facts, list):
        raise RuntimeError("/api/apple/systems/admin-summary reflective_memory.profile_facts is not a list")
    for index, item in enumerate(profile_facts[:4]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/systems/admin-summary reflective_memory.profile_facts[{index}] is not an object")
        for key in ("id", "title", "summary", "tags", "updated_at"):
            if key not in item:
                raise RuntimeError(f"/api/apple/systems/admin-summary reflective_memory.profile_facts[{index}] missing '{key}'")
    pending_proposals = reflective_memory.get("pending_proposals")
    if not isinstance(pending_proposals, list):
        raise RuntimeError("/api/apple/systems/admin-summary reflective_memory.pending_proposals is not a list")
    for index, item in enumerate(pending_proposals[:4]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/systems/admin-summary reflective_memory.pending_proposals[{index}] is not an object")
        for key in ("id", "title", "summary", "status", "memory_type", "confidence"):
            if key not in item:
                raise RuntimeError(f"/api/apple/systems/admin-summary reflective_memory.pending_proposals[{index}] missing '{key}'")
    recent_first_light = reflective_memory.get("recent_first_light")
    if not isinstance(recent_first_light, list):
        raise RuntimeError("/api/apple/systems/admin-summary reflective_memory.recent_first_light is not a list")
    for index, item in enumerate(recent_first_light[:4]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/systems/admin-summary reflective_memory.recent_first_light[{index}] is not an object")
        for key in ("id", "label", "summary"):
            if key not in item:
                raise RuntimeError(f"/api/apple/systems/admin-summary reflective_memory.recent_first_light[{index}] missing '{key}'")
    memory_graph = reflective_memory.get("memory_graph")
    if not isinstance(memory_graph, dict):
        raise RuntimeError("/api/apple/systems/admin-summary reflective_memory.memory_graph is not an object")
    for key in (
        "subject_display_name",
        "preferred_tone",
        "briefing_style",
        "preferred_voice",
        "anchor_count",
        "thread_count",
        "coverage_count",
        "horizon_count",
        "anchors",
        "active_threads",
        "surface_coverage",
        "horizons",
        "guidance_lines",
    ):
        if key not in memory_graph:
            raise RuntimeError(f"/api/apple/systems/admin-summary reflective_memory.memory_graph missing '{key}'")
    for field_name in ("anchors", "active_threads", "surface_coverage", "horizons", "guidance_lines"):
        if not isinstance(memory_graph.get(field_name), list):
            raise RuntimeError(f"/api/apple/systems/admin-summary reflective_memory.memory_graph.{field_name} is not a list")
    for index, item in enumerate((memory_graph.get("anchors") or [])[:4]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/systems/admin-summary reflective_memory.memory_graph.anchors[{index}] is not an object")
        for key in ("id", "title", "summary", "signal_count", "last_signal"):
            if key not in item:
                raise RuntimeError(f"/api/apple/systems/admin-summary reflective_memory.memory_graph.anchors[{index}] missing '{key}'")
    for index, item in enumerate((memory_graph.get("active_threads") or [])[:4]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/systems/admin-summary reflective_memory.memory_graph.active_threads[{index}] is not an object")
        for key in ("id", "title", "summary", "horizon", "signal_count"):
            if key not in item:
                raise RuntimeError(f"/api/apple/systems/admin-summary reflective_memory.memory_graph.active_threads[{index}] missing '{key}'")
    for index, item in enumerate((memory_graph.get("surface_coverage") or [])[:4]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/systems/admin-summary reflective_memory.memory_graph.surface_coverage[{index}] is not an object")
        for key in ("id", "title", "status", "detail"):
            if key not in item:
                raise RuntimeError(f"/api/apple/systems/admin-summary reflective_memory.memory_graph.surface_coverage[{index}] missing '{key}'")
    for index, item in enumerate((memory_graph.get("horizons") or [])[:4]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/systems/admin-summary reflective_memory.memory_graph.horizons[{index}] is not an object")
        for key in ("id", "label", "window_days", "profile_fact_count", "chronicle_entry_count", "first_light_count", "stewardship_decision_count", "summary"):
            if key not in item:
                raise RuntimeError(f"/api/apple/systems/admin-summary reflective_memory.memory_graph.horizons[{index}] missing '{key}'")
    recent_stewardship_decisions = reflective_memory.get("recent_stewardship_decisions")
    if not isinstance(recent_stewardship_decisions, list):
        raise RuntimeError("/api/apple/systems/admin-summary reflective_memory.recent_stewardship_decisions is not a list")
    for index, item in enumerate(recent_stewardship_decisions[:4]):
        if not isinstance(item, dict):
            raise RuntimeError(
                f"/api/apple/systems/admin-summary reflective_memory.recent_stewardship_decisions[{index}] is not an object"
            )
        for key in ("id", "label", "summary"):
            if key not in item:
                raise RuntimeError(
                    f"/api/apple/systems/admin-summary reflective_memory.recent_stewardship_decisions[{index}] missing '{key}'"
                )
    governance_learning = reflective_memory.get("governance_learning")
    if not isinstance(governance_learning, list):
        raise RuntimeError("/api/apple/systems/admin-summary reflective_memory.governance_learning is not a list")
    for index, item in enumerate(governance_learning[:4]):
        if not isinstance(item, dict):
            raise RuntimeError(
                f"/api/apple/systems/admin-summary reflective_memory.governance_learning[{index}] is not an object"
            )
        for key in ("id", "title", "summary", "recommendation", "confidence"):
            if key not in item:
                raise RuntimeError(
                    f"/api/apple/systems/admin-summary reflective_memory.governance_learning[{index}] missing '{key}'"
                )

    sound_state = require_mapping(payloads, "/api/apple/sound-alerts")
    for key in ("count", "recent_items", "high_confidence_items", "attention_flags", "policy_rules", "response_plans"):
        if key not in sound_state:
            raise RuntimeError(f"/api/apple/sound-alerts missing '{key}'")
    for field in ("recent_items", "high_confidence_items"):
        items = sound_state.get(field)
        if not isinstance(items, list):
            raise RuntimeError(f"/api/apple/sound-alerts {field} is not a list")
        for index, item in enumerate(items[:3]):
            if not isinstance(item, dict):
                raise RuntimeError(f"/api/apple/sound-alerts {field}[{index}] is not an object")
            for key in ("id", "label", "detail", "source", "confidence", "received_at", "resolved", "resolved_at"):
                if key not in item:
                    raise RuntimeError(f"/api/apple/sound-alerts {field}[{index}] missing '{key}'")
    policy_rules = sound_state.get("policy_rules")
    if not isinstance(policy_rules, list):
        raise RuntimeError("/api/apple/sound-alerts policy_rules is not a list")
    for index, item in enumerate(policy_rules[:4]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/sound-alerts policy_rules[{index}] is not an object")
        for key in ("id", "title", "detail", "delivery_mode", "active"):
            if key not in item:
                raise RuntimeError(f"/api/apple/sound-alerts policy_rules[{index}] missing '{key}'")
    response_plans = sound_state.get("response_plans")
    if not isinstance(response_plans, list):
        raise RuntimeError("/api/apple/sound-alerts response_plans is not a list")
    for index, item in enumerate(response_plans[:4]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/sound-alerts response_plans[{index}] is not an object")
        for key in ("id", "title", "detail", "target", "priority", "active"):
            if key not in item:
                raise RuntimeError(f"/api/apple/sound-alerts response_plans[{index}] missing '{key}'")

    vision_state = require_mapping(payloads, "/api/apple/vision/scans")
    for key in ("count", "recent_items", "recent_contexts", "attention_flags", "policy_rules", "response_plans"):
        if key not in vision_state:
            raise RuntimeError(f"/api/apple/vision/scans missing '{key}'")
    items = vision_state.get("recent_items")
    if not isinstance(items, list):
        raise RuntimeError("/api/apple/vision/scans recent_items is not a list")
    for index, item in enumerate(items[:3]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/vision/scans recent_items[{index}] is not an object")
        for key in ("id", "context", "source", "text_preview", "received_at", "resolved", "resolved_at"):
            if key not in item:
                raise RuntimeError(f"/api/apple/vision/scans recent_items[{index}] missing '{key}'")
    policy_rules = vision_state.get("policy_rules")
    if not isinstance(policy_rules, list):
        raise RuntimeError("/api/apple/vision/scans policy_rules is not a list")
    for index, item in enumerate(policy_rules[:4]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/vision/scans policy_rules[{index}] is not an object")
        for key in ("id", "title", "detail", "delivery_mode", "active"):
            if key not in item:
                raise RuntimeError(f"/api/apple/vision/scans policy_rules[{index}] missing '{key}'")
    response_plans = vision_state.get("response_plans")
    if not isinstance(response_plans, list):
        raise RuntimeError("/api/apple/vision/scans response_plans is not a list")
    for index, item in enumerate(response_plans[:4]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/vision/scans response_plans[{index}] is not an object")
        for key in ("id", "title", "detail", "target", "priority", "active"):
            if key not in item:
                raise RuntimeError(f"/api/apple/vision/scans response_plans[{index}] missing '{key}'")

    media_state = require_mapping(payloads, "/api/apple/now-playing/state")
    for key in ("title", "artist", "album", "is_playing", "updated_at", "artwork_available", "summary", "routing_rules", "response_plans", "suggested_controls", "recent_items"):
        if key not in media_state:
            raise RuntimeError(f"/api/apple/now-playing/state missing '{key}'")
    summary = media_state.get("summary")
    if not isinstance(summary, dict):
        raise RuntimeError("/api/apple/now-playing/state summary is not an object")
    for key in ("label", "detail"):
        if key not in summary:
            raise RuntimeError(f"/api/apple/now-playing/state summary missing '{key}'")
    routing_rules = media_state.get("routing_rules")
    if not isinstance(routing_rules, list):
        raise RuntimeError("/api/apple/now-playing/state routing_rules is not a list")
    for index, item in enumerate(routing_rules[:4]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/now-playing/state routing_rules[{index}] is not an object")
        for key in ("id", "title", "detail", "delivery_mode", "active"):
            if key not in item:
                raise RuntimeError(f"/api/apple/now-playing/state routing_rules[{index}] missing '{key}'")
    response_plans = media_state.get("response_plans")
    if not isinstance(response_plans, list):
        raise RuntimeError("/api/apple/now-playing/state response_plans is not a list")
    for index, item in enumerate(response_plans[:4]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/now-playing/state response_plans[{index}] is not an object")
        for key in ("id", "title", "detail", "target", "priority", "active"):
            if key not in item:
                raise RuntimeError(f"/api/apple/now-playing/state response_plans[{index}] missing '{key}'")
    suggested_controls = media_state.get("suggested_controls")
    if not isinstance(suggested_controls, list):
        raise RuntimeError("/api/apple/now-playing/state suggested_controls is not a list")
    for index, item in enumerate(suggested_controls[:4]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/now-playing/state suggested_controls[{index}] is not an object")
        for key in ("id", "title", "detail", "style", "active"):
            if key not in item:
                raise RuntimeError(f"/api/apple/now-playing/state suggested_controls[{index}] missing '{key}'")
    media_items = media_state.get("recent_items")
    if not isinstance(media_items, list):
        raise RuntimeError("/api/apple/now-playing/state recent_items is not a list")
    for index, item in enumerate(media_items[:3]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/now-playing/state recent_items[{index}] is not an object")
        for key in ("id", "title", "detail", "ts", "is_playing", "artist", "album"):
            if key not in item:
                raise RuntimeError(f"/api/apple/now-playing/state recent_items[{index}] missing '{key}'")

    control_state = require_mapping(payloads, "/api/apple/control-plane/state")
    for key in ("notifications", "events", "media"):
        if key not in control_state:
            raise RuntimeError(f"/api/apple/control-plane/state missing '{key}'")
    notifications = control_state.get("notifications")
    if not isinstance(notifications, dict):
        raise RuntimeError("/api/apple/control-plane/state notifications is not an object")
    for key in ("total", "pending", "seen", "snoozed", "resolved", "dismissed", "categories", "last_updated_at"):
        if key not in notifications:
            raise RuntimeError(f"/api/apple/control-plane/state notifications missing '{key}'")
    event_stats = control_state.get("events")
    if not isinstance(event_stats, dict):
        raise RuntimeError("/api/apple/control-plane/state events is not an object")
    for key in ("recent_count", "domains", "severities", "last_event_at", "recent_items"):
        if key not in event_stats:
            raise RuntimeError(f"/api/apple/control-plane/state events missing '{key}'")
    recent_items = event_stats.get("recent_items")
    if not isinstance(recent_items, list):
        raise RuntimeError("/api/apple/control-plane/state events recent_items is not a list")
    for index, item in enumerate(recent_items[:4]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/control-plane/state events recent_items[{index}] is not an object")
        for key in ("id", "title", "detail", "domain", "severity", "ts"):
            if key not in item:
                raise RuntimeError(f"/api/apple/control-plane/state events recent_items[{index}] missing '{key}'")
    media_summary = control_state.get("media")
    if not isinstance(media_summary, dict):
        raise RuntimeError("/api/apple/control-plane/state media is not an object")
    for key in ("synced", "updated_at", "title", "is_playing"):
        if key not in media_summary:
            raise RuntimeError(f"/api/apple/control-plane/state media missing '{key}'")
    freshness = control_state.get("freshness")
    if not isinstance(freshness, list):
        raise RuntimeError("/api/apple/control-plane/state freshness is not a list")
    for index, item in enumerate(freshness[:8]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/control-plane/state freshness[{index}] is not an object")
        for key in ("id", "label", "synced", "updated_at", "status", "detail"):
            if key not in item:
                raise RuntimeError(f"/api/apple/control-plane/state freshness[{index}] missing '{key}'")

    reminders = app_state.get("reminders")
    if not isinstance(reminders, dict):
        raise RuntimeError("/api/apple/app-state reminders is not an object")
    top_items = reminders.get("top_items")
    if not isinstance(top_items, list):
        raise RuntimeError("/api/apple/app-state reminders missing list field 'top_items'")
    for index, item in enumerate(top_items[:3]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/app-state reminders top_items[{index}] is not an object")
        for key in ("id", "title", "due", "list", "priority"):
            if key not in item:
                raise RuntimeError(f"/api/apple/app-state reminders top_items[{index}] missing '{key}'")

    reminders_state = require_mapping(payloads, "/api/apple/reminders/state")
    for key in ("synced", "synced_at", "count", "summary", "list_summaries", "open_items", "overdue_items", "due_soon_items", "priority_items", "attention_flags"):
        if key not in reminders_state:
            raise RuntimeError(f"/api/apple/reminders/state missing '{key}'")
    summary = reminders_state.get("summary")
    if not isinstance(summary, dict):
        raise RuntimeError("/api/apple/reminders/state summary is not an object")
    for key in ("open_count", "overdue_count", "due_soon_count", "priority_count", "no_due_date_count"):
        if key not in summary:
            raise RuntimeError(f"/api/apple/reminders/state summary missing '{key}'")
    list_summaries = reminders_state.get("list_summaries")
    if not isinstance(list_summaries, list):
        raise RuntimeError("/api/apple/reminders/state list_summaries is not a list")
    for index, item in enumerate(list_summaries[:4]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/reminders/state list_summaries[{index}] is not an object")
        for key in ("id", "title", "count", "overdue_count", "due_soon_count", "priority_count"):
            if key not in item:
                raise RuntimeError(f"/api/apple/reminders/state list_summaries[{index}] missing '{key}'")
    for field in ("open_items", "overdue_items", "due_soon_items", "priority_items"):
        items = reminders_state.get(field)
        if not isinstance(items, list):
            raise RuntimeError(f"/api/apple/reminders/state {field} is not a list")
        for index, item in enumerate(items[:3]):
            if not isinstance(item, dict):
                raise RuntimeError(f"/api/apple/reminders/state {field}[{index}] is not an object")
            for key in ("id", "title", "due", "list", "priority", "priority_label", "minutes_away", "overdue", "due_soon", "available_actions"):
                if key not in item:
                    raise RuntimeError(f"/api/apple/reminders/state {field}[{index}] missing '{key}'")
    flags = reminders_state.get("attention_flags")
    if not isinstance(flags, list):
        raise RuntimeError("/api/apple/reminders/state attention_flags is not a list")
    for index, item in enumerate(flags[:3]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/reminders/state attention_flags[{index}] is not an object")
        for key in ("id", "reminder_id", "kind", "severity", "title", "detail"):
            if key not in item:
                raise RuntimeError(f"/api/apple/reminders/state attention_flags[{index}] missing '{key}'")

    items = require_data(payloads, "/api/apple/needs")
    if not isinstance(items, list):
        raise RuntimeError("/api/apple/needs returned non-list data payload")
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/needs items[{index}] is not an object")
        for key in (
            "id",
            "text",
            "agent",
            "risk",
            "allowed_actions",
            "priority",
            "tags",
            "requires_confirmation",
            "confirmation_phrase",
            "target_summary",
            "context_lines",
        ):
            if key not in item:
                raise RuntimeError(f"/api/apple/needs items[{index}] missing '{key}'")

    health = require_mapping(payloads, "/api/apple/health/summary?actor=chris")
    for key in (
        "steps_today",
        "heart_rate_avg",
        "sleep_hours",
        "active_calories",
        "stand_hours",
        "hrv",
        "readiness",
        "thor_note",
        "last_sync",
        "protocol_items",
        "alerts",
        "next_actions",
        "readiness_factors",
        "watchlist",
    ):
        if key not in health:
            raise RuntimeError(f"/api/apple/health/summary?actor=chris missing '{key}'")
    readiness_factors = health.get("readiness_factors")
    if not isinstance(readiness_factors, list):
        raise RuntimeError("/api/apple/health/summary?actor=chris readiness_factors is not a list")
    for index, item in enumerate(readiness_factors[:4]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/health/summary?actor=chris readiness_factors[{index}] is not an object")
        for key in ("metric", "label", "value", "missing"):
            if key not in item:
                raise RuntimeError(f"/api/apple/health/summary?actor=chris readiness_factors[{index}] missing '{key}'")
    thor_snapshot = health.get("thor_snapshot")
    if thor_snapshot is not None:
        if not isinstance(thor_snapshot, dict):
            raise RuntimeError("/api/apple/health/summary?actor=chris thor_snapshot is not an object")
        for key in ("activity_streak_days", "total_active_minutes_week", "avg_daily_steps", "readiness", "thor_note", "needs_rest", "last_activity"):
            if key not in thor_snapshot:
                raise RuntimeError(f"/api/apple/health/summary?actor=chris thor_snapshot missing '{key}'")
    completeness = health.get("completeness")
    if completeness is not None:
        if not isinstance(completeness, dict):
            raise RuntimeError("/api/apple/health/summary?actor=chris completeness is not an object")
        for key in ("total_score", "grade", "critical_gaps", "quick_wins"):
            if key not in completeness:
                raise RuntimeError(f"/api/apple/health/summary?actor=chris completeness missing '{key}'")
    watchlist = health.get("watchlist")
    if not isinstance(watchlist, list):
        raise RuntimeError("/api/apple/health/summary?actor=chris watchlist is not a list")
    for index, item in enumerate(watchlist[:6]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/health/summary?actor=chris watchlist[{index}] is not an object")
        for key in ("kind", "title", "detail", "severity"):
            if key not in item:
                raise RuntimeError(f"/api/apple/health/summary?actor=chris watchlist[{index}] missing '{key}'")
    daily_score = health.get("daily_score")
    if daily_score is not None:
        if not isinstance(daily_score, dict):
            raise RuntimeError("/api/apple/health/summary?actor=chris daily_score is not an object")
        for key in ("value", "grade", "message", "estimated"):
            if key not in daily_score:
                raise RuntimeError(f"/api/apple/health/summary?actor=chris daily_score missing '{key}'")
    protocol_items = health.get("protocol_items")
    if not isinstance(protocol_items, list):
        raise RuntimeError("/api/apple/health/summary?actor=chris protocol_items is not a list")
    for index, item in enumerate(protocol_items[:6]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/health/summary?actor=chris protocol_items[{index}] is not an object")
        for key in ("title", "detail", "emphasis"):
            if key not in item:
                raise RuntimeError(f"/api/apple/health/summary?actor=chris protocol_items[{index}] missing '{key}'")
    alerts = health.get("alerts")
    if not isinstance(alerts, list):
        raise RuntimeError("/api/apple/health/summary?actor=chris alerts is not a list")
    for index, item in enumerate(alerts[:6]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/health/summary?actor=chris alerts[{index}] is not an object")
        for key in ("title", "severity"):
            if key not in item:
                raise RuntimeError(f"/api/apple/health/summary?actor=chris alerts[{index}] missing '{key}'")
    next_actions = health.get("next_actions")
    if not isinstance(next_actions, list):
        raise RuntimeError("/api/apple/health/summary?actor=chris next_actions is not a list")
    continuity = health.get("continuity")
    if not isinstance(continuity, dict):
        raise RuntimeError("/api/apple/health/summary?actor=chris continuity is not an object")
    for key in (
        "subject_display_name",
        "readiness_lane",
        "recovery_focus",
        "active_conditions",
        "guidance_lines",
        "profile_fact_count",
        "recent_profile_facts",
        "recent_first_light",
    ):
        if key not in continuity:
            raise RuntimeError(f"/api/apple/health/summary?actor=chris continuity missing '{key}'")
    if not isinstance(continuity.get("active_conditions"), list):
        raise RuntimeError("/api/apple/health/summary?actor=chris continuity active_conditions is not a list")
    if not isinstance(continuity.get("guidance_lines"), list):
        raise RuntimeError("/api/apple/health/summary?actor=chris continuity guidance_lines is not a list")
    recent_profile_facts = continuity.get("recent_profile_facts")
    if not isinstance(recent_profile_facts, list):
        raise RuntimeError("/api/apple/health/summary?actor=chris continuity recent_profile_facts is not a list")
    for index, fact in enumerate(recent_profile_facts[:4]):
        if not isinstance(fact, dict):
            raise RuntimeError(f"/api/apple/health/summary?actor=chris continuity recent_profile_facts[{index}] is not an object")
        for key in ("id", "title", "summary"):
            if key not in fact:
                raise RuntimeError(f"/api/apple/health/summary?actor=chris continuity recent_profile_facts[{index}] missing '{key}'")
    recent_first_light = continuity.get("recent_first_light")
    if not isinstance(recent_first_light, list):
        raise RuntimeError("/api/apple/health/summary?actor=chris continuity recent_first_light is not a list")
    for index, moment in enumerate(recent_first_light[:4]):
        if not isinstance(moment, dict):
            raise RuntimeError(f"/api/apple/health/summary?actor=chris continuity recent_first_light[{index}] is not an object")
        for key in ("id", "label", "summary"):
            if key not in moment:
                raise RuntimeError(f"/api/apple/health/summary?actor=chris continuity recent_first_light[{index}] missing '{key}'")

    notifications_wrapper = require_mapping(payloads, "/api/apple/notifications")
    for key in ("notifications", "summary", "routing", "event_summary"):
        if key not in notifications_wrapper:
            raise RuntimeError(f"/api/apple/notifications missing '{key}'")
    notifications = notifications_wrapper.get("notifications")
    if not isinstance(notifications, list):
        raise RuntimeError("/api/apple/notifications missing list field 'notifications'")
    for index, item in enumerate(notifications[:3]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/notifications notifications[{index}] is not an object")
        for key in ("id", "category", "title", "status", "created_at", "available_actions", "delivery_mode", "decision_reason", "posture_snapshot"):
            if key not in item:
                raise RuntimeError(f"/api/apple/notifications notifications[{index}] missing '{key}'")
    summary = notifications_wrapper.get("summary")
    if not isinstance(summary, dict):
        raise RuntimeError("/api/apple/notifications summary is not an object")
    for key in ("total", "pending", "seen", "snoozed", "resolved", "dismissed", "categories", "last_updated_at"):
        if key not in summary:
            raise RuntimeError(f"/api/apple/notifications summary missing '{key}'")
    routing = notifications_wrapper.get("routing")
    if not isinstance(routing, dict):
        raise RuntimeError("/api/apple/notifications routing is not an object")
    for key in (
        "mode",
        "label",
        "reason",
        "recommended_delivery",
        "focus_active",
        "quiet_hours",
        "hour_local",
        "needs_count",
        "alert_count",
        "present_members",
        "updated_at",
        "lanes",
    ):
        if key not in routing:
            raise RuntimeError(f"/api/apple/notifications routing missing '{key}'")
    lanes = routing.get("lanes")
    if not isinstance(lanes, list):
        raise RuntimeError("/api/apple/notifications routing lanes is not a list")
    for index, item in enumerate(lanes[:4]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/notifications routing lanes[{index}] is not an object")
        for key in ("id", "title", "detail", "active"):
            if key not in item:
                raise RuntimeError(f"/api/apple/notifications routing lanes[{index}] missing '{key}'")
    event_summary = notifications_wrapper.get("event_summary")
    if not isinstance(event_summary, dict):
        raise RuntimeError("/api/apple/notifications event_summary is not an object")
    for key in ("recent_count", "domains", "severities", "last_event_at"):
        if key not in event_summary:
            raise RuntimeError(f"/api/apple/notifications event_summary missing '{key}'")

    events_wrapper = require_mapping(payloads, "/api/apple/events/recent")
    events = events_wrapper.get("events")
    if not isinstance(events, list):
        raise RuntimeError("/api/apple/events/recent missing list field 'events'")
    for index, item in enumerate(events[:3]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/events/recent events[{index}] is not an object")
        for key in ("id", "ts", "domain", "kind", "severity", "title", "status"):
            if key not in item:
                raise RuntimeError(f"/api/apple/events/recent events[{index}] missing '{key}'")

    pending_wrapper = require_mapping(payloads, "/api/apple/notifications/pending")
    pending = pending_wrapper.get("notifications")
    if not isinstance(pending, list):
        raise RuntimeError("/api/apple/notifications/pending missing list field 'notifications'")
    for index, item in enumerate(pending[:3]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/notifications/pending notifications[{index}] is not an object")
        for key in ("id", "title", "body", "category", "badge", "created_at"):
            if key not in item:
                raise RuntimeError(f"/api/apple/notifications/pending notifications[{index}] missing '{key}'")

    navigation_locations = require_mapping(payloads, "/api/apple/navigation/locations")
    for key in ("preferred_location_id", "saved_locations", "navigation_state"):
        if key not in navigation_locations:
            raise RuntimeError(f"/api/apple/navigation/locations missing '{key}'")
    saved_locations = navigation_locations.get("saved_locations")
    if not isinstance(saved_locations, list):
        raise RuntimeError("/api/apple/navigation/locations saved_locations is not a list")
    for index, item in enumerate(saved_locations[:3]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/navigation/locations saved_locations[{index}] is not an object")
        for key in ("id", "label", "address", "geography", "source", "notes"):
            if key not in item:
                raise RuntimeError(f"/api/apple/navigation/locations saved_locations[{index}] missing '{key}'")

    navigation_state = require_mapping(payloads, "/api/apple/navigation/state")
    for key in (
        "favorite_destinations",
        "recent_destinations",
        "active_stop_category_ids",
        "parks_historic_radius_miles",
        "selected_origin_mode",
        "selected_saved_location_id",
        "last_route",
    ):
        if key not in navigation_state:
            raise RuntimeError(f"/api/apple/navigation/state missing '{key}'")
    last_route = navigation_state.get("last_route")
    if not isinstance(last_route, dict):
        raise RuntimeError("/api/apple/navigation/state last_route is not an object")
    for key in ("origin", "destination"):
        if key not in last_route:
            raise RuntimeError(f"/api/apple/navigation/state last_route missing '{key}'")

    navigation_stops = require_mapping(
        payloads,
        "/api/apple/navigation/stops?origin=8384%20Riley%20Rd%2C%20Alexandria%2C%20KY%2041001&destination=Cincinnati%2C%20OH&parks_radius_miles=25",
    )
    sections = navigation_stops.get("sections")
    if not isinstance(sections, list):
        raise RuntimeError("/api/apple/navigation/stops ... missing list field 'sections'")
    for index, section in enumerate(sections[:3]):
        if not isinstance(section, dict):
            raise RuntimeError(f"/api/apple/navigation/stops sections[{index}] is not an object")
        for key in ("id", "label", "items"):
            if key not in section:
                raise RuntimeError(f"/api/apple/navigation/stops sections[{index}] missing '{key}'")
        items = section.get("items")
        if not isinstance(items, list):
            raise RuntimeError(f"/api/apple/navigation/stops sections[{index}] items is not a list")
        for item_index, item in enumerate(items[:3]):
            if not isinstance(item, dict):
                raise RuntimeError(f"/api/apple/navigation/stops sections[{index}] items[{item_index}] is not an object")
            for key in ("name", "address", "description", "url", "route_mile_marker", "distance_from_route"):
                if key not in item:
                    raise RuntimeError(f"/api/apple/navigation/stops sections[{index}] items[{item_index}] missing '{key}'")

    chronicle = require_mapping(payloads, "/api/apple/chronicle")
    for key in ("entries", "context", "patterns", "continuity", "study_workspace", "updated_at"):
        if key not in chronicle:
            raise RuntimeError(f"/api/apple/chronicle missing '{key}'")
    context = chronicle.get("context")
    if not isinstance(context, dict):
        raise RuntimeError("/api/apple/chronicle missing object field 'context'")
    for key in ("active_prayers", "top_themes", "total_entries", "active_prayer_count", "answered_prayer_count"):
        if key not in context:
            raise RuntimeError(f"/api/apple/chronicle context missing '{key}'")
    active_prayers = context.get("active_prayers")
    if not isinstance(active_prayers, list):
        raise RuntimeError("/api/apple/chronicle context active_prayers is not a list")
    for index, item in enumerate(active_prayers[:3]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/chronicle context active_prayers[{index}] is not an object")
        for key in ("id", "text", "category", "times_prayed", "last_prayed_at", "answered", "answer_summary"):
            if key not in item:
                raise RuntimeError(f"/api/apple/chronicle context active_prayers[{index}] missing '{key}'")
    patterns = chronicle.get("patterns")
    if not isinstance(patterns, dict):
        raise RuntimeError("/api/apple/chronicle missing object field 'patterns'")
    for key in ("window_days", "total_recent_entries", "entry_type_breakdown", "recurring_themes", "prayer_arc", "writing_streak_days"):
        if key not in patterns:
            raise RuntimeError(f"/api/apple/chronicle patterns missing '{key}'")
    continuity = chronicle.get("continuity")
    if not isinstance(continuity, dict):
        raise RuntimeError("/api/apple/chronicle missing object field 'continuity'")
    for key in ("relevant_facts", "similar_entries", "situations", "recall_prompt"):
        if key not in continuity:
            raise RuntimeError(f"/api/apple/chronicle continuity missing '{key}'")
    situations = continuity.get("situations")
    if not isinstance(situations, list):
        raise RuntimeError("/api/apple/chronicle continuity situations is not a list")
    for index, item in enumerate(situations[:3]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/chronicle continuity situations[{index}] is not an object")
        for key in ("id", "label", "summary", "signals", "matched_fact_count"):
            if key not in item:
                raise RuntimeError(f"/api/apple/chronicle continuity situations[{index}] missing '{key}'")
    relevant_facts = continuity.get("relevant_facts")
    if not isinstance(relevant_facts, list):
        raise RuntimeError("/api/apple/chronicle continuity relevant_facts is not a list")
    for index, item in enumerate(relevant_facts[:4]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/chronicle continuity relevant_facts[{index}] is not an object")
        for key in ("fact_id", "title", "summary", "lane", "updated_at", "tags"):
            if key not in item:
                raise RuntimeError(f"/api/apple/chronicle continuity relevant_facts[{index}] missing '{key}'")
    similar_entries = continuity.get("similar_entries")
    if not isinstance(similar_entries, list):
        raise RuntimeError("/api/apple/chronicle continuity similar_entries is not a list")
    for index, item in enumerate(similar_entries[:3]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/chronicle continuity similar_entries[{index}] is not an object")
        for key in ("id", "type", "title", "body", "scripture", "timestamp"):
            if key not in item:
                raise RuntimeError(f"/api/apple/chronicle continuity similar_entries[{index}] missing '{key}'")
    study_workspace = chronicle.get("study_workspace")
    if study_workspace is not None:
        if not isinstance(study_workspace, dict):
            raise RuntimeError("/api/apple/chronicle study_workspace is not an object")
        for key in ("passage", "title", "date", "focus_summary", "prompts"):
            if key not in study_workspace:
                raise RuntimeError(f"/api/apple/chronicle study_workspace missing '{key}'")

    publishing = require_mapping(payloads, "/api/apple/publishing")
    for key in ("projects", "revenue_summary", "upcoming", "pending_reviews", "pending_reviews_count", "launch_control", "launch_workspace", "action_items", "continuity"):
        if key not in publishing:
            raise RuntimeError(f"/api/apple/publishing missing '{key}'")
    projects = publishing.get("projects")
    if not isinstance(projects, list):
        raise RuntimeError("/api/apple/publishing projects is not a list")
    for index, item in enumerate(projects):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/publishing projects[{index}] is not an object")
        for key in ("project_id", "title", "type", "status", "platform", "checklist_progress", "checklist_percent", "platform_focus"):
            if key not in item:
                raise RuntimeError(f"/api/apple/publishing projects[{index}] missing '{key}'")
    reviews = publishing.get("pending_reviews")
    if not isinstance(reviews, list):
        raise RuntimeError("/api/apple/publishing pending_reviews is not a list")
    for index, item in enumerate(reviews):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/publishing pending_reviews[{index}] is not an object")
        for key in ("review_id", "title", "stage_key", "stage_display", "content_preview", "word_count", "ready_since"):
            if key not in item:
                raise RuntimeError(f"/api/apple/publishing pending_reviews[{index}] missing '{key}'")
    launch_control = publishing.get("launch_control")
    if launch_control is not None:
        if not isinstance(launch_control, dict):
            raise RuntimeError("/api/apple/publishing launch_control is not an object")
        for key in ("project_id", "title", "phase", "posts_scheduled", "posts_pending_approval", "next_action"):
            if key not in launch_control:
                raise RuntimeError(f"/api/apple/publishing launch_control missing '{key}'")
    launch_workspace = publishing.get("launch_workspace")
    if launch_workspace is not None:
        if not isinstance(launch_workspace, dict):
            raise RuntimeError("/api/apple/publishing launch_workspace is not an object")
        for key in ("project_id", "title", "platform", "platform_focus", "checklist_progress", "checklist_percent", "next_checklist_step", "launch_slug", "asset_status", "checklist", "assets"):
            if key not in launch_workspace:
                raise RuntimeError(f"/api/apple/publishing launch_workspace missing '{key}'")
        checklist = launch_workspace.get("checklist")
        if not isinstance(checklist, list):
            raise RuntimeError("/api/apple/publishing launch_workspace checklist is not a list")
        for index, item in enumerate(checklist[:3]):
            if not isinstance(item, dict):
                raise RuntimeError(f"/api/apple/publishing launch_workspace checklist[{index}] is not an object")
            for key in ("step", "label", "order", "completed", "completed_at"):
                if key not in item:
                    raise RuntimeError(f"/api/apple/publishing launch_workspace checklist[{index}] missing '{key}'")
        assets = launch_workspace.get("assets")
        if not isinstance(assets, list):
            raise RuntimeError("/api/apple/publishing launch_workspace assets is not a list")
        for index, item in enumerate(assets[:3]):
            if not isinstance(item, dict):
                raise RuntimeError(f"/api/apple/publishing launch_workspace assets[{index}] is not an object")
            for key in ("key", "title", "status", "item_count", "detail"):
                if key not in item:
                    raise RuntimeError(f"/api/apple/publishing launch_workspace assets[{index}] missing '{key}'")
    continuity = publishing.get("continuity")
    if not isinstance(continuity, dict):
        raise RuntimeError("/api/apple/publishing continuity is not an object")
    for key in (
        "subject_display_name",
        "briefing_style",
        "launch_focus",
        "active_platforms",
        "pending_review_pressure",
        "profile_fact_count",
        "guidance_lines",
        "recent_profile_facts",
        "recent_first_light",
    ):
        if key not in continuity:
            raise RuntimeError(f"/api/apple/publishing continuity missing '{key}'")
    if not isinstance(continuity.get("active_platforms"), list):
        raise RuntimeError("/api/apple/publishing continuity active_platforms is not a list")
    if not isinstance(continuity.get("guidance_lines"), list):
        raise RuntimeError("/api/apple/publishing continuity guidance_lines is not a list")
    recent_profile_facts = continuity.get("recent_profile_facts")
    if not isinstance(recent_profile_facts, list):
        raise RuntimeError("/api/apple/publishing continuity recent_profile_facts is not a list")
    for index, fact in enumerate(recent_profile_facts[:4]):
        if not isinstance(fact, dict):
            raise RuntimeError(f"/api/apple/publishing continuity recent_profile_facts[{index}] is not an object")
        for key in ("id", "title", "summary"):
            if key not in fact:
                raise RuntimeError(f"/api/apple/publishing continuity recent_profile_facts[{index}] missing '{key}'")
    recent_first_light = continuity.get("recent_first_light")
    if not isinstance(recent_first_light, list):
        raise RuntimeError("/api/apple/publishing continuity recent_first_light is not a list")
    for index, moment in enumerate(recent_first_light[:4]):
        if not isinstance(moment, dict):
            raise RuntimeError(f"/api/apple/publishing continuity recent_first_light[{index}] is not an object")
        for key in ("id", "label", "summary"):
            if key not in moment:
                raise RuntimeError(f"/api/apple/publishing continuity recent_first_light[{index}] missing '{key}'")

    huddle = require_mapping(payloads, "/api/apple/huddle")
    for key in ("reports", "blockers", "highlights", "approvals", "approvals_count", "total_active_work", "runtime", "party_mode", "dossiers", "continuity"):
        if key not in huddle:
            raise RuntimeError(f"/api/apple/huddle missing '{key}'")
    reports = huddle.get("reports")
    if not isinstance(reports, list):
        raise RuntimeError("/api/apple/huddle reports is not a list")
    for index, item in enumerate(reports):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/huddle reports[{index}] is not an object")
        for key in ("agent_id", "agent_name", "domain", "status", "summary", "blockers", "yesterday", "today", "needs", "highlights", "source", "active_work_count"):
            if key not in item:
                raise RuntimeError(f"/api/apple/huddle reports[{index}] missing '{key}'")
    runtime = huddle.get("runtime")
    if runtime is not None:
        if not isinstance(runtime, dict):
            raise RuntimeError("/api/apple/huddle runtime is not an object")
        for key in ("active_mode", "quiet_hours_active", "awake_count", "idle_count", "blocked_count", "last_tick_at", "statuses"):
            if key not in runtime:
                raise RuntimeError(f"/api/apple/huddle runtime missing '{key}'")
        statuses = runtime.get("statuses")
        if not isinstance(statuses, list):
            raise RuntimeError("/api/apple/huddle runtime statuses is not a list")
        for index, item in enumerate(statuses[:3]):
            if not isinstance(item, dict):
                raise RuntimeError(f"/api/apple/huddle runtime statuses[{index}] is not an object")
            for key in ("agent_id", "label", "state", "reason", "last_run_at", "next_run_at", "due_now", "priority"):
                if key not in item:
                    raise RuntimeError(f"/api/apple/huddle runtime statuses[{index}] missing '{key}'")
    party_mode = huddle.get("party_mode")
    if party_mode is not None:
        if not isinstance(party_mode, dict):
            raise RuntimeError("/api/apple/huddle party_mode is not an object")
        for key in ("status", "triggered_by", "dossiers_built_count", "dossiers_attempted", "items_dreamed", "items_researched", "last_log", "started_at", "ended_at"):
            if key not in party_mode:
                raise RuntimeError(f"/api/apple/huddle party_mode missing '{key}'")
    dossiers = huddle.get("dossiers")
    if not isinstance(dossiers, list):
        raise RuntimeError("/api/apple/huddle dossiers is not a list")
    for index, item in enumerate(dossiers[:3]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/huddle dossiers[{index}] is not an object")
        for key in ("dossier_id", "title", "status", "executive_summary", "first_action", "confidence_score", "revenue_estimate_low", "revenue_estimate_high", "effort_hours", "updated_at"):
            if key not in item:
                raise RuntimeError(f"/api/apple/huddle dossiers[{index}] missing '{key}'")
    continuity = huddle.get("continuity")
    if not isinstance(continuity, dict):
        raise RuntimeError("/api/apple/huddle continuity is not an object")
    for key in (
        "subject_display_name",
        "council_focus",
        "active_domains",
        "ready_dossier_count",
        "profile_fact_count",
        "guidance_lines",
        "recent_profile_facts",
        "recent_first_light",
    ):
        if key not in continuity:
            raise RuntimeError(f"/api/apple/huddle continuity missing '{key}'")
    if not isinstance(continuity.get("active_domains"), list):
        raise RuntimeError("/api/apple/huddle continuity active_domains is not a list")
    if not isinstance(continuity.get("guidance_lines"), list):
        raise RuntimeError("/api/apple/huddle continuity guidance_lines is not a list")
    recent_profile_facts = continuity.get("recent_profile_facts")
    if not isinstance(recent_profile_facts, list):
        raise RuntimeError("/api/apple/huddle continuity recent_profile_facts is not a list")
    for index, fact in enumerate(recent_profile_facts[:4]):
        if not isinstance(fact, dict):
            raise RuntimeError(f"/api/apple/huddle continuity recent_profile_facts[{index}] is not an object")
        for key in ("id", "title", "summary"):
            if key not in fact:
                raise RuntimeError(f"/api/apple/huddle continuity recent_profile_facts[{index}] missing '{key}'")
    recent_first_light = continuity.get("recent_first_light")
    if not isinstance(recent_first_light, list):
        raise RuntimeError("/api/apple/huddle continuity recent_first_light is not a list")
    for index, moment in enumerate(recent_first_light[:4]):
        if not isinstance(moment, dict):
            raise RuntimeError(f"/api/apple/huddle continuity recent_first_light[{index}] is not an object")
        for key in ("id", "label", "summary"):
            if key not in moment:
                raise RuntimeError(f"/api/apple/huddle continuity recent_first_light[{index}] missing '{key}'")


def validate_action_contracts(payloads: dict[str, dict]) -> None:
    speak = require_mapping(payloads, "/api/apple/speak")
    for key in ("response", "agent", "speak", "display_text", "spoken_text", "presentation_mode"):
        if key not in speak:
            raise RuntimeError(f"/api/apple/speak missing '{key}'")

    device = require_mapping(payloads, "/api/apple/device/register")
    require_bool(device, "/api/apple/device/register", "registered")

    home_command = require_mapping(payloads, "/api/apple/home/command")
    for key in ("request_id", "status", "boundary_decision", "boundary_reason", "trust_zone", "authority_stage", "arena_status", "approval_mode"):
        if key not in home_command:
            raise RuntimeError(f"/api/apple/home/command missing '{key}'")

    presence = require_mapping(payloads, "/api/apple/presence")
    for key in ("event", "actor_id", "ts"):
        if key not in presence:
            raise RuntimeError(f"/api/apple/presence missing '{key}'")

    for path, expected in (
        ("/api/apple/approvals/req-1/approve", "approved"),
        ("/api/apple/approvals/req-1/reject", "rejected"),
        ("/api/apple/approvals/req-1/cancel", "cancelled"),
    ):
        data = require_mapping(payloads, path)
        if str(data.get("status") or "") != expected:
            raise RuntimeError(f"{path} expected status '{expected}'")

    calendar_store = require_mapping(payloads, "/api/apple/calendar")
    if "stored" not in calendar_store:
        raise RuntimeError("/api/apple/calendar missing 'stored'")

    for path in ("/api/apple/calendar/stage-prep", "/api/apple/calendar/events/cal-1/prepare"):
        data = require_mapping(payloads, path)
        for key in ("status", "title", "start", "location"):
            if key not in data:
                raise RuntimeError(f"{path} missing '{key}'")

    calendar_route = require_mapping(payloads, "/api/apple/calendar/events/cal-1/route")
    for key in (
        "request_id",
        "status",
        "event_id",
        "title",
        "location",
        "maps_url",
        "boundary_decision",
        "boundary_reason",
        "trust_zone",
        "authority_stage",
        "arena_status",
        "approval_mode",
    ):
        if key not in calendar_route:
            raise RuntimeError(f"/api/apple/calendar/events/cal-1/route missing '{key}'")

    reminders_store = require_mapping(payloads, "/api/apple/reminders")
    if "stored" not in reminders_store:
        raise RuntimeError("/api/apple/reminders missing 'stored'")

    for path, expected_action in (
        ("/api/apple/reminders/r1/complete", "complete"),
        ("/api/apple/reminders/r1/snooze", "snooze"),
    ):
        data = require_mapping(payloads, path)
        if str(data.get("status") or "") != "staged_for_review":
            raise RuntimeError(f"{path} expected status 'staged_for_review'")
        for key in ("request_id", "reminder", "performed_action", "boundary_decision", "boundary_reason", "trust_zone", "authority_stage", "arena_status", "approval_mode"):
            if key not in data:
                raise RuntimeError(f"{path} missing '{key}'")
        if str(data.get("performed_action") or "") != expected_action:
            raise RuntimeError(f"{path} expected performed_action '{expected_action}'")

    focus_store = require_mapping(payloads, "/api/apple/focus")
    if str(focus_store.get("status") or "") != "staged_for_review":
        raise RuntimeError("/api/apple/focus expected status 'staged_for_review'")
    for key in ("request_id", "status", "stored", "focus_active", "performed_action", "boundary_decision", "boundary_reason", "trust_zone", "authority_stage", "arena_status", "approval_mode"):
        if key not in focus_store:
            raise RuntimeError(f"/api/apple/focus missing '{key}'")
    if str(focus_store.get("performed_action") or "") != "apply_preset":
        raise RuntimeError("/api/apple/focus expected performed_action 'apply_preset'")

    for path in ("/api/apple/sound-alert", "/api/apple/vision/scan", "/api/apple/now-playing"):
        data = require_mapping(payloads, path)
        require_bool(data, path, "stored")

    for path in ("/api/apple/sound-alerts/sa-1/resolve", "/api/apple/vision/scans/vs-1/resolve"):
        data = require_mapping(payloads, path)
        for key in (
            "request_id",
            "status",
            "id",
            "resolved_at",
            "boundary_decision",
            "boundary_reason",
            "trust_zone",
            "authority_stage",
            "arena_status",
            "approval_mode",
        ):
            if key not in data:
                raise RuntimeError(f"{path} missing '{key}'")

    speak_push = require_mapping(payloads, "/api/apple/speak/push")
    if "sent" not in speak_push:
        raise RuntimeError("/api/apple/speak/push missing 'sent'")

    health_log = require_mapping(payloads, "/api/apple/health/log")
    if "logged" not in health_log:
        raise RuntimeError("/api/apple/health/log missing 'logged'")

    chronicle_capture = require_mapping(payloads, "/api/apple/chronicle/capture")
    require_bool(chronicle_capture, "/api/apple/chronicle/capture", "captured")
    if "entry_id" not in chronicle_capture:
        raise RuntimeError("/api/apple/chronicle/capture missing 'entry_id'")
    for path, expected in (
        ("/api/apple/chronicle/prayers/cp-1/pray", "prayed"),
        ("/api/apple/chronicle/prayers/cp-1/answer", "answered"),
    ):
        data = require_mapping(payloads, path)
        if str(data.get("status") or "") != expected:
            raise RuntimeError(f"{path} expected status '{expected}'")
        if "prayer_id" not in data:
            raise RuntimeError(f"{path} missing 'prayer_id'")
    chronicle_study = require_mapping(payloads, "/api/apple/chronicle/study/save")
    require_bool(chronicle_study, "/api/apple/chronicle/study/save", "captured")
    if "entry_id" not in chronicle_study:
        raise RuntimeError("/api/apple/chronicle/study/save missing 'entry_id'")

    faith_chat = require_mapping(payloads, "/api/apple/faith/chat")
    for key in ("reply", "agent_id", "agent_name"):
        if key not in faith_chat:
            raise RuntimeError(f"/api/apple/faith/chat missing '{key}'")

    lane_review = require_mapping(payloads, "/api/apple/stewardship-lanes/family-stewardship/stage-review")
    if str(lane_review.get("status") or "") != "review_staged":
        raise RuntimeError("/api/apple/stewardship-lanes/family-stewardship/stage-review expected status 'review_staged'")
    for key in ("request_id", "review_id", "performed_action", "lane_id", "lane_title", "review_surface", "packet_target", "boundary_decision", "boundary_reason", "trust_zone", "authority_stage", "arena_status", "approval_mode"):
        if key not in lane_review:
            raise RuntimeError(f"/api/apple/stewardship-lanes/family-stewardship/stage-review missing '{key}'")
    if str(lane_review.get("performed_action") or "") != "stage_lane_review":
        raise RuntimeError("/api/apple/stewardship-lanes/family-stewardship/stage-review expected performed_action 'stage_lane_review'")
    for path, expected_status, expected_action in (
        ("/api/apple/stewardship-reviews/stewardship-review-1/approve", "approved", "approve_stewardship_review"),
        ("/api/apple/stewardship-reviews/stewardship-review-1/route", "rerouted", "route_stewardship_review"),
        ("/api/apple/stewardship-reviews/stewardship-review-1/retire", "retired", "retire_stewardship_review"),
    ):
        data = require_mapping(payloads, path)
        if str(data.get("status") or "") != expected_status:
            raise RuntimeError(f"{path} expected status '{expected_status}'")
        for key in ("request_id", "review_id", "performed_action", "lane_id", "lane_title", "review_surface", "packet_target", "boundary_decision", "boundary_reason", "trust_zone", "authority_stage", "arena_status", "approval_mode"):
            if key not in data:
                raise RuntimeError(f"{path} missing '{key}'")
        if str(data.get("performed_action") or "") != expected_action:
            raise RuntimeError(f"{path} expected performed_action '{expected_action}'")
    for path, expected_status, expected_action in (
        ("/api/apple/governance-proposals/governance-family-stewardship/promote", "promoted", "promote_governance_proposal"),
        ("/api/apple/governance-proposals/governance-family-stewardship/dismiss", "dismissed", "dismiss_governance_proposal"),
    ):
        data = require_mapping(payloads, path)
        if str(data.get("status") or "") != expected_status:
            raise RuntimeError(f"{path} expected status '{expected_status}'")
        for key in ("proposal_id", "candidate_id", "title", "performed_action", "message", "rule_id"):
            if key not in data:
                raise RuntimeError(f"{path} missing '{key}'")
        if str(data.get("performed_action") or "") != expected_action:
            raise RuntimeError(f"{path} expected performed_action '{expected_action}'")

    for path, expected_action in (
        ("/api/apple/publishing/reviews/rev-1/approve", "approve"),
        ("/api/apple/publishing/reviews/rev-1/revise", "revise"),
    ):
        data = require_mapping(payloads, path)
        if str(data.get("status") or "") != "staged_for_review":
            raise RuntimeError(f"{path} expected status 'staged_for_review'")
        for key in ("request_id", "review", "performed_action", "boundary_decision", "boundary_reason", "trust_zone", "authority_stage", "arena_status", "approval_mode", "feedback"):
            if key not in data:
                raise RuntimeError(f"{path} missing '{key}'")
        if str(data.get("performed_action") or "") != expected_action:
            raise RuntimeError(f"{path} expected performed_action '{expected_action}'")

    huddle_start = require_mapping(payloads, "/api/apple/huddle/party-mode/start")
    if str(huddle_start.get("status") or "") != "staged_for_review":
        raise RuntimeError("/api/apple/huddle/party-mode/start expected status 'staged_for_review'")
    for key in ("request_id", "status", "performed_action", "boundary_decision", "boundary_reason", "trust_zone", "authority_stage", "arena_status", "approval_mode"):
        if key not in huddle_start:
            raise RuntimeError(f"/api/apple/huddle/party-mode/start missing '{key}'")
    if str(huddle_start.get("performed_action") or "") != "start_party_mode":
        raise RuntimeError("/api/apple/huddle/party-mode/start expected performed_action 'start_party_mode'")

    forge_save = require_mapping(payloads, "/api/apple/forge/save")
    require_bool(forge_save, "/api/apple/forge/save", "saved")
    if "id" not in forge_save:
        raise RuntimeError("/api/apple/forge/save missing 'id'")
    forge_project = require_mapping(payloads, "/api/apple/forge/projects")
    for key in ("id", "title", "status", "intake_type", "generated_models"):
        if key not in forge_project:
            raise RuntimeError(f"/api/apple/forge/projects missing '{key}'")
    forge_submit = require_mapping(payloads, "/api/apple/forge/submit")
    require_bool(forge_submit, "/api/apple/forge/submit", "queued")
    for key in ("job_id", "photo_count"):
        if key not in forge_submit:
            raise RuntimeError(f"/api/apple/forge/submit missing '{key}'")

    for path, expected in (
        ("/api/apple/systems/trust-zones/shared-email.stage/promote", "promoted"),
        ("/api/apple/systems/trust-zones/shared-email.stage/demote", "demoted"),
    ):
        data = require_mapping(payloads, path)
        if str(data.get("status") or "") != expected:
            raise RuntimeError(f"{path} expected status '{expected}'")
        for key in ("zone_id", "authority_stage", "approval_mode"):
            if key not in data:
                raise RuntimeError(f"{path} missing '{key}'")

    for path, expected in (
        ("/api/apple/systems/resource-arenas/gmail.shared.drafts/suspend", "suspended"),
        ("/api/apple/systems/resource-arenas/gmail.shared.drafts/resume", "active"),
    ):
        data = require_mapping(payloads, path)
        if str(data.get("status") or "") != expected:
            raise RuntimeError(f"{path} expected status '{expected}'")
        for key in ("arena_id", "linked_zone_id"):
            if key not in data:
                raise RuntimeError(f"{path} missing '{key}'")

    sandbox_execute = require_mapping(payloads, "/api/apple/systems/self-improvement/jobs/sj-1/sandbox-execute")
    require_bool(sandbox_execute, "/api/apple/systems/self-improvement/jobs/sj-1/sandbox-execute", "ok")
    require_bool(sandbox_execute, "/api/apple/systems/self-improvement/jobs/sj-1/sandbox-execute", "accepted")
    for key in ("mode", "job_id", "status", "message", "active_run_id", "queue_active_count"):
        if key not in sandbox_execute:
            raise RuntimeError(f"/api/apple/systems/self-improvement/jobs/sj-1/sandbox-execute missing '{key}'")
    sandbox_cancel = require_mapping(payloads, "/api/apple/systems/self-improvement/jobs/sj-1/sandbox-cancel")
    require_bool(sandbox_cancel, "/api/apple/systems/self-improvement/jobs/sj-1/sandbox-cancel", "ok")
    require_bool(sandbox_cancel, "/api/apple/systems/self-improvement/jobs/sj-1/sandbox-cancel", "accepted")
    for key in ("mode", "job_id", "status", "message", "active_run_id", "queue_active_count"):
        if key not in sandbox_cancel:
            raise RuntimeError(f"/api/apple/systems/self-improvement/jobs/sj-1/sandbox-cancel missing '{key}'")
    sandbox_recover = require_mapping(payloads, "/api/apple/systems/self-improvement/jobs/sj-1/sandbox-recover")
    require_bool(sandbox_recover, "/api/apple/systems/self-improvement/jobs/sj-1/sandbox-recover", "ok")
    require_bool(sandbox_recover, "/api/apple/systems/self-improvement/jobs/sj-1/sandbox-recover", "accepted")
    for key in ("mode", "job_id", "status", "message", "active_run_id", "queue_active_count"):
        if key not in sandbox_recover:
            raise RuntimeError(f"/api/apple/systems/self-improvement/jobs/sj-1/sandbox-recover missing '{key}'")

    vendor_sandbox_execute = require_mapping(payloads, "/api/apple/systems/self-improvement/jobs/vendor-prep:vp-1/sandbox-execute")
    require_bool(vendor_sandbox_execute, "/api/apple/systems/self-improvement/jobs/vendor-prep:vp-1/sandbox-execute", "ok")
    require_bool(vendor_sandbox_execute, "/api/apple/systems/self-improvement/jobs/vendor-prep:vp-1/sandbox-execute", "accepted")
    for key in ("mode", "job_id", "status", "message", "active_run_id", "queue_active_count"):
        if key not in vendor_sandbox_execute:
            raise RuntimeError(f"/api/apple/systems/self-improvement/jobs/vendor-prep:vp-1/sandbox-execute missing '{key}'")
    vendor_sandbox_cancel = require_mapping(payloads, "/api/apple/systems/self-improvement/jobs/vendor-prep:vp-1/sandbox-cancel")
    require_bool(vendor_sandbox_cancel, "/api/apple/systems/self-improvement/jobs/vendor-prep:vp-1/sandbox-cancel", "ok")
    require_bool(vendor_sandbox_cancel, "/api/apple/systems/self-improvement/jobs/vendor-prep:vp-1/sandbox-cancel", "accepted")
    for key in ("mode", "job_id", "status", "message", "active_run_id", "queue_active_count"):
        if key not in vendor_sandbox_cancel:
            raise RuntimeError(f"/api/apple/systems/self-improvement/jobs/vendor-prep:vp-1/sandbox-cancel missing '{key}'")
    vendor_sandbox_recover = require_mapping(payloads, "/api/apple/systems/self-improvement/jobs/vendor-prep:vp-1/sandbox-recover")
    require_bool(vendor_sandbox_recover, "/api/apple/systems/self-improvement/jobs/vendor-prep:vp-1/sandbox-recover", "ok")
    require_bool(vendor_sandbox_recover, "/api/apple/systems/self-improvement/jobs/vendor-prep:vp-1/sandbox-recover", "accepted")
    for key in ("mode", "job_id", "status", "message", "active_run_id", "queue_active_count"):
        if key not in vendor_sandbox_recover:
            raise RuntimeError(f"/api/apple/systems/self-improvement/jobs/vendor-prep:vp-1/sandbox-recover missing '{key}'")

    stewardship_sandbox_execute = require_mapping(payloads, "/api/apple/systems/self-improvement/jobs/stewardship-review:stewardship-review-1/sandbox-execute")
    require_bool(stewardship_sandbox_execute, "/api/apple/systems/self-improvement/jobs/stewardship-review:stewardship-review-1/sandbox-execute", "ok")
    require_bool(stewardship_sandbox_execute, "/api/apple/systems/self-improvement/jobs/stewardship-review:stewardship-review-1/sandbox-execute", "accepted")
    for key in ("mode", "job_id", "status", "message", "active_run_id", "queue_active_count"):
        if key not in stewardship_sandbox_execute:
            raise RuntimeError(f"/api/apple/systems/self-improvement/jobs/stewardship-review:stewardship-review-1/sandbox-execute missing '{key}'")
    stewardship_sandbox_cancel = require_mapping(payloads, "/api/apple/systems/self-improvement/jobs/stewardship-review:stewardship-review-1/sandbox-cancel")
    require_bool(stewardship_sandbox_cancel, "/api/apple/systems/self-improvement/jobs/stewardship-review:stewardship-review-1/sandbox-cancel", "ok")
    require_bool(stewardship_sandbox_cancel, "/api/apple/systems/self-improvement/jobs/stewardship-review:stewardship-review-1/sandbox-cancel", "accepted")
    for key in ("mode", "job_id", "status", "message", "active_run_id", "queue_active_count"):
        if key not in stewardship_sandbox_cancel:
            raise RuntimeError(f"/api/apple/systems/self-improvement/jobs/stewardship-review:stewardship-review-1/sandbox-cancel missing '{key}'")
    stewardship_sandbox_recover = require_mapping(payloads, "/api/apple/systems/self-improvement/jobs/stewardship-review:stewardship-review-1/sandbox-recover")
    require_bool(stewardship_sandbox_recover, "/api/apple/systems/self-improvement/jobs/stewardship-review:stewardship-review-1/sandbox-recover", "ok")
    require_bool(stewardship_sandbox_recover, "/api/apple/systems/self-improvement/jobs/stewardship-review:stewardship-review-1/sandbox-recover", "accepted")
    for key in ("mode", "job_id", "status", "message", "active_run_id", "queue_active_count"):
        if key not in stewardship_sandbox_recover:
            raise RuntimeError(f"/api/apple/systems/self-improvement/jobs/stewardship-review:stewardship-review-1/sandbox-recover missing '{key}'")

    for path, expected in (
        ("/api/apple/notifications/n1/seen", "seen"),
        ("/api/apple/notifications/n1/dismiss", "dismissed"),
    ):
        data = require_mapping(payloads, path)
        if str(data.get("status") or "") != expected:
            raise RuntimeError(f"{path} expected status '{expected}'")
        if not isinstance(data.get("notification"), dict):
            raise RuntimeError(f"{path} missing object field 'notification'")

    for path, expected in (
        ("/api/apple/notifications/n1/resolve", "staged_for_review"),
        ("/api/apple/notifications/n1/snooze", "staged_for_review"),
    ):
        data = require_mapping(payloads, path)
        if str(data.get("status") or "") != expected:
            raise RuntimeError(f"{path} expected status '{expected}'")
        for key in ("request_id", "notification", "performed_action", "boundary_decision", "boundary_reason", "trust_zone", "authority_stage", "arena_status", "approval_mode"):
            if key not in data:
                raise RuntimeError(f"{path} missing '{key}'")

    notification_action = require_mapping(payloads, "/api/apple/notifications/n1/action")
    for key in ("ok", "status", "notification", "performed_action"):
        if key not in notification_action:
            raise RuntimeError(f"/api/apple/notifications/n1/action missing '{key}'")


def fetch_http(base_url: str, path: str, *, method: str = "GET", body: dict | None = None) -> dict:
    from urllib.request import Request

    payload = None if body is None else json.dumps(body).encode("utf-8")
    request = Request(
        f"{base_url.rstrip('/')}{path}",
        data=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method=method,
    )
    with urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


def post_http(base_url: str, path: str, body: dict) -> dict:
    from urllib.request import Request

    payload = json.dumps(body).encode("utf-8")
    request = Request(
        f"{base_url.rstrip('/')}{path}",
        data=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    with urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_ssh(ssh_host: str, container: str, path: str, base_url: str) -> dict:
    full_url = f"{base_url.rstrip('/')}{path}"
    python_snippet = (
        "import json, sys, urllib.request; "
        "print(json.dumps(json.loads(urllib.request.urlopen(sys.argv[1]).read().decode('utf-8'))))"
    )
    remote = (
        f"docker exec {shlex.quote(container)} "
        f"python3 -c {shlex.quote(python_snippet)} {shlex.quote(full_url)}"
    )
    output = subprocess.check_output(["ssh", ssh_host, remote], text=True)
    return json.loads(output)


def fetch_all_ssh(
    *,
    ssh_host: str,
    container: str,
    base_url: str,
    paths: list[str],
    attempts: int = 15,
    delay_s: float = 2.0,
) -> dict[str, dict]:
    remote_script = """
import json
import sys
import time
import urllib.request

payload = json.loads(sys.stdin.read())
base_url = str(payload["base_url"]).rstrip("/")
paths = list(payload["paths"])
attempts = int(payload["attempts"])
delay_s = float(payload["delay_s"])

def fetch(path: str) -> dict:
    last_exc = None
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(base_url + path, timeout=10) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:  # pragma: no cover - exercised in live use
            last_exc = exc
            if attempt == attempts:
                raise
            time.sleep(delay_s)
    raise last_exc or RuntimeError(f"failed fetching {path}")

result = {}
for path in paths:
    result[path] = fetch(path)
print(json.dumps(result))
""".strip()

    payload = json.dumps(
        {
            "base_url": base_url,
            "paths": paths,
            "attempts": attempts,
            "delay_s": delay_s,
        }
    )
    remote = f"docker exec -i {shlex.quote(container)} python3 -c {shlex.quote(remote_script)}"
    completed = subprocess.run(
        ["ssh", ssh_host, remote],
        input=payload,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.strip() or completed.stdout.strip() or "unknown ssh verification failure"
        raise RuntimeError(stderr)
    return json.loads(completed.stdout)


def fetch_with_retry(*, use_ssh: bool, path: str, base_url: str, ssh_host: str | None, container: str, attempts: int = 15, delay_s: float = 2.0) -> dict:
    last_exc: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            if use_ssh:
                return fetch_ssh(ssh_host or "", container, path, base_url)
            return fetch_http(base_url, path)
        except HTTPError as exc:  # pragma: no cover - exercised in live use
            if path == "/api/apple/systems/admin-summary" and exc.code in {404, 405}:
                try:
                    fetch_http(base_url, path, method="POST", body={})
                except Exception:
                    last_exc = exc
                else:
                    raise RuntimeError(
                        "/api/apple/systems/admin-summary contract drift: GET failed with "
                        f"HTTP {exc.code}, but POST returned a payload. The live edge is out "
                        "of sync with the documented GET contract."
                    ) from exc
            else:
                last_exc = exc
        except Exception as exc:  # pragma: no cover - exercised in live use
            last_exc = exc
        if attempt == attempts:
            break
        time.sleep(delay_s)
    raise last_exc or RuntimeError(f"failed fetching {path}")


def post_with_retry(*, path: str, body: dict, base_url: str, attempts: int = 15, delay_s: float = 2.0) -> dict:
    last_exc: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return post_http(base_url, path, body)
        except Exception as exc:  # pragma: no cover - exercised in live use
            last_exc = exc
            if attempt == attempts:
                break
            time.sleep(delay_s)
    raise last_exc or RuntimeError(f"failed posting {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8787")
    parser.add_argument("--ssh-host", help="Optional SSH host for remote container probing.")
    parser.add_argument("--container", default="jarvis-family-jarvis-1")
    parser.add_argument("--attempts", type=int, default=15)
    parser.add_argument("--delay-s", type=float, default=2.0)
    parser.add_argument("--keep-fixture", action="store_true")
    parser.add_argument("--exercise-actions", action="store_true")
    args = parser.parse_args()

    use_ssh = bool(args.ssh_host)

    payloads: dict[str, dict] = {}
    if use_ssh:
        path_map = {key: path for key, path in ENDPOINTS}
        try:
            fetched = fetch_all_ssh(
                ssh_host=args.ssh_host or "",
                container=args.container,
                base_url=args.base_url,
                paths=list(path_map.values()),
                attempts=args.attempts,
                delay_s=args.delay_s,
            )
            for key, path in ENDPOINTS:
                payloads[key] = fetched[path]
        except Exception as exc:  # pragma: no cover - exercised in live use
            print(f"failed fetching apple payloads over ssh: {exc}", file=sys.stderr)
            return 1
    else:
        for key, path in ENDPOINTS:
            try:
                payloads[key] = fetch_with_retry(
                    use_ssh=False,
                    path=path,
                    base_url=args.base_url,
                    ssh_host=args.ssh_host,
                    container=args.container,
                    attempts=args.attempts,
                    delay_s=args.delay_s,
                )
            except Exception as exc:  # pragma: no cover - exercised in live use
                print(f"failed fetching {path}: {exc}", file=sys.stderr)
                return 1

    try:
        validate_phase_one_contracts(payloads)
    except Exception as exc:  # pragma: no cover - exercised in live use
        print(f"phase 1 contract validation failed: {exc}", file=sys.stderr)
        return 1

    if args.exercise_actions:
        if use_ssh:
            print("action contract verification is not supported over ssh yet", file=sys.stderr)
            return 1
        action_payloads: dict[str, dict] = {}
        for key, path, body in ACTION_ENDPOINTS:
            try:
                action_payloads[key] = post_with_retry(
                    path=path,
                    body=body,
                    base_url=args.base_url,
                    attempts=args.attempts,
                    delay_s=args.delay_s,
                )
            except Exception as exc:  # pragma: no cover - exercised in live use
                print(f"failed posting {path}: {exc}", file=sys.stderr)
                return 1
        try:
            validate_action_contracts(action_payloads)
        except Exception as exc:  # pragma: no cover - exercised in live use
            print(f"action contract validation failed: {exc}", file=sys.stderr)
            return 1

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".json",
        prefix="jarvis-apple-payloads-",
        delete=False,
    ) as fh:
        json.dump(payloads, fh)
        fixture_path = fh.name

    env = dict(os.environ)
    env["JARVIS_APPLE_PAYLOAD_FIXTURE"] = fixture_path
    try:
        subprocess.run(
            ["swift", "test"],
            cwd=JARVIS_APPLE_DIR,
            env=env,
            check=True,
        )
        print(f"apple contract decode passed using fixture {fixture_path}")
        return 0
    finally:
        if not args.keep_fixture:
            try:
                Path(fixture_path).unlink(missing_ok=True)
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
