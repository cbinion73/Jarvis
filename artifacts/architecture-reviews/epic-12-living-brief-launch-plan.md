# Epic 12 Launch Plan

Last updated: 2026-06-28

## Epic

Epic 12. Living Brief and Operating Picture

## Why This Is Next

The repo already has a real Morning Brief seam:

- `jarvis/morning_brief_pipeline.py`
- `GET /api/briefing/morning`
- `/briefing-center`

But the current brief still underuses the product we now actually have.

Repo-truth findings:

- the Morning Brief exists and is already framed in canon as a core JARVIS experience
- the code currently hardcodes calendar and email as unavailable in `jarvis/morning_brief_pipeline.py`
- JARVIS now has working OpenAI, Google Workspace, family-calendar, and Obsidian support in local repo truth
- the brief is the strongest existing seam for turning those working integrations into practical everyday usefulness

This makes Epic 12 the highest-value next feature lane.

## Product Outcome

Chris should be able to open JARVIS and immediately get:

- what changed
- what matters
- what is waiting
- what JARVIS prepared
- what to do next

And those answers should come from real current signals when available, with plain degraded wording when they are not.

## Canon Guidance

Primary governing canon:

- `docs/CANON-REGISTRY.md`
- `docs/CHRIS-INTENT-CANON.md`
- `docs/CHRIS-CONTEXT-CANON.md`
- `docs/PHASE-GATES.md`
- `docs/JARVIS-PRESERVATION-MAP.md`
- `docs/JARVIS-SESSION-STATE.md`

Critical constraints:

- not a dashboard-first build
- conversation remains primary
- no fake capability claims
- no fake "already did" claims
- no fake calendar, email, memory, or autonomy claims
- recommendation quality matters more than adding more cards

## Slice Order

### Slice 1. Brief Signal Truth Uplift

Goal:
Replace hardcoded unavailable brief labels with real signal posture for currently working integrations and keep degraded wording explicit where data is still not live.

Expected scope:

- inspect `jarvis/morning_brief_pipeline.py`
- inspect current support/status seams used elsewhere in repo truth
- wire truthful signal posture for:
  - calendar
  - email
  - Obsidian/context grounding
  - open loops already available in local repo truth
- preserve honest degraded wording when a support is configured but does not yield usable live data
- update or add tests around Morning Brief truth labels and recommendation shaping

Out of scope:

- major UI redesign
- fake inbox summarization without real retrieval
- fake calendar event synthesis
- autonomous execution claims
- Hetzner deployment claims without live hosted proof

Acceptance criteria:

- Morning Brief no longer hardcodes calendar/email unavailable when repo truth says those supports are connected
- truth labels reflect actual support posture, not stale assumptions
- if a signal is connected-but-empty, the wording says that plainly
- tests cover the new truth-label behavior
- no regression in existing Morning Brief route behavior

### Slice 2. What Is Waiting

Goal:
Add a real "waiting on people / waiting on systems" layer using bounded email/open-loop state.

### Slice 3. While You Were Away

Goal:
Turn existing activity and autonomy/delegation/output seams into a readable "what JARVIS did" layer.

### Slice 4. Recommendation to Action Surface

Goal:
Let the brief hand Chris directly into the right object or next move instead of stopping at narrative.

### Slice 5. Living Brief Acceptance Pass

Goal:
Run a focused acceptance battery proving the brief is useful, truthful, and companion-shaped.

## First Build Office Instruction

Implement Epic 12 Slice 1 only.

Deliver:

- code changes
- tests run
- compile/runtime verification
- exact truth notes for any signals that remain degraded
- any blockers that prevent a live signal from being surfaced honestly
