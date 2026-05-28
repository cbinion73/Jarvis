"""
JARVIS Predictive Drift & Pattern Detection Engine — Heimdall Protocol
Based on Helen Cho Master Binder v1.5, File 21: Predictive Drift & Pattern Detection v1.4

Detects sustained drift from Chris's personal baseline and pattern clusters
that appear before a clinical threshold is crossed.

Routes:
  GET  /api/health/drift/scan        — full drift scan
  GET  /api/health/drift/clusters    — active pattern clusters
  GET  /api/health/drift/baseline    — Chris's personal baseline metrics
"""
from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timedelta
from typing import Any

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Chris's personal baselines — from known data May 2026
# ---------------------------------------------------------------------------

_CHRIS_BASELINES = {
    "resting_hr": {"value": 58.0, "unit": "bpm", "source": "Apple Health May 2026"},
    "hrv": {"value": 45.0, "unit": "ms", "source": "Apple Health May 2026"},
    "sleep_hours": {"value": 7.5, "unit": "hours", "source": "Apple Health May 2026"},
    "steps": {"value": 8432, "unit": "steps/day", "source": "Apple Health May 21 2026"},
    "a1c": {"value": 7.3, "unit": "%", "source": "Lab May 2026", "goal": 7.0},
    "ldl": {"value": 156, "unit": "mg/dL", "source": "Lab May 2026", "goal": 100},
    "egfr": {"value": 87, "unit": "mL/min/1.73m²", "source": "Lab May 2026", "floor": 60},
    "potassium": {"value": 4.5, "unit": "mmol/L", "source": "Lab May 2026", "ceiling": 5.0},
    "systolic_bp": {"value": 140, "unit": "mmHg", "source": "Treatment goal May 2026", "goal": 130},
}

# ---------------------------------------------------------------------------
# Pattern cluster definitions — from Binder §21.4
# ---------------------------------------------------------------------------

_DRIFT_CLUSTERS = {
    "recovery_debt": {
        "name": "Recovery Debt",
        "signals": ["sleep_hours < 6.5", "hrv < 35", "resting_hr > 65", "steps < 5000"],
        "threshold": 2,
        "routing": ["morpheus", "yoda", "deanna-troi", "st-luke"],
        "description": "Accumulated sleep debt and physiological stress accumulation",
    },
    "metabolic_drift": {
        "name": "Metabolic Drift",
        "signals": ["a1c > 7.5", "ldl > 160", "steps < 5000", "sleep_hours < 6.5"],
        "threshold": 2,
        "routing": ["gregory-house", "poison-ivy", "cristina-yang", "morpheus", "thor-fitness", "yoda"],
        "description": "Weight, glucose, lipid, and activity degradation cluster",
    },
    "cardiovascular_load": {
        "name": "Cardiovascular Load",
        "signals": ["systolic_bp > 150", "resting_hr > 65", "sleep_hours < 6.5", "ldl > 160"],
        "threshold": 2,
        "routing": ["cristina-yang", "dr-mccoy", "morpheus", "data"],
        "description": "BP, heart rate, sleep, and lipid convergence toward CV risk",
    },
    "medication_effect": {
        "name": "Medication Effect",
        "signals": ["potassium > 5.0", "egfr < 80", "new_symptom_reported"],
        "threshold": 1,
        "routing": ["sherlock-holmes", "data", "dr-mccoy"],
        "description": "Lab shift or symptom following medication context change",
    },
    "burnout": {
        "name": "Burnout / Cognitive Load",
        "signals": ["sleep_hours < 6.5", "hrv < 35", "steps < 4000"],
        "threshold": 2,
        "routing": ["deanna-troi", "paul-weston", "yoda", "morpheus", "st-luke"],
        "description": "Sleep, HRV, activity decline suggesting stress overload",
    },
}


# ---------------------------------------------------------------------------
# Signal parsing helpers
# ---------------------------------------------------------------------------

def _parse_signal_expr(expr: str) -> tuple[str, str, float] | None:
    """Parse 'metric > threshold' or 'metric < threshold' into (metric, op, value)."""
    m = re.match(r"^\s*(\w+)\s*([<>])\s*([\d.]+)\s*$", expr.strip())
    if m:
        return m.group(1), m.group(2), float(m.group(3))
    return None


def _evaluate_signal_expr(expr: str, signals: dict) -> bool | None:
    """
    Evaluate a single signal expression against current signals.
    Returns True if triggered, False if not, None if data missing.
    """
    if expr == "new_symptom_reported":
        return signals.get("new_symptom_reported", False)

    parsed = _parse_signal_expr(expr)
    if parsed is None:
        return None

    metric, op, threshold = parsed
    signal_entry = signals.get(metric)
    if signal_entry is None:
        return None

    value = signal_entry.get("value")
    if value is None:
        return None

    try:
        value = float(value)
    except (TypeError, ValueError):
        return None

    if op == ">":
        return value > threshold
    elif op == "<":
        return value < threshold
    return None


def _signal_age_hours(signal_entry: dict) -> float | None:
    """Return how many hours old a signal's date is, or None."""
    date_str = signal_entry.get("date")
    if not date_str:
        return None
    try:
        dt = datetime.fromisoformat(date_str)
        return (datetime.utcnow() - dt).total_seconds() / 3600
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

async def get_current_signals() -> dict:
    """
    Pull current signal values from health_db and health_state.
    Returns dict of signal_name → {value, date, source}.
    """
    signals: dict[str, dict] = {}
    today = datetime.utcnow().isoformat()

    # --- Wearable signals from daily_metrics ---
    try:
        try:
            from .health_db import get_latest_metrics
        except ImportError:
            from health_db import get_latest_metrics

        rows = await get_latest_metrics(days=3)
        if rows:
            latest = rows[0]
            date_str = latest.get("date", today)
            if latest.get("resting_hr") is not None:
                signals["resting_hr"] = {"value": float(latest["resting_hr"]), "date": date_str, "source": "apple_health"}
            if latest.get("hrv") is not None:
                signals["hrv"] = {"value": float(latest["hrv"]), "date": date_str, "source": "apple_health"}
            if latest.get("sleep_hours") is not None:
                signals["sleep_hours"] = {"value": float(latest["sleep_hours"]), "date": date_str, "source": "apple_health"}
            if latest.get("steps") is not None:
                signals["steps"] = {"value": float(latest["steps"]), "date": date_str, "source": "apple_health"}
    except Exception as exc:
        log.warning("Could not load daily metrics for signals: %s", exc)

    # --- BP from bp_readings ---
    try:
        try:
            from .health_db import get_bp_readings
        except ImportError:
            from health_db import get_bp_readings

        bp_rows = await get_bp_readings(limit=5)
        if bp_rows:
            latest_bp = bp_rows[0]
            systolic = latest_bp.get("systolic")
            if systolic is not None:
                signals["systolic_bp"] = {
                    "value": float(systolic),
                    "date": latest_bp.get("reading_date", today),
                    "source": "omron",
                }
    except Exception as exc:
        log.warning("Could not load BP readings for signals: %s", exc)

    # --- Labs from health_state ---
    try:
        try:
            from .longevity_council import load_health_state
        except ImportError:
            from longevity_council import load_health_state

        state = load_health_state()
        labs = state.get("biometrics", {}).get("labs", {})
        lab_date = today

        if labs.get("a1c") is not None:
            signals["a1c"] = {"value": float(labs["a1c"]), "date": lab_date, "source": "health_state"}
        if labs.get("ldl") is not None:
            signals["ldl"] = {"value": float(labs["ldl"]), "date": lab_date, "source": "health_state"}
        if labs.get("egfr") is not None:
            signals["egfr"] = {"value": float(labs["egfr"]), "date": lab_date, "source": "health_state"}
        if labs.get("potassium") is not None:
            signals["potassium"] = {"value": float(labs["potassium"]), "date": lab_date, "source": "health_state"}

        # Also check glucose_metrics for A1c
        glucose = state.get("biometrics", {}).get("glucose_metrics", {})
        if "a1c" not in signals and glucose.get("a1c_latest") is not None:
            a1c_str = str(glucose["a1c_latest"]).replace("%", "").strip()
            try:
                signals["a1c"] = {"value": float(a1c_str), "date": glucose.get("a1c_date", lab_date), "source": "health_state"}
            except (ValueError, TypeError):
                pass

    except Exception as exc:
        log.warning("Could not load health state labs for signals: %s", exc)

    # --- Fallback: use hardcoded baselines as current values if no DB data ---
    for key, baseline in _CHRIS_BASELINES.items():
        if key not in signals:
            signals[key] = {
                "value": baseline["value"],
                "date": "2026-05-22",
                "source": f"baseline_fallback ({baseline['source']})",
            }

    return signals


def evaluate_cluster(cluster_def: dict, signals: dict) -> dict:
    """
    Evaluate whether a drift cluster is active based on current signals.
    Returns {active, signals_present, signals_missing, confidence, severity}.
    """
    signals_present = []
    signals_missing = []
    data_ages: list[float] = []

    for expr in cluster_def["signals"]:
        metric_name = expr.split()[0] if expr != "new_symptom_reported" else "new_symptom_reported"
        result = _evaluate_signal_expr(expr, signals)

        # Track data age
        signal_entry = signals.get(metric_name)
        if signal_entry:
            age = _signal_age_hours(signal_entry)
            if age is not None:
                data_ages.append(age)

        if result is True:
            signals_present.append(expr)
        elif result is None:
            signals_missing.append(expr)
        # result is False → signal is in range, not a concern

    threshold = cluster_def.get("threshold", 2)
    active = len(signals_present) >= threshold

    # Determine confidence based on data freshness and signal coverage
    total_signals = len(cluster_def["signals"])
    missing_count = len(signals_missing)

    if data_ages:
        max_age = max(data_ages)
    else:
        max_age = 99

    if missing_count == 0 and max_age < 24:
        confidence = "high"
    elif missing_count <= 1 and max_age < 48:
        confidence = "moderate"
    else:
        confidence = "low"

    # Severity: how many signals above threshold
    if not active:
        severity = "none"
    elif len(signals_present) == threshold:
        severity = "mild"
    elif len(signals_present) == threshold + 1:
        severity = "moderate"
    else:
        severity = "significant"

    return {
        "cluster_id": None,  # filled in by scan_all_clusters
        "name": cluster_def["name"],
        "active": active,
        "signals_present": signals_present,
        "signals_missing": signals_missing,
        "signals_count": len(signals_present),
        "threshold": threshold,
        "confidence": confidence,
        "severity": severity,
        "routing": cluster_def.get("routing", []),
        "description": cluster_def.get("description", ""),
    }


async def scan_all_clusters(signals: dict | None = None) -> list[dict]:
    """
    Evaluate all 5 drift clusters against current signals.
    Returns list of cluster results, active ones first.
    """
    if signals is None:
        signals = await get_current_signals()

    results = []
    for cluster_id, cluster_def in _DRIFT_CLUSTERS.items():
        result = evaluate_cluster(cluster_def, signals)
        result["cluster_id"] = cluster_id
        results.append(result)

    # Sort: active first, then by number of signals present
    results.sort(key=lambda r: (0 if r["active"] else 1, -r["signals_count"]))
    return results


async def get_baseline_deviations(signals: dict | None = None) -> list[dict]:
    """
    Compare current values to Chris's personal baselines.
    Returns list of {metric, current, baseline, deviation_pct, direction, significance}.
    Flags if deviation > 10% for HR/HRV/sleep, > 5% for labs.
    """
    if signals is None:
        signals = await get_current_signals()

    lab_metrics = {"a1c", "ldl", "egfr", "potassium"}
    deviations = []

    for metric, baseline_info in _CHRIS_BASELINES.items():
        baseline_value = baseline_info["value"]
        signal = signals.get(metric)
        if signal is None or signal.get("value") is None:
            continue

        current_value = float(signal["value"])

        if baseline_value == 0:
            continue

        deviation_pct = ((current_value - baseline_value) / baseline_value) * 100
        abs_deviation = abs(deviation_pct)
        direction = "above" if deviation_pct > 0 else "below"

        # Significance threshold: 5% for labs, 10% for wearables
        threshold_pct = 5.0 if metric in lab_metrics else 10.0
        significant = abs_deviation >= threshold_pct

        # Special patient-specific significance overrides
        if metric == "potassium" and current_value >= 5.0:
            significant = True
        if metric == "egfr" and current_value < 60:
            significant = True
        if metric == "systolic_bp" and current_value >= 160:
            significant = True

        deviations.append({
            "metric": metric,
            "current": current_value,
            "baseline": baseline_value,
            "unit": baseline_info.get("unit", ""),
            "deviation_pct": round(deviation_pct, 1),
            "direction": direction,
            "significant": significant,
            "goal": baseline_info.get("goal"),
            "ceiling": baseline_info.get("ceiling"),
            "floor": baseline_info.get("floor"),
            "source": signal.get("source", "unknown"),
            "data_date": signal.get("date"),
        })

    # Sort: significant first
    deviations.sort(key=lambda d: (0 if d["significant"] else 1, -abs(d["deviation_pct"])))
    return deviations


def get_drift_alert_template(cluster_name: str, signals_present: list) -> dict:
    """
    Generate a Drift Alert using the binder template (§21.6).
    Returns structured drift alert dict.
    """
    # Map cluster name to possible drivers
    driver_map = {
        "Recovery Debt": [
            "Insufficient sleep duration or quality",
            "Elevated physiological stress",
            "Illness or immune response",
            "Travel or schedule disruption",
        ],
        "Metabolic Drift": [
            "Dietary change or adherence lapse",
            "Reduced physical activity",
            "Medication dose change or interaction",
            "Sleep-driven glucose elevation",
        ],
        "Cardiovascular Load": [
            "BP medication efficacy or adherence",
            "Sodium or fluid retention",
            "OSA unaddressed — nocturnal hypertension",
            "LDL progression without treatment",
        ],
        "Medication Effect": [
            "ARB + spironolactone hyperkalemia risk",
            "eGFR decline with current regimen",
            "New symptom following dosage change",
        ],
        "Burnout / Cognitive Load": [
            "Sustained work or life stress",
            "Social or relational burden",
            "Sleep deprivation cascade",
        ],
    }

    threshold_map = {
        "Recovery Debt": "If HRV drops below 30ms or sleep averages <6h for 3 consecutive days → O-URGENT review",
        "Metabolic Drift": "If A1c approaches 7.8% or fasting glucose >180 consistently → contact clinician",
        "Cardiovascular Load": "If BP systolic >160 on any reading → contact clinician same day",
        "Medication Effect": "If K+ >5.0 or eGFR <80 → contact clinician within 24 hours",
        "Burnout / Cognitive Load": "If HRV <30ms for 5+ days → council review recommended",
    }

    possible_drivers = driver_map.get(cluster_name, ["Unknown drivers"])
    if_then = threshold_map.get(cluster_name, "Monitor and reassess in 24 hours")

    return {
        "pattern_detected": cluster_name,
        "signals": signals_present,
        "possible_drivers": possible_drivers,
        "confidence": "moderate",
        "oracle_review_needed": cluster_name in {"Medication Effect", "Cardiovascular Load"},
        "recommended_response": f"Review {cluster_name} cluster signals with relevant specialists",
        "if_then_threshold": if_then,
        "generated_at": datetime.utcnow().isoformat(),
    }


async def run_drift_scan() -> dict:
    """
    Full drift scan:
    1. get_current_signals()
    2. scan_all_clusters()
    3. get_baseline_deviations()
    4. Determine overall drift status
    5. Generate drift alerts for active clusters
    6. append_council_decision() to log
    Returns drift report.
    """
    scan_date = datetime.utcnow().isoformat()

    signals = await get_current_signals()
    clusters = await scan_all_clusters(signals)
    deviations = await get_baseline_deviations(signals)

    active_clusters = [c for c in clusters if c["active"]]
    significant_deviations = [d for d in deviations if d["significant"]]

    # Determine overall drift status
    if len(active_clusters) >= 3 or any(c["severity"] == "significant" for c in active_clusters):
        overall_status = "significant drift"
    elif len(active_clusters) == 2:
        overall_status = "moderate drift"
    elif len(active_clusters) == 1 or len(significant_deviations) >= 2:
        overall_status = "mild drift"
    else:
        overall_status = "stable"

    # Generate drift alerts for active clusters
    drift_alerts = []
    for cluster in active_clusters:
        alert = get_drift_alert_template(cluster["name"], cluster["signals_present"])
        alert["cluster_id"] = cluster["cluster_id"]
        alert["severity"] = cluster["severity"]
        alert["confidence"] = cluster["confidence"]
        drift_alerts.append(alert)

    # Monitoring priorities
    monitoring_priorities = []
    for dev in significant_deviations[:5]:
        monitoring_priorities.append(
            f"{dev['metric']}: {dev['current']} {dev['unit']} ({dev['deviation_pct']:+.1f}% vs baseline)"
        )

    # Oracle review needed?
    oracle_needed = any(a["oracle_review_needed"] for a in drift_alerts) or overall_status == "significant drift"

    # One next action
    if active_clusters:
        top_cluster = active_clusters[0]
        one_next = f"Review {top_cluster['name']} cluster — {len(top_cluster['signals_present'])} signals active: {', '.join(top_cluster['signals_present'][:2])}"
    elif significant_deviations:
        top_dev = significant_deviations[0]
        one_next = f"Monitor {top_dev['metric']}: currently {top_dev['current']} vs baseline {top_dev['baseline']} ({top_dev['deviation_pct']:+.1f}%)"
    else:
        one_next = "No significant drift detected. Continue current health habits."

    report = {
        "scan_date": scan_date,
        "overall_drift_status": overall_status,
        "active_clusters": active_clusters,
        "all_clusters": clusters,
        "baseline_deviations": deviations,
        "significant_deviations": significant_deviations,
        "drift_alerts": drift_alerts,
        "monitoring_priorities": monitoring_priorities,
        "oracle_review_needed": oracle_needed,
        "one_next_action": one_next,
        "signals_loaded": list(signals.keys()),
    }

    try:
        try:
            from .longevity_council import append_council_decision
        except ImportError:
            from longevity_council import append_council_decision
        await append_council_decision({"type": "drift_scan", "overall_status": overall_status, "active_clusters": len(active_clusters), "scan_date": scan_date})
    except Exception as exc:
        log.warning("Could not append drift scan to decision log: %s", exc)

    return report
