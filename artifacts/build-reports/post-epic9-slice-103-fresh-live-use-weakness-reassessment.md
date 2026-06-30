# Post-Epic 9 Slice 103: Fresh Live-Use Weakness Reassessment

Ready for Architect Office review: yes

## Exact prompts or routes inspected

Bounded first-turn prompt set inspected:
- `I need help with my inbox.`
- `I need help planning tomorrow.`
- `I need help preparing for tomorrow.`
- `I need help with this meeting.`
- `I need help with this agenda.`
- `I need help with my agenda for tomorrow.`
- `I need help with this presentation.`
- `I need help with this slide deck.`
- `I need help with this pitch.`
- `I need help with my slide deck.`
- `I need help with my pitch.`
- `I need help with my proposal deck.`
- `I need help with this proposal deck.`
- `I need help with this briefing.`
- `I need help with my briefing.`
- `I need help with my follow-up.`
- `I need help with this follow-up.`
- `I need help following up after this meeting.`
- `I need help drafting an email to my boss.`
- `I need help writing a follow-up email after this meeting.`
- `I need help deciding between two apartments.`
- `I need help with a hard conversation.`
- `I need help scheduling around constraints.`
- `I need help with my calendar tomorrow.`
- `I need help with my schedule tomorrow.`
- `I need help figuring out my day.`
- `I need help with my day.`
- `I need help with my priorities for this week.`

Additional targeted comparison prompts:
- `I need help with my presentation.`
- `I need help with my proposal.`
- `I need help getting ready for my presentation.`
- `I need help getting ready for my proposal.`
- `I need help with this proposal.`
- `I need help with this briefing.`
- `I need help with my briefing.`
- `I need help with my follow-up.`

## Exact code seams inspected

Code seams inspected:
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:321)
  - `generate_companion_fallback(...)`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:548)
  - `_request_needs_practical_handle(...)`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:666)
  - `_is_presentation_or_proposal_prep_request(...)`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:691)
  - `_is_tomorrow_planning_request(...)`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:1224)
  - `_generic_practical_fallback_reply(...)`

## Strongest remaining defect found

The strongest remaining first-turn chief-of-staff usefulness defect is the possessive presentation-prep family.

Current repo-truth behavior:
- `I need help with my presentation.`
  - `Let's make it concrete. Is this mostly a decision, a conversation, or a plan you need to sort out first?`
- `I need help with my proposal.`
  - `Let's make it concrete. Is this mostly a decision, a conversation, or a plan you need to sort out first?`
- `I need help with my slide deck.`
  - `Let's make it concrete. Is this mostly a decision, a conversation, or a plan you need to sort out first?`
- `I need help with my pitch.`
  - `Let's make it concrete. Is this mostly a decision, a conversation, or a plan you need to sort out first?`
- `I need help with my proposal deck.`
  - `Let's make it concrete. Is this mostly a decision, a conversation, or a plan you need to sort out first?`
- `I need help getting ready for my presentation.`
  - `Let's make it concrete. Is this mostly a decision, a conversation, or a plan you need to sort out first?`
- `I need help getting ready for my proposal.`
  - `Let's make it concrete. Is this mostly a decision, a conversation, or a plan you need to sort out first?`

Why this is a real defect:
- these are natural first-turn chief-of-staff asks about preparing an owned deliverable
- the truthful adjacent fork already exists and is strong for the same family with `this` phrasing:
  - `I need help with this presentation.` -> `Good. Is the real work the point you need to land, the structure, or getting ready to deliver it cleanly?`
  - `I need help with this proposal.` -> same fork
  - `I need help with this slide deck.` -> same fork
  - `I need help with this pitch.` -> same fork
  - `I need help with this proposal deck.` -> same fork

## Why it is higher value than adjacent options

The possessive presentation-prep family is higher value than the nearby remaining misses because it is both broader and anchored to an already-approved neighboring seam.

Compared with adjacent options:
- `briefing` prompts:
  - still generic, but less clearly tied to a single existing truthful destination
- `follow-up` prompts:
  - still generic, but can mean message drafting, meeting follow-through, or a broader next-step ask
- `my agenda for tomorrow`:
  - real miss, but narrower than the presentation-prep family
- `calendar tomorrow` / `schedule tomorrow`:
  - currently land on the existing capacity fork rather than falling all the way to the generic practical sorter

This makes possessive presentation-prep the clearest next slice: several natural phrasings all miss, and the target fork is already proven with the parallel `this ...` forms.

## Whether code/tests changed or next bounded slice only

No code or tests were changed in this slice.

This is a recommendation-only reassessment. The defect is concrete, but it is cleaner to isolate it as its own bounded opener-hardening slice than to combine reassessment plus implementation here.

## Exact commands run

```bash
python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
prompts = [
    "I need help with my inbox.",
    "I need help planning tomorrow.",
    "I need help preparing for tomorrow.",
    "I need help with this meeting.",
    "I need help with this agenda.",
    "I need help with my agenda for tomorrow.",
    "I need help with this presentation.",
    "I need help with this slide deck.",
    "I need help with this pitch.",
    "I need help with my slide deck.",
    "I need help with my pitch.",
    "I need help with my proposal deck.",
    "I need help with this proposal deck.",
    "I need help with this briefing.",
    "I need help with my briefing.",
    "I need help with my follow-up.",
    "I need help with this follow-up.",
    "I need help following up after this meeting.",
    "I need help drafting an email to my boss.",
    "I need help writing a follow-up email after this meeting.",
    "I need help deciding between two apartments.",
    "I need help with a hard conversation.",
    "I need help scheduling around constraints.",
    "I need help with my calendar tomorrow.",
    "I need help with my schedule tomorrow.",
    "I need help figuring out my day.",
    "I need help with my day.",
    "I need help with my priorities for this week.",
]
for prompt in prompts:
    print(f"PROMPT: {prompt}")
    print(generate_companion_fallback(prompt, packet))
    print("---")
PY

rg -n "def generate_companion_fallback|_is_presentation_or_proposal_prep_request|_is_agenda_request|_is_inbox_request|_is_meeting_prep_request|_is_constraints_scheduling_request|_is_tomorrow_planning_request|_generic_practical_fallback_reply|_request_needs_practical_handle|briefing|follow-up|proposal deck|slide deck|pitch" jarvis/companion_spine.py tests/test_companion_spine.py

python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
prompts = [
    "I need help with my presentation.",
    "I need help with my proposal.",
    "I need help with my slide deck.",
    "I need help with my pitch.",
    "I need help with my proposal deck.",
    "I need help getting ready for my presentation.",
    "I need help getting ready for my proposal.",
    "I need help with this presentation.",
    "I need help with this proposal.",
    "I need help with this slide deck.",
    "I need help with this pitch.",
    "I need help with this proposal deck.",
    "I need help with this briefing.",
    "I need help with my briefing.",
    "I need help with my follow-up.",
    "I need help with my agenda for tomorrow.",
]
for prompt in prompts:
    print(f"PROMPT: {prompt}")
    print(generate_companion_fallback(prompt, packet))
    print("---")
PY
```

## Exact results

Key preserved strong families:
- inbox prompts land on the inbox fork
- tomorrow-prep and tomorrow-planning prompts land on the tomorrow fork
- meeting prompts land on the meeting fork
- agenda prompts land on the agenda fork
- `this` presentation / proposal / slide-deck / pitch / proposal-deck prompts land on the presentation fork
- drafting prompts land on the drafting fork
- decision prompts land on the decision fork
- hard-conversation prompts land on the hard-conversation fork
- constraints-scheduling prompts land on the constraints-aware planning fork

Key remaining possessive presentation-prep weakness:
- the seven possessive prompts above all still fall to the generic practical sorter
- the parallel `this ...` prompts already land on the correct concrete presentation-shaping fork

Adjacent but lower-value remaining misses:
- `I need help with this briefing.` -> generic practical sorter
- `I need help with my briefing.` -> generic practical sorter
- `I need help with my follow-up.` -> generic practical sorter
- `I need help with my agenda for tomorrow.` -> generic practical sorter

## Clear Architect recommendation

Recommend the next bounded slice only:

**Post-Epic 9 slice 104: Companion Possessive Presentation-Prep Opener Hardening**

Suggested bounded scope:
- stay only inside the smallest existing first-turn companion opener seam in `jarvis/companion_spine.py`
- harden natural possessive presentation/prep phrasing so it lands on the existing concrete presentation-shaping fork
- preserve inbox, meeting, agenda, tomorrow-planning, drafting, decision, hard-conversation, and constraints-scheduling seams unchanged
- add only focused opener tests for the possessive presentation family and preserved nearby controls

Why this next:
- it is the strongest remaining first-turn chief-of-staff weakness in current repo truth
- it affects a broader natural family than the remaining `briefing` / `follow-up` / `agenda for tomorrow` misses
- the truthful destination is already established by the approved `this presentation / proposal / slide deck / pitch` seam
