from __future__ import annotations

import json
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib import error, parse, request

from .accounts import PersonalAccount
from .config import AppConfig
from .persistence import append_jsonl, atomic_write_json


GRAPH_BASE = "https://graph.microsoft.com/v1.0"


@dataclass(slots=True)
class MicrosoftGraphStatus:
    app_configured: bool
    token_present: bool
    connected: bool
    mail_ready: bool
    calendar_ready: bool
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "app_configured": self.app_configured,
            "token_present": self.token_present,
            "connected": self.connected,
            "mail_ready": self.mail_ready,
            "calendar_ready": self.calendar_ready,
            "detail": self.detail,
        }


class MicrosoftGraphSupport:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.pending_state_path = self.config.microsoft_token_path.parent / "pending_oauth.json"
        self._pending_states: dict[str, dict[str, str]] = self._load_pending_states()

    def status(self, account: PersonalAccount | None = None) -> MicrosoftGraphStatus:
        token_path = self._token_path_for(account)
        if not self._app_configured():
            return MicrosoftGraphStatus(
                app_configured=False,
                token_present=token_path.exists(),
                connected=False,
                mail_ready=False,
                calendar_ready=False,
                detail="Microsoft Graph is not configured yet. Add the JARVIS_MICROSOFT_* values to .env first.",
            )
        token = self._load_token(account)
        if not token:
            return MicrosoftGraphStatus(
                app_configured=True,
                token_present=token_path.exists(),
                connected=False,
                mail_ready=False,
                calendar_ready=False,
                detail="Microsoft account not connected yet." if account is None else "This Microsoft account is not connected yet.",
            )
        return MicrosoftGraphStatus(
            app_configured=True,
            token_present=True,
            connected=True,
            mail_ready=True,
            calendar_ready=True,
            detail="Microsoft Outlook Mail and Calendar are connected." if account is None else "This Microsoft account is connected.",
        )

    def config_summary(self) -> dict[str, Any]:
        client_id = self.config.microsoft_client_id
        tenant_id = self.config.microsoft_tenant_id
        return {
            "configured": self._app_configured(),
            "client_id_tail": client_id[-12:] if client_id else "",
            "tenant_id_tail": tenant_id[-12:] if tenant_id else "",
            "authority": self.config.microsoft_authority,
            "redirect_uri": self.config.microsoft_redirect_uri,
            "token_path": str(self.config.microsoft_token_path),
        }

    def build_connect_url(self, account: PersonalAccount, _base_url: str) -> dict[str, Any]:
        status = self.status(account)
        if not status.app_configured:
            return {"ok": False, "detail": status.detail}
        state = secrets.token_urlsafe(24)
        self._pending_states[state] = {"account_id": account.account_id}
        self._save_pending_states()
        params = {
            "client_id": self.config.microsoft_client_id,
            "response_type": "code",
            "redirect_uri": self.config.microsoft_redirect_uri,
            "response_mode": "query",
            "scope": " ".join(self._oauth_scopes()),
            "state": state,
        }
        if account.login_hint:
            params["login_hint"] = account.login_hint
        authorization_url = f"{self._authority_base()}/authorize?{parse.urlencode(params)}"
        return {
            "ok": True,
            "authorization_url": authorization_url,
            "state": state,
        }

    def handle_callback(self, code: str, state: str) -> dict[str, Any]:
        if not code:
            return {"ok": False, "detail": "Missing Microsoft authorization code."}
        pending = self._pending_states.get(state, {})
        account_id = pending.get("account_id", "")
        if not account_id:
            return {"ok": False, "detail": "Microsoft callback state did not match the active session."}
        try:
            token_payload = self._token_request(
                {
                    "client_id": self.config.microsoft_client_id,
                    "client_secret": self.config.microsoft_client_secret,
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": self.config.microsoft_redirect_uri,
                    "scope": " ".join(self._oauth_scopes()),
                }
            )
            self._save_token(token_payload, account_id=account_id)
            self._clear_pending_state(state)
            return {
                "ok": True,
                "detail": "Microsoft account connected successfully.",
                "status": self.status_for_account_id(account_id).to_dict(),
                "account_id": account_id,
            }
        except Exception as exc:
            return {"ok": False, "detail": str(exc)}

    def disconnect(self, account: PersonalAccount | None = None) -> dict[str, Any]:
        token_path = self._token_path_for(account)
        if token_path.exists():
            token_path.unlink()
        return {
            "ok": True,
            "message": "Microsoft account disconnected. Local token removed.",
            "status": self.status(account).to_dict(),
        }

    def summary(self, account: PersonalAccount | None = None, *, email_limit: int = 6, event_limit: int = 6) -> dict[str, Any]:
        status = self.status(account)
        summary: dict[str, Any] = {
            "status": status.to_dict(),
            "connect_path": f"/accounts/{self._account_id_for(account)}/connect",
            "disconnect_path": f"/api/accounts/{self._account_id_for(account)}/disconnect",
            "emails": [],
            "calendar_events": [],
            "profile_email": "",
            "counts": {
                "unread_emails": 0,
                "upcoming_events": 0,
            },
        }
        token = self._load_token(account)
        if not token:
            return summary

        try:
            profile = self._graph_get(token["access_token"], "/me?$select=mail,userPrincipalName,displayName")
            profile_email = str(profile.get("mail") or profile.get("userPrincipalName") or "").strip()
            summary["profile_email"] = profile_email
        except Exception as exc:
            summary["profile_error"] = str(exc)

        try:
            mail_params = parse.urlencode(
                {
                    "$select": "id,subject,from,receivedDateTime,bodyPreview,conversationId,internetMessageId,isRead",
                    "$filter": "isRead eq false",
                    "$orderby": "receivedDateTime DESC",
                    "$top": max(1, int(email_limit)),
                }
            )
            mail_payload = self._graph_get(
                token["access_token"],
                f"/me/mailFolders/Inbox/messages?{mail_params}",
            )
            emails: list[dict[str, Any]] = []
            for item in list(mail_payload.get("value") or []):
                sender = (((item.get("from") or {}).get("emailAddress") or {}).get("address") or "").strip()
                emails.append(
                    {
                        "id": str(item.get("id", "")).strip(),
                        "from": sender,
                        "subject": str(item.get("subject", "")).strip() or "(No subject)",
                        "date": str(item.get("receivedDateTime", "")).strip(),
                        "snippet": str(item.get("bodyPreview", "")).strip(),
                        "thread_id": str(item.get("conversationId", "")).strip(),
                        "internet_message_id": str(item.get("internetMessageId", "")).strip(),
                    }
                )
            summary["emails"] = emails
            summary["counts"]["unread_emails"] = len(emails)
        except Exception as exc:
            summary["mail_error"] = str(exc)

        try:
            now = datetime.now(timezone.utc)
            horizon = now + timedelta(days=30)
            params = parse.urlencode(
                {
                    "startDateTime": now.isoformat(),
                    "endDateTime": horizon.isoformat(),
                    "$top": max(1, int(event_limit)),
                    "$select": "id,subject,start,end,location,webLink",
                }
            )
            calendar_payload = self._graph_get(token["access_token"], f"/me/calendarView?{params}")
            events: list[dict[str, Any]] = []
            for item in list(calendar_payload.get("value") or []):
                events.append(
                    {
                        "id": str(item.get("id", "")).strip(),
                        "summary": str(item.get("subject", "")).strip() or "(Untitled event)",
                        "start": str((item.get("start") or {}).get("dateTime", "")).strip(),
                        "end": str((item.get("end") or {}).get("dateTime", "")).strip(),
                        "location": str(((item.get("location") or {}).get("displayName") or "")).strip(),
                        "html_link": str(item.get("webLink", "")).strip(),
                    }
                )
            summary["calendar_events"] = events
            summary["counts"]["upcoming_events"] = len(events)
        except Exception as exc:
            summary["calendar_error"] = str(exc)

        return summary

    def status_for_account_id(self, account_id: str) -> MicrosoftGraphStatus:
        class _Account:
            def __init__(self, account_id: str) -> None:
                self.account_id = account_id

        return self.status(_Account(account_id))  # type: ignore[arg-type]

    def _app_configured(self) -> bool:
        return all(
            (
                self.config.microsoft_client_id,
                self.config.microsoft_tenant_id,
                self.config.microsoft_client_secret,
                self.config.microsoft_redirect_uri,
            )
        )

    def _oauth_scopes(self) -> list[str]:
        return [
            "openid",
            "profile",
            "offline_access",
            "User.Read",
            "Mail.Read",
            "Calendars.Read",
        ]

    def _authority_base(self) -> str:
        tenant = self.config.microsoft_authority or "common"
        return f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0"

    def _log_path_for(self, path: Path) -> Path:
        return path.with_name(f"{path.stem}_log.jsonl")

    def _state_log_path_for(self, path: Path) -> Path:
        return path.with_name(f"{path.stem}_state_log.jsonl")

    def _load_dict_snapshot(self, path: Path) -> dict[str, Any] | None:
        if not path.exists():
            payload = self._load_dict_from_state_log(path)
            if payload is not None:
                return payload
            return self._load_dict_from_log(path)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload = self._load_dict_from_state_log(path)
            if payload is not None:
                return payload
            return self._load_dict_from_log(path)
        if isinstance(payload, dict):
            return payload
        payload = self._load_dict_from_state_log(path)
        if payload is not None:
            return payload
        return self._load_dict_from_log(path)

    def _load_dict_from_log(self, path: Path) -> dict[str, Any] | None:
        log_path = self._log_path_for(path)
        if not log_path.exists():
            return None
        latest: dict[str, Any] | None = None
        try:
            with log_path.open(encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    payload = json.loads(line)
                    record = payload.get("record")
                    if isinstance(record, dict):
                        latest = record
        except (OSError, json.JSONDecodeError):
            return None
        return latest

    def _load_dict_from_state_log(self, path: Path) -> dict[str, Any] | None:
        log_path = self._state_log_path_for(path)
        if not log_path.exists():
            return None
        latest: dict[str, Any] | None = None
        try:
            with log_path.open(encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    payload = json.loads(line)
                    record = payload.get("record")
                    if isinstance(record, dict):
                        latest = record
        except (OSError, json.JSONDecodeError):
            return None
        return latest

    def _save_dict_snapshot(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        append_jsonl(
            self._log_path_for(path),
            {
                "saved_at": datetime.now(timezone.utc).isoformat(),
                "record": payload,
            },
        )
        append_jsonl(
            self._state_log_path_for(path),
            {
                "saved_at": datetime.now(timezone.utc).isoformat(),
                "record": payload,
            },
        )
        atomic_write_json(path, payload)

    def _load_pending_states(self) -> dict[str, dict[str, str]]:
        payload = self._load_dict_snapshot(self.pending_state_path)
        if payload is None:
            return {}
        if not isinstance(payload, dict):
            return {}
        loaded: dict[str, dict[str, str]] = {}
        for key, value in payload.items():
            if isinstance(key, str) and isinstance(value, dict):
                loaded[key] = {"account_id": str(value.get("account_id", "")).strip()}
        return loaded

    def _save_pending_states(self) -> None:
        self._save_dict_snapshot(self.pending_state_path, self._pending_states)

    def _clear_pending_state(self, state: str) -> None:
        self._pending_states.pop(state, None)
        self._save_pending_states()

    def _token_path_for(self, account: PersonalAccount | None = None) -> Path:
        if account is None:
            return self.config.microsoft_token_path
        return self._token_path_for_account_id(self._account_id_for(account))

    def _token_path_for_account_id(self, account_id: str) -> Path:
        return self.config.microsoft_token_path.parent / f"{account_id}.json"

    def _account_id_for(self, account: PersonalAccount | None) -> str:
        if account is None:
            return "default"
        return str(getattr(account, "account_id", "")).strip() or "default"

    def _load_token(self, account: PersonalAccount | None = None) -> dict[str, Any] | None:
        path = self._token_path_for(account)
        token = self._load_dict_snapshot(path)
        if token is None:
            return None
        if not isinstance(token, dict):
            return None
        expires_at = str(token.get("expires_at", "")).strip()
        if expires_at:
            try:
                if datetime.fromisoformat(expires_at) <= datetime.now(timezone.utc) + timedelta(seconds=60):
                    refreshed = self._refresh_token(token, account_id=self._account_id_for(account))
                    if refreshed:
                        token = refreshed
            except Exception:
                pass
        access_token = str(token.get("access_token", "")).strip()
        if not access_token:
            return None
        return token

    def _refresh_token(self, token: dict[str, Any], *, account_id: str) -> dict[str, Any] | None:
        refresh_token = str(token.get("refresh_token", "")).strip()
        if not refresh_token:
            return token
        payload = self._token_request(
            {
                "client_id": self.config.microsoft_client_id,
                "client_secret": self.config.microsoft_client_secret,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "redirect_uri": self.config.microsoft_redirect_uri,
                "scope": " ".join(self._oauth_scopes()),
            }
        )
        if not payload.get("refresh_token"):
            payload["refresh_token"] = refresh_token
        self._save_token(payload, account_id=account_id)
        return payload

    def _save_token(self, token: dict[str, Any], *, account_id: str) -> None:
        expires_in = int(token.get("expires_in", 0) or 0)
        if expires_in > 0:
            token["expires_at"] = (datetime.now(timezone.utc) + timedelta(seconds=expires_in)).isoformat()
        path = self._token_path_for_account_id(account_id)
        self._save_dict_snapshot(path, token)

    def _token_request(self, payload: dict[str, str]) -> dict[str, Any]:
        body = parse.urlencode(payload).encode("utf-8")
        req = request.Request(
            f"{self._authority_base()}/token",
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=20) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Microsoft token exchange failed: {detail}") from exc

    def create_todo_task(
        self,
        title: str,
        *,
        due_date: str | None = None,
        reminder_date: str | None = None,
        body: str = "",
        account: PersonalAccount | None = None,
    ) -> dict[str, Any]:
        """Create a Microsoft To-Do task (shows up in Outlook Tasks + To-Do app).

        Args:
            title: Task title / reminder text.
            due_date: ISO date string e.g. '2026-05-20' — converted to UTC midnight.
            reminder_date: ISO datetime string for the reminder alert (optional).
            body: Optional longer description.
            account: PersonalAccount to use (defaults to configured account).

        Returns:
            The created task as a dict with at minimum {'id', 'title', 'status'}.
        """
        token = self._load_token(account)
        if not token:
            raise RuntimeError("No Microsoft token available — please reconnect in Settings.")

        task: dict[str, Any] = {
            "title": title,
            "status": "notStarted",
            "importance": "normal",
        }
        if body:
            task["body"] = {"content": body, "contentType": "text"}
        if due_date:
            # Graph expects dateTime in UTC
            task["dueDateTime"] = {"dateTime": f"{due_date}T00:00:00", "timeZone": "UTC"}
        if reminder_date:
            task["isReminderOn"] = True
            task["reminderDateTime"] = {"dateTime": reminder_date, "timeZone": "UTC"}

        # Tasks go into the default "Tasks" list — list ID "AQMkADA" magic or just use /tasks shortcut
        result = self._graph_post(token["access_token"], "/me/todo/lists/tasks/tasks", task)
        return {
            "id": result.get("id", ""),
            "title": result.get("title", title),
            "status": result.get("status", "notStarted"),
            "due": result.get("dueDateTime", {}).get("dateTime", ""),
            "created": result.get("createdDateTime", ""),
            "web_link": result.get("webLink", ""),
        }

    def create_calendar_event(
        self,
        title: str,
        *,
        start: str,
        end: str | None = None,
        body: str = "",
        is_reminder: bool = False,
        account: PersonalAccount | None = None,
    ) -> dict[str, Any]:
        """Create an Outlook calendar event.

        Args:
            title: Event subject.
            start: ISO datetime string e.g. '2026-05-20T09:00:00'.
            end: ISO datetime string — defaults to start + 15 minutes.
            body: Optional event body text.
            is_reminder: If True, sets a 0-minute reminder pop-up.
            account: PersonalAccount to use.

        Returns:
            Dict with {'id', 'title', 'start', 'end', 'web_link'}.
        """
        token = self._load_token(account)
        if not token:
            raise RuntimeError("No Microsoft token available — please reconnect in Settings.")

        if end is None:
            # Default 15-minute block
            from datetime import datetime as _dt
            _start = _dt.fromisoformat(start)
            end = (_start + timedelta(minutes=15)).isoformat()

        event: dict[str, Any] = {
            "subject": title,
            "start": {"dateTime": start, "timeZone": "America/Chicago"},
            "end": {"dateTime": end, "timeZone": "America/Chicago"},
            "isReminderOn": True,
            "reminderMinutesBeforeStart": 0 if is_reminder else 15,
        }
        if body:
            event["body"] = {"contentType": "text", "content": body}

        result = self._graph_post(token["access_token"], "/me/events", event)
        return {
            "id": result.get("id", ""),
            "title": result.get("subject", title),
            "start": result.get("start", {}).get("dateTime", start),
            "end": result.get("end", {}).get("dateTime", end),
            "web_link": result.get("webLink", ""),
        }

    def _graph_get(self, access_token: str, path: str) -> dict[str, Any]:
        req = request.Request(
            f"{GRAPH_BASE}{path}",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
            method="GET",
        )
        try:
            with request.urlopen(req, timeout=20) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Microsoft Graph request failed: {detail}") from exc

    def _graph_post(self, access_token: str, path: str, body: dict[str, Any]) -> dict[str, Any]:
        data = json.dumps(body).encode("utf-8")
        req = request.Request(
            f"{GRAPH_BASE}{path}",
            data=data,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=20) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Microsoft Graph POST failed: {detail}") from exc
