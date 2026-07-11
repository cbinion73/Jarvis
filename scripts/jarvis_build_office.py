#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from jarvis.build_office import BuildOffice
from jarvis.office_charters import all_office_briefs, office_charter, onboarding_brief


def _print(payload: Any) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Collision-safe Claude/Codex Build Office control plane")
    parser.add_argument("--repo", default=".", help="JARVIS repository root")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("doctor")

    brief = sub.add_parser("office-brief")
    brief.add_argument("office", choices=["orchestration", "architect", "build", "qa", "all"])

    init = sub.add_parser("init")
    init.add_argument("request")
    init.add_argument("--risk", choices=["low", "medium", "high", "critical"], default="medium")
    init.add_argument("--budget-usd", type=float, default=10.0)
    init.add_argument("--timeout", type=int, default=1800)
    init.add_argument("--mission-id", default="")
    init.add_argument("--implementer", choices=["claude", "codex"], default="codex")
    init.add_argument("--route-mode", choices=["default", "no-claude"], default="default")
    init.add_argument("--contract-ref", default="")
    init.add_argument("--scope", action="append", dest="owned_paths")
    init.add_argument("--dry-run", action="store_true")

    status = sub.add_parser("status")
    status.add_argument("mission_id")

    heartbeat = sub.add_parser("heartbeat")
    heartbeat.add_argument("mission_id", nargs="?")
    heartbeat.add_argument("--by", default="Architect heartbeat", dest="actor")
    heartbeat.add_argument("--interval-seconds", "--cadence-seconds", type=int, default=300)
    heartbeat.add_argument("--dispatch-ready", action="store_true")
    heartbeat.add_argument("--execute", action="store_true")
    heartbeat.add_argument("--watch", action="store_true")
    heartbeat.add_argument("--max-iterations", type=int, default=0)

    inbox = sub.add_parser("inbox")
    inbox.add_argument("provider", choices=["claude", "codex"])

    claim = sub.add_parser("claim")
    claim.add_argument("mission_id")
    claim.add_argument("assignment_id")
    claim.add_argument("--by", required=True, dest="claimed_by")

    dispatch = sub.add_parser("dispatch")
    dispatch.add_argument("mission_id")
    dispatch.add_argument("assignment_id")
    dispatch.add_argument("--dry-run", action="store_true")

    approve = sub.add_parser("approve-dispatch")
    approve.add_argument("mission_id")
    approve.add_argument("--by", required=True, dest="approved_by")

    reclaim = sub.add_parser("reclaim-lease")
    reclaim.add_argument("mission_id")
    reclaim.add_argument("assignment_id")
    reclaim.add_argument("--by", required=True, dest="approved_by")

    recover = sub.add_parser("recover-review")
    recover.add_argument("mission_id")
    recover.add_argument("assignment_id")
    recover.add_argument("--by", required=True, dest="approved_by")
    recover.add_argument("--reason", required=True)

    retry = sub.add_parser("retry")
    retry.add_argument("mission_id")
    retry.add_argument("assignment_id")
    retry.add_argument("--by", required=True, dest="approved_by")

    amend = sub.add_parser("amend-terminal-evidence")
    amend.add_argument("mission_id")
    amend.add_argument("assignment_id")
    amend.add_argument("--by", required=True, dest="actor")
    amend.add_argument("--reason", required=True)

    supersede = sub.add_parser("supersede-assignment")
    supersede.add_argument("mission_id")
    supersede.add_argument("assignment_id")
    supersede.add_argument("--by", required=True, dest="actor")
    supersede.add_argument("--reason", required=True)
    supersede.add_argument("--artifact", action="append", dest="artifacts")

    release = sub.add_parser("release-plan")
    release.add_argument("mission_id")

    cleanup = sub.add_parser("cleanup-plan")
    cleanup.add_argument("mission_id")

    submit = sub.add_parser("submit-result")
    submit.add_argument("mission_id")
    submit.add_argument("assignment_id")
    submit.add_argument("--by", required=True, dest="completed_by")
    submit.add_argument("--status", choices=["completed", "failed", "blocked"], required=True)
    submit.add_argument("--summary", required=True)
    submit.add_argument("--finding", action="append", dest="findings")
    submit.add_argument("--test", action="append", dest="tests")

    demo = sub.add_parser("demo")
    demo.add_argument("--dry-run", action="store_true", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    office = BuildOffice(Path(args.repo))
    try:
        if args.command == "doctor":
            payload = office.doctor()
        elif args.command == "office-brief":
            if args.office == "all":
                payload = all_office_briefs()
            else:
                payload = {
                    "charter": office_charter(args.office),
                    "onboarding_brief": onboarding_brief(args.office),
                }
        elif args.command == "init":
            payload = office.init_mission(
                request=args.request,
                risk=args.risk,
                budget_usd=args.budget_usd,
                timeout_seconds=args.timeout,
                mission_id=args.mission_id,
                implementer=args.implementer,
                route_mode=args.route_mode,
                contract_ref=args.contract_ref,
                owned_paths=args.owned_paths,
                dry_run=args.dry_run,
            )
        elif args.command == "status":
            payload = office.load_mission(args.mission_id)
        elif args.command == "heartbeat":
            target = str(args.mission_id or "").strip().lower()
            if target == "architect":
                if args.watch:
                    for item in office.watch_office_heartbeat(
                        "architect",
                        cadence_seconds=args.interval_seconds,
                        max_iterations=args.max_iterations,
                    ):
                        _print(item)
                        sys.stdout.flush()
                    return 0
                payload = office.office_heartbeat("architect", cadence_seconds=args.interval_seconds)
            else:
                payload = office.heartbeat(
                    args.mission_id,
                    actor=args.actor,
                    interval_seconds=args.interval_seconds,
                    dispatch_ready=args.dispatch_ready,
                    dry_run=not args.execute,
                )
        elif args.command == "inbox":
            payload = office.office_inbox(args.provider)
        elif args.command == "claim":
            payload = office.claim_assignment(
                args.mission_id, args.assignment_id, claimed_by=args.claimed_by
            )
        elif args.command == "dispatch":
            payload = office.dispatch(args.mission_id, args.assignment_id, dry_run=args.dry_run)
        elif args.command == "approve-dispatch":
            payload = office.approve_dispatch(args.mission_id, approved_by=args.approved_by)
        elif args.command == "reclaim-lease":
            payload = office.reclaim_expired_lease(
                args.mission_id, args.assignment_id, approved_by=args.approved_by
            )
        elif args.command == "recover-review":
            payload = office.recover_review_assignment(
                args.mission_id,
                args.assignment_id,
                approved_by=args.approved_by,
                reason=args.reason,
            )
        elif args.command == "retry":
            payload = office.retry_assignment(
                args.mission_id, args.assignment_id, approved_by=args.approved_by
            )
        elif args.command == "amend-terminal-evidence":
            payload = office.amend_terminal_assignment_evidence(
                args.mission_id,
                args.assignment_id,
                actor=args.actor,
                reason=args.reason,
            )
        elif args.command == "supersede-assignment":
            payload = office.supersede_assignment(
                args.mission_id,
                args.assignment_id,
                actor=args.actor,
                reason=args.reason,
                artifacts=args.artifacts,
            )
        elif args.command == "release-plan":
            payload = office.release_plan(args.mission_id)
        elif args.command == "cleanup-plan":
            payload = office.cleanup_plan(args.mission_id)
        elif args.command == "submit-result":
            payload = office.submit_result(
                args.mission_id,
                args.assignment_id,
                completed_by=args.completed_by,
                status=args.status,
                summary=args.summary,
                findings=args.findings,
                tests=args.tests,
            )
        elif args.command == "demo":
            mission = office.init_mission(
                request="Demonstrate collision-safe JARVIS build-office routing",
                risk="medium",
                budget_usd=2.0,
                timeout_seconds=300,
                contract_ref="docs/BUILD-OFFICE-AUTOMATION.md",
                mission_id=f"bo-demo-{__import__('uuid').uuid4().hex[:8]}",
                dry_run=True,
            )
            dispatches = {
                assignment["assignment_id"]: {
                    "dry_run": True,
                    "command": office.adapter_command(mission, assignment),
                }
                for assignment in mission["assignments"]
            }
            payload = {
                "mission": office.load_mission(mission["mission_id"]),
                "dispatches": dispatches,
                "release": office.release_plan(mission["mission_id"]),
                "cleanup": office.cleanup_plan(mission["mission_id"]),
            }
        else:
            raise AssertionError(args.command)
    except (ValueError, KeyError, RuntimeError, FileExistsError) as exc:
        _print({"ok": False, "error": str(exc)})
        return 2
    _print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
