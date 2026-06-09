"""
GAP-3: Verify that ApprovalGuard is fail-closed when supervision evaluation fails.

Prior behavior: exceptions in evaluate_action were swallowed and execution proceeded
without any supervision ruling.  New behavior: fail at staging; block at execution.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import jarvis.approvals as approvals_module
from jarvis.approvals import ActionExecutors, ApprovalGuard, ApprovalQueue


class _FaultySupervisionSupport:
    """Always raises — simulates a supervision engine fault."""

    def evaluate_action(self, **kwargs) -> dict:
        raise RuntimeError("supervision engine unavailable")


class _StubSupervision:
    """Returns a valid resolution for staging; raises on the second call (execution re-evaluation)."""

    def __init__(self, staging_resolution: str = "stage") -> None:
        self._call_count = 0
        self._staging_resolution = staging_resolution

    def evaluate_action(self, **kwargs) -> dict:
        self._call_count += 1
        if self._call_count == 1:
            return {
                "resolution": self._staging_resolution,
                "sandbox_required": False,
                "approval_required": True,
                "escalation_required": False,
            }
        raise RuntimeError("supervision engine unavailable on second call")


class _NoResolutionSupervision:
    """Returns a dict without a resolution field at staging — then raises at execution."""

    def __init__(self) -> None:
        self._call_count = 0

    def evaluate_action(self, **kwargs) -> dict:
        self._call_count += 1
        if self._call_count == 1:
            return {}  # no resolution field
        raise RuntimeError("unavailable")


def _make_guard(tmp_path: Path, supervision, *, sandbox_router=None) -> tuple[ApprovalGuard, ApprovalQueue]:
    original_root = ApprovalQueue.ROOT
    ApprovalQueue.ROOT = tmp_path / "approvals"
    queue = ApprovalQueue()
    guard = ApprovalGuard(queue, supervision_support=supervision, sandbox_router=sandbox_router)
    ApprovalQueue.ROOT = original_root
    return guard, queue


class TestStagingFailClosed(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.tmp = Path(self.tempdir.name)
        self.original_root = ApprovalQueue.ROOT
        self.addCleanup(lambda: setattr(ApprovalQueue, "ROOT", self.original_root))
        ApprovalQueue.ROOT = self.tmp / "approvals"

    def test_staging_raises_when_supervision_throws(self) -> None:
        """request_approval must raise (not silently proceed) if evaluate_action fails."""
        guard, _ = _make_guard(self.tmp, _FaultySupervisionSupport())
        with self.assertRaises(RuntimeError) as ctx:
            guard.request_approval(
                agent_id="pepper",
                agent_label="Pepper",
                action_type="other",
                title="Test action",
                description="Should not stage",
                payload={},
                context={"trust_zone_id": "household_schedule", "lane_id": "family-stewardship"},
            )
        self.assertIn("Supervision evaluation failed", str(ctx.exception))

    def test_staging_succeeds_without_trust_zone(self) -> None:
        """When no trust_zone_id or lane_id, supervision is not called; staging proceeds."""
        guard, queue = _make_guard(self.tmp, _FaultySupervisionSupport())
        request_id = guard.request_approval(
            agent_id="pepper",
            agent_label="Pepper",
            action_type="other",
            title="Ungoverned action",
            description="No trust zone — supervision not invoked",
            payload={},
            context={},  # no trust_zone_id or lane_id
        )
        item = queue.get_by_id(request_id)
        self.assertIsNotNone(item)


class TestExecutionFailClosed(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.tmp = Path(self.tempdir.name)
        self.original_root = ApprovalQueue.ROOT
        self.addCleanup(lambda: setattr(ApprovalQueue, "ROOT", self.original_root))
        ApprovalQueue.ROOT = self.tmp / "approvals"
        self.original_dispatch = dict(ActionExecutors._DISPATCH)
        self.addCleanup(lambda: ActionExecutors._DISPATCH.update(self.original_dispatch))
        ActionExecutors._DISPATCH["other"] = staticmethod(lambda payload: {"status": "ok"})

    def test_execution_uses_stored_decision_when_re_evaluation_fails(self) -> None:
        """If re-evaluation throws but stored decision has a valid resolution, use stored."""
        guard, queue = _make_guard(self.tmp, _StubSupervision(staging_resolution="stage"))
        request_id = guard.request_approval(
            agent_id="pepper",
            agent_label="Pepper",
            action_type="other",
            title="Stored decision test",
            description="Supervision works at staging, fails at execution re-eval",
            payload={},
            context={"trust_zone_id": "household_schedule"},
        )
        queue.approve(request_id, approved_by="chris")
        # Should not raise — stored resolution="stage" allows execution
        result = guard.execute_approved(request_id)
        self.assertIn(result["status"], {"ok", "completed", "failed", "error"})

    def test_execution_blocked_when_stored_decision_empty_and_re_evaluation_fails(self) -> None:
        """If stored decision has no resolution AND re-evaluation fails, execution must be blocked."""
        # Guard whose supervision always raises — simulates fault at execution time.
        guard, queue = _make_guard(self.tmp, _FaultySupervisionSupport())

        # Inject an item that was queued with an empty supervision_decision (pre-fix scenario).
        import uuid
        from jarvis.approvals import ApprovalRequest, _now_iso, _iso_plus_seconds

        item = ApprovalRequest(
            request_id=str(uuid.uuid4()),
            agent_id="pepper",
            agent_label="Pepper",
            action_type="other",
            title="Empty decision test",
            description="Stored decision is empty",
            payload={},
            risk_tier="LOW",
            actor_id="chris",
            requested_at=_now_iso(),
            expires_at=_iso_plus_seconds(3600),
            status="pending",
            trust_zone_id="household_schedule",
            supervision_decision={},  # empty — re-evaluation will also fail
        )
        queue.submit(item)
        queue.approve(item.request_id, approved_by="chris")

        result = guard.execute_approved(item.request_id)
        self.assertEqual(result["status"], "error")
        self.assertIn("supervision policy", result["detail"])

    def test_degraded_block_sets_degraded_flag(self) -> None:
        """The degraded-block response must carry degraded=True so callers can surface it."""
        guard, _queue = _make_guard(self.tmp, _FaultySupervisionSupport())

        # Call _resolve_supervision_decision directly with a fake item that has empty stored decision
        from unittest.mock import MagicMock
        from jarvis.approvals import ApprovalRequest, _now_iso, _iso_plus_seconds

        item = MagicMock(spec=ApprovalRequest)
        item.supervision_decision = {}
        item.trust_zone_id = "household_schedule"
        item.lane_id = ""
        item.agent_id = "pepper"
        item.action_type = "other"
        item.requested_outcome = "test"
        item.arena_id = ""
        item.supervision_context = {}

        decision = guard._resolve_supervision_decision(item)
        self.assertEqual(decision.get("resolution"), "forbidden")
        self.assertTrue(decision.get("degraded"))


if __name__ == "__main__":
    unittest.main()
