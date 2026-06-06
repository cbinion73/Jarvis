from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jarvis.trust import TrustStore


class TrustStoreTests(unittest.TestCase):
    def test_replays_trust_zones_from_append_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = TrustStore(root)
            records = [
                {
                    "zone_id": "household_schedule",
                    "name": "Household Schedule Routing",
                    "authority_stage": "sandbox_live",
                }
            ]

            store.save_trust_zones(records)
            store.trust_zones_path.write_text("", encoding="utf-8")

            self.assertEqual(store.list_trust_zones(), records)

    def test_replays_promotion_records_from_append_log_when_snapshot_is_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = TrustStore(root)
            records = [
                {
                    "record_id": "promo-1",
                    "subject_kind": "trust_zone",
                    "subject_id": "household_schedule",
                    "target_stage": "mature_live",
                }
            ]

            store.save_promotion_records(records)
            store.promotion_records_path.write_text("{broken", encoding="utf-8")

            self.assertEqual(store.list_promotion_records(), records)


if __name__ == "__main__":
    unittest.main()
