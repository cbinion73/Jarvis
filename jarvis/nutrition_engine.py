"""
nutrition_engine.py — JARVIS Nutrition & Metabolic Intelligence
===============================================================
Post-bariatric nutrition tracking, micronutrient assessment, and GLP-1
meal timing guidance tailored to Chris's clinical profile:

  • 52yo male, T2DM (A1c 7.3%), sleeve gastrectomy Dec 2019 (6.5yr ago)
  • Semaglutide 2mg weekly, metformin ER 500mg
  • BMI 35.7, weight ~252 lbs, height 5'10.5"
  • Protein target 90-120g/day
  • Micronutrients flagged overdue: B12, ferritin, iron, Ca, PTH

All functions are synchronous and use stdlib only.
Storage:
  ~/.jarvis/health/nutrition_log.jsonl  — daily meal logs (one JSON object per line)
  ~/.jarvis/health/nutrition_summary.json — cached 7-day summary
"""
from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_HEALTH_DIR = Path.home() / ".jarvis" / "health"
_LOG_PATH = _HEALTH_DIR / "nutrition_log.jsonl"
_SUMMARY_PATH = _HEALTH_DIR / "nutrition_summary.json"
_HEALTH_STATE_CANDIDATES = [
    Path.home() / ".jarvis" / "health" / "health_state.json",
    Path.home() / ".jarvis" / "health_state.json",
    Path.home() / ".jarvis" / "health" / "state.json",
]

# Patient constants
_HEIGHT_IN = 70.5          # 5'10.5"
_WEIGHT_LBS = 252.0
_SURGERY_TYPE = "sleeve"
_PROTEIN_MIN_G = 90.0
_PROTEIN_OPTIMAL_G = 110.0  # midpoint of 90-120 range
_PROTEIN_TARGET_G = 120.0   # upper optimal

_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class NutritionLog:
    """Daily nutrition summary for one calendar date."""
    date: str
    meals: list[dict]           # [{name, protein_g, carb_g, fat_g, calories, time}]
    total_protein_g: float
    total_carbs_g: float
    total_fat_g: float
    total_calories: float
    protein_target_met: bool
    notes: str = ""


@dataclass
class BariatricNutritionStatus:
    """Comprehensive micronutrient and macro status for post-bariatric patient."""
    date: str
    protein_7day_avg_g: float
    protein_target_g: float
    protein_adequacy_pct: float
    vitamin_d_status: str       # "replete" | "insufficient" | "deficient" | "unknown"
    b12_status: str
    iron_status: str
    calcium_status: str
    ferritin_status: str
    overdue_labs: list[str]
    recommendations: list[str]
    supplement_gaps: list[str]


@dataclass
class GLP1MealTiming:
    """Optimized meal timing scaffold around weekly semaglutide injection."""
    injection_day: str          # e.g. "monday"
    injection_time: str         # e.g. "08:00"
    optimal_meal_windows: list[dict]    # [{meal, window, rationale}]
    foods_to_limit: list[str]   # GI side effects
    foods_to_prioritize: list[str]
    post_meal_walk_target_min: int
    notes: list[str]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _today_str() -> str:
    return date.today().isoformat()


def _ensure_dirs() -> None:
    _HEALTH_DIR.mkdir(parents=True, exist_ok=True)


def _load_health_state() -> dict:
    """
    Attempt to load health_state.json from known candidate paths.
    Returns empty dict if not found or unreadable.
    """
    for path in _HEALTH_STATE_CANDIDATES:
        try:
            if path.exists():
                return json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            log.warning("Could not read health state at %s: %s", path, exc)
    return {}


def _read_log_for_date(target_date: str) -> dict | None:
    """
    Scan the JSONL nutrition log and return the entry for target_date.
    Returns None if no entry found.
    """
    if not _LOG_PATH.exists():
        return None
    try:
        with _lock:
            with open(_LOG_PATH, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        if entry.get("date") == target_date:
                            return entry
                    except json.JSONDecodeError:
                        continue
    except Exception as exc:
        log.error("Error reading nutrition log: %s", exc)
    return None


def _write_log_entry(entry: dict) -> None:
    """
    Upsert a daily log entry in the JSONL file.
    Replaces the existing line for that date if present; otherwise appends.
    """
    _ensure_dirs()
    target_date = entry["date"]
    lines: list[str] = []
    replaced = False

    try:
        with _lock:
            if _LOG_PATH.exists():
                with open(_LOG_PATH, encoding="utf-8") as fh:
                    for line in fh:
                        stripped = line.strip()
                        if not stripped:
                            continue
                        try:
                            existing = json.loads(stripped)
                            if existing.get("date") == target_date:
                                lines.append(json.dumps(entry))
                                replaced = True
                            else:
                                lines.append(stripped)
                        except json.JSONDecodeError:
                            lines.append(stripped)

            if not replaced:
                lines.append(json.dumps(entry))

            _LOG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except Exception as exc:
        log.error("Error writing nutrition log: %s", exc)
        raise


def _sum_meals(meals: list[dict]) -> tuple[float, float, float, float]:
    """Return (protein_g, carb_g, fat_g, calories) totals from a meal list."""
    protein = sum(float(m.get("protein_g", 0)) for m in meals)
    carbs = sum(float(m.get("carb_g", 0)) for m in meals)
    fat = sum(float(m.get("fat_g", 0)) for m in meals)
    calories = sum(float(m.get("calories", 0)) for m in meals)
    return protein, carbs, fat, calories


def _entry_to_log(entry: dict) -> NutritionLog:
    """Convert a raw JSONL dict to a NutritionLog dataclass."""
    meals = entry.get("meals", [])
    protein, carbs, fat, cals = _sum_meals(meals)
    return NutritionLog(
        date=entry["date"],
        meals=meals,
        total_protein_g=round(protein, 1),
        total_carbs_g=round(carbs, 1),
        total_fat_g=round(fat, 1),
        total_calories=round(cals, 1),
        protein_target_met=protein >= _PROTEIN_MIN_G,
        notes=entry.get("notes", ""),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_protein_target(weight_lbs: float = _WEIGHT_LBS,
                       surgery_type: str = "sleeve") -> dict:
    """
    Calculate post-bariatric protein targets for a sleeve gastrectomy patient.

    Uses two methodologies:
      1. Absolute daily target based on surgery type (60-80g min; 90-120g optimal)
      2. Per-kg ideal body weight (IBW) calculation: 1.2-1.5g/kg IBW

    IBW for 5'10.5" male (Devine formula): 50 + 2.3 × (inches over 60)
        = 50 + 2.3 × 10.5 ≈ 74.2 kg ≈ 163.5 lbs
    (Rounded conservatively to 172 lbs per clinical guidance for this patient.)

    Args:
        weight_lbs: Current weight in pounds (default 252 lbs).
        surgery_type: "sleeve" | "rygb" | "band"

    Returns:
        dict with keys:
            min_g           — minimum daily protein (g)
            optimal_g       — optimal daily protein midpoint (g)
            target_g        — upper optimal target (g)
            per_kg_ibw_low  — low end per-kg-IBW recommendation (g/kg)
            per_kg_ibw_high — high end per-kg-IBW recommendation (g/kg)
            ibw_lbs         — estimated ideal body weight (lbs)
            ibw_kg          — estimated ideal body weight (kg)
            rationale       — plain-English explanation
    """
    # Devine IBW for 5'10.5" male
    ibw_lbs = 172.0
    ibw_kg = round(ibw_lbs * 0.453592, 1)  # ≈ 78.0 kg

    if surgery_type == "sleeve":
        min_g = 60.0
        optimal_g = 105.0       # midpoint 90-120
        target_g = 120.0
        surgery_note = (
            "Sleeve gastrectomy reduces gastric volume but preserves pylorus; "
            "protein absorption is relatively intact vs. RYGB. "
            "Minimum 60-80g/day for weight maintenance; 90-120g/day for "
            "optimal muscle preservation, especially with semaglutide-driven "
            "appetite suppression and T2DM."
        )
    elif surgery_type == "rygb":
        min_g = 60.0
        optimal_g = 90.0
        target_g = 120.0
        surgery_note = (
            "RYGB bypasses duodenum and proximal jejunum; protein malabsorption "
            "risk is higher. Minimum 60g/day; target 90-120g/day."
        )
    else:  # band or unknown
        min_g = 60.0
        optimal_g = 80.0
        target_g = 100.0
        surgery_note = "Standard post-bariatric protein guidance."

    per_kg_low = round(min_g / ibw_kg, 2)
    per_kg_high = round(target_g / ibw_kg, 2)

    rationale = (
        f"{surgery_note} "
        f"At IBW {ibw_lbs} lbs ({ibw_kg} kg), the per-kg range is "
        f"{per_kg_low}-{per_kg_high}g/kg IBW (guideline: 1.2-1.5g/kg). "
        f"With semaglutide reducing appetite, prioritize protein at every meal "
        f"and use protein shakes to close gaps. "
        f"Daily target: {int(target_g)}g."
    )

    return {
        "min_g": min_g,
        "optimal_g": optimal_g,
        "target_g": target_g,
        "per_kg_ibw_low": per_kg_low,
        "per_kg_ibw_high": per_kg_high,
        "ibw_lbs": ibw_lbs,
        "ibw_kg": ibw_kg,
        "rationale": rationale,
    }


def log_meal(date_str: str, meal: dict) -> dict:
    """
    Append a meal to today's nutrition log and return the updated daily summary.

    The JSONL file stores one JSON object per line, keyed by date. If an entry
    for `date_str` already exists it is updated in-place; otherwise a new entry
    is created.

    Args:
        date_str: ISO date string, e.g. "2026-05-22".
        meal: dict with keys:
                name       (str)   — meal name / description
                protein_g  (float) — protein in grams
                carb_g     (float) — carbohydrates in grams
                fat_g      (float) — fat in grams
                calories   (float) — total calories
                time       (str)   — time string, e.g. "12:30"

    Returns:
        dict — updated daily summary with keys:
            date, meal_count, total_protein_g, total_carbs_g, total_fat_g,
            total_calories, protein_target_met, protein_gap_g, meals
    """
    required = {"name", "protein_g", "carb_g", "fat_g", "calories", "time"}
    missing = required - set(meal.keys())
    if missing:
        raise ValueError(f"Meal dict missing required keys: {missing}")

    # Normalize numeric fields
    meal_clean = {
        "name": str(meal["name"]),
        "protein_g": float(meal["protein_g"]),
        "carb_g": float(meal["carb_g"]),
        "fat_g": float(meal["fat_g"]),
        "calories": float(meal["calories"]),
        "time": str(meal["time"]),
    }

    existing = _read_log_for_date(date_str)
    if existing:
        entry = existing
        entry["meals"].append(meal_clean)
    else:
        entry = {
            "date": date_str,
            "meals": [meal_clean],
            "notes": "",
        }

    _write_log_entry(entry)

    protein, carbs, fat, cals = _sum_meals(entry["meals"])
    gap = max(0.0, _PROTEIN_TARGET_G - protein)

    log.info(
        "Logged meal '%s' for %s — daily protein now %.1fg (target %.0fg, gap %.1fg)",
        meal_clean["name"], date_str, protein, _PROTEIN_TARGET_G, gap,
    )

    return {
        "date": date_str,
        "meal_count": len(entry["meals"]),
        "total_protein_g": round(protein, 1),
        "total_carbs_g": round(carbs, 1),
        "total_fat_g": round(fat, 1),
        "total_calories": round(cals, 1),
        "protein_target_met": protein >= _PROTEIN_MIN_G,
        "protein_gap_g": round(gap, 1),
        "meals": entry["meals"],
    }


def get_daily_nutrition(date_str: str | None = None) -> NutritionLog:
    """
    Return a NutritionLog for the given date (defaults to today).

    Reads from ~/.jarvis/health/nutrition_log.jsonl. If no entry exists for
    the requested date, returns an empty NutritionLog with zero totals.

    Args:
        date_str: ISO date string (e.g. "2026-05-22"). Defaults to today.

    Returns:
        NutritionLog dataclass instance.
    """
    target = date_str or _today_str()
    entry = _read_log_for_date(target)

    if entry:
        return _entry_to_log(entry)

    return NutritionLog(
        date=target,
        meals=[],
        total_protein_g=0.0,
        total_carbs_g=0.0,
        total_fat_g=0.0,
        total_calories=0.0,
        protein_target_met=False,
        notes="No meals logged for this date.",
    )


def get_nutrition_7day_summary() -> dict:
    """
    Return 7-day rolling averages for protein, carbs, fat, and calories.

    Reads the last 7 calendar days from the nutrition JSONL log, computes
    daily averages, compares to targets, and returns a trend assessment.

    Returns:
        dict with keys:
            period_start, period_end,
            days_logged,
            avg_protein_g, avg_carbs_g, avg_fat_g, avg_calories,
            protein_target_g, protein_adequacy_pct,
            protein_trend    — "improving" | "declining" | "stable" | "insufficient_data"
            calories_trend   — same
            days_below_protein_target,
            summary          — plain-English one-liner
    """
    today = date.today()
    days: list[NutritionLog] = []

    for i in range(6, -1, -1):
        d = (today - timedelta(days=i)).isoformat()
        log_entry = get_daily_nutrition(d)
        if log_entry.meals:  # only count days with actual data
            days.append(log_entry)

    period_start = (today - timedelta(days=6)).isoformat()
    period_end = today.isoformat()

    if not days:
        return {
            "period_start": period_start,
            "period_end": period_end,
            "days_logged": 0,
            "avg_protein_g": 0.0,
            "avg_carbs_g": 0.0,
            "avg_fat_g": 0.0,
            "avg_calories": 0.0,
            "protein_target_g": _PROTEIN_TARGET_G,
            "protein_adequacy_pct": 0.0,
            "protein_trend": "insufficient_data",
            "calories_trend": "insufficient_data",
            "days_below_protein_target": 0,
            "summary": "No nutrition data logged in the past 7 days.",
        }

    n = len(days)
    avg_protein = round(sum(d.total_protein_g for d in days) / n, 1)
    avg_carbs = round(sum(d.total_carbs_g for d in days) / n, 1)
    avg_fat = round(sum(d.total_fat_g for d in days) / n, 1)
    avg_cal = round(sum(d.total_calories for d in days) / n, 1)
    days_below = sum(1 for d in days if not d.protein_target_met)
    adequacy_pct = round(avg_protein / _PROTEIN_TARGET_G * 100, 1)

    # Trend: compare first half vs second half of logged days
    def _trend(values: list[float]) -> str:
        if len(values) < 4:
            return "insufficient_data"
        mid = len(values) // 2
        first_half = sum(values[:mid]) / mid
        second_half = sum(values[mid:]) / (len(values) - mid)
        delta_pct = (second_half - first_half) / max(first_half, 1) * 100
        if delta_pct >= 5:
            return "improving"
        if delta_pct <= -5:
            return "declining"
        return "stable"

    protein_trend = _trend([d.total_protein_g for d in days])
    cal_trend = _trend([d.total_calories for d in days])

    if adequacy_pct >= 90:
        summary_txt = (
            f"Protein averaging {avg_protein}g/day — on target "
            f"({adequacy_pct}% of {int(_PROTEIN_TARGET_G)}g goal)."
        )
    else:
        gap = round(_PROTEIN_TARGET_G - avg_protein, 1)
        summary_txt = (
            f"Protein averaging {avg_protein}g/day — {gap}g below target "
            f"({adequacy_pct}% of {int(_PROTEIN_TARGET_G)}g goal). "
            f"{days_below}/{n} days below minimum."
        )

    result = {
        "period_start": period_start,
        "period_end": period_end,
        "days_logged": n,
        "avg_protein_g": avg_protein,
        "avg_carbs_g": avg_carbs,
        "avg_fat_g": avg_fat,
        "avg_calories": avg_cal,
        "protein_target_g": _PROTEIN_TARGET_G,
        "protein_adequacy_pct": adequacy_pct,
        "protein_trend": protein_trend,
        "calories_trend": cal_trend,
        "days_below_protein_target": days_below,
        "summary": summary_txt,
    }

    # Cache to disk
    try:
        _ensure_dirs()
        _SUMMARY_PATH.write_text(
            json.dumps({**result, "cached_at": datetime.now(timezone.utc).isoformat()},
                       indent=2),
            encoding="utf-8",
        )
    except Exception as exc:
        log.warning("Could not cache nutrition summary: %s", exc)

    return result


def assess_bariatric_micronutrients() -> BariatricNutritionStatus:
    """
    Assess post-bariatric micronutrient status using available lab data.

    Reads health_state.json for any stored lab values, then applies
    post-bariatric clinical thresholds. Falls back to known documented
    values for this patient when health_state.json is unavailable.

    Clinical reference values (post-bariatric, ASMBS guidelines):
      Vitamin D:  >30 ng/mL adequate; >40 ng/mL preferred; >50 optimal
      B12:        >400 pg/mL preferred post-bariatric (functional cutoff
                  higher than population normal of 200-300)
      Ferritin:   >50 ng/mL post-bariatric (>12 ng/mL population normal)
      Calcium:    8.5-10.2 mg/dL serum; ionized preferred
      PTH:        10-65 pg/mL; elevated signals Ca malabsorption

    Returns:
        BariatricNutritionStatus dataclass with full assessment.
    """
    today = _today_str()
    health_state = _load_health_state()

    # ------------------------------------------------------------------
    # 7-day protein average
    # ------------------------------------------------------------------
    summary = get_nutrition_7day_summary()
    protein_avg = summary.get("avg_protein_g", 0.0)
    adequacy_pct = summary.get("protein_adequacy_pct", 0.0)

    # ------------------------------------------------------------------
    # Vitamin D
    # Patient: 55.4 ng/mL (May 2026) — replete. Maintenance 2000 IU/day.
    # ------------------------------------------------------------------
    vit_d_val = (
        health_state.get("labs", {}).get("vitamin_d", None)
        or health_state.get("vitamin_d_ngml", None)
    )
    if vit_d_val is None:
        # Use known documented value for this patient
        vit_d_val = 55.4
    vit_d_val = float(vit_d_val)
    if vit_d_val >= 50:
        vit_d_status = "replete"
    elif vit_d_val >= 30:
        vit_d_status = "insufficient"
    elif vit_d_val >= 20:
        vit_d_status = "deficient"
    else:
        vit_d_status = "severely_deficient"

    # ------------------------------------------------------------------
    # B12
    # Patient: 363 pg/mL (date unknown). Post-bariatric threshold >400.
    # Borderline — MMA level needed to confirm functional status.
    # ------------------------------------------------------------------
    b12_val = (
        health_state.get("labs", {}).get("b12", None)
        or health_state.get("b12_pgml", None)
    )
    if b12_val is None:
        b12_val = 363.0
    b12_val = float(b12_val)
    if b12_val >= 400:
        b12_status = "adequate"
    elif b12_val >= 200:
        b12_status = "borderline — MMA level needed"
    else:
        b12_status = "deficient"

    # ------------------------------------------------------------------
    # Iron / Ferritin
    # Patient: transferrin sat 19% (Nov 2019 — 7 years old, outdated).
    # No recent ferritin on record.
    # ------------------------------------------------------------------
    ferritin_val = (
        health_state.get("labs", {}).get("ferritin", None)
        or health_state.get("ferritin_ngml", None)
    )
    iron_sat = (
        health_state.get("labs", {}).get("transferrin_sat_pct", None)
        or health_state.get("iron_sat_pct", None)
    )

    if ferritin_val is None:
        ferritin_status = "unknown — overdue"
    else:
        ferritin_val = float(ferritin_val)
        if ferritin_val >= 50:
            ferritin_status = "adequate"
        elif ferritin_val >= 20:
            ferritin_status = "low-normal — monitor"
        else:
            ferritin_status = "deficient"

    if iron_sat is None or float(iron_sat) < 15:
        # 19% from 2019 is stale and borderline low (normal 20-50%)
        iron_status = "unknown — labs >6yr old, recheck needed"
    else:
        iron_status = "borderline" if float(iron_sat) < 20 else "adequate"

    # ------------------------------------------------------------------
    # Calcium / PTH
    # Patient: no recent Ca or PTH documented. Post-sleeve Ca malabsorption
    # risk is moderate (better than RYGB but present).
    # ------------------------------------------------------------------
    calcium_val = (
        health_state.get("labs", {}).get("calcium", None)
        or health_state.get("calcium_mgdl", None)
    )
    if calcium_val is None:
        calcium_status = "unknown — overdue"
    else:
        calcium_val = float(calcium_val)
        if 8.5 <= calcium_val <= 10.2:
            calcium_status = "normal"
        elif calcium_val < 8.5:
            calcium_status = "low"
        else:
            calcium_status = "elevated"

    # ------------------------------------------------------------------
    # Overdue labs list
    # ------------------------------------------------------------------
    overdue_labs: list[str] = []

    # B12 + MMA — documented but old and borderline
    overdue_labs.append(
        "Serum B12 with methylmalonic acid (MMA) — last B12 363 pg/mL "
        "(borderline post-bariatric), MMA never documented"
    )
    # Iron panel — 2019 data
    overdue_labs.append(
        "Iron panel: ferritin, serum iron, TIBC, transferrin saturation "
        "— last labs Nov 2019 (7 years overdue)"
    )
    # Calcium / PTH
    overdue_labs.append(
        "Calcium panel: total calcium, ionized calcium, PTH, 24h urine calcium "
        "— no recent values documented"
    )
    # Thiamine
    overdue_labs.append(
        "Thiamine (B1) level — not previously documented; "
        "sleeve gastrectomy risk lower than RYGB but relevant with vomiting/poor intake"
    )
    # Zinc & copper (ASMBS standard post-bariatric panel)
    overdue_labs.append(
        "Zinc and copper levels — part of standard annual post-bariatric panel; "
        "not recently documented"
    )

    # ------------------------------------------------------------------
    # Supplement gaps
    # ------------------------------------------------------------------
    supplement_gaps: list[str] = []

    if b12_status != "adequate":
        supplement_gaps.append(
            "Methylcobalamin 1000mcg/day oral (or monthly 1000mcg IM if MMA elevated "
            "or oral absorption concerns post-sleeve)"
        )
    if calcium_status in ("unknown — overdue", "low"):
        supplement_gaps.append(
            "Calcium citrate 1200-1500mg/day in 2-3 divided doses "
            "(citrate form — better absorbed than carbonate post-bariatric; "
            "take separately from iron supplements)"
        )
    if vit_d_status == "replete":
        supplement_gaps.append(
            "Vitamin D3 2000 IU/day maintenance (currently replete at 55.4 ng/mL — "
            "continue current dose)"
        )
    if ferritin_status == "unknown — overdue":
        supplement_gaps.append(
            "Ferrous sulfate or ferrous gluconate if ferritin <50 ng/mL on recheck "
            "(take with vitamin C, separate from calcium by 2h)"
        )

    # ------------------------------------------------------------------
    # Recommendations
    # ------------------------------------------------------------------
    recommendations: list[str] = []

    recommendations.append(
        "PRIORITY: Schedule post-bariatric labs — B12+MMA, iron panel (ferritin, "
        "iron, TIBC, transferrin sat), calcium, PTH, 25-OH vitamin D (confirm), "
        "thiamine, zinc, copper. These are 6+ year overdue at sleeve surgery annual cadence."
    )
    recommendations.append(
        "B12: Current level 363 pg/mL is borderline by post-bariatric standards (>400 preferred). "
        "Order methylmalonic acid (MMA) — elevated MMA confirms functional B12 deficiency "
        "even with serum B12 in 'normal' range. Consider starting methylcobalamin 1000mcg/day "
        "prophylactically pending results."
    )
    recommendations.append(
        "Iron: 2019 transferrin saturation (19%) is borderline and 7 years old. "
        "Sleeve gastrectomy reduces gastric acid, impairing non-heme iron conversion. "
        "Target ferritin >50 ng/mL post-bariatric. Recheck full iron panel urgently."
    )
    recommendations.append(
        "Calcium: Switch to calcium citrate (1200-1500mg/day divided) if not already — "
        "carbonate requires gastric acid for absorption, which is reduced post-sleeve. "
        "PTH should be checked to detect secondary hyperparathyroidism from Ca malabsorption."
    )
    recommendations.append(
        "Protein: Target 90-120g/day. With semaglutide reducing appetite, front-load protein "
        "at each meal before carbs/fat. Use Greek yogurt, cottage cheese, eggs, chicken, fish. "
        "Consider a protein shake (25-30g) on days appetite is suppressed (injection days)."
    )
    recommendations.append(
        "Vitamin D: Currently replete at 55.4 ng/mL (May 2026) — excellent. "
        "Continue maintenance dose 2000 IU/day. Recheck annually."
    )

    return BariatricNutritionStatus(
        date=today,
        protein_7day_avg_g=protein_avg,
        protein_target_g=_PROTEIN_TARGET_G,
        protein_adequacy_pct=adequacy_pct,
        vitamin_d_status=vit_d_status,
        b12_status=b12_status,
        iron_status=iron_status,
        calcium_status=calcium_status,
        ferritin_status=ferritin_status,
        overdue_labs=overdue_labs,
        recommendations=recommendations,
        supplement_gaps=supplement_gaps,
    )


def get_glp1_meal_timing(injection_day: str = "monday",
                         injection_time: str = "08:00") -> GLP1MealTiming:
    """
    Generate optimized meal timing windows around weekly semaglutide 2mg injection.

    Semaglutide pharmacokinetics (Ozempic weekly SC):
      - Tmax: ~24-72h post-injection (GI side effects peak earlier, 6-12h)
      - Half-life: ~1 week; concentrations accumulate over first 4-5 weeks
      - Nausea/vomiting peak: 6-12h post-injection for most patients
      - Gastric emptying slowed throughout week; most pronounced days 1-2

    Strategy:
      - Injection morning: light, protein-dominant breakfast BEFORE injection
        (or 1-2h after if patient tolerates)
      - Hours 6-12 post-injection (nausea window): keep meals very small,
        protein-first, avoid high-fat and high-sugar
      - Days 2-7: normal meal schedule with protein-first discipline
      - Post-meal walk: 10-min walk after 2 largest meals reduces postprandial
        glucose by 20-30% (validated in T2DM CGM studies)

    Args:
        injection_day: Day of week for weekly injection (default "monday").
        injection_time: 24h time string for injection (default "08:00").

    Returns:
        GLP1MealTiming dataclass.
    """
    inj_day = injection_day.lower().strip()

    # Parse injection hour for window calculations
    try:
        inj_hour = int(injection_time.split(":")[0])
    except (ValueError, IndexError):
        inj_hour = 8

    def _fmt_window(h_start: int, h_end: int) -> str:
        """Format hour offset as clock time string (24h)."""
        def _h(h: int) -> str:
            h = h % 24
            return f"{h:02d}:00"
        return f"{_h(inj_hour + h_start)}–{_h(inj_hour + h_end)}"

    optimal_meal_windows = [
        {
            "meal": "Breakfast (injection day)",
            "window": _fmt_window(-1, 0) + " (before injection) or " + _fmt_window(2, 3),
            "rationale": (
                "Eat a protein-forward breakfast 1h before injection, or wait 2-3h "
                "post-injection once GI effects are minimal. Avoid large meals within "
                "1h post-injection to reduce nausea risk."
            ),
        },
        {
            "meal": "Lunch (injection day — nausea window)",
            "window": _fmt_window(4, 6),
            "rationale": (
                "Nausea peaks 6-12h post-injection. Aim to eat lunch before this "
                "window (4-6h post). Keep it small: 3-4oz protein, non-starchy veg. "
                "Skip high-fat sauces and heavy carbs entirely today."
            ),
        },
        {
            "meal": "Dinner (injection day — during nausea window)",
            "window": _fmt_window(11, 13),
            "rationale": (
                "Many patients feel best eating dinner later on injection day, past the "
                "6-12h nausea peak. Keep dinner very small if nausea present — a protein "
                "shake or Greek yogurt is acceptable. Do not force a full meal."
            ),
        },
        {
            "meal": "Days 2-7 (non-injection days)",
            "window": "07:00–08:00 breakfast, 12:00–13:00 lunch, 18:00–19:00 dinner",
            "rationale": (
                "Standard 3-meal schedule. Protein-first at every meal. "
                "1-2 protein snacks if daily protein target not met by dinner. "
                "No drinking 30 min before or after meals (sleeve restriction). "
                "10-min post-meal walk after lunch and dinner."
            ),
        },
        {
            "meal": "Protein snack (any day)",
            "window": "15:00–16:00 and/or 20:00–21:00 if needed",
            "rationale": (
                "Use snacks strategically to close protein gap. Greek yogurt (15-17g), "
                "cottage cheese (14g/½ cup), string cheese + deli turkey, or protein "
                "shake (25-30g). Avoid grazing — 4-5 structured eating occasions/day max."
            ),
        },
    ]

    foods_to_limit = [
        "High-fat foods on injection day (pizza, fried foods, fatty meats) — slow gastric "
        "emptying + semaglutide = nausea amplified",
        "Carbonated beverages — sleeve discomfort, bloating, and reduced gastric capacity",
        "Simple/refined carbohydrates (white bread, juice, candy, sweetened drinks) — "
        "postprandial glucose spikes visible on CGM; semaglutide cannot fully compensate",
        "Large meal volumes (>6-8oz at once) — sleeve capacity; risk of dumping/vomiting",
        "High-sugar foods >15g sugar per serving — dumping syndrome risk post-sleeve",
        "Drinking with or immediately after meals — dilutes digestive enzymes, promotes "
        "early satiety signal loss and poor protein absorption",
        "Alcohol — hypoglycemia risk with semaglutide + metformin; empty calories; "
        "increased GERD post-sleeve",
    ]

    foods_to_prioritize = [
        "Lean protein first: chicken breast, ground turkey, tuna, salmon, shrimp, eggs, "
        "egg whites (25-30g protein per meal)",
        "Greek yogurt (plain, 2% or whole) — 15-17g protein per 6oz; also provides Ca",
        "Cottage cheese (low-fat) — 14g protein per ½ cup; soft texture post-sleeve",
        "Legumes: lentils, chickpeas, edamame — protein + fiber + slow-release carbs",
        "Non-starchy vegetables: broccoli, spinach, zucchini, cauliflower, bell peppers — "
        "volume without glucose impact",
        "Eggs and egg-based dishes — versatile, complete protein, micronutrient dense",
        "Protein shakes on high-nausea days (injection day) — whey or collagen isolate, "
        "25-30g protein, low sugar (<5g)",
        "Fatty fish 2-3x/week: salmon, mackerel, sardines — omega-3s support insulin "
        "sensitivity and reduce inflammation",
        "Soft textures: ground meats, fish, soft-cooked eggs, yogurt, cottage cheese — "
        "easier on sleeve 6yr post-op",
    ]

    notes = [
        f"Injection day: {inj_day.capitalize()} at {injection_time}. "
        "Plan lighter eating on injection day — especially avoid large high-fat meals "
        f"between {_fmt_window(6, 12)} (peak nausea window).",
        "Protein-first rule: eat protein before carbs or fat at every meal. "
        "This maximizes protein absorption in the small gastric pouch before satiety signals fire.",
        "Post-meal walking: 10 minutes of brisk walking after lunch and dinner "
        "reduces postprandial glucose ~20-30% (CGM-validated in T2DM). "
        "Prioritize the post-dinner walk especially.",
        "Hydration: 64+ oz water/day, but NEVER with meals. "
        "Stop drinking 30 min before meals; resume 30 min after. "
        "Dehydration worsens semaglutide GI side effects.",
        "Meal size: Target 4-6oz (½ to ¾ cup) per meal. At 6.5yr post-op, "
        "sleeve has relaxed somewhat — 6-8oz is likely your current capacity. "
        "Stop at first satiety signal; overeating causes pain and vomiting.",
        "Semaglutide + metformin combination: metformin ER reduces GI burden vs. "
        "IR formulation. Take metformin with largest meal of the day (dinner or lunch).",
    ]

    return GLP1MealTiming(
        injection_day=inj_day,
        injection_time=injection_time,
        optimal_meal_windows=optimal_meal_windows,
        foods_to_limit=foods_to_limit,
        foods_to_prioritize=foods_to_prioritize,
        post_meal_walk_target_min=10,
        notes=notes,
    )


def get_post_bariatric_meal_plan(days: int = 7) -> list[dict]:
    """
    Generate a 7-day post-sleeve + GLP-1 + T2DM meal plan framework.

    This is a framework with meal category suggestions, not full recipes.
    Each day follows the protein-first, small-portion, T2DM-friendly structure
    appropriate for a 6.5yr post-sleeve patient on semaglutide.

    Guiding principles:
      - Protein first at every meal (25-35g per meal)
      - Portions: 4-6oz per sitting (3 meals + 1-2 protein snacks)
      - No drinking 30 min before or after meals
      - Avoid: high-sugar foods, carbonated drinks, tough fibrous textures,
        high-fat meals (especially on injection day)
      - Macros: 90-120g protein, <150g carbs (T2DM target), moderate fat
      - Injection day (Monday): lighter, blander eating

    Args:
        days: Number of days to generate (default 7).

    Returns:
        list of dicts, one per day, each with:
            day, day_name, is_injection_day,
            meals (breakfast, lunch, dinner, snacks),
            macros_target, notes
    """
    days = max(1, min(days, 14))

    # Day templates indexed 0 = Monday
    _DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday",
                  "Friday", "Saturday", "Sunday"]

    today_weekday = date.today().weekday()  # 0 = Monday

    # Injection day template (lighter, anti-nausea focus)
    _INJECTION_DAY_MEALS = {
        "breakfast": {
            "suggestion": "2 scrambled eggs + 1 slice turkey or 6oz plain Greek yogurt with ½ tsp cinnamon",
            "protein_g": 20,
            "notes": "Eat 1h before injection OR 2-3h after. Small portion."
        },
        "lunch": {
            "suggestion": "3oz canned tuna or chicken salad (light mayo) in lettuce cups + ½ cup cucumber slices",
            "protein_g": 22,
            "notes": "Eat before 14:00 if possible — ahead of nausea window."
        },
        "dinner": {
            "suggestion": "Protein shake (whey isolate 25-30g) or 3oz soft white fish (tilapia, cod) "
                          "+ steamed zucchini if tolerated",
            "protein_g": 27,
            "notes": "Keep dinner very small if nausea present. Shake is acceptable."
        },
        "snacks": [
            {"suggestion": "String cheese (7g protein)", "protein_g": 7},
            {"suggestion": "½ cup cottage cheese if tolerating solids", "protein_g": 14},
        ],
    }

    # Standard day template — varied by rotation
    _STANDARD_MEALS = [
        {
            "breakfast": {
                "suggestion": "3-egg veggie omelet (spinach, bell pepper) + 2oz turkey sausage",
                "protein_g": 32, "notes": "High-protein start. Cook eggs soft."
            },
            "lunch": {
                "suggestion": "4oz grilled chicken breast + ½ cup roasted broccoli + 2 Tbsp hummus",
                "protein_g": 30, "notes": "Chew thoroughly. No drinking until 30min after."
            },
            "dinner": {
                "suggestion": "4oz baked salmon + ½ cup sautéed zucchini + 2 Tbsp avocado",
                "protein_g": 28, "notes": "Omega-3 rich. 10-min walk after dinner."
            },
            "snacks": [
                {"suggestion": "6oz plain Greek yogurt (Fage 2%)", "protein_g": 17},
                {"suggestion": "1oz almonds + 1 mozzarella string cheese", "protein_g": 11},
            ],
        },
        {
            "breakfast": {
                "suggestion": "Protein smoothie: 1 scoop whey isolate + ½ cup frozen berries "
                              "+ 1 cup unsweetened almond milk + 1 Tbsp PB2",
                "protein_g": 30, "notes": "Sip slowly — counts as a 'meal.' No eating for 30min after."
            },
            "lunch": {
                "suggestion": "3oz ground turkey taco bowl: seasoned turkey + lettuce + salsa "
                              "+ 2 Tbsp plain Greek yogurt (sour cream sub)",
                "protein_g": 27, "notes": "Skip tortillas. Low carb."
            },
            "dinner": {
                "suggestion": "4oz baked cod or tilapia + ½ cup steamed green beans + ½ cup "
                              "cauliflower rice",
                "protein_g": 27, "notes": "Mild, soft texture. Walk after."
            },
            "snacks": [
                {"suggestion": "½ cup cottage cheese + ½ cup blueberries", "protein_g": 14},
                {"suggestion": "2 hard-boiled eggs", "protein_g": 12},
            ],
        },
        {
            "breakfast": {
                "suggestion": "2 eggs scrambled + 3oz smoked salmon + 1 Tbsp cream cheese on cucumber",
                "protein_g": 28, "notes": "High protein, low carb. Easy to prepare."
            },
            "lunch": {
                "suggestion": "4oz shrimp stir-fry with bok choy, snap peas, low-sodium soy sauce + "
                              "½ cup cauliflower rice",
                "protein_g": 26, "notes": "Shrimp is soft, high-protein. Low-carb swap for rice."
            },
            "dinner": {
                "suggestion": "4oz lean pork tenderloin + ½ cup roasted asparagus + "
                              "2 Tbsp tzatziki",
                "protein_g": 30, "notes": "Pork tenderloin is lean and soft when well-cooked."
            },
            "snacks": [
                {"suggestion": "1 scoop collagen peptides in warm broth or coffee", "protein_g": 18},
                {"suggestion": "6oz plain Greek yogurt", "protein_g": 17},
            ],
        },
        {
            "breakfast": {
                "suggestion": "Egg muffins: 3 mini egg muffins (eggs, spinach, turkey) — meal prep friendly",
                "protein_g": 25, "notes": "Make 12 ahead on Sunday. Reheat in 45 sec."
            },
            "lunch": {
                "suggestion": "4oz canned chicken salad (light mayo, celery, dill) in lettuce wraps + "
                              "½ cup cherry tomatoes",
                "protein_g": 28, "notes": "Canned chicken is sleeve-friendly — soft, easy."
            },
            "dinner": {
                "suggestion": "4oz 93% lean ground beef burger (no bun, lettuce wrap) + "
                              "½ cup roasted mushrooms",
                "protein_g": 30, "notes": "No bun — sleeve volume and T2DM carb goals."
            },
            "snacks": [
                {"suggestion": "Edamame ½ cup shelled", "protein_g": 9},
                {"suggestion": "2 Tbsp natural almond butter on celery sticks", "protein_g": 7},
            ],
        },
        {
            "breakfast": {
                "suggestion": "½ cup cottage cheese + ½ cup sliced peaches (fresh or canned in juice) "
                              "+ 1 Tbsp flaxseed",
                "protein_g": 16, "notes": "Lower protein breakfast — compensate at lunch."
            },
            "lunch": {
                "suggestion": "Lentil soup (½ cup) + 3oz rotisserie chicken (white meat, no skin)",
                "protein_g": 31, "notes": "Lentils: protein + fiber. Warming, easy to eat."
            },
            "dinner": {
                "suggestion": "4oz mahi-mahi or halibut, pan-seared + ½ cup sautéed spinach with garlic",
                "protein_g": 29, "notes": "Firm white fish — chew well. Walk after."
            },
            "snacks": [
                {"suggestion": "Protein bar: Quest or RXBar (≥20g protein, <5g sugar)", "protein_g": 20},
                {"suggestion": "1oz pumpkin seeds + string cheese", "protein_g": 11},
            ],
        },
        {
            "breakfast": {
                "suggestion": "Protein pancakes: 1 scoop protein powder + 1 egg + ½ mashed banana "
                              "(makes 2 small pancakes)",
                "protein_g": 28, "notes": "Weekend treat meal. Soft texture, sleeve-friendly."
            },
            "lunch": {
                "suggestion": "4oz grilled chicken Caesar salad (no croutons, light dressing) + "
                              "2 Tbsp parmesan",
                "protein_g": 35, "notes": "High protein. Skip croutons — carb/texture issue."
            },
            "dinner": {
                "suggestion": "4oz lamb chop (trimmed) or beef tenderloin + ½ cup roasted "
                              "Brussels sprouts",
                "protein_g": 30, "notes": "Saturday dinner indulgence — portion control is the key."
            },
            "snacks": [
                {"suggestion": "½ cup plain Greek yogurt + 1 Tbsp honey + walnuts", "protein_g": 15},
                {"suggestion": "Celery + 2 Tbsp peanut butter", "protein_g": 8},
            ],
        },
        {
            "breakfast": {
                "suggestion": "2-egg frittata (mushroom, spinach, feta) — make in small cast iron",
                "protein_g": 22, "notes": "Meal-prep the week's egg muffins while this cooks."
            },
            "lunch": {
                "suggestion": "Soup: 1 cup chicken and vegetable broth-based soup + 3oz chicken chunks",
                "protein_g": 30, "notes": "Warm, hydrating. Good for sleeve comfort."
            },
            "dinner": {
                "suggestion": "4oz baked chicken thigh (skin removed) + ½ cup roasted sweet potato "
                              "(¼ cup portion — T2DM) + green salad",
                "protein_g": 30, "notes": "Sweet potato: limit to ¼ cup for glycemic control."
            },
            "snacks": [
                {"suggestion": "Prep tomorrow's egg muffins while watching TV", "protein_g": 0},
                {"suggestion": "2 hard-boiled eggs or protein shake if protein gap remains", "protein_g": 25},
            ],
        },
    ]

    plan = []
    today_weekday = date.today().weekday()

    for i in range(days):
        current_date = date.today() + timedelta(days=i)
        weekday = current_date.weekday()
        day_name = _DAY_NAMES[weekday]
        is_injection = day_name.lower() == "monday"

        if is_injection:
            meals = _INJECTION_DAY_MEALS
            daily_protein_est = sum([
                meals["breakfast"]["protein_g"],
                meals["lunch"]["protein_g"],
                meals["dinner"]["protein_g"],
            ]) + sum(s["protein_g"] for s in meals["snacks"])
        else:
            template_idx = (weekday - 1) % len(_STANDARD_MEALS)
            meals = _STANDARD_MEALS[template_idx]
            daily_protein_est = sum([
                meals["breakfast"]["protein_g"],
                meals["lunch"]["protein_g"],
                meals["dinner"]["protein_g"],
            ]) + sum(s["protein_g"] for s in meals["snacks"])

        plan.append({
            "day": i + 1,
            "date": current_date.isoformat(),
            "day_name": day_name,
            "is_injection_day": is_injection,
            "meals": {
                "breakfast": meals["breakfast"],
                "lunch": meals["lunch"],
                "dinner": meals["dinner"],
                "snacks": meals["snacks"],
            },
            "macros_target": {
                "protein_g": "90-120",
                "carbs_g": "<150 (T2DM)",
                "fat_g": "40-60",
                "calories": "1400-1800",
            },
            "estimated_protein_g": daily_protein_est,
            "notes": (
                "Injection day — lighter eating, avoid high-fat, protein shakes OK for any meal."
                if is_injection else
                "Protein-first every meal. 10-min walk after lunch + dinner. "
                "No drinking 30 min before/after meals. Stop at first satiety signal."
            ),
        })

    return plan


def get_nutrition_recommendations() -> list[str]:
    """
    Return a prioritized list of nutrition recommendations based on current status.

    Combines protein adequacy from 7-day log, micronutrient assessment, GLP-1
    timing guidance, and T2DM management goals into a ranked action list.

    Higher-priority items appear first (lab safety > micronutrient gaps >
    protein > meal timing > general optimization).

    Returns:
        list[str] — ordered recommendations from most to least urgent.
    """
    recommendations: list[str] = []

    # ------------------------------------------------------------------
    # 1. URGENT: Overdue labs (patient safety)
    # ------------------------------------------------------------------
    recommendations.append(
        "[URGENT] Schedule post-bariatric lab panel — 6+ years overdue: "
        "B12 + methylmalonic acid (MMA), ferritin, serum iron, TIBC, transferrin saturation, "
        "total calcium, ionized calcium, PTH, 25-OH vitamin D (confirm), thiamine (B1), "
        "zinc, copper. These prevent irreversible neurological and bone complications."
    )

    # ------------------------------------------------------------------
    # 2. URGENT: B12 borderline status
    # ------------------------------------------------------------------
    recommendations.append(
        "[URGENT] B12 status borderline: last value 363 pg/mL (post-bariatric optimal >400). "
        "Order MMA level — elevated MMA = functional B12 deficiency even with 'normal' serum B12. "
        "Consider starting methylcobalamin 1000mcg/day orally now while awaiting labs. "
        "Sublingual or IM preferred if absorption concern (reduced intrinsic factor post-sleeve)."
    )

    # ------------------------------------------------------------------
    # 3. HIGH: Iron / ferritin unknown
    # ------------------------------------------------------------------
    recommendations.append(
        "[HIGH] Iron panel 7 years old — ferritin unknown. Post-sleeve reduces gastric acid "
        "→ impairs non-heme iron absorption → iron-deficiency anemia risk. "
        "Target ferritin >50 ng/mL. If deficient: ferrous sulfate 325mg with vitamin C, "
        "separate from calcium by 2h."
    )

    # ------------------------------------------------------------------
    # 4. HIGH: Calcium citrate & PTH
    # ------------------------------------------------------------------
    recommendations.append(
        "[HIGH] Calcium/PTH not recently checked. Post-sleeve: take calcium citrate "
        "(NOT carbonate — requires gastric acid), 1200-1500mg/day divided doses. "
        "Elevated PTH indicates secondary hyperparathyroidism from Ca malabsorption → bone loss. "
        "Recheck total Ca, ionized Ca, PTH."
    )

    # ------------------------------------------------------------------
    # 5. Protein adequacy check
    # ------------------------------------------------------------------
    try:
        summary = get_nutrition_7day_summary()
        avg_protein = summary.get("avg_protein_g", 0.0)
        adequacy_pct = summary.get("protein_adequacy_pct", 0.0)
        days_logged = summary.get("days_logged", 0)

        if days_logged == 0:
            recommendations.append(
                "[MEDIUM] Start logging meals in JARVIS — nutrition tracking enables protein "
                "gap identification. Target: 90-120g/day. With semaglutide suppressing appetite, "
                "undereating protein is a real risk."
            )
        elif adequacy_pct < 75:
            gap = round(_PROTEIN_TARGET_G - avg_protein, 1)
            recommendations.append(
                f"[HIGH] Protein averaging {avg_protein}g/day — {gap}g below target "
                f"({adequacy_pct}% of 120g goal). Add 1-2 protein shakes/day on low-appetite "
                f"days (especially semaglutide injection day). Protein-first at every meal."
            )
        elif adequacy_pct < 90:
            recommendations.append(
                f"[MEDIUM] Protein at {avg_protein}g/day ({adequacy_pct}% of goal). "
                "Small gap — add one Greek yogurt or string cheese snack to close it."
            )
        else:
            recommendations.append(
                f"[OK] Protein on target: {avg_protein}g/day ({adequacy_pct}% of 120g goal). "
                "Maintain current eating pattern."
            )
    except Exception as exc:
        log.warning("Could not retrieve 7-day summary for recommendations: %s", exc)
        recommendations.append(
            "[MEDIUM] Unable to retrieve protein tracking data. "
            "Ensure meals are being logged via JARVIS nutrition tracking."
        )

    # ------------------------------------------------------------------
    # 6. Injection day meal strategy
    # ------------------------------------------------------------------
    recommendations.append(
        "[MEDIUM] Semaglutide injection day (Monday 08:00): eat a protein breakfast "
        "1h before injection. Avoid large, high-fat meals between 14:00-20:00 "
        "(nausea peak window 6-12h post-injection). Use protein shakes for any meal "
        "where appetite is suppressed. Don't skip — protein catabolism worsens with GLP-1."
    )

    # ------------------------------------------------------------------
    # 7. Post-meal walking (CGM impact)
    # ------------------------------------------------------------------
    recommendations.append(
        "[MEDIUM] Post-meal walking: 10-min brisk walk after lunch and dinner reduces "
        "postprandial glucose 20-30% (validated in T2DM). This is additive to semaglutide "
        "and metformin. Build it as a non-negotiable habit — especially after highest-carb meal."
    )

    # ------------------------------------------------------------------
    # 8. Vitamin D — maintenance
    # ------------------------------------------------------------------
    recommendations.append(
        "[LOW/MAINTENANCE] Vitamin D replete at 55.4 ng/mL (May 2026). "
        "Continue vitamin D3 2000 IU/day maintenance. Recheck annually with next "
        "post-bariatric lab panel."
    )

    # ------------------------------------------------------------------
    # 9. Hydration + no drinking with meals
    # ------------------------------------------------------------------
    recommendations.append(
        "[ROUTINE] Hydration: 64+ oz water/day, but STOP drinking 30 min before meals "
        "and resume 30 min after. Drinking with meals dilutes enzymes and causes early "
        "fullness — displacing protein intake. Dehydration worsens semaglutide GI effects."
    )

    # ------------------------------------------------------------------
    # 10. Metformin timing optimization
    # ------------------------------------------------------------------
    recommendations.append(
        "[ROUTINE] Metformin ER 500mg: take with largest meal of the day (typically dinner) "
        "to minimize GI side effects. ER formulation already reduces GI burden vs. IR. "
        "If GI symptoms occur on injection day, consider taking metformin at lunch that day."
    )

    # ------------------------------------------------------------------
    # 11. T2DM carb targets
    # ------------------------------------------------------------------
    recommendations.append(
        "[ROUTINE] T2DM carb management: target <150g carbs/day, distributed across 3 meals "
        "(<50g per meal). Avoid simple carbs and sugary foods — post-sleeve dumping syndrome "
        "risk plus direct postprandial glucose spikes. Legumes (lentils, chickpeas) are "
        "preferred carb sources: high fiber, protein, slow glucose release."
    )

    # ------------------------------------------------------------------
    # 12. Annual bariatric care reminder
    # ------------------------------------------------------------------
    recommendations.append(
        "[REMINDER] Annual post-bariatric care: at 6.5 years post-sleeve, annual follow-up "
        "with bariatric program or PCP familiar with bariatric nutrition is standard of care. "
        "Ensure the following are on record: DEXA scan (bone density), full micronutrient "
        "panel, protein status, and psychological/behavioral check-in."
    )

    return recommendations


# ---------------------------------------------------------------------------
# Module self-test (python -m jarvis.nutrition_engine)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import pprint

    logging.basicConfig(level=logging.INFO)

    print("\n=== Protein Target ===")
    pprint.pprint(get_protein_target())

    print("\n=== Bariatric Micronutrient Assessment ===")
    status = assess_bariatric_micronutrients()
    pprint.pprint(asdict(status))

    print("\n=== GLP-1 Meal Timing (Monday 08:00) ===")
    timing = get_glp1_meal_timing()
    pprint.pprint(asdict(timing))

    print("\n=== 7-Day Summary ===")
    pprint.pprint(get_nutrition_7day_summary())

    print("\n=== Recommendations ===")
    for i, rec in enumerate(get_nutrition_recommendations(), 1):
        print(f"{i}. {rec}\n")

    print("\n=== 7-Day Meal Plan (Days 1-3) ===")
    plan = get_post_bariatric_meal_plan(days=3)
    pprint.pprint(plan)
