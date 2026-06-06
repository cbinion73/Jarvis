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


class AppleRemindersStateStoreTests(unittest.TestCase):
    def test_replays_reminders_state_from_append_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            reminders_path = Path(tmp) / "reminders.json"
            reminders_log_path = Path(tmp) / "reminders_log.jsonl"
            payload = {
                "reminders": [{"id": "r1", "title": "Call mom", "completed": False}],
                "count": 1,
                "source": "eventkit",
                "synced_at": "2026-06-02T12:00:00Z",
            }

            with (
                patch.object(apple_api, "_APPLE_REMINDERS_PATH", reminders_path),
                patch.object(apple_api, "_APPLE_REMINDERS_LOG_PATH", reminders_log_path),
            ):
                apple_api._safe_write_json(reminders_path, payload)
                reminders_path.write_text("", encoding="utf-8")

                loaded = apple_api._safe_read_json(reminders_path, {})

                self.assertEqual(loaded["count"], 1)
                self.assertEqual(loaded["reminders"][0]["title"], "Call mom")


if __name__ == "__main__":
    unittest.main()
