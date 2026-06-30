# Post-Epic 9 Slice 93: Companion Tomorrow-Planning Opener Usefulness Hardening

Ready for Architect Office review: yes

## Exact prompts tested

Repaired tomorrow-planning prompts:
- `I need help planning tomorrow.`
- `I need help scheduling tomorrow.`
- `I need help organizing tomorrow.`
- `I need help planning around two meetings.`

Preserved nearby controls rechecked:
- `I need help with my inbox.`
- `I need help with this meeting follow-up.`
- `I need help drafting an email to my boss.`
- `I need help with a hard conversation.`
- `I need help deciding between two apartments.`
- `I need to get tomorrow under control.`

## Exact code/tests changed

Code changes:
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:427)
  - Added a standalone first-turn tomorrow-planning opener fork ahead of the generic practical sorter.
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:660)
  - Added `_is_tomorrow_planning_request(...)` as the narrow seam-local matcher for tomorrow-planning / scheduling-tomorrow / organizing-tomorrow / planning-around-meetings phrasing.

New tomorrow-planning opener reply:
- `Good. For tomorrow, what actually has to happen, what is fixed, and what can slip?`

Test changes:
- [tests/test_companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/tests/test_companion_spine.py:267)
  - Added focused coverage for the four tomorrow-planning prompts above.

## Exact commands run

```bash
python3 -m py_compile jarvis/companion_spine.py tests/test_companion_spine.py
python3 -m pytest -q tests/test_companion_spine.py -k "help_planning_tomorrow_prompt_gets_concrete_tomorrow_fork or help_scheduling_tomorrow_prompt_gets_concrete_tomorrow_fork or help_organizing_tomorrow_prompt_gets_concrete_tomorrow_fork or planning_around_two_meetings_prompt_gets_concrete_tomorrow_fork or help_with_my_inbox_prompt_gets_concrete_inbox_fork or meeting_agenda_prompt_gets_concrete_meeting_fork or drafting_email_to_boss_prompt_gets_drafting_fork or hard_conversation_prompt_gets_concrete_conversation_fork or decision_shaped_job_prompt_gets_decision_fork"
python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
prompts = [
    "I need help planning tomorrow.",
    "I need help scheduling tomorrow.",
    "I need help organizing tomorrow.",
    "I need help planning around two meetings.",
    "I need help with my inbox.",
    "I need help with this meeting follow-up.",
    "I need help drafting an email to my boss.",
    "I need help with a hard conversation.",
    "I need help deciding between two apartments.",
    "I need to get tomorrow under control.",
]
for prompt in prompts:
    reply = generate_companion_fallback(prompt, packet)
    print(f"PROMPT: {prompt}\nREPLY: {reply}\n")
PY
```

## Exact results

- `py_compile`: passed
- focused pytest: `9 passed, 273 deselected`
- in-process smoke:
  - all four tomorrow-planning prompts now route to:
    - `Good. For tomorrow, what actually has to happen, what is fixed, and what can slip?`
  - preserved nearby controls still behave correctly:
    - `I need help with my inbox.` stays on the inbox fork
    - `I need help with this meeting follow-up.` stays on the meeting fork
    - `I need help drafting an email to my boss.` stays on the drafting fork
    - `I need help with a hard conversation.` stays on the hard-conversation fork
    - `I need help deciding between two apartments.` stays on the concrete decision fork
    - `I need to get tomorrow under control.` keeps the sharper capacity-pushback fork

## Scope safety

This repair stayed inside the smallest existing first-turn companion opener seam only:
- no broad chief-of-staff redesign
- no fake calendar or schedule-awareness claims
- no broad planning-system rewrite
- no changes to unrelated inbox, meeting, drafting, conversation, decision, vacation, retirement, or capability seams

## Architect recommendation

Approve.

This slice fixes the concrete tomorrow-planning family opener weakness with one narrow tomorrow-planning fork and focused regression coverage, while preserving the adjacent hardened seams unchanged.
