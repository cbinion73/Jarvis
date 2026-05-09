# Catalyst Personal in JARVIS

`Catalyst Personal` is the personal-safe adaptation of the work-built Catalyst backend.

It keeps the useful workflow intelligence:

- email triage
- meeting prep
- meeting extraction
- briefing generation
- draft composition
- project planning
- proactive surfacing

It deliberately drops the work-only spine:

- Legacy work database dependencies
- Microsoft Graph assumptions
- Databricks-specific logic
- enterprise identity and connector posture

## Current posture

This layer runs inside JARVIS as a specialist backend rather than as a separate persona.

- JARVIS remains the front door
- Catalyst Personal handles workflow intelligence
- consequential actions still stay under JARVIS approvals
- disconnected connectors are shown honestly as `planned` rather than faked

## Local data

Catalyst Personal stores local workflow artifacts under:

- `/Users/chris/Desktop/CODE/JARVIS/data/catalyst`

That includes:

- captured signals
- email triage runs
- meeting prep runs
- meeting extraction runs
- briefing runs
- draft runs
- project briefs
- implementation plans
- proactive surfacing runs

## Commands

```bash
/Users/chris/Desktop/CODE/JARVIS/.venv/bin/python -m jarvis catalyst-overview
/Users/chris/Desktop/CODE/JARVIS/.venv/bin/python -m jarvis catalyst-signal --actor Chris --source manual --title "Idea" --content "Workflow note"
/Users/chris/Desktop/CODE/JARVIS/.venv/bin/python -m jarvis catalyst-email-triage --actor Chris --sender "name@example.com" --subject "Subject" --body "Email body"
/Users/chris/Desktop/CODE/JARVIS/.venv/bin/python -m jarvis catalyst-meeting-prep --actor Chris --meeting-title "Strategy review" --open-commitment "Follow up on deck" --recent-signal "Vendor needs answer"
/Users/chris/Desktop/CODE/JARVIS/.venv/bin/python -m jarvis catalyst-meeting-extract --actor Chris --transcript "Transcript text"
/Users/chris/Desktop/CODE/JARVIS/.venv/bin/python -m jarvis catalyst-briefing --actor Chris --context "Review current opportunities"
/Users/chris/Desktop/CODE/JARVIS/.venv/bin/python -m jarvis catalyst-draft --actor Chris --intent "Reply to vendor" --context "Need a calm follow-up" --recipient "Vendor" --tone professional
/Users/chris/Desktop/CODE/JARVIS/.venv/bin/python -m jarvis catalyst-project-brief --actor Chris --project-name "Project" --problem "Problem" --desired-outcome "Outcome"
/Users/chris/Desktop/CODE/JARVIS/.venv/bin/python -m jarvis catalyst-implementation-plan --actor Chris --project-name "Project" --brief "Brief text"
/Users/chris/Desktop/CODE/JARVIS/.venv/bin/python -m jarvis catalyst-proactive --actor Chris --horizon today --context "What deserves attention?"
```

## Browser surface

The JARVIS chamber UI now includes a `Catalyst` packet with:

- connector posture
- enabled workflows
- recent signals
- latest workflow runs
- policy summary

## Next good moves

1. wire Gmail as the first personal connector
2. wire Google Calendar as the second personal connector
3. add richer run forms to the Catalyst packet
4. connect Catalyst run activity into the brain mesh active-node lighting
