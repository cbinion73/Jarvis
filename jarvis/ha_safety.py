"""E11: Home Assistant safety layer.

Implements:
- Safe service mapping: which HA domain/service pairs are allowed per context
- Hard constraint: no voice-only unlock of any lock entity
- Config validation: honest unavailable state when HA is not configured
- Audit logging of every HA service call
- Approval policy: which actions require explicit user approval

Security constraints (enforced here, not advisory):
- Remote unlock from voice alone is NEVER permitted.
- Lock operations always require two-factor: an approved trust zone stage + explicit caller confirmation.
- Unsafe services (e.g., automation.reload, script.run for unknown scripts) are denied.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from .persistence import append_jsonl

logger = logging.getLogger("jarvis.ha_safety")

_HA_AUDIT_PATH = Path("data/home/ha_safety_audit.jsonl")

# ---------------------------------------------------------------------------
# Safe service allowlist
# Each entry: (domain, service) → {requires_approval, driving_safe, description}
# ---------------------------------------------------------------------------
_SAFE_SERVICES: dict[tuple[str, str], dict[str, Any]] = {
    # Lights
    ("light", "turn_on"):   {"requires_approval": False, "driving_safe": False, "description": "Turn on a light"},
    ("light", "turn_off"):  {"requires_approval": False, "driving_safe": False, "description": "Turn off a light"},
    ("light", "toggle"):    {"requires_approval": False, "driving_safe": False, "description": "Toggle a light"},
    # Switches
    ("switch", "turn_on"):  {"requires_approval": False, "driving_safe": False, "description": "Turn on a switch"},
    ("switch", "turn_off"): {"requires_approval": False, "driving_safe": False, "description": "Turn off a switch"},
    # Climate
    ("climate", "set_temperature"):   {"requires_approval": False, "driving_safe": True, "description": "Set thermostat temperature"},
    ("climate", "set_hvac_mode"):     {"requires_approval": False, "driving_safe": True, "description": "Set HVAC mode"},
    # Covers (garage door)
    ("cover", "open_cover"):  {"requires_approval": True,  "driving_safe": True,  "description": "Open garage/cover"},
    ("cover", "close_cover"): {"requires_approval": True,  "driving_safe": True,  "description": "Close garage/cover"},
    # Media player
    ("media_player", "media_play"):  {"requires_approval": False, "driving_safe": True,  "description": "Play media"},
    ("media_player", "media_pause"): {"requires_approval": False, "driving_safe": True,  "description": "Pause media"},
    # Notifications
    ("notify", "mobile_app_chris"):  {"requires_approval": False, "driving_safe": True,  "description": "Send mobile notification"},
    # Scene
    ("scene", "turn_on"):    {"requires_approval": False, "driving_safe": False, "description": "Activate a scene"},
    # Input boolean
    ("input_boolean", "turn_on"):  {"requires_approval": False, "driving_safe": False, "description": "Enable input boolean"},
    ("input_boolean", "turn_off"): {"requires_approval": False, "driving_safe": False, "description": "Disable input boolean"},
}

# ---------------------------------------------------------------------------
# Explicitly denied services (always blocked regardless of approval)
# ---------------------------------------------------------------------------
_DENIED_SERVICES: dict[tuple[str, str], str] = {
    ("lock", "unlock"):           "Remote unlock requires physical presence or dedicated two-factor flow — not permitted via voice or API alone.",
    ("lock", "open"):             "Remote unlock requires physical presence or dedicated two-factor flow — not permitted via voice or API alone.",
    ("automation", "reload"):     "Automation reload can affect safety systems — not permitted via API.",
    ("homeassistant", "restart"): "HA restart can cause service outage — not permitted via API.",
    ("homeassistant", "stop"):    "HA stop would disable home safety sensors — not permitted via API.",
    ("shell_command", "*"):       "Shell commands are never permitted via JARVIS.",
    ("python_script", "*"):       "Arbitrary Python execution is never permitted via JARVIS.",
}

# Lock entities require the strongest governance (no voice-only unlock ever)
_LOCK_DOMAINS = frozenset({"lock"})


def _ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _audit(
    *,
    decision: str,
    domain: str,
    service: str,
    entity_id: str,
    actor: str,
    reason: str,
    voice_only: bool = False,
) -> None:
    record = {
        "ts": _ts(),
        "decision": decision,
        "domain": domain,
        "service": service,
        "entity_id": entity_id,
        "actor": actor,
        "reason": reason,
        "voice_only": voice_only,
    }
    try:
        _HA_AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        append_jsonl(_HA_AUDIT_PATH, record)
    except Exception as exc:
        logger.debug("ha_safety audit write failed: %s", exc)


def check_service_call(
    *,
    domain: str,
    service: str,
    entity_id: str,
    actor: str = "system",
    voice_only: bool = False,
    requested_by_voice: bool = False,
) -> dict[str, Any]:
    """Gate a proposed Home Assistant service call through the safety policy.

    Returns:
        {
          allowed: bool,
          requires_approval: bool,
          decision: "allow" | "deny" | "require_approval",
          reason: str,
          voice_safe: bool,
        }
    """
    domain = str(domain or "").strip().lower()
    service = str(service or "").strip().lower()
    entity_id = str(entity_id or "").strip()
    is_voice = voice_only or requested_by_voice

    # Hard constraint 1: no lock unlock from voice
    if domain in _LOCK_DOMAINS and service in ("unlock", "open"):
        reason = "Remote unlock from voice or API alone is never permitted. Physical presence or dedicated two-factor approval required."
        _audit(decision="deny", domain=domain, service=service,
               entity_id=entity_id, actor=actor, reason=reason, voice_only=is_voice)
        return {
            "allowed": False,
            "requires_approval": False,
            "decision": "deny",
            "reason": reason,
            "voice_safe": False,
            "hard_boundary": True,
        }

    # Check explicit deny list
    deny_key = (domain, service)
    wildcard_key = (domain, "*")
    deny_reason = _DENIED_SERVICES.get(deny_key) or _DENIED_SERVICES.get(wildcard_key)
    if deny_reason:
        _audit(decision="deny", domain=domain, service=service,
               entity_id=entity_id, actor=actor, reason=deny_reason, voice_only=is_voice)
        return {
            "allowed": False,
            "requires_approval": False,
            "decision": "deny",
            "reason": deny_reason,
            "voice_safe": False,
            "hard_boundary": True,
        }

    # Check safe allowlist
    service_meta = _SAFE_SERVICES.get((domain, service))
    if service_meta is None:
        reason = f"Service ({domain}.{service}) is not on the safe-service allowlist — fail-closed."
        _audit(decision="deny", domain=domain, service=service,
               entity_id=entity_id, actor=actor, reason=reason, voice_only=is_voice)
        return {
            "allowed": False,
            "requires_approval": False,
            "decision": "deny",
            "reason": reason,
            "voice_safe": False,
            "hard_boundary": False,
        }

    # Allowed — check if approval needed
    needs_approval = bool(service_meta.get("requires_approval"))
    voice_safe = bool(service_meta.get("driving_safe"))
    if needs_approval:
        decision = "require_approval"
        reason = f"{service_meta['description']} requires explicit approval before execution."
    else:
        decision = "allow"
        reason = service_meta["description"]

    _audit(decision=decision, domain=domain, service=service,
           entity_id=entity_id, actor=actor, reason=reason, voice_only=is_voice)
    return {
        "allowed": decision == "allow",
        "requires_approval": needs_approval,
        "decision": decision,
        "reason": reason,
        "voice_safe": voice_safe,
        "hard_boundary": False,
    }


def validate_ha_config(ha_url: str, ha_token: str) -> dict[str, Any]:
    """Validate Home Assistant configuration and return honest availability state."""
    if not ha_url or not ha_url.strip():
        return {
            "configured": False,
            "source": "unavailable",
            "reason": "HOME_ASSISTANT_URL environment variable is not set.",
            "action_required": "Set HOME_ASSISTANT_URL to your HA instance URL in .env",
        }
    if not ha_token or not ha_token.strip():
        return {
            "configured": False,
            "source": "unavailable",
            "reason": "HOME_ASSISTANT_TOKEN environment variable is not set.",
            "action_required": "Create a long-lived access token in HA and set HOME_ASSISTANT_TOKEN in .env",
        }
    return {
        "configured": True,
        "source": "config",
        "ha_url": ha_url.rstrip("/"),
        "token_present": True,
    }


def list_safe_services() -> dict[str, Any]:
    """Return the full safe service allowlist and denied list for UI display."""
    safe = [
        {
            "domain": domain,
            "service": svc,
            "requires_approval": meta["requires_approval"],
            "driving_safe": meta["driving_safe"],
            "description": meta["description"],
        }
        for (domain, svc), meta in sorted(_SAFE_SERVICES.items())
    ]
    denied = [
        {
            "domain": domain,
            "service": svc,
            "reason": reason,
        }
        for (domain, svc), reason in sorted(_DENIED_SERVICES.items())
    ]
    return {
        "safe_services": safe,
        "denied_services": denied,
        "policy": "fail-closed — services not on allowlist are denied",
        "hard_constraints": [
            "Lock unlock is never permitted via voice or API alone",
            "automation.reload and homeassistant.restart are always denied",
            "Shell commands and Python scripts are always denied",
        ],
    }
