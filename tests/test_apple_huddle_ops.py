from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from jarvis.apple_api import _record_huddle_progress_focus, _resolve_huddle_approval
from jarvis.audit import AuditLog, ProgressFocusStore


class _StubWorkItem:
    def __init__(self, work_id: str, title: str, status: str = "proposed") -> None:
        self.work_id = work_id
        self.title = title
        self.status = status
        self.request = title


class _StubWorkStore:
    def __init__(self, item: _StubWorkItem) -> None:
        self._item = item

    def get(self, work_id: str) -> _StubWorkItem | None:
        return self._item if self._item.work_id == work_id else None

    def mark_approved(self, work_id: str, approved_by: str = "Chris") -> None:
        if self._item.work_id == work_id:
            self._item.status = "approved"

    def mark_rejected(self, work_id: str, reason: str = "") -> None:
        if self._item.work_id == work_id:
            self._item.status = "rejected"


class AppleHuddleOpsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._cwd = Path.cwd()
        self._tmpdir = tempfile.TemporaryDirectory()
        os.chdir(self._tmpdir.name)

    def tearDown(self) -> None:
        os.chdir(self._cwd)
        self._tmpdir.cleanup()

    def test_huddle_focus_record_persists_progress_and_activity(self) -> None:
        focus = _record_huddle_progress_focus(
            actor="chris",
            action="Start Huddle Party Mode",
            detail="Huddle launched the overnight research cycle from the native alignment lane.",
            why_now="The native Huddle screen started a real overnight orchestration loop.",
            result_summary="Party mode started from the phone Huddle lane.",
            related_kind="party-mode",
            related_label="Overnight Orchestration",
        )

        self.assertEqual(focus["module"], "Huddle")
        summary = ProgressFocusStore(Path("data/logs")).summary(limit=3)
        self.assertEqual(summary["latest"]["module"], "Huddle")

        recent = AuditLog(Path("data/logs")).list_recent(limit=3, entry_type="operator-action")
        self.assertEqual(recent[0]["action"], "Start Huddle Party Mode")
        self.assertEqual(recent[0]["related_label"], "Overnight Orchestration")

    def test_resolve_huddle_approval_updates_focus_and_activity(self) -> None:
        from unittest.mock import patch

        item = _StubWorkItem("work-1", "Approve marketing budget")
        store = _StubWorkStore(item)

        with patch("jarvis.agent_work.get_all_stores", return_value={"ops": store}):
            approved = _resolve_huddle_approval(work_id="work-1", action="approve", actor="chris")
            rejected = _resolve_huddle_approval(
                work_id="work-1",
                action="reject",
                actor="chris",
                note="Needs one more round of review.",
            )

        self.assertEqual(approved["status"], "approved")
        self.assertEqual(rejected["status"], "rejected")

        summary = ProgressFocusStore(Path("data/logs")).summary(limit=5)
        self.assertEqual(summary["latest"]["module"], "Huddle")

        recent = AuditLog(Path("data/logs")).list_recent(limit=5, entry_type="operator-action")
        titles = [item.get("action") for item in recent]
        self.assertIn("Approve Huddle Decision", titles)
        self.assertIn("Reject Huddle Decision", titles)


if __name__ == "__main__":
    unittest.main()
