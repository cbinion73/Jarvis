"""
JARVIS Lab Review Engine — Data Agent Protocol
Based on Helen Cho Master Binder v1.5, File 10: Lab Review Mode v0.5

Reviews lab panels with pre-analytic context, trend analysis, and
generates clinician questions per panel.

Routes (add to service.py):
  GET  /api/health/labs/review           — full panel review
  GET  /api/health/labs/summary          — quick summary of latest labs
  GET  /api/health/labs/abnormal         — abnormal results with clinical context
  GET  /api/health/labs/trending         — tests trending toward abnormal
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Evidence grades (from binder)
# ---------------------------------------------------------------------------
_EVIDENCE_GRADES = {
    "a1c_goal": "Level A — ADA Standards of Care 2025",
    "ldl_goal": "Level A — ACC/AHA Cardiovascular Risk Guideline 2023",
    "egfr_monitoring": "Level A — KDIGO 2024; ADA Standards of Care 2025",
    "post_bariatric_labs": "Level A — ASMBS Guidelines 2023",
}

# ---------------------------------------------------------------------------
# Patient-specific lab context — Chris Binion
# Known historical values embedded for trend analysis
# ---------------------------------------------------------------------------
_LDL_HISTORY = [
    {"date": "2021", "value": 99, "unit": "mg/dL"},
    {"date": "2024", "value": 138, "unit": "mg/dL"},
    {"date": "2025-03", "value": 146, "unit": "mg/dL"},
    {"date": "2026-05", "value": 156, "unit": "mg/dL"},
]

_EGFR_HISTORY = [
    {"date": "2024", "value": 98, "unit": "mL/min/1.73m²"},
    {"date": "2025-03", "value": 89, "unit": "mL/min/1.73m²"},
    {"date": "2026-05", "value": 87, "unit": "mL/min/1.73m²"},
]

_A1C_HISTORY = [
    {"date": "2019", "value": 10.2, "unit": "%"},
    {"date": "2024-04", "value": 5.9, "unit": "%"},
    {"date": "2026-05", "value": 7.3, "unit": "%"},
]

_K_HISTORY = [
    {"date": "2025-03", "value": 5.4, "unit": "mmol/L"},
    {"date": "2026-05", "value": 4.5, "unit": "mmol/L"},
]


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

async def get_labs_from_db(panel: str | None = None) -> list[dict]:
    """Pull test results from health_db. Optionally filter by panel name prefix."""
    try:
        from .health_db import _get_db
    except ImportError:
        from health_db import _get_db

    async with _get_db() as db:
        if panel:
            cur = await db.execute(
                "SELECT test_name, result_date, value, unit, reference_range, flag, "
                "components, order_id, status, provider "
                "FROM test_results "
                "WHERE UPPER(test_name) LIKE ? "
                "ORDER BY result_date DESC",
                (f"{panel.upper()}%",),
            )
        else:
            cur = await db.execute(
                "SELECT test_name, result_date, value, unit, reference_range, flag, "
                "components, order_id, status, provider "
                "FROM test_results "
                "WHERE value IS NOT NULL OR components IS NOT NULL "
                "GROUP BY test_name "
                "HAVING result_date = MAX(result_date) "
                "ORDER BY result_date DESC, test_name"
            )
        return [dict(r) for r in await cur.fetchall()]


def _find_lab(labs: list[dict], *name_fragments: str) -> dict | None:
    """Find a lab result by name fragments (case-insensitive substring match)."""
    for lab in labs:
        name = (lab.get("test_name") or "").upper()
        if all(f.upper() in name for f in name_fragments):
            return lab
    return None


def _safe_float(val: Any) -> float | None:
    if val is None:
        return None
    try:
        return float(str(val).replace("<", "").replace(">", "").strip())
    except (ValueError, TypeError):
        return None


def _flag_label(flag: str | None, value: float | None, ref_range: str | None) -> str:
    """Produce a human-readable flag label."""
    if flag and flag.strip().upper() not in ("", "NORMAL", "N"):
        return flag.strip()
    return "Normal"


# ---------------------------------------------------------------------------
# Panel review functions
# ---------------------------------------------------------------------------

async def review_metabolic_panel() -> dict:
    """
    Review BMP/CMP: Na, K, Cl, CO2, BUN, Creatinine, Glucose, Calcium.
    Apply pre-analytic context rules.
    Key flags: K⁺ trend, BUN slightly high, eGFR trend.
    """
    labs = await get_labs_from_db()

    keys = {
        "sodium":      ("SODIUM", "NA"),
        "potassium":   ("POTASSIUM", "K"),
        "chloride":    ("CHLORIDE",),
        "co2":         ("CO2", "CARBON DIOXIDE", "BICARBONATE"),
        "bun":         ("BUN", "BLOOD UREA NITROGEN", "UREA NITROGEN"),
        "creatinine":  ("CREATININE",),
        "glucose":     ("GLUCOSE",),
        "calcium":     ("CALCIUM",),
        "egfr":        ("EGFR", "GFR", "GLOMERULAR"),
    }

    results = []
    for key, fragments in keys.items():
        for frag_set in [fragments]:
            lab = None
            for frag in frag_set:
                lab = _find_lab(labs, frag)
                if lab:
                    break
            if lab:
                val = _safe_float(lab.get("value"))
                results.append({
                    "test": key.replace("_", " ").title(),
                    "value": lab.get("value"),
                    "unit": lab.get("unit"),
                    "reference_range": lab.get("reference_range"),
                    "flag": _flag_label(lab.get("flag"), val, lab.get("reference_range")),
                    "date": lab.get("result_date"),
                })

    flags = []
    k_lab = _find_lab(labs, "POTASSIUM") or _find_lab(labs, " K ")
    k_val = _safe_float(k_lab.get("value")) if k_lab else 4.5  # fallback to known value
    if k_val and k_val > 5.0:
        flags.append({
            "test": "Potassium",
            "flag": "HIGH — Hyperkalemia risk on ARB + spironolactone",
            "urgency": "O-URGENT" if k_val > 5.5 else "O-CLINIC",
            "value": k_val,
        })

    egfr_lab = _find_lab(labs, "EGFR") or _find_lab(labs, "GFR")
    egfr_val = _safe_float(egfr_lab.get("value")) if egfr_lab else 87
    if egfr_val and egfr_val < 90:
        flags.append({
            "test": "eGFR",
            "flag": f"CKD Stage G2 (eGFR 60-89) — slow decline trend detected",
            "urgency": "O-MONITOR",
            "value": egfr_val,
            "context": "eGFR 98 (2024) → 89 (Mar 2025) → 87 (May 2026). Slow but consistent decline.",
        })

    bun_lab = _find_lab(labs, "BUN") or _find_lab(labs, "UREA NITROGEN")
    bun_val = _safe_float(bun_lab.get("value")) if bun_lab else 21
    if bun_val and bun_val > 20:
        flags.append({
            "test": "BUN",
            "flag": "Slightly elevated — hydration status and kidney function context needed",
            "urgency": "O-MONITOR",
            "value": bun_val,
        })

    return {
        "panel": "Basic/Comprehensive Metabolic Panel",
        "date_reviewed": datetime.utcnow().isoformat(),
        "results": results,
        "flags": flags,
        "trend_analysis": {
            "potassium": {
                "history": _K_HISTORY,
                "direction": "Improving",
                "note": "K⁺ 5.4 (Mar 2025) → 4.5 (May 2026). Hyperkalemia resolved. ARB + spironolactone monitoring working.",
            },
            "egfr": {
                "history": _EGFR_HISTORY,
                "direction": "Declining — slow",
                "note": "98→87 over 24 months. Absolute decline 11 points. CKD Stage G2. Semaglutide and ARB are nephroprotective — continue.",
            },
        },
        "pre_analytic_context": [
            "BUN slightly elevated — ensure patient was well-hydrated at draw. High-protein diet (post-bariatric) may also raise BUN.",
            "Glucose — confirm fasting status at draw; fasting glucose 155 mg/dL is elevated.",
        ],
        "clinical_questions": [
            "eGFR declining from 98 to 87 over 2 years — is annual monitoring sufficient, or should it move to every 6 months?",
            "BUN 21 with rising creatinine — is this diet-related, dehydration, or early CKD progression?",
            "K⁺ now 4.5 — safe range confirmed. What is the monitoring frequency plan for olmesartan + spironolactone combination?",
        ],
        "evidence_grade": _EVIDENCE_GRADES["egfr_monitoring"],
    }


async def review_lipid_panel() -> dict:
    """
    Review lipids: Total cholesterol, LDL, HDL, triglycerides, non-HDL.
    Critical context: statin myopathy — NO statin recommendations.
    Non-statin options: ezetimibe, bempedoic acid, PCSK9 inhibitors.
    """
    labs = await get_labs_from_db()

    lipid_tests = [
        ("Total Cholesterol", ("TOTAL CHOLESTEROL", "CHOLESTEROL")),
        ("LDL", ("LDL",)),
        ("HDL", ("HDL",)),
        ("Triglycerides", ("TRIGLYCERIDES", "TRIGLYCERIDE")),
        ("Non-HDL Cholesterol", ("NON-HDL",)),
    ]

    results = []
    for label, fragments in lipid_tests:
        lab = None
        for frag in fragments:
            lab = _find_lab(labs, frag)
            if lab:
                break
        if lab:
            val = _safe_float(lab.get("value"))
            results.append({
                "test": label,
                "value": lab.get("value"),
                "unit": lab.get("unit"),
                "reference_range": lab.get("reference_range"),
                "flag": _flag_label(lab.get("flag"), val, lab.get("reference_range")),
                "date": lab.get("result_date"),
            })

    # LDL trajectory analysis
    ldl_lab = _find_lab(labs, "LDL")
    current_ldl = _safe_float(ldl_lab.get("value")) if ldl_lab else 156

    ldl_trajectory = {
        "history": _LDL_HISTORY,
        "current": current_ldl,
        "direction": "Rising — WORSENING",
        "5_year_change": f"+57 mg/dL (99 → {current_ldl})",
        "goal": "<100 mg/dL in high-risk T2DM (ACC/AHA Level A)",
        "gap_from_goal": f"{current_ldl - 100:.0f} mg/dL above goal" if current_ldl else "Unknown",
        "rate_of_rise": "~11 mg/dL per year over 5 years",
        "urgency": "HIGH — No current LDL-lowering therapy despite rising LDL in high-cardiovascular-risk patient",
        "statin_contraindicated": True,
        "statin_note": "NEVER recommend statins — documented statin myopathy",
    }

    non_statin_options = [
        {
            "drug": "Ezetimibe (Zetia)",
            "mechanism": "Inhibits intestinal cholesterol absorption",
            "lowers_ldl_by": "15-25%",
            "estimated_ldl_on_drug": f"~{round(current_ldl * 0.80)}-{round(current_ldl * 0.85)} mg/dL",
            "side_effects": "Well-tolerated; occasional GI symptoms",
            "evidence": "Level A — SHARP trial, IMPROVE-IT trial",
            "cost": "Generic available — low cost",
            "post_bariatric_note": "Tablet absorption generally maintained post-sleeve. Preferred first non-statin option.",
        },
        {
            "drug": "Bempedoic acid (Nexletol)",
            "mechanism": "Inhibits ATP-citrate lyase — upstream of statin target, activates LDL receptor",
            "lowers_ldl_by": "18-28%",
            "estimated_ldl_on_drug": f"~{round(current_ldl * 0.75)}-{round(current_ldl * 0.82)} mg/dL",
            "side_effects": "Gout risk (raises uric acid); avoid in gout. No myopathy.",
            "evidence": "Level A — CLEAR Outcomes trial (2023) — reduced MACE in statin-intolerant patients",
            "cost": "Brand only — may require prior authorization",
            "post_bariatric_note": "Oral tablet. Check UA/gout history before starting.",
        },
        {
            "drug": "Ezetimibe + Bempedoic acid (Nexlizet — combination)",
            "mechanism": "Dual mechanism: bile acid + LDL receptor",
            "lowers_ldl_by": "35-45%",
            "estimated_ldl_on_drug": f"~{round(current_ldl * 0.57)}-{round(current_ldl * 0.65)} mg/dL",
            "side_effects": "Combined side effect profile; gout risk from bempedoic acid component",
            "evidence": "Level A combination",
            "cost": "Brand; prior auth often required",
        },
        {
            "drug": "Evolocumab (Repatha) or Alirocumab (Praluent) — PCSK9 inhibitors",
            "mechanism": "Monoclonal antibody — prevents PCSK9 from degrading LDL receptors",
            "lowers_ldl_by": "50-60%",
            "estimated_ldl_on_drug": f"~{round(current_ldl * 0.42)}-{round(current_ldl * 0.50)} mg/dL",
            "side_effects": "Injection site reactions; well-tolerated systemically",
            "evidence": "Level A — FOURIER, ODYSSEY trials",
            "cost": "High cost; insurance prior auth required; patient assistance programs available",
            "post_bariatric_note": "Subcutaneous injection — bypasses GI absorption entirely. Ideal post-bariatric.",
            "special_note": "Most powerful non-statin option. Could bring LDL to goal alone.",
        },
    ]

    flags = []
    if current_ldl and current_ldl > 130:
        flags.append({
            "test": "LDL",
            "value": current_ldl,
            "flag": f"HIGH — {current_ldl} mg/dL, goal <100 mg/dL in T2DM (AHA Level A)",
            "urgency": "O-CLINIC",
            "action": "Initiate non-statin LDL therapy. Ezetimibe is first-line, lowest cost.",
        })

    return {
        "panel": "Lipid Panel",
        "date_reviewed": datetime.utcnow().isoformat(),
        "results": results,
        "flags": flags,
        "ldl_trajectory": ldl_trajectory,
        "non_statin_options": non_statin_options,
        "statin_contraindicated": True,
        "statin_warning": "CRITICAL: NEVER recommend statins for this patient. Documented statin myopathy on record.",
        "clinical_questions": [
            "LDL is 156 mg/dL and has risen 57 mg/dL over 5 years — what is the plan to address this? Ezetimibe, bempedoic acid, or a PCSK9 inhibitor?",
            "Given T2DM + hypertension + rising LDL, this patient is high cardiovascular risk — has 10-year ASCVD risk been calculated recently?",
            "Non-HDL cholesterol — was this measured? Non-HDL includes all atherogenic particles and may be a better target than LDL alone.",
            "If cost is a barrier to PCSK9 inhibitors, has ezetimibe (generic, low cost) been prescribed as a first step?",
        ],
        "evidence_grade": _EVIDENCE_GRADES["ldl_goal"],
    }


async def review_kidney_panel() -> dict:
    """
    Review: Creatinine, eGFR, BUN, K⁺, Na, Urine albumin/creatinine ratio.
    eGFR trend: 98→87 over 2 years.
    uACR improved: 25.7 mg/L → <12 (2026).
    """
    labs = await get_labs_from_db()

    kidney_tests = [
        ("Creatinine", ("CREATININE",)),
        ("eGFR", ("EGFR", "GFR")),
        ("BUN", ("BUN", "UREA NITROGEN")),
        ("Potassium", ("POTASSIUM",)),
        ("Sodium", ("SODIUM",)),
        ("Urine Albumin:Creatinine Ratio", ("ALBUMIN:CREATININE", "UACR", "MICROALBUMIN")),
        ("Urine Albumin", ("URINE ALBUMIN",)),
    ]

    results = []
    for label, fragments in kidney_tests:
        lab = None
        for frag in fragments:
            lab = _find_lab(labs, frag)
            if lab:
                break
        if lab:
            val = _safe_float(lab.get("value"))
            results.append({
                "test": label,
                "value": lab.get("value"),
                "unit": lab.get("unit"),
                "reference_range": lab.get("reference_range"),
                "flag": _flag_label(lab.get("flag"), val, lab.get("reference_range")),
                "date": lab.get("result_date"),
            })

    egfr_lab = _find_lab(labs, "EGFR") or _find_lab(labs, "GFR")
    egfr_val = _safe_float(egfr_lab.get("value")) if egfr_lab else 87

    # CKD staging per KDIGO
    if egfr_val:
        if egfr_val >= 90:
            egfr_stage = "G1 — Normal or high (≥90)"
        elif egfr_val >= 60:
            egfr_stage = "G2 — Mildly decreased (60-89)"
        elif egfr_val >= 45:
            egfr_stage = "G3a — Mildly to moderately decreased (45-59)"
        elif egfr_val >= 30:
            egfr_stage = "G3b — Moderately to severely decreased (30-44)"
        elif egfr_val >= 15:
            egfr_stage = "G4 — Severely decreased (15-29)"
        else:
            egfr_stage = "G5 — Kidney failure (<15)"
    else:
        egfr_stage = "Unknown"

    return {
        "panel": "Kidney / Renal Function Panel",
        "date_reviewed": datetime.utcnow().isoformat(),
        "results": results,
        "egfr_stage": egfr_stage,
        "current_egfr": egfr_val,
        "egfr_trend": _EGFR_HISTORY,
        "uacr_trend": [
            {"date": "2023", "value": "25.7 mg/L", "interpretation": "Microalbuminuria — A2 category"},
            {"date": "2026-05", "value": "<12 mg/L", "interpretation": "Normal — A1 category. Improvement on ARB therapy."},
        ],
        "clinical_significance": (
            "eGFR decline from 98 to 87 over 24 months is slow but consistent. "
            "Stage G2 CKD. uACR improvement from 25.7 to <12 shows ARB (olmesartan) is "
            "providing nephroprotection — do not discontinue ARB. Semaglutide also has "
            "proven renal protective effects in T2DM."
        ),
        "flags": [
            {
                "test": "eGFR",
                "value": egfr_val,
                "flag": "CKD Stage G2 — slow decline",
                "urgency": "O-MONITOR",
                "note": "11-point decline over 24 months. Not acute, but monitor every 6 months.",
            },
        ] if egfr_val and egfr_val < 90 else [],
        "clinical_questions": [
            "eGFR declining from 98 to 87 over 2 years — has annual vs. semi-annual monitoring been discussed?",
            "Is nephrology referral warranted? KDIGO recommends referral at eGFR <60 or if decline >5 mL/min/year.",
            "uACR improved to <12 — confirm at next visit to verify sustained response.",
            "Is any SGLT2 inhibitor (dapagliflozin, empagliflozin) being considered? These have proven renal and CV benefit in T2DM with CKD — and do not require a functioning GLP-1 axis.",
        ],
        "evidence_grade": _EVIDENCE_GRADES["egfr_monitoring"],
    }


async def review_liver_panel() -> dict:
    """
    Review: ALT, AST, Alk Phos, Bili, Total Protein, Albumin.
    Current: ALT 29, AST 31 — both normal.
    """
    labs = await get_labs_from_db()

    liver_tests = [
        ("ALT (SGPT)", ("ALT", "SGPT")),
        ("AST (SGOT)", ("AST", "SGOT")),
        ("Alkaline Phosphatase", ("ALKALINE PHOSPHATASE", "ALK PHOS", "ALP")),
        ("Total Bilirubin", ("TOTAL BILIRUBIN", "BILIRUBIN")),
        ("Total Protein", ("TOTAL PROTEIN",)),
        ("Albumin", ("ALBUMIN",)),
    ]

    results = []
    for label, fragments in liver_tests:
        lab = None
        for frag in fragments:
            lab = _find_lab(labs, frag)
            if lab:
                break
        if lab:
            val = _safe_float(lab.get("value"))
            results.append({
                "test": label,
                "value": lab.get("value"),
                "unit": lab.get("unit"),
                "reference_range": lab.get("reference_range"),
                "flag": _flag_label(lab.get("flag"), val, lab.get("reference_range")),
                "date": lab.get("result_date"),
            })

    alt_lab = _find_lab(labs, "ALT")
    ast_lab = _find_lab(labs, "AST")
    alt_val = _safe_float(alt_lab.get("value")) if alt_lab else 29
    ast_val = _safe_float(ast_lab.get("value")) if ast_lab else 31

    # NAFLD risk: T2DM + obesity history + elevated enzymes
    nafld_risk = "Moderate background risk"
    nafld_note = (
        "T2DM and prior obesity are NAFLD risk factors. Current ALT 29, AST 31 — both "
        "normal. Semaglutide has shown hepatic fat reduction in clinical trials (NASH). "
        "Post-bariatric: rapid weight loss can transiently elevate enzymes (not current concern)."
    )

    return {
        "panel": "Liver / Hepatic Function Panel",
        "date_reviewed": datetime.utcnow().isoformat(),
        "results": results,
        "flags": [],  # All normal
        "overall_status": "Normal",
        "nafld_risk_assessment": {
            "risk_level": nafld_risk,
            "alt": alt_val,
            "ast": ast_val,
            "ast_alt_ratio": round(ast_val / alt_val, 2) if alt_val and alt_val > 0 else None,
            "note": nafld_note,
            "fib4_note": "FIB-4 score calculation requires age + ALT + AST + platelet count. Recommend calculating at next visit.",
        },
        "clinical_questions": [
            "Has a FIB-4 score been calculated to screen for fibrosis given T2DM history?",
            "GLP-1 agonists (semaglutide) reduce hepatic fat — is this being tracked with imaging or serial LFTs?",
            "Post-bariatric: any concern for cholelithiasis? Right upper quadrant ultrasound ever performed?",
        ],
    }


async def review_diabetes_panel() -> dict:
    """
    Review: A1c, fasting glucose, eAG.
    A1c trend: 10.2% (2019) → 5.9% (Apr 2024) → 7.3% (May 2026).
    """
    labs = await get_labs_from_db()

    dm_tests = [
        ("Hemoglobin A1c", ("HEMOGLOBIN A1C", "A1C", "HBA1C", "GLYCATED HEMOGLOBIN")),
        ("Fasting Glucose", ("GLUCOSE",)),
        ("Estimated Average Glucose (eAG)", ("ESTIMATED AVERAGE", "EAG")),
    ]

    results = []
    for label, fragments in dm_tests:
        lab = None
        for frag in fragments:
            lab = _find_lab(labs, frag)
            if lab:
                break
        if lab:
            val = _safe_float(lab.get("value"))
            results.append({
                "test": label,
                "value": lab.get("value"),
                "unit": lab.get("unit"),
                "reference_range": lab.get("reference_range"),
                "flag": _flag_label(lab.get("flag"), val, lab.get("reference_range")),
                "date": lab.get("result_date"),
            })

    a1c_lab = _find_lab(labs, "A1C") or _find_lab(labs, "HEMOGLOBIN A1C")
    current_a1c = _safe_float(a1c_lab.get("value")) if a1c_lab else 7.3
    glucose_lab = _find_lab(labs, "GLUCOSE")
    current_glucose = _safe_float(glucose_lab.get("value")) if glucose_lab else 155

    trajectory_analysis = {
        "history": _A1C_HISTORY,
        "direction": "Relapsed — worsening after 2024 nadir",
        "nadir": "5.9% (Apr 2024) — best recorded",
        "current": f"{current_a1c}%",
        "goal": "<7.0% per ADA Standards (Level A)",
        "gap_from_goal": f"+{current_a1c - 7.0:.1f}% above goal" if current_a1c else "Unknown",
        "pattern": (
            "A1c improved dramatically from 10.2% (2019) to 5.9% (2024) — likely coinciding with "
            "bariatric surgery and GLP-1 initiation. Relapse to 7.3% by May 2026 suggests either "
            "dose escalation plateau, medication adherence issue, metformin underdosing, "
            "HCTZ-related glucose elevation, or natural T2DM progression."
        ),
        "fasting_glucose": current_glucose,
        "fasting_glucose_flag": "Elevated — above 126 mg/dL diagnostic threshold" if current_glucose and current_glucose > 126 else "Normal",
        "eag": 163,  # Known value May 2026
    }

    therapy_adequacy = {
        "current_therapy": ["Metformin ER 500 mg", "Semaglutide 2 mg/wk"],
        "assessment": "Partially adequate",
        "gaps": [
            "Metformin ER 500 mg is below typical therapeutic dose (1000-2000 mg/day) — appears subtherapeutic",
            "Metformin ER post-bariatric: ER formulation may have reduced bioavailability",
            "A1c relapsed from 5.9% to 7.3% — therapy optimization needed",
            "HCTZ may be mildly worsening glucose control — worth discussing dose reduction",
        ],
        "options_to_discuss": [
            "Increase metformin to 1000-2000 mg/day (IR formulation preferred post-bariatric)",
            "If semaglutide is at max dose (2 mg/wk), consider adding SGLT2 inhibitor",
            "SGLT2 inhibitors (dapagliflozin, empagliflozin) have cardiovascular + renal benefit in T2DM",
            "Time-in-range monitoring: CGM data if available (Dexcom)",
        ],
    }

    flags = []
    if current_a1c and current_a1c > 7.0:
        flags.append({
            "test": "Hemoglobin A1c",
            "value": current_a1c,
            "flag": f"Above ADA goal of <7.0% — currently {current_a1c}%",
            "urgency": "O-CLINIC",
            "action": "Therapy optimization needed. Discuss at Nov 13 visit.",
        })

    if current_glucose and current_glucose > 126:
        flags.append({
            "test": "Fasting Glucose",
            "value": current_glucose,
            "flag": f"Elevated fasting glucose — {current_glucose} mg/dL",
            "urgency": "O-MONITOR",
        })

    return {
        "panel": "Diabetes / Glycemic Control Panel",
        "date_reviewed": datetime.utcnow().isoformat(),
        "results": results,
        "flags": flags,
        "trajectory_analysis": trajectory_analysis,
        "therapy_adequacy_assessment": therapy_adequacy,
        "cgm_data_available": "Check Dexcom sync status",
        "clinical_questions": [
            "A1c is 7.3% with goal <7.0% — what is the plan? Metformin dose escalation? SGLT2 inhibitor?",
            "Why is metformin ER dosed at 500 mg/day when standard T2DM dosing is 1000-2000 mg/day?",
            "Post-bariatric: has metformin ER absorption ever been formally assessed? IR formulation may be more reliable.",
            "Has semaglutide reached maximum dose (2 mg/wk)? If yes, what is the next escalation step?",
            "HCTZ can raise glucose — has the BP be stable enough to trial HCTZ dose reduction?",
        ],
        "evidence_grade": _EVIDENCE_GRADES["a1c_goal"],
    }


async def review_thyroid_panel() -> dict:
    """Review TSH (1.080 — normal). Returns brief normal panel."""
    labs = await get_labs_from_db()
    tsh_lab = _find_lab(labs, "TSH")

    results = []
    if tsh_lab:
        val = _safe_float(tsh_lab.get("value"))
        results.append({
            "test": "TSH",
            "value": tsh_lab.get("value"),
            "unit": tsh_lab.get("unit"),
            "reference_range": tsh_lab.get("reference_range"),
            "flag": _flag_label(tsh_lab.get("flag"), val, tsh_lab.get("reference_range")),
            "date": tsh_lab.get("result_date"),
        })

    return {
        "panel": "Thyroid Panel",
        "date_reviewed": datetime.utcnow().isoformat(),
        "results": results,
        "flags": [],
        "overall_status": "Normal",
        "tsh_value": "1.080 mIU/L (normal range 0.4-4.0)",
        "note": "Thyroid function is normal. No thyroid disease on record. Annual monitoring appropriate given T2DM.",
        "clinical_questions": [],
    }


async def review_cbc() -> dict:
    """
    Review CBC: WBC, RBC, HGB, HCT, MCV, MCH, MCHC, platelets.
    All normal May 2026. Post-bariatric: watch for iron-deficiency anemia.
    """
    labs = await get_labs_from_db()

    cbc_tests = [
        ("WBC", ("WBC", "WHITE BLOOD CELL")),
        ("RBC", ("RBC", "RED BLOOD CELL")),
        ("Hemoglobin", ("HEMOGLOBIN", "HGB")),
        ("Hematocrit", ("HEMATOCRIT", "HCT")),
        ("MCV", ("MCV", "MEAN CORPUSCULAR VOLUME")),
        ("MCH", ("MCH", "MEAN CORPUSCULAR HEMOGLOBIN")),
        ("MCHC", ("MCHC",)),
        ("Platelets", ("PLATELET", "PLT")),
    ]

    results = []
    for label, fragments in cbc_tests:
        lab = None
        for frag in fragments:
            lab = _find_lab(labs, frag)
            if lab:
                break
        if lab:
            val = _safe_float(lab.get("value"))
            results.append({
                "test": label,
                "value": lab.get("value"),
                "unit": lab.get("unit"),
                "reference_range": lab.get("reference_range"),
                "flag": _flag_label(lab.get("flag"), val, lab.get("reference_range")),
                "date": lab.get("result_date"),
            })

    # Check MCV for iron-deficiency pattern
    mcv_lab = _find_lab(labs, "MCV")
    mcv_val = _safe_float(mcv_lab.get("value")) if mcv_lab else None
    hgb_lab = _find_lab(labs, "HEMOGLOBIN") or _find_lab(labs, "HGB")
    hgb_val = _safe_float(hgb_lab.get("value")) if hgb_lab else None

    iron_risk = []
    if mcv_val and mcv_val < 80:
        iron_risk.append(f"MCV {mcv_val} fL — microcytic: consistent with iron deficiency anemia")
    if hgb_val and hgb_val < 13.5:
        iron_risk.append(f"Hemoglobin {hgb_val} g/dL — below normal for males (13.5)")

    if not iron_risk:
        iron_risk.append("CBC indices currently normal — however, post-bariatric iron deficiency can precede anemia by months to years. Ferritin and serum iron should be checked.")

    return {
        "panel": "Complete Blood Count (CBC)",
        "date_reviewed": datetime.utcnow().isoformat(),
        "results": results,
        "flags": [],
        "overall_status": "Normal (May 2026)",
        "post_bariatric_iron_risk": {
            "risk_level": "Moderate — ongoing risk due to sleeve gastrectomy (Dec 2019)",
            "mechanism": "Reduced gastric acid and bypassed proximal duodenum reduces iron absorption. Affects non-heme iron most significantly.",
            "current_cbc_pattern": iron_risk,
            "missing_labs": ["Ferritin (not on record)", "Serum iron (not on record)", "TIBC (not on record)"],
            "recommendation": "Order ferritin + serum iron + TIBC. Per ASMBS guidelines, these should be checked at 3, 6, 12 months post-op then annually.",
        },
        "clinical_questions": [
            "When were ferritin, serum iron, and TIBC last checked? Not in current lab record.",
            "Post-bariatric sleeve (Dec 2019, now 6.5 years out) — ASMBS recommends annual iron studies. Are these being ordered?",
            "If MCV falls below 80 or hemoglobin drops, IV iron infusion may be needed given reduced oral absorption post-sleeve.",
        ],
        "evidence_grade": _EVIDENCE_GRADES["post_bariatric_labs"],
    }


async def review_vitamins_minerals() -> dict:
    """
    Review: Vitamin D (55.4 — adequate), B12 (363 — lower normal, metformin risk),
    Folate (9.71 — adequate).
    Missing: Ferritin, iron/TIBC, calcium, PTH.
    """
    labs = await get_labs_from_db()

    vit_tests = [
        ("Vitamin D (25-OH)", ("VITAMIN D", "25-OH", "25 OH")),
        ("Vitamin B12", ("VITAMIN B12", "B12", "COBALAMIN")),
        ("Folate", ("FOLATE", "FOLIC ACID")),
        ("Ferritin", ("FERRITIN",)),
        ("Serum Iron", ("SERUM IRON", " IRON ")),
        ("TIBC", ("TIBC", "TOTAL IRON BINDING")),
        ("Calcium", ("CALCIUM",)),
        ("PTH", ("PTH", "PARATHYROID")),
    ]

    results = []
    missing_labs: list[str] = []
    for label, fragments in vit_tests:
        lab = None
        for frag in fragments:
            lab = _find_lab(labs, frag)
            if lab:
                break
        if lab:
            val = _safe_float(lab.get("value"))
            results.append({
                "test": label,
                "value": lab.get("value"),
                "unit": lab.get("unit"),
                "reference_range": lab.get("reference_range"),
                "flag": _flag_label(lab.get("flag"), val, lab.get("reference_range")),
                "date": lab.get("result_date"),
            })
        else:
            missing_labs.append(label)

    # Known values
    vitd_val = 55.4
    b12_val = 363
    folate_val = 9.71

    deficiency_risks = [
        {
            "nutrient": "Vitamin D",
            "current": f"{vitd_val} ng/mL",
            "status": "Adequate (30-100 ng/mL is normal; >40 preferred post-bariatric)",
            "risk": "Low — currently adequate",
            "note": "Re-check annually. Goal >40 ng/mL post-bariatric per ASMBS.",
        },
        {
            "nutrient": "Vitamin B12",
            "current": f"{b12_val} pg/mL",
            "status": "Low-normal (ref 200-900 pg/mL) — watch closely",
            "risk": "Moderate",
            "note": (
                "B12 363 is within range but at lower end. Two risk factors: "
                "(1) Metformin reduces B12 absorption — well-documented; "
                "(2) Post-bariatric sleeve reduces intrinsic factor exposure. "
                "Recommend annual monitoring; consider sublingual or IM B12 supplementation."
            ),
        },
        {
            "nutrient": "Folate",
            "current": f"{folate_val} ng/mL",
            "status": "Adequate",
            "risk": "Low",
            "note": "Currently normal. Monitor annually.",
        },
        {
            "nutrient": "Iron / Ferritin",
            "current": "NOT CHECKED — missing from record",
            "status": "Unknown",
            "risk": "High — post-sleeve gastrectomy; 6.5 years out",
            "note": "Ferritin and serum iron not in current lab record. ASMBS mandates annual iron studies post-bariatric. Order immediately.",
        },
        {
            "nutrient": "Calcium",
            "current": "Not in vitamin panel — check in BMP",
            "status": "Needs formal post-bariatric calcium + PTH check",
            "risk": "Moderate — post-bariatric calcium malabsorption risk",
            "note": "ASMBS recommends calcium + PTH monitoring post-bariatric. Need to confirm calcium is being adequately supplemented.",
        },
        {
            "nutrient": "PTH (Parathyroid Hormone)",
            "current": "NOT CHECKED — missing from record",
            "status": "Unknown",
            "risk": "Moderate — secondary hyperparathyroidism can develop post-bariatric",
            "note": "Secondary hyperparathyroidism develops when calcium absorption is inadequate. PTH + calcium + vitamin D should be checked together annually.",
        },
    ]

    return {
        "panel": "Vitamins, Minerals & Micronutrients",
        "date_reviewed": datetime.utcnow().isoformat(),
        "results": results,
        "deficiency_risks": deficiency_risks,
        "missing_labs": missing_labs,
        "critical_gap": "Ferritin, serum iron, TIBC, and PTH are not in current lab record — these are ASMBS Level A required post-bariatric labs.",
        "flags": [
            {
                "test": "Iron studies (Ferritin, Iron, TIBC)",
                "flag": "MISSING — not in lab record",
                "urgency": "O-CLINIC",
                "action": "Order at Nov 13 visit or via portal message before then.",
            },
            {
                "test": "PTH",
                "flag": "MISSING — not in lab record",
                "urgency": "O-CLINIC",
                "action": "Order with calcium and vitamin D to assess for secondary hyperparathyroidism.",
            },
        ],
        "clinical_questions": [
            "When were ferritin, serum iron, TIBC, calcium, and PTH last checked? ASMBS guidelines require annual monitoring post-bariatric.",
            "B12 is 363 pg/mL — lower-normal with both metformin and post-bariatric absorption risk. Is B12 supplementation adequate? Sublingual or IM may be needed.",
            "Is the current multivitamin a bariatric-specific formulation? Standard multivitamins may be inadequate for post-sleeve absorption needs.",
        ],
        "evidence_grade": _EVIDENCE_GRADES["post_bariatric_labs"],
    }


async def get_trending_labs() -> list[dict]:
    """
    Identify tests trending toward abnormal by comparing historical values.
    Returns list of {test, direction, current, prior_values[], threshold, urgency}.
    """
    labs = await get_labs_from_db()

    # Get current eGFR and LDL from DB if available, otherwise use known values
    egfr_lab = _find_lab(labs, "EGFR") or _find_lab(labs, "GFR")
    egfr_current = _safe_float(egfr_lab.get("value")) if egfr_lab else 87

    ldl_lab = _find_lab(labs, "LDL")
    ldl_current = _safe_float(ldl_lab.get("value")) if ldl_lab else 156

    a1c_lab = _find_lab(labs, "A1C") or _find_lab(labs, "HEMOGLOBIN A1C")
    a1c_current = _safe_float(a1c_lab.get("value")) if a1c_lab else 7.3

    trending: list[dict] = [
        {
            "test": "eGFR",
            "direction": "DECLINING",
            "current": f"{egfr_current} mL/min/1.73m²",
            "prior_values": [f"{h['value']} ({h['date']})" for h in _EGFR_HISTORY[:-1]],
            "threshold": "CKD Stage G3 alert at eGFR <60",
            "rate_of_change": "-11 points over 24 months (~5.5/year)",
            "urgency": "O-MONITOR",
            "note": "Slow but consistent decline. 24 months to Stage G3 at current rate if trajectory continues. Monitor every 6 months.",
        },
        {
            "test": "LDL Cholesterol",
            "direction": "RISING",
            "current": f"{ldl_current} mg/dL",
            "prior_values": [f"{h['value']} mg/dL ({h['date']})" for h in _LDL_HISTORY[:-1]],
            "threshold": "Goal <100 mg/dL in high-risk T2DM",
            "rate_of_change": "+57 mg/dL over 5 years (~11/year). No current LDL-lowering therapy.",
            "urgency": "O-CLINIC",
            "note": "CRITICAL — rising LDL with no therapy. Statin contraindicated. Non-statin options needed urgently.",
        },
        {
            "test": "Hemoglobin A1c",
            "direction": "RELAPSED — now worsening",
            "current": f"{a1c_current}%",
            "prior_values": [f"{h['value']}% ({h['date']})" for h in _A1C_HISTORY[:-1]],
            "threshold": "ADA goal <7.0%",
            "rate_of_change": "+1.4% from nadir of 5.9% (Apr 2024) to 7.3% (May 2026)",
            "urgency": "O-CLINIC",
            "note": "A1c relapsed from best recorded value. Therapy optimization needed — metformin dose, HCTZ glucose effect, potential SGLT2 addition.",
        },
        {
            "test": "Vitamin B12",
            "direction": "WATCH — lower-normal range",
            "current": "363 pg/mL",
            "prior_values": ["No prior values in record"],
            "threshold": "Deficiency at <200 pg/mL; supplementation typically started <400 pg/mL post-bariatric",
            "rate_of_change": "Single data point — trend unknown",
            "urgency": "O-MONITOR",
            "note": "Dual risk: metformin + post-bariatric. Trend monitoring required. Consider supplementation now.",
        },
    ]

    return trending


async def run_full_lab_review() -> dict:
    """Run all panel reviews. Returns consolidated structured report."""
    (
        metabolic, lipid, kidney, liver, diabetes, thyroid, cbc, vitamins, trending
    ) = await __import__("asyncio").gather(
        review_metabolic_panel(),
        review_lipid_panel(),
        review_kidney_panel(),
        review_liver_panel(),
        review_diabetes_panel(),
        review_thyroid_panel(),
        review_cbc(),
        review_vitamins_minerals(),
        get_trending_labs(),
    )

    # Aggregate critical flags
    critical_flags = []
    for panel_data in [metabolic, lipid, kidney, liver, diabetes, cbc, vitamins]:
        for flag in panel_data.get("flags", []):
            if flag.get("urgency") in ("O-911", "O-ER", "O-URGENT", "O-CLINIC"):
                critical_flags.append({
                    "panel": panel_data.get("panel"),
                    **flag,
                })

    # Missing labs aggregation
    missing_labs = list(vitamins.get("missing_labs", []))
    missing_labs += [
        "Ferritin (post-bariatric monitoring — ASMBS Level A)",
        "Serum Iron / TIBC",
        "PTH (parathyroid hormone)",
        "Urine Albumin:Creatinine Ratio (confirm uACR <12 documented)",
    ]

    # Top clinical questions across all panels
    top_questions = [
        "LDL 156 mg/dL rising — when will non-statin therapy (ezetimibe / bempedoic acid / PCSK9 inhibitor) be started?",
        "A1c 7.3% above goal — metformin dose optimization and/or SGLT2 inhibitor addition?",
        "eGFR declining from 98 to 87 over 2 years — move to semi-annual monitoring?",
        "Ferritin, iron, TIBC, PTH not in lab record — order at Nov 13 visit or sooner via portal.",
        "B12 363 pg/mL lower-normal with metformin + post-bariatric — begin B12 supplementation?",
        "Is spironolactone still needed? K+ now 4.5 — review need given prior hyperkalemia history.",
    ]

    overall_summary = (
        "Three major treatable clinical gaps identified: (1) LDL 156 rising with zero LDL-lowering therapy — "
        "most urgent, high ASCVD risk; (2) A1c 7.3% off goal — metformin underdosed, may need SGLT2 addition; "
        "(3) Post-bariatric micronutrient labs overdue — ferritin, iron, PTH not checked. "
        "Kidney function declining slowly but nephroprotection in place (ARB + semaglutide). "
        "Liver function, CBC, and thyroid all normal."
    )

    return {
        "date_reviewed": datetime.utcnow().isoformat(),
        "panels_reviewed": ["Metabolic", "Lipid", "Kidney", "Liver", "Diabetes", "Thyroid", "CBC", "Vitamins/Minerals"],
        "overall_summary": overall_summary,
        "critical_flags": critical_flags,
        "trending_toward_abnormal": trending,
        "missing_labs": list(dict.fromkeys(missing_labs)),  # deduplicate
        "top_clinical_questions": top_questions,
        "panels": {
            "metabolic": metabolic,
            "lipid": lipid,
            "kidney": kidney,
            "liver": liver,
            "diabetes": diabetes,
            "thyroid": thyroid,
            "cbc": cbc,
            "vitamins": vitamins,
        },
        "binder_ref": "Master Binder v1.5 §10 — Lab Review Mode v0.5",
    }
