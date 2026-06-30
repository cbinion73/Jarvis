# Post-Epic 9 Slice 109: Fresh Live-Use Weakness Reassessment

Ready for Architect Office review: yes

## Exact prompts or routes inspected

Bounded first-turn prompt set inspected:
- `I need help with my inbox.`
- `I need help planning tomorrow.`
- `I need help with this meeting.`
- `I need help with this agenda.`
- `I need help with my agenda for tomorrow.`
- `I need help with my follow-up.`
- `I need help with this presentation.`
- `I need help with my presentation.`
- `I need help with this briefing.`
- `I need help with my briefing.`
- `I need help writing a briefing.`
- `I need help preparing a briefing.`
- `I need help with a briefing.`
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
- `I need help preparing notes for tomorrow.`
- `I need help with my talking points.`
- `I need help with my talking points for tomorrow.`
- `I need help getting ready for this briefing.`
- `I need help getting ready for my briefing.`

## Exact code seams inspected

Code seams inspected:
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:321)
  - `generate_companion_fallback(...)`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:684)
  - `_is_presentation_or_proposal_prep_request(...)`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:705)
  - `_is_agenda_request(...)`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:717)
  - `_is_tomorrow_planning_request(...)`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:1253)
  - `_generic_practical_fallback_reply(...)`

## Strongest remaining defect found

The strongest remaining first-turn chief-of-staff usefulness defect is the briefing-prep family.

Current repo-truth behavior:
- `I need help with this briefing.`
  - `Let's make it concrete. Is this mostly a decision, a conversation, or a plan you need to sort out first?`
- `I need help with my briefing.`
  - `Let's make it concrete. Is this mostly a decision, a conversation, or a plan you need to sort out first?`
- `I need help writing a briefing.`
  - `Let's make it concrete. Is this mostly a decision, a conversation, or a plan you need to sort out first?`
- `I need help preparing a briefing.`
  - `Let's make it concrete. Is this mostly a decision, a conversation, or a plan you need to sort out first?`
- `I need help with a briefing.`
  - `Let's make it concrete. Is this mostly a decision, a conversation, or a plan you need to sort out first?`
- `I need help getting ready for this briefing.`
  - `Let's make it concrete. Is this mostly a decision, a conversation, or a plan you need to sort out first?`
- `I need help getting ready for my briefing.`
  - `Let's make it concrete. Is this mostly a decision, a conversation, or a plan you need to sort out first?`

Adjacent repo-truth evidence suggests this family should be sharper than that:
- presentation / proposal / slide-deck / pitch prompts already land on the concrete presentation-shaping fork
- the current presentation fork wording already fits briefing-like prep work:
  - `the point you need to land`
  - `the structure`
  - `getting ready to deliver it cleanly`

Why this is a real defect:
- briefing prep is a common chief-of-staff ask
- the family has several natural phrasings, not one isolated alias
- the current generic practical sorter underserves a deliverable-prep problem that already has a nearby truthful destination

## Why it is higher value than adjacent options

The briefing-prep family is higher value than the nearby remaining misses because it is broader and more clearly anchored to an already-approved neighboring seam.

Compared with adjacent options:
- `talking points` / `notes for tomorrow`:
  - still generic, but narrower and more semantically ambiguous
  - may partly overlap with the same prep family, but are less direct than `briefing`
- `calendar tomorrow` / `schedule tomorrow`:
  - already land on the capacity fork rather than the generic practical sorter
- day-planning prompts:
  - already land on overloaded-week or capacity forks

This makes briefing-prep the clearest next slice: several practical phrasings still miss, and the most truthful destination is already proven by the presentation-prep seam.

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
    "I need help with my follow-up.",
    "I need help with this presentation.",
    "I need help with my presentation.",
    "I need help with this briefing.",
    "I need help with my briefing.",
    "I need help writing a briefing.",
    "I need help preparing a briefing.",
    "I need help with a briefing.",
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
    "I need help preparing notes for tomorrow.",
    "I need help with my talking points.",
    "I need help with my talking points for tomorrow.",
    "I need help getting ready for this briefing.",
    "I need help getting ready for my briefing.",
]
for prompt in prompts:
    print(f"PROMPT: {prompt}")
    print(generate_companion_fallback(prompt, packet))
    print("---")
PY

rg -n "def generate_companion_fallback|_is_follow_up_request|_is_presentation_or_proposal_prep_request|_is_agenda_request|_is_inbox_request|_is_meeting_prep_request|_is_constraints_scheduling_request|_is_tomorrow_planning_request|_generic_practical_fallback_reply|_request_needs_practical_handle|briefing|talking points|notes for tomorrow|calendar tomorrow|schedule tomorrow" jarvis/companion_spine.py tests/test_companion_spine.py
```

## Exact results

Key preserved strong families:
- inbox prompts land on the inbox fork
- tomorrow-prep and tomorrow-planning prompts land on the tomorrow fork
- meeting prompts land on the meeting fork
- agenda-for-tomorrow prompts land on the tomorrow fork
- follow-up prompts land on the follow-up fork
- presentation / proposal / slide-deck / pitch prompts land on the presentation fork
- drafting prompts land on the drafting fork
- decision prompts land on the decision fork
- hard-conversation prompts land on the hard-conversation fork
- constraints-scheduling prompts land on the constraints-scheduling fork

Key remaining briefing-prep weakness:
- the seven briefing prompts above still fall to the generic practical sorter
- the current presentation-prep fork already offers a plausible truthful structure for this family

Adjacent but lower-value remaining misses:
- `I need help preparing notes for tomorrow.` -> generic practical sorter
- `I need help with my talking points.` -> generic practical sorter
- `I need help with my talking points for tomorrow.` -> generic practical sorter

## Clear Architect recommendation

Recommend the next bounded slice only:

**Post-Epic 9 slice 110: Companion Briefing-Prep Opener Hardening**

Suggested bounded scope:
- stay only inside the smallest existing first-turn companion opener seam in `jarvis/companion_spine.py`
- harden natural briefing-prep phrasing so it lands on one truthful concrete prep fork instead of the generic practical sorter
- preserve inbox, meeting, agenda, tomorrow-planning, follow-up, presentation, drafting, decision, hard-conversation, and constraints-scheduling seams unchanged
- add only focused opener tests for the briefing-prep family and preserved nearby controls

Why this next:
- it is the strongest remaining first-turn chief-of-staff weakness in current repo truth
- it affects several natural phrasings, not one isolated alias
- the product direction is already strongly suggested by the existing presentation-prep fork
