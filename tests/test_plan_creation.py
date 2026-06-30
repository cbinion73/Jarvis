from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from jarvis.checklists import ChecklistStore, build_direct_checklist_response
from jarvis.plans import PlanStore, build_direct_plan_response
from jarvis.runtime import JarvisRuntime


class PlanCreationTests(unittest.TestCase):
    def test_direct_plan_ask_creates_real_plan_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = PlanStore(Path(tmp) / "data" / "plans")
            payload = build_direct_plan_response(
                store,
                actor="Chris",
                room="office",
                request="Make me a plan for getting the garage cleaned out this weekend.",
            )

            self.assertIsNotNone(payload)
            self.assertIn("made a plan", str(payload.get("output_text", "")).lower())
            created = payload.get("created_plan")
            self.assertIsInstance(created, dict)
            self.assertEqual(created.get("object_kind"), "plan")
            self.assertEqual(created.get("topic"), "getting the garage cleaned out this weekend")
            self.assertGreaterEqual(int(created.get("step_count", 0) or 0), 4)
            self.assertTrue(store.index_path.exists())

            persisted = store.get_plan(str(created.get("plan_id", "")))
            self.assertIsNotNone(persisted)
            self.assertEqual(persisted.get("title"), created.get("title"))
            self.assertEqual(len(list(persisted.get("steps", []))), int(created.get("step_count", 0) or 0))

    def test_missing_context_plan_ask_requests_minimum_detail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = PlanStore(Path(tmp) / "data" / "plans")
            payload = build_direct_plan_response(
                store,
                actor="Chris",
                room="office",
                request="Make me a plan.",
            )

            self.assertIsNotNone(payload)
            self.assertEqual(str(payload.get("output_text", "")).strip(), "I can do that. What is the plan for?")
            self.assertIsNone(payload.get("created_plan"))
            self.assertFalse(store.index_path.exists())

    def test_non_plan_request_does_not_create_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = PlanStore(Path(tmp) / "data" / "plans")
            payload = build_direct_plan_response(
                store,
                actor="Chris",
                room="office",
                request="Help me think through vacation.",
            )

            self.assertIsNone(payload)
            self.assertFalse(store.index_path.exists())

    def test_runtime_plan_intercept_returns_created_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = PlanStore(Path(tmp) / "data" / "plans")
            runtime = SimpleNamespace(
                plan_store=store,
                get_actor=lambda actor_name: SimpleNamespace(display_name=actor_name),
            )

            result = JarvisRuntime._try_handle_plan_creation(
                runtime,
                "Chris",
                "office",
                "Create a plan for finishing this draft.",
            )

            self.assertIsNotNone(result)
            self.assertEqual(result.provider, "plan-engine")
            self.assertIn("made a plan", result.output_text.lower())
            self.assertIsInstance(result.created_plan, dict)
            self.assertEqual(result.created_plan.get("object_kind"), "plan")
            self.assertEqual(result.created_plan.get("topic"), "finishing this draft")

    def test_checklist_regression_control_still_creates_checklist_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ChecklistStore(Path(tmp) / "data" / "checklists")
            payload = build_direct_checklist_response(
                store,
                actor="Chris",
                room="office",
                request="Build a checklist for the Scout campout.",
            )

            self.assertIsNotNone(payload)
            self.assertIn("made a checklist", str(payload.get("output_text", "")).lower())
            created = payload.get("created_checklist")
            self.assertIsInstance(created, dict)
            self.assertEqual(created.get("object_kind"), "checklist")
            self.assertEqual(created.get("topic"), "the Scout campout")


if __name__ == "__main__":
    unittest.main()
