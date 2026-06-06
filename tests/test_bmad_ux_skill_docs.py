import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BMadUxSkillDocsTests(unittest.TestCase):
    def test_bmad_ux_skill_is_consolidated(self) -> None:
        skill = (ROOT / ".agents/skills/bmad-ux/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("name: bmad-ux", skill)
        self.assertIn("Plan UX patterns and design specifications.", skill)
        self.assertIn("# BMad UX", skill)
        self.assertIn("## The DESIGN.md spine", skill)
        self.assertIn("## The EXPERIENCE.md spine", skill)
        self.assertIn("## Discovery", skill)
        self.assertIn("## Reviewer Gate", skill)
        self.assertIn("## Finalize", skill)
        self.assertIn("references/headless.md", skill)
        self.assertIn("references/validate.md", skill)

    def test_bmad_ux_customize_surface_points_at_examples_and_tools(self) -> None:
        config = (ROOT / ".agents/skills/bmad-ux/customize.toml").read_text(
            encoding="utf-8"
        )
        self.assertIn("design_md_examples = [", config)
        self.assertIn("experience_md_examples = [", config)
        self.assertIn("design_handoffs = [", config)
        self.assertIn('validation_report_template = "assets/validation-report-template.html"', config)
        self.assertIn('ux_output_path = "{planning_artifacts}/ux-designs"', config)
        self.assertIn("creative_tools = [", config)
        self.assertIn("doc_standards = [", config)

    def test_bmad_ux_assets_and_references_exist(self) -> None:
        expected = [
            ".agents/skills/bmad-ux/assets/color-themes.md",
            ".agents/skills/bmad-ux/assets/design-directions.md",
            ".agents/skills/bmad-ux/assets/design-example-editorial.md",
            ".agents/skills/bmad-ux/assets/design-example-mobile.md",
            ".agents/skills/bmad-ux/assets/design-example-shadcn.md",
            ".agents/skills/bmad-ux/assets/excalidraw-wireframe.md",
            ".agents/skills/bmad-ux/assets/experience-example-mobile.md",
            ".agents/skills/bmad-ux/assets/experience-example-shadcn.md",
            ".agents/skills/bmad-ux/assets/headless-schemas.md",
            ".agents/skills/bmad-ux/assets/key-screens.md",
            ".agents/skills/bmad-ux/assets/validation-report-template.html",
            ".agents/skills/bmad-ux/references/creative-tools.md",
            ".agents/skills/bmad-ux/references/design-md-spec.md",
            ".agents/skills/bmad-ux/references/headless.md",
            ".agents/skills/bmad-ux/references/validate.md",
        ]
        for rel in expected:
            self.assertTrue((ROOT / rel).exists(), rel)

    def test_legacy_create_ux_design_workflow_files_are_removed(self) -> None:
        removed = [
            ".agents/skills/bmad-create-ux-design/SKILL.md",
            ".agents/skills/bmad-create-ux-design/customize.toml",
            ".agents/skills/bmad-create-ux-design/steps/step-01-init.md",
            ".agents/skills/bmad-create-ux-design/steps/step-07-defining-experience.md",
            ".agents/skills/bmad-create-ux-design/steps/step-14-complete.md",
            ".agents/skills/bmad-create-ux-design/ux-design-template.md",
        ]
        for rel in removed:
            self.assertFalse((ROOT / rel).exists(), rel)


if __name__ == "__main__":
    unittest.main()
