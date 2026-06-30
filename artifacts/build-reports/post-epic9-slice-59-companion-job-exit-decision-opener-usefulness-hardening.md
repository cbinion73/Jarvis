## A. Exact Prompts Tested
- `Help me figure out whether to leave my job.`
- `I think I should quit.`
- `I think I should leave my job.`
- `I think I should resign.`
- `I might need to leave this job.`
- `I want out of this job.`
- `I should probably leave my job.`
- `I might need to quit.`
- bounded controls:
  - `I hate my job.`
  - `I am burned out at work.`
  - `I want to retire.`

## B. Exact Defect Found
- Nearby first-turn quit / leave-my-job phrasing still missed the existing practical decision fork and fell through to the generic fallback.
- Concrete misses before the repair:
  - `I think I should quit.`
  - `I think I should leave my job.`
  - `I think I should resign.`
  - `I might need to leave this job.`
  - `I want out of this job.`

## C. Exact Code / Tests Changed
- Code changed:
  - `jarvis/companion_spine.py`
  - Expanded `DECISION_REQUEST_TERMS` with the smallest local job-exit family:
    - `leave my job`
    - `leave this job`
    - `should quit`
    - `need to quit`
    - `should resign`
    - `need to resign`
    - `want out of this job`
- Tests changed:
  - `tests/test_companion_spine.py`
  - Added focused opener coverage for:
    - `I think I should quit.`
    - `I think I should leave my job.`
    - `I think I should resign.`
  - Added bounded negative controls proving this slice does not over-capture:
    - `I am burned out at work.`
    - `I want to retire.`

## D. Exact Verification Commands Run
- Compile:
  - `python3 -m py_compile jarvis/companion_spine.py tests/test_companion_spine.py`
- Focused pytest:
  - `python3 -m pytest -q tests/test_companion_spine.py -k "decision_shaped_job_prompt_gets_decision_fork or decision_shaped_torn_prompt_gets_decision_fork or quit_prompt_gets_decision_fork or leave_my_job_prompt_gets_decision_fork or resign_prompt_gets_decision_fork or burned_out_prompt_does_not_get_decision_fork or retire_prompt_does_not_get_decision_fork"`
- Compact in-process smoke:
  - `python3 - <<'PY'`
  - `from jarvis.companion_spine import generate_companion_fallback`
  - `packet={'available_capabilities':['ongoing conversation in this shell','conversation turn persistence']}`
  - `prompts=[`
  - `    'Help me figure out whether to leave my job.',`
  - `    'I think I should quit.',`
  - `    'I think I should leave my job.',`
  - `    'I think I should resign.',`
  - `    'I might need to leave this job.',`
  - `    'I want out of this job.',`
  - `    'I should probably leave my job.',`
  - `    'I might need to quit.',`
  - `    'I hate my job.',`
  - `    'I am burned out at work.',`
  - `    'I want to retire.',`
  - `]`
  - `for prompt in prompts:`
  - `    print(f'PROMPT: {prompt}\\nREPLY: {generate_companion_fallback(prompt, packet)}\\n')`
  - `PY`

## E. Verification Results
- Compile:
  - passed with no output
- Focused pytest:
  - `7 passed, 163 deselected in 0.24s`
- Smoke proof:
  - The decision opener now correctly catches:
    - `Help me figure out whether to leave my job.`
    - `I think I should quit.`
    - `I think I should leave my job.`
    - `I think I should resign.`
    - `I might need to leave this job.`
    - `I want out of this job.`
    - `I should probably leave my job.`
    - `I might need to quit.`
  - Bounded controls still stay out:
    - `I hate my job.` -> generic fallback
    - `I am burned out at work.` -> generic fallback
    - `I want to retire.` -> retirement opener

## F. Recommendation
- Approve
- This bounded job-exit opener weakness is repaired cleanly from repo truth.
- If Architect Office wants more confidence, the next step should be an acceptance pass only, not a broader job-transition rewrite.
