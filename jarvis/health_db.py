"""
JARVIS Health Database — async SQLite via aiosqlite.
Stores wearable metrics, MyChart records, and structured health data.

DB location: ~/.jarvis/health/health.db
"""
from __future__ import annotations

import json
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Any

import aiosqlite

log = logging.getLogger(__name__)

_DB_PATH = Path.home() / ".jarvis" / "health" / "health.db"
_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------
_SCHEMA = """
CREATE TABLE IF NOT EXISTS daily_metrics (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    date         TEXT    NOT NULL,
    source       TEXT    NOT NULL DEFAULT 'apple_health',
    steps        INTEGER,
    resting_hr   REAL,
    hrv          REAL,
    sleep_hours  REAL,
    sleep_deep   REAL,
    sleep_rem    REAL,
    active_cal   INTEGER,
    exercise_min INTEGER,
    stand_hours  INTEGER,
    blood_oxygen REAL,
    weight       REAL,
    raw_json     TEXT,
    created_at   TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE(date, source)
);

CREATE TABLE IF NOT EXISTS test_results (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    test_name       TEXT    NOT NULL,
    result_date     TEXT,
    status          TEXT,
    provider        TEXT,
    facility        TEXT,
    raw_text        TEXT,
    value           TEXT,
    unit            TEXT,
    reference_range TEXT,
    flag            TEXT,
    components      TEXT,
    order_id        TEXT,
    synced_at       TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS medications (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    name           TEXT    NOT NULL,
    generic_name   TEXT,
    dosage         TEXT,
    frequency      TEXT,
    prescribed_date TEXT,
    prescriber     TEXT,
    pharmacy       TEXT,
    quantity       TEXT,
    day_supply     INTEGER,
    raw_text       TEXT,
    synced_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS conditions (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    condition_name TEXT    NOT NULL,
    category       TEXT,
    status         TEXT    NOT NULL DEFAULT 'active',
    raw_text       TEXT,
    synced_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS visits (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    visit_date   TEXT,
    visit_type   TEXT,
    provider     TEXT,
    facility     TEXT,
    is_upcoming  INTEGER NOT NULL DEFAULT 0,
    synced_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS treatment_goals (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    goal_name     TEXT    NOT NULL,
    target        TEXT,
    current_value TEXT,
    on_track      INTEGER,
    last_updated  TEXT,
    synced_at     TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS mychart_pages (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    page_key   TEXT    NOT NULL UNIQUE,
    page_type  TEXT,
    content    TEXT,
    synced_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS ecg_readings (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    reading_date    TEXT    NOT NULL,
    source          TEXT    NOT NULL DEFAULT 'kardia',
    classification  TEXT,
    avg_heart_rate  REAL,
    sampling_freq   INTEGER,
    sample_count    INTEGER,
    duration_sec    REAL,
    symptoms        TEXT,
    voltage_json    TEXT,
    raw_json        TEXT,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE(reading_date, source)
);

CREATE TABLE IF NOT EXISTS bp_readings (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    reading_date TEXT    NOT NULL,
    source       TEXT    NOT NULL DEFAULT 'omron',
    systolic     INTEGER,
    diastolic    INTEGER,
    pulse        INTEGER,
    irregular    INTEGER NOT NULL DEFAULT 0,
    body_movement INTEGER NOT NULL DEFAULT 0,
    cuff_wrap    INTEGER NOT NULL DEFAULT 0,
    raw_json     TEXT,
    created_at   TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE(reading_date, source)
);

CREATE TABLE IF NOT EXISTS glucose_readings (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    reading_time TEXT    NOT NULL,
    source       TEXT    NOT NULL DEFAULT 'dexcom',
    glucose_mgdl INTEGER,
    trend        TEXT,
    trend_rate   REAL,
    status       TEXT,
    raw_json     TEXT,
    created_at   TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE(reading_time, source)
);

CREATE TABLE IF NOT EXISTS sync_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    source     TEXT    NOT NULL,
    status     TEXT    NOT NULL,
    detail     TEXT,
    created_at TEXT    NOT NULL DEFAULT (datetime('now'))
);
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

from contextlib import asynccontextmanager

@asynccontextmanager
async def _get_db():
    async with aiosqlite.connect(str(_DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        await db.executescript(_SCHEMA)
        await db.commit()
        # Migrations: add columns to existing tables if they don't exist yet
        for col_sql in [
            "ALTER TABLE test_results ADD COLUMN value TEXT",
            "ALTER TABLE test_results ADD COLUMN unit TEXT",
            "ALTER TABLE test_results ADD COLUMN reference_range TEXT",
            "ALTER TABLE test_results ADD COLUMN flag TEXT",
            "ALTER TABLE test_results ADD COLUMN components TEXT",
            "ALTER TABLE test_results ADD COLUMN order_id TEXT",
        ]:
            try:
                await db.execute(col_sql)
            except Exception:
                pass  # column already exists
        await db.commit()
        yield db


def _now() -> str:
    return datetime.utcnow().isoformat()


# ---------------------------------------------------------------------------
# Daily wearable metrics
# ---------------------------------------------------------------------------

async def upsert_daily_metrics(metrics: dict) -> None:
    day = metrics.get("date") or date.today().isoformat()
    source = metrics.get("source", "apple_health")
    async with _get_db() as db:
        await db.execute("""
            INSERT INTO daily_metrics
              (date, source, steps, resting_hr, hrv, sleep_hours, sleep_deep,
               sleep_rem, active_cal, exercise_min, stand_hours, blood_oxygen,
               weight, raw_json)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(date, source) DO UPDATE SET
              steps        = excluded.steps,
              resting_hr   = excluded.resting_hr,
              hrv          = excluded.hrv,
              sleep_hours  = excluded.sleep_hours,
              sleep_deep   = excluded.sleep_deep,
              sleep_rem    = excluded.sleep_rem,
              active_cal   = excluded.active_cal,
              exercise_min = excluded.exercise_min,
              stand_hours  = excluded.stand_hours,
              blood_oxygen = excluded.blood_oxygen,
              weight       = excluded.weight,
              raw_json     = excluded.raw_json,
              created_at   = excluded.created_at
        """, (
            day, source,
            metrics.get("steps"), metrics.get("resting_hr"), metrics.get("hrv"),
            metrics.get("sleep_hours"), metrics.get("sleep_deep_hours"),
            metrics.get("sleep_rem_hours"), metrics.get("active_calories"),
            metrics.get("exercise_minutes"), metrics.get("stand_hours"),
            metrics.get("blood_oxygen"), metrics.get("weight"),
            json.dumps(metrics),
        ))
        await db.commit()


async def get_latest_metrics(days: int = 7) -> list[dict]:
    async with _get_db() as db:
        cur = await db.execute(
            "SELECT * FROM daily_metrics ORDER BY date DESC LIMIT ?", (days,)
        )
        return [dict(r) for r in await cur.fetchall()]


async def get_today_metrics() -> dict | None:
    today = date.today().isoformat()
    async with _get_db() as db:
        cur = await db.execute(
            "SELECT * FROM daily_metrics WHERE date=? ORDER BY created_at DESC LIMIT 1",
            (today,),
        )
        row = await cur.fetchone()
        return dict(row) if row else None


# ---------------------------------------------------------------------------
# MyChart pages (raw content store)
# ---------------------------------------------------------------------------

async def upsert_mychart_page(page_key: str, page_type: str, content: str) -> None:
    async with _get_db() as db:
        await db.execute("""
            INSERT INTO mychart_pages (page_key, page_type, content, synced_at)
            VALUES (?, ?, ?, datetime('now'))
            ON CONFLICT(page_key) DO UPDATE SET
              page_type = excluded.page_type,
              content   = excluded.content,
              synced_at = excluded.synced_at
        """, (page_key, page_type, content))
        await db.commit()


async def get_mychart_pages() -> list[dict]:
    async with _get_db() as db:
        cur = await db.execute(
            "SELECT page_key, page_type, synced_at, substr(content,1,300) AS preview "
            "FROM mychart_pages ORDER BY synced_at DESC"
        )
        return [dict(r) for r in await cur.fetchall()]


async def get_mychart_page(page_key: str) -> dict | None:
    async with _get_db() as db:
        cur = await db.execute(
            "SELECT * FROM mychart_pages WHERE page_key=?", (page_key,)
        )
        row = await cur.fetchone()
        return dict(row) if row else None


# ---------------------------------------------------------------------------
# Structured clinical data
# ---------------------------------------------------------------------------

async def replace_test_results(results: list[dict]) -> None:
    async with _get_db() as db:
        await db.execute("DELETE FROM test_results")
        await db.executemany("""
            INSERT INTO test_results
              (test_name, result_date, status, provider, facility,
               value, unit, reference_range, flag, components, order_id, raw_text)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, [(
            r.get("test_name"), r.get("result_date"), r.get("status"),
            r.get("provider"), r.get("facility"),
            r.get("value"), r.get("unit"), r.get("reference_range"),
            r.get("flag"), r.get("components"), r.get("order_id"),
            r.get("raw_text"),
        ) for r in results])
        await db.commit()


async def replace_medications(meds: list[dict]) -> None:
    async with _get_db() as db:
        await db.execute("DELETE FROM medications")
        await db.executemany("""
            INSERT INTO medications
              (name, generic_name, dosage, frequency, prescribed_date,
               prescriber, pharmacy, quantity, day_supply, raw_text)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, [(
            m.get("name"), m.get("generic_name"), m.get("dosage"),
            m.get("frequency"), m.get("prescribed_date"), m.get("prescriber"),
            m.get("pharmacy"), m.get("quantity"), m.get("day_supply"),
            m.get("raw_text"),
        ) for m in meds])
        await db.commit()


async def replace_conditions(conds: list[dict]) -> None:
    async with _get_db() as db:
        await db.execute("DELETE FROM conditions")
        await db.executemany("""
            INSERT INTO conditions (condition_name, category, status, raw_text)
            VALUES (?,?,?,?)
        """, [(
            c.get("condition_name"), c.get("category"),
            c.get("status", "active"), c.get("raw_text"),
        ) for c in conds])
        await db.commit()


async def replace_visits(visits_list: list[dict]) -> None:
    async with _get_db() as db:
        await db.execute("DELETE FROM visits")
        await db.executemany("""
            INSERT INTO visits (visit_date, visit_type, provider, facility, is_upcoming)
            VALUES (?,?,?,?,?)
        """, [(
            v.get("visit_date"), v.get("visit_type"),
            v.get("provider"), v.get("facility"),
            1 if v.get("is_upcoming") else 0,
        ) for v in visits_list])
        await db.commit()


async def replace_treatment_goals(goals: list[dict]) -> None:
    async with _get_db() as db:
        await db.execute("DELETE FROM treatment_goals")
        await db.executemany("""
            INSERT INTO treatment_goals
              (goal_name, target, current_value, on_track, last_updated)
            VALUES (?,?,?,?,?)
        """, [(
            g.get("goal_name"), g.get("target"), g.get("current_value"),
            1 if g.get("on_track") else 0, g.get("last_updated"),
        ) for g in goals])
        await db.commit()


# ---------------------------------------------------------------------------
# ECG readings (KardiaMobile via Apple Health / Health Auto Export)
# ---------------------------------------------------------------------------

async def upsert_ecg_reading(rec: dict) -> None:
    """Store one ECG record. reading_date is the ISO start timestamp."""
    async with _get_db() as db:
        await db.execute("""
            INSERT INTO ecg_readings
              (reading_date, source, classification, avg_heart_rate,
               sampling_freq, sample_count, duration_sec, symptoms,
               voltage_json, raw_json)
            VALUES (?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(reading_date, source) DO UPDATE SET
              classification = excluded.classification,
              avg_heart_rate = excluded.avg_heart_rate,
              sampling_freq  = excluded.sampling_freq,
              sample_count   = excluded.sample_count,
              duration_sec   = excluded.duration_sec,
              symptoms       = excluded.symptoms,
              voltage_json   = excluded.voltage_json,
              raw_json       = excluded.raw_json
        """, (
            rec.get("reading_date"), rec.get("source", "kardia"),
            rec.get("classification"), rec.get("avg_heart_rate"),
            rec.get("sampling_freq"), rec.get("sample_count"),
            rec.get("duration_sec"), rec.get("symptoms"),
            rec.get("voltage_json"), rec.get("raw_json"),
        ))
        await db.commit()


async def get_ecg_readings(limit: int = 20) -> list[dict]:
    """Return recent ECG records (no voltage data — summary only)."""
    async with _get_db() as db:
        cur = await db.execute(
            "SELECT id, reading_date, source, classification, avg_heart_rate, "
            "sampling_freq, sample_count, duration_sec, symptoms, created_at "
            "FROM ecg_readings ORDER BY reading_date DESC LIMIT ?", (limit,)
        )
        return [dict(r) for r in await cur.fetchall()]


async def get_ecg_waveform(ecg_id: int) -> dict | None:
    """Return full ECG record including voltage data for waveform rendering."""
    async with _get_db() as db:
        cur = await db.execute(
            "SELECT * FROM ecg_readings WHERE id=?", (ecg_id,)
        )
        row = await cur.fetchone()
        return dict(row) if row else None


# ---------------------------------------------------------------------------
# Blood pressure readings (Omron Connect)
# ---------------------------------------------------------------------------

async def upsert_bp_reading(rec: dict) -> None:
    """Store one BP reading."""
    async with _get_db() as db:
        await db.execute("""
            INSERT INTO bp_readings
              (reading_date, source, systolic, diastolic, pulse,
               irregular, body_movement, cuff_wrap, raw_json)
            VALUES (?,?,?,?,?,?,?,?,?)
            ON CONFLICT(reading_date, source) DO UPDATE SET
              systolic      = excluded.systolic,
              diastolic     = excluded.diastolic,
              pulse         = excluded.pulse,
              irregular     = excluded.irregular,
              body_movement = excluded.body_movement,
              cuff_wrap     = excluded.cuff_wrap,
              raw_json      = excluded.raw_json
        """, (
            rec.get("reading_date"), rec.get("source", "omron"),
            rec.get("systolic"), rec.get("diastolic"), rec.get("pulse"),
            1 if rec.get("irregular") else 0,
            1 if rec.get("body_movement") else 0,
            1 if rec.get("cuff_wrap") else 0,
            rec.get("raw_json"),
        ))
        await db.commit()


async def get_bp_readings(limit: int = 30) -> list[dict]:
    async with _get_db() as db:
        cur = await db.execute(
            "SELECT * FROM bp_readings ORDER BY reading_date DESC LIMIT ?", (limit,)
        )
        return [dict(r) for r in await cur.fetchall()]


async def get_latest_bp() -> dict | None:
    async with _get_db() as db:
        cur = await db.execute(
            "SELECT * FROM bp_readings ORDER BY reading_date DESC LIMIT 1"
        )
        row = await cur.fetchone()
        return dict(row) if row else None


# ---------------------------------------------------------------------------
# Sync log
# ---------------------------------------------------------------------------

async def upsert_glucose_reading(rec: dict) -> None:
    """Insert or update a single CGM glucose reading."""
    async with _get_db() as db:
        await db.execute("""
            INSERT INTO glucose_readings
              (reading_time, source, glucose_mgdl, trend, trend_rate, status, raw_json)
            VALUES (?,?,?,?,?,?,?)
            ON CONFLICT(reading_time, source) DO UPDATE SET
              glucose_mgdl = excluded.glucose_mgdl,
              trend        = excluded.trend,
              trend_rate   = excluded.trend_rate,
              status       = excluded.status,
              raw_json     = excluded.raw_json
        """, (
            rec.get("reading_time"),
            rec.get("source", "dexcom"),
            rec.get("glucose_mgdl"),
            rec.get("trend"),
            rec.get("trend_rate"),
            rec.get("status"),
            rec.get("raw_json"),
        ))
        await db.commit()


async def get_glucose_readings(hours: int = 24) -> list[dict]:
    """Return glucose readings for the past N hours, newest first."""
    async with _get_db() as db:
        cur = await db.execute("""
            SELECT * FROM glucose_readings
            WHERE reading_time >= datetime('now', ? || ' hours')
            ORDER BY reading_time DESC
        """, (f"-{hours}",))
        return [dict(r) for r in await cur.fetchall()]


async def get_latest_glucose() -> dict | None:
    """Return the single most recent glucose reading."""
    async with _get_db() as db:
        cur = await db.execute(
            "SELECT * FROM glucose_readings ORDER BY reading_time DESC LIMIT 1"
        )
        row = await cur.fetchone()
        return dict(row) if row else None


async def get_glucose_stats(hours: int = 24) -> dict:
    """
    Compute time-in-range statistics over the past N hours.
    Returns: mean, min, max, time_in_range_pct, time_below_pct, time_above_pct, gmi, count
    """
    async with _get_db() as db:
        cur = await db.execute("""
            SELECT glucose_mgdl FROM glucose_readings
            WHERE reading_time >= datetime('now', ? || ' hours')
              AND glucose_mgdl IS NOT NULL
            ORDER BY reading_time
        """, (f"-{hours}",))
        rows = [r[0] for r in await cur.fetchall()]

    if not rows:
        return {"count": 0}

    count     = len(rows)
    mean_g    = sum(rows) / count
    in_range  = sum(1 for g in rows if 70 <= g <= 180)
    tight_range = sum(1 for g in rows if 70 <= g <= 140)
    below     = sum(1 for g in rows if g < 70)
    above     = sum(1 for g in rows if g > 180)
    # GMI = Glucose Management Indicator (estimates A1c from mean glucose)
    gmi = round(3.31 + 0.02392 * mean_g, 2)

    return {
        "count":              count,
        "mean_mgdl":          round(mean_g, 1),
        "min_mgdl":           min(rows),
        "max_mgdl":           max(rows),
        "time_in_range_pct":  round(in_range / count * 100, 1),
        "time_tight_range_pct": round(tight_range / count * 100, 1),
        "time_below_pct":     round(below / count * 100, 1),
        "time_above_pct":     round(above / count * 100, 1),
        "gmi":                gmi,
        "hours_covered":      hours,
    }


async def log_sync(source: str, status: str, detail: str = "") -> None:
    async with _get_db() as db:
        await db.execute(
            "INSERT INTO sync_log (source, status, detail) VALUES (?,?,?)",
            (source, status, detail),
        )
        await db.commit()


async def get_last_sync(source: str) -> dict | None:
    async with _get_db() as db:
        cur = await db.execute(
            "SELECT * FROM sync_log WHERE source=? ORDER BY created_at DESC LIMIT 1",
            (source,),
        )
        row = await cur.fetchone()
        return dict(row) if row else None


# ---------------------------------------------------------------------------
# Dashboard summary
# ---------------------------------------------------------------------------

async def get_health_summary() -> dict:
    """Aggregate summary for the dashboard and briefing."""
    async with _get_db() as db:
        # Latest wearable snapshot
        cur = await db.execute(
            "SELECT * FROM daily_metrics ORDER BY date DESC LIMIT 1"
        )
        metrics_row = await cur.fetchone()

        # Active conditions
        cur = await db.execute(
            "SELECT condition_name FROM conditions WHERE status='active'"
        )
        conditions = [r[0] for r in await cur.fetchall()]

        # Medications count
        cur = await db.execute("SELECT COUNT(*) as n FROM medications")
        med_count = (await cur.fetchone())["n"]

        # Current medications list — exclude inpatient/procedural-only and inactive meds
        _EXCLUDE_MED_KEYWORDS = (
            "PROPOFOL", "LIDOCAINE", "ONDANSETRON", "MEPERIDINE", "LABETALOL",
            "LACTATED RINGERS", "LACTATED RINGER", "SUTAB", "FENTANYL", "VERSED",
            "MIDAZOLAM", "DEXTROSE", "NORMAL SALINE", "MORPHINE", "HYDROMORPHONE",
        )
        exclude_clauses = " AND ".join(
            f"UPPER(name) NOT LIKE '%{kw}%'" for kw in _EXCLUDE_MED_KEYWORDS
        )
        cur = await db.execute(
            f"SELECT name, dosage, frequency, raw_text FROM medications "
            f"WHERE {exclude_clauses} "
            f"AND (raw_text IS NULL OR raw_text NOT LIKE '%(inactive)%') "
            f"LIMIT 30"
        )
        meds = [dict(r) for r in await cur.fetchall()]

        # Next upcoming appointment
        cur = await db.execute(
            "SELECT * FROM visits WHERE is_upcoming=1 ORDER BY visit_date ASC LIMIT 1"
        )
        next_appt = await cur.fetchone()

        # Recent test results — include actual values, deduplicated by name (most recent)
        # Panel-level rows have components JSON; component rows have individual values
        cur = await db.execute("""
            SELECT test_name, result_date, status, provider,
                   value, unit, reference_range, flag, components, order_id
            FROM test_results
            WHERE value IS NOT NULL OR components IS NOT NULL
            GROUP BY test_name
            HAVING result_date = MAX(result_date)
            ORDER BY result_date DESC, flag DESC, test_name
            LIMIT 200
        """)
        recent_tests = [dict(r) for r in await cur.fetchall()]

        # Also get a sorted list of all abnormal results (most recent value per test)
        cur = await db.execute("""
            SELECT test_name, result_date, value, unit, reference_range, flag, order_id
            FROM test_results
            WHERE flag IS NOT NULL AND flag != '' AND flag != 'Normal'
            GROUP BY test_name
            HAVING result_date = MAX(result_date)
            ORDER BY result_date DESC
            LIMIT 50
        """)
        abnormal_tests = [dict(r) for r in await cur.fetchall()]

        # Treatment goals
        cur = await db.execute("SELECT * FROM treatment_goals")
        goals = [dict(r) for r in await cur.fetchall()]

        # Last syncs
        cur = await db.execute(
            "SELECT source, MAX(created_at) as last_sync, status "
            "FROM sync_log GROUP BY source"
        )
        last_syncs = {r["source"]: {"last_sync": r["last_sync"], "status": r["status"]}
                      for r in await cur.fetchall()}

        # MyChart last sync time
        cur = await db.execute("SELECT MAX(synced_at) as t FROM mychart_pages")
        row = await cur.fetchone()
        mychart_last_sync = row["t"] if row else None

        # Recent ECG readings (summary, no waveform)
        cur = await db.execute(
            "SELECT id, reading_date, classification, avg_heart_rate, "
            "sample_count, duration_sec FROM ecg_readings "
            "ORDER BY reading_date DESC LIMIT 10"
        )
        ecg_readings = [dict(r) for r in await cur.fetchall()]

        # Latest BP reading
        cur = await db.execute(
            "SELECT * FROM bp_readings ORDER BY reading_date DESC LIMIT 1"
        )
        latest_bp = await cur.fetchone()

        # Recent BP history (last 7)
        cur = await db.execute(
            "SELECT reading_date, systolic, diastolic, pulse "
            "FROM bp_readings ORDER BY reading_date DESC LIMIT 7"
        )
        bp_history = [dict(r) for r in await cur.fetchall()]

    return {
        "metrics":          dict(metrics_row) if metrics_row else None,
        "conditions":       conditions,
        "medication_count": med_count,
        "medications":      meds,
        "next_appointment": dict(next_appt) if next_appt else None,
        "recent_tests":     recent_tests,
        "abnormal_tests":   abnormal_tests,
        "treatment_goals":  goals,
        "last_syncs":       last_syncs,
        "mychart_last_sync": mychart_last_sync,
        "ecg_readings":     ecg_readings,
        "latest_bp":        dict(latest_bp) if latest_bp else None,
        "bp_history":       bp_history,
    }
