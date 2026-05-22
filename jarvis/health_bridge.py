"""
health_bridge.py — JARVIS Health Data Bridge
=============================================
Stores and retrieves Apple Health metrics pushed from Apple Shortcuts.
Also provides readiness scoring and trend analysis for the health agent.

Data flow:
    iPhone Shortcuts → POST /api/health/ingest → health_bridge.ingest() → daily JSON

Storage: ~/.jarvis/health/daily/YYYY-MM-DD.json
"""
from __future__ import annotations

import json
import statistics
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

_HEALTH_DIR = Path.home() / ".jarvis" / "health" / "daily"
_lock = threading.Lock()

METRIC_LABELS = {
    "steps":              "Steps",
    "active_calories":    "Active Calories",
    "exercise_minutes":   "Exercise Minutes",
    "stand_hours":        "Stand Hours",
    "resting_hr":         "Resting HR",
    "hrv":                "HRV (ms)",
    "blood_oxygen":       "Blood Oxygen %",
    "respiratory_rate":   "Respiratory Rate",
    "sleep_hours":        "Sleep Hours",
    "sleep_deep_hours":   "Deep Sleep",
    "sleep_rem_hours":    "REM Sleep",
    "sleep_core_hours":   "Core Sleep",
    "weight_lbs":         "Weight (lbs)",
    "bmi":                "BMI",
    "body_fat_pct":       "Body Fat %",
    "systolic_bp":        "Systolic BP",
    "diastolic_bp":       "Diastolic BP",
    "vo2_max":            "VO2 Max",
    "mindful_minutes":    "Mindful Minutes",
}

READINESS_CONFIG = {
    # metric: (ideal_value, weight, direction)  direction: 'higher'|'lower'
    "hrv":          (60,  0.35, "higher"),
    "resting_hr":   (58,  0.25, "lower"),
    "sleep_hours":  (8.0, 0.25, "higher"),
    "sleep_deep_hours": (1.5, 0.15, "higher"),
}


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _load_day(date: str) -> dict:
    path = _HEALTH_DIR / f"{date}.json"
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_day(date: str, data: dict) -> None:
    _HEALTH_DIR.mkdir(parents=True, exist_ok=True)
    path = _HEALTH_DIR / f"{date}.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def ingest(source: str, metrics: dict[str, Any], date: str | None = None) -> dict:
    """
    Accept health metrics from any source (Shortcuts, manual, etc.)
    Merges with any existing data for that date. Returns the updated snapshot.
    """
    date = date or _today()
    with _lock:
        existing = _load_day(date)
        existing["date"] = date
        existing["source"] = source
        existing["updated_at"] = datetime.now(timezone.utc).isoformat()
        # Merge: only update keys that are present and non-None
        for k, v in metrics.items():
            if v is not None and k in METRIC_LABELS:
                existing[k] = v
        _save_day(date, existing)
    return existing


def get_latest() -> dict | None:
    """Return the most recent day's data (today first, then walk back 7 days)."""
    for delta in range(8):
        d = (datetime.now(timezone.utc) - timedelta(days=delta)).strftime("%Y-%m-%d")
        data = _load_day(d)
        if len(data) > 3:  # has actual metrics beyond just metadata
            return data
    return None


def get_history(days: int = 30) -> list[dict]:
    """Return list of daily snapshots for the past N days (most recent first)."""
    result = []
    for delta in range(days):
        d = (datetime.now(timezone.utc) - timedelta(days=delta)).strftime("%Y-%m-%d")
        data = _load_day(d)
        if data:
            result.append(data)
    return result


def get_trend(metric: str, days: int = 30) -> dict:
    """Return time-series data for a single metric."""
    history = get_history(days)
    points = [
        {"date": h["date"], "value": h[metric]}
        for h in reversed(history)
        if metric in h and h[metric] is not None
    ]
    if not points:
        return {"metric": metric, "points": [], "avg": None, "trend": "insufficient_data"}
    values = [p["value"] for p in points]
    avg = statistics.mean(values)
    # Simple trend: compare last 3 days to prior period
    trend = "stable"
    if len(values) >= 6:
        recent = statistics.mean(values[-3:])
        prior  = statistics.mean(values[-6:-3])
        if recent > prior * 1.05:
            trend = "improving" if READINESS_CONFIG.get(metric, (0, 0, "higher"))[2] == "higher" else "declining"
        elif recent < prior * 0.95:
            trend = "declining" if READINESS_CONFIG.get(metric, (0, 0, "higher"))[2] == "higher" else "improving"
    return {"metric": metric, "label": METRIC_LABELS.get(metric, metric), "points": points, "avg": round(avg, 1), "trend": trend}


def compute_readiness(snapshot: dict | None = None) -> dict:
    """
    Compute a 0–100 readiness score from HRV, resting HR, sleep.
    Returns {"score": int, "grade": str, "factors": [...], "message": str}
    """
    if snapshot is None:
        snapshot = get_latest() or {}

    factors = []
    total_weight = 0.0
    weighted_score = 0.0

    for metric, (ideal, weight, direction) in READINESS_CONFIG.items():
        val = snapshot.get(metric)
        if val is None:
            continue
        # Score this metric 0–100
        if direction == "higher":
            ratio = min(val / ideal, 1.5)
            m_score = min(100, ratio * 100 * (2 - ratio))  # peaks at ideal
        else:
            ratio = min(ideal / max(val, 1), 1.5)
            m_score = min(100, ratio * 100 * (2 - ratio))
        m_score = max(0, min(100, m_score))
        weighted_score += m_score * weight
        total_weight += weight
        factors.append({"metric": metric, "label": METRIC_LABELS[metric], "value": val, "score": round(m_score), "weight": weight})

    if total_weight == 0:
        return {"score": None, "grade": "—", "factors": [], "message": "No data yet — connect Apple Health via Shortcuts."}

    score = round(weighted_score / total_weight)
    if score >= 85:
        grade, message = "Excellent", "You're well-rested and primed to perform."
    elif score >= 70:
        grade, message = "Good", "Solid recovery. You're ready for the day."
    elif score >= 55:
        grade, message = "Moderate", "Adequate recovery. Consider lighter activity."
    elif score >= 40:
        grade, message = "Poor", "Incomplete recovery. Prioritise rest and hydration."
    else:
        grade, message = "Low", "Significantly under-recovered. Rest is the priority."

    return {"score": score, "grade": grade, "factors": factors, "message": message}


def get_morning_summary() -> str:
    """One-paragraph health summary for the morning briefing."""
    snap = get_latest()
    if not snap:
        return ""
    readiness = compute_readiness(snap)
    parts = []
    if snap.get("sleep_hours"):
        parts.append(f"{snap['sleep_hours']:.1f}h sleep")
    if snap.get("hrv"):
        parts.append(f"HRV {snap['hrv']}ms")
    if snap.get("resting_hr"):
        parts.append(f"resting HR {snap['resting_hr']}bpm")
    if snap.get("steps"):
        parts.append(f"{snap['steps']:,} steps yesterday")
    score_str = f" Readiness score: {readiness['score']}/100 ({readiness['grade']})." if readiness.get("score") else ""
    if not parts:
        return ""
    return f"**Health:** {', '.join(parts)}.{score_str} {readiness.get('message', '')}"
