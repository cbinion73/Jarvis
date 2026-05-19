"""JARVIS Cozi Bridge — reads Cozi family calendar via its ICS feed.

Cozi does not expose a public REST API.  Instead it publishes each calendar
as a standard iCalendar (.ics) feed.  Obtain the feed URL from the Cozi web
app (Settings → Calendar → Share / Sync) and store it in the JARVIS family
calendar settings file or the ``COZI_ICS_URL`` environment variable.

Settings file location (first match wins):
  1. ``JARVIS_FAMILY_CALENDAR_SETTINGS_PATH`` env var
  2. ``<cwd>/data/settings/family_calendar.json``

The JSON file must contain at minimum::

    {"ics_url": "https://outlook.live.com/owa/calendar/.../.../cid.ics"}

The ``source`` key (default ``"cozi"``) and ``label`` key are optional.

If neither the settings file nor ``COZI_ICS_URL`` is available, all fetch
methods return empty lists and ``is_configured()`` returns ``False``.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib import error, request

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# ICS feed URL resolution
# ---------------------------------------------------------------------------

_SETTINGS_CANDIDATES: list[Path] = [
    p
    for p in [
        Path(os.environ.get("JARVIS_FAMILY_CALENDAR_SETTINGS_PATH", "")) if os.environ.get("JARVIS_FAMILY_CALENDAR_SETTINGS_PATH") else None,
        Path.cwd() / "data" / "settings" / "family_calendar.json",
        Path(__file__).parent.parent / "data" / "settings" / "family_calendar.json",
    ]
    if p is not None
]


def _load_ics_url_from_settings() -> tuple[str, str, str]:
    """Return ``(ics_url, source, label)`` from the first valid settings file."""
    for candidate in _SETTINGS_CANDIDATES:
        if not candidate.exists():
            continue
        try:
            payload = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        ics_url = str(payload.get("ics_url", "")).strip()
        if ics_url:
            source = str(payload.get("source", "cozi")).strip() or "cozi"
            label = str(payload.get("label", "Family Shared Calendar")).strip() or "Family Shared Calendar"
            return ics_url, source, label
    return "", "cozi", "Family Shared Calendar"


# ---------------------------------------------------------------------------
# ICS parsing helpers
# (Ported from the Catalyst cozi-family-calendar-bridge.ts)
# ---------------------------------------------------------------------------


def _unfold_ics_lines(text: str) -> list[str]:
    """Unfold RFC 5545 line continuations."""
    lines: list[str] = []
    for raw in text.splitlines():
        if raw.startswith((" ", "\t")) and lines:
            lines[-1] += raw[1:]
        else:
            lines.append(raw.rstrip("\r"))
    return lines


def _parse_ics_datetime(raw: str, *, all_day: bool = False) -> str:
    """Convert a DTSTART/DTEND value to an ISO 8601 string.

    Returns an empty string when the value cannot be parsed.
    """
    value = raw.strip()
    if not value:
        return ""

    # All-day events: ``YYYYMMDD``
    if all_day or len(value) == 8:
        try:
            return date.fromisoformat(f"{value[0:4]}-{value[4:6]}-{value[6:8]}").isoformat()
        except ValueError:
            return ""

    # UTC floating: ``YYYYMMDDTHHMMSSz``
    if value.upper().endswith("Z"):
        try:
            return (
                datetime.strptime(value.upper(), "%Y%m%dT%H%M%SZ")
                .replace(tzinfo=timezone.utc)
                .isoformat()
            )
        except ValueError:
            return ""

    # Local: ``YYYYMMDDTHHMMSS``
    try:
        return datetime.strptime(value, "%Y%m%dT%H%M%S").isoformat()
    except ValueError:
        return ""


def _event_in_window(
    start_iso: str,
    end_iso: str,
    *,
    from_dt: datetime,
    to_dt: datetime,
) -> bool:
    """Return True when the event overlaps [from_dt, to_dt]."""
    today = from_dt.date()

    if "T" not in start_iso:
        # All-day event
        try:
            start_date = date.fromisoformat(start_iso)
        except ValueError:
            return False
        if start_date < today:
            if not end_iso:
                return False
            try:
                end_date = date.fromisoformat(end_iso)
            except ValueError:
                return False
            return end_date >= today
        return start_date <= to_dt.date()

    try:
        start_dt = datetime.fromisoformat(start_iso)
    except ValueError:
        return False

    if start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=timezone.utc)

    if start_dt > to_dt:
        return False

    if end_iso and "T" in end_iso:
        try:
            end_dt = datetime.fromisoformat(end_iso)
        except ValueError:
            end_dt = start_dt
        if end_dt.tzinfo is None:
            end_dt = end_dt.replace(tzinfo=timezone.utc)
        return end_dt >= from_dt

    return start_dt >= from_dt


def _parse_ics_events(ics_text: str) -> list[dict[str, Any]]:
    """Parse an ICS document into a list of raw event dicts."""
    lines = _unfold_ics_lines(ics_text)
    events: list[dict[str, Any]] = []
    current: dict[str, str] | None = None
    current_all_day = False

    for line in lines:
        if line == "BEGIN:VEVENT":
            current = {}
            current_all_day = False
            continue

        if line == "END:VEVENT":
            if current:
                start_raw = current.get("DTSTART", "")
                end_raw = current.get("DTEND", "")
                start_iso = _parse_ics_datetime(start_raw, all_day=current_all_day)
                end_iso = _parse_ics_datetime(end_raw, all_day=current_all_day)
                events.append(
                    {
                        "uid": current.get("UID", "").strip(),
                        "summary": current.get("SUMMARY", "").strip() or "(Untitled event)",
                        "description": current.get("DESCRIPTION", "").strip(),
                        "location": current.get("LOCATION", "").strip(),
                        "start_iso": start_iso,
                        "end_iso": end_iso,
                        "all_day": current_all_day,
                    }
                )
            current = None
            continue

        if current is None or ":" not in line:
            continue

        key_part, _, value = line.partition(":")
        key_bits = key_part.split(";")
        key = key_bits[0].upper()

        if key == "DTSTART" and any(b.upper() == "VALUE=DATE" for b in key_bits[1:]):
            current_all_day = True

        current[key] = value

    return events


def _normalise_event(
    raw: dict[str, Any],
    *,
    source: str,
    calendar_name: str,
) -> dict[str, Any]:
    """Convert a raw parsed ICS event to the canonical JARVIS calendar dict."""
    return {
        "external_id": raw["uid"] or f"cozi-{hash(raw['summary'] + raw['start_iso']):#010x}",
        "source": source,
        "title": raw["summary"],
        "description": raw["description"],
        "start_time": raw["start_iso"],
        "end_time": raw["end_iso"],
        "all_day": raw["all_day"],
        "location": raw["location"],
        "attendees": [],
        "organizer": source,
        "color": None,
        "calendar_name": calendar_name,
    }


# ---------------------------------------------------------------------------
# Bridge class
# ---------------------------------------------------------------------------


class CoziBridge:
    """Reads Cozi family calendar events from one or more ICS feeds.

    Supports a primary shared-family feed plus individual per-member feeds.
    All feeds are fetched and merged; each event is tagged with the correct
    ``calendar_name`` (family member or "Family Shared Calendar").

    Feed resolution priority (highest → lowest):
      1. ``feeds`` constructor argument — explicit list of ``(url, label)`` tuples
      2. ``COZI_ICS_URL_<NAME>`` env vars — individual member feeds
         (COZI_ICS_URL_CHRIS, COZI_ICS_URL_REBEKAH, COZI_ICS_URL_ANNA, COZI_ICS_URL_CALEB, …)
      3. ``COZI_ICS_URL`` env var — shared family feed
      4. JARVIS settings file (``data/settings/family_calendar.json``)
    """

    # Known per-member env var suffixes → display labels
    _MEMBER_ENVS: list[tuple[str, str]] = [
        ("COZI_ICS_URL_CHRIS",   "Chris's Calendar"),
        ("COZI_ICS_URL_REBEKAH", "Rebekah's Calendar"),
        ("COZI_ICS_URL_ANNA",    "Anna's Calendar"),
        ("COZI_ICS_URL_CALEB",   "Caleb's Calendar"),
    ]

    def __init__(
        self,
        username: str = "",
        password: str = "",
        feeds: list[tuple[str, str]] | None = None,
    ) -> None:
        self._username = username
        self._password = password

        if feeds is not None:
            # Explicit list provided — use as-is.
            self._feeds: list[tuple[str, str]] = [
                (url.strip(), label.strip()) for url, label in feeds if url.strip()
            ]
        else:
            self._feeds = self._resolve_feeds()

        # Legacy single-feed compat attributes (first feed wins, or empty).
        if self._feeds:
            self._ics_url, self._label = self._feeds[0]
        else:
            self._ics_url = ""
            self._label = "Family Shared Calendar"
        self._source = "cozi"

        if not self._feeds:
            log.warning(
                "CoziBridge: no ICS URLs configured. Set COZI_ICS_URL (shared) "
                "and/or COZI_ICS_URL_CHRIS / _REBEKAH / _ANNA / _CALEB for "
                "individual member feeds."
            )
        else:
            log.info(
                "CoziBridge: %d feed(s) configured: %s",
                len(self._feeds),
                ", ".join(label for _, label in self._feeds),
            )

    @classmethod
    def _resolve_feeds(cls) -> list[tuple[str, str]]:
        """Build the feed list from environment variables and settings file."""
        feeds: list[tuple[str, str]] = []
        seen_urls: set[str] = set()

        def _add(url: str, label: str) -> None:
            url = url.strip()
            if url and url not in seen_urls:
                seen_urls.add(url)
                feeds.append((url, label))

        # 1. Individual member feeds.
        for env_var, label in cls._MEMBER_ENVS:
            url = os.environ.get(env_var, "").strip()
            if url:
                _add(url, label)

        # 2. Shared family feed (env var).
        shared_url = os.environ.get("COZI_ICS_URL", "").strip()
        if shared_url:
            _add(shared_url, "Family Shared Calendar")

        # 3. Settings file (fallback).
        if not feeds:
            file_url, _, file_label = _load_ics_url_from_settings()
            if file_url:
                _add(file_url, file_label)

        return feeds

    # ------------------------------------------------------------------
    # Configuration probe
    # ------------------------------------------------------------------

    def is_configured(self) -> bool:
        """Return True when an ICS URL is available."""
        return bool(self._ics_url)

    # ------------------------------------------------------------------
    # Auth stub
    # ------------------------------------------------------------------

    def _authenticate(self) -> str:
        """Obtain a Cozi session token.

        Cozi does not publish an official API, so authentication here is a
        stub.  The ICS feed URL is typically public (contains a secret token
        in the path) and does not require a separate login step.

        TODO: If Cozi ever exposes an authenticated API, implement the login
        flow here.  The expected endpoint (based on community reverse-
        engineering) is::

            POST https://api.cozi.com/session
            Content-Type: application/json
            {"username": ..., "password": ...}

        and it returns a JSON body containing a ``sessionToken`` field.
        Store the token on ``self._session_token`` and pass it as a query
        parameter or ``Authorization`` header on subsequent requests.
        """
        log.debug("CoziBridge._authenticate called — ICS flow does not require a token.")
        return ""

    # ------------------------------------------------------------------
    # ICS feed fetch
    # ------------------------------------------------------------------

    def _fetch_ics_text(self, url: str | None = None) -> str:
        """Download the raw ICS feed text from *url* (or ``self._ics_url``)."""
        target = (url or self._ics_url).strip()
        if not target:
            raise RuntimeError("No ICS URL supplied.")
        req = request.Request(
            target,
            headers={"User-Agent": "JARVIS/1.0 (family-calendar-bridge)"},
            method="GET",
        )
        try:
            with request.urlopen(req, timeout=20) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except error.HTTPError as exc:
            raise RuntimeError(f"Cozi ICS fetch failed ({exc.code}): {exc.reason}") from exc
        except Exception as exc:
            raise RuntimeError(f"Cozi ICS fetch error: {exc}") from exc

    # ------------------------------------------------------------------
    # Internal helpers for multi-feed collection
    # ------------------------------------------------------------------

    def _collect_events(
        self,
        from_dt: datetime,
        to_dt: datetime,
    ) -> list[dict[str, Any]]:
        """Fetch all configured feeds, filter to window, dedup, and return sorted list."""
        if not self._feeds:
            log.info("CoziBridge: no feeds configured, returning empty list.")
            return []

        all_results: list[dict[str, Any]] = []
        seen_ids: set[str] = set()

        for feed_url, feed_label in self._feeds:
            try:
                ics_text = self._fetch_ics_text(feed_url)
            except Exception as exc:
                log.error("CoziBridge [%s]: %s", feed_label, exc)
                continue

            raw_events = _parse_ics_events(ics_text)
            for raw in raw_events:
                if _event_in_window(raw["start_iso"], raw["end_iso"], from_dt=from_dt, to_dt=to_dt):
                    event = _normalise_event(raw, source=self._source, calendar_name=feed_label)
                    eid = event.get("external_id", "")
                    if eid not in seen_ids:
                        seen_ids.add(eid)
                        all_results.append(event)

        all_results.sort(key=lambda e: (e.get("start_time") or ""))
        return all_results

    # ------------------------------------------------------------------
    # Public event methods
    # ------------------------------------------------------------------

    def fetch_events(
        self,
        days_back: int = 0,
        days_forward: int = 14,
    ) -> list[dict[str, Any]]:
        """Fetch Cozi calendar events within a rolling window across all feeds.

        Returns a list of normalised event dicts:
        ``{external_id, source, title, description, start_time, end_time,
           all_day, location, attendees, organizer, color, calendar_name}``
        """
        if not self._feeds:
            log.info("CoziBridge.fetch_events: no ICS URL configured, returning empty list.")
            return []

        now = datetime.now(timezone.utc)
        from_dt = now - timedelta(days=max(0, int(days_back)))
        to_dt = now + timedelta(days=max(0, int(days_forward)))

        results = self._collect_events(from_dt, to_dt)
        log.debug("CoziBridge.fetch_events: returned %d events from %d feed(s).", len(results), len(self._feeds))
        return results

    def fetch_todays_events(self) -> list[dict[str, Any]]:
        """Fetch Cozi calendar events for today only across all feeds."""
        if not self._feeds:
            return []

        now = datetime.now(timezone.utc)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)

        return self._collect_events(start_of_day, end_of_day)

    def fetch_upcoming_events(self, days: int = 7) -> list[dict[str, Any]]:
        """Fetch Cozi calendar events for the next ``days`` days across all feeds."""
        return self.fetch_events(days_back=0, days_forward=max(1, int(days)))


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_bridge: CoziBridge | None = None


def get_cozi_bridge() -> CoziBridge | None:
    """Return the initialised singleton, or ``None`` if not yet initialised."""
    return _bridge


def init_cozi_bridge(
    username: str | None = None,
    password: str | None = None,
) -> CoziBridge:
    """Initialise (or replace) the module-level singleton.

    Arguments default to the ``COZI_USERNAME`` / ``COZI_PASSWORD`` env vars.
    The ICS URL is resolved from ``COZI_ICS_URL`` or the JARVIS family
    calendar settings file automatically.
    """
    global _bridge  # noqa: PLW0603

    resolved_username = username or os.environ.get("COZI_USERNAME", "")
    resolved_password = password or os.environ.get("COZI_PASSWORD", "")

    _bridge = CoziBridge(username=resolved_username, password=resolved_password)
    if _bridge.is_configured():
        log.info("CoziBridge initialised (ICS source: %r).", _bridge._source)
    else:
        log.warning(
            "CoziBridge initialised but not configured. "
            "Set COZI_ICS_URL or populate data/settings/family_calendar.json."
        )
    return _bridge
