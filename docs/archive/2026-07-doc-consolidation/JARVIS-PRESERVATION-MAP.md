# JARVIS Preservation Map

This document exists to protect what is already real in JARVIS before more work reshapes it.

It is a steering document, not a roadmap.

Use it when deciding:

- what stays in the center of the product
- what supports the center
- what should remain available but secondary
- what should stop steering decisions

Read this after:

1. `docs/JARVIS-RESCOPE-ENTRYPOINT.md`
2. `docs/CHRIS-CONTEXT-CANON.md`
3. `docs/JARVIS-V1-EXECUTION-PLAN.md`

## Governing Principle

JARVIS already contains many real capabilities.

The immediate job is not to keep widening the machine.

The immediate job is to preserve the strongest living product loop and consolidate the system around it:

`conversation -> mission -> visible workspace -> Daily Brief -> open loops -> follow-through`

If work weakens that loop, scatters it, or hides it behind builder-facing surfaces, it is probably drift.

## 1. Core

These define JARVIS and should stay at the center of the product.

### Conversation Shell And Continuity

The live shell, typed and voice entry, and persisted conversation state are the front door.

Why it is core:

- JARVIS is conversation-first
- Chris should not have to navigate first
- continuity is required for companion feeling

Protect:

- `/api/respond`
- conversation state persistence
- shell and voice entry parity
- honest, direct, friend-with-tools posture

### Mission Creation

Natural-language intent turning into a real mission is one of the most important product behaviors in the canon.

Why it is core:

- the product standard is not answer quality alone
- the system must turn objectives into missions

Protect:

- natural-language mission capture
- useful first-pass mission structure
- typed and voice mission parity

### Mission Board / Mission Workspace

This is the primary work surface behind the conversation loop.

Why it is core:

- it makes the mission feel real
- it is where progress, status, open loops, and next action become visible

Protect:

- mission board route and module payload
- mission detail and mutation flows
- post-create routing into mission work

### Daily Brief / Chamber Home

This is the best current candidate for the home experience.

Why it is core:

- it answers what changed, what matters, what JARVIS did, and what comes next
- it carries the strongest “presence” feeling in the repo

Protect:

- briefing synthesis
- already working lane
- needs you lane
- drift and recommendation cues
- chamber-first language and posture

### Open Loops / Needs You / Assistant Notifications

These are the follow-through mechanics of the product.

Why it is core:

- they keep the system from collapsing back into one-turn chat
- they make work and pressure visible without forcing dashboard hunting

Protect:

- open-loop visibility
- notification truth
- actionability from Daily Brief and command surfaces

### Truth, Continuity, And Grounding

Memory, known facts, continuity, and grounded retrieval matter only when truthful.

Why it is core:

- JARVIS loses trust fast if it bluffs
- grounding should strengthen the companion, not fake it

Protect:

- source distinction
- no fake memory claims
- no fake Obsidian claims
- no fake “already did” language

## 2. Supporting

These are important because they strengthen the core loop, even if they are not the center of the user experience.

### Approval Queue

Important because JARVIS should not approve itself or hide decision gates.

### Recovery Center

Important because operational truth and failure visibility preserve trust.

### Progress Center

Important because it helps show motion and continuity across work.

### Command Center

Important as an operator and inspection surface.

It should support the product, not become the product.

### Runtime Kernel / Scheduler / Supervision

Critical backstage machinery.

It matters because it enables continuity, background work, and governable action, but it should remain backstage unless surfaced in a human-useful way.

### Apple / Native Follow-Through Surfaces

Important because they extend the real product loop beyond the web shell and reinforce that JARVIS is present across surfaces.

## 3. Specialist

These lanes look real and useful, but they should plug into the companion loop instead of competing with it.

- Health
- Chronicle
- Catalyst
- Workshop
- Publishing and Foundry
- Finance and Wealth
- Navigation
- Dining
- Household and home operations
- Vision and perception
- Scouting, faith, social, and growth lanes

Rule:

These should remain available as strong domains of help, but none of them should become the main identity of JARVIS.

## 4. Drift / Archive Candidate

These are patterns or forces that should be demoted, contained, or treated skeptically.

### Dashboard-First Framing

Dashboards can exist, but the product should not feel like a command center first.

### Visible Agent Theater

Agents may exist under the hood.

Chris should still experience one coherent presence, not a swarm of visible mode switches.

### Builder-First Clutter

Low-signal controls, deeply operational panels, and developer affordances should not dominate the main surfaces.

### Legacy Doctrine Exerting Authority

Archived or superseded docs should not steer current product decisions.

### Breadth Expansion Without Felt User Outcome

New centers, new modules, and new domain slices that do not strengthen the core loop are probably not current-priority work.

## 5. Do Not Break

If future work risks these, stop and verify first.

- conversation shell and conversation continuity
- mission capture quality
- mission board and mission workspace routes
- Daily Brief and chamber-home synthesis
- open loops and assistant notifications
- approval and recovery truth surfaces
- runtime kernel and scheduler integrity
- truthful grounding and source distinction

## 6. Best Next Consolidation Moves

### 1. Keep The Core Loop Sacred

Preserve and strengthen:

`conversation -> mission -> visible workspace -> Daily Brief -> open loops -> follow-through`

### 2. Make Home And Mission The Clear Center

The chamber home and mission workspace should feel like the obvious center of gravity.

### 3. Resolve Canon Contradictions Quickly

When branch reality and canon disagree, fix the canon or stop the branch from pretending alignment exists.

### 4. Demote Broad Platform Gravity

Operator and specialist surfaces should remain useful, but they should not become the emotional center of the product.

### 5. Prefer Consolidation Over Expansion

JARVIS already has enough real capability to become strong.

The next win is coherence, not more breadth.

## 7. Litmus Questions

Before approving work, ask:

1. Does this strengthen the companion loop?
2. Does this make JARVIS feel more present, more useful, or more trustworthy?
3. Does this help Chris think, decide, build, remember, or act?
4. Does this reduce hunting, clutter, or cognitive burden?
5. Does this preserve truth?

If the answer is no, it probably should not lead the next slice.
