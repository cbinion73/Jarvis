"""E9: Chronicle ownership boundary enforcement.

Chronicle is the authoritative owner of all faith and formation records.
JARVIS memory may reference Chronicle content but must not duplicate or
override it. This module enforces routing rules at the governance layer.

Rules:
1. Faith records (prayer, scripture, devotional, ritual) → Chronicle domain only
2. JARVIS memory facts with domain="chronicle" are read-only from JARVIS perspective
3. Any attempt to write faith-domain content directly to JARVIS memory is blocked
   and redirected to Chronicle with an audit record

Chronicle integration: honest unavailable when Chronicle service is not configured.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from .persistence import append_jsonl

_BOUNDARY_AUDIT_PATH = Path("data/chronicle/boundary_audit.jsonl")

# ---------------------------------------------------------------------------
# Faith-domain content classifier
# ---------------------------------------------------------------------------
FAITH_CONTENT_TAGS = frozenset({
    "prayer", "scripture", "devotional", "bible", "ritual", "worship",
    "sermon", "study", "faith", "spiritual", "church", "liturgy", "sacrament",
    "sabbath", "holy", "communion", "confession",
})

FAITH_DOMAINS = frozenset({"chronicle", "faith", "formation", "ritual", "prayer", "scripture"})


def _ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _audit(event: str, actor: str, content_type: str, extra: dict | None = None) -> None:
    record: dict[str, Any] = {
        "ts": _ts(), "event": event, "actor": actor, "content_type": content_type,
    }
    if extra:
        record.update(extra)
    try:
        _BOUNDARY_AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        append_jsonl(_BOUNDARY_AUDIT_PATH, record)
    except Exception:
        pass


def classify_content(
    *,
    tags: list[str] | None = None,
    domain: str = "",
    content: str = "",
) -> dict[str, Any]:
    """Classify whether content belongs to Chronicle domain.

    Returns:
        {
            is_faith_content: bool,
            domain_owner: "chronicle" | "jarvis",
            routing: "chronicle" | "jarvis_memory",
            reason: str,
        }
    """
    tags = [t.lower() for t in (tags or [])]
    domain_lower = (domain or "").lower()

    # Explicit domain assignment
    if domain_lower in FAITH_DOMAINS:
        return {
            "is_faith_content": True,
            "domain_owner": "chronicle",
            "routing": "chronicle",
            "reason": f"Domain '{domain_lower}' is a Chronicle-owned domain.",
        }

    # Tag-based classification
    faith_tags = [t for t in tags if t in FAITH_CONTENT_TAGS]
    if faith_tags:
        return {
            "is_faith_content": True,
            "domain_owner": "chronicle",
            "routing": "chronicle",
            "reason": f"Content tags {faith_tags} indicate faith/formation content — route to Chronicle.",
        }

    # Content keyword scan (lightweight)
    content_lower = (content or "").lower()
    found_kw = [kw for kw in FAITH_CONTENT_TAGS if kw in content_lower]
    if len(found_kw) >= 2:
        return {
            "is_faith_content": True,
            "domain_owner": "chronicle",
            "routing": "chronicle",
            "reason": f"Content contains faith keywords {found_kw[:3]} — route to Chronicle.",
        }

    return {
        "is_faith_content": False,
        "domain_owner": "jarvis",
        "routing": "jarvis_memory",
        "reason": "No faith-domain signals detected — route to JARVIS memory.",
    }


def enforce_routing(
    *,
    actor: str,
    content_type: str,
    tags: list[str] | None = None,
    domain: str = "",
    content: str = "",
) -> dict[str, Any]:
    """Gate a write request through the Chronicle boundary policy.

    If the content belongs to Chronicle:
    - blocks direct JARVIS memory write
    - returns routing=chronicle with an honest blocker message
    - logs to boundary audit

    Chronicle itself is not called here — the caller must route to Chronicle.
    Honest unavailable: Chronicle service integration is not yet wired;
    the routing decision is correct but Chronicle write must be done manually.
    """
    classification = classify_content(tags=tags, domain=domain, content=content)

    if classification["is_faith_content"]:
        _audit(
            "blocked_jarvis_write",
            actor=actor,
            content_type=content_type,
            extra={"reason": classification["reason"], "routing": "chronicle"},
        )
        return {
            "allowed": False,
            "routing": "chronicle",
            "domain_owner": "chronicle",
            "reason": classification["reason"],
            "action_required": (
                "This content belongs to the Chronicle domain. "
                "Write to Chronicle via /api/chronicle/* or the Chronicle service directly. "
                "JARVIS memory should not duplicate faith records."
            ),
            "chronicle_available": False,
            "chronicle_source": "unavailable",
            "chronicle_reason": "Chronicle service integration requires configuration of CHRONICLE_SERVICE_URL.",
            "source": "blocked",
        }

    _audit("allowed_jarvis_write", actor=actor, content_type=content_type)
    return {
        "allowed": True,
        "routing": "jarvis_memory",
        "domain_owner": "jarvis",
        "reason": classification["reason"],
        "source": "live",
    }


def chronicle_service_status(chronicle_url: str = "") -> dict[str, Any]:
    """Return honest Chronicle service availability."""
    if not chronicle_url or not chronicle_url.strip():
        return {
            "available": False,
            "source": "unavailable",
            "reason": "CHRONICLE_SERVICE_URL is not configured.",
            "action_required": "Set CHRONICLE_SERVICE_URL in .env to enable Chronicle integration.",
        }
    return {
        "available": True,
        "source": "config",
        "chronicle_url": chronicle_url.rstrip("/"),
    }
