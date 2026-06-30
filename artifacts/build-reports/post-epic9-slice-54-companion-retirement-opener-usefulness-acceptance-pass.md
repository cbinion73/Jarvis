## A. Exact Prompts Tested
- `I want to retire.`
- `Help me think through retirement.`
- `I am thinking about retirement.`
- `I might step back from work.`
- `I want to slow down at work for good.`
- `I think I am ready to step away from work for good.`
- `I want to ease out of work.`
- additional nearby retirement-shaped probes:
  - `I want to wind down my career for good.`
  - `I want to be done working soon.`
- bounded controls:
  - `I want to work less.`
  - `I am burned out at work.`
  - `I need a vacation.`

## B. Defect Found
- Yes.
- One real remaining bounded usefulness defect was present at the start of this pass:
  - `I think I am ready to step away from work for good.` still fell through to the generic fallback even though it is clearly adjacent to the already-approved `step back from work` / `slow down at work for good` retirement opener aliases.
- After repairing that smallest local issue, the seam still does not look fully acceptance-complete because two additional nearby retirement-shaped prompts remain generic:
  - `I want to wind down my career for good.`
  - `I want to be done working soon.`

## C. Exact Code / Tests Changed
- Code changed:
  - `jarvis/companion_spine.py`
  - Added one additional standalone retirement opener alias:
    - `step away from work for good`
- Tests changed:
  - `tests/test_companion_spine.py`
  - Added focused opener coverage for:
    - `I think I am ready to step away from work for good.`
- Existing negative controls remained in place:
  - `I want to work less.`
  - `I am burned out at work.`

## D. Exact Verification Commands Run
- Compile:
  - `python3 -m py_compile jarvis/companion_spine.py tests/test_companion_spine.py`
- Focused pytest:
  - `python3 -m pytest -q tests/test_companion_spine.py -k "step_back_from_work_prompt_gets_retirement_fork or slow_down_at_work_for_good_prompt_gets_retirement_fork or step_away_from_work_for_good_prompt_gets_retirement_fork or ease_out_of_work_prompt_gets_retirement_fork or work_less_prompt_does_not_get_retirement_fork or burned_out_prompt_does_not_get_retirement_fork"`
- Compact in-process smoke:
  - `python3 - <<'PY'`
  - `from jarvis.companion_spine import generate_companion_fallback`
  - `packet={'available_capabilities':['ongoing conversation in this shell','conversation turn persistence']}`
  - `prompts=[`
  - `    'I want to retire.',`
  - `    'Help me think through retirement.',`
  - `    'I am thinking about retirement.',`
  - `    'I might step back from work.',`
  - `    'I want to slow down at work for good.',`
  - `    'I think I am ready to step away from work for good.',`
  - `    'I want to ease out of work.',`
  - `    'I want to wind down my career for good.',`
  - `    'I want to be done working soon.',`
  - `    'I want to work less.',`
  - `    'I am burned out at work.',`
  - `    'I need a vacation.',`
  - `]`
  - `for prompt in prompts:`
  - `    print(f'PROMPT: {prompt}\\nREPLY: {generate_companion_fallback(prompt, packet)}\\n')`
  - `PY`

## E. Verification Results
- Compile:
  - passed with no output
- Focused pytest:
  - `6 passed, 148 deselected in 0.17s`
- Smoke proof:
  - Retirement opener works for:
    - `I want to retire.`
    - `Help me think through retirement.`
    - `I am thinking about retirement.`
    - `I might step back from work.`
    - `I want to slow down at work for good.`
    - `I think I am ready to step away from work for good.`
    - `I want to ease out of work.`
  - Bounded controls still stay out:
    - `I want to work less.`
    - `I am burned out at work.`
    - `I need a vacation.`
  - Remaining nearby retirement-shaped prompts still generic:
    - `I want to wind down my career for good.`
    - `I want to be done working soon.`

## F. Recommendation
- Another bounded pass
- This acceptance pass repaired one real alias gap, but the retirement opener is not yet clean enough to close on acceptance evidence from current repo truth.
- The next pass should stay narrow and decide whether one final retirement-exit phrasing family should be absorbed, or whether the current boundary is the truthful stopping point.
