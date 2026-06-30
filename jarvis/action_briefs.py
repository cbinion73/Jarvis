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
class ActionBriefStore:
    root: Path
    read_only: bool = False
    index_path: Path = field(init=False)
    log_path: Path = field(init=False)

    def __post_init__(self) -> None:
        self.index_path = self.root / "action_briefs.json"
        self.log_path = self.root / "action_briefs_log.jsonl"

    def load(self) -> dict[str, Any]:
        default = {"action_briefs": {}, "history": []}
        if not self.index_path.exists():
            return default
        try:
            payload = json.loads(self.index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return default
        if not isinstance(payload, dict):
            return default
        payload.setdefault("action_briefs", {})
        payload.setdefault("history", [])
        return payload

    def save(self, payload: dict[str, Any]) -> None:
        if self.read_only:
            raise RuntimeError("Action-brief storage is read-only in this mode.")
        self.root.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self.index_path, payload)
        append_jsonl(
            self.log_path,
            {
                "saved_at": _now_iso(),
                "records": payload,
            },
        )

    def create_brief(
        self,
        *,
        actor: str,
        room: str,
        title: str,
        topic: str,
        source_request: str,
        summary: str,
        next_steps: list[dict[str, Any]],
        cautions: list[str],
    ) -> dict[str, Any]:
        now = _now_iso()
        brief_id = str(uuid.uuid4())
        record = {
            "brief_id": brief_id,
            "object_kind": "action_brief",
            "actor": actor.strip() or "Chris",
            "room": room.strip() or "office",
            "title": title.strip() or "Action brief",
            "topic": topic.strip(),
            "source_request": source_request.strip(),
            "status": "created",
            "created_at": now,
            "updated_at": now,
            "summary": summary.strip(),
            "next_steps": list(next_steps),
            "cautions": list(cautions),
            "truth_mode": "local_action_brief_only",
            "live_execution_used": False,
            "task_sync_used": False,
            "calendar_sync_used": False,
            "delegation_used": False,
        }
        payload = self.load()
        briefs = dict(payload.get("action_briefs", {}))
        history = list(payload.get("history", []))
        briefs[brief_id] = record
        history.append(
            {
                "event": "action-brief-created",
                "brief_id": brief_id,
                "title": record["title"],
                "topic": record["topic"],
                "actor": record["actor"],
                "created_at": now,
            }
        )
        payload["action_briefs"] = briefs
        payload["history"] = history[-200:]
        self.save(payload)
        return record

    def get_brief(self, brief_id: str) -> dict[str, Any] | None:
        payload = self.load()
        record = payload.get("action_briefs", {}).get(brief_id)
        return dict(record) if isinstance(record, dict) else None


_DIRECT_ACTION_BRIEF_PATTERNS = (
    re.compile(r"^what should i do next on this\?\s*make me a brief\.?$", re.IGNORECASE),
    re.compile(r"^give me a next-steps brief(?:\s+(?:for|on))?\s+(?P<topic>.+?)\.?$", re.IGNORECASE),
    re.compile(r"^make me an action brief(?:\s+(?:for|on))?\s+(?P<topic>.+?)\.?$", re.IGNORECASE),
    re.compile(r"^help me move this forward and give me the brief\.?$", re.IGNORECASE),
)
_DIRECT_ACTION_BRIEF_STARTERS = (
    "what should i do next on this? make me a brief",
    "give me a next-steps brief",
    "make me an action brief",
    "help me move this forward and give me the brief",
)


def is_direct_action_brief_request(request: str) -> bool:
    lowered = " ".join(str(request or "").strip().split()).lower()
    return any(lowered.startswith(prefix) for prefix in _DIRECT_ACTION_BRIEF_STARTERS)


def extract_action_brief_topic(request: str) -> str:
    cleaned = " ".join(str(request or "").strip().split())
    for pattern in _DIRECT_ACTION_BRIEF_PATTERNS:
        matched = pattern.match(cleaned)
        if not matched:
            continue
        topic = str(matched.groupdict().get("topic", "") or "").strip().rstrip(".?!")
        if topic.lower() in {"me", "this", "it"}:
            return ""
        return topic
    return ""


def _title(topic: str) -> str:
    cleaned = str(topic or "").strip().rstrip(".")
    if not cleaned:
        return "Action brief"
    return f"Action brief for {cleaned}"


def _summary(topic: str) -> str:
    cleaned = str(topic or "").strip()
    return (
        f"This action brief is a local next-steps scaffold for {cleaned}. "
        "It does not claim live execution, delegation, or task or calendar sync."
    )


def _next_steps(topic: str) -> list[dict[str, Any]]:
    lowered = str(topic or "").strip().lower()
    if "retirement workshop" in lowered:
        steps = [
            "Define the one decision or outcome the workshop needs to drive",
            "Pull the main constraints or open questions into one short list",
            "Choose the next concrete prep move that reduces uncertainty fastest",
        ]
    elif "scout trailer" in lowered:
        steps = [
            "Name the main storage constraint or failure point first",
            "List the top option categories worth comparing next",
            "Choose the first check that would eliminate a weak option quickly",
        ]
    else:
        cleaned = str(topic or "").strip()
        steps = [
            f"Define the next concrete move for {cleaned}",
            f"Surface the biggest blocker still slowing {cleaned}",
            f"Pick the first action that would move {cleaned} forward this week",
        ]
    return [
        {
            "step_id": f"step-{index + 1}",
            "text": text,
        }
        for index, text in enumerate(steps)
    ]


def _cautions(topic: str) -> list[str]:
    cleaned = str(topic or "").strip()
    return [
        f"This brief is a local planning scaffold for {cleaned}, not a record of execution.",
        f"No task system, calendar, or delegation action has been triggered for {cleaned}.",
    ]


def build_direct_action_brief_response(
    store: ActionBriefStore,
    *,
    actor: str,
    room: str,
    request: str,
) -> dict[str, Any] | None:
    if not is_direct_action_brief_request(request):
        return None
    topic = extract_action_brief_topic(request)
    if not topic:
        return {
            "output_text": "I can do that. What should the action brief be about?",
            "created_action_brief": None,
        }
    created = store.create_brief(
        actor=actor,
        room=room,
        title=_title(topic),
        topic=topic,
        source_request=request,
        summary=_summary(topic),
        next_steps=_next_steps(topic),
        cautions=_cautions(topic),
    )
    return {
        "output_text": (
            f"I made an action brief for {topic}. "
            "It is a bounded local next-steps brief, not a claim of live execution, delegation, or task or calendar sync."
        ),
        "created_action_brief": created,
    }
