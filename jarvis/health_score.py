"""
health_score.py — Daily Health Score engine for JARVIS.

Computes a 0-100 daily health score for Chris across 8 domains:
  sleep, glycemic/nutrition, exercise, hydration, protein (CKD),
  mental health, protocol adherence, and biometric baseline.

Chris's medical context:
  - A1c 7.3% (T2DM, target <7.0)
  - LDL 156 mg/dL (target <100, no statins)
  - CKD Stage 2 — protein 60-90g/day, hydration critical
  - K+ 4.5 on olmesartan + spironolactone
  - BMI 35.7, weight loss goal
  - Sleep target 7.5h
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from .persistence import append_jsonl, atomic_write_jsonl

# ── Data paths ────────────────────────────────────────────────────────────────
JOURNAL_LOG   = Path("data/logs/sam_daily_journal.jsonl")
ADHERENCE_LOG = Path("data/logs/sam_adherence.jsonl")
ADHERENCE_STATE_LOG = ADHERENCE_LOG.with_name("sam_adherence_state_log.jsonl")
JOURNAL_STATE_LOG   = JOURNAL_LOG.with_name("sam_daily_journal_state_log.jsonl")
NUTRITION_LOG = Path.home() / ".jarvis/health/nutrition_log.jsonl"
NUTRITION_STATE_LOG = NUTRITION_LOG.with_name("nutrition_log_state_log.jsonl")
SLEEP_LOG     = Path.home() / ".jarvis/health/sleep_log.jsonl"
SLEEP_STATE_LOG = SLEEP_LOG.with_name("sleep_log_state_log.jsonl")
SCORE_LOG     = Path("data/logs/health_scores.jsonl")
SCORE_STATE_LOG = SCORE_LOG.with_name("health_scores_state_log.jsonl")

# High-glycemic food keywords
HIGH_GLYCEMIC = {"pizza", "cake", "candy", "ice cream", "donut", "chips", "soda", "fries"}

# ── Private helpers ────────────────────────────────────────────────────────────

def _read_jsonl_by_date(path: Path, date_str: str) -> dict:
    """Read a JSONL file and return the record matching date_str, or {}."""
    try:
        if not path.exists():
            return _read_state_log_by_date(path, date_str)
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if obj.get("date") == date_str:
                    return obj
            except Exception:
                continue
    except Exception:
        pass
    return _read_state_log_by_date(path, date_str)


def _read_state_log_by_date(path: Path, date_str: str) -> dict:
    if path == JOURNAL_LOG:
        log_path = JOURNAL_STATE_LOG
    elif path == ADHERENCE_LOG:
        log_path = ADHERENCE_STATE_LOG
    elif path == NUTRITION_LOG:
        log_path = NUTRITION_STATE_LOG
    elif path == SLEEP_LOG:
        log_path = SLEEP_STATE_LOG
    elif path == SCORE_LOG:
        log_path = SCORE_STATE_LOG
    else:
        return {}
    if not log_path.exists():
        return {}
    try:
        latest: list[dict] = []
        for line in log_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            records = payload.get("records")
            if isinstance(records, list):
                latest = [dict(item) for item in records if isinstance(item, dict)]
        for obj in latest:
            if obj.get("date") == date_str:
                return obj
    except Exception:
        return {}
    return {}


def _load_score_records() -> list[dict]:
    try:
        if SCORE_LOG.exists():
            records: list[dict] = []
            for line in SCORE_LOG.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if isinstance(obj, dict):
                    records.append(obj)
            if records:
                return records
    except Exception:
        pass
    return _load_score_records_from_state_log()


def _load_score_records_from_state_log() -> list[dict]:
    if not SCORE_STATE_LOG.exists():
        return []
    try:
        latest: list[dict] = []
        for line in SCORE_STATE_LOG.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            records = payload.get("records")
            if isinstance(records, list):
                latest = [dict(item) for item in records if isinstance(item, dict)]
        return latest
    except Exception:
        return []


def _persist_score_records(records: list[dict]) -> None:
    SCORE_LOG.parent.mkdir(parents=True, exist_ok=True)
    append_jsonl(
        SCORE_STATE_LOG,
        {
            "records": records,
        },
    )
    atomic_write_jsonl(SCORE_LOG, records)


def _load_journal(date_str: str) -> dict:
    """Load sam_daily_journal entry for date_str."""
    try:
        return _read_jsonl_by_date(JOURNAL_LOG, date_str)
    except Exception:
        return {}


def _load_nutrition(date_str: str) -> dict:
    """Load nutrition_log entry for date_str; sums macros from meals list."""
    try:
        raw = _read_jsonl_by_date(NUTRITION_LOG, date_str)
        if not raw:
            return {}
        meals = raw.get("meals", [])
        totals: dict[str, float] = {
            "protein_g": 0.0,
            "carb_g": 0.0,
            "fat_g": 0.0,
            "calories": 0.0,
            "meal_names": [],
        }
        for m in meals:
            totals["protein_g"] += float(m.get("protein_g", 0) or 0)
            totals["carb_g"]    += float(m.get("carb_g", 0) or 0)
            totals["fat_g"]     += float(m.get("fat_g", 0) or 0)
            totals["calories"]  += float(m.get("calories", 0) or 0)
            name = str(m.get("name", "")).lower().strip()
            if name:
                totals["meal_names"].append(name)
        return totals
    except Exception:
        return {}


def _load_sleep(date_str: str) -> dict:
    """Load sleep_log entry for date_str."""
    try:
        return _read_jsonl_by_date(SLEEP_LOG, date_str)
    except Exception:
        return {}


def _load_adherence(date_str: str) -> dict:
    """Load sam_adherence entry for date_str."""
    try:
        return _read_jsonl_by_date(ADHERENCE_LOG, date_str)
    except Exception:
        return {}


# ── Scoring sub-functions ──────────────────────────────────────────────────────

def _score_sleep(sleep: dict) -> tuple[int, str]:
    """Score sleep domain (max 20)."""
    try:
        hours   = float(sleep.get("total_hours", 0) or 0)
        quality = float(sleep.get("sleep_quality", 0) or 0)
        notes   = str(sleep.get("notes", "") or "").lower()

        if not sleep or hours == 0:
            return 5, "No sleep data (gap)"

        # Base score via interpolation
        if hours >= 7.5:
            if hours > 9:
                base = 16
            else:
                # interpolate 7.5h=20, gradually drops after 9
                t = min((hours - 7.5) / 1.5, 1.0)
                base = round(20 - t * 4)
        elif hours >= 6:
            t = (hours - 6) / 1.5
            base = round(14 + t * 6)
        elif hours >= 4:
            t = (hours - 4) / 2
            base = round(8 + t * 6)
        else:
            t = hours / 4
            base = round(t * 8)

        # Quality bonus (max 3 pts, only if hours >= 5)
        bonus = 0
        if hours >= 5 and quality > 0:
            bonus = round((quality / 10) * 3)

        # Fragmentation penalty
        penalty = 0
        if "nap" in notes and hours < 7:
            penalty = 2

        score = max(0, min(20, base + bonus - penalty))
        detail = f"{hours:.1f}h sleep, quality {quality}/10"
        return score, detail
    except Exception:
        return 5, "Sleep scoring error"


def _score_glycemic(nutrition: dict, journal: dict) -> tuple[int, str]:
    """Score glycemic / nutrition quality domain (max 18)."""
    try:
        carbs = float(nutrition.get("carb_g", 0) or 0) if nutrition else 0
        meal_names = nutrition.get("meal_names", []) if nutrition else []

        if not nutrition:
            return 9, "No nutrition data (gap)"

        # Carb-based score
        if carbs <= 80:
            base = 18
        elif carbs <= 100:
            base = 15
        elif carbs <= 130:
            base = 10
        elif carbs <= 160:
            base = 6
        elif carbs <= 200:
            base = 3
        else:
            base = 0

        # Bonus for no high-glycemic items
        has_bad = any(
            hg_word in meal_name
            for meal_name in meal_names
            for hg_word in HIGH_GLYCEMIC
        )
        bonus = 0 if has_bad else 2

        score = min(18, base + bonus)
        detail = f"{carbs:.0f}g carbs logged"
        return score, detail
    except Exception:
        return 9, "Nutrition scoring error"


def _score_exercise(journal: dict) -> tuple[int, str]:
    """Score exercise domain (max 15)."""
    try:
        extracted = journal.get("extracted", {}) if journal else {}
        exercises = extracted.get("exercise", []) or []

        if not exercises:
            return 0, "No exercise logged"

        total_min = 0
        for ex in exercises:
            dur = ex.get("duration_min", 0) or 0
            try:
                total_min += int(dur)
            except Exception:
                pass

        if total_min >= 90:
            score = 15
        elif total_min >= 60:
            score = 13
        elif total_min >= 30:
            score = 10
        else:
            score = 7  # any exercise logged

        detail = f"{total_min} min total exercise"
        return score, detail
    except Exception:
        return 0, "Exercise scoring error"


def _score_hydration(journal: dict) -> tuple[int, str]:
    """Score hydration domain (max 10)."""
    try:
        extracted = journal.get("extracted", {}) if journal else {}
        water_oz = extracted.get("water_oz", None)

        if water_oz is None or (water_oz == 0 and not journal):
            return 1, "No hydration data (gap)"
        if water_oz == 0:
            return 1, "0 oz logged (data gap)"

        oz = float(water_oz)
        if oz >= 96:
            score = 10
        elif oz >= 64:
            score = 7
        elif oz >= 32:
            score = 4
        elif oz >= 16:
            score = 2
        else:
            score = 0

        detail = f"{oz:.0f} oz water"
        return score, detail
    except Exception:
        return 1, "Hydration scoring error"


def _score_protein(nutrition: dict) -> tuple[int, str]:
    """Score protein compliance (CKD) domain (max 10)."""
    try:
        if not nutrition:
            return 5, "No protein data (gap)"

        protein = float(nutrition.get("protein_g", 0) or 0)
        if protein == 0:
            return 5, "0g protein logged (data gap)"

        if 60 <= protein <= 90:
            score = 10
            detail = f"{protein:.0f}g protein (optimal CKD range)"
        elif 50 <= protein < 60:
            score = 7
            detail = f"{protein:.0f}g protein (slightly low)"
        elif 90 < protein <= 100:
            score = 7
            detail = f"{protein:.0f}g protein (approaching CKD limit)"
        elif 40 <= protein < 50:
            score = 4
            detail = f"{protein:.0f}g protein (low)"
        elif 100 < protein <= 110:
            score = 4
            detail = f"{protein:.0f}g protein (over CKD limit)"
        elif protein < 40:
            score = 2
            detail = f"{protein:.0f}g protein (very low)"
        else:  # > 110
            score = 1
            detail = f"{protein:.0f}g protein (dangerous for CKD)"

        return score, detail
    except Exception:
        return 5, "Protein scoring error"


def _score_mental(journal: dict) -> tuple[int, str]:
    """Score mental health domain (max 10)."""
    try:
        extracted = journal.get("extracted", {}) if journal else {}
        mood         = str(extracted.get("mood", "") or "").lower().strip()
        stress_level = float(extracted.get("stress_level", 0) or 0)
        energy_level = float(extracted.get("energy_level", 0) or 0)

        if not journal:
            return 5, "No mental health data (gap)"

        mood_scores = {
            "great": 10, "good": 8, "okay": 6,
            "low": 3, "anxious": 4, "stressed": 3,
        }
        base = mood_scores.get(mood, 5)

        # Clamp stress/energy to 0-10 range then halve
        stress_penalty = min(5, max(0, stress_level / 2))
        energy_bonus   = min(5, max(0, energy_level / 2))

        score = max(0, min(10, round(base - stress_penalty + energy_bonus)))
        detail = f"Mood: {mood or 'unknown'}, stress {stress_level}, energy {energy_level}"
        return score, detail
    except Exception:
        return 5, "Mental health scoring error"


def _score_adherence(adherence: dict) -> tuple[int, str]:
    """Score protocol adherence domain (max 10)."""
    try:
        PROTOCOL_ITEMS = {"workout", "breakfast", "lunch", "dinner", "hydration", "recovery"}
        completed = set(str(x).lower().strip() for x in (adherence.get("completed", []) or []))

        if not adherence:
            return 5, "No adherence data (gap)"

        matched = completed & PROTOCOL_ITEMS
        count   = len(matched)
        score   = round(count * (10 / 6))
        score   = min(10, score)
        detail  = f"{count}/6 protocol items completed"
        return score, detail
    except Exception:
        return 5, "Adherence scoring error"


def _score_baseline() -> tuple[int, str]:
    """
    Score biometric baseline (max 7).
    Static deductions based on Chris's known out-of-range labs.
    Optionally adjusted by journal symptoms/mood.
    """
    # Chris's known values (hardcoded medical context)
    A1C  = 7.3   # target <7.0
    LDL  = 156   # target <100
    BMI  = 35.7  # target <35
    EGFR = 75    # CKD Stage 2 estimate (eGFR 60-89)

    score = 7
    deductions = []
    if A1C >= 7.0:
        score -= 2
        deductions.append("A1c out of range")
    if LDL >= 130:
        score -= 2
        deductions.append("LDL elevated")
    if BMI >= 35:
        score -= 1
        deductions.append("BMI ≥35")
    if EGFR < 90:
        score -= 1
        deductions.append("eGFR<90 (CKD)")

    score = max(0, score)
    detail = "Labs: " + (", ".join(deductions) if deductions else "all in range")
    return score, detail


def _score_baseline_with_journal(journal: dict) -> tuple[int, str]:
    """Baseline score adjusted with optional journal mood/symptoms bonus."""
    score, detail = _score_baseline()
    try:
        extracted = journal.get("extracted", {}) if journal else {}
        symptoms  = extracted.get("physical_symptoms", []) or []
        mood      = str(extracted.get("mood", "") or "").lower().strip()
        if symptoms == [] and mood in ("great", "good"):
            score = min(7, score + 1)
            detail += ", feeling well today (+1)"
    except Exception:
        pass
    return score, detail


# ── Grade / color helpers ──────────────────────────────────────────────────────

def _grade(score: int) -> str:
    if score >= 90:
        return "A"
    if score >= 75:
        return "B"
    if score >= 60:
        return "C"
    if score >= 45:
        return "D"
    return "F"


def _color(score: int) -> str:
    if score >= 75:
        return "#10b981"
    if score >= 50:
        return "#f59e0b"
    return "#ef4444"


# ── Main public functions ──────────────────────────────────────────────────────

def compute_daily_score(date_str: str) -> dict:
    """
    Compute the full daily health score for date_str.
    Returns a dict with score, grade, color, breakdown, has_data.
    Never raises.
    """
    try:
        journal   = _load_journal(date_str)
        nutrition = _load_nutrition(date_str)
        sleep     = _load_sleep(date_str)
        adherence = _load_adherence(date_str)

        has_data = bool(journal or nutrition)

        sleep_pts,     sleep_detail     = _score_sleep(sleep)
        glycemic_pts,  glycemic_detail  = _score_glycemic(nutrition, journal)
        exercise_pts,  exercise_detail  = _score_exercise(journal)
        hydration_pts, hydration_detail = _score_hydration(journal)
        protein_pts,   protein_detail   = _score_protein(nutrition)
        mental_pts,    mental_detail    = _score_mental(journal)
        adherence_pts, adherence_detail = _score_adherence(adherence)
        baseline_pts,  baseline_detail  = _score_baseline_with_journal(journal)

        total = (
            sleep_pts + glycemic_pts + exercise_pts + hydration_pts
            + protein_pts + mental_pts + adherence_pts + baseline_pts
        )
        total = max(0, min(100, total))

        result: dict[str, Any] = {
            "date":  date_str,
            "score": total,
            "grade": _grade(total),
            "color": _color(total),
            "breakdown": {
                "sleep":     {"pts": sleep_pts,     "max": 20, "detail": sleep_detail},
                "glycemic":  {"pts": glycemic_pts,  "max": 18, "detail": glycemic_detail},
                "exercise":  {"pts": exercise_pts,  "max": 15, "detail": exercise_detail},
                "hydration": {"pts": hydration_pts, "max": 10, "detail": hydration_detail},
                "protein":   {"pts": protein_pts,   "max": 10, "detail": protein_detail},
                "mental":    {"pts": mental_pts,    "max": 10, "detail": mental_detail},
                "adherence": {"pts": adherence_pts, "max": 10, "detail": adherence_detail},
                "baseline":  {"pts": baseline_pts,  "max": 7,  "detail": baseline_detail},
            },
            "has_data": has_data,
        }
        return result
    except Exception as exc:
        return {
            "date":      date_str,
            "score":     0,
            "grade":     "F",
            "color":     "#ef4444",
            "breakdown": {},
            "has_data":  False,
            "error":     str(exc),
        }


def upsert_score(entry: dict) -> None:
    """Append or update a score entry in SCORE_LOG (JSONL, upserted by date)."""
    try:
        date_str = entry.get("date", "")
        records = _load_score_records()
        updated_records: list[dict] = []
        updated = False
        for obj in records:
            if obj.get("date") == date_str:
                updated_records.append(entry)
                updated = True
            else:
                updated_records.append(obj)
        if not updated:
            updated_records.append(entry)
        _persist_score_records(updated_records)
    except Exception:
        pass


def get_score_history(days: int = 30) -> list[dict]:
    """
    Return list of {"date": str, "score": int|None, "grade": str, "color": str}
    for the last N calendar days. Reads from cache first; calls compute_daily_score
    for any uncached dates. Skips dates with has_data=False (returns score=None).
    Sorted ascending by date.
    """
    try:
        today  = date.today()
        result: list[dict] = []

        # Load cache index
        cache: dict[str, dict] = {}
        for obj in _load_score_records():
            d = obj.get("date")
            if d:
                cache[d] = obj

        for i in range(days - 1, -1, -1):
            d = (today - timedelta(days=i)).isoformat()
            if d in cache:
                entry = cache[d]
            else:
                entry = compute_daily_score(d)
                if entry.get("has_data"):
                    upsert_score(entry)

            if not entry.get("has_data"):
                result.append({"date": d, "score": None, "grade": None, "color": None})
            else:
                result.append({
                    "date":  d,
                    "score": entry.get("score"),
                    "grade": entry.get("grade"),
                    "color": entry.get("color"),
                })

        return result
    except Exception:
        return []
