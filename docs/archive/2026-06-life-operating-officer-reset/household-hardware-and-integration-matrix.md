# Household Hardware and Integration Matrix

This is the concrete house and workshop inventory JARVIS is now targeting.

## House Stack

| System | Current Hardware | Role in JARVIS | Priority | Notes |
|---|---|---|---|---|
| Voice endpoints | Alexa Dots throughout the house | room-level voice reach | High | Best near-term ambient interface while JARVIS remains the brain |
| Shared displays | Apple TVs throughout the house | family dashboard, Chronicle, watchtower, shared review | High | Excellent family-mode surfaces |
| Climate | Nest thermostat | comfort automation and climate context | High | strong early integration target |
| Lighting and outlets | Kasa lights and outlet controls | room scenes, practical automations, and outlet control | High | strong fit for dawn, dinner, and workshop support |
| Cameras | Kasa cameras | package detection, garage context, and privacy-governed perception feeds | High | likely first real camera path for E4 and E12 |
| Network | Eero Wi-Fi | network foundation and possible presence signal | Medium | useful for device-aware context |
| Garage | MyQ garage door openers | departure choreography, arrival state, security context | High | one of the highest-value real integrations |
| Safety | X-Sense XP0A-MR31 smoke/CO system | smoke and carbon monoxide alert path | High | major E12 real-world upgrade |
| Identity/presence | Family iPhones | approvals, presence, arrival detection, notifications | Highest | strongest second-factor and presence source |
| Wearables | Apple Watches | subtle nudges and confirmations | Medium | good for low-friction alerts |

## Workshop Stack

| System | Current Hardware | Role in JARVIS | Priority | Notes |
|---|---|---|---|---|
| FDM printer | Creality K2 Pro Combo | fit checks, prototypes, multicolor parts | High | primary print-prep and telemetry target |
| Resin printer | Creality HALOT-ONE (CL-60) | fine-detail parts, molds, precision work | Medium | resin-specific workflow lane |
| Laser | Creality Falcon 5W | engraving, templates, masks, signage | Medium | safety-heavy job staging |
| CNC | Titoe 4540 CNC | routed and milled fabrication | Medium | safety-heavy machining lane |
| Craft cutter | Cricut Joy Xtra | labels, vinyl masks, stencils | Medium | household and workshop utility lane |

## Integration Priority Order

### Household

1. iPhone presence and approval flows
2. MyQ garage
3. Nest thermostat
4. Kasa lighting and outlet scenes
5. Kasa cameras
6. X-Sense safety alerts
7. Apple TV display surfaces
8. Alexa endpoint strategy
9. Eero-aware presence enhancements
10. Apple Watch notification refinements

### Workshop

1. Creality K2 print-prep and status adapter
2. HALOT resin workflow lane
3. Falcon laser job-prep and safety gating
4. Titoe CNC job-prep and safety gating
5. Cricut light-fabrication lane

## Architecture Implications

- JARVIS is not one device. It is an orchestration layer across phones, voice endpoints, displays, safety systems, and fabrication tools.
- Alexa Dots are likely the near-term voice edge.
- Apple TVs are likely the near-term family display edge.
- iPhones are the cleanest approval and identity edge.
- Home Assistant should remain the actuator boundary even when individual vendors expose their own apps.

## Next Adapter Wave

The strongest next real integration wave is:

1. MyQ
2. Nest
3. Kasa
4. Kasa cameras
5. X-Sense
6. iPhone presence
7. K2 Pro
