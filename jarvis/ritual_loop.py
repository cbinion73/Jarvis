"""E2: Faith/ritual loop — prayer capture, study review, household ritual summaries.

Provides:
- RitualSummaryStore: prayer/study item persistence + household summaries
- Follow-up resurfacing: items not reviewed in N days surface again
- Chronicle routing: faith records belong to Chronicle domain, not raw JARVIS memory
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path

from .persistence import append_jsonl, atomic_write_json

_RITUAL_ROOT = Path("data/formation/ritual")
_PRAYER_PATH = _RITUAL_ROOT / "prayer_items.json"
_PRAYER_LOG = _RITUAL_ROOT / "prayer_items_log.jsonl"
_STUDY_PATH = _RITUAL_ROOT / "study_items.json"
_STUDY_LOG = _RITUAL_ROOT / "study_items_log.jsonl"
_SUMMARIES_PATH = _RITUAL_ROOT / "household_summaries.json"
_SUMMARIES_LOG = _RITUAL_ROOT / "household_summaries_log.jsonl"


def _ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


PRAYER_STATUS = frozenset({"active", "answered", "deferred", "archived"})
STUDY_STATUS = frozenset({"open", "reviewed", "completed", "archived"})


@dataclass(slots=True)
class PrayerItem:
    prayer_id: str
    actor: str
    subject: str                 # who/what is being prayed for
    request: str                 # the prayer request
    category: str                # personal/family/community/global
    status: str                  # active/answered/deferred/archived
    created_at: str
    last_reviewed_at: str = ""
    answer_note: str = ""
    domain: str = "chronicle"    # always chronicle — not JARVIS memory
    source: str = "live"


@dataclass(slots=True)
class StudyItem:
    study_id: str
    actor: str
    title: str                   # scripture reference or book/topic
    content: str                 # notes, reflection, or key insight
    category: str                # scripture/devotional/book/sermon/other
    status: str                  # open/reviewed/completed/archived
    created_at: str
    last_reviewed_at: str = ""
    follow_up_note: str = ""
    domain: str = "chronicle"
    source: str = "live"


@dataclass(slots=True)
class HouseholdRitualSummary:
    summary_id: str
    week_of: str                 # YYYY-MM-DD (Monday of the week)
    actor: str
    family_devotional_count: int
    prayer_items_added: int
    prayer_items_answered: int
    study_items_reviewed: int
    highlights: str
    prayer_needs: list[str]      # active requests to resurface
    created_at: str
    domain: str = "chronicle"
    source: str = "live"


class RitualSummaryStore:
    """Manages prayer/study items and household ritual summaries."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or _RITUAL_ROOT
        self.root.mkdir(parents=True, exist_ok=True)
        self.prayer_path = self.root / "prayer_items.json"
        self.prayer_log = self.root / "prayer_items_log.jsonl"
        self.study_path = self.root / "study_items.json"
        self.study_log = self.root / "study_items_log.jsonl"
        self.summaries_path = self.root / "household_summaries.json"
        self.summaries_log = self.root / "household_summaries_log.jsonl"

    def _load(self, path: Path) -> list[dict]:
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _save(self, path: Path, records: list[dict]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(path, records)

    # ------------------------------------------------------------------
    # Prayer items
    # ------------------------------------------------------------------

    def add_prayer(
        self,
        *,
        actor: str,
        subject: str,
        request: str,
        category: str = "personal",
    ) -> PrayerItem:
        item = PrayerItem(
            prayer_id=str(uuid.uuid4()),
            actor=actor,
            subject=subject,
            request=request,
            category=category,
            status="active",
            created_at=_ts(),
        )
        records = self._load(self.prayer_path)
        records.append(asdict(item))
        self._save(self.prayer_path, records)
        append_jsonl(self.prayer_log, asdict(item))
        return item

    def update_prayer_status(
        self, prayer_id: str, status: str, answer_note: str = ""
    ) -> dict | None:
        if status not in PRAYER_STATUS:
            raise ValueError(f"status must be one of {sorted(PRAYER_STATUS)}")
        records = self._load(self.prayer_path)
        updated = None
        for r in records:
            if r.get("prayer_id") == prayer_id:
                r["status"] = status
                r["last_reviewed_at"] = _ts()
                if answer_note:
                    r["answer_note"] = answer_note
                updated = r
                break
        if updated:
            self._save(self.prayer_path, records)
        return updated

    def list_active_prayers(self, actor: str) -> list[dict]:
        return [r for r in self._load(self.prayer_path)
                if r.get("actor") == actor and r.get("status") == "active"]

    def get_prayers_needing_review(self, actor: str, stale_days: int = 7) -> list[dict]:
        """Return active prayers not reviewed in stale_days days.

        If last_reviewed_at is empty, the prayer has never been reviewed → always stale.
        """
        now = time.time()
        cutoff = now - (stale_days * 86400)
        stale = []
        for r in self._load(self.prayer_path):
            if r.get("actor") != actor or r.get("status") != "active":
                continue
            last = r.get("last_reviewed_at") or ""
            if not last:
                # Never reviewed → always stale
                stale.append(r)
                continue
            try:
                t = time.mktime(time.strptime(last, "%Y-%m-%dT%H:%M:%SZ"))
                if t < cutoff:
                    stale.append(r)
            except Exception:
                stale.append(r)
        return stale

    # ------------------------------------------------------------------
    # Study items
    # ------------------------------------------------------------------

    def add_study(
        self,
        *,
        actor: str,
        title: str,
        content: str,
        category: str = "scripture",
    ) -> StudyItem:
        item = StudyItem(
            study_id=str(uuid.uuid4()),
            actor=actor,
            title=title,
            content=content,
            category=category,
            status="open",
            created_at=_ts(),
        )
        records = self._load(self.study_path)
        records.append(asdict(item))
        self._save(self.study_path, records)
        append_jsonl(self.study_log, asdict(item))
        return item

    def mark_study_reviewed(self, study_id: str, follow_up_note: str = "") -> dict | None:
        records = self._load(self.study_path)
        updated = None
        for r in records:
            if r.get("study_id") == study_id:
                r["status"] = "reviewed"
                r["last_reviewed_at"] = _ts()
                if follow_up_note:
                    r["follow_up_note"] = follow_up_note
                updated = r
                break
        if updated:
            self._save(self.study_path, records)
        return updated

    def list_study_items(self, actor: str, status: str | None = None) -> list[dict]:
        records = [r for r in self._load(self.study_path) if r.get("actor") == actor]
        if status:
            records = [r for r in records if r.get("status") == status]
        return records

    # ------------------------------------------------------------------
    # Household ritual summaries
    # ------------------------------------------------------------------

    def add_summary(
        self,
        *,
        actor: str,
        week_of: str,
        family_devotional_count: int = 0,
        prayer_items_added: int = 0,
        prayer_items_answered: int = 0,
        study_items_reviewed: int = 0,
        highlights: str = "",
        prayer_needs: list[str] | None = None,
    ) -> HouseholdRitualSummary:
        summary = HouseholdRitualSummary(
            summary_id=str(uuid.uuid4()),
            week_of=week_of,
            actor=actor,
            family_devotional_count=family_devotional_count,
            prayer_items_added=prayer_items_added,
            prayer_items_answered=prayer_items_answered,
            study_items_reviewed=study_items_reviewed,
            highlights=highlights,
            prayer_needs=prayer_needs or [],
            created_at=_ts(),
        )
        records = self._load(self.summaries_path)
        records.append(asdict(summary))
        self._save(self.summaries_path, records)
        append_jsonl(self.summaries_log, asdict(summary))
        return summary

    def list_summaries(self, actor: str, limit: int = 12) -> list[dict]:
        return [r for r in self._load(self.summaries_path) if r.get("actor") == actor][-limit:]
