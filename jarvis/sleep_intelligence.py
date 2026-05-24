"""
sleep_intelligence.py — JARVIS Sleep Architecture & Sleep Quality Intelligence Module.

Provides sleep quality monitoring, sleep debt analysis, HRV-sleep correlation,
sleep logging, and sleep recommendations for Chris Binion.

Patient context (as of May 2026):
  - 52yo male, BMI 35.7, HTN (4 drugs), T2DM
  - Sleep quality monitoring: OSA tested borderline 2019, CPAP device discontinued
    as ineffective, diagnosis removed from active conditions (resolved/historical)
  - SpO2 93% (wearable), HRV SDNN 45ms, RHR 58 bpm, sleep 7.5h (not restorative)
  - Metoprolol ER suppresses HRV pharmacologically

Evidence basis:
  - STOP-BANG questionnaire (Chung et al. Anesthesiology 2008)
  - Drager LF et al. OSA and insulin resistance. Chest 2009
  - Logan AG et al. OSA and resistant hypertension. Hypertension 2001
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional internal imports
# ---------------------------------------------------------------------------

try:
    from jarvis.risk_equations import cpap_cvd_modifier
    _HAS_RISK_EQUATIONS = True
except ImportError:
    _HAS_RISK_EQUATIONS = False
    log.warning("risk_equations not available — cpap_cvd_modifier not loaded (CPAP discontinued, not used)")

try:
    from jarvis.config import JARVIS_HOME
    _JARVIS_HOME = Path(JARVIS_HOME)
except ImportError:
    _JARVIS_HOME = Path.home() / ".jarvis"

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_HEALTH_DIR = _JARVIS_HOME / "health"
_SLEEP_LOG = _HEALTH_DIR / "sleep_log.jsonl"
_HEALTH_STATE = _HEALTH_DIR / "chris_health_state.json"
_HEALTH_DB = _HEALTH_DIR / "health.db"

# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


@dataclass
class OSARiskScore:
    """Structured OSA risk assessment using STOP-BANG + clinical extensions."""

    total_score: int                # 0-100
    risk_level: str                 # "high" | "moderate" | "low"
    ahi_estimate_range: str         # e.g. "likely 15-30 events/hour (moderate OSA)"
    contributing_factors: list[str]
    protective_factors: list[str]
    evidence_basis: str


@dataclass
class CPAPReadinessCase:
    """CPAP historical status case — CPAP was trialed and discontinued as ineffective."""

    patient_summary: str
    quantified_cvd_cost: str        # Not applicable — CPAP discontinued
    quantified_bp_cost: str         # SBP impact
    quantified_hrv_cost: str        # HRV impact
    quantified_a1c_cost: str        # Glycemic impact
    quantified_sleep_cost: str      # Sleep quality impact
    total_annual_risk_cost: str     # Composite
    cpap_projected_benefits: list[str]
    recommended_next_steps: list[str]
    referral_text: str              # Text for sleep medicine referral


@dataclass
class SleepDebtAnalysis:
    """Analysis of sleep debt and quality from available wearable data."""

    target_sleep_hours: float       # 7.5-8.5 for cardiometabolic patient on 4 BP meds
    recent_avg_hours: float
    sleep_debt_hours: float         # cumulative deficit over analysis window
    sleep_quality_score: int        # 0-100
    restorative_sleep_estimate: str # "poor" | "fair" | "adequate" | "good"
    hrv_sleep_correlation: str      # what HRV says about sleep quality
    spo2_concern: str               # what 93% SpO2 means
    recommendations: list[str]


@dataclass
class SleepLog:
    """Single night sleep log entry."""

    date: str                       # ISO date string YYYY-MM-DD
    bedtime: str                    # HH:MM (24h)
    wake_time: str                  # HH:MM (24h)
    total_hours: float
    sleep_quality: int              # 1-10 subjective
    hrv_morning: float | None
    resting_hr: float | None
    spo2_min: float | None
    notes: str = ""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_health_state() -> dict:
    """Load chris_health_state.json if available, else return empty dict."""
    try:
        if _HEALTH_STATE.exists():
            with open(_HEALTH_STATE) as f:
                return json.load(f)
    except Exception as exc:
        log.warning("Could not load health_state: %s", exc)
    return {}


def _ensure_health_dir() -> None:
    """Create ~/.jarvis/health/ if missing."""
    _HEALTH_DIR.mkdir(parents=True, exist_ok=True)


def _query_sleep_from_db(days: int = 7) -> list[dict]:
    """
    Query wearable_daily table from health.db for recent sleep records.

    Returns list of row dicts, empty list on any failure.
    """
    if not _HEALTH_DB.exists():
        log.debug("health.db not found at %s", _HEALTH_DB)
        return []
    try:
        cutoff = (date.today() - timedelta(days=days)).isoformat()
        with sqlite3.connect(str(_HEALTH_DB)) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT * FROM wearable_daily WHERE date >= ? ORDER BY date DESC",
                (cutoff,),
            )
            rows = [dict(r) for r in cur.fetchall()]
            log.debug("Loaded %d wearable_daily rows from health.db", len(rows))
            return rows
    except Exception as exc:
        log.warning("health.db query failed: %s", exc)
        return []


def _load_sleep_log_entries(days: int = 7) -> list[dict]:
    """Load entries from sleep_log.jsonl within the last N days."""
    if not _SLEEP_LOG.exists():
        return []
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    entries: list[dict] = []
    try:
        with open(_SLEEP_LOG) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get("date", "") >= cutoff:
                        entries.append(entry)
                except json.JSONDecodeError:
                    continue
    except Exception as exc:
        log.warning("Could not read sleep_log.jsonl: %s", exc)
    return entries


# ---------------------------------------------------------------------------
# 1. OSA Risk Score
# ---------------------------------------------------------------------------


def calculate_osa_risk_score() -> OSARiskScore:
    """
    Return an OSA risk assessment reflecting the resolved/historical status.

    OSA history for Chris Binion:
      - Tested borderline 2019 during pre-bariatric workup
      - CPAP device prescribed but discontinued as ineffective / not tolerated
      - Diagnosis never formally removed from EMR at the time, now resolved in JARVIS DB
      - Not currently classified as active OSA — monitoring sleep quality only

    Returns:
        OSARiskScore reflecting borderline historical risk, not active OSA.
    """
    log.info("OSA risk score: returning resolved/historical status — OSA not active")

    contributing_factors = [
        "HISTORICAL: OSA tested borderline 2019 (pre-bariatric workup)",
        "HISTORICAL: CPAP device tried and discontinued as ineffective — not currently in use",
        "HISTORICAL: Diagnosis was in EMR but has been resolved in JARVIS health DB",
        "MONITORING: SpO2 93% (wearable May 2026) — track but not attributing to active OSA",
        "MONITORING: HRV SDNN 45ms — autonomic load from HTN/meds, not confirmed OSA",
        "MONITORING: Sleep 7.5h not fully restorative — monitor quality trends",
    ]

    protective_factors = [
        "OSA resolved in JARVIS conditions DB — no longer active problem",
        "Bariatric surgery (sleeve Dec 2019) reduces OSA severity at lower BMI",
        "JARVIS monitoring active — daily HRV and SpO2 tracking for sleep quality trends",
        "No CPAP indicated — previously tried and discontinued as ineffective",
    ]

    return OSARiskScore(
        total_score=25,   # borderline historical, not active
        risk_level="low",
        ahi_estimate_range=(
            "Historical borderline 2019 — not confirmed active. CPAP trialed and discontinued. "
            "No current AHI estimate; sleep quality monitored via HRV and SpO2."
        ),
        contributing_factors=contributing_factors,
        protective_factors=protective_factors,
        evidence_basis=(
            "OSA status: tested borderline 2019, CPAP discontinued as ineffective, "
            "diagnosis resolved 2026. Sleep quality monitoring continues via wearable data."
        ),
    )


# ---------------------------------------------------------------------------
# 2. CPAP Readiness Case
# ---------------------------------------------------------------------------


def build_cpap_readiness_case() -> CPAPReadinessCase:
    """
    Return a CPAPReadinessCase reflecting that CPAP was tried and discontinued.

    History:
      - OSA tested borderline 2019 (pre-bariatric workup)
      - CPAP prescribed, trialed, and discontinued as ineffective / not tolerated
      - CPAP is NOT recommended — diagnosis resolved in JARVIS health DB
      - Sleep quality is monitored via HRV, SpO2, and sleep logging

    Returns:
        CPAPReadinessCase documenting the discontinued CPAP history.
    """
    log.info("build_cpap_readiness_case: CPAP discontinued — returning historical note")

    not_applicable = (
        "Not applicable — CPAP was previously tried and discontinued as ineffective. "
        "OSA is resolved/historical in JARVIS health DB. Sleep quality is monitored via "
        "wearable HRV and SpO2 data."
    )

    return CPAPReadinessCase(
        patient_summary=(
            "Chris Binion, 52yo male, BMI 35.7. OSA tested borderline 2019 during pre-bariatric "
            "workup. CPAP device was prescribed, trialed, and discontinued as ineffective. "
            "Diagnosis has been resolved in JARVIS health DB (May 2026). Sleep quality monitoring "
            "continues via wearable HRV and SpO2 data."
        ),
        quantified_cvd_cost=not_applicable,
        quantified_bp_cost=not_applicable,
        quantified_hrv_cost=not_applicable,
        quantified_a1c_cost=not_applicable,
        quantified_sleep_cost=(
            "SpO2 93% (wearable May 2026) and HRV 45ms are monitored as sleep quality indicators. "
            "These values are tracked for trend, not attributed to active OSA. SpO2 and HRV are "
            "affected by resistant HTN, beta-blocker (metoprolol), and general sleep architecture."
        ),
        total_annual_risk_cost=not_applicable,
        cpap_projected_benefits=[
            "CPAP is not indicated — previously trialed and discontinued as ineffective.",
            "Sleep quality improvements are targeted via consistent sleep schedule, "
            "alcohol avoidance, and A1c/HTN control.",
        ],
        recommended_next_steps=[
            "Continue monitoring SpO2 and HRV via wearable daily log.",
            "Maintain consistent bedtime/wake schedule (±30 min).",
            "Avoid alcohol — suppresses REM and worsens nocturnal SpO2.",
            "Report SpO2 trends to Dr. Wenk if waking SpO2 drops below 92% consistently.",
            "Sleep quality note for Dr. Wenk: OSA tested borderline 2019, CPAP discontinued as "
            "ineffective — sleep non-restorative per HRV but not attributed to active OSA.",
        ],
        referral_text=(
            "RE: Sleep Quality Note — OSA Historical, CPAP Discontinued\n\n"
            "Patient: Chris Binion | DOB: 1973-12-08 | Age: 52yo Male | BMI: 35.7\n\n"
            "OSA was tested borderline in 2019 during pre-bariatric workup. CPAP was prescribed "
            "and trialed but discontinued as ineffective. The diagnosis has been resolved in the "
            "JARVIS health database. Current wearable data shows SpO2 93% and HRV SDNN 45ms — "
            "monitored for sleep quality trends, not attributed to active OSA.\n\n"
            "No sleep medicine referral currently indicated for OSA. Sleep quality monitoring "
            "is ongoing via JARVIS wearable integration."
        ),
    )


# ---------------------------------------------------------------------------
# 3. Sleep Debt Analysis
# ---------------------------------------------------------------------------


def analyze_sleep_debt() -> SleepDebtAnalysis:
    """
    Analyze sleep debt and quality from available wearable and log data.

    Data sources attempted in order:
      1. sleep_log.jsonl (user-logged entries)
      2. health.db wearable_daily table
      3. chris_health_state.json (single data point fallback)

    For Chris:
      - Target: 7.5-8.0 h/night (cardiometabolic patient on 4 BP meds benefits from full sleep)
      - Only 1 confirmed data point (7.5h on 2026-05-21) — data sparsity flagged
      - SpO2 93% at rest → monitored for sleep quality, not attributed to active OSA
      - HRV 45ms: autonomic load from HTN medications and cardiometabolic stress

    Returns:
        SleepDebtAnalysis with debt calculation, quality scores, and recommendations.
    """
    # ── Collect recent data ────────────────────────────────────────────────
    db_rows = _query_sleep_from_db(days=7)
    log_entries = _load_sleep_log_entries(days=7)
    health = _load_health_state()

    # Target hours for cardiometabolic patient on 4 BP meds (full sleep supports recovery)
    target_sleep_hours = 8.0  # hours — upper end of normal for cardiometabolic patient on 4 BP meds

    recent_hours: list[float] = []

    # Pull from wearable DB
    for row in db_rows:
        h = row.get("sleep_hours") or row.get("sleep_total_hours")
        if h:
            try:
                recent_hours.append(float(h))
            except (TypeError, ValueError):
                pass

    # Pull from sleep log (prefer over DB as user-entered)
    for entry in log_entries:
        h = entry.get("total_hours")
        if h:
            try:
                recent_hours.append(float(h))
            except (TypeError, ValueError):
                pass

    # Fallback: single known data point from health_state
    # HARDCODED: 7.5h on 2026-05-21 from Apple Health sync
    data_is_sparse = len(recent_hours) == 0
    if data_is_sparse:
        recent_hours = [7.5]  # hardcoded from health_state biometrics.wearable_metrics.sleep_hours
        log.info(
            "Sleep debt: using hardcoded 7.5h from health_state (sparse data — only 1 wearable data point)"
        )

    recent_avg_hours = sum(recent_hours) / len(recent_hours) if recent_hours else 7.5
    days_tracked = len(recent_hours)

    # Debt calculation (over 7-day window, extrapolate if sparse)
    # Note: if only 1 data point, debt estimate is approximate
    nightly_deficit = max(0.0, target_sleep_hours - recent_avg_hours)
    sleep_debt_hours = round(nightly_deficit * 7, 1)  # project to 7-day window

    # ── Sleep quality score ────────────────────────────────────────────────
    # Base score: 60 (average) — adjusted by clinical factors
    quality_score = 60

    # SpO2 93% at rest is concerning — subtract for likely nocturnal desaturations
    spo2_val = 93.0  # hardcoded from wearable 2026-05-21
    if spo2_val < 94:
        quality_score -= 15  # significant concern — nocturnal desaturations likely
    elif spo2_val < 96:
        quality_score -= 8

    # HRV 45ms — autonomic stress from HTN medications and general cardiometabolic load
    hrv_val = 45  # hardcoded from Apple Health 2026-05-21
    if hrv_val < 50:
        quality_score -= 10  # high mortality risk category signal
    elif hrv_val < 65:
        quality_score -= 5

    # Duration adequate (7.5h ≥ 7.5h minimum), slight credit
    if recent_avg_hours >= 7.5:
        quality_score += 5

    quality_score = max(0, min(100, quality_score))

    # ── Restorative estimate ───────────────────────────────────────────────
    if quality_score >= 75:
        restorative_sleep_estimate = "adequate"
    elif quality_score >= 55:
        restorative_sleep_estimate = "fair"
    elif quality_score >= 35:
        restorative_sleep_estimate = "poor"
    else:
        restorative_sleep_estimate = "very poor"

    # ── HRV-sleep correlation narrative ───────────────────────────────────
    hrv_sleep_correlation = (
        f"HRV SDNN {hrv_val}ms is in the high mortality risk category (<50ms). "
        "Metoprolol ER pharmacologically suppresses HRV by approximately 10-15ms, so the "
        "underlying autonomic health may be somewhat better than the wearable reading suggests. "
        "The remaining autonomic load reflects resistant HTN, T2DM, and general cardiometabolic "
        "stress. Improving A1c control and BP management are the primary levers for HRV improvement. "
        "JARVIS tracks HRV trend weekly — a sustained increase toward ≥53ms is the target."
    )

    # ── SpO2 concern narrative ────────────────────────────────────────────
    spo2_concern = (
        f"Resting SpO2 of {spo2_val:.0f}% (Apple Watch, 2026-05-21) is below the normal ≥97% range. "
        "OSA is resolved/historical and CPAP is discontinued. The 93% reading is monitored as a "
        "sleep quality and cardiovascular health indicator. Potential contributors include: "
        "(1) cardiometabolic load from resistant HTN and T2DM, (2) positional or nocturnal "
        "hypoventilation unrelated to OSA, (3) wearable measurement variability. "
        "If waking SpO2 drops below 92% consistently, report to Dr. Wenk for evaluation. "
        "Current monitoring: log SpO2 at wake-up daily in JARVIS sleep log."
    )

    # ── Recommendations ────────────────────────────────────────────────────
    sparsity_warning = (
        f" [DATA SPARSE: only {days_tracked} day(s) tracked — analysis based on limited data]"
        if data_is_sparse else ""
    )

    recommendations = [
        f"PRIORITY 1: Track sleep data for minimum 14 days before next council run{sparsity_warning}",
        f"Log morning HRV and SpO2 daily in JARVIS sleep log (current: HRV {hrv_val}ms, SpO2 {spo2_val:.0f}%)",
        f"Target ≥{target_sleep_hours:.1f} hours in bed per night — cardiometabolic patients benefit "
        "from upper end of normal sleep for recovery and glycemic control",
        "Maintain consistent bedtime/wake schedule (±30 min) — circadian consistency "
        "supports HRV recovery and metabolic regulation",
        "Pre-bed routine: no screens 30 min before sleep (blue light delays melatonin onset); "
        "room temp 65-68°F; no alcohol (suppresses REM and raises nocturnal SpO2 variability)",
        "Metoprolol note: pharmacological HRV suppression means wearable HRV readings "
        "underestimate true HRV — actual autonomic health may be better than 45ms suggests",
        f"SpO2 monitoring: alert threshold is waking SpO2 <92% consistently — "
        f"current {spo2_val:.0f}% is tracked but not attributed to active OSA (resolved/historical)",
        "A1c and HTN control are the primary levers for improving sleep quality — "
        "better glycemic control reduces overnight autonomic stress",
    ]

    log.info(
        "Sleep debt analysis: avg %.1fh/night, target %.1fh, debt %.1fh, quality %d/100 (%s)",
        recent_avg_hours, target_sleep_hours, sleep_debt_hours,
        quality_score, restorative_sleep_estimate,
    )

    return SleepDebtAnalysis(
        target_sleep_hours=target_sleep_hours,
        recent_avg_hours=round(recent_avg_hours, 2),
        sleep_debt_hours=sleep_debt_hours,
        sleep_quality_score=quality_score,
        restorative_sleep_estimate=restorative_sleep_estimate,
        hrv_sleep_correlation=hrv_sleep_correlation,
        spo2_concern=spo2_concern,
        recommendations=recommendations,
    )


# ---------------------------------------------------------------------------
# 4. Log Sleep Entry
# ---------------------------------------------------------------------------


def log_sleep(log_entry: SleepLog) -> dict:
    """
    Append a sleep log entry to ~/.jarvis/health/sleep_log.jsonl.

    Persists the entry as a JSON line and returns a daily summary dict
    with calculated metrics.

    Args:
        log_entry: SleepLog dataclass with the night's data.

    Returns:
        dict with the logged entry plus daily summary metrics.
    """
    _ensure_health_dir()

    entry_dict = asdict(log_entry)
    entry_dict["logged_at"] = datetime.now().isoformat()

    try:
        with open(_SLEEP_LOG, "a") as f:
            f.write(json.dumps(entry_dict) + "\n")
        log.info("Sleep log entry appended for %s: %.1fh", log_entry.date, log_entry.total_hours)
    except Exception as exc:
        log.error("Failed to write sleep log entry: %s", exc)
        return {"success": False, "error": str(exc)}

    # Build daily summary
    summary = {
        "success": True,
        "date": log_entry.date,
        "total_hours": log_entry.total_hours,
        "sleep_quality": log_entry.sleep_quality,
        "vs_target_hours": round(log_entry.total_hours - 8.0, 2),
        "nightly_debt": round(max(0.0, 8.0 - log_entry.total_hours), 2),
        "hrv_morning": log_entry.hrv_morning,
        "resting_hr": log_entry.resting_hr,
        "spo2_min": log_entry.spo2_min,
        "notes": log_entry.notes,
        "alerts": [],
    }

    # Alert checks
    if log_entry.total_hours < 6.0:
        summary["alerts"].append(
            f"SHORT SLEEP: {log_entry.total_hours:.1f}h < 6.0h minimum — significant sleep debt"
        )
    if log_entry.spo2_min is not None and log_entry.spo2_min < 90:
        summary["alerts"].append(
            f"LOW SpO2: {log_entry.spo2_min:.0f}% overnight nadir — clinically significant desaturation. "
            "Report to physician."
        )
    if log_entry.hrv_morning is not None and log_entry.hrv_morning < 40:
        summary["alerts"].append(
            f"VERY LOW HRV: {log_entry.hrv_morning:.0f}ms — likely high overnight physiological stress"
        )
    if log_entry.sleep_quality <= 3:
        summary["alerts"].append(
            f"POOR SLEEP QUALITY: {log_entry.sleep_quality}/10 — track pattern over next 3 nights"
        )

    return summary


# ---------------------------------------------------------------------------
# 5. 7-Day Sleep Summary
# ---------------------------------------------------------------------------


def get_sleep_7day_summary() -> dict:
    """
    Return 7-day sleep summary from the sleep log.

    Combines data from sleep_log.jsonl and health.db wearable_daily.

    Returns:
        dict with avg_hours, avg_hrv, avg_spo2, quality_trend, debt_hours,
        data_points, and actionable summary string.
    """
    entries = _load_sleep_log_entries(days=7)
    db_rows = _query_sleep_from_db(days=7)

    # Merge sources — prefer sleep_log entries (user-entered) for the same date
    log_dates = {e.get("date") for e in entries}
    for row in db_rows:
        row_date = row.get("date")
        if row_date and row_date not in log_dates:
            # Map DB row to sleep log structure
            entries.append({
                "date": row_date,
                "total_hours": row.get("sleep_hours") or row.get("sleep_total_hours"),
                "hrv_morning": row.get("hrv_sdnn") or row.get("hrv"),
                "resting_hr": row.get("resting_hr"),
                "spo2_min": row.get("spo2_min") or row.get("blood_oxygen"),
                "sleep_quality": None,
                "source": "wearable_daily",
            })

    # Filter to entries with valid hours
    valid = [e for e in entries if e.get("total_hours")]
    data_points = len(valid)

    if data_points == 0:
        # No data available — return known single-point data with sparsity warning
        return {
            "data_points": 0,
            "avg_hours": 7.5,          # hardcoded from health_state 2026-05-21
            "avg_hrv_morning": 45.0,   # hardcoded from Apple Health 2026-05-21
            "avg_spo2_min": 93.0,      # hardcoded from wearable 2026-05-21
            "avg_quality": None,
            "quality_trend": "insufficient_data",
            "7day_debt_hours": max(0.0, (8.0 - 7.5) * 7),
            "nightly_deficit": max(0.0, 8.0 - 7.5),
            "data_sources": ["health_state (hardcoded single data point)"],
            "data_warning": (
                "Only 1 data point available (2026-05-21). "
                "Track sleep for 14+ days for meaningful trend analysis."
            ),
            "summary": (
                "INSUFFICIENT DATA: Only 1 sleep data point available. "
                "Known: 7.5h on 2026-05-21 (Apple Health). "
                "Start logging daily to build a 7-day baseline."
            ),
        }

    hours_list = [float(e["total_hours"]) for e in valid]
    hrv_list = [float(e["hrv_morning"]) for e in valid if e.get("hrv_morning") is not None]
    spo2_list = [float(e["spo2_min"]) for e in valid if e.get("spo2_min") is not None]
    quality_list = [int(e["sleep_quality"]) for e in valid
                    if e.get("sleep_quality") is not None]

    avg_hours = round(sum(hours_list) / len(hours_list), 2)
    avg_hrv = round(sum(hrv_list) / len(hrv_list), 1) if hrv_list else None
    avg_spo2 = round(sum(spo2_list) / len(spo2_list), 1) if spo2_list else None
    avg_quality = round(sum(quality_list) / len(quality_list), 1) if quality_list else None

    # Quality trend (first 3 vs last 3 nights — if enough data)
    quality_trend = "insufficient_data"
    if len(quality_list) >= 4:
        sorted_entries = sorted(valid, key=lambda e: e.get("date", ""))
        early_q = [int(e["sleep_quality"]) for e in sorted_entries[:3] if e.get("sleep_quality")]
        late_q = [int(e["sleep_quality"]) for e in sorted_entries[-3:] if e.get("sleep_quality")]
        if early_q and late_q:
            delta = (sum(late_q) / len(late_q)) - (sum(early_q) / len(early_q))
            if delta > 0.5:
                quality_trend = "improving"
            elif delta < -0.5:
                quality_trend = "declining"
            else:
                quality_trend = "stable"

    nightly_deficit = max(0.0, 8.0 - avg_hours)
    debt_7day = round(nightly_deficit * 7, 1)

    # Construct summary
    spo2_flag = ""
    if avg_spo2 and avg_spo2 < 94:
        spo2_flag = f" ALERT: avg SpO2 {avg_spo2}% — nocturnal desaturations likely."

    summary = (
        f"{data_points} nights tracked | avg {avg_hours:.1f}h/night | "
        f"7-day debt {debt_7day:.1f}h | "
        f"avg HRV {avg_hrv}ms | avg SpO2 {avg_spo2}%.{spo2_flag}"
    )

    return {
        "data_points": data_points,
        "avg_hours": avg_hours,
        "avg_hrv_morning": avg_hrv,
        "avg_spo2_min": avg_spo2,
        "avg_quality": avg_quality,
        "quality_trend": quality_trend,
        "7day_debt_hours": debt_7day,
        "nightly_deficit": round(nightly_deficit, 2),
        "data_sources": ["sleep_log.jsonl", "health.db"],
        "summary": summary,
    }


# ---------------------------------------------------------------------------
# 6. Generate Sleep Medicine Referral
# ---------------------------------------------------------------------------


def generate_sleep_medicine_referral() -> str:
    """
    Generate a sleep quality summary document.

    OSA is resolved/historical — CPAP was trialed and discontinued. This document
    summarizes current sleep quality monitoring data rather than making an OSA referral.

    Returns:
        Multi-line string formatted as a clinical sleep quality summary.
    """
    osa = calculate_osa_risk_score()
    cpap_case = build_cpap_readiness_case()

    today = date.today().strftime("%B %d, %Y")

    referral = f"""
SLEEP QUALITY SUMMARY
Generated: {today}
System: JARVIS Health Intelligence (Sleep Quality Module)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PATIENT DEMOGRAPHICS
Name:       Chris Binion
DOB:        December 8, 1973 (Age 52)
Sex:        Male
BMI:        35.7 (Obesity Class II)
Email:      cbinion73@gmail.com

PRIMARY MEDICAL HISTORY (RELEVANT)
- Essential hypertension — resistant (on 4 antihypertensive agents)
  Current BP: 140/90 mmHg (at goal threshold, not below it)
  Medications: metoprolol ER (beta-blocker), + 3 additional agents
- Type 2 diabetes mellitus — not at glycemic goal
  A1c: 7.3% (goal <7.0%) as of 2026-05-08
- OSA: tested borderline 2019, CPAP trialed and discontinued as ineffective
  Status: RESOLVED/HISTORICAL — not active, not currently treated
- Sleeve gastrectomy (prior) — weight regain, current BMI 35.7
- Dyslipidemia / statin myopathy history

CURRENT WEARABLE METRICS (May 2026)
- Resting SpO2:    93.0% (Apple Watch, 2026-05-21) — monitored, not OSA-attributed
- HRV SDNN:        45 ms (Apple Health, 2026-05-21) — affected by metoprolol + cardiometabolic load
- Resting HR:      58 bpm (on metoprolol — pharmacologically lowered)
- Sleep duration:  7.5 h/night (not fully restorative per HRV-based analysis)

OSA HISTORICAL STATUS
{osa.ahi_estimate_range}

Sleep quality note:
{cpap_case.quantified_sleep_cost}

CPAP STATUS (HISTORICAL)
{cpap_case.patient_summary}

RECOMMENDED NEXT STEPS
""" + "\n".join(f"  • {s}" for s in cpap_case.recommended_next_steps) + f"""

SLEEP QUALITY TREATMENT GOALS
  ☐ Waking SpO2 ≥95% (alert if consistently <92%)
  ☐ HRV SDNN ≥53ms (shift from high to moderate mortality risk category)
  ☐ A1c <7.0% (primary lever for sleep architecture improvement)
  ☐ SBP <130 mmHg (tighter BP control reduces overnight autonomic load)
  ☐ Sleep ≥7.5h/night with consistent schedule

EVIDENCE BASIS
  - Logan AG et al. High prevalence of unrecognized OSA in drug-resistant hypertension.
    Hypertension 2001;17:2202–2208.
  - Drager LF et al. OSA and insulin resistance. Chest 2009;135:1538–1544.
  - Hillis GS et al. HRV and mortality. Meta-analysis 2024.

Generated by JARVIS Sleep Intelligence Module — not a substitute for clinical judgment.
All wearable metrics are estimates; OSA is resolved/historical — CPAP not indicated.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    log.info("Sleep medicine referral generated for Chris Binion")
    return referral.strip()


# ---------------------------------------------------------------------------
# 7. Sleep Recommendations
# ---------------------------------------------------------------------------


def get_sleep_recommendations() -> list[str]:
    """
    Return prioritized sleep recommendations for Chris Binion.

    Note: OSA is resolved/historical. CPAP was trialed and discontinued as ineffective.
    Recommendations focus on sleep quality, HRV monitoring, and cardiometabolic health.

    Returns:
        list[str] of prioritized recommendations, highest impact first.
    """
    return [
        "PRIORITY 1 — Track sleep for 14 days minimum before next JARVIS council run: "
        "Log bedtime, wake time, morning HRV (Apple Watch), and morning SpO2 daily. "
        "One data point (7.5h on 2026-05-21) is insufficient for meaningful trend analysis.",

        "PRIORITY 2 — Log morning HRV and SpO2 daily in JARVIS sleep log: Use the "
        "`log_sleep()` function or JARVIS voice logging. Target metrics: HRV >50ms, SpO2 >95%.",

        "PRIORITY 3 — A1c and HTN control are the primary levers for sleep quality: "
        "Improving A1c from 7.3% toward <7.0% and tightening BP control reduces overnight "
        "autonomic stress and supports HRV recovery.",

        "Consistent bedtime/wake schedule: Maintain within ±30 minutes daily, including "
        "weekends. Circadian consistency supports HRV recovery and metabolic regulation.",

        "Pre-bedtime routine: No screens 30 minutes before sleep (blue light delays "
        "melatonin onset). Room temperature 65-68°F. No alcohol — suppresses REM and "
        "increases nocturnal SpO2 variability.",

        "Metoprolol ER note: Your beta-blocker pharmacologically suppresses HRV by "
        "approximately 10-15ms. This means your true underlying HRV may be higher than "
        "45ms suggests. Track trend over time — sustained improvement reflects cardiometabolic gains.",

        "SpO2 monitoring: Current waking SpO2 93% is tracked as a sleep quality indicator. "
        "OSA is resolved/historical — CPAP was tried and discontinued. If waking SpO2 drops "
        "below 92% consistently, report to Dr. Wenk for evaluation.",

        "Sleep position: left lateral decubitus (left-side sleeping) improves nocturnal "
        "SpO2 and reduces cardiac afterload — beneficial for HTN patients.",

        "Weight loss (semaglutide + A1c control): continued progress toward BMI <30 "
        "will improve sleep architecture, SpO2, and HRV independent of OSA status.",
    ]


# ---------------------------------------------------------------------------
# 8. Assess CPAP Effect on Metrics
# ---------------------------------------------------------------------------


def assess_cpap_effect_on_metrics(months: int = 3) -> dict:
    """
    CPAP is not applicable — previously trialed and discontinued as ineffective.

    Returns a dict noting the historical CPAP status and the alternative
    interventions (A1c control, weight loss, HTN management) that drive
    the same cardiovascular benefits.

    Args:
        months: Not used — CPAP is discontinued.

    Returns:
        dict with CPAP discontinued notice and alternative intervention projections.
    """
    log.info("assess_cpap_effect_on_metrics: CPAP discontinued — returning not-applicable notice")

    return {
        "projection_months": months,
        "generated_date": date.today().isoformat(),
        "data_source": "JARVIS sleep_intelligence.py — CPAP discontinued, not applicable",
        "cpap_status": (
            "DISCONTINUED — CPAP was trialed and discontinued as ineffective. "
            "OSA is resolved/historical in JARVIS health DB. CPAP projections are not applicable."
        ),
        "alternative_interventions": {
            "a1c_control": "Improving A1c from 7.3% toward <7.0% reduces overnight autonomic stress",
            "bp_control": "Tighter BP management reduces cardiometabolic load on sleep architecture",
            "weight_loss": "Continued weight loss toward BMI <30 improves nocturnal SpO2 and HRV",
            "sleep_hygiene": "Consistent schedule, alcohol avoidance, and screen-time reduction",
        },
        "monitoring": {
            "spo2_target": "Waking SpO2 ≥95% — alert threshold <92%",
            "hrv_target": "HRV SDNN ≥53ms — current 45ms on metoprolol",
            "sleep_hours_target": "≥7.5h/night",
        },
        "composite_summary": (
            "CPAP not applicable (discontinued as ineffective). "
            "Primary sleep quality levers: A1c control, BP management, weight loss, sleep hygiene."
        ),
        "caveats": [
            "CPAP was tried and discontinued — not a candidate for CPAP retry without specialist re-evaluation",
            "SpO2 and HRV are monitored as sleep quality indicators, not OSA treatment metrics",
            "These projections are for digital twin calibration — not medical advice",
        ],
    }


# ---------------------------------------------------------------------------
# Module-level convenience
# ---------------------------------------------------------------------------


def run_full_sleep_assessment() -> dict:
    """
    Run the complete sleep intelligence assessment and return all components.

    Convenience function for council integration and briefing generation.

    Returns:
        dict with keys: osa_risk, cpap_case, sleep_debt, recommendations,
        cpap_3month_projection, referral_summary.
    """
    log.info("Running full sleep intelligence assessment for Chris Binion")

    osa = calculate_osa_risk_score()
    cpap_case = build_cpap_readiness_case()
    debt = analyze_sleep_debt()
    recs = get_sleep_recommendations()
    projection = assess_cpap_effect_on_metrics(months=3)

    return {
        "osa_risk": asdict(osa),
        "cpap_case": asdict(cpap_case),
        "sleep_debt": asdict(debt),
        "recommendations": recs,
        "cpap_3month_projection": projection,
        "referral_summary": (
            f"OSA status: RESOLVED/HISTORICAL. "
            f"Tested borderline 2019, CPAP trialed and discontinued as ineffective. "
            f"Sleep quality monitoring active via HRV ({osa.total_score}/100 borderline historical score). "
            "No sleep medicine referral indicated for OSA — focus on A1c, HTN, and weight management."
        ),
        "generated_at": datetime.now().isoformat(),
    }
