# Post-Epic 9 Slice 107: Fresh Live-Use Weakness Reassessment

Ready for Architect Office review: yes

## Exact prompts or routes inspected

Bounded first-turn prompt set inspected:
- `I need help with my inbox.`
- `I need help planning tomorrow.`
- `I need help with this meeting.`
- `I need help with this agenda.`
- `I need help with my agenda for tomorrow.`
- `I need help setting my agenda for tomorrow.`
- `Help me set my agenda for tomorrow.`
- `I need help with tomorrow's agenda.`
- `I need help with this briefing.`
- `I need help with my briefing.`
- `I need help writing a briefing.`
- `I need help preparing a briefing.`
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
- `I need help with this presentation.`
- `I need help with my presentation.`

## Exact code seams inspected

Code seams inspected:
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:321)
  - `generate_companion_fallback(...)`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:671)
  - `_is_follow_up_request(...)`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:705)
  - `_is_agenda_request(...)`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:717)
  - `_is_tomorrow_planning_request(...)`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:1250)
  - `_generic_practical_fallback_reply(...)`

## Strongest remaining defect found

The strongest remaining first-turn chief-of-staff usefulness defect is the agenda-for-tomorrow family.

Current repo-truth behavior:
- `I need help with my agenda for tomorrow.`
  - `Let's make it concrete. Is this mostly a decision, a conversation, or a plan you need to sort out first?`
- `I need help setting my agenda for tomorrow.`
  - `Let's make it concrete. Is this mostly a decision, a conversation, or a plan you need to sort out first?`
- `Help me set my agenda for tomorrow.`
  - `Let's make it concrete. Is this mostly a decision, a conversation, or a plan you need to sort out first?`

Nearby repo-truth evidence shows this family should be sharper than that:
- `I need help with this agenda.` already lands on the agenda fork
- `I need help planning tomorrow.` already lands on the tomorrow-planning fork
- `I need help with tomorrow's agenda.` already lands on the tomorrow-planning fork

Why this is a real defect:
- agenda-setting for tomorrow is a common chief-of-staff first-turn ask
- several natural phrasings still hit the generic practical sorter
- the truthful destination is already strongly implied by the combination of the agenda seam and tomorrow-planning seam

## Why it is higher value than adjacent options

The agenda-for-tomorrow family is higher value than the nearby remaining misses because it is both operationally central and anchored to already-approved neighboring seams.

Compared with adjacent options:
- `briefing` prompts:
  - still generic, but less clearly central to everyday chief-of-staff use
  - also less clearly tied to one already-proven truthful destination
- `calendar tomorrow` / `schedule tomorrow`:
  - currently land on the capacity fork rather than the generic practical sorter
- day-planning prompts:
  - already land on the overloaded-week or capacity seams

Agenda-for-tomorrow is the cleanest next slice because it has multiple natural phrasings and a clear existing product direction: tomorrow structure plus agenda shaping.

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
    "I need help with this meeting.",
    "I need help with this agenda.",
    "I need help with my agenda for tomorrow.",
    "I need help setting my agenda for tomorrow.",
    "Help me set my agenda for tomorrow.",
    "I need help with tomorrow's agenda.",
    "I need help with this briefing.",
    "I need help with my briefing.",
    "I need help writing a briefing.",
    "I need help preparing a briefing.",
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
    "I need help with this presentation.",
    "I need help with my presentation.",
]
for prompt in prompts:
    print(f"PROMPT: {prompt}")
    print(generate_companion_fallback(prompt, packet))
    print("---")
PY

rg -n "def generate_companion_fallback|_is_follow_up_request|_is_presentation_or_proposal_prep_request|_is_agenda_request|_is_inbox_request|_is_meeting_prep_request|_is_constraints_scheduling_request|_is_tomorrow_planning_request|_generic_practical_fallback_reply|_request_needs_practical_handle|briefing|agenda for tomorrow|tomorrow's agenda|calendar tomorrow|schedule tomorrow" jarvis/companion_spine.py tests/test_companion_spine.py
```

## Exact results

Key preserved strong families:
- inbox prompts land on the inbox fork
- tomorrow-prep and tomorrow-planning prompts land on the tomorrow fork
- meeting prompts land on the meeting fork
- plain agenda prompts land on the agenda fork
- follow-up prompts land on the follow-up fork
- presentation / proposal prompts land on the presentation fork
- drafting prompts land on the drafting fork
- decision prompts land on the decision fork
- hard-conversation prompts land on the hard-conversation fork
- constraints-scheduling prompts land on the constraints-scheduling fork

Key remaining agenda-for-tomorrow weakness:
- the three agenda-for-tomorrow prompts above still fall to the generic practical sorter
- `tomorrow's agenda` already lands on the tomorrow fork
- plain `this agenda` already lands on the agenda fork

Adjacent but lower-value remaining misses:
- `I need help with this briefing.` -> generic practical sorter
- `I need help with my briefing.` -> generic practical sorter
- `I need help writing a briefing.` -> generic practical sorter
- `I need help preparing a briefing.` -> generic practical sorter

## Clear Architect recommendation

Recommend the next bounded slice only:

**Post-Epic 9 slice 108: Companion Agenda-For-Tomorrow Opener Hardening**

Suggested bounded scope:
- stay only inside the smallest existing first-turn companion opener seam in `jarvis/companion_spine.py`
- harden natural agenda-for-tomorrow phrasing so it lands on one truthful concrete fork instead of the generic practical sorter
- preserve inbox, meeting, plain-agenda, tomorrow-planning, follow-up, presentation, drafting, decision, hard-conversation, and constraints-scheduling seams unchanged
- add only focused opener tests for the agenda-for-tomorrow family and preserved nearby controls

Why this next:
- it is the strongest remaining first-turn chief-of-staff weakness in current repo truth
- it affects several natural phrasings, not one isolated alias
- the product direction is already proven by neighboring agenda and tomorrow-planning seams
