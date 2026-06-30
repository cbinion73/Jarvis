# Post-Epic 9 Slice 97: Companion Agenda Opener Usefulness Hardening

Ready for Architect Office review: yes

## Exact prompts tested

Repaired agenda-family prompts:
- `I need help with this agenda.`
- `I need help setting the agenda.`
- `Set the agenda with me.`

Preserved nearby controls rechecked:
- `I need help with this meeting agenda.`
- `I need help with my inbox.`
- `I need help drafting an email to my boss.`
- `I need help with a hard conversation.`
- `I need help deciding between two apartments.`
- `I need help planning tomorrow.`
- `I need help with this presentation.`

## Exact code/tests changed

Code changes:
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:419)
  - Added a standalone first-turn agenda opener fork ahead of the inbox, meeting, and generic practical fallbacks.
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:675)
  - Added `_is_agenda_request(...)` as the narrow seam-local matcher for agenda phrasing outside the explicit meeting seam.

New agenda opener reply:
- `Good. Is the real work what needs to be covered, what can wait, or how to keep the conversation from drifting?`

Test changes:
- [tests/test_companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/tests/test_companion_spine.py:292)
  - Added focused coverage for the three agenda-family prompts above.

## Exact commands run

```bash
python3 -m py_compile jarvis/companion_spine.py tests/test_companion_spine.py
python3 -m pytest -q tests/test_companion_spine.py -k "help_with_this_agenda_prompt_gets_concrete_agenda_fork or help_setting_the_agenda_prompt_gets_concrete_agenda_fork or set_the_agenda_with_me_prompt_gets_concrete_agenda_fork or meeting_agenda_prompt_gets_concrete_meeting_fork or help_with_my_inbox_prompt_gets_concrete_inbox_fork or drafting_email_to_boss_prompt_gets_drafting_fork or hard_conversation_prompt_gets_concrete_conversation_fork or decision_shaped_job_prompt_gets_decision_fork or help_planning_tomorrow_prompt_gets_concrete_tomorrow_fork or help_with_this_presentation_prompt_gets_concrete_prep_fork"
python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
prompts = [
    "I need help with this agenda.",
    "I need help setting the agenda.",
    "Set the agenda with me.",
    "I need help with this meeting agenda.",
    "I need help with my inbox.",
    "I need help drafting an email to my boss.",
    "I need help with a hard conversation.",
    "I need help deciding between two apartments.",
    "I need help planning tomorrow.",
    "I need help with this presentation.",
]
for prompt in prompts:
    reply = generate_companion_fallback(prompt, packet)
    print(f"PROMPT: {prompt}\nREPLY: {reply}\n")
PY
```

## Exact results

- `py_compile`: passed
- focused pytest: `10 passed, 279 deselected`
- in-process smoke:
  - all three agenda-family prompts now route to:
    - `Good. Is the real work what needs to be covered, what can wait, or how to keep the conversation from drifting?`
  - preserved nearby controls still behave correctly:
    - `I need help with this meeting agenda.` stays on the meeting fork
    - `I need help with my inbox.` stays on the inbox fork
    - `I need help drafting an email to my boss.` stays on the drafting fork
    - `I need help with a hard conversation.` stays on the hard-conversation fork
    - `I need help deciding between two apartments.` stays on the concrete decision fork
    - `I need help planning tomorrow.` stays on the tomorrow-planning fork
    - `I need help with this presentation.` stays on the presentation/proposal prep fork

## Scope safety

This repair stayed inside the smallest existing first-turn companion opener seam only:
- no broad chief-of-staff redesign
- no fake meeting, audience, or scheduling context claims
- no broad planning-system rewrite
- no changes to unrelated meeting, inbox, drafting, conversation, decision, tomorrow-planning, presentation/proposal, vacation, retirement, or capability seams

## Architect recommendation

Approve.

This slice fixes the concrete agenda-family opener weakness with one narrow agenda fork and focused regression coverage, while preserving the adjacent hardened seams unchanged.
