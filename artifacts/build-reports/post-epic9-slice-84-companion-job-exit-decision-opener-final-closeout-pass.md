# Post-Epic 9 Slice 84: Companion Job-Exit Decision Opener Final Closeout Pass

Ready for Architect Office review: yes

## Exact prompts tested

Remaining nearby job-exit phrases under closeout review:
- `I might need to walk away from this job.`
- `I may need to leave this company.`

Preserved genuine job-exit controls rechecked:
- `I think I should quit.`
- `I think I should leave my job.`
- `I think I need to put in my notice.`

## Whether a defect was found

No new defect was found in the current repo truth.

Both remaining nearby job-exit phrases already truthfully belong inside the existing job-exit decision opener seam, and they already route correctly to the concrete decision fork:
- `walk away from this job`
- `leave this company`

The current boundary also remains intact:
- this slice did not widen into burnout, dislike, retirement, or generic career dissatisfaction routing

## Exact code/tests changed

No code or test changes were needed in this slice.

Current repo-truth seam already includes the remaining closeout phrases:
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:137)
  - `walk away from this job`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:138)
  - `leave this company`

Current focused regression coverage already exists:
- [tests/test_companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/tests/test_companion_spine.py:751)
  - `test_walk_away_from_this_job_prompt_gets_decision_fork`
- [tests/test_companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/tests/test_companion_spine.py:758)
  - `test_leave_this_company_prompt_gets_decision_fork`

## Exact commands run

```bash
python3 -m py_compile jarvis/companion_spine.py tests/test_companion_spine.py
python3 -m pytest -q tests/test_companion_spine.py -k "walk_away_from_this_job_prompt_gets_decision_fork or leave_this_company_prompt_gets_decision_fork or quit_prompt_gets_decision_fork or leave_my_job_prompt_gets_decision_fork or put_in_my_notice_prompt_gets_decision_fork"
python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
prompts = [
    "I might need to walk away from this job.",
    "I may need to leave this company.",
    "I think I should quit.",
    "I think I should leave my job.",
    "I think I need to put in my notice.",
]
for prompt in prompts:
    reply = generate_companion_fallback(prompt, packet)
    print(f"PROMPT: {prompt}\nREPLY: {reply}\n")
PY
```

## Exact results

- `py_compile`: passed
- focused pytest: `5 passed, 259 deselected`
- in-process smoke:
  - `I might need to walk away from this job.` routes to:
    - `Let's make the decision concrete. Is this mostly about money, energy, risk, or which choice you'd regret not taking?`
  - `I may need to leave this company.` routes to:
    - `Let's make the decision concrete. Is this mostly about money, energy, risk, or which choice you'd regret not taking?`
  - preserved core controls still route to the same concrete decision fork:
    - `I think I should quit.`
    - `I think I should leave my job.`
    - `I think I need to put in my notice.`

## Recommendation

Approve.

This slice closes the remaining job-exit opener family on acceptance evidence only. Current repo truth already contains the bounded behavior and focused regression coverage, so no further repair was needed.
