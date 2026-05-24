"""
scenario_engine.py — JARVIS What-If Scenario Modeling Engine
=============================================================
Projects health outcomes based on hypothetical changes to medications,
lifestyle, or conditions. Uses GPT-4o with a clinical pharmacologist /
cardiologist persona to generate evidence-based, quantitative projections.

Patient: Chris Binion | 52 yo Male | T2DM, HTN, Obesity, post-sleeve gastrectomy
Statin myopathy on record — NO STATIN RECOMMENDATIONS EVER.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_SCENARIOS_LOG_PATH = Path.home() / ".jarvis" / "health" / "scenarios.jsonl"
_HEALTH_STATE_PATH  = Path.home() / ".jarvis" / "health" / "chris_health_state.json"

_SCENARIOS_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Patient baseline (hardcoded defaults; overridden by health state when available)
# ---------------------------------------------------------------------------

PATIENT_BASELINE: dict[str, Any] = {
    "name": "Chris",
    "age": 52,
    "sex": "Male",
    "conditions": [
        "Type 2 Diabetes Mellitus (T2DM)",
        "Hypertension (HTN)",
        "Obesity (BMI 35.7)",
        "Post-sleeve gastrectomy",
    ],
    "metrics": {
        "A1c": "7.3%",
        "LDL": "156 mg/dL",
        "blood_pressure": "140/90 mmHg",
        "eGFR": "87 mL/min/1.73m²",
        "potassium": "4.5 mEq/L",
        "weight_lbs": 252,
        "bmi": 35.7,
        "hrv": 45,
        "rhr_bpm": 58,
        "steps_per_day": 8400,
    },
    "medications": [
        "Olmesartan/HCTZ 20/12.5 mg daily",
        "Amlodipine 10 mg daily",
        "Metoprolol ER 50 mg daily",
        "Spironolactone 25 mg daily",
        "Metformin ER 500 mg daily",
        "Semaglutide 2 mg weekly",
        "Citalopram 20 mg daily",
    ],
    "ascvd_risk_10yr": "20–25%",
    "safety_constraints": [
        "ABSOLUTE CONTRAINDICATION: No statins — statin myopathy documented.",
        "Hyperkalemia risk: ARB (olmesartan) + spironolactone — monitor K+ closely.",
        "Post-bariatric pharmacokinetics: altered drug absorption for all medications.",
        "QTc risk: citalopram — avoid medications that further prolong QTc.",
    ],
}


def _load_health_state() -> dict:
    """Load Chris's live health state. Returns {} if unavailable."""
    if _HEALTH_STATE_PATH.exists():
        try:
            return json.loads(_HEALTH_STATE_PATH.read_text())
        except Exception as exc:
            log.warning("Could not load health state: %s", exc)
    return {}


def _baseline_text() -> str:
    """Build a compact text summary of the patient baseline for LLM injection."""
    state = _load_health_state()

    # Try to pull live values from health state; fall back to hardcoded defaults.
    lines = [
        "=== PATIENT BASELINE ===",
        f"Name: {PATIENT_BASELINE['name']} | Age: {PATIENT_BASELINE['age']} | Sex: {PATIENT_BASELINE['sex']}",
        f"Conditions: {', '.join(PATIENT_BASELINE['conditions'])}",
        "",
        "KEY METRICS:",
    ]

    m = PATIENT_BASELINE["metrics"]
    # Override from live state if available
    if state:
        bio = state.get("biometrics", {})
        glucose = bio.get("glucose_metrics", {})
        vitals  = bio.get("vitals", {})
        ident   = state.get("identity_baseline", {})
        if glucose.get("a1c_latest"):
            m = dict(m)
            m["A1c"] = f"{glucose['a1c_latest']}%"
        if vitals.get("blood_pressure", {}).get("latest"):
            m["blood_pressure"] = vitals["blood_pressure"]["latest"]
        if ident.get("current_weight_lbs"):
            m["weight_lbs"] = ident["current_weight_lbs"]
        if ident.get("bmi"):
            m["bmi"] = ident["bmi"]

    lines += [
        f"  A1c: {m['A1c']}",
        f"  LDL: {m['LDL']}",
        f"  Blood Pressure: {m['blood_pressure']}",
        f"  eGFR: {m['eGFR']}",
        f"  K+: {m['potassium']}",
        f"  Weight: {m['weight_lbs']} lbs | BMI: {m['bmi']}",
        f"  HRV: {m['hrv']} | RHR: {m['rhr_bpm']} bpm | Steps/day: {m['steps_per_day']}",
        "",
        "CURRENT MEDICATIONS:",
    ]
    for med in PATIENT_BASELINE["medications"]:
        lines.append(f"  - {med}")

    lines += [
        "",
        f"ASCVD 10-Year Risk: {PATIENT_BASELINE['ascvd_risk_10yr']}",
        "",
        "SAFETY CONSTRAINTS (non-negotiable):",
    ]
    for constraint in PATIENT_BASELINE["safety_constraints"]:
        lines.append(f"  !! {constraint}")

    lines.append("=== END BASELINE ===")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class ScenarioChange:
    change_type: str   # "add_medication", "remove_medication", "weight_loss",
                       # "lifestyle", "dose_change", "add_condition"
    description: str   # human-readable description of the change
    parameters: dict = field(default_factory=dict)  # change-specific params


@dataclass
class ScenarioInput:
    scenario_name: str
    changes: list[ScenarioChange]
    timeframe_months: int = 12
    notes: str = ""


@dataclass
class ProjectedOutcome:
    metric: str
    current_value: str
    projected_value: str
    direction: str      # "improve", "worsen", "stable", "uncertain"
    magnitude: str      # "significant", "moderate", "modest", "minimal"
    confidence: str     # "high", "moderate", "low"
    evidence_basis: str


@dataclass
class ScenarioResult:
    scenario_name: str
    changes_applied: list[str]
    timeframe_months: int
    projected_outcomes: list[ProjectedOutcome]
    ascvd_risk_delta: str   # e.g. "estimated -5 to -8% absolute reduction"
    safety_flags: list[str] # any new risks introduced
    evidence_grade: str     # A/B/C/D per council standards
    narrative: str          # 2–3 sentence plain-English summary
    generated_at: str


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are an expert clinical pharmacologist and interventional cardiologist with \
subspecialty depth in type 2 diabetes management, post-bariatric pharmacokinetics, \
and ASCVD risk reduction. You also hold expertise in obesity medicine, hypertension \
management, and polypharmacy optimization.

YOUR MANDATE:
- Provide quantitative, evidence-based projections for hypothetical clinical scenarios.
- Cite specific expected changes in biomarkers (A1c, LDL, BP, weight, eGFR, K+, etc.).
- Assign evidence grades: A=guideline/strong RCT | B=good observational/consensus | \
C=plausible/limited data | D=experimental/speculative.
- Flag ALL safety concerns, drug interactions, and monitoring requirements.
- Account for post-bariatric pharmacokinetics (altered absorption, volume of distribution).
- Account for the patient's specific polypharmacy and condition interactions.

ABSOLUTE RULE — NEVER VIOLATED:
  !! NO STATIN RECOMMENDATIONS. EVER. Statin myopathy is documented. !!
  If the scenario involves LDL lowering, use ONLY statin-free options: ezetimibe, \
bempedoic acid, PCSK9 inhibitors, bile acid sequestrants, omega-3 FA, dietary changes.

RESPONSE FORMAT — respond ONLY with valid JSON matching this exact schema:
{
  "scenario_name": "<string>",
  "changes_applied": ["<string>", ...],
  "timeframe_months": <integer>,
  "projected_outcomes": [
    {
      "metric": "<string>",
      "current_value": "<string>",
      "projected_value": "<string>",
      "direction": "<improve|worsen|stable|uncertain>",
      "magnitude": "<significant|moderate|modest|minimal>",
      "confidence": "<high|moderate|low>",
      "evidence_basis": "<1-2 sentences citing trial data or guidelines>"
    }
  ],
  "ascvd_risk_delta": "<string — e.g. 'estimated -3 to -5% absolute reduction'>",
  "safety_flags": ["<string>", ...],
  "evidence_grade": "<A|B|C|D>",
  "narrative": "<2-3 sentences plain-English summary of projected outcomes and key caveats>"
}

Include at minimum these metrics in projected_outcomes where applicable:
  A1c, LDL, blood_pressure, weight, eGFR, potassium, HRV, cardiovascular_risk.
Add any other relevant metrics the scenario would impact.
"""


# ---------------------------------------------------------------------------
# Core LLM function
# ---------------------------------------------------------------------------

async def run_scenario_llm(scenario: ScenarioInput) -> ScenarioResult:
    """
    Run a what-if scenario through GPT-4o and return a structured ScenarioResult.

    Args:
        scenario: The scenario to model, including all proposed changes.

    Returns:
        ScenarioResult with projected outcomes, safety flags, and narrative.
    """
    try:
        from .llm_gateway import get_gateway, LLMMessage
    except ImportError:
        from llm_gateway import get_gateway, LLMMessage  # type: ignore

    gw = get_gateway()
    if gw is None:
        raise RuntimeError("LLM gateway unavailable — cannot run scenario.")

    # Build user prompt
    changes_text = "\n".join(
        f"  [{i+1}] {ch.change_type.upper()}: {ch.description}"
        + (f"\n      Parameters: {json.dumps(ch.parameters)}" if ch.parameters else "")
        for i, ch in enumerate(scenario.changes)
    )

    user_prompt = f"""\
{_baseline_text()}

=== SCENARIO REQUEST ===
Scenario Name: {scenario.scenario_name}
Timeframe: {scenario.timeframe_months} months
{f'Notes: {scenario.notes}' if scenario.notes else ''}

PROPOSED CHANGES:
{changes_text}

Model the projected health outcomes for this patient if the above changes are \
implemented. Consider interactions between changes, the patient's existing \
polypharmacy, post-bariatric physiology, and realistic adherence timelines. \
Respond ONLY with valid JSON.
"""

    log.info("Running scenario: %s (%d change(s), %d months)",
             scenario.scenario_name, len(scenario.changes), scenario.timeframe_months)

    try:
        response = await asyncio.to_thread(
            gw.complete,
            messages=[
                LLMMessage("system", _SYSTEM_PROMPT),
                LLMMessage("user", user_prompt),
            ],
            task_type="critical",
            agent_id="scenario-engine",
            force_model="gpt-4o",
            temperature=0.1,
        )
    except Exception as exc:
        log.error("Scenario LLM call failed: %s", exc)
        raise

    if response.error:
        log.error("Scenario LLM error: %s", response.error)
        raise RuntimeError(f"LLM error: {response.error}")

    # Parse response
    raw = response.text.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(0))
            except Exception:
                log.error("Scenario JSON parse failed. Raw (%d chars): %s", len(raw), raw[:2000])
                raise RuntimeError("Failed to parse scenario response as JSON.")
        else:
            log.error("No JSON found in scenario response (%d chars): %s", len(raw), raw[:2000])
            raise RuntimeError("No JSON object found in scenario LLM response.")

    # Hydrate ProjectedOutcome objects
    projected_outcomes = [
        ProjectedOutcome(
            metric          = po.get("metric", "unknown"),
            current_value   = po.get("current_value", "N/A"),
            projected_value = po.get("projected_value", "N/A"),
            direction       = po.get("direction", "uncertain"),
            magnitude       = po.get("magnitude", "minimal"),
            confidence      = po.get("confidence", "low"),
            evidence_basis  = po.get("evidence_basis", ""),
        )
        for po in data.get("projected_outcomes", [])
    ]

    result = ScenarioResult(
        scenario_name    = data.get("scenario_name", scenario.scenario_name),
        changes_applied  = data.get("changes_applied", [c.description for c in scenario.changes]),
        timeframe_months = data.get("timeframe_months", scenario.timeframe_months),
        projected_outcomes = projected_outcomes,
        ascvd_risk_delta = data.get("ascvd_risk_delta", "unknown"),
        safety_flags     = data.get("safety_flags", []),
        evidence_grade   = data.get("evidence_grade", "C"),
        narrative        = data.get("narrative", ""),
        generated_at     = datetime.utcnow().isoformat(),
    )

    # Auto-save every scenario run
    await asyncio.to_thread(save_scenario, result)

    return result


# ---------------------------------------------------------------------------
# Quick scenario factory
# ---------------------------------------------------------------------------

_QUICK_SCENARIO_DEFS: dict[str, ScenarioInput] = {
    "add_ezetimibe": ScenarioInput(
        scenario_name="Add Ezetimibe 10 mg",
        changes=[
            ScenarioChange(
                change_type="add_medication",
                description="Add ezetimibe 10 mg daily for LDL lowering",
                parameters={"drug": "ezetimibe", "dose": "10 mg", "frequency": "daily",
                            "indication": "LDL reduction — statin-free alternative"},
            )
        ],
        timeframe_months=12,
        notes="Patient has documented statin myopathy. Ezetimibe is first-line non-statin LDL therapy.",
    ),

    "add_bempedoic_acid": ScenarioInput(
        scenario_name="Add Bempedoic Acid 180 mg",
        changes=[
            ScenarioChange(
                change_type="add_medication",
                description="Add bempedoic acid 180 mg daily for LDL lowering",
                parameters={"drug": "bempedoic acid", "dose": "180 mg", "frequency": "daily",
                            "indication": "LDL reduction — statin-intolerant patients"},
            )
        ],
        timeframe_months=12,
        notes="CLEAR Outcomes trial: ~13% LDL reduction; cardiovascular event reduction in statin-intolerant patients.",
    ),

    "add_pcsk9i": ScenarioInput(
        scenario_name="Add Alirocumab 75 mg q2w (PCSK9 inhibitor)",
        changes=[
            ScenarioChange(
                change_type="add_medication",
                description="Add alirocumab 75 mg subcutaneous every 2 weeks for LDL lowering",
                parameters={"drug": "alirocumab", "dose": "75 mg", "frequency": "q2w",
                            "route": "subcutaneous", "indication": "LDL reduction — PCSK9 inhibitor"},
            )
        ],
        timeframe_months=12,
        notes="ODYSSEY OUTCOMES: ~50-60% LDL reduction. Highly effective in statin-intolerant patients.",
    ),

    "weight_loss_10pct": ScenarioInput(
        scenario_name="10% Body Weight Loss (~25 lbs)",
        changes=[
            ScenarioChange(
                change_type="weight_loss",
                description="Achieve 10% body weight reduction (~25 lbs, from 252 to ~227 lbs)",
                parameters={"weight_loss_pct": 10, "weight_loss_lbs": 25,
                            "target_weight_lbs": 227, "target_bmi": 32.1},
            )
        ],
        timeframe_months=12,
        notes="Model all downstream metabolic, cardiovascular, and renal effects of 10% weight loss.",
    ),

    "weight_loss_20pct": ScenarioInput(
        scenario_name="20% Body Weight Loss (~50 lbs)",
        changes=[
            ScenarioChange(
                change_type="weight_loss",
                description="Achieve 20% body weight reduction (~50 lbs, from 252 to ~202 lbs)",
                parameters={"weight_loss_pct": 20, "weight_loss_lbs": 50,
                            "target_weight_lbs": 202, "target_bmi": 28.6},
            )
        ],
        timeframe_months=24,
        notes="Model all downstream metabolic, cardiovascular, and renal effects of 20% weight loss. "
              "Consider potential medication dose reductions.",
    ),

    "metformin_dose_up": ScenarioInput(
        scenario_name="Increase Metformin ER 500 mg → 1500 mg",
        changes=[
            ScenarioChange(
                change_type="dose_change",
                description="Titrate Metformin ER from 500 mg daily to 1500 mg daily",
                parameters={"drug": "metformin ER", "current_dose": "500 mg",
                            "new_dose": "1500 mg", "titration": "gradual over 4-6 weeks"},
            )
        ],
        timeframe_months=6,
        notes="Post-bariatric: assess GI tolerance and absorption differences. "
              "Consider B12 monitoring with higher dose.",
    ),

    "semaglutide_dose_up": ScenarioInput(
        scenario_name="Increase Semaglutide 2 mg → 2.4 mg (Obesity Dose)",
        changes=[
            ScenarioChange(
                change_type="dose_change",
                description="Increase semaglutide from 2 mg (diabetes dose) to 2.4 mg (obesity dose)",
                parameters={"drug": "semaglutide", "current_dose": "2 mg",
                            "new_dose": "2.4 mg", "indication_shift": "T2DM → obesity"},
            )
        ],
        timeframe_months=12,
        notes="STEP trials at 2.4 mg show additional weight loss vs 2 mg. "
              "Post-bariatric pharmacokinetics may alter response.",
    ),

    "add_cgm": ScenarioInput(
        scenario_name="Add Continuous Glucose Monitoring (CGM)",
        changes=[
            ScenarioChange(
                change_type="lifestyle",
                description="Add live CGM monitoring (e.g., Dexterity G7 or Libre 3) for real-time glucose feedback",
                parameters={"device": "CGM", "type": "real-time continuous monitoring",
                            "data_integration": "JARVIS health platform"},
            )
        ],
        timeframe_months=6,
        notes="CGM in T2DM not on insulin: evidence for A1c reduction via behavioral feedback loop.",
    ),

    "exercise_150min": ScenarioInput(
        scenario_name="Add 150 min/week Moderate Aerobic Exercise",
        changes=[
            ScenarioChange(
                change_type="lifestyle",
                description="Add structured aerobic exercise: 150 minutes per week at moderate intensity",
                parameters={"type": "aerobic", "duration_min_per_week": 150,
                            "intensity": "moderate (50-70% max HR)", "examples": "brisk walking, cycling, swimming"},
            )
        ],
        timeframe_months=12,
        notes="ADA/ACC guideline-recommended exercise for T2DM and HTN. "
              "Current steps ~8400/day — structured exercise is additive.",
    ),

    "cpap_confirmed": ScenarioInput(
        scenario_name="OSA Treated with CPAP (AHI Normalized)",
        changes=[
            ScenarioChange(
                change_type="add_condition",
                description="Obstructive sleep apnea successfully treated with CPAP therapy — AHI normalized",
                parameters={"condition": "OSA", "treatment": "CPAP", "ahi_status": "normalized",
                            "adherence": "nightly, >4 hours/night"},
            )
        ],
        timeframe_months=12,
        notes="Model downstream effects of OSA treatment on BP, HRV, insulin resistance, "
              "cognitive function, and weight. OSA is a common T2DM/HTN comorbidity.",
    ),
}


async def run_quick_scenario(change_type: str, **kwargs: Any) -> ScenarioResult:
    """
    Run a pre-built scenario by type name.

    Args:
        change_type: One of the predefined scenario keys (e.g. "add_ezetimibe").
        **kwargs: Optional overrides — timeframe_months, notes.

    Returns:
        ScenarioResult from the LLM projection.

    Raises:
        ValueError: If change_type is not recognized.
    """
    if change_type not in _QUICK_SCENARIO_DEFS:
        valid = ", ".join(sorted(_QUICK_SCENARIO_DEFS.keys()))
        raise ValueError(
            f"Unknown quick scenario type: '{change_type}'. "
            f"Valid options: {valid}"
        )

    # Make a copy so we can apply kwargs overrides
    base = _QUICK_SCENARIO_DEFS[change_type]
    scenario = ScenarioInput(
        scenario_name    = base.scenario_name,
        changes          = base.changes,
        timeframe_months = kwargs.get("timeframe_months", base.timeframe_months),
        notes            = kwargs.get("notes", base.notes),
    )

    log.info("Running quick scenario: %s", change_type)
    return await run_scenario_llm(scenario)


# ---------------------------------------------------------------------------
# Parallel scenario comparison
# ---------------------------------------------------------------------------

async def compare_scenarios(scenarios: list[ScenarioInput]) -> dict:
    """
    Run multiple scenarios in parallel and return a comparison table.

    Args:
        scenarios: List of ScenarioInput objects to evaluate concurrently.

    Returns:
        dict with keys:
          - "results": list of ScenarioResult dicts
          - "comparison_table": metric-by-scenario matrix
          - "ascvd_comparison": ASCVD risk delta per scenario
          - "safety_summary": aggregated safety flags
          - "generated_at": ISO timestamp
    """
    log.info("Comparing %d scenarios in parallel", len(scenarios))

    results: list[ScenarioResult] = await asyncio.gather(
        *[run_scenario_llm(s) for s in scenarios],
        return_exceptions=True,
    )

    valid_results: list[ScenarioResult] = []
    errors: list[dict] = []

    for i, r in enumerate(results):
        if isinstance(r, Exception):
            log.error("Scenario '%s' failed: %s", scenarios[i].scenario_name, r)
            errors.append({"scenario": scenarios[i].scenario_name, "error": str(r)})
        else:
            valid_results.append(r)

    # Build comparison table: {metric: {scenario_name: projected_value}}
    all_metrics: set[str] = set()
    for r in valid_results:
        for po in r.projected_outcomes:
            all_metrics.add(po.metric)

    comparison_table: dict[str, dict[str, str]] = {}
    for metric in sorted(all_metrics):
        comparison_table[metric] = {}
        for r in valid_results:
            match = next((po for po in r.projected_outcomes if po.metric == metric), None)
            if match:
                direction_arrow = {"improve": "▲", "worsen": "▼", "stable": "—", "uncertain": "?"}.get(
                    match.direction, "?"
                )
                comparison_table[metric][r.scenario_name] = (
                    f"{match.projected_value} ({direction_arrow} {match.magnitude}, "
                    f"{match.confidence} confidence)"
                )
            else:
                comparison_table[metric][r.scenario_name] = "not modeled"

    return {
        "results": [_result_to_dict(r) for r in valid_results],
        "comparison_table": comparison_table,
        "ascvd_comparison": {r.scenario_name: r.ascvd_risk_delta for r in valid_results},
        "safety_summary": {r.scenario_name: r.safety_flags for r in valid_results},
        "errors": errors,
        "generated_at": datetime.utcnow().isoformat(),
    }


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------

def _result_to_dict(result: ScenarioResult) -> dict:
    """Convert ScenarioResult to a JSON-serializable dict."""
    d = asdict(result)
    return d


def save_scenario(result: ScenarioResult) -> None:
    """
    Append a scenario result to the JSONL scenarios log.

    Args:
        result: The ScenarioResult to persist.
    """
    _SCENARIOS_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = _result_to_dict(result)
    try:
        with open(_SCENARIOS_LOG_PATH, "a") as f:
            f.write(json.dumps(entry) + "\n")
        log.debug("Saved scenario '%s' to %s", result.scenario_name, _SCENARIOS_LOG_PATH)
    except Exception as exc:
        log.error("Failed to save scenario: %s", exc)


def get_saved_scenarios() -> list[dict]:
    """
    Load all previously run scenarios from the JSONL log.

    Returns:
        List of scenario result dicts, ordered oldest-first.
        Returns [] if log does not exist or is empty.
    """
    if not _SCENARIOS_LOG_PATH.exists():
        log.debug("No scenarios log found at %s", _SCENARIOS_LOG_PATH)
        return []

    results = []
    try:
        with open(_SCENARIOS_LOG_PATH) as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    results.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    log.warning("Skipping malformed scenario log line %d: %s", line_num, exc)
    except Exception as exc:
        log.error("Failed to read scenarios log: %s", exc)

    log.debug("Loaded %d saved scenarios from %s", len(results), _SCENARIOS_LOG_PATH)
    return results


# ---------------------------------------------------------------------------
# Quick-access helpers for common single-question scenarios
# ---------------------------------------------------------------------------

async def what_if_ezetimibe() -> ScenarioResult:
    """What if we add ezetimibe 10 mg for LDL lowering?"""
    return await run_quick_scenario("add_ezetimibe")


async def what_if_pcsk9i() -> ScenarioResult:
    """What if we add a PCSK9 inhibitor (alirocumab)?"""
    return await run_quick_scenario("add_pcsk9i")


async def what_if_weight_loss(pct: int = 10) -> ScenarioResult:
    """What if Chris loses 10% or 20% body weight?"""
    if pct == 20:
        return await run_quick_scenario("weight_loss_20pct")
    return await run_quick_scenario("weight_loss_10pct")


async def what_if_exercise() -> ScenarioResult:
    """What if Chris adds 150 min/week structured aerobic exercise?"""
    return await run_quick_scenario("exercise_150min")


async def ldl_reduction_showdown() -> dict:
    """
    Compare all three non-statin LDL-lowering options head-to-head:
    ezetimibe vs bempedoic acid vs alirocumab (PCSK9i).
    """
    scenarios = [
        _QUICK_SCENARIO_DEFS["add_ezetimibe"],
        _QUICK_SCENARIO_DEFS["add_bempedoic_acid"],
        _QUICK_SCENARIO_DEFS["add_pcsk9i"],
    ]
    return await compare_scenarios(scenarios)


async def weight_loss_showdown() -> dict:
    """Compare 10% vs 20% body weight loss outcomes."""
    scenarios = [
        _QUICK_SCENARIO_DEFS["weight_loss_10pct"],
        _QUICK_SCENARIO_DEFS["weight_loss_20pct"],
    ]
    return await compare_scenarios(scenarios)
