from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jarvis.content_ops import ContentOpsStore


class ContentOpsStoreTests(unittest.TestCase):
    def test_replays_queue_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = ContentOpsStore(root)
            record = {
                "queue_id": "queue-1",
                "status": "queued",
                "title": "Launch clip",
                "timestamp": "2026-06-02T00:00:00+00:00",
            }

            store.add_record(store.queue_path, record)
            store.queue_path.write_text("", encoding="utf-8")
            store._log_paths[store.queue_path].write_text("", encoding="utf-8")

            self.assertEqual(store.list_records(store.queue_path), [record])

    def test_replays_marketing_state_from_state_log_when_snapshot_is_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = ContentOpsStore(root)
            payload = {
                "updated_at": "2026-06-02T00:00:00+00:00",
                "campaigns": [{"campaign_id": "camp-1", "status": "live"}],
                "offer_links": [],
                "audience_signals": [],
                "thresholds": {"minimum_live_assets": 1},
                "notes": ["Keep queue warm."],
            }

            store.save_marketing_state(payload)
            store.marketing_state_path.write_text("{broken", encoding="utf-8")
            store._log_paths[store.marketing_state_path].write_text("", encoding="utf-8")

            self.assertEqual(store.marketing_state(), payload)


if __name__ == "__main__":
    unittest.main()
