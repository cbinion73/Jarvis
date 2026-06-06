from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .persistence import append_jsonl, atomic_write_json


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SelfImprovementStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.jobs_path = self.root / "jobs.json"
        self.runs_path = self.root / "runs.json"
        self.runs_log_path = self.root / "runs_log.jsonl"
        self.runs_state_log_path = self.root / "runs_state_log.jsonl"
        self.active_runs_path = self.root / "active_runs.json"
        self.active_runs_log_path = self.root / "active_runs_log.jsonl"
        self.active_runs_state_log_path = self.root / "active_runs_state_log.jsonl"
        self.settings_path = self.root / "settings.json"
        self.settings_log_path = self.root / "settings_log.jsonl"
        self.settings_state_log_path = self.root / "settings_state_log.jsonl"
        self.jobs_log_path = self.root / "jobs_log.jsonl"
        self.jobs_state_log_path = self.root / "jobs_state_log.jsonl"

    def _load_json(self, path: Path, *, default: Any) -> Any:
        if not path.exists():
            return default
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return default

    def _save_json(self, path: Path, payload: Any) -> None:
        atomic_write_json(path, payload)

    def _load_jsonl(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        try:
            rows = [
                json.loads(line)
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        except (OSError, json.JSONDecodeError):
            return []
        return [dict(item) for item in rows if isinstance(item, dict)]

    def _append_active_runs_event(self, payload: dict[str, Any]) -> None:
        append_jsonl(self.active_runs_log_path, payload)

    def _append_active_runs_state(self, payload: dict[str, Any]) -> None:
        append_jsonl(self.active_runs_state_log_path, payload)

    def _append_run_event(self, payload: dict[str, Any]) -> None:
        append_jsonl(self.runs_log_path, payload)

    def _append_run_state(self, payload: dict[str, Any]) -> None:
        append_jsonl(self.runs_state_log_path, payload)

    def _append_settings_event(self, payload: dict[str, Any]) -> None:
        append_jsonl(self.settings_log_path, payload)

    def _append_settings_state(self, payload: dict[str, Any]) -> None:
        append_jsonl(self.settings_state_log_path, payload)

    def _append_jobs_event(self, payload: dict[str, Any]) -> None:
        append_jsonl(self.jobs_log_path, payload)

    def _append_jobs_state(self, payload: dict[str, Any]) -> None:
        append_jsonl(self.jobs_state_log_path, payload)

    def _replay_active_runs(self) -> dict[str, dict[str, Any]]:
        records: dict[str, dict[str, Any]] = {}
        for item in self._load_jsonl(self.active_runs_log_path):
            event_type = str(item.get("event_type", "")).strip().lower()
            if event_type == "replaced":
                snapshot = item.get("active_runs")
                if isinstance(snapshot, dict):
                    records = {
                        str(key): dict(value)
                        for key, value in snapshot.items()
                        if isinstance(value, dict) and str(key).strip()
                    }
                continue
            job_id = str(item.get("job_id", "")).strip()
            if not job_id:
                continue
            if event_type == "upserted":
                record = item.get("record")
                if isinstance(record, dict):
                    records[job_id] = dict(record)
            elif event_type == "cleared":
                records.pop(job_id, None)
        return records

    def _replay_runs(self) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for item in self._load_jsonl(self.runs_log_path):
            event_type = str(item.get("event_type", "")).strip().lower()
            if event_type == "replaced":
                snapshot = item.get("runs")
                if isinstance(snapshot, list):
                    records = [dict(value) for value in snapshot if isinstance(value, dict)]
                continue
            if event_type == "recorded":
                record = item.get("record")
                if isinstance(record, dict):
                    records.append(dict(record))
        return records

    def _replay_settings(self) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        for item in self._load_jsonl(self.settings_log_path):
            event_type = str(item.get("event_type", "")).strip().lower()
            if event_type != "replaced":
                continue
            snapshot = item.get("settings")
            if isinstance(snapshot, dict):
                payload = dict(snapshot)
        return payload

    def _replay_settings_state(self) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        for item in self._load_jsonl(self.settings_state_log_path):
            snapshot = item.get("settings")
            if isinstance(snapshot, dict):
                payload = dict(snapshot)
        return payload

    def _replay_jobs(self) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for item in self._load_jsonl(self.jobs_log_path):
            event_type = str(item.get("event_type", "")).strip().lower()
            if event_type == "replaced":
                snapshot = item.get("jobs")
                if isinstance(snapshot, list):
                    records = [dict(value) for value in snapshot if isinstance(value, dict)]
                continue
            if event_type == "upserted":
                record = item.get("record")
                if not isinstance(record, dict):
                    continue
                job_id = str(record.get("job_id", "")).strip()
                if not job_id:
                    continue
                replaced = False
                for index, existing in enumerate(records):
                    if str(existing.get("job_id", "")).strip() == job_id:
                        records[index] = dict(record)
                        replaced = True
                        break
                if not replaced:
                    records.append(dict(record))
        return records

    def _replay_jobs_state(self) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for item in self._load_jsonl(self.jobs_state_log_path):
            snapshot = item.get("jobs")
            if isinstance(snapshot, list):
                records = [dict(value) for value in snapshot if isinstance(value, dict)]
        return records

    def settings(self) -> dict[str, Any]:
        default = {
            "enabled": True,
            "allow_safe_autonomy": True,
            "allow_configured_model_sync": True,
            "allow_heavy_model_downloads": False,
            "allow_tool_installs": False,
            "allow_code_changes": False,
            "max_auto_actions_per_run": 1,
        }
        if self.settings_state_log_path.exists():
            payload = self._replay_settings_state()
            if payload:
                self._save_json(self.settings_path, payload)
                return payload
        elif self.settings_log_path.exists():
            payload = self._replay_settings()
            if payload:
                self._save_json(self.settings_path, payload)
                return payload
        payload = self._load_json(
            self.settings_path,
            default=default,
        )
        return payload if isinstance(payload, dict) else {}

    def save_settings(self, payload: dict[str, Any]) -> dict[str, Any]:
        event = {
            "event_type": "replaced",
            "recorded_at": _now_iso(),
            "settings": dict(payload),
        }
        self._append_settings_event(event)
        self._append_settings_state(event)
        self._save_json(self.settings_path, payload)
        return payload

    def jobs(self) -> list[dict[str, Any]]:
        if self.jobs_state_log_path.exists():
            payload = self._replay_jobs_state()
            self._save_json(self.jobs_path, payload)
            return payload
        if self.jobs_log_path.exists():
            payload = self._replay_jobs()
            self._save_json(self.jobs_path, payload)
            return payload
        payload = self._load_json(self.jobs_path, default=[])
        return payload if isinstance(payload, list) else []

    def save_jobs(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized = [dict(item) for item in records if isinstance(item, dict)]
        event = {
            "event_type": "replaced",
            "recorded_at": _now_iso(),
            "jobs": normalized,
        }
        self._append_jobs_event(event)
        self._append_jobs_state(event)
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
        self._append_jobs_event(
            {
                "event_type": "upserted",
                "recorded_at": _now_iso(),
                "record": dict(record),
            }
        )
        self.save_jobs(records)
        return record

    def runs(self) -> list[dict[str, Any]]:
        if self.runs_state_log_path.exists():
            payload = self._replay_runs_state()
            self._save_json(self.runs_path, payload)
            return payload
        if self.runs_log_path.exists():
            payload = self._replay_runs()
            self._save_json(self.runs_path, payload)
            return payload
        payload = self._load_json(self.runs_path, default=[])
        return [dict(item) for item in payload if isinstance(item, dict)] if isinstance(payload, list) else []

    def _replay_runs_state(self) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for item in self._load_jsonl(self.runs_state_log_path):
            snapshot = item.get("runs")
            if isinstance(snapshot, list):
                records = [dict(value) for value in snapshot if isinstance(value, dict)]
        return records

    def save_runs(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized = [dict(item) for item in records if isinstance(item, dict)]
        event = {
            "event_type": "replaced",
            "recorded_at": _now_iso(),
            "runs": normalized,
        }
        self._append_run_event(event)
        self._append_run_state(event)
        self._save_json(self.runs_path, normalized)
        return normalized

    def recent_runs(self, limit: int = 12) -> list[dict[str, Any]]:
        records = self.runs()
        return list(reversed(records[-max(1, int(limit)) :]))

    def record_run(self, record: dict[str, Any]) -> dict[str, Any]:
        records = self.runs()
        normalized_record = dict(record)
        records.append(normalized_record)
        self._append_run_event(
            {
                "event_type": "recorded",
                "recorded_at": _now_iso(),
                "record": normalized_record,
            }
        )
        self._append_run_state(
            {
                "event_type": "replaced",
                "recorded_at": _now_iso(),
                "runs": records,
            }
        )
        self._save_json(self.runs_path, records)
        return normalized_record

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        needle = str(run_id).strip()
        if not needle:
            return None
        for item in self.runs():
            if str(item.get("run_id", "")).strip() == needle:
                return dict(item)
        return None

    def active_runs(self) -> dict[str, dict[str, Any]]:
        if self.active_runs_state_log_path.exists():
            payload = self._replay_active_runs_state()
            self._save_json(self.active_runs_path, payload)
            return payload
        if self.active_runs_log_path.exists():
            payload = self._replay_active_runs()
            self._save_json(self.active_runs_path, payload)
            return payload
        payload = self._load_json(self.active_runs_path, default={})
        if not isinstance(payload, dict):
            return {}
        return {
            str(key): dict(value)
            for key, value in payload.items()
            if isinstance(value, dict) and str(key).strip()
        }

    def _replay_active_runs_state(self) -> dict[str, dict[str, Any]]:
        payload: dict[str, dict[str, Any]] = {}
        for item in self._load_jsonl(self.active_runs_state_log_path):
            snapshot = item.get("active_runs")
            if isinstance(snapshot, dict):
                payload = {
                    str(key): dict(value)
                    for key, value in snapshot.items()
                    if isinstance(value, dict) and str(key).strip()
                }
        return payload

    def save_active_runs(self, payload: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
        normalized = {
            str(key): dict(value)
            for key, value in payload.items()
            if isinstance(value, dict) and str(key).strip()
        }
        event = {
            "event_type": "replaced",
            "recorded_at": _now_iso(),
            "active_runs": normalized,
        }
        self._append_active_runs_event(event)
        self._append_active_runs_state(event)
        self._save_json(self.active_runs_path, normalized)
        return normalized

    def get_active_run(self, job_id: str) -> dict[str, Any] | None:
        return dict(self.active_runs().get(str(job_id).strip()) or {}) or None

    def upsert_active_run(self, job_id: str, record: dict[str, Any]) -> dict[str, Any]:
        needle = str(job_id).strip()
        if not needle:
            raise ValueError("job_id is required")
        payload = self.active_runs()
        normalized_record = dict(record)
        payload[needle] = normalized_record
        self._append_active_runs_event(
            {
                "event_type": "upserted",
                "recorded_at": _now_iso(),
                "job_id": needle,
                "record": normalized_record,
            }
        )
        self._append_active_runs_state(
            {
                "event_type": "replaced",
                "recorded_at": _now_iso(),
                "active_runs": payload,
            }
        )
        self._save_json(self.active_runs_path, payload)
        return normalized_record

    def clear_active_run(self, job_id: str) -> None:
        needle = str(job_id).strip()
        if not needle:
            return
        payload = self.active_runs()
        if needle in payload:
            payload.pop(needle, None)
            self._append_active_runs_event(
                {
                    "event_type": "cleared",
                    "recorded_at": _now_iso(),
                    "job_id": needle,
                }
            )
            self._append_active_runs_state(
                {
                    "event_type": "replaced",
                    "recorded_at": _now_iso(),
                    "active_runs": payload,
                }
            )
            self._save_json(self.active_runs_path, payload)
