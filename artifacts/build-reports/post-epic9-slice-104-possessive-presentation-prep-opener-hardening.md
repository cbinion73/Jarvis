# Post-Epic 9 Slice 104: Possessive Presentation-Prep Opener Hardening

Ready for Architect Office review: yes

## Exact prompts inspected

Target family hardened:
- `I need help with my presentation.`
- `I need help with my proposal.`
- `I need help with my slide deck.`
- `I need help with my pitch.`
- `I need help with my proposal deck.`
- `I need help getting ready for my presentation.`
- `I need help getting ready for my proposal.`

Preserved nearby controls checked:
- `I need help with this presentation.`
- `I need help with this proposal.`
- `I need help with this slide deck.`
- `I need help with this pitch.`
- `I need help with my inbox.`
- `I need help with this meeting.`
- `I need help with this agenda.`
- `I need help planning tomorrow.`
- `I need help drafting an email to my boss.`
- `I need help deciding between two apartments.`
- `I need help with a hard conversation.`
- `I need help scheduling around constraints.`

## Exact code/tests changed

Code changes:
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:666)
  - extended `_is_presentation_or_proposal_prep_request(...)` with the possessive presentation/prep family:
    - `help with my presentation`
    - `getting ready for my presentation`
    - `help with my proposal`
    - `getting ready for my proposal`
    - `help with my slide deck`
    - `help with my pitch`
    - `help with my proposal deck`
  - kept the repair inside the existing presentation-shaping opener seam and preserved the current reply shape

Test changes:
- [tests/test_companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/tests/test_companion_spine.py:274)
  - added focused opener coverage for all seven possessive presentation/prep prompts
  - preserved nearby control validation through the focused pytest battery

## Exact commands run

```bash
python3 -m py_compile jarvis/companion_spine.py tests/test_companion_spine.py
python3 -m pytest -q tests/test_companion_spine.py -k "help_with_my_presentation_prompt_gets_concrete_prep_fork or getting_ready_for_my_presentation_prompt_gets_concrete_prep_fork or help_with_my_proposal_prompt_gets_concrete_prep_fork or getting_ready_for_my_proposal_prompt_gets_concrete_prep_fork or help_with_my_slide_deck_prompt_gets_concrete_prep_fork or help_with_my_pitch_prompt_gets_concrete_prep_fork or help_with_my_proposal_deck_prompt_gets_concrete_prep_fork or help_with_my_inbox_prompt_gets_concrete_inbox_fork or help_with_this_meeting_prompt_gets_concrete_meeting_fork or help_with_this_agenda_prompt_gets_concrete_agenda_fork or help_planning_tomorrow_prompt_gets_concrete_tomorrow_fork or drafting_email_to_boss_prompt_gets_drafting_fork or deciding_between_two_jobs_prompt_gets_decision_fork or hard_conversation_prompt_gets_concrete_conversation_fork or scheduling_around_constraints_prompt_gets_constraints_fork"
python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
prompts = [
    "I need help with my presentation.",
    "I need help with my proposal.",
    "I need help with my slide deck.",
    "I need help with my pitch.",
    "I need help with my proposal deck.",
    "I need help getting ready for my presentation.",
    "I need help getting ready for my proposal.",
    "I need help with my inbox.",
    "I need help with this meeting.",
    "I need help with this agenda.",
    "I need help planning tomorrow.",
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

Compile:
- `python3 -m py_compile jarvis/companion_spine.py tests/test_companion_spine.py`
- result: passed

Focused pytest:
- `15 passed, 294 deselected in 0.27s`

In-process smoke after repair:
- `I need help with my presentation.` -> `Good. Is the real work the point you need to land, the structure, or getting ready to deliver it cleanly?`
- `I need help with my proposal.` -> same presentation-shaping fork
- `I need help with my slide deck.` -> same presentation-shaping fork
- `I need help with my pitch.` -> same presentation-shaping fork
- `I need help with my proposal deck.` -> same presentation-shaping fork
- `I need help getting ready for my presentation.` -> same presentation-shaping fork
- `I need help getting ready for my proposal.` -> same presentation-shaping fork

Preserved nearby controls remained correct:
- `I need help with this presentation.` stayed on the presentation-shaping fork
- `I need help with this proposal.` stayed on the presentation-shaping fork
- `I need help with this slide deck.` stayed on the presentation-shaping fork
- `I need help with this pitch.` stayed on the presentation-shaping fork
- `I need help with my inbox.` stayed on the inbox fork
- `I need help with this meeting.` stayed on the meeting fork
- `I need help with this agenda.` stayed on the agenda fork
- `I need help planning tomorrow.` stayed on the tomorrow-planning fork
- `I need help drafting an email to my boss.` stayed on the drafting fork
- `I need help deciding between two apartments.` stayed on the decision fork
- `I need help with a hard conversation.` stayed on the hard-conversation fork
- `I need help scheduling around constraints.` stayed on the constraints-scheduling fork

## Follow-up recommendation

No stronger remaining first-turn defect became visible inside this narrow validation set.

If Architect Office wants the next bounded lane, the cleanest move is another fresh reassessment rather than guessing between the remaining `briefing`, `follow-up`, or `agenda for tomorrow` families.
