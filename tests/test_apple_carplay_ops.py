from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from jarvis.apple_api import _build_carplay_ops_overview, _save_carplay_ops_focus
from jarvis.audit import AuditLog, ProgressFocusStore
from jarvis.recovery_cases import RecoveryCaseStore


class _StubRuntime:
    def list_pending_approvals(self) -> list[dict]:
        return [
            {
                "request_id": "approval-1",
                "request": "Approve the overnight family systems sync",
                "agent": "Sam Wilson",
                "risk_tier": "high",
                "action_class": "approval",
            }
        ]

    def mission_control_snapshot(self, actor_name: str = "Chris") -> dict:
        return {
            "summary": {
                "headline": "Recovery and approvals need a deliberate handoff before sunrise.",
            },
            "active_missions": [
                {"mission_id": "mission-1", "title": "Recovery continuity"},
                {"mission_id": "mission-2", "title": "Morning launch prep"},
            ],
            "pending_approvals": [{"request_id": "approval-1"}],
        }

    def background_agent_status(self, recent_activity: list[dict] | None = None) -> dict:
        return {
            "statuses": [
                {"agent": "Sam Wilson", "status": "awake"},
                {"agent": "Helen Cho", "status": "awake"},
                {"agent": "Recovery Sentinel", "status": "blocked"},
            ]
        }


class CarPlayOpsAppleAPITests(unittest.TestCase):
    def setUp(self) -> None:
        self._cwd = Path.cwd()
        self._tmpdir = tempfile.TemporaryDirectory()
        os.chdir(self._tmpdir.name)

    def tearDown(self) -> None:
        os.chdir(self._cwd)
        self._tmpdir.cleanup()

    def test_build_carplay_ops_overview_returns_live_counts(self) -> None:
        root = Path("data/logs")
        ProgressFocusStore(root).save_focus(
            module="Health",
            reason="Health objective was saved from the command surface.",
            route="/health-center",
            actor="chris",
        )
        case = RecoveryCaseStore(root).upsert_case(
            source_kind="integration",
            title="Weather relay drift",
            detail="Apple weather relay needs investigation.",
            related_route="/recovery-center",
            related_key="weather-relay",
        )
        RecoveryCaseStore(root).record_execution(
            case["case_id"],
            actor="chris",
            action_type="retry",
            note="Retrying the weather relay from the recovery loop.",
        )
        AuditLog(root).log_event(
            "operator-action",
            {
                "actor": "chris",
                "action": "Queue Agent Run",
                "detail": "Sam Wilson picked up the route intelligence handoff.",
                "route_label": "Open Agent Ops",
            },
        )

        overview = _build_carplay_ops_overview(_StubRuntime())

        self.assertEqual(overview["current_focus"]["module"], "Health")
        self.assertEqual(overview["counts"]["approval_count"], 1)
        self.assertEqual(overview["counts"]["recovery_case_count"], 1)
        self.assertEqual(overview["agent_summary"]["awake_count"], 2)
        self.assertEqual(overview["mission_summary"]["active_count"], 2)
        self.assertEqual(overview["recovery_cases"][0]["status_label"], "Investigating")
        self.assertEqual(overview["recent_activity"][0]["title"], "Queue Agent Run")

    def test_save_carplay_ops_focus_persists_progress_and_activity(self) -> None:
        entry = _save_carplay_ops_focus(
            module="Recovery",
            route="/recovery-center",
            actor="chris",
            reason="CarPlay elevated Recovery after a route-side failure signal.",
        )

        self.assertEqual(entry["module"], "Recovery")
        summary = ProgressFocusStore(Path("data/logs")).summary(limit=3)
        self.assertEqual(summary["latest"]["module"], "Recovery")

        recent = AuditLog(Path("data/logs")).list_recent(limit=3, entry_type="operator-action")
        self.assertEqual(recent[0]["action"], "Set CarPlay Ops Focus")
        self.assertEqual(recent[0]["related_label"], "Recovery")


if __name__ == "__main__":
    unittest.main()
