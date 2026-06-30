from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from jarvis.checklists import ChecklistStore
from jarvis.openai_tasks import OpenAIResult
from jarvis.research_packets import ResearchPacketStore
from jarvis.runtime import JarvisRuntime


class CreationTruthProofTests(unittest.TestCase):
    def test_real_local_checklist_creation_gets_persistence_proof(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ChecklistStore(Path(tmp) / "data" / "checklists")
            runtime = SimpleNamespace(
                checklist_store=store,
                get_actor=lambda actor_name: SimpleNamespace(display_name=actor_name),
            )

            created_result = JarvisRuntime._try_handle_checklist_creation(
                runtime,
                "Chris",
                "office",
                "Build a checklist for the Scout campout.",
            )
            proven = JarvisRuntime._with_creation_truth_proof(created_result)

            self.assertIsNotNone(proven)
            self.assertIn("saved locally as a real checklist object", proven.output_text.lower())
            proof = dict(proven.created_checklist.get("creation_proof", {}))
            self.assertEqual(proof.get("storage_mode"), "persisted_local_object_record")
            self.assertTrue(bool(proof.get("created_in_this_turn")))
            self.assertTrue(bool(proof.get("persisted_locally")))
            self.assertFalse(bool(proof.get("returned_payload_only")))
            self.assertFalse(bool(proof.get("standalone_file_written")))
            self.assertEqual(
                proof.get("backing_store_files"),
                ["checklists.json", "checklists_log.jsonl"],
            )

    def test_research_packet_proof_distinguishes_local_object_from_saved_file_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ResearchPacketStore(Path(tmp) / "data" / "research_packets")
            runtime = SimpleNamespace(
                research_packet_store=store,
                get_actor=lambda actor_name: SimpleNamespace(display_name=actor_name),
            )

            created_result = JarvisRuntime._try_handle_research_packet_creation(
                runtime,
                "Chris",
                "office",
                "Build a research packet on the best pool robot options.",
            )
            proven = JarvisRuntime._with_creation_truth_proof(created_result)

            self.assertIsNotNone(proven)
            self.assertIn("saved locally as a real research packet object", proven.output_text.lower())
            proof = dict(proven.created_research_packet.get("creation_proof", {}))
            self.assertEqual(proof.get("storage_mode"), "persisted_local_object_record")
            self.assertFalse(bool(proof.get("standalone_file_written")))
            self.assertEqual(
                proof.get("backing_store_files"),
                ["research_packets.json", "research_packets_log.jsonl"],
            )
            self.assertFalse(bool(proof.get("external_save_used")))

    def test_non_creation_result_does_not_pick_up_fake_create_or_save_language(self) -> None:
        result = OpenAIResult(
            provider="conversation",
            model="conversation",
            output_text="I can help you think it through from here.",
        )

        proven = JarvisRuntime._with_creation_truth_proof(result)

        self.assertIsNotNone(proven)
        self.assertEqual(proven.output_text, "I can help you think it through from here.")
        self.assertEqual(proven.created_checklist, {})
        self.assertNotIn("saved locally as a real", proven.output_text.lower())


if __name__ == "__main__":
    unittest.main()
