"""JARVIS Unified Inbox — syncs Gmail, Outlook, Google Calendar, Outlook Calendar, and Cozi."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _date_str(dt: datetime) -> str:
    """Return YYYY-MM-DD string for a datetime."""
    return dt.strftime("%Y-%m-%d")


def _gmail_date_str(dt: datetime) -> str:
    """Return YYYY/MM/DD string for Gmail query syntax."""
    return dt.strftime("%Y/%m/%d")


class UnifiedInbox:
    """Aggregates and syncs all email and calendar sources into the home DB."""

    def __init__(
        self,
        home_db,
        gmail_bridge=None,
        gcal_bridge=None,
        outlook_bridge=None,
        cozi_bridge=None,
    ) -> None:
        self._db = home_db
        self._gmail = gmail_bridge
        self._gcal = gcal_bridge
        self._outlook = outlook_bridge
        self._cozi = cozi_bridge

    # ── Sync state helpers ─────────────────────────────────────────────────────

    def _get_last_sync(self, source: str) -> datetime | None:
        """Return the last_sync_at timestamp for a source, or None."""
        try:
            conn = self._db._connect()
            if conn is None:
                return None
            import psycopg2.extras  # type: ignore

            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT last_sync_at FROM sync_state WHERE source = %s",
                    (source,),
                )
                row = cur.fetchone()
            conn.close()
            if row and row["last_sync_at"]:
                ts = row["last_sync_at"]
                if isinstance(ts, str):
                    return datetime.fromisoformat(ts)
                return ts
            return None
        except Exception as exc:
            logger.error("unified_inbox._get_last_sync(%s): %s", source, exc)
            return None

    def _set_last_sync(self, source: str, token: str | None = None) -> None:
        """Update sync_state with current timestamp (and optional token) for a source."""
        try:
            conn = self._db._connect()
            if conn is None:
                return
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO sync_state (source, last_sync_at, last_token, status, updated_at)
                    VALUES (%s, NOW(), %s, 'ok', NOW())
                    ON CONFLICT (source) DO UPDATE
                        SET last_sync_at = NOW(),
                            last_token   = EXCLUDED.last_token,
                            status       = 'ok',
                            updated_at   = NOW()
                    """,
                    (source, token),
                )
                conn.commit()
            conn.close()
        except Exception as exc:
            logger.error("unified_inbox._set_last_sync(%s): %s", source, exc)

    def _set_sync_error(self, source: str, detail: str) -> None:
        """Record a sync error in sync_state."""
        try:
            conn = self._db._connect()
            if conn is None:
                return
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO sync_state (source, status, error_detail, updated_at)
                    VALUES (%s, 'error', %s, NOW())
                    ON CONFLICT (source) DO UPDATE
                        SET status       = 'error',
                            error_detail = EXCLUDED.error_detail,
                            updated_at   = NOW()
                    """,
                    (source, detail[:500]),
                )
                conn.commit()
            conn.close()
        except Exception as exc:
            logger.error("unified_inbox._set_sync_error(%s): %s", source, exc)

    # ── Email upsert ───────────────────────────────────────────────────────────

    def _upsert_emails(self, emails: list[dict], source: str) -> dict:
        """Upsert a list of normalised email dicts into email_cache.

        Returns {synced: N, new: N}.
        """
        synced = 0
        new_count = 0
        try:
            conn = self._db._connect()
            if conn is None:
                return {"synced": 0, "new": 0}
            with conn.cursor() as cur:
                for email in emails:
                    cur.execute(
                        """
                        INSERT INTO email_cache
                            (id, external_id, source, thread_id, subject,
                             sender_email, sender_name, recipients, snippet,
                             body_text, received_at, is_read, is_flagged,
                             importance, labels, processed, synced_at)
                        VALUES
                            (gen_random_uuid(), %s, %s, %s, %s,
                             %s, %s, %s, %s,
                             %s, %s, %s, %s,
                             %s, %s, FALSE, NOW())
                        ON CONFLICT (external_id, source) DO UPDATE
                            SET subject     = EXCLUDED.subject,
                                snippet     = EXCLUDED.snippet,
                                body_text   = EXCLUDED.body_text,
                                is_read     = EXCLUDED.is_read,
                                is_flagged  = EXCLUDED.is_flagged,
                                importance  = EXCLUDED.importance,
                                labels      = EXCLUDED.labels,
                                synced_at   = NOW()
                        RETURNING (xmax = 0) AS inserted
                        """,
                        (
                            email.get("external_id", ""),
                            source,
                            email.get("thread_id"),
                            email.get("subject"),
                            email.get("sender_email"),
                            email.get("sender_name"),
                            json.dumps(email.get("recipients") or []),
                            email.get("snippet"),
                            email.get("body_text"),
                            email.get("received_at"),
                            email.get("is_read", False),
                            email.get("is_flagged", False),
                            email.get("importance", "normal"),
                            json.dumps(email.get("labels") or []),
                        ),
                    )
                    row = cur.fetchone()
                    synced += 1
                    if row and row[0]:
                        new_count += 1
                conn.commit()
            conn.close()
        except Exception as exc:
            logger.error("unified_inbox._upsert_emails(%s): %s", source, exc)
        return {"synced": synced, "new": new_count}

    # ── Calendar event upsert ──────────────────────────────────────────────────

    def _upsert_calendar_events(self, events: list[dict], source: str) -> dict:
        """Upsert a list of normalised calendar event dicts into calendar_events.

        Returns {synced: N, new: N}.
        """
        synced = 0
        new_count = 0
        try:
            conn = self._db._connect()
            if conn is None:
                return {"synced": 0, "new": 0}
            with conn.cursor() as cur:
                for event in events:
                    cur.execute(
                        """
                        INSERT INTO calendar_events
                            (id, external_id, source, title, description,
                             start_time, end_time, all_day, location,
                             attendees, organizer, color, calendar_name, synced_at)
                        VALUES
                            (gen_random_uuid(), %s, %s, %s, %s,
                             %s, %s, %s, %s,
                             %s, %s, %s, %s, NOW())
                        ON CONFLICT (external_id, source) DO UPDATE
                            SET title         = EXCLUDED.title,
                                description   = EXCLUDED.description,
                                start_time    = EXCLUDED.start_time,
                                end_time      = EXCLUDED.end_time,
                                all_day       = EXCLUDED.all_day,
                                location      = EXCLUDED.location,
                                attendees     = EXCLUDED.attendees,
                                organizer     = EXCLUDED.organizer,
                                color         = EXCLUDED.color,
                                calendar_name = EXCLUDED.calendar_name,
                                synced_at     = NOW()
                        RETURNING (xmax = 0) AS inserted
                        """,
                        (
                            event.get("external_id", ""),
                            source,
                            event.get("title", "(untitled)"),
                            event.get("description"),
                            event.get("start_time"),
                            event.get("end_time"),
                            bool(event.get("all_day", False)),
                            event.get("location"),
                            json.dumps(event.get("attendees") or []),
                            event.get("organizer"),
                            event.get("color"),
                            event.get("calendar_name"),
                        ),
                    )
                    row = cur.fetchone()
                    synced += 1
                    if row and row[0]:
                        new_count += 1
                conn.commit()
            conn.close()
        except Exception as exc:
            logger.error("unified_inbox._upsert_calendar_events(%s): %s", source, exc)
        return {"synced": synced, "new": new_count}

    # ── Sync methods ───────────────────────────────────────────────────────────

    def sync_gmail(self) -> dict:
        """Fetch new Gmail messages, upsert to email_cache.

        Returns {synced: N, new: N, error: str | None}.
        """
        default = {"synced": 0, "new": 0, "error": None}
        if self._gmail is None:
            logger.info("unified_inbox.sync_gmail: no bridge configured")
            return {**default, "error": "no_bridge"}

        try:
            last_sync = self._get_last_sync("gmail")
            since_date = _gmail_date_str(last_sync) if last_sync else None

            emails = self._gmail.fetch_inbox(max_results=100, since_date=since_date)
            result = self._upsert_emails(emails, source="gmail")
            self._set_last_sync("gmail")
            logger.info(
                "unified_inbox.sync_gmail: synced=%d new=%d",
                result["synced"],
                result["new"],
            )
            return {**result, "error": None}
        except Exception as exc:
            msg = str(exc)
            logger.error("unified_inbox.sync_gmail: %s", msg)
            self._set_sync_error("gmail", msg)
            return {**default, "error": msg}

    def sync_outlook_email(self) -> dict:
        """Fetch new Outlook messages, upsert to email_cache.

        Returns {synced: N, new: N, error: str | None}.
        """
        default = {"synced": 0, "new": 0, "error": None}
        if self._outlook is None:
            logger.info("unified_inbox.sync_outlook_email: no bridge configured")
            return {**default, "error": "no_bridge"}

        try:
            last_sync = self._get_last_sync("outlook")
            since_date = last_sync.isoformat() if last_sync else None

            if hasattr(self._outlook, "fetch_inbox"):
                emails = self._outlook.fetch_inbox(max_results=100, since_date=since_date)
            elif hasattr(self._outlook, "list_messages"):
                emails = self._outlook.list_messages(limit=100, since_date=since_date)
            else:
                logger.warning("unified_inbox.sync_outlook_email: bridge has no fetch method")
                return {**default, "error": "unsupported_bridge"}

            normalised = []
            for m in emails:
                normalised.append(
                    {
                        "external_id": m.get("external_id") or m.get("id", ""),
                        "thread_id": m.get("thread_id") or m.get("conversationId"),
                        "subject": m.get("subject"),
                        "sender_email": m.get("sender_email") or m.get("from_email", ""),
                        "sender_name": m.get("sender_name") or m.get("from_name", ""),
                        "recipients": m.get("recipients") or [],
                        "snippet": m.get("snippet") or m.get("bodyPreview", ""),
                        "body_text": m.get("body_text") or m.get("body", ""),
                        "received_at": m.get("received_at") or m.get("receivedDateTime"),
                        "is_read": bool(m.get("is_read", m.get("isRead", False))),
                        "is_flagged": bool(m.get("is_flagged", m.get("isFlagged", False))),
                        "importance": m.get("importance", "normal"),
                        "labels": m.get("labels") or m.get("categories") or [],
                    }
                )

            result = self._upsert_emails(normalised, source="outlook")
            self._set_last_sync("outlook")
            logger.info(
                "unified_inbox.sync_outlook_email: synced=%d new=%d",
                result["synced"],
                result["new"],
            )
            return {**result, "error": None}
        except Exception as exc:
            msg = str(exc)
            logger.error("unified_inbox.sync_outlook_email: %s", msg)
            self._set_sync_error("outlook", msg)
            return {**default, "error": msg}

    def sync_google_calendar(self) -> dict:
        """Fetch Google Calendar events for next 14 days + past 1 day, upsert to calendar_events.

        Returns {synced: N, new: N, error: str | None}.
        """
        default = {"synced": 0, "new": 0, "error": None}
        if self._gcal is None:
            logger.info("unified_inbox.sync_google_calendar: no bridge configured")
            return {**default, "error": "no_bridge"}

        try:
            now = datetime.now(timezone.utc)
            start = now - timedelta(days=1)
            end = now + timedelta(days=14)

            if hasattr(self._gcal, "get_upcoming_events"):
                raw = self._gcal.get_upcoming_events(days=15)
                event_list = raw if isinstance(raw, list) else raw.get("events", [])
            elif hasattr(self._gcal, "list_events"):
                event_list = self._gcal.list_events(
                    start_date=_date_str(start),
                    end_date=_date_str(end),
                )
            else:
                logger.warning("unified_inbox.sync_google_calendar: bridge has no list method")
                return {**default, "error": "unsupported_bridge"}

            normalised = []
            for e in event_list:
                normalised.append(
                    {
                        "external_id": e.get("external_id") or e.get("id", ""),
                        "title": e.get("title") or e.get("summary", "(untitled)"),
                        "description": e.get("description", ""),
                        "start_time": e.get("start_time") or e.get("start"),
                        "end_time": e.get("end_time") or e.get("end"),
                        "all_day": bool(e.get("all_day", False)),
                        "location": e.get("location"),
                        "attendees": e.get("attendees") or [],
                        "organizer": e.get("organizer"),
                        "color": e.get("color") or e.get("colorId"),
                        "calendar_name": e.get("calendar_name") or "primary",
                    }
                )

            result = self._upsert_calendar_events(normalised, source="google")
            self._set_last_sync("google_calendar")
            logger.info(
                "unified_inbox.sync_google_calendar: synced=%d new=%d",
                result["synced"],
                result["new"],
            )
            return {**result, "error": None}
        except Exception as exc:
            msg = str(exc)
            logger.error("unified_inbox.sync_google_calendar: %s", msg)
            self._set_sync_error("google_calendar", msg)
            return {**default, "error": msg}

    def sync_outlook_calendar(self) -> dict:
        """Fetch Outlook calendar events, upsert to calendar_events.

        Returns {synced: N, new: N, error: str | None}.
        """
        default = {"synced": 0, "new": 0, "error": None}
        if self._outlook is None:
            logger.info("unified_inbox.sync_outlook_calendar: no bridge configured")
            return {**default, "error": "no_bridge"}

        try:
            now = datetime.now(timezone.utc)
            start = now - timedelta(days=1)
            end = now + timedelta(days=14)

            if hasattr(self._outlook, "fetch_calendar_events"):
                event_list = self._outlook.fetch_calendar_events(days_back=1, days_forward=14)
            elif hasattr(self._outlook, "get_calendar_events"):
                event_list = self._outlook.get_calendar_events(
                    start_date=_date_str(start),
                    end_date=_date_str(end),
                )
            elif hasattr(self._outlook, "list_events"):
                event_list = self._outlook.list_events(
                    start_date=_date_str(start),
                    end_date=_date_str(end),
                )
            else:
                logger.warning("unified_inbox.sync_outlook_calendar: bridge has no list method")
                return {**default, "error": "unsupported_bridge"}

            normalised = []
            for e in event_list:
                loc = e.get("location")
                if isinstance(loc, dict):
                    loc = loc.get("displayName")
                normalised.append(
                    {
                        "external_id": e.get("external_id") or e.get("id", ""),
                        "title": e.get("title") or e.get("subject", "(untitled)"),
                        "description": e.get("description") or e.get("bodyPreview", ""),
                        "start_time": e.get("start_time") or (
                            e.get("start", {}).get("dateTime") if isinstance(e.get("start"), dict) else e.get("start")
                        ),
                        "end_time": e.get("end_time") or (
                            e.get("end", {}).get("dateTime") if isinstance(e.get("end"), dict) else e.get("end")
                        ),
                        "all_day": bool(e.get("all_day", e.get("isAllDay", False))),
                        "location": loc,
                        "attendees": e.get("attendees") or [],
                        "organizer": e.get("organizer"),
                        "color": e.get("color"),
                        "calendar_name": e.get("calendar_name", "calendar"),
                    }
                )

            result = self._upsert_calendar_events(normalised, source="outlook")
            self._set_last_sync("outlook_calendar")
            logger.info(
                "unified_inbox.sync_outlook_calendar: synced=%d new=%d",
                result["synced"],
                result["new"],
            )
            return {**result, "error": None}
        except Exception as exc:
            msg = str(exc)
            logger.error("unified_inbox.sync_outlook_calendar: %s", msg)
            self._set_sync_error("outlook_calendar", msg)
            return {**default, "error": msg}

    def sync_cozi(self) -> dict:
        """Fetch Cozi family calendar events, upsert to calendar_events.

        Returns {synced: N, new: N, error: str | None}.
        """
        default = {"synced": 0, "new": 0, "error": None}
        if self._cozi is None:
            logger.info("unified_inbox.sync_cozi: no bridge configured")
            return {**default, "error": "no_bridge"}

        try:
            now = datetime.now(timezone.utc)
            start = now - timedelta(days=1)
            end = now + timedelta(days=14)

            if hasattr(self._cozi, "fetch_events"):
                event_list = self._cozi.fetch_events(days_back=1, days_forward=14)
            elif hasattr(self._cozi, "get_events"):
                event_list = self._cozi.get_events(
                    start_date=_date_str(start),
                    end_date=_date_str(end),
                )
            elif hasattr(self._cozi, "list_events"):
                event_list = self._cozi.list_events(
                    start_date=_date_str(start),
                    end_date=_date_str(end),
                )
            else:
                logger.warning("unified_inbox.sync_cozi: bridge has no list method")
                return {**default, "error": "unsupported_bridge"}

            normalised = []
            for e in event_list:
                normalised.append(
                    {
                        "external_id": e.get("external_id") or e.get("id", ""),
                        "title": e.get("title") or e.get("name", "(untitled)"),
                        "description": e.get("description", ""),
                        "start_time": e.get("start_time") or e.get("start"),
                        "end_time": e.get("end_time") or e.get("end"),
                        "all_day": bool(e.get("all_day", False)),
                        "location": e.get("location"),
                        "attendees": e.get("attendees") or [],
                        "organizer": e.get("organizer"),
                        "color": e.get("color"),
                        "calendar_name": e.get("calendar_name") or "cozi",
                    }
                )

            result = self._upsert_calendar_events(normalised, source="cozi")
            self._set_last_sync("cozi")
            logger.info(
                "unified_inbox.sync_cozi: synced=%d new=%d",
                result["synced"],
                result["new"],
            )
            return {**result, "error": None}
        except Exception as exc:
            msg = str(exc)
            logger.error("unified_inbox.sync_cozi: %s", msg)
            self._set_sync_error("cozi", msg)
            return {**default, "error": msg}

    def sync_all(self) -> dict:
        """Run all syncs.

        Returns {gmail, outlook_email, google_calendar, outlook_calendar, cozi} results.
        """
        logger.info("unified_inbox.sync_all: starting full sync")
        results = {
            "gmail": self.sync_gmail(),
            "outlook_email": self.sync_outlook_email(),
            "google_calendar": self.sync_google_calendar(),
            "outlook_calendar": self.sync_outlook_calendar(),
            "cozi": self.sync_cozi(),
        }
        logger.info("unified_inbox.sync_all: complete")
        return results

    # ── Read methods ───────────────────────────────────────────────────────────

    def get_unified_calendar(self, start_date: str, end_date: str) -> list[dict]:
        """Return merged, sorted calendar events from all sources for a date range.

        Args:
            start_date: ISO date string 'YYYY-MM-DD'.
            end_date:   ISO date string 'YYYY-MM-DD' (inclusive).
        """
        try:
            conn = self._db._connect()
            if conn is None:
                return []
            import psycopg2.extras  # type: ignore

            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, external_id, source, title, description,
                           start_time, end_time, all_day, location,
                           attendees, organizer, project_id, is_project_signal,
                           color, calendar_name
                    FROM calendar_events
                    WHERE start_time >= %s::date
                      AND start_time <  %s::date + INTERVAL '1 day'
                    ORDER BY start_time ASC
                    """,
                    (start_date, end_date),
                )
                rows = [dict(r) for r in cur.fetchall()]
            conn.close()
            return rows
        except Exception as exc:
            logger.error("unified_inbox.get_unified_calendar: %s", exc)
            return []

    def get_todays_agenda(self) -> dict:
        """Return {date, events: [...sorted by time...], email_summary: {gmail_unread, outlook_unread}}."""
        today = _date_str(datetime.now(timezone.utc))
        events = self.get_unified_calendar(today, today)
        email_stats = self.get_email_stats()
        return {
            "date": today,
            "events": events,
            "email_summary": {
                "gmail_unread": email_stats.get("gmail", {}).get("unread", 0),
                "outlook_unread": email_stats.get("outlook", {}).get("unread", 0),
            },
        }

    def get_upcoming_events(self, days: int = 7) -> list[dict]:
        """Return next N days of events sorted by time."""
        now = datetime.now(timezone.utc)
        start = _date_str(now)
        end = _date_str(now + timedelta(days=days))
        return self.get_unified_calendar(start, end)

    def get_unified_email(self, limit: int = 50, unread_only: bool = False) -> list[dict]:
        """Return merged email from Gmail + Outlook sorted by received_at desc."""
        try:
            conn = self._db._connect()
            if conn is None:
                return []
            import psycopg2.extras  # type: ignore

            unread_clause = "AND is_read = FALSE" if unread_only else ""
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    f"""
                    SELECT id, external_id, source, thread_id, subject,
                           sender_email, sender_name, snippet, received_at,
                           is_read, is_flagged, importance, labels,
                           project_id, signal_id, processed
                    FROM email_cache
                    WHERE source IN ('gmail', 'outlook')
                    {unread_clause}
                    ORDER BY received_at DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
                rows = [dict(r) for r in cur.fetchall()]
            conn.close()
            return rows
        except Exception as exc:
            logger.error("unified_inbox.get_unified_email: %s", exc)
            return []

    def get_email_stats(self) -> dict:
        """Return {gmail: {unread, total}, outlook: {unread, total}, total_unread: N}."""
        default: dict = {
            "gmail": {"unread": 0, "total": 0},
            "outlook": {"unread": 0, "total": 0},
            "total_unread": 0,
        }
        try:
            conn = self._db._connect()
            if conn is None:
                return default
            import psycopg2.extras  # type: ignore

            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        source,
                        COUNT(*) AS total,
                        COUNT(*) FILTER (WHERE is_read = FALSE) AS unread
                    FROM email_cache
                    WHERE source IN ('gmail', 'outlook')
                    GROUP BY source
                    """
                )
                rows = {r["source"]: dict(r) for r in cur.fetchall()}
            conn.close()

            gmail_row = rows.get("gmail", {})
            outlook_row = rows.get("outlook", {})
            gmail_unread = int(gmail_row.get("unread", 0))
            outlook_unread = int(outlook_row.get("unread", 0))
            return {
                "gmail": {
                    "unread": gmail_unread,
                    "total": int(gmail_row.get("total", 0)),
                },
                "outlook": {
                    "unread": outlook_unread,
                    "total": int(outlook_row.get("total", 0)),
                },
                "total_unread": gmail_unread + outlook_unread,
            }
        except Exception as exc:
            logger.error("unified_inbox.get_email_stats: %s", exc)
            return default


# ── Module-level singleton ─────────────────────────────────────────────────────

_inbox: UnifiedInbox | None = None


def get_unified_inbox() -> UnifiedInbox | None:
    """Return the module-level UnifiedInbox singleton, or None if not initialized."""
    return _inbox


def init_unified_inbox(
    home_db,
    gmail_bridge=None,
    gcal_bridge=None,
    outlook_bridge=None,
    cozi_bridge=None,
) -> UnifiedInbox:
    """Initialize and return the module-level UnifiedInbox singleton."""
    global _inbox
    _inbox = UnifiedInbox(
        home_db,
        gmail_bridge=gmail_bridge,
        gcal_bridge=gcal_bridge,
        outlook_bridge=outlook_bridge,
        cozi_bridge=cozi_bridge,
    )
    logger.info("unified_inbox: initialized")
    return _inbox
