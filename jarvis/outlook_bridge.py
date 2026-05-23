"""JARVIS Outlook Bridge — reads Outlook email and calendar via Microsoft Graph.

Uses the existing *delegated* OAuth token stored on disk by MicrosoftGraphSupport
(the one acquired through the browser-based PKCE / authorisation-code flow).
This is required for personal Outlook.com accounts; the client-credentials
(app-only) flow returns 401 for those mailboxes.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
_TOKEN_ENDPOINT_TMPL = "https://login.microsoftonline.com/{authority}/oauth2/v2.0/token"
_OAUTH_SCOPES = "openid profile offline_access User.Read Mail.Read Calendars.Read"

# ---------------------------------------------------------------------------
# Optional requests import — fall back to urllib when absent.
# ---------------------------------------------------------------------------
try:
    import requests as _requests  # type: ignore[import]
    _REQUESTS_AVAILABLE = True
except ImportError:
    _REQUESTS_AVAILABLE = False
    from urllib import error as _url_error, parse as _url_parse, request as _url_request  # type: ignore[assignment]


def _dt_to_iso(dt: datetime) -> str:
    """Convert a timezone-aware datetime to an ISO-8601 string using 'Z' suffix.

    Microsoft Graph rejects the '+00:00' form in calendarView query params.
    """
    utc = dt.astimezone(timezone.utc)
    return utc.strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Main bridge class
# ---------------------------------------------------------------------------


class OutlookBridge:
    """Microsoft Graph bridge for personal Outlook.com mail + calendar.

    Authenticates via a delegated access token stored in *token_path*.
    Automatically refreshes the token whenever it is within 120 seconds of
    expiry and persists the refreshed credentials back to the same file.
    """

    def __init__(
        self,
        token_path: Path | str,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        authority: str = "common",
    ) -> None:
        self._token_path = Path(token_path)
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri
        self._authority = authority
        # In-memory cache so we don't hit disk on every request.
        self._token_cache: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Token management
    # ------------------------------------------------------------------

    def _load_token(self) -> dict[str, Any]:
        """Return a valid token dict, refreshing from disk/remote as needed."""
        # Re-read from disk only when our in-memory cache is empty.
        if not self._token_cache:
            if not self._token_path.exists():
                raise RuntimeError(
                    f"Outlook delegated token not found at {self._token_path}. "
                    "Please connect your Microsoft account through the JARVIS UI."
                )
            try:
                disk_token = json.loads(self._token_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise RuntimeError(
                    f"Cannot read Outlook token from {self._token_path}: {exc}"
                ) from exc
            if not isinstance(disk_token, dict) or not disk_token.get("access_token"):
                raise RuntimeError("Outlook token file is empty or malformed.")
            self._token_cache = disk_token

        token = self._token_cache

        # Refresh if within 120 s of expiry.
        expires_at_raw = str(token.get("expires_at", "")).strip()
        if expires_at_raw:
            try:
                expires_at = datetime.fromisoformat(expires_at_raw)
                if expires_at <= datetime.now(timezone.utc) + timedelta(seconds=120):
                    log.info("Outlook token near expiry — refreshing.")
                    token = self._refresh_token(token)
            except Exception as exc:
                log.warning("Could not parse/refresh Outlook token expiry: %s", exc)

        return token

    def _refresh_token(self, token: dict[str, Any]) -> dict[str, Any]:
        refresh_tok = str(token.get("refresh_token", "")).strip()
        if not refresh_tok:
            log.warning("Outlook token has no refresh_token; using stale access_token.")
            return token

        endpoint = _TOKEN_ENDPOINT_TMPL.format(authority=self._authority)
        payload = {
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_tok,
            "redirect_uri": self._redirect_uri,
            "scope": _OAUTH_SCOPES,
        }

        try:
            if _REQUESTS_AVAILABLE:
                resp = _requests.post(endpoint, data=payload, timeout=20)
                new_token: dict[str, Any] = resp.json()
            else:
                from urllib import error as _uerr, parse as _uparse, request as _ureq
                body = _uparse.urlencode(payload).encode("utf-8")
                req = _ureq.Request(
                    endpoint,
                    data=body,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    method="POST",
                )
                with _ureq.urlopen(req, timeout=20) as r:
                    new_token = json.loads(r.read().decode("utf-8"))
        except Exception as exc:
            log.error("Outlook token refresh failed: %s", exc)
            return token

        if not new_token.get("access_token"):
            log.error("Outlook token refresh returned no access_token: %s", new_token)
            return token

        # Preserve existing refresh_token if the server didn't rotate it.
        if not new_token.get("refresh_token"):
            new_token["refresh_token"] = refresh_tok

        # Compute and store expiry timestamp.
        expires_in = int(new_token.get("expires_in", 3600) or 3600)
        new_token["expires_at"] = (
            datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        ).isoformat()

        # Persist to disk.
        try:
            self._token_path.parent.mkdir(parents=True, exist_ok=True)
            self._token_path.write_text(
                json.dumps(new_token, indent=2) + "\n", encoding="utf-8"
            )
        except OSError as exc:
            log.warning("Could not persist refreshed Outlook token: %s", exc)

        self._token_cache = new_token
        log.info("Outlook access token refreshed — expires %s", new_token["expires_at"])
        return new_token

    def _get_access_token(self) -> str:
        return str(self._load_token()["access_token"])

    def _auth_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._get_access_token()}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------
    # Internal HTTP helpers
    # ------------------------------------------------------------------

    def _graph_get(self, path: str) -> dict[str, Any]:
        url = f"{GRAPH_BASE}{path}"
        if _REQUESTS_AVAILABLE:
            resp = _requests.get(url, headers=self._auth_headers(), timeout=30)
            if not resp.ok:
                raise RuntimeError(
                    f"Graph GET {path} failed ({resp.status_code}): {resp.text[:300]}"
                )
            return resp.json()  # type: ignore[return-value]
        else:
            from urllib import error as _uerr, request as _ureq
            req = _ureq.Request(url, headers=self._auth_headers(), method="GET")
            try:
                with _ureq.urlopen(req, timeout=30) as r:
                    return json.loads(r.read().decode("utf-8"))  # type: ignore[return-value]
            except _uerr.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")
                raise RuntimeError(f"Graph GET {path} failed ({exc.code}): {detail}") from exc

    def _graph_patch(self, path: str, body: dict[str, Any]) -> None:
        url = f"{GRAPH_BASE}{path}"
        if _REQUESTS_AVAILABLE:
            resp = _requests.patch(url, headers=self._auth_headers(), json=body, timeout=20)
            if not resp.ok:
                raise RuntimeError(
                    f"Graph PATCH {path} failed ({resp.status_code}): {resp.text[:300]}"
                )
        else:
            from urllib import error as _uerr, request as _ureq
            data = json.dumps(body).encode("utf-8")
            req = _ureq.Request(url, data=data, headers=self._auth_headers(), method="PATCH")
            try:
                with _ureq.urlopen(req, timeout=20):
                    pass
            except _uerr.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")
                raise RuntimeError(f"Graph PATCH {path} failed ({exc.code}): {detail}") from exc

    # ------------------------------------------------------------------
    # Email
    # ------------------------------------------------------------------

    def fetch_inbox(
        self,
        max_results: int = 50,
        unread_only: bool = False,
        since_date: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch messages from the signed-in user's inbox.

        Returns normalised dicts with keys:
        ``external_id, thread_id, subject, sender_email, sender_name,
        snippet, body_text, received_at, is_read, is_flagged, importance, labels``
        """
        select = (
            "id,conversationId,subject,from,bodyPreview,body,"
            "receivedDateTime,isRead,flag,importance,categories"
        )
        params = [
            ("$select", select),
            ("$orderby", "receivedDateTime DESC"),
            ("$top", str(max(1, int(max_results)))),
        ]
        filters = []
        if unread_only:
            filters.append("isRead eq false")
        if since_date:
            # since_date can be ISO 8601 or just a date string like "2026-05-18T00:00:00Z"
            # Graph API uses receivedDateTime ge 'YYYY-MM-DDTHH:MM:SSZ'
            try:
                from datetime import datetime, timezone
                dt = datetime.fromisoformat(since_date.replace("Z", "+00:00"))
                filters.append(f"receivedDateTime ge {dt.strftime('%Y-%m-%dT%H:%M:%SZ')}")
            except Exception:
                pass  # If date parsing fails, skip the filter
        if filters:
            params.append(("$filter", " and ".join(filters)))

        qs = "&".join(f"{k}={v}" for k, v in params)
        path = f"/me/mailFolders/Inbox/messages?{qs}"
        try:
            payload = self._graph_get(path)
        except Exception as exc:
            log.error("fetch_inbox failed: %s", exc)
            return []

        results: list[dict[str, Any]] = []
        for item in payload.get("value") or []:
            from_addr = (item.get("from") or {}).get("emailAddress") or {}
            flag_status = str((item.get("flag") or {}).get("flagStatus", "")).lower()
            results.append(
                {
                    "external_id": str(item.get("id", "")).strip(),
                    "thread_id": str(item.get("conversationId", "")).strip(),
                    "subject": str(item.get("subject", "")).strip() or "(No subject)",
                    "sender_email": str(from_addr.get("address", "")).strip(),
                    "sender_name": str(from_addr.get("name", "")).strip(),
                    "snippet": str(item.get("bodyPreview", "")).strip(),
                    "body_text": str(
                        (item.get("body") or {}).get("content", "")
                    ).strip(),
                    "received_at": str(item.get("receivedDateTime", "")).strip(),
                    "is_read": bool(item.get("isRead", False)),
                    "is_flagged": flag_status == "flagged",
                    "importance": str(item.get("importance", "normal")).strip(),
                    "labels": list(item.get("categories") or []),
                }
            )
        return results

    def get_unread_count(self) -> int:
        """Return the number of unread messages in the inbox."""
        path = "/me/mailFolders/Inbox/messages?$filter=isRead eq false&$select=id&$top=1000"
        try:
            payload = self._graph_get(path)
            return len(payload.get("value") or [])
        except Exception as exc:
            log.error("get_unread_count failed: %s", exc)
            return 0

    def mark_as_read(self, message_id: str) -> None:
        """Mark a single message as read."""
        if not message_id:
            return
        try:
            self._graph_patch(f"/me/messages/{message_id}", {"isRead": True})
            log.debug("Marked message %s as read.", message_id)
        except Exception as exc:
            log.error("mark_as_read(%s) failed: %s", message_id, exc)

    # ------------------------------------------------------------------
    # Calendar
    # ------------------------------------------------------------------

    def fetch_calendar_events(
        self,
        days_back: int = 1,
        days_forward: int = 14,
    ) -> list[dict[str, Any]]:
        """Fetch calendar events within a rolling window around today.

        Returns normalised dicts with keys:
        ``external_id, source, title, description, start_time, end_time,
        all_day, location, attendees, organizer, calendar_name``
        """
        now = datetime.now(timezone.utc)
        start_dt = now - timedelta(days=max(0, int(days_back)))
        end_dt = now + timedelta(days=max(0, int(days_forward)))

        select = (
            "id,subject,bodyPreview,start,end,isAllDay,"
            "location,attendees,organizer,calendar"
        )
        path = (
            f"/me/calendarView"
            f"?startDateTime={_dt_to_iso(start_dt)}"
            f"&endDateTime={_dt_to_iso(end_dt)}"
            f"&$select={select}"
            f"&$orderby=start/dateTime ASC"
            f"&$top=100"
        )
        try:
            payload = self._graph_get(path)
        except Exception as exc:
            log.error("fetch_calendar_events failed: %s", exc)
            return []

        return self._normalise_events(payload.get("value") or [])

    def fetch_todays_events(self) -> list[dict[str, Any]]:
        """Fetch calendar events for today only."""
        now = datetime.now(timezone.utc)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)

        select = (
            "id,subject,bodyPreview,start,end,isAllDay,"
            "location,attendees,organizer,calendar"
        )
        path = (
            f"/me/calendarView"
            f"?startDateTime={_dt_to_iso(start_of_day)}"
            f"&endDateTime={_dt_to_iso(end_of_day)}"
            f"&$select={select}"
            f"&$orderby=start/dateTime ASC"
            f"&$top=50"
        )
        try:
            payload = self._graph_get(path)
        except Exception as exc:
            log.error("fetch_todays_events failed: %s", exc)
            return []

        return self._normalise_events(payload.get("value") or [])

    def create_calendar_event(
        self,
        title: str,
        start: str,
        end: str | None = None,
        description: str = "",
        location: str = "",
    ) -> dict[str, Any]:
        """Create an event on the user's primary Outlook calendar.

        Args:
            title:       Event subject line.
            start:       ISO 8601 datetime, e.g. ``'2026-05-23T15:00:00'``.
            end:         ISO 8601 datetime.  Defaults to start + 1 hour.
            description: Optional body text.
            location:    Optional location string.

        Returns:
            Dict with ``{id, title, start, end, web_link}`` on success,
            or ``{error: str}`` on failure.
        """
        from datetime import datetime as _dt
        try:
            _load = _dt.fromisoformat(start)
        except Exception:
            return {"error": f"Cannot parse start datetime: {start!r}"}

        if end is None:
            end = (_load + timedelta(hours=1)).isoformat()

        event_body: dict[str, Any] = {
            "subject": title,
            "start": {"dateTime": start, "timeZone": "America/Chicago"},
            "end":   {"dateTime": end,   "timeZone": "America/Chicago"},
            "isReminderOn": True,
            "reminderMinutesBeforeStart": 15,
        }
        if description:
            event_body["body"] = {"contentType": "text", "content": description}
        if location:
            event_body["location"] = {"displayName": location}

        try:
            token = self._load_token()
            if not token.get("access_token"):
                return {"error": "Outlook token missing — please reconnect in Settings."}

            url = f"{GRAPH_BASE}/me/events"
            if _REQUESTS_AVAILABLE:
                resp = _requests.post(url, headers=self._auth_headers(), json=event_body, timeout=20)
                if not resp.ok:
                    return {"error": f"Graph POST /me/events failed ({resp.status_code}): {resp.text[:300]}"}
                result = resp.json()
            else:
                from urllib import error as _uerr, request as _ureq
                data = json.dumps(event_body).encode("utf-8")
                headers = {**self._auth_headers(), "Content-Type": "application/json"}
                req = _ureq.Request(url, data=data, headers=headers, method="POST")
                try:
                    with _ureq.urlopen(req, timeout=20) as r:
                        result = json.loads(r.read().decode("utf-8"))
                except _uerr.HTTPError as exc:
                    detail = exc.read().decode("utf-8", errors="replace")
                    return {"error": f"Graph POST /me/events failed ({exc.code}): {detail}"}

            log.info("OutlookBridge: created event '%s' (id=%s)", title, result.get("id", ""))
            return {
                "id":       result.get("id", ""),
                "title":    result.get("subject", title),
                "start":    (result.get("start") or {}).get("dateTime", start),
                "end":      (result.get("end")   or {}).get("dateTime", end),
                "web_link": result.get("webLink", ""),
            }
        except Exception as exc:
            log.error("OutlookBridge.create_calendar_event('%s'): %s", title, exc)
            return {"error": str(exc)}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalise_events(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for item in items:
            organizer_info = (item.get("organizer") or {}).get("emailAddress") or {}
            location_info = str(
                (item.get("location") or {}).get("displayName") or ""
            ).strip()
            attendees = [
                str((a.get("emailAddress") or {}).get("address", "")).strip()
                for a in (item.get("attendees") or [])
                if (a.get("emailAddress") or {}).get("address")
            ]
            calendar_name = str(
                (item.get("calendar") or {}).get("name", "")
            ).strip()
            results.append(
                {
                    "external_id": str(item.get("id", "")).strip(),
                    "source": "outlook",
                    "title": str(item.get("subject", "")).strip()
                    or "(Untitled event)",
                    "description": str(item.get("bodyPreview", "")).strip(),
                    "start_time": str(
                        (item.get("start") or {}).get("dateTime", "")
                    ).strip(),
                    "end_time": str(
                        (item.get("end") or {}).get("dateTime", "")
                    ).strip(),
                    "all_day": bool(item.get("isAllDay", False)),
                    "location": location_info,
                    "attendees": attendees,
                    "organizer": str(organizer_info.get("address", "")).strip(),
                    "calendar_name": calendar_name,
                }
            )
        return results


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_bridge: OutlookBridge | None = None


def get_outlook_bridge() -> OutlookBridge | None:
    """Return the initialised singleton, or ``None`` if not yet initialised."""
    return _bridge


def init_outlook_bridge(
    token_path: Path | str | None = None,
    client_id: str | None = None,
    client_secret: str | None = None,
    redirect_uri: str | None = None,
    authority: str | None = None,
) -> OutlookBridge:
    """Initialise (or replace) the module-level OutlookBridge singleton.

    All arguments default to environment variables when not supplied.

    ``token_path`` should point to the delegated OAuth token JSON written by
    :class:`~jarvis.microsoft_graph.MicrosoftGraphSupport` after the user
    authorises via the browser.  The default resolves from
    ``JARVIS_MICROSOFT_TOKEN_PATH`` (falling back to
    ``data/microsoft_graph/token.json``).
    """
    global _bridge  # noqa: PLW0603

    # Resolve token path.
    if token_path is None:
        raw_path = os.environ.get(
            "JARVIS_MICROSOFT_TOKEN_PATH",
            "data/microsoft_graph/token.json",
        )
        token_path = Path(raw_path)

    resolved_client_id = client_id or os.environ.get("JARVIS_MICROSOFT_CLIENT_ID", "")
    resolved_client_secret = client_secret or os.environ.get(
        "JARVIS_MICROSOFT_CLIENT_SECRET", ""
    )
    resolved_redirect_uri = redirect_uri or os.environ.get(
        "JARVIS_MICROSOFT_REDIRECT_URI", ""
    )
    resolved_authority = (
        authority or os.environ.get("JARVIS_MICROSOFT_AUTHORITY", "common")
    )

    _bridge = OutlookBridge(
        token_path=token_path,
        client_id=resolved_client_id,
        client_secret=resolved_client_secret,
        redirect_uri=resolved_redirect_uri,
        authority=resolved_authority,
    )
    log.info("OutlookBridge initialised (delegated token at %s)", token_path)
    return _bridge
