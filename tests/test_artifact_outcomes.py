from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from jarvis.artifact_outcomes import ArtifactOutcomeStore
from jarvis.checklists import ChecklistStore
from jarvis.runtime import JarvisRuntime


class _RuntimeLike(SimpleNamespace):
    _resolve_artifact_outcome_target = JarvisRuntime._resolve_artifact_outcome_target
    record_artifact_outcome = JarvisRuntime.record_artifact_outcome
    artifact_outcome_snapshot = JarvisRuntime.artifact_outcome_snapshot
    artifact_outcome_summary = JarvisRuntime.artifact_outcome_summary


class ArtifactOutcomeTests(unittest.TestCase):
    def test_store_records_and_filters_outcomes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ArtifactOutcomeStore(Path(tmp) / "data" / "outcomes")

            created = store.record_outcome(
                recorded_by="Chris",
                target_kind="checklist",
                target_id="checklist-1",
                target_category="work_object",
                target_label="Trip checklist",
                storage_mode="persisted_local_object_record",
                backing_store_files=["checklists.json", "checklists_log.jsonl"],
                outcome="helpful",
                note="Used it while packing.",
            )

            history = store.list_outcomes(target_kind="checklist", target_id="checklist-1")

            self.assertEqual(created["outcome"], "helpful")
            self.assertEqual(len(history), 1)
            self.assertEqual(history[0]["target_label"], "Trip checklist")
            self.assertEqual(history[0]["note"], "Used it while packing.")

    def test_runtime_records_outcome_for_real_checklist_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            checklist_store = ChecklistStore(Path(tmp) / "data" / "checklists")
            artifact_outcome_store = ArtifactOutcomeStore(Path(tmp) / "data" / "outcomes")
            created = checklist_store.create_checklist(
                actor="Chris",
                room="office",
                title="Trip checklist",
                topic="the trip",
                source_request="Make me a checklist for the trip.",
                items=["Pack clothes", "Pack chargers"],
            )

            runtime = _RuntimeLike(
                checklist_store=checklist_store,
                artifact_outcome_store=artifact_outcome_store,
                mission_support=SimpleNamespace(mission_delegation_report=lambda mission_id, report_id: None),
                get_actor=lambda actor_name: SimpleNamespace(display_name=actor_name),
            )

            result = runtime.record_artifact_outcome(
                "Chris",
                target_kind="checklist",
                target_id=created["checklist_id"],
                outcome="used",
                note="Actually used this to get packed.",
            )
            snapshot = runtime.artifact_outcome_snapshot(
                target_kind="checklist",
                target_id=created["checklist_id"],
            )

            self.assertEqual(result["recorded_outcome"]["outcome"], "used")
            self.assertEqual(result["target"]["storage_mode"], "persisted_local_object_record")
            self.assertEqual(result["learning_effect"], "none")
            self.assertEqual(snapshot["latest_outcome"]["outcome"], "used")
            self.assertEqual(len(snapshot["outcome_history"]), 1)

    def test_runtime_records_outcome_for_real_delegation_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            artifact_outcome_store = ArtifactOutcomeStore(Path(tmp) / "data" / "outcomes")
            report = {
                "report_id": "report-1",
                "title": "Weather review delivered",
                "summary": "Storm returned a concrete travel weather readout.",
                "artifact_ref": "/api/missions/mission-1/delegation-reports/report-1",
            }
            runtime = _RuntimeLike(
                artifact_outcome_store=artifact_outcome_store,
                mission_support=SimpleNamespace(
                    mission_delegation_report=lambda mission_id, report_id: dict(report)
                    if mission_id == "mission-1" and report_id == "report-1"
                    else None
                ),
                get_actor=lambda actor_name: SimpleNamespace(display_name=actor_name),
            )

            result = runtime.record_artifact_outcome(
                "Chris",
                target_kind="delegation_report",
                target_id="report-1",
                mission_id="mission-1",
                outcome="completed",
                note="Used the delegated output and closed the loop.",
            )

            self.assertEqual(result["target"]["target_category"], "delegated_output")
            self.assertEqual(result["target"]["artifact_ref"], "/api/missions/mission-1/delegation-reports/report-1")
            self.assertEqual(result["recorded_outcome"]["outcome"], "completed")

    def test_runtime_rejects_invalid_outcome_label(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            checklist_store = ChecklistStore(Path(tmp) / "data" / "checklists")
            artifact_outcome_store = ArtifactOutcomeStore(Path(tmp) / "data" / "outcomes")
            created = checklist_store.create_checklist(
                actor="Chris",
                room="office",
                title="Trip checklist",
                topic="the trip",
                source_request="Make me a checklist for the trip.",
                items=["Pack clothes"],
            )
            runtime = _RuntimeLike(
                checklist_store=checklist_store,
                artifact_outcome_store=artifact_outcome_store,
                mission_support=SimpleNamespace(mission_delegation_report=lambda mission_id, report_id: None),
                get_actor=lambda actor_name: SimpleNamespace(display_name=actor_name),
            )

            with self.assertRaisesRegex(ValueError, "outcome must be one of"):
                runtime.record_artifact_outcome(
                    "Chris",
                    target_kind="checklist",
                    target_id=created["checklist_id"],
                    outcome="amazing",
                )

    def test_runtime_summarizes_explicit_recorded_outcomes_without_learning_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            checklist_store = ChecklistStore(Path(tmp) / "data" / "checklists")
            artifact_outcome_store = ArtifactOutcomeStore(Path(tmp) / "data" / "outcomes")
            created = checklist_store.create_checklist(
                actor="Chris",
                room="office",
                title="Trip checklist",
                topic="the trip",
                source_request="Make me a checklist for the trip.",
                items=["Pack clothes", "Pack chargers"],
            )
            runtime = _RuntimeLike(
                checklist_store=checklist_store,
                artifact_outcome_store=artifact_outcome_store,
                mission_support=SimpleNamespace(mission_delegation_report=lambda mission_id, report_id: None),
                get_actor=lambda actor_name: SimpleNamespace(display_name=actor_name),
            )

            runtime.record_artifact_outcome(
                "Chris",
                target_kind="checklist",
                target_id=created["checklist_id"],
                outcome="helpful",
                note="Used it while packing.",
            )
            runtime.record_artifact_outcome(
                "Chris",
                target_kind="checklist",
                target_id=created["checklist_id"],
                outcome="completed",
                note="Finished the list.",
            )
            summary = runtime.artifact_outcome_summary()

            self.assertEqual(summary["total_records"], 2)
            self.assertEqual(summary["counts_by_outcome"]["helpful"], 1)
            self.assertEqual(summary["counts_by_outcome"]["completed"], 1)
            self.assertEqual(summary["counts_by_target_kind"]["checklist"], 2)
            self.assertEqual(summary["recent_outcomes"][0]["outcome"], "completed")
            self.assertEqual(summary["learning_effect"], "none")


if __name__ == "__main__":
    unittest.main()
