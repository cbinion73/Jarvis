from __future__ import annotations

"""
JARVIS Agent Work System — Epic 2 (Autonomous Loop)
=====================================================
Persistent work-item tracking so agents can self-start, propose ideas,
get approval, implement, track effectiveness, and report at standup.

Lifecycle:
  DREAMED → RESEARCHING → PROPOSED → APPROVED → IMPLEMENTING → TRACKING → CLOSED

Storage:
  ~/.jarvis/agents/<agent_id>/work.jsonl   — one record per work item
"""

import json
import logging
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .persistence import append_jsonl, atomic_write_jsonl

logger = logging.getLogger("jarvis.agent_work")

# ---------------------------------------------------------------------------
# Catalyst sync helper — mirrors every agent work event into CatalystDB.
# Fire-and-forget: never raises, never blocks the calling thread.
# ---------------------------------------------------------------------------

def _catalyst_sync(item: "WorkItem", event: str) -> None:
    """
    Mirror an agent work item state change into CatalystDB.
    Called after every mutation in AgentWorkStore.

    Mapping:
      dreamed      → raw_signal (LOW)
      researching  → raw_signal (STANDARD)
      proposed     → raw_signal (STANDARD)
      approved     → raw_signal (CRITICAL) + catalyst_task + decision record
      rejected     → raw_signal (STANDARD)
      implementing → raw_signal (STANDARD) + commitment record
      tracking     → raw_signal (LOW)
      closed       → raw_signal (LOW)
    """
    try:
        from .catalyst_db import get_catalyst_db
        db = get_catalyst_db()
        if db is None:
            return

        crit_map = {
            "dreamed":      "LOW",
            "researching":  "STANDARD",
            "proposed":     "STANDARD",
            "approved":     "CRITICAL",
            "rejected":     "STANDARD",
            "implementing": "STANDARD",
            "tracking":     "LOW",
            "closed":       "LOW",
        }
        # Also escalate by item priority
        priority_crit = (
            "CRITICAL" if item.priority <= 2
            else ("LOW" if item.priority >= 8 else "STANDARD")
        )
        crit = "CRITICAL" if "CRITICAL" in (crit_map.get(event, "STANDARD"), priority_crit) else priority_crit

        signal = db.ingest_signal(
            user_id="chris",
            signal_type="agent_work",
            content=f"[{item.agent_id}] {event}: {item.title}",
            external_id=f"agent_work:{item.work_id}:{event}",
            source_metadata={
                "work_id":  item.work_id,
                "agent_id": item.agent_id,
                "domain":   item.domain,
                "status":   item.status,
                "event":    event,
                "priority": item.priority,
                "tags":     item.tags,
            },
            criticality=crit,
        )
        signal_id = (signal or {}).get("id")

        # approved → create a catalyst_task so it appears in the Tasks pane
        if event == "approved" and signal_id:
            task_pri = "high" if item.priority <= 2 else ("low" if item.priority >= 8 else "medium")
            db.create_task(
                user_id="chris",
                title=item.title,
                task_type="agent_approved",
                source_signal_id=signal_id,
            )
            # Record the approval as a decision
            db.record_decision(
                user_id="chris",
                signal_id=signal_id,
                description=f"Approved agent work item: {item.title}",
                reasoning=(item.proposal or item.idea)[:400],
                confidence=0.9,
            )

        # implementing → create a commitment so it appears in the Commitments panel
        if event == "implementing" and signal_id:
            db.create_commitment(
                user_id="chris",
                signal_id=signal_id,
                description=f"{item.agent_id} implementing: {item.title}",
                responsible_party=item.agent_id,
                confidence=0.85,
            )

    except Exception:
        pass  # Catalyst is additive — agent work continues even if sync fails


# ---------------------------------------------------------------------------
# Status constants
# ---------------------------------------------------------------------------

STATUS_DREAMED       = "dreamed"
STATUS_RESEARCHING   = "researching"
STATUS_PROPOSED      = "proposed"
STATUS_APPROVED      = "approved"
STATUS_IMPLEMENTING  = "implementing"
STATUS_TRACKING      = "tracking"
STATUS_CLOSED        = "closed"

ACTIVE_STATUSES = {
    STATUS_DREAMED,
    STATUS_RESEARCHING,
    STATUS_PROPOSED,
    STATUS_APPROVED,
    STATUS_IMPLEMENTING,
    STATUS_TRACKING,
}

STATUS_ORDER = [
    STATUS_DREAMED,
    STATUS_RESEARCHING,
    STATUS_PROPOSED,
    STATUS_APPROVED,
    STATUS_IMPLEMENTING,
    STATUS_TRACKING,
    STATUS_CLOSED,
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# WorkItem dataclass
# ---------------------------------------------------------------------------

@dataclass
class WorkItem:
    work_id: str
    agent_id: str
    domain: str                  # e.g. "passive-income", "growth", "household"
    title: str
    status: str = STATUS_DREAMED

    # Content at each stage
    idea: str = ""               # The original inspiration / hypothesis
    research: str = ""           # Research notes, links, numbers
    proposal: str = ""           # Formal pitch to Chris (who/what/why/cost/return)
    implementation: str = ""     # Steps taken, links deployed, code written
    metrics: str = ""            # Measurements collected after launch
    effectiveness_score: float = 0.0  # 0–10; auto-updated by tracking loop

    # Metadata
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)
    created_date: str = field(default_factory=_today)  # YYYY-MM-DD for easy filtering
    approved_at: str = ""
    closed_at: str = ""
    approved_by: str = ""
    rejection_reason: str = ""
    tags: list[str] = field(default_factory=list)
    priority: int = 5            # 1 = highest, 10 = lowest
    approval_request_id: str = ""  # Links to ApprovalQueue request


# ---------------------------------------------------------------------------
# AgentWorkStore
# ---------------------------------------------------------------------------

class AgentWorkStore:
    """
    Per-agent persistent work item store.
    All methods are thread-safe.  Backed by JSONL files.
    """

    def __init__(self, agent_id: str, base_dir: Path | None = None) -> None:
        self.agent_id = agent_id
        if base_dir is None:
            base_dir = Path.home() / ".jarvis" / "agents" / agent_id
        self._path = base_dir / "work.jsonl"
        self._state_log_path = base_dir / "work_state_log.jsonl"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._items: list[WorkItem] = self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> list[WorkItem]:
        if not self._path.exists():
            return self._load_from_state_log()
        items: list[WorkItem] = []
        try:
            for line in self._path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    # Fill any missing keys so old records don't crash
                    wi = WorkItem(
                        work_id=data.get("work_id", str(uuid.uuid4())),
                        agent_id=data.get("agent_id", self.agent_id),
                        domain=data.get("domain", "general"),
                        title=data.get("title", ""),
                        status=data.get("status", STATUS_DREAMED),
                        idea=data.get("idea", ""),
                        research=data.get("research", ""),
                        proposal=data.get("proposal", ""),
                        implementation=data.get("implementation", ""),
                        metrics=data.get("metrics", ""),
                        effectiveness_score=float(data.get("effectiveness_score", 0.0)),
                        created_at=data.get("created_at", _now_iso()),
                        updated_at=data.get("updated_at", _now_iso()),
                        created_date=data.get("created_date", _today()),
                        approved_at=data.get("approved_at", ""),
                        closed_at=data.get("closed_at", ""),
                        approved_by=data.get("approved_by", ""),
                        rejection_reason=data.get("rejection_reason", ""),
                        tags=data.get("tags", []),
                        priority=int(data.get("priority", 5)),
                        approval_request_id=data.get("approval_request_id", ""),
                    )
                    items.append(wi)
                except Exception:
                    pass
        except OSError:
            return self._load_from_state_log()
        return items or self._load_from_state_log()

    def _save(self) -> None:
        try:
            atomic_write_jsonl(self._path, [asdict(item) for item in self._items])
            append_jsonl(
                self._state_log_path,
                {
                    "saved_at": _now_iso(),
                    "records": [asdict(item) for item in self._items],
                },
            )
        except OSError as exc:
            logger.warning("[%s] Failed to save work store: %s", self.agent_id, exc)

    def _load_from_state_log(self) -> list[WorkItem]:
        if not self._state_log_path.exists():
            return []
        try:
            latest: list[WorkItem] = []
            for line in self._state_log_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                records = payload.get("records")
                if not isinstance(records, list):
                    continue
                candidate: list[WorkItem] = []
                for data in records:
                    if not isinstance(data, dict):
                        continue
                    try:
                        candidate.append(
                            WorkItem(
                                work_id=data.get("work_id", str(uuid.uuid4())),
                                agent_id=data.get("agent_id", self.agent_id),
                                domain=data.get("domain", "general"),
                                title=data.get("title", ""),
                                status=data.get("status", STATUS_DREAMED),
                                idea=data.get("idea", ""),
                                research=data.get("research", ""),
                                proposal=data.get("proposal", ""),
                                implementation=data.get("implementation", ""),
                                metrics=data.get("metrics", ""),
                                effectiveness_score=float(data.get("effectiveness_score", 0.0)),
                                created_at=data.get("created_at", _now_iso()),
                                updated_at=data.get("updated_at", _now_iso()),
                                created_date=data.get("created_date", _today()),
                                approved_at=data.get("approved_at", ""),
                                closed_at=data.get("closed_at", ""),
                                approved_by=data.get("approved_by", ""),
                                rejection_reason=data.get("rejection_reason", ""),
                                tags=data.get("tags", []),
                                priority=int(data.get("priority", 5)),
                                approval_request_id=data.get("approval_request_id", ""),
                            )
                        )
                    except Exception:
                        continue
                latest = candidate
            return latest
        except OSError:
            return []

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    def _touch(self, item: WorkItem) -> None:
        item.updated_at = _now_iso()

    def dream_idea(
        self,
        title: str,
        idea: str,
        domain: str = "general",
        tags: list[str] | None = None,
        priority: int = 5,
    ) -> WorkItem:
        """Create a new WorkItem in DREAMED status."""
        with self._lock:
            item = WorkItem(
                work_id=str(uuid.uuid4()),
                agent_id=self.agent_id,
                domain=domain,
                title=title,
                status=STATUS_DREAMED,
                idea=idea,
                tags=tags or [],
                priority=priority,
            )
            self._items.append(item)
            self._save()
            logger.info("[%s] Dreamed: %s", self.agent_id, title[:60])
        _catalyst_sync(item, "dreamed")
        return item

    def advance_to_research(self, work_id: str, research_notes: str) -> WorkItem | None:
        with self._lock:
            item = self._find(work_id)
            if item is None:
                return None
            item.status = STATUS_RESEARCHING
            item.research = research_notes
            self._touch(item)
            self._save()
        _catalyst_sync(item, "researching")
        return item

    def submit_proposal(self, work_id: str, proposal_text: str) -> WorkItem | None:
        with self._lock:
            item = self._find(work_id)
            if item is None:
                return None
            item.status = STATUS_PROPOSED
            item.proposal = proposal_text
            self._touch(item)
            self._save()
        _catalyst_sync(item, "proposed")
        return item

    def mark_approved(self, work_id: str, approved_by: str = "Chris") -> WorkItem | None:
        with self._lock:
            item = self._find(work_id)
            if item is None:
                return None
            item.status = STATUS_APPROVED
            item.approved_by = approved_by
            item.approved_at = _now_iso()
            self._touch(item)
            self._save()
        _catalyst_sync(item, "approved")
        return item

    def mark_rejected(self, work_id: str, reason: str = "") -> WorkItem | None:
        with self._lock:
            item = self._find(work_id)
            if item is None:
                return None
            item.status = STATUS_CLOSED
            item.rejection_reason = reason
            item.closed_at = _now_iso()
            self._touch(item)
            self._save()
        _catalyst_sync(item, "rejected")
        return item

    def start_implementing(self, work_id: str, implementation_notes: str = "") -> WorkItem | None:
        with self._lock:
            item = self._find(work_id)
            if item is None:
                return None
            item.status = STATUS_IMPLEMENTING
            if implementation_notes:
                item.implementation = implementation_notes
            self._touch(item)
            self._save()
        _catalyst_sync(item, "implementing")
        return item

    def log_result(
        self,
        work_id: str,
        metrics: str,
        effectiveness_score: float = 0.0,
        move_to_tracking: bool = True,
    ) -> WorkItem | None:
        with self._lock:
            item = self._find(work_id)
            if item is None:
                return None
            item.metrics = metrics
            item.effectiveness_score = effectiveness_score
            if move_to_tracking:
                item.status = STATUS_TRACKING
            self._touch(item)
            self._save()
        _catalyst_sync(item, "tracking")
        return item

    def close(self, work_id: str, final_metrics: str = "") -> WorkItem | None:
        with self._lock:
            item = self._find(work_id)
            if item is None:
                return None
            item.status = STATUS_CLOSED
            item.closed_at = _now_iso()
            if final_metrics:
                item.metrics = final_metrics
            self._touch(item)
            self._save()
        _catalyst_sync(item, "closed")
        return item

    def update_metrics(self, work_id: str, metrics: str, score: float) -> WorkItem | None:
        with self._lock:
            item = self._find(work_id)
            if item is None:
                return None
            item.metrics = metrics
            item.effectiveness_score = score
            self._touch(item)
            self._save()
            return item

    def link_approval(self, work_id: str, approval_request_id: str) -> WorkItem | None:
        with self._lock:
            item = self._find(work_id)
            if item is None:
                return None
            item.approval_request_id = approval_request_id
            self._touch(item)
            self._save()
            return item

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def _find(self, work_id: str) -> WorkItem | None:
        for item in self._items:
            if item.work_id == work_id:
                return item
        return None

    def get(self, work_id: str) -> WorkItem | None:
        with self._lock:
            return self._find(work_id)

    def get_active(self) -> list[WorkItem]:
        with self._lock:
            return [i for i in self._items if i.status in ACTIVE_STATUSES]

    def get_by_status(self, status: str) -> list[WorkItem]:
        with self._lock:
            return [i for i in self._items if i.status == status]

    def get_by_domain(self, domain: str) -> list[WorkItem]:
        with self._lock:
            return [i for i in self._items if i.domain == domain]

    def get_recent(self, limit: int = 10) -> list[WorkItem]:
        with self._lock:
            return list(reversed(self._items[-max(1, limit):]))

    def get_todays_dreams(self) -> list[WorkItem]:
        today = _today()
        with self._lock:
            return [i for i in self._items if i.created_date == today and i.status == STATUS_DREAMED]

    def get_proposed(self) -> list[WorkItem]:
        return self.get_by_status(STATUS_PROPOSED)

    def get_approved(self) -> list[WorkItem]:
        return self.get_by_status(STATUS_APPROVED)

    def count_by_status(self) -> dict[str, int]:
        with self._lock:
            counts: dict[str, int] = {}
            for item in self._items:
                counts[item.status] = counts.get(item.status, 0) + 1
            return counts

    def get_standup_summary(self) -> dict[str, Any]:
        """
        Return a structured summary of this agent's recent work for standup use.
        Covers: completed since yesterday, active items, what's needed.
        """
        from datetime import timedelta
        cutoff = (
            datetime.now(timezone.utc) - timedelta(hours=26)
        ).isoformat()

        with self._lock:
            recently_advanced = [
                i for i in self._items
                if i.updated_at >= cutoff and i.status not in (STATUS_DREAMED,)
            ]
            active = [i for i in self._items if i.status in ACTIVE_STATUSES]
            needs_approval = [i for i in self._items if i.status == STATUS_PROPOSED]
            tracking = [i for i in self._items if i.status == STATUS_TRACKING]

        return {
            "agent_id": self.agent_id,
            "recently_advanced": [asdict(i) for i in recently_advanced[:5]],
            "active_count": len(active),
            "needs_approval": [asdict(i) for i in needs_approval[:3]],
            "tracking_count": len(tracking),
            "status_counts": self.count_by_status(),
        }

    def all_items(self) -> list[WorkItem]:
        with self._lock:
            return list(self._items)


# ---------------------------------------------------------------------------
# Global registry — one store per agent, lazily created
# ---------------------------------------------------------------------------

_stores: dict[str, AgentWorkStore] = {}
_stores_lock = threading.Lock()


def get_work_store(agent_id: str) -> AgentWorkStore:
    """Return the singleton AgentWorkStore for agent_id."""
    with _stores_lock:
        if agent_id not in _stores:
            _stores[agent_id] = AgentWorkStore(agent_id)
        return _stores[agent_id]


def _discover_stores() -> None:
    """Scan ~/.jarvis/agents/ and lazy-load any agent work stores found on disk."""
    base = Path.home() / ".jarvis" / "agents"
    if not base.exists():
        return
    for agent_dir in base.iterdir():
        if not agent_dir.is_dir():
            continue
        work_file = agent_dir / "work.jsonl"
        if work_file.exists() and agent_dir.name not in _stores:
            _stores[agent_dir.name] = AgentWorkStore(agent_dir.name, base_dir=agent_dir)


def get_all_stores() -> dict[str, AgentWorkStore]:
    """Return snapshot of all agent work stores, including those discovered on disk."""
    with _stores_lock:
        _discover_stores()
        return dict(_stores)


def get_all_proposed() -> list[dict]:
    """Return all PROPOSED items across all agents (for approval dashboard)."""
    results = []
    with _stores_lock:
        stores = list(_stores.values())
    for store in stores:
        for item in store.get_proposed():
            results.append(asdict(item))
    return results
