from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jarvis.audit import AuditLog
from jarvis.doctrine import SharedDoctrineStore
from jarvis.supervision import SupervisionStore, SupervisionSupport
from jarvis.trust import TrustStore, TrustSupport


class SupervisionPlaneTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.trust_support = TrustSupport(TrustStore(root / "trust"), default_owner_principal="chris")
        self.doctrine_store = SharedDoctrineStore(root / "settings" / "shared_doctrine.json")
        self.audit_log = AuditLog(root / "logs")
        self.support = SupervisionSupport(
            SupervisionStore(root / "supervision"),
            trust_support=self.trust_support,
            doctrine_store=self.doctrine_store,
            audit_log=self.audit_log,
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_stage_alert_actions_do_not_bypass_review(self) -> None:
        decision = self.support.evaluate_action(
            agent_id="watcher",
            action_type="notification_workflow",
            requested_outcome="quietly close a notification",
            trust_zone_id="household_attention",
            context={"touches_external_state": True, "reversible": True},
        )
        self.assertEqual(decision["resolution"], "stage")
        self.assertTrue(decision["approval_required"])
        self.assertFalse(decision["sandbox_required"])

    def test_sandbox_live_contracts_require_sandbox_for_bounded_live_actions(self) -> None:
        decision = self.support.evaluate_action(
            agent_id="pepper",
            action_type="calendar_route",
            requested_outcome="reroute today's pickup",
            trust_zone_id="household_schedule",
            context={"touches_external_state": True, "reversible": True},
        )
        self.assertEqual(decision["resolution"], "sandbox")
        self.assertTrue(decision["sandbox_required"])
        self.assertEqual(decision["rollback_posture"], "reversible")

    def test_cross_zone_work_escalates_even_for_known_agent(self) -> None:
        decision = self.support.evaluate_action(
            agent_id="system-steward",
            action_type="huddle_workflow",
            requested_outcome="wake a new council and modify another lane",
            trust_zone_id="household_huddle",
            context={"cross_zone": True, "touches_external_state": True, "reversible": False},
        )
        self.assertEqual(decision["resolution"], "escalate")
        self.assertTrue(decision["approval_required"])
        self.assertTrue(decision["escalation_required"])

    def test_reviewed_success_synthesizes_supervision_doctrine_candidate(self) -> None:
        for index in range(3):
            decision = self.support.evaluate_action(
                agent_id="pepper",
                action_type="calendar_route",
                requested_outcome=f"reroute family logistics #{index}",
                trust_zone_id="household_schedule",
                context={"touches_external_state": True, "reversible": True},
            )
            self.support.record_review(
                decision_id=str(decision["decision_id"]),
                reviewer="chris",
                outcome="approved",
                notes="reviewed success",
                rollback_executed=False,
                doctrine_ready=True,
            )

        result = self.support.refresh_doctrine_candidates(synthesized_by="test-suite")
        self.assertEqual(result["candidate_count"], 1)
        self.assertEqual(result["candidates"][0]["source"], "supervision")
        self.assertEqual(
            result["candidates"][0]["policy_effects"]["action_type"],
            "calendar_route",
        )

    def test_promotion_evidence_can_be_collected_by_trust_zone(self) -> None:
        decision = self.support.evaluate_action(
            agent_id="pepper",
            action_type="calendar_route",
            requested_outcome="reroute family logistics",
            trust_zone_id="household_schedule",
            arena_id="household.schedule.routing",
            context={"touches_external_state": True, "reversible": True},
        )
        self.support.record_review(
            decision_id=str(decision["decision_id"]),
            reviewer="chris",
            outcome="approved",
            notes="reviewed success",
            rollback_executed=False,
            doctrine_ready=True,
        )

        evidence = self.support.promotion_evidence(
            subject_kind="trust_zone",
            subject_id="household_schedule",
        )

        self.assertEqual(evidence["summary"]["review_count"], 1)
        self.assertEqual(evidence["summary"]["approved_count"], 1)
        self.assertEqual(evidence["reviews"][0]["arena_id"], "household.schedule.routing")


if __name__ == "__main__":
    unittest.main()
