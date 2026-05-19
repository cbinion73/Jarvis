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
    last_host: str = ""
    last_origin: str = ""
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
        self._heal_device_label(device)
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
        fingerprint = str(payload.get("fingerprint", "")).strip()
        user_agent = str(payload.get("user_agent", "")).strip()
        last_host = str(payload.get("last_host", "")).strip()
        label = str(payload.get("label", "")).strip()

        state["devices"] = self._dedupe_devices(state["devices"])
        existing = next((item for item in state["devices"] if item.device_id == device_id), None)
        if existing is None:
            existing = self._find_existing_session_device(
                state["devices"],
                fingerprint=fingerprint,
                user_agent=user_agent,
                last_host=last_host,
                label=label,
            )
            if existing is not None:
                device_id = existing.device_id
        if existing:
            device = existing
            device.label = str(payload.get("label", device.label)).strip() or device.label or "Browser session"
            device.device_type = str(payload.get("device_type", device.device_type)).strip() or device.device_type or "browser"
            device.room = str(payload.get("room", device.room)).strip() or device.room
            device.user_agent = str(payload.get("user_agent", device.user_agent)).strip() or device.user_agent
            device.fingerprint = fingerprint or device.fingerprint
            device.last_host = str(payload.get("last_host", device.last_host)).strip() or device.last_host
            device.last_origin = str(payload.get("last_origin", device.last_origin)).strip() or device.last_origin
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
                user_agent=user_agent,
                notes=str(payload.get("notes", "")).strip(),
                last_seen_at=_now_iso(),
                fingerprint=fingerprint,
                last_host=last_host,
                last_origin=str(payload.get("last_origin", "")).strip(),
            )
            state["devices"].append(device)
        state = self._sync_member_devices(state)

        resolved_actor = ""
        actor_source = "none"
        stable_suggested = ""
        if not device.shared and device.suggested_default_actor_id:
            recent = [item for item in device.actor_history[:4] if item]
            if recent and len(recent) >= 3 and len(set(recent)) == 1 and recent[0] == device.suggested_default_actor_id:
                stable_suggested = device.suggested_default_actor_id
        if not device.shared:
            resolved_actor = device.default_actor_id or device.owner_user_id or stable_suggested
            if device.default_actor_id or device.owner_user_id:
                actor_source = "device-default"
            elif stable_suggested:
                actor_source = "suggested-default"
            else:
                actor_source = "none"
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
                recent = [item for item in device.actor_history[:4] if item]
                if len(recent) >= 3 and len(set(recent[:3])) == 1:
                    device.suggested_default_actor_id = recent[0]
        elif device.shared:
            device.suggested_default_actor_id = ""
        self._heal_device_label(device, resolved_actor_id=resolved_actor)
        member = next((item for item in state["members"] if item.user_id == resolved_actor), None)
        self._save(state)
        return {
            "device": device.to_dict(),
            "resolved_actor_id": resolved_actor,
            "resolved_actor_label": member.display_name if member else "",
            "shared": device.shared,
            "trust_level": device.trust_level,
            "actor_source": actor_source,
            "auto_resolved": bool(resolved_actor and actor_source == "suggested-default"),
        }

    def _find_existing_session_device(
        self,
        devices: list[DeviceIdentity],
        *,
        fingerprint: str,
        user_agent: str,
        last_host: str,
        label: str,
    ) -> DeviceIdentity | None:
        ranked = sorted(
            devices,
            key=lambda item: (str(item.last_seen_at or ""), bool(item.owner_user_id or item.default_actor_id)),
            reverse=True,
        )
        if fingerprint:
            exact = [item for item in ranked if str(item.fingerprint).strip() == fingerprint]
            if last_host:
                host_match = [item for item in exact if str(item.last_host).strip() == last_host]
                if host_match:
                    return host_match[0]
            if exact:
                return exact[0]
        if user_agent:
            same_agent = [item for item in ranked if str(item.user_agent).strip() == user_agent]
            if last_host:
                host_match = [item for item in same_agent if str(item.last_host).strip() == last_host]
                if host_match:
                    return host_match[0]
            if label:
                label_match = [item for item in same_agent if str(item.label).strip() == label]
                if label_match:
                    return label_match[0]
        return None

    def _dedupe_devices(self, devices: list[DeviceIdentity]) -> list[DeviceIdentity]:
        grouped: dict[tuple[str, str, str], DeviceIdentity] = {}
        passthrough: list[DeviceIdentity] = []
        ordered = sorted(devices, key=lambda item: str(item.last_seen_at or ""), reverse=True)
        for item in ordered:
            fingerprint = str(item.fingerprint or "").strip()
            user_agent = str(item.user_agent or "").strip()
            label = str(item.label or "").strip()
            key = (fingerprint, user_agent, label)
            if not fingerprint and not user_agent:
                passthrough.append(item)
                continue
            existing = grouped.get(key)
            if existing is None:
                grouped[key] = item
                continue
            grouped[key] = self._merge_device_records(existing, item)
        merged = list(grouped.values()) + passthrough
        merged = self._merge_physical_device_duplicates(merged)
        merged.sort(key=lambda item: str(item.last_seen_at or ""), reverse=True)
        return merged

    def _merge_physical_device_duplicates(self, devices: list[DeviceIdentity]) -> list[DeviceIdentity]:
        grouped: dict[tuple[str, str, str], DeviceIdentity] = {}
        passthrough: list[DeviceIdentity] = []
        ordered = sorted(devices, key=lambda item: str(item.last_seen_at or ""), reverse=True)
        for item in ordered:
            key = self._physical_device_signature(item)
            if key is None:
                passthrough.append(item)
                continue
            existing = grouped.get(key)
            if existing is None:
                grouped[key] = item
                continue
            if self._should_merge_physical_duplicates(existing, item):
                grouped[key] = self._merge_device_records(existing, item)
            else:
                passthrough.append(item)
        return list(grouped.values()) + passthrough

    def _should_merge_physical_duplicates(self, first: DeviceIdentity, second: DeviceIdentity) -> bool:
        if first.shared or second.shared:
            return False
        if bool(first.owner_user_id or first.default_actor_id) != bool(second.owner_user_id or second.default_actor_id):
            return True
        first_generic = self._is_generic_device_label(first.label)
        second_generic = self._is_generic_device_label(second.label)
        if first_generic != second_generic:
            return True
        return first.device_type == second.device_type

    def _physical_device_signature(self, device: DeviceIdentity) -> tuple[str, str, str] | None:
        hardware = self._inferred_hardware_label(device)
        device_type = str(device.device_type or "").strip().lower()
        if device_type == "browser":
            device_type = "desktop" if hardware in {"Mac", "Windows PC", "Linux Device"} else device_type
        width = ""
        height = ""
        fingerprint = str(device.fingerprint or "").strip()
        if fingerprint:
            parts = fingerprint.split("|")
            if len(parts) >= 4:
                width = parts[-2].strip()
                height = parts[-1].strip()
        if not width or not height:
            return None
        platform = "mobile" if device_type in {"phone", "tablet"} else "desktop"
        return (hardware, f"{width}x{height}", platform)

    def _merge_device_records(self, primary: DeviceIdentity, secondary: DeviceIdentity) -> DeviceIdentity:
        primary.owner_user_id = primary.owner_user_id or secondary.owner_user_id
        primary.default_actor_id = primary.default_actor_id or secondary.default_actor_id
        primary.trust_level = primary.trust_level or secondary.trust_level or "trusted"
        primary.shared = bool(primary.shared or secondary.shared)
        primary.room = primary.room or secondary.room
        primary.always_available = bool(primary.always_available or secondary.always_available)
        primary.user_agent = primary.user_agent or secondary.user_agent
        primary.notes = primary.notes or secondary.notes
        primary.fingerprint = primary.fingerprint or secondary.fingerprint
        if not primary.last_host and secondary.last_host:
            primary.last_host = secondary.last_host
        if not primary.last_origin and secondary.last_origin:
            primary.last_origin = secondary.last_origin
        primary.last_actor_id = primary.last_actor_id or secondary.last_actor_id
        primary.last_actor_source = primary.last_actor_source or secondary.last_actor_source
        merged_history = [item for item in list(primary.actor_history) + list(secondary.actor_history) if item]
        deduped_history: list[str] = []
        for actor_id in merged_history:
            if actor_id not in deduped_history:
                deduped_history.append(actor_id)
        primary.actor_history = deduped_history[:5]
        primary.suggested_default_actor_id = primary.suggested_default_actor_id or secondary.suggested_default_actor_id
        if str(secondary.last_seen_at or "") > str(primary.last_seen_at or ""):
            primary.last_seen_at = secondary.last_seen_at
        self._heal_device_label(primary)
        return primary

    def _heal_device_label(self, device: DeviceIdentity, *, resolved_actor_id: str = "") -> None:
        if device.shared:
            return
        current_label = str(device.label or "").strip()
        if current_label and not self._is_generic_device_label(current_label):
            return
        actor_id = (
            str(resolved_actor_id or "").strip().lower()
            or str(device.default_actor_id or "").strip().lower()
            or str(device.owner_user_id or "").strip().lower()
            or str(device.suggested_default_actor_id or "").strip().lower()
        )
        if not actor_id:
            return
        actor = self.household.users.get(actor_id)
        if not actor:
            return
        hardware = self._inferred_hardware_label(device)
        if not hardware:
            return
        device.label = f"{actor.display_name} {hardware}".strip()

    def _is_generic_device_label(self, label: str) -> bool:
        normalized = str(label or "").strip().lower()
        if not normalized:
            return True
        generic_labels = {
            "unnamed device",
            "browser session",
            "browser",
            "iphone browser",
            "ipad browser",
            "android phone browser",
            "android tablet browser",
            "mac browser",
            "macos browser",
            "macintel browser",
            "windows pc browser",
            "linux device browser",
        }
        return normalized in generic_labels or normalized.endswith(" browser")

    def _inferred_hardware_label(self, device: DeviceIdentity) -> str:
        user_agent = str(device.user_agent or "").strip().lower()
        device_type = str(device.device_type or "").strip().lower()
        label = str(device.label or "").strip().lower()

        if "iphone" in user_agent or "iphone" in label:
            return "iPhone"
        if "ipad" in user_agent or "ipad" in label:
            return "iPad"
        if "android" in user_agent and "mobile" in user_agent:
            return "Android Phone"
        if "android" in user_agent:
            return "Android Tablet"
        if "macintosh" in user_agent or "mac os x" in user_agent or "macos" in label or "macintel" in label:
            return "Mac"
        if "windows nt" in user_agent:
            return "Windows PC"
        if "linux" in user_agent:
            return "Linux Device"
        if device_type == "phone":
            return "Phone"
        if device_type == "tablet":
            return "Tablet"
        if device_type == "desktop":
            return "Desktop"
        if device_type == "laptop":
            return "Laptop"
        if device_type == "display":
            return "Display"
        return "Device"

    def update_service(self, payload: dict[str, Any]) -> dict[str, Any]:
        state = self.load()
        state["service"] = self._coerce_service({**state["service"], **payload})
        self._save(state)
        return state["service"]

    def prune_devices(
        self,
        *,
        stale_days: int = 7,
        prune_test_like: bool = True,
    ) -> dict[str, Any]:
        state = self.load()
        deduped = self._dedupe_devices(state["devices"])
        kept: list[DeviceIdentity] = []
        removed: list[DeviceIdentity] = []
        now = datetime.now(UTC)

        for item in deduped:
            keep = True
            label = str(item.label or "").strip().lower()
            user_agent = str(item.user_agent or "").strip().lower()
            host = str(item.last_host or "").strip().lower()
            mapped = bool(item.owner_user_id or item.default_actor_id or item.suggested_default_actor_id)

            last_seen = None
            try:
                if item.last_seen_at:
                    last_seen = datetime.fromisoformat(str(item.last_seen_at).replace("Z", "+00:00"))
            except ValueError:
                last_seen = None
            age_days = ((now - last_seen).total_seconds() / 86400.0) if last_seen else 9999

            test_like = prune_test_like and (
                "headlesschrome" in user_agent
                or "electron" in user_agent
                or "codex/" in user_agent
                or label in {"macintel browser"}
            )
            stale_browser = (
                age_days >= stale_days
                and not mapped
                and not item.shared
                and not item.always_available
                and not host.endswith(".ts.net")
            )

            if test_like or stale_browser:
                keep = False

            if keep:
                kept.append(item)
            else:
                removed.append(item)

        state["devices"] = kept
        state = self._sync_member_devices(state)
        self._save(state)
        return {
            "ok": True,
            "removed_count": len(removed),
            "kept_count": len(kept),
            "removed_devices": [item.to_dict() for item in removed[:25]],
        }

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
            last_host=str(payload.get("last_host", "")).strip(),
            last_origin=str(payload.get("last_origin", "")).strip(),
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
