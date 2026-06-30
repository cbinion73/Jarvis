## A. Exact Prompts Tested
- retirement opener prompts already in lane:
  - `I want to retire.`
  - `I might step back from work.`
  - `I want to slow down at work for good.`
  - `I think I am ready to step away from work for good.`
  - `I want to ease out of work.`
- remaining retirement-exit family under review:
  - `I want to wind down my career for good.`
  - `I want to be done working soon.`
- nearby family checks:
  - `I want to wind down my career.`
  - `I think I am ready to be done working soon.`
- bounded controls:
  - `I want to work less.`
  - `I am burned out at work.`
  - `I want to end my career soon.`

## B. Whether a Defect Was Found
- Yes.
- The remaining retirement-exit family still fell through to the generic fallback even though it clearly belonged with the existing retirement opener:
  - `I want to wind down my career for good.`
  - `I want to be done working soon.`

## C. Exact Code / Tests Changed
- Code changed:
  - `jarvis/companion_spine.py`
  - Added two bounded retirement-exit opener aliases:
    - `wind down my career`
    - `be done working soon`
- Tests changed:
  - `tests/test_companion_spine.py`
  - Added focused positive coverage for:
    - `I want to wind down my career for good.`
    - `I want to be done working soon.`
  - Added one bounded negative control to show the seam did not broaden farther than intended:
    - `I want to end my career soon.`

## D. Exact Verification Commands Run
- Compile:
  - `python3 -m py_compile jarvis/companion_spine.py tests/test_companion_spine.py`
- Focused pytest:
  - `python3 -m pytest -q tests/test_companion_spine.py -k "step_back_from_work_prompt_gets_retirement_fork or slow_down_at_work_for_good_prompt_gets_retirement_fork or step_away_from_work_for_good_prompt_gets_retirement_fork or ease_out_of_work_prompt_gets_retirement_fork or wind_down_my_career_prompt_gets_retirement_fork or be_done_working_soon_prompt_gets_retirement_fork or work_less_prompt_does_not_get_retirement_fork or burned_out_prompt_does_not_get_retirement_fork or end_my_career_soon_prompt_does_not_get_retirement_fork"`
- Compact in-process smoke:
  - `python3 - <<'PY'`
  - `from jarvis.companion_spine import generate_companion_fallback`
  - `packet={'available_capabilities':['ongoing conversation in this shell','conversation turn persistence']}`
  - `prompts=[`
  - `    'I want to retire.',`
  - `    'I might step back from work.',`
  - `    'I want to slow down at work for good.',`
  - `    'I think I am ready to step away from work for good.',`
  - `    'I want to ease out of work.',`
  - `    'I want to wind down my career for good.',`
  - `    'I want to be done working soon.',`
  - `    'I want to wind down my career.',`
  - `    'I think I am ready to be done working soon.',`
  - `    'I want to work less.',`
  - `    'I am burned out at work.',`
  - `    'I want to end my career soon.',`
  - `]`
  - `for prompt in prompts:`
  - `    print(f'PROMPT: {prompt}\\nREPLY: {generate_companion_fallback(prompt, packet)}\\n')`
  - `PY`

## E. Verification Results
- Compile:
  - passed with no output
- Focused pytest:
  - `9 passed, 148 deselected in 0.17s`
- Smoke proof:
  - The retirement opener now correctly catches:
    - `I want to retire.`
    - `I might step back from work.`
    - `I want to slow down at work for good.`
    - `I think I am ready to step away from work for good.`
    - `I want to ease out of work.`
    - `I want to wind down my career for good.`
    - `I want to be done working soon.`
    - `I want to wind down my career.`
    - `I think I am ready to be done working soon.`
  - Bounded controls still stay out:
    - `I want to work less.`
    - `I am burned out at work.`
    - `I want to end my career soon.`

## F. Recommendation
- Approve
- This remaining retirement-exit family clearly belonged in the existing retirement opener and is now covered with a narrow, truthful patch.
- Stop here on the current truthful boundary; no additional opener widening looks necessary from repo truth.
