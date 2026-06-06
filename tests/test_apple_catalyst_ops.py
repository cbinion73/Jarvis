from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from jarvis.apple_api import (
    _approve_catalyst_approval,
    _build_catalyst_ops_overview,
    _execute_catalyst_recovery_case,
    _save_catalyst_progress_focus,
)
from jarvis.audit import AuditLog, ProgressFocusStore
from jarvis.recovery_cases import RecoveryCaseStore


class _StubApprovalStore:
    def __init__(self) -> None:
        self.records = [
            {
                "request_id": "approval-1",
                "status": "pending",
                "request": "Approve storm comms handoff",
                "agent": "Sam Wilson",
                "risk_tier": "high",
            }
        ]

    def update_status(self, request_id: str, status: str) -> dict | None:
        for item in self.records:
            if item["request_id"] == request_id:
                item["status"] = status
                return dict(item)
        return None


class _StubRuntime:
    def __init__(self, _root: Path) -> None:
        self.approval_store = _StubApprovalStore()

    def list_pending_approvals(self) -> list[dict]:
        return [
            {
                "request_id": "approval-1",
                "request": "Approve storm comms handoff",
                "agent": "Sam Wilson",
                "risk_tier": "high",
                "detail": "Queued from the overnight operator lane.",
            }
        ]


class CatalystOpsAppleAPITests(unittest.TestCase):
    def setUp(self) -> None:
        self._cwd = Path.cwd()
        self._tmpdir = tempfile.TemporaryDirectory()
        os.chdir(self._tmpdir.name)

    def tearDown(self) -> None:
        os.chdir(self._cwd)
        self._tmpdir.cleanup()

    def test_build_overview_returns_focus_approval_and_recovery_state(self) -> None:
        root = Path("data/logs")
        ProgressFocusStore(root).save_focus(
            module="Recovery",
            reason="Catalyst elevated recovery after a phone-side drift alert.",
            route="/recovery-center",
            actor="chris",
        )
        case = RecoveryCaseStore(root).upsert_case(
            source_kind="integration",
            title="Weather relay drift",
            detail="Apple weather relay needs attention.",
            related_route="/recovery-center",
            related_key="weather-relay",
        )
        RecoveryCaseStore(root).record_execution(
            case["case_id"],
            actor="chris",
            action_type="retry",
            note="Retry the weather relay before commute mode.",
        )
        AuditLog(root).log_event(
            "operator-action",
            {
                "actor": "chris",
                "action": "Set Catalyst Focus",
                "detail": "Catalyst moved the shared progress focus to Recovery.",
                "route_label": "Open Recovery",
            },
        )

        overview = _build_catalyst_ops_overview(_StubRuntime(Path("data")))

        self.assertEqual(overview["current_focus"]["module"], "Recovery")
        self.assertEqual(overview["counts"]["approval_count"], 1)
        self.assertEqual(overview["recovery_cases"][0]["next_action_type"], "retry")
        self.assertEqual(overview["approvals"][0]["title"], "Approve storm comms handoff")

    def test_focus_approval_and_recovery_actions_persist_continuity(self) -> None:
        runtime = _StubRuntime(Path("data"))
        case = RecoveryCaseStore(Path("data/logs")).upsert_case(
            source_kind="failure",
            title="Planner drift",
            detail="Planner route hydration slipped.",
            related_route="/recovery-center",
            related_key="planner-drift",
        )

        focus = _save_catalyst_progress_focus(
            module="Progress",
            route="/progress-center",
            actor="chris",
            reason="Catalyst is tightening the next Level 3 closure target.",
        )
        self.assertEqual(focus["module"], "Progress")

        approval = _approve_catalyst_approval(runtime, request_id="approval-1", actor="chris")
        self.assertEqual(approval["status"], "approved")

        recovery = _execute_catalyst_recovery_case(
            case_id=case["case_id"],
            actor="chris",
            action_type="retry",
            note="Catalyst ran the retry loop from the native ops studio.",
        )
        self.assertEqual(recovery["status"], "recorded")

        focus_summary = ProgressFocusStore(Path("data/logs")).summary(limit=8)
        self.assertEqual(focus_summary["latest"]["module"], "Recovery")

        recent = AuditLog(Path("data/logs")).list_recent(limit=6, entry_type="operator-action")
        titles = [item.get("action") for item in recent]
        self.assertIn("Set Catalyst Focus", titles)
        self.assertIn("Approve Catalyst Approval", titles)
        self.assertIn("Execute Catalyst Recovery Loop", titles)


if __name__ == "__main__":
    unittest.main()
