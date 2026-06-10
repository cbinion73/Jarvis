"""H4: Noise-learning delivery feedback system.

Records delivery feedback (useful / noisy / wrong_time / wrong_surface /
missed_urgency) and adapts future notification routing decisions based on
accumulated history.  The feedback store is consulted by
apple_api._choose_delivery_mode() to suppress domains that have been
consistently marked noisy, escalate domains consistently marked
missed_urgency, and respect surface preferences.

All feedback is persisted with JSONL audit; no external dependencies.
"""
from __future__ import annotations

import json
import time
import uuid
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .persistence import append_jsonl, atomic_write_json

# ── Constants ─────────────────────────────────────────────────────────────────

FEEDBACK_TYPES = frozenset({
    "useful",          # delivered at the right time, right surface, right level
    "noisy",           # this kind of notification is too frequent / irrelevant
    "wrong_time",      # correct content but wrong timing
    "wrong_surface",   # should have gone to a different surface
    "missed_urgency",  # should have been higher priority / reached me sooner
})

# After this many noisy signals for a (domain, mode) pair, suppress that domain
# in that mode (unless critical severity).
SUPPRESS_THRESHOLD = 3

# After this many missed_urgency signals for a (domain, mode) pair, escalate
# that domain in that mode (upgrade hold_for_brief → badge_only, suppress → badge_only).
ESCALATE_THRESHOLD = 2

_DEFAULT_ROOT = Path("data/delivery_feedback")


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass(slots=True)
class DeliveryFeedback:
    feedback_id: str
    actor: str
    feedback_type: str       # one of FEEDBACK_TYPES
    domain: str              # notification domain (work/health/family/faith/social/…)
    severity: str            # info/low/high/critical
    delivery_mode: str       # how it was delivered (badge_only/push/suppress/…)
    active_mode: str         # household mode at time of delivery (normal/crisis/sabbath/…)
    notification_id: str     # id of the notification being rated
    note: str                # optional free-text from user
    created_at: str
    source: str = "user"


# ── Store ─────────────────────────────────────────────────────────────────────

class DeliveryFeedbackStore:
    """Durable feedback store with JSONL audit trail."""

    def __init__(self, root: Path = _DEFAULT_ROOT) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.feedback_path = self.root / "feedback.json"
        self.audit_path = self.root / "feedback_log.jsonl"

    # ── Persistence ──────────────────────────────────────────────────────────

    def _load(self) -> list[dict]:
        if not self.feedback_path.exists():
            return []
        try:
            payload = json.loads(self.feedback_path.read_text(encoding="utf-8"))
            return payload if isinstance(payload, list) else []
        except Exception:
            return []

    def _save(self, records: list[dict]) -> None:
        atomic_write_json(self.feedback_path, records)

    # ── Write ─────────────────────────────────────────────────────────────────

    def record(
        self,
        actor: str,
        feedback_type: str,
        domain: str,
        severity: str = "info",
        delivery_mode: str = "",
        active_mode: str = "normal",
        notification_id: str = "",
        note: str = "",
    ) -> dict:
        """Record a delivery feedback event.

        Returns the persisted feedback record.
        """
        if feedback_type not in FEEDBACK_TYPES:
            raise ValueError(
                f"Unknown feedback_type {feedback_type!r}. "
                f"Valid: {sorted(FEEDBACK_TYPES)}"
            )

        fb = DeliveryFeedback(
            feedback_id=str(uuid.uuid4()),
            actor=str(actor or "chris").strip(),
            feedback_type=feedback_type,
            domain=str(domain or "").strip().lower(),
            severity=str(severity or "info").strip().lower(),
            delivery_mode=str(delivery_mode or "").strip(),
            active_mode=str(active_mode or "normal").strip(),
            notification_id=str(notification_id or "").strip(),
            note=str(note or "").strip(),
            created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )
        payload = asdict(fb)

        records = self._load()
        records.append(payload)
        self._save(records)
        append_jsonl(self.audit_path, {**payload, "event": "feedback_recorded"})
        return payload

    # ── Read / Summarise ─────────────────────────────────────────────────────

    def list_feedback(
        self,
        actor: str = "",
        domain: str = "",
        active_mode: str = "",
        limit: int = 0,
    ) -> list[dict]:
        """Return feedback records, optionally filtered."""
        records = self._load()
        if actor:
            actor_lower = actor.strip().lower()
            records = [r for r in records if str(r.get("actor") or "").lower() == actor_lower]
        if domain:
            domain_lower = domain.strip().lower()
            records = [r for r in records if str(r.get("domain") or "").lower() == domain_lower]
        if active_mode:
            records = [r for r in records if str(r.get("active_mode") or "") == active_mode]
        if limit:
            records = records[-limit:]
        return records

    def get_routing_adjustments(
        self,
        actor: str = "",
        active_mode: str = "normal",
        lookback: int = 50,
    ) -> dict[str, Any]:
        """Return routing adjustments learned from feedback history.

        Returns a dict with:
          suppress_domains: list[str]   — domains to suppress (too noisy)
          escalate_domains: list[str]   — domains to escalate (missed urgency)
          surface_hints: dict[str, str] — domain → preferred surface
        """
        records = self.list_feedback(actor=actor, limit=lookback)
        # Filter to relevant mode — if no mode-specific data, fall back to all modes
        mode_records = [r for r in records if str(r.get("active_mode") or "") == active_mode]
        if len(mode_records) < 5:
            mode_records = records  # not enough mode-specific data; use all

        noisy_counts: dict[str, int] = defaultdict(int)
        escalate_counts: dict[str, int] = defaultdict(int)
        surface_votes: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

        for r in mode_records:
            domain = str(r.get("domain") or "").lower()
            ftype = str(r.get("feedback_type") or "")
            surface = str(r.get("delivery_mode") or "")
            if not domain:
                continue
            if ftype == "noisy":
                noisy_counts[domain] += 1
            elif ftype == "missed_urgency":
                escalate_counts[domain] += 1
            elif ftype == "wrong_surface" and surface:
                # Downvote current surface; hints point elsewhere
                pass
            elif ftype == "useful" and surface:
                surface_votes[domain][surface] += 1

        suppress_domains = [d for d, cnt in noisy_counts.items() if cnt >= SUPPRESS_THRESHOLD]
        escalate_domains = [d for d, cnt in escalate_counts.items() if cnt >= ESCALATE_THRESHOLD]

        # Remove escalation conflicts (if both noisy and escalate, escalation wins for safety)
        escalate_set = set(escalate_domains)
        suppress_domains = [d for d in suppress_domains if d not in escalate_set]

        # Best surface per domain (most useful votes)
        surface_hints: dict[str, str] = {}
        for domain, votes in surface_votes.items():
            if votes:
                surface_hints[domain] = max(votes, key=lambda k: votes[k])

        return {
            "suppress_domains": suppress_domains,
            "escalate_domains": escalate_domains,
            "surface_hints": surface_hints,
            "noisy_counts": dict(noisy_counts),
            "escalate_counts": dict(escalate_counts),
            "records_analyzed": len(mode_records),
        }


# ── Module-level singleton ────────────────────────────────────────────────────

_store: DeliveryFeedbackStore | None = None


def get_feedback_store(root: Path = _DEFAULT_ROOT) -> DeliveryFeedbackStore:
    global _store
    if _store is None:
        _store = DeliveryFeedbackStore(root=root)
    return _store
