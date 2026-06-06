from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jarvis.agentic import BackgroundStateStore, LifeAgentStudioStore


class BackgroundStateStoreTests(unittest.TestCase):
    def test_replays_background_state_from_append_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = BackgroundStateStore(Path(tmp))
            payload = {
                "agents": {
                    "ambient-router": {
                        "state": "awake",
                        "last_run_at": "2026-06-02T12:00:00+00:00",
                    }
                },
                "last_tick_at": "2026-06-02T12:05:00+00:00",
            }

            store.save(payload)
            store.state_path.write_text("", encoding="utf-8")

            loaded = store.load()

            self.assertEqual(loaded["last_tick_at"], "2026-06-02T12:05:00+00:00")
            self.assertEqual(loaded["agents"]["ambient-router"]["state"], "awake")

    def test_replays_life_agent_profiles_from_append_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = LifeAgentStudioStore(Path(tmp))
            agents = store.default_agents()
            store.save(agents)
            store.path.write_text("", encoding="utf-8")

            loaded = store.load()

            self.assertTrue(loaded)
            self.assertEqual(loaded[0].agent_id, agents[0].agent_id)
            self.assertEqual(loaded[0].label, agents[0].label)


if __name__ == "__main__":
    unittest.main()
