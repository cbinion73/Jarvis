# JARVIS AG2 Adoption Map

This note maps the current AG2 platform to the JARVIS seams in this checkout.

The goal is not to replace JARVIS with AG2.

The goal is to identify the small parts of AG2 that can strengthen JARVIS without weakening:

- mission-first product behavior
- approval and trust boundaries
- supervision and doctrine
- Apple and web product surfaces

## Recommendation Summary

Use AG2 selectively at the adapter and orchestration edge, not as the center of the system.

Best fit order:

1. Use AG2 MCP and toolkit patterns to tighten external-tool session management.
2. Use AG2 approval and tool-middleware patterns to clean up JARVIS tool execution boundaries.
3. Use AG2 swarm and handoff patterns only for bounded internal delegation lanes.
4. Use AG2 observability patterns to improve supervision traces and agent-run visibility.

Avoid using AG2 as:

- the source of truth for missions
- the owner of approval policy
- the owner of supervision or doctrine
- the replacement runtime for JARVIS

## Why This Is The Right Posture

JARVIS already has product-specific operating contracts that AG2 does not know about:

- mission contracts and mission lifecycle
- agent registry contracts
- approval queue and staged execution
- supervision decisions and doctrine promotion
- Apple-native and web-native surfaces

Primary local seams:

- `jarvis/tools/base.py`
- `jarvis/mcp_server.py`
- `jarvis/supervision.py`
- `jarvis/autonomy_state.py`
- `jarvis/missions.py`
- `jarvis/runtime.py`
- `jarvis/interfaces.py`
- `data/agents/jarvis_agent_registry.v1.json`
- `data/missions/jarvis_mission_model.v1.json`

That means AG2 is a fit when it helps JARVIS execute more cleanly, but not when it tries to redefine the product model.

## Adoption Map

### Seam 1: MCP Session And Toolkit Management

AG2 concept:

- MCP client session management
- toolkits that group external tools behind a stable adapter

Best JARVIS fit:

- `jarvis/mcp_server.py`
- future external connector adapters
- any bridge layer that needs dynamic external-tool mounting

Why this is a strong fit:

- JARVIS already exposes MCP tools with `FastMCP`.
- The repo has real tool surfaces and external integrations, but connector handling can still sprawl.
- AG2's MCP session-management pattern is a useful reference for on-demand tool access and shared session lifecycle.

What to borrow:

- a dedicated session manager abstraction for external MCP servers
- toolkit grouping for related tools
- lifecycle ownership for connect, reuse, close, and error posture

What to avoid:

- moving JARVIS business logic into AG2 toolkits
- making AG2 the public interface instead of JARVIS's own MCP and HTTP surfaces

Recommendation:

- `Use`

## Seam 2: Approval Middleware And Tool Execution Policy

AG2 concept:

- approval-required tool middleware
- pre-execution checks around tool calls
- toolkit-level middleware chains

Best JARVIS fit:

- `jarvis/tools/base.py`
- `jarvis/tools/__init__.py`
- `jarvis/supervision.py`
- `jarvis/autonomy_state.py`
- approval-facing routes in `jarvis/web.py` and `jarvis/apple_api.py`

Why this is a strong fit:

- JARVIS already has `ApprovalFlag` and approval-aware execution concepts.
- Approval and supervision policy exist, but the boundary between tool intent, approval requirement, sandboxing, and execution can still be cleaner.
- AG2 middleware patterns are useful as a structure for that boundary.

What to borrow:

- explicit preflight middleware for approval checks
- middleware stages for redaction, audit, sandbox policy, and consequence classification
- a consistent tool invocation envelope

What to preserve as JARVIS-owned:

- the approval queue
- supervision decisions
- doctrine promotion
- trust-zone policy

What to avoid:

- delegating approval truth to AG2 defaults
- bypassing JARVIS supervision because middleware "already checked it"

Recommendation:

- `Use`

## Seam 3: Bounded Delegation And Handoff Flows

AG2 concept:

- swarm orchestration
- handoffs between agents
- nested or delegated subtasks

Best JARVIS fit:

- `jarvis/interfaces.py`
- `jarvis/missions.py`
- `jarvis/runtime.py`
- handoff and workstate surfaces already discussed in repo docs and tests

Why this is a conditional fit:

- JARVIS already models handoff, delegation, ownership transfer, and bounded work.
- AG2 has practical patterns for routing work between agents and returning a result.
- That is useful only if JARVIS remains the owner of mission context, authority, and escalation.

What to borrow:

- small internal delegation runners
- structured handoff payloads
- clearer return contracts for delegated work

What to avoid:

- exposing a visible "swarm of bots" as the product interaction model
- letting delegated tasks outrun mission ownership or approval state
- replacing JARVIS agent contracts with AG2 agent definitions

Recommendation:

- `Adapt`

## Seam 4: Observability And Run Tracing

AG2 concept:

- agent-run observability
- tool-call traces
- execution metadata capture

Best JARVIS fit:

- `jarvis/supervision.py`
- `jarvis/audit.py`
- scheduler and runtime status surfaces
- mission and autonomy review pages

Why this is a good fit:

- JARVIS already values supervision traces and reviewed success.
- Better observability would help explain why a delegated run happened, what tools it touched, and where it stopped.
- This supports trust and debugging instead of changing the product model.

What to borrow:

- standardized execution trace shapes
- correlation ids across agent runs and tool calls
- richer replay metadata for reviewed work

What to avoid:

- observability that is disconnected from mission, lane, or approval context
- adding telemetry volume without preserving operator usefulness

Recommendation:

- `Use`

## Seam 5: Agent Definitions And Core Runtime

AG2 concept:

- framework-native agent definitions
- framework-owned runtime loops
- framework-first orchestration model

Best JARVIS fit:

- none as a primary replacement

Why this is a poor fit:

- JARVIS already has a contract-driven model for agents, lanes, missions, trust zones, and escalation.
- JARVIS is not a generic agent sandbox. It is a product with a specific operating model.
- Replacing the runtime center would create drift faster than it would create value.

Local contracts that should remain primary:

- `data/agents/jarvis_agent_registry.v1.json`
- `data/missions/jarvis_mission_model.v1.json`
- `jarvis/supervision.py`
- `jarvis/runtime.py`

Recommendation:

- `Avoid`

## Use Adapt Avoid Matrix

| AG2 capability | JARVIS seam | Recommendation | Why |
| --- | --- | --- | --- |
| MCP client session management | `jarvis/mcp_server.py` and future connector adapters | Use | Good fit for cleaner external-tool lifecycle |
| Toolkits | tool adapter layer around JARVIS-owned tools | Use | Helps grouping and session ownership |
| Approval-required middleware | `jarvis/tools/base.py`, supervision, approvals | Use | Strong fit if JARVIS remains policy owner |
| Tool middleware chains | tool execution pipeline | Use | Good for audit, sandbox, and redaction staging |
| Swarm handoffs | mission-local delegation and return contracts | Adapt | Useful internally, risky as product model |
| Nested chats / generic multi-agent chat | top-level user interaction | Avoid | Pulls JARVIS toward visible agent theater |
| Framework-native agent definitions | registry and mission contract layer | Avoid | Conflicts with JARVIS's canonical contracts |
| Framework-owned runtime orchestration | `jarvis/runtime.py` | Avoid | Would weaken mission and supervision ownership |
| Observability integrations | supervision and audit traces | Use | Improves trust, replay, and debugging |

## Build Order

If we use AG2 ideas here, the order should be:

1. Add a narrow MCP session-manager layer for external tool access.
2. Add a tiny middleware pipeline around JARVIS tool execution.
3. Trial a bounded delegation runner behind a single mission-local handoff path.
4. Add run-trace metadata that feeds supervision and audit views.

## First Concrete Implementation I Recommend

The first code change worth making is a small adapter layer around JARVIS tool execution that:

- preserves `ApprovalFlag` as the local contract
- adds explicit preflight middleware hooks
- cleanly separates:
  - consequence classification
  - approval requirement
  - sandbox requirement
  - audit logging
  - execution

Primary files:

- `jarvis/tools/base.py`
- `jarvis/tools/__init__.py`
- new adapter module such as `jarvis/tools/middleware.py`
- narrow callsites in the current tool execution path

Why this should land first:

- it is the smallest high-signal reuse
- it aligns with JARVIS's truth and trust posture
- it does not require runtime replacement
- it creates a better foundation for later MCP and delegation work

## Explicit Non-Goals

This adoption path should not:

- rewrite JARVIS around AG2
- replace the mission model
- replace the agent registry
- replace supervision or doctrine
- widen autonomy before JARVIS review and approval boundaries are clearer

## External AG2 References

These are the AG2 capability areas this map is based on:

- AG2 repository: <https://github.com/ag2ai/ag2>
- AG2 approval-required tool docs: <https://docs.ag2.ai/latest/docs/beta/tools/approval_required/>
- AG2 tool middleware docs: <https://docs.ag2.ai/latest/docs/beta/tools/tool_middleware/>
- AG2 toolkit docs: <https://docs.ag2.ai/latest/docs/beta/tools/toolkits/>
- AG2 MCP client docs: <https://docs.ag2.ai/latest/docs/user-guide/advanced-concepts/tools/mcp/client/>
- AG2 MCP session manager docs: <https://docs.ag2.ai/latest/docs/user-guide/advanced-concepts/tools/mcp/mcp_client_session_manager/>

