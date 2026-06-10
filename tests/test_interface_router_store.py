from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jarvis.interfaces import InterfaceRouterStore


class InterfaceRouterStoreTests(unittest.TestCase):
    def test_replays_sessions_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = InterfaceRouterStore(Path(tmp))
            saved = store.save_session(
                {
                    "request_id": "req-1",
                    "target_system": "catalyst",
                    "status": "accepted",
                }
            )

            store.sessions_path.write_text("", encoding="utf-8")
            store._log_path(store.sessions_path).write_text("", encoding="utf-8")
            loaded = store.get_session("req-1")

            self.assertEqual(loaded, saved)

    def test_replays_results_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = InterfaceRouterStore(Path(tmp))
            saved = store.save_result(
                {
                    "request_id": "req-1",
                    "source_system": "chronicle",
                    "status": "completed",
                    "summary": "Done",
                }
            )

            store.results_path.write_text("", encoding="utf-8")
            store._log_path(store.results_path).write_text("", encoding="utf-8")
            loaded = store.get_result("req-1")

            self.assertEqual(loaded, saved)

    def test_filters_seeded_sessions_from_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = InterfaceRouterStore(Path(tmp))
            store.sessions_path.write_text(
                """
{
  "demo": {
    "request_id": "demo",
    "prompt": "Continue my formation thread in Chronicle for troop meeting follow-up"
  },
  "real": {
    "request_id": "real",
    "prompt": "Open Chronicle timeline"
  }
}
                """.strip(),
                encoding="utf-8",
            )

            self.assertIsNone(store.get_session("demo"))
            self.assertEqual(store.get_session("real")["request_id"], "real")


if __name__ == "__main__":
    unittest.main()
