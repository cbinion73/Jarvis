#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

SESSION_STATE_PATH = REPO_ROOT / "docs" / "JARVIS-SESSION-STATE.md"
MATURITY_MODEL_PATH = REPO_ROOT / "docs" / "JARVIS-MATURITY-MODEL.md"
ROADMAP_PATH = REPO_ROOT / "docs" / "JARVIS-CIVILIZATION-SCALE-MASTER-ROADMAP.md"
CHECKLIST_PATH = REPO_ROOT / "docs" / "JARVIS-LEVEL9-COMPREHENSIVE-CHECKLIST.md"
LEVEL3_EXIT_REPORT_PATH = REPO_ROOT / "docs" / "JARVIS-LEVEL3-EXIT-REPORT.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def verify_docs_truth(repo_root: Path) -> list[str]:
    docs = {
        "session_state": repo_root / "docs" / "JARVIS-SESSION-STATE.md",
        "maturity_model": repo_root / "docs" / "JARVIS-MATURITY-MODEL.md",
        "roadmap": repo_root / "docs" / "JARVIS-CIVILIZATION-SCALE-MASTER-ROADMAP.md",
        "checklist": repo_root / "docs" / "JARVIS-LEVEL9-COMPREHENSIVE-CHECKLIST.md",
        "level3_exit_report": repo_root / "docs" / "JARVIS-LEVEL3-EXIT-REPORT.md",
    }

    failures: list[str] = []
    missing = [name for name, path in docs.items() if not path.exists()]
    if missing:
        return [f"missing required docs: {', '.join(missing)}"]

    session_state = _read(docs["session_state"])
    maturity_model = _read(docs["maturity_model"])
    roadmap = _read(docs["roadmap"])
    checklist = _read(docs["checklist"])
    level3_exit_report = _read(docs["level3_exit_report"])

    canonical_placement = "Overall placement: solid Level 4, partial Level 5."
    if canonical_placement not in session_state:
        failures.append("session state missing canonical overall placement")

    if "JARVIS-SESSION-STATE.md` is the authoritative execution document." not in session_state:
        failures.append("session state missing authoritative execution document rule")

    if "Honest overall placement: solid Level 4, partial Level 5." not in maturity_model:
        failures.append("maturity model missing canonical overall placement")

    if "`docs/JARVIS-SESSION-STATE.md`\nis the authoritative source" not in maturity_model and "`docs/JARVIS-SESSION-STATE.md` is the authoritative source" not in maturity_model:
        failures.append("maturity model does not defer current percentages and execution order to session state")

    for stale_phrase in (
        "- current primary level",
        "- entering this level",
        "Level 3 is COMPLETE.",
    ):
        if stale_phrase in maturity_model:
            failures.append(f"maturity model still contains stale phrase: {stale_phrase}")

    if "If planning documents disagree about current execution status, maturity\nplacement, or what should be worked next, `docs/JARVIS-SESSION-STATE.md` wins." not in roadmap:
        failures.append("roadmap does not defer current execution status to session state")

    if "Docs conflict on whether Level 3 is complete." not in checklist:
        failures.append("Level 9 checklist missing docs-truth Level 3 conflict row")
    if "Documentation truth" not in checklist:
        failures.append("Level 9 checklist missing documentation truth row")

    if "not the current source of truth for JARVIS maturity placement" not in level3_exit_report:
        failures.append("Level 3 exit report does not mark itself as non-authoritative for current placement")
    if "historical evidence" not in level3_exit_report:
        failures.append("Level 3 exit report missing historical evidence framing")
    if "**Level 3 is COMPLETE.**" in level3_exit_report:
        failures.append("Level 3 exit report still makes an unconditional current completion claim")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Fail when JARVIS maturity docs drift out of truth alignment.")
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    args = parser.parse_args()

    failures = verify_docs_truth(Path(args.repo_root).resolve())
    if failures:
        print("docs truth verification failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    print("docs truth verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
