from __future__ import annotations

import json
import importlib
import sys
import tempfile
import types
import unittest
from pathlib import Path

import jarvis.approvals as approvals_module
from jarvis.approvals import ApprovalQueue, init_approvals

if "fastapi" not in sys.modules:
    fastapi_stub = types.ModuleType("fastapi")

    class _FastAPI:  # pragma: no cover - test stub only
        pass

    class _HTTPException(Exception):  # pragma: no cover - test stub only
        pass

    fastapi_stub.FastAPI = _FastAPI
    fastapi_stub.HTTPException = _HTTPException
    sys.modules["fastapi"] = fastapi_stub

apple_api = importlib.import_module("jarvis.apple_api")

from jarvis.apple_api import (
    _StewardshipReviewStore,
    _stage_calendar_route_governed_approval,
    _serialize_stewardship_review,
    _stage_stewardship_review_governed_approval,
)


class _StubSupervisionSupport:
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
        return {
            "resolution": "stage",
            "sandbox_required": False,
            "approval_required": True,
            "escalation_required": False,
            "agent_id": agent_id,
            "action_type": action_type,
            "trust_zone_id": trust_zone_id,
            "lane_id": lane_id,
            "requested_outcome": requested_outcome,
        }


class StewardshipReviewGovernanceTests(unittest.TestCase):
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

    def _restore_root(self) -> None:
        ApprovalQueue.ROOT = self.original_root

    def _restore_singletons(self) -> None:
        approvals_module._guard_singleton = self.original_guard
        approvals_module._queue_singleton = self.original_queue

    def test_stage_stewardship_review_creates_governed_approval_record(self) -> None:
        queue, _guard = init_approvals(_StubSupervisionSupport())

        request_id, decision = _stage_stewardship_review_governed_approval(
            lane={
                "name": "Family Stewardship",
                "primary_agents": ["pepper"],
            },
            review={
                "id": "stewardship-review::family-stewardship::abc123",
                "lane_id": "family-stewardship",
                "lane_title": "Family Stewardship",
                "review_surface": "brief",
                "packet_target": "family",
                "trust_zone": "household_schedule",
            },
            actor="chris",
            detail="Family stewardship is ready for deliberate review.",
        )

        self.assertTrue(request_id)
        self.assertEqual(decision["resolution"], "stage")
        item = queue.get_by_id(request_id)
        self.assertIsNotNone(item)
        assert item is not None
        self.assertEqual(item.agent_id, "pepper")
        self.assertEqual(item.trust_zone_id, "household_schedule")
        self.assertEqual(item.lane_id, "family-stewardship")
        self.assertEqual(
            item.payload.get("_sandbox_job_id"),
            "stewardship-review:stewardship-review::family-stewardship::abc123",
        )

    def test_stewardship_review_store_persists_governance_fields(self) -> None:
        store = _StewardshipReviewStore(Path(self.tempdir.name) / "stewardship_reviews.json")

        saved = store.upsert(
            lane_id="family-stewardship",
            lane_title="Family Stewardship",
            review_surface="brief",
            packet_target="family",
            boundary_decision="stage",
            boundary_reason="Deliberate review required before wider execution.",
            trust_zone="household_schedule",
            authority_stage="sandbox_live",
            arena_status="active",
            approval_mode="stage_and_alert",
            actor="chris",
            approval_request_id="approval-123",
            supervision_decision={"resolution": "stage", "approval_required": True},
        )

        hydrated = _serialize_stewardship_review(saved)
        self.assertEqual(hydrated["approval_request_id"], "approval-123")
        self.assertEqual(hydrated["supervision_decision"]["resolution"], "stage")

    def test_stewardship_review_store_replays_from_append_log_when_snapshot_is_blank(self) -> None:
        store_path = Path(self.tempdir.name) / "stewardship_reviews.json"
        store = _StewardshipReviewStore(store_path)

        saved = store.upsert(
            lane_id="family-stewardship",
            lane_title="Family Stewardship",
            review_surface="brief",
            packet_target="family",
            boundary_decision="stage",
            boundary_reason="Deliberate review required before wider execution.",
            trust_zone="household_schedule",
            authority_stage="sandbox_live",
            arena_status="active",
            approval_mode="stage_and_alert",
            actor="chris",
            approval_request_id="approval-123",
            supervision_decision={"resolution": "stage", "approval_required": True},
        )

        store_path.write_text("", encoding="utf-8")

        replayed = store.get(str(saved["id"]))

        self.assertIsNotNone(replayed)
        assert replayed is not None
        self.assertEqual(replayed["approval_request_id"], "approval-123")
        self.assertEqual(replayed["lane_id"], "family-stewardship")

    def test_stage_calendar_route_creates_governed_sandbox_approval(self) -> None:
        queue, _guard = init_approvals(_StubSupervisionSupport())

        request_id, decision = _stage_calendar_route_governed_approval(
            actor="chris",
            event_id="evt-42",
            title="Soccer Pickup",
            location="123 Main St, Franklin, TN",
            maps_url="http://maps.apple.com/?daddr=123%20Main%20St",
            trust_zone="household_schedule",
            boundary_reason="Schedule routing stays bounded through sandbox review.",
        )

        self.assertTrue(request_id)
        self.assertEqual(decision["resolution"], "stage")
        item = queue.get_by_id(request_id)
        self.assertIsNotNone(item)
        assert item is not None
        self.assertEqual(item.agent_id, "herald")
        self.assertEqual(item.action_type, "calendar_route")
        self.assertEqual(item.trust_zone_id, "household_schedule")
        self.assertEqual(item.lane_id, "executive-calendar")
        self.assertEqual(item.arena_id, "household.schedule.routing")
        self.assertEqual(item.payload.get("_sandbox_job_id"), "calendar-route:evt-42")


if __name__ == "__main__":
    unittest.main()
