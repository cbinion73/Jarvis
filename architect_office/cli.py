from __future__ import annotations

import argparse
from pathlib import Path

from .git_inspector import inspect_git_state
from .phase_rules import evaluate_phase_scope
from .report_checker import check_report
from .review_writer import build_review


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Architect Office procedural governance checks.")
    subparsers = parser.add_subparsers(dest="command")

    review_parser = subparsers.add_parser("review", help="Review a Build Office report against a phase gate.")
    review_parser.add_argument("--phase", required=True, help="Phase identifier to validate against.")
    review_parser.add_argument("--report", required=True, help="Path to the Build Office report markdown.")
    review_parser.add_argument("--output", help="Optional path for writing the Architecture Office review markdown.")
    review_parser.add_argument(
        "--repo-root",
        default=Path(__file__).resolve().parents[1],
        type=Path,
        help="Repository root to inspect. Defaults to the current JARVIS checkout.",
    )
    review_parser.set_defaults(func=command_review)
    return parser


def command_review(args: argparse.Namespace) -> int:
    git = inspect_git_state(args.repo_root, expected_branch=args.phase)
    report = check_report(args.report)
    scope = evaluate_phase_scope(args.phase, [report.text, "\n".join(git.status_lines)])
    review = build_review(phase=args.phase, git=git, report=report, scope=scope)
    print(review.markdown)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(review.markdown + "\n", encoding="utf-8")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 0
    return args.func(args)
