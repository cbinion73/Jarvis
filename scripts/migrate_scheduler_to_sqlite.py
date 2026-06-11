#!/usr/bin/env python3
"""One-time migration: import active scheduler queue items from JSONL into SQLite.

Usage:
    python3 scripts/migrate_scheduler_to_sqlite.py [--dry-run]

What it does
------------
1. Opens ~/.jarvis/scheduler/queue.jsonl and imports any active (queued/running)
   items into ~/.jarvis/scheduler/scheduler.db.
2. Archives queue_state_log.jsonl → queue_state_log.jsonl.bak (does NOT delete
   it in case manual inspection is needed).
3. Archives queue.jsonl → queue.jsonl.bak.
4. Prints a summary.

The 111 GB queue_state_log.jsonl is NOT imported — only current active state
from queue.jsonl is preserved.  Historical snapshots are intentionally discarded.

Safety
------
- Dry-run mode prints what would happen without touching any files.
- If scheduler.db already has items the script exits cleanly (idempotent).
- The .bak files can be deleted manually after confirming the scheduler runs correctly.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

SCHEDULER_DIR = Path.home() / ".jarvis" / "scheduler"
QUEUE_JSONL = SCHEDULER_DIR / "queue.jsonl"
STATE_LOG = SCHEDULER_DIR / "queue_state_log.jsonl"
DB_PATH = SCHEDULER_DIR / "scheduler.db"

ACTIVE_STATUSES = {"queued", "running"}

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;

CREATE TABLE IF NOT EXISTS queue_items (
    item_id      TEXT PRIMARY KEY,
    agent_id     TEXT NOT NULL,
    status       TEXT NOT NULL,
    queued_at    TEXT,
    started_at   TEXT,
    completed_at TEXT,
    payload_json TEXT,
    result_json  TEXT,
    error_text   TEXT,
    updated_at   TEXT,
    item_json    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS queue_events (
    event_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id    TEXT NOT NULL,
    event_type TEXT NOT NULL,
    created_at TEXT NOT NULL,
    event_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_qi_status      ON queue_items(status);
CREATE INDEX IF NOT EXISTS idx_qe_created_at  ON queue_events(created_at);
"""

UPSERT_ITEM = """
INSERT INTO queue_items
    (item_id, agent_id, status, queued_at, started_at, completed_at,
     payload_json, result_json, error_text, updated_at, item_json)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), ?)
ON CONFLICT(item_id) DO UPDATE SET
    status       = excluded.status,
    started_at   = excluded.started_at,
    completed_at = excluded.completed_at,
    result_json  = excluded.result_json,
    error_text   = excluded.error_text,
    updated_at   = excluded.updated_at,
    item_json    = excluded.item_json
"""


def _open_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    for stmt in SCHEMA.split(";"):
        stmt = stmt.strip()
        if stmt:
            conn.execute(stmt)
    conn.commit()
    return conn


def _read_active_items(jsonl_path: Path) -> list[dict]:
    if not jsonl_path.exists():
        return []
    items = []
    skipped = 0
    for line in jsonl_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            if data.get("status") in ACTIVE_STATUSES:
                items.append(data)
            else:
                skipped += 1
        except Exception:
            skipped += 1
    print(f"  queue.jsonl: {len(items)} active items found, {skipped} skipped (terminal/invalid)")
    return items


def _import_items(conn: sqlite3.Connection, items: list[dict], dry_run: bool) -> int:
    if not items:
        return 0
    imported = 0
    for data in items:
        # Reset running → queued (zombie recovery)
        if data.get("status") == "running":
            data["status"] = "queued"
            data["started_at"] = ""
        item_id = data.get("item_id", "")
        if not item_id:
            continue
        if not dry_run:
            conn.execute(
                UPSERT_ITEM,
                (
                    item_id,
                    data.get("agent_id", "unknown"),
                    data["status"],
                    data.get("queued_at"),
                    data.get("started_at") or None,
                    data.get("completed_at") or None,
                    json.dumps(data.get("payload", {})),
                    json.dumps(data.get("result", {})),
                    data.get("error") or None,
                    json.dumps(data),
                ),
            )
        imported += 1
    if not dry_run:
        conn.commit()
    return imported


def _archive(path: Path, dry_run: bool) -> None:
    if not path.exists():
        return
    bak = path.with_suffix(path.suffix + ".bak")
    size_mb = path.stat().st_size / (1024 * 1024)
    if dry_run:
        print(f"  [dry-run] would rename {path.name} ({size_mb:.1f} MB) → {bak.name}")
    else:
        path.rename(bak)
        print(f"  Archived {path.name} ({size_mb:.1f} MB) → {bak.name}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Preview without modifying files")
    args = parser.parse_args()

    dry_run: bool = args.dry_run
    if dry_run:
        print("DRY-RUN mode — no files will be modified\n")

    # Check if migration already done
    if DB_PATH.exists():
        conn = sqlite3.connect(str(DB_PATH))
        count = conn.execute("SELECT COUNT(*) FROM queue_items").fetchone()[0]
        conn.close()
        if count > 0:
            print(f"scheduler.db already contains {count} item(s) — migration already complete.")
            sys.exit(0)

    print(f"Scheduler directory: {SCHEDULER_DIR}")

    # Read active items from queue.jsonl
    print("\n[1/4] Reading active items from queue.jsonl…")
    items = _read_active_items(QUEUE_JSONL)

    # Open / create SQLite DB
    print("\n[2/4] Initialising scheduler.db…")
    if dry_run:
        print(f"  [dry-run] would create {DB_PATH}")
        conn = None
    else:
        conn = _open_db(DB_PATH)
        print(f"  Created {DB_PATH}")

    # Import items
    print("\n[3/4] Importing active items into SQLite…")
    imported = _import_items(conn or sqlite3.connect(":memory:"), items, dry_run)
    if dry_run:
        print(f"  [dry-run] would import {imported} item(s)")
    else:
        print(f"  Imported {imported} item(s)")

    # Archive old files
    print("\n[4/4] Archiving legacy JSONL files…")
    _archive(QUEUE_JSONL, dry_run)
    _archive(STATE_LOG, dry_run)

    print("\n✓ Migration complete.")
    if not dry_run:
        print("  You can delete the .bak files after confirming the scheduler runs correctly.")
        print(f"  DB size: {DB_PATH.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
