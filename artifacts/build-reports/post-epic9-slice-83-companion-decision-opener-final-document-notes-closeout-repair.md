# Post-Epic 9 Slice 83: Companion Decision Opener Final Document-Notes Closeout Repair

Ready for Architect Office review: yes

## Exact prompts tested

Remaining document-shaped decision prompt under review:
- `I need help with this decision notes.`

Genuine decision controls rechecked:
- `I need help deciding between two jobs.`
- `I need help choosing.`
- `I need help making a decision.`

## Whether a defect was found

Yes.

One remaining adjacent document-family leak still existed:
- `I need help with this decision notes.`

That prompt belongs with the same bounded decision document-writing family already guarded by:
- `memo`
- `outline`
- `review`
- `summary`
- `recap`
- `overview`
- `chapter`
- `log`

It does not truthfully belong in the concrete decision fork.

## Exact code/tests changed

Code change:
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:945)
  - Added `notes` to the existing `decision_document_terms` guard inside `_is_decision_shaped_request`.

Test changes:
- [tests/test_companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/tests/test_companion_spine.py:810)
  - Added focused regression coverage for:
    - `I need help with this decision notes.`
  - Reused already-correct decision controls:
    - `I need help deciding between two jobs.`
    - `I need help choosing.`
    - `I need help making a decision.`

## Exact commands run

```bash
python3 -m py_compile jarvis/companion_spine.py tests/test_companion_spine.py
python3 -m pytest -q tests/test_companion_spine.py -k "decision_notes_prompt_does_not_get_decision_fork or deciding_between_two_jobs_prompt_gets_decision_fork or help_choosing_prompt_gets_decision_fork or decision_shaped_job_prompt_gets_decision_fork"
python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
prompts = [
    "I need help with this decision notes.",
    "I need help deciding between two jobs.",
    "I need help choosing.",
    "I need help making a decision.",
]
for prompt in prompts:
    reply = generate_companion_fallback(prompt, packet)
    print(f"PROMPT: {prompt}\nREPLY: {reply}\n")
PY
```

## Exact results

- `py_compile`: passed
- focused pytest: `4 passed, 260 deselected`
- in-process smoke:
  - `decision notes` now stays out of the concrete decision fork
  - `deciding between two jobs`, `help choosing`, and `making a decision` still route to:
    - `Let's make the decision concrete. Is this mostly about money, energy, risk, or which choice you'd regret not taking?`

## Recommendation

Approve.

This is a one-term extension of the existing bounded decision document-writing guard. It closes the remaining `decision notes` leak without broadening the decision seam beyond the current document-family boundary.
