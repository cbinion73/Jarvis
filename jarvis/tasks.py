"""
tasks.py — Persistent task store for JARVIS.

Tasks are the primary action-item store. Stored at ~/.jarvis/tasks.json.
Thread-safe via a module-level Lock.
"""
from __future__ import annotations

import json
import os
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .persistence import append_jsonl, atomic_write_json

_TASKS_PATH = Path(os.path.expanduser("~/.jarvis/tasks.json"))
_TASKS_LOG_PATH = _TASKS_PATH.with_name("tasks_log.jsonl")
_TASKS_STATE_LOG_PATH = _TASKS_PATH.with_name("tasks_state_log.jsonl")
_lock = threading.Lock()

_PRIORITY_ORDER = {"high": 0, "normal": 1, "low": 2}
_VALID_STATUSES = {"pending", "in_progress", "done", "cancelled"}
_VALID_PRIORITIES = {"high", "normal", "low"}
_VALID_DOMAINS = {
    "personal", "family", "work", "health", "faith", "finance", "home", "workshop",
}
_VALID_ACTORS = {"chris", "rebekah", "anna", "caleb", "family"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load() -> list[dict]:
    try:
        if _TASKS_PATH.exists():
            payload = json.loads(_TASKS_PATH.read_text(encoding="utf-8"))
            if isinstance(payload, list) and payload:
                return payload
            return _load_from_state_log()
    except Exception:
        return _load_from_state_log()
    if not _TASKS_PATH.exists():
        return _load_from_state_log()
    return []


def _load_from_log() -> list[dict]:
    try:
        if _TASKS_LOG_PATH.exists():
            latest: list[dict] = []
            for line in _TASKS_LOG_PATH.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                payload = json.loads(line)
                records = payload.get("records")
                if isinstance(records, list):
                    latest = [dict(item) for item in records if isinstance(item, dict)]
            return latest
    except Exception:
        pass
    return []


def _load_from_state_log() -> list[dict]:
    try:
        if _TASKS_STATE_LOG_PATH.exists():
            latest: list[dict] = []
            for line in _TASKS_STATE_LOG_PATH.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                payload = json.loads(line)
                records = payload.get("records")
                if isinstance(records, list):
                    latest = [dict(item) for item in records if isinstance(item, dict)]
            return latest
    except Exception:
        pass
    return []


def _save(tasks: list[dict]) -> None:
    _TASKS_PATH.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(_TASKS_PATH, tasks)
    append_jsonl(
        _TASKS_LOG_PATH,
        {
            "saved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "records": tasks,
        },
    )
    append_jsonl(
        _TASKS_STATE_LOG_PATH,
        {
            "saved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "records": tasks,
        },
    )


def add_task(
    title: str,
    *,
    body: str = "",
    priority: str = "normal",
    due: str | None = None,
    actor: str = "chris",
    domain: str = "personal",
    source: str = "manual",
    tags: list[str] | None = None,
) -> dict:
    """Create and persist a new task. Returns the created task dict."""
    now = _now_iso()
    task: dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "title": title.strip(),
        "body": body.strip(),
        "status": "pending",
        "priority": priority if priority in _VALID_PRIORITIES else "normal",
        "due": due,
        "actor": actor if actor in _VALID_ACTORS else "chris",
        "domain": domain if domain in _VALID_DOMAINS else "personal",
        "source": source,
        "tags": tags or [],
        "created_at": now,
        "updated_at": now,
        "completed_at": None,
    }
    with _lock:
        tasks = _load()
        tasks.append(task)
        _save(tasks)
    return task


def list_tasks(
    *,
    include_done: bool = False,
    actor: str | None = None,
    domain: str | None = None,
    priority: str | None = None,
) -> list[dict]:
    """Return tasks matching the given filters."""
    with _lock:
        tasks = _load()

    if not include_done:
        tasks = [t for t in tasks if t.get("status") not in ("done", "cancelled")]
    if actor:
        tasks = [t for t in tasks if t.get("actor") == actor]
    if domain:
        tasks = [t for t in tasks if t.get("domain") == domain]
    if priority:
        tasks = [t for t in tasks if t.get("priority") == priority]
    return tasks


def get_task(task_id: str) -> dict | None:
    """Return a single task by ID, or None if not found."""
    with _lock:
        tasks = _load()
    for t in tasks:
        if t["id"] == task_id:
            return t
    return None


def update_task(task_id: str, **fields) -> bool:
    """Partially update a task. Returns True if found and updated."""
    # Strip read-only / ID fields from updates
    for key in ("id", "created_at"):
        fields.pop(key, None)

    with _lock:
        tasks = _load()
        for t in tasks:
            if t["id"] == task_id:
                # Validate enums
                if "status" in fields and fields["status"] not in _VALID_STATUSES:
                    fields.pop("status")
                if "priority" in fields and fields["priority"] not in _VALID_PRIORITIES:
                    fields.pop("priority")
                if "actor" in fields and fields["actor"] not in _VALID_ACTORS:
                    fields.pop("actor")
                if "domain" in fields and fields["domain"] not in _VALID_DOMAINS:
                    fields.pop("domain")
                t.update(fields)
                t["updated_at"] = _now_iso()
                _save(tasks)
                return True
    return False


def complete_task(task_id: str) -> bool:
    """Mark a task done. Returns True if found."""
    now = _now_iso()
    with _lock:
        tasks = _load()
        for t in tasks:
            if t["id"] == task_id:
                t["status"] = "done"
                t["completed_at"] = now
                t["updated_at"] = now
                _save(tasks)
                return True
    return False


def delete_task(task_id: str) -> bool:
    """Hard-delete a task. Returns True if found."""
    with _lock:
        tasks = _load()
        new = [t for t in tasks if t["id"] != task_id]
        if len(new) < len(tasks):
            _save(new)
            return True
    return False


def pending_tasks(
    actor: str | None = None,
    domain: str | None = None,
) -> list[dict]:
    """Return pending and in_progress tasks, sorted by due date then priority."""
    with _lock:
        tasks = _load()

    active = [t for t in tasks if t.get("status") in ("pending", "in_progress")]
    if actor:
        active = [t for t in active if t.get("actor") == actor]
    if domain:
        active = [t for t in active if t.get("domain") == domain]

    def sort_key(t: dict):
        due = t.get("due") or "9999-99-99"
        pri = _PRIORITY_ORDER.get(t.get("priority", "normal"), 1)
        return (due, pri)

    return sorted(active, key=sort_key)
