"""
GAP-5: Governance endpoints require a known viewer/actor.

Tests verify:
- GET /api/memory-proposals: rejects unknown viewer (403), accepts known viewer
- POST /api/learning/proposals/{id}: rejects missing viewer (422), rejects unknown (403)
- POST /api/apple/governance-proposals/{id}/promote: rejects unknown actor (403)
- POST /api/apple/governance-proposals/{id}/dismiss: rejects unknown actor (403)
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
from types import SimpleNamespace
from unittest.mock import MagicMock

import jarvis.approvals as approvals_module
from jarvis.approvals import ApprovalQueue

# ---------------------------------------------------------------------------
# Minimal FastAPI / uvicorn stubs (copied from test_service_promotion_api.py)
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
# Stub runtime
# ---------------------------------------------------------------------------

_KNOWN = {"chris", "rebekah", "caleb", "anna"}

def _make_runtime():
    rt = MagicMock()

    def _get_actor(name):
        if str(name).strip().lower() in _KNOWN:
            return SimpleNamespace(display_name=name.title(), user_id=name.lower())
        raise KeyError(f"Unknown actor: {name}")

    rt.get_actor.side_effect = _get_actor
    rt.memory_proposals.return_value = []
    rt.resolve_memory_proposal.return_value = {"ok": True}
    rt.config = MagicMock()
    rt.config.data_root = Path(tempfile.mkdtemp())
    return rt


def _run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Base test class with shared app setup
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

        # Suppress apple_api registration — we test it separately
        self._orig_apple = service_module._register_apple_api
        service_module._register_apple_api = lambda app, runtime: None
        self.addCleanup(lambda: setattr(service_module, "_register_apple_api", self._orig_apple))

        self.runtime = _make_runtime()
        self.app = service_module.build_app(self.runtime)

    def _restore_singletons(self):
        approvals_module._guard_singleton = self._orig_guard
        approvals_module._queue_singleton = self._orig_queue

    def _route(self, path, method="GET"):
        for r in self.app.router.routes:
            if getattr(r, "path", None) == path and method.upper() in getattr(r, "methods", set()):
                return r.endpoint
        raise AssertionError(f"Route {method} {path} not registered")


# ---------------------------------------------------------------------------
# Tests: GET /api/memory-proposals
# ---------------------------------------------------------------------------

class TestMemoryProposalsViewer(_ServiceTestBase):

    def test_known_viewer_succeeds(self):
        fn = self._route("/api/memory-proposals", "GET")
        _run(fn(viewer="chris", status=""))
        self.runtime.memory_proposals.assert_called_once()

    def test_default_viewer_chris_succeeds(self):
        fn = self._route("/api/memory-proposals", "GET")
        _run(fn(viewer="Chris", status=""))
        self.runtime.memory_proposals.assert_called()

    def test_unknown_viewer_raises_403(self):
        fn = self._route("/api/memory-proposals", "GET")
        with self.assertRaises(HTTPException) as ctx:
            _run(fn(viewer="intruder", status=""))
        self.assertEqual(ctx.exception.status_code, 403)


# ---------------------------------------------------------------------------
# Tests: POST /api/learning/proposals/{id}
# ---------------------------------------------------------------------------

class TestLearningProposalViewer(_ServiceTestBase):

    def _decide(self, proposal_id, payload):
        fn = self._route("/api/learning/proposals/{proposal_id}", "POST")
        return _run(fn(proposal_id=proposal_id, payload=payload))

    def test_missing_viewer_raises_422(self):
        with self.assertRaises(HTTPException) as ctx:
            self._decide("prop-1", {"decision": "approved"})
        self.assertEqual(ctx.exception.status_code, 422)

    def test_unknown_viewer_raises_403(self):
        with self.assertRaises(HTTPException) as ctx:
            self._decide("prop-1", {"viewer": "nobody", "decision": "approved"})
        self.assertEqual(ctx.exception.status_code, 403)

    def test_known_viewer_resolves_proposal(self):
        self._decide("prop-1", {"viewer": "chris", "decision": "approved"})
        self.runtime.resolve_memory_proposal.assert_called_once_with("prop-1", "approved")

    def test_empty_string_viewer_raises_422(self):
        with self.assertRaises(HTTPException) as ctx:
            self._decide("prop-1", {"viewer": "", "decision": "approved"})
        self.assertEqual(ctx.exception.status_code, 422)


# ---------------------------------------------------------------------------
# Tests: apple governance-proposals (promote / dismiss) — via apple_api
# ---------------------------------------------------------------------------

class TestGovernanceProposalActor(unittest.TestCase):

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self._orig_cwd = os.getcwd()
        os.chdir(self.tempdir.name)
        self.addCleanup(os.chdir, self._orig_cwd)

        import jarvis.apple_api as apple_api_module
        self.apple_api = apple_api_module

        self.runtime = _make_runtime()
        self.app = sys.modules["fastapi"].FastAPI()
        apple_api_module._register_apple_api(self.app, self.runtime)

    def _route(self, path, method="POST"):
        for r in self.app.router.routes:
            if getattr(r, "path", None) == path and method.upper() in getattr(r, "methods", set()):
                return r.endpoint
        raise AssertionError(f"Route {method} {path} not found in apple_api")

    def test_promote_unknown_actor_raises_403(self):
        fn = self._route("/api/apple/governance-proposals/{proposal_id}/promote")
        with self.assertRaises(HTTPException) as ctx:
            _run(fn(proposal_id="gp-1", payload={"actor": "intruder"}))
        self.assertEqual(ctx.exception.status_code, 403)

    def test_dismiss_unknown_actor_raises_403(self):
        fn = self._route("/api/apple/governance-proposals/{proposal_id}/dismiss")
        with self.assertRaises(HTTPException) as ctx:
            _run(fn(proposal_id="gp-1", payload={"actor": "intruder"}))
        self.assertEqual(ctx.exception.status_code, 403)

    def test_promote_known_actor_passes_auth(self):
        fn = self._route("/api/apple/governance-proposals/{proposal_id}/promote")
        try:
            _run(fn(proposal_id="nonexistent", payload={"actor": "chris"}))
        except HTTPException as exc:
            # 404 (proposal not found) is expected — 403 is NOT
            self.assertNotEqual(exc.status_code, 403, "Auth should pass for known actor")

    def test_dismiss_known_actor_passes_auth(self):
        fn = self._route("/api/apple/governance-proposals/{proposal_id}/dismiss")
        try:
            _run(fn(proposal_id="nonexistent", payload={"actor": "chris"}))
        except HTTPException as exc:
            self.assertNotEqual(exc.status_code, 403, "Auth should pass for known actor")


if __name__ == "__main__":
    unittest.main()
