"""Obsidian retrieval must work from a synced index when the vault is absent.

Production (Hetzner) never carries the vault — it lives on the Mac. Jarvis
there honestly refused to claim vault access ("that vault path isn't
active"). These tests pin the fix: a synced index alone serves retrieval,
labeled honestly as reflecting the last sync, and the vault-present
behavior is unchanged.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from jarvis.obsidian_context import ObsidianVaultSupport


def _index_payload() -> dict:
    return {
        "vault_path": "/nonexistent/vault",
        "generated_at": "2026-07-03T12:00:00+00:00",
        "backend": "native",
        "file_count": 2,
        "files": [
            {
                "rel_path": "Missions/Books.md",
                "title": "Mission: Books",
                "headings": ["Goals"],
                "preview": "Building a lasting authorship platform that generates passive income.",
                "mtime_ns": 1,
                "size": 100,
            },
            {
                "rel_path": "Knowledge/Camping.md",
                "title": "Camping Notes",
                "headings": ["Gear"],
                "preview": "Family camping gear list and favorite spots by the lake.",
                "mtime_ns": 1,
                "size": 90,
            },
        ],
    }


class SyncedIndexModeTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        self.index_path = root / "index.json"
        self.index_path.write_text(json.dumps(_index_payload()), encoding="utf-8")
        self.support = ObsidianVaultSupport(
            vault_path=root / "no-vault-here",
            index_path=self.index_path,
            retriever_backend="native",
        )

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_mode_is_synced_index_when_vault_absent(self) -> None:
        self.assertEqual(self.support.mode, "synced-index")
        self.assertTrue(self.support.enabled)

    def test_retrieval_serves_from_synced_index(self) -> None:
        hits = self.support.retrieve("authorship platform books", limit=3)
        self.assertTrue(hits)
        self.assertEqual(hits[0]["title"], "Mission: Books")

    def test_status_is_honest_about_sync(self) -> None:
        status = self.support.status()
        self.assertEqual(status["mode"], "synced-index")
        self.assertTrue(status["enabled"])
        self.assertFalse(status["vault_exists"])
        self.assertIn("synced index", status["detail"])
        self.assertIn("last sync", status["detail"])

    def test_unavailable_without_vault_or_index(self) -> None:
        support = ObsidianVaultSupport(
            vault_path=Path(self._tmp.name) / "nope",
            index_path=Path(self._tmp.name) / "missing.json",
        )
        self.assertEqual(support.mode, "unavailable")
        self.assertFalse(support.enabled)
        self.assertEqual(support.retrieve("anything"), [])

    def test_live_vault_mode_unchanged(self) -> None:
        vault = Path(self._tmp.name) / "vault"
        vault.mkdir()
        (vault / "note.md").write_text("# Hello\nA real note about sailing.", encoding="utf-8")
        support = ObsidianVaultSupport(
            vault_path=vault,
            index_path=Path(self._tmp.name) / "live-index.json",
            retriever_backend="native",
        )
        self.assertEqual(support.mode, "live-vault")
        hits = support.retrieve("sailing note", limit=2)
        self.assertTrue(hits)


if __name__ == "__main__":
    unittest.main()
