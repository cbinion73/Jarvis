from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from jarvis.checklists import ChecklistStore, build_direct_checklist_response
from jarvis.decision_matrices import DecisionMatrixStore, build_direct_decision_matrix_response
from jarvis.drafts import DraftStore, build_direct_draft_response
from jarvis.itineraries import ItineraryStore, build_direct_itinerary_response
from jarvis.plans import PlanStore, build_direct_plan_response
from jarvis.recommendations import RecommendationStore, build_direct_recommendation_response
from jarvis.research_packets import ResearchPacketStore, build_direct_research_packet_response
from jarvis.runtime import JarvisRuntime
from jarvis.task_lists import TaskListStore, build_direct_task_list_response


class TaskListCreationTests(unittest.TestCase):
    def test_direct_explicit_task_breakdown_ask_creates_real_task_list_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = TaskListStore(Path(tmp) / "data" / "task_lists")
            payload = build_direct_task_list_response(
                store,
                actor="Chris",
                room="office",
                request="Make me a task list for the garage cleanout.",
            )

            self.assertIsNotNone(payload)
            self.assertIn("task list", str(payload.get("output_text", "")).lower())
            created = payload.get("created_task_list")
            self.assertIsInstance(created, dict)
            self.assertEqual(created.get("object_kind"), "task_list")
            self.assertEqual(created.get("topic"), "the garage cleanout")
            self.assertEqual(created.get("truth_mode"), "local_task_list_scaffold_only")
            self.assertFalse(bool(created.get("live_task_system_used")))
            self.assertGreaterEqual(len(list(created.get("tasks", []))), 4)
            self.assertTrue(store.index_path.exists())

            persisted = store.get_task_list(str(created.get("task_list_id", "")))
            self.assertIsNotNone(persisted)
            self.assertEqual(persisted.get("title"), created.get("title"))
            self.assertEqual(persisted.get("summary"), created.get("summary"))

    def test_missing_context_task_breakdown_ask_requests_minimum_detail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = TaskListStore(Path(tmp) / "data" / "task_lists")
            payload = build_direct_task_list_response(
                store,
                actor="Chris",
                room="office",
                request="Break this into tasks for me.",
            )

            self.assertIsNotNone(payload)
            self.assertEqual(
                str(payload.get("output_text", "")).strip(),
                "I can do that. What should I break into tasks?",
            )
            self.assertIsNone(payload.get("created_task_list"))
            self.assertFalse(store.index_path.exists())

    def test_non_task_breakdown_request_does_not_create_task_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = TaskListStore(Path(tmp) / "data" / "task_lists")
            payload = build_direct_task_list_response(
                store,
                actor="Chris",
                room="office",
                request="Help me think through retirement.",
            )

            self.assertIsNone(payload)
            self.assertFalse(store.index_path.exists())

    def test_runtime_task_list_intercept_returns_created_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = TaskListStore(Path(tmp) / "data" / "task_lists")
            runtime = SimpleNamespace(
                task_list_store=store,
                get_actor=lambda actor_name: SimpleNamespace(display_name=actor_name),
            )

            result = JarvisRuntime._try_handle_task_list_creation(
                runtime,
                "Chris",
                "office",
                "Turn this into a task breakdown for the retirement workshop.",
            )

            self.assertIsNotNone(result)
            self.assertEqual(result.provider, "task-list-engine")
            self.assertIn("task list", result.output_text.lower())
            self.assertIsInstance(result.created_task_list, dict)
            self.assertEqual(result.created_task_list.get("object_kind"), "task_list")
            self.assertEqual(result.created_task_list.get("topic"), "the retirement workshop")

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

    def test_draft_regression_control_still_creates_draft_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = DraftStore(Path(tmp) / "data" / "drafts")
            payload = build_direct_draft_response(
                store,
                actor="Chris",
                room="office",
                request="Draft a text to the Scout parents about the campout.",
            )

            self.assertIsNotNone(payload)
            self.assertIsInstance(payload.get("created_draft"), dict)
            self.assertEqual(payload["created_draft"].get("object_kind"), "draft")

    def test_research_regression_control_still_creates_research_packet_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ResearchPacketStore(Path(tmp) / "data" / "research_packets")
            payload = build_direct_research_packet_response(
                store,
                actor="Chris",
                room="office",
                request="Research Scout trailer storage solutions.",
            )

            self.assertIsNotNone(payload)
            self.assertIsInstance(payload.get("created_research_packet"), dict)
            self.assertEqual(payload["created_research_packet"].get("object_kind"), "research_packet")

    def test_recommendation_regression_control_still_creates_recommendation_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = RecommendationStore(Path(tmp) / "data" / "recommendations")
            payload = build_direct_recommendation_response(
                store,
                actor="Chris",
                room="office",
                request="Recommend the best pool robot for me.",
            )

            self.assertIsNotNone(payload)
            self.assertIsInstance(payload.get("created_recommendation"), dict)
            self.assertEqual(payload["created_recommendation"].get("object_kind"), "recommendation")

    def test_decision_matrix_regression_control_still_creates_decision_matrix_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = DecisionMatrixStore(Path(tmp) / "data" / "decision_matrices")
            payload = build_direct_decision_matrix_response(
                store,
                actor="Chris",
                room="office",
                request="Compare these two pool robots for me.",
            )

            self.assertIsNotNone(payload)
            self.assertIsInstance(payload.get("created_decision_matrix"), dict)
            self.assertEqual(payload["created_decision_matrix"].get("object_kind"), "decision_matrix")

    def test_itinerary_regression_control_still_creates_itinerary_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ItineraryStore(Path(tmp) / "data" / "itineraries")
            payload = build_direct_itinerary_response(
                store,
                actor="Chris",
                room="office",
                request="Make me an itinerary for our weekend trip.",
            )

            self.assertIsNotNone(payload)
            self.assertIsInstance(payload.get("created_itinerary"), dict)
            self.assertEqual(payload["created_itinerary"].get("object_kind"), "itinerary")


if __name__ == "__main__":
    unittest.main()
