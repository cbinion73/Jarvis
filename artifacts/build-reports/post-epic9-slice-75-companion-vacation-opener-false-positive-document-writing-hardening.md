# Post-Epic 9 Slice 75: Companion Vacation Opener False-Positive Document-Writing Hardening

Ready for Architect Office review: yes

## Exact prompts tested

False-positive document-writing probes:
- `I need help with this travel essay.`
- `I need help with this travel chapter.`
- `I need help with this travel memo.`
- `I need help with this trip report.`
- `I need help with this vacation note.`
- `I need help with this hotel review.`

True vacation/travel controls:
- `I need to plan a trip.`
- `I need help planning travel.`
- `I need help planning a vacation.`

## Whether a defect was found

Yes.

The standalone vacation/travel opener was overmatching on travel nouns inside document-shaped prompts, which incorrectly routed writing requests into the vacation or hotel/flight logistics forks.

Before repair, all of these wrongly triggered the travel opener family:
- `I need help with this travel essay.`
- `I need help with this travel chapter.`
- `I need help with this travel memo.`
- `I need help with this trip report.`
- `I need help with this vacation note.`
- `I need help with this hotel review.`

## Exact code/tests changed

Code change:
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:371)
  - Added a narrow `vacation_document_terms` guard:
    - `essay`
    - `chapter`
    - `memo`
    - `report`
    - `note`
    - `review`
  - Prevented the standalone vacation opener and the hotel/flight logistics opener from firing when those document-shaped terms are present.

Test changes:
- [tests/test_companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/tests/test_companion_spine.py:2090)
  - Added focused regression coverage for:
    - `travel essay`
    - `travel chapter`
    - `travel memo`
    - `trip report`
    - `vacation note`
    - `hotel review`
  - Reused true vacation/travel controls to verify no regression:
    - `I want to plan a trip.`
    - `I need a vacation but I do not know what I need.`

## Exact verification commands run

```bash
python3 -m py_compile jarvis/companion_spine.py tests/test_companion_spine.py
python3 -m pytest -q tests/test_companion_spine.py -k "travel_essay_prompt_does_not_get_vacation_fork or travel_chapter_prompt_does_not_get_vacation_fork or travel_memo_prompt_does_not_get_vacation_fork or trip_report_prompt_does_not_get_vacation_fork or vacation_note_prompt_does_not_get_vacation_fork or hotel_review_prompt_does_not_get_logistics_fork or trip_planning_prompt_gets_concrete_vacation_fork or standalone_vacation_prompt_gets_concrete_fork or uncertain_vacation_prompt_gets_concrete_vacation_fork"
python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
prompts = [
    "I need help with this travel essay.",
    "I need help with this travel chapter.",
    "I need help with this travel memo.",
    "I need help with this trip report.",
    "I need help with this vacation note.",
    "I need help with this hotel review.",
    "I need to plan a trip.",
    "I need help planning travel.",
    "I need help planning a vacation.",
]
for prompt in prompts:
    reply = generate_companion_fallback(prompt, packet)
    print(f"PROMPT: {prompt}\nREPLY: {reply}\n")
PY
```

## Verification results

- `py_compile`: passed
- focused pytest: `9 passed, 228 deselected`
- in-process smoke:
  - all document-shaped travel prompts stayed out of the vacation and hotel/flight logistics forks
  - the true vacation/travel controls still routed to:
    - `Good. Is the real question where to go, what kind of trip this needs to be, or what is making it hard to land?`

## Recommendation

Approve.

This is a narrow opener overmatch repair inside the standalone vacation seam only. It removes document-writing false positives without widening into a broader travel-writing classifier.
