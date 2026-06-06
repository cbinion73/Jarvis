from __future__ import annotations

import sys
import tempfile
import types
import unittest
from pathlib import Path

from jarvis.promotion import PromotionEngine
from jarvis.audit import AuditLog
from jarvis.doctrine import SharedDoctrineStore
from jarvis.supervision import SupervisionStore, SupervisionSupport
from jarvis.trust import TrustStore, TrustSupport


if "langgraph.graph" not in sys.modules:
    langgraph_module = types.ModuleType("langgraph")
    graph_module = types.ModuleType("langgraph.graph")

    class _StubStateGraph:
        def __init__(self, *_args, **_kwargs) -> None:
            self._nodes: dict[str, object] = {}

        def add_node(self, name: str, fn: object) -> None:
            self._nodes[name] = fn

        def add_edge(self, *_args, **_kwargs) -> None:
            return None

        def compile(self):
            class _Compiled:
                def invoke(self, state):
                    return state

            return _Compiled()

    graph_module.END = "END"
    graph_module.START = "START"
    graph_module.StateGraph = _StubStateGraph
    langgraph_module.graph = graph_module
    sys.modules["langgraph"] = langgraph_module
    sys.modules["langgraph.graph"] = graph_module

from jarvis.runtime import JarvisRuntime


class PromotionEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = PromotionEngine()

    def test_mature_live_requires_explicit_human_consent_after_track_record(self) -> None:
        stage = {
            "stage_id": "mature_live",
            "promotion_criteria": {
                "minimum_review_count": 5,
                "minimum_success_rate": 0.9,
                "maximum_boundary_violations": 0,
            },
        }
        claim = self.engine.new_claim(
            subject_kind="trust_zone",
            subject_id="household_schedule",
            current_stage="sandbox_live",
            target_stage="mature_live",
            actor="chris",
            trust_zone="household_schedule",
            human_consent=False,
        )
        reviews = [
            {"outcome": "approved", "rollback_executed": False, "doctrine_ready": True}
            for _ in range(5)
        ]

        verdict = self.engine.evaluate_claim(
            claim,
            reviews,
            threshold=self.engine.threshold_from_stage(stage),
        )

        self.assertEqual(verdict.decision, "pending_consent")
        self.assertTrue(verdict.human_consent_required)
        self.assertFalse(verdict.human_consent_present)

    def test_boundary_violations_hold_promotion_before_consent_gate(self) -> None:
        stage = {
            "stage_id": "sandbox_live",
            "promotion_criteria": {
                "minimum_review_count": 3,
                "minimum_success_rate": 0.9,
                "maximum_boundary_violations": 0,
            },
        }
        claim = self.engine.new_claim(
            subject_kind="agent",
            subject_id="pepper",
            current_stage="stage_alert",
            target_stage="sandbox_live",
            actor="system-steward",
        )
        reviews = [
            {"outcome": "approved", "rollback_executed": False},
            {"outcome": "approved", "rollback_executed": True},
            {"outcome": "rejected", "rollback_executed": False},
        ]

        verdict = self.engine.evaluate_claim(
            claim,
            reviews,
            threshold=self.engine.threshold_from_stage(stage),
        )

        self.assertEqual(verdict.decision, "hold")
        self.assertGreater(verdict.metrics["boundary_violations"], 0)

    def test_clean_track_record_promotes_without_extra_gate(self) -> None:
        stage = {
            "stage_id": "sandbox_live",
            "promotion_criteria": {
                "minimum_review_count": 3,
                "minimum_success_rate": 0.9,
                "maximum_boundary_violations": 0,
            },
        }
        claim = self.engine.new_claim(
            subject_kind="resource_arena",
            subject_id="household.schedule.routing",
            current_stage="stage_alert",
            target_stage="sandbox_live",
            actor="system-steward",
        )
        reviews = [
            {"outcome": "approved", "rollback_executed": False},
            {"outcome": "approved", "rollback_executed": False},
            {"outcome": "approved", "rollback_executed": False},
        ]

        verdict = self.engine.evaluate_claim(
            claim,
            reviews,
            threshold=self.engine.threshold_from_stage(stage),
        )

        self.assertEqual(verdict.decision, "promote")
        self.assertEqual(verdict.metrics["boundary_violations"], 0)


class PromotionApplicationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.trust_support = TrustSupport(TrustStore(root / "trust"), default_owner_principal="chris")
        self.doctrine_store = SharedDoctrineStore(root / "settings" / "shared_doctrine.json")
        self.audit_log = AuditLog(root / "logs")
        self.supervision_support = SupervisionSupport(
            SupervisionStore(root / "supervision"),
            trust_support=self.trust_support,
            doctrine_store=self.doctrine_store,
            audit_log=self.audit_log,
        )
        stages = self.trust_support.store.list_authority_stages()
        for item in stages:
            if not isinstance(item, dict):
                continue
            stage_id = str(item.get("stage_id") or "").strip()
            criteria = dict(item.get("promotion_criteria") or {})
            if stage_id == "sandbox_live":
                criteria["minimum_review_count"] = 3
                criteria["minimum_success_rate"] = 0.9
            elif stage_id == "mature_live":
                criteria["minimum_review_count"] = 5
                criteria["minimum_success_rate"] = 0.9
            item["promotion_criteria"] = criteria
        self.trust_support.store.save_authority_stages(stages)
        self.runtime = object.__new__(JarvisRuntime)
        self.runtime.trust_support = self.trust_support
        self.runtime.supervision_support = self.supervision_support

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _record_review(
        self,
        *,
        agent_id: str,
        trust_zone_id: str,
        action_type: str,
        arena_id: str,
        outcome: str = "approved",
        rollback_executed: bool = False,
    ) -> None:
        decision = self.supervision_support.evaluate_action(
            agent_id=agent_id,
            action_type=action_type,
            requested_outcome=f"{action_type} outcome",
            trust_zone_id=trust_zone_id,
            arena_id=arena_id,
            context={"touches_external_state": True, "reversible": True},
        )
        self.supervision_support.record_review(
            decision_id=str(decision["decision_id"]),
            reviewer="chris",
            outcome=outcome,
            notes="reviewed in test",
            rollback_executed=rollback_executed,
            doctrine_ready=True,
        )

    def test_apply_promotion_promotes_trust_zone_when_evidence_is_clean(self) -> None:
        for _ in range(5):
            self._record_review(
                agent_id="pepper",
                trust_zone_id="household_schedule",
                action_type="calendar_route",
                arena_id="household.schedule.routing",
            )

        result = self.runtime.apply_promotion_decision(
            subject_kind="trust_zone",
            subject_id="household_schedule",
            target_stage="mature_live",
            actor="system-steward",
            basis="test-apply",
            human_consent=True,
        )

        self.assertTrue(result["applied"])
        self.assertEqual(result["updated"]["authority_stage"], "mature_live")
        self.assertEqual(self.trust_support.get_trust_zone("household_schedule")["authority_stage"], "mature_live")

    def test_apply_promotion_requires_consent_for_mature_live(self) -> None:
        for _ in range(5):
            self._record_review(
                agent_id="pepper",
                trust_zone_id="household_schedule",
                action_type="calendar_route",
                arena_id="household.schedule.routing",
            )

        with self.assertRaises(PermissionError):
            self.runtime.apply_promotion_decision(
                subject_kind="trust_zone",
                subject_id="household_schedule",
                target_stage="mature_live",
                actor="system-steward",
                basis="test-no-consent",
                human_consent=False,
            )

    def test_apply_promotion_advances_agent_contract_stage(self) -> None:
        for _ in range(3):
            self._record_review(
                agent_id="watcher",
                trust_zone_id="household_attention",
                action_type="notification_workflow",
                arena_id="household.attention.workflow",
            )

        result = self.runtime.apply_promotion_decision(
            subject_kind="agent",
            subject_id="watcher",
            target_stage="sandbox_live",
            actor="system-steward",
            basis="test-agent-apply",
        )

        self.assertTrue(result["applied"])
        self.assertEqual(result["updated"]["authority_stage"], "sandbox_live")
        self.assertEqual(self.supervision_support.get_contract("watcher")["authority_stage"], "sandbox_live")

    def test_batch_apply_skips_pending_consent_and_applies_safe_agent_promotion(self) -> None:
        for _ in range(5):
            self._record_review(
                agent_id="pepper",
                trust_zone_id="household_schedule",
                action_type="calendar_route",
                arena_id="household.schedule.routing",
            )
        for _ in range(3):
            self._record_review(
                agent_id="watcher",
                trust_zone_id="household_attention",
                action_type="notification_workflow",
                arena_id="household.attention.workflow",
            )

        result = self.runtime.apply_promotion_recommendations(limit=10)

        self.assertGreaterEqual(result["applied_count"], 1)
        self.assertTrue(
            any(item["subject_kind"] == "agent" and item["subject_id"] == "watcher" for item in result["applied"])
        )
        self.assertTrue(
            any(item["subject_kind"] == "trust_zone" and item["subject_id"] == "household_schedule" for item in result["skipped"])
        )


if __name__ == "__main__":
    unittest.main()
