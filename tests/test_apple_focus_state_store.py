from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import importlib
import sys
import types
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


class AppleFocusStateStoreTests(unittest.TestCase):
    def test_replays_focus_state_from_append_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            focus_path = Path(tmp) / "focus_state.json"
            focus_log_path = Path(tmp) / "focus_state_log.jsonl"
            payload = {
                "focus_active": True,
                "mode": "deep_work",
                "updated_at": "2026-06-02T12:00:00Z",
            }

            with (
                patch.object(apple_api, "_FOCUS_STATE_PATH", focus_path),
                patch.object(apple_api, "_FOCUS_STATE_LOG_PATH", focus_log_path),
            ):
                apple_api._safe_write_json(focus_path, payload)
                focus_path.write_text("", encoding="utf-8")

                loaded = apple_api._safe_read_json(focus_path, {})

                self.assertTrue(loaded["focus_active"])
                self.assertEqual(loaded["mode"], "deep_work")


if __name__ == "__main__":
    unittest.main()
