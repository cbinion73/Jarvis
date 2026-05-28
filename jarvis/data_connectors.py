"""
JARVIS Data Connectors — Epic 4
================================
Unified data-fetching layer for real-time household signals.

All connectors:
  - Return structured dicts (not raw API objects)
  - Degrade gracefully (return empty/mock data on failure, log the error)
  - Cache aggressively (most data is stale after 5-30 min, not 5 seconds)
  - Never block the scheduler (all calls have timeouts)

Connector map:
  GoogleCalendarConnector  — today's events, upcoming meetings, conflicts
  GmailConnector           — unread count, flagged messages, action items
  HomeAssistantConnector   — house state, device status, sensor readings
  WeatherConnector         — current conditions, hourly forecast, alerts
  NewsConnector            — RSS/headlines for configured topics
  ApprovalQueueConnector   — stub for the approval layer (Epic 6)
  BriefingDataAggregator   — calls all connectors and assembles agent context
"""
from __future__ import annotations

import json
import logging
import threading
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, FIRST_COMPLETED
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Any
from urllib import error, request
from urllib.parse import urlencode

logger = logging.getLogger("jarvis.data_connectors")

# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------


@dataclass
class CacheEntry:
    data: dict
    fetched_at: float  # time.monotonic()
    ttl_seconds: int


class ConnectorCache:
    """Thread-safe in-memory cache for connector responses."""

    def __init__(self) -> None:
        self._store: dict[str, CacheEntry] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> dict | None:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            age = time.monotonic() - entry.fetched_at
            if age > entry.ttl_seconds:
                del self._store[key]
                return None
            return entry.data

    def set(self, key: str, data: dict, ttl_seconds: int) -> None:
        with self._lock:
            self._store[key] = CacheEntry(
                data=data,
                fetched_at=time.monotonic(),
                ttl_seconds=ttl_seconds,
            )

    def invalidate(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)


# Module-level cache shared across all connectors
_cache = ConnectorCache()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _local_date_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _local_time_str() -> str:
    return datetime.now().strftime("%H:%M")


def _celsius_to_f(c: float) -> float:
    return round(c * 9 / 5 + 32, 1)


def _ms_to_mph(ms: float) -> float:
    return round(ms * 2.237, 1)


def _wind_direction(degrees: float) -> str:
    dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
            "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    idx = round(degrees / (360 / len(dirs))) % len(dirs)
    return dirs[idx]


def _weather_icon(condition_id: int, description: str) -> str:
    """Map OWM condition ID to a weather emoji."""
    desc = description.lower()
    if condition_id >= 200 and condition_id < 300:
        return "⛈️"
    if condition_id >= 300 and condition_id < 400:
        return "🌦️"
    if condition_id >= 500 and condition_id < 600:
        return "🌧️"
    if condition_id >= 600 and condition_id < 700:
        return "❄️"
    if condition_id >= 700 and condition_id < 800:
        if "fog" in desc or "mist" in desc or "haze" in desc:
            return "🌫️"
        return "🌫️"
    if condition_id == 800:
        return "☀️"
    if condition_id == 801:
        return "🌤️"
    if condition_id in (802, 803):
        return "⛅"
    if condition_id == 804:
        return "☁️"
    return "🌡️"


def _safe_http_get(url: str, headers: dict | None = None, timeout: int = 5) -> bytes | None:
    """Make a GET request with timeout. Returns bytes or None on failure."""
    try:
        req = request.Request(url, headers=headers or {})
        with request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except Exception as exc:
        logger.warning("HTTP GET failed for %s: %s", url, exc)
        return None


# ---------------------------------------------------------------------------
# Google Calendar Connector
# ---------------------------------------------------------------------------


class GoogleCalendarConnector:
    TTL = 300  # 5 minutes

    def __init__(self, config: Any) -> None:
        self._config = config

    def _build_service(self) -> Any | None:
        """Try to build a Google Calendar service. Returns None if unavailable."""
        try:
            from google.auth.transport.requests import Request as GoogleRequest
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
        except ImportError:
            return None

        token_path = self._config.google_token_path
        if not token_path.exists():
            return None

        try:
            scopes = ["https://www.googleapis.com/auth/calendar.readonly"]
            credentials = Credentials.from_authorized_user_file(str(token_path), scopes=scopes)
            if getattr(credentials, "expired", False) and getattr(credentials, "refresh_token", None):
                credentials.refresh(GoogleRequest())
            if not getattr(credentials, "valid", False):
                return None
            return build("calendar", "v3", credentials=credentials, cache_discovery=False)
        except Exception as exc:
            logger.warning("GoogleCalendarConnector: could not build service: %s", exc)
            return None

    def _normalize_event(self, item: dict) -> dict:
        start = item.get("start", {})
        end = item.get("end", {})
        attendees = item.get("attendees", [])
        attendee_emails = [a.get("email", "") for a in attendees if a.get("email")]
        is_meeting = len(attendees) > 1
        return {
            "id": item.get("id", ""),
            "title": item.get("summary", "(Untitled)"),
            "start": start.get("dateTime") or start.get("date") or "",
            "end": end.get("dateTime") or end.get("date") or "",
            "location": item.get("location", ""),
            "attendees": attendee_emails,
            "is_meeting": is_meeting,
            "calendar": item.get("organizer", {}).get("email", "primary"),
            "description": (item.get("description", "") or "")[:200],
        }

    def _mock_today_events(self) -> dict:
        today = _local_date_str()
        return {
            "events": [
                {
                    "id": "mock-001",
                    "title": "Team Standup",
                    "start": f"{today}T09:00:00",
                    "end": f"{today}T09:30:00",
                    "location": "",
                    "attendees": ["team@example.com"],
                    "is_meeting": True,
                    "calendar": "primary",
                    "description": "Daily sync",
                },
                {
                    "id": "mock-002",
                    "title": "Client Check-In",
                    "start": f"{today}T14:00:00",
                    "end": f"{today}T15:00:00",
                    "location": "Zoom",
                    "attendees": ["client@example.com"],
                    "is_meeting": True,
                    "calendar": "primary",
                    "description": "Monthly review",
                },
                {
                    "id": "mock-003",
                    "title": "School Pickup",
                    "start": f"{today}T15:45:00",
                    "end": f"{today}T16:15:00",
                    "location": "Elementary School",
                    "attendees": [],
                    "is_meeting": False,
                    "calendar": "family",
                    "description": "",
                },
            ],
            "count": 3,
            "next_event": None,
            "has_conflict": False,
            "fetched_at": _now_iso(),
            "source": "mock",
        }

    def get_today_events(self, actor_id: str = "chris") -> dict:
        cache_key = f"calendar_today_{actor_id}"
        cached = _cache.get(cache_key)
        if cached is not None:
            return cached

        service = self._build_service()
        if service is None:
            logger.warning("GoogleCalendarConnector: no service available, returning mock data")
            result = self._mock_today_events()
            _cache.set(cache_key, result, self.TTL)
            return result

        try:
            now = datetime.now(timezone.utc)
            start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = start_of_day + timedelta(days=1)

            raw = (
                service.events()
                .list(
                    calendarId="primary",
                    timeMin=start_of_day.isoformat(),
                    timeMax=end_of_day.isoformat(),
                    singleEvents=True,
                    orderBy="startTime",
                    maxResults=20,
                )
                .execute()
            )
            events = [self._normalize_event(e) for e in raw.get("items", [])]

            # Find next upcoming event
            now_iso = now.isoformat()
            next_event = None
            for evt in events:
                if evt["start"] >= now_iso:
                    next_event = evt
                    break

            # Detect conflicts (overlapping events)
            has_conflict = False
            for i in range(len(events) - 1):
                if events[i]["end"] and events[i + 1]["start"]:
                    if events[i]["end"] > events[i + 1]["start"]:
                        has_conflict = True
                        break

            result = {
                "events": events,
                "count": len(events),
                "next_event": next_event,
                "has_conflict": has_conflict,
                "fetched_at": _now_iso(),
                "source": "google_calendar",
            }
            _cache.set(cache_key, result, self.TTL)
            return result

        except Exception as exc:
            logger.warning("GoogleCalendarConnector.get_today_events failed: %s", exc)
            result = self._mock_today_events()
            _cache.set(cache_key, result, self.TTL)
            return result

    def get_upcoming_events(self, days: int = 7, actor_id: str = "chris") -> dict:
        cache_key = f"calendar_upcoming_{actor_id}_{days}"
        cached = _cache.get(cache_key)
        if cached is not None:
            return cached

        service = self._build_service()
        if service is None:
            logger.warning("GoogleCalendarConnector: no service available for upcoming events, returning mock data")
            # Return mock with a few more events spread across the week
            today = _local_date_str()
            result = {
                "events": [
                    {
                        "id": "mock-week-001",
                        "title": "Weekly Planning",
                        "start": f"{today}T10:00:00",
                        "end": f"{today}T11:00:00",
                        "location": "",
                        "attendees": [],
                        "is_meeting": False,
                        "calendar": "primary",
                        "description": "",
                    },
                    {
                        "id": "mock-week-002",
                        "title": "Family Dinner",
                        "start": f"{today}T18:30:00",
                        "end": f"{today}T20:00:00",
                        "location": "Home",
                        "attendees": [],
                        "is_meeting": False,
                        "calendar": "family",
                        "description": "",
                    },
                ],
                "count": 2,
                "next_event": None,
                "has_conflict": False,
                "fetched_at": _now_iso(),
                "source": "mock",
            }
            _cache.set(cache_key, result, self.TTL)
            return result

        try:
            now = datetime.now(timezone.utc)
            horizon = now + timedelta(days=days)

            raw = (
                service.events()
                .list(
                    calendarId="primary",
                    timeMin=now.isoformat(),
                    timeMax=horizon.isoformat(),
                    singleEvents=True,
                    orderBy="startTime",
                    maxResults=50,
                )
                .execute()
            )
            events = [self._normalize_event(e) for e in raw.get("items", [])]
            next_event = events[0] if events else None

            result = {
                "events": events,
                "count": len(events),
                "next_event": next_event,
                "has_conflict": False,
                "fetched_at": _now_iso(),
                "source": "google_calendar",
            }
            _cache.set(cache_key, result, self.TTL)
            return result

        except Exception as exc:
            logger.warning("GoogleCalendarConnector.get_upcoming_events failed: %s", exc)
            result = {
                "events": [],
                "count": 0,
                "next_event": None,
                "has_conflict": False,
                "fetched_at": _now_iso(),
                "source": "mock",
            }
            _cache.set(cache_key, result, self.TTL)
            return result


# ---------------------------------------------------------------------------
# Gmail Connector
# ---------------------------------------------------------------------------


class GmailConnector:
    TTL = 120  # 2 minutes

    # Keywords that suggest action is required
    _ACTION_KEYWORDS = (
        "invoice", "please review", "action required", "approve", "confirm",
        "deadline", "urgent", "asap", "follow up", "response needed",
        "your attention", "awaiting", "by eod", "by end of day",
    )
    # Senders/subjects that are likely newsletters
    _NEWSLETTER_PATTERNS = (
        "unsubscribe", "newsletter", "digest", "weekly", "daily briefing",
        "noreply", "no-reply", "marketing", "promotion",
    )

    def __init__(self, config: Any) -> None:
        self._config = config

    def _build_service(self) -> Any | None:
        try:
            from google.auth.transport.requests import Request as GoogleRequest
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
        except ImportError:
            return None

        token_path = self._config.google_token_path
        if not token_path.exists():
            return None

        try:
            scopes = ["https://www.googleapis.com/auth/gmail.readonly"]
            credentials = Credentials.from_authorized_user_file(str(token_path), scopes=scopes)
            if getattr(credentials, "expired", False) and getattr(credentials, "refresh_token", None):
                credentials.refresh(GoogleRequest())
            if not getattr(credentials, "valid", False):
                return None
            return build("gmail", "v1", credentials=credentials, cache_discovery=False)
        except Exception as exc:
            logger.warning("GmailConnector: could not build service: %s", exc)
            return None

    def _is_newsletter(self, from_addr: str, subject: str) -> bool:
        combined = (from_addr + " " + subject).lower()
        return any(pat in combined for pat in self._NEWSLETTER_PATTERNS)

    def _is_action_item(self, subject: str, snippet: str) -> bool:
        combined = (subject + " " + snippet).lower()
        return any(kw in combined for kw in self._ACTION_KEYWORDS)

    def _guess_priority(self, subject: str, snippet: str) -> str:
        combined = (subject + " " + snippet).lower()
        if any(kw in combined for kw in ("urgent", "asap", "critical", "immediately")):
            return "high"
        if any(kw in combined for kw in ("invoice", "deadline", "action required", "approve")):
            return "medium"
        return "normal"

    def get_inbox_summary(self, actor_id: str = "chris") -> dict:
        cache_key = f"gmail_inbox_{actor_id}"
        cached = _cache.get(cache_key)
        if cached is not None:
            return cached

        service = self._build_service()
        if service is None:
            logger.warning("GmailConnector: no service available, returning mock data")
            result = {
                "unread_count": 14,
                "flagged_count": 2,
                "action_items": [
                    {
                        "id": "mock-email-001",
                        "from": "vendor@example.com",
                        "subject": "Invoice #1042 — Please Approve",
                        "snippet": "Attached is the invoice for services rendered. Please approve by EOD.",
                        "received_at": _now_iso(),
                        "priority": "high",
                    },
                    {
                        "id": "mock-email-002",
                        "from": "dr.patel@clinic.com",
                        "subject": "Appointment Confirmation Needed",
                        "snippet": "Please confirm your appointment for next Tuesday at 2pm.",
                        "received_at": _now_iso(),
                        "priority": "medium",
                    },
                ],
                "newsletters": 3,
                "source": "mock",
                "fetched_at": _now_iso(),
            }
            _cache.set(cache_key, result, self.TTL)
            return result

        try:
            # Get unread messages
            unread_resp = (
                service.users()
                .messages()
                .list(userId="me", q="in:inbox is:unread", maxResults=25)
                .execute()
            )
            message_refs = unread_resp.get("messages", [])
            unread_count = len(message_refs)

            # Get flagged/starred messages
            flagged_resp = (
                service.users()
                .messages()
                .list(userId="me", q="in:inbox is:starred", maxResults=10)
                .execute()
            )
            flagged_count = len(flagged_resp.get("messages", []))

            action_items = []
            newsletter_count = 0

            for msg_ref in message_refs[:20]:
                try:
                    metadata = (
                        service.users()
                        .messages()
                        .get(
                            userId="me",
                            id=msg_ref["id"],
                            format="metadata",
                            metadataHeaders=["From", "Subject", "Date"],
                        )
                        .execute()
                    )
                    headers = {
                        entry.get("name", "").lower(): entry.get("value", "")
                        for entry in metadata.get("payload", {}).get("headers", [])
                    }
                    from_addr = headers.get("from", "")
                    subject = headers.get("subject", "(No subject)")
                    snippet = metadata.get("snippet", "")
                    received_at = headers.get("date", _now_iso())

                    if self._is_newsletter(from_addr, subject):
                        newsletter_count += 1
                    elif self._is_action_item(subject, snippet):
                        action_items.append({
                            "id": msg_ref["id"],
                            "from": from_addr,
                            "subject": subject,
                            "snippet": snippet[:200],
                            "received_at": received_at,
                            "priority": self._guess_priority(subject, snippet),
                        })
                except Exception:
                    pass  # skip individual message errors

            result = {
                "unread_count": unread_count,
                "flagged_count": flagged_count,
                "action_items": action_items[:5],  # cap to top 5
                "newsletters": newsletter_count,
                "source": "gmail",
                "fetched_at": _now_iso(),
            }
            _cache.set(cache_key, result, self.TTL)
            return result

        except Exception as exc:
            logger.warning("GmailConnector.get_inbox_summary failed: %s", exc)
            result = {
                "unread_count": 0,
                "flagged_count": 0,
                "action_items": [],
                "newsletters": 0,
                "source": "mock",
                "fetched_at": _now_iso(),
            }
            _cache.set(cache_key, result, self.TTL)
            return result


# ---------------------------------------------------------------------------
# Home Assistant Connector
# ---------------------------------------------------------------------------


class HomeAssistantConnector:
    """Connects to Home Assistant REST API."""

    TTL = 30  # 30 seconds — house state changes fast

    def __init__(self, config: Any) -> None:
        self._config = config

    @property
    def _base_url(self) -> str:
        return (self._config.home_assistant_url or "").rstrip("/")

    @property
    def _token(self) -> str:
        return self._config.home_assistant_token or ""

    def _is_configured(self) -> bool:
        return bool(self._base_url and self._token)

    def _ha_get(self, path: str) -> dict | list | None:
        """GET a HA API path. Returns parsed JSON or None on failure."""
        if not self._is_configured():
            return None
        url = f"{self._base_url}/api{path}"
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }
        raw = _safe_http_get(url, headers=headers, timeout=5)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except Exception as exc:
            logger.warning("HomeAssistantConnector: JSON parse error for %s: %s", path, exc)
            return None

    def _ha_post(self, path: str, payload: dict) -> dict | None:
        """POST to a HA API path. Returns parsed JSON or None on failure."""
        if not self._is_configured():
            return None
        url = f"{self._base_url}/api{path}"
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }
        try:
            data = json.dumps(payload).encode()
            req = request.Request(url, data=data, headers=headers, method="POST")
            with request.urlopen(req, timeout=5) as resp:
                return json.loads(resp.read())
        except Exception as exc:
            logger.warning("HomeAssistantConnector: POST failed for %s: %s", path, exc)
            return None

    def _mock_house_state(self) -> dict:
        return {
            "present_members": ["Chris"],
            "doors": {"front": "locked", "garage": "closed", "back": "locked"},
            "garage": {"door": "closed", "last_change": _now_iso()},
            "temperature": {"inside": 71.0, "target": 70.0, "mode": "cool"},
            "lights_on": ["office"],
            "alerts": [],
            "devices_offline": [],
            "source": "mock",
            "fetched_at": _now_iso(),
        }

    def get_house_state(self) -> dict:
        cache_key = "ha_house_state"
        cached = _cache.get(cache_key)
        if cached is not None:
            return cached

        if not self._is_configured():
            logger.warning("HomeAssistantConnector: not configured (HA_URL or HA_TOKEN missing), returning mock")
            result = self._mock_house_state()
            _cache.set(cache_key, result, self.TTL)
            return result

        states = self._ha_get("/states")
        if not isinstance(states, list):
            logger.warning("HomeAssistantConnector: could not fetch states, returning mock")
            result = self._mock_house_state()
            _cache.set(cache_key, result, self.TTL)
            return result

        # Parse states into categories
        present_members: list[str] = []
        doors: dict[str, str] = {}
        garage_info: dict[str, str] = {}
        inside_temp: float | None = None
        target_temp: float | None = None
        climate_mode: str = "unknown"
        lights_on: list[str] = []
        alerts: list[dict] = []
        devices_offline: list[str] = []

        for entity in states:
            entity_id: str = entity.get("entity_id", "")
            state: str = entity.get("state", "unknown")
            attrs: dict = entity.get("attributes", {})
            friendly_name: str = attrs.get("friendly_name", entity_id)

            # Person / device tracker for presence
            if entity_id.startswith("person.") or entity_id.startswith("device_tracker."):
                if state in ("home", "Home"):
                    name = friendly_name or entity_id.split(".", 1)[-1].replace("_", " ").title()
                    if name not in present_members:
                        present_members.append(name)

            # Locks and doors
            elif entity_id.startswith("lock.") or entity_id.startswith("binary_sensor.") and "door" in entity_id:
                label = friendly_name.lower().replace(" ", "_")
                doors[label] = state

            # Cover (garage door)
            elif entity_id.startswith("cover.") and "garage" in entity_id:
                garage_info = {
                    "door": state,
                    "last_change": entity.get("last_changed", _now_iso()),
                }

            # Climate
            elif entity_id.startswith("climate."):
                inside_temp_raw = attrs.get("current_temperature")
                target_temp_raw = attrs.get("temperature")
                climate_mode = attrs.get("hvac_mode", state)
                if inside_temp_raw is not None:
                    try:
                        inside_temp = float(inside_temp_raw)
                    except (TypeError, ValueError):
                        pass
                if target_temp_raw is not None:
                    try:
                        target_temp = float(target_temp_raw)
                    except (TypeError, ValueError):
                        pass

            # Sensor temperature (fallback for inside temp)
            elif entity_id.startswith("sensor.") and "temperature" in entity_id and "outside" not in entity_id:
                if inside_temp is None:
                    try:
                        inside_temp = float(state)
                    except (TypeError, ValueError):
                        pass

            # Lights
            elif entity_id.startswith("light.") and state == "on":
                room = friendly_name or entity_id.split(".", 1)[-1].replace("_", " ").title()
                lights_on.append(room)

            # Safety sensors
            elif entity_id.startswith("binary_sensor.") and any(
                kw in entity_id for kw in ("smoke", "co", "carbon_monoxide", "leak", "flood")
            ):
                if state in ("on", "detected"):
                    alerts.append({
                        "entity": entity_id,
                        "state": state,
                        "message": f"{friendly_name}: {state}",
                    })

            # Unavailable devices
            elif state in ("unavailable", "unknown") and entity_id.startswith(
                ("switch.", "light.", "sensor.", "binary_sensor.")
            ):
                devices_offline.append(entity_id)

        # Build temperature dict (convert from C if needed — HA stores in the unit configured)
        # We'll trust HA's unit and note it
        temperature_info = {
            "inside": inside_temp if inside_temp is not None else 0.0,
            "target": target_temp if target_temp is not None else 0.0,
            "mode": climate_mode,
        }

        result = {
            "present_members": present_members,
            "doors": doors if doors else {"front": "unknown"},
            "garage": garage_info if garage_info else {"door": "unknown", "last_change": _now_iso()},
            "temperature": temperature_info,
            "lights_on": lights_on,
            "alerts": alerts,
            "devices_offline": devices_offline[:10],  # cap list
            "source": "home_assistant",
            "fetched_at": _now_iso(),
        }
        _cache.set(cache_key, result, self.TTL)
        return result

    def get_sensor(self, entity_id: str) -> dict:
        """Get a single HA entity state."""
        cache_key = f"ha_sensor_{entity_id}"
        cached = _cache.get(cache_key)
        if cached is not None:
            return cached

        if not self._is_configured():
            return {"entity_id": entity_id, "state": "unknown", "attributes": {}, "source": "mock"}

        data = self._ha_get(f"/states/{entity_id}")
        if not isinstance(data, dict):
            return {"entity_id": entity_id, "state": "unknown", "attributes": {}, "source": "mock"}

        result = {
            "entity_id": entity_id,
            "state": data.get("state", "unknown"),
            "attributes": data.get("attributes", {}),
            "last_changed": data.get("last_changed", ""),
            "source": "home_assistant",
        }
        _cache.set(cache_key, result, 15)  # 15s for individual sensors
        return result

    def call_service(self, domain: str, service: str, entity_id: str, **kwargs: Any) -> bool:
        """
        Call a HA service. Returns True on success.
        NOTE: This is a write operation — should only be called after approval.
        """
        if not self._is_configured():
            logger.warning("HomeAssistantConnector.call_service: not configured")
            return False

        payload: dict[str, Any] = {"entity_id": entity_id}
        payload.update(kwargs)

        result = self._ha_post(f"/services/{domain}/{service}", payload)
        if result is None:
            return False
        logger.info("HomeAssistantConnector: called %s.%s on %s", domain, service, entity_id)
        return True


# ---------------------------------------------------------------------------
# Weather Connector
# ---------------------------------------------------------------------------


class WeatherConnector:
    """OpenWeatherMap API connector."""

    TTL = 600  # 10 minutes

    # Default location: Alexandria, VA
    DEFAULT_LAT = 38.8048
    DEFAULT_LON = -77.0469

    def __init__(self, config: Any) -> None:
        self._config = config

    @property
    def _api_key(self) -> str:
        import os
        return os.getenv("OPENWEATHER_API_KEY", "")

    @property
    def _lat(self) -> float:
        import os
        try:
            return float(os.getenv("WEATHER_LAT", str(self.DEFAULT_LAT)))
        except ValueError:
            return self.DEFAULT_LAT

    @property
    def _lon(self) -> float:
        import os
        try:
            return float(os.getenv("WEATHER_LON", str(self.DEFAULT_LON)))
        except ValueError:
            return self.DEFAULT_LON

    def _is_configured(self) -> bool:
        # Prefer WeatherKit (free) when the Apple key is present
        from pathlib import Path
        if Path("data/settings/apns_key.p8").exists() and Path("data/settings/apns_config.json").exists():
            return True
        return bool(self._api_key)

    def _mock_current(self) -> dict:
        return {
            "temp_f": 74.0,
            "feels_like_f": 72.0,
            "condition": "Partly Cloudy",
            "humidity": 55,
            "wind_mph": 8.5,
            "wind_dir": "SW",
            "visibility_miles": 10.0,
            "alerts": [],
            "icon": "⛅",
            "source": "mock",
            "fetched_at": _now_iso(),
        }

    def get_current(self) -> dict:
        cache_key = "weather_current"
        cached = _cache.get(cache_key)
        if cached is not None:
            return cached

        if not self._is_configured():
            logger.warning("WeatherConnector: no weather API configured, returning mock data")
            result = self._mock_current()
            _cache.set(cache_key, result, self.TTL)
            return result

        # ── WeatherKit (preferred, free) ─────────────────────────────────────
        from pathlib import Path as _Path
        if _Path("data/settings/apns_key.p8").exists():
            try:
                from jarvis import weatherkit_client as _wk
                result = _wk.get_current(self._lat, self._lon)
                _cache.set(cache_key, result, self.TTL)
                return result
            except Exception as _exc:
                logger.warning("WeatherKit get_current failed: %s — falling back to OWM", _exc)

        # ── OpenWeatherMap (fallback) ─────────────────────────────────────────
        params = urlencode({
            "lat": self._lat,
            "lon": self._lon,
            "appid": self._api_key,
            "units": "imperial",
            "exclude": "minutely,daily",
        })
        url = f"https://api.openweathermap.org/data/3.0/onecall?{params}"
        raw = _safe_http_get(url, timeout=5)

        if raw is None:
            logger.warning("WeatherConnector: API call failed, returning mock data")
            result = self._mock_current()
            _cache.set(cache_key, result, self.TTL)
            return result

        try:
            data = json.loads(raw)
            current = data.get("current", {})
            weather_list = current.get("weather", [{}])
            weather_info = weather_list[0] if weather_list else {}

            condition_id = weather_info.get("id", 800)
            description = weather_info.get("description", "clear sky")
            condition = weather_info.get("main", description.title())

            # Check for alerts
            alerts_raw = data.get("alerts", [])
            alert_msgs = [a.get("event", "Weather alert") for a in alerts_raw]

            result = {
                "temp_f": round(float(current.get("temp", 70)), 1),
                "feels_like_f": round(float(current.get("feels_like", 70)), 1),
                "condition": condition,
                "humidity": int(current.get("humidity", 50)),
                "wind_mph": _ms_to_mph(float(current.get("wind_speed", 0))),
                "wind_dir": _wind_direction(float(current.get("wind_deg", 0))),
                "visibility_miles": round(float(current.get("visibility", 16000)) / 1609.34, 1),
                "alerts": alert_msgs,
                "icon": _weather_icon(condition_id, description),
                "source": "openweathermap",
                "fetched_at": _now_iso(),
            }
            _cache.set(cache_key, result, self.TTL)
            return result

        except Exception as exc:
            logger.warning("WeatherConnector: failed to parse response: %s", exc)
            result = self._mock_current()
            _cache.set(cache_key, result, self.TTL)
            return result

    def get_forecast(self, hours: int = 24) -> dict:
        cache_key = f"weather_forecast_{hours}"
        cached = _cache.get(cache_key)
        if cached is not None:
            return cached

        if not self._is_configured():
            result = {
                "hourly": [
                    {"hour": f"{h:02d}:00", "temp_f": 72.0 + h * 0.5, "condition": "Partly Cloudy", "icon": "⛅"}
                    for h in range(min(hours, 12))
                ],
                "daily_high_f": 78.0,
                "daily_low_f": 62.0,
                "source": "mock",
                "fetched_at": _now_iso(),
            }
            _cache.set(cache_key, result, self.TTL)
            return result

        # ── WeatherKit (preferred, free) ─────────────────────────────────────
        from pathlib import Path as _Path
        if _Path("data/settings/apns_key.p8").exists():
            try:
                from jarvis import weatherkit_client as _wk
                result = _wk.get_forecast(self._lat, self._lon, days=7)
                # Normalise hourly list to match OWM consumer expectations
                result.setdefault("hourly", result.pop("hourly", []))
                _cache.set(cache_key, result, self.TTL)
                return result
            except Exception as _exc:
                logger.warning("WeatherKit get_forecast failed: %s — falling back to OWM", _exc)

        # ── OpenWeatherMap (fallback) ─────────────────────────────────────────
        params = urlencode({
            "lat": self._lat,
            "lon": self._lon,
            "appid": self._api_key,
            "units": "imperial",
            "exclude": "minutely,alerts",
        })
        url = f"https://api.openweathermap.org/data/3.0/onecall?{params}"
        raw = _safe_http_get(url, timeout=5)

        if raw is None:
            result = {
                "hourly": [],
                "daily_high_f": 0.0,
                "daily_low_f": 0.0,
                "source": "mock",
                "fetched_at": _now_iso(),
            }
            _cache.set(cache_key, result, self.TTL)
            return result

        try:
            data = json.loads(raw)
            hourly_raw = data.get("hourly", [])[:hours]
            hourly = []
            for entry in hourly_raw:
                weather_info = entry.get("weather", [{}])[0]
                cond_id = weather_info.get("id", 800)
                desc = weather_info.get("description", "clear")
                ts = entry.get("dt", 0)
                hour_label = datetime.fromtimestamp(ts).strftime("%H:%M") if ts else "??"
                hourly.append({
                    "hour": hour_label,
                    "temp_f": round(float(entry.get("temp", 70)), 1),
                    "condition": weather_info.get("main", desc.title()),
                    "icon": _weather_icon(cond_id, desc),
                })

            daily_raw = data.get("daily", [{}])
            daily_today = daily_raw[0] if daily_raw else {}
            daily_temp = daily_today.get("temp", {})

            result = {
                "hourly": hourly,
                "daily_high_f": round(float(daily_temp.get("max", 0)), 1),
                "daily_low_f": round(float(daily_temp.get("min", 0)), 1),
                "source": "openweathermap",
                "fetched_at": _now_iso(),
            }
            _cache.set(cache_key, result, self.TTL)
            return result

        except Exception as exc:
            logger.warning("WeatherConnector.get_forecast failed: %s", exc)
            result = {
                "hourly": [],
                "daily_high_f": 0.0,
                "daily_low_f": 0.0,
                "source": "mock",
                "fetched_at": _now_iso(),
            }
            _cache.set(cache_key, result, self.TTL)
            return result


# ---------------------------------------------------------------------------
# News Connector
# ---------------------------------------------------------------------------


class NewsConnector:
    """Fetches RSS headlines for configured topics."""

    TTL = 1800  # 30 minutes

    DEFAULT_FEEDS = [
        ("AP Top News", "https://feeds.apnews.com/rss/apf-topnews"),
        ("Christianity Today", "https://www.christianitytoday.com/ct/channel/rss.xml"),
        ("3D Printing Industry", "https://3dprintingindustry.com/feed/"),
    ]

    def __init__(self, config: Any) -> None:
        self._config = config

    def _parse_rss(self, xml_bytes: bytes, source_name: str, max_items: int) -> list[dict]:
        """Parse RSS XML bytes into headline dicts."""
        headlines = []
        try:
            root = ET.fromstring(xml_bytes)
            # RSS 2.0 structure: rss > channel > item
            # Try both rss and Atom formats
            items = root.findall(".//item")
            if not items:
                # Try Atom feed
                ns = {"atom": "http://www.w3.org/2005/Atom"}
                items = root.findall(".//atom:entry", ns)

            for item in items[:max_items]:
                # RSS 2.0
                title_el = item.find("title")
                link_el = item.find("link")
                pub_el = item.find("pubDate") or item.find("published")

                # Atom fallback
                if title_el is None:
                    title_el = item.find("{http://www.w3.org/2005/Atom}title")
                if link_el is None:
                    link_el = item.find("{http://www.w3.org/2005/Atom}link")
                if pub_el is None:
                    pub_el = item.find("{http://www.w3.org/2005/Atom}published")

                title = (title_el.text or "").strip() if title_el is not None else ""
                if link_el is not None:
                    link = link_el.text or link_el.get("href", "")
                else:
                    link = ""
                link = (link or "").strip()
                published = (pub_el.text or "").strip() if pub_el is not None else ""

                if title:
                    headlines.append({
                        "title": title,
                        "source": source_name,
                        "url": link,
                        "published": published,
                    })
        except ET.ParseError as exc:
            logger.warning("NewsConnector: XML parse error for %s: %s", source_name, exc)
        return headlines

    def get_headlines(self, max_per_feed: int = 3) -> dict:
        cache_key = f"news_headlines_{max_per_feed}"
        cached = _cache.get(cache_key)
        if cached is not None:
            return cached

        all_headlines: list[dict] = []
        any_real = False

        for feed_name, feed_url in self.DEFAULT_FEEDS:
            raw = _safe_http_get(feed_url, timeout=5)
            if raw is None:
                logger.warning("NewsConnector: could not fetch %s", feed_url)
                continue
            items = self._parse_rss(raw, feed_name, max_per_feed)
            all_headlines.extend(items)
            if items:
                any_real = True

        if not any_real:
            logger.warning("NewsConnector: all feeds failed, returning mock headlines")
            result = {
                "headlines": [
                    {
                        "title": "Top Story: Community Leaders Meet to Address Local Concerns",
                        "source": "AP Top News",
                        "url": "https://apnews.com",
                        "published": _now_iso(),
                    },
                    {
                        "title": "Faith in Action: How Local Churches Are Serving Their Communities",
                        "source": "Christianity Today",
                        "url": "https://www.christianitytoday.com",
                        "published": _now_iso(),
                    },
                    {
                        "title": "New 3D Printing Materials Expand Design Possibilities",
                        "source": "3D Printing Industry",
                        "url": "https://3dprintingindustry.com",
                        "published": _now_iso(),
                    },
                ],
                "total": 3,
                "fetched_at": _now_iso(),
                "source": "mock",
            }
            _cache.set(cache_key, result, self.TTL)
            return result

        result = {
            "headlines": all_headlines,
            "total": len(all_headlines),
            "fetched_at": _now_iso(),
            "source": "rss",
        }
        _cache.set(cache_key, result, self.TTL)
        return result


# ---------------------------------------------------------------------------
# Approval Queue Connector (Epic 6 stub)
# ---------------------------------------------------------------------------


class ApprovalQueueConnector:
    """Stub for the approval layer — Epic 6 will fill this in."""

    def get_pending(self) -> dict:
        return {
            "pending": [],
            "count": 0,
            "source": "stub",
            "fetched_at": _now_iso(),
        }


# ---------------------------------------------------------------------------
# Briefing Data Aggregator
# ---------------------------------------------------------------------------


class BriefingDataAggregator:
    """
    Calls all connectors in parallel (ThreadPoolExecutor) and assembles
    a unified context dict for agents.
    """

    def __init__(
        self,
        calendar: GoogleCalendarConnector,
        gmail: GmailConnector,
        ha: HomeAssistantConnector,
        weather: WeatherConnector,
        news: NewsConnector,
    ) -> None:
        self.calendar = calendar
        self.gmail = gmail
        self.ha = ha
        self.weather = weather
        self.news = news

    def get_morning_context(self, actor_id: str = "chris") -> dict:
        """
        Returns unified morning briefing context. Runs all fetches in parallel,
        waits up to 8 seconds total.
        """
        results: dict[str, dict] = {}
        errors: dict[str, str] = {}

        tasks = {
            "calendar": lambda: self.calendar.get_today_events(actor_id),
            "inbox": lambda: self.gmail.get_inbox_summary(actor_id),
            "house": lambda: self.ha.get_house_state(),
            "weather": lambda: self.weather.get_current(),
            "headlines": lambda: self.news.get_headlines(),
        }

        with ThreadPoolExecutor(max_workers=5, thread_name_prefix="jarvis-agg") as pool:
            futures = {pool.submit(fn): name for name, fn in tasks.items()}
            done, pending = wait(futures.keys(), timeout=8)

            for future in done:
                name = futures[future]
                try:
                    results[name] = future.result()
                except Exception as exc:
                    logger.warning("BriefingDataAggregator: %s fetch failed: %s", name, exc)
                    errors[name] = str(exc)
                    results[name] = {}

            for future in pending:
                name = futures[future]
                logger.warning("BriefingDataAggregator: %s timed out", name)
                errors[name] = "timeout"
                results[name] = {}
                future.cancel()

        return {
            "calendar": results.get("calendar", {}),
            "inbox": results.get("inbox", {}),
            "house": results.get("house", {}),
            "weather": results.get("weather", {}),
            "headlines": results.get("headlines", {}),
            "assembled_at": _now_iso(),
            "actor_id": actor_id,
            "errors": errors,
        }

    def get_quick_context(self) -> dict:
        """Lighter version: weather + house state only (< 2 sec)."""
        results: dict[str, dict] = {}

        tasks = {
            "weather": lambda: self.weather.get_current(),
            "house": lambda: self.ha.get_house_state(),
        }

        with ThreadPoolExecutor(max_workers=2, thread_name_prefix="jarvis-quick") as pool:
            futures = {pool.submit(fn): name for name, fn in tasks.items()}
            done, pending = wait(futures.keys(), timeout=4)

            for future in done:
                name = futures[future]
                try:
                    results[name] = future.result()
                except Exception as exc:
                    logger.warning("BriefingDataAggregator.quick: %s failed: %s", name, exc)
                    results[name] = {}

            for future in pending:
                name = futures[future]
                logger.warning("BriefingDataAggregator.quick: %s timed out", name)
                results[name] = {}
                future.cancel()

        return {
            "weather": results.get("weather", {}),
            "house": results.get("house", {}),
            "assembled_at": _now_iso(),
        }


# ---------------------------------------------------------------------------
# Module-level singletons
# ---------------------------------------------------------------------------

_calendar_connector: GoogleCalendarConnector | None = None
_gmail_connector: GmailConnector | None = None
_ha_connector: HomeAssistantConnector | None = None
_weather_connector: WeatherConnector | None = None
_news_connector: NewsConnector | None = None
_aggregator: BriefingDataAggregator | None = None


def init_connectors(config: Any) -> BriefingDataAggregator:
    """Initialize all connectors with config. Returns aggregator. Safe to call multiple times."""
    global _calendar_connector, _gmail_connector, _ha_connector
    global _weather_connector, _news_connector, _aggregator

    if _aggregator is not None:
        return _aggregator

    _calendar_connector = GoogleCalendarConnector(config)
    _gmail_connector = GmailConnector(config)
    _ha_connector = HomeAssistantConnector(config)
    _weather_connector = WeatherConnector(config)
    _news_connector = NewsConnector(config)

    _aggregator = BriefingDataAggregator(
        calendar=_calendar_connector,
        gmail=_gmail_connector,
        ha=_ha_connector,
        weather=_weather_connector,
        news=_news_connector,
    )

    logger.info("JARVIS data connectors initialized (Epic 4)")
    return _aggregator


def get_aggregator() -> BriefingDataAggregator | None:
    return _aggregator


def get_calendar() -> GoogleCalendarConnector | None:
    return _calendar_connector


def get_gmail() -> GmailConnector | None:
    return _gmail_connector


def get_ha() -> HomeAssistantConnector | None:
    return _ha_connector


def get_weather() -> WeatherConnector | None:
    return _weather_connector


def get_news() -> NewsConnector | None:
    return _news_connector
