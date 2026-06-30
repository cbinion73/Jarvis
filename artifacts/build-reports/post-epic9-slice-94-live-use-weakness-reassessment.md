# Post-Epic 9 Slice 94: Live-Use Weakness Reassessment

Ready for Architect Office review: yes

## Exact prompts or routes inspected

Companion first-turn prompts inspected:
- `I need help with this presentation.`
- `I need help getting ready for this presentation.`
- `I need help with this proposal.`
- `I need help getting ready for this proposal.`
- `I need help with this agenda.`
- `I need help setting the agenda.`
- `I need help with this meeting agenda.`
- `I need help with this meeting.`
- `I need help with my priorities.`
- `I need help planning my day.`
- `I need help planning around two meetings.`
- `I need help scheduling around two meetings.`
- `I need help with this meeting follow-up.`
- `I need help drafting an email to my boss.`
- `I need help with a hard conversation.`
- `I need help deciding between two apartments.`
- `I need to get tomorrow under control.`

Code seams inspected:
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:321)
  - `generate_companion_fallback(...)`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:535)
  - `_request_needs_practical_handle(...)`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:1208)
  - `_generic_practical_fallback_reply(...)`

## Strongest remaining defect found

The strongest remaining first-turn chief-of-staff weakness is the presentation / proposal prep opener family.

Current repo-truth behavior:
- `I need help with this presentation.`  
  - `Let's make it concrete. Is this mostly a decision, a conversation, or a plan you need to sort out first?`
- `I need help getting ready for this presentation.`  
  - `Let's make it concrete. Is this mostly a decision, a conversation, or a plan you need to sort out first?`
- `I need help with this proposal.`  
  - `Let's make it concrete. Is this mostly a decision, a conversation, or a plan you need to sort out first?`
- `I need help getting ready for this proposal.`  
  - `Let's make it concrete. Is this mostly a decision, a conversation, or a plan you need to sort out first?`

Why this is a real defect:
- these are common chief-of-staff style first turns
- all four currently collapse to the same generic practical sorter
- unlike the inbox, meeting, drafting, and tomorrow-planning families, this lane still has no concrete opener at all

## Why it is higher value than adjacent options

Presentation / proposal prep is higher value than the nearby remaining options because it combines multiple natural phrasings with a clearly missing first-turn fork.

Compared with adjacent options:
- agenda outside the meeting seam:
  - still weak for:
    - `I need help with this agenda.`
    - `I need help setting the agenda.`
  - but this is a smaller two-prompt family, and the related `meeting agenda` phrasing is already correctly handled by the meeting fork
- scheduling around constraints:
  - `I need help scheduling around two meetings.` is still generic, but it is narrower than the broader presentation/proposal family
- priorities / day planning:
  - already have sharper nearby behavior in the capacity/tomorrow lanes

Presentation / proposal prep is the clearest remaining family where both importance and current weakness are high, and where no stronger adjacent opener currently catches the request.

## Whether code/tests changed or next bounded slice only

No code or tests were changed in this slice.

This is a recommendation-only reassessment. The defect is concrete, but it is cleaner to give presentation/proposal prep its own bounded opener-hardening slice than to combine assessment plus implementation here.

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
    "I need help with this meeting agenda.",
    "I need help with this meeting.",
    "I need help with my priorities.",
    "I need help planning my day.",
    "I need help planning around two meetings.",
    "I need help scheduling around two meetings.",
    "I need help with this meeting follow-up.",
    "I need help drafting an email to my boss.",
    "I need help with a hard conversation.",
    "I need help deciding between two apartments.",
    "I need to get tomorrow under control.",
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
    "I need help with this presentation.",
    "I need help getting ready for this presentation.",
    "I need help with this proposal.",
    "I need help getting ready for this proposal.",
    "I need help with this agenda.",
    "I need help setting the agenda.",
    "I need help with this meeting agenda.",
    "I need help with this meeting.",
]
for prompt in prompts:
    reply = generate_companion_fallback(prompt, packet)
    print(f"PROMPT: {prompt}\nREPLY: {reply}\n")
PY
```

## Exact results

Key presentation / proposal results:
- `I need help with this presentation.` -> generic practical sorter
- `I need help getting ready for this presentation.` -> generic practical sorter
- `I need help with this proposal.` -> generic practical sorter
- `I need help getting ready for this proposal.` -> generic practical sorter

Adjacent comparison evidence:
- agenda outside the meeting seam:
  - `I need help with this agenda.` -> generic practical sorter
  - `I need help setting the agenda.` -> generic practical sorter
- meeting seam remains correct:
  - `I need help with this meeting agenda.` -> meeting fork
  - `I need help with this meeting.` -> meeting fork
- other hardened lanes remain correct:
  - `I need help with my priorities.` -> capacity pushback
  - `I need help planning my day.` -> overloaded-week fork
  - `I need help planning around two meetings.` -> tomorrow-planning fork
  - `I need help with this meeting follow-up.` -> meeting fork
  - `I need help drafting an email to my boss.` -> drafting fork
  - `I need help with a hard conversation.` -> hard-conversation fork
  - `I need help deciding between two apartments.` -> decision fork
  - `I need to get tomorrow under control.` -> capacity pushback

## Clear Architect recommendation

Recommend the next bounded slice only:

**Post-Epic 9 slice 95: Companion Presentation / Proposal Prep Opener Hardening**

Suggested bounded scope:
- stay only inside the smallest existing first-turn companion opener seam in `jarvis/companion_spine.py`
- harden natural presentation / proposal prep phrasing so it lands on one concrete prep-shaped fork
- preserve the existing inbox, meeting, drafting, decision, conversation, and tomorrow-planning seams unchanged
- add only focused opener tests for the presentation/proposal family and preserved nearby controls

Why this next:
- it is the strongest remaining first-turn chief-of-staff weakness in current repo truth
- it affects four natural phrasings, not just one alias
- it is broader and higher-value than the adjacent agenda-only family while still narrow enough for one bounded opener slice
