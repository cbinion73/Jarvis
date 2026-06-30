# JARVIS LangChain Integration Seams

This note marks the places in this checkout where LangChain or LangGraph would add real value without trying to replace JARVIS's product-specific architecture.

## Recommendation Summary

Use LangChain selectively at the framework boundary, not as the center of the system.

Best fit order:

1. Expand `LangGraph` for durable multi-step runtime flows that already behave like graphs.
2. Add a narrow LangChain provider/tool adapter layer around the existing agent tool registry.
3. Add retrieval plumbing only for bounded research and continuity surfaces.

Avoid using LangChain as:

- the source of truth for memory
- the owner of approval and trust policy
- a replacement for JARVIS runtime orchestration

## Seam 1: Graph-Native Runtime Flows

Primary files:

- `jarvis/graphs.py`
- `jarvis/runtime.py`

Why this is a strong fit:

- `jarvis/graphs.py` already imports `StateGraph` from `langgraph.graph`.
- The repo already models response generation, party mode, background cycles, and wealth leverage as explicit graph flows.
- This is the cleanest place to deepen LangGraph usage without introducing architectural drift.

What exists now:

- `run_response_graph(...)`
- `run_party_mode_graph(...)`
- `run_background_cycle_graph(...)`
- `run_wealth_leverage_graph(...)`

Why it is valuable:

- JARVIS already has long-running, stateful, branchable workflows.
- LangGraph is useful when the steps, transitions, retries, checkpoints, and resumable state matter more than generic chat loops.
- This aligns with JARVIS's always-on orchestrator direction better than generic agent executors do.

Best next move here:

- Standardize graph state shapes and transition patterns in `jarvis/graphs.py`.
- Move approval waits, fallback branches, and recovery branches into explicit graph edges where helpful.
- Keep business logic in JARVIS modules and use LangGraph only as the workflow shell.

## Seam 2: Provider And Tool Adapter Boundary

Primary files:

- `jarvis/agent.py`
- `jarvis/tools/__init__.py`
- `jarvis/tools/base.py`
- `jarvis/llm_gateway.py`
- `jarvis/openai_tasks.py`

Why this is a strong fit:

- `jarvis/agent.py` currently hand-converts the internal tool registry into OpenAI function-calling payloads.
- The repo already has a durable tool contract with approval flags and structured tool results.
- This is the right boundary to experiment with LangChain model and tool wrappers while preserving JARVIS policy.

What exists now:

- `TOOL_REGISTRY` and `TOOL_DEFINITIONS` in `jarvis/tools/__init__.py`
- approval-aware tools in `jarvis/tools/*.py`
- hand-built OpenAI function schema conversion in `jarvis/agent.py`
- hand-built provider routing in `jarvis/llm_gateway.py`

Why it is valuable:

- LangChain can simplify model abstraction and tool binding.
- JARVIS keeps its own approval and trust logic instead of leaking that into framework defaults.
- This creates a clean experiment surface without rewriting the runtime or memory stores.

Best next move here:

- Add a small adapter module that converts JARVIS tools into LangChain-compatible tools.
- Keep `needs_approval(...)` and `ToolResult` as JARVIS-owned concepts.
- Use the adapter first in `jarvis/agent.py`, not everywhere at once.

Constraint:

- Do not replace `jarvis/llm_gateway.py` wholesale. It already captures JARVIS-specific routing, model-cost awareness, and local-first posture.

## Seam 3: Bounded Retrieval For Research And Continuity

Primary files:

- `jarvis/browser_search.py`
- `jarvis/research_packets.py`
- `jarvis/obsidian_context.py`
- `jarvis/context_builder.py`
- `jarvis/openviking_context.py`

Why this is a good but narrower fit:

- JARVIS already has research and continuity surfaces that gather context from specific sources.
- LangChain retrievers and document transformers can help when the need is document selection and condensation, not authoritative memory ownership.

What exists now:

- browser-backed search and fetch in `jarvis/browser_search.py`
- continuity context assembly in `jarvis/graphs.py` and related context modules
- multiple product-specific stores for memory and state

Why it is valuable:

- It could improve source selection, chunking, reranking, and citation assembly for research packets or bounded continuity context.
- It should stay scoped to retrieval tasks rather than trying to become the system memory layer.

Best next move here:

- Apply LangChain retrieval primitives only to source gathering or bounded context assembly.
- Do not migrate `jarvis/memory.py`, `jarvis/agent_memory.py`, or `jarvis/known_facts.py` to LangChain memory abstractions.

## What To Skip

Skip these ideas unless the architecture changes materially:

- replacing JARVIS memory with LangChain memory
- replacing the approval queue with framework middleware
- replacing runtime orchestration with a generic ReAct-style agent executor
- wrapping every LLM call in LangChain just for consistency

Those moves would increase complexity faster than they would improve capability.

## Build Order

If we implement this, the order should be:

1. Strengthen `jarvis/graphs.py` as the primary LangGraph surface.
2. Add a tiny tool adapter layer for `jarvis/agent.py`.
3. Trial retrieval adapters only in research or continuity paths.

## First Concrete Implementation I Recommend

The first code change worth making is a small adapter module for `jarvis/agent.py` that:

- converts JARVIS tool definitions into LangChain-compatible tools
- preserves approval gating before execution
- lets us test LangChain model-plus-tool binding without disturbing the rest of the runtime

That is the smallest high-signal experiment in this repo.
