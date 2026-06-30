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
class RecommendationStore:
    root: Path
    read_only: bool = False
    index_path: Path = field(init=False)
    log_path: Path = field(init=False)

    def __post_init__(self) -> None:
        self.index_path = self.root / "recommendations.json"
        self.log_path = self.root / "recommendations_log.jsonl"

    def load(self) -> dict[str, Any]:
        default = {"recommendations": {}, "history": []}
        if not self.index_path.exists():
            return default
        try:
            payload = json.loads(self.index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return default
        if not isinstance(payload, dict):
            return default
        payload.setdefault("recommendations", {})
        payload.setdefault("history", [])
        return payload

    def save(self, payload: dict[str, Any]) -> None:
        if self.read_only:
            raise RuntimeError("Recommendation storage is read-only in this mode.")
        self.root.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self.index_path, payload)
        append_jsonl(
            self.log_path,
            {
                "saved_at": _now_iso(),
                "records": payload,
            },
        )

    def create_recommendation(
        self,
        *,
        actor: str,
        room: str,
        title: str,
        topic: str,
        source_request: str,
        recommendation: str,
        rationale: str,
        assumptions: list[str],
        next_steps: list[str],
    ) -> dict[str, Any]:
        now = _now_iso()
        recommendation_id = str(uuid.uuid4())
        record = {
            "recommendation_id": recommendation_id,
            "object_kind": "recommendation",
            "actor": actor.strip() or "Chris",
            "room": room.strip() or "office",
            "title": title.strip() or "Recommendation",
            "topic": topic.strip(),
            "source_request": source_request.strip(),
            "status": "created",
            "created_at": now,
            "updated_at": now,
            "recommendation": recommendation.strip(),
            "rationale": rationale.strip(),
            "assumptions": list(assumptions),
            "next_steps": list(next_steps),
            "truth_mode": "local_heuristic_only",
            "live_retrieval_used": False,
            "linked_research_packet_id": "",
        }
        payload = self.load()
        recommendations = dict(payload.get("recommendations", {}))
        history = list(payload.get("history", []))
        recommendations[recommendation_id] = record
        history.append(
            {
                "event": "recommendation-created",
                "recommendation_id": recommendation_id,
                "title": record["title"],
                "topic": record["topic"],
                "actor": record["actor"],
                "created_at": now,
            }
        )
        payload["recommendations"] = recommendations
        payload["history"] = history[-200:]
        self.save(payload)
        return record

    def get_recommendation(self, recommendation_id: str) -> dict[str, Any] | None:
        payload = self.load()
        record = payload.get("recommendations", {}).get(recommendation_id)
        return dict(record) if isinstance(record, dict) else None


_DIRECT_RECOMMENDATION_PATTERNS = (
    re.compile(r"^recommend\s+(?P<topic>.+?)\.?$", re.IGNORECASE),
    re.compile(r"^give me a recommendation(?:\s+(?:on|for|about))?\s+(?P<topic>.+?)\.?$", re.IGNORECASE),
    re.compile(r"^make me a recommendation(?:\s+(?:on|for|about))?\s+(?P<topic>.+?)\.?$", re.IGNORECASE),
)
_DIRECT_RECOMMENDATION_STARTERS = (
    "recommend ",
    "give me a recommendation",
    "make me a recommendation",
)


def is_direct_recommendation_request(request: str) -> bool:
    lowered = " ".join(str(request or "").strip().split()).lower()
    if re.match(r"^recommend(?:[\s.?!]|$)", lowered):
        return True
    return any(lowered.startswith(prefix) for prefix in _DIRECT_RECOMMENDATION_STARTERS)


def extract_recommendation_topic(request: str) -> str:
    cleaned = " ".join(str(request or "").strip().split())
    for pattern in _DIRECT_RECOMMENDATION_PATTERNS:
        matched = pattern.match(cleaned)
        if not matched:
            continue
        return str(matched.group("topic") or "").strip().rstrip(".?!")
    return ""


def _title(topic: str) -> str:
    cleaned = str(topic or "").strip().rstrip(".")
    if not cleaned:
        return "Recommendation"
    return f"Recommendation for {cleaned}"


def _heuristic_bundle(topic: str) -> tuple[str, str, list[str], list[str]]:
    cleaned = str(topic or "").strip()
    lowered = cleaned.lower()
    if "pool robot" in lowered:
        return (
            "Start with a reliable cordless robot that handles walls well and is easy to clean out after each cycle.",
            "That is a bounded local heuristic based on the usual tradeoff between cleaning performance, maintenance friction, and day-to-day convenience, not a live market ranking.",
            [
                "Pool size and surface were not specified.",
                "This does not claim live price or model comparisons.",
            ],
            [
                "Set the budget ceiling first.",
                "Decide whether wall-climbing matters enough to be a must-have.",
                "Then compare 2 or 3 candidates against cleanup friction and reliability.",
            ],
        )
    if "retirement communit" in lowered:
        return (
            "Start with a proximity-first shortlist of 2 or 3 communities that fit your real distance, budget, and care-level constraints.",
            "That is a bounded local recommendation about how to focus the decision, not a claim that specific communities were live-researched or ranked here.",
            [
                "No live community dataset was pulled in this path.",
                "Budget and care-level priorities were not specified.",
            ],
            [
                "Set the maximum drive distance you actually want.",
                "Name the care level and monthly range that would still feel realistic.",
                "Use those filters before comparing specific communities.",
            ],
        )
    if "scout" in lowered and "trailer" in lowered:
        return (
            "Use a covered, access-controlled trailer setup with weather protection and a simple internal gear-zoning system.",
            "That is a bounded local recommendation based on the usual Scout-trailer tradeoff between access, weather protection, and theft risk, not a live facility search.",
            [
                "No live storage facility search happened here.",
                "Trailer size and storage-site limits were not specified.",
            ],
            [
                "Decide whether weather protection or on-demand access matters more.",
                "Measure the trailer so you do not shortlist the wrong storage type.",
                "Then compare only the options that meet those two constraints.",
            ],
        )
    if "passive income" in lowered:
        return (
            "Start with one durable yield lane you can actually maintain, then pair it with one active asset lane only if you still have real build energy.",
            "That is a bounded local heuristic about focus and sequencing, not a live-validated income ranking or proof of returns.",
            [
                "Risk tolerance and available capital were not specified.",
                "This does not claim live performance data.",
            ],
            [
                "Set the cash, time, and risk you are actually willing to commit.",
                "Pick the one passive lane you would still keep up when life gets busy.",
                "Only add a second lane after the first one is genuinely stable.",
            ],
        )
    return (
        f"Start by narrowing {cleaned} to one decision frame and one main constraint before trying to optimize it.",
        "That is a bounded local recommendation based on the wording of the ask, not a live external finding or proof-backed ranking.",
        [
            "No live external retrieval happened in this path.",
            f"The key constraint for {cleaned} was not specified.",
        ],
        [
            f"Name the main constraint that should drive {cleaned}.",
            f"Pick the top 2 or 3 options or directions worth comparing for {cleaned}.",
            "Then compare them against the same one or two criteria.",
        ],
    )


def build_direct_recommendation_response(
    store: RecommendationStore,
    *,
    actor: str,
    room: str,
    request: str,
) -> dict[str, Any] | None:
    if not is_direct_recommendation_request(request):
        return None
    topic = extract_recommendation_topic(request)
    if not topic:
        return {
            "output_text": "I can do that. What do you want a recommendation on?",
            "created_recommendation": None,
        }
    recommendation, rationale, assumptions, next_steps = _heuristic_bundle(topic)
    created = store.create_recommendation(
        actor=actor,
        room=room,
        title=_title(topic),
        topic=topic,
        source_request=request,
        recommendation=recommendation,
        rationale=rationale,
        assumptions=assumptions,
        next_steps=next_steps,
    )
    return {
        "output_text": (
            f"I made a recommendation for {topic}. "
            "It is a bounded local recommendation, not a claim of live external research."
        ),
        "created_recommendation": created,
    }
