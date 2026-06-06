import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class Level9MockupPlanningSurfacesTests(unittest.TestCase):
    def test_delivery_checklist_operationalizes_roadmap_and_society_stack(self) -> None:
        html = (ROOT / "artifacts/mockups/jarvis-delivery-checklist.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("JARVIS Delivery Checklist", html)
        self.assertIn("operationalizes the civilization-scale roadmap", html)
        self.assertIn("BMAD and OpenClaw", html)
        self.assertIn("Make the promotion engine real enough to govern sandbox-to-live progression", html)
        self.assertIn("Register OpenClaw as the governed execution layer inside JARVIS", html)

    def test_implementation_sidebar_keeps_operator_and_foundry_gaps_visible(self) -> None:
        html = (
            ROOT / "artifacts/mockups/jarvis-implementation-sidebar.html"
        ).read_text(encoding="utf-8")
        self.assertIn("JARVIS Comprehensive Checklist", html)
        self.assertIn("CLI and operator command closeout", html)
        self.assertIn("`away-report` operator flow", html)
        self.assertIn("Recursive foundry and specialist-agent generation", html)
        self.assertIn("builder-agent and newborn-agent pipeline", html)

    def test_next_arc_checklist_tracks_rollout_posture_after_governance_convergence(self) -> None:
        html = (ROOT / "artifacts/mockups/jarvis-next-arc-checklist.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("JARVIS Next Arc Checklist", html)
        self.assertIn("Governance proposal convergence is now live", html)
        self.assertIn("Stewardship lane rollout controls", html)
        self.assertIn("Governance rollout posture automation", html)
        self.assertIn("promoted governance proposals actually influence default lane posture", html)
        self.assertIn("shared chamber-home aggregate", html)


if __name__ == "__main__":
    unittest.main()
