"""E10: External systems governance — read/write boundaries, approval policy, sync health.

Maintains a registry of external system connectors (Google, OpenClaw, etc.)
Each connector has:
- capability declaration (read/write/sync)
- approval policy (which operations need human approval)
- sync health state (last sync, error count, status)
- failure state (honest unavailable when auth/config fails)

No actual API calls are made here. This is the governance contract.
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .persistence import append_jsonl, atomic_write_json

_EXTSY_ROOT = Path("data/external_systems")
_REGISTRY_PATH = _EXTSY_ROOT / "registry.json"
_SYNC_LOG = _EXTSY_ROOT / "sync_log.jsonl"
_AUDIT_PATH = _EXTSY_ROOT / "external_systems_audit.jsonl"


def _ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


CONNECTOR_STATUSES = frozenset({"configured", "unconfigured", "auth_failed", "sync_error", "healthy", "disabled"})
OPERATION_TYPES = frozenset({"read", "write", "sync", "delete", "publish", "notify"})

# Operations that always require approval
ALWAYS_REQUIRES_APPROVAL: frozenset[str] = frozenset({"write", "delete", "publish", "notify"})


@dataclass(slots=True)
class ExternalSystemConnector:
    connector_id: str
    name: str                        # e.g. "google_calendar", "openClaw", "notion"
    display_name: str
    capabilities: list[str]          # subset of OPERATION_TYPES
    approval_required_for: list[str] # which ops need approval
    config_env_vars: list[str]       # env vars required to configure
    status: str                      # configured/unconfigured/auth_failed/sync_error/healthy/disabled
    last_sync_at: str = ""
    last_error: str = ""
    error_count: int = 0
    created_at: str = ""
    notes: str = ""
    source: str = "config"           # config / unavailable / live


@dataclass(slots=True)
class SyncHealthRecord:
    record_id: str
    connector_id: str
    synced_at: str
    success: bool
    items_synced: int = 0
    error: str = ""


class ExternalSystemRegistry:
    """Registry of external system connectors with governance audit."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or _EXTSY_ROOT
        self.root.mkdir(parents=True, exist_ok=True)
        self.registry_path = self.root / "registry.json"
        self.sync_log_path = self.root / "sync_log.jsonl"
        self.audit_path = self.root / "external_systems_audit.jsonl"

    def _load(self) -> list[dict]:
        if not self.registry_path.exists():
            return []
        try:
            data = json.loads(self.registry_path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _save(self, records: list[dict]) -> None:
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self.registry_path, records)

    def _audit(self, event: str, connector_id: str, actor: str, extra: dict | None = None) -> None:
        record: dict[str, Any] = {
            "ts": _ts(), "event": event, "connector_id": connector_id, "actor": actor,
        }
        if extra:
            record.update(extra)
        try:
            append_jsonl(self.audit_path, record)
        except Exception:
            pass

    def register(
        self,
        *,
        name: str,
        display_name: str,
        capabilities: list[str],
        config_env_vars: list[str] | None = None,
        approval_required_for: list[str] | None = None,
        notes: str = "",
    ) -> ExternalSystemConnector:
        invalid_caps = [c for c in capabilities if c not in OPERATION_TYPES]
        if invalid_caps:
            raise ValueError(f"Unknown capability types: {invalid_caps}")
        # Always require approval for sensitive ops regardless of what caller passes
        approval = list(set(approval_required_for or []) | (ALWAYS_REQUIRES_APPROVAL & set(capabilities)))
        connector = ExternalSystemConnector(
            connector_id=str(uuid.uuid4()),
            name=name.strip(),
            display_name=display_name.strip(),
            capabilities=capabilities,
            approval_required_for=approval,
            config_env_vars=config_env_vars or [],
            status="unconfigured",
            created_at=_ts(),
            notes=notes,
        )
        records = self._load()
        records.append(asdict(connector))
        self._save(records)
        self._audit("registered", connector.connector_id, "system", {"name": name})
        return connector

    def get(self, connector_id: str) -> dict | None:
        for r in self._load():
            if r.get("connector_id") == connector_id:
                return r
        return None

    def get_by_name(self, name: str) -> dict | None:
        for r in self._load():
            if r.get("name") == name:
                return r
        return None

    def list_all(self) -> list[dict]:
        return self._load()

    def update_status(
        self,
        connector_id: str,
        status: str,
        last_error: str = "",
        increment_error: bool = False,
    ) -> dict | None:
        if status not in CONNECTOR_STATUSES:
            raise ValueError(f"status must be one of {sorted(CONNECTOR_STATUSES)}")
        records = self._load()
        updated = None
        for r in records:
            if r.get("connector_id") == connector_id:
                r["status"] = status
                if last_error:
                    r["last_error"] = last_error
                if increment_error:
                    r["error_count"] = int(r.get("error_count") or 0) + 1
                updated = r
                break
        if updated:
            self._save(records)
        return updated

    def record_sync(
        self,
        connector_id: str,
        success: bool,
        items_synced: int = 0,
        error: str = "",
    ) -> SyncHealthRecord:
        record = SyncHealthRecord(
            record_id=str(uuid.uuid4()),
            connector_id=connector_id,
            synced_at=_ts(),
            success=success,
            items_synced=items_synced,
            error=error,
        )
        try:
            append_jsonl(self.sync_log_path, asdict(record))
        except Exception:
            pass
        # Update connector status
        records = self._load()
        for r in records:
            if r.get("connector_id") == connector_id:
                r["last_sync_at"] = record.synced_at
                if not success:
                    r["last_error"] = error
                    r["error_count"] = int(r.get("error_count") or 0) + 1
                    r["status"] = "sync_error"
                else:
                    r["error_count"] = 0
                    r["last_error"] = ""
                    r["status"] = "healthy"
                break
        self._save(records)
        return record

    def check_operation(
        self,
        connector_id: str,
        operation: str,
        actor: str,
    ) -> dict[str, Any]:
        """Gate an external system operation through the approval policy.

        Returns:
            {allowed, requires_approval, reason, connector_status, source}
        """
        connector = self.get(connector_id)
        if not connector:
            return {
                "allowed": False,
                "requires_approval": False,
                "reason": f"Connector {connector_id!r} not found in registry.",
                "source": "blocked",
            }

        if connector.get("status") in ("unconfigured", "auth_failed", "disabled"):
            return {
                "allowed": False,
                "requires_approval": False,
                "reason": f"Connector '{connector.get('name')}' status is {connector.get('status')!r}.",
                "connector_status": connector.get("status"),
                "source": "unavailable",
                "action_required": f"Set env vars: {', '.join(connector.get('config_env_vars', []))}",
            }

        caps = connector.get("capabilities", [])
        if operation not in caps:
            return {
                "allowed": False,
                "requires_approval": False,
                "reason": f"Connector '{connector.get('name')}' does not support operation '{operation}'. Capabilities: {caps}",
                "source": "blocked",
            }

        needs_approval = operation in (connector.get("approval_required_for") or [])
        self._audit("operation_checked", connector_id, actor, {"operation": operation, "needs_approval": needs_approval})
        return {
            "allowed": not needs_approval,
            "requires_approval": needs_approval,
            "reason": (
                f"Operation '{operation}' requires explicit approval before execution."
                if needs_approval else
                f"Operation '{operation}' is permitted for connector '{connector.get('name')}'."
            ),
            "connector_status": connector.get("status"),
            "source": "live",
        }
