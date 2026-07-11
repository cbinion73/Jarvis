from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import time
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
OFFICE_HEARTBEAT_NAMES = {"architect"}
RECOVERABLE_REVIEW_STATES = {"failed", "blocked", "leased", "running"}
SUPERSEDED_ASSIGNMENT_STATUS = "superseded"
SUPERSEDED_RECOVERY_ARTIFACTS = {
    ("bo-control-plane-qa-dispatch-recovery-8117af25", "claude-analysis"): [
        "_bmad-output/implementation-artifacts/evidence/CONTROL-PLANE-QA-DISPATCH-RECOVERY-AC7-AC9-EVIDENCE.md",
    ],
    ("bo-control-plane-qa-dispatch-recovery-replacement-ac9d2a79", "codex-implementation"): [
        "_bmad-output/implementation-artifacts/evidence/D0-1-DEPLOYMENT-SECRET-HYGIENE-QA-REPAIR-APPROVAL.md",
    ],
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return cleaned[:48] or "mission"


def _normalize_repo_path(value: str) -> str:
    normalized = value.strip().replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    normalized = re.sub(r"/{2,}", "/", normalized)
    return normalized.strip("/")


def _run(
    args: Sequence[str],
    *,
    cwd: Path,
    timeout: int = 30,
    check: bool = True,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        cwd=str(cwd),
        input=input_text,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=check,
    )


def _static_prefix(pattern: str) -> str:
    normalized = _normalize_repo_path(pattern).casefold()
    wildcard = min(
        [index for token in "*[?" if (index := normalized.find(token)) >= 0]
        or [len(normalized)]
    )
    return normalized[:wildcard].rstrip("/")


def scopes_overlap(left: Sequence[str], right: Sequence[str]) -> bool:
    """Conservatively report whether two writable glob sets may touch one path."""
    for first in left:
        for second in right:
            a = _normalize_repo_path(first).casefold()
            b = _normalize_repo_path(second).casefold()
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
        review_provider: str | None = None,
        include_analysis: bool = True,
        owned_paths: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        worktree_root = self.repo_root.parent
        slug = mission_id.removeprefix("bo-")
        implementer = implementer.strip().lower()
        if implementer not in {"claude", "codex"}:
            raise ValueError("implementer must be claude or codex")
        reviewer = (review_provider or ("claude" if implementer == "codex" else "codex")).strip().lower()
        if reviewer not in {"claude", "codex"}:
            raise ValueError("review_provider must be claude or codex")
        scopes = [item.strip() for item in list(owned_paths or ["**"]) if item.strip()]
        if not scopes:
            raise ValueError("at least one owned path is required")
        assignments: list[dict[str, Any]] = []
        implementation_worktree = worktree_root / f"{self.repo_root.name}-{implementer}-{slug}"
        if include_analysis and risk in {"high", "critical"}:
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
        route_mode: str = "default",
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
        route_mode = route_mode.strip().lower()
        if route_mode not in {"default", "no-claude"}:
            raise ValueError("route_mode must be one of: default, no-claude")
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
        include_analysis = route_mode != "no-claude"
        review_provider = "codex" if route_mode == "no-claude" else None
        assignments = self._default_assignments(
            mission_id,
            risk,
            implementer=implementer,
            review_provider=review_provider,
            include_analysis=include_analysis,
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
            "route_mode": route_mode,
            "budget_enforcement": {
                "claude": "hard-dollar-cap",
                "codex": "time-proxy-only; CLI exposes no dollar-cap flag",
            },
            "requires_cross_review": risk in {"medium", "high", "critical"},
            "routing": {
                "implementer": implementer,
                "reviewer": review_provider or ("claude" if implementer == "codex" else "codex"),
            },
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

    def mission_ids(self) -> list[str]:
        if not self.state_root.exists():
            return []
        mission_ids: list[str] = []
        for path in sorted(self.state_root.glob("*/mission.json")):
            try:
                mission = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(mission, dict) and mission.get("mission_id"):
                mission_ids.append(str(mission["mission_id"]))
        return mission_ids

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

    def _mission_state_signature(self, mission: dict[str, Any]) -> str:
        relevant_assignments: list[dict[str, Any]] = []
        for assignment in mission.get("assignments", []):
            evidence = dict(assignment.get("evidence") or {})
            relevant_assignments.append(
                {
                    "assignment_id": assignment.get("assignment_id"),
                    "duty": assignment.get("duty"),
                    "office": assignment.get("office"),
                    "provider": assignment.get("provider"),
                    "status": assignment.get("status"),
                    "writable": assignment.get("writable"),
                    "lease": {
                        "holder": dict(assignment.get("lease") or {}).get("holder", ""),
                        "expires_at": dict(assignment.get("lease") or {}).get("expires_at", ""),
                    },
                    "evidence": {
                        "exit_code": evidence.get("exit_code"),
                        "commit": evidence.get("commit", ""),
                        "changed_files": evidence.get("changed_files", []),
                        "scope_violations": evidence.get("scope_violations", []),
                        "verdict": evidence.get("verdict", ""),
                        "target_fingerprint": evidence.get("target_fingerprint", ""),
                    },
                }
            )
        payload = {
            "mission_status": mission.get("status"),
            "risk": mission.get("risk"),
            "contract": {
                "status": dict(mission.get("architecture_contract") or {}).get("status"),
                "reference": dict(mission.get("architecture_contract") or {}).get("reference"),
                "sha256": dict(mission.get("architecture_contract") or {}).get("sha256"),
            },
            "approvals": mission.get("approvals", {}),
            "assignments": relevant_assignments,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    def _heartbeat_actions(self, mission: dict[str, Any]) -> list[dict[str, Any]]:
        actions: list[dict[str, Any]] = []
        contract = dict(mission.get("architecture_contract") or {})
        if contract.get("status") != "frozen" or not str(contract.get("reference") or "").strip():
            actions.append(
                {
                    "kind": "awaiting-architect-contract",
                    "office": "architect",
                    "summary": "Build remains blocked until Architect supplies a frozen committed contract.",
                }
            )
        for assignment in mission.get("assignments", []):
            assignment_id = str(assignment.get("assignment_id") or "")
            duty = str(assignment.get("duty") or "")
            office = str(assignment.get("office") or office_for_duty(duty))
            status = str(assignment.get("status") or "")
            ready, reason = self._assignment_ready(mission, assignment)
            if ready:
                kind = {
                    "analysis": "route-to-architect",
                    "implementation": "route-to-build",
                    "review": "route-to-quality",
                }.get(duty, "route-ready-assignment")
                actions.append(
                    {
                        "kind": kind,
                        "office": office,
                        "assignment_id": assignment_id,
                        "provider": str(assignment.get("provider") or ""),
                        "summary": reason,
                    }
                )
            elif status in {"planned", "provisioned"} and reason:
                actions.append(
                    {
                        "kind": "waiting",
                        "office": office,
                        "assignment_id": assignment_id,
                        "provider": str(assignment.get("provider") or ""),
                        "summary": reason,
                    }
                )
            if status in {"failed", "blocked"}:
                actions.append(
                    {
                        "kind": "disposition-required" if duty == "review" else "repair-or-retry-required",
                        "office": "architect",
                        "assignment_id": assignment_id,
                        "provider": str(assignment.get("provider") or ""),
                        "summary": f"{assignment_id} is {status}; Architect must classify and route the supported next move.",
                    }
                )
            expires_at = str((assignment.get("lease") or {}).get("expires_at", ""))
            if status in WRITE_ASSIGNMENT_STATES and expires_at:
                try:
                    expired = datetime.fromisoformat(expires_at) < datetime.now(timezone.utc)
                except ValueError:
                    expired = False
                    actions.append(
                        {
                            "kind": "lease-recovery-required",
                            "office": "architect",
                            "assignment_id": assignment_id,
                            "summary": "Lease expiry is invalid; manual recovery required.",
                        }
                    )
                if expired:
                    actions.append(
                        {
                            "kind": "lease-recovery-required",
                            "office": "architect",
                            "assignment_id": assignment_id,
                            "summary": "Lease expired; reclaim through the recorded recovery path.",
                        }
                    )
        if self._repo_changes():
            actions.append(
                {
                    "kind": "main-dirty",
                    "office": "architect",
                    "summary": "Main checkout is dirty; intake and release gates remain blocked.",
                }
            )
        return actions

    def heartbeat(
        self,
        mission_id: str | None = None,
        *,
        actor: str = "Architect heartbeat",
        interval_seconds: int = 300,
        dispatch_ready: bool = False,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        actor = actor.strip() or "Architect heartbeat"
        mission_ids = [mission_id] if mission_id else self.mission_ids()
        summaries: list[dict[str, Any]] = []
        for current_id in mission_ids:
            with self._locked():
                mission = self.load_mission(str(current_id))
                signature = self._mission_state_signature(mission)
                prior = dict(mission.get("heartbeat") or {})
                unchanged = signature == str(prior.get("last_state_signature") or "")
                detected_actions = self._heartbeat_actions(mission)
                actions = [] if unchanged else detected_actions
                route_actions = [item for item in actions if str(item.get("kind", "")).startswith("route-to-")]
                heartbeat_state = {
                    "last_at": _now_iso(),
                    "last_by": actor,
                    "interval_seconds": int(interval_seconds),
                    "last_state_signature": signature,
                    "unchanged_cycles": int(prior.get("unchanged_cycles", 0)) + 1 if unchanged else 0,
                    "last_action_count": len(actions),
                    "suppressed_action_count": len(detected_actions) if unchanged else 0,
                    "last_route_count": len(route_actions),
                }
                mission["heartbeat"] = heartbeat_state
                self.save_mission(
                    mission,
                    event="heartbeat-noop" if unchanged and not actions else "heartbeat-routed",
                    actor=actor,
                    unchanged=unchanged,
                    action_count=len(actions),
                    route_count=len(route_actions),
                )
            summary: dict[str, Any] = {
                "mission_id": str(current_id),
                "unchanged": unchanged,
                "heartbeat": heartbeat_state,
                "actions": actions,
            }
            if dispatch_ready:
                dispatches: list[dict[str, Any]] = []
                latest = self.load_mission(str(current_id))
                for action in route_actions:
                    assignment_id = str(action.get("assignment_id") or "")
                    if not assignment_id:
                        continue
                    try:
                        dispatches.append(
                            {
                                "assignment_id": assignment_id,
                                "dry_run": dry_run,
                                "result": self.dispatch(str(current_id), assignment_id, dry_run=dry_run),
                            }
                        )
                    except (RuntimeError, ValueError, KeyError) as exc:
                        dispatches.append(
                            {
                                "assignment_id": assignment_id,
                                "dry_run": dry_run,
                                "error": str(exc),
                            }
                        )
                summary["dispatches"] = dispatches
            summaries.append(summary)
        return {
            "ok": True,
            "generated_at": _now_iso(),
            "actor": actor,
            "interval_seconds": int(interval_seconds),
            "mission_count": len(summaries),
            "missions": summaries,
        }

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
            target_ready, reason, _ = self._review_target_state(mission, assignment)
            if not target_ready:
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

    def _heartbeat_state_path(self, office: str) -> Path:
        return self.state_root / "heartbeats" / f"{office}.json"

    def _mission_summaries(self) -> list[dict[str, Any]]:
        missions: list[dict[str, Any]] = []
        if not self.state_root.exists():
            return missions
        for path in sorted(self.state_root.glob("*/mission.json")):
            try:
                mission = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(mission, dict) and isinstance(mission.get("assignments"), list):
                missions.append(mission)
        return missions

    def _close_superseded_recovery_failures(self) -> list[dict[str, Any]]:
        closed: list[dict[str, Any]] = []
        for mission in self._mission_summaries():
            mission_id = str(mission.get("mission_id") or "")
            changed = False
            for assignment in mission.get("assignments", []):
                if not isinstance(assignment, dict):
                    continue
                status = str(assignment.get("status") or "")
                if status not in {"failed", "blocked"}:
                    continue
                artifacts = self._superseding_recovery_artifacts(mission_id, assignment)
                if not artifacts:
                    continue
                assignment["status"] = SUPERSEDED_ASSIGNMENT_STATUS
                assignment["superseded_at"] = _now_iso()
                assignment["superseded_by"] = "Architect heartbeat"
                assignment["superseded_reason"] = "Committed durable evidence replaced this failure."
                assignment["superseded_by_artifacts"] = artifacts
                assignment["superseded_from_status"] = status
                closed.append(
                    {
                        "mission_id": mission_id,
                        "assignment_id": str(assignment.get("assignment_id") or ""),
                        "artifacts": artifacts,
                    }
                )
                changed = True
            if changed:
                self.save_mission(
                    mission,
                    event="assignment-superseded",
                    actor="Architect heartbeat",
                    reason="Committed durable evidence replaced this failure.",
                    closed_from_heartbeat=True,
                )
        return closed

    def _architect_heartbeat_actions(self) -> list[dict[str, Any]]:
        actions: list[dict[str, Any]] = []
        for mission in self._mission_summaries():
            mission_id = str(mission.get("mission_id") or "")
            assignments = [item for item in mission.get("assignments", []) if isinstance(item, dict)]
            for assignment in assignments:
                assignment_id = str(assignment.get("assignment_id") or "")
                duty = str(assignment.get("duty") or "")
                status = str(assignment.get("status") or "")
                office = str(assignment.get("office") or office_for_duty(duty) if duty else "")
                ready, reason = self._assignment_ready(mission, assignment)
                if office == "architect" and ready:
                    actions.append(
                        {
                            "kind": "architect-assignment-ready",
                            "mission_id": mission_id,
                            "assignment_id": assignment_id,
                            "severity": "action",
                            "summary": f"{assignment_id} is ready for Architect pickup.",
                            "command": (
                                "python3 scripts/jarvis_build_office.py claim "
                                f"{mission_id} {assignment_id} --by architect-office"
                            ),
                            "detail": reason,
                        }
                    )
                if status in {"failed", "blocked"}:
                    if self._superseding_recovery_artifacts(mission_id, assignment):
                        continue
                    evidence = dict(assignment.get("evidence") or {})
                    actions.append(
                        {
                            "kind": "assignment-needs-disposition",
                            "mission_id": mission_id,
                            "assignment_id": assignment_id,
                            "severity": "action",
                            "summary": f"{assignment_id} is {status}; Architect must classify the finding or failure.",
                            "detail": str(
                                evidence.get("summary")
                                or evidence.get("stderr_tail")
                                or evidence.get("provision_error")
                                or evidence.get("collision")
                                or ""
                            )[-1000:],
                        }
                    )
                expires_at = str((assignment.get("lease") or {}).get("expires_at") or "")
                if status in WRITE_ASSIGNMENT_STATES and expires_at:
                    try:
                        expired = datetime.fromisoformat(expires_at) < datetime.now(timezone.utc)
                    except ValueError:
                        expired = True
                    if expired:
                        actions.append(
                            {
                                "kind": "lease-needs-recovery",
                                "mission_id": mission_id,
                                "assignment_id": assignment_id,
                                "severity": "action",
                                "summary": f"{assignment_id} has an expired or invalid lease.",
                                "command": (
                                    "python3 scripts/jarvis_build_office.py reclaim-lease "
                                    f"{mission_id} {assignment_id} --by Chris"
                                ),
                            }
                        )
            implementations = [item for item in assignments if item.get("duty") == "implementation"]
            reviews = [item for item in assignments if item.get("duty") == "review"]
            if implementations and all(item.get("status") == "completed" for item in implementations):
                for review in reviews:
                    if review.get("status") in {"planned", "provisioned"}:
                        ready, reason = self._assignment_ready(mission, review)
                        if ready:
                            actions.append(
                                {
                                    "kind": "route-build-to-quality",
                                    "mission_id": mission_id,
                                    "assignment_id": str(review.get("assignment_id") or ""),
                                    "severity": "action",
                                    "summary": "Build evidence is complete and Quality review is ready.",
                                    "command": (
                                        "python3 scripts/jarvis_build_office.py dispatch "
                                        f"{mission_id} {review.get('assignment_id')} --dry-run"
                                    ),
                                    "detail": reason,
                                }
                            )
            if mission.get("status") in {"blocked", "failed"}:
                actions.append(
                    {
                        "kind": "mission-needs-architect-attention",
                        "mission_id": mission_id,
                        "assignment_id": "",
                        "severity": "action",
                        "summary": f"Mission is {mission.get('status')}; Architect should classify the blocker.",
                    }
                )
        if self._repo_changes():
            actions.append(
                {
                    "kind": "main-checkout-dirty",
                    "mission_id": "",
                    "assignment_id": "",
                    "severity": "blocker",
                    "summary": "Main checkout is dirty; mission intake and release gates are blocked.",
                    "command": "git status --short",
                }
            )
        return sorted(
            actions,
            key=lambda item: (
                str(item.get("severity") or ""),
                str(item.get("mission_id") or ""),
                str(item.get("assignment_id") or ""),
                str(item.get("kind") or ""),
            ),
        )

    @staticmethod
    def _heartbeat_signature(actions: list[dict[str, Any]]) -> str:
        stable_actions = [
            {
                "kind": item.get("kind", ""),
                "mission_id": item.get("mission_id", ""),
                "assignment_id": item.get("assignment_id", ""),
                "summary": item.get("summary", ""),
                "detail": item.get("detail", ""),
            }
            for item in actions
        ]
        payload = json.dumps(stable_actions, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()

    def office_heartbeat(self, office: str = "architect", *, cadence_seconds: int = 300) -> dict[str, Any]:
        office = office.strip().lower()
        if office not in OFFICE_HEARTBEAT_NAMES:
            raise ValueError(f"office heartbeat must be one of: {', '.join(sorted(OFFICE_HEARTBEAT_NAMES))}")
        if cadence_seconds <= 0:
            raise ValueError("cadence_seconds must be positive")
        with self._locked():
            if office == "architect":
                self._close_superseded_recovery_failures()
                actions = self._architect_heartbeat_actions()
            else:
                raise AssertionError(office)
            signature = self._heartbeat_signature(actions)
            state_path = self._heartbeat_state_path(office)
            prior: dict[str, Any] = {}
            if state_path.exists():
                try:
                    parsed = json.loads(state_path.read_text(encoding="utf-8"))
                    if isinstance(parsed, dict):
                        prior = parsed
                except (OSError, json.JSONDecodeError):
                    prior = {}
            previous_signature = str(prior.get("state_signature") or "")
            changed_since_last = signature != previous_signature
            needs_action = bool(actions)
            generated_at = _now_iso()
            payload = {
                "office": office,
                "cadence_seconds": cadence_seconds,
                "generated_at": generated_at,
                "status": "attention-required" if needs_action else "idle",
                "needs_action": needs_action,
                "changed_since_last": changed_since_last,
                "state_signature": signature,
                "previous_signature": previous_signature,
                "next_check_after_seconds": cadence_seconds,
                "summary": (
                    f"{len(actions)} action(s) need Architect attention."
                    if needs_action
                    else "No material control-plane changes. Architect can stay idle."
                ),
                "actions": actions,
            }
            state_path.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_json(
                state_path,
                {
                    "office": office,
                    "cadence_seconds": cadence_seconds,
                    "last_checked_at": generated_at,
                    "state_signature": signature,
                    "needs_action": needs_action,
                    "action_count": len(actions),
                },
            )
            self._append_event(
                "office-heartbeat",
                f"office-{office}",
                office=office,
                needs_action=needs_action,
                changed_since_last=changed_since_last,
                action_count=len(actions),
            )
            return payload

    def watch_office_heartbeat(
        self,
        office: str = "architect",
        *,
        cadence_seconds: int = 300,
        max_iterations: int = 0,
    ) -> Iterator[dict[str, Any]]:
        iterations = 0
        while True:
            iterations += 1
            yield self.office_heartbeat(office, cadence_seconds=cadence_seconds)
            if max_iterations and iterations >= max_iterations:
                return
            time.sleep(cadence_seconds)

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

    def recover_review_assignment(
        self,
        mission_id: str,
        assignment_id: str,
        *,
        approved_by: str,
        reason: str,
    ) -> dict[str, Any]:
        approved_by = approved_by.strip()
        reason = reason.strip()
        if not approved_by:
            raise ValueError("approved_by is required")
        if not reason:
            raise ValueError("reason is required")
        with self._locked():
            mission = self.load_mission(mission_id)
            assignment = self._find_assignment(mission, assignment_id)
            if assignment.get("writable"):
                raise RuntimeError("Only non-writable review assignments can be recovered.")
            if assignment.get("duty") != "review":
                raise RuntimeError("Only review assignments can be recovered.")
            status = str(assignment.get("status") or "")
            recovery = dict(assignment.get("recovery") or {})
            if (
                status == "planned"
                and recovery.get("approved_by") == approved_by
                and recovery.get("reason") == reason
            ):
                return dict(assignment)
            if status == "completed":
                raise RuntimeError("Successful completed reviews may not be recovered.")
            if status not in RECOVERABLE_REVIEW_STATES:
                raise RuntimeError("Review assignment is not in a recoverable state.")
            recovered_at = _now_iso()
            history = [
                dict(item)
                for item in assignment.get("evidence_history", [])
                if isinstance(item, dict)
            ]
            prior_evidence = dict(assignment.get("evidence") or {})
            lease_snapshot = dict(assignment.get("lease") or {})
            snapshot = {
                **prior_evidence,
                "recovered_from_status": status,
                "recovered_by": approved_by,
                "recovery_reason": reason,
                "recovered_at": recovered_at,
                "lease_snapshot": lease_snapshot,
            }
            if snapshot and (not history or history[-1] != snapshot):
                history.append(snapshot)
            assignment["evidence_history"] = history[-20:]
            assignment["evidence"] = {}
            assignment["status"] = "planned"
            assignment["lease"] = {
                **lease_snapshot,
                "released_at": recovered_at,
                "recovered_at": recovered_at,
                "recovered_by": approved_by,
                "recovery_reason": reason,
            }
            assignment["recovery"] = {
                "approved_by": approved_by,
                "reason": reason,
                "recovered_at": recovered_at,
                "from_status": status,
            }
            self.save_mission(
                mission,
                event="review-recovered",
                assignment_id=assignment_id,
                approved_by=approved_by,
                reason=reason,
                from_status=status,
            )
            return dict(assignment)

    def _artifact_is_committed(self, artifact: str) -> bool:
        artifact = _normalize_repo_path(artifact)
        if not artifact:
            return False
        try:
            return _run(
                ["git", "cat-file", "-t", f"HEAD:{artifact}"], cwd=self.repo_root
            ).stdout.strip() == "blob"
        except (subprocess.SubprocessError, OSError):
            return False

    def _superseding_recovery_artifacts(
        self, mission_id: str, assignment: dict[str, Any]
    ) -> list[str]:
        key = (str(mission_id), str(assignment.get("assignment_id") or ""))
        artifacts = list(SUPERSEDED_RECOVERY_ARTIFACTS.get(key, []))
        artifacts.extend(str(item) for item in assignment.get("superseded_by_artifacts", []) if str(item).strip())
        return [artifact for artifact in artifacts if self._artifact_is_committed(artifact)]

    def supersede_assignment(
        self,
        mission_id: str,
        assignment_id: str,
        *,
        actor: str,
        reason: str,
        artifacts: list[str] | None = None,
    ) -> dict[str, Any]:
        actor = actor.strip()
        reason = reason.strip()
        if not actor:
            raise ValueError("actor is required")
        if not reason:
            raise ValueError("reason is required")
        with self._locked():
            mission = self.load_mission(mission_id)
            assignment = self._find_assignment(mission, assignment_id)
            status = str(assignment.get("status") or "")
            if status == SUPERSEDED_ASSIGNMENT_STATUS:
                return dict(assignment)
            if status not in {"failed", "blocked"}:
                raise RuntimeError("Only failed or blocked assignments can be superseded.")
            resolved_artifacts = [str(item).strip() for item in (artifacts or []) if str(item).strip()]
            if not resolved_artifacts:
                resolved_artifacts = self._superseding_recovery_artifacts(mission_id, assignment)
            if not resolved_artifacts:
                raise RuntimeError("Committed durable evidence is required to supersede the failure.")
            if not all(self._artifact_is_committed(item) for item in resolved_artifacts):
                raise RuntimeError("Superseding evidence must be committed durable evidence.")
            assignment["status"] = SUPERSEDED_ASSIGNMENT_STATUS
            assignment["superseded_at"] = _now_iso()
            assignment["superseded_by"] = actor
            assignment["superseded_reason"] = reason
            assignment["superseded_by_artifacts"] = resolved_artifacts
            assignment["superseded_from_status"] = status
            self.save_mission(
                mission,
                event="assignment-superseded",
                assignment_id=assignment_id,
                actor=actor,
                reason=reason,
                artifacts=resolved_artifacts,
                from_status=status,
            )
            return dict(assignment)

    def amend_terminal_assignment_evidence(
        self,
        mission_id: str,
        assignment_id: str,
        *,
        actor: str,
        reason: str,
    ) -> dict[str, Any]:
        actor = actor.strip()
        reason = reason.strip()
        if not actor:
            raise ValueError("actor is required")
        if not reason:
            raise ValueError("reason is required")
        with self._locked():
            mission = self.load_mission(mission_id)
            assignment = self._find_assignment(mission, assignment_id)
            if not assignment.get("writable"):
                raise RuntimeError("Only writable terminal assignments can be amended.")
            status = str(assignment.get("status") or "")
            if status not in TERMINAL_ASSIGNMENT_STATES:
                raise RuntimeError("Assignment is not terminal.")
            worktree = Path(str(assignment.get("worktree") or ""))
            if not worktree.is_dir() or worktree.resolve() == self.repo_root:
                raise RuntimeError("Amendment requires the original isolated worktree.")
            baseline_commit = str(mission.get("baseline_commit") or "").strip()
            if not baseline_commit:
                raise RuntimeError("Mission baseline commit is missing.")
            try:
                head_commit = _run(["git", "rev-parse", "HEAD"], cwd=worktree, timeout=15).stdout.strip()
            except (subprocess.SubprocessError, OSError) as exc:
                raise RuntimeError("Amendment requires a readable isolated worktree.") from exc
            if not head_commit or head_commit == baseline_commit:
                raise RuntimeError("Amendment requires a newer worktree commit than the mission baseline.")
            current_evidence = dict(assignment.get("evidence") or {})
            if any(
                item.get("duty") == "review" and str(item.get("status") or "") == "completed"
                for item in mission.get("assignments", [])
            ):
                raise RuntimeError("Completed QA approvals may not be amended.")
            fresh = self.capture_evidence(
                worktree,
                int(current_evidence.get("exit_code", 0) or 0),
                str(current_evidence.get("stdout_tail") or ""),
                str(current_evidence.get("stderr_tail") or ""),
                str(current_evidence.get("started_at") or _now_iso()),
                baseline_commit=baseline_commit,
            )
            violations = self._scope_violations(assignment, fresh["changed_files"])
            if violations:
                raise RuntimeError("Amendment would include out-of-scope or forbidden changes.")
            if not fresh["changed_files"]:
                raise RuntimeError("Amendment requires non-empty changed files.")
            if current_evidence.get("commit") == fresh["commit"] and current_evidence.get("changed_files") == fresh["changed_files"]:
                raise RuntimeError("Assignment evidence is already consistent; no amendment is needed.")
            history = [dict(item) for item in assignment.get("evidence_history", []) if isinstance(item, dict)]
            history.append(
                {
                    **current_evidence,
                    "original_commit": str(current_evidence.get("commit") or ""),
                    "original_baseline_commit": str(current_evidence.get("baseline_commit") or baseline_commit),
                    "original_changed_files": list(current_evidence.get("changed_files") or []),
                    "original_stdout_tail": str(current_evidence.get("stdout_tail") or ""),
                    "original_stderr_tail": str(current_evidence.get("stderr_tail") or ""),
                    "original_started_at": str(current_evidence.get("started_at") or ""),
                    "original_completed_at": str(current_evidence.get("completed_at") or ""),
                    "completion_actor": str(current_evidence.get("completed_by") or ""),
                    "correction_actor": actor,
                    "correction_reason": reason,
                    "correction_at": _now_iso(),
                }
            )
            assignment["evidence_history"] = history[-20:]
            corrected_at = _now_iso()
            corrected = {
                **fresh,
                "corrected_at": corrected_at,
                "corrected_by": actor,
                "correction_reason": reason,
                "amended_from_commit": str(current_evidence.get("commit") or ""),
                "amended_from_baseline_commit": str(current_evidence.get("baseline_commit") or baseline_commit),
            }
            assignment["evidence"] = corrected
            self.save_mission(
                mission,
                event="terminal-evidence-amended",
                assignment_id=assignment_id,
                actor=actor,
                reason=reason,
                amended_from_commit=str(current_evidence.get("commit") or ""),
                amended_to_commit=fresh["commit"],
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
        review_target_instruction = ""
        if assignment.get("duty") == "review":
            target_ready, _, target = self._review_target_state(mission, assignment)
            if target_ready:
                review_target_instruction = (
                    "Immutable review target: "
                    f"commit {target['commit']}, baseline {target['baseline_commit']}, "
                    f"fingerprint {target['target_fingerprint']}, "
                    f"changed files {', '.join(target['changed_files'])}."
                )
        return "\n".join(
            [
                str(assignment.get("onboarding_brief") or onboarding_brief(charter["office"])),
                f"This assignment is governed by recorded charter version: {recorded_version}",
                contract_instruction,
                review_target_instruction,
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
            if assignment.get("duty") == "review":
                target_ready, reason, target = self._review_target_state(mission, assignment)
                if not target_ready:
                    raise RuntimeError(f"Review assignment is not ready: {reason}")
                command = [
                    "codex",
                    "exec",
                    "--ephemeral",
                    "--json",
                    "-C",
                    worktree,
                    "-s",
                    "read-only",
                    "review",
                    "--commit",
                    target["commit"],
                    "--title",
                    f"{mission['mission_id']} immutable review",
                ]
            else:
                command = [
                    "codex",
                    "exec",
                    "--ephemeral",
                    "--json",
                    "-C",
                    worktree,
                    "-s",
                    "workspace-write" if assignment["writable"] else "read-only",
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
        stdin = None
        if dry_run:
            self.release_lease(mission_id, assignment_id, status="provisioned" if assignment["writable"] else "planned")
            return {
                "dry_run": True,
                "command": command,
                "display_command": shlex.join(command),
                "stdin": "[prompt via stdin]" if stdin else "",
            }
        started = _now_iso()
        timeout = int(mission["timeout_seconds"])
        if assignment["provider"] == "codex":
            timeout = min(timeout, max(60, int(float(mission["budget_usd"]) * 300)))
        with self._locked():
            mission = self.load_mission(mission_id)
            assignment = self._find_assignment(mission, assignment_id)
            assignment["status"] = "running"
            self.save_mission(mission, event="assignment-started", assignment_id=assignment_id)
        try:
            completed = _run(command, cwd=cwd, timeout=timeout, check=False, input_text=stdin)
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
            review_error = ""
            if assignment.get("duty") == "review":
                target_ready, reason, _ = self._review_target_state(mission, assignment)
                if not target_ready:
                    review_error = reason
                    evidence["review_target_error"] = reason
            final_status = (
                "completed"
                if completed.returncode == 0 and not violations and not review_error
                else "failed"
            )
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
        duty = str(assignment.get("duty") or "")
        if not assignment.get("writable") and duty != "review":
            return list(changed_files)
        owned = [str(item).casefold() for item in assignment.get("owned_paths", [])]
        forbidden = [str(item).casefold() for item in assignment.get("forbidden_paths", [])]
        violations: list[str] = []
        for path in changed_files:
            normalized = _normalize_repo_path(path).casefold()
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
            "baseline_commit": baseline_commit,
            "commit": commit,
            "changed_files": changed_files,
            "target_fingerprint": self._worktree_fingerprint(cwd, changed_files),
            "stdout_tail": _redact_output(stdout[-8000:]),
            "stderr_tail": _redact_output(stderr[-4000:]),
        }

    def _review_target_state(
        self,
        mission: dict[str, Any],
        review_assignment: dict[str, Any],
    ) -> tuple[bool, str, dict[str, Any]]:
        implementations = self._assignment_status(mission, "implementation")
        if not implementations:
            return False, "implementation review target is unavailable", {}
        implementation = implementations[0]
        evidence = dict(implementation.get("evidence") or {})
        commit = str(evidence.get("commit") or "").strip()
        changed_files = [str(item) for item in evidence.get("changed_files", [])]
        fingerprint = str(evidence.get("target_fingerprint") or "").strip()
        baseline_commit = str(
            evidence.get("baseline_commit") or mission.get("baseline_commit") or ""
        ).strip()
        worktree = Path(str(implementation.get("worktree") or ""))
        target = {
            "commit": commit,
            "baseline_commit": baseline_commit,
            "changed_files": changed_files,
            "target_fingerprint": fingerprint,
        }
        if not commit or not changed_files or not fingerprint or not worktree.is_dir():
            return False, "implementation review target is not frozen", target
        if baseline_commit != str(mission.get("baseline_commit") or ""):
            return (
                False,
                "implementation review target baseline no longer matches durable Build evidence",
                target,
            )
        try:
            current_commit = _run(["git", "rev-parse", "HEAD"], cwd=worktree, timeout=15).stdout.strip()
        except (subprocess.SubprocessError, OSError):
            return False, "implementation review target is unavailable", target
        if current_commit != commit:
            return False, "implementation review target commit changed after Build handoff", target
        violations = self._scope_violations(review_assignment, changed_files)
        if violations:
            target["scope_violations"] = violations
            forbidden = [str(item).casefold() for item in review_assignment.get("forbidden_paths", [])]
            if any(
                fnmatch.fnmatch(_normalize_repo_path(path).casefold(), pattern)
                for path in violations
                for pattern in forbidden
            ):
                return False, "implementation review target includes forbidden paths", target
            return False, "implementation review target changed files fall outside the review scope", target
        current_fingerprint = self._worktree_fingerprint(worktree, changed_files)
        if current_fingerprint != fingerprint:
            return False, "implementation review target changed after Build handoff", target
        return True, "implementation review target is unchanged", target

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
        review_assignment = {
            "duty": "review",
            "writable": False,
            "owned_paths": list(implementation.get("owned_paths") or []),
            "forbidden_paths": list(implementation.get("forbidden_paths") or []),
        }
        ready, reason, _ = self._review_target_state(mission, review_assignment)
        return ready, reason

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
                target_ready, reason, _ = self._review_target_state(mission, assignment)
                if not target_ready:
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
                    "baseline_commit": str(mission.get("baseline_commit") or ""),
                    "changed_files": [],
                    "stdout_tail": "",
                    "stderr_tail": "",
                }
                if assignment.get("duty") == "review":
                    _, _, target = self._review_target_state(mission, assignment)
                    if target:
                        base_evidence.update(target)
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
            if reviews and implementation:
                target_ready, reason, _ = self._review_target_state(mission, reviews[0])
                if not target_ready:
                    reasons.append(reason)
            if analyses and mission["risk"] in {"high", "critical"} and any(
                a["status"] != "completed" for a in analyses
            ):
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
