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


class AppleCalendarStateStoreTests(unittest.TestCase):
    def test_replays_calendar_state_from_append_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            calendar_path = Path(tmp) / "calendar_events.json"
            calendar_log_path = Path(tmp) / "calendar_events_log.jsonl"
            payload = {
                "events": [{"id": "e1", "title": "Doctor Visit"}],
                "count": 1,
                "source": "eventkit",
                "synced_at": "2026-06-02T12:00:00Z",
            }

            with (
                patch.object(apple_api, "_APPLE_CALENDAR_PATH", calendar_path),
                patch.object(apple_api, "_APPLE_CALENDAR_LOG_PATH", calendar_log_path),
            ):
                apple_api._safe_write_json(calendar_path, payload)
                calendar_path.write_text("", encoding="utf-8")

                loaded = apple_api._safe_read_json(calendar_path, {})

                self.assertEqual(loaded["count"], 1)
                self.assertEqual(loaded["events"][0]["title"], "Doctor Visit")


if __name__ == "__main__":
    unittest.main()
