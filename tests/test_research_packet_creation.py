from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from jarvis.checklists import ChecklistStore, build_direct_checklist_response
from jarvis.drafts import DraftStore, build_direct_draft_response
from jarvis.plans import PlanStore, build_direct_plan_response
from jarvis.research_packets import ResearchPacketStore, build_direct_research_packet_response
from jarvis.runtime import JarvisRuntime


class ResearchPacketCreationTests(unittest.TestCase):
    def test_direct_explicit_research_ask_creates_real_research_packet_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ResearchPacketStore(Path(tmp) / "data" / "research_packets")
            payload = build_direct_research_packet_response(
                store,
                actor="Chris",
                room="office",
                request="Research retirement communities near Northern Kentucky.",
            )

            self.assertIsNotNone(payload)
            self.assertIn("research packet scaffold", str(payload.get("output_text", "")).lower())
            created = payload.get("created_research_packet")
            self.assertIsInstance(created, dict)
            self.assertEqual(created.get("object_kind"), "research_packet")
            self.assertEqual(created.get("topic"), "retirement communities near Northern Kentucky")
            self.assertEqual(created.get("truth_mode"), "local_scaffold_only")
            self.assertFalse(bool(created.get("live_retrieval_used")))
            self.assertEqual(list(created.get("gathered_material", [])), [])
            self.assertGreaterEqual(len(list(created.get("open_questions", []))), 3)
            self.assertTrue(store.index_path.exists())

            persisted = store.get_packet(str(created.get("packet_id", "")))
            self.assertIsNotNone(persisted)
            self.assertEqual(persisted.get("title"), created.get("title"))
            self.assertEqual(persisted.get("summary"), created.get("summary"))

    def test_missing_context_research_ask_requests_minimum_detail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ResearchPacketStore(Path(tmp) / "data" / "research_packets")
            payload = build_direct_research_packet_response(
                store,
                actor="Chris",
                room="office",
                request="Research.",
            )

            self.assertIsNotNone(payload)
            self.assertEqual(
                str(payload.get("output_text", "")).strip(),
                "I can do that. What should the research packet cover?",
            )
            self.assertIsNone(payload.get("created_research_packet"))
            self.assertFalse(store.index_path.exists())

    def test_research_ask_can_attach_live_source_material(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ResearchPacketStore(Path(tmp) / "data" / "research_packets")
            payload = build_direct_research_packet_response(
                store,
                actor="Chris",
                room="office",
                request="Research retirement communities near Northern Kentucky.",
                retriever=lambda _topic: [
                    {
                        "title": "Example Source",
                        "url": "https://example.com/research",
                        "snippet": "A live source summary.",
                        "source": "browser_search",
                        "rank": 1,
                    }
                ],
            )

            self.assertIsNotNone(payload)
            created = payload.get("created_research_packet")
            self.assertIsInstance(created, dict)
            self.assertEqual(created.get("truth_mode"), "live_sources_attached")
            self.assertTrue(bool(created.get("live_retrieval_used")))
            self.assertEqual(len(list(created.get("gathered_material", []))), 1)
            self.assertIn("attached live source summaries", str(payload.get("output_text", "")).lower())

    def test_non_research_request_does_not_create_research_packet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ResearchPacketStore(Path(tmp) / "data" / "research_packets")
            payload = build_direct_research_packet_response(
                store,
                actor="Chris",
                room="office",
                request="Help me think through retirement.",
            )

            self.assertIsNone(payload)
            self.assertFalse(store.index_path.exists())

    def test_runtime_research_packet_intercept_returns_created_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ResearchPacketStore(Path(tmp) / "data" / "research_packets")
            runtime = SimpleNamespace(
                research_packet_store=store,
                get_actor=lambda actor_name: SimpleNamespace(display_name=actor_name),
                _record_artifact_creation_result=lambda _actor_name, _room, _request, result: result,
            )

            with patch(
                "jarvis.runtime.retrieve_research_material",
                return_value=[
                    {
                        "title": "Example Source",
                        "url": "https://example.com/pool-robot",
                        "snippet": "A live source summary.",
                        "source": "browser_search",
                        "rank": 1,
                    }
                ],
            ):
                result = JarvisRuntime._try_handle_research_packet_creation(
                    runtime,
                    "Chris",
                    "office",
                    "Build a research packet on the best pool robot options.",
                )

            self.assertIsNotNone(result)
            self.assertEqual(result.provider, "research-packet-engine")
            self.assertIn("attached live source summaries", result.output_text.lower())
            self.assertIsInstance(result.created_research_packet, dict)
            self.assertEqual(result.created_research_packet.get("object_kind"), "research_packet")
            self.assertEqual(result.created_research_packet.get("topic"), "the best pool robot options")
            self.assertEqual(result.created_research_packet.get("truth_mode"), "live_sources_attached")

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


if __name__ == "__main__":
    unittest.main()
