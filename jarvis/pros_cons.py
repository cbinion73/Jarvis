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
class ProsConsStore:
    root: Path
    read_only: bool = False
    index_path: Path = field(init=False)
    log_path: Path = field(init=False)

    def __post_init__(self) -> None:
        self.index_path = self.root / "pros_cons.json"
        self.log_path = self.root / "pros_cons_log.jsonl"

    def load(self) -> dict[str, Any]:
        default = {"pros_cons": {}, "history": []}
        if not self.index_path.exists():
            return default
        try:
            payload = json.loads(self.index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return default
        if not isinstance(payload, dict):
            return default
        payload.setdefault("pros_cons", {})
        payload.setdefault("history", [])
        return payload

    def save(self, payload: dict[str, Any]) -> None:
        if self.read_only:
            raise RuntimeError("Pros-cons storage is read-only in this mode.")
        self.root.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self.index_path, payload)
        append_jsonl(
            self.log_path,
            {
                "saved_at": _now_iso(),
                "records": payload,
            },
        )

    def create_sheet(
        self,
        *,
        actor: str,
        room: str,
        title: str,
        topic: str,
        source_request: str,
        summary: str,
        pros: list[str],
        cons: list[str],
        framing_note: str,
    ) -> dict[str, Any]:
        now = _now_iso()
        pros_cons_id = str(uuid.uuid4())
        record = {
            "pros_cons_id": pros_cons_id,
            "object_kind": "pros_cons",
            "actor": actor.strip() or "Chris",
            "room": room.strip() or "office",
            "title": title.strip() or "Pros and cons",
            "topic": topic.strip(),
            "source_request": source_request.strip(),
            "status": "created",
            "created_at": now,
            "updated_at": now,
            "summary": summary.strip(),
            "pros": list(pros),
            "cons": list(cons),
            "framing_note": framing_note.strip(),
            "truth_mode": "local_pros_cons_scaffold_only",
            "live_discovery_used": False,
            "validated_analysis_used": False,
            "live_execution_used": False,
        }
        payload = self.load()
        sheets = dict(payload.get("pros_cons", {}))
        history = list(payload.get("history", []))
        sheets[pros_cons_id] = record
        history.append(
            {
                "event": "pros-cons-created",
                "pros_cons_id": pros_cons_id,
                "title": record["title"],
                "topic": record["topic"],
                "actor": record["actor"],
                "created_at": now,
            }
        )
        payload["pros_cons"] = sheets
        payload["history"] = history[-200:]
        self.save(payload)
        return record

    def get_sheet(self, pros_cons_id: str) -> dict[str, Any] | None:
        payload = self.load()
        record = payload.get("pros_cons", {}).get(pros_cons_id)
        return dict(record) if isinstance(record, dict) else None


_DIRECT_PROS_CONS_PATTERNS = (
    re.compile(r"^give me the pros and cons(?:\s+(?:for|of|on))?\s+(?P<topic>.+?)\.?$", re.IGNORECASE),
    re.compile(r"^lay out the tradeoffs(?:\s+(?:for|of|on))?\s+(?P<topic>.+?)\.?$", re.IGNORECASE),
    re.compile(r"^make me a pros and cons sheet(?:\s+(?:for|on))?\s+(?P<topic>.+?)\.?$", re.IGNORECASE),
    re.compile(r"^show me the tradeoffs(?:\s+(?:for|of|on))?\s+(?P<topic>.+?)\.?$", re.IGNORECASE),
)
_DIRECT_PROS_CONS_STARTERS = (
    "give me the pros and cons",
    "lay out the tradeoffs",
    "make me a pros and cons sheet",
    "show me the tradeoffs",
)


def is_direct_pros_cons_request(request: str) -> bool:
    lowered = " ".join(str(request or "").strip().split()).lower()
    return any(lowered.startswith(prefix) for prefix in _DIRECT_PROS_CONS_STARTERS)


def extract_pros_cons_topic(request: str) -> str:
    cleaned = " ".join(str(request or "").strip().split())
    for pattern in _DIRECT_PROS_CONS_PATTERNS:
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
        return "Pros and cons"
    return f"Pros and cons for {cleaned}"


def _summary(topic: str) -> str:
    cleaned = str(topic or "").strip()
    return (
        f"This pros-cons sheet is a local tradeoff scaffold for {cleaned}. "
        "It does not claim live discovery, validated analysis, or execution."
    )


def _bundle(topic: str) -> tuple[list[str], list[str], str]:
    lowered = str(topic or "").strip().lower()
    if "retirement workshop" in lowered:
        pros = [
            "Lets you see the upside of simplifying versus deepening the workshop.",
            "Makes tradeoffs visible before overcommitting to one structure.",
            "Keeps the decision grounded in what the workshop actually needs to do.",
        ]
        cons = [
            "Still depends on missing constraints you may not have surfaced yet.",
            "Can look cleaner than reality if the outcome is still vague.",
            "Does not validate the workshop path with outside proof on its own.",
        ]
        note = "This is a bounded local tradeoff framing, not a validated workshop analysis."
        return pros, cons, note
    if "scout trailer" in lowered:
        pros = [
            "Makes the weather, theft, and access tradeoffs easier to compare.",
            "Helps separate convenience from true risk reduction.",
            "Keeps storage choices from collapsing into a single price-only decision.",
        ]
        cons = [
            "Does not discover or validate live storage options.",
            "Can miss physical constraints if trailer dimensions are still unknown.",
            "Needs site-specific checks before a final decision is trustworthy.",
        ]
        note = "This is a local tradeoff scaffold, not a validated storage analysis."
        return pros, cons, note
    if "passive income" in lowered:
        pros = [
            "Surfaces the tradeoff between sustainability and upside clearly.",
            "Helps compare maintenance burden against expected return shape.",
            "Keeps the conversation from drifting into vague opportunity language.",
        ]
        cons = [
            "Does not validate any income lane with live market proof.",
            "Can hide how much execution discipline each lane really needs.",
            "Still depends on your risk tolerance and capital, which may be underspecified.",
        ]
        note = "This is a local pros-cons framing, not validated investment analysis."
        return pros, cons, note
    if "pool robot" in lowered:
        pros = [
            "Makes reliability, friction, and price tradeoffs easier to see.",
            "Helps separate feature appetite from real everyday value.",
            "Keeps the choice from becoming pure gadget shopping.",
        ]
        cons = [
            "Does not validate models or prices with live market data.",
            "Can overgeneralize if the pool setup is still vague.",
            "Needs real candidate narrowing before a final pick is solid.",
        ]
        note = "This is a bounded local tradeoff sheet, not a validated market analysis."
        return pros, cons, note
    cleaned = str(topic or "").strip()
    pros = [
        f"Clarifies the upside paths inside {cleaned}.",
        f"Helps compare tradeoffs inside {cleaned} without collapsing them into one vague take.",
        f"Gives you a cleaner frame for deciding what matters most in {cleaned}.",
    ]
    cons = [
        f"Does not validate {cleaned} with live discovery or proof.",
        f"Can still miss the key constraint if {cleaned} is underspecified.",
        f"Needs a sharper decision standard before {cleaned} becomes a final call.",
    ]
    note = f"This is a bounded local pros-cons scaffold for {cleaned}, not validated analysis."
    return pros, cons, note


def build_direct_pros_cons_response(
    store: ProsConsStore,
    *,
    actor: str,
    room: str,
    request: str,
) -> dict[str, Any] | None:
    if not is_direct_pros_cons_request(request):
        return None
    topic = extract_pros_cons_topic(request)
    if not topic:
        return {
            "output_text": "I can do that. What should the pros and cons cover?",
            "created_pros_cons": None,
        }
    pros, cons, note = _bundle(topic)
    created = store.create_sheet(
        actor=actor,
        room=room,
        title=_title(topic),
        topic=topic,
        source_request=request,
        summary=_summary(topic),
        pros=pros,
        cons=cons,
        framing_note=note,
    )
    return {
        "output_text": (
            f"I made a pros and cons sheet for {topic}. "
            "It is a bounded local tradeoff scaffold, not a claim of live discovery, validated analysis, or execution."
        ),
        "created_pros_cons": created,
    }
