from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from jarvis.research_tasks import ResearchTaskStore
from jarvis.runtime import JarvisRuntime


class _RuntimeLike(SimpleNamespace):
    create_research_task = JarvisRuntime.create_research_task
    research_task_snapshot = JarvisRuntime.research_task_snapshot
    research_task_queue_snapshot = JarvisRuntime.research_task_queue_snapshot
    update_research_task = JarvisRuntime.update_research_task
    add_research_task_evidence = JarvisRuntime.add_research_task_evidence
    generate_research_task_synthesis = JarvisRuntime.generate_research_task_synthesis


class ResearchTaskTests(unittest.TestCase):
    def test_store_creates_and_lists_real_research_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ResearchTaskStore(Path(tmp) / "data" / "research_tasks")

            created = store.create_task(
                actor="Chris",
                title="Pool robot follow-up",
                question="Which pool robot direction should I investigate first?",
                desired_scope="Start with local comparison criteria and obvious tradeoffs.",
                constraints=["Keep it under $1,000"],
                source_expectations=["Manufacturer specs", "owner reviews"],
            )

            listed = store.list_tasks()

            self.assertEqual(created["status"], "queued")
            self.assertEqual(created["object_kind"], "research_task")
            self.assertFalse(bool(created["research_performed"]))
            self.assertEqual(len(listed), 1)
            self.assertEqual(listed[0]["task_id"], created["task_id"])
            self.assertTrue(store.index_path.exists())

    def test_runtime_creates_truthful_research_task_without_claiming_research_happened(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ResearchTaskStore(Path(tmp) / "data" / "research_tasks")
            runtime = _RuntimeLike(
                research_task_store=store,
                get_actor=lambda actor_name: SimpleNamespace(display_name=actor_name),
            )

            result = runtime.create_research_task(
                "Chris",
                title="Retirement communities",
                question="What should I compare across retirement communities near Northern Kentucky?",
                desired_scope="Capture scope and source expectations only.",
                constraints=["Keep it within practical driving distance"],
                source_expectations=["pricing", "care level", "distance"],
            )
            queue = runtime.research_task_queue_snapshot()
            snapshot = runtime.research_task_snapshot(result["task"]["task_id"])

            self.assertEqual(result["task"]["status"], "queued")
            self.assertEqual(result["research_effect"], "not_performed")
            self.assertIn("queued intent only", result["message"].lower())
            self.assertEqual(queue["total_tasks"], 1)
            self.assertEqual(queue["counts_by_status"]["queued"], 1)
            self.assertEqual(snapshot["task"]["title"], "Retirement communities")
            self.assertFalse(bool(snapshot["task"]["source_discovery_performed"]))

    def test_runtime_rejects_invalid_research_task_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ResearchTaskStore(Path(tmp) / "data" / "research_tasks")
            runtime = _RuntimeLike(
                research_task_store=store,
                get_actor=lambda actor_name: SimpleNamespace(display_name=actor_name),
            )

            with self.assertRaisesRegex(ValueError, "status must be one of"):
                runtime.create_research_task(
                    "Chris",
                    title="Bad status",
                    question="What should I research here?",
                    status="running",
                )

    def test_runtime_updates_research_task_fields_without_claiming_research_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ResearchTaskStore(Path(tmp) / "data" / "research_tasks")
            runtime = _RuntimeLike(
                research_task_store=store,
                get_actor=lambda actor_name: SimpleNamespace(display_name=actor_name),
            )
            created = runtime.create_research_task(
                "Chris",
                title="Retirement communities",
                question="What should I compare first?",
                desired_scope="Start narrow.",
            )

            updated = runtime.update_research_task(
                created["task"]["task_id"],
                title="Retirement communities shortlist",
                question="Which retirement communities should I compare first near Northern Kentucky?",
                desired_scope="Focus on pricing, care level, and distance first.",
                status="in_progress",
                constraints=["Stay within driving distance"],
                source_expectations=["pricing", "care level"],
            )
            snapshot = runtime.research_task_snapshot(created["task"]["task_id"])

            self.assertEqual(updated["task"]["title"], "Retirement communities shortlist")
            self.assertEqual(updated["task"]["status"], "in_progress")
            self.assertEqual(updated["task"]["constraints"], ["Stay within driving distance"])
            self.assertEqual(updated["research_effect"], "not_performed")
            self.assertFalse(bool(updated["task"]["research_performed"]))
            self.assertIn("do not imply", updated["message"].lower())
            self.assertEqual(snapshot["task"]["source_expectations"], ["pricing", "care level"])

    def test_runtime_attaches_manual_evidence_without_marking_research_completed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ResearchTaskStore(Path(tmp) / "data" / "research_tasks")
            runtime = _RuntimeLike(
                research_task_store=store,
                get_actor=lambda actor_name: SimpleNamespace(display_name=actor_name),
            )
            created = runtime.create_research_task(
                "Chris",
                title="Pool robot options",
                question="Which pool robot direction should I compare first?",
                desired_scope="Keep it narrow for now.",
            )

            attached = runtime.add_research_task_evidence(
                created["task"]["task_id"],
                source_label="Owner review thread",
                source_locator="https://example.com/review-thread",
                evidence_note="Several owners reported easy maintenance.",
                capture_status="captured",
                confidence_label="preliminary",
            )
            snapshot = runtime.research_task_snapshot(created["task"]["task_id"])

            self.assertEqual(attached["evidence_item"]["source_label"], "Owner review thread")
            self.assertEqual(attached["evidence_item"]["capture_mode"], "manual_entry")
            self.assertFalse(bool(attached["evidence_item"]["retrieval_used"]))
            self.assertEqual(attached["research_effect"], "not_performed")
            self.assertFalse(bool(attached["task"]["research_performed"]))
            self.assertEqual(len(snapshot["task"]["evidence_items"]), 1)
            self.assertIn("does not imply completed research", attached["message"].lower())

    def test_runtime_generates_synthesis_only_from_attached_evidence_with_explicit_uncertainty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ResearchTaskStore(Path(tmp) / "data" / "research_tasks")
            runtime = _RuntimeLike(
                research_task_store=store,
                get_actor=lambda actor_name: SimpleNamespace(display_name=actor_name),
            )
            created = runtime.create_research_task(
                "Chris",
                title="Pool robot options",
                question="Which pool robot direction should I compare first?",
                desired_scope="Keep it narrow for now.",
                source_expectations=["manufacturer specs", "owner reviews"],
            )
            runtime.add_research_task_evidence(
                created["task"]["task_id"],
                source_label="Owner review thread",
                source_locator="https://example.com/review-thread",
                evidence_note="Several owners reported easy maintenance.",
                capture_status="captured",
                confidence_label="preliminary",
            )

            result = runtime.generate_research_task_synthesis(created["task"]["task_id"])

            self.assertEqual(result["research_effect"], "not_performed")
            self.assertFalse(bool(result["task"]["research_performed"]))
            self.assertEqual(result["synthesis"]["synthesis_mode"], "attached_evidence_only")
            self.assertEqual(result["synthesis"]["evidence_count"], 1)
            self.assertEqual(len(result["synthesis"]["evidence_ids_used"]), 1)
            self.assertIn("Several owners reported easy maintenance.", result["synthesis"]["supported_points"][0])
            self.assertTrue(result["synthesis"]["uncertainties"])
            self.assertFalse(bool(result["synthesis"]["externally_validated"]))
            self.assertIn("attached to this task", result["message"].lower())

    def test_runtime_rejects_synthesis_when_no_evidence_is_attached(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ResearchTaskStore(Path(tmp) / "data" / "research_tasks")
            runtime = _RuntimeLike(
                research_task_store=store,
                get_actor=lambda actor_name: SimpleNamespace(display_name=actor_name),
            )
            created = runtime.create_research_task(
                "Chris",
                title="Retirement communities",
                question="What should I compare first?",
            )

            with self.assertRaisesRegex(ValueError, "at least one attached evidence item is required"):
                runtime.generate_research_task_synthesis(created["task"]["task_id"])


if __name__ == "__main__":
    unittest.main()
