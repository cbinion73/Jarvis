"""D3 / H5: Proactive prompt builder + orchestrator.

Constructs why-now prompts with confidence, source_facts, suggested actions,
snooze/dismiss support, and an audit trail.  All prompts carry a truth label
and are never presented as live data if they are inferred or stale.

H5 adds ProactiveOrchestrator: aggregates calendar, health, approvals, presence
and mode signals into prioritized pending prompts — de-duplicated, never faked.
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .persistence import append_jsonl, atomic_write_json


def _ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


PROMPT_STATES = frozenset({"pending", "delivered", "snoozed", "dismissed", "acted"})
SNOOZE_REASONS = frozenset({"not_now", "busy", "irrelevant", "already_handled"})
DISMISS_REASONS = frozenset({"not_useful", "wrong_time", "wrong_surface", "already_handled", "do_not_repeat"})


@dataclass(slots=True)
class ProactivePrompt:
    prompt_id: str
    actor: str
    title: str
    body: str
    why_now: str
    confidence: float           # 0.0–1.0
    source_facts: list[str]     # list of supporting fact_ids or description strings
    suggested_actions: list[dict]  # [{label, action_type, payload}]
    state: str                  # pending/delivered/snoozed/dismissed/acted
    created_at: str
    delivered_at: str = ""
    snoozed_until: str = ""
    dismissed_at: str = ""
    snooze_reason: str = ""
    dismiss_reason: str = ""
    domain: str = ""
    priority: int = 5           # 1=highest, 10=lowest
    source: str = "inferred"    # observed_fact / inferred / user-requested
    audit_events: list[dict] = field(default_factory=list)


class ProactivePromptStore:
    """Durable store for proactive prompts with JSONL audit trail."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.prompts_path = self.root / "proactive_prompts.json"
        self.audit_path = self.root / "proactive_audit.jsonl"

    def _load(self) -> list[dict]:
        if not self.prompts_path.exists():
            return []
        try:
            payload = json.loads(self.prompts_path.read_text(encoding="utf-8"))
            return payload if isinstance(payload, list) else []
        except Exception:
            return []

    def _save(self, records: list[dict]) -> None:
        atomic_write_json(self.prompts_path, records)

    def _audit(self, event: str, prompt_id: str, extra: dict | None = None) -> None:
        record: dict[str, Any] = {
            "ts": _ts(),
            "event": event,
            "prompt_id": prompt_id,
        }
        if extra:
            record.update(extra)
        try:
            append_jsonl(self.audit_path, record)
        except Exception:
            pass

    def add(self, prompt: ProactivePrompt) -> dict:
        records = self._load()
        payload = asdict(prompt)
        records.append(payload)
        self._save(records)
        self._audit("created", prompt.prompt_id)
        return payload

    def list_pending(self, actor: str | None = None) -> list[dict]:
        records = self._load()
        out = []
        for r in records:
            if r.get("state") not in ("pending", "snoozed"):
                continue
            if actor and r.get("actor") != actor:
                continue
            # Exclude snoozed prompts whose snooze window hasn't expired
            if r.get("state") == "snoozed" and r.get("snoozed_until"):
                if r["snoozed_until"] > _ts():
                    continue
            out.append(r)
        out.sort(key=lambda x: (int(x.get("priority") or 5), x.get("created_at", "")))
        return out

    def mark_delivered(self, prompt_id: str) -> dict | None:
        records = self._load()
        updated = None
        for r in records:
            if r.get("prompt_id") == prompt_id:
                r["state"] = "delivered"
                r["delivered_at"] = _ts()
                updated = r
                break
        if updated:
            self._save(records)
            self._audit("delivered", prompt_id)
        return updated

    def snooze(self, prompt_id: str, snooze_until: str, reason: str = "") -> dict | None:
        if reason and reason not in SNOOZE_REASONS:
            raise ValueError(f"snooze reason must be one of {sorted(SNOOZE_REASONS)}")
        records = self._load()
        updated = None
        for r in records:
            if r.get("prompt_id") == prompt_id:
                r["state"] = "snoozed"
                r["snoozed_until"] = snooze_until
                r["snooze_reason"] = reason
                updated = r
                break
        if updated:
            self._save(records)
            self._audit("snoozed", prompt_id, {"until": snooze_until, "reason": reason})
        return updated

    def dismiss(self, prompt_id: str, reason: str = "") -> dict | None:
        if reason and reason not in DISMISS_REASONS:
            raise ValueError(f"dismiss reason must be one of {sorted(DISMISS_REASONS)}")
        records = self._load()
        updated = None
        for r in records:
            if r.get("prompt_id") == prompt_id:
                r["state"] = "dismissed"
                r["dismissed_at"] = _ts()
                r["dismiss_reason"] = reason
                updated = r
                break
        if updated:
            self._save(records)
            self._audit("dismissed", prompt_id, {"reason": reason})
        return updated

    def mark_acted(self, prompt_id: str) -> dict | None:
        records = self._load()
        updated = None
        for r in records:
            if r.get("prompt_id") == prompt_id:
                r["state"] = "acted"
                updated = r
                break
        if updated:
            self._save(records)
            self._audit("acted", prompt_id)
        return updated


class ProactivePromptBuilder:
    """Construct well-formed ProactivePrompts with validated fields."""

    def build(
        self,
        *,
        actor: str,
        title: str,
        body: str,
        why_now: str,
        confidence: float = 0.7,
        source_facts: list[str] | None = None,
        suggested_actions: list[dict] | None = None,
        domain: str = "",
        priority: int = 5,
        source: str = "inferred",
    ) -> ProactivePrompt:
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence must be 0.0–1.0")
        if priority not in range(1, 11):
            raise ValueError("priority must be 1–10")
        if source not in ("observed_fact", "inferred", "user-requested"):
            raise ValueError("source must be observed_fact, inferred, or user-requested")
        return ProactivePrompt(
            prompt_id=str(uuid.uuid4()),
            actor=actor,
            title=title,
            body=body,
            why_now=why_now,
            confidence=confidence,
            source_facts=source_facts or [],
            suggested_actions=suggested_actions or [],
            state="pending",
            created_at=_ts(),
            domain=domain,
            priority=priority,
            source=source,
        )


# ── H5: Proactive Orchestrator ────────────────────────────────────────────────

class ProactiveOrchestrator:
    """H5: Aggregate signals → produce de-duplicated pending prompts.

    Signal collectors (each fail-open):
      • mode       — suspended mode prompts daily mode reminders
      • approvals  — pending approval queue items
      • calendar   — today's agenda from UnifiedInbox
      • health     — overdue health check-ins from health_state
      • presence   — foreground-active triggers immediate delivery hint

    De-duplication: prompts with the same (actor, domain, title) that are still
    pending or snoozed are not re-created within the same run.

    All data comes from real stores; if a store is unavailable, that signal is
    silently skipped — no fabricated prompts.
    """

    def __init__(self, root: Path | None = None, runtime: Any = None) -> None:
        from pathlib import Path as _Path
        self._root = root or _Path.home() / ".jarvis" / "proactive"
        self._store = ProactivePromptStore(self._root)
        self._builder = ProactivePromptBuilder()
        self._created: list[dict] = []
        self._runtime = runtime  # optional JarvisRuntime for approval access

    def _existing_titles(self, actor: str) -> set[str]:
        """Titles of active (pending/snoozed) prompts — used for de-dup."""
        return {r.get("title", "") for r in self._store.list_pending(actor=actor)}

    def _add(self, actor: str, existing: set[str], **kwargs: Any) -> dict | None:
        title = kwargs.get("title", "")
        if title in existing:
            return None
        p = self._builder.build(actor=actor, **kwargs)
        result = self._store.add(p)
        existing.add(title)
        self._created.append(result)
        return result

    # ── Signal collectors ─────────────────────────────────────────────────────

    def _collect_mode(self, actor: str, existing: set[str]) -> None:
        try:
            from .mode_resolver import get_active_mode_summary
            summary = get_active_mode_summary()
            mode_id = summary.get("mode_id", "normal")
            if mode_id in ("crisis", "sabbath", "travel_light", "recovery"):
                label = summary.get("label", mode_id)
                self._add(
                    actor, existing,
                    title=f"Active mode: {label}",
                    body=(
                        f"JARVIS is currently operating in {label!r} mode. "
                        "Some agents are suspended and notification levels may differ."
                    ),
                    why_now="Mode affects all downstream routing and agent availability.",
                    confidence=1.0,
                    source_facts=[f"mode_id={mode_id}"],
                    suggested_actions=[{"label": "Review mode settings", "action_type": "navigate", "payload": "/modes"}],
                    domain="system",
                    priority=2,
                    source="observed_fact",
                )
        except Exception:
            pass

    def _collect_approvals(self, actor: str, existing: set[str]) -> None:
        try:
            rt = self._runtime
            if rt is None:
                return
            pending = rt.list_pending_approvals()
            for ap in pending[:5]:  # cap at 5 to avoid prompt flooding
                ap_id = ap.get("approval_id", "")
                ap_title = ap.get("title") or ap.get("action_type", "Approval needed")
                self._add(
                    actor, existing,
                    title=f"Approval needed: {ap_title}",
                    body=ap.get("summary") or f"A request is waiting for your approval: {ap_title}",
                    why_now="This action cannot proceed without your approval.",
                    confidence=1.0,
                    source_facts=[f"approval_id={ap_id}"],
                    suggested_actions=[
                        {"label": "Review", "action_type": "navigate", "payload": f"/approvals/{ap_id}"},
                        {"label": "Approve", "action_type": "approve", "payload": {"approval_id": ap_id}},
                    ],
                    domain="approvals",
                    priority=1,
                    source="observed_fact",
                )
        except Exception:
            pass

    def _collect_calendar(self, actor: str, existing: set[str]) -> None:
        try:
            from .unified_inbox import get_unified_inbox
            inbox = get_unified_inbox()
            if inbox is None:
                return
            agenda = inbox.get_todays_agenda()
            events = agenda.get("events", []) if isinstance(agenda, dict) else []
            # Only surface next upcoming event if within 30 minutes
            from datetime import datetime, timezone, timedelta
            now = datetime.now(timezone.utc)
            for ev in events[:10]:
                start_str = ev.get("start") or ev.get("start_time", "")
                if not start_str:
                    continue
                try:
                    start = datetime.fromisoformat(str(start_str))
                    if start.tzinfo is None:
                        start = start.replace(tzinfo=timezone.utc)
                    delta = start - now
                    if timedelta(0) <= delta <= timedelta(minutes=30):
                        ev_title = ev.get("title") or ev.get("summary", "Upcoming event")
                        mins = int(delta.total_seconds() / 60)
                        self._add(
                            actor, existing,
                            title=f"Starting soon: {ev_title}",
                            body=f"'{ev_title}' starts in {mins} minute(s).",
                            why_now=f"Event begins in {mins} min — preparation window.",
                            confidence=0.95,
                            source_facts=[f"calendar_event={ev.get('event_id', ev_title)}"],
                            suggested_actions=[{"label": "Open calendar", "action_type": "navigate", "payload": "/calendar"}],
                            domain="calendar",
                            priority=2,
                            source="observed_fact",
                        )
                except Exception:
                    continue
        except Exception:
            pass

    def _collect_health(self, actor: str, existing: set[str]) -> None:
        try:
            from .longevity_council import load_health_state
            health = load_health_state()
            last_checkin = health.get("last_checkin_at") or health.get("updated_at", "")
            if not last_checkin:
                return
            from datetime import datetime, timezone, timedelta
            last = datetime.fromisoformat(str(last_checkin))
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            overdue_threshold = timedelta(hours=25)
            if datetime.now(timezone.utc) - last > overdue_threshold:
                self._add(
                    actor, existing,
                    title="Health check-in overdue",
                    body="Your last health check-in was more than 25 hours ago.",
                    why_now="Regular check-ins keep your health context current for Three Moves.",
                    confidence=0.85,
                    source_facts=[f"last_checkin={last_checkin}"],
                    suggested_actions=[{"label": "Log check-in", "action_type": "navigate", "payload": "/health/checkin"}],
                    domain="health",
                    priority=4,
                    source="inferred",
                )
        except Exception:
            pass

    def _collect_presence(self, actor: str, existing: set[str]) -> None:
        try:
            from .apple_api import _foreground_active
            if _foreground_active():
                pending = self._store.list_pending(actor=actor)
                if pending:
                    top = pending[0]
                    top_title = top.get("title", "")
                    self._add(
                        actor, existing,
                        title=f"Ready for review: {top_title}",
                        body=(
                            f"You are actively using the app. "
                            f"There is a pending item ready for your attention: {top_title}"
                        ),
                        why_now="Device heartbeat confirms you are in the foreground right now.",
                        confidence=0.9,
                        source_facts=["foreground_active=true"],
                        suggested_actions=[{"label": "Review now", "action_type": "navigate", "payload": "/proactive"}],
                        domain="presence",
                        priority=3,
                        source="observed_fact",
                    )
        except Exception:
            pass

    # ── Public API ────────────────────────────────────────────────────────────

    def run(self, actor: str = "chris") -> dict[str, Any]:
        """Collect all signals and create de-duplicated pending prompts.

        Returns a summary: how many prompts were created and their IDs.
        Never raises — all collector errors are silently swallowed.
        """
        self._created = []
        existing = self._existing_titles(actor)

        self._collect_mode(actor, existing)
        self._collect_approvals(actor, existing)
        self._collect_calendar(actor, existing)
        self._collect_health(actor, existing)
        self._collect_presence(actor, existing)

        return {
            "actor": actor,
            "created_count": len(self._created),
            "created_ids": [p["prompt_id"] for p in self._created],
            "run_at": _ts(),
        }


def get_orchestrator(root: Path | None = None, runtime: Any = None) -> ProactiveOrchestrator:
    """Return a fresh ProactiveOrchestrator (not a singleton — stateless between runs)."""
    return ProactiveOrchestrator(root=root, runtime=runtime)
