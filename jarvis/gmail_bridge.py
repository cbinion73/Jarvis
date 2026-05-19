"""JARVIS Gmail Bridge — reads Gmail inbox for home intelligence."""

from __future__ import annotations

import base64
import json
import logging
import re
from datetime import datetime, timezone
from email.utils import parseaddr
from pathlib import Path
from typing import Any

logger = logging.getLogger("jarvis.gmail_bridge")

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
    logger.warning("gmail_bridge: google-api-python-client not installed — Gmail will be unavailable")


# ---------------------------------------------------------------------------
# Body extraction helpers
# ---------------------------------------------------------------------------

def _decode_base64_safe(data: str) -> str:
    """URL-safe base64 decode used by Gmail API for message bodies."""
    try:
        padded = data + "=" * (4 - len(data) % 4)
        return base64.urlsafe_b64decode(padded).decode("utf-8", errors="replace")
    except Exception:
        return ""


def _extract_plain_text(payload: dict) -> str:
    """
    Recursively extract plain-text content from a Gmail message payload.
    Handles multipart/plain, multipart/alternative, and nested MIME parts.
    """
    mime_type = payload.get("mimeType", "")
    body_data = payload.get("body", {}).get("data", "")

    if mime_type == "text/plain" and body_data:
        return _decode_base64_safe(body_data)

    if mime_type in ("text/html",):
        # Only return HTML content as fallback if we find nothing else
        return ""

    parts = payload.get("parts", [])
    if not parts:
        return _decode_base64_safe(body_data) if body_data else ""

    # For multipart/alternative, prefer text/plain
    if mime_type == "multipart/alternative":
        for part in parts:
            if part.get("mimeType") == "text/plain":
                text = _extract_plain_text(part)
                if text:
                    return text
        # Fallback: take the first part
        for part in parts:
            text = _extract_plain_text(part)
            if text:
                return text
        return ""

    # For multipart/mixed and others, concatenate all text parts
    result_parts: list[str] = []
    for part in parts:
        text = _extract_plain_text(part)
        if text:
            result_parts.append(text)
    return "\n".join(result_parts)


def _parse_sender(from_header: str) -> tuple[str, str]:
    """Parse 'Name <email>' into (name, email). Returns ('', raw) on failure."""
    name, email = parseaddr(from_header)
    return (name.strip(), email.strip().lower())


def _header_value(headers: list[dict], name: str) -> str:
    """Case-insensitive header lookup from Gmail message headers list."""
    name_lower = name.lower()
    for h in headers:
        if h.get("name", "").lower() == name_lower:
            return str(h.get("value", ""))
    return ""


def _parse_importance(headers: list[dict]) -> str:
    """Derive importance from X-Priority or Importance headers."""
    priority = _header_value(headers, "X-Priority") or _header_value(headers, "Importance")
    if not priority:
        return "normal"
    priority = priority.strip().lower()
    if priority in ("1", "2", "high"):
        return "high"
    if priority in ("4", "5", "low"):
        return "low"
    return "normal"


def _epoch_ms_to_iso(epoch_ms: str | int | None) -> str:
    """Convert Gmail internalDate (epoch ms as string) to ISO UTC string."""
    if not epoch_ms:
        return ""
    try:
        ts = int(epoch_ms) / 1000.0
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    except (ValueError, OSError):
        return ""


# ---------------------------------------------------------------------------
# GmailBridge
# ---------------------------------------------------------------------------

class GmailBridge:
    """
    Reads Gmail inbox for JARVIS home intelligence.

    Uses stored OAuth credentials from the JARVIS Google bridge token files.
    All methods are synchronous and return empty results on failure rather
    than raising exceptions.
    """

    def __init__(self, credentials_path: str) -> None:
        self._credentials_path = Path(credentials_path)
        self._service = None

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
            logger.warning("gmail_bridge: credentials file not found: %s", self._credentials_path)
            return {}
        try:
            raw = self._credentials_path.read_text(encoding="utf-8")
            data = json.loads(raw)
            if not isinstance(data, dict):
                logger.warning("gmail_bridge: credentials file is not a JSON object")
                return {}
            return data
        except (OSError, json.JSONDecodeError) as exc:
            logger.error("gmail_bridge: failed to read credentials: %s", exc)
            return {}

    def _get_service(self):
        """
        Build (or return cached) Gmail API service using stored credentials.
        Refreshes the token if expired.
        Returns None if unavailable.
        """
        if self._service is not None:
            return self._service

        if not _GOOGLE_LIBS_AVAILABLE:
            logger.error("gmail_bridge: Google API libraries are not installed")
            return None

        cred_data = self._load_credentials()
        if not cred_data:
            return None

        try:
            scopes = cred_data.get("scopes", ["https://www.googleapis.com/auth/gmail.readonly"])
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
                logger.debug("gmail_bridge: refreshing expired token")
                credentials.refresh(GoogleRequest())
                # Persist the refreshed token
                self._persist_refreshed_token(credentials)

            service = _build_service("gmail", "v1", credentials=credentials, cache_discovery=False)
            self._service = service
            return service

        except Exception as exc:
            logger.error("gmail_bridge: failed to build Gmail service: %s", exc)
            return None

    def _persist_refreshed_token(self, credentials) -> None:
        """Write refreshed token back to credentials_path."""
        try:
            cred_data = self._load_credentials()
            cred_data["token"] = credentials.token
            if credentials.expiry:
                cred_data["expiry"] = credentials.expiry.isoformat()
            self._credentials_path.write_text(
                json.dumps(cred_data, indent=2) + "\n",
                encoding="utf-8",
            )
            logger.debug("gmail_bridge: persisted refreshed token to %s", self._credentials_path)
        except Exception as exc:
            logger.warning("gmail_bridge: failed to persist refreshed token: %s", exc)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fetch_inbox(
        self,
        max_results: int = 50,
        unread_only: bool = False,
        since_date: str | None = None,
    ) -> list[dict]:
        """
        Fetch emails from the Gmail inbox.

        Args:
            max_results: Maximum number of messages to return.
            unread_only: If True, only return unread messages.
            since_date: Optional date filter in 'YYYY/MM/DD' format (Gmail query syntax).

        Returns:
            List of dicts with keys:
              external_id, thread_id, subject, sender_email, sender_name,
              snippet, body_text, received_at, is_read, is_flagged,
              importance, labels
        """
        service = self._get_service()
        if service is None:
            return []

        try:
            query_parts: list[str] = ["in:inbox"]
            if unread_only:
                query_parts.append("is:unread")
            if since_date:
                query_parts.append(f"after:{since_date}")
            query = " ".join(query_parts)

            list_response = (
                service.users()
                .messages()
                .list(userId="me", q=query, maxResults=max_results)
                .execute()
            )

            message_refs = list_response.get("messages", [])
            if not message_refs:
                return []

            results: list[dict] = []
            for ref in message_refs:
                msg = self._fetch_message_detail(service, ref["id"])
                if msg:
                    results.append(msg)

            return results

        except Exception as exc:
            logger.error("gmail_bridge.fetch_inbox: %s", exc)
            return []

    def _fetch_message_detail(self, service, message_id: str) -> dict | None:
        """Fetch full message detail and parse into a normalized dict."""
        try:
            raw = (
                service.users()
                .messages()
                .get(userId="me", id=message_id, format="full")
                .execute()
            )

            payload = raw.get("payload", {})
            headers = payload.get("headers", [])
            label_ids = raw.get("labelIds", [])

            subject = _header_value(headers, "Subject") or "(No subject)"
            from_raw = _header_value(headers, "From")
            sender_name, sender_email = _parse_sender(from_raw)
            received_at = _epoch_ms_to_iso(raw.get("internalDate"))
            snippet = raw.get("snippet", "")
            is_read = "UNREAD" not in label_ids
            is_flagged = "STARRED" in label_ids
            importance = _parse_importance(headers)

            # Extract body text (may be slow for large emails but necessary)
            body_text = _extract_plain_text(payload)

            return {
                "external_id": raw.get("id", ""),
                "thread_id": raw.get("threadId", ""),
                "subject": subject,
                "sender_email": sender_email,
                "sender_name": sender_name,
                "snippet": snippet,
                "body_text": body_text,
                "received_at": received_at,
                "is_read": is_read,
                "is_flagged": is_flagged,
                "importance": importance,
                "labels": label_ids,
            }

        except Exception as exc:
            logger.warning("gmail_bridge: failed to fetch message %s: %s", message_id, exc)
            return None

    def fetch_email_body(self, message_id: str) -> str:
        """
        Fetch full body text for a single Gmail message by ID.

        Returns empty string on failure.
        """
        service = self._get_service()
        if service is None:
            return ""

        try:
            raw = (
                service.users()
                .messages()
                .get(userId="me", id=message_id, format="full")
                .execute()
            )
            payload = raw.get("payload", {})
            return _extract_plain_text(payload)

        except Exception as exc:
            logger.error("gmail_bridge.fetch_email_body(%s): %s", message_id, exc)
            return ""

    def mark_as_read(self, message_id: str) -> None:
        """
        Mark a Gmail message as read by removing the UNREAD label.
        Silently logs on failure.
        """
        service = self._get_service()
        if service is None:
            return

        try:
            service.users().messages().modify(
                userId="me",
                id=message_id,
                body={"removeLabelIds": ["UNREAD"]},
            ).execute()
            logger.debug("gmail_bridge: marked %s as read", message_id)

        except Exception as exc:
            logger.error("gmail_bridge.mark_as_read(%s): %s", message_id, exc)

    def get_unread_count(self) -> int:
        """
        Return the count of unread messages in the inbox.
        Returns 0 on failure.
        """
        service = self._get_service()
        if service is None:
            return 0

        try:
            response = (
                service.users()
                .messages()
                .list(userId="me", q="in:inbox is:unread", maxResults=1)
                .execute()
            )
            # resultSizeEstimate is the best approximation available without
            # paginating through all results
            return int(response.get("resultSizeEstimate", 0))

        except Exception as exc:
            logger.error("gmail_bridge.get_unread_count: %s", exc)
            return 0


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_bridge: GmailBridge | None = None


def get_gmail_bridge() -> GmailBridge | None:
    """Return the module-level GmailBridge singleton (None if not initialised)."""
    return _bridge


def init_gmail_bridge(credentials_path: str) -> GmailBridge:
    """
    Create and return the module-level GmailBridge singleton.

    Args:
        credentials_path: Absolute path to the OAuth token JSON file from the
                          JARVIS Google bridge (e.g. data/google/bridge/tokens/<id>.json).

    Returns:
        The initialised GmailBridge instance.
    """
    global _bridge
    _bridge = GmailBridge(credentials_path)
    logger.info("gmail_bridge: initialised with credentials at %s", credentials_path)
    return _bridge
