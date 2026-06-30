# Post-Epic 9 Slice 90: Live-Use Weakness Reassessment

Ready for Architect Office review: yes

## Exact prompts or routes inspected

Companion first-turn prompts inspected:
- `I need help with my inbox.`
- `I need to get through my inbox.`
- `I need help with my inbox triage.`
- `I need to clear my inbox.`
- `I need help triaging my inbox.`
- `I need help with my priorities.`
- `I need help planning my day.`
- `I need help planning tomorrow.`
- `I need help scheduling tomorrow.`
- `I need help planning around two meetings.`
- `I need to get tomorrow under control.`
- `I need help organizing tomorrow.`
- `I need help with this presentation.`
- `I need help getting ready for this presentation.`
- `I need help with this proposal.`
- `I need help getting ready for this proposal.`
- `I need help with this agenda.`
- `I need help with this meeting follow-up.`
- `I need help drafting an email to my boss.`
- `I need help writing a follow-up email after this meeting.`
- `I need help with a hard conversation.`
- `I need help deciding between two apartments.`

Code seams inspected:
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:321)
  - `generate_companion_fallback(...)`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:535)
  - `_request_needs_practical_handle(...)`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:1108)
  - `_generic_practical_fallback_reply(...)`

## Strongest remaining defect found

The strongest remaining first-turn chief-of-staff weakness is the inbox opener family.

Current repo-truth behavior:
- `I need help with my inbox.`  
  - `Let's make it concrete. Is this mostly a decision, a conversation, or a plan you need to sort out first?`
- `I need to get through my inbox.`  
  - `I'm here. Give me the short version, or tell me which part feels off.`
- `I need help with my inbox triage.`  
  - `Let's make it concrete. Is this mostly a decision, a conversation, or a plan you need to sort out first?`
- `I need to clear my inbox.`  
  - `I'm here. Give me the short version, or tell me which part feels off.`
- `I need help triaging my inbox.`  
  - `Let's make it concrete. Is this mostly a decision, a conversation, or a plan you need to sort out first?`

Why this is a real defect:
- inbox handling is a central chief-of-staff use case
- the current behavior splits across the generic practical sorter and the generic non-practical fallback
- unlike the now-hardened meeting and drafting lanes, the inbox family still has no concrete first-turn fork at all

## Why it is higher value than adjacent options

Inbox is higher value than the remaining adjacent options because it combines:
- higher practical importance
- multiple natural first-turn phrasings
- consistently weak current behavior

Compared with nearby alternatives:
- tomorrow-planning / scheduling:
  - still weak for prompts like `I need help planning tomorrow.`
  - but at least one nearby phrasing already lands on a stronger capacity pushback:
    - `I need to get tomorrow under control.`
- presentation / proposal:
  - still generic, but these are narrower and less core than inbox triage
- agenda:
  - still generic for `I need help with this agenda.`
  - but `meeting agenda` is already covered inside the meeting opener seam

Inbox is the clearest remaining family where both importance and current weakness are high.

## Whether code/tests changed or next bounded slice only

No code or tests were changed in this slice.

This is a recommendation-only reassessment. The defect is concrete, but the cleanest next move is to give inbox its own bounded opener-hardening slice rather than mixing assessment plus implementation here.

## Exact commands run

```bash
python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
prompts = [
    "I need help with my inbox.",
    "I need to get through my inbox.",
    "I need help with my priorities.",
    "I need help planning my day.",
    "I need help planning tomorrow.",
    "I need help scheduling tomorrow.",
    "I need help planning around two meetings.",
    "I need help with this presentation.",
    "I need help getting ready for this presentation.",
    "I need help with this proposal.",
    "I need help getting ready for this proposal.",
    "I need help with this agenda.",
    "I need help with my inbox triage.",
    "I need help with a hard conversation.",
    "I need help deciding between two apartments.",
    "I need help drafting an email to my boss.",
    "I need help writing a follow-up email after this meeting.",
    "I need help with this meeting follow-up.",
]
for prompt in prompts:
    reply = generate_companion_fallback(prompt, packet)
    print(f"PROMPT: {prompt}\nREPLY: {reply}\n")
PY
rg -n "inbox|priorities|planning tomorrow|scheduling tomorrow|presentation|proposal|agenda|follow-up|follow up|priorities|triage" tests/test_companion_spine.py jarvis/companion_spine.py
python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
prompts = [
    "I need help with my inbox.",
    "I need to get through my inbox.",
    "I need help with my inbox triage.",
    "I need to clear my inbox.",
    "I need help triaging my inbox.",
    "I need help planning tomorrow.",
    "I need help scheduling tomorrow.",
    "I need help planning around two meetings.",
    "I need to get tomorrow under control.",
    "I need help organizing tomorrow.",
]
for prompt in prompts:
    reply = generate_companion_fallback(prompt, packet)
    print(f"PROMPT: {prompt}\nREPLY: {reply}\n")
PY
```

## Exact results

Key inbox-family results:
- `I need help with my inbox.`  
  - generic practical sorter
- `I need to get through my inbox.`  
  - generic non-practical fallback
- `I need help with my inbox triage.`  
  - generic practical sorter
- `I need to clear my inbox.`  
  - generic non-practical fallback
- `I need help triaging my inbox.`  
  - generic practical sorter

Comparison evidence from adjacent families:
- tomorrow-planning:
  - `I need help planning tomorrow.` -> generic practical sorter
  - `I need help scheduling tomorrow.` -> generic practical sorter
  - `I need to get tomorrow under control.` -> capacity pushback
- presentation / proposal:
  - still generic practical sorter
- preserved hardened lanes still behave correctly:
  - `I need help with a hard conversation.` -> hard-conversation fork
  - `I need help deciding between two apartments.` -> decision fork
  - `I need help drafting an email to my boss.` -> drafting fork
  - `I need help writing a follow-up email after this meeting.` -> drafting fork
  - `I need help with this meeting follow-up.` -> meeting fork

## Clear Architect recommendation

Recommend the next bounded slice only:

**Post-Epic 9 slice 91: Companion Inbox Opener Usefulness Hardening**

Suggested bounded scope:
- stay only inside the smallest existing first-turn companion opener seam in `jarvis/companion_spine.py`
- harden natural inbox / inbox-triage / clear-my-inbox phrasing so it lands on one concrete inbox-shaped fork
- preserve the existing meeting, drafting, decision, and hard-conversation seams unchanged
- add only focused opener tests for the inbox family and preserved nearby controls

Why this next:
- it is the strongest remaining first-turn chief-of-staff weakness in current repo truth
- it affects several natural phrasings, not just one alias
- it can be repaired as one bounded opener-family hardening slice without broad architecture changes
