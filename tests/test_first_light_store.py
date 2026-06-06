from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jarvis.first_light import FirstLightStore


class FirstLightStoreTests(unittest.TestCase):
    def test_replays_first_light_state_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "first_light.json"
            store = FirstLightStore(path=path)
            packet = {
                "packet_id": "pkt-1",
                "user_id": "chris",
                "headline": "Hydrate and start with the most important thing.",
            }

            user_state = store.mark_presented("chris", packet, "America/New_York")

            path.write_text("", encoding="utf-8")
            store.log_path.write_text("", encoding="utf-8")
            replayed = FirstLightStore(path=path)
            status = replayed.status("chris", "America/New_York")

            self.assertEqual(user_state["last_packet_id"], "pkt-1")
            self.assertTrue(status["already_presented_today"])
            self.assertEqual(status["latest_packet"]["packet_id"], "pkt-1")
            self.assertEqual(status["latest_packet"]["headline"], packet["headline"])


if __name__ == "__main__":
    unittest.main()
