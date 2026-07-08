# JARVIS V1 Mission Contract

## Purpose

This document defines Story A1 of the V1 backlog.

It specifies what a V1 mission must contain, how a conversation becomes a
mission, and what the mission workspace must receive immediately after
creation.

This is a product contract first and an implementation guide second.

Read this after:

1. `docs/JARVIS-V1-EXECUTION-PLAN.md`
2. `docs/JARVIS-V1-BUILD-BACKLOG.md`
3. `docs/JARVIS-CANONICAL-MOMENTS.md`

## Contract Goal

When Chris expresses an objective, JARVIS must produce a mission that feels:

- understood
- structured
- actionable
- stewarded

If the output feels like saved text, a generic task, or an agent dossier, the
contract has not been met.

## V1 Mission Standard

A V1 mission must do all of the following:

1. name the objective clearly
2. identify the primary life domain
3. explain what success looks like
4. establish a first plan
5. produce immediate next actions
6. create visible accountability
7. hand off cleanly to the mission workspace

## Input Contract

### Accepted input types

V1 supports:

- typed natural-language objective
- spoken natural-language objective
- follow-up message that advances an existing mission

### Example valid inputs

- `I want to lose 40 pounds.`
- `Help me increase book sales.`
- `I want to prepare for retirement.`
- `Am I ready for summer camp?`
- `How am I doing on my health goals?`

### Input assumptions

- the user may be vague
- the user may describe outcome, not steps
- the user may include multiple concerns in one request
- JARVIS should still produce a useful first mission frame rather than asking many questions

## Launch Domains

V1 mission creation is optimized first for:

1. Health and Longevity
2. Writing and Publishing
3. JARVIS Development
4. Scouting and Service

If a request spans multiple domains, JARVIS should:

- choose one primary domain
- note secondary domains if they materially affect the plan
- avoid fragmenting the initial experience into multiple competing missions unless truly necessary

## Required Mission Fields

These fields are required for every V1 mission.

### Identity

- `mission_id`
- `title`
- `objective`
- `primary_domain`
- `created_at`
- `updated_at`
- `origin`

### Meaning

- `mission_type`
- `why_this_matters`
- `success_definition`
- `time_horizon`
- `status`
- `momentum`

### Plan

- `milestones`
- `next_actions`
- `recommendation`
- `risks`
- `open_loops`

### Stewardship

- `accountability_cadence`
- `progress_signal`
- `support_message`

### Visibility

- `workspace_route`
- `brief_summary`
- `truth_labels`

## Optional Mission Fields

These may be empty in V1 without breaking the experience.

- `target_metrics`
- `due_date`
- `secondary_domains`
- `linked_memories`
- `background_prepared_outputs`
- `approvals`
- `selected_agents`
- `evidence`

These fields can exist in the persistence model, but they must not be required
for the first felt product loop to work.

## Field Definitions

### `mission_type`

A human-meaningful classification of the mission.

Examples:

- `goal-pursuit`
- `campaign`
- `readiness-check`
- `plan-build`
- `recovery`

### `time_horizon`

A coarse planning range.

Allowed V1 values:

- `today`
- `this-week`
- `this-month`
- `this-quarter`
- `ongoing`

### `status`

Allowed V1 values:

- `active`
- `needs-input`
- `at-risk`
- `on-track`
- `paused`
- `completed`

### `momentum`

Allowed V1 values:

- `building`
- `steady`
- `slipping`
- `blocked`
- `unknown`

### `progress_signal`

A plain-language summary of current progress.

Examples:

- `You are slightly ahead of pace.`
- `This mission has not moved in 9 days.`
- `Readiness is improving, but two items remain unresolved.`

### `truth_labels`

Each important mission section should be able to indicate whether it is:

- `confirmed`
- `inferred`
- `missing`
- `stale`
- `unavailable`

## Milestone Contract

Each V1 mission must have 3 to 5 milestones.

Milestones must be:

- outcome-shaped
- understandable without extra context
- sequenced enough to feel like a plan

Bad milestones:

- `Process data`
- `Think about options`
- `Use agent support`

Good milestones:

- `Establish target weight and weekly pace`
- `Create a 4-week movement plan`
- `Define book promotion calendar`
- `Confirm summer camp readiness gaps`

## Next Action Contract

Each V1 mission must have 1 to 3 next actions.

The first next action must be:

- specific
- short
- user-understandable
- immediately actionable or clearly in progress by JARVIS

Bad next action:

- `Continue mission work`

Good next actions:

- `Log current weight and target weight for the new plan`
- `Review the first 3 campaign options JARVIS prepared`
- `Confirm which camp items are still missing`

## Recommendation Contract

Each V1 mission must produce exactly one dominant recommendation.

This recommendation should feel like stewardship.

Examples:

- `Start with consistency, not intensity, for the first two weeks.`
- `Campaign B is the best first move based on current sales velocity.`
- `Solve the two readiness gaps before buying any additional camp supplies.`

## Accountability Contract

Each V1 mission must establish a visible accountability posture at creation.

Required elements:

- cadence
- progress signal
- support message

Examples:

- cadence: `weekly`
- progress signal: `No meaningful health activity has been logged this week.`
- support message: `Let’s recover momentum without overcorrecting.`

The tone must be supportive, direct, and non-shaming.

## Conversation-To-Mission Flow

The V1 flow is:

1. Chris expresses an objective
2. JARVIS identifies the primary domain and mission type
3. JARVIS frames the mission
4. JARVIS generates milestones and next actions
5. JARVIS generates one recommendation and one accountability signal
6. JARVIS creates the mission record
7. JARVIS routes the user into the mission workspace
8. JARVIS reflects the mission in the Daily Brief and `What Matters`

## Workspace Handoff Contract

Immediately after mission creation, the workspace must receive:

- `mission_id`
- `title`
- `objective`
- `primary_domain`
- `status`
- `momentum`
- `milestones`
- `next_actions`
- `recommendation`
- `progress_signal`
- `accountability_cadence`
- `open_loops`
- `truth_labels`

If the workspace requires approvals, agents, or deeper evidence to feel usable,
the contract is too heavy for V1.

## Brief Linkage Contract

Every newly created active mission must produce a brief-ready summary with:

- mission title
- one-sentence why-it-matters summary
- current status
- top next action

This is the minimum needed for `What Matters`.

## Domain-Specific Expectations

### Health and Longevity

Must usually include:

- measurable target or direction
- consistency-oriented next steps
- progress cadence
- habit or routine framing

### Writing and Publishing

Must usually include:

- growth or output objective
- campaign or content milestones
- audience or promotion next actions
- success indicators

### JARVIS Development

Must usually include:

- product objective
- delivery milestone framing
- current blocker or risk
- next build step

### Scouting and Service

Must usually include:

- readiness or event objective
- missing-items or logistics clarity
- timeline sensitivity
- recommended next coordination step

## Tone Contract

Mission creation language should sound like:

- `Understood. Let's build a plan.`
- `Let's create the mission.`
- `I mapped the first version of this.`
- `Here is the plan I recommend starting with.`

It should not sound like:

- raw schema output
- assistant hedging
- visible agent bureaucracy
- generic productivity coaching

## Anti-Patterns

The mission contract is broken if the result becomes:

- a glorified note
- a task list with no strategy
- a dossier full of internal system detail
- a dashboard artifact with no clear next move
- an over-asked clarification funnel before any useful structure appears

## Current Code Impact

The current mission creation path in `jarvis/missions.py` already provides:

- `mission_id`
- inferred domain
- title
- brief
- status
- follow-ups
- selected agents

V1 implementation must strengthen that path to produce:

- better domain routing for the launch domains
- explicit objective and success framing
- user-facing milestones
- user-facing next actions
- accountability cadence
- recommendation
- progress signal
- workspace-ready payload

## Acceptance Tests

This contract is satisfied when all of the following are true:

1. A health objective creates a useful mission with milestones and next actions.
2. A writing objective creates a useful campaign-style mission.
3. A JARVIS Development objective creates a build-focused mission with a real next step.
4. A scouting objective creates a readiness-style mission with missing-item awareness.
5. Each mission routes cleanly into the workspace.
6. Each mission appears correctly in `What Matters`.
7. Voice and typed creation both satisfy the same mission standard.

## Immediate Implementation Consequence

After this contract, the next build step should be:

1. update `jarvis/missions.py` mission creation output
2. update mission workspace payload expectations
3. update Daily Brief linkage to consume the new mission summary

That is the first real slice of the Life Operating Officer product.
