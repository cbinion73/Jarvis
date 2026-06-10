"""F5: Long-horizon reviews — monthly, seasonal, yearly.

Provides structured reviews across:
- health
- faith
- family
- work
- finances
- learning
- identity

Each review captures:
- Current state assessment
- Progress since last review
- Lessons from prior reviews that shaped current guidance
- Drift flags (areas falling short of stated goals)
- Forward intentions
- How prior lessons changed current approach

Reviews are append-only, provenance-backed, and linked to prior reviews.
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any

from .persistence import append_jsonl, atomic_write_json

_HORIZON_ROOT = Path("data/horizon_reviews")
_REVIEWS_PATH = _HORIZON_ROOT / "reviews.json"
_REVIEWS_LOG = _HORIZON_ROOT / "reviews_log.jsonl"

REVIEW_CADENCES = frozenset({"monthly", "seasonal", "yearly"})
REVIEW_DOMAINS = frozenset({"health", "faith", "family", "work", "finances", "learning", "identity"})
REVIEW_STATUSES = frozenset({"draft", "complete", "archived"})


def _ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


@dataclass(slots=True)
class DomainReview:
    """Review of one domain for a given period."""
    domain: str
    current_state: str              # honest assessment of where things are
    progress_since_last: str        # what moved, what didn't
    lessons_applied: list[str]      # lessons from prior reviews that shaped this period
    drift_flags: list[str]          # areas falling short
    forward_intentions: list[str]   # concrete intentions for next period
    domain_score: int               # 1-10 self-rating for this domain
    confidence: float               # 0.0–1.0 confidence in this assessment


@dataclass(slots=True)
class HorizonReview:
    """A long-horizon review covering all or selected domains."""
    review_id: str
    actor: str
    cadence: str                    # monthly/seasonal/yearly
    period_label: str               # e.g. "2026-06", "2026-Q2", "2026"
    period_start: str               # YYYY-MM-DD
    period_end: str                 # YYYY-MM-DD
    domain_reviews: list[dict]      # list of DomainReview dicts
    overall_narrative: str          # 2-3 paragraph summary of the period
    key_lesson: str                 # the single most important lesson
    what_changed_guidance: str      # how prior reviews changed current behavior/guidance
    prior_review_id: str            # links to the previous review in this cadence
    status: str                     # draft/complete/archived
    created_at: str
    completed_at: str = ""
    source: str = "long_horizon"


class LongHorizonStore:
    """Manages long-horizon reviews with prior-review linkage."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or _HORIZON_ROOT
        self.root.mkdir(parents=True, exist_ok=True)
        self.reviews_path = self.root / "reviews.json"
        self.log_path = self.root / "reviews_log.jsonl"

    def _load(self) -> list[dict]:
        if not self.reviews_path.exists():
            return []
        try:
            data = json.loads(self.reviews_path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _save(self, records: list[dict]) -> None:
        self.reviews_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self.reviews_path, records)

    def create_review(
        self,
        *,
        actor: str,
        cadence: str,
        period_label: str,
        period_start: str,
        period_end: str,
        domain_reviews: list[dict] | None = None,
        overall_narrative: str = "",
        key_lesson: str = "",
        what_changed_guidance: str = "",
    ) -> HorizonReview:
        if cadence not in REVIEW_CADENCES:
            raise ValueError(f"cadence must be one of {sorted(REVIEW_CADENCES)}")
        if not period_label.strip():
            raise ValueError("period_label is required")

        # Find prior review in this cadence for this actor
        prior_id = self._find_prior_review_id(actor, cadence, period_label)

        # Validate domain reviews
        validated_domains: list[dict] = []
        for dr in (domain_reviews or []):
            if isinstance(dr, dict):
                domain = str(dr.get("domain", ""))
                if domain not in REVIEW_DOMAINS:
                    raise ValueError(f"domain must be one of {sorted(REVIEW_DOMAINS)}, got {domain!r}")
                validated_domains.append(dr)

        review = HorizonReview(
            review_id=str(uuid.uuid4()),
            actor=actor,
            cadence=cadence,
            period_label=period_label.strip(),
            period_start=period_start,
            period_end=period_end,
            domain_reviews=validated_domains,
            overall_narrative=overall_narrative,
            key_lesson=key_lesson,
            what_changed_guidance=what_changed_guidance,
            prior_review_id=prior_id,
            status="draft",
            created_at=_ts(),
        )
        records = self._load()
        records.append(asdict(review))
        self._save(records)
        try:
            append_jsonl(self.log_path, asdict(review))
        except Exception:
            pass
        return review

    def _find_prior_review_id(self, actor: str, cadence: str, period_label: str) -> str:
        """Find the most recent completed review in this cadence for this actor."""
        matching = [
            r for r in self._load()
            if r.get("actor") == actor
            and r.get("cadence") == cadence
            and r.get("status") == "complete"
            and r.get("period_label") != period_label
        ]
        if not matching:
            return ""
        # Return most recent by created_at
        return sorted(matching, key=lambda r: r.get("created_at", ""))[-1].get("review_id", "")

    def complete_review(self, review_id: str, actor: str) -> dict | None:
        records = self._load()
        updated = None
        for r in records:
            if r.get("review_id") == review_id:
                if r.get("actor") != actor:
                    raise PermissionError(f"Actor {actor!r} did not create review {review_id!r}")
                r["status"] = "complete"
                r["completed_at"] = _ts()
                updated = r
                break
        if updated:
            self._save(records)
        return updated

    def get_review(self, review_id: str) -> dict | None:
        for r in self._load():
            if r.get("review_id") == review_id:
                return r
        return None

    def list_reviews(
        self,
        actor: str,
        cadence: str | None = None,
        limit: int = 24,
    ) -> list[dict]:
        records = [r for r in self._load() if r.get("actor") == actor]
        if cadence:
            records = [r for r in records if r.get("cadence") == cadence]
        return records[-limit:]

    def get_arc_summary(self, actor: str, cadence: str, limit: int = 6) -> dict[str, Any]:
        """Return a summary showing how prior lessons changed current guidance.

        This is the key Level 9 capability: showing the long arc of growth.
        """
        reviews = [
            r for r in self._load()
            if r.get("actor") == actor
            and r.get("cadence") == cadence
            and r.get("status") == "complete"
        ][-limit:]

        if not reviews:
            return {
                "actor": actor,
                "cadence": cadence,
                "reviews_found": 0,
                "source": "unavailable",
                "reason": f"No completed {cadence} reviews found for actor {actor!r}",
            }

        # Extract key lessons and guidance changes
        lessons = [r.get("key_lesson", "") for r in reviews if r.get("key_lesson")]
        guidance_changes = [r.get("what_changed_guidance", "") for r in reviews if r.get("what_changed_guidance")]

        # Domain drift flags across all reviews
        all_drift: dict[str, int] = {}
        for r in reviews:
            for dr in (r.get("domain_reviews") or []):
                for flag in (dr.get("drift_flags") or []):
                    all_drift[flag] = all_drift.get(flag, 0) + 1

        persistent_drift = [flag for flag, count in all_drift.items() if count >= 2]

        return {
            "actor": actor,
            "cadence": cadence,
            "period_count": len(reviews),
            "period_range": f"{reviews[0].get('period_label', '?')} → {reviews[-1].get('period_label', '?')}",
            "key_lessons": lessons,
            "guidance_changes": guidance_changes,
            "persistent_drift_flags": persistent_drift,
            "most_recent_review_id": reviews[-1].get("review_id", ""),
            "source": "live",
        }

    def get_domain_trend(self, actor: str, domain: str, cadence: str = "monthly") -> dict[str, Any]:
        """Show trend for one domain across reviews."""
        if domain not in REVIEW_DOMAINS:
            raise ValueError(f"domain must be one of {sorted(REVIEW_DOMAINS)}")

        reviews = [
            r for r in self._load()
            if r.get("actor") == actor and r.get("cadence") == cadence
        ]

        trend = []
        for r in reviews:
            for dr in (r.get("domain_reviews") or []):
                if dr.get("domain") == domain:
                    trend.append({
                        "period_label": r.get("period_label"),
                        "domain_score": dr.get("domain_score"),
                        "drift_flags": dr.get("drift_flags", []),
                        "key_intention": (dr.get("forward_intentions") or [""])[0],
                    })

        return {
            "actor": actor,
            "domain": domain,
            "cadence": cadence,
            "data_points": len(trend),
            "trend": trend,
            "source": "live" if trend else "unavailable",
        }
