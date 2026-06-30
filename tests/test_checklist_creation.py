from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from jarvis.checklists import ChecklistStore, build_direct_checklist_response
from jarvis.runtime import JarvisRuntime


class ChecklistCreationTests(unittest.TestCase):
    def test_direct_checklist_ask_creates_real_checklist_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ChecklistStore(Path(tmp) / "data" / "checklists")
            payload = build_direct_checklist_response(
                store,
                actor="Chris",
                room="office",
                request="Make me a checklist for getting ready for the trip.",
            )

            self.assertIsNotNone(payload)
            self.assertIn("made a checklist", str(payload.get("output_text", "")).lower())
            created = payload.get("created_checklist")
            self.assertIsInstance(created, dict)
            self.assertEqual(created.get("object_kind"), "checklist")
            self.assertEqual(created.get("topic"), "getting ready for the trip")
            self.assertGreaterEqual(int(created.get("item_count", 0) or 0), 4)
            self.assertTrue(store.index_path.exists())

            persisted = store.get_checklist(str(created.get("checklist_id", "")))
            self.assertIsNotNone(persisted)
            self.assertEqual(persisted.get("title"), created.get("title"))
            self.assertEqual(len(list(persisted.get("items", []))), int(created.get("item_count", 0) or 0))

    def test_missing_context_checklist_ask_requests_minimum_detail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ChecklistStore(Path(tmp) / "data" / "checklists")
            payload = build_direct_checklist_response(
                store,
                actor="Chris",
                room="office",
                request="Make me a checklist.",
            )

            self.assertIsNotNone(payload)
            self.assertEqual(str(payload.get("output_text", "")).strip(), "I can do that. What is the checklist for?")
            self.assertIsNone(payload.get("created_checklist"))
            self.assertFalse(store.index_path.exists())

    def test_non_checklist_request_does_not_create_checklist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ChecklistStore(Path(tmp) / "data" / "checklists")
            payload = build_direct_checklist_response(
                store,
                actor="Chris",
                room="office",
                request="Help me think through vacation.",
            )

            self.assertIsNone(payload)
            self.assertFalse(store.index_path.exists())

    def test_runtime_checklist_intercept_returns_created_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ChecklistStore(Path(tmp) / "data" / "checklists")
            runtime = SimpleNamespace(
                checklist_store=store,
                get_actor=lambda actor_name: SimpleNamespace(display_name=actor_name),
            )

            result = JarvisRuntime._try_handle_checklist_creation(
                runtime,
                "Chris",
                "office",
                "Build a checklist for the Scout campout.",
            )

            self.assertIsNotNone(result)
            self.assertEqual(result.provider, "checklist-engine")
            self.assertIn("made a checklist", result.output_text.lower())
            self.assertIsInstance(result.created_checklist, dict)
            self.assertEqual(result.created_checklist.get("object_kind"), "checklist")
            self.assertEqual(result.created_checklist.get("topic"), "the Scout campout")


if __name__ == "__main__":
    unittest.main()
