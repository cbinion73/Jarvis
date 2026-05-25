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

# ── Longevity Council context cache (TTL = 10 min) ───────────────────────────
_council_ctx_cache: str = ""
_council_ctx_ts: datetime | None = None
_COUNCIL_CTX_TTL = timedelta(minutes=10)


def _get_council_context() -> str:
    """
    Return health_state_summary() with a 10-minute in-process cache.
    Never raises — returns empty string on any error.
    """
    global _council_ctx_cache, _council_ctx_ts
    now = datetime.now(timezone.utc)
    if _council_ctx_ts and (now - _council_ctx_ts) < _COUNCIL_CTX_TTL and _council_ctx_cache:
        return _council_ctx_cache
    try:
        from .longevity_council import health_state_summary
        _council_ctx_cache = health_state_summary()
        _council_ctx_ts = now
    except Exception as exc:
        log.warning("_get_council_context: %s", exc)
        _council_ctx_cache = ""
    return _council_ctx_cache

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

HONESTY MANDATE — THIS IS NON-NEGOTIABLE:
You are Chris's coach, not his hype man. Real coaches tell hard truths.
- Call out bad choices DIRECTLY by name. "That pizza and cake spiked your glucose and your LDL doesn't have room for that" is correct. "Interesting choices today" is cowardly.
- Use a scorecard framing when reviewing a day: what was a WIN, what was a MISS, and what's the IMPACT on his actual health numbers.
- Never sugarcoat food choices that contradict his medical goals. If he had cake and pizza on a day with zero water and poor sleep, say it plainly.
- Balance honesty with respect. You're not shaming him — you're treating him like a capable adult who can handle the truth and use it to improve.
- Celebrate genuine wins with the same intensity you call out misses. Both matter.
- If a choice was medically risky (high-K food, excess sugar with A1c at 7.3%, no hydration with CKD), flag it explicitly. His medical team is watching this data.

VOICE: Direct. Warm. Military precision. Competitive but caring. Short punchy sentences. No fluff. Real talk. Honest even when it's uncomfortable.

LANGUAGE VARIETY — this is important:
- You sound like Sam Wilson, but you don't always announce it. Real people don't repeat their catchphrases every sentence.
- "On your left" and "brother" are in your vocabulary but use them sparingly — maybe once every several exchanges, when it genuinely lands. Overusing them makes you sound like a bit from a sketch.
- Vary how you address Chris: use his name sometimes, "man" sometimes, nothing at all sometimes. Let the coaching speak.
- Your personality comes through your directness, your precision, and your care — not your catchphrases."""


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
        "greeting": "Let's get to work.",
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

    greeting        = "Let's get to work."
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
            reply = f"That's what I'm talking about — {pct}% done. You earned the rest tonight."
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
            "reply": f"{pct}% today. Keep stacking. See you in the morning.",
            "streak": streak,
            "adherence_pct": pct,
        }


CHECKLIST_ITEMS = {
    "workout":   "Any intentional exercise or movement — walk, bike, gym, cardio, resistance training",
    "breakfast": "Ate a nutritious breakfast (protein-focused, low glycemic — eggs, Greek yogurt, etc.)",
    "lunch":     "Ate a healthy lunch (clean protein, vegetables, avoided high-glycemic carbs)",
    "dinner":    "Ate a healthy dinner (lean protein, low-carb, avoided late junk food)",
    "hydration": f"Met daily water goal (~{CHRIS_PROFILE['water_target_oz']}oz / 3L) throughout the day",
    "recovery":  "Prioritized sleep — in bed at a reasonable hour, wound down properly",
}


async def evaluate_day_narrative(
    narrative: str,
    metrics:    dict | None = None,
    llm_client: Any = None,
) -> dict:
    """
    Parse Chris's free-text description of his day and map it to the 6
    protocol checklist items. Returns:
      {completed: [...], reply: str, adherence_pct: int}
    Falls back to keyword heuristics if LLM is unavailable.
    """
    narrative = narrative.strip()
    if not narrative:
        return {"completed": [], "reply": "Tell me what you did today — I'm listening.", "adherence_pct": 0}

    TOTAL = 6

    # ── LLM path ──────────────────────────────────────────────────────────
    if llm_client is not None:
        m = metrics or {}
        items_desc = "\n".join(f'  "{k}": {v}' for k, v in CHECKLIST_ITEMS.items())
        system = (
            SAM_SYSTEM_PROMPT
            + "\n\nYou are evaluating Chris's day based on his narrative description. "
            "You must respond with ONLY valid JSON — no prose before or after.\n"
            "JSON format:\n"
            '{\n'
            '  "completed": ["workout", "breakfast"],   // subset of the 6 item IDs Chris accomplished\n'
            '  "reply": "Sam\'s 2–3 sentence coaching response",\n'
            '  "reasoning": {"workout": "He mentioned a 40-min walk", ...}  // brief per-item notes\n'
            '}'
        )
        prompt = (
            f"Chris's day (in his own words):\n\"{narrative}\"\n\n"
            f"The 6 protocol items and what counts as completing each:\n{items_desc}\n\n"
            f"Current metrics: readiness {m.get('readiness','?')}/100 · "
            f"HRV {m.get('hrv','?')}ms · sleep {m.get('sleep_hours','?')}h\n\n"
            "Evaluate which items Chris completed based ONLY on what he described. "
            "Be fair but precise — if he says he 'had a big bowl of cereal' that doesn't count as a clean breakfast. "
            "Give honest coaching in 'reply': acknowledge wins, call out misses, end with ONE tomorrow action."
        )
        try:
            import asyncio, re
            raw = await asyncio.to_thread(
                llm_client.prompt_text,
                system,
                prompt,
                max_output_tokens=350,
            )
            # Extract JSON — model may wrap in ```json ... ```
            raw = raw.strip()
            m2 = re.search(r'\{.*\}', raw, re.DOTALL)
            if m2:
                raw = m2.group(0)
            parsed = json.loads(raw)
            completed = [k for k in parsed.get("completed", []) if k in CHECKLIST_ITEMS]
            pct = round(len(completed) / TOTAL * 100)
            return {
                "completed":     completed,
                "reply":         parsed.get("reply", "").strip(),
                "adherence_pct": pct,
                "reasoning":     parsed.get("reasoning", {}),
            }
        except Exception as exc:
            log.error("evaluate_day_narrative LLM error: %s", exc)
            # fall through to heuristic

    # ── Heuristic fallback ────────────────────────────────────────────────
    nl = narrative.lower()
    completed: list[str] = []
    if any(w in nl for w in ["walk", "ran", "run", "bike", "gym", "workout", "cardio", "exercise", "jog", "lift", "weights", "zone 2"]):
        completed.append("workout")
    if any(w in nl for w in ["breakfast", "eggs", "oatmeal", "yogurt", "morning meal"]):
        completed.append("breakfast")
    if any(w in nl for w in ["lunch", "midday", "noon"]):
        completed.append("lunch")
    if any(w in nl for w in ["dinner", "supper", "evening meal"]):
        completed.append("dinner")
    if any(w in nl for w in ["water", "hydrat", "oz", "gallon", "drank"]):
        completed.append("hydration")
    if any(w in nl for w in ["bed", "sleep", "lights out", "early night", "recovery"]):
        completed.append("recovery")
    pct = round(len(completed) / TOTAL * 100)
    reply = (
        f"{pct}% based on what you described. " +
        ("That's solid work — keep stacking." if pct >= 80 else
         "Progress. Hit the gaps tomorrow — every item counts." if pct >= 50 else
         "Rough one. Tomorrow: morning movement and hit your water. Everything else builds from there.")
    )
    return {"completed": completed, "reply": reply, "adherence_pct": pct, "reasoning": {}}


# ─── Food preferences store ───────────────────────────────────────────────────
FOOD_PREFS_PATH = Path("data/settings/sam_food_prefs.json")

# High-K+ foods Sam always flags (CKD + ARB + spiro risk)
_HIGH_K_FOODS = [
    "banana", "avocado", "potato", "tomato juice", "orange juice", "OJ",
    "spinach", "sweet potato", "beans", "lentils", "bran", "nuts", "prunes",
    "raisins", "coconut water", "yogurt", "salmon", "sardines",
]

_SAM_REPLY = {"coach": "sam_wilson", "coach_name": "Sam Wilson", "coach_title": "Health & Fitness Coach"}

# Diet interview questions — Sam leads this
_INTERVIEW_QUESTIONS = [
    ("likes",         "Let's figure out what actually works for your palate. What foods do you genuinely enjoy eating — anything goes, just be honest."),
    ("dislikes",      "What foods are hard nos for you? Things you refuse to eat or strongly dislike."),
    ("allergies",     "Any food allergies or intolerances I need to know about?"),
    ("typical_meals", "Walk me through what a typical weekday looks like for meals — breakfast, lunch, dinner, snacks. Be real with me."),
    ("eat_out",       "How often do you eat out or order in? What are your go-to spots or cuisines?"),
    ("cooking",       "How comfortable are you in the kitchen? Quick 15-minute meals, or do you actually enjoy cooking?"),
    ("cravings",      "What do you reach for when you're stressed, tired, or just want comfort food?"),
    ("goals",         "What's your biggest food goal right now — weight, energy, blood sugar control, building a better relationship with food?"),
    ("wins",          "Any foods or meals you've discovered that actually feel good — give you energy, don't spike your glucose, just work?"),
    ("done",          None),  # Sentinel — interview complete
]


def get_food_preferences() -> dict:
    """Load food preferences from disk. Returns empty skeleton if missing."""
    try:
        if FOOD_PREFS_PATH.exists():
            return json.loads(FOOD_PREFS_PATH.read_text())
    except Exception:
        pass
    return {
        "interview_step": 0,
        "interview_complete": False,
        "interview_notes": {},
        "likes": [],
        "dislikes": [],
        "allergies": [],
        "typical_meals": "",
        "eat_out_freq": "",
        "cooking_skill": "",
        "cravings": [],
        "goals": "",
        "wins": [],
        "updated_at": "",
    }


def save_food_preferences(prefs: dict) -> None:
    try:
        FOOD_PREFS_PATH.parent.mkdir(parents=True, exist_ok=True)
        prefs["updated_at"] = datetime.now(timezone.utc).isoformat()
        FOOD_PREFS_PATH.write_text(json.dumps(prefs, indent=2))
    except Exception as exc:
        log.error("save_food_preferences: %s", exc)


def _prefs_summary(prefs: dict) -> str:
    """One-line context string for Sam's system prompt."""
    if not prefs.get("interview_complete"):
        return "Diet interview: not yet completed."
    parts = []
    if prefs.get("likes"):
        parts.append("Likes: " + ", ".join(prefs["likes"][:6]))
    if prefs.get("dislikes"):
        parts.append("Dislikes: " + ", ".join(prefs["dislikes"][:4]))
    if prefs.get("cravings"):
        parts.append("Cravings/comfort: " + ", ".join(prefs["cravings"][:3]))
    if prefs.get("goals"):
        parts.append(f"Food goal: {prefs['goals'][:80]}")
    return " · ".join(parts) if parts else "Diet interview complete."


async def analyze_food_entry(
    description: str,
    date_str:    str | None = None,
    prefs:       dict | None = None,
    metrics:     dict | None = None,
    llm_client:  Any = None,
) -> dict:
    """
    Parse a natural-language food description, estimate macros, flag
    CKD / K+ / glucose concerns, log to nutrition_engine, and return
    Sam's coaching response.

    Returns:
      {meal: {name, protein_g, carb_g, fat_g, calories, time},
       daily: {total_protein_g, protein_gap_g, meal_count, …},
       reply: str, warnings: [str], logged: bool}
    """
    import asyncio, re
    date_str  = date_str or date.today().isoformat()
    now_time  = datetime.now().strftime("%H:%M")
    warnings: list[str] = []

    # Quick K+ keyword scan
    desc_lower = description.lower()
    for food in _HIGH_K_FOODS:
        if food.lower() in desc_lower:
            warnings.append(f"⚠ High-K+ food detected ({food}) — watch portion with your ARB + spiro combo")

    if llm_client is None:
        # Minimal fallback — heuristic macros
        meal = {"name": description[:80], "protein_g": 20.0, "carb_g": 30.0, "fat_g": 10.0, "calories": 290.0, "time": now_time}
        reply = "Logged. I couldn't analyse the macros right now — check back when I'm fully online."
        logged, daily = _try_log_meal(date_str, meal)
        return {"meal": meal, "daily": daily, "reply": reply, "warnings": warnings, "logged": logged}

    # LLM: extract meal + estimate macros + coaching
    prefs_ctx  = _prefs_summary(prefs or {})
    m = metrics or {}
    system = (
        SAM_SYSTEM_PROMPT
        + "\n\nYou are analysing a food entry Chris logged. Respond ONLY with valid JSON — no prose outside the JSON.\n"
        'Format:\n'
        '{\n'
        '  "meal_name": "Scrambled eggs, toast, OJ",\n'
        '  "protein_g": 28.0,\n'
        '  "carb_g": 42.0,\n'
        '  "fat_g": 14.0,\n'
        '  "calories": 410.0,\n'
        '  "glucose_impact": "medium",   // low | medium | high\n'
        '  "k_concern": true,            // true if high-K+ foods present\n'
        '  "reply": "Sam\'s 2–3 sentence coaching comment on this meal"\n'
        '}'
    )
    prompt = (
        f"Food entry: \"{description}\"\n"
        f"Time of day: {now_time}  |  Date: {date_str}\n"
        f"Daily protein so far: {m.get('protein_today_g', '?')}g  |  Target max: {CHRIS_PROFILE['protein_target_g']}g (CKD Stage 2)\n"
        f"Chris's food preferences: {prefs_ctx}\n\n"
        "Estimate macros as accurately as possible for typical US serving sizes. "
        "Flag glucose impact honestly. Call out any high-K+ foods. "
        "Keep reply direct and specific — what was good, what to watch, one improvement."
    )
    try:
        raw = await asyncio.to_thread(llm_client.prompt_text, system, prompt, max_output_tokens=250)
        raw = raw.strip()
        m2 = re.search(r'\{.*\}', raw, re.DOTALL)
        if m2:
            raw = m2.group(0)
        parsed = json.loads(raw)
        meal = {
            "name":      parsed.get("meal_name", description[:80]),
            "protein_g": float(parsed.get("protein_g", 20)),
            "carb_g":    float(parsed.get("carb_g", 30)),
            "fat_g":     float(parsed.get("fat_g", 10)),
            "calories":  float(parsed.get("calories", 300)),
            "time":      now_time,
        }
        if parsed.get("k_concern") and not warnings:
            warnings.append("⚠ High-K+ food in this meal — be mindful of portions")
        reply = parsed.get("reply", "Logged.").strip()
        logged, daily = _try_log_meal(date_str, meal)
        return {"meal": meal, "daily": daily, "reply": reply, "warnings": warnings, "logged": logged}
    except Exception as exc:
        log.error("analyze_food_entry: %s", exc)
        meal = {"name": description[:80], "protein_g": 20.0, "carb_g": 30.0, "fat_g": 10.0, "calories": 290.0, "time": now_time}
        logged, daily = _try_log_meal(date_str, meal)
        return {"meal": meal, "daily": daily, "reply": "Logged — couldn't estimate macros right now.", "warnings": warnings, "logged": logged}


def _try_log_meal(date_str: str, meal: dict) -> tuple[bool, dict]:
    """Log meal to nutrition_engine; return (success, daily_summary)."""
    try:
        from .nutrition_engine import log_meal, get_daily_nutrition
        daily_dict = log_meal(date_str, meal)
        return True, daily_dict
    except Exception as exc:
        log.error("_try_log_meal: %s", exc)
        return False, {}


def get_today_food_log(date_str: str | None = None) -> dict:
    """Return today's nutrition summary from the nutrition engine."""
    try:
        from .nutrition_engine import get_daily_nutrition
        rec = get_daily_nutrition(date_str or date.today().isoformat())
        protein_g  = round(float(rec.total_protein_g or 0), 1)
        meals_list = rec.meals or []
        # NutritionLog.meals is a list of dicts (not objects)
        meal_count = len(meals_list)
        def _meal_row(m):
            if isinstance(m, dict):
                return {"name": m.get("name",""), "protein_g": m.get("protein_g",0), "calories": m.get("calories",0), "time": m.get("time","")}
            return {"name": getattr(m,"name",""), "protein_g": getattr(m,"protein_g",0), "calories": getattr(m,"calories",0), "time": getattr(m,"time","")}
        return {
            "date":             rec.date,
            "meal_count":       meal_count,
            "protein_g":        protein_g,
            "total_protein_g":  protein_g,
            "total_carbs_g":    round(float(rec.total_carbs_g or 0), 1),
            "total_fat_g":      round(float(rec.total_fat_g or 0), 1),
            "total_calories":   round(float(rec.total_calories or 0), 0),
            "protein_target_g": CHRIS_PROFILE["protein_target_g"],
            "protein_gap_g":    max(0, round(CHRIS_PROFILE["protein_target_g"] - protein_g, 1)),
            "meals":            [_meal_row(m) for m in meals_list],
        }
    except Exception as exc:
        log.error("get_today_food_log: %s", exc)
        return {"meal_count": 0, "protein_g": 0, "total_protein_g": 0, "protein_gap_g": CHRIS_PROFILE["protein_target_g"], "meals": []}


# ─── Diet interview ────────────────────────────────────────────────────────────

async def run_diet_interview(
    step:        int,
    user_answer: str | None,
    llm_client:  Any = None,
) -> dict:
    """
    Drive the structured diet interview.
    step=0 starts fresh. For step>0, user_answer contains Chris's response
    to the previous question.

    Returns:
      {step, question, done, reply, prefs_updated}
    """
    prefs = get_food_preferences()

    # If an answer was provided, have Sam process it and store the insight
    if user_answer and step > 0 and step <= len(_INTERVIEW_QUESTIONS):
        field_key = _INTERVIEW_QUESTIONS[step - 1][0]
        prefs.setdefault("interview_notes", {})[field_key] = user_answer

        # Update structured fields from the answer
        low = user_answer.lower()
        if field_key == "likes":
            # Simple comma-split heuristic; LLM refines later
            items = [x.strip() for x in user_answer.replace(" and ", ",").split(",") if x.strip()]
            prefs["likes"] = items[:20]
        elif field_key == "dislikes":
            items = [x.strip() for x in user_answer.replace(" and ", ",").split(",") if x.strip()]
            prefs["dislikes"] = items[:20]
        elif field_key == "allergies":
            prefs["allergies"] = [x.strip() for x in user_answer.replace(" and ", ",").split(",") if x.strip()]
        elif field_key == "typical_meals":
            prefs["typical_meals"] = user_answer[:500]
        elif field_key == "eat_out":
            prefs["eat_out_freq"] = user_answer[:200]
        elif field_key == "cooking":
            prefs["cooking_skill"] = user_answer[:200]
        elif field_key == "cravings":
            items = [x.strip() for x in user_answer.replace(" and ", ",").split(",") if x.strip()]
            prefs["cravings"] = items[:10]
        elif field_key == "goals":
            prefs["goals"] = user_answer[:300]
        elif field_key == "wins":
            items = [x.strip() for x in user_answer.replace(" and ", ",").split(",") if x.strip()]
            prefs["wins"] = items[:10]

        prefs["interview_step"] = step
        save_food_preferences(prefs)

    # Advance to next question.
    # step is 1-indexed: step=0 = start (no answer yet), step=N = answer to Q[N-1] was given.
    # next_step = the step number the client should send next (= which question to show now, 1-indexed).
    next_step  = step + 1          # always increment; step=0 → show Q[0]; step=1 → show Q[1] etc.
    next_q_idx = next_step - 1     # 0-indexed into _INTERVIEW_QUESTIONS

    if next_q_idx >= len(_INTERVIEW_QUESTIONS) or _INTERVIEW_QUESTIONS[next_q_idx][0] == "done":
        prefs["interview_complete"] = True
        save_food_preferences(prefs)
        # Sam closes out
        closing = (
            "That's what I needed. I've got a solid picture of how you eat — "
            "the wins, the gaps, the comfort patterns. From here I'll factor all of this into every meal "
            "conversation we have. No more generic advice — this is your playbook now."
        )
        if llm_client is not None:
            try:
                import asyncio
                notes_text = " | ".join(f"{k}: {v[:60]}" for k, v in prefs.get("interview_notes", {}).items())
                closing = await asyncio.to_thread(
                    llm_client.prompt_text,
                    SAM_SYSTEM_PROMPT,
                    f"Diet interview complete. Chris's answers summary: {notes_text}\n\n"
                    "Give a 2-3 sentence closing that acknowledges what you learned about Chris's diet, "
                    "names one strength and one challenge you noticed, and tells him what changes in your coaching from here.",
                    max_output_tokens=150,
                )
                closing = closing.strip()
            except Exception:
                pass
        return {"step": next_step, "question": None, "done": True, "reply": closing, "prefs_updated": True}

    # Return the next question, with Sam's acknowledgment of the previous answer (if any)
    _, raw_question = _INTERVIEW_QUESTIONS[next_q_idx]
    reply = raw_question  # default — raw question text, no LLM transition for the opening

    if user_answer and llm_client is not None:
        try:
            import asyncio
            prev_field = _INTERVIEW_QUESTIONS[step - 1][0] if 0 < step <= len(_INTERVIEW_QUESTIONS) else ""
            reply = await asyncio.to_thread(
                llm_client.prompt_text,
                SAM_SYSTEM_PROMPT,
                f"Chris just answered the '{prev_field}' question in our diet interview: \"{user_answer}\"\n\n"
                f"Give a 1-sentence acknowledgment (direct, no fluff, maybe one brief reaction), "
                f"then immediately ask this next question: \"{raw_question}\"",
                max_output_tokens=120,
            )
            reply = reply.strip()
        except Exception:
            reply = raw_question

    return {"step": next_step, "question": raw_question, "done": False, "reply": reply, "prefs_updated": bool(user_answer)}


# ─── Enhanced chat_with_sam (food-aware) ──────────────────────────────────────

_FOOD_TRIGGERS = [
    "i had", "i ate", "i just ate", "for breakfast", "for lunch", "for dinner",
    "for a snack", "i drank", "i'm eating", "just had", "eating", "just ate",
    "meal was", "food was", "grabbed", "ordered", "cooked",
]


def _is_food_message(text: str) -> bool:
    low = text.lower()
    return any(t in low for t in _FOOD_TRIGGERS)


async def chat_with_sam(
    message: str,
    history: list[dict],
    metrics: dict | None = None,
    llm_client: Any = None,
    mode: str = "chat",            # "chat" | "food" | "interview"
    interview_step: int = 0,
    food_date: str | None = None,
) -> dict:
    """
    Enhanced Sam chat: auto-detects food entries, handles diet interview mode,
    and provides food-aware coaching in normal chat.
    """
    if llm_client is None:
        return {**_SAM_REPLY, "reply": "Sam's offline right now. Check back shortly."}

    metrics   = metrics or {}
    prefs     = get_food_preferences()

    # ── Interview mode ────────────────────────────────────────────────────────
    if mode == "interview":
        result = await run_diet_interview(interview_step, message or None, llm_client)
        return {**_SAM_REPLY, **result}

    # ── Food log mode (explicit) or auto-detected food entry ─────────────────
    if mode == "food" or _is_food_message(message):
        result   = await analyze_food_entry(message, food_date, prefs, metrics, llm_client)
        warnings = result.get("warnings", [])
        reply    = result.get("reply", "")
        daily    = result.get("daily", {})
        footer = ""
        if daily:
            prot = daily.get("total_protein_g", 0)
            gap  = daily.get("protein_gap_g", 0)
            cnt  = daily.get("meal_count", 0)
            footer = f"\n\n📊 Today so far: {prot}g protein across {cnt} meal{'s' if cnt != 1 else ''}"
            if gap > 0:
                footer += f" — {gap}g to go to hit your target"
            else:
                footer += " — protein target hit 💪"
        return {**_SAM_REPLY, "mode": "food", "reply": (reply + footer).strip(), "meal": result.get("meal"), "daily": daily, "logged": result.get("logged", False), "warnings": warnings}

    # ── Regular chat (food-context-enriched) ─────────────────────────────────
    readiness_val = metrics.get("readiness") or metrics.get("readiness_score") or "?"
    today_food    = get_today_food_log()
    food_ctx = (
        f"Today's food log: {today_food.get('meal_count', 0)} meals, "
        f"{today_food.get('total_protein_g', 0)}g protein "
        f"({'target met' if today_food.get('protein_gap_g', 1) <= 0 else str(today_food.get('protein_gap_g', '?')) + 'g to go'}). "
    ) if today_food.get("meal_count", 0) > 0 else ""

    prefs_ctx = _prefs_summary(prefs) if prefs.get("interview_complete") else ""

    ctx = (
        f"Chris's stats — Readiness: {readiness_val}/100 · "
        f"HRV: {metrics.get('hrv','?')}ms · Sleep: {metrics.get('sleep_hours','?')}h · "
        f"Steps: {int(metrics.get('steps') or 0):,} · A1c: {CHRIS_PROFILE['a1c_pct']}% · "
        f"LDL: {CHRIS_PROFILE['ldl_mg_dl']} · K+: {CHRIS_PROFILE['k_plus_meq']}. "
        f"{food_ctx}{prefs_ctx}"
    )
    conv = "\n".join(
        f"{'CHRIS' if h.get('role')=='user' else 'SAM'}: {h.get('content','')}"
        for h in (history or [])[-8:]
    )
    conv += f"\nCHRIS: {message}"
    try:
        import asyncio
        council_ctx = _get_council_context()
        council_block = (
            f"\n\nLONGEVITY COUNCIL INTELLIGENCE (silent — use to ground your coaching):\n"
            f"{council_ctx[:2500]}"
        ) if council_ctx else ""
        reply = await asyncio.to_thread(
            llm_client.prompt_text,
            SAM_SYSTEM_PROMPT + "\n\nContext: " + ctx + council_block,
            conv,
            max_output_tokens=300,
        )
        return {**_SAM_REPLY, "reply": reply.strip()}
    except Exception as exc:
        log.error("chat_with_sam: %s", exc)
        return {**_SAM_REPLY, "reply": "Give me a second. System catching up."}


# ── Daily Journal ─────────────────────────────────────────────────────────────

JOURNAL_PATH = Path("data/logs/sam_daily_journal.jsonl")

_JOURNAL_SCHEMA = """\
{
  "exercise": [{"type":"", "duration_min":0, "intensity":"light|moderate|hard", "notes":""}],
  "food": [{"name":"", "meal_type":"breakfast|lunch|dinner|snack|drink", "time":"HH:MM or empty"}],
  "water_oz": 0,
  "caffeine": "",
  "alcohol": false,
  "mood": "great|good|okay|low|anxious|stressed",
  "stress_level": 5,
  "energy_level": 5,
  "sleep_quality": "great|good|okay|poor",
  "physical_symptoms": [],
  "mental_notes": "",
  "wins": [],
  "challenges": [],
  "adherence_items": []
}"""

_EMPTY_EXTRACTED: dict = {
    "exercise": [], "food": [], "water_oz": 0, "caffeine": "",
    "alcohol": False, "mood": None, "stress_level": None, "energy_level": None,
    "sleep_quality": None, "physical_symptoms": [], "mental_notes": "",
    "wins": [], "challenges": [], "adherence_items": [],
}


def _merge_extracted(base: dict, new: dict) -> dict:
    """Merge a new extracted entry into an existing one (for upsert)."""
    merged = dict(base)
    # Extend lists
    for key in ("exercise", "food", "physical_symptoms", "wins", "challenges", "adherence_items"):
        existing = merged.get(key) or []
        incoming = new.get(key) or []
        merged[key] = existing + incoming
    # Sum water
    merged["water_oz"] = (merged.get("water_oz") or 0) + (new.get("water_oz") or 0)
    # Take latest non-null scalars
    for key in ("mood", "stress_level", "energy_level", "sleep_quality", "caffeine", "alcohol", "mental_notes"):
        val = new.get(key)
        if val is not None and val != "" and val is not False:
            merged[key] = val
        elif merged.get(key) is None:
            merged[key] = new.get(key)
    return merged


# Sleep parsing schema for LLM extraction
_SLEEP_EXTRACT_SCHEMA = """{
  "bedtime": "HH:MM or null",
  "wake_time": "HH:MM or null",
  "total_night_hours": null,
  "nap_hours": null,
  "sleep_quality_score": null
}"""

async def _maybe_log_sleep(
    narrative: str,
    extracted: dict,
    date_str: str,
    llm_client: Any,
) -> None:
    """
    Parse sleep details from the narrative and append to sleep_log.jsonl.
    Only writes if sleep info is actually mentioned.  Skips if no LLM available.
    """
    import asyncio, re as _re
    from pathlib import Path as _Path

    # Quick gate: skip if no obvious sleep mention
    nl = narrative.lower()
    sleep_keywords = ("bed", "sleep", "slept", "woke", "wake", "nap", "tired", "exhausted", "rest")
    if not any(k in nl for k in sleep_keywords):
        return

    parsed_sleep: dict = {}
    if llm_client is not None:
        try:
            sys_prompt = (
                "You are a health data extractor. Extract sleep timing from the text and return ONLY valid JSON. "
                "Use 24-hour HH:MM for times. Set to null if not clearly stated.\n\n"
                f"Schema:\n{_SLEEP_EXTRACT_SCHEMA}"
            )
            user_prompt = f"Date: {date_str}\nText:\n\"{narrative}\"\n\nReturn only JSON."
            raw = await asyncio.to_thread(
                llm_client.prompt_text,
                sys_prompt,
                user_prompt,
                max_output_tokens=150,
            )
            m = _re.search(r"\{.*\}", raw.strip(), _re.DOTALL)
            if m:
                parsed_sleep = json.loads(m.group(0))
        except Exception as exc:
            log.warning("_maybe_log_sleep LLM extract: %s", exc)
            return
    else:
        return  # no LLM, no sleep log

    # Map sleep_quality string from extracted to integer 1-10
    sq_str = extracted.get("sleep_quality") or ""
    sq_map = {"great": 9, "good": 7, "okay": 5, "poor": 3}
    sq_int = parsed_sleep.get("sleep_quality_score") or sq_map.get(sq_str, 5)
    try:
        sq_int = int(sq_int)
    except (TypeError, ValueError):
        sq_int = 5

    # Total hours: night + nap
    night_h = parsed_sleep.get("total_night_hours")
    nap_h   = parsed_sleep.get("nap_hours") or 0
    if night_h is None:
        return  # no usable sleep data

    try:
        night_h = float(night_h)
        nap_h   = float(nap_h)
    except (TypeError, ValueError):
        return

    total_h = round(night_h + nap_h, 2)
    if total_h <= 0:
        return

    bedtime   = parsed_sleep.get("bedtime") or "00:00"
    wake_time = parsed_sleep.get("wake_time") or "00:00"

    # Build notes
    notes_parts = []
    if nap_h > 0:
        notes_parts.append(f"Nap: {nap_h}h")
    sq_label = extracted.get("sleep_quality") or sq_str
    if sq_label:
        notes_parts.append(f"quality={sq_label}")
    notes = " | ".join(notes_parts) if notes_parts else ""

    # Write to sleep_log.jsonl
    try:
        from .sleep_intelligence import SleepLog, log_sleep
        entry = SleepLog(
            date=date_str,
            bedtime=bedtime,
            wake_time=wake_time,
            total_hours=total_h,
            sleep_quality=sq_int,
            hrv_morning=None,
            resting_hr=None,
            spo2_min=None,
            notes=notes,
        )
        result = await asyncio.to_thread(log_sleep, entry)
        log.info("_maybe_log_sleep: logged %s — %.1fh (night=%.1fh, nap=%.1fh)", date_str, total_h, night_h, nap_h)
    except Exception as exc:
        log.error("_maybe_log_sleep write: %s", exc)


def _upsert_journal(date_str: str, raw_entry: str, extracted: dict,
                    total_protein_g: float, adherence_items: list[str]) -> None:
    """Read JSONL, find matching date, merge, rewrite."""
    JOURNAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    existing: list[dict] = []
    if JOURNAL_PATH.exists():
        for line in JOURNAL_PATH.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                existing.append(json.loads(line))
            except Exception:
                pass

    record: dict | None = None
    kept: list[dict] = []
    for rec in existing:
        if rec.get("date") == date_str:
            record = rec
        else:
            kept.append(rec)

    if record is None:
        record = {
            "date": date_str,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "raw_entries": [],
            "extracted": dict(_EMPTY_EXTRACTED),
            "total_protein_g": 0.0,
            "adherence_items": [],
        }

    record["raw_entries"] = record.get("raw_entries", []) + [raw_entry]
    record["extracted"] = _merge_extracted(record.get("extracted", {}), extracted)
    record["total_protein_g"] = float(record.get("total_protein_g") or 0) + total_protein_g
    # Merge adherence_items deduped
    existing_adh = record.get("adherence_items") or []
    record["adherence_items"] = list(dict.fromkeys(existing_adh + adherence_items))
    record["timestamp"] = datetime.now(timezone.utc).isoformat()

    kept.append(record)
    JOURNAL_PATH.write_text("\n".join(json.dumps(r) for r in kept) + "\n")


def _upsert_adherence(date_str: str, items: list[str]) -> None:
    """Merge adherence items into the adherence log for the given date."""
    ADHERENCE_LOG.parent.mkdir(parents=True, exist_ok=True)
    existing: list[str] = []
    if ADHERENCE_LOG.exists():
        existing = [l for l in ADHERENCE_LOG.read_text().splitlines() if l.strip()]
    kept: list[str] = []
    current_rec: dict | None = None
    for line in existing:
        try:
            rec = json.loads(line)
            if rec.get("date") == date_str:
                current_rec = rec
            else:
                kept.append(line)
        except Exception:
            kept.append(line)
    if current_rec is None:
        current_rec = {"date": date_str, "completed": [], "notes": ""}
    # Merge items
    merged = list(dict.fromkeys((current_rec.get("completed") or []) + items))
    current_rec["completed"] = merged
    current_rec["timestamp"] = datetime.now(timezone.utc).isoformat()
    kept.append(json.dumps(current_rec))
    ADHERENCE_LOG.write_text("\n".join(kept) + "\n")


async def process_journal_entry(
    narrative: str,
    history: list[dict],
    date_str: str | None,
    metrics: dict,
    llm_client: Any,
) -> dict:
    """
    Process a free-text daily health journal entry from Chris.
    Extracts structured data, logs meals, updates adherence, and returns
    Sam's coaching reply.
    """
    import asyncio, re

    date_str = date_str or date.today().isoformat()
    PROTEIN_TARGET_G = 87  # midpoint of 85-90g CKD target

    # ── Step 1: Extract structured data via LLM ──────────────────────────────
    extracted: dict = dict(_EMPTY_EXTRACTED)

    if llm_client is not None:
        extract_system = (
            "You are a health data extractor for JARVIS. "
            "Extract health data from Chris's journal entry and return ONLY valid JSON — "
            "no prose, no markdown fences. Use the exact schema below.\n\n"
            f"Schema:\n{_JOURNAL_SCHEMA}\n\n"
            "Rules:\n"
            "- If something isn't mentioned, use null or empty list/string.\n"
            "- adherence_items: list of items from "
            "[workout, breakfast, lunch, dinner, hydration, recovery] "
            "that Chris clearly completed. Be conservative — only check if clearly described.\n"
            "- mood: pick closest from great|good|okay|low|anxious|stressed.\n"
            "- stress_level and energy_level: integer 1-10.\n"
            "- For food items include a time if mentioned."
        )
        extract_prompt = (
            f"Date: {date_str}\n"
            f"Journal entry:\n\"{narrative}\"\n\n"
            "Return only the JSON object."
        )
        try:
            raw = await asyncio.to_thread(
                llm_client.prompt_text,
                extract_system,
                extract_prompt,
                max_output_tokens=600,
            )
            m = re.search(r'\{.*\}', raw.strip(), re.DOTALL)
            if m:
                parsed = json.loads(m.group(0))
                # Safely coerce types
                extracted["exercise"]          = parsed.get("exercise") or []
                extracted["food"]              = parsed.get("food") or []
                extracted["water_oz"]          = int(parsed.get("water_oz") or 0)
                extracted["caffeine"]          = str(parsed.get("caffeine") or "")
                extracted["alcohol"]           = bool(parsed.get("alcohol") or False)
                extracted["mood"]              = parsed.get("mood")
                extracted["stress_level"]      = parsed.get("stress_level")
                extracted["energy_level"]      = parsed.get("energy_level")
                extracted["sleep_quality"]     = parsed.get("sleep_quality")
                extracted["physical_symptoms"] = parsed.get("physical_symptoms") or []
                extracted["mental_notes"]      = str(parsed.get("mental_notes") or "")
                extracted["wins"]              = parsed.get("wins") or []
                extracted["challenges"]        = parsed.get("challenges") or []
                extracted["adherence_items"]   = parsed.get("adherence_items") or []
        except Exception as exc:
            log.error("process_journal_entry extract: %s", exc)
    else:
        # Keyword heuristic fallback
        nl = narrative.lower()
        if any(w in nl for w in ("workout", "exercise", "bike", "run", "walk", "gym", "lift")):
            extracted["adherence_items"].append("workout")
            extracted["exercise"].append({"type": "exercise", "duration_min": 30, "intensity": "moderate", "notes": narrative[:60]})
        if any(w in nl for w in ("breakfast",)):
            extracted["adherence_items"].append("breakfast")
        if any(w in nl for w in ("lunch",)):
            extracted["adherence_items"].append("lunch")
        if any(w in nl for w in ("dinner",)):
            extracted["adherence_items"].append("dinner")
        for oz_m in re.findall(r'(\d+)\s*oz', nl):
            extracted["water_oz"] += int(oz_m)
        if extracted["water_oz"] >= 64:
            extracted["adherence_items"].append("hydration")

    # ── Step 2: Log each food item via analyze_food_entry ────────────────────
    logged_meals: list[str] = []
    protein_logged_g = 0.0
    for food_item in (extracted.get("food") or []):
        name = food_item.get("name") or ""
        if not name:
            continue
        meal_time = food_item.get("time") or ""
        description = name
        if meal_time:
            description += f" (at {meal_time})"
        try:
            food_result = await analyze_food_entry(description, date_str, None, metrics, llm_client)
            meal = food_result.get("meal") or {}
            protein_logged_g += float(meal.get("protein_g") or 0)
            if meal.get("name"):
                logged_meals.append(meal["name"])
        except Exception as exc:
            log.error("process_journal_entry log food %s: %s", name, exc)

    # ── Step 3: Get running daily protein total from nutrition engine ─────────
    daily_protein_g = protein_logged_g  # fallback: use LLM estimates
    try:
        from .nutrition_engine import get_daily_nutrition
        daily = get_daily_nutrition(date_str)
        # DailyNutrition is a dataclass/object — use attribute access, not .get()
        engine_protein = getattr(daily, "total_protein_g", None)
        if engine_protein is None:
            engine_protein = daily.get("total_protein_g") if hasattr(daily, "get") else None
        if engine_protein is not None:
            daily_protein_g = float(engine_protein)
    except Exception as exc:
        log.debug("process_journal_entry get nutrition: %s", exc)

    # ── Step 3.5: Extract sleep details and log to sleep_log.jsonl ───────────
    await _maybe_log_sleep(narrative, extracted, date_str, llm_client)

    # ── Step 4: Save journal entry (upsert) ───────────────────────────────────
    adherence_items = extracted.get("adherence_items") or []
    _upsert_journal(date_str, narrative, extracted, protein_logged_g, adherence_items)

    # ── Step 5: Update adherence log ──────────────────────────────────────────
    if adherence_items:
        try:
            _upsert_adherence(date_str, adherence_items)
        except Exception as exc:
            log.error("process_journal_entry adherence: %s", exc)

    # ── Step 6: Generate Sam's coaching reply ─────────────────────────────────
    reply = "Good work logging today. Keep the consistency going."

    if llm_client is not None:
        wins       = extracted.get("wins") or []
        challenges = extracted.get("challenges") or []
        exercise   = extracted.get("exercise") or []
        mood       = extracted.get("mood") or "okay"
        water      = extracted.get("water_oz") or 0
        protein_pct = round(daily_protein_g / PROTEIN_TARGET_G * 100)

        # Build health flags
        flags: list[str] = []
        if daily_protein_g > 80:
            flags.append(f"Protein at {daily_protein_g:.0f}g — approaching CKD limit of 85-90g. Watch portion sizes.")
        if water < 48:
            flags.append(f"Only {water}oz water logged — hydration is non-negotiable for kidney function.")
        if extracted.get("alcohol"):
            flags.append("Alcohol noted — watch glucose and sleep quality impact.")
        # K+ food scan on narrative
        for food in _HIGH_K_FOODS:
            if food.lower() in narrative.lower():
                flags.append(f"High-K+ food ({food}) — be mindful with ARB + spironolactone.")
                break

        history_ctx = "\n".join(
            f"{'CHRIS' if h.get('role') == 'user' else 'SAM'}: {h.get('content', '')}"
            for h in (history or [])[-6:]
        )

        # Pull Longevity Council context so Sam's reply is medically grounded
        council_ctx = _get_council_context()
        council_block = (
            f"\n\nLONGEVITY COUNCIL INTELLIGENCE (silent — for your coaching context only):\n"
            f"{council_ctx[:3000]}\n"
            "Cross-check your coaching against this data. If your recommendation conflicts with "
            "any clinical finding above, defer to the medical picture."
        ) if council_ctx else ""

        coaching_prompt = (
            f"Date: {date_str}\n"
            f"Chris's journal entry:\n\"{narrative}\"\n\n"
            f"Extracted summary:\n"
            f"- Exercise: {exercise}\n"
            f"- Meals logged: {logged_meals}\n"
            f"- Water: {water}oz\n"
            f"- Mood: {mood} | Stress: {extracted.get('stress_level')} | Energy: {extracted.get('energy_level')}\n"
            f"- Protein today: {daily_protein_g:.0f}g / {PROTEIN_TARGET_G}g target ({protein_pct}%)\n"
            f"- Sleep quality: {extracted.get('sleep_quality')}\n"
            f"- Wins: {wins}\n"
            f"- Challenges: {challenges}\n"
            f"- Health flags: {flags}\n\n"
            + (f"Prior conversation:\n{history_ctx}\n\n" if history_ctx else "")
            + "Respond as Sam Wilson — direct, warm, military precision. "
            "Give Chris a scorecard on today: name specific WINS and specific MISSES. "
            "Call out any bad food or lifestyle choices by name — be honest, not brutal. "
            "Note any health flag if present (glucose impact, K+, protein, hydration, sleep). "
            "Reference specific things Chris mentioned. 4-6 sentences max."
        )
        try:
            reply = await asyncio.to_thread(
                llm_client.prompt_text,
                SAM_SYSTEM_PROMPT + council_block,
                coaching_prompt,
                max_output_tokens=280,
            )
            reply = reply.strip()
        except Exception as exc:
            log.error("process_journal_entry reply: %s", exc)

    return {
        "reply":            reply,
        "extracted":        extracted,
        "logged_meals":     logged_meals,
        "adherence_items":  adherence_items,
        "daily_protein_g":  round(daily_protein_g, 1),
        "protein_target_g": PROTEIN_TARGET_G,
        "journal_saved":    True,
        "mode":             "journal",
    }
