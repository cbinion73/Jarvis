# Post-Epic 9 Slice 85: Live-Use Weakness Assessment

Ready for Architect Office review: yes

## Exact prompts or routes inspected

Primary companion first-turn prompts inspected:
- `I need to prep for a meeting.`
- `Help me think through this meeting.`
- `I have a big meeting tomorrow.`
- `I need to get ready for this meeting with my boss.`
- `I need help with this meeting agenda.`
- `I need help with this meeting.`
- `I need help with my inbox.`
- `I need to get organized.`
- `I need to make a plan for this week.`
- `I need help figuring out my priorities.`
- `I need help with this presentation.`
- `I need help with this proposal.`
- `I need help planning my day.`
- `I need help deciding between two apartments.`
- `I need help with a tough text.`
- `I need help drafting an email to my boss.`

Preserved control prompts rechecked:
- `I need help with a hard conversation.`
- `I need help deciding between two apartments.`
- `I need help drafting an email to my boss.`

Code seam inspected:
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:1108)
  - `_generic_practical_fallback_reply`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:1184)
  - `_should_include_live_context`

Morning Brief / `/briefing-center` was not pursued further in this slice because the companion first-turn seam already showed a clearer, higher-value live-use defect.

## Strongest remaining defect found

The strongest remaining live-use defect is the lack of a concrete meeting-prep opener in the default companion path.

Current repo-truth behavior:
- `I need to prep for a meeting.`  
  - `I'm here. Give me the short version, or tell me which part feels off.`
- `I have a big meeting tomorrow.`  
  - `I'm here. Give me the short version, or tell me which part feels off.`
- `I need to get ready for this meeting with my boss.`  
  - `I'm here. Give me the short version, or tell me which part feels off.`
- `Help me think through this meeting.`  
  - `Let's make it concrete. Is this mostly a decision, a conversation, or a plan you need to sort out first?`
- `I need help with this meeting agenda.`  
  - `Let's make it concrete. Is this mostly a decision, a conversation, or a plan you need to sort out first?`

Why this is a real defect:
- these are common first-turn chief-of-staff asks
- the current replies are materially weaker than the already-hardened vacation, retirement, drafting, job-exit, and hard-conversation openers
- the code already treats `meeting` as significant enough to include in live-context gating, but there is no matching concrete first-turn meeting opener inside the practical fallback seam

## Why this is higher value than adjacent options

This is higher value than nearby alternatives because it is both broader and more central to live use:
- it affects several natural first-turn prompts, not just one alias
- it sits squarely in the chief-of-staff / practical companion lane
- it currently falls back to either the generic non-practical reply or the generic practical sorter, both of which are weaker than the concrete forks now available in neighboring seams

Adjacent options were considered but not chosen:
- inbox/open-loop phrasing:
  - `I need help with my inbox.` currently gets the generic practical sorter, but that is a narrower lane than meeting prep
- drafting alias drift:
  - `I need help drafting an email to my boss.` currently routes into the hard-conversation fork, which is a real narrower defect, but it is less central than the broader missing meeting opener family

## Code/tests changed or next slice only

No code or tests were changed in this slice.

This slice is a recommendation-only assessment. The defect is concrete, but the safer bounded next move is to give it its own repair slice rather than combine assessment plus implementation.

## Exact commands run

```bash
rg -n "briefing-center|morning_brief|generate_companion_fallback|DEFAULT_COMPANION|fallback" jarvis/companion_spine.py jarvis/morning_brief_pipeline.py jarvis/render_pages.py jarvis/service.py tests/test_companion_spine.py
sed -n '1,220p' jarvis/companion_spine.py
python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
prompts = [
    "I need to prep for a meeting.",
    "Help me think through this meeting.",
    "I need to have a difficult meeting with my boss.",
    "I need help with my inbox.",
    "I need to get organized.",
    "I need to make a plan for this week.",
    "I need help figuring out my priorities.",
    "I need help with this presentation.",
    "I need help with this proposal.",
    "I need help planning my day.",
    "I need help deciding between two apartments.",
    "I need help with a tough text.",
]
for prompt in prompts:
    reply = generate_companion_fallback(prompt, packet)
    print(f"PROMPT: {prompt}\nREPLY: {reply}\n")
PY
python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
prompts = [
    "I need to prep for a meeting.",
    "Help me think through this meeting.",
    "I have a big meeting tomorrow.",
    "I need to get ready for this meeting with my boss.",
    "I need help with this meeting agenda.",
    "I need help with this meeting.",
    "I need help with a hard conversation.",
    "I need help deciding between two apartments.",
    "I need help drafting an email to my boss.",
]
for prompt in prompts:
    reply = generate_companion_fallback(prompt, packet)
    print(f"PROMPT: {prompt}\nREPLY: {reply}\n")
PY
rg -n "meeting|agenda|big meeting|prep for a meeting|get ready for this meeting" tests/test_companion_spine.py jarvis/companion_spine.py
nl -ba jarvis/companion_spine.py | sed -n '1080,1225p'
```

## Exact results

Key smoke results:
- `I need to prep for a meeting.`  
  - generic non-practical fallback
- `I have a big meeting tomorrow.`  
  - generic non-practical fallback
- `I need to get ready for this meeting with my boss.`  
  - generic non-practical fallback
- `Help me think through this meeting.`  
  - generic practical sorter
- `I need help with this meeting agenda.`  
  - generic practical sorter

Preserved neighboring controls:
- `I need help with a hard conversation.`  
  - still routes to the hard-conversation fork
- `I need help deciding between two apartments.`  
  - still routes to the concrete decision fork

Additional adjacent evidence:
- `I need help drafting an email to my boss.`  
  - currently routes into the hard-conversation fork, which is a narrower adjacent issue but not the highest-value remaining defect

Code inspection result:
- `meeting` is present in `_should_include_live_context`
- no concrete meeting-prep first-turn opener exists in `_generic_practical_fallback_reply`
- no focused meeting opener tests currently exist in `tests/test_companion_spine.py`

## Clear Architect recommendation

Recommend the next bounded slice only:

**Post-Epic 9 slice 86: Companion Meeting Opener Usefulness Hardening**

Suggested bounded scope:
- stay only inside the standalone first-turn companion meeting opener seam in `jarvis/companion_spine.py`
- harden natural meeting-prep / meeting-agenda / get-ready-for-this-meeting phrasing so it lands on one concrete meeting-shaped fork
- keep hard-conversation, decision, and drafting seams intact
- add only focused opener tests for the meeting family and preserved nearby controls

Why this next:
- it is the clearest remaining first-turn live-use weakness
- it is more practically important than the adjacent inbox or drafting-alias issues
- it can be repaired as one narrow existing-seam uplift without broad architecture changes
