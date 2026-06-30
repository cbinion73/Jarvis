# Post-Epic 9 Slice 102: Tomorrow-Prep Opener Hardening

Ready for Architect Office review: yes

## Exact prompts inspected

Target family hardened:
- `I need help preparing for tomorrow.`
- `I need help getting ready for tomorrow.`
- `Help me get ready for tomorrow.`
- `I need to get ready for tomorrow.`
- `I need help with tomorrow.`
- `I need help with tomorrow's plan.`
- `I need help with tomorrow morning.`

Preserved nearby controls checked:
- `I need help with my inbox.`
- `I need help with this meeting.`
- `I need help with this agenda.`
- `I need help with this presentation.`
- `I need help drafting an email to my boss.`
- `I need help deciding between two apartments.`
- `I need help with a hard conversation.`
- `I need help scheduling around constraints.`

## Exact code/tests changed

Code changes:
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:691)
  - extended `_is_tomorrow_planning_request(...)` with the tomorrow-prep family:
    - `help preparing for tomorrow`
    - `help getting ready for tomorrow`
    - `get ready for tomorrow`
    - `help with tomorrow`
    - `help with tomorrow's plan`
    - `help with tomorrow morning`
  - kept the repair inside the existing tomorrow-planning seam and preserved the current reply shape

Test changes:
- [tests/test_companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/tests/test_companion_spine.py:351)
  - added focused opener coverage for all seven tomorrow-prep prompts
  - preserved nearby control validation through the focused pytest battery

## Exact commands run

```bash
python3 -m py_compile jarvis/companion_spine.py tests/test_companion_spine.py
python3 -m pytest -q tests/test_companion_spine.py -k "help_preparing_for_tomorrow_prompt_gets_concrete_tomorrow_fork or help_getting_ready_for_tomorrow_prompt_gets_concrete_tomorrow_fork or help_me_get_ready_for_tomorrow_prompt_gets_concrete_tomorrow_fork or need_to_get_ready_for_tomorrow_prompt_gets_concrete_tomorrow_fork or help_with_tomorrow_prompt_gets_concrete_tomorrow_fork or help_with_tomorrows_plan_prompt_gets_concrete_tomorrow_fork or help_with_tomorrow_morning_prompt_gets_concrete_tomorrow_fork or help_with_my_inbox_prompt_gets_concrete_inbox_fork or help_with_this_meeting_prompt_gets_concrete_meeting_fork or help_with_this_agenda_prompt_gets_concrete_agenda_fork or help_with_this_presentation_prompt_gets_concrete_prep_fork or drafting_email_to_boss_prompt_gets_drafting_fork or deciding_between_two_jobs_prompt_gets_decision_fork or hard_conversation_prompt_gets_concrete_conversation_fork or scheduling_around_constraints_prompt_gets_constraints_fork"
python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
prompts = [
    "I need help preparing for tomorrow.",
    "I need help getting ready for tomorrow.",
    "Help me get ready for tomorrow.",
    "I need to get ready for tomorrow.",
    "I need help with tomorrow.",
    "I need help with tomorrow's plan.",
    "I need help with tomorrow morning.",
    "I need help with my inbox.",
    "I need help with this meeting.",
    "I need help with this agenda.",
    "I need help with this presentation.",
    "I need help drafting an email to my boss.",
    "I need help deciding between two apartments.",
    "I need help with a hard conversation.",
    "I need help scheduling around constraints.",
]
for prompt in prompts:
    print(f"PROMPT: {prompt}")
    print(generate_companion_fallback(prompt, packet))
    print()
PY
```

## Exact results

Compile:
- `python3 -m py_compile jarvis/companion_spine.py tests/test_companion_spine.py`
- result: passed

Focused pytest:
- `15 passed, 287 deselected in 0.25s`

In-process smoke after repair:
- `I need help preparing for tomorrow.` -> `Good. For tomorrow, what actually has to happen, what is fixed, and what can slip?`
- `I need help getting ready for tomorrow.` -> same tomorrow-planning fork
- `Help me get ready for tomorrow.` -> same tomorrow-planning fork
- `I need to get ready for tomorrow.` -> same tomorrow-planning fork
- `I need help with tomorrow.` -> same tomorrow-planning fork
- `I need help with tomorrow's plan.` -> same tomorrow-planning fork
- `I need help with tomorrow morning.` -> same tomorrow-planning fork

Preserved nearby controls remained correct:
- `I need help with my inbox.` stayed on the inbox fork
- `I need help with this meeting.` stayed on the meeting fork
- `I need help with this agenda.` stayed on the agenda fork
- `I need help with this presentation.` stayed on the presentation/proposal prep fork
- `I need help drafting an email to my boss.` stayed on the drafting fork
- `I need help deciding between two apartments.` stayed on the decision fork
- `I need help with a hard conversation.` stayed on the hard-conversation fork
- `I need help scheduling around constraints.` stayed on the constraints-scheduling fork

## Follow-up recommendation

No stronger remaining first-turn defect became newly visible inside this narrow validation set.

If Architect Office wants the next bounded lane, the cleanest move is another fresh reassessment rather than guessing the next alias family from adjacency alone.
