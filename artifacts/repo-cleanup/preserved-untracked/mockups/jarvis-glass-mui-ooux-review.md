# JARVIS Glass UX/UI Review

## What the current Glass theme does well

- It has a strong identity and feels distinctly like JARVIS.
- It already exposes the right product areas: Catalyst, Agents, Approvals, Family, Home, Chronicle, Workshop.
- It has a good "ambient command center" emotional tone.

## Where it breaks down

- The UI is scene-first instead of object-first. The orb and floating pills dominate attention more than the actual units of work.
- Related things are split into separate destinations even when they are the same underlying object.
- Status is highly visual but weakly structured. It looks active before it becomes actionable.
- Important actions are hidden inside themed panels instead of being promoted into a stable decision surface.
- The layout feels custom in every area, which makes the product harder to scale and harder to learn.

## OOUX object model to anchor the redesign

Primary objects:

- Decision
- Workflow
- Agent
- Domain
- Briefing packet
- Artifact

Key relationships:

- Decisions unblock or reroute workflows.
- Workflows are owned by agents.
- Domains filter workflows, decisions, and artifacts.
- Briefing packets summarize objects rather than acting like a separate content type.

Key calls to action:

- Approve
- Hold
- Escalate
- Open workflow
- Assign agent
- Inspect trace
- Open related artifact

## MUI X changes that fit JARVIS

- Use a `DataGrid`-style decision queue for approvals, interventions, and high-priority work.
- Use consistent cards, chips, tabs, drawers, and toolbars instead of bespoke layouts in every section.
- Use responsive grid structure so the system stays clear on laptop and smaller desktop widths.
- Use theme tokens and component overrides to keep Glass as a material layer while normalizing interaction patterns.
- Use a single filter model across domains, agents, and workflow states.

## The visual shift

- Keep the Glass mood.
- Reduce ornamental motion.
- Replace floating ambient status with explicit structured summaries.
- Promote decision quality, traceability, and information density.
- Make the interface feel more like an operating console and less like a cinematic splash screen.
