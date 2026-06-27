from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from architect_office.canon_registry import assess_canon_usage, load_canon_registry
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
        registry = load_canon_registry(Path(__file__).resolve().parents[1])
        canon = assess_canon_usage(registry, report.text)

        review = build_review(
            phase="phase-0a-runtime-health",
            git=git,
            report=report,
            scope=scope,
            canon=canon,
        )

        self.assertIn("## Decision", review.markdown)
        self.assertIn("## Scope Checked", review.markdown)
        self.assertIn("## Canon Sources Checked", review.markdown)
        self.assertIn("## Chris Canon Sources Checked", review.markdown)
        self.assertIn("docs/CHRIS-CONTEXT-CANON.md", review.markdown)
        self.assertIn("## Non-Canon References Detected", review.markdown)
        self.assertIn("## Evidence Reviewed", review.markdown)
        self.assertIn("## Findings", review.markdown)
        self.assertIn("## Risks", review.markdown)
        self.assertIn("## Required Follow-up", review.markdown)
        self.assertIn("## Final Judgment", review.markdown)

    def test_missing_chris_context_creates_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docs = root / "docs"
            docs.mkdir()
            (docs / "CANON-REGISTRY.md").write_text(
                "\n".join(
                    [
                        "# Canon Registry",
                        "- `docs/CHRIS-INTENT-CANON.md` [canon] missing",
                        "- `docs/PHASE-GATES.md` [canon] active phase gates",
                        "- `docs/ARCHITECTURE-OFFICE-PROTOCOL.md` [canon] protocol",
                        "- `docs/BUILD-OFFICE-PROTOCOL.md` [canon] protocol",
                    ]
                ),
                encoding="utf-8",
            )

            registry = load_canon_registry(root)
            canon = assess_canon_usage(registry, "No special references.")

        self.assertIn("Cannot fully evaluate product fit because Chris canon is missing.", canon.warnings)

    def test_non_canon_binding_reference_is_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docs = root / "docs"
            docs.mkdir(parents=True)
            (docs / "CHRIS-CONTEXT-CANON.md").write_text("# Chris Context Canon\n", encoding="utf-8")
            (docs / "CANON-REGISTRY.md").write_text(
                "\n".join(
                    [
                        "# Canon Registry",
                        "- `docs/CHRIS-CONTEXT-CANON.md` [canon] context",
                        "- `docs/archive/old-roadmap.md` [deprecated] old roadmap",
                    ]
                ),
                encoding="utf-8",
            )

            registry = load_canon_registry(root)
            canon = assess_canon_usage(
                registry,
                "The authoritative source of truth is old-roadmap.md and it governs this change.",
            )

        self.assertIn("docs/archive/old-roadmap.md", canon.non_canon_references)

    def test_stale_override_reference_is_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docs = root / "docs" / "archive"
            docs.mkdir(parents=True)
            (root / "docs" / "CHRIS-CONTEXT-CANON.md").write_text("# Chris Context Canon\n", encoding="utf-8")
            (root / "docs" / "CANON-REGISTRY.md").write_text(
                "\n".join(
                    [
                        "# Canon Registry",
                        "- `docs/CHRIS-CONTEXT-CANON.md` [canon] context",
                        "- `docs/archive/stale.md` [deprecated] stale roadmap",
                    ]
                ),
                encoding="utf-8",
            )

            registry = load_canon_registry(root)
            canon = assess_canon_usage(
                registry,
                "The authoritative stale.md source overrides the phase gates.",
            )

        self.assertIn("docs/archive/stale.md", canon.stale_override_references)
        self.assertIn("Stale docs appear to override active phase gates.", canon.warnings)

    def test_unsupported_capability_claim_without_proof_is_flagged(self) -> None:
        registry = load_canon_registry(Path(__file__).resolve().parents[1])
        canon = assess_canon_usage(
            registry,
            "I searched, I found, and I opened the required runtime surfaces.",
        )
        self.assertTrue(canon.unsupported_capability_claims)
        self.assertIn("Build Office makes capability claims without proof.", canon.warnings)


if __name__ == "__main__":
    unittest.main()
