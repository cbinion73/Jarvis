# Post-Epic 9 Slice 87: Companion Drafting Opener Boss-Email Usefulness Hardening

Ready for Architect Office review: yes

## Exact prompts tested

Repaired drafting opener prompt:
- `I need help drafting an email to my boss.`

Preserved correct drafting controls rechecked:
- `I need help writing an email to my boss.`

Preserved nearby controls rechecked:
- `I need help with a hard conversation.`
- `I need to prep for a meeting.`
- `I need help deciding between two apartments.`

## Exact code/tests changed

Code change:
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:920)
  - Added the narrow drafting trigger `drafting an email` to the existing `_is_drafting_request(...)` term list.

Test change:
- [tests/test_companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/tests/test_companion_spine.py:460)
  - Added focused regression coverage for:
    - `I need help drafting an email to my boss.`

The existing nearby controls and existing correct drafting phrasing were preserved without changing their seams.

## Exact commands run

```bash
python3 -m py_compile jarvis/companion_spine.py tests/test_companion_spine.py
python3 -m pytest -q tests/test_companion_spine.py -k "drafting_email_to_boss_prompt_gets_drafting_fork or writing_email_to_boss_prompt_gets_drafting_fork or hard_conversation_prompt_gets_concrete_conversation_fork or prep_for_meeting_prompt_gets_concrete_meeting_fork or decision_shaped_job_prompt_gets_decision_fork"
python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
prompts = [
    "I need help drafting an email to my boss.",
    "I need help writing an email to my boss.",
    "I need help with a hard conversation.",
    "I need to prep for a meeting.",
    "I need help deciding between two apartments.",
]
for prompt in prompts:
    reply = generate_companion_fallback(prompt, packet)
    print(f"PROMPT: {prompt}\nREPLY: {reply}\n")
PY
```

## Exact results

- `py_compile`: passed
- focused pytest: `5 passed, 266 deselected`
- in-process smoke:
  - `I need help drafting an email to my boss.` now routes to the drafting fork:
    - `Do you want blunt, warm, or diplomatic, and do you want the angle first or the actual draft?`
  - preserved drafting control still routes to the drafting fork:
    - `I need help writing an email to my boss.`
  - preserved nearby controls still behave correctly:
    - `I need help with a hard conversation.` stays on the hard-conversation fork
    - `I need to prep for a meeting.` stays on the meeting fork
    - `I need help deciding between two apartments.` stays on the concrete decision fork

## Scope safety

This repair stayed inside the smallest existing drafting opener seam only:
- no broad drafting redesign
- no conversation seam rewrite
- no fake email or inbox context claims
- no changes to unrelated meeting, decision, vacation, retirement, or capability seams

## Architect recommendation

Approve.

This slice fixes the one narrow boss-email drafting miss with a single drafting trigger refinement and focused regression coverage, while preserving the adjacent hardened seams unchanged.
