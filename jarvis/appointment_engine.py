"""
JARVIS Appointment Intelligence Module
=======================================
Manages appointment lifecycle: storage, visit prep packet generation,
outcome recording, and health-state integration.

Storage:
  ~/.jarvis/health/appointments.json          — appointment list
  ~/.jarvis/health/appointment_outcomes.jsonl — append-only outcomes log
"""
from __future__ import annotations

import dataclasses
import json
import logging
import os
from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_HEALTH_DIR = Path.home() / ".jarvis" / "health"
_APPOINTMENTS_FILE = _HEALTH_DIR / "appointments.json"
_OUTCOMES_FILE = _HEALTH_DIR / "appointment_outcomes.jsonl"
_HEALTH_STATE_FILE = _HEALTH_DIR / "chris_health_state.json"


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class Appointment:
    """Single scheduled appointment."""

    id: str
    provider: str
    specialty: str
    date: str                       # ISO "YYYY-MM-DD"
    time: str                       # "HH:MM"
    location: str
    reason: str
    prep_required: bool
    priority_questions: list[str]
    labs_to_request: list[str]
    medications_to_review: list[str]
    outcomes: dict | None = None    # filled after visit


@dataclass
class VisitPrepPacket:
    """Full pre-visit preparation packet for an appointment."""

    appointment: Appointment
    generated_at: str                       # ISO datetime string
    patient_summary: str                    # 3-sentence clinical summary
    priority_questions: list[dict]          # [{rank, question, clinical_context, desired_outcome}]
    medication_reconciliation: list[dict]   # [{med, current, proposed_change, rationale}]
    labs_to_order: list[dict]               # [{test, rationale, urgency}]
    screenings_to_discuss: list[dict]       # [{screening, status, action}]
    clinical_data_snapshot: dict            # key metrics for the visit
    since_last_visit: list[str]             # notable changes since last visit


@dataclass
class AppointmentOutcome:
    """Recorded outcome after a completed visit."""

    appointment_id: str
    recorded_at: str                        # ISO datetime string
    decisions_made: list[dict]              # [{topic, decision, action_item}]
    medications_changed: list[dict]         # [{med, change_type, new_dose}]
    labs_ordered: list[str]
    referrals_made: list[str]
    follow_up_date: str | None
    notes: str


# ---------------------------------------------------------------------------
# Default appointment seed data
# ---------------------------------------------------------------------------

_WENK_APPOINTMENT_DEFAULT: dict = {
    "id": "apt-wenk-20261113",
    "provider": "Dr. Susan Wenk",
    "specialty": "Primary Care / Internal Medicine",
    "date": "2026-11-13",
    "time": "10:00",
    "location": "TBD",
    "reason": "Chronic disease management: T2DM, HTN, dyslipidemia, post-bariatric follow-up",
    "prep_required": True,
    "priority_questions": [],
    "labs_to_request": [],
    "medications_to_review": [],
    "outcomes": None,
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _ensure_health_dir() -> None:
    """Create ~/.jarvis/health/ if it does not exist."""
    _HEALTH_DIR.mkdir(parents=True, exist_ok=True)


def _load_appointments_raw() -> list[dict]:
    """
    Load raw appointment dicts from disk.

    If the file is missing or empty, seeds it with the Dr. Wenk appointment
    and returns that list.  If the file exists but does not contain the
    canonical ``apt-wenk-20261113`` record, that record is injected and the
    file is updated so subsequent lookups succeed.
    """
    _ensure_health_dir()
    if not _APPOINTMENTS_FILE.exists() or _APPOINTMENTS_FILE.stat().st_size == 0:
        log.info("appointments.json not found — seeding with Dr. Wenk appointment")
        _save_appointments_raw([_WENK_APPOINTMENT_DEFAULT])
        return [_WENK_APPOINTMENT_DEFAULT]

    try:
        with _APPOINTMENTS_FILE.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, list):
            log.warning("appointments.json root is not a list — resetting")
            _save_appointments_raw([_WENK_APPOINTMENT_DEFAULT])
            return [_WENK_APPOINTMENT_DEFAULT]

        # Ensure canonical Wenk record is present by its canonical ID
        ids = {rec.get("id") for rec in data}
        if "apt-wenk-20261113" not in ids:
            log.info(
                "Canonical apt-wenk-20261113 not found in appointments.json — injecting"
            )
            data.insert(0, _WENK_APPOINTMENT_DEFAULT)
            _save_appointments_raw(data)

        return data
    except (json.JSONDecodeError, OSError) as exc:
        log.error("Failed to load appointments.json: %s", exc)
        return [_WENK_APPOINTMENT_DEFAULT]


def _save_appointments_raw(appointments: list[dict]) -> None:
    """Persist appointment list to disk."""
    _ensure_health_dir()
    try:
        with _APPOINTMENTS_FILE.open("w", encoding="utf-8") as fh:
            json.dump(appointments, fh, indent=2, default=str)
    except OSError as exc:
        log.error("Failed to save appointments.json: %s", exc)


def _dict_to_appointment(raw: dict) -> Appointment:
    """Convert a raw dict to an Appointment dataclass, tolerating missing keys."""
    return Appointment(
        id=raw.get("id", ""),
        provider=raw.get("provider", ""),
        specialty=raw.get("specialty", ""),
        date=raw.get("date", ""),
        time=raw.get("time", ""),
        location=raw.get("location", ""),
        reason=raw.get("reason", ""),
        prep_required=raw.get("prep_required", False),
        priority_questions=raw.get("priority_questions", []),
        labs_to_request=raw.get("labs_to_request", []),
        medications_to_review=raw.get("medications_to_review", []),
        outcomes=raw.get("outcomes"),
    )


def _load_health_state() -> dict:
    """
    Load chris_health_state.json from ~/.jarvis/health/.

    Returns an empty dict if the file is missing or unreadable.
    """
    if not _HEALTH_STATE_FILE.exists():
        log.info("chris_health_state.json not found — proceeding without health state")
        return {}
    try:
        with _HEALTH_STATE_FILE.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        log.error("Failed to load chris_health_state.json: %s", exc)
        return {}


def _save_health_state(state: dict) -> None:
    """Persist health state dict to disk."""
    try:
        with _HEALTH_STATE_FILE.open("w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=2, default=str)
    except OSError as exc:
        log.error("Failed to save chris_health_state.json: %s", exc)


# ---------------------------------------------------------------------------
# Clinical constants for Dr. Wenk visit prep
# ---------------------------------------------------------------------------

_PATIENT_SUMMARY = (
    "Chris is a 52-year-old male with T2DM (A1c 7.3%), treatment-resistant hypertension "
    "on 4 agents (BP 140/90), statin myopathy with untreated LDL 156 mg/dL "
    "(10yr ASCVD risk 15.2%), and post-sleeve gastrectomy (Dec 2019) with BMI 35.7. "
    "OSA tested borderline 2019, CPAP discontinued as ineffective, diagnosis resolved. "
    "He has overdue post-bariatric labs and a K+ of 5.4 (Mar 2025) on olmesartan + spironolactone."
)

_PRIORITY_QUESTIONS: list[dict] = [
    {
        "rank": 1,
        "question": "LDL is 156 mg/dL with no active lipid therapy — what do we start today?",
        "clinical_context": (
            "LDL rose from 99 to 156 mg/dL over 5 years; no active therapy; "
            "statin myopathy documented; 10-year ASCVD risk 15.2%; goal <100 mg/dL. "
            "Grade A evidence for non-statin alternatives."
        ),
        "desired_outcome": (
            "Start ezetimibe 10 mg today. Discuss bempedoic acid and PCSK9i "
            "(alirocumab) as escalation options. No statin rechallenge without "
            "specialist evaluation."
        ),
        "urgency": "CRITICAL",
    },
    {
        "rank": 2,
        "question": "A1c is 7.3% — can we intensify diabetes management?",
        "clinical_context": (
            "A1c relapsed from 5.9% (2024) to 7.3% (2026); on semaglutide 2 mg + "
            "metformin ER 500 mg (underdosed for body weight); goal <7.0%."
        ),
        "desired_outcome": (
            "Increase metformin ER to 1000–1500 mg if tolerated. Discuss semaglutide "
            "2.4 mg (obesity dose) for additional weight loss and CV benefit. "
            "Check CGM time-in-range if available."
        ),
        "urgency": "HIGH",
    },
    {
        "rank": 3,
        "question": "I take spironolactone and my K+ was 5.4 in March 2025 — is spironolactone still indicated?",
        "clinical_context": (
            "Olmesartan/HCTZ + spironolactone + T2DM = hyperkalemia triad. "
            "K+ was 5.4 in Mar 2025; current K+ 4.5. Dual RAAS blockade carries "
            "significant hyperkalemia and AKI risk."
        ),
        "desired_outcome": (
            "Confirm indication for spironolactone (resistant HTN vs. "
            "hyperaldosteronism). Check current K+. If spironolactone not essential, "
            "discuss stopping or switching to finerenone."
        ),
        "urgency": "HIGH — safety",
    },
    {
        "rank": 4,
        "question": "Sleep quality: OSA tested borderline 2019, CPAP tried and discontinued — should we document this formally?",
        "clinical_context": (
            "OSA was borderline on testing 2019; CPAP was prescribed but discontinued as ineffective. "
            "Diagnosis was never formally removed from EMR. Wearable shows SpO2 93% and HRV 45ms — "
            "monitored as sleep quality indicators, not attributed to active OSA. "
            "JARVIS health DB has the diagnosis marked resolved."
        ),
        "desired_outcome": (
            "Formally document OSA as resolved/historical in EMR. Confirm no further OSA workup "
            "is indicated given CPAP was tried and discontinued. Continue wearable SpO2 and HRV monitoring."
        ),
        "urgency": "MODERATE — documentation",
    },
    {
        "rank": 5,
        "question": "When was my last colonoscopy, and am I overdue?",
        "clinical_context": (
            "52-year-old male with family history of colonic polyps; "
            "colonoscopy status unknown in chart."
        ),
        "desired_outcome": (
            "Confirm last colonoscopy date. If not done or overdue: schedule now."
        ),
        "urgency": "MODERATE",
    },
    {
        "rank": 6,
        "question": "I had sleeve gastrectomy in December 2019 — can we order a full post-bariatric micronutrient panel?",
        "clinical_context": (
            "Sleeve gastrectomy Dec 2019 (6.5 years ago). No documented ferritin, "
            "iron panel, B12 with MMA, calcium, PTH, or thiamine since surgery. "
            "Micronutrient deficiencies are silent and progressive."
        ),
        "desired_outcome": (
            "Order today: ferritin, iron, TIBC, transferrin saturation, B12 with MMA, "
            "calcium, ionized calcium, PTH, thiamine, zinc."
        ),
        "urgency": "MODERATE",
    },
]

_MEDICATION_RECONCILIATION: list[dict] = [
    {
        "med": "Metformin ER",
        "current": "500 mg daily",
        "proposed_change": "Increase to 1000–1500 mg daily",
        "rationale": (
            "Underdosed for A1c 7.3% and body weight ~252 lbs. "
            "Post-bariatric absorption slightly reduced but still effective. "
            "Titrate up over 4 weeks to minimize GI side effects."
        ),
    },
    {
        "med": "Spironolactone",
        "current": "25 mg daily",
        "proposed_change": "Review indication — consider stopping",
        "rationale": (
            "K+ 5.4 documented Mar 2025 on olmesartan + spironolactone + T2DM. "
            "If added for resistant HTN rather than confirmed hyperaldosteronism, "
            "risk/benefit tilts toward stopping. Confirm indication first."
        ),
    },
    {
        "med": "Semaglutide",
        "current": "2 mg weekly (diabetes dose)",
        "proposed_change": "Discuss escalating to 2.4 mg (obesity dose)",
        "rationale": (
            "A1c 7.3% and BMI 35.7 both above goal. 2.4 mg dose provides "
            "additional ~2–3% weight loss and documented CV mortality reduction "
            "(SELECT trial). May require prior auth."
        ),
    },
    {
        "med": "Ciprofloxacin (historical Rx)",
        "current": "Unknown — possibly stale",
        "proposed_change": "Flag: confirm this is not an active prescription",
        "rationale": (
            "QTc prolongation risk in combination with citalopram. "
            "If not current, should be removed from active med list."
        ),
    },
    {
        "med": "Olmesartan/HCTZ, Amlodipine, Metoprolol",
        "current": "Current doses",
        "proposed_change": "Continue — confirm adherence",
        "rationale": (
            "BP 140/90 on four agents suggests adherence check before adding "
            "a fifth agent. White-coat effect also possible."
        ),
    },
    {
        "med": "Citalopram",
        "current": "Current dose",
        "proposed_change": "Continue — no change",
        "rationale": (
            "QTc interaction risk with any fluoroquinolone — confirm ciprofloxacin "
            "is not active."
        ),
    },
]

_LABS_TO_ORDER: list[dict] = [
    {
        "test": "Comprehensive Metabolic Panel (CMP)",
        "rationale": "Baseline electrolytes, renal function, LFTs",
        "urgency": "Routine",
    },
    {
        "test": "Potassium (K+)",
        "rationale": "Monitor hyperkalemia risk on olmesartan + spironolactone; last 4.5, prior 5.4",
        "urgency": "Immediate — safety",
    },
    {
        "test": "Creatinine / eGFR",
        "rationale": "Renal function check on dual RAAS blockade; current eGFR 87",
        "urgency": "Immediate — safety",
    },
    {
        "test": "Lipid panel",
        "rationale": "Confirm LDL before starting ezetimibe; last LDL 156 mg/dL",
        "urgency": "High",
    },
    {
        "test": "Hemoglobin A1c",
        "rationale": "Last measured May 2026 at 7.3%; 6-month follow-up due at Nov visit",
        "urgency": "High",
    },
    {
        "test": "CBC",
        "rationale": "Routine — screen for anemia (post-bariatric iron risk)",
        "urgency": "Routine",
    },
    {
        "test": "TSH",
        "rationale": "Not recently documented; hypothyroidism mimics dyslipidemia and fatigue",
        "urgency": "Routine",
    },
    {
        "test": "Urine microalbumin/creatinine ratio",
        "rationale": "Annual diabetic nephropathy screen; eGFR 87 borderline",
        "urgency": "Routine — annual",
    },
    {
        "test": "Ferritin",
        "rationale": "Post-bariatric iron deficiency screen — not checked since sleeve (Dec 2019)",
        "urgency": "Overdue",
    },
    {
        "test": "Iron / TIBC / Transferrin saturation",
        "rationale": "Complete iron panel for bariatric follow-up",
        "urgency": "Overdue",
    },
    {
        "test": "B12 with MMA (methylmalonic acid)",
        "rationale": "Post-bariatric B12 deficiency; MMA detects functional deficiency before serum B12 drops",
        "urgency": "Overdue",
    },
    {
        "test": "25-OH Vitamin D",
        "rationale": "Recheck — post-bariatric absorption impaired",
        "urgency": "Overdue",
    },
    {
        "test": "Calcium / Ionized Calcium",
        "rationale": "Post-bariatric hypocalcemia risk; PTH-calcium axis",
        "urgency": "Overdue",
    },
    {
        "test": "Intact PTH",
        "rationale": "Secondary hyperparathyroidism from chronic calcium/D3 deficiency post-bariatric",
        "urgency": "Overdue",
    },
    {
        "test": "Thiamine (B1)",
        "rationale": "Post-bariatric thiamine deficiency can cause neuropathy and cardiac dysfunction",
        "urgency": "Overdue",
    },
    {
        "test": "Zinc",
        "rationale": "Zinc deficiency common post-sleeve; affects immune function and wound healing",
        "urgency": "Overdue",
    },
    {
        "test": "Phosphorus",
        "rationale": "Hypophosphatemia in post-bariatric patients with vitamin D deficiency",
        "urgency": "Routine",
    },
]

_SCREENINGS_TO_DISCUSS: list[dict] = [
    {
        "screening": "Colonoscopy",
        "status": "Unknown — not documented in chart",
        "action": "Confirm last colonoscopy date; schedule if not done or overdue (family hx polyps)",
    },
    {
        "screening": "Diabetic eye exam (retinopathy screening)",
        "status": "Not documented",
        "action": "Refer to ophthalmology for dilated fundus exam",
    },
    {
        "screening": "Diabetic foot exam",
        "status": "Not documented",
        "action": "Perform monofilament and visual inspection at this visit",
    },
    {
        "screening": "Dental exam",
        "status": "Not documented",
        "action": "Confirm last dental visit; diabetics at higher risk for periodontal disease",
    },
    {
        "screening": "Sleep quality monitoring — OSA historical",
        "status": "OSA tested borderline 2019, CPAP discontinued as ineffective, diagnosis resolved",
        "action": "Formally document OSA as resolved/historical in EMR; continue wearable SpO2 and HRV monitoring",
    },
]

_SINCE_LAST_VISIT: list[str] = [
    "A1c relapsed from 5.9% (2024) to 7.3% (May 2026) — above goal",
    "LDL rose from 99 to 156 mg/dL over 5 years — no active lipid therapy",
    "K+ 5.4 documented Mar 2025 on olmesartan + spironolactone combination",
    "HRV trending down: 45 ms (autonomic stress from HTN and cardiometabolic load; OSA resolved/historical)",
    "eGFR stable at 87 but borderline CKD3 threshold — annual urine albumin check overdue",
    "Post-bariatric micronutrient panel not completed since Dec 2019 surgery (6.5 years overdue)",
    "Colonoscopy status unknown — family history of polyps increases risk",
    "No documented diabetic eye exam, foot exam, or dental in current record",
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_appointments() -> list[Appointment]:
    """
    Load and return all appointments from ~/.jarvis/health/appointments.json.

    If the file does not exist, creates it and seeds it with the Dr. Susan Wenk
    appointment on November 13, 2026. Returns an empty list only if all parsing
    attempts fail.

    Returns:
        list[Appointment]: All stored appointments as dataclass instances.
    """
    raw_list = _load_appointments_raw()
    appointments = []
    for raw in raw_list:
        try:
            appointments.append(_dict_to_appointment(raw))
        except Exception as exc:
            log.warning("Skipping malformed appointment record: %s — %s", raw.get("id"), exc)
    return appointments


def generate_visit_prep_packet(appointment_id: str) -> VisitPrepPacket:
    """
    Generate a full pre-visit preparation packet for the given appointment.

    For the Dr. Wenk appointment (apt-wenk-20261113), returns a richly populated
    packet with ranked priority questions, medication reconciliation plan, ordered
    labs, screening discussions, and a clinical data snapshot.  For other
    appointments, returns a minimal packet with placeholder content.

    Clinical data is loaded from chris_health_state.json where available;
    hardcoded fallbacks are used when the file is missing.

    Args:
        appointment_id: The ``id`` field of the target Appointment.

    Returns:
        VisitPrepPacket: Complete pre-visit packet ready for formatting.

    Raises:
        ValueError: If no appointment with the given ID is found.
    """
    appointments = get_appointments()
    apt = next((a for a in appointments if a.id == appointment_id), None)
    if apt is None:
        raise ValueError(f"No appointment found with id '{appointment_id}'")

    generated_at = datetime.now().isoformat(timespec="seconds")
    snapshot = get_clinical_data_snapshot()

    if appointment_id == "apt-wenk-20261113":
        return VisitPrepPacket(
            appointment=apt,
            generated_at=generated_at,
            patient_summary=_PATIENT_SUMMARY,
            priority_questions=_PRIORITY_QUESTIONS,
            medication_reconciliation=_MEDICATION_RECONCILIATION,
            labs_to_order=_LABS_TO_ORDER,
            screenings_to_discuss=_SCREENINGS_TO_DISCUSS,
            clinical_data_snapshot=snapshot,
            since_last_visit=_SINCE_LAST_VISIT,
        )

    # Generic packet for other appointments
    log.info("Generating generic prep packet for appointment %s", appointment_id)
    return VisitPrepPacket(
        appointment=apt,
        generated_at=generated_at,
        patient_summary=(
            "Chris is a 52-year-old male with T2DM, treatment-resistant HTN, "
            "statin myopathy, and post-sleeve gastrectomy (Dec 2019). "
            "Key active issues: A1c 7.3%, LDL 156, BP 140/90, K+ 5.4 history."
        ),
        priority_questions=[],
        medication_reconciliation=[],
        labs_to_order=[],
        screenings_to_discuss=[],
        clinical_data_snapshot=snapshot,
        since_last_visit=[],
    )


def get_clinical_data_snapshot() -> dict:
    """
    Return a snapshot of key clinical metrics for the current visit packet.

    Attempts to load values from chris_health_state.json. Falls back to
    known-good hardcoded values from the most recent records when the health
    state file is unavailable or a key is missing.

    Returns:
        dict: Flat dict of metric names to current values with units embedded.
    """
    state = _load_health_state()

    # Defaults from the patient context provided at module build time
    defaults: dict[str, Any] = {
        "A1c": "7.3% (May 2026)",
        "LDL": "156 mg/dL (2026) — no active therapy",
        "Blood_pressure": "140/90 mmHg",
        "eGFR": "87 mL/min/1.73m²",
        "K_plus": "4.5 mEq/L (current); prior 5.4 Mar 2025",
        "weight_lbs": 252,
        "BMI": 35.7,
        "HRV_ms": 45,
        "RHR_bpm": 58,
        "avg_daily_steps": 8400,
        "ASCVD_10yr_risk_pct": 15.2,
        "SpO2_overnight": "93%",
        "semaglutide_dose": "2 mg weekly",
        "metformin_dose": "500 mg ER daily",
        "post_bariatric_years": 6.5,
        "sleeve_gastrectomy_date": "2019-12-01",
    }

    # Attempt to pull live values from health state
    try:
        labs = state.get("labs_diagnostics", {})
        biometrics = state.get("biometrics", {})
        meds = state.get("current_care_state", {}).get("medications", [])

        if labs:
            for entry in labs if isinstance(labs, list) else []:
                name = entry.get("test", "")
                value = entry.get("value")
                if name == "HbA1c" and value:
                    defaults["A1c"] = f"{value}% (live)"
                elif name == "LDL" and value:
                    defaults["LDL"] = f"{value} mg/dL (live)"
                elif name in ("eGFR", "GFR") and value:
                    defaults["eGFR"] = f"{value} mL/min/1.73m² (live)"
                elif name in ("Potassium", "K+") and value:
                    defaults["K_plus"] = f"{value} mEq/L (live)"

        if biometrics:
            bw = biometrics.get("weight_lbs") or biometrics.get("weight")
            if bw:
                defaults["weight_lbs"] = bw
            bmi = biometrics.get("BMI") or biometrics.get("bmi")
            if bmi:
                defaults["BMI"] = bmi
            hrv = biometrics.get("HRV") or biometrics.get("hrv_ms")
            if hrv:
                defaults["HRV_ms"] = hrv
            rhr = biometrics.get("RHR") or biometrics.get("resting_hr")
            if rhr:
                defaults["RHR_bpm"] = rhr
    except Exception as exc:
        log.debug("Health state partial parse failed (non-fatal): %s", exc)

    return defaults


def record_appointment_outcome(appointment_id: str, outcome: AppointmentOutcome) -> dict:
    """
    Record the outcome of a completed visit.

    Appends a JSON line to ~/.jarvis/health/appointment_outcomes.jsonl and
    updates the ``outcomes`` field of the matching appointment in
    appointments.json.  Also triggers health state update via
    :func:`apply_appointment_outcomes_to_health_state`.

    Args:
        appointment_id: ID of the appointment that was completed.
        outcome: Populated :class:`AppointmentOutcome` dataclass.

    Returns:
        dict: Confirmation payload with keys ``status``, ``appointment_id``,
              ``recorded_at``, and ``health_state_update``.
    """
    _ensure_health_dir()

    # 1. Append to JSONL outcomes log
    outcome_dict = asdict(outcome)
    try:
        with _OUTCOMES_FILE.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(outcome_dict, default=str) + "\n")
        log.info("Outcome for %s appended to outcomes log", appointment_id)
    except OSError as exc:
        log.error("Failed to write outcome to JSONL: %s", exc)

    # 2. Update appointment in appointments.json
    raw_list = _load_appointments_raw()
    updated = False
    for raw in raw_list:
        if raw.get("id") == appointment_id:
            raw["outcomes"] = outcome_dict
            updated = True
            break
    if updated:
        _save_appointments_raw(raw_list)
        log.info("appointments.json updated with outcomes for %s", appointment_id)
    else:
        log.warning("appointment_id %s not found in appointments.json — outcomes not merged", appointment_id)

    # 3. Apply outcomes to health state
    health_update = apply_appointment_outcomes_to_health_state(outcome)

    return {
        "status": "recorded",
        "appointment_id": appointment_id,
        "recorded_at": outcome.recorded_at,
        "outcomes_file": str(_OUTCOMES_FILE),
        "appointments_updated": updated,
        "health_state_update": health_update,
    }


def apply_appointment_outcomes_to_health_state(outcome: AppointmentOutcome) -> dict:
    """
    Apply visit outcomes to chris_health_state.json.

    Processes each category of outcome:
    - Medication changes → update or append to medications list
    - New labs ordered → append to open_questions
    - Referrals → append to open_questions or care team
    - Follow-up date → append to open_questions

    Args:
        outcome: Completed :class:`AppointmentOutcome` instance.

    Returns:
        dict: Summary of changes applied, with keys ``medications_updated``,
              ``open_questions_added``, and ``errors``.
    """
    state = _load_health_state()
    errors: list[str] = []
    meds_updated: list[str] = []
    questions_added: list[str] = []

    # Medication changes
    try:
        current_meds: list[dict] = (
            state.get("current_care_state", {}).get("medications", [])
        )
        for change in outcome.medications_changed:
            med_name = change.get("med", "")
            change_type = change.get("change_type", "")
            new_dose = change.get("new_dose", "")
            matched = False
            for m in current_meds:
                if med_name.lower() in (m.get("name", "")).lower():
                    if change_type == "stopped":
                        m["status"] = "discontinued"
                        m["discontinued_date"] = outcome.recorded_at[:10]
                    elif change_type in ("dose_change", "new"):
                        if new_dose:
                            m["dose"] = new_dose
                    matched = True
                    meds_updated.append(f"{med_name}: {change_type}")
                    break
            if not matched and change_type == "new":
                current_meds.append({
                    "name": med_name,
                    "dose": new_dose,
                    "status": "active",
                    "started": outcome.recorded_at[:10],
                })
                meds_updated.append(f"NEW: {med_name} {new_dose}")
        if "current_care_state" not in state:
            state["current_care_state"] = {}
        state["current_care_state"]["medications"] = current_meds
    except Exception as exc:
        errors.append(f"medication update failed: {exc}")
        log.error("apply_appointment_outcomes_to_health_state — medication error: %s", exc)

    # Labs ordered → open_questions
    try:
        open_q: list[dict] = state.get("open_questions", [])
        for lab in outcome.labs_ordered:
            entry = {
                "question": f"Await result: {lab}",
                "source": f"Ordered at appointment {outcome.appointment_id}",
                "created": outcome.recorded_at[:10],
                "status": "pending",
            }
            open_q.append(entry)
            questions_added.append(f"Lab result pending: {lab}")
        state["open_questions"] = open_q
    except Exception as exc:
        errors.append(f"labs open_questions update failed: {exc}")
        log.error("apply_appointment_outcomes_to_health_state — labs error: %s", exc)

    # Referrals → open_questions
    try:
        open_q = state.get("open_questions", [])
        for referral in outcome.referrals_made:
            entry = {
                "question": f"Schedule and complete referral: {referral}",
                "source": f"Referral from appointment {outcome.appointment_id}",
                "created": outcome.recorded_at[:10],
                "status": "pending",
            }
            open_q.append(entry)
            questions_added.append(f"Referral: {referral}")
        state["open_questions"] = open_q
    except Exception as exc:
        errors.append(f"referrals open_questions update failed: {exc}")
        log.error("apply_appointment_outcomes_to_health_state — referrals error: %s", exc)

    # Follow-up date
    if outcome.follow_up_date:
        try:
            open_q = state.get("open_questions", [])
            open_q.append({
                "question": f"Schedule follow-up visit on or around {outcome.follow_up_date}",
                "source": f"Follow-up set at appointment {outcome.appointment_id}",
                "created": outcome.recorded_at[:10],
                "status": "pending",
            })
            state["open_questions"] = open_q
            questions_added.append(f"Follow-up date: {outcome.follow_up_date}")
        except Exception as exc:
            errors.append(f"follow-up date update failed: {exc}")

    # Persist
    if state:
        _save_health_state(state)

    return {
        "medications_updated": meds_updated,
        "open_questions_added": questions_added,
        "errors": errors,
    }


def get_upcoming_appointments(days_ahead: int = 30) -> list[dict]:
    """
    Return appointments scheduled within the next ``days_ahead`` days.

    Each returned dict is the appointment serialized with an added ``urgency``
    key:
    - ``"immediate"``  — within 7 days
    - ``"soon"``       — within 14 days
    - ``"upcoming"``   — within 30 days (or ``days_ahead``)

    Args:
        days_ahead: Look-ahead window in calendar days (default 30).

    Returns:
        list[dict]: Upcoming appointments sorted by date ascending, each
                    augmented with ``urgency`` and ``days_until`` keys.
    """
    appointments = get_appointments()
    today = date.today()
    cutoff = today + timedelta(days=days_ahead)
    upcoming: list[dict] = []

    for apt in appointments:
        try:
            apt_date = date.fromisoformat(apt.date)
        except ValueError:
            log.warning("Appointment %s has unparseable date '%s'", apt.id, apt.date)
            continue

        if today <= apt_date <= cutoff:
            days_until = (apt_date - today).days
            if days_until <= 7:
                urgency = "immediate"
            elif days_until <= 14:
                urgency = "soon"
            else:
                urgency = "upcoming"

            entry = asdict(apt)
            entry["urgency"] = urgency
            entry["days_until"] = days_until
            upcoming.append(entry)

    upcoming.sort(key=lambda x: x["date"])
    return upcoming


def format_visit_prep_as_text(packet: VisitPrepPacket) -> str:
    """
    Format a :class:`VisitPrepPacket` as a clean, print-ready plain-text document.

    Designed to be readable aloud, printed for the visit, or sent as a portal
    message.  Sections are separated by clear headers and horizontal rules.

    Args:
        packet: A populated :class:`VisitPrepPacket` instance.

    Returns:
        str: Formatted multi-section text document.
    """
    apt = packet.appointment
    lines: list[str] = []

    def hr(char: str = "=", width: int = 72) -> str:
        return char * width

    def section(title: str) -> None:
        lines.append("")
        lines.append(hr())
        lines.append(f"  {title.upper()}")
        lines.append(hr())

    # Header
    lines.append(hr("="))
    lines.append("  JARVIS VISIT PREP PACKET")
    lines.append(hr("="))
    lines.append(f"  Provider : {apt.provider}")
    lines.append(f"  Specialty: {apt.specialty}")
    lines.append(f"  Date     : {apt.date}  {apt.time}")
    lines.append(f"  Location : {apt.location}")
    lines.append(f"  Reason   : {apt.reason}")
    lines.append(f"  Generated: {packet.generated_at}")
    lines.append(hr("="))

    # Patient summary
    section("Patient Summary")
    lines.append(packet.patient_summary)

    # Clinical snapshot
    section("Clinical Data Snapshot")
    for key, value in packet.clinical_data_snapshot.items():
        label = key.replace("_", " ").title()
        lines.append(f"  {label:<30} {value}")

    # Priority questions
    section("Priority Questions (Ranked by Clinical Urgency)")
    for q in packet.priority_questions:
        urgency_tag = f"[{q.get('urgency', '')}]" if q.get("urgency") else ""
        lines.append("")
        lines.append(f"  #{q['rank']}  {q['question']}  {urgency_tag}")
        lines.append(hr("-", 72))
        lines.append(f"  Context : {q.get('clinical_context', '')}")
        lines.append(f"  Goal    : {q.get('desired_outcome', '')}")

    # Medication reconciliation
    section("Medication Reconciliation")
    for m in packet.medication_reconciliation:
        lines.append("")
        lines.append(f"  {m['med']}")
        lines.append(f"    Current        : {m.get('current', 'unknown')}")
        lines.append(f"    Proposed Change: {m.get('proposed_change', 'N/A')}")
        lines.append(f"    Rationale      : {m.get('rationale', '')}")

    # Labs to order
    section("Labs to Order")
    urgency_groups: dict[str, list[dict]] = {}
    for lab in packet.labs_to_order:
        urg = lab.get("urgency", "Routine")
        urgency_groups.setdefault(urg, []).append(lab)

    urgency_order = ["Immediate — safety", "High", "Overdue", "Routine — annual", "Routine"]
    remaining = set(urgency_groups.keys()) - set(urgency_order)
    for urg in urgency_order + sorted(remaining):
        if urg not in urgency_groups:
            continue
        lines.append(f"\n  [{urg}]")
        for lab in urgency_groups[urg]:
            lines.append(f"    - {lab['test']}")
            if lab.get("rationale"):
                lines.append(f"      {lab['rationale']}")

    # Screenings
    section("Screenings to Discuss")
    for s in packet.screenings_to_discuss:
        lines.append("")
        lines.append(f"  {s['screening']}")
        lines.append(f"    Status : {s.get('status', 'unknown')}")
        lines.append(f"    Action : {s.get('action', '')}")

    # Since last visit
    section("Notable Since Last Visit")
    for note in packet.since_last_visit:
        lines.append(f"  - {note}")

    # Footer
    lines.append("")
    lines.append(hr("="))
    lines.append("  End of Visit Prep Packet — JARVIS Appointment Intelligence")
    lines.append(hr("="))

    return "\n".join(lines)


def get_appointment_history() -> list[dict]:
    """
    Return all past appointments that have recorded outcomes.

    Merges data from both appointments.json (for appointment details) and
    appointment_outcomes.jsonl (for the full outcome log).  Past is defined
    as any appointment whose date is strictly before today.

    Returns:
        list[dict]: Past appointments with outcomes, sorted by date descending
                    (most recent first).  Each dict contains the full
                    appointment data plus an ``outcome_log`` key with the
                    matching JSONL records (list, may be empty).
    """
    today = date.today()
    appointments = get_appointments()

    # Load outcomes log indexed by appointment_id
    outcomes_by_id: dict[str, list[dict]] = {}
    if _OUTCOMES_FILE.exists():
        try:
            with _OUTCOMES_FILE.open("r", encoding="utf-8") as fh:
                for lineno, line in enumerate(fh, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                        aid = rec.get("appointment_id", "")
                        outcomes_by_id.setdefault(aid, []).append(rec)
                    except json.JSONDecodeError as exc:
                        log.warning("JSONL line %d malformed: %s", lineno, exc)
        except OSError as exc:
            log.error("Failed to read outcomes JSONL: %s", exc)

    history: list[dict] = []
    for apt in appointments:
        try:
            apt_date = date.fromisoformat(apt.date)
        except ValueError:
            continue
        if apt_date < today:
            entry = asdict(apt)
            entry["outcome_log"] = outcomes_by_id.get(apt.id, [])
            history.append(entry)

    history.sort(key=lambda x: x["date"], reverse=True)
    return history
