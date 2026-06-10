"""F7: Personnel/device continuity — role/member/device change management.

Handles:
- New member onboarding (new family member, roommate, caregiver)
- New device registration (phone, tablet, computer)
- Changed role (child → adult, guest → member)
- Departed device (device lost/replaced/decommissioned)
- Permission update (add/remove/change capabilities)
- Memory migration (safe transfer of memory from old device/role to new)

Design goals:
- No restricted memory exposed during role changes
- Context preserved across device replacements
- Clean audit trail for all continuity events
- Honest unavailable when migration cannot be verified
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any

from .persistence import append_jsonl, atomic_write_json

_CONTINUITY_ROOT = Path("data/continuity")
_EVENTS_PATH = _CONTINUITY_ROOT / "continuity_events.json"
_EVENTS_LOG = _CONTINUITY_ROOT / "continuity_events_log.jsonl"
_AUDIT_PATH = _CONTINUITY_ROOT / "continuity_audit.jsonl"

CONTINUITY_EVENT_TYPES = frozenset({
    "member_joined",
    "member_departed",
    "device_added",
    "device_departed",
    "role_changed",
    "permission_updated",
    "memory_migrated",
})

CONTINUITY_STATUSES = frozenset({"pending", "in_progress", "complete", "failed", "blocked"})


def _ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


@dataclass(slots=True)
class ContinuityEvent:
    """A continuity event — any change to household membership, devices, or roles."""
    event_id: str
    event_type: str                  # member_joined / device_departed / role_changed / etc.
    actor: str                       # who initiated this change
    subject: str                     # who/what this change is about
    status: str                      # pending/in_progress/complete/failed/blocked
    created_at: str
    description: str
    old_state: dict                  # what was true before
    new_state: dict                  # what is true after
    memory_impact: str               # what memory is affected ("none", description of migration)
    restricted_data_cleared: bool    # whether restricted data was properly isolated
    verified_at: str = ""
    verified_by: str = ""
    failure_reason: str = ""
    steps_completed: list[str] = field(default_factory=list)
    steps_remaining: list[str] = field(default_factory=list)
    notes: str = ""
    source: str = "continuity"


# ---------------------------------------------------------------------------
# Continuity workflows
# ---------------------------------------------------------------------------

def _member_onboarding_steps(member_name: str) -> list[str]:
    return [
        f"Create household profile for '{member_name}'",
        f"Assign initial permission level",
        f"Configure communication preferences",
        f"Introduce to JARVIS capabilities",
        f"Set formation preferences (faith/health/family)",
        f"Verify memory scope restrictions are correct",
        f"Confirm profile visible to appropriate household members",
    ]


def _device_onboarding_steps(device_name: str, owner: str) -> list[str]:
    return [
        f"Register device '{device_name}' in device registry",
        f"Assign device to owner '{owner}'",
        f"Configure device permission level",
        f"Test JARVIS connectivity from device",
        f"Verify restricted data not exposed on new device",
        f"Confirm notification routing to new device",
    ]


def _role_change_steps(subject: str, old_role: str, new_role: str) -> list[str]:
    steps = [
        f"Review current memory entries for '{subject}' in role '{old_role}'",
        f"Identify entries that need re-permissioning for role '{new_role}'",
        f"Update household profile with new role",
        f"Update permission level to match new role",
    ]
    if old_role == "child" and new_role == "adult":
        steps.extend([
            "Verify child-restricted content remains appropriately gated",
            "Grant adult-level access to appropriate memory domains",
            "Update formation guidance to adult profile",
        ])
    steps.append("Audit memory access with new role to confirm no leakage")
    return steps


def _device_departure_steps(device_name: str) -> list[str]:
    return [
        f"Mark device '{device_name}' as departed in registry",
        f"Revoke access tokens for departed device",
        f"Confirm no active sessions on departed device",
        f"Remove device from notification routing",
        f"Verify sensitive data not accessible from departed device",
        f"Archive device record",
    ]


def _memory_migration_steps(from_context: str, to_context: str) -> list[str]:
    return [
        f"Inventory memory entries associated with '{from_context}'",
        f"Classify each entry as: migrate / archive / delete / restricted",
        f"Migrate approved entries to '{to_context}' context",
        f"Verify restricted entries remain inaccessible in new context",
        f"Confirm provenance is preserved on migrated entries",
        f"Create migration audit record",
    ]


class ContinuityStore:
    """Manages household continuity events."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or _CONTINUITY_ROOT
        self.root.mkdir(parents=True, exist_ok=True)
        self.events_path = self.root / "continuity_events.json"
        self.log_path = self.root / "continuity_events_log.jsonl"
        self.audit_path = self.root / "continuity_audit.jsonl"

    def _load(self) -> list[dict]:
        if not self.events_path.exists():
            return []
        try:
            data = json.loads(self.events_path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _save(self, records: list[dict]) -> None:
        self.events_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self.events_path, records)

    def _audit(self, event: str, actor: str, extra: dict | None = None) -> None:
        record: dict[str, Any] = {"ts": _ts(), "event": event, "actor": actor}
        if extra:
            record.update(extra)
        try:
            append_jsonl(self.audit_path, record)
        except Exception:
            pass

    def _create_event(
        self,
        event_type: str,
        actor: str,
        subject: str,
        description: str,
        old_state: dict,
        new_state: dict,
        memory_impact: str,
        steps_remaining: list[str],
    ) -> ContinuityEvent:
        event = ContinuityEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            actor=actor,
            subject=subject,
            status="pending",
            created_at=_ts(),
            description=description,
            old_state=old_state,
            new_state=new_state,
            memory_impact=memory_impact,
            restricted_data_cleared=False,
            steps_remaining=steps_remaining,
        )
        records = self._load()
        records.append(asdict(event))
        self._save(records)
        try:
            append_jsonl(self.log_path, asdict(event))
        except Exception:
            pass
        self._audit(f"continuity_event_{event_type}", actor, {"event_id": event.event_id, "subject": subject})
        return event

    # ------------------------------------------------------------------
    # Member events
    # ------------------------------------------------------------------

    def member_joined(
        self,
        *,
        member_name: str,
        role: str,
        actor: str,
        initial_permission: str = "guest",
        notes: str = "",
    ) -> ContinuityEvent:
        steps = _member_onboarding_steps(member_name)
        return self._create_event(
            event_type="member_joined",
            actor=actor,
            subject=member_name,
            description=f"New household member '{member_name}' joined with role '{role}'",
            old_state={"member": None},
            new_state={"member": member_name, "role": role, "permission": initial_permission},
            memory_impact="New member profile created. No existing memory affected.",
            steps_remaining=steps,
        )

    def member_departed(
        self,
        *,
        member_name: str,
        actor: str,
        reason: str = "",
    ) -> ContinuityEvent:
        steps = [
            f"Archive memory entries for '{member_name}'",
            f"Move restricted entries to archive-only access",
            f"Revoke all active sessions",
            f"Remove from household notification routing",
            f"Document departure reason in continuity log",
        ]
        return self._create_event(
            event_type="member_departed",
            actor=actor,
            subject=member_name,
            description=f"Household member '{member_name}' departed",
            old_state={"member": member_name},
            new_state={"member": None, "archived": True},
            memory_impact=f"Memory entries for '{member_name}' archived. Restricted data protected.",
            steps_remaining=steps,
        )

    # ------------------------------------------------------------------
    # Device events
    # ------------------------------------------------------------------

    def device_added(
        self,
        *,
        device_name: str,
        device_type: str,
        owner: str,
        actor: str,
        permission_level: str = "adult",
    ) -> ContinuityEvent:
        steps = _device_onboarding_steps(device_name, owner)
        return self._create_event(
            event_type="device_added",
            actor=actor,
            subject=device_name,
            description=f"New {device_type} '{device_name}' added for '{owner}'",
            old_state={"device": None},
            new_state={"device": device_name, "type": device_type, "owner": owner, "permission": permission_level},
            memory_impact="Device registered. Memory access governed by owner's permission level.",
            steps_remaining=steps,
        )

    def device_departed(
        self,
        *,
        device_name: str,
        owner: str,
        actor: str,
        reason: str = "decommissioned",
    ) -> ContinuityEvent:
        steps = _device_departure_steps(device_name)
        return self._create_event(
            event_type="device_departed",
            actor=actor,
            subject=device_name,
            description=f"Device '{device_name}' departed (owner: {owner}, reason: {reason})",
            old_state={"device": device_name, "owner": owner, "active": True},
            new_state={"device": device_name, "active": False, "reason": reason},
            memory_impact="Access tokens revoked. Restricted data no longer accessible from this device.",
            steps_remaining=steps,
        )

    # ------------------------------------------------------------------
    # Role change
    # ------------------------------------------------------------------

    def role_changed(
        self,
        *,
        subject: str,
        old_role: str,
        new_role: str,
        actor: str,
        reason: str = "",
    ) -> ContinuityEvent:
        steps = _role_change_steps(subject, old_role, new_role)
        return self._create_event(
            event_type="role_changed",
            actor=actor,
            subject=subject,
            description=f"Role changed for '{subject}': {old_role} → {new_role}",
            old_state={"subject": subject, "role": old_role},
            new_state={"subject": subject, "role": new_role, "reason": reason},
            memory_impact=f"Permission level updated from '{old_role}' to '{new_role}'. Memory scope reviewed.",
            steps_remaining=steps,
        )

    # ------------------------------------------------------------------
    # Memory migration
    # ------------------------------------------------------------------

    def memory_migrated(
        self,
        *,
        from_context: str,
        to_context: str,
        actor: str,
        reason: str = "",
    ) -> ContinuityEvent:
        steps = _memory_migration_steps(from_context, to_context)
        return self._create_event(
            event_type="memory_migrated",
            actor=actor,
            subject=f"{from_context} → {to_context}",
            description=f"Memory migration: '{from_context}' → '{to_context}'. Reason: {reason}",
            old_state={"context": from_context},
            new_state={"context": to_context, "reason": reason},
            memory_impact="Entries classified and migrated. Restricted entries remain inaccessible in new context.",
            steps_remaining=steps,
        )

    # ------------------------------------------------------------------
    # Event lifecycle
    # ------------------------------------------------------------------

    def advance_step(self, event_id: str, actor: str, step_completed: str) -> dict | None:
        records = self._load()
        updated = None
        for r in records:
            if r.get("event_id") == event_id:
                remaining = list(r.get("steps_remaining") or [])
                completed = list(r.get("steps_completed") or [])
                if step_completed in remaining:
                    remaining.remove(step_completed)
                    completed.append(step_completed)
                r["steps_remaining"] = remaining
                r["steps_completed"] = completed
                if not remaining:
                    r["status"] = "complete"
                    r["verified_at"] = _ts()
                    r["verified_by"] = actor
                    r["restricted_data_cleared"] = True
                else:
                    r["status"] = "in_progress"
                updated = r
                break
        if updated:
            self._save(records)
            self._audit("step_advanced", actor, {"event_id": event_id, "step": step_completed})
        return updated

    def fail_event(self, event_id: str, actor: str, reason: str) -> dict | None:
        records = self._load()
        updated = None
        for r in records:
            if r.get("event_id") == event_id:
                r["status"] = "failed"
                r["failure_reason"] = reason
                updated = r
                break
        if updated:
            self._save(records)
            self._audit("event_failed", actor, {"event_id": event_id, "reason": reason})
        return updated

    def get(self, event_id: str) -> dict | None:
        for r in self._load():
            if r.get("event_id") == event_id:
                return r
        return None

    def list_events(self, event_type: str | None = None, status: str | None = None) -> list[dict]:
        records = self._load()
        if event_type:
            records = [r for r in records if r.get("event_type") == event_type]
        if status:
            records = [r for r in records if r.get("status") == status]
        return records
