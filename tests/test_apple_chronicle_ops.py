from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from jarvis.apple_api import (
    _capture_chronicle_entry,
    _mark_chronicle_prayer_answered,
    _mark_chronicle_prayer_prayed,
    _review_chronicle_entry,
    _save_chronicle_study_entry,
)
from jarvis.audit import AuditLog, ProgressFocusStore


class AppleChronicleOpsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._cwd = Path.cwd()
        self._tmpdir = tempfile.TemporaryDirectory()
        os.chdir(self._tmpdir.name)

    def tearDown(self) -> None:
        os.chdir(self._cwd)
        self._tmpdir.cleanup()

    def test_capture_chronicle_entry_persists_focus_and_activity(self) -> None:
        result = _capture_chronicle_entry(
            entry_type="reflection",
            note="Gratitude in the middle of fatigue.",
            actor="chris",
        )

        self.assertTrue(result["captured"])
        self.assertEqual(result["focus"]["module"], "Chronicle")

        summary = ProgressFocusStore(Path("data/logs")).summary(limit=4)
        self.assertEqual(summary["latest"]["module"], "Chronicle")

        recent = AuditLog(Path("data/logs")).list_recent(limit=3, entry_type="operator-action")
        self.assertEqual(recent[0]["action"], "Capture Chronicle Note")
        self.assertEqual(recent[0]["related_label"], "Gratitude in the middle of fatigue.")

        entries_path = Path("data/chronicle/entries.jsonl")
        self.assertTrue(entries_path.exists())
        rows = [json.loads(line) for line in entries_path.read_text().splitlines() if line.strip()]
        self.assertEqual(rows[-1]["entry_type"], "reflection")

    def test_prayer_and_study_actions_update_shared_focus(self) -> None:
        prayed = _mark_chronicle_prayer_prayed(
            prayer_id="prayer-1",
            actor="chris",
            note="Prayed through this on the walk home.",
        )
        answered = _mark_chronicle_prayer_answered(
            prayer_id="prayer-1",
            actor="chris",
            note="This was answered through an unexpected family conversation.",
        )
        study = _save_chronicle_study_entry(
            actor="chris",
            title="Evening Reflection",
            passage="Psalm 23",
            notes="The study pulled me back toward trust and patience.",
        )

        self.assertEqual(prayed["status"], "prayed")
        self.assertEqual(answered["status"], "answered")
        self.assertTrue(study["captured"])
        self.assertEqual(study["focus"]["module"], "Chronicle")

        summary = ProgressFocusStore(Path("data/logs")).summary(limit=6)
        self.assertEqual(summary["latest"]["module"], "Chronicle")

        recent = AuditLog(Path("data/logs")).list_recent(limit=6, entry_type="operator-action")
        titles = [item.get("action") for item in recent]
        self.assertIn("Log Chronicle Prayer", titles)
        self.assertIn("Mark Chronicle Prayer Answered", titles)
        self.assertIn("Save Chronicle Study", titles)

    def test_review_chronicle_entry_updates_shared_focus_and_review_lane(self) -> None:
        capture = _capture_chronicle_entry(
            entry_type="reflection",
            note="Remember how calm arrived after the hard conversation.",
            actor="chris",
        )

        result = _review_chronicle_entry(
            entry_id=capture["entry_id"],
            actor="chris",
            title="Remember how calm arrived after the hard conversation.",
            entry_type="reflection",
            status="family",
            note="Carry this into family devotional prep.",
        )

        self.assertEqual(result["status"], "recorded")
        self.assertEqual(result["review"]["review_status_label"], "Queue Family Handoff")
        self.assertEqual(result["focus"]["module"], "Chronicle")

        recent = AuditLog(Path("data/logs")).list_recent(limit=4, entry_type="operator-action")
        self.assertEqual(recent[0]["action"], "Queue Family Handoff")
        self.assertEqual(recent[0]["related_kind"], "chronicle-review")


if __name__ == "__main__":
    unittest.main()
