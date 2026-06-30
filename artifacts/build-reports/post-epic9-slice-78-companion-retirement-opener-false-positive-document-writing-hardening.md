# Post-Epic 9 Slice 78: Companion Retirement Opener False-Positive Document-Writing Hardening

Ready for Architect Office review: yes

## Exact prompts tested

False-positive document-writing probes:
- `I need help with this retirement essay.`
- `I need help with this retirement memo.`
- `I need help with this retirement chapter.`
- `I need help with this retirement review.`
- `I need help with this retirement overview.`
- `I need help with this retirement outline.`
- `I need help with this retirement recap.`

True retirement controls:
- `I need help planning retirement.`
- `I want to retire.`

## Whether a defect was found

Yes.

The standalone retirement opener was overmatching on `retirement` inside document-shaped prompts, which incorrectly routed writing requests into the retirement fork.

Before repair, all of these wrongly triggered the retirement opener:
- `I need help with this retirement essay.`
- `I need help with this retirement memo.`
- `I need help with this retirement chapter.`
- `I need help with this retirement review.`
- `I need help with this retirement overview.`
- `I need help with this retirement outline.`
- `I need help with this retirement recap.`

## Exact code/tests changed

Code change:
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:356)
  - Added a narrow `retirement_document_terms` guard for:
    - `essay`
    - `memo`
    - `chapter`
    - `review`
    - `overview`
    - `outline`
    - `recap`
  - Prevented the retirement opener from firing when those document-shaped terms are present alongside `retirement`.

Test changes:
- [tests/test_companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/tests/test_companion_spine.py:1944)
  - Added focused regression coverage for all seven retirement document-writing prompts above.
  - Added one true in-bounds retirement control:
    - `I need help planning retirement.`
  - Reused `I want to retire.` as the core retirement control in the focused proof.

## Exact verification commands run

```bash
python3 -m py_compile jarvis/companion_spine.py tests/test_companion_spine.py
python3 -m pytest -q tests/test_companion_spine.py -k "retirement_essay_prompt_does_not_get_retirement_fork or retirement_memo_prompt_does_not_get_retirement_fork or retirement_chapter_prompt_does_not_get_retirement_fork or retirement_review_prompt_does_not_get_retirement_fork or retirement_overview_prompt_does_not_get_retirement_fork or retirement_outline_prompt_does_not_get_retirement_fork or retirement_recap_prompt_does_not_get_retirement_fork or planning_retirement_prompt_gets_retirement_fork or retire_prompt_does_not_get_decision_fork"
python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
prompts = [
    "I need help with this retirement essay.",
    "I need help with this retirement memo.",
    "I need help with this retirement chapter.",
    "I need help with this retirement review.",
    "I need help with this retirement overview.",
    "I need help with this retirement outline.",
    "I need help with this retirement recap.",
    "I need help planning retirement.",
    "I want to retire.",
]
for prompt in prompts:
    reply = generate_companion_fallback(prompt, packet)
    print(f"PROMPT: {prompt}\nREPLY: {reply}\n")
PY
```

## Verification results

- `py_compile`: passed
- focused pytest: `9 passed, 243 deselected`
- in-process smoke:
  - all document-shaped retirement prompts stayed out of the retirement fork
  - the true retirement controls still routed to:
    - `For you, I don't think retirement means doing nothing. I think it means getting work out of the driver's seat. Do you want to think about money, time, or identity first?`

## Recommendation

Approve.

This is a narrow opener overmatch repair inside the standalone retirement seam only. It removes document-writing false positives without widening into a broader retirement-writing classifier.
