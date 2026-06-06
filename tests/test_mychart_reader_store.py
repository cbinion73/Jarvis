from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jarvis import mychart_reader


class MyChartReaderStoreTests(unittest.TestCase):
    def test_replays_records_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            health_dir = Path(tmp)
            records_path = health_dir / "mychart_records.json"
            records_log_path = health_dir / "mychart_records_log.jsonl"
            records_state_log_path = health_dir / "mychart_records_state_log.jsonl"

            with (
                patch.object(mychart_reader, "_HEALTH_DIR", health_dir),
                patch.object(mychart_reader, "_RECORDS_PATH", records_path),
                patch.object(mychart_reader, "_RECORDS_LOG_PATH", records_log_path),
                patch.object(mychart_reader, "_RECORDS_STATE_LOG_PATH", records_state_log_path),
            ):
                saved = mychart_reader.store_page_data("medications", "<div>Aspirin 81mg</div>")

                records_path.write_text("", encoding="utf-8")
                records_log_path.write_text("", encoding="utf-8")
                loaded = mychart_reader.load_records()

                self.assertEqual(loaded["last_updated"], saved["last_updated"])
                self.assertIn("medications", loaded)
                self.assertEqual(loaded["medications"]["page_type"], "html")
                self.assertIn("Aspirin", loaded["medications"]["content"])


if __name__ == "__main__":
    unittest.main()
