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


if __name__ == "__main__":
    unittest.main()
