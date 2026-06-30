# Post-Epic 9 Slice 106: Follow-Up Opener Hardening

Ready for Architect Office review: yes

## Exact prompts inspected

Target family hardened:
- `I need help with my follow-up.`
- `I need help with this follow-up.`
- `I need help following up after this meeting.`
- `I need help with the follow-up.`
- `I need help with a follow-up.`
- `I need help with my meeting follow-up.`

Preserved nearby controls checked:
- `I need help with my inbox.`
- `I need help with this meeting.`
- `I need help with this agenda.`
- `I need help planning tomorrow.`
- `I need help with this presentation.`
- `I need help drafting an email to my boss.`
- `I need help writing a follow-up email after this meeting.`
- `I need help deciding between two apartments.`
- `I need help with a hard conversation.`
- `I need help scheduling around constraints.`

## Exact code/tests changed

Code changes:
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:426)
  - added a dedicated first-turn follow-up fork before the generic practical sorter:
    - `Good. Is the real work the message you owe, the decision you need before you send it, or the next move you need to lock in?`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:671)
  - added `_is_follow_up_request(...)` with the bounded prompt family:
    - `help with my follow-up`
    - `help with this follow-up`
    - `help following up after this meeting`
    - `help with the follow-up`
    - `help with a follow-up`
    - `help with my meeting follow-up`

Test changes:
- [tests/test_companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/tests/test_companion_spine.py:267)
  - added focused opener coverage for all six follow-up prompts
  - preserved nearby control validation through the focused pytest battery

## Exact commands run

```bash
python3 -m py_compile jarvis/companion_spine.py tests/test_companion_spine.py
python3 -m pytest -q tests/test_companion_spine.py -k "help_with_my_follow_up_prompt_gets_concrete_follow_up_fork or help_with_this_follow_up_prompt_gets_concrete_follow_up_fork or help_following_up_after_this_meeting_prompt_gets_concrete_follow_up_fork or help_with_the_follow_up_prompt_gets_concrete_follow_up_fork or help_with_a_follow_up_prompt_gets_concrete_follow_up_fork or help_with_my_meeting_follow_up_prompt_gets_concrete_follow_up_fork or help_with_my_inbox_prompt_gets_concrete_inbox_fork or help_with_this_meeting_prompt_gets_concrete_meeting_fork or help_with_this_agenda_prompt_gets_concrete_agenda_fork or help_planning_tomorrow_prompt_gets_concrete_tomorrow_fork or help_with_this_presentation_prompt_gets_concrete_prep_fork or drafting_email_to_boss_prompt_gets_drafting_fork or writing_follow_up_email_after_meeting_prompt_gets_drafting_fork or deciding_between_two_jobs_prompt_gets_decision_fork or hard_conversation_prompt_gets_concrete_conversation_fork or scheduling_around_constraints_prompt_gets_constraints_fork"
python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
prompts = [
    "I need help with my follow-up.",
    "I need help with this follow-up.",
    "I need help following up after this meeting.",
    "I need help with the follow-up.",
    "I need help with a follow-up.",
    "I need help with my meeting follow-up.",
    "I need help with my inbox.",
    "I need help with this meeting.",
    "I need help with this agenda.",
    "I need help planning tomorrow.",
    "I need help with this presentation.",
    "I need help drafting an email to my boss.",
    "I need help writing a follow-up email after this meeting.",
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
- `16 passed, 299 deselected in 0.24s`

In-process smoke after repair:
- `I need help with my follow-up.` -> `Good. Is the real work the message you owe, the decision you need before you send it, or the next move you need to lock in?`
- `I need help with this follow-up.` -> same follow-up fork
- `I need help following up after this meeting.` -> same follow-up fork
- `I need help with the follow-up.` -> same follow-up fork
- `I need help with a follow-up.` -> same follow-up fork
- `I need help with my meeting follow-up.` -> same follow-up fork

Preserved nearby controls remained correct:
- `I need help with my inbox.` stayed on the inbox fork
- `I need help with this meeting.` stayed on the meeting fork
- `I need help with this agenda.` stayed on the agenda fork
- `I need help planning tomorrow.` stayed on the tomorrow-planning fork
- `I need help with this presentation.` stayed on the presentation fork
- `I need help drafting an email to my boss.` stayed on the drafting fork
- `I need help writing a follow-up email after this meeting.` stayed on the drafting fork
- `I need help deciding between two apartments.` stayed on the decision fork
- `I need help with a hard conversation.` stayed on the hard-conversation fork
- `I need help scheduling around constraints.` stayed on the constraints-scheduling fork

## Follow-up recommendation

No stronger remaining defect became visible inside this narrow validation set.

If Architect Office wants the next bounded lane, the cleanest move is another fresh reassessment rather than guessing between the remaining `briefing` and `agenda for tomorrow` families.
