# Post-Epic 9 Slice 98: Live-Use Weakness Reassessment

Ready for Architect Office review: yes

## Exact prompts or routes inspected

Companion first-turn prompts inspected:
- `I need help with this agenda.`
- `I need help setting the agenda.`
- `Set the agenda with me.`
- `I need help planning my day.`
- `I need help with my day.`
- `I need help with today's plan.`
- `I need help with my priorities.`
- `I need help setting priorities.`
- `I need help prioritizing today.`
- `I need help scheduling around two meetings.`
- `I need help scheduling around constraints.`
- `I need help scheduling around my constraints.`
- `I need help planning around constraints.`
- `I need help with this slide deck.`
- `I need help with this pitch.`
- `I need help with this presentation.`
- `I need help with this proposal.`
- `I need help with this meeting agenda.`
- `I need help with this meeting.`
- `I need help with my inbox.`
- `I need help drafting an email to my boss.`
- `I need help with a hard conversation.`
- `I need help deciding between two apartments.`
- `I need help planning tomorrow.`

Code seams inspected:
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:321)
  - `generate_companion_fallback(...)`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:535)
  - `_request_needs_practical_handle(...)`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:1208)
  - `_generic_practical_fallback_reply(...)`

## Strongest remaining defect found

The strongest remaining first-turn chief-of-staff weakness is the scheduling-around-constraints family.

Current repo-truth behavior:
- `I need help scheduling around two meetings.`  
  - `Let's make it concrete. Is this mostly a decision, a conversation, or a plan you need to sort out first?`
- `I need help scheduling around constraints.`  
  - `Let's make it concrete. Is this mostly a decision, a conversation, or a plan you need to sort out first?`
- `I need help scheduling around my constraints.`  
  - `Let's make it concrete. Is this mostly a decision, a conversation, or a plan you need to sort out first?`
- `I need help planning around constraints.`  
  - `Let's make it concrete. Is this mostly a decision, a conversation, or a plan you need to sort out first?`

Why this is a real defect:
- these are natural chief-of-staff asks about working around fixed commitments or limits
- the current behavior is still the generic practical sorter for every prompt in the family
- nearby operational seams are already sharper:
  - `I need help planning tomorrow.` -> tomorrow-planning fork
  - `I need help with my priorities.` -> capacity pushback
  - `I need help planning my day.` -> overloaded-week fork

## Why it is higher value than adjacent options

Scheduling-around-constraints is higher value than the nearby remaining options because it is broader, more operational, and clearly underserved.

Compared with adjacent options:
- slide deck / pitch wording:
  - still weak, but narrower and less central than scheduling around constraints
  - also less proven than the now-hardened presentation / proposal prep family
- planning-day / priorities variants:
  - already have stronger nearby behavior through existing capacity and tomorrow-planning seams
- agenda family:
  - now repaired

This is the clearest remaining family where several natural phrasings still miss and where the current repo already suggests the truthful direction: concrete help around what is fixed versus what can move.

## Whether code/tests changed or next bounded slice only

No code or tests were changed in this slice.

This is a recommendation-only reassessment. The defect is concrete, but it is cleaner to give scheduling-around-constraints its own bounded opener-hardening slice than to combine assessment plus implementation here.

## Exact commands run

```bash
python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
prompts = [
    "I need help scheduling around two meetings.",
    "I need help scheduling around constraints.",
    "I need help scheduling around my constraints.",
    "I need help planning around constraints.",
    "I need help planning my day.",
    "I need help with my day.",
    "I need help with today's plan.",
    "I need help with my priorities.",
    "I need help setting priorities.",
    "I need help prioritizing today.",
    "I need help with this slide deck.",
    "I need help with this pitch.",
    "I need help with a hard conversation.",
    "I need help drafting an email to my boss.",
    "I need help with my inbox.",
    "I need help planning tomorrow.",
    "I need help with this presentation.",
    "I need help with this agenda.",
]
for prompt in prompts:
    reply = generate_companion_fallback(prompt, packet)
    print(f"PROMPT: {prompt}\nREPLY: {reply}\n")
PY
rg -n "scheduling around|constraints|planning my day|today's plan|setting priorities|prioritizing today|slide deck|pitch" jarvis/companion_spine.py tests/test_companion_spine.py
python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
prompts = [
    "I need help scheduling around two meetings.",
    "I need help scheduling around constraints.",
    "I need help scheduling around my constraints.",
    "I need help planning around constraints.",
    "I need help with this slide deck.",
    "I need help with this pitch.",
    "I need help with this presentation.",
    "I need help planning tomorrow.",
]
for prompt in prompts:
    reply = generate_companion_fallback(prompt, packet)
    print(f"PROMPT: {prompt}\nREPLY: {reply}\n")
PY
```

## Exact results

Key scheduling-around-constraints results:
- `I need help scheduling around two meetings.` -> generic practical sorter
- `I need help scheduling around constraints.` -> generic practical sorter
- `I need help scheduling around my constraints.` -> generic practical sorter
- `I need help planning around constraints.` -> generic practical sorter

Comparison evidence from adjacent families:
- planning-day / priorities are already stronger:
  - `I need help planning my day.` -> overloaded-week fork
  - `I need help with my day.` -> overloaded-week fork
  - `I need help with today's plan.` -> overloaded-week fork
  - `I need help with my priorities.` -> capacity pushback
  - `I need help setting priorities.` -> capacity pushback
- slide deck / pitch are still weak but narrower:
  - `I need help with this slide deck.` -> generic practical sorter
  - `I need help with this pitch.` -> generic practical sorter
- preserved hardened lanes remain correct:
  - `I need help with a hard conversation.` -> hard-conversation fork
  - `I need help drafting an email to my boss.` -> drafting fork
  - `I need help with my inbox.` -> inbox fork
  - `I need help planning tomorrow.` -> tomorrow-planning fork
  - `I need help with this presentation.` -> presentation/proposal prep fork
  - `I need help with this agenda.` -> agenda fork

## Clear Architect recommendation

Recommend the next bounded slice only:

**Post-Epic 9 slice 99: Companion Scheduling-Around-Constraints Opener Hardening**

Suggested bounded scope:
- stay only inside the smallest existing first-turn companion opener seam in `jarvis/companion_spine.py`
- harden natural scheduling-around-constraints phrasing so it lands on one concrete constraints-aware planning fork
- preserve the existing tomorrow-planning, inbox, meeting, agenda, drafting, decision, and hard-conversation seams unchanged
- add only focused opener tests for the constraints-scheduling family and preserved nearby controls

Why this next:
- it is the strongest remaining first-turn chief-of-staff weakness in current repo truth
- it affects several natural phrasings, not just one alias
- it is more operationally important than the remaining slide deck / pitch misses
