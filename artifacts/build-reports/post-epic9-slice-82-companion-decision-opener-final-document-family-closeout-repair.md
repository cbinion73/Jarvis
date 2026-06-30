# Post-Epic 9 Slice 82: Companion Decision Opener Final Document-Family Closeout Repair

Ready for Architect Office review: yes

## Exact prompts tested

Remaining document-shaped decision prompts under review:
- `I need help with this decision overview.`
- `I need help with this decision chapter.`
- `I need help with this decision log.`

Genuine decision controls rechecked:
- `I need help deciding between two jobs.`
- `I need help choosing.`
- `I need help making a decision.`

## Whether a defect was found

Yes.

Fresh repo-truth smoke showed three adjacent document-family leaks still routing into the concrete decision fork:
- `decision overview`
- `decision chapter`
- `decision log`

All three belong with the same bounded decision document-writing family already guarded by:
- `memo`
- `outline`
- `review`
- `summary`
- `recap`

They do not truthfully belong in the concrete decision fork.

## Exact code/tests changed if any

Code change:
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:945)
  - Added `overview`, `chapter`, and `log` to the existing `decision_document_terms` guard inside `_is_decision_shaped_request`.

Context retained:
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:115)
  - The earlier `deciding` / `choosing` repair stayed intact so genuine decision asks continue to route correctly.

Test changes:
- [tests/test_companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/tests/test_companion_spine.py:795)
  - Added focused regression coverage for:
    - `I need help with this decision overview.`
    - `I need help with this decision chapter.`
    - `I need help with this decision log.`
  - Reused already-correct decision controls:
    - `I need help deciding between two jobs.`
    - `I need help choosing.`
    - `I need help making a decision.`

## Exact verification commands run

```bash
python3 -m py_compile jarvis/companion_spine.py tests/test_companion_spine.py
python3 -m pytest -q tests/test_companion_spine.py -k "decision_overview_prompt_does_not_get_decision_fork or decision_chapter_prompt_does_not_get_decision_fork or decision_log_prompt_does_not_get_decision_fork or deciding_between_two_jobs_prompt_gets_decision_fork or help_choosing_prompt_gets_decision_fork or decision_shaped_job_prompt_gets_decision_fork"
python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
prompts = [
    "I need help with this decision overview.",
    "I need help with this decision chapter.",
    "I need help with this decision log.",
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
- focused pytest: `6 passed, 257 deselected`
- in-process smoke:
  - `decision overview`, `decision chapter`, and `decision log` now stay out of the concrete decision fork
  - `deciding between two jobs`, `help choosing`, and `making a decision` still route to:
    - `Let's make the decision concrete. Is this mostly about money, energy, risk, or which choice you'd regret not taking?`

## Recommendation

Approve.

This closes the remaining adjacent document-family leaks inside the current bounded decision opener seam without widening scope beyond the existing document-writing guard.
