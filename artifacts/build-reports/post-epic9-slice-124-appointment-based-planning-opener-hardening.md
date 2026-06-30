# Post-Epic 9 Slice 124: Companion Appointment-Based Planning Opener Hardening

Ready for Architect Office review: yes

## Exact prompts inspected

Target appointment-based planning family:
- `I need help planning around two appointments.`
- `I need help planning around my appointments.`
- `I need help scheduling around appointments.`
- `I need help around my appointments tomorrow.`

Preserved nearby controls:
- `I need help planning around two meetings.`
- `I need help planning around constraints.`
- `I need help scheduling around constraints.`
- `I need help planning tomorrow.`
- `I need help with this meeting.`
- `I need help with my follow-up.`
- `I need help with my email.`
- `I need help with this presentation.`
- `I need help deciding between two apartments.`
- `I need help with a hard conversation.`

## Exact code/tests changed

Code:
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:738)
  - extended `_is_tomorrow_planning_request(...)` with the bounded appointment-based planning aliases:
    - `help planning around two appointments`
    - `help planning around my appointments`
    - `help scheduling around appointments`
    - `help around my appointments tomorrow`
  - kept the repair inside the existing tomorrow-planning opener seam so these prompts land on a concrete planning fork instead of the generic practical sorter

Tests:
- [tests/test_companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/tests/test_companion_spine.py:582)
  - added focused opener coverage for all four appointment-based planning prompts
  - preserved nearby control validation through the focused pytest battery

## Exact commands run

Pre-repair smoke:

```bash
python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet={"available_capabilities":["ongoing conversation in this shell","conversation turn persistence"]}
prompts=[
    "I need help planning around two appointments.",
    "I need help planning around my appointments.",
    "I need help scheduling around appointments.",
    "I need help around my appointments tomorrow.",
    "I need help planning around two meetings.",
    "I need help planning around constraints.",
    "I need help scheduling around constraints.",
    "I need help planning tomorrow.",
    "I need help with this meeting.",
    "I need help with my follow-up.",
    "I need help with my email.",
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
python3 -m pytest -q tests/test_companion_spine.py -k "planning_around_two_appointments_prompt_gets_concrete_tomorrow_fork or planning_around_my_appointments_prompt_gets_concrete_tomorrow_fork or scheduling_around_appointments_prompt_gets_concrete_tomorrow_fork or help_around_my_appointments_tomorrow_prompt_gets_concrete_tomorrow_fork or planning_around_two_meetings_prompt_gets_concrete_tomorrow_fork or planning_around_constraints_prompt_gets_constraints_fork or scheduling_around_constraints_prompt_gets_constraints_fork or help_planning_tomorrow_prompt_gets_concrete_tomorrow_fork or help_with_this_meeting_prompt_gets_concrete_meeting_fork or help_with_my_follow_up_prompt_gets_concrete_follow_up_fork or help_with_my_email_prompt_gets_concrete_inbox_fork or help_with_this_presentation_prompt_gets_concrete_prep_fork or deciding_between_two_jobs_prompt_gets_decision_fork or hard_conversation_prompt_gets_concrete_conversation_fork"
```

Post-repair smoke:

```bash
python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet={"available_capabilities":["ongoing conversation in this shell","conversation turn persistence"]}
prompts=[
    "I need help planning around two appointments.",
    "I need help planning around my appointments.",
    "I need help scheduling around appointments.",
    "I need help around my appointments tomorrow.",
    "I need help planning around two meetings.",
    "I need help planning around constraints.",
    "I need help scheduling around constraints.",
    "I need help planning tomorrow.",
    "I need help with this meeting.",
    "I need help with my follow-up.",
    "I need help with my email.",
    "I need help with this presentation.",
    "I need help deciding between two apartments.",
    "I need help with a hard conversation.",
]
for prompt in prompts:
    print(f'PROMPT: {prompt}')
    print(generate_companion_fallback(prompt, packet))
    print()
PY
```

## Exact results

Pre-repair repo truth:
- all four target prompts fell to the generic practical sorter instead of a nearby concrete planning fork

Compile:
- `python3 -m py_compile jarvis/companion_spine.py tests/test_companion_spine.py`
- result: passed

Focused pytest:
- `14 passed, 336 deselected in 0.24s`

Post-repair smoke:
- `I need help planning around two appointments.` -> `Good. For tomorrow, what actually has to happen, what is fixed, and what can slip?`
- `I need help planning around my appointments.` -> same tomorrow-planning fork
- `I need help scheduling around appointments.` -> same tomorrow-planning fork
- `I need help around my appointments tomorrow.` -> same tomorrow-planning fork

Preserved nearby controls stayed on their existing concrete seams:
- `planning around two meetings` -> tomorrow-planning fork
- `planning around constraints` -> constraints-scheduling fork
- `scheduling around constraints` -> constraints-scheduling fork
- `planning tomorrow` -> tomorrow-planning fork
- `this meeting` -> meeting fork
- `my follow-up` -> follow-up fork
- `my email` -> inbox fork
- `this presentation` -> presentation-prep fork
- `deciding between two apartments` -> decision fork
- `a hard conversation` -> hard-conversation fork

## Follow-up recommendation

No stronger remaining defect became visible inside this narrow validation set. The cleanest next move is another fresh live-use reassessment rather than guessing the next family from adjacency alone.
