from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jarvis.catalyst import CatalystStore


class CatalystStoreTests(unittest.TestCase):
    def test_replays_pipeline_state_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = CatalystStore(Path(tmp))

            saved = store.update_pipeline_state(
                {
                    "active_lane": "family-savings",
                    "review": {"status": "staged", "owner": "jarvis"},
                }
            )

            store.pipeline_state_path.write_text("", encoding="utf-8")
            store._log_path(store.pipeline_state_path).write_text("", encoding="utf-8")
            loaded = store.pipeline_state()

            self.assertEqual(loaded["active_lane"], saved["active_lane"])
            self.assertEqual(loaded["review"]["status"], "staged")
            self.assertEqual(loaded["review"]["owner"], "jarvis")

    def test_replays_work_lifecycle_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = CatalystStore(Path(tmp))

            saved = store.save_work_lifecycle(
                [
                    {
                        "work_id": "work-1",
                        "title": "Review savings lever",
                        "status": "planned",
                    }
                ]
            )

            store.work_lifecycle_path.write_text("", encoding="utf-8")
            store._log_path(store.work_lifecycle_path).write_text("", encoding="utf-8")
            loaded = store.work_lifecycle()

            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0]["work_id"], saved[0]["work_id"])
            self.assertEqual(loaded[0]["title"], "Review savings lever")


if __name__ == "__main__":
    unittest.main()
