from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jarvis import appointment_engine


class AppointmentEngineStoreTests(unittest.TestCase):
    def test_replays_appointments_from_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            health_dir = Path(tmp)
            appointments_path = health_dir / "appointments.json"
            outcomes_path = health_dir / "appointment_outcomes.jsonl"
            health_state_path = health_dir / "chris_health_state.json"

            appointments = [
                {
                    "id": "apt-1",
                    "provider": "Dr. Test",
                    "specialty": "Primary Care",
                    "date": "2026-06-03",
                    "time": "09:00",
                    "location": "Clinic",
                    "reason": "Follow-up",
                    "prep_required": True,
                    "priority_questions": [],
                    "labs_to_request": [],
                    "medications_to_review": [],
                    "outcomes": None,
                }
            ]

            with (
                patch.object(appointment_engine, "_HEALTH_DIR", health_dir),
                patch.object(appointment_engine, "_APPOINTMENTS_FILE", appointments_path),
                patch.object(appointment_engine, "_OUTCOMES_FILE", outcomes_path),
                patch.object(appointment_engine, "_HEALTH_STATE_FILE", health_state_path),
            ):
                appointment_engine._save_appointments_raw(appointments)
                appointments_path.write_text("", encoding="utf-8")

                replayed = appointment_engine._load_appointments_raw()

                self.assertEqual(replayed[0]["provider"], "Dr. Test")

    def test_replays_health_state_from_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            health_dir = Path(tmp)
            appointments_path = health_dir / "appointments.json"
            outcomes_path = health_dir / "appointment_outcomes.jsonl"
            health_state_path = health_dir / "chris_health_state.json"
            state = {
                "current_care_state": {
                    "medications": [{"name": "Metformin", "dose": "500 mg"}],
                },
                "open_questions": [],
            }

            with (
                patch.object(appointment_engine, "_HEALTH_DIR", health_dir),
                patch.object(appointment_engine, "_APPOINTMENTS_FILE", appointments_path),
                patch.object(appointment_engine, "_OUTCOMES_FILE", outcomes_path),
                patch.object(appointment_engine, "_HEALTH_STATE_FILE", health_state_path),
            ):
                appointment_engine._save_health_state(state)
                health_state_path.write_text("", encoding="utf-8")

                replayed = appointment_engine._load_health_state()

                self.assertEqual(replayed["current_care_state"]["medications"][0]["name"], "Metformin")

    def test_replays_appointment_outcomes_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            health_dir = Path(tmp)
            appointments_path = health_dir / "appointments.json"
            outcomes_path = health_dir / "appointment_outcomes.jsonl"
            health_state_path = health_dir / "chris_health_state.json"
            appointments = [
                {
                    "id": "apt-1",
                    "provider": "Dr. Test",
                    "specialty": "Primary Care",
                    "date": "2026-06-01",
                    "time": "09:00",
                    "location": "Clinic",
                    "reason": "Follow-up",
                    "prep_required": True,
                    "priority_questions": [],
                    "labs_to_request": [],
                    "medications_to_review": [],
                    "outcomes": None,
                }
            ]
            outcome = appointment_engine.AppointmentOutcome(
                appointment_id="apt-1",
                recorded_at="2026-06-01T15:00:00+00:00",
                decisions_made=[{"topic": "labs", "decision": "repeat A1c", "action_item": "order"}],
                medications_changed=[],
                labs_ordered=["A1c"],
                referrals_made=[],
                follow_up_date=None,
                notes="Stable overall.",
            )

            with (
                patch.object(appointment_engine, "_HEALTH_DIR", health_dir),
                patch.object(appointment_engine, "_APPOINTMENTS_FILE", appointments_path),
                patch.object(appointment_engine, "_OUTCOMES_FILE", outcomes_path),
                patch.object(appointment_engine, "_HEALTH_STATE_FILE", health_state_path),
            ):
                appointment_engine._save_appointments_raw(appointments)
                appointment_engine.record_appointment_outcome("apt-1", outcome)
                outcomes_path.write_text("", encoding="utf-8")

                history = appointment_engine.get_appointment_history()

                self.assertEqual(len(history), 1)
                self.assertEqual(history[0]["id"], "apt-1")
                self.assertEqual(history[0]["outcome_log"][0]["labs_ordered"], ["A1c"])


if __name__ == "__main__":
    unittest.main()
