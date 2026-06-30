# Post-Epic 9 Slice 101: Fresh Live-Use Weakness Reassessment

Ready for Architect Office review: yes

## Exact prompts or routes inspected

Bounded first-turn prompt set inspected:
- `I need help with my inbox.`
- `I need help planning tomorrow.`
- `I need help with this meeting.`
- `I need help with this agenda.`
- `I need help with this presentation.`
- `I need help with this slide deck.`
- `I need help with this pitch.`
- `I need help drafting an email to my boss.`
- `I need help writing a follow-up email after this meeting.`
- `I need help deciding between two apartments.`
- `I need help with a hard conversation.`
- `I need help scheduling around constraints.`
- `I need help prioritizing this week.`
- `I need help with my priorities for this week.`
- `I need help with my schedule.`
- `I need help with my calendar.`
- `I need help planning my week.`
- `I need help organizing this week.`
- `I need help getting my week under control.`
- `I need help planning my day.`
- `I need help with my day.`
- `I need help setting priorities.`
- `I need help with this follow-up.`
- `I need help with this proposal deck.`
- `I need help with this briefing.`
- `I need help preparing for tomorrow.`
- `I need help getting ready for tomorrow.`
- `Help me get ready for tomorrow.`
- `I need to get ready for tomorrow.`
- `I need help with tomorrow.`
- `I need help with tomorrow's plan.`
- `I need help with tomorrow morning.`
- `I need help with my follow-up.`
- `I need help with a follow-up.`
- `I need help following up after this meeting.`
- `I need help with a briefing.`
- `I need help with my briefing.`
- `I need help with my proposal deck.`
- `I need help with my slide deck.`
- `I need help with my pitch.`
- `I need help with my agenda for tomorrow.`
- `I need help with my calendar tomorrow.`
- `I need help with my schedule tomorrow.`

## Exact code seams inspected

Code seams inspected:
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:321)
  - `generate_companion_fallback(...)`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:548)
  - `_request_needs_practical_handle(...)`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:691)
  - `_is_tomorrow_planning_request(...)`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:1218)
  - `_generic_practical_fallback_reply(...)`

## Strongest remaining defect found

The strongest remaining first-turn chief-of-staff usefulness defect is the tomorrow-prep family.

Current repo-truth behavior:
- `I need help preparing for tomorrow.`
  - `Let's make it concrete. Is this mostly a decision, a conversation, or a plan you need to sort out first?`
- `I need help getting ready for tomorrow.`
  - `Let's make it concrete. Is this mostly a decision, a conversation, or a plan you need to sort out first?`
- `Help me get ready for tomorrow.`
  - `Let's make it concrete. Is this mostly a decision, a conversation, or a plan you need to sort out first?`
- `I need to get ready for tomorrow.`
  - `I'm here. Give me the short version, or tell me which part feels off.`
- `I need help with tomorrow.`
  - `Let's make it concrete. Is this mostly a decision, a conversation, or a plan you need to sort out first?`
- `I need help with tomorrow's plan.`
  - `Let's make it concrete. Is this mostly a decision, a conversation, or a plan you need to sort out first?`
- `I need help with tomorrow morning.`
  - `Let's make it concrete. Is this mostly a decision, a conversation, or a plan you need to sort out first?`

Why this is a real defect:
- these are natural chief-of-staff asks about getting tomorrow under control
- the current repo already has a truthful adjacent fork for tomorrow planning:
  - `I need help planning tomorrow.` -> `Good. For tomorrow, what actually has to happen, what is fixed, and what can slip?`
- one variant, `I need to get ready for tomorrow.`, misses even the generic practical sorter and falls all the way to the non-practical fallback

## Why it is higher value than adjacent options

Tomorrow-prep is higher value than the nearby remaining options because it is both more practical and more central to everyday live use.

Compared with adjacent misses:
- possessive slide-deck / pitch / proposal-deck variants:
  - still miss in some phrasing, but they are narrower and less central than tomorrow-prep
- follow-up / briefing phrasing:
  - still generic, but less clearly anchored to an already-strong neighboring fork
- calendar-tomorrow / schedule-tomorrow phrasing:
  - currently lands on the existing capacity fork, so it is not as weak as tomorrow-prep

Tomorrow-prep is the clearest remaining family where several natural phrasings all miss while the truthful destination is already implied by an approved nearby seam.

## Whether code/tests changed or next bounded slice only

No code or tests were changed in this slice.

This is a recommendation-only reassessment. The defect is concrete, but it is cleaner to isolate it as its own bounded opener-hardening slice than to combine assessment plus repair here.

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
    "I need help with this presentation.",
    "I need help with this slide deck.",
    "I need help with this pitch.",
    "I need help drafting an email to my boss.",
    "I need help writing a follow-up email after this meeting.",
    "I need help deciding between two apartments.",
    "I need help with a hard conversation.",
    "I need help scheduling around constraints.",
    "I need help prioritizing this week.",
    "I need help with my priorities for this week.",
    "I need help with my schedule.",
    "I need help with my calendar.",
    "I need help planning my week.",
    "I need help organizing this week.",
    "I need help getting my week under control.",
    "I need help planning my day.",
    "I need help with my day.",
    "I need help setting priorities.",
    "I need help with this follow-up.",
    "I need help with this proposal deck.",
    "I need help with this briefing.",
    "I need help preparing for tomorrow.",
    "I need help figuring out my day.",
]
for prompt in prompts:
    print(f"PROMPT: {prompt}")
    print(generate_companion_fallback(prompt, packet))
    print("---")
PY

rg -n "def generate_companion_fallback|_is_presentation_or_proposal_prep_request|_is_agenda_request|_is_inbox_request|_is_meeting_prep_request|_is_constraints_scheduling_request|_is_tomorrow_planning_request|_generic_practical_fallback_reply|_request_needs_practical_handle|calendar|schedule|priorit" jarvis/companion_spine.py tests/test_companion_spine.py

python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
prompts = [
    "I need help preparing for tomorrow.",
    "I need help getting ready for tomorrow.",
    "Help me get ready for tomorrow.",
    "I need to get ready for tomorrow.",
    "I need help with tomorrow.",
    "I need help with tomorrow's plan.",
    "I need help with tomorrow morning.",
    "I need help with my follow-up.",
    "I need help with this follow-up.",
    "I need help with a follow-up.",
    "I need help following up after this meeting.",
    "I need help with this briefing.",
    "I need help with a briefing.",
    "I need help with my briefing.",
    "I need help with my proposal deck.",
    "I need help with my slide deck.",
    "I need help with my pitch.",
    "I need help with my agenda for tomorrow.",
    "I need help with my calendar tomorrow.",
    "I need help with my schedule tomorrow.",
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
- meeting prompts land on the meeting fork
- agenda prompts land on the agenda fork
- presentation / proposal / `this slide deck` / `this pitch` land on the presentation fork
- drafting prompts land on the drafting fork
- decision prompts land on the decision fork
- hard-conversation prompts land on the hard-conversation fork
- constraints-scheduling prompts land on the constraints-aware planning fork

Key remaining tomorrow-prep weakness:
- all the tomorrow-prep phrasings above still miss the existing tomorrow-planning fork
- three of them fall to the generic practical sorter
- one of them, `I need to get ready for tomorrow.`, falls to the generic non-practical fallback

Adjacent but lower-value remaining misses:
- `I need help with my slide deck.` -> generic practical sorter
- `I need help with my pitch.` -> generic practical sorter
- `I need help with my proposal deck.` -> generic practical sorter
- `I need help with this briefing.` -> generic practical sorter
- `I need help with my follow-up.` -> generic practical sorter

## Clear Architect recommendation

Recommend the next bounded slice only:

**Post-Epic 9 slice 102: Companion Tomorrow-Prep Opener Hardening**

Suggested bounded scope:
- stay only inside the smallest existing first-turn companion opener seam in `jarvis/companion_spine.py`
- harden natural tomorrow-prep phrasing so it lands on the existing concrete tomorrow-planning fork
- preserve existing inbox, meeting, agenda, presentation, drafting, decision, hard-conversation, and constraints-scheduling seams unchanged
- add only focused opener tests for the tomorrow-prep family and preserved nearby controls

Why this next:
- it is the strongest remaining first-turn chief-of-staff weakness in current repo truth
- it affects several natural phrasings rather than one isolated alias
- the truthful destination is already established by the approved tomorrow-planning seam
