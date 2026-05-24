"""
agent_catalyst.py — Per-Agent Catalyst (Work Intelligence) Interface
=====================================================================
Every JARVIS agent MUST have and use Catalyst.

This module provides ``AgentCatalyst`` — a thin, per-agent facade over
CatalystDB that gives every agent a standard API for:

  - Logging signals (observations, alerts, completions)
  - Creating tasks that appear in the Work Intelligence UI
  - Recording commitments (things the agent is promising to do)
  - Recording decisions (choices made by the agent or user)
  - Querying work context (recent signals, open tasks) for prompt injection

Usage (from any agent module):

    from .agent_catalyst import get_agent_catalyst

    cat = get_agent_catalyst("thor")          # health agent
    cat.log_signal("Sleep score dropped to 72 — below threshold", criticality="CRITICAL")
    cat.create_task("Review hydration protocol this week")
    cat.log_commitment("Monitor sleep metrics for 7 consecutive days")

The factory function is always safe to call — if CatalystDB is not yet
initialised (e.g. during startup), all methods silently no-op.
"""

from __future__ import annotations

import logging
import threading
from typing import Any

logger = logging.getLogger("jarvis.agent_catalyst")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _db():
    """Return the CatalystDB singleton or None if not ready."""
    try:
        from .catalyst_db import get_catalyst_db
        return get_catalyst_db()
    except Exception:
        return None


# ---------------------------------------------------------------------------
# AgentCatalyst
# ---------------------------------------------------------------------------

class AgentCatalyst:
    """
    Work Intelligence interface for a single JARVIS agent.

    All methods are:
    - Thread-safe
    - Fire-and-forget: they log errors but never raise
    - No-op when CatalystDB is unavailable
    """

    USER_ID = "chris"

    def __init__(self, agent_id: str) -> None:
        self.agent_id = agent_id

    # ------------------------------------------------------------------
    # Signals
    # ------------------------------------------------------------------

    def log_signal(
        self,
        content: str,
        *,
        signal_type: str = "agent_activity",
        criticality: str = "STANDARD",
        metadata: dict[str, Any] | None = None,
        external_id: str | None = None,
    ) -> str | None:
        """
        Ingest a signal into CatalystDB raw_signals.

        Returns the signal UUID on success, None on failure.

        criticality: "CRITICAL" | "STANDARD" | "LOW"
        """
        try:
            db = _db()
            if db is None:
                return None
            meta = {"agent_id": self.agent_id, **(metadata or {})}
            row = db.ingest_signal(
                user_id=self.USER_ID,
                signal_type=signal_type,
                content=f"[{self.agent_id}] {content}",
                external_id=external_id,
                source_metadata=meta,
                criticality=criticality,
            )
            return (row or {}).get("id")
        except Exception as exc:
            logger.debug("[%s] log_signal failed: %s", self.agent_id, exc)
            return None

    def log_observation(self, content: str, metadata: dict[str, Any] | None = None) -> str | None:
        """Log a LOW-criticality agent observation."""
        return self.log_signal(content, signal_type="agent_observation",
                               criticality="LOW", metadata=metadata)

    def log_alert(self, content: str, metadata: dict[str, Any] | None = None) -> str | None:
        """Log a CRITICAL-criticality agent alert."""
        return self.log_signal(content, signal_type="agent_alert",
                               criticality="CRITICAL", metadata=metadata)

    def log_completion(self, what: str, metadata: dict[str, Any] | None = None) -> str | None:
        """Log completion of an agent action."""
        return self.log_signal(f"Completed: {what}", signal_type="agent_completion",
                               criticality="LOW", metadata=metadata)

    # ------------------------------------------------------------------
    # Tasks
    # ------------------------------------------------------------------

    def create_task(
        self,
        title: str,
        *,
        priority: str = "medium",
        due_date: str | None = None,
        task_type: str = "agent_task",
        signal_id: str | None = None,
    ) -> str | None:
        """
        Create a task in catalyst_tasks (visible in WI Tasks pane).
        Returns the task UUID or None.

        priority: "high" | "medium" | "low"
        """
        try:
            db = _db()
            if db is None:
                return None
            row = db.create_task(
                user_id=self.USER_ID,
                title=f"[{self.agent_id}] {title}",
                priority=priority,
                due_date=due_date,
                source_signal_id=signal_id,
                task_type=task_type,
            )
            return (row or {}).get("id")
        except Exception as exc:
            logger.debug("[%s] create_task failed: %s", self.agent_id, exc)
            return None

    # ------------------------------------------------------------------
    # Commitments
    # ------------------------------------------------------------------

    def log_commitment(
        self,
        description: str,
        *,
        due_date: str | None = None,
        confidence: float = 0.8,
        signal_id: str | None = None,
    ) -> str | None:
        """
        Record a commitment made by this agent.
        Returns the commitment UUID or None.

        If signal_id is None, a backing signal is auto-created.
        """
        try:
            db = _db()
            if db is None:
                return None
            if signal_id is None:
                signal_id = self.log_signal(
                    f"Commitment: {description}",
                    signal_type="agent_commitment",
                    criticality="STANDARD",
                )
            if signal_id is None:
                return None
            row = db.create_commitment(
                user_id=self.USER_ID,
                signal_id=signal_id,
                description=f"[{self.agent_id}] {description}",
                responsible_party=self.agent_id,
                due_date=due_date,
                confidence=confidence,
            )
            return (row or {}).get("id")
        except Exception as exc:
            logger.debug("[%s] log_commitment failed: %s", self.agent_id, exc)
            return None

    # ------------------------------------------------------------------
    # Decisions
    # ------------------------------------------------------------------

    def record_decision(
        self,
        description: str,
        *,
        reasoning: str = "",
        confidence: float = 0.7,
        signal_id: str | None = None,
    ) -> str | None:
        """
        Record a decision made by this agent or Chris.
        Returns the decision UUID or None.
        """
        try:
            db = _db()
            if db is None:
                return None
            if signal_id is None:
                signal_id = self.log_signal(
                    f"Decision: {description}",
                    signal_type="agent_decision",
                    criticality="STANDARD",
                )
            if signal_id is None:
                return None
            row = db.record_decision(
                user_id=self.USER_ID,
                signal_id=signal_id,
                description=f"[{self.agent_id}] {description}",
                reasoning=reasoning[:800] if reasoning else None,
                confidence=confidence,
            )
            return (row or {}).get("id")
        except Exception as exc:
            logger.debug("[%s] record_decision failed: %s", self.agent_id, exc)
            return None

    # ------------------------------------------------------------------
    # System events
    # ------------------------------------------------------------------

    def log_event(
        self,
        event_type: str,
        description: str,
        metadata: dict[str, Any] | None = None,
        severity: str = "info",
    ) -> None:
        """Log a system event (appears in WI event log)."""
        try:
            db = _db()
            if db is None:
                return
            db.log_system_event(
                event_type=event_type,
                description=f"[{self.agent_id}] {description}",
                metadata={**(metadata or {}), "agent_id": self.agent_id},
                severity=severity,
            )
        except Exception as exc:
            logger.debug("[%s] log_event failed: %s", self.agent_id, exc)

    # ------------------------------------------------------------------
    # Context (for prompt injection)
    # ------------------------------------------------------------------

    def get_context(self, limit: int = 10) -> dict[str, Any]:
        """
        Return recent signals + open tasks for this agent.
        Designed to be injected into agent prompts so the agent
        knows what it has already done and what's still open.

        Returns::

            {
              "agent_id": "thor",
              "recent_signals": [...],
              "open_tasks": [...],
              "error": None | str,
            }
        """
        result: dict[str, Any] = {
            "agent_id": self.agent_id,
            "recent_signals": [],
            "open_tasks": [],
            "error": None,
        }
        try:
            db = _db()
            if db is None:
                result["error"] = "CatalystDB not available"
                return result

            # Recent signals from this agent
            all_signals = db.get_recent_signals(self.USER_ID, limit=limit * 4)
            result["recent_signals"] = [
                s for s in all_signals
                if f"[{self.agent_id}]" in (s.get("content") or "")
            ][:limit]

            # Open tasks assigned to this agent (prefix match)
            all_tasks = db.list_open_tasks(self.USER_ID)
            result["open_tasks"] = [
                t for t in all_tasks
                if (t.get("title") or "").startswith(f"[{self.agent_id}]")
            ][:limit]

        except Exception as exc:
            result["error"] = str(exc)
            logger.debug("[%s] get_context failed: %s", self.agent_id, exc)

        return result

    def context_snippet(self, limit: int = 5) -> str:
        """
        Return a compact plain-text context snippet for prompt injection.
        Typically injected near the end of an agent's system prompt.
        """
        ctx = self.get_context(limit=limit)
        lines: list[str] = []

        signals = ctx.get("recent_signals", [])
        if signals:
            lines.append("Recent Catalyst signals:")
            for s in signals[:3]:
                content = (s.get("content") or "").replace(f"[{self.agent_id}] ", "")
                lines.append(f"  • {content[:120]}")

        tasks = ctx.get("open_tasks", [])
        if tasks:
            lines.append("Open Catalyst tasks:")
            for t in tasks[:3]:
                title = (t.get("title") or "").replace(f"[{self.agent_id}] ", "")
                lines.append(f"  ◦ {title[:120]}")

        return "\n".join(lines) if lines else ""


# ---------------------------------------------------------------------------
# Global singleton registry — one AgentCatalyst per agent_id
# ---------------------------------------------------------------------------

_catalysts: dict[str, AgentCatalyst] = {}
_catalysts_lock = threading.Lock()


def get_agent_catalyst(agent_id: str) -> AgentCatalyst:
    """
    Return the singleton AgentCatalyst for *agent_id*.
    Safe to call at any time — creates on first access.
    """
    with _catalysts_lock:
        if agent_id not in _catalysts:
            _catalysts[agent_id] = AgentCatalyst(agent_id)
        return _catalysts[agent_id]


def all_agent_ids() -> list[str]:
    """Return the canonical list of all 56 JARVIS agent IDs."""
    return [
        # Command
        "nick-fury", "pepper-potts", "star-lord",
        # Engineering
        "iron-man", "spider-man", "war-machine", "ant-man", "groot",
        "loki", "luke-cage", "iron-fist", "nebula", "korg",
        "america-chavez", "makkari",
        # Intelligence
        "black-widow", "hawkeye", "falcon", "winter-soldier",
        "moon-knight", "blade", "daredevil", "jessica-jones",
        "okoye", "agent-13",
        # Analysis
        "hulk", "scarlet-witch", "gamora", "mantis",
        # Publishing
        "stan-lee", "ms-marvel", "robbie-robertson", "jjj",
        # Power
        "thor", "captain-marvel", "mbaku", "sentry",
        # Interface
        "friday", "wasp",
        # Finance
        "black-panther",
        # Scheduling
        "doctor-strange",
        # Workshop
        "rocket", "workshop-foreman",
        # Operations
        "captain-america", "shang-chi", "drax", "punisher",
        "elektra", "ghost-rider", "valkyrie", "nick-fury-jr",
        "yelena", "kate-bishop", "nova",
        # Vision
        "vision",
        # Chronicle
        "wong",
        # Health/Shuri
        "shuri",
        # Heimdall
        "heimdall",
    ]


def ensure_all_agents_registered() -> None:
    """
    Pre-warm the singleton registry for every known agent.
    Call once at startup (optional — get_agent_catalyst is lazy).
    """
    for agent_id in all_agent_ids():
        get_agent_catalyst(agent_id)
    logger.info("AgentCatalyst: %d agents registered", len(all_agent_ids()))
