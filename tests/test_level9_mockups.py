import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class Level9MockupsTests(unittest.TestCase):
    def test_seam_tracker_page_exposes_current_counts(self) -> None:
        html = (ROOT / "artifacts/mockups/jarvis-seam-tracker.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("JARVIS Seam Tracker", html)
        self.assertIn("187", html)
        self.assertIn("38", html)
        self.assertIn("34", html)
        self.assertIn("Seams are internal implementation checkpoints", html)
        self.assertIn("./jarvis-path-to-level-9-checklist.html", html)
        self.assertIn("Current Stacked Tip", html)
        self.assertIn("codex/level9-knowledge-maker-durability-slice", html)
        self.assertIn("114078c", html)
        self.assertIn("codex/level9-household-durability-wave-slice", html)
        self.assertIn("Remaining Delta Clusters", html)
        self.assertIn("Live wiring and service surfaces", html)
        self.assertIn("Docs and planning truth", html)
        self.assertIn("Seams To Checklist Phase Map", html)
        self.assertIn("Phase A", html)
        self.assertIn("Phase J", html)
        self.assertIn("./jarvis-progress-dashboard.html", html)
        self.assertIn("Progress Dashboard", html)

    def test_level9_checklist_links_to_seam_tracker(self) -> None:
        html = (
            ROOT / "artifacts/mockups/jarvis-path-to-level-9-checklist.html"
        ).read_text(encoding="utf-8")
        self.assertIn("./jarvis-seam-tracker.html", html)
        self.assertIn("Seam tracker", html)
        self.assertIn("Seams are internal implementation checkpoints", html)

    def test_progress_dashboard_captures_recommendation_model(self) -> None:
        html = (ROOT / "artifacts/mockups/jarvis-progress-dashboard.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("JARVIS Progress Dashboard", html)
        self.assertIn("The Core Question", html)
        self.assertIn("Open Seam Tracker", html)
        self.assertIn("Four Layers", html)
        self.assertIn("Roadmap", html)
        self.assertIn("Seams", html)
        self.assertIn("Substrate", html)
        self.assertIn("Experience", html)
        self.assertIn("Status Categories", html)
        self.assertIn("Mocked", html)
        self.assertIn("Compounding", html)
        self.assertIn("Theater List", html)
        self.assertIn("What To Track Weekly", html)
        self.assertIn("What seams were completed?", html)
        self.assertIn("0 to 5 Score Meaning", html)
        self.assertIn("visual mockup", html)
        self.assertIn("Truth-Telling Example", html)
        self.assertIn("mocked visually, stubbed logically", html)
        self.assertIn("What JARVIS Can Actually Do Today", html)


if __name__ == "__main__":
    unittest.main()
