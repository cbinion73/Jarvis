from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any, TypedDict

try:
    from langgraph.graph import END, START, StateGraph
except ModuleNotFoundError:  # pragma: no cover - local fallback for cold runtimes
    START = "__start__"
    END = "__end__"

    class StateGraph:  # type: ignore[override]
        def __init__(self, *_args, **_kwargs) -> None:
            self._nodes: dict[str, Any] = {}
            self._edges: dict[str, list[str]] = {}

        def add_node(self, name: str, fn: Any) -> None:
            self._nodes[name] = fn

        def add_edge(self, source: str, target: str) -> None:
            self._edges.setdefault(source, []).append(target)

        def compile(self):
            nodes = dict(self._nodes)
            edges = {key: list(value) for key, value in self._edges.items()}

            class _CompiledGraph:
                def invoke(self, state: dict[str, Any]) -> dict[str, Any]:
                    current = dict(state)
                    cursor = START
                    visited: set[tuple[str, str]] = set()

                    while True:
                        next_nodes = edges.get(cursor, [])
                        if not next_nodes:
                            return current
                        next_node = next_nodes[0]
                        if next_node == END:
                            return current
                        edge_key = (cursor, next_node)
                        if edge_key in visited:
                            return current
                        visited.add(edge_key)
                        update = nodes[next_node](current) or {}
                        if isinstance(update, dict):
                            current.update(update)
                        cursor = next_node

            return _CompiledGraph()

from .models import RequestPlan
from .openai_tasks import OpenAIResult
from .companion_spine import run_companion_turn

_COMPILED_GRAPHS: dict[str, Any] = {}


class ResponseGraphState(TypedDict, total=False):
    runtime: Any
    plan: RequestPlan
    continuity_context: str
    context_excerpt: str
    result: OpenAIResult


class PartyModeGraphState(TypedDict, total=False):
    runtime: Any
    actor_name: str
    room: str
    prompt: str
    selected_agents: list[Any]
    retrieved_context: str
    participants: list[dict[str, Any]]
    synthesis: str


class WealthLeverageGraphState(TypedDict, total=False):
    runtime: Any
    actor_name: str
    room: str
    prompt: str
    selected_agents: list[Any]
    retrieved_context: str
    participants: list[dict[str, Any]]
    synthesis: str


class BackgroundGraphState(TypedDict, total=False):
    runtime: Any
    active_mode: str
    recent_activity: list[dict[str, Any]]
    integration_status: list[dict[str, Any]]
    scheduler_snapshot: dict[str, Any]
    memory_curator_snapshot: dict[str, Any]
    openviking_sync: dict[str, Any]


def _compile_graph(name: str, builder: Any) -> Any:
    compiled = _COMPILED_GRAPHS.get(name)
    if compiled is None:
        graph = builder()
        compiled = graph.compile()
        _COMPILED_GRAPHS[name] = compiled
    return compiled


def _build_linear_graph(state_type: Any, nodes: list[tuple[str, Any]]) -> Any:
    graph = StateGraph(state_type)
    previous = START
    for node_name, node_fn in nodes:
        graph.add_node(node_name, node_fn)
        graph.add_edge(previous, node_name)
        previous = node_name
    graph.add_edge(previous, END)
    return graph


def _build_live_context(runtime) -> str:
    """Build a compact live-data block: weather + today's calendar events."""
    import datetime
    lines: list[str] = []

    # ── Weather ──────────────────────────────────────────────────────────────
    try:
        wx = runtime.storm_weather_summary()
        if wx.get("available"):
            cur = wx.get("current", {})
            temp = cur.get("temperature_f")
            cond = cur.get("condition", "")
            loc  = cur.get("location", "")
            wind = cur.get("wind", "")
            alerts = wx.get("alerts", [])
            wx_line = f"Weather ({loc}): {temp}°F, {cond}"
            if wind:
                wx_line += f", {wind}"
            if alerts:
                wx_line += f" — ⚠ {alerts[0].get('headline', 'Alert active')}"
            lines.append(wx_line)
    except Exception:
        pass

    # ── Calendar ─────────────────────────────────────────────────────────────
    try:
        today = datetime.date.today().isoformat()
        cal = runtime.family_calendar.summary()
        all_events = cal.get("events", []) if isinstance(cal, dict) else []
        events = [e for e in all_events if str(e.get("start_date", "") or e.get("start", ""))[:10] == today]
        if events:
            lines.append(f"Today's calendar ({today}):")
            for ev in events[:8]:
                title = ev.get("title") or ev.get("summary", "Untitled")
                start = ev.get("start_time") or ev.get("start", "")
                who   = ev.get("actor") or ev.get("calendar", "")
                entry = f"  • {title}"
                if start:
                    entry += f" at {start}"
                if who:
                    entry += f" ({who})"
                lines.append(entry)
        else:
            lines.append(f"Today's calendar ({today}): No events found.")
    except Exception:
        pass

    return "\n".join(lines)


def run_response_graph(runtime, plan: RequestPlan, continuity_context: str = "") -> OpenAIResult:
    step_events: list[dict[str, Any]] = []

    def load_context(state: ResponseGraphState) -> ResponseGraphState:
        current_runtime = state["runtime"]
        current_plan = state["plan"]
        current_continuity_context = state.get("continuity_context", "")
        context_parts: list[str] = []

        # Live weather + calendar — always injected so JARVIS knows the day
        live = _build_live_context(current_runtime)
        if live.strip():
            context_parts.append(live.strip())

        if current_runtime.openviking_support.enabled and current_plan.context_lane != "restricted-local":
            retrieved = current_runtime.openviking_support.party_mode_context(
                current_plan.request,
                limit=4 if current_plan.context_lane == "party-mode" else 3,
            )
            if retrieved.strip():
                context_parts.append(retrieved.strip())
        if current_continuity_context.strip():
            context_parts.append(current_continuity_context.strip())
        update = {"context_excerpt": "\n\n".join(context_parts).strip()}
        step_events.append(
            {
                "node": "load_context",
                "status": "completed",
                "updated_keys": ["context_excerpt"],
                "context_present": bool(str(update.get("context_excerpt", "")).strip()),
            }
        )
        return update

    def generate(state: ResponseGraphState) -> ResponseGraphState:
        current_runtime = state["runtime"]
        current_plan = state["plan"]
        context_excerpt = state.get("context_excerpt", "")
        actor = current_runtime.get_actor(current_plan.actor)
        result = run_companion_turn(
            current_runtime,
            actor,
            current_plan.room,
            current_plan.request,
            plan=current_plan,
            continuity_context=context_excerpt,
        )
        created_objects = getattr(current_runtime, "_created_objects_from_result", lambda *_args, **_kwargs: [])(result)
        step_events.append(
            {
                "node": "generate",
                "status": "completed",
                "updated_keys": ["result"],
                "provider": str(result.provider or "").strip(),
                "created_object_count": len(created_objects),
            }
        )
        return {"result": result}

    compiled = _compile_graph(
        "response_graph",
        lambda: _build_linear_graph(
            ResponseGraphState,
            [("load_context", load_context), ("generate", generate)],
        ),
    )
    initial_state = {
        "runtime": runtime,
        "plan": plan,
        "continuity_context": continuity_context,
    }
    try:
        final_state = compiled.invoke(initial_state)
        result = final_state["result"]
    except Exception as exc:
        record_fn = getattr(runtime, "record_workflow_run", None)
        if callable(record_fn):
            record_fn(
                workflow_kind="response_graph",
                actor=plan.actor,
                room=plan.room,
                request=plan.request,
                status="failed",
                provider="",
                model=plan.model,
                graph_name="response_graph",
                runtime_surface="graph",
                active_nodes=["response_graph", plan.module],
                nodes_planned=["load_context", "generate"],
                step_events=step_events,
                execution_trace=[],
                created_objects=[],
                plan=plan,
                result_summary={"error": str(exc)},
                output_text="",
                metadata={"plan": asdict(plan), "continuity_context_supplied": bool(continuity_context.strip())},
            )
        raise
    record_fn = getattr(runtime, "record_workflow_run", None)
    if callable(record_fn):
        created_objects = getattr(runtime, "_created_objects_from_result", lambda *_args, **_kwargs: [])(result)
        record = record_fn(
            workflow_kind="response_graph",
            actor=plan.actor,
            room=plan.room,
            request=plan.request,
            status="completed",
            provider=result.provider,
            model=result.model,
            graph_name="response_graph",
            runtime_surface="graph",
            active_nodes=["response_graph", plan.module, result.provider],
            nodes_planned=["load_context", "generate"],
            step_events=step_events,
            execution_trace=list(getattr(result, "execution_trace", []) or []),
            created_objects=created_objects,
            plan=plan,
            result_summary={
                "created_object_count": len(created_objects),
                "execution_trace_count": len(list(getattr(result, "execution_trace", []) or [])),
            },
            output_text=str(result.output_text or "").strip(),
            metadata={"plan": asdict(plan), "continuity_context_supplied": bool(continuity_context.strip())},
        )
        if record and isinstance(result.execution_trace, list):
            result.execution_trace.append(
                {
                    "type": "workflow_run",
                    "status": "recorded",
                    "workflow_kind": "response_graph",
                    "run_id": str(record.get("run_id", "") or "").strip(),
                }
            )
    return result


def run_party_mode_graph(runtime, actor_name: str, room: str, prompt: str, selected_agents: list[Any]) -> dict[str, Any]:
    step_events: list[dict[str, Any]] = []

    def load_context(state: PartyModeGraphState) -> PartyModeGraphState:
        current_runtime = state["runtime"]
        current_prompt = state["prompt"]
        retrieved_context = ""
        if current_runtime.openviking_support.enabled and current_prompt.strip():
            retrieved_context = current_runtime.openviking_support.party_mode_context(current_prompt, limit=5)
        step_events.append({"node": "load_context", "status": "completed", "updated_keys": ["retrieved_context"]})
        return {"retrieved_context": retrieved_context}

    def gather_participants(state: PartyModeGraphState) -> PartyModeGraphState:
        current_runtime = state["runtime"]
        current_prompt = state["prompt"]
        retrieved_context = state.get("retrieved_context", "")
        participants: list[dict[str, Any]] = []
        for agent in state.get("selected_agents", [])[:8]:
            system_prompt = (
                f"You are {agent.label}, a specialist agent inside Chris's personal JARVIS mesh. "
                f"Title: {getattr(agent, 'title', agent.label)} "
                f"Category: {getattr(agent, 'category', 'strategist')} "
                f"Purpose: {getattr(agent, 'purpose', agent.role)} "
                f"Role: {agent.role} "
                f"Personality: {agent.personality} "
                f"Instructions: {agent.instructions} "
                f"Specific information: {agent.knowledge} "
                f"Logic: {agent.logic} "
                f"Authority: {getattr(agent, 'authority_level', 'advise')} "
                f"Party role: {getattr(agent, 'party_role', '')} "
                "Respond in 2-4 concise sentences. Give your perspective, your main concern, and your recommended next move. "
                "Stay in character, but be practical."
            )
            if retrieved_context:
                system_prompt += "\n\nRetrieved continuity context from OpenViking:\n" + retrieved_context
            output_text = current_runtime.openai_client.prompt_text(system_prompt, current_prompt, max_output_tokens=220).strip()
            participants.append(
                {
                    "agent_id": agent.agent_id,
                    "label": agent.label,
                    "tier": agent.tier,
                    "response": output_text,
                }
            )
        step_events.append(
            {
                "node": "gather_participants",
                "status": "completed",
                "updated_keys": ["participants"],
                "participant_count": len(participants),
            }
        )
        return {"participants": participants}

    def synthesize(state: PartyModeGraphState) -> PartyModeGraphState:
        current_runtime = state["runtime"]
        current_prompt = state["prompt"]
        retrieved_context = state.get("retrieved_context", "")
        participants = state.get("participants", [])
        current_actor_name = state["actor_name"]
        current_room = state["room"]
        synthesis_prompt = (
            f"Actor: {current_actor_name}. Room: {current_room}. "
            "You are JARVIS synthesizing a roundtable of specialist life agents into one coherent answer. "
            "Keep the voice formal, calm, and concise. "
            "State the recommendation, the tradeoff, and the next step."
        )
        synthesis_context = json.dumps(
            {
                "request": current_prompt,
                "retrieved_context": retrieved_context,
                "participants": participants,
            },
            indent=2,
        )
        synthesis = current_runtime.openai_client.prompt_text(
            synthesis_prompt,
            synthesis_context,
            max_output_tokens=320,
        ).strip()
        step_events.append({"node": "synthesize", "status": "completed", "updated_keys": ["synthesis"]})
        return {"synthesis": synthesis}

    compiled = _compile_graph(
        "party_mode_graph",
        lambda: _build_linear_graph(
            PartyModeGraphState,
            [
                ("load_context", load_context),
                ("gather_participants", gather_participants),
                ("synthesize", synthesize),
            ],
        ),
    )
    final_state = compiled.invoke(
        {
            "runtime": runtime,
            "actor_name": actor_name,
            "room": room,
            "prompt": prompt,
            "selected_agents": selected_agents,
        }
    )
    result = {
        "participants": final_state.get("participants", []),
        "retrieved_context": final_state.get("retrieved_context", ""),
        "synthesis": final_state.get("synthesis", ""),
    }
    record_fn = getattr(runtime, "record_workflow_run", None)
    if callable(record_fn):
        record_fn(
            workflow_kind="party_mode_graph",
            actor=actor_name,
            room=room,
            request=prompt,
            status="completed",
            provider="openai",
            model=str(getattr(runtime.config, "openai_text_model", "") or "").strip(),
            graph_name="party_mode_graph",
            runtime_surface="graph",
            active_nodes=["party_mode_graph"],
            nodes_planned=["load_context", "gather_participants", "synthesize"],
            step_events=step_events,
            execution_trace=[],
            created_objects=[],
            result_summary={"participant_count": len(result["participants"])},
            output_text=str(result.get("synthesis", "") or "").strip(),
            metadata={"selected_agent_count": len(selected_agents)},
        )
    return result


def run_background_cycle_graph(
    runtime,
    *,
    active_mode: str,
    recent_activity: list[dict[str, Any]],
    integration_status: list[dict[str, Any]],
) -> dict[str, Any]:
    step_events: list[dict[str, Any]] = []

    def tick_scheduler(state: BackgroundGraphState) -> BackgroundGraphState:
        current_runtime = state["runtime"]
        scheduler_snapshot = current_runtime.background_scheduler.tick(
            active_mode=state["active_mode"],
            integration_status=state["integration_status"],
            recent_activity=state["recent_activity"],
            quiet_hours=(current_runtime.household.quiet_start, current_runtime.household.quiet_end),
        )
        step_events.append({"node": "tick_scheduler", "status": "completed", "updated_keys": ["scheduler_snapshot"]})
        return {"scheduler_snapshot": scheduler_snapshot}

    def curate_memory(state: BackgroundGraphState) -> BackgroundGraphState:
        current_runtime = state["runtime"]
        step_events.append({"node": "curate_memory", "status": "completed", "updated_keys": ["memory_curator_snapshot"]})
        return {"memory_curator_snapshot": current_runtime.memory_curator.rules_snapshot(state["recent_activity"])}

    def sync_openviking(state: BackgroundGraphState) -> BackgroundGraphState:
        current_runtime = state["runtime"]
        sync_result = {"ok": False, "enabled": False, "performed": False}
        if current_runtime.openviking_support.enabled:
            status = current_runtime.openviking_support.status()
            sync_result = {
                "ok": status.get("ok", False),
                "enabled": True,
                "performed": False,
                "base_url": status.get("base_url", ""),
                "memory_uri_root": status.get("memory_uri_root", ""),
                "detail": status.get("detail", ""),
                "pending_entries": len(current_runtime.memory_support.store.list_entries()),
            }
        step_events.append({"node": "sync_openviking", "status": "completed", "updated_keys": ["openviking_sync"]})
        return {"openviking_sync": sync_result}

    compiled = _compile_graph(
        "background_cycle_graph",
        lambda: _build_linear_graph(
            BackgroundGraphState,
            [
                ("tick_scheduler", tick_scheduler),
                ("curate_memory", curate_memory),
                ("sync_openviking", sync_openviking),
            ],
        ),
    )
    final_state = compiled.invoke(
        {
            "runtime": runtime,
            "active_mode": active_mode,
            "recent_activity": recent_activity,
            "integration_status": integration_status,
        }
    )
    result = {
        "scheduler": final_state.get("scheduler_snapshot", {}),
        "memory_curator": final_state.get("memory_curator_snapshot", {}),
        "openviking_sync": final_state.get("openviking_sync", {}),
    }
    record_fn = getattr(runtime, "record_workflow_run", None)
    if callable(record_fn):
        record_fn(
            workflow_kind="background_cycle_graph",
            actor="system",
            room="background",
            request=f"background-cycle:{active_mode}",
            status="completed",
            provider="system",
            model="background-cycle",
            graph_name="background_cycle_graph",
            runtime_surface="graph",
            active_nodes=["background_cycle_graph"],
            nodes_planned=["tick_scheduler", "curate_memory", "sync_openviking"],
            step_events=step_events,
            execution_trace=[],
            created_objects=[],
            result_summary={"recent_activity_count": len(recent_activity)},
            output_text="",
            metadata={"active_mode": active_mode},
        )
    return result


def run_wealth_leverage_graph(runtime, actor_name: str, room: str, prompt: str, selected_agents: list[Any]) -> dict[str, Any]:
    focus_areas = [
        "passive-income ideas",
        "venture and opportunity triage",
        "tooling and automation leverage",
        "ROI-aware experimentation",
    ]
    step_events: list[dict[str, Any]] = []

    def load_context(state: WealthLeverageGraphState) -> WealthLeverageGraphState:
        current_runtime = state["runtime"]
        current_prompt = state["prompt"]
        retrieved_context = ""
        retrieval_prompt = (
            "Wealth and leverage planning for Chris. "
            "Focus on financial independence, passive income, scalable leverage, and experiments that compound. "
            f"Current prompt: {current_prompt}"
        )
        if current_runtime.openviking_support.enabled:
            retrieved_context = current_runtime.openviking_support.party_mode_context(retrieval_prompt, limit=5)
        step_events.append({"node": "load_context", "status": "completed", "updated_keys": ["retrieved_context"]})
        return {"retrieved_context": retrieved_context}

    def gather_participants(state: WealthLeverageGraphState) -> WealthLeverageGraphState:
        current_runtime = state["runtime"]
        current_prompt = state["prompt"]
        retrieved_context = state.get("retrieved_context", "")
        participants: list[dict[str, Any]] = []
        for agent in state.get("selected_agents", [])[:6]:
            system_prompt = (
                f"You are {agent.label}, a specialist life agent inside Chris's JARVIS mesh. "
                f"Title: {getattr(agent, 'title', agent.label)}. "
                f"Role: {agent.role}. "
                f"Purpose: {getattr(agent, 'purpose', agent.role)}. "
                f"Personality: {agent.personality}. "
                f"Instructions: {agent.instructions}. "
                f"Logic: {agent.logic}. "
                f"Party role: {getattr(agent, 'party_role', '')}. "
                "You are participating in a dedicated wealth-and-leverage workflow. "
                "Respond in 3 concise bullets or short paragraphs. "
                "Cover: (1) your best opportunity recommendation, (2) the main risk or tradeoff, (3) the next experiment worth running. "
                "Be concrete, practical, and tailored to Chris's desire for financial independence and passive income."
            )
            if retrieved_context:
                system_prompt += "\n\nRetrieved continuity context from OpenViking:\n" + retrieved_context
            response = current_runtime.openai_client.prompt_text(
                system_prompt,
                current_prompt,
                model=current_runtime.config.openai_text_model,
                max_output_tokens=260,
            ).strip()
            participants.append(
                {
                    "agent_id": agent.agent_id,
                    "label": agent.label,
                    "title": getattr(agent, "title", ""),
                    "response": response,
                }
            )
        step_events.append(
            {
                "node": "gather_participants",
                "status": "completed",
                "updated_keys": ["participants"],
                "participant_count": len(participants),
            }
        )
        return {"participants": participants}

    def synthesize(state: WealthLeverageGraphState) -> WealthLeverageGraphState:
        current_runtime = state["runtime"]
        current_prompt = state["prompt"]
        retrieved_context = state.get("retrieved_context", "")
        participants = state.get("participants", [])
        current_actor_name = state["actor_name"]
        current_room = state["room"]
        synthesis_prompt = (
            f"Actor: {current_actor_name}. Room: {current_room}. "
            "You are JARVIS synthesizing a dedicated wealth-and-leverage council into one coherent answer. "
            "The user cares about financial independence, passive income, scalable leverage, and experiments with sensible ROI. "
            "Write with a calm executive tone. "
            "Return exactly four sections with short headings: Recommendation, Best Bets, Risks, Next Experiment."
        )
        synthesis_context = json.dumps(
            {
                "request": current_prompt,
                "focus_areas": focus_areas,
                "retrieved_context": retrieved_context,
                "participants": participants,
            },
            indent=2,
        )
        synthesis = current_runtime.openai_client.prompt_text(
            synthesis_prompt,
            synthesis_context,
            model=current_runtime.config.openai_text_model,
            max_output_tokens=420,
        ).strip()
        step_events.append({"node": "synthesize", "status": "completed", "updated_keys": ["synthesis"]})
        return {"synthesis": synthesis}

    compiled = _compile_graph(
        "wealth_leverage_graph",
        lambda: _build_linear_graph(
            WealthLeverageGraphState,
            [
                ("load_context", load_context),
                ("gather_participants", gather_participants),
                ("synthesize", synthesize),
            ],
        ),
    )
    final_state = compiled.invoke(
        {
            "runtime": runtime,
            "actor_name": actor_name,
            "room": room,
            "prompt": prompt,
            "selected_agents": selected_agents,
        }
    )
    result = {
        "focus_areas": focus_areas,
        "participants": final_state.get("participants", []),
        "retrieved_context": final_state.get("retrieved_context", ""),
        "synthesis": final_state.get("synthesis", ""),
    }
    record_fn = getattr(runtime, "record_workflow_run", None)
    if callable(record_fn):
        record_fn(
            workflow_kind="wealth_leverage_graph",
            actor=actor_name,
            room=room,
            request=prompt,
            status="completed",
            provider="openai",
            model=str(getattr(runtime.config, "openai_text_model", "") or "").strip(),
            graph_name="wealth_leverage_graph",
            runtime_surface="graph",
            active_nodes=["wealth_leverage_graph"],
            nodes_planned=["load_context", "gather_participants", "synthesize"],
            step_events=step_events,
            execution_trace=[],
            created_objects=[],
            result_summary={"participant_count": len(result["participants"]), "focus_area_count": len(focus_areas)},
            output_text=str(result.get("synthesis", "") or "").strip(),
            metadata={"selected_agent_count": len(selected_agents)},
        )
    return result
