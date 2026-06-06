from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jarvis.wealth import WealthLeverageStore


class WealthLeverageStoreTests(unittest.TestCase):
    def test_replays_outcomes_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = WealthLeverageStore(root)
            record = {
                "entry_id": "wealth-1",
                "timestamp": "2026-06-02T00:00:00+00:00",
                "request": "Increase passive income",
                "workflow": "wealth-and-leverage",
            }

            store.append(record)
            store.path.write_text("", encoding="utf-8")

            self.assertEqual(store.recent(), [record])

    def test_replays_finance_state_from_state_log_when_snapshot_is_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = WealthLeverageStore(root)
            payload = {
                "updated_at": "2026-06-02T00:00:00+00:00",
                "family_finance": {"cash": {"available": 12000}},
                "wealth": {"capital": {"wealth_account_available": 50000}},
            }

            store.save_finance_state(payload)
            store.finance_state_path.write_text("{broken", encoding="utf-8")

            self.assertEqual(store.finance_state(), payload)


if __name__ == "__main__":
    unittest.main()
