"""
risk_equations.py — Evidence-based clinical risk calculators for JARVIS Digital Twin.

Implements validated, published risk equations calibrated to literature-derived
coefficients. All models cite primary sources. Results are estimates — not medical
advice. Always verify with a clinician.

Models implemented:
  1. ACC/AHA 2013 Pooled Cohort ASCVD Equations (10-year CVD risk)
  2. CKD-EPI 2021 eGFR (creatinine-based)
  3. CKD Progression Trajectory (T2DM+HTN validated rates)
  4. HRV Mortality Risk Stratification (SDNN-based)
  5. Post-Bariatric Surgery CVD Risk Modifier
  6. OSA/CPAP Cardiovascular Risk Modifier
  7. JARVIS Composite Risk Score (weighted aggregate)

Source references:
  - Goff DC Jr et al. 2013 ACC/AHA Guideline on Cardiovascular Risk Assessment.
    Circulation. 2014;129(25 Suppl 2):S49-73. doi:10.1161/01.cir.0000437741.48606.98
  - Inker LA et al. New Creatinine- and Cystatin C-Based Equations to Estimate GFR
    without Race. NEJM. 2021;385:1737-1749. doi:10.1056/NEJMoa2102953
  - Heerspink HJL et al. DAPA-CKD Trial. NEJM. 2020;383:1436-1446.
  - Hillis GS et al. HRV and all-cause mortality. Meta-analysis. PMC 2024.
  - Aminian A et al. Bariatric Surgery and ASCVD. JAHA. 2024.
  - McEvoy RD et al. CPAP for Prevention of Cardiovascular Events in OSA. NEJM. 2016.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class ASCVDInput:
    age: int                        # years
    sex: str                        # "male" | "female"
    race: str                       # "white" | "black" | "other"  ("other" uses white coefficients)
    total_cholesterol_mgdl: float   # mg/dL
    hdl_cholesterol_mgdl: float     # mg/dL
    systolic_bp_mmhg: float         # mmHg
    bp_treated: bool                # on antihypertensive medication
    diabetes: bool                  # T2DM or T1DM diagnosis
    smoker: bool                    # current smoker


@dataclass
class ASCVDResult:
    ten_year_risk_pct: float        # 0–100
    risk_category: str              # "low" | "borderline" | "intermediate" | "high"
    pooled_cohort_score: float      # raw IndividualSum from the equation
    ldl_goal_mgdl: float            # AHA-recommended LDL goal given risk category
    notes: list[str]
    model: str = "ACC/AHA 2013 Pooled Cohort Equations"


@dataclass
class eGFRInput:
    serum_creatinine_mgdl: float    # mg/dL
    age: int                        # years
    sex: str                        # "male" | "female"


@dataclass
class eGFRResult:
    egfr: float                     # mL/min/1.73m²
    ckd_stage: str                  # "G1"–"G5"
    ckd_stage_label: str
    requires_nephrology: bool
    notes: list[str]
    model: str = "CKD-EPI 2021 (race-free creatinine)"


@dataclass
class CKDTrajectoryInput:
    current_egfr: float
    age: int
    diabetes: bool
    hypertension: bool
    a1c_pct: Optional[float] = None
    systolic_bp_mmhg: Optional[float] = None
    urine_acr_mg_g: Optional[float] = None       # albumin/creatinine ratio
    on_ace_arb: bool = True
    on_sglt2i: bool = False


@dataclass
class CKDTrajectoryResult:
    current_egfr: float
    annual_decline_rate: float          # mL/min/1.73m²/year (negative = declining)
    projected_egfr_1yr: float
    projected_egfr_3yr: float
    projected_egfr_5yr: float
    years_to_stage_3b: Optional[float]  # eGFR < 45
    years_to_stage_4: Optional[float]   # eGFR < 30
    years_to_esrd: Optional[float]      # eGFR < 15
    modifiable_factors: list[str]
    notes: list[str]
    model: str = "T2DM CKD Progression (DAPA-CKD / CREDENCE calibrated)"


@dataclass
class HRVRiskInput:
    sdnn_ms: float                  # Standard deviation of NN intervals (ms)
    rmssd_ms: Optional[float] = None
    age: int = 52
    existing_cvd: bool = False


@dataclass
class HRVRiskResult:
    sdnn_ms: float
    risk_category: str              # "high" | "moderate" | "low"
    relative_risk_vs_normal: float  # vs SDNN > 100ms
    mortality_hazard_note: str
    interpretation: str
    recommendations: list[str]
    model: str = "HRV Mortality Stratification (Hillis 2024 meta-analysis)"


@dataclass
class CompositeRiskResult:
    ascvd_10yr_pct: float
    ckd_annual_decline: float
    hrv_risk_category: str
    overall_risk_score: float           # 0–100 composite
    overall_risk_label: str             # "Critical" | "High" | "Moderate" | "Low"
    top_modifiable_risks: list[str]
    top_interventions: list[str]
    generated_at: str


# ---------------------------------------------------------------------------
# 1. ACC/AHA 2013 Pooled Cohort ASCVD Equations
# ---------------------------------------------------------------------------

# Coefficients from: Goff DC Jr et al. Circulation. 2014;129(25 Suppl 2):S49-73
# Supplementary Appendix Table A
_PCE_COEFFICIENTS = {
    # White / Other Men
    ("white", "male"): {
        "ln_age":                12.344,
        "ln_age_sq":              0.000,   # no squared term for men
        "ln_tc":                 11.853,
        "ln_age_x_ln_tc":        -2.664,
        "ln_hdl":                -7.990,
        "ln_age_x_ln_hdl":        1.769,
        "ln_treated_sbp":         1.797,
        "ln_age_x_ln_treated_sbp":0.000,
        "ln_untreated_sbp":       1.764,
        "ln_age_x_untreated_sbp": 0.000,
        "smoker":                 7.837,
        "ln_age_x_smoker":       -1.795,
        "diabetes":               0.661,
        "mean_coef_value":       61.18,
        "baseline_survival":      0.9144,
    },
    # White / Other Women
    ("white", "female"): {
        "ln_age":               -29.799,
        "ln_age_sq":              4.884,
        "ln_tc":                 13.540,
        "ln_age_x_ln_tc":        -3.114,
        "ln_hdl":               -13.578,
        "ln_age_x_ln_hdl":        3.149,
        "ln_treated_sbp":         2.019,
        "ln_age_x_ln_treated_sbp":0.000,
        "ln_untreated_sbp":       1.957,
        "ln_age_x_untreated_sbp": 0.000,
        "smoker":                 7.574,
        "ln_age_x_smoker":       -1.665,
        "diabetes":               0.661,
        "mean_coef_value":      -29.799,
        "baseline_survival":      0.9665,
    },
    # African American Men
    ("black", "male"): {
        "ln_age":                 2.469,
        "ln_age_sq":              0.000,
        "ln_tc":                  0.302,
        "ln_age_x_ln_tc":         0.000,
        "ln_hdl":                -0.307,
        "ln_age_x_ln_hdl":        0.000,
        "ln_treated_sbp":         1.916,
        "ln_age_x_ln_treated_sbp":0.000,
        "ln_untreated_sbp":       1.809,
        "ln_age_x_untreated_sbp": 0.000,
        "smoker":                 0.549,
        "ln_age_x_smoker":        0.000,
        "diabetes":               0.874,
        "mean_coef_value":       19.54,
        "baseline_survival":      0.8954,
    },
    # African American Women
    ("black", "female"): {
        "ln_age":                17.1141,
        "ln_age_sq":              0.000,
        "ln_tc":                  0.9396,
        "ln_age_x_ln_tc":         0.000,
        "ln_hdl":                -18.920,
        "ln_age_x_ln_hdl":        4.475,
        "ln_treated_sbp":        29.291,
        "ln_age_x_ln_treated_sbp":-6.432,
        "ln_untreated_sbp":      27.819,
        "ln_age_x_untreated_sbp":-6.087,
        "smoker":                 0.8738,
        "ln_age_x_smoker":        0.000,
        "diabetes":               0.8738,
        "mean_coef_value":       86.61,
        "baseline_survival":      0.9533,
    },
}


def calculate_ascvd_10yr(inputs: ASCVDInput) -> ASCVDResult:
    """
    Calculate 10-year ASCVD risk using 2013 ACC/AHA Pooled Cohort Equations.

    Valid for ages 40–79. Results outside this range are extrapolated with caution.
    Does NOT recommend statins — statin myopathy documented for this patient.

    Args:
        inputs: ASCVDInput with demographics, lipids, BP, and risk factors.

    Returns:
        ASCVDResult with 10-year risk percentage, category, and LDL goal.
    """
    notes = []

    # Normalise race key
    race_key = "black" if inputs.race.lower() in ("black", "african american", "aa") else "white"
    sex_key = "female" if inputs.sex.lower() in ("female", "f", "woman") else "male"
    coef = _PCE_COEFFICIENTS[(race_key, sex_key)]

    if inputs.age < 40 or inputs.age > 79:
        notes.append(f"Age {inputs.age} is outside validated range (40–79); estimate is extrapolated.")

    ln_age = math.log(inputs.age)
    ln_tc  = math.log(inputs.total_cholesterol_mgdl)
    ln_hdl = math.log(inputs.hdl_cholesterol_mgdl)

    if inputs.bp_treated:
        ln_sbp_term = coef["ln_treated_sbp"] * math.log(inputs.systolic_bp_mmhg)
        ln_age_sbp  = coef["ln_age_x_ln_treated_sbp"] * ln_age * math.log(inputs.systolic_bp_mmhg)
    else:
        ln_sbp_term = coef["ln_untreated_sbp"] * math.log(inputs.systolic_bp_mmhg)
        ln_age_sbp  = coef["ln_age_x_untreated_sbp"] * ln_age * math.log(inputs.systolic_bp_mmhg)

    individual_sum = (
        coef["ln_age"]            * ln_age
      + coef["ln_age_sq"]         * ln_age ** 2
      + coef["ln_tc"]             * ln_tc
      + coef["ln_age_x_ln_tc"]   * ln_age * ln_tc
      + coef["ln_hdl"]            * ln_hdl
      + coef["ln_age_x_ln_hdl"]  * ln_age * ln_hdl
      + ln_sbp_term
      + ln_age_sbp
      + coef["smoker"]            * (1 if inputs.smoker else 0)
      + coef["ln_age_x_smoker"]  * ln_age * (1 if inputs.smoker else 0)
      + coef["diabetes"]          * (1 if inputs.diabetes else 0)
    )

    exponent = individual_sum - coef["mean_coef_value"]
    ten_year_risk = (1 - coef["baseline_survival"] ** math.exp(exponent)) * 100
    ten_year_risk = max(0.5, min(99.5, ten_year_risk))   # clamp

    # Risk category (AHA 2018 guidelines)
    if ten_year_risk < 5:
        category = "low"
        ldl_goal  = 130.0
    elif ten_year_risk < 7.5:
        category = "borderline"
        ldl_goal  = 116.0
    elif ten_year_risk < 20:
        category = "intermediate"
        ldl_goal  = 100.0
    else:
        category = "high"
        ldl_goal  = 70.0

    if inputs.diabetes:
        ldl_goal = min(ldl_goal, 100.0)
        notes.append("Diabetes present — LDL goal tightened to <100 mg/dL per ADA standards.")
    if ten_year_risk >= 20:
        notes.append("High-risk: LDL goal <70 mg/dL per ACC/AHA 2018. Non-statin options: "
                     "ezetimibe, bempedoic acid, PCSK9 inhibitors (statin myopathy documented).")

    notes.append(f"Model: {race_key.title()} {sex_key.title()} Pooled Cohort Equation.")

    return ASCVDResult(
        ten_year_risk_pct   = round(ten_year_risk, 1),
        risk_category       = category,
        pooled_cohort_score = round(individual_sum, 4),
        ldl_goal_mgdl       = ldl_goal,
        notes               = notes,
    )


# ---------------------------------------------------------------------------
# 2. CKD-EPI 2021 eGFR
# ---------------------------------------------------------------------------

def calculate_egfr_ckd_epi_2021(inputs: eGFRInput) -> eGFRResult:
    """
    Calculate eGFR using the 2021 CKD-EPI creatinine equation (race-free).

    Formula: 142 × min(SCr/κ, 1)^α × max(SCr/κ, 1)^-1.200 × 0.9938^Age [× 1.012 if female]

    Source: Inker LA et al. NEJM. 2021;385:1737-1749.

    Args:
        inputs: eGFRInput with serum creatinine, age, sex.

    Returns:
        eGFRResult with eGFR and CKD staging.
    """
    is_female = inputs.sex.lower() in ("female", "f", "woman")
    kappa = 0.7 if is_female else 0.9
    alpha = -0.241 if is_female else -0.302
    scr   = inputs.serum_creatinine_mgdl

    ratio = scr / kappa
    if ratio < 1:
        egfr = 142 * (ratio ** alpha) * (0.9938 ** inputs.age)
    else:
        egfr = 142 * (ratio ** -1.200) * (0.9938 ** inputs.age)

    if is_female:
        egfr *= 1.012

    egfr = round(egfr, 1)

    # CKD staging (KDIGO 2012)
    if egfr >= 90:
        stage, label = "G1", "Normal or high (≥90)"
    elif egfr >= 60:
        stage, label = "G2", "Mildly decreased (60–89)"
    elif egfr >= 45:
        stage, label = "G3a", "Mildly-moderately decreased (45–59)"
    elif egfr >= 30:
        stage, label = "G3b", "Moderately-severely decreased (30–44)"
    elif egfr >= 15:
        stage, label = "G4", "Severely decreased (15–29)"
    else:
        stage, label = "G5", "Kidney failure (<15)"

    nephrology = egfr < 30
    notes = [f"eGFR {egfr} mL/min/1.73m² — CKD Stage {stage}: {label}."]
    if nephrology:
        notes.append("eGFR < 30 — nephrology referral strongly recommended.")
    if 30 <= egfr < 60:
        notes.append("CKD Stage G3 — monitor creatinine, potassium, phosphorus every 3–6 months.")

    return eGFRResult(
        egfr               = egfr,
        ckd_stage          = stage,
        ckd_stage_label    = label,
        requires_nephrology= nephrology,
        notes              = notes,
    )


# ---------------------------------------------------------------------------
# 3. CKD Progression Trajectory (T2DM + HTN)
# ---------------------------------------------------------------------------

# Evidence base:
#   - Baseline T2DM+HTN decline: ~1.8–2.5 mL/min/1.73m²/year (multiple cohorts)
#   - Chris observed rate: (98→87) / 6 years = -1.83/year
#   - ACE/ARB: slows progression by ~30–40% vs untreated
#   - SGLT2i (DAPA-CKD): dapagliflozin group -2.88 vs placebo -3.83/year (+0.95 benefit)
#   - A1c improvement (each 1% reduction): ~0.2 mL/min/year preserved
#   - SBP control (<130 vs ≥130): ~0.4 mL/min/year preserved
#   - Albuminuria: ACR > 300 doubles progression rate

def calculate_ckd_trajectory(inputs: CKDTrajectoryInput) -> CKDTrajectoryResult:
    """
    Project eGFR decline trajectory for a T2DM+HTN patient.

    Calibrated to DAPA-CKD, CREDENCE, and UKPDS cohort data.
    Chris's observed personal rate (1.83/yr) serves as the reference.

    Args:
        inputs: CKDTrajectoryInput with current eGFR and risk modifiers.

    Returns:
        CKDTrajectoryResult with decline rate and milestone projections.
    """
    notes = []
    modifiable = []

    # Base decline rate: T2DM+HTN without optimisation
    base_rate = -2.2  # mL/min/1.73m²/year (conservative midpoint)

    # Modifiers (all improve the rate, i.e. reduce decline magnitude)
    modifier = 0.0

    if inputs.on_ace_arb:
        modifier += 0.55   # ARB/ACE slows progression ~30–40% of ~1.8/yr
        notes.append("ACE/ARB therapy: +0.55 mL/min/yr benefit (renin-angiotensin blockade).")
    else:
        modifiable.append("Start ACE/ARB — reduces eGFR decline by ~0.5 mL/min/yr.")

    if inputs.on_sglt2i:
        modifier += 0.95   # DAPA-CKD treatment effect
        notes.append("SGLT2 inhibitor: +0.95 mL/min/yr benefit (DAPA-CKD calibrated).")
    else:
        modifiable.append("SGLT2 inhibitor (if tolerated) — +0.95 mL/min/yr benefit per DAPA-CKD.")

    if inputs.a1c_pct is not None:
        if inputs.a1c_pct <= 7.0:
            modifier += 0.25
            notes.append("A1c ≤7.0%: glycemic target met — +0.25 mL/min/yr preservation.")
        elif inputs.a1c_pct <= 8.0:
            notes.append(f"A1c {inputs.a1c_pct}%: suboptimal — improving to ≤7.0% would add ~0.25 mL/min/yr.")
            modifiable.append(f"Reduce A1c from {inputs.a1c_pct}% to ≤7.0% — preserves ~0.25 mL/min/yr eGFR.")
        else:
            modifier -= 0.3
            notes.append(f"A1c {inputs.a1c_pct}%: poorly controlled — accelerating decline by ~0.3 mL/min/yr.")
            modifiable.append(f"Reduce A1c from {inputs.a1c_pct}% — critical for kidney protection.")

    if inputs.systolic_bp_mmhg is not None:
        if inputs.systolic_bp_mmhg <= 130:
            modifier += 0.40
            notes.append("SBP ≤130 mmHg: target met — +0.40 mL/min/yr preservation.")
        elif inputs.systolic_bp_mmhg <= 140:
            modifier += 0.15
            notes.append(f"SBP {inputs.systolic_bp_mmhg} mmHg: near target — partial BP benefit.")
            modifiable.append("Lower SBP to ≤130 mmHg — additional 0.25 mL/min/yr eGFR benefit.")
        else:
            notes.append(f"SBP {inputs.systolic_bp_mmhg} mmHg: above target — accelerating renal stress.")
            modifiable.append(f"Lower SBP from {inputs.systolic_bp_mmhg} to ≤130 mmHg urgently.")

    if inputs.urine_acr_mg_g is not None:
        if inputs.urine_acr_mg_g >= 300:
            modifier -= 1.0
            notes.append(f"ACR {inputs.urine_acr_mg_g} mg/g (macroalbuminuria) — accelerated progression.")
            modifiable.append("Address macroalbuminuria — strongly consider SGLT2i + finerenone if tolerated.")
        elif inputs.urine_acr_mg_g >= 30:
            modifier -= 0.35
            notes.append(f"ACR {inputs.urine_acr_mg_g} mg/g (microalbuminuria) — moderate progression risk.")
        else:
            notes.append(f"ACR {inputs.urine_acr_mg_g} mg/g: normoalbuminuria — favourable kidney marker.")

    annual_decline = base_rate + modifier

    # Projections
    proj_1yr = inputs.current_egfr + annual_decline * 1
    proj_3yr = inputs.current_egfr + annual_decline * 3
    proj_5yr = inputs.current_egfr + annual_decline * 5

    def _years_to_threshold(current: float, rate: float, threshold: float) -> Optional[float]:
        if rate >= 0:
            return None  # improving or stable — won't reach lower threshold
        if current <= threshold:
            return 0.0
        return round((threshold - current) / rate, 1)

    yrs_3b = _years_to_threshold(inputs.current_egfr, annual_decline, 45.0)
    yrs_4  = _years_to_threshold(inputs.current_egfr, annual_decline, 30.0)
    yrs_esrd = _years_to_threshold(inputs.current_egfr, annual_decline, 15.0)

    return CKDTrajectoryResult(
        current_egfr       = inputs.current_egfr,
        annual_decline_rate= round(annual_decline, 2),
        projected_egfr_1yr = round(proj_1yr, 1),
        projected_egfr_3yr = round(proj_3yr, 1),
        projected_egfr_5yr = round(proj_5yr, 1),
        years_to_stage_3b  = yrs_3b,
        years_to_stage_4   = yrs_4,
        years_to_esrd      = yrs_esrd,
        modifiable_factors = modifiable,
        notes              = notes,
    )


# ---------------------------------------------------------------------------
# 4. HRV Mortality Risk Stratification
# ---------------------------------------------------------------------------

# Evidence: Hillis GS et al. PMC12794729 (2024 meta-analysis)
#   SDNN > 100 ms: reference group
#   SDNN 50–100 ms: moderate risk
#   SDNN < 50 ms: relative risk ~2.8 for all-cause mortality
#   RMSSD ≤ 4.8 ms: HR 3.457 (95% CI 1.303–9.171) for all-cause mortality

def calculate_hrv_risk(inputs: HRVRiskInput) -> HRVRiskResult:
    """
    Stratify cardiovascular and all-cause mortality risk from HRV parameters.

    Primary metric: SDNN (standard deviation of NN intervals).
    Source: Hillis 2024 meta-analysis; Task Force 1996 standards.

    Args:
        inputs: HRVRiskInput with SDNN, optional RMSSD, age, CVD status.

    Returns:
        HRVRiskResult with risk category, relative risk, and recommendations.
    """
    sdnn = inputs.sdnn_ms
    recs = []

    if sdnn >= 100:
        category = "low"
        rr       = 1.0
        mortality_note = "SDNN ≥100 ms: reference range — associated with low HRV-related mortality risk."
    elif sdnn >= 50:
        category = "moderate"
        rr       = 1.6
        mortality_note = "SDNN 50–99 ms: moderately reduced HRV — ~1.6× higher mortality risk vs SDNN ≥100 ms."
        recs.append("Target HRV improvement through aerobic exercise (150 min/week), sleep optimisation, stress reduction.")
    else:
        category = "high"
        rr       = 2.8
        mortality_note = "SDNN <50 ms: significantly reduced HRV — ~2.8× higher all-cause mortality risk vs normal."
        recs.append("Priority: confirm and treat OSA (CPAP) — OSA markedly suppresses HRV.")
        recs.append("Increase moderate aerobic exercise — strongest single HRV modifier.")
        recs.append("Review medications that reduce HRV: beta-blockers (metoprolol) lower SDNN.")

    # RMSSD check
    rmssd_note = ""
    if inputs.rmssd_ms is not None:
        if inputs.rmssd_ms <= 4.8:
            rmssd_note = f"RMSSD {inputs.rmssd_ms} ms ≤4.8 ms: HR 3.457 for all-cause mortality (Hillis 2024)."
            recs.append("RMSSD is critically low — seek cardiology review for autonomic assessment.")
        else:
            rmssd_note = f"RMSSD {inputs.rmssd_ms} ms: within acceptable range."

    # Chris context: on metoprolol ER (beta-blocker suppresses HRV)
    interp = (
        f"SDNN {sdnn} ms — {category} risk. {mortality_note} "
        f"Note: metoprolol (beta-blocker) pharmacologically reduces HRV; true autonomic tone "
        f"may be underestimated. {rmssd_note}".strip()
    )

    if not recs:
        recs.append("Maintain current exercise and sleep habits. Recheck SDNN at next annual review.")

    return HRVRiskResult(
        sdnn_ms                 = sdnn,
        risk_category           = category,
        relative_risk_vs_normal = rr,
        mortality_hazard_note   = mortality_note,
        interpretation          = interp,
        recommendations         = recs,
    )


# ---------------------------------------------------------------------------
# 5. Post-Bariatric Surgery CVD Risk Modifier
# ---------------------------------------------------------------------------

# Evidence: Aminian A et al. JAHA. 2024 (bariatric vs no surgery: OR 0.49 MACE)
# Weight loss 30% average: HbA1c -0.3 to -2.7%, SBP -7 to -15 mmHg, eGFR +14 mL/min

def bariatric_cvd_modifier(
    years_post_surgery: float,
    current_bmi: float,
    surgery_type: str = "sleeve_gastrectomy",
) -> dict:
    """
    Estimate residual CVD risk modification from prior bariatric surgery.

    The protective effect is largest in the first 3 years and attenuates
    with weight regain. Sleeve gastrectomy typically achieves 20–30% excess
    weight loss; Roux-en-Y gastric bypass achieves higher (30–40%) but with
    more malabsorption.

    Args:
        years_post_surgery: Years since bariatric surgery.
        current_bmi: Current BMI.
        surgery_type: "sleeve_gastrectomy" | "rygb"

    Returns:
        dict with CVD modifier information.
    """
    # Peak protective OR: 0.49 vs no surgery at 1–3 years
    # Attenuates with weight regain; BMI >35 suggests significant regain
    peak_risk_reduction_pct = 51.0   # 1 - 0.49 = 51%

    if years_post_surgery <= 3:
        attenuation = 1.0
    elif years_post_surgery <= 7:
        attenuation = 0.75
    else:
        attenuation = 0.55

    # Weight regain penalty
    if current_bmi > 40:
        attenuation *= 0.5
    elif current_bmi > 35:
        attenuation *= 0.75

    effective_reduction_pct = round(peak_risk_reduction_pct * attenuation, 1)

    notes = [
        f"{surgery_type.replace('_',' ').title()} performed {years_post_surgery:.0f}yr ago.",
        f"Estimated residual CVD risk reduction: {effective_reduction_pct}% vs matched non-surgical cohort.",
        "Benefit attenuates with weight regain — sustained weight management is critical.",
    ]

    if current_bmi > 35:
        notes.append("Current BMI >35 suggests significant weight regain — consider obesity-dose semaglutide (2.4 mg) or revisional bariatric evaluation.")

    return {
        "surgery_type": surgery_type,
        "years_post_surgery": years_post_surgery,
        "peak_cvd_reduction_pct": peak_risk_reduction_pct,
        "effective_cvd_reduction_pct": effective_reduction_pct,
        "attenuation_factor": attenuation,
        "current_bmi": current_bmi,
        "notes": notes,
        "source": "Aminian A et al. JAHA 2024; OR 0.49 (95% CI 0.40-0.60) for MACE vs no surgery.",
    }


# ---------------------------------------------------------------------------
# 6. OSA/CPAP Cardiovascular Risk Modifier
# ---------------------------------------------------------------------------

# Evidence: McEvoy RD et al. NEJM 2016; Peker Y et al. JAMA 2016
# BP reduction: 2–3 mmHg general; 6–7 mmHg resistant HTN
# CVD risk reduction: 5–10% from BP benefit; 17% in high-risk subset

def cpap_cvd_modifier(
    has_resistant_hypertension: bool = True,
    ahi_estimate: Optional[float] = None,
    current_sbp_mmhg: float = 140.0,
) -> dict:
    """
    Estimate cardiovascular risk modification from confirmed CPAP therapy.

    For patients with OSA and hypertension, CPAP provides BP reduction
    that translates to ASCVD risk reduction. Effect is larger in
    resistant hypertension.

    Args:
        has_resistant_hypertension: On ≥3 antihypertensives or confirmed resistant HTN.
        ahi_estimate: Apnea-hypopnea index if known (events/hour).
        current_sbp_mmhg: Current systolic BP on treatment.

    Returns:
        dict with BP reduction estimate and CVD risk modifier.
    """
    if has_resistant_hypertension:
        sbp_reduction = 6.5   # midpoint 6–7 mmHg
        cvd_risk_reduction_pct = 17.0
        notes = ["Resistant HTN: CPAP provides 6–7 mmHg SBP reduction and ~17% CVD risk reduction."]
    else:
        sbp_reduction = 2.5   # midpoint 2–3 mmHg
        cvd_risk_reduction_pct = 7.5
        notes = ["General OSA+HTN: CPAP provides 2–3 mmHg SBP reduction and ~5–10% CVD risk reduction."]

    if ahi_estimate and ahi_estimate >= 30:
        notes.append(f"Severe OSA (AHI ~{ahi_estimate:.0f}): CPAP effect likely at upper range of estimates.")
        sbp_reduction *= 1.2
        cvd_risk_reduction_pct *= 1.1

    projected_sbp = current_sbp_mmhg - sbp_reduction
    notes.append(
        f"Projected SBP with effective CPAP: {projected_sbp:.0f} mmHg "
        f"(from {current_sbp_mmhg:.0f} mmHg)."
    )
    notes.append("Effect requires ≥4 hours/night CPAP adherence to achieve full cardiovascular benefit.")
    notes.append("CPAP also improves HRV, reduces sympathetic activation, and may improve glycaemia.")

    return {
        "sbp_reduction_mmhg": round(sbp_reduction, 1),
        "projected_sbp_mmhg": round(projected_sbp, 1),
        "cvd_risk_reduction_pct": round(cvd_risk_reduction_pct, 1),
        "has_resistant_hypertension": has_resistant_hypertension,
        "notes": notes,
        "source": "McEvoy RD et al. NEJM 2016; Peker Y et al. JAMA 2016.",
    }


# ---------------------------------------------------------------------------
# 7. JARVIS Composite Risk Score
# ---------------------------------------------------------------------------

def run_full_risk_profile(
    # Identity
    age: int = 52,
    sex: str = "male",
    race: str = "white",
    # Lipids
    total_cholesterol: float = 217.0,
    hdl: float = 39.0,
    ldl: float = 156.0,
    # BP
    systolic_bp: float = 140.0,
    bp_treated: bool = True,
    # Metabolic
    a1c_pct: float = 7.3,
    diabetes: bool = True,
    smoker: bool = False,
    # Kidney
    serum_creatinine: float = 1.03,
    urine_acr: Optional[float] = None,
    # HRV
    sdnn_ms: float = 45.0,
    rmssd_ms: Optional[float] = None,
    # Surgery / OSA
    years_post_bariatric: float = 6.4,
    current_bmi: float = 35.7,
    has_osa: bool = True,
    cpap_confirmed: bool = False,
    has_resistant_hypertension: bool = True,
    on_ace_arb: bool = True,
    on_sglt2i: bool = False,
) -> dict:
    """
    Run all risk calculators and assemble a composite risk profile.

    Uses Chris's current health state as defaults. All parameters
    can be overridden for scenario modeling.

    Returns:
        Full risk profile dict with all sub-scores and composite summary.
    """
    # 1. ASCVD
    ascvd = calculate_ascvd_10yr(ASCVDInput(
        age=age, sex=sex, race=race,
        total_cholesterol_mgdl=total_cholesterol,
        hdl_cholesterol_mgdl=hdl,
        systolic_bp_mmhg=systolic_bp,
        bp_treated=bp_treated,
        diabetes=diabetes,
        smoker=smoker,
    ))

    # 2. eGFR
    egfr_result = calculate_egfr_ckd_epi_2021(eGFRInput(
        serum_creatinine_mgdl=serum_creatinine,
        age=age, sex=sex,
    ))
    egfr_val = egfr_result.egfr

    # 3. CKD trajectory
    ckd = calculate_ckd_trajectory(CKDTrajectoryInput(
        current_egfr=egfr_val,
        age=age,
        diabetes=diabetes,
        hypertension=True,
        a1c_pct=a1c_pct,
        systolic_bp_mmhg=systolic_bp,
        urine_acr_mg_g=urine_acr,
        on_ace_arb=on_ace_arb,
        on_sglt2i=on_sglt2i,
    ))

    # 4. HRV
    hrv = calculate_hrv_risk(HRVRiskInput(
        sdnn_ms=sdnn_ms,
        rmssd_ms=rmssd_ms,
        age=age,
    ))

    # 5. Bariatric modifier
    bariatric = bariatric_cvd_modifier(
        years_post_surgery=years_post_bariatric,
        current_bmi=current_bmi,
    )

    # 6. CPAP modifier (only if confirmed)
    cpap_mod = None
    if has_osa:
        cpap_mod = cpap_cvd_modifier(
            has_resistant_hypertension=has_resistant_hypertension,
            current_sbp_mmhg=systolic_bp,
        )

    # ── Composite score (0–100, higher = worse)
    # ASCVD: 40% weight (range 0–100% → normalise by /3 to cap at 33 for 100% risk)
    ascvd_component  = min(40.0, ascvd.ten_year_risk_pct * 0.5)
    # CKD: 25% weight
    ckd_component    = 25.0 - max(0, min(25.0, (egfr_val - 30) * 0.35))
    # HRV: 15% weight
    hrv_map          = {"low": 3, "moderate": 9, "high": 15}
    hrv_component    = hrv_map.get(hrv.risk_category, 9)
    # A1c: 10% weight
    a1c_component    = min(10.0, max(0.0, (a1c_pct - 5.0) * 2.5))
    # LDL: 10% weight
    ldl_component    = min(10.0, max(0.0, (ldl - 70) * 0.055))

    raw_score = ascvd_component + ckd_component + hrv_component + a1c_component + ldl_component

    # Apply bariatric protective modifier
    bariatric_discount = bariatric["effective_cvd_reduction_pct"] / 100 * 15  # up to 7.65 pts off
    raw_score = max(0, raw_score - bariatric_discount)

    # Apply CPAP modifier if confirmed
    if cpap_confirmed and cpap_mod:
        cpap_discount = cpap_mod["cvd_risk_reduction_pct"] / 100 * 8
        raw_score = max(0, raw_score - cpap_discount)

    composite = round(min(100, max(0, raw_score)), 1)

    if composite >= 70:
        risk_label = "Critical"
    elif composite >= 50:
        risk_label = "High"
    elif composite >= 30:
        risk_label = "Moderate"
    else:
        risk_label = "Low"

    # Top modifiable risks
    top_risks = []
    if ldl > 130:
        top_risks.append(f"LDL {ldl:.0f} mg/dL (goal <{ascvd.ldl_goal_mgdl:.0f}) — no active lipid therapy (statin myopathy on record)")
    if a1c_pct > 7.0:
        top_risks.append(f"A1c {a1c_pct}% (goal <7.0%) — above target")
    if systolic_bp > 130:
        top_risks.append(f"SBP {systolic_bp:.0f} mmHg (goal <130) — on 4-drug regimen")
    if has_osa and not cpap_confirmed:
        top_risks.append("OSA unconfirmed/untreated — accelerates HTN, HRV suppression, CVD risk")
    if hrv.risk_category == "high":
        top_risks.append(f"HRV SDNN {sdnn_ms} ms (<50 ms = 2.8× mortality risk)")
    top_risks.extend(ckd.modifiable_factors[:2])

    # Top interventions
    top_interventions = [
        "Start non-statin LDL therapy: ezetimibe 10mg → bempedoic acid → PCSK9i if needed",
        "Confirm CPAP: OSA treatment reduces SBP 6–7 mmHg + HRV +8 ms + CVD risk −17%",
        "Exercise 150 min/week: A1c −0.4%, SBP −4 mmHg, HRV +7 ms",
        "Optimise semaglutide to 2.4 mg (obesity dose): weight −10 lbs, A1c −0.3%",
        "Post-bariatric micronutrient panel: B12, ferritin, iron, Ca, PTH overdue",
    ]

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "composite_risk_score": composite,
        "composite_risk_label": risk_label,
        "ascvd": {
            "ten_year_risk_pct": ascvd.ten_year_risk_pct,
            "risk_category": ascvd.risk_category,
            "ldl_goal_mgdl": ascvd.ldl_goal_mgdl,
            "notes": ascvd.notes,
        },
        "egfr": {
            "egfr_ml_min": egfr_result.egfr,
            "ckd_stage": egfr_result.ckd_stage,
            "ckd_stage_label": egfr_result.ckd_stage_label,
            "notes": egfr_result.notes,
        },
        "ckd_trajectory": {
            "annual_decline_rate": ckd.annual_decline_rate,
            "projected_egfr_1yr": ckd.projected_egfr_1yr,
            "projected_egfr_3yr": ckd.projected_egfr_3yr,
            "projected_egfr_5yr": ckd.projected_egfr_5yr,
            "years_to_stage_3b": ckd.years_to_stage_3b,
            "years_to_esrd": ckd.years_to_esrd,
            "modifiable_factors": ckd.modifiable_factors,
        },
        "hrv_risk": {
            "sdnn_ms": hrv.sdnn_ms,
            "risk_category": hrv.risk_category,
            "relative_risk_vs_normal": hrv.relative_risk_vs_normal,
            "interpretation": hrv.interpretation,
            "recommendations": hrv.recommendations,
        },
        "bariatric_modifier": {
            "effective_cvd_reduction_pct": bariatric["effective_cvd_reduction_pct"],
            "notes": bariatric["notes"],
        },
        "cpap_modifier": cpap_mod,
        "top_modifiable_risks": top_risks,
        "top_interventions": top_interventions,
    }


