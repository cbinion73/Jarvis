# JARVIS

JARVIS is a whole-home household associate, not just a voice assistant. This workspace now contains:

- the original APEX-style OpenAI voice starter
- BMAD-shaped planning artifacts for JARVIS
- a Python scaffold for the household orchestrator, permission engine, and family-mode runtime

## Current Direction

The target system is:

- local-first for home state, sensors, automations, and sensitive memory
- OpenAI-powered for voice, reasoning, summaries, and multimodal assistance
- OpenClaw-backed for agent shell, chat, approvals, and future tool orchestration
- Home Assistant-backed for the house nervous system

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Key environment values:

```bash
OPENAI_API_KEY=sk-proj-your-key-here
ELEVENLABS_API_KEY=your-elevenlabs-key-here
OPENAI_TEXT_MODEL=gpt-5.4-mini
OPENAI_ROUTER_MODEL=gpt-5.4-nano
OPENAI_REALTIME_MODEL=gpt-realtime-1.5
JARVIS_TTS_PROVIDER=auto
JARVIS_STT_PROVIDER=auto
LOCALAI_BASE_URL=http://127.0.0.1:8080
PIPER_MODEL_PATH=/share/piper/en_GB-alan-medium.onnx
JARVIS_GOOGLE_CLIENT_SECRET=config/google_client_secret.json
```

## Planning Artifacts

BMAD-shaped first drafts live in:

- [_bmad-output/planning-artifacts/jarvis-prd-v1.md](/Users/chris/Desktop/CODE/JARVIS/_bmad-output/planning-artifacts/jarvis-prd-v1.md)
- [_bmad-output/planning-artifacts/jarvis-architecture-v1.md](/Users/chris/Desktop/CODE/JARVIS/_bmad-output/planning-artifacts/jarvis-architecture-v1.md)
- [_bmad-output/planning-artifacts/jarvis-epics-v1.md](/Users/chris/Desktop/CODE/JARVIS/_bmad-output/planning-artifacts/jarvis-epics-v1.md)

Shared context for future agent work lives in:

- [docs/project-context.md](/Users/chris/Desktop/CODE/JARVIS/docs/project-context.md)
- [docs/household-hardware-and-integration-matrix.md](/Users/chris/Desktop/CODE/JARVIS/docs/household-hardware-and-integration-matrix.md)

## Python Scaffold

The first runtime scaffold lives in [jarvis](/Users/chris/Desktop/CODE/JARVIS/jarvis).

Useful commands:

```bash
python -m jarvis summary
python -m jarvis voice-stack
python -m jarvis briefing --actor Chris
python -m jarvis plan --actor Chris --room office --request "Prep my morning meeting"
python -m jarvis respond --actor Chris --room office --request "Summarize today's priorities"
python -m jarvis openclaw-bridge --request "Jarvis, prep my meeting brief"
python -m jarvis meeting-brief --context "Meeting: ... "
python -m jarvis meeting-followup --transcript "Transcript or notes ..."
python -m jarvis decision-framework --context "Meeting says it is a decision session, but the room is still vague."
python -m jarvis research-summary --topic "agentic AI workflows" --notes "Source notes ..."
python -m jarvis confidentiality-review --text "Sensitive work text ..."
python -m jarvis manuscript-review --excerpt "Draft excerpt ..."
python -m jarvis ironclad-editor --excerpt "Purpose activates performance through aligned organizational behaviors."
python -m jarvis venture-brief --topic "agentic AI workflows" --notes "Market notes ..."
python -m jarvis devotional-pause --theme "stewardship under pressure"
python -m jarvis family-devotional --theme "leadership without striving" --context "Prepare something suitable for tonight."
python -m jarvis chronicle-capture --theme "stewardship under pressure" --note "Reflection ..."
python -m jarvis chronicle-timeline --limit 5
python -m jarvis chronicle-themes --limit 20
python -m jarvis mode-status
python -m jarvis mode-brief --mode dawn-protocol
python -m jarvis mode-transition --actor Rebekah --mode family-morning --reason "Kids are up."
python -m jarvis family-plan --actor Rebekah --request "Give me the calm version of tonight."
python -m jarvis departure-plan --actor Rebekah --context "School drop-off and troop handoff both hit tonight."
python -m jarvis rebekah-center --request "Give me the calm version of tonight with troop logistics, groceries, and school prep."
python -m jarvis troop-plan --actor Rebekah --request "Plan tonight's troop meeting with light rain before arrival and indoor backup."
python -m jarvis grocery-support --actor Rebekah --request "Group the grocery pickup and suggest an easy dinner."
python -m jarvis meal-plan --actor Rebekah --request "Group the pickup and keep dinner easy, warm, and fast."
python -m jarvis vehicle-plan --actor Chris --request "Rebekah needs the van tonight, and I still need a lunch-window supply run."
python -m jarvis weather-contingency --actor Rebekah --request "Light rain may affect school departure and troop arrival tonight."
python -m jarvis message-draft --actor Rebekah --audience "Troop parents" --purpose "Indoor backup update" --context "Rain may affect arrival..."
python -m jarvis parent-message --actor Rebekah --audience "Troop parents" --purpose "Indoor backup update" --context "Rain may affect arrival..."
python -m jarvis message-drafts --limit 5
python -m jarvis anomaly-watch
python -m jarvis security-event --actor Chris --category package --location "front porch" --detail "Package delivered near the rain-exposed edge of the porch." --severity watch
python -m jarvis safety-alert --actor Chris --hazard leak --source "garage freezer area" --detail "Water pooling detected near the freezer line." --severity critical
python -m jarvis weather-alert --actor Rebekah --context "Troop meeting arrival and school departure both depend on a short rain break."
python -m jarvis child-arrival --actor Caleb --location "front door" --detail "Backpack dropped by the mudroom door and snack requested immediately."
python -m jarvis unlock-policy --actor Chris --target "front door"
python -m jarvis overnight-review
python -m jarvis security-incidents --limit 10
python -m jarvis home-overview
python -m jarvis room-scene --actor Chris --room kitchen --scene "Dinner Mode"
python -m jarvis climate-status
python -m jarvis climate-control --actor Chris --zone "main floor" --mode heat_cool --target-temp 69
python -m jarvis access-overview
python -m jarvis access-control --actor Chris --target "front door" --state locked
python -m jarvis garage-status
python -m jarvis garage-check --actor Chris --target "Main Garage Door"
python -m jarvis leak-monitor
python -m jarvis cold-storage-monitor
python -m jarvis energy-window --appliance dishwasher
python -m jarvis outage-readiness
python -m jarvis perception-overview
python -m jarvis mic-ingress --microphone "Kitchen Alexa Dot" --transcript "Jarvis, what does the family need to know this morning?" --wake-word --actor-hint Rebekah
python -m jarvis presence-update --sensor "Kitchen Presence" --room kitchen --occupied --detail "Kids entered the kitchen for breakfast."
python -m jarvis phone-presence --actor Anna --state arriving --zone home-boundary --detail "Anna is approaching the house after school."
python -m jarvis camera-event --camera "Porch Camera" --event-type package --detail "Package dropped near the exposed edge during light rain." --object package --confidence high
python -m jarvis package-rule --zone "front porch" --preferred-drop "left side under cover" --rain-sensitive --note "Avoid the exposed edge when rain is likely."
python -m jarvis object-recognition --source "Workshop Overhead Camera" --room workshop --object "garden bench bracket" --detail "Bracket on the bench with visible crack near bend radius." --confidence high
python -m jarvis environmental-anomaly --category freezer --source "garage freezer" --reading "3 degrees warmer than baseline" --baseline "0 to 3 degrees above baseline variance" --severity elevated --detail "Still safe, but outside the household norm."
python -m jarvis privacy-state
python -m jarvis privacy-update --kind microphone --target kitchen-alexa-dot --muted true
python -m jarvis memory-overview --viewer Chris
python -m jarvis memory-remember --actor Chris --type personal --scope personal --owner Chris --summary "Chris prefers the executive brief after coffee." --detail "Hold the dense briefing until caffeine has entered the bloodstream." --tags "preference,morning,executive"
python -m jarvis memory-review --viewer Chris
python -m jarvis memory-proposals --status pending
python -m jarvis memory-approve --proposal-id <proposal-id> --decision approved
python -m jarvis memory-export --viewer Chris
python -m jarvis memory-forget --viewer Chris --entry-id <entry-id>
python -m jarvis voice-note --actor Rebekah --source van --note "Permission forms, snack rotation, and summer camp shirt sizes need follow-up."
python -m jarvis voice-notes --limit 5
python -m jarvis child-boundaries
python -m jarvis tutor --actor Caleb --subject math --request "Quiz me on fractions and make me explain my steps."
python -m jarvis tutoring-summaries --viewer Rebekah --limit 5
python -m jarvis device-boundary --actor Caleb --window "After-school reset"
python -m jarvis device-boundaries --limit 10
python -m jarvis workshop-plan --actor Chris --request "Prepare a prototype plan for the Garden of Hope bracket replacement."
python -m jarvis printer-status
python -m jarvis inspect-part --actor Chris --part "Garden bench bracket" --observations "Stress crack at bend radius..." --goals "Increase durability and prototype quickly."
python -m jarvis material-recommendation --actor Chris --part "Garden bench bracket" --use-case "Outdoor prototype and final fabrication decision" --requirements "Outdoor durability, drain path, moderate load, fast prototype iteration."
python -m jarvis cad-package --actor Chris --part "Garden bench bracket" --dimensions "hole spacing 110 mm, plate width 30 mm, thickness 8 mm, bend radius 12 mm" --constraints "Preserve hole pattern, add drain path, allow subtle Scout motif."
python -m jarvis print-prep --actor Chris --part "Garden bench bracket" --printer bambu-x1c --material PETG-CF --profile functional-prototype --notes "Orient to protect bend strength and confirm fit before load testing."
python -m jarvis safety-check --actor Chris --operation "Cut and drill steel bracket replacement" --context "Bench work, eye protection on, manual review before machine run."
python -m jarvis inventory
python -m jarvis vendor-prep --actor Chris --part "Garden bench bracket" --vendor "carbon-fiber service bureau" --process "CNC or reinforced nylon fabrication" --material "carbon-fiber nylon" --notes "Preserve hole spacing and add a drain path."
python -m jarvis cad-packages --limit 5
python -m jarvis print-preps --limit 5
python -m jarvis vendor-preps --limit 5
python -m jarvis serve --host 0.0.0.0 --port 8787
python -m jarvis voice --text "Jarvis, what should I focus on this morning?" --silent
python -m jarvis voice --text-loop
python -m jarvis voice --loop
python -m jarvis voice --realtime
python -m jarvis voice --list-devices
python -m jarvis catalyst-overview
python -m jarvis catalyst-email-triage --actor Chris --sender "name@example.com" --subject "Subject" --body "Email body"
python -m jarvis catalyst-project-brief --actor Chris --project-name "Project" --problem "Problem" --desired-outcome "Outcome"
python apex_hello.py
python apex_hello.py --loop
python apex_hello.py --loop --text-input
python apex_hello.py --list-devices
```

See [docs/catalyst-personal.md](/Users/chris/Desktop/CODE/JARVIS/docs/catalyst-personal.md) for the personal-safe Catalyst backend now embedded in JARVIS.
See [docs/google-connect.md](/Users/chris/Desktop/CODE/JARVIS/docs/google-connect.md) for personal Gmail and Google Calendar connection setup.

## Local Product Surface

The current MVP product is a local JARVIS dashboard with:

- household summary
- Body Home Mission framing
- morning briefing generation
- request planning
- approval queue
- integration status
- recent activity log
- explainability and approval-history review
- family-facing low-clutter display mode
- live OpenAI-backed response generation

Once running, open:

```text
http://127.0.0.1:8787
```

## Voice Shell

Epic 2 now has a dedicated JARVIS voice shell inside `python -m jarvis voice`.

- `--text` runs one inferred turn through the real runtime
- `--text-loop` runs a typed conversation loop with wake-word handling
- `--loop` runs push-to-talk mic capture
- `--realtime` runs OpenAI Realtime transcription with server-side VAD
- `--list-devices` shows local input devices

The local voice context map lives in [household/jarvis_voice_context.example.json](/Users/chris/Desktop/CODE/JARVIS/household/jarvis_voice_context.example.json).

Additional voice-shell behavior now in place:

- `--quiet` lowers reply intensity and playback volume for calmer interactions
- `--whisper` pushes the shell into a softer, low-disruption mode
- spoken playback is now interruptible, so a new turn can cut off the previous reply
- local macOS fallback TTS is available when ElevenLabs is unavailable
- local-first provider routing is now available through `Piper` and `LocalAI`
- on this machine, run the voice shell from [`.venv`](/Users/chris/Desktop/CODE/JARVIS/.venv) if you want the full audio dependency path instead of the reduced parser fallback from the system Python

The local voice stack guide lives in [docs/local-voice-stack.md](/Users/chris/Desktop/CODE/JARVIS/docs/local-voice-stack.md).

Supporting local-voice assets now live in:

- [infra/docker-compose.local-voice.yml](/Users/chris/Desktop/CODE/JARVIS/infra/docker-compose.local-voice.yml)
- [infra/localai/models/whisper-1.yaml](/Users/chris/Desktop/CODE/JARVIS/infra/localai/models/whisper-1.yaml)
- [infra/localai/models/jarvis-piper.yaml](/Users/chris/Desktop/CODE/JARVIS/infra/localai/models/jarvis-piper.yaml)
- [infra/livekit/jarvis_agent.py](/Users/chris/Desktop/CODE/JARVIS/infra/livekit/jarvis_agent.py)

## House Nervous System

Epic 3 now has a dedicated local home-control subsystem:

- `home-overview` for the staged household control picture
- `room-scene` for room scenes and practical lighting intent
- `climate-status` and `climate-control` for Nest-shaped climate state and changes
- `access-overview` and `access-control` for lock and monitored-door state
- `garage-status` and `garage-check` for MyQ-shaped garage state and safe-close review
- `leak-monitor` for leak sensor summaries
- `cold-storage-monitor` for freezer and fridge variance status
- `energy-window` for utility-aware appliance timing
- `outage-readiness` for outage posture, degrade order, and manual fallbacks

The home-control profile lives in [household/jarvis_home_assistant.example.json](/Users/chris/Desktop/CODE/JARVIS/household/jarvis_home_assistant.example.json).

## Perception Mesh

Epic 4 now has a dedicated local perception subsystem:

- `perception-overview` for the ambient sensing rollup
- `mic-ingress` for far-field microphone events
- `presence-update` for room occupancy changes
- `phone-presence` for iPhone-based arrival and departure context
- `camera-event` for workshop, porch, and garage camera events
- `package-rule` for preferred delivery-drop logic
- `object-recognition` for workshop-part recognition events
- `environmental-anomaly` for freezer, weather, motion, and network anomalies
- `privacy-state` and `privacy-update` for camera/microphone indicators and mute state

## Family Modes

Epic 6 now has a fuller household-rhythm layer:

- `mode-brief` for mode-specific playbooks across Dawn Protocol, Family Morning, Steward Mode, Work Mode, Deep Work, Dinner Mode, Chronicle Mode, Goodnight, and Watchtower
- `departure-plan` for mudroom-style leaving-the-house choreography
- `meal-plan` for structured low-complexity meal support with grocery grouping
- `vehicle-plan` for van/car assignment and route posture
- `weather-contingency` for rain-aware family logistics

The family-mode profile lives in [household/jarvis_family_profile.example.json](/Users/chris/Desktop/CODE/JARVIS/household/jarvis_family_profile.example.json).

The perception profile lives in [household/jarvis_perception_profile.example.json](/Users/chris/Desktop/CODE/JARVIS/household/jarvis_perception_profile.example.json).

## Memory Core

Epic 5 now has a dedicated local memory subsystem:

- `memory-overview` for schema, counts, encryption posture, and pending proposals
- `memory-remember` for household, personal, project, and safety memory capture
- `memory-review` for permission-filtered entry review
- `memory-forget` for explicit deletion
- `memory-export` for local decrypted export
- `memory-proposals` and `memory-approve` for sensitive-fact approval workflow

The memory profile lives in [household/jarvis_memory_profile.example.json](/Users/chris/Desktop/CODE/JARVIS/household/jarvis_memory_profile.example.json).

## Executive and Chronicle Tools

Epic 3 now has local specialist surfaces:

- `meeting-brief` for executive prep
- `meeting-followup` for transcript follow-up matrices
- `decision-framework` for criteria-first steering when a meeting is drifting
- `research-summary` for evidence-tiered summaries
- `confidentiality-review` for Thermo-safe redaction checks
- `manuscript-review` for executive editing support
- `ironclad-editor` for the named Iron-Clad Executive Editor protocol
- `venture-brief` for venture and market-monitoring pattern briefs
- `devotional-pause` for Scripture, interpretation, prayer, silence, and next-step framing
- `family-devotional` for family-table devotional preparation
- `chronicle-capture`, `chronicle-timeline`, and `chronicle-themes` for local Chronicle reflection storage and recurring-theme review

## Family Modes and Logistics

Epic 4 now has local family-mode and logistics surfaces:

- `mode-status` and `mode-transition` for household mode state
- `family-plan` for calm sequencing and contingency planning
- `message-draft` and `message-drafts` for staged family communication
- `anomaly-watch` for explicit watch items and household tensions

The family-mode profile lives in [household/jarvis_family_profile.example.json](/Users/chris/Desktop/CODE/JARVIS/household/jarvis_family_profile.example.json).

## Rebekah Coordination

Epic 8 now has a dedicated Rebekah-facing coordination lane:

- `rebekah-center` for the calm command-brief surface
- `troop-plan` for weather, backup, supplies, and parent-note planning
- `parent-message` for staged parent communication with approval handoff
- `grocery-support` for grouped groceries and an easy dinner suggestion
- `voice-note` and `voice-notes` for van-style follow-up capture

## Security and Watchtower

Epic 12 now has a dedicated security subsystem:

- `security-event` for package and unusual-motion incident capture
- `safety-alert` for smoke, CO, and leak escalation
- `weather-alert` for departure and event timing advisories
- `child-arrival` for safe-home and arrival event capture
- `unlock-policy` for no-unlock-with-voice-only enforcement checks
- `overnight-review` for the quiet overnight watchtower rollup
- `security-incidents` for recent incident review

## Infrastructure and Deployment

Epic 14 now has explicit deployment artifacts:

- [infrastructure-and-deployment.md](/Users/chris/Desktop/CODE/JARVIS/docs/infrastructure-and-deployment.md) for the target household footprint
- [operations-runbook.md](/Users/chris/Desktop/CODE/JARVIS/docs/operations-runbook.md) for day-to-day runtime operations
- [jarvis_infra_profile.example.json](/Users/chris/Desktop/CODE/JARVIS/household/jarvis_infra_profile.example.json) for host, display, storage, power, and network planning
- [com.chris.jarvis.dashboard.plist](/Users/chris/Desktop/CODE/JARVIS/infra/launchd/com.chris.jarvis.dashboard.plist) and [com.chris.jarvis.voice-shell.plist](/Users/chris/Desktop/CODE/JARVIS/infra/launchd/com.chris.jarvis.voice-shell.plist) for launchd packaging
- [install_launchd_services.sh](/Users/chris/Desktop/CODE/JARVIS/infra/scripts/install_launchd_services.sh) for installing the local dashboard service template

## Child-Safe Tutoring

Epic 5 now has a dedicated tutoring subsystem:

- `child-boundaries` shows the enforced boundaries for Caleb and Anna
- `tutor` runs a child-safe tutoring turn with persistent session logging
- `tutoring-summaries` gives an adult-only parent view of recent coaching patterns
- `device-boundary` and `device-boundaries` handle device dock and study-boundary routines

The tutoring policy profile lives in [household/jarvis_tutoring_profile.example.json](/Users/chris/Desktop/CODE/JARVIS/household/jarvis_tutoring_profile.example.json).

## Workshop Copilot

Epic 6 now has a dedicated workshop subsystem:

- `workshop-plan` for prototype and material sequencing
- `printer-status` for the local Bambu status seam
- `inspect-part` for persistent diagnosis from observations
- `material-recommendation` for prototype-vs-final material guidance
- `cad-package` and `cad-packages` for persistent rough CAD package generation
- `print-prep` and `print-preps` for staged slicer handoff guidance
- `safety-check` for workshop interlocks and warnings
- `inventory` for filament, consumable, and hardware status
- `vendor-prep` and `vendor-preps` for staged external fabrication packages behind approval

The current workshop profile now reflects the real maker fleet:

- Creality K2 Pro Combo
- Creality HALOT-ONE
- Creality Falcon 5W laser
- Titoe 4540 CNC
- Cricut Joy Xtra

The workshop profile lives in [household/jarvis_workshop_profile.example.json](/Users/chris/Desktop/CODE/JARVIS/household/jarvis_workshop_profile.example.json).

## Build Guide Mapping

| Guide Layer | Original | This Workspace |
| --- | --- | --- |
| Brain SDK | `anthropic` | `openai` |
| Brain env var | `ANTHROPIC_API_KEY` | `OPENAI_API_KEY` |
| Brain client | `anthropic.Anthropic()` | `OpenAI()` |
| Generation call | `messages.create(...)` | `responses.create(...)` |
| Text output | `response.content[0].text` | `response.output_text` |
| Voice SDK | `elevenlabs` | `elevenlabs` |
