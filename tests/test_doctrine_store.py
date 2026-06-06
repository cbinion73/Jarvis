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


if __name__ == "__main__":
    unittest.main()
