from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from jarvis.health_checkins import HealthCheckInStore


class HealthCheckInStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self._cwd = Path.cwd()
        self._tmpdir = tempfile.TemporaryDirectory()
        os.chdir(self._tmpdir.name)

    def tearDown(self) -> None:
        os.chdir(self._cwd)
        self._tmpdir.cleanup()

    def test_save_and_list_checkins_preserve_latest_first(self) -> None:
        store = HealthCheckInStore(Path("data/system"))
        first = store.save_checkin(
            actor_id="chris",
            symptoms="Brain fog",
            note="Started after a short night of sleep.",
            energy_level=3,
            sleep_hours=5.0,
            stress_level=6,
            source="unit-test",
        )
        second = store.save_checkin(
            actor_id="chris",
            symptoms="Recovered after walk",
            note="Energy improved after lunch walk.",
            energy_level=7,
            sleep_hours=7.0,
            stress_level=3,
            source="unit-test",
        )

        entries = store.list_checkins("chris", limit=4)

        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["checkin_id"], second["checkin_id"])
        self.assertEqual(entries[1]["checkin_id"], first["checkin_id"])
        self.assertEqual(entries[0]["energy_level"], 7)
        self.assertEqual(entries[0]["sleep_hours"], 7.0)
        self.assertEqual(entries[0]["stress_level"], 3)

    def test_store_replays_from_state_log_when_snapshot_missing(self) -> None:
        store = HealthCheckInStore(Path("data/system"))
        saved = store.save_checkin(
            actor_id="chris",
            symptoms="Low energy",
            note="Using the replay path.",
            energy_level=4,
            sleep_hours=6.0,
            stress_level=5,
            source="unit-test",
        )

        store.path.unlink()

        replayed = store.list_checkins("chris", limit=2)

        self.assertEqual(len(replayed), 1)
        self.assertEqual(replayed[0]["checkin_id"], saved["checkin_id"])
        self.assertEqual(replayed[0]["note"], "Using the replay path.")


if __name__ == "__main__":
    unittest.main()
