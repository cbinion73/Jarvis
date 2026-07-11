from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import jarvis.build_office as build_office_module
from jarvis.build_office import BuildOffice, scopes_overlap
from jarvis.office_charters import CHARTER_VERSION


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
        (self.root / "ARCHITECT-CONTRACT.md").write_text(
            "# Frozen Architect Contract\n\nImplement the bounded test request.\n",
            encoding="utf-8",
        )
        (self.root / "contracts").mkdir()
        (self.root / "contracts" / "placeholder.txt").write_text("fixture\n", encoding="utf-8")
        _git(self.root, "add", "README.md")
        _git(self.root, "add", "ARCHITECT-CONTRACT.md")
        _git(self.root, "add", "contracts/placeholder.txt")
        _git(self.root, "commit", "-m", "baseline")
        self.office = BuildOffice(self.root)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _init_mission(self, **kwargs):
        kwargs.setdefault("contract_ref", "ARCHITECT-CONTRACT.md")
        return self.office.init_mission(**kwargs)

    def _complete_analysis(self, mission_id: str) -> None:
        state = self.office.load_mission(mission_id)
        analysis = next(item for item in state["assignments"] if item["duty"] == "analysis")
        analysis["status"] = "completed"
        analysis["evidence"] = {"summary": "Architect contract confirmed"}
        self.office.save_mission(state, event="test-analysis-complete")

    def _complete_implementation_for_review(self, mission_id: str) -> None:
        state = self.office.load_mission(mission_id)
        implementation = self.office._find_assignment(state, "codex-implementation")
        worktree = Path(implementation["worktree"])
        target = worktree / "jarvis" / "example.py"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("VALUE = 1\n", encoding="utf-8")
        _git(worktree, "add", "jarvis/example.py")
        _git(worktree, "commit", "-m", "implement review fixture")
        implementation["status"] = "completed"
        implementation["evidence"] = self.office.capture_evidence(
            worktree,
            0,
            "",
            "",
            datetime.now(timezone.utc).isoformat(),
            baseline_commit=state["baseline_commit"],
        )
        self.office.save_mission(state, event="test-implementation-complete")

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
            self._init_mission(
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
        mission = self._init_mission(
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
        mission = self._init_mission(
            request="Plan a risky migration",
            risk="high",
            mission_id="bo-high",
            provision=False,
        )
        duties = [item["duty"] for item in mission["assignments"]]
        self.assertEqual(duties, ["analysis", "implementation", "review"])

    def test_no_claude_route_omits_analysis_and_uses_codex_quality_lane(self) -> None:
        mission = self._init_mission(
            request="Plan a risky migration without Claude",
            risk="high",
            mission_id="bo-no-claude",
            route_mode="no-claude",
            provision=False,
        )
        assignments = {item["assignment_id"]: item for item in mission["assignments"]}
        self.assertEqual(set(assignments), {"codex-implementation", "codex-review"})
        self.assertNotIn("analysis", [item["duty"] for item in mission["assignments"]])
        self.assertEqual(mission["route_mode"], "no-claude")
        self.assertEqual(mission["routing"], {"implementer": "codex", "reviewer": "codex"})

    def test_mission_and_assignments_record_office_charter(self) -> None:
        mission = self._init_mission(
            request="Bind assignments to office charters",
            risk="high",
            mission_id="bo-charters",
            provision=False,
        )
        self.assertEqual(mission["charter_version"], CHARTER_VERSION)
        offices = {item["duty"]: item["office"] for item in mission["assignments"]}
        self.assertEqual(
            offices,
            {"analysis": "architect", "implementation": "build", "review": "qa"},
        )
        self.assertTrue(
            all(item["charter_version"] == CHARTER_VERSION for item in mission["assignments"])
        )

    def test_assignment_prompt_includes_copy_ready_charter(self) -> None:
        mission = self._init_mission(
            request="Teach the Build Office",
            mission_id="bo-charter-prompt",
            provision=False,
        )
        assignment = self.office._find_assignment(mission, "codex-implementation")
        prompt = self.office.build_prompt(mission, assignment)
        self.assertIn("JARVIS Build Office", prompt)
        self.assertIn(f"recorded charter version: {CHARTER_VERSION}", prompt)
        self.assertIn("You must not:", prompt)
        self.assertIn("Mission: Teach the Build Office", prompt)
        self.assertIn("Frozen Architect contract: ARCHITECT-CONTRACT.md", prompt)
        self.assertIn(mission["architecture_contract"]["sha256"], prompt)
        self.assertIn("Implement the bounded test request.", prompt)

    def test_assignment_prompt_uses_recorded_charter_snapshot(self) -> None:
        mission = self._init_mission(
            request="Preserve the assigned rules",
            mission_id="bo-charter-snapshot",
            provision=False,
        )
        assignment = self.office._find_assignment(mission, "codex-implementation")
        assignment["onboarding_brief"] = "RECORDED OFFICE RULES"
        prompt = self.office.build_prompt(mission, assignment)
        self.assertIn("RECORDED OFFICE RULES", prompt)

    def test_assignment_office_mismatch_fails_closed(self) -> None:
        mission = self._init_mission(
            request="Reject conflicting identity",
            mission_id="bo-office-mismatch",
            provision=False,
        )
        assignment = dict(self.office._find_assignment(mission, "codex-implementation"))
        assignment["office"] = "qa"
        with self.assertRaisesRegex(ValueError, "conflicts with duty"):
            self.office.build_prompt(mission, assignment)

    def test_missing_architect_contract_blocks_build(self) -> None:
        mission = self.office.init_mission(
            request="Do not make Build invent the contract",
            mission_id="bo-missing-contract",
            provision=True,
        )
        self.assertEqual(self.office.office_inbox("codex")["items"], [])
        with self.assertRaisesRegex(RuntimeError, "awaiting frozen Architect contract"):
            self.office.dispatch(mission["mission_id"], "codex-implementation", dry_run=True)

    def test_uncommitted_or_missing_contract_reference_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "committed at the mission baseline"):
            self.office.init_mission(
                request="Reject a fake contract",
                mission_id="bo-fake-contract",
                contract_ref="does-not-exist.md",
                provision=False,
            )
        with self.assertRaisesRegex(ValueError, "committed file blob"):
            self.office.init_mission(
                request="Reject a directory contract",
                mission_id="bo-directory-contract",
                contract_ref="contracts",
                provision=False,
            )

    def test_unknown_assignment_duty_fails_closed_during_prompt_build(self) -> None:
        mission = self._init_mission(
            request="Reject an ungoverned duty",
            mission_id="bo-unknown-duty",
            provision=False,
        )
        assignment = dict(self.office._find_assignment(mission, "codex-implementation"))
        assignment["duty"] = "merge"
        with self.assertRaisesRegex(ValueError, "No office charter"):
            self.office.build_prompt(mission, assignment)

    def test_implementer_is_configurable_and_reviewer_is_always_other_provider(self) -> None:
        mission = self._init_mission(
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
            self._init_mission(request="Do work", provision=False)

    def test_critical_dispatch_requires_explicit_human_approval(self) -> None:
        mission = self._init_mission(
            request="Perform critical migration",
            risk="critical",
            mission_id="bo-critical",
            provision=True,
        )
        with self.assertRaisesRegex(RuntimeError, "dispatch approval"):
            self.office.dispatch(mission["mission_id"], "codex-implementation", dry_run=True)
        approval = self.office.approve_dispatch(mission["mission_id"], approved_by="Chris")
        self._complete_analysis(mission["mission_id"])
        dispatched = self.office.dispatch(
            mission["mission_id"], "codex-implementation", dry_run=True
        )
        self.assertTrue(approval["dispatch"])
        self.assertEqual(approval["dispatch_approved_by"], "Chris")
        self.assertTrue(dispatched["dry_run"])

    def test_writable_assignment_never_targets_main_checkout(self) -> None:
        mission = self._init_mission(
            request="Do work", mission_id="bo-main-target", provision=False
        )
        state = self.office.load_mission(mission["mission_id"])
        assignment = self.office._find_assignment(state, "codex-implementation")
        assignment["worktree"] = str(self.root)
        self.office.save_mission(state, event="test-modified")
        with self.assertRaisesRegex(RuntimeError, "main checkout"):
            self.office.provision_assignment(mission["mission_id"], "codex-implementation")

    def test_real_dispatch_refuses_missing_worktree_instead_of_falling_back_to_main(self) -> None:
        mission = self._init_mission(
            request="Never fall back to main",
            mission_id="bo-no-fallback",
            provision=False,
        )
        with self.assertRaisesRegex(RuntimeError, "refusing to run in the main checkout"):
            self.office.dispatch(mission["mission_id"], "codex-implementation")

    def test_provision_creates_unique_branch_and_worktree_off_main(self) -> None:
        mission = self._init_mission(
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
        first = self._init_mission(
            request="First change", mission_id="bo-first", provision=False
        )
        second = self._init_mission(
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
        mission = self._init_mission(
            request="Implement safely", mission_id="bo-dispatch", provision=True
        )
        codex = self.office.dispatch(
            mission["mission_id"], "codex-implementation", dry_run=True
        )
        self._complete_implementation_for_review(mission["mission_id"])
        claude = self.office.dispatch(
            mission["mission_id"], "claude-review", dry_run=True
        )
        self.assertEqual(codex["command"][:2], ["codex", "exec"])
        self.assertIn("workspace-write", codex["command"])
        self.assertEqual(claude["command"][:2], ["claude", "-p"])
        self.assertIn("plan", claude["command"])
        self.assertIn("Do not switch branches", codex["display_command"])

    def test_codex_review_dispatch_uses_supported_command_shape_and_exact_commit(self) -> None:
        mission = self._init_mission(
            request="Recover QA dispatch",
            mission_id="bo-codex-review-shape",
            risk="medium",
            route_mode="no-claude",
            provision=True,
        )
        self._complete_implementation_for_review(mission["mission_id"])
        state = self.office.load_mission(mission["mission_id"])
        implementation = self.office._find_assignment(state, "codex-implementation")
        review = self.office.dispatch(mission["mission_id"], "codex-review", dry_run=True)
        command = review["command"]
        self.assertEqual(command[:2], ["codex", "exec"])
        self.assertIn("review", command)
        self.assertIn("--commit", command)
        self.assertEqual(
            command[command.index("--commit") + 1],
            implementation["evidence"]["commit"],
        )
        self.assertEqual(command[-1], "-")
        self.assertEqual(review["stdin"], "[prompt via stdin]")
        self.assertNotIn("-a", command)
        self.assertNotIn("--ask-for-approval", command)

    def test_review_scope_validation_preserves_dotfile_owned_paths(self) -> None:
        mission = self._init_mission(
            request="D0.1 review scope",
            mission_id="bo-review-dotfile",
            risk="medium",
            route_mode="no-claude",
            owned_paths=[
                "deploy/docker-compose.yml",
                ".env.example",
                "scripts/verify_deploy_config.py",
                "tests/test_deploy_config.py",
            ],
            provision=False,
        )
        review = self.office._find_assignment(mission, "codex-review")
        violations = self.office._scope_violations(
            review,
            [
                ".env.example",
                "deploy/docker-compose.yml",
                "scripts/verify_deploy_config.py",
                "tests/test_deploy_config.py",
            ],
        )
        self.assertEqual(violations, [])

    def test_review_scope_validation_rejects_out_of_scope_and_forbidden_paths(self) -> None:
        mission = self._init_mission(
            request="D0.1 review scope",
            mission_id="bo-review-scope-blocks",
            risk="medium",
            route_mode="no-claude",
            owned_paths=["deploy/**", ".env.example"],
            provision=False,
        )
        review = self.office._find_assignment(mission, "codex-review")
        review["forbidden_paths"] = [".env.example", "deploy/docker-compose.yml"]
        violations = self.office._scope_violations(
            review,
            [".env.example", "deploy/docker-compose.yml", "docs/outside.md"],
        )
        self.assertEqual(
            violations,
            [".env.example", "deploy/docker-compose.yml", "docs/outside.md"],
        )

    def test_review_process_mutation_blocks_completion(self) -> None:
        mission = self._init_mission(
            request="Detect QA mutation",
            mission_id="bo-review-mutation",
            risk="medium",
            route_mode="no-claude",
            owned_paths=["jarvis/**"],
            provision=True,
        )
        self._complete_implementation_for_review(mission["mission_id"])
        state = self.office.load_mission(mission["mission_id"])
        implementation = self.office._find_assignment(state, "codex-implementation")
        target = Path(implementation["worktree"]) / "jarvis" / "example.py"
        original_run = build_office_module._run

        def fake_run(args, *, cwd, timeout=30, check=True, input_text=None):
            if list(args[:2]) == ["codex", "exec"]:
                self.assertEqual(args[-1], "-")
                self.assertIn("Frozen Architect contract", input_text or "")
                target.write_text("VALUE = 99\n", encoding="utf-8")
                return subprocess.CompletedProcess(
                    args=list(args),
                    returncode=0,
                    stdout="reviewed",
                    stderr="",
                )
            return original_run(args, cwd=cwd, timeout=timeout, check=check, input_text=input_text)

        with patch("jarvis.build_office._run", side_effect=fake_run):
            result = self.office.dispatch(mission["mission_id"], "codex-review")
        self.assertEqual(result["status"], "failed")
        self.assertIn("review_target_error", result["evidence"])
        self.assertIn("changed after Build handoff", result["evidence"]["review_target_error"])

    def test_nonzero_model_exit_marks_assignment_failed_and_releases_lease(self) -> None:
        mission = self._init_mission(
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
        mission = self._init_mission(
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
        mission = self._init_mission(
            request="Implement safely", mission_id="bo-release-blocked", provision=False
        )
        plan = self.office.release_plan(mission["mission_id"])
        self.assertEqual(plan["status"], "blocked")
        self.assertIn("implementation incomplete", plan["reasons"])
        self.assertIn("independent review incomplete", plan["reasons"])
        self.assertFalse(plan["mutated_git"])

    def test_high_risk_release_also_requires_analysis(self) -> None:
        mission = self._init_mission(
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

    def test_no_claude_route_can_skip_analysis_gate_while_retaining_review_gate(self) -> None:
        mission = self._init_mission(
            request="Risky change without Claude",
            risk="high",
            mission_id="bo-no-claude-release",
            route_mode="no-claude",
            provision=False,
        )
        state = self.office.load_mission(mission["mission_id"])
        for assignment in state["assignments"]:
            if assignment["duty"] == "implementation":
                assignment["status"] = "completed"
                assignment["evidence"] = {
                    "exit_code": 0,
                    "commit": "different",
                    "changed_files": ["jarvis/example.py"],
                }
            elif assignment["duty"] == "review":
                assignment["status"] = "planned"
        self.office.save_mission(state, event="test-no-claude-partial")
        plan = self.office.release_plan(mission["mission_id"])
        self.assertNotIn("required analysis incomplete", plan["reasons"])
        self.assertIn("independent review incomplete", plan["reasons"])

    def test_release_rejects_noop_implementation_and_scope_violation(self) -> None:
        mission = self._init_mission(
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
        mission = self._init_mission(
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

    def test_recover_review_assignment_preserves_history_and_is_idempotent(self) -> None:
        mission = self._init_mission(
            request="Recover failed QA review",
            mission_id="bo-review-recover",
            risk="medium",
            route_mode="no-claude",
            owned_paths=[
                ".env.example",
                "deploy/docker-compose.yml",
                "scripts/verify_deploy_config.py",
                "tests/test_deploy_config.py",
            ],
            provision=False,
        )
        state = self.office.load_mission(mission["mission_id"])
        review = self.office._find_assignment(state, "codex-review")
        review["status"] = "running"
        review["lease"] = {
            "holder": "codex-office",
            "acquired_at": datetime.now(timezone.utc).isoformat(),
        }
        review["evidence_history"] = [{"summary": "AC7 rejection"}]
        review["evidence"] = {
            "exit_code": 2,
            "commit": "44185456511efdb07e4cd43e04cd4f651f2818d3",
            "changed_files": [
                ".env.example",
                "deploy/docker-compose.yml",
                "scripts/verify_deploy_config.py",
                "tests/test_deploy_config.py",
            ],
            "target_fingerprint": "b53c182f7e883473825fdb4e3992e24a80622f6bcf66936a1dd641ded7537dbc",
            "stderr_tail": "error: unexpected argument '-a' found",
        }
        self.office.save_mission(state, event="test-review-running")
        recovered = self.office.recover_review_assignment(
            mission["mission_id"],
            "codex-review",
            approved_by="Chris",
            reason="unsupported codex flags",
        )
        self.assertEqual(recovered["status"], "planned")
        self.assertEqual(recovered["evidence"], {})
        self.assertEqual(len(recovered["evidence_history"]), 2)
        self.assertEqual(
            recovered["evidence_history"][-1]["stderr_tail"],
            "error: unexpected argument '-a' found",
        )
        self.assertEqual(
            recovered["evidence_history"][-1]["recovery_reason"],
            "unsupported codex flags",
        )
        self.assertIn("released_at", recovered["lease"])
        again = self.office.recover_review_assignment(
            mission["mission_id"],
            "codex-review",
            approved_by="Chris",
            reason="unsupported codex flags",
        )
        self.assertEqual(again["status"], "planned")
        self.assertEqual(len(again["evidence_history"]), 2)

    def test_recover_review_assignment_rejects_invalid_states(self) -> None:
        mission = self._init_mission(
            request="Reject invalid review recovery",
            mission_id="bo-review-recover-invalid",
            risk="medium",
            route_mode="no-claude",
            provision=False,
        )
        with self.assertRaisesRegex(RuntimeError, "recoverable state"):
            self.office.recover_review_assignment(
                mission["mission_id"],
                "codex-review",
                approved_by="Chris",
                reason="try too early",
            )
        with self.assertRaisesRegex(RuntimeError, "non-writable review"):
            self.office.recover_review_assignment(
                mission["mission_id"],
                "codex-implementation",
                approved_by="Chris",
                reason="wrong lane",
            )
        state = self.office.load_mission(mission["mission_id"])
        review = self.office._find_assignment(state, "codex-review")
        review["status"] = "completed"
        review["evidence"] = {"summary": "approved"}
        self.office.save_mission(state, event="test-review-complete")
        with self.assertRaisesRegex(RuntimeError, "Successful completed reviews"):
            self.office.recover_review_assignment(
                mission["mission_id"],
                "codex-review",
                approved_by="Chris",
                reason="should refuse",
            )

    def test_stale_revision_is_rejected(self) -> None:
        mission = self._init_mission(
            request="Protect revisions", mission_id="bo-cas", provision=False
        )
        stale = self.office.load_mission(mission["mission_id"])
        current = self.office.load_mission(mission["mission_id"])
        self.office.save_mission(current, event="first-update")
        with self.assertRaisesRegex(RuntimeError, "revision conflict"):
            self.office.save_mission(stale, event="stale-update")

    def test_release_plan_becomes_approval_required_only_with_cross_evidence(self) -> None:
        mission = self._init_mission(
            request="Implement safely", mission_id="bo-release-ready", provision=True
        )
        self._complete_implementation_for_review(mission["mission_id"])
        self.office.claim_assignment(
            mission["mission_id"], "claude-review", claimed_by="Claude QA Office"
        )
        self.office.submit_result(
            mission["mission_id"],
            "claude-review",
            completed_by="Claude QA Office",
            status="completed",
            summary="Approved against the frozen target.",
        )
        plan = self.office.release_plan(mission["mission_id"])
        self.assertEqual(plan["status"], "approval-required")
        self.assertEqual(plan["reasons"], [])
        self.assertTrue(plan["approval_required"])
        self.assertFalse(plan["mutated_git"])

    def test_events_are_append_only_and_revision_increases(self) -> None:
        mission = self._init_mission(
            request="Trace this", mission_id="bo-events", provision=False
        )
        before = mission["revision"]
        self.office.acquire_lease(mission["mission_id"], "claude-review")
        after = self.office.load_mission(mission["mission_id"])
        events = [json.loads(line) for line in self.office.events_path.read_text().splitlines()]
        self.assertGreater(after["revision"], before)
        self.assertEqual([item["event"] for item in events], ["mission-created", "lease-acquired"])

    def test_inbox_shows_high_risk_analysis_before_implementation(self) -> None:
        self._init_mission(
            request="Audit a risky change",
            risk="high",
            mission_id="bo-heartbeat-analysis",
            provision=False,
        )
        inbox = self.office.office_inbox("claude")
        self.assertEqual(
            [item["assignment_id"] for item in inbox["items"]],
            ["claude-analysis"],
        )
        self.assertEqual(inbox["items"][0]["office"], "architect")
        self.assertEqual(inbox["items"][0]["charter_version"], CHARTER_VERSION)
        self.assertIn("JARVIS Architect Office", inbox["items"][0]["prompt"])

    def test_critical_implementation_stays_out_of_inbox_until_approved(self) -> None:
        mission = self._init_mission(
            request="Critical implementation gate",
            risk="critical",
            mission_id="bo-heartbeat-critical",
            provision=True,
        )
        codex_before = self.office.office_inbox("codex")
        self.assertEqual(codex_before["items"], [])
        self.office.approve_dispatch(mission["mission_id"], approved_by="Chris")
        state = self.office.load_mission(mission["mission_id"])
        analysis = self.office._find_assignment(state, "claude-analysis")
        analysis["status"] = "completed"
        analysis["evidence"] = {"summary": "Ready to implement"}
        self.office.save_mission(state, event="test-analysis-complete")
        codex_after = self.office.office_inbox("codex")
        self.assertEqual(
            [item["assignment_id"] for item in codex_after["items"]],
            ["codex-implementation"],
        )

    def test_claim_and_submit_result_complete_review_lane(self) -> None:
        mission = self._init_mission(
            request="Heartbeat review flow",
            mission_id="bo-heartbeat-review",
            provision=True,
        )
        self._complete_implementation_for_review(mission["mission_id"])
        inbox = self.office.office_inbox("claude")
        self.assertEqual([item["assignment_id"] for item in inbox["items"]], ["claude-review"])
        claimed = self.office.claim_assignment(
            mission["mission_id"], "claude-review", claimed_by="Claude QA Office"
        )
        self.assertEqual(claimed["status"], "leased")
        submitted = self.office.submit_result(
            mission["mission_id"],
            "claude-review",
            completed_by="Claude QA Office",
            status="completed",
            summary="No blocking findings.",
            findings=["Optional naming cleanup only."],
            tests=["Read-only contract review"],
        )
        self.assertEqual(submitted["status"], "completed")
        plan = self.office.release_plan(mission["mission_id"])
        self.assertEqual(plan["status"], "approval-required")

    def test_failed_review_submission_blocks_release(self) -> None:
        mission = self._init_mission(
            request="Blocked review flow",
            mission_id="bo-heartbeat-blocked",
            provision=True,
        )
        self._complete_implementation_for_review(mission["mission_id"])
        self.office.claim_assignment(
            mission["mission_id"], "claude-review", claimed_by="Claude QA Office"
        )
        self.office.submit_result(
            mission["mission_id"],
            "claude-review",
            completed_by="Claude QA Office",
            status="failed",
            summary="Blocking contract mismatch.",
            findings=["Release gate misses a required invariant."],
        )
        plan = self.office.release_plan(mission["mission_id"])
        self.assertEqual(plan["status"], "blocked")
        self.assertIn("claude-review is failed", plan["reasons"])

    def test_heartbeat_routes_ready_build_once_then_noops_unchanged_state(self) -> None:
        mission = self._init_mission(
            request="Heartbeat should route ready build",
            mission_id="bo-heartbeat-route-build",
            provision=True,
        )
        first = self.office.heartbeat(mission["mission_id"], actor="Architect heartbeat")
        self.assertFalse(first["missions"][0]["unchanged"])
        self.assertEqual(
            [item["kind"] for item in first["missions"][0]["actions"]],
            ["route-to-build", "waiting"],
        )
        self.assertEqual(
            first["missions"][0]["actions"][0]["assignment_id"],
            "codex-implementation",
        )
        second = self.office.heartbeat(mission["mission_id"], actor="Architect heartbeat")
        self.assertTrue(second["missions"][0]["unchanged"])
        self.assertEqual(second["missions"][0]["actions"], [])
        self.assertEqual(second["missions"][0]["heartbeat"]["unchanged_cycles"], 1)
        self.assertEqual(second["missions"][0]["heartbeat"]["suppressed_action_count"], 2)

    def test_heartbeat_routes_completed_build_to_quality(self) -> None:
        mission = self._init_mission(
            request="Heartbeat should route quality",
            mission_id="bo-heartbeat-route-quality",
            provision=True,
        )
        self.office.heartbeat(mission["mission_id"], actor="Architect heartbeat")
        self._complete_implementation_for_review(mission["mission_id"])
        routed = self.office.heartbeat(mission["mission_id"], actor="Architect heartbeat")
        actions = routed["missions"][0]["actions"]
        self.assertEqual([item["kind"] for item in actions], ["route-to-quality"])
        self.assertEqual(actions[0]["office"], "qa")
        self.assertEqual(actions[0]["assignment_id"], "claude-review")

    def test_heartbeat_sends_failed_review_to_architect_disposition(self) -> None:
        mission = self._init_mission(
            request="Heartbeat should escalate review findings",
            mission_id="bo-heartbeat-review-disposition",
            provision=True,
        )
        self._complete_implementation_for_review(mission["mission_id"])
        self.office.claim_assignment(
            mission["mission_id"], "claude-review", claimed_by="Claude QA Office"
        )
        self.office.submit_result(
            mission["mission_id"],
            "claude-review",
            completed_by="Claude QA Office",
            status="failed",
            summary="Blocking contract mismatch.",
        )
        routed = self.office.heartbeat(mission["mission_id"], actor="Architect heartbeat")
        actions = routed["missions"][0]["actions"]
        self.assertEqual([item["kind"] for item in actions], ["disposition-required"])
        self.assertEqual(actions[0]["office"], "architect")

    def test_heartbeat_can_dry_run_dispatch_ready_assignment(self) -> None:
        mission = self._init_mission(
            request="Heartbeat can preview dispatch",
            mission_id="bo-heartbeat-dispatch-preview",
            provision=True,
        )
        routed = self.office.heartbeat(
            mission["mission_id"],
            actor="Architect heartbeat",
            dispatch_ready=True,
            dry_run=True,
        )
        dispatches = routed["missions"][0]["dispatches"]
        self.assertEqual([item["assignment_id"] for item in dispatches], ["codex-implementation"])
        self.assertTrue(dispatches[0]["result"]["dry_run"])

    def test_review_refuses_target_changed_after_build_handoff(self) -> None:
        mission = self._init_mission(
            request="Review one immutable target",
            mission_id="bo-moving-review-target",
            provision=True,
        )
        self._complete_implementation_for_review(mission["mission_id"])
        implementation = self.office._find_assignment(
            self.office.load_mission(mission["mission_id"]), "codex-implementation"
        )
        target = Path(implementation["worktree"]) / "jarvis" / "example.py"
        target.write_text("VALUE = 2\n", encoding="utf-8")
        self.assertEqual(self.office.office_inbox("claude")["items"], [])
        with self.assertRaisesRegex(RuntimeError, "target changed"):
            self.office.claim_assignment(
                mission["mission_id"], "claude-review", claimed_by="Claude QA Office"
            )

    def test_review_submission_refuses_target_changed_after_claim(self) -> None:
        mission = self._init_mission(
            request="Keep target fixed during review",
            mission_id="bo-target-changed-after-claim",
            provision=True,
        )
        self._complete_implementation_for_review(mission["mission_id"])
        self.office.claim_assignment(
            mission["mission_id"], "claude-review", claimed_by="Claude QA Office"
        )
        implementation = self.office._find_assignment(
            self.office.load_mission(mission["mission_id"]), "codex-implementation"
        )
        target = Path(implementation["worktree"]) / "jarvis" / "example.py"
        target.write_text("VALUE = 3\n", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "target changed"):
            self.office.submit_result(
                mission["mission_id"],
                "claude-review",
                completed_by="Claude QA Office",
                status="completed",
                summary="This verdict must not be accepted.",
            )

    def test_release_refuses_target_changed_after_qa_verdict(self) -> None:
        mission = self._init_mission(
            request="Release only the reviewed target",
            mission_id="bo-target-changed-after-verdict",
            provision=True,
        )
        self._complete_implementation_for_review(mission["mission_id"])
        self.office.claim_assignment(
            mission["mission_id"], "claude-review", claimed_by="Claude QA Office"
        )
        self.office.submit_result(
            mission["mission_id"],
            "claude-review",
            completed_by="Claude QA Office",
            status="completed",
            summary="Approved frozen target.",
        )
        implementation = self.office._find_assignment(
            self.office.load_mission(mission["mission_id"]), "codex-implementation"
        )
        target = Path(implementation["worktree"]) / "jarvis" / "example.py"
        target.write_text("VALUE = 4\n", encoding="utf-8")
        plan = self.office.release_plan(mission["mission_id"])
        self.assertEqual(plan["status"], "blocked")
        self.assertIn("implementation review target changed after Build handoff", plan["reasons"])

    def test_architect_heartbeat_is_idle_and_repeats_cheaply_when_nothing_changed(self) -> None:
        first = self.office.office_heartbeat("architect", cadence_seconds=300)
        second = self.office.office_heartbeat("architect", cadence_seconds=300)
        self.assertEqual(first["status"], "idle")
        self.assertFalse(first["needs_action"])
        self.assertTrue(first["changed_since_last"])
        self.assertEqual(second["status"], "idle")
        self.assertFalse(second["needs_action"])
        self.assertFalse(second["changed_since_last"])
        self.assertEqual(second["next_check_after_seconds"], 300)

    def test_architect_heartbeat_surfaces_ready_architect_assignment(self) -> None:
        self._init_mission(
            request="Architect should analyze this high risk mission",
            risk="high",
            mission_id="bo-architect-heartbeat-ready",
            provision=False,
        )
        heartbeat = self.office.office_heartbeat("architect", cadence_seconds=300)
        self.assertEqual(heartbeat["status"], "attention-required")
        self.assertTrue(heartbeat["needs_action"])
        self.assertTrue(heartbeat["changed_since_last"])
        actions = {(item["kind"], item["assignment_id"]) for item in heartbeat["actions"]}
        self.assertIn(("architect-assignment-ready", "claude-analysis"), actions)
        self.assertIn("claim bo-architect-heartbeat-ready claude-analysis", heartbeat["actions"][0]["command"])

    def test_architect_heartbeat_routes_completed_build_to_quality_review(self) -> None:
        mission = self._init_mission(
            request="Route completed implementation to Quality",
            mission_id="bo-heartbeat-route-quality",
            provision=True,
        )
        self._complete_implementation_for_review(mission["mission_id"])
        heartbeat = self.office.office_heartbeat("architect", cadence_seconds=300)
        route_actions = [
            item for item in heartbeat["actions"] if item["kind"] == "route-build-to-quality"
        ]
        self.assertEqual(len(route_actions), 1)
        self.assertEqual(route_actions[0]["assignment_id"], "claude-review")
        self.assertIn("dispatch bo-heartbeat-route-quality claude-review --dry-run", route_actions[0]["command"])

    def test_architect_heartbeat_surfaces_failed_assignment_for_disposition(self) -> None:
        mission = self._init_mission(
            request="Classify a failed build",
            mission_id="bo-heartbeat-failed-assignment",
            provision=False,
        )
        state = self.office.load_mission(mission["mission_id"])
        implementation = self.office._find_assignment(state, "codex-implementation")
        implementation["status"] = "failed"
        implementation["evidence"] = {"stderr_tail": "unsupported -a flag"}
        self.office.save_mission(state, event="test-failed-assignment")
        heartbeat = self.office.office_heartbeat("architect", cadence_seconds=300)
        disposition_actions = [
            item for item in heartbeat["actions"] if item["kind"] == "assignment-needs-disposition"
        ]
        self.assertEqual(len(disposition_actions), 1)
        self.assertEqual(disposition_actions[0]["assignment_id"], "codex-implementation")
        self.assertIn("unsupported -a flag", disposition_actions[0]["detail"])

    def test_release_blocks_review_target_baseline_mismatch(self) -> None:
        mission = self._init_mission(
            request="Release only the matching baseline",
            mission_id="bo-review-baseline-mismatch",
            risk="medium",
            route_mode="no-claude",
            provision=True,
        )
        self._complete_implementation_for_review(mission["mission_id"])
        state = self.office.load_mission(mission["mission_id"])
        implementation = self.office._find_assignment(state, "codex-implementation")
        implementation["evidence"]["baseline_commit"] = "different-baseline"
        review = self.office._find_assignment(state, "codex-review")
        review["status"] = "completed"
        review["evidence"] = {"summary": "Approved frozen target."}
        self.office.save_mission(state, event="test-review-baseline-mismatch")
        plan = self.office.release_plan(mission["mission_id"])
        self.assertEqual(plan["status"], "blocked")
        self.assertIn(
            "implementation review target baseline no longer matches durable Build evidence",
            plan["reasons"],
        )


if __name__ == "__main__":
    unittest.main()
