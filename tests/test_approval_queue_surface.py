from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path

from jarvis.approvals import ApprovalQueue, ApprovalRequest, RiskTier
from jarvis.approval_queue_surface import (
    build_approval_queue_snapshot,
    render_approval_queue_html,
    write_approval_queue_snapshot,
)
from scripts.manage_approval_queue import main as approval_queue_main


class ApprovalQueueSurfaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name) / "approvals"
        self.previous_root = ApprovalQueue.ROOT
        ApprovalQueue.ROOT = self.root

    def tearDown(self) -> None:
        ApprovalQueue.ROOT = self.previous_root
        self.temp_dir.cleanup()

    def _request(self, request_id: str, *, title: str, status: str = "pending") -> ApprovalRequest:
        requested_at = datetime.now(timezone.utc) - timedelta(hours=1)
        expires_at = requested_at + timedelta(days=2)
        return ApprovalRequest(
            request_id=request_id,
            agent_id="sam",
            agent_label="Sam Wilson",
            action_type="calendar_change",
            title=title,
            description=f"{title} for Chris",
            payload={"calendar_id": "family"},
            risk_tier=RiskTier.MEDIUM,
            actor_id="chris",
            requested_at=requested_at.isoformat(),
            expires_at=expires_at.isoformat(),
            status=status,
            priority=2,
            tags=["calendar", "family"],
            trust_zone_id="household_schedule",
            lane_id="daily-life",
            arena_id="household.schedule.routing",
            requested_outcome="Reschedule the pediatrician visit",
            supervision_decision={"resolution": "stage", "approval_required": True},
        )

    def _seed_queue(self) -> None:
        queue = ApprovalQueue()
        queue.submit(self._request("pending-1", title="Move pediatrician visit"))
        queue.submit(self._request("pending-2", title="Send school delay note"))
        queue.submit(self._request("done-1", title="Cancel dentist check-in"))
        self.assertTrue(queue.reject("done-1", reason="Need Chris to confirm timing", rejected_by="chris"))

        queue.submit(self._request("done-2", title="Approve garage service"))
        approved = queue.approve("done-2", approved_by="chris")
        self.assertIsNotNone(approved)
        self.assertTrue(queue.mark_executed("done-2"))

    def test_snapshot_captures_pending_history_and_action_hints(self) -> None:
        self._seed_queue()

        snapshot = build_approval_queue_snapshot(approvals_root=self.root)

        self.assertEqual(snapshot["pending_count"], 2)
        self.assertEqual(snapshot["history_count"], 2)
        self.assertEqual(snapshot["what_needs_me"][0]["title"], "Move pediatrician visit")
        self.assertIn("scripts/manage_approval_queue.py approve pending-1", snapshot["pending"][0]["commands"]["approve"])
        self.assertEqual(snapshot["history"][0]["status"], "executed")

    def test_html_render_exposes_operator_commands_and_history(self) -> None:
        self._seed_queue()
        snapshot = build_approval_queue_snapshot(approvals_root=self.root)

        html = render_approval_queue_html(snapshot)

        self.assertIn("JARVIS Approval Queue", html)
        self.assertIn("Needs Me Now", html)
        self.assertIn("python3 scripts/manage_approval_queue.py approve pending-1", html)
        self.assertIn('/api/approvals/pending-1/approve', html)
        self.assertIn("Open this through the app for live actions", html)
        self.assertIn("Decision History", html)
        self.assertIn("Move pediatrician visit", html)
        self.assertIn("Approve garage service", html)

    def test_write_snapshot_outputs_html_and_json(self) -> None:
        self._seed_queue()
        snapshot = build_approval_queue_snapshot(approvals_root=self.root)
        html_path = Path(self.temp_dir.name) / "jarvis-approval-queue.html"
        json_path = Path(self.temp_dir.name) / "jarvis-approval-queue.json"

        outputs = write_approval_queue_snapshot(snapshot, html_output=html_path, json_output=json_path)

        self.assertEqual(outputs["html"], str(html_path))
        self.assertEqual(outputs["json"], str(json_path))
        self.assertTrue(html_path.exists())
        self.assertTrue(json_path.exists())
        self.assertIn("JARVIS Approval Queue", html_path.read_text(encoding="utf-8"))
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["pending_count"], 2)

    def test_cli_can_list_approve_execute_and_render(self) -> None:
        queue = ApprovalQueue()
        queue.submit(self._request("pending-1", title="Move pediatrician visit"))

        list_stdout = io.StringIO()
        with redirect_stdout(list_stdout):
            exit_code = approval_queue_main(["--root", str(self.root), "list"])
        self.assertEqual(exit_code, 0)
        listed = json.loads(list_stdout.getvalue())
        self.assertEqual(listed["pending"][0]["request_id"], "pending-1")

        approve_stdout = io.StringIO()
        with redirect_stdout(approve_stdout):
            exit_code = approval_queue_main(["--root", str(self.root), "approve", "pending-1"])
        self.assertEqual(exit_code, 0)
        approved = json.loads(approve_stdout.getvalue())
        self.assertEqual(approved["approved"]["status"], "approved")

        execute_stdout = io.StringIO()
        with redirect_stdout(execute_stdout):
            exit_code = approval_queue_main(["--root", str(self.root), "execute", "pending-1"])
        self.assertEqual(exit_code, 0)
        executed = json.loads(execute_stdout.getvalue())
        self.assertEqual(executed["executed"], "pending-1")

        render_stdout = io.StringIO()
        with redirect_stdout(render_stdout):
            exit_code = approval_queue_main(["--root", str(self.root), "render"])
        self.assertEqual(exit_code, 0)
        rendered = json.loads(render_stdout.getvalue())
        self.assertTrue(Path(rendered["html"]).exists())
        self.assertTrue(Path(rendered["json"]).exists())


if __name__ == "__main__":
    unittest.main()
