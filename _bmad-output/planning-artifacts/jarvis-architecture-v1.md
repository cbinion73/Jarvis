---
workflowType: "manual-bmad-architecture-bootstrap"
project: "JARVIS"
sourceDocuments:
  - "_bmad-output/planning-artifacts/jarvis-prd-v1.md"
---

# Architecture Decision Document - JARVIS

**Author:** Chris + Codex
**Date:** 2026-05-05
**Status:** Draft v1

## 1. Architectural Thesis

JARVIS should be built as a layered household platform:

1. Local home state and actuation
2. Local orchestration, permissions, and memory policy
3. OpenAI multimodal reasoning and voice
4. OpenClaw as operator shell, approvals surface, and future channel bridge

The system should not rely on one giant model prompt. It should route work across cheaper local logic, cheap OpenAI routing models, stronger planning models, and a dedicated voice model where real-time speech matters.

## 2. Top-Level System

```text
Voice satellites / cameras / sensors
        ->
Local wake word + presence + room inference
        ->
JARVIS Orchestrator
        ->
Permission Engine
        ->
Memory Core + Household State
        ->
Tool Router
        ->
Home Assistant / OpenClaw / OpenAI / Calendar / Email / Workshop tools
        ->
Action Log + Approval Surface
```

## 3. Core Decisions

### ADR-001: Local first home boundary

Use Home Assistant as the single home-control authority. JARVIS should call Home Assistant rather than speaking directly to individual smart devices where avoidable.

Why:

- keeps automations local
- reduces vendor lock-in
- matches the product requirement for outage resilience

### ADR-002: Tiered OpenAI model strategy

Use different OpenAI models for different work classes.

Recommended routing:

- `gpt-realtime-1.5` for full duplex voice conversations where low-latency audio matters
- `gpt-5.4-mini` for default reasoning, executive work, Chronicle, workshop planning, and family coordination
- `gpt-5.4-nano` for cheap local-cloud helpers such as tagging, classification, summarization of low-risk state, and routine selection

Rationale:

- OpenAI's current model docs position `gpt-realtime-1.5` as the best voice model.
- OpenAI's compare docs position `gpt-5.4-mini` as the strongest mini for coding, computer use, and subagents at lower cost than flagship tiers.
- `gpt-5.4-nano` is cheap enough to use on routine routing and inventory-style work.

### ADR-003: OpenClaw as shell, not the household brain

Use OpenClaw for:

- operator chat
- approval workflows
- future channel integrations
- gateway and local runtime conveniences

Do not make OpenClaw the only place where household policy lives. The JARVIS domain runtime should own:

- user profiles
- household modes
- permission classes
- family guardrails
- domain-specific orchestration rules

### ADR-004: Python domain runtime

Use Python for the first JARVIS domain runtime because:

- this workspace already started in Python
- OpenAI and ElevenLabs are already wired here
- household policy and orchestration are straightforward to express in dataclasses and services
- later integrations can still expose HTTP/WebSocket boundaries for mixed-language extensions

### ADR-005: Consequential actions require explicit approval

Any action that changes shared state outside the local house context should pass through approval checks.

Examples:

- send message
- modify family calendar
- submit order
- unlock remotely
- vendor upload

### ADR-006: Child-safe tutoring is an explicit subsystem

Kid workflows are not a lighter copy of adult agent workflows. They need separate policy:

- no doing homework for them
- more Socratic prompting
- parent-visible boundaries
- different memory access

## 4. Proposed Repository Structure

```text
JARVIS/
  jarvis/
    main.py
    runtime.py
    config.py
    models.py
    permissions.py
    orchestrator.py
    briefing.py
  household/
    jarvis_household.example.json
  docs/
    project-context.md
  _bmad-output/
    planning-artifacts/
      jarvis-prd-v1.md
      jarvis-architecture-v1.md
      jarvis-epics-v1.md
```

## 5. Runtime Components

### 5.1 Orchestrator

Responsibilities:

- understand request
- infer room and mode
- choose module
- choose model tier
- check approval class
- stage the next action

### 5.2 Permission Engine

Responsibilities:

- classify actions 0-6
- determine whether approval is required
- enforce child/adult boundaries
- prevent unsafe defaults

### 5.3 Household Configuration

Responsibilities:

- define users, rooms, modes, quiet hours, and module priorities
- provide a serializable source of truth for family-specific behavior

### 5.4 Briefing Builder

Responsibilities:

- generate morning/evening brief shells
- support user-specific framing
- keep tone adaptive by mode

## 6. Integration Boundaries

### Home Assistant

- preferred connection: Home Assistant WebSocket API
- role: entity state, automations, scenes, service calls

### OpenAI

- `Responses API` for text and multimodal planning work
- `Realtime API` for voice sessions
- model routing handled by JARVIS config, not ad hoc prompts

### OpenClaw

- local chat and gateway access
- operator surface for direct household control and later channels

### ElevenLabs

- premium persona voice output for high-touch modes
- local fallback voice for critical alerts and degraded operation

## 7. Security Baseline

- no cameras in bedrooms or bathrooms
- visible/physical mic and camera mute controls
- no raw household video cloud archive by default
- least privilege on every integration token
- separate profiles for adults and children
- audit trail for all class 4-6 actions
- second factor for remote unlock and similar actions

## 8. Delivery Plan

### Slice A: Foundation

- household config
- runtime assembly
- permission engine
- request planner

### Slice B: Voice + Briefing

- OpenAI text model router
- morning brief builder
- persona tuning
- OpenClaw operator flow

### Slice C: Home Nervous System

- Home Assistant client
- mode triggers
- safety and anomaly event shapes

### Slice D: Work + Family Specialists

- executive work planner
- family logistics planner
- child tutoring policy
- Chronicle and faith hooks

### Slice E: Workshop

- printer status adapters
- part inspection ingress
- vendor-prep approval flows

## 9. Open Questions

- Should the first room-level voice prototype use OpenAI Realtime directly or Home Assistant Assist plus escalation?
- Which Home Assistant entities already exist in Chris's real house, and which are aspirational?
- Which calendar/email providers should be first-class in Phase 1 versus later?
- How much of the family dashboard should live inside OpenClaw versus a dedicated control UI?
