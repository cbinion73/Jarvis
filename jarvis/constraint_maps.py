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
class ConstraintMapStore:
    root: Path
    read_only: bool = False
    index_path: Path = field(init=False)
    log_path: Path = field(init=False)

    def __post_init__(self) -> None:
        self.index_path = self.root / "constraint_maps.json"
        self.log_path = self.root / "constraint_maps_log.jsonl"

    def load(self) -> dict[str, Any]:
        default = {"constraint_maps": {}, "history": []}
        if not self.index_path.exists():
            return default
        try:
            payload = json.loads(self.index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return default
        if not isinstance(payload, dict):
            return default
        payload.setdefault("constraint_maps", {})
        payload.setdefault("history", [])
        return payload

    def save(self, payload: dict[str, Any]) -> None:
        if self.read_only:
            raise RuntimeError("Constraint-map storage is read-only in this mode.")
        self.root.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self.index_path, payload)
        append_jsonl(
            self.log_path,
            {
                "saved_at": _now_iso(),
                "records": payload,
            },
        )

    def create_map(
        self,
        *,
        actor: str,
        room: str,
        title: str,
        topic: str,
        source_request: str,
        summary: str,
        constraints: list[dict[str, Any]],
        framing_note: str,
    ) -> dict[str, Any]:
        now = _now_iso()
        constraint_map_id = str(uuid.uuid4())
        record = {
            "constraint_map_id": constraint_map_id,
            "object_kind": "constraint_map",
            "actor": actor.strip() or "Chris",
            "room": room.strip() or "office",
            "title": title.strip() or "Constraint map",
            "topic": topic.strip(),
            "source_request": source_request.strip(),
            "status": "created",
            "created_at": now,
            "updated_at": now,
            "summary": summary.strip(),
            "constraints": list(constraints),
            "framing_note": framing_note.strip(),
            "truth_mode": "local_constraint_map_scaffold_only",
            "live_discovery_used": False,
            "external_policy_lookup_used": False,
            "validated_proof_used": False,
        }
        payload = self.load()
        maps = dict(payload.get("constraint_maps", {}))
        history = list(payload.get("history", []))
        maps[constraint_map_id] = record
        history.append(
            {
                "event": "constraint-map-created",
                "constraint_map_id": constraint_map_id,
                "title": record["title"],
                "topic": record["topic"],
                "actor": record["actor"],
                "created_at": now,
            }
        )
        payload["constraint_maps"] = maps
        payload["history"] = history[-200:]
        self.save(payload)
        return record

    def get_map(self, constraint_map_id: str) -> dict[str, Any] | None:
        payload = self.load()
        record = payload.get("constraint_maps", {}).get(constraint_map_id)
        return dict(record) if isinstance(record, dict) else None


_DIRECT_CONSTRAINT_MAP_PATTERNS = (
    re.compile(r"^map the constraints(?:\s+(?:for|on))?\s+(?P<topic>.+?)\.?$", re.IGNORECASE),
    re.compile(r"^what constraints am i working with(?:\s+(?:for|on))?\s+(?P<topic>.+?)\?\s*make me the map\.?$", re.IGNORECASE),
    re.compile(r"^lay out the constraints(?:\s+(?:for|on))?\s+(?P<topic>.+?)\.?$", re.IGNORECASE),
    re.compile(r"^give me a constraint map(?:\s+(?:for|on))?\s+(?P<topic>.+?)\.?$", re.IGNORECASE),
)
_DIRECT_CONSTRAINT_MAP_STARTERS = (
    "map the constraints",
    "what constraints am i working with",
    "lay out the constraints",
    "give me a constraint map",
)


def is_direct_constraint_map_request(request: str) -> bool:
    lowered = " ".join(str(request or "").strip().split()).lower()
    return any(lowered.startswith(prefix) for prefix in _DIRECT_CONSTRAINT_MAP_STARTERS)


def extract_constraint_map_topic(request: str) -> str:
    cleaned = " ".join(str(request or "").strip().split())
    for pattern in _DIRECT_CONSTRAINT_MAP_PATTERNS:
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
        return "Constraint map"
    return f"Constraint map for {cleaned}"


def _summary(topic: str) -> str:
    cleaned = str(topic or "").strip()
    return (
        f"This constraint map is a local constraint scaffold for {cleaned}. "
        "It does not claim live discovery, external policy lookup, or validated proof."
    )


def _constraint_bundle(topic: str) -> tuple[list[dict[str, Any]], str]:
    lowered = str(topic or "").strip().lower()
    if "retirement workshop" in lowered:
        constraints = [
            {"constraint_id": "constraint-1", "label": "Outcome clarity", "notes": "The workshop needs one clear result, not three competing ones."},
            {"constraint_id": "constraint-2", "label": "Time and attention", "notes": "Too much scope will overload the day fast."},
            {"constraint_id": "constraint-3", "label": "Decision readiness", "notes": "Missing inputs may cap how far the workshop can realistically go."},
        ]
        note = "This is a bounded local constraint framing, not a live policy or proof-backed workshop assessment."
        return constraints, note
    if "scout trailer" in lowered:
        constraints = [
            {"constraint_id": "constraint-1", "label": "Weather exposure", "notes": "Protection requirements limit the viable storage shapes."},
            {"constraint_id": "constraint-2", "label": "Access practicality", "notes": "The best-protected option can still fail if access becomes a constant hassle."},
            {"constraint_id": "constraint-3", "label": "Security and theft risk", "notes": "Security needs may eliminate cheaper but weaker setups."},
        ]
        note = "This is a bounded local constraint map, not live site discovery or validated policy retrieval."
        return constraints, note
    if "passive income" in lowered:
        constraints = [
            {"constraint_id": "constraint-1", "label": "Capital available", "notes": "Some lanes are eliminated if the real starting capital is limited."},
            {"constraint_id": "constraint-2", "label": "Maintenance capacity", "notes": "The lane has to fit your actual ongoing attention budget."},
            {"constraint_id": "constraint-3", "label": "Risk tolerance", "notes": "A fragile risk posture rules out some higher-upside options."},
        ]
        note = "This is a bounded local constraint map, not validated market or policy analysis."
        return constraints, note
    if "pool robot" in lowered:
        constraints = [
            {"constraint_id": "constraint-1", "label": "Pool setup", "notes": "Shape, size, and surface can narrow the viable robot classes."},
            {"constraint_id": "constraint-2", "label": "Budget ceiling", "notes": "Price range may eliminate feature-heavy options immediately."},
            {"constraint_id": "constraint-3", "label": "Maintenance tolerance", "notes": "A high-maintenance robot can be the wrong choice even if it looks stronger on paper."},
        ]
        note = "This is a bounded local constraint map, not live market discovery or validated product proof."
        return constraints, note
    cleaned = str(topic or "").strip()
    constraints = [
        {"constraint_id": "constraint-1", "label": "Core limit", "notes": f"There is likely one main limiting factor inside {cleaned} that should drive the frame."},
        {"constraint_id": "constraint-2", "label": "Resource boundary", "notes": f"Time, money, attention, or energy likely caps the real moves inside {cleaned}."},
        {"constraint_id": "constraint-3", "label": "Decision condition", "notes": f"A missing condition or requirement may block a clean decision on {cleaned}."},
    ]
    note = f"This is a bounded local constraint map for {cleaned}, not live discovery, external policy lookup, or validated proof."
    return constraints, note


def build_direct_constraint_map_response(
    store: ConstraintMapStore,
    *,
    actor: str,
    room: str,
    request: str,
) -> dict[str, Any] | None:
    if not is_direct_constraint_map_request(request):
        return None
    topic = extract_constraint_map_topic(request)
    if not topic:
        return {
            "output_text": "I can do that. What should the constraint map cover?",
            "created_constraint_map": None,
        }
    constraints, note = _constraint_bundle(topic)
    created = store.create_map(
        actor=actor,
        room=room,
        title=_title(topic),
        topic=topic,
        source_request=request,
        summary=_summary(topic),
        constraints=constraints,
        framing_note=note,
    )
    return {
        "output_text": (
            f"I made a constraint map for {topic}. "
            "It is a bounded local constraint scaffold, not a claim of live discovery, external policy lookup, or validated proof."
        ),
        "created_constraint_map": created,
    }
