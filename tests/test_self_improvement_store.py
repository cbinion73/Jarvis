from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from jarvis.self_improvement import SelfImprovementStore


class SelfImprovementStoreTests(unittest.TestCase):
    def test_settings_replay_from_state_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = SelfImprovementStore(Path(tmp))
            store.save_settings(
                {
                    "enabled": True,
                    "allow_safe_autonomy": False,
                    "allow_configured_model_sync": True,
                    "allow_heavy_model_downloads": False,
                    "allow_tool_installs": False,
                    "allow_code_changes": False,
                    "max_auto_actions_per_run": 2,
                }
            )

            store.settings_path.write_text("{}\n", encoding="utf-8")
            store.settings_log_path.write_text("", encoding="utf-8")

            replayed = store.settings()
            self.assertEqual(replayed["allow_safe_autonomy"], False)
            self.assertEqual(replayed["max_auto_actions_per_run"], 2)
            projection = json.loads(store.settings_path.read_text(encoding="utf-8"))
            self.assertEqual(projection, replayed)

    def test_jobs_replay_from_state_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = SelfImprovementStore(Path(tmp))
            store.upsert_job({"job_id": "job-a", "job_key": "alpha", "status": "queued"})
            store.upsert_job({"job_id": "job-b", "job_key": "beta", "status": "running"})

            store.jobs_path.write_text("[]\n", encoding="utf-8")
            store.jobs_log_path.write_text("", encoding="utf-8")

            replayed = store.jobs()
            self.assertEqual(
                replayed,
                [
                    {"job_id": "job-a", "job_key": "alpha", "status": "queued"},
                    {"job_id": "job-b", "job_key": "beta", "status": "running"},
                ],
            )
            self.assertEqual(store.get_job("job-b"), {"job_id": "job-b", "job_key": "beta", "status": "running"})
            projection = json.loads(store.jobs_path.read_text(encoding="utf-8"))
            self.assertEqual(projection, replayed)

    def test_runs_replay_from_state_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = SelfImprovementStore(Path(tmp))
            store.record_run({"run_id": "run-a", "status": "ok"})
            store.record_run({"run_id": "run-b", "status": "failed"})

            store.runs_path.write_text("[]\n", encoding="utf-8")
            store.runs_log_path.write_text("", encoding="utf-8")

            replayed = store.runs()
            self.assertEqual(
                replayed,
                [
                    {"run_id": "run-a", "status": "ok"},
                    {"run_id": "run-b", "status": "failed"},
                ],
            )
            self.assertEqual(store.get_run("run-b"), {"run_id": "run-b", "status": "failed"})
            projection = json.loads(store.runs_path.read_text(encoding="utf-8"))
            self.assertEqual(projection, replayed)

    def test_save_runs_records_replaced_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = SelfImprovementStore(Path(tmp))
            store.save_runs(
                [
                    {"run_id": "run-a", "status": "ok"},
                    {"run_id": "run-b", "status": "failed"},
                ]
            )

            log_rows = [
                json.loads(line)
                for line in store.runs_log_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            self.assertEqual(len(log_rows), 1)
            self.assertEqual(log_rows[0].get("event_type"), "replaced")
            self.assertEqual(log_rows[0].get("runs", [])[0].get("run_id"), "run-a")
            self.assertEqual(store.recent_runs(limit=1), [{"run_id": "run-b", "status": "failed"}])

    def test_active_runs_replay_from_state_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = SelfImprovementStore(Path(tmp))
            store.upsert_active_run("job-a", {"job_id": "job-a", "status": "running"})
            store.upsert_active_run("job-b", {"job_id": "job-b", "status": "queued"})
            store.clear_active_run("job-a")

            store.active_runs_path.write_text("{}\n", encoding="utf-8")
            store.active_runs_log_path.write_text("", encoding="utf-8")

            replayed = store.active_runs()
            self.assertEqual(
                replayed,
                {"job-b": {"job_id": "job-b", "status": "queued"}},
            )

            projection = json.loads(store.active_runs_path.read_text(encoding="utf-8"))
            self.assertEqual(projection, replayed)

    def test_save_active_runs_records_replaced_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = SelfImprovementStore(Path(tmp))
            store.save_active_runs(
                {
                    "job-a": {"job_id": "job-a", "status": "running"},
                    "job-b": {"job_id": "job-b", "status": "queued"},
                }
            )

            log_rows = [
                json.loads(line)
                for line in store.active_runs_log_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            self.assertEqual(len(log_rows), 1)
            self.assertEqual(log_rows[0].get("event_type"), "replaced")
            self.assertEqual(log_rows[0].get("active_runs", {}).get("job-a", {}).get("status"), "running")
            self.assertEqual(store.active_runs().get("job-b", {}).get("status"), "queued")


if __name__ == "__main__":
    unittest.main()
