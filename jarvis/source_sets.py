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
class SourceSetStore:
    root: Path
    read_only: bool = False
    index_path: Path = field(init=False)
    log_path: Path = field(init=False)

    def __post_init__(self) -> None:
        self.index_path = self.root / "source_sets.json"
        self.log_path = self.root / "source_sets_log.jsonl"

    def load(self) -> dict[str, Any]:
        default = {"source_sets": {}, "history": []}
        if not self.index_path.exists():
            return default
        try:
            payload = json.loads(self.index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return default
        if not isinstance(payload, dict):
            return default
        payload.setdefault("source_sets", {})
        payload.setdefault("history", [])
        return payload

    def save(self, payload: dict[str, Any]) -> None:
        if self.read_only:
            raise RuntimeError("Source-set storage is read-only in this mode.")
        self.root.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self.index_path, payload)
        append_jsonl(
            self.log_path,
            {
                "saved_at": _now_iso(),
                "records": payload,
            },
        )

    def create_source_set(
        self,
        *,
        actor: str,
        room: str,
        title: str,
        topic: str,
        source_request: str,
        summary: str,
        source_groups: list[dict[str, Any]],
        open_questions: list[str],
    ) -> dict[str, Any]:
        now = _now_iso()
        source_set_id = str(uuid.uuid4())
        record = {
            "source_set_id": source_set_id,
            "object_kind": "source_set",
            "actor": actor.strip() or "Chris",
            "room": room.strip() or "office",
            "title": title.strip() or "Source set",
            "topic": topic.strip(),
            "source_request": source_request.strip(),
            "status": "created",
            "created_at": now,
            "updated_at": now,
            "summary": summary.strip(),
            "source_groups": list(source_groups),
            "open_questions": list(open_questions),
            "truth_mode": "local_source_set_scaffold_only",
            "live_retrieval_used": False,
            "source_verification_completed": False,
        }
        payload = self.load()
        source_sets = dict(payload.get("source_sets", {}))
        history = list(payload.get("history", []))
        source_sets[source_set_id] = record
        history.append(
            {
                "event": "source-set-created",
                "source_set_id": source_set_id,
                "title": record["title"],
                "topic": record["topic"],
                "actor": record["actor"],
                "created_at": now,
            }
        )
        payload["source_sets"] = source_sets
        payload["history"] = history[-200:]
        self.save(payload)
        return record

    def get_source_set(self, source_set_id: str) -> dict[str, Any] | None:
        payload = self.load()
        record = payload.get("source_sets", {}).get(source_set_id)
        return dict(record) if isinstance(record, dict) else None


_DIRECT_SOURCE_SET_PATTERNS = (
    re.compile(r"^put together a source set(?:\s+(?:on|for|around))?\s+(?P<topic>.+?)\.?$", re.IGNORECASE),
    re.compile(r"^collect the sources(?:\s+(?:for|on|around))?\s+(?P<topic>.+?)\.?$", re.IGNORECASE),
    re.compile(r"^make me a source set(?:\s+(?:for|on|around))?\s+(?P<topic>.+?)\.?$", re.IGNORECASE),
    re.compile(r"^organize the source material(?:\s+(?:for|on|around))?\s+(?P<topic>.+?)\.?$", re.IGNORECASE),
)
_DIRECT_SOURCE_SET_STARTERS = (
    "put together a source set",
    "collect the sources",
    "make me a source set",
    "organize the source material",
)


def is_direct_source_set_request(request: str) -> bool:
    lowered = " ".join(str(request or "").strip().split()).lower()
    return any(lowered.startswith(prefix) for prefix in _DIRECT_SOURCE_SET_STARTERS)


def extract_source_set_topic(request: str) -> str:
    cleaned = " ".join(str(request or "").strip().split())
    for pattern in _DIRECT_SOURCE_SET_PATTERNS:
        matched = pattern.match(cleaned)
        if not matched:
            continue
        return str(matched.group("topic") or "").strip().rstrip(".?!")
    return ""


def _title(topic: str) -> str:
    cleaned = str(topic or "").strip().rstrip(".")
    if not cleaned:
        return "Source set"
    return f"Source set for {cleaned}"


def _summary(topic: str) -> str:
    cleaned = str(topic or "").strip()
    return (
        f"This source set is a local scaffold for {cleaned}. "
        "It does not claim live retrieval or verified external source collection."
    )


def _source_groups(topic: str) -> list[dict[str, Any]]:
    lowered = str(topic or "").strip().lower()
    if "passive income" in lowered:
        groups = [
            ("market-context", "Market context and lane definitions"),
            ("risk-tradeoffs", "Risk and maintenance tradeoffs"),
            ("examples", "Example lanes or candidate models to inspect"),
        ]
    elif "retirement workshop" in lowered:
        groups = [
            ("decision-context", "Decision context and participant needs"),
            ("numbers", "Numbers, constraints, and planning inputs"),
            ("follow-up", "Follow-up questions and unresolved gaps"),
        ]
    elif "pool robot" in lowered:
        groups = [
            ("product-candidates", "Candidate products or categories"),
            ("evaluation-criteria", "Evaluation criteria and tradeoffs"),
            ("verification-gaps", "Verification gaps before purchase"),
        ]
    elif "scout trailer" in lowered:
        groups = [
            ("storage-categories", "Storage categories or option types"),
            ("risk-factors", "Security, weather, and access factors"),
            ("site-checks", "Site-specific checks still needed"),
        ]
    else:
        groups = [
            ("context", "Context and framing"),
            ("comparison-points", "Comparison points or key claims"),
            ("gaps", "Open gaps and checks still needed"),
        ]
    return [
        {
            "group_id": f"group-{index + 1}",
            "label": label,
            "items": [],
        }
        for index, (_, label) in enumerate(groups)
    ]


def _open_questions(topic: str) -> list[str]:
    cleaned = str(topic or "").strip()
    return [
        f"What source types matter most for {cleaned}?",
        f"What is still missing from the source picture for {cleaned}?",
        f"What would need live retrieval or verification before trusting the source set for {cleaned}?",
    ]


def build_direct_source_set_response(
    store: SourceSetStore,
    *,
    actor: str,
    room: str,
    request: str,
) -> dict[str, Any] | None:
    if not is_direct_source_set_request(request):
        return None
    topic = extract_source_set_topic(request)
    if not topic:
        return {
            "output_text": "I can do that. What should the source set cover?",
            "created_source_set": None,
        }
    created = store.create_source_set(
        actor=actor,
        room=room,
        title=_title(topic),
        topic=topic,
        source_request=request,
        summary=_summary(topic),
        source_groups=_source_groups(topic),
        open_questions=_open_questions(topic),
    )
    return {
        "output_text": (
            f"I made a source set for {topic}. "
            "It is a bounded local source scaffold, not a claim of live retrieval or verified source collection."
        ),
        "created_source_set": created,
    }
