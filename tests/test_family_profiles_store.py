from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jarvis.family_profiles import FamilyModeManager


class FamilyProfilesStoreTests(unittest.TestCase):
    def test_replays_mode_state_from_state_log_when_snapshot_is_blank(self) -> None:
        original_root = FamilyModeManager.ROOT
        with tempfile.TemporaryDirectory() as tmp:
            FamilyModeManager.ROOT = Path(tmp)
            try:
                manager = FamilyModeManager()
                manager.set_mode("focus", triggered_by="manual")
                manager.set_active_actor("rebekah")

                manager._mode_path().write_text("", encoding="utf-8")
                manager._mode_log_path().write_text("", encoding="utf-8")

                replayed = FamilyModeManager()

                self.assertEqual(replayed.get_current_mode().mode_id, "focus")
                self.assertEqual(replayed.get_active_actor(), "rebekah")
                self.assertTrue(replayed._mode_since)
            finally:
                FamilyModeManager.ROOT = original_root


if __name__ == "__main__":
    unittest.main()
