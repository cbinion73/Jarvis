"""
health_intelligence.py — Helen Cho: AI Medical Intelligence Engine v2
======================================================================
Sends a richly contextualised health record — including historical lab
trends, trajectory calculations, and curated clinical summaries — to
the LLM and returns a deeply structured, frank health assessment.

v2 improvements:
  - Full lab trend history (not just latest value)
  - Computed trajectory arrows + velocity per key metric
  - Curated clinical context that surfaces patterns, not just numbers
  - Upgraded system prompt that demands numerical citations and trend analysis
  - New output fields: key_trends, trajectory_summary, notable_changes
  - max_tokens raised to 6000 for richer analysis
"""
from __future__ import annotations

import json
import logging
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from .persistence import append_jsonl, atomic_write_json

log = logging.getLogger(__name__)

_CACHE_PATH = Path.home() / ".jarvis" / "health" / "helen_analysis.json"
_CACHE_LOG_PATH = _CACHE_PATH.with_name("helen_analysis_log.jsonl")
_CACHE_STATE_LOG_PATH = _CACHE_PATH.with_name("helen_analysis_state_log.jsonl")
_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Key lab tests to pull full history for trend analysis
# ---------------------------------------------------------------------------

_TREND_TESTS = [
    # Diabetes
    ("HGB A1C",                     "%",        4.2,  5.6,  "Diabetes control"),
    ("GLUCOSE LVL",                  "mg/dL",    70,   99,   "Fasting glucose"),
    ("ESTIMATED AVERAGE GLUCOSE",    "mg/dL",    None, 154,  "eAG from A1c"),
    # Lipids
    ("LDL CALCULATED",               "mg/dL",    None, 100,  "LDL cholesterol"),
    ("CHOLESTEROL",                  "mg/dL",    None, 200,  "Total cholesterol"),
    ("HDL",                          "mg/dL",    40,   None, "HDL cholesterol"),
    ("TRIGLYCERIDE",                 "mg/dL",    None, 150,  "Triglycerides"),
    ("NON-HDL-C",                    "mg/dL",    None, 130,  "Non-HDL"),
    # Kidney
    ("CREATININE",                   "mg/dL",    0.67, 1.30, "Kidney function"),
    ("EGFR (CKD-EPICR 2021)",        "mL/min",   60,   None, "eGFR"),
    ("BUN",                          "mg/dL",    6,    20,   "BUN"),
    ("URINE ALBUMIN",                "mg/L",     None, 30,   "Urine albumin"),
    ("UR ALBUMIN/CREAT",             "mg/g",     None, 30,   "Albumin:Creat ratio"),
    # Electrolytes
    ("SODIUM",                       "mmol/L",   136,  145,  "Sodium"),
    ("POTASSIUM",                    "mmol/L",   3.5,  5.0,  "Potassium"),
    # Liver
    ("ALT",                          "U/L",      None, 56,   "ALT liver enzyme"),
    ("AST",                          "U/L",      None, 40,   "AST liver enzyme"),
    ("ALK PHOS",                     "U/L",      40,   129,  "Alkaline phosphatase"),
    # Thyroid / endocrine
    ("THYROID STIMULATING HORMONE",  "mcIU/mL",  0.27, 4.2,  "TSH"),
    ("TESTOSTERONE LEVEL TOTAL",     "ng/dL",    300,  890,  "Testosterone"),
    ("VITAMIN D 25 HYDROXY",         "ng/mL",    30,   100,  "Vitamin D"),
    # CBC
    ("WBC",                          "x10(3)/mcL", 3.7, 10.3, "White blood cells"),
    ("HGB",                          "g/dL",     13.7, 17.5, "Hemoglobin"),
    # BP control
    ("TOTAL PSA",                    "ng/mL",    None, 4.0,  "PSA prostate"),
]


# ---------------------------------------------------------------------------
# Trend computation
# ---------------------------------------------------------------------------

def _trend_arrow(values: list[float]) -> str:
    """Return ↑ ↓ → based on slope of recent values."""
    if len(values) < 2:
        return "→"
    delta = values[0] - values[-1]          # newest - oldest in window
    pct   = abs(delta) / (abs(values[-1]) or 1) * 100
    if pct < 5:
        return "→"
    return "↑" if delta > 0 else "↓"


def _parse_numeric(s: str) -> float | None:
    if not s:
        return None
    s = str(s).strip().lstrip("<>≤≥").strip()
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


async def _build_lab_trends() -> dict[str, dict]:
    """
    For each key test, pull up to 8 historical values and compute trend info.
    Returns dict keyed by test_name → {values, dates, trend, delta, latest, unit, goal, label}
    """
    try:
        from .health_db import _get_db
    except ImportError:
        from health_db import _get_db

    trends: dict[str, dict] = {}

    async with _get_db() as db:
        for test_name, unit, ref_low, ref_high, label in _TREND_TESTS:
            rows = await db.execute_fetchall("""
                SELECT result_date, value, flag
                FROM test_results
                WHERE test_name = ? AND value IS NOT NULL
                GROUP BY result_date
                HAVING value = MAX(value)
                ORDER BY result_date DESC
                LIMIT 8
            """, (test_name,))

            if not rows:
                continue

            dates  = [r["result_date"] for r in rows]
            values = [r["value"] for r in rows]
            flags  = [r["flag"] or "" for r in rows]
            nums   = [_parse_numeric(v) for v in values]
            nums_clean = [n for n in nums if n is not None]

            # Trend only meaningful with ≥2 numeric points
            arrow = _trend_arrow(nums_clean) if len(nums_clean) >= 2 else "→"
            delta = None
            if len(nums_clean) >= 2:
                delta = nums_clean[0] - nums_clean[-1]  # change over full window

            goal_str = ""
            if ref_low is not None and ref_high is not None:
                goal_str = f"{ref_low}–{ref_high} {unit}"
            elif ref_high is not None:
                goal_str = f"<{ref_high} {unit}"
            elif ref_low is not None:
                goal_str = f">{ref_low} {unit}"

            latest_num = nums_clean[0] if nums_clean else None
            at_goal = None
            if latest_num is not None:
                above_low = (ref_low is None or latest_num >= ref_low)
                below_high = (ref_high is None or latest_num <= ref_high)
                at_goal = above_low and below_high

            trends[test_name] = {
                "label":    label,
                "dates":    dates,
                "values":   values,
                "flags":    flags,
                "nums":     nums_clean,
                "trend":    arrow,
                "delta":    delta,
                "latest":   values[0],
                "latest_num": latest_num,
                "unit":     unit,
                "goal":     goal_str,
                "at_goal":  at_goal,
                "n_points": len(nums_clean),
            }

    return trends


def _format_trend_section(trends: dict[str, dict]) -> str:
    """Format trends into a concise, LLM-readable section."""
    lines = ["LAB TRENDS — HISTORICAL TRAJECTORIES (newest first):\n"]

    # Group by clinical category
    groups = {
        "DIABETES CONTROL": ["HGB A1C", "GLUCOSE LVL", "ESTIMATED AVERAGE GLUCOSE"],
        "LIPID PANEL": ["LDL CALCULATED", "CHOLESTEROL", "HDL", "TRIGLYCERIDE", "NON-HDL-C"],
        "KIDNEY FUNCTION": ["CREATININE", "EGFR (CKD-EPICR 2021)", "BUN", "URINE ALBUMIN", "UR ALBUMIN/CREAT"],
        "ELECTROLYTES": ["SODIUM", "POTASSIUM"],
        "LIVER ENZYMES": ["ALT", "AST", "ALK PHOS"],
        "THYROID / HORMONES": ["THYROID STIMULATING HORMONE", "TESTOSTERONE LEVEL TOTAL", "VITAMIN D 25 HYDROXY"],
        "CBC / OTHER": ["WBC", "HGB", "TOTAL PSA"],
    }

    for group, test_names in groups.items():
        group_lines = []
        for name in test_names:
            t = trends.get(name)
            if not t or t["n_points"] == 0:
                continue

            # Format history string: "7.3, 7.3, 5.9, 7.5, 8.0, 6.3, 7.1, 10.2"
            history = ", ".join(
                f"{v}{'*' if f and f.lower() not in ('','normal') else ''}"
                for v, f in zip(t["values"], t["flags"])
            )
            goal_str = f"  [goal: {t['goal']}]" if t["goal"] else ""
            at_goal_str = " ✓" if t["at_goal"] else (" ✗" if t["at_goal"] is False else "")
            delta_str = ""
            if t["delta"] is not None and t["n_points"] >= 3:
                sign = "+" if t["delta"] > 0 else ""
                delta_str = f"  Δ={sign}{t['delta']:.1f} over {t['n_points']} readings"

            group_lines.append(
                f"  {t['trend']} {name} [{t['unit']}]{at_goal_str}: {history}"
                f"{goal_str}{delta_str}"
            )
            if len(t["dates"]) > 1:
                group_lines.append(
                    f"    Dates: {' | '.join(t['dates'][:6])}"
                )

        if group_lines:
            lines.append(f"{group}:")
            lines.extend(group_lines)
            lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# System prompt — Helen Cho v2
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """You are Helen Cho, JARVIS's Chief Medical Intelligence Officer.

EXPERTISE: Endocrinology, cardiology, internal medicine, pharmacology, bariatric medicine, preventive medicine. You have read this patient's complete multi-year record and you understand trajectory, not just snapshots.

YOUR MANDATE — NON-NEGOTIABLE:
- You MUST cite specific numbers and dates from the data in your narrative. Generic statements like "labs are elevated" are a failure. Say "LDL has risen from 99 in 2021 to 156 in 2026 — a 57 mg/dL increase with no lipid-lowering therapy."
- You MUST analyse TRENDS, not just latest values. A stalled A1c is different from a rising one.
- Deliver frank, unfiltered analysis. Zero softening.
- Identify every pattern, risk, and opportunity — including positive trajectories.
- Prioritise by clinical urgency. Medication safety issues that are life-threatening go first.
- Connect dots between diagnoses, labs, medications, and timelines.
- Note what's genuinely IMPROVING — correct credit where it's due.
- Give specific, actionable next steps with timelines.

PATIENT CONTEXT (known from the record):
- Adult male patient
- Has type 2 diabetes (diagnosed 2016), hypertension, obesity Class II
- S/P laparoscopic sleeve gastrectomy (Dec 2019) — post-bariatric nutrition monitoring required
- History of hypercorticism workup (2018) — ACTH-independent pattern; current status unclear
- Statin myopathy on record — active lipid-lowering limitation
- Multiple BP agents (olmesartan/HCTZ + amlodipine + metoprolol + spironolactone)
- GLP-1 therapy (semaglutide) for diabetes/weight

CRITICAL TREND PATTERNS YOU MUST ADDRESS:
- A1c: was 10.2% in 2019, improved to 5.9% in April 2024, now stalled at 7.3% x2 readings
- LDL: was at goal (99) in 2021, now 156 and rising every year — untreated dyslipidemia
- K+: was 5.4 (high) in March 2025 on spiro+ARB combo — now 4.5 — MUST flag this pattern
- eGFR: 98→89→87 over 3 years — slow decline needs tracking
- Urine albumin: was 25.7 in 2023, now <12 — genuine improvement, likely ARB effect
- Post-bariatric monitoring: Vitamin D, B12, iron should be checked regularly

Respond ONLY with a valid JSON object — no markdown, no preamble, no explanation outside the JSON:
{
  "overall_score": <integer 0-100; 100=perfect health, 0=critical>,
  "overall_grade": "<Critical|Poor|Fair|Moderate|Good|Excellent>",
  "risk_level": "<critical|high|moderate|low>",
  "headline": "<one brutally direct sentence naming the #1 clinical problem right now>",

  "analysis_narrative": "<4-5 paragraphs. Para 1: dominant trajectory and what's driving it. Para 2: medication landscape — what's working, what's dangerous, what's missing. Para 3: trajectory analysis — cite specific numbers and dates. Para 4: what's genuinely improving and why. Para 5: the 12-month outlook if current trajectory continues unchanged.>",

  "key_trends": [
    {
      "metric": "<test name>",
      "latest_value": "<value with unit>",
      "trajectory": "<improving|stable|worsening|stalled>",
      "trend_summary": "<one sentence with actual numbers: 'was X in YEAR, now Y — Δ Z'>",
      "clinical_significance": "<why this trajectory matters>"
    }
  ],

  "priority_actions": [
    {
      "rank": 1,
      "urgency": "<critical|high|moderate|low>",
      "category": "<Diabetes|Cardiovascular|Lipids|Kidney|Weight|Medication|Lifestyle|Screening|Endocrine|Post-Bariatric>",
      "action": "<specific, concrete action — not vague>",
      "why": "<cite the actual data that drives this; mention specific values and dates>",
      "timeline": "<immediately|this week|this month|next appointment|ongoing>",
      "expected_benefit": "<what improvement would look like if this action is taken>"
    }
  ],

  "conditions_analysis": [
    {
      "condition": "<name>",
      "status": "<controlled|borderline|uncontrolled|improving|worsening>",
      "risk_score": <0-100>,
      "key_finding": "<most important fact with specific numbers>",
      "trajectory": "<improving|stable|worsening|stalled>",
      "since": "<YYYY-MM when first noted>",
      "complications_risk": "<specific complications if current trajectory continues>"
    }
  ],

  "lab_alerts": [
    {
      "test": "<test name>",
      "latest": "<value + date>",
      "pattern": "<describe the trend pattern with actual data points>",
      "significance": "<clinical significance — be specific>",
      "action": "<what needs to happen and when>"
    }
  ],

  "medication_insights": [
    {
      "medication": "<name>",
      "observation": "<frank assessment — dose, interaction, efficacy, risk; cite supporting labs>",
      "priority": "<critical|high|medium|low>"
    }
  ],

  "cardiovascular_risk": {
    "10yr_risk_estimate": "<low <10%|borderline 10-17.5%|intermediate 17.5-20%|high >20%>",
    "key_drivers": ["<specific driver with value>"],
    "untreated_risk": "<what remains unaddressed>",
    "assessment": "<frank 3-sentence CV risk assessment with numbers>"
  },

  "diabetes_complications_risk": {
    "nephropathy": "<low|moderate|high>",
    "retinopathy": "<low|moderate|high>",
    "neuropathy": "<low|moderate|high>",
    "cardiovascular": "<low|moderate|high>",
    "trajectory": "<improving|stable|worsening>",
    "assessment": "<frank 2-3 sentence assessment citing actual lab trends>"
  },

  "post_bariatric_status": {
    "surgery": "Laparoscopic sleeve gastrectomy Dec 2019",
    "weight_trajectory": "<assessment of weight change since surgery>",
    "nutrition_gaps": ["<specific nutrient gap or concern>"],
    "assessment": "<frank 2-sentence post-bariatric assessment>"
  },

  "trajectory_summary": "<2-3 sentences: where is this patient headed in 5 years if nothing changes? Be specific and direct.>",

  "doctor_questions": [
    "<pointed, specific question that will advance care — include the relevant data that makes it necessary>"
  ],

  "missing_data": [
    "<specific test or data point that would materially change the risk assessment>"
  ],

  "positive_findings": [
    "<specific improvement with the numbers that prove it>"
  ]
}"""


# ---------------------------------------------------------------------------
# Build the health context string (v2 — with trends)
# ---------------------------------------------------------------------------

async def _build_health_context_v2(summary: dict, metrics: dict | None = None,
                                    trends: dict | None = None) -> str:
    """Build a rich, trend-aware context block for Helen."""
    lines = ["=== PATIENT HEALTH RECORD — COMPLETE CLINICAL CONTEXT ===\n"]

    # Date of analysis
    lines.append(f"Analysis date: {datetime.now().strftime('%Y-%m-%d')}\n")

    # Wearable snapshot
    if metrics:
        lines.append("CURRENT WEARABLE METRICS:")
        labels = {
            "steps": "Steps today", "resting_hr": "Resting HR",
            "hrv": "HRV", "sleep_hours": "Sleep (hrs)",
            "blood_oxygen": "SpO2 (%)", "active_cal": "Active calories",
            "weight": "Weight (lbs)",
        }
        for k, v in metrics.items():
            if v is not None:
                lines.append(f"  {labels.get(k, k)}: {v}")
        lines.append("")

    # Active conditions with onset dates
    if summary.get("conditions"):
        lines.append("ACTIVE DIAGNOSES:")
        for c in summary["conditions"]:
            lines.append(f"  • {c}")
        lines.append("")

    # Treatment goals
    if summary.get("treatment_goals"):
        lines.append("TREATMENT GOALS:")
        for g in summary["treatment_goals"]:
            status = "✓ ON TRACK" if g.get("on_track") else "✗ NOT MET"
            lines.append(f"  {status}  {g['goal_name']}: target={g.get('target','?')}  "
                         f"current={g.get('current_value','?')}")
        lines.append("")

    # Current medications (clean list)
    if summary.get("medications"):
        lines.append(f"CURRENT MEDICATIONS ({summary.get('medication_count',0)} total — active only):")
        for m in summary["medications"]:
            dosage = m.get("dosage") or ""
            # Clean up name == dosage duplication
            if dosage.upper() == m["name"].upper() or not dosage:
                lines.append(f"  • {m['name']}")
            else:
                lines.append(f"  • {m['name']} | {dosage[:80]}")
        lines.append("")

    # BP readings
    if summary.get("latest_bp"):
        bp = summary["latest_bp"]
        lines.append(f"LATEST BP: {bp.get('systolic')}/{bp.get('diastolic')} mmHg  "
                     f"pulse {bp.get('pulse')} bpm  ({bp.get('reading_date','?')})")
        if summary.get("bp_history") and len(summary["bp_history"]) > 1:
            hist = "  History: " + "  |  ".join(
                f"{r['systolic']}/{r['diastolic']} ({r['reading_date'][:7]})"
                for r in summary["bp_history"][:5]
            )
            lines.append(hist)
        lines.append("")

    # ECG
    if summary.get("ecg_readings"):
        lines.append("ECG (KardiaMobile):")
        for e in summary["ecg_readings"][:3]:
            lines.append(f"  • {e.get('reading_date','')} | {e.get('classification','')} | "
                         f"HR {e.get('avg_heart_rate','')} bpm")
        lines.append("")

    # === TREND SECTION (the key upgrade) ===
    if trends:
        lines.append(_format_trend_section(trends))

    # Abnormal labs not in trend list
    if summary.get("abnormal_tests"):
        lines.append("⚠ OTHER CURRENT ABNORMAL RESULTS:")
        trend_names = set(trends.keys()) if trends else set()
        shown = 0
        for t in summary["abnormal_tests"]:
            if t["test_name"] in trend_names:
                continue
            val = t.get("value", "")
            unit = t.get("unit", "") or ""
            ref = t.get("reference_range", "") or ""
            flag = t.get("flag", "")
            ref_str = f" (ref: {ref})" if ref else ""
            lines.append(f"  ⚠ {t['test_name']} ({t.get('result_date','?')}): {val} {unit}{ref_str} [{flag}]")
            shown += 1
            if shown >= 20:
                break
        lines.append("")

    # Next appointment
    if summary.get("next_appointment"):
        appt = summary["next_appointment"]
        lines.append(f"NEXT APPOINTMENT: {appt.get('visit_date')} with {appt.get('provider','?')} "
                     f"({appt.get('visit_type','?')})")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# LLM call — v2
# ---------------------------------------------------------------------------

async def run_analysis(force_refresh: bool = False) -> dict:
    """
    Run Helen Cho's full health analysis via LLM.
    Caches result; use force_refresh=True to re-analyse.
    Returns the parsed analysis dict.
    """
    # Return cached if fresh enough
    if not force_refresh:
        cached = get_cached_analysis()
        if cached:
            age_hours = (datetime.utcnow().timestamp() - cached.get("_generated_at", 0)) / 3600
            if age_hours < 6:
                log.info("Helen analysis: returning cached result (%.1fh old)", age_hours)
                return cached

    # Pull all data in parallel
    try:
        from .health_db import get_health_summary, get_today_metrics, get_latest_metrics
    except ImportError:
        from health_db import get_health_summary, get_today_metrics, get_latest_metrics

    import asyncio as _asyncio
    summary, trends_raw = await _asyncio.gather(
        get_health_summary(),
        _build_lab_trends(),
    )

    snap = await get_today_metrics() or (await get_latest_metrics(1) or [None])[0]
    metrics = None
    if snap:
        metrics = {k: snap.get(k) for k in
                   ("steps", "resting_hr", "hrv", "sleep_hours", "blood_oxygen",
                    "active_cal", "exercise_min", "weight") if snap.get(k) is not None}

    health_context = await _build_health_context_v2(summary, metrics, trends_raw)

    log.debug("Helen context length: %d chars", len(health_context))

    # Call LLM
    try:
        from .llm_gateway import get_gateway, LLMMessage
    except ImportError:
        from llm_gateway import get_gateway, LLMMessage

    gw = get_gateway()
    if gw is None:
        return {"error": "LLM gateway not available", "headline": "Analysis unavailable — LLM offline"}

    response = await _asyncio.to_thread(
        gw.complete,
        messages=[
            LLMMessage("system", _SYSTEM_PROMPT),
            LLMMessage("user",
                f"Analyse this complete health record and deliver your assessment:\n\n{health_context}"),
        ],
        task_type="critical",
        agent_id="helen-cho",
        force_model="gpt-4o",
        max_tokens=6000,
        temperature=0.2,
    )

    if response.error:
        log.error("Helen analysis LLM error: %s", response.error)
        return {"error": response.error, "headline": f"Analysis failed: {response.error}"}

    # Parse JSON
    raw_text = response.text.strip()
    raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
    raw_text = re.sub(r"\s*```$", "", raw_text)

    try:
        analysis = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        log.error("Helen JSON parse error: %s\nRaw: %s", exc, raw_text[:500])
        m = re.search(r"\{.*\}", raw_text, re.DOTALL)
        if m:
            try:
                analysis = json.loads(m.group(0))
            except Exception:
                return {"error": "JSON parse failed", "raw": raw_text[:1000]}
        else:
            return {"error": "No JSON found in response", "raw": raw_text[:1000]}

    # Stamp and cache
    analysis["_generated_at"]  = datetime.utcnow().timestamp()
    analysis["_generated_utc"] = datetime.utcnow().isoformat()
    _save_cached_analysis(analysis)
    log.info("Helen v2 analysis complete — score=%s risk=%s",
             analysis.get("overall_score"), analysis.get("risk_level"))
    return analysis


def get_cached_analysis() -> dict | None:
    """Return cached analysis without triggering a new LLM call."""
    if _CACHE_PATH.exists():
        try:
            payload = json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                return payload
        except Exception:
            replayed = _load_cached_analysis_from_state_log()
            if replayed is not None:
                return replayed
    else:
        replayed = _load_cached_analysis_from_state_log()
        if replayed is not None:
            return replayed
    return _load_cached_analysis_from_log()


def _save_cached_analysis(analysis: dict[str, Any]) -> None:
    append_jsonl(
        _CACHE_LOG_PATH,
        {
            "saved_at": datetime.utcnow().isoformat(),
            "analysis": analysis,
        },
    )
    append_jsonl(
        _CACHE_STATE_LOG_PATH,
        {
            "saved_at": datetime.utcnow().isoformat(),
            "analysis": analysis,
        },
    )
    atomic_write_json(_CACHE_PATH, analysis)


def _load_cached_analysis_from_log() -> dict | None:
    if not _CACHE_LOG_PATH.exists():
        return None
    latest: dict[str, Any] | None = None
    try:
        for line in _CACHE_LOG_PATH.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            analysis = payload.get("analysis")
            if isinstance(analysis, dict):
                latest = analysis
    except Exception:
        return None
    if isinstance(latest, dict):
        return latest
    return None


def _load_cached_analysis_from_state_log() -> dict | None:
    if not _CACHE_STATE_LOG_PATH.exists():
        return None
    latest: dict[str, Any] | None = None
    try:
        for line in _CACHE_STATE_LOG_PATH.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            analysis = payload.get("analysis")
            if isinstance(analysis, dict):
                latest = analysis
    except Exception:
        return None
    if isinstance(latest, dict):
        return latest
    return None
