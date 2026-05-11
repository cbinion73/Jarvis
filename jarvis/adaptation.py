from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ADAPTATION_PATH = Path.cwd() / "data" / "settings" / "adaptation_profiles.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class AdaptationStore:
    def __init__(self, path: Path = ADAPTATION_PATH) -> None:
        self.path = path

    def load(self) -> dict[str, Any]:
        default = {"profiles": {}, "history": [], "personalization": {"settings": {}, "history": []}}
        if not self.path.exists():
            return default
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return default
        if not isinstance(payload, dict):
            return default
        payload.setdefault("profiles", {})
        payload.setdefault("history", [])
        personalization = payload.get("personalization")
        if not isinstance(personalization, dict):
            personalization = {"settings": {}, "history": []}
        personalization.setdefault("settings", {})
        personalization.setdefault("history", [])
        payload["personalization"] = personalization
        return payload

    def save(self, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

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
