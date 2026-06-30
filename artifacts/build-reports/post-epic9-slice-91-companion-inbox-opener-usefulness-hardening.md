# Post-Epic 9 Slice 91: Companion Inbox Opener Usefulness Hardening

Ready for Architect Office review: yes

## Exact prompts tested

Repaired inbox-family prompts:
- `I need help with my inbox.`
- `I need to get through my inbox.`
- `I need help with my inbox triage.`
- `I need to clear my inbox.`
- `I need help triaging my inbox.`

Preserved nearby controls rechecked:
- `I need help with this meeting follow-up.`
- `I need help drafting an email to my boss.`
- `I need help writing a follow-up email after this meeting.`
- `I need help with a hard conversation.`
- `I need help deciding between two apartments.`

## Exact code/tests changed

Code changes:
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:417)
  - Added a standalone first-turn inbox opener fork ahead of the generic practical and non-practical fallbacks.
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:643)
  - Added `_is_inbox_request(...)` as the narrow seam-local matcher for inbox / inbox-triage / clear-my-inbox phrasing.

New inbox opener reply:
- `Good. Is the real problem triage, replies you owe, or clearing the pile without getting sucked into it?`

Test changes:
- [tests/test_companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/tests/test_companion_spine.py:232)
  - Added focused coverage for the five inbox-family prompts above.

## Exact commands run

```bash
python3 -m py_compile jarvis/companion_spine.py tests/test_companion_spine.py
python3 -m pytest -q tests/test_companion_spine.py -k "help_with_my_inbox_prompt_gets_concrete_inbox_fork or get_through_my_inbox_prompt_gets_concrete_inbox_fork or inbox_triage_prompt_gets_concrete_inbox_fork or clear_my_inbox_prompt_gets_concrete_inbox_fork or triaging_my_inbox_prompt_gets_concrete_inbox_fork or meeting_agenda_prompt_gets_concrete_meeting_fork or drafting_email_to_boss_prompt_gets_drafting_fork or writing_follow_up_email_after_meeting_prompt_gets_drafting_fork or hard_conversation_prompt_gets_concrete_conversation_fork or decision_shaped_job_prompt_gets_decision_fork"
python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
prompts = [
    "I need help with my inbox.",
    "I need to get through my inbox.",
    "I need help with my inbox triage.",
    "I need to clear my inbox.",
    "I need help triaging my inbox.",
    "I need help with this meeting follow-up.",
    "I need help drafting an email to my boss.",
    "I need help writing a follow-up email after this meeting.",
    "I need help with a hard conversation.",
    "I need help deciding between two apartments.",
]
for prompt in prompts:
    reply = generate_companion_fallback(prompt, packet)
    print(f"PROMPT: {prompt}\nREPLY: {reply}\n")
PY
```

## Exact results

- `py_compile`: passed
- focused pytest: `10 passed, 268 deselected`
- in-process smoke:
  - all five inbox-family prompts now route to:
    - `Good. Is the real problem triage, replies you owe, or clearing the pile without getting sucked into it?`
  - preserved nearby controls still behave correctly:
    - `I need help with this meeting follow-up.` stays on the meeting fork
    - `I need help drafting an email to my boss.` stays on the drafting fork
    - `I need help writing a follow-up email after this meeting.` stays on the drafting fork
    - `I need help with a hard conversation.` stays on the hard-conversation fork
    - `I need help deciding between two apartments.` stays on the concrete decision fork

## Scope safety

This repair stayed inside the smallest existing first-turn companion opener seam only:
- no broad chief-of-staff redesign
- no fake inbox, thread, or account claims
- no broad planning or scheduling rewrite
- no changes to unrelated meeting, drafting, conversation, decision, vacation, retirement, or capability seams

## Architect recommendation

Approve.

This slice fixes the concrete inbox-family opener weakness with one narrow inbox fork and focused regression coverage, while preserving the adjacent hardened seams unchanged.
