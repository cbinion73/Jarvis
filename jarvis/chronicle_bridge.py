"""
chronicle_bridge.py — Epic 9: Chronicle Integration Bridge

Manages bidirectional context flow between JARVIS and Chronicle,
Chris's faith journal and reflection app.

JARVIS → Chronicle:
  - Daily reflection prompt (One Above All prepares contextual reflection)
  - Gratitude capture (expressions of gratitude detected in conversation)
  - Prayer request packaging (a concern structured for prayer)
  - Milestone recording (significant family or personal events)
  - Scripture connection (life events mapped to a passage)

Chronicle → JARVIS:
  - Formation memory (current study, prayer focus)
  - Answered prayer notifications (surface in morning briefing)
  - Spiritual timeline data (morning brief spiritual context)

Disciple (agent_id: chronicle-curator) — guardian of spiritual continuity
and legacy — orchestrates this integration on behalf of Chris and the
formation-director (One Above All).
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from .data_hygiene import filter_records

logger = logging.getLogger("jarvis.chronicle_bridge")

# ---------------------------------------------------------------------------
# Scripture reference data — inline so always available offline
# ---------------------------------------------------------------------------

SCRIPTURE_BY_THEME: dict[str, list[dict]] = {
    "anxiety": [
        {
            "ref": "Philippians 4:6-7",
            "text": (
                "Do not be anxious about anything, but in every situation, by prayer and petition, "
                "with thanksgiving, present your requests to God. And the peace of God, which transcends "
                "all understanding, will guard your hearts and your minds in Christ Jesus."
            ),
        },
        {
            "ref": "Matthew 6:34",
            "text": (
                "Therefore do not worry about tomorrow, for tomorrow will worry about itself. "
                "Each day has enough trouble of its own."
            ),
        },
    ],
    "provision": [
        {
            "ref": "Philippians 4:19",
            "text": "And my God will meet all your needs according to the riches of his glory in Christ Jesus.",
        },
        {
            "ref": "Matthew 6:33",
            "text": (
                "But seek first his kingdom and his righteousness, and all these things will be given to you as well."
            ),
        },
    ],
    "strength": [
        {
            "ref": "Isaiah 40:31",
            "text": (
                "But those who hope in the Lord will renew their strength. They will soar on wings like eagles; "
                "they will run and not grow weary, they will walk and not be faint."
            ),
        },
        {
            "ref": "Philippians 4:13",
            "text": "I can do all this through him who gives me strength.",
        },
    ],
    "peace": [
        {
            "ref": "John 14:27",
            "text": (
                "Peace I leave with you; my peace I give you. I do not give to you as the world gives. "
                "Do not let your hearts be troubled and do not be afraid."
            ),
        },
        {
            "ref": "Isaiah 26:3",
            "text": "You will keep in perfect peace those whose minds are steadfast, because they trust in you.",
        },
    ],
    "wisdom": [
        {
            "ref": "James 1:5",
            "text": (
                "If any of you lacks wisdom, you should ask God, who gives generously to all without finding fault, "
                "and it will be given to you."
            ),
        },
        {
            "ref": "Proverbs 3:5-6",
            "text": (
                "Trust in the Lord with all your heart and lean not on your own understanding; "
                "in all your ways submit to him, and he will make your paths straight."
            ),
        },
    ],
    "family": [
        {
            "ref": "Joshua 24:15",
            "text": "But as for me and my household, we will serve the Lord.",
        },
        {
            "ref": "Proverbs 22:6",
            "text": (
                "Start children off on the way they should go, "
                "and even when they are old they will not turn from it."
            ),
        },
    ],
    "faith": [
        {
            "ref": "Hebrews 11:1",
            "text": "Now faith is confidence in what we hope for and assurance about what we do not see.",
        },
        {
            "ref": "Romans 8:28",
            "text": (
                "And we know that in all things God works for the good of those who love him, "
                "who have been called according to his purpose."
            ),
        },
    ],
    "purpose": [
        {
            "ref": "Jeremiah 29:11",
            "text": (
                "For I know the plans I have for you, declares the Lord, plans to prosper you and not to harm you, "
                "plans to give you hope and a future."
            ),
        },
        {
            "ref": "Ephesians 2:10",
            "text": (
                "For we are God's handiwork, created in Christ Jesus to do good works, "
                "which God prepared in advance for us to do."
            ),
        },
    ],
    "gratitude": [
        {
            "ref": "1 Thessalonians 5:16-18",
            "text": (
                "Rejoice always, pray continually, give thanks in all circumstances; "
                "for this is God's will for you in Christ Jesus."
            ),
        },
        {
            "ref": "Psalm 100:4",
            "text": (
                "Enter his gates with thanksgiving and his courts with praise; "
                "give thanks to him and praise his name."
            ),
        },
    ],
    "leadership": [
        {
            "ref": "Mark 10:45",
            "text": (
                "For even the Son of Man did not come to be served, but to serve, "
                "and to give his life as a ransom for many."
            ),
        },
        {
            "ref": "Proverbs 11:14",
            "text": (
                "For lack of guidance a nation falls, but victory is won through many advisers."
            ),
        },
    ],
    "trust": [
        {
            "ref": "Proverbs 3:5-6",
            "text": (
                "Trust in the Lord with all your heart and lean not on your own understanding; "
                "in all your ways submit to him, and he will make your paths straight."
            ),
        },
        {
            "ref": "Psalm 56:3",
            "text": "When I am afraid, I put my trust in you.",
        },
    ],
    "hope": [
        {
            "ref": "Romans 15:13",
            "text": (
                "May the God of hope fill you with all joy and peace as you trust in him, "
                "so that you may overflow with hope by the power of the Holy Spirit."
            ),
        },
        {
            "ref": "Lamentations 3:22-23",
            "text": (
                "Because of the Lord's great love we are not consumed, for his compassions never fail. "
                "They are new every morning; great is your faithfulness."
            ),
        },
    ],
    "grief": [
        {
            "ref": "Psalm 34:18",
            "text": "The Lord is close to the brokenhearted and saves those who are crushed in spirit.",
        },
        {
            "ref": "Matthew 5:4",
            "text": "Blessed are those who mourn, for they will be comforted.",
        },
    ],
}

# Keyword → theme mapping (ordered from most specific to broadest so first
# match wins)
_THEME_KEYWORDS: list[tuple[str, str]] = [
    # anxiety / worry first — before "peace" which overlaps
    (r"\b(anxious|anxiety|worried|worry|stress|stressed|overwhelm)\b", "anxiety"),
    (r"\b(provid|provision|finances|money|needs|bills)\b", "provision"),
    (r"\b(strength|tired|exhausted|worn|weary|weak)\b", "strength"),
    (r"\b(peace|calm|rest|still|quiet)\b", "peace"),
    (r"\b(wisdom|decision|discern|direction|counsel|choose)\b", "wisdom"),
    (r"\b(family|household|children|kids|marriage|spouse|wife|husband|parenting)\b", "family"),
    (r"\b(faith|believe|trust|doubt|uncertain)\b", "faith"),
    (r"\b(purpose|calling|vocation|mission|meaning|why)\b", "purpose"),
    (r"\b(grateful|gratitude|thankful|blessed|thank)\b", "gratitude"),
    (r"\b(lead|leader|leadership|manage|team|influence)\b", "leadership"),
    (r"\b(hope|future|promise|waiting)\b", "hope"),
    (r"\b(grief|loss|mourn|sad|heartbreak|hard)\b", "grief"),
    (r"\b(trust)\b", "trust"),
]

# Gratitude patterns for `capture_gratitude` detection
_GRATITUDE_PATTERNS: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"\bthank\s+God\b",
        r"\bthankful\s+for\b",
        r"\bI'?m?\s+grateful\b",
        r"\bso\s+grateful\b",
        r"\bblessed\b",
        r"\bGod\s+provided\b",
        r"\bGod\s+came\s+through\b",
        r"\bGod\s+is\s+good\b",
        r"\bpraise\s+(God|the Lord|Jesus|Him)\b",
        r"\bthankfulness\b",
        r"\bgratitude\b",
        r"\bGod\s+answered\b",
        r"\bprayer\s+answered\b",
    ]
]

# Prayer / concern patterns for `package_prayer_request` auto-detection
_CONCERN_PATTERNS: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"\bplease\s+pray\b",
        r"\bneed\s+(prayer|God'?s?\s+help)\b",
        r"\bask\s+(God|Jesus|the Lord)\b",
        r"\bworried\s+about\b",
        r"\bstruggling\s+with\b",
        r"\bI\s+don'?t\s+know\s+what\s+to\s+do\b",
    ]
]


def find_scripture_for_context(context_text: str) -> dict | None:
    """
    Simple keyword matching to find a relevant Scripture for a given context.

    Returns {"ref": str, "text": str, "theme": str} or None.
    The first matching theme wins; within a theme the first passage is returned.
    """
    lower = context_text.lower()
    for pattern, theme in _THEME_KEYWORDS:
        if re.search(pattern, lower):
            passages = SCRIPTURE_BY_THEME.get(theme, [])
            if passages:
                passage = passages[0]
                return {"ref": passage["ref"], "text": passage["text"], "theme": theme}
    return None


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ChronicleEntry:
    """A structured context packet for Chronicle."""

    entry_id: str               # uuid4
    entry_type: str             # "reflection" | "prayer" | "scripture" | "formation"
                                # | "milestone" | "gratitude" | "insight"
    title: str
    body: str                   # main text
    scripture_ref: str          # e.g. "Philippians 4:6-7" (optional)
    scripture_text: str         # the actual verse text (optional)
    themes: list[str]           # ["peace", "trust", "provision"]
    actor_id: str               # "chris"
    created_at: str
    source: str                 # "jarvis_suggested" | "user_initiated" | "auto_captured"
    mood: str                   # "grateful" | "struggling" | "hopeful" | "peaceful"
                                # | "uncertain" | "joyful"
    linked_events: list[str]    # event IDs this is connected to
    tags: list[str]
    sent_to_chronicle: bool     # has this been pushed to Chronicle?
    sent_at: str

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ChronicleEntry":
        return cls(
            entry_id=str(data.get("entry_id", str(uuid.uuid4()))),
            entry_type=str(data.get("entry_type", "reflection")),
            title=str(data.get("title", "")),
            body=str(data.get("body", "")),
            scripture_ref=str(data.get("scripture_ref", "")),
            scripture_text=str(data.get("scripture_text", "")),
            themes=list(data.get("themes", [])),
            actor_id=str(data.get("actor_id", "chris")),
            created_at=str(data.get("created_at", _now_iso())),
            source=str(data.get("source", "jarvis_suggested")),
            mood=str(data.get("mood", "hopeful")),
            linked_events=list(data.get("linked_events", [])),
            tags=list(data.get("tags", [])),
            sent_to_chronicle=bool(data.get("sent_to_chronicle", False)),
            sent_at=str(data.get("sent_at", "")),
        )


@dataclass
class ChroniclePatternInsight:
    """A spiritual pattern JARVIS noticed across Chronicle entries."""

    insight_id: str
    pattern_type: str       # "theme_recurrence" | "answer_to_prayer"
                            # | "growth_marker" | "struggle_pattern"
    title: str
    description: str        # "You've been praying about provision for 6 weeks…"
    evidence: list[str]     # entry IDs or descriptions supporting the insight
    scripture_connections: list[str]
    detected_at: str
    surfaced_to_user: bool

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ChroniclePatternInsight":
        return cls(
            insight_id=str(data.get("insight_id", str(uuid.uuid4()))),
            pattern_type=str(data.get("pattern_type", "theme_recurrence")),
            title=str(data.get("title", "")),
            description=str(data.get("description", "")),
            evidence=list(data.get("evidence", [])),
            scripture_connections=list(data.get("scripture_connections", [])),
            detected_at=str(data.get("detected_at", _now_iso())),
            surfaced_to_user=bool(data.get("surfaced_to_user", False)),
        )


# ---------------------------------------------------------------------------
# ChronicleSnapshotReader
# ---------------------------------------------------------------------------


class ChronicleSnapshotReader:
    """
    Reads the latest Chronicle snapshot from the ChronicleService data directory.
    Caches for 5 minutes. Thread-safe.

    Path resolution order:
      1. CHRONICLE_SNAPSHOT_DIR env var  (VPS / Docker volume mount)
      2. Mac default: ~/Library/Application Support/ChronicleService/…
    """
    _env_dir = os.environ.get("CHRONICLE_SNAPSHOT_DIR")
    SNAPSHOT_DIR = (
        Path(_env_dir)
        if _env_dir
        else Path.home() / "Library" / "Application Support" / "ChronicleService" / "app" / "data" / "sync-snapshots"
    )
    CACHE_TTL = 300  # seconds

    def __init__(self) -> None:
        self._cache: dict | None = None
        self._cache_at: float = 0.0
        self._lock = threading.Lock()

    def _latest_snapshot_path(self) -> Path | None:
        if not self.SNAPSHOT_DIR.exists():
            return None
        # Prefer dated snapshots (snapshot-YYYY-…) over legacy files; sort by name desc
        dated = sorted(
            [p for p in self.SNAPSHOT_DIR.glob("*.json") if p.stem.startswith("snapshot-20")],
            key=lambda p: p.name,
            reverse=True,
        )
        return dated[0] if dated else None

    def _load(self) -> dict:
        # Try dated snapshots newest-first until we find one with appState/chronicleEntries
        if not self.SNAPSHOT_DIR.exists():
            return {}
        dated = sorted(
            [p for p in self.SNAPSHOT_DIR.glob("*.json") if p.stem.startswith("snapshot-20")],
            key=lambda p: p.name,
            reverse=True,
        )
        for path in dated:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                state = data.get("appState", {})
                if state.get("chronicleEntries") is not None:
                    return state
            except Exception:
                continue
        return {}

    def _state(self) -> dict:
        now = time.time()
        with self._lock:
            if self._cache is None or (now - self._cache_at) > self.CACHE_TTL:
                self._cache = self._load()
                self._cache_at = now
            return self._cache

    def get_entries(self, limit: int = 20) -> list[dict]:
        entries = filter_records([dict(item) for item in self._state().get("chronicleEntries", []) if isinstance(item, dict)])
        # Sort by date descending
        try:
            entries = sorted(entries, key=lambda e: e.get("date", ""), reverse=True)
        except Exception:
            pass
        return entries[:limit]

    def get_prayer_items(self) -> list[dict]:
        return filter_records([dict(item) for item in self._state().get("prayerItems", []) if isinstance(item, dict)])

    def get_formation_rhythms(self) -> list[dict]:
        return self._state().get("formationRhythms", [])

    def get_owned_books(self) -> list[dict]:
        return self._state().get("ownedBooks", [])

    def search_entries(self, query: str, limit: int = 20) -> list[dict]:
        q = query.lower()
        entries = self.get_entries(limit=1000)
        results = []
        for e in entries:
            text = " ".join([
                e.get("title", ""),
                e.get("body", ""),
                e.get("passage", ""),
                " ".join(e.get("themes", [])),
            ]).lower()
            if q in text:
                results.append(e)
        return results[:limit]

    def quick_capture(self, entry_type: str, content: str, passage: str = "") -> dict:
        """
        Create a new Chronicle entry from a quick capture.
        Generates ID, title, timestamp automatically.
        Returns the new entry dict (does NOT write — caller does the write).
        """
        import time, uuid
        type_titles = {
            "gratitude": "Gratitude",
            "prayer": "Prayer request",
            "note": "Note",
            "milestone": "Milestone",
            "reflection": "Reflection",
            "insight": "Insight",
            "study": "Study note",
        }
        today = datetime.now().strftime("%Y-%m-%d")
        title_prefix = type_titles.get(entry_type, entry_type.capitalize())
        # Use first ~40 chars of content as title suffix
        short = content[:40].strip().rstrip(".,!?")
        title = f"{title_prefix} — {short}" if len(content) > 4 else title_prefix
        entry = {
            "id": str(uuid.uuid4()),
            "date": today,
            "type": entry_type,
            "title": title,
            "body": content,
            "autoCapture": False,
        }
        if passage:
            entry["passage"] = passage
        return entry

    def get_context(self) -> dict:
        """
        Return a compact spiritual context blob for the Morning Brief and conversation AI.
        Includes: current study passage, top 3 active prayer needs, today's formation rhythm,
        top 3 themes from recent entries, streak info.
        Never raises.
        """
        try:
            data = self.get_dashboard()
            if not data.get("ok"):
                return {"ok": False}

            entries = data.get("entries", [])
            prayers = data.get("prayer_items", [])
            rhythms = data.get("formation_rhythms", [])
            tags = data.get("tags", {})

            # Current study: most recent entry with a passage
            study_entry = next((e for e in entries if e.get("passage")), None)

            # Active prayers (top 3, unanswered)
            active_prayers = [p for p in prayers if not p.get("answered")][:3]

            # Today's rhythm: find the one scheduled for today (or first active)
            today = datetime.now().strftime("%A").lower()  # e.g. "monday"
            todays_rhythm = None
            for r in rhythms:
                days = [d.lower() for d in r.get("days", [])]
                if today in days or "daily" in days:
                    todays_rhythm = r
                    break
            if not todays_rhythm and rhythms:
                todays_rhythm = rhythms[0]

            # Top themes (sorted by count)
            top_themes = sorted(tags.items(), key=lambda x: x[1], reverse=True)[:5]

            return {
                "ok": True,
                "study": {
                    "passage": study_entry.get("passage") if study_entry else None,
                    "title": study_entry.get("title") if study_entry else None,
                    "date": study_entry.get("date") if study_entry else None,
                } if study_entry else None,
                "active_prayers": [
                    {"id": p.get("id"), "text": p.get("text"), "category": p.get("category")}
                    for p in active_prayers
                ],
                "todays_rhythm": {
                    "name": todays_rhythm.get("name") if todays_rhythm else None,
                    "description": todays_rhythm.get("description", "") if todays_rhythm else None,
                } if todays_rhythm else None,
                "top_themes": [t[0] for t in top_themes],
                "total_entries": data.get("total", 0),
                "active_prayer_count": data.get("active_prayers", 0),
                "answered_prayer_count": data.get("answered_prayers", 0),
            }
        except Exception as exc:
            import logging
            logging.getLogger("jarvis.chronicle_bridge").warning("get_context failed: %s", exc)
            return {"ok": False, "error": str(exc)}

    def get_patterns(self) -> dict:
        """
        Analyze the last 30 days of entries for patterns.
        Returns: recurring_themes, entry_type_breakdown, prayer_arcs, writing_streak.
        Never raises.
        """
        try:
            from collections import Counter
            from datetime import timedelta
            data = self.get_dashboard()
            if not data.get("ok"):
                return {"ok": False}

            entries = data.get("entries", [])
            prayers = data.get("prayer_items", [])
            cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            recent = [e for e in entries if e.get("date", "") >= cutoff]

            # Entry type breakdown
            type_counts = Counter(e.get("type", "note") for e in recent)

            # Recurring themes (from themes arrays)
            all_themes = []
            for e in recent:
                all_themes.extend(e.get("themes", []))
            theme_counts = Counter(all_themes)
            top_themes = [{"theme": t, "count": c} for t, c in theme_counts.most_common(8)]

            # Prayer-to-gratitude arcs: prayers that got answered in the window
            answered = [p for p in prayers if p.get("answered")]
            prayer_arc = {
                "total_active": len([p for p in prayers if not p.get("answered")]),
                "answered_total": len(answered),
                "answered_recent": len([p for p in answered
                                        if p.get("dateAnswered", "") >= cutoff]),
            }

            # Writing streak: count consecutive days with entries
            dates = sorted({e.get("date") for e in entries if e.get("date")}, reverse=True)
            streak = 0
            if dates:
                check = datetime.now()
                for d in dates:
                    if d == check.strftime("%Y-%m-%d") or d == (check - timedelta(days=1)).strftime("%Y-%m-%d"):
                        streak += 1
                        check = datetime.strptime(d, "%Y-%m-%d") - timedelta(days=1)
                    else:
                        break

            return {
                "ok": True,
                "window_days": 30,
                "total_recent_entries": len(recent),
                "entry_type_breakdown": dict(type_counts),
                "recurring_themes": top_themes,
                "prayer_arc": prayer_arc,
                "writing_streak_days": streak,
            }
        except Exception as exc:
            import logging
            logging.getLogger("jarvis.chronicle_bridge").warning("get_patterns failed: %s", exc)
            return {"ok": False, "error": str(exc)}

    def get_dashboard(self) -> dict:
        """Full dashboard payload for /api/chronicle/recent."""
        entries = self.get_entries(limit=20)
        prayers = self.get_prayer_items()
        rhythms = self.get_formation_rhythms()
        books = self.get_owned_books()

        active_prayers = [p for p in prayers if not p.get("answered")]
        answered_prayers = [p for p in prayers if p.get("answered")]

        # Collect themes from entries
        theme_counts: dict[str, int] = {}
        for e in entries:
            for t in e.get("themes", []):
                theme_counts[t] = theme_counts.get(t, 0) + 1
        tags = sorted(theme_counts.keys(), key=lambda t: -theme_counts[t])

        return {
            "ok": True,
            "entries": entries,
            "total": len(entries),
            "tags": tags,
            "prayer_items": prayers,
            "active_prayers": len(active_prayers),
            "answered_prayers": len(answered_prayers),
            "formation_rhythms": rhythms,
            "owned_books": books,
            "chronicle_available": self._latest_snapshot_path() is not None,
        }

    def invalidate_cache(self) -> None:
        with self._lock:
            self._cache = None
            self._cache_at = 0.0


# ---------------------------------------------------------------------------
# ChronicleBridge
# ---------------------------------------------------------------------------


class ChronicleBridge:
    """
    Manages bidirectional context flow between JARVIS and Chronicle.

    JARVIS → Chronicle flows:
    - Daily reflection prompt (One Above All prepares a contextual reflection)
    - Gratitude capture (when Chris expresses gratitude in conversation)
    - Prayer request packaging (when Chris mentions a need, structured for prayer)
    - Milestone recording (when significant family/personal events happen)
    - Scripture connection (when a life event connects to a passage)

    Chronicle → JARVIS flows:
    - Formation memory (Chronicle tells JARVIS what Chris is studying/praying about)
    - Prayer answered notifications (when an answered prayer is marked in Chronicle)
    - Spiritual timeline data (for morning brief spiritual context)

    Storage:
        ~/.jarvis/chronicle/entries/
        ~/.jarvis/chronicle/insights/
        ~/.jarvis/chronicle/pending_entries.jsonl
        ~/.jarvis/chronicle/formation_context.json
        ~/.jarvis/chronicle/answered_prayers.jsonl
    """

    ROOT = Path.home() / ".jarvis" / "chronicle"

    def __init__(self, chronicle_client: Any = None) -> None:
        self._chronicle_client = chronicle_client
        self._entries_dir = self.ROOT / "entries"
        self._insights_dir = self.ROOT / "insights"
        self._pending_path = self.ROOT / "pending_entries.jsonl"
        self._formation_path = self.ROOT / "formation_context.json"
        self._answered_path = self.ROOT / "answered_prayers.jsonl"
        self._ensure_dirs()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_dirs(self) -> None:
        for d in (self._entries_dir, self._insights_dir):
            d.mkdir(parents=True, exist_ok=True)

    def _entry_path(self, entry_id: str) -> Path:
        return self._entries_dir / f"{entry_id}.json"

    def _insight_path(self, insight_id: str) -> Path:
        return self._insights_dir / f"{insight_id}.json"

    def _write_json(self, path: Path, data: dict) -> None:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def _read_json(self, path: Path) -> dict | None:
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def _append_jsonl(self, path: Path, data: dict) -> None:
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(data, ensure_ascii=False) + "\n")

    def _read_jsonl(self, path: Path) -> list[dict]:
        if not path.exists():
            return []
        lines: list[dict] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    lines.append(json.loads(line))
                except Exception:
                    pass
        return lines

    def _detect_themes(self, text: str) -> list[str]:
        """Extract matching theme labels from free text."""
        found: list[str] = []
        lower = text.lower()
        for pattern, theme in _THEME_KEYWORDS:
            if re.search(pattern, lower) and theme not in found:
                found.append(theme)
        return found

    def _infer_mood(self, themes: list[str], text: str) -> str:
        lower = text.lower()
        if any(t in themes for t in ("gratitude",)):
            return "grateful"
        if any(t in themes for t in ("grief", "anxiety")):
            if re.search(r"\bpeace|peaceful|calm\b", lower):
                return "peaceful"
            return "struggling"
        if any(t in themes for t in ("hope", "faith", "purpose")):
            return "hopeful"
        if any(t in themes for t in ("peace",)):
            return "peaceful"
        return "hopeful"

    # ------------------------------------------------------------------
    # JARVIS → Chronicle
    # ------------------------------------------------------------------

    def prepare_daily_reflection(
        self, actor_id: str = "chris", context: dict | None = None
    ) -> ChronicleEntry:
        """
        One Above All prepares a daily reflection prompt.

        Uses the morning context (what's happening today) to suggest a relevant
        Scripture and reflection question. The returned entry is complete and
        ready to use — not merely a Scripture reference.

        Pattern: Find a Scripture that speaks to today's challenges and
        opportunities; frame a reflection question that invites honest encounter
        with the text.
        """
        context = context or {}
        context_text = (
            context.get("summary", "")
            + " "
            + context.get("theme", "")
            + " "
            + context.get("notes", "")
        ).strip()

        scripture = find_scripture_for_context(context_text) if context_text else None

        # Graceful fallback: choose a passage based on the day of the week so
        # no two mornings feel identical even with no context.
        if scripture is None:
            day_index = datetime.now().weekday()  # 0 = Monday
            fallback_themes = [
                "purpose", "wisdom", "strength", "peace",
                "family", "gratitude", "faith",
            ]
            theme = fallback_themes[day_index % len(fallback_themes)]
            passages = SCRIPTURE_BY_THEME.get(theme, [])
            if passages:
                passage = passages[0]
                scripture = {"ref": passage["ref"], "text": passage["text"], "theme": theme}

        ref = scripture["ref"] if scripture else ""
        verse_text = scripture["text"] if scripture else ""
        theme_label = scripture["theme"] if scripture else "faith"

        # Compose a complete, ready-to-use reflection prompt
        reflection_question = _REFLECTION_QUESTIONS.get(
            theme_label,
            "Where have you seen God at work today, even in the ordinary moments?",
        )

        body_parts = [
            f"Scripture: {ref}",
            f'"{verse_text}"',
            "",
            "Reflection:",
            reflection_question,
            "",
            "Invitation: Sit quietly for a few moments. What word or phrase from this passage stays with you?",
        ]
        body = "\n".join(body_parts)

        title = f"Morning Reflection — {datetime.now().strftime('%A, %B %-d')}"

        entry = ChronicleEntry(
            entry_id=str(uuid.uuid4()),
            entry_type="reflection",
            title=title,
            body=body,
            scripture_ref=ref,
            scripture_text=verse_text,
            themes=[theme_label],
            actor_id=actor_id,
            created_at=_now_iso(),
            source="jarvis_suggested",
            mood="hopeful",
            linked_events=[],
            tags=["daily-reflection", "morning", theme_label],
            sent_to_chronicle=False,
            sent_at="",
        )
        self.save_entry_local(entry)
        return entry

    def capture_gratitude(
        self, text: str, context: dict | None = None
    ) -> "ChronicleEntry | None":
        """
        Detect expressions of gratitude in conversation text and package for
        Chronicle.

        Patterns: "thank God", "I'm grateful", "blessed", "thankful for",
        "God provided", and related phrases.

        Returns None if no gratitude is detected.
        """
        if not any(p.search(text) for p in _GRATITUDE_PATTERNS):
            return None

        themes = self._detect_themes(text)
        if "gratitude" not in themes:
            themes.insert(0, "gratitude")

        scripture = find_scripture_for_context(text)
        ref = scripture["ref"] if scripture else "1 Thessalonians 5:16-18"
        verse_text = scripture["text"] if scripture else SCRIPTURE_BY_THEME["gratitude"][0]["text"]

        # Derive a concise title from the first sentence of the text
        first_sentence = re.split(r"[.!?\n]", text.strip())[0][:80].strip()
        title = f"Gratitude — {first_sentence}" if first_sentence else "A Moment of Gratitude"

        entry = ChronicleEntry(
            entry_id=str(uuid.uuid4()),
            entry_type="gratitude",
            title=title,
            body=text.strip(),
            scripture_ref=ref,
            scripture_text=verse_text,
            themes=themes,
            actor_id=(context or {}).get("actor_id", "chris"),
            created_at=_now_iso(),
            source="auto_captured",
            mood="grateful",
            linked_events=[],
            tags=["gratitude"] + themes[:3],
            sent_to_chronicle=False,
            sent_at="",
        )
        self.save_entry_local(entry)
        return entry

    def package_prayer_request(
        self, concern: str, actor_id: str = "chris"
    ) -> ChronicleEntry:
        """
        Package a prayer request for Chronicle.
        Connects to relevant Scripture if a theme can be identified.
        """
        themes = self._detect_themes(concern)
        scripture = find_scripture_for_context(concern)

        ref = scripture["ref"] if scripture else ""
        verse_text = scripture["text"] if scripture else ""

        first_line = re.split(r"[.!?\n]", concern.strip())[0][:80].strip()
        title = f"Prayer — {first_line}" if first_line else "A Prayer Request"

        body_parts = [concern.strip()]
        if ref:
            body_parts += ["", f"Anchoring Scripture: {ref}", f'"{verse_text}"']

        entry = ChronicleEntry(
            entry_id=str(uuid.uuid4()),
            entry_type="prayer",
            title=title,
            body="\n".join(body_parts),
            scripture_ref=ref,
            scripture_text=verse_text,
            themes=themes or ["faith"],
            actor_id=actor_id,
            created_at=_now_iso(),
            source="user_initiated",
            mood=self._infer_mood(themes, concern),
            linked_events=[],
            tags=["prayer-request"] + themes[:3],
            sent_to_chronicle=False,
            sent_at="",
        )
        self.save_entry_local(entry)
        return entry

    def record_milestone(
        self,
        title: str,
        description: str,
        milestone_type: str = "family",
    ) -> ChronicleEntry:
        """
        Record a significant life event: graduation, answered prayer, major
        decision, family milestone.
        """
        themes = self._detect_themes(description)
        if milestone_type == "family" and "family" not in themes:
            themes.insert(0, "family")

        scripture = find_scripture_for_context(description)
        ref = scripture["ref"] if scripture else ""
        verse_text = scripture["text"] if scripture else ""

        entry = ChronicleEntry(
            entry_id=str(uuid.uuid4()),
            entry_type="milestone",
            title=title,
            body=description.strip(),
            scripture_ref=ref,
            scripture_text=verse_text,
            themes=themes,
            actor_id="chris",
            created_at=_now_iso(),
            source="user_initiated",
            mood="grateful",
            linked_events=[],
            tags=["milestone", milestone_type] + themes[:2],
            sent_to_chronicle=False,
            sent_at="",
        )
        self.save_entry_local(entry)
        return entry

    # ------------------------------------------------------------------
    # Chronicle → JARVIS
    # ------------------------------------------------------------------

    def receive_formation_memory(self, memory_data: dict) -> None:
        """
        Chronicle sends formation context (current study, prayer focus).
        Persisted locally and stored in the known_facts memory layer under
        the 'faith' domain.
        """
        # Persist formation context locally for offline retrieval
        try:
            existing = self._read_json(self._formation_path) or {}
            existing.update(memory_data)
            existing["updated_at"] = _now_iso()
            self._write_json(self._formation_path, existing)
        except Exception as exc:
            logger.warning("Could not persist formation memory: %s", exc)

        # Store as MemoryFacts in the Being Known layer
        try:
            from .known_facts import get_memory, MemoryFact  # type: ignore[import]
            store = get_memory()
            if store is not None:
                now = _now_iso()
                for key, value in memory_data.items():
                    if key in ("updated_at",) or not value:
                        continue
                    fact = MemoryFact(
                        fact_id=str(uuid.uuid4()),
                        domain="faith",
                        actor_id="chris",
                        key=f"chronicle_{key}",
                        value=str(value)[:500],
                        confidence=1.0,
                        source="system",
                        created_at=now,
                        updated_at=now,
                        expires_at="",
                        tags=["chronicle", "formation"],
                        last_surfaced_at="",
                        surface_count=0,
                        confirmed=True,
                    )
                    store.set_fact(fact)
                logger.debug("Formation memory stored: %d keys", len(memory_data))
        except Exception as exc:
            logger.debug("Could not store formation memory in known_facts: %s", exc)

    def receive_answered_prayer(self, prayer_data: dict) -> None:
        """
        When a prayer is marked answered in Chronicle, persist the event so
        it surfaces in the next JARVIS morning briefing.
        """
        prayer_data = dict(prayer_data)
        prayer_data.setdefault("received_at", _now_iso())
        prayer_data.setdefault("surfaced", False)

        try:
            self._append_jsonl(self._answered_path, prayer_data)
            logger.info(
                "Answered prayer received: %s",
                prayer_data.get("title", prayer_data.get("entry_id", "unknown")),
            )
        except Exception as exc:
            logger.warning("Could not persist answered prayer: %s", exc)

    def get_morning_spiritual_context(self, actor_id: str = "chris") -> dict:
        """
        Get spiritual context for the morning briefing:
        - Current study passage / theme
        - Active prayer requests (count)
        - Recent answered prayers
        - Pattern insights
        - A ready-to-use reflection prompt

        Returns a dict formatted for the briefing packet.
        """
        formation = self._read_json(self._formation_path) or {}

        # Count active (unsent) prayer entries
        pending = self.get_pending_entries()
        prayer_requests = [e for e in pending if e.entry_type == "prayer"]

        # Answered prayers not yet surfaced
        all_answered = self._read_jsonl(self._answered_path)
        unsurfaced_answers = [a for a in all_answered if not a.get("surfaced", False)]

        # Daily reflection
        try:
            reflection_entry = self.prepare_daily_reflection(
                actor_id=actor_id,
                context={"summary": formation.get("current_study", "")},
            )
            reflection_prompt = reflection_entry.body
            scripture_of_day = {
                "ref": reflection_entry.scripture_ref,
                "text": reflection_entry.scripture_text,
            }
        except Exception:
            reflection_prompt = ""
            scripture_of_day = {}

        # Top insight (most recently detected, not yet surfaced)
        insights = [i for i in self.get_insights() if not i.surfaced_to_user]
        top_insight = insights[0].description if insights else ""

        return {
            "current_study": formation.get("current_study", ""),
            "current_theme": formation.get("current_theme", ""),
            "prayer_count": len(prayer_requests),
            "answered_recently": [
                a.get("title", a.get("entry_id", "")) for a in unsurfaced_answers[:3]
            ],
            "reflection_prompt": reflection_prompt,
            "scripture_of_day": scripture_of_day,
            "top_insight": top_insight,
        }

    # ------------------------------------------------------------------
    # Pattern detection
    # ------------------------------------------------------------------

    def detect_patterns(
        self, entries: list[ChronicleEntry]
    ) -> list[ChroniclePatternInsight]:
        """
        Simple pattern detection over Chronicle entries.

        Checks for:
        - Theme recurrence: same tag appears 3+ times in 30 days
        - Prayer answers: prayer entry followed by gratitude entry sharing tags
        - Growth markers: struggle entry followed later by insight/peace entry
        """
        insights: list[ChroniclePatternInsight] = []
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)

        recent = [
            e for e in entries
            if _parse_iso(e.created_at) is not None
            and _parse_iso(e.created_at) >= cutoff  # type: ignore[operator]
        ]

        # --- Theme recurrence ---
        theme_counts: dict[str, list[str]] = {}
        for entry in recent:
            for tag in entry.tags + entry.themes:
                if tag in ("prayer-request", "milestone", "gratitude"):
                    continue
                theme_counts.setdefault(tag, [])
                theme_counts[tag].append(entry.entry_id)

        for theme, entry_ids in theme_counts.items():
            if len(entry_ids) >= 3:
                passages = SCRIPTURE_BY_THEME.get(theme, [])
                scripture_refs = [p["ref"] for p in passages[:2]]
                insights.append(ChroniclePatternInsight(
                    insight_id=str(uuid.uuid4()),
                    pattern_type="theme_recurrence",
                    title=f"Recurring theme: {theme}",
                    description=(
                        f'The theme of "{theme}" has appeared {len(entry_ids)} times '
                        f"in your entries over the past 30 days. "
                        f"This may be an invitation to linger here a little longer."
                    ),
                    evidence=entry_ids,
                    scripture_connections=scripture_refs,
                    detected_at=_now_iso(),
                    surfaced_to_user=False,
                ))

        # --- Prayer answers ---
        prayer_entries = [e for e in recent if e.entry_type == "prayer"]
        gratitude_entries = [e for e in recent if e.entry_type == "gratitude"]

        for prayer in prayer_entries:
            prayer_dt = _parse_iso(prayer.created_at)
            prayer_tag_set = set(prayer.tags + prayer.themes)
            for gratitude in gratitude_entries:
                gratitude_dt = _parse_iso(gratitude.created_at)
                if gratitude_dt is None or prayer_dt is None:
                    continue
                if gratitude_dt <= prayer_dt:
                    continue
                gratitude_tag_set = set(gratitude.tags + gratitude.themes)
                overlap = prayer_tag_set & gratitude_tag_set - {
                    "prayer-request", "gratitude", "auto_captured"
                }
                if overlap:
                    insights.append(ChroniclePatternInsight(
                        insight_id=str(uuid.uuid4()),
                        pattern_type="answer_to_prayer",
                        title="A prayer appears to have been answered",
                        description=(
                            f'You prayed about "{prayer.title}" and later recorded gratitude '
                            f'around "{gratitude.title}". These share the theme(s): '
                            f'{", ".join(overlap)}. Worth noting in your journal.'
                        ),
                        evidence=[prayer.entry_id, gratitude.entry_id],
                        scripture_connections=["1 Thessalonians 5:16-18"],
                        detected_at=_now_iso(),
                        surfaced_to_user=False,
                    ))

        # --- Growth markers: struggle → insight / peace ---
        struggle_entries = [
            e for e in recent
            if e.mood in ("struggling", "uncertain")
        ]
        hopeful_entries = [
            e for e in recent
            if e.mood in ("peaceful", "grateful", "joyful", "hopeful")
        ]

        for struggle in struggle_entries:
            struggle_dt = _parse_iso(struggle.created_at)
            for hopeful in hopeful_entries:
                hopeful_dt = _parse_iso(hopeful.created_at)
                if hopeful_dt is None or struggle_dt is None:
                    continue
                gap = hopeful_dt - struggle_dt
                if timedelta(days=1) <= gap <= timedelta(days=21):
                    shared_tags = (
                        set(struggle.tags + struggle.themes)
                        & set(hopeful.tags + hopeful.themes)
                    ) - {"auto_captured"}
                    if shared_tags:
                        insights.append(ChroniclePatternInsight(
                            insight_id=str(uuid.uuid4()),
                            pattern_type="growth_marker",
                            title="A movement from struggle to peace",
                            description=(
                                f'After recording struggle around "{struggle.title}", '
                                f'you later captured a more hopeful moment in "{hopeful.title}". '
                                f"This arc — from hard to held — is worth remembering."
                            ),
                            evidence=[struggle.entry_id, hopeful.entry_id],
                            scripture_connections=["Romans 8:28", "Psalm 34:18"],
                            detected_at=_now_iso(),
                            surfaced_to_user=False,
                        ))

        # Persist new insights
        for insight in insights:
            try:
                self._write_json(self._insight_path(insight.insight_id), insight.to_dict())
            except Exception as exc:
                logger.warning("Could not persist insight %s: %s", insight.insight_id, exc)

        return insights

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def save_entry_local(self, entry: ChronicleEntry) -> None:
        """Persist an entry to disk and append to pending queue."""
        try:
            self._write_json(self._entry_path(entry.entry_id), entry.to_dict())
            if not entry.sent_to_chronicle:
                self._append_jsonl(self._pending_path, entry.to_dict())
        except Exception as exc:
            logger.warning("Could not save ChronicleEntry %s: %s", entry.entry_id, exc)

    def get_pending_entries(self) -> list[ChronicleEntry]:
        """Return all entries that have not yet been pushed to Chronicle."""
        raw = self._read_jsonl(self._pending_path)
        entries = [ChronicleEntry.from_dict(r) for r in raw]
        # Filter: only those not yet sent (pending file may lag mark_entry_sent)
        return [e for e in entries if not e.sent_to_chronicle]

    def mark_entry_sent(self, entry_id: str) -> None:
        """Mark an entry as successfully sent to Chronicle."""
        path = self._entry_path(entry_id)
        data = self._read_json(path)
        if data is None:
            logger.warning("mark_entry_sent: entry %s not found", entry_id)
            return
        data["sent_to_chronicle"] = True
        data["sent_at"] = _now_iso()
        self._write_json(path, data)

        # Rewrite pending file excluding this entry_id
        raw = self._read_jsonl(self._pending_path)
        remaining = [r for r in raw if r.get("entry_id") != entry_id]
        try:
            self._pending_path.write_text(
                "\n".join(json.dumps(r, ensure_ascii=False) for r in remaining) + "\n"
                if remaining else "",
                encoding="utf-8",
            )
        except Exception as exc:
            logger.warning("Could not rewrite pending_entries.jsonl: %s", exc)

    def get_recent_entries(self, limit: int = 10) -> list[ChronicleEntry]:
        """Return the most recently created entries (across all types)."""
        all_entries: list[ChronicleEntry] = []
        for path in sorted(
            self._entries_dir.glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )[:limit * 2]:
            data = self._read_json(path)
            if data:
                try:
                    all_entries.append(ChronicleEntry.from_dict(data))
                except Exception:
                    pass
        # Sort by created_at descending
        all_entries.sort(
            key=lambda e: e.created_at,
            reverse=True,
        )
        return all_entries[:limit]

    def get_insights(self) -> list[ChroniclePatternInsight]:
        """Return all persisted pattern insights."""
        insights: list[ChroniclePatternInsight] = []
        for path in sorted(self._insights_dir.glob("*.json")):
            data = self._read_json(path)
            if data:
                try:
                    insights.append(ChroniclePatternInsight.from_dict(data))
                except Exception:
                    pass
        return insights


# ---------------------------------------------------------------------------
# Reflection question bank (keyed by theme)
# ---------------------------------------------------------------------------

_REFLECTION_QUESTIONS: dict[str, str] = {
    "anxiety": (
        "What specific worry has occupied your thoughts recently? "
        "Can you lay it before God in prayer today — not to fix it, but to release it?"
    ),
    "provision": (
        "Where have you seen God provide in ways you didn't expect? "
        "What would it look like to trust Him today with what you cannot yet see?"
    ),
    "strength": (
        "Where do you feel depleted right now? "
        "What would it mean to let God's strength carry what you can't carry yourself today?"
    ),
    "peace": (
        "Is there something inside you that peace hasn't yet reached? "
        "What would it take to let the peace of Christ stand guard there?"
    ),
    "wisdom": (
        "What decision or season is requiring more wisdom than you feel you have? "
        "Have you asked God directly — and what are you expecting in response?"
    ),
    "family": (
        "What is one thing your family needs from you this week that only you can give? "
        "How does your faith shape the way you lead and love at home?"
    ),
    "faith": (
        "Where is your faith being stretched right now? "
        "What would it look like to take one small step forward in trust, even in uncertainty?"
    ),
    "purpose": (
        "What work or calling feels most alive to you right now? "
        "Where do you sense God's pleasure in how you're spending your days?"
    ),
    "gratitude": (
        "Pause and name three specific things — large or small — for which you are grateful today. "
        "How does gratitude change the way you see the rest of your day?"
    ),
    "leadership": (
        "Who are you serving this week? "
        "Where might you be leading from ambition rather than from calling?"
    ),
    "trust": (
        "Is there an area of your life where you are holding on tightly? "
        "What would it look like to open your hands and trust God with that today?"
    ),
    "hope": (
        "What promise from God are you holding onto right now? "
        "How does that hope shape the way you face today?"
    ),
    "grief": (
        "What loss or hard thing are you carrying? "
        "God is close to the brokenhearted — what would it mean to let Him near this part of your story?"
    ),
}


# ---------------------------------------------------------------------------
# DiscipleWorkflow
# ---------------------------------------------------------------------------


class DiscipleWorkflow:
    """
    Disciple (chronicle-curator) orchestrates the JARVIS ↔ Chronicle integration.

    Disciple's role: guardian of spiritual continuity and legacy. They ensure
    Chris's formation journey is captured, reflected on, and remembered.

    Key patterns:
    - Each morning: pull spiritual context for the briefing
    - Detect gratitude / prayer moments in conversations
    - Weekly: surface pattern insights
    - Prepare daily reflection prompt using context from today
    """

    AGENT_ID = "chronicle-curator"
    AGENT_NAME = "Disciple"

    def __init__(
        self,
        bridge: ChronicleBridge,
        memory_store: Any = None,
    ) -> None:
        self._bridge = bridge
        self._memory_store = memory_store

    # ------------------------------------------------------------------
    # Morning briefing integration
    # ------------------------------------------------------------------

    def on_morning_briefing(self, briefing_packet: dict) -> dict:
        """
        Add spiritual context to the morning briefing packet.

        Returns a dict with keys: scripture_of_day, reflection_prompt,
        prayer_count, answered_recently, top_insight.
        """
        try:
            actor_id = briefing_packet.get("actor_id", "chris")
            spiritual = self._bridge.get_morning_spiritual_context(actor_id=actor_id)
            return {
                "scripture_of_day": spiritual.get("scripture_of_day", {}),
                "reflection_prompt": spiritual.get("reflection_prompt", ""),
                "prayer_count": spiritual.get("prayer_count", 0),
                "answered_recently": spiritual.get("answered_recently", []),
                "top_insight": spiritual.get("top_insight", ""),
                "current_study": spiritual.get("current_study", ""),
            }
        except Exception as exc:
            logger.warning("DiscipleWorkflow.on_morning_briefing error: %s", exc)
            return {}

    # ------------------------------------------------------------------
    # Conversation scanning
    # ------------------------------------------------------------------

    def on_conversation_text(self, text: str) -> list[ChronicleEntry]:
        """
        Scan conversation text for:
        - Gratitude expressions → capture_gratitude()
        - Concern / prayer mentions → package_prayer_request()
        - (Scripture references are logged via the bridge as reflection entries)

        Returns list of entries created (may be empty).
        """
        created: list[ChronicleEntry] = []

        # Gratitude check
        gratitude_entry = self._bridge.capture_gratitude(text)
        if gratitude_entry is not None:
            created.append(gratitude_entry)
            logger.debug("Gratitude captured: %s", gratitude_entry.title)

        # Prayer / concern check (only if not already caught as gratitude)
        if not created and any(p.search(text) for p in _CONCERN_PATTERNS):
            concern_entry = self._bridge.package_prayer_request(text)
            created.append(concern_entry)
            logger.debug("Prayer request packaged: %s", concern_entry.title)

        return created

    # ------------------------------------------------------------------
    # Weekly pattern review
    # ------------------------------------------------------------------

    def weekly_pattern_review(self) -> list[ChroniclePatternInsight]:
        """
        Run pattern detection over recent Chronicle entries.
        Returns new insights (unsurfaced to user).
        """
        entries = self._bridge.get_recent_entries(limit=50)
        insights = self._bridge.detect_patterns(entries)
        new_insights = [i for i in insights if not i.surfaced_to_user]
        logger.info(
            "Weekly pattern review: %d entries examined, %d new insights",
            len(entries),
            len(new_insights),
        )
        return new_insights

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def get_workflow_status(self) -> dict:
        """Return Disciple workflow status for the 'Already Working' zone."""
        pending = self._bridge.get_pending_entries()
        insights = self._bridge.get_insights()
        recent = self._bridge.get_recent_entries(limit=5)
        formation = self._bridge._read_json(self._bridge._formation_path) or {}

        return {
            "agent": self.AGENT_NAME,
            "agent_id": self.AGENT_ID,
            "pending_entries": len(pending),
            "total_insights": len(insights),
            "unsurfaced_insights": sum(1 for i in insights if not i.surfaced_to_user),
            "recent_entry_titles": [e.title for e in recent],
            "current_study": formation.get("current_study", ""),
            "formation_updated_at": formation.get("updated_at", ""),
            "status": "active",
        }


# ---------------------------------------------------------------------------
# Module-level singletons and init helpers
# ---------------------------------------------------------------------------

_bridge_singleton: ChronicleBridge | None = None
_disciple_singleton: DiscipleWorkflow | None = None


def init_chronicle_bridge(
    chronicle_client: Any = None,
    memory_store: Any = None,
) -> tuple[ChronicleBridge, DiscipleWorkflow]:
    """
    Initialise the module-level ChronicleBridge and DiscipleWorkflow singletons.
    Safe to call multiple times; subsequent calls are no-ops and return the
    existing instances.
    """
    global _bridge_singleton, _disciple_singleton

    if _bridge_singleton is not None:
        assert _disciple_singleton is not None
        return _bridge_singleton, _disciple_singleton

    bridge = ChronicleBridge(chronicle_client=chronicle_client)
    disciple = DiscipleWorkflow(bridge=bridge, memory_store=memory_store)

    _bridge_singleton = bridge
    _disciple_singleton = disciple
    logger.info("ChronicleBridge and DiscipleWorkflow (chronicle-curator) initialised")
    return bridge, disciple


def get_chronicle_bridge() -> ChronicleBridge | None:
    """Return the module-level ChronicleBridge singleton, or None if not yet initialised."""
    return _bridge_singleton


def get_disciple() -> DiscipleWorkflow | None:
    """Return the module-level DiscipleWorkflow singleton, or None if not yet initialised."""
    return _disciple_singleton


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _parse_iso(s: str) -> datetime | None:
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None
