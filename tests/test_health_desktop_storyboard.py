import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class HealthDesktopStoryboardTests(unittest.TestCase):
    def test_storyboard_covers_command_brief_trends_coach_care_and_consultation(self) -> None:
        html = (ROOT / "artifacts/mockups/health-desktop-storyboard.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("JARVIS Health Intelligence Desktop Experience", html)
        self.assertIn('const screenOrder = ["command", "brief", "trends", "coach", "care", "conversation"]', html)
        self.assertIn("Here's your health command center.", html)
        self.assertIn("Training readiness, recovery actions, pacing, and daily plan coaching.", html)
        self.assertIn("Medication adherence, care lane coordination, schedule, and escalation tracking.", html)
        self.assertIn("Interactive consultation screen for spoken or guided health conversations.", html)

    def test_storyboard_exposes_live_mockup_controls_and_stateful_desktop_actions(self) -> None:
        html = (ROOT / "artifacts/mockups/health-desktop-storyboard.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("Open any storyboard screen to explore the live mockup.", html)
        self.assertIn("Prototype mode: screen navigation, range filters, export, coaching, care, and voice demo are all interactive.", html)
        self.assertIn("Opening health desktop settings.", html)
        self.assertIn("health storyboard live hydrate failed", html)
        self.assertIn("Care circle monitoring is active and can be promoted for review.", html)
        self.assertIn("showToast(\"Food log captured\", \"Sam updated the coaching thread.\");", html)


if __name__ == "__main__":
    unittest.main()
