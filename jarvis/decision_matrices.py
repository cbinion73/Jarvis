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
class DecisionMatrixStore:
    root: Path
    read_only: bool = False
    index_path: Path = field(init=False)
    log_path: Path = field(init=False)

    def __post_init__(self) -> None:
        self.index_path = self.root / "decision_matrices.json"
        self.log_path = self.root / "decision_matrices_log.jsonl"

    def load(self) -> dict[str, Any]:
        default = {"decision_matrices": {}, "history": []}
        if not self.index_path.exists():
            return default
        try:
            payload = json.loads(self.index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return default
        if not isinstance(payload, dict):
            return default
        payload.setdefault("decision_matrices", {})
        payload.setdefault("history", [])
        return payload

    def save(self, payload: dict[str, Any]) -> None:
        if self.read_only:
            raise RuntimeError("Decision matrix storage is read-only in this mode.")
        self.root.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self.index_path, payload)
        append_jsonl(
            self.log_path,
            {
                "saved_at": _now_iso(),
                "records": payload,
            },
        )

    def create_matrix(
        self,
        *,
        actor: str,
        room: str,
        title: str,
        topic: str,
        source_request: str,
        summary: str,
        criteria: list[str],
        options: list[dict[str, Any]],
        recommendation_note: str,
    ) -> dict[str, Any]:
        now = _now_iso()
        matrix_id = str(uuid.uuid4())
        record = {
            "matrix_id": matrix_id,
            "object_kind": "decision_matrix",
            "actor": actor.strip() or "Chris",
            "room": room.strip() or "office",
            "title": title.strip() or "Decision matrix",
            "topic": topic.strip(),
            "source_request": source_request.strip(),
            "status": "created",
            "created_at": now,
            "updated_at": now,
            "summary": summary.strip(),
            "criteria": list(criteria),
            "options": list(options),
            "recommendation_note": recommendation_note.strip(),
            "truth_mode": "local_matrix_scaffold_only",
            "live_retrieval_used": False,
        }
        payload = self.load()
        matrices = dict(payload.get("decision_matrices", {}))
        history = list(payload.get("history", []))
        matrices[matrix_id] = record
        history.append(
            {
                "event": "decision-matrix-created",
                "matrix_id": matrix_id,
                "title": record["title"],
                "topic": record["topic"],
                "actor": record["actor"],
                "created_at": now,
            }
        )
        payload["decision_matrices"] = matrices
        payload["history"] = history[-200:]
        self.save(payload)
        return record

    def get_matrix(self, matrix_id: str) -> dict[str, Any] | None:
        payload = self.load()
        record = payload.get("decision_matrices", {}).get(matrix_id)
        return dict(record) if isinstance(record, dict) else None


_DIRECT_MATRIX_PATTERNS = (
    re.compile(r"^compare\s+(?P<topic>.+?)\.?$", re.IGNORECASE),
    re.compile(r"^help me choose(?:\s+(?:between|among))?\s+(?P<topic>.+?)\.?$", re.IGNORECASE),
    re.compile(r"^make me a decision matrix(?:\s+(?:for|on|about))?\s+(?P<topic>.+?)\.?$", re.IGNORECASE),
    re.compile(r"^create a decision matrix(?:\s+(?:for|on|about))?\s+(?P<topic>.+?)\.?$", re.IGNORECASE),
)
_DIRECT_MATRIX_STARTERS = (
    "compare ",
    "help me choose",
    "make me a decision matrix",
    "create a decision matrix",
)


def is_direct_decision_matrix_request(request: str) -> bool:
    lowered = " ".join(str(request or "").strip().split()).lower()
    if re.match(r"^(?:compare|help me choose)(?:[\s.?!]|$)", lowered):
        return True
    return any(lowered.startswith(prefix) for prefix in _DIRECT_MATRIX_STARTERS)


def extract_decision_matrix_topic(request: str) -> str:
    cleaned = " ".join(str(request or "").strip().split())
    for pattern in _DIRECT_MATRIX_PATTERNS:
        matched = pattern.match(cleaned)
        if not matched:
            continue
        return str(matched.group("topic") or "").strip().rstrip(".?!")
    return ""


def _title(topic: str) -> str:
    cleaned = str(topic or "").strip().rstrip(".")
    if not cleaned:
        return "Decision matrix"
    return f"Decision matrix for {cleaned}"


def _criteria_and_note(topic: str) -> tuple[list[str], str]:
    lowered = str(topic or "").strip().lower()
    if "pool robot" in lowered:
        return (
            ["cleaning performance", "maintenance friction", "reliability", "price"],
            "Use the matrix to compare the same 2 or 3 robots on cleaning performance, upkeep friction, and price before you choose.",
        )
    if "retirement communit" in lowered:
        return (
            ["proximity", "monthly cost", "care fit", "day-to-day feel"],
            "Use the matrix to hold the communities to the same distance, cost, and care-fit standard before you decide.",
        )
    if "passive income" in lowered:
        return (
            ["capital required", "maintenance load", "risk", "time to cash flow"],
            "Use the matrix to compare income ideas on upkeep burden and risk, not just upside.",
        )
    if "trailer" in lowered and "storage" in lowered:
        return (
            ["weather protection", "access", "theft risk", "cost"],
            "Use the matrix to compare storage options on protection, access, and theft risk before you commit.",
        )
    return (
        ["fit", "cost", "risk", "effort"],
        "Use the matrix to force the options through the same criteria instead of deciding from vibe alone.",
    )


def _option_slots(topic: str) -> list[dict[str, Any]]:
    lowered = str(topic or "").strip().lower()
    if "between two" in lowered or "these two" in lowered or "two " in lowered:
        labels = ["Option 1", "Option 2"]
    else:
        labels = ["Option 1", "Option 2", "Option 3"]
    return [
        {
            "option_id": f"option-{index + 1}",
            "label": label,
            "notes": "",
        }
        for index, label in enumerate(labels)
    ]


def _summary(topic: str) -> str:
    cleaned = str(topic or "").strip()
    return (
        f"This matrix is a local decision scaffold for {cleaned}. "
        "It does not claim live external proof or completed option discovery."
    )


def build_direct_decision_matrix_response(
    store: DecisionMatrixStore,
    *,
    actor: str,
    room: str,
    request: str,
) -> dict[str, Any] | None:
    if not is_direct_decision_matrix_request(request):
        return None
    topic = extract_decision_matrix_topic(request)
    if not topic:
        return {
            "output_text": "I can do that. What do you want compared?",
            "created_decision_matrix": None,
        }
    criteria, recommendation_note = _criteria_and_note(topic)
    created = store.create_matrix(
        actor=actor,
        room=room,
        title=_title(topic),
        topic=topic,
        source_request=request,
        summary=_summary(topic),
        criteria=criteria,
        options=_option_slots(topic),
        recommendation_note=recommendation_note,
    )
    return {
        "output_text": (
            f"I made a decision matrix for {topic}. "
            "It is a bounded local comparison scaffold, not a claim of live external proof."
        ),
        "created_decision_matrix": created,
    }
