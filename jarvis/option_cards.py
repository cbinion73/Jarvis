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
class OptionCardStore:
    root: Path
    read_only: bool = False
    index_path: Path = field(init=False)
    log_path: Path = field(init=False)

    def __post_init__(self) -> None:
        self.index_path = self.root / "option_cards.json"
        self.log_path = self.root / "option_cards_log.jsonl"

    def load(self) -> dict[str, Any]:
        default = {"option_cards": {}, "history": []}
        if not self.index_path.exists():
            return default
        try:
            payload = json.loads(self.index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return default
        if not isinstance(payload, dict):
            return default
        payload.setdefault("option_cards", {})
        payload.setdefault("history", [])
        return payload

    def save(self, payload: dict[str, Any]) -> None:
        if self.read_only:
            raise RuntimeError("Option-card storage is read-only in this mode.")
        self.root.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self.index_path, payload)
        append_jsonl(
            self.log_path,
            {
                "saved_at": _now_iso(),
                "records": payload,
            },
        )

    def create_option_card(
        self,
        *,
        actor: str,
        room: str,
        title: str,
        topic: str,
        source_request: str,
        summary: str,
        options: list[dict[str, Any]],
        framing_note: str,
    ) -> dict[str, Any]:
        now = _now_iso()
        option_card_id = str(uuid.uuid4())
        record = {
            "option_card_id": option_card_id,
            "object_kind": "option_card",
            "actor": actor.strip() or "Chris",
            "room": room.strip() or "office",
            "title": title.strip() or "Option card",
            "topic": topic.strip(),
            "source_request": source_request.strip(),
            "status": "created",
            "created_at": now,
            "updated_at": now,
            "summary": summary.strip(),
            "options": list(options),
            "framing_note": framing_note.strip(),
            "truth_mode": "local_option_card_scaffold_only",
            "live_discovery_used": False,
            "validated_ranking_used": False,
            "live_execution_used": False,
        }
        payload = self.load()
        cards = dict(payload.get("option_cards", {}))
        history = list(payload.get("history", []))
        cards[option_card_id] = record
        history.append(
            {
                "event": "option-card-created",
                "option_card_id": option_card_id,
                "title": record["title"],
                "topic": record["topic"],
                "actor": record["actor"],
                "created_at": now,
            }
        )
        payload["option_cards"] = cards
        payload["history"] = history[-200:]
        self.save(payload)
        return record

    def get_option_card(self, option_card_id: str) -> dict[str, Any] | None:
        payload = self.load()
        record = payload.get("option_cards", {}).get(option_card_id)
        return dict(record) if isinstance(record, dict) else None


_DIRECT_OPTION_CARD_PATTERNS = (
    re.compile(r"^lay out my options(?:\s+(?:for|on))?\s+(?P<topic>.+?)\.?$", re.IGNORECASE),
    re.compile(r"^give me the options(?:\s+(?:for|on))?\s+(?P<topic>.+?)\.?$", re.IGNORECASE),
    re.compile(r"^make me option cards(?:\s+(?:for|on))?\s+(?P<topic>.+?)\.?$", re.IGNORECASE),
    re.compile(r"^show me the options(?:\s+(?:for|on))?\s+(?P<topic>.+?)\.?$", re.IGNORECASE),
)
_DIRECT_OPTION_CARD_STARTERS = (
    "lay out my options",
    "give me the options",
    "make me option cards",
    "show me the options",
)


def is_direct_option_card_request(request: str) -> bool:
    lowered = " ".join(str(request or "").strip().split()).lower()
    return any(lowered.startswith(prefix) for prefix in _DIRECT_OPTION_CARD_STARTERS)


def extract_option_card_topic(request: str) -> str:
    cleaned = " ".join(str(request or "").strip().split())
    for pattern in _DIRECT_OPTION_CARD_PATTERNS:
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
        return "Option card"
    return f"Option card for {cleaned}"


def _summary(topic: str) -> str:
    cleaned = str(topic or "").strip()
    return (
        f"This option card is a local option-shaping scaffold for {cleaned}. "
        "It does not claim live discovery, validated ranking, or execution."
    )


def _option_bundle(topic: str) -> tuple[list[dict[str, Any]], str]:
    lowered = str(topic or "").strip().lower()
    if "retirement workshop" in lowered:
        options = [
            {"option_id": "option-1", "label": "Simplify the workshop scope", "notes": "Cut the workshop to the one outcome that matters most."},
            {"option_id": "option-2", "label": "Deepen the prep", "notes": "Gather the missing constraints before committing to structure."},
            {"option_id": "option-3", "label": "Stage the workshop", "notes": "Split discovery from decision so the day is less overloaded."},
        ]
        note = "These are bounded local option shapes, not a ranked or validated recommendation set."
        return options, note
    if "scout trailer" in lowered:
        options = [
            {"option_id": "option-1", "label": "Protection-first storage", "notes": "Favor weather and theft protection first."},
            {"option_id": "option-2", "label": "Access-first storage", "notes": "Favor convenience if frequent access matters most."},
            {"option_id": "option-3", "label": "Balanced compromise", "notes": "Trade a little convenience for lower exposure and manageable cost."},
        ]
        note = "These options frame the tradeoff space locally; they do not claim live discovery of sites or validated ranking."
        return options, note
    if "passive income" in lowered:
        options = [
            {"option_id": "option-1", "label": "Durable low-maintenance lane", "notes": "Prefer sustainability over maximum upside."},
            {"option_id": "option-2", "label": "Higher-upside active lane", "notes": "Requires more attention and tolerance for volatility."},
            {"option_id": "option-3", "label": "Staged hybrid path", "notes": "Start durable, then add the second lane only after stability."},
        ]
        note = "These are local option cards for shaping the decision, not live-ranked investment choices."
        return options, note
    if "pool robot" in lowered:
        options = [
            {"option_id": "option-1", "label": "Reliability-first pick", "notes": "Favor lower friction and dependable use."},
            {"option_id": "option-2", "label": "Feature-rich pick", "notes": "Favor more capability if upkeep tradeoffs are acceptable."},
            {"option_id": "option-3", "label": "Value-first pick", "notes": "Favor price discipline if the essentials are covered."},
        ]
        note = "These option cards shape the choice locally; they do not claim live market discovery or validated ranking."
        return options, note
    cleaned = str(topic or "").strip()
    options = [
        {"option_id": "option-1", "label": "Conservative path", "notes": f"Lower-risk option shape for {cleaned}."},
        {"option_id": "option-2", "label": "Balanced path", "notes": f"Middle-ground option shape for {cleaned}."},
        {"option_id": "option-3", "label": "Aggressive path", "notes": f"Higher-upside but higher-risk option shape for {cleaned}."},
    ]
    note = f"These option cards are a bounded local framing for {cleaned}, not a claim of live discovery or validated ranking."
    return options, note


def build_direct_option_card_response(
    store: OptionCardStore,
    *,
    actor: str,
    room: str,
    request: str,
) -> dict[str, Any] | None:
    if not is_direct_option_card_request(request):
        return None
    topic = extract_option_card_topic(request)
    if not topic:
        return {
            "output_text": "I can do that. What should the option card cover?",
            "created_option_card": None,
        }
    options, framing_note = _option_bundle(topic)
    created = store.create_option_card(
        actor=actor,
        room=room,
        title=_title(topic),
        topic=topic,
        source_request=request,
        summary=_summary(topic),
        options=options,
        framing_note=framing_note,
    )
    return {
        "output_text": (
            f"I made an option card for {topic}. "
            "It is a bounded local option scaffold, not a claim of live discovery, validated ranking, or execution."
        ),
        "created_option_card": created,
    }
