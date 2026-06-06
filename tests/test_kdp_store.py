from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jarvis import kdp_store


class KDPStoreTests(unittest.TestCase):
    def test_replays_books_and_sync_meta_from_logs_when_snapshots_are_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            books_path = data_dir / "books.json"
            books_log_path = data_dir / "books_log.jsonl"
            sales_path = data_dir / "sales_history.jsonl"
            sales_state_log_path = data_dir / "sales_history_state_log.jsonl"
            sync_meta_path = data_dir / "sync_meta.json"
            sync_meta_log_path = data_dir / "sync_meta_log.jsonl"

            with (
                patch.object(kdp_store, "KDP_DATA_DIR", data_dir),
                patch.object(kdp_store, "BOOKS_PATH", books_path),
                patch.object(kdp_store, "BOOKS_LOG_PATH", books_log_path),
                patch.object(kdp_store, "SALES_PATH", sales_path),
                patch.object(kdp_store, "SALES_STATE_LOG_PATH", sales_state_log_path),
                patch.object(kdp_store, "SYNC_META_PATH", sync_meta_path),
                patch.object(kdp_store, "SYNC_META_LOG_PATH", sync_meta_log_path),
            ):
                kdp_store.save_sync_result(
                    {
                        "books": [{"asin": "B001", "title": "Shared Ownership"}],
                        "sales": {"units": 3},
                        "synced_at": "2026-06-02T12:00:00Z",
                        "ok": True,
                    }
                )

                books_path.write_text("", encoding="utf-8")
                sync_meta_path.write_text("", encoding="utf-8")

                books = kdp_store.load_books()
                sales = kdp_store.load_sales_history()
                meta = kdp_store.load_sync_meta()

                self.assertEqual(len(books), 1)
                self.assertEqual(books[0]["asin"], "B001")
                self.assertEqual(len(sales), 1)
                self.assertEqual(sales[0]["units"], 3)
                self.assertEqual(meta["book_count"], 1)
                self.assertEqual(meta["status"], "synced")


if __name__ == "__main__":
    unittest.main()
