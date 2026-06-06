import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BMadDevStoryDocsTests(unittest.TestCase):
    def test_dev_story_tracks_baseline_commit_and_project_context(self) -> None:
        skill = (ROOT / ".agents/skills/bmad-dev-story/SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("YAML frontmatter `baseline_commit`", skill)
        self.assertIn("`project_context` = `**/project-context.md` (load if exists)", skill)
        self.assertIn("If story file YAML frontmatter already contains `baseline_commit`, preserve the existing value and do not overwrite it", skill)
        self.assertIn("Run `git rev-parse HEAD` to capture current commit into {{baseline_commit}}", skill)
        self.assertIn("If story file has no YAML frontmatter, create frontmatter at the top containing only `baseline_commit: {{baseline_commit}}`", skill)

    def test_dev_story_resume_logic_handles_review_continuations(self) -> None:
        skill = (ROOT / ".agents/skills/bmad-dev-story/SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Set {{current_status}} to development_status[{{story_key}}]", skill)
        self.assertIn("Set {{current_status}} to the story file Status section value", skill)
        self.assertIn("{{current_status}} == 'ready-for-dev' OR (review_continuation == true AND {{current_status}} != 'in-progress')", skill)
        self.assertIn("Status updated: {{current_status}} → in-progress", skill)
        self.assertIn("{{current_status}} is neither ready-for-dev nor in-progress", skill)


if __name__ == "__main__":
    unittest.main()
