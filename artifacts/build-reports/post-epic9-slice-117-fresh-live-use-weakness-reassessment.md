# Post-Epic 9 Slice 117: Fresh Live-Use Weakness Reassessment

Ready for Architect Office review: yes

## Exact prompts or routes inspected

Fresh bounded prompt sweep:
- `I need help with this debrief.`
- `I need help after this meeting.`
- `I need help with my notes for this meeting.`
- `I need help with meeting notes.`
- `I need help with this recap.`
- `I need help mapping out tomorrow.`
- `I need help planning around two appointments.`
- `I need help planning around my appointments.`
- `I need help scheduling around appointments.`
- `I need help with my schedule tomorrow.`
- `I need help with tomorrow afternoon.`
- `I need help with this outline.`
- `I need help with this summary.`
- `I need help with this meeting.`
- `I need help with my follow-up.`
- `I need help planning tomorrow.`
- `I need help scheduling around constraints.`
- `I need help with this presentation.`

Direct comparison battery:
- `I need help with this debrief.`
- `I need help after this meeting.`
- `I need help with my notes for this meeting.`
- `I need help with meeting notes.`
- `I need help with my follow-up.`
- `I need help with this meeting.`
- `I need help with this agenda.`
- `I need help mapping out tomorrow.`
- `I need help planning around two appointments.`
- `I need help planning around my appointments.`
- `I need help planning tomorrow.`
- `I need help scheduling around constraints.`

## Exact code seams inspected

- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:321)
  - `generate_companion_fallback(...)` branch ordering for first-turn opener routing
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:635)
  - `_is_meeting_prep_request(...)`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:678)
  - `_is_follow_up_request(...)`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:734)
  - `_is_tomorrow_planning_request(...)`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:754)
  - `_is_constraints_scheduling_request(...)`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:1270)
  - `_generic_practical_fallback_reply(...)`

## Strongest remaining defect found

The strongest remaining first-turn live-use defect is the post-meeting debrief/notes family under-routing to the generic practical sorter:

- `I need help with this debrief.`
- `I need help after this meeting.`
- `I need help with my notes for this meeting.`
- `I need help with meeting notes.`

Current repo truth for all four:
- `Let's make it concrete. Is this mostly a decision, a conversation, or a plan you need to sort out first?`

That is materially weaker than the two already-truthful nearby seams:
- `I need help with this meeting.` -> meeting fork
- `I need help with my follow-up.` -> follow-up fork

## Why it is higher value than adjacent options

This family is higher value than the nearby misses because:

1. It sits directly between two already-approved truthful seams:
   - meeting prep
   - follow-up
2. The user intent is common and practical:
   - debriefing a meeting
   - figuring out what to do after a meeting
   - turning meeting notes into next moves
3. The bounded repair space is clearer than the remaining planning variants:
   - `mapping out tomorrow` and `planning around appointments` are still real misses, but they do not yet map as tightly to one already-proven destination seam as debrief/follow-up does
4. The current contrast is strong in repo truth:
   - `this meeting` already gets a concrete meeting fork
   - `my follow-up` already gets a concrete follow-up fork
   - but `after this meeting` and `meeting notes` still fall all the way to the generic sorter
5. This makes the next bounded lane relatively low-risk: it can likely stay inside an existing meeting/follow-up-adjacent opener seam rather than requiring a new architecture lane.

## Whether code/tests changed or next bounded slice only

No code or tests changed in this slice.

This is a recommendation-only reassessment slice.

## Exact commands run

Fresh prompt sweep:

```bash
python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
prompts = [
    "I need help with this debrief.",
    "I need help after this meeting.",
    "I need help with my notes for this meeting.",
    "I need help with meeting notes.",
    "I need help with this recap.",
    "I need help mapping out tomorrow.",
    "I need help planning around two appointments.",
    "I need help planning around my appointments.",
    "I need help scheduling around appointments.",
    "I need help with my schedule tomorrow.",
    "I need help with tomorrow afternoon.",
    "I need help with this outline.",
    "I need help with this summary.",
    "I need help with this meeting.",
    "I need help with my follow-up.",
    "I need help planning tomorrow.",
    "I need help scheduling around constraints.",
    "I need help with this presentation.",
]
for prompt in prompts:
    print('PROMPT:', prompt)
    print(generate_companion_fallback(prompt, packet))
    print('---')
PY
```

Direct comparison battery:

```bash
python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
prompts = [
    "I need help with this debrief.",
    "I need help after this meeting.",
    "I need help with my notes for this meeting.",
    "I need help with meeting notes.",
    "I need help with my follow-up.",
    "I need help with this meeting.",
    "I need help with this agenda.",
    "I need help mapping out tomorrow.",
    "I need help planning around two appointments.",
    "I need help planning around my appointments.",
    "I need help planning tomorrow.",
    "I need help scheduling around constraints.",
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
sed -n '635,765p' jarvis/companion_spine.py
sed -n '1270,1328p' jarvis/companion_spine.py
```

## Exact results

Highest-value current miss:
- `I need help with this debrief.` -> generic practical sorter
- `I need help after this meeting.` -> generic practical sorter
- `I need help with my notes for this meeting.` -> generic practical sorter
- `I need help with meeting notes.` -> generic practical sorter

Direct seam comparison:
- `I need help with this meeting.` -> meeting fork
- `I need help with my follow-up.` -> follow-up fork
- `I need help with this agenda.` -> agenda fork

Other inspected misses still exist, but ranked lower:
- `I need help mapping out tomorrow.` -> generic practical sorter
- `I need help planning around two appointments.` -> generic practical sorter
- `I need help planning around my appointments.` -> generic practical sorter
- `I need help scheduling around appointments.` -> generic practical sorter

## Clear Architect recommendation

Recommended next bounded slice only:

**Slice 118: Companion Post-Meeting Debrief / Notes Opener Hardening**

Bounded target family:
- `I need help with this debrief.`
- `I need help after this meeting.`
- `I need help with my notes for this meeting.`
- `I need help with meeting notes.`

Truth boundary to preserve:
- route post-meeting/debrief phrasing to the smallest truthful nearby seam
- keep explicit meeting-prep prompts on the meeting fork
- keep explicit follow-up prompts on the follow-up fork
- keep agenda, inbox, drafting, tomorrow-planning, decision, hard-conversation, and constraints-scheduling seams unchanged
- do not imply calendar access, attendee memory, or live note retrieval

That is the cleanest next repair because it closes a common post-meeting chief-of-staff ask using already-established neighboring truth seams, without starting a broader planning or object architecture lane.
