from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jarvis.memory import MemoryStore
from jarvis.models import MemoryEntry, MemoryProfileFact, MemoryProposal


class MemoryStoreTests(unittest.TestCase):
    def test_replays_entries_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = MemoryStore(Path(tmp))
            entry = MemoryEntry(
                entry_id="entry-1",
                memory_type="personal",
                scope="personal",
                owner="Chris",
                project="",
                title="Preferred coffee",
                summary="Likes pour over coffee in the morning.",
                tags=["coffee"],
                sensitivity="low",
                approval_status="approved",
                cloud_excluded=False,
                encrypted_payload="ciphertext",
                created_at="2026-06-02T10:00:00Z",
                updated_at="2026-06-02T10:00:00Z",
            )

            saved = store.add_entry(entry)
            store.entries_path.write_text("", encoding="utf-8")
            store._log_path(store.entries_path).write_text("", encoding="utf-8")
            loaded = store.list_entries()

            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0]["entry_id"], saved["entry_id"])
            self.assertEqual(loaded[0]["title"], "Preferred coffee")

    def test_replays_proposals_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = MemoryStore(Path(tmp))
            proposal = MemoryProposal(
                proposal_id="proposal-1",
                actor="jarvis",
                memory_type="project",
                scope="project",
                owner="Chris",
                project="JARVIS",
                title="Capture roadmap preference",
                summary="Prefers small stacked checkpoints.",
                tags=["roadmap"],
                sensitivity="low",
                payload={"note": "stacked branches"},
                status="pending",
                rationale="Repeated request pattern",
                created_at="2026-06-02T10:05:00Z",
            )

            saved = store.add_proposal(proposal)
            store.proposals_path.write_text("", encoding="utf-8")
            store._log_path(store.proposals_path).write_text("", encoding="utf-8")
            loaded = store.list_proposals()

            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0]["proposal_id"], saved["proposal_id"])
            self.assertEqual(loaded[0]["payload"]["note"], "stacked branches")

    def test_replays_profile_facts_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = MemoryStore(Path(tmp))
            fact = MemoryProfileFact(
                fact_id="fact-1",
                subject_user_id="chris",
                subject_display_name="Chris",
                lane="preferences",
                title="Morning briefing style",
                summary="Prefers fast high-signal summaries.",
                tags=["briefing"],
                source_entry_ids=["entry-1"],
                confidence="confirmed",
                status="active",
                source_type="user-stated",
                boundary_label="",
                created_at="2026-06-02T10:10:00Z",
                updated_at="2026-06-02T10:10:00Z",
            )

            saved = store.upsert_profile_fact(fact)
            store.facts_path.write_text("", encoding="utf-8")
            store._log_path(store.facts_path).write_text("", encoding="utf-8")
            loaded = store.list_profile_facts()

            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0]["fact_id"], saved["fact_id"])
            self.assertEqual(loaded[0]["summary"], "Prefers fast high-signal summaries.")


if __name__ == "__main__":
    unittest.main()
