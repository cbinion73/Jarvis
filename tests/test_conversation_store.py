from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jarvis.conversation import ConversationStore


class ConversationStoreTests(unittest.TestCase):
    def test_replays_index_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = ConversationStore(root)
            created = store.create("Chris", "office")

            store.index_path.write_text("", encoding="utf-8")
            (root / "index_log.jsonl").write_text("", encoding="utf-8")
            replayed = ConversationStore(root)

            recent = replayed.list_recent()
            self.assertEqual(len(recent), 1)
            self.assertEqual(recent[0]["conversation_id"], created["conversation_id"])

    def test_replays_thread_from_state_log_when_snapshot_is_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = ConversationStore(root)
            created = store.create("Chris", "office")
            conversation_id = created["conversation_id"]
            updated = store.append_turn(
                conversation_id,
                role="user",
                text="Need a family plan for tonight.",
                actor="Chris",
                room="office",
            )
            assert updated is not None

            thread_path = root / f"{conversation_id}.json"
            thread_path.write_text("{broken", encoding="utf-8")
            thread_path.with_suffix(".log.jsonl").write_text("", encoding="utf-8")
            replayed = ConversationStore(root)

            record = replayed.get(conversation_id)
            self.assertIsNotNone(record)
            assert record is not None
            self.assertEqual(record["conversation_id"], conversation_id)
            self.assertEqual(record["turn_count"], 1)
            self.assertEqual(record["latest_user_text"], "Need a family plan for tonight.")


if __name__ == "__main__":
    unittest.main()
