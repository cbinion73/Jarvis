"""
JARVIS Symptom Triage Engine — Oracle-First Protocol
Based on Helen Cho Master Binder v1.5, File 09: Symptom Triage Mode

Routes:
  POST /api/health/symptom/triage    — full triage with Oracle gate + specialist routing
  GET  /api/health/symptom/redflags  — list of Chris's personalized red flag symptoms
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
# Red flag symptom lists — hardcoded, keyword-matched, no LLM
# ---------------------------------------------------------------------------

_RED_FLAGS_911 = [
    "chest pain", "chest pressure", "chest tightness",
    "shortness of breath", "can't breathe",
    "fainting", "passed out", "loss of consciousness",
    "seizure", "stroke symptoms", "face drooping", "arm weakness", "speech difficulty",
    "severe allergic reaction", "throat swelling", "can't swallow",
    "severe bleeding", "vomiting blood", "black tarry stool",
    "glucose below 54", "glucose under 54", "severe low blood sugar",
    "severe confusion", "unable to think",
]

_RED_FLAGS_ER = [
    "bp over 180", "blood pressure 180", "systolic over 180",
    "glucose over 400", "blood sugar over 400",
    "potassium over 6", "heart racing", "palpitations with dizziness",
    "severe headache", "worst headache of my life",
    "vision changes sudden", "numbness on one side",
    "lips swelling", "hives all over",
    "severe abdominal pain",
]

_RED_FLAGS_URGENT = [
    "glucose over 300", "blood sugar 300",
    "bp over 160", "blood pressure 160",
    "potassium over 5", "k+ over 5",
    "chest discomfort mild", "shortness of breath mild",
    "significant dizziness", "severe headache not worst ever",
    "new medication reaction", "rash after medication",
    "ankle swelling sudden", "leg swelling sudden",
    "fever over 103",
]

# ---------------------------------------------------------------------------
# Routing map — symptom keyword → specialist agent_ids
# ---------------------------------------------------------------------------

_ROUTING_MAP: list[tuple[list[str], list[str]]] = [
    (
        ["chest", "palpitations", "bp", "blood pressure", "shortness of breath", "cardiac", "heart"],
        ["cristina-yang", "dr-mccoy"],
    ),
    (
        ["blood sugar", "glucose", "dizzy", "sweating", "hypoglycemia", "hyperglycemia", "a1c"],
        ["gregory-house", "data"],
    ),
    (
        ["reaction", "rash", "new medication", "side effect", "drug", "allergy", "medication"],
        ["sherlock-holmes", "dr-mccoy"],
    ),
    (
        ["tired", "fatigue", "sleep", "apnea", "snoring", "exhausted", "drowsy"],
        ["morpheus", "dr-mccoy"],
    ),
    (
        ["anxiety", "depression", "mood", "sad", "overwhelmed", "stress", "mental", "emotion"],
        ["deanna-troi", "paul-weston"],
    ),
    (
        ["back", "joint", "muscle", "headache", "pain", "ache", "sore"],
        ["dr-mccoy", "thor-fitness"],
    ),
    (
        ["nausea", "stomach", "eating", "weight", "nauseous", "vomit", "appetite", "nutrition"],
        ["poison-ivy", "gregory-house"],
    ),
]


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def classify_symptom_urgency(symptoms: str) -> dict:
    """
    Keyword-match symptoms string against red flag lists.
    Returns {oracle_pathway, matched_flags, requires_immediate_action}.
    Checks 911 first, then ER, then URGENT. Case-insensitive.
    """
    text = symptoms.lower()

    matched_911 = [f for f in _RED_FLAGS_911 if f in text]
    if matched_911:
        return {
            "oracle_pathway": "O-911",
            "matched_flags": matched_911,
            "requires_immediate_action": True,
        }

    matched_er = [f for f in _RED_FLAGS_ER if f in text]
    if matched_er:
        return {
            "oracle_pathway": "O-ER",
            "matched_flags": matched_er,
            "requires_immediate_action": True,
        }

    matched_urgent = [f for f in _RED_FLAGS_URGENT if f in text]
    if matched_urgent:
        return {
            "oracle_pathway": "O-URGENT",
            "matched_flags": matched_urgent,
            "requires_immediate_action": False,
        }

    # Non-urgent: check if any general symptom words warrant clinic vs monitor
    clinic_words = ["pain", "discomfort", "swelling", "fever", "nausea", "vomiting",
                    "diarrhea", "bleeding", "rash", "cough", "infection"]
    if any(w in text for w in clinic_words):
        return {
            "oracle_pathway": "O-CLINIC",
            "matched_flags": [],
            "requires_immediate_action": False,
        }

    return {
        "oracle_pathway": "O-MONITOR",
        "matched_flags": [],
        "requires_immediate_action": False,
    }


def route_to_specialists(symptoms: str, pathway: str) -> list[str]:
    """
    Route to relevant council members based on symptom keywords.
    Returns list of agent_ids. Always includes the-oracle first and dr-mccoy.
    """
    text = symptoms.lower()
    routed: list[str] = []

    for keywords, agents in _ROUTING_MAP:
        if any(kw in text for kw in keywords):
            for agent in agents:
                if agent not in routed:
                    routed.append(agent)

    # Always include the-oracle first and dr-mccoy
    result: list[str] = ["the-oracle"]
    for agent in routed:
        if agent != "the-oracle" and agent != "dr-mccoy":
            result.append(agent)
    if "dr-mccoy" not in result:
        result.append("dr-mccoy")

    return result


async def run_triage(
    symptoms: str,
    duration: str = "",
    severity: int | None = None,
    associated_symptoms: str = "",
    context: str = "",
) -> dict:
    """
    Full triage flow:
    1. classify_symptom_urgency() — immediate keyword check, no LLM
    2. If O-911 or O-ER: return emergency response immediately with action steps
    3. route_to_specialists()
    4. LLM call: build a structured triage report with routed specialists
    5. append_council_decision() to log
    Returns triage report dict.
    """
    triage_date = datetime.utcnow().isoformat()
    urgency = classify_symptom_urgency(symptoms)
    pathway = urgency["oracle_pathway"]

    # --- Emergency short-circuit ---
    if pathway == "O-911":
        report = {
            "triage_date": triage_date,
            "symptom_input": symptoms,
            "oracle_pathway": pathway,
            "requires_immediate_action": True,
            "emergency_instructions": "Call 911 now. Do not drive yourself. Do not wait to see if symptoms improve.",
            "urgency_summary": "Emergency: symptoms match 911-level red flags.",
            "matched_red_flags": urgency["matched_flags"],
            "routed_specialists": ["the-oracle"],
            "specialist_assessment": "Emergency services required. No further assessment at this time.",
            "recommended_action": "Call 911 immediately.",
            "action_category": "Emergency care now",
            "if_then_rule": "Do not wait. Call 911 now.",
            "do_not": ["Drive yourself", "Wait to see if symptoms improve", "Take additional medications without EMS guidance"],
            "confidence": "high",
        }
        try:
            from .longevity_council import append_council_decision
        except ImportError:
            from longevity_council import append_council_decision
        await append_council_decision({"type": "symptom_triage", **report})
        return report

    if pathway == "O-ER":
        report = {
            "triage_date": triage_date,
            "symptom_input": symptoms,
            "oracle_pathway": pathway,
            "requires_immediate_action": True,
            "emergency_instructions": "Go to the emergency room now. Do not wait for an appointment.",
            "urgency_summary": "ER-level: symptoms require emergency department evaluation.",
            "matched_red_flags": urgency["matched_flags"],
            "routed_specialists": ["the-oracle", "cristina-yang", "dr-mccoy"],
            "specialist_assessment": "Emergency room evaluation required. Do not delay.",
            "recommended_action": "Go to the nearest emergency room immediately.",
            "action_category": "Emergency care now",
            "if_then_rule": "If symptoms worsen in transit, call 911.",
            "do_not": ["Drive yourself if symptomatic", "Wait for a scheduled appointment"],
            "confidence": "high",
        }
        try:
            from .longevity_council import append_council_decision
        except ImportError:
            from longevity_council import append_council_decision
        await append_council_decision({"type": "symptom_triage", **report})
        return report

    # --- Non-emergency: route to specialists and run LLM triage ---
    routed_specialists = route_to_specialists(symptoms + " " + associated_symptoms, pathway)

    specialist_names = {
        "the-oracle": "The Oracle (Red Flag Sentinel)",
        "cristina-yang": "Cristina Yang (Cardiovascular)",
        "gregory-house": "Gregory House (Metabolic & Diagnostic)",
        "sherlock-holmes": "Sherlock Holmes (Medication Sentinel)",
        "morpheus": "Morpheus (Sleep & Circadian)",
        "data": "Data (Lab Intelligence)",
        "poison-ivy": "Poison Ivy (Nutritional Biochemistry)",
        "dr-mccoy": "Dr. McCoy (Primary Care)",
        "thor-fitness": "Thor (Physical Performance)",
        "deanna-troi": "Deanna Troi (Mental Health — Empathic)",
        "paul-weston": "Dr. Paul Weston (Mental Health — Clinical)",
        "yoda": "Yoda (Behavior & Lifestyle)",
        "st-luke": "St. Luke (Spiritual Stewardship)",
    }
    specialist_labels = [specialist_names.get(s, s) for s in routed_specialists]

    # Build health state summary for context
    health_context = ""
    try:
        try:
            from .longevity_council import health_state_summary
        except ImportError:
            from longevity_council import health_state_summary
        health_context = health_state_summary()
    except Exception as exc:
        log.warning("Could not load health state: %s", exc)

    severity_str = f" | Severity: {severity}/10" if severity is not None else ""
    duration_str = f" | Duration: {duration}" if duration else ""
    assoc_str = f" | Associated symptoms: {associated_symptoms}" if associated_symptoms else ""
    context_str = f" | Context: {context}" if context else ""

    triage_prompt = f"""You are the JARVIS Longevity Council conducting a structured symptom triage.

PATIENT: Chris Binion | Male, 52 | T2DM (A1c 7.3%) | Hypertension (BP 140/90, 4 meds)
SAFETY FLAGS: NO STATINS EVER (statin myopathy). K+ monitoring critical (ARB+spiro). Post-bariatric sleeve gastrectomy Dec 2019.

SYMPTOM REPORT:
Primary symptoms: {symptoms}{severity_str}{duration_str}{assoc_str}{context_str}

ORACLE PATHWAY ASSIGNED: {pathway}
MATCHED RED FLAGS: {urgency['matched_flags'] if urgency['matched_flags'] else 'None'}

ROUTED SPECIALISTS: {', '.join(specialist_labels)}

{health_context}

Produce a structured triage report. Respond ONLY with valid JSON matching this schema exactly:
{{
  "triage_date": "{triage_date}",
  "symptom_input": "{symptoms}",
  "oracle_pathway": "{pathway}",
  "requires_immediate_action": false,
  "emergency_instructions": null,
  "urgency_summary": "<one sentence on urgency level and why>",
  "matched_red_flags": {json.dumps(urgency['matched_flags'])},
  "routed_specialists": {json.dumps(routed_specialists)},
  "specialist_assessment": "<2-4 sentences from the routed specialists' combined perspective>",
  "recommended_action": "<specific action Chris should take>",
  "action_category": "<Contact clinician soon | Schedule routine | Monitor | Emergency care now>",
  "if_then_rule": "<If [symptom or threshold], then [action]>",
  "do_not": ["<thing to avoid>"],
  "confidence": "<high | moderate | low>"
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
                LLMMessage("system", "You are JARVIS Symptom Triage Engine. Respond ONLY with valid JSON."),
                LLMMessage("user", triage_prompt),
            ],
            task_type="critical",
            agent_id="symptom-triage",
            force_model="gpt-4o",
            max_tokens=1500,
            temperature=0.2,
        )

        if response.error:
            raise RuntimeError(f"LLM error: {response.error}")

        raw = response.text.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        report = json.loads(raw)

    except Exception as exc:
        log.error("Triage LLM call failed: %s", exc)
        # Fallback: return structured report without LLM assessment
        report = {
            "triage_date": triage_date,
            "symptom_input": symptoms,
            "oracle_pathway": pathway,
            "requires_immediate_action": False,
            "emergency_instructions": None,
            "urgency_summary": f"Pathway {pathway} assigned based on keyword screening. LLM assessment unavailable.",
            "matched_red_flags": urgency["matched_flags"],
            "routed_specialists": routed_specialists,
            "specialist_assessment": "LLM specialist assessment unavailable. Please consult your healthcare provider.",
            "recommended_action": "Contact your clinician to discuss these symptoms.",
            "action_category": "Contact clinician soon",
            "if_then_rule": "If symptoms worsen, escalate to urgent care.",
            "do_not": [],
            "confidence": "low",
            "llm_error": str(exc),
        }

    # Log to council decision log
    try:
        try:
            from .longevity_council import append_council_decision
        except ImportError:
            from longevity_council import append_council_decision
        await append_council_decision({"type": "symptom_triage", **report})
    except Exception as exc:
        log.warning("Could not append to decision log: %s", exc)

    return report


def get_red_flags_for_patient() -> dict:
    """
    Return Chris's personalized red flag list with patient-specific context.
    """
    return {
        "patient": "Chris Binion",
        "last_updated": "2026-05-22",
        "call_911": {
            "description": "Call 911 immediately — life-threatening emergency",
            "triggers": _RED_FLAGS_911,
            "patient_specific": [
                "Glucose below 54 mg/dL — severe hypoglycemia (semaglutide + metformin use)",
                "Any altered consciousness or inability to respond",
                "Chest pain with diaphoresis (sweating) — possible MI",
            ],
        },
        "go_to_er": {
            "description": "Go to emergency room immediately",
            "triggers": _RED_FLAGS_ER,
            "patient_specific": [
                "BP systolic over 180 — hypertensive crisis risk (on 4-drug regimen)",
                "K+ over 6.0 — dangerous hyperkalemia (ARB + spironolactone combination)",
                "Glucose over 400 mg/dL — severe hyperglycemia",
            ],
        },
        "contact_clinician_urgently": {
            "description": "Contact clinician same day or go to urgent care",
            "triggers": _RED_FLAGS_URGENT,
            "patient_specific": [
                "K+ over 5.0 — elevated hyperkalemia risk on ARB + spironolactone",
                "BP over 160 — above established threshold for this patient",
                "Glucose over 300 mg/dL — significant hyperglycemia on semaglutide",
                "Any rash or muscle pain after starting a new medication — statin myopathy history",
            ],
        },
        "absolute_contraindications": [
            {
                "trigger": "Any statin being prescribed or recommended",
                "action": "REFUSE and alert immediately — documented statin myopathy on record",
                "urgency": "critical",
            },
        ],
        "monitoring_thresholds": {
            "potassium_ceiling": "5.0 mmol/L (ARB + spironolactone regimen)",
            "glucose_hypoglycemia_threshold": "54 mg/dL (severe hypoglycemia)",
            "glucose_hyperglycemia_threshold": "300 mg/dL (action required)",
            "bp_action_threshold": "160/100 mmHg (contact clinician)",
            "bp_emergency_threshold": "180/120 mmHg (ER now)",
            "egfr_floor": "60 mL/min/1.73m² (CKD stage 3 alert)",
        },
    }
