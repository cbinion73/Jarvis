from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SelfImprovementStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.jobs_path = self.root / "jobs.json"
        self.runs_path = self.root / "runs.json"
        self.settings_path = self.root / "settings.json"

    def _load_json(self, path: Path, *, default: Any) -> Any:
        if not path.exists():
            return default
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return default

    def _save_json(self, path: Path, payload: Any) -> None:
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def settings(self) -> dict[str, Any]:
        payload = self._load_json(
            self.settings_path,
            default={
                "enabled": True,
                "allow_safe_autonomy": True,
                "allow_configured_model_sync": True,
                "allow_heavy_model_downloads": False,
                "allow_tool_installs": False,
                "allow_code_changes": False,
                "max_auto_actions_per_run": 1,
            },
        )
        return payload if isinstance(payload, dict) else {}

    def save_settings(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._save_json(self.settings_path, payload)
        return payload

    def jobs(self) -> list[dict[str, Any]]:
        payload = self._load_json(self.jobs_path, default=[])
        return payload if isinstance(payload, list) else []

    def save_jobs(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        self._save_json(self.jobs_path, records)
        return records

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        needle = str(job_id).strip()
        if not needle:
            return None
        for item in self.jobs():
            if str(item.get("job_id", "")).strip() == needle:
                return dict(item)
        return None

    def find_job_by_key(self, job_key: str) -> dict[str, Any] | None:
        needle = str(job_key).strip()
        if not needle:
            return None
        for item in self.jobs():
            if str(item.get("job_key", "")).strip() == needle:
                return dict(item)
        return None

    def upsert_job(self, record: dict[str, Any]) -> dict[str, Any]:
        job_id = str(record.get("job_id", "")).strip()
        if not job_id:
            raise ValueError("job_id is required")
        records = self.jobs()
        replaced = False
        for index, item in enumerate(records):
            if str(item.get("job_id", "")).strip() == job_id:
                records[index] = record
                replaced = True
                break
        if not replaced:
            records.append(record)
        self.save_jobs(records)
        return record

    def runs(self) -> list[dict[str, Any]]:
        payload = self._load_json(self.runs_path, default=[])
        return payload if isinstance(payload, list) else []

    def recent_runs(self, limit: int = 12) -> list[dict[str, Any]]:
        records = self.runs()
        return list(reversed(records[-max(1, int(limit)) :]))

    def record_run(self, record: dict[str, Any]) -> dict[str, Any]:
        records = self.runs()
        records.append(record)
        self._save_json(self.runs_path, records)
        return record

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        needle = str(run_id).strip()
        if not needle:
            return None
        for item in self.runs():
            if str(item.get("run_id", "")).strip() == needle:
                return dict(item)
        return None
