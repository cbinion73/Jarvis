## A. Scope Reviewed
- Standalone first-turn vacation opener seam only in `jarvis/companion_spine.py`
- Nearby natural first-turn prompts around:
  - `vacation`
  - `trip`
  - `travel`
  - `get away`
- Explicitly kept `hotel` / `flight` on the logistics-first organizer path

## B. Exact Prompts Tested
- `Help me think through vacation.`
- `I want to plan a trip.`
- `I need a vacation but I do not know what I need.`
- `I need to travel but I am not sure why.`
- `I want to get away for a few days.`
- `We need to get away.`
- `I think we should get away.`
- `I need to go away for a bit.`
- `I need to get out of town.`
- `I want to go on vacation.`
- `We should take a trip.`
- `I need help with travel plans.`
- bounded controls:
  - `I need a break.`
  - `I want to book a hotel.`
  - `I need a flight.`

## C. Defect Found
- Yes: one final bounded usefulness defect remained.
- Nearby getaway phrasing that did not use the exact repaired alias `get away` still fell through to the generic fallback.
- Concrete failures before the repair:
  - `I need to go away for a bit.`
  - `I need to get out of town.`

## D. Exact Code / Tests Changed
- Code changed:
  - `jarvis/companion_spine.py`
  - Extended the standalone vacation opener match to include:
    - `go away`
    - `out of town`
- Tests changed:
  - `tests/test_companion_spine.py`
  - Added focused opener coverage for:
    - `I need to go away for a bit.`
    - `I need to get out of town.`

## E. Exact Verification Commands Run
- Compile:
  - `python3 -m py_compile jarvis/companion_spine.py tests/test_companion_spine.py`
- Focused pytest:
  - `python3 -m pytest -q tests/test_companion_spine.py -k "standalone_vacation_prompt_gets_concrete_fork or trip_planning_prompt_gets_concrete_vacation_fork or uncertain_vacation_prompt_gets_concrete_vacation_fork or get_away_prompt_gets_concrete_vacation_fork or go_away_prompt_gets_concrete_vacation_fork or get_out_of_town_prompt_gets_concrete_vacation_fork"`
- Compact in-process smoke:
  - `python3 - <<'PY'`
  - `from jarvis.companion_spine import generate_companion_fallback`
  - `packet={'available_capabilities':['ongoing conversation in this shell','conversation turn persistence']}`
  - `prompts=[`
  - `    'Help me think through vacation.',`
  - `    'I want to plan a trip.',`
  - `    'I need a vacation but I do not know what I need.',`
  - `    'I need to travel but I am not sure why.',`
  - `    'I want to get away for a few days.',`
  - `    'We need to get away.',`
  - `    'I think we should get away.',`
  - `    'I need to go away for a bit.',`
  - `    'I need to get out of town.',`
  - `    'I want to go on vacation.',`
  - `    'We should take a trip.',`
  - `    'I need help with travel plans.',`
  - `    'I need a break.',`
  - `    'I want to book a hotel.',`
  - `    'I need a flight.',`
  - `]`
  - `for prompt in prompts:`
  - `    print(f'PROMPT: {prompt}\\nREPLY: {generate_companion_fallback(prompt, packet)}\\n')`
  - `PY`

## F. Verification Results
- Compile:
  - passed with no output
- Focused pytest:
  - `6 passed, 142 deselected in 0.17s`
- Smoke proof:
  - `vacation` / `trip` / `travel` / `get away` / `go away` / `out of town` prompts now all route to:
    - `Good. Is the real question where to go, what kind of trip this needs to be, or what is making it hard to land?`
  - `I need a break.` still stays on the generic fallback
  - `hotel` / `flight` still stay on the logistics-first organizer path

## G. Closeout Judgment
- The standalone vacation opener seam is now clean enough to close on acceptance evidence.
- No broader scope expansion was needed.
- No booking, retrieval, memory, or autonomy drift was introduced.

## H. Recommendation
- Approve
- No additional bounded opener pass appears necessary from current repo truth
