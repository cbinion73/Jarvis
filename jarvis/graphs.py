from __future__ import annotations

import json
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from .models import RequestPlan
from .openai_tasks import OpenAIResult


class ResponseGraphState(TypedDict, total=False):
    plan: RequestPlan
    context_excerpt: str
    result: OpenAIResult


class PartyModeGraphState(TypedDict, total=False):
    actor_name: str
    room: str
    prompt: str
    selected_agents: list[Any]
    retrieved_context: str
    participants: list[dict[str, Any]]
    synthesis: str


class WealthLeverageGraphState(TypedDict, total=False):
    actor_name: str
    room: str
    prompt: str
    selected_agents: list[Any]
    retrieved_context: str
    participants: list[dict[str, Any]]
    synthesis: str


class BackgroundGraphState(TypedDict, total=False):
    active_mode: str
    recent_activity: list[dict[str, Any]]
    integration_status: list[dict[str, Any]]
    scheduler_snapshot: dict[str, Any]
    memory_curator_snapshot: dict[str, Any]
    openviking_sync: dict[str, Any]


def run_response_graph(runtime, plan: RequestPlan) -> OpenAIResult:
    def load_context(state: ResponseGraphState) -> ResponseGraphState:
        current_plan = state["plan"]
        context_excerpt = ""
        if runtime.openviking_support.enabled and current_plan.context_lane != "restricted-local":
            context_excerpt = runtime.openviking_support.party_mode_context(
                current_plan.request,
                limit=4 if current_plan.context_lane == "party-mode" else 3,
            )
        return {"context_excerpt": context_excerpt}

    def generate(state: ResponseGraphState) -> ResponseGraphState:
        current_plan = state["plan"]
        context_excerpt = state.get("context_excerpt", "")
        result = runtime.openai_client.respond(
            current_plan,
            supplemental_context=context_excerpt,
        )
        return {"result": result}

    graph = StateGraph(ResponseGraphState)
    graph.add_node("load_context", load_context)
    graph.add_node("generate", generate)
    graph.add_edge(START, "load_context")
    graph.add_edge("load_context", "generate")
    graph.add_edge("generate", END)
    compiled = graph.compile()
    final_state = compiled.invoke({"plan": plan})
    return final_state["result"]


def run_party_mode_graph(runtime, actor_name: str, room: str, prompt: str, selected_agents: list[Any]) -> dict[str, Any]:
    def load_context(state: PartyModeGraphState) -> PartyModeGraphState:
        retrieved_context = ""
        if runtime.openviking_support.enabled and prompt.strip():
            retrieved_context = runtime.openviking_support.party_mode_context(prompt, limit=5)
        return {"retrieved_context": retrieved_context}

    def gather_participants(state: PartyModeGraphState) -> PartyModeGraphState:
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
            output_text = runtime.openai_client.prompt_text(system_prompt, prompt, max_output_tokens=220).strip()
            participants.append(
                {
                    "agent_id": agent.agent_id,
                    "label": agent.label,
                    "tier": agent.tier,
                    "response": output_text,
                }
            )
        return {"participants": participants}

    def synthesize(state: PartyModeGraphState) -> PartyModeGraphState:
        retrieved_context = state.get("retrieved_context", "")
        participants = state.get("participants", [])
        synthesis_prompt = (
            f"Actor: {actor_name}. Room: {room}. "
            "You are JARVIS synthesizing a roundtable of specialist life agents into one coherent answer. "
            "Keep the voice formal, calm, and concise. "
            "State the recommendation, the tradeoff, and the next step."
        )
        synthesis_context = json.dumps(
            {
                "request": prompt,
                "retrieved_context": retrieved_context,
                "participants": participants,
            },
            indent=2,
        )
        synthesis = runtime.openai_client.prompt_text(
            synthesis_prompt,
            synthesis_context,
            max_output_tokens=320,
        ).strip()
        return {"synthesis": synthesis}

    graph = StateGraph(PartyModeGraphState)
    graph.add_node("load_context", load_context)
    graph.add_node("gather_participants", gather_participants)
    graph.add_node("synthesize", synthesize)
    graph.add_edge(START, "load_context")
    graph.add_edge("load_context", "gather_participants")
    graph.add_edge("gather_participants", "synthesize")
    graph.add_edge("synthesize", END)
    compiled = graph.compile()
    final_state = compiled.invoke(
        {
            "actor_name": actor_name,
            "room": room,
            "prompt": prompt,
            "selected_agents": selected_agents,
        }
    )
    return {
        "participants": final_state.get("participants", []),
        "retrieved_context": final_state.get("retrieved_context", ""),
        "synthesis": final_state.get("synthesis", ""),
    }


def run_background_cycle_graph(
    runtime,
    *,
    active_mode: str,
    recent_activity: list[dict[str, Any]],
    integration_status: list[dict[str, Any]],
) -> dict[str, Any]:
    def tick_scheduler(state: BackgroundGraphState) -> BackgroundGraphState:
        scheduler_snapshot = runtime.background_scheduler.tick(
            active_mode=state["active_mode"],
            integration_status=state["integration_status"],
            recent_activity=state["recent_activity"],
            quiet_hours=(runtime.household.quiet_start, runtime.household.quiet_end),
        )
        return {"scheduler_snapshot": scheduler_snapshot}

    def curate_memory(state: BackgroundGraphState) -> BackgroundGraphState:
        return {"memory_curator_snapshot": runtime.memory_curator.rules_snapshot(state["recent_activity"])}

    def sync_openviking(state: BackgroundGraphState) -> BackgroundGraphState:
        sync_result = {"ok": False, "enabled": False, "performed": False}
        if runtime.openviking_support.enabled:
            status = runtime.openviking_support.status()
            sync_result = {
                "ok": status.get("ok", False),
                "enabled": True,
                "performed": False,
                "base_url": status.get("base_url", ""),
                "memory_uri_root": status.get("memory_uri_root", ""),
                "detail": status.get("detail", ""),
                "pending_entries": len(runtime.memory_support.store.list_entries()),
            }
        return {"openviking_sync": sync_result}

    graph = StateGraph(BackgroundGraphState)
    graph.add_node("tick_scheduler", tick_scheduler)
    graph.add_node("curate_memory", curate_memory)
    graph.add_node("sync_openviking", sync_openviking)
    graph.add_edge(START, "tick_scheduler")
    graph.add_edge("tick_scheduler", "curate_memory")
    graph.add_edge("curate_memory", "sync_openviking")
    graph.add_edge("sync_openviking", END)
    compiled = graph.compile()
    final_state = compiled.invoke(
        {
            "active_mode": active_mode,
            "recent_activity": recent_activity,
            "integration_status": integration_status,
        }
    )
    return {
        "scheduler": final_state.get("scheduler_snapshot", {}),
        "memory_curator": final_state.get("memory_curator_snapshot", {}),
        "openviking_sync": final_state.get("openviking_sync", {}),
    }


def run_wealth_leverage_graph(runtime, actor_name: str, room: str, prompt: str, selected_agents: list[Any]) -> dict[str, Any]:
    focus_areas = [
        "passive-income ideas",
        "venture and opportunity triage",
        "tooling and automation leverage",
        "ROI-aware experimentation",
    ]

    def load_context(state: WealthLeverageGraphState) -> WealthLeverageGraphState:
        retrieved_context = ""
        retrieval_prompt = (
            "Wealth and leverage planning for Chris. "
            "Focus on financial independence, passive income, scalable leverage, and experiments that compound. "
            f"Current prompt: {prompt}"
        )
        if runtime.openviking_support.enabled:
            retrieved_context = runtime.openviking_support.party_mode_context(retrieval_prompt, limit=5)
        return {"retrieved_context": retrieved_context}

    def gather_participants(state: WealthLeverageGraphState) -> WealthLeverageGraphState:
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
            response = runtime.openai_client.prompt_text(
                system_prompt,
                prompt,
                model=runtime.config.openai_text_model,
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
        return {"participants": participants}

    def synthesize(state: WealthLeverageGraphState) -> WealthLeverageGraphState:
        retrieved_context = state.get("retrieved_context", "")
        participants = state.get("participants", [])
        synthesis_prompt = (
            f"Actor: {actor_name}. Room: {room}. "
            "You are JARVIS synthesizing a dedicated wealth-and-leverage council into one coherent answer. "
            "The user cares about financial independence, passive income, scalable leverage, and experiments with sensible ROI. "
            "Write with a calm executive tone. "
            "Return exactly four sections with short headings: Recommendation, Best Bets, Risks, Next Experiment."
        )
        synthesis_context = json.dumps(
            {
                "request": prompt,
                "focus_areas": focus_areas,
                "retrieved_context": retrieved_context,
                "participants": participants,
            },
            indent=2,
        )
        synthesis = runtime.openai_client.prompt_text(
            synthesis_prompt,
            synthesis_context,
            model=runtime.config.openai_text_model,
            max_output_tokens=420,
        ).strip()
        return {"synthesis": synthesis}

    graph = StateGraph(WealthLeverageGraphState)
    graph.add_node("load_context", load_context)
    graph.add_node("gather_participants", gather_participants)
    graph.add_node("synthesize", synthesize)
    graph.add_edge(START, "load_context")
    graph.add_edge("load_context", "gather_participants")
    graph.add_edge("gather_participants", "synthesize")
    graph.add_edge("synthesize", END)
    compiled = graph.compile()
    final_state = compiled.invoke(
        {
            "actor_name": actor_name,
            "room": room,
            "prompt": prompt,
            "selected_agents": selected_agents,
        }
    )
    return {
        "focus_areas": focus_areas,
        "participants": final_state.get("participants", []),
        "retrieved_context": final_state.get("retrieved_context", ""),
        "synthesis": final_state.get("synthesis", ""),
    }
