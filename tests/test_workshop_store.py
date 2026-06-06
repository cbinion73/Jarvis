from __future__ import annotations

import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

from jarvis.models import CadPackage, VendorPrep, WorkshopInspection
from jarvis.workshop import WorkshopStore


class WorkshopStoreTests(unittest.TestCase):
    def test_replays_inspections_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = WorkshopStore(Path(tmp))
            inspection = WorkshopInspection(
                inspection_id="inspection-1",
                actor="chris",
                part_name="Bracket",
                request="Diagnose warp",
                observations="Warped edge after print",
                goals="Recover part for reuse",
                diagnosis="Thermal stress",
                recommended_material="PLA",
                recommended_process="anneal",
                safety_notes=["Use gloves"],
                next_steps=["Anneal and re-measure"],
                image_path="",
                timestamp="2026-06-02T10:00:00+00:00",
            )

            store.add_inspection(inspection)
            store.inspections_path.write_text("", encoding="utf-8")

            records = store.list_inspections()

            self.assertEqual(records, [asdict(inspection)])

    def test_replays_vendor_preps_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = WorkshopStore(Path(tmp))
            prep = VendorPrep(
                prep_id="prep-1",
                actor="chris",
                part_name="Bracket",
                vendor_target="SendCutSend",
                material="Aluminum",
                process="laser_cut",
                package_summary="Ready for quote",
                approval_request_id="approval-1",
                status="draft",
                timestamp="2026-06-02T10:00:00+00:00",
                updated_at="2026-06-02T10:00:00+00:00",
            )

            store.add_vendor_prep(prep)
            store.vendor_preps_path.write_text("", encoding="utf-8")

            records = store.list_vendor_preps()

            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["part_name"], "Bracket")
            self.assertEqual(records[0]["vendor_target"], "SendCutSend")

    def test_replays_generic_record_store_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = WorkshopStore(Path(tmp))
            package = CadPackage(
                package_id="cad-1",
                actor="chris",
                part_name="Latch",
                family="hardware",
                summary="Door alignment bracket",
                parameters=["width=24", "height=10"],
                openscad_stub="cube([24,10,4]);",
                fit_checks=["clear hinge"],
                artifact_dir="artifacts/latch",
                script_path="designs/latch.scad",
                cadquery_script_path="designs/latch.py",
                model_path="artifacts/latch/latch.stl",
                step_path="artifacts/latch/latch.step",
                mesh_3mf_path="artifacts/latch/latch.3mf",
                slicer_pack_dir="artifacts/latch/slicer_pack",
                creative_profile="utility",
                export_status="ready",
                export_detail="Generated successfully",
                export_engine="cadquery",
                timestamp="2026-06-02T10:15:00+00:00",
            )

            store.add_cad_package(package)
            store.cad_packages_path.write_text("", encoding="utf-8")

            packages = store.list_cad_packages()

            self.assertEqual(len(packages), 1)
            self.assertEqual(packages[0]["package_id"], "cad-1")
            self.assertEqual(packages[0]["export_status"], "ready")


if __name__ == "__main__":
    unittest.main()
