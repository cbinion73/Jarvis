import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BMadProductBriefSkillDocsTests(unittest.TestCase):
    def test_brief_skill_is_consolidated_into_single_surface(self) -> None:
        skill = (
            ROOT / ".agents/skills/bmad-product-brief/SKILL.md"
        ).read_text(encoding="utf-8")
        self.assertIn("name: bmad-product-brief", skill)
        self.assertIn("Create, update, or validate a product brief.", skill)
        self.assertIn("## Intent Operating Modes", skill)
        self.assertIn("## Headless Mode", skill)
        self.assertIn("## Discovery", skill)
        self.assertIn("{workflow.brief_template}", skill)
        self.assertIn("{workflow.external_handoffs}", skill)

    def test_brief_customize_surface_points_at_new_asset_template(self) -> None:
        config = (
            ROOT / ".agents/skills/bmad-product-brief/customize.toml"
        ).read_text(encoding="utf-8")
        self.assertIn('brief_template = "assets/brief-template.md"', config)
        self.assertIn('brief_output_path = "{planning_artifacts}/briefs"', config)
        self.assertIn("doc_standards = [", config)
        self.assertIn("external_sources = []", config)
        self.assertIn("external_handoffs = []", config)

    def test_brief_template_asset_exists(self) -> None:
        template = (
            ROOT / ".agents/skills/bmad-product-brief/assets/brief-template.md"
        ).read_text(encoding="utf-8")
        self.assertIn("# Product Brief Template", template)
        self.assertIn("## Default Structure", template)
        self.assertIn("## Executive Summary", template)
        self.assertIn("## The Problem", template)
        self.assertIn("## Vision", template)

    def test_legacy_product_brief_workflow_files_are_removed(self) -> None:
        removed = [
            ".agents/skills/bmad-product-brief/agents/artifact-analyzer.md",
            ".agents/skills/bmad-product-brief/agents/opportunity-reviewer.md",
            ".agents/skills/bmad-product-brief/agents/skeptic-reviewer.md",
            ".agents/skills/bmad-product-brief/agents/web-researcher.md",
            ".agents/skills/bmad-product-brief/bmad-manifest.json",
            ".agents/skills/bmad-product-brief/prompts/contextual-discovery.md",
            ".agents/skills/bmad-product-brief/prompts/draft-and-review.md",
            ".agents/skills/bmad-product-brief/prompts/finalize.md",
            ".agents/skills/bmad-product-brief/prompts/guided-elicitation.md",
            ".agents/skills/bmad-product-brief/resources/brief-template.md",
        ]
        for rel in removed:
            self.assertFalse((ROOT / rel).exists(), rel)


if __name__ == "__main__":
    unittest.main()
