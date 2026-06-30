# Post-Epic 9 Slice 114: Companion One-on-One / Check-In Meeting Opener Hardening

Ready for Architect Office review: yes

## Exact prompts inspected

Target one-on-one / check-in family:
- `I need help with my one-on-one.`
- `I need help getting ready for my one-on-one.`
- `I need help preparing for my one-on-one.`
- `I need help with my 1:1.`
- `I need help with this check-in.`

Preserved nearby controls:
- `I need help with this meeting.`
- `I need help with this agenda.`
- `I need help with my email.`
- `I need help drafting an email to my boss.`
- `I need help with this presentation.`
- `I need help planning tomorrow.`
- `I need help with my follow-up.`
- `I need help deciding between two apartments.`
- `I need help with a hard conversation.`
- `I need help scheduling around constraints.`

## Exact code/tests changed

Code:
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:635)
  - widened `_is_meeting_prep_request(...)` just enough to recognize meeting-adjacent aliases without the literal word `meeting`
  - added bounded support for:
    - `one-on-one`
    - `1:1`
    - `check-in`
  - added direct phrase matches for the five target prompts so they route to the existing truthful meeting fork
  - left agenda routing separate, so explicit agenda phrasing still stays on the agenda fork

Tests:
- [tests/test_companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/tests/test_companion_spine.py:629)
  - added focused opener coverage for all five new one-on-one / check-in prompts
  - preserved nearby control validation through the focused pytest battery

## Exact commands run

Pre-repair smoke:

```bash
python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
prompts = [
    "I need help with my one-on-one.",
    "I need help getting ready for my one-on-one.",
    "I need help preparing for my one-on-one.",
    "I need help with my 1:1.",
    "I need help with this check-in.",
    "I need help with this meeting.",
    "I need help with this agenda.",
    "I need help with my email.",
    "I need help drafting an email to my boss.",
    "I need help with this presentation.",
    "I need help planning tomorrow.",
    "I need help with my follow-up.",
    "I need help deciding between two apartments.",
    "I need help with a hard conversation.",
    "I need help scheduling around constraints.",
]
for prompt in prompts:
    print('PROMPT:', prompt)
    print(generate_companion_fallback(prompt, packet))
    print('---')
PY
```

Compile:

```bash
python3 -m py_compile jarvis/companion_spine.py tests/test_companion_spine.py
```

Focused pytest:

```bash
python3 -m pytest -q tests/test_companion_spine.py -k "help_with_my_one_on_one_prompt_gets_concrete_meeting_fork or getting_ready_for_my_one_on_one_prompt_gets_concrete_meeting_fork or preparing_for_my_one_on_one_prompt_gets_concrete_meeting_fork or help_with_my_one_on_one_numeric_prompt_gets_concrete_meeting_fork or help_with_this_check_in_prompt_gets_concrete_meeting_fork or help_with_this_meeting_prompt_gets_concrete_meeting_fork or help_with_this_agenda_prompt_gets_concrete_agenda_fork or help_with_my_email_prompt_gets_concrete_inbox_fork or drafting_email_to_boss_prompt_gets_drafting_fork or help_with_this_presentation_prompt_gets_concrete_prep_fork or help_planning_tomorrow_prompt_gets_concrete_tomorrow_fork or help_with_my_follow_up_prompt_gets_concrete_follow_up_fork or deciding_between_two_jobs_prompt_gets_decision_fork or hard_conversation_prompt_gets_concrete_conversation_fork or scheduling_around_constraints_prompt_gets_constraints_fork"
```

Post-repair smoke:

```bash
python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
prompts = [
    "I need help with my one-on-one.",
    "I need help getting ready for my one-on-one.",
    "I need help preparing for my one-on-one.",
    "I need help with my 1:1.",
    "I need help with this check-in.",
    "I need help with this meeting.",
    "I need help with this agenda.",
    "I need help with my email.",
    "I need help drafting an email to my boss.",
    "I need help with this presentation.",
    "I need help planning tomorrow.",
    "I need help with my follow-up.",
    "I need help deciding between two apartments.",
    "I need help with a hard conversation.",
    "I need help scheduling around constraints.",
]
for prompt in prompts:
    print(f'PROMPT: {prompt}')
    print(generate_companion_fallback(prompt, packet))
    print()
PY
```

## Exact results

Pre-repair repo truth:
- all five target prompts fell to the generic practical sorter instead of the meeting fork

Compile:
- `python3 -m py_compile jarvis/companion_spine.py tests/test_companion_spine.py`
- result: passed

Focused pytest:
- `15 passed, 318 deselected in 0.25s`

Post-repair smoke:
- `I need help with my one-on-one.` -> `Good. Is the real work for this meeting the outcome you need, how you need to say it, or the agenda you need to walk in with?`
- `I need help getting ready for my one-on-one.` -> same meeting fork
- `I need help preparing for my one-on-one.` -> same meeting fork
- `I need help with my 1:1.` -> same meeting fork
- `I need help with this check-in.` -> same meeting fork

Preserved nearby controls stayed on their existing concrete seams:
- `this meeting` -> meeting fork
- `this agenda` -> agenda fork
- `my email` -> inbox fork
- `drafting an email to my boss` -> drafting fork
- `this presentation` -> presentation-prep fork
- `planning tomorrow` -> tomorrow-planning fork
- `my follow-up` -> follow-up fork
- `deciding between two apartments` -> decision fork
- `a hard conversation` -> hard-conversation fork
- `scheduling around constraints` -> constraints-scheduling fork

## Follow-up recommendation

No stronger remaining defect became visible inside this narrow validation set. The cleanest next move is another fresh live-use reassessment rather than guessing the next family from adjacency alone.
