from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from jarvis.action_briefs import ActionBriefStore, build_direct_action_brief_response
from jarvis.checklists import ChecklistStore, build_direct_checklist_response
from jarvis.constraint_maps import ConstraintMapStore, build_direct_constraint_map_response
from jarvis.decision_matrices import DecisionMatrixStore, build_direct_decision_matrix_response
from jarvis.decision_memos import DecisionMemoStore, build_direct_decision_memo_response
from jarvis.drafts import DraftStore, build_direct_draft_response
from jarvis.evidence_bundles import EvidenceBundleStore, build_direct_evidence_bundle_response
from jarvis.itineraries import ItineraryStore, build_direct_itinerary_response
from jarvis.option_cards import OptionCardStore, build_direct_option_card_response
from jarvis.plans import PlanStore, build_direct_plan_response
from jarvis.pros_cons import ProsConsStore, build_direct_pros_cons_response
from jarvis.question_sets import QuestionSetStore, build_direct_question_set_response
from jarvis.recap_packets import RecapPacketStore, build_direct_recap_packet_response
from jarvis.recommendations import RecommendationStore, build_direct_recommendation_response
from jarvis.research_packets import ResearchPacketStore, build_direct_research_packet_response
from jarvis.runtime import JarvisRuntime
from jarvis.source_sets import SourceSetStore, build_direct_source_set_response
from jarvis.structured_notes import StructuredNoteStore, build_direct_structured_note_response
from jarvis.task_lists import TaskListStore, build_direct_task_list_response


class QuestionSetCreationTests(unittest.TestCase):
    def test_direct_explicit_question_set_ask_creates_real_question_set_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = QuestionSetStore(Path(tmp) / "data" / "question_sets")
            payload = build_direct_question_set_response(
                store,
                actor="Chris",
                room="office",
                request="What questions should I be asking about the retirement workshop?",
            )

            self.assertIsNotNone(payload)
            self.assertIn("question set", str(payload.get("output_text", "")).lower())
            created = payload.get("created_question_set")
            self.assertIsInstance(created, dict)
            self.assertEqual(created.get("object_kind"), "question_set")
            self.assertEqual(created.get("topic"), "the retirement workshop")
            self.assertEqual(created.get("truth_mode"), "local_question_set_scaffold_only")
            self.assertFalse(bool(created.get("live_research_used")))
            self.assertFalse(bool(created.get("validated_discovery_used")))
            self.assertFalse(bool(created.get("external_retrieval_used")))
            self.assertGreaterEqual(len(list(created.get("questions", []))), 3)
            self.assertTrue(store.index_path.exists())

            persisted = store.get_question_set(str(created.get("question_set_id", "")))
            self.assertIsNotNone(persisted)
            self.assertEqual(persisted.get("title"), created.get("title"))
            self.assertEqual(persisted.get("framing_note"), created.get("framing_note"))

    def test_missing_context_question_set_ask_requests_minimum_detail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = QuestionSetStore(Path(tmp) / "data" / "question_sets")
            payload = build_direct_question_set_response(
                store,
                actor="Chris",
                room="office",
                request="Make me a question set.",
            )

            self.assertIsNotNone(payload)
            self.assertEqual(
                str(payload.get("output_text", "")).strip(),
                "I can do that. What should the question set cover?",
            )
            self.assertIsNone(payload.get("created_question_set"))
            self.assertFalse(store.index_path.exists())

    def test_non_clarification_request_does_not_create_question_set_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = QuestionSetStore(Path(tmp) / "data" / "question_sets")
            payload = build_direct_question_set_response(
                store,
                actor="Chris",
                room="office",
                request="Help me think through retirement.",
            )

            self.assertIsNone(payload)
            self.assertFalse(store.index_path.exists())

    def test_runtime_question_set_intercept_returns_created_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = QuestionSetStore(Path(tmp) / "data" / "question_sets")
            runtime = SimpleNamespace(
                question_set_store=store,
                get_actor=lambda actor_name: SimpleNamespace(display_name=actor_name),
            )

            result = JarvisRuntime._try_handle_question_set_creation(
                runtime,
                "Chris",
                "office",
                "Give me the discovery questions for the pool robot decision.",
            )

            self.assertIsNotNone(result)
            self.assertEqual(result.provider, "question-set-engine")
            self.assertIn("question set", result.output_text.lower())
            self.assertIsInstance(result.created_question_set, dict)
            self.assertEqual(result.created_question_set.get("object_kind"), "question_set")
            self.assertEqual(result.created_question_set.get("topic"), "the pool robot decision")

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
            self.assertEqual(payload["created_recap_packet"].get("object_kind"), "recap_packet")

    def test_source_set_regression_control_still_creates_source_set_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = SourceSetStore(Path(tmp) / "data" / "source_sets")
            payload = build_direct_source_set_response(
                store,
                actor="Chris",
                room="office",
                request="Put together a source set on passive income ideas.",
            )
            self.assertIsNotNone(payload)
            self.assertEqual(payload["created_source_set"].get("object_kind"), "source_set")

    def test_structured_note_regression_control_still_creates_structured_note_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = StructuredNoteStore(Path(tmp) / "data" / "structured_notes")
            payload = build_direct_structured_note_response(
                store,
                actor="Chris",
                room="office",
                request="Capture a note about passive income ideas.",
            )
            self.assertIsNotNone(payload)
            self.assertEqual(payload["created_structured_note"].get("object_kind"), "structured_note")

    def test_action_brief_regression_control_still_creates_action_brief_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ActionBriefStore(Path(tmp) / "data" / "action_briefs")
            payload = build_direct_action_brief_response(
                store,
                actor="Chris",
                room="office",
                request="Give me a next-steps brief for the retirement workshop.",
            )
            self.assertIsNotNone(payload)
            self.assertEqual(payload["created_action_brief"].get("object_kind"), "action_brief")

    def test_decision_memo_regression_control_still_creates_decision_memo_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = DecisionMemoStore(Path(tmp) / "data" / "decision_memos")
            payload = build_direct_decision_memo_response(
                store,
                actor="Chris",
                room="office",
                request="Make me a decision memo on which pool robot to buy.",
            )
            self.assertIsNotNone(payload)
            self.assertEqual(payload["created_decision_memo"].get("object_kind"), "decision_memo")

    def test_option_card_regression_control_still_creates_option_card_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = OptionCardStore(Path(tmp) / "data" / "option_cards")
            payload = build_direct_option_card_response(
                store,
                actor="Chris",
                room="office",
                request="Lay out my options on the retirement workshop.",
            )
            self.assertIsNotNone(payload)
            self.assertEqual(payload["created_option_card"].get("object_kind"), "option_card")

    def test_pros_cons_regression_control_still_creates_pros_cons_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ProsConsStore(Path(tmp) / "data" / "pros_cons")
            payload = build_direct_pros_cons_response(
                store,
                actor="Chris",
                room="office",
                request="Give me the pros and cons of the retirement workshop options.",
            )
            self.assertIsNotNone(payload)
            self.assertEqual(payload["created_pros_cons"].get("object_kind"), "pros_cons")

    def test_constraint_map_regression_control_still_creates_constraint_map_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ConstraintMapStore(Path(tmp) / "data" / "constraint_maps")
            payload = build_direct_constraint_map_response(
                store,
                actor="Chris",
                room="office",
                request="Give me a constraint map for the pool robot decision.",
            )
            self.assertIsNotNone(payload)
            self.assertEqual(payload["created_constraint_map"].get("object_kind"), "constraint_map")


if __name__ == "__main__":
    unittest.main()
