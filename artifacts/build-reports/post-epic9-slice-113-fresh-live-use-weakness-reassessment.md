# Post-Epic 9 Slice 113: Fresh Live-Use Weakness Reassessment

Ready for Architect Office review: yes

## Exact prompts or routes inspected

Fresh bounded prompt sweep:
- `I need help with my one-on-one.`
- `I need help getting ready for my one-on-one.`
- `I need help preparing for my one-on-one.`
- `I need help with my 1:1.`
- `I need help with this check-in.`
- `I need help with this debrief.`
- `I need help after this meeting.`
- `I need help with this deck.`
- `I need help getting ready for this deck.`
- `I need help with my talking points.`
- `I need help mapping out tomorrow.`
- `I need help planning around two appointments.`
- `I need help sorting out today.`
- `I need help with my priorities today.`
- `I need help with my notes for this meeting.`
- `I need help with this agenda.`
- `I need help with this meeting.`
- `I need help with this presentation.`
- `I need help planning tomorrow.`
- `I need help with my email.`

Direct comparison battery:
- `I need help with this meeting.`
- `I need help with my one-on-one.`
- `I need help getting ready for my one-on-one.`
- `I need help preparing for my one-on-one.`
- `I need help with my 1:1.`
- `I need help with this check-in.`
- `I need help with this debrief.`
- `I need help after this meeting.`
- `I need help with this agenda.`
- `I need help with my email.`
- `I need help with this presentation.`
- `I need help planning tomorrow.`

## Exact code seams inspected

- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:321)
  - `generate_companion_fallback(...)` branch ordering for first-turn opener routing
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:635)
  - `_is_meeting_prep_request(...)`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:672)
  - `_is_follow_up_request(...)`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:685)
  - `_is_presentation_or_proposal_prep_request(...)`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:725)
  - `_is_tomorrow_planning_request(...)`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:745)
  - `_is_constraints_scheduling_request(...)`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:1261)
  - `_generic_practical_fallback_reply(...)`

## Strongest remaining defect found

The strongest remaining first-turn live-use defect is the meeting-adjacent one-on-one/check-in family under-routing out of the existing meeting seam:

- `I need help with my one-on-one.`
- `I need help getting ready for my one-on-one.`
- `I need help preparing for my one-on-one.`
- `I need help with my 1:1.`
- `I need help with this check-in.`

Current repo truth for all of those:
- `Let's make it concrete. Is this mostly a decision, a conversation, or a plan you need to sort out first?`

That is materially weaker than the existing truthful meeting fork already available for:
- `I need help with this meeting.`
  - `Good. Is the real work for this meeting the outcome you need, how you need to say it, or the agenda you need to walk in with?`

## Why it is higher value than adjacent options

This family is higher value than the nearby misses because:

1. It is a common chief-of-staff ask that is semantically very close to the already-approved meeting seam.
2. The truthful destination seam already exists and is good:
   - it frames the work around outcome, delivery, and agenda
   - it does not fake calendar context, attendee knowledge, or external retrieval
3. The miss is broad enough to cover natural workplace language that real users send:
   - `one-on-one`
   - `1:1`
   - `check-in`
4. Nearby misses are either narrower or less clearly mapped to an existing seam:
   - `this deck` / `talking points` are presentation-adjacent but more artifact-specific
   - `mapping out tomorrow` and `planning around two appointments` are planning variants, but planning already has stronger concrete nearby coverage than the one-on-one family does
5. The new inbox/email-management repair is now clean, which leaves the one-on-one family as the clearest remaining case where an already-good concrete fork exists but natural first-turn phrasing still falls to the generic sorter.

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
    "I need help with my one-on-one.",
    "I need help getting ready for my one-on-one.",
    "I need help preparing for my one-on-one.",
    "I need help with my 1:1.",
    "I need help with this check-in.",
    "I need help with this debrief.",
    "I need help after this meeting.",
    "I need help with this deck.",
    "I need help getting ready for this deck.",
    "I need help with my talking points.",
    "I need help mapping out tomorrow.",
    "I need help planning around two appointments.",
    "I need help sorting out today.",
    "I need help with my priorities today.",
    "I need help with my notes for this meeting.",
    "I need help with this agenda.",
    "I need help with this meeting.",
    "I need help with this presentation.",
    "I need help planning tomorrow.",
    "I need help with my email.",
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
    "I need help with this meeting.",
    "I need help with my one-on-one.",
    "I need help getting ready for my one-on-one.",
    "I need help preparing for my one-on-one.",
    "I need help with my 1:1.",
    "I need help with this check-in.",
    "I need help with this debrief.",
    "I need help after this meeting.",
    "I need help with this agenda.",
    "I need help with my email.",
    "I need help with this presentation.",
    "I need help planning tomorrow.",
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
sed -n '635,760p' jarvis/companion_spine.py
sed -n '1261,1320p' jarvis/companion_spine.py
```

## Exact results

Highest-value current miss:
- `I need help with my one-on-one.` -> generic practical sorter
- `I need help getting ready for my one-on-one.` -> generic practical sorter
- `I need help preparing for my one-on-one.` -> generic practical sorter
- `I need help with my 1:1.` -> generic practical sorter
- `I need help with this check-in.` -> generic practical sorter

Direct seam comparison:
- `I need help with this meeting.` -> meeting fork
- `I need help with this agenda.` -> agenda fork
- `I need help with my email.` -> inbox fork
- `I need help with this presentation.` -> presentation-prep fork
- `I need help planning tomorrow.` -> tomorrow-planning fork

Other inspected misses still exist, but ranked lower:
- `I need help with this deck.` -> generic practical sorter
- `I need help getting ready for this deck.` -> generic practical sorter
- `I need help with my talking points.` -> generic practical sorter
- `I need help mapping out tomorrow.` -> generic practical sorter
- `I need help planning around two appointments.` -> generic practical sorter
- `I need help with this debrief.` -> generic practical sorter
- `I need help after this meeting.` -> generic practical sorter

## Clear Architect recommendation

Recommended next bounded slice only:

**Slice 114: Companion One-on-One / Check-In Meeting Opener Hardening**

Bounded target family:
- `I need help with my one-on-one.`
- `I need help getting ready for my one-on-one.`
- `I need help preparing for my one-on-one.`
- `I need help with my 1:1.`
- `I need help with this check-in.`

Truth boundary to preserve:
- route meeting-adjacent prep phrasing to the existing truthful meeting fork
- keep explicit agenda phrasing on the agenda fork
- keep inbox, drafting, presentation, tomorrow-planning, decision, and hard-conversation seams unchanged
- do not imply calendar access, attendee details, or live meeting context

That is the cleanest next repair because it closes a broad, practical, already-well-defined chief-of-staff miss using an existing truthful seam without needing new architecture.
