# Post-Epic 9 Slice 119: Fresh Live-Use Weakness Reassessment

Ready for Architect Office review: yes

## Exact prompts or routes inspected

Fresh bounded prompt sweep:
- `I need help mapping out tomorrow.`
- `I need help planning around two appointments.`
- `I need help planning around my appointments.`
- `I need help scheduling around appointments.`
- `I need help with my schedule tomorrow.`
- `I need help with tomorrow afternoon.`
- `I need help with this outline.`
- `I need help with this summary.`
- `I need help with this recap.`
- `I need help with my schedule this week.`
- `I need help planning tomorrow.`
- `I need help scheduling around constraints.`
- `I need help with this meeting.`
- `I need help with my follow-up.`
- `I need help with this presentation.`
- `I need help with my email.`
- `I need help with my one-on-one.`

Direct comparison battery:
- `I need help planning around two meetings.`
- `I need help planning around two appointments.`
- `I need help planning around my appointments.`
- `I need help scheduling around appointments.`
- `I need help scheduling around constraints.`
- `I need help planning around constraints.`
- `I need help planning tomorrow.`
- `I need help mapping out tomorrow.`
- `I need help with tomorrow afternoon.`
- `I need help with my schedule tomorrow.`
- `I need help with tomorrow's schedule.`
- `I need help with my schedule for tomorrow.`
- `I need help scheduling tomorrow.`
- `I need help organizing tomorrow.`

## Exact code seams inspected

- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:321)
  - `generate_companion_fallback(...)` opener ordering
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:89)
  - `OVERLOADED_PLANNING_REQUEST_TERMS`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:438)
  - tomorrow-planning fork entry point
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:738)
  - `_is_tomorrow_planning_request(...)`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:758)
  - `_is_constraints_scheduling_request(...)`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:1274)
  - `_generic_practical_fallback_reply(...)`

## Strongest remaining defect found

The strongest remaining first-turn live-use defect is the tomorrow-schedule family misrouting onto the overloaded-week pushback path instead of the existing tomorrow-planning fork:

- `I need help with my schedule tomorrow.`
- `I need help with my schedule for tomorrow.`

Current repo truth:
- `You do not need a better plan yet. You need one cut. What is actually immovable this week?`

That is not just generic. It is actively wrong on timeframe: the user asked about tomorrow, but the reply pushes them into a week-level overload fork with `this week` language.

## Why it is higher value than adjacent options

This outranks the other remaining misses because:

1. It is a misroute into the wrong concrete fork, not just a fallback-to-generic miss.
2. The mismatch is user-visible and specific:
   - tomorrow request
   - week-level answer
3. The nearby truthful seam already exists and works for very close phrasing:
   - `I need help planning tomorrow.` -> tomorrow-planning fork
   - `I need help scheduling tomorrow.` -> tomorrow-planning fork
   - `I need help organizing tomorrow.` -> tomorrow-planning fork
   - `I need help with tomorrow's schedule.` -> tomorrow-planning fork
4. The defect is highly concrete in code:
   - `schedule` currently appears in `OVERLOADED_PLANNING_REQUEST_TERMS`
   - that makes `my schedule tomorrow` look like overloaded-week language before the narrower tomorrow-planning intent is honored
5. The appointment-based planning family is still a real miss, but it currently falls to the generic sorter. By contrast, the tomorrow-schedule family is being pushed into a specific but misleading lane, which is a sharper usability defect.

## Whether code/tests changed or next bounded slice only

No code or tests changed in this slice.

This is a recommendation-only reassessment slice.

## Exact commands run

Fresh prompt sweep:

```bash
python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet={"available_capabilities":["ongoing conversation in this shell","conversation turn persistence"]}
prompts=[
    "I need help mapping out tomorrow.",
    "I need help planning around two appointments.",
    "I need help planning around my appointments.",
    "I need help scheduling around appointments.",
    "I need help with my schedule tomorrow.",
    "I need help with tomorrow afternoon.",
    "I need help with this outline.",
    "I need help with this summary.",
    "I need help with this recap.",
    "I need help with my schedule this week.",
    "I need help planning tomorrow.",
    "I need help scheduling around constraints.",
    "I need help with this meeting.",
    "I need help with my follow-up.",
    "I need help with this presentation.",
    "I need help with my email.",
    "I need help with my one-on-one.",
]
for prompt in prompts:
    print('PROMPT:', prompt)
    print(generate_companion_fallback(prompt, packet))
    print('---')
PY
```

Tomorrow/constraints comparison battery:

```bash
python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet={"available_capabilities":["ongoing conversation in this shell","conversation turn persistence"]}
prompts=[
    "I need help planning around two meetings.",
    "I need help planning around two appointments.",
    "I need help planning around my appointments.",
    "I need help scheduling around appointments.",
    "I need help scheduling around constraints.",
    "I need help planning around constraints.",
    "I need help planning tomorrow.",
    "I need help mapping out tomorrow.",
    "I need help with tomorrow afternoon.",
    "I need help with my schedule tomorrow.",
    "I need help with tomorrow's schedule.",
    "I need help with my schedule for tomorrow.",
    "I need help scheduling tomorrow.",
    "I need help organizing tomorrow.",
]
for prompt in prompts:
    print(prompt)
    print(generate_companion_fallback(prompt, packet))
    print()
PY
```

Code seam inspection:

```bash
sed -n '321,445p' jarvis/companion_spine.py
sed -n '635,770p' jarvis/companion_spine.py
sed -n '1274,1332p' jarvis/companion_spine.py
nl -ba jarvis/companion_spine.py | sed -n '79,100p'
```

## Exact results

Highest-value current defect:
- `I need help with my schedule tomorrow.` -> overloaded-week pushback fork
- `I need help with my schedule for tomorrow.` -> overloaded-week pushback fork

Direct seam comparison:
- `I need help planning tomorrow.` -> tomorrow-planning fork
- `I need help scheduling tomorrow.` -> tomorrow-planning fork
- `I need help organizing tomorrow.` -> tomorrow-planning fork
- `I need help with tomorrow's schedule.` -> tomorrow-planning fork

Other inspected misses still exist, but ranked lower:
- `I need help planning around two appointments.` -> generic practical sorter
- `I need help planning around my appointments.` -> generic practical sorter
- `I need help scheduling around appointments.` -> generic practical sorter
- `I need help mapping out tomorrow.` -> generic practical sorter
- `I need help with this outline.` -> generic practical sorter
- `I need help with this summary.` -> generic practical sorter
- `I need help with this recap.` -> generic practical sorter

## Clear Architect recommendation

Recommended next bounded slice only:

**Slice 120: Companion Tomorrow-Schedule Opener Hardening**

Bounded target family:
- `I need help with my schedule tomorrow.`
- `I need help with my schedule for tomorrow.`

Truth boundary to preserve:
- route tomorrow-schedule phrasing to the existing tomorrow-planning fork
- do not weaken the overloaded-week capacity-pushback lane for genuine week/schedule overload asks
- keep constraints-scheduling, meeting, follow-up, agenda, inbox, drafting, presentation, decision, and hard-conversation seams unchanged

That is the cleanest next repair because it corrects a concrete misroute into the wrong fork, with a clear repo-truth contrast between tomorrow-schedule phrasing that works and tomorrow-schedule phrasing that does not.
