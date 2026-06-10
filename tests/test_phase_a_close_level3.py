"""
Phase A: Close Level 3 — comprehensive test suite.

Tests:
A7/A9 — Home state: _unavailable_home_state returns source='unavailable', not 'mock'
A6    — Recovery loop: upsert_case accepts owner/root_cause/prevention_note;
         close_case writes closure_note/closed_at; set_lifecycle_fields persists
A1    — Runtime posture: _build_deployment_context detects env correctly
A4    — Mission board: audit log written on completion; lessons_learned field accepted
A8    — Apple command-center: /api/apple/command-center returns all 6 sections
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

# ---------------------------------------------------------------------------
# FastAPI stub (must be installed before importing jarvis modules)
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


class _MockApp:
    def __init__(self):
        self.routes: list[dict] = []

    def _reg(self, path, methods):
        def dec(fn):
            self.routes.append({"path": path, "methods": methods, "endpoint": fn})
            return fn
        return dec

    def get(self, path, *a, **kw):    return self._reg(path, {"GET"})
    def post(self, path, *a, **kw):   return self._reg(path, {"POST"})
    def put(self, path, *a, **kw):    return self._reg(path, {"PUT"})
    def patch(self, path, *a, **kw):  return self._reg(path, {"PATCH"})
    def delete(self, path, *a, **kw): return self._reg(path, {"DELETE"})
    def websocket(self, path, *a, **kw): return self._reg(path, {"WS"})
    def on_event(self, *a, **kw):     return lambda fn: fn
    def mount(self, *a, **kw):        pass


def _body(resp) -> dict:
    if isinstance(resp, dict):
        return resp
    raw = getattr(resp, "body", None) or b"{}"
    return json.loads(raw)


# ---------------------------------------------------------------------------
# A7/A9 — Home state unavailable
# ---------------------------------------------------------------------------

class TestHomeStateUnavailable(unittest.TestCase):
    """_unavailable_home_state must return source='unavailable', never 'mock'."""

    def setUp(self):
        import jarvis.apple_api as apple_api
        self.apple_api = apple_api

    def test_unavailable_home_state_source_is_unavailable(self):
        state = self.apple_api._unavailable_home_state()
        self.assertEqual(state["source"], "unavailable")

    def test_unavailable_home_state_available_false(self):
        state = self.apple_api._unavailable_home_state()
        self.assertFalse(state["available"])

    def test_unavailable_home_state_has_error(self):
        state = self.apple_api._unavailable_home_state("custom reason")
        self.assertIn("custom reason", state["error"])

    def test_unavailable_home_state_has_blocker(self):
        state = self.apple_api._unavailable_home_state()
        self.assertIn("HOME_ASSISTANT_URL", state["blocker"])

    def test_unavailable_home_state_has_fetched_at(self):
        state = self.apple_api._unavailable_home_state()
        self.assertIn("fetched_at", state)

    def test_unavailable_home_state_has_empty_collections(self):
        state = self.apple_api._unavailable_home_state()
        self.assertEqual(state["present_members"], [])
        self.assertEqual(state["doors"], {})
        self.assertEqual(state["lights_on"], [])

    def test_mock_home_state_deprecated_wrapper_returns_unavailable(self):
        """_mock_home_state is deprecated but must NOT return source='mock'."""
        state = self.apple_api._mock_home_state()
        self.assertNotEqual(state["source"], "mock")
        self.assertEqual(state["source"], "unavailable")

    def test_apple_home_state_uses_unavailable_when_ha_none(self):
        """When get_ha() returns None, apple_home_state returns source=unavailable."""
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        orig_cwd = os.getcwd()
        os.chdir(self.tmpdir.name)
        self.addCleanup(os.chdir, orig_cwd)
        (Path(self.tmpdir.name) / "data" / "apple").mkdir(parents=True, exist_ok=True)

        app = _MockApp()
        runtime = MagicMock()
        runtime.chamber_home_aggregate.return_value = {"action_items": []}
        from jarvis.apple_api import _register_apple_api

        with patch("jarvis.data_connectors.get_ha", return_value=None):
            _register_apple_api(app, runtime)
            route = next(r for r in app.routes if r["path"] == "/api/apple/home/state")
            result = asyncio.run(route["endpoint"]())

        data = _body(result).get("data") or _body(result)
        self.assertEqual(data.get("source"), "unavailable")
        self.assertFalse(data.get("available", True))


# ---------------------------------------------------------------------------
# A6 — Recovery loop lifecycle fields
# ---------------------------------------------------------------------------

class TestRecoveryLifecycleFields(unittest.TestCase):
    """RecoveryStore must persist owner, root_cause, prevention_note, verification_note,
    closure_note on create and close."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        from jarvis.recovery_cases import RecoveryCaseStore as RecoveryStore
        self.store = RecoveryStore(Path(self.tmpdir.name) / "recovery")

    def _upsert(self, **kwargs):
        return self.store.upsert_case(
            source_kind="test",
            title="Test case",
            detail="Test detail",
            related_route="/test",
            related_key=f"key-{id(kwargs)}",
            **kwargs,
        )

    def test_upsert_stores_owner(self):
        case = self._upsert(owner="Chris")
        self.assertEqual(case["owner"], "Chris")

    def test_upsert_stores_root_cause(self):
        case = self._upsert(root_cause="Database timeout")
        self.assertEqual(case["root_cause"], "Database timeout")

    def test_upsert_stores_prevention_note(self):
        case = self._upsert(prevention_note="Add retry logic")
        self.assertEqual(case["prevention_note"], "Add retry logic")

    def test_upsert_creates_verification_note_empty(self):
        case = self._upsert()
        self.assertIn("verification_note", case)
        self.assertEqual(case["verification_note"], "")

    def test_upsert_creates_closure_note_empty(self):
        case = self._upsert()
        self.assertIn("closure_note", case)
        self.assertEqual(case["closure_note"], "")

    def test_upsert_creates_closed_at_empty(self):
        case = self._upsert()
        self.assertIn("closed_at", case)
        self.assertEqual(case["closed_at"], "")

    def test_set_lifecycle_fields_persists(self):
        case = self._upsert()
        updated = self.store.set_lifecycle_fields(
            case["case_id"],
            owner="Chris",
            root_cause="Timeout",
            prevention_note="Add retry",
            verification_note="Tested OK",
        )
        self.assertEqual(updated["owner"], "Chris")
        self.assertEqual(updated["root_cause"], "Timeout")
        self.assertEqual(updated["prevention_note"], "Add retry")
        self.assertEqual(updated["verification_note"], "Tested OK")

    def test_set_lifecycle_fields_not_found_raises(self):
        with self.assertRaises(KeyError):
            self.store.set_lifecycle_fields("nonexistent-id", owner="Chris")

    def test_close_case_sets_resolved_status(self):
        case = self._upsert()
        closed = self.store.close_case(case["case_id"], actor="Chris", closure_note="Fixed.")
        self.assertEqual(closed["status"], "resolved")

    def test_close_case_sets_closed_at(self):
        case = self._upsert()
        closed = self.store.close_case(case["case_id"], actor="Chris")
        self.assertNotEqual(closed["closed_at"], "")

    def test_close_case_sets_closed_by(self):
        case = self._upsert()
        closed = self.store.close_case(case["case_id"], actor="Chris")
        self.assertEqual(closed["closed_by"], "Chris")

    def test_close_case_sets_closure_note(self):
        case = self._upsert()
        closed = self.store.close_case(case["case_id"], actor="Chris", closure_note="All clear.")
        self.assertEqual(closed["closure_note"], "All clear.")

    def test_close_case_sets_verification_note(self):
        case = self._upsert()
        closed = self.store.close_case(case["case_id"], actor="Chris", verification_note="Regression test passed.")
        self.assertEqual(closed["verification_note"], "Regression test passed.")

    def test_close_case_writes_history_entry(self):
        case = self._upsert()
        closed = self.store.close_case(case["case_id"], actor="Chris", closure_note="Done.")
        actions = [h["action"] for h in closed.get("history", [])]
        self.assertIn("closed", actions)

    def test_close_nonexistent_raises(self):
        with self.assertRaises(KeyError):
            self.store.close_case("nonexistent", actor="Chris")

    def test_lifecycle_fields_survive_reload(self):
        case = self._upsert(owner="Chris", root_cause="Disk full")
        from jarvis.recovery_cases import RecoveryCaseStore as RecoveryStore
        store2 = RecoveryStore(Path(self.tmpdir.name) / "recovery")
        reloaded = store2.get_case(case["case_id"])
        self.assertEqual(reloaded["owner"], "Chris")
        self.assertEqual(reloaded["root_cause"], "Disk full")


# ---------------------------------------------------------------------------
# A1 — Runtime posture: deployment context
# ---------------------------------------------------------------------------

class TestDeploymentContext(unittest.TestCase):
    """_build_deployment_context must correctly label env."""

    def setUp(self):
        from jarvis.runtime_posture import _build_deployment_context
        self._build = _build_deployment_context

    def test_local_env_when_no_docker(self):
        with patch.dict(os.environ, {}, clear=True):
            def _no_exists(p):
                return False
            with patch.object(Path, "exists", _no_exists):
                ctx = self._build(Path("."))
        self.assertEqual(ctx["env"], "local")
        self.assertFalse(ctx["in_docker"])
        self.assertFalse(ctx["in_ci"])

    def test_docker_env_when_dockerenv_exists(self):
        with patch.dict(os.environ, {}, clear=True):
            # Patch Path.exists as an unbound method — it receives 'self' (the Path instance)
            original_exists = Path.exists
            def _patched_exists(p):
                return str(p) == "/.dockerenv"
            with patch.object(Path, "exists", _patched_exists):
                ctx = self._build(Path("."))
        self.assertEqual(ctx["env"], "docker")
        self.assertTrue(ctx["in_docker"])

    def test_ci_env_when_ci_set(self):
        with patch.dict(os.environ, {"CI": "1"}, clear=False):
            def _no_exists(p):
                return False
            with patch.object(Path, "exists", _no_exists):
                ctx = self._build(Path("."))
        self.assertEqual(ctx["env"], "ci")
        self.assertTrue(ctx["in_ci"])

    def test_docker_env_has_services_expected(self):
        with patch.dict(os.environ, {"DOCKER_CONTAINER": "1"}, clear=False):
            def _no_exists(p):
                return False
            with patch.object(Path, "exists", _no_exists):
                ctx = self._build(Path("."))
        self.assertIn("jarvis", ctx["services_expected"])
        self.assertIn("postgres", ctx["services_expected"])

    def test_local_env_has_empty_services(self):
        with patch.dict(os.environ, {}, clear=True):
            def _no_exists(p):
                return False
            with patch.object(Path, "exists", _no_exists):
                ctx = self._build(Path("."))
        self.assertEqual(ctx["services_expected"], [])

    def test_docker_label_mentions_hetzner(self):
        with patch.dict(os.environ, {"DOCKER_CONTAINER": "1"}, clear=False):
            def _patched_exists(p):
                return False
            with patch.object(Path, "exists", _patched_exists):
                ctx = self._build(Path("."))
        self.assertIn("Hetzner", ctx["label"])

    def test_posture_snapshot_includes_deployment_key(self):
        """build_runtime_posture_snapshot() must return a 'deployment' section."""
        from jarvis.runtime_posture import build_runtime_posture_snapshot
        runtime = MagicMock()
        runtime.config = MagicMock()
        runtime.config.runtime_profile_path = Path("nonexistent.json")
        runtime.config.home_profile_path = Path("nonexistent.json")
        runtime.config.perception_profile_path = Path("nonexistent.json")
        runtime.config.workshop_profile_path = Path("nonexistent.json")
        runtime.guardian_status_snapshot.return_value = {"active": False, "status": {}, "recent_events": []}
        runtime.service_runtime_snapshot.return_value = {"role": "dev", "live_probe": {}, "hosted_probe": {}, "build_drift": False}
        runtime.google_workspace_summary.return_value = {}
        runtime.microsoft_graph_summary.return_value = {}
        runtime.family_calendar_summary.return_value = {}
        runtime.openviking_status.return_value = {}
        runtime.home_support.adapter.live = False

        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        orig = os.getcwd()
        os.chdir(tmpdir.name)
        self.addCleanup(os.chdir, orig)

        snapshot = build_runtime_posture_snapshot(runtime)
        self.assertIn("deployment", snapshot)
        self.assertIn("env", snapshot["deployment"])

    def test_launchd_section_has_local_only_note(self):
        """launchd section must be clearly labeled as local-only."""
        from jarvis.runtime_posture import build_runtime_posture_snapshot
        runtime = MagicMock()
        runtime.config = MagicMock()
        runtime.config.runtime_profile_path = Path("nonexistent.json")
        runtime.config.home_profile_path = Path("nonexistent.json")
        runtime.config.perception_profile_path = Path("nonexistent.json")
        runtime.config.workshop_profile_path = Path("nonexistent.json")
        runtime.guardian_status_snapshot.return_value = {"active": False, "status": {}, "recent_events": []}
        runtime.service_runtime_snapshot.return_value = {"role": "dev", "live_probe": {}, "hosted_probe": {}, "build_drift": False}
        runtime.google_workspace_summary.return_value = {}
        runtime.microsoft_graph_summary.return_value = {}
        runtime.family_calendar_summary.return_value = {}
        runtime.openviking_status.return_value = {}
        runtime.home_support.adapter.live = False

        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        orig = os.getcwd()
        os.chdir(tmpdir.name)
        self.addCleanup(os.chdir, orig)

        snapshot = build_runtime_posture_snapshot(runtime)
        launchd = snapshot.get("launchd", {})
        self.assertIn("note", launchd)
        self.assertIn("local-only", launchd["note"])


# ---------------------------------------------------------------------------
# A4 — Mission board: lessons_learned field + audit on closure
# ---------------------------------------------------------------------------

class TestMissionLessonsLearned(unittest.TestCase):
    """Mission dossier must persist lessons_learned; audit written on close."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        root = Path(self.tmpdir.name)
        from jarvis.missions import MissionStore, MissionSupport
        from jarvis.agentic import AgentRegistry
        from jarvis.audit import ApprovalStore
        from jarvis.trust import TrustSupport, TrustStore

        store = MissionStore(root / "missions")
        approval_store = ApprovalStore(root / "approvals")
        agent_registry = AgentRegistry()
        trust_store = TrustStore(root / "trust")
        trust_support = TrustSupport(trust_store)
        self.support = MissionSupport(
            store=store,
            trust_support=trust_support,
            approval_store=approval_store,
            agent_registry=agent_registry,
        )
        self.audit_root = root / "audit"

    def _create(self) -> dict:
        return self.support.create_mission(
            actor="chris",
            room="command-center",
            request="test mission for lessons learned",
        )

    def test_mission_accepts_lessons_learned_field(self):
        m = self._create()
        m["lessons_learned"] = "Always test in staging first."
        saved = self.support.save_mission(m)
        reloaded = self.support.get_mission(m["mission_id"])
        self.assertEqual(reloaded["lessons_learned"], "Always test in staging first.")

    def test_update_to_completed_writes_audit_log(self):
        m = self._create()
        m["lessons_learned"] = "Testing matters."
        self.support.save_mission(m)
        self.support.update_mission_status(m["mission_id"], "completed", note="All done.")
        from jarvis.audit import AuditLog
        log = AuditLog(self.audit_root)
        events = log.list_recent(limit=10, entry_type="mission_lifecycle")
        self.assertTrue(len(events) >= 1, "Expected at least one mission_lifecycle audit event")
        ev = events[0]
        self.assertEqual(ev["status"], "completed")
        self.assertEqual(ev["mission_id"], m["mission_id"])

    def test_audit_event_includes_lessons_learned(self):
        m = self._create()
        m["lessons_learned"] = "Key lesson."
        self.support.save_mission(m)
        self.support.update_mission_status(m["mission_id"], "completed")
        from jarvis.audit import AuditLog
        log = AuditLog(self.audit_root)
        events = log.list_recent(limit=10, entry_type="mission_lifecycle")
        self.assertGreater(len(events), 0)
        self.assertIn("lessons_learned", events[0])

    def test_update_to_blocked_also_writes_audit(self):
        m = self._create()
        self.support.update_mission_status(m["mission_id"], "blocked", note="External blocker.")
        from jarvis.audit import AuditLog
        log = AuditLog(self.audit_root)
        events = log.list_recent(limit=10, entry_type="mission_lifecycle")
        self.assertTrue(any(e["status"] == "blocked" for e in events))

    def test_update_to_active_does_not_write_audit(self):
        m = self._create()
        self.support.update_mission_status(m["mission_id"], "active")
        from jarvis.audit import AuditLog
        log = AuditLog(self.audit_root)
        events = log.list_recent(limit=10, entry_type="mission_lifecycle")
        self.assertEqual(len(events), 0, "Active status update must not write audit event")


# ---------------------------------------------------------------------------
# A8 — Command center route: /api/apple/command-center
# ---------------------------------------------------------------------------

class TestAppleCommandCenterRoute(unittest.TestCase):
    """GET /api/apple/command-center must return 6 sections with source labels."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.orig_cwd = os.getcwd()
        os.chdir(self.tmpdir.name)
        self.addCleanup(os.chdir, self.orig_cwd)
        (Path(self.tmpdir.name) / "data" / "apple").mkdir(parents=True, exist_ok=True)

    def _setup_route(self):
        from jarvis.apple_api import _register_apple_api
        app = _MockApp()
        runtime = MagicMock()
        runtime.family_mode_snapshot.return_value = {"mode": "normal", "mode_label": "Normal"}
        runtime.list_pending_approvals.return_value = []
        runtime.navigation_state.return_value = {}
        runtime.list_missions.return_value = []
        runtime.chamber_home_aggregate.return_value = {"action_items": []}
        _register_apple_api(app, runtime)
        return app

    def _find_route(self, app, path, method="GET"):
        for r in app.routes:
            if r["path"] == path and method.upper() in r["methods"]:
                return r["endpoint"]
        raise AssertionError(f"Route {method} {path} not found")

    def test_route_exists(self):
        app = self._setup_route()
        paths = [r["path"] for r in app.routes]
        self.assertIn("/api/apple/command-center", paths)

    def test_route_is_get(self):
        app = self._setup_route()
        for r in app.routes:
            if r["path"] == "/api/apple/command-center":
                self.assertIn("GET", r["methods"])
                return
        self.fail("Route not found")

    def _call_command_center(self):
        app = self._setup_route()
        endpoint = self._find_route(app, "/api/apple/command-center")
        result = asyncio.run(endpoint())
        return _body(result)

    def test_returns_today_section(self):
        body = self._call_command_center()
        data = body.get("data", body)
        self.assertIn("today", data)

    def test_returns_focus_section(self):
        body = self._call_command_center()
        data = body.get("data", body)
        self.assertIn("focus", data)

    def test_returns_family_section(self):
        body = self._call_command_center()
        data = body.get("data", body)
        self.assertIn("family", data)

    def test_returns_decisions_section(self):
        body = self._call_command_center()
        data = body.get("data", body)
        self.assertIn("decisions", data)

    def test_returns_navigate_section(self):
        body = self._call_command_center()
        data = body.get("data", body)
        self.assertIn("navigate", data)

    def test_returns_continuity_section(self):
        body = self._call_command_center()
        data = body.get("data", body)
        self.assertIn("continuity", data)

    def test_returns_generated_at(self):
        body = self._call_command_center()
        data = body.get("data", body)
        self.assertIn("generated_at", data)

    def test_focus_section_has_mode(self):
        body = self._call_command_center()
        data = body.get("data", body)
        focus = data.get("focus", {})
        self.assertIn("mode", focus)

    def test_decisions_section_has_pending_count(self):
        body = self._call_command_center()
        data = body.get("data", body)
        decisions = data.get("decisions", {})
        self.assertIn("pending_count", decisions)

    def test_continuity_section_has_mission_count(self):
        body = self._call_command_center()
        data = body.get("data", body)
        continuity = data.get("continuity", {})
        self.assertIn("mission_count", continuity)

    def test_sections_have_source_labels(self):
        body = self._call_command_center()
        data = body.get("data", body)
        for section in ["today", "focus", "decisions", "navigate", "continuity"]:
            self.assertIn("source", data.get(section, {}), f"Section '{section}' missing source label")

    def test_response_is_ok_wrapped(self):
        body = self._call_command_center()
        self.assertTrue(body.get("ok", False), f"Expected ok=True, got: {body}")


if __name__ == "__main__":
    unittest.main()
