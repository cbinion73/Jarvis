"""E14: Infrastructure deployment contract.

Defines the recovery path, health check requirements, and operational
constraints for the JARVIS always-on host deployment.

This is a governance contract, not a deployment tool. It:
- Declares required infrastructure components and their expected states
- Provides honest availability checks for each component
- Defines the recovery path when components fail
- Checks config completeness before asserting "ready"

Actual deployment is handled by Docker Compose + CI/CD on Hetzner.
This module never modifies infrastructure — read-only governance only.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from .persistence import append_jsonl

_INFRA_AUDIT_PATH = Path("data/infra/health_audit.jsonl")


def _ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# ---------------------------------------------------------------------------
# Infrastructure component registry
# ---------------------------------------------------------------------------
INFRA_COMPONENTS = {
    "jarvis_service": {
        "display_name": "JARVIS FastAPI service",
        "required": True,
        "env_vars": [],
        "health_endpoint": "/api/status",
        "recovery": "docker compose restart jarvis",
    },
    "postgres": {
        "display_name": "PostgreSQL database",
        "required": True,
        "env_vars": ["POSTGRES_PASSWORD"],
        "health_endpoint": None,
        "recovery": "docker compose restart postgres",
    },
    "redis": {
        "display_name": "Redis cache",
        "required": True,
        "env_vars": ["REDIS_URL"],
        "health_endpoint": None,
        "recovery": "docker compose restart redis",
    },
    "chronicle": {
        "display_name": "Chronicle service",
        "required": False,
        "env_vars": ["CHRONICLE_SERVICE_URL"],
        "health_endpoint": "/health",
        "recovery": "docker compose restart chronicle",
    },
    "ghostwritr": {
        "display_name": "Ghostwritr service",
        "required": False,
        "env_vars": ["GHOSTWRITR_URL"],
        "health_endpoint": "/health",
        "recovery": "docker compose restart ghostwritr",
    },
    "cloudflared": {
        "display_name": "Cloudflare Tunnel",
        "required": True,
        "env_vars": ["CLOUDFLARE_TUNNEL_TOKEN"],
        "health_endpoint": None,
        "recovery": "docker compose restart cloudflared",
    },
    "nas_backup": {
        "display_name": "NAS backup storage",
        "required": False,
        "env_vars": ["NAS_BACKUP_PATH", "NAS_BACKUP_HOST"],
        "health_endpoint": None,
        "recovery": "Verify NAS network connectivity; check NAS_BACKUP_HOST reachability.",
    },
    "ups": {
        "display_name": "UPS power supply",
        "required": False,
        "env_vars": ["UPS_APCUPSD_HOST"],
        "health_endpoint": None,
        "recovery": "Check UPS battery status; verify apcupsd daemon on host.",
    },
}


def check_component(component_id: str, env_vars: dict[str, str] | None = None) -> dict[str, Any]:
    """Return honest availability state for a single infrastructure component."""
    env_vars = env_vars or {}
    comp = INFRA_COMPONENTS.get(component_id)
    if not comp:
        return {
            "component_id": component_id,
            "available": False,
            "source": "unavailable",
            "reason": f"Component '{component_id}' is not in the infrastructure registry.",
        }

    missing_vars = [v for v in comp.get("env_vars", []) if not env_vars.get(v)]
    if missing_vars:
        return {
            "component_id": component_id,
            "display_name": comp["display_name"],
            "available": False,
            "source": "unavailable",
            "required": comp["required"],
            "reason": f"Missing env vars: {', '.join(missing_vars)}",
            "action_required": f"Set in .env: {', '.join(missing_vars)}",
            "recovery": comp.get("recovery", ""),
        }

    return {
        "component_id": component_id,
        "display_name": comp["display_name"],
        "available": True,
        "source": "config",
        "required": comp["required"],
        "health_endpoint": comp.get("health_endpoint"),
        "recovery": comp.get("recovery", ""),
    }


def full_deployment_check(env_vars: dict[str, str] | None = None) -> dict[str, Any]:
    """Check all infrastructure components and return deployment readiness.

    Returns:
        {
            ready: bool,
            required_ready: bool,
            components: [...],
            missing_required: [...],
            recovery_steps: [...],
            source: "config" | "unavailable",
        }
    """
    env_vars = env_vars or {}
    components = []
    missing_required: list[str] = []
    recovery_steps: list[str] = []

    for comp_id in INFRA_COMPONENTS:
        result = check_component(comp_id, env_vars)
        result["component_id"] = comp_id
        components.append(result)
        if not result["available"] and INFRA_COMPONENTS[comp_id]["required"]:
            missing_required.append(comp_id)
            rec = INFRA_COMPONENTS[comp_id].get("recovery", "")
            if rec:
                recovery_steps.append(f"{comp_id}: {rec}")

    required_ready = len(missing_required) == 0
    optional_unavailable = [
        c["component_id"] for c in components
        if not c["available"] and not INFRA_COMPONENTS[c["component_id"]]["required"]
    ]

    # Log to audit
    record: dict[str, Any] = {
        "ts": _ts(),
        "event": "deployment_check",
        "required_ready": required_ready,
        "missing_required": missing_required,
        "optional_unavailable": optional_unavailable,
    }
    try:
        _INFRA_AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        append_jsonl(_INFRA_AUDIT_PATH, record)
    except Exception:
        pass

    return {
        "ready": required_ready and len(optional_unavailable) == 0,
        "required_ready": required_ready,
        "source": "config" if required_ready else "unavailable",
        "components": components,
        "missing_required": missing_required,
        "optional_unavailable": optional_unavailable,
        "recovery_steps": recovery_steps,
        "deployment_notes": [
            "JARVIS runs on Hetzner VPS via Docker Compose.",
            "Push to main branch triggers CI/CD deploy.",
            "Data is persisted in Docker volume at /app/data.",
            "NAS backup and UPS monitoring are optional but recommended for always-on operation.",
        ],
    }
