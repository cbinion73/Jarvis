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


class ApplePrayerActivityStoreTests(unittest.TestCase):
    def test_replays_prayer_activity_from_append_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "prayer_activity.json"
            state_log_path = Path(tmp) / "prayer_activity_log.jsonl"
            payload = {
                "prayer-1": {
                    "times_prayed": 3,
                    "last_prayed_at": "2026-06-02T12:00:00Z",
                }
            }

            with (
                patch.object(apple_api, "_CHRONICLE_PRAYER_ACTIVITY_PATH", state_path),
                patch.object(apple_api, "_CHRONICLE_PRAYER_ACTIVITY_LOG_PATH", state_log_path),
            ):
                apple_api._safe_write_json(state_path, payload)
                state_path.write_text("", encoding="utf-8")

                loaded = apple_api._safe_read_json(state_path, {})

                self.assertEqual(loaded["prayer-1"]["times_prayed"], 3)
                self.assertEqual(loaded["prayer-1"]["last_prayed_at"], "2026-06-02T12:00:00Z")


if __name__ == "__main__":
    unittest.main()
