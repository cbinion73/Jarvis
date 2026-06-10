"""E13: Workshop/fabrication safety — Bambu, resin printer, Cricut, general workshop.

Honest unavailable: no device is wired without credentials/IP config.
Safety pre-checks: every job must pass a checklist before staging.
Job staging API: jobs are staged (not auto-submitted) for operator review.

Hard constraints:
- No hazardous automation without manual override confirmation
- No auto-start for resin/high-temp operations
- Every job requires safety_acknowledged=True from operator
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .persistence import append_jsonl, atomic_write_json

_WORKSHOP_ROOT = Path("data/workshop")
_JOBS_PATH = _WORKSHOP_ROOT / "staged_jobs.json"
_JOBS_LOG = _WORKSHOP_ROOT / "staged_jobs_log.jsonl"
_SAFETY_AUDIT = _WORKSHOP_ROOT / "safety_audit.jsonl"


def _ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# ---------------------------------------------------------------------------
# Device definitions
# ---------------------------------------------------------------------------
WORKSHOP_DEVICES: dict[str, dict[str, Any]] = {
    "bambu_x1c": {
        "display_name": "Bambu Lab X1C",
        "device_type": "3d_printer",
        "hazard_level": "moderate",
        "env_var": "BAMBU_X1C_IP",
        "access_code_var": "BAMBU_X1C_ACCESS_CODE",
        "requires_manual_override": False,
        "safety_checks": [
            "filament_loaded",
            "bed_clear",
            "enclosure_closed",
            "material_compatible",
        ],
    },
    "resin_printer": {
        "display_name": "Resin Printer",
        "device_type": "resin_printer",
        "hazard_level": "high",
        "env_var": "RESIN_PRINTER_IP",
        "access_code_var": "RESIN_PRINTER_TOKEN",
        "requires_manual_override": True,
        "safety_checks": [
            "ventilation_active",
            "ppe_available",
            "vat_filled",
            "fep_intact",
            "uv_exposure_correct",
        ],
    },
    "cricut": {
        "display_name": "Cricut Maker",
        "device_type": "cutting_machine",
        "hazard_level": "low",
        "env_var": "CRICUT_API_TOKEN",
        "access_code_var": None,
        "requires_manual_override": False,
        "safety_checks": [
            "material_loaded",
            "blade_correct",
            "mat_aligned",
        ],
    },
}

JOB_STATES = frozenset({"staged", "safety_approved", "submitted", "completed", "failed", "cancelled"})


@dataclass(slots=True)
class StagedJob:
    job_id: str
    device_id: str
    actor: str
    job_type: str                # print/cut/mill/etc.
    description: str
    material: str
    estimated_duration_min: int
    safety_checks_passed: list[str]
    safety_checks_failed: list[str]
    safety_acknowledged: bool    # must be True before submission
    state: str                   # staged/safety_approved/submitted/completed/failed/cancelled
    created_at: str
    safety_approved_at: str = ""
    safety_approved_by: str = ""
    submitted_at: str = ""
    completed_at: str = ""
    failure_reason: str = ""
    notes: str = ""
    source: str = "live"


class WorkshopSafetyGate:
    """Gates workshop jobs through safety pre-checks before staging."""

    def __init__(self, root: Path | None = None, env_vars: dict[str, str] | None = None) -> None:
        self.root = root or _WORKSHOP_ROOT
        self.root.mkdir(parents=True, exist_ok=True)
        self.env_vars = env_vars or {}
        self.jobs_path = self.root / "staged_jobs.json"
        self.jobs_log = self.root / "staged_jobs_log.jsonl"
        self.safety_audit = self.root / "safety_audit.jsonl"

    def _load(self) -> list[dict]:
        if not self.jobs_path.exists():
            return []
        try:
            data = json.loads(self.jobs_path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _save(self, records: list[dict]) -> None:
        self.jobs_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self.jobs_path, records)

    def _audit(self, event: str, job_id: str, actor: str, extra: dict | None = None) -> None:
        record: dict[str, Any] = {
            "ts": _ts(), "event": event, "job_id": job_id, "actor": actor,
        }
        if extra:
            record.update(extra)
        try:
            append_jsonl(self.safety_audit, record)
        except Exception:
            pass

    def device_status(self, device_id: str) -> dict[str, Any]:
        """Return honest device availability and config state."""
        device = WORKSHOP_DEVICES.get(device_id)
        if not device:
            return {
                "device_id": device_id,
                "available": False,
                "source": "unavailable",
                "reason": f"Device '{device_id}' is not in the workshop device registry.",
            }
        env_var = device.get("env_var")
        if env_var and not self.env_vars.get(env_var):
            return {
                "device_id": device_id,
                "display_name": device["display_name"],
                "available": False,
                "source": "unavailable",
                "reason": f"Environment variable {env_var!r} is not set.",
                "action_required": f"Set {env_var} in .env to connect this device.",
                "hazard_level": device["hazard_level"],
                "requires_manual_override": device["requires_manual_override"],
            }
        return {
            "device_id": device_id,
            "display_name": device["display_name"],
            "available": True,
            "source": "config",
            "device_type": device["device_type"],
            "hazard_level": device["hazard_level"],
            "requires_manual_override": device["requires_manual_override"],
            "required_safety_checks": device["safety_checks"],
        }

    def run_safety_checks(self, device_id: str, checks_passed: list[str]) -> dict[str, Any]:
        """Validate that all required safety checks have been passed.

        checks_passed: list of check names the operator attests are satisfied.
        Returns: {all_passed, passed, failed, requires_manual_override}
        """
        device = WORKSHOP_DEVICES.get(device_id)
        if not device:
            return {"all_passed": False, "error": f"Unknown device: {device_id}"}
        required = device.get("safety_checks", [])
        passed = [c for c in required if c in checks_passed]
        failed = [c for c in required if c not in checks_passed]
        return {
            "all_passed": len(failed) == 0,
            "passed": passed,
            "failed": failed,
            "requires_manual_override": device.get("requires_manual_override", False),
            "hazard_level": device["hazard_level"],
        }

    def stage_job(
        self,
        *,
        device_id: str,
        actor: str,
        job_type: str,
        description: str,
        material: str = "",
        estimated_duration_min: int = 0,
        checks_passed: list[str] | None = None,
        notes: str = "",
    ) -> dict[str, Any]:
        """Stage a job after running safety pre-checks.

        Returns error if device unavailable or safety checks fail.
        All staged jobs require safety_acknowledged=True before submission.
        """
        # Device availability check
        status = self.device_status(device_id)
        if not status.get("available"):
            return {
                "ok": False,
                "staged": False,
                "reason": status.get("reason", "Device unavailable"),
                "source": status.get("source", "unavailable"),
                "action_required": status.get("action_required", ""),
            }

        # Safety checks
        safety = self.run_safety_checks(device_id, checks_passed or [])
        if not safety["all_passed"]:
            self._audit("safety_check_failed", "n/a", actor, {
                "device_id": device_id,
                "failed_checks": safety["failed"],
            })
            return {
                "ok": False,
                "staged": False,
                "reason": f"Safety checks failed: {safety['failed']}",
                "failed_checks": safety["failed"],
                "passed_checks": safety["passed"],
                "source": "blocked",
            }

        # Stage the job
        job = StagedJob(
            job_id=str(uuid.uuid4()),
            device_id=device_id,
            actor=actor,
            job_type=job_type,
            description=description,
            material=material,
            estimated_duration_min=estimated_duration_min,
            safety_checks_passed=safety["passed"],
            safety_checks_failed=safety["failed"],
            safety_acknowledged=False,
            state="staged",
            created_at=_ts(),
            notes=notes,
        )
        records = self._load()
        records.append(asdict(job))
        self._save(records)
        try:
            append_jsonl(self.jobs_log, asdict(job))
        except Exception:
            pass
        self._audit("job_staged", job.job_id, actor, {"device_id": device_id})

        return {
            "ok": True,
            "staged": True,
            "job_id": job.job_id,
            "state": "staged",
            "requires_manual_override": safety.get("requires_manual_override", False),
            "next_step": (
                "Manual override acknowledgement required before submission."
                if safety.get("requires_manual_override")
                else "Operator safety acknowledgement required before submission."
            ),
            "source": "live",
        }

    def acknowledge_safety(self, job_id: str, actor: str) -> dict | None:
        """Operator acknowledges safety — allows job submission."""
        records = self._load()
        updated = None
        for r in records:
            if r.get("job_id") == job_id:
                if r.get("state") != "staged":
                    raise ValueError(f"Job {job_id} is not in staged state (state={r.get('state')})")
                r["safety_acknowledged"] = True
                r["state"] = "safety_approved"
                r["safety_approved_at"] = _ts()
                r["safety_approved_by"] = actor
                updated = r
                break
        if updated:
            self._save(records)
            self._audit("safety_acknowledged", job_id, actor)
        return updated

    def list_staged_jobs(self, device_id: str | None = None) -> list[dict]:
        records = self._load()
        if device_id:
            records = [r for r in records if r.get("device_id") == device_id]
        return records
