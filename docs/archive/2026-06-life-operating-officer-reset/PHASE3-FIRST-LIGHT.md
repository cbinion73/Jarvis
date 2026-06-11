# Phase 3: First Light Protocol

Phase 3 adds an anticipatory morning protocol to JARVIS.

## What it does

- Detects the first eligible morning check-in for a user profile
- Waits until after the configured morning window (`6 AM` by default)
- Generates a composed `First Light` packet
- Stores a once-per-day record so the protocol does not keep reopening
- Lets manual briefing requests force a packet preview without consuming the automatic morning trigger before the window opens

## Sources used

First Light can draw from:

- merged Google + family calendar
- unread Gmail counts
- family focus and departure checklist
- approvals
- strategic brief
- cross-domain synthesis
- formation themes

Each section is marked with a truth posture such as:

- `live`
- `staged`
- `interpreted`
- `unavailable`

## Storage

State is stored in:

- `data/settings/first_light.json`

This includes:

- last presented date per user
- packet history for comparison and `what changed since last time`

## API

- `GET /api/first-light?actor=Chris`
- `GET /api/first-light?actor=Chris&force=true`

## UI

- the shell checks First Light automatically after identity binding and dashboard load
- if eligible, it opens the briefing modal automatically
- the existing Briefing packet now renders the richer First Light protocol when present
