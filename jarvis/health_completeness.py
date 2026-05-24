"""
JARVIS Health — Baseline Completeness Score
============================================
Computes a 100-point completeness score across 8 health domains by reading
Chris's canonical health state JSON at ~/.jarvis/health/chris_health_state.json.

Usage
-----
    from jarvis.health_completeness import run_completeness_check
    result = run_completeness_check()

Or from the CLI::

    python -m jarvis.health_completeness
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

_HEALTH_STATE_PATH = Path.home() / ".jarvis" / "health" / "chris_health_state.json"
_OUTPUT_PATH = Path.home() / ".jarvis" / "health" / "completeness_score.json"

# ---------------------------------------------------------------------------
# Grade thresholds
# ---------------------------------------------------------------------------
_GRADES = [
    (90, "A"),
    (80, "B+"),
    (70, "B"),
    (60, "C"),
    (0,  "D"),
]


def _grade(score: float) -> str:
    for threshold, letter in _GRADES:
        if score >= threshold:
            return letter
    return "D"


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _present(value: Any) -> bool:
    """Return True if *value* is non-None and non-empty."""
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() not in ("", "null", "unknown", "TODO", "N/A")
    if isinstance(value, (list, dict)):
        return len(value) > 0
    return True


def _months_since(date_str: str | None) -> float | None:
    """
    Return approximate months since *date_str* (ISO-8601 date).
    Returns None when the date cannot be parsed.
    """
    if not date_str or not _present(date_str):
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            dt = datetime.strptime(date_str.strip()[:10], fmt)
            now = datetime.now()
            return (now.year - dt.year) * 12 + (now.month - dt.month)
        except ValueError:
            continue
    return None


def _lab_credit(lab_entry: dict | None) -> float:
    """
    Return 0.0–1.0 credit for a lab entry based on recency.
    >24 months → 0, >12 months → 0.5, current → 1.0.
    """
    if lab_entry is None:
        return 0.0
    if not _present(lab_entry.get("value")) and not _present(lab_entry.get("result")):
        return 0.0
    date_str = lab_entry.get("date") or lab_entry.get("result_date")
    age = _months_since(date_str)
    if age is None:
        return 0.5  # date unknown but value present → partial credit
    if age > 24:
        return 0.0
    if age > 12:
        return 0.5
    return 1.0


# ---------------------------------------------------------------------------
# Domain scorers
# ---------------------------------------------------------------------------

def _score_identity_vitals(state: dict) -> dict:
    """Domain 1 — Identity & Vitals (15 pts, 3 pts each)."""
    ib = state.get("identity_baseline", {})
    max_score = 15
    items = {
        "DOB": ("date_of_birth", 3),
        "height": ("height", 3),
        "weight": ("current_weight_lbs", 3),
        "waist measurement": ("waist_circumference", 3),
        "BMI": ("bmi", 3),
    }
    score = 0.0
    gaps = []
    for label, (key, pts) in items.items():
        val = ib.get(key)
        if _present(val):
            # Partial credit: weight marked estimated
            if key == "current_weight_lbs":
                # Look for 'estimated' indicator in lifestyle context
                notes = str(val)
                if "estimated" in str(state.get("identity_baseline", {})).lower():
                    score += pts * 0.7
                    gaps.append("weight flagged as estimated — confirm measured value")
                else:
                    score += pts
            else:
                score += pts
        else:
            gaps.append(f"{label} missing")

    return {
        "score": round(score, 1),
        "max": max_score,
        "pct": round(score / max_score * 100, 1),
        "gaps": gaps,
    }


def _find_lab(labs: list[dict], *names: str) -> dict | None:
    """Find the most recent lab entry matching any of the given name keywords."""
    names_lower = [n.lower() for n in names]
    matches = [
        lab for lab in labs
        if any(kw in lab.get("panel", "").lower() for kw in names_lower)
    ]
    if not matches:
        return None
    # Return most recent
    def sort_key(lab: dict) -> str:
        return lab.get("date") or lab.get("result_date") or ""
    return max(matches, key=sort_key)


def _score_lab_coverage(state: dict) -> dict:
    """Domain 2 — Lab Coverage (20 pts, 2.5 pts each across 8 panels)."""
    labs_list: list[dict] = state.get("labs_diagnostics", {}).get("labs", [])
    max_score = 20.0
    pts_each = 2.5

    panels = [
        ("Metabolic Panel", ("metabolic", "cmp", "bmp", "comprehensive metabolic", "basic metabolic")),
        ("Lipids", ("lipid", "cholesterol", "ldl", "hdl", "triglyceride")),
        ("CBC", ("cbc", "complete blood count", "hemoglobin", "hematocrit", "wbc", "rbc")),
        ("HbA1c", ("hemoglobin a1c", "hba1c", "a1c", "glycated")),
        ("Kidney Function", ("creatinine", "gfr", "bun", "kidney", "renal")),
        ("Electrolytes", ("electrolyte", "sodium", "potassium", "chloride", "bicarbonate", "co2")),
        ("Thyroid", ("thyroid", "tsh", "t3", "t4", "free t")),
        ("Micronutrients", ("vitamin d", "b12", "folate", "magnesium", "zinc", "ferritin", "iron")),
    ]

    score = 0.0
    gaps = []
    for panel_name, keywords in panels:
        lab = _find_lab(labs_list, *keywords)
        credit = _lab_credit(lab)
        score += pts_each * credit
        if credit == 0.0:
            gaps.append(f"{panel_name} missing or >24 months old")
        elif credit < 1.0:
            age = _months_since(lab.get("date") or lab.get("result_date")) if lab else None
            if age and age > 12:
                gaps.append(f"{panel_name} last drawn {age:.0f} months ago — refresh recommended")
            else:
                gaps.append(f"{panel_name} date unknown — verify recency")

    return {
        "score": round(score, 1),
        "max": max_score,
        "pct": round(score / max_score * 100, 1),
        "gaps": gaps,
    }


def _score_medication_verification(state: dict) -> dict:
    """
    Domain 3 — Medication Verification (15 pts).
    Scored proportionally to how complete each med record is (indication + dose + last review).
    """
    meds: list[dict] = state.get("current_care_state", {}).get("medications", [])
    max_score = 15.0
    gaps = []

    if not meds:
        return {
            "score": 0.0,
            "max": max_score,
            "pct": 0.0,
            "gaps": ["No medications documented"],
        }

    total_fields = 0
    filled_fields = 0
    for med in meds:
        name = med.get("name") or med.get("medication")
        dose = med.get("dose") or med.get("dosage")
        reason = med.get("reason") or med.get("indication")
        # Last review date may not be in state; note it as a gap
        total_fields += 3  # name, dose, reason
        if _present(name):
            filled_fields += 1
        if _present(dose):
            filled_fields += 1
        else:
            gaps.append(f"Dose missing for {name or 'unknown med'}")
        if _present(reason):
            filled_fields += 1
        else:
            gaps.append(f"Indication missing for {name or 'unknown med'}")

    # Last review date not typically in state — always flag it
    gaps.append("Medication review date not documented in health state")

    completeness = filled_fields / total_fields if total_fields > 0 else 0.0
    score = max_score * completeness

    return {
        "score": round(score, 1),
        "max": max_score,
        "pct": round(completeness * 100, 1),
        "gaps": gaps[:6],  # cap for readability
    }


def _score_wearable_data(state: dict) -> dict:
    """Domain 4 — Wearable Data Streams (10 pts)."""
    bm = state.get("biometrics", {})
    gm = bm.get("glucose_metrics", {})
    wm = bm.get("wearable_metrics", {})
    vitals = bm.get("vitals", {})

    max_score = 10.0
    score = 0.0
    gaps = []

    # CGM live (3 pts)
    if gm.get("cgm_active") is True:
        score += 3.0
    else:
        gaps.append("Live CGM not connected (Dexcom OAuth pending)")

    # Home BP log (3 pts)
    bp_log = vitals.get("blood_pressure", {}).get("home_bp_log", "")
    if _present(bp_log) and "no" not in str(bp_log).lower() and "pending" not in str(bp_log).lower():
        score += 3.0
    else:
        gaps.append("Home BP log empty — no Omron readings in database")

    # HRV/steps (2 pts)
    hrv_present = _present(wm.get("hrv")) or _present(wm.get("steps"))
    if hrv_present:
        steps = wm.get("steps")
        hrv = wm.get("hrv")
        score += 1.0 if _present(steps) else 0.0
        score += 1.0 if _present(hrv) else 0.0
        if not _present(hrv):
            gaps.append("HRV not synced to wearable metrics")
    else:
        score += 0.0
        gaps.append("HRV and step data not present")

    # SpO2 (2 pts)
    spo2 = bm.get("vitals", {}).get("oxygen_saturation") or wm.get("spo2") or wm.get("blood_oxygen")
    if _present(spo2):
        score += 2.0
    else:
        gaps.append("SpO2/blood oxygen data not documented")

    return {
        "score": round(score, 1),
        "max": max_score,
        "pct": round(score / max_score * 100, 1),
        "gaps": gaps,
    }


def _score_care_team(state: dict) -> dict:
    """Domain 5 — Care Team (10 pts)."""
    team: list[dict] = state.get("current_care_state", {}).get("care_team", [])
    max_score = 10.0
    score = 0.0
    gaps = []

    def _has_role(*keywords: str) -> bool:
        for member in team:
            role = (member.get("role") or member.get("specialty") or "").lower()
            name = (member.get("name") or "").lower()
            if any(kw.lower() in role or kw.lower() in name for kw in keywords):
                return True
        return False

    roles = [
        ("PCP", 3, ("primary care", "pcp", "internal medicine", "family medicine", "treating physician")),
        ("Cardiologist", 2, ("cardiol",)),
        ("Endocrinologist", 2, ("endocrinol", "diabetes", "endo")),
        ("Sleep Medicine", 1, ("sleep",)),
        ("Other Specialists", 2, ("neurol", "nephrol", "ophthalmol", "retina", "pulmonol", "dermatol", "orthop", "specialist")),
    ]

    for label, pts, keywords in roles:
        if _has_role(*keywords):
            score += pts
        else:
            gaps.append(f"{label} not documented in care team")

    return {
        "score": round(score, 1),
        "max": max_score,
        "pct": round(score / max_score * 100, 1),
        "gaps": gaps,
    }


def _score_family_history(state: dict) -> dict:
    """Domain 6 — Family History (10 pts)."""
    fh = state.get("medical_history", {}).get("family_history", [])
    max_score = 10.0
    score = 0.0
    gaps = []

    # family_history is a list of {condition, relation, notes}
    relations_text = " ".join(
        (entry.get("relation") or "").lower() for entry in fh
    ).strip()

    # Parents (4 pts)
    if any(kw in relations_text for kw in ("parent", "mother", "father", "mom", "dad")):
        score += 4.0
    else:
        gaps.append("Parental family history not documented")

    # Siblings (3 pts)
    if any(kw in relations_text for kw in ("sibling", "brother", "sister")):
        score += 3.0
    else:
        gaps.append("Sibling family history not documented")

    # Grandparents (2 pts)
    if any(kw in relations_text for kw in ("grandparent", "grandmother", "grandfather", "grandma", "grandpa")):
        score += 2.0
    else:
        gaps.append("Grandparental family history not documented")

    # Hereditary conditions documented (1 pt) — any entry counts
    if fh:
        score += 1.0
    else:
        gaps.append("No hereditary conditions documented")

    return {
        "score": round(score, 1),
        "max": max_score,
        "pct": round(score / max_score * 100, 1),
        "gaps": gaps,
    }


def _score_behavioral_data(state: dict) -> dict:
    """Domain 7 — Behavioral Data (10 pts)."""
    cc = state.get("current_care_state", {})
    lc = state.get("lifestyle_context", {})
    max_score = 10.0
    score = 0.0
    gaps = []

    # Supplements documented (2 pts)
    supplements = cc.get("supplements", [])
    if _present(supplements):
        score += 2.0
    else:
        gaps.append("Supplements not documented")

    # Alcohol use (2 pts)
    nutrition = lc.get("nutrition", {})
    alcohol = (
        nutrition.get("alcohol")
        or nutrition.get("alcohol_use")
        or lc.get("stress_mood", {}).get("alcohol")
    )
    if _present(alcohol):
        score += 2.0
    else:
        gaps.append("Alcohol use not documented in lifestyle context")

    # Exercise pattern (2 pts)
    movement = lc.get("movement", {})
    if _present(movement) and (
        _present(movement.get("pattern"))
        or _present(movement.get("frequency"))
        or _present(movement.get("type"))
        or _present(movement.get("description"))
        or len(movement) >= 2
    ):
        score += 2.0
    else:
        gaps.append("Exercise pattern not documented")

    # Sleep consistency data (2 pts)
    sleep = lc.get("sleep", {})
    if _present(sleep) and (
        _present(sleep.get("average_hours"))
        or _present(sleep.get("consistency"))
        or _present(sleep.get("schedule"))
        or len(sleep) >= 2
    ):
        score += 2.0
    else:
        gaps.append("Sleep consistency data not documented")

    # Diet pattern (2 pts)
    diet = (
        nutrition.get("diet_pattern")
        or nutrition.get("pattern")
        or nutrition.get("description")
        or nutrition.get("type")
    )
    if _present(diet):
        score += 2.0
    else:
        gaps.append("Diet pattern not documented in nutrition context")

    return {
        "score": round(score, 1),
        "max": max_score,
        "pct": round(score / max_score * 100, 1),
        "gaps": gaps,
    }


def _score_screening_status(state: dict) -> dict:
    """Domain 8 — Screening Status (10 pts)."""
    pc = state.get("preventive_care", {})
    screenings: list[dict] = pc.get("screenings", [])
    max_score = 10.0
    score = 0.0
    gaps = []

    def _screening_done(*keywords: str) -> bool:
        for s in screenings:
            item = (s.get("item") or "").lower()
            status = (s.get("status") or "").lower()
            if any(kw.lower() in item for kw in keywords):
                return "done" in status or "complete" in status or "normal" in status or "negative" in status
        return False

    # Colonoscopy (3 pts)
    if _screening_done("colonoscopy", "colon"):
        score += 3.0
    else:
        gaps.append("Colonoscopy status unknown or not completed")

    # CPAP confirmed (3 pts)
    sleep_apnea = pc.get("sleep_apnea_evaluation", {})
    treatment = (sleep_apnea.get("treatment_status") or "").lower()
    if "cpap" in treatment and "todo" not in treatment and "unconfirmed" not in treatment:
        score += 3.0
    else:
        gaps.append("CPAP status unconfirmed — OSA diagnosis active but treatment unclear")

    # Eye exam / retinal exam (2 pts)
    if _screening_done("retinal", "eye", "vision", "ophthalmol"):
        score += 2.0
    else:
        gaps.append("Eye exam not documented as completed")

    # Dental (1 pt)
    dental = pc.get("dental", {})
    dental_status = (dental.get("status") or "").lower() if isinstance(dental, dict) else ""
    if _present(dental) and ("done" in dental_status or "current" in dental_status or "complete" in dental_status):
        score += 1.0
    else:
        gaps.append("Dental exam status not documented")

    # Skin check (1 pt)
    skin = pc.get("skin_check", {})
    skin_status = (skin.get("status") or "").lower() if isinstance(skin, dict) else ""
    if _present(skin) and ("done" in skin_status or "current" in skin_status or "complete" in skin_status):
        score += 1.0
    else:
        gaps.append("Skin check status not documented")

    return {
        "score": round(score, 1),
        "max": max_score,
        "pct": round(score / max_score * 100, 1),
        "gaps": gaps,
    }


# ---------------------------------------------------------------------------
# Critical gaps and quick wins
# ---------------------------------------------------------------------------

_CRITICAL_KEYWORDS = [
    "cgm not connected",
    "cpap status",
    "colonoscopy",
    "home bp log",
    "kidney",
    "thyroid",
    "parental family",
    "no medications",
]


def _derive_quick_wins(domains: dict) -> list[str]:
    """Surface low-effort, high-value gaps as quick wins."""
    quick_wins = []
    easy_phrases = [
        "weight flagged as estimated",
        "alcohol use",
        "diet pattern",
        "supplements not documented",
        "skin check",
        "dental exam",
        "sleep consistency",
        "exercise pattern",
        "dose missing",
        "indication missing",
        "medication review date",
    ]
    for domain_data in domains.values():
        for gap in domain_data.get("gaps", []):
            gl = gap.lower()
            if any(phrase in gl for phrase in easy_phrases):
                quick_wins.append(gap)
    return quick_wins[:6]


def _derive_critical_gaps(domains: dict) -> list[str]:
    critical = []
    for domain_data in domains.values():
        for gap in domain_data.get("gaps", []):
            gl = gap.lower()
            if any(kw in gl for kw in _CRITICAL_KEYWORDS):
                critical.append(gap)
    return critical


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def calculate_completeness(state: dict) -> dict:
    """
    Compute a 100-point Baseline Completeness Score from a health state dict.

    Parameters
    ----------
    state : dict
        Parsed contents of chris_health_state.json.

    Returns
    -------
    dict
        Scoring object with total_score, grade, per-domain breakdowns,
        critical_gaps, quick_wins, and calculated_at timestamp.
    """
    scorers = {
        "identity_vitals":         _score_identity_vitals,
        "lab_coverage":            _score_lab_coverage,
        "medication_verification": _score_medication_verification,
        "wearable_data_streams":   _score_wearable_data,
        "care_team":               _score_care_team,
        "family_history":          _score_family_history,
        "behavioral_data":         _score_behavioral_data,
        "screening_status":        _score_screening_status,
    }

    domains: dict[str, dict] = {}
    total = 0.0

    for key, fn in scorers.items():
        try:
            result = fn(state)
        except Exception:
            log.exception("Error scoring domain %s", key)
            result = {"score": 0.0, "max": 10, "pct": 0.0, "gaps": ["Scoring error"]}
        domains[key] = result
        total += result["score"]

    total = round(total, 1)

    return {
        "total_score": total,
        "grade": _grade(total),
        "domains": domains,
        "critical_gaps": _derive_critical_gaps(domains),
        "quick_wins": _derive_quick_wins(domains),
        "calculated_at": datetime.now(timezone.utc).isoformat(),
    }


def run_completeness_check() -> dict:
    """
    Load the health state from disk, calculate the completeness score,
    save the result to ~/.jarvis/health/completeness_score.json, and return it.

    Returns
    -------
    dict
        The completeness scoring object.

    Raises
    ------
    FileNotFoundError
        If chris_health_state.json does not exist.
    """
    if not _HEALTH_STATE_PATH.exists():
        raise FileNotFoundError(f"Health state not found: {_HEALTH_STATE_PATH}")

    try:
        state = json.loads(_HEALTH_STATE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        log.error("Failed to parse health state JSON: %s", exc)
        raise

    result = calculate_completeness(state)

    _OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    _OUTPUT_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
    log.info(
        "Completeness score: %.1f/100 (%s) — saved to %s",
        result["total_score"],
        result["grade"],
        _OUTPUT_PATH,
    )
    return result


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        result = run_completeness_check()
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"\nHealth Completeness Score: {result['total_score']}/100  Grade: {result['grade']}\n")
    for domain, data in result["domains"].items():
        bar = "#" * int(data["pct"] / 10)
        print(f"  {domain:<28} {data['score']:>5}/{data['max']}  [{bar:<10}]  {data['pct']:.0f}%")

    if result["critical_gaps"]:
        print("\nCritical Gaps:")
        for g in result["critical_gaps"]:
            print(f"  ! {g}")

    if result["quick_wins"]:
        print("\nQuick Wins:")
        for w in result["quick_wins"]:
            print(f"  * {w}")
