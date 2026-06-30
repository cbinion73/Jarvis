from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from jarvis.checklists import ChecklistStore, build_direct_checklist_response
from jarvis.decision_matrices import DecisionMatrixStore, build_direct_decision_matrix_response
from jarvis.drafts import DraftStore, build_direct_draft_response
from jarvis.evidence_bundles import EvidenceBundleStore, build_direct_evidence_bundle_response
from jarvis.itineraries import ItineraryStore, build_direct_itinerary_response
from jarvis.plans import PlanStore, build_direct_plan_response
from jarvis.recap_packets import RecapPacketStore, build_direct_recap_packet_response
from jarvis.recommendations import RecommendationStore, build_direct_recommendation_response
from jarvis.research_packets import ResearchPacketStore, build_direct_research_packet_response
from jarvis.runtime import JarvisRuntime
from jarvis.source_sets import SourceSetStore, build_direct_source_set_response
from jarvis.task_lists import TaskListStore, build_direct_task_list_response


class SourceSetCreationTests(unittest.TestCase):
    def test_direct_explicit_source_set_ask_creates_real_source_set_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = SourceSetStore(Path(tmp) / "data" / "source_sets")
            payload = build_direct_source_set_response(
                store,
                actor="Chris",
                room="office",
                request="Put together a source set on passive income ideas.",
            )

            self.assertIsNotNone(payload)
            self.assertIn("source set", str(payload.get("output_text", "")).lower())
            created = payload.get("created_source_set")
            self.assertIsInstance(created, dict)
            self.assertEqual(created.get("object_kind"), "source_set")
            self.assertEqual(created.get("topic"), "passive income ideas")
            self.assertEqual(created.get("truth_mode"), "local_source_set_scaffold_only")
            self.assertFalse(bool(created.get("live_retrieval_used")))
            self.assertFalse(bool(created.get("source_verification_completed")))
            self.assertGreaterEqual(len(list(created.get("source_groups", []))), 3)
            self.assertTrue(store.index_path.exists())

            persisted = store.get_source_set(str(created.get("source_set_id", "")))
            self.assertIsNotNone(persisted)
            self.assertEqual(persisted.get("title"), created.get("title"))
            self.assertEqual(persisted.get("summary"), created.get("summary"))

    def test_missing_context_source_set_ask_requests_minimum_detail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = SourceSetStore(Path(tmp) / "data" / "source_sets")
            payload = build_direct_source_set_response(
                store,
                actor="Chris",
                room="office",
                request="Collect the sources.",
            )

            self.assertIsNotNone(payload)
            self.assertEqual(
                str(payload.get("output_text", "")).strip(),
                "I can do that. What should the source set cover?",
            )
            self.assertIsNone(payload.get("created_source_set"))
            self.assertFalse(store.index_path.exists())

    def test_non_source_set_request_does_not_create_source_set(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = SourceSetStore(Path(tmp) / "data" / "source_sets")
            payload = build_direct_source_set_response(
                store,
                actor="Chris",
                room="office",
                request="Help me think through retirement.",
            )

            self.assertIsNone(payload)
            self.assertFalse(store.index_path.exists())

    def test_runtime_source_set_intercept_returns_created_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = SourceSetStore(Path(tmp) / "data" / "source_sets")
            runtime = SimpleNamespace(
                source_set_store=store,
                get_actor=lambda actor_name: SimpleNamespace(display_name=actor_name),
            )

            result = JarvisRuntime._try_handle_source_set_creation(
                runtime,
                "Chris",
                "office",
                "Make me a source set for pool robot options.",
            )

            self.assertIsNotNone(result)
            self.assertEqual(result.provider, "source-set-engine")
            self.assertIn("source set", result.output_text.lower())
            self.assertIsInstance(result.created_source_set, dict)
            self.assertEqual(result.created_source_set.get("object_kind"), "source_set")
            self.assertEqual(result.created_source_set.get("topic"), "pool robot options")

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

    def test_task_list_regression_control_still_creates_task_list_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = TaskListStore(Path(tmp) / "data" / "task_lists")
            payload = build_direct_task_list_response(
                store,
                actor="Chris",
                room="office",
                request="Make me a task list for the garage cleanout.",
            )

            self.assertIsNotNone(payload)
            self.assertIsInstance(payload.get("created_task_list"), dict)
            self.assertEqual(payload["created_task_list"].get("object_kind"), "task_list")

    def test_evidence_bundle_regression_control_still_creates_evidence_bundle_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = EvidenceBundleStore(Path(tmp) / "data" / "evidence_bundles")
            payload = build_direct_evidence_bundle_response(
                store,
                actor="Chris",
                room="office",
                request="Pull together the evidence on passive income ideas.",
            )

            self.assertIsNotNone(payload)
            self.assertIsInstance(payload.get("created_evidence_bundle"), dict)
            self.assertEqual(payload["created_evidence_bundle"].get("object_kind"), "evidence_bundle")

    def test_recap_packet_regression_control_still_creates_recap_packet_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = RecapPacketStore(Path(tmp) / "data" / "recap_packets")
            payload = build_direct_recap_packet_response(
                store,
                actor="Chris",
                room="office",
                request="Give me a recap of the retirement options.",
            )

            self.assertIsNotNone(payload)
            self.assertIsInstance(payload.get("created_recap_packet"), dict)
            self.assertEqual(payload["created_recap_packet"].get("object_kind"), "recap_packet")


if __name__ == "__main__":
    unittest.main()
