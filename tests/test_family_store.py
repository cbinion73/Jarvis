from __future__ import annotations

import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

from jarvis.family import FamilyStore
from jarvis.models import MessageDraft, ModeState


class FamilyStoreTests(unittest.TestCase):
    def test_replays_mode_state_from_history_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = FamilyStore(root)
            mode_state = ModeState(
                mode="focus",
                status="manual",
                reason="School-night transition",
                actor="Chris",
                timestamp="2026-06-02T00:00:00+00:00",
            )

            store.save_mode_state(mode_state)
            store.mode_state_path.write_text("", encoding="utf-8")

            self.assertEqual(store.load_mode_state(), asdict(mode_state))

    def test_replays_mode_state_from_history_log_when_history_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = FamilyStore(root)
            mode_state = ModeState(
                mode="focus",
                status="manual",
                reason="School-night transition",
                actor="Chris",
                timestamp="2026-06-02T00:00:00+00:00",
            )

            store.save_mode_state(mode_state)
            store.mode_state_path.write_text("", encoding="utf-8")
            store.mode_history_path.write_text("", encoding="utf-8")

            self.assertEqual(store.load_mode_state(), asdict(mode_state))

    def test_replays_message_drafts_from_append_log_when_snapshot_is_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = FamilyStore(root)
            draft = MessageDraft(
                draft_id="draft-1",
                actor="Chris",
                audience="family",
                purpose="coordination",
                tone="warm",
                context="Dinner update",
                body="Dinner is at 6:30.",
                status="draft",
                timestamp="2026-06-02T00:00:00+00:00",
            )

            store.add_draft(draft)
            store.message_drafts_path.write_text("{broken", encoding="utf-8")

            self.assertEqual(store.list_drafts(), [asdict(draft)])


if __name__ == "__main__":
    unittest.main()
