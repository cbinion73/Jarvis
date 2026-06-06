from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jarvis.approvals import ApprovalQueue, ApprovalRequest, RiskTier
from jarvis.integrations import IntegrationStatus
from jarvis.memory import MemoryStore
from jarvis.models import MemoryEntry, MemoryProfileFact, MemoryProposal
from jarvis.supervision_snapshot import (
    build_supervision_snapshot,
    render_supervision_snapshot_html,
    write_supervision_snapshot,
)


class SupervisionSnapshotTests(unittest.TestCase):
    def test_build_snapshot_collects_real_attention_and_memory_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            approvals_root = tmp_path / "approvals"
            memory_root = tmp_path / "memory"

            old_root = ApprovalQueue.ROOT
            ApprovalQueue.ROOT = approvals_root
            try:
                queue = ApprovalQueue()
                queue.submit(
                    ApprovalRequest(
                        request_id="req-1",
                        agent_id="agent-1",
                        agent_label="Scout",
                        action_type="deploy",
                        title="Approve local rollout",
                        description="Needs confirmation before continuing rollout",
                        payload={"lane": "level9"},
                        risk_tier=RiskTier.HIGH,
                        actor_id="chris",
                        requested_at="2026-06-03T12:00:00+00:00",
                        expires_at="2036-06-03T12:00:00+00:00",
                        status="pending",
                    )
                )
            finally:
                ApprovalQueue.ROOT = old_root

            memory_store = MemoryStore(memory_root)
            memory_store.add_entry(
                MemoryEntry(
                    entry_id="mem-1",
                    memory_type="personal",
                    scope="day",
                    owner="Chris",
                    project="level9",
                    title="Morning oversight note",
                    summary="Need to review queue depth.",
                    tags=["oversight"],
                    sensitivity="internal",
                    approval_status="approved",
                    cloud_excluded=False,
                    encrypted_payload="{}",
                    created_at="2026-06-02T11:00:00+00:00",
                    updated_at="2026-06-02T11:00:00+00:00",
                )
            )
            memory_store.add_proposal(
                MemoryProposal(
                    proposal_id="prop-1",
                    actor="Scout",
                    memory_type="project",
                    scope="lane",
                    owner="Chris",
                    project="level9",
                    title="Queue posture update",
                    summary="Promote the queue from hidden to visible.",
                    tags=["approval-queue"],
                    sensitivity="internal",
                    payload={"state": "proposed"},
                    status="pending",
                    rationale="Needed for observability",
                    created_at="2026-06-02T11:30:00+00:00",
                )
            )
            memory_store.upsert_profile_fact(
                MemoryProfileFact(
                    fact_id="fact-1",
                    subject_user_id="chris",
                    subject_display_name="Chris",
                    lane="level9",
                    title="Prefers inspectable proof",
                    summary="Needs openable proof surfaces.",
                    tags=["doctrine"],
                    source_entry_ids=["mem-1"],
                    confidence="confirmed",
                    status="active",
                    source_type="user-stated",
                    boundary_label="internal",
                    created_at="2026-06-02T11:00:00+00:00",
                    updated_at="2026-06-02T11:00:00+00:00",
                )
            )

            snapshot = build_supervision_snapshot(
                memory_root=memory_root,
                approvals_root=approvals_root,
                integration_statuses=[
                    IntegrationStatus(name="memory-profile", ok=True, detail="loaded"),
                    IntegrationStatus(name="google-workspace", ok=False, detail="token missing"),
                ],
            )

            self.assertEqual(snapshot["memory"]["entry_count"], 1)
            self.assertEqual(len(snapshot["attention_queue"]), 1)
            self.assertEqual(snapshot["attention_queue"][0]["title"], "Approve local rollout")
            self.assertTrue(any(item["kind"] == "integration" for item in snapshot["what_needs_me"]))
            self.assertEqual(snapshot["memory"]["proposal_count"], 1)
            self.assertEqual(snapshot["memory"]["pending_proposals"][0], "Queue posture update")

    def test_render_and_write_snapshot_outputs_openable_report(self) -> None:
        snapshot = {
            "generated_at": "2026-06-02T12:00:00+00:00",
            "lane": {
                "branch": "codex/test",
                "head": "abc1234",
                "dirty_count": 2,
                "recent_commits": ["abc1234 Add proof surface"],
                "dirty_sample": [" M jarvis/foo.py"],
            },
            "return_brief": {"summary": "1 approval pending", "what_needs_me_count": 1},
            "attention_queue": [{"request_id": "req-1", "title": "Approve local rollout", "why_now": "Queue needs review"}],
            "memory": {
                "entry_count": 2,
                "proposal_count": 1,
                "fact_count": 1,
                "latest_entry_titles": ["Morning oversight note"],
                "pending_proposals": ["Queue posture update"],
            },
            "registry": {"agent_count": 4, "domains": ["health"], "authority_stages": ["observe"]},
            "integrations": [{"name": "memory-profile", "ok": True, "detail": "loaded"}],
            "what_needs_me": [{"title": "Approve local rollout", "detail": "high request", "kind": "approval"}],
            "proof_paths": {"generated_html": "out.html", "generated_json": "out.json"},
        }

        html = render_supervision_snapshot_html(snapshot)
        self.assertIn("JARVIS Supervision Snapshot", html)
        self.assertIn("Return Brief", html)
        self.assertIn("What Needs Me", html)
        self.assertIn("Attention Queue", html)
        self.assertIn("Memory Inspector", html)
        self.assertIn("Open Approval Queue", html)
        self.assertIn('/api/approvals/req-1/approve', html)
        self.assertIn("/api/supervision-snapshot", html)
        self.assertIn("Raw Snapshot JSON", html)

        with tempfile.TemporaryDirectory() as tmp:
            html_path = Path(tmp) / "snapshot.html"
            json_path = Path(tmp) / "snapshot.json"
            outputs = write_supervision_snapshot(snapshot, html_output=html_path, json_output=json_path)
            self.assertEqual(outputs["html"], str(html_path))
            self.assertTrue(html_path.exists())
            self.assertTrue(json_path.exists())
            self.assertIn("Approve local rollout", html_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
