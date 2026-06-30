# Post-Epic 9 Slice 118: Companion Post-Meeting Debrief / Notes Opener Hardening

Ready for Architect Office review: yes

## Exact prompts inspected

Target post-meeting debrief / notes family:
- `I need help with this debrief.`
- `I need help after this meeting.`
- `I need help with my notes for this meeting.`
- `I need help with meeting notes.`

Preserved nearby controls:
- `I need help with my follow-up.`
- `I need help with this meeting.`
- `I need help with this agenda.`
- `I need help with my email.`
- `I need help drafting an email to my boss.`
- `I need help planning tomorrow.`
- `I need help deciding between two apartments.`
- `I need help with a hard conversation.`
- `I need help scheduling around constraints.`

## Exact code/tests changed

Code:
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:678)
  - extended `_is_follow_up_request(...)` with the bounded post-meeting aliases:
    - `help with this debrief`
    - `help after this meeting`
    - `help with my notes for this meeting`
    - `help with meeting notes`
  - kept the repair inside the existing follow-up opener seam so post-meeting phrasing lands on the smallest truthful nearby fork instead of the generic practical sorter

Tests:
- [tests/test_companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/tests/test_companion_spine.py:325)
  - added focused opener coverage for all four post-meeting debrief / notes prompts
  - preserved nearby control validation through the focused pytest battery

## Exact commands run

Pre-repair smoke:

```bash
python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet={"available_capabilities":["ongoing conversation in this shell","conversation turn persistence"]}
for prompt in [
    "I need help with this debrief.",
    "I need help after this meeting.",
    "I need help with my notes for this meeting.",
    "I need help with meeting notes.",
    "I need help with my follow-up.",
    "I need help with this meeting.",
]:
    print('PROMPT:',prompt)
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
python3 -m pytest -q tests/test_companion_spine.py -k "help_with_this_debrief_prompt_gets_concrete_follow_up_fork or help_after_this_meeting_prompt_gets_concrete_follow_up_fork or help_with_my_notes_for_this_meeting_prompt_gets_concrete_follow_up_fork or help_with_meeting_notes_prompt_gets_concrete_follow_up_fork or help_with_my_follow_up_prompt_gets_concrete_follow_up_fork or help_with_this_meeting_prompt_gets_concrete_meeting_fork or help_with_this_agenda_prompt_gets_concrete_agenda_fork or help_with_my_email_prompt_gets_concrete_inbox_fork or drafting_email_to_boss_prompt_gets_drafting_fork or help_planning_tomorrow_prompt_gets_concrete_tomorrow_fork or deciding_between_two_jobs_prompt_gets_decision_fork or hard_conversation_prompt_gets_concrete_conversation_fork or scheduling_around_constraints_prompt_gets_constraints_fork"
```

Post-repair smoke:

```bash
python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet={"available_capabilities":["ongoing conversation in this shell","conversation turn persistence"]}
prompts=[
    "I need help with this debrief.",
    "I need help after this meeting.",
    "I need help with my notes for this meeting.",
    "I need help with meeting notes.",
    "I need help with my follow-up.",
    "I need help with this meeting.",
    "I need help with this agenda.",
    "I need help with my email.",
    "I need help drafting an email to my boss.",
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
- all four target prompts fell to the generic practical sorter instead of a nearby concrete fork

Compile:
- `python3 -m py_compile jarvis/companion_spine.py tests/test_companion_spine.py`
- result: passed

Focused pytest:
- `13 passed, 327 deselected in 0.25s`

Post-repair smoke:
- `I need help with this debrief.` -> `Good. Is the real work the message you owe, the decision you need before you send it, or the next move you need to lock in?`
- `I need help after this meeting.` -> same follow-up fork
- `I need help with my notes for this meeting.` -> same follow-up fork
- `I need help with meeting notes.` -> same follow-up fork

Preserved nearby controls stayed on their existing concrete seams:
- `my follow-up` -> follow-up fork
- `this meeting` -> meeting fork
- `this agenda` -> agenda fork
- `my email` -> inbox fork
- `drafting an email to my boss` -> drafting fork
- `planning tomorrow` -> tomorrow-planning fork
- `deciding between two apartments` -> decision fork
- `a hard conversation` -> hard-conversation fork
- `scheduling around constraints` -> constraints-scheduling fork

## Follow-up recommendation

No stronger remaining defect became visible inside this narrow validation set. The cleanest next move is another fresh live-use reassessment rather than guessing the next family from adjacency alone.
