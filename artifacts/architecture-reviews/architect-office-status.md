# Architect Office Status

Last updated: 2026-06-27

This is the live Architect Office checklist for JARVIS.

## Jarvis Workstream

### Epic 1. Governance, Review, and Separation of Duties

Status:
- completed

Story:
- establish Architect Office / Build Office / QA separation and canon-aware review flow

Slices completed in implementation order:
- governance scaffold and review loop established
- QA protocol added to canon
- preservation map and master build plan added
- Build Office reporting/review loop established

### Epic 2. Companion Mind

Status:
- active

Story:
- build a truthful, useful default companion conversation path Chris can talk to tomorrow

Slices completed in implementation order:
- default Obsidian conversation behavior fenced so Jarvis does not bluff live Obsidian grounding in the normal companion path
- bounded companion reply quality hardening added for therapist drift, generic chatbot drift, and abstract meaning drift
- live-smoke fallback repair added for drift-sensitive prompts
- expected `8787` runtime path recovered as a trustworthy current-code smoke target
- `8787` launchd conflict documented as an operational truth artifact
- reflective-question repair hardening added so vague reflective questions become practical next-step prompts
- capability-answer grounding polish added so Jarvis answers capability questions in plain human language
- greeting and re-entry opener polish added for warmer, more useful first-turn replies
- generic practical fallback specificity hardening added so unmatched practical asks get concrete forks
- generic non-practical fallback warmth hardening added so unmatched non-practical asks get a warmer truthful handle
- generic empathy / validation repair hardening added so bland sympathy/validation lines get repaired into a real conversational handle
- over-explaining reply trim hardening added so padded replies get trimmed down to the useful core
- decision-support fallback hardening added so common decision-shaped prompts get a concrete first fork instead of a flat fallback
- decision-reply tradeoff grounding hardening added so flat decision replies get repaired into a concrete tradeoff fork
- practical-reply hedge reduction hardening added so hedged practical replies get repaired into a concrete next move
- capacity-pushback hardening added so overloaded planning replies get narrowed into one honest cut-first move
- drafting opener specificity hardening added so drafting asks get a concrete writing handle instead of the generic practical fallback
- fork-follow-up continuity hardening added so short replies to Jarvis's own fork questions continue the prior thread instead of resetting generically
- decision and plan-fork follow-up continuity hardening added so short replies like `energy`, `risk`, `plan`, or `conversation` continue approved fork threads instead of resetting generically

Current Epic 2 status:
- the highest-value tomorrow-conversation hardening slices are largely in place
- the decision-support slice is procedurally approved in isolated review state
- the decision-reply tradeoff slice is procedurally approved in isolated review state
- the practical-reply hedge reduction slice is procedurally approved in isolated review state
- the capacity-pushback slice is procedurally approved in isolated review state
- the drafting opener slice is procedurally approved in isolated review state
- the fork-follow-up continuity slice is procedurally approved in isolated review state
- the decision and plan-fork follow-up continuity slice is procedurally approved in isolated review state
- the latest Epic 2 tomorrow-readiness validation passed regression and guardrail suites but only reached a soft-pass because the expected `8787` runtime path is not currently safe to smoke without mutating local state
- the read-only smoke-mode enabling slice is procedurally approved in isolated review state on the companion-approved reusable baseline
- the earlier reusable review workspace blocker has been resolved by establishing the companion-approved reusable isolated baseline with the matching approved runtime prerequisites
- a new reusable isolated baseline now exists at `/Users/chris/Desktop/CODE/JARVIS-review-companion-approved-baseline` on branch `codex/review-companion-approved-baseline` and is suitable for future isolated Epic 2 review slices
- Epic 2 now has an isolated tomorrow-readiness `pass` on the approved reusable baseline, including live `8787` friend-style posture proof and tracked non-mutation evidence
- remaining work is now smaller polish and coverage decisions, not a missing core conversation spine
- next work should enable safe live runtime proof before more Companion Mind polish slices are added

### Epic 3. Memory Grounding

Status:
- completed

Story:
- give JARVIS bounded, truthful personal grounding without bluffing memory

Planned lanes:
- compact retrieval
- source distinction
- profile versus retrieval separation
- bounded personal context use
- no fake memory or fake Obsidian claims

Current Epic 3 entry status:
- assessment complete
- recommended first slice is structured profile-memory grounding with explicit source labels in the companion context packet
- Obsidian remains out of scope for the default conversation path in this first slice
- the first Epic 3 slice is procedurally approved in slice-only isolated review state
- recommended second slice is memory-transparency answer hardening for direct self-knowledge prompts
- the second Epic 3 slice is procedurally approved in slice-only isolated review state
- recommended third slice is confidence-aware memory wording hardening for uncertain local memory
- the third Epic 3 slice is procedurally approved in slice-only isolated review state
- recommended fourth slice is relevance-gated memory grounding for ordinary companion prompts
- the fourth Epic 3 slice is procedurally approved in slice-only isolated review state
- recommended fifth slice is retrieval-reason transparency for memory relevance challenge prompts
- the fifth Epic 3 slice is procedurally approved in slice-only isolated review state
- recommended sixth slice is mixed-memory tension wording hardening for conflicting or non-unified local context
- the sixth Epic 3 slice is procedurally approved in slice-only isolated review state
- recommended seventh slice is temporal caution wording for potentially stale local memory
- the seventh Epic 3 slice is procedurally approved in slice-only isolated review state
- recommended eighth slice is memory-dispute acknowledgment hardening for user correction prompts
- the eighth Epic 3 slice is procedurally approved in slice-only isolated review state
- recommended ninth slice is memory-dispute follow-up clarification hardening for correction prompts
- the ninth Epic 3 slice is procedurally approved in slice-only isolated review state
- recommended tenth slice is same-turn correction restatement hardening for explicit user-provided replacements
- the tenth Epic 3 slice is procedurally approved in slice-only isolated review state
- recommended eleventh slice is correction-priority follow-through for same-turn corrected help requests
- the eleventh Epic 3 slice is procedurally approved in slice-only isolated review state
- recommended twelfth slice is short-turn correction continuity for corrected follow-up replies
- the twelfth Epic 3 slice is procedurally approved in slice-only isolated review state
- recommended thirteenth slice is memory-overreach reduction for simple present-tense requests
- the thirteenth Epic 3 slice is procedurally approved in slice-only isolated review state
- recommended fourteenth slice is personal-context usefulness tightening for clearly relevant prompts
- the fourteenth Epic 3 slice is procedurally approved in slice-only isolated review state
- recommended fifteenth slice is correction-safe decision support for corrected personal frames
- the fifteenth Epic 3 slice is procedurally approved in slice-only isolated review state
- recommended sixteenth slice is correction-safe drafting support for corrected personal frames
- the sixteenth Epic 3 slice is procedurally approved in slice-only isolated review state
- recommended seventeenth slice is compact memory-summary discipline for personal-grounding replies
- the seventeenth Epic 3 slice is procedurally approved in slice-only isolated review state
- recommended eighteenth slice is Epic 3 final consistency and regression polish
- the eighteenth Epic 3 slice is procedurally approved in slice-only isolated review state
- Epic 3 is ready for bounded closeout review
- Epic 3 closeout package has been delivered from the isolated review target
- Epic 3 is procedurally closed from the isolated review target
- next recommended epic is Epic 4 Hands and Workbench
- recommended first Epic 4 slice is checklist object creation for direct checklist asks

### Epic 4. Hands and Workbench

Status:
- active

Story:
- let conversation produce real useful objects when hands are needed

Planned lanes:
- checklist creation
- plan creation
- draft creation
- research packet creation
- recommendation and evidence surfaces
- workbench object routing
- no empty modal behavior

### Epic 5. Tool Truth and Action Surfaces

Status:
- not started

Story:
- move from advice-only interaction into truthful bounded action

Planned lanes:
- search and retrieval proof
- file and artifact creation proof
- save/open boundaries
- explicit degraded-mode honesty
- execution traces behind capability claims

### Epic 6. Workforce and Delegation

Status:
- not started

Story:
- add subordinate agents only when they produce inspectable work and do not become theater

Planned lanes:
- bounded delegation
- inspectable outputs
- handoff visibility
- ownership and acknowledgment
- agent output review

### Epic 7. Learning Loop

Status:
- not started

Story:
- make JARVIS improve over time without destabilizing truth or trust

Planned lanes:
- outcome capture
- usefulness feedback
- bounded adjustment loops
- regression checks around learned behavior

### Epic 8. Self-Research

Status:
- not started

Story:
- eventually support self-directed research and longer-range assistance under explicit boundaries

Planned lanes:
- scoped research tasks
- evidence packet generation
- source-backed synthesis
- explicit uncertainty handling

### Epic 9. Autonomy

Status:
- not started

Story:
- support bounded self-directed action only after the earlier trust and capability layers are stable

Planned lanes:
- bounded autonomous follow-through
- explicit task initiation boundaries
- approval-aware action planning
- pause, resume, and abort control
- autonomy state visibility
- non-theatrical background execution

## Complete

- [x] Architect Office and Build Office separation clarified in canon
- [x] QA Team protocol added and elevated into canon
- [x] JARVIS preservation map added to active canon
- [x] JARVIS master build plan added with epics, acceptance criteria, Definition of Ready, and Definition of Done
- [x] Build Office thread established in Codex and pinned as `Jarvis Build Office`
- [x] Standing Build Office instruction pattern established for formal reports and evidence-backed delivery
- [x] Epic 1 procedurally approved in isolated review state
- [x] Obsidian default conversation fence procedurally approved in isolated review state
- [x] Bounded companion-mind reply quality hardening procedurally approved in isolated review state
- [x] Companion live-smoke fallback repair and `8787` operational truth artifact procedurally approved in isolated review state
- [x] Reflective-question repair hardening procedurally approved in isolated review state
- [x] Capability answer grounding polish procedurally approved in isolated review state
- [x] Greeting and re-entry opener polish procedurally approved in isolated review state
- [x] Generic practical fallback specificity hardening procedurally approved in isolated review state
- [x] Generic non-practical fallback warmth hardening procedurally approved in isolated review state
- [x] Generic empathy / validation repair hardening procedurally approved in isolated review state
- [x] Over-explaining reply trim hardening procedurally approved in isolated review state
- [x] Fork-follow-up continuity hardening procedurally approved in isolated review state
- [x] Decision and plan-fork follow-up continuity hardening procedurally approved in isolated review state

## Active

- [x] Produce the baseline Architecture Review for current JARVIS state
- [x] Create the first-pass fact-base map of existing JARVIS capability
- [ ] Reconcile canon with current runtime truth where drift exists
- [x] Land authoritative `docs/CHRIS-INTENT-CANON.md` from canon-owner text
- [x] Assess the Obsidian canon/runtime mismatch without changing product behavior
- [x] Decide the Obsidian path: fence current runtime behavior behind non-default conditions
- [x] Review Build Office fence/disable implementation
- [x] Re-check default conversational truth posture after the Obsidian fence lands
- [x] Require clean isolation of the Obsidian fence slice for procedural approval
- [x] Define the next approved implementation slice after governance/canon cleanup
- [x] Direct the next bounded companion-mind slice
- [x] Review the bounded companion-mind implementation proposal
- [x] Require clean isolation of the bounded companion-mind slice for procedural approval
- [x] Decide whether tomorrow-readiness now requires QA or a live runtime smoke
- [x] Run a bounded live runtime smoke for tomorrow-conversation readiness
- [x] Restore trustworthy default local runtime behavior on the expected `8787` path
- [x] Identify the next smallest approved Companion Mind slice after the current tomorrow-readiness approvals
- [x] Direct the next bounded Companion Mind implementation slice
- [x] Require clean isolated review state for the reflective-question repair slice before formal approval
- [x] Identify the next smallest approved Companion Mind slice after reflective-question repair approval
- [x] Direct the next bounded Companion Mind implementation slice after reflective-question repair approval
- [x] Require clean isolated review state for the capability-answer grounding slice before formal approval
- [x] Identify the next smallest approved Companion Mind slice after capability-answer grounding approval
- [x] Direct the next bounded Companion Mind implementation slice after capability-answer grounding approval
- [x] Require clean isolated review state for the greeting and re-entry opener slice before formal approval
- [x] Identify the next smallest approved Companion Mind slice after greeting and re-entry opener approval
- [x] Direct the next bounded Companion Mind implementation slice after greeting and re-entry opener approval
- [x] Require clean isolated review state for the generic practical fallback slice before formal approval
- [x] Identify the next smallest approved Companion Mind slice after generic practical fallback approval
- [x] Direct the next bounded Companion Mind implementation slice after generic practical fallback approval
- [x] Require clean isolated review state for the generic non-practical fallback slice before formal approval
- [x] Identify the next smallest approved Companion Mind slice after generic non-practical fallback approval
- [x] Direct the next bounded Companion Mind implementation slice after generic non-practical fallback approval
- [ ] Require clean isolated review state for the over-explaining trim slice before formal approval
- [x] Require clean isolated review state for the over-explaining trim slice before formal approval
- [x] Identify the next smallest approved Companion Mind slice after over-explaining trim approval
- [x] Direct the next bounded Companion Mind implementation slice after over-explaining trim approval
- [ ] Require clean isolated review state for the decision-support fallback slice before formal approval
- [x] Require clean isolated review state for the decision-support fallback slice before formal approval
- [x] Identify the next smallest approved Companion Mind slice after decision-support fallback approval
- [x] Direct the next bounded Companion Mind implementation slice after decision-support fallback approval
- [ ] Require clean isolated review state for the decision-reply tradeoff grounding slice before formal approval
- [x] Require clean isolated review state for the decision-reply tradeoff grounding slice before formal approval
- [x] Identify the next smallest approved Companion Mind slice after decision-reply tradeoff grounding approval
- [x] Direct the next bounded Companion Mind implementation slice after decision-reply tradeoff grounding approval
- [ ] Require clean isolated review state for the practical-reply hedge reduction slice before formal approval
- [x] Require clean isolated review state for the practical-reply hedge reduction slice before formal approval
- [x] Identify the next smallest approved Companion Mind slice after practical-reply hedge reduction approval
- [x] Direct the next bounded Companion Mind implementation slice after practical-reply hedge reduction approval
- [ ] Require clean isolated review state for the capacity-pushback slice before formal approval
- [x] Require clean isolated review state for the capacity-pushback slice before formal approval
- [x] Identify the next smallest approved Companion Mind slice after capacity-pushback approval
- [x] Direct the next bounded Companion Mind implementation slice after capacity-pushback approval
- [x] Require clean isolated review state for the drafting opener specificity slice before formal approval
- [x] Identify the next smallest approved Companion Mind slice after drafting opener specificity approval
- [x] Direct the next bounded Companion Mind implementation slice after drafting opener specificity approval
- [x] Review the fork-follow-up continuity implementation proposal
- [x] Require clean isolated review state for the fork-follow-up continuity slice before formal approval
- [x] Identify the next smallest approved Companion Mind slice after fork-follow-up continuity approval
- [x] Direct the next bounded Companion Mind implementation slice after fork-follow-up continuity approval
- [x] Review the decision and plan-fork follow-up continuity implementation proposal
- [x] Require clean isolated review state for the decision and plan-fork follow-up continuity slice before formal approval
- [x] Identify the next highest-value Epic 2 step after decision and plan-fork follow-up continuity approval
- [x] Direct the next bounded Epic 2 validation pass after decision and plan-fork follow-up continuity approval
- [x] Review the Epic 2 tomorrow-readiness regression and live-smoke report
- [x] Identify the next bounded enabling slice after the Epic 2 soft-pass verdict
- [x] Direct the next bounded enabling slice after the Epic 2 soft-pass verdict
- [x] Review the read-only runtime smoke mode implementation report
- [x] Require clean isolated review state for the read-only runtime smoke mode slice before formal approval
- [x] Review the isolated read-only smoke-mode re-delivery report
- [x] Identify the next bounded review-infrastructure step after the isolated smoke-mode blocker
- [x] Direct the next bounded review-infrastructure assignment after the isolated smoke-mode blocker
- [x] Review the companion-approved reusable isolated baseline report
- [x] Identify the next bounded procedural approval step after the companion-approved reusable baseline was established
- [x] Direct the next bounded procedural approval assignment after the companion-approved reusable baseline was established
- [x] Identify the next bounded Epic 2 validation step after isolated smoke-mode approval
- [x] Direct the next bounded Epic 2 validation step after isolated smoke-mode approval
- [x] Review the isolated Epic 2 tomorrow-readiness verdict
- [x] Identify the next bounded post-Epic-2 step after isolated tomorrow-readiness pass
- [x] Direct the next bounded post-Epic-2 assignment after isolated tomorrow-readiness pass
- [x] Review the Epic 3 entry assessment and first-slice recommendation
- [x] Identify the first bounded Epic 3 implementation slice
- [x] Direct the first bounded Epic 3 implementation slice
- [x] Review the first Epic 3 implementation report
- [x] Require clean isolated review state for the first Epic 3 slice before formal approval
- [x] Identify the next bounded Epic 3 planning step after first-slice approval
- [x] Direct the next bounded Epic 3 planning step after first-slice approval
- [x] Review the second Epic 3 slice recommendation
- [x] Identify the second bounded Epic 3 implementation slice
- [x] Direct the second bounded Epic 3 implementation slice
- [x] Review the second Epic 3 implementation report
- [x] Identify the next bounded Epic 3 planning step after second-slice approval
- [x] Direct the next bounded Epic 3 planning step after second-slice approval
- [x] Review the third Epic 3 slice recommendation
- [x] Identify the third bounded Epic 3 implementation slice
- [x] Direct the third bounded Epic 3 implementation slice
- [x] Review the third Epic 3 implementation report
- [x] Identify the next bounded Epic 3 planning step after third-slice approval
- [x] Direct the next bounded Epic 3 planning step after third-slice approval
- [x] Review the fourth Epic 3 slice recommendation
- [x] Identify the fourth bounded Epic 3 implementation slice
- [x] Direct the fourth bounded Epic 3 implementation slice
- [x] Review the fourth Epic 3 implementation report
- [x] Identify the next bounded Epic 3 planning step after fourth-slice approval
- [x] Direct the next bounded Epic 3 planning step after fourth-slice approval
- [x] Review the fifth Epic 3 slice recommendation
- [x] Identify the fifth bounded Epic 3 implementation slice
- [x] Direct the fifth bounded Epic 3 implementation slice
- [x] Review the fifth Epic 3 implementation report
- [x] Identify the next bounded Epic 3 planning step after fifth-slice approval
- [x] Direct the next bounded Epic 3 planning step after fifth-slice approval
- [x] Review the sixth Epic 3 slice recommendation
- [x] Identify the sixth bounded Epic 3 implementation slice
- [x] Direct the sixth bounded Epic 3 implementation slice
- [x] Review the sixth Epic 3 implementation report
- [x] Identify the next bounded Epic 3 planning step after sixth-slice approval
- [x] Direct the next bounded Epic 3 planning step after sixth-slice approval
- [x] Review the seventh Epic 3 slice recommendation
- [x] Identify the seventh bounded Epic 3 implementation slice
- [x] Direct the seventh bounded Epic 3 implementation slice
- [x] Review the seventh Epic 3 implementation report
- [x] Identify the next bounded Epic 3 planning step after seventh-slice approval
- [x] Direct the next bounded Epic 3 planning step after seventh-slice approval
- [x] Review the eighth Epic 3 slice recommendation
- [x] Identify the eighth bounded Epic 3 implementation slice
- [x] Direct the eighth bounded Epic 3 implementation slice
- [x] Request the Build Office isolated review package for the eighth Epic 3 slice
- [x] Review the eighth Epic 3 isolated implementation report
- [x] Procedurally approve the eighth Epic 3 slice in isolated review state
- [x] Identify the next bounded Epic 3 planning step after eighth-slice approval
- [x] Direct the next bounded Epic 3 planning step after eighth-slice approval
- [x] Review the ninth Epic 3 isolated implementation report
- [x] Procedurally approve the ninth Epic 3 slice in isolated review state
- [x] Identify the next bounded Epic 3 planning step after ninth-slice approval
- [x] Direct the next bounded Epic 3 planning step after ninth-slice approval
- [x] Review the tenth Epic 3 isolated implementation report
- [x] Procedurally approve the tenth Epic 3 slice in isolated review state
- [x] Identify the next bounded Epic 3 planning step after tenth-slice approval
- [x] Direct the next bounded Epic 3 planning step after tenth-slice approval
- [x] Review the eleventh Epic 3 isolated implementation report
- [x] Procedurally approve the eleventh Epic 3 slice in isolated review state
- [x] Identify the next bounded Epic 3 planning step after eleventh-slice approval
- [x] Direct the next bounded Epic 3 planning step after eleventh-slice approval
- [x] Review the twelfth Epic 3 isolated implementation report
- [x] Procedurally approve the twelfth Epic 3 slice in isolated review state
- [x] Identify the next bounded Epic 3 planning step after twelfth-slice approval
- [x] Direct the next bounded Epic 3 planning step after twelfth-slice approval
- [x] Review the thirteenth Epic 3 isolated implementation report
- [x] Procedurally approve the thirteenth Epic 3 slice in isolated review state
- [x] Identify the next bounded Epic 3 planning step after thirteenth-slice approval
- [x] Direct the next bounded Epic 3 planning step after thirteenth-slice approval
- [x] Review the fourteenth Epic 3 isolated implementation report
- [x] Procedurally approve the fourteenth Epic 3 slice in isolated review state
- [x] Identify the next bounded Epic 3 planning step after fourteenth-slice approval
- [x] Direct the next bounded Epic 3 planning step after fourteenth-slice approval
- [x] Review the fifteenth Epic 3 isolated implementation report
- [x] Procedurally approve the fifteenth Epic 3 slice in isolated review state
- [x] Identify the next bounded Epic 3 planning step after fifteenth-slice approval
- [x] Direct the next bounded Epic 3 planning step after fifteenth-slice approval
- [x] Review the sixteenth Epic 3 isolated implementation report
- [x] Procedurally approve the sixteenth Epic 3 slice in isolated review state
- [x] Identify the next bounded Epic 3 planning step after sixteenth-slice approval
- [x] Direct the next bounded Epic 3 planning step after sixteenth-slice approval
- [x] Review the seventeenth Epic 3 isolated implementation report
- [x] Procedurally approve the seventeenth Epic 3 slice in isolated review state
- [x] Identify the next bounded Epic 3 planning step after seventeenth-slice approval
- [x] Direct the next bounded Epic 3 planning step after seventeenth-slice approval
- [x] Review the eighteenth Epic 3 isolated implementation report
- [x] Procedurally approve the eighteenth Epic 3 slice in isolated review state
- [x] Identify the next bounded Epic 3 planning step after eighteenth-slice approval
- [x] Direct the next bounded Epic 3 planning step after eighteenth-slice approval
- [x] Review the Epic 3 closeout package from the isolated review target
- [x] Procedurally close Epic 3 from the isolated review target
- [x] Identify the next bounded post-Epic-3 planning step
- [x] Direct the first bounded Epic 4 implementation slice
- [ ] Require clean isolated review state for the generic empathy / validation repair slice before formal approval
- [x] Require clean isolated review state for the generic empathy / validation repair slice before formal approval

## Upcoming

- [ ] Require QA verification before approval on future higher-risk slices
- [x] Decide whether to require an isolated review state before formal approval of the recent main-repo slices
- [x] Require clean isolated review state for the recent main-repo companion/runtime slices before formal approval

## Current Focus

Architect Office is working the governance loop first so future JARVIS work can be directed, tested, and approved cleanly instead of managed ad hoc.

Immediate active review lane:
- Epic 3 slice 8 approved in isolated review state at `/Users/chris/Desktop/CODE/JARVIS-review-epic3-memory-grounding-clean`
- Epic 3 slice 9 approved in isolated review state at `/Users/chris/Desktop/CODE/JARVIS-review-epic3-memory-grounding-clean`
- Epic 3 slice 10 approved in isolated review state at `/Users/chris/Desktop/CODE/JARVIS-review-epic3-memory-grounding-clean`
- Epic 3 slice 11 approved in isolated review state at `/Users/chris/Desktop/CODE/JARVIS-review-epic3-memory-grounding-clean`
- Epic 3 slice 12 approved in isolated review state at `/Users/chris/Desktop/CODE/JARVIS-review-epic3-memory-grounding-clean`
- Epic 3 slice 13 approved in isolated review state at `/Users/chris/Desktop/CODE/JARVIS-review-epic3-memory-grounding-clean`
- Epic 3 slice 14 approved in isolated review state at `/Users/chris/Desktop/CODE/JARVIS-review-epic3-memory-grounding-clean`
- Epic 3 slice 15 approved in isolated review state at `/Users/chris/Desktop/CODE/JARVIS-review-epic3-memory-grounding-clean`
- Epic 3 slice 16 approved in isolated review state at `/Users/chris/Desktop/CODE/JARVIS-review-epic3-memory-grounding-clean`
- Epic 3 slice 17 approved in isolated review state at `/Users/chris/Desktop/CODE/JARVIS-review-epic3-memory-grounding-clean`
- Epic 3 slice 18 approved in isolated review state at `/Users/chris/Desktop/CODE/JARVIS-review-epic3-memory-grounding-clean`
- Epic 3 closeout package delivered from `/Users/chris/Desktop/CODE/JARVIS-review-epic3-memory-grounding-clean`
- Epic 3 procedurally closed from `/Users/chris/Desktop/CODE/JARVIS-review-epic3-memory-grounding-clean`
- next active Build Office assignment is Epic 4 slice 1: `checklist object creation for direct checklist asks`

Process improvement:
- the office protocols now default to isolated-first execution when the main repo is mixed
- preferred isolation order is now:
  - clean sibling `git worktree` first
  - reusable named clean workspace second
  - fresh clone only when necessary
- the goal is to avoid the recurring two-pass pattern where Build Office implements in mixed state and then has to recreate the same slice in a clean review target

Current epic:
- Post-Epic-1 Architect Office review and fact-base mapping

Current Epic 1 status:
- procedurally approved in isolated review state at `/Users/chris/Desktop/JARVIS-epic1-governance-clone`
- isolated Architect Office tests passed
- isolated review command returned `Approve`
- note: the isolated review still flags missing Chris canon in the review path, which affects product-fit evaluation but does not block Epic 1 process approval

Current baseline review status:
- baseline review artifact created at `/Users/chris/Desktop/CODE/JARVIS/artifacts/architecture-reviews/jarvis-baseline-architecture-review-2026-06-27.md`
- fact-base map created at `/Users/chris/Desktop/CODE/JARVIS/artifacts/architecture-reviews/jarvis-fact-base-map-2026-06-27.md`
- highest-priority repo findings:
  - `docs/CHRIS-INTENT-CANON.md` has now been landed from canon-owner text and elevated as the highest-priority product-intent source
  - Obsidian canon/runtime mismatch is now confirmed against authoritative owner text
  - main repo remains a mixed worktree

Current Obsidian assessment status:
- Build Office mismatch assessment received
- mismatch is clear: current code implements bounded local retrieval while authoritative canon still says live Obsidian retrieval is not yet integrated into conversation and belongs to Phase 3
- Architect Office chose the fence path so default behavior can match canon without broad rollback churn
- Build Office implemented the bounded fence/disable slice
- narrow validation passed in the main repo
- isolated review target `/Users/chris/Desktop/JARVIS-obsidian-fence-review` passed bounded validation cleanly
- procedural approval granted for the bounded fence slice

Next implementation priority:
- define the smallest companion-mind hardening slice that makes tomorrow's conversational experience more helpful, natural, and trustworthy
- Build Office assessment recommends a bounded companion reply quality gate and repair pass as the next smallest high-value slice
- Build Office implemented that bounded reply quality gate and validated it in the main repo
- isolated review target `/Users/chris/Desktop/JARVIS-companion-mind-review` passed bounded validation cleanly
- procedural approval granted for the bounded companion-mind slice
- Architect Office chose a bounded live runtime smoke as the next best readiness check for tomorrow's conversational usefulness
- Build Office completed that live smoke and found a split result:
  - fresh current code on `8788` now gives acceptable friend-like default conversation posture after one small local fallback fix
  - expected local path `8787` is still not trustworthy because it is being supervised/relaunched into drifted startup state
  - `openai_available` was `false` during the smoke, so the validated live posture was the fallback path rather than an OpenAI-backed path
  - Architect Office therefore treats tomorrow-readiness as a fail on operational runtime trust, not on the bounded fallback conversation quality itself
- Build Office then completed the bounded `8787` runtime-trust slice:
  - exact cause was external user-level `launchd` supervision, not an in-repo runtime mystery
  - two LaunchAgents were involved:
    - `com.chris.jarvis.dashboard` from the active checkout
    - `com.jarvis.runtime` from a stale competing checkout at `/Users/chris/Desktop/JARVIS`
  - the competing stale checkout path was unloaded
  - the remaining dashboard LaunchAgent was also unloaded when it still did not produce a trustworthy smoke target
  - the current repo was then direct-launched on `8787`
  - `/health` and `/api/gateway/status` passed on `8787`
  - required prompt smoke on `8787` passed
  - Build Office therefore reported tomorrow-readiness on the expected path as `pass`

Current runtime blocker:
- no active blocker remains on the expected local runtime path while the direct current-code `8787` launch stays in place
- residual operational risk remains:
  - the prior LaunchAgents were unloaded rather than repo-fixed
  - if those LaunchAgents are reloaded later without cleanup, the same trust problem can recur

Operational truth capture:
- Build Office added the operator artifact at `/Users/chris/Desktop/CODE/JARVIS/artifacts/architecture-reviews/jarvis-8787-launchd-conflict-2026-06-27.md`
- the artifact records:
  - exact conflicting LaunchAgents
  - competing checkout paths
  - observed `8787` drift/failure mode
  - evidence that the issue was external `launchd` supervision
  - bounded recovery steps
  - recurrence risk
  - operator verification steps before future live smokes
- Build Office marked the artifact slice as not procedurally isolated because it still lives in the mixed main-repo worktree

Architect Office decision:
- formal approval will continue to require isolated review state for recent bounded slices that were implemented in the mixed main-repo worktree
- rationale:
  - earlier bounded approvals already used isolated review targets as the clean procedural standard
  - the current main repo still contains unrelated runtime, canon, test, data, and artifact changes in view
  - the companion-mind live smoke fix and the `8787` operational truth artifact are both reviewable, but not yet procedurally clean in the main worktree
- next Build Office instruction should therefore produce a minimal isolated review target for:
  - the bounded companion-mind live-smoke fix
  - the `8787` launchd conflict artifact
- Build Office completed that isolation pass:
  - isolated target path: `/Users/chris/Desktop/CODE/JARVIS-review-companion-8787`
  - isolated branch: `phase-1-companion-spine-review-companion-8787`
  - isolated files:
    - `jarvis/companion_spine.py`
    - `tests/test_companion_spine.py`
    - `artifacts/architecture-reviews/jarvis-8787-launchd-conflict-2026-06-27.md`
  - narrow validation passed in the isolated target
  - Build Office marked the isolated target `Ready for Architecture Review: yes`
- Architect Office review result for `/Users/chris/Desktop/CODE/JARVIS-review-companion-8787`:
  - isolated scope matches the requested bounded slice only
  - isolated `jarvis/companion_spine.py` and `tests/test_companion_spine.py` match the current main-repo bounded implementation exactly
  - `artifacts/architecture-reviews/jarvis-8787-launchd-conflict-2026-06-27.md` is present and captures the required operator truth clearly
  - procedural approval granted for the isolated companion/runtime review slice
- next Architect Office move:
  - choose the next smallest Companion Mind slice that improves tomorrow's default conversation usefulness without broadening into Memory, Hands, or UI work
- Build Office assessment result:
  - 4 candidate next slices were assessed
  - recommended next slice: `Reflective-question repair hardening`
  - rationale:
    - current repair logic can let vague reflective questions pass untouched because any `?` currently counts as a practical handle
    - this is a real weakness in ordinary conversation quality
    - it stays local to the existing approved companion repair seam instead of broadening scope
  - likely files:
    - `jarvis/companion_spine.py`
    - `tests/test_companion_spine.py`
- Build Office implementation result:
  - `Reflective-question repair hardening` implemented in the default Companion Mind repair seam
  - targeted tests passed: `python3 -m pytest -q tests/test_companion_spine.py`
  - runtime smoke was intentionally skipped because `/api/respond` would mutate local conversation/log state in the mixed worktree
  - Build Office marked the slice `Ready for Architecture Review: no` because it still lives only in the mixed main-repo worktree
- Build Office isolation result:
  - isolated target path: `/Users/chris/Desktop/CODE/JARVIS-review-reflective-repair`
  - isolated branch: `phase-1-companion-spine-review-reflective-repair`
  - isolated files:
    - `jarvis/companion_spine.py`
    - `tests/test_companion_spine.py`
  - targeted isolated validation passed
  - Build Office marked the isolated target `Ready for Architecture Review: yes`
- Architect Office review result for `/Users/chris/Desktop/CODE/JARVIS-review-reflective-repair`:
  - isolated scope matches the requested reflective-question slice only
  - isolated `jarvis/companion_spine.py` and `tests/test_companion_spine.py` match the current bounded main-repo implementation exactly
  - procedural approval granted for the reflective-question repair slice
- Build Office assessment result after reflective-question repair approval:
  - 4 candidate next slices were assessed
  - recommended next slice: `Capability answer grounding polish`
  - rationale:
    - current capability answers are truthful but still expose raw internal labels in a way that sounds more like an internal feature list than a smart friend with tools
    - this is a high-signal trust moment because users explicitly ask what Jarvis can actually do
    - the slice stays local to one approved companion seam and is smaller than broader tone or fallback work
  - likely files:
    - `jarvis/companion_spine.py`
    - `tests/test_companion_spine.py`
- Build Office implementation result:
  - `Capability answer grounding polish` implemented in the default Companion Mind path
  - full companion test file passed: `python3 -m pytest -q tests/test_companion_spine.py`
  - safe in-process companion-path smoke passed for:
    - `What can you actually do right now?`
    - `Hey Jarvis`
    - `Help me think through vacation`
  - Build Office marked the slice `Ready for Architecture Review: no` because it still lives only in the mixed main-repo worktree
- Build Office isolation result:
  - isolated target path: `/Users/chris/Desktop/CODE/JARVIS-review-capability-grounding`
  - isolated branch: `phase-1-companion-spine-review-capability-grounding`
  - isolated files:
    - `jarvis/companion_spine.py`
    - `tests/test_companion_spine.py`
  - targeted isolated validation passed
  - Build Office marked the isolated target `Ready for Architecture Review: yes`
- Architect Office review result for `/Users/chris/Desktop/CODE/JARVIS-review-capability-grounding`:
  - isolated scope matches the requested capability-answer slice only
  - isolated `jarvis/companion_spine.py` and `tests/test_companion_spine.py` match the current bounded main-repo implementation exactly
  - procedural approval granted for the capability-answer grounding slice
- Build Office assessment result after capability-answer grounding approval:
  - 4 candidate next slices were assessed
  - recommended next slice: `Greeting and re-entry opener polish`
  - rationale:
    - short greetings and proof-of-life prompts are still thin and mechanically serviceable rather than especially warm or useful
    - this is a high-frequency tomorrow-readiness moment
    - the slice stays extremely local to the existing fallback seam and is smaller than broader fallback or fork expansion
  - likely files:
    - `jarvis/companion_spine.py`
    - `tests/test_companion_spine.py`
- Build Office implementation result:
  - `Greeting and re-entry opener polish` implemented in the default Companion Mind path
  - full companion test file passed: `python3 -m pytest -q tests/test_companion_spine.py`
  - safe in-process companion-path smoke passed for:
    - `Hey Jarvis`
    - `Is Jarvis working?`
    - `Help me think through vacation`
  - Build Office marked the slice `Ready for Architecture Review: no` because it still lives only in the mixed main-repo worktree
- Build Office isolation result:
  - isolated target path: `/Users/chris/Desktop/CODE/JARVIS-review-greeting-openers`
  - isolated branch: `phase-1-companion-spine-review-greeting-openers`
  - isolated files:
    - `jarvis/companion_spine.py`
    - `tests/test_companion_spine.py`
  - targeted isolated validation passed
  - Build Office marked the isolated target `Ready for Architecture Review: yes`
- Architect Office review result for `/Users/chris/Desktop/CODE/JARVIS-review-greeting-openers`:
  - isolated scope matches the requested greeting/re-entry opener slice only
  - isolated `jarvis/companion_spine.py` and `tests/test_companion_spine.py` match the current bounded main-repo implementation exactly
  - procedural approval granted for the greeting and re-entry opener slice
- Build Office assessment result after greeting and re-entry opener approval:
  - 4 candidate next slices were assessed
  - recommended next slice: `Generic practical fallback specificity hardening`
  - rationale:
    - unmatched practical requests still fall into an operational catch-all that sounds more like service-state messaging than a smart friend helping with a real-life problem
    - this improves a wider set of ordinary conversations than another micro-polish slice
    - the slice stays local to the same approved fallback seam and is safer than adding multiple topic-specific forks first
  - likely files:
    - `jarvis/companion_spine.py`
    - `tests/test_companion_spine.py`
- Build Office implementation result:
  - `Generic practical fallback specificity hardening` implemented in the default Companion Mind path
  - full companion test file passed: `python3 -m pytest -q tests/test_companion_spine.py`
  - safe in-process companion-path smoke passed for:
    - `Help me think through a hard conversation with my brother`
    - `I need to get my week under control`
    - `Help me think through vacation`
  - Build Office marked the slice `Ready for Architecture Review: no` because it still lives only in the mixed main-repo worktree
- Build Office isolation result:
  - isolated target path: `/Users/chris/Desktop/CODE/JARVIS-review-generic-practical-fallback`
  - isolated branch: `phase-1-companion-spine-review-generic-practical-fallback`
  - isolated files:
    - `jarvis/companion_spine.py`
    - `tests/test_companion_spine.py`
  - targeted isolated validation passed
  - Build Office marked the isolated target `Ready for Architecture Review: yes`
- Architect Office review result for `/Users/chris/Desktop/CODE/JARVIS-review-generic-practical-fallback`:
  - isolated scope matches the requested generic practical fallback slice only
  - isolated `jarvis/companion_spine.py` and `tests/test_companion_spine.py` match the current bounded main-repo implementation exactly
  - procedural approval granted for the generic practical fallback slice
- Build Office assessment result after generic practical fallback approval:
  - 4 candidate next slices were assessed
  - recommended next slice: `Generic non-practical fallback warmth hardening`
  - rationale:
    - unmatched non-practical ordinary conversation still falls through to cold service-state messaging
    - practical fallbacks are now in better shape, so this is the weakest visible part of the default path
    - the slice stays inside the same approved fallback seam and is safer than adding more topic-specific forks first
  - likely files:
    - `jarvis/companion_spine.py`
    - `tests/test_companion_spine.py`
- Build Office implementation result:
  - `Generic non-practical fallback warmth hardening` implemented in the default Companion Mind path
  - full companion test file passed: `python3 -m pytest -q tests/test_companion_spine.py`
  - safe in-process companion-path smoke passed for:
    - `I've had a weird day`
    - `I'm kind of off today`
    - `Help me think through vacation`
  - Build Office marked the slice `Ready for Architecture Review: no` because it still lives only in the mixed main-repo worktree
- Build Office isolation result:
  - isolated target path: `/Users/chris/Desktop/CODE/JARVIS-review-non-practical-fallback`
  - isolated branch: `phase-1-companion-spine-review-non-practical-fallback`
  - isolated files:
    - `jarvis/companion_spine.py`
    - `tests/test_companion_spine.py`
  - targeted isolated validation passed
  - Build Office marked the isolated target `Ready for Architecture Review: yes`
- Architect Office review result for `/Users/chris/Desktop/CODE/JARVIS-review-non-practical-fallback`:
  - isolated scope matches the requested generic non-practical fallback slice only
  - isolated `jarvis/companion_spine.py` and `tests/test_companion_spine.py` match the current bounded main-repo implementation exactly
  - procedural approval granted for the generic non-practical fallback slice
- Build Office assessment result after generic non-practical fallback approval:
  - 4 candidate next slices were assessed
  - recommended next slice: `Generic empathy / validation repair hardening`
  - rationale:
    - bland sympathy or thin validation can still pass if it avoids the current explicit therapist/chatbot patterns
    - this is now one of the weakest visible parts of ordinary conversation quality
    - the slice stays inside the same approved reply-repair seam and is safer than broader fork or architecture work
  - likely files:
    - `jarvis/companion_spine.py`
    - `tests/test_companion_spine.py`
- Build Office implementation result:
  - `Generic empathy / validation repair hardening` implemented in the default Companion Mind path
  - full companion test file passed: `python3 -m pytest -q tests/test_companion_spine.py`
  - safe in-process companion-path smoke passed for:
    - `I've had a weird day`
    - `I'm kind of off today`
    - `Help me think through vacation`
  - Build Office marked the slice `Ready for Architecture Review: no` because it still lives only in the mixed main-repo worktree
- Build Office isolation result:
  - isolated target path: `/Users/chris/Desktop/CODE/JARVIS-review-empathy-repair`
  - isolated branch: `phase-1-companion-spine-review-empathy-repair`
  - isolated files:
    - `jarvis/companion_spine.py`
    - `tests/test_companion_spine.py`
  - targeted isolated validation passed
  - Build Office marked the isolated target `Ready for Architecture Review: yes`
- Architect Office review result for `/Users/chris/Desktop/CODE/JARVIS-review-empathy-repair`:
  - isolated scope matches the requested empathy / validation repair slice only
  - isolated `jarvis/companion_spine.py` and `tests/test_companion_spine.py` match the current bounded main-repo implementation exactly
  - procedural approval granted for the generic empathy / validation repair slice
- Build Office assessment result after generic empathy / validation repair approval:
  - 4 candidate next slices were assessed
  - recommended next slice: `Over-explaining reply trim hardening`
  - rationale:
    - model replies can still be long, soft, and padded even when they technically contain a useful handle
    - the code already forbids over-explaining, but there is not yet a matching enforcement pass
    - the slice stays inside the same approved reply-repair seam and improves ordinary conversation quality across many prompts
  - likely files:
    - `jarvis/companion_spine.py`
    - `tests/test_companion_spine.py`
- Build Office implementation result:
  - `Over-explaining reply trim hardening` implemented in the default Companion Mind path
  - full companion test file passed: `python3 -m pytest -q tests/test_companion_spine.py`
  - safe in-process companion-path smoke passed for:
    - `I've had a weird day`
    - `I need to get my week under control`
    - `Help me think through vacation`
  - Build Office marked the slice `Ready for Architecture Review: no` because it still lives only in the mixed main-repo worktree
- Build Office isolation result:
  - isolated target path: `/Users/chris/Desktop/CODE/JARVIS-review-overexplaining-trim`
  - isolated branch: `phase-1-companion-spine-review-overexplaining-trim`
  - isolated files:
    - `jarvis/companion_spine.py`
    - `tests/test_companion_spine.py`
  - targeted isolated validation passed
  - Build Office marked the isolated target `Ready for Architecture Review: yes`
- Architect Office review result for `/Users/chris/Desktop/CODE/JARVIS-review-overexplaining-trim`:
  - isolated scope matches the requested over-explaining trim slice only
  - isolated `jarvis/companion_spine.py` and `tests/test_companion_spine.py` match the current bounded main-repo implementation exactly
  - procedural approval granted for the over-explaining trim slice

Near-term product priority:
- after the current governance/canon cleanup, the next approved slices should optimize for a conversational, helpful friend Chris can talk to tomorrow

Current Build Office thread:
- `Jarvis Build Office`

Decision rule:
- no Build Office work is complete until Architect Office review exists
