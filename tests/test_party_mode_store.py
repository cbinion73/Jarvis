from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jarvis.party_mode import PartyModeController, PartySession


class PartyModeStoreTests(unittest.TestCase):
    def test_replays_saved_sessions_from_append_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            controller = PartyModeController()
            controller._sessions_path = Path(tmp) / "party_sessions.jsonl"
            controller._sessions_state_log_path = Path(tmp) / "party_sessions_state_log.jsonl"

            records = [
                {
                    "session_id": "sess-1",
                    "started_at": "2026-06-02T01:00:00+00:00",
                    "ended_at": "2026-06-02T02:00:00+00:00",
                    "status": "completed",
                    "dossiers_built": ["work-1"],
                    "dossiers_attempted": 1,
                    "items_dreamed": 2,
                    "items_researched": 1,
                    "agent_log": ["done"],
                    "triggered_by": "manual",
                }
            ]

            controller._persist_saved_sessions(records)
            controller._sessions_path.write_text("", encoding="utf-8")

            loaded = controller._load_saved_sessions()

            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0]["session_id"], "sess-1")
            self.assertEqual(loaded[0]["dossiers_built"], ["work-1"])

    def test_finalize_session_persists_through_recoverable_store(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            controller = PartyModeController()
            controller._sessions_path = Path(tmp) / "party_sessions.jsonl"
            controller._sessions_state_log_path = Path(tmp) / "party_sessions_state_log.jsonl"
            session = PartySession(
                session_id="sess-2",
                started_at="2026-06-02T01:00:00+00:00",
                dossiers_built=["work-2"],
            )

            controller._finalize_session(session)
            controller._sessions_path.write_text("", encoding="utf-8")

            loaded = controller._load_saved_sessions()

            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0]["session_id"], "sess-2")
            self.assertEqual(loaded[0]["status"], "completed")


if __name__ == "__main__":
    unittest.main()
