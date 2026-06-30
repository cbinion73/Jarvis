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
class RecapPacketStore:
    root: Path
    read_only: bool = False
    index_path: Path = field(init=False)
    log_path: Path = field(init=False)

    def __post_init__(self) -> None:
        self.index_path = self.root / "recap_packets.json"
        self.log_path = self.root / "recap_packets_log.jsonl"

    def load(self) -> dict[str, Any]:
        default = {"recap_packets": {}, "history": []}
        if not self.index_path.exists():
            return default
        try:
            payload = json.loads(self.index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return default
        if not isinstance(payload, dict):
            return default
        payload.setdefault("recap_packets", {})
        payload.setdefault("history", [])
        return payload

    def save(self, payload: dict[str, Any]) -> None:
        if self.read_only:
            raise RuntimeError("Recap-packet storage is read-only in this mode.")
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
        highlights: list[dict[str, Any]],
        open_questions: list[str],
    ) -> dict[str, Any]:
        now = _now_iso()
        packet_id = str(uuid.uuid4())
        record = {
            "packet_id": packet_id,
            "object_kind": "recap_packet",
            "actor": actor.strip() or "Chris",
            "room": room.strip() or "office",
            "title": title.strip() or "Recap packet",
            "topic": topic.strip(),
            "source_request": source_request.strip(),
            "status": "created",
            "created_at": now,
            "updated_at": now,
            "summary": summary.strip(),
            "highlights": list(highlights),
            "open_questions": list(open_questions),
            "truth_mode": "local_recap_scaffold_only",
            "live_retrieval_used": False,
            "external_synthesis_complete": False,
        }
        payload = self.load()
        packets = dict(payload.get("recap_packets", {}))
        history = list(payload.get("history", []))
        packets[packet_id] = record
        history.append(
            {
                "event": "recap-packet-created",
                "packet_id": packet_id,
                "title": record["title"],
                "topic": record["topic"],
                "actor": record["actor"],
                "created_at": now,
            }
        )
        payload["recap_packets"] = packets
        payload["history"] = history[-200:]
        self.save(payload)
        return record

    def get_packet(self, packet_id: str) -> dict[str, Any] | None:
        payload = self.load()
        record = payload.get("recap_packets", {}).get(packet_id)
        return dict(record) if isinstance(record, dict) else None


_DIRECT_RECAP_PATTERNS = (
    re.compile(r"^give me a recap(?:\s+(?:of|on|for))?\s+(?P<topic>.+?)\.?$", re.IGNORECASE),
    re.compile(r"^summarize(?: this)?(?:\s+into a packet)?(?:\s+(?:for|of|on))?\s*(?P<topic>.+?)?\.?$", re.IGNORECASE),
    re.compile(r"^make me a brief(?:\s+(?:on|for|of))?\s+(?P<topic>.+?)\.?$", re.IGNORECASE),
    re.compile(r"^put together a recap(?:\s+(?:on|for|of))?\s+(?P<topic>.+?)\.?$", re.IGNORECASE),
)
_DIRECT_RECAP_STARTERS = (
    "give me a recap",
    "summarize",
    "make me a brief",
    "put together a recap",
)


def is_direct_recap_packet_request(request: str) -> bool:
    lowered = " ".join(str(request or "").strip().split()).lower()
    return any(lowered.startswith(prefix) for prefix in _DIRECT_RECAP_STARTERS)


def extract_recap_topic(request: str) -> str:
    cleaned = " ".join(str(request or "").strip().split())
    for pattern in _DIRECT_RECAP_PATTERNS:
        matched = pattern.match(cleaned)
        if not matched:
            continue
        return str(matched.group("topic") or "").strip().rstrip(".?!")
    return ""


def _title(topic: str) -> str:
    cleaned = str(topic or "").strip().rstrip(".")
    if not cleaned:
        return "Recap packet"
    return f"Recap packet for {cleaned}"


def _summary(topic: str) -> str:
    cleaned = str(topic or "").strip()
    return (
        f"This recap packet is a local scaffold for {cleaned}. "
        "It does not claim live retrieval or complete external synthesis."
    )


def _highlights(topic: str) -> list[dict[str, Any]]:
    lowered = str(topic or "").strip().lower()
    if "retirement" in lowered:
        lines = [
            "Frame the main retirement options or paths in play",
            "Capture the biggest tradeoffs that still drive the decision",
            "Separate what is known from what still needs stronger evidence",
        ]
    elif "passive income" in lowered:
        lines = [
            "Summarize the main passive-income lanes under consideration",
            "Capture the biggest risk, effort, and maintenance tradeoffs",
            "Mark where the recap still rests on assumptions instead of verified evidence",
        ]
    elif "scout trailer" in lowered:
        lines = [
            "Summarize the storage options or categories under discussion",
            "Capture the tradeoffs around weather, access, and security",
            "Mark which parts still need live confirmation or site-specific proof",
        ]
    else:
        lines = [
            f"Summarize the main threads inside {topic}",
            f"Capture the key tradeoffs or decisions around {topic}",
            f"Mark what remains unverified or incomplete for {topic}",
        ]
    return [
        {
            "highlight_id": f"highlight-{index + 1}",
            "text": text,
        }
        for index, text in enumerate(lines)
    ]


def _open_questions(topic: str) -> list[str]:
    cleaned = str(topic or "").strip()
    return [
        f"What still needs better proof or synthesis for {cleaned}?",
        f"What is the most decision-relevant gap in {cleaned}?",
        f"What should the next deeper pass on {cleaned} resolve?",
    ]


def build_direct_recap_packet_response(
    store: RecapPacketStore,
    *,
    actor: str,
    room: str,
    request: str,
) -> dict[str, Any] | None:
    if not is_direct_recap_packet_request(request):
        return None
    topic = extract_recap_topic(request)
    if topic.lower() in {"me", "this", "it"}:
        topic = ""
    if not topic:
        return {
            "output_text": "I can do that. What should the recap packet cover?",
            "created_recap_packet": None,
        }
    created = store.create_packet(
        actor=actor,
        room=room,
        title=_title(topic),
        topic=topic,
        source_request=request,
        summary=_summary(topic),
        highlights=_highlights(topic),
        open_questions=_open_questions(topic),
    )
    return {
        "output_text": (
            f"I made a recap packet for {topic}. "
            "It is a bounded local recap scaffold, not a claim of live retrieval or complete external synthesis."
        ),
        "created_recap_packet": created,
    }
