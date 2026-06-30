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
class DecisionMemoStore:
    root: Path
    read_only: bool = False
    index_path: Path = field(init=False)
    log_path: Path = field(init=False)

    def __post_init__(self) -> None:
        self.index_path = self.root / "decision_memos.json"
        self.log_path = self.root / "decision_memos_log.jsonl"

    def load(self) -> dict[str, Any]:
        default = {"decision_memos": {}, "history": []}
        if not self.index_path.exists():
            return default
        try:
            payload = json.loads(self.index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return default
        if not isinstance(payload, dict):
            return default
        payload.setdefault("decision_memos", {})
        payload.setdefault("history", [])
        return payload

    def save(self, payload: dict[str, Any]) -> None:
        if self.read_only:
            raise RuntimeError("Decision-memo storage is read-only in this mode.")
        self.root.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self.index_path, payload)
        append_jsonl(
            self.log_path,
            {
                "saved_at": _now_iso(),
                "records": payload,
            },
        )

    def create_memo(
        self,
        *,
        actor: str,
        room: str,
        title: str,
        topic: str,
        source_request: str,
        recommendation: str,
        rationale: str,
        tradeoffs: list[str],
        assumptions: list[str],
    ) -> dict[str, Any]:
        now = _now_iso()
        memo_id = str(uuid.uuid4())
        record = {
            "memo_id": memo_id,
            "object_kind": "decision_memo",
            "actor": actor.strip() or "Chris",
            "room": room.strip() or "office",
            "title": title.strip() or "Decision memo",
            "topic": topic.strip(),
            "source_request": source_request.strip(),
            "status": "created",
            "created_at": now,
            "updated_at": now,
            "recommendation": recommendation.strip(),
            "rationale": rationale.strip(),
            "tradeoffs": list(tradeoffs),
            "assumptions": list(assumptions),
            "truth_mode": "local_decision_memo_only",
            "live_retrieval_used": False,
            "validated_sourcing_used": False,
            "live_execution_used": False,
        }
        payload = self.load()
        memos = dict(payload.get("decision_memos", {}))
        history = list(payload.get("history", []))
        memos[memo_id] = record
        history.append(
            {
                "event": "decision-memo-created",
                "memo_id": memo_id,
                "title": record["title"],
                "topic": record["topic"],
                "actor": record["actor"],
                "created_at": now,
            }
        )
        payload["decision_memos"] = memos
        payload["history"] = history[-200:]
        self.save(payload)
        return record

    def get_memo(self, memo_id: str) -> dict[str, Any] | None:
        payload = self.load()
        record = payload.get("decision_memos", {}).get(memo_id)
        return dict(record) if isinstance(record, dict) else None


_DIRECT_DECISION_MEMO_PATTERNS = (
    re.compile(r"^make me a decision memo(?:\s+(?:for|on))?\s+(?P<topic>.+?)\.?$", re.IGNORECASE),
    re.compile(r"^give me a memo(?:\s+(?:for|on))?\s+(?P<topic>.+?)\.?$", re.IGNORECASE),
    re.compile(r"^write up the decision(?:\s+(?:for|on))?\s+(?P<topic>.+?)\.?$", re.IGNORECASE),
    re.compile(r"^create a decision memo(?:\s+(?:for|on))?\s+(?P<topic>.+?)\.?$", re.IGNORECASE),
)
_DIRECT_DECISION_MEMO_STARTERS = (
    "make me a decision memo",
    "give me a memo",
    "write up the decision",
    "create a decision memo",
)


def is_direct_decision_memo_request(request: str) -> bool:
    lowered = " ".join(str(request or "").strip().split()).lower()
    return any(lowered.startswith(prefix) for prefix in _DIRECT_DECISION_MEMO_STARTERS)


def extract_decision_memo_topic(request: str) -> str:
    cleaned = " ".join(str(request or "").strip().split())
    for pattern in _DIRECT_DECISION_MEMO_PATTERNS:
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
        return "Decision memo"
    return f"Decision memo for {cleaned}"


def _memo_bundle(topic: str) -> tuple[str, str, list[str], list[str]]:
    cleaned = str(topic or "").strip()
    lowered = cleaned.lower()
    if "pool robot" in lowered:
        return (
            "Narrow to the most reliable low-friction robot rather than chasing maximum feature count.",
            "That recommendation holds the decision on the tradeoff between cleaning performance, maintenance friction, and price, but it does not claim live market validation.",
            [
                "Premium features often add upkeep friction.",
                "Lower price only wins if reliability stays acceptable.",
                "Wall-climbing matters only if the pool shape actually makes it worth paying for.",
            ],
            [
                "No live product comparison or price check happened here.",
                "Pool size and surface were not specified.",
            ],
        )
    if "retirement" in lowered:
        return (
            "Choose the option that best fits the real life you want next, not just the one that looks most optimized on paper.",
            "That recommendation focuses the memo on fit, cost, and day-to-day sustainability, but it does not claim validated external proof or completed scenario modeling.",
            [
                "Lower cost can still be the wrong move if it creates daily friction.",
                "Proximity and support may matter more than headline amenities.",
                "A slower path can still be the stronger choice if it preserves flexibility.",
            ],
            [
                "No live retirement dataset or facility validation was used here.",
                "Your exact financial and lifestyle constraints were not fully specified.",
            ],
        )
    if "scout trailer" in lowered:
        return (
            "Favor the storage option that reduces weather and theft risk without making access so hard that the trailer becomes a constant hassle.",
            "That recommendation lays out the tradeoff between protection, access, and cost, but it does not claim validated site proof or completed execution.",
            [
                "Cheaper storage can become expensive if it increases damage or theft risk.",
                "Best protection is not automatically best if access becomes impractical.",
                "A workable setup needs both physical fit and daily usability.",
            ],
            [
                "No live storage-site verification happened here.",
                "Trailer dimensions and site restrictions were not specified.",
            ],
        )
    if "passive income" in lowered:
        return (
            "Prioritize the lane you can sustain consistently over the one with the most seductive upside story.",
            "That recommendation grounds the memo in maintenance load, risk, and time-to-return tradeoffs, but it does not claim validated external proof of returns.",
            [
                "Higher upside often comes with higher management drag.",
                "A lower-maintenance lane can outperform in real life if you actually stick with it.",
                "Diversifying too early can dilute momentum before one lane is stable.",
            ],
            [
                "No live market or return data was used here.",
                "Risk tolerance, capital, and available time were not fully specified.",
            ],
        )
    return (
        f"Choose the path for {cleaned} that survives contact with your real constraints, not just the one that sounds best in theory.",
        "That recommendation is a bounded local decision memo based on the request wording, not a claim of validated sourcing, live proof, or execution.",
        [
            f"The strongest option for {cleaned} may not be the most ambitious one.",
            f"Tradeoffs for {cleaned} matter more than a single headline advantage.",
            f"The memo should separate confidence from assumptions for {cleaned}.",
        ],
        [
            "No live external validation happened in this path.",
            f"The key constraint for {cleaned} was not fully specified.",
        ],
    )


def build_direct_decision_memo_response(
    store: DecisionMemoStore,
    *,
    actor: str,
    room: str,
    request: str,
) -> dict[str, Any] | None:
    if not is_direct_decision_memo_request(request):
        return None
    topic = extract_decision_memo_topic(request)
    if not topic:
        return {
            "output_text": "I can do that. What should the decision memo cover?",
            "created_decision_memo": None,
        }
    recommendation, rationale, tradeoffs, assumptions = _memo_bundle(topic)
    created = store.create_memo(
        actor=actor,
        room=room,
        title=_title(topic),
        topic=topic,
        source_request=request,
        recommendation=recommendation,
        rationale=rationale,
        tradeoffs=tradeoffs,
        assumptions=assumptions,
    )
    return {
        "output_text": (
            f"I made a decision memo for {topic}. "
            "It is a bounded local decision memo, not a claim of validated sourcing, live proof, or execution."
        ),
        "created_decision_memo": created,
    }
