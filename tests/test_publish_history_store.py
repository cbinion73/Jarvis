from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from jarvis.publish_history import PublishHistoryStore


class PublishHistoryStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self._cwd = Path.cwd()
        self._tmpdir = tempfile.TemporaryDirectory()
        os.chdir(self._tmpdir.name)

    def tearDown(self) -> None:
        os.chdir(self._cwd)
        self._tmpdir.cleanup()

    def test_record_event_preserves_latest_first(self) -> None:
        store = PublishHistoryStore(Path("data/system"))
        first = store.record_event(
            actor_id="chris",
            event_type="project-created",
            title="Create Draft Project",
            detail="Created a draft launch project.",
            status_label="Draft Created",
            project_id="pub-1",
        )
        second = store.record_event(
            actor_id="chris",
            event_type="review-approved",
            title="Approve Publish Review",
            detail="Approved launch chapter review.",
            status_label="Approved",
            review_id="rev-1",
        )

        rows = store.list_history("chris", limit=4)

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["history_id"], second["history_id"])
        self.assertEqual(rows[1]["history_id"], first["history_id"])
        self.assertEqual(rows[0]["status_label"], "Approved")

    def test_summary_replays_from_state_log_when_snapshot_missing(self) -> None:
        store = PublishHistoryStore(Path("data/system"))
        saved = store.record_event(
            actor_id="chris",
            event_type="checklist-completed",
            title="Complete Publish Checklist Step",
            detail="Marked pricing set complete.",
            status_label="Completed",
            project_id="pub-1",
            step="pricing_set",
        )

        store.path.unlink()

        summary = store.summary("chris", limit=4)

        self.assertEqual(summary["count"], 1)
        self.assertEqual(summary["counts"]["completed"], 1)
        self.assertEqual(summary["items"][0]["history_id"], saved["history_id"])


if __name__ == "__main__":
    unittest.main()
