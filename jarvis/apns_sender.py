"""
JARVIS APNs Sender
==================
Sends push notifications to iPhone via Apple Push Notification service (APNs).

Authentication uses the token-based (.p8 key) approach — no certificate renewal needed.

Setup (one-time):
  1. developer.apple.com → Keys → + → Enable "Apple Push Notifications service (APNs)"
  2. Download AuthKey_XXXXXXXXXX.p8 → save to data/settings/apns_key.p8
  3. Set APNS_KEY_ID, APNS_TEAM_ID in data/settings/apns_config.json

Config file schema (data/settings/apns_config.json):
  {
    "key_id":   "XXXXXXXXXX",   // 10-char Key ID shown in portal
    "team_id":  "YYYYYYYYYY",   // 10-char Team ID (top-right in portal)
    "sandbox":  true            // true = development builds, false = production
  }
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_CONFIG_PATH  = Path("data/settings/apns_config.json")
_KEY_PATH     = Path("data/settings/apns_key.p8")
_TOKENS_PATH  = Path("data/settings/apns_device_tokens.json")
_BUNDLE_ID    = "com.binion.jarvisphone"

# ---------------------------------------------------------------------------
# Token store
# ---------------------------------------------------------------------------

def _load_tokens() -> dict[str, list[str]]:
    """Load {actor_id: [token, …]} from disk."""
    if not _TOKENS_PATH.exists():
        return {}
    try:
        return json.loads(_TOKENS_PATH.read_text())
    except Exception:
        return {}


def _save_tokens(tokens: dict[str, list[str]]) -> None:
    _TOKENS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _TOKENS_PATH.write_text(json.dumps(tokens, indent=2))


def register_device_token(actor_id: str, token: str, platform: str = "ios") -> None:
    """Store a device APNs token for an actor. Deduplicates automatically."""
    tokens = _load_tokens()
    actor_tokens = tokens.get(actor_id, [])
    if token not in actor_tokens:
        actor_tokens.append(token)
        tokens[actor_id] = actor_tokens
        _save_tokens(tokens)
        logger.info("apns: registered token for %s (%s)", actor_id, platform)


def get_tokens(actor_id: str) -> list[str]:
    """Return all stored APNs tokens for an actor."""
    return _load_tokens().get(actor_id, [])


# ---------------------------------------------------------------------------
# JWT builder
# ---------------------------------------------------------------------------

def _build_jwt(key_id: str, team_id: str) -> str:
    import jwt as _jwt

    private_key = _KEY_PATH.read_text()
    now = int(time.time())
    payload = {"iss": team_id, "iat": now}
    token = _jwt.encode(
        payload,
        private_key,
        algorithm="ES256",
        headers={"kid": key_id},
    )
    # PyJWT ≥ 2.0 returns str directly
    return token if isinstance(token, str) else token.decode("utf-8")


# ---------------------------------------------------------------------------
# Push sender
# ---------------------------------------------------------------------------

def send_push(
    actor_id: str,
    title: str,
    body: str,
    badge: int = 0,
    category: str = "general",
    extra: dict[str, Any] | None = None,
    *,
    collapse_id: str | None = None,
) -> int:
    """
    Send a push notification to all devices registered for *actor_id*.

    Returns the number of devices successfully notified.
    """
    if not _CONFIG_PATH.exists():
        logger.debug("apns: config not found at %s — skipping push", _CONFIG_PATH)
        return 0
    if not _KEY_PATH.exists():
        logger.debug("apns: key not found at %s — skipping push", _KEY_PATH)
        return 0

    tokens = get_tokens(actor_id)
    if not tokens:
        logger.debug("apns: no tokens for %s", actor_id)
        return 0

    try:
        config = json.loads(_CONFIG_PATH.read_text())
    except Exception as exc:
        logger.warning("apns: bad config: %s", exc)
        return 0

    key_id  = config.get("key_id",  "")
    team_id = config.get("team_id", "")
    sandbox = config.get("sandbox", True)

    if not key_id or not team_id:
        logger.warning("apns: key_id / team_id not set in config")
        return 0

    try:
        jwt_token = _build_jwt(key_id, team_id)
    except Exception as exc:
        logger.warning("apns: JWT build failed: %s", exc)
        return 0

    host = "api.sandbox.push.apple.com" if sandbox else "api.push.apple.com"
    base_headers = {
        "authorization":  f"bearer {jwt_token}",
        "apns-topic":     _BUNDLE_ID,
        "apns-push-type": "alert",
        "apns-priority":  "10",
    }
    if collapse_id:
        base_headers["apns-collapse-id"] = collapse_id

    payload: dict[str, Any] = {
        "aps": {
            "alert": {"title": title, "body": body},
            "sound": "default",
            "category": category,
        }
    }
    if badge >= 0:
        payload["aps"]["badge"] = badge
    if extra:
        payload.update(extra)

    success = 0
    dead_tokens: list[str] = []

    try:
        import httpx
        with httpx.Client(http2=True, verify=True) as client:
            for device_token in tokens:
                url = f"https://{host}/3/device/{device_token}"
                try:
                    resp = client.post(url, json=payload, headers=base_headers, timeout=10)
                    if resp.status_code == 200:
                        success += 1
                        logger.info("apns: pushed to %s/%s", actor_id, device_token[-8:])
                    elif resp.status_code == 410:
                        # Token expired — remove it
                        dead_tokens.append(device_token)
                        logger.info("apns: token expired for %s", actor_id)
                    else:
                        err = resp.json().get("reason", resp.text)
                        logger.warning("apns: push failed (%s): %s", resp.status_code, err)
                except Exception as exc:
                    logger.warning("apns: send error for %s: %s", device_token[-8:], exc)
    except ImportError:
        logger.warning("apns: httpx not available")
        return 0

    # Clean up expired tokens
    if dead_tokens:
        all_tokens = _load_tokens()
        actor_tokens = [t for t in all_tokens.get(actor_id, []) if t not in dead_tokens]
        all_tokens[actor_id] = actor_tokens
        _save_tokens(all_tokens)

    return success


# ---------------------------------------------------------------------------
# Convenience wrappers called by other JARVIS modules
# ---------------------------------------------------------------------------

def push_approval_request(actor_id: str, title: str, agent: str, request_id: str) -> int:
    """Fire the 'needs your approval' push with deep-link data."""
    return send_push(
        actor_id,
        title=f"🔔 Needs Your Approval",
        body=f"{agent}: {title}",
        category="approval",
        extra={"request_id": request_id},
        collapse_id=f"approval-{request_id}",
    )


def push_briefing_ready(actor_id: str, greeting: str) -> int:
    """Fire the morning brief ready push."""
    return send_push(
        actor_id,
        title="Your JARVIS Brief is Ready",
        body=greeting,
        category="briefing",
        collapse_id="morning-brief",
    )


def push_health_alert(actor_id: str, message: str) -> int:
    """Fire a health signal alert push."""
    return send_push(
        actor_id,
        title="⚕️ Health Signal",
        body=message,
        category="healthSignal",
    )
