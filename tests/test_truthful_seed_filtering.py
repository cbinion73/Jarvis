from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from jarvis.audit import ApprovalStore
from jarvis.chronicle import ChronicleStore
from jarvis.data_hygiene import filter_records
from jarvis.family import FamilyStore
from jarvis.first_light import FirstLightStore


class TruthfulSeedFilteringTests(unittest.TestCase):
    def test_filter_records_removes_known_seeded_family_and_faith_content(self) -> None:
        records = [
            {"request": "Approve parent message to Troop parents about Indoor backup update"},
            {"text": "Please keep prayers for Sarah in front of the team."},
            {"subject": "Real connected note"},
        ]

        filtered = filter_records(records)

        self.assertEqual(filtered, [{"subject": "Real connected note"}])

    def test_family_store_hides_seeded_message_drafts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = FamilyStore(root)
            store.message_drafts_path.write_text(
                json.dumps(
                    [
                        {
                            "draft_id": "demo-1",
                            "audience": "Troop parents",
                            "purpose": "Indoor backup update",
                            "body": "Hi troop parents",
                            "status": "staged",
                        }
                    ]
                ),
                encoding="utf-8",
            )

            self.assertEqual(store.list_drafts(), [])

    def test_approval_store_hides_seeded_requests(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = ApprovalStore(root)
            store.pending_path.write_text(
                json.dumps(
                    [
                        {
                            "request_id": "demo-approval",
                            "status": "pending",
                            "request": "Draft a parent message about tonight's troop meeting",
                        }
                    ]
                ),
                encoding="utf-8",
            )

            self.assertEqual(store.list_all(), [])
            self.assertEqual(store.list_pending(), [])

    def test_first_light_store_hides_seeded_packets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "first_light.json"
            path.write_text(
                json.dumps(
                    {
                        "users": {"chris": {"last_packet_id": "demo"}},
                        "history": [
                            {
                                "packet_id": "demo",
                                "user_id": "chris",
                                "watch_line": "Rain may affect troop arrival later.",
                                "formation_cue": "Keep the morning in a low-friction lane.",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            store = FirstLightStore(path=path)

            payload = store.load()

            self.assertEqual(payload["history"], [])

    def test_chronicle_store_hides_seeded_reflections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = ChronicleStore(root)
            store.entries_path.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "timestamp": "2026-06-09T00:00:00+00:00",
                                "theme": "stewardship under pressure",
                                "note": "Today felt noisy",
                            }
                        ),
                        json.dumps(
                            {
                                "timestamp": "2026-06-09T00:00:01+00:00",
                                "theme": "real",
                                "note": "Keep going",
                            }
                        ),
                    ]
                ),
                encoding="utf-8",
            )

            recent = store.list_recent(limit=10)

            self.assertEqual(len(recent), 1)
            self.assertEqual(recent[0]["theme"], "real")


if __name__ == "__main__":
    unittest.main()
