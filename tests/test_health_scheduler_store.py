from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jarvis import health_scheduler


class HealthSchedulerStoreTests(unittest.TestCase):
    def test_replays_schedule_config_and_appointments_from_logs_when_snapshots_are_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            health_dir = Path(tmp)
            config_path = health_dir / "schedule_config.json"
            appointments_path = health_dir / "appointments.json"

            with (
                patch.object(health_scheduler, "_HEALTH_DIR", health_dir),
                patch.object(health_scheduler, "_SCHEDULE_CONFIG_PATH", config_path),
                patch.object(health_scheduler, "_APPOINTMENTS_PATH", appointments_path),
            ):
                cfg = health_scheduler._load_schedule_config()
                appts = health_scheduler._load_appointments()

                self.assertTrue(cfg["morning_brief"]["enabled"])
                self.assertEqual(len(appts), 1)

                config_path.write_text("", encoding="utf-8")
                appointments_path.write_text("", encoding="utf-8")

                replayed_cfg = health_scheduler._load_schedule_config()
                replayed_appts = health_scheduler._load_appointments()

                self.assertTrue(replayed_cfg["drift_check"]["enabled"])
                self.assertEqual(replayed_appts[0]["provider"], "Dr. Susan Wenk")

    def test_replays_morning_brief_and_schedule_status_from_logs_when_snapshots_are_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            health_dir = Path(tmp)
            brief_path = health_dir / "morning_brief.json"
            status_path = health_dir / "schedule_status.json"
            config_path = health_dir / "schedule_config.json"
            appointments_path = health_dir / "appointments.json"
            brief = {
                "date": "2026-06-02",
                "generated_at": "2026-06-02T06:00:00",
                "oracle_pathway": "O-CLEAR",
                "oracle_flags": [],
                "day_type": "Push",
                "readiness_score": 90,
                "three_moves": ["Lift heavy"],
                "drift_alerts": [],
                "active_drift_clusters": [],
                "upcoming_appointments": [],
                "pre_appointment_alert": None,
                "push_sent": False,
                "headline": "All systems stable — Push day with readiness score 90. Execute your Three Moves.",
            }
            status = {
                "last_runs": {
                    "morning_brief": "2026-06-02T06:05:00",
                },
                "updated_at": "2026-06-02T06:05:00",
            }

            with (
                patch.object(health_scheduler, "_HEALTH_DIR", health_dir),
                patch.object(health_scheduler, "_MORNING_BRIEF_PATH", brief_path),
                patch.object(health_scheduler, "_SCHEDULE_STATUS_PATH", status_path),
                patch.object(health_scheduler, "_SCHEDULE_CONFIG_PATH", config_path),
                patch.object(health_scheduler, "_APPOINTMENTS_PATH", appointments_path),
                patch.object(health_scheduler, "_now_iso", return_value="2026-06-02T06:05:00"),
                patch("jarvis.health_scheduler.datetime", new=_FrozenDateTime),
            ):
                health_scheduler._save_json(config_path, health_scheduler._DEFAULT_SCHEDULE_CONFIG)
                health_scheduler._save_json(brief_path, brief)
                health_scheduler._save_json(status_path, status)

                brief_path.write_text("", encoding="utf-8")
                status_path.write_text("", encoding="utf-8")

                replayed_brief = health_scheduler.get_morning_brief()
                replayed_status = health_scheduler.get_schedule_status()

                self.assertEqual(replayed_brief["headline"], "All systems stable — Push day with readiness score 90. Execute your Three Moves.")
                self.assertEqual(replayed_status["last_runs"]["morning_brief"], "2026-06-02T06:05:00")

    def test_replays_predictions_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            health_dir = Path(tmp)
            predictions_path = health_dir / "twin_predictions.jsonl"
            predictions_state_log_path = health_dir / "twin_predictions_state_log.jsonl"
            status_path = health_dir / "schedule_status.json"
            config_path = health_dir / "schedule_config.json"
            appointments_path = health_dir / "appointments.json"
            health_state_path = health_dir / "chris_health_state.json"
            prediction = {
                "prediction_id": "pred-1",
                "metric": "resting_heart_rate",
                "predicted_value": 58,
                "check_date": "2026-06-02",
                "actual_value": None,
            }

            with (
                patch.object(health_scheduler, "_HEALTH_DIR", health_dir),
                patch.object(health_scheduler, "_PREDICTIONS_PATH", predictions_path),
                patch.object(health_scheduler, "_PREDICTIONS_STATE_LOG_PATH", predictions_state_log_path),
                patch.object(health_scheduler, "_SCHEDULE_STATUS_PATH", status_path),
                patch.object(health_scheduler, "_SCHEDULE_CONFIG_PATH", config_path),
                patch.object(health_scheduler, "_APPOINTMENTS_PATH", appointments_path),
                patch.object(health_scheduler, "_HEALTH_STATE_PATH", health_state_path),
                patch.object(health_scheduler, "_today_str", return_value="2026-06-02"),
                patch.object(health_scheduler, "_now_iso", return_value="2026-06-02T08:00:00"),
            ):
                health_scheduler._save_json(config_path, health_scheduler._DEFAULT_SCHEDULE_CONFIG)
                health_scheduler._save_json(health_state_path, {"vitals": {"resting_heart_rate": 60}})
                health_scheduler._save_prediction_records([prediction])
                predictions_path.write_text("", encoding="utf-8")

                result = asyncio.run(health_scheduler.run_prediction_scorer())
                replayed = health_scheduler._load_prediction_records()

                self.assertEqual(result["newly_scored"], 1)
                self.assertEqual(replayed[0]["actual_value"], 60)
                self.assertEqual(replayed[0]["scored_at"], "2026-06-02T08:00:00")


class _FrozenDateTime:
    @staticmethod
    def now(tz=None):
        from datetime import datetime, timezone

        current = datetime(2026, 6, 2, 6, 0, 0, tzinfo=timezone.utc if tz else None)
        if tz is not None:
            return current.astimezone(tz)
        return current.replace(tzinfo=None)

    @staticmethod
    def fromisoformat(value: str):
        from datetime import datetime

        return datetime.fromisoformat(value)


if __name__ == "__main__":
    unittest.main()
