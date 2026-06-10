"""G4: Unified household mode resolver.

Single function of truth: ``get_active_mode_contract()`` always returns
one ``ModeContract``.  The precedence rule is:

    situation mode (Level9ModeManager) overrides time-of-day mode
    (family_profiles) whenever the situation mode is not "normal".

Call sites (scheduler, runtime, apple_api, daily_stewardship) all import
from here.  None of them talk directly to Level9ModeManager or
family_profiles for mode resolution — this is the one gate.

Fail-safe: if any store load fails, returns LEVEL9_MODES["normal"].
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("jarvis.mode_resolver")

# Authority-stage ordering used by G3 (autonomy ceiling enforcement).
# Lower index = less authority.  The ceiling is enforced by sequence number.
STAGE_SEQUENCE: dict[str, int] = {
    "monitor":      0,
    "suggest":      1,
    "sandbox":      2,
    "sandbox_live": 3,
    "live":         4,
}

# Module-level imports — required so tests can patch
# ``jarvis.mode_resolver.Level9ModeManager``.
try:
    from .household_modes import Level9ModeManager, LEVEL9_MODES, ModeContract
except ImportError:
    Level9ModeManager = None  # type: ignore[assignment,misc]
    LEVEL9_MODES = {}         # type: ignore[assignment]
    ModeContract = None       # type: ignore[assignment,misc]


def _normal_contract():
    """Return the 'normal' ModeContract (fail-safe fallback)."""
    return LEVEL9_MODES.get("normal") if LEVEL9_MODES else None


def get_active_mode_contract():
    """Return the currently active ModeContract.

    Situation modes (Level9ModeManager) take precedence over time-of-day
    modes (family_profiles) whenever the situation mode is not 'normal'.

    Always returns a ModeContract — never raises.
    """
    if Level9ModeManager is None or not LEVEL9_MODES:
        return _normal_contract()

    # --- 1. Read situation mode (Level9ModeManager) ---
    try:
        manager = Level9ModeManager()
        situation_mode = manager.get_current_mode()
    except Exception as exc:
        logger.warning("mode_resolver: Level9ModeManager failed (%s) — falling back to normal", exc)
        return _normal_contract()

    # If a non-normal situation mode is active, it wins.
    if situation_mode.mode_id != "normal":
        return situation_mode

    # --- 2. Read time-of-day mode (family_profiles) ---
    # Map family_profiles time-of-day token → Level9 mode_id override.
    # Only a handful of time-of-day tokens have a meaningful Level9 analog;
    # everything else stays "normal".
    TIME_OF_DAY_MAP: dict[str, str] = {
        "night":      "normal",    # quiet_hours handled by posture, not mode
        "morning":    "normal",
        "evening":    "normal",
        "school":     "school",    # maps to Level9 "school" mode
        "sabbath":    "sabbath",   # maps to Level9 "sabbath" mode
        "rest":       "normal",
        "weekend":    "normal",
    }

    try:
        from .family_profiles import get_family_manager
        mgr = get_family_manager()
        if mgr is not None:
            tod_obj = mgr.get_current_mode()           # returns HouseholdMode
            tod_mode = getattr(tod_obj, "mode_id", str(tod_obj))
            mapped = TIME_OF_DAY_MAP.get(str(tod_mode or "").lower(), "normal")
            if mapped != "normal":
                return LEVEL9_MODES.get(mapped, _normal_contract())
    except Exception as exc:
        logger.debug("mode_resolver: family_profiles lookup failed (%s) — using normal", exc)

    return situation_mode  # already "normal"


def get_active_mode_summary() -> dict[str, Any]:
    """Return a compact summary dict for API responses and logging."""
    contract = get_active_mode_contract()
    if contract is None:
        return {
            "mode_id": "normal", "display_name": "Normal",
            "autonomy_ceiling": "sandbox_live", "notification_level": "all",
            "tts_enabled": True, "briefing_style": "condensed",
            "verbosity": "normal", "tone": "steady",
            "suspended_agents": [], "required_agents": [],
            "suppress_domains": [], "alert_domains": [],
            "source": "mode_resolver_fallback",
        }
    return {
        "mode_id":            contract.mode_id,
        "display_name":       contract.display_name,
        "autonomy_ceiling":   contract.autonomy_ceiling,
        "notification_level": contract.notification_level,
        "tts_enabled":        contract.tts_enabled,
        "briefing_style":     contract.briefing_style,
        "verbosity":          contract.verbosity,
        "tone":               contract.tone,
        "suspended_agents":   contract.suspended_agents,
        "required_agents":    contract.required_agents,
        "suppress_domains":   contract.suppress_domains,
        "alert_domains":      contract.alert_domains,
        "source":             "mode_resolver",
    }


def autonomy_ceiling_sequence(mode_id_or_ceiling: str) -> int:
    """Return the sequence number for a mode_id or raw stage string.

    Used by G3 (assess_action_boundary autonomy cap).
    """
    # If it looks like a direct stage name, use that
    if mode_id_or_ceiling in STAGE_SEQUENCE:
        return STAGE_SEQUENCE[mode_id_or_ceiling]

    # Otherwise treat as mode_id and get its ceiling
    if LEVEL9_MODES:
        mode = LEVEL9_MODES.get(mode_id_or_ceiling)
        if mode is not None:
            return STAGE_SEQUENCE.get(mode.autonomy_ceiling, 99)

    return 99  # unknown → don't restrict
