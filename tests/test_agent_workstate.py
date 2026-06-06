from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jarvis.agentic import AgentRegistry
from jarvis.missions import MissionStore, MissionSupport


class _StubTrustSupport:
    def __init__(self) -> None:
        self._zones: dict[str, dict] = {}

    def get_trust_zone(self, zone_id: str) -> dict | None:
        return self._zones.get(zone_id)

    def upsert_trust_zone(self, zone) -> None:
        self._zones[zone.zone_id] = {"zone_id": zone.zone_id, "created_at": getattr(zone, "created_at", ""), "updated_at": getattr(zone, "updated_at", "")}


class _StubApprovalStore:
    def list_all(self) -> list[dict]:
        return []

    def save(self, approval) -> None:
        return None


class AgentWorkStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        root = Path(self.tmpdir.name)
        self.support = MissionSupport(
            MissionStore(root / "missions"),
            trust_support=_StubTrustSupport(),
            approval_store=_StubApprovalStore(),
            agent_registry=AgentRegistry(),
        )

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_create_mission_bootstraps_agent_workspaces(self) -> None:
        dossier = self.support.create_mission(
            actor="Chris",
            room="office",
            request="Plan tomorrow's family weather and inbox posture.",
            memory_snapshot={"active_mode": {"mode": "day", "status": "active", "reason": "test"}},
        )

        work_states = dossier["agent_work_states"]
        self.assertTrue(work_states)
        self.assertIn("ambient-router", work_states)
        lead = work_states["ambient-router"]
        self.assertEqual(lead["ownership_mode"], "lead")
        self.assertGreaterEqual(len(lead["active_tasks"]), 1)
        self.assertGreaterEqual(len(lead["recent_decisions"]), 1)

        supporting_agents = [state for agent_id, state in work_states.items() if agent_id != "ambient-router"]
        self.assertTrue(any(len(state["pending_reviews"]) >= 1 for state in supporting_agents))

    def test_handoff_requires_ack_for_ownership_transfer(self) -> None:
        dossier = self.support.create_mission(
            actor="Chris",
            room="office",
            request="Organize the family project and compare next steps together.",
        )
        mission_id = dossier["mission_id"]
        selected_agents = dossier["selected_agents"]
        from_agent = selected_agents[0]
        to_agent = selected_agents[1]

        updated = self.support.create_agent_handoff(
            mission_id,
            from_agent=from_agent,
            to_agent=to_agent,
            task_title="Own the next planning pass",
            summary="Take over sequencing and keep the current partial work intact.",
            partial_work="Lead agent already framed the mission and gathered first-pass context.",
            transfer_ownership=True,
        )

        transfer = updated["ownership_transfers"][0]
        self.assertEqual(transfer["status"], "pending-acceptance")
        blocked = updated["agent_work_states"][from_agent]["blocked_tasks"]
        self.assertTrue(any(item["status"] == "awaiting-transfer-acceptance" for item in blocked))

        acknowledged = self.support.acknowledge_agent_handoff(
            mission_id,
            updated["handoffs"][0]["handoff_id"],
            receiving_agent=to_agent,
            accepted=True,
            note="I can take this over cleanly.",
        )

        accepted_transfer = acknowledged["ownership_transfers"][0]
        self.assertEqual(accepted_transfer["status"], "accepted")
        self.assertTrue(accepted_transfer["safe_to_release"])
        self.assertEqual(acknowledged["agent_work_states"][to_agent]["ownership_mode"], "lead")
        self.assertFalse(acknowledged["agent_work_states"][from_agent]["blocked_tasks"])

    def test_duplicate_suppression_and_summary_counts_are_durable(self) -> None:
        dossier = self.support.create_mission(
            actor="Chris",
            room="office",
            request="Build a workshop project together and keep ownership clear.",
        )
        mission_id = dossier["mission_id"]
        selected_agents = dossier["selected_agents"]

        updated = self.support.suppress_duplicate_work(
            mission_id,
            duplicate_key="cad-review-pass",
            winning_agent=selected_agents[0],
            suppressed_agent=selected_agents[1],
            rationale="The lead agent already owns this review lane, so the supporting lane should stand down.",
            task_title="CAD review pass",
            task_id="task-cad-review",
        )

        self.assertEqual(len(updated["duplicate_suppressions"]), 1)
        blocked = updated["agent_work_states"][selected_agents[1]]["blocked_tasks"]
        self.assertTrue(any(item["status"] == "suppressed-duplicate" for item in blocked))

        summary = self.support.mission_work_state(mission_id)["summary"]
        self.assertGreaterEqual(summary["blocked_tasks"], 1)
        self.assertEqual(summary["duplicate_suppressions"], 1)

    def test_mission_control_summary_includes_agent_society_health(self) -> None:
        dossier = self.support.create_mission(
            actor="Chris",
            room="office",
            request="Plan tomorrow's family weather, inbox posture, and delegated follow-through.",
        )
        mission_id = dossier["mission_id"]
        selected_agents = dossier["selected_agents"]
        lead_agent = selected_agents[0]
        support_agent = selected_agents[1]

        updated = self.support.create_agent_handoff(
            mission_id,
            from_agent=lead_agent,
            to_agent=support_agent,
            task_title="Own the next delegated review",
            summary="Take over a bounded follow-through review and keep the current framing intact.",
            partial_work="Lead agent already framed the mission and captured first-pass evidence.",
            transfer_ownership=True,
        )

        control = self.support.mission_control_summary(actor="Chris", limit=12)
        society = dict(control.get("agent_society") or {})
        society_summary = dict(society.get("summary") or {})
        agent_rows = list(society.get("agents") or [])
        lane_rows = list(society.get("lanes") or [])

        self.assertGreaterEqual(society_summary.get("active_agents", 0), 2)
        self.assertGreaterEqual(society_summary.get("blocked_agents", 0), 1)
        self.assertGreaterEqual(society_summary.get("pending_review_agents", 0), 1)
        self.assertTrue(any(item.get("agent_id") == lead_agent for item in agent_rows))
        self.assertTrue(any(int(item.get("blocked_tasks", 0) or 0) > 0 for item in agent_rows))
        self.assertTrue(any(int(item.get("pending_reviews", 0) or 0) > 0 for item in agent_rows))
        self.assertTrue(any(item.get("lane_id") for item in lane_rows))
        self.assertEqual(updated["mission_id"], mission_id)


if __name__ == "__main__":
    unittest.main()
