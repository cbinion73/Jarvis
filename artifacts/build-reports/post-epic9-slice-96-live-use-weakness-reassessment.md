# Post-Epic 9 Slice 96: Live-Use Weakness Reassessment

Ready for Architect Office review: yes

## Exact prompts or routes inspected

Companion first-turn prompts inspected:
- `I need help with this presentation.`
- `I need help getting ready for this presentation.`
- `I need help with this proposal.`
- `I need help getting ready for this proposal.`
- `I need help with this agenda.`
- `I need help setting the agenda.`
- `Set the agenda with me.`
- `I need help with this meeting agenda.`
- `I need help with this meeting.`
- `I need help with my priorities.`
- `I need help planning my day.`
- `I need help scheduling around two meetings.`
- `I need help scheduling around constraints.`
- `I need help scheduling around my constraints.`
- `I need help planning around constraints.`
- `I need help planning around two meetings.`
- `I need help with this meeting follow-up.`
- `I need help drafting an email to my boss.`
- `I need help with a hard conversation.`
- `I need help deciding between two apartments.`
- `I need help planning tomorrow.`

Code seams inspected:
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:321)
  - `generate_companion_fallback(...)`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:424)
  - meeting opener fork
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:1208)
  - `_generic_practical_fallback_reply(...)`

## Strongest remaining defect found

The strongest remaining first-turn chief-of-staff weakness is agenda phrasing outside the meeting seam.

Current repo-truth behavior:
- `I need help with this agenda.`  
  - `Let's make it concrete. Is this mostly a decision, a conversation, or a plan you need to sort out first?`
- `I need help setting the agenda.`  
  - `Let's make it concrete. Is this mostly a decision, a conversation, or a plan you need to sort out first?`
- `Set the agenda with me.`  
  - `I'm here. Give me the short version, or tell me which part feels off.`

Why this is a real defect:
- these are natural chief-of-staff first turns
- the current behavior ranges from generic practical sorting to generic non-practical fallback
- the adjacent meeting seam already proves JARVIS has a truthful, concrete way to talk about agenda work when the phrasing explicitly says `meeting agenda`

## Why it is higher value than adjacent options

Agenda phrasing outside the meeting seam is higher value than the nearby remaining options because it is both more concrete and more directly connected to an already-approved neighboring seam.

Compared with adjacent options:
- scheduling around constraints:
  - still weak, but broader and less clearly scoped for one next bounded opener slice
- priorities / planning-day variants:
  - already have stronger nearby capacity and tomorrow-planning behavior
- presentation / proposal prep:
  - now repaired

Agenda is the clearest remaining family where:
- multiple natural prompts still miss
- one prompt (`Set the agenda with me.`) still falls all the way to the generic non-practical fallback
- there is an obvious truthful neighboring seam to align with without broad architecture changes

## Whether code/tests changed or next bounded slice only

No code or tests were changed in this slice.

This is a recommendation-only reassessment. The defect is concrete, but it is cleaner to give agenda phrasing its own bounded opener-hardening slice than to combine assessment plus implementation here.

## Exact commands run

```bash
python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
prompts = [
    "I need help with this presentation.",
    "I need help getting ready for this presentation.",
    "I need help with this proposal.",
    "I need help getting ready for this proposal.",
    "I need help with this agenda.",
    "I need help setting the agenda.",
    "I need help with my priorities.",
    "I need help planning my day.",
    "I need help scheduling around two meetings.",
    "I need help scheduling around constraints.",
    "I need help scheduling around my constraints.",
    "I need help planning around constraints.",
    "I need help with this meeting agenda.",
    "I need help with this meeting.",
    "I need help with my inbox.",
    "I need help drafting an email to my boss.",
    "I need help with a hard conversation.",
    "I need help deciding between two apartments.",
    "I need help planning tomorrow.",
]
for prompt in prompts:
    reply = generate_companion_fallback(prompt, packet)
    print(f"PROMPT: {prompt}\nREPLY: {reply}\n")
PY
rg -n "presentation|proposal|agenda|priorities|planning my day|scheduling around two meetings|setting the agenda" jarvis/companion_spine.py tests/test_companion_spine.py
python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
prompts = [
    "I need help with this agenda.",
    "I need help setting the agenda.",
    "Set the agenda with me.",
    "I need help scheduling around two meetings.",
    "I need help scheduling around constraints.",
    "I need help scheduling around my constraints.",
    "I need help planning around constraints.",
    "I need help with this meeting agenda.",
    "I need help planning tomorrow.",
]
for prompt in prompts:
    reply = generate_companion_fallback(prompt, packet)
    print(f"PROMPT: {prompt}\nREPLY: {reply}\n")
PY
```

## Exact results

Key agenda-family results:
- `I need help with this agenda.` -> generic practical sorter
- `I need help setting the agenda.` -> generic practical sorter
- `Set the agenda with me.` -> generic non-practical fallback

Adjacent comparison evidence:
- meeting seam remains correct:
  - `I need help with this meeting agenda.` -> meeting fork
  - `I need help with this meeting.` -> meeting fork
- scheduling-around-constraints remains weak but broader:
  - `I need help scheduling around two meetings.` -> generic practical sorter
  - `I need help scheduling around constraints.` -> generic practical sorter
  - `I need help scheduling around my constraints.` -> generic practical sorter
  - `I need help planning around constraints.` -> generic practical sorter
- other hardened lanes remain correct:
  - `I need help with my priorities.` -> capacity pushback
  - `I need help planning my day.` -> overloaded-week fork
  - `I need help planning tomorrow.` -> tomorrow-planning fork
  - `I need help with my inbox.` -> inbox fork
  - `I need help drafting an email to my boss.` -> drafting fork
  - `I need help with a hard conversation.` -> hard-conversation fork
  - `I need help deciding between two apartments.` -> decision fork

## Clear Architect recommendation

Recommend the next bounded slice only:

**Post-Epic 9 slice 97: Companion Agenda Opener Usefulness Hardening**

Suggested bounded scope:
- stay only inside the smallest existing first-turn companion opener seam in `jarvis/companion_spine.py`
- harden natural agenda phrasing outside the explicit meeting seam so it lands on one concrete agenda-shaped fork
- preserve the existing meeting, inbox, drafting, decision, conversation, and tomorrow-planning seams unchanged
- add only focused opener tests for the agenda family and preserved nearby controls

Why this next:
- it is the strongest remaining first-turn chief-of-staff weakness in current repo truth
- it covers multiple natural prompts, including one that still falls to the generic non-practical fallback
- it has a clear truthful adjacent seam to align with without broad architecture changes
