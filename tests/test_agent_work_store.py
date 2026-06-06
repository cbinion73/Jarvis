from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jarvis.agent_work import AgentWorkStore


class AgentWorkStoreTests(unittest.TestCase):
    def test_replays_work_items_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = AgentWorkStore("pepper", base_dir=Path(tmp) / "pepper")

            item = store.dream_idea(
                title="Launch household logistics experiment",
                idea="Prototype a lower-friction pickup reminder flow.",
                domain="household",
                tags=["family", "logistics"],
                priority=3,
            )
            store._path.write_text("", encoding="utf-8")

            replayed = AgentWorkStore("pepper", base_dir=Path(tmp) / "pepper")
            proposed = replayed.all_items()

            self.assertEqual(len(proposed), 1)
            self.assertEqual(proposed[0].work_id, item.work_id)
            self.assertEqual(proposed[0].title, "Launch household logistics experiment")
            self.assertEqual(proposed[0].status, "dreamed")


if __name__ == "__main__":
    unittest.main()
