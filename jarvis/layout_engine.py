"""
layout_engine.py — Adaptive Overview layout for JARVIS.

Manages three named modes (Morning Brief, Lunch Brief, Daily Recap) that
auto-activate by time of day, support manual override with 4-hour TTL,
and learn from user interactions to re-rank cards within zones over time.

Zero external dependencies. Degrades gracefully if data files don't exist.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path

from .persistence import append_jsonl, atomic_write_json

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LAYOUT_STATE_PATH    = Path("data/settings/layout_state.json")
INTERACTIONS_LOG     = Path("data/logs/layout_interactions.jsonl")
WEIGHTS_CACHE_PATH   = Path("data/settings/layout_weights_cache.json")
LAYOUT_STATE_LOG_PATH  = LAYOUT_STATE_PATH.with_name(f"{LAYOUT_STATE_PATH.stem}_log.jsonl")
WEIGHTS_CACHE_LOG_PATH = WEIGHTS_CACHE_PATH.with_name(f"{WEIGHTS_CACHE_PATH.stem}_log.jsonl")
MODE_HISTORY_LOG_PATH  = Path("data/family/mode_history_state_log.jsonl")
MANUAL_OVERRIDE_TTL  = 4 * 3600   # seconds — 4 hours, then returns to auto
LEARNING_WINDOW_DAYS = 30
WEIGHTS_CACHE_TTL_H  = 1          # hours — rebuild cache if older than this

_log_lock    = threading.Lock()
_cache_dirty = False               # set True after log_interaction; cleared after rebuild

# ---------------------------------------------------------------------------
# Mode definitions — single source of truth
# ---------------------------------------------------------------------------

MODES: dict[str, dict] = {
    "morning_brief": {
        "label":      "Morning Brief",
        "icon":       "🌅",
        "time_range": (5, 11),   # 5am – 11am
        "defaults": {
            "sam":        "hero",
            "briefing":   "hero",
            "calendar":   "priority",
            "approvals":  "priority",
            "health":     "priority",
            "tasks":      "priority",
            "reminders":  "ambient",
            "email":      "ambient",
            "finance":    "ambient",
            "dining":     "ambient",
            "agents":     "ambient",
            "catalyst":   "ambient",
            "chronicle":  "ambient",
            "publishing": "ambient",
            "forge":      "ambient",
            "vision":     "ambient",
            "idea_inbox": "ambient",
            "maps_usage":     "ambient",
            "jarvis_costs":   "ambient",
        },
    },
    "lunch_brief": {
        "label":      "Lunch Brief",
        "icon":       "☀️",
        "time_range": (11, 17),  # 11am – 5pm
        "defaults": {
            "briefing":   "ambient",
            "calendar":   "hero",
            "tasks":      "hero",
            "approvals":  "priority",
            "reminders":  "priority",
            "email":      "priority",
            "finance":    "priority",
            "dining":     "priority",
            "sam":        "ambient",
            "health":     "ambient",
            "agents":     "ambient",
            "catalyst":   "ambient",
            "chronicle":  "ambient",
            "publishing": "ambient",
            "forge":      "ambient",
            "vision":     "ambient",
            "idea_inbox": "ambient",
            "maps_usage":     "ambient",
            "jarvis_costs":   "ambient",
        },
    },
    "daily_recap": {
        "label":      "Daily Recap",
        "icon":       "🌙",
        "time_range": (17, 24),  # 5pm – midnight
        "defaults": {
            "sam":        "hero",
            "health":     "hero",
            "approvals":  "priority",
            "finance":    "priority",
            "dining":     "priority",
            "briefing":   "priority",
            "calendar":   "priority",
            "tasks":      "priority",
            "reminders":  "ambient",
            "email":      "ambient",
            "agents":     "ambient",
            "catalyst":   "ambient",
            "chronicle":  "ambient",
            "publishing": "ambient",
            "forge":      "ambient",
            "vision":     "ambient",
            "idea_inbox": "ambient",
            "maps_usage":     "ambient",
            "jarvis_costs":   "ambient",
        },
    },
}

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now_utc().isoformat()


def _load_state() -> dict:
    try:
        if LAYOUT_STATE_PATH.exists():
            return json.loads(LAYOUT_STATE_PATH.read_text())
    except Exception:
        return _load_state_from_log()
    if not LAYOUT_STATE_PATH.exists():
        return _load_state_from_log()
    return {}


def _load_state_from_log() -> dict:
    try:
        if LAYOUT_STATE_LOG_PATH.exists():
            latest: dict = {}
            for line in LAYOUT_STATE_LOG_PATH.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                payload = json.loads(line)
                records = payload.get("records")
                if isinstance(records, dict):
                    latest = dict(records)
            return latest
    except Exception:
        pass
    return {}


def _save_state(state: dict) -> None:
    try:
        atomic_write_json(LAYOUT_STATE_PATH, state)
        append_jsonl(
            LAYOUT_STATE_LOG_PATH,
            {
                "saved_at": _now_iso(),
                "records": state,
            },
        )
    except Exception:
        pass


def _load_weights_cache_from_log() -> dict:
    try:
        if WEIGHTS_CACHE_LOG_PATH.exists():
            latest: dict = {}
            for line in WEIGHTS_CACHE_LOG_PATH.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                payload = json.loads(line)
                records = payload.get("records")
                if isinstance(records, dict):
                    latest = dict(records)
            return latest
    except Exception:
        pass
    return {}


def _compute_auto_mode() -> str:
    """Determine mode from current local hour. Never raises."""
    try:
        hour = datetime.now().hour  # local time
        for mode_key, cfg in MODES.items():
            lo, hi = cfg["time_range"]
            if lo <= hour < hi:
                return mode_key
    except Exception:
        pass
    return "morning_brief"  # fallback for midnight–5am and any error


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_current_mode() -> str:
    """
    Return the active mode key.
    Manual override wins if not expired; otherwise delegates to auto-detection.
    Never raises.
    """
    try:
        state = _load_state()
        override_mode    = state.get("override_mode")
        override_expires = state.get("override_expires_at")

        if override_mode and override_expires:
            expires_dt = datetime.fromisoformat(override_expires)
            if _now_utc() < expires_dt:
                return override_mode
            # Expired — clear it silently
            state.pop("override_mode", None)
            state.pop("override_expires_at", None)
            state.pop("override_set_at", None)
            _save_state(state)
    except Exception:
        pass
    return _compute_auto_mode()


def set_mode(mode: str, *, manual: bool = True) -> dict:
    """
    Set the active layout mode.
    manual=True  → writes a 4-hour override (user-initiated).
    manual=False → clears any override (system returning to auto).
    Returns the full state payload dict.
    """
    if mode not in MODES:
        raise ValueError(f"Unknown mode '{mode}'. Valid: {list(MODES)}")

    state = _load_state()
    now   = _now_utc()

    if manual:
        from datetime import timedelta
        expires = now + timedelta(seconds=MANUAL_OVERRIDE_TTL)
        state["override_mode"]       = mode
        state["override_set_at"]     = now.isoformat()
        state["override_expires_at"] = expires.isoformat()
    else:
        state.pop("override_mode",       None)
        state.pop("override_set_at",     None)
        state.pop("override_expires_at", None)

    _save_state(state)

    # Append to mode_history.jsonl (matches existing format)
    try:
        log_path = Path("data/family/mode_history.jsonl")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "mode":      mode,
            "status":    "manual" if manual else "scheduled",
            "reason":    "User selected mode" if manual else "Auto mode resumed",
            "actor":     "Chris" if manual else "system",
            "timestamp": now.isoformat(),
        }
        with _log_lock:
            append_jsonl(log_path, record)
            append_jsonl(
                MODE_HISTORY_LOG_PATH,
                {
                    "saved_at": now.isoformat(),
                    "records": [record],
                },
            )
    except Exception:
        pass

    return _build_state_dict(state, mode)


def log_interaction(card_id: str, mode: str, action: str) -> None:
    """
    Append one card-interaction record to INTERACTIONS_LOG.
    Actions vocabulary: 'click', 'expand', 'navigate', 'dismiss'.
    Thread-safe. Never raises.
    """
    global _cache_dirty
    try:
        INTERACTIONS_LOG.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "ts":      _now_iso(),
            "card_id": card_id,
            "mode":    mode,
            "action":  action,
            "hour":    datetime.now().hour,
        }
        with _log_lock:
            with INTERACTIONS_LOG.open("a") as f:
                f.write(json.dumps(record) + "\n")
        _cache_dirty = True
    except Exception:
        pass


def rebuild_weights_cache() -> dict:
    """
    Compute learned weights for all modes and write to WEIGHTS_CACHE_PATH.
    Called by the startup task and periodic 6-hour job. Returns the cache dict.
    Thread-safe (uses _log_lock). Never raises.
    """
    global _cache_dirty
    cache: dict = {"updated_at": _now_iso(), "weights": {}}
    try:
        for mode in MODES:
            cache["weights"][mode] = get_learned_weights(mode)
        with _log_lock:
            atomic_write_json(WEIGHTS_CACHE_PATH, cache)
            append_jsonl(
                WEIGHTS_CACHE_LOG_PATH,
                {
                    "saved_at": _now_iso(),
                    "records": cache,
                },
            )
        _cache_dirty = False
    except Exception:
        pass
    return cache


def get_cached_weights(mode: str) -> dict[str, float]:
    """
    Return learned weights for a mode.
    Uses the on-disk cache if it is fresh (<= WEIGHTS_CACHE_TTL_H hours old)
    AND not dirty. Otherwise falls back to a live log scan (and triggers a
    background rebuild via the dirty flag).
    Never raises.
    """
    global _cache_dirty
    if not _cache_dirty:
        try:
            if WEIGHTS_CACHE_PATH.exists():
                cache = json.loads(WEIGHTS_CACHE_PATH.read_text())
            else:
                cache = _load_weights_cache_from_log()
            updated_str = cache.get("updated_at", "") if isinstance(cache, dict) else ""
            if updated_str:
                updated = datetime.fromisoformat(updated_str)
                if updated.tzinfo is None:
                    updated = updated.replace(tzinfo=timezone.utc)
                age_h = (_now_utc() - updated).total_seconds() / 3600
                if age_h <= WEIGHTS_CACHE_TTL_H:
                    return cache.get("weights", {}).get(mode, {})
        except Exception:
            try:
                cache = _load_weights_cache_from_log()
                updated_str = cache.get("updated_at", "") if isinstance(cache, dict) else ""
                if updated_str:
                    updated = datetime.fromisoformat(updated_str)
                    if updated.tzinfo is None:
                        updated = updated.replace(tzinfo=timezone.utc)
                    age_h = (_now_utc() - updated).total_seconds() / 3600
                    if age_h <= WEIGHTS_CACHE_TTL_H:
                        return cache.get("weights", {}).get(mode, {})
            except Exception:
                pass
    # Cache miss, stale, or dirty — live scan (cache will be rebuilt by background job)
    return get_learned_weights(mode)


def get_learned_weights(mode: str) -> dict[str, float]:
    """
    Compute card weights for a mode from the last 30 days of interactions.
    Scores: navigate=3, expand=2, click=1, dismiss=-1.
    Normalized 0.0–1.0. Cards with no history → 0.5 (neutral).
    Never raises.
    """
    weights: dict[str, float] = {}
    try:
        if not INTERACTIONS_LOG.exists():
            return {}

        from datetime import timedelta
        cutoff = _now_utc() - timedelta(days=LEARNING_WINDOW_DAYS)
        action_scores = {"navigate": 3, "expand": 2, "click": 1, "dismiss": -1}
        scores: dict[str, float] = {}

        with INTERACTIONS_LOG.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    if rec.get("mode") != mode:
                        continue
                    ts = datetime.fromisoformat(rec["ts"])
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=timezone.utc)
                    if ts < cutoff:
                        continue
                    card  = rec.get("card_id", "")
                    score = action_scores.get(rec.get("action", ""), 0)
                    scores[card] = scores.get(card, 0) + score
                except Exception:
                    continue

        if not scores:
            return {}

        max_score = max(scores.values()) or 1
        for card, score in scores.items():
            weights[card] = max(0.0, min(1.0, score / max_score))
    except Exception:
        pass
    return weights


def get_alert_state(runtime) -> list[dict]:
    """
    Return a list of active alert dicts: {card, zone, level, message}.
    Checks four conditions, each individually guarded. Never raises.
    """
    alerts: list[dict] = []
    try:
        # 1. Pending approvals
        try:
            pending = runtime.list_pending_approvals() if hasattr(runtime, "list_pending_approvals") else []
            n = len(pending)
            if n > 0:
                alerts.append({
                    "card":    "approvals",
                    "zone":    "hero",
                    "level":   "amber",
                    "message": f"{n} approval{'s' if n != 1 else ''} need your attention",
                })
        except Exception:
            pass

        # 2. Health anomalies
        try:
            snap = runtime.dashboard_snapshot() if hasattr(runtime, "dashboard_snapshot") else {}
            health = snap.get("health") or {}
            anomalies = health.get("anomalies") or []
            if anomalies:
                alerts.append({
                    "card":    "health",
                    "zone":    "hero",
                    "level":   "red",
                    "message": f"Health alert: {anomalies[0]}" if isinstance(anomalies[0], str) else "Health anomaly detected",
                })
        except Exception:
            pass

        # 3. Imminent calendar event (< 15 min)
        try:
            snap = runtime.dashboard_snapshot() if hasattr(runtime, "dashboard_snapshot") else {}
            events = snap.get("calendar", {}).get("today_events") or []
            now_ts = _now_utc().timestamp()
            for ev in events:
                start_str = ev.get("start") or ev.get("start_time") or ""
                if not start_str:
                    continue
                start_dt = datetime.fromisoformat(start_str)
                if start_dt.tzinfo is None:
                    start_dt = start_dt.replace(tzinfo=timezone.utc)
                mins_away = (start_dt.timestamp() - now_ts) / 60
                if 0 < mins_away < 15:
                    title = ev.get("title") or ev.get("summary") or "Event"
                    alerts.append({
                        "card":    "calendar",
                        "zone":    "priority",
                        "level":   "blue",
                        "message": f"Starting in {int(mins_away)} min: {title}",
                    })
                    break
        except Exception:
            pass

        # 4. Active critical agent
        try:
            if hasattr(runtime, "scheduler") and runtime.scheduler:
                running = [
                    item for item in runtime.scheduler.get_running()
                    if getattr(item, "priority", 10) <= 2
                ]
                if running:
                    label = getattr(running[0], "agent_label", "Agent")
                    alerts.append({
                        "card":    "agents",
                        "zone":    "priority",
                        "level":   "amber",
                        "message": f"Critical agent active: {label}",
                    })
        except Exception:
            pass

    except Exception:
        pass
    return alerts


def compute_layout(
    mode: str,
    weights: dict[str, float],
    alerts: list[dict],
) -> dict:
    """
    Compute final card → zone assignments.
    Priority: alerts > learned weights > mode defaults.
    Hero cap: 2 cards.
    Returns {hero:[…], priority:[…], ambient:[…]}.
    """
    cfg = MODES.get(mode) or MODES["morning_brief"]
    slots: dict[str, str] = dict(cfg["defaults"])

    # Apply alert overrides (force card into specified zone)
    for alert in alerts:
        card = alert.get("card")
        zone = alert.get("zone")
        if card and zone and card in slots:
            slots[card] = zone

    # Apply learned weights
    for card, weight in weights.items():
        if card not in slots:
            continue
        current_zone = slots[card]
        if weight > 0.85 and current_zone == "priority":
            slots[card] = "hero"
        elif weight > 0.70 and current_zone == "ambient":
            slots[card] = "priority"
        elif weight < 0.20 and current_zone == "hero":
            slots[card] = "priority"

    # Enforce hero cap (max 2 cards)
    hero_cards = [c for c, z in slots.items() if z == "hero"]
    if len(hero_cards) > 2:
        # Keep the first two; demote the rest to priority
        for c in hero_cards[2:]:
            slots[c] = "priority"

    # Build ordered lists (preserve defaults order for stability)
    all_cards = list(cfg["defaults"].keys())
    hero     = [c for c in all_cards if slots.get(c) == "hero"]
    priority = [c for c in all_cards if slots.get(c) == "priority"]
    ambient  = [c for c in all_cards if slots.get(c) == "ambient"]

    return {"hero": hero, "priority": priority, "ambient": ambient}


def get_layout_insights(user_id: str, mode: str, weights: dict) -> list[str]:
    """
    Return up to 3 plain-English insight strings derived from card weights.
    Rule-based: compares weights across cards and modes. Never raises.
    """
    insights: list[str] = []
    try:
        if not weights:
            return insights

        # Find heaviest and lightest cards
        sorted_cards = sorted(weights.items(), key=lambda x: x[1], reverse=True)

        if sorted_cards:
            top_card, top_weight = sorted_cards[0]
            if top_weight >= 0.8:
                label = top_card.replace("_", " ").title()
                insights.append(f"{label} is your most-opened card this week")

        if len(sorted_cards) >= 2:
            bottom_card, bottom_weight = sorted_cards[-1]
            if bottom_weight <= 0.2 and bottom_card not in ("briefing", "sam"):
                label = bottom_card.replace("_", " ").title()
                insights.append(f"{label} is rarely opened — consider moving it to ambient")

        # Morning vs evening comparison: compare morning_brief weights vs daily_recap weights
        try:
            morning_weights = get_cached_weights("morning_brief")
            recap_weights   = get_cached_weights("daily_recap")
            for card in list(weights.keys())[:5]:
                m = morning_weights.get(card, 0.5)
                r = recap_weights.get(card, 0.5)
                label = card.replace("_", " ").title()
                if m > 0 and r > 0 and m / (r + 0.01) >= 2.5:
                    insights.append(f"You check {label} more in the morning than evening")
                    break
                elif r > 0 and m > 0 and r / (m + 0.01) >= 2.5:
                    insights.append(f"{label} gets more attention in the evening")
                    break
        except Exception:
            pass

    except Exception:
        pass

    return insights[:3]


def _build_state_dict(state: dict, mode: str) -> dict:
    return {
        "mode":              mode,
        "auto_mode":         _compute_auto_mode(),
        "manual_override":   bool(state.get("override_mode")),
        "override_expires_at": state.get("override_expires_at"),
        "modes": {
            k: {"label": v["label"], "icon": v["icon"]}
            for k, v in MODES.items()
        },
    }


def get_state_payload(runtime, user_id: str = "chris") -> dict:
    """
    Assemble the full payload for GET /api/layout/state.
    Called from an asyncio.to_thread so it can do blocking I/O.
    """
    mode    = get_current_mode()
    weights = get_cached_weights(mode)
    alerts  = get_alert_state(runtime)
    layout  = compute_layout(mode, weights, alerts)
    state   = _load_state()
    insights = get_layout_insights(user_id, mode, weights)

    return {
        "mode":              mode,
        "auto_mode":         _compute_auto_mode(),
        "manual_override":   bool(state.get("override_mode") and state.get("override_expires_at")),
        "override_expires_at": state.get("override_expires_at"),
        "alerts":            alerts,
        "card_weights":      weights,
        "layout":            layout,
        "insights":          insights,
        "modes": {
            k: {"label": v["label"], "icon": v["icon"]}
            for k, v in MODES.items()
        },
    }
