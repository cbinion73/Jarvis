from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


Runner = Callable[[list[str], Path], str]


@dataclass(frozen=True)
class GitInspection:
    repo_root: Path
    branch: str
    latest_commit: str
    status_lines: list[str]
    is_clean: bool
    branch_matches_phase: bool
    has_uncommitted_changes: bool


def inspect_git_state(repo_root: str | Path, expected_branch: str, runner: Runner | None = None) -> GitInspection:
    root = Path(repo_root)
    run = runner or _default_runner
    branch = run(["git", "branch", "--show-current"], root).strip()
    latest_commit = run(["git", "rev-parse", "--short", "HEAD"], root).strip()
    raw_status = run(["git", "status", "--short"], root)
    status_lines = [line for line in raw_status.splitlines() if line.strip()]
    is_clean = not status_lines
    return GitInspection(
        repo_root=root,
        branch=branch,
        latest_commit=latest_commit,
        status_lines=status_lines,
        is_clean=is_clean,
        branch_matches_phase=branch == expected_branch,
        has_uncommitted_changes=not is_clean,
    )


def _default_runner(cmd: list[str], cwd: Path) -> str:
    completed = subprocess.run(
        cmd,
        cwd=cwd,
        check=True,
        text=True,
        capture_output=True,
    )
    return completed.stdout
