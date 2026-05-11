# Phase 5: Adaptive Personas and Digital Twin Foundations

Phase 5 adds the first honest adaptation layer on top of identity, memory, First Light, and always-on runtime.

## What this phase adds

- Profile-backed voice identity settings per person
- Presence-oriented room preferences per person
- Device learning from repeated use
- A visible adaptive persona snapshot in Settings
- A stored "digital twin" foundation built from:
  - identity profile
  - approved profile facts
  - First Light history
  - device behavior
  - connected presence signals

## Voice identity

Each family profile can now carry:

- `preferred_voice`
- `voice_aliases`

These are not biometric speaker models. They are profile-backed cues that let JARVIS improve name inference and voice personalization without pretending to do more than it does.

## Presence identity

Each family profile can now carry:

- `primary_rooms`
- `morning_room`

This gives JARVIS a cleaner starting point for:

- First Light interpretation
- room-aware anticipation
- presence-sensitive handoffs

## Device learning

Each device can now remember:

- `last_actor_id`
- `last_actor_source`
- `actor_history`
- `suggested_default_actor_id`

That means a shared or drifting device can start to show a trustworthy default suggestion after repeated use, instead of forcing the household to re-teach JARVIS the same pattern forever.

## Persona snapshot

New API:

- `GET /api/persona-snapshot`
- `POST /api/persona-refresh`

The adaptive persona snapshot includes:

- voice identity
- presence identity
- morning pattern
- stable preferences from approved profile facts
- likely next needs
- signal counts

This is the first visible digital-twin layer: a structured summary of what JARVIS has learned and what it still does not know.

## Truth boundaries

Phase 5 still does **not** claim:

- biometric speaker recognition
- face recognition
- continuous household presence certainty
- fully autonomous anticipation

It uses real local signals and real stored history, but it stays honest about the limits.
