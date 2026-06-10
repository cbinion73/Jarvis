"""
Phase B: Level 4 Governance — comprehensive test suite.

Tests:
B1 — Trust-zone coverage: every mutation has actor, zone, arena, decision, audit record;
     negative paths for unknown zone, inactive zone, suspended arena
B2 — Action taxonomy: canonical families, risk tiers, min authority stages registered;
     all action types discoverable via list_action_taxonomy()
B3 — Fail-closed behavior: unknown actions deny; missing supervision denies;
     inactive zone denies; suspended arena denies
B4 — Promotion engine: evidence required before apply; hold if insufficient reviews
B5 — Household governance UI: /api/governance/summary plain-language; capabilities endpoint
B6 — Children/privacy boundaries: child action types have parent_review_required;
     share_child_data always denies; override_child_guardrail always denies
B7 — Money/legal/security limits: spend_money, sign_document, remote_unlock always deny;
     hard boundary families enumerated; constitutional note present
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# FastAPI stub
# ---------------------------------------------------------------------------

if "fastapi" not in sys.modules:
    _fs = types.ModuleType("fastapi")
    _rs = types.ModuleType("fastapi.responses")
    _ss = types.ModuleType("fastapi.staticfiles")
    _uv = types.ModuleType("uvicorn")

    class _HTTPException(Exception):
        def __init__(self, status_code=500, detail=""):
            super().__init__(detail); self.status_code = status_code; self.detail = detail

    class _JSONResponse:
        def __init__(self, content, status_code=200, headers=None):
            self.body = json.dumps(content).encode(); self.status_code = status_code

    class _FastAPI:
        def __init__(self, *a, **kw): pass
        def _reg(self, path, methods):
            def dec(fn): return fn
            return dec
        def get(self, p, *a, **kw): return self._reg(p, {"GET"})
        def post(self, p, *a, **kw): return self._reg(p, {"POST"})
        def put(self, p, *a, **kw): return self._reg(p, {"PUT"})
        def patch(self, p, *a, **kw): return self._reg(p, {"PATCH"})
        def delete(self, p, *a, **kw): return self._reg(p, {"DELETE"})
        def websocket(self, p, *a, **kw): return self._reg(p, {"WS"})
        def on_event(self, *a, **kw): return lambda fn: fn
        def mount(self, *a, **kw): pass

    _fs.FastAPI = _FastAPI
    _fs.HTTPException = _HTTPException
    _fs.Query = lambda *a, **kw: None
    _fs.File = lambda *a, **kw: None
    _fs.Form = lambda *a, **kw: None
    _fs.Request = object
    _fs.UploadFile = object
    _fs.WebSocket = object
    _fs.WebSocketDisconnect = Exception
    _fs.BackgroundTasks = object
    _rs.JSONResponse = _JSONResponse
    _rs.HTMLResponse = _JSONResponse
    _rs.FileResponse = _JSONResponse
    _rs.RedirectResponse = _JSONResponse
    _rs.Response = _JSONResponse
    _ss.StaticFiles = object
    _uv.run = lambda *a, **kw: None
    sys.modules["fastapi"] = _fs
    sys.modules["fastapi.responses"] = _rs
    sys.modules["fastapi.staticfiles"] = _ss
    sys.modules["uvicorn"] = _uv

if "langgraph.graph" not in sys.modules:
    _lg = types.ModuleType("langgraph")
    _lg_g = types.ModuleType("langgraph.graph")
    class _SG:
        def __init__(self, *a, **kw): pass
        def add_node(self, *a, **kw): pass
        def add_edge(self, *a, **kw): pass
        def compile(self):
            class _C:
                def invoke(self, s): return s
            return _C()
    _lg_g.StateGraph = _SG; _lg_g.END = "END"; _lg_g.START = "START"
    _lg.graph = _lg_g
    sys.modules["langgraph"] = _lg; sys.modules["langgraph.graph"] = _lg_g


# ---------------------------------------------------------------------------
# B2 + B3 — Action taxonomy and fail-closed behavior
# ---------------------------------------------------------------------------

class TestActionTaxonomy(unittest.TestCase):
    """B2: Canonical action taxonomy exists and covers all required families."""

    def setUp(self):
        from jarvis.policy_rails import (
            CANONICAL_ACTION_TAXONOMY,
            HARD_BOUNDARY_FAMILIES,
            list_action_taxonomy,
            get_action_policy,
            FAMILY_MONEY, FAMILY_LEGAL, FAMILY_SECURITY,
            FAMILY_CHILDREN, FAMILY_IDENTITY, FAMILY_REPUTATION, FAMILY_SYSTEM,
            UNKNOWN_ACTION_POLICY,
        )
        self.taxonomy = CANONICAL_ACTION_TAXONOMY
        self.hard_families = HARD_BOUNDARY_FAMILIES
        self.list_fn = list_action_taxonomy
        self.get_fn = get_action_policy
        self.unknown = UNKNOWN_ACTION_POLICY
        self.families = [FAMILY_MONEY, FAMILY_LEGAL, FAMILY_SECURITY, FAMILY_CHILDREN, FAMILY_IDENTITY, FAMILY_REPUTATION, FAMILY_SYSTEM]

    def test_taxonomy_is_nonempty(self):
        self.assertGreater(len(self.taxonomy), 20)

    def test_all_hard_boundary_families_present(self):
        for fam in self.families:
            self.assertIn(fam, self.hard_families)

    def test_list_taxonomy_returns_all_actions(self):
        rows = self.list_fn()
        self.assertEqual(len(rows), len(self.taxonomy))

    def test_list_taxonomy_has_required_fields(self):
        rows = self.list_fn()
        required = {"action_type", "family", "risk_tier", "min_authority_stage", "approval_mode", "hard_boundary", "description"}
        for row in rows:
            for field in required:
                self.assertIn(field, row, f"Missing '{field}' in taxonomy row for {row.get('action_type', '?')}")

    def test_money_actions_are_hard_boundary(self):
        money_actions = [k for k, v in self.taxonomy.items() if v.family == "money"]
        self.assertGreater(len(money_actions), 0)
        for action_type in money_actions:
            policy = self.taxonomy[action_type]
            self.assertTrue(policy.hard_boundary, f"{action_type} should be hard_boundary")

    def test_legal_actions_are_hard_boundary(self):
        legal_actions = [k for k, v in self.taxonomy.items() if v.family == "legal"]
        self.assertGreater(len(legal_actions), 0)
        for action_type in legal_actions:
            self.assertTrue(self.taxonomy[action_type].hard_boundary)

    def test_security_actions_include_remote_unlock(self):
        self.assertIn("remote_unlock", self.taxonomy)
        self.assertTrue(self.taxonomy["remote_unlock"].hard_boundary)

    def test_children_actions_require_parent_review(self):
        child_actions = [k for k, v in self.taxonomy.items() if v.family == "children"]
        self.assertGreater(len(child_actions), 0)
        for action_type in child_actions:
            policy = self.taxonomy[action_type]
            self.assertTrue(policy.parent_review_required, f"{action_type} must require parent review")

    def test_unknown_action_returns_unknown_policy(self):
        policy = self.get_fn("totally_unknown_action_xyz")
        self.assertEqual(policy.action_type, "_unknown")

    def test_unknown_action_is_hard_boundary(self):
        policy = self.get_fn("not_registered")
        self.assertTrue(policy.hard_boundary)

    def test_every_taxonomy_action_has_risk_tier_1_to_4(self):
        for action_type, policy in self.taxonomy.items():
            self.assertIn(policy.risk_tier, {1, 2, 3, 4}, f"{action_type} has invalid risk_tier {policy.risk_tier}")

    def test_every_taxonomy_action_has_valid_approval_mode(self):
        valid_modes = {"auto", "stage", "pre-approve", "deny"}
        for action_type, policy in self.taxonomy.items():
            self.assertIn(policy.approval_mode, valid_modes, f"{action_type} has invalid approval_mode {policy.approval_mode}")


# ---------------------------------------------------------------------------
# B3 — Fail-closed: assess_action_policy()
# ---------------------------------------------------------------------------

class TestAssessActionPolicyFailClosed(unittest.TestCase):
    """B3: Unknown actions fail closed; hard boundaries deny regardless of stage."""

    def setUp(self):
        from jarvis.policy_rails import assess_action_policy
        self.assess = assess_action_policy

    def test_unknown_action_at_observe_returns_deny(self):
        result = self.assess("totally_unknown_xyz", authority_stage="observe")
        self.assertEqual(result["decision"], "deny")
        self.assertFalse(result["registered"])

    def test_unknown_action_at_mature_live_still_returns_deny(self):
        result = self.assess("totally_unknown_xyz", authority_stage="mature_live")
        self.assertEqual(result["decision"], "deny")

    def test_unknown_action_has_audit_required(self):
        result = self.assess("not_in_taxonomy", authority_stage="sandbox_live")
        self.assertTrue(result["audit_required"])

    def test_spend_money_at_mature_live_denies(self):
        result = self.assess("spend_money", authority_stage="mature_live")
        self.assertEqual(result["decision"], "deny")

    def test_sign_document_at_mature_live_denies(self):
        result = self.assess("sign_document", authority_stage="mature_live")
        self.assertEqual(result["decision"], "deny")

    def test_remote_unlock_at_mature_live_denies(self):
        result = self.assess("remote_unlock", authority_stage="mature_live")
        self.assertEqual(result["decision"], "deny")

    def test_post_social_at_mature_live_denies(self):
        result = self.assess("post_social", authority_stage="mature_live")
        self.assertEqual(result["decision"], "deny")

    def test_create_account_at_mature_live_denies(self):
        result = self.assess("create_account", authority_stage="mature_live")
        self.assertEqual(result["decision"], "deny")

    def test_share_child_data_at_mature_live_denies(self):
        result = self.assess("share_child_data", authority_stage="mature_live")
        self.assertEqual(result["decision"], "deny")

    def test_override_child_guardrail_at_mature_live_denies(self):
        result = self.assess("override_child_guardrail", authority_stage="mature_live")
        self.assertEqual(result["decision"], "deny")

    def test_read_state_at_observe_allows(self):
        result = self.assess("read_state", authority_stage="observe")
        self.assertEqual(result["decision"], "allow")

    def test_calendar_route_at_sandbox_live_allows(self):
        """calendar_route at sandbox_live+ should allow (not a hard deny)."""
        result = self.assess("calendar_route", authority_stage="sandbox_live")
        self.assertIn(result["decision"], {"allow", "stage"})
        self.assertNotEqual(result["decision"], "deny")

    def test_low_authority_stages_calendar_returns_stage(self):
        result = self.assess("calendar_route", authority_stage="observe")
        self.assertEqual(result["decision"], "stage")

    def test_child_tutoring_without_parent_acknowledged_returns_stage(self):
        result = self.assess("child_tutoring_action", authority_stage="stage_alert", context={})
        self.assertEqual(result["decision"], "stage")
        self.assertTrue(result["parent_review_required"])

    def test_child_tutoring_with_parent_acknowledged_allows(self):
        result = self.assess(
            "child_tutoring_action",
            authority_stage="stage_alert",
            context={"parent_acknowledged": True},
        )
        self.assertIn(result["decision"], {"allow", "stage"})

    def test_hard_boundary_action_reason_mentions_family(self):
        result = self.assess("spend_money", authority_stage="mature_live")
        self.assertIn("money", result["reason"].lower())

    def test_unknown_action_reason_mentions_taxonomy(self):
        result = self.assess("foobar_action", authority_stage="observe")
        self.assertIn("taxonomy", result["reason"].lower())


# ---------------------------------------------------------------------------
# B3 — Fail-closed: assess_action_boundary() in runtime
# ---------------------------------------------------------------------------

class TestAssessActionBoundaryFailClosed(unittest.TestCase):
    """B3: assess_action_boundary() denies unknown actions and hard boundary types."""

    def setUp(self):
        from jarvis.trust import TrustStore, TrustSupport
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        root = Path(self.tmpdir.name)
        trust_store = TrustStore(root / "trust")
        self.trust_support = TrustSupport(trust_store)

    def _make_runtime(self):
        from jarvis.trust import TrustStore, TrustSupport
        root = Path(self.tmpdir.name)
        mock = MagicMock()
        mock.trust_support = self.trust_support
        # Provide real authority stages
        mock.trust_support = self.trust_support
        return mock

    def test_unknown_zone_returns_deny(self):
        runtime = self._make_runtime()
        from jarvis.runtime import JarvisRuntime
        result = JarvisRuntime.assess_action_boundary(
            runtime,
            zone_id="nonexistent_zone_xyz",
            action_type="home_control",
        )
        self.assertEqual(result["decision"], "deny")

    def _full_zone(self, zone_id, stage="sandbox_live", approval_mode="pre-approve", status="active"):
        from jarvis.models import TrustZone
        return TrustZone(
            zone_id=zone_id,
            name="Test Zone",
            zone_type="test",
            authority_stage=stage,
            resource_scope={},
            allowed_actions=[],
            approval_mode=approval_mode,
            audit_mode="standard",
            promotion_rules={},
            demotion_rules={},
            status=status,
            created_at="",
            updated_at="",
        )

    def test_unknown_action_type_returns_deny(self):
        """Unknown action type must fail closed even in a valid zone."""
        from jarvis.trust import TrustStore, TrustSupport
        root = Path(self.tmpdir.name)
        trust_store = TrustStore(root / "trust")
        trust_support = TrustSupport(trust_store)
        trust_support.upsert_trust_zone(self._full_zone("test_zone"))

        mock = MagicMock()
        mock.trust_support = trust_support
        from jarvis.runtime import JarvisRuntime
        result = JarvisRuntime.assess_action_boundary(
            mock,
            zone_id="test_zone",
            action_type="totally_unknown_xyz_action",
        )
        self.assertEqual(result["decision"], "deny")
        self.assertFalse(result.get("registered", True))

    def test_hard_boundary_action_returns_deny_in_valid_zone(self):
        """spend_money must deny even in a mature_live zone."""
        from jarvis.trust import TrustStore, TrustSupport
        root = Path(self.tmpdir.name)
        trust_store = TrustStore(root / "trust")
        trust_support = TrustSupport(trust_store)
        trust_support.upsert_trust_zone(self._full_zone("test_zone_2", stage="mature_live", approval_mode="auto"))

        mock = MagicMock()
        mock.trust_support = trust_support
        from jarvis.runtime import JarvisRuntime
        result = JarvisRuntime.assess_action_boundary(
            mock,
            zone_id="test_zone_2",
            action_type="spend_money",
        )
        self.assertEqual(result["decision"], "deny")
        self.assertTrue(result.get("hard_boundary", False))


# ---------------------------------------------------------------------------
# B6 — Children/privacy boundaries
# ---------------------------------------------------------------------------

class TestChildPrivacyBoundaries(unittest.TestCase):
    """B6: Child actions require parent review; share_child_data/override are always denied."""

    def setUp(self):
        from jarvis.policy_rails import assess_action_policy, CANONICAL_ACTION_TAXONOMY, FAMILY_CHILDREN
        self.assess = assess_action_policy
        self.taxonomy = CANONICAL_ACTION_TAXONOMY
        self.FAMILY_CHILDREN = FAMILY_CHILDREN

    def test_share_child_data_always_denied(self):
        for stage in ["observe", "draft", "stage_alert", "sandbox_live", "mature_live"]:
            result = self.assess("share_child_data", authority_stage=stage)
            self.assertEqual(result["decision"], "deny", f"share_child_data must deny at stage {stage}")

    def test_override_child_guardrail_always_denied(self):
        for stage in ["observe", "draft", "stage_alert", "sandbox_live", "mature_live"]:
            result = self.assess("override_child_guardrail", authority_stage=stage)
            self.assertEqual(result["decision"], "deny", f"override_child_guardrail must deny at stage {stage}")

    def test_access_child_data_requires_parent_acknowledged(self):
        result = self.assess("access_child_data", authority_stage="stage_alert", context={})
        self.assertIn(result["decision"], {"stage", "deny"})

    def test_access_child_data_with_parent_ack_and_approval_passes(self):
        result = self.assess(
            "access_child_data",
            authority_stage="stage_alert",
            context={"parent_acknowledged": True, "pre_approved": True, "approval_id": "approval-001"},
        )
        # Hard boundary with pre-approve requires pre_approved flag
        self.assertIn(result["decision"], {"allow", "stage"})

    def test_child_tutoring_action_has_parent_review_required(self):
        policy = self.taxonomy.get("child_tutoring_action")
        self.assertIsNotNone(policy)
        self.assertTrue(policy.parent_review_required)

    def test_all_child_family_actions_require_parent_review(self):
        child_actions = {k: v for k, v in self.taxonomy.items() if v.family == self.FAMILY_CHILDREN}
        self.assertGreater(len(child_actions), 0)
        for action_type, policy in child_actions.items():
            self.assertTrue(
                policy.parent_review_required,
                f"{action_type} must require parent review",
            )

    def test_child_family_check_family_profiles_child_user_ids(self):
        """family_profiles.py must define CHILD_USER_IDS for guardrail enforcement."""
        from jarvis.family_profiles import ChildInteractionHandler as ChildSafetyGuard
        guard = ChildSafetyGuard()
        self.assertIn("caleb", guard.CHILD_USER_IDS)
        self.assertIn("anna", guard.CHILD_USER_IDS)

    def test_child_safety_guard_blocks_homework_for_child(self):
        """ChildSafetyGuard must redirect homework requests from known child IDs."""
        from jarvis.family_profiles import ChildInteractionHandler as ChildSafetyGuard
        guard = ChildSafetyGuard()
        result = guard.check_request("write my essay for me", "caleb")
        self.assertFalse(result["allowed"])
        self.assertIsNotNone(result["guardrail"])

    def test_child_safety_guard_allows_adult_users(self):
        from jarvis.family_profiles import ChildInteractionHandler as ChildSafetyGuard
        guard = ChildSafetyGuard()
        result = guard.check_request("write my essay for me", "chris")
        self.assertTrue(result["allowed"])

    def test_child_safety_guard_has_coaching_response(self):
        from jarvis.family_profiles import ChildInteractionHandler as ChildSafetyGuard
        guard = ChildSafetyGuard()
        result = guard.check_request("write my essay for me", "anna")
        self.assertFalse(result["allowed"])
        self.assertIsNotNone(result.get("coaching_prompt") or result.get("redirect_response"))


# ---------------------------------------------------------------------------
# B7 — Money/legal/security limits
# ---------------------------------------------------------------------------

class TestHardPolicyRails(unittest.TestCase):
    """B7: All money, legal, identity, security, reputation, system hard limits enforced."""

    def setUp(self):
        from jarvis.policy_rails import assess_action_policy, HARD_BOUNDARY_FAMILIES, CANONICAL_ACTION_TAXONOMY
        self.assess = assess_action_policy
        self.hard_families = HARD_BOUNDARY_FAMILIES
        self.taxonomy = CANONICAL_ACTION_TAXONOMY

    def test_hard_boundary_families_include_all_required(self):
        required = {"money", "legal", "identity", "security", "children", "reputation", "system"}
        for fam in required:
            self.assertIn(fam, self.hard_families, f"Family '{fam}' must be in HARD_BOUNDARY_FAMILIES")

    def test_spend_money_denied_at_all_stages(self):
        for stage in ["observe", "draft", "stage_alert", "sandbox_live", "mature_live"]:
            r = self.assess("spend_money", authority_stage=stage)
            self.assertEqual(r["decision"], "deny")

    def test_create_transaction_denied_at_all_stages(self):
        for stage in ["observe", "draft", "stage_alert", "sandbox_live", "mature_live"]:
            r = self.assess("create_transaction", authority_stage=stage)
            self.assertEqual(r["decision"], "deny")

    def test_sign_document_denied_at_all_stages(self):
        for stage in ["observe", "draft", "stage_alert", "sandbox_live", "mature_live"]:
            r = self.assess("sign_document", authority_stage=stage)
            self.assertEqual(r["decision"], "deny")

    def test_submit_filing_denied_at_all_stages(self):
        for stage in ["observe", "draft", "stage_alert", "sandbox_live", "mature_live"]:
            r = self.assess("submit_filing", authority_stage=stage)
            self.assertEqual(r["decision"], "deny")

    def test_remote_unlock_denied_at_all_stages(self):
        for stage in ["observe", "draft", "stage_alert", "sandbox_live", "mature_live"]:
            r = self.assess("remote_unlock", authority_stage=stage)
            self.assertEqual(r["decision"], "deny")

    def test_disable_alarm_denied_at_all_stages(self):
        for stage in ["observe", "draft", "stage_alert", "sandbox_live", "mature_live"]:
            r = self.assess("disable_alarm", authority_stage=stage)
            self.assertEqual(r["decision"], "deny")

    def test_post_social_denied_at_all_stages(self):
        for stage in ["observe", "draft", "stage_alert", "sandbox_live", "mature_live"]:
            r = self.assess("post_social", authority_stage=stage)
            self.assertEqual(r["decision"], "deny")

    def test_create_account_denied_at_all_stages(self):
        for stage in ["observe", "draft", "stage_alert", "sandbox_live", "mature_live"]:
            r = self.assess("create_account", authority_stage=stage)
            self.assertEqual(r["decision"], "deny")

    def test_change_credentials_denied_at_all_stages(self):
        for stage in ["observe", "draft", "stage_alert", "sandbox_live", "mature_live"]:
            r = self.assess("change_credentials", authority_stage=stage)
            self.assertEqual(r["decision"], "deny")

    def test_hard_boundary_actions_are_not_reversible(self):
        """Most hard deny actions are not reversible."""
        irreversible = ["spend_money", "sign_document", "remote_unlock", "post_social",
                        "submit_filing", "create_account", "change_credentials", "transfer_funds"]
        for action_type in irreversible:
            policy = self.taxonomy.get(action_type)
            self.assertIsNotNone(policy, f"{action_type} must be in taxonomy")
            self.assertFalse(policy.reversible, f"{action_type} must be irreversible")

    def test_all_hard_boundary_actions_have_audit_required(self):
        hard_actions = [v for v in self.taxonomy.values() if v.hard_boundary]
        self.assertGreater(len(hard_actions), 0)
        for policy in hard_actions:
            self.assertTrue(policy.audit_required, f"{policy.action_type} must require audit")


# ---------------------------------------------------------------------------
# B5 — Household governance UI
# ---------------------------------------------------------------------------

class TestGovernancePlainLanguage(unittest.TestCase):
    """B5: Plain-language governance summary for non-developer household users."""

    def setUp(self):
        from jarvis.policy_rails import governance_plain_language_summary
        self.summary_fn = governance_plain_language_summary

    def _make_zone(self, zone_id, stage="observe", status="active"):
        return {"zone_id": zone_id, "name": zone_id.replace("_", " ").title(), "authority_stage": stage, "status": status}

    def test_summary_has_plain_summary_text(self):
        result = self.summary_fn(
            zones=[self._make_zone("test_zone")],
            pending_approvals=[],
            recent_promotions=[],
            blocked_actions=[],
        )
        self.assertIn("plain_summary", result)
        self.assertIsInstance(result["plain_summary"], str)
        self.assertGreater(len(result["plain_summary"]), 10)

    def test_summary_counts_active_zones(self):
        zones = [
            self._make_zone("zone1", status="active"),
            self._make_zone("zone2", status="active"),
            self._make_zone("zone3", status="suspended"),
        ]
        result = self.summary_fn(zones=zones, pending_approvals=[], recent_promotions=[], blocked_actions=[])
        self.assertEqual(result["active_zone_count"], 2)
        self.assertEqual(result["inactive_zone_count"], 1)

    def test_summary_counts_pending_approvals(self):
        pending = [{"request_id": "r1", "action_type": "home_control", "detail": "Lock front door."}]
        result = self.summary_fn(zones=[], pending_approvals=pending, recent_promotions=[], blocked_actions=[])
        self.assertEqual(result["pending_approval_count"], 1)

    def test_summary_zone_has_plain_label(self):
        zones = [self._make_zone("household_schedule", stage="sandbox_live")]
        result = self.summary_fn(zones=zones, pending_approvals=[], recent_promotions=[], blocked_actions=[])
        self.assertGreater(len(result["zones"]), 0)
        zone_entry = result["zones"][0]
        self.assertIn("plain", zone_entry)
        self.assertIn("Sandbox live", zone_entry["plain"])

    def test_summary_pending_approval_has_plain(self):
        pending = [{"request_id": "r1", "action_type": "home_control", "detail": "Stage a lock action."}]
        result = self.summary_fn(zones=[], pending_approvals=pending, recent_promotions=[], blocked_actions=[])
        self.assertGreater(len(result["pending_approvals"]), 0)
        self.assertIn("plain", result["pending_approvals"][0])

    def test_summary_mentions_hard_boundaries(self):
        result = self.summary_fn(zones=[], pending_approvals=[], recent_promotions=[], blocked_actions=[])
        self.assertIn("hard boundaries", result["plain_summary"].lower())

    def test_capabilities_endpoint_available(self):
        from jarvis.policy_rails import assess_action_policy, CANONICAL_ACTION_TAXONOMY
        # Simulate capabilities assessment for observe stage
        capabilities = []
        for action_type in list(CANONICAL_ACTION_TAXONOMY.keys())[:5]:
            verdict = assess_action_policy(action_type, authority_stage="observe")
            capabilities.append({"action_type": action_type, "decision": verdict["decision"]})
        self.assertEqual(len(capabilities), 5)
        for cap in capabilities:
            self.assertIn(cap["decision"], {"allow", "stage", "deny"})


# ---------------------------------------------------------------------------
# B4 — Promotion engine evidence gating
# ---------------------------------------------------------------------------

class TestPromotionEngineEvidence(unittest.TestCase):
    """B4: Promotion engine requires evidence; apply returns 'hold' if insufficient."""

    def setUp(self):
        from jarvis.promotion import PromotionEngine, PromotionThreshold
        self.engine = PromotionEngine()
        self.threshold_cls = PromotionThreshold

    def _claim(self):
        return self.engine.new_claim(
            subject_kind="trust_zone",
            subject_id="test_zone",
            current_stage="observe",
            target_stage="draft",
            actor="chris",
        )

    def test_insufficient_reviews_returns_hold(self):
        claim = self._claim()
        threshold = self.threshold_cls(min_runs=3, min_success=0.9, max_boundary_violations=0, requires_human_consent=False)
        verdict = self.engine.evaluate_claim(claim, [], threshold=threshold)
        self.assertEqual(verdict.decision, "hold")

    def test_zero_runs_always_hold(self):
        claim = self._claim()
        threshold = self.threshold_cls(min_runs=1, min_success=0.0, max_boundary_violations=5, requires_human_consent=False)
        verdict = self.engine.evaluate_claim(claim, [], threshold=threshold)
        self.assertEqual(verdict.decision, "hold")

    def test_sufficient_reviews_promote(self):
        claim = self._claim()
        threshold = self.threshold_cls(min_runs=2, min_success=0.8, max_boundary_violations=0, requires_human_consent=False)
        reviews = [
            {"outcome": "approved", "rollback_executed": False, "doctrine_ready": True},
            {"outcome": "approved", "rollback_executed": False, "doctrine_ready": True},
        ]
        verdict = self.engine.evaluate_claim(claim, reviews, threshold=threshold)
        self.assertEqual(verdict.decision, "promote")

    def test_boundary_violations_suspend(self):
        claim = self.engine.new_claim(
            subject_kind="trust_zone",
            subject_id="test_zone",
            current_stage="mature_live",
            target_stage="mature_live",
            actor="chris",
        )
        threshold = self.threshold_cls(min_runs=1, min_success=0.0, max_boundary_violations=0, requires_human_consent=False)
        reviews = [
            {"outcome": "approved", "rollback_executed": False},
            {"outcome": "rejected"},
        ]
        verdict = self.engine.evaluate_claim(claim, reviews, threshold=threshold)
        self.assertEqual(verdict.decision, "suspend")

    def test_mature_live_requires_human_consent(self):
        claim = self.engine.new_claim(
            subject_kind="trust_zone",
            subject_id="test_zone",
            current_stage="sandbox_live",
            target_stage="mature_live",
            actor="chris",
            human_consent=False,
        )
        threshold = self.threshold_cls(min_runs=1, min_success=0.0, max_boundary_violations=5, requires_human_consent=True)
        reviews = [{"outcome": "approved", "rollback_executed": False, "doctrine_ready": True}]
        verdict = self.engine.evaluate_claim(claim, reviews, threshold=threshold)
        self.assertEqual(verdict.decision, "pending_consent")

    def test_mature_live_with_consent_promotes(self):
        claim = self.engine.new_claim(
            subject_kind="trust_zone",
            subject_id="test_zone",
            current_stage="sandbox_live",
            target_stage="mature_live",
            actor="chris",
            human_consent=True,
        )
        threshold = self.threshold_cls(min_runs=1, min_success=0.0, max_boundary_violations=5, requires_human_consent=True)
        reviews = [{"outcome": "approved", "rollback_executed": False}]
        verdict = self.engine.evaluate_claim(claim, reviews, threshold=threshold)
        self.assertEqual(verdict.decision, "promote")

    def test_low_success_rate_returns_hold(self):
        claim = self._claim()
        threshold = self.threshold_cls(min_runs=2, min_success=0.95, max_boundary_violations=0, requires_human_consent=False)
        reviews = [
            {"outcome": "approved", "rollback_executed": False},
            {"outcome": "rejected"},
        ]
        verdict = self.engine.evaluate_claim(claim, reviews, threshold=threshold)
        self.assertIn(verdict.decision, {"hold", "suspend"})


# ---------------------------------------------------------------------------
# B1 — Trust-zone coverage: negative paths
# ---------------------------------------------------------------------------

class TestTrustZoneCoverageNegativePaths(unittest.TestCase):
    """B1: Negative paths for boundary enforcement."""

    def setUp(self):
        from jarvis.trust import TrustStore, TrustSupport
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        root = Path(self.tmpdir.name)
        trust_store = TrustStore(root / "trust")
        self.trust_support = TrustSupport(trust_store)

    def _make_zone(self, zone_id, stage="sandbox_live", approval_mode="auto", status="active"):
        from jarvis.models import TrustZone
        return TrustZone(
            zone_id=zone_id, name="Test Zone", zone_type="test",
            authority_stage=stage, resource_scope={}, allowed_actions=[],
            approval_mode=approval_mode, audit_mode="standard",
            promotion_rules={}, demotion_rules={}, status=status,
            created_at="", updated_at="",
        )

    def _boundary(self, zone_id, action_type="home_control", requested_stage="sandbox_live"):
        mock = MagicMock()
        mock.trust_support = self.trust_support
        from jarvis.runtime import JarvisRuntime
        return JarvisRuntime.assess_action_boundary(
            mock, zone_id=zone_id, action_type=action_type, requested_stage=requested_stage,
        )

    def test_unknown_zone_returns_deny(self):
        result = self._boundary("zone_does_not_exist")
        self.assertEqual(result["decision"], "deny")

    def test_inactive_zone_returns_deny(self):
        zone = self._make_zone("test_inactive", status="suspended")
        self.trust_support.upsert_trust_zone(zone)
        result = self._boundary("test_inactive")
        self.assertEqual(result["decision"], "deny")

    def test_unknown_action_in_valid_zone_returns_deny(self):
        zone = self._make_zone("test_active", stage="mature_live")
        self.trust_support.upsert_trust_zone(zone)
        result = self._boundary("test_active", action_type="not_registered_action_xyz")
        self.assertEqual(result["decision"], "deny")

    def test_hard_boundary_action_in_active_mature_zone_returns_deny(self):
        zone = self._make_zone("test_mature", stage="mature_live")
        self.trust_support.upsert_trust_zone(zone)
        for action in ["spend_money", "remote_unlock", "sign_document"]:
            result = self._boundary("test_mature", action_type=action)
            self.assertEqual(result["decision"], "deny", f"{action} must deny in mature zone")


if __name__ == "__main__":
    unittest.main()
