import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BMadPrdSkillDocsTests(unittest.TestCase):
    def test_bmad_prd_skill_exists_with_create_update_validate_intents(self) -> None:
        skill = (ROOT / ".agents/skills/bmad-prd/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("name: bmad-prd", skill)
        self.assertIn("Create, update, or validate a PRD.", skill)
        self.assertIn("Intent Modes", skill)
        self.assertIn("**Create.**", skill)
        self.assertIn("**Update.**", skill)
        self.assertIn("**Validate**", skill)
        self.assertIn("references/headless.md", skill)
        self.assertIn("references/validate.md", skill)

    def test_bmad_prd_customize_surface_exposes_new_templates(self) -> None:
        config = (ROOT / ".agents/skills/bmad-prd/customize.toml").read_text(
            encoding="utf-8"
        )
        self.assertIn('prd_template = "assets/prd-template.md"', config)
        self.assertIn(
            'validation_checklist_template = "assets/prd-validation-checklist.md"',
            config,
        )
        self.assertIn(
            'validation_report_template = "assets/validation-report-template.html"',
            config,
        )
        self.assertIn("doc_standards = [", config)
        self.assertIn('external_sources = []', config)
        self.assertIn('external_handoffs = []', config)

    def test_bmad_prd_headless_reference_exists(self) -> None:
        headless = (ROOT / ".agents/skills/bmad-prd/references/headless.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("# Headless Mode", headless)
        self.assertIn("Do not ask.", headless)
        self.assertIn('status: "partial"', headless)
        self.assertIn("validation-report.html", headless)
        self.assertIn("offer_to_update", headless)

    def test_legacy_prd_skills_are_deprecation_shims(self) -> None:
        checks = {
            ".agents/skills/bmad-create-prd/SKILL.md": "create intent",
            ".agents/skills/bmad-edit-prd/SKILL.md": "update intent",
            ".agents/skills/bmad-validate-prd/SKILL.md": "validate intent",
        }
        for rel, intent in checks.items():
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertIn("DEPRECATED", text)
            self.assertIn("forwards to `bmad-prd`", text)
            self.assertIn(intent, text)
            self.assertIn("Invoke `bmad-prd`", text)

    def test_legacy_prd_workflow_payload_files_are_removed(self) -> None:
        removed = [
            ".agents/skills/bmad-create-prd/data/domain-complexity.csv",
            ".agents/skills/bmad-create-prd/data/prd-purpose.md",
            ".agents/skills/bmad-create-prd/data/project-types.csv",
            ".agents/skills/bmad-create-prd/steps-c/step-01-init.md",
            ".agents/skills/bmad-create-prd/steps-c/step-12-complete.md",
            ".agents/skills/bmad-create-prd/templates/prd-template.md",
            ".agents/skills/bmad-edit-prd/data/prd-purpose.md",
            ".agents/skills/bmad-edit-prd/steps-e/step-e-01-discovery.md",
            ".agents/skills/bmad-edit-prd/steps-e/step-e-04-complete.md",
            ".agents/skills/bmad-validate-prd/data/domain-complexity.csv",
            ".agents/skills/bmad-validate-prd/data/project-types.csv",
            ".agents/skills/bmad-validate-prd/steps-v/step-v-01-discovery.md",
            ".agents/skills/bmad-validate-prd/steps-v/step-v-13-report-complete.md",
        ]
        for rel in removed:
            self.assertFalse((ROOT / rel).exists(), rel)


if __name__ == "__main__":
    unittest.main()
