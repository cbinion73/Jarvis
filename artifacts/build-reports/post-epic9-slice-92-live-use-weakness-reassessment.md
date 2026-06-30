# Post-Epic 9 Slice 92: Live-Use Weakness Reassessment

Ready for Architect Office review: yes

## Exact prompts or routes inspected

Companion first-turn prompts inspected:
- `I need help with my priorities.`
- `I need help planning tomorrow.`
- `I need help scheduling tomorrow.`
- `I need help organizing tomorrow.`
- `I need help planning around two meetings.`
- `I need help with this presentation.`
- `I need help getting ready for this presentation.`
- `I need help with this proposal.`
- `I need help getting ready for this proposal.`
- `I need help with this agenda.`
- `I need help with this meeting agenda.`
- `I need help with this meeting follow-up.`
- `I need help drafting an email to my boss.`
- `I need help with a hard conversation.`
- `I need help deciding between two apartments.`
- `I need to get tomorrow under control.`
- `I need help planning my day.`

Code seams inspected:
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:321)
  - `generate_companion_fallback(...)`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:535)
  - `_request_needs_practical_handle(...)`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:1208)
  - `_generic_practical_fallback_reply(...)`

## Strongest remaining defect found

The strongest remaining first-turn chief-of-staff weakness is the tomorrow-planning / tomorrow-scheduling opener family.

Current repo-truth behavior:
- `I need help planning tomorrow.`  
  - `Let's make it concrete. Is this mostly a decision, a conversation, or a plan you need to sort out first?`
- `I need help scheduling tomorrow.`  
  - `Let's make it concrete. Is this mostly a decision, a conversation, or a plan you need to sort out first?`
- `I need help organizing tomorrow.`  
  - `Let's make it concrete. Is this mostly a decision, a conversation, or a plan you need to sort out first?`
- `I need help planning around two meetings.`  
  - `Let's make it concrete. Is this mostly a decision, a conversation, or a plan you need to sort out first?`

Why this is a real defect:
- these are natural first-turn chief-of-staff asks
- they are more operational than the generic practical sorter suggests
- a closely adjacent variant already proves the seam wants to be sharper:
  - `I need to get tomorrow under control.`  
    - `You do not need a better plan yet. You need one cut. What actually has to happen, and what can slip?`

## Why it is higher value than adjacent options

Tomorrow-planning is higher value than the nearby remaining options because it combines operational importance with multiple natural phrasings and a clear truthful upgrade path.

Compared with adjacent options:
- presentation / proposal prep:
  - still weak, but narrower and less central than tomorrow planning
- generic `agenda` phrasing:
  - still generic, but `meeting agenda` is already covered by the meeting fork
- priorities:
  - already routes to a stronger capacity pushback

Tomorrow-planning is the clearest remaining family where the repo already shows the right direction through the stronger `get tomorrow under control` behavior, but the more natural phrasings still miss it.

## Whether code/tests changed or next bounded slice only

No code or tests were changed in this slice.

This is a recommendation-only reassessment. The defect is concrete, but it is cleaner to give tomorrow-planning its own bounded opener-hardening slice than to combine assessment plus implementation here.

## Exact commands run

```bash
python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
prompts = [
    "I need help with my priorities.",
    "I need help planning tomorrow.",
    "I need help scheduling tomorrow.",
    "I need help organizing tomorrow.",
    "I need help planning around two meetings.",
    "I need help with this presentation.",
    "I need help getting ready for this presentation.",
    "I need help with this proposal.",
    "I need help getting ready for this proposal.",
    "I need help with this agenda.",
    "I need help with this meeting agenda.",
    "I need help with this meeting follow-up.",
    "I need help drafting an email to my boss.",
    "I need help with a hard conversation.",
    "I need help deciding between two apartments.",
    "I need to get tomorrow under control.",
    "I need help planning my day.",
]
for prompt in prompts:
    reply = generate_companion_fallback(prompt, packet)
    print(f"PROMPT: {prompt}\nREPLY: {reply}\n")
PY
rg -n "priorities|planning tomorrow|scheduling tomorrow|organizing tomorrow|planning around two meetings|presentation|proposal|agenda" tests/test_companion_spine.py jarvis/companion_spine.py
```

## Exact results

Key tomorrow-planning results:
- `I need help planning tomorrow.` -> generic practical sorter
- `I need help scheduling tomorrow.` -> generic practical sorter
- `I need help organizing tomorrow.` -> generic practical sorter
- `I need help planning around two meetings.` -> generic practical sorter

Comparison evidence from adjacent families:
- `I need to get tomorrow under control.` -> capacity pushback
- `I need help planning my day.` -> stronger overloaded-week fork
- `I need help with my priorities.` -> capacity pushback
- `I need help with this presentation.` -> generic practical sorter
- `I need help getting ready for this presentation.` -> generic practical sorter
- `I need help with this proposal.` -> generic practical sorter
- `I need help getting ready for this proposal.` -> generic practical sorter
- `I need help with this agenda.` -> generic practical sorter
- preserved hardened lanes still behave correctly:
  - `I need help with this meeting agenda.` -> meeting fork
  - `I need help with this meeting follow-up.` -> meeting fork
  - `I need help drafting an email to my boss.` -> drafting fork
  - `I need help with a hard conversation.` -> hard-conversation fork
  - `I need help deciding between two apartments.` -> decision fork

## Clear Architect recommendation

Recommend the next bounded slice only:

**Post-Epic 9 slice 93: Companion Tomorrow-Planning Opener Usefulness Hardening**

Suggested bounded scope:
- stay only inside the smallest existing first-turn companion opener seam in `jarvis/companion_spine.py`
- harden natural tomorrow-planning / scheduling-tomorrow / organizing-tomorrow / planning-around-meetings phrasing so it lands on one concrete tomorrow-planning fork
- preserve the existing inbox, meeting, drafting, decision, and hard-conversation seams unchanged
- add only focused opener tests for the tomorrow-planning family and preserved nearby controls

Why this next:
- it is the strongest remaining first-turn chief-of-staff weakness in current repo truth
- it affects several natural phrasings, not just one alias
- it has a clear truthful direction already suggested by the stronger `get tomorrow under control` behavior
