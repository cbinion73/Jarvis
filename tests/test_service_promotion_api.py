from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from types import SimpleNamespace

import jarvis.approvals as approvals_module
import jarvis.main as main_module
from jarvis.approvals import ApprovalQueue, init_approvals

if "fastapi" not in sys.modules:
    fastapi_stub = types.ModuleType("fastapi")
    responses_stub = types.ModuleType("fastapi.responses")
    staticfiles_stub = types.ModuleType("fastapi.staticfiles")
    uvicorn_stub = types.ModuleType("uvicorn")

    class _Route:
        def __init__(self, path: str, methods: set[str], endpoint) -> None:
            self.path = path
            self.methods = methods
            self.endpoint = endpoint

    class _Router:
        def __init__(self) -> None:
            self.routes: list[_Route] = []

    class _FastAPI:  # pragma: no cover - test stub only
        def __init__(self, *args, **kwargs) -> None:
            self.router = _Router()

        def _register(self, path: str, methods: set[str]):
            def decorator(fn):
                self.router.routes.append(_Route(path, methods, fn))
                return fn

            return decorator

        def get(self, path: str, *args, **kwargs):
            return self._register(path, {"GET"})

        def post(self, path: str, *args, **kwargs):
            return self._register(path, {"POST"})

        def put(self, path: str, *args, **kwargs):
            return self._register(path, {"PUT"})

        def patch(self, path: str, *args, **kwargs):
            return self._register(path, {"PATCH"})

        def delete(self, path: str, *args, **kwargs):
            return self._register(path, {"DELETE"})

        def websocket(self, path: str, *args, **kwargs):
            return self._register(path, {"WEBSOCKET"})

        def on_event(self, *args, **kwargs):
            def decorator(fn):
                return fn

            return decorator

        def mount(self, *args, **kwargs) -> None:
            return None

    class _HTTPException(Exception):  # pragma: no cover - test stub only
        def __init__(self, status_code: int, detail: str = "") -> None:
            super().__init__(detail)
            self.status_code = status_code
            self.detail = detail

    class _JSONResponse:  # pragma: no cover - test stub only
        def __init__(self, content, status_code: int = 200, headers: dict | None = None) -> None:
            self.body = json.dumps(content).encode("utf-8")
            self.status_code = status_code
            self.headers = headers or {}

    class _HTMLResponse(_JSONResponse):  # pragma: no cover - test stub only
        pass

    class _Response(_JSONResponse):  # pragma: no cover - test stub only
        pass

    class _FileResponse(_JSONResponse):  # pragma: no cover - test stub only
        pass

    class _RedirectResponse(_JSONResponse):  # pragma: no cover - test stub only
        pass

    class _StaticFiles:  # pragma: no cover - test stub only
        def __init__(self, *args, **kwargs) -> None:
            return None

    class _BackgroundTasks:  # pragma: no cover - test stub only
        def add_task(self, *args, **kwargs) -> None:
            return None

    class _Request:  # pragma: no cover - test stub only
        base_url = "http://testserver/"

    class _UploadFile:  # pragma: no cover - test stub only
        filename = ""
        content_type = "application/octet-stream"

    class _WebSocket:  # pragma: no cover - test stub only
        async def accept(self) -> None:
            return None

    class _WebSocketDisconnect(Exception):  # pragma: no cover - test stub only
        pass

    def _return_default(value=None, **kwargs):  # pragma: no cover - test stub only
        return value

    fastapi_stub.BackgroundTasks = _BackgroundTasks
    fastapi_stub.FastAPI = _FastAPI
    fastapi_stub.File = _return_default
    fastapi_stub.Form = _return_default
    fastapi_stub.HTTPException = _HTTPException
    fastapi_stub.Query = _return_default
    fastapi_stub.Request = _Request
    fastapi_stub.UploadFile = _UploadFile
    fastapi_stub.WebSocket = _WebSocket
    fastapi_stub.WebSocketDisconnect = _WebSocketDisconnect
    responses_stub.FileResponse = _FileResponse
    responses_stub.HTMLResponse = _HTMLResponse
    responses_stub.JSONResponse = _JSONResponse
    responses_stub.RedirectResponse = _RedirectResponse
    responses_stub.Response = _Response
    staticfiles_stub.StaticFiles = _StaticFiles
    uvicorn_stub.run = lambda *args, **kwargs: None
    sys.modules["fastapi"] = fastapi_stub
    sys.modules["fastapi.responses"] = responses_stub
    sys.modules["fastapi.staticfiles"] = staticfiles_stub
    sys.modules["uvicorn"] = uvicorn_stub

if "langgraph.graph" not in sys.modules:
    langgraph_module = types.ModuleType("langgraph")
    graph_module = types.ModuleType("langgraph.graph")

    class _StubStateGraph:  # pragma: no cover - test stub only
        def __init__(self, *_args, **_kwargs) -> None:
            self._nodes: dict[str, object] = {}

        def add_node(self, name: str, fn: object) -> None:
            self._nodes[name] = fn

        def add_edge(self, *_args, **_kwargs) -> None:
            return None

        def compile(self):
            class _Compiled:
                def invoke(self, state):
                    return state

            return _Compiled()

    graph_module.END = "END"
    graph_module.START = "START"
    graph_module.StateGraph = _StubStateGraph
    langgraph_module.graph = graph_module
    sys.modules["langgraph"] = langgraph_module
    sys.modules["langgraph.graph"] = graph_module

import jarvis.service as service_module


class _StubSupervisionSupport:
    def evaluate_action(
        self,
        *,
        agent_id: str,
        action_type: str,
        requested_outcome: str,
        trust_zone_id: str = "",
        lane_id: str = "",
        arena_id: str = "",
        context: dict | None = None,
    ) -> dict:
        if action_type == "calendar_change":
            return {
                "resolution": "sandbox",
                "sandbox_required": True,
                "approval_required": False,
                "escalation_required": False,
                "trust_zone_id": trust_zone_id,
                "lane_id": lane_id,
                "requested_outcome": requested_outcome,
            }
        return {
            "resolution": "stage",
            "sandbox_required": False,
            "approval_required": True,
            "escalation_required": False,
            "trust_zone_id": trust_zone_id,
            "lane_id": lane_id,
            "requested_outcome": requested_outcome,
        }


class _StubRuntime:
    def __init__(self) -> None:
        self.config = SimpleNamespace(
            tts_provider="auto",
            elevenlabs_voice="",
            piper_model_path=None,
            piper_speaker="0",
            second_brain_enabled=False,
        )
        self.supervision_support = _StubSupervisionSupport()
        self.promotion_calls: list[tuple[str, dict]] = []
        self.sandbox_calls: list[dict] = []

    def execute_sandbox_job(self, *, actor_name: str, job_id: str, triggered_by: str) -> dict:
        payload = {
            "actor_name": actor_name,
            "job_id": job_id,
            "triggered_by": triggered_by,
        }
        self.sandbox_calls.append(payload)
        return {"ok": True, "accepted": True, "job": {"job_id": job_id, "status": "sandbox-queued"}}

    def list_promotion_records(self, limit: int = 50) -> list[dict]:
        self.promotion_calls.append(("list_records", {"limit": limit}))
        return [{"subject_id": "household_schedule", "limit": limit}]

    def list_promotion_recommendations(self, limit: int = 12) -> list[dict]:
        self.promotion_calls.append(("list_recommendations", {"limit": limit}))
        return [{"subject_id": "pepper", "limit": limit}]

    def evaluate_promotion_claim(
        self,
        *,
        subject_kind: str,
        subject_id: str,
        target_stage: str,
        actor: str,
        basis: str,
        human_consent: bool,
    ) -> dict:
        payload = {
            "subject_kind": subject_kind,
            "subject_id": subject_id,
            "target_stage": target_stage,
            "actor": actor,
            "basis": basis,
            "human_consent": human_consent,
        }
        self.promotion_calls.append(("evaluate", payload))
        return {"decision": "promote", **payload}

    def apply_promotion_decision(
        self,
        *,
        subject_kind: str,
        subject_id: str,
        target_stage: str,
        actor: str,
        basis: str,
        human_consent: bool,
    ) -> dict:
        payload = {
            "subject_kind": subject_kind,
            "subject_id": subject_id,
            "target_stage": target_stage,
            "actor": actor,
            "basis": basis,
            "human_consent": human_consent,
        }
        self.promotion_calls.append(("apply", payload))
        return {"applied": True, "updated": {"authority_stage": target_stage}, **payload}

    def apply_promotion_recommendations(
        self,
        *,
        actor: str,
        basis: str,
        limit: int,
    ) -> dict:
        payload = {"actor": actor, "basis": basis, "limit": limit}
        self.promotion_calls.append(("apply_recommendations", payload))
        return {"applied": [{"subject_id": "household_schedule"}], **payload}


class ServicePromotionApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.original_cwd = os.getcwd()
        os.chdir(self.tempdir.name)
        self.addCleanup(os.chdir, self.original_cwd)

        self.original_root = ApprovalQueue.ROOT
        ApprovalQueue.ROOT = Path(self.tempdir.name) / "approvals"
        self.addCleanup(self._restore_root)

        self.original_guard = approvals_module._guard_singleton
        self.original_queue = approvals_module._queue_singleton
        approvals_module._guard_singleton = None
        approvals_module._queue_singleton = None
        self.addCleanup(self._restore_singletons)

        self.original_register_apple_api = service_module._register_apple_api
        service_module._register_apple_api = lambda app, runtime: None
        self.addCleanup(self._restore_register_apple_api)

        self.runtime = _StubRuntime()
        self.queue, self.guard = init_approvals(
            self.runtime.supervision_support,
            self.runtime.execute_sandbox_job,
        )
        self.app = service_module.build_app(self.runtime)

    def _restore_root(self) -> None:
        ApprovalQueue.ROOT = self.original_root

    def _restore_singletons(self) -> None:
        approvals_module._guard_singleton = self.original_guard
        approvals_module._queue_singleton = self.original_queue

    def _restore_register_apple_api(self) -> None:
        service_module._register_apple_api = self.original_register_apple_api

    def _route(self, path: str, method: str):
        for route in self.app.router.routes:
            if getattr(route, "path", None) == path and method.upper() in getattr(route, "methods", set()):
                return route.endpoint
        raise AssertionError(f"Could not find route {method} {path}")

    def _json_body(self, response) -> dict:
        return json.loads(response.body.decode("utf-8"))

    def test_promotion_routes_delegate_to_runtime_methods(self) -> None:
        records = asyncio.run(self._route("/api/promotion-records", "GET")(limit=7))
        recommendations = asyncio.run(self._route("/api/promotion-recommendations", "GET")(limit=5))
        evaluation = asyncio.run(
            self._route("/api/promotion/evaluate", "POST")(
                {
                    "subject_kind": "trust_zone",
                    "subject_id": "household_schedule",
                    "target_stage": "mature_live",
                    "actor": "Chris",
                    "basis": "reviewed-evidence",
                    "human_consent": True,
                }
            )
        )
        applied = asyncio.run(
            self._route("/api/promotion/apply", "POST")(
                {
                    "subject_kind": "agent",
                    "subject_id": "pepper",
                    "target_stage": "sandbox_live",
                    "actor": "system-steward",
                    "basis": "promotion-application",
                    "human_consent": False,
                }
            )
        )
        auto_applied = asyncio.run(
            self._route("/api/promotion/apply-recommendations", "POST")(
                {"actor": "system-steward", "basis": "nightly-review", "limit": 3}
            )
        )

        self.assertEqual(self._json_body(records)["records"][0]["limit"], 7)
        self.assertEqual(self._json_body(recommendations)["recommendations"][0]["limit"], 5)
        self.assertEqual(self._json_body(evaluation)["decision"], "promote")
        self.assertTrue(self._json_body(applied)["applied"])
        self.assertEqual(len(self._json_body(auto_applied)["applied"]), 1)
        self.assertEqual(
            self.runtime.promotion_calls,
            [
                ("list_records", {"limit": 7}),
                ("list_recommendations", {"limit": 5}),
                (
                    "evaluate",
                    {
                        "subject_kind": "trust_zone",
                        "subject_id": "household_schedule",
                        "target_stage": "mature_live",
                        "actor": "Chris",
                        "basis": "reviewed-evidence",
                        "human_consent": True,
                    },
                ),
                (
                    "apply",
                    {
                        "subject_kind": "agent",
                        "subject_id": "pepper",
                        "target_stage": "sandbox_live",
                        "actor": "system-steward",
                        "basis": "promotion-application",
                        "human_consent": False,
                    },
                ),
                (
                    "apply_recommendations",
                    {"actor": "system-steward", "basis": "nightly-review", "limit": 3},
                ),
            ],
        )

    def test_approval_submit_and_execute_expose_supervision_metadata(self) -> None:
        submit_response = asyncio.run(
            self._route("/api/approvals/submit", "POST")(
                {
                    "agent_id": "pepper",
                    "agent_label": "Pepper",
                    "action_type": "calendar_change",
                    "title": "Route pickup change",
                    "description": "Adjust the afternoon pickup window.",
                    "payload": {"event_id": "evt-1", "_sandbox_job_id": "stewardship-review:job-1"},
                    "context": {
                        "trust_zone_id": "household_schedule",
                        "lane_id": "family-stewardship",
                        "touches_external_state": True,
                        "reversible": True,
                    },
                }
            )
        )
        submit_payload = self._json_body(submit_response)
        request_id = submit_payload["request_id"]
        self.queue.approve(request_id, approved_by="chris")

        execute_response = asyncio.run(self._route("/api/approvals/{request_id}/execute", "POST")(request_id))
        execute_payload = self._json_body(execute_response)

        self.assertEqual(submit_response.status_code, 201)
        self.assertEqual(submit_payload["trust_zone_id"], "household_schedule")
        self.assertEqual(submit_payload["lane_id"], "family-stewardship")
        self.assertEqual(submit_payload["supervision_decision"]["resolution"], "sandbox")
        self.assertEqual(execute_payload["status"], "executed")
        self.assertEqual(execute_payload["result"]["status"], "sandbox_routed")
        self.assertEqual(execute_payload["supervision_decision"]["resolution"], "sandbox")
        self.assertEqual(self.runtime.sandbox_calls[0]["job_id"], "stewardship-review:job-1")


class MainApprovalInitializationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._patched: list[tuple[object, str, object]] = []

    def tearDown(self) -> None:
        for obj, name, value in reversed(self._patched):
            setattr(obj, name, value)

    def _patch(self, obj: object, name: str, value: object) -> None:
        self._patched.append((obj, name, getattr(obj, name)))
        setattr(obj, name, value)

    def test_command_serve_passes_supervision_support_and_sandbox_router_to_approval_init(self) -> None:
        calls: list[tuple[object, object]] = []
        served: list[tuple[object, str, int]] = []

        def fake_init_approvals(supervision_support, sandbox_router):
            calls.append((supervision_support, sandbox_router))
            return None, None

        def fake_serve(runtime, host, port):
            served.append((runtime, host, port))

        flag_overrides = {
            "_KNOWN_FACTS_IMPORT_OK": False,
            "_CONNECTORS_IMPORT_OK": False,
            "_APPROVALS_IMPORT_OK": True,
            "_LLM_GATEWAY_IMPORT_OK": False,
            "_SCHEDULER_IMPORT_OK": False,
            "_CHRONICLE_BRIDGE_IMPORT_OK": False,
            "_WORK_INTELLIGENCE_IMPORT_OK": False,
            "_VOICE_PIPELINE_IMPORT_OK": False,
            "_FAMILY_PROFILES_IMPORT_OK": False,
            "_PUBLISHING_IMPORT_OK": False,
            "_GHOSTWRITR_BRIDGE_IMPORT_OK": False,
            "_SOCIAL_ENGINE_IMPORT_OK": False,
            "_WORKSHOP_COPILOT_IMPORT_OK": False,
            "_FINANCIAL_INTELLIGENCE_IMPORT_OK": False,
            "_GROWTH_INTELLIGENCE_IMPORT_OK": False,
            "_HOME_INTELLIGENCE_IMPORT_OK": False,
        }
        for name, value in flag_overrides.items():
            self._patch(main_module, name, value)

        self._patch(main_module, "_init_approvals", fake_init_approvals)
        self._patch(main_module, "_ensure_ollama_running", lambda: None)
        self._patch(service_module, "serve", fake_serve)

        runtime = SimpleNamespace(
            config=SimpleNamespace(),
            supervision_support="supervision-support",
            execute_sandbox_job="sandbox-router",
        )

        result = main_module.command_serve(runtime, "127.0.0.1", 8787)

        self.assertEqual(result, 0)
        self.assertEqual(calls, [("supervision-support", "sandbox-router")])
        self.assertEqual(served, [(runtime, "127.0.0.1", 8787)])

    def test_python_module_help_invokes_cli_entrypoint(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "jarvis.main", "--help"],
            cwd="/Users/chris/Desktop/JARVIS",
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("serve", result.stdout)
        self.assertIn("JARVIS household runtime scaffold", result.stdout)


if __name__ == "__main__":
    unittest.main()
