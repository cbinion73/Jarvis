"""
JARVIS Omron Partner API Integration — OAuth 2.0 + Blood Pressure / Weight sync.

Real API docs: https://omronhealthcare-ohi.atlassian.net/wiki/spaces/API/pages/2480308225/

Setup:
  1. Register at https://www.omronhealthcare.com/partners → get client_id + client_secret
  2. Add OMRON_CLIENT_ID and OMRON_CLIENT_SECRET to .env
     (Optional: OMRON_STAGING=1 to use staging environment during development)
  3. JARVIS needs a public notification URL — add OMRON_NOTIFY_BASE to .env if different
     from your JARVIS base URL (e.g. ngrok tunnel). During registration provide:
       Redirect URI:     http(s)://<your-host>/api/health/omron/callback
       Notification URI: http(s)://<your-host>/api/health/omron/notification
  4. Visit /api/health/omron/connect in JARVIS to start the OAuth flow

OAuth flow:
  GET  /api/health/omron/connect        → redirect to Omron auth page
  GET  /api/health/omron/callback       → exchange code for tokens, save, redirect home
  POST /api/health/omron/notification   → Omron pushes new-data events here
  POST /api/health/omron/sync           → manually pull latest measurements
  GET  /api/health/omron/status         → connection status + last sync info
"""
from __future__ import annotations

import base64
import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import httpx

from .persistence import append_jsonl, atomic_write_json

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Environment-aware endpoints
# ---------------------------------------------------------------------------

def _staging() -> bool:
    return os.getenv("OMRON_STAGING", "").lower() in ("1", "true", "yes")

def _auth_hostname() -> str:
    return "stg-oauth-website.ohiomron.com" if _staging() else "prd-oauth-website.ohiomron.com"

def _api_hostname() -> str:
    return "stg-oauth.ohiomron.com" if _staging() else "prd-oauth.ohiomron.com"

def _env_prefix() -> str:
    return "stg" if _staging() else "prd"

def _auth_url() -> str:
    return f"https://{_auth_hostname()}/connect/authorize"

def _token_url() -> str:
    return f"https://{_api_hostname()}/{_env_prefix()}/connect/token"

def _data_url() -> str:
    return f"https://{_api_hostname()}/{_env_prefix()}/api/measurement"

def _revoke_url() -> str:
    return f"https://{_api_hostname()}/{_env_prefix()}/connect/revocation"

# Scopes as defined by Omron Partner API
_SCOPES = "bloodpressure activity weight openid offline_access"

# ---------------------------------------------------------------------------
# Token storage
# ---------------------------------------------------------------------------

_TOKENS_PATH = Path.home() / ".jarvis" / "omron_tokens.json"
_TOKENS_LOG_PATH = _TOKENS_PATH.with_name("omron_tokens_log.jsonl")
_TOKENS_STATE_LOG_PATH = _TOKENS_PATH.with_name("omron_tokens_state_log.jsonl")
_TOKENS_PATH.parent.mkdir(parents=True, exist_ok=True)


def _load_tokens() -> dict:
    if _TOKENS_PATH.exists():
        try:
            return json.loads(_TOKENS_PATH.read_text())
        except Exception:
            log.warning("Omron token snapshot unreadable; replaying state log")
    tokens = _load_tokens_from_state_log()
    if tokens:
        atomic_write_json(_TOKENS_PATH, tokens)
        return tokens
    tokens = _load_tokens_from_log()
    if tokens:
        atomic_write_json(_TOKENS_PATH, tokens)
        return tokens
    return {}


def _load_tokens_from_state_log() -> dict:
    if not _TOKENS_STATE_LOG_PATH.exists():
        return {}
    try:
        last: dict[str, Any] | None = None
        for line in _TOKENS_STATE_LOG_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            payload = json.loads(line)
            tokens = payload.get("tokens")
            if isinstance(tokens, dict):
                last = tokens
        if last is not None:
            return last
    except Exception:
        log.warning("Omron token state log unreadable", exc_info=True)
    return {}


def _load_tokens_from_log() -> dict:
    if not _TOKENS_LOG_PATH.exists():
        return {}
    try:
        last: dict[str, Any] | None = None
        for line in _TOKENS_LOG_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            payload = json.loads(line)
            if isinstance(payload, dict):
                last = payload
        if last is not None:
            return last
    except Exception:
        log.warning("Omron token append log unreadable", exc_info=True)
    return {}


def _save_tokens(tokens: dict) -> None:
    append_jsonl(_TOKENS_LOG_PATH, tokens)
    append_jsonl(
        _TOKENS_STATE_LOG_PATH,
        {
            "saved_at": datetime.utcnow().isoformat(),
            "tokens": tokens,
        },
    )
    atomic_write_json(_TOKENS_PATH, tokens)


def _decode_jwt_payload(token: str) -> dict:
    """Decode the payload section of a JWT without verifying the signature."""
    try:
        parts = token.split(".")
        if len(parts) < 2:
            return {}
        # Add padding
        payload = parts[1] + "=" * (4 - len(parts[1]) % 4)
        return json.loads(base64.urlsafe_b64decode(payload))
    except Exception:
        return {}


def _extract_user_id(tokens: dict) -> str | None:
    """Extract the Omron user ID (sub claim) from the access token JWT."""
    access_token = tokens.get("access_token", "")
    if access_token:
        payload = _decode_jwt_payload(access_token)
        uid = payload.get("sub") or payload.get("custom:userId")
        if uid:
            return uid
    return None


# ---------------------------------------------------------------------------
# Connection status
# ---------------------------------------------------------------------------

def get_connection_status() -> dict:
    client_id = os.getenv("OMRON_CLIENT_ID", "")
    if not client_id:
        return {
            "connected": False,
            "configured": False,
            "message": "Add OMRON_CLIENT_ID + OMRON_CLIENT_SECRET to .env",
        }
    tokens = _load_tokens()
    if not tokens.get("access_token"):
        return {
            "connected": False,
            "configured": True,
            "message": "Not connected — visit /api/health/omron/connect",
        }
    expires_at = tokens.get("expires_at", 0)
    expired = datetime.utcnow().timestamp() > expires_at
    env = "staging" if _staging() else "production"
    return {
        "connected":  not expired,
        "configured": True,
        "expired":    expired,
        "last_sync":  tokens.get("last_sync"),
        "user_id":    tokens.get("user_id"),
        "environment": env,
        "message":    f"Connected ({env})" if not expired else "Token expired — reconnect",
    }


# ---------------------------------------------------------------------------
# OAuth flow helpers
# ---------------------------------------------------------------------------

def build_auth_url(redirect_uri: str, state: str = "jarvis") -> str:
    """Return the Omron authorization URL to redirect the user to."""
    client_id = os.getenv("OMRON_CLIENT_ID", "")
    if not client_id:
        raise ValueError("OMRON_CLIENT_ID not set in environment")
    params = {
        "response_type": "code",
        "client_id":     client_id,
        "redirect_uri":  redirect_uri,
        "scope":         _SCOPES,
        "state":         state,
    }
    return f"{_auth_url()}?{urlencode(params)}"


async def exchange_code(code: str, redirect_uri: str) -> dict:
    """Exchange authorization code for access + refresh tokens."""
    client_id     = os.getenv("OMRON_CLIENT_ID", "")
    client_secret = os.getenv("OMRON_CLIENT_SECRET", "")

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            _token_url(),
            data={
                "grant_type":    "authorization_code",
                "code":          code,
                "redirect_uri":  redirect_uri,
                "client_id":     client_id,
                "client_secret": client_secret,
                "scope":         _SCOPES,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15,
        )
        resp.raise_for_status()
        tokens = resp.json()

    # Stamp expiry and extract user ID
    tokens["expires_at"] = (
        datetime.utcnow() + timedelta(seconds=tokens.get("expiresIn", tokens.get("expires_in", 3600)))
    ).timestamp()
    uid = _extract_user_id(tokens)
    if uid:
        tokens["user_id"] = uid

    _save_tokens(tokens)
    log.info("Omron tokens saved — user_id=%s", tokens.get("user_id"))
    return tokens


async def _refresh_if_needed() -> dict | None:
    """Refresh access token if expiring within 5 minutes."""
    tokens = _load_tokens()
    if not tokens.get("access_token"):
        return None

    expires_at = tokens.get("expires_at", 0)
    if datetime.utcnow().timestamp() < expires_at - 300:
        return tokens  # still valid

    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        log.warning("Omron: token expired and no refresh token — reconnect required")
        return None

    client_id     = os.getenv("OMRON_CLIENT_ID", "")
    client_secret = os.getenv("OMRON_CLIENT_SECRET", "")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                _token_url(),
                data={
                    "grant_type":    "refresh_token",
                    "refresh_token": refresh_token,
                    "redirect_uri":  tokens.get("redirect_uri", ""),
                    "client_id":     client_id,
                    "client_secret": client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=15,
            )
            resp.raise_for_status()
            new_tokens = resp.json()

        new_tokens["expires_at"] = (
            datetime.utcnow() + timedelta(
                seconds=new_tokens.get("expiresIn", new_tokens.get("expires_in", 3600))
            )
        ).timestamp()
        # Preserve fields not in refresh response
        if "refresh_token" not in new_tokens:
            new_tokens["refresh_token"] = refresh_token
        for k in ("user_id", "last_sync", "redirect_uri"):
            if k in tokens:
                new_tokens.setdefault(k, tokens[k])

        _save_tokens(new_tokens)
        log.info("Omron access token refreshed")
        return new_tokens

    except Exception as exc:
        log.error("Omron token refresh failed: %s", exc)
        return None


async def revoke() -> bool:
    """Revoke the current refresh token."""
    tokens = _load_tokens()
    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        return False
    client_id     = os.getenv("OMRON_CLIENT_ID", "")
    client_secret = os.getenv("OMRON_CLIENT_SECRET", "")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                _revoke_url(),
                data={
                    "client_id":        client_id,
                    "client_secret":    client_secret,
                    "token":            refresh_token,
                    "token_type_hint":  "refresh_token",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10,
            )
        _save_tokens({})
        log.info("Omron consent revoked (status %s)", resp.status_code)
        return True
    except Exception as exc:
        log.error("Omron revocation failed: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Data fetch — BP (with pagination)
# ---------------------------------------------------------------------------

async def _fetch_bp_page(
    access_token: str,
    since: str,
    pagination_key: str | None = None,
) -> tuple[list[dict], str | None]:
    """Fetch one page of BP readings. Returns (readings, next_pagination_key)."""
    data: dict[str, Any] = {
        "type":  "bloodpressure",
        "since": since,
        "limit": 100,
    }
    if pagination_key:
        data["bloodpressurePaginationKey"] = pagination_key

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            _data_url(),
            data=data,
            headers={
                "Authorization":  f"Bearer {access_token}",
                "Content-Type":   "application/x-www-form-urlencoded",
            },
            timeout=20,
        )
        resp.raise_for_status()
        body = resp.json()

    result = body.get("result", {})
    readings = result.get("bloodPressure", [])
    next_key = result.get("paginationKey", {}).get("bloodpressurePaginationKey")
    return readings, next_key


async def sync_bp(days_back: int = 90) -> dict:
    """
    Fetch blood pressure measurements from Omron Partner API.
    Stores results in health_db.bp_readings.
    Returns {"ok": True, "count": N} or {"ok": False, "error": ...}.
    """
    try:
        from .health_db import upsert_bp_reading, log_sync
    except ImportError:
        from health_db import upsert_bp_reading, log_sync

    tokens = await _refresh_if_needed()
    if not tokens:
        return {"ok": False, "error": "Not connected to Omron — visit /api/health/omron/connect"}

    access_token = tokens["access_token"]
    since = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%d")

    count = 0
    afib_count = 0
    pagination_key = None

    try:
        while True:
            readings, pagination_key = await _fetch_bp_page(access_token, since, pagination_key)

            for r in readings:
                # When AFib detected, Omron sets systolic/diastolic/pulse all to 0
                possible_afib = r.get("possibleAfib", False)
                systolic  = r.get("systolic", 0)
                diastolic = r.get("diastolic", 0)
                pulse     = r.get("pulse", 0)

                if possible_afib:
                    afib_count += 1
                    log.warning("Omron AFib event detected: %s", r.get("dateTimeLocal", ""))

                if not systolic and not possible_afib:
                    continue  # skip zero readings that aren't AFib flags

                reading_date = r.get("dateTimeLocal") or r.get("dateTime", "")

                await upsert_bp_reading({
                    "reading_date":  reading_date,
                    "source":        "omron",
                    "systolic":      systolic if not possible_afib else None,
                    "diastolic":     diastolic if not possible_afib else None,
                    "pulse":         pulse if not possible_afib else None,
                    "irregular":     possible_afib,
                    "body_movement": False,
                    "cuff_wrap":     False,
                    "raw_json":      json.dumps(r),
                })
                count += 1

            # Stop paginating if no more data
            if not pagination_key:
                break

    except httpx.HTTPStatusError as exc:
        err = f"Omron API {exc.response.status_code}: {exc.response.text[:300]}"
        log.error(err)
        await log_sync("omron", "error", err)
        return {"ok": False, "error": err}
    except Exception as exc:
        log.error("Omron sync error: %s", exc)
        await log_sync("omron", "error", str(exc))
        return {"ok": False, "error": str(exc)}

    tokens["last_sync"] = datetime.utcnow().isoformat()
    _save_tokens(tokens)

    msg = f"Synced {count} BP readings"
    if afib_count:
        msg += f" ({afib_count} AFib events!)"
    await log_sync("omron", "success", msg)
    log.info("Omron sync complete: %s", msg)
    return {"ok": True, "count": count, "afib_events": afib_count}


# ---------------------------------------------------------------------------
# Notification handler (called from service.py route)
# ---------------------------------------------------------------------------

async def handle_notification(payload: dict) -> dict:
    """
    Process a push notification from Omron.
    Payload: {"id": <user_id>, "timestamp": <ms_epoch>, "type": "bloodpressure"|"activity"|"weight"}
    Triggers a sync automatically.
    """
    user_id   = payload.get("id")
    data_type = payload.get("type", "")
    ts        = payload.get("timestamp", 0)

    log.info("Omron notification: user=%s type=%s ts=%s", user_id, data_type, ts)

    if data_type == "bloodpressure":
        result = await sync_bp(days_back=7)  # only pull last 7 days on notification
        return result

    # activity / weight — pull latest (extensible later)
    return {"ok": True, "message": f"Notification received for {data_type}, no sync implemented yet"}
