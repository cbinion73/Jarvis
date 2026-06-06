from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jarvis.forge import ForgeStore


class ForgeStoreTests(unittest.TestCase):
    def test_replays_project_index_and_project_file_from_append_logs_when_snapshots_are_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ForgeStore(root=Path(tmp) / "forge")
            project = store.create_project("Test Forge Project", "Prototype enclosure")
            project_id = project["id"]

            store._index_path.write_text("", encoding="utf-8")
            store._project_path(project_id).write_text("", encoding="utf-8")

            listed = store.list_projects()
            replayed = store.get_project(project_id)

            self.assertEqual(len(listed), 1)
            self.assertEqual(listed[0]["id"], project_id)
            self.assertIsNotNone(replayed)
            self.assertEqual(replayed["title"], "Test Forge Project")
            self.assertEqual(replayed["description"], "Prototype enclosure")


if __name__ == "__main__":
    unittest.main()
