"""N2: SQLite hybrid index for active JARVIS state.

Provides a queryable, concurrency-safe SQLite index alongside the
append-only JSONL audit trail. Raw JSONL/JSON files are never replaced —
the SQLite index is a secondary, rebuildable query layer only.

Design principles:
- JSONL is the source of truth (audit, history, raw facts)
- SQLite is for fast queries on active state (approvals, memory, agents, zones)
- WAL mode for concurrent reads
- Schema versioning so migrations don't drop data
- index.rebuild() recreates from JSONL if SQLite is ever lost or corrupt
"""
from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator

_INDEX_ROOT = Path("data/index")
_DB_PATH = _INDEX_ROOT / "jarvis_index.db"
_SCHEMA_VERSION = 1


def _ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS approvals (
    request_id TEXT PRIMARY KEY,
    actor TEXT NOT NULL,
    action_class TEXT NOT NULL,
    status TEXT NOT NULL,
    domain TEXT DEFAULT '',
    lane TEXT DEFAULT '',
    room TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT DEFAULT '',
    second_factor_required INTEGER DEFAULT 0,
    raw_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS memory_entries (
    entry_id TEXT PRIMARY KEY,
    owner TEXT NOT NULL,
    title TEXT NOT NULL,
    project TEXT DEFAULT '',
    tags TEXT DEFAULT '[]',
    approval_status TEXT DEFAULT 'active',
    sensitivity TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT DEFAULT '',
    raw_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS trust_zones (
    zone_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    status TEXT NOT NULL,
    authority_stage TEXT NOT NULL,
    actor TEXT DEFAULT '',
    raw_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agents (
    agent_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    state TEXT NOT NULL,
    role TEXT DEFAULT '',
    zone TEXT DEFAULT '',
    arena TEXT DEFAULT '',
    authority_stage TEXT DEFAULT '',
    paused INTEGER DEFAULT 0,
    proposed_by TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT DEFAULT '',
    raw_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS workstream_items (
    item_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    status TEXT NOT NULL,
    owner TEXT DEFAULT '',
    priority TEXT DEFAULT 'normal',
    domain TEXT DEFAULT '',
    created_at TEXT DEFAULT '',
    raw_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_approvals_status ON approvals(status);
CREATE INDEX IF NOT EXISTS idx_approvals_actor ON approvals(actor);
CREATE INDEX IF NOT EXISTS idx_memory_owner ON memory_entries(owner);
CREATE INDEX IF NOT EXISTS idx_memory_status ON memory_entries(approval_status);
CREATE INDEX IF NOT EXISTS idx_agents_state ON agents(state);
CREATE INDEX IF NOT EXISTS idx_workstream_status ON workstream_items(status);
"""


class SQLiteIndex:
    """SQLite index layer for JARVIS active state.

    The JSONL audit trail is never touched — this is a secondary, rebuildable
    query index only.  Call rebuild() to regenerate from source JSON files.
    """

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or _DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    @contextmanager
    def _conn(self) -> Generator[sqlite3.Connection, None, None]:
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._conn() as conn:
            conn.executescript(SCHEMA_SQL)
            cur = conn.execute("SELECT MAX(version) FROM schema_version")
            row = cur.fetchone()
            current = row[0] if row and row[0] is not None else 0
            if current < _SCHEMA_VERSION:
                conn.execute(
                    "INSERT OR REPLACE INTO schema_version (version, applied_at) VALUES (?, ?)",
                    (_SCHEMA_VERSION, _ts()),
                )

    def schema_version(self) -> int:
        with self._conn() as conn:
            cur = conn.execute("SELECT MAX(version) FROM schema_version")
            row = cur.fetchone()
            return row[0] if row and row[0] is not None else 0

    # ------------------------------------------------------------------
    # Upsert methods (called by stores after writes)
    # ------------------------------------------------------------------

    def upsert_approval(self, record: dict) -> None:
        with self._conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO approvals
                  (request_id, actor, action_class, status, domain, lane, room,
                   created_at, updated_at, second_factor_required, raw_json)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """, (
                record.get("request_id", ""),
                record.get("actor", ""),
                record.get("action_class", ""),
                record.get("status", ""),
                record.get("domain", ""),
                record.get("lane", ""),
                record.get("room", ""),
                record.get("created_at", ""),
                record.get("updated_at", ""),
                int(bool(record.get("second_factor_required"))),
                json.dumps(record),
            ))

    def upsert_memory_entry(self, record: dict) -> None:
        with self._conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO memory_entries
                  (entry_id, owner, title, project, tags, approval_status,
                   sensitivity, created_at, updated_at, raw_json)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (
                record.get("entry_id", ""),
                record.get("owner", ""),
                record.get("title", ""),
                record.get("project", ""),
                json.dumps(record.get("tags", [])),
                record.get("approval_status", "active"),
                record.get("sensitivity", ""),
                record.get("created_at", ""),
                record.get("updated_at", ""),
                json.dumps(record),
            ))

    def upsert_trust_zone(self, record: dict) -> None:
        with self._conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO trust_zones
                  (zone_id, name, status, authority_stage, actor, raw_json)
                VALUES (?,?,?,?,?,?)
            """, (
                record.get("zone_id", ""),
                record.get("name", ""),
                record.get("status", "inactive"),
                record.get("authority_stage", "observe"),
                record.get("actor", ""),
                json.dumps(record),
            ))

    def upsert_agent(self, record: dict) -> None:
        with self._conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO agents
                  (agent_id, name, state, role, zone, arena, authority_stage,
                   paused, proposed_by, created_at, updated_at, raw_json)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                record.get("agent_id", ""),
                record.get("name", ""),
                record.get("state", "proposed"),
                record.get("role", ""),
                record.get("zone", ""),
                record.get("arena", ""),
                record.get("authority_stage", ""),
                int(bool(record.get("paused"))),
                record.get("proposed_by", ""),
                record.get("created_at", ""),
                record.get("updated_at", ""),
                json.dumps(record),
            ))

    def upsert_workstream_item(self, record: dict) -> None:
        with self._conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO workstream_items
                  (item_id, title, status, owner, priority, domain, created_at, raw_json)
                VALUES (?,?,?,?,?,?,?,?)
            """, (
                record.get("item_id", record.get("id", "")),
                record.get("title", ""),
                record.get("status", "open"),
                record.get("owner", ""),
                record.get("priority", "normal"),
                record.get("domain", ""),
                record.get("created_at", ""),
                json.dumps(record),
            ))

    # ------------------------------------------------------------------
    # Query methods
    # ------------------------------------------------------------------

    def query_approvals(
        self,
        status: str | None = None,
        actor: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        clauses = []
        params: list[Any] = []
        if status:
            clauses.append("status = ?"); params.append(status)
        if actor:
            clauses.append("actor = ?"); params.append(actor)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        with self._conn() as conn:
            cur = conn.execute(
                f"SELECT raw_json FROM approvals {where} ORDER BY created_at DESC LIMIT ?",
                params + [limit],
            )
            return [json.loads(row[0]) for row in cur.fetchall()]

    def query_memory(
        self,
        owner: str | None = None,
        approval_status: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        clauses = []
        params: list[Any] = []
        if owner:
            clauses.append("owner = ?"); params.append(owner)
        if approval_status:
            clauses.append("approval_status = ?"); params.append(approval_status)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        with self._conn() as conn:
            cur = conn.execute(
                f"SELECT raw_json FROM memory_entries {where} ORDER BY created_at DESC LIMIT ?",
                params + [limit],
            )
            return [json.loads(row[0]) for row in cur.fetchall()]

    def query_agents(
        self,
        state: str | None = None,
        paused: bool | None = None,
        limit: int = 100,
    ) -> list[dict]:
        clauses = []
        params: list[Any] = []
        if state:
            clauses.append("state = ?"); params.append(state)
        if paused is not None:
            clauses.append("paused = ?"); params.append(int(paused))
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        with self._conn() as conn:
            cur = conn.execute(
                f"SELECT raw_json FROM agents {where} ORDER BY created_at DESC LIMIT ?",
                params + [limit],
            )
            return [json.loads(row[0]) for row in cur.fetchall()]

    def query_workstream(
        self,
        status: str | None = None,
        owner: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        clauses = []
        params: list[Any] = []
        if status:
            clauses.append("status = ?"); params.append(status)
        if owner:
            clauses.append("owner = ?"); params.append(owner)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        with self._conn() as conn:
            cur = conn.execute(
                f"SELECT raw_json FROM workstream_items {where} ORDER BY created_at DESC LIMIT ?",
                params + [limit],
            )
            return [json.loads(row[0]) for row in cur.fetchall()]

    # ------------------------------------------------------------------
    # Rebuild from JSON source files (makes SQLite fully rebuildable)
    # ------------------------------------------------------------------

    def rebuild(
        self,
        *,
        approvals_path: Path | None = None,
        memory_path: Path | None = None,
        agents_path: Path | None = None,
        workstream_path: Path | None = None,
        trust_zones_path: Path | None = None,
        root: Path | None = None,
    ) -> dict[str, int]:
        """Rebuild all index tables from source JSON/JSONL files.

        Returns counts of records indexed per table.
        """
        r = root or Path("data")
        counts: dict[str, int] = {}

        def _load_json(p: Path) -> list[dict]:
            if not p or not p.exists():
                return []
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                return data if isinstance(data, list) else []
            except Exception:
                return []

        # Approvals
        ap = approvals_path or r / "approvals" / "approvals.json"
        for record in _load_json(ap):
            try:
                self.upsert_approval(record)
            except Exception:
                pass
        with self._conn() as conn:
            counts["approvals"] = conn.execute("SELECT COUNT(*) FROM approvals").fetchone()[0]

        # Memory
        mp = memory_path or r / "memory" / "entries.json"
        for record in _load_json(mp):
            try:
                self.upsert_memory_entry(record)
            except Exception:
                pass
        with self._conn() as conn:
            counts["memory_entries"] = conn.execute("SELECT COUNT(*) FROM memory_entries").fetchone()[0]

        # Agents
        agp = agents_path or r / "foundry" / "agents.json"
        for record in _load_json(agp):
            try:
                self.upsert_agent(record)
            except Exception:
                pass
        with self._conn() as conn:
            counts["agents"] = conn.execute("SELECT COUNT(*) FROM agents").fetchone()[0]

        # Workstream
        wsp = workstream_path or r / "workstreams" / "items.json"
        for record in _load_json(wsp):
            try:
                self.upsert_workstream_item(record)
            except Exception:
                pass
        with self._conn() as conn:
            counts["workstream_items"] = conn.execute("SELECT COUNT(*) FROM workstream_items").fetchone()[0]

        # Trust zones
        tzp = trust_zones_path or r / "trust" / "trust_zones.json"
        for record in _load_json(tzp):
            try:
                self.upsert_trust_zone(record)
            except Exception:
                pass
        with self._conn() as conn:
            counts["trust_zones"] = conn.execute("SELECT COUNT(*) FROM trust_zones").fetchone()[0]

        return counts

    def health(self) -> dict[str, Any]:
        """Return index health: table counts + schema version + db path."""
        with self._conn() as conn:
            tables = ["approvals", "memory_entries", "trust_zones", "agents", "workstream_items"]
            counts = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}
        return {
            "schema_version": self.schema_version(),
            "db_path": str(self.db_path),
            "wal_mode": True,
            "concurrency_safe": True,
            "rebuildable_from_jsonl": True,
            "table_counts": counts,
            "source": "sqlite_index",
        }
