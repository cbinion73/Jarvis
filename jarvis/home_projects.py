"""
home_projects.py — Database access layer for JARVIS Home Intelligence System.

Database: postgresql://chris@127.0.0.1:5432/jarvis_home
Uses psycopg2 with RealDictCursor. Pure sync, thread-pool safe.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

import psycopg2
import psycopg2.extras

from .data_hygiene import filter_records

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _serialize(row: dict) -> dict:
    """Convert UUID, datetime, Decimal, and date objects to JSON-safe types."""
    out = {}
    for k, v in row.items():
        if isinstance(v, uuid.UUID):
            out[k] = str(v)
        elif isinstance(v, datetime):
            out[k] = v.isoformat()
        elif isinstance(v, date):
            out[k] = v.isoformat()
        elif isinstance(v, Decimal):
            out[k] = float(v)
        else:
            out[k] = v
    return out


def _rows(cursor) -> list[dict]:
    return [_serialize(dict(r)) for r in cursor.fetchall()]


def _one(cursor) -> dict | None:
    row = cursor.fetchone()
    return _serialize(dict(row)) if row else None


def _build_set_clause(data: dict, excluded: set[str] | None = None) -> tuple[str, list]:
    """Build SET col = %s, ... clause and values list from a dict."""
    excluded = excluded or set()
    cols = [k for k in data if k not in excluded]
    clause = ", ".join(f"{c} = %s" for c in cols)
    values = [data[c] for c in cols]
    return clause, values


# ---------------------------------------------------------------------------
# Core class
# ---------------------------------------------------------------------------

class HomeDB:
    """Synchronous database access layer for jarvis_home."""

    def __init__(self, db_url: str) -> None:
        self._db_url = db_url
        log.info("HomeDB initialised (url=%s)", db_url)

    # ── Connection ──────────────────────────────────────────────────────────

    def _connect(self):
        """Return a psycopg2 connection with autocommit=False."""
        conn = psycopg2.connect(self._db_url)
        conn.autocommit = False
        return conn

    # ── Projects ────────────────────────────────────────────────────────────

    def list_projects(self, status: str | None = None, track: str | None = None) -> list[dict]:
        """Return all projects, optionally filtered by status and/or track."""
        sql = "SELECT * FROM home_projects WHERE 1=1"
        params: list[Any] = []
        if status:
            sql += " AND status = %s"
            params.append(status)
        if track:
            sql += " AND track = %s"
            params.append(track)
        sql += " ORDER BY created_at DESC"
        try:
            with self._connect() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(sql, params)
                    return _rows(cur)
        except Exception:
            log.exception("list_projects failed")
            raise

    def get_project(self, project_id: str) -> dict | None:
        """Return a single project by ID, or None if not found."""
        try:
            with self._connect() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute("SELECT * FROM home_projects WHERE id = %s", (project_id,))
                    return _one(cur)
        except Exception:
            log.exception("get_project failed project_id=%s", project_id)
            raise

    def create_project(self, data: dict) -> dict:
        """Insert a new project and return the created row."""
        fields = [
            "title", "track", "category", "status",
            "problem_statement", "objective",
            "projected_value", "realized_value", "payback_months",
            "start_date", "target_date", "notes",
        ]
        present = {k: data[k] for k in fields if k in data}
        cols = ", ".join(present.keys())
        placeholders = ", ".join(["%s"] * len(present))
        sql = (
            f"INSERT INTO home_projects ({cols}) VALUES ({placeholders}) RETURNING *"
        )
        try:
            with self._connect() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(sql, list(present.values()))
                    row = _one(cur)
                conn.commit()
            log.info("create_project id=%s title=%s", row["id"], row.get("title"))
            return row
        except Exception:
            log.exception("create_project failed data=%s", data)
            raise

    def update_project(self, project_id: str, data: dict) -> dict:
        """Update project fields and return the updated row."""
        excluded = {"id", "created_at"}
        data = {**data, "updated_at": datetime.now(timezone.utc)}
        set_clause, values = _build_set_clause(data, excluded)
        sql = f"UPDATE home_projects SET {set_clause} WHERE id = %s RETURNING *"
        try:
            with self._connect() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(sql, values + [project_id])
                    row = _one(cur)
                conn.commit()
            if row is None:
                raise ValueError(f"Project {project_id} not found")
            log.info("update_project id=%s", project_id)
            return row
        except Exception:
            log.exception("update_project failed project_id=%s", project_id)
            raise

    def get_project_summary(self) -> dict:
        """Return counts by status/track and total projected/realized value."""
        try:
            with self._connect() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute("""
                        SELECT
                            status,
                            track,
                            COUNT(*) AS cnt,
                            SUM(projected_value) AS projected,
                            SUM(realized_value)  AS realized
                        FROM home_projects
                        GROUP BY status, track
                    """)
                    rows = _rows(cur)
            by_status: dict[str, int] = {}
            by_track: dict[str, int] = {}
            total_projected = 0.0
            total_realized = 0.0
            for r in rows:
                by_status[r["status"]] = by_status.get(r["status"], 0) + int(r["cnt"])
                by_track[r["track"]] = by_track.get(r["track"], 0) + int(r["cnt"])
                total_projected += float(r["projected"] or 0)
                total_realized += float(r["realized"] or 0)
            return {
                "by_status": by_status,
                "by_track": by_track,
                "total_projected_value": round(total_projected, 2),
                "total_realized_value": round(total_realized, 2),
            }
        except Exception:
            log.exception("get_project_summary failed")
            raise

    # ── Tasks ───────────────────────────────────────────────────────────────

    def list_tasks(
        self,
        project_id: str | None = None,
        status: str | None = None,
        due_before: str | None = None,
    ) -> list[dict]:
        """Return tasks, optionally filtered by project, status, due_before."""
        sql = "SELECT * FROM project_tasks WHERE 1=1"
        params: list[Any] = []
        if project_id:
            sql += " AND project_id = %s"
            params.append(project_id)
        if status:
            sql += " AND status = %s"
            params.append(status)
        if due_before:
            sql += " AND due_date <= %s"
            params.append(due_before)
        sql += " ORDER BY due_date ASC NULLS LAST, priority DESC, created_at DESC"
        try:
            with self._connect() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(sql, params)
                    return _rows(cur)
        except Exception:
            log.exception("list_tasks failed")
            raise

    def get_task(self, task_id: str) -> dict | None:
        try:
            with self._connect() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute("SELECT * FROM project_tasks WHERE id = %s", (task_id,))
                    return _one(cur)
        except Exception:
            log.exception("get_task failed task_id=%s", task_id)
            raise

    def create_task(self, data: dict) -> dict:
        fields = [
            "project_id", "title", "description", "status", "priority",
            "due_date", "blocked_reason", "next_step", "source", "source_signal_id",
        ]
        present = {k: data[k] for k in fields if k in data}
        cols = ", ".join(present.keys())
        placeholders = ", ".join(["%s"] * len(present))
        sql = f"INSERT INTO project_tasks ({cols}) VALUES ({placeholders}) RETURNING *"
        try:
            with self._connect() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(sql, list(present.values()))
                    row = _one(cur)
                conn.commit()
            log.info("create_task id=%s title=%s", row["id"], row.get("title"))
            return row
        except Exception:
            log.exception("create_task failed data=%s", data)
            raise

    def update_task(self, task_id: str, data: dict) -> dict:
        excluded = {"id", "created_at"}
        data = {**data, "updated_at": datetime.now(timezone.utc)}
        set_clause, values = _build_set_clause(data, excluded)
        sql = f"UPDATE project_tasks SET {set_clause} WHERE id = %s RETURNING *"
        try:
            with self._connect() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(sql, values + [task_id])
                    row = _one(cur)
                conn.commit()
            if row is None:
                raise ValueError(f"Task {task_id} not found")
            log.info("update_task id=%s", task_id)
            return row
        except Exception:
            log.exception("update_task failed task_id=%s", task_id)
            raise

    def complete_task(self, task_id: str) -> dict:
        """Mark a task as complete and stamp completed_at."""
        now = datetime.now(timezone.utc)
        sql = """
            UPDATE project_tasks
               SET status = 'complete', completed_at = %s, updated_at = %s
             WHERE id = %s
         RETURNING *
        """
        try:
            with self._connect() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(sql, (now, now, task_id))
                    row = _one(cur)
                conn.commit()
            if row is None:
                raise ValueError(f"Task {task_id} not found")
            log.info("complete_task id=%s", task_id)
            return row
        except Exception:
            log.exception("complete_task failed task_id=%s", task_id)
            raise

    def get_overdue_tasks(self) -> list[dict]:
        """Return open/in_progress/blocked tasks whose due_date is in the past."""
        sql = """
            SELECT * FROM project_tasks
             WHERE status NOT IN ('complete','dismissed')
               AND due_date < CURRENT_DATE
             ORDER BY due_date ASC
        """
        try:
            with self._connect() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(sql)
                    return _rows(cur)
        except Exception:
            log.exception("get_overdue_tasks failed")
            raise

    def get_tasks_due_today(self) -> list[dict]:
        """Return open/in_progress/blocked tasks due today."""
        sql = """
            SELECT * FROM project_tasks
             WHERE status NOT IN ('complete','dismissed')
               AND due_date = CURRENT_DATE
             ORDER BY priority DESC
        """
        try:
            with self._connect() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(sql)
                    return _rows(cur)
        except Exception:
            log.exception("get_tasks_due_today failed")
            raise

    # ── Signals ─────────────────────────────────────────────────────────────

    def create_signal(self, data: dict) -> dict:
        fields = [
            "type", "source", "subject", "body", "sender",
            "external_id", "project_id", "classification",
            "extracted_tasks", "signal_date",
        ]
        present = {k: data[k] for k in fields if k in data}
        # JSONB: ensure extracted_tasks is serialised
        if "extracted_tasks" in present and isinstance(present["extracted_tasks"], (list, dict)):
            present["extracted_tasks"] = json.dumps(present["extracted_tasks"])
        cols = ", ".join(present.keys())
        placeholders = ", ".join(["%s"] * len(present))
        sql = f"INSERT INTO home_signals ({cols}) VALUES ({placeholders}) RETURNING *"
        try:
            with self._connect() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(sql, list(present.values()))
                    row = _one(cur)
                conn.commit()
            log.info("create_signal id=%s type=%s source=%s", row["id"], row.get("type"), row.get("source"))
            return row
        except Exception:
            log.exception("create_signal failed data=%s", data)
            raise

    def list_unclassified_signals(self, limit: int = 50) -> list[dict]:
        sql = """
            SELECT * FROM home_signals
             WHERE classified = FALSE
             ORDER BY signal_date DESC NULLS LAST, created_at DESC
             LIMIT %s
        """
        try:
            with self._connect() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(sql, (limit,))
                    return _rows(cur)
        except Exception:
            log.exception("list_unclassified_signals failed")
            raise

    def mark_signal_classified(
        self,
        signal_id: str,
        classification: str,
        project_id: str | None = None,
        extracted_tasks: list | None = None,
    ) -> None:
        params: list[Any] = [classification]
        extra = ""
        if project_id is not None:
            extra += ", project_id = %s"
            params.append(project_id)
        if extracted_tasks is not None:
            extra += ", extracted_tasks = %s"
            params.append(json.dumps(extracted_tasks))
        params.append(signal_id)
        sql = f"""
            UPDATE home_signals
               SET classified = TRUE, classification = %s{extra}
             WHERE id = %s
        """
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, params)
                conn.commit()
            log.info("mark_signal_classified signal_id=%s class=%s", signal_id, classification)
        except Exception:
            log.exception("mark_signal_classified failed signal_id=%s", signal_id)
            raise

    def get_signals_for_project(self, project_id: str, limit: int = 20) -> list[dict]:
        sql = """
            SELECT * FROM home_signals
             WHERE project_id = %s
             ORDER BY signal_date DESC NULLS LAST, created_at DESC
             LIMIT %s
        """
        try:
            with self._connect() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(sql, (project_id, limit))
                    return _rows(cur)
        except Exception:
            log.exception("get_signals_for_project failed project_id=%s", project_id)
            raise

    # ── Value Log ───────────────────────────────────────────────────────────

    def log_value(
        self,
        project_id: str,
        amount: float,
        type_: str,
        description: str | None = None,
        source: str = "manual",
    ) -> dict:
        sql = """
            INSERT INTO value_log (project_id, amount, type, description, source)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING *
        """
        try:
            with self._connect() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(sql, (project_id, amount, type_, description, source))
                    row = _one(cur)
                conn.commit()
            log.info("log_value project=%s amount=%s type=%s", project_id, amount, type_)
            return row
        except Exception:
            log.exception("log_value failed project_id=%s", project_id)
            raise

    def get_value_summary(self, project_id: str | None = None) -> dict:
        """Return total revenue, savings, cost optionally scoped to a project."""
        params: list[Any] = []
        where = ""
        if project_id:
            where = "WHERE project_id = %s"
            params.append(project_id)
        sql = f"""
            SELECT
                project_id::text,
                type,
                SUM(amount) AS total
            FROM value_log
            {where}
            GROUP BY project_id, type
        """
        try:
            with self._connect() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(sql, params)
                    rows = _rows(cur)
            # Aggregate
            by_project: dict[str, dict[str, float]] = {}
            totals: dict[str, float] = {"revenue": 0.0, "savings": 0.0, "cost": 0.0}
            for r in rows:
                pid = r["project_id"]
                t = r["type"]
                amt = float(r["total"] or 0)
                by_project.setdefault(pid, {"revenue": 0.0, "savings": 0.0, "cost": 0.0})
                by_project[pid][t] = by_project[pid].get(t, 0.0) + amt
                totals[t] = totals.get(t, 0.0) + amt
            return {"totals": totals, "by_project": by_project}
        except Exception:
            log.exception("get_value_summary failed project_id=%s", project_id)
            raise

    # ── Calendar Events ──────────────────────────────────────────────────────

    def upsert_calendar_event(self, data: dict) -> dict:
        """INSERT ... ON CONFLICT (external_id, source) DO UPDATE."""
        fields = [
            "external_id", "source", "title", "description",
            "start_time", "end_time", "all_day", "location",
            "attendees", "organizer", "project_id", "is_project_signal",
            "color", "calendar_name",
        ]
        present = {k: data[k] for k in fields if k in data}
        if "attendees" in present and isinstance(present["attendees"], (list, dict)):
            present["attendees"] = json.dumps(present["attendees"])
        cols = ", ".join(present.keys())
        placeholders = ", ".join(["%s"] * len(present))
        # Build SET for conflict update (skip external_id and source — they're the conflict keys)
        update_cols = [k for k in present if k not in ("external_id", "source")]
        set_clause = ", ".join(f"{c} = EXCLUDED.{c}" for c in update_cols)
        set_clause += ", synced_at = NOW()"
        sql = f"""
            INSERT INTO calendar_events ({cols})
            VALUES ({placeholders})
            ON CONFLICT (external_id, source) DO UPDATE SET {set_clause}
            RETURNING *
        """
        try:
            with self._connect() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(sql, list(present.values()))
                    row = _one(cur)
                conn.commit()
            return row
        except Exception:
            log.exception("upsert_calendar_event failed external_id=%s", data.get("external_id"))
            raise

    def list_calendar_events(
        self,
        start: str,
        end: str,
        source: str | None = None,
    ) -> list[dict]:
        params: list[Any] = [start, end]
        extra = ""
        if source:
            extra = " AND source = %s"
            params.append(source)
        sql = f"""
            SELECT * FROM calendar_events
             WHERE start_time >= %s AND start_time < %s{extra}
             ORDER BY start_time ASC
        """
        try:
            with self._connect() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(sql, params)
                    return _rows(cur)
        except Exception:
            log.exception("list_calendar_events failed start=%s end=%s", start, end)
            raise

    def get_todays_events(self) -> list[dict]:
        sql = """
            SELECT * FROM calendar_events
             WHERE start_time >= CURRENT_DATE
               AND start_time <  CURRENT_DATE + INTERVAL '1 day'
             ORDER BY start_time ASC
        """
        try:
            with self._connect() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(sql)
                    return _rows(cur)
        except Exception:
            log.exception("get_todays_events failed")
            raise

    def get_upcoming_events(self, days: int = 7) -> list[dict]:
        sql = """
            SELECT * FROM calendar_events
             WHERE start_time >= NOW()
               AND start_time <  NOW() + INTERVAL '%s days'
             ORDER BY start_time ASC
        """
        try:
            with self._connect() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    # Use mogrify-safe approach: cast days to int, pass as literal
                    cur.execute(
                        """
                        SELECT * FROM calendar_events
                         WHERE start_time >= NOW()
                           AND start_time <  NOW() + (%s * INTERVAL '1 day')
                         ORDER BY start_time ASC
                        """,
                        (days,),
                    )
                    return _rows(cur)
        except Exception:
            log.exception("get_upcoming_events failed days=%s", days)
            raise

    def delete_old_events(self, before_days: int = 30) -> None:
        """Delete calendar events whose end_time is older than before_days days."""
        sql = """
            DELETE FROM calendar_events
             WHERE end_time < NOW() - (%s * INTERVAL '1 day')
        """
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (before_days,))
                    deleted = cur.rowcount
                conn.commit()
            log.info("delete_old_events deleted=%d before_days=%d", deleted, before_days)
        except Exception:
            log.exception("delete_old_events failed")
            raise

    # ── Email Cache ──────────────────────────────────────────────────────────

    def upsert_email(self, data: dict) -> dict:
        """INSERT ... ON CONFLICT (external_id, source) DO UPDATE."""
        fields = [
            "external_id", "source", "thread_id", "subject",
            "sender_email", "sender_name", "recipients", "snippet",
            "body_text", "received_at", "is_read", "is_flagged",
            "importance", "labels", "project_id", "signal_id", "processed",
        ]
        present = {k: data[k] for k in fields if k in data}
        for jf in ("recipients", "labels"):
            if jf in present and isinstance(present[jf], (list, dict)):
                present[jf] = json.dumps(present[jf])
        cols = ", ".join(present.keys())
        placeholders = ", ".join(["%s"] * len(present))
        update_cols = [k for k in present if k not in ("external_id", "source")]
        set_clause = ", ".join(f"{c} = EXCLUDED.{c}" for c in update_cols)
        set_clause += ", synced_at = NOW()"
        sql = f"""
            INSERT INTO email_cache ({cols})
            VALUES ({placeholders})
            ON CONFLICT (external_id, source) DO UPDATE SET {set_clause}
            RETURNING *
        """
        try:
            with self._connect() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(sql, list(present.values()))
                    row = _one(cur)
                conn.commit()
            return row
        except Exception:
            log.exception("upsert_email failed external_id=%s", data.get("external_id"))
            raise

    def list_emails(
        self,
        source: str | None = None,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        params: list[Any] = []
        conditions = ["1=1"]
        if source:
            conditions.append("source = %s")
            params.append(source)
        if unread_only:
            conditions.append("is_read = FALSE")
        where = " AND ".join(conditions)
        sql = f"""
            SELECT * FROM email_cache
             WHERE {where}
             ORDER BY received_at DESC
             LIMIT %s OFFSET %s
        """
        params += [limit, offset]
        try:
            with self._connect() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(sql, params)
                    return filter_records(_rows(cur))
        except Exception:
            log.exception("list_emails failed source=%s unread_only=%s", source, unread_only)
            raise

    def get_email_stats(self) -> dict:
        """Return {gmail: {total, unread, flagged}, outlook: {total, unread, flagged}}."""
        try:
            rows = self.list_emails(limit=1000)
            result: dict[str, dict] = {}
            for r in rows:
                source = str(r.get("source") or "").strip() or "unknown"
                bucket = result.setdefault(source, {"total": 0, "unread": 0, "flagged": 0})
                bucket["total"] += 1
                if not bool(r.get("is_read")):
                    bucket["unread"] += 1
                if bool(r.get("is_flagged")):
                    bucket["flagged"] += 1
            # Ensure both sources are present even with no data
            for src in ("gmail", "outlook"):
                result.setdefault(src, {"total": 0, "unread": 0, "flagged": 0})
            return result
        except Exception:
            log.exception("get_email_stats failed")
            raise

    def mark_email_read(self, email_id: str) -> None:
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE email_cache SET is_read = TRUE, synced_at = NOW() WHERE id = %s",
                        (email_id,),
                    )
                conn.commit()
            log.debug("mark_email_read id=%s", email_id)
        except Exception:
            log.exception("mark_email_read failed email_id=%s", email_id)
            raise

    def mark_email_processed(self, email_id: str, signal_id: str | None = None) -> None:
        params: list[Any] = []
        extra = ""
        if signal_id is not None:
            extra = ", signal_id = %s"
            params.append(signal_id)
        params.append(email_id)
        sql = f"UPDATE email_cache SET processed = TRUE{extra}, synced_at = NOW() WHERE id = %s"
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, params)
                conn.commit()
            log.debug("mark_email_processed id=%s signal_id=%s", email_id, signal_id)
        except Exception:
            log.exception("mark_email_processed failed email_id=%s", email_id)
            raise

    def get_unprocessed_emails(self, limit: int = 20) -> list[dict]:
        sql = """
            SELECT * FROM email_cache
             WHERE processed = FALSE
             ORDER BY received_at DESC
             LIMIT %s
        """
        try:
            with self._connect() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(sql, (limit,))
                    return _rows(cur)
        except Exception:
            log.exception("get_unprocessed_emails failed")
            raise

    # ── Sync State ───────────────────────────────────────────────────────────

    def get_sync_state(self, source: str) -> dict | None:
        try:
            with self._connect() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute("SELECT * FROM sync_state WHERE source = %s", (source,))
                    return _one(cur)
        except Exception:
            log.exception("get_sync_state failed source=%s", source)
            raise

    def update_sync_state(
        self,
        source: str,
        last_sync_at: str | datetime | None = None,
        last_token: str | None = None,
        status: str = "ok",
        error_detail: str | None = None,
    ) -> None:
        now = datetime.now(timezone.utc)
        if last_sync_at is None:
            last_sync_at = now
        sql = """
            INSERT INTO sync_state (source, last_sync_at, last_token, status, error_detail, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (source) DO UPDATE SET
                last_sync_at  = EXCLUDED.last_sync_at,
                last_token    = EXCLUDED.last_token,
                status        = EXCLUDED.status,
                error_detail  = EXCLUDED.error_detail,
                updated_at    = EXCLUDED.updated_at
        """
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (source, last_sync_at, last_token, status, error_detail, now))
                conn.commit()
            log.info("update_sync_state source=%s status=%s", source, status)
        except Exception:
            log.exception("update_sync_state failed source=%s", source)
            raise

    def get_all_sync_states(self) -> list[dict]:
        try:
            with self._connect() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute("SELECT * FROM sync_state ORDER BY source")
                    return _rows(cur)
        except Exception:
            log.exception("get_all_sync_states failed")
            raise

    # ── Dashboard ────────────────────────────────────────────────────────────

    def get_dashboard_data(self) -> dict:
        """
        Return a consolidated snapshot for the JARVIS home dashboard.

        Shape:
        {
          projects: {total, active, stalled, complete, by_track: {revenue, savings, operations}},
          tasks: {total_open, overdue, due_today, due_this_week},
          email: {gmail_unread, outlook_unread, total_unread},
          calendar: {today_count, upcoming_3_days: [events]},
          value: {total_projected_revenue, total_projected_savings, total_realized},
          signals: {unclassified_count},
        }
        """
        try:
            with self._connect() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:

                    # --- Projects ---
                    cur.execute("""
                        SELECT status, track, COUNT(*) AS cnt
                        FROM home_projects
                        GROUP BY status, track
                    """)
                    project_rows = _rows(cur)

                    # --- Project value ---
                    cur.execute("""
                        SELECT
                            track,
                            SUM(projected_value) AS projected,
                            SUM(realized_value)  AS realized
                        FROM home_projects
                        GROUP BY track
                    """)
                    value_rows = _rows(cur)

                    # --- Tasks ---
                    cur.execute("""
                        SELECT
                            COUNT(*) FILTER (WHERE status NOT IN ('complete','dismissed'))
                                AS total_open,
                            COUNT(*) FILTER (
                                WHERE status NOT IN ('complete','dismissed')
                                  AND due_date < CURRENT_DATE
                            ) AS overdue,
                            COUNT(*) FILTER (
                                WHERE status NOT IN ('complete','dismissed')
                                  AND due_date = CURRENT_DATE
                            ) AS due_today,
                            COUNT(*) FILTER (
                                WHERE status NOT IN ('complete','dismissed')
                                  AND due_date BETWEEN CURRENT_DATE
                                                    AND CURRENT_DATE + INTERVAL '7 days'
                            ) AS due_this_week
                        FROM project_tasks
                    """)
                    task_row = _one(cur) or {}

                    # --- Email ---
                    cur.execute("""
                        SELECT
                            source,
                            SUM(CASE WHEN is_read = FALSE THEN 1 ELSE 0 END) AS unread
                        FROM email_cache
                        GROUP BY source
                    """)
                    email_rows = _rows(cur)

                    # --- Calendar: today ---
                    cur.execute("""
                        SELECT COUNT(*) AS cnt FROM calendar_events
                         WHERE start_time >= CURRENT_DATE
                           AND start_time <  CURRENT_DATE + INTERVAL '1 day'
                    """)
                    today_cal = _one(cur) or {"cnt": 0}

                    # --- Calendar: upcoming 14 days ---
                    cur.execute("""
                        SELECT * FROM calendar_events
                         WHERE start_time >= NOW()
                           AND start_time <  NOW() + INTERVAL '14 days'
                         ORDER BY start_time ASC
                         LIMIT 20
                    """)
                    upcoming_events = _rows(cur)

                    # --- Signals ---
                    cur.execute("""
                        SELECT COUNT(*) AS cnt FROM home_signals WHERE classified = FALSE
                    """)
                    sig_row = _one(cur) or {"cnt": 0}

            # Assemble projects
            proj_by_status: dict[str, int] = {}
            proj_by_track: dict[str, int] = {}
            for r in project_rows:
                proj_by_status[r["status"]] = proj_by_status.get(r["status"], 0) + int(r["cnt"])
                proj_by_track[r["track"]] = proj_by_track.get(r["track"], 0) + int(r["cnt"])
            total_projects = sum(proj_by_status.values())

            # Assemble value
            total_projected_revenue = 0.0
            total_projected_savings = 0.0
            total_realized = 0.0
            for r in value_rows:
                track = r.get("track", "")
                if track == "revenue":
                    total_projected_revenue += float(r["projected"] or 0)
                elif track == "savings":
                    total_projected_savings += float(r["projected"] or 0)
                total_realized += float(r["realized"] or 0)

            # Assemble email
            email_by_source: dict[str, int] = {}
            for r in email_rows:
                email_by_source[r["source"]] = int(r["unread"] or 0)
            gmail_unread = email_by_source.get("gmail", 0)
            outlook_unread = email_by_source.get("outlook", 0)

            return {
                "projects": {
                    "total": total_projects,
                    "active": proj_by_status.get("active", 0),
                    "stalled": proj_by_status.get("stalled", 0),
                    "complete": proj_by_status.get("complete", 0),
                    "by_track": {
                        "revenue": proj_by_track.get("revenue", 0),
                        "savings": proj_by_track.get("savings", 0),
                        "operations": proj_by_track.get("operations", 0),
                    },
                },
                "tasks": {
                    "total_open": int(task_row.get("total_open") or 0),
                    "overdue": int(task_row.get("overdue") or 0),
                    "due_today": int(task_row.get("due_today") or 0),
                    "due_this_week": int(task_row.get("due_this_week") or 0),
                },
                "email": {
                    "gmail_unread": gmail_unread,
                    "outlook_unread": outlook_unread,
                    "total_unread": gmail_unread + outlook_unread,
                },
                "calendar": {
                    "today_count": int(today_cal.get("cnt") or 0),
                    "upcoming_3_days": upcoming_events,
                },
                "value": {
                    "total_projected_revenue": round(total_projected_revenue, 2),
                    "total_projected_savings": round(total_projected_savings, 2),
                    "total_realized": round(total_realized, 2),
                },
                "signals": {
                    "unclassified_count": int(sig_row.get("cnt") or 0),
                },
            }
        except Exception:
            log.exception("get_dashboard_data failed")
            raise


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_db: HomeDB | None = None


def get_home_db() -> HomeDB | None:
    """Return the module-level HomeDB singleton, or None if not initialised."""
    return _db


def init_home_db(db_url: str) -> HomeDB:
    """Initialise (or re-initialise) the module-level HomeDB singleton."""
    global _db
    _db = HomeDB(db_url)
    log.info("init_home_db singleton ready")
    return _db


# ---------------------------------------------------------------------------
# Convenience: default URL
# ---------------------------------------------------------------------------

DEFAULT_DB_URL = "postgresql://chris@127.0.0.1:5432/jarvis_home"
