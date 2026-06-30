# Post-Epic 9 Slice 126: Companion Tomorrow-Mapping Opener Hardening

## Scope
- Stayed only inside the existing first-turn tomorrow-planning opener seam in [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:738).
- Kept the change bounded to `map out tomorrow` phrasing.
- Did not broaden into generic `outline` / `summary` / `recap` handling.

## Exact Code Changed
- Added two narrow matcher phrases in [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:740):
  - `map out tomorrow`
  - `mapping out tomorrow`
- Added four focused regression tests in [tests/test_companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/tests/test_companion_spine.py:649):
  - `I need help mapping out tomorrow.`
  - `Help me map out tomorrow.`
  - `I need help mapping out tomorrow morning.`
  - `I need help mapping out tomorrow afternoon.`

## Exact Prompts Changed
- `I need help mapping out tomorrow.`
- `Help me map out tomorrow.`
- `I need help mapping out tomorrow morning.`
- `I need help mapping out tomorrow afternoon.`

## Exact Preserved Controls Checked
- `I need help with tomorrow's plan.`
- `I need help planning tomorrow.`
- `I need help planning around two appointments.`
- `I need help planning around constraints.`
- `I need help with this meeting.`
- `I need help with my email.`

## Non-Obvious Boundary Decisions
- I kept the matcher at `map out tomorrow` / `mapping out tomorrow` only.
- I did not broaden into nearby but different phrasing like:
  - `I need help sketching out tomorrow.`
  - `I need help laying out tomorrow.`
- Those still fall to the generic practical sorter in current repo truth, which preserves the requested narrow boundary around tomorrow-mapping language only.
- One clearly-adjacent variant now routes correctly via the same narrow match without extra code:
  - `I need help mapping out tomorrow evening.`

## Exact Commands Run

```bash
python3 -m py_compile jarvis/companion_spine.py tests/test_companion_spine.py

python3 -m pytest -q tests/test_companion_spine.py -k "mapping_out_tomorrow_prompt_gets_concrete_tomorrow_fork or map_out_tomorrow_prompt_gets_concrete_tomorrow_fork or mapping_out_tomorrow_morning_prompt_gets_concrete_tomorrow_fork or mapping_out_tomorrow_afternoon_prompt_gets_concrete_tomorrow_fork or help_with_tomorrows_plan_prompt_gets_concrete_tomorrow_fork or help_planning_tomorrow_prompt_gets_concrete_tomorrow_fork or planning_around_two_appointments_prompt_gets_concrete_tomorrow_fork or planning_around_constraints_prompt_gets_constraints_fork or help_with_this_meeting_prompt_gets_concrete_meeting_fork or help_with_my_email_prompt_gets_concrete_inbox_fork"

python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet = {'available_capabilities': ['ongoing conversation in this shell', 'conversation turn persistence']}
prompts = [
    'I need help mapping out tomorrow.',
    'Help me map out tomorrow.',
    'I need help mapping out tomorrow morning.',
    'I need help mapping out tomorrow afternoon.',
    "I need help with tomorrow's plan.",
    'I need help planning tomorrow.',
    'I need help planning around two appointments.',
    'I need help planning around constraints.',
    'I need help with this meeting.',
    'I need help with my email.',
]
for prompt in prompts:
    print('PROMPT:', prompt)
    print(generate_companion_fallback(prompt, packet))
    print('---')
PY

python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet = {'available_capabilities': ['ongoing conversation in this shell', 'conversation turn persistence']}
prompts = [
    'I need help mapping out tomorrow evening.',
    'I need help sketching out tomorrow.',
    'I need help laying out tomorrow.',
]
for prompt in prompts:
    print('PROMPT:', prompt)
    print(generate_companion_fallback(prompt, packet))
    print('---')
PY
```

## Pytest Results
- `python3 -m py_compile jarvis/companion_spine.py tests/test_companion_spine.py`
  - passed
- Focused pytest:
  - `10 passed, 344 deselected in 0.16s`

## Smoke Results
- Changed prompts now route to the existing tomorrow-planning fork:
  - `Good. For tomorrow, what actually has to happen, what is fixed, and what can slip?`
- Preserved controls still route correctly:
  - `tomorrow's plan` -> tomorrow-planning fork
  - `planning tomorrow` -> tomorrow-planning fork
  - `planning around two appointments` -> tomorrow-planning fork
  - `planning around constraints` -> constraints-scheduling fork
  - `this meeting` -> meeting fork
  - `my email` -> inbox fork

## Recommendation
- Ready for Architect Office review: yes
