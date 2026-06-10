"""F2: Level 9 Household Modes.

Situation-based modes that actively drive:
- priorities (what JARVIS focuses on)
- alerts (notification thresholds and types)
- agents (which background agents run)
- rituals (what formation practices are surfaced)
- autonomy limits (what JARVIS may do without approval)
- UI posture (tone, verbosity, surface emphasis)

Level 9 modes: normal, travel, crisis, sabbath, school, health_recovery,
               guest, sprint, emergency

These complement the time-of-day modes in family_profiles.py.
Situation modes override time-of-day modes when active.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any

from .persistence import append_jsonl, atomic_write_json

_MODE_ROOT = Path("data/household/modes")
_MODE_STATE_PATH = _MODE_ROOT / "mode_state.json"
_MODE_HISTORY_PATH = _MODE_ROOT / "mode_history.jsonl"
_MODE_AUDIT_PATH = _MODE_ROOT / "mode_audit.jsonl"


def _ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# ---------------------------------------------------------------------------
# Mode behavior contracts
# ---------------------------------------------------------------------------

@dataclass
class ModeContract:
    """Full behavioral contract for a household situation mode."""
    mode_id: str
    display_name: str
    description: str
    situation: str                      # when this mode applies

    # Priorities (what JARVIS actively surfaces)
    priority_domains: list[str]         # domains to emphasize
    deprioritize_domains: list[str]     # domains to quiet

    # Alerts
    notification_level: str             # all / important / critical_only / silent
    alert_domains: list[str]            # domains that can interrupt in this mode
    suppress_domains: list[str]         # domains whose alerts are suppressed

    # Agents
    required_agents: list[str]          # agents that MUST run
    suspended_agents: list[str]         # agents that MUST NOT run
    optional_agents: list[str]          # agents that may run if available

    # Rituals
    suggested_rituals: list[str]        # rituals to surface
    suppressed_rituals: list[str]       # rituals to quiet

    # Autonomy limits
    autonomy_ceiling: str               # max authority stage allowed in this mode
    requires_approval_for: list[str]    # action families requiring approval
    auto_approves: list[str]            # action families auto-approved (fast path)

    # UI posture
    tone: str                           # steady / urgent / gentle / restful / focused / warm
    verbosity: str                      # high / normal / low / minimal
    briefing_style: str                 # full / condensed / minimal / off
    tts_enabled: bool

    # Mode lifecycle
    max_duration_hours: int             # 0 = indefinite
    auto_exit_triggers: list[str]       # conditions that end this mode
    can_be_set_by: list[str]            # permission levels that can set this mode


# ---------------------------------------------------------------------------
# Level 9 mode definitions
# ---------------------------------------------------------------------------

LEVEL9_MODES: dict[str, ModeContract] = {
    "normal": ModeContract(
        mode_id="normal",
        display_name="Normal",
        description="Standard household operation. All domains active, balanced priorities.",
        situation="Typical day at home with normal family routine.",
        priority_domains=["work", "family", "health"],
        deprioritize_domains=[],
        notification_level="all",
        alert_domains=["health", "security", "family", "work", "finances"],
        suppress_domains=[],
        required_agents=["nick-fury", "kang", "natasha"],
        suspended_agents=[],
        optional_agents=["pepper", "storm", "ultron", "watcher"],
        suggested_rituals=["morning_briefing", "evening_review", "prayer"],
        suppressed_rituals=[],
        autonomy_ceiling="sandbox_live",
        requires_approval_for=["financial", "identity", "public_communication"],
        auto_approves=["notification", "research", "draft_generation"],
        tone="steady",
        verbosity="normal",
        briefing_style="condensed",
        tts_enabled=True,
        max_duration_hours=0,
        auto_exit_triggers=["manual"],
        can_be_set_by=["admin", "adult"],
    ),

    "travel": ModeContract(
        mode_id="travel",
        display_name="Travel",
        description="Away from home. Remote operations, location-aware, reduced home monitoring.",
        situation="Family traveling — at hotel, on road, or visiting family.",
        priority_domains=["navigation", "logistics", "family_safety"],
        deprioritize_domains=["home_automation", "workshop"],
        notification_level="important",
        alert_domains=["health", "security", "family", "navigation"],
        suppress_domains=["home_automation", "workshop", "local_calendar"],
        required_agents=["pepper", "ultron"],
        suspended_agents=["workshop-copilot"],
        optional_agents=["nick-fury", "kang", "storm"],
        suggested_rituals=["travel_prayer", "daily_check_in"],
        suppressed_rituals=["morning_standup", "home_routine"],
        autonomy_ceiling="suggest",
        requires_approval_for=["financial", "identity", "home_automation"],
        auto_approves=["notification", "research", "weather", "navigation"],
        tone="light",
        verbosity="low",
        briefing_style="minimal",
        tts_enabled=True,
        max_duration_hours=0,
        auto_exit_triggers=["location_home", "manual"],
        can_be_set_by=["admin", "adult"],
    ),

    "crisis": ModeContract(
        mode_id="crisis",
        display_name="Crisis",
        description="Active crisis — medical, financial, or safety. All resources redirected.",
        situation="Household facing acute crisis requiring immediate attention.",
        priority_domains=["health", "security", "family_safety", "finances"],
        deprioritize_domains=["work", "learning", "recreation"],
        notification_level="critical_only",
        alert_domains=["health", "security", "family_safety"],
        suppress_domains=["work", "social", "entertainment"],
        required_agents=["pepper", "ultron", "storm"],
        suspended_agents=["workshop-copilot", "content-agent"],
        optional_agents=["nick-fury"],
        suggested_rituals=["crisis_prayer", "support_check_in"],
        suppressed_rituals=["learning_review", "work_standup", "leisure_planning"],
        autonomy_ceiling="suggest",
        requires_approval_for=["financial", "medical_action", "public_communication"],
        auto_approves=["emergency_notification", "safety_alert"],
        tone="urgent",
        verbosity="minimal",
        briefing_style="minimal",
        tts_enabled=True,
        max_duration_hours=48,
        auto_exit_triggers=["manual_close", "resolution_confirmed"],
        can_be_set_by=["admin", "adult"],
    ),

    "sabbath": ModeContract(
        mode_id="sabbath",
        display_name="Sabbath / Rest",
        description="Intentional rest. JARVIS quiets to near-silence. Formation and family only.",
        situation="Sabbath observance or intentional family rest day.",
        priority_domains=["faith", "family", "rest"],
        deprioritize_domains=["work", "finances", "productivity"],
        notification_level="critical_only",
        alert_domains=["health", "security"],
        suppress_domains=["work", "finances", "social_media", "tasks"],
        required_agents=["moon-knight"],
        suspended_agents=["kang", "content-agent", "workshop-copilot"],
        optional_agents=["pepper"],
        suggested_rituals=["sabbath_prayer", "family_devotional", "rest_meditation"],
        suppressed_rituals=["work_standup", "productivity_review", "task_planning"],
        autonomy_ceiling="monitor",
        requires_approval_for=["any_external_action"],
        auto_approves=[],
        tone="restful",
        verbosity="minimal",
        briefing_style="off",
        tts_enabled=False,
        max_duration_hours=24,
        auto_exit_triggers=["time_sunset_to_sunset", "manual"],
        can_be_set_by=["admin", "adult"],
    ),

    "school": ModeContract(
        mode_id="school",
        display_name="School",
        description="School day active. Children's learning prioritized. Parental oversight heightened.",
        situation="Children are doing school — homeschool or in-person school day.",
        priority_domains=["parenting", "education", "family_logistics"],
        deprioritize_domains=["work_deep", "entertainment"],
        notification_level="important",
        alert_domains=["family", "health", "education"],
        suppress_domains=["entertainment", "social_media"],
        required_agents=["pepper", "mockingbird"],
        suspended_agents=[],
        optional_agents=["nick-fury", "kang"],
        suggested_rituals=["morning_school_prayer", "learning_check_in"],
        suppressed_rituals=["leisure_planning"],
        autonomy_ceiling="sandbox_live",
        requires_approval_for=["child_interaction", "external_tutoring"],
        auto_approves=["schedule_notification", "homework_reminder"],
        tone="warm",
        verbosity="normal",
        briefing_style="condensed",
        tts_enabled=True,
        max_duration_hours=8,
        auto_exit_triggers=["time_school_end", "manual"],
        can_be_set_by=["admin", "adult"],
    ),

    "health_recovery": ModeContract(
        mode_id="health_recovery",
        display_name="Health Recovery",
        description="Medical situation or recovery in progress. Health monitoring prioritized, demands reduced.",
        situation="Chris or family member in active health recovery or medical episode.",
        priority_domains=["health", "rest", "care"],
        deprioritize_domains=["work", "finances", "social"],
        notification_level="important",
        alert_domains=["health", "medication", "appointments"],
        suppress_domains=["work", "social_media", "entertainment_heavy"],
        required_agents=["pepper"],
        suspended_agents=["workshop-copilot", "content-agent"],
        optional_agents=["ultron", "storm"],
        suggested_rituals=["healing_prayer", "rest_check_in", "hydration_reminder"],
        suppressed_rituals=["productivity_review", "work_standup"],
        autonomy_ceiling="suggest",
        requires_approval_for=["medical_action", "schedule_change"],
        auto_approves=["health_reminder", "medication_notification"],
        tone="gentle",
        verbosity="minimal",
        briefing_style="minimal",
        tts_enabled=False,
        max_duration_hours=0,
        auto_exit_triggers=["manual_recovery_confirmed"],
        can_be_set_by=["admin", "adult"],
    ),

    "guest": ModeContract(
        mode_id="guest",
        display_name="Guest",
        description="Guests present. Family data hidden. Public-safe interactions only.",
        situation="Non-family guests in home — friends, service workers, or visitors.",
        priority_domains=["hospitality", "security"],
        deprioritize_domains=["family_private", "finances", "health"],
        notification_level="silent",
        alert_domains=["security"],
        suppress_domains=["family_private", "finances", "health", "children"],
        required_agents=["ultron"],
        suspended_agents=["pepper", "mockingbird"],
        optional_agents=[],
        suggested_rituals=["hospitality_greeting"],
        suppressed_rituals=["family_devotional", "health_review", "financial_review"],
        autonomy_ceiling="suggest",
        requires_approval_for=["family_data_access", "financial", "health"],
        auto_approves=["public_information", "weather", "navigation"],
        tone="warm",
        verbosity="low",
        briefing_style="off",
        tts_enabled=True,
        max_duration_hours=8,
        auto_exit_triggers=["guest_departure", "manual"],
        can_be_set_by=["admin", "adult"],
    ),

    "sprint": ModeContract(
        mode_id="sprint",
        display_name="Sprint",
        description="Focused work sprint. Interruptions minimized. Productivity maximized.",
        situation="Committed work sprint — deadline pressure or deliberate deep focus.",
        priority_domains=["work", "catalyst", "publishing"],
        deprioritize_domains=["social", "recreation", "home_management"],
        notification_level="critical_only",
        alert_domains=["health", "family_emergency"],
        suppress_domains=["social_media", "entertainment", "non-urgent_tasks"],
        required_agents=["kang", "nick-fury"],
        suspended_agents=["pepper"],
        optional_agents=["ultron"],
        suggested_rituals=["sprint_prayer", "focus_intention"],
        suppressed_rituals=["leisure_planning", "social_check_in"],
        autonomy_ceiling="sandbox_live",
        requires_approval_for=["financial", "public_communication"],
        auto_approves=["research", "draft_generation", "task_update"],
        tone="focused",
        verbosity="low",
        briefing_style="minimal",
        tts_enabled=False,
        max_duration_hours=4,
        auto_exit_triggers=["timer_complete", "manual"],
        can_be_set_by=["admin", "adult"],
    ),

    "emergency": ModeContract(
        mode_id="emergency",
        display_name="Emergency",
        description="Life or safety emergency. All resources redirected immediately.",
        situation="Fire, medical emergency, security breach, or immediate safety threat.",
        priority_domains=["safety", "health", "family"],
        deprioritize_domains=["work", "finances", "social", "learning"],
        notification_level="all",
        alert_domains=["safety", "health", "family", "security"],
        suppress_domains=["work", "entertainment", "social_media"],
        required_agents=["ultron", "pepper", "moon-knight", "storm"],
        suspended_agents=["workshop-copilot", "content-agent", "kang"],
        optional_agents=["nick-fury"],
        suggested_rituals=["emergency_prayer"],
        suppressed_rituals=["all_non_safety_rituals"],
        autonomy_ceiling="sandbox_live",
        requires_approval_for=["financial_over_100"],
        auto_approves=["emergency_call", "safety_alert", "911_information"],
        tone="urgent",
        verbosity="minimal",
        briefing_style="minimal",
        tts_enabled=True,
        max_duration_hours=12,
        auto_exit_triggers=["emergency_resolved", "manual"],
        can_be_set_by=["admin", "adult", "any_authenticated"],
    ),
}

LEVEL9_MODE_IDS = frozenset(LEVEL9_MODES.keys())


# ---------------------------------------------------------------------------
# Level 9 Mode Manager
# ---------------------------------------------------------------------------

class Level9ModeManager:
    """Manages Level 9 situation-based household modes with full behavior enforcement."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or _MODE_ROOT
        self.root.mkdir(parents=True, exist_ok=True)
        self.state_path = self.root / "mode_state.json"
        self.history_path = self.root / "mode_history.jsonl"
        self.audit_path = self.root / "mode_audit.jsonl"

    # ------------------------------------------------------------------
    # State management
    # ------------------------------------------------------------------

    def _load_state(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return {"current_mode": "normal", "set_at": _ts(), "set_by": "system", "override_reason": ""}
        try:
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        except Exception:
            return {"current_mode": "normal", "set_at": _ts(), "set_by": "system", "override_reason": ""}

    def _save_state(self, state: dict[str, Any]) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self.state_path, state)

    def _audit(self, event: str, actor: str, extra: dict | None = None) -> None:
        record: dict[str, Any] = {"ts": _ts(), "event": event, "actor": actor}
        if extra:
            record.update(extra)
        try:
            append_jsonl(self.audit_path, record)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Mode operations
    # ------------------------------------------------------------------

    def get_current_mode(self) -> ModeContract:
        state = self._load_state()
        mode_id = state.get("current_mode", "normal")
        return LEVEL9_MODES.get(mode_id, LEVEL9_MODES["normal"])

    def get_status(self) -> dict[str, Any]:
        state = self._load_state()
        mode = self.get_current_mode()
        return {
            "current_mode": mode.mode_id,
            "display_name": mode.display_name,
            "description": mode.description,
            "set_at": state.get("set_at", ""),
            "set_by": state.get("set_by", "system"),
            "override_reason": state.get("override_reason", ""),
            "tone": mode.tone,
            "verbosity": mode.verbosity,
            "notification_level": mode.notification_level,
            "autonomy_ceiling": mode.autonomy_ceiling,
            "source": "live",
        }

    def set_mode(
        self,
        mode_id: str,
        actor: str,
        reason: str = "",
        permission_level: str = "adult",
    ) -> dict[str, Any]:
        """Set the current household mode.

        Returns: {ok, mode_id, previous_mode, ...}
        Raises ValueError for unknown mode or insufficient permissions.
        """
        if mode_id not in LEVEL9_MODE_IDS:
            raise ValueError(f"Unknown mode: {mode_id!r}. Valid: {sorted(LEVEL9_MODE_IDS)}")

        mode = LEVEL9_MODES[mode_id]

        # Permission check
        if permission_level not in mode.can_be_set_by and "any_authenticated" not in mode.can_be_set_by:
            raise PermissionError(
                f"Mode '{mode_id}' requires permission level in {mode.can_be_set_by}; "
                f"actor '{actor}' has level '{permission_level}'"
            )

        prev_state = self._load_state()
        prev_mode = prev_state.get("current_mode", "normal")

        new_state = {
            "current_mode": mode_id,
            "set_at": _ts(),
            "set_by": actor,
            "override_reason": reason,
            "previous_mode": prev_mode,
        }
        self._save_state(new_state)

        history_record = {
            "ts": _ts(),
            "event": "mode_changed",
            "from_mode": prev_mode,
            "to_mode": mode_id,
            "actor": actor,
            "reason": reason,
        }
        try:
            append_jsonl(self.history_path, history_record)
        except Exception:
            pass
        self._audit("mode_set", actor, {"from": prev_mode, "to": mode_id, "reason": reason})

        return {
            "ok": True,
            "mode_id": mode_id,
            "previous_mode": prev_mode,
            "display_name": mode.display_name,
            "tone": mode.tone,
            "autonomy_ceiling": mode.autonomy_ceiling,
            "notification_level": mode.notification_level,
            "source": "live",
        }

    def get_behavior_impact(self, mode_id: str | None = None) -> dict[str, Any]:
        """Return the full behavior impact of a mode for UI display."""
        mode = LEVEL9_MODES.get(mode_id or "", self.get_current_mode())
        return {
            "mode_id": mode.mode_id,
            "display_name": mode.display_name,
            "priority_domains": mode.priority_domains,
            "deprioritize_domains": mode.deprioritize_domains,
            "alert_domains": mode.alert_domains,
            "suppress_domains": mode.suppress_domains,
            "required_agents": mode.required_agents,
            "suspended_agents": mode.suspended_agents,
            "suggested_rituals": mode.suggested_rituals,
            "suppressed_rituals": mode.suppressed_rituals,
            "autonomy_ceiling": mode.autonomy_ceiling,
            "tone": mode.tone,
            "verbosity": mode.verbosity,
            "notification_level": mode.notification_level,
            "tts_enabled": mode.tts_enabled,
            "max_duration_hours": mode.max_duration_hours,
            "auto_exit_triggers": mode.auto_exit_triggers,
        }

    def check_action_permitted(
        self,
        action_family: str,
        mode_id: str | None = None,
    ) -> dict[str, Any]:
        """Check whether an action family is permitted in the current (or given) mode."""
        mode = LEVEL9_MODES.get(mode_id or "", self.get_current_mode())
        if action_family in mode.auto_approves:
            return {
                "permitted": True,
                "approval_required": False,
                "reason": f"Action '{action_family}' is auto-approved in {mode.mode_id} mode.",
                "mode_id": mode.mode_id,
            }
        if action_family in mode.requires_approval_for or "any_external_action" in mode.requires_approval_for:
            return {
                "permitted": True,
                "approval_required": True,
                "reason": f"Action '{action_family}' requires explicit approval in {mode.mode_id} mode.",
                "mode_id": mode.mode_id,
            }
        return {
            "permitted": True,
            "approval_required": False,
            "reason": f"Action '{action_family}' is not restricted in {mode.mode_id} mode.",
            "mode_id": mode.mode_id,
        }

    def list_modes(self) -> dict[str, dict[str, Any]]:
        return {
            mode_id: {
                "mode_id": mode.mode_id,
                "display_name": mode.display_name,
                "description": mode.description,
                "situation": mode.situation,
                "tone": mode.tone,
                "autonomy_ceiling": mode.autonomy_ceiling,
            }
            for mode_id, mode in LEVEL9_MODES.items()
        }

    def mode_history(self, limit: int = 20) -> list[dict]:
        if not self.history_path.exists():
            return []
        lines = self.history_path.read_text(encoding="utf-8").strip().splitlines()
        records = []
        for line in lines:
            try:
                records.append(json.loads(line))
            except Exception:
                pass
        return records[-limit:]
