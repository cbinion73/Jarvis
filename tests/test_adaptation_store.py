from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jarvis.adaptation import AdaptationStore


class AdaptationStoreTests(unittest.TestCase):
    def test_replays_adaptation_payload_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "adaptation_profiles.json"
            store = AdaptationStore(path=path)
            payload = {
                "profiles": {
                    "chris": {
                        "generated_at": "2026-06-02T00:00:00+00:00",
                        "digital_twin": {"headline": "Best in quiet morning focus."},
                        "signal_counts": {"first_light": 3},
                    }
                },
                "history": [
                    {
                        "user_id": "chris",
                        "generated_at": "2026-06-02T00:00:00+00:00",
                        "summary": "Best in quiet morning focus.",
                        "signals": {"first_light": 3},
                    }
                ],
                "personalization": {
                    "settings": {"chris": {"enabled": True}},
                    "history": [],
                },
            }

            store.save(payload)
            path.write_text("", encoding="utf-8")
            store.log_path.write_text("", encoding="utf-8")

            replayed = AdaptationStore(path=path)
            self.assertEqual(replayed.load(), payload)


if __name__ == "__main__":
    unittest.main()
