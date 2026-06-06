from __future__ import annotations

import os
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch

from jarvis.apple_api import (
    _build_carplay_ops_overview,
    _pass_carplay_huddle_idea,
    _queue_carplay_agent_run,
    _queue_carplay_huddle_idea,
    _research_carplay_huddle_idea_now,
    _resolve_carplay_supervision_item,
    _save_carplay_ops_focus,
    _start_carplay_huddle_party_mode,
)
from jarvis.audit import AuditLog, ProgressFocusStore
from jarvis.chronicle_reviews import ChronicleReviewStore
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
        ChronicleReviewStore().review_entry(
            entry_id="chronicle-1",
            actor_id="chris",
            title="Remember the calm after the hard conversation",
            entry_type="reflection",
            status="study",
            note="Use this in tomorrow's study lane.",
        )

        @dataclass
        class _StubHuddle:
            agent_reports: list[dict]
            blockers: list[str]
            approvals_needed: list[dict]

        class _StubPartyController:
            def get_status(self) -> dict:
                return {"status": "idle"}

        class _StubDossier:
            status = "ready"

        class _StubDossierStore:
            def get_all(self) -> list:
                return [_StubDossier(), _StubDossier()]

        with (
            patch(
                "jarvis.standup.collect_all_standups",
                return_value=_StubHuddle(
                    agent_reports=[{"agent_id": "sam-wilson"}],
                    blockers=["Need a tighter family launch decision lane."],
                    approvals_needed=[{"work_id": "approval-1"}],
                ),
            ),
            patch("jarvis.party_mode.get_party_controller", return_value=_StubPartyController()),
            patch("jarvis.dossier.get_dossier_store", return_value=_StubDossierStore()),
            patch(
                "jarvis.ideas.list_ideas",
                return_value=[
                    {
                        "id": "idea-1",
                        "text": "Research a calmer school launch cadence",
                        "status": "captured",
                        "domain": "family",
                        "created_at": "2026-06-06T08:00:00Z",
                    }
                ],
            ),
            patch(
                "jarvis.ideas.stats",
                return_value={"total": 1, "by_status": {"captured": 1, "queued": 0}},
            ),
        ):
            overview = _build_carplay_ops_overview(_StubRuntime())

        self.assertEqual(overview["current_focus"]["module"], "Health")
        self.assertEqual(overview["counts"]["approval_count"], 1)
        self.assertEqual(overview["counts"]["recovery_case_count"], 1)
        self.assertEqual(overview["agent_summary"]["awake_count"], 2)
        self.assertEqual(overview["mission_summary"]["active_count"], 2)
        self.assertEqual(overview["recovery_cases"][0]["status_label"], "Investigating")
        self.assertEqual(overview["recent_activity"][0]["title"], "Queue Agent Run")
        self.assertEqual(overview["huddle_summary"]["queued_idea_count"], 1)
        self.assertEqual(overview["huddle_ideas"][0]["domain"], "family")
        self.assertEqual(overview["chronicle_summary"]["review_count"], 1)
        self.assertEqual(overview["chronicle_reviews"][0]["review_status_label"], "Study Next")
        self.assertIn("agent_ops", overview)
        self.assertIn("supervision_items", overview)
        self.assertIn("huddle_summary", overview)
        self.assertIn("huddle_ideas", overview)
        self.assertIn("chronicle_reviews", overview)

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

    def test_carplay_huddle_actions_persist_continuity(self) -> None:
        from jarvis.ideas import add_idea
        from unittest.mock import patch

        idea = add_idea(
            "Research a tighter morning route handoff",
            "user",
            "Captured for in-car Huddle triage.",
            "operations",
            [],
        )
        queued = _queue_carplay_huddle_idea(idea_id=idea["id"], actor="chris")
        self.assertEqual(queued["status"], "queued")

        passed = _pass_carplay_huddle_idea(idea_id=idea["id"], actor="chris")
        self.assertEqual(passed["status"], "passed")

        research_idea = add_idea(
            "Research family launch ops in the car lane",
            "user",
            "Ready for immediate research.",
            "family",
            [],
        )

        class _StubWorkItem:
            work_id = "carplay-huddle-work-1"

        class _StubWorkStore:
            def dream_idea(self, *args, **kwargs):
                return _StubWorkItem()

        with (
            patch("jarvis.llm_gateway.get_gateway", return_value=object()),
            patch("jarvis.agent_work.get_work_store", return_value=_StubWorkStore()),
        ):
            researched = _research_carplay_huddle_idea_now(idea_id=research_idea["id"], actor="chris")

        self.assertTrue(researched["queued"])
        self.assertEqual(researched["work_id"], "carplay-huddle-work-1")

        started = _start_carplay_huddle_party_mode(_StubRuntime(), actor="chris")
        self.assertIn(started["status"], {"started", "already_running"})

        summary = ProgressFocusStore(Path("data/logs")).summary(limit=8)
        self.assertEqual(summary["latest"]["module"], "Huddle")
        recent = AuditLog(Path("data/logs")).list_recent(limit=8, entry_type="operator-action")
        titles = [item.get("action") for item in recent]
        self.assertIn("Queue CarPlay Huddle Idea", titles)
        self.assertIn("Pass CarPlay Huddle Idea", titles)
        self.assertIn("Research CarPlay Huddle Idea Now", titles)
        self.assertIn("Start CarPlay Huddle Party Mode", titles)


if __name__ == "__main__":
    unittest.main()
