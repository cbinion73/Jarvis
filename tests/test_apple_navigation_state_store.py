from __future__ import annotations

import importlib
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch


if "fastapi" not in sys.modules:
    fastapi_stub = types.ModuleType("fastapi")
    responses_stub = types.ModuleType("fastapi.responses")
    staticfiles_stub = types.ModuleType("fastapi.staticfiles")
    uvicorn_stub = types.ModuleType("uvicorn")

    class _Route:  # pragma: no cover - test stub only
        def __init__(self, path: str, methods: set[str], endpoint) -> None:
            self.path = path
            self.methods = methods
            self.endpoint = endpoint

    class _Router:  # pragma: no cover - test stub only
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
        pass

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

    class _JSONResponse:  # pragma: no cover - test stub only
        def __init__(self, content=None, status_code: int = 200, headers: dict | None = None) -> None:
            self.body = b"{}"
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

    def _return_default(value=None, **kwargs):  # pragma: no cover - test stub only
        return value

    fastapi_stub.FastAPI = _FastAPI
    fastapi_stub.HTTPException = _HTTPException
    fastapi_stub.BackgroundTasks = _BackgroundTasks
    fastapi_stub.Request = _Request
    fastapi_stub.UploadFile = _UploadFile
    fastapi_stub.WebSocket = _WebSocket
    fastapi_stub.WebSocketDisconnect = _WebSocketDisconnect
    fastapi_stub.File = _return_default
    fastapi_stub.Form = _return_default
    fastapi_stub.Query = _return_default
    responses_stub.JSONResponse = _JSONResponse
    responses_stub.HTMLResponse = _HTMLResponse
    responses_stub.Response = _Response
    responses_stub.FileResponse = _FileResponse
    responses_stub.RedirectResponse = _RedirectResponse
    staticfiles_stub.StaticFiles = _StaticFiles
    sys.modules["fastapi"] = fastapi_stub
    sys.modules["fastapi.responses"] = responses_stub
    sys.modules["fastapi.staticfiles"] = staticfiles_stub
    sys.modules["uvicorn"] = uvicorn_stub

apple_api = importlib.import_module("jarvis.apple_api")


class AppleNavigationStateStoreTests(unittest.TestCase):
    def test_replays_navigation_state_from_append_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            nav_path = Path(tmp) / "navigation_state.json"
            nav_log_path = Path(tmp) / "navigation_state_log.jsonl"

            with (
                patch.object(apple_api, "_NAVIGATION_STATE_PATH", nav_path),
                patch.object(apple_api, "_NAVIGATION_STATE_LOG_PATH", nav_log_path),
            ):
                saved = apple_api._save_navigation_state(
                    {
                        "favorite_destinations": ["Office"],
                        "selected_origin_mode": "saved_location",
                        "selected_saved_location_id": "hq",
                    }
                )
                nav_path.write_text("", encoding="utf-8")

                loaded = apple_api._load_navigation_state()

                self.assertEqual(saved["favorite_destinations"], ["Office"])
                self.assertEqual(loaded["favorite_destinations"], ["Office"])
                self.assertEqual(loaded["selected_saved_location_id"], "hq")

    def test_route_history_persists_and_resume_updates_focus_and_audit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            nav_path = Path(tmp) / "navigation_state.json"
            nav_log_path = Path(tmp) / "navigation_state_log.jsonl"
            audit_root = Path(tmp) / "logs"

            with (
                patch.object(apple_api, "_NAVIGATION_STATE_PATH", nav_path),
                patch.object(apple_api, "_NAVIGATION_STATE_LOG_PATH", nav_log_path),
                patch.object(apple_api, "_ACTIVITY_AUDIT_ROOT", audit_root),
            ):
                saved, entry = apple_api._record_navigation_route_history(
                    origin="Home Base",
                    destination="Office",
                    origin_mode="home",
                    source_label="Navigation route preview",
                )
                resumed = apple_api._resume_navigation_route_history(route_id=entry["route_id"], actor="Chris")

            self.assertEqual(saved["last_route"]["destination"], "Office")
            self.assertEqual(len(saved["route_history"]), 1)
            self.assertEqual(saved["route_history"][0]["preview_count"], 1)
            self.assertEqual(resumed["state"]["last_route"]["origin"], "Home Base")
            self.assertEqual(resumed["route"]["resume_count"], 1)
            self.assertEqual(resumed["focus"]["module"], "Navigation")
            recent = apple_api.AuditLog(audit_root).list_recent(limit=3, entry_type="operator-action")
            self.assertTrue(any(item.get("action") == "Resume Navigation Route" for item in recent))

    def test_records_operator_action_into_activity_audit_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            audit_root = Path(tmp) / "logs"

            with patch.object(apple_api, "_ACTIVITY_AUDIT_ROOT", audit_root):
                apple_api._record_operator_action(
                    actor="Chris",
                    domain="navigation",
                    action="Update Apple Navigation State",
                    detail="Persisted route from Home to Office.",
                    why_now="Apple surface selected or refreshed a route destination.",
                    result_summary="Navigation continuity updated from Apple route state.",
                    route="/navigation-center",
                    route_label="Open Navigation",
                    related_kind="route-preview",
                    related_label="Office",
                )

            records = apple_api.AuditLog(audit_root).list_recent()

            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["entry_type"], "operator-action")
            self.assertEqual(records[0]["actor"], "Chris")
            self.assertEqual(records[0]["domain"], "navigation")
            self.assertEqual(records[0]["related_route"], "/navigation-center")
            self.assertEqual(records[0]["route_label"], "Open Navigation")
            self.assertEqual(records[0]["related_kind"], "route-preview")
            self.assertEqual(records[0]["related_label"], "Office")
            self.assertEqual(records[0]["result_summary"], "Navigation continuity updated from Apple route state.")


if __name__ == "__main__":
    unittest.main()
