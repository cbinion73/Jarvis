from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from architect_office.git_inspector import GitInspection
from architect_office.phase_rules import evaluate_phase_scope
from architect_office.report_checker import REQUIRED_SECTIONS, check_report
from architect_office.review_writer import build_review


class ArchitectOfficeReportCheckerTests(unittest.TestCase):
    def test_report_checker_detects_missing_required_sections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "report.md"
            path.write_text("# Build Office Report\n\n## A. Start State\n", encoding="utf-8")

            result = check_report(path)

        self.assertFalse(result.complete)
        self.assertEqual(result.present_sections, ["## A. Start State"])
        self.assertEqual(result.missing_sections, list(REQUIRED_SECTIONS[1:]))

    def test_review_writer_outputs_required_sections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "report.md"
            path.write_text("\n\n".join(REQUIRED_SECTIONS), encoding="utf-8")
            report = check_report(path)

        git = GitInspection(
            repo_root=Path("/tmp/fake"),
            branch="phase-0a-runtime-health",
            latest_commit="abc1234",
            status_lines=[],
            is_clean=True,
            branch_matches_phase=True,
            has_uncommitted_changes=False,
        )
        scope = evaluate_phase_scope("phase-0a-runtime-health", [report.text])

        review = build_review(
            phase="phase-0a-runtime-health",
            git=git,
            report=report,
            scope=scope,
        )

        self.assertIn("## A. Decision", review.markdown)
        self.assertIn("## B. Process Check", review.markdown)
        self.assertIn("## C. Phase Scope", review.markdown)
        self.assertIn("## D. Evidence Review", review.markdown)
        self.assertIn("## E. Truth Contract", review.markdown)
        self.assertIn("## F. Risks", review.markdown)
        self.assertIn("## G. Next Action", review.markdown)


if __name__ == "__main__":
    unittest.main()
