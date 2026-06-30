from __future__ import annotations

import unittest
from types import SimpleNamespace

from jarvis.checklists import ChecklistStore
from jarvis.openai_tasks import JarvisOpenAIClient
from jarvis.runtime import JarvisRuntime, _build_action_truth_summary

from tests.test_companion_spine import _plan


class SaveOpenTruthProofTests(unittest.TestCase):
    def test_system_prompt_explicitly_forbids_fake_open_load_and_save_claims(self) -> None:
        client = JarvisOpenAIClient(SimpleNamespace())
        prompt = client._system_prompt_with_context(
            _plan("Open mission control."),
            supplemental_context="Known local context:\n- Chris prefers practical help.",
        )
        self.assertIn("opened, loaded, accessed, or saved", prompt)
        self.assertIn("requested ui route is not the same thing as an already-open surface", prompt.lower())

    def test_action_truth_marks_packet_open_as_request_not_completed_open(self) -> None:
        summary = _build_action_truth_summary(
            result=None,
            requested_packet="mission-control",
            requested_catalyst_page="email",
        )

        self.assertTrue(bool(summary.get("surface_open_requested")))
        self.assertEqual(summary.get("surface_open_target"), "mission-control")
        self.assertFalse(bool(summary.get("surface_open_completed_in_runtime")))
        self.assertTrue(bool(summary.get("catalyst_page_requested")))
        self.assertEqual(summary.get("catalyst_page_target"), "email")
        self.assertFalse(bool(summary.get("reasoning_only")))

    def test_action_truth_distinguishes_local_object_record_from_saved_file(self) -> None:
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            store = ChecklistStore(Path(tmp) / "data" / "checklists")
            runtime = SimpleNamespace(
                checklist_store=store,
                get_actor=lambda actor_name: SimpleNamespace(display_name=actor_name),
            )

            created_result = JarvisRuntime._with_creation_truth_proof(
                JarvisRuntime._try_handle_checklist_creation(
                    runtime,
                    "Chris",
                    "office",
                    "Build a checklist for the Scout campout.",
                )
            )
            summary = _build_action_truth_summary(result=created_result)

            self.assertTrue(bool(summary.get("persisted_local_objects_created")))
            self.assertFalse(bool(summary.get("standalone_file_written")))
            self.assertFalse(bool(summary.get("external_save_used")))
            created_objects = list(summary.get("created_objects") or [])
            self.assertEqual(len(created_objects), 1)
            self.assertEqual(created_objects[0].get("object_kind"), "checklist")
            self.assertEqual(created_objects[0].get("storage_mode"), "persisted_local_object_record")


if __name__ == "__main__":
    unittest.main()
