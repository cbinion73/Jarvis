from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from .models import AttentionDisposition, InterruptionLevel, TriggerType, UserAttentionState


def _now() -> datetime:
    return datetime.now(UTC)


def _now_iso() -> str:
    return _now().isoformat()


def _parse_iso(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


@dataclass(slots=True)
class PresenceSnapshot:
    attention_state: UserAttentionState
    active_mode: str
    quiet_hours_active: bool
    focus_mode: bool = False
    conversation_active: bool = False
    source: str = "scheduler"
    observed_at: str = field(default_factory=_now_iso)


@dataclass(slots=True)
class EventEnvelope:
    event_id: str
    trigger_type: TriggerType
    topic: str
    source: str
    occurred_at: str
    available_at: str
    status: str
    lane: str = "system"
    urgency: int = 5
    attention_hint: AttentionDisposition = AttentionDisposition.STAGED
    dedupe_key: str = ""
    target_agents: list[str] = field(default_factory=list)
    payload: dict[str, Any] = field(default_factory=dict)
    processed_at: str = ""
    wake_count: int = 0
    wake_summary: list[dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class WakeDecision:
    agent_id: str
    label: str
    trigger_type: TriggerType
    event_id: str
    reason: str
    urgency: int
    attention: AttentionDisposition
    interrupt: bool
    staged: bool
    silent: bool
    source_topic: str
    occurred_at: str


class DurableEventStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.events_path = self.root / "event_bus_events.json"
        self.dedupe_path = self.root / "event_bus_dedupe.json"
        self.log_path = self.root / "event_bus_log.jsonl"

    def list_events(self) -> list[EventEnvelope]:
        if not self.events_path.exists():
            return []
        try:
            payload = json.loads(self.events_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
        items = payload.get("events", []) if isinstance(payload, dict) else []
        events: list[EventEnvelope] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            try:
                events.append(
                    EventEnvelope(
                        event_id=str(item.get("event_id", "")) or str(uuid.uuid4()),
                        trigger_type=TriggerType(str(item.get("trigger_type", TriggerType.SIGNAL.value))),
                        topic=str(item.get("topic", "")),
                        source=str(item.get("source", "")),
                        occurred_at=str(item.get("occurred_at", "")) or _now_iso(),
                        available_at=str(item.get("available_at", "")) or str(item.get("occurred_at", "")) or _now_iso(),
                        status=str(item.get("status", "pending")),
                        lane=str(item.get("lane", "system")),
                        urgency=max(1, min(10, int(item.get("urgency", 5)))),
                        attention_hint=AttentionDisposition(str(item.get("attention_hint", AttentionDisposition.STAGED.value))),
                        dedupe_key=str(item.get("dedupe_key", "")),
                        target_agents=[str(value) for value in list(item.get("target_agents", []) or [])],
                        payload=dict(item.get("payload") or {}),
                        processed_at=str(item.get("processed_at", "")),
                        wake_count=int(item.get("wake_count", 0)),
                        wake_summary=[dict(value) for value in list(item.get("wake_summary", []) or []) if isinstance(value, dict)],
                    )
                )
            except (ValueError, TypeError):
                continue
        return events

    def save_events(self, events: list[EventEnvelope]) -> None:
        payload = {"events": [asdict(item) for item in events]}
        self.events_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def _load_dedupe(self) -> dict[str, str]:
        if not self.dedupe_path.exists():
            return {}
        try:
            payload = json.loads(self.dedupe_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
        if not isinstance(payload, dict):
            return {}
        return {str(key): str(value) for key, value in payload.items() if str(key).strip()}

    def _save_dedupe(self, payload: dict[str, str]) -> None:
        self.dedupe_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def _append_log(self, payload: dict[str, Any]) -> None:
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload) + "\n")

    def publish(self, event: EventEnvelope, *, dedupe_window_seconds: int = 0) -> EventEnvelope | None:
        events = self.list_events()
        dedupe = self._load_dedupe()
        if event.dedupe_key and dedupe_window_seconds > 0:
            seen_at = _parse_iso(dedupe.get(event.dedupe_key, ""))
            occurred_at = _parse_iso(event.occurred_at) or _now()
            if seen_at is not None and occurred_at - seen_at < timedelta(seconds=dedupe_window_seconds):
                return None
            dedupe[event.dedupe_key] = event.occurred_at
            self._save_dedupe(dedupe)
        events.append(event)
        self.save_events(events)
        self._append_log({"kind": "published", "event": asdict(event)})
        return event

    def pending(self, *, now: datetime | None = None, limit: int = 120) -> list[EventEnvelope]:
        current = now or _now()
        items = [
            event
            for event in self.list_events()
            if event.status == "pending" and (_parse_iso(event.available_at) or current) <= current
        ]
        items.sort(key=lambda item: (item.occurred_at, item.event_id))
        return items[: max(1, int(limit))]

    def mark_processed(self, event_id: str, wake_summary: list[dict[str, Any]], *, processed_at: datetime | None = None) -> None:
        current = processed_at or _now()
        events = self.list_events()
        for event in events:
            if event.event_id != event_id:
                continue
            event.status = "processed"
            event.processed_at = current.isoformat()
            event.wake_count = len(wake_summary)
            event.wake_summary = [dict(item) for item in wake_summary]
            self._append_log(
                {
                    "kind": "processed",
                    "event_id": event_id,
                    "processed_at": event.processed_at,
                    "wake_count": event.wake_count,
                }
            )
            break
        self.save_events(events)

    def summary(self, *, limit: int = 20) -> dict[str, Any]:
        events = self.list_events()
        pending = [event for event in events if event.status == "pending"]
        recent = list(reversed(events[-max(1, int(limit)) :]))
        return {
            "total_events": len(events),
            "pending_events": len(pending),
            "recent": [asdict(item) for item in recent],
        }
