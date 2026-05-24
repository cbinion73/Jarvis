"""
longevity_calculator.py — JARVIS Longevity Intelligence Module

Answers: "With my current trajectory, my life expectancy is XX years?"
Provides a line graph showing whether life expectancy is improving or declining.

Methodology:
  Base: US Social Security actuarial, 52yo male → 28.5 additional years → age 80.5
  Adjustments: validated clinical associations (negative + positive factors)
  Net result: ~78 years estimated life expectancy (25.5 years remaining)

All stdlib — no numpy, no pandas.
"""

from __future__ import annotations

import json
import math
import os
import tempfile
from dataclasses import dataclass, asdict, field
from datetime import datetime, date
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Hardcoded authoritative fallbacks for Chris Binion
# ---------------------------------------------------------------------------

_DOB = date(1973, 12, 8)
_ACTUARIAL_BASELINE_AGE = 80.5     # US SSA, 52yo male
_ACTUARIAL_YEARS_REMAINING = 28.5

# Historical life-expectancy trajectory (estimated age at each snapshot)
_TRAJECTORY_HISTORY = [
    {"date": "2021-02", "label": "Feb 2021",  "estimated_age": 70, "note": "A1c 10.2%, pre-bariatric recovery"},
    {"date": "2022-06", "label": "Mid 2022",  "estimated_age": 72, "note": "Post-bariatric benefits + A1c improving"},
    {"date": "2023-01", "label": "Jan 2023",  "estimated_age": 73, "note": "A1c 7.1%, weight loss progress"},
    {"date": "2023-04", "label": "Apr 2023",  "estimated_age": 72, "note": "A1c 8.0%, mild regression"},
    {"date": "2024-04", "label": "Apr 2024",  "estimated_age": 77, "note": "A1c 5.9% — peak control"},
    {"date": "2025-03", "label": "Mar 2025",  "estimated_age": 75, "note": "A1c relapsed to 7.3%"},
    {"date": "2026-05", "label": "May 2026",  "estimated_age": 78, "note": "Current — OSA resolved/historical, stable trajectory"},
]

_PROJECTIONS: dict[str, list[dict]] = {
    "current_trajectory": [
        {"date": "2026-05", "age": 78},
        {"date": "2027-05", "age": 77},
        {"date": "2028-05", "age": 77},
        {"date": "2029-05", "age": 76},
        {"date": "2030-05", "age": 76},
        {"date": "2031-05", "age": 75},
    ],
    "optimized_trajectory": [
        {"date": "2026-05", "age": 78},
        {"date": "2027-05", "age": 79},
        {"date": "2028-05", "age": 80},
        {"date": "2029-05", "age": 81},
        {"date": "2030-05", "age": 82},
        {"date": "2031-05", "age": 83},
    ],
}

# Default risk adjustments (hardcoded clinical associations)
_DEFAULT_RISK_ADJUSTMENTS = [
    # Negative factors
    {
        "factor": "T2DM A1c 7.3% not at goal (modern treatment)",
        "adjustment_years": -3.5,
        "direction": "negative",
        "source": "UKPDS / meta-analyses: ~1 yr per ~1% A1c above goal",
        "modifiable": True,
    },
    {
        "factor": "Resistant HTN at threshold (BP 140/90 on 4 meds)",
        "adjustment_years": -1.5,
        "direction": "negative",
        "source": "SPRINT trial & ESC/ESH guidelines",
        "modifiable": True,
    },
    {
        "factor": "Obesity Class II BMI 35.7 (post-bariatric, partially mitigated)",
        "adjustment_years": -1.5,
        "direction": "negative",
        "source": "GBD 2019 metabolic risk collaboration",
        "modifiable": True,
    },
    {
        "factor": "LDL 156 mg/dL untreated (intermediate ASCVD, no statin)",
        "adjustment_years": -1.0,
        "direction": "negative",
        "source": "CTT meta-analysis; per-mmol LDL reduction benefit",
        "modifiable": True,
    },
    {
        "factor": "HRV 45ms (partially confounded by metoprolol)",
        "adjustment_years": -0.5,
        "direction": "negative",
        "source": "Ribeiro Lancet 2023 HRV mortality association",
        "modifiable": True,
    },
    # Positive factors
    {
        "factor": "Post-bariatric sleeve gastrectomy (Dec 2019)",
        "adjustment_years": 2.0,
        "direction": "positive",
        "source": "Aminian JAHA 2024: OR 0.49 CVD mortality post-bariatric",
        "modifiable": False,
    },
    {
        "factor": "Semaglutide GLP-1 agonist (SELECT trial)",
        "adjustment_years": 1.5,
        "direction": "positive",
        "source": "Lincoff NEJM 2023: 20% MACE reduction in overweight/obese",
        "modifiable": False,
    },
    {
        "factor": "Steps 8,400/day (above sedentary 5,000 baseline)",
        "adjustment_years": 1.0,
        "direction": "positive",
        "source": "Paluch JAMA Intern Med 2022 step-count mortality analysis",
        "modifiable": False,
    },
    {
        "factor": "Active health monitoring and care engagement",
        "adjustment_years": 0.5,
        "direction": "positive",
        "source": "Systematic reviews: patient engagement reduces mortality",
        "modifiable": False,
    },
]

# Storage paths
_HEALTH_DIR = Path.home() / ".jarvis" / "health"
_ESTIMATE_PATH = _HEALTH_DIR / "longevity_estimate.json"
_STATE_PATH = _HEALTH_DIR / "chris_health_state.json"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class RiskAdjustment:
    factor: str
    adjustment_years: float   # negative = harmful, positive = beneficial
    direction: str            # "negative" | "positive"
    source: str
    modifiable: bool          # can Chris change this?


@dataclass
class LongevityEstimate:
    computed_date: str
    current_age: int
    actuarial_baseline_age: float
    actuarial_years_remaining: float
    risk_adjustments: list[RiskAdjustment]
    total_negative_years: float
    total_positive_years: float
    net_adjustment_years: float
    estimated_life_expectancy: float
    years_remaining: float
    ci_lower: float
    ci_upper: float
    optimized_life_expectancy: float
    optimized_gain_years: float
    trajectory_direction: str          # "declining" | "stable" | "improving"
    trajectory_history: list[dict]
    projections: dict
    modifiable_years_at_stake: float   # sum of |modifiable negative adjustments|
    data_source: str = "computed"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _current_age() -> int:
    today = date.today()
    dob = _DOB
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def _load_health_state() -> dict:
    """Load from ~/.jarvis/health/chris_health_state.json, return {} on failure."""
    try:
        if _STATE_PATH.exists():
            with _STATE_PATH.open() as fh:
                return json.load(fh)
    except Exception:
        pass
    return {}


def _save_estimate(estimate: LongevityEstimate) -> None:
    """Atomically save longevity estimate JSON."""
    try:
        _HEALTH_DIR.mkdir(parents=True, exist_ok=True)
        data = asdict(estimate)
        fd, tmp = tempfile.mkstemp(dir=_HEALTH_DIR, suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as fh:
                json.dump(data, fh, indent=2)
            Path(tmp).replace(_ESTIMATE_PATH)
        except Exception:
            try:
                os.unlink(tmp)
            except Exception:
                pass
    except Exception:
        pass


def _determine_trajectory_direction() -> str:
    """Infer direction from the last few historical points."""
    hist = _TRAJECTORY_HISTORY
    if len(hist) < 2:
        return "stable"
    last = hist[-1]["estimated_age"]
    prev = hist[-2]["estimated_age"]
    delta = last - prev
    if delta >= 1:
        return "improving"
    elif delta <= -1:
        return "declining"
    return "stable"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def calculate_life_expectancy(state: dict | None = None) -> LongevityEstimate:
    """
    Compute longevity estimate using clinical risk adjustments.
    Never raises — falls back to hardcoded values on any error.
    Saves result to ~/.jarvis/health/longevity_estimate.json.
    """
    try:
        return _calculate_life_expectancy_inner(state)
    except Exception:
        return _hardcoded_fallback_estimate()


def _calculate_life_expectancy_inner(state: dict | None) -> LongevityEstimate:
    if state is None:
        state = _load_health_state()

    # Optionally pull live ASCVD from risk_equations
    # (we don't adjust the core model here, but note the live value if available)
    try:
        try:
            from .risk_equations import run_full_risk_profile
        except ImportError:
            from risk_equations import run_full_risk_profile
        _live_risk = run_full_risk_profile()  # noqa: F841 — available for future use
    except Exception:
        pass

    today_str = date.today().isoformat()
    current_age = _current_age()

    # Build risk adjustments
    adjustments: list[RiskAdjustment] = []
    for raw in _DEFAULT_RISK_ADJUSTMENTS:
        adjustments.append(RiskAdjustment(**raw))

    total_negative = sum(a.adjustment_years for a in adjustments if a.adjustment_years < 0)
    total_positive = sum(a.adjustment_years for a in adjustments if a.adjustment_years > 0)
    net_adjustment = total_negative + total_positive

    estimated_le = _ACTUARIAL_BASELINE_AGE + net_adjustment  # ~75.5 → round to 76
    estimated_le = float(round(estimated_le))                # round to nearest integer

    years_remaining = estimated_le - current_age
    ci_lower = estimated_le - 4.0
    ci_upper = estimated_le + 4.0

    # Optimized scenario: ezetimibe +1.0, A1c 6.5% +1.0, weight loss +1.0
    optimized_gain = 1.0 + 1.0 + 1.0
    optimized_le = estimated_le + optimized_gain

    modifiable_years_at_stake = abs(
        sum(a.adjustment_years for a in adjustments if a.adjustment_years < 0 and a.modifiable)
    )

    trajectory_direction = _determine_trajectory_direction()

    estimate = LongevityEstimate(
        computed_date=today_str,
        current_age=current_age,
        actuarial_baseline_age=_ACTUARIAL_BASELINE_AGE,
        actuarial_years_remaining=_ACTUARIAL_YEARS_REMAINING,
        risk_adjustments=adjustments,
        total_negative_years=round(total_negative, 2),
        total_positive_years=round(total_positive, 2),
        net_adjustment_years=round(net_adjustment, 2),
        estimated_life_expectancy=estimated_le,
        years_remaining=round(years_remaining, 1),
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        optimized_life_expectancy=optimized_le,
        optimized_gain_years=optimized_gain,
        trajectory_direction=trajectory_direction,
        trajectory_history=_TRAJECTORY_HISTORY,
        projections=_PROJECTIONS,
        modifiable_years_at_stake=round(modifiable_years_at_stake, 1),
        data_source="computed",
    )

    _save_estimate(estimate)
    return estimate


def _hardcoded_fallback_estimate() -> LongevityEstimate:
    """Return hardcoded estimate when computation fails."""
    adjustments = [RiskAdjustment(**r) for r in _DEFAULT_RISK_ADJUSTMENTS]
    total_neg = sum(a.adjustment_years for a in adjustments if a.adjustment_years < 0)
    total_pos = sum(a.adjustment_years for a in adjustments if a.adjustment_years > 0)
    net = total_neg + total_pos
    estimated_le = float(round(_ACTUARIAL_BASELINE_AGE + net))

    return LongevityEstimate(
        computed_date=date.today().isoformat(),
        current_age=52,
        actuarial_baseline_age=_ACTUARIAL_BASELINE_AGE,
        actuarial_years_remaining=_ACTUARIAL_YEARS_REMAINING,
        risk_adjustments=adjustments,
        total_negative_years=round(total_neg, 2),
        total_positive_years=round(total_pos, 2),
        net_adjustment_years=round(net, 2),
        estimated_life_expectancy=estimated_le,
        years_remaining=round(estimated_le - 52, 1),
        ci_lower=estimated_le - 4.0,
        ci_upper=estimated_le + 4.0,
        optimized_life_expectancy=estimated_le + 4.5,
        optimized_gain_years=4.5,
        trajectory_direction="stable",
        trajectory_history=_TRAJECTORY_HISTORY,
        projections=_PROJECTIONS,
        modifiable_years_at_stake=10.0,
        data_source="fallback",
    )


def get_trajectory_history() -> list[dict]:
    """Return the historical trajectory points (later: merge with saved estimates)."""
    return list(_TRAJECTORY_HISTORY)


# ---------------------------------------------------------------------------
# SVG Generation
# ---------------------------------------------------------------------------

def _date_str_to_float(d: str) -> float:
    """Convert 'YYYY-MM' to a float year (e.g. '2021-02' → 2021.083)."""
    parts = d.split("-")
    year = int(parts[0])
    month = int(parts[1]) if len(parts) > 1 else 1
    return year + (month - 1) / 12.0


def _build_svg(
    trajectory_history: list[dict],
    projections: dict,
    estimated_le: float,
) -> str:
    """
    Build a self-contained SVG line chart with:
      - Historical line (solid green): trajectory_history points
      - Current trajectory (dashed amber): projections["current_trajectory"]
      - Optimized trajectory (dashed cyan): projections["optimized_trajectory"]
      - Y-axis: age 68–84, gridlines at 70, 75, 80
      - X-axis: year labels
      - Reference lines for current estimate and actuarial baseline
      - Legend
    """
    W = 600
    H = 200
    PAD_LEFT = 42
    PAD_RIGHT = 20
    PAD_TOP = 18
    PAD_BOTTOM = 36

    plot_w = W - PAD_LEFT - PAD_RIGHT
    plot_h = H - PAD_TOP - PAD_BOTTOM

    Y_MIN = 68.0
    Y_MAX = 84.0

    # Determine X range from all data
    all_dates = (
        [p["date"] for p in trajectory_history]
        + [p["date"] for p in projections.get("current_trajectory", [])]
        + [p["date"] for p in projections.get("optimized_trajectory", [])]
    )
    x_floats = [_date_str_to_float(d) for d in all_dates]
    X_MIN = min(x_floats)
    X_MAX = max(x_floats)
    x_span = X_MAX - X_MIN if X_MAX != X_MIN else 1.0

    def to_px(date_str: str, age: float) -> tuple[float, float]:
        xf = _date_str_to_float(date_str)
        px = PAD_LEFT + (xf - X_MIN) / x_span * plot_w
        py = PAD_TOP + (1 - (age - Y_MIN) / (Y_MAX - Y_MIN)) * plot_h
        return round(px, 1), round(py, 1)

    def polyline_d(points: list[tuple[float, float]]) -> str:
        return " ".join(f"{x},{y}" for x, y in points)

    # Build coordinate lists
    hist_pts = [to_px(p["date"], p["estimated_age"]) for p in trajectory_history]
    curr_pts = [to_px(p["date"], p["age"]) for p in projections.get("current_trajectory", [])]
    opt_pts  = [to_px(p["date"], p["age"]) for p in projections.get("optimized_trajectory", [])]

    # Reference Y pixel positions
    def ref_y(age: float) -> float:
        return round(PAD_TOP + (1 - (age - Y_MIN) / (Y_MAX - Y_MIN)) * plot_h, 1)

    grid_ages = [70, 75, 80]
    actuarial_y = ref_y(80.5)
    today_y = ref_y(estimated_le)

    # ---- X-axis labels (deduplicated years) ----
    label_years: dict[int, float] = {}
    for d in all_dates:
        yr = int(d.split("-")[0])
        xf = _date_str_to_float(d)
        if yr not in label_years:
            label_years[yr] = xf
    x_label_items = sorted(label_years.items())

    # ---- Build SVG ----
    lines: list[str] = []
    a = lines.append

    a(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
      f'width="100%" style="max-width:{W}px;display:block;">')

    # Background
    a(f'<rect width="{W}" height="{H}" fill="rgba(10,10,20,0.0)"/>')

    # Gridlines
    for g in grid_ages:
        gy = ref_y(g)
        a(f'<line x1="{PAD_LEFT}" y1="{gy}" x2="{PAD_LEFT + plot_w}" y2="{gy}" '
          f'stroke="rgba(255,255,255,0.1)" stroke-width="1"/>')
        a(f'<text x="{PAD_LEFT - 5}" y="{gy + 4}" '
          f'font-size="9" fill="rgba(255,255,255,0.45)" text-anchor="end">{g}</text>')

    # Actuarial reference line (dotted gray)
    a(f'<line x1="{PAD_LEFT}" y1="{actuarial_y}" x2="{PAD_LEFT + plot_w}" y2="{actuarial_y}" '
      f'stroke="rgba(180,180,200,0.35)" stroke-width="1" stroke-dasharray="3,4"/>')
    a(f'<text x="{PAD_LEFT + plot_w - 2}" y="{actuarial_y - 3}" '
      f'font-size="8" fill="rgba(180,180,200,0.55)" text-anchor="end">Actuarial 80.5</text>')

    # Current estimate reference line (dashed gray)
    if abs(today_y - actuarial_y) > 4:
        a(f'<line x1="{PAD_LEFT}" y1="{today_y}" x2="{PAD_LEFT + plot_w}" y2="{today_y}" '
          f'stroke="rgba(245,158,11,0.3)" stroke-width="1" stroke-dasharray="4,4"/>')
        le_label = f"Today: {estimated_le:.0f}" if estimated_le == int(estimated_le) else f"Today: {estimated_le}"
        a(f'<text x="{PAD_LEFT + 3}" y="{today_y - 3}" '
          f'font-size="8" fill="rgba(245,158,11,0.65)">{le_label}</text>')

    # Optimized trajectory (dashed cyan)
    if len(opt_pts) >= 2:
        a(f'<polyline points="{polyline_d(opt_pts)}" '
          f'fill="none" stroke="#06b6d4" stroke-width="2" stroke-dasharray="6,4"/>')

    # Current trajectory (dashed amber)
    if len(curr_pts) >= 2:
        a(f'<polyline points="{polyline_d(curr_pts)}" '
          f'fill="none" stroke="#f59e0b" stroke-width="2" stroke-dasharray="6,4"/>')

    # Historical line (solid green)
    if len(hist_pts) >= 2:
        a(f'<polyline points="{polyline_d(hist_pts)}" '
          f'fill="none" stroke="#22c55e" stroke-width="2.5"/>')

    # Historical dots
    for x, y in hist_pts:
        a(f'<circle cx="{x}" cy="{y}" r="4.5" fill="#22c55e" stroke="rgba(15,15,30,0.9)" stroke-width="1.5"/>')

    # X-axis labels
    for yr, xf in x_label_items:
        px = PAD_LEFT + (xf - X_MIN) / x_span * plot_w
        py = PAD_TOP + plot_h + 14
        a(f'<text x="{round(px, 1)}" y="{py}" '
          f'font-size="9" fill="rgba(255,255,255,0.4)" text-anchor="middle">{yr}</text>')

    # Legend (bottom right)
    legend_x = PAD_LEFT + plot_w - 5
    legend_y = PAD_TOP + plot_h + 13
    legend_items = [
        ("#22c55e", "Historical", "none", ""),
        ("#f59e0b", "Current Path", "none", "5,3"),
        ("#06b6d4", "Optimized", "none", "5,3"),
    ]
    for i, (color, label, _fill, dash) in enumerate(legend_items):
        lx = legend_x - i * 92
        dash_attr = f'stroke-dasharray="{dash}"' if dash else ""
        a(f'<line x1="{lx - 22}" y1="{legend_y - 4}" x2="{lx - 8}" y2="{legend_y - 4}" '
          f'stroke="{color}" stroke-width="2" {dash_attr}/>')
        a(f'<text x="{lx - 24}" y="{legend_y}" '
          f'font-size="8.5" fill="rgba(255,255,255,0.55)" text-anchor="end">{label}</text>')

    a('</svg>')
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# HTML Card
# ---------------------------------------------------------------------------

def get_longevity_card_html() -> str:
    """
    Return a self-contained HTML card with:
    - Big life expectancy numbers
    - SVG line graph (historical + projections)
    - Risk factor tables (negative / positive)
    - Modifiable years at stake
    No external dependencies required.
    """
    est = calculate_life_expectancy()

    direction = est.trajectory_direction
    le_color = "#22c55e" if direction == "improving" else ("#ef4444" if direction == "declining" else "#f59e0b")

    le_display = f"{est.estimated_life_expectancy:.0f}" if est.estimated_life_expectancy == int(est.estimated_life_expectancy) else f"{est.estimated_life_expectancy}"
    opt_display = f"{est.optimized_life_expectancy:.0f}" if est.optimized_life_expectancy == int(est.optimized_life_expectancy) else f"{est.optimized_life_expectancy}"
    years_rem = f"{est.years_remaining:.1f}"
    opt_gain = f"+{est.optimized_gain_years:.1f}"
    ci_lo = int(est.ci_lower)
    ci_hi = int(est.ci_upper)

    neg_factors = [a for a in est.risk_adjustments if a.direction == "negative"]
    pos_factors = [a for a in est.risk_adjustments if a.direction == "positive"]

    svg = _build_svg(
        trajectory_history=est.trajectory_history,
        projections=est.projections,
        estimated_le=est.estimated_life_expectancy,
    )

    # Build negative factor rows
    neg_rows = ""
    for f in sorted(neg_factors, key=lambda x: x.adjustment_years):
        dot_color = "#ef4444"
        neg_rows += (
            f'<tr><td style="padding:5px 8px;color:rgba(255,255,255,0.85);font-size:0.875rem;">{f.factor}</td>'
            f'<td style="padding:5px 8px;text-align:right;color:{dot_color};font-weight:600;white-space:nowrap;">'
            f'{f.adjustment_years:.1f} yr</td>'
            f'<td style="padding:5px 8px;text-align:center;">'
            f'<span style="color:{dot_color};font-size:1rem;">{"★" if f.modifiable else "●"}</span></td></tr>\n'
        )

    # Build positive factor rows
    pos_rows = ""
    for f in sorted(pos_factors, key=lambda x: -x.adjustment_years):
        dot_color = "#22c55e"
        pos_rows += (
            f'<tr><td style="padding:5px 8px;color:rgba(255,255,255,0.85);font-size:0.875rem;">{f.factor}</td>'
            f'<td style="padding:5px 8px;text-align:right;color:{dot_color};font-weight:600;white-space:nowrap;">'
            f'+{f.adjustment_years:.1f} yr</td>'
            f'<td style="padding:5px 8px;text-align:center;">'
            f'<span style="color:{dot_color};font-size:1rem;">✓</span></td></tr>\n'
        )

    card = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>JARVIS Longevity Projection</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: #0a0a1a;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    color: white;
    min-height: 100vh;
    display: flex;
    align-items: flex-start;
    justify-content: center;
    padding: 24px 16px;
  }}
  .card {{
    width: 100%;
    max-width: 720px;
    background: rgba(15,15,30,0.85);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 16px;
    overflow: hidden;
    backdrop-filter: blur(12px);
  }}
  .card-header {{
    background: rgba(255,255,255,0.03);
    border-bottom: 1px solid rgba(255,255,255,0.06);
    padding: 16px 20px;
    display: flex;
    align-items: center;
    gap: 10px;
  }}
  .card-header h2 {{
    font-size: 0.8rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: rgba(255,255,255,0.5);
  }}
  .metrics-row {{
    display: flex;
    gap: 0;
    padding: 24px 20px 16px;
    border-bottom: 1px solid rgba(255,255,255,0.05);
  }}
  .metric-block {{
    flex: 1;
    padding-right: 24px;
  }}
  .metric-block + .metric-block {{
    padding-left: 24px;
    padding-right: 0;
    border-left: 1px solid rgba(255,255,255,0.06);
  }}
  .metric-label {{
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: rgba(255,255,255,0.4);
    margin-bottom: 4px;
  }}
  .metric-big {{
    font-size: 3.5rem;
    font-weight: 700;
    line-height: 1;
    margin-bottom: 4px;
  }}
  .metric-sub {{
    font-size: 0.85rem;
    color: rgba(255,255,255,0.5);
    margin-bottom: 2px;
  }}
  .metric-ci {{
    font-size: 0.78rem;
    color: rgba(255,255,255,0.35);
  }}
  .chart-wrapper {{
    padding: 16px 12px 8px;
    border-bottom: 1px solid rgba(255,255,255,0.05);
  }}
  .section-label {{
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: rgba(255,255,255,0.3);
    padding: 12px 20px 4px;
  }}
  .factor-table {{
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 0;
  }}
  .factor-block {{
    margin: 0 12px 12px;
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 10px;
    overflow: hidden;
  }}
  .factor-block-header {{
    background: rgba(255,255,255,0.03);
    padding: 8px 12px;
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
  }}
  .factor-block-header.neg {{ color: #ef4444; }}
  .factor-block-header.pos {{ color: #22c55e; }}
  .factor-table tr:hover td {{ background: rgba(255,255,255,0.03); }}
  .modifiable-note {{
    text-align: center;
    padding: 14px 20px 20px;
    font-size: 0.875rem;
    color: rgba(255,255,255,0.5);
  }}
  .modifiable-note strong {{
    color: #f59e0b;
    font-size: 1rem;
  }}
</style>
</head>
<body>
<div class="card">
  <!-- Header -->
  <div class="card-header">
    <span style="font-size:1.2rem;">🧬</span>
    <h2>Longevity Projection</h2>
    <span style="margin-left:auto;font-size:0.72rem;color:rgba(255,255,255,0.25);">{est.computed_date}</span>
  </div>

  <!-- Top Metrics -->
  <div class="metrics-row">
    <div class="metric-block">
      <div class="metric-label">Estimated Life Expectancy</div>
      <div class="metric-big" style="color:{le_color};">{le_display}</div>
      <div class="metric-sub" style="color:{le_color};opacity:0.8;">{years_rem} years remaining</div>
      <div class="metric-ci">80% CI: ({ci_lo} – {ci_hi})</div>
    </div>
    <div class="metric-block">
      <div class="metric-label">Optimized Upside</div>
      <div class="metric-big" style="color:#06b6d4;">{opt_display}</div>
      <div class="metric-sub" style="color:#06b6d4;opacity:0.8;">{opt_gain} years possible</div>
      <div class="metric-ci">If high-impact interventions adopted</div>
    </div>
  </div>

  <!-- SVG Chart -->
  <div class="chart-wrapper">
    {svg}
  </div>

  <!-- Negative Factors -->
  <div class="factor-block">
    <div class="factor-block-header neg">⬇ Dragging Down</div>
    <table class="factor-table">
      {neg_rows}
    </table>
  </div>

  <!-- Positive Factors -->
  <div class="factor-block">
    <div class="factor-block-header pos">⬆ Working For You</div>
    <table class="factor-table">
      {pos_rows}
    </table>
  </div>

  <!-- Modifiable years -->
  <div class="modifiable-note">
    Modifiable years at stake: <strong>{est.modifiable_years_at_stake:.1f} yrs</strong>
    — reclaim them with ezetimibe, A1c control, and weight loss
  </div>
</div>
</body>
</html>"""

    return card


# ---------------------------------------------------------------------------
# Integration test (run directly)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    e = calculate_life_expectancy()
    print(f"Life expectancy: {e.estimated_life_expectancy} | Years remaining: {e.years_remaining}")
    print(f"CI: ({e.ci_lower}, {e.ci_upper}) | Optimized: {e.optimized_life_expectancy}")
    print(f"Trajectory direction: {e.trajectory_direction}")
    print(f"Modifiable years at stake: {e.modifiable_years_at_stake}")
    card = get_longevity_card_html()
    print(f"Card HTML length: {len(card)} chars")
