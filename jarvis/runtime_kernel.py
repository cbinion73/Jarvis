from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
import uuid
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .agentic import AgentDefinition, AgentRegistry

SCHEMA_VERSION = "1.0"
DEFAULT_HEARTBEAT_STALE_AFTER_SECONDS = 180
DEFAULT_HEARTBEAT_MISSED_AFTER_SECONDS = 600

LIFECYCLE_IDLE = "idle"
LIFECYCLE_WAKING = "waking"
LIFECYCLE_RUNNING = "running"
LIFECYCLE_PAUSED = "paused"
LIFECYCLE_INTERRUPTED = "interrupted"
LIFECYCLE_BLOCKED = "blocked"
LIFECYCLE_ESCALATING = "escalating"
LIFECYCLE_RETIRING = "retiring"
LIFECYCLE_RETIRED = "retired"

CONTROL_ACTIONS = {
    "wake",
    "pause",
    "resume",
    "interrupt",
    "escalate",
    "retire",
    "retire-now",
}

ACTIVE_LIFECYCLE_STATES = {
    LIFECYCLE_WAKING,
    LIFECYCLE_RUNNING,
    LIFECYCLE_INTERRUPTED,
    LIFECYCLE_BLOCKED,
    LIFECYCLE_ESCALATING,
    LIFECYCLE_RETIRING,
}


def _now() -> datetime:
    return datetime.now(UTC)


def _iso(value: datetime) -> str:
    return value.isoformat()


def _parse_iso(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _age_seconds(now: datetime, value: str) -> int | None:
    parsed = _parse_iso(value)
    if parsed is None:
        return None
    return max(0, int((now - parsed).total_seconds()))


def _clock_minutes(value: str) -> int:
    hours, minutes = value.split(":", 1)
    return int(hours) * 60 + int(minutes)


def _within_quiet_hours(now: datetime, start: str, end: str) -> bool:
    start_minutes = _clock_minutes(start)
    end_minutes = _clock_minutes(end)
    current = now.hour * 60 + now.minute
    if start_minutes <= end_minutes:
        return start_minutes <= current < end_minutes
    return current >= start_minutes or current < end_minutes


class AgentRuntimeKernelStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.state_path = self.root / "runtime_kernel_state.json"
        self.event_log_path = self.root / "runtime_kernel_events.jsonl"

    def load(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return self.default_state()
        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return self.default_state()
        if not isinstance(payload, dict):
            return self.default_state()
        payload.setdefault("schema_version", SCHEMA_VERSION)
        payload.setdefault("agents", {})
        payload.setdefault("updated_at", "")
        return payload

    def save(self, payload: dict[str, Any]) -> None:
        payload = dict(payload)
        payload["schema_version"] = SCHEMA_VERSION
        self.state_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def append_event(self, payload: dict[str, Any]) -> None:
        with self.event_log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload) + "\n")

    def list_events(self, *, agent_id: str = "", limit: int = 40) -> list[dict[str, Any]]:
        if not self.event_log_path.exists():
            return []
        records: list[dict[str, Any]] = []
        for line in self.event_log_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if agent_id and str(payload.get("agent_id", "")).strip() != agent_id.strip():
                continue
            records.append(payload)
        return list(reversed(records[-max(1, int(limit)):]))

    def default_state(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "updated_at": "",
            "agents": {},
        }


class AgentRuntimeKernel:
    def __init__(
        self,
        store: AgentRuntimeKernelStore,
        registry: AgentRegistry,
        *,
        heartbeat_stale_after_seconds: int = DEFAULT_HEARTBEAT_STALE_AFTER_SECONDS,
        heartbeat_missed_after_seconds: int = DEFAULT_HEARTBEAT_MISSED_AFTER_SECONDS,
    ) -> None:
        self.store = store
        self.registry = registry
        self.heartbeat_stale_after_seconds = max(30, int(heartbeat_stale_after_seconds))
        self.heartbeat_missed_after_seconds = max(
            self.heartbeat_stale_after_seconds + 1,
            int(heartbeat_missed_after_seconds),
        )

    def migrate_legacy_background_state(self, payload: dict[str, Any]) -> None:
        state = self.store.load()
        if state.get("agents"):
            return
        legacy_agents = payload.get("agents", {}) if isinstance(payload, dict) else {}
        if not isinstance(legacy_agents, dict):
            return
        now = _now()
        migrated: dict[str, Any] = {}
        definitions = self.registry.by_id()
        for agent_id, raw in legacy_agents.items():
            definition = definitions.get(agent_id)
            if definition is None or not isinstance(raw, dict):
                continue
            entry = self._default_entry(definition, now=now)
            legacy_state = str(raw.get("state", "")).strip().lower()
            if legacy_state == "awake":
                entry["lifecycle"]["current_state"] = LIFECYCLE_RUNNING
                entry["lifecycle"]["desired_state"] = LIFECYCLE_RUNNING
            elif legacy_state == "blocked":
                entry["lifecycle"]["current_state"] = LIFECYCLE_BLOCKED
                entry["lifecycle"]["desired_state"] = LIFECYCLE_RUNNING
            else:
                entry["lifecycle"]["current_state"] = LIFECYCLE_IDLE
                entry["lifecycle"]["desired_state"] = LIFECYCLE_IDLE
            last_run_at = str(raw.get("last_run_at", "")).strip()
            next_run_at = str(raw.get("next_run_at", "")).strip()
            if last_run_at:
                entry["run"]["last_started_at"] = last_run_at
                entry["run"]["last_heartbeat_at"] = last_run_at
                entry["heartbeat"]["last_heartbeat_at"] = last_run_at
            if next_run_at:
                entry["run"]["next_due_at"] = next_run_at
            migrated[agent_id] = entry
        state["agents"] = migrated
        state["updated_at"] = _iso(now)
        self.store.save(state)

    def apply_control(
        self,
        agent_id: str,
        action: str,
        *,
        actor: str = "system",
        reason: str = "",
        execution_lane: str = "",
        recorded_at: datetime | None = None,
    ) -> dict[str, Any]:
        command = str(action or "").strip().lower()
        if command not in CONTROL_ACTIONS:
            raise ValueError(f"Unsupported lifecycle action: {action}")
        now = recorded_at or _now()
        state = self._load_synced_state(now=now)
        entry = self._require_entry(state, agent_id, now=now)
        lifecycle = entry["lifecycle"]
        run = entry["run"]
        supervision = entry["supervision"]
        previous_state = str(lifecycle.get("current_state", LIFECYCLE_IDLE))
        note = reason.strip()

        if command == "wake":
            self._ensure_not_retired(previous_state)
            lifecycle["current_state"] = LIFECYCLE_WAKING
            lifecycle["desired_state"] = LIFECYCLE_RUNNING
            lifecycle["wake_reason"] = note or "manual-wake"
            run["run_id"] = run.get("run_id") or self._run_id()
            run["status"] = LIFECYCLE_WAKING
            run["wake_count"] = int(run.get("wake_count", 0) or 0) + 1
            run["last_started_at"] = _iso(now)
            supervision["attention_reason"] = ""
        elif command == "pause":
            self._ensure_not_retired(previous_state)
            lifecycle["current_state"] = LIFECYCLE_PAUSED
            lifecycle["desired_state"] = LIFECYCLE_PAUSED
            lifecycle["pause_reason"] = note or "manual-pause"
            lifecycle["paused_at"] = _iso(now)
            run["status"] = LIFECYCLE_PAUSED
        elif command == "resume":
            self._ensure_not_retired(previous_state)
            lifecycle["current_state"] = LIFECYCLE_WAKING
            lifecycle["desired_state"] = LIFECYCLE_RUNNING
            lifecycle["resume_reason"] = note or "manual-resume"
            lifecycle["resumed_at"] = _iso(now)
            run["run_id"] = run.get("run_id") or self._run_id()
            run["status"] = LIFECYCLE_WAKING
            run["resume_count"] = int(run.get("resume_count", 0) or 0) + 1
        elif command == "interrupt":
            self._ensure_not_retired(previous_state)
            lifecycle["current_state"] = LIFECYCLE_INTERRUPTED
            lifecycle["desired_state"] = LIFECYCLE_PAUSED
            lifecycle["interrupt_reason"] = note or "manual-interrupt"
            lifecycle["interrupted_at"] = _iso(now)
            run["status"] = LIFECYCLE_INTERRUPTED
            run["interrupt_count"] = int(run.get("interrupt_count", 0) or 0) + 1
            supervision["requires_attention"] = True
            supervision["attention_reason"] = lifecycle["interrupt_reason"]
        elif command == "escalate":
            self._ensure_not_retired(previous_state)
            lifecycle["current_state"] = LIFECYCLE_ESCALATING
            lifecycle["desired_state"] = LIFECYCLE_ESCALATING
            lifecycle["escalation_reason"] = note or "manual-escalation"
            lifecycle["escalated_at"] = _iso(now)
            run["status"] = LIFECYCLE_ESCALATING
            run["escalation_count"] = int(run.get("escalation_count", 0) or 0) + 1
            supervision["requires_attention"] = True
            supervision["attention_reason"] = lifecycle["escalation_reason"]
        elif command == "retire":
            self._ensure_not_retired(previous_state)
            lifecycle["current_state"] = LIFECYCLE_RETIRING
            lifecycle["desired_state"] = LIFECYCLE_RETIRED
            lifecycle["retire_reason"] = note or "manual-retire"
            lifecycle["retirement_requested_at"] = _iso(now)
            run["status"] = LIFECYCLE_RETIRING
            supervision["requires_attention"] = True
            supervision["attention_reason"] = lifecycle["retire_reason"]
        elif command == "retire-now":
            lifecycle["current_state"] = LIFECYCLE_RETIRED
            lifecycle["desired_state"] = LIFECYCLE_RETIRED
            lifecycle["retire_reason"] = note or "manual-retire-now"
            lifecycle["retired_at"] = _iso(now)
            run["status"] = LIFECYCLE_RETIRED
            run["run_id"] = ""
            supervision["requires_attention"] = False
            supervision["attention_reason"] = ""

        if execution_lane.strip():
            run["execution_lane"] = execution_lane.strip()
        lifecycle["last_transition_at"] = _iso(now)
        lifecycle["last_transition_by"] = actor.strip() or "system"
        lifecycle["last_transition_action"] = command
        state["updated_at"] = _iso(now)
        self.store.save(state)
        self.store.append_event(
            {
                "event_id": str(uuid.uuid4()),
                "recorded_at": _iso(now),
                "agent_id": entry["agent_id"],
                "action": command,
                "actor": actor.strip() or "system",
                "reason": note,
                "previous_state": previous_state,
                "current_state": lifecycle["current_state"],
                "desired_state": lifecycle["desired_state"],
                "run_id": run.get("run_id", ""),
            }
        )
        snapshot = self.snapshot(observed_at=now)
        return {
            "ok": True,
            "action": command,
            "agent": snapshot["agents"][entry["agent_id"]],
            "summary": snapshot["summary"],
        }

    def record_heartbeat(
        self,
        agent_id: str,
        *,
        actor: str = "system",
        note: str = "",
        run_id: str = "",
        observed_at: datetime | None = None,
    ) -> dict[str, Any]:
        now = observed_at or _now()
        state = self._load_synced_state(now=now)
        entry = self._require_entry(state, agent_id, now=now)
        heartbeat = entry["heartbeat"]
        run = entry["run"]
        lifecycle = entry["lifecycle"]
        heartbeat["last_heartbeat_at"] = _iso(now)
        heartbeat["last_heartbeat_note"] = note.strip()
        heartbeat["last_heartbeat_by"] = actor.strip() or "system"
        run["last_heartbeat_at"] = heartbeat["last_heartbeat_at"]
        run["run_id"] = run_id.strip() or run.get("run_id") or self._run_id()
        if lifecycle.get("current_state") == LIFECYCLE_WAKING:
            lifecycle["current_state"] = LIFECYCLE_RUNNING
            lifecycle["desired_state"] = LIFECYCLE_RUNNING
            lifecycle["last_transition_at"] = _iso(now)
            lifecycle["last_transition_action"] = "heartbeat-promote"
            run["status"] = LIFECYCLE_RUNNING
        state["updated_at"] = _iso(now)
        self.store.save(state)
        self.store.append_event(
            {
                "event_id": str(uuid.uuid4()),
                "recorded_at": _iso(now),
                "agent_id": entry["agent_id"],
                "action": "heartbeat",
                "actor": actor.strip() or "system",
                "reason": note.strip(),
                "current_state": lifecycle["current_state"],
                "run_id": run["run_id"],
            }
        )
        snapshot = self.snapshot(observed_at=now)
        return {
            "ok": True,
            "agent": snapshot["agents"][entry["agent_id"]],
            "summary": snapshot["summary"],
        }

    def snapshot(
        self,
        *,
        active_mode: str = "",
        integration_status: list[dict[str, Any]] | None = None,
        recent_activity: list[dict[str, Any]] | None = None,
        quiet_hours: tuple[str, str] = ("22:00", "06:00"),
        observed_at: datetime | None = None,
    ) -> dict[str, Any]:
        now = observed_at or _now()
        state = self._load_synced_state(now=now)
        integration_map = self._integration_map(integration_status or [])
        recent_modules = [
            str(item.get("module", "")).strip().lower()
            for item in list(recent_activity or [])[:10]
            if str(item.get("module", "")).strip()
        ]
        quiet_active = _within_quiet_hours(now, quiet_hours[0], quiet_hours[1])
        rows: list[dict[str, Any]] = []
        agents = state.get("agents", {})
        for definition in self.registry.list():
            entry = agents.get(definition.agent_id)
            if not isinstance(entry, dict):
                entry = self._default_entry(definition, now=now)
                agents[definition.agent_id] = entry
            row = self._refresh_entry(
                entry,
                definition,
                integration_map=integration_map,
                recent_modules=recent_modules,
                active_mode=active_mode,
                quiet_active=quiet_active,
                now=now,
            )
            rows.append(row)
        state["updated_at"] = _iso(now)
        self.store.save(state)
        return {
            "generated_at": _iso(now),
            "schema_version": SCHEMA_VERSION,
            "active_mode": active_mode,
            "quiet_hours_active": quiet_active,
            "summary": self._summary(rows),
            "agents": agents,
            "status_rows": rows,
            "supported_actions": sorted(CONTROL_ACTIONS),
        }

    def _load_synced_state(self, *, now: datetime) -> dict[str, Any]:
        state = self.store.load()
        agents = state.setdefault("agents", {})
        existing = set(agents.keys())
        for definition in self.registry.list():
            if definition.agent_id not in existing:
                agents[definition.agent_id] = self._default_entry(definition, now=now)
        return state

    def _require_entry(self, state: dict[str, Any], agent_id: str, *, now: datetime) -> dict[str, Any]:
        definition = self.registry.by_id().get(agent_id.strip())
        if definition is None:
            raise KeyError(f"Unknown agent: {agent_id}")
        entry = state.setdefault("agents", {}).get(definition.agent_id)
        if not isinstance(entry, dict):
            entry = self._default_entry(definition, now=now)
            state["agents"][definition.agent_id] = entry
        return entry

    def _default_entry(self, definition: AgentDefinition, *, now: datetime) -> dict[str, Any]:
        current_state = LIFECYCLE_RUNNING if definition.agent_id == "ambient-router" else LIFECYCLE_IDLE
        run_id = self._run_id() if current_state == LIFECYCLE_RUNNING else ""
        timestamp = _iso(now)
        return {
            "agent_id": definition.agent_id,
            "label": definition.label,
            "contract": {
                "title": definition.label,
                "role": definition.purpose,
                "mission": definition.purpose,
                "lane_owner": definition.primary_domain,
                "execution_lane": definition.primary_domain,
                "authority_boundary": definition.autonomy_posture,
                "cadence_minutes": definition.cadence_minutes,
                "trust_zone": definition.trust_zone,
                "sandbox_class": definition.agent_class,
                "escalation_target": "jarvis-orchestrator",
                "allowed_tools": list(definition.allowed_tools),
                "mission_roles": list(definition.mission_roles),
                "success_metrics": list(definition.success_metrics),
            },
            "lifecycle": {
                "current_state": current_state,
                "desired_state": current_state,
                "last_transition_at": timestamp,
                "last_transition_by": "runtime-kernel-bootstrap",
                "last_transition_action": "bootstrap",
                "wake_reason": "front-door-availability" if definition.agent_id == "ambient-router" else "",
                "pause_reason": "",
                "resume_reason": "",
                "interrupt_reason": "",
                "escalation_reason": "",
                "retire_reason": "",
            },
            "run": {
                "run_id": run_id,
                "status": current_state,
                "execution_lane": definition.primary_domain,
                "run_revision": 1 if run_id else 0,
                "wake_count": 1 if run_id else 0,
                "resume_count": 0,
                "interrupt_count": 0,
                "escalation_count": 0,
                "last_started_at": timestamp if run_id else "",
                "last_heartbeat_at": timestamp if run_id else "",
                "next_due_at": _iso(now + timedelta(minutes=definition.cadence_minutes)),
            },
            "heartbeat": {
                "last_heartbeat_at": timestamp if run_id else "",
                "status": "fresh" if run_id else "unknown",
                "stale_after_seconds": self.heartbeat_stale_after_seconds,
                "missed_after_seconds": self.heartbeat_missed_after_seconds,
                "last_heartbeat_note": "",
                "last_heartbeat_by": "",
            },
            "health": {
                "status": "healthy" if run_id else "standing-by",
                "reason": "Front-door routing stays available." if run_id else "Standing by.",
                "blocked_dependencies": [],
                "quiet_hours_posture": definition.quiet_hours_behavior,
            },
            "supervision": {
                "requires_attention": False,
                "attention_reason": "",
                "last_operator_note": "",
            },
        }

    def _refresh_entry(
        self,
        entry: dict[str, Any],
        definition: AgentDefinition,
        *,
        integration_map: dict[str, bool],
        recent_modules: list[str],
        active_mode: str,
        quiet_active: bool,
        now: datetime,
    ) -> dict[str, Any]:
        lifecycle = entry["lifecycle"]
        run = entry["run"]
        heartbeat = entry["heartbeat"]
        health = entry["health"]
        supervision = entry["supervision"]
        current_state = str(lifecycle.get("current_state", LIFECYCLE_IDLE))

        blocked_dependencies = [
            dep for dep in definition.dependencies if not integration_map.get(dep, False)
        ]
        heartbeat_status = self._heartbeat_status(now, heartbeat)
        lifecycle_reason = self._state_reason(
            current_state=current_state,
            lifecycle=lifecycle,
            blocked_dependencies=blocked_dependencies,
            quiet_active=quiet_active,
            definition=definition,
            recent_modules=recent_modules,
            active_mode=active_mode,
        )

        if current_state == LIFECYCLE_WAKING and not blocked_dependencies:
            lifecycle["current_state"] = LIFECYCLE_RUNNING
            current_state = LIFECYCLE_RUNNING
            run["status"] = LIFECYCLE_RUNNING
            lifecycle["last_transition_action"] = "wake-promote"
            lifecycle["last_transition_at"] = lifecycle.get("last_transition_at") or _iso(now)
        if current_state == LIFECYCLE_RETIRING and not run.get("run_id"):
            lifecycle["current_state"] = LIFECYCLE_RETIRED
            current_state = LIFECYCLE_RETIRED
            run["status"] = LIFECYCLE_RETIRED
            lifecycle["retired_at"] = _iso(now)
        if current_state not in {LIFECYCLE_PAUSED, LIFECYCLE_INTERRUPTED, LIFECYCLE_ESCALATING, LIFECYCLE_RETIRING, LIFECYCLE_RETIRED}:
            if blocked_dependencies:
                lifecycle["current_state"] = LIFECYCLE_BLOCKED
                lifecycle["desired_state"] = LIFECYCLE_RUNNING
                current_state = LIFECYCLE_BLOCKED
                run["status"] = LIFECYCLE_BLOCKED
            elif current_state == LIFECYCLE_BLOCKED and not blocked_dependencies:
                lifecycle["current_state"] = LIFECYCLE_RUNNING if run.get("run_id") else LIFECYCLE_IDLE
                current_state = lifecycle["current_state"]
                run["status"] = current_state

        if current_state == LIFECYCLE_RUNNING and not run.get("run_id"):
            run["run_id"] = self._run_id()
            run["run_revision"] = int(run.get("run_revision", 0) or 0) + 1
            run["wake_count"] = int(run.get("wake_count", 0) or 0) + 1
            run["last_started_at"] = run.get("last_started_at") or _iso(now)
        if current_state in {LIFECYCLE_IDLE, LIFECYCLE_RETIRED}:
            supervision["requires_attention"] = False if current_state == LIFECYCLE_RETIRED else bool(supervision.get("requires_attention", False))
        if current_state == LIFECYCLE_RUNNING and heartbeat_status == "missed":
            supervision["requires_attention"] = True
            supervision["attention_reason"] = "Heartbeat missed while running."
        elif current_state == LIFECYCLE_RUNNING and heartbeat_status == "stale" and not supervision.get("attention_reason"):
            supervision["attention_reason"] = "Heartbeat stale."

        health["blocked_dependencies"] = blocked_dependencies
        health["quiet_hours_posture"] = definition.quiet_hours_behavior
        health["status"], health["reason"] = self._health_summary(
            current_state=current_state,
            blocked_dependencies=blocked_dependencies,
            heartbeat_status=heartbeat_status,
            quiet_active=quiet_active,
            definition=definition,
            lifecycle_reason=lifecycle_reason,
        )
        heartbeat["status"] = heartbeat_status

        last_started = str(run.get("last_started_at", "")).strip()
        last_started_dt = _parse_iso(last_started) or now
        next_due = last_started_dt + timedelta(minutes=definition.cadence_minutes)
        run["next_due_at"] = _iso(next_due)
        due_now = now >= next_due

        return {
            "agent_id": definition.agent_id,
            "label": definition.label,
            "state": lifecycle["current_state"],
            "desired_state": lifecycle["desired_state"],
            "reason": lifecycle_reason,
            "cadence_minutes": definition.cadence_minutes,
            "dependencies": list(definition.dependencies),
            "blocked_dependencies": blocked_dependencies,
            "owns": list(definition.owns),
            "memory_scope": list(definition.memory_scope),
            "last_run_at": last_started,
            "next_run_at": run["next_due_at"],
            "due_now": due_now,
            "priority": self._priority_for(
                current_state=lifecycle["current_state"],
                due_now=due_now,
                blocked_dependencies=blocked_dependencies,
                supervision=supervision,
            ),
            "execution_lane": str(run.get("execution_lane", definition.primary_domain)),
            "run_id": str(run.get("run_id", "")),
            "heartbeat_status": heartbeat_status,
            "health_status": health["status"],
            "attention_required": bool(supervision.get("requires_attention", False)),
            "attention_reason": str(supervision.get("attention_reason", "")),
            "shared_doctrine": [],
        }

    def _heartbeat_status(self, now: datetime, heartbeat: dict[str, Any]) -> str:
        age = _age_seconds(now, str(heartbeat.get("last_heartbeat_at", "")))
        if age is None:
            return "unknown"
        if age >= int(heartbeat.get("missed_after_seconds", self.heartbeat_missed_after_seconds)):
            return "missed"
        if age >= int(heartbeat.get("stale_after_seconds", self.heartbeat_stale_after_seconds)):
            return "stale"
        return "fresh"

    def _health_summary(
        self,
        *,
        current_state: str,
        blocked_dependencies: list[str],
        heartbeat_status: str,
        quiet_active: bool,
        definition: AgentDefinition,
        lifecycle_reason: str,
    ) -> tuple[str, str]:
        if current_state == LIFECYCLE_RETIRED:
            return "retired", lifecycle_reason
        if current_state == LIFECYCLE_RETIRING:
            return "retiring", lifecycle_reason
        if current_state == LIFECYCLE_ESCALATING:
            return "attention", lifecycle_reason
        if current_state == LIFECYCLE_INTERRUPTED:
            return "attention", lifecycle_reason
        if current_state == LIFECYCLE_PAUSED:
            return "paused", lifecycle_reason
        if blocked_dependencies:
            return "blocked", lifecycle_reason
        if current_state == LIFECYCLE_RUNNING and heartbeat_status == "missed":
            return "degraded", "Heartbeat missed while the agent is marked running."
        if current_state == LIFECYCLE_RUNNING and heartbeat_status == "stale":
            return "watch", "Heartbeat is stale and should be checked."
        if quiet_active and definition.quiet_hours_behavior == "idle" and current_state == LIFECYCLE_IDLE:
            return "quiet-hours", lifecycle_reason
        if current_state == LIFECYCLE_RUNNING:
            return "healthy", lifecycle_reason
        if current_state == LIFECYCLE_WAKING:
            return "starting", lifecycle_reason
        return "standing-by", lifecycle_reason

    def _state_reason(
        self,
        *,
        current_state: str,
        lifecycle: dict[str, Any],
        blocked_dependencies: list[str],
        quiet_active: bool,
        definition: AgentDefinition,
        recent_modules: list[str],
        active_mode: str,
    ) -> str:
        if current_state == LIFECYCLE_PAUSED:
            return str(lifecycle.get("pause_reason", "") or "Paused by operator.")
        if current_state == LIFECYCLE_INTERRUPTED:
            return str(lifecycle.get("interrupt_reason", "") or "Interrupted for operator review.")
        if current_state == LIFECYCLE_ESCALATING:
            return str(lifecycle.get("escalation_reason", "") or "Escalated for review.")
        if current_state == LIFECYCLE_RETIRING:
            return str(lifecycle.get("retire_reason", "") or "Retirement requested.")
        if current_state == LIFECYCLE_RETIRED:
            return str(lifecycle.get("retire_reason", "") or "Retired from active runtime.")
        if blocked_dependencies:
            return "Waiting on " + ", ".join(blocked_dependencies)
        if definition.agent_id == "ambient-router":
            return "Front-door routing stays available."
        lowered_mode = active_mode.lower()
        if quiet_active and definition.quiet_hours_behavior == "idle":
            return "Quiet hours posture in effect."
        if current_state == LIFECYCLE_RUNNING and (
            any(owner.lower() in recent_modules for owner in definition.owns)
            or self._mode_match(lowered_mode, definition.agent_id)
        ):
            return f"Current mode '{active_mode}' or recent work makes this agent relevant."
        if current_state == LIFECYCLE_RUNNING:
            return "Running in its assigned execution lane."
        if current_state == LIFECYCLE_WAKING:
            return str(lifecycle.get("wake_reason", "") or "Wake requested.")
        return "Standing by until its next useful window."

    def _priority_for(
        self,
        *,
        current_state: str,
        due_now: bool,
        blocked_dependencies: list[str],
        supervision: dict[str, Any],
    ) -> str:
        if blocked_dependencies:
            return "hold"
        if current_state in {LIFECYCLE_ESCALATING, LIFECYCLE_INTERRUPTED, LIFECYCLE_RETIRING}:
            return "attention"
        if bool(supervision.get("requires_attention", False)):
            return "attention"
        if current_state in {LIFECYCLE_RUNNING, LIFECYCLE_WAKING}:
            return "high" if due_now else "medium"
        if current_state == LIFECYCLE_PAUSED:
            return "hold"
        if current_state == LIFECYCLE_RETIRED:
            return "retired"
        return "medium" if due_now else "low"

    def _integration_map(self, integration_status: list[dict[str, Any]]) -> dict[str, bool]:
        mapping: dict[str, bool] = {}
        for item in integration_status:
            name = str(item.get("name", "")).lower()
            ok = bool(item.get("ok", False))
            if "home assistant" in name:
                mapping["home_assistant"] = ok
            if "perception" in name:
                mapping["perception"] = ok
            if "openai" in name or "api" in name:
                mapping["openai"] = ok
        return mapping

    def _mode_match(self, lowered_mode: str, agent_id: str) -> bool:
        return (
            (agent_id == "family-logistics" and any(key in lowered_mode for key in ("family", "dinner", "dawn", "goodnight")))
            or (agent_id == "executive-watch" and any(key in lowered_mode for key in ("work", "deep")))
            or (agent_id == "chronicle-curator" and "chronicle" in lowered_mode)
            or (agent_id == "workshop-watch" and "workshop" in lowered_mode)
            or (agent_id == "home-ops" and any(key in lowered_mode for key in ("night", "watchtower", "family", "movie")))
            or (agent_id == "watchtower" and any(key in lowered_mode for key in ("watch", "night", "goodnight")))
            or (agent_id == "storm" and any(key in lowered_mode for key in ("weather", "travel", "watch", "family", "outdoor", "storm")))
        )

    def _summary(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        counts: dict[str, int] = {}
        attention_required = 0
        running = 0
        for row in rows:
            state = str(row.get("state", "unknown"))
            counts[state] = counts.get(state, 0) + 1
            if bool(row.get("attention_required", False)):
                attention_required += 1
            if state == LIFECYCLE_RUNNING:
                running += 1
        return {
            "total_agents": len(rows),
            "running_agents": running,
            "attention_required": attention_required,
            "lifecycle_counts": counts,
        }

    def _run_id(self) -> str:
        return f"run-{uuid.uuid4().hex[:12]}"

    def _ensure_not_retired(self, current_state: str) -> None:
        if current_state == LIFECYCLE_RETIRED:
            raise ValueError("Retired agents cannot be controlled without re-registration.")
