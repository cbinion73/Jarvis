"""
health_agent.py — Helen Cho: JARVIS Health Agent
==================================================
Named after Dr. Helen Cho from Avengers: Age of Ultron —
biomedical scientist and regenerative medicine expert.

Synthesises Apple Health + Epic FHIR data into:
  - Morning briefing health paragraph
  - Dashboard card data
  - Trend alerts and anomaly flags
  - Medical records summary
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any

logger = logging.getLogger("jarvis.health_agent")

AGENT_ID   = "helen-cho"
AGENT_NAME = "Helen Cho"
AGENT_TITLE = "Health & Medical Intelligence"


def get_dashboard_data() -> dict:
    """Return structured data for the health overview card."""
    from .health_bridge import get_latest, compute_readiness, get_trend
    snap      = get_latest()
    readiness = compute_readiness(snap)
    result: dict[str, Any] = {
        "has_data": snap is not None,
        "date":     snap.get("date") if snap else None,
        "readiness": readiness,
        "metrics": {},
        "trends":  {},
    }
    if snap:
        for key in ("steps", "resting_hr", "hrv", "sleep_hours", "blood_oxygen",
                    "active_calories", "exercise_minutes", "weight_lbs"):
            if snap.get(key) is not None:
                result["metrics"][key] = snap[key]
        # Quick 7-day trend for key metrics
        for m in ("hrv", "resting_hr", "sleep_hours", "steps"):
            t = get_trend(m, days=7)
            if t.get("avg") is not None:
                result["trends"][m] = {"avg": t["avg"], "trend": t["trend"]}
    return result


def get_morning_summary() -> str:
    """Health paragraph for the morning brief. Returns '' if no data."""
    from .health_bridge import get_morning_summary as _health_summary
    return _health_summary()


def get_epic_summary() -> dict:
    """Pull a summary of medical records from Epic. Returns empty dict if not connected."""
    from .epic_fhir import is_connected, EpicFHIRClient
    if not is_connected():
        return {"connected": False}
    try:
        client       = EpicFHIRClient()
        patient      = client.get_patient()
        conditions   = client.get_conditions()
        medications  = client.get_medications()
        appointments = client.get_appointments(count=5)
        return {
            "connected":             True,
            "patient":               patient,
            "conditions":            conditions,
            "medications":           medications,
            "upcoming_appointments": appointments,
        }
    except Exception as exc:
        logger.warning("Helen Cho: Epic summary failed: %s", exc)
        return {"connected": True, "error": str(exc)[:200]}


def flag_anomalies() -> list[dict]:
    """
    Check for metrics outside healthy ranges. Returns list of concern dicts.
    Each: {metric, value, message, severity: 'info'|'warn'|'alert'}
    """
    from .health_bridge import get_latest
    snap = get_latest()
    if not snap:
        return []
    concerns = []

    checks = [
        ("resting_hr",   lambda v: v > 100, "alert", "Elevated resting HR"),
        ("resting_hr",   lambda v: v < 40,  "alert", "Unusually low resting HR"),
        ("blood_oxygen", lambda v: v < 95,  "alert", "Low blood oxygen"),
        ("hrv",          lambda v: v < 20,  "warn",  "Very low HRV — high stress or poor recovery"),
        ("sleep_hours",  lambda v: v < 5,   "warn",  "Under 5 hours sleep"),
        ("sleep_hours",  lambda v: v < 6.5, "info",  "Sleep below recommended 7–9 hours"),
        ("systolic_bp",  lambda v: v > 140, "alert", "Elevated systolic blood pressure"),
        ("diastolic_bp", lambda v: v > 90,  "warn",  "Elevated diastolic blood pressure"),
    ]
    for metric, test, severity, message in checks:
        val = snap.get(metric)
        if val is not None:
            try:
                if test(float(val)):
                    concerns.append({"metric": metric, "value": val, "message": message, "severity": severity})
            except (TypeError, ValueError):
                pass
    return concerns


def get_labs_summary() -> list[dict]:
    """Recent lab results from Epic (last 20)."""
    from .epic_fhir import is_connected, EpicFHIRClient
    if not is_connected():
        return []
    try:
        return EpicFHIRClient().get_observations("laboratory", count=20)
    except Exception as exc:
        logger.warning("Helen Cho: labs failed: %s", exc)
        return []
