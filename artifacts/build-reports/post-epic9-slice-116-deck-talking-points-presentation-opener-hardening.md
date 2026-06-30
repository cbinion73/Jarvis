# Post-Epic 9 Slice 116: Companion Deck / Talking-Points Presentation Opener Hardening

Ready for Architect Office review: yes

## Exact prompts inspected

Target deck / talking-points family:
- `I need help with this deck.`
- `I need help getting ready for this deck.`
- `I need help with my talking points.`

Preserved nearby controls:
- `I need help with this slide deck.`
- `I need help with this presentation.`
- `I need help with this meeting.`
- `I need help with this agenda.`
- `I need help with my email.`
- `I need help drafting an email to my boss.`
- `I need help with my follow-up.`
- `I need help planning tomorrow.`
- `I need help deciding between two apartments.`
- `I need help with a hard conversation.`
- `I need help scheduling around constraints.`

## Exact code/tests changed

Code:
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:691)
  - extended `_is_presentation_or_proposal_prep_request(...)` with the bounded presentation shorthand family:
    - `help with this deck`
    - `getting ready for this deck`
    - `help with my talking points`
  - kept the repair inside the existing presentation-prep opener seam so these prompts land on the same truthful prep fork as `this slide deck` and `this presentation`

Tests:
- [tests/test_companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/tests/test_companion_spine.py:389)
  - added focused opener coverage for all three deck / talking-points prompts
  - preserved nearby control validation through the focused pytest battery

## Exact commands run

Pre-repair smoke:

```bash
python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
prompts = [
    "I need help with this deck.",
    "I need help getting ready for this deck.",
    "I need help with my talking points.",
    "I need help with this slide deck.",
    "I need help with this presentation.",
    "I need help with this meeting.",
    "I need help with this agenda.",
    "I need help with my email.",
    "I need help drafting an email to my boss.",
    "I need help with my follow-up.",
    "I need help planning tomorrow.",
    "I need help deciding between two apartments.",
    "I need help with a hard conversation.",
    "I need help scheduling around constraints.",
]
for prompt in prompts:
    print('PROMPT:', prompt)
    print(generate_companion_fallback(prompt, packet))
    print('---')
PY
```

Compile:

```bash
python3 -m py_compile jarvis/companion_spine.py tests/test_companion_spine.py
```

Focused pytest:

```bash
python3 -m pytest -q tests/test_companion_spine.py -k "help_with_this_deck_prompt_gets_concrete_prep_fork or getting_ready_for_this_deck_prompt_gets_concrete_prep_fork or help_with_my_talking_points_prompt_gets_concrete_prep_fork or help_with_this_slide_deck_prompt_gets_concrete_prep_fork or help_with_this_presentation_prompt_gets_concrete_prep_fork or help_with_this_meeting_prompt_gets_concrete_meeting_fork or help_with_this_agenda_prompt_gets_concrete_agenda_fork or help_with_my_email_prompt_gets_concrete_inbox_fork or drafting_email_to_boss_prompt_gets_drafting_fork or help_with_my_follow_up_prompt_gets_concrete_follow_up_fork or help_planning_tomorrow_prompt_gets_concrete_tomorrow_fork or deciding_between_two_jobs_prompt_gets_decision_fork or hard_conversation_prompt_gets_concrete_conversation_fork or scheduling_around_constraints_prompt_gets_constraints_fork"
```

Post-repair smoke:

```bash
python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
prompts = [
    "I need help with this deck.",
    "I need help getting ready for this deck.",
    "I need help with my talking points.",
    "I need help with this slide deck.",
    "I need help with this presentation.",
    "I need help with this meeting.",
    "I need help with this agenda.",
    "I need help with my email.",
    "I need help drafting an email to my boss.",
    "I need help with my follow-up.",
    "I need help planning tomorrow.",
    "I need help deciding between two apartments.",
    "I need help with a hard conversation.",
    "I need help scheduling around constraints.",
]
for prompt in prompts:
    print(f'PROMPT: {prompt}')
    print(generate_companion_fallback(prompt, packet))
    print()
PY
```

## Exact results

Pre-repair repo truth:
- `I need help with this deck.` -> generic practical sorter
- `I need help getting ready for this deck.` -> generic practical sorter
- `I need help with my talking points.` -> generic practical sorter

Compile:
- `python3 -m py_compile jarvis/companion_spine.py tests/test_companion_spine.py`
- result: passed

Focused pytest:
- `14 passed, 322 deselected in 0.25s`

Post-repair smoke:
- `I need help with this deck.` -> `Good. Is the real work the point you need to land, the structure, or getting ready to deliver it cleanly?`
- `I need help getting ready for this deck.` -> same presentation-prep fork
- `I need help with my talking points.` -> same presentation-prep fork

Preserved nearby controls stayed on their existing concrete seams:
- `this slide deck` -> presentation-prep fork
- `this presentation` -> presentation-prep fork
- `this meeting` -> meeting fork
- `this agenda` -> agenda fork
- `my email` -> inbox fork
- `drafting an email to my boss` -> drafting fork
- `my follow-up` -> follow-up fork
- `planning tomorrow` -> tomorrow-planning fork
- `deciding between two apartments` -> decision fork
- `a hard conversation` -> hard-conversation fork
- `scheduling around constraints` -> constraints-scheduling fork

## Follow-up recommendation

No stronger remaining defect became visible inside this narrow validation set. The cleanest next move is another fresh live-use reassessment rather than guessing the next family from adjacency alone.
