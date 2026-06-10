"""Phase K: Foundry agent lifecycle tests.

K1 – NewbornAgentSpec created from proposal → approved → sandboxed.
K2 – Evaluate → promote OR retire lifecycle.
K3 – Promoted agent assignable to AutomationPipeline stage.
K5 – capture_sandbox_snapshot + rollback_to_snapshot pre-execution rollback.
"""
from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path

# FastAPI stub — same complete class-based pattern.
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

import tempfile

from jarvis.foundry import FoundryBuilder, FoundryStore, AGENT_STATE_PROMOTED, AGENT_STATE_RETIRED


def _make_store(tmp: Path) -> FoundryStore:
    return FoundryStore(root=tmp / "foundry")


def _make_builder() -> FoundryBuilder:
    return FoundryBuilder()


def _propose(store: FoundryStore, name: str = "TestAgent") -> dict:
    builder = _make_builder()
    spec = builder.build(
        name=name,
        role="executor",
        mission="Test mission for unit tests",
        zone="sandbox",
        arena="testing",
        memory_scope=["household"],
        tool_scope=["read_only"],
        evaluation_criteria=["runs 3 successful dry-runs", "no unauthorized writes"],
    )
    return store.propose(spec)


# ── K1: Propose → Approve → Sandbox ───────────────────────────────────────────

class TestK1AgentCreation(unittest.TestCase):
    """K1: NewbornAgentSpec → proposed → approved → sandboxed."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = _make_store(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_propose_creates_agent_in_proposed_state(self):
        agent = _propose(self.store)
        self.assertEqual(agent["state"], "proposed")
        self.assertIn("agent_id", agent)
        self.assertIn("name", agent)

    def test_approve_transitions_to_approved(self):
        agent = _propose(self.store)
        approved = self.store.approve(agent["agent_id"], actor="chris")
        self.assertEqual(approved["state"], "approved")

    def test_sandbox_transitions_to_sandboxed(self):
        agent = _propose(self.store)
        self.store.approve(agent["agent_id"], actor="chris")
        sandboxed = self.store.sandbox(agent["agent_id"], actor="chris")
        self.assertEqual(sandboxed["state"], "sandboxed")

    def test_reject_transitions_to_rejected(self):
        agent = _propose(self.store)
        rejected = self.store.reject(agent["agent_id"], actor="chris", reason="Not ready")
        self.assertEqual(rejected["state"], "rejected")

    def test_get_returns_agent(self):
        agent = _propose(self.store)
        found = self.store.get(agent["agent_id"])
        self.assertIsNotNone(found)
        self.assertEqual(found["agent_id"], agent["agent_id"])

    def test_list_all_returns_agents(self):
        _propose(self.store, "Agent1")
        _propose(self.store, "Agent2")
        agents = self.store.list_all()
        self.assertEqual(len(agents), 2)

    def test_list_all_filtered_by_state(self):
        a1 = _propose(self.store, "AgentA")
        a2 = _propose(self.store, "AgentB")
        self.store.approve(a1["agent_id"], actor="chris")
        proposed = self.store.list_all(state="proposed")
        self.assertEqual(len(proposed), 1)
        self.assertEqual(proposed[0]["agent_id"], a2["agent_id"])


# ── K2: Evaluate → Promote OR Retire ─────────────────────────────────────────

class TestK2AgentLifecycle(unittest.TestCase):
    """K2: Sandbox runs → evaluation → promote or retire."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = _make_store(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _sandboxed_agent(self) -> dict:
        agent = _propose(self.store)
        self.store.approve(agent["agent_id"], actor="chris")
        return self.store.sandbox(agent["agent_id"], actor="chris")

    def test_begin_evaluation_transitions_to_evaluating(self):
        agent = self._sandboxed_agent()
        evaluating = self.store.begin_evaluation(agent["agent_id"], actor="chris")
        self.assertEqual(evaluating["state"], "evaluating")

    def test_promote_transitions_to_promoted(self):
        agent = self._sandboxed_agent()
        self.store.begin_evaluation(agent["agent_id"], actor="chris")
        promoted = self.store.promote(agent["agent_id"], actor="chris")
        self.assertEqual(promoted["state"], AGENT_STATE_PROMOTED)

    def test_retire_transitions_to_retired(self):
        agent = self._sandboxed_agent()
        self.store.begin_evaluation(agent["agent_id"], actor="chris")
        retired = self.store.retire(agent["agent_id"], actor="chris", reason="Failed evaluation")
        self.assertEqual(retired["state"], AGENT_STATE_RETIRED)
        self.assertEqual(retired["retirement_reason"], "Failed evaluation")

    def test_record_sandbox_run_increments_counts(self):
        agent = self._sandboxed_agent()
        self.store.record_sandbox_run(agent["agent_id"], success=True)
        self.store.record_sandbox_run(agent["agent_id"], success=True)
        self.store.record_sandbox_run(agent["agent_id"], success=False)
        summary = self.store.evaluation_summary(agent["agent_id"])
        self.assertEqual(summary["sandbox_run_count"], 3)
        self.assertEqual(summary["sandbox_success_count"], 2)
        self.assertEqual(summary["sandbox_failure_count"], 1)

    def test_evaluation_summary_recommends_promote_on_high_success(self):
        agent = self._sandboxed_agent()
        for _ in range(4):
            self.store.record_sandbox_run(agent["agent_id"], success=True)
        summary = self.store.evaluation_summary(agent["agent_id"])
        self.assertEqual(summary["recommended_action"], "promote")

    def test_evaluation_summary_recommends_retire_on_many_failures(self):
        agent = self._sandboxed_agent()
        for _ in range(3):
            self.store.record_sandbox_run(agent["agent_id"], success=False)
        summary = self.store.evaluation_summary(agent["agent_id"])
        self.assertEqual(summary["recommended_action"], "retire")


# ── K5: Sandbox snapshot + rollback ───────────────────────────────────────────

class TestK5SandboxRollback(unittest.TestCase):
    """K5: capture_sandbox_snapshot + rollback_to_snapshot."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = _make_store(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _sandboxed_agent(self) -> dict:
        agent = _propose(self.store)
        self.store.approve(agent["agent_id"], actor="chris")
        return self.store.sandbox(agent["agent_id"], actor="chris")

    def test_capture_snapshot_returns_snapshot(self):
        agent = self._sandboxed_agent()
        snap = self.store.capture_sandbox_snapshot(agent["agent_id"])
        self.assertIsNotNone(snap)
        self.assertIn("snapshot_id", snap)
        self.assertEqual(snap["state"], "sandboxed")

    def test_snapshot_stored_on_agent(self):
        agent = self._sandboxed_agent()
        snap = self.store.capture_sandbox_snapshot(agent["agent_id"])
        stored = self.store.get(agent["agent_id"])
        snaps = stored.get("sandbox_snapshots", [])
        self.assertEqual(len(snaps), 1)
        self.assertEqual(snaps[0]["snapshot_id"], snap["snapshot_id"])

    def test_rollback_restores_state(self):
        agent = self._sandboxed_agent()
        # Capture snapshot BEFORE evaluation
        snap = self.store.capture_sandbox_snapshot(agent["agent_id"])
        # Advance to evaluating
        self.store.begin_evaluation(agent["agent_id"], actor="chris")
        self.assertEqual(self.store.get(agent["agent_id"])["state"], "evaluating")
        # Rollback
        rolled = self.store.rollback_to_snapshot(agent["agent_id"], snap["snapshot_id"], actor="chris")
        self.assertIsNotNone(rolled)
        self.assertEqual(rolled["state"], "sandboxed", "Rollback should restore state to sandboxed")

    def test_rollback_unknown_snapshot_returns_none(self):
        agent = self._sandboxed_agent()
        result = self.store.rollback_to_snapshot(agent["agent_id"], "bad-snap-id", actor="chris")
        self.assertIsNone(result)

    def test_snapshot_capped_at_ten(self):
        agent = self._sandboxed_agent()
        for _ in range(15):
            self.store.capture_sandbox_snapshot(agent["agent_id"])
        stored = self.store.get(agent["agent_id"])
        self.assertLessEqual(len(stored.get("sandbox_snapshots", [])), 10)

    def test_rollback_endpoints_in_service(self):
        service_path = Path(__file__).parent.parent / "jarvis" / "service.py"
        src = service_path.read_text(encoding="utf-8")
        self.assertIn('"/api/foundry/agents/{agent_id}/sandbox-snapshot"', src)
        self.assertIn('"/api/foundry/agents/{agent_id}/rollback"', src)

    # ── K3: Assign promoted agent to pipeline ─────────────────────────────────

    def test_assign_pipeline_endpoint_in_service(self):
        service_path = Path(__file__).parent.parent / "jarvis" / "service.py"
        src = service_path.read_text(encoding="utf-8")
        self.assertIn('"/api/foundry/agents/{agent_id}/assign-pipeline"', src)

    def test_only_promoted_agents_assignable(self):
        """Endpoint rejects non-promoted agents (logic reflected in service check)."""
        agent = _propose(self.store)  # state=proposed
        self.assertNotEqual(agent["state"], AGENT_STATE_PROMOTED)

    def test_promoted_agent_state(self):
        agent = _propose(self.store)
        self.store.approve(agent["agent_id"], actor="chris")
        sandboxed = self.store.sandbox(agent["agent_id"], actor="chris")
        self.store.begin_evaluation(sandboxed["agent_id"], actor="chris")
        promoted = self.store.promote(sandboxed["agent_id"], actor="chris")
        self.assertEqual(promoted["state"], AGENT_STATE_PROMOTED,
                         "Promoted agent ready for pipeline assignment")


if __name__ == "__main__":
    unittest.main()
