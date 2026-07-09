import csv
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BMadFacilitationDocsTests(unittest.TestCase):
    def test_customize_examples_point_at_consolidated_prd_surface(self) -> None:
        skill = (ROOT / ".agents/skills/bmad-customize/SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("One workflow only", skill)
        self.assertIn("`bmad-prd.toml`", skill)
        self.assertNotIn("`bmad-create-prd.toml`", skill)

    def test_advanced_elicitation_method_catalog_expands_core_and_risk_coverage(self) -> None:
        methods_path = ROOT / ".agents/skills/bmad-advanced-elicitation/methods.csv"
        with methods_path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))

        self.assertGreaterEqual(len(rows), 69)
        by_name = {row["method_name"]: row for row in rows}
        self.assertEqual(by_name["Problem Decomposition"]["category"], "core")
        self.assertEqual(by_name["Analogy Mapping"]["category"], "core")
        self.assertEqual(by_name["Steelmanning"]["category"], "core")
        self.assertEqual(by_name["Constraint Injection"]["category"], "creative")
        self.assertEqual(by_name["Source Triangulation"]["category"], "research")
        self.assertEqual(by_name["Assumption Audit"]["category"], "risk")
        self.assertEqual(by_name["Boundary & Edge Case Sweep"]["category"], "technical")

    def test_brainstorming_contract_requires_collaborative_not_batch_ideation(self) -> None:
        skill = (ROOT / ".agents/skills/bmad-brainstorming/SKILL.md").read_text(
            encoding="utf-8"
        )
        facilitator = (
            ROOT / ".agents/skills/bmad-brainstorming/references/mode-facilitator.md"
        ).read_text(encoding="utf-8")
        partner = (
            ROOT / ".agents/skills/bmad-brainstorming/references/mode-partner.md"
        ).read_text(encoding="utf-8")

        self.assertIn("Aim past 100 ideas; resist concluding.", skill)
        self.assertIn("You do not supply ideas.", facilitator)
        self.assertIn("never a source of ideas", facilitator)
        self.assertIn("collaborative, not extractive", partner)


if __name__ == "__main__":
    unittest.main()
