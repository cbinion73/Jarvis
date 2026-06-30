# Post-Epic 9 Slice 105: Fresh Live-Use Weakness Reassessment

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
- `I need help with my presentation.`
- `I need help with this briefing.`
- `I need help with my briefing.`
- `I need help with this follow-up.`
- `I need help with my follow-up.`
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
- `I need help with my proposal deck.`
- `I need help with my pitch.`
- `I need help with my slide deck.`
- `I need help with my proposal.`

Additional targeted comparison prompts:
- `I need help with the follow-up.`
- `I need help with a follow-up.`
- `I need help with my meeting follow-up.`
- `I need help with this meeting follow-up.`
- `I need help following up with my boss.`
- `I need help writing a briefing.`
- `I need help preparing a briefing.`
- `I need help setting my agenda for tomorrow.`
- `Help me set my agenda for tomorrow.`
- `I need help with tomorrow's agenda.`

## Exact code seams inspected

Code seams inspected:
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:321)
  - `generate_companion_fallback(...)`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:548)
  - `_request_needs_practical_handle(...)`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:630)
  - `_is_meeting_prep_request(...)`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:666)
  - `_is_presentation_or_proposal_prep_request(...)`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:687)
  - `_is_agenda_request(...)`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:699)
  - `_is_tomorrow_planning_request(...)`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:1232)
  - `_generic_practical_fallback_reply(...)`

## Strongest remaining defect found

The strongest remaining first-turn chief-of-staff usefulness defect is the follow-up family.

Current repo-truth behavior:
- `I need help with my follow-up.`
  - `Let's make it concrete. Is this mostly a decision, a conversation, or a plan you need to sort out first?`
- `I need help with this follow-up.`
  - `Let's make it concrete. Is this mostly a decision, a conversation, or a plan you need to sort out first?`
- `I need help following up after this meeting.`
  - `Let's make it concrete. Is this mostly a decision, a conversation, or a plan you need to sort out first?`
- `I need help with the follow-up.`
  - `Let's make it concrete. Is this mostly a decision, a conversation, or a plan you need to sort out first?`
- `I need help with a follow-up.`
  - `Let's make it concrete. Is this mostly a decision, a conversation, or a plan you need to sort out first?`
- `I need help with my meeting follow-up.`
  - `Let's make it concrete. Is this mostly a decision, a conversation, or a plan you need to sort out first?`

Nearby repo-truth evidence shows the family should be sharper than that:
- `I need help with this meeting follow-up.` already lands on the meeting fork
- `I need help writing a follow-up email after this meeting.` already lands on the drafting fork

Why this is a real defect:
- follow-up is a high-frequency chief-of-staff ask in ordinary live use
- the family has several natural phrasings, not one isolated alias
- the current sorter reply is too generic given the strength of nearby meeting and drafting seams

## Why it is higher value than adjacent options

The follow-up family is higher value than the nearby remaining misses because it is both broader and more operationally central.

Compared with adjacent options:
- `briefing` prompts:
  - still generic, but less clearly central to everyday companion use
  - also less grounded to already-proven neighboring seams than follow-up
- `my agenda for tomorrow` prompts:
  - still generic in some phrasings, but narrower as a family
  - `tomorrow's agenda` already lands on the tomorrow-planning fork
- `calendar tomorrow` / `schedule tomorrow`:
  - currently land on the capacity fork rather than the generic practical sorter

Follow-up is the clearest next slice because it has multiple natural first-turn phrasings, touches common chief-of-staff behavior, and sits directly between already-approved meeting and drafting seams.

## Whether code/tests changed or next bounded slice only

No code or tests changed in this slice.

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
    "I need help with my presentation.",
    "I need help with this briefing.",
    "I need help with my briefing.",
    "I need help with this follow-up.",
    "I need help with my follow-up.",
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
    "I need help with my proposal deck.",
    "I need help with my pitch.",
    "I need help with my slide deck.",
    "I need help with my proposal.",
]
for prompt in prompts:
    print(f"PROMPT: {prompt}")
    print(generate_companion_fallback(prompt, packet))
    print("---")
PY

rg -n "def generate_companion_fallback|_is_presentation_or_proposal_prep_request|_is_agenda_request|_is_inbox_request|_is_meeting_prep_request|_is_constraints_scheduling_request|_is_tomorrow_planning_request|_generic_practical_fallback_reply|_request_needs_practical_handle|briefing|follow-up|agenda for tomorrow|calendar tomorrow|schedule tomorrow" jarvis/companion_spine.py tests/test_companion_spine.py

python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
prompts = [
    "I need help with my follow-up.",
    "I need help with this follow-up.",
    "I need help following up after this meeting.",
    "I need help with the follow-up.",
    "I need help with a follow-up.",
    "I need help with my meeting follow-up.",
    "I need help with this meeting follow-up.",
    "I need help following up with my boss.",
    "I need help with my briefing.",
    "I need help with this briefing.",
    "I need help writing a briefing.",
    "I need help preparing a briefing.",
    "I need help with my agenda for tomorrow.",
    "I need help setting my agenda for tomorrow.",
    "Help me set my agenda for tomorrow.",
    "I need help with tomorrow's agenda.",
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
- presentation / proposal / slide-deck / pitch / proposal-deck prompts land on the presentation fork
- drafting prompts land on the drafting fork
- decision prompts land on the decision fork
- hard-conversation prompts land on the hard-conversation fork
- constraints-scheduling prompts land on the constraints-aware planning fork

Key remaining follow-up weakness:
- the six follow-up prompts above still fall to the generic practical sorter
- `this meeting follow-up` already lands on the meeting fork
- `follow-up email after this meeting` already lands on the drafting fork

Adjacent but lower-value remaining misses:
- `I need help with this briefing.` -> generic practical sorter
- `I need help with my briefing.` -> generic practical sorter
- `I need help writing a briefing.` -> generic practical sorter
- `I need help preparing a briefing.` -> generic practical sorter
- `I need help with my agenda for tomorrow.` -> generic practical sorter
- `I need help setting my agenda for tomorrow.` -> generic practical sorter

## Clear Architect recommendation

Recommend the next bounded slice only:

**Post-Epic 9 slice 106: Companion Follow-Up Opener Hardening**

Suggested bounded scope:
- stay only inside the smallest existing first-turn companion opener seam in `jarvis/companion_spine.py`
- harden natural follow-up phrasing so it lands on one truthful concrete fork rather than the generic practical sorter
- preserve inbox, meeting, agenda, tomorrow-planning, presentation, drafting, decision, hard-conversation, and constraints-scheduling seams unchanged
- add only focused opener tests for the follow-up family and preserved nearby controls

Why this next:
- it is the strongest remaining first-turn chief-of-staff weakness in current repo truth
- it affects several natural phrasings, not one isolated alias
- it sits directly adjacent to already-approved meeting and drafting seams, so the product value is higher than the remaining `briefing` or `agenda for tomorrow` families
