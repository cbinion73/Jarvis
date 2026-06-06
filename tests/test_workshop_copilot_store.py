from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jarvis.workshop_copilot import MaterialStock, PrintJob, WorkshopCopilotStore, WorkshopProject


class WorkshopCopilotStoreTests(unittest.TestCase):
    def test_replays_projects_jobs_and_materials_from_logs_when_snapshots_are_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = WorkshopCopilotStore(root=Path(tmp))
            project = WorkshopProject(
                project_id="project-1",
                title="Clamp rack",
                description="Wall-mounted clamp rack",
                machine="k2_pro",
                status="designing",
                material="pla",
            )
            job = PrintJob(
                job_id="job-1",
                project_id="project-1",
                machine="k2_pro",
                file="clamp_rack.gcode",
                status="queued",
            )
            material = MaterialStock(
                material_id="mat-1",
                name="PLA Black 1kg",
                material_type="pla",
                quantity_g=850,
            )

            store.save_project(project)
            store.log_job(job)
            store.save_material(material)

            store.projects_path.write_text("", encoding="utf-8")
            store.jobs_path.write_text("", encoding="utf-8")
            store.materials_path.write_text("", encoding="utf-8")

            loaded_project = store.get_project("project-1")
            loaded_jobs = store.get_active_jobs()
            loaded_materials = store.get_materials()

            self.assertIsNotNone(loaded_project)
            assert loaded_project is not None
            self.assertEqual(loaded_project.title, "Clamp rack")
            self.assertEqual(len(loaded_jobs), 1)
            self.assertEqual(loaded_jobs[0].job_id, "job-1")
            self.assertEqual(len(loaded_materials), 1)
            self.assertEqual(loaded_materials[0].material_id, "mat-1")


if __name__ == "__main__":
    unittest.main()
