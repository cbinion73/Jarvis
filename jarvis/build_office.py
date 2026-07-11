from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator, Sequence

import fcntl

from .persistence import append_jsonl, atomic_write_json
from .office_charters import CHARTER_VERSION, charter_for_duty, onboarding_brief, office_for_duty


RISK_LEVELS = {"low", "medium", "high", "critical"}
TERMINAL_ASSIGNMENT_STATES = {"completed", "failed", "cancelled", "released"}
WRITE_ASSIGNMENT_STATES = {"leased", "running"}
MANUAL_RESULT_STATES = {"completed", "failed", "blocked"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return cleaned[:48] or "mission"


def _run(
    args: Sequence[str],
    *,
    cwd: Path,
    timeout: int = 30,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        cwd=str(cwd),
        text=True,
        capture_output=True,
        timeout=timeout,
        check=check,
    )


def _static_prefix(pattern: str) -> str:
    normalized = pattern.strip().lstrip("./").casefold()
    wildcard = min(
        [index for token in "*[?" if (index := normalized.find(token)) >= 0]
        or [len(normalized)]
    )
    return normalized[:wildcard].rstrip("/")


def scopes_overlap(left: Sequence[str], right: Sequence[str]) -> bool:
    """Conservatively report whether two writable glob sets may touch one path."""
    for first in left:
        for second in right:
            a = first.strip().lstrip("./").casefold()
            b = second.strip().lstrip("./").casefold()
            if not a or not b:
                return True
            if a == b or fnmatch.fnmatch(a, b) or fnmatch.fnmatch(b, a):
                return True
            a_prefix = _static_prefix(a)
            b_prefix = _static_prefix(b)
            if not a_prefix or not b_prefix:
                return True
            if a_prefix == b_prefix:
                return True
            if a_prefix.startswith(f"{b_prefix}/") or b_prefix.startswith(f"{a_prefix}/"):
                return True
    return False


def _redact_output(value: str) -> str:
    redacted = re.sub(
        r"(?im)^([A-Z][A-Z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD)[A-Z0-9_]*\s*=\s*).+$",
        r"\1[REDACTED]",
        value,
    )
    redacted = re.sub(r"(?i)\b(bearer\s+)[a-z0-9._~+/=-]{12,}", r"\1[REDACTED]", redacted)
    redacted = re.sub(r"\b(?:sk|ghp|github_pat)_[A-Za-z0-9_-]{12,}\b", "[REDACTED_TOKEN]", redacted)
    redacted = re.sub(
        r"-----BEGIN [^-]+-----.*?-----END [^-]+-----",
        "[REDACTED_PRIVATE_BLOCK]",
        redacted,
        flags=re.DOTALL,
    )
    return redacted


@dataclass(slots=True)
class BuildOffice:
    repo_root: Path
    state_root: Path | None = None

    def __post_init__(self) -> None:
        self.repo_root = self.repo_root.resolve()
        if self.state_root is None:
            self.state_root = self.repo_root / "_bmad-output" / "build-office-runs"
        else:
            self.state_root = self.state_root.resolve()

    @property
    def events_path(self) -> Path:
        return self.state_root / "events.jsonl"

    @property
    def lock_path(self) -> Path:
        return self.state_root / ".control.lock"

    @contextmanager
    def _locked(self) -> Iterator[None]:
        self.state_root.mkdir(parents=True, exist_ok=True)
        with self.lock_path.open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def _mission_path(self, mission_id: str) -> Path:
        return self.state_root / mission_id / "mission.json"

    def _append_event(self, event: str, mission_id: str, **details: Any) -> None:
        append_jsonl(
            self.events_path,
            {"event": event, "mission_id": mission_id, "at": _now_iso(), **details},
        )

    def _git(self, *args: str, timeout: int = 30) -> str:
        return _run(["git", *args], cwd=self.repo_root, timeout=timeout).stdout.strip()

    def _repo_changes(self) -> list[str]:
        lines = self._git("status", "--porcelain=v1", "--untracked-files=all").splitlines()
        try:
            state_relative = self.state_root.relative_to(self.repo_root).as_posix().rstrip("/")
        except ValueError:
            state_relative = ""
        if not state_relative:
            return lines
        kept: list[str] = []
        for line in lines:
            path = line[3:] if len(line) > 3 else line
            if path == state_relative or path.startswith(f"{state_relative}/"):
                continue
            kept.append(line)
        return kept

    def doctor(self) -> dict[str, Any]:
        git_root = ""
        git_error = ""
        try:
            git_root = self._git("rev-parse", "--show-toplevel")
        except (subprocess.SubprocessError, OSError) as exc:
            git_error = str(exc)
        changes: list[str] = []
        if git_root:
            changes = self._repo_changes()
        primary_checkout = (self.repo_root / ".git").is_dir()
        return {
            "ok": bool(git_root and primary_checkout and shutil.which("claude") and shutil.which("codex")),
            "repo_root": git_root,
            "repo_clean": not bool(changes),
            "primary_checkout": primary_checkout,
            "git_error": git_error,
            "claude_cli": shutil.which("claude") or "",
            "codex_cli": shutil.which("codex") or "",
            "git_cli": shutil.which("git") or "",
        }

    def _default_assignments(
        self,
        mission_id: str,
        risk: str,
        *,
        implementer: str = "codex",
        owned_paths: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        worktree_root = self.repo_root.parent
        slug = mission_id.removeprefix("bo-")
        implementer = implementer.strip().lower()
        if implementer not in {"claude", "codex"}:
            raise ValueError("implementer must be claude or codex")
        reviewer = "claude" if implementer == "codex" else "codex"
        scopes = [item.strip() for item in list(owned_paths or ["**"]) if item.strip()]
        if not scopes:
            raise ValueError("at least one owned path is required")
        assignments: list[dict[str, Any]] = []
        implementation_worktree = worktree_root / f"{self.repo_root.name}-{implementer}-{slug}"
        if risk in {"high", "critical"}:
            assignments.append(
                self._assignment(
                    mission_id,
                    "claude-analysis",
                    "claude",
                    "analysis",
                    ["_bmad-output/build-office-runs/**"],
                    worktree_root / f"{self.repo_root.name}-claude-{slug}-analysis",
                    writable=False,
                )
            )
        assignments.append(
            self._assignment(
                mission_id,
                f"{implementer}-implementation",
                implementer,
                "implementation",
                scopes,
                implementation_worktree,
                writable=True,
            )
        )
        if risk in {"medium", "high", "critical"}:
            assignments.append(
                self._assignment(
                    mission_id,
                    f"{reviewer}-review",
                    reviewer,
                    "review",
                    scopes,
                    implementation_worktree,
                    writable=False,
                )
            )
        return assignments

    def _assignment(
        self,
        mission_id: str,
        assignment_id: str,
        provider: str,
        duty: str,
        owned_paths: list[str],
        worktree: Path,
        *,
        writable: bool,
    ) -> dict[str, Any]:
        office = office_for_duty(duty)
        branch_key = hashlib.sha256(f"{mission_id}:{assignment_id}".encode()).hexdigest()[:10]
        branch = f"build-office/{_slug(mission_id)}/{_slug(assignment_id)}-{branch_key}" if writable else ""
        return {
            "assignment_id": assignment_id,
            "provider": provider,
            "duty": duty,
            "office": office,
            "charter_version": CHARTER_VERSION,
            "onboarding_brief": onboarding_brief(office),
            "writable": writable,
            "owned_paths": owned_paths,
            "forbidden_paths": [".git/**", "data/**", "**/.env", "**/*secret*"],
            "worktree": str(worktree),
            "branch": branch,
            "status": "planned",
            "lease": {},
            "evidence": {},
        }

    def init_mission(
        self,
        *,
        request: str,
        risk: str = "medium",
        budget_usd: float = 10.0,
        timeout_seconds: int = 1800,
        mission_id: str = "",
        implementer: str = "codex",
        contract_ref: str = "",
        owned_paths: list[str] | None = None,
        provision: bool = True,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        request = request.strip()
        contract_ref = contract_ref.strip()
        risk = risk.strip().lower()
        if not request:
            raise ValueError("request is required")
        if risk not in RISK_LEVELS:
            raise ValueError(f"risk must be one of: {', '.join(sorted(RISK_LEVELS))}")
        if budget_usd <= 0:
            raise ValueError("budget_usd must be positive")
        doctor = self.doctor()
        if not doctor["repo_root"]:
            raise RuntimeError("Build Office requires a Git repository.")
        if not doctor["repo_clean"]:
            raise RuntimeError("Main repository must be clean before mission intake.")
        if not doctor["primary_checkout"]:
            raise RuntimeError("Build Office intake must run from the primary checkout, not a linked worktree.")
        mission_id = mission_id.strip() or f"bo-{_slug(request)}-{uuid.uuid4().hex[:8]}"
        baseline = self._git("rev-parse", "HEAD")
        architecture_contract = self._freeze_contract(contract_ref, baseline)
        self._validate_owned_paths(list(owned_paths or ["**"]))
        assignments = self._default_assignments(
            mission_id,
            risk,
            implementer=implementer,
            owned_paths=owned_paths,
        )
        if architecture_contract["status"] == "frozen":
            for assignment in assignments:
                assignment["forbidden_paths"] = sorted(
                    set([*assignment["forbidden_paths"], architecture_contract["reference"]])
                )
        now = _now_iso()
        mission = {
            "schema_version": 1,
            "charter_version": CHARTER_VERSION,
            "mission_id": mission_id,
            "revision": 1,
            "request": request,
            "risk": risk,
            "status": "planned",
            "repo_root": str(self.repo_root),
            "baseline_commit": baseline,
            "budget_usd": float(budget_usd),
            "timeout_seconds": int(timeout_seconds),
            "budget_enforcement": {
                "claude": "hard-dollar-cap",
                "codex": "time-proxy-only; CLI exposes no dollar-cap flag",
            },
            "requires_cross_review": risk in {"medium", "high", "critical"},
            "routing": {"implementer": implementer, "reviewer": "claude" if implementer == "codex" else "codex"},
            "architecture_contract": architecture_contract,
            "approvals": {"dispatch": risk != "critical", "dispatch_approved_at": ""},
            "assignments": assignments,
            "release": {"status": "blocked", "reasons": ["implementation incomplete"]},
            "created_at": now,
            "updated_at": now,
        }
        with self._locked():
            if self._mission_path(mission_id).exists():
                raise FileExistsError(f"Mission already exists: {mission_id}")
            atomic_write_json(self._mission_path(mission_id), mission)
            self._append_event("mission-created", mission_id, risk=risk, dry_run=dry_run)
        if provision:
            for assignment in assignments:
                if assignment["writable"]:
                    self.provision_assignment(mission_id, assignment["assignment_id"], dry_run=dry_run)
        return self.load_mission(mission_id)

    def _freeze_contract(self, contract_ref: str, baseline: str) -> dict[str, Any]:
        if not contract_ref:
            return {"reference": "", "status": "missing", "sha256": ""}
        reference = Path(contract_ref)
        if reference.is_absolute() or ".." in reference.parts:
            raise ValueError("contract_ref must be a repository-relative path")
        normalized = reference.as_posix().lstrip("./")
        if not normalized:
            raise ValueError("contract_ref must name a committed file")
        cursor = self.repo_root
        for component in Path(normalized).parts:
            cursor = cursor / component
            if cursor.is_symlink():
                raise ValueError("contract_ref may not traverse a symlink")
        try:
            object_type = _run(
                ["git", "cat-file", "-t", f"{baseline}:{normalized}"], cwd=self.repo_root
            ).stdout.strip()
            if object_type != "blob":
                raise ValueError("contract_ref must name a committed file blob")
            content = _run(
                ["git", "show", f"{baseline}:{normalized}"], cwd=self.repo_root
            ).stdout
        except ValueError:
            raise
        except (subprocess.SubprocessError, OSError) as exc:
            raise ValueError("contract_ref must name a file committed at the mission baseline") from exc
        if not content.strip():
            raise ValueError("contract_ref may not be empty")
        return {
            "reference": normalized,
            "status": "frozen",
            "sha256": hashlib.sha256(content.encode()).hexdigest(),
            "baseline_commit": baseline,
            "content": content,
        }

    def load_mission(self, mission_id: str) -> dict[str, Any]:
        path = self._mission_path(mission_id)
        if not path.exists():
            raise KeyError(f"Unknown mission: {mission_id}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"Invalid mission state: {mission_id}")
        required = {"mission_id", "revision", "request", "risk", "assignments", "baseline_commit"}
        if not required.issubset(payload) or not isinstance(payload.get("assignments"), list):
            raise ValueError(f"Invalid mission shape: {mission_id}")
        return payload

    def _validate_owned_paths(self, paths: list[str]) -> None:
        for pattern in paths:
            prefix = _static_prefix(pattern)
            if not prefix:
                continue
            candidate = self.repo_root / prefix
            relative = Path(prefix)
            cursor = self.repo_root
            for component in relative.parts:
                cursor = cursor / component
                if cursor.is_symlink():
                    raise ValueError(f"owned path may not traverse a symlink: {pattern}")
            try:
                candidate.resolve().relative_to(self.repo_root)
            except ValueError as exc:
                raise ValueError(f"owned path escapes repository: {pattern}") from exc

    def save_mission(self, mission: dict[str, Any], *, event: str, **details: Any) -> None:
        path = self._mission_path(str(mission["mission_id"]))
        if path.exists():
            current = json.loads(path.read_text(encoding="utf-8"))
            if int(current.get("revision", -1)) != int(mission.get("revision", -2)):
                raise RuntimeError("Mission revision conflict; reload before saving.")
        mission["revision"] = int(mission.get("revision", 0)) + 1
        mission["updated_at"] = _now_iso()
        atomic_write_json(self._mission_path(str(mission["mission_id"])), mission)
        self._append_event(event, str(mission["mission_id"]), revision=mission["revision"], **details)

    @staticmethod
    def _find_assignment(mission: dict[str, Any], assignment_id: str) -> dict[str, Any]:
        for assignment in mission.get("assignments", []):
            if assignment.get("assignment_id") == assignment_id:
                return assignment
        raise KeyError(f"Unknown assignment: {assignment_id}")

    @staticmethod
    def _assignment_status(mission: dict[str, Any], duty: str) -> list[dict[str, Any]]:
        return [item for item in mission.get("assignments", []) if item.get("duty") == duty]

    def _assignment_ready(self, mission: dict[str, Any], assignment: dict[str, Any]) -> tuple[bool, str]:
        status = str(assignment.get("status") or "")
        if status not in {"planned", "provisioned"}:
            return False, f"assignment status is {status or 'unknown'}"
        duty = str(assignment.get("duty") or "")
        if duty == "analysis":
            return True, "analysis is ready"
        if duty == "implementation":
            contract = mission.get("architecture_contract") or {}
            if contract.get("status") != "frozen" or not str(contract.get("reference") or "").strip():
                return False, "awaiting frozen Architect contract"
            if mission.get("risk") == "critical" and not bool((mission.get("approvals") or {}).get("dispatch")):
                return False, "awaiting dispatch approval"
            analyses = self._assignment_status(mission, "analysis")
            if analyses and any(item.get("status") != "completed" for item in analyses):
                return False, "awaiting required analysis"
            if assignment.get("writable") and status != "provisioned":
                return False, "writable worktree is not provisioned"
            return True, "implementation is ready"
        if duty == "review":
            implementations = self._assignment_status(mission, "implementation")
            if not implementations or any(item.get("status") != "completed" for item in implementations):
                return False, "awaiting implementation evidence"
            unchanged, reason = self._review_target_unchanged(mission, implementations[0])
            if not unchanged:
                return False, reason
            return True, "review is ready"
        return False, f"unknown duty: {duty}"

    def provision_assignment(self, mission_id: str, assignment_id: str, *, dry_run: bool = False) -> dict[str, Any]:
        with self._locked():
            mission = self.load_mission(mission_id)
            assignment = self._find_assignment(mission, assignment_id)
            if not assignment["writable"]:
                return assignment
            worktree = Path(assignment["worktree"])
            branch = str(assignment["branch"])
            if worktree.resolve() == self.repo_root:
                raise RuntimeError("Writable assignments may not use the main checkout.")
            if worktree.exists() and any(worktree.iterdir()):
                raise RuntimeError(f"Worktree path is occupied: {worktree}")
            branch_exists = _run(
                ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
                cwd=self.repo_root,
                check=False,
            ).returncode == 0
            if branch_exists:
                raise RuntimeError(f"Assignment branch already exists: {branch}")
            if not dry_run:
                worktree.parent.mkdir(parents=True, exist_ok=True)
                try:
                    _run(
                        ["git", "worktree", "add", "-b", branch, str(worktree), mission["baseline_commit"]],
                        cwd=self.repo_root,
                        timeout=120,
                    )
                except (subprocess.SubprocessError, OSError) as exc:
                    assignment["status"] = "blocked"
                    assignment["evidence"] = {"provision_error": str(exc), "recorded_at": _now_iso()}
                    self.save_mission(mission, event="assignment-blocked", assignment_id=assignment_id, reason="provision failed")
                    raise RuntimeError(f"Unable to provision assignment worktree: {exc}") from exc
            assignment["status"] = "provisioned" if not dry_run else "planned"
            self.save_mission(mission, event="assignment-provisioned", assignment_id=assignment_id, dry_run=dry_run)
            return dict(assignment)

    def office_inbox(self, provider: str) -> dict[str, Any]:
        provider = provider.strip().lower()
        if provider not in {"claude", "codex"}:
            raise ValueError("provider must be claude or codex")
        items: list[dict[str, Any]] = []
        if self.state_root.exists():
            for path in sorted(self.state_root.glob("*/mission.json")):
                try:
                    mission = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue
                if not isinstance(mission, dict) or not isinstance(mission.get("assignments"), list):
                    continue
                for assignment in mission["assignments"]:
                    if not isinstance(assignment, dict) or assignment.get("provider") != provider:
                        continue
                    expected_office = office_for_duty(str(assignment.get("duty") or ""))
                    if assignment.get("office") and assignment.get("office") != expected_office:
                        continue
                    ready, reason = self._assignment_ready(mission, assignment)
                    if not ready:
                        continue
                    payload = {
                        "mission_id": str(mission.get("mission_id") or ""),
                        "assignment_id": str(assignment.get("assignment_id") or ""),
                        "duty": str(assignment.get("duty") or ""),
                        "office": str(assignment.get("office") or expected_office),
                        "charter_version": str(assignment.get("charter_version") or mission.get("charter_version") or CHARTER_VERSION),
                        "risk": str(mission.get("risk") or ""),
                        "request": str(mission.get("request") or ""),
                        "architecture_contract": dict(mission.get("architecture_contract") or {}),
                        "status": str(assignment.get("status") or ""),
                        "writable": bool(assignment.get("writable")),
                        "worktree": str(assignment.get("worktree") or ""),
                        "branch": str(assignment.get("branch") or ""),
                        "owned_paths": list(assignment.get("owned_paths") or []),
                        "forbidden_paths": list(assignment.get("forbidden_paths") or []),
                        "mission_file": str(path),
                        "ready_reason": reason,
                        "claim_command": (
                            f"python3 scripts/jarvis_build_office.py claim {mission.get('mission_id')} "
                            f"{assignment.get('assignment_id')} --by {provider}-office"
                        ),
                        "submit_command_hint": (
                            f"python3 scripts/jarvis_build_office.py submit-result {mission.get('mission_id')} "
                            f"{assignment.get('assignment_id')} --by {provider}-office --status completed "
                            "--summary '...'"
                        ),
                        "prompt": self.build_prompt(mission, assignment),
                    }
                    if assignment.get("duty") == "review":
                        implementation = next(
                            (item for item in mission["assignments"] if item.get("duty") == "implementation"),
                            {},
                        )
                        payload["review_target"] = {
                            "provider": str(implementation.get("provider") or ""),
                            "worktree": str(implementation.get("worktree") or ""),
                            "branch": str(implementation.get("branch") or ""),
                            "evidence": dict(implementation.get("evidence") or {}),
                        }
                    items.append(payload)
        items.sort(key=lambda item: (item["risk"], item["mission_id"], item["assignment_id"]))
        return {"provider": provider, "generated_at": _now_iso(), "items": items}

    def _active_write_assignments(self, *, exclude: tuple[str, str] | None = None) -> Iterator[tuple[str, dict[str, Any]]]:
        if not self.state_root.exists():
            return
        for path in self.state_root.glob("*/mission.json"):
            try:
                mission = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(mission, dict) or not isinstance(mission.get("assignments"), list):
                continue
            for assignment in mission.get("assignments", []):
                if not isinstance(assignment, dict):
                    continue
                key = (str(mission.get("mission_id", "")), str(assignment.get("assignment_id", "")))
                if exclude == key:
                    continue
                if assignment.get("writable") and assignment.get("status") in WRITE_ASSIGNMENT_STATES:
                    yield key[0], assignment

    def acquire_lease(self, mission_id: str, assignment_id: str, *, holder: str = "") -> dict[str, Any]:
        with self._locked():
            mission = self.load_mission(mission_id)
            assignment = self._find_assignment(mission, assignment_id)
            if not assignment["writable"]:
                assignment["status"] = "leased"
                assignment["lease"] = {"holder": holder or assignment["provider"], "acquired_at": _now_iso()}
                self.save_mission(mission, event="lease-acquired", assignment_id=assignment_id)
                return dict(assignment)
            worktree = Path(assignment["worktree"]).resolve()
            if worktree == self.repo_root:
                raise RuntimeError("Writable assignment targets the main checkout.")
            for other_mission, other in self._active_write_assignments(exclude=(mission_id, assignment_id)):
                same_worktree = Path(other["worktree"]).resolve() == worktree
                overlap = scopes_overlap(assignment["owned_paths"], other["owned_paths"])
                if same_worktree or overlap:
                    reason = f"collision with {other_mission}/{other['assignment_id']}"
                    assignment["status"] = "blocked"
                    assignment["evidence"] = {"collision": reason, "recorded_at": _now_iso()}
                    self.save_mission(mission, event="assignment-blocked", assignment_id=assignment_id, reason=reason)
                    raise RuntimeError(reason)
            assignment["status"] = "leased"
            assignment["lease"] = {
                "holder": holder or assignment["provider"],
                "acquired_at": _now_iso(),
                "expires_at": (datetime.now(timezone.utc) + timedelta(seconds=int(mission["timeout_seconds"]))).isoformat(),
                "worktree": str(worktree),
                "owned_paths": list(assignment["owned_paths"]),
            }
            self.save_mission(mission, event="lease-acquired", assignment_id=assignment_id)
            return dict(assignment)

    def claim_assignment(self, mission_id: str, assignment_id: str, *, claimed_by: str) -> dict[str, Any]:
        claimed_by = claimed_by.strip()
        if not claimed_by:
            raise ValueError("claimed_by is required")
        mission = self.load_mission(mission_id)
        assignment = self._find_assignment(mission, assignment_id)
        ready, reason = self._assignment_ready(mission, assignment)
        if not ready:
            raise RuntimeError(f"Assignment is not ready: {reason}")
        return self.acquire_lease(mission_id, assignment_id, holder=claimed_by)

    def release_lease(self, mission_id: str, assignment_id: str, *, status: str = "released") -> dict[str, Any]:
        with self._locked():
            mission = self.load_mission(mission_id)
            assignment = self._find_assignment(mission, assignment_id)
            assignment["status"] = status
            assignment["lease"] = {**dict(assignment.get("lease") or {}), "released_at": _now_iso()}
            self.save_mission(mission, event="lease-released", assignment_id=assignment_id, status=status)
            return dict(assignment)

    def reclaim_expired_lease(self, mission_id: str, assignment_id: str, *, approved_by: str) -> dict[str, Any]:
        approved_by = approved_by.strip()
        if not approved_by:
            raise ValueError("approved_by is required")
        with self._locked():
            mission = self.load_mission(mission_id)
            assignment = self._find_assignment(mission, assignment_id)
            if assignment.get("status") not in WRITE_ASSIGNMENT_STATES:
                raise RuntimeError("Only an active writable lease can be reclaimed.")
            expires_at = str((assignment.get("lease") or {}).get("expires_at", ""))
            try:
                expired = bool(expires_at) and datetime.fromisoformat(expires_at) < datetime.now(timezone.utc)
            except ValueError as exc:
                raise RuntimeError("Lease expiry is invalid; manual recovery required.") from exc
            if not expired:
                raise RuntimeError("Lease has not expired.")
            assignment["status"] = "expired"
            assignment["lease"] = {
                **dict(assignment.get("lease") or {}),
                "reclaimed_at": _now_iso(),
                "reclaimed_by": approved_by,
            }
            self.save_mission(mission, event="lease-reclaimed", assignment_id=assignment_id, approved_by=approved_by)
            return dict(assignment)

    def retry_assignment(self, mission_id: str, assignment_id: str, *, approved_by: str) -> dict[str, Any]:
        approved_by = approved_by.strip()
        if not approved_by:
            raise ValueError("approved_by is required")
        with self._locked():
            mission = self.load_mission(mission_id)
            assignment = self._find_assignment(mission, assignment_id)
            if not assignment.get("writable"):
                raise RuntimeError("Only writable assignments use the retry lifecycle.")
            if assignment.get("status") not in {"failed", "expired", "blocked"}:
                raise RuntimeError("Assignment is not in a retryable state.")
            worktree = Path(str(assignment.get("worktree", "")))
            if not worktree.is_dir() or worktree.resolve() == self.repo_root:
                raise RuntimeError("Retry requires the original isolated worktree.")
            branch = _run(
                ["git", "branch", "--show-current"], cwd=worktree, timeout=15
            ).stdout.strip()
            if branch != assignment.get("branch"):
                raise RuntimeError("Retry worktree is on the wrong branch.")
            prior = dict(assignment.get("evidence") or {})
            history = [dict(item) for item in assignment.get("evidence_history", []) if isinstance(item, dict)]
            if prior:
                history.append(prior)
            assignment["evidence_history"] = history[-20:]
            assignment["evidence"] = {}
            assignment["lease"] = {}
            assignment["status"] = "provisioned"
            assignment["retry_count"] = int(assignment.get("retry_count", 0)) + 1
            assignment["retry_approved_by"] = approved_by
            assignment["retry_approved_at"] = _now_iso()
            self.save_mission(
                mission,
                event="assignment-retry-approved",
                assignment_id=assignment_id,
                approved_by=approved_by,
            )
            return dict(assignment)

    def build_prompt(self, mission: dict[str, Any], assignment: dict[str, Any]) -> str:
        charter = charter_for_duty(str(assignment.get("duty") or ""))
        stored_office = str(assignment.get("office") or charter["office"])
        if stored_office != charter["office"]:
            raise ValueError(
                f"Assignment office {stored_office} conflicts with duty {assignment.get('duty')}"
            )
        recorded_version = str(
            assignment.get("charter_version")
            or mission.get("charter_version")
            or CHARTER_VERSION
        )
        contract = dict(mission.get("architecture_contract") or {})
        contract_instruction = (
            f"Frozen Architect contract: {contract.get('reference')} "
            f"(sha256 {contract.get('sha256')}, baseline {contract.get('baseline_commit')}). "
            "Follow this immutable recorded content before acting:\n"
            f"<frozen-architect-contract>\n{contract.get('content')}\n</frozen-architect-contract>"
            if contract.get("status") == "frozen"
            else "Frozen Architect contract: MISSING. Build work must not begin."
        )
        return "\n".join(
            [
                str(assignment.get("onboarding_brief") or onboarding_brief(charter["office"])),
                f"This assignment is governed by recorded charter version: {recorded_version}",
                contract_instruction,
                f"Mission: {mission['request']}",
                f"Duty: {assignment['duty']}",
                f"Writable: {assignment['writable']}",
                f"Owned paths: {', '.join(assignment['owned_paths'])}",
                f"Forbidden paths: {', '.join(assignment['forbidden_paths'])}",
                "Do not switch branches, touch main, push, merge, clean unrelated files, or exceed this scope.",
                "Ground every completion claim in changed-file, test, and Git evidence.",
            ]
        )

    def adapter_command(self, mission: dict[str, Any], assignment: dict[str, Any]) -> list[str]:
        prompt = self.build_prompt(mission, assignment)
        worktree = str(assignment["worktree"])
        if assignment["provider"] == "claude":
            command = [
                "claude",
                "-p",
                "--output-format",
                "json",
                "--max-budget-usd",
                str(mission["budget_usd"]),
                "--permission-mode",
                "acceptEdits" if assignment["writable"] else "plan",
                "--disallowedTools",
                "Bash(git push:*) Bash(git checkout:*) Bash(git switch:*) Bash(git merge:*) Bash(git worktree remove:*) Bash(git branch -D:*)",
                prompt,
            ]
        elif assignment["provider"] == "codex":
            command = [
                "codex",
                "exec",
                "--ephemeral",
                "--json",
                "-C",
                worktree,
                "-s",
                "workspace-write" if assignment["writable"] else "read-only",
                "-a",
                "never",
                prompt,
            ]
        else:
            raise ValueError(f"Unsupported provider: {assignment['provider']}")
        return command

    def dispatch(self, mission_id: str, assignment_id: str, *, dry_run: bool = False) -> dict[str, Any]:
        mission = self.load_mission(mission_id)
        if mission["risk"] == "critical" and not bool((mission.get("approvals") or {}).get("dispatch")):
            raise RuntimeError("Critical-risk mission requires explicit dispatch approval.")
        planned = self._find_assignment(mission, assignment_id)
        cwd = Path(planned["worktree"])
        if planned["writable"] and not dry_run:
            if planned["status"] != "provisioned" or not cwd.is_dir():
                raise RuntimeError("Writable assignment worktree is not provisioned; refusing to run in the main checkout.")
            if cwd.resolve() == self.repo_root:
                raise RuntimeError("Writable assignment may not dispatch in the main checkout.")
        elif planned["duty"] == "review" and not cwd.is_dir() and not dry_run:
            raise RuntimeError("Review target worktree is unavailable; refusing to review the wrong checkout.")
        elif planned["duty"] == "analysis" and not cwd.is_dir():
            cwd = self.repo_root
        ready, reason = self._assignment_ready(mission, planned)
        if not ready:
            raise RuntimeError(f"Assignment is not ready: {reason}")
        assignment = self.acquire_lease(mission_id, assignment_id)
        mission = self.load_mission(mission_id)
        command = self.adapter_command(mission, assignment)
        if dry_run:
            self.release_lease(mission_id, assignment_id, status="provisioned" if assignment["writable"] else "planned")
            return {"dry_run": True, "command": command, "display_command": shlex.join(command)}
        started = _now_iso()
        timeout = int(mission["timeout_seconds"])
        if assignment["provider"] == "codex":
            timeout = min(timeout, max(60, int(float(mission["budget_usd"]) * 300)))
        try:
            completed = _run(command, cwd=cwd, timeout=timeout, check=False)
            evidence = self.capture_evidence(
                cwd,
                completed.returncode,
                completed.stdout,
                completed.stderr,
                started,
                baseline_commit=str(mission["baseline_commit"]),
            )
            violations = self._scope_violations(assignment, evidence["changed_files"])
            if violations:
                evidence["scope_violations"] = violations
            final_status = "completed" if completed.returncode == 0 and not violations else "failed"
        except subprocess.TimeoutExpired as exc:
            evidence = {"started_at": started, "completed_at": _now_iso(), "timeout": True, "error": str(exc)}
            final_status = "failed"
        with self._locked():
            mission = self.load_mission(mission_id)
            assignment = self._find_assignment(mission, assignment_id)
            assignment["evidence"] = evidence
            assignment["status"] = final_status
            assignment["lease"] = {**dict(assignment.get("lease") or {}), "released_at": _now_iso()}
            self.save_mission(mission, event="assignment-finished", assignment_id=assignment_id, status=final_status)
        return {"status": final_status, "evidence": evidence}

    def approve_dispatch(self, mission_id: str, *, approved_by: str) -> dict[str, Any]:
        approved_by = approved_by.strip()
        if not approved_by:
            raise ValueError("approved_by is required")
        with self._locked():
            mission = self.load_mission(mission_id)
            mission["approvals"] = {
                **dict(mission.get("approvals") or {}),
                "dispatch": True,
                "dispatch_approved_at": _now_iso(),
                "dispatch_approved_by": approved_by,
            }
            self.save_mission(mission, event="dispatch-approved", approved_by=approved_by)
            return dict(mission["approvals"])

    def _scope_violations(self, assignment: dict[str, Any], changed_files: list[str]) -> list[str]:
        if not assignment.get("writable"):
            return list(changed_files)
        owned = [str(item).casefold() for item in assignment.get("owned_paths", [])]
        forbidden = [str(item).casefold() for item in assignment.get("forbidden_paths", [])]
        violations: list[str] = []
        for path in changed_files:
            normalized = path.strip().lstrip("./").casefold()
            allowed = any(fnmatch.fnmatch(normalized, pattern) for pattern in owned)
            denied = any(fnmatch.fnmatch(normalized, pattern) for pattern in forbidden)
            if not allowed or denied:
                violations.append(path)
        return sorted(set(violations))

    def capture_evidence(
        self,
        cwd: Path,
        exit_code: int,
        stdout: str,
        stderr: str,
        started: str,
        *,
        baseline_commit: str,
    ) -> dict[str, Any]:
        changed_files: list[str] = []
        commit = ""
        if (cwd / ".git").exists() or (cwd / ".git").is_file():
            try:
                committed = _run(
                    ["git", "diff", "--name-only", f"{baseline_commit}...HEAD"], cwd=cwd
                ).stdout.splitlines()
                working = _run(
                    ["git", "status", "--porcelain=v1", "--untracked-files=all"], cwd=cwd
                ).stdout.splitlines()
                changed_files = sorted(set(committed + [line[3:] for line in working if len(line) > 3]))
                commit = _run(["git", "rev-parse", "HEAD"], cwd=cwd).stdout.strip()
            except subprocess.SubprocessError:
                pass
        return {
            "exit_code": exit_code,
            "started_at": started,
            "completed_at": _now_iso(),
            "commit": commit,
            "changed_files": changed_files,
            "target_fingerprint": self._worktree_fingerprint(cwd, changed_files),
            "stdout_tail": _redact_output(stdout[-8000:]),
            "stderr_tail": _redact_output(stderr[-4000:]),
        }

    def _worktree_fingerprint(self, cwd: Path, changed_files: list[str]) -> str:
        if not ((cwd / ".git").exists() or (cwd / ".git").is_file()):
            return ""
        try:
            commit = _run(["git", "rev-parse", "HEAD"], cwd=cwd).stdout.strip()
            status = _run(
                ["git", "status", "--porcelain=v1", "--untracked-files=all"], cwd=cwd
            ).stdout
            tracked_diff = _run(["git", "diff", "--binary", "HEAD"], cwd=cwd).stdout
        except (subprocess.SubprocessError, OSError):
            return ""
        digest = hashlib.sha256()
        digest.update(commit.encode())
        digest.update(b"\0")
        digest.update(status.encode())
        digest.update(b"\0tracked-diff\0")
        digest.update(tracked_diff.encode())
        for relative in sorted(set(changed_files)):
            digest.update(b"\0path\0")
            digest.update(relative.encode())
            path = cwd / relative
            if path.is_symlink():
                digest.update(b"\0symlink\0")
                digest.update(os.readlink(path).encode())
            elif path.is_file():
                digest.update(b"\0file\0")
                try:
                    digest.update(path.read_bytes())
                except OSError:
                    return ""
            else:
                digest.update(b"\0missing\0")
        return digest.hexdigest()

    def _review_target_unchanged(
        self, mission: dict[str, Any], implementation: dict[str, Any]
    ) -> tuple[bool, str]:
        evidence = dict(implementation.get("evidence") or {})
        recorded = str(evidence.get("target_fingerprint") or "")
        changed_files = [str(item) for item in evidence.get("changed_files", [])]
        worktree = Path(str(implementation.get("worktree") or ""))
        if not recorded or not worktree.is_dir():
            return False, "implementation review target is not frozen"
        current = self._worktree_fingerprint(worktree, changed_files)
        if not current or current != recorded:
            return False, "implementation review target changed after Build handoff"
        return True, "implementation review target is unchanged"

    def submit_result(
        self,
        mission_id: str,
        assignment_id: str,
        *,
        completed_by: str,
        status: str,
        summary: str,
        findings: list[str] | None = None,
        tests: list[str] | None = None,
    ) -> dict[str, Any]:
        completed_by = completed_by.strip()
        status = status.strip().lower()
        summary = summary.strip()
        if not completed_by:
            raise ValueError("completed_by is required")
        if status not in MANUAL_RESULT_STATES:
            raise ValueError(f"status must be one of: {', '.join(sorted(MANUAL_RESULT_STATES))}")
        if not summary:
            raise ValueError("summary is required")
        with self._locked():
            mission = self.load_mission(mission_id)
            assignment = self._find_assignment(mission, assignment_id)
            current_status = str(assignment.get("status") or "")
            if current_status in TERMINAL_ASSIGNMENT_STATES:
                raise RuntimeError("Assignment is already terminal.")
            if assignment.get("duty") == "review":
                implementation = next(
                    (item for item in mission["assignments"] if item.get("duty") == "implementation"),
                    {},
                )
                unchanged, reason = self._review_target_unchanged(mission, implementation)
                if not unchanged:
                    raise RuntimeError(reason)
            base_evidence: dict[str, Any]
            if assignment.get("writable"):
                worktree = Path(str(assignment.get("worktree") or ""))
                if not worktree.is_dir() or worktree.resolve() == self.repo_root:
                    raise RuntimeError("Writable submission requires the original isolated worktree.")
                base_evidence = self.capture_evidence(
                    worktree,
                    0 if status == "completed" else 1,
                    "",
                    "",
                    str((assignment.get("lease") or {}).get("acquired_at") or _now_iso()),
                    baseline_commit=str(mission["baseline_commit"]),
                )
                violations = self._scope_violations(assignment, base_evidence["changed_files"])
                if violations:
                    base_evidence["scope_violations"] = violations
                    status = "failed"
            else:
                base_evidence = {
                    "exit_code": 0 if status == "completed" else 1,
                    "started_at": str((assignment.get("lease") or {}).get("acquired_at") or _now_iso()),
                    "completed_at": _now_iso(),
                    "commit": "",
                    "changed_files": [],
                    "stdout_tail": "",
                    "stderr_tail": "",
                }
            evidence = {
                **base_evidence,
                "summary": summary,
                "findings": [item.strip() for item in (findings or []) if item.strip()],
                "tests": [item.strip() for item in (tests or []) if item.strip()],
                "completed_by": completed_by,
                "manual_result": True,
                "verdict": status,
            }
            assignment["evidence"] = evidence
            assignment["status"] = status
            assignment["lease"] = {**dict(assignment.get("lease") or {}), "released_at": _now_iso()}
            self.save_mission(
                mission,
                event="assignment-finished",
                assignment_id=assignment_id,
                status=status,
                completed_by=completed_by,
            )
            return {"status": status, "evidence": evidence}

    def release_plan(self, mission_id: str) -> dict[str, Any]:
        with self._locked():
            mission = self.load_mission(mission_id)
            reasons: list[str] = []
            implementation = [a for a in mission["assignments"] if a["duty"] == "implementation"]
            analyses = [a for a in mission["assignments"] if a["duty"] == "analysis"]
            reviews = [a for a in mission["assignments"] if a["duty"] == "review"]
            contract = mission.get("architecture_contract") or {}
            if contract.get("status") != "frozen" or not str(contract.get("reference") or "").strip():
                reasons.append("frozen Architect contract missing")
            if not implementation or any(a["status"] != "completed" for a in implementation):
                reasons.append("implementation incomplete")
            if mission["requires_cross_review"] and (not reviews or any(a["status"] != "completed" for a in reviews)):
                reasons.append("independent review incomplete")
            if reviews and all(a["status"] == "completed" for a in reviews) and implementation:
                unchanged, reason = self._review_target_unchanged(mission, implementation[0])
                if not unchanged:
                    reasons.append(reason)
            if mission["risk"] in {"high", "critical"} and (not analyses or any(a["status"] != "completed" for a in analyses)):
                reasons.append("required analysis incomplete")
            for assignment in mission["assignments"]:
                if assignment["status"] in {"failed", "blocked", "running", "leased"}:
                    reasons.append(f"{assignment['assignment_id']} is {assignment['status']}")
                if assignment["status"] == "completed" and not assignment.get("evidence"):
                    reasons.append(f"{assignment['assignment_id']} has no evidence")
                if assignment["duty"] == "implementation" and assignment["status"] == "completed":
                    evidence = dict(assignment.get("evidence") or {})
                    if evidence.get("commit") == mission["baseline_commit"] or not evidence.get("changed_files"):
                        reasons.append(f"{assignment['assignment_id']} produced no changes")
                    if evidence.get("scope_violations"):
                        reasons.append(f"{assignment['assignment_id']} changed files outside its lease")
                expires_at = str((assignment.get("lease") or {}).get("expires_at", ""))
                if assignment["status"] in WRITE_ASSIGNMENT_STATES and expires_at:
                    try:
                        if datetime.fromisoformat(expires_at) < datetime.now(timezone.utc):
                            reasons.append(f"{assignment['assignment_id']} lease expired")
                    except ValueError:
                        reasons.append(f"{assignment['assignment_id']} lease expiry is invalid")
            if self._repo_changes():
                reasons.append("main checkout is dirty")
            plan = {
                "status": "blocked" if reasons else "approval-required",
                "reasons": sorted(set(reasons)),
                "baseline_commit": mission["baseline_commit"],
                "main_head": self._git("rev-parse", "HEAD"),
                "mutated_git": False,
                "approval_required": True,
            }
            mission["release"] = plan
            self.save_mission(mission, event="release-planned", status=plan["status"])
            return plan

    def cleanup_plan(self, mission_id: str) -> dict[str, Any]:
        mission = self.load_mission(mission_id)
        removable: list[str] = []
        blocked: list[str] = []
        for assignment in mission["assignments"]:
            worktree = Path(assignment["worktree"])
            if not assignment["writable"] or not worktree.exists():
                continue
            if assignment["status"] in WRITE_ASSIGNMENT_STATES:
                blocked.append(str(worktree))
                continue
            try:
                status = _run(
                    ["git", "status", "--porcelain=v1"], cwd=worktree, check=False, timeout=15
                ).stdout.strip()
            except (subprocess.SubprocessError, OSError):
                blocked.append(str(worktree))
                continue
            (blocked if status else removable).append(str(worktree))
        return {"removable_worktrees": removable, "blocked_worktrees": blocked, "mutated_git": False}
