---
title: 'Versioned office charters and automatic onboarding'
type: 'feature'
created: '2026-07-11'
status: 'done'
review_loop_iteration: 0
baseline_commit: '5def6d185a2a495d093584f42af286bf3d4d523b'
context:
  - '{project-root}/docs/BUILD-OFFICE-AUTOMATION.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The Orchestration, Architect, Build, and QA Offices have agreed roles in conversation, but no single versioned contract defines their authority, handoffs, prohibited actions, evidence, or escalation rules. Assignment prompts therefore leave room for role drift, self-approval, and cross-office collisions.

**Approach:** Add one canonical office-charter registry, expose copy-ready office onboarding through the Build Office CLI, and embed the applicable charter version and instructions into every generated assignment prompt and inbox item.

## Boundaries & Constraints

**Always:** Orchestration owns goal intake, mission lifecycle, routing, dependencies, heartbeats, collision control, retries, escalation, and release-gate evaluation. Architect owns frozen technical contracts and dispositions of QA findings. Build implements only bounded approved missions in isolated writable worktrees. QA independently verifies and never repairs the work it reviews. Chris remains product-intent owner and initial final merge authority. Every office response must use durable mission evidence rather than chat-only summaries.

**Ask First:** Changing Chris's product intent, allowing an office to approve its own work, granting merge or push authority, making QA writable, changing the four-office topology, or assigning autonomous external side effects requires Chris's approval.

**Never:** Put the offices inside JARVIS runtime behavior; duplicate BMAD planning artifacts; allow two writable offices on the same worktree or overlapping scope; silently revise a frozen contract; let Orchestration design, Build self-review, QA fix, or Architect merge; automatically push or merge.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Office onboarding | Known office name | Versioned, copy-ready charter containing purpose, authority, inputs, outputs, prohibitions, gates, evidence, and heartbeat procedure | Reject unknown office names with valid choices |
| Assignment generation | Mission assignment with a recognized duty | Prompt and inbox identify the governing charter version and include duty-specific instructions | Fail closed if no charter maps to the duty |
| Contract evolution | Charter text changes | Version is explicitly incremented and newly created missions record that version | Existing mission evidence retains its recorded version |

</frozen-after-approval>

## Code Map

- `docs/OFFICE-CHARTERS.md` -- canonical human-readable authority and handoff contract for all four offices.
- `jarvis/office_charters.py` -- versioned machine-readable charter registry and duty-to-office resolution.
- `jarvis/build_office.py` -- records charter version on missions and injects charter instructions into prompts and inbox payloads.
- `scripts/jarvis_build_office.py` -- exposes an `office-brief` onboarding command.
- `tests/test_office_charters.py` -- validates completeness, authority separation, lookup failures, and onboarding output.
- `tests/test_build_office.py` -- verifies mission/prompt/inbox charter integration and fail-closed duty handling.

## Tasks & Acceptance

**Execution:**
- [x] `docs/OFFICE-CHARTERS.md` -- define exact responsibilities, authority matrix, lifecycle, handoffs, evidence, heartbeat, escalation, and human gates.
- [x] `jarvis/office_charters.py` -- provide one immutable versioned registry and copy-ready onboarding brief generation.
- [x] `jarvis/build_office.py` -- bind mission assignments to the registry without changing collision or release semantics.
- [x] `scripts/jarvis_build_office.py` -- add `office-brief {orchestration|architect|build|qa|all}`.
- [x] `tests/test_office_charters.py`, `tests/test_build_office.py` -- cover the I/O matrix and separation-of-duties invariants.
- [x] `docs/BUILD-OFFICE-AUTOMATION.md` -- replace provisional role language with links and practical onboarding commands.

**Acceptance Criteria:**
- Given a new office session, when its operator runs `office-brief`, then it receives a self-contained instruction that identifies what it owns, what it must not do, how it receives work, and how it hands work back.
- Given any generated assignment, when an office reads its prompt or inbox payload, then the applicable office role and charter version are explicit.
- Given the standard lifecycle, when work moves from goal to release, then no office designs, implements, verifies, and approves the same change.
- Given existing Build Office missions and tests, when the suite runs, then prior lifecycle, collision, retry, scope, and release behavior remains intact.

## Verification

**Commands:**
- `python3 -m pytest -q tests/test_office_charters.py tests/test_build_office.py` -- expected: all charter and existing control-plane tests pass.
- `python3 scripts/jarvis_build_office.py office-brief all` -- expected: valid JSON containing all four versioned onboarding briefs.
- `python3 scripts/jarvis_build_office.py demo --dry-run` -- expected: generated prompts remain executable and contain charter metadata.

## Suggested Review Order

**Authority and lifecycle**

- Start with the binding separation-of-duty model and end-to-end handoffs.
  [`OFFICE-CHARTERS.md:7`](../../docs/OFFICE-CHARTERS.md#L7)

- Review the machine-readable projection used to teach every persistent office.
  [`office_charters.py:7`](../../jarvis/office_charters.py#L7)

**Frozen contracts and assignments**

- Mission intake freezes a committed Architect blob and forbids Build from changing it.
  [`build_office.py:270`](../../jarvis/build_office.py#L270)

- Blob validation records immutable content, baseline, and SHA-256 instead of trusting labels.
  [`build_office.py:348`](../../jarvis/build_office.py#L348)

- Prompts combine the recorded office snapshot with the exact frozen technical contract.
  [`build_office.py:690`](../../jarvis/build_office.py#L690)

**QA target integrity**

- Fingerprinting covers commits, worktree state, tracked diffs, and changed-file content.
  [`build_office.py:854`](../../jarvis/build_office.py#L854)

- Release planning revalidates the reviewed target after QA submits its verdict.
  [`build_office.py:1012`](../../jarvis/build_office.py#L1012)

**Operator surface and proof**

- The CLI exposes onboarding and requires an Architect contract reference at intake.
  [`jarvis_build_office.py:29`](../../scripts/jarvis_build_office.py#L29)

- Contract, identity, and prompt tests prove fail-closed assignment behavior.
  [`test_build_office.py:126`](../../tests/test_build_office.py#L126)

- Moving-target tests cover handoff, active review, and post-verdict mutation.
  [`test_build_office.py:567`](../../tests/test_build_office.py#L567)
