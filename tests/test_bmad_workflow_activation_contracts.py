import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BMadWorkflowActivationContractsTests(unittest.TestCase):
    def test_workflow_skills_share_activation_completion_gate(self) -> None:
        expected = [
            ".agents/skills/bmad-check-implementation-readiness/SKILL.md",
            ".agents/skills/bmad-checkpoint-preview/SKILL.md",
            ".agents/skills/bmad-code-review/SKILL.md",
            ".agents/skills/bmad-correct-course/SKILL.md",
            ".agents/skills/bmad-document-project/SKILL.md",
            ".agents/skills/bmad-domain-research/SKILL.md",
            ".agents/skills/bmad-generate-project-context/SKILL.md",
            ".agents/skills/bmad-market-research/SKILL.md",
            ".agents/skills/bmad-qa-generate-e2e-tests/SKILL.md",
            ".agents/skills/bmad-retrospective/SKILL.md",
            ".agents/skills/bmad-sprint-planning/SKILL.md",
            ".agents/skills/bmad-sprint-status/SKILL.md",
            ".agents/skills/bmad-technical-research/SKILL.md",
        ]
        for rel in expected:
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertIn("Activation is complete.", text, rel)
            self.assertIn("confirm every entry was executed in order", text, rel)
            self.assertIn("Do not begin the main workflow until all activation steps have been completed.", text, rel)
            self.assertIn("If the script fails", text, rel)
            self.assertIn("base → team → user order", text, rel)

    def test_authoring_skills_share_activation_completion_gate(self) -> None:
        expected = [
            ".agents/skills/bmad-create-architecture/SKILL.md",
            ".agents/skills/bmad-create-epics-and-stories/SKILL.md",
            ".agents/skills/bmad-create-story/SKILL.md",
            ".agents/skills/bmad-quick-dev/SKILL.md",
        ]
        for rel in expected:
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertIn("Activation is complete.", text, rel)
            self.assertIn("confirm every entry was executed in order", text, rel)
            self.assertIn("Do not begin the main workflow until all activation steps have been completed.", text, rel)
            self.assertIn("If the script fails", text, rel)
            self.assertIn("base → team → user order", text, rel)


if __name__ == "__main__":
    unittest.main()
