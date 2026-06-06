#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from jarvis.approvals import ApprovalQueue, ApprovalRequest
from jarvis.approval_queue_surface import (
    build_approval_queue_snapshot,
    write_approval_queue_snapshot,
)


def _queue_with_root(root: Path | None) -> ApprovalQueue:
    if root is not None:
        ApprovalQueue.ROOT = root
    return ApprovalQueue()


def _print_json(payload: object) -> int:
    print(json.dumps(payload, indent=2))
    return 0


def _serialize_request(item: ApprovalRequest | None) -> dict | None:
    if item is None:
        return None
    return {
        "request_id": item.request_id,
        "title": item.title,
        "description": item.description,
        "status": item.status,
        "risk_tier": item.risk_tier,
        "agent_label": item.agent_label,
        "actor_id": item.actor_id,
        "action_type": item.action_type,
        "requested_at": item.requested_at,
        "expires_at": item.expires_at,
        "approved_by": item.approved_by,
        "approved_at": item.approved_at,
        "executed_at": item.executed_at,
        "rejection_reason": item.rejection_reason,
        "requires_confirmation": item.requires_confirmation,
        "confirmation_phrase": item.confirmation_phrase,
        "supervision_decision": dict(item.supervision_decision or {}),
    }


def _cmd_list(args: argparse.Namespace) -> int:
    queue = _queue_with_root(args.root)
    pending = [_serialize_request(item) for item in queue.get_pending()]
    return _print_json({"pending": pending})


def _cmd_show(args: argparse.Namespace) -> int:
    queue = _queue_with_root(args.root)
    item = queue.get_by_id(args.request_id)
    if item is None:
        print(f"missing approval request: {args.request_id}", file=sys.stderr)
        return 1
    return _print_json({"request": _serialize_request(item)})


def _cmd_approve(args: argparse.Namespace) -> int:
    queue = _queue_with_root(args.root)
    item = queue.approve(args.request_id, approved_by=args.approved_by)
    if item is None:
        print(f"unable to approve request: {args.request_id}", file=sys.stderr)
        return 1
    return _print_json({"approved": _serialize_request(item)})


def _cmd_reject(args: argparse.Namespace) -> int:
    queue = _queue_with_root(args.root)
    ok = queue.reject(args.request_id, reason=args.reason, rejected_by=args.rejected_by)
    if not ok:
        print(f"unable to reject request: {args.request_id}", file=sys.stderr)
        return 1
    return _print_json({"rejected": args.request_id, "reason": args.reason})


def _cmd_cancel(args: argparse.Namespace) -> int:
    queue = _queue_with_root(args.root)
    ok = queue.cancel(args.request_id)
    if not ok:
        print(f"unable to cancel request: {args.request_id}", file=sys.stderr)
        return 1
    return _print_json({"cancelled": args.request_id})


def _cmd_execute(args: argparse.Namespace) -> int:
    queue = _queue_with_root(args.root)
    ok = queue.mark_executed(args.request_id)
    if not ok:
        print(f"unable to mark request executed: {args.request_id}", file=sys.stderr)
        return 1
    return _print_json({"executed": args.request_id})


def _cmd_render(args: argparse.Namespace) -> int:
    snapshot = build_approval_queue_snapshot(approvals_root=args.root)
    outputs = write_approval_queue_snapshot(snapshot)
    return _print_json(outputs)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect and operate the local JARVIS approval queue.")
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Override the approval queue root for local testing or seeded demos.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List pending approval requests as JSON.")
    list_parser.set_defaults(func=_cmd_list)

    show_parser = subparsers.add_parser("show", help="Show a single approval request.")
    show_parser.add_argument("request_id")
    show_parser.set_defaults(func=_cmd_show)

    approve_parser = subparsers.add_parser("approve", help="Approve a pending request.")
    approve_parser.add_argument("request_id")
    approve_parser.add_argument("--approved-by", default="chris")
    approve_parser.set_defaults(func=_cmd_approve)

    reject_parser = subparsers.add_parser("reject", help="Reject a pending request.")
    reject_parser.add_argument("request_id")
    reject_parser.add_argument("--reason", default="")
    reject_parser.add_argument("--rejected-by", default="chris")
    reject_parser.set_defaults(func=_cmd_reject)

    cancel_parser = subparsers.add_parser("cancel", help="Cancel a pending request.")
    cancel_parser.add_argument("request_id")
    cancel_parser.set_defaults(func=_cmd_cancel)

    execute_parser = subparsers.add_parser("execute", help="Mark an approved request as executed.")
    execute_parser.add_argument("request_id")
    execute_parser.set_defaults(func=_cmd_execute)

    render_parser = subparsers.add_parser("render", help="Render the local approval queue HTML and JSON surfaces.")
    render_parser.set_defaults(func=_cmd_render)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
