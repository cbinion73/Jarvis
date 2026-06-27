from __future__ import annotations

import sys
import types
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch


if "fastapi" not in sys.modules:
    fastapi_stub = types.ModuleType("fastapi")
    responses_stub = types.ModuleType("fastapi.responses")
    staticfiles_stub = types.ModuleType("fastapi.staticfiles")
    uvicorn_stub = types.ModuleType("uvicorn")

    class _FastAPI:
        def __init__(self, *args, **kwargs) -> None:
            return None

    fastapi_stub.FastAPI = _FastAPI
    fastapi_stub.HTTPException = Exception
    fastapi_stub.Query = lambda *args, **kwargs: None
    fastapi_stub.File = lambda *args, **kwargs: None
    fastapi_stub.Form = lambda *args, **kwargs: None
    fastapi_stub.Request = object
    fastapi_stub.UploadFile = object
    fastapi_stub.WebSocket = object
    fastapi_stub.WebSocketDisconnect = Exception
    fastapi_stub.BackgroundTasks = object
    responses_stub.JSONResponse = dict
    responses_stub.HTMLResponse = dict
    responses_stub.FileResponse = dict
    responses_stub.RedirectResponse = dict
    responses_stub.Response = dict
    staticfiles_stub.StaticFiles = object
    uvicorn_stub.run = lambda *args, **kwargs: None
    sys.modules["fastapi"] = fastapi_stub
    sys.modules["fastapi.responses"] = responses_stub
    sys.modules["fastapi.staticfiles"] = staticfiles_stub
    sys.modules["uvicorn"] = uvicorn_stub

if "langgraph.graph" not in sys.modules:
    langgraph_module = types.ModuleType("langgraph")
    graph_module = types.ModuleType("langgraph.graph")

    class _StubStateGraph:
        def __init__(self, *_args, **_kwargs) -> None:
            return None

        def add_node(self, *_args, **_kwargs) -> None:
            return None

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


from jarvis.runtime import JarvisRuntime


class MissionFollowupRuntimeTests(unittest.TestCase):
    def _runtime(self) -> JarvisRuntime:
        return object.__new__(JarvisRuntime)

    def test_followup_marks_active_mission_complete(self) -> None:
        runtime = self._runtime()
        called: dict[str, str] = {}

        def update_status(_self, mission_id: str, status: str, *, note: str = "") -> dict:
            called["mission_id"] = mission_id
            called["status"] = status
            called["note"] = note
            return {"mission_id": mission_id, "status": status, "mission_review": {}, "next_step": "Review completion"}

        with patch.object(JarvisRuntime, "get_actor", lambda _self, actor_name: SimpleNamespace(display_name=actor_name)), patch.object(
            JarvisRuntime,
            "mission_control_snapshot",
            lambda _self, actor_name: {
                "active_missions": [
                    {
                        "mission_id": "mission-1",
                        "title": "Health Reset",
                        "workspace_route": "/mission-board?mission_id=mission-1",
                        "conversation_route": {"route": "/health-center", "route_label": "Open Health"},
                    }
                ]
            },
        ), patch.object(JarvisRuntime, "update_mission_status", update_status):
            result = runtime._try_handle_mission_followup("Chris", "office", "mark it complete")
        self.assertIsNotNone(result)
        self.assertEqual(called["mission_id"], "mission-1")
        self.assertEqual(called["status"], "completed")
        self.assertIn("marked complete", result.output_text.lower())

    def test_followup_marks_active_mission_blocked(self) -> None:
        runtime = self._runtime()
        called: dict[str, str] = {}

        def update_status(_self, mission_id: str, status: str, *, note: str = "") -> dict:
            called["status"] = status
            return {
                "mission_id": mission_id,
                "status": status,
                "mission_review": {"next_attention": "Waiting on missing assumptions"},
                "next_step": "Review blocker",
            }

        with patch.object(JarvisRuntime, "get_actor", lambda _self, actor_name: SimpleNamespace(display_name=actor_name)), patch.object(
            JarvisRuntime,
            "mission_control_snapshot",
            lambda _self, actor_name: {
                "active_missions": [
                    {
                        "mission_id": "mission-1",
                        "title": "Health Reset",
                        "workspace_route": "/mission-board?mission_id=mission-1",
                        "conversation_route": {"route": "/health-center", "route_label": "Open Health"},
                    }
                ]
            },
        ), patch.object(JarvisRuntime, "update_mission_status", update_status):
            result = runtime._try_handle_mission_followup("Chris", "office", "this is blocked right now")
        self.assertIsNotNone(result)
        self.assertEqual(called["status"], "blocked")
        self.assertIn("Waiting on missing assumptions", result.output_text)

    def test_followup_updates_next_step(self) -> None:
        runtime = self._runtime()
        called: dict[str, str] = {}

        def update_details(_self, mission_id: str, *, title: str = "", brief: str = "", request: str = "", next_step: str = "", note: str = "") -> dict:
            called["mission_id"] = mission_id
            called["next_step"] = next_step
            called["note"] = note
            return {
                "mission_id": mission_id,
                "next_step": next_step,
                "recommendation": "Keep the plan travel-resistant.",
            }

        with patch.object(JarvisRuntime, "get_actor", lambda _self, actor_name: SimpleNamespace(display_name=actor_name)), patch.object(
            JarvisRuntime,
            "mission_control_snapshot",
            lambda _self, actor_name: {
                "active_missions": [
                    {
                        "mission_id": "mission-1",
                        "title": "Health Reset",
                        "workspace_route": "/mission-board?mission_id=mission-1",
                        "conversation_route": {"route": "/health-center", "route_label": "Open Health"},
                    }
                ]
            },
        ), patch.object(JarvisRuntime, "update_mission_details", update_details):
            result = runtime._try_handle_mission_followup("Chris", "office", "next step is stage the travel workout plan")
        self.assertIsNotNone(result)
        self.assertEqual(called["mission_id"], "mission-1")
        self.assertEqual(called["next_step"], "stage the travel workout plan")
        self.assertIn("next step is now", result.output_text.lower())

    def test_surface_hint_uses_recommended_route_packet(self) -> None:
        runtime = self._runtime()
        with patch.object(
            JarvisRuntime,
            "mission_control_snapshot",
            lambda _self, actor_name: {
                "recommended_route": {
                    "packet": "health",
                    "route": "/health-center",
                    "route_label": "Open Health",
                    "mission_id": "mission-1",
                    "detail": "Stage a travel-resistant workout plan.",
                }
            },
        ):
            hint = runtime._mission_surface_hint("Chris")
        self.assertEqual(hint["packet"], "health")
        self.assertEqual(hint["route"], "/health-center")

    def test_allowed_background_jobs_include_domain_specific_items(self) -> None:
        runtime = self._runtime()
        jobs = runtime._mission_allowed_background_jobs({"primary_domain": "writing"})
        titles = {str(item.get("title", "")).strip() for item in jobs}
        self.assertIn("Mission milestone proposals", titles)
        self.assertIn("Next-action suggestions", titles)
        self.assertIn("Stalled mission detection", titles)
        self.assertIn("Writing opportunity spotting", titles)

    def test_accountability_update_flags_stalled_missions_supportively(self) -> None:
        runtime = self._runtime()
        stale_update = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        payload = runtime._mission_accountability_update(
            {
                "primary_domain": "health",
                "updated_at": stale_update,
                "next_step": "Stage the travel workout plan.",
                "progress_signal": "Consistency matters more than intensity right now.",
                "support_message": "Let’s recover momentum without overcorrecting.",
                "work_state_summary": {},
                "background_prepared_outputs": [],
            }
        )
        self.assertEqual(payload["status"], "stalled")
        self.assertEqual(payload["stale_after_days"], 7)
        self.assertEqual(payload["days_since_update"], 10)
        self.assertIn("calm restart", payload["headline"])
        self.assertIn("Stage the travel workout plan.", payload["supportive_follow_up"])


if __name__ == "__main__":
    unittest.main()
