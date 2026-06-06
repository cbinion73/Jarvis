import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BMadInvestigateSkillDocsTests(unittest.TestCase):
    def test_bmad_investigate_skill_has_forensic_workflow_contract(self) -> None:
        skill = (ROOT / ".agents/skills/bmad-investigate/SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("name: bmad-investigate", skill)
        self.assertIn("Forensic case investigation with evidence-graded findings", skill)
        self.assertIn("# Investigate", skill)
        self.assertIn("## Principles", skill)
        self.assertIn("## On Activation", skill)
        self.assertIn("### Outcome 3: Cause is reasoned about with discipline", skill)
        self.assertIn("### Outcome 5: Report is finalized and the hand-off is clean", skill)
        self.assertIn("{workflow.case_file_template}", skill)

    def test_bmad_investigate_customize_surface_points_at_case_file_template(self) -> None:
        config = (ROOT / ".agents/skills/bmad-investigate/customize.toml").read_text(
            encoding="utf-8"
        )
        self.assertIn("activation_steps_prepend = []", config)
        self.assertIn("activation_steps_append = []", config)
        self.assertIn("persistent_facts = [", config)
        self.assertIn('case_file_template = "references/case-file-template.md"', config)
        self.assertIn('case_file_subdir = "investigations"', config)
        self.assertIn('case_file_filename = "{slug}-investigation.md"', config)
        self.assertIn('on_complete = ""', config)

    def test_bmad_investigate_case_file_template_exists(self) -> None:
        template = (
            ROOT / ".agents/skills/bmad-investigate/references/case-file-template.md"
        ).read_text(encoding="utf-8")
        self.assertIn("# Investigation: {title}", template)
        self.assertIn("## Hand-off Brief", template)
        self.assertIn("## Evidence Inventory", template)
        self.assertIn("## Investigation Backlog", template)
        self.assertIn("## Confirmed Findings", template)
        self.assertIn("## Hypothesized Paths", template)
        self.assertIn("## Source Code Trace", template)
        self.assertIn("## Follow-up: {date}", template)


if __name__ == "__main__":
    unittest.main()
