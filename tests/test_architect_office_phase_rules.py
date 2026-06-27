from __future__ import annotations

import unittest
from pathlib import Path

from architect_office.canon_registry import assess_canon_usage, load_canon_registry
from architect_office.git_inspector import inspect_git_state
from architect_office.phase_rules import evaluate_phase_scope


class ArchitectOfficePhaseRuleTests(unittest.TestCase):
    def test_canon_registry_includes_chris_context_canon(self) -> None:
        registry = load_canon_registry(Path(__file__).resolve().parents[1])

        self.assertIn("docs/CHRIS-CONTEXT-CANON.md", registry.canon_paths)

    def test_phase_rules_flag_obsidian_during_phase1(self) -> None:
        scope = evaluate_phase_scope(
            "phase-1-companion-spine",
            ["This pass adds Obsidian integration and a local data format migration."],
        )

        self.assertIn("obsidian integration", scope.forbidden_hits)
        self.assertIn("local data format migration", scope.forbidden_hits)

    def test_phase_rules_allow_runtime_health_work_in_phase0a(self) -> None:
        scope = evaluate_phase_scope(
            "phase-0a-runtime-health",
            ["This task is focused on runtime health and smoke validation."],
        )

        self.assertIn("runtime health", scope.allowed_hits)
        self.assertIn("smoke validation", scope.allowed_hits)
        self.assertEqual(scope.forbidden_hits, [])

    def test_dirty_git_status_can_be_represented_without_repo_mutation(self) -> None:
        responses = {
            ("git", "branch", "--show-current"): "phase-1-companion-spine\n",
            ("git", "rev-parse", "--short", "HEAD"): "deadbee\n",
            ("git", "status", "--short"): " M jarvis/runtime.py\n?? notes.txt\n",
        }

        def runner(cmd: list[str], cwd: Path) -> str:
            return responses[tuple(cmd)]

        inspection = inspect_git_state(
            repo_root=Path("/tmp/fake"),
            expected_branch="phase-1-companion-spine",
            runner=runner,
        )

        self.assertFalse(inspection.is_clean)
        self.assertTrue(inspection.branch_matches_phase)
        self.assertEqual(inspection.status_lines, [" M jarvis/runtime.py", "?? notes.txt"])

    def test_report_text_with_therapist_dashboard_and_fake_capability_language_produces_warnings(self) -> None:
        registry = load_canon_registry(Path(__file__).resolve().parents[1])
        canon = assess_canon_usage(
            registry,
            (
                "As an AI assistant, your concern is valid. "
                "I opened the dashboard and Obsidian says the agents did the work."
            ),
        )

        self.assertIn("therapist language risk detected.", canon.warnings)
        self.assertIn("dashboard-first behavior risk detected.", canon.warnings)
        self.assertIn("fake capability language requires evidence.", canon.warnings)
        self.assertIn("obsidian claims without retrieval evidence risk detected.", canon.warnings)


if __name__ == "__main__":
    unittest.main()
