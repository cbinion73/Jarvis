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
class PlanStore:
    root: Path
    read_only: bool = False
    index_path: Path = field(init=False)
    log_path: Path = field(init=False)

    def __post_init__(self) -> None:
        self.index_path = self.root / "plans.json"
        self.log_path = self.root / "plans_log.jsonl"

    def load(self) -> dict[str, Any]:
        default = {"plans": {}, "history": []}
        if not self.index_path.exists():
            return default
        try:
            payload = json.loads(self.index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return default
        if not isinstance(payload, dict):
            return default
        payload.setdefault("plans", {})
        payload.setdefault("history", [])
        return payload

    def save(self, payload: dict[str, Any]) -> None:
        if self.read_only:
            raise RuntimeError("Plan storage is read-only in this mode.")
        self.root.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self.index_path, payload)
        append_jsonl(
            self.log_path,
            {
                "saved_at": _now_iso(),
                "records": payload,
            },
        )

    def create_plan(
        self,
        *,
        actor: str,
        room: str,
        title: str,
        topic: str,
        source_request: str,
        steps: list[str],
    ) -> dict[str, Any]:
        now = _now_iso()
        plan_id = str(uuid.uuid4())
        record = {
            "plan_id": plan_id,
            "object_kind": "plan",
            "actor": actor.strip() or "Chris",
            "room": room.strip() or "office",
            "title": title.strip() or "Plan",
            "topic": topic.strip(),
            "source_request": source_request.strip(),
            "status": "created",
            "created_at": now,
            "updated_at": now,
            "step_count": len(steps),
            "steps": [
                {
                    "step_id": f"step-{index + 1}",
                    "text": step,
                    "completed": False,
                }
                for index, step in enumerate(steps)
            ],
        }
        payload = self.load()
        plans = dict(payload.get("plans", {}))
        history = list(payload.get("history", []))
        plans[plan_id] = record
        history.append(
            {
                "event": "plan-created",
                "plan_id": plan_id,
                "title": record["title"],
                "topic": record["topic"],
                "actor": record["actor"],
                "created_at": now,
            }
        )
        payload["plans"] = plans
        payload["history"] = history[-200:]
        self.save(payload)
        return record

    def get_plan(self, plan_id: str) -> dict[str, Any] | None:
        payload = self.load()
        record = payload.get("plans", {}).get(plan_id)
        return dict(record) if isinstance(record, dict) else None


_DIRECT_PLAN_PATTERNS = (
    re.compile(r"^(?:make|build|create)(?: me)? a plan(?:\s+(?:for|about))?\s+(?P<topic>.+?)\.?$", re.IGNORECASE),
    re.compile(r"^i need a plan(?:\s+(?:for|about))?\s+(?P<topic>.+?)\.?$", re.IGNORECASE),
    re.compile(r"^can you (?:make|build|create)(?: me)? a plan(?:\s+(?:for|about))?\s+(?P<topic>.+?)\.?$", re.IGNORECASE),
)
_DIRECT_PLAN_STARTERS = (
    "make me a plan",
    "make a plan",
    "build a plan",
    "create a plan",
    "i need a plan",
    "can you make me a plan",
    "can you build a plan",
    "can you create a plan",
)


def is_direct_plan_request(request: str) -> bool:
    lowered = str(request or "").strip().lower()
    return any(lowered.startswith(prefix) for prefix in _DIRECT_PLAN_STARTERS)


def extract_plan_topic(request: str) -> str:
    cleaned = " ".join(str(request or "").strip().split())
    for pattern in _DIRECT_PLAN_PATTERNS:
        matched = pattern.match(cleaned)
        if not matched:
            continue
        topic = str(matched.group("topic") or "").strip().rstrip(".?!")
        return topic
    return ""


def _topic_title(topic: str) -> str:
    cleaned = str(topic or "").strip().rstrip(".")
    if not cleaned:
        return "Plan"
    if cleaned.lower().startswith(("the ", "this ", "my ", "our ")):
        return f"{cleaned[0].upper()}{cleaned[1:]} plan"
    return f"Plan for {cleaned}"


def _generic_plan_steps(topic: str) -> list[str]:
    cleaned = str(topic or "").strip().rstrip(".")
    return [
        f"Define the outcome for {cleaned}",
        f"Break {cleaned} into the main work blocks",
        f"Handle the time-sensitive or blocking pieces first",
        f"Set the next concrete action for {cleaned}",
    ]


def build_plan_steps(topic: str) -> list[str]:
    lowered = str(topic or "").strip().lower()
    if "garage" in lowered and any(term in lowered for term in ("clean", "cleaned", "cleaning", "cleaned out")):
        return [
            "Pick the part of the garage you are clearing first",
            "Pull out trash, obvious donations, and anything that needs to leave",
            "Group what stays by zone so it can go back cleanly",
            "Do the sweep, reset, and one final keep-or-cut pass",
        ]
    if any(term in lowered for term in ("scout", "campout", "camping", "camp")):
        return [
            "Lock in the schedule, forms, and who is responsible for what",
            "Split gear, food, and personal items into a packing pass",
            "Handle any prep work before the day-of rush",
            "Do one final load-out check before departure",
        ]
    if "retirement workshop" in lowered:
        return [
            "Decide the one outcome the workshop needs to produce",
            "Outline the main sections: framing, decisions, and next moves",
            "Pull the examples, materials, or numbers you need in the room",
            "Set the final prep pass so the workshop opens cleanly",
        ]
    if "draft" in lowered:
        return [
            "Name what is still unfinished in the draft",
            "Fix the biggest structure or clarity issue first",
            "Run one polish pass for wording and flow",
            "Finish with the final send-or-share check",
        ]
    return _generic_plan_steps(topic)


def build_direct_plan_response(
    store: PlanStore,
    *,
    actor: str,
    room: str,
    request: str,
) -> dict[str, Any] | None:
    if not is_direct_plan_request(request):
        return None
    topic = extract_plan_topic(request)
    if not topic:
        return {
            "output_text": "I can do that. What is the plan for?",
            "created_plan": None,
        }
    steps = build_plan_steps(topic)
    created = store.create_plan(
        actor=actor,
        room=room,
        title=_topic_title(topic),
        topic=topic,
        source_request=request,
        steps=steps,
    )
    return {
        "output_text": f"I made a plan for {topic}. It has {len(steps)} steps to start.",
        "created_plan": created,
    }
