from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jarvis.financial_intelligence import Account, BudgetTracker, FinancialStore


class FinancialStoreTests(unittest.TestCase):
    def test_replays_accounts_from_append_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            FinancialStore.ROOT = Path(tmp) / "finance"
            store = FinancialStore()
            account = Account(
                account_id="acct-1",
                name="Checking",
                account_type="checking",
                institution="Local Bank",
                balance=1234.56,
                currency="USD",
                last_updated="2026-06-02T22:00:00+00:00",
            )

            store.save_accounts([account])
            store._accounts_path.write_text("", encoding="utf-8")

            replayed = store.load_accounts()

            self.assertEqual(len(replayed), 1)
            self.assertEqual(replayed[0].account_id, "acct-1")
            self.assertEqual(replayed[0].balance, 1234.56)

    def test_replays_budgets_from_append_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            FinancialStore.ROOT = Path(tmp) / "finance"
            store = FinancialStore()
            tracker = BudgetTracker(store)

            tracker.set_budget("food", 950.0)
            tracker._budgets_path.write_text("", encoding="utf-8")

            replayed = tracker._load_budgets()

            self.assertEqual(replayed["food"], 950.0)


if __name__ == "__main__":
    unittest.main()
