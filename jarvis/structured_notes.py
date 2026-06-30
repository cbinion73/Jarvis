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
class StructuredNoteStore:
    root: Path
    read_only: bool = False
    index_path: Path = field(init=False)
    log_path: Path = field(init=False)

    def __post_init__(self) -> None:
        self.index_path = self.root / "structured_notes.json"
        self.log_path = self.root / "structured_notes_log.jsonl"

    def load(self) -> dict[str, Any]:
        default = {"structured_notes": {}, "history": []}
        if not self.index_path.exists():
            return default
        try:
            payload = json.loads(self.index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return default
        if not isinstance(payload, dict):
            return default
        payload.setdefault("structured_notes", {})
        payload.setdefault("history", [])
        return payload

    def save(self, payload: dict[str, Any]) -> None:
        if self.read_only:
            raise RuntimeError("Structured-note storage is read-only in this mode.")
        self.root.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self.index_path, payload)
        append_jsonl(
            self.log_path,
            {
                "saved_at": _now_iso(),
                "records": payload,
            },
        )

    def create_note(
        self,
        *,
        actor: str,
        room: str,
        title: str,
        topic: str,
        source_request: str,
        summary: str,
        note_lines: list[str],
        tags: list[str],
    ) -> dict[str, Any]:
        now = _now_iso()
        note_id = str(uuid.uuid4())
        record = {
            "note_id": note_id,
            "object_kind": "structured_note",
            "actor": actor.strip() or "Chris",
            "room": room.strip() or "office",
            "title": title.strip() or "Structured note",
            "topic": topic.strip(),
            "source_request": source_request.strip(),
            "status": "created",
            "created_at": now,
            "updated_at": now,
            "summary": summary.strip(),
            "note_lines": list(note_lines),
            "tags": list(tags),
            "truth_mode": "local_structured_note_only",
            "external_note_system_used": False,
            "obsidian_write_used": False,
        }
        payload = self.load()
        notes = dict(payload.get("structured_notes", {}))
        history = list(payload.get("history", []))
        notes[note_id] = record
        history.append(
            {
                "event": "structured-note-created",
                "note_id": note_id,
                "title": record["title"],
                "topic": record["topic"],
                "actor": record["actor"],
                "created_at": now,
            }
        )
        payload["structured_notes"] = notes
        payload["history"] = history[-200:]
        self.save(payload)
        return record

    def get_note(self, note_id: str) -> dict[str, Any] | None:
        payload = self.load()
        record = payload.get("structured_notes", {}).get(note_id)
        return dict(record) if isinstance(record, dict) else None


_DIRECT_STRUCTURED_NOTE_PATTERNS = (
    re.compile(r"^turn this into a note(?:\s+(?:for|about|on))?\s*(?P<topic>.+?)?\.?$", re.IGNORECASE),
    re.compile(r"^capture a note(?:\s+(?:for|about|on))?\s+(?P<topic>.+?)\.?$", re.IGNORECASE),
    re.compile(r"^make me a note(?:\s+(?:for|about|on))?\s+(?P<topic>.+?)\.?$", re.IGNORECASE),
    re.compile(r"^write this down as a note(?:\s+(?:for|about|on))?\s+(?P<topic>.+?)\.?$", re.IGNORECASE),
)
_DIRECT_STRUCTURED_NOTE_STARTERS = (
    "turn this into a note",
    "capture a note",
    "make me a note",
    "write this down as a note",
)


def is_direct_structured_note_request(request: str) -> bool:
    lowered = " ".join(str(request or "").strip().split()).lower()
    return any(lowered.startswith(prefix) for prefix in _DIRECT_STRUCTURED_NOTE_STARTERS)


def extract_structured_note_topic(request: str) -> str:
    cleaned = " ".join(str(request or "").strip().split())
    for pattern in _DIRECT_STRUCTURED_NOTE_PATTERNS:
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
        return "Structured note"
    return f"Note for {cleaned}"


def _summary(topic: str) -> str:
    cleaned = str(topic or "").strip()
    return (
        f"This note is a local structured capture for {cleaned}. "
        "It does not claim an Obsidian save or any external note sync."
    )


def _note_lines(topic: str) -> list[str]:
    cleaned = str(topic or "").strip()
    lowered = cleaned.lower()
    if "passive income" in lowered:
        lines = [
            "Topic capture: passive income ideas worth sorting later",
            "Keep the first pass focused on lanes, tradeoffs, and next checks",
            "Do not treat this note as proof of research or external verification",
        ]
    elif "retirement workshop" in lowered:
        lines = [
            "Topic capture: retirement workshop planning note",
            "Hold the main questions, constraints, and follow-up items in one place",
            "Keep external sources or workshop materials separate unless they were actually added",
        ]
    elif "scout trailer" in lowered:
        lines = [
            "Topic capture: Scout trailer storage note",
            "Keep option ideas, risks, and open checks together",
            "Do not imply any synced note system or external storage write",
        ]
    else:
        lines = [
            f"Topic capture: {cleaned}",
            f"Keep the core idea for {cleaned} in one bounded local note",
            f"Separate what is captured now from anything that still needs deeper work on {cleaned}",
        ]
    return lines


def _tags(topic: str) -> list[str]:
    cleaned = str(topic or "").strip().lower()
    base = ["local-note", "structured-capture"]
    if "retirement" in cleaned:
        base.append("retirement")
    elif "passive income" in cleaned:
        base.append("passive-income")
    elif "scout" in cleaned:
        base.append("scout")
    return base


def build_direct_structured_note_response(
    store: StructuredNoteStore,
    *,
    actor: str,
    room: str,
    request: str,
) -> dict[str, Any] | None:
    if not is_direct_structured_note_request(request):
        return None
    topic = extract_structured_note_topic(request)
    if not topic:
        return {
            "output_text": "I can do that. What should the note be about?",
            "created_structured_note": None,
        }
    created = store.create_note(
        actor=actor,
        room=room,
        title=_title(topic),
        topic=topic,
        source_request=request,
        summary=_summary(topic),
        note_lines=_note_lines(topic),
        tags=_tags(topic),
    )
    return {
        "output_text": (
            f"I made a note for {topic}. "
            "It is a bounded local note object, not a claim of an Obsidian save or external note sync."
        ),
        "created_structured_note": created,
    }
