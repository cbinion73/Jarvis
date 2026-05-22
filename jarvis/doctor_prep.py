"""
JARVIS Doctor Prep Engine — Hermione Granger Protocol
Based on Helen Cho Master Binder v1.5, File 12: Doctor Prep Mode v0.8

Generates one-page visit briefs, portal messages, post-visit task lists,
and second-opinion packets.

Routes (add to service.py):
  POST /api/health/doctor-prep/brief        — generate one-page visit brief
  POST /api/health/doctor-prep/portal-msg   — generate portal message
  POST /api/health/doctor-prep/post-visit   — translate post-visit instructions
  GET  /api/health/doctor-prep/questions    — standing top questions for next visit
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime
from typing import Any

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Patient constants
# ---------------------------------------------------------------------------
_PATIENT_NAME = "Chris Binion"
_PATIENT_DOB = "1973-12-08"
_PATIENT_AGE = 52
_NEXT_VISIT_DATE = "2026-11-13"
_NEXT_VISIT_PROVIDER = "Dr. Susan Wenk"
_VISIT_TYPE_DEFAULT = "chronic_follow_up"

_VISIT_TYPES = {
    "acute_concern": "Acute Concern Visit",
    "chronic_follow_up": "Chronic Disease Follow-Up",
    "lab_follow_up": "Lab Results Follow-Up",
    "medication_follow_up": "Medication Review",
    "preventive": "Preventive / Annual Wellness",
    "specialist": "Specialist Consultation",
    "second_opinion": "Second Opinion",
}

# ---------------------------------------------------------------------------
# Standing priority questions — always current for this patient
# ---------------------------------------------------------------------------
_STANDING_PRIORITY_QUESTIONS: list[dict] = [
    {
        "rank": 1,
        "question": "LDL is 156 mg/dL and has risen 57 mg/dL over 5 years — has ezetimibe, bempedoic acid (Nexletol), or a PCSK9 inhibitor been considered? Statins are contraindicated due to documented statin myopathy.",
        "why_critical": "LDL 156 mg/dL in a patient with T2DM + hypertension is high cardiovascular risk. No LDL-lowering therapy is currently prescribed. ADA/ACC Level A guidance: LDL <100 mg/dL in high-risk T2DM.",
        "supporting_data": "LDL trend: 99 (2021) → 138 (2024) → 146 (Mar 2025) → 156 (May 2026). Statin myopathy documented — statins NEVER appropriate.",
        "urgency": "HIGH",
        "domain": "cardiology",
        "statin_warning": "NEVER suggest statins. Non-statin options: ezetimibe, bempedoic acid, PCSK9 inhibitors.",
    },
    {
        "rank": 2,
        "question": "A1c is 7.3% with a goal of <7.0%. Metformin ER is only 500 mg/day — why is this below the therapeutic range of 1000-2000 mg/day? Is ER formulation appropriate post-bariatric sleeve gastrectomy?",
        "why_critical": "A1c has relapsed from 5.9% (Apr 2024) to 7.3% (May 2026). Metformin ER appears subtherapeutic, and ER bioavailability is reduced post-bariatric surgery.",
        "supporting_data": "A1c: 5.9% (2024) → 7.3% (2026). Metformin ER 500 mg. Sleeve gastrectomy Dec 2019. Standard dose: 1000-2000 mg/day.",
        "urgency": "HIGH",
        "domain": "endocrinology",
    },
    {
        "rank": 3,
        "question": "Is spironolactone still clinically necessary? Potassium was 5.4 mmol/L in March 2025 on ARB + spironolactone — hyperkalemia risk. K⁺ is now 4.5 — is the benefit worth the risk?",
        "why_critical": "Olmesartan (ARB) + spironolactone is a high-risk hyperkalemia pair. K⁺ 5.4 documented. Now normalized to 4.5 — is spironolactone still the right call at current BP control?",
        "supporting_data": "K⁺: 5.4 mmol/L (Mar 2025) → 4.5 (May 2026). Currently on olmesartan/HCTZ + amlodipine + metoprolol + spironolactone.",
        "urgency": "MODERATE",
        "domain": "hypertension",
    },
    {
        "rank": 4,
        "question": "Colonoscopy — when is the next one due? Family history of polyps on record. Standard guidelines recommend 3-5 year interval after polyp removal.",
        "why_critical": "Colorectal cancer screening is a major longevity gap. Family history of polyps increases risk. Need to confirm last scope date and confirm next interval.",
        "supporting_data": "Family history of polyps. No colonoscopy date in current medical record.",
        "urgency": "MODERATE",
        "domain": "gastroenterology",
    },
    {
        "rank": 5,
        "question": "CPAP for OSA — OSA is diagnosed, but was CPAP ever formally prescribed, fitted, and is adherence currently being tracked?",
        "why_critical": "Untreated OSA worsens cardiovascular risk, blood pressure control, glucose metabolism, and cognitive function. All relevant to this patient's active conditions.",
        "supporting_data": "OSA diagnosed. CPAP not confirmed in records. BP uncontrolled (140/90, goal <130/80). A1c above goal.",
        "urgency": "MODERATE",
        "domain": "sleep_medicine",
    },
    {
        "rank": 6,
        "question": "Post-bariatric labs: when were ferritin, serum iron, TIBC, calcium, and PTH last checked? These are ASMBS Level A mandatory annual labs after sleeve gastrectomy.",
        "why_critical": "Post-bariatric patients have high risk of iron deficiency (ferritin), calcium malabsorption (hypocalcemia, secondary hyperparathyroidism), and B12 depletion. None of these are in the current lab record.",
        "supporting_data": "Sleeve gastrectomy Dec 2019 — 6.5 years ago. Ferritin, serum iron, TIBC, calcium, PTH not in current lab record. B12 363 pg/mL (lower-normal, metformin + post-bariatric risk).",
        "urgency": "MODERATE",
        "domain": "post_bariatric",
    },
]


# ---------------------------------------------------------------------------
# LLM helper
# ---------------------------------------------------------------------------

async def _llm_generate(system_prompt: str, user_prompt: str) -> str | None:
    """Call the LLM gateway. Returns text or None on failure."""
    try:
        from .llm_gateway import get_gateway, LLMMessage
    except ImportError:
        from llm_gateway import get_gateway, LLMMessage

    gw = get_gateway()
    if gw is None:
        log.warning("LLM gateway unavailable in doctor_prep")
        return None

    try:
        response = await asyncio.to_thread(
            gw.complete,
            messages=[LLMMessage("system", system_prompt), LLMMessage("user", user_prompt)],
            task_type="clinical",
            agent_id="hermione-granger",
            force_model="gpt-4o",
            temperature=0.3,
        )
        if response.error:
            log.warning("LLM error in doctor_prep: %s", response.error)
            return None
        raw = response.text.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        return raw
    except Exception as exc:
        log.error("LLM call failed in doctor_prep: %s", exc)
        return None


def _build_health_context() -> str:
    """Build a concise health context string for LLM prompts."""
    return f"""
PATIENT: {_PATIENT_NAME}, Male, Age {_PATIENT_AGE}, DOB {_PATIENT_DOB}
NEXT VISIT: {_NEXT_VISIT_DATE} with {_NEXT_VISIT_PROVIDER}

ACTIVE CONDITIONS:
- T2DM — A1c 7.3% (goal <7.0%) — off goal
- Hypertension — BP 140/90 (goal <130/80) — off goal
- OSA — CPAP status unknown
- CKD Stage G2 — eGFR 87, declining slowly
- Post-bariatric sleeve gastrectomy Dec 2019

MEDICATIONS (current):
- Semaglutide 2 mg/wk (GLP-1)
- Metformin ER 500 mg (subtherapeutic dose — concern)
- Olmesartan/HCTZ (ARB + diuretic)
- Amlodipine 10 mg (CCB)
- Metoprolol ER 50 mg (beta-blocker)
- Spironolactone 25 mg (K⁺-sparing diuretic — hyperkalemia risk pair with olmesartan)
- Citalopram 20 mg (SSRI)
- Multivitamin

CRITICAL SAFETY:
- STATIN MYOPATHY — NEVER recommend statins
- K⁺ was 5.4 (Mar 2025) on ARB + spironolactone — hyperkalemia alert pair

KEY LAB FINDINGS (May 2026):
- A1c 7.3% (goal <7.0%) — relapsed from 5.9% (Apr 2024)
- LDL 156 mg/dL RISING (99 in 2021, +57 over 5 years) — NO LDL therapy — CRITICAL GAP
- eGFR 87 (down from 98 in 2024) — slow decline
- K⁺ 4.5 (normalized from 5.4 — stable)
- Vitamin D 55.4 — adequate
- B12 363 — lower-normal, metformin + post-bariatric risk
- Ferritin/iron/PTH — NOT IN RECORD (overdue post-bariatric)

UPCOMING PRIORITY ACTIONS:
1. Initiate non-statin LDL therapy (ezetimibe first-line — low cost, generic)
2. Optimize metformin (500 mg → 1000-2000 mg, consider IR formulation post-bariatric)
3. Review spironolactone need given K⁺ history
4. Confirm colonoscopy schedule (family history of polyps)
5. Confirm CPAP prescription and adherence
6. Order post-bariatric labs: ferritin, iron, TIBC, calcium, PTH
""".strip()


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

async def generate_visit_brief(
    visit_type: str = "chronic_follow_up",
    main_concern: str = "",
    goals_for_visit: str = "",
) -> dict:
    """
    Generate a one-page visit brief using LLM with full health context.
    Visit types: acute_concern | chronic_follow_up | lab_follow_up |
                 medication_follow_up | preventive | specialist | second_opinion
    """
    visit_label = _VISIT_TYPES.get(visit_type, "Visit")
    health_context = _build_health_context()

    system_prompt = """You are Hermione Granger — JARVIS's Doctor Prep Specialist.
You generate concise, organized, clinically accurate one-page visit briefs for patients.

Rules:
- No statins — patient has documented statin myopathy
- Use clear sections: Purpose, Key Data, Priority Questions, Concerns
- Clinical but accessible language — patient will hand this to their doctor
- Be specific: include dates, exact values, exact drug names and doses
- Respond with valid JSON only"""

    user_prompt = f"""Generate a one-page visit brief for this upcoming appointment.

Visit type: {visit_label}
Main concern: {main_concern or 'Routine chronic disease management'}
Goals for visit: {goals_for_visit or 'Review A1c, BP, LDL; address medication gaps; confirm preventive care status'}

Health context:
{health_context}

Respond with JSON:
{{
  "visit_type": "{visit_label}",
  "visit_date": "{_NEXT_VISIT_DATE}",
  "provider": "{_NEXT_VISIT_PROVIDER}",
  "purpose": "...",
  "key_data_points": [{{"metric": "...", "value": "...", "goal": "...", "status": "..."}}],
  "priority_questions": ["...", "..."],
  "medications_to_discuss": ["...", "..."],
  "preventive_care_gaps": ["...", "..."],
  "labs_to_request": ["...", "..."],
  "formatted_brief": "Plain text version for printing"
}}"""

    raw = await _llm_generate(system_prompt, user_prompt)

    if raw:
        try:
            parsed = json.loads(raw)
            parsed["generated_at"] = datetime.utcnow().isoformat()
            parsed["binder_ref"] = "Master Binder v1.5 §12 — Doctor Prep Mode v0.8"
            return parsed
        except (json.JSONDecodeError, ValueError) as exc:
            log.warning("Could not parse LLM visit brief JSON: %s", exc)

    # Fallback structured brief — always clinically accurate
    return {
        "visit_type": visit_label,
        "visit_date": _NEXT_VISIT_DATE,
        "provider": _NEXT_VISIT_PROVIDER,
        "purpose": main_concern or "Chronic disease management: T2DM, hypertension, post-bariatric care",
        "key_data_points": [
            {"metric": "A1c", "value": "7.3%", "goal": "<7.0%", "status": "Above goal"},
            {"metric": "LDL", "value": "156 mg/dL", "goal": "<100 mg/dL", "status": "Critical gap — no therapy"},
            {"metric": "BP", "value": "140/90 mmHg", "goal": "<130/80 mmHg", "status": "Above goal"},
            {"metric": "eGFR", "value": "87 mL/min/1.73m²", "goal": ">60 (stable)", "status": "Slow decline — monitor"},
            {"metric": "K⁺", "value": "4.5 mmol/L", "goal": "<5.0 mmol/L", "status": "Normal — was 5.4 in 2025"},
        ],
        "priority_questions": [q["question"] for q in _STANDING_PRIORITY_QUESTIONS[:4]],
        "medications_to_discuss": [
            "LDL therapy — ezetimibe, bempedoic acid, or PCSK9 inhibitor (no statins)",
            "Metformin ER 500 mg — subtherapeutic dose; consider IR formulation post-bariatric",
            "Spironolactone — still needed given prior K⁺ 5.4?",
        ],
        "preventive_care_gaps": [
            "Colonoscopy — confirm schedule given family history of polyps",
            "CPAP — confirm prescription and adherence for diagnosed OSA",
        ],
        "labs_to_request": [
            "Ferritin, serum iron, TIBC (post-bariatric ASMBS Level A — overdue)",
            "PTH + calcium (secondary hyperparathyroidism screen post-bariatric)",
            "BMP (K⁺, creatinine monitoring — next quarterly check)",
        ],
        "formatted_brief": (
            f"VISIT BRIEF — {_NEXT_VISIT_DATE} with {_NEXT_VISIT_PROVIDER}\n"
            f"Patient: {_PATIENT_NAME}, {_PATIENT_AGE}M\n\n"
            f"TOP PRIORITIES:\n"
            f"1. LDL 156 mg/dL rising — no LDL therapy. Ezetimibe or non-statin option urgently needed.\n"
            f"   NOTE: Statin myopathy documented — statins are NEVER appropriate.\n"
            f"2. A1c 7.3% (goal <7.0%) — metformin ER 500 mg appears subtherapeutic.\n"
            f"3. Spironolactone still needed? Prior K⁺ 5.4 on ARB + spironolactone.\n"
            f"4. CPAP for OSA — has this been prescribed and tracked?\n"
            f"5. Post-bariatric labs overdue: ferritin, iron, PTH — 6+ years out from surgery.\n"
        ),
        "generated_at": datetime.utcnow().isoformat(),
        "binder_ref": "Master Binder v1.5 §12 — Doctor Prep Mode v0.8",
        "llm_used": False,
    }


async def generate_portal_message(
    subject: str,
    concern: str,
    relevant_data: str = "",
) -> dict:
    """
    Generate a concise portal message to Dr. Wenk.
    Rules: one issue, include dates/values, clear question, respectful tone.
    """
    health_context = _build_health_context()

    system_prompt = """You are Hermione Granger — JARVIS's Doctor Prep specialist.
Generate a professional, concise patient portal message.

Rules:
- One issue per message
- Include specific dates and lab values
- End with a clear, direct question
- Respectful, collaborative tone — not demanding
- Under 200 words
- No statins — patient has statin myopathy
- Respond with JSON only"""

    user_prompt = f"""Generate a portal message to {_NEXT_VISIT_PROVIDER} about:

Subject: {subject}
Concern: {concern}
Relevant data: {relevant_data or 'See health context'}

Health context (use relevant parts only):
{health_context}

Respond with JSON:
{{
  "to": "{_NEXT_VISIT_PROVIDER}",
  "subject": "...",
  "message_body": "...",
  "key_question": "...",
  "urgency": "routine | this_week | today",
  "estimated_word_count": 0
}}"""

    raw = await _llm_generate(system_prompt, user_prompt)

    if raw:
        try:
            parsed = json.loads(raw)
            parsed["generated_at"] = datetime.utcnow().isoformat()
            return parsed
        except (json.JSONDecodeError, ValueError):
            pass

    # Fallback message template
    return {
        "to": _NEXT_VISIT_PROVIDER,
        "subject": subject,
        "message_body": (
            f"Dear {_NEXT_VISIT_PROVIDER},\n\n"
            f"I am writing regarding: {concern}\n\n"
            f"{relevant_data}\n\n"
            "I would appreciate your guidance on next steps. "
            "My next scheduled visit is November 13, 2026, but I wanted to raise this proactively.\n\n"
            f"Thank you,\n{_PATIENT_NAME}"
        ),
        "key_question": concern,
        "urgency": "routine",
        "generated_at": datetime.utcnow().isoformat(),
        "llm_used": False,
    }


async def get_standing_priority_questions() -> list[dict]:
    """
    Return the standing list of top questions based on current health state.
    These are the questions that MUST be asked at the Nov 13, 2026 visit.
    """
    return _STANDING_PRIORITY_QUESTIONS


async def translate_post_visit(
    clinician_said: str,
    diagnosis: str = "",
    medications: str = "",
    tests_ordered: str = "",
    follow_up: str = "",
) -> dict:
    """
    Translate post-visit instructions into plain-English action items.
    Returns: {plain_english_summary, tasks[], questions_still_open[], warning_signs[], follow_up_date}
    """
    system_prompt = """You are Hermione Granger — JARVIS's Doctor Prep specialist.
Translate clinician post-visit notes into clear, actionable patient instructions.

Rules:
- Plain English — no jargon
- Numbered action list
- Include specific warning signs to watch for
- Flag any medication changes
- Never recommend statins (patient has statin myopathy)
- Respond with JSON only"""

    user_prompt = f"""Translate this post-visit information for patient {_PATIENT_NAME}:

What the clinician said: {clinician_said}
New/changed diagnosis: {diagnosis or 'None'}
Medication changes: {medications or 'None'}
Tests ordered: {tests_ordered or 'None'}
Follow-up instructions: {follow_up or 'None'}

Patient context: T2DM, hypertension, post-bariatric sleeve, statin myopathy (NEVER statins).

Respond with JSON:
{{
  "plain_english_summary": "...",
  "tasks": [
    {{"task": "...", "when": "...", "why": "..."}}
  ],
  "medication_changes": [{{"drug": "...", "change": "...", "instructions": "..."}}],
  "questions_still_open": ["..."],
  "warning_signs": [{{"sign": "...", "action": "..."}}],
  "follow_up_date": "...",
  "follow_up_provider": "..."
}}"""

    raw = await _llm_generate(system_prompt, user_prompt)

    if raw:
        try:
            parsed = json.loads(raw)
            parsed["generated_at"] = datetime.utcnow().isoformat()
            parsed["binder_ref"] = "Master Binder v1.5 §12 — Post-Visit Translation"
            return parsed
        except (json.JSONDecodeError, ValueError) as exc:
            log.warning("Could not parse post-visit translation: %s", exc)

    # Fallback: raw passthrough with basic structure
    return {
        "plain_english_summary": clinician_said,
        "tasks": [
            {"task": "Review the visit notes carefully", "when": "Today", "why": "LLM translation unavailable — review manually"},
            {"task": "Schedule any tests ordered", "when": "This week", "why": tests_ordered or "As directed"},
        ],
        "medication_changes": [{"drug": medications, "change": "As directed", "instructions": "Follow clinician instructions"}] if medications else [],
        "questions_still_open": ["Review with clinician at follow-up"],
        "warning_signs": [
            {"sign": "Symptoms worsen significantly", "action": "Call the office or go to urgent care"},
            {"sign": "K⁺ symptoms (weakness, palpitations) — on ARB + spironolactone", "action": "Call immediately"},
        ],
        "follow_up_date": follow_up or "As directed",
        "follow_up_provider": _NEXT_VISIT_PROVIDER,
        "generated_at": datetime.utcnow().isoformat(),
        "llm_used": False,
        "binder_ref": "Master Binder v1.5 §12 — Post-Visit Translation",
    }
