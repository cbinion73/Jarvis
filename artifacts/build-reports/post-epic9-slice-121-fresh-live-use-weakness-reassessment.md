# Post-Epic 9 Slice 121: Fresh Live-Use Weakness Reassessment

Ready for Architect Office review: yes

## Exact prompts or routes inspected

Fresh bounded prompt sweep:
- `I need help mapping out tomorrow.`
- `I need help planning around two appointments.`
- `I need help planning around my appointments.`
- `I need help scheduling around appointments.`
- `I need help around my appointments tomorrow.`
- `I need help with tomorrow afternoon.`
- `I need help with this outline.`
- `I need help with this summary.`
- `I need help with this recap.`
- `I need help with my calendar tomorrow.`
- `I need help planning tomorrow.`
- `I need help scheduling around constraints.`
- `I need help with this meeting.`
- `I need help with my follow-up.`
- `I need help with my email.`
- `I need help with this presentation.`

Tomorrow/calendar comparison battery:
- `I need help with my calendar tomorrow.`
- `I need help with my calendar for tomorrow.`
- `I need help with tomorrow's calendar.`
- `I need help with my calendar this week.`
- `I need help planning around two appointments.`
- `I need help planning around my appointments.`
- `I need help scheduling around appointments.`
- `I need help mapping out tomorrow.`
- `I need help planning tomorrow.`
- `I need help scheduling around constraints.`

## Exact code seams inspected

- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:321)
  - `generate_companion_fallback(...)` opener ordering
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:89)
  - `OVERLOADED_PLANNING_REQUEST_TERMS`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:438)
  - tomorrow-planning fork entry point
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:738)
  - `_is_tomorrow_planning_request(...)`
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:1276)
  - `_generic_practical_fallback_reply(...)`

## Strongest remaining defect found

The strongest remaining first-turn live-use defect is the tomorrow-calendar family misrouting into the overloaded-week pushback fork instead of the existing tomorrow-planning fork:

- `I need help with my calendar tomorrow.`
- `I need help with my calendar for tomorrow.`

Current repo truth:
- `You do not need a better plan yet. You need one cut. What is actually immovable this week?`

That is not just a fallback miss. It is the wrong concrete fork with the wrong timeframe: tomorrow ask, week-level reply.

## Why it is higher value than adjacent options

This outranks the remaining generic misses because:

1. It is a misroute into the wrong existing fork, not merely a generic-sorter fallback.
2. The mismatch is easy to feel in live use:
   - tomorrow request
   - `this week` pushback answer
3. The nearby truthful seam already exists and works for almost the same phrasing:
   - `I need help with tomorrow's calendar.` -> tomorrow-planning fork
   - `I need help planning tomorrow.` -> tomorrow-planning fork
4. The defect is concrete in code:
   - `calendar` is still inside `OVERLOADED_PLANNING_REQUEST_TERMS`
   - the tomorrow-planning matcher does not yet catch the possessive-calendar aliases
5. Appointment-based planning and `mapping out tomorrow` are still real misses, but they currently fall to the generic sorter. By contrast, the tomorrow-calendar family is being actively misclassified into a misleading week-level lane, which is a sharper chief-of-staff usefulness defect.

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
    "I need help around my appointments tomorrow.",
    "I need help with tomorrow afternoon.",
    "I need help with this outline.",
    "I need help with this summary.",
    "I need help with this recap.",
    "I need help with my calendar tomorrow.",
    "I need help planning tomorrow.",
    "I need help scheduling around constraints.",
    "I need help with this meeting.",
    "I need help with my follow-up.",
    "I need help with my email.",
    "I need help with this presentation.",
]
for prompt in prompts:
    print('PROMPT:', prompt)
    print(generate_companion_fallback(prompt, packet))
    print('---')
PY
```

Tomorrow/calendar comparison battery:

```bash
python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet={"available_capabilities":["ongoing conversation in this shell","conversation turn persistence"]}
prompts=[
    "I need help with my calendar tomorrow.",
    "I need help with my calendar for tomorrow.",
    "I need help with tomorrow's calendar.",
    "I need help with my calendar this week.",
    "I need help planning around two appointments.",
    "I need help planning around my appointments.",
    "I need help scheduling around appointments.",
    "I need help mapping out tomorrow.",
    "I need help planning tomorrow.",
    "I need help scheduling around constraints.",
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
sed -n '738,776p' jarvis/companion_spine.py
sed -n '1276,1328p' jarvis/companion_spine.py
nl -ba jarvis/companion_spine.py | sed -n '89,100p'
```

## Exact results

Highest-value current defect:
- `I need help with my calendar tomorrow.` -> overloaded-week pushback fork
- `I need help with my calendar for tomorrow.` -> overloaded-week pushback fork

Direct seam comparison:
- `I need help with tomorrow's calendar.` -> tomorrow-planning fork
- `I need help planning tomorrow.` -> tomorrow-planning fork
- `I need help scheduling around constraints.` -> constraints-scheduling fork

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

**Slice 122: Companion Tomorrow-Calendar Opener Hardening**

Bounded target family:
- `I need help with my calendar tomorrow.`
- `I need help with my calendar for tomorrow.`

Truth boundary to preserve:
- route tomorrow-calendar phrasing to the existing tomorrow-planning fork
- do not weaken the overloaded-week capacity-pushback lane for genuine week/calendar overload asks
- keep constraints-scheduling, meeting, follow-up, agenda, inbox, drafting, presentation, decision, and hard-conversation seams unchanged

That is the cleanest next repair because it fixes another concrete misroute into the wrong fork, with a very tight repo-truth contrast between tomorrow-calendar phrasing that already works and tomorrow-calendar phrasing that still does not.
