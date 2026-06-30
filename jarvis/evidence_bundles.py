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
class EvidenceBundleStore:
    root: Path
    read_only: bool = False
    index_path: Path = field(init=False)
    log_path: Path = field(init=False)

    def __post_init__(self) -> None:
        self.index_path = self.root / "evidence_bundles.json"
        self.log_path = self.root / "evidence_bundles_log.jsonl"

    def load(self) -> dict[str, Any]:
        default = {"evidence_bundles": {}, "history": []}
        if not self.index_path.exists():
            return default
        try:
            payload = json.loads(self.index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return default
        if not isinstance(payload, dict):
            return default
        payload.setdefault("evidence_bundles", {})
        payload.setdefault("history", [])
        return payload

    def save(self, payload: dict[str, Any]) -> None:
        if self.read_only:
            raise RuntimeError("Evidence-bundle storage is read-only in this mode.")
        self.root.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self.index_path, payload)
        append_jsonl(
            self.log_path,
            {
                "saved_at": _now_iso(),
                "records": payload,
            },
        )

    def create_bundle(
        self,
        *,
        actor: str,
        room: str,
        title: str,
        topic: str,
        source_request: str,
        summary: str,
        evidence_lines: list[dict[str, Any]],
        open_questions: list[str],
    ) -> dict[str, Any]:
        now = _now_iso()
        bundle_id = str(uuid.uuid4())
        record = {
            "bundle_id": bundle_id,
            "object_kind": "evidence_bundle",
            "actor": actor.strip() or "Chris",
            "room": room.strip() or "office",
            "title": title.strip() or "Evidence bundle",
            "topic": topic.strip(),
            "source_request": source_request.strip(),
            "status": "created",
            "created_at": now,
            "updated_at": now,
            "summary": summary.strip(),
            "evidence_lines": list(evidence_lines),
            "open_questions": list(open_questions),
            "truth_mode": "local_evidence_scaffold_only",
            "live_retrieval_used": False,
            "source_verification_completed": False,
        }
        payload = self.load()
        bundles = dict(payload.get("evidence_bundles", {}))
        history = list(payload.get("history", []))
        bundles[bundle_id] = record
        history.append(
            {
                "event": "evidence-bundle-created",
                "bundle_id": bundle_id,
                "title": record["title"],
                "topic": record["topic"],
                "actor": record["actor"],
                "created_at": now,
            }
        )
        payload["evidence_bundles"] = bundles
        payload["history"] = history[-200:]
        self.save(payload)
        return record

    def get_bundle(self, bundle_id: str) -> dict[str, Any] | None:
        payload = self.load()
        record = payload.get("evidence_bundles", {}).get(bundle_id)
        return dict(record) if isinstance(record, dict) else None


_DIRECT_EVIDENCE_PATTERNS = (
    re.compile(r"^pull together the evidence(?:\s+(?:for|on|around))?\s+(?P<topic>.+?)\.?$", re.IGNORECASE),
    re.compile(r"^make me an evidence bundle(?:\s+(?:for|on|around))?\s+(?P<topic>.+?)\.?$", re.IGNORECASE),
    re.compile(r"^gather the evidence(?:\s+(?:for|on|around))?\s+(?P<topic>.+?)\.?$", re.IGNORECASE),
    re.compile(r"^put together the evidence(?:\s+(?:for|on|around))?\s+(?P<topic>.+?)\.?$", re.IGNORECASE),
)
_DIRECT_EVIDENCE_STARTERS = (
    "pull together the evidence",
    "make me an evidence bundle",
    "gather the evidence",
    "put together the evidence",
)


def is_direct_evidence_bundle_request(request: str) -> bool:
    lowered = " ".join(str(request or "").strip().split()).lower()
    return any(lowered.startswith(prefix) for prefix in _DIRECT_EVIDENCE_STARTERS)


def extract_evidence_bundle_topic(request: str) -> str:
    cleaned = " ".join(str(request or "").strip().split())
    for pattern in _DIRECT_EVIDENCE_PATTERNS:
        matched = pattern.match(cleaned)
        if not matched:
            continue
        return str(matched.group("topic") or "").strip().rstrip(".?!")
    return ""


def _title(topic: str) -> str:
    cleaned = str(topic or "").strip().rstrip(".")
    if not cleaned:
        return "Evidence bundle"
    return f"Evidence bundle for {cleaned}"


def _summary(topic: str) -> str:
    cleaned = str(topic or "").strip()
    return (
        f"This evidence bundle is a local scaffold for {cleaned}. "
        "It does not claim live retrieval or external proof verification."
    )


def _evidence_lines(topic: str) -> list[dict[str, Any]]:
    lowered = str(topic or "").strip().lower()
    if "passive income" in lowered:
        lines = [
            "Define the income lanes or options that are actually being compared",
            "Capture the risk, maintenance load, and time-to-cash-flow evidence each lane needs",
            "Separate assumptions from anything that would still need live verification",
        ]
    elif "retirement workshop" in lowered:
        lines = [
            "Capture the decision the workshop has to support",
            "List the numbers, tradeoffs, and participant needs that matter most",
            "Mark what is confirmed versus what still needs follow-up evidence",
        ]
    elif "pool robot" in lowered:
        lines = [
            "Capture the buying criteria that actually matter: performance, upkeep, price",
            "List what evidence would separate the finalists cleanly",
            "Mark what is still unverified without live product research",
        ]
    elif "scout trailer" in lowered:
        lines = [
            "Capture the storage options or categories being considered",
            "List the evidence needed on security, weather protection, and access",
            "Mark which facts are still assumptions without live site or vendor checks",
        ]
    else:
        lines = [
            f"Capture the key claims or options involved in {topic}",
            f"List the evidence needed to compare or support {topic}",
            f"Mark what remains unverified for {topic}",
        ]
    return [
        {
            "line_id": f"evidence-{index + 1}",
            "text": text,
            "verified": False,
        }
        for index, text in enumerate(lines)
    ]


def _open_questions(topic: str) -> list[str]:
    cleaned = str(topic or "").strip()
    return [
        f"What part of {cleaned} needs the strongest proof first?",
        f"What is still assumption versus evidence in {cleaned}?",
        f"What outside source or check would most reduce ambiguity for {cleaned}?",
    ]


def build_direct_evidence_bundle_response(
    store: EvidenceBundleStore,
    *,
    actor: str,
    room: str,
    request: str,
) -> dict[str, Any] | None:
    if not is_direct_evidence_bundle_request(request):
        return None
    topic = extract_evidence_bundle_topic(request)
    if not topic:
        return {
            "output_text": "I can do that. What should the evidence bundle cover?",
            "created_evidence_bundle": None,
        }
    created = store.create_bundle(
        actor=actor,
        room=room,
        title=_title(topic),
        topic=topic,
        source_request=request,
        summary=_summary(topic),
        evidence_lines=_evidence_lines(topic),
        open_questions=_open_questions(topic),
    )
    return {
        "output_text": (
            f"I made an evidence bundle for {topic}. "
            "It is a bounded local evidence scaffold, not a claim of live retrieval or verified external proof."
        ),
        "created_evidence_bundle": created,
    }
