"""
GAP-8 partial: Foundry proposal pipeline endpoints.

Tests verify:
- POST /api/foundry/proposals creates and persists a proposal
- POST /api/foundry/proposals returns 400 when title missing
- POST /api/foundry/proposals normalizes unknown kind to 'feature'
- GET /api/foundry/proposals lists all proposals
- GET /api/foundry/proposals filters by status
- GET /api/foundry/proposals filters by kind
- POST /api/foundry/proposals/{id}/approve approves a proposal
- POST /api/foundry/proposals/{id}/approve rejects a proposal
- POST /api/foundry/proposals/{id}/approve returns 404 on unknown id
- POST /api/foundry/proposals/{id}/approve returns 400 on invalid action
- Approved proposal has approved_by and approved_at fields set
- Rejected proposal has rejection_reason field set
- Proposal is written to the proposals log (JSONL)
- system_agent trust zone is bootstrapped and active
- boundary check blocks approve when zone is paused/suspended
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import jarvis.approvals as approvals_module
from jarvis.approvals import ApprovalQueue

# ---------------------------------------------------------------------------
# FastAPI stub (same pattern)
# ---------------------------------------------------------------------------

if "fastapi" not in sys.modules:
    fastapi_stub = types.ModuleType("fastapi")
    responses_stub = types.ModuleType("fastapi.responses")
    staticfiles_stub = types.ModuleType("fastapi.staticfiles")
    uvicorn_stub = types.ModuleType("uvicorn")

    class _Route:
        def __init__(self, path, methods, endpoint):
            self.path = path; self.methods = methods; self.endpoint = endpoint

    class _Router:
        def __init__(self): self.routes = []

    class _FastAPI:
        def __init__(self, *a, **kw): self.router = _Router()
        def _reg(self, path, methods):
            def dec(fn):
                self.router.routes.append(_Route(path, methods, fn)); return fn
            return dec
        def get(self, path, *a, **kw):    return self._reg(path, {"GET"})
        def post(self, path, *a, **kw):   return self._reg(path, {"POST"})
        def put(self, path, *a, **kw):    return self._reg(path, {"PUT"})
        def patch(self, path, *a, **kw):  return self._reg(path, {"PATCH"})
        def delete(self, path, *a, **kw): return self._reg(path, {"DELETE"})
        def websocket(self, path, *a, **kw): return self._reg(path, {"WS"})
        def on_event(self, *a, **kw):     return lambda fn: fn
        def mount(self, *a, **kw):        pass

    class _HTTPException(Exception):
        def __init__(self, status_code=500, detail=""):
            super().__init__(detail); self.status_code = status_code; self.detail = detail

    class _JSONResponse:
        def __init__(self, content, status_code=200, headers=None):
            self.body = json.dumps(content).encode(); self.status_code = status_code

    fastapi_stub.FastAPI = _FastAPI
    fastapi_stub.HTTPException = _HTTPException
    fastapi_stub.Query = lambda *a, **kw: None
    fastapi_stub.File = lambda *a, **kw: None
    fastapi_stub.Form = lambda *a, **kw: None
    fastapi_stub.Request = object
    fastapi_stub.UploadFile = object
    fastapi_stub.WebSocket = object
    fastapi_stub.WebSocketDisconnect = Exception
    fastapi_stub.BackgroundTasks = object
    responses_stub.JSONResponse = _JSONResponse
    responses_stub.HTMLResponse = _JSONResponse
    responses_stub.FileResponse = _JSONResponse
    responses_stub.RedirectResponse = _JSONResponse
    responses_stub.Response = _JSONResponse
    staticfiles_stub.StaticFiles = object
    uvicorn_stub.run = lambda *a, **kw: None
    sys.modules["fastapi"] = fastapi_stub
    sys.modules["fastapi.responses"] = responses_stub
    sys.modules["fastapi.staticfiles"] = staticfiles_stub
    sys.modules["uvicorn"] = uvicorn_stub

if "langgraph.graph" not in sys.modules:
    lg = types.ModuleType("langgraph")
    lg_graph = types.ModuleType("langgraph.graph")
    class _SG:
        def __init__(self, *a, **kw): pass
        def add_node(self, *a, **kw): pass
        def add_edge(self, *a, **kw): pass
        def compile(self):
            class _C:
                def invoke(self, s): return s
            return _C()
    lg_graph.StateGraph = _SG; lg_graph.END = "END"; lg_graph.START = "START"
    lg.graph = lg_graph
    sys.modules["langgraph"] = lg; sys.modules["langgraph.graph"] = lg_graph

import jarvis.service as service_module

HTTPException = sys.modules["fastapi"].HTTPException


# ---------------------------------------------------------------------------
# Base test class with full service setup
# ---------------------------------------------------------------------------

class _ServiceTestBase(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self._orig_cwd = os.getcwd()
        os.chdir(self.tempdir.name)
        self.addCleanup(os.chdir, self._orig_cwd)

        self._orig_root = ApprovalQueue.ROOT
        ApprovalQueue.ROOT = Path(self.tempdir.name) / "approvals"
        self.addCleanup(lambda: setattr(ApprovalQueue, "ROOT", self._orig_root))

        self._orig_guard = approvals_module._guard_singleton
        self._orig_queue = approvals_module._queue_singleton
        approvals_module._guard_singleton = None
        approvals_module._queue_singleton = None
        self.addCleanup(self._restore_singletons)

        self._orig_apple = service_module._register_apple_api
        service_module._register_apple_api = lambda app, runtime: None
        self.addCleanup(lambda: setattr(service_module, "_register_apple_api", self._orig_apple))

        self.runtime = MagicMock()
        self.runtime.list_stewardship_lanes.return_value = []
        self.runtime.assess_action_boundary.return_value = {
            "decision": "allow",
            "reason": "system_agent cleared",
            "trust_zone": "system_agent",
            "authority_stage": "stage_alert",
            "approval_mode": "stage_and_alert",
            "arena_status": "active",
        }
        self.app = service_module.build_app(self.runtime)

    def _restore_singletons(self):
        approvals_module._guard_singleton = self._orig_guard
        approvals_module._queue_singleton = self._orig_queue

    def _route(self, path, method="POST"):
        for r in self.app.router.routes:
            if getattr(r, "path", None) == path and method.upper() in getattr(r, "methods", set()):
                return r.endpoint
        raise AssertionError(f"Route {method} {path} not registered")

    def _run(self, coro):
        return asyncio.run(coro)

    @staticmethod
    def _body(resp) -> dict:
        if isinstance(resp, dict):
            return resp
        raw = getattr(resp, "body", None) or getattr(resp, "content", None) or b"{}"
        return json.loads(raw)

    def _create_proposal(self, **kwargs):
        payload = {"title": "Test proposal", "kind": "feature", **kwargs}
        fn = self._route("/api/foundry/proposals", "POST")
        return self._run(fn(payload))

    def _list_proposals(self, status=None, kind=None):
        fn = self._route("/api/foundry/proposals", "GET")
        return self._run(fn(status=status, kind=kind))

    def _approve_proposal(self, proposal_id, action="approve", **kwargs):
        payload = {"action": action, **kwargs}
        fn = self._route("/api/foundry/proposals/{proposal_id}/approve", "POST")
        return self._run(fn(proposal_id, payload=payload))


# ---------------------------------------------------------------------------
# Route registration
# ---------------------------------------------------------------------------

class TestRouteRegistration(_ServiceTestBase):

    def test_create_proposal_route_registered(self):
        self._route("/api/foundry/proposals", "POST")

    def test_list_proposals_route_registered(self):
        self._route("/api/foundry/proposals", "GET")

    def test_approve_proposal_route_registered(self):
        self._route("/api/foundry/proposals/{proposal_id}/approve", "POST")


# ---------------------------------------------------------------------------
# POST /api/foundry/proposals
# ---------------------------------------------------------------------------

class TestCreateProposal(_ServiceTestBase):

    def test_create_returns_proposal_with_id(self):
        resp = self._create_proposal(title="Add health scoring")
        body = self._body(resp)
        proposal = body.get("data", body).get("proposal") or body.get("proposal")
        self.assertIsNotNone(proposal)
        self.assertTrue(str(proposal.get("id", "")).startswith("prop_"))

    def test_create_status_is_pending(self):
        resp = self._create_proposal(title="Add health scoring")
        body = self._body(resp)
        proposal = (body.get("data") or body).get("proposal") or body.get("proposal")
        self.assertEqual(proposal.get("status"), "pending")

    def test_create_preserves_kind(self):
        resp = self._create_proposal(title="Refactor trust zones", kind="refactor")
        body = self._body(resp)
        proposal = (body.get("data") or body).get("proposal") or body.get("proposal")
        self.assertEqual(proposal.get("kind"), "refactor")

    def test_create_normalizes_unknown_kind_to_feature(self):
        resp = self._create_proposal(title="Random", kind="unknown_type")
        body = self._body(resp)
        proposal = (body.get("data") or body).get("proposal") or body.get("proposal")
        self.assertEqual(proposal.get("kind"), "feature")

    def test_create_400_when_title_missing(self):
        fn = self._route("/api/foundry/proposals", "POST")
        with self.assertRaises(HTTPException) as ctx:
            self._run(fn({"kind": "feature"}))
        self.assertEqual(ctx.exception.status_code, 400)

    def test_create_persists_to_proposals_file(self):
        self._create_proposal(title="Persist me")
        proposals_path = Path(self.tempdir.name) / "data" / "foundry" / "proposals.json"
        self.assertTrue(proposals_path.exists(), "proposals.json should be created")
        data = json.loads(proposals_path.read_text())
        self.assertEqual(len(data.get("proposals", [])), 1)

    def test_create_writes_to_log(self):
        self._create_proposal(title="Log me")
        log_path = Path(self.tempdir.name) / "data" / "foundry" / "proposals_log.jsonl"
        self.assertTrue(log_path.exists(), "proposals_log.jsonl should be created")
        lines = [l for l in log_path.read_text().splitlines() if l.strip()]
        self.assertEqual(len(lines), 1)


# ---------------------------------------------------------------------------
# GET /api/foundry/proposals
# ---------------------------------------------------------------------------

class TestListProposals(_ServiceTestBase):

    def test_list_returns_empty_initially(self):
        resp = self._list_proposals()
        body = self._body(resp)
        inner = body.get("data") or body
        self.assertEqual(inner.get("count", inner.get("proposals", {}) and len(inner.get("proposals", []))), 0)

    def test_list_returns_created_proposals(self):
        self._create_proposal(title="Proposal A")
        self._create_proposal(title="Proposal B")
        resp = self._list_proposals()
        body = self._body(resp)
        inner = body.get("data") or body
        proposals = inner.get("proposals", [])
        self.assertEqual(len(proposals), 2)

    def test_list_filters_by_status(self):
        self._create_proposal(title="Pending one")
        resp_all = self._list_proposals()
        body_all = self._body(resp_all)
        inner_all = body_all.get("data") or body_all
        all_proposals = inner_all.get("proposals", [])
        self.assertEqual(len(all_proposals), 1)

        resp_filtered = self._list_proposals(status="approved")
        body_filtered = self._body(resp_filtered)
        inner_filtered = body_filtered.get("data") or body_filtered
        filtered = inner_filtered.get("proposals", [])
        self.assertEqual(len(filtered), 0)

    def test_list_filters_by_kind(self):
        self._create_proposal(title="Feature one", kind="feature")
        self._create_proposal(title="Bug fix one", kind="bugfix")
        resp = self._list_proposals(kind="bugfix")
        body = self._body(resp)
        inner = body.get("data") or body
        proposals = inner.get("proposals", [])
        self.assertEqual(len(proposals), 1)
        self.assertEqual(proposals[0]["kind"], "bugfix")


# ---------------------------------------------------------------------------
# POST /api/foundry/proposals/{id}/approve
# ---------------------------------------------------------------------------

class TestApproveProposal(_ServiceTestBase):

    def _get_proposal_id(self, resp):
        body = self._body(resp)
        proposal = (body.get("data") or body).get("proposal") or body.get("proposal")
        return proposal["id"]

    def test_approve_sets_status_to_approved(self):
        prop_id = self._get_proposal_id(self._create_proposal(title="Approve me"))
        resp = self._approve_proposal(prop_id, action="approve", actor="chris")
        body = self._body(resp)
        inner = body.get("data") or body
        proposal = inner.get("proposal") or {}
        self.assertEqual(proposal.get("status"), "approved")

    def test_approve_sets_approved_by(self):
        prop_id = self._get_proposal_id(self._create_proposal(title="Approve me"))
        self._approve_proposal(prop_id, action="approve", actor="chris")
        proposals_path = Path(self.tempdir.name) / "data" / "foundry" / "proposals.json"
        data = json.loads(proposals_path.read_text())
        approved = next((p for p in data["proposals"] if p["id"] == prop_id), None)
        self.assertEqual(approved.get("approved_by"), "chris")
        self.assertIsNotNone(approved.get("approved_at"))

    def test_reject_sets_status_to_rejected(self):
        prop_id = self._get_proposal_id(self._create_proposal(title="Reject me"))
        resp = self._approve_proposal(prop_id, action="reject", reason="Not ready yet")
        body = self._body(resp)
        inner = body.get("data") or body
        proposal = inner.get("proposal") or {}
        self.assertEqual(proposal.get("status"), "rejected")

    def test_reject_sets_rejection_reason(self):
        prop_id = self._get_proposal_id(self._create_proposal(title="Reject me"))
        self._approve_proposal(prop_id, action="reject", reason="Out of scope")
        proposals_path = Path(self.tempdir.name) / "data" / "foundry" / "proposals.json"
        data = json.loads(proposals_path.read_text())
        rejected = next((p for p in data["proposals"] if p["id"] == prop_id), None)
        self.assertEqual(rejected.get("rejection_reason"), "Out of scope")

    def test_approve_404_on_unknown_id(self):
        fn = self._route("/api/foundry/proposals/{proposal_id}/approve", "POST")
        with self.assertRaises(HTTPException) as ctx:
            self._run(fn("prop_nonexistent", payload={"action": "approve"}))
        self.assertEqual(ctx.exception.status_code, 404)

    def test_approve_400_on_invalid_action(self):
        prop_id = self._get_proposal_id(self._create_proposal(title="Test"))
        fn = self._route("/api/foundry/proposals/{proposal_id}/approve", "POST")
        with self.assertRaises(HTTPException) as ctx:
            self._run(fn(prop_id, payload={"action": "execute"}))
        self.assertEqual(ctx.exception.status_code, 400)

    def test_approve_blocked_when_boundary_denies(self):
        prop_id = self._get_proposal_id(self._create_proposal(title="Test"))
        self.runtime.assess_action_boundary.return_value = {
            "decision": "deny",
            "reason": "Arena suspended",
            "trust_zone": "system_agent",
            "authority_stage": "stage_alert",
            "approval_mode": "deny",
            "arena_status": "suspended",
        }
        resp = self._approve_proposal(prop_id, action="approve")
        body = self._body(resp)
        inner = body.get("data") or body
        self.assertEqual(inner.get("status"), "blocked_by_boundary")


# ---------------------------------------------------------------------------
# system_agent trust zone bootstrapped
# ---------------------------------------------------------------------------

class TestSystemAgentZoneBootstrapped(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)

    def test_system_agent_zone_is_bootstrapped(self):
        from jarvis.trust import TrustStore, TrustSupport
        store = TrustStore(Path(self.tmpdir.name))
        ts = TrustSupport(store=store, default_owner_principal="chris")
        ts.bootstrap_defaults()
        zones = ts.store.list_trust_zones()
        zone_ids = {str(z.get("zone_id", "")) for z in zones}
        self.assertIn("system_agent", zone_ids, "system_agent zone must be bootstrapped")

    def test_system_agent_zone_is_active(self):
        from jarvis.trust import TrustStore, TrustSupport
        store = TrustStore(Path(self.tmpdir.name))
        ts = TrustSupport(store=store, default_owner_principal="chris")
        ts.bootstrap_defaults()
        zones = ts.store.list_trust_zones()
        zone = next((z for z in zones if z.get("zone_id") == "system_agent"), None)
        self.assertIsNotNone(zone)
        self.assertEqual(zone.get("status"), "active")


if __name__ == "__main__":
    unittest.main()
