"""E6: Sandbox rollback packet generator and audit layer.

Every sandbox job gets a rollback packet at launch time so the operator
can inspect what would be reversed if the job is cancelled or fails.

Rollback packets are durable (persisted to JSONL) and include:
- Pre-state snapshot of relevant data files
- Reverse instructions (what to restore)
- Audit trail of attempts and outcomes
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .persistence import append_jsonl, atomic_write_json

_ROLLBACK_ROOT = Path("data/sandbox/rollback")
_ROLLBACK_PACKETS_PATH = _ROLLBACK_ROOT / "packets.json"
_ROLLBACK_AUDIT_PATH = _ROLLBACK_ROOT / "rollback_audit.jsonl"


def _ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# ---------------------------------------------------------------------------
# Rollback packet states
# ---------------------------------------------------------------------------
ROLLBACK_PENDING = "pending"
ROLLBACK_APPLIED = "applied"
ROLLBACK_SKIPPED = "skipped"
ROLLBACK_FAILED = "failed"

ROLLBACK_STATES = frozenset({ROLLBACK_PENDING, ROLLBACK_APPLIED, ROLLBACK_SKIPPED, ROLLBACK_FAILED})


@dataclass(slots=True)
class RollbackPacket:
    """A snapshot of pre-execution state for a sandbox job."""
    packet_id: str
    job_id: str
    job_type: str
    actor: str
    state: str                          # pending / applied / skipped / failed
    created_at: str
    pre_state: dict                     # snapshot of relevant state before execution
    reverse_instructions: list[str]     # human-readable steps to reverse the job
    files_touched: list[str]            # file paths that will be modified
    rollback_applied_at: str = ""
    rollback_applied_by: str = ""
    rollback_failure_reason: str = ""
    audit_events: list[dict] = field(default_factory=list)


class SandboxRollbackStore:
    """Manages rollback packets for sandbox jobs."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or _ROLLBACK_ROOT
        self.root.mkdir(parents=True, exist_ok=True)
        self.packets_path = self.root / "packets.json"
        self.audit_path = self.root / "rollback_audit.jsonl"

    def _load(self) -> list[dict]:
        if not self.packets_path.exists():
            return []
        try:
            data = json.loads(self.packets_path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _save(self, records: list[dict]) -> None:
        self.packets_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self.packets_path, records)

    def _audit(self, event: str, packet_id: str, actor: str, extra: dict | None = None) -> None:
        record: dict[str, Any] = {
            "ts": _ts(),
            "event": event,
            "packet_id": packet_id,
            "actor": actor,
        }
        if extra:
            record.update(extra)
        try:
            self.audit_path.parent.mkdir(parents=True, exist_ok=True)
            append_jsonl(self.audit_path, record)
        except Exception:
            pass

    def create_packet(
        self,
        *,
        job_id: str,
        job_type: str,
        actor: str,
        pre_state: dict | None = None,
        reverse_instructions: list[str] | None = None,
        files_touched: list[str] | None = None,
    ) -> RollbackPacket:
        """Create and persist a rollback packet for a sandbox job."""
        packet = RollbackPacket(
            packet_id=str(uuid.uuid4()),
            job_id=job_id,
            job_type=job_type,
            actor=actor,
            state=ROLLBACK_PENDING,
            created_at=_ts(),
            pre_state=pre_state or {},
            reverse_instructions=reverse_instructions or [],
            files_touched=files_touched or [],
        )
        records = self._load()
        records.append(asdict(packet))
        self._save(records)
        self._audit("created", packet.packet_id, actor, {"job_id": job_id, "job_type": job_type})
        return packet

    def get_by_job(self, job_id: str) -> list[dict]:
        return [r for r in self._load() if r.get("job_id") == job_id]

    def get_by_packet_id(self, packet_id: str) -> dict | None:
        for r in self._load():
            if r.get("packet_id") == packet_id:
                return r
        return None

    def apply_rollback(self, packet_id: str, actor: str) -> dict | None:
        """Mark a rollback as applied — actual file restoration is handled by the caller."""
        records = self._load()
        updated = None
        for r in records:
            if r.get("packet_id") == packet_id:
                if r.get("state") != ROLLBACK_PENDING:
                    raise ValueError(f"Rollback {packet_id} is not in pending state (state={r.get('state')})")
                r["state"] = ROLLBACK_APPLIED
                r["rollback_applied_at"] = _ts()
                r["rollback_applied_by"] = actor
                updated = r
                break
        if updated is None:
            return None
        self._save(records)
        self._audit("applied", packet_id, actor)
        return updated

    def skip_rollback(self, packet_id: str, actor: str, reason: str = "") -> dict | None:
        """Mark a rollback as skipped (e.g. job succeeded, no rollback needed)."""
        records = self._load()
        updated = None
        for r in records:
            if r.get("packet_id") == packet_id:
                r["state"] = ROLLBACK_SKIPPED
                updated = r
                break
        if updated is None:
            return None
        self._save(records)
        self._audit("skipped", packet_id, actor, {"reason": reason})
        return updated

    def fail_rollback(self, packet_id: str, actor: str, reason: str) -> dict | None:
        """Mark a rollback as failed."""
        records = self._load()
        updated = None
        for r in records:
            if r.get("packet_id") == packet_id:
                r["state"] = ROLLBACK_FAILED
                r["rollback_failure_reason"] = reason
                updated = r
                break
        if updated is None:
            return None
        self._save(records)
        self._audit("failed", packet_id, actor, {"reason": reason})
        return updated

    def list_pending(self) -> list[dict]:
        return [r for r in self._load() if r.get("state") == ROLLBACK_PENDING]


def capture_file_state(paths: list[str | Path]) -> dict[str, str]:
    """Capture the current text content of a list of files for rollback snapshot.

    Returns dict of {path_str: content}. Missing files are noted as 'NOT_FOUND'.
    Large files (>50KB) get a SHA256 digest instead of full content.
    """
    import hashlib
    snapshot: dict[str, str] = {}
    for p in paths:
        path = Path(p)
        try:
            if not path.exists():
                snapshot[str(p)] = "NOT_FOUND"
            elif path.stat().st_size > 50 * 1024:
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                snapshot[str(p)] = f"LARGE_FILE_SHA256:{digest}"
            else:
                snapshot[str(p)] = path.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            snapshot[str(p)] = f"ERROR:{exc}"
    return snapshot
