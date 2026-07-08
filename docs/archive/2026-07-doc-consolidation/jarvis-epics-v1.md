---
workflowType: "manual-bmad-epics-bootstrap"
project: "JARVIS"
sourceDocuments:
  - "_bmad-output/planning-artifacts/jarvis-prd-v1.md"
  - "_bmad-output/planning-artifacts/jarvis-architecture-v1.md"
---

# JARVIS - Epic Breakdown

## Overview

This document decomposes the JARVIS PRD and architecture into a first implementation backlog that preserves the household-associate vision while still letting us ship in thin slices.

## Requirements Inventory

### Functional Requirements

- `FR1` Voice shell with room and speaker context.
- `FR2` Household modes and family briefings.
- `FR3` Permission-gated actions.
- `FR4` Home Assistant integration seam.
- `FR5` Executive work copilot flows.
- `FR6` Family logistics planning flows.
- `FR7` Child-safe tutoring guardrails.
- `FR8` Workshop and printer support paths.
- `FR9` Faith and Chronicle support hooks.
- `FR10` Security and anomaly monitoring hooks.

### NonFunctional Requirements

- `NFR1` Local-first sensitive state.
- `NFR2` Clear approval and auditability.
- `NFR3` Modularity for new rooms/tools.
- `NFR4` Manual fallback when AI fails.
- `NFR5` Helpful-not-creepy user experience.

### Additional Requirements

- Use Home Assistant as the actuator boundary.
- Use OpenClaw for chat/operator shell, not sole business logic.
- Use tiered OpenAI model routing.
- Keep children out of adult work data and tools.

### UX Design Requirements

- Present household modes in plain language.
- Keep approvals explicit and readable.
- Preserve different tones for Chris, Rebekah, Caleb, and Anna.
- Avoid dashboard clutter in family-facing surfaces.

### FR Coverage Map

- Epic 1 covers FR2, FR3, FR10, NFR1-NFR5.
- Epic 2 covers FR1, FR4.
- Epic 3 covers FR5 and part of FR9.
- Epic 4 covers FR6 and family-facing parts of FR2.
- Epic 5 covers FR7.
- Epic 6 covers FR8.

## Epic List

- Epic 1: Household runtime foundation
- Epic 2: Voice, OpenAI routing, and operator shell
- Epic 3: Executive work and Chronicle assistance
- Epic 4: Family logistics and home modes
- Epic 5: Child-safe tutoring
- Epic 6: Workshop and maker copilot

## Epic 1: Household Runtime Foundation

Establish the family-aware runtime, policy model, and planning artifacts that every later module depends on.

### Story 1.1: Create household configuration model

As a system maintainer,
I want a structured household config file,
So that users, rooms, modes, and module priorities are explicit and versioned.

**Acceptance Criteria:**

**Given** a fresh checkout  
**When** the runtime loads  
**Then** it can parse a household config file with users, rooms, and modes  
**And** it fails clearly when required fields are missing

### Story 1.2: Implement permission engine

As a household operator,
I want actions classified by risk,
So that JARVIS knows when to observe, prepare, ask, or block.

**Acceptance Criteria:**

**Given** an action request  
**When** it is evaluated  
**Then** the runtime returns a risk class and approval requirement  
**And** restricted actions are blocked

### Story 1.3: Implement request planner

As a household operator,
I want JARVIS to generate a plan before acting,
So that every request is routed with context and guardrails.

**Acceptance Criteria:**

**Given** a user, room, and request  
**When** the planner runs  
**Then** it returns module, model tier, approval class, and rationale

## Epic 2: Voice, OpenAI Routing, and Operator Shell

Connect the runtime to voice and operator surfaces without collapsing everything into one model call.

### Story 2.1: Add OpenAI model routing config

As a developer,
I want explicit text, router, and realtime model settings,
So that cost and quality can be tuned independently.

### Story 2.2: Build local morning briefing command

As Chris,
I want a morning briefing generator,
So that JARVIS can summarize Body, Home, and Mission cleanly.

### Story 2.3: Define OpenClaw bridge seam

As a developer,
I want a clear boundary between JARVIS domain logic and OpenClaw,
So that chat, approvals, and channels can be added without moving household policy into the shell.

## Epic 3: Executive Work and Chronicle Assistance

Support Chris's strategy, writing, and faith/Chronicle workflows.

### Story 3.1: Add executive work mode planner

As Chris,
I want meeting and writing requests routed to an executive module,
So that JARVIS can distinguish manuscript, research, and meeting work from household chores.

### Story 3.2: Add Chronicle and devotional mode hooks

As Chris,
I want Scripture and Chronicle requests recognized as a separate mode,
So that faith interactions are grounded and not mixed with generic productivity output.

### Story 3.3: Add confidentiality tagging

As Chris,
I want work-sensitive material flagged for stricter handling,
So that external sharing and family surfaces do not expose private company context.

## Epic 4: Family Logistics and Home Modes

Support Rebekah's coordination burden and the house-wide rhythm engine.

### Story 4.1: Add household mode transitions

As the household,
I want Dawn, Family Morning, Work, Dinner, and Goodnight modes,
So that the system behavior changes with the day instead of remaining static.

### Story 4.2: Add family logistics planner

As Rebekah,
I want schedule and reminder requests routed to a family logistics module,
So that groceries, troop plans, and departure loops feel calm instead of chaotic.

### Story 4.3: Add message drafting guardrails

As a family operator,
I want outbound family messages staged but not sent,
So that JARVIS helps prepare communication without overstepping.

## Epic 5: Child-Safe Tutoring

Provide coaching without dishonest completion.

### Story 5.1: Add child profile boundaries

As a parent,
I want child profiles isolated from adult data,
So that household trust and safety are preserved.

### Story 5.2: Add tutoring response policy

As a parent,
I want tutoring prompts to encourage explanation and effort,
So that JARVIS forms capability instead of replacing it.

### Story 5.3: Add parent-visible progress summaries

As a parent,
I want lightweight summaries of tutoring interactions,
So that I can monitor patterns without reading every exchange.

## Epic 6: Workshop and Maker Copilot

Support creative making without unsafe automation.

### Story 6.1: Add workshop mode planner

As Chris,
I want workshop requests recognized distinctly,
So that printer, material, and part-support workflows get the right context.

### Story 6.2: Add printer integration seam

As Chris,
I want a printer-status adapter interface,
So that Bambu and future device integrations can plug into the same runtime model.

### Story 6.3: Add vendor-prep approval flow

As Chris,
I want quote prep and upload requests staged for review,
So that JARVIS can help aggressively without making external commitments on its own.
