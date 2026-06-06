"""
publishing_suite.py — Epic 11: Publishing & Revenue Suite
==========================================================
Unified publishing and revenue operations module for JARVIS.

Agents covered:
  stan-lee          — Writing & Ghostwritr Integration Lead
  robbie-robertson  — Book Publishing & Distribution Lead
  loki              — Marketing & Promotion Director
  iron-fist         — Course & Training Creation Lead (roster member, ops via Orchestrator)
  amadeus-cho       — Web Presence Lead (roster member, ops via Orchestrator)
  jjj               — Social Media Manager (ContentCalendar primary operator)
  quicksilver       — Platform Deployment Lead (timing via ContentCalendar)
  sage              — Performance Analytics Lead

Persistent storage: ~/.jarvis/publishing/
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .persistence import append_jsonl, atomic_write_json, atomic_write_jsonl

logger = logging.getLogger("jarvis.publishing_suite")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _parse_date(date_str: str) -> datetime | None:
    if not date_str:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z"):
        try:
            return datetime.strptime(date_str[:26], fmt[:len(date_str)])
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Core data models
# ---------------------------------------------------------------------------

@dataclass
class PublishingProject:
    project_id: str
    project_type: str       # "book" | "course" | "blog_post" | "social_campaign" | "website"
    title: str
    status: str             # "draft" | "editing" | "ready" | "published" | "archived"
    platform: str           # "amazon_kdp" | "gumroad" | "coursera" | "udemy" | "wordpress" | "instagram" | etc.
    created_at: str
    updated_at: str
    published_at: str = ""
    url: str = ""
    description: str = ""
    tags: list[str] = field(default_factory=list)
    revenue_tracking: bool = False
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "PublishingProject":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class RevenueStream:
    stream_id: str
    stream_type: str        # "book_royalty" | "course_revenue" | "affiliate" | "consulting" | "other"
    source: str             # platform or client name
    project_id: str = ""    # linked publishing project if any
    monthly_estimate: float = 0.0
    last_payment: float = 0.0
    last_payment_date: str = ""
    currency: str = "USD"
    notes: str = ""
    active: bool = True
    tracking_url: str = ""  # where to check balance/reports

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "RevenueStream":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class SocialPost:
    post_id: str
    platform: str           # "twitter" | "instagram" | "linkedin" | "facebook"
    content: str
    media_urls: list[str] = field(default_factory=list)
    status: str = "draft"   # "draft" | "scheduled" | "posted" | "failed"
    scheduled_at: str = ""
    posted_at: str = ""
    campaign_id: str = ""
    project_id: str = ""
    performance: dict = field(default_factory=dict)  # {"likes": int, "shares": int, "reach": int, "clicks": int}

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "SocialPost":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ContentCalendarItem:
    item_id: str
    title: str
    content_type: str       # "social_post" | "blog_post" | "newsletter" | "video" | "podcast"
    platform: str
    planned_date: str
    status: str = "idea"    # "idea" | "outline" | "draft" | "ready" | "published"
    project_id: str = ""
    notes: str = ""
    assigned_agent: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ContentCalendarItem":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# PublishingStore — persistent JSON / JSONL storage
# ---------------------------------------------------------------------------

class PublishingStore:
    """
    Persistent storage for all publishing data.

    Files:
      ~/.jarvis/publishing/projects.json
      ~/.jarvis/publishing/revenue_streams.json
      ~/.jarvis/publishing/social_posts.jsonl
      ~/.jarvis/publishing/content_calendar.jsonl
    """

    ROOT = Path.home() / ".jarvis" / "publishing"

    def __init__(self, root: Path | None = None) -> None:
        self._root = root or self.ROOT
        self._root.mkdir(parents=True, exist_ok=True)
        self._projects_path = self._root / "projects.json"
        self._revenue_path = self._root / "revenue_streams.json"
        self._posts_path = self._root / "social_posts.jsonl"
        self._calendar_path = self._root / "content_calendar.jsonl"
        self._projects_log_path = self._projects_path.with_name("projects_log.jsonl")
        self._revenue_log_path = self._revenue_path.with_name("revenue_streams_log.jsonl")
        self._posts_log_path = self._posts_path.with_name("social_posts_state_log.jsonl")
        self._calendar_log_path = self._calendar_path.with_name("content_calendar_state_log.jsonl")

    def _json_log_path_for(self, path: Path) -> Path:
        if path == self._projects_path:
            return self._projects_log_path
        if path == self._revenue_path:
            return self._revenue_log_path
        return path.with_name(f"{path.stem}_log.jsonl")

    def _jsonl_log_path_for(self, path: Path) -> Path:
        if path == self._posts_path:
            return self._posts_log_path
        if path == self._calendar_path:
            return self._calendar_log_path
        return path.with_name(f"{path.stem}_log.jsonl")

    # ------------------------------------------------------------------
    # Projects
    # ------------------------------------------------------------------

    def _load_projects(self) -> dict[str, dict]:
        return self._load_json_dict(self._projects_path)

    def _save_projects(self, data: dict[str, dict]) -> None:
        self._save_json_dict(self._projects_path, data, "projects")

    def save_project(self, project: PublishingProject) -> None:
        data = self._load_projects()
        data[project.project_id] = project.to_dict()
        self._save_projects(data)

    def get_project(self, project_id: str) -> PublishingProject | None:
        data = self._load_projects()
        raw = data.get(project_id)
        if raw is None:
            return None
        try:
            return PublishingProject.from_dict(raw)
        except Exception:
            return None

    def list_projects(
        self, status: str | None = None, project_type: str | None = None
    ) -> list[PublishingProject]:
        data = self._load_projects()
        projects: list[PublishingProject] = []
        for raw in data.values():
            try:
                p = PublishingProject.from_dict(raw)
                if status and p.status != status:
                    continue
                if project_type and p.project_type != project_type:
                    continue
                projects.append(p)
            except Exception:
                pass
        projects.sort(key=lambda p: p.updated_at, reverse=True)
        return projects

    # ------------------------------------------------------------------
    # Revenue streams
    # ------------------------------------------------------------------

    def _load_revenue(self) -> dict[str, dict]:
        return self._load_json_dict(self._revenue_path)

    def _save_revenue(self, data: dict[str, dict]) -> None:
        self._save_json_dict(self._revenue_path, data, "revenue streams")

    def save_revenue_stream(self, stream: RevenueStream) -> None:
        data = self._load_revenue()
        data[stream.stream_id] = stream.to_dict()
        self._save_revenue(data)

    def list_revenue_streams(self, active_only: bool = True) -> list[RevenueStream]:
        data = self._load_revenue()
        streams: list[RevenueStream] = []
        for raw in data.values():
            try:
                s = RevenueStream.from_dict(raw)
                if active_only and not s.active:
                    continue
                streams.append(s)
            except Exception:
                pass
        return streams

    # ------------------------------------------------------------------
    # Social posts (JSONL)
    # ------------------------------------------------------------------

    def _load_posts(self) -> list[dict]:
        return self._load_jsonl(self._posts_path)

    def _save_posts(self, posts: list[dict]) -> None:
        self._save_jsonl(self._posts_path, posts, "social posts")

    def save_social_post(self, post: SocialPost) -> None:
        posts = self._load_posts()
        # Update-or-append
        for i, p in enumerate(posts):
            if p.get("post_id") == post.post_id:
                posts[i] = post.to_dict()
                self._save_posts(posts)
                return
        posts.append(post.to_dict())
        self._save_posts(posts)

    def get_scheduled_posts(self) -> list[SocialPost]:
        posts = self._load_posts()
        result = []
        for raw in posts:
            try:
                p = SocialPost.from_dict(raw)
                if p.status in ("draft", "scheduled"):
                    result.append(p)
            except Exception:
                pass
        result.sort(key=lambda p: p.scheduled_at or "9999")
        return result

    def list_posts(self, status: str | None = None) -> list[SocialPost]:
        posts = self._load_posts()
        result = []
        for raw in posts:
            try:
                p = SocialPost.from_dict(raw)
                if status and p.status != status:
                    continue
                result.append(p)
            except Exception:
                pass
        return result

    # ------------------------------------------------------------------
    # Content calendar (JSONL)
    # ------------------------------------------------------------------

    def _load_calendar(self) -> list[dict]:
        return self._load_jsonl(self._calendar_path)

    def _save_calendar(self, items: list[dict]) -> None:
        self._save_jsonl(self._calendar_path, items, "content calendar")

    def _load_json_dict(self, path: Path) -> dict[str, dict]:
        if path.exists():
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    return payload
            except (OSError, json.JSONDecodeError):
                pass
        log_path = self._json_log_path_for(path)
        if not log_path.exists():
            return {}
        try:
            latest: dict[str, dict] = {}
            for line in log_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                data = payload.get("data")
                if isinstance(data, dict):
                    latest = data
            return latest
        except OSError:
            return {}

    def _save_json_dict(self, path: Path, data: dict[str, dict], label: str) -> None:
        try:
            append_jsonl(
                self._json_log_path_for(path),
                {
                    "saved_at": _now_iso(),
                    "data": data,
                },
                ensure_ascii=False,
            )
            atomic_write_json(path, data, ensure_ascii=False)
        except OSError as exc:
            logger.warning("Failed to save %s: %s", label, exc)

    def _load_jsonl(self, path: Path) -> list[dict]:
        if path.exists():
            try:
                items = []
                for line in path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        item = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(item, dict):
                        items.append(item)
                if items:
                    return items
            except OSError:
                pass
        log_path = self._jsonl_log_path_for(path)
        if not log_path.exists():
            return []
        try:
            latest: list[dict] = []
            for line in log_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                records = payload.get("records")
                if isinstance(records, list):
                    latest = [dict(item) for item in records if isinstance(item, dict)]
            return latest
        except OSError:
            return []

    def _save_jsonl(self, path: Path, records: list[dict], label: str) -> None:
        try:
            append_jsonl(
                self._jsonl_log_path_for(path),
                {
                    "saved_at": _now_iso(),
                    "records": records,
                },
                ensure_ascii=False,
            )
            atomic_write_jsonl(path, records, ensure_ascii=False)
        except OSError as exc:
            logger.warning("Failed to save %s: %s", label, exc)

    def save_calendar_item(self, item: ContentCalendarItem) -> None:
        items = self._load_calendar()
        for i, raw in enumerate(items):
            if raw.get("item_id") == item.item_id:
                items[i] = item.to_dict()
                self._save_calendar(items)
                return
        items.append(item.to_dict())
        self._save_calendar(items)

    def list_calendar_items(self) -> list[ContentCalendarItem]:
        result = []
        for raw in self._load_calendar():
            try:
                result.append(ContentCalendarItem.from_dict(raw))
            except Exception:
                pass
        return result


# ---------------------------------------------------------------------------
# ContentCalendar — calendar management layer
# ---------------------------------------------------------------------------

class ContentCalendar:
    """
    Manages the content calendar across all publishing operations.
    J. Jonah Jameson (jjj) is the primary operator for social content.
    Quicksilver handles deployment timing.
    """

    ROOT = Path.home() / ".jarvis" / "publishing"

    def __init__(self, store: PublishingStore | None = None) -> None:
        self._store = store or PublishingStore()

    def add_item(self, item: ContentCalendarItem) -> None:
        self._store.save_calendar_item(item)
        logger.debug("ContentCalendar: added item %s (%s)", item.item_id, item.title)

    def get_upcoming(self, days: int = 14) -> list[ContentCalendarItem]:
        today_str = _today()
        cutoff = (datetime.now(timezone.utc) + timedelta(days=days)).strftime("%Y-%m-%d")
        return [
            item
            for item in self._store.list_calendar_items()
            if item.planned_date >= today_str and item.planned_date <= cutoff
            and item.status != "published"
        ]

    def get_overdue(self) -> list[ContentCalendarItem]:
        today_str = _today()
        return [
            item
            for item in self._store.list_calendar_items()
            if item.planned_date < today_str and item.status not in ("published",)
        ]

    def update_status(self, item_id: str, status: str) -> bool:
        items = self._store.list_calendar_items()
        for item in items:
            if item.item_id == item_id:
                item.status = status
                self._store.save_calendar_item(item)
                return True
        return False

    def get_by_platform(self, platform: str) -> list[ContentCalendarItem]:
        return [
            item
            for item in self._store.list_calendar_items()
            if item.platform.lower() == platform.lower()
        ]

    def get_today(self) -> list[ContentCalendarItem]:
        today_str = _today()
        return [
            item
            for item in self._store.list_calendar_items()
            if item.planned_date == today_str
        ]


# ---------------------------------------------------------------------------
# StanLeeAgent — Writing & Ghostwritr Integration Lead
# ---------------------------------------------------------------------------

class StanLeeAgent:
    """
    Stan Lee: exclamation point energy, loves a good story, sees narrative everywhere.

    Stan bridges JARVIS and Ghostwritr (future integration).
    For now: manuscript tracking, writing session prep, and writing productivity.
    """

    WRITING_SESSION_KEY = "stan_lee_sessions"

    def __init__(self, store: PublishingStore) -> None:
        self._store = store
        self._sessions_path = store._root / "writing_sessions.jsonl"
        self._sessions_log_path = self._sessions_path.with_name("writing_sessions_state_log.jsonl")

    def _load_sessions(self) -> list[dict]:
        if self._sessions_path.exists():
            try:
                sessions = []
                for line in self._sessions_path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        sessions.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
                if sessions:
                    return sessions
            except OSError:
                pass
        return self._load_sessions_from_log()

    def _load_sessions_from_log(self) -> list[dict]:
        if not self._sessions_log_path.exists():
            return []
        try:
            latest: list[dict] = []
            for line in self._sessions_log_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                payload = json.loads(line)
                records = payload.get("records")
                if isinstance(records, list):
                    latest = [dict(item) for item in records if isinstance(item, dict)]
            return latest
        except Exception:
            return []

    def _save_session(self, session: dict) -> None:
        try:
            records = self._load_sessions()
            records.append(session)
            atomic_write_jsonl(self._sessions_path, records, ensure_ascii=False)
            append_jsonl(
                self._sessions_log_path,
                {
                    "saved_at": _now_iso(),
                    "records": records,
                },
                ensure_ascii=False,
            )
        except OSError as exc:
            logger.warning("StanLeeAgent: failed to save session: %s", exc)

    def prep_writing_session(
        self, project: PublishingProject, context: dict | None = None
    ) -> dict:
        """
        Prepare context for a writing session.

        Returns: {"goal": str, "context": str, "last_excerpt": str, "stan_says": str}
        """
        context = context or {}
        sessions = [s for s in self._load_sessions() if s.get("project_id") == project.project_id]
        last_session = sessions[-1] if sessions else None

        total_words = sum(s.get("words_written", 0) for s in sessions)
        daily_goal = context.get("daily_goal", 500)

        last_excerpt = ""
        if last_session:
            last_excerpt = last_session.get("excerpt", "")
            last_date = last_session.get("date", "")
            last_words = last_session.get("words_written", 0)
            session_note = f"Last session ({last_date}): {last_words} words written."
        else:
            session_note = "No prior sessions found — time to start the journey!"

        stan_says_options = [
            f"Excelsior! '{project.title}' is going to change lives. Now let's get those words down!",
            f"Every great story starts with a single sentence. Today, we write the next chapter of '{project.title}'!",
            f"True believers write even when the words don't come easy. You've got {daily_goal} words to find today — go find them!",
            f"The best story is the one you finish. '{project.title}' needs you. Nuff said.",
            f"With great writing comes great responsibility. {daily_goal} words. Let's go!",
        ]
        import hashlib
        idx = int(hashlib.md5(_today().encode()).hexdigest(), 16) % len(stan_says_options)
        stan_says = stan_says_options[idx]

        return {
            "goal": f"Write {daily_goal} words on '{project.title}'",
            "context": (
                f"Project: {project.title} | Status: {project.status} | "
                f"Platform: {project.platform} | Total words so far: {total_words:,}. "
                f"{session_note}"
            ),
            "last_excerpt": last_excerpt,
            "stan_says": stan_says,
            "total_words_to_date": total_words,
            "session_count": len(sessions),
        }

    def track_writing_session(
        self, words_written: int, project_id: str, notes: str = ""
    ) -> dict:
        """Log a writing session and update project status."""
        session = {
            "session_id": str(uuid.uuid4()),
            "project_id": project_id,
            "words_written": words_written,
            "date": _today(),
            "timestamp": _now_iso(),
            "notes": notes,
            "excerpt": "",  # could be populated by caller
        }
        self._save_session(session)

        # Update project's updated_at
        project = self._store.get_project(project_id)
        if project:
            project.updated_at = _now_iso()
            self._store.save_project(project)

        sessions = [s for s in self._load_sessions() if s.get("project_id") == project_id]
        total_words = sum(s.get("words_written", 0) for s in sessions)

        return {
            "session_id": session["session_id"],
            "project_id": project_id,
            "words_written": words_written,
            "total_words": total_words,
            "session_count": len(sessions),
            "message": f"Great session! {words_written} words logged. Total: {total_words:,}.",
        }

    def get_manuscript_status(self) -> list[dict]:
        """Current status of all active manuscripts."""
        projects = self._store.list_projects(project_type="book")
        sessions = self._load_sessions()

        result = []
        for project in projects:
            if project.status == "archived":
                continue
            proj_sessions = [s for s in sessions if s.get("project_id") == project.project_id]
            total_words = sum(s.get("words_written", 0) for s in proj_sessions)
            last_session = proj_sessions[-1] if proj_sessions else None
            result.append({
                "project_id": project.project_id,
                "title": project.title,
                "status": project.status,
                "total_words": total_words,
                "session_count": len(proj_sessions),
                "last_session_date": last_session.get("date", "") if last_session else "",
                "platform": project.platform,
                "notes": project.notes,
            })
        return result


# ---------------------------------------------------------------------------
# RobbieRobertsonAgent — Book Publishing & Distribution Lead
# ---------------------------------------------------------------------------

class RobbieRobertsonAgent:
    """
    Robbie Robertson: steady, experienced, knows the publishing game.
    Gets books from manuscript to market without drama.
    """

    BOOK_PUBLISHING_CHECKLIST = [
        {"step": "manuscript_final", "label": "Final manuscript complete", "order": 1},
        {"step": "isbn", "label": "ISBN obtained", "order": 2},
        {"step": "cover_design", "label": "Cover designed", "order": 3},
        {"step": "interior_format", "label": "Interior formatted (KDP-ready PDF)", "order": 4},
        {"step": "kdp_account", "label": "KDP account setup", "order": 5},
        {"step": "title_metadata", "label": "Title, subtitle, description written", "order": 6},
        {"step": "categories_keywords", "label": "7 categories + 7 keywords selected", "order": 7},
        {"step": "pricing_set", "label": "Pricing set", "order": 8},
        {"step": "publish_draft", "label": "Published as draft on KDP", "order": 9},
        {"step": "proof_reviewed", "label": "Proof copy reviewed", "order": 10},
        {"step": "published_live", "label": "Published live", "order": 11},
    ]

    COURSE_PUBLISHING_CHECKLIST = [
        {"step": "outline_complete", "label": "Course outline complete", "order": 1},
        {"step": "recordings_done", "label": "All video/audio recordings done", "order": 2},
        {"step": "assets_prepared", "label": "Workbooks, slides, resources prepared", "order": 3},
        {"step": "platform_account", "label": "Platform account setup (Udemy/Coursera/Gumroad)", "order": 4},
        {"step": "course_metadata", "label": "Title, description, thumbnail done", "order": 5},
        {"step": "pricing_set", "label": "Pricing and access tiers set", "order": 6},
        {"step": "preview_published", "label": "Preview/intro lesson published", "order": 7},
        {"step": "published_live", "label": "Course published live", "order": 8},
    ]

    def __init__(self, store: PublishingStore) -> None:
        self._store = store
        self._checklist_path = store._root / "publishing_checklists.json"
        self._checklist_log_path = self._checklist_path.with_name("publishing_checklists_log.jsonl")

    def _load_checklists(self) -> dict:
        if self._checklist_path.exists():
            try:
                payload = json.loads(self._checklist_path.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    return payload
            except (OSError, json.JSONDecodeError):
                pass
        if not self._checklist_log_path.exists():
            return {}
        try:
            latest: dict[str, Any] = {}
            for line in self._checklist_log_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                data = payload.get("checklists")
                if isinstance(data, dict):
                    latest = data
            return latest
        except OSError:
            return {}

    def _save_checklists(self, data: dict) -> None:
        try:
            append_jsonl(
                self._checklist_log_path,
                {
                    "saved_at": _now_iso(),
                    "checklists": data,
                },
                ensure_ascii=False,
            )
            atomic_write_json(self._checklist_path, data, ensure_ascii=False)
        except OSError as exc:
            logger.warning("RobbieRobertsonAgent: failed to save checklists: %s", exc)

    def get_publishing_checklist(self, project: PublishingProject) -> list[dict]:
        """Returns a publishing checklist for the given project type."""
        if project.project_type == "book":
            template = self.BOOK_PUBLISHING_CHECKLIST
        elif project.project_type == "course":
            template = self.COURSE_PUBLISHING_CHECKLIST
        else:
            return []

        checklists = self._load_checklists()
        project_checklist = checklists.get(project.project_id, {})

        result = []
        for item in template:
            result.append({
                "step": item["step"],
                "label": item["label"],
                "order": item["order"],
                "completed": project_checklist.get(item["step"], False),
                "completed_at": project_checklist.get(f"{item['step']}_at", ""),
            })
        return result

    def track_kdp_checklist(self, project_id: str, step: str, completed: bool) -> dict:
        """Track completion of a KDP publishing step."""
        checklists = self._load_checklists()
        if project_id not in checklists:
            checklists[project_id] = {}
        checklists[project_id][step] = completed
        if completed:
            checklists[project_id][f"{step}_at"] = _now_iso()
        self._save_checklists(checklists)

        project = self._store.get_project(project_id)
        completed_steps = sum(1 for k, v in checklists[project_id].items() if not k.endswith("_at") and v)
        template = self.BOOK_PUBLISHING_CHECKLIST
        if project and project.project_type == "course":
            template = self.COURSE_PUBLISHING_CHECKLIST
        total_steps = len(template)

        return {
            "project_id": project_id,
            "step": step,
            "completed": completed,
            "progress": f"{completed_steps}/{total_steps}",
            "percent": round(completed_steps / max(total_steps, 1) * 100),
        }

    def format_kdp_metadata(self, book_info: dict) -> dict:
        """
        Format book metadata for Amazon KDP.
        Returns structured metadata ready for KDP entry.
        """
        title = book_info.get("title", "")
        subtitle = book_info.get("subtitle", "")
        author = book_info.get("author", "Chris Binion")
        description = book_info.get("description", "")

        # Format description as HTML for KDP
        paragraphs = [p.strip() for p in description.split("\n\n") if p.strip()]
        html_description = "\n".join(f"<p>{p}</p>" for p in paragraphs) if paragraphs else f"<p>{description}</p>"

        # KDP pricing suggestions based on page count / market
        page_count = book_info.get("page_count", 200)
        if page_count < 100:
            price_suggestion = 2.99
        elif page_count < 200:
            price_suggestion = 4.99
        elif page_count < 350:
            price_suggestion = 6.99
        else:
            price_suggestion = 9.99

        return {
            "title": title,
            "subtitle": subtitle,
            "author": author,
            "html_description": html_description,
            "categories": book_info.get("categories", [])[:7],
            "keywords": book_info.get("keywords", [])[:7],
            "price_ebook_usd": price_suggestion,
            "price_paperback_usd": round(price_suggestion * 2.5, 2),
            "kdp_select_eligible": True,
            "language": book_info.get("language", "English"),
            "isbn": book_info.get("isbn", ""),
            "publisher": book_info.get("publisher", ""),
            "publication_date": book_info.get("publication_date", ""),
        }

    def get_books_status(self) -> list[dict]:
        """Status of all books in the publishing pipeline."""
        projects = self._store.list_projects(project_type="book")
        checklists = self._load_checklists()
        result = []
        for project in projects:
            project_checklist = checklists.get(project.project_id, {})
            completed_steps = sum(1 for k, v in project_checklist.items() if not k.endswith("_at") and v)
            total_steps = len(self.BOOK_PUBLISHING_CHECKLIST)
            result.append({
                "project_id": project.project_id,
                "title": project.title,
                "status": project.status,
                "platform": project.platform,
                "checklist_progress": f"{completed_steps}/{total_steps}",
                "checklist_percent": round(completed_steps / max(total_steps, 1) * 100),
                "url": project.url,
                "revenue_tracking": project.revenue_tracking,
                "updated_at": project.updated_at,
            })
        return result


# ---------------------------------------------------------------------------
# LokiAgent — Marketing & Promotion Director
# ---------------------------------------------------------------------------

class LokiAgent:
    """
    Loki: master of narrative, audience, and timing.
    Never wastes a good launch moment.
    """

    def __init__(self, store: PublishingStore) -> None:
        self._store = store
        self._launch_plans_path = store._root / "launch_plans.json"
        self._launch_plans_log_path = self._launch_plans_path.with_name("launch_plans_log.jsonl")

    def _load_plans(self) -> dict:
        if self._launch_plans_path.exists():
            try:
                payload = json.loads(self._launch_plans_path.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    return payload
            except (OSError, json.JSONDecodeError):
                pass
        if not self._launch_plans_log_path.exists():
            return {}
        try:
            latest: dict[str, Any] = {}
            for line in self._launch_plans_log_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                data = payload.get("plans")
                if isinstance(data, dict):
                    latest = data
            return latest
        except OSError:
            return {}

    def _save_plans(self, data: dict) -> None:
        try:
            append_jsonl(
                self._launch_plans_log_path,
                {
                    "saved_at": _now_iso(),
                    "plans": data,
                },
                ensure_ascii=False,
            )
            atomic_write_json(self._launch_plans_path, data, ensure_ascii=False)
        except OSError as exc:
            logger.warning("LokiAgent: failed to save launch plans: %s", exc)

    def build_launch_plan(self, project: PublishingProject) -> dict:
        """
        Build a book/course launch plan with daily action cadence.

        Phases:
        - Pre-launch (4 weeks out): tease, build list, advance reviews
        - Launch week: daily content cadence, promo codes, outreach
        - Post-launch (2 weeks): testimonials, ads, social proof
        """
        plan = {
            "plan_id": str(uuid.uuid4()),
            "project_id": project.project_id,
            "project_title": project.title,
            "project_type": project.project_type,
            "created_at": _now_iso(),
            "phases": {
                "pre_launch": {
                    "label": "Pre-Launch (Weeks -4 to -1)",
                    "goal": "Build anticipation, grow the list, secure reviews",
                    "actions": [
                        {"week": -4, "action": "Announce the project — 'Something big is coming' teaser post across all platforms"},
                        {"week": -4, "action": "Create a landing page or waitlist signup"},
                        {"week": -3, "action": "Share 3 compelling behind-the-scenes content pieces"},
                        {"week": -3, "action": "Reach out to 10 potential advance readers / reviewers"},
                        {"week": -2, "action": "Email your list: early access or pre-order opportunity"},
                        {"week": -2, "action": "Post 'countdown' content — share the transformation this offers"},
                        {"week": -2, "action": "Confirm advance review copies sent to 5+ readers"},
                        {"week": -1, "action": "Final teaser: 'Dropping [day]' — build urgency"},
                        {"week": -1, "action": "Schedule all launch-week posts in advance"},
                        {"week": -1, "action": "Prep promo codes / early-bird pricing if applicable"},
                    ],
                },
                "launch_week": {
                    "label": "Launch Week",
                    "goal": "Maximum visibility, sales velocity, social proof",
                    "actions": [
                        {"day": 1, "action": f"Launch day: 'IT'S LIVE!' announcement on all platforms with direct link"},
                        {"day": 1, "action": "Email your list with the launch announcement and personal note"},
                        {"day": 2, "action": "Share a reader/student first impression or early testimonial"},
                        {"day": 3, "action": "Midweek recap: 'Here's what people are saying...' social proof post"},
                        {"day": 4, "action": "Behind-the-scenes: 'Why I wrote this' personal story post"},
                        {"day": 5, "action": "FAQ or 'objection crusher' post — address common hesitations"},
                        {"day": 6, "action": "Final 48-hour push: 'Early bird pricing ends Sunday' urgency post"},
                        {"day": 7, "action": "Last chance email + social post — close the launch window"},
                    ],
                },
                "post_launch": {
                    "label": "Post-Launch (Weeks +1 to +2)",
                    "goal": "Sustain momentum, gather reviews, start evergreen marketing",
                    "actions": [
                        {"week": 1, "action": "Request honest reviews from advance readers — provide template"},
                        {"week": 1, "action": "Share 2-3 detailed testimonials or success stories"},
                        {"week": 1, "action": "Set up or tune paid ads with top-performing organic content"},
                        {"week": 2, "action": "Publish a case study or 'results so far' post"},
                        {"week": 2, "action": "Submit to relevant directories, lists, and press opportunities"},
                        {"week": 2, "action": "Plan ongoing evergreen content strategy for long-tail discovery"},
                    ],
                },
            },
            "platform_focus": project.platform,
            "status": "draft",
        }

        plans = self._load_plans()
        plans[project.project_id] = plan
        self._save_plans(plans)
        return plan

    def generate_social_content_ideas(
        self, project: PublishingProject, count: int = 5
    ) -> list[dict]:
        """
        Generate social content ideas for a project.
        Returns: [{"platform": str, "idea": str, "hook": str, "type": str}]
        """
        templates: list[dict] = [
            {
                "type": "behind_the_scenes",
                "platform": "instagram",
                "idea": f"Show the messy desk / writing process behind '{project.title}'",
                "hook": "Nobody shows you this part...",
            },
            {
                "type": "quote_pull",
                "platform": "twitter",
                "idea": f"Pull a compelling quote or insight from '{project.title}'",
                "hook": "This one idea changed how I think about [topic]:",
            },
            {
                "type": "transformation",
                "platform": "linkedin",
                "idea": f"Share the transformation readers get from '{project.title}'",
                "hook": "Before: [struggle]. After: [outcome]. Here's how:",
            },
            {
                "type": "faq",
                "platform": "facebook",
                "idea": f"Answer the top 3 questions you get about the topic of '{project.title}'",
                "hook": "Everyone asks me about [X]. Here's the real answer:",
            },
            {
                "type": "story",
                "platform": "instagram",
                "idea": f"Share the origin story — why you wrote '{project.title}'",
                "hook": "I almost didn't write this book. Here's what changed...",
            },
            {
                "type": "social_proof",
                "platform": "twitter",
                "idea": f"Share an early reader reaction to '{project.title}'",
                "hook": "Got this message this morning and it made my day:",
            },
            {
                "type": "tip",
                "platform": "linkedin",
                "idea": f"Extract a single actionable tip from '{project.title}' as a standalone post",
                "hook": "One thing that will immediately [improve X]:",
            },
            {
                "type": "countdown",
                "platform": "instagram",
                "idea": f"Countdown to launch / milestone for '{project.title}'",
                "hook": f"[X] days until '{project.title}' drops. Are you ready?",
            },
        ]
        return templates[:count]

    def get_launch_status(self, project_id: str) -> dict:
        """Current launch plan status and next actions."""
        plans = self._load_plans()
        plan = plans.get(project_id)
        if not plan:
            return {
                "project_id": project_id,
                "has_plan": False,
                "message": "No launch plan exists. Call build_launch_plan() to create one.",
            }

        # Determine next actionable phase
        status = plan.get("status", "draft")
        created_at = plan.get("created_at", "")

        return {
            "project_id": project_id,
            "has_plan": True,
            "plan_id": plan.get("plan_id"),
            "project_title": plan.get("project_title"),
            "status": status,
            "created_at": created_at,
            "phases": list(plan.get("phases", {}).keys()),
            "next_action": "Review pre-launch phase and set target launch date." if status == "draft" else "Continue executing current phase.",
        }


# ---------------------------------------------------------------------------
# SageAgent — Performance Analytics Lead
# ---------------------------------------------------------------------------

class SageAgent:
    """
    Sage: pattern recognition, data clarity, no noise.
    Turns revenue/analytics data into decisions.
    """

    def __init__(self, store: PublishingStore) -> None:
        self._store = store

    def get_revenue_summary(self) -> dict:
        """
        Aggregate all revenue streams.
        """
        streams = self._store.list_revenue_streams(active_only=False)
        active_streams = [s for s in streams if s.active]
        total_monthly = sum(s.monthly_estimate for s in active_streams)

        by_type: dict[str, float] = {}
        for s in active_streams:
            by_type[s.stream_type] = by_type.get(s.stream_type, 0.0) + s.monthly_estimate

        # Identify streams that need attention (zero or no recent payment)
        needs_attention: list[str] = []
        trending_up: list[str] = []
        today = datetime.now(timezone.utc)

        for s in active_streams:
            if s.monthly_estimate == 0:
                needs_attention.append(f"{s.source} ({s.stream_type}) — no revenue estimate set")
            elif s.last_payment_date:
                lp_date = _parse_date(s.last_payment_date)
                if lp_date:
                    days_since = (today - lp_date.replace(tzinfo=timezone.utc) if lp_date.tzinfo is None else today - lp_date).days
                    if days_since > 60:
                        needs_attention.append(f"{s.source} — last payment {days_since} days ago")
                    elif days_since < 30 and s.last_payment > s.monthly_estimate * 0.8:
                        trending_up.append(f"{s.source} ({s.stream_type})")

        return {
            "total_monthly_estimate": round(total_monthly, 2),
            "streams": [s.to_dict() for s in active_streams],
            "stream_count": len(active_streams),
            "by_type": {k: round(v, 2) for k, v in by_type.items()},
            "trending_up": trending_up,
            "needs_attention": needs_attention,
            "last_updated": _now_iso(),
        }

    def get_content_performance(self) -> dict:
        """
        Aggregate social post performance across platforms.
        Returns top performers, engagement rates, platform breakdown.
        """
        posts = self._store.list_posts()
        posted = [p for p in posts if p.status == "posted" and p.performance]

        platform_stats: dict[str, dict] = {}
        all_engagement = []

        for post in posted:
            perf = post.performance
            likes = perf.get("likes", 0)
            shares = perf.get("shares", 0)
            reach = perf.get("reach", 0)
            clicks = perf.get("clicks", 0)
            engagement = likes + shares * 2 + clicks
            reach_rate = round(engagement / max(reach, 1) * 100, 2)

            if post.platform not in platform_stats:
                platform_stats[post.platform] = {
                    "post_count": 0,
                    "total_likes": 0,
                    "total_shares": 0,
                    "total_reach": 0,
                    "total_clicks": 0,
                }
            ps = platform_stats[post.platform]
            ps["post_count"] += 1
            ps["total_likes"] += likes
            ps["total_shares"] += shares
            ps["total_reach"] += reach
            ps["total_clicks"] += clicks

            all_engagement.append({
                "post_id": post.post_id,
                "platform": post.platform,
                "content_preview": post.content[:80],
                "engagement_score": engagement,
                "reach_rate": reach_rate,
            })

        all_engagement.sort(key=lambda x: x["engagement_score"], reverse=True)

        return {
            "total_posts_analyzed": len(posted),
            "top_performers": all_engagement[:5],
            "platform_breakdown": platform_stats,
            "generated_at": _now_iso(),
        }

    def get_publishing_metrics(self) -> dict:
        """Books sold, courses enrolled, web traffic summaries."""
        projects = self._store.list_projects()
        published = [p for p in projects if p.status == "published"]
        in_progress = [p for p in projects if p.status in ("draft", "editing", "ready")]

        by_type: dict[str, int] = {}
        for p in published:
            by_type[p.project_type] = by_type.get(p.project_type, 0) + 1

        revenue_tracked = [p for p in published if p.revenue_tracking]

        return {
            "total_projects": len(projects),
            "published_count": len(published),
            "in_progress_count": len(in_progress),
            "by_type": by_type,
            "revenue_tracked_count": len(revenue_tracked),
            "platforms": list({p.platform for p in published}),
            "generated_at": _now_iso(),
        }

    def generate_performance_report(self, period: str = "monthly") -> str:
        """Generate a plain-English performance report for Nick Fury briefing."""
        revenue = self.get_revenue_summary()
        metrics = self.get_publishing_metrics()
        content = self.get_content_performance()

        lines = [
            f"Publishing & Revenue Report ({period.capitalize()})",
            "=" * 50,
            "",
            f"Revenue: ${revenue['total_monthly_estimate']:,.2f}/mo estimated across {revenue['stream_count']} active stream(s).",
        ]

        if revenue["by_type"]:
            lines.append("Breakdown by type:")
            for stream_type, amount in revenue["by_type"].items():
                lines.append(f"  - {stream_type.replace('_', ' ').title()}: ${amount:,.2f}/mo")

        if revenue["trending_up"]:
            lines.append(f"Trending up: {', '.join(revenue['trending_up'])}")

        if revenue["needs_attention"]:
            lines.append("Needs attention:")
            for item in revenue["needs_attention"]:
                lines.append(f"  - {item}")

        lines.extend([
            "",
            f"Publishing Pipeline: {metrics['published_count']} published, {metrics['in_progress_count']} in progress.",
        ])

        if metrics["by_type"]:
            type_summary = ", ".join(f"{v} {k.replace('_', ' ')}" for k, v in metrics["by_type"].items())
            lines.append(f"Published by type: {type_summary}.")

        if content["total_posts_analyzed"] > 0:
            lines.extend([
                "",
                f"Content Performance: {content['total_posts_analyzed']} post(s) analyzed.",
            ])
            if content["top_performers"]:
                top = content["top_performers"][0]
                lines.append(f"Top post: '{top['content_preview']}...' (score: {top['engagement_score']})")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# PublishingSuiteOrchestrator
# ---------------------------------------------------------------------------

class PublishingSuiteOrchestrator:
    """
    Ties all publishing agents together.
    Called by the scheduler for the weekly publishing cadence check.
    """

    def __init__(self, store: PublishingStore) -> None:
        self._store = store
        self.stan = StanLeeAgent(store)
        self.robbie = RobbieRobertsonAgent(store)
        self.loki = LokiAgent(store)
        self.sage = SageAgent(store)
        self.calendar = ContentCalendar(store)

    def weekly_publishing_check(self) -> dict:
        """
        Weekly check covering:
        - Manuscripts: any books in editing/ready phase?
        - Publishing pipeline: any books stuck in a checklist step?
        - Launch plans: any launches coming up in 30 days?
        - Revenue: any streams needing attention?
        - Content calendar: any posts overdue?

        Returns structured report for Nick Fury briefing.
        """
        now = _now_iso()

        # Manuscripts
        manuscripts = self.stan.get_manuscript_status()
        active_manuscripts = [m for m in manuscripts if m["status"] in ("draft", "editing")]

        # Books pipeline
        books_status = self.robbie.get_books_status()
        stuck_books = [
            b for b in books_status
            if b["status"] not in ("published", "archived") and b["checklist_percent"] < 100
        ]

        # Revenue
        revenue = self.sage.get_revenue_summary()

        # Content calendar
        overdue = self.calendar.get_overdue()
        upcoming = self.calendar.get_upcoming(days=30)

        # Launch plans
        loki_plans = self.loki._load_plans()
        active_launches = [
            p for p in self._store.list_projects()
            if p.status in ("editing", "ready") and p.project_id in loki_plans
        ]

        items: list[str] = []
        action_required = False

        if active_manuscripts:
            items.append(f"Active manuscripts: {len(active_manuscripts)} — {', '.join(m['title'] for m in active_manuscripts[:3])}")

        if stuck_books:
            action_required = True
            items.append(f"Publishing pipeline: {len(stuck_books)} book(s) need checklist progress")

        if active_launches:
            items.append(f"Upcoming launches: {len(active_launches)} project(s) have launch plans active")

        if revenue["needs_attention"]:
            action_required = True
            for item in revenue["needs_attention"][:3]:
                items.append(f"Revenue attention: {item}")

        if overdue:
            action_required = True
            items.append(f"Content overdue: {len(overdue)} calendar item(s) past their planned date")

        if upcoming:
            items.append(f"Upcoming content: {len(upcoming)} item(s) in the next 30 days")

        summary = (
            f"Publishing suite: {len(manuscripts)} manuscript(s), "
            f"${revenue['total_monthly_estimate']:,.2f}/mo estimated revenue, "
            f"{len(overdue)} overdue content item(s)."
        )

        return {
            "summary": summary,
            "items": items,
            "action_required": action_required,
            "priority": "normal" if action_required else "low",
            "generated_at": now,
            "manuscripts": manuscripts,
            "books_status": books_status,
            "revenue_summary": revenue,
            "overdue_calendar": [i.to_dict() for i in overdue],
            "upcoming_calendar": [i.to_dict() for i in upcoming[:10]],
        }

    def get_dashboard_status(self) -> dict:
        """Quick status for the Already Working zone."""
        projects = self._store.list_projects()
        active = [p for p in projects if p.status not in ("published", "archived")]
        published = [p for p in projects if p.status == "published"]
        revenue = self.sage.get_revenue_summary()
        overdue = self.calendar.get_overdue()
        upcoming_today = self.calendar.get_today()

        return {
            "active_projects": len(active),
            "published_projects": len(published),
            "monthly_revenue_estimate": revenue["total_monthly_estimate"],
            "active_streams": revenue["stream_count"],
            "overdue_content": len(overdue),
            "content_today": len(upcoming_today),
            "last_updated": _now_iso(),
        }


# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

def seed_publishing_data(store: PublishingStore) -> bool:
    """
    Create a sample project and revenue stream if the store is empty.
    Returns True if seeding occurred, False if data already exists.
    """
    existing_projects = store.list_projects()
    if existing_projects:
        return False

    # Sample book project
    sample_book = PublishingProject(
        project_id=str(uuid.uuid4()),
        project_type="book",
        title="The Leadership Code: Building Teams That Actually Work",
        status="editing",
        platform="amazon_kdp",
        created_at=_now_iso(),
        updated_at=_now_iso(),
        description=(
            "A practical guide to building high-performing teams in the modern workplace. "
            "Covers communication frameworks, accountability systems, and the hidden dynamics "
            "that make or break team culture."
        ),
        tags=["leadership", "management", "teams", "business"],
        revenue_tracking=True,
        notes="Target Q3 launch. Need to finalize chapters 8-10.",
    )

    # Sample course project
    sample_course = PublishingProject(
        project_id=str(uuid.uuid4()),
        project_type="course",
        title="Productivity Mastery: The 90-Day System",
        status="draft",
        platform="gumroad",
        created_at=_now_iso(),
        updated_at=_now_iso(),
        description=(
            "A structured 90-day course for professionals who want to dramatically increase "
            "their output without burning out. Includes video modules, worksheets, and weekly check-ins."
        ),
        tags=["productivity", "systems", "professional development"],
        revenue_tracking=True,
        notes="Module 1-4 recorded. Need modules 5-8.",
    )

    # Sample revenue stream
    sample_stream = RevenueStream(
        stream_id=str(uuid.uuid4()),
        stream_type="book_royalty",
        source="Amazon KDP",
        project_id="",
        monthly_estimate=0.0,
        last_payment=0.0,
        last_payment_date="",
        notes="Pending first publication. Set up tracking once book goes live.",
        active=True,
        tracking_url="https://kdp.amazon.com/en_US/reports",
    )

    # Sample content calendar items
    today = datetime.now(timezone.utc)
    sample_items = [
        ContentCalendarItem(
            item_id=str(uuid.uuid4()),
            title="LinkedIn post: Leadership tip of the week",
            content_type="social_post",
            platform="linkedin",
            planned_date=(today + timedelta(days=2)).strftime("%Y-%m-%d"),
            status="idea",
            notes="Pull from Chapter 3 — delegation framework",
            assigned_agent="jjj",
        ),
        ContentCalendarItem(
            item_id=str(uuid.uuid4()),
            title="Book announcement teaser post",
            content_type="social_post",
            platform="instagram",
            planned_date=(today + timedelta(days=7)).strftime("%Y-%m-%d"),
            status="outline",
            notes="Behind-the-scenes writing photo + caption about the journey",
            assigned_agent="jjj",
        ),
        ContentCalendarItem(
            item_id=str(uuid.uuid4()),
            title="Course preview email to newsletter list",
            content_type="newsletter",
            platform="email",
            planned_date=(today + timedelta(days=14)).strftime("%Y-%m-%d"),
            status="idea",
            notes="Tease the 90-day productivity course — include waitlist link",
            assigned_agent="loki",
        ),
    ]

    store.save_project(sample_book)
    store.save_project(sample_course)
    store.save_revenue_stream(sample_stream)
    for item in sample_items:
        store.save_calendar_item(item)

    logger.info(
        "PublishingStore seeded with 2 sample projects, 1 revenue stream, %d calendar items",
        len(sample_items),
    )
    return True


# ---------------------------------------------------------------------------
# Module-level singleton helpers
# ---------------------------------------------------------------------------

_publishing_singleton: PublishingSuiteOrchestrator | None = None


def init_publishing(runtime: Any = None) -> PublishingSuiteOrchestrator:
    """
    Create and initialise the module-level PublishingSuiteOrchestrator singleton.
    Safe to call multiple times — subsequent calls are no-ops.
    """
    global _publishing_singleton

    if _publishing_singleton is not None:
        return _publishing_singleton

    store = PublishingStore()
    seeded = seed_publishing_data(store)
    if seeded:
        logger.info("Publishing suite seeded with initial data")

    orchestrator = PublishingSuiteOrchestrator(store)
    _publishing_singleton = orchestrator
    logger.info("PublishingSuiteOrchestrator singleton initialised")
    return orchestrator


def get_publishing() -> PublishingSuiteOrchestrator | None:
    """Return the module-level PublishingSuiteOrchestrator singleton if initialised."""
    return _publishing_singleton
