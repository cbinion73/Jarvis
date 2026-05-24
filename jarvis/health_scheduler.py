"""
health_scheduler.py — JARVIS Autonomous Daily Steward

Scheduled health jobs for Chris's personal health AI:
  - Morning brief (06:00 daily)
  - Drift checks (every 6 hours)
  - Weekly council (Sunday 07:00)
  - Prediction scorer (daily)
  - Pre-appointment alerts (7-day advance)

All async functions use asyncio properly.
All internal imports are wrapped in try/except ImportError for resilience.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_HEALTH_DIR = Path.home() / ".jarvis" / "health"
_HEALTH_STATE_PATH   = _HEALTH_DIR / "chris_health_state.json"
_DAY_CARD_PATH       = _HEALTH_DIR / "day_card.json"
_MORNING_BRIEF_PATH  = _HEALTH_DIR / "morning_brief.json"
_APPOINTMENTS_PATH   = _HEALTH_DIR / "appointments.json"
_PREDICTIONS_PATH    = _HEALTH_DIR / "twin_predictions.jsonl"
_SCHEDULE_CONFIG_PATH = _HEALTH_DIR / "schedule_config.json"
_SCHEDULE_STATUS_PATH = _HEALTH_DIR / "schedule_status.json"

# ---------------------------------------------------------------------------
# Default schedule config
# ---------------------------------------------------------------------------

_DEFAULT_SCHEDULE_CONFIG: dict[str, Any] = {
    "morning_brief":        {"enabled": True,  "hour": 6,       "minute": 0},
    "drift_check":          {"enabled": True,  "interval_hours": 6},
    "weekly_council":       {"enabled": True,  "day_of_week": "sunday", "hour": 7},
    "prediction_scorer":    {"enabled": True,  "interval_days": 1},
    "pre_appointment_check":{"enabled": True,  "days_advance": 7},
}

# Default appointment list (Dr. Wenk Nov 13)
_DEFAULT_APPOINTMENTS: list[dict[str, Any]] = [
    {
        "id": "apt-001",
        "provider": "Dr. Susan Wenk",
        "type": "Primary Care",
        "date": "2026-11-13",
        "time": "10:00",
        "location": "Primary Care Office",
        "prep_required": True,
        "outcomes": None,
    }
]

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _ensure_health_dir() -> None:
    """Create ~/.jarvis/health directory if it does not exist."""
    _HEALTH_DIR.mkdir(parents=True, exist_ok=True)


def _load_json(path: Path, default: Any = None) -> Any:
    """Load JSON from *path*, returning *default* if missing or corrupt."""
    try:
        if path.exists():
            return json.loads(path.read_text())
    except Exception as exc:
        log.warning("Failed to read %s: %s", path, exc)
    return default if default is not None else {}


def _save_json(path: Path, data: Any, *, indent: int = 2) -> None:
    """Atomically save *data* as JSON to *path*."""
    _ensure_health_dir()
    tmp = path.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(data, indent=indent, default=str))
        tmp.replace(path)
    except Exception as exc:
        log.error("Failed to write %s: %s", path, exc)


def _load_health_state() -> dict:
    """Load Chris's full health state JSON."""
    return _load_json(_HEALTH_STATE_PATH, {})


def _load_schedule_config() -> dict:
    """Load schedule config, creating defaults if the file is missing."""
    _ensure_health_dir()
    if not _SCHEDULE_CONFIG_PATH.exists():
        _save_json(_SCHEDULE_CONFIG_PATH, _DEFAULT_SCHEDULE_CONFIG)
        return _DEFAULT_SCHEDULE_CONFIG.copy()
    cfg = _load_json(_SCHEDULE_CONFIG_PATH, {})
    # Back-fill any missing keys from defaults
    for key, val in _DEFAULT_SCHEDULE_CONFIG.items():
        cfg.setdefault(key, val)
    return cfg


def _load_appointments() -> list[dict]:
    """Load appointments, seeding with defaults when file is absent."""
    _ensure_health_dir()
    if not _APPOINTMENTS_PATH.exists():
        _save_json(_APPOINTMENTS_PATH, _DEFAULT_APPOINTMENTS)
        return list(_DEFAULT_APPOINTMENTS)
    data = _load_json(_APPOINTMENTS_PATH, [])
    return data if isinstance(data, list) else []


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _parse_appointment_datetime(appt: dict) -> datetime | None:
    """Parse an appointment's date+time into a datetime object."""
    try:
        date_str = appt.get("date", "")
        time_str = appt.get("time", "00:00")
        return datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    except Exception:
        return None


def _generate_headline(
    oracle_pathway: str,
    day_type: str,
    drift_alerts: list[dict],
    three_moves: list,
    readiness_score: int,
) -> str:
    """Generate a one-sentence morning brief headline."""
    if oracle_pathway in ("O-911", "O-ER"):
        return "URGENT: Oracle has flagged an emergency — immediate action required."
    if oracle_pathway == "O-URGENT":
        return "Urgent health signal detected — review Oracle flags before starting your day."
    if oracle_pathway == "O-CLINIC":
        return "A clinical concern needs attention within the next day or two."
    n_alerts = len(drift_alerts)
    if n_alerts >= 3:
        return (
            f"Significant drift detected across {n_alerts} clusters — "
            f"today is a {day_type} day with readiness {readiness_score}."
        )
    if n_alerts > 0:
        return (
            f"Mild drift present ({n_alerts} cluster{'s' if n_alerts > 1 else ''}) — "
            f"{day_type} day, readiness {readiness_score}. Focus on your Three Moves."
        )
    return (
        f"All systems stable — {day_type} day with readiness score {readiness_score}. "
        f"Execute your Three Moves."
    )


# ---------------------------------------------------------------------------
# 1. run_morning_brief
# ---------------------------------------------------------------------------

async def run_morning_brief() -> dict:
    """
    Full morning autonomous run.

    Steps:
    1. Load health state.
    2. Get current signals from drift_detection.
    3. Run Oracle-only check from longevity_council.
    4. Classify day type via daily_stewardship.
    5. Generate Three Moves via daily_stewardship.
    6. Run drift scan via drift_detection.
    7. Check upcoming appointments.
    8. Assemble, save, and return morning brief.

    Returns:
        Morning brief dict with keys: date, generated_at, oracle_pathway,
        day_type, readiness_score, three_moves, drift_alerts,
        active_drift_clusters, upcoming_appointments, pre_appointment_alert,
        push_sent, headline.
    """
    log.info("run_morning_brief: starting autonomous morning run")

    # ---- 1. Health state ----
    health_state = _load_health_state()

    # ---- 2. Current signals ----
    signals: dict = {}
    try:
        try:
            from .drift_detection import get_current_signals
        except ImportError:
            from drift_detection import get_current_signals  # type: ignore
        signals = await get_current_signals()
        log.debug("run_morning_brief: signals fetched (%d keys)", len(signals))
    except Exception as exc:
        log.warning("run_morning_brief: get_current_signals failed: %s", exc)

    # ---- 3. Oracle check (first agent only) ----
    oracle_pathway = "O-CLEAR"
    oracle_result: dict = {}
    try:
        try:
            from .longevity_council import THE_ORACLE, health_state_summary
        except ImportError:
            from longevity_council import THE_ORACLE, health_state_summary  # type: ignore
        context_str = health_state_summary() or json.dumps(health_state, default=str)
        oracle_result = await THE_ORACLE.analyze(context_str)
        oracle_pathway = oracle_result.get("oracle_pathway", "O-CLEAR")
        log.info("run_morning_brief: oracle_pathway=%s", oracle_pathway)
    except Exception as exc:
        log.warning("run_morning_brief: oracle check failed: %s", exc)

    # ---- 4. Classify day type ----
    day_type = "Maintain"
    readiness_score = 70
    try:
        try:
            from .daily_stewardship import classify_day_type
        except ImportError:
            from daily_stewardship import classify_day_type  # type: ignore
        day_result = await classify_day_type(signals, oracle_pathway)
        day_type = day_result.get("day_type", "Maintain")
        readiness_score = day_result.get("readiness_score", 70)
        log.debug("run_morning_brief: day_type=%s readiness=%s", day_type, readiness_score)
    except Exception as exc:
        log.warning("run_morning_brief: classify_day_type failed: %s", exc)

    # ---- 5. Three Moves ----
    three_moves: list = []
    try:
        try:
            from .daily_stewardship import generate_three_moves
        except ImportError:
            from daily_stewardship import generate_three_moves  # type: ignore
        moves_raw = await generate_three_moves(day_type, signals, health_state)
        # generate_three_moves returns list[dict]; extract text for the brief
        three_moves = [
            m.get("move") or m.get("text") or str(m)
            for m in moves_raw
        ]
        log.debug("run_morning_brief: three_moves generated")
    except Exception as exc:
        log.warning("run_morning_brief: generate_three_moves failed: %s", exc)

    # ---- 6. Drift scan ----
    drift_alerts: list[dict] = []
    active_drift_clusters: list[dict] = []
    try:
        try:
            from .drift_detection import run_drift_scan
        except ImportError:
            from drift_detection import run_drift_scan  # type: ignore
        drift_report = await run_drift_scan()
        drift_alerts = drift_report.get("drift_alerts", [])
        active_drift_clusters = drift_report.get("active_clusters", [])
        log.debug(
            "run_morning_brief: drift_alerts=%d active_clusters=%d",
            len(drift_alerts), len(active_drift_clusters),
        )
    except Exception as exc:
        log.warning("run_morning_brief: run_drift_scan failed: %s", exc)

    # ---- 7. Upcoming appointments ----
    upcoming_appointments = check_pre_appointment_alerts()
    pre_alert: dict | None = None
    for appt in upcoming_appointments:
        if appt.get("urgent"):
            pre_alert = appt
            break

    # ---- 8. Assemble and save ----
    headline = _generate_headline(
        oracle_pathway, day_type, drift_alerts, three_moves, readiness_score
    )

    brief: dict[str, Any] = {
        "date": _today_str(),
        "generated_at": _now_iso(),
        "oracle_pathway": oracle_pathway,
        "oracle_flags": oracle_result.get("flags", []),
        "day_type": day_type,
        "readiness_score": readiness_score,
        "three_moves": three_moves,
        "drift_alerts": drift_alerts,
        "active_drift_clusters": active_drift_clusters,
        "upcoming_appointments": upcoming_appointments,
        "pre_appointment_alert": pre_alert,
        "push_sent": False,
        "headline": headline,
    }

    _save_json(_MORNING_BRIEF_PATH, brief)
    update_schedule_status("morning_brief", _now_iso())
    log.info("run_morning_brief: complete — %s", headline)
    return brief


# ---------------------------------------------------------------------------
# 2. check_pre_appointment_alerts
# ---------------------------------------------------------------------------

def check_pre_appointment_alerts() -> list[dict]:
    """
    Read appointments and return those within the next 7 days.

    For appointments within 72 hours, adds ``urgent: True`` and a
    ``visit_prep_endpoint`` for the doctor-prep system.

    Returns:
        List of appointment dicts annotated with ``days_until``,
        ``hours_until``, ``urgent``, and optionally
        ``visit_prep_endpoint``.
    """
    appointments = _load_appointments()
    config = _load_schedule_config()
    days_advance = config.get("pre_appointment_check", {}).get("days_advance", 7)
    now = datetime.now()
    cutoff = now + timedelta(days=days_advance)

    results: list[dict] = []
    for appt in appointments:
        appt_dt = _parse_appointment_datetime(appt)
        if appt_dt is None:
            continue
        if appt_dt < now:
            # Past appointment — skip
            continue
        if appt_dt > cutoff:
            continue

        delta = appt_dt - now
        hours_until = delta.total_seconds() / 3600
        days_until = delta.days

        enriched = dict(appt)
        enriched["days_until"] = days_until
        enriched["hours_until"] = round(hours_until, 1)
        enriched["urgent"] = hours_until <= 72

        if enriched["urgent"]:
            provider_slug = (appt.get("provider", "unknown")
                             .lower().replace(" ", "-").replace(".", ""))
            enriched["visit_prep_endpoint"] = f"/api/health/doctor-prep/{provider_slug}"
            log.info(
                "check_pre_appointment_alerts: URGENT — %s in %.1fh",
                appt.get("provider"), hours_until,
            )

        results.append(enriched)

    results.sort(key=lambda a: a["hours_until"])
    return results


# ---------------------------------------------------------------------------
# 3. run_closed_loop_update
# ---------------------------------------------------------------------------

async def run_closed_loop_update(trigger: str, data: dict) -> dict:
    """
    Handle arrival of new health data and update the digital twin.

    Called when new labs, vitals, CGM, or wearable data is imported.

    Args:
        trigger: One of ``"new_labs"``, ``"new_vitals"``, ``"new_cgm"``,
                 ``"new_wearables"``.
        data:    Payload from the ingest event (varies by trigger).

    Returns:
        Delta summary dict with keys: trigger, calibration_result,
        drift_report, risk_updated, predictions_scored, alerts, timestamp.
    """
    log.info("run_closed_loop_update: trigger=%s", trigger)
    result: dict[str, Any] = {
        "trigger": trigger,
        "timestamp": _now_iso(),
        "calibration_result": None,
        "drift_report": None,
        "risk_updated": False,
        "predictions_scored": None,
        "alerts": [],
        "changes": [],
    }

    # ---- Recalibrate twin ----
    try:
        try:
            from .twin_calibrator import run_calibration
        except ImportError:
            from twin_calibrator import run_calibration  # type: ignore
        cal = await asyncio.to_thread(run_calibration)
        result["calibration_result"] = cal
        metrics = cal.get("metrics_calibrated", 0)
        result["changes"].append(f"Twin recalibrated: {metrics} metrics updated")
        log.info("run_closed_loop_update: calibration complete — %d metrics", metrics)
    except Exception as exc:
        log.warning("run_closed_loop_update: twin calibration failed: %s", exc)
        result["calibration_result"] = {"error": str(exc)}

    # ---- Re-run drift scan ----
    try:
        try:
            from .drift_detection import run_drift_scan
        except ImportError:
            from drift_detection import run_drift_scan  # type: ignore
        drift = await run_drift_scan()
        result["drift_report"] = drift
        new_alerts = drift.get("drift_alerts", [])
        if new_alerts:
            result["alerts"].extend(new_alerts)
            result["changes"].append(f"{len(new_alerts)} drift alert(s) raised after {trigger}")
        log.info("run_closed_loop_update: drift scan complete — status=%s", drift.get("overall_status"))
    except Exception as exc:
        log.warning("run_closed_loop_update: drift scan failed: %s", exc)
        result["drift_report"] = {"error": str(exc)}

    # ---- Re-run risk profile if labs changed ----
    if trigger == "new_labs":
        try:
            try:
                from .risk_equations import run_risk_profile
            except ImportError:
                from risk_equations import run_risk_profile  # type: ignore
            risk = await asyncio.to_thread(run_risk_profile)
            result["risk_updated"] = True
            result["risk_profile"] = risk
            result["changes"].append("Risk profile updated from new labs")
            log.info("run_closed_loop_update: risk profile updated")
        except Exception as exc:
            log.warning("run_closed_loop_update: risk profile update failed: %s", exc)
            result["risk_updated"] = False

    # ---- Score predictions ----
    try:
        scored = await run_prediction_scorer()
        result["predictions_scored"] = scored
        if scored.get("newly_scored", 0):
            result["changes"].append(
                f"{scored['newly_scored']} prediction(s) scored with new data"
            )
    except Exception as exc:
        log.warning("run_closed_loop_update: prediction scoring failed: %s", exc)

    update_schedule_status(f"closed_loop_{trigger}", _now_iso())
    log.info("run_closed_loop_update: complete — %d changes", len(result["changes"]))
    return result


# ---------------------------------------------------------------------------
# 4. run_prediction_scorer
# ---------------------------------------------------------------------------

async def run_prediction_scorer() -> dict:
    """
    Score pending predictions against current health state.

    Reads ``~/.jarvis/health/twin_predictions.jsonl``. For each prediction
    where ``check_date <= today`` and ``actual_value is None``, attempts to
    fill in the actual value from the current health state. Saves the updated
    file. Returns a scoring summary.

    Returns:
        Dict with keys: total_predictions, checked, newly_scored,
        still_pending, errors, timestamp.
    """
    log.info("run_prediction_scorer: starting")
    today = _today_str()
    health_state = _load_health_state()

    # Flatten health state values for easy lookup: metric -> value
    metric_lookup: dict[str, Any] = {}
    for section_key, section_val in health_state.items():
        if isinstance(section_val, dict):
            for k, v in section_val.items():
                if isinstance(v, (int, float, str)):
                    metric_lookup[k.lower()] = v
        elif isinstance(section_val, (int, float, str)):
            metric_lookup[section_key.lower()] = section_val

    predictions: list[dict] = []
    if _PREDICTIONS_PATH.exists():
        try:
            raw_lines = _PREDICTIONS_PATH.read_text().splitlines()
            for line in raw_lines:
                line = line.strip()
                if not line:
                    continue
                try:
                    predictions.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    log.warning("run_prediction_scorer: skipping malformed line: %s", exc)
        except Exception as exc:
            log.warning("run_prediction_scorer: could not read predictions file: %s", exc)

    total = len(predictions)
    checked = 0
    newly_scored = 0
    errors = 0

    updated: list[dict] = []
    for pred in predictions:
        check_date = pred.get("check_date", "")
        actual = pred.get("actual_value")
        if actual is not None:
            updated.append(pred)
            continue

        if check_date > today:
            # Not yet due
            updated.append(pred)
            continue

        # Due — attempt to score
        checked += 1
        metric = pred.get("metric", "").lower()
        found_value = metric_lookup.get(metric)

        if found_value is not None:
            pred = dict(pred)
            pred["actual_value"] = found_value
            pred["scored_at"] = _now_iso()
            # Simple accuracy flag
            predicted = pred.get("predicted_value")
            if predicted is not None:
                try:
                    pred_f = float(predicted)
                    act_f = float(found_value)
                    pct_err = abs(pred_f - act_f) / max(abs(pred_f), 1e-9) * 100
                    pred["accuracy_pct_error"] = round(pct_err, 2)
                    pred["hit"] = pct_err <= 10  # within 10% counts as a hit
                except (TypeError, ValueError):
                    pred["accuracy_pct_error"] = None
                    pred["hit"] = None
            newly_scored += 1
            log.debug(
                "run_prediction_scorer: scored %s → actual=%s", metric, found_value
            )
        else:
            log.debug(
                "run_prediction_scorer: metric %s not found in health state", metric
            )
            errors += 1

        updated.append(pred)

    # Save back
    if predictions:
        _ensure_health_dir()
        try:
            _PREDICTIONS_PATH.write_text(
                "\n".join(json.dumps(p, default=str) for p in updated) + "\n"
            )
        except Exception as exc:
            log.error("run_prediction_scorer: failed to save predictions: %s", exc)

    still_pending = sum(
        1 for p in updated
        if p.get("actual_value") is None and p.get("check_date", "") <= today
    )

    summary = {
        "total_predictions": total,
        "checked": checked,
        "newly_scored": newly_scored,
        "still_pending": still_pending,
        "errors": errors,
        "timestamp": _now_iso(),
    }
    update_schedule_status("prediction_scorer", _now_iso())
    log.info(
        "run_prediction_scorer: done — newly_scored=%d still_pending=%d",
        newly_scored, still_pending,
    )
    return summary


# ---------------------------------------------------------------------------
# 5. get_schedule_status
# ---------------------------------------------------------------------------

def get_schedule_status() -> dict:
    """
    Return current schedule config and last/next run times.

    Reads ``schedule_config.json`` and ``schedule_status.json``.

    Returns:
        Dict with keys: config, last_runs, next_runs, enabled_jobs.
    """
    config = _load_schedule_config()
    status = _load_json(_SCHEDULE_STATUS_PATH, {})
    now = datetime.now()

    next_runs: dict[str, str] = {}
    last_runs: dict[str, str] = status.get("last_runs", {})

    # morning_brief — next 06:00
    if config.get("morning_brief", {}).get("enabled"):
        h = config["morning_brief"].get("hour", 6)
        m = config["morning_brief"].get("minute", 0)
        next_run = now.replace(hour=h, minute=m, second=0, microsecond=0)
        if next_run <= now:
            next_run += timedelta(days=1)
        next_runs["morning_brief"] = next_run.isoformat(timespec="seconds")

    # drift_check — every N hours from last run
    if config.get("drift_check", {}).get("enabled"):
        interval = config["drift_check"].get("interval_hours", 6)
        last = last_runs.get("drift_check")
        if last:
            try:
                last_dt = datetime.fromisoformat(last)
                next_run = last_dt + timedelta(hours=interval)
            except ValueError:
                next_run = now + timedelta(hours=interval)
        else:
            next_run = now + timedelta(hours=interval)
        next_runs["drift_check"] = next_run.isoformat(timespec="seconds")

    # weekly_council — next Sunday 07:00
    if config.get("weekly_council", {}).get("enabled"):
        target_dow = config["weekly_council"].get("day_of_week", "sunday").lower()
        _dow_map = {
            "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
            "friday": 4, "saturday": 5, "sunday": 6,
        }
        target_dow_int = _dow_map.get(target_dow, 6)
        h = config["weekly_council"].get("hour", 7)
        days_ahead = (target_dow_int - now.weekday()) % 7
        if days_ahead == 0:
            candidate = now.replace(hour=h, minute=0, second=0, microsecond=0)
            if candidate <= now:
                days_ahead = 7
        next_run = (now + timedelta(days=days_ahead)).replace(
            hour=h, minute=0, second=0, microsecond=0
        )
        next_runs["weekly_council"] = next_run.isoformat(timespec="seconds")

    # prediction_scorer — daily
    if config.get("prediction_scorer", {}).get("enabled"):
        interval_days = config["prediction_scorer"].get("interval_days", 1)
        last = last_runs.get("prediction_scorer")
        if last:
            try:
                last_dt = datetime.fromisoformat(last)
                next_run = last_dt + timedelta(days=interval_days)
            except ValueError:
                next_run = now + timedelta(days=interval_days)
        else:
            next_run = now + timedelta(days=interval_days)
        next_runs["prediction_scorer"] = next_run.isoformat(timespec="seconds")

    enabled_jobs = [
        job for job, cfg in config.items()
        if isinstance(cfg, dict) and cfg.get("enabled")
    ]

    return {
        "config": config,
        "last_runs": last_runs,
        "next_runs": next_runs,
        "enabled_jobs": enabled_jobs,
        "retrieved_at": _now_iso(),
    }


# ---------------------------------------------------------------------------
# 6. update_schedule_status
# ---------------------------------------------------------------------------

def update_schedule_status(job: str, last_run: str) -> None:
    """
    Update the persisted schedule status file after a job completes.

    Args:
        job:      Name of the job that just ran (e.g. ``"morning_brief"``).
        last_run: ISO-format timestamp of completion.
    """
    _ensure_health_dir()
    status = _load_json(_SCHEDULE_STATUS_PATH, {"last_runs": {}})
    if "last_runs" not in status or not isinstance(status["last_runs"], dict):
        status["last_runs"] = {}
    status["last_runs"][job] = last_run
    status["updated_at"] = _now_iso()
    _save_json(_SCHEDULE_STATUS_PATH, status)
    log.debug("update_schedule_status: %s → %s", job, last_run)


# ---------------------------------------------------------------------------
# 7. run_weekly_council
# ---------------------------------------------------------------------------

async def run_weekly_council() -> dict:
    """
    Run the full 19-agent Longevity Council.

    Designed for weekly execution (typically Sunday 07:00). Invokes
    ``run_council()`` from longevity_council with force_refresh=True.
    Saves the council result to ``council_cache.json`` (handled internally
    by longevity_council) and returns a human-readable summary.

    Returns:
        Dict with keys: run_at, agents_completed, agents_failed,
        oracle_pathway, top_recommendations, council_result (full).
    """
    log.info("run_weekly_council: starting full 19-agent council")
    run_at = _now_iso()

    council_result: dict = {}
    try:
        try:
            from .longevity_council import run_council, health_state_summary
        except ImportError:
            from longevity_council import run_council, health_state_summary  # type: ignore

        context = health_state_summary() or json.dumps(_load_health_state(), default=str)
        council_result = await run_council(context, force_refresh=True)
        log.info("run_weekly_council: council complete")
    except Exception as exc:
        log.error("run_weekly_council: council failed: %s", exc)
        council_result = {"error": str(exc)}

    # Build summary
    agents_completed = 0
    agents_failed = 0
    top_recommendations: list[str] = []

    for key, val in council_result.items():
        if key.startswith("_"):
            continue
        if isinstance(val, dict):
            if "error" in val:
                agents_failed += 1
            else:
                agents_completed += 1
                # Try to extract a top recommendation from each agent
                recs = (
                    val.get("recommendations")
                    or val.get("top_recommendations")
                    or val.get("action_items")
                    or []
                )
                if isinstance(recs, list) and recs:
                    top_recommendations.append(str(recs[0]))
                elif isinstance(recs, str):
                    top_recommendations.append(recs)

    oracle_pathway = (
        council_result.get("_oracle", {}).get("oracle_pathway", "O-CLEAR")
        if isinstance(council_result.get("_oracle"), dict)
        else "O-CLEAR"
    )

    summary = {
        "run_at": run_at,
        "agents_completed": agents_completed,
        "agents_failed": agents_failed,
        "oracle_pathway": oracle_pathway,
        "top_recommendations": top_recommendations[:10],  # Cap at 10
        "emergency": council_result.get("_emergency", False),
        "council_result": council_result,
    }

    update_schedule_status("weekly_council", run_at)
    log.info(
        "run_weekly_council: complete — %d completed, %d failed",
        agents_completed, agents_failed,
    )
    return summary


# ---------------------------------------------------------------------------
# 8. get_morning_brief
# ---------------------------------------------------------------------------

def get_morning_brief() -> dict:
    """
    Return the last saved morning brief from disk.

    If the brief is older than 12 hours, returns the data with
    ``stale: True`` added so callers can decide whether to trigger a refresh.

    Returns:
        Morning brief dict, possibly annotated with ``stale: True`` and
        ``stale_hours: float``.
    """
    if not _MORNING_BRIEF_PATH.exists():
        log.debug("get_morning_brief: no brief on disk")
        return {"stale": True, "error": "No morning brief found"}

    brief = _load_json(_MORNING_BRIEF_PATH, {})
    if not brief:
        return {"stale": True, "error": "Morning brief is empty"}

    generated_at_str = brief.get("generated_at", "")
    stale = False
    stale_hours = 0.0
    if generated_at_str:
        try:
            generated_at = datetime.fromisoformat(generated_at_str)
            age = datetime.now() - generated_at
            stale_hours = age.total_seconds() / 3600
            if stale_hours > 12:
                stale = True
                log.info(
                    "get_morning_brief: brief is %.1fh old — marking stale",
                    stale_hours,
                )
        except ValueError:
            stale = True

    if stale:
        brief["stale"] = True
        brief["stale_hours"] = round(stale_hours, 1)

    return brief


# ---------------------------------------------------------------------------
# CLI entry point (on-demand runs)
# ---------------------------------------------------------------------------

async def _main_async(command: str) -> None:
    """Async entry point for on-demand CLI execution."""
    dispatch: dict[str, Any] = {
        "morning":     run_morning_brief,
        "drift":       lambda: __import__(
            "drift_detection", fromlist=["run_drift_scan"]
        ).run_drift_scan(),
        "council":     run_weekly_council,
        "score":       run_prediction_scorer,
        "status":      lambda: asyncio.coroutine(
            lambda: get_schedule_status()
        )(),
        "brief":       lambda: asyncio.coroutine(
            lambda: get_morning_brief()
        )(),
        "appointments": lambda: asyncio.coroutine(
            lambda: check_pre_appointment_alerts()
        )(),
    }

    if command == "morning":
        result = await run_morning_brief()
    elif command == "council":
        result = await run_weekly_council()
    elif command == "score":
        result = await run_prediction_scorer()
    elif command == "status":
        result = get_schedule_status()
    elif command == "brief":
        result = get_morning_brief()
    elif command == "appointments":
        result = check_pre_appointment_alerts()
    else:
        print(f"Unknown command: {command}")
        print("Available: morning, council, score, status, brief, appointments")
        return

    print(json.dumps(result, indent=2, default=str))


def main() -> None:
    """
    CLI entry point.

    Usage:
        python -m jarvis.health_scheduler <command>

    Commands:
        morning       Run full morning brief
        council       Run weekly 19-agent council
        score         Run prediction scorer
        status        Show schedule status
        brief         Show last morning brief
        appointments  Show upcoming appointments
    """
    import sys
    command = sys.argv[1] if len(sys.argv) > 1 else "status"
    asyncio.run(_main_async(command))


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    )
    main()
