from __future__ import annotations

import importlib
import sys
import tempfile
import types
import unittest
from pathlib import Path


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


class _NullEventLog:
    def record(self, **_: object) -> dict[str, object]:
        return {}


class AppleNotificationCenterStoreTests(unittest.TestCase):
    def test_notification_center_store_replays_from_append_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store_path = Path(tmp) / "notification_center.json"
            store = apple_api._NotificationCenterStore(store_path, _NullEventLog())

            created = store.create(
                category="system",
                title="Door left open",
                detail="Garage side door has been open for 12 minutes.",
                severity="medium",
                source_summary="Home alert",
            )

            store_path.write_text("", encoding="utf-8")

            replayed = store.get(str(created["id"]))

            self.assertIsNotNone(replayed)
            assert replayed is not None
            self.assertEqual(replayed["title"], "Door left open")
            self.assertEqual(replayed["severity"], "medium")


if __name__ == "__main__":
    unittest.main()
