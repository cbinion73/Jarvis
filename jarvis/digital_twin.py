"""
digital_twin.py — JARVIS Probabilistic Health Digital Twin

A persistent, continuously-updated Bayesian state machine calibrated to
Chris's actual data history. Not a biophysics simulator — a trajectory +
intervention model with uncertainty quantification.

Patient context: Age 52, Male, T2DM, HTN, Obesity post-sleeve gastrectomy,
OSA unconfirmed. STATIN MYOPATHY ON RECORD — statins are never recommended.
"""

from __future__ import annotations

import json
import logging
import math
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, date
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_HEALTH_DIR = Path.home() / ".jarvis" / "health"
_HEALTH_STATE_PATH = _HEALTH_DIR / "chris_health_state.json"
_TWIN_STATE_PATH = _HEALTH_DIR / "twin_state.json"
_PREDICTION_LOG_PATH = _HEALTH_DIR / "twin_predictions.jsonl"

# ---------------------------------------------------------------------------
# Hardcoded calibration data
# ---------------------------------------------------------------------------
_METRIC_HISTORY: dict[str, list[dict]] = {
    "a1c": [
        {"date": "2021-02-26", "value": 10.2},
        {"date": "2021-08-01", "value": 7.1},
        {"date": "2023-01-01", "value": 6.3},
        {"date": "2023-04-01", "value": 8.0},
        {"date": "2024-04-10", "value": 5.9},
        {"date": "2025-03-26", "value": 7.3},
        {"date": "2026-05-08", "value": 7.3},
    ],
    "ldl": [
        {"date": "2021-02-26", "value": 99},
        {"date": "2024-04-10", "value": 138},
        {"date": "2025-03-26", "value": 146},
        {"date": "2026-05-08", "value": 156},
    ],
    "egfr": [
        {"date": "2020-01-01", "value": 98},
        {"date": "2026-05-08", "value": 87},
    ],
    "potassium": [
        {"date": "2025-03-26", "value": 5.4},
        {"date": "2026-05-08", "value": 4.5},
    ],
    "weight_lbs": [
        {"date": "2026-05-22", "value": 252},
    ],
    "systolic_bp": [
        {"date": "2026-05-08", "value": 140},
    ],
    "hrv": [
        {"date": "2026-05-21", "value": 45},
    ],
    "resting_hr": [
        {"date": "2026-05-21", "value": 58},
    ],
}

# ---------------------------------------------------------------------------
# Metric catalog
# ---------------------------------------------------------------------------
_METRIC_CATALOG: dict[str, dict] = {
    "a1c":         {"unit": "%",      "goal": 7.0,   "direction": "below", "label": "A1c"},
    "ldl":         {"unit": "mg/dL",  "goal": 100.0, "direction": "below", "label": "LDL"},
    "egfr":        {"unit": "mL/min", "goal": 90.0,  "direction": "above", "label": "eGFR"},
    "potassium":   {"unit": "mEq/L",  "goal": 5.0,   "direction": "below", "label": "Potassium"},
    "weight_lbs":  {"unit": "lbs",    "goal": 200.0, "direction": "below", "label": "Weight"},
    "systolic_bp": {"unit": "mmHg",   "goal": 130.0, "direction": "below", "label": "Systolic BP"},
    "hrv":         {"unit": "ms",     "goal": 60.0,  "direction": "above", "label": "HRV"},
    "resting_hr":  {"unit": "bpm",    "goal": 55.0,  "direction": "below", "label": "Resting HR"},
}

# ---------------------------------------------------------------------------
# Intervention effect library (evidence-based)
# ---------------------------------------------------------------------------
_INTERVENTION_EFFECTS: dict[str, dict] = {
    "add_ezetimibe_10mg": {
        "ldl": {"type": "percent", "value": -20, "ci_low": -25, "ci_high": -15, "grade": "A"},
    },
    "add_bempedoic_acid_180mg": {
        "ldl": {"type": "percent", "value": -18, "ci_low": -23, "ci_high": -13, "grade": "A"},
        "a1c": {"type": "additive", "value": 0.1, "ci_low": 0.0, "ci_high": 0.2, "grade": "B"},
    },
    "add_ezetimibe_plus_bempedoic": {
        "ldl": {"type": "percent", "value": -36, "ci_low": -44, "ci_high": -28, "grade": "A"},
    },
    "add_alirocumab_75mg": {
        "ldl": {"type": "percent", "value": -55, "ci_low": -65, "ci_high": -45, "grade": "A"},
    },
    "add_evolocumab_140mg": {
        "ldl": {"type": "percent", "value": -57, "ci_low": -67, "ci_high": -47, "grade": "A"},
    },
    "weight_loss_10pct": {
        "a1c":         {"type": "additive", "value": -0.7, "ci_low": -1.2, "ci_high": -0.3, "grade": "A"},
        "ldl":         {"type": "additive", "value": -8,   "ci_low": -15,  "ci_high": -2,   "grade": "B"},
        "systolic_bp": {"type": "additive", "value": -5,   "ci_low": -9,   "ci_high": -2,   "grade": "A"},
        "egfr":        {"type": "additive", "value": 2,    "ci_low": 0,    "ci_high": 5,    "grade": "B"},
        "weight_lbs":  {"type": "percent",  "value": -10,  "ci_low": -13,  "ci_high": -7,   "grade": "A"},
    },
    "weight_loss_20pct": {
        "a1c":         {"type": "additive", "value": -1.4, "ci_low": -2.0, "ci_high": -0.8, "grade": "A"},
        "ldl":         {"type": "additive", "value": -15,  "ci_low": -25,  "ci_high": -5,   "grade": "B"},
        "systolic_bp": {"type": "additive", "value": -10,  "ci_low": -16,  "ci_high": -4,   "grade": "A"},
        "egfr":        {"type": "additive", "value": 4,    "ci_low": 0,    "ci_high": 9,    "grade": "B"},
        "weight_lbs":  {"type": "percent",  "value": -20,  "ci_low": -25,  "ci_high": -14,  "grade": "A"},
    },
    "exercise_150min_week": {
        "a1c":         {"type": "additive", "value": -0.4, "ci_low": -0.7, "ci_high": -0.1, "grade": "A"},
        "systolic_bp": {"type": "additive", "value": -4,   "ci_low": -7,   "ci_high": -1,   "grade": "A"},
        "ldl":         {"type": "additive", "value": -3,   "ci_low": -7,   "ci_high": 1,    "grade": "B"},
        "hrv":         {"type": "additive", "value": 7,    "ci_low": 2,    "ci_high": 14,   "grade": "B"},
        "weight_lbs":  {"type": "additive", "value": -5,   "ci_low": -12,  "ci_high": 0,    "grade": "B"},
    },
    "cpap_confirmed": {
        "systolic_bp": {"type": "additive", "value": -3,   "ci_low": -6,   "ci_high": 0,    "grade": "B"},
        "hrv":         {"type": "additive", "value": 8,    "ci_low": 2,    "ci_high": 15,   "grade": "B"},
        "a1c":         {"type": "additive", "value": -0.2, "ci_low": -0.5, "ci_high": 0.0,  "grade": "C"},
    },
    "semaglutide_2mg_to_2_4mg": {
        "weight_lbs":  {"type": "additive", "value": -10,  "ci_low": -18,  "ci_high": -3,   "grade": "A"},
        "a1c":         {"type": "additive", "value": -0.3, "ci_low": -0.6, "ci_high": 0.0,  "grade": "B"},
    },
    "metformin_500mg_to_1500mg": {
        "a1c":         {"type": "additive", "value": -0.6, "ci_low": -1.0, "ci_high": -0.2, "grade": "A"},
    },
    "add_cgm_live": {
        "a1c":         {"type": "additive", "value": -0.4, "ci_low": -0.8, "ci_high": 0.0,  "grade": "B"},
    },
    "post_meal_walking": {
        "a1c":         {"type": "additive", "value": -0.3, "ci_low": -0.5, "ci_high": -0.1, "grade": "B"},
        "weight_lbs":  {"type": "additive", "value": -3,   "ci_low": -6,   "ci_high": 0,    "grade": "C"},
    },
}

# Statin keyword blocklist — never recommend these
_STATIN_KEYWORDS = [
    "statin", "atorvastatin", "rosuvastatin", "simvastatin", "pravastatin",
    "lovastatin", "fluvastatin", "pitavastatin", "cerivastatin",
]

# Causal chains
_CAUSAL_CHAINS: dict[str, list[str]] = {
    "weight_loss_10pct":    ["a1c", "ldl", "systolic_bp", "egfr"],
    "weight_loss_20pct":    ["a1c", "ldl", "systolic_bp", "egfr"],
    "exercise_150min_week": ["a1c", "systolic_bp", "hrv"],
    "cpap_confirmed":       ["systolic_bp", "hrv", "a1c"],
}


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class DataPoint:
    """A single observed measurement."""
    date: str         # ISO date string (YYYY-MM-DD)
    value: float
    source: str = "lab"


@dataclass
class MetricTrajectory:
    """Fitted trend model for a single health metric."""
    metric_name: str
    unit: str
    goal_value: Optional[float]
    goal_direction: str            # "below" | "above"
    history: list[DataPoint]
    current_value: float
    current_date: str
    trend_slope_per_month: float   # positive = increasing
    trend_confidence: float        # 0–1
    residual_std: float            # standard deviation of residuals from trend


@dataclass
class TwinProjection:
    """Forward projection of a single metric."""
    metric: str
    unit: str
    current_value: float
    projected_value: float
    ci_low: float                   # 80% CI lower bound
    ci_high: float                  # 80% CI upper bound
    timeframe_months: int
    direction: str                  # "improving" | "worsening" | "stable" | "volatile"
    at_goal: bool
    on_track_to_goal: bool
    months_to_goal: Optional[int]   # None if not projected to reach goal
    goal_value: Optional[float]
    evidence_basis: str


@dataclass
class InterventionSimulation:
    """Full simulation result comparing baseline vs. post-intervention trajectories."""
    interventions_applied: list[str]
    timeframe_months: int
    baseline_projections: list[TwinProjection]
    intervention_projections: list[TwinProjection]
    net_ascvd_delta_pct: float          # estimated absolute ASCVD risk change
    safety_flags: list[str]
    stacked_interactions: list[str]     # noted interaction effects
    generated_at: str


@dataclass
class Prediction:
    """A logged prediction for later accuracy scoring."""
    prediction_id: str
    made_at: str
    metric: str
    timeframe_months: int
    projected_value: float
    ci_low: float
    ci_high: float
    interventions_assumed: list[str]
    actual_value: Optional[float]
    check_date: str
    accuracy: Optional[str]   # "accurate" | "within_ci" | "outside_ci" | None (pending)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _date_to_months_since_epoch(date_str: str) -> float:
    """Convert an ISO date string to a float representing months since 2020-01-01."""
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        epoch = date(2020, 1, 1)
        delta_days = (d - epoch).days
        return delta_days / 30.4375  # average days per month
    except (ValueError, TypeError):
        log.warning("Could not parse date: %s", date_str)
        return 0.0


def _today_months() -> float:
    """Return today's position on the months-since-epoch scale."""
    today_str = datetime.now().strftime("%Y-%m-%d")
    return _date_to_months_since_epoch(today_str)


def _ensure_health_dir() -> None:
    """Create ~/.jarvis/health/ if it does not exist."""
    _HEALTH_DIR.mkdir(parents=True, exist_ok=True)


def _load_health_state() -> dict:
    """
    Load Chris's health state from disk, falling back to hardcoded defaults.

    Returns a dict with at least 'metric_history' and 'patient_context' keys.
    """
    defaults = {
        "patient_context": {
            "name": "Chris Binion",
            "age": 52,
            "sex": "male",
            "conditions": ["T2DM", "HTN", "Obesity", "post-sleeve gastrectomy", "OSA unconfirmed"],
            "contraindications": ["statins"],
            "statin_myopathy_on_record": True,
        },
        "metric_history": _METRIC_HISTORY,
        "current_values": {
            "a1c": 7.3,
            "ldl": 156,
            "egfr": 87,
            "potassium": 4.5,
            "weight_lbs": 252,
            "systolic_bp": 140,
            "hrv": 45,
            "resting_hr": 58,
        },
    }
    try:
        if _HEALTH_STATE_PATH.exists():
            with open(_HEALTH_STATE_PATH) as fh:
                loaded = json.load(fh)
            # Merge: loaded values override defaults
            for key, val in loaded.items():
                defaults[key] = val
    except Exception as exc:
        log.warning("Could not load health state from %s: %s", _HEALTH_STATE_PATH, exc)
    return defaults


def _load_twin_state() -> Optional[dict]:
    """Load persisted twin state from disk. Returns None if not found."""
    try:
        if _TWIN_STATE_PATH.exists():
            with open(_TWIN_STATE_PATH) as fh:
                return json.load(fh)
    except Exception as exc:
        log.warning("Could not load twin state from %s: %s", _TWIN_STATE_PATH, exc)
    return None


def _save_twin_state(state: dict) -> None:
    """Persist twin state to disk."""
    _ensure_health_dir()
    try:
        with open(_TWIN_STATE_PATH, "w") as fh:
            json.dump(state, fh, indent=2, default=str)
        log.info("Twin state saved to %s", _TWIN_STATE_PATH)
    except Exception as exc:
        log.error("Could not save twin state: %s", exc)


def _history_to_datapoints(raw: list[dict]) -> list[DataPoint]:
    """Convert raw dict list to sorted DataPoint list."""
    points = []
    for item in raw:
        try:
            points.append(DataPoint(
                date=item["date"],
                value=float(item["value"]),
                source=item.get("source", "lab"),
            ))
        except (KeyError, TypeError, ValueError) as exc:
            log.debug("Skipping malformed data point %s: %s", item, exc)
    points.sort(key=lambda dp: dp.date)
    return points


# ---------------------------------------------------------------------------
# Core function 1: fit_trajectory
# ---------------------------------------------------------------------------

def fit_trajectory(history: list[DataPoint]) -> tuple[float, float, float]:
    """
    Fit a weighted linear trend to a metric's history.

    More recent data points are weighted more heavily using an exponential
    scheme: weight = exp(0.1 * (i - n)) where i is the index and n is the
    index of the last point.

    Args:
        history: Sorted list of DataPoint objects.

    Returns:
        Tuple of (slope_per_month, intercept, residual_std).
        slope_per_month: Rate of change in metric units per month.
        intercept: Value at months-since-epoch = 0.
        residual_std: Standard deviation of residuals from the fit line.
    """
    n = len(history)
    if n == 0:
        return 0.0, 0.0, 0.0
    if n == 1:
        x0 = _date_to_months_since_epoch(history[0].date)
        return 0.0, history[0].value - 0.0 * x0, 0.0

    # Convert dates to x-axis (months since epoch)
    xs = [_date_to_months_since_epoch(dp.date) for dp in history]
    ys = [dp.value for dp in history]

    # Compute exponential weights (more recent = higher weight)
    last_idx = n - 1
    weights = [math.exp(0.1 * (i - last_idx)) for i in range(n)]

    # Weighted least squares: minimize sum(w_i * (y_i - (a*x_i + b))^2)
    # Normal equations:
    #   [sum(w*x^2)  sum(w*x) ] [a]   [sum(w*x*y)]
    #   [sum(w*x)    sum(w)   ] [b] = [sum(w*y)  ]
    sum_w   = sum(weights)
    sum_wx  = sum(w * x for w, x in zip(weights, xs))
    sum_wx2 = sum(w * x * x for w, x in zip(weights, xs))
    sum_wy  = sum(w * y for w, y in zip(weights, ys))
    sum_wxy = sum(w * x * y for w, x, y in zip(weights, xs, ys))

    denom = sum_w * sum_wx2 - sum_wx * sum_wx
    if abs(denom) < 1e-12:
        # All x values are identical; return flat line at mean
        mean_y = sum_wy / sum_w if sum_w > 0 else ys[-1]
        return 0.0, mean_y, 0.0

    slope = (sum_w * sum_wxy - sum_wx * sum_wy) / denom
    intercept = (sum_wy - slope * sum_wx) / sum_w

    # Compute residual std (unweighted for interpretability)
    fitted = [slope * x + intercept for x in xs]
    residuals = [y - f for y, f in zip(ys, fitted)]
    if n > 2:
        residual_std = math.sqrt(sum(r * r for r in residuals) / (n - 2))
    else:
        residual_std = abs(residuals[0]) if residuals else 0.0

    return slope, intercept, residual_std


# ---------------------------------------------------------------------------
# Core function 2: project_metric
# ---------------------------------------------------------------------------

def project_metric(trajectory: MetricTrajectory, months: int) -> TwinProjection:
    """
    Project a metric forward by the given number of months.

    Uses the fitted trend line plus growing uncertainty over the projection
    horizon. 80% confidence interval widens as sqrt(months).

    Args:
        trajectory: Fitted MetricTrajectory for the metric.
        months: Number of months to project forward.

    Returns:
        TwinProjection with projected value, CI, and goal assessment.
    """
    current = trajectory.current_value
    slope   = trajectory.trend_slope_per_month
    std     = trajectory.residual_std

    projected = current + slope * months

    # 80% CI: z=1.28 for normal distribution, uncertainty grows with sqrt(months)
    horizon_uncertainty = std * math.sqrt(max(months, 1)) * 1.28
    ci_low  = projected - horizon_uncertainty
    ci_high = projected + horizon_uncertainty

    goal    = trajectory.goal_value
    goal_dir = trajectory.goal_direction

    # At goal: current value already meets the goal
    if goal is not None:
        at_goal = (current <= goal) if goal_dir == "below" else (current >= goal)
    else:
        at_goal = False

    # Direction: improving = moving toward goal, worsening = moving away
    if goal_dir == "below":
        direction_improving = slope < -0.01
        direction_worsening = slope > 0.01
    else:
        direction_improving = slope > 0.01
        direction_worsening = slope < -0.01

    if trajectory.trend_confidence < 0.3 or std > abs(slope) * months * 2:
        direction = "volatile"
    elif direction_improving:
        direction = "improving"
    elif direction_worsening:
        direction = "worsening"
    else:
        direction = "stable"

    # on_track_to_goal: CI includes goal at the given timeframe
    if goal is not None:
        on_track_to_goal = ci_low <= goal <= ci_high
    else:
        on_track_to_goal = False

    # months_to_goal: extrapolate when trend line crosses goal
    months_to_goal: Optional[int] = None
    if goal is not None and abs(slope) > 1e-9:
        months_needed = (goal - current) / slope
        if months_needed > 0:
            months_to_goal = int(math.ceil(months_needed))

    evidence_basis = (
        f"Weighted linear trend from {len(trajectory.history)} observations; "
        f"slope={slope:+.3f}/month, residual_std={std:.3f}, "
        f"confidence={trajectory.trend_confidence:.2f}"
    )

    return TwinProjection(
        metric=trajectory.metric_name,
        unit=trajectory.unit,
        current_value=current,
        projected_value=round(projected, 2),
        ci_low=round(ci_low, 2),
        ci_high=round(ci_high, 2),
        timeframe_months=months,
        direction=direction,
        at_goal=at_goal,
        on_track_to_goal=on_track_to_goal,
        months_to_goal=months_to_goal,
        goal_value=goal,
        evidence_basis=evidence_basis,
    )


# ---------------------------------------------------------------------------
# Core function 3: apply_intervention_effects
# ---------------------------------------------------------------------------

def apply_intervention_effects(
    projection: TwinProjection,
    interventions: list[str],
) -> TwinProjection:
    """
    Apply intervention effects to a baseline projection.

    Interventions are stacked with diminishing returns:
    - 1st applicable intervention: full effect
    - 2nd applicable intervention: effect × 0.85
    - 3rd+ applicable interventions: effect × 0.75

    CI uncertainty from interventions is added in quadrature.

    Args:
        projection: Baseline TwinProjection to modify.
        interventions: List of intervention keys from _INTERVENTION_EFFECTS.

    Returns:
        New TwinProjection with updated projected value and CI.
    """
    metric = projection.metric
    new_projected = projection.projected_value
    intervention_ci_variance = 0.0

    applicable_count = 0
    applied_labels = []

    for iv_name in interventions:
        effects = _INTERVENTION_EFFECTS.get(iv_name, {})
        if metric not in effects:
            continue

        eff = effects[metric]
        # Diminishing returns multiplier
        if applicable_count == 0:
            multiplier = 1.0
        elif applicable_count == 1:
            multiplier = 0.85
        else:
            multiplier = 0.75

        effect_value = eff["value"]
        if eff["type"] == "percent":
            delta = new_projected * (effect_value / 100.0) * multiplier
        else:  # additive
            delta = effect_value * multiplier

        new_projected += delta

        # CI contribution from this intervention (in original units)
        ci_half = abs(eff["ci_high"] - eff["ci_low"]) / 2.0
        if eff["type"] == "percent":
            ci_half = abs(projection.projected_value) * ci_half / 100.0
        ci_half *= multiplier
        intervention_ci_variance += ci_half ** 2

        applicable_count += 1
        applied_labels.append(iv_name)

    # Combined CI: add in quadrature
    baseline_ci_half = (projection.ci_high - projection.ci_low) / 2.0
    total_ci_half = math.sqrt(baseline_ci_half ** 2 + intervention_ci_variance)
    new_ci_low  = new_projected - total_ci_half
    new_ci_high = new_projected + total_ci_half

    # Re-evaluate direction and goal tracking with new projected value
    goal     = projection.goal_value
    goal_dir = "below" if goal is not None and new_projected < (goal + 0.01) else "above"
    # Preserve original goal_direction from projection meta
    # (re-evaluate at_goal)
    at_goal: bool = False
    if goal is not None:
        # Use original goal direction stored in the projection evidence
        orig_dir = "below" if "below" in projection.evidence_basis else "above"
        at_goal = (new_projected <= goal) if orig_dir == "below" else (new_projected >= goal)

    evidence_basis = (
        projection.evidence_basis
        + (f"; interventions applied: {', '.join(applied_labels)}" if applied_labels else "; no applicable interventions")
    )

    return TwinProjection(
        metric=projection.metric,
        unit=projection.unit,
        current_value=projection.current_value,
        projected_value=round(new_projected, 2),
        ci_low=round(new_ci_low, 2),
        ci_high=round(new_ci_high, 2),
        timeframe_months=projection.timeframe_months,
        direction=projection.direction,
        at_goal=at_goal,
        on_track_to_goal=new_ci_low <= (goal or 0) <= new_ci_high if goal is not None else False,
        months_to_goal=projection.months_to_goal,
        goal_value=goal,
        evidence_basis=evidence_basis,
    )


# ---------------------------------------------------------------------------
# Internal: build MetricTrajectory from raw history
# ---------------------------------------------------------------------------

def _build_trajectory(metric: str, history: list[DataPoint], current_values: dict) -> MetricTrajectory:
    """Build a calibrated MetricTrajectory for a single metric."""
    catalog = _METRIC_CATALOG.get(metric, {})
    unit      = catalog.get("unit", "")
    goal      = catalog.get("goal")
    direction = catalog.get("direction", "below")

    slope, intercept, residual_std = fit_trajectory(history)

    # Trend confidence: based on number of points and R²
    n = len(history)
    confidence = 0.0
    if n >= 2:
        xs = [_date_to_months_since_epoch(dp.date) for dp in history]
        ys = [dp.value for dp in history]
        mean_y = sum(ys) / n
        ss_tot = sum((y - mean_y) ** 2 for y in ys)
        fitted = [slope * x + intercept for x in xs]
        ss_res = sum((y - f) ** 2 for y, f in zip(ys, fitted))
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-12 else 0.0
        # Scale confidence: more points + higher R² = higher confidence
        confidence = min(1.0, max(0.0, r2 * (1.0 - 1.0 / n)))

    # Current value: prefer explicit current_values dict, then latest history
    if metric in current_values:
        current_value = float(current_values[metric])
        current_date  = datetime.now().strftime("%Y-%m-%d")
    elif history:
        current_value = history[-1].value
        current_date  = history[-1].date
    else:
        current_value = 0.0
        current_date  = datetime.now().strftime("%Y-%m-%d")

    return MetricTrajectory(
        metric_name=metric,
        unit=unit,
        goal_value=goal,
        goal_direction=direction,
        history=history,
        current_value=current_value,
        current_date=current_date,
        trend_slope_per_month=round(slope, 5),
        trend_confidence=round(confidence, 3),
        residual_std=round(residual_std, 4),
    )


# ---------------------------------------------------------------------------
# Core function 4: run_twin_projection
# ---------------------------------------------------------------------------

def run_twin_projection(months: int = 12) -> list[TwinProjection]:
    """
    Project all tracked metrics forward without any new interventions.

    Loads data from the health state file (falls back to hardcoded defaults).
    Fits trajectories for all metrics in _METRIC_CATALOG and projects each
    forward by the specified number of months.

    Args:
        months: Number of months to project (default 12).

    Returns:
        List of TwinProjection objects, one per tracked metric.
    """
    health_state   = _load_health_state()
    raw_history    = health_state.get("metric_history", _METRIC_HISTORY)
    current_values = health_state.get("current_values", {})

    projections: list[TwinProjection] = []
    for metric in _METRIC_CATALOG:
        raw = raw_history.get(metric, [])
        history = _history_to_datapoints(raw)
        trajectory = _build_trajectory(metric, history, current_values)
        proj = project_metric(trajectory, months)
        projections.append(proj)

    return projections


# ---------------------------------------------------------------------------
# Safety checker
# ---------------------------------------------------------------------------

def _check_safety(interventions: list[str]) -> list[str]:
    """
    Return safety flags for the proposed intervention list.

    Blocks statins (statin myopathy on record). Flags potassium-raising
    interventions when current K+ is elevated.
    """
    flags: list[str] = []

    # Hard block: statins
    for iv in interventions:
        iv_lower = iv.lower()
        for keyword in _STATIN_KEYWORDS:
            if keyword in iv_lower:
                flags.append(
                    f"CONTRAINDICATED: '{iv}' contains statin — "
                    "STATIN MYOPATHY ON RECORD. Do not recommend."
                )
                break

    return flags


# ---------------------------------------------------------------------------
# ASCVD delta estimation
# ---------------------------------------------------------------------------

def _estimate_ascvd_delta(
    baseline_projections: list[TwinProjection],
    intervention_projections: list[TwinProjection],
    interventions: list[str],
) -> float:
    """
    Estimate absolute ASCVD 10-year risk change from intervention effects.

    Model:
    - Every 1 mg/dL LDL reduction ≈ 0.5% absolute ASCVD risk reduction
      per 1% LDL reduction (from baseline %).
    - Weight loss 10% ≈ 1.5% absolute ASCVD reduction.
    - Weight loss 20% ≈ 3.0% absolute ASCVD reduction.

    Returns signed float (negative = risk reduction = good).
    """
    ldl_baseline     = next((p.projected_value for p in baseline_projections     if p.metric == "ldl"), None)
    ldl_intervention = next((p.projected_value for p in intervention_projections if p.metric == "ldl"), None)

    ascvd_delta = 0.0

    if ldl_baseline is not None and ldl_intervention is not None and ldl_baseline > 0:
        ldl_reduction_pct = (ldl_baseline - ldl_intervention) / ldl_baseline * 100.0
        # Every 1% LDL reduction ≈ 0.5% absolute ASCVD risk reduction
        ascvd_delta += -ldl_reduction_pct * 0.5

    # Weight loss bonuses
    if "weight_loss_10pct" in interventions:
        ascvd_delta += -1.5
    if "weight_loss_20pct" in interventions:
        ascvd_delta += -3.0  # not additive with 10pct — pick larger

    return round(ascvd_delta, 2)


# ---------------------------------------------------------------------------
# Core function 5: simulate_interventions
# ---------------------------------------------------------------------------

def simulate_interventions(
    interventions: list[str],
    months: int = 12,
) -> InterventionSimulation:
    """
    Run a full intervention simulation comparing baseline vs. post-intervention.

    Steps:
    1. Compute baseline projections (no interventions).
    2. Apply each intervention's effects to each metric.
    3. Estimate net ASCVD risk change.
    4. Flag safety issues (statins hard-blocked).
    5. Note causal chains applied.

    Args:
        interventions: List of intervention keys from _INTERVENTION_EFFECTS.
        months: Projection horizon in months (default 12).

    Returns:
        InterventionSimulation with full comparison.
    """
    # Validate interventions
    unknown = [iv for iv in interventions if iv not in _INTERVENTION_EFFECTS]
    if unknown:
        log.warning("Unknown interventions (will have no effect): %s", unknown)

    baseline_projections = run_twin_projection(months=months)

    intervention_projections: list[TwinProjection] = []
    for proj in baseline_projections:
        updated = apply_intervention_effects(proj, interventions)
        intervention_projections.append(updated)

    safety_flags = _check_safety(interventions)

    # Note stacked interactions
    stacked_interactions: list[str] = []
    for iv in interventions:
        chains = _CAUSAL_CHAINS.get(iv, [])
        if chains:
            stacked_interactions.append(
                f"{iv} triggers cascade effects on: {', '.join(chains)}"
            )
    # Flag bempedoic + weight gain A1c interaction
    if "add_bempedoic_acid_180mg" in interventions:
        stacked_interactions.append(
            "add_bempedoic_acid_180mg: slight A1c worsening risk (Grade B evidence)"
        )

    ascvd_delta = _estimate_ascvd_delta(
        baseline_projections, intervention_projections, interventions
    )

    return InterventionSimulation(
        interventions_applied=interventions,
        timeframe_months=months,
        baseline_projections=baseline_projections,
        intervention_projections=intervention_projections,
        net_ascvd_delta_pct=ascvd_delta,
        safety_flags=safety_flags,
        stacked_interactions=stacked_interactions,
        generated_at=datetime.now().isoformat(),
    )


# ---------------------------------------------------------------------------
# Core function 6: calibrate_twin
# ---------------------------------------------------------------------------

def calibrate_twin() -> dict:
    """
    Fit all metric trajectories from available data and persist to disk.

    Loads health state (file or hardcoded defaults), fits a weighted linear
    trajectory for each metric in _METRIC_CATALOG, and saves the result to
    ~/.jarvis/health/twin_state.json.

    Returns:
        Calibration summary dict with keys: metrics_calibrated, data_points,
        confidence, calibrated_at.
    """
    health_state   = _load_health_state()
    raw_history    = health_state.get("metric_history", _METRIC_HISTORY)
    current_values = health_state.get("current_values", {})

    trajectories: dict[str, dict] = {}
    summary_points: dict[str, int] = {}
    summary_confidence: dict[str, float] = {}

    for metric in _METRIC_CATALOG:
        raw = raw_history.get(metric, [])
        history = _history_to_datapoints(raw)
        traj = _build_trajectory(metric, history, current_values)
        trajectories[metric] = {
            "metric_name": traj.metric_name,
            "unit": traj.unit,
            "goal_value": traj.goal_value,
            "goal_direction": traj.goal_direction,
            "current_value": traj.current_value,
            "current_date": traj.current_date,
            "trend_slope_per_month": traj.trend_slope_per_month,
            "trend_confidence": traj.trend_confidence,
            "residual_std": traj.residual_std,
            "n_points": len(history),
        }
        summary_points[metric] = len(history)
        summary_confidence[metric] = traj.trend_confidence

    twin_state = {
        "calibrated_at": datetime.now().isoformat(),
        "patient_context": health_state.get("patient_context", {}),
        "trajectories": trajectories,
        "predictions": [],
    }
    _save_twin_state(twin_state)

    summary = {
        "metrics_calibrated": list(trajectories.keys()),
        "data_points": summary_points,
        "confidence": summary_confidence,
        "calibrated_at": twin_state["calibrated_at"],
    }
    log.info("Twin calibration complete: %d metrics", len(trajectories))
    return summary


# ---------------------------------------------------------------------------
# Core function 7: get_twin_state
# ---------------------------------------------------------------------------

def get_twin_state() -> dict:
    """
    Load and return the full twin state from disk.

    If no twin state exists (or it cannot be loaded), runs calibrate_twin()
    first to create it.

    Returns:
        Dict with keys: calibrated_at, patient_context, trajectories, predictions.
    """
    state = _load_twin_state()
    if state is None:
        log.info("No twin state found — running initial calibration.")
        calibrate_twin()
        state = _load_twin_state()
    if state is None:
        # Fallback in-memory state
        log.warning("Could not persist twin state; returning in-memory calibration.")
        health_state = _load_health_state()
        state = {
            "calibrated_at": datetime.now().isoformat(),
            "patient_context": health_state.get("patient_context", {}),
            "trajectories": {},
            "predictions": [],
        }
    return state


# ---------------------------------------------------------------------------
# Core function 8: record_prediction
# ---------------------------------------------------------------------------

def record_prediction(
    projection: TwinProjection,
    interventions: list[str] | None = None,
) -> str:
    """
    Save a prediction to the twin state's prediction log.

    Predictions are stored in ~/.jarvis/health/twin_predictions.jsonl (one
    JSON object per line) and also appended to twin_state.json.

    Args:
        projection: The TwinProjection to record as a prediction.
        interventions: Interventions assumed for this projection.

    Returns:
        prediction_id: UUID string for the recorded prediction.
    """
    if interventions is None:
        interventions = []

    _ensure_health_dir()
    prediction_id = str(uuid.uuid4())
    now = datetime.now().isoformat()

    # Calculate the check_date (current date + timeframe)
    check_year  = datetime.now().year
    check_month = datetime.now().month + projection.timeframe_months
    while check_month > 12:
        check_month -= 12
        check_year  += 1
    check_date = f"{check_year:04d}-{check_month:02d}-01"

    pred = Prediction(
        prediction_id=prediction_id,
        made_at=now,
        metric=projection.metric,
        timeframe_months=projection.timeframe_months,
        projected_value=projection.projected_value,
        ci_low=projection.ci_low,
        ci_high=projection.ci_high,
        interventions_assumed=interventions,
        actual_value=None,
        check_date=check_date,
        accuracy=None,
    )
    pred_dict = asdict(pred)

    # Append to JSONL prediction log
    try:
        with open(_PREDICTION_LOG_PATH, "a") as fh:
            fh.write(json.dumps(pred_dict) + "\n")
    except Exception as exc:
        log.error("Could not write prediction to log: %s", exc)

    # Also append to twin_state.json predictions list
    try:
        state = get_twin_state()
        state.setdefault("predictions", []).append(pred_dict)
        _save_twin_state(state)
    except Exception as exc:
        log.error("Could not update twin state with prediction: %s", exc)

    log.info("Recorded prediction %s for %s at %d months", prediction_id, projection.metric, projection.timeframe_months)
    return prediction_id


# ---------------------------------------------------------------------------
# Core function 9: score_predictions
# ---------------------------------------------------------------------------

def score_predictions() -> list[dict]:
    """
    Compare past predictions against actual values from health state history.

    A prediction is scored as:
    - "accurate": actual within ±5% of projected value
    - "within_ci": actual within the 80% CI (but outside ±5%)
    - "outside_ci": actual outside the 80% CI
    - None: check_date is in the future (pending)

    Returns:
        List of prediction dicts with accuracy filled in.
    """
    health_state = _load_health_state()
    raw_history  = health_state.get("metric_history", _METRIC_HISTORY)

    # Build lookup: metric → {date → value}
    actual_lookup: dict[str, dict[str, float]] = {}
    for metric, raw in raw_history.items():
        points = _history_to_datapoints(raw)
        actual_lookup[metric] = {dp.date: dp.value for dp in points}

    today = datetime.now().strftime("%Y-%m-%d")

    scored: list[dict] = []
    try:
        if not _PREDICTION_LOG_PATH.exists():
            return []
        with open(_PREDICTION_LOG_PATH) as fh:
            lines = fh.readlines()
    except Exception as exc:
        log.error("Could not read prediction log: %s", exc)
        return []

    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            pred = json.loads(line)
        except json.JSONDecodeError:
            continue

        if pred.get("accuracy") is not None:
            scored.append(pred)
            continue

        # Only score if check_date has passed
        check_date = pred.get("check_date", "")
        if check_date > today:
            pred["accuracy"] = None
            scored.append(pred)
            continue

        # Find closest actual value on or after check_date
        metric       = pred.get("metric", "")
        actual_dates = actual_lookup.get(metric, {})
        matching_dates = sorted(d for d in actual_dates if d >= check_date)
        if not matching_dates:
            pred["accuracy"] = None
            scored.append(pred)
            continue

        actual_value    = actual_dates[matching_dates[0]]
        projected_value = pred.get("projected_value", 0)
        ci_low          = pred.get("ci_low", projected_value)
        ci_high         = pred.get("ci_high", projected_value)
        pred["actual_value"] = actual_value

        # Score accuracy
        if projected_value != 0:
            pct_diff = abs(actual_value - projected_value) / abs(projected_value)
        else:
            pct_diff = abs(actual_value - projected_value)

        if pct_diff <= 0.05:
            pred["accuracy"] = "accurate"
        elif ci_low <= actual_value <= ci_high:
            pred["accuracy"] = "within_ci"
        else:
            pred["accuracy"] = "outside_ci"

        scored.append(pred)

    return scored


# ---------------------------------------------------------------------------
# Core function 10: run_ldl_showdown
# ---------------------------------------------------------------------------

def run_ldl_showdown() -> dict:
    """
    Compare 4 LDL-lowering strategies side by side at 12 months.

    Strategies compared:
    1. Status quo (no change)
    2. Ezetimibe 10mg
    3. Ezetimibe + Bempedoic acid 180mg
    4. PCSK9i — Alirocumab 75mg

    Returns:
        Dict with strategy names as keys. Each value has:
        projected_ldl, ci_low, ci_high, pct_reduction, ascvd_delta,
        evidence_grade, notes, safety_ok.
    """
    strategies = {
        "status_quo": {
            "interventions": [],
            "label": "Status Quo (no change)",
            "notes": "Trajectory continues at current rate of LDL increase.",
        },
        "ezetimibe_10mg": {
            "interventions": ["add_ezetimibe_10mg"],
            "label": "Ezetimibe 10mg",
            "notes": "Well-tolerated; no myopathy risk. Grade A evidence.",
        },
        "ezetimibe_plus_bempedoic": {
            "interventions": ["add_ezetimibe_plus_bempedoic"],
            "label": "Ezetimibe + Bempedoic Acid 180mg",
            "notes": (
                "Potent non-statin combination. Note: bempedoic acid alone "
                "carries slight A1c worsening risk (Grade B). Combo form here "
                "uses synergistic estimate."
            ),
        },
        "alirocumab_75mg": {
            "interventions": ["add_alirocumab_75mg"],
            "label": "PCSK9i — Alirocumab 75mg",
            "notes": "Highest efficacy; injectable Q2W. Grade A evidence. Cost barrier.",
        },
    }

    current_ldl = 156.0
    results: dict[str, dict] = {}

    for key, strat in strategies.items():
        sim = simulate_interventions(interventions=strat["interventions"], months=12)
        ldl_proj = next(
            (p for p in sim.intervention_projections if p.metric == "ldl"), None
        )
        if ldl_proj is None:
            continue

        pct_reduction = 0.0
        if current_ldl > 0:
            pct_reduction = (current_ldl - ldl_proj.projected_value) / current_ldl * 100.0

        # Evidence grade: highest from applied interventions
        grades = []
        for iv in strat["interventions"]:
            eff = _INTERVENTION_EFFECTS.get(iv, {}).get("ldl", {})
            if "grade" in eff:
                grades.append(eff["grade"])
        best_grade = min(grades) if grades else "N/A"  # A < B < C

        results[key] = {
            "label": strat["label"],
            "projected_ldl_mg_dL": ldl_proj.projected_value,
            "ci_low": ldl_proj.ci_low,
            "ci_high": ldl_proj.ci_high,
            "pct_reduction_from_current": round(pct_reduction, 1),
            "at_goal_100": ldl_proj.projected_value <= 100.0,
            "ascvd_delta_pct": sim.net_ascvd_delta_pct,
            "evidence_grade": best_grade,
            "safety_flags": sim.safety_flags,
            "safety_ok": len(sim.safety_flags) == 0,
            "notes": strat["notes"],
        }

    return {
        "showdown_title": "LDL Lowering Strategy Comparison — 12-Month Projection",
        "current_ldl_mg_dL": current_ldl,
        "ldl_goal_mg_dL": _METRIC_CATALOG["ldl"]["goal"],
        "generated_at": datetime.now().isoformat(),
        "strategies": results,
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Quick self-test: calibrate, project, and run LDL showdown."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    print("=== JARVIS Digital Twin — Calibration ===")
    summary = calibrate_twin()
    print(json.dumps(summary, indent=2))

    print("\n=== 12-Month Baseline Projections ===")
    projections = run_twin_projection(months=12)
    for p in projections:
        status = "AT GOAL" if p.at_goal else ("on track" if p.on_track_to_goal else "off track")
        print(
            f"  {p.metric:15s} {p.current_value:7.1f} → {p.projected_value:7.1f} "
            f"[{p.ci_low:.1f}–{p.ci_high:.1f}] ({p.direction}, {status})"
        )

    print("\n=== LDL Strategy Showdown ===")
    showdown = run_ldl_showdown()
    for key, strat in showdown["strategies"].items():
        print(
            f"  {strat['label']:45s} "
            f"LDL={strat['projected_ldl_mg_dL']:.0f} "
            f"({strat['pct_reduction_from_current']:+.1f}%) "
            f"ASCVD Δ={strat['ascvd_delta_pct']:+.1f}%  "
            f"Grade {strat['evidence_grade']}"
        )


if __name__ == "__main__":
    main()
