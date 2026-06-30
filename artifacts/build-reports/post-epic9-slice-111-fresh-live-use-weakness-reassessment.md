# Post-Epic 9 Slice 111: Fresh Live-Use Weakness Reassessment

Ready for Architect Office review: yes

## Exact prompts or routes inspected

Fresh bounded first-turn prompt sweep:
- `I need help with my email.`
- `I need help getting through email.`
- `I need help triaging email.`
- `I need help with my one-on-one.`
- `I need help getting ready for my one-on-one.`
- `I need help preparing for my one-on-one.`
- `I need help with my 1:1.`
- `I need help planning my day tomorrow.`
- `I need help mapping out tomorrow.`
- `I need help planning around two appointments.`
- `I need help with this deck.`
- `I need help getting ready for this deck.`
- `I need help with my talking points.`
- `I need help with meeting notes.`
- `I need help with my follow-up note.`
- `I need help with my priorities today.`
- `I need help sorting out today.`
- `I need help with this debrief.`
- `I need help after this meeting.`
- `I need help with this check-in.`

Direct seam-comparison controls:
- `I need help with my inbox.`
- `I need help writing an email to my boss.`
- `I need help with this meeting.`
- `I need help with this presentation.`
- `I need help planning tomorrow.`

## Exact code seams inspected

- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:321)
  - `generate_companion_fallback(...)` branch ordering for first-turn opener routing
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:656)
  - `_is_inbox_request(...)`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:684)
  - `_is_presentation_or_proposal_prep_request(...)`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:724)
  - `_is_tomorrow_planning_request(...)`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:1037)
  - `_is_drafting_request(...)`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:1260)
  - `_generic_practical_fallback_reply(...)`

## Strongest remaining defect found

The strongest remaining first-turn live-use defect is the natural inbox/email-management family under-routing out of the existing inbox seam:

- `I need help with my email.`
- `I need help getting through email.`
- `I need help triaging email.`

Current repo truth for all three:
- `Let's make it concrete. Is this mostly a decision, a conversation, or a plan you need to sort out first?`

That is materially weaker than the existing truthful inbox fork already available for:
- `I need help with my inbox.`
  - `Good. Is the real problem triage, replies you owe, or clearing the pile without getting sucked into it?`

## Why it is higher value than adjacent options

This family is higher value than the nearby misses because:

1. It is a broader, more frequent chief-of-staff ask than the narrower `one-on-one`, `deck`, or `talking points` families.
2. The truthful destination seam already exists and is good: the inbox fork does not fake inbox/thread understanding and stays at honest triage/reply/clear-the-pile posture.
3. Adjacent drafting behavior is already clean:
   - `I need help writing an email to my boss.` correctly lands on the drafting fork
   - that makes the remaining email-management family a narrow opener-classification gap rather than a broader email redesign
4. Some adjacent misses are already partially served by concrete nearby seams:
   - `I need help planning my day tomorrow.` already gets a concrete capacity-pushback reply
   - `I need help with my priorities today.` already gets a concrete capacity-pushback reply
- By contrast, the inbox/email-management family still falls all the way back to the generic sorter even when the user is clearly asking for inbox triage help.

## Whether code/tests changed or next bounded slice only

No code or tests changed in this slice.

This is a recommendation-only reassessment slice.

## Exact commands run

Prompt sweep:

```bash
python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
prompts = [
    "I need help with my email.",
    "I need help getting through email.",
    "I need help triaging email.",
    "I need help with my one-on-one.",
    "I need help getting ready for my one-on-one.",
    "I need help preparing for my one-on-one.",
    "I need help with my 1:1.",
    "I need help planning my day tomorrow.",
    "I need help mapping out tomorrow.",
    "I need help planning around two appointments.",
    "I need help with this deck.",
    "I need help getting ready for this deck.",
    "I need help with my talking points.",
    "I need help with meeting notes.",
    "I need help with my follow-up note.",
    "I need help with my priorities today.",
    "I need help sorting out today.",
    "I need help with this debrief.",
    "I need help after this meeting.",
    "I need help with this check-in.",
]
for prompt in prompts:
    print('PROMPT:', prompt)
    print(generate_companion_fallback(prompt, packet))
    print('---')
PY
```

Direct seam comparison:

```bash
python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
prompts = [
    "I need help with my inbox.",
    "I need help with my email.",
    "I need help getting through email.",
    "I need help triaging email.",
    "I need help writing an email to my boss.",
    "I need help with this meeting.",
    "I need help with my one-on-one.",
    "I need help getting ready for my one-on-one.",
    "I need help with this presentation.",
    "I need help with this deck.",
    "I need help getting ready for this deck.",
    "I need help planning tomorrow.",
    "I need help mapping out tomorrow.",
]
for prompt in prompts:
    print(prompt)
    print(generate_companion_fallback(prompt, packet))
    print()
PY
```

Code-seam inspection:

```bash
sed -n '321,470p' jarvis/companion_spine.py
sed -n '635,780p' jarvis/companion_spine.py
sed -n '1037,1195p' jarvis/companion_spine.py
sed -n '1220,1365p' jarvis/companion_spine.py
```

## Exact results

Highest-value current miss:
- `I need help with my email.` -> generic practical sorter
- `I need help getting through email.` -> generic practical sorter
- `I need help triaging email.` -> generic practical sorter

Direct comparison against existing truthful seams:
- `I need help with my inbox.` -> inbox fork
- `I need help writing an email to my boss.` -> drafting fork

Other inspected misses still exist, but ranked lower:
- `I need help with my one-on-one.` -> generic practical sorter
- `I need help getting ready for my one-on-one.` -> generic practical sorter
- `I need help with this deck.` -> generic practical sorter
- `I need help getting ready for this deck.` -> generic practical sorter
- `I need help mapping out tomorrow.` -> generic practical sorter

Lower-priority because:
- they are narrower subfamilies than inbox/email-management
- or they already sit closer to existing partially useful concrete planning behavior

## Clear Architect recommendation

Recommended next bounded slice only:

**Slice 112: Companion Email-Management / Inbox-Triage Opener Hardening**

Bounded target family:
- `I need help with my email.`
- `I need help getting through email.`
- `I need help triaging email.`

Truth boundary to preserve:
- route inbox-management phrasing to the existing truthful inbox fork
- keep explicit single-message drafting prompts on the drafting fork
- do not imply live inbox retrieval, account access, sender knowledge, or thread understanding

That is the cleanest next repair because it closes a broad everyday chief-of-staff miss using an already-proven truthful seam, without needing new architecture.
