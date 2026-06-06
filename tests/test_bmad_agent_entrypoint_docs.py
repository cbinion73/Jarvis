import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BMadAgentEntrypointDocsTests(unittest.TestCase):
    def test_named_agents_share_activation_completion_gate_and_menu_dispatch_contract(self) -> None:
        expected = [
            ".agents/skills/bmad-agent-analyst/SKILL.md",
            ".agents/skills/bmad-agent-architect/SKILL.md",
            ".agents/skills/bmad-agent-dev/SKILL.md",
            ".agents/skills/bmad-agent-pm/SKILL.md",
            ".agents/skills/bmad-agent-tech-writer/SKILL.md",
            ".agents/skills/bmad-agent-ux-designer/SKILL.md",
        ]
        for rel in expected:
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertIn("Activation is complete.", text, rel)
            self.assertIn("confirm every entry was executed in order", text, rel)
            self.assertIn("render `{agent.menu}` as a numbered table", text, rel)
            self.assertIn("Only pause to clarify when two or more items are genuinely close", text, rel)
            self.assertIn("they can invoke the `bmad-help` skill at any time for advice", text, rel)

    def test_dev_customize_adds_investigation_route(self) -> None:
        config = (ROOT / ".agents/skills/bmad-agent-dev/customize.toml").read_text(
            encoding="utf-8"
        )
        self.assertIn('code = "IN"', config)
        self.assertIn('skill = "bmad-investigate"', config)

    def test_pm_customize_consolidates_legacy_prd_routes(self) -> None:
        config = (ROOT / ".agents/skills/bmad-agent-pm/customize.toml").read_text(
            encoding="utf-8"
        )
        self.assertIn('code = "PRD"', config)
        self.assertIn('skill = "bmad-prd"', config)
        self.assertNotIn('skill = "bmad-create-prd"', config)
        self.assertNotIn('skill = "bmad-edit-prd"', config)
        self.assertNotIn('skill = "bmad-validate-prd"', config)

    def test_ux_customize_routes_to_consolidated_bmad_ux_skill(self) -> None:
        config = (
            ROOT / ".agents/skills/bmad-agent-ux-designer/customize.toml"
        ).read_text(encoding="utf-8")
        self.assertIn('code = "CU"', config)
        self.assertIn('skill = "bmad-ux"', config)
        self.assertNotIn('skill = "bmad-create-ux-design"', config)


if __name__ == "__main__":
    unittest.main()
