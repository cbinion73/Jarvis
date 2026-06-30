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
class ResearchPacketStore:
    root: Path
    read_only: bool = False
    index_path: Path = field(init=False)
    log_path: Path = field(init=False)

    def __post_init__(self) -> None:
        self.index_path = self.root / "research_packets.json"
        self.log_path = self.root / "research_packets_log.jsonl"

    def load(self) -> dict[str, Any]:
        default = {"research_packets": {}, "history": []}
        if not self.index_path.exists():
            return default
        try:
            payload = json.loads(self.index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return default
        if not isinstance(payload, dict):
            return default
        payload.setdefault("research_packets", {})
        payload.setdefault("history", [])
        return payload

    def save(self, payload: dict[str, Any]) -> None:
        if self.read_only:
            raise RuntimeError("Research packet storage is read-only in this mode.")
        self.root.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self.index_path, payload)
        append_jsonl(
            self.log_path,
            {
                "saved_at": _now_iso(),
                "records": payload,
            },
        )

    def create_packet(
        self,
        *,
        actor: str,
        room: str,
        title: str,
        topic: str,
        source_request: str,
        summary: str,
        open_questions: list[str],
        next_steps: list[str],
        truth_mode: str = "local_scaffold_only",
        live_retrieval_used: bool = False,
        gathered_material: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        now = _now_iso()
        packet_id = str(uuid.uuid4())
        record = {
            "packet_id": packet_id,
            "object_kind": "research_packet",
            "actor": actor.strip() or "Chris",
            "room": room.strip() or "office",
            "title": title.strip() or "Research packet",
            "topic": topic.strip(),
            "source_request": source_request.strip(),
            "status": "created",
            "created_at": now,
            "updated_at": now,
            "summary": summary.strip(),
            "truth_mode": truth_mode.strip() or "local_scaffold_only",
            "live_retrieval_used": bool(live_retrieval_used),
            "gathered_material": list(gathered_material or []),
            "open_questions": list(open_questions),
            "next_steps": list(next_steps),
        }
        payload = self.load()
        packets = dict(payload.get("research_packets", {}))
        history = list(payload.get("history", []))
        packets[packet_id] = record
        history.append(
            {
                "event": "research-packet-created",
                "packet_id": packet_id,
                "title": record["title"],
                "topic": record["topic"],
                "actor": record["actor"],
                "created_at": now,
            }
        )
        payload["research_packets"] = packets
        payload["history"] = history[-200:]
        self.save(payload)
        return record

    def get_packet(self, packet_id: str) -> dict[str, Any] | None:
        payload = self.load()
        record = payload.get("research_packets", {}).get(packet_id)
        return dict(record) if isinstance(record, dict) else None


_DIRECT_RESEARCH_PATTERNS = (
    re.compile(r"^research\s+(?P<topic>.+?)\.?$", re.IGNORECASE),
    re.compile(r"^put together a research packet(?:\s+(?:for|on|about))?\s+(?P<topic>.+?)\.?$", re.IGNORECASE),
    re.compile(r"^build a research packet(?:\s+(?:for|on|about))?\s+(?P<topic>.+?)\.?$", re.IGNORECASE),
    re.compile(r"^create a research packet(?:\s+(?:for|on|about))?\s+(?P<topic>.+?)\.?$", re.IGNORECASE),
)
_DIRECT_RESEARCH_STARTERS = (
    "put together a research packet",
    "build a research packet",
    "create a research packet",
)


def is_direct_research_request(request: str) -> bool:
    lowered = " ".join(str(request or "").strip().split()).lower()
    if re.match(r"^research(?:[\s.?!]|$)", lowered):
        return True
    return any(lowered.startswith(prefix) for prefix in _DIRECT_RESEARCH_STARTERS)


def extract_research_topic(request: str) -> str:
    cleaned = " ".join(str(request or "").strip().split())
    for pattern in _DIRECT_RESEARCH_PATTERNS:
        matched = pattern.match(cleaned)
        if not matched:
            continue
        return str(matched.group("topic") or "").strip().rstrip(".?!")
    return ""


def _topic_title(topic: str) -> str:
    cleaned = str(topic or "").strip().rstrip(".")
    if not cleaned:
        return "Research packet"
    return f"Research packet on {cleaned}"


def _research_summary(topic: str) -> str:
    cleaned = str(topic or "").strip()
    return (
        f"This packet is a local scaffold for {cleaned}. "
        "It captures the research target and next steps, but it does not include live external findings yet."
    )


def _research_summary_with_sources(topic: str, gathered_material: list[dict[str, Any]]) -> str:
    cleaned = str(topic or "").strip()
    count = len(list(gathered_material or []))
    return (
        f"This packet is a scoped research object for {cleaned}. "
        f"It includes {count} attached live source summaries gathered for the first pass."
    )


def _research_open_questions(topic: str) -> list[str]:
    cleaned = str(topic or "").strip()
    lowered = cleaned.lower()
    if "retirement communit" in lowered:
        return [
            "Which locations or distance limits matter most?",
            "What budget or care-level constraints need to be compared?",
            "What tradeoffs should the packet track first: cost, services, or proximity?",
        ]
    if "pool robot" in lowered:
        return [
            "What pool size, surface, or debris load matters here?",
            "What price band should the packet compare first?",
            "Which buying criteria matter most: cleaning performance, reliability, or maintenance?",
        ]
    if "scout" in lowered and "trailer" in lowered:
        return [
            "What trailer dimensions or gear volume need to be covered?",
            "Is the main concern theft, weather, or daily access?",
            "Are there storage-site limits or costs that should shape the packet?",
        ]
    return [
        f"What constraints matter most for {cleaned}?",
        f"What comparison categories should the packet track for {cleaned}?",
        f"What decision will this research packet need to support for {cleaned}?",
    ]


def _research_next_steps(topic: str) -> list[str]:
    cleaned = str(topic or "").strip()
    return [
        f"Lock the scope and success criteria for {cleaned}",
        f"Gather the first credible sources or options for {cleaned}",
        f"Compare the strongest candidates against the same criteria",
    ]


def build_direct_research_packet_response(
    store: ResearchPacketStore,
    *,
    actor: str,
    room: str,
    request: str,
    retriever: Any | None = None,
) -> dict[str, Any] | None:
    if not is_direct_research_request(request):
        return None
    topic = extract_research_topic(request)
    if not topic:
        return {
            "output_text": "I can do that. What should the research packet cover?",
            "created_research_packet": None,
        }
    gathered_material: list[dict[str, Any]] = []
    if callable(retriever):
        try:
            raw_material = retriever(topic)
        except Exception:
            raw_material = []
        if isinstance(raw_material, list):
            gathered_material = [dict(item) for item in raw_material if isinstance(item, dict)]
    live_retrieval_used = bool(gathered_material)
    created = store.create_packet(
        actor=actor,
        room=room,
        title=_topic_title(topic),
        topic=topic,
        source_request=request,
        summary=_research_summary_with_sources(topic, gathered_material)
        if live_retrieval_used
        else _research_summary(topic),
        open_questions=_research_open_questions(topic),
        next_steps=_research_next_steps(topic),
        truth_mode="live_sources_attached" if live_retrieval_used else "local_scaffold_only",
        live_retrieval_used=live_retrieval_used,
        gathered_material=gathered_material,
    )
    output_text = (
        f"I made a research packet for {topic} with attached live source summaries."
        if live_retrieval_used
        else (
            f"I made a research packet scaffold for {topic}. "
            "It captures the scope and next steps, but it does not claim live external findings yet."
        )
    )
    return {
        "output_text": output_text,
        "created_research_packet": created,
    }
