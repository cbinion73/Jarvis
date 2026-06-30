# Post-Epic 9 Slice 123: Fresh Live-Use Weakness Reassessment

Ready for Architect Office review: yes

## Exact prompts or routes inspected

Fresh bounded prompt sweep:
- `I need help planning around two appointments.`
- `I need help planning around my appointments.`
- `I need help scheduling around appointments.`
- `I need help around my appointments tomorrow.`
- `I need help mapping out tomorrow.`
- `I need help with tomorrow afternoon.`
- `I need help with this outline.`
- `I need help with this summary.`
- `I need help with this recap.`
- `I need help with this agenda.`
- `I need help planning around constraints.`
- `I need help planning around two meetings.`
- `I need help planning tomorrow.`
- `I need help with this meeting.`
- `I need help with my follow-up.`
- `I need help with my email.`
- `I need help with this presentation.`

Focused comparison battery:
- `I need help planning around two meetings.`
- `I need help planning around two appointments.`
- `I need help planning around my appointments.`
- `I need help scheduling around appointments.`
- `I need help around my appointments tomorrow.`
- `I need help planning around constraints.`
- `I need help scheduling around constraints.`
- `I need help planning tomorrow.`
- `I need help mapping out tomorrow.`
- `I need help with tomorrow afternoon.`

## Exact code seams inspected

- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:321)
  - `generate_companion_fallback(...)` opener ordering
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:738)
  - `_is_tomorrow_planning_request(...)`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:760)
  - `_is_constraints_scheduling_request(...)`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:1278)
  - `_generic_practical_fallback_reply(...)`

## Strongest remaining defect found

The strongest remaining first-turn live-use defect is the appointment-based planning family still under-routing to the generic practical sorter:

- `I need help planning around two appointments.`
- `I need help planning around my appointments.`
- `I need help scheduling around appointments.`
- `I need help around my appointments tomorrow.`

Current repo truth for all four:
- `Let's make it concrete. Is this mostly a decision, a conversation, or a plan you need to sort out first?`

That is materially weaker than the two already-truthful nearby planning seams:
- `I need help planning around two meetings.` -> tomorrow-planning fork
- `I need help planning around constraints.` / `I need help scheduling around constraints.` -> constraints-scheduling fork

## Why it is higher value than adjacent options

This family is higher value than the nearby misses because:

1. It is a broad practical chief-of-staff ask that is clearly adjacent to two already-approved planning seams.
2. The repo-truth contrast is especially strong:
   - `planning around two meetings` already lands on the tomorrow-planning fork
   - `planning around constraints` already lands on the constraints-scheduling fork
   - but `planning around appointments` still falls to the generic sorter
3. It covers multiple natural phrasings instead of a single isolated alias:
   - two appointments
   - my appointments
   - scheduling around appointments
   - around my appointments tomorrow
4. It outranks `mapping out tomorrow` because that is effectively one remaining tomorrow alias, while the appointment family is a larger, more practical cluster with a clearer neighboring seam relationship.
5. It outranks generic document-shaped misses like `outline`, `summary`, and `recap` because those do not yet point to a single obvious truthful destination seam the way appointment-based planning does.

## Whether code/tests changed or next bounded slice only

No code or tests changed in this slice.

This is a recommendation-only reassessment slice.

## Exact commands run

Fresh prompt sweep:

```bash
python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet={"available_capabilities":["ongoing conversation in this shell","conversation turn persistence"]}
prompts=[
    "I need help planning around two appointments.",
    "I need help planning around my appointments.",
    "I need help scheduling around appointments.",
    "I need help around my appointments tomorrow.",
    "I need help mapping out tomorrow.",
    "I need help with tomorrow afternoon.",
    "I need help with this outline.",
    "I need help with this summary.",
    "I need help with this recap.",
    "I need help with this agenda.",
    "I need help planning around constraints.",
    "I need help planning around two meetings.",
    "I need help planning tomorrow.",
    "I need help with this meeting.",
    "I need help with my follow-up.",
    "I need help with my email.",
    "I need help with this presentation.",
]
for prompt in prompts:
    print('PROMPT:', prompt)
    print(generate_companion_fallback(prompt, packet))
    print('---')
PY
```

Focused comparison battery:

```bash
python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet={"available_capabilities":["ongoing conversation in this shell","conversation turn persistence"]}
prompts=[
    "I need help planning around two meetings.",
    "I need help planning around two appointments.",
    "I need help planning around my appointments.",
    "I need help scheduling around appointments.",
    "I need help around my appointments tomorrow.",
    "I need help planning around constraints.",
    "I need help scheduling around constraints.",
    "I need help planning tomorrow.",
    "I need help mapping out tomorrow.",
    "I need help with tomorrow afternoon.",
]
for prompt in prompts:
    print(prompt)
    print(generate_companion_fallback(prompt, packet))
    print()
PY
```

Code seam inspection:

```bash
sed -n '321,445p' jarvis/companion_spine.py
sed -n '738,776p' jarvis/companion_spine.py
sed -n '1278,1328p' jarvis/companion_spine.py
```

## Exact results

Highest-value current miss:
- `I need help planning around two appointments.` -> generic practical sorter
- `I need help planning around my appointments.` -> generic practical sorter
- `I need help scheduling around appointments.` -> generic practical sorter
- `I need help around my appointments tomorrow.` -> generic practical sorter

Direct seam comparison:
- `I need help planning around two meetings.` -> tomorrow-planning fork
- `I need help planning around constraints.` -> constraints-scheduling fork
- `I need help scheduling around constraints.` -> constraints-scheduling fork
- `I need help planning tomorrow.` -> tomorrow-planning fork

Other inspected misses still exist, but ranked lower:
- `I need help mapping out tomorrow.` -> generic practical sorter
- `I need help with this outline.` -> generic practical sorter
- `I need help with this summary.` -> generic practical sorter
- `I need help with this recap.` -> generic practical sorter

## Clear Architect recommendation

Recommended next bounded slice only:

**Slice 124: Companion Appointment-Based Planning Opener Hardening**

Bounded target family:
- `I need help planning around two appointments.`
- `I need help planning around my appointments.`
- `I need help scheduling around appointments.`
- `I need help around my appointments tomorrow.`

Truth boundary to preserve:
- route appointment-based planning phrasing to the smallest truthful nearby planning seam
- keep explicit constraints phrasing on the constraints-scheduling fork
- keep explicit tomorrow-planning prompts on the tomorrow-planning fork
- keep meeting, follow-up, agenda, inbox, drafting, presentation, decision, and hard-conversation seams unchanged
- do not imply live calendar retrieval, appointment details, or external schedule access

That is the cleanest next repair because it closes a practical scheduling cluster using already-proven neighboring seams, without broadening into a new planning architecture.
