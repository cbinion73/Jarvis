"""E1: Health loop — morning check-in, evening review, Three Moves, doctor packet, drift scan.

Provides durable persistence for:
- Morning health check-ins (mood, energy, sleep, hydration)
- Evening review (Three Moves outcomes, what worked, drift scan)
- Doctor packet generation (structured summary for medical appointments)
- Drift scan follow-up cycles (flag unresolved health items)

All data is append-only (JSONL) for audit safety.
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .persistence import append_jsonl, atomic_write_json

_HEALTH_ROOT = Path("data/health")
_CHECKINS_PATH = _HEALTH_ROOT / "checkins.json"
_CHECKINS_LOG_PATH = _HEALTH_ROOT / "checkins_log.jsonl"
_REVIEWS_PATH = _HEALTH_ROOT / "evening_reviews.json"
_REVIEWS_LOG_PATH = _HEALTH_ROOT / "evening_reviews_log.jsonl"
_DRIFT_PATH = _HEALTH_ROOT / "drift_items.json"


def _ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# ---------------------------------------------------------------------------
# Morning check-in
# ---------------------------------------------------------------------------
MOOD_LEVELS = ("low", "moderate", "good", "great")
ENERGY_LEVELS = ("depleted", "low", "moderate", "high")
SLEEP_LEVELS = ("poor", "fair", "good", "great")


@dataclass(slots=True)
class MorningCheckin:
    checkin_id: str
    actor: str
    date: str                    # YYYY-MM-DD
    mood: str                    # low/moderate/good/great
    energy: str                  # depleted/low/moderate/high
    sleep_quality: str           # poor/fair/good/great
    sleep_hours: float
    hydration_oz: float
    three_moves: list[str]       # 3 intentions for the day
    gratitude: str
    notes: str
    created_at: str
    source: str = "live"


@dataclass(slots=True)
class EveningReview:
    review_id: str
    actor: str
    date: str
    checkin_id: str              # links back to morning check-in
    three_moves_outcomes: list[dict]   # [{move, completed, notes}]
    what_worked: str
    what_didnt: str
    health_rating: int           # 1-10 self-rating for the day
    drift_flags: list[str]       # health items to follow up
    notes: str
    created_at: str
    source: str = "live"


@dataclass(slots=True)
class DriftItem:
    drift_id: str
    actor: str
    description: str
    category: str                # hydration/sleep/exercise/nutrition/mental/medical
    created_at: str
    resolved_at: str = ""
    resolved_by: str = ""
    resolution_note: str = ""
    status: str = "open"         # open/resolved/escalated
    source: str = "live"


class HealthLoopStore:
    """Durable store for health loop data."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or _HEALTH_ROOT
        self.root.mkdir(parents=True, exist_ok=True)
        self.checkins_path = self.root / "checkins.json"
        self.checkins_log = self.root / "checkins_log.jsonl"
        self.reviews_path = self.root / "evening_reviews.json"
        self.reviews_log = self.root / "evening_reviews_log.jsonl"
        self.drift_path = self.root / "drift_items.json"

    def _load_json(self, path: Path) -> list[dict]:
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _save_json(self, path: Path, records: list[dict]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(path, records)

    # ------------------------------------------------------------------
    # Morning check-in
    # ------------------------------------------------------------------

    def add_checkin(
        self,
        *,
        actor: str,
        date: str,
        mood: str,
        energy: str,
        sleep_quality: str,
        sleep_hours: float,
        hydration_oz: float = 0.0,
        three_moves: list[str] | None = None,
        gratitude: str = "",
        notes: str = "",
    ) -> MorningCheckin:
        if mood not in MOOD_LEVELS:
            raise ValueError(f"mood must be one of {MOOD_LEVELS}")
        if energy not in ENERGY_LEVELS:
            raise ValueError(f"energy must be one of {ENERGY_LEVELS}")
        if sleep_quality not in SLEEP_LEVELS:
            raise ValueError(f"sleep_quality must be one of {SLEEP_LEVELS}")
        moves = (three_moves or [])[:3]
        checkin = MorningCheckin(
            checkin_id=str(uuid.uuid4()),
            actor=actor,
            date=date,
            mood=mood,
            energy=energy,
            sleep_quality=sleep_quality,
            sleep_hours=float(sleep_hours),
            hydration_oz=float(hydration_oz),
            three_moves=moves,
            gratitude=gratitude,
            notes=notes,
            created_at=_ts(),
        )
        records = self._load_json(self.checkins_path)
        records.append(asdict(checkin))
        self._save_json(self.checkins_path, records)
        append_jsonl(self.checkins_log, asdict(checkin))
        return checkin

    def get_checkin_for_date(self, actor: str, date: str) -> dict | None:
        for r in reversed(self._load_json(self.checkins_path)):
            if r.get("actor") == actor and r.get("date") == date:
                return r
        return None

    def list_checkins(self, actor: str, limit: int = 30) -> list[dict]:
        return [r for r in self._load_json(self.checkins_path) if r.get("actor") == actor][-limit:]

    # ------------------------------------------------------------------
    # Evening review
    # ------------------------------------------------------------------

    def add_evening_review(
        self,
        *,
        actor: str,
        date: str,
        checkin_id: str = "",
        three_moves_outcomes: list[dict] | None = None,
        what_worked: str = "",
        what_didnt: str = "",
        health_rating: int = 5,
        drift_flags: list[str] | None = None,
        notes: str = "",
    ) -> EveningReview:
        if not (1 <= health_rating <= 10):
            raise ValueError("health_rating must be between 1 and 10")
        review = EveningReview(
            review_id=str(uuid.uuid4()),
            actor=actor,
            date=date,
            checkin_id=checkin_id,
            three_moves_outcomes=three_moves_outcomes or [],
            what_worked=what_worked,
            what_didnt=what_didnt,
            health_rating=health_rating,
            drift_flags=drift_flags or [],
            notes=notes,
            created_at=_ts(),
        )
        records = self._load_json(self.reviews_path)
        records.append(asdict(review))
        self._save_json(self.reviews_path, records)
        append_jsonl(self.reviews_log, asdict(review))
        # Auto-create drift items for any flagged health items
        for flag in (drift_flags or []):
            self.add_drift_item(actor=actor, description=flag, category="general")
        return review

    def list_reviews(self, actor: str, limit: int = 30) -> list[dict]:
        return [r for r in self._load_json(self.reviews_path) if r.get("actor") == actor][-limit:]

    # ------------------------------------------------------------------
    # Drift scan
    # ------------------------------------------------------------------

    def add_drift_item(
        self,
        *,
        actor: str,
        description: str,
        category: str = "general",
    ) -> DriftItem:
        item = DriftItem(
            drift_id=str(uuid.uuid4()),
            actor=actor,
            description=description,
            category=category,
            created_at=_ts(),
        )
        records = self._load_json(self.drift_path)
        records.append(asdict(item))
        self._save_json(self.drift_path, records)
        return item

    def resolve_drift_item(self, drift_id: str, actor: str, note: str = "") -> dict | None:
        records = self._load_json(self.drift_path)
        updated = None
        for r in records:
            if r.get("drift_id") == drift_id:
                r["status"] = "resolved"
                r["resolved_at"] = _ts()
                r["resolved_by"] = actor
                r["resolution_note"] = note
                updated = r
                break
        if updated:
            self._save_json(self.drift_path, records)
        return updated

    def list_open_drift_items(self, actor: str) -> list[dict]:
        return [r for r in self._load_json(self.drift_path)
                if r.get("actor") == actor and r.get("status") == "open"]

    # ------------------------------------------------------------------
    # Doctor packet
    # ------------------------------------------------------------------

    def build_doctor_packet(self, actor: str, days: int = 14) -> dict[str, Any]:
        """Generate a structured summary for a medical appointment.

        Returns honest unavailable state if no data exists.
        """
        checkins = self.list_checkins(actor, limit=days)
        reviews = self.list_reviews(actor, limit=days)
        open_drift = self.list_open_drift_items(actor)

        if not checkins and not reviews:
            return {
                "source": "unavailable",
                "reason": "No health check-in data found for this actor.",
                "actor": actor,
                "days": days,
            }

        avg_sleep = (
            round(sum(c.get("sleep_hours", 0) for c in checkins) / len(checkins), 1)
            if checkins else None
        )
        avg_rating = (
            round(sum(r.get("health_rating", 5) for r in reviews) / len(reviews), 1)
            if reviews else None
        )
        mood_counts: dict[str, int] = {}
        for c in checkins:
            m = c.get("mood", "unknown")
            mood_counts[m] = mood_counts.get(m, 0) + 1

        return {
            "source": "live",
            "actor": actor,
            "period_days": days,
            "checkin_count": len(checkins),
            "review_count": len(reviews),
            "avg_sleep_hours": avg_sleep,
            "avg_daily_health_rating": avg_rating,
            "mood_distribution": mood_counts,
            "open_drift_items": open_drift,
            "recent_drift_flags": [
                flag
                for r in reviews[-7:]
                for flag in r.get("drift_flags", [])
            ],
        }
