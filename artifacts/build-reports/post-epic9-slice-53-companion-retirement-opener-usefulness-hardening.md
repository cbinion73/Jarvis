## A. Exact Prompts Tested
- `I want to retire.`
- `Help me think through retirement.`
- `I am thinking about retirement.`
- `I might step back from work.`
- `I want to slow down at work for good.`
- `I want to ease out of work.`
- bounded controls:
  - `I want to work less.`
  - `I am burned out at work.`
  - `I need a vacation.`

## B. Exact Defect Found
- The explicit retirement opener already worked for direct `retire` / `retirement` phrasing.
- But nearby first-turn retirement-shaped phrasing still fell through to the generic fallback instead of reaching the existing retirement fork.
- Concrete failing prompts before the repair:
  - `I might step back from work.`
  - `I want to slow down at work for good.`
  - `I want to ease out of work.`

## C. Exact Code / Tests Changed
- Code changed:
  - `jarvis/companion_spine.py`
  - Expanded the standalone retirement opener match to include:
    - `step back from work`
    - `slow down at work for good`
    - `ease out of work`
- Tests changed:
  - `tests/test_companion_spine.py`
  - Added focused opener coverage for:
    - `I might step back from work.`
    - `I want to slow down at work for good.`
    - `I want to ease out of work.`
  - Added negative controls proving this slice does not over-capture:
    - `I want to work less.`
    - `I am burned out at work.`

## D. Exact Verification Commands Run
- Compile:
  - `python3 -m py_compile jarvis/companion_spine.py tests/test_companion_spine.py`
- Focused pytest:
  - `python3 -m pytest -q tests/test_companion_spine.py -k "step_back_from_work_prompt_gets_retirement_fork or slow_down_at_work_for_good_prompt_gets_retirement_fork or ease_out_of_work_prompt_gets_retirement_fork or work_less_prompt_does_not_get_retirement_fork or burned_out_prompt_does_not_get_retirement_fork"`
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
  - `    'I want to ease out of work.',`
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
  - `5 passed, 148 deselected in 0.16s`
- Smoke proof:
  - Direct retirement prompts still route to:
    - `For you, I don't think retirement means doing nothing. I think it means getting work out of the driver's seat. Do you want to think about money, time, or identity first?`
  - Newly hardened nearby phrasing now routes to the same retirement fork:
    - `I might step back from work.`
    - `I want to slow down at work for good.`
    - `I want to ease out of work.`
  - Bounded controls remain outside the retirement lane:
    - `I want to work less.` -> generic fallback
    - `I am burned out at work.` -> generic fallback
    - `I need a vacation.` -> vacation opener

## F. Recommendation
- Approve
- This bounded retirement opener weakness is repaired cleanly from repo truth.
- If Architect Office wants another pass, it should be an acceptance pass only, not another widening repair pass.
