from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jarvis.financial_intelligence import Account, BudgetTracker, FinancialStore, Transaction


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

    def test_merges_manual_and_linked_transactions_without_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            FinancialStore.ROOT = Path(tmp) / "finance"
            store = FinancialStore()

            manual = Transaction(
                transaction_id="manual-1",
                account_id="acct-manual",
                date="2026-06-10",
                description="Manual grocery",
                amount=-42.5,
                category="food",
            )
            linked = Transaction(
                transaction_id="plaid:txn-1",
                account_id="plaid:acct-1",
                date="2026-06-09",
                description="Linked salary",
                amount=1200.0,
                category="income",
                source_agent="plaid",
            )

            store.append_transaction(manual)
            store.upsert_linked_transactions([linked])

            replayed = store.load_transactions()

            self.assertEqual(len(replayed), 2)
            ids = {txn.transaction_id for txn in replayed}
            self.assertIn("manual-1", ids)
            self.assertIn("plaid:txn-1", ids)


if __name__ == "__main__":
    unittest.main()
