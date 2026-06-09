"""
Phase B Audit: assess_action_boundary enforcement across all four trust zone levels.

Tests verify negative paths and sequence enforcement for all four levels:
  Observe (sequence=0) / Draft+Stage (sequence=1-2) / Sandbox Live (sequence=3) / Mature Delegated (sequence=4)

Negative paths:
- Unknown zone → decision=deny
- Zone status != active → decision=deny
- Unknown arena (when arena_id provided) → decision=deny
- Arena suspended or paused → decision=deny

Sequence enforcement for restricted action types (home_control, notification_workflow, etc.):
- Zone at observe requesting sandbox_live → decision=stage
- Zone at draft requesting sandbox_live → decision=stage
- Zone at stage_alert requesting sandbox_live → decision=stage
- Zone at sandbox_live requesting sandbox_live → decision=allow
- Zone at mature_live requesting sandbox_live → decision=allow

Non-apple_api call site (runtime.py stewardship lane):
- action_type=stewardship_lane_review is not in the restricted list → allow at any stage

Bootstrapped zone states:
- household_attention at stage_alert, requesting sandbox_live for notification_workflow → stage
- household_tasks at stage_alert, requesting sandbox_live for reminder_workflow → stage
- household_schedule at sandbox_live, requesting sandbox_live for calendar_route → allow
"""
from __future__ import annotations

import tempfile
import types
import unittest
from dataclasses import asdict
from pathlib import Path

from jarvis.trust import TrustStore, TrustSupport
from jarvis.models import TrustZone, ResourceArena


def _make_trust_support(tmp_path: Path) -> TrustSupport:
    store = TrustStore(tmp_path)
    ts = TrustSupport(store=store, default_owner_principal="chris")
    ts.bootstrap_defaults()
    return ts


def _make_runtime(ts: TrustSupport):
    """Minimal stand-in for JarvisRuntime — only needs trust_support for these tests."""
    import jarvis.runtime as runtime_mod
    obj = object.__new__(runtime_mod.JarvisRuntime)
    obj.trust_support = ts
    return obj


def _add_zone(ts: TrustSupport, *, zone_id: str, authority_stage: str, status: str = "active"):
    """Add or update a trust zone in TrustSupport's store."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    records = ts.store.list_trust_zones()
    records = [r for r in records if str(r.get("zone_id", "")) != zone_id]
    records.append(asdict(TrustZone(
        zone_id=zone_id,
        name=f"Test Zone {zone_id}",
        description="Test zone",
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


def _add_arena(ts: TrustSupport, *, arena_id: str, status: str = "active"):
    """Add or update a resource arena in TrustSupport's store."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    records = ts.store.list_resource_arenas()
    records = [r for r in records if str(r.get("arena_id", "")) != arena_id]
    records.append(asdict(ResourceArena(
        arena_id=arena_id,
        name=f"Test Arena {arena_id}",
        resource_type="test",
        linked_zone_id="test_zone",
        owner_principal="chris",
        risk_class="low",
        limits={},
        pause_conditions=[],
        status=status,
        created_at=now,
        updated_at=now,
    )))
    ts.store.save_resource_arenas(records)


# ---------------------------------------------------------------------------
# Negative paths
# ---------------------------------------------------------------------------

class TestBoundaryNegativePaths(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.root = Path(self.tmpdir.name)
        self.ts = _make_trust_support(self.root)
        self.runtime = _make_runtime(self.ts)

    def test_unknown_zone_returns_deny(self):
        result = self.runtime.assess_action_boundary(
            zone_id="nonexistent_zone",
            action_type="home_control",
            requested_stage="sandbox_live",
        )
        self.assertEqual(result["decision"], "deny")
        self.assertIn("nonexistent_zone", result.get("reason", ""))

    def test_inactive_zone_returns_deny(self):
        _add_zone(self.ts, zone_id="test_inactive", authority_stage="sandbox_live", status="inactive")
        result = self.runtime.assess_action_boundary(
            zone_id="test_inactive",
            action_type="home_control",
            requested_stage="sandbox_live",
        )
        self.assertEqual(result["decision"], "deny")
        self.assertIn("not active", result.get("reason", "").lower())

    def test_suspended_zone_returns_deny(self):
        _add_zone(self.ts, zone_id="test_suspended", authority_stage="mature_live", status="suspended")
        result = self.runtime.assess_action_boundary(
            zone_id="test_suspended",
            action_type="home_control",
            requested_stage="sandbox_live",
        )
        self.assertEqual(result["decision"], "deny")

    def test_unknown_arena_returns_deny(self):
        _add_zone(self.ts, zone_id="test_zone_arena", authority_stage="sandbox_live")
        result = self.runtime.assess_action_boundary(
            zone_id="test_zone_arena",
            arena_id="nonexistent.arena",
            action_type="home_control",
            requested_stage="sandbox_live",
        )
        self.assertEqual(result["decision"], "deny")
        self.assertIn("nonexistent.arena", result.get("reason", ""))

    def test_suspended_arena_returns_deny(self):
        _add_zone(self.ts, zone_id="test_zone_susp_arena", authority_stage="sandbox_live")
        _add_arena(self.ts, arena_id="test.susp.arena", status="suspended")
        result = self.runtime.assess_action_boundary(
            zone_id="test_zone_susp_arena",
            arena_id="test.susp.arena",
            action_type="home_control",
            requested_stage="sandbox_live",
        )
        self.assertEqual(result["decision"], "deny")
        self.assertIn("suspended", result.get("reason", "").lower())

    def test_paused_arena_returns_deny(self):
        _add_zone(self.ts, zone_id="test_zone_paused_arena", authority_stage="sandbox_live")
        _add_arena(self.ts, arena_id="test.paused.arena", status="paused")
        result = self.runtime.assess_action_boundary(
            zone_id="test_zone_paused_arena",
            arena_id="test.paused.arena",
            action_type="home_control",
            requested_stage="sandbox_live",
        )
        self.assertEqual(result["decision"], "deny")


# ---------------------------------------------------------------------------
# Sequence enforcement — restricted action types
# ---------------------------------------------------------------------------

class TestBoundarySequenceEnforcement(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.root = Path(self.tmpdir.name)
        self.ts = _make_trust_support(self.root)
        self.runtime = _make_runtime(self.ts)

    def test_observe_requesting_sandbox_live_returns_stage(self):
        _add_zone(self.ts, zone_id="test_observe", authority_stage="observe")
        result = self.runtime.assess_action_boundary(
            zone_id="test_observe",
            action_type="home_control",
            requested_stage="sandbox_live",
        )
        self.assertEqual(result["decision"], "stage")
        self.assertEqual(result["authority_stage"], "observe")

    def test_draft_requesting_sandbox_live_returns_stage(self):
        _add_zone(self.ts, zone_id="test_draft", authority_stage="draft")
        result = self.runtime.assess_action_boundary(
            zone_id="test_draft",
            action_type="notification_workflow",
            requested_stage="sandbox_live",
        )
        self.assertEqual(result["decision"], "stage")
        self.assertEqual(result["authority_stage"], "draft")

    def test_stage_alert_requesting_sandbox_live_returns_stage(self):
        _add_zone(self.ts, zone_id="test_stage_alert", authority_stage="stage_alert")
        result = self.runtime.assess_action_boundary(
            zone_id="test_stage_alert",
            action_type="reminder_workflow",
            requested_stage="sandbox_live",
        )
        self.assertEqual(result["decision"], "stage")
        self.assertEqual(result["authority_stage"], "stage_alert")

    def test_sandbox_live_requesting_sandbox_live_returns_allow(self):
        _add_zone(self.ts, zone_id="test_sandbox", authority_stage="sandbox_live")
        result = self.runtime.assess_action_boundary(
            zone_id="test_sandbox",
            action_type="home_control",
            requested_stage="sandbox_live",
        )
        self.assertEqual(result["decision"], "allow")

    def test_mature_live_requesting_sandbox_live_returns_allow(self):
        _add_zone(self.ts, zone_id="test_mature", authority_stage="mature_live")
        result = self.runtime.assess_action_boundary(
            zone_id="test_mature",
            action_type="home_control",
            requested_stage="sandbox_live",
        )
        self.assertEqual(result["decision"], "allow")

    def test_all_restricted_action_types_enforce_sequence(self):
        """Every action type in the restricted set must produce 'stage' when zone is at observe."""
        _add_zone(self.ts, zone_id="test_observe_all", authority_stage="observe")
        restricted = [
            "home_control", "calendar_route", "signal_resolution",
            "notification_workflow", "reminder_workflow", "publishing_review",
            "focus_workflow", "huddle_workflow",
        ]
        for action_type in restricted:
            with self.subTest(action_type=action_type):
                result = self.runtime.assess_action_boundary(
                    zone_id="test_observe_all",
                    action_type=action_type,
                    requested_stage="sandbox_live",
                )
                self.assertEqual(result["decision"], "stage",
                                 f"{action_type} should be staged at observe level")


# ---------------------------------------------------------------------------
# Non-restricted action type (stewardship_lane_review call site)
# ---------------------------------------------------------------------------

class TestNonRestrictedActionType(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.root = Path(self.tmpdir.name)
        self.ts = _make_trust_support(self.root)
        self.runtime = _make_runtime(self.ts)

    def test_non_restricted_action_allows_at_observe(self):
        """stewardship_lane_review is not in the restricted set — zone at observe still allows."""
        _add_zone(self.ts, zone_id="test_stewardship_zone", authority_stage="observe")
        result = self.runtime.assess_action_boundary(
            zone_id="test_stewardship_zone",
            action_type="stewardship_lane_review",
            requested_stage="sandbox_live",
        )
        self.assertEqual(result["decision"], "allow",
                         "Non-restricted action types bypass sequence enforcement")

    def test_non_restricted_action_result_contains_zone_id(self):
        _add_zone(self.ts, zone_id="test_stewardship_zone2", authority_stage="stage_alert")
        result = self.runtime.assess_action_boundary(
            zone_id="test_stewardship_zone2",
            action_type="stewardship_lane_review",
            requested_stage="sandbox_live",
        )
        self.assertEqual(result["trust_zone"], "test_stewardship_zone2")


# ---------------------------------------------------------------------------
# Bootstrapped zone real-world states
# ---------------------------------------------------------------------------

class TestBootstrappedZoneStates(unittest.TestCase):
    """Verify that bootstrapped zones behave correctly under boundary checks."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.root = Path(self.tmpdir.name)
        self.ts = _make_trust_support(self.root)
        self.runtime = _make_runtime(self.ts)

    def test_household_attention_stage_alert_requests_sandbox_live_returns_stage(self):
        """household_attention is bootstrapped at stage_alert; sandbox_live request should stage."""
        result = self.runtime.assess_action_boundary(
            zone_id="household_attention",
            action_type="notification_workflow",
            requested_stage="sandbox_live",
        )
        self.assertEqual(result["decision"], "stage")
        self.assertEqual(result["authority_stage"], "stage_alert")

    def test_household_tasks_stage_alert_requests_sandbox_live_returns_stage(self):
        """household_tasks is bootstrapped at stage_alert; sandbox_live request should stage."""
        result = self.runtime.assess_action_boundary(
            zone_id="household_tasks",
            action_type="reminder_workflow",
            requested_stage="sandbox_live",
        )
        self.assertEqual(result["decision"], "stage")

    def test_household_schedule_sandbox_live_requests_sandbox_live_returns_allow(self):
        """household_schedule is bootstrapped at sandbox_live; should allow sandbox_live actions."""
        result = self.runtime.assess_action_boundary(
            zone_id="household_schedule",
            action_type="calendar_route",
            requested_stage="sandbox_live",
        )
        self.assertEqual(result["decision"], "allow")

    def test_household_home_draft_requests_sandbox_live_returns_stage(self):
        """household_home is bootstrapped at draft; sandbox_live request should stage."""
        result = self.runtime.assess_action_boundary(
            zone_id="household_home",
            action_type="home_control",
            requested_stage="sandbox_live",
        )
        self.assertEqual(result["decision"], "stage")

    def test_household_safety_stage_alert_requests_sandbox_live_returns_stage(self):
        """household_safety is bootstrapped at stage_alert; sandbox_live request should stage."""
        result = self.runtime.assess_action_boundary(
            zone_id="household_safety",
            action_type="signal_resolution",
            requested_stage="sandbox_live",
        )
        self.assertEqual(result["decision"], "stage")

    def test_household_perception_sandbox_live_requests_sandbox_live_returns_allow(self):
        """household_perception is bootstrapped at sandbox_live; should allow."""
        result = self.runtime.assess_action_boundary(
            zone_id="household_perception",
            action_type="signal_resolution",
            requested_stage="sandbox_live",
        )
        self.assertEqual(result["decision"], "allow")

    def test_publication_review_stage_alert_requests_sandbox_live_returns_stage(self):
        """publication_review is bootstrapped at stage_alert."""
        result = self.runtime.assess_action_boundary(
            zone_id="publication_review",
            action_type="publishing_review",
            requested_stage="sandbox_live",
        )
        self.assertEqual(result["decision"], "stage")


# ---------------------------------------------------------------------------
# Response shape completeness
# ---------------------------------------------------------------------------

class TestBoundaryResponseShape(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.root = Path(self.tmpdir.name)
        self.ts = _make_trust_support(self.root)
        self.runtime = _make_runtime(self.ts)

    def _required_keys(self):
        return {"decision", "reason", "trust_zone", "authority_stage", "approval_mode", "arena_status"}

    def test_deny_response_has_required_keys(self):
        result = self.runtime.assess_action_boundary(
            zone_id="nonexistent",
            action_type="home_control",
            requested_stage="sandbox_live",
        )
        for key in self._required_keys():
            self.assertIn(key, result, f"Missing key '{key}' in deny response")

    def test_stage_response_has_required_keys(self):
        _add_zone(self.ts, zone_id="test_keys_stage", authority_stage="observe")
        result = self.runtime.assess_action_boundary(
            zone_id="test_keys_stage",
            action_type="home_control",
            requested_stage="sandbox_live",
        )
        for key in self._required_keys():
            self.assertIn(key, result, f"Missing key '{key}' in stage response")

    def test_allow_response_has_required_keys(self):
        _add_zone(self.ts, zone_id="test_keys_allow", authority_stage="sandbox_live")
        result = self.runtime.assess_action_boundary(
            zone_id="test_keys_allow",
            action_type="home_control",
            requested_stage="sandbox_live",
        )
        for key in self._required_keys():
            self.assertIn(key, result, f"Missing key '{key}' in allow response")


if __name__ == "__main__":
    unittest.main()
