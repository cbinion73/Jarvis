from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jarvis.perception import PerceptionStore


class PerceptionStoreTests(unittest.TestCase):
    def test_replays_microphone_events_from_append_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = PerceptionStore(root)
            record = {
                "event_id": "mic-1",
                "microphone": "kitchen",
                "transcript": "Jarvis, turn on the lights",
                "timestamp": "2026-06-02T00:00:00+00:00",
            }

            store.append_record(store.microphone_events_path, record)
            store.microphone_events_path.write_text("", encoding="utf-8")

            self.assertEqual(store.list_records(store.microphone_events_path), [record])

    def test_replays_privacy_state_from_append_log_when_snapshot_is_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = PerceptionStore(root)
            payload = {
                "cameras": {"front-door": {"enabled": True, "zone": "entry"}},
                "microphones": {"kitchen": {"muted": False, "zone": "kitchen"}},
                "physicalMuteRequired": True,
                "sensitiveZones": ["bedroom"],
                "lastUpdated": "2026-06-02T00:00:00+00:00",
            }

            store.save_privacy_state(payload)
            store.privacy_state_path.write_text("{broken", encoding="utf-8")

            self.assertEqual(store.load_privacy_state(), payload)


if __name__ == "__main__":
    unittest.main()
