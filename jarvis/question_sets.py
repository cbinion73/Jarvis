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
class QuestionSetStore:
    root: Path
    read_only: bool = False
    index_path: Path = field(init=False)
    log_path: Path = field(init=False)

    def __post_init__(self) -> None:
        self.index_path = self.root / "question_sets.json"
        self.log_path = self.root / "question_sets_log.jsonl"

    def load(self) -> dict[str, Any]:
        default = {"question_sets": {}, "history": []}
        if not self.index_path.exists():
            return default
        try:
            payload = json.loads(self.index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return default
        if not isinstance(payload, dict):
            return default
        payload.setdefault("question_sets", {})
        payload.setdefault("history", [])
        return payload

    def save(self, payload: dict[str, Any]) -> None:
        if self.read_only:
            raise RuntimeError("Question-set storage is read-only in this mode.")
        self.root.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self.index_path, payload)
        append_jsonl(
            self.log_path,
            {
                "saved_at": _now_iso(),
                "records": payload,
            },
        )

    def create_question_set(
        self,
        *,
        actor: str,
        room: str,
        title: str,
        topic: str,
        source_request: str,
        summary: str,
        questions: list[str],
        framing_note: str,
    ) -> dict[str, Any]:
        now = _now_iso()
        question_set_id = str(uuid.uuid4())
        record = {
            "question_set_id": question_set_id,
            "object_kind": "question_set",
            "actor": actor.strip() or "Chris",
            "room": room.strip() or "office",
            "title": title.strip() or "Question set",
            "topic": topic.strip(),
            "source_request": source_request.strip(),
            "status": "created",
            "created_at": now,
            "updated_at": now,
            "summary": summary.strip(),
            "questions": list(questions),
            "framing_note": framing_note.strip(),
            "truth_mode": "local_question_set_scaffold_only",
            "live_research_used": False,
            "validated_discovery_used": False,
            "external_retrieval_used": False,
        }
        payload = self.load()
        question_sets = dict(payload.get("question_sets", {}))
        history = list(payload.get("history", []))
        question_sets[question_set_id] = record
        history.append(
            {
                "event": "question-set-created",
                "question_set_id": question_set_id,
                "title": record["title"],
                "topic": record["topic"],
                "actor": record["actor"],
                "created_at": now,
            }
        )
        payload["question_sets"] = question_sets
        payload["history"] = history[-200:]
        self.save(payload)
        return record

    def get_question_set(self, question_set_id: str) -> dict[str, Any] | None:
        payload = self.load()
        record = payload.get("question_sets", {}).get(question_set_id)
        return dict(record) if isinstance(record, dict) else None


_DIRECT_QUESTION_SET_PATTERNS = (
    re.compile(r"^what questions should i be asking(?:\s+(?:for|about|on))?\s+(?P<topic>.+?)\??$", re.IGNORECASE),
    re.compile(r"^make me a question set(?:\s+(?:for|on))?\s+(?P<topic>.+?)\.?$", re.IGNORECASE),
    re.compile(r"^help me figure out what we still need to clarify(?:\s+(?:for|about|on))?\s+(?P<topic>.+?)\.?$", re.IGNORECASE),
    re.compile(r"^give me the discovery questions(?:\s+(?:for|on))?\s+(?P<topic>.+?)\.?$", re.IGNORECASE),
)
_DIRECT_QUESTION_SET_STARTERS = (
    "what questions should i be asking",
    "make me a question set",
    "help me figure out what we still need to clarify",
    "give me the discovery questions",
)


def is_direct_question_set_request(request: str) -> bool:
    lowered = " ".join(str(request or "").strip().split()).lower()
    return any(lowered.startswith(prefix) for prefix in _DIRECT_QUESTION_SET_STARTERS)


def extract_question_set_topic(request: str) -> str:
    cleaned = " ".join(str(request or "").strip().split())
    for pattern in _DIRECT_QUESTION_SET_PATTERNS:
        matched = pattern.match(cleaned)
        if not matched:
            continue
        topic = str(matched.group("topic") or "").strip().rstrip(".?!")
        if topic.lower() in {"me", "this", "it"}:
            return ""
        return topic
    return ""


def _title(topic: str) -> str:
    cleaned = str(topic or "").strip().rstrip(".")
    if not cleaned:
        return "Question set"
    return f"Question set for {cleaned}"


def _summary(topic: str) -> str:
    cleaned = str(topic or "").strip()
    return (
        f"This question set is a local clarification scaffold for {cleaned}. "
        "It does not claim live research, validated discovery, or external retrieval."
    )


def _question_bundle(topic: str) -> tuple[list[str], str]:
    lowered = str(topic or "").strip().lower()
    if "retirement workshop" in lowered:
        questions = [
            "What exact outcome does the workshop need to produce?",
            "What do we still not know that could change the structure of the workshop?",
            "What constraints would make a simpler or staged format the smarter move?",
        ]
        note = "These are bounded local discovery questions, not the result of live research or validated discovery."
        return questions, note
    if "scout trailer" in lowered:
        questions = [
            "What storage conditions are actually non-negotiable for the trailer?",
            "What facts about size, access, or weather exposure are still missing?",
            "What unknown would most change the storage decision if it were answered next?",
        ]
        note = "These are local clarification questions, not live site discovery or external retrieval."
        return questions, note
    if "passive income" in lowered:
        questions = [
            "What do we still need to clarify about capital, time, and risk tolerance?",
            "Which unknown would most change the ranking of the passive-income lanes?",
            "What assumption is still being treated too casually in the current framing?",
        ]
        note = "These are bounded local discovery questions, not validated market research."
        return questions, note
    if "pool robot" in lowered:
        questions = [
            "What pool facts still need to be clarified before the robot direction is trustworthy?",
            "Which feature assumption is still driving too much of the decision?",
            "What missing budget or maintenance detail would most change the recommendation?",
        ]
        note = "These are local question prompts, not live product research or validated discovery."
        return questions, note
    cleaned = str(topic or "").strip()
    questions = [
        f"What is still unclear about {cleaned} that would change the decision or plan?",
        f"What assumption about {cleaned} needs to be tested instead of guessed?",
        f"What question would unlock the next clean move on {cleaned}?",
    ]
    note = f"These are bounded local clarification questions for {cleaned}, not live research or external retrieval."
    return questions, note


def build_direct_question_set_response(
    store: QuestionSetStore,
    *,
    actor: str,
    room: str,
    request: str,
) -> dict[str, Any] | None:
    if not is_direct_question_set_request(request):
        return None
    topic = extract_question_set_topic(request)
    if not topic:
        return {
            "output_text": "I can do that. What should the question set cover?",
            "created_question_set": None,
        }
    questions, note = _question_bundle(topic)
    created = store.create_question_set(
        actor=actor,
        room=room,
        title=_title(topic),
        topic=topic,
        source_request=request,
        summary=_summary(topic),
        questions=questions,
        framing_note=note,
    )
    return {
        "output_text": (
            f"I made a question set for {topic}. "
            "It is a bounded local clarification scaffold, not a claim of live research, validated discovery, or external retrieval."
        ),
        "created_question_set": created,
    }
