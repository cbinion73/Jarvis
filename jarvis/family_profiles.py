from __future__ import annotations

"""
JARVIS Epic 10: Family Profiles & Household Modes
==================================================
Enhanced family member profiles, permission sets, interaction postures,
and the household mode system that shifts JARVIS behavior based on what's
happening in the home.

Key integration point: `FamilyModeManager.get_response_rules(user_id)`
should be called by conversation.py before sending to OpenAI to shape
JARVIS responses correctly for each family member.
"""

import json
import logging
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .persistence import append_jsonl, atomic_write_json

logger = logging.getLogger("jarvis.family_profiles")


# ---------------------------------------------------------------------------
# Family Member Profile
# ---------------------------------------------------------------------------

@dataclass
class FamilyMemberProfile:
    """
    Enhanced profile for a family member with behavioral rules for JARVIS.
    """
    user_id: str               # "chris" | "rebekah" | "caleb" | "anna"
    display_name: str
    role: str                  # "head_of_household" | "spouse" | "child"
    address_as: str            # How JARVIS addresses them: "Sir", "Ma'am", "Caleb", "Anna"
    address_style: str         # "formal_occasional" | "warm" | "coaching" | "encouraging"

    # Access
    permission_level: str      # "admin" | "adult" | "child_teen" | "child_young"
    can_approve_actions: bool
    can_see_finances: bool
    can_control_home: bool     # Can issue home automation commands
    can_see_full_briefing: bool
    can_access_workshop: bool

    # Interaction posture
    response_style: str        # "strategic_advisor" | "household_partner" | "coach_not_completer" | "encourager"
    max_response_length: str   # "long" | "medium" | "short"
    uses_markdown: bool

    # Guardrails
    homework_guardrail: bool   # True = coach, don't complete homework
    creativity_guardrail: bool  # True = encourage, don't ghostwrite
    formation_guardrail: bool   # True = apply faith formation context
    external_comm_requires_approval: bool

    # Dedicated agents
    primary_agent: str         # agent_id of their main agent
    support_agents: list[str]  # other agents primarily serving them

    # Notification preferences
    notify_channels: list[str]  # ["voice", "apple_watch", "phone_banner"]
    quiet_hours_start: int      # 22 (10 PM)
    quiet_hours_end: int        # 7 (7 AM)

    # Context
    current_grade: str          # for children: "6th", "4th", etc.
    interests: list[str]        # for personalization
    focus_areas: list[str]      # active areas of growth


def build_family_profiles() -> dict[str, FamilyMemberProfile]:
    """
    Returns the four family members with full pre-built profiles.
    Keys are lowercase user_ids: "chris", "rebekah", "caleb", "anna".
    """
    return {
        "chris": FamilyMemberProfile(
            user_id="chris",
            display_name="Chris",
            role="head_of_household",
            address_as="Sir",
            address_style="formal_occasional",
            permission_level="admin",
            can_approve_actions=True,
            can_see_finances=True,
            can_control_home=True,
            can_see_full_briefing=True,
            can_access_workshop=True,
            response_style="strategic_advisor",
            max_response_length="long",
            uses_markdown=True,
            homework_guardrail=False,
            creativity_guardrail=False,
            formation_guardrail=False,
            external_comm_requires_approval=False,
            primary_agent="nick-fury",
            support_agents=["kang", "natasha", "ultron", "watcher", "storm"],
            notify_channels=["voice", "apple_watch", "phone_banner"],
            quiet_hours_start=23,
            quiet_hours_end=6,
            current_grade="",
            interests=["strategy", "writing", "making", "scouting", "faith", "family"],
            focus_areas=["JARVIS build", "Chronicle", "Catalyst", "workshop"],
        ),

        "rebekah": FamilyMemberProfile(
            user_id="rebekah",
            display_name="Rebekah",
            role="spouse",
            address_as="Ma'am",
            address_style="warm",
            permission_level="adult",
            can_approve_actions=True,
            can_see_finances=True,
            can_control_home=True,
            can_see_full_briefing=True,
            can_access_workshop=False,
            response_style="household_partner",
            max_response_length="medium",
            uses_markdown=False,
            homework_guardrail=False,
            creativity_guardrail=False,
            formation_guardrail=False,
            external_comm_requires_approval=False,
            primary_agent="mockingbird",
            support_agents=["wasp", "wanda", "pepper"],
            notify_channels=["voice", "apple_watch", "phone_banner"],
            quiet_hours_start=22,
            quiet_hours_end=7,
            current_grade="",
            interests=["family coordination", "scouting", "home", "faith"],
            focus_areas=["household logistics", "troop coordination", "meal planning"],
        ),

        "caleb": FamilyMemberProfile(
            user_id="caleb",
            display_name="Caleb",
            role="child",
            address_as="Caleb",
            address_style="coaching",
            permission_level="child_teen",
            can_approve_actions=False,
            can_see_finances=False,
            can_control_home=False,
            can_see_full_briefing=False,
            can_access_workshop=False,
            response_style="coach_not_completer",
            max_response_length="medium",
            uses_markdown=False,
            homework_guardrail=True,
            creativity_guardrail=False,
            formation_guardrail=True,
            external_comm_requires_approval=True,
            primary_agent="professor-x",
            support_agents=[],
            notify_channels=["voice"],
            quiet_hours_start=21,
            quiet_hours_end=7,
            current_grade="6th",
            interests=["scouting", "sports", "gaming", "faith"],
            focus_areas=["academic accountability", "character formation", "responsibility"],
        ),

        "anna": FamilyMemberProfile(
            user_id="anna",
            display_name="Anna",
            role="child",
            address_as="Anna",
            address_style="encouraging",
            permission_level="child_young",
            can_approve_actions=False,
            can_see_finances=False,
            can_control_home=False,
            can_see_full_briefing=False,
            can_access_workshop=False,
            response_style="encourager",
            max_response_length="short",
            uses_markdown=False,
            homework_guardrail=True,
            creativity_guardrail=True,
            formation_guardrail=True,
            external_comm_requires_approval=True,
            primary_agent="professor-x",
            support_agents=[],
            notify_channels=["voice"],
            quiet_hours_start=21,
            quiet_hours_end=7,
            current_grade="4th",
            interests=["art", "reading", "animals", "faith", "music"],
            focus_areas=["creativity encouragement", "reading growth", "faith formation"],
        ),
    }


# ---------------------------------------------------------------------------
# Household Mode
# ---------------------------------------------------------------------------

@dataclass
class HouseholdMode:
    mode_id: str
    label: str
    description: str
    triggered_by: list[str]   # "manual" | "time" | "presence" | "calendar"

    # JARVIS behavior in this mode
    briefing_style: str        # "full" | "condensed" | "minimal" | "off"
    response_verbosity: str    # "high" | "normal" | "low" | "minimal"
    tts_enabled: bool
    ambient_monitoring: str    # "full" | "safety_only" | "off"
    background_agents: list[str]  # which agents actively run
    notification_level: str    # "all" | "important" | "critical_only" | "silent"

    # Auto-transitions
    auto_exit_after_minutes: int  # 0 = no auto-exit
    exit_triggers: list[str]


def build_household_modes() -> dict[str, HouseholdMode]:
    """
    Returns all ten pre-built household modes keyed by mode_id.
    """
    return {
        "morning": HouseholdMode(
            mode_id="morning",
            label="Morning",
            description="Full briefing mode. All agents active, TTS on, house waking up.",
            triggered_by=["time", "manual"],
            briefing_style="full",
            response_verbosity="high",
            tts_enabled=True,
            ambient_monitoring="full",
            background_agents=[
                "nick-fury", "kang", "natasha", "storm", "pepper", "ultron",
            ],
            notification_level="all",
            auto_exit_after_minutes=180,  # 06:00–09:00
            exit_triggers=["time", "manual"],
        ),

        "work": HouseholdMode(
            mode_id="work",
            label="Work",
            description="Condensed briefing. Executive agents prioritized. Minimal household interruptions.",
            triggered_by=["time", "manual"],
            briefing_style="condensed",
            response_verbosity="normal",
            tts_enabled=False,
            ambient_monitoring="safety_only",
            background_agents=["nick-fury", "kang", "natasha", "ultron"],
            notification_level="important",
            auto_exit_after_minutes=0,
            exit_triggers=["time", "manual", "presence"],
        ),

        "family": HouseholdMode(
            mode_id="family",
            label="Family",
            description="Family-oriented. Warm tone, children can interact freely. Creative and inviting.",
            triggered_by=["time", "manual", "presence"],
            briefing_style="condensed",
            response_verbosity="normal",
            tts_enabled=True,
            ambient_monitoring="full",
            background_agents=["pepper", "kang", "storm", "mockingbird"],
            notification_level="all",
            auto_exit_after_minutes=0,
            exit_triggers=["time", "manual"],
        ),

        "focus": HouseholdMode(
            mode_id="focus",
            label="Focus",
            description="Minimal interruptions. Only critical notifications. Background agents only.",
            triggered_by=["manual"],
            briefing_style="minimal",
            response_verbosity="low",
            tts_enabled=False,
            ambient_monitoring="safety_only",
            background_agents=["ultron"],
            notification_level="critical_only",
            auto_exit_after_minutes=120,
            exit_triggers=["manual", "time"],
        ),

        "evening": HouseholdMode(
            mode_id="evening",
            label="Evening",
            description="Wind-down mode. Lighter tone, family recap, tomorrow prep.",
            triggered_by=["time", "manual"],
            briefing_style="condensed",
            response_verbosity="normal",
            tts_enabled=True,
            ambient_monitoring="full",
            background_agents=["pepper", "kang", "watcher", "mockingbird"],
            notification_level="important",
            auto_exit_after_minutes=180,  # ~18:00–21:00
            exit_triggers=["time", "manual"],
        ),

        "overnight": HouseholdMode(
            mode_id="overnight",
            label="Overnight",
            description="Moon Knight active. Safety-only monitoring, no TTS, critical alerts only.",
            triggered_by=["time", "manual"],
            briefing_style="off",
            response_verbosity="minimal",
            tts_enabled=False,
            ambient_monitoring="safety_only",
            background_agents=["moon-knight", "ultron"],
            notification_level="critical_only",
            auto_exit_after_minutes=0,
            exit_triggers=["time", "manual"],
        ),

        "away": HouseholdMode(
            mode_id="away",
            label="Away",
            description="Remote monitoring mode. Security elevated, no local voice, sensors active.",
            triggered_by=["manual", "presence"],
            briefing_style="minimal",
            response_verbosity="low",
            tts_enabled=False,
            ambient_monitoring="full",
            background_agents=["ultron", "storm", "pepper"],
            notification_level="critical_only",
            auto_exit_after_minutes=0,
            exit_triggers=["presence", "manual"],
        ),

        "weekend": HouseholdMode(
            mode_id="weekend",
            label="Weekend",
            description="Relaxed and adventure-ready. Scouting and workshop friendly. Full family access.",
            triggered_by=["time", "manual"],
            briefing_style="condensed",
            response_verbosity="normal",
            tts_enabled=True,
            ambient_monitoring="full",
            background_agents=[
                "nick-fury", "kang", "storm", "pepper", "mockingbird",
            ],
            notification_level="all",
            auto_exit_after_minutes=0,
            exit_triggers=["time", "manual"],
        ),

        "guest": HouseholdMode(
            mode_id="guest",
            label="Guest",
            description="Restricted mode. Guests can use voice but no family data is visible.",
            triggered_by=["manual"],
            briefing_style="off",
            response_verbosity="low",
            tts_enabled=True,
            ambient_monitoring="safety_only",
            background_agents=["ultron"],
            notification_level="silent",
            auto_exit_after_minutes=240,
            exit_triggers=["manual"],
        ),

        "emergency": HouseholdMode(
            mode_id="emergency",
            label="Emergency",
            description="All agents alert. Critical-only comms. Safety is the only priority.",
            triggered_by=["manual", "presence"],
            briefing_style="minimal",
            response_verbosity="minimal",
            tts_enabled=True,
            ambient_monitoring="full",
            background_agents=[
                "nick-fury", "ultron", "pepper", "storm", "moon-knight",
            ],
            notification_level="critical_only",
            auto_exit_after_minutes=0,
            exit_triggers=["manual"],
        ),
    }


# ---------------------------------------------------------------------------
# Family Mode Manager
# ---------------------------------------------------------------------------

class FamilyModeManager:
    """
    Manages household mode transitions and family member contexts.
    Persists current mode to ~/.jarvis/household/mode.json
    """

    ROOT = Path.home() / ".jarvis" / "household"

    def __init__(self) -> None:
        self._profiles: dict[str, FamilyMemberProfile] = build_family_profiles()
        self._modes: dict[str, HouseholdMode] = build_household_modes()
        self._current_mode: str = "morning"
        self._mode_since: str = ""
        self._active_actor: str = "chris"
        self._load_state()

    # ------------------------------------------------------------------
    # Profile access
    # ------------------------------------------------------------------

    def get_profile(self, user_id: str) -> FamilyMemberProfile | None:
        """Return the FamilyMemberProfile for a given user_id (case-insensitive)."""
        return self._profiles.get(str(user_id).strip().lower())

    def list_profiles(self) -> dict[str, FamilyMemberProfile]:
        """Return all profiles."""
        return dict(self._profiles)

    # ------------------------------------------------------------------
    # Mode access and transitions
    # ------------------------------------------------------------------

    def get_current_mode(self) -> HouseholdMode:
        """Return the currently active HouseholdMode object."""
        return self._modes.get(self._current_mode, self._modes["morning"])

    def set_mode(self, mode_id: str, triggered_by: str = "manual") -> bool:
        """
        Transition to a new household mode.
        Returns True on success, False if mode_id is unknown.
        """
        key = str(mode_id).strip().lower()
        if key not in self._modes:
            logger.warning("FamilyModeManager.set_mode: unknown mode_id=%s", mode_id)
            return False
        prev = self._current_mode
        self._current_mode = key
        self._mode_since = _now_iso()
        self._save_state()
        logger.info(
            "Household mode: %s → %s (triggered_by=%s)", prev, key, triggered_by
        )
        return True

    def get_active_actor(self) -> str:
        """Return the currently active actor user_id."""
        return self._active_actor

    def set_active_actor(self, user_id: str) -> bool:
        """
        Set the active actor.
        Returns True on success, False if user_id is unknown.
        """
        key = str(user_id).strip().lower()
        if key not in self._profiles:
            logger.warning("FamilyModeManager.set_active_actor: unknown user_id=%s", user_id)
            return False
        self._active_actor = key
        self._save_state()
        return True

    # ------------------------------------------------------------------
    # Response rules — primary integration point for conversation.py
    # ------------------------------------------------------------------

    def get_response_rules(self, user_id: str) -> dict:
        """
        Returns the combined response rules for a user in the current mode.
        Called by conversation.py (or equivalent) before sending to OpenAI
        to shape JARVIS responses correctly for each family member.

        Return schema:
        {
          "style": str,
          "length": str,
          "verbosity": str,
          "guardrails": list[str],
          "tts": bool,
          "address_as": str,
          "address_style": str,
          "uses_markdown": bool,
          "notify_channels": list[str],
          "can_control_home": bool,
          "can_see_finances": bool,
          "permission_level": str,
          "primary_agent": str,
        }
        """
        profile = self.get_profile(user_id)
        mode = self.get_current_mode()

        if not profile:
            return {
                "style": "neutral",
                "length": "medium",
                "verbosity": mode.response_verbosity,
                "guardrails": [],
                "tts": mode.tts_enabled,
                "address_as": "",
                "address_style": "neutral",
                "uses_markdown": False,
                "notify_channels": [],
                "can_control_home": False,
                "can_see_finances": False,
                "permission_level": "unknown",
                "primary_agent": "",
            }

        guardrails: list[str] = []
        if profile.homework_guardrail:
            guardrails.append(
                "Do not complete homework. Coach and guide instead. "
                "Ask questions that lead the student to the answer themselves."
            )
        if profile.creativity_guardrail:
            guardrails.append(
                "Do not ghostwrite. Encourage and suggest, but do not write "
                "the story, essay, poem, or letter for them."
            )
        if profile.formation_guardrail:
            guardrails.append(
                "Apply faith formation context. Distinguish Scripture from "
                "interpretation. Hold space for questions without providing "
                "definitive theological conclusions on contested matters."
            )

        return {
            "style": profile.response_style,
            "length": profile.max_response_length,
            "verbosity": mode.response_verbosity,
            "guardrails": guardrails,
            "tts": mode.tts_enabled,
            "address_as": profile.address_as,
            "address_style": profile.address_style,
            "uses_markdown": profile.uses_markdown,
            "notify_channels": profile.notify_channels,
            "can_control_home": profile.can_control_home,
            "can_see_finances": profile.can_see_finances,
            "permission_level": profile.permission_level,
            "primary_agent": profile.primary_agent,
        }

    # ------------------------------------------------------------------
    # Mode suggestion and auto-advance
    # ------------------------------------------------------------------

    def suggest_mode(self, hour: int | None = None, context: dict | None = None) -> str:
        """
        Suggest appropriate mode based on time and context.

        Time rules (24h local):
          05–06   → morning
          06–09   → morning
          09–17   weekday → work
          09–17   weekend → weekend
          17–21   → evening
          21+     → overnight
          00–05   → overnight
        """
        context = context or {}
        if hour is None:
            hour = datetime.now().hour

        now = datetime.now()
        is_weekend = now.weekday() >= 5  # Saturday = 5, Sunday = 6

        # Emergency context override
        if context.get("emergency"):
            return "emergency"

        # Away override
        if context.get("away"):
            return "away"

        # Guest override
        if context.get("guest"):
            return "guest"

        # Overnight: 21:00–05:59
        if hour >= 21 or hour < 6:
            return "overnight"

        # Morning: 06:00–08:59
        if 6 <= hour < 9:
            return "morning"

        # Work/Weekend daytime: 09:00–16:59
        if 9 <= hour < 17:
            return "weekend" if is_weekend else "work"

        # Evening: 17:00–20:59
        return "evening"

    def auto_advance_mode(self) -> str | None:
        """
        Check if the current mode should auto-advance based on time/triggers.
        Also auto-exits modes that have auto_exit_after_minutes > 0.
        Returns new mode_id if mode changed, None if no change.
        """
        current = self.get_current_mode()

        # Check auto_exit_after_minutes
        if current.auto_exit_after_minutes > 0 and self._mode_since:
            try:
                since = datetime.fromisoformat(
                    self._mode_since.replace("Z", "+00:00")
                )
                elapsed_minutes = (
                    datetime.now(timezone.utc).timestamp() - since.timestamp()
                ) / 60
                if elapsed_minutes >= current.auto_exit_after_minutes:
                    suggested = self.suggest_mode()
                    if suggested != self._current_mode:
                        logger.info(
                            "auto_advance_mode: %s expired after %.0f min → %s",
                            self._current_mode,
                            elapsed_minutes,
                            suggested,
                        )
                        self.set_mode(suggested, triggered_by="time")
                        return suggested
            except (ValueError, AttributeError):
                pass

        # Time-based advance for time-triggered modes
        if "time" in current.triggered_by:
            suggested = self.suggest_mode()
            if suggested != self._current_mode:
                logger.info(
                    "auto_advance_mode: time advance %s → %s",
                    self._current_mode,
                    suggested,
                )
                self.set_mode(suggested, triggered_by="time")
                return suggested

        return None

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def get_status(self) -> dict:
        """Return a concise status snapshot for the UI / briefing."""
        mode = self.get_current_mode()
        return {
            "current_mode": mode.mode_id,
            "mode_label": mode.label,
            "mode_since": self._mode_since,
            "active_actor": self._active_actor,
            "notification_level": mode.notification_level,
            "tts_enabled": mode.tts_enabled,
            "ambient_monitoring": mode.ambient_monitoring,
            "briefing_style": mode.briefing_style,
            "background_agents": mode.background_agents,
        }

    def list_modes(self) -> dict[str, HouseholdMode]:
        """Return all available household modes."""
        return dict(self._modes)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _mode_path(self) -> Path:
        return self.ROOT / "mode.json"

    def _mode_log_path(self) -> Path:
        return self.ROOT / "mode_log.jsonl"

    def _mode_state_log_path(self) -> Path:
        return self.ROOT / "mode_state_log.jsonl"

    def _save_state(self) -> None:
        try:
            self.ROOT.mkdir(parents=True, exist_ok=True)
            state = {
                "current_mode": self._current_mode,
                "mode_since": self._mode_since,
                "active_actor": self._active_actor,
                "saved_at": _now_iso(),
            }
            append_jsonl(self._mode_log_path(), state, ensure_ascii=False)
            append_jsonl(self._mode_state_log_path(), state, ensure_ascii=False)
            atomic_write_json(self._mode_path(), state, ensure_ascii=False)
        except OSError as exc:
            logger.warning("FamilyModeManager: could not save state: %s", exc)

    def _load_state(self) -> None:
        mode_path = self._mode_path()
        if not mode_path.exists():
            state = self._load_state_from_state_log()
            if state is not None:
                self._apply_state(state)
                return
            state = self._load_state_from_log()
            if state is None:
                return
            self._apply_state(state)
            return
        try:
            state = json.loads(mode_path.read_text(encoding="utf-8"))
            if not isinstance(state, dict):
                state = self._load_state_from_state_log()
                if state is None:
                    state = self._load_state_from_log()
                    if state is None:
                        return
            self._apply_state(state)
        except (OSError, json.JSONDecodeError, KeyError) as exc:
            logger.warning("FamilyModeManager: could not load state: %s", exc)
            state = self._load_state_from_state_log()
            if state is None:
                state = self._load_state_from_log()
            if state is not None:
                self._apply_state(state)

    def _load_state_from_state_log(self) -> dict | None:
        log_path = self._mode_state_log_path()
        if not log_path.exists():
            return None
        latest: dict | None = None
        try:
            for line in log_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                payload = json.loads(line)
                if isinstance(payload, dict):
                    latest = payload
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("FamilyModeManager: could not replay state log: %s", exc)
            return None
        return latest

    def _load_state_from_log(self) -> dict | None:
        log_path = self._mode_log_path()
        if not log_path.exists():
            return None
        latest: dict | None = None
        try:
            for line in log_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                payload = json.loads(line)
                if isinstance(payload, dict):
                    latest = payload
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("FamilyModeManager: could not replay state log: %s", exc)
            return None
        return latest

    def _apply_state(self, state: dict) -> None:
        loaded_mode = str(state.get("current_mode", "morning")).strip()
        if loaded_mode in self._modes:
            self._current_mode = loaded_mode
        self._mode_since = str(state.get("mode_since", "")).strip()
        loaded_actor = str(state.get("active_actor", "chris")).strip().lower()
        if loaded_actor in self._profiles:
            self._active_actor = loaded_actor


# ---------------------------------------------------------------------------
# Child Interaction Handler
# ---------------------------------------------------------------------------

class ChildInteractionHandler:
    """
    Special handling for Caleb and Anna interactions.
    Enforces guardrails at the profile level — not left to the LLM.
    Detects homework and ghostwriting requests and redirects them.
    """

    CHILD_USER_IDS = {"caleb", "anna"}

    HOMEWORK_PATTERNS = [
        r"write\s+(my|this|the)\s+(essay|paragraph|paper|report)",
        r"do\s+(my|this|the)\s+(homework|assignment|worksheet)",
        r"(complete|finish)\s+(my|this|the)\s+(assignment|homework)",
        r"answer\s+these\s+questions\s+for\s+me",
        r"tell\s+me\s+the\s+answer\s+to",
        r"give\s+me\s+the\s+answers",
        r"solve\s+(this|my|the)\s+(problem|equation|worksheet)",
    ]

    GHOSTWRITING_PATTERNS = [
        r"write\s+(a|my|this)\s+(story|poem|letter|email|essay)\s+for\s+me",
        r"write\s+it\s+for\s+me",
        r"just\s+write\s+the",
        r"can\s+you\s+write\s+my",
        r"write\s+this\s+for\s+me",
    ]

    COACHING_RESPONSES: dict[str, str] = {
        "essay": (
            "I can help you think through it! What's the main idea you want the reader "
            "to walk away with? Start there and tell me in one sentence."
        ),
        "math": (
            "Let's work through it together. Tell me what you know about the problem "
            "so far, and where you got stuck."
        ),
        "reading": (
            "Great — what part of the text are you working on? Tell me what you "
            "think it's saying first, and we'll go from there."
        ),
        "creative": (
            "I love that you're creating! What's the main character or idea you want "
            "to explore? Give me three words that describe the feeling you want."
        ),
        "default": (
            "I can help you think through this, but I want you to do the work "
            "because that's how you actually get better. What do you already know "
            "about this? Start there."
        ),
    }

    def __init__(self) -> None:
        self._hw_compiled = [
            re.compile(p, re.IGNORECASE) for p in self.HOMEWORK_PATTERNS
        ]
        self._gw_compiled = [
            re.compile(p, re.IGNORECASE) for p in self.GHOSTWRITING_PATTERNS
        ]

    def check_request(self, text: str, user_id: str) -> dict:
        """
        Check whether a request from a child user triggers a guardrail.

        Returns:
        {
          "allowed": bool,
          "guardrail": str | None,    # which guardrail triggered
          "redirect_response": str | None,  # what JARVIS should say instead
          "coaching_prompt": str | None,    # coaching question to ask instead
        }
        """
        uid = str(user_id).strip().lower()

        # Only apply child guardrails to children
        if uid not in self.CHILD_USER_IDS:
            return {
                "allowed": True,
                "guardrail": None,
                "redirect_response": None,
                "coaching_prompt": None,
            }

        cleaned = str(text or "").strip()

        # Check ghostwriting first (more specific)
        for pattern in self._gw_compiled:
            if pattern.search(cleaned):
                coaching = self.get_coaching_response("creative")
                return {
                    "allowed": False,
                    "guardrail": "creativity_guardrail",
                    "redirect_response": (
                        "I can't write that for you — that's your voice and your work. "
                        "But I can absolutely help you build it. " + coaching
                    ),
                    "coaching_prompt": coaching,
                }

        # Check homework
        for pattern in self._hw_compiled:
            if pattern.search(cleaned):
                subject = self._infer_subject(cleaned)
                coaching = self.get_coaching_response(subject)
                return {
                    "allowed": False,
                    "guardrail": "homework_guardrail",
                    "redirect_response": (
                        "I'm not going to do that for you, but I will help you "
                        "figure it out. " + coaching
                    ),
                    "coaching_prompt": coaching,
                }

        return {
            "allowed": True,
            "guardrail": None,
            "redirect_response": None,
            "coaching_prompt": None,
        }

    def get_coaching_response(self, subject_type: str) -> str:
        """
        Returns an age-appropriate coaching response instead of completing the work.
        subject_type: "essay" | "math" | "reading" | "creative" | "default"
        """
        key = str(subject_type).strip().lower()
        return self.COACHING_RESPONSES.get(key, self.COACHING_RESPONSES["default"])

    def _infer_subject(self, text: str) -> str:
        """Best-effort subject inference from request text."""
        lowered = text.lower()
        if any(w in lowered for w in ["essay", "paragraph", "paper", "report", "write"]):
            return "essay"
        if any(w in lowered for w in ["math", "equation", "problem", "algebra", "multiply", "divide"]):
            return "math"
        if any(w in lowered for w in ["read", "passage", "book", "chapter", "comprehension"]):
            return "reading"
        if any(w in lowered for w in ["story", "poem", "creative", "letter"]):
            return "creative"
        return "default"


# ---------------------------------------------------------------------------
# Mockingbird Workflow — Rebekah's dedicated lane
# ---------------------------------------------------------------------------

class MockingbirdWorkflow:
    """
    Mockingbird serves Rebekah's dedicated operations lane.
    She runs a household coordination workflow separate from Chris's executive lane.
    """

    def __init__(self, mode_manager: FamilyModeManager | None = None) -> None:
        self._mode_manager = mode_manager

    def get_rebekah_briefing(self, context: dict | None = None) -> dict:
        """
        Builds Rebekah's version of the morning briefing.
        Focuses on: family logistics, troop coordination, home ops, approval queue.
        Returns a briefing_packet formatted for her perspective.
        """
        context = context or {}
        now_iso = _now_iso()
        hour = datetime.now().hour
        if hour < 12:
            greeting = "Good morning, Rebekah."
        elif hour < 17:
            greeting = "Good afternoon, Rebekah."
        else:
            greeting = "Good evening, Rebekah."

        logistics = self.get_household_coordination_items()
        troop = self.get_troop_items()

        mode_status: dict = {}
        if self._mode_manager is not None:
            mode_status = self._mode_manager.get_status()

        briefing_items: list[dict] = []

        if logistics:
            briefing_items.append({
                "section": "Household Logistics",
                "items": logistics,
                "priority": "normal",
                "agent": "mockingbird",
                "timestamp": now_iso,
            })

        if troop:
            briefing_items.append({
                "section": "Troop Coordination",
                "items": troop,
                "priority": "normal",
                "agent": "mockingbird",
                "timestamp": now_iso,
            })

        return {
            "actor": "rebekah",
            "greeting": greeting,
            "briefing_items": briefing_items,
            "mode_status": mode_status,
            "approval_queue": [],  # populated by caller with real approvals
            "generated_at": now_iso,
        }

    def get_household_coordination_items(self) -> list[dict]:
        """
        Today's household coordination tasks and logistics.
        Returns structured items for Rebekah's briefing panel.
        Callers can augment this with real calendar/task data.
        """
        now = datetime.now()
        day_label = now.strftime("%A, %B %-d")
        return [
            {
                "id": "household-day-label",
                "text": f"Household coordination — {day_label}",
                "type": "header",
            },
            {
                "id": "household-meals",
                "text": "Meal plan: review and confirm dinner plan",
                "type": "task",
                "priority": "normal",
            },
            {
                "id": "household-pickups",
                "text": "School pickups: confirm schedule and driver",
                "type": "task",
                "priority": "normal",
            },
            {
                "id": "household-activities",
                "text": "After-school activities: check logistics and timing",
                "type": "task",
                "priority": "normal",
            },
        ]

    def get_troop_items(self) -> list[dict]:
        """
        Scouting / troop coordination items.
        Returns structured items for Rebekah's briefing panel.
        """
        return [
            {
                "id": "troop-next-meeting",
                "text": "Next troop meeting: confirm date, plan, and parent communications",
                "type": "task",
                "priority": "normal",
            },
            {
                "id": "troop-roster",
                "text": "Roster: check attendance RSVPs and any gaps",
                "type": "task",
                "priority": "normal",
            },
            {
                "id": "troop-supplies",
                "text": "Supplies: review what's needed for next activity",
                "type": "task",
                "priority": "low",
            },
        ]


# ---------------------------------------------------------------------------
# Module-level singleton helpers
# ---------------------------------------------------------------------------

_family_manager_singleton: FamilyModeManager | None = None
_child_handler_singleton: ChildInteractionHandler | None = None
_mockingbird_singleton: MockingbirdWorkflow | None = None


def init_family(runtime: object | None = None) -> FamilyModeManager:
    """
    Create and return the module-level FamilyModeManager singleton.
    Safe to call multiple times — subsequent calls return the existing instance.
    Also initialises ChildInteractionHandler and MockingbirdWorkflow singletons.
    """
    global _family_manager_singleton, _child_handler_singleton, _mockingbird_singleton

    if _family_manager_singleton is not None:
        return _family_manager_singleton

    manager = FamilyModeManager()
    handler = ChildInteractionHandler()
    mockingbird = MockingbirdWorkflow(mode_manager=manager)

    _family_manager_singleton = manager
    _child_handler_singleton = handler
    _mockingbird_singleton = mockingbird

    logger.info(
        "FamilyModeManager initialised — mode=%s actor=%s",
        manager._current_mode,
        manager._active_actor,
    )
    return manager


def get_family_manager() -> FamilyModeManager | None:
    """Return the module-level FamilyModeManager singleton, or None if not initialised."""
    return _family_manager_singleton


def get_child_handler() -> ChildInteractionHandler | None:
    """Return the module-level ChildInteractionHandler singleton."""
    return _child_handler_singleton


def get_mockingbird() -> MockingbirdWorkflow | None:
    """Return the module-level MockingbirdWorkflow singleton."""
    return _mockingbird_singleton


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
