"""
Level 8: human-consented trust zone promotion for system_agent.

Verifies:
- POST /api/trust-zones/{zone_id}/consent-promote requires human_consent=true
- Missing or false human_consent returns 400
- Unknown zone_id returns 404
- Valid consent-promote advances system_agent stage_alert → sandbox_live
- After promotion, assess_action_boundary for foundry_proposal_review returns allow
- Promotion is recorded in the promotion log (promote_trust_zone called)
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
import types
import unittest
from dataclasses import asdict
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import jarvis.approvals as approvals_module
from jarvis.approvals import ApprovalQueue

# ---------------------------------------------------------------------------
# FastAPI stub
# ---------------------------------------------------------------------------

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

    class _HTTPException(Exception):
        def __init__(self, status_code=500, detail=""):
            super().__init__(detail); self.status_code = status_code; self.detail = detail

    class _JSONResponse:
        def __init__(self, content, status_code=200, headers=None):
            self.body = json.dumps(content).encode(); self.status_code = status_code

    _fs.FastAPI = _FastAPI
    _fs.HTTPException = _HTTPException
    _fs.Query = lambda *a, **kw: None
    _fs.File = lambda *a, **kw: None
    _fs.Form = lambda *a, **kw: None
    _fs.Request = object
    _fs.UploadFile = object
    _fs.WebSocket = object
    _fs.WebSocketDisconnect = Exception
    _fs.BackgroundTasks = object
    _rs.JSONResponse = _JSONResponse
    _rs.HTMLResponse = _JSONResponse
    _rs.FileResponse = _JSONResponse
    _rs.RedirectResponse = _JSONResponse
    _rs.Response = _JSONResponse
    _ss.StaticFiles = object
    _uv.run = lambda *a, **kw: None
    sys.modules["fastapi"] = _fs
    sys.modules["fastapi.responses"] = _rs
    sys.modules["fastapi.staticfiles"] = _ss
    sys.modules["uvicorn"] = _uv

if "langgraph.graph" not in sys.modules:
    _lg = types.ModuleType("langgraph")
    _lg_g = types.ModuleType("langgraph.graph")
    class _SG:
        def __init__(self, *a, **kw): pass
        def add_node(self, *a, **kw): pass
        def add_edge(self, *a, **kw): pass
        def compile(self):
            class _C:
                def invoke(self, s): return s
            return _C()
    _lg_g.StateGraph = _SG; _lg_g.END = "END"; _lg_g.START = "START"
    _lg.graph = _lg_g
    sys.modules["langgraph"] = _lg; sys.modules["langgraph.graph"] = _lg_g

import jarvis.service as service_module

HTTPException = sys.modules["fastapi"].HTTPException


# ---------------------------------------------------------------------------
# Base
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
        self.app = service_module.build_app(self.runtime)

    def _restore_singletons(self):
        approvals_module._guard_singleton = self._orig_guard
        approvals_module._queue_singleton = self._orig_queue

    def _route(self, path_template: str, method: str = "POST"):
        for r in self.app.router.routes:
            if getattr(r, "path", None) == path_template and method.upper() in getattr(r, "methods", set()):
                return r.endpoint
        raise AssertionError(f"Route {method} {path_template} not found")

    def _run(self, coro):
        return asyncio.run(coro)

    @staticmethod
    def _body(resp) -> dict:
        if isinstance(resp, dict):
            return resp
        raw = getattr(resp, "body", None) or b"{}"
        return json.loads(raw)


# ---------------------------------------------------------------------------
# POST /api/trust-zones/{zone_id}/consent-promote — guardrails
# ---------------------------------------------------------------------------

class TestConsentPromoteGuardrails(_ServiceTestBase):

    def setUp(self):
        super().setUp()
        self.fn = self._route("/api/trust-zones/{zone_id}/consent-promote", "POST")

    def test_missing_human_consent_returns_400(self):
        with self.assertRaises(HTTPException) as ctx:
            self._run(self.fn("system_agent", payload={}))
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("human_consent", ctx.exception.detail)

    def test_false_human_consent_returns_400(self):
        with self.assertRaises(HTTPException) as ctx:
            self._run(self.fn("system_agent", payload={"human_consent": False}))
        self.assertEqual(ctx.exception.status_code, 400)

    def test_unknown_zone_returns_404(self):
        self.runtime.promote_trust_zone.side_effect = KeyError("Unknown trust zone: ghost_zone")
        with self.assertRaises(HTTPException) as ctx:
            self._run(self.fn("ghost_zone", payload={"human_consent": True}))
        self.assertEqual(ctx.exception.status_code, 404)

    def test_none_human_consent_returns_400(self):
        with self.assertRaises(HTTPException) as ctx:
            self._run(self.fn("system_agent", payload={"human_consent": None}))
        self.assertEqual(ctx.exception.status_code, 400)


# ---------------------------------------------------------------------------
# POST /api/trust-zones/{zone_id}/consent-promote — happy path
# ---------------------------------------------------------------------------

class TestConsentPromoteHappyPath(_ServiceTestBase):

    def setUp(self):
        super().setUp()
        self.fn = self._route("/api/trust-zones/{zone_id}/consent-promote", "POST")
        self.runtime.promote_trust_zone.return_value = {
            "zone_id": "system_agent",
            "authority_stage": "sandbox_live",
            "status": "active",
        }

    def test_promote_calls_runtime_promote_trust_zone(self):
        self._run(self.fn("system_agent", payload={"human_consent": True}))
        self.runtime.promote_trust_zone.assert_called_once_with(
            "system_agent",
            actor="chris",
            basis="human-consented-promotion",
        )

    def test_response_contains_promoted_true(self):
        body = self._body(self._run(self.fn("system_agent", payload={"human_consent": True})))
        self.assertTrue(body["promoted"])

    def test_response_contains_new_authority_stage(self):
        body = self._body(self._run(self.fn("system_agent", payload={"human_consent": True})))
        self.assertEqual(body["authority_stage"], "sandbox_live")

    def test_custom_actor_passed_through(self):
        self._run(self.fn("system_agent", payload={"human_consent": True, "actor": "admin"}))
        self.runtime.promote_trust_zone.assert_called_once_with(
            "system_agent",
            actor="admin",
            basis="human-consented-promotion",
        )

    def test_custom_basis_passed_through(self):
        self._run(self.fn("system_agent", payload={
            "human_consent": True,
            "basis": "chris-explicit-grant-2026-06-09",
        }))
        self.runtime.promote_trust_zone.assert_called_once_with(
            "system_agent",
            actor="chris",
            basis="chris-explicit-grant-2026-06-09",
        )

    def test_zone_id_in_response(self):
        body = self._body(self._run(self.fn("system_agent", payload={"human_consent": True})))
        self.assertEqual(body["zone_id"], "system_agent")


# ---------------------------------------------------------------------------
# Integration: system_agent promoted → boundary returns allow
# ---------------------------------------------------------------------------

class TestSystemAgentPromotionUnlocksApproval(unittest.TestCase):
    """
    After promoting system_agent to sandbox_live, assess_action_boundary
    for foundry_proposal_review must return decision=allow (not stage).
    """

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.root = Path(self.tmpdir.name)

        from jarvis.trust import TrustStore, TrustSupport
        store = TrustStore(self.root)
        self.ts = TrustSupport(store=store, default_owner_principal="chris")
        self.ts.bootstrap_defaults()

        import jarvis.runtime as runtime_mod
        self.runtime = object.__new__(runtime_mod.JarvisRuntime)
        self.runtime.trust_support = self.ts

    def test_before_promotion_boundary_returns_stage(self):
        result = self.runtime.assess_action_boundary(
            zone_id="system_agent",
            action_type="foundry_proposal_review",
            requested_stage="sandbox_live",
        )
        self.assertEqual(result["decision"], "stage",
                         "Before promotion, system_agent at stage_alert must return stage")

    def test_after_promotion_boundary_returns_allow(self):
        self.runtime.promote_trust_zone("system_agent", actor="chris", basis="test")
        result = self.runtime.assess_action_boundary(
            zone_id="system_agent",
            action_type="foundry_proposal_review",
            requested_stage="sandbox_live",
        )
        self.assertEqual(result["decision"], "allow",
                         "After promoting to sandbox_live, boundary must return allow")

    def test_promote_trust_zone_advances_one_stage(self):
        zone_before = self.ts.get_trust_zone("system_agent")
        self.assertEqual(zone_before.get("authority_stage"), "stage_alert")

        self.runtime.promote_trust_zone("system_agent", actor="chris", basis="test")

        zone_after = self.ts.get_trust_zone("system_agent")
        self.assertEqual(zone_after.get("authority_stage"), "sandbox_live")

    def test_promote_unknown_zone_raises_key_error(self):
        with self.assertRaises(KeyError):
            self.runtime.promote_trust_zone("nonexistent_zone", actor="chris", basis="test")


# ---------------------------------------------------------------------------
# Route registered
# ---------------------------------------------------------------------------

class TestConsentPromoteRouteRegistered(_ServiceTestBase):

    def test_consent_promote_route_exists(self):
        routes = [getattr(r, "path", None) for r in self.app.router.routes]
        self.assertIn(
            "/api/trust-zones/{zone_id}/consent-promote",
            routes,
            "Route /api/trust-zones/{zone_id}/consent-promote must be registered",
        )

    def test_consent_promote_is_post_only(self):
        for r in self.app.router.routes:
            if getattr(r, "path", None) == "/api/trust-zones/{zone_id}/consent-promote":
                self.assertIn("POST", r.methods)
                return
        self.fail("Route not found")


if __name__ == "__main__":
    unittest.main()
