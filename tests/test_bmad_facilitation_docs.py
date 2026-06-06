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
        workflow = (ROOT / ".agents/skills/bmad-brainstorming/workflow.md").read_text(
            encoding="utf-8"
        )
        step = (
            ROOT / ".agents/skills/bmad-brainstorming/steps/step-03-technique-execution.md"
        ).read_text(encoding="utf-8")

        self.assertIn("100+ collaboratively developed ideas", workflow)
        self.assertIn("This is a session goal, not a request to generate a large list.", workflow)
        self.assertIn("AIM FOR 100+ COLLABORATIVE IDEAS", step)
        self.assertIn("do not batch-generate ideas to satisfy the count", step)
        self.assertIn("Present at most one new idea, provocation, or angle before asking for user input", step)
        self.assertIn("The goal is quantity through collaboration, not a generated list.", step)
        self.assertIn("Batch-generating idea lists instead of facilitating dialogue", step)


if __name__ == "__main__":
    unittest.main()
