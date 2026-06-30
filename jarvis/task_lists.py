from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any

from .persistence import append_jsonl, atomic_write_json


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class TaskListStore:
    root: Path
    read_only: bool = False
    index_path: Path = field(init=False)
    log_path: Path = field(init=False)

    def __post_init__(self) -> None:
        self.index_path = self.root / "task_lists.json"
        self.log_path = self.root / "task_lists_log.jsonl"

    def load(self) -> dict[str, Any]:
        default = {"task_lists": {}, "history": []}
        if not self.index_path.exists():
            return default
        try:
            payload = json.loads(self.index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return default
        if not isinstance(payload, dict):
            return default
        payload.setdefault("task_lists", {})
        payload.setdefault("history", [])
        return payload

    def save(self, payload: dict[str, Any]) -> None:
        if self.read_only:
            raise RuntimeError("Task-list storage is read-only in this mode.")
        self.root.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self.index_path, payload)
        append_jsonl(
            self.log_path,
            {
                "saved_at": _now_iso(),
                "records": payload,
            },
        )

    def create_task_list(
        self,
        *,
        actor: str,
        room: str,
        title: str,
        topic: str,
        source_request: str,
        summary: str,
        tasks: list[dict[str, Any]],
    ) -> dict[str, Any]:
        now = _now_iso()
        task_list_id = str(uuid.uuid4())
        record = {
            "task_list_id": task_list_id,
            "object_kind": "task_list",
            "actor": actor.strip() or "Chris",
            "room": room.strip() or "office",
            "title": title.strip() or "Task list",
            "topic": topic.strip(),
            "source_request": source_request.strip(),
            "status": "created",
            "created_at": now,
            "updated_at": now,
            "summary": summary.strip(),
            "tasks": list(tasks),
            "truth_mode": "local_task_list_scaffold_only",
            "live_task_system_used": False,
        }
        payload = self.load()
        task_lists = dict(payload.get("task_lists", {}))
        history = list(payload.get("history", []))
        task_lists[task_list_id] = record
        history.append(
            {
                "event": "task-list-created",
                "task_list_id": task_list_id,
                "title": record["title"],
                "topic": record["topic"],
                "actor": record["actor"],
                "created_at": now,
            }
        )
        payload["task_lists"] = task_lists
        payload["history"] = history[-200:]
        self.save(payload)
        return record

    def get_task_list(self, task_list_id: str) -> dict[str, Any] | None:
        payload = self.load()
        record = payload.get("task_lists", {}).get(task_list_id)
        return dict(record) if isinstance(record, dict) else None


_DIRECT_TASK_LIST_PATTERNS = (
    re.compile(r"^break(?: this)? into tasks(?:\s+(?:for|on|about))?\s*(?P<topic>.+?)?\.?$", re.IGNORECASE),
    re.compile(r"^make me a task list(?:\s+(?:for|on|about))?\s+(?P<topic>.+?)\.?$", re.IGNORECASE),
    re.compile(r"^turn(?: this)? into a task breakdown(?:\s+(?:for|on|about))?\s+(?P<topic>.+?)\.?$", re.IGNORECASE),
    re.compile(r"^create a task list(?:\s+(?:for|on|about))?\s+(?P<topic>.+?)\.?$", re.IGNORECASE),
)
_DIRECT_TASK_LIST_STARTERS = (
    "break this into tasks",
    "break into tasks",
    "make me a task list",
    "turn this into a task breakdown",
    "create a task list",
)


def is_direct_task_list_request(request: str) -> bool:
    lowered = " ".join(str(request or "").strip().split()).lower()
    return any(lowered.startswith(prefix) for prefix in _DIRECT_TASK_LIST_STARTERS)


def extract_task_list_topic(request: str) -> str:
    cleaned = " ".join(str(request or "").strip().split())
    for pattern in _DIRECT_TASK_LIST_PATTERNS:
        matched = pattern.match(cleaned)
        if not matched:
            continue
        return str(matched.group("topic") or "").strip().rstrip(".?!")
    return ""


def _title(topic: str) -> str:
    cleaned = str(topic or "").strip().rstrip(".")
    if not cleaned:
        return "Task list"
    return f"Task list for {cleaned}"


def _summary(topic: str) -> str:
    cleaned = str(topic or "").strip()
    return (
        f"This task list is a local scaffold for {cleaned}. "
        "It does not claim sync to a live task system."
    )


def _task_texts(topic: str) -> list[str]:
    lowered = str(topic or "").strip().lower()
    if "garage" in lowered and any(word in lowered for word in ("clean", "cleanout", "cleaned")):
        return [
            "Define the first garage zone to tackle",
            "Pull trash, donations, and obvious removals first",
            "Sort what stays by category or location",
            "Reset the space and do one final keep-or-cut pass",
        ]
    if "retirement workshop" in lowered:
        return [
            "Lock the outcome the workshop needs to produce",
            "Draft the workshop flow and main sections",
            "Gather any numbers, materials, or examples needed",
            "Run the final prep pass before the workshop day",
        ]
    if "scout trailer" in lowered or ("scout" in lowered and "trailer" in lowered):
        return [
            "List the gear or systems that have to be ready first",
            "Handle repairs, supplies, or missing items",
            "Load and label the trailer by use or access order",
            "Do a final readiness check before it needs to move",
        ]
    return [
        f"Define the outcome for {topic}",
        f"Break {topic} into the main work blocks",
        f"Handle the blockers or time-sensitive pieces first",
        f"Set the next concrete action for {topic}",
    ]


def _tasks(topic: str) -> list[dict[str, Any]]:
    return [
        {
            "task_id": f"task-{index + 1}",
            "text": text,
            "completed": False,
        }
        for index, text in enumerate(_task_texts(topic))
    ]


def build_direct_task_list_response(
    store: TaskListStore,
    *,
    actor: str,
    room: str,
    request: str,
) -> dict[str, Any] | None:
    if not is_direct_task_list_request(request):
        return None
    topic = extract_task_list_topic(request)
    if topic.lower() in {"me", "this", "it"}:
        topic = ""
    if not topic:
        return {
            "output_text": "I can do that. What should I break into tasks?",
            "created_task_list": None,
        }
    created = store.create_task_list(
        actor=actor,
        room=room,
        title=_title(topic),
        topic=topic,
        source_request=request,
        summary=_summary(topic),
        tasks=_tasks(topic),
    )
    return {
        "output_text": (
            f"I made a task list for {topic}. "
            "It is a bounded local task breakdown, not a claim of live task-system sync."
        ),
        "created_task_list": created,
    }
