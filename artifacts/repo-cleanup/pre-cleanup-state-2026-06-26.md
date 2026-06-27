# Jarvis Pre-Cleanup State Snapshot

- Repo path: `/Users/chris/Desktop/CODE/JARVIS`
- Branch: `main`
- HEAD: `994d281e0ff7a9a04919f1255d09d2f0c1b8e401`
- HEAD label: `994d281 Ignore generated runtime state artifacts`
- Snapshot date: `2026-06-26`
- User data policy: user data, runtime logs, data stores, and external vaults must not be deleted during cleanup

## Git Status

```text
 M .env.example
M  .gitignore
A  artifacts/jarvis-phase-0a-runtime-health-stabilization.md
M  jarvis/adaptation.py
 M jarvis/apple_api.py
M  jarvis/approvals.py
M  jarvis/assistant_core.py
M  jarvis/audit.py
 M jarvis/config.py
 M jarvis/dining.py
 M jarvis/drift_detection.py
M  jarvis/event_fabric.py
M  jarvis/llm_gateway.py
 M jarvis/longevity_council.py
M  jarvis/main.py
M  jarvis/memory.py
 M jarvis/nav_bridge.py
M  jarvis/persistence.py
 M jarvis/quarterly_review.py
 M jarvis/render_pages.py
 M jarvis/runtime.py
 M jarvis/service.py
A  jarvis/state_log_utils.py
M  jarvis/user_profile.py
 M jarvis/voice_ui.py
 M tests/test_command_center_service_surface.py
 M tests/test_event_log_wiring_phase3.py
 M tests/test_voice_ui_conversation_posture.py
?? _bmad-output/brainstorming/
?? artifacts/jarvis-consolidation-phase-0-snapshot.md
?? artifacts/jarvis-understanding-audit-2026-06-26.md
?? artifacts/mockups/.qlpreview/
?? artifacts/mockups/jarvis-chamber-mission-preview.html
?? artifacts/mockups/jarvis-glass-mui-ooux-proposal.html
?? artifacts/mockups/jarvis-glass-mui-ooux-review.md
?? artifacts/mockups/jarvis-life-officer-mcu-notes.md
?? artifacts/mockups/jarvis-life-officer-mcu-proposal.html
?? docs/JARVIS-ARRIVAL-AND-CONVERSATION-WORKSPACE-DOCTRINE.md
?? docs/JARVIS-GLASS-THEME-UX-SPECIFICATION.md
?? docs/JARVIS-OBJECT-POSTURE-REPRESENTATION-DOCTRINE.md
?? docs/JARVIS-REJOIN-OPERATION-IMPLEMENTATION-PLAN.md
?? docs/JARVIS-REJOIN-OPERATION-MILESTONE.md
?? tests/test_runtime_mission_followup.py
```

## Modified Files

- `.env.example`
- `.gitignore`
- `jarvis/adaptation.py`
- `jarvis/apple_api.py`
- `jarvis/approvals.py`
- `jarvis/assistant_core.py`
- `jarvis/audit.py`
- `jarvis/config.py`
- `jarvis/dining.py`
- `jarvis/drift_detection.py`
- `jarvis/event_fabric.py`
- `jarvis/llm_gateway.py`
- `jarvis/longevity_council.py`
- `jarvis/main.py`
- `jarvis/memory.py`
- `jarvis/nav_bridge.py`
- `jarvis/persistence.py`
- `jarvis/quarterly_review.py`
- `jarvis/render_pages.py`
- `jarvis/runtime.py`
- `jarvis/service.py`
- `jarvis/user_profile.py`
- `jarvis/voice_ui.py`
- `tests/test_command_center_service_surface.py`
- `tests/test_event_log_wiring_phase3.py`
- `tests/test_voice_ui_conversation_posture.py`

## Untracked Files

- `_bmad-output/brainstorming/brainstorming-session-2026-06-11-15-28-50.md`
- `artifacts/jarvis-consolidation-phase-0-snapshot.md`
- `artifacts/jarvis-understanding-audit-2026-06-26.md`
- `artifacts/mockups/.qlpreview/jarvis-chamber-mission-preview.html.png`
- `artifacts/mockups/.qlpreview/jarvis-glass-mui-ooux-proposal.html.png`
- `artifacts/mockups/.qlpreview/jarvis-life-officer-mcu-proposal.html.png`
- `artifacts/mockups/jarvis-chamber-mission-preview.html`
- `artifacts/mockups/jarvis-glass-mui-ooux-proposal.html`
- `artifacts/mockups/jarvis-glass-mui-ooux-review.md`
- `artifacts/mockups/jarvis-life-officer-mcu-notes.md`
- `artifacts/mockups/jarvis-life-officer-mcu-proposal.html`
- `docs/JARVIS-ARRIVAL-AND-CONVERSATION-WORKSPACE-DOCTRINE.md`
- `docs/JARVIS-GLASS-THEME-UX-SPECIFICATION.md`
- `docs/JARVIS-OBJECT-POSTURE-REPRESENTATION-DOCTRINE.md`
- `docs/JARVIS-REJOIN-OPERATION-IMPLEMENTATION-PLAN.md`
- `docs/JARVIS-REJOIN-OPERATION-MILESTONE.md`
- `tests/test_runtime_mission_followup.py`

## Known Giant Logs

```text
data/settings/assistant_core_log.jsonl         13G
data/settings/assistant_core_state_log.jsonl   13G
data/logs/llm_usage_state_log.jsonl            47M
data/agents/event_bus_state_log.jsonl          41M
```

## Known Runtime Data Paths

- `data/settings/`
- `data/logs/`
- `data/agents/`
- `data/system/`
- `data/state/`
- `data/google/`
- `data/openviking/`
- `data/microsoft_graph/`
- `~/.jarvis/approvals/`
- `/Volumes/Monday/JARVIS`
- `/Volumes/Monday/Obsidian`

## Notes

- Staged Phase 0A runtime-health work was already present at capture time and is also preserved separately in `artifacts/repo-cleanup/pre-cleanup-index.patch`.
- Unstaged preexisting dirty work is preserved in `artifacts/repo-cleanup/pre-cleanup-working-tree.patch`.
