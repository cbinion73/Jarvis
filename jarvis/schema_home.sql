-- JARVIS Home Intelligence Schema
-- jarvis_home database
-- Tracks home projects, tasks, signals, email, calendar, and value

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ─── HOME PROJECTS ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS home_projects (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    title           TEXT        NOT NULL,
    track           TEXT        NOT NULL CHECK (track IN ('revenue','savings','operations')),
    category        TEXT,       -- e.g. 'passive_income','rental','energy_efficiency','subscription_audit'
    status          TEXT        NOT NULL DEFAULT 'active'
                                CHECK (status IN ('active','planning','stalled','complete','archived')),
    problem_statement TEXT,
    objective       TEXT,
    projected_value NUMERIC(12,2),   -- annual revenue or savings in USD
    realized_value  NUMERIC(12,2)    DEFAULT 0,
    payback_months  INTEGER,
    start_date      DATE,
    target_date     DATE,
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ─── PROJECT TASKS ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS project_tasks (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      UUID        REFERENCES home_projects(id) ON DELETE CASCADE,
    title           TEXT        NOT NULL,
    description     TEXT,
    status          TEXT        NOT NULL DEFAULT 'open'
                                CHECK (status IN ('open','in_progress','blocked','complete','dismissed')),
    priority        TEXT        DEFAULT 'medium'
                                CHECK (priority IN ('low','medium','high','critical')),
    due_date        DATE,
    completed_at    TIMESTAMPTZ,
    blocked_reason  TEXT,
    next_step       TEXT,
    source          TEXT        DEFAULT 'manual'
                                CHECK (source IN ('manual','email_signal','calendar_signal','voice','agent')),
    source_signal_id UUID,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ─── HOME SIGNALS ─────────────────────────────────────────────────────────────
-- Immutable inbox of extracted intelligence from all sources
CREATE TABLE IF NOT EXISTS home_signals (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    type            TEXT        NOT NULL
                                CHECK (type IN ('email','calendar','voice','note','document','photo')),
    source          TEXT        NOT NULL
                                CHECK (source IN ('gmail','outlook','google_calendar',
                                                  'outlook_calendar','cozi','manual','agent')),
    subject         TEXT,
    body            TEXT,
    sender          TEXT,
    external_id     TEXT,       -- message/event ID from the originating system
    project_id      UUID        REFERENCES home_projects(id),
    classified      BOOLEAN     DEFAULT FALSE,
    classification  TEXT,       -- 'project_update','contractor_quote','bill','scheduling','family','other'
    extracted_tasks JSONB,      -- [{title, priority, due_date}]
    signal_date     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ─── VALUE LOG ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS value_log (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      UUID        REFERENCES home_projects(id) ON DELETE CASCADE,
    amount          NUMERIC(12,2) NOT NULL,
    type            TEXT        NOT NULL CHECK (type IN ('revenue','savings','cost')),
    description     TEXT,
    logged_date     DATE        DEFAULT CURRENT_DATE,
    source          TEXT        DEFAULT 'manual'
                                CHECK (source IN ('manual','email_signal','bank','agent')),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ─── CALENDAR EVENTS ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS calendar_events (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id     TEXT        NOT NULL,
    source          TEXT        NOT NULL CHECK (source IN ('google','outlook','cozi')),
    title           TEXT        NOT NULL,
    description     TEXT,
    start_time      TIMESTAMPTZ,
    end_time        TIMESTAMPTZ,
    all_day         BOOLEAN     DEFAULT FALSE,
    location        TEXT,
    attendees       JSONB,      -- [{name, email}]
    organizer       TEXT,
    project_id      UUID        REFERENCES home_projects(id),
    is_project_signal BOOLEAN   DEFAULT FALSE,
    color           TEXT,       -- Cozi color tags
    calendar_name   TEXT,       -- which calendar within the source
    synced_at       TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(external_id, source)
);

-- ─── EMAIL CACHE ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS email_cache (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id     TEXT        NOT NULL,
    source          TEXT        NOT NULL CHECK (source IN ('gmail','outlook')),
    thread_id       TEXT,
    subject         TEXT,
    sender_email    TEXT,
    sender_name     TEXT,
    recipients      JSONB,      -- [{name, email}]
    snippet         TEXT,
    body_text       TEXT,
    received_at     TIMESTAMPTZ,
    is_read         BOOLEAN     DEFAULT FALSE,
    is_flagged      BOOLEAN     DEFAULT FALSE,
    importance      TEXT        DEFAULT 'normal' CHECK (importance IN ('low','normal','high')),
    labels          JSONB,      -- Gmail labels or Outlook categories as string array
    project_id      UUID        REFERENCES home_projects(id),
    signal_id       UUID        REFERENCES home_signals(id),
    processed       BOOLEAN     DEFAULT FALSE,
    synced_at       TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(external_id, source)
);

-- ─── SYNC STATE ───────────────────────────────────────────────────────────────
-- Tracks last successful sync per source so we only fetch deltas
CREATE TABLE IF NOT EXISTS sync_state (
    source          TEXT        PRIMARY KEY,
    last_sync_at    TIMESTAMPTZ,
    last_token      TEXT,       -- page token, delta token, sync token per API
    status          TEXT        DEFAULT 'ok' CHECK (status IN ('ok','error','pending')),
    error_detail    TEXT,
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO sync_state (source) VALUES
    ('gmail'), ('outlook'), ('google_calendar'), ('outlook_calendar'), ('cozi')
ON CONFLICT (source) DO NOTHING;

-- ─── INDEXES ──────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_tasks_project      ON project_tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status       ON project_tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_due_date     ON project_tasks(due_date);
CREATE INDEX IF NOT EXISTS idx_signals_project    ON home_signals(project_id);
CREATE INDEX IF NOT EXISTS idx_signals_source     ON home_signals(source);
CREATE INDEX IF NOT EXISTS idx_signals_classified ON home_signals(classified);
CREATE INDEX IF NOT EXISTS idx_calendar_start     ON calendar_events(start_time);
CREATE INDEX IF NOT EXISTS idx_calendar_source    ON calendar_events(source);
CREATE INDEX IF NOT EXISTS idx_email_received     ON email_cache(received_at DESC);
CREATE INDEX IF NOT EXISTS idx_email_source       ON email_cache(source);
CREATE INDEX IF NOT EXISTS idx_email_processed    ON email_cache(processed);
CREATE INDEX IF NOT EXISTS idx_value_project      ON value_log(project_id);
