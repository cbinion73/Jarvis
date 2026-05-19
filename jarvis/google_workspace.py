from __future__ import annotations

import base64
import json
import os
import secrets
import shutil
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from email.utils import make_msgid, parseaddr
from pathlib import Path
from typing import Any

from .accounts import PersonalAccount
from .config import AppConfig

try:
    from google.auth.transport.requests import Request as GoogleRequest
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import Flow
    from googleapiclient.discovery import build
except ModuleNotFoundError:  # pragma: no cover - optional dependency path
    GoogleRequest = None  # type: ignore[assignment]
    Credentials = None  # type: ignore[assignment]
    Flow = None  # type: ignore[assignment]
    build = None  # type: ignore[assignment]


SCOPES = (
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
)


@dataclass(slots=True)
class GoogleWorkspaceStatus:
    credentials_file_present: bool
    libraries_ready: bool
    token_present: bool
    connected: bool
    gmail_ready: bool
    calendar_ready: bool
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "credentials_file_present": self.credentials_file_present,
            "libraries_ready": self.libraries_ready,
            "token_present": self.token_present,
            "connected": self.connected,
            "gmail_ready": self.gmail_ready,
            "calendar_ready": self.calendar_ready,
            "detail": self.detail,
        }


class GoogleWorkspaceSupport:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.pending_state_path = self.config.google_token_path.parent / "pending_oauth.json"
        self._pending_states: dict[str, dict[str, str]] = self._load_pending_states()

    def status(self, account: PersonalAccount | Any | None = None) -> GoogleWorkspaceStatus:
        self._import_bridge_bundle_internal(account_id=self._account_id_for(account))
        token_path = self._token_path_for(account)
        if not self.config.google_client_secret_path.exists():
            return GoogleWorkspaceStatus(
                credentials_file_present=False,
                libraries_ready=self._libraries_ready(),
                token_present=token_path.exists(),
                connected=False,
                gmail_ready=False,
                calendar_ready=False,
                detail="Google client secret is missing. Add config/google_client_secret.json first.",
            )
        if not self._libraries_ready():
            return GoogleWorkspaceStatus(
                credentials_file_present=True,
                libraries_ready=False,
                token_present=token_path.exists(),
                connected=False,
                gmail_ready=False,
                calendar_ready=False,
                detail="Google API libraries are not installed in the current runtime.",
            )
        credentials = self._load_credentials(account)
        if not credentials:
            return GoogleWorkspaceStatus(
                credentials_file_present=True,
                libraries_ready=True,
                token_present=token_path.exists(),
                connected=False,
                gmail_ready=False,
                calendar_ready=False,
                detail="Google account not connected yet." if account is None else "This Google account is not connected yet.",
            )
        if not getattr(credentials, "valid", False):
            return GoogleWorkspaceStatus(
                credentials_file_present=True,
                libraries_ready=True,
                token_present=token_path.exists(),
                connected=False,
                gmail_ready=False,
                calendar_ready=False,
                detail="Google token exists but is not currently valid.",
            )
        return GoogleWorkspaceStatus(
            credentials_file_present=True,
            libraries_ready=True,
            token_present=True,
            connected=True,
            gmail_ready=True,
            calendar_ready=True,
            detail="Google Gmail and Calendar are connected." if account is None else "This Google account is connected.",
        )

    def disconnect(self, account: PersonalAccount | None = None) -> dict[str, Any]:
        account_id = self._account_id_for(account)
        token_path = self._token_path_for(account)
        if token_path.exists():
            token_path.unlink()
        bridge_token_path = self._bridge_token_path_for_account_id(account_id)
        if bridge_token_path.exists():
            bridge_token_path.unlink()
        return {
            "ok": True,
            "message": "Google account disconnected. Local token removed.",
            "status": self.status(account).to_dict(),
        }

    def save_client_secret_json(self, raw_json: str) -> dict[str, Any]:
        text = raw_json.strip()
        if not text:
            return {
                "ok": False,
                "detail": "No Google OAuth client JSON was provided.",
            }
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            return {
                "ok": False,
                "detail": f"Google OAuth JSON could not be parsed: {exc.msg}.",
            }

        if not isinstance(payload, dict):
            return {
                "ok": False,
                "detail": "Google OAuth JSON must be an object.",
            }

        if "installed" not in payload and "web" not in payload:
            return {
                "ok": False,
                "detail": "Google OAuth JSON must contain either an 'installed' or 'web' client block.",
            }

        self.config.google_client_secret_path.parent.mkdir(parents=True, exist_ok=True)
        self.config.google_client_secret_path.write_text(
            json.dumps(payload, indent=2) + "\n",
            encoding="utf-8",
        )
        self._export_bridge_bundle_internal()
        return {
            "ok": True,
            "detail": f"Google OAuth client saved to {self.config.google_client_secret_path}.",
            "status": self.status().to_dict(),
        }

    def client_secret_summary(self) -> dict[str, Any]:
        self._import_bridge_bundle_internal()
        if not self.config.google_client_secret_path.exists():
            return {
                "present": False,
                "path": str(self.config.google_client_secret_path),
                "client_type": "",
                "client_id_tail": "",
            }
        try:
            payload = json.loads(self.config.google_client_secret_path.read_text(encoding="utf-8"))
        except Exception:
            return {
                "present": True,
                "path": str(self.config.google_client_secret_path),
                "client_type": "unreadable",
                "client_id_tail": "",
            }
        client_type = "installed" if "installed" in payload else ("web" if "web" in payload else "unknown")
        block = payload.get(client_type, {}) if isinstance(payload.get(client_type, {}), dict) else {}
        client_id = str(block.get("client_id", ""))
        return {
            "present": True,
            "path": str(self.config.google_client_secret_path),
            "client_type": client_type,
            "client_id_tail": client_id[-18:] if client_id else "",
        }

    def build_connect_url(self, account: PersonalAccount, base_url: str) -> dict[str, Any]:
        status = self.status(account)
        if not status.credentials_file_present:
            return {
                "ok": False,
                "detail": status.detail,
            }
        if not status.libraries_ready:
            return {
                "ok": False,
                "detail": status.detail,
            }
        flow = self._build_flow(base_url)
        state = secrets.token_urlsafe(24)
        authorization_url, returned_state = flow.authorization_url(
            access_type="offline",
            prompt="consent",
            login_hint=account.login_hint or None,
            state=state,
        )
        payload = {
            "account_id": account.account_id,
            "code_verifier": str(getattr(flow, "code_verifier", "") or ""),
        }
        self._pending_states[state] = payload
        self._pending_states[returned_state] = payload
        self._save_pending_states()
        return {
            "ok": True,
            "authorization_url": authorization_url,
            "state": returned_state,
        }

    def handle_callback(self, base_url: str, code: str, state: str) -> dict[str, Any]:
        if not code:
            return {"ok": False, "detail": "Missing Google authorization code."}
        pending = self._pending_states.get(state, {})
        account_id = pending.get("account_id", "")
        if not account_id:
            return {"ok": False, "detail": "Google callback state did not match the active session."}
        if not self._libraries_ready():
            return {"ok": False, "detail": "Google API libraries are unavailable."}
        try:
            flow = self._build_flow(base_url, state=state)
            code_verifier = pending.get("code_verifier", "")
            if code_verifier:
                flow.code_verifier = code_verifier
            try:
                flow.fetch_token(code=code)
            except Warning:
                # oauthlib raises Warning (not Exception) when returned scopes
                # differ from requested scopes (e.g. Google bundles in previously
                # granted scopes). The credentials are still valid — continue.
                pass
            credentials = flow.credentials
            self._save_credentials(credentials, account_id=account_id)
            self._clear_pending_payload(pending)
            return {
                "ok": True,
                "detail": "Google account connected successfully.",
                "status": self.status_for_account_id(account_id).to_dict(),
                "account_id": account_id,
            }
        except Exception as exc:  # pragma: no cover - remote OAuth path
            return {"ok": False, "detail": str(exc)}

    def summary(self, account: PersonalAccount | None = None, *, email_limit: int = 6, event_limit: int = 6) -> dict[str, Any]:
        status = self.status(account)
        summary: dict[str, Any] = {
            "status": status.to_dict(),
            "connect_path": "/google/connect",
            "disconnect_path": "/api/google/disconnect",
            "emails": [],
            "calendar_events": [],
            "profile_email": "",
            "counts": {
                "unread_emails": 0,
                "upcoming_events": 0,
            },
        }
        if not status.connected:
            return summary

        credentials = self._load_credentials(account)
        if not credentials:
            return summary

        try:
            gmail_service = build("gmail", "v1", credentials=credentials, cache_discovery=False)
            profile = gmail_service.users().getProfile(userId="me").execute()
            summary["profile_email"] = str(profile.get("emailAddress", "")).strip()
            unread_payload = (
                gmail_service.users()
                .messages()
                .list(userId="me", q="in:inbox is:unread", maxResults=email_limit)
                .execute()
            )
            message_refs = unread_payload.get("messages", [])
            emails: list[dict[str, Any]] = []
            for item in message_refs:
                metadata = (
                    gmail_service.users()
                    .messages()
                    .get(
                        userId="me",
                        id=item["id"],
                        format="metadata",
                        metadataHeaders=["From", "Subject", "Date"],
                    )
                    .execute()
                )
                headers = {
                    entry.get("name", "").lower(): entry.get("value", "")
                    for entry in metadata.get("payload", {}).get("headers", [])
                }
                emails.append(
                    {
                        "id": item["id"],
                        "from": headers.get("from", ""),
                        "subject": headers.get("subject", "(No subject)"),
                        "date": headers.get("date", ""),
                        "snippet": metadata.get("snippet", ""),
                    }
                )
            summary["emails"] = emails
            summary["counts"]["unread_emails"] = len(emails)
        except Exception as exc:  # pragma: no cover - remote API path
            summary["gmail_error"] = str(exc)

        try:
            calendar_service = build("calendar", "v3", credentials=credentials, cache_discovery=False)
            now = datetime.now(timezone.utc).isoformat()
            horizon = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
            calendar_payload = (
                calendar_service.events()
                .list(
                    calendarId="primary",
                    timeMin=now,
                    timeMax=horizon,
                    maxResults=event_limit,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            events: list[dict[str, Any]] = []
            for item in calendar_payload.get("items", []):
                start = item.get("start", {})
                end = item.get("end", {})
                events.append(
                    {
                        "id": item.get("id", ""),
                        "summary": item.get("summary", "(Untitled event)"),
                        "start": start.get("dateTime") or start.get("date") or "",
                        "end": end.get("dateTime") or end.get("date") or "",
                        "location": item.get("location", ""),
                        "html_link": item.get("htmlLink", ""),
                    }
                )
            summary["calendar_events"] = events
            summary["counts"]["upcoming_events"] = len(events)
        except Exception as exc:  # pragma: no cover - remote API path
            summary["calendar_error"] = str(exc)

        return summary

    def create_gmail_draft(
        self,
        account: PersonalAccount,
        *,
        to_value: str,
        subject: str,
        body: str,
        thread_id: str = "",
        in_reply_to: str = "",
        references: list[str] | None = None,
    ) -> dict[str, Any]:
        if not self._draft_write_enabled():
            return {
                "ok": False,
                "reason": "draft_write_disabled",
                "detail": "Gmail draft write is disabled. JARVIS is operating in read-only mailbox mode.",
                "account_id": account.account_id,
                "provider": "gmail",
                "read_only_mode": True,
            }
        status = self.status(account)
        if not status.connected:
            return {
                "ok": False,
                "reason": "account_unavailable",
                "detail": status.detail,
                "account_id": account.account_id,
                "provider": "gmail",
            }
        credentials = self._load_credentials(account)
        if not credentials:
            return {
                "ok": False,
                "reason": "account_unavailable",
                "detail": "Google account credentials are unavailable.",
                "account_id": account.account_id,
                "provider": "gmail",
            }
        missing_scopes = self._missing_scopes(credentials, ("https://www.googleapis.com/auth/gmail.compose",))
        if missing_scopes:
            return {
                "ok": False,
                "reason": "reauthorization_required",
                "detail": "Google account is connected for read-only access. Reconnect the mailbox to grant Gmail draft write access.",
                "account_id": account.account_id,
                "provider": "gmail",
                "reconnect_required": True,
                "missing_scopes": missing_scopes,
            }
        to_address = self._extract_email_address(to_value)
        if not to_address:
            return {
                "ok": False,
                "reason": "recipient_unavailable",
                "detail": "Could not determine a recipient email address for the Gmail draft.",
                "account_id": account.account_id,
                "provider": "gmail",
            }

        try:
            gmail_service = build("gmail", "v1", credentials=credentials, cache_discovery=False)
            message = EmailMessage()
            message["To"] = to_address
            message["Subject"] = subject.strip() or "Draft"
            message["Message-ID"] = make_msgid()
            if in_reply_to.strip():
                message["In-Reply-To"] = in_reply_to.strip()
            reference_headers = [item.strip() for item in (references or []) if str(item).strip()]
            if in_reply_to.strip() and in_reply_to.strip() not in reference_headers:
                reference_headers.append(in_reply_to.strip())
            if reference_headers:
                message["References"] = " ".join(reference_headers)
            message.set_content(body or "")

            encoded = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")
            payload: dict[str, Any] = {"message": {"raw": encoded}}
            if thread_id.strip():
                payload["message"]["threadId"] = thread_id.strip()
            created = gmail_service.users().drafts().create(userId="me", body=payload).execute()
            message_payload = created.get("message", {}) if isinstance(created, dict) else {}
            return {
                "ok": True,
                "provider": "gmail",
                "account_id": account.account_id,
                "draft_id": str(created.get("id", "")).strip(),
                "message_id": str(message_payload.get("id", "")).strip(),
                "thread_id": str(message_payload.get("threadId", "")).strip() or thread_id.strip(),
                "recipient": to_address,
            }
        except Exception as exc:  # pragma: no cover - remote API path
            return {
                "ok": False,
                "reason": "gmail_write_failed",
                "detail": str(exc),
                "account_id": account.account_id,
                "provider": "gmail",
            }

    def _libraries_ready(self) -> bool:
        return all((GoogleRequest, Credentials, Flow, build))

    def _build_flow(self, base_url: str, *, state: str | None = None):
        flow = Flow.from_client_secrets_file(
            str(self.config.google_client_secret_path),
            scopes=self._oauth_scopes(),
            state=state,
        )
        flow.redirect_uri = f"{base_url.rstrip('/')}/google/callback"
        return flow

    def status_for_account_id(self, account_id: str) -> GoogleWorkspaceStatus:
        class _Account:
            def __init__(self, account_id: str) -> None:
                self.account_id = account_id

        return self.status(_Account(account_id))  # type: ignore[arg-type]

    def bridge_status(self) -> dict[str, Any]:
        self._import_bridge_bundle_internal()
        bridge_dir = self._bridge_dir()
        manifest = self._read_bridge_manifest()
        token_dir = self._bridge_tokens_dir()
        token_files = sorted(path.name for path in token_dir.glob("*.json"))
        default_account_id = manifest.get("default_account_id", self._default_account_id())
        return {
            "bridge_dir": str(bridge_dir.resolve()),
            "bridge_configured": True,
            "client_secret_present": self._bridge_client_secret_path().exists(),
            "local_client_secret_present": self.config.google_client_secret_path.exists(),
            "bridge_token_files": token_files,
            "local_token_files": sorted(path.name for path in self._local_token_dir().glob("*.json") if path.name != "pending_oauth.json"),
            "default_account_id": default_account_id,
            "connected_account_ids": manifest.get("connected_account_ids", self._connected_account_ids()),
            "last_exported_at": manifest.get("exported_at", ""),
            "default_account_status": self.status_for_account_id(default_account_id).to_dict() if default_account_id else self.status().to_dict(),
        }

    def export_bridge_bundle(self) -> dict[str, Any]:
        exported = self._export_bridge_bundle_internal()
        status = self.bridge_status()
        status.update(
            {
                "ok": True,
                "exported_files": exported["exported_files"],
                "detail": f"Exported Google bridge bundle to {status['bridge_dir']}.",
            }
        )
        return status

    def import_bridge_bundle(self, account_id: str = "") -> dict[str, Any]:
        imported = self._import_bridge_bundle_internal(account_id=account_id or None)
        status = self.bridge_status()
        status.update(
            {
                "ok": True,
                "imported_files": imported["imported_files"],
                "detail": "Imported Google bridge bundle into JARVIS local credentials.",
            }
        )
        return status

    def _load_credentials(self, account: PersonalAccount | None = None):
        account_id = self._account_id_for(account)
        self._import_bridge_bundle_internal(account_id=account_id)
        if not self._libraries_ready():
            return None
        token_path = self._token_path_for(account)
        if not token_path.exists():
            return None
        try:
            credentials = Credentials.from_authorized_user_file(
                str(token_path),
                scopes=self._oauth_scopes(),
            )
        except Exception:
            return None
        if getattr(credentials, "expired", False) and getattr(credentials, "refresh_token", None):
            try:
                credentials.refresh(GoogleRequest())
                self._save_credentials(credentials, account_id=account_id)
            except Exception:
                return credentials
        return credentials

    def _save_credentials(self, credentials, *, account_id: str) -> None:
        token_path = self._token_path_for_account_id(account_id)
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(credentials.to_json(), encoding="utf-8")
        self._export_bridge_bundle_internal(account_id=account_id)

    def _oauth_scopes(self) -> list[str]:
        scopes = list(SCOPES)
        if self._draft_write_enabled():
            scopes.insert(0, "https://www.googleapis.com/auth/gmail.compose")
        return scopes

    def _draft_write_enabled(self) -> bool:
        value = os.getenv("JARVIS_GMAIL_DRAFT_WRITE_ENABLED", "").strip().lower()
        return value in {"1", "true", "yes", "on"}

    def _load_pending_states(self) -> dict[str, dict[str, str]]:
        if not self.pending_state_path.exists():
            return {}
        try:
            payload = json.loads(self.pending_state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        if not isinstance(payload, dict):
            return {}
        loaded: dict[str, dict[str, str]] = {}
        for key, value in payload.items():
            if not isinstance(key, str) or not isinstance(value, dict):
                continue
            loaded[key] = {
                "account_id": str(value.get("account_id", "")),
                "code_verifier": str(value.get("code_verifier", "")),
            }
        return loaded

    def _save_pending_states(self) -> None:
        self.pending_state_path.parent.mkdir(parents=True, exist_ok=True)
        self.pending_state_path.write_text(
            json.dumps(self._pending_states, indent=2) + "\n",
            encoding="utf-8",
        )

    def _clear_pending_payload(self, payload: dict[str, str]) -> None:
        keys_to_remove = [key for key, value in self._pending_states.items() if value == payload]
        for key in keys_to_remove:
            self._pending_states.pop(key, None)
        self._save_pending_states()

    def _token_path_for(self, account: PersonalAccount | None = None) -> Path:
        if account is None:
            return self.config.google_token_path
        return self._token_path_for_account_id(self._account_id_for(account))

    def _token_path_for_account_id(self, account_id: str) -> Path:
        base_dir = self.config.google_token_path.parent
        return base_dir / f"{account_id}.json"

    def _bridge_dir(self) -> Path:
        configured = os.getenv("GOOGLE_CREDENTIAL_BRIDGE_DIR", "").strip()
        if configured:
            return Path(configured).expanduser()
        return self.config.google_token_path.parent / "bridge"

    def _bridge_client_secret_path(self) -> Path:
        return self._bridge_dir() / "client_secret.json"

    def _bridge_tokens_dir(self) -> Path:
        return self._bridge_dir() / "tokens"

    def _bridge_manifest_path(self) -> Path:
        return self._bridge_dir() / "manifest.json"

    def _bridge_token_path_for_account_id(self, account_id: str) -> Path:
        return self._bridge_tokens_dir() / f"{account_id}.json"

    def _local_token_dir(self) -> Path:
        return self.config.google_token_path.parent

    def _connected_account_ids(self) -> list[str]:
        ids = sorted(
            path.stem
            for path in self._local_token_dir().glob("*.json")
            if path.name != "pending_oauth.json"
        )
        return ids

    def _default_account_id(self) -> str:
        ids = self._connected_account_ids()
        if "default" in ids:
            return "default"
        return ids[0] if ids else "default"

    def _read_bridge_manifest(self) -> dict[str, Any]:
        path = self._bridge_manifest_path()
        if not path.exists():
            return {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return payload if isinstance(payload, dict) else {}

    def _export_bridge_bundle_internal(self, account_id: str | None = None) -> dict[str, Any]:
        bridge_dir = self._bridge_dir()
        tokens_dir = self._bridge_tokens_dir()
        bridge_dir.mkdir(parents=True, exist_ok=True)
        tokens_dir.mkdir(parents=True, exist_ok=True)
        exported_files: list[str] = []

        if self.config.google_client_secret_path.exists():
            target = self._bridge_client_secret_path()
            shutil.copy2(self.config.google_client_secret_path, target)
            exported_files.append(str(target))

        token_paths = (
            [self._token_path_for_account_id(account_id)]
            if account_id
            else [
                path
                for path in self._local_token_dir().glob("*.json")
                if path.name != "pending_oauth.json"
            ]
        )
        for source in token_paths:
            if not source.exists():
                continue
            target = self._bridge_token_path_for_account_id(source.stem)
            shutil.copy2(source, target)
            exported_files.append(str(target))

        manifest = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "bridge_dir": str(bridge_dir.resolve()),
            "client_secret_path": str(self._bridge_client_secret_path().resolve()),
            "tokens_dir": str(tokens_dir.resolve()),
            "local_client_secret_path": str(self.config.google_client_secret_path.resolve()),
            "local_token_dir": str(self._local_token_dir().resolve()),
            "token_files": sorted(path.name for path in tokens_dir.glob("*.json")),
            "connected_account_ids": self._connected_account_ids(),
            "default_account_id": self._default_account_id(),
        }
        self._bridge_manifest_path().write_text(
            json.dumps(manifest, indent=2) + "\n",
            encoding="utf-8",
        )
        exported_files.append(str(self._bridge_manifest_path()))
        return {"exported_files": exported_files}

    def _import_bridge_bundle_internal(self, account_id: str | None = None) -> dict[str, Any]:
        imported_files: list[str] = []
        bridge_dir = self._bridge_dir()
        if not bridge_dir.exists():
            return {"imported_files": imported_files}

        client_secret = self._bridge_client_secret_path()
        if client_secret.exists() and self._copy_if_newer(client_secret, self.config.google_client_secret_path):
            imported_files.append(str(self.config.google_client_secret_path))

        bridge_tokens = (
            [self._bridge_token_path_for_account_id(account_id)]
            if account_id
            else list(self._bridge_tokens_dir().glob("*.json"))
        )
        for source in bridge_tokens:
            if not source.exists():
                continue
            target = self._token_path_for_account_id(source.stem)
            if self._copy_if_newer(source, target):
                imported_files.append(str(target))
        return {"imported_files": imported_files}

    @staticmethod
    def _copy_if_newer(source: Path, target: Path) -> bool:
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            shutil.copy2(source, target)
            return True
        try:
            source_stat = source.stat()
            target_stat = target.stat()
        except OSError:
            shutil.copy2(source, target)
            return True
        if source_stat.st_mtime > target_stat.st_mtime:
            shutil.copy2(source, target)
            return True
        return False

    @staticmethod
    def _account_id_for(account: PersonalAccount | Any | None) -> str:
        if account is None:
            return "default"
        return str(getattr(account, "account_id", "default"))

    @staticmethod
    def _extract_email_address(value: str) -> str:
        _, address = parseaddr(str(value or "").strip())
        return address.strip().lower()

    @staticmethod
    def _missing_scopes(credentials, required_scopes: tuple[str, ...]) -> list[str]:
        granted = {str(scope).strip() for scope in list(getattr(credentials, "scopes", []) or []) if str(scope).strip()}
        return [scope for scope in required_scopes if scope not in granted]
