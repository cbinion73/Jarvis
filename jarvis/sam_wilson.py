"""
SAM WILSON — JARVIS Health & Fitness Coach
"On your left."
"""
from __future__ import annotations
import json, logging
from datetime import date, datetime, timezone, timedelta
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

ADHERENCE_LOG  = Path("data/logs/sam_adherence.jsonl")
PROTOCOL_CACHE = Path("data/settings/sam_protocol_today.json")

CHRIS_PROFILE = {
    "age": 52, "weight_lbs": 247, "weight_kg": 112,
    "a1c_pct": 7.3, "ldl_mg_dl": 156, "egfr": 87, "k_plus_meq": 4.5,
    "protein_target_g": 85, "fiber_target_g": 35,
    "water_target_oz": 96, "sleep_target_h": 7.5,
    "zone2_hr_low": 101, "zone2_hr_high": 118, "zone3_hr_high": 135,
}

SAM_SYSTEM_PROMPT = """You are Sam Wilson — Falcon, now Captain America — serving as Chris's dedicated health and fitness coach inside JARVIS.

BACKGROUND: Former pararescue jumper (most demanding fitness role in special ops) and VA counselor. You program, coach, and hold accountable with precision and warmth. "On your left" is your energy.

COACHING PHILOSOPHY:
- Consistency beats intensity every time
- Cardio is medicine — critical for Chris's glucose management
- Food is fuel. Morning cardio before breakfast hits glucose hardest.
- Recovery IS training
- "Every mile you run today is a vote for the version of you at 78."

CHRIS'S MEDICAL CONTEXT:
- Age 52, ~247 lbs, T2 Diabetes (A1c 7.3%, on GLP-1)
- LDL 156 mg/dL — cardio + diet critical
- CKD Stage 2 (eGFR 87) — moderate protein max 85-90g/day, hydration non-negotiable
- K+ 4.5 mEq/L on ARB (olmesartan) + spironolactone — limit high-K foods
- Hypertension controlled on olmesartan

ABSOLUTE SAFETY RULES — NEVER VIOLATE:
1. NEVER recommend statins — statin myopathy on record
2. Limit high-potassium foods — bananas, OJ, potatoes, tomato juice, avocado excess
3. Protein max 85-90g/day — CKD Stage 2
4. Hydration always high priority — kidney function depends on it
5. Low glycemic nutrition — A1c management

VOICE: Direct. Warm. Military precision. Competitive but caring. Call Chris "brother" or by name. Short punchy sentences. No fluff. Real talk."""


def _compute_targets(metrics: dict) -> dict:
    readiness = int(metrics.get("readiness") or metrics.get("readiness_score") or metrics.get("score") or 75)
    steps_yesterday = int(metrics.get("steps") or 8000)
    if readiness >= 85:
        intensity, minutes, strength = "high", 35, True
    elif readiness >= 70:
        intensity, minutes, strength = "moderate", 25, True
    elif readiness >= 50:
        intensity, minutes, strength = "light", 20, False
    else:
        intensity, minutes, strength = "recovery", 0, False
    steps_target = min(max(steps_yesterday + 500, 8000), 12000)
    return {
        "workout_intensity": intensity,
        "cardio_minutes": minutes,
        "strength_today": strength,
        "steps_target": steps_target,
        "water_oz": CHRIS_PROFILE["water_target_oz"],
        "sleep_h": CHRIS_PROFILE["sleep_target_h"],
        "protein_g": CHRIS_PROFILE["protein_target_g"],
        "fiber_g": CHRIS_PROFILE["fiber_target_g"],
    }


def _fallback_protocol(targets: dict, today_str: str) -> dict:
    mins = targets["cardio_minutes"]
    return {
        "date": today_str,
        "greeting": "On your left. Let's work, brother.",
        "movement": {
            "primary": f"{mins}-min Zone 2 run" if mins > 0 else "Active recovery walk",
            "details": f"Keep HR {CHRIS_PROFILE['zone2_hr_low']}–{CHRIS_PROFILE['zone2_hr_high']} bpm. Nose breathing only.",
            "alternative": "Stationary bike or brisk walk — same zone, less impact on joints.",
            "timing": "Before breakfast — morning cardio hits glucose control hardest.",
        },
        "nutrition": {
            "breakfast": "3-egg veggie scramble + 1 slice Ezekiel bread + black coffee",
            "lunch": "Large salad with 4oz grilled chicken, olive oil + lemon dressing, chickpeas",
            "dinner": "4oz salmon + roasted broccoli + ½ cup quinoa",
            "snacks": "Handful of almonds or low-fat Greek yogurt",
            "watch": "Skip bananas and OJ today — K+ monitoring with ARB + spiro combo.",
        },
        "hydration": {
            "target_oz": targets["water_oz"],
            "schedule": "16oz before 9am · 16oz by noon · 32oz afternoon · 32oz evening",
            "why": "CKD Stage 2 — kidneys need consistent flow. Non-negotiable.",
        },
        "recovery": {
            "sleep_target_h": targets["sleep_h"],
            "bedtime": "10:30 PM",
            "tip": "5 min box breathing before bed — in 4, hold 4, out 4, hold 4. HRV will thank you.",
        },
        "targets": targets,
        "sam_says": "Every mile you run today is a vote for the version of you at 78. I'll see you on the other side.",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


async def generate_daily_protocol(llm_client: Any, metrics: dict | None = None) -> dict:
    """Generate today's full health protocol. Uses cache if already generated today."""
    cached = get_cached_protocol()
    if cached:
        return cached

    metrics = metrics or {}
    targets = _compute_targets(metrics)
    today_str = date.today().strftime("%A, %B %-d")

    context = f"""Today: {today_str}
Chris's metrics:
- Readiness: {metrics.get('readiness') or metrics.get('readiness_score') or metrics.get('score') or '?'}/100
- HRV: {metrics.get('hrv') or '?'}ms
- Sleep: {metrics.get('sleep_hours') or '?'}h
- Steps yesterday: {int(metrics.get('steps') or 0):,}

Targets calculated:
- Intensity: {targets['workout_intensity']} | Cardio: {targets['cardio_minutes']} min Zone 2 | Strength: {'Yes' if targets['strength_today'] else 'Rest day'}
- Steps: {targets['steps_target']:,} | Water: {targets['water_oz']}oz | Protein: {targets['protein_g']}g | Fiber: {targets['fiber_g']}g

Generate Chris's daily protocol as Sam Wilson. Return ONLY valid JSON, no markdown:
{{
  "greeting": "<1 punchy Sam Wilson opening line>",
  "movement": {{
    "primary": "<specific workout>",
    "details": "<heart rate zone and what to focus on>",
    "alternative": "<lower-impact option>",
    "timing": "<best time of day and why>"
  }},
  "nutrition": {{
    "breakfast": "<specific meal>",
    "lunch": "<specific meal>",
    "dinner": "<specific meal>",
    "snacks": "<if needed>",
    "watch": "<one food to avoid/limit today — tie to K+ or glycemic control>"
  }},
  "hydration": {{
    "target_oz": {targets['water_oz']},
    "schedule": "<timing guidance>",
    "why": "<one sentence on why — kidney/CKD angle>"
  }},
  "recovery": {{
    "sleep_target_h": {targets['sleep_h']},
    "bedtime": "<target bedtime>",
    "tip": "<one specific recovery tip>"
  }},
  "sam_says": "<closing accountability line — direct, personal, max 2 sentences>"
}}"""

    try:
        import asyncio
        response = await asyncio.to_thread(
            llm_client.prompt_text, SAM_SYSTEM_PROMPT, context, max_output_tokens=700,
        )
        text = response.strip()
        # Strip markdown if present
        if "```" in text:
            parts = text.split("```")
            text = parts[1] if len(parts) > 1 else text
            if text.startswith("json"):
                text = text[4:]
        data = json.loads(text.strip())
        # Normalize: sam_says sometimes ends up inside recovery — lift it
        if not data.get("sam_says") and isinstance(data.get("recovery"), dict):
            nested = data["recovery"].pop("sam_says", None)
            if nested:
                data["sam_says"] = nested
        data["targets"] = targets
        data["date"] = today_str
        data["generated_at"] = datetime.now(timezone.utc).isoformat()
        PROTOCOL_CACHE.parent.mkdir(parents=True, exist_ok=True)
        PROTOCOL_CACHE.write_text(json.dumps(data, indent=2))
        return data
    except Exception as exc:
        log.error("sam_wilson.generate_daily_protocol: %s", exc)
        return _fallback_protocol(targets, today_str)


def get_cached_protocol() -> dict | None:
    try:
        if not PROTOCOL_CACHE.exists():
            return None
        data = json.loads(PROTOCOL_CACHE.read_text())
        gen = datetime.fromisoformat(data.get("generated_at", "1970-01-01"))
        if gen.date() == date.today():
            return data
        return None
    except Exception:
        return None


def log_adherence(items_completed: list[str], notes: str = "") -> None:
    ADHERENCE_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "date": date.today().isoformat(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "completed": items_completed,
        "notes": notes,
    }
    with ADHERENCE_LOG.open("a") as f:
        f.write(json.dumps(entry) + "\n")


def get_streak() -> dict:
    if not ADHERENCE_LOG.exists():
        return {"streak": 0, "total_days": 0, "last_checkin": None}
    try:
        entries = []
        with ADHERENCE_LOG.open() as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
        if not entries:
            return {"streak": 0, "total_days": 0, "last_checkin": None}
        entries.sort(key=lambda e: e.get("date", ""), reverse=True)
        streak, check_date = 0, date.today()
        for entry in entries:
            edate = date.fromisoformat(entry["date"])
            if edate == check_date or edate == check_date - timedelta(days=1):
                if entry.get("completed"):
                    streak += 1
                    check_date = edate - timedelta(days=1)
                else:
                    break
            else:
                break
        return {
            "streak": streak,
            "total_days": len(set(e["date"] for e in entries)),
            "last_checkin": entries[0]["date"] if entries else None,
        }
    except Exception as exc:
        log.error("sam_wilson.get_streak: %s", exc)
        return {"streak": 0, "total_days": 0, "last_checkin": None}


async def get_morning_checkin(metrics: dict | None = None) -> dict:
    """
    Compact morning check-in data for the banner card.
    Returns Sam's greeting, today's key focus, and current metrics.
    """
    metrics = metrics or {}
    protocol = get_cached_protocol()
    streak   = get_streak()

    greeting        = "On your left. Let's work, brother."
    focus_primary   = "Zone 2 cardio — before breakfast"
    focus_details   = f"HR {CHRIS_PROFILE['zone2_hr_low']}–{CHRIS_PROFILE['zone2_hr_high']} bpm · Nose breathing"
    timing          = "Before breakfast — morning cardio hits glucose hardest."
    nutrition_watch = None

    if protocol:
        greeting        = protocol.get("greeting", greeting)
        mv              = protocol.get("movement", {})
        focus_primary   = mv.get("primary",  focus_primary)
        focus_details   = mv.get("details",  focus_details)
        timing          = mv.get("timing",   timing)
        nutrition_watch = (protocol.get("nutrition") or {}).get("watch")

    return {
        "greeting":        greeting,
        "focus_primary":   focus_primary,
        "focus_details":   focus_details,
        "timing":          timing,
        "nutrition_watch": nutrition_watch,
        "readiness":       metrics.get("readiness"),
        "hrv":             metrics.get("hrv"),
        "sleep_hours":     metrics.get("sleep_hours"),
        "streak":          streak,
    }


async def submit_evening_checkin(
    completed:  list[str],
    notes:      str = "",
    metrics:    dict | None = None,
    llm_client: Any = None,
) -> dict:
    """
    Log today's adherence and get Sam's end-of-day coaching response.
    Standard checklist has 6 items: workout, breakfast, lunch, dinner,
    hydration, recovery.
    """
    log_adherence(completed, notes)
    streak = get_streak()

    TOTAL_ITEMS = 6
    pct = round(len(completed) / TOTAL_ITEMS * 100)

    if llm_client is None:
        if pct >= 80:
            reply = f"That's what I'm talking about — {pct}% done. Sleep well, brother. You earned it."
        elif pct >= 50:
            reply = f"{pct}% is progress. Use the night for recovery. Stack it better tomorrow."
        else:
            reply = "Rough day — it happens. Non-negotiables tomorrow: morning cardio and hit your water. Everything else is bonus."
        return {"reply": reply, "streak": streak, "adherence_pct": pct}

    m = metrics or {}
    context = (
        f"End-of-day check-in. Chris completed {len(completed)}/{TOTAL_ITEMS} items ({pct}%): "
        f"{', '.join(completed) if completed else 'none logged'}. "
        f"Notes: '{notes}'. "
        f"Current streak: {streak.get('streak', 0)} days. "
        f"Readiness: {m.get('readiness', '?')}/100 · "
        f"HRV: {m.get('hrv', '?')}ms · "
        f"Sleep last night: {m.get('sleep_hours', '?')}h."
    )
    prompt = (
        "Give Chris a brief 2–3 sentence end-of-day coaching response. "
        "Acknowledge what he did or missed honestly. Direct, warm, no fluff. "
        "End with one specific actionable thing for tomorrow."
    )
    try:
        import asyncio
        reply = await asyncio.to_thread(
            llm_client.prompt_text,
            SAM_SYSTEM_PROMPT,
            context + "\n\n" + prompt,
            max_output_tokens=120,
        )
        return {"reply": reply.strip(), "streak": streak, "adherence_pct": pct}
    except Exception as exc:
        log.error("submit_evening_checkin: %s", exc)
        return {
            "reply": f"{pct}% today. Keep stacking. See you in the morning, brother.",
            "streak": streak,
            "adherence_pct": pct,
        }


async def chat_with_sam(
    message: str,
    history: list[dict],
    metrics: dict | None = None,
    llm_client: Any = None,
) -> dict:
    if llm_client is None:
        return {"reply": "Sam's offline right now. Check back shortly.", "coach": "sam_wilson", "coach_name": "Sam Wilson", "coach_title": "Health & Fitness Coach"}
    metrics = metrics or {}
    readiness_val = metrics.get("readiness") or metrics.get("readiness_score") or "?"
    ctx = (
        f"Chris's stats right now — Readiness: {readiness_val}/100 · "
        f"HRV: {metrics.get('hrv','?')}ms · Sleep: {metrics.get('sleep_hours','?')}h · "
        f"Steps: {int(metrics.get('steps') or 0):,} · A1c: {CHRIS_PROFILE['a1c_pct']}% · "
        f"LDL: {CHRIS_PROFILE['ldl_mg_dl']} · K+: {CHRIS_PROFILE['k_plus_meq']}"
    )
    conv = "\n".join(
        f"{'CHRIS' if h.get('role')=='user' else 'SAM'}: {h.get('content','')}"
        for h in (history or [])[-6:]
    )
    conv += f"\nCHRIS: {message}"
    try:
        import asyncio
        reply = await asyncio.to_thread(
            llm_client.prompt_text,
            SAM_SYSTEM_PROMPT + "\n\nContext: " + ctx,
            conv,
            max_output_tokens=300,
        )
        return {"reply": reply.strip(), "coach": "sam_wilson", "coach_name": "Sam Wilson", "coach_title": "Health & Fitness Coach"}
    except Exception as exc:
        log.error("chat_with_sam: %s", exc)
        return {"reply": "Give me a second, brother. System catching up.", "coach": "sam_wilson", "coach_name": "Sam Wilson", "coach_title": "Health & Fitness Coach"}
