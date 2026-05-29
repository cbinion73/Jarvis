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
from urllib.request import urlopen

REPO_ROOT = Path(__file__).resolve().parents[1]
JARVIS_APPLE_DIR = REPO_ROOT / "JarvisApple"

ENDPOINTS: list[tuple[str, str]] = [
    ("/api/apple/status", "/api/apple/status"),
    ("/api/apple/app-state", "/api/apple/app-state"),
    ("/api/apple/calendar/state", "/api/apple/calendar/state"),
    ("/api/apple/reminders/state", "/api/apple/reminders/state"),
    ("/api/apple/focus-state", "/api/apple/focus-state"),
    ("/api/apple/notifications", "/api/apple/notifications"),
    ("/api/apple/events/recent", "/api/apple/events/recent"),
    ("/api/apple/weather", "/api/apple/weather"),
    ("/api/apple/navigation/locations", "/api/apple/navigation/locations"),
    (
        "/api/apple/navigation/route?origin=8384%20Riley%20Rd%2C%20Alexandria%2C%20KY%2041001&destination=Cincinnati%2C%20OH",
        "/api/apple/navigation/route?origin=8384%20Riley%20Rd%2C%20Alexandria%2C%20KY%2041001&destination=Cincinnati%2C%20OH",
    ),
    ("/api/apple/briefing?actor=chris", "/api/apple/briefing?actor=chris"),
    ("/api/apple/needs", "/api/apple/needs"),
    ("/api/apple/health/summary?actor=chris", "/api/apple/health/summary?actor=chris"),
    ("/api/apple/home/state", "/api/apple/home/state"),
    ("/api/apple/catalyst", "/api/apple/catalyst"),
    ("/api/apple/chronicle", "/api/apple/chronicle"),
    ("/api/apple/faith?actor=chris", "/api/apple/faith?actor=chris"),
    ("/api/apple/publishing", "/api/apple/publishing"),
    ("/api/apple/huddle", "/api/apple/huddle"),
    ("/api/apple/forge", "/api/apple/forge"),
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


def validate_phase_one_contracts(payloads: dict[str, dict]) -> None:
    briefing = require_mapping(payloads, "/api/apple/briefing?actor=chris")
    command_items = require_list(briefing, "/api/apple/briefing?actor=chris", "command_items")
    for index, item in enumerate(command_items):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/briefing?actor=chris command_items[{index}] is not an object")
        for key in ("id", "title", "detail", "priority", "kind"):
            if key not in item:
                raise RuntimeError(f"/api/apple/briefing?actor=chris command_items[{index}] missing '{key}'")

    home_state = require_mapping(payloads, "/api/apple/home/state")
    action_items = require_list(home_state, "/api/apple/home/state", "action_items")
    home_context = home_state.get("home_context")
    if not isinstance(home_context, dict):
        raise RuntimeError("/api/apple/home/state missing object field 'home_context'")
    for key in ("agenda", "attention", "projects"):
        if key not in home_context:
            raise RuntimeError(f"/api/apple/home/state home_context missing '{key}'")
    for index, item in enumerate(action_items):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/home/state action_items[{index}] is not an object")
        for key in ("id", "title", "detail", "command", "service", "emphasis"):
            if key not in item:
                raise RuntimeError(f"/api/apple/home/state action_items[{index}] missing '{key}'")

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
            for key in ("id", "title", "start", "end", "location", "calendar", "all_day", "prep_window_open", "route_ready"):
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
    posture = focus_state.get("interruption_posture")
    if not isinstance(posture, dict):
        raise RuntimeError("/api/apple/focus-state missing object field 'interruption_posture'")
    for key in ("mode", "label", "reason", "recommended_delivery", "quiet_hours", "hour_local"):
        if key not in posture:
            raise RuntimeError(f"/api/apple/focus-state interruption_posture missing '{key}'")

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
    for key in ("synced", "synced_at", "count", "open_items", "overdue_items", "due_soon_items", "priority_items", "attention_flags"):
        if key not in reminders_state:
            raise RuntimeError(f"/api/apple/reminders/state missing '{key}'")
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
        if "allowed_actions" not in item:
            raise RuntimeError(f"/api/apple/needs items[{index}] missing 'allowed_actions'")

    notifications_wrapper = require_mapping(payloads, "/api/apple/notifications")
    notifications = notifications_wrapper.get("notifications")
    if not isinstance(notifications, list):
        raise RuntimeError("/api/apple/notifications missing list field 'notifications'")
    for index, item in enumerate(notifications[:3]):
        if not isinstance(item, dict):
            raise RuntimeError(f"/api/apple/notifications notifications[{index}] is not an object")
        for key in ("id", "category", "title", "status", "created_at", "available_actions", "delivery_mode", "decision_reason", "posture_snapshot"):
            if key not in item:
                raise RuntimeError(f"/api/apple/notifications notifications[{index}] missing '{key}'")

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

    chronicle = require_mapping(payloads, "/api/apple/chronicle")
    context = chronicle.get("context")
    if not isinstance(context, dict):
        raise RuntimeError("/api/apple/chronicle missing object field 'context'")
    for key in ("active_prayers", "top_themes", "total_entries", "active_prayer_count", "answered_prayer_count"):
        if key not in context:
            raise RuntimeError(f"/api/apple/chronicle context missing '{key}'")
    patterns = chronicle.get("patterns")
    if not isinstance(patterns, dict):
        raise RuntimeError("/api/apple/chronicle missing object field 'patterns'")
    for key in ("window_days", "total_recent_entries", "entry_type_breakdown", "recurring_themes", "prayer_arc", "writing_streak_days"):
        if key not in patterns:
            raise RuntimeError(f"/api/apple/chronicle patterns missing '{key}'")

    publishing = require_mapping(payloads, "/api/apple/publishing")
    for key in ("projects", "revenue_summary", "upcoming", "pending_reviews", "pending_reviews_count", "launch_control", "action_items"):
        if key not in publishing:
            raise RuntimeError(f"/api/apple/publishing missing '{key}'")
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

    huddle = require_mapping(payloads, "/api/apple/huddle")
    for key in ("reports", "blockers", "highlights", "approvals", "approvals_count", "total_active_work"):
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


def fetch_http(base_url: str, path: str) -> dict:
    with urlopen(f"{base_url.rstrip('/')}{path}") as response:
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


def fetch_with_retry(*, use_ssh: bool, path: str, base_url: str, ssh_host: str | None, container: str, attempts: int = 15, delay_s: float = 2.0) -> dict:
    last_exc: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            if use_ssh:
                return fetch_ssh(ssh_host or "", container, path, base_url)
            return fetch_http(base_url, path)
        except Exception as exc:  # pragma: no cover - exercised in live use
            last_exc = exc
            if attempt == attempts:
                break
            time.sleep(delay_s)
    raise last_exc or RuntimeError(f"failed fetching {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8787")
    parser.add_argument("--ssh-host", help="Optional SSH host for remote container probing.")
    parser.add_argument("--container", default="jarvis-family-jarvis-1")
    parser.add_argument("--keep-fixture", action="store_true")
    args = parser.parse_args()

    use_ssh = bool(args.ssh_host)

    payloads: dict[str, dict] = {}
    for key, path in ENDPOINTS:
        try:
            payloads[key] = fetch_with_retry(
                use_ssh=use_ssh,
                path=path,
                base_url=args.base_url,
                ssh_host=args.ssh_host,
                container=args.container,
            )
        except Exception as exc:  # pragma: no cover - exercised in live use
            print(f"failed fetching {path}: {exc}", file=sys.stderr)
            return 1

    try:
        validate_phase_one_contracts(payloads)
    except Exception as exc:  # pragma: no cover - exercised in live use
        print(f"phase 1 contract validation failed: {exc}", file=sys.stderr)
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
