import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BMadSpecSkillDocsTests(unittest.TestCase):
    def test_bmad_spec_skill_exists_with_kernel_contract_language(self) -> None:
        skill = (ROOT / ".agents/skills/bmad-spec/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("name: bmad-spec", skill)
        self.assertIn("canonical, preservation-validated machine contract", skill)
        self.assertIn("# BMad Spec", skill)
        self.assertIn("## Workspace", skill)
        self.assertIn("## The Operation", skill)
        self.assertIn("## Companions", skill)
        self.assertIn("## Spec Law", skill)
        self.assertIn("## Self-Validate", skill)
        self.assertIn("{workflow.spec_template}", skill)

    def test_bmad_spec_customize_surface_points_at_template(self) -> None:
        config = (ROOT / ".agents/skills/bmad-spec/customize.toml").read_text(
            encoding="utf-8"
        )
        self.assertIn('spec_template = "assets/spec-template.md"', config)
        self.assertIn('spec_output_path = "{output_folder}/specs"', config)
        self.assertIn("persistent_facts = [", config)
        self.assertIn("on_complete = \"\"", config)

    def test_bmad_spec_assets_exist(self) -> None:
        template = (ROOT / ".agents/skills/bmad-spec/assets/spec-template.md").read_text(
            encoding="utf-8"
        )
        schemas = (
            ROOT / ".agents/skills/bmad-spec/assets/headless-schemas.md"
        ).read_text(encoding="utf-8")
        self.assertIn("# {Spec Title}", template)
        self.assertIn("## Why", template)
        self.assertIn("## Capabilities", template)
        self.assertIn("## Constraints", template)
        self.assertIn("## Success signal", template)
        self.assertIn("# Headless JSON Response", schemas)
        self.assertIn("\"status\": \"complete\"", schemas)
        self.assertIn("\"status\": \"blocked\"", schemas)


if __name__ == "__main__":
    unittest.main()
