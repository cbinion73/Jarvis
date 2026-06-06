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


class AppleNowPlayingStateStoreTests(unittest.TestCase):
    def test_replays_now_playing_state_from_append_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "now_playing.json"
            state_log_path = Path(tmp) / "now_playing_log.jsonl"
            payload = {
                "title": "Higher Ground",
                "artist": "Stevie Wonder",
                "album": "Innervisions",
                "is_playing": True,
                "updated_at": "2026-06-02T12:00:00Z",
            }

            with (
                patch.object(apple_api, "_APPLE_NOW_PLAYING_PATH", state_path),
                patch.object(apple_api, "_APPLE_NOW_PLAYING_LOG_PATH", state_log_path),
            ):
                apple_api._safe_write_json(state_path, payload)
                state_path.write_text("", encoding="utf-8")

                loaded = apple_api._safe_read_json(state_path, {})

                self.assertEqual(loaded["title"], "Higher Ground")
                self.assertTrue(loaded["is_playing"])


if __name__ == "__main__":
    unittest.main()
