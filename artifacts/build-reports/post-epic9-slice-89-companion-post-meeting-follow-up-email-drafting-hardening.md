# Post-Epic 9 Slice 89: Companion Post-Meeting Follow-Up Email Drafting Hardening

Ready for Architect Office review: yes

## Exact prompts tested

Repaired follow-up email drafting prompts:
- `I need help writing a follow-up email after this meeting.`
- `I need to send a follow-up email after this meeting.`

Preserved nearby controls rechecked:
- `I need help with this meeting follow-up.`
- `I need help with a hard conversation.`
- `I need help deciding between two apartments.`
- `I need help drafting an email to my boss.`
- `I need help writing an email to my boss.`

## Exact code/tests changed

Code changes:
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:566)
  - Added the narrow practical-handle terms:
    - `writing a follow-up email`
    - `writing a follow up email`
    - `send a follow-up email`
    - `send a follow up email`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:924)
  - Added the narrow drafting-opener terms:
    - `writing a follow-up email`
    - `writing a follow up email`
    - `follow-up email`
    - `follow up email`

Test changes:
- [tests/test_companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/tests/test_companion_spine.py:467)
  - Added focused regression coverage for:
    - `I need help writing a follow-up email after this meeting.`
    - `I need to send a follow-up email after this meeting.`

## Exact commands run

```bash
python3 -m py_compile jarvis/companion_spine.py tests/test_companion_spine.py
python3 -m pytest -q tests/test_companion_spine.py -k "writing_follow_up_email_after_meeting_prompt_gets_drafting_fork or send_follow_up_email_after_meeting_prompt_gets_drafting_fork or meeting_agenda_prompt_gets_concrete_meeting_fork or hard_conversation_prompt_gets_concrete_conversation_fork or decision_shaped_job_prompt_gets_decision_fork or drafting_email_to_boss_prompt_gets_drafting_fork or writing_email_to_boss_prompt_gets_drafting_fork"
python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
prompts = [
    "I need help writing a follow-up email after this meeting.",
    "I need to send a follow-up email after this meeting.",
    "I need help with this meeting follow-up.",
    "I need help with a hard conversation.",
    "I need help deciding between two apartments.",
    "I need help drafting an email to my boss.",
    "I need help writing an email to my boss.",
]
for prompt in prompts:
    reply = generate_companion_fallback(prompt, packet)
    print(f"PROMPT: {prompt}\nREPLY: {reply}\n")
PY
```

## Exact results

- `py_compile`: passed
- focused pytest: `7 passed, 266 deselected`
- in-process smoke:
  - `I need help writing a follow-up email after this meeting.` now routes to the drafting fork:
    - `Do you want blunt, warm, or diplomatic, and do you want the angle first or the actual draft?`
  - `I need to send a follow-up email after this meeting.` now routes to the drafting fork:
    - `Do you want blunt, warm, or diplomatic, and do you want the angle first or the actual draft?`
  - preserved nearby controls still behave correctly:
    - `I need help with this meeting follow-up.` stays on the meeting fork
    - `I need help with a hard conversation.` stays on the hard-conversation fork
    - `I need help deciding between two apartments.` stays on the concrete decision fork
    - `I need help drafting an email to my boss.` stays on the drafting fork
    - `I need help writing an email to my boss.` stays on the drafting fork

## Scope safety

This repair stayed inside the smallest existing drafting opener seam only:
- no broad drafting redesign
- no meeting seam rewrite
- no fake inbox, email, or calendar context claims
- no changes to unrelated vacation, retirement, capability, or broader conversation routing

## Architect recommendation

Approve.

This slice fixes the concrete post-meeting follow-up email drafting miss with narrow drafting-trigger refinements and focused regression coverage, while preserving the adjacent meeting, conversation, decision, and existing drafting seams unchanged.
