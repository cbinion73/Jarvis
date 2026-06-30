from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from jarvis.checklists import ChecklistStore, build_direct_checklist_response
from jarvis.drafts import DraftStore, build_direct_draft_response
from jarvis.plans import PlanStore, build_direct_plan_response
from jarvis.runtime import JarvisRuntime


class DraftCreationTests(unittest.TestCase):
    def test_direct_explicit_drafting_ask_creates_real_draft_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = DraftStore(Path(tmp) / "data" / "drafts")
            payload = build_direct_draft_response(
                store,
                actor="Chris",
                room="office",
                request="Draft a text to the Scout parents about the campout.",
            )

            self.assertIsNotNone(payload)
            self.assertIn("i drafted", str(payload.get("output_text", "")).lower())
            created = payload.get("created_draft")
            self.assertIsInstance(created, dict)
            self.assertEqual(created.get("object_kind"), "draft")
            self.assertEqual(created.get("draft_kind"), "text")
            self.assertEqual(created.get("topic"), "to the Scout parents about the campout")
            self.assertIn("Quick note about the campout", str(created.get("content", "")))
            self.assertTrue(store.index_path.exists())

            persisted = store.get_draft(str(created.get("draft_id", "")))
            self.assertIsNotNone(persisted)
            self.assertEqual(persisted.get("title"), created.get("title"))
            self.assertEqual(persisted.get("content"), created.get("content"))

    def test_missing_context_drafting_ask_requests_minimum_detail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = DraftStore(Path(tmp) / "data" / "drafts")
            payload = build_direct_draft_response(
                store,
                actor="Chris",
                room="office",
                request="Write me an email draft.",
            )

            self.assertIsNotNone(payload)
            self.assertEqual(
                str(payload.get("output_text", "")).strip(),
                "I can do that. Who is it for, and what is it about?",
            )
            self.assertIsNone(payload.get("created_draft"))
            self.assertFalse(store.index_path.exists())

    def test_non_drafting_request_does_not_create_draft(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = DraftStore(Path(tmp) / "data" / "drafts")
            payload = build_direct_draft_response(
                store,
                actor="Chris",
                room="office",
                request="Help me think through retirement.",
            )

            self.assertIsNone(payload)
            self.assertFalse(store.index_path.exists())

    def test_runtime_draft_intercept_returns_created_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = DraftStore(Path(tmp) / "data" / "drafts")
            runtime = SimpleNamespace(
                draft_store=store,
                get_actor=lambda actor_name: SimpleNamespace(display_name=actor_name),
            )

            result = JarvisRuntime._try_handle_draft_creation(
                runtime,
                "Chris",
                "office",
                "Create a draft message to Rebekah about this weekend.",
            )

            self.assertIsNotNone(result)
            self.assertEqual(result.provider, "draft-engine")
            self.assertIn("i drafted", result.output_text.lower())
            self.assertIsInstance(result.created_draft, dict)
            self.assertEqual(result.created_draft.get("object_kind"), "draft")
            self.assertEqual(result.created_draft.get("draft_kind"), "message")
            self.assertEqual(result.created_draft.get("topic"), "to Rebekah about this weekend")

    def test_checklist_regression_control_still_creates_checklist_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ChecklistStore(Path(tmp) / "data" / "checklists")
            payload = build_direct_checklist_response(
                store,
                actor="Chris",
                room="office",
                request="Make me a checklist for getting ready for the trip.",
            )

            self.assertIsNotNone(payload)
            self.assertIsInstance(payload.get("created_checklist"), dict)
            self.assertEqual(payload["created_checklist"].get("object_kind"), "checklist")

    def test_plan_regression_control_still_creates_plan_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = PlanStore(Path(tmp) / "data" / "plans")
            payload = build_direct_plan_response(
                store,
                actor="Chris",
                room="office",
                request="Make me a plan for the Scout campout.",
            )

            self.assertIsNotNone(payload)
            self.assertIsInstance(payload.get("created_plan"), dict)
            self.assertEqual(payload["created_plan"].get("object_kind"), "plan")


if __name__ == "__main__":
    unittest.main()
