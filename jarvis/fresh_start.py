from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .accounts import AccountRegistry
from .config import AppConfig
from .family_calendar import FamilyCalendarSupport
from .identity import IdentityRegistry
from .settings import LocationSettingsStore, VoiceSettingsStore


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _now_stamp() -> str:
    return _now_utc().strftime("%Y%m%d-%H%M%S")


@dataclass(slots=True)
class FreshStartProtocol:
    config: AppConfig
    root: Path = Path.cwd()
    data_root: Path = field(init=False)
    backup_root: Path = field(init=False)

    def __post_init__(self) -> None:
        self.data_root = self.root / "data"
        self.backup_root = self.root / "artifacts" / "fresh_start_backups"

    @property
    def preserved_sources(self) -> list[str]:
        return [
            "config/google_client_secret.json",
            "data/agents/life_agents.json",
            "data/google",
            "data/memory/fernet.key",
            "data/settings/accounts.json",
            "data/settings/family_calendar.json",
            "data/trust",
        ]

    @property
    def reset_targets(self) -> list[str]:
        return [
            "data/approvals",
            "data/agents/background_state.json",
            "data/agents/tick_log.jsonl",
            "data/catalyst",
            "data/chat_uploads",
            "data/chronicle",
            "data/content",
            "data/conversations",
            "data/family",
            "data/home",
            "data/logs/actions.jsonl",
            "data/memory/entries.json",
            "data/memory/profile_facts.json",
            "data/memory/proposals.json",
            "data/perception",
            "data/router",
            "data/security",
            "data/settings/adaptation_profiles.json",
            "data/settings/assistant_core.json",
            "data/settings/first_light.json",
            "data/settings/identity.json",
            "data/settings/locations.json",
            "data/settings/shared_doctrine.json",
            "data/settings/voice.json",
            "data/system",
            "data/tutoring",
            "data/wealth",
            "data/weather/storm_weather.json",
            "data/workshop",
        ]

    @property
    def transient_targets(self) -> list[str]:
        return [
            "data/google/pending_oauth.json",
        ]

    def preview(self) -> dict[str, Any]:
        return {
            "mode": "preview",
            "timestamp": _now_utc().isoformat(),
            "preserved_sources": [item for item in self.preserved_sources if self._resolve(item).exists()],
            "reset_targets": [item for item in self.reset_targets if self._resolve(item).exists()],
            "transient_targets": [item for item in self.transient_targets if self._resolve(item).exists()],
            "rebuild_plan": self._rebuild_plan(),
        }

    def execute(self, *, create_backup: bool = True) -> dict[str, Any]:
        started_at = _now_utc().isoformat()
        backup_dir = self.backup_root / _now_stamp() if create_backup else None
        backed_up: list[str] = []
        removed: list[str] = []

        if backup_dir is not None:
            backup_dir.mkdir(parents=True, exist_ok=True)

        for relative in [*self.reset_targets, *self.transient_targets]:
            path = self._resolve(relative)
            if not path.exists():
                continue
            if backup_dir is not None:
                self._backup_path(path, backup_dir / relative)
                backed_up.append(relative)
            self._delete_path(path)
            removed.append(relative)

        rebuilt = self._rebuild_from_sources()
        return {
            "mode": "execute",
            "started_at": started_at,
            "completed_at": _now_utc().isoformat(),
            "backup_dir": str(backup_dir) if backup_dir is not None else "",
            "backed_up": backed_up,
            "removed": removed,
            "preserved_sources": [item for item in self.preserved_sources if self._resolve(item).exists()],
            "rebuilt": rebuilt,
        }

    def _rebuild_from_sources(self) -> dict[str, Any]:
        household = self.config.load_household()

        identity_registry = IdentityRegistry(household)
        identity_defaults = identity_registry.load()
        identity_registry._save(identity_defaults)  # intentional protocol-level reseed

        voice_store = VoiceSettingsStore(self.config)
        voice_defaults = voice_store.defaults()
        voice_store.save(voice_defaults.to_dict())

        location_store = LocationSettingsStore(self.config)
        location_defaults = location_store.defaults()
        location_store.save(location_defaults)

        family_calendar = FamilyCalendarSupport()
        family_calendar_summary = family_calendar.summary(event_limit=6, horizon_days=21)

        accounts = AccountRegistry(household).describe()

        return {
            "identity": {
                "member_count": len(identity_registry.describe().get("members", [])),
                "device_count": len(identity_registry.describe().get("devices", [])),
                "service": identity_registry.describe().get("service", {}),
            },
            "voice": voice_store.describe(),
            "locations": location_store.load(),
            "family_calendar": {
                "configured": bool(family_calendar_summary.get("configured")),
                "detail": family_calendar_summary.get("detail", ""),
                "error": family_calendar_summary.get("error", ""),
                "count": int((family_calendar_summary.get("counts") or {}).get("upcoming_events", 0)),
                "source": (family_calendar_summary.get("calendar") or {}).get("source", ""),
                "label": (family_calendar_summary.get("calendar") or {}).get("label", ""),
            },
            "accounts": {
                "count": len(accounts.get("accounts", [])),
                "accounts": accounts.get("accounts", []),
            },
            "source_checks": {
                "google_client_secret_present": self.config.google_client_secret_path.exists(),
                "google_token_present": self.config.google_token_path.exists(),
                "family_calendar_settings_present": self._resolve("data/settings/family_calendar.json").exists(),
            },
        }

    def _rebuild_plan(self) -> dict[str, Any]:
        return {
            "identity": "Rebuild from household config defaults.",
            "voice": "Reset to provider defaults from environment and available local voices.",
            "locations": "Reset to household-profile home location.",
            "family_calendar": "Preserve Cozi/ICS settings and verify live summary from the upstream feed.",
            "accounts": "Preserve connector account definitions and report their current local metadata.",
            "memory": "Keep encryption key but wipe entries, proposals, and profile facts.",
        }

    def _resolve(self, relative: str) -> Path:
        return self.root / relative

    def _backup_path(self, source: Path, target: Path) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, target, dirs_exist_ok=True)
        else:
            shutil.copy2(source, target)

    def _delete_path(self, path: Path) -> None:
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink(missing_ok=True)
