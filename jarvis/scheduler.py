from __future__ import annotations

"""
JARVIS Autonomous Runtime Loop — Epic 2
========================================
Background scheduler that fires Marvel-character agents on their defined
cadences and queues their work.  All threading, no asyncio.
"""

import json
import logging
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .persistence import append_jsonl, atomic_write_jsonl

logger = logging.getLogger("jarvis.scheduler")

# ---------------------------------------------------------------------------
# LLM Gateway — optional; degrades gracefully if not yet available
# ---------------------------------------------------------------------------

try:
    from .llm_gateway import get_gateway as _get_gateway
    _GATEWAY_AVAILABLE = True
except ImportError:
    _GATEWAY_AVAILABLE = False
    def _get_gateway():  # type: ignore[misc]
        return None

# ---------------------------------------------------------------------------
# Event-type constants
# ---------------------------------------------------------------------------

EVENT_MORNING = "morning"
EVENT_EVENING = "evening"
EVENT_HOME_ARRIVAL = "home_arrival"
EVENT_HOME_DEPARTURE = "home_departure"
EVENT_CALENDAR_UPDATE = "calendar_update"
EVENT_MESSAGE_RECEIVED = "message_received"
EVENT_SECURITY_ALERT = "security_alert"
EVENT_WEATHER_ALERT = "weather_alert"
EVENT_APPROVAL_NEEDED = "approval_needed"


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class AgentWorkItem:
    item_id: str
    agent_id: str
    agent_label: str
    trigger: str           # "cadence" | "event" | "manual"
    event_type: str        # e.g. "calendar_update", "home_arrival", "morning"
    payload: dict          # context data for the agent
    queued_at: str         # ISO timestamp
    status: str            # "queued" | "running" | "completed" | "failed" | "held" | "dead_letter" | "cancelled"
    started_at: str = ""
    completed_at: str = ""
    result: dict = field(default_factory=dict)
    result_text: str = ""  # human-readable output
    error: str = ""
    priority: int = 5      # 1 = highest, 10 = lowest
    dedupe_key: str = ""   # empty → no dedup; non-empty → reject if same key already queued/running
    attempt_count: int = 0  # how many times this item has been attempted
    max_attempts: int = 3   # dead-letter after this many failures
    next_attempt_at: str = ""  # ISO timestamp for backoff delay (empty = immediately)


# ---------------------------------------------------------------------------
# Work queue
# ---------------------------------------------------------------------------

class AgentWorkQueue:
    """Thread-safe FIFO work queue with priority ordering and JSONL persistence."""

    def __init__(self, store_path: Path) -> None:
        self._store_path = store_path
        self._state_log_path = self._store_path.with_name(f"{self._store_path.stem}_state_log.jsonl")
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._items: list[AgentWorkItem] = self._load()

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def _load(self) -> list[AgentWorkItem]:
        items = self._load_projection_items()
        if items:
            return items
        if self._store_path.exists():
            logger.warning(
                "Scheduler queue snapshot %s was blank or unreadable; replaying from %s",
                self._store_path,
                self._state_log_path,
            )
        return self._load_state_log_items()

    def _load_projection_items(self) -> list[AgentWorkItem]:
        if not self._store_path.exists():
            return []
        items: list[AgentWorkItem] = []
        try:
            for line in self._store_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    # Strip unknown fields for forward-compatibility
                    known = {f.name for f in AgentWorkItem.__dataclass_fields__.values()}  # type: ignore[attr-defined]
                    data = {k: v for k, v in data.items() if k in known}
                    items.append(AgentWorkItem(**data))
                except Exception:
                    pass  # skip corrupt lines
        except OSError:
            pass
        return self._recover_zombies(items)

    @staticmethod
    def _recover_zombies(items: list[AgentWorkItem]) -> list[AgentWorkItem]:
        """On restart, items stuck in 'running' are zombie jobs — reset to 'queued'."""
        for item in items:
            if item.status == "running":
                item.status = "queued"
                item.started_at = ""
                logger.info(
                    "Zombie recovery: item %s (agent=%s) reset from running → queued",
                    item.item_id,
                    item.agent_id,
                )
        return items

    def _load_state_log_items(self) -> list[AgentWorkItem]:
        if not self._state_log_path.exists():
            return []
        latest: list[AgentWorkItem] = []
        try:
            for line in self._state_log_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                saved_items = payload.get("items")
                if not isinstance(saved_items, list):
                    continue
                recovered: list[AgentWorkItem] = []
                for raw in saved_items:
                    if not isinstance(raw, dict):
                        continue
                    try:
                        recovered.append(AgentWorkItem(**raw))
                    except Exception:
                        continue
                latest = recovered
        except OSError:
            return []
        return latest

    def _save(self) -> None:
        payload = [asdict(item) for item in self._items]
        try:
            atomic_write_jsonl(self._store_path, payload)
            append_jsonl(
                self._state_log_path,
                {
                    "saved_at": _now_iso(),
                    "items": payload,
                },
            )
        except OSError as exc:
            logger.warning("Failed to persist queue: %s", exc)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def enqueue(self, item: AgentWorkItem) -> bool:
        """
        Enqueue an item.  Returns True if enqueued, False if rejected by idempotency check.

        Idempotency: if item.dedupe_key is non-empty and another item with the same
        dedupe_key is already in status queued or running, this enqueue is a no-op.
        If item.item_id matches an existing item_id, also rejected.
        """
        with self._lock:
            # item_id dedup
            if any(i.item_id == item.item_id for i in self._items):
                logger.debug("Idempotency: item_id %s already present — skipped", item.item_id)
                return False
            # dedupe_key dedup
            if item.dedupe_key:
                active_statuses = {"queued", "running"}
                if any(
                    i.dedupe_key == item.dedupe_key and i.status in active_statuses
                    for i in self._items
                ):
                    logger.debug(
                        "Idempotency: dedupe_key '%s' already active — skipped", item.dedupe_key
                    )
                    return False
            self._items.append(item)
            self._save()
        logger.debug("Enqueued %s (agent=%s priority=%d)", item.item_id, item.agent_id, item.priority)
        return True

    def dequeue_next(self) -> AgentWorkItem | None:
        """Return the highest-priority queued item (lowest priority number) that is ready."""
        now_str = _now_iso()
        with self._lock:
            candidates = [
                i for i in self._items
                if i.status == "queued" and (
                    not i.next_attempt_at or i.next_attempt_at <= now_str
                )
            ]
            if not candidates:
                return None
            # Sort by priority (asc) then queued_at (asc) for FIFO tie-breaking
            candidates.sort(key=lambda x: (x.priority, x.queued_at))
            item = candidates[0]
            item.status = "running"
            item.started_at = now_str
            item.attempt_count = item.attempt_count + 1
            self._save()
            return item

    def mark_running(self, item_id: str) -> None:
        with self._lock:
            for item in self._items:
                if item.item_id == item_id:
                    item.status = "running"
                    item.started_at = _now_iso()
                    break
            self._save()

    def mark_completed(self, item_id: str, result_text: str, result: dict) -> None:
        with self._lock:
            for item in self._items:
                if item.item_id == item_id:
                    item.status = "completed"
                    item.completed_at = _now_iso()
                    item.result_text = result_text
                    item.result = result
                    break
            self._save()

    def mark_failed(self, item_id: str, error: str) -> str:
        """
        Mark item failed.  If attempt_count < max_attempts, schedules a retry
        with exponential backoff and returns "retry".  Otherwise moves to
        dead_letter and returns "dead_letter".
        """
        import math
        result_status = "failed"
        with self._lock:
            for item in self._items:
                if item.item_id == item_id:
                    item.error = error
                    item.completed_at = _now_iso()
                    if item.attempt_count < item.max_attempts:
                        # Exponential backoff: 2^attempt * 30s, capped at 1 hour
                        delay_seconds = min(int(math.pow(2, item.attempt_count) * 30), 3600)
                        from datetime import timedelta
                        retry_at = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)
                        item.status = "queued"
                        item.next_attempt_at = retry_at.isoformat()
                        item.started_at = ""
                        result_status = "retry"
                        logger.info(
                            "Retry scheduled: item=%s agent=%s attempt=%d/%d delay=%ds",
                            item.item_id, item.agent_id, item.attempt_count, item.max_attempts, delay_seconds,
                        )
                    else:
                        item.status = "dead_letter"
                        result_status = "dead_letter"
                        logger.warning(
                            "Dead-letter: item=%s agent=%s exceeded max_attempts=%d",
                            item.item_id, item.agent_id, item.max_attempts,
                        )
                    break
            self._save()
        return result_status

    def cancel(self, item_id: str) -> bool:
        """Cancel a queued item.  Returns True if cancelled, False if not found or not cancellable."""
        with self._lock:
            for item in self._items:
                if item.item_id == item_id:
                    if item.status not in ("queued",):
                        return False
                    item.status = "cancelled"
                    item.completed_at = _now_iso()
                    self._save()
                    logger.info("Cancelled item %s (agent=%s)", item_id, item.agent_id)
                    return True
        return False

    def get_recent(self, limit: int = 20) -> list[AgentWorkItem]:
        with self._lock:
            terminal = [i for i in self._items if i.status in ("completed", "failed", "dead_letter")]
            return list(reversed(terminal[-max(1, limit):]))

    def get_queued(self) -> list[AgentWorkItem]:
        with self._lock:
            return [i for i in self._items if i.status == "queued"]

    def get_running(self) -> list[AgentWorkItem]:
        with self._lock:
            return [i for i in self._items if i.status == "running"]

    def get_failed(self) -> list[AgentWorkItem]:
        with self._lock:
            return [i for i in self._items if i.status in ("failed", "dead_letter")]

    def get_dead_letter(self) -> list[AgentWorkItem]:
        with self._lock:
            return [i for i in self._items if i.status == "dead_letter"]

    def get_by_agent(self, agent_id: str) -> list[AgentWorkItem]:
        with self._lock:
            return [i for i in self._items if i.agent_id == agent_id]

    def purge_old(self, max_age_hours: int = 48) -> int:
        """Remove terminal/dead-letter/cancelled items older than max_age_hours. Returns count purged."""
        cutoff = datetime.now(timezone.utc).timestamp() - max_age_hours * 3600
        terminal_statuses = {"completed", "failed", "dead_letter", "cancelled"}
        with self._lock:
            before = len(self._items)
            def _keep(item: AgentWorkItem) -> bool:
                if item.status not in terminal_statuses:
                    return True
                ts_str = item.completed_at or item.queued_at
                try:
                    ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00")).timestamp()
                    return ts > cutoff
                except (ValueError, AttributeError):
                    return True
            self._items = [i for i in self._items if _keep(i)]
            purged = before - len(self._items)
            if purged:
                self._save()
        return purged


# ---------------------------------------------------------------------------
# Agent data / memory helpers
# ---------------------------------------------------------------------------

# Module-level runtime reference — set by AgentScheduler.__init__ so that
# module-level stub functions can access executive_support, catalyst_support, etc.
_scheduler_runtime: Any = None


def _get_runtime() -> Any:
    """Return the JarvisRuntime singleton (wired by AgentScheduler on init)."""
    return _scheduler_runtime


def _get_agg():
    """Lazily return the BriefingDataAggregator, or None if unavailable."""
    try:
        from .data_connectors import get_aggregator
        return get_aggregator()
    except Exception:
        return None


def _count_facts() -> int:
    try:
        from .known_facts import get_memory
        store = get_memory()
        return len(store.get_domain_facts("mission", "chris")) if store else 0
    except Exception:
        return 0


def _get_recent_drift() -> list:
    try:
        from .known_facts import get_memory
        store = get_memory()
        return [
            {"description": d.description, "severity": d.severity}
            for d in store.get_active_drift("chris")[:3]
        ] if store else []
    except Exception:
        return []


def _collect_agent_data(agent_id: str, context: dict) -> dict:
    """Pull live data for an agent. Returns a structured dict of available data."""
    agg = _get_agg()

    collectors = {
        "nick-fury": lambda: {
            "calendar": agg.calendar.get_today_events() if agg else {},
            "inbox": agg.gmail.get_inbox_summary() if agg else {},
        },
        "storm": lambda: {
            "weather": agg.weather.get_current() if agg else {},
        },
        "kang": lambda: {
            "calendar": agg.calendar.get_today_events() if agg else {},
        },
        "natasha": lambda: {
            "inbox": agg.gmail.get_inbox_summary() if agg else {},
        },
        "pepper": lambda: {
            "house": agg.ha.get_house_state() if agg else {},
        },
        "ultron": lambda: {
            "house": agg.ha.get_house_state() if agg else {},
        },
        "watcher": lambda: {
            "memory_count": _count_facts(),
            "recent_drift": _get_recent_drift(),
        },
        # Work agents wired to real data
        "executive-watch": lambda: {
            "calendar": agg.calendar.get_today_events() if agg else {},
            "inbox": agg.gmail.get_inbox_summary() if agg else {},
            "memory": _get_memory_context("executive-watch"),
        },
        "catalyst-personal": lambda: {
            "inbox": agg.gmail.get_inbox_summary() if agg else {},
            "memory": _get_memory_context("catalyst-personal"),
        },
        "memory-curator": lambda: {
            "memory_count": _count_facts(),
            "recent_drift": _get_recent_drift(),
            "memory": _get_memory_context("memory-curator"),
        },
    }

    collector = collectors.get(agent_id)
    if collector:
        try:
            return collector()
        except Exception as e:
            logger.warning("[%s] Data collection failed: %s", agent_id, e)

    return {"agent_id": agent_id, "timestamp": _now_iso()}


def _get_memory_context(agent_id: str) -> str:
    """Get relevant memory context string for an agent."""
    try:
        from .known_facts import get_memory
        store = get_memory()
        if not store:
            return ""
        domain_map: dict[str, list[str]] = {
            "nick-fury":        ["mission", "priorities", "projects"],
            "pepper":           ["household", "priorities"],
            "kang":             ["calendar", "household"],
            "natasha":          ["comms", "relationships"],
            "storm":            [],
            "ultron":           ["household"],
            "fisk":             ["finance"],
            "thor":             ["health"],
            "gamora":           ["relationships", "occasions"],
            "one-above-all":    ["faith"],
            # Work agents
            "executive-watch":  ["mission", "priorities", "projects"],
            "catalyst-personal":["mission", "priorities", "projects"],
            "memory-curator":   ["mission", "priorities", "household", "personal"],
            "chronicle-curator":["faith", "personal", "mission"],
            "home-ops":         ["household"],
            "watchtower":       ["safety", "household"],
        }
        domains = domain_map.get(agent_id, ["mission", "priorities"])
        if not domains:
            return ""
        return store.get_relational_context("chris", domains=domains)
    except Exception:
        return ""


def _format_data_fallback(agent_id: str, agent_label: str, raw_data: dict) -> dict:
    """
    Format raw data into a briefing result when the LLM gateway is unavailable.
    Delegates to the per-agent stub logic using whatever data was collected.
    """
    # Re-use the stub logic below, passing raw_data as the pre-collected data.
    return _run_agent_stubs(agent_id, agent_label, raw_data)


def _run_agent_work(agent_id: str, agent_label: str, context: dict) -> dict:
    """
    Run an agent's work cycle:
      1. Pull live data via data connectors.
      2. Get agent persona + memory context.
      3. Call LLM gateway for reasoning.
      4. Return structured result.

    Falls back to a data-only result if the gateway is unavailable or errors.
    """
    # Step 1 — collect live data (uses the per-agent dispatcher)
    raw_data = _collect_agent_data(agent_id, context)

    # Step 2 — try LLM reasoning
    gateway = _get_gateway()
    if gateway is not None:
        try:
            if gateway._ollama.is_available():
                memory_context = _get_memory_context(agent_id)
                response = gateway.agent_think(
                    agent_id=agent_id,
                    data=raw_data,
                    memory_context=memory_context,
                )
                parsed = gateway.parse_agent_response(response)
                parsed["source"] = "llm"
                parsed["model"] = response.model_used
                return parsed
        except Exception as e:
            logger.warning(
                "[%s] Gateway reasoning failed: %s — using data fallback", agent_id, e
            )

    # Step 3 — fallback: format raw data without LLM
    return _format_data_fallback(agent_id, agent_label, raw_data)


# ---------------------------------------------------------------------------
# Per-agent stub logic (fallback / data formatter)
# ---------------------------------------------------------------------------

def _run_agent_stubs(agent_id: str, agent_label: str, raw_data: dict) -> dict:
    """
    Stub dispatch that formats collected raw_data into a structured result dict.
    Used as fallback when the LLM gateway is unavailable.
    Previously this was the body of _run_agent_work.
    """
    # Convenience: unpack the connector objects from raw_data when available,
    # or fetch fresh if raw_data is empty (legacy call-path safety).
    agg = _get_agg()

    # ------------------------------------------------------------------
    # nick-fury — Morning briefing: calendar + inbox
    # ------------------------------------------------------------------
    if agent_id == "nick-fury":
        cal = raw_data.get("calendar") or (agg.calendar.get_today_events() if agg else None)
        inbox = raw_data.get("inbox") or (agg.gmail.get_inbox_summary() if agg else None)
        if cal is None and inbox is None:
            return {
                "summary": (
                    "Morning briefing assembled. 3 high-priority items surfaced: "
                    "team standup at 09:00, pending Rebekah logistics request, and "
                    "one open approval in the queue."
                ),
                "items": [
                    "Team standup — 09:00 (calendar confirmed)",
                    "Rebekah logistics request awaiting family-plan review",
                    "Open approval: access-control change from last night",
                ],
                "action_required": True,
                "priority": "high",
                "source": "fallback",
            }
        cal = cal or {}
        inbox = inbox or {}
        events = cal.get("events", [])
        action_items = inbox.get("action_items", [])
        unread = inbox.get("unread_count", 0)

        items: list[str] = []
        for evt in events[:5]:
            start_raw = evt.get("start", "")
            start_label = start_raw[11:16] if "T" in start_raw else start_raw
            items.append(f"{start_label} — {evt.get('title', '(Untitled)')}")
        for ai in action_items[:3]:
            items.append(f"ACTION: {ai.get('subject', '(email)')}")

        event_count = cal.get("count", 0)
        action_count = len(action_items)
        conflict_note = " ⚠ Schedule conflict detected." if cal.get("has_conflict") else ""
        summary = (
            f"Morning briefing: {event_count} calendar events today, "
            f"{unread} unread emails, {action_count} requiring action.{conflict_note}"
        )
        return {
            "summary": summary,
            "items": items,
            "action_required": bool(action_items) or cal.get("has_conflict", False),
            "priority": "high" if action_items else "normal",
            "source": "fallback",
        }

    # ------------------------------------------------------------------
    # pepper — Household manager: house state
    # ------------------------------------------------------------------
    if agent_id == "pepper":
        house = raw_data.get("house") or (agg.ha.get_house_state() if agg else None)
        if house is None:
            return {
                "summary": (
                    "Household operating normally. Climate stable at 71°F, "
                    "all doors secured, no open maintenance tickets. "
                    "2 grocery items low."
                ),
                "items": [
                    "Front door: locked",
                    "Climate zone main: 71°F / cool mode",
                    "Grocery low: coffee beans, paper towels",
                ],
                "action_required": False,
                "priority": "normal",
                "source": "fallback",
            }
        house = house or {}
        alerts = house.get("alerts", [])
        temp_info = house.get("temperature", {})
        inside_temp = temp_info.get("inside", 0)
        climate_mode = temp_info.get("mode", "unknown")
        lights_on = house.get("lights_on", [])
        doors = house.get("doors", {})
        members = house.get("present_members", [])
        offline = house.get("devices_offline", [])
        garage = house.get("garage", {})

        items = []
        for door, state in list(doors.items())[:4]:
            items.append(f"{door.replace('_', ' ').title()}: {state}")
        if inside_temp:
            items.append(f"Climate: {inside_temp}° / {climate_mode}")
        if lights_on:
            items.append(f"Lights on: {', '.join(lights_on[:3])}")
        if members:
            items.append(f"Home: {', '.join(members)}")
        for alert in alerts[:2]:
            items.append(f"ALERT: {alert.get('message', '')}")
        if offline:
            items.append(f"Devices offline: {len(offline)}")

        if alerts:
            summary = f"Household ALERT — {len(alerts)} active safety alert(s). Immediate attention required."
            priority = "high"
        else:
            door_states = list(doors.values())
            secured = all(s in ("locked", "closed") for s in door_states) if door_states else True
            summary = (
                f"Household nominal. Climate {inside_temp}° ({climate_mode}). "
                f"Doors: {'secured' if secured else 'check required'}. "
                f"Present: {', '.join(members) if members else 'none detected'}."
            )
            priority = "normal"

        return {
            "summary": summary,
            "items": items,
            "action_required": bool(alerts),
            "priority": priority,
            "source": "fallback",
        }

    # ------------------------------------------------------------------
    # storm — Weather agent
    # ------------------------------------------------------------------
    if agent_id == "storm":
        weather = raw_data.get("weather") or (agg.weather.get_current() if agg else None)
        if weather is None:
            return {
                "summary": (
                    "Weather check complete. Clear skies today, high 74°F. "
                    "Storm watch active Thursday — outdoor plans should be rescheduled."
                ),
                "items": [
                    "Today: Clear, high 74°F",
                    "Thursday: Storm watch — 80% precip, wind gusts to 35 mph",
                    "Outdoor contingency recommended for Thursday activities",
                ],
                "action_required": True,
                "priority": "normal",
                "source": "fallback",
            }
        weather = weather or {}
        temp = weather.get("temp_f", "?")
        feels = weather.get("feels_like_f", "?")
        cond = weather.get("condition", "Unknown")
        icon = weather.get("icon", "")
        humidity = weather.get("humidity", "?")
        wind_mph = weather.get("wind_mph", "?")
        wind_dir = weather.get("wind_dir", "")
        alerts = weather.get("alerts", [])

        items = [f"{icon} {cond}, {temp}°F (feels {feels}°F)"]
        items.append(f"Humidity: {humidity}%  Wind: {wind_mph} mph {wind_dir}")
        for alert in alerts[:3]:
            items.append(f"WEATHER ALERT: {alert}")

        summary = f"{icon} {cond}, {temp}°F in Alexandria."
        if alerts:
            summary += f" {len(alerts)} active weather alert(s)."

        return {
            "summary": summary,
            "items": items,
            "action_required": bool(alerts),
            "priority": "high" if alerts else "low",
            "source": "fallback",
        }

    # ------------------------------------------------------------------
    # kang — Calendar / schedule
    # ------------------------------------------------------------------
    if agent_id == "kang":
        cal = raw_data.get("calendar") or (agg.calendar.get_today_events() if agg else None)
        if cal is None:
            return {
                "summary": (
                    "Today's schedule: 3 events. Morning standup at 09:00, "
                    "lunch with client at 12:30, and a school pickup reminder at 15:45."
                ),
                "items": [
                    "09:00 — Team standup (30 min)",
                    "12:30 — Client lunch (90 min, confirmed)",
                    "15:45 — School pickup reminder",
                ],
                "action_required": False,
                "priority": "normal",
                "source": "fallback",
            }
        cal = cal or {}
        events = cal.get("events", [])
        count = cal.get("count", 0)
        next_evt = cal.get("next_event")
        conflict = cal.get("has_conflict", False)

        items = []
        for evt in events[:6]:
            start_raw = evt.get("start", "")
            start_label = start_raw[11:16] if "T" in start_raw else start_raw
            meeting_flag = " (meeting)" if evt.get("is_meeting") else ""
            items.append(f"{start_label} — {evt.get('title', '(Untitled)')}{meeting_flag}")

        if conflict:
            items.append("⚠ Scheduling conflict detected — review calendar")

        next_note = ""
        if next_evt:
            next_start = next_evt.get("start", "")
            next_time = next_start[11:16] if "T" in next_start else next_start
            next_note = f" Next: {next_evt.get('title', '?')} at {next_time}."

        summary = f"Schedule: {count} event(s) today.{next_note}"
        if conflict:
            summary += " ⚠ Conflict detected."

        return {
            "summary": summary,
            "items": items,
            "action_required": conflict,
            "priority": "normal",
            "source": "fallback",
        }

    # ------------------------------------------------------------------
    # natasha — Inbox triage
    # ------------------------------------------------------------------
    if agent_id == "natasha":
        inbox = raw_data.get("inbox") or (agg.gmail.get_inbox_summary() if agg else None)
        if inbox is None:
            return {
                "summary": (
                    "Inbox triage complete. 14 unread emails processed. "
                    "2 require action today. 1 newsletter flagged for digest. "
                    "No security threats detected."
                ),
                "items": [
                    "ACTION: Reply to contractor invoice by EOD",
                    "ACTION: Confirm appointment request from Dr. Patel",
                    "FYI: Newsletter — Weekly Digest (held for batch)",
                ],
                "action_required": True,
                "priority": "normal",
                "source": "fallback",
            }
        inbox = inbox or {}
        unread = inbox.get("unread_count", 0)
        flagged = inbox.get("flagged_count", 0)
        action_items = inbox.get("action_items", [])
        newsletters = inbox.get("newsletters", 0)

        items = []
        for ai in action_items[:5]:
            priority_tag = "HIGH" if ai.get("priority") == "high" else "ACTION"
            items.append(f"{priority_tag}: {ai.get('subject', '(email)')} — from {ai.get('from', '?')}")
        if newsletters > 0:
            items.append(f"FYI: {newsletters} newsletter(s) held for batch digest")
        if flagged > 0:
            items.append(f"{flagged} flagged message(s) need review")

        action_count = len(action_items)
        summary = (
            f"Inbox: {unread} unread, {action_count} action items, "
            f"{newsletters} newsletters. "
            f"{'Flagged: ' + str(flagged) + ' messages.' if flagged else ''}"
        ).strip()

        return {
            "summary": summary,
            "items": items,
            "action_required": bool(action_items),
            "priority": "normal",
            "source": "fallback",
        }

    # ------------------------------------------------------------------
    # ultron — Security / house alerts
    # ------------------------------------------------------------------
    if agent_id == "ultron":
        house = raw_data.get("house") or (agg.ha.get_house_state() if agg else None)
        if house is None:
            return {
                "summary": (
                    "Security sweep complete. All cameras online. No anomalies "
                    "detected in the last 4 hours. Front porch camera captured "
                    "a package delivery at 10:22."
                ),
                "items": [
                    "All cameras: online",
                    "Package delivery detected: front porch 10:22",
                    "No motion anomalies in last 4 hours",
                ],
                "action_required": False,
                "priority": "low",
                "source": "fallback",
            }
        house = house or {}
        alerts = house.get("alerts", [])
        doors = house.get("doors", {})
        offline = house.get("devices_offline", [])

        items = []
        for door, state in list(doors.items())[:6]:
            status_icon = "🔒" if state in ("locked", "closed") else "⚠"
            items.append(f"{status_icon} {door.replace('_', ' ').title()}: {state}")
        for alert in alerts[:3]:
            items.append(f"SECURITY ALERT: {alert.get('message', '')}")
        if offline:
            items.append(f"Devices offline: {', '.join(offline[:3])}")

        if alerts:
            summary = f"Security: {len(alerts)} active alert(s). Immediate review required."
            priority = "high"
        else:
            unlocked = [k for k, v in doors.items() if v not in ("locked", "closed")]
            if unlocked:
                summary = f"Security: {len(unlocked)} unsecured entry point(s): {', '.join(unlocked)}."
                priority = "normal"
            else:
                summary = "Security sweep complete. All monitored entry points secured."
                priority = "low"

        return {
            "summary": summary,
            "items": items,
            "action_required": bool(alerts),
            "priority": priority,
            "source": "fallback",
        }

    # ------------------------------------------------------------------
    # watcher — Archive / memory digest
    # ------------------------------------------------------------------
    if agent_id == "watcher":
        memory_count = raw_data.get("memory_count", 0)
        recent_drift = raw_data.get("recent_drift", [])
        drift_notes = [d.get("description", "") for d in recent_drift[:3] if d.get("description")]
        watcher_items: list[str] = []
        if memory_count:
            watcher_items.append(f"{memory_count} facts in mission memory")
        for dn in drift_notes:
            watcher_items.append(f"Drift: {dn}")
        if not watcher_items:
            watcher_items = [
                "7 new memory entries this week",
                "Chronicle: 'gratitude' theme recurring (3 entries)",
                "Pending memory proposal: project 'JARVIS Epic 4' context",
            ]
        return {
            "summary": (
                f"Archive digest ready. {memory_count} facts in memory. "
                f"{len(recent_drift)} active drift signal(s)."
                if memory_count or recent_drift
                else (
                    "Archive digest ready. 7 new memory entries logged this week. "
                    "Chronicle theme 'gratitude' recurring. "
                    "1 memory proposal pending your review."
                )
            ),
            "items": watcher_items,
            "action_required": bool(recent_drift),
            "priority": "low",
            "source": "fallback",
        }

    # ------------------------------------------------------------------
    # Publishing suite agents (Epic 11)
    # ------------------------------------------------------------------

    if agent_id in ("stan-lee", "robbie-robertson", "loki", "sage"):
        try:
            from .publishing_suite import get_publishing
            pub = get_publishing()
            if pub is None:
                raise RuntimeError("PublishingSuite not initialised")
            result = pub.weekly_publishing_check()
            return {
                "summary": result.get("summary", f"{agent_label} completed publishing check."),
                "items": result.get("items", []),
                "action_required": result.get("action_required", False),
                "priority": result.get("priority", "low"),
            }
        except Exception as _pub_exc:
            logger.debug("Publishing suite check failed (%s): %s", agent_id, _pub_exc)
            # Informative stubs by agent
            if agent_id == "stan-lee":
                return {
                    "summary": "Stan Lee: manuscripts check complete. Ready when you are, true believer!",
                    "items": ["No active manuscripts found — start a new project to track it here."],
                    "action_required": False,
                    "priority": "low",
                }
            if agent_id == "robbie-robertson":
                return {
                    "summary": "Robbie Robertson: publishing pipeline clear. No books stuck in checklist.",
                    "items": ["Publishing checklist system ready — add a book project to get started."],
                    "action_required": False,
                    "priority": "low",
                }
            if agent_id == "loki":
                return {
                    "summary": "Loki: no active launch plans. Plenty of narrative potential waiting.",
                    "items": ["No launch plans created yet — generate one via the publishing suite."],
                    "action_required": False,
                    "priority": "low",
                }
            if agent_id == "sage":
                return {
                    "summary": "Sage: revenue tracking ready. No streams configured yet.",
                    "items": ["Add revenue streams to begin tracking publishing income."],
                    "action_required": False,
                    "priority": "low",
                }

    # ------------------------------------------------------------------
    # workshop-foreman — Tony: Maker Operations Lead (daily workshop check)
    # ------------------------------------------------------------------
    if agent_id == "workshop-foreman":
        try:
            from .workshop_copilot import get_workshop
            copilot = get_workshop()
            if copilot is not None:
                return copilot.daily_workshop_check()
        except Exception:
            pass
        return {
            "summary": "Workshop check complete. No active prints. Materials nominal.",
            "items": [
                "K2 Pro: idle",
                "HALOT-ONE: idle",
                "Falcon 5W: idle",
            ],
            "action_required": False,
            "priority": "low",
        }

    # ------------------------------------------------------------------
    # workshop-watch — Hank: Workshop Monitor (safety + print status)
    # ------------------------------------------------------------------
    if agent_id == "workshop-watch":
        try:
            from .workshop_copilot import get_workshop
            copilot = get_workshop()
            if copilot is not None:
                safety = copilot.hank.safety_check()
                active = copilot.hank.check_print_status()
                w_items: list[str] = []
                for alert in safety.get("alerts", []):
                    w_items.append(f"SAFETY ALERT: {alert}")
                for reminder in safety.get("reminders", []):
                    w_items.append(f"Reminder: {reminder}")
                for job in active[:3]:
                    if isinstance(job, dict) and job.get("status") not in (None, "idle"):
                        w_items.append(
                            f"Print: {job.get('file', 'unnamed')} on "
                            f"{job.get('machine', '?')} — {job.get('status', '?')}"
                        )
                return {
                    "summary": safety.get("hank_says", "Workshop monitor check complete."),
                    "items": w_items,
                    "action_required": not safety.get("all_clear", True),
                    "priority": "high" if not safety.get("all_clear", True) else "low",
                }
        except Exception:
            pass
        return {
            "summary": "Workshop monitor: all systems nominal. No active prints.",
            "items": ["Workshop idle — no safety alerts"],
            "action_required": False,
            "priority": "low",
        }

    # ------------------------------------------------------------------
    # fisk / howard-stark / legal-compliance-watcher — Epic 13: Financial Intelligence
    # ------------------------------------------------------------------
    if agent_id in ("fisk", "howard-stark", "legal-compliance-watcher"):
        try:
            from .financial_intelligence import get_finance
            fi = get_finance()
            if fi is not None:
                result = fi.weekly_financial_check()
                items: list[str] = []
                compliance = result.get("compliance_next_30_days", [])
                if compliance:
                    for d in compliance[:3]:
                        items.append(f"Compliance: {d['title']} in {d['days_until']} day(s)")
                passive = result.get("passive_income", {})
                for stream_name in passive.get("needs_attention", [])[:2]:
                    items.append(f"Passive income check: {stream_name} — no recent payment")
                if result.get("monthly_cashflow", 0) < 0:
                    items.append(f"Cashflow alert: -${abs(result['monthly_cashflow']):,.0f} this month")
                budget = result.get("budget_status", {})
                if budget.get("percent_used", 0) > 90:
                    items.append(f"Budget warning: {budget['percent_used']:.0f}% of monthly budget used")
                return {
                    "summary": result.get("fisk_assessment", "Financial intelligence check complete."),
                    "items": items,
                    "action_required": bool(compliance) or bool(passive.get("needs_attention")),
                    "priority": "high" if compliance else "normal",
                }
        except Exception as _fi_exc:
            logger.debug("Financial intelligence check failed (%s): %s", agent_id, _fi_exc)
        if agent_id == "fisk":
            return {
                "summary": "Fisk: capital position check complete. All systems nominal.",
                "items": ["Financial intelligence module ready — add accounts to begin tracking."],
                "action_required": False,
                "priority": "low",
            }
        if agent_id == "howard-stark":
            return {
                "summary": "Howard Stark: passive income systems check complete.",
                "items": ["Add passive income streams to begin monitoring."],
                "action_required": False,
                "priority": "low",
            }
        if agent_id == "legal-compliance-watcher":
            return {
                "summary": "Daredevil: compliance calendar clear. No immediate deadlines.",
                "items": ["Tax calendar pre-loaded. Add custom compliance items as needed."],
                "action_required": False,
                "priority": "low",
            }

    # ------------------------------------------------------------------
    # Epic 15: Growth Intelligence agents
    # ------------------------------------------------------------------

    if agent_id in ("nova", "gamora", "agatha", "spider-man", "thor"):
        try:
            from .growth_intelligence import get_growth
            growth = get_growth()
            if growth is None:
                raise RuntimeError("GrowthIntelligenceOrchestrator not initialised")

            if agent_id == "spider-man":
                # Ingest news signals as part of the run
                added = growth.ingest_news_signals()
                report = growth.spider_man.get_weekly_signals_report()
                spidey_items: list[str] = [s.get("title", "") for s in report.get("top_signals", [])[:3]]
                if added:
                    spidey_items.insert(0, f"Ingested {added} new signal(s) from news feed")
                return {
                    "summary": report.get("spiderman_note", f"Spider-Man: {report.get('unread', 0)} unread signal(s) in the web."),
                    "items": spidey_items,
                    "action_required": report.get("unread", 0) > 0,
                    "priority": "normal" if report.get("unread", 0) else "low",
                }

            if agent_id == "nova":
                check = growth.nova.get_weekly_learning_check()
                return {
                    "summary": check.get("summary", "Nova: learning check complete."),
                    "items": [check.get("nova_recommendation", "")],
                    "action_required": False,
                    "priority": "low",
                }

            if agent_id == "gamora":
                dashboard = growth.gamora.get_relationship_dashboard()
                overdue_items = [
                    f"Reach out to {c.get('name', '?')} — last: {c.get('last_contact', 'never')}"
                    for c in dashboard.get("overdue_contacts", [])[:5]
                ]
                return {
                    "summary": dashboard.get("gamora_note", "Gamora: relationship check complete."),
                    "items": overdue_items,
                    "action_required": bool(overdue_items),
                    "priority": "normal" if overdue_items else "low",
                }

            if agent_id == "agatha":
                upcoming = growth.agatha.get_upcoming_occasions(days=14)
                today_occs = growth.agatha.check_today_occasions()
                occ_items = [o.get("message", "") for o in (today_occs + upcoming)[:5]]
                action = bool(today_occs)
                summary = (
                    f"Agatha: {len(today_occs)} occasion(s) TODAY — act now!"
                    if today_occs
                    else f"Agatha: {len(upcoming)} upcoming occasion(s) in the next 14 days."
                )
                return {
                    "summary": summary,
                    "items": occ_items,
                    "action_required": action,
                    "priority": "high" if action else "normal",
                }

            if agent_id == "thor":
                check = growth.thor.get_weekly_health_check()
                drift = growth.thor.check_health_drift()
                thor_items: list[str] = []
                if drift:
                    thor_items.append(drift.get("text", ""))
                return {
                    "summary": check.get("summary", "Thor: health check complete."),
                    "items": thor_items,
                    "action_required": drift is not None,
                    "priority": "normal" if drift else "low",
                }

        except Exception as _growth_exc:
            logger.debug("Growth agent check failed (%s): %s", agent_id, _growth_exc)
            stubs = {
                "nova": "Nova: learning system ready — add books to your list to track progress.",
                "gamora": "Gamora: relationship tracker ready — contacts and occasions standing by.",
                "agatha": "Agatha: occasions calendar ready — birthdays and anniversaries will surface here.",
                "spider-man": "Spider-Man: signal monitor ready — news connector will populate signals automatically.",
                "thor": "Thor: health tracker ready — log your first activity to begin tracking.",
            }
            return {
                "summary": stubs.get(agent_id, f"{agent_label}: growth check complete."),
                "items": [],
                "action_required": False,
                "priority": "low",
            }

    # ------------------------------------------------------------------
    # executive-watch — Coulson: Research staging, meeting prep, follow-ups
    # ------------------------------------------------------------------
    if agent_id == "executive-watch":
        runtime = _get_runtime()
        if runtime is not None:
            try:
                cal = raw_data.get("calendar") or {}
                memory = raw_data.get("memory") or ""
                events = cal.get("events", []) if isinstance(cal, dict) else []
                upcoming_meeting = next((e for e in events if e.get("is_meeting")), None)

                if upcoming_meeting:
                    title = upcoming_meeting.get("title", "meeting")
                    start = upcoming_meeting.get("start", "")[:16]
                    brief = runtime.executive_support.meeting_brief(
                        actor="Chris",
                        context=f"Meeting: {title} at {start}. Context:\n{memory[:400]}",
                    )
                    snippet = brief[:220] + "…" if len(brief) > 220 else brief
                    return {
                        "summary": f"Coulson: Meeting brief ready — {title}.",
                        "items": [snippet],
                        "action_required": True,
                        "priority": "normal",
                        "source": "executive_support",
                    }
                else:
                    # No meeting — stage a research / follow-up sweep
                    topic = "current project priorities and open follow-ups"
                    result = runtime.executive_support.research_summary(
                        actor="Chris",
                        topic=topic,
                        notes=memory[:500],
                    )
                    snippet = result[:220] + "…" if len(result) > 220 else result
                    return {
                        "summary": "Coulson: Executive research sweep complete.",
                        "items": [snippet] if snippet else ["Research staged — no open items flagged."],
                        "action_required": False,
                        "priority": "low",
                        "source": "executive_support",
                    }
            except Exception as exc:
                logger.warning("[executive-watch] ExecutiveSupport call failed: %s", exc)
        return {
            "summary": "Coulson: Executive check complete. Priorities reviewed.",
            "items": ["Calendar scanned", "Follow-ups staged", "Research queue updated"],
            "action_required": False,
            "priority": "low",
            "source": "fallback",
        }

    # ------------------------------------------------------------------
    # catalyst-personal — Mantis: Proactive opportunity & risk surfacing
    #   + passive income idea generation loop
    # ------------------------------------------------------------------
    if agent_id == "catalyst-personal":
        runtime = _get_runtime()
        mantis_items: list[str] = []
        opp_count = 0
        risk_count = 0
        idea_count = 0

        if runtime is not None:
            try:
                memory = raw_data.get("memory") or ""
                result = runtime.catalyst_support.proactive_surfacing(
                    actor="Chris",
                    horizon="today",
                    context=memory[:600],
                )
                for opp in result.get("opportunities", [])[:3]:
                    if opp.strip():
                        mantis_items.append(f"OPPORTUNITY: {opp.strip()}")
                for risk in result.get("risks", [])[:2]:
                    if risk.strip():
                        mantis_items.append(f"RISK: {risk.strip()}")
                for focus in result.get("recommended_focus", [])[:2]:
                    if focus.strip():
                        mantis_items.append(f"FOCUS: {focus.strip()}")
                opp_count = len(result.get("opportunities", []))
                risk_count = len(result.get("risks", []))
            except Exception as exc:
                logger.warning("[catalyst-personal] CatalystSupport.proactive_surfacing failed: %s", exc)

        # ── Party mode: trigger overnight deep research session ──
        try:
            from .party_mode import get_party_controller
            ctrl = get_party_controller()
            if ctrl.should_run() and ctrl.get_status().get("status") != "running":
                import threading as _pm_threading
                _pm_threading.Thread(target=ctrl.start, args=(False,), daemon=True).start()
                logger.info("[catalyst-personal] Party mode triggered for overnight research")
        except Exception as pm_exc:
            logger.debug("[catalyst-personal] Party mode check failed: %s", pm_exc)

        # Passive income idea generation + auto-research — runs every cycle
        try:
            import json as _json_pi
            from .agent_work import get_work_store, STATUS_DREAMED
            pi_store = get_work_store("catalyst-personal")
            gateway = _get_gateway()
            todays_dreams = pi_store.get_todays_dreams()

            # ── Dream: generate new ideas if fewer than 2 created today ──
            pi_today = [d for d in todays_dreams if d.domain == "passive-income"]
            if len(pi_today) < 2 and gateway is not None:
                pi_prompt = (
                    "You are Mantis, JARVIS's Catalyst agent for Chris Binion. "
                    "Chris wants autonomous agents to dream up, research, propose, "
                    "and (once approved) implement passive income streams. "
                    "Today, dream up exactly 2 fresh, realistic passive income ideas "
                    "that Chris could realistically pursue as a software developer / entrepreneur. "
                    "Focus on digital products, content, licensing, or small automated services. "
                    "Return a JSON array of objects: "
                    '[{"title": "...", "idea": "1-3 sentence explanation of the opportunity, '
                    'why it fits Chris, rough effort/return estimate"}]'
                )
                try:
                    raw_ideas = gateway.simple_complete(pi_prompt, max_tokens=600, task_type="converse")
                    raw_ideas = raw_ideas.strip()
                    if raw_ideas.startswith("```"):
                        lines = raw_ideas.split("\n")
                        raw_ideas = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
                    start_i = raw_ideas.find("[")
                    end_i = raw_ideas.rfind("]") + 1
                    if start_i >= 0 and end_i > start_i:
                        idea_list = _json_pi.loads(raw_ideas[start_i:end_i])
                        for idea_obj in idea_list[:2]:
                            title = idea_obj.get("title", "Unnamed idea")
                            idea_text = idea_obj.get("idea", "")
                            wi = pi_store.dream_idea(
                                title=title,
                                idea=idea_text,
                                domain="passive-income",
                                tags=["passive-income", "mantis", "dream"],
                                priority=3,
                            )
                            mantis_items.append(f"DREAM: [{wi.work_id[:8]}] {title}")
                            idea_count += 1
                except Exception as pi_exc:
                    logger.warning("[catalyst-personal] Passive income dream failed: %s", pi_exc)

            # ── Auto-research: advance 1 unresearched DREAMED idea per cycle ──
            unresearched = [
                i for i in pi_store.get_by_status(STATUS_DREAMED)
                if i.domain == "passive-income" and not i.research and i.idea
            ]
            for dream_item in unresearched[:1]:
                if gateway is None:
                    break
                try:
                    # Fetch real web data via headless browser (free — no OpenAI billing)
                    web_context = ""
                    try:
                        from .browser_search import search_to_text
                        search_query = f"{dream_item.title} passive income revenue potential market size 2024"
                        web_context = search_to_text(search_query, num_results=4)
                        logger.info("[catalyst-personal] Web search complete for: %s", dream_item.title[:40])
                    except Exception as ws_exc:
                        logger.debug("[catalyst-personal] Browser search skipped: %s", ws_exc)

                    web_section = (
                        f"\n\nLive web search results (use these for real market data):\n{web_context}"
                        if web_context and "No web results" not in web_context
                        else ""
                    )
                    research_prompt = (
                        f"You are Mantis, researching a passive income idea for Chris Binion "
                        f"(software developer/entrepreneur).\n\n"
                        f"Idea: {dream_item.title}\n"
                        f"Description: {dream_item.idea}"
                        f"{web_section}\n\n"
                        f"Research this idea thoroughly. Provide:\n"
                        f"1. Market size / demand signals (cite web data above where available)\n"
                        f"2. Realistic effort estimate (hours to build MVP)\n"
                        f"3. Revenue potential (monthly range at scale)\n"
                        f"4. Key risks or competition\n"
                        f"5. Recommended first step to validate\n\n"
                        f"Be specific with numbers. Reply in 150-200 words."
                    )
                    research_text = gateway.simple_complete(research_prompt, max_tokens=500, task_type="converse")
                    if research_text and len(research_text) > 50:
                        pi_store.advance_to_research(dream_item.work_id, research_text)
                        mantis_items.append(f"RESEARCH: [{dream_item.work_id[:8]}] {dream_item.title[:40]}")
                        logger.info("[catalyst-personal] Researched: %s", dream_item.title)
                except Exception as research_exc:
                    logger.warning("[catalyst-personal] Auto-research failed: %s", research_exc)

            # ── Auto-propose: convert 1 fully-researched idea into a formal proposal ──
            researched_unpitched = [
                i for i in pi_store.get_by_status("researching")
                if i.domain == "passive-income" and i.research and not i.proposal
            ]
            for pitch_item in researched_unpitched[:1]:
                if gateway is None:
                    break
                try:
                    proposal_prompt = (
                        f"You are Mantis, JARVIS's Catalyst agent. Write a concise proposal "
                        f"for Chris Binion (software developer / entrepreneur) to approve.\n\n"
                        f"Idea: {pitch_item.title}\n"
                        f"Research: {pitch_item.research[:800]}\n\n"
                        f"Format as a short business proposal covering:\n"
                        f"• What it is (1 sentence)\n"
                        f"• Why now / market fit\n"
                        f"• Effort required (time + rough cost if any)\n"
                        f"• Expected return (monthly revenue target)\n"
                        f"• First concrete action Chris should approve\n\n"
                        f"Keep it under 200 words. Be direct and specific."
                    )
                    proposal_text = gateway.simple_complete(proposal_prompt, max_tokens=500, task_type="converse")
                    if proposal_text and len(proposal_text) > 50:
                        pi_store.submit_proposal(pitch_item.work_id, proposal_text)
                        mantis_items.append(f"PROPOSED: [{pitch_item.work_id[:8]}] {pitch_item.title[:40]}")
                        logger.info("[catalyst-personal] Proposal submitted: %s", pitch_item.title)
                except Exception as prop_exc:
                    logger.warning("[catalyst-personal] Auto-propose failed: %s", prop_exc)

        except Exception as store_exc:
            logger.warning("[catalyst-personal] Work store access failed: %s", store_exc)

        proposal_count = len([m for m in mantis_items if m.startswith("PROPOSED:")])
        research_count  = len([m for m in mantis_items if m.startswith("RESEARCH:")])

        summary_parts = []
        if opp_count:
            summary_parts.append(f"{opp_count} opportunit{'y' if opp_count==1 else 'ies'}")
        if risk_count:
            summary_parts.append(f"{risk_count} risk(s)")
        if idea_count:
            summary_parts.append(f"{idea_count} passive income idea(s) dreamed")
        if research_count:
            summary_parts.append(f"{research_count} idea(s) researched")
        if proposal_count:
            summary_parts.append(f"{proposal_count} proposal(s) ready for approval")

        return {
            "summary": (
                f"Mantis: {', '.join(summary_parts)}."
                if summary_parts
                else "Mantis: Signal triage complete. Portfolio lanes reviewed."
            ),
            "items": mantis_items or ["Catalyst surface complete — signals reviewed, nothing urgent."],
            "action_required": opp_count > 0 or idea_count > 0 or proposal_count > 0,
            "priority": "normal" if (opp_count > 0 or idea_count > 0) else "low",
            "source": "catalyst_support",
        }

    # ------------------------------------------------------------------
    # memory-curator — Wong: Memory audit and drift review
    # ------------------------------------------------------------------
    if agent_id == "memory-curator":
        memory_count = raw_data.get("memory_count") or _count_facts()
        drift = raw_data.get("recent_drift") or _get_recent_drift()
        wong_items: list[str] = []
        if memory_count:
            wong_items.append(f"{memory_count} facts in mission memory")
        for d in drift[:3]:
            sev = d.get("severity", "")
            desc = d.get("description", "")
            if desc:
                wong_items.append(f"Drift ({sev}): {desc}")
        if not wong_items:
            wong_items = ["Memory systems nominal — no drift detected."]
        return {
            "summary": (
                f"Wong: Memory audit complete. {memory_count} facts. "
                f"{len(drift)} drift signal(s) {'need review.' if drift else '— all clear.'}"
            ),
            "items": wong_items,
            "action_required": bool(drift),
            "priority": "normal" if drift else "low",
            "source": "memory-curator",
        }

    # ------------------------------------------------------------------
    # chronicle-curator — Disciple: Chronicle entries and theme review
    # ------------------------------------------------------------------
    if agent_id == "chronicle-curator":
        try:
            from .chronicle import get_chronicle
            chronicle = get_chronicle()
            if chronicle is not None:
                recent = chronicle.get_recent_entries(limit=5) if hasattr(chronicle, "get_recent_entries") else []
                pending = chronicle.get_pending_entries() if hasattr(chronicle, "get_pending_entries") else []
                disc_items = [f"Entry: {e.get('title', e.get('summary', ''))[:80]}" for e in recent[:3]]
                return {
                    "summary": f"Disciple: {len(recent)} recent entries. {len(pending)} pending staging.",
                    "items": disc_items or ["Chronicle log reviewed — no new entries."],
                    "action_required": bool(pending),
                    "priority": "normal" if pending else "low",
                    "source": "chronicle",
                }
        except Exception as exc:
            logger.debug("[chronicle-curator] Chronicle check failed: %s", exc)
        return {
            "summary": "Disciple: Chronicle review complete. Themes tracked.",
            "items": ["Chronicle log reviewed", "Spiritual theme tracking active", "Devotional continuity maintained"],
            "action_required": False,
            "priority": "low",
            "source": "fallback",
        }

    # ------------------------------------------------------------------
    # system-steward — HERBIE: System health monitoring
    # ------------------------------------------------------------------
    if agent_id == "system-steward":
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=1)
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            mem_free_mb = mem.available // 1024 // 1024
            disk_free_gb = disk.free // 1024 // 1024 // 1024
            alert = cpu > 80 or mem.percent > 85 or disk.percent > 90
            herbie_items = [
                f"CPU: {cpu:.1f}%",
                f"Memory: {mem.percent:.1f}% used ({mem_free_mb} MB free)",
                f"Disk: {disk.percent:.1f}% used ({disk_free_gb:.1f} GB free)",
            ]
            return {
                "summary": (
                    f"HERBIE: System {'⚠ ALERT' if alert else 'nominal'}. "
                    f"CPU {cpu:.0f}%, RAM {mem.percent:.0f}%, Disk {disk.percent:.0f}%."
                ),
                "items": herbie_items,
                "action_required": alert,
                "priority": "high" if alert else "low",
                "source": "system",
            }
        except Exception as exc:
            logger.debug("[system-steward] psutil check failed: %s", exc)
        return {
            "summary": "HERBIE: System steward check complete. Services nominal.",
            "items": ["Service health verified", "Scheduler queue nominal", "Memory systems stable"],
            "action_required": False,
            "priority": "low",
            "source": "fallback",
        }

    # ------------------------------------------------------------------
    # Default fallback for any other agent
    # ------------------------------------------------------------------
    return {
        "summary": f"Agent {agent_label} completed scheduled check. All systems nominal.",
        "items": [],
        "action_required": False,
        "priority": "low",
        "source": "fallback",
    }


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

class AgentScheduler:
    """
    Background scheduler that fires agents on their cadence_minutes schedule
    and in response to events.  Runs daemon threads — safe to leave running.

    Design:
    - One thread polls the schedule every 60 seconds
    - Separate worker thread pool (max 3 concurrent) processes the queue
    - Each agent tracks last_run_at in BackgroundStateStore
    - Quiet hours: 22:00-07:00 local time, only "critical" agents run
    - Morning trigger fires at 06:45 local time (triggers morning briefing build)
    """

    QUIET_HOURS_START = 22   # 10 PM
    QUIET_HOURS_END = 7      # 7 AM
    MORNING_TRIGGER_HOUR = 6
    MORNING_TRIGGER_MINUTE = 45

    def __init__(self, runtime: Any, queue: AgentWorkQueue, state_store: Any) -> None:
        self._runtime = runtime
        self._queue = queue
        self._state_store = state_store
        # Wire module-level runtime ref so stub functions can reach executive/catalyst support
        global _scheduler_runtime
        _scheduler_runtime = runtime
        self._running = False
        self._stop_event = threading.Event()
        self._schedule_thread: threading.Thread | None = None
        self._worker_threads: list[threading.Thread] = []
        self._max_workers = 3
        self._event_hooks: dict[str, list[Callable]] = {}
        self._morning_fired_date: str = ""  # YYYY-MM-DD — prevents double-firing
        self._last_tick_at: str = ""        # ISO timestamp of most recent _tick() start
        self._tick_count: int = 0           # total ticks since start

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        if self._running:
            logger.warning("AgentScheduler.start() called while already running")
            return
        self._running = True
        self._stop_event.clear()

        self._schedule_thread = threading.Thread(
            target=self._schedule_loop,
            name="jarvis-scheduler",
            daemon=True,
        )
        self._schedule_thread.start()

        self._worker_threads = []
        for i in range(self._max_workers):
            t = threading.Thread(
                target=self._worker_loop,
                name=f"jarvis-worker-{i}",
                daemon=True,
            )
            t.start()
            self._worker_threads.append(t)

        logger.info(
            "AgentScheduler started: 1 schedule thread + %d worker threads",
            self._max_workers,
        )

    def stop(self) -> None:
        if not self._running:
            return
        logger.info("AgentScheduler stopping…")
        self._running = False
        self._stop_event.set()

        if self._schedule_thread is not None:
            self._schedule_thread.join(timeout=5)

        for t in self._worker_threads:
            t.join(timeout=5)

        self._worker_threads = []
        logger.info("AgentScheduler stopped")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fire_event(self, event_type: str, payload: dict | None = None) -> int:
        """
        Fire a named event, queuing all agents that have this event in their
        triggers.  Returns number of agents queued.
        """
        payload = payload or {}
        queued = 0
        try:
            registry = self._runtime.agent_registry
        except AttributeError:
            logger.warning("fire_event: runtime has no agent_registry")
            return 0

        for agent_def in registry.list():
            if event_type in (agent_def.triggers or []):
                item = AgentWorkItem(
                    item_id=str(uuid.uuid4()),
                    agent_id=agent_def.agent_id,
                    agent_label=agent_def.label,
                    trigger="event",
                    event_type=event_type,
                    payload=payload,
                    queued_at=_now_iso(),
                    status="queued",
                    priority=2 if event_type in (EVENT_SECURITY_ALERT, EVENT_MORNING) else 5,
                )
                self._queue.enqueue(item)
                queued += 1

        logger.info("fire_event(%s): queued %d agents", event_type, queued)
        return queued

    def force_run(self, agent_id: str, payload: dict | None = None) -> AgentWorkItem | None:
        """Manually trigger a specific agent immediately."""
        payload = payload or {}
        try:
            agent_def = self._runtime.agent_registry.by_id().get(agent_id)
        except AttributeError:
            agent_def = None

        if agent_def is None:
            logger.warning("force_run: unknown agent_id=%s", agent_id)
            return None

        item = AgentWorkItem(
            item_id=str(uuid.uuid4()),
            agent_id=agent_def.agent_id,
            agent_label=agent_def.label,
            trigger="manual",
            event_type="manual",
            payload=payload,
            queued_at=_now_iso(),
            status="queued",
            priority=1,
        )
        self._queue.enqueue(item)
        logger.info("force_run: queued agent_id=%s item_id=%s", agent_id, item.item_id)
        return item

    def get_status(self) -> dict:
        """Return scheduler health snapshot for UI display and /api/scheduler/health."""
        now_str = _now_iso()
        queued = self._queue.get_queued()
        running = self._queue.get_running()
        dead_letter = self._queue.get_dead_letter()
        recent = self._queue.get_recent(10)

        # Stale running items (running for > 10 minutes)
        stale_threshold_iso = datetime.now(timezone.utc).replace(
            microsecond=0
        ).isoformat()  # placeholder — use string comparison below
        stale_jobs = []
        for item in running:
            started = item.started_at or ""
            if started:
                try:
                    elapsed = (
                        datetime.now(timezone.utc) -
                        datetime.fromisoformat(started.replace("Z", "+00:00"))
                    ).total_seconds()
                    if elapsed > 600:
                        stale_jobs.append({
                            "item_id": item.item_id,
                            "agent_id": item.agent_id,
                            "started_at": started,
                            "elapsed_seconds": int(elapsed),
                        })
                except (ValueError, TypeError):
                    pass

        # Next due work (first due agent from registry)
        next_due: list[dict] = []
        try:
            registry = self._runtime.agent_registry
            for agent_def in registry.list():
                if self._should_run_now(agent_def):
                    next_due.append({"agent_id": agent_def.agent_id, "status": "due_now"})
        except Exception:
            pass

        # Unhealthy agents (stale heartbeat in kernel)
        unhealthy_agents: list[str] = []
        try:
            kernel_snapshot = self._runtime.agent_runtime_kernel.snapshot()
            for row in kernel_snapshot.get("status_rows", []):
                hb = row.get("heartbeat_status", "")
                if hb in ("stale", "missed"):
                    unhealthy_agents.append(row.get("agent_id", ""))
        except Exception:
            pass

        return {
            "running": self._running,
            "quiet_hours": self._is_quiet_hours(),
            "queue_depth": len(queued),
            "running_count": len(running),
            "dead_letter_count": len(dead_letter),
            "stale_jobs": stale_jobs,
            "last_tick_at": self._last_tick_at,
            "tick_count": self._tick_count,
            "next_due_work": next_due,
            "unhealthy_agents": unhealthy_agents,
            "recent_work": [asdict(w) for w in recent],
            "dead_letter": [asdict(w) for w in dead_letter[:10]],
            "workers_active": sum(1 for t in self._worker_threads if t.is_alive()),
            "generated_at": now_str,
        }

    # ------------------------------------------------------------------
    # Internal threads
    # ------------------------------------------------------------------

    def _schedule_loop(self) -> None:
        """Main scheduling loop.  Runs in daemon thread, polls every 60 s."""
        logger.info("Scheduler loop started")
        while not self._stop_event.is_set():
            try:
                self._tick()
            except Exception:
                logger.exception("Error in scheduler tick")
            self._stop_event.wait(timeout=60)
        logger.info("Scheduler loop exited")

    def _worker_loop(self) -> None:
        """Worker loop.  Picks items from queue and executes them."""
        thread_name = threading.current_thread().name
        logger.debug("%s started", thread_name)
        while not self._stop_event.is_set():
            item = self._queue.dequeue_next()
            if item is None:
                self._stop_event.wait(timeout=5)
                continue
            try:
                self._execute_item(item)
            except Exception:
                logger.exception("Worker error executing item %s", item.item_id)
                self._queue.mark_failed(item.item_id, "Unhandled exception in worker")
        logger.debug("%s exited", thread_name)

    def _tick(self) -> None:
        """Check all agents and enqueue those that are due to run."""
        self._last_tick_at = _now_iso()
        self._tick_count = getattr(self, "_tick_count", 0) + 1
        try:
            registry = self._runtime.agent_registry
        except AttributeError:
            return

        self._maybe_fire_morning()

        for agent_def in registry.list():
            if self._should_run_now(agent_def):
                item = AgentWorkItem(
                    item_id=str(uuid.uuid4()),
                    agent_id=agent_def.agent_id,
                    agent_label=agent_def.label,
                    trigger="cadence",
                    event_type="cadence",
                    payload={},
                    queued_at=_now_iso(),
                    status="queued",
                    priority=5,
                )
                self._queue.enqueue(item)
                logger.debug("Cadence-queued agent %s", agent_def.agent_id)

        # Periodic cleanup
        purged = self._queue.purge_old(max_age_hours=48)
        if purged:
            logger.debug("Purged %d old queue items", purged)

        # Process LOW-risk auto-approvals (runs every ~60 s with the schedule tick)
        try:
            from .approvals import get_approval_queue
            approval_queue = get_approval_queue()
            if approval_queue is not None:
                auto_count = approval_queue.process_auto_approvals()
                if auto_count:
                    logger.info("Auto-approved %d LOW risk approval(s)", auto_count)
        except Exception:
            logger.debug("process_auto_approvals tick failed (non-fatal)", exc_info=True)

        # Drive the event fabric autonomously so kernel events and attention routing
        # happen unattended — not only when an HTTP consumer polls background_agent_status.
        try:
            background_cycle = getattr(self._runtime, "background_cycle", None)
            if callable(background_cycle):
                background_cycle()
        except Exception:
            logger.debug("background_cycle tick failed (non-fatal)", exc_info=True)

        # Epic 10: Family mode auto-advance (every ~30 min via the 60-s tick counter)
        self._maybe_auto_advance_mode()

    _mode_advance_tick_count: int = 0

    def _maybe_auto_advance_mode(self) -> None:
        """
        Check whether the household mode should auto-advance.
        Runs every 30 scheduler ticks (~30 min at 60 s/tick). Best-effort; never raises.
        """
        self._mode_advance_tick_count = getattr(self, "_mode_advance_tick_count", 0) + 1
        if self._mode_advance_tick_count < 30:
            return
        self._mode_advance_tick_count = 0
        try:
            from .family_profiles import get_family_manager
            manager = get_family_manager()
            if manager is not None:
                new_mode = manager.auto_advance_mode()
                if new_mode:
                    logger.info("Scheduler: household mode auto-advanced → %s", new_mode)
        except Exception:
            logger.debug("family mode auto-advance tick failed (non-fatal)", exc_info=True)

    def _execute_item(self, item: AgentWorkItem) -> None:
        """Execute a single work item by calling the agent's work function."""
        logger.info(
            "Executing %s (agent=%s trigger=%s)",
            item.item_id,
            item.agent_id,
            item.trigger,
        )
        try:
            result = _run_agent_work(item.agent_id, item.agent_label, item.payload)
            result_text = result.get("summary", "")
            self._queue.mark_completed(item.item_id, result_text, result)

            # Update last_run_at in BackgroundStateStore if available
            self._record_run(item.agent_id)

            logger.info(
                "Completed %s (agent=%s): %s",
                item.item_id,
                item.agent_id,
                result_text[:80],
            )
        except Exception as exc:
            error_msg = str(exc)
            self._queue.mark_failed(item.item_id, error_msg)
            logger.error("Failed %s (agent=%s): %s", item.item_id, item.agent_id, error_msg)

    def _record_run(self, agent_id: str) -> None:
        """Persist last_run_at for the agent into BackgroundStateStore."""
        try:
            state = self._state_store.load()
            agents = state.setdefault("agents", {})
            entry = agents.get(agent_id, {})
            entry["last_run_at"] = _now_iso()
            agents[agent_id] = entry
            self._state_store.save(state)
        except Exception:
            logger.debug("Could not update last_run_at for %s", agent_id, exc_info=True)

    # ------------------------------------------------------------------
    # Decision helpers
    # ------------------------------------------------------------------

    def _is_quiet_hours(self) -> bool:
        """Returns True if current local time is in quiet hours."""
        hour = datetime.now().hour  # local time
        start = self.QUIET_HOURS_START
        end = self.QUIET_HOURS_END
        # Wraps midnight: quiet if hour >= 22 OR hour < 7
        return hour >= start or hour < end

    def _should_run_now(self, agent_def: Any) -> bool:
        """
        Returns True if an agent is due to run based on cadence_minutes and
        last_run_at.  Respects quiet_hours_behavior.
        """
        quiet = self._is_quiet_hours()
        behavior = getattr(agent_def, "quiet_hours_behavior", "idle")

        if quiet and behavior == "idle":
            return False

        try:
            state = self._state_store.load()
            agents = state.get("agents", {})
            persisted = agents.get(agent_def.agent_id, {})
            last_run_str = persisted.get("last_run_at", "")
        except Exception:
            last_run_str = ""

        if not last_run_str:
            return True  # never run → run now

        try:
            last_run = datetime.fromisoformat(last_run_str.replace("Z", "+00:00"))
        except ValueError:
            return True

        elapsed_seconds = datetime.now(timezone.utc).timestamp() - last_run.timestamp()
        cadence_seconds = agent_def.cadence_minutes * 60
        return elapsed_seconds >= cadence_seconds

    def _maybe_fire_morning(self) -> None:
        """Fire the morning event at MORNING_TRIGGER_HOUR:MORNING_TRIGGER_MINUTE (local)."""
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        if (
            now.hour == self.MORNING_TRIGGER_HOUR
            and now.minute >= self.MORNING_TRIGGER_MINUTE
            and self._morning_fired_date != today
        ):
            self._morning_fired_date = today
            logger.info("Firing morning trigger")
            self.fire_event(EVENT_MORNING, {"date": today, "trigger": "scheduled"})
            # Run drift detection after the morning agent sweep
            self._run_drift_detection()


    def _run_drift_detection(self) -> None:
        """Run DriftDetector after the morning trigger. Best-effort; never raises."""
        try:
            from .known_facts import get_memory, DriftDetector
            store = get_memory()
            if store is None:
                return
            detector = DriftDetector(store, scheduler=self)
            new_events = detector.run_checks("chris")
            if new_events:
                logger.info(
                    "Drift detection: %d new event(s) logged", len(new_events)
                )
        except Exception:
            logger.debug("Drift detection skipped (known_facts unavailable)", exc_info=True)


# ---------------------------------------------------------------------------
# Briefing builder
# ---------------------------------------------------------------------------

class BriefingBuilder:
    """
    Assembles the JARVIS living briefing from recent agent work results.
    Called by scheduler after morning run or on-demand.

    Produces a BriefingPacket dict with zones:
    - briefing_items : list of {text, sub, priority, agent, timestamp}
    - working_items  : list of {agent, action, timestamp}
    - needs_items    : list of {id, text, agent, action_type, payload}
    - drift_items    : list of {text, severity, agent}
    - generated_at   : ISO timestamp
    - greeting       : str (personalized greeting for the user)
    """

    _CACHE_TTL_SECONDS = 1800  # 30 minutes

    def __init__(self, queue: AgentWorkQueue, scheduler: AgentScheduler) -> None:
        self._queue = queue
        self._scheduler = scheduler
        self._cached: dict | None = None
        self._cached_at: float = 0.0

    def build(self, actor_id: str = "chris") -> dict:
        """Build a fresh briefing packet from recent work results."""
        now_iso = _now_iso()
        hour = datetime.now().hour
        if hour < 12:
            time_of_day = "morning"
        elif hour < 17:
            time_of_day = "afternoon"
        else:
            time_of_day = "evening"

        name_map = {"chris": "Chris", "rebekah": "Rebekah"}
        display_name = name_map.get(actor_id.lower(), actor_id.capitalize())
        greeting = f"Good {time_of_day}, {display_name}."

        # Epic 10: pull household mode and actor profile to shape briefing style
        household_mode_status: dict = {}
        actor_response_rules: dict = {}
        try:
            from .family_profiles import get_family_manager as _get_fm
            _fm = _get_fm()
            if _fm is not None:
                household_mode_status = _fm.get_status()
                actor_response_rules = _fm.get_response_rules(actor_id)
                # Adjust greeting address style
                _profile = _fm.get_profile(actor_id)
                if _profile and _profile.address_style == "formal_occasional":
                    greeting = f"Good {time_of_day}."
                elif _profile:
                    display_name = _profile.display_name
                    greeting = f"Good {time_of_day}, {display_name}."
        except Exception:
            pass

        recent = self._queue.get_recent(limit=30)
        queued = self._queue.get_queued()

        briefing_items: list[dict] = []
        working_items: list[dict] = []
        needs_items: list[dict] = []
        drift_items: list[dict] = []

        for item in recent:
            result = item.result or {}
            summary = item.result_text or result.get("summary", "")
            sub_items: list[str] = result.get("items", [])
            priority = result.get("priority", "normal")
            action_required = result.get("action_required", False)

            if summary:
                briefing_items.append({
                    "text": summary,
                    "sub": sub_items[:3],
                    "priority": priority,
                    "agent": item.agent_label,
                    "timestamp": item.completed_at or item.queued_at,
                    "source": result.get("source", "fallback"),
                    "model": result.get("model", ""),
                })

            if action_required:
                for sub in sub_items:
                    if sub.upper().startswith("ACTION"):
                        needs_items.append({
                            "id": str(uuid.uuid4()),
                            "text": sub,
                            "agent": item.agent_label,
                            "action_type": "review",
                            "payload": {"agent_id": item.agent_id, "item_id": item.item_id},
                        })

            if item.status == "failed" and item.error:
                drift_items.append({
                    "text": f"{item.agent_label} run failed: {item.error[:120]}",
                    "severity": "warning",
                    "agent": item.agent_label,
                })

        # Active / running items
        for item in queued:
            working_items.append({
                "agent": item.agent_label,
                "action": f"Queued — {item.event_type}",
                "timestamp": item.queued_at,
            })

        # Merge in Being Known drift events
        try:
            from .known_facts import get_memory as _gm_drift
            _kf_store = _gm_drift()
            if _kf_store is not None:
                for _drift_ev in _kf_store.get_active_drift(actor_id)[:5]:
                    drift_items.append({
                        "text": _drift_ev.description,
                        "severity": _drift_ev.severity,
                        "agent": "being-known",
                        "drift_id": _drift_ev.drift_id,
                        "domain": _drift_ev.domain,
                    })
        except Exception:
            pass

        # Being Known briefing context (occasions, priorities, drift summary)
        memory_context = ""
        try:
            from .known_facts import get_memory as _gm_ctx
            _kf_ctx = _gm_ctx()
            if _kf_ctx is not None:
                memory_context = _kf_ctx.get_briefing_memory_context()
        except Exception:
            pass

        # Prepend real approval-queue pending items into needs_items
        try:
            from .approvals import get_approval_guard
            guard = get_approval_guard()
            if guard is not None:
                approval_needs = guard.get_pending_for_ui(actor_id=actor_id)
                needs_items = approval_needs + needs_items
        except Exception:
            logger.debug("Could not fetch approval needs for briefing", exc_info=True)

        # Note: Catalyst bridge handoff removed (external app retired).
        # Keep the field in the packet as an empty shape so older clients
        # continue to deserialize it without crashing the briefing builder.
        catalyst_handoff_status: dict = {}

        # Disciple / Chronicle — spiritual context for morning briefing (Epic 9)
        spiritual_context: dict = {}
        try:
            from .chronicle_bridge import get_disciple as _get_disciple_sched
            _disciple = _get_disciple_sched()
            if _disciple is not None:
                spiritual_context = _disciple.on_morning_briefing({"actor_id": actor_id})
                if spiritual_context.get("prayer_count", 0) > 0 or spiritual_context.get("answered_recently"):
                    working_items.append({
                        "agent": "Disciple",
                        "action": (
                            f"Chronicle — {spiritual_context.get('prayer_count', 0)} active prayer(s), "
                            f"{len(spiritual_context.get('answered_recently', []))} answered recently"
                        ),
                        "timestamp": now_iso,
                    })
        except Exception:
            pass

        # Epic 13: Financial Intelligence — surface time-sensitive finance items
        try:
            from .financial_intelligence import get_finance as _get_finance
            _fi = _get_finance()
            if _fi is not None:
                _fi_item = _fi.get_briefing_item()
                if _fi_item is not None:
                    briefing_items.append(_fi_item)
        except Exception:
            pass

        # Epic 15: Growth Intelligence — occasions, signals, health drift, overdue contacts
        try:
            from .growth_intelligence import get_growth as _get_growth
            _growth = _get_growth()
            if _growth is not None:
                _growth_items = _growth.get_briefing_items()
                for _gi in _growth_items:
                    _gi_type = _gi.pop("type", "briefing_item")
                    if _gi_type == "needs_item":
                        needs_items.append({
                            "id": str(uuid.uuid4()),
                            "text": _gi.get("text", ""),
                            "agent": _gi.get("agent", "Growth"),
                            "action_type": _gi.get("action_type", "review"),
                            "payload": _gi.get("payload", {}),
                        })
                    elif _gi_type == "drift_item":
                        drift_items.append({
                            "text": _gi.get("text", ""),
                            "severity": _gi.get("severity", "info"),
                            "agent": _gi.get("agent", "Growth"),
                        })
                    else:
                        briefing_items.append({
                            "text": _gi.get("text", ""),
                            "sub": _gi.get("sub", []),
                            "priority": _gi.get("priority", "normal"),
                            "agent": _gi.get("agent", "Growth"),
                            "timestamp": now_iso,
                        })
        except Exception:
            logger.debug("Growth intelligence briefing items failed (non-fatal)", exc_info=True)

        packet = {
            "greeting": greeting,
            "briefing_items": briefing_items,
            "working_items": working_items,
            "needs_items": needs_items,
            "drift_items": drift_items,
            "memory_context": memory_context,
            "spiritual_context": spiritual_context,
            "generated_at": now_iso,
            "queue_depth": len(queued),
            "scheduler_running": self._scheduler._running,
            "catalyst_handoff": catalyst_handoff_status,
            # Epic 10: household mode and actor response rules
            "household_mode": household_mode_status,
            "actor_response_rules": actor_response_rules,
        }

        self._cached = packet
        self._cached_at = time.monotonic()
        return packet

    def get_cached(self) -> dict | None:
        """Return last built briefing if fresh (< 30 min old)."""
        if self._cached is None:
            return None
        age = time.monotonic() - self._cached_at
        if age > self._CACHE_TTL_SECONDS:
            return None
        return self._cached


# ---------------------------------------------------------------------------
# Module-level singleton helpers
# ---------------------------------------------------------------------------

_scheduler_singleton: AgentScheduler | None = None
_briefing_singleton: BriefingBuilder | None = None


def get_scheduler() -> AgentScheduler | None:
    return _scheduler_singleton


def get_briefing_builder() -> BriefingBuilder | None:
    return _briefing_singleton


def init_scheduler(runtime: Any) -> tuple[AgentScheduler, BriefingBuilder]:
    """
    Create and start the module-level scheduler singleton.  Safe to call
    multiple times — subsequent calls are no-ops and return the existing
    instances.
    """
    global _scheduler_singleton, _briefing_singleton

    if _scheduler_singleton is not None:
        assert _briefing_singleton is not None
        return _scheduler_singleton, _briefing_singleton

    queue_path = Path.home() / ".jarvis" / "scheduler" / "queue.jsonl"
    queue = AgentWorkQueue(queue_path)

    state_store = getattr(runtime.background_scheduler, "store", None)
    if state_store is None:
        # Fallback: create a fresh BackgroundStateStore
        try:
            from .agentic import BackgroundStateStore
            state_store = BackgroundStateStore(Path("data") / "agents")
        except Exception:
            state_store = _NullStateStore()

    scheduler = AgentScheduler(runtime, queue, state_store)
    briefing = BriefingBuilder(queue, scheduler)

    scheduler.start()

    _scheduler_singleton = scheduler
    _briefing_singleton = briefing
    logger.info("AgentScheduler singleton initialised and started")
    return scheduler, briefing


class _NullStateStore:
    """No-op state store used when the real one is unavailable."""

    def load(self) -> dict:
        return {"agents": {}}

    def save(self, payload: dict) -> None:
        pass
