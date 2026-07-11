from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from jarvis.build_office import BuildOffice, scopes_overlap


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, text=True, capture_output=True, check=True
    ).stdout.strip()


class BuildOfficeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "JARVIS"
        self.root.mkdir()
        _git(self.root, "init", "-b", "main")
        _git(self.root, "config", "user.email", "build-office@example.test")
        _git(self.root, "config", "user.name", "Build Office Test")
        (self.root / "README.md").write_text("# Test\n", encoding="utf-8")
        _git(self.root, "add", "README.md")
        _git(self.root, "commit", "-m", "baseline")
        self.office = BuildOffice(self.root)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_scope_overlap_is_conservative(self) -> None:
        self.assertTrue(scopes_overlap(["jarvis/**"], ["jarvis/runtime.py"]))
        self.assertTrue(scopes_overlap(["**"], ["tests/**"]))
        self.assertFalse(scopes_overlap(["jarvis/**"], ["docs/**"]))

    def test_owned_scope_rejects_nested_symlink_alias(self) -> None:
        (self.root / "jarvis").mkdir()
        (self.root / "vendor").mkdir()
        (self.root / "vendor" / "link").symlink_to(self.root / "jarvis", target_is_directory=True)
        _git(self.root, "add", "vendor/link")
        _git(self.root, "commit", "-m", "add symlink fixture")
        with self.assertRaisesRegex(ValueError, "traverse a symlink"):
            self.office.init_mission(
                request="Reject aliased scope",
                mission_id="bo-symlink",
                owned_paths=["vendor/link/**"],
                provision=False,
            )

    @patch("jarvis.build_office.shutil.which")
    def test_doctor_reports_cli_and_git_truth(self, which) -> None:
        which.side_effect = lambda command: f"/usr/bin/{command}"
        result = self.office.doctor()
        self.assertTrue(result["ok"])
        self.assertTrue(result["repo_clean"])
        self.assertEqual(Path(result["repo_root"]).resolve(), self.root.resolve())

    def test_medium_risk_mission_routes_codex_implementation_and_claude_review(self) -> None:
        mission = self.office.init_mission(
            request="Implement a bounded feature",
            risk="medium",
            mission_id="bo-medium",
            provision=False,
        )
        assignments = {item["assignment_id"]: item for item in mission["assignments"]}
        self.assertEqual(set(assignments), {"codex-implementation", "claude-review"})
        self.assertTrue(assignments["codex-implementation"]["writable"])
        self.assertFalse(assignments["claude-review"]["writable"])
        self.assertTrue(mission["requires_cross_review"])

    def test_high_risk_adds_claude_analysis_before_implementation(self) -> None:
        mission = self.office.init_mission(
            request="Plan a risky migration",
            risk="high",
            mission_id="bo-high",
            provision=False,
        )
        duties = [item["duty"] for item in mission["assignments"]]
        self.assertEqual(duties, ["analysis", "implementation", "review"])

    def test_implementer_is_configurable_and_reviewer_is_always_other_provider(self) -> None:
        mission = self.office.init_mission(
            request="Let Claude implement this bounded slice",
            risk="medium",
            mission_id="bo-claude-implements",
            implementer="claude",
            owned_paths=["docs/**"],
            provision=False,
        )
        assignments = {item["assignment_id"]: item for item in mission["assignments"]}
        self.assertEqual(set(assignments), {"claude-implementation", "codex-review"})
        self.assertEqual(assignments["claude-implementation"]["owned_paths"], ["docs/**"])
        self.assertEqual(mission["routing"], {"implementer": "claude", "reviewer": "codex"})

    def test_dirty_main_blocks_mission_intake(self) -> None:
        (self.root / "dirty.txt").write_text("dirty", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "clean"):
            self.office.init_mission(request="Do work", provision=False)

    def test_critical_dispatch_requires_explicit_human_approval(self) -> None:
        mission = self.office.init_mission(
            request="Perform critical migration",
            risk="critical",
            mission_id="bo-critical",
            provision=False,
        )
        with self.assertRaisesRegex(RuntimeError, "dispatch approval"):
            self.office.dispatch(mission["mission_id"], "codex-implementation", dry_run=True)
        approval = self.office.approve_dispatch(mission["mission_id"], approved_by="Chris")
        dispatched = self.office.dispatch(
            mission["mission_id"], "codex-implementation", dry_run=True
        )
        self.assertTrue(approval["dispatch"])
        self.assertEqual(approval["dispatch_approved_by"], "Chris")
        self.assertTrue(dispatched["dry_run"])

    def test_writable_assignment_never_targets_main_checkout(self) -> None:
        mission = self.office.init_mission(
            request="Do work", mission_id="bo-main-target", provision=False
        )
        state = self.office.load_mission(mission["mission_id"])
        assignment = self.office._find_assignment(state, "codex-implementation")
        assignment["worktree"] = str(self.root)
        self.office.save_mission(state, event="test-modified")
        with self.assertRaisesRegex(RuntimeError, "main checkout"):
            self.office.provision_assignment(mission["mission_id"], "codex-implementation")

    def test_real_dispatch_refuses_missing_worktree_instead_of_falling_back_to_main(self) -> None:
        mission = self.office.init_mission(
            request="Never fall back to main",
            mission_id="bo-no-fallback",
            provision=False,
        )
        with self.assertRaisesRegex(RuntimeError, "refusing to run in the main checkout"):
            self.office.dispatch(mission["mission_id"], "codex-implementation")

    def test_provision_creates_unique_branch_and_worktree_off_main(self) -> None:
        mission = self.office.init_mission(
            request="Provision isolated work",
            mission_id="bo-provision",
            provision=True,
        )
        assignment = self.office._find_assignment(mission, "codex-implementation")
        worktree = Path(assignment["worktree"])
        self.assertTrue(worktree.exists())
        self.assertNotEqual(worktree.resolve(), self.root.resolve())
        self.assertEqual(
            _git(worktree, "branch", "--show-current"),
            assignment["branch"],
        )

    def test_overlapping_active_leases_block_second_dispatch(self) -> None:
        first = self.office.init_mission(
            request="First change", mission_id="bo-first", provision=False
        )
        second = self.office.init_mission(
            request="Second change", mission_id="bo-second", provision=False
        )
        self.office.acquire_lease(first["mission_id"], "codex-implementation")
        with self.assertRaisesRegex(RuntimeError, "collision with bo-first"):
            self.office.acquire_lease(second["mission_id"], "codex-implementation")
        blocked = self.office.load_mission(second["mission_id"])
        assignment = self.office._find_assignment(blocked, "codex-implementation")
        self.assertEqual(assignment["status"], "blocked")
        self.assertIn("collision", assignment["evidence"])

    def test_dry_run_dispatch_returns_bounded_commands_without_running_models(self) -> None:
        mission = self.office.init_mission(
            request="Implement safely", mission_id="bo-dispatch", provision=False
        )
        codex = self.office.dispatch(
            mission["mission_id"], "codex-implementation", dry_run=True
        )
        claude = self.office.dispatch(
            mission["mission_id"], "claude-review", dry_run=True
        )
        self.assertEqual(codex["command"][:2], ["codex", "exec"])
        self.assertIn("workspace-write", codex["command"])
        self.assertEqual(claude["command"][:2], ["claude", "-p"])
        self.assertIn("plan", claude["command"])
        self.assertIn("Do not switch branches", codex["display_command"])

    def test_nonzero_model_exit_marks_assignment_failed_and_releases_lease(self) -> None:
        mission = self.office.init_mission(
            request="Exercise failure path",
            mission_id="bo-failure",
            provision=True,
        )
        completed = subprocess.CompletedProcess(
            args=["codex"], returncode=7, stdout="model failed", stderr="failure"
        )
        with patch("jarvis.build_office._run", return_value=completed):
            result = self.office.dispatch(mission["mission_id"], "codex-implementation")
        assignment = self.office._find_assignment(
            self.office.load_mission(mission["mission_id"]), "codex-implementation"
        )
        self.assertEqual(result["status"], "failed")
        self.assertEqual(assignment["status"], "failed")
        self.assertEqual(assignment["evidence"]["exit_code"], 7)
        self.assertIn("released_at", assignment["lease"])
        retried = self.office.retry_assignment(
            mission["mission_id"], "codex-implementation", approved_by="Chris"
        )
        self.assertEqual(retried["status"], "provisioned")
        self.assertEqual(retried["retry_count"], 1)
        self.assertEqual(retried["evidence_history"][0]["exit_code"], 7)
        second = self.office.dispatch(
            mission["mission_id"], "codex-implementation", dry_run=True
        )
        self.assertTrue(second["dry_run"])

    def test_cleanup_plan_refuses_dirty_agent_worktree(self) -> None:
        mission = self.office.init_mission(
            request="Prepare cleanup evidence",
            mission_id="bo-cleanup",
            provision=True,
        )
        state = self.office.load_mission(mission["mission_id"])
        assignment = self.office._find_assignment(state, "codex-implementation")
        assignment["status"] = "completed"
        self.office.save_mission(state, event="test-completed")
        worktree = Path(assignment["worktree"])
        (worktree / "uncommitted.txt").write_text("preserve me", encoding="utf-8")
        plan = self.office.cleanup_plan(mission["mission_id"])
        self.assertEqual(plan["removable_worktrees"], [])
        self.assertEqual(plan["blocked_worktrees"], [str(worktree)])
        self.assertFalse(plan["mutated_git"])

    def test_release_plan_blocks_missing_implementation_and_review(self) -> None:
        mission = self.office.init_mission(
            request="Implement safely", mission_id="bo-release-blocked", provision=False
        )
        plan = self.office.release_plan(mission["mission_id"])
        self.assertEqual(plan["status"], "blocked")
        self.assertIn("implementation incomplete", plan["reasons"])
        self.assertIn("independent review incomplete", plan["reasons"])
        self.assertFalse(plan["mutated_git"])

    def test_high_risk_release_also_requires_analysis(self) -> None:
        mission = self.office.init_mission(
            request="Risky change",
            risk="high",
            mission_id="bo-analysis-gate",
            provision=False,
        )
        state = self.office.load_mission(mission["mission_id"])
        for assignment in state["assignments"]:
            assignment["status"] = "completed" if assignment["duty"] != "analysis" else "planned"
            assignment["evidence"] = {
                "exit_code": 0,
                "commit": "different",
                "changed_files": ["jarvis/example.py"] if assignment["duty"] == "implementation" else [],
            }
        self.office.save_mission(state, event="test-partial")
        plan = self.office.release_plan(mission["mission_id"])
        self.assertIn("required analysis incomplete", plan["reasons"])

    def test_release_rejects_noop_implementation_and_scope_violation(self) -> None:
        mission = self.office.init_mission(
            request="Scoped change",
            mission_id="bo-scope-gate",
            owned_paths=["jarvis/**"],
            provision=False,
        )
        state = self.office.load_mission(mission["mission_id"])
        implementation = self.office._find_assignment(state, "codex-implementation")
        implementation["status"] = "completed"
        implementation["evidence"] = {
            "exit_code": 0,
            "commit": state["baseline_commit"],
            "changed_files": [],
            "scope_violations": ["docs/outside.md"],
        }
        review = self.office._find_assignment(state, "claude-review")
        review["status"] = "completed"
        review["evidence"] = {"exit_code": 0, "commit": "", "changed_files": []}
        self.office.save_mission(state, event="test-invalid-evidence")
        plan = self.office.release_plan(mission["mission_id"])
        self.assertIn("codex-implementation produced no changes", plan["reasons"])
        self.assertIn("codex-implementation changed files outside its lease", plan["reasons"])

    def test_expired_lease_requires_named_reclaimer(self) -> None:
        mission = self.office.init_mission(
            request="Recover stale work",
            mission_id="bo-expired",
            provision=False,
        )
        self.office.acquire_lease(mission["mission_id"], "codex-implementation")
        state = self.office.load_mission(mission["mission_id"])
        assignment = self.office._find_assignment(state, "codex-implementation")
        assignment["lease"]["expires_at"] = (
            datetime.now(timezone.utc) - timedelta(seconds=1)
        ).isoformat()
        self.office.save_mission(state, event="test-expired")
        reclaimed = self.office.reclaim_expired_lease(
            mission["mission_id"], "codex-implementation", approved_by="Chris"
        )
        self.assertEqual(reclaimed["status"], "expired")
        self.assertEqual(reclaimed["lease"]["reclaimed_by"], "Chris")

    def test_stale_revision_is_rejected(self) -> None:
        mission = self.office.init_mission(
            request="Protect revisions", mission_id="bo-cas", provision=False
        )
        stale = self.office.load_mission(mission["mission_id"])
        current = self.office.load_mission(mission["mission_id"])
        self.office.save_mission(current, event="first-update")
        with self.assertRaisesRegex(RuntimeError, "revision conflict"):
            self.office.save_mission(stale, event="stale-update")

    def test_release_plan_becomes_approval_required_only_with_cross_evidence(self) -> None:
        mission = self.office.init_mission(
            request="Implement safely", mission_id="bo-release-ready", provision=False
        )
        state = self.office.load_mission(mission["mission_id"])
        for assignment in state["assignments"]:
            assignment["status"] = "completed"
            assignment["evidence"] = {
                "exit_code": 0,
                "commit": "abc123",
                "changed_files": ["jarvis/example.py"] if assignment["duty"] == "implementation" else [],
            }
        self.office.save_mission(state, event="test-completed")
        plan = self.office.release_plan(mission["mission_id"])
        self.assertEqual(plan["status"], "approval-required")
        self.assertEqual(plan["reasons"], [])
        self.assertTrue(plan["approval_required"])
        self.assertFalse(plan["mutated_git"])

    def test_events_are_append_only_and_revision_increases(self) -> None:
        mission = self.office.init_mission(
            request="Trace this", mission_id="bo-events", provision=False
        )
        before = mission["revision"]
        self.office.acquire_lease(mission["mission_id"], "claude-review")
        after = self.office.load_mission(mission["mission_id"])
        events = [json.loads(line) for line in self.office.events_path.read_text().splitlines()]
        self.assertGreater(after["revision"], before)
        self.assertEqual([item["event"] for item in events], ["mission-created", "lease-acquired"])


if __name__ == "__main__":
    unittest.main()
