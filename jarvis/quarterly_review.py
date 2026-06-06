"""
JARVIS Quarterly Longevity Council Review — Full Board Meeting
Based on Helen Cho Master Binder v1.5, File 13: Quarterly Longevity Council Engine v0.9

The health board meeting: review 90 days, identify improvements and worsening,
set next 90-day objectives, generate doctor discussion packet.

Routes:
  POST /api/health/quarterly/review       — run full quarterly review (LLM-intensive)
  GET  /api/health/quarterly/objectives   — current 90-day objectives
  POST /api/health/quarterly/objectives   — set new 90-day objectives
  GET  /api/health/quarterly/doctor-packet — quarterly doctor discussion packet
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .persistence import append_jsonl, atomic_write_json

log = logging.getLogger(__name__)

_OBJECTIVES_PATH = Path.home() / ".jarvis" / "health" / "quarterly_objectives.json"
_OBJECTIVES_LOG_PATH = _OBJECTIVES_PATH.with_name("quarterly_objectives_log.jsonl")
_OBJECTIVES_STATE_LOG_PATH = _OBJECTIVES_PATH.with_name("quarterly_objectives_state_log.jsonl")
_OBJECTIVES_PATH.parent.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Pre-loaded data for first quarterly review — from known clinical history
# ---------------------------------------------------------------------------

_KNOWN_IMPROVEMENTS = [
    "Urine albumin improved: 25.7 mg/L (2023) → <12 mg/L (2026) — ARB therapy protecting kidneys",
    "Potassium normalized: 5.4 mmol/L (Mar 2025) → 4.5 mmol/L (May 2026)",
    "Vitamin D now adequate: 55.4 ng/mL (was deficient pre-op)",
    "Liver enzymes normal: ALT 29, AST 31 (May 2026)",
    "Steps averaging 8,432/day — solid baseline activity",
    "Sleep averaging 7.5h — adequate duration",
    "Diabetic retinopathy: none detected (Apr 2025)",
    "PSA: 0.65 ng/mL — normal",
]

_KNOWN_WORSENING = [
    "LDL: 99 (2021) → 156 mg/dL (2026) — worsening every year, NO treatment in place",
    "A1c: relapsed from 5.9% (Apr 2024) → 7.3% (May 2026) — stalled above goal",
    "eGFR: drifting 98 (2024) → 87 (May 2026) — slow kidney function decline",
    "BMI: 35.7 — post-bariatric goal of <30 not achieved",
    "BP: 140/90 — at clinician threshold, not at ADA target of <130/80",
    "OSA: diagnosed but CPAP never confirmed — cardiovascular risk unaddressed",
]

_KNOWN_RISKS = [
    {"risk": "ASCVD — LDL 156 with no therapy, T2DM, HTN, male, 52", "urgency": "critical"},
    {"risk": "A1c stalled 7.3% — diabetes complications accumulating silently", "urgency": "high"},
    {"risk": "OSA untreated — worsening BP, glucose, HRV, cardiac risk", "urgency": "high"},
    {"risk": "eGFR slow decline — K+ history adds risk with current regimen", "urgency": "moderate"},
    {"risk": "Post-bariatric micronutrient surveillance lapsed (ferritin, Ca, PTH)", "urgency": "moderate"},
]

_KNOWN_OPPORTUNITIES = [
    "Non-statin LDL therapy (ezetimibe, bempedoic acid) — never tried, massive CV risk reduction potential",
    "CPAP evaluation and initiation — would improve BP, A1c, HRV, energy",
    "Metformin ER 500mg → IR + dose increase — may improve A1c substantially",
    "Post-meal walking habit — could lower A1c 0.3-0.5% with high consistency",
    "Colonoscopy — family hx polyps; overdue; early detection = curative",
    "CGM data (Dexcom G7 once live) — real-time glucose feedback for dietary decisions",
]

_REQUIRED_OBJECTIVE_FIELDS = [
    "objective", "domain", "why_it_matters", "baseline", "target",
    "weekly_actions", "measurement_plan",
]

_COUNCIL_MEMBERS_QUARTERLY = [
    "the-oracle", "helen-cho", "cristina-yang", "gregory-house",
    "sherlock-holmes", "data", "poison-ivy", "dr-mccoy",
    "morpheus", "thor-fitness", "yoda", "deanna-troi", "alfred",
]


# ---------------------------------------------------------------------------
# Context assembly
# ---------------------------------------------------------------------------

async def build_quarterly_context() -> str:
    """
    Assemble the quarterly review context from all available data sources.
    """
    sections: list[str] = []

    # 1. Health state summary
    try:
        try:
            from .longevity_council import health_state_summary
        except ImportError:
            from longevity_council import health_state_summary
        summary = health_state_summary()
        if summary:
            sections.append(summary)
    except Exception as exc:
        log.warning("Could not load health state summary: %s", exc)

    # 2. Wearable summary (last 30 days)
    try:
        try:
            from .health_db import get_latest_metrics
        except ImportError:
            from health_db import get_latest_metrics

        rows = await get_latest_metrics(days=30)
        if rows:
            valid_steps = [r["steps"] for r in rows if r.get("steps")]
            valid_rhr = [r["resting_hr"] for r in rows if r.get("resting_hr")]
            valid_hrv = [r["hrv"] for r in rows if r.get("hrv")]
            valid_sleep = [r["sleep_hours"] for r in rows if r.get("sleep_hours")]

            wearable_lines = ["=== WEARABLE SUMMARY (30 days) ==="]
            if valid_steps:
                wearable_lines.append(f"Steps avg: {sum(valid_steps)/len(valid_steps):.0f}/day | Latest: {valid_steps[0]}")
            if valid_rhr:
                wearable_lines.append(f"Resting HR avg: {sum(valid_rhr)/len(valid_rhr):.1f} bpm | Latest: {valid_rhr[0]:.1f}")
            if valid_hrv:
                wearable_lines.append(f"HRV avg: {sum(valid_hrv)/len(valid_hrv):.1f} ms | Latest: {valid_hrv[0]:.1f}")
            if valid_sleep:
                wearable_lines.append(f"Sleep avg: {sum(valid_sleep)/len(valid_sleep):.1f}h | Latest: {valid_sleep[0]:.1f}h")
            wearable_lines.append(f"Days with data: {len(rows)}")
            sections.append("\n".join(wearable_lines))
    except Exception as exc:
        log.warning("Could not load wearable summary: %s", exc)

    # 3. Lab review
    try:
        try:
            from .lab_review import run_full_lab_review, get_trending_labs
        except ImportError:
            from lab_review import run_full_lab_review, get_trending_labs

        trending = await get_trending_labs()
        if trending:
            trend_lines = ["=== TRENDING LABS ==="]
            for t in trending[:8]:
                trend_lines.append(f"  {t.get('test_name', 'Unknown')}: {t.get('trend', 'no trend data')}")
            sections.append("\n".join(trend_lines))
    except Exception as exc:
        log.warning("Could not load lab trends: %s", exc)

    # 4. Medication context
    try:
        try:
            from .medication_sentinel import get_medication_list
        except ImportError:
            from medication_sentinel import get_medication_list

        meds = await get_medication_list()
        if meds:
            med_lines = ["=== CURRENT MEDICATIONS ==="]
            for m in meds[:10]:
                med_lines.append(f"  {m.get('name', 'Unknown')} {m.get('dosage', '')} — {m.get('frequency', '')}")
            sections.append("\n".join(med_lines))
    except Exception as exc:
        log.warning("Could not load medication list: %s", exc)

    # 5. Pre-loaded known clinical history (first review baseline)
    sections.append("=== KNOWN CLINICAL TRAJECTORY (Pre-loaded) ===")
    sections.append("IMPROVEMENTS:")
    for item in _KNOWN_IMPROVEMENTS:
        sections.append(f"  + {item}")
    sections.append("WORSENING TRENDS:")
    for item in _KNOWN_WORSENING:
        sections.append(f"  - {item}")
    sections.append("KNOWN RISKS:")
    for r in _KNOWN_RISKS:
        sections.append(f"  [{r['urgency'].upper()}] {r['risk']}")
    sections.append("KNOWN OPPORTUNITIES:")
    for o in _KNOWN_OPPORTUNITIES:
        sections.append(f"  * {o}")

    # 6. Active goals
    try:
        objectives = await get_current_objectives()
        if objectives:
            obj_lines = [f"=== ACTIVE 90-DAY OBJECTIVES ({len(objectives)}) ==="]
            for obj in objectives:
                obj_lines.append(f"  - {obj.get('objective', 'Unknown')} | Domain: {obj.get('domain')} | Target: {obj.get('target')}")
            sections.append("\n".join(obj_lines))
    except Exception as exc:
        log.warning("Could not load objectives: %s", exc)

    return "\n\n".join(sections)


# ---------------------------------------------------------------------------
# Quarterly review engine
# ---------------------------------------------------------------------------

async def run_quarterly_review(
    review_period_days: int = 90,
    major_life_context: str = "",
    additional_context: str = "",
) -> dict:
    """
    Full quarterly review via LLM using the full council context.
    Returns structured quarterly report matching binder schema (§13.11).
    """
    review_end = datetime.utcnow()
    review_start = review_end - timedelta(days=review_period_days)

    context = await build_quarterly_context()

    life_ctx = f"\nMAJOR LIFE CONTEXT THIS PERIOD: {major_life_context}" if major_life_context else ""
    add_ctx = f"\nADDITIONAL CONTEXT: {additional_context}" if additional_context else ""

    full_prompt = f"""You are the JARVIS Longevity Council running the Full Board Quarterly Review for Chris Binion.

PATIENT: Chris Binion | Male, 52 | T2DM | Hypertension | Post-bariatric (Dec 2019)
SAFETY: NO STATINS EVER (statin myopathy). K+ monitoring critical. Upcoming appointment: Dr. Wenk Nov 13 2026.
REVIEW PERIOD: {review_start.strftime('%Y-%m-%d')} to {review_end.strftime('%Y-%m-%d')} ({review_period_days} days)
{life_ctx}{add_ctx}

FULL HEALTH DATA PACKAGE:
{context}

COUNCIL INSTRUCTIONS:
1. The Oracle runs first — identify any immediate safety flags
2. Review data quality: what is present, what is missing
3. Classify: what improved, what worsened, what stayed stable
4. Identify top 3 risks (with urgency) and top 3 opportunities (with expected impact)
5. Propose up to 3 new 90-day objectives — each must be specific, measurable, achievable
6. Generate 3-5 discussion items for the Nov 13 visit with Dr. Wenk
7. Generate 3-5 operations tasks for Alfred (logistics, scheduling, labs to order)
8. State ONE next action (most important thing Chris should do in the next 7 days)

Respond ONLY with valid JSON matching this exact schema:
{{
  "review_period_start": "{review_start.strftime('%Y-%m-%d')}",
  "review_period_end": "{review_end.strftime('%Y-%m-%d')}",
  "baseline_completeness_score": "<0-100 score of how complete the available data is>",
  "oracle_safety_flags": [],
  "improvements": [],
  "worsening_trends": [],
  "stable_areas": [],
  "top_risks": [
    {{"risk": "<description>", "urgency": "<critical|high|moderate|low>", "rationale": "<why>"}}
  ],
  "top_opportunities": [
    {{"opportunity": "<description>", "expected_impact": "<what would improve>", "feasibility": "<high|moderate|low>"}}
  ],
  "completed_goals": [],
  "modified_goals": [],
  "new_90_day_objectives": [
    {{
      "objective": "<specific goal>",
      "domain": "<metabolic|cardiovascular|sleep|fitness|mental|preventive>",
      "why_it_matters": "<clinical rationale>",
      "baseline": "<current value>",
      "target": "<specific target>",
      "weekly_actions": ["<action 1>", "<action 2>"],
      "measurement_plan": "<how to measure progress>"
    }}
  ],
  "doctor_discussion_items": [
    {{"topic": "<topic>", "data": "<supporting data>", "ask": "<specific question or request>"}}
  ],
  "operations_tasks": [
    {{"task": "<task>", "owner": "alfred", "deadline": "<timeframe>", "category": "<lab|scheduling|device|medication|preventive>"}}
  ],
  "agents_consulted": {json.dumps(_COUNCIL_MEMBERS_QUARTERLY)},
  "confidence": "<high|moderate|low>",
  "status": "active",
  "one_next_action": "<single most important action in next 7 days>"
}}"""

    try:
        try:
            from .llm_gateway import get_gateway, LLMMessage
        except ImportError:
            from llm_gateway import get_gateway, LLMMessage

        gw = get_gateway()
        if gw is None:
            raise RuntimeError("LLM gateway unavailable")

        response = await asyncio.to_thread(
            gw.complete,
            messages=[
                LLMMessage("system", "You are the JARVIS Longevity Council. Respond ONLY with valid JSON."),
                LLMMessage("user", full_prompt),
            ],
            task_type="critical",
            agent_id="quarterly-review",
            force_model="gpt-4o",
            max_tokens=4000,
            temperature=0.3,
        )

        if response.error:
            raise RuntimeError(f"LLM error: {response.error}")

        raw = response.text.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        report = json.loads(raw)

    except Exception as exc:
        log.error("Quarterly review LLM call failed: %s", exc)
        # Return structured fallback with pre-loaded data
        report = {
            "review_period_start": review_start.strftime("%Y-%m-%d"),
            "review_period_end": review_end.strftime("%Y-%m-%d"),
            "baseline_completeness_score": 65,
            "oracle_safety_flags": ["LDL 156 mg/dL with no treatment — ASCVD risk accumulating"],
            "improvements": _KNOWN_IMPROVEMENTS,
            "worsening_trends": _KNOWN_WORSENING,
            "stable_areas": ["Kidney protection (albumin normalized)", "Liver function normal", "PSA normal"],
            "top_risks": _KNOWN_RISKS,
            "top_opportunities": [{"opportunity": o, "expected_impact": "significant", "feasibility": "high"} for o in _KNOWN_OPPORTUNITIES[:3]],
            "completed_goals": [],
            "modified_goals": [],
            "new_90_day_objectives": [],
            "doctor_discussion_items": [
                {"topic": "Non-statin LDL therapy", "data": "LDL 156 mg/dL, rising trend since 2021", "ask": "Begin ezetimibe or bempedoic acid"},
                {"topic": "CPAP evaluation", "data": "OSA diagnosed, CPAP not confirmed initiated", "ask": "Order titration study or confirm CPAP use"},
                {"topic": "A1c optimization", "data": "A1c 7.3%, up from 5.9% in 2024", "ask": "Consider metformin dose increase or GLP-1 adjustment"},
            ],
            "operations_tasks": [
                {"task": "Order BMP panel (K+, eGFR, creatinine)", "owner": "alfred", "deadline": "before Nov 13 visit", "category": "lab"},
                {"task": "Schedule colonoscopy", "owner": "alfred", "deadline": "Q3 2026", "category": "preventive"},
            ],
            "agents_consulted": _COUNCIL_MEMBERS_QUARTERLY,
            "confidence": "low",
            "status": "active",
            "one_next_action": "Discuss non-statin LDL treatment with Dr. Wenk at Nov 13 visit — this is the highest-impact unaddressed risk.",
            "llm_error": str(exc),
        }

    # Log to council decision log
    try:
        try:
            from .longevity_council import append_council_decision
        except ImportError:
            from longevity_council import append_council_decision
        await append_council_decision({
            "type": "quarterly_review",
            "review_period_start": report.get("review_period_start"),
            "review_period_end": report.get("review_period_end"),
            "confidence": report.get("confidence"),
            "one_next_action": report.get("one_next_action"),
        })
    except Exception as exc:
        log.warning("Could not append quarterly review to decision log: %s", exc)

    return report


# ---------------------------------------------------------------------------
# Objectives management
# ---------------------------------------------------------------------------

async def get_current_objectives() -> list[dict]:
    """
    Return current 90-day objectives from saved file or health_state active_goals.
    """
    # Check saved objectives file first
    if _OBJECTIVES_PATH.exists():
        try:
            data = json.loads(_OBJECTIVES_PATH.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and "objectives" in data:
                return data["objectives"]
        except Exception as exc:
            log.warning("Could not load objectives file: %s", exc)
            replayed = _load_objectives_from_state_log() or _load_objectives_from_log()
            if replayed:
                return replayed
    else:
        replayed = _load_objectives_from_state_log() or _load_objectives_from_log()
        if replayed:
            return replayed

    # Fall back to health_state active_goals
    try:
        try:
            from .longevity_council import load_health_state
        except ImportError:
            from longevity_council import load_health_state

        state = load_health_state()
        goals = state.get("active_goals", [])
        if goals:
            return goals
    except Exception as exc:
        log.warning("Could not load health state goals: %s", exc)

    return []


async def set_objectives(objectives: list[dict]) -> dict:
    """
    Save new 90-day objectives to ~/.jarvis/health/quarterly_objectives.json.
    Validates required fields on each objective.
    """
    errors = []
    for i, obj in enumerate(objectives):
        missing = [f for f in _REQUIRED_OBJECTIVE_FIELDS if f not in obj]
        if missing:
            errors.append(f"Objective {i+1} missing fields: {missing}")

    if errors:
        return {"ok": False, "errors": errors}

    payload = {
        "saved_at": datetime.utcnow().isoformat(),
        "count": len(objectives),
        "objectives": objectives,
    }

    try:
        atomic_write_json(_OBJECTIVES_PATH, payload)
        append_jsonl(_OBJECTIVES_LOG_PATH, {"saved_at": payload["saved_at"], "payload": payload})
        append_jsonl(_OBJECTIVES_STATE_LOG_PATH, {"saved_at": payload["saved_at"], "payload": payload})
    except Exception as exc:
        return {"ok": False, "errors": [str(exc)]}

    return {
        "ok": True,
        "count": len(objectives),
        "saved_to": str(_OBJECTIVES_PATH),
        "objectives": objectives,
    }


def _load_objectives_from_log() -> list[dict]:
    try:
        if not _OBJECTIVES_LOG_PATH.exists():
            return []
        latest: list[dict] = []
        for line in _OBJECTIVES_LOG_PATH.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            entry = json.loads(line)
            payload = entry.get("payload")
            if isinstance(payload, dict):
                objectives = payload.get("objectives")
                if isinstance(objectives, list):
                    latest = [dict(item) for item in objectives if isinstance(item, dict)]
        return latest
    except Exception as exc:
        log.warning("Could not replay objectives log: %s", exc)
        return []


def _load_objectives_from_state_log() -> list[dict]:
    try:
        if not _OBJECTIVES_STATE_LOG_PATH.exists():
            return []
        latest: list[dict] = []
        for line in _OBJECTIVES_STATE_LOG_PATH.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            entry = json.loads(line)
            payload = entry.get("payload")
            if isinstance(payload, dict):
                objectives = payload.get("objectives")
                if isinstance(objectives, list):
                    latest = [dict(item) for item in objectives if isinstance(item, dict)]
        return latest
    except Exception as exc:
        log.warning("Could not replay objectives state log: %s", exc)
        return []


# ---------------------------------------------------------------------------
# Doctor packet generation (no LLM — built from module outputs)
# ---------------------------------------------------------------------------

async def generate_doctor_packet() -> dict:
    """
    Generate the quarterly doctor discussion packet for the Nov 13 visit with Dr. Wenk.
    Builds from current health state, lab trends, and known risks.
    No LLM required.
    """
    packet_date = datetime.utcnow().isoformat()

    # Top trends from known clinical data
    top_trends = [
        {"trend": "LDL rising: 99→138→146→156 mg/dL (2021-2026)", "direction": "worsening", "action_needed": True},
        {"trend": "A1c relapsed: 5.9% (Apr 2024) → 7.3% (May 2026)", "direction": "worsening", "action_needed": True},
        {"trend": "eGFR declining: 98→89→87 mL/min/1.73m² (2024-2026)", "direction": "worsening", "action_needed": True},
        {"trend": "Albumin improved: 25.7→<12 mg/L (2023-2026)", "direction": "improving", "action_needed": False},
        {"trend": "K+ normalized: 5.4→4.5 mmol/L (2025-2026)", "direction": "improving", "action_needed": False},
    ]

    # Relevant vitals and labs
    vitals_and_labs = {
        "blood_pressure": "140/90 mmHg (goal <130/80)",
        "ldl": "156 mg/dL (goal <100, NO statin — myopathy history)",
        "a1c": "7.3% (goal <7.0)",
        "egfr": "87 mL/min/1.73m² (goal >60, monitoring for decline)",
        "potassium": "4.5 mmol/L (ceiling 5.0 on ARB+spiro)",
        "vitamin_d": "55.4 ng/mL (adequate)",
        "alt_ast": "ALT 29, AST 31 (normal)",
        "psa": "0.65 ng/mL (normal)",
    }

    # Medication changes or concerns
    medication_context = [
        "Current: semaglutide, metformin ER 500mg, olmesartan/HCTZ, amlodipine, metoprolol, spironolactone",
        "HARD STOP: No statins — documented statin myopathy",
        "Concern: K+ was 5.4 (Mar 2025) on ARB+spiro combination — now 4.5, monitoring continued",
        "Discussion: Metformin dose optimization (currently on low dose ER formulation)",
        "Discussion: Non-statin LDL options never explored — ezetimibe, bempedoic acid candidates",
    ]

    # Questions for Dr. Wenk (Nov 13)
    questions_for_doctor = [
        {
            "topic": "LDL Management — Non-Statin Options",
            "data": "LDL 156 mg/dL, rising yearly since 2021. ASCVD risk elevated: T2DM + HTN + Male + 52yo. Cannot use statins.",
            "ask": "Can we start ezetimibe 10mg or bempedoic acid? PCSK9 inhibitor as escalation path?",
            "urgency": "critical",
        },
        {
            "topic": "A1c Optimization",
            "data": "A1c 7.3%, goal <7.0%. Relapsed from 5.9% in Apr 2024. On semaglutide + metformin ER 500mg.",
            "ask": "Should metformin be increased (ER 500→1000mg)? Is GLP-1 dose adequate? Consider adding SGLT2i for CV+renal benefit?",
            "urgency": "high",
        },
        {
            "topic": "OSA and CPAP Status",
            "data": "OSA diagnosed. CPAP initiation unclear. Unaddressed OSA worsens BP, glucose, HRV.",
            "ask": "Confirm CPAP status. If not initiated, order titration study. OSA tx would improve multiple conditions.",
            "urgency": "high",
        },
        {
            "topic": "eGFR Decline Monitoring",
            "data": "eGFR 98→89→87 over 2 years. On ARB + spiro — K+ was 5.4 historically.",
            "ask": "Is SGLT2i (dapagliflozin/empagliflozin) appropriate for renal protection? What is eGFR threshold for medication review?",
            "urgency": "moderate",
        },
        {
            "topic": "Post-Bariatric Micronutrient Surveillance",
            "data": "Sleeve gastrectomy Dec 2019. Last full panel unknown. Ferritin, Ca, PTH, B12 surveillance may be lapsed.",
            "ask": "Order annual post-bariatric panel: ferritin, B12, folate, Ca, Mg, PTH, D, zinc.",
            "urgency": "moderate",
        },
    ]

    # Requested outcomes
    requested_outcomes = [
        "Prescription: non-statin lipid therapy initiated (ezetimibe preferred)",
        "Lab order: BMP, lipid panel, A1c, CBC, micronutrient panel",
        "Referral or order: CPAP titration or sleep study if OSA untreated",
        "Discussion: colonoscopy scheduling (family hx polyps, overdue)",
        "Decision: Metformin dose optimization and/or SGLT2i addition for A1c + renal protection",
    ]

    # Load any current objectives
    current_objectives = []
    try:
        current_objectives = await get_current_objectives()
    except Exception:
        pass

    packet = {
        "packet_date": packet_date,
        "appointment": {
            "date": "2026-11-13",
            "provider": "Dr. Wenk",
            "type": "Follow-up",
        },
        "top_trends": top_trends,
        "vitals_and_labs": vitals_and_labs,
        "medication_context": medication_context,
        "questions_for_doctor": questions_for_doctor,
        "requested_outcomes": requested_outcomes,
        "current_objectives": current_objectives,
        "safety_reminders": [
            "NO STATINS — documented statin myopathy. Flag any statin recommendation.",
            "Monitor K+ quarterly — ARB + spironolactone hyperkalemia risk.",
            "Post-bariatric: medication absorption altered for all oral medications.",
        ],
    }

    return packet
