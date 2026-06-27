from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jarvis.assistant_core import AssistantCoreStore


class AssistantCoreStoreTests(unittest.TestCase):
    def test_read_only_store_keeps_service_runtime_state_in_memory_without_writing_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "assistant_core.json"
            store = AssistantCoreStore(path=path, read_only=True)

            saved = store.save_service_runtime(
                "runtime",
                {
                    "pid": 1234,
                    "cwd": "/tmp/jarvis-smoke",
                },
            )

            state = store.load()
            self.assertEqual(saved["pid"], 1234)
            self.assertEqual(state["service_runtime"]["runtime"]["pid"], 1234)
            self.assertFalse(path.exists())
            self.assertFalse(store.log_path.exists())
            self.assertFalse(store.state_log_path.exists())

    def test_replays_assistant_core_state_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "assistant_core.json"
            store = AssistantCoreStore(path=path)

            deferred = store.set_deferred(
                "task-1",
                until="2026-06-03T09:00:00+00:00",
                actor="Chris",
                reason="Waiting on external input",
            )

            path.write_text("", encoding="utf-8")
            store.log_path.write_text("", encoding="utf-8")
            replayed = AssistantCoreStore(path=path)
            record = replayed.deferred_record("task-1")
            state = replayed.load()

            self.assertIsNotNone(record)
            self.assertEqual(record["item_key"], "task-1")
            self.assertEqual(record["reason"], deferred["reason"])
            self.assertEqual(state["history"][-1]["type"], "deferred")
            self.assertEqual(state["deferred"]["task-1"]["actor"], "Chris")


if __name__ == "__main__":
    unittest.main()
