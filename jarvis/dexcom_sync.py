"""
JARVIS Dexcom G7 Integration — OAuth 2.0 + CGM real-time glucose sync.

API docs: https://developer.dexcom.com/

Setup:
  1. Register at https://developer.dexcom.com → create an app → get client_id + client_secret
  2. Set redirect URI in your Dexcom app to: http://localhost:8787/api/health/dexcom/callback
     (if Dexcom requires HTTPS or rejects localhost, run ngrok and use the ngrok URL just for setup)
  3. Add DEXCOM_CLIENT_ID and DEXCOM_CLIENT_SECRET to .env
  4. Visit /api/health/dexcom/connect in JARVIS to start the OAuth flow

OAuth flow:
  GET  /api/health/dexcom/connect      → redirect to Dexcom auth page
  GET  /api/health/dexcom/callback     → exchange code for tokens, save, redirect home
  POST /api/health/dexcom/sync         → manually pull latest readings
  GET  /api/health/dexcom/status       → connection status + glucose stats
  GET  /api/health/dexcom/current      → latest reading + trend

Data pulled:
  - EGVs (Estimated Glucose Values) — 5-minute readings with trend arrows
  - Trend rate (mg/dL/min) — rate of change
  - Stored in health_db.glucose_readings
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode

import httpx

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

def _sandbox() -> bool:
    return os.getenv("DEXCOM_SANDBOX", "").lower() in ("1", "true", "yes")

def _base_url() -> str:
    return "https://sandbox-api.dexcom.com" if _sandbox() else "https://api.dexcom.com"

def _auth_url() -> str:
    return f"{_base_url()}/v2/oauth2/login"

def _token_url() -> str:
    return f"{_base_url()}/v2/oauth2/token"

def _egv_url() -> str:
    return f"{_base_url()}/v3/users/self/egvs"

# Trend arrow display
_TREND_ARROWS = {
    "doubleUp":       "⬆⬆",
    "singleUp":       "⬆",
    "fortyFiveUp":    "↗",
    "flat":           "→",
    "fortyFiveDown":  "↘",
    "singleDown":     "⬇",
    "doubleDown":     "⬇⬇",
    "notComputable":  "?",
    "rateOutOfRange": "??",
    "none":           "",
}

# ---------------------------------------------------------------------------
# Token storage
# ---------------------------------------------------------------------------

_TOKENS_PATH = Path.home() / ".jarvis" / "dexcom_tokens.json"
_TOKENS_PATH.parent.mkdir(parents=True, exist_ok=True)


def _load_tokens() -> dict:
    if _TOKENS_PATH.exists():
        try:
            return json.loads(_TOKENS_PATH.read_text())
        except Exception:
            pass
    return {}


def _save_tokens(tokens: dict) -> None:
    _TOKENS_PATH.write_text(json.dumps(tokens, indent=2))


# ---------------------------------------------------------------------------
# Connection status
# ---------------------------------------------------------------------------

def get_connection_status() -> dict:
    client_id = os.getenv("DEXCOM_CLIENT_ID", "")
    if not client_id:
        return {
            "connected":  False,
            "configured": False,
            "message":    "Add DEXCOM_CLIENT_ID + DEXCOM_CLIENT_SECRET to .env",
        }
    tokens = _load_tokens()
    if not tokens.get("access_token"):
        return {
            "connected":  False,
            "configured": True,
            "message":    "Not connected — visit /api/health/dexcom/connect",
        }
    expires_at = tokens.get("expires_at", 0)
    expired = datetime.utcnow().timestamp() > expires_at
    env = "sandbox" if _sandbox() else "production"
    return {
        "connected":   not expired,
        "configured":  True,
        "expired":     expired,
        "last_sync":   tokens.get("last_sync"),
        "environment": env,
        "message":     f"Connected ({env})" if not expired else "Token expired — reconnect",
    }


# ---------------------------------------------------------------------------
# OAuth flow
# ---------------------------------------------------------------------------

def build_auth_url(redirect_uri: str, state: str = "jarvis") -> str:
    """Return the Dexcom authorization URL."""
    client_id = os.getenv("DEXCOM_CLIENT_ID", "")
    if not client_id:
        raise ValueError("DEXCOM_CLIENT_ID not set in .env")
    params = {
        "client_id":     client_id,
        "redirect_uri":  redirect_uri,
        "response_type": "code",
        "scope":         "offline_access",
        "state":         state,
    }
    return f"{_auth_url()}?{urlencode(params)}"


async def exchange_code(code: str, redirect_uri: str) -> dict:
    """
    Exchange authorization code for access + refresh tokens.
    Dexcom requires client credentials as HTTP Basic auth, not in the POST body.
    """
    client_id     = os.getenv("DEXCOM_CLIENT_ID", "")
    client_secret = os.getenv("DEXCOM_CLIENT_SECRET", "")

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            _token_url(),
            data={
                "grant_type":   "authorization_code",
                "code":         code,
                "redirect_uri": redirect_uri,
            },
            auth=(client_id, client_secret),   # Basic auth — Dexcom requirement
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15,
        )

        if not resp.is_success:
            body = resp.text[:500]
            log.error("Dexcom token exchange failed %s: %s", resp.status_code, body)
            raise ValueError(f"Dexcom token exchange {resp.status_code}: {body}")

        tokens = resp.json()

    tokens["expires_at"] = (
        datetime.utcnow() + timedelta(seconds=tokens.get("expires_in", 7200))
    ).timestamp()
    tokens["redirect_uri"] = redirect_uri
    _save_tokens(tokens)
    log.info("Dexcom tokens saved — expires_in=%s", tokens.get("expires_in"))
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
        log.warning("Dexcom: token expired, no refresh token — reconnect required")
        return None

    client_id     = os.getenv("DEXCOM_CLIENT_ID", "")
    client_secret = os.getenv("DEXCOM_CLIENT_SECRET", "")

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                _token_url(),
                data={
                    "grant_type":    "refresh_token",
                    "refresh_token": refresh_token,
                    "redirect_uri":  tokens.get("redirect_uri", ""),
                },
                auth=(client_id, client_secret),   # Basic auth
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=15,
            )
            resp.raise_for_status()
            new_tokens = resp.json()

        new_tokens["expires_at"] = (
            datetime.utcnow() + timedelta(seconds=new_tokens.get("expires_in", 7200))
        ).timestamp()
        # Preserve fields not returned in refresh response
        for k in ("redirect_uri", "last_sync"):
            if k in tokens:
                new_tokens.setdefault(k, tokens[k])
        if "refresh_token" not in new_tokens:
            new_tokens["refresh_token"] = refresh_token

        _save_tokens(new_tokens)
        log.info("Dexcom access token refreshed")
        return new_tokens

    except Exception as exc:
        log.error("Dexcom token refresh failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Data fetch
# ---------------------------------------------------------------------------

async def sync_egvs(hours_back: int = 24) -> dict:
    """
    Fetch EGV (glucose) readings from Dexcom API.
    Stores results in health_db.glucose_readings.
    Returns {"ok": True, "count": N, "latest": {...}} or {"ok": False, "error": ...}.

    Dexcom EGV response:
    {
      "egvs": [
        {
          "systemTime": "2024-01-01T12:00:00",
          "displayTime": "2024-01-01T07:00:00",   # local time
          "value": 120,
          "realtimeValue": 120,
          "smoothedValue": 119,
          "status": null,
          "trend": "flat",
          "trendRate": 0.0
        }
      ],
      "unit": "mg/dL",
      "rateUnit": "mg/dL/min"
    }
    """
    try:
        from .health_db import upsert_glucose_reading, log_sync
    except ImportError:
        from health_db import upsert_glucose_reading, log_sync

    tokens = await _refresh_if_needed()
    if not tokens:
        return {"ok": False, "error": "Not connected to Dexcom — visit /api/health/dexcom/connect"}

    access_token = tokens["access_token"]

    # Dexcom API uses ISO8601 with T and no timezone suffix for UTC
    end_dt   = datetime.utcnow()
    start_dt = end_dt - timedelta(hours=hours_back)
    start_str = start_dt.strftime("%Y-%m-%dT%H:%M:%S")
    end_str   = end_dt.strftime("%Y-%m-%dT%H:%M:%S")

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                _egv_url(),
                params={"startDate": start_str, "endDate": end_str},
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=20,
            )
            resp.raise_for_status()
            body = resp.json()

    except httpx.HTTPStatusError as exc:
        err = f"Dexcom API {exc.response.status_code}: {exc.response.text[:300]}"
        log.error(err)
        await log_sync("dexcom", "error", err)
        return {"ok": False, "error": err}
    except Exception as exc:
        log.error("Dexcom sync error: %s", exc)
        await log_sync("dexcom", "error", str(exc))
        return {"ok": False, "error": str(exc)}

    egvs = body.get("egvs", [])
    count = 0
    latest = None

    for egv in egvs:
        # Use systemTime (UTC) as the canonical reading time
        reading_time = egv.get("systemTime") or egv.get("displayTime", "")
        glucose      = egv.get("value")
        trend        = egv.get("trend", "")
        trend_rate   = egv.get("trendRate")
        status       = egv.get("status")  # None = normal; "low" / "high" = out of sensor range

        # Skip readings where sensor can't compute a value
        if glucose is None or trend in ("notComputable", "rateOutOfRange") and glucose == 0:
            continue

        await upsert_glucose_reading({
            "reading_time": reading_time,
            "source":       "dexcom",
            "glucose_mgdl": glucose,
            "trend":        trend,
            "trend_rate":   trend_rate,
            "status":       status,
            "raw_json":     json.dumps(egv),
        })
        count += 1
        if latest is None:
            latest = {
                "reading_time": reading_time,
                "glucose_mgdl": glucose,
                "trend":        trend,
                "trend_arrow":  _TREND_ARROWS.get(trend or "", ""),
                "trend_rate":   trend_rate,
                "status":       status,
            }

    tokens["last_sync"] = datetime.utcnow().isoformat()
    _save_tokens(tokens)

    msg = f"Synced {count} glucose readings"
    await log_sync("dexcom", "success", msg)
    log.info("Dexcom sync complete: %s", msg)

    return {"ok": True, "count": count, "latest": latest}


async def get_current_reading() -> dict | None:
    """
    Return the most recent glucose reading with display-friendly fields.
    Does NOT call the API — reads from local DB.
    """
    try:
        from .health_db import get_latest_glucose
    except ImportError:
        from health_db import get_latest_glucose

    rec = await get_latest_glucose()
    if not rec:
        return None

    trend = rec.get("trend", "")
    glucose = rec.get("glucose_mgdl")

    # Classify glucose range
    if glucose is None:
        range_label = "unknown"
    elif glucose < 54:
        range_label = "very_low"
    elif glucose < 70:
        range_label = "low"
    elif glucose <= 180:
        range_label = "in_range"
    elif glucose <= 250:
        range_label = "high"
    else:
        range_label = "very_high"

    # How old is this reading?
    age_min = None
    try:
        reading_dt = datetime.fromisoformat(rec["reading_time"])
        age_min = round((datetime.utcnow() - reading_dt).total_seconds() / 60)
    except Exception:
        pass

    return {
        "glucose_mgdl":  glucose,
        "trend":         trend,
        "trend_arrow":   _TREND_ARROWS.get(trend or "", ""),
        "trend_rate":    rec.get("trend_rate"),
        "range":         range_label,
        "reading_time":  rec.get("reading_time"),
        "age_minutes":   age_min,
        "stale":         age_min is not None and age_min > 15,
        "source":        rec.get("source", "dexcom"),
    }
