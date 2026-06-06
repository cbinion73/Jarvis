from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jarvis.home import HomeStore


class HomeStoreTests(unittest.TestCase):
    def test_replays_overrides_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = HomeStore(root)

            expected = store.save_override(
                "light.kitchen",
                state="on",
                attributes={"brightness": 80},
            )
            store.overrides_path.write_text("", encoding="utf-8")

            self.assertEqual(
                store.load_overrides(),
                {"light.kitchen": expected},
            )

    def test_replays_actions_from_state_log_when_snapshot_is_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = HomeStore(root)
            record = {
                "action_id": "action-1",
                "actor": "Chris",
                "category": "lights",
                "target": "light.kitchen",
                "action": "light.turn_on",
                "outcome": "simulated",
                "detail": "Turned on kitchen light.",
                "live_attempted": False,
                "timestamp": "2026-06-02T00:00:00+00:00",
            }

            store.add_action(record)
            store.actions_path.write_text("{broken", encoding="utf-8")

            self.assertEqual(store.list_actions(), [record])


if __name__ == "__main__":
    unittest.main()
