"""
growth_intelligence.py — Epic 15: Self-Improvement & Growth
============================================================
Unified personal growth layer for JARVIS.  Five agents cover the full
spectrum of Chris's growth life:

  - NovaAgent       (nova)          — Personal Learning & Growth Director
  - GamoraAgent     (gamora)        — Relationship Intelligence Lead
  - AgathaAgent     (agatha)        — Occasions & Gift Intelligence Lead
  - SpiderManAgent  (spider-man)    — World Signal & Intelligence Monitor
  - ThorAgent       (thor)          — Health & Fitness Steward

All personal data (relationships, health) is stored locally only — never
sent to external APIs.  Pure stdlib; no new dependencies.

Storage layout:
    ~/.jarvis/growth/learning.json
    ~/.jarvis/growth/relationships.json
    ~/.jarvis/growth/occasions.json
    ~/.jarvis/growth/signals.jsonl
    ~/.jarvis/growth/health_log.jsonl
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today() -> str:
    return date.today().isoformat()


def _today_md() -> str:
    """Return today as MM-DD for birthday/anniversary matching."""
    return date.today().strftime("%m-%d")


def _days_until_md(md: str) -> int:
    """Days until next occurrence of a MM-DD date string."""
    try:
        month, day = (int(x) for x in md.split("-"))
    except (ValueError, AttributeError):
        return 9999
    today = date.today()
    candidate = date(today.year, month, day)
    if candidate < today:
        candidate = date(today.year + 1, month, day)
    return (candidate - today).days


def _days_until_date(date_str: str) -> int:
    """Days until a YYYY-MM-DD or MM-DD date string."""
    if not date_str:
        return 9999
    if len(date_str) == 5:  # MM-DD
        return _days_until_md(date_str)
    try:
        target = date.fromisoformat(date_str)
        return (target - date.today()).days
    except ValueError:
        return 9999


def _parse_date(date_str: str) -> date | None:
    try:
        if len(date_str) == 5:
            month, day = (int(x) for x in date_str.split("-"))
            today = date.today()
            return date(today.year, month, day)
        return date.fromisoformat(date_str)
    except (ValueError, AttributeError):
        return None


def _frequency_days(freq: str) -> int:
    mapping = {
        "weekly": 7,
        "monthly": 30,
        "quarterly": 90,
        "annual": 365,
        "as_needed": 9999,
    }
    return mapping.get(freq, 9999)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class LearningItem:
    item_id: str
    title: str
    item_type: str          # "book" | "podcast" | "article" | "course" | "video" | "practice"
    topic: str              # "strategy" | "writing" | "faith" | "leadership" | "technology" | "parenting" | "finance" | "maker" | etc.
    status: str             # "want_to" | "in_progress" | "completed" | "abandoned"
    source: str = ""        # where it came from
    url: str = ""
    notes: str = ""
    started_at: str = ""
    completed_at: str = ""
    rating: int = 0         # 1-5 stars
    key_takeaway: str = ""  # what stuck
    recommended_by: str = ""


@dataclass
class Relationship:
    contact_id: str
    name: str
    relationship_type: str      # "friend" | "family" | "mentor" | "colleague" | "community"
    last_contact: str = ""      # ISO date
    contact_frequency: str = "monthly"  # "weekly" | "monthly" | "quarterly" | "annual" | "as_needed"
    notes: str = ""
    birthday: str = ""          # MM-DD format
    anniversary: str = ""       # MM-DD (if applicable)
    shared_interests: list[str] = field(default_factory=list)
    open_threads: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    is_family: bool = False


@dataclass
class Occasion:
    occasion_id: str
    title: str
    occasion_type: str          # "birthday" | "anniversary" | "graduation" | "holiday" | "custom"
    contact_id: str = ""        # linked relationship
    date: str = ""              # MM-DD recurring or YYYY-MM-DD one-time
    recurring: bool = True
    advance_notice_days: int = 14  # when to surface
    gift_ideas: list[str] = field(default_factory=list)
    gift_history: list[dict] = field(default_factory=list)  # [{"year": int, "gift": str, "notes": str}]
    notes: str = ""
    active: bool = True


@dataclass
class WorldSignal:
    signal_id: str
    title: str
    signal_type: str        # "news" | "industry" | "opportunity" | "threat" | "trend"
    topic: str              # which of Chris's interest areas this touches
    summary: str = ""
    source: str = ""
    url: str = ""
    detected_at: str = ""
    surfaced: bool = False
    relevance_score: float = 0.0  # 0.0-1.0
    tags: list[str] = field(default_factory=list)


@dataclass
class HealthLog:
    log_id: str
    actor_id: str
    date: str
    activity_type: str      # "walk" | "run" | "workout" | "yoga" | "hike" | "bike" | "swim" | "other"
    duration_minutes: int = 0
    intensity: str = "moderate"  # "light" | "moderate" | "vigorous"
    notes: str = ""
    steps: int = 0
    calories_active: int = 0
    heart_rate_avg: int = 0


# ---------------------------------------------------------------------------
# GrowthStore
# ---------------------------------------------------------------------------

class GrowthStore:
    """
    Manages all growth data persisted under ~/.jarvis/growth/.

    Files:
        learning.json       — list of LearningItem dicts
        relationships.json  — list of Relationship dicts
        occasions.json      — list of Occasion dicts
        signals.jsonl       — append-only WorldSignal records
        health_log.jsonl    — append-only HealthLog records
    """

    ROOT = Path.home() / ".jarvis" / "growth"

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or self.ROOT
        self.root.mkdir(parents=True, exist_ok=True)
        self._learning_path = self.root / "learning.json"
        self._relationships_path = self.root / "relationships.json"
        self._occasions_path = self.root / "occasions.json"
        self._signals_path = self.root / "signals.jsonl"
        self._health_path = self.root / "health_log.jsonl"
        self._seed_if_empty()

    # ------------------------------------------------------------------
    # Internal IO helpers
    # ------------------------------------------------------------------

    def _load_json(self, path: Path, *, default: Any = None) -> Any:
        if not path.exists():
            return default if default is not None else []
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return default if default is not None else []

    def _save_json(self, path: Path, payload: Any) -> None:
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def _load_jsonl(self, path: Path) -> list[dict]:
        if not path.exists():
            return []
        records: list[dict] = []
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        except OSError:
            pass
        return records

    def _append_jsonl(self, path: Path, record: dict) -> None:
        try:
            with path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(record) + "\n")
        except OSError:
            pass

    # ------------------------------------------------------------------
    # Learning
    # ------------------------------------------------------------------

    def load_learning(self) -> list[LearningItem]:
        raw = self._load_json(self._learning_path)
        items: list[LearningItem] = []
        for d in raw if isinstance(raw, list) else []:
            try:
                items.append(LearningItem(**{k: v for k, v in d.items() if k in LearningItem.__dataclass_fields__}))
            except (TypeError, AttributeError):
                pass
        return items

    def save_learning(self, items: list[LearningItem]) -> None:
        self._save_json(self._learning_path, [asdict(i) for i in items])

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    def load_relationships(self) -> list[Relationship]:
        raw = self._load_json(self._relationships_path)
        contacts: list[Relationship] = []
        for d in raw if isinstance(raw, list) else []:
            try:
                contacts.append(Relationship(**{k: v for k, v in d.items() if k in Relationship.__dataclass_fields__}))
            except (TypeError, AttributeError):
                pass
        return contacts

    def save_relationships(self, contacts: list[Relationship]) -> None:
        self._save_json(self._relationships_path, [asdict(c) for c in contacts])

    # ------------------------------------------------------------------
    # Occasions
    # ------------------------------------------------------------------

    def load_occasions(self) -> list[Occasion]:
        raw = self._load_json(self._occasions_path)
        occasions: list[Occasion] = []
        for d in raw if isinstance(raw, list) else []:
            try:
                occasions.append(Occasion(**{k: v for k, v in d.items() if k in Occasion.__dataclass_fields__}))
            except (TypeError, AttributeError):
                pass
        return occasions

    def save_occasions(self, occasions: list[Occasion]) -> None:
        self._save_json(self._occasions_path, [asdict(o) for o in occasions])

    # ------------------------------------------------------------------
    # Signals (append-only JSONL)
    # ------------------------------------------------------------------

    def load_signals(self) -> list[WorldSignal]:
        records = self._load_jsonl(self._signals_path)
        signals: list[WorldSignal] = []
        for d in records:
            try:
                signals.append(WorldSignal(**{k: v for k, v in d.items() if k in WorldSignal.__dataclass_fields__}))
            except (TypeError, AttributeError):
                pass
        return signals

    def append_signal(self, signal: WorldSignal) -> None:
        self._append_jsonl(self._signals_path, asdict(signal))

    def update_signal(self, signal_id: str, **kwargs: Any) -> bool:
        """Update a signal record by rewriting the JSONL."""
        records = self._load_jsonl(self._signals_path)
        found = False
        for rec in records:
            if rec.get("signal_id") == signal_id:
                rec.update(kwargs)
                found = True
        if found:
            try:
                with self._signals_path.open("w", encoding="utf-8") as fh:
                    for rec in records:
                        fh.write(json.dumps(rec) + "\n")
            except OSError:
                pass
        return found

    # ------------------------------------------------------------------
    # Health log (append-only JSONL)
    # ------------------------------------------------------------------

    def load_health_log(self, actor_id: str = "chris") -> list[HealthLog]:
        records = self._load_jsonl(self._health_path)
        logs: list[HealthLog] = []
        for d in records:
            if d.get("actor_id") == actor_id:
                try:
                    logs.append(HealthLog(**{k: v for k, v in d.items() if k in HealthLog.__dataclass_fields__}))
                except (TypeError, AttributeError):
                    pass
        return logs

    def append_health_log(self, log: HealthLog) -> None:
        self._append_jsonl(self._health_path, asdict(log))

    # ------------------------------------------------------------------
    # Seed
    # ------------------------------------------------------------------

    def _seed_if_empty(self) -> None:
        """Seed with sample data when first run."""
        # Seed relationships
        if not self._relationships_path.exists():
            seed_contacts = [
                Relationship(
                    contact_id="rebekah-binion",
                    name="Rebekah Binion",
                    relationship_type="family",
                    last_contact=_today(),
                    contact_frequency="weekly",
                    notes="Wife. Core partner in everything.",
                    birthday="03-15",
                    anniversary="07-05",
                    shared_interests=["faith", "family", "home"],
                    open_threads=[],
                    tags=["spouse", "immediate-family"],
                    is_family=True,
                ),
                Relationship(
                    contact_id="dad-binion",
                    name="Dad (Bob Binion)",
                    relationship_type="family",
                    last_contact="",
                    contact_frequency="monthly",
                    notes="Dad. Important to stay connected.",
                    birthday="05-22",
                    anniversary="",
                    shared_interests=["faith", "hunting", "family history"],
                    open_threads=[],
                    tags=["parent", "immediate-family"],
                    is_family=True,
                ),
                Relationship(
                    contact_id="mom-binion",
                    name="Mom (Carolyn Binion)",
                    relationship_type="family",
                    last_contact="",
                    contact_frequency="monthly",
                    notes="Mom. Always supportive.",
                    birthday="09-08",
                    anniversary="",
                    shared_interests=["faith", "family", "reading"],
                    open_threads=[],
                    tags=["parent", "immediate-family"],
                    is_family=True,
                ),
            ]
            self.save_relationships(seed_contacts)

        # Seed occasions
        if not self._occasions_path.exists():
            seed_occasions = [
                Occasion(
                    occasion_id="rebekah-birthday",
                    title="Rebekah's Birthday",
                    occasion_type="birthday",
                    contact_id="rebekah-binion",
                    date="03-15",
                    recurring=True,
                    advance_notice_days=21,
                    gift_ideas=[
                        "Experience together (restaurant, concert, trip)",
                        "Something for her creative side",
                        "Thoughtful personalized gift",
                    ],
                    gift_history=[],
                    notes="Plan something meaningful, not just practical.",
                    active=True,
                ),
                Occasion(
                    occasion_id="wedding-anniversary",
                    title="Wedding Anniversary",
                    occasion_type="anniversary",
                    contact_id="rebekah-binion",
                    date="07-05",
                    recurring=True,
                    advance_notice_days=30,
                    gift_ideas=[
                        "Overnight trip or weekend away",
                        "Renewal of a meaningful tradition",
                        "Personalized keepsake",
                    ],
                    gift_history=[],
                    notes="One of the most important occasions of the year.",
                    active=True,
                ),
                Occasion(
                    occasion_id="dad-birthday",
                    title="Dad's Birthday",
                    occasion_type="birthday",
                    contact_id="dad-binion",
                    date="05-22",
                    recurring=True,
                    advance_notice_days=14,
                    gift_ideas=[
                        "Something for his hobbies (hunting, outdoors)",
                        "Family photo or keepsake",
                        "Gift card + phone call",
                    ],
                    gift_history=[],
                    notes="",
                    active=True,
                ),
            ]
            self.save_occasions(seed_occasions)

        # Seed learning items
        if not self._learning_path.exists():
            seed_learning = [
                LearningItem(
                    item_id="book-good-strategy",
                    title="Good Strategy / Bad Strategy",
                    item_type="book",
                    topic="strategy",
                    status="want_to",
                    source="Nova recommendation",
                    url="",
                    notes="Clarity on what makes strategy work vs. feel-good goals.",
                    started_at="",
                    completed_at="",
                    rating=0,
                    key_takeaway="",
                    recommended_by="nova",
                ),
                LearningItem(
                    item_id="book-ruthless-hurry",
                    title="The Ruthless Elimination of Hurry — John Mark Comer",
                    item_type="book",
                    topic="faith",
                    status="want_to",
                    source="Nova recommendation",
                    url="",
                    notes="Pace and presence. Critical for someone who never stops.",
                    started_at="",
                    completed_at="",
                    rating=0,
                    key_takeaway="",
                    recommended_by="nova",
                ),
                LearningItem(
                    item_id="book-psychology-money",
                    title="The Psychology of Money — Morgan Housel",
                    item_type="book",
                    topic="finance",
                    status="want_to",
                    source="Nova recommendation",
                    url="",
                    notes="Reframes the money relationship. Highly rated for mindset shift.",
                    started_at="",
                    completed_at="",
                    rating=0,
                    key_takeaway="",
                    recommended_by="nova",
                ),
            ]
            self.save_learning(seed_learning)


# ---------------------------------------------------------------------------
# NovaAgent — Personal Learning & Growth Director
# ---------------------------------------------------------------------------

class NovaAgent:
    """
    Nova: cosmic awareness, sees patterns in growth across time.
    Tracks what Chris is learning and surfaces the next most valuable thing.
    """

    SUGGESTION_POOL: dict[str, list[dict]] = {
        "strategy": [
            {"title": "Good Strategy/Bad Strategy", "type": "book", "why": "Sharpens the strategy instinct Chris uses every day"},
            {"title": "The Effective Executive — Peter Drucker", "type": "book", "why": "Timeless on prioritization and contribution"},
            {"title": "Playing to Win — Roger Martin", "type": "book", "why": "Choice cascade model used by the best operators"},
        ],
        "writing": [
            {"title": "Bird by Bird — Anne Lamott", "type": "book", "why": "For the messy middle of any manuscript"},
            {"title": "On Writing — Stephen King", "type": "book", "why": "Direct and honest about the craft"},
            {"title": "Several Short Sentences About Writing — Verlyn Klinkenborg", "type": "book", "why": "Rethinks the sentence from the ground up"},
        ],
        "faith": [
            {"title": "Knowing God — J.I. Packer", "type": "book", "why": "Deep formation reading, not surface theology"},
            {"title": "The Ruthless Elimination of Hurry — John Mark Comer", "type": "book", "why": "For a strategist who never stops"},
            {"title": "The Ragamuffin Gospel — Brennan Manning", "type": "book", "why": "Grace that sticks"},
        ],
        "leadership": [
            {"title": "The Motive — Patrick Lencioni", "type": "book", "why": "Checks leadership motivation"},
            {"title": "Dare to Lead — Brené Brown", "type": "book", "why": "For leading family and teams"},
            {"title": "The First 90 Days — Michael Watkins", "type": "book", "why": "Transitions and influence"},
        ],
        "finance": [
            {"title": "The Psychology of Money — Morgan Housel", "type": "book", "why": "Reframes the money relationship"},
            {"title": "Die with Zero — Bill Perkins", "type": "book", "why": "Challenging framework on life investment"},
            {"title": "The Simple Path to Wealth — JL Collins", "type": "book", "why": "Clear and direct long-term compounding path"},
        ],
        "maker": [
            {"title": "The Design of Everyday Things — Don Norman", "type": "book", "why": "Makes Chris a better product thinker"},
            {"title": "Hooked — Nir Eyal", "type": "book", "why": "Understanding habit-forming product design"},
            {"title": "Shop Class as Soulcraft — Matthew Crawford", "type": "book", "why": "Philosophy of making, craft, and meaning"},
        ],
        "parenting": [
            {"title": "The Tech-Wise Family — Andy Crouch", "type": "book", "why": "Practical formation in a digital age"},
            {"title": "Hold On to Your Kids — Gordon Neufeld", "type": "book", "why": "Attachment-first approach to raising kids"},
        ],
        "technology": [
            {"title": "The Pragmatic Programmer — Hunt & Thomas", "type": "book", "why": "Evergreen principles for building well"},
            {"title": "A Philosophy of Software Design — John Ousterhout", "type": "book", "why": "Complexity as the enemy"},
        ],
    }

    def __init__(self, store: GrowthStore) -> None:
        self._store = store

    def get_reading_list(self, status: str | None = None) -> list[LearningItem]:
        items = self._store.load_learning()
        if status:
            items = [i for i in items if i.status == status]
        return items

    def add_learning_item(self, item: LearningItem) -> None:
        items = self._store.load_learning()
        # Avoid duplicates by item_id
        items = [i for i in items if i.item_id != item.item_id]
        items.append(item)
        self._store.save_learning(items)

    def log_completion(self, item_id: str, rating: int, takeaway: str) -> None:
        items = self._store.load_learning()
        for item in items:
            if item.item_id == item_id:
                item.status = "completed"
                item.completed_at = _today()
                item.rating = max(1, min(5, rating))
                item.key_takeaway = takeaway
                break
        self._store.save_learning(items)

    def get_growth_snapshot(self) -> dict:
        """
        Current learning snapshot.
        """
        all_items = self._store.load_learning()
        today = date.today()
        month_start = today.replace(day=1).isoformat()

        in_progress = [i for i in all_items if i.status == "in_progress"]
        completed_this_month = [
            i for i in all_items
            if i.status == "completed" and i.completed_at >= month_start
        ]
        want_to_count = sum(1 for i in all_items if i.status == "want_to")

        # Dominant topics from completed items
        topic_counts: dict[str, int] = {}
        for item in all_items:
            if item.status == "completed":
                topic_counts[item.topic] = topic_counts.get(item.topic, 0) + 1
        dominant_topics = sorted(topic_counts, key=lambda t: topic_counts[t], reverse=True)[:3]

        # Nova recommendation: surface the highest-rated suggestion not already tracked
        tracked_titles = {i.title.lower() for i in all_items}
        recommendation = ""
        for topic in (dominant_topics or list(self.SUGGESTION_POOL.keys())):
            for suggestion in self.SUGGESTION_POOL.get(topic, []):
                if suggestion["title"].lower() not in tracked_titles:
                    recommendation = f"{suggestion['title']} — {suggestion['why']}"
                    break
            if recommendation:
                break
        if not recommendation:
            recommendation = "You're in good shape — add new topics to your list to get a fresh recommendation."

        # Streak: count consecutive days with activity
        recent_dates = sorted(
            {i.started_at[:10] for i in all_items if i.started_at}
            | {i.completed_at[:10] for i in all_items if i.completed_at},
            reverse=True,
        )
        streak = 0
        check = today
        for ds in recent_dates:
            try:
                d = date.fromisoformat(ds)
                if d == check:
                    streak += 1
                    check -= timedelta(days=1)
                elif d < check:
                    break
            except ValueError:
                continue

        return {
            "in_progress": [asdict(i) for i in in_progress],
            "completed_this_month": [asdict(i) for i in completed_this_month],
            "want_to_list": want_to_count,
            "dominant_topics": dominant_topics,
            "nova_recommendation": recommendation,
            "consistency_streak": streak,
        }

    def suggest_next_learning(self, current_focus: list[str] | None = None) -> list[dict]:
        """
        Curated suggestions based on Chris's profile and current learning.
        """
        tracked_titles = {i.title.lower() for i in self._store.load_learning()}
        topics = current_focus or list(self.SUGGESTION_POOL.keys())
        suggestions: list[dict] = []
        for topic in topics:
            for item in self.SUGGESTION_POOL.get(topic, []):
                if item["title"].lower() not in tracked_titles:
                    suggestions.append({"title": item["title"], "type": item["type"], "topic": topic, "why": item["why"]})
        return suggestions[:10]

    def get_weekly_learning_check(self) -> dict:
        snapshot = self.get_growth_snapshot()
        in_progress_count = len(snapshot["in_progress"])
        completed_count = len(snapshot["completed_this_month"])
        summary_parts = []
        if in_progress_count:
            summary_parts.append(f"{in_progress_count} item(s) in progress")
        if completed_count:
            summary_parts.append(f"{completed_count} completed this month")
        summary = "Nova: " + (", ".join(summary_parts) if summary_parts else "Learning list ready — pick something up this week.")
        return {
            "summary": summary,
            "in_progress": snapshot["in_progress"],
            "nova_recommendation": snapshot["nova_recommendation"],
            "consistency_streak": snapshot["consistency_streak"],
        }


# ---------------------------------------------------------------------------
# GamoraAgent — Relationship Intelligence Lead
# ---------------------------------------------------------------------------

class GamoraAgent:
    """
    Gamora: direct, loyal, protective of what matters.
    Makes sure the people worth keeping get Chris's attention.
    "The ones worth keeping deserve your attention."
    """

    def __init__(self, store: GrowthStore) -> None:
        self._store = store

    def get_relationship_dashboard(self) -> dict:
        overdue = [asdict(c) for c in self.get_overdue_contacts()]
        upcoming = self.get_upcoming_occasions(days=30)
        contacts = self._store.load_relationships()
        open_threads: list[dict] = []
        for c in contacts:
            for thread in c.open_threads:
                open_threads.append({"contact": c.name, "contact_id": c.contact_id, "thread": thread})

        gamora_note = "The ones worth keeping deserve your attention."
        if overdue:
            gamora_note = f"{len(overdue)} contact(s) overdue. Reach out — don't let the gap grow."
        elif upcoming:
            gamora_note = f"{len(upcoming)} occasion(s) coming up. Be ready."

        return {
            "overdue_contacts": overdue,
            "upcoming_occasions": upcoming,
            "open_threads": open_threads,
            "gamora_note": gamora_note,
        }

    def add_contact(self, rel: Relationship) -> None:
        contacts = self._store.load_relationships()
        contacts = [c for c in contacts if c.contact_id != rel.contact_id]
        contacts.append(rel)
        self._store.save_relationships(contacts)

    def update_contact(self, contact_id: str, **kwargs: Any) -> bool:
        contacts = self._store.load_relationships()
        found = False
        for contact in contacts:
            if contact.contact_id == contact_id:
                for key, value in kwargs.items():
                    if hasattr(contact, key):
                        setattr(contact, key, value)
                found = True
                break
        if found:
            self._store.save_relationships(contacts)
        return found

    def log_contact(self, contact_id: str, notes: str = "") -> None:
        contacts = self._store.load_relationships()
        for contact in contacts:
            if contact.contact_id == contact_id:
                contact.last_contact = _today()
                if notes:
                    existing = contact.notes.strip()
                    contact.notes = f"{existing}\n{_today()}: {notes}".strip()
                break
        self._store.save_relationships(contacts)

    def get_contact(self, contact_id: str) -> Relationship | None:
        for c in self._store.load_relationships():
            if c.contact_id == contact_id:
                return c
        return None

    def list_contacts(self, relationship_type: str | None = None) -> list[Relationship]:
        contacts = self._store.load_relationships()
        if relationship_type:
            contacts = [c for c in contacts if c.relationship_type == relationship_type]
        return contacts

    def get_overdue_contacts(self) -> list[Relationship]:
        """Contacts not reached in longer than their contact_frequency."""
        today = date.today()
        overdue: list[Relationship] = []
        for contact in self._store.load_relationships():
            freq_days = _frequency_days(contact.contact_frequency)
            if freq_days >= 9999:
                continue
            if not contact.last_contact:
                # Never contacted — treat as overdue if frequency is meaningful
                if freq_days < 9999:
                    overdue.append(contact)
                continue
            try:
                last = date.fromisoformat(contact.last_contact)
                elapsed = (today - last).days
                if elapsed > freq_days:
                    overdue.append(contact)
            except ValueError:
                pass
        return overdue

    def get_today_occasions(self) -> list[dict]:
        """Any birthdays/anniversaries today."""
        today_md = _today_md()
        results: list[dict] = []
        for contact in self._store.load_relationships():
            if contact.birthday == today_md:
                results.append({
                    "type": "birthday",
                    "contact": contact.name,
                    "contact_id": contact.contact_id,
                    "message": f"Today is {contact.name}'s birthday!",
                })
            if contact.anniversary and contact.anniversary == today_md:
                results.append({
                    "type": "anniversary",
                    "contact": contact.name,
                    "contact_id": contact.contact_id,
                    "message": f"Today is {contact.name}'s anniversary!",
                })
        return results

    def get_upcoming_occasions(self, days: int = 30) -> list[dict]:
        """Occasions in the next N days with gift ideas."""
        results: list[dict] = []
        for contact in self._store.load_relationships():
            for occ_type, date_str in [("birthday", contact.birthday), ("anniversary", contact.anniversary)]:
                if not date_str:
                    continue
                days_until = _days_until_md(date_str)
                if 0 < days_until <= days:
                    results.append({
                        "type": occ_type,
                        "contact": contact.name,
                        "contact_id": contact.contact_id,
                        "date": date_str,
                        "days_until": days_until,
                        "message": f"{contact.name}'s {occ_type} in {days_until} day(s)",
                    })
        results.sort(key=lambda x: x["days_until"])
        return results


# ---------------------------------------------------------------------------
# AgathaAgent — Occasions & Gift Intelligence
# ---------------------------------------------------------------------------

class AgathaAgent:
    """
    Agatha: always up to something — knows what people want before they say it.
    Surfaces occasions and gift intelligence so Chris never misses a moment.
    "I've been expecting this."
    """

    # Generic gift suggestions by interest
    _INTEREST_GIFTS: dict[str, list[dict]] = {
        "faith": [
            {"idea": "Devotional book from a trusted author", "why": "Something for their spiritual formation", "estimated_cost": "$15–25", "where": "Amazon or Christian bookstore"},
            {"idea": "Journaling Bible", "why": "Combines reflection and scripture", "estimated_cost": "$30–50", "where": "Amazon"},
        ],
        "reading": [
            {"idea": "Book from their favorite genre", "why": "Always appreciated by readers", "estimated_cost": "$15–20", "where": "Amazon or local bookstore"},
            {"idea": "Audible or Kindle credit", "why": "Lets them choose what they want next", "estimated_cost": "$25", "where": "Amazon"},
        ],
        "family": [
            {"idea": "Framed family photo", "why": "Personal and lasting", "estimated_cost": "$20–50", "where": "Shutterfly or local framer"},
            {"idea": "Family experience (dinner, outing)", "why": "Memory-making over things", "estimated_cost": "$50–100", "where": "Local"},
        ],
        "home": [
            {"idea": "Candle or home fragrance set", "why": "Creates atmosphere they enjoy", "estimated_cost": "$20–40", "where": "Amazon or HomeGoods"},
            {"idea": "Practical kitchen upgrade", "why": "Something they'll use every day", "estimated_cost": "$30–80", "where": "Amazon"},
        ],
        "outdoors": [
            {"idea": "National Parks pass", "why": "Opens up hundreds of destinations", "estimated_cost": "$80", "where": "nps.gov"},
            {"idea": "Quality outdoor gear item", "why": "Practical and intentional", "estimated_cost": "$40–100", "where": "REI or Amazon"},
        ],
        "default": [
            {"idea": "Experience together", "why": "Presence is the best gift", "estimated_cost": "Varies", "where": "Depends on experience"},
            {"idea": "Handwritten note + meaningful item", "why": "Personal attention stands out", "estimated_cost": "$20–50", "where": "Local"},
            {"idea": "Amazon gift card with a personal note", "why": "Lets them choose what they need most", "estimated_cost": "$50", "where": "Amazon"},
        ],
    }

    def __init__(self, store: GrowthStore) -> None:
        self._store = store
        self._gamora = GamoraAgent(store)

    def get_occasions_calendar(self, days_ahead: int = 60) -> list[Occasion]:
        occasions = self._store.load_occasions()
        upcoming: list[Occasion] = []
        for occ in occasions:
            if not occ.active:
                continue
            days = _days_until_date(occ.date)
            if 0 <= days <= days_ahead:
                upcoming.append(occ)
        upcoming.sort(key=lambda o: _days_until_date(o.date))
        return upcoming

    def add_occasion(self, occasion: Occasion) -> None:
        occasions = self._store.load_occasions()
        occasions = [o for o in occasions if o.occasion_id != occasion.occasion_id]
        occasions.append(occasion)
        self._store.save_occasions(occasions)

    def get_gift_suggestions(
        self,
        contact_id: str,
        budget_usd: float | None = None,
        occasion_type: str | None = None,
    ) -> list[dict]:
        """
        Suggest gifts based on contact's shared interests and gift history.
        """
        contact = self._gamora.get_contact(contact_id)
        if contact is None:
            return self._INTEREST_GIFTS["default"]

        suggestions: list[dict] = []
        already_given = set()

        # Gather gift history from occasions for this contact
        for occ in self._store.load_occasions():
            if occ.contact_id == contact_id:
                for hist in occ.gift_history:
                    already_given.add(str(hist.get("gift", "")).lower())

        # Pull suggestions by shared interests
        for interest in contact.shared_interests:
            for suggestion in self._INTEREST_GIFTS.get(interest, []):
                if suggestion["idea"].lower() not in already_given:
                    suggestions.append(suggestion)

        if not suggestions:
            suggestions = list(self._INTEREST_GIFTS["default"])

        # Budget filter
        if budget_usd is not None:
            def _within_budget(s: dict) -> bool:
                cost = s.get("estimated_cost", "")
                if not isinstance(cost, str):
                    return True
                if "Varies" in cost:
                    return True
                try:
                    # Parse the high end of range like "$20–40"
                    parts = cost.replace("$", "").replace(",", "").split("–")
                    high = float(parts[-1].strip())
                    return high <= budget_usd
                except (ValueError, IndexError):
                    return True
            suggestions = [s for s in suggestions if _within_budget(s)]

        return suggestions[:5]

    def log_gift_given(
        self,
        contact_id: str,
        occasion_id: str,
        gift: str,
        notes: str = "",
    ) -> None:
        occasions = self._store.load_occasions()
        for occ in occasions:
            if occ.occasion_id == occasion_id and occ.contact_id == contact_id:
                occ.gift_history.append({
                    "year": date.today().year,
                    "gift": gift,
                    "notes": notes,
                })
                break
        self._store.save_occasions(occasions)

    def get_upcoming_occasions(self, days: int = 30) -> list[dict]:
        """Formatted occasions with days-until and gift suggestions."""
        results: list[dict] = []
        for occ in self.get_occasions_calendar(days_ahead=days):
            days_until = _days_until_date(occ.date)
            gifts = self.get_gift_suggestions(occ.contact_id, occasion_type=occ.occasion_type) if occ.contact_id else []
            contact = self._gamora.get_contact(occ.contact_id) if occ.contact_id else None
            results.append({
                "occasion_id": occ.occasion_id,
                "title": occ.title,
                "occasion_type": occ.occasion_type,
                "contact_name": contact.name if contact else "",
                "date": occ.date,
                "days_until": days_until,
                "gift_ideas": occ.gift_ideas[:3],
                "gift_suggestions": gifts[:3],
                "notes": occ.notes,
            })
        return results

    def check_today_occasions(self) -> list[dict]:
        """Any occasions today that need immediate action."""
        today_md = _today_md()
        today_full = _today()
        results: list[dict] = []
        for occ in self._store.load_occasions():
            if not occ.active:
                continue
            matches = False
            if occ.recurring and occ.date == today_md:
                matches = True
            elif not occ.recurring and occ.date == today_full:
                matches = True
            if matches:
                contact = self._gamora.get_contact(occ.contact_id) if occ.contact_id else None
                results.append({
                    "occasion_id": occ.occasion_id,
                    "title": occ.title,
                    "occasion_type": occ.occasion_type,
                    "contact_name": contact.name if contact else "",
                    "message": f"TODAY: {occ.title}" + (f" for {contact.name}" if contact else ""),
                })
        return results


# ---------------------------------------------------------------------------
# SpiderManAgent — World Signal & Intelligence Monitor
# ---------------------------------------------------------------------------

class SpiderManAgent:
    """
    Spider-Man: spider-sense for what matters in the world.
    Watches industry signals, news, and opportunities so Chris doesn't have to.
    "My spider-sense went off."
    """

    WATCHED_TOPICS = [
        "AI publishing tools",
        "self-publishing industry news",
        "3D printing technology",
        "laser cutting CNC news",
        "faith and culture",
        "Boy Scouts of America",
        "personal productivity tools",
        "content creator economy",
        "passive income strategies",
    ]

    # Keywords for relevance scoring (topic → keyword set)
    _TOPIC_KEYWORDS: dict[str, set[str]] = {
        "AI publishing tools": {"ai", "artificial intelligence", "publishing", "book", "author", "manuscript", "writing tool", "llm"},
        "self-publishing industry news": {"self-publishing", "indie author", "amazon kdp", "kindle", "print on demand", "isbn", "royalt"},
        "3D printing technology": {"3d print", "fdm", "resin", "filament", "creality", "bambu", "sla", "msla", "stl"},
        "laser cutting CNC news": {"laser", "cnc", "router", "engraving", "cutting", "lightburn", "falcon"},
        "faith and culture": {"faith", "church", "christian", "bible", "gospel", "theology", "spiritual"},
        "Boy Scouts of America": {"boy scouts", "bsa", "scouting", "scout", "merit badge", "eagle scout"},
        "personal productivity tools": {"productivity", "workflow", "automation", "notion", "obsidian", "second brain", "pkm"},
        "content creator economy": {"creator", "youtube", "podcast", "substack", "newsletter", "monetize", "content"},
        "passive income strategies": {"passive income", "revenue stream", "royalt", "digital product", "recurring revenue", "affiliate"},
    }

    def __init__(self, store: GrowthStore) -> None:
        self._store = store

    def get_signals(self, limit: int = 10) -> list[WorldSignal]:
        """Get recent unread signals."""
        signals = self._store.load_signals()
        unread = [s for s in signals if not s.surfaced]
        # Sort by detected_at desc, then relevance desc
        unread.sort(key=lambda s: (s.detected_at, s.relevance_score), reverse=True)
        return unread[:limit]

    def log_signal(self, signal: WorldSignal) -> None:
        if not signal.detected_at:
            signal.detected_at = _now_iso()
        self._store.append_signal(signal)

    def mark_surfaced(self, signal_id: str) -> None:
        self._store.update_signal(signal_id, surfaced=True)

    def _score_relevance(self, text: str) -> tuple[float, str]:
        """
        Score a headline/text for relevance to Chris's watched topics.
        Returns (score, matched_topic).
        """
        text_lower = text.lower()
        best_score = 0.0
        best_topic = "general"
        for topic, keywords in self._TOPIC_KEYWORDS.items():
            matches = sum(1 for kw in keywords if kw in text_lower)
            score = min(1.0, matches / max(1, len(keywords) * 0.3))
            if score > best_score:
                best_score = score
                best_topic = topic
        return best_score, best_topic

    def ingest_from_news_connector(self, headlines: dict) -> int:
        """
        Takes output from NewsConnector.get_headlines() and converts relevant
        headlines to WorldSignals. Returns count added.
        """
        items = headlines.get("headlines", [])
        if not isinstance(items, list):
            return 0

        existing_titles = {s.title.lower() for s in self._store.load_signals()}
        added = 0

        for headline in items:
            if isinstance(headline, str):
                title = headline
                source = ""
                url = ""
            elif isinstance(headline, dict):
                title = str(headline.get("title", headline.get("text", ""))).strip()
                source = str(headline.get("source", ""))
                url = str(headline.get("url", ""))
            else:
                continue

            if not title or title.lower() in existing_titles:
                continue

            score, topic = self._score_relevance(title)
            if score < 0.1:
                continue  # not relevant enough

            signal = WorldSignal(
                signal_id=str(uuid.uuid4()),
                title=title,
                signal_type="news",
                topic=topic,
                summary=title,
                source=source,
                url=url,
                detected_at=_now_iso(),
                surfaced=False,
                relevance_score=round(score, 3),
                tags=[topic],
            )
            self.log_signal(signal)
            existing_titles.add(title.lower())
            added += 1

        return added

    def get_weekly_signals_report(self) -> dict:
        """Weekly signal digest for briefing."""
        all_signals = self._store.load_signals()
        one_week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        recent = [s for s in all_signals if s.detected_at >= one_week_ago]
        unread = [s for s in recent if not s.surfaced]

        top_signals = sorted(unread, key=lambda s: s.relevance_score, reverse=True)[:5]
        topic_counts: dict[str, int] = {}
        for s in recent:
            topic_counts[s.topic] = topic_counts.get(s.topic, 0) + 1

        return {
            "signals_this_week": len(recent),
            "unread": len(unread),
            "top_signals": [asdict(s) for s in top_signals],
            "top_topics": sorted(topic_counts, key=lambda t: topic_counts[t], reverse=True)[:3],
            "spiderman_note": (
                f"Spider-sense caught {len(unread)} unread signal(s) this week."
                if unread else "All signals reviewed. Nothing new in the web."
            ),
        }


# ---------------------------------------------------------------------------
# ThorAgent — Health & Fitness Steward
# ---------------------------------------------------------------------------

class ThorAgent:
    """
    Thor: health and physical readiness as mission preparation.
    "The body is worthy of the mission."
    """

    _ACTIVITY_SUGGESTIONS: list[dict] = [
        {"activity": "Walk", "duration_min": 20, "intensity": "light", "why": "Easy daily foundation — 20 minutes is enough to matter"},
        {"activity": "Bodyweight workout", "duration_min": 25, "intensity": "moderate", "why": "No equipment needed, builds consistency"},
        {"activity": "Run/jog", "duration_min": 30, "intensity": "vigorous", "why": "Best cardiovascular return per minute"},
        {"activity": "Yoga or stretching", "duration_min": 20, "intensity": "light", "why": "Recovery day choice — mobility matters"},
        {"activity": "Bike ride", "duration_min": 45, "intensity": "moderate", "why": "Good for active recovery and family time"},
        {"activity": "Hike", "duration_min": 60, "intensity": "moderate", "why": "Combines outdoor reset with real movement"},
    ]

    def __init__(self, store: GrowthStore) -> None:
        self._store = store

    def log_activity(self, log: HealthLog) -> None:
        if not log.log_id:
            log.log_id = str(uuid.uuid4())
        if not log.date:
            log.date = _today()
        self._store.append_health_log(log)

    def get_health_snapshot(self, actor_id: str = "chris") -> dict:
        logs = self._store.load_health_log(actor_id)
        today = date.today()
        week_start = (today - timedelta(days=7)).isoformat()

        week_logs = [lg for lg in logs if lg.date >= week_start]
        activities_this_week = sorted(week_logs, key=lambda lg: lg.date, reverse=True)

        # Streak: consecutive activity days
        activity_dates = sorted({lg.date for lg in logs}, reverse=True)
        streak = 0
        check = today
        for ds in activity_dates:
            try:
                d = date.fromisoformat(ds)
                if d == check:
                    streak += 1
                    check -= timedelta(days=1)
                elif d < check:
                    break
            except ValueError:
                continue

        # Stats
        total_active_minutes = sum(lg.duration_minutes for lg in week_logs)
        steps_list = [lg.steps for lg in week_logs if lg.steps]
        avg_steps = int(sum(steps_list) / len(steps_list)) if steps_list else 0

        # Last activity
        last_activity = activities_this_week[0].date if activities_this_week else ""
        days_since_last = (today - date.fromisoformat(last_activity)).days if last_activity else 99

        # Readiness assessment (compassionate)
        if days_since_last == 0:
            readiness = "strong"
            thor_note = "You moved today. The body is worthy of the mission."
        elif days_since_last == 1:
            readiness = "good"
            thor_note = "Good momentum — keep the streak alive today."
        elif days_since_last == 2:
            readiness = "moderate"
            thor_note = "Two days rest. Today is a good day to move, even just a walk."
        elif days_since_last == 3:
            readiness = "rest_day"
            thor_note = "Three days without movement. The mission needs a ready body — even 20 minutes counts."
        else:
            readiness = "rest_day"
            thor_note = f"{days_since_last} days since last activity. No judgment — just get started again. Any movement is worthy."

        needs_rest = streak >= 6  # Suggest rest if 6+ straight days

        return {
            "activity_streak_days": streak,
            "activities_this_week": [asdict(lg) for lg in activities_this_week],
            "total_active_minutes_week": total_active_minutes,
            "avg_daily_steps": avg_steps,
            "sleep_avg_hours": 0.0,  # Placeholder — HealthKit integration future
            "readiness": readiness,
            "thor_note": thor_note,
            "needs_rest": needs_rest,
            "last_activity": last_activity,
        }

    def check_health_drift(self) -> dict | None:
        """
        If no activity logged in 3+ days, return a drift item. Otherwise None.
        """
        snapshot = self.get_health_snapshot()
        last = snapshot.get("last_activity", "")
        if not last:
            return {
                "text": "No activity logged yet. Thor suggests starting simple — even a 20-minute walk.",
                "severity": "info",
                "agent": "Thor",
            }
        try:
            days_since = (date.today() - date.fromisoformat(last)).days
        except ValueError:
            return None
        if days_since >= 3:
            return {
                "text": snapshot["thor_note"],
                "severity": "warning" if days_since >= 5 else "info",
                "agent": "Thor",
            }
        return None

    def get_activity_suggestions(self, available_minutes: int = 30) -> list[dict]:
        """Suggest activities based on time available and recent history."""
        suggestions = [
            s for s in self._ACTIVITY_SUGGESTIONS
            if s["duration_min"] <= available_minutes
        ]
        return suggestions[:4]

    def get_weekly_health_check(self) -> dict:
        snapshot = self.get_health_snapshot()
        return {
            "summary": f"Thor: {snapshot['thor_note']}",
            "activity_streak_days": snapshot["activity_streak_days"],
            "total_active_minutes_week": snapshot["total_active_minutes_week"],
            "readiness": snapshot["readiness"],
            "activities_this_week": len(snapshot["activities_this_week"]),
        }


# ---------------------------------------------------------------------------
# GrowthIntelligenceOrchestrator
# ---------------------------------------------------------------------------

class GrowthIntelligenceOrchestrator:
    """
    Unified orchestrator for all five growth agents.
    Used by the briefing builder, scheduler, and API.
    """

    def __init__(self, store: GrowthStore) -> None:
        self._store = store
        self.nova = NovaAgent(store)
        self.gamora = GamoraAgent(store)
        self.agatha = AgathaAgent(store)
        self.spider_man = SpiderManAgent(store)
        self.thor = ThorAgent(store)

    def daily_growth_check(self) -> dict:
        """
        Daily check across all growth agents.
        Returns structured report; urgent items go into needs_items.
        """
        # Occasions today
        today_occasions = self.agatha.check_today_occasions()

        # Overdue contacts
        overdue = self.gamora.get_overdue_contacts()

        # Health drift
        drift = self.thor.check_health_drift()

        # Unread signals
        signals = self.spider_man.get_signals(limit=5)

        needs_items: list[dict] = []
        for occ in today_occasions:
            needs_items.append({
                "text": occ["message"],
                "agent": "Agatha",
                "action_type": "occasion",
                "payload": {"occasion_id": occ.get("occasion_id"), "contact_id": occ.get("contact_id", "")},
            })

        drift_items: list[dict] = []
        for contact in overdue[:3]:
            drift_items.append({
                "text": f"Overdue: Reach out to {contact.name} (last contact: {contact.last_contact or 'never'})",
                "severity": "info",
                "agent": "Gamora",
            })
        if drift:
            drift_items.append(drift)

        return {
            "today_occasions": today_occasions,
            "overdue_contacts": [asdict(c) for c in overdue],
            "health_drift": drift,
            "new_signals": [asdict(s) for s in signals],
            "needs_items": needs_items,
            "drift_items": drift_items,
            "checked_at": _now_iso(),
        }

    def weekly_growth_check(self) -> dict:
        """
        Weekly comprehensive review for all growth agents.
        """
        return {
            "learning": self.nova.get_weekly_learning_check(),
            "relationships": self.gamora.get_relationship_dashboard(),
            "occasions": self.agatha.get_upcoming_occasions(days=30),
            "signals": self.spider_man.get_weekly_signals_report(),
            "health": self.thor.get_weekly_health_check(),
            "checked_at": _now_iso(),
        }

    def get_briefing_items(self) -> list[dict]:
        """
        Surface growth intelligence into the morning briefing.

        Returns a list of items in BriefingBuilder format:
          - "type": "briefing_item" | "drift_item"
          - "text": str
          - "sub": list[str]
          - "priority": str
          - "agent": str
          - Other keys as needed
        """
        items: list[dict] = []

        # Upcoming occasions in 7 days → high priority briefing items
        upcoming = self.agatha.get_upcoming_occasions(days=7)
        for occ in upcoming:
            items.append({
                "type": "briefing_item",
                "text": f"{occ['title']} in {occ['days_until']} day(s)",
                "sub": [f"Gift idea: {occ['gift_ideas'][0]}" if occ["gift_ideas"] else "Plan something thoughtful"],
                "priority": "high",
                "agent": "Agatha",
            })

        # Today's occasions → needs items (urgent)
        today_occs = self.agatha.check_today_occasions()
        for occ in today_occs:
            items.append({
                "type": "needs_item",
                "text": occ["message"],
                "sub": [],
                "priority": "high",
                "agent": "Agatha",
                "action_type": "occasion",
                "payload": {"occasion_id": occ.get("occasion_id", "")},
            })

        # Overdue contacts → drift items
        overdue = self.gamora.get_overdue_contacts()
        for contact in overdue[:2]:
            items.append({
                "type": "drift_item",
                "text": f"Reach out to {contact.name} — last contact: {contact.last_contact or 'never'}",
                "severity": "info",
                "agent": "Gamora",
            })

        # Good signal/article → normal briefing item
        top_signals = self.spider_man.get_signals(limit=2)
        for signal in top_signals:
            items.append({
                "type": "briefing_item",
                "text": f"Signal: {signal.title}",
                "sub": [f"Topic: {signal.topic}"],
                "priority": "normal",
                "agent": "Spider-Man",
            })

        # Health drift → drift item
        health_drift = self.thor.check_health_drift()
        if health_drift:
            items.append({
                "type": "drift_item",
                "text": health_drift["text"],
                "severity": health_drift.get("severity", "info"),
                "agent": "Thor",
            })

        return items

    def get_dashboard_status(self) -> dict:
        """For the Already Working zone on the dashboard."""
        snapshot = self.nova.get_growth_snapshot()
        health = self.thor.get_health_snapshot()
        overdue_count = len(self.gamora.get_overdue_contacts())
        upcoming_occasions = self.agatha.get_upcoming_occasions(days=14)

        return {
            "learning_in_progress": len(snapshot["in_progress"]),
            "learning_streak": snapshot["consistency_streak"],
            "nova_recommendation": snapshot["nova_recommendation"],
            "overdue_contacts": overdue_count,
            "upcoming_occasions": len(upcoming_occasions),
            "next_occasion": upcoming_occasions[0] if upcoming_occasions else None,
            "health_readiness": health["readiness"],
            "thor_note": health["thor_note"],
            "activity_streak": health["activity_streak_days"],
        }

    def ingest_news_signals(self) -> int:
        """Pull from NewsConnector and add relevant signals."""
        try:
            from .data_connectors import get_aggregator
            agg = get_aggregator()
            if agg is None:
                return 0
            headlines = agg.news.get_headlines()
            return self.spider_man.ingest_from_news_connector(headlines)
        except Exception:
            return 0


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_growth_singleton: GrowthIntelligenceOrchestrator | None = None


def init_growth(runtime: Any = None) -> GrowthIntelligenceOrchestrator:
    """Initialize (or return) the module-level growth orchestrator singleton."""
    global _growth_singleton
    if _growth_singleton is not None:
        return _growth_singleton
    store = GrowthStore()
    _growth_singleton = GrowthIntelligenceOrchestrator(store)
    return _growth_singleton


def get_growth() -> GrowthIntelligenceOrchestrator | None:
    """Return the growth orchestrator singleton if initialized."""
    return _growth_singleton
