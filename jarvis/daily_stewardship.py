"""
JARVIS Daily Stewardship Engine
Based on Helen Cho Master Binder v1.5 — File 08: Daily Stewardship Mode

Day Types: Medical Attention | Recovery | Maintain | Push | Constraint

Routes (registered in service.py):
  POST /api/health/stewardship/morning   — morning check-in, returns day card
  POST /api/health/stewardship/evening   — evening review
  GET  /api/health/stewardship/today     — current day card (from cache)
  GET  /api/health/stewardship/history   — last 7 days of check-ins
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

from .persistence import append_jsonl, atomic_write_json

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths & constants
# ---------------------------------------------------------------------------

_DAY_CARD_PATH = Path.home() / ".jarvis" / "health" / "day_card.json"
_DAY_CARD_PATH.parent.mkdir(parents=True, exist_ok=True)
_DAY_CARD_LOG_PATH = _DAY_CARD_PATH.with_name("day_card_log.jsonl")
_DAY_CARD_STATE_LOG_PATH = _DAY_CARD_PATH.with_name("day_card_state_log.jsonl")

_COUNCIL_CACHE_PATH = Path.home() / ".jarvis" / "health" / "council_cache.json"
_COUNCIL_CACHE_TTL_HOURS = 6

# Day type constants
DAY_TYPES = {
    "Medical Attention": "Oracle has flagged something requiring clinical contact today.",
    "Recovery": "Body signals demand rest — take it easy and prioritise sleep.",
    "Maintain": "Normal day; hold habits, no particular push or constraint.",
    "Push": "Strong readiness — capacity to exceed baseline exercise/nutrition targets.",
    "Constraint": "External limits today — adapt expectations, don't abandon habits.",
}

# Chris's profile for LLM prompts
_CHRIS_PROFILE = """
Patient: Chris Binion | Male, 52 | T2DM (A1c 7.3%) | Hypertension (BP ~140/90 on 4 meds)
Active meds: semaglutide, metformin, olmesartan/HCTZ, amlodipine, metoprolol, spironolactone
SAFETY FLAG: NO STATINS EVER — statin myopathy on record
Surgery: sleeve gastrectomy Dec 2019 (bariatric)
Top goals: A1c <7% | LDL management without statins | BP control | Weight maintenance | Sleep quality
Current LDL: 156 mg/dL (elevated, no lipid therapy)
""".strip()

def _current_season() -> str:
    """Return current Northern Hemisphere season by calendar month."""
    month = date.today().month
    if month in (12, 1, 2):
        return "winter"
    if month in (3, 4, 5):
        return "spring"
    if month in (6, 7, 8):
        return "summer"
    return "autumn"


# ---------------------------------------------------------------------------
# Signal retrieval
# ---------------------------------------------------------------------------

async def get_morning_signals() -> dict:
    """Pull today's readiness signals from DB: sleep, HRV, RHR, glucose, steps from yesterday."""
    try:
        try:
            from .health_db import get_latest_metrics, get_latest_glucose, get_latest_bp
        except ImportError:
            from health_db import get_latest_metrics, get_latest_glucose, get_latest_bp

        # Fetch last 2 days of metrics (today may be empty, yesterday has yesterday's data)
        metrics_list = await get_latest_metrics(days=2)
        latest_metrics: dict = metrics_list[0] if metrics_list else {}

        # Latest glucose reading
        glucose_row = await get_latest_glucose()
        latest_glucose = glucose_row.get("glucose_mgdl") if glucose_row else None

        # Latest BP
        bp_row = await get_latest_bp()

        signals = {
            "sleep_hours": latest_metrics.get("sleep_hours"),
            "hrv": latest_metrics.get("hrv"),
            "resting_hr": latest_metrics.get("resting_hr"),
            "latest_glucose": latest_glucose,
            "steps_yesterday": latest_metrics.get("steps"),
            "exercise_min": latest_metrics.get("exercise_min"),
            "date_of_metrics": latest_metrics.get("date"),
        }

        if bp_row:
            signals["bp_systolic"] = bp_row.get("systolic")
            signals["bp_diastolic"] = bp_row.get("diastolic")

        # Remove None values so callers can check key presence
        signals = {k: v for k, v in signals.items() if v is not None}

        log.info("Morning signals: %s", signals)
        return signals

    except Exception as exc:
        log.warning("Could not fetch morning signals: %s", exc)
        return {}


# ---------------------------------------------------------------------------
# Day type classification
# ---------------------------------------------------------------------------

async def classify_day_type(signals: dict, oracle_pathway: str) -> dict:
    """
    Classify the day type based on signals + Oracle pathway.

    Priority order:
    1. If oracle_pathway in (O-911, O-ER, O-URGENT) → Medical Attention
    2. If sleep < 6.0 OR hrv < 30 OR rhr > 72 → Recovery
    3. If sleep >= 7.5 AND hrv >= 50 AND rhr <= 60 → Push
    4. Else → Maintain
    (Constraint is set manually — default to Maintain if no constraint signal)

    Returns: {day_type, reason, readiness_score (0-100), signals_used}
    """
    sleep = signals.get("sleep_hours")
    hrv = signals.get("hrv")
    rhr = signals.get("resting_hr")
    glucose = signals.get("latest_glucose")

    signals_used: list[str] = []

    # --- Step 1: Oracle override ---
    if oracle_pathway in ("O-911", "O-ER", "O-URGENT"):
        return {
            "day_type": "Medical Attention",
            "reason": f"Oracle flagged {oracle_pathway} — clinical contact required today.",
            "readiness_score": 0,
            "signals_used": ["oracle_pathway"],
        }

    # --- Step 2: Recovery triggers ---
    recovery_reasons: list[str] = []
    if sleep is not None and sleep < 6.0:
        recovery_reasons.append(f"sleep {sleep:.1f}h (< 6h threshold)")
        signals_used.append("sleep_hours")
    if hrv is not None and hrv < 30:
        recovery_reasons.append(f"HRV {hrv:.0f} (< 30 threshold)")
        signals_used.append("hrv")
    if rhr is not None and rhr > 72:
        recovery_reasons.append(f"RHR {rhr:.0f} bpm (> 72 threshold)")
        signals_used.append("resting_hr")

    if recovery_reasons:
        # Readiness score: penalise proportionally
        score = 40
        if sleep is not None:
            sleep_score = min(1.0, sleep / 8.0) * 30
            score = int(sleep_score + 10)
        return {
            "day_type": "Recovery",
            "reason": "Low readiness: " + "; ".join(recovery_reasons),
            "readiness_score": max(10, score),
            "signals_used": signals_used,
        }

    # --- Step 3: Push triggers ---
    push_conditions: list[str] = []
    if sleep is not None and sleep >= 7.5:
        push_conditions.append(f"sleep {sleep:.1f}h")
        signals_used.append("sleep_hours")
    if hrv is not None and hrv >= 50:
        push_conditions.append(f"HRV {hrv:.0f}")
        signals_used.append("hrv")
    if rhr is not None and rhr <= 60:
        push_conditions.append(f"RHR {rhr:.0f} bpm")
        signals_used.append("resting_hr")

    if len(push_conditions) == 3:
        # All three push conditions met
        readiness = 85
        if sleep is not None:
            readiness += min(10, int((sleep - 7.5) * 10))
        if hrv is not None:
            readiness += min(5, int((hrv - 50) / 5))
        return {
            "day_type": "Push",
            "reason": "Strong readiness: " + ", ".join(push_conditions),
            "readiness_score": min(99, readiness),
            "signals_used": signals_used,
        }

    # --- Step 4: Maintain (default) ---
    # Compute a moderate readiness score
    score_parts = []
    if sleep is not None:
        score_parts.append(min(35, int(sleep / 8.0 * 35)))
        signals_used.append("sleep_hours")
    if hrv is not None:
        score_parts.append(min(25, int(hrv / 70.0 * 25)))
        signals_used.append("hrv")
    if rhr is not None:
        # Lower RHR = better; 45=best, 80=worst
        rhr_score = max(0, min(20, int((80 - rhr) / (80 - 45) * 20)))
        score_parts.append(rhr_score)
        signals_used.append("resting_hr")

    readiness = int(sum(score_parts) * 100 / (35 + 25 + 20)) if score_parts else 65

    # Penalise elevated glucose slightly
    if glucose is not None and glucose > 180:
        readiness = max(40, readiness - 10)
        signals_used.append("latest_glucose")

    return {
        "day_type": "Maintain",
        "reason": "Normal readiness — hold habits, no push or constraint.",
        "readiness_score": max(50, min(84, readiness)),
        "signals_used": list(set(signals_used)),
    }


# ---------------------------------------------------------------------------
# Three Moves generation
# ---------------------------------------------------------------------------

async def generate_three_moves(day_type: str, signals: dict, health_state: dict, season: str = "") -> list[dict]:
    """
    Use LLM (via Oracle's gateway) to generate Today's Three Moves.
    Each move: {move, why, effort_level (low/medium/high), domain (glucose/bp/sleep/nutrition/movement/mindset)}
    """
    try:
        try:
            from .llm_gateway import get_gateway, LLMMessage
        except ImportError:
            from llm_gateway import get_gateway, LLMMessage

        gw = get_gateway()
        if gw is None:
            log.warning("LLM gateway unavailable — using fallback Three Moves")
            return _fallback_three_moves(day_type, signals, season=season)

        today = date.today().isoformat()
        signal_lines = []
        if signals.get("sleep_hours") is not None:
            signal_lines.append(f"  Sleep last night: {signals['sleep_hours']:.1f} hours")
        if signals.get("hrv") is not None:
            signal_lines.append(f"  HRV: {signals['hrv']:.0f} ms")
        if signals.get("resting_hr") is not None:
            signal_lines.append(f"  Resting HR: {signals['resting_hr']:.0f} bpm")
        if signals.get("latest_glucose") is not None:
            signal_lines.append(f"  Latest glucose: {signals['latest_glucose']} mg/dL")
        if signals.get("steps_yesterday") is not None:
            signal_lines.append(f"  Steps yesterday: {signals['steps_yesterday']:,}")
        if signals.get("bp_systolic") and signals.get("bp_diastolic"):
            signal_lines.append(f"  BP: {signals['bp_systolic']}/{signals['bp_diastolic']} mmHg")

        system_prompt = """You are JARVIS's Daily Stewardship Engine. Your job is to generate exactly THREE high-leverage health actions for Chris today.
Each move must be specific, actionable, and matched to the day type and current signals.
Respond ONLY with valid JSON — an array of exactly 3 move objects.
Each object: {"move": "<action>", "why": "<one sentence reason>", "effort_level": "<low|medium|high>", "domain": "<glucose|bp|sleep|nutrition|movement|mindset>"}"""

        season_line = f"Season: {season.capitalize()}" if season else ""
        user_prompt = f"""Today: {today}
Day Type: {day_type}
{season_line}

Chris's profile:
{_CHRIS_PROFILE}

Today's readiness signals:
{chr(10).join(signal_lines) if signal_lines else '  No wearable data available today.'}

Generate Today's Three Moves — exactly 3 specific health actions matched to this day type and season.
For {day_type} day:
- Recovery: gentle movement only, protein focus, sleep hygiene
- Push: resistance training, time-restricted eating, bonus activity
- Maintain: standard habit stack, glucose management, consistent routine
- Medical Attention: minimum exertion, prepare for clinical contact
- Constraint: adapted moves that work around external limits
{f"Season context ({season}): tailor movement suggestions to seasonal conditions (indoor/outdoor, temperature, daylight)." if season else ""}

Return ONLY a JSON array of exactly 3 move objects."""

        response = await asyncio.to_thread(
            gw.complete,
            messages=[
                LLMMessage("system", system_prompt),
                LLMMessage("user", user_prompt),
            ],
            task_type="standard",
            agent_id="daily-stewardship",
            max_tokens=600,
            temperature=0.3,
        )

        if response.error:
            log.warning("Three Moves LLM error: %s", response.error)
            return _fallback_three_moves(day_type, signals)

        raw = response.text.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        try:
            moves = json.loads(raw)
            if isinstance(moves, list) and len(moves) == 3:
                return moves
        except json.JSONDecodeError:
            # Try to extract JSON array
            m = re.search(r"\[.*\]", raw, re.DOTALL)
            if m:
                try:
                    moves = json.loads(m.group(0))
                    if isinstance(moves, list) and len(moves) >= 3:
                        return moves[:3]
                except Exception:
                    pass

        log.warning("Could not parse Three Moves from LLM — using fallback")
        return _fallback_three_moves(day_type, signals, season=season)

    except Exception as exc:
        log.error("generate_three_moves failed: %s", exc)
        return _fallback_three_moves(day_type, signals, season=season)


def _fallback_three_moves(day_type: str, signals: dict, season: str = "") -> list[dict]:
    """Hardcoded fallback moves when LLM is unavailable."""
    glucose = signals.get("latest_glucose", 150)
    _s = (season or "").lower()

    # Season-appropriate movement suggestions
    _recovery_move = {
        "winter": "20-minute indoor walk or light yoga — no more",
        "spring": "20-minute gentle outdoor walk in the fresh air — no more",
        "summer": "20-minute morning walk before the heat builds — no more",
        "autumn": "20-minute outdoor walk while the weather holds — no more",
    }.get(_s, "20-minute gentle walk — no more")

    _push_move = {
        "winter": "Resistance training session — 30-45 min, full body (indoor gym or home)",
        "spring": "Resistance training or outdoor circuit — 30-45 min, full body",
        "summer": "Early-morning resistance training (before heat) — 30-45 min, full body",
        "autumn": "Resistance training session — 30-45 min, full body",
    }.get(_s, "Resistance training session — 30-45 min, full body")

    _push_bonus = {
        "winter": "Short post-dinner indoor walk (15-20 min) — blunts glucose spike without cold exposure",
        "spring": "Evening walk after dinner (20-30 min) — great weather for it",
        "summer": "Short post-dinner indoor walk or light stretching — skip outdoor heat after 6pm",
        "autumn": "Evening walk after dinner (20-30 min) — crisp air, ideal glucose-blunting conditions",
    }.get(_s, "Evening walk after dinner (20-30 min)")

    if day_type == "Recovery":
        return [
            {"move": _recovery_move, "why": "Light movement aids recovery without taxing a fatigued system.", "effort_level": "low", "domain": "movement"},
            {"move": "High-protein breakfast — eggs, Greek yogurt, or cottage cheese", "why": "Protein stabilises glucose and supports muscle recovery.", "effort_level": "low", "domain": "nutrition"},
            {"move": "Lights out by 9:30pm tonight", "why": "Sleep debt compounds — an early night is the single best recovery move.", "effort_level": "medium", "domain": "sleep"},
        ]
    elif day_type == "Push":
        return [
            {"move": _push_move, "why": "High readiness is the window for strength work that preserves muscle on semaglutide.", "effort_level": "high", "domain": "movement"},
            {"move": "Time-restricted eating: first meal after 12pm, last meal by 7pm", "why": "Metabolic fasting window improves insulin sensitivity and supports A1c goal.", "effort_level": "medium", "domain": "nutrition"},
            {"move": _push_bonus, "why": "Post-meal walk blunts the glucose spike and adds to step count.", "effort_level": "low", "domain": "glucose"},
        ]
    elif day_type == "Medical Attention":
        return [
            {"move": "Contact your care team or clinician today", "why": "Oracle has flagged a finding that requires clinical review — don't delay.", "effort_level": "medium", "domain": "mindset"},
            {"move": "Minimum exertion only — rest if uncertain", "why": "Until clinician input, conserve energy and avoid stress on the system.", "effort_level": "low", "domain": "movement"},
            {"move": "Log all symptoms and readings before the call", "why": "Specific data — glucose, BP, HR, symptoms — gives the clinician what they need.", "effort_level": "low", "domain": "mindset"},
        ]
    elif day_type == "Constraint":
        return [
            {"move": "Hotel gym 15 min or 10 flights of stairs — something counts", "why": "Consistency during constrained days builds the habit that survives travel.", "effort_level": "medium", "domain": "movement"},
            {"move": "Order protein-first at every meal: meat, fish, eggs before carbs", "why": "Restaurant meals are carb-heavy by default — protein-first blunts glucose spikes.", "effort_level": "low", "domain": "nutrition"},
            {"move": "Set a 10pm alarm — in bed regardless of time zone or schedule", "why": "Sleep is the constraint-day metric most likely to slip; protect it deliberately.", "effort_level": "medium", "domain": "sleep"},
        ]
    else:  # Maintain
        post_meal_rule = "15-min walk after dinner" if (glucose or 0) > 160 else "30-min walk anytime today"
        return [
            {"move": post_meal_rule, "why": "Daily movement is the highest-leverage glucose management tool available.", "effort_level": "low", "domain": "glucose"},
            {"move": "High-protein breakfast — skip the bagel, choose eggs or Greek yogurt", "why": "Protein-first mornings reduce the post-breakfast glucose spike and keep hunger lower.", "effort_level": "low", "domain": "nutrition"},
            {"move": "In bed by 10:30pm", "why": "Consistent sleep timing sets circadian rhythm, which directly affects glucose control and cortisol.", "effort_level": "medium", "domain": "sleep"},
        ]


# ---------------------------------------------------------------------------
# If-then rule generator
# ---------------------------------------------------------------------------

def _generate_if_then_rule(day_type: str, signals: dict) -> str:
    """Generate a single personalised if-then contingency rule for the day."""
    glucose = signals.get("latest_glucose", 150)
    rhr = signals.get("resting_hr", 65)

    if day_type == "Medical Attention":
        return "If you feel any new symptoms (chest tightness, dizziness, shortness of breath), call 911 or go to the ER — do not wait."
    elif day_type == "Recovery":
        return "If you feel worse as the day goes on (rising fatigue, dizziness), stop all activity and rest — recovery is the priority, not the goal list."
    elif day_type == "Push":
        return "If glucose drops below 80 during or after training, stop, eat 15g fast carbs, and wait 15 minutes before continuing."
    elif day_type == "Constraint":
        return "If you can't fit in the planned move, do 5 minutes of stairs or a 10-minute walk — something always beats nothing."
    else:  # Maintain
        if glucose and glucose > 180:
            return "If glucose > 180 after dinner, take a 15-min walk immediately — do not sit down first."
        elif rhr and rhr > 70:
            return "If resting HR is still elevated tonight, prioritise sleep over any other evening activity."
        else:
            return "If glucose > 180 after any meal today, take a 15-min walk within 30 minutes of finishing."


# ---------------------------------------------------------------------------
# Oracle pathway check (lightweight — uses cache when fresh)
# ---------------------------------------------------------------------------

async def _get_oracle_pathway_lightweight() -> tuple[str, str]:
    """
    Return (oracle_pathway, oracle_summary) from the council cache if fresh (< 6h),
    otherwise return (O-MONITOR, '') to avoid triggering a full council run.
    """
    if _COUNCIL_CACHE_PATH.exists():
        try:
            cached = json.loads(_COUNCIL_CACHE_PATH.read_text())
            age_hours = (datetime.utcnow().timestamp() - cached.get("_generated_at", 0)) / 3600
            if age_hours < _COUNCIL_CACHE_TTL_HOURS:
                oracle = cached.get("_oracle", {})
                pathway = oracle.get("oracle_pathway", "O-MONITOR")
                summary = oracle.get("summary", "")
                log.info("Using cached Oracle result: %s (%.1fh old)", pathway, age_hours)
                return pathway, summary
        except Exception as exc:
            log.warning("Could not read council cache: %s", exc)

    # No fresh cache — return safe default without triggering LLM
    log.info("No fresh Oracle cache — defaulting to O-MONITOR for morning check-in")
    return "O-MONITOR", "No recent council analysis — monitoring mode."


# ---------------------------------------------------------------------------
# Morning check-in
# ---------------------------------------------------------------------------

async def run_morning_checkin(context: str = "") -> dict:
    """
    Full morning check-in flow:
    1. get_morning_signals()
    2. Get Oracle pathway (from cache or lightweight)
    3. classify_day_type()
    4. generate_three_moves()
    5. Build day card
    6. append_council_decision() to log
    7. Save to cache
    Returns the day card dict.
    """
    today = date.today().isoformat()
    generated_at = datetime.utcnow().isoformat()
    season = _current_season()

    # 1. Signals
    signals = await get_morning_signals()

    # 2. Oracle pathway
    oracle_pathway, oracle_summary = await _get_oracle_pathway_lightweight()

    # 3. Classify day type
    classification = await classify_day_type(signals, oracle_pathway)
    day_type = classification["day_type"]

    # 4. Load health state for context
    try:
        try:
            from .longevity_council import load_health_state
        except ImportError:
            from longevity_council import load_health_state
        health_state = load_health_state()
    except Exception:
        health_state = {}

    # 5. Generate Three Moves
    three_moves = await generate_three_moves(day_type, signals, health_state, season=season)

    # 6. If-then rule
    if_then_rule = _generate_if_then_rule(day_type, signals)

    # Build day card
    day_card: dict[str, Any] = {
        "date": today,
        "day_type": day_type,
        "readiness_score": classification["readiness_score"],
        "oracle_pathway": oracle_pathway,
        "oracle_summary": oracle_summary,
        "signals": {
            "sleep_hours": signals.get("sleep_hours"),
            "hrv": signals.get("hrv"),
            "resting_hr": signals.get("resting_hr"),
            "latest_glucose": signals.get("latest_glucose"),
            "steps_yesterday": signals.get("steps_yesterday"),
        },
        "classification_reason": classification["reason"],
        "three_moves": three_moves,
        "if_then_rule": if_then_rule,
        "context": context or None,
        "season": season,
        "generated_at": generated_at,
    }

    # 7. Log to council decision log
    try:
        try:
            from .longevity_council import append_council_decision
        except ImportError:
            from longevity_council import append_council_decision
        await append_council_decision({
            "type": "daily_stewardship_morning",
            "date": today,
            "day_type": day_type,
            "readiness_score": classification["readiness_score"],
            "oracle_pathway": oracle_pathway,
            "signals": signals,
            "three_moves": three_moves,
            "generated_at": generated_at,
        })
    except Exception as exc:
        log.warning("Could not append to decision log: %s", exc)

    # 8. Save to cache
    _save_day_card(day_card)

    return day_card


# ---------------------------------------------------------------------------
# Evening review
# ---------------------------------------------------------------------------

async def run_evening_review(
    wins: str = "",
    struggles: str = "",
    energy: int | None = None,
) -> dict:
    """
    Evening review:
    - Report on Three Moves completion via wins/struggles text
    - Overall day score
    - One note for tomorrow
    - Update decision log
    """
    today = date.today().isoformat()
    generated_at = datetime.utcnow().isoformat()

    # Load today's day card for context
    cached_card = get_cached_day_card()
    day_type = cached_card.get("day_type", "Maintain") if cached_card else "Maintain"
    three_moves = cached_card.get("three_moves", []) if cached_card else []

    # Compute a simple day score
    energy_score = energy if energy is not None else 5
    wins_score = 7 if wins else 5
    day_score = max(1, min(10, (energy_score + wins_score) // 2))

    # Generate a note for tomorrow using LLM if available
    tomorrow_note = await _generate_tomorrow_note(day_type, wins, struggles, energy)

    review = {
        "date": today,
        "day_type": day_type,
        "wins": wins or None,
        "struggles": struggles or None,
        "energy_rating": energy,
        "day_score": day_score,
        "tomorrow_note": tomorrow_note,
        "reviewed_at": generated_at,
        "three_moves_reviewed": [m.get("move", "") for m in three_moves],
    }

    # Log to decision log
    try:
        try:
            from .longevity_council import append_council_decision
        except ImportError:
            from longevity_council import append_council_decision
        await append_council_decision({
            "type": "daily_stewardship_evening",
            "date": today,
            "day_type": day_type,
            "day_score": day_score,
            "wins": wins,
            "struggles": struggles,
            "energy": energy,
            "tomorrow_note": tomorrow_note,
            "reviewed_at": generated_at,
        })
    except Exception as exc:
        log.warning("Could not append evening review to decision log: %s", exc)

    return review


async def _generate_tomorrow_note(
    day_type: str,
    wins: str,
    struggles: str,
    energy: int | None,
) -> str:
    """Generate one actionable note for tomorrow based on today's review."""
    try:
        try:
            from .llm_gateway import get_gateway, LLMMessage
        except ImportError:
            from llm_gateway import get_gateway, LLMMessage

        gw = get_gateway()
        if gw is None:
            return _fallback_tomorrow_note(struggles)

        prompt = f"""Today was a {day_type} day.
Wins: {wins or 'not reported'}
Struggles: {struggles or 'not reported'}
Energy (1-10): {energy or 'not rated'}

Write ONE sentence — a specific, actionable note for tomorrow based on what happened today.
Be concrete. Focus on one behaviour to adjust or reinforce. No preamble."""

        response = await asyncio.to_thread(
            gw.complete,
            messages=[LLMMessage("user", prompt)],
            task_type="standard",
            agent_id="daily-stewardship-evening",
            max_tokens=100,
            temperature=0.3,
        )

        if response.error or not response.text:
            return _fallback_tomorrow_note(struggles)

        return response.text.strip()

    except Exception as exc:
        log.warning("Tomorrow note generation failed: %s", exc)
        return _fallback_tomorrow_note(struggles)


def _fallback_tomorrow_note(struggles: str) -> str:
    if struggles:
        return f"Tomorrow, plan for the struggle you had today: {struggles[:100]}"
    return "Tomorrow, pick up where today left off — consistency compounds."


# ---------------------------------------------------------------------------
# Cache access
# ---------------------------------------------------------------------------

def _load_day_card_from_log() -> dict | None:
    if not _DAY_CARD_LOG_PATH.exists():
        return None
    try:
        latest: dict[str, Any] | None = None
        with _DAY_CARD_LOG_PATH.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(entry, dict) and isinstance(entry.get("day_card"), dict):
                    latest = entry["day_card"]
        return latest
    except Exception as exc:
        log.warning("Could not replay day card cache log: %s", exc)
    return None


def _load_day_card_from_state_log() -> dict | None:
    if not _DAY_CARD_STATE_LOG_PATH.exists():
        return None
    try:
        latest: dict[str, Any] | None = None
        with _DAY_CARD_STATE_LOG_PATH.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(entry, dict) and isinstance(entry.get("day_card"), dict):
                    latest = entry["day_card"]
        return latest
    except Exception as exc:
        log.warning("Could not replay day card state log: %s", exc)
    return None


def _save_day_card(day_card: dict[str, Any]) -> None:
    try:
        append_jsonl(
            _DAY_CARD_LOG_PATH,
            {
                "saved_at": datetime.utcnow().isoformat(),
                "day_card": day_card,
            },
        )
        append_jsonl(
            _DAY_CARD_STATE_LOG_PATH,
            {
                "saved_at": datetime.utcnow().isoformat(),
                "day_card": day_card,
            },
        )
        atomic_write_json(_DAY_CARD_PATH, day_card)
    except Exception as exc:
        log.warning("Could not save day card cache: %s", exc)


def get_cached_day_card() -> dict | None:
    """Return today's cached day card if it exists and is from today."""
    card: dict[str, Any] | None = None
    if _DAY_CARD_PATH.exists():
        try:
            loaded = json.loads(_DAY_CARD_PATH.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                card = loaded
        except Exception as exc:
            log.warning("Could not read day card cache: %s", exc)
    if card is None:
        card = _load_day_card_from_state_log() or _load_day_card_from_log()
    if isinstance(card, dict) and card.get("date") == date.today().isoformat():
        return card
    return None


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------

async def get_stewardship_history(days: int = 7) -> list[dict]:
    """Return last N days of morning check-ins from decision log."""
    _DECISION_LOG_PATH = Path.home() / ".jarvis" / "health" / "council_decision_log.jsonl"
    if not _DECISION_LOG_PATH.exists():
        return []

    try:
        entries = []
        with open(_DECISION_LOG_PATH) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get("type") == "daily_stewardship_morning":
                        entries.append(entry)
                except json.JSONDecodeError:
                    continue

        # Sort by date descending and take the last N
        entries.sort(key=lambda e: e.get("date", ""), reverse=True)
        return entries[:days]

    except Exception as exc:
        log.warning("Could not read stewardship history: %s", exc)
        return []
