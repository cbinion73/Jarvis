# Post-Epic 9 Slice 122: Companion Tomorrow-Calendar Opener Hardening

Ready for Architect Office review: yes

## Exact prompts inspected

Target tomorrow-calendar family:
- `I need help with my calendar tomorrow.`
- `I need help with my calendar for tomorrow.`

Preserved nearby controls:
- `I need help with tomorrow's calendar.`
- `I need help planning tomorrow.`
- `I need help scheduling tomorrow.`
- `I need help organizing tomorrow.`
- `I need help with my calendar this week.`
- `I need help with my schedule this week.`
- `I need help scheduling around constraints.`
- `I need help with this meeting.`
- `I need help with my follow-up.`
- `I need help with my email.`
- `I need help drafting an email to my boss.`
- `I need help deciding between two apartments.`
- `I need help with a hard conversation.`

## Exact code/tests changed

Code:
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:738)
  - extended `_is_tomorrow_planning_request(...)` with the bounded tomorrow-calendar aliases:
    - `help with my calendar tomorrow`
    - `help with my calendar for tomorrow`
  - kept the repair inside the existing tomorrow-planning opener seam so those prompts route to the tomorrow fork before the overloaded-week `calendar` trigger can misclassify them

Tests:
- [tests/test_companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/tests/test_companion_spine.py:558)
  - added focused opener coverage for both tomorrow-calendar prompts
  - added a guard test proving `I need help with my calendar this week.` still stays on the overloaded-week capacity-pushback lane

## Exact commands run

Pre-repair smoke:

```bash
python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet={"available_capabilities":["ongoing conversation in this shell","conversation turn persistence"]}
prompts=[
    "I need help with my calendar tomorrow.",
    "I need help with my calendar for tomorrow.",
    "I need help with tomorrow's calendar.",
    "I need help planning tomorrow.",
    "I need help scheduling tomorrow.",
    "I need help organizing tomorrow.",
    "I need help with my calendar this week.",
    "I need help with this meeting.",
    "I need help with my follow-up.",
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
python3 -m pytest -q tests/test_companion_spine.py -k "help_with_my_calendar_tomorrow_prompt_gets_concrete_tomorrow_fork or help_with_my_calendar_for_tomorrow_prompt_gets_concrete_tomorrow_fork or help_with_my_calendar_this_week_prompt_keeps_capacity_pushback or help_with_my_schedule_tomorrow_prompt_gets_concrete_tomorrow_fork or help_with_my_schedule_for_tomorrow_prompt_gets_concrete_tomorrow_fork or help_with_my_schedule_this_week_prompt_keeps_capacity_pushback or help_planning_tomorrow_prompt_gets_concrete_tomorrow_fork or help_scheduling_tomorrow_prompt_gets_concrete_tomorrow_fork or help_organizing_tomorrow_prompt_gets_concrete_tomorrow_fork or scheduling_around_constraints_prompt_gets_constraints_fork or help_with_this_meeting_prompt_gets_concrete_meeting_fork or help_with_my_follow_up_prompt_gets_concrete_follow_up_fork or help_with_my_email_prompt_gets_concrete_inbox_fork or drafting_email_to_boss_prompt_gets_drafting_fork or deciding_between_two_jobs_prompt_gets_decision_fork or hard_conversation_prompt_gets_concrete_conversation_fork"
```

Post-repair smoke:

```bash
python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet={"available_capabilities":["ongoing conversation in this shell","conversation turn persistence"]}
prompts=[
    "I need help with my calendar tomorrow.",
    "I need help with my calendar for tomorrow.",
    "I need help with tomorrow's calendar.",
    "I need help planning tomorrow.",
    "I need help scheduling tomorrow.",
    "I need help organizing tomorrow.",
    "I need help with my calendar this week.",
    "I need help with my schedule this week.",
    "I need help scheduling around constraints.",
    "I need help with this meeting.",
    "I need help with my follow-up.",
    "I need help with my email.",
    "I need help drafting an email to my boss.",
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
- `I need help with my calendar tomorrow.` -> overloaded-week pushback fork
- `I need help with my calendar for tomorrow.` -> overloaded-week pushback fork

Compile:
- `python3 -m py_compile jarvis/companion_spine.py tests/test_companion_spine.py`
- result: passed

Focused pytest:
- `16 passed, 330 deselected in 0.61s`

Post-repair smoke:
- `I need help with my calendar tomorrow.` -> `Good. For tomorrow, what actually has to happen, what is fixed, and what can slip?`
- `I need help with my calendar for tomorrow.` -> same tomorrow-planning fork

Preserved nearby controls stayed correct:
- `tomorrow's calendar` -> tomorrow-planning fork
- `planning tomorrow` -> tomorrow-planning fork
- `scheduling tomorrow` -> tomorrow-planning fork
- `organizing tomorrow` -> tomorrow-planning fork
- `my calendar this week` -> overloaded-week capacity-pushback fork
- `my schedule this week` -> overloaded-week capacity-pushback fork
- `scheduling around constraints` -> constraints-scheduling fork
- `this meeting` -> meeting fork
- `my follow-up` -> follow-up fork
- `my email` -> inbox fork
- `drafting an email to my boss` -> drafting fork
- `deciding between two apartments` -> decision fork
- `a hard conversation` -> hard-conversation fork

## Follow-up recommendation

No stronger remaining defect became visible inside this narrow validation set. The cleanest next move is another fresh live-use reassessment rather than guessing the next family from adjacency alone.
