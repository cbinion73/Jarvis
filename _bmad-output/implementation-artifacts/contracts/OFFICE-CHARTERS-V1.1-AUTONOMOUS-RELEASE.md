---
title: Office Charters v1.1 Autonomous Delivery and Release
status: frozen
owner: architect-office
charter_version_target: 1.1.0
risk: critical
approved_by: Chris
approval_basis: Chris explicitly delegated autonomous build, integration, push, deployment verification, recovery, and roadmap continuation while remaining an observer through the dashboard.
---

# Frozen Architect Contract: Office Charters v1.1 Autonomous Delivery and Release

## Bounded goal

Version the office charter from `1.0.0` to `1.1.0` so Orchestration is the only continuous heartbeat and actively carries durable signals between event-driven Architect, Build, and QA offices. After all independent evidence gates pass, Orchestration may mechanically integrate, push, observe deployment health, recover or roll back failure, update visible status, and advance the next dependency-ready approved roadmap mission without routine Chris approval.

This transfers gated release authority; it does not collapse separation of duties, permit an office to approve itself, authorize product-intent changes, or waive evidence.

## Risk classification

**Critical.** The change grants autonomous merge, push, and deployment authority and alters the delivery control plane. Dispatch and first autonomous release require the contract, independent Build implementation, independent QA approval, and explicit mission evidence. Existing product missions may continue under v1.0, but no office may claim v1.1 release authority until the implementation is canonical and its onboarding brief reports `1.1.0`.

## Authority invariants

1. **One heartbeat:** Orchestration is the only continuously polling office. Architect, Build, and QA are event-driven and are actively awakened by Orchestration with exact mission evidence.
2. **Separation of duties:** No office may design, implement, independently verify, and approve the same change. Architect does not implement its contract; Build does not self-review; QA does not repair; Orchestration does not invent architecture, implement product code, perform QA, or waive findings.
3. **Active routing:** Every Orchestration cycle must advance durable state, verify active progress, recover a supported failure, deliver the next office signal, or escalate an exact blocker. Repeatedly reporting an unchanged inbox is not orchestration.
4. **Gated release:** Orchestration may integrate, merge, push, and observe deployment only when the frozen contract, immutable Build target, exact changed-file evidence, independent QA approval, Architect finding disposition, scope checks, target fingerprint, clean-state checks, and required tests all agree.
5. **No gate waiver:** Missing, stale, contradictory, or moving-target evidence blocks release. Orchestration cannot reinterpret an approval, accept Build self-approval, or convert a QA rejection into a warning.
6. **Automated recovery:** Failed dispatch, stale lease, crashed office, missing response, rejected implementation, deployment-health failure, or unchanged state must enter a recorded retry, reroute, rollback, or precise escalation path; it must not stall silently.
7. **Release safety:** Pushes that trigger deployment require a recorded pre-release ref, post-deploy health verification, bounded observation window, and a tested rollback plan. Health failure blocks roadmap advancement and triggers rollback or a precise recovery mission.
8. **Observer posture:** Chris owns product vision and may inspect or intervene through the dashboard, but is not a routine contract, repair, merge, push, or deployment gate after v1.1 becomes canonical.
9. **Human-only blockers:** Orchestration may escalate to Chris only for unavailable credentials/OAuth consent, a new purchase or paid service, unavailable physical access, legal/contractual authorization, unrecoverable destructive data loss, or genuinely conflicting product intent.
10. **No silent authority growth:** Authority remains limited to approved roadmap goals and committed frozen contracts. A new product direction still requires Chris intent and Architect contract work.

## Owned paths

- `docs/OFFICE-CHARTERS.md`
- `jarvis/office_charters.py`
- `jarvis/build_office.py`
- `scripts/jarvis_build_office.py`
- `tests/test_office_charters.py`
- `tests/test_build_office.py`
- `docs/BUILD-OFFICE-AUTOMATION.md`

## Existing-work preservation boundary

At contract freeze, `main` contains uncommitted changes in:

- `jarvis/build_office.py`
- `tests/test_build_office.py`

Those changes are not owned by Architect and must not be overwritten, cleaned, staged into the contract commit, or silently absorbed. Orchestration must first identify their durable owner and either commit/isolate them through their existing mission or establish a clean immutable baseline containing them. The v1.1 Build assignment must use an isolated worktree from that resolved baseline.

## Forbidden actions

- Architect implementation of this contract.
- QA modification of reviewed files.
- Build work in `main` or any other office worktree.
- Silent cleanup or loss of the existing dirty changes.
- Release without independent QA approval tied to the exact immutable target fingerprint.
- Force push, history rewrite, destructive cleanup, unbounded retry, secret disclosure, or bypass of a protected branch/provider control.
- Product feature work, roadmap reprioritization, or unrelated refactoring inside this governance mission.

## Required build list

1. Version both human and machine-readable charters to `1.1.0` and keep them semantically equivalent.
2. Update the authority matrix and prose so Orchestration owns gated integration, merge, push, deployment observation, rollback initiation, status publication, and advancement to the next dependency-ready mission.
3. Remove routine final-release gating from Chris while preserving Chris as product-intent owner, observer, intervention authority, and owner of the enumerated human-only blockers.
4. Change office heartbeat contracts so only Orchestration polls continuously; Architect, Build, and QA receive active wake-up signals and submit terminal mission evidence.
5. Specify and implement active Orchestration transitions for contract request, Build wake-up, QA routing, Architect finding disposition, Build repair, release evaluation, deployment observation, rollback/recovery, and next-mission advancement.
6. Preserve existing collision, lease, contract-freeze, immutable-target, scope, retry, review, and evidence gates.
7. Add a fail-closed autonomous release decision that returns a structured blocked reason for every missing gate and cannot mutate Git or deployment state when blocked.
8. Add recorded release evidence containing approved target, integration result, pushed ref, deployment trigger/result, health evidence, rollback ref/result when applicable, and next mission decision.
9. Update CLI/operator documentation and onboarding output to teach the v1.1 topology and authority without relying on chat memory.
10. Add regression and adversarial tests for every acceptance criterion below without performing a real push, deployment, purchase, external communication, or destructive action.

## Acceptance criteria

### AC1 — Versioned semantic parity

Given the completed target, when QA compares `docs/OFFICE-CHARTERS.md`, `jarvis/office_charters.py`, and `office-brief all`, then all report version `1.1.0` and express the same authorities, prohibitions, heartbeat topology, handoffs, and done conditions.

### AC2 — Single active heartbeat

Given a ready assignment for Architect, Build, or QA, when Orchestration processes a mission cycle, then it emits an exact office wake-up signal containing mission ID, assignment ID, contract/digest, scope or immutable target, requested action, and required evidence. No other office charter requires continuous polling.

### AC3 — No passive stale loop

Given an unchanged active mission across configured cycles, when Orchestration evaluates it, then it diagnoses process, lease, command, worktree, target, evidence, and owner state and records a supported retry, reroute, or exact escalation rather than returning the same waiting summary indefinitely.

### AC4 — Separation preserved

Given any mission lifecycle, when duties and evidence are inspected, then no office designed, implemented, independently verified, and approved the same target, and no self-review or waived blocking finding can satisfy the release gate.

### AC5 — Autonomous release gate

Given a frozen contract, clean immutable Build target, exact scope evidence, passing required tests, independent QA approval for the matching fingerprint, and no unresolved Architect revision, when Orchestration evaluates release, then it may create a recorded integration/push/deploy plan and execute the supported release path without asking Chris for routine approval.

### AC6 — Fail-closed release

Given any missing, stale, contradictory, rejected, dirty, out-of-scope, or moving-target evidence, when release is evaluated, then no merge, push, or deployment occurs and the durable result names the exact failed gate and current owner.

### AC7 — Deployment health and rollback

Given an autonomously pushed release, when deployment health fails within the observation window, then Orchestration records the failure, stops roadmap advancement, executes or routes the bounded rollback/recovery policy, verifies the resulting health state, and publishes the outcome.

### AC8 — Roadmap continuation

Given a healthy released mission and an approved dependency-ordered roadmap, when the mission closes, then Orchestration updates visible status and initializes or requests the next contract for the next dependency-ready item without waiting for Chris.

### AC9 — Human-only escalation

Given a blocker, when it matches one of the enumerated human-only categories, then Orchestration asks Chris with the exact missing authority or input. Other operational failures remain owned by the office loop and cannot be escalated merely because an office response is stale.

### AC10 — Preservation and regression

Given the v1.0 control-plane test suite and the pre-existing dirty changes, when Build and QA complete v1.1, then prior contract freezing, collision, lease, retry, scope, immutable-target, and review protections still pass and the pre-existing work is neither lost nor silently bundled.

## Build order

1. Resolve and preserve the existing dirty control-plane changes through Orchestration before provisioning v1.1.
2. Add failing charter-version, authority, heartbeat, separation, and release-gate tests.
3. Update the machine-readable charter registry and onboarding output.
4. Update the human-readable charter and Build Office automation documentation to exact semantic parity.
5. Implement active wake-up/routing and fail-closed autonomous release state transitions through the existing control-plane seams.
6. Implement recorded deployment-health observation and rollback/recovery evidence without invoking real external mutation in tests.
7. Run focused office/control-plane tests, full relevant regression tests, exact changed-file checks, and independent QA.
8. After QA approval, Orchestration uses the existing v1.0 human-gated release path for this governance change. Autonomous authority begins only after v1.1 is canonical and `office-brief all` reports `1.1.0`.

## Required QA evidence

- Exact immutable commit and fingerprint.
- Exact changed-file list restricted to owned paths.
- Human/machine charter semantic comparison.
- `office-brief all` output showing `1.1.0` for every office.
- Focused tests covering AC1–AC10, including blocked release and failed-health rollback simulations.
- Existing office/control-plane regression suite.
- Proof that tests performed no real merge, push, deployment, purchase, external communication, or destructive cleanup.
- Proof that the pre-existing dirty work was preserved or cleanly incorporated through its owning mission.

Missing evidence blocks canonical adoption. No office may self-certify v1.1.

## Initial rollout guardrail

The v1.1 governance implementation itself is released under v1.0 authority. Chris's instruction in this contract is the explicit approval to release the independently approved v1.1 governance target. After that release is healthy and canonical, subsequent approved-roadmap releases follow v1.1 without routine Chris gating.
