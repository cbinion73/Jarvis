"""Phase N: Infrastructure + Hardware tests.

N1  BLOCKED (HOME_ASSISTANT_URL / TOKEN / entity map not available).
N2  SQLite hybrid index: queryable, concurrency-safe, rebuildable from JSONL.
N3  BLOCKED (perception hardware).
N4  BLOCKED (device network access).
N5  BLOCKED (hardware procurement).

N2 is the only unblocked item this session.
"""
from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path

# FastAPI stub.
if "fastapi" not in sys.modules:
    _fs = types.ModuleType("fastapi")
    _rs = types.ModuleType("fastapi.responses")
    _ss = types.ModuleType("fastapi.staticfiles")
    _uv = types.ModuleType("uvicorn")

    class _Route:
        def __init__(self, path, methods, endpoint):
            self.path = path; self.methods = methods; self.endpoint = endpoint

    class _Router:
        def __init__(self): self.routes = []

    class _FastAPI:
        def __init__(self, *a, **kw): self.router = _Router()
        def _reg(self, path, methods):
            def dec(fn): self.router.routes.append(_Route(path, methods, fn)); return fn
            return dec
        def get(self, path, *a, **kw):    return self._reg(path, {"GET"})
        def post(self, path, *a, **kw):   return self._reg(path, {"POST"})
        def put(self, path, *a, **kw):    return self._reg(path, {"PUT"})
        def patch(self, path, *a, **kw):  return self._reg(path, {"PATCH"})
        def delete(self, path, *a, **kw): return self._reg(path, {"DELETE"})
        def websocket(self, path, *a, **kw): return self._reg(path, {"WS"})
        def on_event(self, *a, **kw):     return lambda fn: fn
        def mount(self, *a, **kw):        pass
        def add_middleware(self, *a, **kw): pass

    class _HTTPException(Exception):
        def __init__(self, status_code=500, detail=""):
            super().__init__(detail); self.status_code = status_code; self.detail = detail

    _rs.JSONResponse = dict
    _fs.FastAPI = _FastAPI
    _fs.HTTPException = _HTTPException
    _fs.Request = object
    _fs.BackgroundTasks = object
    _fs.File = lambda *a, **kw: None
    _fs.Form = lambda *a, **kw: None
    _fs.Query = lambda *a, **kw: None
    _fs.UploadFile = object
    _fs.WebSocket = object
    _fs.WebSocketDisconnect = Exception
    _fs.responses = _rs
    _fs.staticfiles = _ss
    _uv.run = lambda *a, **kw: None

    for _m, _s in (
        ("fastapi", _fs),
        ("fastapi.responses", _rs),
        ("fastapi.staticfiles", _ss),
        ("fastapi.middleware.cors", types.ModuleType("fastapi.middleware.cors")),
        ("uvicorn", _uv),
    ):
        sys.modules.setdefault(_m, _s)

import json
import tempfile

SERVICE = Path(__file__).parent.parent / "jarvis" / "service.py"


# ── N1 / N3 / N4 / N5: BLOCKED items ─────────────────────────────────────────

class TestNBlockedItems(unittest.TestCase):
    """Document which N items are BLOCKED and why."""

    def test_n1_blocked_home_assistant_credentials(self):
        """N1: BLOCKED — HOME_ASSISTANT_URL and HOME_ASSISTANT_TOKEN not provisioned."""
        import os
        ha_url = os.environ.get("HOME_ASSISTANT_URL", "")
        self.assertEqual(ha_url, "",
                         "If HOME_ASSISTANT_URL is set, N1 can be implemented — update this test.")

    def test_n3_blocked_perception_hardware(self):
        """N3: BLOCKED — perception hardware (cameras, presence sensors) not installed."""
        self.skipTest("N3 BLOCKED: perception hardware not available. "
                      "Unblock: procure porch/garage/room presence sensors.")

    def test_n4_blocked_workshop_device_access(self):
        """N4: BLOCKED — Bambu/Cricut/resin devices not on accessible network."""
        self.skipTest("N4 BLOCKED: workshop device network access not available. "
                      "Unblock: expose device status API on local network.")

    def test_n5_blocked_hardware_procurement(self):
        """N5: BLOCKED — always-on host / NAS / UPS not procured."""
        self.skipTest("N5 BLOCKED: hardware not procured. "
                      "Unblock: set up dedicated always-on host with NAS.")


# ── N2: SQLite hybrid index ────────────────────────────────────────────────────

class TestN2SQLiteIndex(unittest.TestCase):
    """N2: SQLite index — queryable, concurrency-safe, rebuildable, JSONL-preserving."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        from jarvis.sqlite_index import SQLiteIndex
        self.idx = SQLiteIndex(db_path=Path(self.tmp.name) / "test_index.db")

    def tearDown(self):
        self.tmp.cleanup()

    # Schema + health
    def test_schema_version_initialized(self):
        self.assertGreaterEqual(self.idx.schema_version(), 1)

    def test_health_returns_expected_fields(self):
        health = self.idx.health()
        self.assertIn("schema_version", health)
        self.assertIn("db_path", health)
        self.assertTrue(health["wal_mode"])
        self.assertTrue(health["concurrency_safe"])
        self.assertTrue(health["rebuildable_from_jsonl"])
        self.assertIn("table_counts", health)

    def test_table_counts_all_present(self):
        tables = self.idx.health()["table_counts"]
        for t in ("approvals", "memory_entries", "trust_zones", "agents", "workstream_items"):
            self.assertIn(t, tables)

    # Approvals
    def test_upsert_and_query_approval(self):
        self.idx.upsert_approval({
            "request_id": "req-001",
            "actor": "jarvis",
            "action_class": "send_message",
            "status": "pending",
            "domain": "family",
            "lane": "household",
            "room": "living-room",
            "created_at": "2026-06-10T00:00:00Z",
        })
        results = self.idx.query_approvals(status="pending")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["request_id"], "req-001")

    def test_approval_filter_by_actor(self):
        self.idx.upsert_approval({
            "request_id": "req-a", "actor": "jarvis", "action_class": "t",
            "status": "pending", "created_at": "2026-06-10T00:00:00Z",
        })
        self.idx.upsert_approval({
            "request_id": "req-b", "actor": "chris", "action_class": "t",
            "status": "pending", "created_at": "2026-06-10T00:00:01Z",
        })
        jarvis_results = self.idx.query_approvals(actor="jarvis")
        self.assertEqual(len(jarvis_results), 1)
        self.assertEqual(jarvis_results[0]["request_id"], "req-a")

    def test_approval_upsert_updates_existing(self):
        record = {
            "request_id": "req-001", "actor": "jarvis", "action_class": "t",
            "status": "pending", "created_at": "2026-06-10T00:00:00Z",
        }
        self.idx.upsert_approval(record)
        record["status"] = "approved"
        self.idx.upsert_approval(record)
        results = self.idx.query_approvals(status="approved")
        self.assertEqual(len(results), 1)

    # Memory entries
    def test_upsert_and_query_memory(self):
        self.idx.upsert_memory_entry({
            "entry_id": "mem-001",
            "owner": "chris",
            "title": "Test memory entry",
            "project": "jarvis",
            "tags": ["test"],
            "approval_status": "active",
            "created_at": "2026-06-10T00:00:00Z",
        })
        results = self.idx.query_memory(owner="chris")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["entry_id"], "mem-001")

    def test_memory_filter_by_approval_status(self):
        self.idx.upsert_memory_entry({
            "entry_id": "m-a", "owner": "chris", "title": "Active",
            "approval_status": "active", "created_at": "2026-06-10T00:00:00Z",
        })
        self.idx.upsert_memory_entry({
            "entry_id": "m-b", "owner": "chris", "title": "Retired",
            "approval_status": "retired", "created_at": "2026-06-10T00:00:01Z",
        })
        active = self.idx.query_memory(approval_status="active")
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]["entry_id"], "m-a")

    # Agents
    def test_upsert_and_query_agent(self):
        self.idx.upsert_agent({
            "agent_id": "agent-001",
            "name": "ResearchAgent",
            "state": "promoted",
            "role": "research",
            "zone": "household",
            "arena": "knowledge",
            "authority_stage": "suggest",
            "created_at": "2026-06-10T00:00:00Z",
        })
        results = self.idx.query_agents(state="promoted")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "ResearchAgent")

    def test_agent_filter_paused(self):
        self.idx.upsert_agent({
            "agent_id": "a-1", "name": "AgentA", "state": "promoted",
            "paused": True, "created_at": "2026-06-10T00:00:00Z",
        })
        self.idx.upsert_agent({
            "agent_id": "a-2", "name": "AgentB", "state": "promoted",
            "paused": False, "created_at": "2026-06-10T00:00:01Z",
        })
        paused = self.idx.query_agents(paused=True)
        self.assertEqual(len(paused), 1)
        self.assertEqual(paused[0]["agent_id"], "a-1")

    # Workstream
    def test_upsert_and_query_workstream(self):
        self.idx.upsert_workstream_item({
            "item_id": "ws-001",
            "title": "Build SQLite index",
            "status": "in_progress",
            "owner": "chris",
            "created_at": "2026-06-10T00:00:00Z",
        })
        results = self.idx.query_workstream(status="in_progress")
        self.assertEqual(len(results), 1)

    # Rebuild
    def test_rebuild_from_json_files(self):
        """rebuild() reads source JSON files and indexes them."""
        tmp2 = tempfile.TemporaryDirectory()
        data_root = Path(tmp2.name)
        approvals_dir = data_root / "approvals"
        approvals_dir.mkdir()
        (approvals_dir / "approvals.json").write_text(json.dumps([{
            "request_id": "rebuilt-req-001",
            "actor": "jarvis",
            "action_class": "notify",
            "status": "pending",
            "created_at": "2026-06-10T00:00:00Z",
        }]))
        counts = self.idx.rebuild(root=data_root)
        self.assertIn("approvals", counts)
        self.assertGreaterEqual(counts["approvals"], 1)
        results = self.idx.query_approvals(status="pending")
        self.assertTrue(any(r["request_id"] == "rebuilt-req-001" for r in results))
        tmp2.cleanup()

    def test_rebuild_missing_files_graceful(self):
        """rebuild() handles missing source files without error."""
        tmp2 = tempfile.TemporaryDirectory()
        counts = self.idx.rebuild(root=Path(tmp2.name))
        # All counts should be 0 (no source files)
        for count in counts.values():
            self.assertEqual(count, 0)
        tmp2.cleanup()

    # Service endpoints
    def test_index_endpoints_in_service(self):
        src = SERVICE.read_text(encoding="utf-8")
        self.assertIn('"/api/index/health"', src)
        self.assertIn('"/api/index/rebuild"', src)
        self.assertIn('"/api/index/query/approvals"', src)
        self.assertIn('"/api/index/query/agents"', src)
        self.assertIn('"/api/index/query/memory"', src)

    def test_trust_zone_upsert_and_health(self):
        self.idx.upsert_trust_zone({
            "zone_id": "zone-home",
            "name": "Home",
            "status": "active",
            "authority_stage": "suggest",
            "actor": "chris",
        })
        health = self.idx.health()
        self.assertGreaterEqual(health["table_counts"]["trust_zones"], 1)


if __name__ == "__main__":
    unittest.main()
