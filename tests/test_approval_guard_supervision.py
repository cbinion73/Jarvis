from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import jarvis.approvals as approvals_module
from jarvis.approvals import (
    ActionExecutors,
    ApprovalGuard,
    ApprovalQueue,
    init_approvals,
    request_document_review,
)


class _StubSupervisionSupport:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def evaluate_action(
        self,
        *,
        agent_id: str,
        action_type: str,
        requested_outcome: str,
        trust_zone_id: str = "",
        lane_id: str = "",
        arena_id: str = "",
        context: dict | None = None,
    ) -> dict:
        payload = {
            "agent_id": agent_id,
            "action_type": action_type,
            "requested_outcome": requested_outcome,
            "trust_zone_id": trust_zone_id,
            "lane_id": lane_id,
            "arena_id": arena_id,
            "context": dict(context or {}),
        }
        self.calls.append(payload)
        if action_type == "home_control":
            return {
                "resolution": "forbidden",
                "sandbox_required": False,
                "approval_required": True,
                "escalation_required": True,
            }
        if action_type == "calendar_change":
            return {
                "resolution": "sandbox",
                "sandbox_required": True,
                "approval_required": False,
                "escalation_required": False,
            }
        return {
            "resolution": "stage",
            "sandbox_required": False,
            "approval_required": True,
            "escalation_required": False,
        }


class ApprovalGuardSupervisionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.original_root = ApprovalQueue.ROOT
        ApprovalQueue.ROOT = Path(self.tempdir.name) / "approvals"
        self.addCleanup(self._restore_root)
        self.original_guard = approvals_module._guard_singleton
        self.original_queue = approvals_module._queue_singleton
        approvals_module._guard_singleton = None
        approvals_module._queue_singleton = None
        self.addCleanup(self._restore_singletons)
        self.supervision = _StubSupervisionSupport()
        self.queue = ApprovalQueue()
        self.guard = ApprovalGuard(self.queue, supervision_support=self.supervision)
        self.original_dispatch = dict(ActionExecutors._DISPATCH)
        self.addCleanup(self._restore_dispatch)
        ActionExecutors._DISPATCH["other"] = staticmethod(lambda payload: {"status": "ok", "payload": payload})
        self.sandbox_calls: list[dict] = []

    def _restore_root(self) -> None:
        ApprovalQueue.ROOT = self.original_root

    def _restore_singletons(self) -> None:
        approvals_module._guard_singleton = self.original_guard
        approvals_module._queue_singleton = self.original_queue

    def _restore_dispatch(self) -> None:
        ActionExecutors._DISPATCH = self.original_dispatch

    def _sandbox_router(self, *, actor_name: str, job_id: str, triggered_by: str) -> dict:
        payload = {"actor_name": actor_name, "job_id": job_id, "triggered_by": triggered_by}
        self.sandbox_calls.append(payload)
        return {"ok": True, "accepted": True, "job": {"job_id": job_id, "status": "sandbox-queued"}}

    def test_request_approval_captures_supervision_metadata(self) -> None:
        request_id = self.guard.request_approval(
            agent_id="pepper",
            agent_label="Pepper",
            action_type="other",
            title="Test staged action",
            description="Stage something governed.",
            payload={"value": 1},
            context={
                "trust_zone_id": "household_schedule",
                "lane_id": "family-stewardship",
                "requested_outcome": "stage governed test action",
                "touches_external_state": True,
                "reversible": True,
            },
        )

        item = self.queue.get_by_id(request_id)
        self.assertIsNotNone(item)
        assert item is not None
        self.assertEqual(item.trust_zone_id, "household_schedule")
        self.assertEqual(item.lane_id, "family-stewardship")
        self.assertEqual(item.requested_outcome, "stage governed test action")
        self.assertEqual(item.supervision_decision["resolution"], "stage")

    def test_execute_approved_blocks_forbidden_actions(self) -> None:
        request_id = self.guard.request_approval(
            agent_id="apple-home",
            agent_label="Apple Home",
            action_type="home_control",
            title="Unlock door",
            description="Execute a home command",
            payload={"command": "unlock"},
            context={"trust_zone_id": "household_home", "touches_external_state": True, "reversible": False},
        )
        self.queue.approve(request_id, approved_by="chris")

        result = self.guard.execute_approved(request_id)

        self.assertEqual(result["status"], "error")
        self.assertIn("supervision policy", result["detail"])

    def test_execute_approved_blocks_unsandboxed_actions(self) -> None:
        request_id = self.guard.request_approval(
            agent_id="pepper",
            agent_label="Pepper",
            action_type="calendar_change",
            title="Reroute pickup",
            description="Adjust today's calendar",
            payload={"event_id": "evt-1"},
            context={"trust_zone_id": "household_schedule", "touches_external_state": True, "reversible": True},
        )
        self.queue.approve(request_id, approved_by="chris")

        result = self.guard.execute_approved(request_id)

        self.assertEqual(result["status"], "error")
        self.assertIn("sandbox routing", result["detail"])

    def test_execute_approved_routes_into_sandbox_when_router_and_job_id_are_present(self) -> None:
        guarded = ApprovalGuard(
            self.queue,
            supervision_support=self.supervision,
            sandbox_router=self._sandbox_router,
        )
        request_id = guarded.request_approval(
            agent_id="pepper",
            agent_label="Pepper",
            action_type="calendar_change",
            title="Reroute pickup",
            description="Adjust today's calendar",
            payload={"event_id": "evt-1", "_sandbox_job_id": "stewardship-review:rev-123"},
            context={"trust_zone_id": "household_schedule", "touches_external_state": True, "reversible": True},
        )
        self.queue.approve(request_id, approved_by="chris")

        result = guarded.execute_approved(request_id)

        self.assertEqual(result["status"], "sandbox_routed")
        self.assertEqual(result["sandbox_job_id"], "stewardship-review:rev-123")
        self.assertEqual(len(self.sandbox_calls), 1)
        self.assertEqual(self.sandbox_calls[0]["job_id"], "stewardship-review:rev-123")

    def test_request_document_review_uses_governed_submission_when_guard_is_initialized(self) -> None:
        queue, _guard = init_approvals(self.supervision)

        request_id = request_document_review(
            title="Chapter 4 Draft",
            preview="A preview of the current draft.",
            submission_id="sub-123",
            track_type="chapter",
            project_id="proj-1",
            chapter_number=4,
            ghostwritr_url="http://127.0.0.1:3000/books/test",
        )

        self.assertIsNotNone(request_id)
        item = queue.get_by_id(str(request_id))
        self.assertIsNotNone(item)
        assert item is not None
        self.assertEqual(item.trust_zone_id, "publication_review")
        self.assertEqual(item.lane_id, "wealth-opportunity")
        self.assertEqual(item.supervision_decision["resolution"], "stage")


if __name__ == "__main__":
    unittest.main()
