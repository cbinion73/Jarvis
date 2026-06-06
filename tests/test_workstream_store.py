from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jarvis.workstreams import AutonomousWorkstreamStore


class AutonomousWorkstreamStoreTests(unittest.TestCase):
    def test_replays_state_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = AutonomousWorkstreamStore(Path(tmp))

            saved = store.save_state(
                {
                    "mission": "Run bounded autonomous work",
                    "updated_at": "2026-06-02T12:00:00Z",
                    "lanes": [{"lane_id": "passive-income", "label": "Passive Income"}],
                }
            )

            store.state_path.write_text("", encoding="utf-8")
            store._log_path(store.state_path).write_text("", encoding="utf-8")
            loaded = store.state()

            self.assertEqual(loaded["mission"], saved["mission"])
            self.assertEqual(loaded["lanes"][0]["lane_id"], "passive-income")

    def test_replays_items_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = AutonomousWorkstreamStore(Path(tmp))

            saved = store.save_items(
                [
                    {
                        "item_id": "item-1",
                        "lane_id": "passive-income",
                        "title": "Screen new income idea",
                        "status": "planned",
                    }
                ]
            )

            store.items_path.write_text("", encoding="utf-8")
            store._log_path(store.items_path).write_text("", encoding="utf-8")
            loaded = store.items()

            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0]["item_id"], saved[0]["item_id"])
            self.assertEqual(loaded[0]["title"], "Screen new income idea")


if __name__ == "__main__":
    unittest.main()
