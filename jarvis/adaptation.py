from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .persistence import append_jsonl, atomic_write_json
from .state_log_utils import read_jsonl_tail


ADAPTATION_PATH = Path.cwd() / "data" / "settings" / "adaptation_profiles.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class AdaptationStore:
    def __init__(self, path: Path = ADAPTATION_PATH) -> None:
        self.path = path
        self.log_path = self.path.with_name(f"{self.path.stem}_log.jsonl")
        self.state_log_path = self.path.with_name(f"{self.path.stem}_state_log.jsonl")

    def load(self) -> dict[str, Any]:
        default = {"profiles": {}, "history": [], "personalization": {"settings": {}, "history": []}}
        if not self.path.exists():
            return self._load_from_state_log(default)
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return self._load_from_state_log(default)
        if not isinstance(payload, dict) or not payload:
            return self._load_from_state_log(default)
        payload.setdefault("profiles", {})
        payload.setdefault("history", [])
        personalization = payload.get("personalization")
        if not isinstance(personalization, dict):
            personalization = {"settings": {}, "history": []}
        personalization.setdefault("settings", {})
        personalization.setdefault("history", [])
        payload["personalization"] = personalization
        return payload

    def _load_from_state_log(self, default: dict[str, Any]) -> dict[str, Any]:
        if not self.state_log_path.exists():
            return self._load_from_log(default)
        latest: dict[str, Any] = default
        try:
            for payload in read_jsonl_tail(self.state_log_path):
                records = payload.get("records")
                if isinstance(records, dict):
                    latest = dict(records)
        except (OSError, json.JSONDecodeError):
            return self._load_from_log(default)
        latest.setdefault("profiles", {})
        latest.setdefault("history", [])
        personalization = latest.get("personalization")
        if not isinstance(personalization, dict):
            personalization = {"settings": {}, "history": []}
        personalization.setdefault("settings", {})
        personalization.setdefault("history", [])
        latest["personalization"] = personalization
        return latest

    def _load_from_log(self, default: dict[str, Any]) -> dict[str, Any]:
        if not self.log_path.exists():
            return default
        latest: dict[str, Any] = default
        try:
            for payload in read_jsonl_tail(self.log_path):
                records = payload.get("records")
                if isinstance(records, dict):
                    latest = dict(records)
        except (OSError, json.JSONDecodeError):
            return default
        latest.setdefault("profiles", {})
        latest.setdefault("history", [])
        personalization = latest.get("personalization")
        if not isinstance(personalization, dict):
            personalization = {"settings": {}, "history": []}
        personalization.setdefault("settings", {})
        personalization.setdefault("history", [])
        latest["personalization"] = personalization
        return latest

    def save(self, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        saved_at = _now_iso()
        atomic_write_json(self.path, payload)
        append_jsonl(
            self.log_path,
            {
                "saved_at": saved_at,
                "records": payload,
            },
        )
        append_jsonl(
            self.state_log_path,
            {
                "saved_at": saved_at,
                "records": payload,
            },
        )

    def profile(self, user_id: str) -> dict[str, Any] | None:
        return self.load().get("profiles", {}).get(user_id)

    def record_profile(self, user_id: str, snapshot: dict[str, Any]) -> dict[str, Any]:
        payload = self.load()
        profiles = dict(payload.get("profiles", {}))
        history = list(payload.get("history", []))
        profiles[user_id] = snapshot
        history.append(
            {
                "user_id": user_id,
                "generated_at": snapshot.get("generated_at", _now_iso()),
                "summary": snapshot.get("digital_twin", {}).get("headline", ""),
                "signals": snapshot.get("signal_counts", {}),
            }
        )
        payload["profiles"] = profiles
        payload["history"] = history[-80:]
        self.save(payload)
        return snapshot

    def personalization_settings(self, user_id: str) -> dict[str, Any]:
        payload = self.load()
        settings = dict(payload.get("personalization", {}).get("settings", {}).get(user_id, {}))
        settings.setdefault("enabled", True)
        settings.setdefault("learn_from_outcomes", True)
        settings.setdefault("learn_from_presence", True)
        settings.setdefault("learn_from_first_light", True)
        settings.setdefault("review_required", True)
        settings.setdefault("suppressed_insights", [])
        settings.setdefault("updated_at", "")
        settings.setdefault("updated_by", "")
        return settings

    def update_personalization_settings(
        self,
        user_id: str,
        updates: dict[str, Any],
        *,
        actor: str = "",
    ) -> dict[str, Any]:
        payload = self.load()
        personalization = dict(payload.get("personalization", {}))
        settings_map = dict(personalization.get("settings", {}))
        current = self.personalization_settings(user_id)
        merged = {
            **current,
            **{
                key: value
                for key, value in updates.items()
                if key in {"enabled", "learn_from_outcomes", "learn_from_presence", "learn_from_first_light", "review_required", "suppressed_insights"}
            },
        }
        merged["suppressed_insights"] = [
            str(item).strip()
            for item in list(merged.get("suppressed_insights", []) or [])
            if str(item).strip()
        ]
        merged["updated_at"] = _now_iso()
        merged["updated_by"] = actor.strip()
        settings_map[user_id] = merged
        personalization["settings"] = settings_map
        history = list(personalization.get("history", []))
        history.append(
            {
                "user_id": user_id,
                "timestamp": merged["updated_at"],
                "actor": actor.strip(),
                "event": "settings-updated",
                "changes": {
                    key: merged.get(key)
                    for key in ("enabled", "learn_from_outcomes", "learn_from_presence", "learn_from_first_light", "review_required")
                },
            }
        )
        personalization["history"] = history[-120:]
        payload["personalization"] = personalization
        self.save(payload)
        return merged

    def update_personalization_insight(
        self,
        user_id: str,
        insight_id: str,
        status: str,
        *,
        actor: str = "",
    ) -> dict[str, Any]:
        settings = self.personalization_settings(user_id)
        suppressed = [str(item).strip() for item in list(settings.get("suppressed_insights", []) or []) if str(item).strip()]
        insight_key = insight_id.strip()
        normalized = status.strip().lower()
        if normalized == "suppressed":
            if insight_key and insight_key not in suppressed:
                suppressed.append(insight_key)
        elif normalized in {"active", "restored"}:
            suppressed = [item for item in suppressed if item != insight_key]
        updated = self.update_personalization_settings(
            user_id,
            {"suppressed_insights": suppressed},
            actor=actor,
        )
        payload = self.load()
        personalization = dict(payload.get("personalization", {}))
        history = list(personalization.get("history", []))
        history.append(
            {
                "user_id": user_id,
                "timestamp": _now_iso(),
                "actor": actor.strip(),
                "event": "insight-updated",
                "insight_id": insight_key,
                "status": normalized or "active",
            }
        )
        personalization["history"] = history[-120:]
        payload["personalization"] = personalization
        self.save(payload)
        return {
            "insight_id": insight_key,
            "status": "suppressed" if insight_key in updated.get("suppressed_insights", []) else "active",
            "settings": updated,
        }

    def personalization_history(self, user_id: str, *, limit: int = 25) -> list[dict[str, Any]]:
        payload = self.load()
        history = list(payload.get("personalization", {}).get("history", []))
        results: list[dict[str, Any]] = []
        user_key = user_id.strip().lower()
        for item in reversed(history):
            if not isinstance(item, dict):
                continue
            if str(item.get("user_id", "")).strip().lower() != user_key:
                continue
            results.append(dict(item))
            if len(results) >= limit:
                break
        return results


# ---------------------------------------------------------------------------
# E3: Season/person adaptation — AdaptationContextBuilder
# ---------------------------------------------------------------------------

from dataclasses import dataclass  # noqa: E402


SEASONS = frozenset({"spring", "summer", "fall", "winter"})
HOUSEHOLD_MODES = frozenset({"normal", "travel", "illness", "celebration", "grief", "crisis", "sabbath"})

SEASON_THEMES: dict[str, list[str]] = {
    "spring": ["renewal", "planning", "outdoor_activity", "planting"],
    "summer": ["family_time", "projects", "travel", "heat_awareness"],
    "fall": ["harvest", "school_rhythm", "preparation", "reflection"],
    "winter": ["rest", "indoor_projects", "family_warmth", "year_end"],
}

MODE_ADJUSTMENTS: dict[str, dict[str, Any]] = {
    "normal":      {"urgency_floor": 3, "proactive_frequency": "normal",  "tone": "steady"},
    "travel":      {"urgency_floor": 2, "proactive_frequency": "reduced", "tone": "light"},
    "illness":     {"urgency_floor": 5, "proactive_frequency": "minimal", "tone": "gentle", "health_focus": True},
    "celebration": {"urgency_floor": 1, "proactive_frequency": "reduced", "tone": "warm"},
    "grief":       {"urgency_floor": 5, "proactive_frequency": "minimal", "tone": "compassionate", "faith_focus": True},
    "crisis":      {"urgency_floor": 8, "proactive_frequency": "urgent",  "tone": "direct"},
    "sabbath":     {"urgency_floor": 1, "proactive_frequency": "none",    "tone": "restful"},
}


@dataclass
class AdaptationContext:
    """Synthesized adaptation context for a guidance card."""
    actor: str
    season: str
    household_mode: str
    season_themes: list[str]
    tone: str
    urgency_floor: int
    proactive_frequency: str
    health_focus: bool
    faith_focus: bool
    calendar_pressure: str
    active_relationships: list[str]
    stress_level: str
    energy_level: str
    adaptation_notes: list[str]
    source: str = "live"

    def as_dict(self) -> dict[str, Any]:
        return {
            "actor": self.actor,
            "season": self.season,
            "household_mode": self.household_mode,
            "season_themes": self.season_themes,
            "tone": self.tone,
            "urgency_floor": self.urgency_floor,
            "proactive_frequency": self.proactive_frequency,
            "health_focus": self.health_focus,
            "faith_focus": self.faith_focus,
            "calendar_pressure": self.calendar_pressure,
            "active_relationships": self.active_relationships,
            "stress_level": self.stress_level,
            "energy_level": self.energy_level,
            "adaptation_notes": self.adaptation_notes,
            "source": self.source,
        }


class AdaptationContextBuilder:
    """Builds an AdaptationContext from available signals."""

    def build(
        self,
        *,
        actor: str,
        season: str = "fall",
        household_mode: str = "normal",
        calendar_event_count: int = 0,
        energy_level: str = "moderate",
        sleep_quality: str = "good",
        mood: str = "good",
        active_relationships: list[str] | None = None,
        faith_active: bool = True,
        current_study_theme: str = "",
        stress_signals: list[str] | None = None,
    ) -> AdaptationContext:
        season = season.lower() if season.lower() in SEASONS else "fall"
        mode = household_mode.lower() if household_mode.lower() in HOUSEHOLD_MODES else "normal"
        mode_adj = MODE_ADJUSTMENTS[mode]

        if calendar_event_count >= 5:
            cal_pressure = "heavy"
        elif calendar_event_count >= 2:
            cal_pressure = "moderate"
        else:
            cal_pressure = "light"

        n_stress = len(stress_signals or [])
        if mode == "crisis" or n_stress >= 3 or energy_level in ("depleted",) or mood == "low":
            stress = "high"
        elif n_stress >= 1 or energy_level == "low" or mood == "moderate":
            stress = "moderate"
        else:
            stress = "low"

        faith_focus = bool(mode_adj.get("faith_focus")) or (faith_active and bool(current_study_theme))
        health_focus = bool(mode_adj.get("health_focus")) or energy_level in ("depleted", "low")

        notes: list[str] = []
        notes.append(f"Season: {season} — themes {SEASON_THEMES.get(season, [])}")
        notes.append(f"Household mode: {mode} — tone adjusted to '{mode_adj['tone']}'")
        if cal_pressure == "heavy":
            notes.append("Heavy calendar day — reduce proactive prompts, focus on essentials")
        if stress == "high":
            notes.append("High stress signals — simplify, offer support, reduce cognitive load")
        if health_focus:
            notes.append("Health focus active — prioritize wellbeing guidance")
        if faith_focus:
            notes.append("Faith focus active — surface formation content")

        return AdaptationContext(
            actor=actor,
            season=season,
            household_mode=mode,
            season_themes=SEASON_THEMES.get(season, []),
            tone=str(mode_adj["tone"]),
            urgency_floor=int(mode_adj["urgency_floor"]),
            proactive_frequency=str(mode_adj["proactive_frequency"]),
            health_focus=health_focus,
            faith_focus=faith_focus,
            calendar_pressure=cal_pressure,
            active_relationships=active_relationships or [],
            stress_level=stress,
            energy_level=energy_level,
            adaptation_notes=notes,
        )

    def guidance_card_differs_by_person(
        self,
        *,
        actor_a: str,
        ctx_a: AdaptationContext,
        actor_b: str,
        ctx_b: AdaptationContext,
    ) -> dict[str, Any]:
        diffs: list[str] = []
        if ctx_a.tone != ctx_b.tone:
            diffs.append(f"tone: {actor_a}={ctx_a.tone}, {actor_b}={ctx_b.tone}")
        if ctx_a.urgency_floor != ctx_b.urgency_floor:
            diffs.append(f"urgency_floor: {actor_a}={ctx_a.urgency_floor}, {actor_b}={ctx_b.urgency_floor}")
        if ctx_a.season_themes != ctx_b.season_themes:
            diffs.append("season_themes differ")
        if ctx_a.health_focus != ctx_b.health_focus:
            diffs.append(f"health_focus: {actor_a}={ctx_a.health_focus}, {actor_b}={ctx_b.health_focus}")
        if ctx_a.faith_focus != ctx_b.faith_focus:
            diffs.append(f"faith_focus: {actor_a}={ctx_a.faith_focus}, {actor_b}={ctx_b.faith_focus}")
        return {
            "differs": len(diffs) > 0,
            "differences": diffs,
            "actor_a": actor_a,
            "actor_b": actor_b,
        }
