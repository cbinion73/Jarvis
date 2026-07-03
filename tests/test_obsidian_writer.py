"""Writing learned knowledge back into Obsidian — the other half of the loop.

Trust boundary under test: nothing is ever written without approval, every
written note is unambiguously tagged as Jarvis-authored, writes only happen
in live-vault mode, and no proposal-supplied path can escape the vault.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from jarvis.obsidian_context import ObsidianVaultSupport
from jarvis.obsidian_writer import (
    build_note_markdown,
    extract_obsidian_save_topic,
    is_direct_obsidian_save_request,
    propose_note,
    sanitize_vault_relpath,
    slugify_title,
    write_approved_note,
)


class _FakeApprovalRequest:
    def __init__(self, request_id: str, payload: dict) -> None:
        self.request_id = request_id
        self.payload = payload
        self.action_type = "obsidian_note"


class _FakeQueue:
    def __init__(self) -> None:
        self.submitted: list = []

    def submit(self, request) -> str:
        self.submitted.append(request)
        return request.request_id


class RequestDetectionTests(unittest.TestCase):
    def test_recognizes_save_phrasings(self) -> None:
        for phrase in (
            "Save this to my Obsidian vault",
            "write this to obsidian about the book launch",
            "add this to my notes",
            "put this in my vault",
            "make an obsidian note about camping gear",
        ):
            self.assertTrue(is_direct_obsidian_save_request(phrase), phrase)

    def test_does_not_misfire_on_unrelated_requests(self) -> None:
        for phrase in (
            "What does my Obsidian vault say about books?",
            "Tell me about my notes",
            "Save the earth",
        ):
            self.assertFalse(is_direct_obsidian_save_request(phrase), phrase)

    def test_extracts_topic_when_present(self) -> None:
        self.assertEqual(
            extract_obsidian_save_topic("Save this to my Obsidian vault about the book launch strategy"),
            "the book launch strategy",
        )

    def test_empty_topic_when_none_given(self) -> None:
        self.assertEqual(extract_obsidian_save_topic("Save this to my Obsidian vault"), "")


class PathSafetyTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.vault = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_default_path_used_when_empty(self) -> None:
        dest = sanitize_vault_relpath("", self.vault, fallback_title="My Idea")
        self.assertTrue(str(dest).startswith(str(self.vault.resolve())))
        self.assertIn("Jarvis Notes", str(dest))
        self.assertTrue(dest.name.endswith(".md"))

    def test_escape_attempt_is_neutralized(self) -> None:
        dest = sanitize_vault_relpath("../../../etc/passwd", self.vault, fallback_title="Safe")
        # Must still resolve inside the vault — never outside it.
        dest.relative_to(self.vault.resolve())

    def test_absolute_path_attempt_is_neutralized(self) -> None:
        dest = sanitize_vault_relpath("/etc/passwd", self.vault, fallback_title="Safe")
        dest.relative_to(self.vault.resolve())

    def test_collision_gets_unique_suffix(self) -> None:
        (self.vault / "Jarvis Notes").mkdir()
        existing = self.vault / "Jarvis Notes" / "Idea.md"
        existing.write_text("existing", encoding="utf-8")
        dest = sanitize_vault_relpath("Jarvis Notes/Idea.md", self.vault, fallback_title="Idea")
        self.assertNotEqual(dest, existing)
        self.assertTrue(dest.exists() is False)

    def test_slugify_handles_junk_input(self) -> None:
        self.assertTrue(slugify_title("").strip())
        self.assertNotIn("/", slugify_title("Weird / Title * Here"))


class MarkdownBuildTests(unittest.TestCase):
    def test_frontmatter_tags_jarvis_authorship_unambiguously(self) -> None:
        md = build_note_markdown(
            title="Test Note", body="Some body text.", tags=["a", "b"],
            proposal_id="req-1", created_at="2026-07-04T00:00:00+00:00",
            source="conversation", source_detail="a chat about testing",
        )
        self.assertIn("source: jarvis", md)
        self.assertIn("created_by: jarvis", md)
        self.assertIn("proposal_id: req-1", md)
        self.assertIn("# Test Note", md)
        self.assertIn("Some body text.", md)
        self.assertIn("Drafted by Jarvis", md)


class ProposalLifecycleTests(unittest.TestCase):
    def test_propose_note_never_writes_to_disk(self) -> None:
        queue = _FakeQueue()
        result = propose_note(
            queue, actor_id="chris", agent_id="jarvis-companion",
            title="Camping Trip Notes", body="Pack the tent.",
            source="conversation", source_detail="a chat about camping",
        )
        self.assertEqual(result["status"], "pending_approval")
        self.assertEqual(len(queue.submitted), 1)
        self.assertEqual(queue.submitted[0].action_type, "obsidian_note")
        self.assertEqual(queue.submitted[0].risk_tier, "medium")

    def test_write_refuses_outside_live_vault_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            support = ObsidianVaultSupport(
                vault_path=Path(tmp) / "no-vault-here",
                index_path=Path(tmp) / "index.json",
            )
            self.assertEqual(support.mode, "unavailable")
            request = _FakeApprovalRequest("req-1", {"title": "X", "body": "Y"})
            result = write_approved_note(support, request)
        self.assertFalse(result["written"])
        self.assertIn("not writable", result["reason"])

    def test_write_succeeds_in_live_vault_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp) / "vault"
            vault.mkdir()
            support = ObsidianVaultSupport(vault_path=vault, index_path=Path(tmp) / "index.json")
            self.assertEqual(support.mode, "live-vault")
            request = _FakeApprovalRequest(
                "req-2",
                {"title": "Camping Notes", "body": "Pack the tent.", "tags": ["camping"],
                 "source": "conversation", "source_detail": "a chat"},
            )
            result = write_approved_note(support, request)
            self.assertTrue(result["written"])
            written_path = vault / result["path"]
            self.assertTrue(written_path.exists())
            content = written_path.read_text(encoding="utf-8")
            self.assertIn("source: jarvis", content)
            self.assertIn("Pack the tent.", content)

    def test_write_never_overwrites_existing_note(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp) / "vault"
            (vault / "Jarvis Notes").mkdir(parents=True)
            existing = vault / "Jarvis Notes" / "Camping Notes.md"
            existing.write_text("Chris's own real note.", encoding="utf-8")
            support = ObsidianVaultSupport(vault_path=vault, index_path=Path(tmp) / "index.json")
            request = _FakeApprovalRequest(
                "req-3",
                {"title": "Camping Notes", "body": "Jarvis draft.", "source": "conversation"},
            )
            result = write_approved_note(support, request)
            self.assertTrue(result["written"])
            self.assertEqual(existing.read_text(encoding="utf-8"), "Chris's own real note.")
            self.assertNotEqual(vault / result["path"], existing)


if __name__ == "__main__":
    unittest.main()
