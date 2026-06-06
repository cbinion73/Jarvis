from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jarvis.models import DeviceBoundaryRoutine, TutoringSession
from jarvis.tutoring import TutoringStore


class TutoringStoreTests(unittest.TestCase):
    def test_replays_sessions_from_append_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = TutoringStore(Path(tmp))
            session = TutoringSession(
                session_id="sess-1",
                actor="Caleb",
                subject="math",
                request="Help me study fractions",
                coaching_mode="guided-practice",
                response_text="Let's break it down.",
                parent_summary="Practiced fractions.",
                boundary_status="allowed",
                encouragement="You can do this.",
                follow_up="Try one more example.",
                frustration_signal="calm",
                timestamp="2026-06-02T12:00:00+00:00",
            )

            store.add_session(session)
            store.sessions_path.write_text("", encoding="utf-8")

            records = store.list_sessions("Caleb")

            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["subject"], "math")
            self.assertEqual(records[0]["actor"], "Caleb")

    def test_replays_boundaries_from_append_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = TutoringStore(Path(tmp))
            routine = DeviceBoundaryRoutine(
                routine_id="routine-1",
                actor="Caleb",
                window_label="Evening dock",
                checklist=["Dock tablet", "Reset desk"],
                device_expectation="No devices after 8pm",
                reminder_text="Dock the device and reset the desk.",
                status="active",
                timestamp="2026-06-02T22:00:00+00:00",
            )

            store.add_boundary(routine)
            store.boundaries_path.write_text("", encoding="utf-8")

            records = store.list_boundaries("Caleb")

            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["routine_id"], "routine-1")
            self.assertEqual(records[0]["status"], "active")


if __name__ == "__main__":
    unittest.main()
