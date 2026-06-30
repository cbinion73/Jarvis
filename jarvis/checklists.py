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
class ChecklistStore:
    root: Path
    read_only: bool = False
    index_path: Path = field(init=False)
    log_path: Path = field(init=False)

    def __post_init__(self) -> None:
        self.index_path = self.root / "checklists.json"
        self.log_path = self.root / "checklists_log.jsonl"

    def load(self) -> dict[str, Any]:
        default = {"checklists": {}, "history": []}
        if not self.index_path.exists():
            return default
        try:
            payload = json.loads(self.index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return default
        if not isinstance(payload, dict):
            return default
        payload.setdefault("checklists", {})
        payload.setdefault("history", [])
        return payload

    def save(self, payload: dict[str, Any]) -> None:
        if self.read_only:
            raise RuntimeError("Checklist storage is read-only in this mode.")
        self.root.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self.index_path, payload)
        append_jsonl(
            self.log_path,
            {
                "saved_at": _now_iso(),
                "records": payload,
            },
        )

    def create_checklist(
        self,
        *,
        actor: str,
        room: str,
        title: str,
        topic: str,
        source_request: str,
        items: list[str],
    ) -> dict[str, Any]:
        now = _now_iso()
        checklist_id = str(uuid.uuid4())
        record = {
            "checklist_id": checklist_id,
            "object_kind": "checklist",
            "actor": actor.strip() or "Chris",
            "room": room.strip() or "office",
            "title": title.strip() or "Checklist",
            "topic": topic.strip(),
            "source_request": source_request.strip(),
            "status": "created",
            "created_at": now,
            "updated_at": now,
            "item_count": len(items),
            "items": [
                {
                    "item_id": f"item-{index + 1}",
                    "text": item,
                    "completed": False,
                }
                for index, item in enumerate(items)
            ],
        }
        payload = self.load()
        checklists = dict(payload.get("checklists", {}))
        history = list(payload.get("history", []))
        checklists[checklist_id] = record
        history.append(
            {
                "event": "checklist-created",
                "checklist_id": checklist_id,
                "title": record["title"],
                "topic": record["topic"],
                "actor": record["actor"],
                "created_at": now,
            }
        )
        payload["checklists"] = checklists
        payload["history"] = history[-200:]
        self.save(payload)
        return record

    def get_checklist(self, checklist_id: str) -> dict[str, Any] | None:
        payload = self.load()
        record = payload.get("checklists", {}).get(checklist_id)
        return dict(record) if isinstance(record, dict) else None


_DIRECT_CHECKLIST_PATTERNS = (
    re.compile(r"^(?:make|build|create)(?: me)? a checklist(?:\s+(?:for|about))?\s+(?P<topic>.+?)\.?$", re.IGNORECASE),
    re.compile(r"^i need a checklist(?:\s+(?:for|about))?\s+(?P<topic>.+?)\.?$", re.IGNORECASE),
    re.compile(r"^can you (?:make|build|create)(?: me)? a checklist(?:\s+(?:for|about))?\s+(?P<topic>.+?)\.?$", re.IGNORECASE),
)
_DIRECT_CHECKLIST_STARTERS = (
    "make me a checklist",
    "make a checklist",
    "build a checklist",
    "create a checklist",
    "i need a checklist",
    "can you make me a checklist",
    "can you build a checklist",
    "can you create a checklist",
)


def is_direct_checklist_request(request: str) -> bool:
    lowered = str(request or "").strip().lower()
    return any(lowered.startswith(prefix) for prefix in _DIRECT_CHECKLIST_STARTERS)


def extract_checklist_topic(request: str) -> str:
    cleaned = " ".join(str(request or "").strip().split())
    for pattern in _DIRECT_CHECKLIST_PATTERNS:
        matched = pattern.match(cleaned)
        if not matched:
            continue
        topic = str(matched.group("topic") or "").strip().rstrip(".?!")
        return topic
    return ""


def _topic_title(topic: str) -> str:
    cleaned = str(topic or "").strip().rstrip(".")
    if not cleaned:
        return "Checklist"
    if cleaned.lower().startswith(("the ", "this ", "my ", "our ")):
        return f"{cleaned[0].upper()}{cleaned[1:]} checklist"
    return f"Checklist for {cleaned}"


def _generic_checklist_items(topic: str) -> list[str]:
    cleaned = str(topic or "").strip().rstrip(".")
    return [
        f"Write down what has to happen for {cleaned}",
        f"Gather the things you need for {cleaned}",
        f"Handle the time-sensitive parts of {cleaned} first",
        f"Do a quick review pass before {cleaned}",
    ]


def build_checklist_items(topic: str) -> list[str]:
    lowered = str(topic or "").strip().lower()
    if any(term in lowered for term in ("trip", "travel", "vacation", "flight")):
        return [
            "Confirm the timing and any tickets or reservations",
            "Pack clothes for the weather and one backup layer",
            "Pack chargers, meds, toiletries, and travel basics",
            "Make sure IDs, wallet, and keys are set aside",
            "Do one last house and bag check before leaving",
        ]
    if any(term in lowered for term in ("scout", "campout", "camping", "camp")):
        return [
            "Confirm the departure time, location, and required forms",
            "Pack sleeping gear, clothes layers, and rain backup",
            "Pack water, mess kit, flashlight, and personal items",
            "Check any troop gear, food, or duty assignments",
            "Do a final gear check before loading out",
        ]
    if "weekend" in lowered:
        return [
            "Lock in what actually has to happen this weekend",
            "Pull together the things you need ahead of time",
            "Set one anchor block for errands, plans, or rest",
            "Leave one pass for anything that can still move",
        ]
    return _generic_checklist_items(topic)


def build_direct_checklist_response(
    store: ChecklistStore,
    *,
    actor: str,
    room: str,
    request: str,
) -> dict[str, Any] | None:
    if not is_direct_checklist_request(request):
        return None
    topic = extract_checklist_topic(request)
    if not topic:
        return {
            "output_text": "I can do that. What is the checklist for?",
            "created_checklist": None,
        }
    items = build_checklist_items(topic)
    created = store.create_checklist(
        actor=actor,
        room=room,
        title=_topic_title(topic),
        topic=topic,
        source_request=request,
        items=items,
    )
    return {
        "output_text": f"I made a checklist for {topic}. It has {len(items)} items to start.",
        "created_checklist": created,
    }
