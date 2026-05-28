"""
catalyst_db.py — Work Intelligence Database Layer
===================================================
PostgreSQL schema and access layer for JARVIS Work Intelligence (formerly Catalyst).

Database:  postgresql://chris@127.0.0.1:5432/jarvis_catalyst
Pattern:   psycopg2 with RealDictCursor, synchronous, thread-pool safe.
           Mirrors the pattern established in home_projects.py.

Schema source: Ported from Catalyst Oracle 19c/23ai migrations (10 migration files).
All 23 tables are defined here. Call CatalystDB.ensure_schema() once at startup
to create tables if they don't exist.

Tables (in dependency order):
  1.  users                        — local user registry (replaces Oracle pilot_users)
  2.  user_sessions                — session tokens (replaces pilot_sessions)
  3.  user_preferences             — autonomy levels per user
  4.  raw_signals                  — immutable source evidence
  5.  raw_emails                   — email metadata linked to signals
  6.  projects                     — active work items
  7.  project_a3s                  — A3 lean planning docs
  8.  project_memory               — learned routing aliases + exemplars
  9.  routing_feedback             — signal routing corrections
  10. milestones                   — project milestones
  11. workstreams                  — workstream lanes inside milestones
  12. tasks                        — project-derived + ad-hoc tasks
  13. commitments                  — extracted commitments from signals
  14. decisions                    — recorded decisions with reasoning
  15. contacts                     — people mentioned / interacted with
  16. contact_sensitivity          — tier classification (1=exec, 2=peer, 3=general)
  17. briefing_items               — scored items for morning/evening briefing
  18. agent_actions                — individual agent action log
  19. agent_action_signals         — signals that contributed to an action
  20. agent_workflow_runs          — full workflow execution runs
  21. agent_workflow_steps         — individual steps inside a run
  22. preference_rules             — learned behavioral preference rules
  23. initiatives                  — AI value tracking initiatives
  24. value_use_cases              — individual value captures per initiative
  25. project_impact_assessments   — financial impact analysis per project
  26. project_impact_hypotheses    — FCF-tree hypotheses inside an assessment
  27. project_baseline_requests    — Databricks metric baseline requests
  28. project_baseline_results     — resolved baseline values
  29. project_value_attributions   — final value attributions from baselines
  30. project_activity_log         — meeting / activity journal entries
  31. system_logs                  — workflow run telemetry
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

log = logging.getLogger("jarvis.catalyst_db")

# ---------------------------------------------------------------------------
# psycopg2 import guard (mirrors ghostwritr_bridge.py pattern)
# ---------------------------------------------------------------------------
try:
    import psycopg2
    import psycopg2.extras
    _PG_AVAILABLE = True
except ImportError:
    _PG_AVAILABLE = False
    log.warning("psycopg2 not installed — CatalystDB unavailable")

# ---------------------------------------------------------------------------
# Env / defaults
# ---------------------------------------------------------------------------
_DEFAULT_URL = os.environ.get(
    "CATALYST_DB_URL",
    "postgresql://chris@127.0.0.1:5432/jarvis_catalyst",
)

# ---------------------------------------------------------------------------
# DDL — all tables
# ---------------------------------------------------------------------------
_SCHEMA_SQL = """
-- ── Users ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(320) UNIQUE NOT NULL,
    display_name    VARCHAR(255),
    role            VARCHAR(50) DEFAULT 'owner',
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_sessions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_token_hash  VARCHAR(128) NOT NULL,
    expires_at          TIMESTAMPTZ NOT NULL,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    last_seen_at        TIMESTAMPTZ DEFAULT NOW(),
    user_agent          VARCHAR(500),
    remote_addr         VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS idx_sessions_user ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON user_sessions(session_token_hash);

-- ── User Preferences ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_preferences (
    user_id                     VARCHAR(255) PRIMARY KEY,
    autonomy_level              SMALLINT DEFAULT 0 CHECK (autonomy_level BETWEEN 0 AND 100),
    threshold_suggest_only      SMALLINT DEFAULT 20,
    threshold_draft_for_review  SMALLINT DEFAULT 50,
    threshold_act_notify_after  SMALLINT DEFAULT 80,
    threshold_full_auto         SMALLINT DEFAULT 100,
    correct_actions_streak      INTEGER DEFAULT 0,
    total_actions_approved      INTEGER DEFAULT 0,
    total_actions_overridden    INTEGER DEFAULT 0,
    last_override_at            TIMESTAMPTZ,
    autonomy_floor              SMALLINT DEFAULT 0,
    updated_at                  TIMESTAMPTZ DEFAULT NOW()
);

-- ── Raw Signals ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS raw_signals (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             VARCHAR(255) NOT NULL,
    signal_type         VARCHAR(50) NOT NULL
                        CHECK (signal_type IN (
                            'calendar_event','email','teams_message',
                            'meeting_transcript','quick_note','notebook_photo',
                            'slack_message','document','web_clip','news',
                            'agent_activity','agent_alert','agent_commitment',
                            'agent_completion','agent_decision','agent_observation',
                            'agent_route','agent_work'
                        )),
    signal_criticality  VARCHAR(20) DEFAULT 'STANDARD'
                        CHECK (signal_criticality IN ('CRITICAL','STANDARD','LOW')),
    content             TEXT NOT NULL,
    external_id         VARCHAR(500),
    source_metadata     JSONB DEFAULT '{}',
    classification      VARCHAR(50)
                        CHECK (classification IN (
                            'new_initiative','related_to_existing','ambiguous',NULL
                        )),
    related_project_id  UUID,
    classified_at       TIMESTAMPTZ,
    embedding           JSONB,          -- 1536-dim float array stored as JSONB
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_signals_user ON raw_signals(user_id);
CREATE INDEX IF NOT EXISTS idx_signals_type ON raw_signals(signal_type);
CREATE INDEX IF NOT EXISTS idx_signals_created ON raw_signals(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_signals_project ON raw_signals(related_project_id)
    WHERE related_project_id IS NOT NULL;

-- ── Raw Emails ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS raw_emails (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         VARCHAR(255) NOT NULL,
    signal_id       UUID REFERENCES raw_signals(id) ON DELETE SET NULL,
    message_id      VARCHAR(500) UNIQUE NOT NULL,
    subject         VARCHAR(1000),
    from_address    VARCHAR(500),
    received_at     TIMESTAMPTZ,
    is_read         BOOLEAN DEFAULT FALSE,
    importance      VARCHAR(20),
    conversation_id VARCHAR(500),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_emails_user ON raw_emails(user_id);
CREATE INDEX IF NOT EXISTS idx_emails_received ON raw_emails(received_at DESC);
CREATE INDEX IF NOT EXISTS idx_emails_conversation ON raw_emails(conversation_id)
    WHERE conversation_id IS NOT NULL;

-- ── Projects ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS projects (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             VARCHAR(255) NOT NULL,
    name                VARCHAR(500) NOT NULL,
    problem_statement   TEXT,
    status              VARCHAR(20) DEFAULT 'active'
                        CHECK (status IN ('active','at_risk','stalled','complete','archived')),
    source_signal_id    UUID REFERENCES raw_signals(id) ON DELETE SET NULL,
    embedding           JSONB,
    last_activity_at    TIMESTAMPTZ DEFAULT NOW(),
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_projects_user ON projects(user_id);
CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);

-- ── Project A3s ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS project_a3s (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                 VARCHAR(255) NOT NULL,
    project_id              UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    project_leader          VARCHAR(500),
    business_unit_impacted  VARCHAR(500),
    review_due_date         TIMESTAMPTZ,
    direct_impact_amount    NUMERIC(18,2),
    start_date              TIMESTAMPTZ,
    scope                   TEXT,
    objectives              TEXT,
    project_metrics         TEXT,
    current_results         TEXT,
    team                    TEXT,
    review_plan             TEXT,
    executive_summary       TEXT,
    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (user_id, project_id)
);

-- ── Project Memory ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS project_memory (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             VARCHAR(255) NOT NULL,
    project_id          UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    memory_type         VARCHAR(30) NOT NULL
                        CHECK (memory_type IN ('alias','exemplar','expected_outcome','negative')),
    memory_text         TEXT NOT NULL,
    confidence_score    NUMERIC(4,3) DEFAULT 0.700,
    source_signal_id    UUID REFERENCES raw_signals(id) ON DELETE SET NULL,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pmem_project ON project_memory(project_id);
CREATE INDEX IF NOT EXISTS idx_pmem_user ON project_memory(user_id);

-- ── Routing Feedback ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS routing_feedback (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                 VARCHAR(255) NOT NULL,
    signal_id               UUID REFERENCES raw_signals(id) ON DELETE CASCADE,
    selected_project_id     UUID REFERENCES projects(id) ON DELETE SET NULL,
    rejected_project_id     UUID REFERENCES projects(id) ON DELETE SET NULL,
    classification          VARCHAR(50),
    feedback_type           VARCHAR(30)
                            CHECK (feedback_type IN (
                                'positive_project_link','negative_project_link',
                                'new_initiative','override'
                            )),
    source_signal_type      VARCHAR(50),
    source_excerpt          TEXT,
    reason                  TEXT,
    created_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rfeedback_user ON routing_feedback(user_id);
CREATE INDEX IF NOT EXISTS idx_rfeedback_signal ON routing_feedback(signal_id);

-- ── Milestones ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS milestones (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id         VARCHAR(255) NOT NULL,
    name            VARCHAR(500) NOT NULL,
    due_date        TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_milestones_project ON milestones(project_id);

-- ── Workstreams ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS workstreams (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    milestone_id    UUID REFERENCES milestones(id) ON DELETE SET NULL,
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id         VARCHAR(255) NOT NULL,
    name            VARCHAR(500) NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_workstreams_project ON workstreams(project_id);

-- ── Tasks ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS catalyst_tasks (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             VARCHAR(255) NOT NULL,
    project_id          UUID REFERENCES projects(id) ON DELETE SET NULL,
    workstream_id       UUID REFERENCES workstreams(id) ON DELETE SET NULL,
    source_signal_id    UUID REFERENCES raw_signals(id) ON DELETE SET NULL,
    title               VARCHAR(1000) NOT NULL,
    description         TEXT,
    task_type           VARCHAR(30) DEFAULT 'project_derived'
                        CHECK (task_type IN (
                            'project_derived','ad_hoc','routine',
                            'agent_task','agent_approved'
                        )),
    status              VARCHAR(20) DEFAULT 'open'
                        CHECK (status IN ('open','in_progress','complete','blocked')),
    priority            VARCHAR(10) DEFAULT 'medium'
                        CHECK (priority IN ('high','medium','low')),
    assigned_to         VARCHAR(500),
    due_date            TIMESTAMPTZ,
    completed_at        TIMESTAMPTZ,
    recurrence_rule     VARCHAR(200),
    streak_count        INTEGER DEFAULT 0,
    blocked_reason      TEXT,
    next_step           TEXT,
    scheduled_for       TIMESTAMPTZ,
    archived_at         TIMESTAMPTZ,
    last_touched_at     TIMESTAMPTZ DEFAULT NOW(),
    version_num         INTEGER DEFAULT 1,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ctasks_user ON catalyst_tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_ctasks_project ON catalyst_tasks(project_id)
    WHERE project_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_ctasks_status ON catalyst_tasks(status);
CREATE INDEX IF NOT EXISTS idx_ctasks_due ON catalyst_tasks(due_date)
    WHERE due_date IS NOT NULL AND archived_at IS NULL;

-- ── Commitments ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS commitments (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             VARCHAR(255) NOT NULL,
    source_signal_id    UUID NOT NULL REFERENCES raw_signals(id) ON DELETE CASCADE,
    description         TEXT,
    responsible_party   VARCHAR(500),
    due_date            TIMESTAMPTZ,
    status              VARCHAR(20) DEFAULT 'open'
                        CHECK (status IN ('open','completed','overdue','dismissed')),
    confidence_score    NUMERIC(4,3) DEFAULT 0.700,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_commitments_user ON commitments(user_id);
CREATE INDEX IF NOT EXISTS idx_commitments_status ON commitments(status);

-- ── Decisions ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS decisions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             VARCHAR(255) NOT NULL,
    source_signal_id    UUID NOT NULL REFERENCES raw_signals(id) ON DELETE CASCADE,
    description         TEXT,
    reasoning           TEXT,
    made_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    confidence_score    NUMERIC(4,3) DEFAULT 0.700,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_decisions_user ON decisions(user_id);
CREATE INDEX IF NOT EXISTS idx_decisions_made ON decisions(made_at DESC);

-- ── Contacts ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS contacts (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             VARCHAR(255) NOT NULL,
    display_name        VARCHAR(500),
    email_address       VARCHAR(500),
    job_title           VARCHAR(500),
    company_name        VARCHAR(500),
    interaction_count   INTEGER DEFAULT 0,
    last_interaction_at TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (user_id, email_address)
);

CREATE INDEX IF NOT EXISTS idx_contacts_user ON contacts(user_id);
CREATE INDEX IF NOT EXISTS idx_contacts_email ON contacts(email_address)
    WHERE email_address IS NOT NULL;

-- ── Contact Sensitivity ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS contact_sensitivity (
    contact_id      VARCHAR(255) PRIMARY KEY,
    tier            SMALLINT NOT NULL CHECK (tier IN (1, 2, 3)),
    tier_source     VARCHAR(20) DEFAULT 'default'
                    CHECK (tier_source IN ('explicit','inferred','default')),
    tier_set_at     TIMESTAMPTZ DEFAULT NOW()
);

-- ── Briefing Items ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS briefing_items (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             VARCHAR(255) NOT NULL,
    content             TEXT,
    source_type         VARCHAR(50),
    source_signal_id    UUID REFERENCES raw_signals(id) ON DELETE SET NULL,
    confidence_score    NUMERIC(4,3),
    reasoning_chain     TEXT,
    briefing_date       VARCHAR(10) NOT NULL,   -- YYYY-MM-DD
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_briefing_user_date ON briefing_items(user_id, briefing_date DESC);

-- ── Agent Actions ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS agent_actions (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                 VARCHAR(255) NOT NULL,
    agent_name              VARCHAR(100),
    workflow_name           VARCHAR(100),
    action_type             VARCHAR(100),
    status                  VARCHAR(20) DEFAULT 'PENDING'
                            CHECK (status IN (
                                'PENDING','EXECUTING','COMPLETED','FAILED','ROLLED_BACK'
                            )),
    reasoning_chain         TEXT,
    confidence_at_exec      NUMERIC(4,3),
    autonomy_level_at_exec  SMALLINT,
    rule_ids_applied        JSONB DEFAULT '[]',
    source_signal_id        UUID REFERENCES raw_signals(id) ON DELETE SET NULL,
    target_entity_type      VARCHAR(50),
    target_entity_id        UUID,
    created_at              TIMESTAMPTZ DEFAULT NOW(),
    completed_at            TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_actions_user ON agent_actions(user_id);
CREATE INDEX IF NOT EXISTS idx_actions_status ON agent_actions(status);
CREATE INDEX IF NOT EXISTS idx_actions_workflow ON agent_actions(workflow_name);

-- ── Agent Action Signals ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS agent_action_signals (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    action_id       UUID NOT NULL REFERENCES agent_actions(id) ON DELETE CASCADE,
    signal_type     VARCHAR(50),
    signal_weight   NUMERIC(4,3),
    signal_payload  JSONB DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_aas_action ON agent_action_signals(action_id);

-- ── Agent Workflow Runs ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS agent_workflow_runs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             VARCHAR(255) NOT NULL,
    workflow_name       VARCHAR(100) NOT NULL,
    source_signal_id    UUID REFERENCES raw_signals(id) ON DELETE SET NULL,
    signal_kind         VARCHAR(50),
    status              VARCHAR(20) DEFAULT 'PENDING'
                        CHECK (status IN (
                            'PENDING','EXECUTING','COMPLETED','FAILED','NEEDS_REVIEW'
                        )),
    overall_confidence  NUMERIC(4,3),
    summary             TEXT,
    target_entity_type  VARCHAR(50),
    target_entity_id    UUID,
    started_at          TIMESTAMPTZ,
    completed_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_runs_user ON agent_workflow_runs(user_id);
CREATE INDEX IF NOT EXISTS idx_runs_workflow ON agent_workflow_runs(workflow_name);
CREATE INDEX IF NOT EXISTS idx_runs_status ON agent_workflow_runs(status);
CREATE INDEX IF NOT EXISTS idx_runs_created ON agent_workflow_runs(created_at DESC);

-- ── Agent Workflow Steps ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS agent_workflow_steps (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id          UUID NOT NULL REFERENCES agent_workflow_runs(id) ON DELETE CASCADE,
    user_id         VARCHAR(255) NOT NULL,
    agent_name      VARCHAR(100),
    step_name       VARCHAR(200),
    status          VARCHAR(20) DEFAULT 'PENDING'
                    CHECK (status IN (
                        'PENDING','EXECUTING','COMPLETED','FAILED','NEEDS_REVIEW','SKIPPED'
                    )),
    input_summary   TEXT,
    output_summary  TEXT,
    confidence_score NUMERIC(4,3),
    provenance      JSONB DEFAULT '{}',
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_steps_run ON agent_workflow_steps(run_id);
CREATE INDEX IF NOT EXISTS idx_steps_agent ON agent_workflow_steps(agent_name);

-- ── Preference Rules ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS preference_rules (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             VARCHAR(255) NOT NULL,
    rule_text           TEXT NOT NULL,
    validation_source   VARCHAR(20) DEFAULT 'inferred'
                        CHECK (validation_source IN ('explicit','implicit','inferred')),
    confidence_score    NUMERIC(4,3) DEFAULT 0.500,
    is_stale            BOOLEAN DEFAULT FALSE,
    last_validated_at   TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_prules_user ON preference_rules(user_id);
CREATE INDEX IF NOT EXISTS idx_prules_stale ON preference_rules(is_stale);

-- ── Initiatives ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS initiatives (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                 VARCHAR(255) NOT NULL,
    name                    VARCHAR(500) NOT NULL,
    description             TEXT,
    linked_project_id       UUID REFERENCES projects(id) ON DELETE SET NULL,
    total_projected_value   NUMERIC(15,2) DEFAULT 0,
    total_committed_value   NUMERIC(15,2) DEFAULT 0,
    total_realized_value    NUMERIC(15,2) DEFAULT 0,
    use_case_count          INTEGER DEFAULT 0,
    business_unit           VARCHAR(500),
    owner_name              VARCHAR(500),
    primary_users           JSONB DEFAULT '[]',
    usage_summary           TEXT,
    why_this_matters        TEXT,
    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_initiatives_user ON initiatives(user_id);
CREATE INDEX IF NOT EXISTS idx_initiatives_project ON initiatives(linked_project_id)
    WHERE linked_project_id IS NOT NULL;

-- ── Value Use Cases ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS value_use_cases (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    initiative_id   UUID NOT NULL REFERENCES initiatives(id) ON DELETE CASCADE,
    user_id         VARCHAR(255) NOT NULL,
    value_type      VARCHAR(50)
                    CHECK (value_type IN (
                        'Revenue','Savings','Efficiency','Risk Avoidance'
                    )),
    amount          NUMERIC(15,2),
    confidence      VARCHAR(20)
                    CHECK (confidence IN ('Projected','Committed','Realized')),
    stakeholder     VARCHAR(500),
    evidence_links  JSONB DEFAULT '[]',
    description     TEXT,
    used_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_vuc_initiative ON value_use_cases(initiative_id);
CREATE INDEX IF NOT EXISTS idx_vuc_user ON value_use_cases(user_id);

-- ── Project Impact Assessments ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS project_impact_assessments (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             VARCHAR(255) NOT NULL,
    project_id          UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    analyst_name        VARCHAR(100) DEFAULT 'financial-impact-analyst',
    analyst_summary     TEXT,
    overall_confidence  NUMERIC(5,4),
    assessment_json     JSONB NOT NULL DEFAULT '{}',
    approval_status     VARCHAR(30) DEFAULT 'draft'
                        CHECK (approval_status IN (
                            'draft','needs_baseline','ready_for_review','approved','rejected'
                        )),
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_assessments_project ON project_impact_assessments(project_id);

-- ── Project Impact Hypotheses ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS project_impact_hypotheses (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_id               UUID NOT NULL
                                REFERENCES project_impact_assessments(id) ON DELETE CASCADE,
    user_id                     VARCHAR(255) NOT NULL,
    project_id                  UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    title                       VARCHAR(500),
    impact_mode                 VARCHAR(20) CHECK (impact_mode IN ('direct','enterprise')),
    fcf_node                    VARCHAR(80),
    value_type                  VARCHAR(80),
    hypothesis                  TEXT,
    business_mechanism          TEXT,
    formula                     TEXT,
    baseline_metric_needed      VARCHAR(500),
    baseline_source             VARCHAR(50),
    estimated_change_percent    NUMERIC(10,4),
    direct_amount_usd           NUMERIC(15,2),
    confidence                  NUMERIC(5,4),
    created_at                  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_hypotheses_assessment ON project_impact_hypotheses(assessment_id);

-- ── Project Baseline Requests ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS project_baseline_requests (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_id               UUID NOT NULL
                                REFERENCES project_impact_assessments(id) ON DELETE CASCADE,
    user_id                     VARCHAR(255) NOT NULL,
    project_id                  UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    metric                      VARCHAR(500),
    business_unit               VARCHAR(200),
    product                     VARCHAR(200),
    region                      VARCHAR(200),
    time_period                 VARCHAR(200),
    databricks_question         TEXT,
    needed_for_impact_title     VARCHAR(500),
    status                      VARCHAR(20) DEFAULT 'pending'
                                CHECK (status IN ('pending','queried','resolved','blocked')),
    created_at                  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_breqs_assessment ON project_baseline_requests(assessment_id);

-- ── Project Baseline Results ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS project_baseline_results (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id          UUID NOT NULL
                        REFERENCES project_baseline_requests(id) ON DELETE CASCADE,
    assessment_id       UUID NOT NULL
                        REFERENCES project_impact_assessments(id) ON DELETE CASCADE,
    user_id             VARCHAR(255) NOT NULL,
    project_id          UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    metric              VARCHAR(500),
    baseline_value      NUMERIC(18,4),
    baseline_unit       VARCHAR(100),
    source_system       VARCHAR(100) DEFAULT 'manual',
    source_catalog      VARCHAR(200),
    source_schema       VARCHAR(200),
    source_table        VARCHAR(200),
    query_text          TEXT,
    provenance_json     JSONB DEFAULT '{}',
    retrieved_at        TIMESTAMPTZ DEFAULT NOW(),
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_bresults_request ON project_baseline_results(request_id);

-- ── Project Value Attributions ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS project_value_attributions (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_id           UUID NOT NULL
                            REFERENCES project_impact_assessments(id) ON DELETE CASCADE,
    hypothesis_id           UUID REFERENCES project_impact_hypotheses(id) ON DELETE SET NULL,
    baseline_result_id      UUID REFERENCES project_baseline_results(id) ON DELETE SET NULL,
    user_id                 VARCHAR(255) NOT NULL,
    project_id              UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    title                   VARCHAR(500),
    fcf_node                VARCHAR(80),
    value_type              VARCHAR(80),
    annualized_value_usd    NUMERIC(18,2),
    formula                 TEXT,
    confidence              NUMERIC(5,4),
    provenance_json         JSONB DEFAULT '{}',
    created_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_attributions_assessment
    ON project_value_attributions(assessment_id);

-- ── Project Activity Log ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS project_activity_log (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                 VARCHAR(255) NOT NULL,
    project_id              UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    meeting_title           VARCHAR(500),
    responsible_party       VARCHAR(500),
    activity_at             TIMESTAMPTZ DEFAULT NOW(),
    top_actions_completed   JSONB DEFAULT '[]',
    help_needed             TEXT,
    issues_risks            JSONB DEFAULT '[]',
    countermeasures         JSONB DEFAULT '[]',
    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_activity_project ON project_activity_log(project_id);
CREATE INDEX IF NOT EXISTS idx_activity_at ON project_activity_log(activity_at DESC);

-- ── System Logs ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS system_logs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             VARCHAR(255) NOT NULL,
    workflow_name       VARCHAR(100),
    agent_set           JSONB DEFAULT '[]',
    job_id              VARCHAR(200),
    token_count         INTEGER,
    latency_ms          INTEGER,
    confidence_scores   JSONB DEFAULT '{}',
    status              VARCHAR(20) CHECK (status IN ('success','failed')),
    error_message       TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_syslogs_user ON system_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_syslogs_workflow ON system_logs(workflow_name);
CREATE INDEX IF NOT EXISTS idx_syslogs_created ON system_logs(created_at DESC);
"""


# ---------------------------------------------------------------------------
# Serialiser (mirrors home_projects.py)
# ---------------------------------------------------------------------------

def _serialize(row: dict) -> dict:
    """Convert UUID, datetime, Decimal objects to JSON-safe types."""
    out: dict[str, Any] = {}
    for k, v in row.items():
        if isinstance(v, uuid.UUID):
            out[k] = str(v)
        elif isinstance(v, datetime):
            out[k] = v.isoformat()
        elif isinstance(v, Decimal):
            out[k] = float(v)
        elif isinstance(v, (dict, list)):
            out[k] = v
        else:
            out[k] = v
    return out


def _rows(cursor) -> list[dict]:
    return [_serialize(dict(r)) for r in cursor.fetchall()]


def _one(cursor) -> dict | None:
    row = cursor.fetchone()
    return _serialize(dict(row)) if row else None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# CatalystDB
# ---------------------------------------------------------------------------

class CatalystDB:
    """
    Synchronous database access layer for jarvis_catalyst.

    All methods return plain dicts / lists of dicts.  Returns None (or [])
    on failures — callers decide how to degrade.
    """

    def __init__(self, db_url: str = _DEFAULT_URL) -> None:
        self._db_url = db_url
        self._available = _PG_AVAILABLE

    # ── Connection ──────────────────────────────────────────────────────────

    def _connect(self):
        conn = psycopg2.connect(self._db_url)
        conn.autocommit = False
        return conn

    def _q(self, sql: str, params=()) -> list[dict]:
        """Run a SELECT, return list of dicts."""
        if not self._available:
            return []
        try:
            with self._connect() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(sql, params)
                    return _rows(cur)
        except Exception as exc:
            log.warning("CatalystDB query error: %s", exc)
            return []

    def _q1(self, sql: str, params=()) -> dict | None:
        """Run a SELECT, return one dict or None."""
        if not self._available:
            return None
        try:
            with self._connect() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(sql, params)
                    return _one(cur)
        except Exception as exc:
            log.warning("CatalystDB query1 error: %s", exc)
            return None

    def _exec(self, sql: str, params=()) -> bool:
        """Run an INSERT/UPDATE/DELETE. Returns True on success."""
        if not self._available:
            return False
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, params)
                conn.commit()
            return True
        except Exception as exc:
            log.warning("CatalystDB exec error: %s", exc)
            return False

    def _exec_returning(self, sql: str, params=()) -> dict | None:
        """Run INSERT … RETURNING *. Returns the new row dict or None."""
        if not self._available:
            return None
        try:
            with self._connect() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(sql, params)
                    result = _one(cur)
                conn.commit()
            return result
        except Exception as exc:
            log.warning("CatalystDB exec_returning error: %s", exc)
            return None

    # ── Schema bootstrap ────────────────────────────────────────────────────

    def ensure_schema(self) -> bool:
        """Create all tables and indexes if they don't exist. Safe to call repeatedly."""
        if not self._available:
            log.warning("CatalystDB: psycopg2 not available — schema not created")
            return False
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(_SCHEMA_SQL)
                    cur.execute(
                        """
                        ALTER TABLE raw_signals
                            DROP CONSTRAINT IF EXISTS raw_signals_signal_type_check;
                        ALTER TABLE raw_signals
                            ADD CONSTRAINT raw_signals_signal_type_check
                            CHECK (signal_type IN (
                                'calendar_event','email','teams_message',
                                'meeting_transcript','quick_note','notebook_photo',
                                'slack_message','document','web_clip','news',
                                'agent_activity','agent_alert','agent_commitment',
                                'agent_completion','agent_decision','agent_observation',
                                'agent_route','agent_work'
                            ));

                        ALTER TABLE catalyst_tasks
                            DROP CONSTRAINT IF EXISTS catalyst_tasks_task_type_check;
                        ALTER TABLE catalyst_tasks
                            ADD CONSTRAINT catalyst_tasks_task_type_check
                            CHECK (task_type IN (
                                'project_derived','ad_hoc','routine',
                                'agent_task','agent_approved'
                            ));
                        """
                    )
                conn.commit()
            log.info("CatalystDB: schema ensured on jarvis_catalyst")
            return True
        except Exception as exc:
            log.error("CatalystDB.ensure_schema failed: %s", exc)
            return False

    def is_available(self) -> bool:
        if not self._available:
            return False
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
            return True
        except Exception:
            return False

    # ── User Preferences ────────────────────────────────────────────────────

    def get_preferences(self, user_id: str) -> dict:
        row = self._q1(
            "SELECT * FROM user_preferences WHERE user_id = %s", (user_id,)
        )
        if not row:
            return {"user_id": user_id, "autonomy_level": 0}
        return row

    def upsert_preferences(self, user_id: str, data: dict) -> bool:
        cols = ["autonomy_level", "threshold_suggest_only", "threshold_draft_for_review",
                "threshold_act_notify_after", "threshold_full_auto", "autonomy_floor"]
        updates = {k: data[k] for k in cols if k in data}
        if not updates:
            return False
        set_parts = ", ".join(f"{k} = %s" for k in updates)
        vals = list(updates.values())
        return self._exec(
            f"""INSERT INTO user_preferences (user_id, {", ".join(updates)})
                VALUES (%s, {", ".join(["%s"] * len(updates))})
                ON CONFLICT (user_id) DO UPDATE SET {set_parts}, updated_at = NOW()""",
            (user_id, *vals, *vals),
        )

    # ── Signals ─────────────────────────────────────────────────────────────

    def ingest_signal(
        self,
        user_id: str,
        signal_type: str,
        content: str,
        *,
        external_id: str | None = None,
        source_metadata: dict | None = None,
        criticality: str = "STANDARD",
    ) -> dict | None:
        return self._exec_returning(
            """INSERT INTO raw_signals
               (user_id, signal_type, content, external_id, source_metadata, signal_criticality)
               VALUES (%s, %s, %s, %s, %s, %s)
               RETURNING *""",
            (
                user_id,
                signal_type,
                content,
                external_id,
                json.dumps(source_metadata or {}),
                criticality,
            ),
        )

    def get_recent_signals(self, user_id: str, limit: int = 50) -> list[dict]:
        return self._q(
            "SELECT * FROM raw_signals WHERE user_id = %s ORDER BY created_at DESC LIMIT %s",
            (user_id, limit),
        )

    def classify_signal(
        self,
        signal_id: str,
        classification: str,
        related_project_id: str | None = None,
    ) -> bool:
        return self._exec(
            """UPDATE raw_signals
               SET classification = %s, related_project_id = %s, classified_at = NOW()
               WHERE id = %s""",
            (classification, related_project_id, signal_id),
        )

    def ingest_email_signal(
        self,
        user_id: str,
        message_id: str,
        subject: str,
        from_address: str,
        body: str,
        *,
        received_at: str | None = None,
        conversation_id: str | None = None,
        importance: str | None = None,
    ) -> dict | None:
        """Ingest an email as both a raw_signal and a raw_email record."""
        try:
            with self._connect() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    # raw_signal
                    cur.execute(
                        """INSERT INTO raw_signals (user_id, signal_type, content,
                           external_id, source_metadata)
                           VALUES (%s, 'email', %s, %s, %s)
                           ON CONFLICT DO NOTHING
                           RETURNING *""",
                        (
                            user_id,
                            f"Subject: {subject}\n\n{body}",
                            message_id,
                            json.dumps({"subject": subject, "from": from_address}),
                        ),
                    )
                    signal_row = _one(cur)
                    signal_id = signal_row["id"] if signal_row else None

                    # raw_email
                    cur.execute(
                        """INSERT INTO raw_emails
                           (user_id, signal_id, message_id, subject, from_address,
                            received_at, conversation_id, importance)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                           ON CONFLICT (message_id) DO NOTHING
                           RETURNING *""",
                        (
                            user_id,
                            signal_id,
                            message_id,
                            subject,
                            from_address,
                            received_at,
                            conversation_id,
                            importance,
                        ),
                    )
                    email_row = _one(cur)
                conn.commit()
            return email_row
        except Exception as exc:
            log.warning("ingest_email_signal error: %s", exc)
            return None

    # ── Projects ─────────────────────────────────────────────────────────────

    def list_projects(self, user_id: str, status: str | None = None) -> list[dict]:
        if status:
            return self._q(
                "SELECT * FROM projects WHERE user_id = %s AND status = %s "
                "ORDER BY last_activity_at DESC",
                (user_id, status),
            )
        return self._q(
            "SELECT * FROM projects WHERE user_id = %s AND status != 'archived' "
            "ORDER BY last_activity_at DESC",
            (user_id,),
        )

    def get_project(self, project_id: str) -> dict | None:
        return self._q1("SELECT * FROM projects WHERE id = %s", (project_id,))

    def create_project(
        self,
        user_id: str,
        name: str,
        *,
        problem_statement: str | None = None,
        source_signal_id: str | None = None,
    ) -> dict | None:
        return self._exec_returning(
            """INSERT INTO projects (user_id, name, problem_statement, source_signal_id)
               VALUES (%s, %s, %s, %s)
               RETURNING *""",
            (user_id, name, problem_statement, source_signal_id),
        )

    def update_project_status(self, project_id: str, status: str) -> bool:
        return self._exec(
            "UPDATE projects SET status = %s, updated_at = NOW() WHERE id = %s",
            (status, project_id),
        )

    def touch_project(self, project_id: str) -> bool:
        return self._exec(
            "UPDATE projects SET last_activity_at = NOW(), updated_at = NOW() WHERE id = %s",
            (project_id,),
        )

    # ── Tasks ─────────────────────────────────────────────────────────────────

    def list_open_tasks(self, user_id: str, project_id: str | None = None) -> list[dict]:
        if project_id:
            return self._q(
                "SELECT * FROM catalyst_tasks WHERE user_id = %s AND project_id = %s "
                "AND status != 'complete' AND archived_at IS NULL ORDER BY due_date NULLS LAST",
                (user_id, project_id),
            )
        return self._q(
            "SELECT * FROM catalyst_tasks WHERE user_id = %s "
            "AND status != 'complete' AND archived_at IS NULL ORDER BY due_date NULLS LAST",
            (user_id,),
        )

    def create_task(
        self,
        user_id: str,
        title: str,
        *,
        project_id: str | None = None,
        priority: str = "medium",
        due_date: str | None = None,
        source_signal_id: str | None = None,
        task_type: str = "ad_hoc",
    ) -> dict | None:
        return self._exec_returning(
            """INSERT INTO catalyst_tasks
               (user_id, title, project_id, priority, due_date, source_signal_id, task_type)
               VALUES (%s, %s, %s, %s, %s, %s, %s)
               RETURNING *""",
            (user_id, title, project_id, priority, due_date, source_signal_id, task_type),
        )

    def complete_task(self, task_id: str) -> bool:
        return self._exec(
            "UPDATE catalyst_tasks SET status = 'complete', completed_at = NOW(), "
            "updated_at = NOW() WHERE id = %s",
            (task_id,),
        )

    # ── Commitments ──────────────────────────────────────────────────────────

    def list_open_commitments(self, user_id: str) -> list[dict]:
        return self._q(
            "SELECT * FROM commitments WHERE user_id = %s AND status = 'open' "
            "ORDER BY due_date NULLS LAST",
            (user_id,),
        )

    def create_commitment(
        self,
        user_id: str,
        signal_id: str,
        description: str,
        *,
        responsible_party: str | None = None,
        due_date: str | None = None,
        confidence: float = 0.7,
    ) -> dict | None:
        return self._exec_returning(
            """INSERT INTO commitments
               (user_id, source_signal_id, description, responsible_party, due_date,
                confidence_score)
               VALUES (%s, %s, %s, %s, %s, %s)
               RETURNING *""",
            (user_id, signal_id, description, responsible_party, due_date, confidence),
        )

    def update_commitment_status(self, commitment_id: str, status: str) -> bool:
        return self._exec(
            "UPDATE commitments SET status = %s, updated_at = NOW() WHERE id = %s",
            (status, commitment_id),
        )

    # ── Decisions ────────────────────────────────────────────────────────────

    def record_decision(
        self,
        user_id: str,
        signal_id: str,
        description: str,
        *,
        reasoning: str | None = None,
        confidence: float = 0.7,
    ) -> dict | None:
        return self._exec_returning(
            """INSERT INTO decisions
               (user_id, source_signal_id, description, reasoning, confidence_score)
               VALUES (%s, %s, %s, %s, %s)
               RETURNING *""",
            (user_id, signal_id, description, reasoning, confidence),
        )

    def list_recent_decisions(self, user_id: str, limit: int = 20) -> list[dict]:
        return self._q(
            "SELECT * FROM decisions WHERE user_id = %s ORDER BY made_at DESC LIMIT %s",
            (user_id, limit),
        )

    # ── Contacts ─────────────────────────────────────────────────────────────

    def upsert_contact(
        self,
        user_id: str,
        email_address: str,
        display_name: str | None = None,
        *,
        job_title: str | None = None,
        company_name: str | None = None,
    ) -> dict | None:
        return self._exec_returning(
            """INSERT INTO contacts (user_id, email_address, display_name, job_title, company_name)
               VALUES (%s, %s, %s, %s, %s)
               ON CONFLICT (user_id, email_address) DO UPDATE
               SET display_name  = COALESCE(EXCLUDED.display_name, contacts.display_name),
                   job_title     = COALESCE(EXCLUDED.job_title, contacts.job_title),
                   company_name  = COALESCE(EXCLUDED.company_name, contacts.company_name),
                   interaction_count = contacts.interaction_count + 1,
                   last_interaction_at = NOW(),
                   updated_at = NOW()
               RETURNING *""",
            (user_id, email_address, display_name, job_title, company_name),
        )

    # ── Briefing ──────────────────────────────────────────────────────────────

    def save_briefing_item(
        self,
        user_id: str,
        content: str,
        briefing_date: str,
        *,
        source_type: str | None = None,
        signal_id: str | None = None,
        confidence: float | None = None,
        reasoning_chain: str | None = None,
    ) -> dict | None:
        return self._exec_returning(
            """INSERT INTO briefing_items
               (user_id, content, briefing_date, source_type, source_signal_id,
                confidence_score, reasoning_chain)
               VALUES (%s, %s, %s, %s, %s, %s, %s)
               RETURNING *""",
            (user_id, content, briefing_date, source_type, signal_id, confidence, reasoning_chain),
        )

    def get_briefing_items(self, user_id: str, briefing_date: str) -> list[dict]:
        return self._q(
            "SELECT * FROM briefing_items WHERE user_id = %s AND briefing_date = %s "
            "ORDER BY confidence_score DESC NULLS LAST",
            (user_id, briefing_date),
        )

    # ── Workflow Run Logging ──────────────────────────────────────────────────

    def start_workflow_run(
        self,
        user_id: str,
        workflow_name: str,
        *,
        signal_id: str | None = None,
        signal_kind: str | None = None,
    ) -> dict | None:
        return self._exec_returning(
            """INSERT INTO agent_workflow_runs
               (user_id, workflow_name, source_signal_id, signal_kind, status, started_at)
               VALUES (%s, %s, %s, %s, 'EXECUTING', NOW())
               RETURNING *""",
            (user_id, workflow_name, signal_id, signal_kind),
        )

    def complete_workflow_run(
        self,
        run_id: str,
        *,
        status: str = "COMPLETED",
        summary: str | None = None,
        confidence: float | None = None,
    ) -> bool:
        return self._exec(
            """UPDATE agent_workflow_runs
               SET status = %s, summary = %s, overall_confidence = %s, completed_at = NOW()
               WHERE id = %s""",
            (status, summary, confidence, run_id),
        )

    def log_workflow_step(
        self,
        run_id: str,
        user_id: str,
        agent_name: str,
        step_name: str,
        *,
        status: str = "COMPLETED",
        input_summary: str | None = None,
        output_summary: str | None = None,
        confidence: float | None = None,
    ) -> dict | None:
        return self._exec_returning(
            """INSERT INTO agent_workflow_steps
               (run_id, user_id, agent_name, step_name, status,
                input_summary, output_summary, confidence_score, started_at, completed_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
               RETURNING *""",
            (run_id, user_id, agent_name, step_name, status,
             input_summary, output_summary, confidence),
        )

    # ── Initiatives / Value Tracking ──────────────────────────────────────────

    def list_initiatives(self, user_id: str) -> list[dict]:
        return self._q(
            "SELECT * FROM initiatives WHERE user_id = %s ORDER BY created_at DESC",
            (user_id,),
        )

    def create_initiative(
        self,
        user_id: str,
        name: str,
        *,
        description: str | None = None,
        business_unit: str | None = None,
        owner_name: str | None = None,
    ) -> dict | None:
        return self._exec_returning(
            """INSERT INTO initiatives (user_id, name, description, business_unit, owner_name)
               VALUES (%s, %s, %s, %s, %s)
               RETURNING *""",
            (user_id, name, description, business_unit, owner_name),
        )

    def add_value_use_case(
        self,
        initiative_id: str,
        user_id: str,
        value_type: str,
        amount: float,
        confidence: str,
        *,
        stakeholder: str | None = None,
        description: str | None = None,
    ) -> dict | None:
        result = self._exec_returning(
            """INSERT INTO value_use_cases
               (initiative_id, user_id, value_type, amount, confidence,
                stakeholder, description)
               VALUES (%s, %s, %s, %s, %s, %s, %s)
               RETURNING *""",
            (initiative_id, user_id, value_type, amount, confidence, stakeholder, description),
        )
        if result:
            # Update initiative totals
            col = {
                "Projected": "total_projected_value",
                "Committed": "total_committed_value",
                "Realized":  "total_realized_value",
            }.get(confidence, "total_projected_value")
            self._exec(
                f"""UPDATE initiatives
                    SET {col} = {col} + %s, use_case_count = use_case_count + 1,
                    updated_at = NOW()
                    WHERE id = %s""",
                (amount, initiative_id),
            )
        return result

    # ── System Log ───────────────────────────────────────────────────────────

    def log_system_event(
        self,
        user_id: str,
        workflow_name: str,
        *,
        status: str = "success",
        token_count: int | None = None,
        latency_ms: int | None = None,
        error_message: str | None = None,
        confidence_scores: dict | None = None,
        agent_set: list | None = None,
    ) -> bool:
        return self._exec(
            """INSERT INTO system_logs
               (user_id, workflow_name, status, token_count, latency_ms,
                error_message, confidence_scores, agent_set)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                user_id,
                workflow_name,
                status,
                token_count,
                latency_ms,
                error_message,
                json.dumps(confidence_scores or {}),
                json.dumps(agent_set or []),
            ),
        )

    # ── Dashboard summary ─────────────────────────────────────────────────────

    def get_work_summary(self, user_id: str) -> dict:
        """Quick counts for the Work Intelligence overview card."""
        try:
            active = self._q1(
                "SELECT COUNT(*) AS n FROM projects WHERE user_id = %s AND status = 'active'",
                (user_id,),
            )
            at_risk = self._q1(
                "SELECT COUNT(*) AS n FROM projects WHERE user_id = %s AND status = 'at_risk'",
                (user_id,),
            )
            open_tasks = self._q1(
                "SELECT COUNT(*) AS n FROM catalyst_tasks WHERE user_id = %s "
                "AND status != 'complete' AND archived_at IS NULL",
                (user_id,),
            )
            overdue_commitments = self._q1(
                "SELECT COUNT(*) AS n FROM commitments WHERE user_id = %s AND status = 'overdue'",
                (user_id,),
            )
            return {
                "active_projects": int(active["n"]) if active else 0,
                "at_risk_projects": int(at_risk["n"]) if at_risk else 0,
                "open_tasks": int(open_tasks["n"]) if open_tasks else 0,
                "overdue_commitments": int(overdue_commitments["n"]) if overdue_commitments else 0,
            }
        except Exception as exc:
            log.warning("get_work_summary error: %s", exc)
            return {
                "active_projects": 0,
                "at_risk_projects": 0,
                "open_tasks": 0,
                "overdue_commitments": 0,
            }


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_db: CatalystDB | None = None


def get_catalyst_db() -> CatalystDB:
    """Return the module-level CatalystDB singleton."""
    global _db
    if _db is None:
        url = os.environ.get("CATALYST_DB_URL", _DEFAULT_URL)
        _db = CatalystDB(url)
    return _db


def init_catalyst_db(db_url: str | None = None) -> CatalystDB:
    """
    Initialise (or reinitialise) the singleton and ensure the schema exists.
    Call once at JARVIS startup.
    """
    global _db
    url = db_url or os.environ.get("CATALYST_DB_URL", _DEFAULT_URL)
    _db = CatalystDB(url)
    _db.ensure_schema()
    return _db
