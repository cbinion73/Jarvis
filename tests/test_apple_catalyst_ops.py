from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jarvis.apple_api import (
    _approve_catalyst_approval,
    _build_catalyst_ops_overview,
    _execute_catalyst_recovery_case,
    _queue_catalyst_agent_run,
    _resolve_catalyst_supervision_item,
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

    def mission_control_snapshot(self, actor_name: str = "Chris") -> dict:
        return {
            "summary": {},
            "active_missions": [],
            "pending_approvals": [],
        }


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
        self.assertEqual(overview["counts"]["mission_count"], 0)
        self.assertEqual(overview["recovery_cases"][0]["next_action_type"], "retry")
        self.assertEqual(overview["approvals"][0]["title"], "Approve storm comms handoff")
        self.assertEqual(overview["recent_activity"][0]["related_route"], "/command-center")
        self.assertIn("agent_ops", overview)
        self.assertIn("supervision_items", overview)

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

    def test_update_catalyst_mission_status_records_shared_focus(self) -> None:
        class _MissionRuntime(_StubRuntime):
            def update_mission_status(self, mission_id: str, status: str, *, note: str = "") -> dict:
                return {
                    "mission_id": mission_id,
                    "title": "Morning route recovery",
                    "status": status,
                    "request": "Stabilize the commute surfaces",
                }

            def mission_control_snapshot(self, actor_name: str = "Chris") -> dict:
                return {
                    "summary": {},
                    "active_missions": [
                        {
                            "mission_id": "mission-1",
                            "title": "Morning route recovery",
                            "brief": "Stabilize the commute surfaces before departure.",
                            "status": "queued",
                            "lane": "next",
                            "next_step": "Retry route hydration.",
                        }
                    ],
                    "pending_approvals": [],
                }

        from jarvis.apple_api import _update_catalyst_mission_status

        result = _update_catalyst_mission_status(
            _MissionRuntime(Path("data")),
            mission_id="mission-1",
            status="active",
            actor="chris",
            note="Catalyst moved the mission into the now lane.",
        )

        self.assertEqual(result["status"], "recorded")
        summary = ProgressFocusStore(Path("data/logs")).summary(limit=4)
        self.assertEqual(summary["latest"]["module"], "Mission Board")
        recent = AuditLog(Path("data/logs")).list_recent(limit=3, entry_type="operator-action")
        self.assertEqual(recent[0]["action"], "Move Catalyst Mission to Now")

    def test_queue_agent_run_and_supervision_action_record_shared_focus(self) -> None:
        runtime = _StubRuntime(Path("data"))

        class _QueuedItem:
            item_id = "queued-1"

        class _StubScheduler:
            def force_run(self, agent_id: str) -> _QueuedItem | None:
                if agent_id == "sam-wilson":
                    return _QueuedItem()
                return None

        supervision_snapshot = {
            "attention_queue": [
                {
                    "request_id": "approval-1",
                    "title": "Approve storm comms handoff",
                    "agent_label": "Sam Wilson",
                    "risk_tier": "high",
                    "why_now": "The handoff needs a bounded review before the route opens.",
                    "action_type": "handoff",
                }
            ]
        }

        with patch("jarvis.scheduler.get_scheduler", return_value=_StubScheduler()):
            queued = _queue_catalyst_agent_run(agent_id="sam-wilson", actor="chris")
        self.assertEqual(queued["status"], "queued")
        self.assertEqual(queued["agent_id"], "sam-wilson")

        with patch("jarvis.supervision_snapshot.build_supervision_snapshot", return_value=supervision_snapshot):
            result = _resolve_catalyst_supervision_item(
                runtime,
                request_id="approval-1",
                action="reject",
                actor="chris",
                reason="Catalyst wants a safer plan before this handoff executes.",
            )

        self.assertEqual(result["status"], "rejected")
        summary = ProgressFocusStore(Path("data/logs")).summary(limit=5)
        self.assertEqual(summary["latest"]["module"], "Supervision")
        recent = AuditLog(Path("data/logs")).list_recent(limit=4, entry_type="operator-action")
        titles = [item.get("action") for item in recent]
        self.assertIn("Queue Catalyst Agent Run", titles)
        self.assertIn("Reject Catalyst Supervision Review", titles)


if __name__ == "__main__":
    unittest.main()
