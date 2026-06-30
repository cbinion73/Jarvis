# Post-Epic 9 Slice 115: Fresh Live-Use Weakness Reassessment

Ready for Architect Office review: yes

## Exact prompts or routes inspected

Fresh bounded prompt sweep:
- `I need help with this deck.`
- `I need help getting ready for this deck.`
- `I need help with my talking points.`
- `I need help with this debrief.`
- `I need help after this meeting.`
- `I need help with my notes for this meeting.`
- `I need help mapping out tomorrow.`
- `I need help planning around two appointments.`
- `I need help planning around my appointments.`
- `I need help with this slide deck.`
- `I need help with this meeting.`
- `I need help with this agenda.`
- `I need help planning tomorrow.`
- `I need help with my email.`
- `I need help with my one-on-one.`
- `I need help with my follow-up.`
- `I need help with this presentation.`

Direct comparison battery:
- `I need help with this slide deck.`
- `I need help with this deck.`
- `I need help getting ready for this deck.`
- `I need help with my talking points.`
- `I need help with this presentation.`
- `I need help with this proposal.`
- `I need help with this debrief.`
- `I need help after this meeting.`
- `I need help mapping out tomorrow.`
- `I need help planning around two appointments.`

## Exact code seams inspected

- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:321)
  - `generate_companion_fallback(...)` branch ordering for first-turn opener routing
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:691)
  - `_is_presentation_or_proposal_prep_request(...)`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:635)
  - `_is_meeting_prep_request(...)`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:678)
  - `_is_follow_up_request(...)`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:731)
  - `_is_tomorrow_planning_request(...)`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:751)
  - `_is_constraints_scheduling_request(...)`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:1267)
  - `_generic_practical_fallback_reply(...)`

## Strongest remaining defect found

The strongest remaining first-turn live-use defect is the presentation/deck shorthand family under-routing out of the existing presentation-prep seam:

- `I need help with this deck.`
- `I need help getting ready for this deck.`
- `I need help with my talking points.`

Current repo truth for all three:
- `Let's make it concrete. Is this mostly a decision, a conversation, or a plan you need to sort out first?`

That is materially weaker than the existing truthful prep fork already available for:
- `I need help with this slide deck.`
- `I need help with this presentation.`
- `I need help with this proposal.`

All three of those already return:
- `Good. Is the real work the point you need to land, the structure, or getting ready to deliver it cleanly?`

## Why it is higher value than adjacent options

This family is higher value than the nearby misses because:

1. It is clearly adjacent to an already-approved truthful seam rather than requiring a new lane.
2. The destination seam is already strong and honest:
   - it frames the work around point, structure, and delivery
   - it does not fake audience, calendar, slide, or document context
3. The miss is ordinary real-world phrasing:
   - `deck` is a common shorthand for `slide deck`
   - `talking points` is a natural first-turn prep ask in the same presentation/prep neighborhood
4. Nearby misses are more ambiguous:
   - `debrief` and `after this meeting` could belong to meeting, follow-up, or notes work depending on intent
   - `mapping out tomorrow` and `planning around two appointments` suggest a planning lane, but there is not yet the same clean one-to-one seam match that already exists for `deck` vs `slide deck`
5. The existing comparison is especially strong in current repo truth:
   - `this slide deck` works
   - `this deck` does not
   - that makes the next bounded repair unusually concrete and low-risk

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
    "I need help with this deck.",
    "I need help getting ready for this deck.",
    "I need help with my talking points.",
    "I need help with this debrief.",
    "I need help after this meeting.",
    "I need help with my notes for this meeting.",
    "I need help mapping out tomorrow.",
    "I need help planning around two appointments.",
    "I need help planning around my appointments.",
    "I need help with this slide deck.",
    "I need help with this meeting.",
    "I need help with this agenda.",
    "I need help planning tomorrow.",
    "I need help with my email.",
    "I need help with my one-on-one.",
    "I need help with my follow-up.",
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
    "I need help with this slide deck.",
    "I need help with this deck.",
    "I need help getting ready for this deck.",
    "I need help with my talking points.",
    "I need help with this presentation.",
    "I need help with this proposal.",
    "I need help with this debrief.",
    "I need help after this meeting.",
    "I need help mapping out tomorrow.",
    "I need help planning around two appointments.",
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
sed -n '1267,1325p' jarvis/companion_spine.py
```

## Exact results

Highest-value current miss:
- `I need help with this deck.` -> generic practical sorter
- `I need help getting ready for this deck.` -> generic practical sorter
- `I need help with my talking points.` -> generic practical sorter

Direct seam comparison:
- `I need help with this slide deck.` -> presentation-prep fork
- `I need help with this presentation.` -> presentation-prep fork
- `I need help with this proposal.` -> presentation-prep fork

Other inspected misses still exist, but ranked lower:
- `I need help with this debrief.` -> generic practical sorter
- `I need help after this meeting.` -> generic practical sorter
- `I need help with my notes for this meeting.` -> generic practical sorter
- `I need help mapping out tomorrow.` -> generic practical sorter
- `I need help planning around two appointments.` -> generic practical sorter
- `I need help planning around my appointments.` -> generic practical sorter

## Clear Architect recommendation

Recommended next bounded slice only:

**Slice 116: Companion Deck / Talking-Points Presentation Opener Hardening**

Bounded target family:
- `I need help with this deck.`
- `I need help getting ready for this deck.`
- `I need help with my talking points.`

Truth boundary to preserve:
- route deck/presentation shorthand to the existing truthful presentation-prep fork
- keep meeting, agenda, inbox, drafting, follow-up, tomorrow-planning, decision, hard-conversation, and constraints-scheduling seams unchanged
- do not imply audience knowledge, slide access, stored materials, or live presentation context

That is the cleanest next repair because it closes a broad, natural shorthand miss using an already-proven truthful seam, with a very tight repo-truth comparison between `slide deck` and `deck`.
