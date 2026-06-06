from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from jarvis.chronicle_reviews import ChronicleReviewStore


class ChronicleReviewStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self._cwd = Path.cwd()
        self._tmpdir = tempfile.TemporaryDirectory()
        os.chdir(self._tmpdir.name)

    def tearDown(self) -> None:
        os.chdir(self._cwd)
        self._tmpdir.cleanup()

    def test_review_entry_persists_and_updates(self) -> None:
        store = ChronicleReviewStore()

        first = store.review_entry(
            entry_id="entry-1",
            actor_id="chris",
            title="Evening Gratitude",
            entry_type="reflection",
            status="study",
            note="Use this in tomorrow morning study.",
        )
        second = store.review_entry(
            entry_id="entry-1",
            actor_id="chris",
            title="Evening Gratitude",
            entry_type="reflection",
            status="family",
            note="Share this with the family devotional.",
        )

        self.assertEqual(first["review_status_label"], "Study Next")
        self.assertEqual(second["review_status_label"], "Queue Family Handoff")

        summary = store.review_summary(actor_id="chris", limit=4)
        self.assertEqual(summary["count"], 1)
        self.assertEqual(summary["counts"]["family"], 1)
        self.assertEqual(summary["items"][0]["entry_title"], "Evening Gratitude")


if __name__ == "__main__":
    unittest.main()
