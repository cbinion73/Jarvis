"""
catalyst_bridge.py — RETIRED (external Catalyst app integration)
=================================================================
The external Catalyst app has been consolidated into JARVIS.
Work intelligence is now native:  jarvis/work_intelligence.py
Persistent storage is now native: jarvis/catalyst_db.py (PostgreSQL)
Background workers:               jarvis/wi_workers.py

What remains active in this file
---------------------------------
- ``extract_action_items()``   — pure-Python regex helper, still used by
  the /api/catalyst/extract-actions endpoint in service.py.

Everything else in this module (CatalystBridge, MantisWorkflow,
init_catalyst_bridge, get_catalyst_bridge, get_mantis) is inert:
the bridge is no longer initialised at startup and the corresponding
service endpoints return HTTP 410 Gone.

Do NOT delete this file yet — extract_action_items is still imported
by service.py.  When that endpoint is migrated to work_intelligence.py
this file can be safely removed.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .persistence import append_jsonl, atomic_write_json, atomic_write_jsonl

logger = logging.getLogger("jarvis.catalyst_bridge")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _expires_iso(hours: int = 24) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


# ---------------------------------------------------------------------------
# CatalystContext dataclass
# ---------------------------------------------------------------------------

@dataclass
class CatalystContext:
    """A structured context packet passed between JARVIS and Catalyst."""

    context_id: str           # uuid4
    source: str               # "jarvis" | "catalyst"
    context_type: str         # "briefing" | "meeting_prep" | "decision" | "action_pack" | "signal"
    title: str
    body: str                 # main context text
    structured_data: dict     # type-specific structured payload
    actor_id: str             # "chris"
    created_at: str           # ISO
    expires_at: str           # ISO (most contexts expire in 24h)
    tags: list[str] = field(default_factory=list)
    priority: str = "normal"  # "low" | "normal" | "high"
    action_required: bool = False
    catalyst_view: str = "inbox"  # "inbox" | "today" | "projects" | "decisions"
    sent: bool = False        # True once delivered to Catalyst

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CatalystContext":
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)


# ---------------------------------------------------------------------------
# Action item extraction
# ---------------------------------------------------------------------------

def extract_action_items(text: str) -> list[dict[str, str]]:
    """
    Simple regex-based action item extraction from conversation text.
    No LLM needed for basic patterns.

    Patterns:
    - "remind me to {X}"    → type: reminder
    - "I need to {X}"       → type: task
    - "I'll {X}"            → type: commitment
    - "can you {X}"         → type: request
    - "add to list: {X}"    → type: list_item
    - "todo: {X}"           → type: task
    - "I should {X}"        → type: task
    - "we need to {X}"      → type: task
    - "action: {X}"         → type: task
    - "task: {X}"           → type: task

    Returns list of {"text": str, "type": str, "raw": str}
    """
    patterns: list[tuple[str, str]] = [
        (r"remind(?:ing)? me to (.+?)(?:\.|$|\n)", "reminder"),
        (r"I need to (.+?)(?:\.|$|\n)", "task"),
        (r"I'll (.+?)(?:\.|$|\n)", "commitment"),
        (r"can you (.+?)(?:\.|$|\n)", "request"),
        (r"add to (?:my )?list[:\s]+(.+?)(?:\.|$|\n)", "list_item"),
        (r"todo[:\s]+(.+?)(?:\.|$|\n)", "task"),
        (r"task[:\s]+(.+?)(?:\.|$|\n)", "task"),
        (r"action[:\s]+(.+?)(?:\.|$|\n)", "task"),
        (r"I should (.+?)(?:\.|$|\n)", "task"),
        (r"we need to (.+?)(?:\.|$|\n)", "task"),
    ]

    results: list[dict[str, str]] = []
    seen: set[str] = set()

    for pattern, action_type in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
            raw = match.group(0).strip()
            extracted = match.group(1).strip().rstrip(".,;")
            # Deduplicate by normalised extracted text
            key = extracted.lower()
            if key and key not in seen:
                seen.add(key)
                results.append({"text": extracted, "type": action_type, "raw": raw})

    return results


# ---------------------------------------------------------------------------
# CatalystBridge
# ---------------------------------------------------------------------------

class CatalystBridge:
    """
    Manages bidirectional context flow between JARVIS and Catalyst.

    Storage:
      ~/.jarvis/catalyst/contexts/            — one JSON file per CatalystContext
      ~/.jarvis/catalyst/pending_handoffs.jsonl — contexts awaiting Catalyst pickup
    """

    ROOT = Path.home() / ".jarvis" / "catalyst"

    def __init__(self, catalyst_client: Any = None) -> None:
        # catalyst_client: CatalystStore or CatalystSupport from catalyst.py
        self._client = catalyst_client
        self._contexts_dir = self.ROOT / "contexts"
        self._pending_path = self.ROOT / "pending_handoffs.jsonl"
        self._contexts_dir.mkdir(parents=True, exist_ok=True)
        self._pending_path.parent.mkdir(parents=True, exist_ok=True)
        if not self._pending_path.exists():
            self._pending_path.write_text("", encoding="utf-8")

    def _pending_log_path(self) -> Path:
        return self.ROOT / "pending_handoffs_log.jsonl"

    def _context_path(self, context_id: str) -> Path:
        return self._contexts_dir / f"{context_id}.json"

    def _context_log_path(self, context_id: str) -> Path:
        return self._contexts_dir / f"{context_id}_log.jsonl"

    def _load_pending_records_from_log(self) -> list[dict[str, Any]]:
        log_path = self._pending_log_path()
        if not log_path.exists():
            return []
        latest: list[dict[str, Any]] = []
        try:
            for line in log_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                payload = json.loads(line)
                items = payload.get("items")
                if isinstance(items, list):
                    latest = [item for item in items if isinstance(item, dict)]
        except (OSError, json.JSONDecodeError):
            return []
        return latest

    def _persist_pending_records(self, items: list[dict[str, Any]]) -> None:
        append_jsonl(
            self._pending_log_path(),
            {
                "saved_at": _now_iso(),
                "items": items,
            },
            ensure_ascii=False,
        )
        atomic_write_jsonl(self._pending_path, items, ensure_ascii=False)

    def _load_context_payload(self, context_id: str) -> dict[str, Any] | None:
        path = self._context_path(context_id)
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data
            except (OSError, json.JSONDecodeError):
                pass
        log_path = self._context_log_path(context_id)
        if not log_path.exists():
            return None
        latest: dict[str, Any] | None = None
        try:
            for line in log_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                entry = json.loads(line)
                payload = entry.get("data")
                if isinstance(payload, dict):
                    latest = payload
        except (OSError, json.JSONDecodeError):
            return None
        return latest

    def _persist_context_payload(self, ctx: CatalystContext) -> None:
        payload = ctx.to_dict()
        append_jsonl(
            self._context_log_path(ctx.context_id),
            {
                "saved_at": _now_iso(),
                "data": payload,
            },
            ensure_ascii=False,
        )
        atomic_write_json(self._context_path(ctx.context_id), payload, ensure_ascii=False)

    # -----------------------------------------------------------------------
    # JARVIS → Catalyst
    # -----------------------------------------------------------------------

    def package_morning_handoff(
        self,
        briefing_packet: dict,
        actor_id: str = "chris",
    ) -> CatalystContext:
        """
        Takes the JARVIS morning briefing and packages it as a Catalyst context.
        Includes today's priorities, pending decisions, and open loops.
        """
        briefing_items = briefing_packet.get("briefing_items", [])
        needs_items = briefing_packet.get("needs_items", [])
        drift_items = briefing_packet.get("drift_items", [])
        memory_context = briefing_packet.get("memory_context", "")

        priorities = [item.get("text", "") for item in briefing_items if item.get("priority") == "high"]
        open_loops = [item.get("text", "") for item in needs_items]
        drift_notes = [item.get("text", "") for item in drift_items]

        body_lines = ["# JARVIS Morning Handoff\n"]
        if memory_context:
            body_lines.append(f"**Memory Context:**\n{memory_context}\n")
        if priorities:
            body_lines.append("**Today's High-Priority Items:**")
            body_lines.extend(f"- {p}" for p in priorities)
            body_lines.append("")
        if open_loops:
            body_lines.append("**Open Loops / Action Needed:**")
            body_lines.extend(f"- {l}" for l in open_loops)
            body_lines.append("")
        if drift_notes:
            body_lines.append("**Drift / Watch Points:**")
            body_lines.extend(f"- {d}" for d in drift_notes)
            body_lines.append("")

        ctx = CatalystContext(
            context_id=str(uuid.uuid4()),
            source="jarvis",
            context_type="briefing",
            title=f"Morning Handoff — {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
            body="\n".join(body_lines).strip(),
            structured_data={
                "briefing_items": briefing_items,
                "needs_items": needs_items,
                "drift_items": drift_items,
                "priorities": priorities,
                "open_loops": open_loops,
                "queue_depth": briefing_packet.get("queue_depth", 0),
            },
            actor_id=actor_id,
            created_at=_now_iso(),
            expires_at=_expires_iso(24),
            tags=["morning", "briefing", "handoff"],
            priority="high",
            action_required=bool(open_loops),
            catalyst_view="today",
        )
        self._persist_context(ctx)
        self._enqueue_handoff(ctx)
        return ctx

    def package_meeting_prep(
        self,
        event: dict,
        actor_id: str = "chris",
    ) -> CatalystContext:
        """
        Before a meeting, package relevant context for Catalyst.
        Includes attendee notes, prior meeting context, open loops, and agenda items.
        event: calendar event dict (title, start, end, attendees, description)
        """
        title = str(event.get("title", event.get("summary", "Meeting"))).strip()
        start = str(event.get("start", "")).strip()
        end = str(event.get("end", "")).strip()
        attendees = event.get("attendees", [])
        description = str(event.get("description", "")).strip()

        # Pull meeting prep from CatalystSupport if available
        catalyst_prep: dict = {}
        if self._client is not None:
            try:
                support = self._client if hasattr(self._client, "meeting_prep") else None
                if support is not None:
                    signals = support.store.list_signals(limit=5) if hasattr(support, "store") else []
                    signal_titles = [s.get("title", "") for s in signals]
                    catalyst_prep = support.meeting_prep(
                        actor=actor_id,
                        meeting_title=title,
                        open_commitments=[],
                        recent_signals=signal_titles,
                    )
            except Exception:
                logger.debug("Could not run CatalystSupport.meeting_prep", exc_info=True)

        attendee_list = attendees if isinstance(attendees, list) else []
        brief_points = catalyst_prep.get("brief_points", [])
        watch_points = catalyst_prep.get("watch_points", [])
        agenda = catalyst_prep.get("suggested_agenda", [])

        body_lines = [f"# Meeting Prep: {title}\n"]
        if start:
            body_lines.append(f"**When:** {start}" + (f" → {end}" if end else "") + "\n")
        if attendee_list:
            body_lines.append("**Attendees:** " + ", ".join(str(a) for a in attendee_list) + "\n")
        if description:
            body_lines.append(f"**Description:** {description}\n")
        if brief_points:
            body_lines.append("**Brief Points:**")
            body_lines.extend(f"- {p}" for p in brief_points)
            body_lines.append("")
        if watch_points:
            body_lines.append("**Watch Points:**")
            body_lines.extend(f"- {w}" for w in watch_points)
            body_lines.append("")
        if agenda:
            body_lines.append("**Suggested Agenda:**")
            body_lines.extend(f"- {a}" for a in agenda)
            body_lines.append("")

        ctx = CatalystContext(
            context_id=str(uuid.uuid4()),
            source="jarvis",
            context_type="meeting_prep",
            title=f"Meeting Prep: {title}",
            body="\n".join(body_lines).strip(),
            structured_data={
                "event": event,
                "attendees": attendee_list,
                "brief_points": brief_points,
                "watch_points": watch_points,
                "suggested_agenda": agenda,
                "catalyst_prep_run_id": catalyst_prep.get("run_id", ""),
            },
            actor_id=actor_id,
            created_at=_now_iso(),
            expires_at=_expires_iso(6),
            tags=["meeting", "prep", "calendar"],
            priority="high",
            action_required=False,
            catalyst_view="today",
        )
        self._persist_context(ctx)
        self._enqueue_handoff(ctx)
        return ctx

    def package_action_items(
        self,
        conversation_text: str,
        extracted_actions: list[dict],
    ) -> CatalystContext:
        """
        After a JARVIS conversation, package action items for Catalyst.
        extracted_actions: [{"text": str, "owner": str, "due": str, "project": str}]
        """
        action_lines = []
        for item in extracted_actions:
            text = str(item.get("text", "")).strip()
            if not text:
                continue
            owner = str(item.get("owner", "chris")).strip()
            due = str(item.get("due", "")).strip()
            project = str(item.get("project", "")).strip()
            line = f"- {text}"
            if owner and owner.lower() != "chris":
                line += f" (@{owner})"
            if due:
                line += f" [due: {due}]"
            if project:
                line += f" #{project}"
            action_lines.append(line)

        body_lines = ["# Action Pack from Conversation\n"]
        if action_lines:
            body_lines.append("**Actions:**")
            body_lines.extend(action_lines)
            body_lines.append("")
        # Include a short excerpt from the conversation
        excerpt = conversation_text[:400].strip()
        if excerpt:
            body_lines.append(f"**Conversation excerpt:**\n> {excerpt}...")

        ctx = CatalystContext(
            context_id=str(uuid.uuid4()),
            source="jarvis",
            context_type="action_pack",
            title=f"Action Pack — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}",
            body="\n".join(body_lines).strip(),
            structured_data={
                "actions": extracted_actions,
                "conversation_excerpt": conversation_text[:800],
                "action_count": len(extracted_actions),
            },
            actor_id="chris",
            created_at=_now_iso(),
            expires_at=_expires_iso(48),
            tags=["actions", "conversation", "inbox"],
            priority="normal" if len(extracted_actions) < 3 else "high",
            action_required=True,
            catalyst_view="inbox",
        )
        self._persist_context(ctx)
        self._enqueue_handoff(ctx)
        return ctx

    def package_decision_support(
        self,
        decision_topic: str,
        context: dict,
    ) -> CatalystContext:
        """
        When Chris faces a decision, assemble relevant context from JARVIS memory
        and hand to Catalyst for deep work.
        """
        factors = context.get("factors", [])
        options = context.get("options", [])
        constraints = context.get("constraints", [])
        background = str(context.get("background", "")).strip()
        urgency = str(context.get("urgency", "normal")).strip()

        body_lines = [f"# Decision Support: {decision_topic}\n"]
        if background:
            body_lines.append(f"**Background:**\n{background}\n")
        if factors:
            body_lines.append("**Key Factors:**")
            body_lines.extend(f"- {f}" for f in factors)
            body_lines.append("")
        if options:
            body_lines.append("**Options:**")
            body_lines.extend(f"- {o}" for o in options)
            body_lines.append("")
        if constraints:
            body_lines.append("**Constraints:**")
            body_lines.extend(f"- {c}" for c in constraints)
            body_lines.append("")
        body_lines.append("*Packaged by Mantis for deep work in Catalyst.*")

        ctx = CatalystContext(
            context_id=str(uuid.uuid4()),
            source="jarvis",
            context_type="decision",
            title=f"Decision: {decision_topic}",
            body="\n".join(body_lines).strip(),
            structured_data={
                "decision_topic": decision_topic,
                "factors": factors,
                "options": options,
                "constraints": constraints,
                "background": background,
                "urgency": urgency,
            },
            actor_id="chris",
            created_at=_now_iso(),
            expires_at=_expires_iso(72),
            tags=["decision", "deep-work"],
            priority="high" if urgency == "urgent" else "normal",
            action_required=True,
            catalyst_view="decisions",
        )
        self._persist_context(ctx)
        self._enqueue_handoff(ctx)
        return ctx

    # -----------------------------------------------------------------------
    # Catalyst → JARVIS
    # -----------------------------------------------------------------------

    def receive_completion(self, completion_data: dict) -> None:
        """
        Catalyst calls this when a task/project is marked complete.
        JARVIS updates memory and can surface the win in the briefing.
        """
        task_id = str(completion_data.get("task_id", completion_data.get("work_id", ""))).strip()
        task_title = str(completion_data.get("title", "")).strip()
        completed_at = str(completion_data.get("completed_at", _now_iso())).strip()
        notes = str(completion_data.get("notes", "")).strip()

        logger.info("Catalyst completion received: %s (%s)", task_title or task_id, completed_at)

        # Persist a signal in CatalystSupport if available
        if self._client is not None:
            try:
                support = self._client if hasattr(self._client, "capture_signal") else None
                if support is not None:
                    support.capture_signal(
                        actor="chris",
                        source="catalyst-completion",
                        title=f"Completed: {task_title}" if task_title else "Task completed",
                        content=notes or f"Work item {task_id} marked complete in Catalyst.",
                        tags=["catalyst", "completion", "win"],
                        work_id=task_id,
                    )
            except Exception:
                logger.debug("Could not capture completion signal", exc_info=True)

        # Persist a local completion record
        record = {
            "event": "completion",
            "task_id": task_id,
            "title": task_title,
            "completed_at": completed_at,
            "notes": notes,
            "received_at": _now_iso(),
        }
        self._append_event_log(record)

    def receive_project_update(self, project_data: dict) -> None:
        """Catalyst pushes project status. Update pipeline state memory."""
        project_id = str(project_data.get("project_id", "")).strip()
        project_name = str(project_data.get("name", project_data.get("title", ""))).strip()
        status = str(project_data.get("status", "active")).strip()

        logger.info("Catalyst project update: %s → %s", project_name or project_id, status)

        if self._client is not None:
            try:
                support = self._client if hasattr(self._client, "update_pipeline_state") else None
                if support is not None and project_id:
                    support.update_pipeline_state({
                        "projects": {
                            project_id: {
                                "name": project_name,
                                "status": status,
                                "last_update": _now_iso(),
                            }
                        }
                    })
            except Exception:
                logger.debug("Could not update pipeline state", exc_info=True)

        record = {
            "event": "project_update",
            "project_id": project_id,
            "name": project_name,
            "status": status,
            "received_at": _now_iso(),
            "raw": project_data,
        }
        self._append_event_log(record)

    def receive_signal(self, signal_data: dict) -> None:
        """Catalyst sends a signal needing JARVIS intelligence."""
        title = str(signal_data.get("title", "Signal from Catalyst")).strip()
        content = str(signal_data.get("content", signal_data.get("body", ""))).strip()
        tags = list(signal_data.get("tags", []))
        source = str(signal_data.get("source", "catalyst")).strip()

        logger.info("Catalyst signal received: %s", title)

        if self._client is not None:
            try:
                support = self._client if hasattr(self._client, "capture_signal") else None
                if support is not None:
                    support.capture_signal(
                        actor="chris",
                        source=source,
                        title=title,
                        content=content,
                        tags=["catalyst-inbound", *tags],
                    )
            except Exception:
                logger.debug("Could not capture inbound signal", exc_info=True)

        record = {
            "event": "signal",
            "title": title,
            "content": content,
            "tags": tags,
            "source": source,
            "received_at": _now_iso(),
        }
        self._append_event_log(record)

    # -----------------------------------------------------------------------
    # Pending handoffs
    # -----------------------------------------------------------------------

    def get_pending_handoffs(self) -> list[CatalystContext]:
        """Get contexts waiting to be sent to Catalyst."""
        results: list[CatalystContext] = []
        if self._pending_path.exists():
            try:
                lines = self._pending_path.read_text(encoding="utf-8").splitlines()
            except OSError:
                lines = []
        else:
            lines = []
        if not lines:
            lines = [json.dumps(item) for item in self._load_pending_records_from_log()]
        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                ctx = CatalystContext.from_dict(data)
                if not ctx.sent:
                    results.append(ctx)
            except (json.JSONDecodeError, TypeError):
                continue
        return results

    def mark_handoff_sent(self, context_id: str) -> None:
        """Mark a pending handoff as sent so it's no longer returned as pending."""
        if self._pending_path.exists():
            try:
                lines = self._pending_path.read_text(encoding="utf-8").splitlines()
            except OSError:
                lines = []
        else:
            lines = []
        if not lines:
            lines = [json.dumps(item) for item in self._load_pending_records_from_log()]
        updated_records: list[dict[str, Any]] = []
        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                if str(data.get("context_id", "")).strip() == context_id:
                    data["sent"] = True
                if isinstance(data, dict):
                    updated_records.append(data)
            except (json.JSONDecodeError, TypeError):
                continue
        self._persist_pending_records(updated_records)
        # Also update the persisted context file
        data = self._load_context_payload(context_id)
        if data is not None:
            data["sent"] = True
            self._persist_context_payload(CatalystContext.from_dict(data))

    def get_recent_contexts(self, limit: int = 10) -> list[CatalystContext]:
        """Return recent contexts (most recent first), regardless of sent status."""
        ctx_files = sorted(
            self._contexts_dir.glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        results: list[CatalystContext] = []
        for ctx_file in ctx_files[:limit]:
            try:
                data = self._load_context_payload(ctx_file.stem)
                if data is None:
                    continue
                results.append(CatalystContext.from_dict(data))
            except (OSError, json.JSONDecodeError, TypeError):
                continue
        return results

    # -----------------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------------

    def _persist_context(self, ctx: CatalystContext) -> None:
        """Write context to its own JSON file."""
        self._persist_context_payload(ctx)

    def _enqueue_handoff(self, ctx: CatalystContext) -> None:
        """Append context to pending_handoffs.jsonl."""
        items = self._load_pending_records_from_log()
        if not items and self._pending_path.exists():
            try:
                for line in self._pending_path.read_text(encoding="utf-8").splitlines():
                    if not line.strip():
                        continue
                    payload = json.loads(line)
                    if isinstance(payload, dict):
                        items.append(payload)
            except (OSError, json.JSONDecodeError):
                items = []
        items.append(ctx.to_dict())
        self._persist_pending_records(items)

    def _append_event_log(self, record: dict) -> None:
        """Append a Catalyst→JARVIS event to a local log."""
        log_path = self.ROOT / "inbound_events.jsonl"
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")


# ---------------------------------------------------------------------------
# MantisWorkflow
# ---------------------------------------------------------------------------

class MantisWorkflow:
    """
    Mantis (catalyst-personal) orchestrates the JARVIS ↔ Catalyst workflow.

    Mantis's superpower: she senses the energy of the work. She knows what's
    draining vs. alive. She packages work for Catalyst before Chris has to ask.

    Key patterns:
    - "I noticed the weight before you did" — proactive packaging
    - After calendar check: prep meeting context 1 hour before each meeting
    - After morning briefing: package today's Catalyst handoff
    - After conversation: detect and package any mentioned action items
    """

    AGENT_ID = "catalyst-personal"
    AGENT_NAME = "Mantis"

    def __init__(
        self,
        bridge: CatalystBridge,
        scheduler: Any = None,
        memory_store: Any = None,
    ) -> None:
        self._bridge = bridge
        self._scheduler = scheduler
        self._memory = memory_store
        self._last_morning_package: str | None = None  # ISO timestamp
        self._last_meeting_package: str | None = None  # ISO timestamp

    def on_morning_briefing_ready(self, briefing_packet: dict) -> CatalystContext | None:
        """Called by BriefingBuilder. Packages morning handoff for Catalyst."""
        try:
            ctx = self._bridge.package_morning_handoff(briefing_packet, actor_id="chris")
            self._last_morning_package = _now_iso()
            logger.info(
                "Mantis: morning handoff packaged → context_id=%s (%d action loops)",
                ctx.context_id,
                len(ctx.structured_data.get("open_loops", [])),
            )
            return ctx
        except Exception:
            logger.warning("Mantis: could not package morning handoff", exc_info=True)
            return None

    def on_meeting_approaching(
        self,
        event: dict,
        minutes_until: int = 60,
    ) -> CatalystContext | None:
        """Called by Kang/scheduler. Packages meeting prep context."""
        try:
            ctx = self._bridge.package_meeting_prep(event, actor_id="chris")
            self._last_meeting_package = _now_iso()
            meeting_title = str(event.get("title", event.get("summary", "Meeting"))).strip()
            logger.info(
                "Mantis: meeting prep packaged → %s (T-%d min), context_id=%s",
                meeting_title,
                minutes_until,
                ctx.context_id,
            )
            return ctx
        except Exception:
            logger.warning("Mantis: could not package meeting prep", exc_info=True)
            return None

    def on_conversation_complete(self, conversation_text: str) -> list[dict]:
        """
        After a JARVIS conversation, extract action items using simple heuristics.
        If any are found, packages them for Catalyst automatically.

        Returns list of extracted action dicts.
        """
        if not conversation_text or not conversation_text.strip():
            return []

        raw_items = extract_action_items(conversation_text)
        if not raw_items:
            return []

        # Normalise into the richer action dict shape
        actions = [
            {
                "text": item["text"],
                "type": item["type"],
                "owner": "chris",
                "due": "",
                "project": "",
                "raw": item["raw"],
            }
            for item in raw_items
        ]

        try:
            self._bridge.package_action_items(conversation_text, actions)
            logger.info("Mantis: packaged %d action items from conversation", len(actions))
        except Exception:
            logger.warning("Mantis: could not package action items", exc_info=True)

        return actions

    def get_workflow_status(self) -> dict:
        """Status for the Already Working zone in the dashboard."""
        pending = self._bridge.get_pending_handoffs()
        return {
            "agent": self.AGENT_NAME,
            "agent_id": self.AGENT_ID,
            "action": "Workflow intelligence active",
            "pending_handoffs": len(pending),
            "last_morning_package": self._last_morning_package,
            "last_meeting_package": self._last_meeting_package,
            "catalyst_root": str(CatalystBridge.ROOT),
        }


# ---------------------------------------------------------------------------
# Module-level singletons
# ---------------------------------------------------------------------------

_bridge: CatalystBridge | None = None
_mantis: MantisWorkflow | None = None


def init_catalyst_bridge(
    catalyst_client: Any = None,
    scheduler: Any = None,
    memory_store: Any = None,
) -> tuple[CatalystBridge, MantisWorkflow]:
    """
    Initialise the Catalyst bridge and Mantis workflow singletons.
    Safe to call multiple times — subsequent calls are no-ops.
    """
    global _bridge, _mantis

    if _bridge is not None and _mantis is not None:
        return _bridge, _mantis

    _bridge = CatalystBridge(catalyst_client=catalyst_client)
    _mantis = MantisWorkflow(_bridge, scheduler=scheduler, memory_store=memory_store)

    logger.info("CatalystBridge + MantisWorkflow initialised")
    return _bridge, _mantis


def get_catalyst_bridge() -> CatalystBridge | None:
    return _bridge


def get_mantis() -> MantisWorkflow | None:
    return _mantis
