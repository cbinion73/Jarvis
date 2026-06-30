from __future__ import annotations

import tempfile
import unittest
from types import ModuleType
from pathlib import Path
from unittest.mock import patch

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

    def test_status_reports_llamaindex_backend_when_available(self) -> None:
        support = ObsidianVaultSupport(self.vault, self.index_path, retriever_backend="llamaindex")
        with _fake_llamaindex():
            status = support.status()
        self.assertEqual(status["requested_retriever_backend"], "llamaindex")
        self.assertEqual(status["active_retriever_backend"], "llamaindex")
        self.assertTrue(status["llamaindex_available"])

    def test_llamaindex_backend_writes_chunk_index_and_retrieves(self) -> None:
        support = ObsidianVaultSupport(
            self.vault,
            self.index_path,
            retriever_backend="llamaindex",
            chunk_size=64,
            chunk_overlap=8,
        )
        with _fake_llamaindex():
            payload = support.ensure_index()
            hits = support.retrieve("retirement meaningful building", limit=2)
        self.assertEqual(payload["backend"], "llamaindex")
        self.assertGreater(payload["chunk_count"], 0)
        self.assertEqual(hits[0]["title"], "Retirement Vision")
        self.assertIn("meaningful building", hits[0]["snippet"])


class _FakeDocument:
    def __init__(self, text: str, metadata: dict | None = None) -> None:
        self.text = text
        self.metadata = metadata or {}


class _FakeNode:
    def __init__(self, text: str, metadata: dict | None = None) -> None:
        self._text = text
        self.metadata = metadata or {}

    def get_content(self, metadata_mode: str | None = None) -> str:
        return self._text


class _FakeSentenceSplitter:
    def __init__(self, chunk_size: int = 768, chunk_overlap: int = 80) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def get_nodes_from_documents(self, documents: list[_FakeDocument]) -> list[_FakeNode]:
        nodes: list[_FakeNode] = []
        for document in documents:
            paragraphs = [
                part.strip()
                for part in document.text.split("\n\n")
                if part.strip() and not part.strip().startswith("#")
            ]
            for paragraph in paragraphs:
                nodes.append(_FakeNode(paragraph, metadata=dict(document.metadata)))
        return nodes


def _fake_llamaindex():
    core_module = ModuleType("llama_index.core")
    core_module.Document = _FakeDocument
    node_parser_module = ModuleType("llama_index.core.node_parser")
    node_parser_module.SentenceSplitter = _FakeSentenceSplitter
    return patch.dict(
        "sys.modules",
        {
            "llama_index": ModuleType("llama_index"),
            "llama_index.core": core_module,
            "llama_index.core.node_parser": node_parser_module,
        },
    )


if __name__ == "__main__":
    unittest.main()
