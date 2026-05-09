# Current Blockers

## Verified tonight

- The local JARVIS runtime scaffold works for summary, planning, approval staging, and integration-status reporting.
- OpenClaw is configured with env-backed OpenAI auth and a working local model selection path.

## Active blockages

1. Home Assistant is not connected yet.
   Current state: the live adapter exists, but `HOME_ASSISTANT_URL` or `HOME_ASSISTANT_TOKEN` is still missing from the runtime path used by the scaffold.

2. The BMAD/OpenClaw wizard drifts into optional channel setup before it helps with core household architecture.
   Current impact: we should keep using BMAD as artifact structure, not as the primary execution engine for every step.

3. No live household entity map is wired to the real house yet.
   Current impact: the repo now has a profile-backed entity map and working local house-control flows, but real garage, climate, lighting, lock, and leak entities still need the actual Home Assistant names and services.

4. Memory is now encrypted and local, but it is not yet connected to Obsidian or other human-facing note systems.
   Current impact: the memory core works inside JARVIS with review, export, and approvals, but there is not yet a first-class vault publishing layer for shared long-form notes.

5. No live Bambu or workshop integrations are wired yet.
   Current impact: the local maker stack now handles planning, inspections, CAD packaging, print prep, safety checks, inventory, and vendor staging, but printer telemetry and upload paths are still simulated.

6. Realtime reply audio is not yet a single full-duplex speech session.
   Current impact: the Realtime path now handles streaming transcription and interruptible playback, but spoken replies still come back through `Responses API` plus ElevenLabs or local fallback speech instead of one unified speech-to-speech session.

7. Wake word, speaker, and room inference are currently heuristic.
   Current impact: they work from config, context phrases, input-device mapping, and perception events, but not yet from dedicated local wake-word or biometric speaker models.

8. The perception subsystem is profile-backed, but not yet wired to physical devices.
   Current impact: microphone ingress, presence, phone arrival, camera events, package rules, anomalies, and privacy state now work in the product, but the actual household camera feeds, motion sensors, and mute indicators still need rollout.

9. The E14 deployment footprint is defined, but it is not yet applied to household hardware.
   Current impact: launchd templates, runbooks, display/storage/network plans, and voice-satellite guidance now exist, but the final always-on host, NAS path, UPS stack, and segmented network still need to be rolled out in the house.

## Next practical moves

- Add real Home Assistant credentials and entity names.
- Map actual family calendar and reminder sources.
- Decide whether Phase 1 voice should begin with OpenAI Realtime directly or a Home Assistant Assist front end with JARVIS escalation.
- Add first real device adapter: garage, freezer, or printer.
- Wire the first real perception feeds: porch camera, garage camera, one room presence sensor, and one phone-arrival automation.
- Add the first human-facing memory publishing layer, likely Obsidian vault output for Chronicle, executive notes, and household memory review.
- Apply the defined E14 host, storage, UPS, and network plan to the real household footprint.
