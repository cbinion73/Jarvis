"""F6: Household-operable admin — non-developer controls.

Provides plain-language admin operations for:
- Agents: pause, resume, retire, promote, review
- Memory: inspect, correct, dispute, retire facts
- Modes: set, inspect impact, view history
- Permissions: grant, revoke, inspect
- Autonomy: set autonomy ceiling, inspect current authority
- Devices: add, remove, inspect, permission assignment
- Integrations: enable, disable, inspect sync health
- Audits: view audit log, export, search

All operations are designed for non-developer household users.
No file edits, JSON, scripts, or developer intervention required.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from .persistence import append_jsonl, atomic_write_json

_ADMIN_ROOT = Path("data/household/admin")
_ADMIN_AUDIT_PATH = _ADMIN_ROOT / "admin_audit.jsonl"
_DEVICES_PATH = _ADMIN_ROOT / "devices.json"
_INTEGRATIONS_PATH = _ADMIN_ROOT / "integrations.json"
_PERMISSIONS_PATH = _ADMIN_ROOT / "permissions.json"


def _ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# ---------------------------------------------------------------------------
# Admin permission levels
# ---------------------------------------------------------------------------

ADMIN_PERMISSIONS = frozenset({"admin", "adult", "child", "guest"})

# What each permission level can do in household admin
ADMIN_CAPABILITY_MAP: dict[str, list[str]] = {
    "admin": [
        "set_mode", "manage_agents", "manage_memory", "manage_permissions",
        "manage_devices", "manage_integrations", "view_audit", "view_audit_summary",
        "export_data", "set_autonomy_ceiling", "manage_legacy",
    ],
    "adult": [
        "set_mode", "view_agents", "manage_own_memory", "view_permissions",
        "manage_devices_own", "view_integrations", "view_audit_summary",
    ],
    "child": [
        "view_mode", "view_own_memory",
    ],
    "guest": [
        "view_mode",
    ],
}


@dataclass
class AdminDevice:
    device_id: str
    display_name: str
    device_type: str              # phone/tablet/laptop/smart_speaker/camera/hub
    owner: str                    # family member who owns/uses this
    permission_level: str         # what this device can do
    registered_at: str
    last_seen_at: str = ""
    status: str = "active"        # active/inactive/revoked


@dataclass
class AdminIntegration:
    integration_id: str
    display_name: str
    service_name: str             # google_calendar, notion, home_assistant, etc.
    enabled: bool
    sync_health: str              # healthy/degraded/failed/unconfigured
    last_sync_at: str
    registered_by: str
    registered_at: str
    notes: str = ""


class HouseholdAdminStore:
    """Non-developer household admin operations."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or _ADMIN_ROOT
        self.root.mkdir(parents=True, exist_ok=True)
        self.audit_path = self.root / "admin_audit.jsonl"
        self.devices_path = self.root / "devices.json"
        self.integrations_path = self.root / "integrations.json"
        self.permissions_path = self.root / "permissions.json"

    def _load(self, path: Path) -> list[dict]:
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _save(self, path: Path, records: list[dict]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(path, records)

    def _audit(self, event: str, actor: str, extra: dict | None = None) -> None:
        record: dict[str, Any] = {"ts": _ts(), "event": event, "actor": actor}
        if extra:
            record.update(extra)
        try:
            append_jsonl(self.audit_path, record)
        except Exception:
            pass

    def _check_permission(self, actor_level: str, required_capability: str) -> None:
        caps = ADMIN_CAPABILITY_MAP.get(actor_level, [])
        if required_capability not in caps:
            raise PermissionError(
                f"Permission level '{actor_level}' cannot perform '{required_capability}'. "
                f"Required: admin or adult with appropriate permissions."
            )

    # ------------------------------------------------------------------
    # Capability inspection
    # ------------------------------------------------------------------

    def what_can_i_do(self, actor_level: str) -> dict[str, Any]:
        """Plain-language summary of what this actor can do."""
        caps = ADMIN_CAPABILITY_MAP.get(actor_level, [])
        return {
            "permission_level": actor_level,
            "capabilities": caps,
            "cannot_do": [
                cap for caps_list in ADMIN_CAPABILITY_MAP.values()
                for cap in caps_list
                if cap not in caps
            ],
            "plain_summary": (
                f"As a(n) {actor_level}, you can: {', '.join(caps) if caps else 'view mode only'}."
            ),
            "source": "live",
        }

    # ------------------------------------------------------------------
    # Devices
    # ------------------------------------------------------------------

    def register_device(
        self,
        *,
        display_name: str,
        device_type: str,
        owner: str,
        permission_level: str,
        actor: str,
        actor_level: str = "admin",
    ) -> AdminDevice:
        self._check_permission(actor_level, "manage_devices")
        if permission_level not in ADMIN_PERMISSIONS:
            raise ValueError(f"permission_level must be one of {sorted(ADMIN_PERMISSIONS)}")
        import uuid
        device = AdminDevice(
            device_id=str(uuid.uuid4()),
            display_name=display_name.strip(),
            device_type=device_type,
            owner=owner,
            permission_level=permission_level,
            registered_at=_ts(),
        )
        records = self._load(self.devices_path)
        records.append(asdict(device))
        self._save(self.devices_path, records)
        self._audit("device_registered", actor, {"device_id": device.device_id, "name": display_name})
        return device

    def list_devices(self, actor_level: str = "admin") -> list[dict]:
        self._check_permission(actor_level, "manage_devices")
        return self._load(self.devices_path)

    def revoke_device(self, device_id: str, actor: str, actor_level: str = "admin") -> dict | None:
        self._check_permission(actor_level, "manage_devices")
        records = self._load(self.devices_path)
        updated = None
        for r in records:
            if r.get("device_id") == device_id:
                r["status"] = "revoked"
                updated = r
                break
        if updated:
            self._save(self.devices_path, records)
            self._audit("device_revoked", actor, {"device_id": device_id})
        return updated

    # ------------------------------------------------------------------
    # Integrations
    # ------------------------------------------------------------------

    def register_integration(
        self,
        *,
        display_name: str,
        service_name: str,
        registered_by: str,
        actor_level: str = "admin",
        notes: str = "",
    ) -> AdminIntegration:
        self._check_permission(actor_level, "manage_integrations")
        import uuid
        integration = AdminIntegration(
            integration_id=str(uuid.uuid4()),
            display_name=display_name.strip(),
            service_name=service_name.strip(),
            enabled=False,
            sync_health="unconfigured",
            last_sync_at="",
            registered_by=registered_by,
            registered_at=_ts(),
            notes=notes,
        )
        records = self._load(self.integrations_path)
        records.append(asdict(integration))
        self._save(self.integrations_path, records)
        self._audit("integration_registered", registered_by, {"service": service_name})
        return integration

    def toggle_integration(self, integration_id: str, enabled: bool, actor: str, actor_level: str = "admin") -> dict | None:
        self._check_permission(actor_level, "manage_integrations")
        records = self._load(self.integrations_path)
        updated = None
        for r in records:
            if r.get("integration_id") == integration_id:
                r["enabled"] = enabled
                updated = r
                break
        if updated:
            self._save(self.integrations_path, records)
            self._audit("integration_toggled", actor, {"integration_id": integration_id, "enabled": enabled})
        return updated

    def list_integrations(self, actor_level: str = "adult") -> list[dict]:
        if actor_level not in ("admin", "adult"):
            raise PermissionError("Only admin or adult can view integrations")
        return self._load(self.integrations_path)

    # ------------------------------------------------------------------
    # Permissions
    # ------------------------------------------------------------------

    def grant_permission(
        self,
        *,
        member: str,
        permission_level: str,
        actor: str,
        actor_level: str = "admin",
        reason: str = "",
    ) -> dict[str, Any]:
        self._check_permission(actor_level, "manage_permissions")
        if permission_level not in ADMIN_PERMISSIONS:
            raise ValueError(f"permission_level must be one of {sorted(ADMIN_PERMISSIONS)}")

        records = self._load(self.permissions_path)
        found = False
        for r in records:
            if r.get("member") == member:
                r["permission_level"] = permission_level
                r["updated_at"] = _ts()
                r["updated_by"] = actor
                r["reason"] = reason
                found = True
                break
        if not found:
            records.append({
                "member": member,
                "permission_level": permission_level,
                "granted_at": _ts(),
                "granted_by": actor,
                "updated_at": _ts(),
                "updated_by": actor,
                "reason": reason,
            })
        self._save(self.permissions_path, records)
        self._audit("permission_granted", actor, {"member": member, "level": permission_level, "reason": reason})
        return {"ok": True, "member": member, "permission_level": permission_level}

    def get_permission(self, member: str) -> dict[str, Any]:
        for r in self._load(self.permissions_path):
            if r.get("member") == member:
                return r
        return {"member": member, "permission_level": "guest", "source": "default"}

    def list_permissions(self, actor_level: str = "admin") -> list[dict]:
        self._check_permission(actor_level, "view_permissions")
        return self._load(self.permissions_path)

    # ------------------------------------------------------------------
    # Audit log
    # ------------------------------------------------------------------

    def get_audit_summary(self, actor_level: str = "admin", limit: int = 50) -> list[dict]:
        self._check_permission(actor_level, "view_audit_summary")
        if not self.audit_path.exists():
            return []
        lines = self.audit_path.read_text(encoding="utf-8").strip().splitlines()
        records = []
        for line in lines:
            try:
                records.append(json.loads(line))
            except Exception:
                pass
        return records[-limit:]
