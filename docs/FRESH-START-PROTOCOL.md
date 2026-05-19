# JARVIS Fresh Start Protocol

## Purpose

This protocol wipes derived user/runtime state and rebuilds JARVIS from preserved source-of-truth inputs such as:

- household profile config
- Cozi / ICS family calendar settings
- connected account metadata
- preserved Google credentials and tokens

The goal is a true clean baseline, not an ad hoc partial cleanup.

## Command

Preview only:

```bash
python -m jarvis fresh-start
```

Execute the reset and rebuild:

```bash
python -m jarvis fresh-start --execute
```

Execute without creating a backup snapshot:

```bash
python -m jarvis fresh-start --execute --no-backup
```

## What Is Preserved

These are treated as source-of-truth or connector material, not runtime residue:

- `config/google_client_secret.json`
- `data/agents/life_agents.json`
- `data/google/`
- `data/memory/fernet.key`
- `data/settings/accounts.json`
- `data/settings/family_calendar.json`
- `data/trust/`

## What Is Wiped

The protocol removes derived or user-generated runtime state including:

- approvals
- conversation threads
- memory entries, proposals, and profile facts
- family, home, perception, security, wealth, content, tutoring, chronicle, workshop, and catalyst runtime outputs
- assistant core / first light / identity / doctrine / adaptation / location / voice local state
- background agent state
- self-improvement system state
- router sessions/results
- chat uploads
- workshop model forge artifacts
- action audit log
- pending OAuth scratch state

## What Is Rebuilt

After the wipe, the protocol rebuilds the baseline by:

1. Recreating `identity.json` from the household config defaults.
2. Recreating `voice.json` from current environment/provider defaults.
3. Recreating `locations.json` from the household-profile home location.
4. Preserving and verifying the family calendar feed configuration.
5. Preserving and reporting connected account metadata.

## Backup Behavior

By default, execute mode copies removed targets into:

```text
artifacts/fresh_start_backups/<timestamp>/
```

Use `--no-backup` only when you explicitly want destructive cleanup with no rollback snapshot.

## Operational Note

If JARVIS is already running, the safest workflow is:

1. run preview
2. stop or recycle the dashboard process if needed
3. run execute
4. reload the dashboard

This avoids a long-lived process holding stale in-memory state across the reset.
