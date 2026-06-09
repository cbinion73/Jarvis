"""
Boundary enforcement for newly added action types:
- stewardship_lane_review (runtime.py:8957 call site)
- foundry_proposal_review (/api/foundry/proposals/{id}/approve)

Both were previously missing from the restricted set, so a zone at observe
would return 'allow' instead of 'stage'. After the fix they enforce the same
sequence rule as all other governed action types.
"""
from __future__ import annotations

import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

from jarvis.trust import TrustStore, TrustSupport
from jarvis.models import TrustZone


def _make_runtime(tmp_path: Path):
    store = TrustStore(tmp_path)
    ts = TrustSupport(store=store, default_owner_principal="chris")
    ts.bootstrap_defaults()
    import jarvis.runtime as runtime_mod
    obj = object.__new__(runtime_mod.JarvisRuntime)
    obj.trust_support = ts
    return obj


def _add_zone(ts: TrustSupport, *, zone_id: str, authority_stage: str, status: str = "active"):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    records = ts.store.list_trust_zones()
    records = [r for r in records if str(r.get("zone_id", "")) != zone_id]
    records.append(asdict(TrustZone(
        zone_id=zone_id,
        name=f"Test Zone {zone_id}",
        description="",
        zone_type="household",
        authority_stage=authority_stage,
        resource_scope={},
        allowed_actions=[],
        approval_mode="stage_and_alert",
        audit_mode="standard",
        promotion_rules={},
        demotion_rules={},
        status=status,
        created_at=now,
        updated_at=now,
    )))
    ts.store.save_trust_zones(records)


class TestStewardshipLaneReviewBoundary(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.runtime = _make_runtime(Path(self.tmpdir.name))

    def test_observe_zone_returns_stage_for_stewardship_lane_review(self):
        _add_zone(self.runtime.trust_support, zone_id="tz_observe", authority_stage="observe")
        result = self.runtime.assess_action_boundary(
            zone_id="tz_observe",
            action_type="stewardship_lane_review",
            requested_stage="sandbox_live",
        )
        self.assertEqual(result["decision"], "stage",
                         "stewardship_lane_review at observe must be staged, not allowed")

    def test_draft_zone_returns_stage_for_stewardship_lane_review(self):
        _add_zone(self.runtime.trust_support, zone_id="tz_draft", authority_stage="draft")
        result = self.runtime.assess_action_boundary(
            zone_id="tz_draft",
            action_type="stewardship_lane_review",
            requested_stage="sandbox_live",
        )
        self.assertEqual(result["decision"], "stage")

    def test_stage_alert_zone_returns_stage_for_stewardship_lane_review(self):
        _add_zone(self.runtime.trust_support, zone_id="tz_stage_alert", authority_stage="stage_alert")
        result = self.runtime.assess_action_boundary(
            zone_id="tz_stage_alert",
            action_type="stewardship_lane_review",
            requested_stage="sandbox_live",
        )
        self.assertEqual(result["decision"], "stage")

    def test_sandbox_live_zone_returns_allow_for_stewardship_lane_review(self):
        _add_zone(self.runtime.trust_support, zone_id="tz_sandbox", authority_stage="sandbox_live")
        result = self.runtime.assess_action_boundary(
            zone_id="tz_sandbox",
            action_type="stewardship_lane_review",
            requested_stage="sandbox_live",
        )
        self.assertEqual(result["decision"], "allow")

    def test_mature_live_zone_returns_allow_for_stewardship_lane_review(self):
        _add_zone(self.runtime.trust_support, zone_id="tz_mature", authority_stage="mature_live")
        result = self.runtime.assess_action_boundary(
            zone_id="tz_mature",
            action_type="stewardship_lane_review",
            requested_stage="sandbox_live",
        )
        self.assertEqual(result["decision"], "allow")


class TestFoundryProposalReviewBoundary(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.runtime = _make_runtime(Path(self.tmpdir.name))

    def test_observe_zone_returns_stage_for_foundry_proposal_review(self):
        _add_zone(self.runtime.trust_support, zone_id="tz_obs2", authority_stage="observe")
        result = self.runtime.assess_action_boundary(
            zone_id="tz_obs2",
            action_type="foundry_proposal_review",
            requested_stage="sandbox_live",
        )
        self.assertEqual(result["decision"], "stage",
                         "foundry_proposal_review at observe must be staged")

    def test_stage_alert_zone_returns_stage_for_foundry_proposal_review(self):
        """system_agent is bootstrapped at stage_alert — approve must be staged there."""
        result = self.runtime.assess_action_boundary(
            zone_id="system_agent",
            action_type="foundry_proposal_review",
            requested_stage="sandbox_live",
        )
        self.assertEqual(result["decision"], "stage")

    def test_sandbox_live_zone_returns_allow_for_foundry_proposal_review(self):
        _add_zone(self.runtime.trust_support, zone_id="tz_sandbox2", authority_stage="sandbox_live")
        result = self.runtime.assess_action_boundary(
            zone_id="tz_sandbox2",
            action_type="foundry_proposal_review",
            requested_stage="sandbox_live",
        )
        self.assertEqual(result["decision"], "allow")


class TestRestrictedSetCompleteness(unittest.TestCase):
    """All known governed action types must produce 'stage' at observe level."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.runtime = _make_runtime(Path(self.tmpdir.name))
        _add_zone(self.runtime.trust_support, zone_id="tz_observe_all", authority_stage="observe")

    def test_all_governed_action_types_stage_at_observe(self):
        governed = [
            "home_control",
            "calendar_route",
            "signal_resolution",
            "notification_workflow",
            "reminder_workflow",
            "publishing_review",
            "focus_workflow",
            "huddle_workflow",
            "stewardship_lane_review",
            "foundry_proposal_review",
        ]
        for action_type in governed:
            with self.subTest(action_type=action_type):
                result = self.runtime.assess_action_boundary(
                    zone_id="tz_observe_all",
                    action_type=action_type,
                    requested_stage="sandbox_live",
                )
                self.assertEqual(result["decision"], "stage",
                                 f"{action_type} must be staged at observe level")


if __name__ == "__main__":
    unittest.main()
