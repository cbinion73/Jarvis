from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jarvis.doctrine import SharedDoctrineStore


class SharedDoctrineStoreTests(unittest.TestCase):
    def test_replays_doctrine_state_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            doctrine_path = Path(tmp) / "shared_doctrine.json"
            store = SharedDoctrineStore(doctrine_path)

            saved = store.replace_candidates(
                [
                    {
                        "candidate_id": "cand-1",
                        "title": "Promote reviewed pattern",
                        "status": "pending",
                    }
                ],
                synthesis_meta={"source": "test"},
            )

            doctrine_path.write_text("", encoding="utf-8")
            store._log_path().write_text("", encoding="utf-8")
            loaded = store.load()

            self.assertEqual(loaded["generated_at"], saved["generated_at"])
            self.assertEqual(len(loaded["candidates"]), 1)
            self.assertEqual(loaded["candidates"][0]["candidate_id"], "cand-1")
            self.assertEqual(loaded["last_synthesis"]["source"], "test")

    def test_filters_seeded_doctrine_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            doctrine_path = Path(tmp) / "shared_doctrine.json"
            store = SharedDoctrineStore(doctrine_path)
            doctrine_path.write_text(
                """
{
  "generated_at": "2026-06-10T00:00:00Z",
  "candidates": [
    {"candidate_id": "demo", "title": "Draft a parent message about tonight's troop meeting"},
    {"candidate_id": "real", "title": "Real governed doctrine"}
  ],
  "rules": [
    {"rule_id": "rule-demo", "summary": "Indoor backup update for Troop parents"},
    {"rule_id": "rule-real", "summary": "Review successful interventions weekly"}
  ],
  "history": [
    {"event": "synthesized", "note": "Please keep prayers for Sarah in front of the team."},
    {"event": "synthesized", "note": "Real history"}
  ],
  "last_synthesis": {}
}
                """.strip(),
                encoding="utf-8",
            )

            loaded = store.load()

        self.assertEqual([item["candidate_id"] for item in loaded["candidates"]], ["real"])
        self.assertEqual([item["rule_id"] for item in loaded["rules"]], ["rule-real"])
        self.assertEqual(len(loaded["history"]), 1)
        self.assertEqual(loaded["history"][0]["note"], "Real history")


if __name__ == "__main__":
    unittest.main()
