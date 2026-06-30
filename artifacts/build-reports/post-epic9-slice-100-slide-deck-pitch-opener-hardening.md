# Post-Epic 9 Slice 100: Slide-Deck-And-Pitch Opener Hardening

Ready for Architect Office review: yes

## Exact prompts inspected

Target family hardened:
- `I need help with this slide deck.`
- `I need help with this pitch.`

Preserved nearby controls checked:
- `I need help with this presentation.`
- `I need help with this proposal.`
- `I need help with this agenda.`
- `I need help with this meeting.`
- `I need help planning tomorrow.`
- `I need help drafting an email to my boss.`
- `I need help deciding between two apartments.`
- `I need help with a hard conversation.`

## Exact code/tests changed

Code changes:
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:666)
  - extended the existing `_is_presentation_or_proposal_prep_request(...)` opener matcher with:
    - `help with this slide deck`
    - `help with this pitch`
  - kept the repair inside the existing presentation/proposal prep seam instead of adding a new opener family

Test changes:
- [tests/test_companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/tests/test_companion_spine.py:292)
  - added focused opener coverage for:
    - `help with this slide deck`
    - `help with this pitch`
  - validation also re-checked preserved nearby controls from presentation/proposal, agenda, meeting, tomorrow-planning, drafting, decision, and hard-conversation seams

## Exact commands run

```bash
python3 -m py_compile jarvis/companion_spine.py tests/test_companion_spine.py
python3 -m pytest -q tests/test_companion_spine.py -k "help_with_this_slide_deck_prompt_gets_concrete_prep_fork or help_with_this_pitch_prompt_gets_concrete_prep_fork or help_with_this_presentation_prompt_gets_concrete_prep_fork or help_with_this_proposal_prompt_gets_concrete_prep_fork or help_with_this_agenda_prompt_gets_concrete_agenda_fork or test_help_planning_tomorrow_prompt_gets_concrete_tomorrow_fork or test_help_with_this_meeting_prompt_gets_concrete_meeting_fork or drafting_email_to_boss_prompt_gets_drafting_fork or deciding_between_two_jobs_prompt_gets_decision_fork or test_hard_conversation_prompt_gets_concrete_conversation_fork"
python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
prompts = [
    "I need help with this slide deck.",
    "I need help with this pitch.",
    "I need help with this presentation.",
    "I need help with this proposal.",
    "I need help with this agenda.",
    "I need help with this meeting.",
    "I need help planning tomorrow.",
    "I need help drafting an email to my boss.",
    "I need help deciding between two apartments.",
    "I need help with a hard conversation.",
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
- `10 passed, 285 deselected in 0.21s`

In-process smoke after repair:
- `I need help with this slide deck.`
  - `Good. Is the real work the point you need to land, the structure, or getting ready to deliver it cleanly?`
- `I need help with this pitch.`
  - `Good. Is the real work the point you need to land, the structure, or getting ready to deliver it cleanly?`

Preserved nearby controls remained correct:
- `I need help with this presentation.` stayed on the presentation/proposal prep fork
- `I need help with this proposal.` stayed on the presentation/proposal prep fork
- `I need help with this agenda.` stayed on the agenda fork
- `I need help with this meeting.` stayed on the meeting fork
- `I need help planning tomorrow.` stayed on the tomorrow-planning fork
- `I need help drafting an email to my boss.` stayed on the drafting fork
- `I need help deciding between two apartments.` stayed on the decision fork
- `I need help with a hard conversation.` stayed on the hard-conversation fork

## Follow-up recommendation

No stronger new defect surfaced inside this repaired opener family during validation.

If Architect Office wants the next bounded first-turn usefulness pass, the next best candidate should come from a fresh reassessment rather than assuming another adjacent presentation alias family without repo-truth smoke.
