import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BMadDistillatorRetiredTests(unittest.TestCase):
    def test_legacy_bmad_distillator_workflow_files_are_removed(self) -> None:
        removed = [
            ".agents/skills/bmad-distillator/SKILL.md",
            ".agents/skills/bmad-distillator/agents/distillate-compressor.md",
            ".agents/skills/bmad-distillator/agents/round-trip-reconstructor.md",
            ".agents/skills/bmad-distillator/resources/compression-rules.md",
            ".agents/skills/bmad-distillator/resources/distillate-format-reference.md",
            ".agents/skills/bmad-distillator/resources/splitting-strategy.md",
            ".agents/skills/bmad-distillator/scripts/analyze_sources.py",
            ".agents/skills/bmad-distillator/scripts/tests/test_analyze_sources.py",
        ]
        for rel in removed:
            self.assertFalse((ROOT / rel).exists(), rel)


if __name__ == "__main__":
    unittest.main()
