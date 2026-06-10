from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any
import urllib.error
import urllib.request

from .health_bridge import get_latest as get_latest_health_snapshot
from .reminders import pending_reminders


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _safe_load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _safe_load_json_list(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return [item for item in payload if isinstance(item, dict)] if isinstance(payload, list) else []


def _safe_mtime_iso(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()
    except OSError:
        return ""


def _parse_iso(value: object) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _age_seconds(value: object) -> float | None:
    parsed = _parse_iso(value)
    if parsed is None:
        return None
    return max(0.0, (_now_utc() - parsed).total_seconds())


def _age_hours(value: object) -> float | None:
    age = _age_seconds(value)
    if age is None:
        return None
    return round(age / 3600, 2)


def _status_for_age(
    value: object,
    *,
    warn_after_seconds: int,
    fail_after_seconds: int,
) -> str:
    age = _age_seconds(value)
    if age is None:
        return "blocked"
    if age > fail_after_seconds:
        return "blocked"
    if age > warn_after_seconds:
        return "watch"
    return "ready"


def _probe_json(url: str, *, timeout: int = 6) -> dict[str, Any]:
    target = str(url or "").strip()
    if not target:
        return {"ok": False, "url": "", "detail": "No URL configured."}
    try:
        request = urllib.request.Request(target, method="GET")
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            payload = json.loads(raw) if raw else {}
        return {"ok": True, "url": target, "payload": payload, "detail": ""}
    except urllib.error.URLError as exc:
        return {"ok": False, "url": target, "payload": {}, "detail": str(exc).strip()}
    except Exception as exc:  # pragma: no cover - defensive guard
        return {"ok": False, "url": target, "payload": {}, "detail": str(exc).strip()}


def _service_state(*, required: bool, installed: bool, healthy: bool, configured: bool = True) -> str:
    if required and (not configured or not installed or not healthy):
        return "blocked"
    if installed and healthy and configured:
        return "ready"
    if configured or installed:
        return "watch"
    return "watch" if not required else "blocked"


def _summarise_accounts(summary: dict[str, Any]) -> tuple[int, list[str]]:
    connected: list[str] = []
    for item in list(summary.get("accounts") or []):
        if not isinstance(item, dict):
            continue
        status = item.get("status") or {}
        if not isinstance(status, dict) or not status.get("connected"):
            continue
        account = item.get("account") or {}
        if isinstance(account, dict):
            label = str(account.get("label") or account.get("owner_display_name") or account.get("account_id") or "account").strip()
        else:
            label = "account"
        connected.append(label)
    return len(connected), connected


def _profile_counts(profile: dict[str, Any], keys: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for key in keys:
        value = profile.get(key)
        counts[key] = len(value) if isinstance(value, list) else 0
    return counts


def _perception_feed_summary(repo_root: Path, *, warn_after_hours: int, fail_after_hours: int) -> dict[str, Any]:
    perception_root = repo_root / "data" / "perception"
    feeds = [
        "camera_events.json",
        "presence_events.json",
        "phone_presence_events.json",
        "microphone_events.json",
        "vision_observations.json",
        "environmental_anomalies.json",
        "object_events.json",
    ]
    records: list[dict[str, Any]] = []
    states: list[str] = []
    warn_seconds = warn_after_hours * 3600
    fail_seconds = fail_after_hours * 3600
    for name in feeds:
        path = perception_root / name
        updated_at = _safe_mtime_iso(path)
        state = _status_for_age(updated_at, warn_after_seconds=warn_seconds, fail_after_seconds=fail_seconds) if path.exists() else "blocked"
        records.append(
            {
                "feed": name,
                "path": str(path),
                "exists": path.exists(),
                "updated_at": updated_at,
                "age_hours": _age_hours(updated_at),
                "state": state,
            }
        )
        states.append(state)
    overall = "blocked" if "blocked" in states else ("watch" if "watch" in states else "ready")
    return {"state": overall, "feeds": records}


def _health_sync_summary(*, warn_after_hours: int, fail_after_hours: int) -> dict[str, Any]:
    latest = get_latest_health_snapshot() or {}
    updated_at = str(latest.get("updated_at", "")).strip()
    state = _status_for_age(
        updated_at,
        warn_after_seconds=warn_after_hours * 3600,
        fail_after_seconds=fail_after_hours * 3600,
    ) if updated_at else "blocked"
    return {
        "state": state,
        "latest_date": str(latest.get("date", "")).strip(),
        "updated_at": updated_at,
        "age_hours": _age_hours(updated_at),
        "source": str(latest.get("source", "")).strip(),
        "metric_count": len([key for key in latest.keys() if key not in {"date", "source", "updated_at"}]),
    }


def _build_deployment_context(repo_root: Path) -> dict[str, Any]:
    """Detect deployment environment: Docker (Hetzner production) vs local dev vs CI."""
    in_docker = Path("/.dockerenv").exists() or os.environ.get("DOCKER_CONTAINER") == "1"
    in_ci = bool(os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"))
    hetzner_host = os.environ.get("HETZNER_HOST", "")
    data_path = os.environ.get("DATA_PATH", "/app/data" if in_docker else str(repo_root / "data"))

    if in_ci:
        env = "ci"
        label = "GitHub Actions CI"
        note = "Running in CI — not production."
    elif in_docker:
        env = "docker"
        label = "Docker (Hetzner production)"
        note = (
            "Running in Docker. Production stack: jarvis + chronicle + ghostwritr + "
            "nginx + cloudflared + postgres + redis. Data volume: jarvis_data at /app/data. "
            "Deployment: push to main → GitHub Actions → SSH → docker compose up -d --build jarvis."
        )
    else:
        env = "local"
        label = "Local dev (macOS)"
        note = (
            "Running locally. This is a dev/test environment, NOT production. "
            "Production runs on Hetzner VPS via Docker Compose."
        )

    services_expected = ["jarvis", "chronicle", "ghostwritr", "nginx", "cloudflared", "postgres", "redis"] if in_docker else []

    return {
        "env": env,
        "label": label,
        "in_docker": in_docker,
        "in_ci": in_ci,
        "hetzner_host": hetzner_host,
        "data_path": data_path,
        "services_expected": services_expected,
        "note": note,
    }


def build_runtime_posture_snapshot(runtime: Any) -> dict[str, Any]:
    repo_root = Path.cwd()
    config = runtime.config
    profile_path = Path(getattr(config, "runtime_profile_path", repo_root / "household" / "jarvis_runtime_profile.example.json"))
    profile = _safe_load_json(profile_path)
    launch_agents_dir = Path.home() / "Library" / "LaunchAgents"
    guardian = runtime.guardian_status_snapshot()
    guardian_state = guardian.get("status") if isinstance(guardian.get("status"), dict) else {}
    guardian_generated_at = str(guardian_state.get("generated_at", "")).strip()
    guardian_repo_root = str((guardian_state.get("guardian") or {}).get("repo_root", "")).strip() if isinstance(guardian_state, dict) else ""

    service_runtime = runtime.service_runtime_snapshot(include_probe=True)
    google_summary = runtime.google_workspace_summary()
    microsoft_summary = runtime.microsoft_graph_summary()
    family_calendar = runtime.family_calendar_summary()
    openviking = runtime.openviking_status()

    thresholds = profile.get("freshness") if isinstance(profile.get("freshness"), dict) else {}
    guardian_warn = int(thresholds.get("guardian_warn_after_seconds", 180) or 180)
    guardian_fail = int(thresholds.get("guardian_fail_after_seconds", 900) or 900)
    reminder_warn_days = int(thresholds.get("reminder_warn_after_days", 7) or 7)
    reminder_fail_days = int(thresholds.get("reminder_fail_after_days", 30) or 30)
    perception_warn = int(thresholds.get("perception_warn_after_hours", 24) or 24)
    perception_fail = int(thresholds.get("perception_fail_after_hours", 72) or 72)
    workshop_warn = int(thresholds.get("workshop_warn_after_days", 14) or 14)
    workshop_fail = int(thresholds.get("workshop_fail_after_days", 45) or 45)
    health_warn = int(thresholds.get("health_warn_after_hours", 24) or 24)
    health_fail = int(thresholds.get("health_fail_after_hours", 72) or 72)

    runtime_plan = profile.get("runtime") if isinstance(profile.get("runtime"), dict) else {}
    services = runtime_plan.get("services") if isinstance(runtime_plan.get("services"), list) else []
    if not services:
        services = [
            {
                "label": "com.jarvis.runtime",
                "required": True,
                "health_url": "http://127.0.0.1:8787/health",
                "template": "ops/launchd/com.jarvis.runtime.plist.template",
            },
            {
                "label": "com.jarvis.guardian",
                "required": True,
                "template": "ops/launchd/com.jarvis.guardian.plist.template",
            },
            {
                "label": "com.jarvis.assistant-autonomy",
                "required": True,
                "template": "ops/launchd/com.jarvis.assistant-autonomy.plist.template",
            },
            {
                "label": "com.jarvis.openviking",
                "required": False,
                "health_url": "http://127.0.0.1:1933/health",
                "template": "ops/launchd/com.jarvis.openviking.plist.template",
            },
        ]

    service_rows: list[dict[str, Any]] = []
    service_states: list[str] = []
    for entry in services:
        if not isinstance(entry, dict):
            continue
        label = str(entry.get("label", "")).strip()
        if not label:
            continue
        required = bool(entry.get("required", False))
        plist_name = str(entry.get("plist_name", f"{label}.plist")).strip() or f"{label}.plist"
        installed_path = launch_agents_dir / plist_name
        template_path = repo_root / str(entry.get("template", "")).strip() if str(entry.get("template", "")).strip() else None
        health_url = str(entry.get("health_url", "")).strip()
        configured = True
        healthy = False
        health_detail = ""
        if label == "com.jarvis.runtime":
            healthy = bool(service_runtime.get("live_probe", {}).get("ok"))
            health_detail = str(service_runtime.get("live_probe", {}).get("detail", "")).strip()
        elif label == "com.jarvis.openviking":
            configured = bool(openviking.get("enabled"))
            healthy = bool(openviking.get("ok"))
            health_detail = str(openviking.get("detail", "")).strip()
        elif label == "com.jarvis.guardian":
            healthy = guardian.get("active", False) and _status_for_age(
                guardian_generated_at,
                warn_after_seconds=guardian_warn,
                fail_after_seconds=guardian_fail,
            ) != "blocked"
            health_detail = f"last snapshot {guardian_generated_at}" if guardian_generated_at else "guardian has not written a snapshot yet"
        else:
            healthy = installed_path.exists()
            if health_url:
                probe = _probe_json(health_url)
                healthy = bool(probe.get("ok"))
                health_detail = str(probe.get("detail", "")).strip()

        state = _service_state(
            required=required,
            installed=installed_path.exists(),
            healthy=healthy,
            configured=configured,
        )
        service_rows.append(
            {
                "label": label,
                "required": required,
                "purpose": str(entry.get("purpose", "")).strip(),
                "installed": installed_path.exists(),
                "installed_path": str(installed_path),
                "template_path": str(template_path) if template_path else "",
                "template_exists": bool(template_path and template_path.exists()),
                "health_url": health_url,
                "healthy": healthy,
                "configured": configured,
                "state": state,
                "detail": health_detail,
            }
        )
        service_states.append(state)

    reminders_path = Path.home() / ".jarvis" / "reminders.json"
    reminders_updated_at = _safe_mtime_iso(reminders_path)
    reminder_state = _status_for_age(
        reminders_updated_at,
        warn_after_seconds=reminder_warn_days * 86400,
        fail_after_seconds=reminder_fail_days * 86400,
    ) if reminders_path.exists() else "watch"
    pending = pending_reminders()

    home_profile = _safe_load_json(config.home_profile_path)
    perception_profile = _safe_load_json(config.perception_profile_path)
    workshop_profile = _safe_load_json(config.workshop_profile_path)

    google_connected_count, google_connected_labels = _summarise_accounts(google_summary)
    microsoft_connected_count, microsoft_connected_labels = _summarise_accounts(microsoft_summary)
    calendar_state = "ready" if family_calendar.get("configured") and not family_calendar.get("error") else "blocked"
    home_state = "ready" if runtime.home_support.adapter.live else ("watch" if config.home_assistant_url else "blocked")

    perception_feeds = _perception_feed_summary(
        repo_root,
        warn_after_hours=perception_warn,
        fail_after_hours=perception_fail,
    )

    workshop_inventory = list(workshop_profile.get("inventory") or []) if isinstance(workshop_profile.get("inventory"), list) else []
    workshop_risk = [
        item for item in workshop_inventory
        if str(item.get("status", "")).strip().lower() in {"watch", "restock"}
    ]
    workshop_profile_updated_at = _safe_mtime_iso(config.workshop_profile_path)
    workshop_state = _status_for_age(
        workshop_profile_updated_at,
        warn_after_seconds=workshop_warn * 86400,
        fail_after_seconds=workshop_fail * 86400,
    ) if config.workshop_profile_path.exists() else "blocked"

    health_sync = _health_sync_summary(warn_after_hours=health_warn, fail_after_hours=health_fail)

    deployment_drift = service_runtime.get("drift", {}) if isinstance(service_runtime.get("drift"), dict) else {}
    deployment_state = "ready"
    if any(bool(deployment_drift.get(key)) for key in ("startup_vs_disk", "live_probe_vs_disk", "live_probe_vs_startup")):
        deployment_state = "watch"
    if service_runtime.get("live_probe", {}).get("ok") is False:
        deployment_state = "blocked"

    guardian_state_label = _status_for_age(
        guardian_generated_at,
        warn_after_seconds=guardian_warn,
        fail_after_seconds=guardian_fail,
    ) if guardian.get("active") else "blocked"

    sections = [
        guardian_state_label,
        deployment_state,
        "blocked" if "blocked" in service_states else ("watch" if "watch" in service_states else "ready"),
        calendar_state,
        reminder_state,
        home_state,
        perception_feeds.get("state", "blocked"),
        workshop_state,
        str(health_sync.get("state", "blocked")),
    ]
    overall_state = "blocked" if "blocked" in sections else ("watch" if "watch" in sections else "ready")

    durability = profile.get("durability") if isinstance(profile.get("durability"), dict) else {}
    integrations = profile.get("integrations") if isinstance(profile.get("integrations"), dict) else {}
    push_path = profile.get("push_path") if isinstance(profile.get("push_path"), dict) else {}
    devices = profile.get("devices") if isinstance(profile.get("devices"), dict) else {}

    return {
        "generated_at": _now_utc().isoformat(),
        "state": overall_state,
        "profile": {
            "path": str(profile_path),
            "exists": profile_path.exists(),
            "host_alias": str((profile.get("host") or {}).get("alias", "")).strip() if isinstance(profile.get("host"), dict) else "",
            "role": str((profile.get("host") or {}).get("role", "")).strip() if isinstance(profile.get("host"), dict) else "",
        },
        "host": {
            "repo_root": str(repo_root),
            "cwd": str(Path.cwd()),
            "platform": os.uname().sysname,
            "guardian_repo_root": guardian_repo_root,
            "guardian_repo_matches_checkout": bool(guardian_repo_root) and guardian_repo_root == str(repo_root),
        },
        "runtime": {
            "service_role": str(service_runtime.get("role", "")).strip(),
            "runtime_health": service_runtime.get("live_probe", {}),
            "hosted_health": service_runtime.get("hosted_probe", {}),
            "build_drift": deployment_drift,
            "state": deployment_state,
        },
        "guardian": {
            "active": bool(guardian.get("active")),
            "generated_at": guardian_generated_at,
            "age_seconds": _age_seconds(guardian_generated_at),
            "state": guardian_state_label,
            "recent_events": guardian.get("recent_events", []),
            "consecutive_runtime_failures": int(guardian_state.get("consecutive_runtime_failures", 0) or 0),
        },
        "deployment": _build_deployment_context(repo_root),
        "launchd": {
            "note": "local-only — not applicable in Docker production on Hetzner",
            "install_script": str(repo_root / "ops" / "install_launchd_services.sh"),
            "launch_agents_dir": str(launch_agents_dir),
            "services": service_rows,
            "state": "blocked" if "blocked" in service_states else ("watch" if "watch" in service_states else "ready"),
        },
        "durability": {
            "power": durability.get("power", {}),
            "network": durability.get("network", {}),
            "storage": durability.get("storage", {}),
            "recovery": durability.get("recovery", {}),
            "push_path": push_path,
        },
        "integrations": {
            "doctrine": integrations,
            "calendars": {
                "state": calendar_state,
                "family_calendar": family_calendar,
                "google_connected_accounts": google_connected_count,
                "google_connected_labels": google_connected_labels,
                "microsoft_connected_accounts": microsoft_connected_count,
                "microsoft_connected_labels": microsoft_connected_labels,
            },
            "reminders": {
                "state": reminder_state,
                "path": str(reminders_path),
                "exists": reminders_path.exists(),
                "updated_at": reminders_updated_at,
                "age_hours": _age_hours(reminders_updated_at),
                "pending_count": len(pending),
                "truth": "Persistent local queue is real; mirrored reminder providers still need explicit live wiring.",
            },
            "home_automation": {
                "state": home_state,
                "home_assistant_live": bool(runtime.home_support.adapter.live),
                "profile_path": str(config.home_profile_path),
                "counts": _profile_counts(home_profile, ["scenes", "lights", "switches", "climate", "locks", "doors", "garage", "leakSensors"]),
            },
            "perception": {
                "state": perception_feeds.get("state", "blocked"),
                "profile_path": str(config.perception_profile_path),
                "counts": _profile_counts(perception_profile, ["microphones", "presenceSensors", "phonePresence", "cameras", "privacyZones"]),
                "feeds": perception_feeds.get("feeds", []),
            },
            "workshop": {
                "state": workshop_state,
                "profile_path": str(config.workshop_profile_path),
                "updated_at": workshop_profile_updated_at,
                "age_hours": _age_hours(workshop_profile_updated_at),
                "counts": _profile_counts(workshop_profile, ["printers", "materials", "safetyInterlocks", "vendorTargets", "inventory"]),
                "inventory_attention": len(workshop_risk),
                "inventory_attention_items": [str(item.get("name", "")).strip() for item in workshop_risk[:6]],
            },
            "health_sync": health_sync,
        },
        "devices": devices,
    }
