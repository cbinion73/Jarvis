# Post-Epic 9 Slice 110: Briefing-Prep Opener Hardening

Ready for Architect Office review: yes

## Exact prompts inspected

Target briefing-prep family:
- `I need help with this briefing.`
- `I need help with my briefing.`
- `I need help writing a briefing.`
- `I need help preparing a briefing.`
- `I need help with a briefing.`
- `I need help getting ready for this briefing.`
- `I need help getting ready for my briefing.`

Preserved nearby controls:
- `I need help with this presentation.`
- `I need help with my inbox.`
- `I need help with this meeting.`
- `I need help with this agenda.`
- `I need help planning tomorrow.`
- `I need help with my follow-up.`
- `I need help drafting an email to my boss.`
- `I need help deciding between two apartments.`
- `I need help with a hard conversation.`
- `I need help scheduling around constraints.`

## Exact code/tests changed

Code:
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:684)
  - extended `_is_presentation_or_proposal_prep_request(...)` with the bounded briefing-prep alias family:
    - `help with this briefing`
    - `help with my briefing`
    - `help with a briefing`
    - `writing a briefing`
    - `preparing a briefing`
    - `getting ready for this briefing`
    - `getting ready for my briefing`
  - kept the repair inside the existing presentation-prep opener seam so briefing prompts land on the same truthful prep fork instead of the generic practical sorter

Tests:
- [tests/test_companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/tests/test_companion_spine.py:389)
  - added focused opener coverage for all seven briefing-prep prompts
  - preserved nearby control validation through the focused pytest battery

## Exact commands run

Pre-repair smoke:

```bash
python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
prompts = [
    "I need help with this briefing.",
    "I need help with my briefing.",
    "I need help writing a briefing.",
    "I need help preparing a briefing.",
    "I need help with a briefing.",
    "I need help getting ready for this briefing.",
    "I need help getting ready for my briefing.",
]
for prompt in prompts:
    print(f"PROMPT: {prompt}")
    print(generate_companion_fallback(prompt, packet))
    print()
PY
```

Compile:

```bash
python3 -m py_compile jarvis/companion_spine.py tests/test_companion_spine.py
```

Focused pytest:

```bash
python3 -m pytest -q tests/test_companion_spine.py -k "help_with_this_briefing_prompt_gets_concrete_prep_fork or help_with_my_briefing_prompt_gets_concrete_prep_fork or help_with_a_briefing_prompt_gets_concrete_prep_fork or writing_a_briefing_prompt_gets_concrete_prep_fork or preparing_a_briefing_prompt_gets_concrete_prep_fork or getting_ready_for_this_briefing_prompt_gets_concrete_prep_fork or getting_ready_for_my_briefing_prompt_gets_concrete_prep_fork or help_with_this_presentation_prompt_gets_concrete_prep_fork or help_with_my_inbox_prompt_gets_concrete_inbox_fork or help_with_this_meeting_prompt_gets_concrete_meeting_fork or help_with_this_agenda_prompt_gets_concrete_agenda_fork or help_planning_tomorrow_prompt_gets_concrete_tomorrow_fork or help_with_my_follow_up_prompt_gets_concrete_follow_up_fork or drafting_email_to_boss_prompt_gets_drafting_fork or deciding_between_two_jobs_prompt_gets_decision_fork or hard_conversation_prompt_gets_concrete_conversation_fork or scheduling_around_constraints_prompt_gets_constraints_fork"
```

Post-repair smoke:

```bash
python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
prompts = [
    "I need help with this briefing.",
    "I need help with my briefing.",
    "I need help writing a briefing.",
    "I need help preparing a briefing.",
    "I need help with a briefing.",
    "I need help getting ready for this briefing.",
    "I need help getting ready for my briefing.",
    "I need help with this presentation.",
    "I need help with my inbox.",
    "I need help with this meeting.",
    "I need help with this agenda.",
    "I need help planning tomorrow.",
    "I need help with my follow-up.",
    "I need help drafting an email to my boss.",
    "I need help deciding between two apartments.",
    "I need help with a hard conversation.",
    "I need help scheduling around constraints.",
]
for prompt in prompts:
    print(f"PROMPT: {prompt}")
    print(generate_companion_fallback(prompt, packet))
    print()
PY
```

## Exact results

Pre-repair repo truth:
- all seven briefing-prep prompts fell to the generic practical sorter instead of a concrete prep fork

Compile:
- `python3 -m py_compile jarvis/companion_spine.py tests/test_companion_spine.py`
- result: passed

Focused pytest:
- `17 passed, 308 deselected in 0.22s`

Post-repair smoke:
- `I need help with this briefing.` -> `Good. Is the real work the point you need to land, the structure, or getting ready to deliver it cleanly?`
- `I need help with my briefing.` -> same fork
- `I need help writing a briefing.` -> same fork
- `I need help preparing a briefing.` -> same fork
- `I need help with a briefing.` -> same fork
- `I need help getting ready for this briefing.` -> same fork
- `I need help getting ready for my briefing.` -> same fork

Preserved nearby controls stayed on their existing seams:
- `this presentation` -> presentation-prep fork
- `my inbox` -> inbox fork
- `this meeting` -> meeting fork
- `this agenda` -> agenda fork
- `planning tomorrow` -> tomorrow-planning fork
- `my follow-up` -> follow-up fork
- `drafting an email to my boss` -> drafting fork
- `deciding between two apartments` -> decision fork
- `a hard conversation` -> hard-conversation fork
- `scheduling around constraints` -> constraints-scheduling fork

## Follow-up recommendation

No stronger remaining defect became visible inside this narrow validation set. The cleanest next move is another fresh live-use reassessment rather than guessing the next family from adjacency alone.
