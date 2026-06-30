# Post-Epic 9 Slice 99: Scheduling-Around-Constraints Opener Hardening

Ready for Architect Office review: yes

## Exact prompts inspected

Target family hardened:
- `I need help scheduling around two meetings.`
- `I need help scheduling around constraints.`
- `I need help scheduling around my constraints.`
- `I need help planning around constraints.`

Preserved nearby controls checked:
- `I need help with this agenda.`
- `I need help planning tomorrow.`
- `I need help with my inbox.`
- `I need help with this meeting.`
- `I need help drafting an email to my boss.`
- `I need help deciding between two apartments.`
- `I need help with a hard conversation.`

## Exact code/tests changed

Code changes:
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:431)
  - added a narrow `_is_constraints_scheduling_request(...)` opener guard
  - routed the target family to a concrete constraints-aware planning fork before the generic practical sorter
  - left the existing tomorrow-planning fork unchanged for `planning tomorrow` and `planning around two meetings`

Test changes:
- [tests/test_companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/tests/test_companion_spine.py:337)
  - added focused opener coverage for:
    - `scheduling around two meetings`
    - `scheduling around constraints`
    - `scheduling around my constraints`
    - `planning around constraints`
  - kept agenda and tomorrow-planning coverage in the focused validation battery

## Exact commands run

```bash
python3 -m py_compile jarvis/companion_spine.py tests/test_companion_spine.py
python3 -m pytest -q tests/test_companion_spine.py -k "scheduling_around_two_meetings_prompt_gets_constraints_fork or scheduling_around_constraints_prompt_gets_constraints_fork or scheduling_around_my_constraints_prompt_gets_constraints_fork or planning_around_constraints_prompt_gets_constraints_fork or help_with_this_agenda_prompt_gets_concrete_agenda_fork or help_planning_tomorrow_prompt_gets_concrete_tomorrow_fork"
python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
prompts = [
    "I need help scheduling around two meetings.",
    "I need help scheduling around constraints.",
    "I need help scheduling around my constraints.",
    "I need help planning around constraints.",
    "I need help with this agenda.",
    "I need help planning tomorrow.",
    "I need help with my inbox.",
    "I need help with this meeting.",
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
- `6 passed, 287 deselected in 0.19s`

In-process smoke after repair:
- `I need help scheduling around two meetings.`
  - `Good. What is fixed, what actually has to happen, and what can move around those constraints?`
- `I need help scheduling around constraints.`
  - `Good. What is fixed, what actually has to happen, and what can move around those constraints?`
- `I need help scheduling around my constraints.`
  - `Good. What is fixed, what actually has to happen, and what can move around those constraints?`
- `I need help planning around constraints.`
  - `Good. What is fixed, what actually has to happen, and what can move around those constraints?`

Preserved controls remained correct:
- `I need help with this agenda.` stayed on the agenda fork
- `I need help planning tomorrow.` stayed on the tomorrow-planning fork
- `I need help with my inbox.` stayed on the inbox fork
- `I need help with this meeting.` stayed on the meeting fork
- `I need help drafting an email to my boss.` stayed on the drafting fork
- `I need help deciding between two apartments.` stayed on the decision fork
- `I need help with a hard conversation.` stayed on the hard-conversation fork

## Follow-up recommendation

No stronger new defect surfaced inside this repaired seam during validation.

If Architect Office wants the next bounded first-turn usefulness pass, the previously observed `slide deck` / `pitch` family still looks like a narrower adjacent miss, but it remains lower-value than the constraints-scheduling defect that this slice closed.
