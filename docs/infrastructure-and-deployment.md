# JARVIS Infrastructure and Deployment

## Purpose

This document closes the gap between a developer-local prototype and a household runtime that can stay up on purpose.

The goal is not enterprise ceremony. The goal is a dependable, local-first home runtime with clear boundaries around uptime, storage, network trust, and family-facing surfaces.

## E14 Outcome

Epic 14 defines:

1. local runtime packaging
2. voice satellite hardware direction
3. wall and family display surfaces
4. NAS and encrypted storage posture
5. UPS and outage resilience
6. segmented network and secure remote access

The related profile is [jarvis_infra_profile.example.json](/Users/chris/Desktop/CODE/JARVIS/household/jarvis_infra_profile.example.json).

## Runtime Packaging

The current recommended host is a small always-on macOS box or an existing always-on workstation that already runs:

- Home Assistant-adjacent tooling
- the local Python runtime
- OpenClaw
- the JARVIS dashboard

Runtime assumptions:

- repo root: `/Users/chris/Desktop/CODE/JARVIS`
- Python entrypoint: `/Users/chris/Desktop/CODE/JARVIS/.venv/bin/python`
- dashboard command: `python -m jarvis serve --host 127.0.0.1 --port 8787`
- voice shell command: `python -m jarvis voice --text-loop`

Packaged service artifacts:

- [start_jarvis_dashboard.sh](/Users/chris/Desktop/CODE/JARVIS/infra/scripts/start_jarvis_dashboard.sh)
- [start_jarvis_voice_shell.sh](/Users/chris/Desktop/CODE/JARVIS/infra/scripts/start_jarvis_voice_shell.sh)
- [com.chris.jarvis.dashboard.plist](/Users/chris/Desktop/CODE/JARVIS/infra/launchd/com.chris.jarvis.dashboard.plist)
- [com.chris.jarvis.voice-shell.plist](/Users/chris/Desktop/CODE/JARVIS/infra/launchd/com.chris.jarvis.voice-shell.plist)
- [install_launchd_services.sh](/Users/chris/Desktop/CODE/JARVIS/infra/scripts/install_launchd_services.sh)

Recommended service posture:

- dashboard service: auto-start, keep alive
- voice shell service: opt-in template, not auto-started by default
- OpenClaw gateway: keep as a separate service boundary
- Home Assistant: separate host/process boundary

## Voice Satellite Plan

Phase 1 posture:

- kitchen satellite for family logistics and morning flow
- office satellite for higher-trust work and meeting prep
- push-to-talk or supervised wake behavior first

Recommended node shape:

- existing Alexa Dots as the practical first whole-home voice edge
- Raspberry Pi 5 or similar small Linux node only where you want a more local/custom room satellite later
- far-field mic array where ambient voice matters beyond Alexa coverage
- small powered speaker, Alexa endpoint, or Apple TV-adjacent output
- wired Ethernet or strong dedicated Wi-Fi

Practical note:

The current codebase already supports a central runtime plus device/room inference. A real satellite rollout should treat satellites as capture and playback edges, not as independent reasoning brains.

## Display Surfaces

Recommended surfaces:

1. kitchen display or Apple TV surface
2. office display
3. living-room Apple TV or shared screen

Behavior:

- kitchen defaults to `Family` display mode
- office defaults to `Full` display mode
- living room uses `Family` mode for Chronicle, family agenda, and shared review

This aligns with the current browser app:

- `Full` mode keeps approvals, explainability, integrations, workshop, and admin review visible
- `Family` mode hides executive/admin-heavy panels

## Storage Plan

Primary live data stays local inside `data/`.

Recommended backup pattern:

- keep active runtime data local on the host SSD
- back up selected folders to an encrypted NAS share
- exclude throwaway runtime/build directories

High-value backup targets:

- `data/chronicle`
- `data/family`
- `data/security`
- `data/tutoring`
- `data/workshop`
- `docs`

Do not prioritize backing up:

- `.venv`
- `__pycache__`

Operational rule:

If family memory, Chronicle, or security history matters, the backup path must be encrypted and recoverable without depending on cloud-only restores.

## UPS and Outage Resilience

Critical loads:

- JARVIS runtime host
- network gateway/router
- switch
- Home Assistant host

Recommended minimum:

- 30 minutes of UPS runtime for the core stack
- graceful shutdown path if projected runtime drops below 10 minutes

Behavior during outage:

- preserve network and control path first
- preserve logging and local state second
- degrade voice and display surfaces before losing the core host

## Network and Remote Access

Recommended segments:

1. `trusted-admin`
2. `iot-home`
3. `guest`

Rules:

- JARVIS runtime host sits in `trusted-admin`
- Home Assistant, Kasa cameras, other cameras, sensors, Alexa endpoints, MyQ, Nest, Kasa lighting, and similar devices sit in `iot-home`
- guest devices never get direct reach into JARVIS or Home Assistant admin surfaces

Remote access posture:

- VPN only
- MFA required
- no direct public internet exposure for JARVIS or Home Assistant

## What E14 Does Not Pretend To Finish

Epic 14 defines the target footprint and provides deployable local artifacts. It does not mean the house is already wired.

Still separate from this epic:

- live Home Assistant credentials and entity maps
- live Bambu adapter
- production-grade wake-word and speaker ID
- finished perception hardware/privacy rollout

Those remain real next steps, but the deployment architecture is no longer undefined.
