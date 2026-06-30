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
class DraftStore:
    root: Path
    read_only: bool = False
    index_path: Path = field(init=False)
    log_path: Path = field(init=False)

    def __post_init__(self) -> None:
        self.index_path = self.root / "drafts.json"
        self.log_path = self.root / "drafts_log.jsonl"

    def load(self) -> dict[str, Any]:
        default = {"drafts": {}, "history": []}
        if not self.index_path.exists():
            return default
        try:
            payload = json.loads(self.index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return default
        if not isinstance(payload, dict):
            return default
        payload.setdefault("drafts", {})
        payload.setdefault("history", [])
        return payload

    def save(self, payload: dict[str, Any]) -> None:
        if self.read_only:
            raise RuntimeError("Draft storage is read-only in this mode.")
        self.root.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self.index_path, payload)
        append_jsonl(
            self.log_path,
            {
                "saved_at": _now_iso(),
                "records": payload,
            },
        )

    def create_draft(
        self,
        *,
        actor: str,
        room: str,
        title: str,
        topic: str,
        draft_kind: str,
        source_request: str,
        content: str,
    ) -> dict[str, Any]:
        now = _now_iso()
        draft_id = str(uuid.uuid4())
        record = {
            "draft_id": draft_id,
            "object_kind": "draft",
            "draft_kind": draft_kind,
            "actor": actor.strip() or "Chris",
            "room": room.strip() or "office",
            "title": title.strip() or "Draft",
            "topic": topic.strip(),
            "source_request": source_request.strip(),
            "status": "created",
            "created_at": now,
            "updated_at": now,
            "content": content.strip(),
            "preview": content.strip().splitlines()[0][:160] if content.strip() else "",
        }
        payload = self.load()
        drafts = dict(payload.get("drafts", {}))
        history = list(payload.get("history", []))
        drafts[draft_id] = record
        history.append(
            {
                "event": "draft-created",
                "draft_id": draft_id,
                "title": record["title"],
                "topic": record["topic"],
                "draft_kind": record["draft_kind"],
                "actor": record["actor"],
                "created_at": now,
            }
        )
        payload["drafts"] = drafts
        payload["history"] = history[-200:]
        self.save(payload)
        return record

    def get_draft(self, draft_id: str) -> dict[str, Any] | None:
        payload = self.load()
        record = payload.get("drafts", {}).get(draft_id)
        return dict(record) if isinstance(record, dict) else None


_DIRECT_DRAFT_PATTERNS = (
    re.compile(
        r"^draft(?: me)?\s+(?:a|an)?\s*(?P<artifact>text|message|email(?: draft)?|draft email|outline)(?P<topic>\s+.+?)?\.?$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^write(?: me)?\s+(?:a|an)?\s*(?P<artifact>text|message|email(?: draft)?|draft email|outline)(?P<topic>\s+.+?)?\.?$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^create(?: me)?\s+(?:a|an)?\s*(?P<artifact>draft(?:\s+(?:message|email|text|outline))?)(?P<topic>\s+.+?)?\.?$",
        re.IGNORECASE,
    ),
)


def _normalize_artifact(raw: str) -> str:
    lowered = str(raw or "").strip().lower()
    if lowered in {"draft email", "email draft", "email"}:
        return "email"
    if lowered in {"draft message", "message"}:
        return "message"
    if lowered in {"draft text", "text"}:
        return "text"
    if lowered in {"draft outline", "outline"}:
        return "outline"
    return "draft"


def is_direct_draft_request(request: str) -> bool:
    cleaned = " ".join(str(request or "").strip().split())
    return any(pattern.match(cleaned) for pattern in _DIRECT_DRAFT_PATTERNS)


def extract_draft_details(request: str) -> tuple[str, str]:
    cleaned = " ".join(str(request or "").strip().split())
    for pattern in _DIRECT_DRAFT_PATTERNS:
        matched = pattern.match(cleaned)
        if not matched:
            continue
        artifact = _normalize_artifact(str(matched.group("artifact") or ""))
        topic = str(matched.group("topic") or "").strip().rstrip(".?!")
        return artifact, topic
    return "draft", ""


def _strip_leading_preposition(topic: str) -> str:
    return re.sub(r"^(?:to|for|about|on|regarding)\s+", "", str(topic or "").strip(), flags=re.IGNORECASE).strip()


def _draft_title(draft_kind: str, topic: str) -> str:
    cleaned_topic = str(topic or "").strip()
    if draft_kind == "outline":
        stripped = _strip_leading_preposition(cleaned_topic)
        return f"Outline for {stripped}" if stripped else "Outline"
    if not cleaned_topic:
        return "Draft"
    label = {
        "email": "Email draft",
        "message": "Message draft",
        "text": "Text draft",
    }.get(draft_kind, "Draft")
    return f"{label} {cleaned_topic}".strip()


def _recipient_and_subject(topic: str) -> tuple[str, str]:
    cleaned = str(topic or "").strip()
    lowered = cleaned.lower()
    recipient = ""
    subject = ""
    if " about " in lowered:
        split_index = lowered.index(" about ")
        before = cleaned[:split_index].strip()
        after = cleaned[split_index + len(" about "):].strip()
        if before.lower().startswith("to "):
            recipient = before[3:].strip()
        subject = after
    elif lowered.startswith("to "):
        recipient = cleaned[3:].strip()
    elif lowered.startswith("about "):
        subject = cleaned[6:].strip()
    elif lowered.startswith("for "):
        subject = cleaned[4:].strip()
    else:
        subject = cleaned
    return recipient, subject


def _build_text_like_content(draft_kind: str, topic: str) -> str:
    recipient, subject = _recipient_and_subject(topic)
    greeting_name = recipient or "there"
    subject_line = f" about {subject}" if subject else ""
    opener = "Hi" if draft_kind == "email" else "Hey"
    closing = "Thanks,\nChris" if draft_kind == "email" else "Let me know what works."
    body = (
        f"{opener} {greeting_name},\n\n"
        f"Quick note{subject_line}. I wanted to reach out now so this is clear and easy to act on.\n\n"
        f"{closing}"
    )
    if draft_kind == "email":
        subject_text = subject.title() if subject else "Quick note"
        return f"Subject: {subject_text}\n\n{body}"
    return body


def _build_outline_content(topic: str) -> str:
    subject = _strip_leading_preposition(topic) or "the topic"
    lowered = subject.lower()
    if "passive income" in lowered and "active building" in lowered:
        bullets = [
            "Frame the tension between passive income and active building",
            "Show where passive income helps and where it can blur the real work",
            "Ground the contrast in one concrete example or lived tradeoff",
            "Close with the choice or takeaway you want the reader to keep",
        ]
    else:
        bullets = [
            f"Open with what {subject} is really trying to answer",
            f"Lay out the main contrast or structure inside {subject}",
            f"Add one concrete example that makes {subject} real",
            f"Close with the next move or takeaway for {subject}",
        ]
    return "\n".join(f"{index + 1}. {bullet}" for index, bullet in enumerate(bullets))


def build_draft_content(draft_kind: str, topic: str) -> str:
    if draft_kind == "outline":
        return _build_outline_content(topic)
    return _build_text_like_content(draft_kind, topic)


def _descriptor(draft_kind: str, topic: str) -> str:
    noun = {
        "email": "email",
        "message": "message",
        "text": "text",
        "outline": "outline",
    }.get(draft_kind, "draft")
    article = "an" if noun[:1] in {"a", "e", "i", "o", "u"} else "a"
    cleaned_topic = str(topic or "").strip()
    if not cleaned_topic:
        return f"{article} {noun}"
    if cleaned_topic.lower().startswith(("to ", "for ", "about ", "on ", "regarding ")):
        return f"{article} {noun} {cleaned_topic}"
    return f"{article} {noun} about {cleaned_topic}"


def _missing_context_prompt(draft_kind: str) -> str:
    if draft_kind == "outline":
        return "I can do that. What should the outline cover?"
    if draft_kind in {"email", "message", "text"}:
        return "I can do that. Who is it for, and what is it about?"
    return "I can do that. What should the draft be about?"


def build_direct_draft_response(
    store: DraftStore,
    *,
    actor: str,
    room: str,
    request: str,
) -> dict[str, Any] | None:
    if not is_direct_draft_request(request):
        return None
    draft_kind, topic = extract_draft_details(request)
    if not topic:
        return {
            "output_text": _missing_context_prompt(draft_kind),
            "created_draft": None,
        }
    created = store.create_draft(
        actor=actor,
        room=room,
        title=_draft_title(draft_kind, topic),
        topic=topic,
        draft_kind=draft_kind,
        source_request=request,
        content=build_draft_content(draft_kind, topic),
    )
    return {
        "output_text": f"I drafted {_descriptor(draft_kind, topic)}. It is ready to review.",
        "created_draft": created,
    }
