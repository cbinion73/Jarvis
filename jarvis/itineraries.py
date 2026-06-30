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
class ItineraryStore:
    root: Path
    read_only: bool = False
    index_path: Path = field(init=False)
    log_path: Path = field(init=False)

    def __post_init__(self) -> None:
        self.index_path = self.root / "itineraries.json"
        self.log_path = self.root / "itineraries_log.jsonl"

    def load(self) -> dict[str, Any]:
        default = {"itineraries": {}, "history": []}
        if not self.index_path.exists():
            return default
        try:
            payload = json.loads(self.index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return default
        if not isinstance(payload, dict):
            return default
        payload.setdefault("itineraries", {})
        payload.setdefault("history", [])
        return payload

    def save(self, payload: dict[str, Any]) -> None:
        if self.read_only:
            raise RuntimeError("Itinerary storage is read-only in this mode.")
        self.root.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self.index_path, payload)
        append_jsonl(
            self.log_path,
            {
                "saved_at": _now_iso(),
                "records": payload,
            },
        )

    def create_itinerary(
        self,
        *,
        actor: str,
        room: str,
        title: str,
        topic: str,
        source_request: str,
        summary: str,
        segments: list[dict[str, Any]],
    ) -> dict[str, Any]:
        now = _now_iso()
        itinerary_id = str(uuid.uuid4())
        record = {
            "itinerary_id": itinerary_id,
            "object_kind": "itinerary",
            "actor": actor.strip() or "Chris",
            "room": room.strip() or "office",
            "title": title.strip() or "Itinerary",
            "topic": topic.strip(),
            "source_request": source_request.strip(),
            "status": "created",
            "created_at": now,
            "updated_at": now,
            "summary": summary.strip(),
            "segments": list(segments),
            "truth_mode": "local_itinerary_scaffold_only",
            "live_calendar_used": False,
            "live_maps_used": False,
            "live_booking_used": False,
        }
        payload = self.load()
        itineraries = dict(payload.get("itineraries", {}))
        history = list(payload.get("history", []))
        itineraries[itinerary_id] = record
        history.append(
            {
                "event": "itinerary-created",
                "itinerary_id": itinerary_id,
                "title": record["title"],
                "topic": record["topic"],
                "actor": record["actor"],
                "created_at": now,
            }
        )
        payload["itineraries"] = itineraries
        payload["history"] = history[-200:]
        self.save(payload)
        return record

    def get_itinerary(self, itinerary_id: str) -> dict[str, Any] | None:
        payload = self.load()
        record = payload.get("itineraries", {}).get(itinerary_id)
        return dict(record) if isinstance(record, dict) else None


_DIRECT_ITINERARY_PATTERNS = (
    re.compile(r"^make me an itinerary(?:\s+(?:for|on|about))?\s+(?P<topic>.+?)\.?$", re.IGNORECASE),
    re.compile(r"^create a trip itinerary(?:\s+(?:for|on|about))?\s+(?P<topic>.+?)\.?$", re.IGNORECASE),
    re.compile(r"^build a day plan(?:\s+(?:for|on|about))?\s+(?P<topic>.+?)\.?$", re.IGNORECASE),
    re.compile(r"^put together an agenda(?:\s+(?:for|on|about))?\s+(?P<topic>.+?)\.?$", re.IGNORECASE),
)
_DIRECT_ITINERARY_STARTERS = (
    "make me an itinerary",
    "create a trip itinerary",
    "build a day plan",
    "put together an agenda",
)


def is_direct_itinerary_request(request: str) -> bool:
    lowered = " ".join(str(request or "").strip().split()).lower()
    return any(lowered.startswith(prefix) for prefix in _DIRECT_ITINERARY_STARTERS)


def extract_itinerary_topic(request: str) -> str:
    cleaned = " ".join(str(request or "").strip().split())
    for pattern in _DIRECT_ITINERARY_PATTERNS:
        matched = pattern.match(cleaned)
        if not matched:
            continue
        return str(matched.group("topic") or "").strip().rstrip(".?!")
    return ""


def _title(topic: str) -> str:
    cleaned = str(topic or "").strip().rstrip(".")
    if not cleaned:
        return "Itinerary"
    return f"Itinerary for {cleaned}"


def _summary(topic: str) -> str:
    cleaned = str(topic or "").strip()
    return (
        f"This itinerary is a local scaffold for {cleaned}. "
        "It does not claim live calendar, routing, or booking proof."
    )


def _segments(topic: str) -> list[dict[str, Any]]:
    lowered = str(topic or "").strip().lower()
    if "campout" in lowered or "scout" in lowered:
        items = [
            ("prep", "Prep and load-out"),
            ("departure", "Departure and arrival window"),
            ("core", "Main campout blocks and duties"),
            ("close", "Pack-out and return"),
        ]
    elif "retirement workshop" in lowered:
        items = [
            ("setup", "Room setup and material check"),
            ("open", "Opening frame and goals"),
            ("core", "Workshop working blocks"),
            ("close", "Wrap-up and next steps"),
        ]
    elif "saturday" in lowered or "day plan" in lowered:
        items = [
            ("morning", "Morning anchor block"),
            ("midday", "Midday work or outing block"),
            ("afternoon", "Afternoon flex block"),
            ("evening", "Evening closeout block"),
        ]
    else:
        items = [
            ("start", "Start block"),
            ("middle", "Main middle block"),
            ("buffer", "Buffer or transition block"),
            ("finish", "Finish block"),
        ]
    return [
        {
            "segment_id": segment_id,
            "label": label,
            "notes": "",
        }
        for segment_id, label in items
    ]


def build_direct_itinerary_response(
    store: ItineraryStore,
    *,
    actor: str,
    room: str,
    request: str,
) -> dict[str, Any] | None:
    if not is_direct_itinerary_request(request):
        return None
    topic = extract_itinerary_topic(request)
    if not topic:
        return {
            "output_text": "I can do that. What is the itinerary for?",
            "created_itinerary": None,
        }
    created = store.create_itinerary(
        actor=actor,
        room=room,
        title=_title(topic),
        topic=topic,
        source_request=request,
        summary=_summary(topic),
        segments=_segments(topic),
    )
    return {
        "output_text": (
            f"I made an itinerary for {topic}. "
            "It is a bounded local itinerary scaffold, not a claim of live calendar, routing, or booking proof."
        ),
        "created_itinerary": created,
    }
