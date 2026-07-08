import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class Level9GovernanceDocsTests(unittest.TestCase):
    # test_branch_control_reflects_helper_clone_topology and
    # test_branch_integration_rubric_mentions_roadmap_order were removed
    # 2026-07-08: their target docs (docs/level9-branch-control.md,
    # docs/branch-integration-rubric.md) were archived to
    # docs/archive/2026-07-doc-consolidation/ as part of the vision/doc
    # consolidation described in docs/README.md. Both asserted only on
    # doc prose, not runtime behavior.

    def test_blockers_remove_old_realtime_audio_item(self) -> None:
        text = (ROOT / "docs/blockers.md").read_text(encoding="utf-8")
        self.assertNotIn("Realtime reply audio is not yet a single full-duplex speech session.", text)
        self.assertIn("Wake word, speaker, and room inference are currently heuristic.", text)
        self.assertIn("The perception subsystem is profile-backed, but not yet wired to physical devices.", text)
        self.assertIn("The E14 deployment footprint is defined, but it is not yet applied to household hardware.", text)


if __name__ == "__main__":
    unittest.main()
