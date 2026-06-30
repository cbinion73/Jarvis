# Post-Epic 9 Slice 88: Live-Use Weakness Reassessment

Ready for Architect Office review: yes

## Exact prompts or routes inspected

Companion first-turn prompts inspected:
- `I need help with my inbox.`
- `I need to get through my inbox.`
- `I need help with my priorities.`
- `I need help planning my day.`
- `I need help planning tomorrow.`
- `I need help with this presentation.`
- `I need help getting ready for this presentation.`
- `I need help with this proposal.`
- `I need help getting ready for this proposal.`
- `I need help scheduling this week.`
- `I need help planning around two meetings.`
- `I need help with this meeting follow-up.`
- `I need help writing a follow-up email after this meeting.`
- `I need to send a follow-up email after this meeting.`
- `I need help with this follow-up.`
- `I need help with this agenda.`
- `I need help with a tough text.`
- `I need help with a hard conversation.`
- `I need help deciding between two apartments.`

Code seams inspected:
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:321)
  - `generate_companion_fallback(...)`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:530)
  - `_request_needs_practical_handle(...)`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:916)
  - `_is_drafting_request(...)`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:1108)
  - `_generic_practical_fallback_reply(...)`

## Strongest remaining defect found

The strongest remaining first-turn live-use defect is the post-meeting follow-up email drafting family.

Current repo-truth behavior:
- `I need help writing a follow-up email after this meeting.`  
  - `Let's make it concrete. Is this mostly a decision, a conversation, or a plan you need to sort out first?`
- `I need to send a follow-up email after this meeting.`  
  - `I'm here. Give me the short version, or tell me which part feels off.`

Why this is a real defect:
- these are explicit drafting asks, not generic planning asks
- they sit directly adjacent to the now-approved meeting opener seam and the existing drafting opener seam
- the current behavior under-uses both of those hardened seams and drops to weaker generic fallbacks

## Why it is higher value than adjacent options

This is higher value than nearby alternatives because it is both more concrete and more bounded than the other remaining misses.

Compared with adjacent options:
- inbox phrasing:
  - still somewhat weak, but would likely need a broader new opener family with more ambiguous truthful boundaries
- presentation / proposal phrasing:
  - still generic, but does not yet have as clear a neighboring existing seam to attach to
- planning tomorrow / planning around two meetings:
  - also weak, but less sharply bounded than the follow-up-email drafting miss

By contrast, the post-meeting follow-up email family is:
- already clearly drafting-shaped
- already adjacent to an approved meeting opener
- already adjacent to an approved drafting opener
- narrow enough to repair inside an existing seam without inventing a new lane

## Whether code/tests changed or next bounded slice only

No code or tests were changed in this slice.

This is a recommendation-only reassessment. The defect is concrete, but it is cleaner to give it its own bounded repair slice than to combine assessment plus implementation here.

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
    "I need help with this presentation.",
    "I need help with this proposal.",
    "I need help getting ready for this presentation.",
    "I need help getting ready for this proposal.",
    "I need help scheduling this week.",
    "I need help planning around two meetings.",
    "I need help with this meeting follow-up.",
    "I need help writing a follow-up email after this meeting.",
    "I need to send a follow-up email after this meeting.",
    "I need help with this follow-up.",
    "I need help with this agenda.",
    "I need help with a tough text.",
    "I need help with a hard conversation.",
    "I need help deciding between two apartments.",
]
for prompt in prompts:
    reply = generate_companion_fallback(prompt, packet)
    print(f"PROMPT: {prompt}\nREPLY: {reply}\n")
PY
rg -n "inbox|priorities|planning tomorrow|presentation|proposal|agenda|follow-up|follow up|schedule|scheduling" tests/test_companion_spine.py jarvis/companion_spine.py
python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
prompts = [
    "I need help with my inbox.",
    "I need to get through my inbox.",
    "I need help planning tomorrow.",
    "I need help planning around two meetings.",
    "I need help with this presentation.",
    "I need help getting ready for this presentation.",
    "I need help with this proposal.",
    "I need help getting ready for this proposal.",
    "I need help writing a follow-up email after this meeting.",
    "I need to send a follow-up email after this meeting.",
    "I need help with this meeting follow-up.",
    "I need help with this agenda.",
]
for prompt in prompts:
    reply = generate_companion_fallback(prompt, packet)
    print(f"PROMPT: {prompt}\nREPLY: {reply}\n")
PY
```

## Exact results

Key results:
- `I need help writing a follow-up email after this meeting.`  
  - generic practical sorter
- `I need to send a follow-up email after this meeting.`  
  - generic non-practical fallback

Evidence that this is adjacent to existing hardened seams:
- `I need help with this meeting follow-up.`  
  - now lands on the meeting opener fork
- `I need help with a hard conversation.`  
  - still lands on the hard-conversation fork
- `I need help deciding between two apartments.`  
  - still lands on the concrete decision fork

Adjacent weaker-but-not-chosen candidates:
- inbox:
  - `I need help with my inbox.` -> generic practical sorter
  - `I need to get through my inbox.` -> generic non-practical fallback
- presentation / proposal:
  - still generic practical sorter

## Clear Architect recommendation

Recommend the next bounded slice only:

**Post-Epic 9 slice 89: Companion Post-Meeting Follow-Up Email Drafting Hardening**

Suggested bounded scope:
- stay only inside the smallest existing first-turn drafting opener seam in `jarvis/companion_spine.py`
- harden explicit post-meeting follow-up email phrasing so it routes to the existing drafting fork
- preserve the new meeting opener seam, hard-conversation seam, and decision seam unchanged
- add only focused drafting-opener tests for the repaired follow-up email family and preserved nearby controls

Why this next:
- it is the clearest remaining concrete first-turn miss after slices 86 and 87
- it can be repaired inside an existing seam without broad architecture changes
- it is more bounded and safer than starting a new inbox or presentation/proposal opener family
