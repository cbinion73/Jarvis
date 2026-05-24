"""
ghostwritr_bridge.py — JARVIS integration with the Ghostwritr platform
=======================================================================
Connects to Ghostwritr (Next.js on localhost:3000, PostgreSQL via Prisma)
to monitor book projects, detect stages ready for review, and route them
through the JARVIS approval queue.

Persistent storage: ~/.jarvis/publishing/ghostwritr_reviews.jsonl
  One DraftReview record per line (JARVIS-side tracking only).

HTTP: urllib.request (stdlib) — no requests library
DB:  psycopg2 (import-guarded — degrades gracefully if not installed)
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
import urllib.request
import urllib.error

logger = logging.getLogger("jarvis.ghostwritr_bridge")

# ---------------------------------------------------------------------------
# DB driver import guards (asyncpg preferred, psycopg2 as fallback)
# ---------------------------------------------------------------------------
try:
    import asyncpg  # type: ignore
    _ASYNCPG_AVAILABLE = True
except ImportError:
    _ASYNCPG_AVAILABLE = False

try:
    import psycopg2  # type: ignore
    import psycopg2.extras  # type: ignore
    _PSYCOPG2_AVAILABLE = True
except ImportError:
    _PSYCOPG2_AVAILABLE = False
    logger.debug("psycopg2 not installed — GhostwritrDB will fall back to asyncpg or be unavailable")

_DB_AVAILABLE = _ASYNCPG_AVAILABLE or _PSYCOPG2_AVAILABLE


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

NONFICTION_STAGES = [
    "BOOK_SETUP",
    "PROMISE",
    "AUDIENCE",
    "MARKET_ANALYSIS",
    "OUTLINE",
    "BASE_STORY",
    "RESEARCH",
    "EXTERNAL_STORIES",
    "PERSONAL_STORIES",
    "MANIFEST",
    "CHAPTER_DRAFT",
    "EDITING",
    "TYPESET",
    "LAUNCH_LISTING",
    "PRESS_KIT",
    "SOCIAL_CAMPAIGN",
    "AUDIO_PREP",
    "COURSE_DESIGN",
    "SPEAKING_KIT",
]

FICTION_STAGES = [
    "BOOK_SETUP",
    "STORY_SETUP",
    "STORY_CORE",
    "WORLD_CAST",
    "PLOT_BLUEPRINT",
    "SCENE_PLAN",
    "FICTION_DRAFT",
    "EDITING",
    "TYPESET",
    "LAUNCH_LISTING",
    "PRESS_KIT",
    "SOCIAL_CAMPAIGN",
]

STAGE_DISPLAY_NAMES: dict[str, str] = {
    # Setup
    "BOOK_SETUP": "Book Setup",
    "PROMISE": "Promise",
    "AUDIENCE": "Audience",
    "MARKET_ANALYSIS": "Market Analysis",
    # Material
    "OUTLINE": "Outline",
    "BASE_STORY": "Base Story",
    "RESEARCH": "Research",
    "EXTERNAL_STORIES": "External Stories",
    "PERSONAL_STORIES": "Personal Stories",
    # Production
    "MANIFEST": "Manifest",
    "CHAPTER_DRAFT": "Chapter Draft",
    "EDITING": "Editing",
    "TYPESET": "Typeset",
    # Post-Production
    "LAUNCH_LISTING": "Launch Listing",
    "PRESS_KIT": "Press Kit",
    "SOCIAL_CAMPAIGN": "Social Campaign",
    "AUDIO_PREP": "Audio Prep",
    "COURSE_DESIGN": "Course Design",
    "SPEAKING_KIT": "Speaking Kit",
    # Fiction-specific
    "STORY_SETUP": "Story Setup",
    "STORY_CORE": "Story Core",
    "WORLD_CAST": "World & Cast",
    "PLOT_BLUEPRINT": "Plot Blueprint",
    "SCENE_PLAN": "Scene Plan",
    "FICTION_DRAFT": "Fiction Draft",
}

# Stage groups matching Ghostwritr's sidebar navigation
STAGE_GROUPS: dict[str, list[str]] = {
    "SETUP": ["BOOK_SETUP", "PROMISE", "AUDIENCE", "MARKET_ANALYSIS"],
    "MATERIAL": ["OUTLINE", "BASE_STORY", "RESEARCH", "EXTERNAL_STORIES", "PERSONAL_STORIES"],
    "PRODUCTION": ["MANIFEST", "CHAPTER_DRAFT", "EDITING", "TYPESET"],
    "POST-PRODUCTION": ["LAUNCH_LISTING", "PRESS_KIT", "SOCIAL_CAMPAIGN", "AUDIO_PREP", "COURSE_DESIGN", "SPEAKING_KIT"],
}

# Stage statuses
STATUS_NOT_STARTED = "NOT_STARTED"
STATUS_IN_PROGRESS = "IN_PROGRESS"
STATUS_READY_FOR_REVIEW = "READY_FOR_REVIEW"
STATUS_COMMITTED = "COMMITTED"
STATUS_BLOCKED = "BLOCKED"

# Stages that count as "active" (not yet committed)
_ACTIVE_STATUSES = {STATUS_IN_PROGRESS, STATUS_READY_FOR_REVIEW, STATUS_BLOCKED}
_REVIEW_STATUSES = {STATUS_READY_FOR_REVIEW}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stage_display(key: str) -> str:
    return STAGE_DISPLAY_NAMES.get(key, key.replace("_", " ").title())


def _stages_for_workflow(workflow_type: str) -> list[str]:
    if workflow_type == "FICTION":
        return FICTION_STAGES
    return NONFICTION_STAGES


def _current_stage(stages: list[dict]) -> str:
    """Return the most advanced IN_PROGRESS or READY_FOR_REVIEW stage key."""
    # Order matters: check against the canonical stage order
    # We want the *last* (most advanced) stage that is active
    in_progress_keys = [
        s["stageKey"] for s in stages
        if s.get("status") in _ACTIVE_STATUSES
    ]
    return in_progress_keys[-1] if in_progress_keys else ""


def _compute_stage_groups(stages: list[dict]) -> list[dict]:
    """
    Compute stage group breakdown for UI display.
    Returns a list of group dicts ordered as: SETUP, MATERIAL, PRODUCTION, POST-PRODUCTION.
    Each group: {name, stages: [{key, display, status}], complete, total, group_status}
    group_status: 'committed' | 'in_progress' | 'review' | 'blocked' | 'not_started'
    """
    # Build a map of stageKey -> status from the stages list
    status_map: dict[str, str] = {}
    for s in stages:
        key = str(s.get("stageKey") or s.get("stage_key") or "")
        if key:
            status_map[key] = str(s.get("status") or STATUS_NOT_STARTED)

    result = []
    for group_name, group_keys in STAGE_GROUPS.items():
        stage_items = []
        committed = 0
        total = len(group_keys)
        has_review = False
        has_in_progress = False
        has_blocked = False

        for key in group_keys:
            st = status_map.get(key, STATUS_NOT_STARTED)
            stage_items.append({
                "key": key,
                "display": _stage_display(key),
                "status": st,
            })
            if st == STATUS_COMMITTED:
                committed += 1
            elif st == STATUS_READY_FOR_REVIEW:
                has_review = True
            elif st == STATUS_IN_PROGRESS:
                has_in_progress = True
            elif st == STATUS_BLOCKED:
                has_blocked = True

        # Derive group-level status
        if committed == total:
            group_status = "committed"
        elif has_review:
            group_status = "review"
        elif has_blocked:
            group_status = "blocked"
        elif has_in_progress:
            group_status = "in_progress"
        else:
            group_status = "not_started"

        result.append({
            "name": group_name,
            "stages": stage_items,
            "complete": committed,
            "total": total,
            "group_status": group_status,
        })
    return result


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    records: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return records


def _save_jsonl(path: Path, records: list[dict]) -> None:
    try:
        lines = [json.dumps(r, ensure_ascii=False) for r in records]
        path.write_text(
            "\n".join(lines) + ("\n" if lines else ""),
            encoding="utf-8",
        )
    except OSError as exc:
        logger.warning("GhostwritrBridge: failed to write %s: %s", path.name, exc)


def _make_review_id(book_id: str, stage_key: str) -> str:
    """Stable deterministic review_id from book + stage."""
    return str(uuid.uuid5(uuid.NAMESPACE_OID, f"{book_id}:{stage_key}"))


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class BookProject:
    """Represents one Ghostwritr book project."""
    book_id: str
    slug: str
    title: str
    subtitle: str
    workflow_type: str          # "NONFICTION" | "FICTION"
    book_status: str            # Ghostwritr Book.status
    current_stage: str          # most advanced IN_PROGRESS or READY_FOR_REVIEW stage key
    stages_complete: int        # count of COMMITTED stages
    total_stages: int           # 9 for nonfiction, 8 for fiction
    stages_ready_for_review: list  # stage keys with status READY_FOR_REVIEW
    last_activity: str          # ISO datetime of Book.updatedAt
    ghostwritr_url: str         # {base_url}/books/{slug}

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DraftReview:
    """JARVIS-side tracking record for a stage that is READY_FOR_REVIEW."""
    review_id: str              # uuid5(book_id + stage_key) — stable
    book_id: str
    slug: str
    title: str
    stage_key: str
    stage_display: str          # human name
    content_preview: str        # first 500 chars of active artifact content
    word_count: int
    ready_since: str            # ISO datetime
    jarvis_status: str          # "pending" | "approved" | "needs_revision"
    feedback: str
    approval_id: str            # JARVIS ApprovalQueue request_id if submitted

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "DraftReview":
        fields = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in fields})


# ---------------------------------------------------------------------------
# GhostwritrClient — HTTP layer
# ---------------------------------------------------------------------------

class GhostwritrClient:
    """
    HTTP client for the Ghostwritr Next.js API.
    All calls use urllib.request (stdlib). Never raises — returns {} on error.
    """

    DEFAULT_TIMEOUT = 10

    def __init__(self, base_url: str) -> None:
        self._base = base_url.rstrip("/")
        self._available_cache: bool | None = None
        self._available_checked_at: datetime | None = None
        self._CACHE_TTL = timedelta(seconds=30)

    def _get_json(self, path: str) -> dict:
        url = f"{self._base}{path}"
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=self.DEFAULT_TIMEOUT) as resp:
                raw = resp.read()
                return json.loads(raw)
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, OSError) as exc:
            logger.debug("GhostwritrClient GET %s failed: %s", path, exc)
            return {}

    def is_available(self) -> bool:
        """Check if the Ghostwritr server is up. Cached for 30s."""
        now = datetime.now(timezone.utc)
        if (
            self._available_cache is not None
            and self._available_checked_at is not None
            and now - self._available_checked_at < self._CACHE_TTL
        ):
            return self._available_cache

        try:
            req = urllib.request.Request(f"{self._base}/")
            with urllib.request.urlopen(req, timeout=self.DEFAULT_TIMEOUT) as resp:
                ok = resp.status < 500
        except Exception:
            ok = False

        self._available_cache = ok
        self._available_checked_at = now
        return ok

    def get_manuscript(self, slug: str) -> dict:
        """GET /api/books/{slug}/manuscript-export?format=json"""
        return self._get_json(f"/api/books/{slug}/manuscript-export?format=json")

    def get_promise(self, slug: str) -> dict:
        """GET /api/books/{slug}/promise-export?format=json"""
        return self._get_json(f"/api/books/{slug}/promise-export?format=json")

    def get_promise_status(self, slug: str) -> dict:
        """GET /api/books/{slug}/promise-status → {isRunning, elapsedSeconds}"""
        return self._get_json(f"/api/books/{slug}/promise-status")

    def get_chapter_progress(self, slug: str) -> dict:
        """GET /api/books/{slug}/outline/chapter-progress"""
        return self._get_json(f"/api/books/{slug}/outline/chapter-progress")

    def list_books_with_stages(self) -> list[dict]:
        """GET /api/internal/jarvis → [{id, slug, titleWorking, stages:[...]}]"""
        payload = self._get_json("/api/internal/jarvis")
        if payload.get("ok"):
            return payload.get("books") or []
        return []

    def trigger_workflow(self, run_id: str, internal_token: str) -> dict:
        """
        POST /api/internal/workflow-runs/process
        Requires x-internal-workflow-token header and body {runId}.
        Returns {} on any error.
        """
        url = f"{self._base}/api/internal/workflow-runs/process"
        body = json.dumps({"runId": run_id}).encode("utf-8")
        try:
            req = urllib.request.Request(
                url,
                data=body,
                method="POST",
                headers={
                    "Content-Type": "application/json",
                    "x-internal-workflow-token": internal_token,
                },
            )
            with urllib.request.urlopen(req, timeout=self.DEFAULT_TIMEOUT) as resp:
                raw = resp.read()
                return json.loads(raw)
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, OSError) as exc:
            logger.debug("GhostwritrClient POST workflow-runs/process failed: %s", exc)
            return {}


# ---------------------------------------------------------------------------
# GhostwritrDB — direct PostgreSQL reads
# ---------------------------------------------------------------------------

class GhostwritrDB:
    """
    Direct read access to the Ghostwritr PostgreSQL database.

    Uses asyncpg (native async driver) when available, falling back to
    psycopg2 run in a thread executor.  All public methods are synchronous
    wrappers — async callers should use run_in_executor.  All methods return
    empty / False results on error and never raise.
    """

    def __init__(self, db_url: str) -> None:
        self._db_url = db_url
        self._available_cache: bool | None = None
        self._available_checked_at: datetime | None = None
        # Cache success for 60s; cache failure for 15s so we retry reasonably fast
        self._CACHE_TTL_OK = timedelta(seconds=60)
        self._CACHE_TTL_FAIL = timedelta(seconds=15)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _connect_sync(self):
        """Open a synchronous psycopg2 connection. Returns None on failure."""
        if not _PSYCOPG2_AVAILABLE:
            return None
        try:
            return psycopg2.connect(self._db_url, connect_timeout=8)
        except Exception as exc:
            logger.debug("GhostwritrDB psycopg2 connect failed: %s", exc)
            return None

    def _run_sync_query(self, sql: str, params=None) -> list[dict]:
        """Run a read query in a new psycopg2 connection. Returns rows as dicts."""
        conn = self._connect_sync()
        if conn is None:
            return []
        try:
            with conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(sql, params)
                    return [dict(r) for r in cur.fetchall()]
        except Exception as exc:
            logger.debug("GhostwritrDB query failed: %s", exc)
            return []
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def is_available(self) -> bool:
        """Test DB connection. Cached 60s on success, 15s on failure."""
        if not _PSYCOPG2_AVAILABLE:
            return False

        now = datetime.now(timezone.utc)
        if (
            self._available_cache is not None
            and self._available_checked_at is not None
        ):
            ttl = self._CACHE_TTL_OK if self._available_cache else self._CACHE_TTL_FAIL
            if now - self._available_checked_at < ttl:
                return self._available_cache

        conn = self._connect_sync()
        ok = conn is not None
        if conn:
            try:
                conn.close()
            except Exception:
                pass

        self._available_cache = ok
        self._available_checked_at = now
        return ok

    def list_books(self) -> list[dict]:
        """
        SELECT id, slug, titleWorking, subtitle, status, workflowType,
               createdAt, updatedAt FROM "Book" ORDER BY "updatedAt" DESC
        """
        if not _PSYCOPG2_AVAILABLE:
            return []
        conn = self._connect_sync()
        if conn is None:
            return []
        try:
            with conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(
                        """
                        SELECT id, slug, "titleWorking", subtitle, status,
                               "workflowType", "createdAt", "updatedAt"
                        FROM "Book"
                        ORDER BY "updatedAt" DESC
                        """
                    )
                    rows = cur.fetchall()
                    return [dict(r) for r in rows]
        except Exception as exc:
            logger.debug("GhostwritrDB.list_books failed: %s", exc)
            return []
        finally:
            conn.close()

    def get_book_stages(self, book_id: str) -> list[dict]:
        """SELECT * FROM "BookStage" WHERE bookId = book_id"""
        if not _PSYCOPG2_AVAILABLE:
            return []
        conn = self._connect_sync()
        if conn is None:
            return []
        try:
            with conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(
                        'SELECT * FROM "BookStage" WHERE "bookId" = %s',
                        (book_id,),
                    )
                    rows = cur.fetchall()
                    return [dict(r) for r in rows]
        except Exception as exc:
            logger.debug("GhostwritrDB.get_book_stages failed: %s", exc)
            return []
        finally:
            conn.close()

    def get_book_with_stages(self, slug: str) -> dict:
        """Return book row joined with its stages."""
        if not _PSYCOPG2_AVAILABLE:
            return {}
        conn = self._connect_sync()
        if conn is None:
            return {}
        try:
            with conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(
                        """
                        SELECT id, slug, "titleWorking", subtitle, status,
                               "workflowType", "createdAt", "updatedAt"
                        FROM "Book"
                        WHERE slug = %s
                        LIMIT 1
                        """,
                        (slug,),
                    )
                    book_row = cur.fetchone()
                    if book_row is None:
                        return {}
                    book = dict(book_row)

                    cur.execute(
                        'SELECT * FROM "BookStage" WHERE "bookId" = %s',
                        (book["id"],),
                    )
                    stages = [dict(r) for r in cur.fetchall()]
                    book["stages"] = stages
                    return book
        except Exception as exc:
            logger.debug("GhostwritrDB.get_book_with_stages failed: %s", exc)
            return {}
        finally:
            conn.close()

    def get_active_artifact_content(self, book_id: str, stage_key: str) -> tuple[str, int]:
        """
        Fetch the active artifact version content for a given book stage.
        Returns (content_text, word_count). Returns ("", 0) on any error.
        Traverses: BookStage → Artifact → ArtifactVersion (active).
        """
        if not _PSYCOPG2_AVAILABLE:
            return "", 0
        conn = self._connect_sync()
        if conn is None:
            return "", 0
        try:
            with conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    # Get the stage
                    cur.execute(
                        'SELECT id FROM "BookStage" WHERE "bookId" = %s AND "stageKey" = %s LIMIT 1',
                        (book_id, stage_key),
                    )
                    stage_row = cur.fetchone()
                    if stage_row is None:
                        return "", 0

                    # Get the first artifact for this stage
                    cur.execute(
                        'SELECT id, "currentVersionId" FROM "Artifact" WHERE "stageId" = %s LIMIT 1',
                        (stage_row["id"],),
                    )
                    artifact_row = cur.fetchone()
                    if artifact_row is None or artifact_row["currentVersionId"] is None:
                        return "", 0

                    # Get the active version content
                    cur.execute(
                        'SELECT "contentText", "contentJson" FROM "ArtifactVersion" WHERE id = %s LIMIT 1',
                        (artifact_row["currentVersionId"],),
                    )
                    ver_row = cur.fetchone()
                    if ver_row is None:
                        return "", 0

                    content_text: str = ver_row["contentText"] or ""
                    if not content_text and ver_row["contentJson"]:
                        # Fall back to serializing the JSON blob
                        try:
                            cj = ver_row["contentJson"]
                            if isinstance(cj, str):
                                cj = json.loads(cj)
                            content_text = json.dumps(cj)
                        except Exception:
                            content_text = ""

                    word_count = len(content_text.split()) if content_text else 0
                    return content_text, word_count
        except Exception as exc:
            logger.debug("GhostwritrDB.get_active_artifact_content failed: %s", exc)
            return "", 0
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# GhostwritrBridge — main coordinator
# ---------------------------------------------------------------------------

class GhostwritrBridge:
    """
    Bridges JARVIS and Ghostwritr.

    - Reads book/stage data from the Ghostwritr DB (psycopg2)
    - Fetches content previews via the Ghostwritr HTTP API
    - Routes READY_FOR_REVIEW stages to the JARVIS approval queue
    - Persists DraftReview records to ~/.jarvis/publishing/ghostwritr_reviews.jsonl
    """

    REVIEWS_FILENAME = "ghostwritr_reviews.jsonl"

    def __init__(
        self,
        base_url: str | None = None,
        db_url: str | None = None,
        internal_token: str | None = None,
    ) -> None:
        self._base_url = (
            base_url
            or os.environ.get("GHOSTWRITR_BASE_URL", "http://localhost:3000")
        ).rstrip("/")
        self._db_url = (
            db_url
            or os.environ.get(
                "GHOSTWRITR_DB_URL",
                "postgresql://postgres:postgres@localhost:5432/book_platform_builder",
            )
        )
        self._internal_token = (
            internal_token
            or os.environ.get("GHOSTWRITR_INTERNAL_TOKEN", "")
        )

        self._client = GhostwritrClient(self._base_url)
        self._db = GhostwritrDB(self._db_url)

        # Persistent storage
        self._root = Path.home() / ".jarvis" / "publishing"
        self._root.mkdir(parents=True, exist_ok=True)
        self._reviews_path = self._root / self.REVIEWS_FILENAME

    # ------------------------------------------------------------------
    # Internal JSONL helpers
    # ------------------------------------------------------------------

    def _load_reviews(self) -> list[dict]:
        return _load_jsonl(self._reviews_path)

    def _save_reviews(self, records: list[dict]) -> None:
        _save_jsonl(self._reviews_path, records)

    def _upsert_review(self, review: DraftReview) -> None:
        """Insert or update a review record by review_id."""
        records = self._load_reviews()
        for i, r in enumerate(records):
            if r.get("review_id") == review.review_id:
                records[i] = review.to_dict()
                self._save_reviews(records)
                return
        records.append(review.to_dict())
        self._save_reviews(records)

    def _get_review(self, review_id: str) -> DraftReview | None:
        for r in self._load_reviews():
            if r.get("review_id") == review_id:
                try:
                    return DraftReview.from_dict(r)
                except Exception:
                    return None
        return None

    def _review_exists(self, review_id: str) -> bool:
        return any(r.get("review_id") == review_id for r in self._load_reviews())

    # ------------------------------------------------------------------
    # Book data
    # ------------------------------------------------------------------

    def _rows_to_book_project(self, book: dict, stages: list[dict]) -> BookProject:
        workflow = str(book.get("workflowType") or "NONFICTION")
        total = len(_stages_for_workflow(workflow))
        committed = sum(1 for s in stages if s.get("status") == STATUS_COMMITTED)
        ready_keys = [
            s["stageKey"] for s in stages
            if s.get("status") == STATUS_READY_FOR_REVIEW
        ]
        cur_stage = _current_stage(stages)

        updated_at = book.get("updatedAt")
        if isinstance(updated_at, datetime):
            last_activity = updated_at.isoformat()
        else:
            last_activity = str(updated_at) if updated_at else _now_iso()

        return BookProject(
            book_id=str(book.get("id", "")),
            slug=str(book.get("slug", "")),
            title=str(book.get("titleWorking") or "Untitled"),
            subtitle=str(book.get("subtitle") or ""),
            workflow_type=workflow,
            book_status=str(book.get("status") or ""),
            current_stage=cur_stage,
            stages_complete=committed,
            total_stages=total,
            stages_ready_for_review=ready_keys,
            last_activity=last_activity,
            ghostwritr_url=f"{self._base_url}/books/{book.get('slug', '')}",
        )

    def _list_books_with_stages(self) -> list[tuple[dict, list[dict]]]:
        """
        Return list of (book_row, stages_rows).
        Prefers HTTP API (always works via port 3000); falls back to DB.
        """
        # Try HTTP API first — works even when direct Postgres is blocked
        http_books = self._client.list_books_with_stages()
        if http_books:
            result = []
            for b in http_books:
                book_row = {
                    "id": b.get("id", ""),
                    "slug": b.get("slug", ""),
                    "titleWorking": b.get("titleWorking"),
                    "subtitle": b.get("subtitle"),
                    "status": b.get("status", ""),
                    "workflowType": b.get("workflowType", ""),
                    "createdAt": b.get("createdAt"),
                    "updatedAt": b.get("updatedAt"),
                }
                stages = b.get("stages") or []
                result.append((book_row, stages))
            return result
        # Fallback: direct Postgres
        if self._db.is_available():
            books = self._db.list_books()
            return [(b, self._db.get_book_stages(str(b.get("id", "")))) for b in books]
        return []

    def get_active_books(self) -> list[BookProject]:
        """
        Return all books mapped to BookProject.
        Uses HTTP API first, falls back to direct DB.
        """
        pairs = self._list_books_with_stages()
        result: list[BookProject] = []
        for book, stages in pairs:
            try:
                result.append(self._rows_to_book_project(book, stages))
            except Exception as exc:
                logger.debug("GhostwritrBridge: failed to map book %s: %s", book.get("id"), exc)
        return result

    # ------------------------------------------------------------------
    # Review detection and management
    # ------------------------------------------------------------------

    def check_for_new_reviews(self) -> list[DraftReview]:
        """
        Scan all books for READY_FOR_REVIEW stages not yet tracked in our JSONL.
        For each new one: fetch content preview, submit to JARVIS approval queue,
        save to JSONL.
        Returns the list of newly discovered DraftReview records.
        Uses HTTP API first; falls back to direct DB.
        """
        pairs = self._list_books_with_stages()
        if not pairs:
            logger.debug("GhostwritrBridge.check_for_new_reviews: no books available via HTTP or DB")
            return []

        new_reviews: list[DraftReview] = []

        for book, stages in pairs:
            book_id = str(book.get("id", ""))
            slug = str(book.get("slug", ""))
            title = str(book.get("titleWorking") or "Untitled")

            ready_stages = [s for s in stages if s.get("status") == STATUS_READY_FOR_REVIEW]
            for stage in ready_stages:
                stage_key = str(stage.get("stageKey", ""))
                review_id = _make_review_id(book_id, stage_key)

                if self._review_exists(review_id):
                    continue

                # Fetch content preview
                content_text = ""
                word_count = 0
                try:
                    content_text, word_count = self._db.get_active_artifact_content(book_id, stage_key)
                except Exception as exc:
                    logger.debug("GhostwritrBridge: content fetch failed for %s/%s: %s", slug, stage_key, exc)

                # Fall back to manuscript export if DB content not found
                if not content_text and self._client.is_available():
                    manuscript = self._client.get_manuscript(slug)
                    if manuscript:
                        # Try to find content for this stage in the manuscript
                        content_text = str(manuscript.get("content") or manuscript.get("text") or "")
                        if not content_text:
                            content_text = json.dumps(manuscript)[:500]
                        word_count = len(content_text.split())

                content_preview = content_text[:500]

                # Determine ready_since from stage metadata or now
                ready_since = _now_iso()
                metadata = stage.get("metadataJson")
                if metadata:
                    try:
                        if isinstance(metadata, str):
                            metadata = json.loads(metadata)
                        ready_since = metadata.get("readySince") or metadata.get("updatedAt") or ready_since
                    except Exception:
                        pass

                updated_at = book.get("updatedAt")
                if isinstance(updated_at, datetime):
                    ready_since = updated_at.isoformat()
                elif isinstance(updated_at, str) and updated_at:
                    ready_since = updated_at

                review = DraftReview(
                    review_id=review_id,
                    book_id=book_id,
                    slug=slug,
                    title=title,
                    stage_key=stage_key,
                    stage_display=_stage_display(stage_key),
                    content_preview=content_preview,
                    word_count=word_count,
                    ready_since=ready_since,
                    jarvis_status="pending",
                    feedback="",
                    approval_id="",
                )

                # Submit to JARVIS approval queue
                approval_id = ""
                try:
                    from .approvals import request_document_review
                    approval_id = request_document_review(
                        title=f"{title} — {_stage_display(stage_key)}",
                        preview=content_preview,
                        submission_id=review_id,
                        track_type=stage_key,
                        project_id=book_id,
                        ghostwritr_url=f"{self._base_url}/books/{slug}",
                    ) or ""
                except Exception as exc:
                    logger.warning("GhostwritrBridge: approval queue unavailable: %s", exc)

                review.approval_id = approval_id
                self._upsert_review(review)
                new_reviews.append(review)
                logger.info(
                    "GhostwritrBridge: new review queued — book=%s stage=%s review_id=%s",
                    slug, stage_key, review_id,
                )

        return new_reviews

    def get_pending_reviews(self) -> list[DraftReview]:
        """Return all DraftReview records with jarvis_status='pending'."""
        result: list[DraftReview] = []
        for raw in self._load_reviews():
            if raw.get("jarvis_status") == "pending":
                try:
                    result.append(DraftReview.from_dict(raw))
                except Exception:
                    pass
        result.sort(key=lambda r: r.ready_since)
        return result

    def mark_approved(self, review_id: str, feedback: str = "") -> DraftReview | None:
        """Mark a review as approved."""
        review = self._get_review(review_id)
        if review is None:
            logger.warning("GhostwritrBridge.mark_approved: review %s not found", review_id)
            return None
        review.jarvis_status = "approved"
        review.feedback = feedback
        self._upsert_review(review)
        logger.info("GhostwritrBridge: review %s approved", review_id)
        return review

    def mark_needs_revision(self, review_id: str, feedback: str) -> DraftReview | None:
        """Mark a review as needing revision with feedback."""
        review = self._get_review(review_id)
        if review is None:
            logger.warning("GhostwritrBridge.mark_needs_revision: review %s not found", review_id)
            return None
        review.jarvis_status = "needs_revision"
        review.feedback = feedback
        self._upsert_review(review)
        logger.info("GhostwritrBridge: review %s marked needs_revision", review_id)
        return review

    # ------------------------------------------------------------------
    # Dashboard and summaries
    # ------------------------------------------------------------------

    def get_publishing_dashboard(self) -> dict[str, Any]:
        """
        Full publishing dashboard dict.
        Shape:
          {
            "ghostwritr_available": bool,
            "db_available": bool,
            "active_books": [BookProject.to_dict() + stage_groups + word_count...],
            "pending_reviews": int,
            "pending_review_list": [DraftReview.to_dict()...],
            "total_books": int,
            "books_in_progress": int,
          }
        """
        ghostwritr_up = self._client.is_available()
        # db_available shows whether direct Postgres works (informational only;
        # get_active_books() uses HTTP API first so this doesn't gate data)
        db_up = self._db.is_available()

        # Fetch raw pairs so we can compute stage groups from the full stage list
        pairs = self._list_books_with_stages()
        active_books: list[BookProject] = []
        books_with_groups: list[dict] = []

        for book, stages in pairs:
            try:
                bp = self._rows_to_book_project(book, stages)
                active_books.append(bp)
                book_dict = bp.to_dict()
                book_dict["stage_groups"] = _compute_stage_groups(stages)
                # Attempt lightweight word-count from manuscript export
                word_count = 0
                chapter_count = 0
                try:
                    if ghostwritr_up:
                        ms = self._client.get_manuscript(bp.slug)
                        chapters = ms.get("chapters") or [] if ms else []
                        if isinstance(chapters, list):
                            chapter_count = len(chapters)
                            for ch in chapters:
                                content = ch.get("content") or ch.get("text") or ""
                                word_count += len(str(content).split())
                except Exception:
                    pass
                book_dict["word_count"] = word_count
                book_dict["chapter_count"] = chapter_count
                books_with_groups.append(book_dict)
            except Exception as exc:
                logger.debug("GhostwritrBridge dashboard: failed to map book %s: %s",
                             book.get("id"), exc)

        pending = self.get_pending_reviews()

        books_in_progress = sum(
            1 for b in active_books
            if b.book_status not in ("PUBLISHED", "ARCHIVED", "")
        )

        return {
            "ghostwritr_available": ghostwritr_up,
            "db_available": db_up,
            "active_books": books_with_groups,
            "pending_reviews": len(pending),
            "pending_review_list": [r.to_dict() for r in pending],
            "total_books": len(active_books),
            "books_in_progress": books_in_progress,
        }

    def get_book_summary(self, slug: str) -> dict[str, Any]:
        """
        Return title + chapter count + total word count + stage progress
        for a specific book slug.
        """
        book = self._db.get_book_with_stages(slug)
        title = str(book.get("titleWorking") or slug)
        stages = book.get("stages", [])
        committed = sum(1 for s in stages if s.get("status") == STATUS_COMMITTED)
        total_stages = len(stages)

        # Fetch manuscript for word count
        manuscript = {}
        if self._client.is_available():
            manuscript = self._client.get_manuscript(slug)

        chapter_count = 0
        total_word_count = 0
        if manuscript:
            chapters = manuscript.get("chapters") or []
            if isinstance(chapters, list):
                chapter_count = len(chapters)
                for ch in chapters:
                    content = ch.get("content") or ch.get("text") or ""
                    total_word_count += len(str(content).split())
            else:
                content = manuscript.get("content") or manuscript.get("text") or ""
                total_word_count = len(str(content).split())

        return {
            "slug": slug,
            "title": title,
            "chapter_count": chapter_count,
            "total_word_count": total_word_count,
            "stages_complete": committed,
            "total_stages": total_stages,
            "stage_progress": f"{committed}/{total_stages}",
        }


# ---------------------------------------------------------------------------
# StanLeeWorkflow — agent-level coordinator
# ---------------------------------------------------------------------------

class StanLeeWorkflow:
    """
    High-level workflow coordinator for Stan Lee's publishing operations.
    Wraps GhostwritrBridge with agent-specific business logic for the
    JARVIS morning briefing and feedback routing.
    """

    def __init__(self, bridge: GhostwritrBridge) -> None:
        self._bridge = bridge

    def on_morning_briefing(self) -> dict[str, Any]:
        """
        Check for new READY_FOR_REVIEW stages, collect all outstanding reviews.
        Returns briefing payload with summary, items, action_needed.
        """
        new_reviews = self._bridge.check_for_new_reviews()
        pending = self._bridge.get_pending_reviews()
        active_books = self._bridge.get_active_books()

        action_needed = bool(pending)
        items: list[str] = []

        if new_reviews:
            for r in new_reviews[:5]:
                items.append(
                    f"NEW: '{r.title}' — {r.stage_display} is ready for review"
                )

        if pending:
            for r in pending[:5]:
                items.append(
                    f"PENDING: '{r.title}' — {r.stage_display} (since {r.ready_since[:10]})"
                )

        for b in active_books[:5]:
            if b.current_stage:
                items.append(
                    f"{b.title}: {_stage_display(b.current_stage)} "
                    f"({b.stages_complete}/{b.total_stages} stages complete)"
                )

        summary = (
            f"{len(active_books)} active book(s), "
            f"{len(new_reviews)} new stage(s) ready for review, "
            f"{len(pending)} pending review(s)."
        )

        return {
            "summary": summary,
            "items": items,
            "action_needed": action_needed,
            "new_reviews_count": len(new_reviews),
            "pending_count": len(pending),
        }

    def get_stan_lee_briefing_item(self) -> dict[str, Any]:
        """Return a briefing dict suitable for the JARVIS morning briefing system."""
        morning = self.on_morning_briefing()
        pending = self._bridge.get_pending_reviews()

        return {
            "agent": "Stan Lee",
            "domain": "ghostwritr",
            "summary": morning["summary"],
            "items": morning["items"],
            "action_needed": morning["action_needed"],
            "new_reviews_count": morning["new_reviews_count"],
            "pending_count": morning["pending_count"],
            "pending_reviews": [r.to_dict() for r in pending],
            "generated_at": _now_iso(),
        }

    def on_feedback_received(self, review_id: str, feedback: str) -> dict[str, Any]:
        """
        Mark a review as needs_revision and package feedback for Ghostwritr.
        Returns a dict ready to show Chris (stub for sending back to Ghostwritr —
        Ghostwritr has no inbound feedback API; this is prep for manual action).
        """
        review = self._bridge.mark_needs_revision(review_id, feedback)
        if review is None:
            return {
                "status": "error",
                "review_id": review_id,
                "detail": "Review not found",
            }
        return {
            "status": "feedback_recorded",
            "review_id": review_id,
            "book": review.title,
            "stage": review.stage_display,
            "ghostwritr_url": f"{self._bridge._base_url}/books/{review.slug}",
            "ghostwritr_api_payload": {
                "review_id": review_id,
                "action": "request_revision",
                "stage_key": review.stage_key,
                "feedback": feedback,
                "timestamp": _now_iso(),
            },
            "note": (
                "Ghostwritr has no inbound feedback API. "
                "Open the URL above and apply this feedback manually."
            ),
        }


# ---------------------------------------------------------------------------
# Module-level singletons
# ---------------------------------------------------------------------------

_bridge_singleton: GhostwritrBridge | None = None
_workflow_singleton: StanLeeWorkflow | None = None


def init_ghostwritr_bridge(config: dict | None = None) -> tuple[GhostwritrBridge, StanLeeWorkflow]:
    """
    Create and initialise the module-level GhostwritrBridge and StanLeeWorkflow
    singletons. Safe to call multiple times — subsequent calls are no-ops.

    config dict keys (all optional):
      base_url, db_url, internal_token
    """
    global _bridge_singleton, _workflow_singleton

    if _bridge_singleton is not None:
        assert _workflow_singleton is not None
        return _bridge_singleton, _workflow_singleton

    cfg = config or {}
    bridge = GhostwritrBridge(
        base_url=cfg.get("base_url"),
        db_url=cfg.get("db_url"),
        internal_token=cfg.get("internal_token"),
    )
    workflow = StanLeeWorkflow(bridge)

    _bridge_singleton = bridge
    _workflow_singleton = workflow

    # Skip DB availability check here — it's checked lazily on first use.
    # This prevents a 15s startup stall if Postgres.app is still waking up.
    logger.info(
        "GhostwritrBridge singleton initialised (base=%s)",
        bridge._base_url,
    )
    return bridge, workflow


def get_ghostwritr_bridge() -> GhostwritrBridge | None:
    """Return the module-level GhostwritrBridge singleton (None if not initialised)."""
    return _bridge_singleton


def get_stan_lee_workflow() -> StanLeeWorkflow | None:
    """Return the module-level StanLeeWorkflow singleton (None if not initialised)."""
    return _workflow_singleton
