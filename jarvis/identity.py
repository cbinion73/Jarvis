from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .data_hygiene import record_looks_like_test_data
from .models import HouseholdProfile


IDENTITY_PATH = Path.cwd() / "data" / "settings" / "identity.json"


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(slots=True)
class FamilyMemberIdentity:
    user_id: str
    display_name: str
    role: str
    permissions: str
    trust_level: str = "standard"
    privacy_boundary: str = "personal"
    preferred_tone: str = "calm and direct"
    briefing_style: str = "first-light"
    anticipation_style: str = "quietly proactive"
    preferred_voice: str = ""
    voice_aliases: list[str] = field(default_factory=list)
    primary_rooms: list[str] = field(default_factory=list)
    morning_room: str = ""
    notes: str = ""
    priorities: list[str] = field(default_factory=list)
    device_ids: list[str] = field(default_factory=list)
    active: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class DeviceIdentity:
    device_id: str
    label: str
    device_type: str
    owner_user_id: str = ""
    default_actor_id: str = ""
    trust_level: str = "trusted"
    shared: bool = False
    room: str = ""
    always_available: bool = False
    user_agent: str = ""
    notes: str = ""
    last_seen_at: str = ""
    fingerprint: str = ""
    last_actor_id: str = ""
    last_actor_source: str = ""
    actor_history: list[str] = field(default_factory=list)
    suggested_default_actor_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class IdentityRegistry:
    def __init__(self, household: HouseholdProfile, path: Path = IDENTITY_PATH) -> None:
        self.household = household
        self.path = path

    def load(self) -> dict[str, Any]:
        defaults = self._defaults()
        if not self.path.exists():
            return defaults
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return defaults
        members = self._load_members(payload.get("members", []), defaults["members"])
        devices = self._load_devices(payload.get("devices", []))
        data = {
            "members": members,
            "devices": devices,
            "service": self._coerce_service(payload.get("service", defaults["service"])),
            "updated_at": str(payload.get("updated_at", defaults["updated_at"])),
        }
        return self._sync_member_devices(data)

    def describe(self) -> dict[str, Any]:
        state = self.load()
        members = [item.to_dict() for item in state["members"]]
        devices = [item.to_dict() for item in state["devices"]]
        return {
            "members": members,
            "devices": devices,
            "service": state["service"],
            "device_types": [
                {"id": "phone", "label": "Phone"},
                {"id": "tablet", "label": "Tablet"},
                {"id": "laptop", "label": "Laptop"},
                {"id": "desktop", "label": "Desktop"},
                {"id": "display", "label": "Shared Display"},
                {"id": "workshop", "label": "Workshop Device"},
                {"id": "browser", "label": "Browser Session"},
                {"id": "other", "label": "Other"},
            ],
            "trust_levels": [
                {"id": "trusted", "label": "Trusted"},
                {"id": "standard", "label": "Standard"},
                {"id": "child-safe", "label": "Child Safe"},
                {"id": "restricted", "label": "Restricted"},
            ],
            "owners": [{"id": user.user_id, "label": user.display_name} for user in self.household.users.values()],
        }

    def member(self, user_ref: str) -> FamilyMemberIdentity | None:
        target = str(user_ref).strip().lower()
        if not target:
            return None
        for item in self.load()["members"]:
            if item.user_id == target or item.display_name.strip().lower() == target:
                return item
        return None

    def save_member(self, payload: dict[str, Any]) -> FamilyMemberIdentity:
        state = self.load()
        member = self._coerce_member(payload, state["members"])
        next_members: list[FamilyMemberIdentity] = []
        replaced = False
        for item in state["members"]:
            if item.user_id == member.user_id:
                next_members.append(member)
                replaced = True
            else:
                next_members.append(item)
        if not replaced:
            next_members.append(member)
        state["members"] = next_members
        state = self._sync_member_devices(state)
        self._save(state)
        return member

    def save_device(self, payload: dict[str, Any]) -> DeviceIdentity:
        state = self.load()
        existing = next(
            (
                item for item in state["devices"]
                if item.device_id == str(payload.get("device_id", "")).strip()
            ),
            None,
        )
        merged_payload = {**(existing.to_dict() if existing else {}), **payload}
        device = self._coerce_device(merged_payload)
        next_devices: list[DeviceIdentity] = []
        replaced = False
        for item in state["devices"]:
            if item.device_id == device.device_id:
                next_devices.append(device)
                replaced = True
            else:
                next_devices.append(item)
        if not replaced:
            next_devices.append(device)
        state["devices"] = next_devices
        state = self._sync_member_devices(state)
        self._save(state)
        return device

    def bind_session_device(self, payload: dict[str, Any]) -> dict[str, Any]:
        state = self.load()
        device_id = str(payload.get("device_id", "")).strip() or str(uuid.uuid4())
        existing = next((item for item in state["devices"] if item.device_id == device_id), None)
        if existing:
            device = existing
            device.label = str(payload.get("label", device.label)).strip() or device.label or "Browser session"
            device.device_type = str(payload.get("device_type", device.device_type)).strip() or device.device_type or "browser"
            device.room = str(payload.get("room", device.room)).strip() or device.room
            device.user_agent = str(payload.get("user_agent", device.user_agent)).strip() or device.user_agent
            device.fingerprint = str(payload.get("fingerprint", device.fingerprint)).strip() or device.fingerprint
            device.last_seen_at = _now_iso()
        else:
            device = DeviceIdentity(
                device_id=device_id,
                label=str(payload.get("label", "")).strip() or "Browser session",
                device_type=str(payload.get("device_type", "")).strip() or "browser",
                owner_user_id=str(payload.get("owner_user_id", "")).strip().lower(),
                default_actor_id=str(payload.get("default_actor_id", "")).strip().lower(),
                trust_level=str(payload.get("trust_level", "trusted")).strip() or "trusted",
                shared=bool(payload.get("shared", False)),
                room=str(payload.get("room", "")).strip(),
                always_available=bool(payload.get("always_available", False)),
                user_agent=str(payload.get("user_agent", "")).strip(),
                notes=str(payload.get("notes", "")).strip(),
                last_seen_at=_now_iso(),
                fingerprint=str(payload.get("fingerprint", "")).strip(),
            )
            state["devices"].append(device)
        state = self._sync_member_devices(state)

        resolved_actor = ""
        actor_source = "none"
        if not device.shared:
            resolved_actor = device.default_actor_id or device.owner_user_id
            actor_source = "device-default" if resolved_actor else "none"
        session_actor_id = str(payload.get("session_actor_id", "")).strip().lower()
        if device.shared and session_actor_id and session_actor_id in self.household.users:
            resolved_actor = session_actor_id
            actor_source = "session-override"
        if resolved_actor:
            history = [item for item in device.actor_history if item != resolved_actor]
            history.insert(0, resolved_actor)
            device.actor_history = history[:5]
            device.last_actor_id = resolved_actor
            device.last_actor_source = actor_source
            if not device.shared and not device.default_actor_id and not device.owner_user_id:
                recent = device.actor_history[:3]
                if len(recent) == 3 and len(set(recent)) == 1:
                    device.suggested_default_actor_id = recent[0]
        member = next((item for item in state["members"] if item.user_id == resolved_actor), None)
        self._save(state)
        return {
            "device": device.to_dict(),
            "resolved_actor_id": resolved_actor,
            "resolved_actor_label": member.display_name if member else "",
            "shared": device.shared,
            "trust_level": device.trust_level,
            "actor_source": actor_source,
        }

    def update_service(self, payload: dict[str, Any]) -> dict[str, Any]:
        state = self.load()
        state["service"] = self._coerce_service({**state["service"], **payload})
        self._save(state)
        return state["service"]

    def _save(self, state: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "members": [item.to_dict() for item in state["members"]],
            "devices": [item.to_dict() for item in state["devices"]],
            "service": state["service"],
            "updated_at": _now_iso(),
        }
        self.path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def _defaults(self) -> dict[str, Any]:
        members = [
            FamilyMemberIdentity(
                user_id=user.user_id,
                display_name=user.display_name,
                role=user.role,
                permissions=user.permissions,
                trust_level="child-safe" if "child" in user.permissions.lower() else "trusted",
                privacy_boundary="child" if "child" in user.permissions.lower() else "personal",
                priorities=list(user.priorities),
            )
            for user in self.household.users.values()
        ]
        return {
            "members": members,
            "devices": [],
            "service": self._coerce_service({}),
            "updated_at": _now_iso(),
        }

    def _load_members(self, payload: list[Any], defaults: list[FamilyMemberIdentity]) -> list[FamilyMemberIdentity]:
        by_id = {item.user_id: item for item in defaults}
        members: list[FamilyMemberIdentity] = []
        for raw in payload if isinstance(payload, list) else []:
            try:
                member = self._coerce_member(raw, defaults)
            except Exception:
                continue
            by_id.pop(member.user_id, None)
            members.append(member)
        members.extend(by_id.values())
        return members

    def _load_devices(self, payload: list[Any]) -> list[DeviceIdentity]:
        devices: list[DeviceIdentity] = []
        for raw in payload if isinstance(payload, list) else []:
            if record_looks_like_test_data(raw):
                continue
            try:
                devices.append(self._coerce_device(raw))
            except Exception:
                continue
        return devices

    def _coerce_member(self, payload: dict[str, Any], defaults: list[FamilyMemberIdentity]) -> FamilyMemberIdentity:
        user_id = str(payload.get("user_id", "")).strip().lower()
        if user_id not in self.household.users:
            raise ValueError("Unknown household user")
        household_user = self.household.users[user_id]
        existing_default = next((item for item in defaults if item.user_id == user_id), None)
        default = existing_default or FamilyMemberIdentity(
            user_id=household_user.user_id,
            display_name=household_user.display_name,
            role=household_user.role,
            permissions=household_user.permissions,
            priorities=list(household_user.priorities),
        )
        return FamilyMemberIdentity(
            user_id=user_id,
            display_name=str(payload.get("display_name", default.display_name)).strip() or default.display_name,
            role=str(payload.get("role", default.role)).strip() or default.role,
            permissions=str(payload.get("permissions", default.permissions)).strip() or default.permissions,
            trust_level=str(payload.get("trust_level", default.trust_level)).strip() or default.trust_level,
            privacy_boundary=str(payload.get("privacy_boundary", default.privacy_boundary)).strip() or default.privacy_boundary,
            preferred_tone=str(payload.get("preferred_tone", default.preferred_tone)).strip() or default.preferred_tone,
            briefing_style=str(payload.get("briefing_style", default.briefing_style)).strip() or default.briefing_style,
            anticipation_style=str(payload.get("anticipation_style", default.anticipation_style)).strip() or default.anticipation_style,
            preferred_voice=str(payload.get("preferred_voice", default.preferred_voice)).strip(),
            voice_aliases=[str(item).strip() for item in payload.get("voice_aliases", default.voice_aliases) if str(item).strip()],
            primary_rooms=[str(item).strip() for item in payload.get("primary_rooms", default.primary_rooms) if str(item).strip()],
            morning_room=str(payload.get("morning_room", default.morning_room)).strip(),
            notes=str(payload.get("notes", default.notes)).strip(),
            priorities=[str(item).strip() for item in payload.get("priorities", default.priorities) if str(item).strip()],
            device_ids=[str(item).strip() for item in payload.get("device_ids", default.device_ids) if str(item).strip()],
            active=bool(payload.get("active", True)),
        )

    def _coerce_device(self, payload: dict[str, Any]) -> DeviceIdentity:
        owner_user_id = str(payload.get("owner_user_id", "")).strip().lower()
        default_actor_id = str(payload.get("default_actor_id", "")).strip().lower()
        if owner_user_id and owner_user_id not in self.household.users:
            owner_user_id = ""
        if default_actor_id and default_actor_id not in self.household.users:
            default_actor_id = owner_user_id
        return DeviceIdentity(
            device_id=str(payload.get("device_id", "")).strip() or str(uuid.uuid4()),
            label=str(payload.get("label", "")).strip() or "Unnamed device",
            device_type=str(payload.get("device_type", "")).strip() or "other",
            owner_user_id=owner_user_id,
            default_actor_id=default_actor_id,
            trust_level=str(payload.get("trust_level", "trusted")).strip() or "trusted",
            shared=bool(payload.get("shared", False)),
            room=str(payload.get("room", "")).strip(),
            always_available=bool(payload.get("always_available", False)),
            user_agent=str(payload.get("user_agent", "")).strip(),
            notes=str(payload.get("notes", "")).strip(),
            last_seen_at=str(payload.get("last_seen_at", "")).strip(),
            fingerprint=str(payload.get("fingerprint", "")).strip(),
            last_actor_id=str(payload.get("last_actor_id", "")).strip().lower(),
            last_actor_source=str(payload.get("last_actor_source", "")).strip(),
            actor_history=[str(item).strip().lower() for item in payload.get("actor_history", []) if str(item).strip()],
            suggested_default_actor_id=str(payload.get("suggested_default_actor_id", "")).strip().lower(),
        )

    def _coerce_service(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "always_on_enabled": bool(payload.get("always_on_enabled", False)),
            "host_label": str(payload.get("host_label", "Primary JARVIS host")).strip() or "Primary JARVIS host",
            "host_type": str(payload.get("host_type", "desktop")).strip() or "desktop",
            "lan_url": str(payload.get("lan_url", "")).strip(),
            "hostname": str(payload.get("hostname", "jarvis.local")).strip() or "jarvis.local",
            "launch_on_boot": bool(payload.get("launch_on_boot", False)),
            "watchdog_enabled": bool(payload.get("watchdog_enabled", False)),
            "notes": str(payload.get("notes", "Run JARVIS as local infrastructure, not a manual dev process.")).strip(),
        }

    def _sync_member_devices(self, state: dict[str, Any]) -> dict[str, Any]:
        devices: list[DeviceIdentity] = state["devices"]
        device_ids_by_owner: dict[str, list[str]] = {}
        for item in devices:
            if item.owner_user_id:
                device_ids_by_owner.setdefault(item.owner_user_id, []).append(item.device_id)
        next_members: list[FamilyMemberIdentity] = []
        for item in state["members"]:
            item.device_ids = sorted(set(device_ids_by_owner.get(item.user_id, [])))
            next_members.append(item)
        state["members"] = next_members
        return state
