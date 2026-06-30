# Post-Epic 9 Slice 125: Fresh Live-Use Weakness Reassessment

## Goal
- Reassess fresh current repo truth after the appointment-based planning repair.
- Identify the single highest-value remaining first-turn chief-of-staff or companion usefulness defect.
- Keep this slice recommendation-first. No code or test changes were made.

## Exact Code Seams Inspected
- `jarvis/companion_spine.py:321` `generate_companion_fallback`
- `jarvis/companion_spine.py:553` `_request_needs_practical_handle`
- `jarvis/companion_spine.py:678` `_is_follow_up_request`
- `jarvis/companion_spine.py:695` `_is_presentation_or_proposal_prep_request`
- `jarvis/companion_spine.py:726` `_is_agenda_request`
- `jarvis/companion_spine.py:738` `_is_tomorrow_planning_request`
- `jarvis/companion_spine.py:766` `_is_constraints_scheduling_request`
- `jarvis/companion_spine.py:1282` `_generic_practical_fallback_reply`

## Exact Prompts / Routes Inspected

### Candidate remaining-miss family
- `I need help mapping out tomorrow.`
- `Help me map out tomorrow.`
- `I need help mapping out tomorrow morning.`
- `I need help mapping out tomorrow afternoon.`
- `I need help sketching out tomorrow.`
- `I need help laying out tomorrow.`

### Adjacent already-correct tomorrow-planning controls
- `I need help with tomorrow's plan.`
- `I need help planning tomorrow.`
- `I need help with tomorrow afternoon.`
- `I need help with tomorrow evening.`

### Nearby lower-priority comparison probes
- `I need help with this outline.`
- `I need help with this summary.`
- `I need help with this recap.`
- `I need help with this proposal outline.`
- `I need help with this presentation outline.`
- `I need help with this meeting outline.`
- `I need help with this briefing outline.`
- `I need help with this follow-up note.`

### Preserved nearby concrete controls
- `I need help planning around two appointments.`
- `I need help around my appointments tomorrow.`
- `I need help with my one-on-one.`
- `I need help with my follow-up.`
- `I need help with this briefing.`
- `I need help with my email.`
- `I need help with my calendar for tomorrow.`
- `I need help with my schedule for tomorrow.`

## Strongest Remaining Defect Found
- The strongest remaining first-turn usefulness defect is the narrow tomorrow-mapping family:
  - `I need help mapping out tomorrow.`
  - `Help me map out tomorrow.`
  - `I need help mapping out tomorrow morning.`
  - `I need help mapping out tomorrow afternoon.`
- Current repo-truth behavior for that family is:
  - `Let's make it concrete. Is this mostly a decision, a conversation, or a plan you need to sort out first?`
- That is weaker than the already-approved nearby tomorrow-planning fork:
  - `Good. For tomorrow, what actually has to happen, what is fixed, and what can slip?`

## Why This Is Higher Value Than Adjacent Options
- This family is semantically the same live-use intent as already-supported tomorrow-planning asks like `planning tomorrow`, `tomorrow's plan`, `tomorrow afternoon`, and `tomorrow evening`.
- The current miss downgrades a concrete chief-of-staff planning ask into the broad generic practical sorter, which is a noticeable usefulness regression relative to adjacent phrasing that already works.
- Compared with nearby generic document nouns like `outline`, `summary`, and `recap`, the tomorrow-mapping family has a clearer truthful destination in the current repo: the existing tomorrow-planning seam.
- The document-noun probes did not expose a higher-value nearby seam defect:
  - generic `outline` / `summary` / `recap` still fall to the broad sorter, but they do not have one obvious already-approved destination without widening scope
  - specific compound forms already route truthfully:
    - `proposal outline` -> presentation/prep fork
    - `presentation outline` -> presentation/prep fork
    - `meeting outline` -> meeting fork
    - `briefing outline` -> presentation/prep fork
    - `follow-up note` -> follow-up fork

## Why The Current Miss Happens
- `generate_companion_fallback` correctly checks `_is_tomorrow_planning_request` before the generic sorter.
- `_is_tomorrow_planning_request` currently covers direct phrases such as:
  - `help planning tomorrow`
  - `help scheduling tomorrow`
  - `help organizing tomorrow`
  - `help preparing for tomorrow`
  - `help getting ready for tomorrow`
  - `help with tomorrow's plan`
  - `help with tomorrow morning`
  - the newer agenda / schedule / calendar / appointments variants
- It does not currently include `map out tomorrow` or close nearby phrasing.
- Because `_request_needs_practical_handle` still recognizes these as practical asks, they then fall through to `_generic_practical_fallback_reply`, which returns the broad decision/conversation/plan sorter.

## Code / Tests Changed In This Slice
- None.
- This slice is recommendation-only.

## Exact Commands Run

```bash
sed -n '358,360p' /Users/chris/.codex/memories/MEMORY.md
sed -n '994,995p' /Users/chris/.codex/memories/MEMORY.md
rg -n "def generate_companion_fallback|def _is_meeting_prep_request|def _is_inbox_request|def _is_follow_up_request|def _is_presentation_or_proposal_prep_request|def _is_agenda_request|def _is_tomorrow_planning_request|def _is_constraints_scheduling_request|def _is_drafting_request|def _is_decision_shaped_request|def _generic_practical_fallback_reply" jarvis/companion_spine.py
sed -n '321,445p' jarvis/companion_spine.py
sed -n '678,776p' jarvis/companion_spine.py
sed -n '553,590p' jarvis/companion_spine.py
sed -n '1188,1288p' jarvis/companion_spine.py
sed -n '1282,1338p' jarvis/companion_spine.py
rg -n "mapping out tomorrow|map out tomorrow|outline|summary|recap|tomorrow afternoon|tomorrow evening" tests/test_companion_spine.py
rg -n "tomorrow('| afternoon| evening| morning| plan| schedule| calendar| agenda| appointments| planning tomorrow| getting ready for tomorrow| preparing for tomorrow)" tests/test_companion_spine.py
python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet = {}
prompts = [
    'I need help mapping out tomorrow.',
    'Help me map out tomorrow.',
    'I need help mapping out tomorrow morning.',
    'I need help mapping out tomorrow afternoon.',
    "I need help with tomorrow's plan.",
    'I need help planning tomorrow.',
    'I need help with tomorrow afternoon.',
    'I need help with tomorrow evening.',
    'I need help with this outline.',
    'I need help with this summary.',
    'I need help with this recap.',
    'I need help with this proposal outline.',
    'I need help with this presentation outline.',
    'I need help with this meeting outline.',
    'I need help with this briefing outline.',
    'I need help with this follow-up note.',
    'I need help with my inbox.',
    'I need help with this meeting.',
    'I need help with this presentation.',
    'I need help planning around constraints.',
]
for prompt in prompts:
    print('PROMPT:', prompt)
    print(generate_companion_fallback(prompt, packet))
    print('---')
PY
python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet = {}
prompts = [
    'I need help mapping out tomorrow.',
    'Help me map out tomorrow.',
    'I need help mapping out tomorrow morning.',
    'I need help mapping out tomorrow afternoon.',
    'I need help sketching out tomorrow.',
    'I need help laying out tomorrow.',
]
for prompt in prompts:
    print('PROMPT:', prompt)
    print(generate_companion_fallback(prompt, packet))
    print('---')
PY
python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet = {}
prompts = [
    'I need help planning around two appointments.',
    'I need help around my appointments tomorrow.',
    'I need help with my one-on-one.',
    'I need help with my follow-up.',
    'I need help with this briefing.',
    'I need help with my email.',
    'I need help with my calendar for tomorrow.',
    'I need help with my schedule for tomorrow.',
]
for prompt in prompts:
    print('PROMPT:', prompt)
    print(generate_companion_fallback(prompt, packet))
    print('---')
PY
```

## Exact Results
- `map out tomorrow` family currently misses the tomorrow-planning seam and falls to the broad practical sorter.
- Adjacent already-approved tomorrow-planning prompts still route correctly to:
  - `Good. For tomorrow, what actually has to happen, what is fixed, and what can slip?`
- Nearby specific compound prompts already route correctly to their concrete forks.
- No regression was observed in the preserved nearby controls checked in this pass.

## Architect Recommendation
- Recommend the next bounded slice as:
  - `Post-Epic 9 Companion Tomorrow-Mapping Opener Hardening`
- Proposed bounded scope:
  - stay only inside the existing first-turn tomorrow-planning opener seam in `jarvis/companion_spine.py`
  - harden `map out tomorrow` and the smallest clearly-adjacent variants that truthfully belong to the same tomorrow-planning family
  - preserve inbox, meeting, agenda, follow-up, presentation, drafting, decision, hard-conversation, constraints-scheduling, and overloaded-week routing unchanged
- Recommendation strength:
  - highest-value next bounded repair from current repo truth
  - no code change performed in this reassessment slice
