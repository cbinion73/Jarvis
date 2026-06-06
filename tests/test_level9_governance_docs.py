import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class Level9GovernanceDocsTests(unittest.TestCase):
    def test_branch_control_reflects_helper_clone_topology(self) -> None:
        text = (ROOT / "docs/level9-branch-control.md").read_text(encoding="utf-8")
        self.assertIn("## Runtime Topology", text)
        self.assertIn("/tmp/jarvis-push-helper", text)
        self.assertIn("Helper-clone-backed worktrees", text)
        self.assertIn("quarantined", text)
        self.assertIn("codex/level9-governance-slice", text)
        self.assertIn("codex/level9-agent-society-slice", text)
        self.assertIn("codex/level9-event-truth-lane", text)
        self.assertIn("codex/level9-household-operability-lane", text)

    def test_branch_integration_rubric_mentions_roadmap_order(self) -> None:
        text = (ROOT / "docs/branch-integration-rubric.md").read_text(encoding="utf-8")
        self.assertIn("docs/JARVIS-CIVILIZATION-SCALE-MASTER-ROADMAP.md", text)
        self.assertIn("advances the civilization-scale phase order", text)
        self.assertIn("event truth is becoming stronger", text)
        self.assertIn("better preserves roadmap sequencing", text)

    def test_blockers_remove_old_realtime_audio_item(self) -> None:
        text = (ROOT / "docs/blockers.md").read_text(encoding="utf-8")
        self.assertNotIn("Realtime reply audio is not yet a single full-duplex speech session.", text)
        self.assertIn("Wake word, speaker, and room inference are currently heuristic.", text)
        self.assertIn("The perception subsystem is profile-backed, but not yet wired to physical devices.", text)
        self.assertIn("The E14 deployment footprint is defined, but it is not yet applied to household hardware.", text)


if __name__ == "__main__":
    unittest.main()
