# JARVIS Project Context

## Mission

JARVIS is a private household intelligence system with a JARVIS personality, not a novelty smart speaker. The assistant should reduce friction, improve stewardship, and preserve family trust.

## Architectural Stance

- Local first for home state, sensors, automations, and sensitive memory.
- OpenAI for voice, multimodal reasoning, executive assistance, and workshop/creative copilots.
- OpenClaw for local chat, approvals, operator shell, and future channel integrations.
- Home Assistant as the house nervous system and actuator boundary.
- Strong permission model for any action that leaves the home, changes shared commitments, or affects physical security.

## Known Household Stack

- Alexa Dots throughout the house for ambient voice reach.
- Apple TVs throughout the house for shared display surfaces.
- Nest thermostat for climate control.
- Kasa for lighting and outlet controls.
- Kasa cameras for porch, garage, and perception/security feeds.
- Eero Wi-Fi as the network foundation.
- MyQ garage door openers for arrival and departure state.
- X-Sense XP0A-MR31 smoke and CO system with voice location.
- Family iPhones for identity, presence, and second-factor approvals.
- Apple Watches for quieter alerts and wearable nudges.

## Known Workshop Stack

- Creality K2 Pro Combo as the primary FDM printer.
- Creality HALOT-ONE for fine-detail resin work.
- Creality Falcon 5W laser for engraving, templates, and light cutting.
- Titoe 4540 CNC for routed and milled fabrication.
- Cricut Joy Xtra for labels, masks, and stencil workflows.

## Model Routing

- `gpt-realtime-1.5` for rich duplex voice sessions.
- `gpt-5.4-mini` for primary household reasoning and executive/copilot work.
- `gpt-5.4-nano` for cheap routing, classification, tagging, and low-risk summarization.
- Local heuristics or local small models for wake word, room classification, and safety-first guard checks.

## User Profiles

- Chris: strategist, writer, maker, Scout leader, Chronicle builder.
- Rebekah: household coordinator, troop organizer, family logistics lead.
- Caleb: coached student with accountability and formation guardrails.
- Anna: creative student with encouragement and anti-ghostwriting boundaries.

## Core Guardrails

- No automatic external messaging without explicit approval.
- No remote unlock from voice alone.
- No deceptive homework completion for children.
- No cloud archive of raw household video by default.
- No bedroom or bathroom cameras.
- No physically hazardous workshop automation without manual control.

## Initial Build Target

The first implementation target is Phase 1 plus the spine of later phases:

1. Voice/persona shell
2. Morning brief and household state model
3. Permission engine
4. Family profiles and modes
5. OpenAI model router
6. Home Assistant/OpenClaw integration seams
7. Planning artifacts detailed enough to drive implementation stories

## Current Integration Priorities

1. iPhone presence and approval flows
2. MyQ garage state
3. Nest thermostat
4. Kasa lighting and outlet scenes
5. Kasa camera feeds
6. X-Sense safety alerts
7. Apple TV family display surfaces
8. Alexa endpoint strategy
