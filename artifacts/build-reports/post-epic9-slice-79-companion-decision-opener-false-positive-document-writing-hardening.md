# Post-Epic 9 Slice 79: Companion Decision Opener False-Positive Document-Writing Hardening

Ready for Architect Office review: yes

## Exact prompts tested

False-positive document-writing probes:
- `I need help with this job decision memo.`
- `I need help with this decision memo.`
- `I need help with this decision outline.`
- `I need help with this decision review.`

Under-routing decision probes:
- `I need help deciding between two jobs.`
- `I need help choosing.`

True in-bounds decision control:
- `I need help making a decision.`

## Whether a defect was found

Yes.

The decision seam had a split matcher defect:

- bare `decision` was too broad and overmatched document-shaped prompts like `decision memo`
- the verb forms `deciding` and `choosing` were missing, so genuine decision asks under-routed to the generic practical sorter

## Exact code/tests changed

Code changes:
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:115)
  - Added the missing decision verb forms to `DECISION_REQUEST_TERMS`:
    - `deciding`
    - `choosing`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:941)
  - Added a narrow `decision_document_terms` guard in `_is_decision_shaped_request` for:
    - `memo`
    - `outline`
    - `review`
  - Prevented document-shaped `decision` prompts from entering the concrete decision fork.

Test changes:
- [tests/test_companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/tests/test_companion_spine.py:765)
  - Added focused regression coverage for:
    - `job decision memo`
    - `decision memo`
    - `decision outline`
    - `decision review`
    - `deciding between two jobs`
    - `help choosing`

## Exact verification commands run

```bash
python3 -m py_compile jarvis/companion_spine.py tests/test_companion_spine.py
python3 -m pytest -q tests/test_companion_spine.py -k "job_decision_memo_prompt_does_not_get_decision_fork or decision_memo_prompt_does_not_get_decision_fork or decision_outline_prompt_does_not_get_decision_fork or decision_review_prompt_does_not_get_decision_fork or deciding_between_two_jobs_prompt_gets_decision_fork or help_choosing_prompt_gets_decision_fork or decision_shaped_job_prompt_gets_decision_fork"
python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
prompts = [
    "I need help with this job decision memo.",
    "I need help with this decision memo.",
    "I need help with this decision outline.",
    "I need help with this decision review.",
    "I need help deciding between two jobs.",
    "I need help choosing.",
    "I need help making a decision.",
]
for prompt in prompts:
    reply = generate_companion_fallback(prompt, packet)
    print(f"PROMPT: {prompt}\nREPLY: {reply}\n")
PY
```

## Verification results

- `py_compile`: passed
- focused pytest: `7 passed, 251 deselected`
- in-process smoke:
  - all document-shaped decision prompts stayed out of the concrete decision fork
  - `deciding between two jobs`, `help choosing`, and `making a decision` all routed to:
    - `Let's make the decision concrete. Is this mostly about money, energy, risk, or which choice you'd regret not taking?`

## Recommendation

Approve.

This is a narrow overmatch-and-underrouting repair inside the decision seam only. It removes document-writing false positives while pulling the nearby genuine decision verb forms into the existing concrete decision fork.
