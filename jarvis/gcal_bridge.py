"""JARVIS Google Calendar Bridge — reads Google Calendar for home intelligence."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .persistence import append_jsonl, atomic_write_json

logger = logging.getLogger("jarvis.gcal_bridge")

# ---------------------------------------------------------------------------
# Google API library imports (with graceful degradation)
# ---------------------------------------------------------------------------

try:
    from google.auth.transport.requests import Request as GoogleRequest
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build as _build_service

    _GOOGLE_LIBS_AVAILABLE = True
except ImportError:
    GoogleRequest = None  # type: ignore[assignment]
    Credentials = None  # type: ignore[assignment]
    _build_service = None  # type: ignore[assignment]
    _GOOGLE_LIBS_AVAILABLE = False
    logger.warning("gcal_bridge: google-api-python-client not installed — Calendar will be unavailable")


# ---------------------------------------------------------------------------
# Datetime helpers
# ---------------------------------------------------------------------------

def _to_iso_utc(dt_str: str | None) -> str:
    """
    Normalize a Google Calendar datetime string to ISO 8601 UTC.

    Google returns either:
      - 'dateTime': '2025-05-18T10:00:00-05:00'  (with timezone offset)
      - 'date':     '2025-05-18'                  (all-day events, no time)

    Always returns an ISO string. All-day events return 'YYYY-MM-DD' unchanged.
    Timed events are converted to UTC.
    """
    if not dt_str:
        return ""
    # All-day format: 'YYYY-MM-DD' (10 chars, no 'T')
    if len(dt_str) == 10 and "T" not in dt_str:
        return dt_str
    try:
        # Parse with offset awareness
        # Python 3.7+ handles most ISO 8601 offsets via fromisoformat, but
        # the trailing 'Z' needs special handling in Python < 3.11
        normalized = dt_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        utc_dt = dt.astimezone(timezone.utc)
        return utc_dt.isoformat()
    except (ValueError, AttributeError):
        return dt_str


def _is_all_day(event: dict) -> bool:
    """Return True if the Google Calendar event is an all-day event."""
    start = event.get("start", {})
    # All-day events have 'date' key; timed events have 'dateTime' key
    return "date" in start and "dateTime" not in start


def _parse_attendees(raw: list[dict]) -> list[dict]:
    """
    Parse Google Calendar attendees list into normalized format.

    Returns: [{"name": str, "email": str}, ...]
    """
    result: list[dict] = []
    for attendee in raw:
        if not isinstance(attendee, dict):
            continue
        email = str(attendee.get("email", "")).strip().lower()
        display_name = str(attendee.get("displayName", "")).strip()
        if email:
            result.append({"name": display_name, "email": email})
    return result


def _parse_organizer(raw: dict | None) -> str:
    """Return organizer email string, or empty string."""
    if not raw or not isinstance(raw, dict):
        return ""
    return str(raw.get("email", "")).strip().lower()


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _iso_utc(dt: datetime) -> str:
    """Convert a datetime to ISO 8601 UTC string for API calls."""
    return dt.astimezone(timezone.utc).isoformat()


def _event_to_dict(event: dict, calendar_name: str = "", color: str = "") -> dict:
    """
    Convert a raw Google Calendar event dict into the JARVIS-normalized format.

    Returns a dict with keys:
      external_id, source, title, description, start_time, end_time,
      all_day, location, attendees, organizer, calendar_name, color
    """
    start = event.get("start", {})
    end = event.get("end", {})
    all_day = _is_all_day(event)

    start_raw = start.get("date") if all_day else start.get("dateTime")
    end_raw = end.get("date") if all_day else end.get("dateTime")

    return {
        "external_id": str(event.get("id", "")),
        "source": "google",
        "title": str(event.get("summary", "(Untitled event)")),
        "description": str(event.get("description", "") or ""),
        "start_time": _to_iso_utc(start_raw),
        "end_time": _to_iso_utc(end_raw),
        "all_day": all_day,
        "location": str(event.get("location", "") or ""),
        "attendees": _parse_attendees(event.get("attendees", []) or []),
        "organizer": _parse_organizer(event.get("organizer")),
        "calendar_name": calendar_name,
        "color": color or str(event.get("colorId", "") or ""),
    }


# ---------------------------------------------------------------------------
# GoogleCalendarBridge
# ---------------------------------------------------------------------------

class GoogleCalendarBridge:
    """
    Reads Google Calendar events for JARVIS home intelligence.

    Uses stored OAuth credentials from the JARVIS Google bridge token files.
    All methods are synchronous and return empty results on failure rather
    than raising exceptions.
    """

    def __init__(self, credentials_path: str) -> None:
        self._credentials_path = Path(credentials_path)
        self._service = None

    def _credentials_log_path(self) -> Path:
        return self._credentials_path.with_name(f"{self._credentials_path.stem}_log.jsonl")

    def _credentials_state_log_path(self) -> Path:
        return self._credentials_path.with_name(f"{self._credentials_path.stem}_state_log.jsonl")

    def _load_credentials_from_log(self) -> dict:
        log_path = self._credentials_log_path()
        if not log_path.exists():
            return {}
        latest: dict[str, Any] = {}
        try:
            for line in log_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                payload = json.loads(line)
                credentials = payload.get("credentials")
                if isinstance(credentials, dict):
                    latest = credentials
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("gcal_bridge: failed to replay credentials log %s: %s", log_path, exc)
            return {}
        return latest

    def _load_credentials_from_state_log(self) -> dict:
        log_path = self._credentials_state_log_path()
        if not log_path.exists():
            return {}
        latest: dict[str, Any] = {}
        try:
            for line in log_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                payload = json.loads(line)
                credentials = payload.get("credentials")
                if isinstance(credentials, dict):
                    latest = credentials
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("gcal_bridge: failed to replay credentials state log %s: %s", log_path, exc)
            return {}
        return latest

    def _persist_credentials_snapshot(self, payload: dict[str, Any]) -> None:
        self._credentials_path.parent.mkdir(parents=True, exist_ok=True)
        append_jsonl(
            self._credentials_log_path(),
            {
                "saved_at": datetime.now(tz=timezone.utc).isoformat(),
                "credentials": payload,
            },
            ensure_ascii=False,
        )
        append_jsonl(
            self._credentials_state_log_path(),
            {
                "saved_at": datetime.now(tz=timezone.utc).isoformat(),
                "credentials": payload,
            },
            ensure_ascii=False,
        )
        atomic_write_json(self._credentials_path, payload, ensure_ascii=False)

    # ------------------------------------------------------------------
    # Credential loading and service construction
    # ------------------------------------------------------------------

    def _load_credentials(self) -> dict:
        """
        Read OAuth token JSON from credentials_path.

        Expected format:
          {
            "token": "ya29...",
            "refresh_token": "1//...",
            "client_id": "...",
            "client_secret": "...",
            "token_uri": "https://oauth2.googleapis.com/token",
            "scopes": [...]
          }
        """
        if not self._credentials_path.exists():
            replayed = self._load_credentials_from_state_log()
            if replayed:
                return replayed
            replayed = self._load_credentials_from_log()
            if replayed:
                return replayed
            logger.warning("gcal_bridge: credentials file not found: %s", self._credentials_path)
            return {}
        try:
            raw = self._credentials_path.read_text(encoding="utf-8")
            data = json.loads(raw)
            if not isinstance(data, dict):
                replayed = self._load_credentials_from_state_log()
                if replayed:
                    return replayed
                replayed = self._load_credentials_from_log()
                if replayed:
                    return replayed
                logger.warning("gcal_bridge: credentials file is not a JSON object")
                return {}
            return data
        except (OSError, json.JSONDecodeError) as exc:
            logger.error("gcal_bridge: failed to read credentials: %s", exc)
            replayed = self._load_credentials_from_state_log()
            if replayed:
                return replayed
            return self._load_credentials_from_log()

    def _get_service(self):
        """
        Build (or return cached) Google Calendar API service using stored credentials.
        Refreshes the token if expired.
        Returns None if unavailable.
        """
        if self._service is not None:
            return self._service

        if not _GOOGLE_LIBS_AVAILABLE:
            logger.error("gcal_bridge: Google API libraries are not installed")
            return None

        cred_data = self._load_credentials()
        if not cred_data:
            return None

        try:
            scopes = cred_data.get("scopes", ["https://www.googleapis.com/auth/calendar.readonly"])
            if isinstance(scopes, str):
                scopes = [scopes]

            credentials = Credentials(
                token=cred_data.get("token"),
                refresh_token=cred_data.get("refresh_token"),
                client_id=cred_data.get("client_id"),
                client_secret=cred_data.get("client_secret"),
                token_uri=cred_data.get("token_uri", "https://oauth2.googleapis.com/token"),
                scopes=scopes,
            )

            # Refresh if expired
            if credentials.expired and credentials.refresh_token:
                logger.debug("gcal_bridge: refreshing expired token")
                credentials.refresh(GoogleRequest())
                self._persist_refreshed_token(credentials)

            service = _build_service("calendar", "v3", credentials=credentials, cache_discovery=False)
            self._service = service
            return service

        except Exception as exc:
            logger.error("gcal_bridge: failed to build Calendar service: %s", exc)
            return None

    def _persist_refreshed_token(self, credentials) -> None:
        """Write refreshed token back to credentials_path."""
        try:
            cred_data = self._load_credentials()
            cred_data["token"] = credentials.token
            if credentials.expiry:
                cred_data["expiry"] = credentials.expiry.isoformat()
            self._persist_credentials_snapshot(cred_data)
            logger.debug("gcal_bridge: persisted refreshed token to %s", self._credentials_path)
        except Exception as exc:
            logger.warning("gcal_bridge: failed to persist refreshed token: %s", exc)

    # ------------------------------------------------------------------
    # Calendar metadata helpers
    # ------------------------------------------------------------------

    def _get_calendar_metadata(self, calendar_id: str) -> dict:
        """
        Fetch name and color for a specific calendar ID.
        Returns {'name': str, 'color': str}. Empty dict on failure.
        """
        service = self._get_service()
        if service is None:
            return {}
        try:
            cal = service.calendars().get(calendarId=calendar_id).execute()
            return {
                "name": str(cal.get("summary", "") or ""),
                "color": str(cal.get("backgroundColor", "") or ""),
            }
        except Exception as exc:
            logger.debug("gcal_bridge: could not fetch calendar metadata for %s: %s", calendar_id, exc)
            return {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fetch_events(
        self,
        days_back: int = 1,
        days_forward: int = 14,
        calendar_id: str = "primary",
    ) -> list[dict]:
        """
        Fetch Google Calendar events within a time window.

        Args:
            days_back: How many days into the past to include.
            days_forward: How many days into the future to include.
            calendar_id: Calendar ID to query. Defaults to 'primary'.

        Returns:
            List of normalized event dicts:
              external_id, source, title, description, start_time, end_time,
              all_day, location, attendees, organizer, calendar_name, color
        """
        service = self._get_service()
        if service is None:
            return []

        try:
            now = _now_utc()
            time_min = _iso_utc(now - timedelta(days=days_back))
            time_max = _iso_utc(now + timedelta(days=days_forward))

            meta = self._get_calendar_metadata(calendar_id)
            calendar_name = meta.get("name", "")
            calendar_color = meta.get("color", "")

            response = (
                service.events()
                .list(
                    calendarId=calendar_id,
                    timeMin=time_min,
                    timeMax=time_max,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )

            raw_events = response.get("items", [])
            return [_event_to_dict(e, calendar_name, calendar_color) for e in raw_events]

        except Exception as exc:
            logger.error("gcal_bridge.fetch_events: %s", exc)
            return []

    def fetch_todays_events(self) -> list[dict]:
        """
        Fetch all events occurring today across ALL accessible calendars,
        sorted by start time.

        Returns:
            List of normalized event dicts for today.
        """
        service = self._get_service()
        if service is None:
            return []

        try:
            now = _now_utc()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = today_start + timedelta(days=1)
            time_min = _iso_utc(today_start)
            time_max = _iso_utc(today_end)

            cal_list_resp = service.calendarList().list().execute()
            calendars = cal_list_resp.get("items", [])

            INCLUDE_ROLES = {"owner", "writer", "reader"}
            all_events: list[dict] = []

            for cal in calendars:
                cal_id   = cal.get("id", "")
                role     = cal.get("accessRole", "")
                if role not in INCLUDE_ROLES:
                    continue
                cal_name  = str(cal.get("summary", "") or cal_id)
                cal_color = str(cal.get("backgroundColor", "") or cal.get("colorId", "") or "")
                try:
                    response = (
                        service.events()
                        .list(
                            calendarId=cal_id,
                            timeMin=time_min,
                            timeMax=time_max,
                            singleEvents=True,
                            orderBy="startTime",
                        )
                        .execute()
                    )
                    for e in response.get("items", []):
                        all_events.append(_event_to_dict(e, cal_name, cal_color))
                except Exception as cal_exc:
                    logger.warning("gcal_bridge: skipping calendar %s: %s", cal_id[:20], cal_exc)

            all_events.sort(key=lambda ev: ev.get("start_time", "") or "9999")
            return all_events

        except Exception as exc:
            logger.error("gcal_bridge.fetch_todays_events: %s", exc)
            return []

    def fetch_upcoming_events(self, days: int = 7) -> list[dict]:
        """
        Fetch upcoming events across ALL accessible calendars for the next `days` days,
        sorted by start time.

        Args:
            days: Number of days forward to fetch.

        Returns:
            List of normalized event dicts sorted by start_time.
        """
        service = self._get_service()
        if service is None:
            return []

        try:
            now = _now_utc()
            time_min = _iso_utc(now)
            time_max = _iso_utc(now + timedelta(days=days))

            # Get all calendars the user has access to
            cal_list_resp = service.calendarList().list().execute()
            calendars = cal_list_resp.get("items", [])

            # Skip calendars the user only reads (not their own) unless
            # they are the owner or writer — always include primary
            INCLUDE_ROLES = {"owner", "writer", "reader"}
            all_events: list[dict] = []

            for cal in calendars:
                cal_id = cal.get("id", "")
                role = cal.get("accessRole", "")
                if role not in INCLUDE_ROLES:
                    continue
                cal_name  = str(cal.get("summary", "") or cal_id)
                cal_color = str(cal.get("backgroundColor", "") or cal.get("colorId", "") or "")
                try:
                    response = (
                        service.events()
                        .list(
                            calendarId=cal_id,
                            timeMin=time_min,
                            timeMax=time_max,
                            singleEvents=True,
                            orderBy="startTime",
                        )
                        .execute()
                    )
                    for e in response.get("items", []):
                        all_events.append(_event_to_dict(e, cal_name, cal_color))
                except Exception as cal_exc:
                    logger.warning("gcal_bridge: skipping calendar %s: %s", cal_id[:20], cal_exc)

            # Sort merged results by start_time
            def _sort_key(ev: dict) -> str:
                t = ev.get("start_time", "")
                return t if t else "9999"

            all_events.sort(key=_sort_key)
            return all_events

        except Exception as exc:
            logger.error("gcal_bridge.fetch_upcoming_events: %s", exc)
            return []

    def list_calendars(self) -> list[dict]:
        """
        Return all calendars accessible by the authenticated account.

        Returns:
            List of dicts: [{"id": str, "name": str, "color": str}, ...]
        """
        service = self._get_service()
        if service is None:
            return []

        try:
            response = service.calendarList().list().execute()
            items = response.get("items", [])
            result: list[dict] = []
            for cal in items:
                result.append({
                    "id": str(cal.get("id", "")),
                    "name": str(cal.get("summary", "") or ""),
                    "color": str(cal.get("backgroundColor", "") or cal.get("colorId", "") or ""),
                })
            return result

        except Exception as exc:
            logger.error("gcal_bridge.list_calendars: %s", exc)
            return []

    def create_event(
        self,
        title: str,
        start: str,
        end: str,
        description: str | None = None,
        location: str | None = None,
    ) -> dict:
        """
        Create a calendar event on the primary calendar.

        Args:
            title: Event title/summary.
            start: Start datetime as ISO 8601 string (e.g. '2025-05-18T10:00:00-05:00').
                   For all-day events, use 'YYYY-MM-DD' format.
            end: End datetime as ISO 8601 string.
            description: Optional event description.
            location: Optional event location.

        Returns:
            Normalized event dict on success, or {'error': str} on failure.
        """
        service = self._get_service()
        if service is None:
            return {"error": "Google Calendar service unavailable"}

        try:
            # Determine if this is an all-day event (date-only strings)
            all_day = len(start) == 10 and "T" not in start

            if all_day:
                start_block = {"date": start}
                end_block = {"date": end}
            else:
                # Normalize to UTC for storage
                start_block = {"dateTime": _to_iso_utc(start), "timeZone": "UTC"}
                end_block = {"dateTime": _to_iso_utc(end), "timeZone": "UTC"}

            body: dict[str, Any] = {
                "summary": title,
                "start": start_block,
                "end": end_block,
            }
            if description is not None:
                body["description"] = description
            if location is not None:
                body["location"] = location

            created = (
                service.events()
                .insert(calendarId="primary", body=body)
                .execute()
            )

            logger.info("gcal_bridge: created event '%s' (id=%s)", title, created.get("id"))
            meta = self._get_calendar_metadata("primary")
            return _event_to_dict(created, meta.get("name", ""), meta.get("color", ""))

        except Exception as exc:
            logger.error("gcal_bridge.create_event('%s'): %s", title, exc)
            return {"error": str(exc)}


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_bridge: GoogleCalendarBridge | None = None


def get_gcal_bridge() -> GoogleCalendarBridge | None:
    """Return the module-level GoogleCalendarBridge singleton (None if not initialised)."""
    return _bridge


def init_gcal_bridge(credentials_path: str) -> GoogleCalendarBridge:
    """
    Create and return the module-level GoogleCalendarBridge singleton.

    Args:
        credentials_path: Absolute path to the OAuth token JSON file from the
                          JARVIS Google bridge (e.g. data/google/bridge/tokens/<id>.json).

    Returns:
        The initialised GoogleCalendarBridge instance.
    """
    global _bridge
    _bridge = GoogleCalendarBridge(credentials_path)
    logger.info("gcal_bridge: initialised with credentials at %s", credentials_path)
    return _bridge
