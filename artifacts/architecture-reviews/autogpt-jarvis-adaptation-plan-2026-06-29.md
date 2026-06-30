# AutoGPT -> JARVIS Adaptation Plan

Date: 2026-06-29

## Recommendation Summary

JARVIS should borrow a few strong infrastructure ideas from AutoGPT, but not its product posture.

The right carryover is:

- durable run orchestration
- graph-shaped workflow templates
- explicit agent/run inspection
- benchmarked task evaluation
- protocolized tool and agent boundaries

The wrong carryover is:

- dashboard-first agent-builder UX
- generic continuous-autonomy theater
- a marketplace/platform identity replacing companion-first JARVIS

## Current Source Truth

AutoGPT repo structure and license posture, as verified today:

- the repository contains both `autogpt_platform` and `classic` surfaces
- `autogpt_platform` includes `backend`, `frontend`, `analytics`, and `graph_templates`
- everything inside `autogpt_platform` is under the Polyform Shield License
- everything outside `autogpt_platform` is under the MIT License, including Forge and agbenchmark

Primary sources:

- [AutoGPT repository](https://github.com/significant-gravitas/autogpt)
- [AutoGPT license overview](https://github.com/significant-gravitas/autogpt/blob/master/LICENSE)
- [AutoGPT platform tree](https://github.com/significant-gravitas/autogpt/tree/master/autogpt_platform)

## JARVIS Seams That Already Match

The current repo already has strong seams where AutoGPT-style infrastructure can be adapted without changing the product identity:

- workflow shell:
  - [jarvis/graphs.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/graphs.py:1)
  - [jarvis/runtime.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/runtime.py:57)
- tool registry and approval-aware execution:
  - [jarvis/agent.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/agent.py:28)
  - [jarvis/tools/__init__.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/tools/__init__.py:1)
  - [jarvis/tools/base.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/tools/base.py:1)
  - [jarvis/approvals.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/approvals.py:367)
- durable work artifacts and reviewable outputs:
  - [jarvis/research_tasks.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/research_tasks.py:1)
  - [jarvis/artifact_outcomes.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/artifact_outcomes.py:1)
  - [jarvis/recommendations.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/recommendations.py:1)
  - [jarvis/decision_memos.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/decision_memos.py:1)
- product doctrine and guardrails:
  - [docs/JARVIS-MASTER-BUILD-PLAN.md](/Users/chris/Desktop/CODE/JARVIS/docs/JARVIS-MASTER-BUILD-PLAN.md:1)
  - [docs/JARVIS-LANGCHAIN-INTEGRATION-SEAMS.md](/Users/chris/Desktop/CODE/JARVIS/docs/JARVIS-LANGCHAIN-INTEGRATION-SEAMS.md:1)

## What JARVIS Should Borrow

### 1. Run Ledger, Not Agent Theater

Borrow from AutoGPT:

- explicit run records
- stateful step transitions
- inspectable execution history

Apply to JARVIS:

- every bounded agentic workflow should emit one durable run record with:
  - request
  - plan
  - tool calls
  - approval waits
  - artifacts created
  - final outcome
- keep this as a backend truth surface, not a flashy builder UI

Best JARVIS landing zone:

- `jarvis/runtime.py`
- `jarvis/agent_work.py`
- `jarvis/artifact_outcomes.py`
- `jarvis/research_tasks.py`

### 2. Graph Templates For Repeatable Flows

Borrow from AutoGPT:

- graph templates as reusable workflow shapes

Apply to JARVIS:

- create a small internal template layer around existing graph-native flows instead of inventing new orchestration
- templates should cover repeatable JARVIS work such as:
  - research packet flow
  - morning brief assembly
  - recommendation -> artifact -> approval flow
  - post-meeting follow-through

Best JARVIS landing zone:

- `jarvis/graphs.py`
- a new narrow template helper, likely adjacent to `jarvis/graphs.py`

### 3. Protocolized Tool Boundary

Borrow from AutoGPT classic / Forge:

- cleaner agent/tool contracts
- less hand-built tool wiring

Apply to JARVIS:

- keep approval logic, truth posture, and risk gating owned by JARVIS
- add a narrow adapter layer so tools can be bound to alternate agent runtimes without rewriting the registry
- do not replace the existing approval model with framework middleware

Best JARVIS landing zone:

- `jarvis/agent.py`
- `jarvis/tools/__init__.py`
- `jarvis/tools/base.py`

### 4. Benchmark Harness For Real Usefulness

Borrow from agbenchmark:

- explicit scenario evaluation
- repeatable scorecards

Apply to JARVIS:

- create a benchmark harness around JARVIS’s real product seams:
  - companion first-turn routing
  - morning brief truthfulness
  - drafting/follow-up usefulness
  - approval-aware action staging
- measure usefulness and truth, not generic “agent autonomy”

Best JARVIS landing zone:

- `tests/`
- `artifacts/build-reports/`
- possibly a new small benchmark runner script

### 5. Supervised Delegation Workspace

Borrow from AutoGPT platform:

- inspectable backend job posture
- clear run state

Apply to JARVIS:

- keep delegation subordinate to conversation
- expose a reviewable “what ran, what stalled, what needs approval” lane
- do not turn the product into a low-code agent operating system

Best JARVIS landing zone:

- `jarvis/runtime.py`
- existing work/research/recommendation stores
- Apple and dashboard review surfaces only after backend truth exists

## What JARVIS Should Not Borrow

- do not import AutoGPT’s platform identity as JARVIS’s identity
- do not make an agent-builder canvas the main UX
- do not import generic continuous-autonomy claims
- do not centralize the system around “agents” instead of companion usefulness
- do not pull code from `autogpt_platform` unless we deliberately accept its license terms

## Five Bounded Slices

### Slice 1. Durable Workflow Run Ledger

Goal:

- make bounded agentic work legible end to end

Scope:

- add one canonical run record contract for graph-driven and artifact-producing workflows
- persist requested action, effective plan, step events, approval pauses, and output artifacts

Likely JARVIS files:

- `jarvis/runtime.py`
- `jarvis/agent_work.py`
- `jarvis/artifact_outcomes.py`
- `tests/` focused around workflow recording

Acceptance:

- one real workflow can be replayed from durable repo/runtime truth without narrative explanation

### Slice 2. Graph Template Registry

Goal:

- stop hand-shaping repeatable multi-step flows one by one

Scope:

- define a tiny template registry for existing graph-native JARVIS workflows
- no new autonomy surface

Likely JARVIS files:

- `jarvis/graphs.py`
- new helper near `jarvis/graphs.py`

Acceptance:

- at least two existing flows share a common explicit template contract

### Slice 3. Tool Adapter Boundary

Goal:

- make the tool layer portable without surrendering approval control

Scope:

- build one adapter from JARVIS tool definitions to an alternate agent runtime contract
- preserve `needs_approval(...)` and `ToolResult` as JARVIS-owned truth

Likely JARVIS files:

- `jarvis/agent.py`
- `jarvis/tools/__init__.py`
- `jarvis/tools/base.py`

Acceptance:

- a small tool subset can be bound through the adapter with approval gating unchanged

### Slice 4. Live-Use Evaluation Harness

Goal:

- score the system on actual JARVIS usefulness instead of raw autonomy demos

Scope:

- add a narrow benchmark battery for:
  - companion prompts
  - morning brief truth
  - drafting usefulness
  - approval-aware action staging

Likely JARVIS files:

- `tests/`
- possibly one new benchmark runner
- `artifacts/build-reports/`

Acceptance:

- we can re-run one fixed scenario battery and compare before/after behavior

### Slice 5. Delegation Review Surface

Goal:

- give delegated work a truthful inspection lane

Scope:

- surface run status, stalls, outputs, and pending approvals from the new run ledger
- no new broad UI family unless the existing surface cannot host it

Likely JARVIS files:

- `jarvis/runtime.py`
- `jarvis/render_pages.py`
- Apple/dashboard surface only if the backend truth is already present

Acceptance:

- Chris can see what actually happened in delegated work without reading logs or trusting narration

## Recommended Execution Order

Do these in this order:

1. run ledger
2. graph templates
3. tool adapter boundary
4. evaluation harness
5. delegation review surface

That order matters because JARVIS should gain backend truth before it gains more autonomy-looking UI.

## My Recommendation

Proceed with **Slice 1: Durable Workflow Run Ledger** first.

Why this first:

- it gives JARVIS the highest-value AutoGPT-style improvement without product drift
- it strengthens truth, reviewability, and later delegation
- it supports the existing JARVIS doctrine better than importing a builder or platform frontend

## What I Changed In This Slice

- added this adaptation plan artifact only
- did not change code
- did not import external code

## Repo-Truth Notes

- this plan is intentionally architecture-first and recommendation-first
- any direct code borrowing should favor the MIT-licensed AutoGPT surfaces outside `autogpt_platform`
- if we later want implementation slices, they should be packaged as the same bounded Build Office lane style already used in this repo
