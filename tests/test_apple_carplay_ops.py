from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jarvis.apple_api import (
    _build_carplay_ops_overview,
    _queue_carplay_agent_run,
    _resolve_carplay_supervision_item,
    _save_carplay_ops_focus,
)
from jarvis.audit import AuditLog, ProgressFocusStore
from jarvis.recovery_cases import RecoveryCaseStore


class _StubApprovalStore:
    def __init__(self) -> None:
        self.records = [
            {
                "request_id": "approval-1",
                "status": "pending",
                "request": "Approve the overnight family systems sync",
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
    def __init__(self) -> None:
        self.approval_store = _StubApprovalStore()

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
        self.assertIn("agent_ops", overview)
        self.assertIn("supervision_items", overview)

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

    def test_carplay_agent_and_supervision_actions_persist_continuity(self) -> None:
        runtime = _StubRuntime()

        class _QueuedItem:
            item_id = "carplay-queued-1"

        class _StubScheduler:
            def force_run(self, agent_id: str) -> _QueuedItem | None:
                if agent_id == "sam-wilson":
                    return _QueuedItem()
                return None

        supervision_snapshot = {
            "attention_queue": [
                {
                    "request_id": "approval-1",
                    "title": "Approve the overnight family systems sync",
                    "agent_label": "Sam Wilson",
                    "risk_tier": "high",
                    "why_now": "The route-side family systems sync needs bounded review before sunrise.",
                }
            ]
        }

        with patch("jarvis.scheduler.get_scheduler", return_value=_StubScheduler()):
            queued = _queue_carplay_agent_run(agent_id="sam-wilson", actor="chris")
        self.assertEqual(queued["status"], "queued")

        with patch("jarvis.supervision_snapshot.build_supervision_snapshot", return_value=supervision_snapshot):
            result = _resolve_carplay_supervision_item(
                runtime,
                request_id="approval-1",
                action="approve",
                actor="chris",
                reason="CarPlay approved the review from the in-car supervision lane.",
            )

        self.assertEqual(result["status"], "approved")
        summary = ProgressFocusStore(Path("data/logs")).summary(limit=5)
        self.assertEqual(summary["latest"]["module"], "Supervision")
        recent = AuditLog(Path("data/logs")).list_recent(limit=4, entry_type="operator-action")
        titles = [item.get("action") for item in recent]
        self.assertIn("Queue CarPlay Agent Run", titles)
        self.assertIn("Approve CarPlay Supervision Review", titles)


if __name__ == "__main__":
    unittest.main()
