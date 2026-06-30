# Post-Epic 9 Slice 81: Companion Decision Opener Final Document-Recap Repair

Ready for Architect Office review: yes

## Exact prompts tested

Remaining document-shaped decision prompt under review:
- `I need help with this decision recap.`

Genuine decision controls rechecked:
- `I need help deciding between two jobs.`
- `I need help choosing.`
- `I need help making a decision.`

## Whether a defect was found

Yes.

One remaining adjacent document-family leak still existed:
- `I need help with this decision recap.`

That prompt belongs with the same bounded decision document-writing family already guarded by:
- `memo`
- `outline`
- `review`
- `summary`

It does not truthfully belong in the concrete decision fork.

## Exact code/tests changed if any

Code change:
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:945)
  - Added `recap` to the existing `decision_document_terms` guard inside `_is_decision_shaped_request`.

Context retained:
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:115)
  - The earlier `deciding` / `choosing` repair stayed intact so genuine decision asks continue to route correctly.

Test changes:
- [tests/test_companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/tests/test_companion_spine.py:790)
  - Added focused regression coverage for:
    - `I need help with this decision recap.`
  - Reused already-correct decision controls:
    - `I need help deciding between two jobs.`
    - `I need help choosing.`
    - `I need help making a decision.`

## Exact verification commands run

```bash
python3 -m py_compile jarvis/companion_spine.py tests/test_companion_spine.py
python3 -m pytest -q tests/test_companion_spine.py -k "decision_recap_prompt_does_not_get_decision_fork or deciding_between_two_jobs_prompt_gets_decision_fork or help_choosing_prompt_gets_decision_fork or decision_shaped_job_prompt_gets_decision_fork"
python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
prompts = [
    "I need help with this decision recap.",
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
- focused pytest: `4 passed, 255 deselected`
- in-process smoke:
  - `decision recap` now stays out of the concrete decision fork
  - `deciding between two jobs`, `help choosing`, and `making a decision` still route to:
    - `Let's make the decision concrete. Is this mostly about money, energy, risk, or which choice you'd regret not taking?`

## Recommendation

Approve.

This final repair is a one-word extension of the existing document-writing guard inside the decision seam only. It closes the remaining leak without widening scope beyond the current bounded decision opener behavior.
