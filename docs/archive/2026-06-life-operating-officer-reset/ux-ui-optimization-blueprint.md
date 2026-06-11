# JARVIS UX/UI Optimization Blueprint

## Purpose

This document turns the shell roundtable into an implementation-ready refactor package for [jarvis/voice_ui.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/voice_ui.py).

The current shell has grown into a mixed surface that tries to be a:

- launcher
- dashboard
- chat shell
- packet browser
- modal hub
- workspace switcher
- status console

That creates hierarchy failure, scan fatigue, and unnecessary render churn. The target state is:

`quiet shell -> radial routing -> focused scene -> explicit approvals`

## Primary Shell Job

The home shell has one primary job:

- orient Chris fast
- surface what needs attention now
- provide one obvious next move
- route into deeper systems only on demand

The home shell is not the place to permanently display all domains, cards, packets, telemetry, and controls.

## Information Hierarchy

### Layer Model

The shell should be reduced to four layers.

| Layer | Name | Purpose | Visible By Default |
|---|---|---|---|
| 0 | Ambient Shell | center core, background, posture, mode | yes |
| 1 | Radial Router | domain selection and shallow branching | no |
| 2 | Active Scene | one focused workspace at a time | only when selected |
| 3 | Overlay | approval, settings, editor, narrow modal work | only when invoked |

### Persistent Home Objects

Only these objects may persist on the home shell:

- `JARVIS core`
- `one-line system posture`
- `active mode`
- `top priorities`
- `pending approvals`
- `resume context`

Everything else must be:

- scene-only
- drawer-only
- digest-only
- or modal-only

### Attention Tiers

| Tier | Meaning | Allowed Home Weight |
|---|---|---|
| 1 | requires action now | hero or primary row |
| 2 | useful next context | compact support block |
| 3 | ambient awareness | status strip or digest |
| 4 | archival or deep control | hidden until opened |

### Signal Classification Rules

Every source object should be normalized into one of these classes before rendering:

- `priority`
- `approval`
- `resume`
- `ambient`
- `scene-entry`

Home rendering should consume only the derived signal model, not raw runtime objects.

## Home Scene Wireframe

### Idle Home

```text
+-----------------------------------------------------------+
|                                                           |
|                        JARVIS CORE                        |
|                  "2 meetings. 1 approval."                |
|                                                           |
|                    [ Ask / Speak / Open ]                 |
|                                                           |
|  PRIORITIES                                               |
|  1. Meeting prep ready                                    |
|  2. Family conflict tonight                               |
|  3. Chronicle follow-up available                         |
|                                                           |
|  APPROVALS                     RESUME                     |
|  1 pending                     Return to Catalyst Brief   |
|                                                           |
|  STATUS: Local | Connected | House stable | Mode: Morning |
+-----------------------------------------------------------+
```

### Workspace Active

```text
+-----------------------------------------------------------+
| JARVIS CORE (reduced)     Mode: Executive     1 approval  |
|-----------------------------------------------------------|
|                                                           |
|                 ACTIVE SCENE: CATALYST                    |
|                                                           |
|  scene header                                             |
|  scene summary                                            |
|  scene content                                            |
|                                                           |
|-----------------------------------------------------------|
| signal strip                    resume / approval strip   |
+-----------------------------------------------------------+
```

### Rules

- Home must never open as a multi-domain dashboard wall.
- Home must never show more than one hero object.
- Home must never show more than 3 priority signals.
- Home may show at most 1 household interrupt at primary weight.
- Home approvals always outrank ambient telemetry.

## Scene Model

Scenes replace the old pattern of previewing every subsystem on the shell.

### Core Scenes

- `Day`
- `Home`
- `Family`
- `Build`
- `Faith`
- `System`

### Scene Contract

Each scene should own:

- header
- summary
- primary content
- scene-specific actions
- scene-specific support strip

Each scene should not own:

- global radial state
- unrelated domain previews
- duplicated shell chrome

### Scene Boundaries

| Scene | Primary Use | Examples |
|---|---|---|
| `Day` | today, schedule, comms, approvals | agenda, meeting prep, message triage |
| `Home` | house state and practical controls | cameras, rooms, environmental status |
| `Family` | routines and coordination | family calendar, conflicts, logistics |
| `Build` | maker and projects | workshop, fabrication, active builds |
| `Faith` | Chronicle transitions and summaries | study entry, prayer continuity, formation handoff |
| `System` | settings, services, diagnostics | runtime, providers, bridge status |

## Radial Interaction Spec

The radial is a router, not a permanent ontology viewer.

### Root Taxonomy

The stable root ring should be:

- `Day`
- `Home`
- `Family`
- `Build`
- `Faith`
- `System`

### Radial Rules

- maximum 6 root sectors
- maximum 5 children per node before restructuring
- maximum 3 depth levels
- only one active branch at a time
- only one visible path at a time
- leaf nodes must launch a scene or focused destination
- clicking center closes
- clicking outside closes
- selecting a destination closes radial and opens the scene

### Depth Model

| Ring | Meaning | Example |
|---|---|---|
| 1 | domain | `Day` |
| 2 | mode | `Meetings` |
| 3 | destination | `Open Meeting Prep` |

Anything deeper belongs in the target scene, not the radial.

### Normalized Node Shape

```json
{
  "id": "day",
  "label": "Day",
  "kind": "domain",
  "description": "Today, communication, and executive flow.",
  "children": [
    {
      "id": "day-meetings",
      "label": "Meetings",
      "kind": "mode",
      "children": [
        {
          "id": "launch-meeting-prep",
          "label": "Open Meeting Prep",
          "kind": "launch",
          "target": "scene:day?panel=meetings"
        }
      ]
    }
  ]
}
```

### Radial Acceptance Criteria

- no wedge text collisions at normal desktop width
- no recursive fan-out beyond 3 rings
- no sibling branch remains open after switching branch
- no scene renders behind the radial until a launch node is selected

## Action And Approval Grammar

The shell must visually distinguish system intent before action.

### Action States

- `Inform`
- `Suggest`
- `Prepare`
- `Await Approval`
- `Execute`

### Approval Card Requirements

Every approval surface must include:

- source
- requested action
- consequence or scope
- approve
- deny
- inspect

Approval UI must not reuse the same styling as passive summary cards.

## `voice_ui.py` Refactor Plan

The current file is carrying too many responsibilities. The refactor should separate view architecture before visual polish.

### Current Mixed Responsibilities

- shell frame rendering
- packet ontology
- radial routing
- workspace rendering
- modal state
- signal rendering
- layout edit state
- polling-driven updates
- Chronicle and Catalyst workspace framing

### Target Structure

Split responsibility conceptually into:

1. `Shell Frame`
2. `Signal Model`
3. `Radial Router`
4. `Scene Renderer`
5. `Overlay Controller`

This can still begin inside `voice_ui.py`, but the boundaries should be explicit enough to extract later.

### Refactor Stages

#### Stage 1: Home Reset

- reduce home shell to allowed persistent objects
- remove duplicated nav outside the radial core
- stop rendering multi-domain previews on home
- gate conversation rail when not active

#### Stage 2: Scene Extraction

- introduce one `activeScene` state key
- create render functions for:
  - `renderDayScene`
  - `renderHomeScene`
  - `renderFamilyScene`
  - `renderBuildScene`
  - `renderFaithScene`
  - `renderSystemScene`
- unmount inactive scenes

#### Stage 3: Radial Normalization

- replace deep packet-driven recursive behavior with normalized radial node data
- cap depth at 3 rings
- ensure leaf nodes route to scenes

#### Stage 4: Overlay Discipline

- replace modal boolean sprawl with one overlay controller
- allow only one overlay at a time
- prevent simultaneous overlay and radial conflict

#### Stage 5: Performance Trimming

- derive home signal model once per refresh
- normalize radial tree once
- lazy-mount heavy workspace surfaces
- stop refreshing non-visible scenes
- reduce DOM weight for hidden systems by unmounting rather than hiding

### Proposed State Model

```text
shellMode: idle | listening | routing | workspace | approval | alert
activeScene: day | home | family | build | faith | system | null
radialOpen: boolean
radialPath: string[]
activeOverlay: { type, payload } | null
homeSignals:
  - priorities[]
  - approvals[]
  - ambient[]
  - resume
```

### Implementation Anchors In `voice_ui.py`

The current file already exposes obvious anchor points:

- `render_voice_shell(...)`
- `packetTreePresets`
- radial SVG path helpers
- packet modal open and close handlers
- Chronicle workspace iframe surface
- Catalyst workspace iframe surface

These should be used as the initial cut lines for the refactor rather than attempting a total rewrite in one pass.

## First-Pass Deletion List

The first subtraction pass should remove or defer these from the home shell:

- always-visible packet trees
- duplicate navigation surfaces that mirror the radial
- passive chip clouds
- multi-domain card stacks on first load
- decorative status fragments that do not change decisions
- ambient telemetry at primary visual weight
- more than one simultaneously prominent workspace cluster
- chat rail dominance when the user is not in chat mode
- hidden-but-mounted heavy panels that are not active

## First-Pass Keep List

These deserve persistent prominence:

- `JARVIS core`
- `Ask / Speak` entry
- `top priorities`
- `pending approvals`
- `resume where you left off`
- `current mode`
- `small status strip`

## Acceptance Criteria

### UX

- Home feels calm within 3 seconds of load.
- The user can identify the next most likely action immediately.
- Only one major workspace appears at a time.
- The radial feels like a route chooser, not another dashboard.
- Approval actions are unmistakable.

### UI

- The shell opens without a left-side tree menu.
- The home shell shows no more than 3 primary signals.
- Only one hero block is visible on home.
- Passive telemetry is moved to a digest or status strip.

### Performance

- Opening the radial does not trigger a full workspace rerender.
- Switching scenes does not rerender unrelated inactive surfaces.
- Hidden workspaces are unmounted.
- Idle shell DOM is materially smaller than the current shell DOM.

## Recommended Implementation Order

1. Home shell subtraction pass
2. `activeScene` introduction
3. radial depth and taxonomy normalization
4. conversation rail collapse rules
5. overlay controller consolidation
6. scene extraction
7. performance audit and cleanup
8. visual refinement

## Immediate Build Tickets

- `AC-UI-001` Replace dashboard-first home with quiet shell state
- `AC-UI-002` Remove duplicated navigation outside radial core
- `AC-UI-003` Introduce scene-based rendering with `activeScene`
- `AC-UI-004` Cap radial taxonomy at 6 root sectors and 3 rings
- `AC-UI-005` Collapse conversation rail unless active
- `AC-UI-006` Replace modal sprawl with one overlay controller
- `AC-UI-007` Move ambient telemetry into digest or status strip
- `AC-UI-008` Unmount inactive workspaces and stop hidden refresh churn

## Final Direction

Do not start with color polish.

Start by reducing what the shell is allowed to render, then enforce a scene-based interaction model. If we do that first, later visual refinement will amplify clarity instead of decorating clutter.
