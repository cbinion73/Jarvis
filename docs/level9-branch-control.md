# Level 9 Branch Control

This document is the active control map for parallel Level 9 implementation work.

## Principle

JARVIS should advance through parallel lanes only when each lane has a clear ownership boundary, low file-overlap, and a crisp merge target. The goal is acceleration without creating false progress or integration fog.

## Runtime Topology

- Primary synced checkout:
  - Repo: `/Users/chris/Library/CloudStorage/OneDrive-Personal/CODE/CODE/JARVIS`
  - Branch: `codex/apple-native-command-surface`
  - Role: integration lane and doctrine source
- Clean execution base:
  - Repo: `/tmp/jarvis-push-helper`
  - Role: stable branch/checkpoint base for Level 9 slices

## Current Operational Status

- Helper-clone-backed worktrees are the active parallel execution model.
- OneDrive-backed Level 9 worktrees created from the primary checkout repeatedly stalled in `locked initializing` and should be treated as quarantined until re-proven healthy.
- Clean slice checkpoints currently live in `/tmp/jarvis-push-helper` and are the source of truth for autonomous branch progression.

## Integration Lane

- Branch: `codex/apple-native-command-surface`
- Role: active integration lane for in-flight backend + Apple surface work already underway in the main working copy
- Notes:
  - This lane currently contains dirty, uncommitted work.
  - It should not be used for broad new parallel experiments.
  - New work here should be limited to finishing the current governance/promotion substrate slice and stabilizing it into a clean commit.

## Parallel Lanes

### 1. Governance Runtime

- Branch: `codex/level9-governance-runtime`
- Worktree: `/private/tmp/jarvis-level9-governance-runtime`
- Active helper lane: `/private/tmp/jarvis-level9-governance-helper` on `codex/level9-governance-slice`
- Scope:
  - trust-zone control plane
  - promotion engine
  - supervision contracts
  - consent gates
  - promotion application flows
  - rollback, demotion, suspension posture
- Merge target:
  - backend governance substrate
- Avoid:
  - broad UI work
  - unrelated Apple surface changes

### 2. Agent Society Health

- Branch: `codex/level9-agent-society-health`
- Worktree: `/private/tmp/jarvis-level9-agent-society-health`
- Active helper lane: `/private/tmp/jarvis-level9-agent-society-helper` on `codex/level9-agent-society-slice`
- Scope:
  - mission control inspectability
  - agent work-state visibility
  - blocked-work visibility
  - pending-review pressure
  - handoff and ownership health
  - stewardship lane summaries
- Merge target:
  - operator-facing always-on staff visibility
- Avoid:
  - low-level persistence rewrites
  - trust-zone mechanics unless strictly required for display

### 3. Event Truth And Persistence

- Branch: `codex/level9-event-truth-persistence`
- Worktree: `/private/tmp/jarvis-level9-event-truth-persistence`
- Active helper lane: `/private/tmp/jarvis-level9-event-truth-helper` on `codex/level9-event-truth-lane`
- Scope:
  - append-only event history
  - projections over event truth
  - replay and auditability
  - durable run records
  - locking and concurrency safety
- Merge target:
  - Level 4+ substrate integrity
- Avoid:
  - presentation-layer work
  - household UX concerns

### 4. Household Operability

- Branch: `codex/level9-household-operability`
- Worktree: `/private/tmp/jarvis-level9-household-operability`
- Active helper lane: `/private/tmp/jarvis-level9-household-operability-helper` on `codex/level9-household-operability-lane`
- Scope:
  - non-builder controls
  - family-safe surfaces
  - approvals and review ergonomics
  - Rebekah-usable command/review flows
  - household-visible trust-stage status
- Merge target:
  - legitimacy and operator independence
- Avoid:
  - deep runtime-kernel mutation
  - persistence-engine rewrites

## Execution Order

1. Stabilize the current integration lane into a clean governance/promotion commit.
2. Advance `codex/level9-agent-society-health` in parallel because it can move fast with low conflict.
3. Use `codex/level9-event-truth-persistence` for the next deeper substrate pass once the current governance slice is landed.
4. Pull `codex/level9-household-operability` forward when the operator-facing surfaces can consume the new governance and mission-health outputs.

## Merge Rules

- Merge by capability slice, not by elapsed time.
- Do not merge a lane that changes both substrate and UI unless that coupling is unavoidable.
- Prefer small, credible commits that preserve replayable system truth.
- If a lane begins to overlap `jarvis/runtime.py` and `jarvis/service.py` heavily with another active lane, stop and re-slice before continuing.

## Current Decision

The currently healthy parallel execution lanes under active control are:

- `codex/level9-governance-slice`
- `codex/level9-agent-society-slice`
- `codex/level9-event-truth-lane`
- `codex/level9-household-operability-lane`

Reason:

- They are backed by clean helper-clone worktrees that actually materialize and run.
- They preserve separation between governance, inspectability, and persistence concerns.
- They restore real parallel execution capacity while the original synced-checkout worktree paths remain quarantined.
