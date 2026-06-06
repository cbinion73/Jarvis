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

    class _FastAPI:  # pragma: no cover - test stub only
        pass

    class _HTTPException(Exception):  # pragma: no cover - test stub only
        pass

    fastapi_stub.FastAPI = _FastAPI
    fastapi_stub.HTTPException = _HTTPException
    sys.modules["fastapi"] = fastapi_stub

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
