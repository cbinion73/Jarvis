from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jarvis import tasks


class TasksStoreTests(unittest.TestCase):
    def test_replays_tasks_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tasks_path = Path(tmp) / "tasks.json"
            tasks_log_path = Path(tmp) / "tasks_log.jsonl"
            tasks_state_log_path = Path(tmp) / "tasks_state_log.jsonl"

            with (
                patch.object(tasks, "_TASKS_PATH", tasks_path),
                patch.object(tasks, "_TASKS_LOG_PATH", tasks_log_path),
                patch.object(tasks, "_TASKS_STATE_LOG_PATH", tasks_state_log_path),
            ):
                created = tasks.add_task(
                    "Check continuity lane",
                    priority="high",
                    actor="chris",
                    domain="work",
                )

                tasks_path.write_text("", encoding="utf-8")
                listed = tasks.list_tasks()

                self.assertEqual(len(listed), 1)
                self.assertEqual(listed[0]["id"], created["id"])
                self.assertEqual(listed[0]["title"], "Check continuity lane")
                self.assertEqual(listed[0]["priority"], "high")
                self.assertEqual(listed[0]["domain"], "work")


if __name__ == "__main__":
    unittest.main()
