"""
JARVIS Medication Sentinel — Sherlock Holmes Protocol
Based on Helen Cho Master Binder v1.5, File 11: Medication Sentinel Mode v0.7

Medication sentinel builds a structured medication timeline, screens for
side effects, interactions, and duplicate therapy, and generates
pharmacist/prescriber questions.

Routes (add to service.py):
  POST /api/health/medication/sentinel   — full sentinel review
  GET  /api/health/medication/list       — current medication list from DB
  GET  /api/health/medication/safety     — quick safety check (interactions + flags)
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
# Patient constants — Chris Binion
# ---------------------------------------------------------------------------
_PATIENT_ID = "chris-binion"
_DOB = "1973-12-08"

# Medications excluded from analysis (inpatient/procedural/inactive)
_EXCLUDE_MED_KEYWORDS = (
    "PROPOFOL", "LIDOCAINE", "ONDANSETRON", "MEPERIDINE", "LABETALOL",
    "LACTATED RINGERS", "LACTATED RINGER", "SUTAB", "FENTANYL", "VERSED",
    "MIDAZOLAM", "DEXTROSE", "NORMAL SALINE", "MORPHINE", "HYDROMORPHONE",
)

# ---------------------------------------------------------------------------
# Known hardcoded interactions for Chris's regimen
# These are definite — do NOT rely on LLM for these.
# ---------------------------------------------------------------------------
_KNOWN_INTERACTIONS: list[dict] = [
    {
        "drugs": "Olmesartan (ARB) + Spironolactone (K⁺-sparing diuretic)",
        "drug_a": "olmesartan",
        "drug_b": "spironolactone",
        "mechanism": "Both agents raise serum potassium. ARB blocks aldosterone-mediated K⁺ excretion; spironolactone is a mineralocorticoid antagonist.",
        "severity": "Potentially serious",
        "evidence": "K⁺ 5.4 mmol/L documented Mar 2025 on this combination. Normalized to 4.5 May 2026 — monitoring successful.",
        "action": "Continue quarterly BMP monitoring. Alert threshold: K⁺ >5.0.",
        "binder_ref": "Sherlock Protocol §11.4 — Hyperkalemia Risk Pair",
    },
    {
        "drugs": "HCTZ + Semaglutide",
        "drug_a": "hctz",
        "drug_b": "semaglutide",
        "mechanism": "Thiazide diuretics can cause mild hyperglycemia by inhibiting pancreatic insulin secretion and increasing insulin resistance.",
        "severity": "Minor/possible",
        "evidence": "A1c 7.3% — partial worsening may be HCTZ contribution on top of T2DM.",
        "action": "Factor into A1c goal discussions. Consider whether HCTZ dose can be reduced as BP improves.",
        "binder_ref": "Sherlock Protocol §11.5",
    },
    {
        "drugs": "Metoprolol + Semaglutide",
        "drug_a": "metoprolol",
        "drug_b": "semaglutide",
        "mechanism": "Beta-blockers blunt the tachycardia that normally signals hypoglycemia. Patient may not feel early hypoglycemia warning signs.",
        "severity": "Minor/possible",
        "evidence": "Clinically relevant in T2DM with glucose-lowering therapy. Semaglutide alone has low hypoglycemia risk, but worth noting.",
        "action": "Patient should monitor for atypical hypoglycemia symptoms: sweating, confusion, fatigue without palpitations.",
        "binder_ref": "Sherlock Protocol §11.5",
    },
    {
        "drugs": "Metformin ER — Post-bariatric absorption concern",
        "drug_a": "metformin",
        "drug_b": "sleeve_gastrectomy",
        "mechanism": "Sleeve gastrectomy accelerates gastric emptying. Extended-release formulations rely on a prolonged gastric residence time that may be shortened post-bariatric.",
        "severity": "Moderate",
        "evidence": "Post-sleeve gastrectomy Dec 2019. ER forms of metformin have demonstrated reduced bioavailability in post-bariatric patients.",
        "action": "Clinician should consider switching Metformin ER → Metformin IR if A1c remains above goal. Also dose is only 500 mg — subtherapeutic for T2DM with A1c 7.3%.",
        "binder_ref": "Sherlock Protocol §11.6 — Post-Bariatric ER Formulation Risk",
    },
    {
        "drugs": "Metoprolol ER — Post-bariatric absorption concern",
        "drug_a": "metoprolol",
        "drug_b": "sleeve_gastrectomy",
        "mechanism": "Same mechanism as metformin ER — reduced gastric residence time may reduce ER absorption reliability.",
        "severity": "Moderate",
        "evidence": "Post-sleeve gastrectomy Dec 2019. BP goal not fully met (140/90, goal <130/80).",
        "action": "Clinician should assess whether metoprolol ER is providing adequate beta-blockade. May need IR formulation or dose adjustment.",
        "binder_ref": "Sherlock Protocol §11.6",
    },
    {
        "drugs": "Citalopram — QTc risk at high doses or with co-medications",
        "drug_a": "citalopram",
        "drug_b": "qtc_risk",
        "mechanism": "Citalopram dose-dependently prolongs QTc interval. At 20 mg alone: low risk. Risk increases >40 mg or with other QTc-prolonging agents.",
        "severity": "Minor/possible",
        "evidence": "Current dose 20 mg — below the threshold dose. No active QTc-prolonging co-medications identified.",
        "action": "Safe at current dose. Flag immediately if ciprofloxacin, azithromycin, haloperidol, or other QTc-prolonging agents are added.",
        "binder_ref": "Sherlock Protocol §11.7 — QTc Surveillance",
    },
]

# ---------------------------------------------------------------------------
# Duplicate therapy patterns
# ---------------------------------------------------------------------------
_DUPLICATE_THERAPY_PATTERNS: list[dict] = [
    {
        "pattern": "Complex multi-drug antihypertensive regimen",
        "drugs_involved": ["olmesartan", "hctz", "amlodipine", "metoprolol", "spironolactone"],
        "drug_count": 5,
        "severity": "Flag for review",
        "clinical_note": (
            "Five BP-lowering agents (ARB + thiazide + CCB + beta-blocker + aldosterone antagonist). "
            "This is a complex regimen appropriate for resistant hypertension, but each agent adds "
            "side effect and interaction burden. Spironolactone addition was likely for K⁺-sparing "
            "effect and anti-aldosterone benefit, but prior K⁺ 5.4 warrants ongoing justification."
        ),
        "question": "Is 5-drug antihypertensive therapy still needed, or can any agent be de-escalated as BP improves?",
    },
    {
        "pattern": "Dual glucose-lowering therapy",
        "drugs_involved": ["metformin", "semaglutide"],
        "drug_count": 2,
        "severity": "Expected — note only",
        "clinical_note": (
            "Metformin + semaglutide is a guideline-concordant combination for T2DM with "
            "cardiovascular risk. Expected and appropriate. However, metformin ER 500 mg is "
            "subtherapeutic for an A1c of 7.3% — typical therapeutic dose is 1000-2000 mg/day."
        ),
        "question": "Why is metformin ER at 500 mg when A1c is 7.3% and the therapeutic dose is up to 2000 mg/day?",
    },
    {
        "pattern": "Multiple potassium-affecting agents",
        "drugs_involved": ["olmesartan", "spironolactone", "hctz"],
        "drug_count": 3,
        "severity": "Potentially serious",
        "clinical_note": (
            "Olmesartan raises K⁺ (ARB effect); spironolactone raises K⁺ (K⁺-sparing diuretic); "
            "HCTZ lowers K⁺ (wasting diuretic). Net effect: variable, but prior K⁺ 5.4 shows "
            "the hyperkalemia direction dominated in Mar 2025. K⁺ now 4.5 — stable, but this "
            "triple-K⁺ interaction requires quarterly monitoring."
        ),
        "question": "Is spironolactone still clinically necessary given prior K⁺ 5.4 and current ARB therapy?",
    },
    {
        "pattern": "Serotonin pathway — single agent (safe)",
        "drugs_involved": ["citalopram"],
        "drug_count": 1,
        "severity": "No concern — monitor",
        "clinical_note": (
            "Citalopram 20 mg is the only serotonergic agent. No serotonin syndrome risk. "
            "Flag if tramadol, triptans, linezolid, or other serotonergic agents are added."
        ),
        "question": None,
    },
]


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

async def get_medication_list() -> list[dict]:
    """Pull current medications from health_db, clean duplicate/excluded entries."""
    try:
        from .health_db import _get_db
    except ImportError:
        from health_db import _get_db

    exclude_clauses = " AND ".join(
        f"UPPER(name) NOT LIKE '%{kw}%'" for kw in _EXCLUDE_MED_KEYWORDS
    )

    async with _get_db() as db:
        cur = await db.execute(
            f"SELECT id, name, generic_name, dosage, frequency, prescribed_date, "
            f"prescriber, pharmacy, quantity, day_supply, raw_text "
            f"FROM medications "
            f"WHERE {exclude_clauses} "
            f"AND (raw_text IS NULL OR raw_text NOT LIKE '%(inactive)%') "
            f"ORDER BY name"
        )
        rows = [dict(r) for r in await cur.fetchall()]

    # Deduplicate by normalized name (keep first occurrence)
    seen: set[str] = set()
    deduped: list[dict] = []
    for r in rows:
        key = re.sub(r"\s+", " ", (r.get("name") or "").upper().strip())
        if key and key not in seen:
            seen.add(key)
            deduped.append(r)

    return deduped


async def check_duplicate_therapy(meds: list[dict]) -> list[dict]:
    """
    Check for duplicate therapy patterns.
    Returns list of concerns with severity.
    """
    med_names_lower = " ".join(
        ((m.get("name") or "") + " " + (m.get("generic_name") or "")).lower()
        for m in meds
    )

    concerns: list[dict] = []
    for pattern in _DUPLICATE_THERAPY_PATTERNS:
        matched = [
            d for d in pattern["drugs_involved"]
            if d.lower() in med_names_lower
        ]
        if len(matched) >= 2 or (len(pattern["drugs_involved"]) == 1 and len(matched) == 1):
            concern = {
                "pattern": pattern["pattern"],
                "drugs_matched": matched,
                "severity": pattern["severity"],
                "clinical_note": pattern["clinical_note"],
            }
            if pattern.get("question"):
                concern["question"] = pattern["question"]
            concerns.append(concern)

    return concerns


async def check_interactions(meds: list[dict]) -> list[dict]:
    """
    Check known clinically significant interactions for this patient's regimen.
    Hardcoded — does not rely on LLM.
    Returns list of interactions with severity labels from binder:
    "Potentially serious | Moderate | Minor/possible | Unknown"
    """
    med_names_lower = " ".join(
        ((m.get("name") or "") + " " + (m.get("generic_name") or "")).lower()
        for m in meds
    )

    # Treat post-bariatric as always present for this patient
    med_names_lower += " sleeve_gastrectomy"

    found: list[dict] = []
    for ix in _KNOWN_INTERACTIONS:
        a = ix["drug_a"].lower()
        b = ix["drug_b"].lower()
        if a in med_names_lower and b in med_names_lower:
            found.append({k: v for k, v in ix.items() if k not in ("drug_a", "drug_b")})

    return found


async def build_medication_timeline(recent_changes: str = "") -> dict:
    """
    Build Sherlock's timeline structure.
    Confidence labels: Strong temporal association | Moderate | Weak | Unclear | Unlikely
    """
    # Static timeline for Chris — reflects known medication history
    timeline = {
        "what_changed": recent_changes or "No recent changes reported",
        "when_changed": "Unknown — no change date provided",
        "known_history": [
            {
                "date": "2019-12",
                "event": "Bariatric sleeve gastrectomy",
                "medication_impact": "All oral extended-release formulations now have altered absorption kinetics",
            },
            {
                "date": "2019",
                "event": "A1c 10.2% — initiated intensive diabetes management",
                "medication_impact": "Metformin initiated; semaglutide added later as A1c improved then relapsed",
            },
            {
                "date": "2024-04",
                "event": "A1c 5.9% — best recorded",
                "medication_impact": "GLP-1 and metformin working; semaglutide likely titrated up",
            },
            {
                "date": "2025-03",
                "event": "K⁺ 5.4 mmol/L — hyperkalemia",
                "medication_impact": "Olmesartan + spironolactone combination confirmed hyperkalemic. Monitoring adjusted.",
            },
            {
                "date": "2026-05",
                "event": "A1c 7.3%, K⁺ 4.5, LDL 156 — current state",
                "medication_impact": "A1c relapsed off peak. LDL rising with no LDL-lowering therapy. K⁺ normalized.",
            },
        ],
        "symptoms_before_after": "Not reported",
        "temporal_association": "Historical reconstruction — no acute medication change to evaluate",
        "confidence_label": "Moderate",
        "sherlock_note": (
            "The most important unresolved medication gap: LDL 156 mg/dL and rising with NO "
            "LDL-lowering therapy. Statin myopathy precludes statins. Non-statin options "
            "(ezetimibe, bempedoic acid, PCSK9 inhibitor) have not been initiated."
        ),
    }

    return timeline


async def generate_pharmacist_questions(
    meds: list[dict],
    interactions: list[dict],
    concerns: str = "",
) -> list[str]:
    """Generate top pharmacist/prescriber questions using LLM. 5-7 questions."""
    try:
        from .llm_gateway import get_gateway, LLMMessage
    except ImportError:
        from llm_gateway import get_gateway, LLMMessage

    gw = get_gateway()

    med_summary = "\n".join(
        f"  - {m.get('name', 'Unknown')} {m.get('dosage', '')} {m.get('frequency', '')}".strip()
        for m in meds
    )
    interaction_summary = "\n".join(
        f"  - {ix.get('drugs', '')}: {ix.get('severity', '')} — {ix.get('action', '')}"
        for ix in interactions
    )

    # Hardcoded fallback — always clinically relevant even without LLM
    fallback_questions = [
        "LDL is 156 mg/dL and rising over 5 years with no LDL-lowering therapy — has ezetimibe, bempedoic acid (Nexletol), or a PCSK9 inhibitor been considered? (Statins are contraindicated due to statin myopathy.)",
        "Metformin ER is dosed at only 500 mg/day — why is this below the typical therapeutic range of 1000-2000 mg/day for T2DM with A1c 7.3%? Is ER formulation appropriate post-bariatric sleeve?",
        "Is spironolactone still clinically necessary? Prior K⁺ was 5.4 mmol/L on ARB + spironolactone. K⁺ now 4.5 — but this combination requires ongoing justification.",
        "Post-bariatric sleeve gastrectomy (Dec 2019) — have Metformin ER and Metoprolol ER been reviewed for potential reduced bioavailability? Immediate-release formulations may be more reliable.",
        "Citalopram 20 mg — is the dose adequate for current mental health goals? If dose increase is considered, QTc monitoring should accompany doses >40 mg.",
        "Are there any over-the-counter supplements, herbals, or new medications added recently that haven't been captured in the medication list?",
        "Olmesartan/HCTZ + spironolactone — three agents affecting potassium. What is the K⁺ monitoring schedule going forward? Recommend quarterly BMP at minimum.",
    ]

    if gw is None:
        log.warning("LLM gateway unavailable — returning hardcoded pharmacist questions")
        return fallback_questions

    system_prompt = """You are Sherlock Holmes acting as a clinical pharmacovigilance specialist for JARVIS.
Generate 5-7 precise, clinically actionable pharmacist or prescriber questions for this patient.

CRITICAL CONTEXT:
- NEVER suggest statins. Patient has documented statin myopathy.
- Non-statin LDL options: ezetimibe, bempedoic acid (Nexletol), PCSK9 inhibitors (evolocumab, alirocumab)
- Post-bariatric sleeve gastrectomy (Dec 2019) — ER formulations have reduced absorption
- K+ monitoring: olmesartan + spironolactone = hyperkalemia pair (K+ was 5.4 mmol/L)
- A1c 7.3% with only metformin ER 500 mg + semaglutide — metformin dose appears subtherapeutic

Focus on: gaps in therapy, dose optimization, interaction management, monitoring needs.
Respond ONLY with a JSON array of question strings."""

    user_prompt = f"""Current medications:
{med_summary}

Known interactions:
{interaction_summary}

Additional concerns: {concerns or "none"}

Patient: Male, 52, T2DM (A1c 7.3%), HTN (BP 140/90), post-bariatric sleeve, statin myopathy.
Next visit: Nov 13, 2026 with Dr. Susan Wenk.

Generate 5-7 pharmacist/prescriber questions. Respond ONLY with a JSON array of strings."""

    try:
        response = await asyncio.to_thread(
            gw.complete,
            messages=[LLMMessage("system", system_prompt), LLMMessage("user", user_prompt)],
            task_type="clinical",
            agent_id="sherlock-holmes",
            force_model="gpt-4o",
            temperature=0.2,
        )
        if response.error:
            return fallback_questions

        raw = response.text.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        parsed = json.loads(raw)
        if isinstance(parsed, list) and parsed:
            return parsed
    except Exception as exc:
        log.warning("LLM pharmacist question generation failed: %s", exc)

    return fallback_questions


async def run_sentinel_review(
    new_medications: list[str] | None = None,
    stopped_medications: list[str] | None = None,
    reported_symptoms: str = "",
    context: str = "",
) -> dict:
    """
    Full sentinel review. Returns MedicationStateUpdateObject matching binder schema.
    """
    new_medications = new_medications or []
    stopped_medications = stopped_medications or []

    meds = await get_medication_list()
    interactions = await check_interactions(meds)
    duplicates = await check_duplicate_therapy(meds)
    timeline = await build_medication_timeline(
        recent_changes=f"Added: {new_medications}; Stopped: {stopped_medications}" if (new_medications or stopped_medications) else ""
    )
    questions = await generate_pharmacist_questions(meds, interactions, context)

    # Determine oracle risk level
    serious = [i for i in interactions if i.get("severity") == "Potentially serious"]
    moderate = [i for i in interactions if i.get("severity") == "Moderate"]

    if serious:
        oracle_risk = "O-MONITOR"
        risk_rationale = f"{len(serious)} potentially serious interaction(s) — all currently monitored and stable."
    elif moderate:
        oracle_risk = "O-CLINIC"
        risk_rationale = f"{len(moderate)} moderate concern(s) requiring clinician discussion at next visit."
    else:
        oracle_risk = "O-CLEAR"
        risk_rationale = "No acute safety concerns identified."

    # Supplement concerns (post-bariatric)
    supplement_concerns = [
        "Post-bariatric: fat-soluble vitamin absorption (A, D, E, K) may be reduced — verify vitamin D is adequate (current 55.4 — adequate).",
        "B12 363 pg/mL — lower end of normal; metformin reduces B12 absorption. Monitor annually.",
        "Multivitamin only — post-bariatric patients typically need higher-dose B12, iron, calcium with D. Confirm formulation is bariatric-specific.",
        "Iron/ferritin not recently checked — post-sleeve gastrectomy iron deficiency risk is significant.",
    ]

    prescriber_questions = [
        "LDL 156 mg/dL rising — non-statin therapy (ezetimibe, bempedoic acid, PCSK9 inhibitor) should be initiated given T2DM + cardiovascular risk.",
        "Metformin ER 500 mg appears subtherapeutic for A1c 7.3% — dose escalation or switch to IR post-bariatric?",
        "Is spironolactone still indicated? K+ was 5.4 in March 2025. If BP remains controlled on 4 agents, consider de-escalation.",
        "CPAP for OSA — has this been formally prescribed and is adherence being tracked?",
    ]

    return {
        "date_reviewed": datetime.utcnow().isoformat(),
        "medication_list_verified": [
            f"{m.get('name', 'Unknown')} {m.get('dosage', '')} {m.get('frequency', '')}".strip()
            for m in meds
        ],
        "medication_count": len(meds),
        "new_medications": new_medications,
        "stopped_medications": stopped_medications,
        "dose_or_timing_changes": [],
        "adherence_issues": [],
        "reported_side_effects": [reported_symptoms] if reported_symptoms else [],
        "possible_interactions_to_verify": interactions,
        "interaction_count": len(interactions),
        "duplicate_therapy_concerns": duplicates,
        "supplement_concerns": supplement_concerns,
        "oracle_risk_level": oracle_risk,
        "oracle_risk_rationale": risk_rationale,
        "pharmacist_questions": questions,
        "prescriber_questions": prescriber_questions,
        "medication_timeline": timeline,
        "recommended_follow_up": [
            "Quarterly BMP (K⁺, creatinine) — next due ~Aug 2026",
            "Discuss non-statin LDL therapy with Dr. Wenk at Nov 13 visit",
            "Confirm metformin dose adequacy and ER vs IR formulation post-bariatric",
            "Review spironolactone continued need given K⁺ history",
        ],
        "agents_consulted": ["sherlock-holmes", "the-oracle"],
        "confidence": "high",
        "status": "complete",
        "binder_ref": "Master Binder v1.5 §11 — Medication Sentinel Mode v0.7",
    }
