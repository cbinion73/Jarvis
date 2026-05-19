# JARVIS

JARVIS is a private intelligence chamber for the household — not a chatbot, not a smart speaker. It runs on a dedicated M4 Mac Mini, knows your home, your family, your rhythms, and your work, and it operates with clear trust boundaries between people and the things it's allowed to do on your behalf. Every action is either pre-approved, proposable, or held until a human says go. The goal is a system that makes the household feel cared for without surrendering control or privacy to a cloud platform.

---

## Quick Start

1. **Clone / open the project**
   ```bash
   git clone <repo-url> JARVIS
   cd JARVIS
   ```

2. **Run setup**
   ```bash
   bash scripts/setup.sh
   ```

3. **Edit `.env` with your API keys**
   ```bash
   cp .env.example .env
   # Fill in OPENAI_API_KEY, ELEVENLABS_API_KEY, and any integration keys
   ```

4. **Verify everything is up**
   ```bash
   python scripts/verify.py
   ```

5. **Open the dashboard**
   ```
   http://localhost:8787
   ```

---

## Architecture

- **Python backend (FastAPI, port 8787)** — household orchestrator, permission engine, family-mode runtime, agent dispatch, memory core, and all subsystem integrations
- **Local models via Ollama** — `phi3.5` for fast routing/classification (~200ms), `gpt-oss-20b` (or `qwen2.5:14b` as stand-in) for local reasoning; no cloud dependency for sensitive household data
- **Apple clients** — `JarvisPhone` and `JarvisWatch` connect via `JarvisKit`; health, location, and watch context flow through a typed API contract and do not leave the local network

---

## Docs

- [`docs/OLLAMA-SETUP.md`](docs/OLLAMA-SETUP.md) — install Ollama, pull models, verify the local model stack, RAM usage, troubleshooting
- [`docs/JARVIS-APPLE-HANDOFF-PACK.md`](docs/JARVIS-APPLE-HANDOFF-PACK.md) — Apple platform integration details, JarvisKit design, handoff protocol
- [`JarvisApple/HEALTH-API-CONTRACT.md`](JarvisApple/HEALTH-API-CONTRACT.md) — typed contract for health and watch data flowing from Apple devices to the JARVIS backend

---

## Python Commands

```bash
python -m jarvis serve --host 0.0.0.0 --port 8787   # start the server
python -m jarvis summary                              # household summary
python -m jarvis briefing --actor Chris              # morning briefing
python -m jarvis home-overview                       # house state
python -m jarvis mode-status                         # current household mode
python -m jarvis memory-overview --viewer Chris      # memory core status
python -m jarvis voice --text "Good morning"         # single voice turn
python -m jarvis voice --text-loop                   # typed conversation loop
python -m jarvis voice --realtime                    # OpenAI Realtime with VAD
```

Full command reference is preserved below for developer reference.

<details>
<summary>Full command list</summary>

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
python -m jarvis memory-forget --viewer Chris --entry-id <entry-id>
python -m jarvis memory-export --viewer Chris
python -m jarvis memory-proposals --status pending
python -m jarvis memory-approve --proposal-id <proposal-id> --decision approved
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
```

</details>

---

## Related Docs

- [docs/local-voice-stack.md](docs/local-voice-stack.md) — Piper, LocalAI, and voice shell setup
- [docs/catalyst-personal.md](docs/catalyst-personal.md) — personal-safe Catalyst backend
- [docs/google-connect.md](docs/google-connect.md) — Gmail and Google Calendar connection
- [docs/infrastructure-and-deployment.md](docs/infrastructure-and-deployment.md) — household deployment footprint
- [docs/operations-runbook.md](docs/operations-runbook.md) — day-to-day runtime operations
