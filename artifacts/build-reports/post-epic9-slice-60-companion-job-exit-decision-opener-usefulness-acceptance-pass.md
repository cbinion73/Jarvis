## A. Exact Prompts Tested
- already-covered opener family:
  - `Help me figure out whether to leave my job.`
  - `I think I should quit.`
  - `I think I should leave my job.`
  - `I think I should resign.`
  - `I might need to leave this job.`
  - `I want out of this job.`
  - `I should probably leave my job.`
  - `I might need to quit.`
- additional nearby first-turn probes:
  - `I should probably resign.`
  - `I may need to quit.`
  - `I should leave this job.`
  - `I think I need to leave this job.`
  - `I want to quit my job.`
- bounded controls:
  - `I hate my job.`
  - `I am burned out at work.`
  - `I want to retire.`

## B. Whether a Defect Was Found
- Yes.
- One real remaining bounded usefulness defect was present at the start of this pass:
  - shorthand job-exit phrasing built around `resign` and `quit my job` still fell through to the generic fallback.
- Concrete misses before the repair:
  - `I should probably resign.`
  - `I want to quit my job.`

## C. Exact Code / Tests Changed
- Code changed:
  - `jarvis/companion_spine.py`
  - Expanded `DECISION_REQUEST_TERMS` with the smallest remaining job-exit aliases:
    - `quit my job`
    - `resign`
- Tests changed:
  - `tests/test_companion_spine.py`
  - Added focused opener coverage for:
    - `I should probably resign.`
    - `I want to quit my job.`
- Existing bounded controls remained in place:
  - `I am burned out at work.`
  - `I want to retire.`

## D. Exact Verification Commands Run
- Compile:
  - `python3 -m py_compile jarvis/companion_spine.py tests/test_companion_spine.py`
- Focused pytest:
  - `python3 -m pytest -q tests/test_companion_spine.py -k "decision_shaped_job_prompt_gets_decision_fork or decision_shaped_torn_prompt_gets_decision_fork or quit_prompt_gets_decision_fork or leave_my_job_prompt_gets_decision_fork or resign_prompt_gets_decision_fork or should_probably_resign_prompt_gets_decision_fork or quit_my_job_prompt_gets_decision_fork or burned_out_prompt_does_not_get_decision_fork or retire_prompt_does_not_get_decision_fork"`
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
  - `    'I should probably resign.',`
  - `    'I may need to quit.',`
  - `    'I should leave this job.',`
  - `    'I think I need to leave this job.',`
  - `    'I want to quit my job.',`
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
  - `9 passed, 163 deselected in 0.17s`
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
    - `I should probably resign.`
    - `I may need to quit.`
    - `I should leave this job.`
    - `I think I need to leave this job.`
    - `I want to quit my job.`
  - Bounded controls still stay out:
    - `I hate my job.` -> generic fallback
    - `I am burned out at work.` -> generic fallback
    - `I want to retire.` -> retirement opener

## F. Recommendation
- Approve
- This acceptance pass repaired one last small job-exit alias family, and the standalone opener now holds cleanly across the nearby first-turn phrasing tested here.
- If Architect Office wants another step, it should be a closeout pass only, not more widening work.
