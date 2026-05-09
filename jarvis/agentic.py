from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path


def _now() -> datetime:
    return datetime.now(UTC)


def _now_iso() -> str:
    return _now().isoformat()


def _parse_iso(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


@dataclass(slots=True)
class AgentDefinition:
    agent_id: str
    label: str
    purpose: str
    cadence_minutes: int
    triggers: list[str]
    dependencies: list[str]
    memory_scope: list[str]
    owns: list[str]
    quiet_hours_behavior: str = "idle"


@dataclass(slots=True)
class AgentStatus:
    agent_id: str
    label: str
    state: str
    reason: str
    cadence_minutes: int
    dependencies: list[str]
    blocked_dependencies: list[str]
    owns: list[str]
    memory_scope: list[str]
    last_run_at: str
    next_run_at: str
    due_now: bool
    priority: str


@dataclass(slots=True)
class LifeAgentProfile:
    agent_id: str
    label: str
    tier: str
    role: str
    personality: str
    instructions: str
    knowledge: str
    logic: str
    connections: list[str]
    enabled: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


class BackgroundStateStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.state_path = self.root / "background_state.json"
        self.tick_log_path = self.root / "tick_log.jsonl"

    def load(self) -> dict:
        if not self.state_path.exists():
            return {"agents": {}, "last_tick_at": ""}
        try:
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"agents": {}, "last_tick_at": ""}

    def save(self, payload: dict) -> None:
        self.state_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def log_tick(self, snapshot: dict) -> None:
        with self.tick_log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(snapshot) + "\n")


class AgentRegistry:
    def __init__(self) -> None:
        self._agents = [
            AgentDefinition(
                agent_id="ambient-router",
                label="Ambient Router",
                purpose="Maintain the front-door JARVIS shell, classify incoming requests, and keep the live conversational layer coherent.",
                cadence_minutes=1,
                triggers=["voice request", "typed command", "mode change"],
                dependencies=[],
                memory_scope=["session", "routing"],
                owns=["voice shell", "request routing", "wake-word posture"],
            ),
            AgentDefinition(
                agent_id="family-logistics",
                label="Family Logistics",
                purpose="Watch family rhythm, departure prep, dinner flow, and the calm version of tonight.",
                cadence_minutes=10,
                triggers=["family mode", "departure window", "meal window", "school rhythm"],
                dependencies=[],
                memory_scope=["household", "personal"],
                owns=["family plans", "meal timing", "departure checklists"],
            ),
            AgentDefinition(
                agent_id="executive-watch",
                label="Executive Watch",
                purpose="Stage meeting prep, writing support, and decision framing without hijacking the house.",
                cadence_minutes=20,
                triggers=["office context", "meeting prep", "writing session"],
                dependencies=["openai"],
                memory_scope=["project", "personal"],
                owns=["briefs", "follow-ups", "research staging"],
            ),
            AgentDefinition(
                agent_id="catalyst-personal",
                label="Catalyst Personal",
                purpose="Run personal workflow intelligence for mail triage, meeting prep, project planning, and proactive surfacing without work-only infrastructure.",
                cadence_minutes=20,
                triggers=["manual capture", "meeting transcript", "project planning", "inbox review"],
                dependencies=["openai"],
                memory_scope=["project", "personal"],
                owns=["workflow runs", "signal triage", "briefing recommendations"],
            ),
            AgentDefinition(
                agent_id="chronicle-curator",
                label="Chronicle Curator",
                purpose="Track spiritual themes, devotional cadence, and reflection continuity.",
                cadence_minutes=30,
                triggers=["devotional request", "reflection capture", "Chronicle mode"],
                dependencies=["openai"],
                memory_scope=["project", "personal"],
                owns=["Chronicle entries", "theme summaries", "devotional staging"],
            ),
            AgentDefinition(
                agent_id="workshop-watch",
                label="Workshop Watch",
                purpose="Prepare maker plans, printer handoffs, and safety posture for active builds.",
                cadence_minutes=15,
                triggers=["workshop mode", "print prep", "part inspection"],
                dependencies=[],
                memory_scope=["project", "safety"],
                owns=["workshop plans", "print staging", "vendor prep"],
            ),
            AgentDefinition(
                agent_id="home-ops",
                label="Home Ops",
                purpose="Track household control state, lighting, garage, climate, and routine scene readiness.",
                cadence_minutes=5,
                triggers=["mode transition", "garage event", "lighting scene", "climate change"],
                dependencies=["home_assistant"],
                memory_scope=["household", "safety"],
                owns=["home actions", "scene posture", "core routines"],
            ),
            AgentDefinition(
                agent_id="watchtower",
                label="Watchtower",
                purpose="Surface only meaningful household anomalies, alerts, and overnight concerns.",
                cadence_minutes=5,
                triggers=["safety alert", "weather change", "arrival event", "anomaly"],
                dependencies=["perception", "home_assistant"],
                memory_scope=["safety", "household"],
                owns=["incident review", "overnight watch", "anomaly triage"],
            ),
            AgentDefinition(
                agent_id="memory-curator",
                label="Memory Curator",
                purpose="Decide what deserves durable memory instead of allowing the system to become a sentimental junk drawer.",
                cadence_minutes=15,
                triggers=["meaningful preference", "repeated friction", "project continuity", "safety fact"],
                dependencies=[],
                memory_scope=["household", "personal", "project", "safety"],
                owns=["memory proposals", "forget posture", "curation rules"],
            ),
        ]

    def list(self) -> list[AgentDefinition]:
        return list(self._agents)

    def by_id(self) -> dict[str, AgentDefinition]:
        return {agent.agent_id: agent for agent in self._agents}


class LifeAgentStudioStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "life_agents.json"

    def load(self) -> list[LifeAgentProfile]:
        if not self.path.exists():
            agents = self.default_agents()
            self.save(agents)
            return agents
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            agents = self.default_agents()
            self.save(agents)
            return agents
        items = payload.get("agents", []) if isinstance(payload, dict) else []
        agents: list[LifeAgentProfile] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            agents.append(
                LifeAgentProfile(
                    agent_id=str(item.get("agent_id", "")).strip(),
                    label=str(item.get("label", "")).strip() or "Unnamed Agent",
                    tier=str(item.get("tier", "strategic")).strip() or "strategic",
                    role=str(item.get("role", "")).strip(),
                    personality=str(item.get("personality", "")).strip(),
                    instructions=str(item.get("instructions", "")).strip(),
                    knowledge=str(item.get("knowledge", "")).strip(),
                    logic=str(item.get("logic", "")).strip(),
                    connections=[str(entry).strip() for entry in item.get("connections", []) if str(entry).strip()],
                    enabled=bool(item.get("enabled", True)),
                )
            )
        if not agents:
            agents = self.default_agents()
            self.save(agents)
        return agents

    def save(self, agents: list[LifeAgentProfile]) -> None:
        self.path.write_text(
            json.dumps({"agents": [agent.to_dict() for agent in agents]}, indent=2) + "\n",
            encoding="utf-8",
        )

    def upsert(self, payload: dict) -> LifeAgentProfile:
        agents = self.load()
        agent_id = str(payload.get("agent_id", "")).strip() or self._slugify(str(payload.get("label", "agent")).strip() or "agent")
        profile = LifeAgentProfile(
            agent_id=agent_id,
            label=str(payload.get("label", "")).strip() or "Unnamed Agent",
            tier=str(payload.get("tier", "strategic")).strip() or "strategic",
            role=str(payload.get("role", "")).strip(),
            personality=str(payload.get("personality", "")).strip(),
            instructions=str(payload.get("instructions", "")).strip(),
            knowledge=str(payload.get("knowledge", "")).strip(),
            logic=str(payload.get("logic", "")).strip(),
            connections=[str(entry).strip() for entry in payload.get("connections", []) if str(entry).strip()],
            enabled=bool(payload.get("enabled", True)),
        )
        replaced = False
        for index, existing in enumerate(agents):
            if existing.agent_id == profile.agent_id:
                agents[index] = profile
                replaced = True
                break
        if not replaced:
            agents.append(profile)
        self.save(agents)
        return profile

    def delete(self, agent_id: str) -> bool:
        agent_id = agent_id.strip()
        if not agent_id:
            return False
        agents = self.load()
        kept = [agent for agent in agents if agent.agent_id != agent_id]
        if len(kept) == len(agents):
            return False
        for agent in kept:
            agent.connections = [entry for entry in agent.connections if entry != agent_id]
        self.save(kept)
        return True

    def default_agents(self) -> list[LifeAgentProfile]:
        return [
            LifeAgentProfile(
                agent_id="jarvis-orchestrator",
                label="Jarvis Orchestrator",
                tier="orchestrator",
                role="Front-door intelligence that routes work, protects permissions, and keeps the house coherent.",
                personality="Calm, formal, dry, and highly competent. Speaks like an executive household associate rather than a chatbot.",
                instructions="Own the conversation, decide which specialist should weigh in, and preserve the single JARVIS persona at the surface.",
                knowledge="Household operating modes, approvals, active routines, and the current state of the JARVIS system.",
                logic="Route, stage, challenge risky decisions politely, ask for approval before consequential action, and synthesize multiple agents when needed.",
                connections=["family-chief", "calendar-steward", "formation-director", "workshop-foreman"],
            ),
            LifeAgentProfile(
                agent_id="family-chief",
                label="Family Chief",
                tier="strategic",
                role="Reduce friction in family logistics, routines, transitions, and emotional load.",
                personality="Warm, practical, protective, and quietly anticipatory.",
                instructions="Think in terms of calm evenings, departure flow, meals, kids, and protecting Rebekah from avoidable friction.",
                knowledge="Family routines, school rhythm, departure windows, meal patterns, and household task pressure points.",
                logic="Prioritize calm, coverage, and realistic logistics over theoretical optimization.",
                connections=["jarvis-orchestrator", "calendar-steward"],
            ),
            LifeAgentProfile(
                agent_id="calendar-steward",
                label="Calendar Steward",
                tier="strategic",
                role="Manage time, commitments, scheduling pressure, and free windows.",
                personality="Orderly, measured, and politely skeptical of overbooked optimism.",
                instructions="Surface conflicts, prep windows, and realistic sequencing for work, family, and travel.",
                knowledge="Calendar events, time estimates, buffers, travel assumptions, and deadline pressure.",
                logic="Sequence by reality, not wishful thinking. Protect margin where possible.",
                connections=["jarvis-orchestrator", "family-chief", "executive-counsel"],
            ),
            LifeAgentProfile(
                agent_id="executive-counsel",
                label="Executive Counsel",
                tier="strategic",
                role="Support work decisions, writing, research, and priority framing.",
                personality="Precise, analytical, discreet, and unexcited by corporate nonsense.",
                instructions="Clarify tradeoffs, prep meetings, shape decisions, and reduce cognitive clutter.",
                knowledge="Projects, open loops, meeting context, strategic options, and writing objectives.",
                logic="Diagnose, rank, frame options, then recommend the next clean move.",
                connections=["jarvis-orchestrator", "calendar-steward", "workshop-foreman"],
            ),
            LifeAgentProfile(
                agent_id="formation-director",
                label="Formation Director",
                tier="execution",
                role="Guard spiritual rhythm, reflection continuity, and formation over convenience.",
                personality="Steady, reverent, and gently incisive.",
                instructions="Coach toward prayer, Scripture, reflection, and integrity without becoming saccharine.",
                knowledge="Chronicle themes, devotional cadence, spiritual pressure points, and reflection history.",
                logic="Prefer depth, honesty, and formation over productivity theater.",
                connections=["jarvis-orchestrator", "family-chief"],
            ),
            LifeAgentProfile(
                agent_id="workshop-foreman",
                label="Workshop Foreman",
                tier="execution",
                role="Support builds, printer plans, materials, and safe workshop execution.",
                personality="Technical, matter-of-fact, and mildly unimpressed by rushed improvisation.",
                instructions="Think in parts, tolerances, materials, safety, and next physical action.",
                knowledge="Printer state, workshop projects, safety posture, and build constraints.",
                logic="Protect safety first, then recommend the fastest sensible path to a reliable result.",
                connections=["jarvis-orchestrator", "executive-counsel"],
            ),
        ]

    def _slugify(self, value: str) -> str:
        letters = [ch.lower() if ch.isalnum() else "-" for ch in value]
        slug = "".join(letters).strip("-")
        while "--" in slug:
            slug = slug.replace("--", "-")
        return slug or f"agent-{_now().strftime('%H%M%S')}"


class MemoryCurator:
    RULES = [
        {
            "rule_id": "stable-preference",
            "label": "Stable Preferences",
            "capture_when": "A preference affects repeated household flow or the quality of JARVIS assistance.",
            "store_as": "personal",
            "examples": ["brief after coffee", "preferred voice", "meeting-prep style"],
        },
        {
            "rule_id": "repeated-friction",
            "label": "Repeated Friction",
            "capture_when": "The same friction point appears in multiple requests or household plans.",
            "store_as": "household",
            "examples": ["departure bottleneck", "charging routine failure", "garage confusion"],
        },
        {
            "rule_id": "project-continuity",
            "label": "Project Continuity",
            "capture_when": "A decision, constraint, or insight will materially affect later work.",
            "store_as": "project",
            "examples": ["Chronicle positioning", "workshop dimension decision", "book voice principle"],
        },
        {
            "rule_id": "safety-and-boundaries",
            "label": "Safety And Boundaries",
            "capture_when": "A fact affects safety, privacy, child boundaries, or approval posture.",
            "store_as": "safety",
            "examples": ["allergy", "no voice unlock", "child tutoring boundary"],
        },
        {
            "rule_id": "formation-over-convenience",
            "label": "Formation Over Convenience",
            "capture_when": "A pattern shows how the family wants JARVIS to coach rather than replace human effort.",
            "store_as": "household",
            "examples": ["kids explain their work", "messages require approval", "device dock rhythm"],
        },
        {
            "rule_id": "discard-noise",
            "label": "Discard Noise",
            "capture_when": "A fact is transient, redundant, easily recoverable, or merely decorative.",
            "store_as": "do-not-store",
            "examples": ["one-off weather mention", "fleeting joke", "single transient sensor blip"],
        },
    ]

    def rules_snapshot(self, recent_activity: list[dict]) -> dict:
        candidates = self._curation_candidates(recent_activity)
        return {
            "rules": self.RULES,
            "candidates": candidates,
            "summary": self._summary(candidates),
        }

    def _curation_candidates(self, recent_activity: list[dict]) -> list[dict]:
        candidates: list[dict] = []
        for item in recent_activity[:12]:
            request = str(item.get("request", "")).strip()
            module = str(item.get("module", "unknown")).strip()
            rationale = str(item.get("rationale", "")).strip()
            lowered = request.lower()
            if not request:
                continue

            rule_id = ""
            proposed_type = ""
            note = ""

            if any(token in lowered for token in ("prefer", "usually", "always", "after coffee", "voice", "calm version")):
                rule_id = "stable-preference"
                proposed_type = "personal"
                note = "Looks like a reusable preference rather than a one-off request."
            elif any(token in lowered for token in ("garage", "charger", "backpack", "departure", "friction", "forget")):
                rule_id = "repeated-friction"
                proposed_type = "household"
                note = "Looks like a household friction loop worth remembering."
            elif module in {"executive-work", "workshop-copilot", "faith-and-formation"}:
                rule_id = "project-continuity"
                proposed_type = "project"
                note = "This appears tied to long-range project continuity."
            elif any(token in lowered for token in ("approval", "permission", "safety", "allergy", "unlock", "child")):
                rule_id = "safety-and-boundaries"
                proposed_type = "safety"
                note = "This touches safety or family boundaries."
            else:
                continue

            candidates.append(
                {
                    "rule_id": rule_id,
                    "proposed_type": proposed_type,
                    "module": module,
                    "request": request,
                    "rationale": rationale,
                    "note": note,
                }
            )
        return candidates[:8]

    def _summary(self, candidates: list[dict]) -> str:
        if not candidates:
            return "The curator is quiet. Nothing recent looks durable enough to store."
        counts: dict[str, int] = {}
        for item in candidates:
            counts[item["proposed_type"]] = counts.get(item["proposed_type"], 0) + 1
        fragments = [f"{kind} {count}" for kind, count in sorted(counts.items())]
        return "Current candidates suggest: " + ", ".join(fragments) + "."


class BackgroundTaskScheduler:
    def __init__(self, store: BackgroundStateStore, registry: AgentRegistry) -> None:
        self.store = store
        self.registry = registry

    def tick(
        self,
        *,
        active_mode: str,
        integration_status: list[dict],
        recent_activity: list[dict],
        quiet_hours: tuple[str, str],
    ) -> dict:
        now = _now()
        state = self.store.load()
        agents_state = state.get("agents", {})
        recent_modules = [str(item.get("module", "")).strip() for item in recent_activity[:10]]
        integration_map = self._integration_map(integration_status)
        quiet_now = self._within_quiet_hours(now, *quiet_hours)

        statuses: list[AgentStatus] = []
        for definition in self.registry.list():
            persisted = agents_state.get(definition.agent_id, {})
            last_run = _parse_iso(str(persisted.get("last_run_at", ""))) or now
            next_run = last_run
            cadence_seconds = definition.cadence_minutes * 60
            if persisted.get("last_run_at"):
                next_run = last_run.fromtimestamp(last_run.timestamp() + cadence_seconds, tz=UTC)
            due_now = now >= next_run
            blocked_dependencies = [
                dep for dep in definition.dependencies if not integration_map.get(dep, False)
            ]

            if blocked_dependencies:
                agent_state = "blocked"
                reason = "Waiting on " + ", ".join(blocked_dependencies)
                priority = "hold"
            elif definition.agent_id == "ambient-router":
                agent_state = "awake"
                reason = "Front-door routing stays available."
                priority = "high"
            elif quiet_now and definition.quiet_hours_behavior == "idle":
                agent_state = "idle"
                reason = "Quiet hours posture in effect."
                priority = "low"
            elif definition.agent_id == "memory-curator" and any(module for module in recent_modules):
                agent_state = "awake" if due_now or recent_modules else "idle"
                reason = "Recent activity gives the curator something to sort."
                priority = "medium"
            elif any(owner in recent_modules for owner in definition.owns) or self._mode_match(active_mode, definition.agent_id):
                agent_state = "awake"
                reason = f"Current mode '{active_mode}' or recent work makes this agent relevant."
                priority = "high" if due_now else "medium"
            else:
                agent_state = "idle"
                reason = "Standing by until its next useful window."
                priority = "low" if not due_now else "medium"

            status = AgentStatus(
                agent_id=definition.agent_id,
                label=definition.label,
                state=agent_state,
                reason=reason,
                cadence_minutes=definition.cadence_minutes,
                dependencies=definition.dependencies,
                blocked_dependencies=blocked_dependencies,
                owns=definition.owns,
                memory_scope=definition.memory_scope,
                last_run_at=last_run.isoformat(),
                next_run_at=next_run.isoformat(),
                due_now=due_now,
                priority=priority,
            )
            statuses.append(status)

            agents_state[definition.agent_id] = {
                "state": agent_state,
                "last_run_at": status.last_run_at if agent_state == "awake" else persisted.get("last_run_at", status.last_run_at),
                "next_run_at": status.next_run_at,
            }

        snapshot = {
            "last_tick_at": now.isoformat(),
            "quiet_hours_active": quiet_now,
            "active_mode": active_mode,
            "agents": agents_state,
            "awake_count": sum(1 for item in statuses if item.state == "awake"),
            "idle_count": sum(1 for item in statuses if item.state == "idle"),
            "blocked_count": sum(1 for item in statuses if item.state == "blocked"),
            "statuses": [asdict(item) for item in statuses],
        }
        self.store.save(snapshot)
        self.store.log_tick(snapshot)
        return snapshot

    def _integration_map(self, integration_status: list[dict]) -> dict[str, bool]:
        mapping = {}
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

    def _mode_match(self, active_mode: str, agent_id: str) -> bool:
        lowered = active_mode.lower()
        return (
            (agent_id == "family-logistics" and any(key in lowered for key in ("family", "dinner", "dawn", "goodnight")))
            or (agent_id == "executive-watch" and any(key in lowered for key in ("work", "deep")))
            or (agent_id == "chronicle-curator" and "chronicle" in lowered)
            or (agent_id == "workshop-watch" and "workshop" in lowered)
            or (agent_id == "home-ops" and any(key in lowered for key in ("night", "watchtower", "family", "movie")))
            or (agent_id == "watchtower" and any(key in lowered for key in ("watch", "night", "goodnight")))
        )

    def _within_quiet_hours(self, now: datetime, start: str, end: str) -> bool:
        start_minutes = _clock_minutes(start)
        end_minutes = _clock_minutes(end)
        current = now.hour * 60 + now.minute
        if start_minutes <= end_minutes:
            return start_minutes <= current < end_minutes
        return current >= start_minutes or current < end_minutes


def _clock_minutes(value: str) -> int:
    hours, minutes = value.split(":", 1)
    return int(hours) * 60 + int(minutes)
