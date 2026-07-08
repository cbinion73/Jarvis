---
workflowType: "manual-bmad-prd-bootstrap"
project: "JARVIS"
sourceDocuments:
  - "/Users/chris/Desktop/apex_build_guide_v1.pdf"
  - "User narrative and PRD prompt from 2026-05-05"
---

# Product Requirements Document - JARVIS

**Author:** Chris + Codex
**Date:** 2026-05-05
**Status:** Draft v1

## Executive Summary

JARVIS is an always-on orchestrator for the Chris/Rebekah household, composed
of specialized agents working continuously on the household's behalf.

It should function as a private household operating system that blends home
control, family logistics, executive assistance, creative making support, faith
rhythms, child-safe tutoring, and security-aware automation.

When a household member engages directly, the relevant agents should focus into
the foreground.

When no one is engaging directly, those agents should continue bounded work in
the background on monitoring, preparation, delegated tasks, continuity, and
stewardship.

The product is not "a smart speaker with a British voice." The product is an orchestration layer that understands the people, rooms, projects, permissions, rhythms, and risks of a real household.

## Product Vision

Build a JARVIS-inspired household intelligence system that is:

- proactive without being invasive
- personality-rich without becoming manipulative
- local-first for sensitive household state
- permission-governed for any consequential action
- family-specific instead of generic
- formation-oriented for children and faith workflows
- always-on rather than session-bound
- orchestrator-first rather than interface-first

## North Star

JARVIS helps the family live with less friction, better judgment, stronger stewardship, and more creative capacity.

Success is measured by whether the household becomes calmer, safer, more organized, more spiritually grounded, and less reactive.

Operationally, success also means the household experiences JARVIS as a
continuously running staff of specialized agents rather than a tool that only
exists when opened.

## Primary Users

### Chris

- Executive briefings
- Meeting prep and follow-up
- Manuscript editing
- Research synthesis
- Workshop/CAD/3D printing support
- Chronicle ideation
- Faith reflection

### Rebekah

- Schedule coordination
- Grocery and meal planning
- Parent communication drafts
- Troop/event logistics
- Household reminders with low tech fuss

### Caleb

- Homework coaching
- Morning readiness prompts
- Accountability without shaming
- Device and study boundaries

### Anna

- Project organization
- Presentation practice
- Reminder and charging flows
- Creative support without replacing her voice

## Core Principles

1. Local first, cloud when worth it
2. Personality with boundaries
3. Explicit approval for consequential actions
4. Separate profiles, memory scopes, and permissions
5. Formation over convenience

## Scope

### In Scope

- Whole-home voice interaction
- Wake word and room-aware commands
- Home Assistant-based local home control
- Family briefings and logistics
- Executive work support
- Workshop/maker copilot workflows
- Faith and devotional routines
- Child-safe tutoring guardrails
- Security monitoring and anomaly alerts
- Memory-aware project assistance
- Approval-governed agent actions

### Out of Scope for MVP

- Autonomous robots
- Autonomous vehicle control
- Unsupervised child messaging
- Unsupervised purchases or financial actions
- Medical diagnosis
- Cloud archival of raw household camera feeds
- Unsafe machinery automation

## Product Modules

### 1. JARVIS Orchestrator

- Intent routing
- User/room context
- Memory retrieval
- Tool selection
- Approval gating
- Action logging
- Result summarization

### 2. House Nervous System

- Lights, climate, locks, garage, cameras, leak sensors, freezer monitoring
- Presence detection and house modes
- Home Assistant as the actuator boundary

### 3. Perception Mesh

- Far-field microphones
- Room and workshop cameras
- Door/garage/package cameras
- Environmental sensors
- Wearables and phone location when explicitly allowed

### 4. Voice and Persona Layer

- Formal, witty, concise, dryly humorous associate persona
- British-inspired voice with quiet mode
- Interruptible voice output
- Local fallback voice for critical alerts

### 5. Memory Core

- Household memory
- Personal memory
- Project memory
- Safety memory
- Short-lived session memory
- External cited knowledge

### 6. Family Logistics

- Daily family briefing
- Calendar conflict detection
- Parent message drafting
- Device charging and backpack reminders
- Meal/grocery support
- Vehicle coordination

### 7. Executive Work

- Meeting prep
- Research summaries with citations
- Follow-up extraction
- Confidentiality filtering
- Manuscript editing and jargon detection

### 8. Workshop / Maker

- Printer monitoring
- Part inspection
- CAD idea support
- Material suggestions
- Safety warnings
- Vendor prep with approval gates

### 9. Faith and Formation

- Devotional pauses
- Scripture/prayer framing
- Chronicle integration
- Reflection and prayer themes over time

### 10. Child Tutor

- Quiz coaching
- Socratic explanation support
- Presentation rehearsal
- Parent-visible summaries
- No deceptive assignment completion

### 11. Security and Safety

- Door and garage state
- Unusual motion
- Leak/smoke/freezer anomalies
- Workshop safety state
- Weather alerts
- Overnight watch mode

## Functional Requirements

### Voice

- `V-001` Respond to `JARVIS` wake word.
- `V-002` Support room-aware commands.
- `V-003` Allow interruption while speaking.
- `V-004` Identify speaker where possible.
- `V-005` Support quiet mode.
- `V-006` Maintain the household associate persona.
- `V-007` Support offline fallback alerts.

### Home Control

- `H-001` Control lights by room, scene, time, and intent.
- `H-002` Control thermostat and home modes.
- `H-003` Monitor and protect lock/door state.
- `H-004` Monitor garage state and safe closing checks.
- `H-005` Trigger Dawn, Family Morning, Work, Dinner, Goodnight, and Watchtower modes.
- `H-006` Keep core automations available during internet outage where hardware allows.

### Family Logistics

- `F-001` Generate daily family briefings.
- `F-002` Detect schedule conflicts and suggest calmer alternatives.
- `F-003` Draft family and parent communications for approval.
- `F-004` Track school reminders and readiness loops.
- `F-005` Support meal planning and grocery grouping.
- `F-006` Provide departure checklists and reminders.
- `F-007` Support vehicle usage coordination.

### Work and Writing

- `W-001` Summarize daily work agenda.
- `W-002` Build meeting prep briefs.
- `W-003` Track commitments from transcripts and notes.
- `W-004` Edit manuscripts against defined voice rules.
- `W-005` Apply confidentiality filters.
- `W-006` Generate cited research summaries.
- `W-007` Maintain project-specific memory boundaries.

### Workshop

- `M-001` Monitor printer jobs and status.
- `M-002` Support part inspection from images or scans.
- `M-003` Prepare rough CAD/print directions for approval.
- `M-004` Warn on workshop safety state.
- `M-005` Require explicit approval before vendor uploads or purchases.

### Faith and Chronicle

- `C-001` Provide Scripture-grounded devotional prompts.
- `C-002` Distinguish Scripture from interpretation.
- `C-003` Support Chronicle-facing reflection capture.
- `C-004` Respect theological profile and uncertainty.

### Child Safety and Tutoring

- `K-001` Coach without completing assignments dishonestly.
- `K-002` Maintain child-specific permissions.
- `K-003` Prevent access to adult work data.
- `K-004` Support device dock and study boundary routines.
- `K-005` Block unsafe or inappropriate content paths.

## Non-Functional Requirements

- `NFR-001` Core home actions should feel conversational.
- `NFR-002` Sensitive household state should remain local by default.
- `NFR-003` Consequential actions must be explainable and auditable.
- `NFR-004` Manual controls must remain available during AI failure.
- `NFR-005` Physical-world actions must require stricter approvals than advisory actions.
- `NFR-006` The system must be modular enough to add rooms, devices, and specialist agents without major rewrites.
- `NFR-007` The experience must feel helpful rather than creepy.

## Permission Model

| Class | Meaning | Example | Approval |
| --- | --- | --- | --- |
| 0 | Observe | read sensor state | none |
| 1 | Suggest | recommend route, meal, or reminder timing | none |
| 2 | Prepare | draft a message or prepare a print file | none, but no send/submit |
| 3 | Execute low risk | lights, scenes, playlists | normal voice confirmation |
| 4 | Execute medium risk | send text, move shared event | explicit confirmation |
| 5 | Execute high risk | remote unlock, submit order, post online | confirmation plus second factor |
| 6 | Restricted | money movement, unsafe machinery | blocked/manual only |

## MVP Roadmap

### Phase 1: JARVIS Wakes Up

- Voice shell
- Persona layer
- Home Assistant integration seam
- Morning briefing
- Family dashboard
- Action logging

### Phase 2: JARVIS Remembers

- User profiles
- Household/project memory
- Manuscript and Scouts modes
- Grocery and logistics routines
- Permission engine v1

### Phase 3: JARVIS Sees

- Workshop camera workflows
- Package detection
- Visual safety checks
- Part inspection

### Phase 4: JARVIS Acts

- Approved outbound messages
- Shared calendar changes
- Print preparation
- Research monitoring

### Phase 5: The Stark House

- Advanced room-wide voice
- AR workshop overlays
- Predictive maintenance
- Secure remote access
- Proactive family orchestration

## Top Risks

- Feels creepy instead of helpful
- Notification overload
- Over-automation of parenting/formation
- Cloud leakage of sensitive data
- Unsafe external actions
- Child misuse or overreliance
- Security gaps across smart-home and agent layers

## Product Position

The weak version is a talking smart speaker.

The strong version is a private household intelligence system with a JARVIS personality, local trust boundaries, and real judgment about when to act, when to prepare, and when to stay quiet.
