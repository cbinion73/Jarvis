#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SESSION_STATE_PATH = REPO_ROOT / "docs" / "JARVIS-SESSION-STATE.md"
DEFAULT_OUTPUT_PATH = REPO_ROOT / "artifacts" / "qa" / "level9-truth-report.json"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from jarvis.data_hygiene import record_looks_like_test_data, string_looks_like_test_data
from jarvis.runtime_posture import _build_deployment_context

LEVEL_EVIDENCE_MAP = {
    "Level 2: Unified Command Product": [
        "tests/e2e/jarvis-platform.e2e.cjs",
        "tests/test_glass_theme_shell.py",
    ],
    "Level 3: Household Operating System": [
        "tests/test_level3_exit_gate.py",
        "tests/test_phase_a_close_level3.py",
        "docs/JARVIS-LEVEL3-EXIT-REPORT.md",
    ],
    "Level 4: Governed Intelligence System": [
        "tests/test_phase_b_level4_governance.py",
        "tests/test_governance_authn.py",
        "tests/test_phase_b_trust_boundary_audit.py",
    ],
    "Level 5: Ambient Household Intelligence": [
        "tests/test_phase_d_ambient_voice_memory.py",
        "tests/test_phase_h5_proactive_orchestrator.py",
        "tests/test_level5_presence_routing.py",
    ],
    "Level 6: Memory and Continuity Engine": [
        "tests/test_phase_i_memory_improvements.py",
        "tests/test_truthful_seed_filtering.py",
        "tests/e2e/jarvis-memory-governance.e2e.cjs",
    ],
    "Level 7: Formation and Stewardship Platform": [
        "tests/test_phase_j_personalization.py",
        "tests/test_level7_season_formation.py",
        "tests/test_stewardship_daily_gap9.py",
    ],
    "Level 8: Bounded Autonomous Operator": [
        "tests/test_phase_k_foundry_lifecycle.py",
        "tests/test_level8_zone_consent_promote.py",
        "tests/test_phase_e_formation_autonomy.py",
    ],
    "Level 9: Family Civilization Layer": [
        "tests/test_phase_l_civilization.py",
        "tests/test_phase_f_level9.py",
        "docs/JARVIS-LEVEL9-COMPREHENSIVE-CHECKLIST.md",
    ],
}

SEED_SCAN_DIRS = [
    "data",
    "artifacts/generated",
]

TEXT_FILE_SUFFIXES = {".json", ".jsonl", ".txt", ".html", ".md"}
MAX_SCAN_FILE_BYTES = 1_000_000
MAX_SCAN_TOTAL_BYTES = 25_000_000


@dataclass
class LevelRow:
    level: str
    percent_text: str
    target_text: str


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _display_path(path: Path, repo_root: Path) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return os.fspath(path)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_session_state(path: Path) -> tuple[list[LevelRow], list[str]]:
    text = _read_text(path)
    lines = text.splitlines()

    levels: list[LevelRow] = []
    blockers: list[str] = []

    in_table = False
    in_blockers = False
    for line in lines:
        if line.strip().startswith("| Level | Current realistic state | Target for Level 9 program |"):
            in_table = True
            continue
        if in_table:
            if not line.startswith("|"):
                in_table = False
            elif line.startswith("|---"):
                continue
            else:
                cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
                if len(cells) >= 3:
                    levels.append(LevelRow(level=cells[0], percent_text=cells[1], target_text=cells[2]))

        if line.strip() == "## External Blockers":
            in_blockers = True
            continue
        if in_blockers:
            if line.startswith("#") and line.strip() != "## External Blockers":
                in_blockers = False
                continue
            stripped = line.strip()
            if stripped.startswith("- "):
                blockers.append(stripped[2:].strip())

    return levels, blockers


def _percent_number(text: str) -> float | None:
    match = re.search(r"(\d+)(?:\.\d+)?", text)
    if not match:
        return None
    return float(match.group(1))


def _git_capture(repo_root: Path, args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
        )
    except Exception as exc:  # pragma: no cover - defensive
        return f"error: {exc}"
    return (result.stdout or result.stderr or "").strip()


def _git_truth(repo_root: Path) -> dict[str, Any]:
    branch_status = _git_capture(repo_root, ["status", "--short", "--branch"])
    branch_line = branch_status.splitlines()[0] if branch_status else ""
    head = _git_capture(repo_root, ["rev-parse", "HEAD"])
    return {
        "branch_status": branch_line,
        "head": head,
        "dirty": any(line and not line.startswith("##") for line in branch_status.splitlines()),
        "status_excerpt": branch_status.splitlines()[1:21],
    }


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _summarize_qa_report(path: Path, repo_root: Path) -> dict[str, Any]:
    payload = _load_json(path)
    if not payload:
        return {
            "path": _display_path(path, repo_root),
            "status": "missing",
            "summary": {},
            "failures": [],
        }
    return {
        "path": _display_path(path, repo_root),
        "status": "present",
        "summary": dict(payload.get("summary") or {}),
        "failures": list(payload.get("failures") or []),
        "warnings": list(payload.get("warnings") or []),
        "started_at": payload.get("started_at"),
        "finished_at": payload.get("finished_at"),
    }


def _seed_findings_for_payload(payload: Any, rel_path: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if isinstance(payload, dict):
        items = [payload]
    elif isinstance(payload, list):
        items = list(payload)
    else:
        items = [payload]

    for index, item in enumerate(items):
        if record_looks_like_test_data(item):
            findings.append(
                {
                    "path": rel_path,
                    "index": index,
                    "kind": "structured-seed",
                }
            )
    return findings


def _seed_findings_for_text(text: str, rel_path: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if string_looks_like_test_data(line):
            findings.append(
                {
                    "path": rel_path,
                    "line": line_number,
                    "kind": "text-seed",
                    "excerpt": line.strip()[:160],
                }
            )
    return findings


def _scan_file_for_seed_data(path: Path, repo_root: Path) -> list[dict[str, Any]]:
    rel_path = _display_path(path, repo_root)
    suffix = path.suffix.lower()
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    findings: list[dict[str, Any]] = []
    if suffix == ".json":
        try:
            findings.extend(_seed_findings_for_payload(json.loads(text), rel_path))
        except json.JSONDecodeError:
            findings.extend(_seed_findings_for_text(text, rel_path))
    elif suffix == ".jsonl":
        for line_number, raw in enumerate(text.splitlines(), start=1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                item = json.loads(raw)
            except json.JSONDecodeError:
                if string_looks_like_test_data(raw):
                    findings.append({"path": rel_path, "line": line_number, "kind": "jsonl-text-seed", "excerpt": raw[:160]})
                continue
            if record_looks_like_test_data(item):
                findings.append({"path": rel_path, "line": line_number, "kind": "jsonl-structured-seed"})
    else:
        findings.extend(_seed_findings_for_text(text, rel_path))
    return findings


def _scan_seed_directories(repo_root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    scanned_files = 0
    skipped_files = 0
    scanned_bytes = 0
    for rel_dir in SEED_SCAN_DIRS:
        directory = repo_root / rel_dir
        if not directory.exists():
            continue
        for path in sorted(directory.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in TEXT_FILE_SUFFIXES:
                continue
            try:
                size = path.stat().st_size
            except OSError:
                skipped_files += 1
                continue
            if size > MAX_SCAN_FILE_BYTES or scanned_bytes + size > MAX_SCAN_TOTAL_BYTES:
                skipped_files += 1
                continue
            scanned_files += 1
            scanned_bytes += size
            findings.extend(_scan_file_for_seed_data(path, repo_root))
    return findings, {
        "scanned_files": scanned_files,
        "skipped_files": skipped_files,
        "scanned_bytes": scanned_bytes,
        "max_file_bytes": MAX_SCAN_FILE_BYTES,
        "max_total_bytes": MAX_SCAN_TOTAL_BYTES,
    }


def _scan_mock_source_markers(repo_root: Path) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for path in sorted((repo_root / "jarvis").rglob("*.py")):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            if "_mock_" in line or '"mock"' in line or "'mock'" in line:
                findings.append(
                    {
                        "path": _display_path(path, repo_root),
                        "line": line_number,
                        "excerpt": line.strip()[:160],
                    }
                )
    return findings


def build_truth_report(repo_root: Path, session_state_path: Path) -> dict[str, Any]:
    levels, blockers = parse_session_state(session_state_path)
    git = _git_truth(repo_root)
    deployment = _build_deployment_context(repo_root)
    platform_report = _summarize_qa_report(repo_root / "artifacts" / "qa" / "jarvis-platform-report.json", repo_root)
    provider_report = _summarize_qa_report(repo_root / "artifacts" / "qa" / "jarvis-provider-layer-report.json", repo_root)
    fake_data_findings, scan_stats = _scan_seed_directories(repo_root)
    source_markers = _scan_mock_source_markers(repo_root)

    unresolved_failures: list[str] = []
    unresolved_failures.extend(str(item) for item in platform_report.get("failures") or [])
    unresolved_failures.extend(str(item) for item in provider_report.get("failures") or [])
    unresolved_failures.extend(
        f"fake-data:{item.get('path')}:{item.get('line', item.get('index', '?'))}"
        for item in fake_data_findings
    )

    level_rows: list[dict[str, Any]] = []
    for row in levels:
        level_rows.append(
            {
                "level": row.level,
                "percent": _percent_number(row.percent_text),
                "percent_text": row.percent_text,
                "target_text": row.target_text,
                "evidence_links": LEVEL_EVIDENCE_MAP.get(row.level, []),
                "open_blockers": blockers,
                "last_verification_date": _now_iso(),
                "owner": "Codex autonomous run",
            }
        )

    provider_truth = {
        "platform_report": platform_report,
        "provider_report": provider_report,
        "status": "warning" if provider_report.get("status") == "present" else "unverified",
    }

    channel_truth = {
        "local": {
            "status": "ready",
            "detail": deployment.get("label"),
            "data_path": deployment.get("data_path"),
        },
        "github": {
            "status": "observed",
            "detail": git.get("branch_status", ""),
        },
        "deployed": {
            "status": "unverified",
            "detail": "No live network verification was performed in this run.",
        },
        "cloudflare": {
            "status": "unverified",
            "detail": "Cloudflare edge not probed from this sandboxed run.",
        },
        "docker": {
            "status": "ready" if deployment.get("in_docker") else "local-only",
            "detail": deployment.get("note"),
        },
        "data_volume": {
            "status": "ready" if "data_path" in deployment else "unknown",
            "detail": str(deployment.get("data_path", "")),
        },
        "providers": provider_truth,
    }

    return {
        "generated_at": _now_iso(),
        "source_of_truth": _display_path(session_state_path, repo_root),
        "git": git,
        "deployment": deployment,
        "channel_truth": channel_truth,
        "scorecard": level_rows,
        "proof_ledger": {
            "platform_e2e": platform_report,
            "provider_battery": provider_report,
            "production_revision": {
                "git_head": git.get("head"),
                "deployed_revision": "unverified in this run",
            },
            "unresolved_failures": unresolved_failures,
        },
        "no_fake_data_audit": {
            "status": "fail" if fake_data_findings else "pass",
            "seed_findings": fake_data_findings,
            "source_markers": source_markers,
            "scanned_directories": SEED_SCAN_DIRS,
            "scan_stats": scan_stats,
        },
        "external_blockers": blockers,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a machine-readable Level 9 truth report.")
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--session-state", default=str(SESSION_STATE_PATH))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    session_state_path = Path(args.session_state).resolve()
    output_path = Path(args.output).resolve()

    report = build_truth_report(repo_root, session_state_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

    summary = {
        "output": str(output_path),
        "levels": len(report.get("scorecard") or []),
        "fake_data_findings": len((report.get("no_fake_data_audit") or {}).get("seed_findings") or []),
        "platform_failures": len((report.get("proof_ledger") or {}).get("platform_e2e", {}).get("failures") or []),
        "provider_failures": len((report.get("proof_ledger") or {}).get("provider_battery", {}).get("failures") or []),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
