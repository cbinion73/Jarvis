import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BMadWorkflowNavigationDocsTests(unittest.TestCase):
    def test_bmad_help_uses_preceded_by_and_followed_by_catalog_language(self) -> None:
        skill = (ROOT / ".agents/skills/bmad-help/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("module,skill,display-name,menu-code,description,action,args,phase,preceded-by,followed-by,required,output-location,outputs", skill)
        self.assertIn("**Sequencing** determines recommended ordering", skill)
        self.assertIn("`preceded-by`", skill)
        self.assertIn("`followed-by`", skill)
        self.assertIn("[PR] PRD", skill)
        self.assertIn("`bmad-prd`", skill)

    def test_bmad_prfaq_manifest_and_activation_language_match_new_schema(self) -> None:
        skill = (ROOT / ".agents/skills/bmad-prfaq/SKILL.md").read_text(encoding="utf-8")
        manifest = (ROOT / ".agents/skills/bmad-prfaq/bmad-manifest.json").read_text(
            encoding="utf-8"
        )
        self.assertIn("confirm every entry was executed in order", skill)
        self.assertIn("\"preceded-by\": [\"brainstorming\", \"perform-research\"]", manifest)
        self.assertIn("\"followed-by\": [\"create-prd\"]", manifest)
        self.assertNotIn("\"after\":", manifest)
        self.assertNotIn("\"before\":", manifest)


if __name__ == "__main__":
    unittest.main()
