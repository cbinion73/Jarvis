from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jarvis.obsidian_context import ObsidianVaultSupport


class ObsidianContextTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        root = Path(self.tmpdir.name)
        self.vault = root / "vault"
        self.vault.mkdir(parents=True, exist_ok=True)
        (self.vault / "Retirement").mkdir(parents=True, exist_ok=True)
        (self.vault / "Books").mkdir(parents=True, exist_ok=True)
        (self.vault / "Retirement" / "Retirement Vision.md").write_text(
            "# Retirement Vision\n\nRetirement means getting work out of the driver's seat without stopping meaningful building.\n",
            encoding="utf-8",
        )
        (self.vault / "Books" / "Writing with a Thinking Partner.md").write_text(
            "# Writing with a Thinking Partner\n\nWriting goes better when the thinking loop stays warm and specific.\n",
            encoding="utf-8",
        )
        self.index_path = root / "indexes" / "obsidian" / "index.json"

    def test_status_reports_readable_vault(self) -> None:
        support = ObsidianVaultSupport(self.vault, self.index_path)
        status = support.status()
        self.assertTrue(status["enabled"])
        self.assertEqual(status["markdown_file_count"], 2)
        self.assertFalse(status["index_exists"])

    def test_ensure_index_writes_derived_index(self) -> None:
        support = ObsidianVaultSupport(self.vault, self.index_path)
        payload = support.ensure_index()
        self.assertTrue(self.index_path.exists())
        self.assertEqual(payload["file_count"], 2)
        self.assertEqual(len(payload["files"]), 2)

    def test_retrieve_returns_ranked_snippets(self) -> None:
        support = ObsidianVaultSupport(self.vault, self.index_path)
        hits = support.retrieve("What does Obsidian say about retirement?", limit=2)
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["title"], "Retirement Vision")
        self.assertIn("driver's seat", hits[0]["snippet"])

    def test_conversation_context_formats_hits(self) -> None:
        support = ObsidianVaultSupport(self.vault, self.index_path)
        context = support.conversation_context("help me with writing", limit=2)
        self.assertIn("Retrieved Obsidian notes:", context)
        self.assertIn("Writing with a Thinking Partner", context)


if __name__ == "__main__":
    unittest.main()
