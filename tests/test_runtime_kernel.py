from __future__ import annotations

import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from jarvis.agentic import AgentRegistry
from jarvis.runtime_kernel import (
    AgentRuntimeKernel,
    AgentRuntimeKernelStore,
    LIFECYCLE_BLOCKED,
    LIFECYCLE_ESCALATING,
    LIFECYCLE_IDLE,
    LIFECYCLE_INTERRUPTED,
    LIFECYCLE_PAUSED,
    LIFECYCLE_RETIRED,
    LIFECYCLE_RETIRING,
    LIFECYCLE_RUNNING,
)


class AgentRuntimeKernelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.registry = AgentRegistry()
        self.kernel = AgentRuntimeKernel(
            AgentRuntimeKernelStore(Path(self.tempdir.name)),
            self.registry,
            heartbeat_stale_after_seconds=60,
            heartbeat_missed_after_seconds=180,
        )

    def test_bootstrap_snapshot_creates_runtime_entries(self) -> None:
        snapshot = self.kernel.snapshot(
            active_mode="family-morning",
            integration_status=[],
            recent_activity=[],
            quiet_hours=("22:00", "06:00"),
            observed_at=datetime(2026, 6, 1, 12, 0, tzinfo=UTC),
        )

        self.assertEqual(snapshot["summary"]["total_agents"], len(self.registry.list()))
        ambient = snapshot["agents"]["ambient-router"]
        self.assertEqual(ambient["lifecycle"]["current_state"], LIFECYCLE_RUNNING)
        self.assertTrue(ambient["run"]["run_id"])

    def test_pause_resume_interrupt_escalate_and_retire_controls_are_durable(self) -> None:
        now = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
        agent_id = "workshop-watch"

        paused = self.kernel.apply_control(agent_id, "pause", actor="Chris", reason="Hold work", recorded_at=now)
        self.assertEqual(paused["agent"]["lifecycle"]["current_state"], LIFECYCLE_PAUSED)

        resumed = self.kernel.apply_control(agent_id, "resume", actor="Chris", reason="Resume work", recorded_at=now + timedelta(minutes=1))
        self.assertEqual(resumed["agent"]["lifecycle"]["current_state"], LIFECYCLE_RUNNING)

        interrupted = self.kernel.apply_control(agent_id, "interrupt", actor="Chris", reason="Need review", recorded_at=now + timedelta(minutes=2))
        self.assertEqual(interrupted["agent"]["lifecycle"]["current_state"], LIFECYCLE_INTERRUPTED)

        escalated = self.kernel.apply_control(agent_id, "escalate", actor="Chris", reason="Escalate to supervisor", recorded_at=now + timedelta(minutes=3))
        self.assertEqual(escalated["agent"]["lifecycle"]["current_state"], LIFECYCLE_ESCALATING)

        retiring = self.kernel.apply_control(agent_id, "retire", actor="Chris", reason="Retire gracefully", recorded_at=now + timedelta(minutes=4))
        self.assertEqual(retiring["agent"]["lifecycle"]["current_state"], LIFECYCLE_RETIRING)

        retired = self.kernel.apply_control(agent_id, "retire-now", actor="Chris", reason="Retire now", recorded_at=now + timedelta(minutes=5))
        self.assertEqual(retired["agent"]["lifecycle"]["current_state"], LIFECYCLE_RETIRED)

    def test_heartbeat_transitions_from_fresh_to_stale_to_missed(self) -> None:
        now = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
        self.kernel.apply_control("system-steward", "wake", actor="Chris", reason="Begin maintenance", recorded_at=now)
        self.kernel.record_heartbeat("system-steward", actor="system", note="healthy", observed_at=now)

        fresh = self.kernel.snapshot(observed_at=now + timedelta(seconds=30))
        stale = self.kernel.snapshot(observed_at=now + timedelta(seconds=90))
        missed = self.kernel.snapshot(observed_at=now + timedelta(seconds=240))

        system_row_fresh = next(row for row in fresh["status_rows"] if row["agent_id"] == "system-steward")
        system_row_stale = next(row for row in stale["status_rows"] if row["agent_id"] == "system-steward")
        system_row_missed = next(row for row in missed["status_rows"] if row["agent_id"] == "system-steward")
        self.assertEqual(system_row_fresh["heartbeat_status"], "fresh")
        self.assertEqual(system_row_stale["heartbeat_status"], "stale")
        self.assertEqual(system_row_missed["heartbeat_status"], "missed")

    def test_dependency_blocking_surfaces_in_status_rows(self) -> None:
        snapshot = self.kernel.snapshot(
            active_mode="family-morning",
            integration_status=[
                {"name": "OpenAI API", "ok": True},
                {"name": "Home Assistant", "ok": False},
                {"name": "Perception Mesh", "ok": False},
            ],
            recent_activity=[],
            observed_at=datetime(2026, 6, 1, 12, 0, tzinfo=UTC),
        )
        home_ops = next(row for row in snapshot["status_rows"] if row["agent_id"] == "home-ops")
        watchtower = next(row for row in snapshot["status_rows"] if row["agent_id"] == "watchtower")

        self.assertEqual(home_ops["state"], LIFECYCLE_BLOCKED)
        self.assertIn("home_assistant", home_ops["blocked_dependencies"])
        self.assertEqual(watchtower["state"], LIFECYCLE_BLOCKED)
        self.assertIn("perception", watchtower["blocked_dependencies"])

    def test_legacy_background_state_migration_preserves_last_run(self) -> None:
        legacy_last_run = "2026-05-31T13:11:05+00:00"
        self.kernel.migrate_legacy_background_state(
            {
                "agents": {
                    "ambient-router": {
                        "state": "awake",
                        "last_run_at": legacy_last_run,
                        "next_run_at": "2026-05-31T13:12:05+00:00",
                    }
                }
            }
        )

        snapshot = self.kernel.snapshot(observed_at=datetime(2026, 6, 1, 12, 0, tzinfo=UTC))
        ambient = snapshot["agents"]["ambient-router"]
        self.assertEqual(ambient["run"]["last_started_at"], legacy_last_run)
        self.assertEqual(ambient["lifecycle"]["current_state"], LIFECYCLE_RUNNING)


if __name__ == "__main__":
    unittest.main()
