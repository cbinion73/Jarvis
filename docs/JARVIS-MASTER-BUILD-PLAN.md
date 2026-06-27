# JARVIS Master Build Plan

This document is the Architect Office build plan for JARVIS.

It defines what we are trying to accomplish, the major epics and story lanes, the acceptance criteria that govern progress, and the Definition of Done that Build Office and QA must satisfy before Architect Office approves work.

This is a planning and governance document. It is not permission to begin every epic immediately. Phase gates, Chris canon, and Architect Office assignment still control what may actually be built next.

## 1. What We Are Trying To Accomplish

JARVIS should become the private companion intelligence Chris wishes ChatGPT could become for his life.

The target relationship model is:

> a smart, loyal friend with tools

That means JARVIS must help Chris:

- think
- decide
- build
- remember
- act

And it must do that without drifting into:

- therapist behavior
- dashboard-first behavior
- generic chatbot behavior
- mystical companion behavior
- fake autonomy
- empty modal or workbench behavior
- agent theater
- fake tool or memory claims

Architect Office is not trying to maximize visible features.

Architect Office is trying to produce a truthful, useful, durable companion system that earns continued use in Chris's real life.

## 2. North Star

Architect Office should keep testing the build against two questions:

1. Would Chris want to keep talking to this?
2. Did JARVIS help Chris think, decide, build, remember, or act?

If the answer is no, the work is not good enough even if the code technically works.

## 2.1 Immediate Practical Goal

Beyond the long-range build order, Architect Office should optimize near-term work for one practical outcome:

Chris should have a conversational, helpful friend to talk to tomorrow.

That means near-term implementation slices should prefer:

- conversation quality over feature breadth
- helpfulness over impressive architecture
- practical next-step support over abstract capability
- trustworthy warmth over therapist tone
- grounded truth over fake competence

If a slice makes the system more elaborate but does not make tomorrow's conversation more useful, it is probably not the next best slice.

## 3. Build Order

The canonical build order is:

1. Mind
2. Memory
3. Hands
4. Workforce
5. Autonomy
6. Learning loop
7. Self-research

This means:

- conversation quality and truth posture come before expansion
- memory grounding comes before broad autonomy claims
- useful hands come before decorative UI
- workforce comes after visible, bounded, inspectable work exists
- autonomy comes after companion usefulness and truth are stable

## 4. Epic Structure

### Epic 1. Governance, Review, and Separation of Duties

Purpose:
Make sure Architect Office, QA, and Build Office can operate cleanly without collapsing into one function.

Story lanes:

- Build Office request, report, and review loop
- canon-aware Architecture Review process
- QA verification protocol and evidence grading
- phase-gate enforcement
- approval boundaries and truthfulness boundaries

Success looks like:
Build Office can implement, QA can verify, and Architect Office can approve or reject based on repo truth instead of narrative commentary.

### Epic 2. Companion Mind

Purpose:
Establish the primary conversation spine so ordinary interaction already feels like the right product.

Story lanes:

- primary conversation spine
- context packet discipline
- friend-with-tools voice posture
- truth contract enforcement
- anti-therapist and anti-generic-chatbot response tests
- ordinary conversation remains primary

Success looks like:
JARVIS feels direct, warm, practical, honest, loyal, and useful by default.

### Epic 3. Memory Grounding

Purpose:
Give JARVIS bounded, truthful personal grounding without bluffing memory.

Story lanes:

- compact retrieval
- source distinction
- profile versus retrieval separation
- bounded personal context use
- no fake memory or fake Obsidian claims

Success looks like:
JARVIS can use relevant memory and retrieval when available, and plainly state limits when not.

### Epic 4. Hands and Workbench

Purpose:
Let conversation produce real useful objects when hands are needed.

Story lanes:

- checklist creation
- plan creation
- draft creation
- research packet creation
- recommendation and evidence surfaces
- workbench object routing
- no empty modal behavior

Success looks like:
When Chris needs something built, JARVIS places a real object on the table instead of opening decorative UI.

### Epic 5. Tool Truth and Action Surfaces

Purpose:
Move from advice-only interaction into truthful bounded action.

Story lanes:

- search and retrieval proof
- file and artifact creation proof
- save/open boundaries
- explicit degraded-mode honesty
- execution traces behind capability claims

Success looks like:
Capability language matches actual execution and can be verified.

### Epic 6. Workforce and Delegation

Purpose:
Add subordinate agents only when they produce inspectable work and do not become theater.

Story lanes:

- bounded delegation
- inspectable outputs
- handoff visibility
- ownership and acknowledgment
- agent output review

Success looks like:
Delegated work creates real reviewable results rather than invisible claims about background intelligence.

### Epic 7. Learning Loop

Purpose:
Make JARVIS improve over time without destabilizing truth or trust.

Story lanes:

- outcome capture
- usefulness feedback
- bounded adjustment loops
- regression checks around learned behavior

Success looks like:
JARVIS gets more useful through evidence-backed iteration, not by accumulating lore or bluffing adaptation.

### Epic 8. Self-Research

Purpose:
Eventually support self-directed research and longer-range assistance under explicit boundaries.

Story lanes:

- scoped research tasks
- evidence packet generation
- source-backed synthesis
- explicit uncertainty handling

Success looks like:
JARVIS can explore, gather, and return useful source-backed work without slipping into fake autonomy.

## 5. Story Shape

Every story assigned by Architect Office should include:

- requested outcome
- phase
- in-scope work
- out-of-scope work
- canon sources that govern the slice
- required tests
- required runtime evidence
- approval questions

Every story should be small enough that:

- Build Office can implement it in a bounded pass
- QA can verify it without ambiguity
- Architect Office can approve or reject it without broad interpretation

## 6. Acceptance Criteria Framework

Every story and epic should be judged through four acceptance lenses.

### Product Fit

- Does this feel like a smart, loyal friend with tools?
- Would Chris actually want to keep talking to this?
- Does it help him think, decide, build, remember, or act?

### Truth Fit

- Are all capability claims backed by actual execution?
- Are limits stated plainly?
- Is retrieval or memory honestly distinguished from assumption?

### Scope Fit

- Is the work inside the active phase gate?
- Does it avoid forbidden scope?
- Does it preserve current canon and strategic boundaries?

### Evidence Fit

- Do relevant tests exist and pass?
- Is runtime proof present when runtime claims are made?
- Is the git state declared honestly?
- Is the Build Office report complete enough for review?

## 7. Epic-Level Acceptance Criteria

### Epic 1. Governance, Review, and Separation of Duties

- Architect Office can issue bounded assignments.
- Build Office returns a structured report.
- QA can verify claims independently.
- Architecture Review can identify canon gaps, missing evidence, and non-canon drift.
- No function self-certifies its own work.

### Epic 2. Companion Mind

- Default replies match the friend-with-tools voice standard.
- Therapist language, generic assistant language, and mystical drift are actively checked.
- Conversation remains primary during normal interaction.
- JARVIS does not bluff tools, memory, Obsidian, or agents.

### Epic 3. Memory Grounding

- Memory or retrieval is compact and relevant.
- Retrieved context is distinguishable from profile or static context.
- JARVIS does not claim retrieval when retrieval did not happen.
- External knowledge sources are protected from destructive write behavior unless explicitly approved.

### Epic 4. Hands and Workbench

- Workbench outputs are real and useful.
- Empty modals do not appear.
- Generic filler objects are not created by default.
- Missing context is requested before low-value artifacts are produced.

### Epic 5. Tool Truth and Action Surfaces

- Tool/action claims are evidence-backed.
- Degraded mode is honest.
- Save/open/create language is used only when true.
- Runtime proof exists for claimed action paths.

### Epic 6. Workforce and Delegation

- Delegation produces inspectable outputs.
- Ownership and handoff are visible.
- Agent claims are attributable.
- There is no agent theater.

### Epic 7. Learning Loop

- Learning mechanisms improve usefulness without inventing false memory.
- Regressions are testable.
- Adjustments are bounded and reviewable.

### Epic 8. Self-Research

- Research outputs are source-backed.
- Scope is bounded.
- Uncertainty is stated honestly.
- The behavior does not imply autonomous competence beyond the evidence.

## 8. Definition of Done

A story is done only when all of the following are true:

1. The work stays inside the active phase gate.
2. The work aligns with Chris canon and active canon.
3. The implementation is complete enough to evaluate the requested outcome.
4. Relevant tests were run and reported honestly.
5. Runtime evidence exists for runtime claims.
6. Known limitations and risks are stated plainly.
7. The Build Office report is complete.
8. QA concerns are either resolved or explicitly logged.
9. Architect Office review exists.
10. The result passes the practical product test:
    Would Chris want to keep talking to this, and did JARVIS help him think, decide, build, remember, or act?

If any of those are missing, the story is not done.

## 9. Definition of Ready

Before Build Office should start a story, the story should already have:

- a clear requested outcome
- explicit scope boundaries
- an assigned phase
- canon sources named
- evidence expectations named
- no hidden product-direction ambiguity

If those are not present, the work should go back to Architect Office for clarification before implementation starts.

## 10. Near-Term Sequence

The near-term Architect Office sequence is:

1. finish the governance and handoff loop
2. complete the full fact-base map of existing JARVIS capability
3. produce the baseline Architecture Review for current JARVIS state
4. reconcile canon against current runtime truth where drift exists
5. define the next approved implementation slice
6. send that slice to Build Office
7. require QA and Architecture Review before approval

Near-term product priority after governance and canon cleanup:

1. make tomorrow's conversational experience more helpful, natural, and trustworthy
2. strengthen the companion mind before expanding more surfaces
3. only add new hands, memory, or tools when they clearly improve the actual conversation relationship

## 11. Current Planning Warnings

- Do not let broad feature excitement outrun canon.
- Do not treat commentary as proof.
- Do not let stale docs override active phase gates.
- Do not let runtime experimentation silently become product direction.
- Do not let Obsidian, agents, or UI expansion jump ahead of the build order without explicit canon change.

## 12. Planning Rule

Architect Office should direct small bounded slices that strengthen the companion system in the correct order.

The build plan is successful only if JARVIS becomes more truthful, more useful, more grounded, and more worth talking to over time.
