from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .audit import AuditLog, ProgressSnapshotStore, SeamTrackerStore
from .agent_registry_contract import load_contract_bundle
from .approval_queue_surface import build_approval_queue_snapshot
from .recovery_cases import RecoveryCaseStore
from .supervision_snapshot import build_supervision_snapshot


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUDIT_ROOT = REPO_ROOT / "data" / "logs"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _activity_items(limit: int = 8) -> list[dict[str, Any]]:
    audit = AuditLog(DEFAULT_AUDIT_ROOT)
    rows = []
    for item in audit.list_recent(limit=limit):
        entry_type = str(item.get("entry_type", ""))
        title = ""
        if entry_type in {"home-action", "operator-action"}:
            title = str(item.get("action", "") or item.get("title", "")).strip()
        if not title:
            title = str(
                item.get("detail")
                or item.get("action")
                or item.get("output_preview")
                or item.get("title")
                or item.get("entry_type")
                or "activity"
            )
        rows.append(
            {
                "entry_type": entry_type,
                "timestamp": str(item.get("timestamp", "")),
                "title": title,
                "subtitle": str(
                    item.get("why_now")
                    or item.get("domain")
                    or item.get("actor")
                    or item.get("provider")
                    or ""
                ),
                "actor": str(item.get("actor", "")),
                "result": str(item.get("result_summary", "")),
                "detail": str(item.get("detail", "")),
                "related_route": str(item.get("related_route", "")),
                "route_label": str(item.get("route_label", "")),
                "related_kind": str(item.get("related_kind", "")),
                "related_label": str(item.get("related_label", "")),
            }
        )
    progress_store = ProgressSnapshotStore(DEFAULT_AUDIT_ROOT)
    for snapshot in list(progress_store.summary(limit=max(1, limit // 2)).get("recent") or []):
        if not isinstance(snapshot, dict):
            continue
        progress_counts = dict(snapshot.get("progress_counts") or {})
        seam_counts = dict(snapshot.get("seam_counts") or {})
        rows.append(
            {
                "entry_type": "progress-snapshot",
                "timestamp": str(snapshot.get("saved_at", "")),
                "title": "Progress Snapshot Persisted",
                "subtitle": str(snapshot.get("next_focus", "")).strip() or "No next focus recorded yet.",
                "actor": "JARVIS",
                "result": "Durable progress history updated.",
                "detail": (
                    f"Useful={int(progress_counts.get('useful', 0) or 0)} · "
                    f"Wired={int(progress_counts.get('wired', 0) or 0)} · "
                    f"Seams={int(seam_counts.get('Useful', 0) or 0)} useful / {int(seam_counts.get('Wired', 0) or 0)} wired."
                ),
                "related_route": "/progress-center",
                "route_label": "Open Progress Center",
                "related_kind": "progress",
                "related_label": str(snapshot.get("next_focus", "")).strip() or "Progress",
            }
        )
    rows.sort(key=lambda item: str(item.get("timestamp", "")), reverse=True)
    return rows[:limit]


def _read_json_list(path: Path) -> list[dict[str, Any]]:
    try:
        payload = json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return []
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return []


def _hosted_deployment() -> dict[str, Any]:
    deploy_script_path = REPO_ROOT / "deploy" / "deploy.sh"
    workflow_path = REPO_ROOT / ".github" / "workflows" / "deploy.yml"
    nginx_path = REPO_ROOT / "deploy" / "nginx.conf"
    compose_path = REPO_ROOT / "deploy" / "docker-compose.yml"

    def read_text(path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            return ""

    deploy_script = read_text(deploy_script_path)
    workflow = read_text(workflow_path)
    nginx_conf = read_text(nginx_path)
    compose = read_text(compose_path)

    public_routes: list[str] = []
    for line in nginx_conf.splitlines():
        line = line.strip()
        if not line.startswith("server_name "):
            continue
        server_name = line.removeprefix("server_name ").rstrip(";").strip()
        if server_name:
            public_routes.append(f"https://{server_name}")

    hosted_url = next((route for route in public_routes if "jarvis.teambinion.org" in route), "https://jarvis.teambinion.org")
    deploy_mode = "GitHub Actions main deploy" if "branches: [main]" in workflow else "manual deploy script"
    edge_provider = "Cloudflare Tunnel" if "cloudflared:" in compose else "direct nginx edge"
    remote_detail = "Workflow deploys from GitHub Actions to root over SSH." if "username: root" in workflow else "Manual deploy script expects a jarvis SSH target."
    summary = f"Hosted edge is defined for {hosted_url} through nginx plus {edge_provider}, with {deploy_mode.lower()} artifacts present in this checkout."
    next_action = (
        "Push through the real deploy path, or merge to main so the GitHub Actions deploy job can rebuild jarvis."
        if "branches: [main]" in workflow
        else "Run the deploy script against the hosted server after the branch is ready to publish."
    )
    return {
        "status": "Wired",
        "status_label": "wired",
        "status_class": "artifact",
        "summary": summary,
        "hosted_url": hosted_url,
        "edge_provider": edge_provider,
        "deploy_mode": deploy_mode,
        "remote_detail": remote_detail,
        "public_routes": public_routes,
        "proof_files": [
            "deploy/deploy.sh",
            ".github/workflows/deploy.yml",
            "deploy/nginx.conf",
            "deploy/docker-compose.yml",
        ],
        "next_action": next_action,
        "deploy_script_present": bool(deploy_script.strip()),
        "workflow_present": bool(workflow.strip()),
        "nginx_present": bool(nginx_conf.strip()),
        "compose_present": bool(compose.strip()),
    }


def _failure_recovery(
    *,
    supervision_snapshot: dict[str, Any],
    approval_snapshot: dict[str, Any],
    activity_feed: list[dict[str, Any]],
) -> dict[str, Any]:
    recovery_case_store = RecoveryCaseStore()
    integrations = list(supervision_snapshot.get("integrations") or [])
    failing_integrations = []
    for item in integrations:
        if bool(item.get("ok", False)):
            continue
        failing_integrations.append(
            {
                "name": str(item.get("name", "")).strip() or "integration",
                "detail": str(item.get("detail", "")).strip() or "Integration needs review.",
            }
        )

    recent_failures = []
    for item in activity_feed:
        haystack = " ".join(
            [
                str(item.get("title", "")),
                str(item.get("subtitle", "")),
                str(item.get("result", "")),
                str(item.get("entry_type", "")),
            ]
        ).lower()
        if not any(token in haystack for token in ("fail", "error", "recover", "rollback", "blocked")):
            continue
        recent_failures.append(
            {
                "title": str(item.get("title", "")).strip() or "Runtime failure surfaced",
                "detail": str(item.get("result", "")).strip()
                or str(item.get("subtitle", "")).strip()
                or "Recent runtime activity needs recovery attention.",
                "timestamp": str(item.get("timestamp", "")).strip(),
            }
        )
        if len(recent_failures) >= 5:
            break

    pending_count = int(approval_snapshot.get("pending_count", 0) or 0)
    lane = dict(supervision_snapshot.get("lane") or {})
    dirty_count = int(lane.get("dirty_count", 0) or 0)
    action_items = []
    if pending_count:
        action_items.append(
            {
                "title": "Approval queue needs review",
                "detail": f"{pending_count} pending approval item(s) are waiting in /approval-queue.",
            }
        )
    for item in failing_integrations[:3]:
        action_items.append(
            {
                "title": f"Repair {item['name']}",
                "detail": item["detail"],
            }
        )
    if dirty_count:
        action_items.append(
            {
                "title": "Lane has unreconciled local residue",
                "detail": f"{dirty_count} working-tree change(s) are still present in the current lane.",
            }
        )
    if not action_items:
        action_items.append(
            {
                "title": "Recovery posture is stable",
                "detail": "No active integration failures or approval bottlenecks are currently surfaced.",
            }
        )

    recovery_cases = []
    try:
        recovery_cases = recovery_case_store.list_cases()
    except Exception:
        recovery_cases = []
    unresolved_cases = [
        item for item in recovery_cases
        if str(item.get("status", "")).strip().lower() in {"open", "investigating", "watch"}
    ]
    if unresolved_cases:
        investigating_count = sum(
            1 for item in unresolved_cases
            if str(item.get("status", "")).strip().lower() == "investigating"
        )
        watch_count = sum(
            1 for item in unresolved_cases
            if str(item.get("status", "")).strip().lower() == "watch"
        )
        action_items.insert(
            0,
            {
                "title": "Durable recovery cases need review",
                "detail": f"{len(unresolved_cases)} case(s) are open, including {investigating_count} investigating and {watch_count} watch item(s).",
            },
        )

    return {
        "integration_issue_count": len(failing_integrations),
        "recent_failure_count": len(recent_failures),
        "pending_approval_count": pending_count,
        "dirty_count": dirty_count,
        "recovery_case_count": len(recovery_cases),
        "unresolved_recovery_case_count": len(unresolved_cases),
        "failing_integrations": failing_integrations,
        "recent_failures": recent_failures,
        "action_items": action_items[:5],
    }


def _brief_preview(
    *,
    supervision_snapshot: dict[str, Any],
    activity_feed: list[dict[str, Any]],
) -> dict[str, Any]:
    return_brief = dict(supervision_snapshot.get("return_brief") or {})
    what_needs_me = list(supervision_snapshot.get("what_needs_me") or [])
    memory = dict(supervision_snapshot.get("memory") or {})
    top_need = dict(what_needs_me[0]) if what_needs_me else {}
    activity_titles = [
        str(item.get("title", "")).strip()
        for item in activity_feed[:3]
        if str(item.get("title", "")).strip()
    ]
    lines = []
    summary = str(return_brief.get("summary", "")).strip()
    if summary:
        lines.append(summary)
    if top_need:
        lines.append(
            f"Top need: {str(top_need.get('title', '')).strip()} - {str(top_need.get('detail', '')).strip()}".strip(" -")
        )
    if activity_titles:
        lines.append(f"Recent motion: {'; '.join(activity_titles)}")
    if not lines:
        lines.append("JARVIS has not assembled a daily brief preview yet.")
    return {
        "actor": "Chris",
        "headline": str(lines[0]),
        "supporting_lines": lines[1:4],
        "memory_entry_count": int(memory.get("entry_count", 0) or 0),
        "live_news": False,
        "rss_articles": 0,
        "rss_sources": [],
        "briefing_text": "\n\n".join(lines),
    }


def _timeline_preview(
    *,
    approval_snapshot: dict[str, Any],
    supervision_snapshot: dict[str, Any],
    activity_feed: list[dict[str, Any]],
) -> dict[str, Any]:
    what_needs_me = list(supervision_snapshot.get("what_needs_me") or [])
    pending = list(approval_snapshot.get("pending") or [])
    items: list[dict[str, Any]] = []
    for item in pending[:2]:
        items.append(
            {
                "item_id": str(item.get("request_id", "")).strip(),
                "title": str(item.get("title", "")).strip() or "Approval queue item",
                "domain": "approvals",
                "status": str(item.get("risk_tier", "")).strip() or "pending",
                "lane": str(item.get("agent_label", "")).strip() or "approval-queue",
                "summary": str(item.get("description", "")).strip() or "Approval needs operator review.",
                "available_actions": [
                    {"id": "approve", "label": "Approve"},
                    {"id": "reject", "label": "Reject"},
                    {"id": "defer-4h", "label": "Later Today"},
                ],
            }
        )
    for item in what_needs_me[:2]:
        items.append(
            {
                "item_id": "",
                "title": str(item.get("title", "")).strip() or "Needs attention",
                "domain": str(item.get("kind", "")).strip() or "operations",
                "status": "needs-me",
                "lane": "command-center",
                "summary": str(item.get("detail", "")).strip() or "JARVIS surfaced this for review.",
                "available_actions": [],
            }
        )
    recent_motion = [
        str(item.get("title", "")).strip()
        for item in activity_feed[:3]
        if str(item.get("title", "")).strip()
    ]
    return {
        "summary": {
            "waiting_on_you": len(pending),
            "needs_revisit": len(what_needs_me),
            "recent_motion_count": len(recent_motion),
        },
        "items": items[:4],
        "recent_motion": recent_motion,
    }


def _open_loop_inspector(
    *,
    approval_snapshot: dict[str, Any],
    supervision_snapshot: dict[str, Any],
    activity_feed: list[dict[str, Any]],
) -> dict[str, Any]:
    pending = list(approval_snapshot.get("pending") or [])
    what_needs_me = list(supervision_snapshot.get("what_needs_me") or [])
    recent_motion = [
        str(item.get("title", "")).strip()
        for item in activity_feed[:3]
        if str(item.get("title", "")).strip()
    ]
    items: list[dict[str, Any]] = []
    for item in pending[:3]:
        title = str(item.get("title", "")).strip() or "Approval queue item"
        summary = str(item.get("description", "")).strip() or "Approval needs operator review."
        items.append(
            {
                "item_id": str(item.get("request_id", "")).strip(),
                "title": title,
                "domain": "approvals",
                "status": "pending",
                "owner_agent": str(item.get("agent_label", "")).strip() or "approval-queue",
                "summary": summary,
                "next_action": f"Resolve approval posture for {title.lower()}.".strip(),
                "next_review_at": "Today",
                "auto_execution": {"summary": "Manual approval required before execution."},
                "available_actions": [
                    {"id": "approve", "label": "Approve"},
                    {"id": "reject", "label": "Reject"},
                    {"id": "defer-4h", "label": "Later Today"},
                ],
            }
        )
    proactive_surface = [
        {
            "title": str(item.get("title", "")).strip() or "Open loop",
            "proactive_reason": str(item.get("detail", "")).strip() or "JARVIS surfaced this for operator review.",
        }
        for item in what_needs_me[:3]
    ]
    task_lanes = [
        {
            "owner_agent": str(item.get("owner_agent", "")).strip() or "JARVIS",
            "domain": str(item.get("domain", "")).strip() or "general",
            "lane": str(item.get("summary", "")).strip() or "Open loop queue",
            "approval_threshold": {"summary": str((item.get("auto_execution") or {}).get("summary", "")).strip() or "Review required."},
        }
        for item in items[:4]
    ]
    if not task_lanes and proactive_surface:
        task_lanes.append(
            {
                "owner_agent": "command-center",
                "domain": "operations",
                "lane": "What Needs Me",
                "approval_threshold": {"summary": "Operator review required."},
            }
        )
    return {
        "summary": {
            "total": len(items),
            "waiting_on_you": len(pending),
            "staged": 0,
            "needs_revisit": len(what_needs_me),
            "hidden_deferred": 0,
            "recent_motion_count": len(recent_motion),
        },
        "items": items[:5],
        "proactive_surface": proactive_surface[:4],
        "task_lanes": task_lanes[:4],
        "recent_motion": recent_motion,
    }


def _detail_inspector(
    *,
    approval_snapshot: dict[str, Any],
    open_loop_inspector: dict[str, Any],
    notification_preview: dict[str, Any],
    activity_feed: list[dict[str, Any]],
) -> dict[str, Any]:
    open_loop_items = list(open_loop_inspector.get("items") or [])
    if open_loop_items:
        item = dict(open_loop_items[0])
        title = str(item.get("title", "")).strip() or "Open loop"
        domain = str(item.get("domain", "")).strip() or "general"
        item_id = str(item.get("item_id", "")).strip()
        history_items = list(approval_snapshot.get("history") or [])
        matching_history = [
            decision
            for decision in history_items
            if (item_id and str(decision.get("request_id", "")).strip() == item_id)
            or title.lower() in str(decision.get("title", "")).lower()
        ][:3]
        last_decision = dict(matching_history[0]) if matching_history else {}
        matching_activity = [
            activity
            for activity in activity_feed
            if title.lower() in str(activity.get("title", "")).lower()
            or domain.lower() in str(activity.get("subtitle", "")).lower()
        ][:3]
        return {
            "source_kind": "open-loop",
            "title": title,
            "summary": str(item.get("summary", "")).strip() or "JARVIS surfaced a live open-loop item.",
            "domain": domain,
            "status": str(item.get("status", "")).strip() or "open",
            "owner_agent": str(item.get("owner_agent", "")).strip() or "JARVIS",
            "next_action": str(item.get("next_action", "")).strip() or "No next action captured.",
            "next_review_at": str(item.get("next_review_at", "")).strip() or "not scheduled",
            "autonomy_summary": str((item.get("auto_execution") or {}).get("summary", "")).strip() or "Review required.",
            "available_actions": list(item.get("available_actions") or []),
            "why_now": str(item.get("summary", "")).strip() or "JARVIS surfaced this open loop for review.",
            "evidence_lines": [
                f"Owner agent: {str(item.get('owner_agent', '')).strip() or 'JARVIS'}",
                f"Review schedule: {str(item.get('next_review_at', '')).strip() or 'not scheduled'}",
                f"Autonomy posture: {str((item.get('auto_execution') or {}).get('summary', '')).strip() or 'Review required.'}",
            ],
            "decision_history": [
                {
                    "status": str(decision.get("status", "")).strip() or "unknown",
                    "actor": str(decision.get("approved_by", "")).strip() or str(decision.get("actor_id", "")).strip() or "-",
                    "when": str(decision.get("approved_at", "")).strip()
                    or str(decision.get("executed_at", "")).strip()
                    or str(decision.get("requested_at", "")).strip(),
                    "resolution": str((decision.get("supervision_decision") or {}).get("resolution", "")).strip()
                    or "unclassified",
                }
                for decision in matching_history
            ],
            "last_decision_summary": (
                f"{str(last_decision.get('status', '')).strip() or 'No prior decision'}"
                f" by {str(last_decision.get('approved_by', '')).strip() or str(last_decision.get('actor_id', '')).strip() or '-'}"
            ).strip(),
            "change_summary": "No action diff captured yet.",
            "action_result_summary": "No action result captured yet.",
            "change_evidence_summary": "No post-action evidence captured yet.",
            "field_delta_summary": "No field deltas captured yet.",
            "contract_delta_summary": "No contract deltas captured yet.",
            "derived_delta_summary": "No derived deltas captured yet.",
            "recent_trace": [
                {
                    "title": str(activity.get("title", "")).strip() or "Activity",
                    "detail": str(activity.get("subtitle", "")).strip() or str(activity.get("result", "")).strip() or "Recent activity signal.",
                    "timestamp": str(activity.get("timestamp", "")).strip(),
                }
                for activity in matching_activity
            ],
        }
    notification_items = list(notification_preview.get("items") or [])
    if notification_items:
        item = dict(notification_items[0])
        title = str(item.get("title", "")).strip() or "Notification"
        matching_activity = [
            activity
            for activity in activity_feed
            if title.lower() in str(activity.get("title", "")).lower()
            or str(item.get("why_this_surfaced_now", "")).strip().lower() in str(activity.get("title", "")).lower()
        ][:3]
        return {
            "source_kind": "notification",
            "title": title,
            "summary": str(item.get("why_this_surfaced_now", "")).strip() or "JARVIS surfaced this for operator review.",
            "domain": "assistant-core",
            "status": str(item.get("status", "")).strip() or "unseen",
            "owner_agent": "notification-feed",
            "next_action": "Open or ignore this surfaced notification.",
            "next_review_at": "now",
            "autonomy_summary": "Operator review required before the notification is cleared.",
            "available_actions": [{"id": "open", "label": "Open"}, {"id": "ignore", "label": "Ignore"}],
            "why_now": str(item.get("why_this_surfaced_now", "")).strip() or "Recent runtime pressure surfaced this notification.",
            "evidence_lines": [
                f"Notification status: {str(item.get('status', '')).strip() or 'unseen'}",
                f"Priority class: {str(item.get('priority_class', '')).strip() or 'normal'}",
                "Operator review is required before this surfaced notification is cleared.",
            ],
            "decision_history": [],
            "last_decision_summary": "No prior approval decision attached.",
            "change_summary": "No action diff captured yet.",
            "action_result_summary": "No action result captured yet.",
            "change_evidence_summary": "No post-action evidence captured yet.",
            "field_delta_summary": "No field deltas captured yet.",
            "contract_delta_summary": "No contract deltas captured yet.",
            "derived_delta_summary": "No derived deltas captured yet.",
            "recent_trace": [
                {
                    "title": str(activity.get("title", "")).strip() or "Activity",
                    "detail": str(activity.get("subtitle", "")).strip() or str(activity.get("result", "")).strip() or "Recent activity signal.",
                    "timestamp": str(activity.get("timestamp", "")).strip(),
                }
                for activity in matching_activity
            ],
        }
    return {
        "source_kind": "none",
        "title": "No item selected",
        "summary": "Select an open loop or notification to inspect deeper detail.",
        "domain": "general",
        "status": "idle",
        "owner_agent": "command-center",
        "next_action": "Choose a surfaced item.",
        "next_review_at": "not scheduled",
        "autonomy_summary": "No active item selected.",
        "available_actions": [],
        "why_now": "The detail inspector activates when JARVIS has a live item to inspect.",
        "evidence_lines": ["No evidence captured because no live item is currently selected."],
        "decision_history": [],
        "last_decision_summary": "No prior decision attached.",
        "change_summary": "No action diff captured yet.",
        "action_result_summary": "No action result captured yet.",
        "change_evidence_summary": "No post-action evidence captured yet.",
        "field_delta_summary": "No field deltas captured yet.",
        "contract_delta_summary": "No contract deltas captured yet.",
        "derived_delta_summary": "No derived deltas captured yet.",
        "recent_trace": [],
    }


def _notification_preview(
    *,
    supervision_snapshot: dict[str, Any],
    approval_snapshot: dict[str, Any],
    activity_feed: list[dict[str, Any]],
) -> dict[str, Any]:
    what_needs_me = list(supervision_snapshot.get("what_needs_me") or [])
    items: list[dict[str, Any]] = []
    for item in what_needs_me[:2]:
        items.append(
            {
                "notification_id": "",
                "title": str(item.get("title", "")).strip() or "Attention item",
                "status": "unseen",
                "priority_class": "normal",
                "why_this_surfaced_now": str(item.get("detail", "")).strip() or "JARVIS surfaced this for operator review.",
                "actions": {},
            }
        )
    for item in list(approval_snapshot.get("pending") or [])[:1]:
        items.append(
            {
                "notification_id": "",
                "title": str(item.get("title", "")).strip() or "Approval request",
                "status": "surfaced",
                "priority_class": str(item.get("risk_tier", "")).strip() or "high",
                "why_this_surfaced_now": str(item.get("description", "")).strip() or "Pending approval needs a decision.",
                "actions": {},
            }
        )
    event_titles = [
        str(item.get("title", "")).strip()
        for item in activity_feed[:3]
        if str(item.get("title", "")).strip()
    ]
    return {
        "summary": {
            "total": len(items),
            "unread": len(items),
            "event_signals": len(event_titles),
        },
        "items": items[:4],
        "recent_events": event_titles,
    }


def _action_journal(
    *,
    approval_snapshot: dict[str, Any],
    activity_feed: list[dict[str, Any]],
) -> dict[str, Any]:
    history = list(approval_snapshot.get("history") or [])
    entries: list[dict[str, Any]] = []
    for item in history[:4]:
        entries.append(
            {
                "kind": "approval-history",
                "title": str(item.get("title", "")).strip() or "Approval history entry",
                "status": str(item.get("status", "")).strip() or "unknown",
                "detail": str((item.get("supervision_decision") or {}).get("resolution", "")).strip()
                or str(item.get("approved_by", "")).strip()
                or "Recent approval decision.",
                "timestamp": str(item.get("approved_at", "")).strip()
                or str(item.get("executed_at", "")).strip()
                or str(item.get("requested_at", "")).strip(),
                "related_kind": "open-loop",
                "related_label": str(item.get("title", "")).strip() or "Related open loop",
            }
        )
    for item in activity_feed[:4]:
        entries.append(
            {
                "kind": str(item.get("entry_type", "")).strip() or "activity",
                "title": str(item.get("title", "")).strip() or "Recent activity",
                "status": str(item.get("result", "")).strip() or "observed",
                "detail": str(item.get("subtitle", "")).strip() or "Recent runtime activity.",
                "timestamp": str(item.get("timestamp", "")).strip(),
                "related_kind": str(item.get("related_kind", "")).strip() or ("open-loop" if str(item.get("subtitle", "")).strip() else "activity"),
                "related_label": str(item.get("related_label", "")).strip() or str(item.get("subtitle", "")).strip() or str(item.get("title", "")).strip() or "Related activity",
            }
        )
    entries.sort(key=lambda item: str(item.get("timestamp", "")), reverse=True)
    operator_count = sum(
        1 for item in entries[:8] if str(item.get("kind", "")).strip() in {"approval-history", "local-action", "home-action", "operator-action"}
    )
    autonomous_count = sum(
        1
        for item in entries[:8]
        if str(item.get("kind", "")).strip() not in {"approval-history", "local-action", "home-action", "operator-action"}
    )
    return {
        "count": len(entries[:8]),
        "operator_count": operator_count,
        "autonomous_count": autonomous_count,
        "entries": entries[:8],
    }


def _needs_me_cockpit(
    *,
    supervision_snapshot: dict[str, Any],
    approval_snapshot: dict[str, Any],
    open_loop_inspector: dict[str, Any],
    notification_preview: dict[str, Any],
    failure_recovery: dict[str, Any],
) -> dict[str, Any]:
    queue: dict[str, dict[str, Any]] = {}

    def urgency_score(level: str) -> int:
        normalized = str(level or "").strip().lower()
        return {
            "critical": 4,
            "high": 3,
            "medium": 2,
            "normal": 1,
            "low": 0,
        }.get(normalized, 1)

    def normalized_key(title: str, source: str) -> str:
        normalized_title = " ".join(str(title or "").strip().lower().split()) or "untitled"
        normalized_source = str(source or "").strip().lower() or "general"
        return f"{normalized_title}::{normalized_source}"

    def add_need(
        *,
        title: str,
        detail: str,
        urgency: str,
        source: str,
        route: str,
        route_label: str,
        action_hint: str,
        focus_targets: list[str] | None = None,
        primary_action: dict[str, Any] | None = None,
    ) -> None:
        cleaned_title = str(title or "").strip()
        if not cleaned_title:
            return
        key = normalized_key(cleaned_title, source)
        candidate_score = urgency_score(urgency)
        existing = queue.get(key)
        if existing is None:
            queue[key] = {
                "need_key": key,
                "title": cleaned_title,
                "detail": str(detail or "").strip() or "Needs operator review.",
                "urgency": str(urgency or "normal").strip().lower() or "normal",
                "urgency_score": candidate_score,
                "sources": [str(source or "general").strip() or "general"],
                "route": str(route or "/command-center").strip() or "/command-center",
                "route_label": str(route_label or "Open command center").strip() or "Open command center",
                "action_hint": str(action_hint or "").strip() or "Inspect this item from the command center.",
                "focus_targets": [str(item).strip() for item in (focus_targets or []) if str(item).strip()],
                "primary_action": dict(primary_action or {}),
            }
            return
        source_label = str(source or "general").strip() or "general"
        if source_label not in existing["sources"]:
            existing["sources"].append(source_label)
        if candidate_score > int(existing.get("urgency_score", 0) or 0):
            existing["urgency"] = str(urgency or "normal").strip().lower() or "normal"
            existing["urgency_score"] = candidate_score
            existing["route"] = str(route or existing.get("route", "")).strip() or existing["route"]
            existing["route_label"] = str(route_label or existing.get("route_label", "")).strip() or existing["route_label"]
            existing["action_hint"] = str(action_hint or existing.get("action_hint", "")).strip() or existing["action_hint"]
            if focus_targets:
                existing["focus_targets"] = [str(item).strip() for item in focus_targets if str(item).strip()]
            if primary_action:
                existing["primary_action"] = dict(primary_action)
        if detail and len(str(detail)) > len(str(existing.get("detail", ""))):
            existing["detail"] = str(detail).strip()

    what_needs_me = list(supervision_snapshot.get("what_needs_me") or [])
    for item in what_needs_me[:6]:
        title = str(item.get("title", "")).strip()
        detail = str(item.get("detail", "")).strip()
        joined = f"{title} {detail}".lower()
        urgency = "high" if any(token in joined for token in ("urgent", "high", "approval", "blocked", "review")) else "normal"
        add_need(
            title=title,
            detail=detail,
            urgency=urgency,
            source="supervision",
            route="/supervision-snapshot",
            route_label="Open supervision",
            action_hint="Inspect the supervision snapshot for full return-brief context.",
            focus_targets=["open-loop", "journal"],
        )

    for item in list(approval_snapshot.get("pending") or [])[:6]:
        risk_tier = str(item.get("risk_tier", "")).strip().lower()
        urgency = "critical" if risk_tier == "high" else "high" if risk_tier in {"medium", "elevated"} else "normal"
        request_id = str(item.get("request_id", "")).strip()
        actions = dict(item.get("actions") or {})
        add_need(
            title=str(item.get("title", "")).strip() or "Pending approval",
            detail=str(item.get("description", "")).strip() or "Approval queue needs review.",
            urgency=urgency,
            source="approval",
            route="/approval-queue",
            route_label="Open approval queue",
            action_hint="Approve, reject, cancel, or execute from the approval queue.",
            focus_targets=["open-loop", "journal"],
            primary_action={
                "label": "Approve",
                "endpoint": str(actions.get("approve") or (f"/api/approvals/{request_id}/approve" if request_id else "")).strip(),
                "method": "POST",
            } if request_id or actions.get("approve") else None,
        )

    for item in list(open_loop_inspector.get("items") or [])[:6]:
        status = str(item.get("status", "")).strip().lower()
        urgency = "high" if status in {"pending", "needs-me", "waiting"} else "normal"
        item_id = str(item.get("item_id", "")).strip()
        domain = str(item.get("domain", "")).strip()
        available_actions = list(item.get("available_actions") or [])
        primary_open_loop_action = None
        if item_id and domain and available_actions:
            first_action = dict(available_actions[0] or {})
            action_id = str(first_action.get("id", "")).strip()
            if action_id:
                primary_open_loop_action = {
                    "label": str(first_action.get("label") or action_id),
                    "endpoint": "/api/open-loops/action",
                    "method": "POST",
                    "body": {
                        "actor": "Chris",
                        "domain": domain,
                        "item_id": item_id,
                        "action": action_id,
                    },
                }
        add_need(
            title=str(item.get("title", "")).strip() or "Open loop needs review",
            detail=str(item.get("summary", "")).strip() or str(item.get("next_action", "")).strip() or "Open-loop review needed.",
            urgency=urgency,
            source="open-loop",
            route="/command-center",
            route_label="Inspect open loop",
            action_hint=str(item.get("next_action", "")).strip() or "Inspect this open loop from the command center.",
            focus_targets=["open-loop"],
            primary_action=primary_open_loop_action,
        )

    for item in list(notification_preview.get("items") or [])[:6]:
        priority_class = str(item.get("priority_class", "")).strip().lower()
        urgency = "high" if priority_class == "high" else "normal"
        notification_id = str(item.get("notification_id", "")).strip()
        actions = dict(item.get("actions") or {})
        add_need(
            title=str(item.get("title", "")).strip() or "Notification surfaced",
            detail=str(item.get("why_this_surfaced_now", "")).strip() or str(item.get("status", "")).strip() or "Notification needs review.",
            urgency=urgency,
            source="notification",
            route="/command-center",
            route_label="Inspect notification",
            action_hint="Open or ignore the surfaced notification from the command center.",
            focus_targets=["notification", "journal"],
            primary_action={
                "label": "Open",
                "endpoint": str(actions.get("open") or (f"/api/assistant-core/notifications/{notification_id}" if notification_id else "")).strip(),
                "method": "POST",
                "body": {"actor": "Chris", "status": "opened"},
            } if notification_id or actions.get("open") else None,
        )

    for item in list(failure_recovery.get("failing_integrations") or [])[:4]:
        add_need(
            title=f"Repair {str(item.get('name', '')).strip() or 'integration'}",
            detail=str(item.get("detail", "")).strip() or "Integration failure surfaced.",
            urgency="critical",
            source="failure",
            route="/supervision-snapshot",
            route_label="Open recovery view",
            action_hint="Inspect failure and recovery posture before retrying related actions.",
            focus_targets=["journal", "open-loop"],
        )

    for item in list(failure_recovery.get("recent_failures") or [])[:4]:
        add_need(
            title=str(item.get("title", "")).strip() or "Recent failure surfaced",
            detail=str(item.get("detail", "")).strip() or str(item.get("timestamp", "")).strip() or "Runtime failure needs review.",
            urgency="high",
            source="failure",
            route="/command-center",
            route_label="Inspect failure trace",
            action_hint="Review the command-center detail surfaces and recent trace before acting.",
            focus_targets=["journal", "open-loop"],
        )

    items = sorted(
        queue.values(),
        key=lambda item: (
            -int(item.get("urgency_score", 0) or 0),
            -len(list(item.get("sources") or [])),
            str(item.get("title", "")),
        ),
    )[:8]
    critical_count = sum(1 for item in items if str(item.get("urgency", "")).strip() == "critical")
    high_count = sum(1 for item in items if str(item.get("urgency", "")).strip() == "high")
    return {
        "total": len(items),
        "critical_count": critical_count,
        "high_count": high_count,
        "approval_count": sum(1 for item in items if "approval" in list(item.get("sources") or [])),
        "failure_count": sum(1 for item in items if "failure" in list(item.get("sources") or [])),
        "notification_count": sum(1 for item in items if "notification" in list(item.get("sources") or [])),
        "headline": str(items[0].get("title", "")) if items else "Nothing urgent right now.",
        "items": items,
    }


def _needs_motion(
    *,
    needs_cockpit: dict[str, Any],
    activity_feed: list[dict[str, Any]],
) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    for item in list(needs_cockpit.get("items") or [])[:5]:
        entries.append(
            {
                "kind": "active",
                "title": str(item.get("title", "")).strip() or "Active need",
                "status": str(item.get("urgency", "")).strip() or "normal",
                "detail": str(item.get("detail", "")).strip()
                or str(item.get("action_hint", "")).strip()
                or "JARVIS surfaced this need for operator review.",
                "timestamp": "live queue",
                "need_key": str(item.get("need_key", "")).strip(),
                "source_kind": "need",
                "source_label": str(item.get("title", "")).strip() or str(item.get("need_key", "")).strip() or "Active need",
                "queue_state": " / ".join(
                    part
                    for part in [
                        str(item.get("urgency", "")).strip(),
                        ", ".join(str(source).strip() for source in (item.get("sources") or []) if str(source).strip()),
                    ]
                    if part
                )
                or "active",
                "transition": "observed -> active",
                "evidence_links": [
                    {"label": "Command Center", "href": "/command-center"},
                    {
                        "label": "Open approval queue" if "approval" in list(item.get("sources") or []) else "Open open loops JSON",
                        "href": "/approval-queue" if "approval" in list(item.get("sources") or []) else "/api/open-loops?actor=Chris",
                    },
                ],
                "evidence": " / ".join(
                    part
                    for part in [
                        str(item.get("urgency", "")).strip(),
                        ", ".join(str(source).strip() for source in (item.get("sources") or []) if str(source).strip()),
                        str(item.get("route_label", "")).strip(),
                    ]
                    if part
                ),
            }
        )
    for item in activity_feed:
        haystack = " ".join(
            [
                str(item.get("title", "")),
                str(item.get("subtitle", "")),
                str(item.get("result", "")),
                str(item.get("entry_type", "")),
            ]
        ).lower()
        if not any(token in haystack for token in ("approval", "review", "fail", "error", "blocked", "notification")):
            continue
        entries.append(
            {
                "kind": "signal",
                "title": str(item.get("title", "")).strip() or "Recent signal",
                "status": str(item.get("entry_type", "")).strip() or "activity",
                "detail": str(item.get("result", "")).strip()
                or str(item.get("subtitle", "")).strip()
                or "Recent runtime activity may have changed triage posture.",
                "timestamp": str(item.get("timestamp", "")).strip() or "recent activity",
                "need_key": "",
                "source_kind": "activity",
                "source_label": str(item.get("subtitle", "")).strip() or str(item.get("title", "")).strip() or "Recent activity",
                "source_entry_type": str(item.get("entry_type", "")).strip() or "activity",
                "queue_state": str(item.get("entry_type", "")).strip() or "signal",
                "transition": "runtime signal -> review",
                "evidence_links": [
                    {"label": "Activity JSON", "href": "/api/activity"},
                    {"label": "Command Center", "href": "/command-center"},
                ],
                "evidence": " / ".join(
                    part
                    for part in [
                        str(item.get("entry_type", "")).strip(),
                        str(item.get("subtitle", "")).strip(),
                        str(item.get("timestamp", "")).strip(),
                    ]
                    if part
                ),
            }
        )
        if len(entries) >= 8:
            break
    return {
        "count": len(entries[:8]),
        "active_count": sum(1 for item in entries[:8] if str(item.get("kind", "")).strip() == "active"),
        "signal_count": sum(1 for item in entries[:8] if str(item.get("kind", "")).strip() == "signal"),
        "entries": entries[:8],
    }


def _registry_status() -> dict[str, Any]:
    try:
        bundle = load_contract_bundle(validate=True)
        snapshot = bundle.snapshot()
    except Exception as exc:
        return {
            "agent_count": 0,
            "domains": [],
            "authority_stages": [],
            "registry_error": str(exc),
            "sample_contracts": [],
        }

    agents = list(bundle.registry.get("agents", []))
    sample_contracts = []
    for item in agents[:6]:
        if not isinstance(item, dict):
            continue
        sample_contracts.append(
            {
                "agent_id": str(item.get("agent_id", "")),
                "label": str(item.get("label", "") or item.get("agent_id", "")),
                "domain": str(item.get("operating_domain", "")),
                "authority_stage": str(item.get("authority_stage", "")),
            }
        )
    return {
        "agent_count": int(snapshot.get("agent_count", 0) or 0),
        "domains": list(snapshot.get("domains", []) or []),
        "authority_stages": list(snapshot.get("authority_stages", []) or []),
        "registry_error": "",
        "sample_contracts": sample_contracts,
    }


def _mission_task_board() -> dict[str, Any]:
    dossiers = _read_json_list(REPO_ROOT / "data" / "missions" / "dossiers.json")
    task_agents = _read_json_list(REPO_ROOT / "data" / "missions" / "task_agents.json")
    task_agents_by_mission: dict[str, list[dict[str, Any]]] = {}
    for item in task_agents:
        mission_id = str(item.get("mission_id", "")).strip()
        if not mission_id:
            continue
        task_agents_by_mission.setdefault(mission_id, []).append(item)

    items = []
    counts = {"now": 0, "next": 0, "blocked": 0, "completed": 0}
    for dossier in dossiers[:8]:
        mission_id = str(dossier.get("mission_id", "")).strip()
        subtasks = [item for item in list(dossier.get("subtasks") or []) if isinstance(item, dict)]
        active_subtasks = [item for item in subtasks if str(item.get("status", "")).strip().lower() == "active"]
        blocked_subtasks = [item for item in subtasks if str(item.get("status", "")).strip().lower() == "blocked"]
        completed_subtasks = [item for item in subtasks if str(item.get("status", "")).strip().lower() == "completed"]
        status = str(dossier.get("status", "")).strip().lower() or "active"
        if status == "completed":
            lane = "completed"
            counts["completed"] += 1
        elif blocked_subtasks:
            lane = "blocked"
            counts["blocked"] += 1
        elif active_subtasks:
            lane = "now"
            counts["now"] += 1
        else:
            lane = "next"
            counts["next"] += 1
        mission_task_agents = task_agents_by_mission.get(mission_id, [])
        items.append(
            {
                "mission_id": mission_id,
                "title": str(dossier.get("title", "")).strip() or str(dossier.get("request", "")).strip() or "Mission",
                "brief": str(dossier.get("brief", "")).strip() or "No mission brief captured yet.",
                "status": status or "active",
                "lane": lane,
                "lane_class": "accepted" if lane == "completed" else "regressed" if lane == "blocked" else "steady" if lane == "next" else "artifact",
                "primary_domain": str(dossier.get("primary_domain", "")).strip() or "general",
                "owner_agent": str(dossier.get("owner_agent", "")).strip() or "jarvis-orchestrator",
                "selected_agents": [str(item).strip() for item in list(dossier.get("selected_agents") or []) if str(item).strip()],
                "task_agent_labels": [str(item.get("label", "")).strip() for item in mission_task_agents if str(item.get("label", "")).strip()],
                "subtask_count": len(subtasks),
                "active_count": len(active_subtasks),
                "blocked_count": len(blocked_subtasks),
                "completed_count": len(completed_subtasks),
                "next_step": str((active_subtasks[0] if active_subtasks else (subtasks[0] if subtasks else {})).get("title", "")).strip() or "Review mission brief",
                "what_became_real": str(dossier.get("brief", "")).strip() or "Mission board record loaded from the local mission store.",
                "remains_partial": "Mission workspaces are live now, but broader mission creation/edit flows, richer handoff authoring, and deeper seam linkage still need a later slice.",
                "updated_at": str(dossier.get("updated_at", "")).strip() or str(dossier.get("created_at", "")).strip() or "not recorded",
            }
        )

    return {
        "summary": f"{counts['now']} now, {counts['next']} next, {counts['blocked']} blocked, {counts['completed']} completed mission lane(s).",
        "item_count": len(items),
        "counts": counts,
        "items": items,
    }


def _agent_ops_roster() -> dict[str, Any]:
    registry_payload = json.loads((REPO_ROOT / "data" / "agents" / "jarvis_agent_registry.v1.json").read_text())
    runtime_path = REPO_ROOT / "data" / "agents" / "runtime_kernel_state.json"
    try:
        runtime_payload = json.loads(runtime_path.read_text())
    except FileNotFoundError:
        runtime_payload = {"agents": {}}
    task_agents_path = REPO_ROOT / "data" / "missions" / "task_agents.json"
    try:
        task_agents_payload = json.loads(task_agents_path.read_text()) if task_agents_path.exists() else []
    except (OSError, json.JSONDecodeError):
        task_agents_payload = []
    registry_agents = list(registry_payload.get("agents") or [])
    runtime_agents = dict(runtime_payload.get("agents") or {})
    task_agents = [dict(item) for item in list(task_agents_payload or []) if isinstance(item, dict)]

    def maturity_label(promotion_status: str) -> tuple[str, str]:
        normalized = str(promotion_status or "").strip().lower()
        if normalized in {"core", "durable"}:
            return "Durable", "accepted"
        if normalized in {"ephemeral", "trial"}:
            return "Wired", "steady"
        if normalized in {"promoted", "compounding"}:
            return "Compounding", "accepted"
        return "Useful", "artifact"

    def status_badge(runtime_entry: dict[str, Any], registry_entry: dict[str, Any]) -> tuple[str, str]:
        lifecycle = dict(runtime_entry.get("lifecycle") or {})
        health = dict(runtime_entry.get("health") or {})
        current_state = str(lifecycle.get("current_state", "")).strip().lower()
        health_status = str(health.get("status", "")).strip().lower()
        if current_state == "blocked" or health_status in {"blocked", "degraded"}:
            return "blocked", "regressed"
        if current_state in {"running", "active"} and health_status in {"healthy", "fresh"}:
            return "running", "accepted"
        if current_state in {"running", "active"}:
            return "active", "artifact"
        if current_state:
            return current_state, "steady"
        status = str(registry_entry.get("status", "")).strip().lower()
        return (status or "unknown"), ("steady" if status else "artifact")

    items = []
    counts = {"running": 0, "blocked": 0, "attention": 0, "core_agents": 0, "task_agents": 0, "promoted": 0}
    for registry_entry in registry_agents[:12]:
        agent_id = str(registry_entry.get("agent_id", "")).strip()
        runtime_entry = dict(runtime_agents.get(agent_id) or {})
        contract = dict(runtime_entry.get("contract") or {})
        lifecycle = dict(runtime_entry.get("lifecycle") or {})
        heartbeat = dict(runtime_entry.get("heartbeat") or {})
        health = dict(runtime_entry.get("health") or {})
        supervision = dict(runtime_entry.get("supervision") or {})
        status_label, status_class = status_badge(runtime_entry, registry_entry)
        maturity, maturity_class = maturity_label(str(registry_entry.get("promotion_status", "")).strip())
        counts["core_agents"] += 1
        if status_label == "blocked":
            counts["blocked"] += 1
        elif supervision.get("requires_attention"):
            counts["attention"] += 1
        else:
            counts["running"] += 1
        if maturity == "Compounding":
            counts["promoted"] += 1
        items.append(
            {
                "agent_id": agent_id,
                "name": str(registry_entry.get("label", "")).strip() or agent_id,
                "purpose": str(registry_entry.get("purpose", "")).strip() or str(contract.get("mission", "")).strip() or "No purpose recorded.",
                "domain": str(registry_entry.get("operating_domain", "")).strip() or str(contract.get("execution_lane", "")).strip() or "general",
                "status": status_label,
                "status_class": status_class,
                "assignment": str(registry_entry.get("primary_lane", "")).strip() or str(contract.get("lane_owner", "")).strip() or "unassigned",
                "last_activity": str(heartbeat.get("last_heartbeat_at", "")).strip() or str(lifecycle.get("last_transition_at", "")).strip() or "not recorded",
                "module": str(contract.get("execution_lane", "")).strip() or str(registry_entry.get("primary_lane", "")).strip() or "general",
                "maturity": maturity,
                "maturity_class": maturity_class,
                "authority_stage": str(registry_entry.get("authority_stage", "")).strip() or "draft",
                "mission_roles": [str(item).strip() for item in list(registry_entry.get("mission_roles") or contract.get("mission_roles") or []) if str(item).strip()],
                "attention_reason": str(supervision.get("attention_reason", "")).strip() or str(health.get("reason", "")).strip(),
                "heartbeat_status": str(heartbeat.get("status", "")).strip() or "unknown",
                "source_kind": "core-agent",
                "source_label": "Core Agent",
                "is_task_agent": False,
                "mission_id": "",
                "template_id": "",
                "promotion_candidate": False,
                "policy_assignment": "",
                "memory_boundary": "",
            }
        )

    for task_entry in task_agents[:12]:
        agent_id = str(task_entry.get("agent_id", "")).strip()
        if not agent_id:
            continue
        status_value = str(task_entry.get("status", "")).strip().lower() or "active"
        promotion_status = str(task_entry.get("promotion_status", "")).strip()
        maturity, maturity_class = maturity_label(promotion_status)
        attention_reason = ""
        if bool(task_entry.get("promotion_candidate")):
            attention_reason = "Eligible for promotion based on recent task-agent outcomes."
        if status_value in {"blocked", "failed"}:
            status_label, status_class = "blocked", "regressed"
            counts["blocked"] += 1
        elif status_value in {"retired", "paused"}:
            status_label, status_class = status_value, "steady"
            counts["attention"] += 1
        elif attention_reason:
            status_label, status_class = "attention", "artifact"
            counts["attention"] += 1
        else:
            status_label, status_class = status_value or "active", "accepted"
            counts["running"] += 1
        counts["task_agents"] += 1
        if str(promotion_status).strip().lower() in {"promoted", "compounding"}:
            counts["promoted"] += 1
        mission_id = str(task_entry.get("mission_id", "")).strip()
        items.append(
            {
                "agent_id": agent_id,
                "name": str(task_entry.get("label", "")).strip() or agent_id,
                "purpose": str(task_entry.get("purpose", "")).strip() or "No purpose recorded.",
                "domain": str(task_entry.get("domain", "")).strip() or "general",
                "status": status_label,
                "status_class": status_class,
                "assignment": mission_id or str(task_entry.get("trust_zone", "")).strip() or "unassigned",
                "last_activity": str(task_entry.get("last_used_at", "")).strip() or str(task_entry.get("updated_at", "")).strip() or str(task_entry.get("created_at", "")).strip() or "not recorded",
                "module": str(task_entry.get("domain", "")).strip() or str(task_entry.get("template_id", "")).strip() or "mission-control",
                "maturity": maturity,
                "maturity_class": maturity_class,
                "authority_stage": "task-agent",
                "mission_roles": [str(item).strip() for item in list(task_entry.get("mission_roles") or []) if str(item).strip()],
                "attention_reason": attention_reason,
                "heartbeat_status": status_value or "unknown",
                "source_kind": "task-agent",
                "source_label": "Task Agent",
                "is_task_agent": True,
                "mission_id": mission_id,
                "template_id": str(task_entry.get("template_id", "")).strip(),
                "promotion_candidate": bool(task_entry.get("promotion_candidate")),
                "policy_assignment": str(task_entry.get("policy_assignment", "")).strip(),
                "memory_boundary": str(task_entry.get("memory_boundary", "")).strip(),
            }
        )

    return {
        "summary": (
            f"{counts['running']} running, {counts['blocked']} blocked, {counts['attention']} needing attention "
            f"across {len(items)} visible agent(s), including {counts['task_agents']} task agent(s) and {counts['promoted']} promoted agent(s)."
        ),
        "item_count": len(items),
        "counts": counts,
        "items": items,
    }


def _progress_dashboard(
    lane_progress: dict[str, Any],
    seam_tracker: dict[str, Any],
    mission_task_board: dict[str, Any],
    agent_ops_roster: dict[str, Any],
    failure_recovery: dict[str, Any],
) -> dict[str, Any]:
    dirty_count = int(lane_progress.get("dirty_count", 0) or 0)
    recent_commits = list(lane_progress.get("recent_commits") or [])
    seam_counts = dict(seam_tracker.get("counts") or {})
    mission_counts = dict(mission_task_board.get("counts") or {})
    agent_counts = dict(agent_ops_roster.get("counts") or {})
    failure_count = int(failure_recovery.get("integration_issue_count", 0) or 0)

    def readiness(status: str) -> tuple[str, str]:
        normalized = str(status or "").strip()
        mapping = {
            "Idea": ("idea", "steady"),
            "Mocked": ("mocked", "steady"),
            "Stubbed": ("stubbed", "artifact"),
            "Wired": ("wired", "artifact"),
            "Useful": ("useful", "accepted"),
            "Durable": ("durable", "accepted"),
            "Compounding": ("compounding", "accepted"),
        }
        return mapping.get(normalized, (normalized.lower() or "wired", "steady"))

    modules = [
        {
            "module": "Command Center/Home",
            "level": "Level 3",
            "status": "Useful",
            "summary": f"Live route with needs, memory, activity, missions, seams, and agent operations. Dirty lane posture: {dirty_count}.",
            "evidence": recent_commits[0] if recent_commits else "No recent commit captured.",
        },
        {
            "module": "Agent Operations",
            "level": "Level 3",
            "status": "Useful" if int(agent_ops_roster.get("item_count", 0) or 0) else "Stubbed",
            "summary": f"{agent_counts.get('running', 0)} running agent(s), {agent_counts.get('blocked', 0)} blocked, {agent_counts.get('attention', 0)} needing attention.",
            "evidence": agent_ops_roster.get("summary", "No agent roster summary yet."),
        },
        {
            "module": "Mission Board",
            "level": "Level 3",
            "status": "Useful" if int(mission_task_board.get("item_count", 0) or 0) else "Stubbed",
            "summary": f"{mission_counts.get('now', 0)} now, {mission_counts.get('next', 0)} next, {mission_counts.get('blocked', 0)} blocked, {mission_counts.get('completed', 0)} completed.",
            "evidence": mission_task_board.get("summary", "No mission board summary yet."),
        },
        {
            "module": "Progress",
            "level": "Level 3",
            "status": "Wired",
            "summary": f"{seam_counts.get('Useful', 0)} useful seam(s), {seam_counts.get('Wired', 0)} wired seam(s), {seam_counts.get('Durable', 0)} durable seam(s).",
            "evidence": seam_tracker.get("summary", "No seam tracker summary yet."),
        },
        {
            "module": "Failure & Recovery",
            "level": "Level 3",
            "status": "Wired" if failure_count else "Useful",
            "summary": f"{failure_count} integration issue(s), {int(failure_recovery.get('pending_approval_count', 0) or 0)} pending approval gate(s).",
            "evidence": failure_recovery.get("action_items", [{}])[0].get("detail", "Recovery posture stable.") if list(failure_recovery.get("action_items") or []) else "Recovery posture stable.",
        },
    ]

    items = []
    for item in modules:
        readiness_label, readiness_class = readiness(item["status"])
        items.append(
            {
                "module": item["module"],
                "roadmap_level": item["level"],
                "status": item["status"],
                "status_label": readiness_label,
                "status_class": readiness_class,
                "summary": item["summary"],
                "evidence": item["evidence"],
            }
        )

    counts = {
        "useful": sum(1 for item in items if item["status"] == "Useful"),
        "wired": sum(1 for item in items if item["status"] == "Wired"),
        "durable": sum(1 for item in items if item["status"] == "Durable"),
        "compounding": sum(1 for item in items if item["status"] == "Compounding"),
    }
    return {
        "summary": f"{counts['useful']} useful, {counts['wired']} wired, {counts['durable']} durable, {counts['compounding']} compounding modules in the visible Level 3 base.",
        "item_count": len(items),
        "counts": counts,
        "items": items,
    }


def _level3_checklist(
    *,
    progress_dashboard: dict[str, Any],
    seam_tracker: dict[str, Any],
    core_modules: dict[str, Any],
    lane_progress: dict[str, Any],
    failure_recovery: dict[str, Any],
) -> dict[str, Any]:
    progress_items = [item for item in list(progress_dashboard.get("items") or []) if isinstance(item, dict)]
    seam_items = [item for item in list(seam_tracker.get("items") or []) if isinstance(item, dict)]
    module_items = [item for item in list(core_modules.get("items") or []) if isinstance(item, dict)]
    remaining_items = [item for item in progress_items if str(item.get("status", "")).strip() != "Useful"]
    branch = str(lane_progress.get("branch", "")).strip() or "unknown branch"
    dirty_count = int(lane_progress.get("dirty_count", 0) or 0)
    issue_count = int(failure_recovery.get("integration_issue_count", 0) or 0)
    approval_count = int(failure_recovery.get("pending_approval_count", 0) or 0)

    def seam_named(name: str) -> dict[str, Any]:
        for item in seam_items:
            if str(item.get("name", "")).strip() == name:
                return item
        return {}

    def module_named(title: str) -> dict[str, Any]:
        for item in module_items:
            if str(item.get("title", "")).strip() == title:
                return item
        return {}

    activity_seam = seam_named("Activity Feed Standalone Surface")
    mission_seam = seam_named("Mission Task Board Standalone Surface")
    agent_ops_seam = seam_named("Agent Operations Module Standalone Surface")
    health_module = module_named("Health")

    items = [
        {
            "title": "Durable Cross-Surface Activity Continuity",
            "status": "Open",
            "status_class": "steady",
            "area": "Activity Feed and Command Center",
            "why_open": str(activity_seam.get("remains_partial", "")).strip()
            or "Activity continuity still needs a durable shared event substrate instead of command-center-local bridges.",
            "live_signal": f"{len(remaining_items)} remaining non-useful progress row(s) still depend on summary-level continuity rather than durable shared events.",
            "exact_files": [
                "jarvis/audit.py",
                "jarvis/command_center_index.py",
                "jarvis/service.py",
                "jarvis/render_pages.py",
            ],
            "proof_routes": ["/command-center", "/activity-center", "/api/activity/module"],
            "next_slice": "Persist home and operator continuity events into the shared audit/event substrate, then render those same durable entries in both Command Center and Activity Feed.",
        },
        {
            "title": "Mission Board Depth Beyond Lane Changes",
            "status": "Open",
            "status_class": "steady",
            "area": "Mission and Task Board",
            "why_open": str(mission_seam.get("remains_partial", "")).strip()
            or "Mission flows still need richer mission editing and deeper seam linkage.",
            "live_signal": str(mission_seam.get("what_became_real", "")).strip()
            or "Mission posture is still strongest at the lane-summary level.",
            "exact_files": [
                "jarvis/command_center_index.py",
                "jarvis/service.py",
                "jarvis/render_pages.py",
                "tests/test_command_center_service_surface.py",
            ],
            "proof_routes": ["/mission-board", "/api/mission-board/module", "/api/missions"],
            "next_slice": "Deepen mission edit flows further and expand seam linkage beyond the first mission-detail pass now that mission authoring, mission workspaces, handoff authoring, and per-agent work-state controls are live on the standalone route.",
        },
        {
            "title": "Agent Operations Assignment and Continuity Controls",
            "status": "Open",
            "status_class": "steady",
            "area": "Agent Roster and Ops",
            "why_open": str(agent_ops_seam.get("remains_partial", "")).strip()
            or "Agent operations still need broader continuity beyond the new assignment editing and outcome review flow.",
            "live_signal": str(agent_ops_seam.get("what_became_real", "")).strip()
            or "Dedicated route exists, but deeper agent mutation controls are still missing.",
            "exact_files": [
                "jarvis/command_center_index.py",
                "jarvis/service.py",
                "jarvis/render_pages.py",
                "tests/test_command_center_index.py",
            ],
            "proof_routes": ["/agent-ops-center", "/api/agent-ops/module"],
            "next_slice": "Deepen cross-route continuity now that mission-linked assignment editing, per-agent outcome review, task-agent promotion, and retirement controls are live on the standalone route.",
        },
        {
            "title": "Durable Seam and Progress Persistence",
            "status": "Open",
            "status_class": "steady",
            "area": "Progress and Seam Tracker",
            "why_open": "Progress is still wired at the readiness layer, and seam records are still branch-scoped local records without durable mission-linked persistence.",
            "live_signal": f"{int(progress_dashboard.get('counts', {}).get('wired', 0) or 0)} wired module(s), {int(seam_tracker.get('counts', {}).get('Wired', 0) or 0)} wired seam(s), branch {branch}, {dirty_count} local change(s).",
            "exact_files": [
                "jarvis/command_center_index.py",
                "jarvis/service.py",
                "jarvis/render_pages.py",
                "tests/test_command_center_service_surface.py",
            ],
            "proof_routes": ["/progress-center", "/api/progress/module", "/api/command-center"],
            "next_slice": "Move seam and readiness records onto a durable backing store so progress history, next-focus posture, and mission linkage survive branch-local control-surface refreshes.",
        },
        {
            "title": "Recovery, Approval, and Supervision Mutation Loops",
            "status": "Open",
            "status_class": "steady",
            "area": "Failure Recovery Stack",
            "why_open": "Failure, approval, and supervision routes now share durable continuity, recovery-gate execution, and durable remediation controls, but broader self-healing depth and richer non-approval execution planning still need follow-on slices.",
            "live_signal": f"{issue_count} integration issue(s) and {approval_count} pending approval gate(s) still define the live failure posture.",
            "exact_files": [
                "jarvis/service.py",
                "jarvis/render_pages.py",
                "jarvis/command_center_index.py",
                "tests/test_command_center_service_surface.py",
            ],
            "proof_routes": ["/recovery-center", "/approval-queue", "/supervision-snapshot"],
            "next_slice": "Deepen broader self-healing and richer recovery planning now that durable remediation and non-approval execution flows are visible across Recovery, Approval Queue, and Supervision Snapshot.",
        },
        {
            "title": "Runtime Hydration Reliability for Partial Modules",
            "status": "Open",
            "status_class": "steady",
            "area": "Module Data Health",
            "why_open": str(health_module.get("remains_partial", "")).strip()
            or "Some module routes still degrade into partial hydration or warning-driven fallback in this runtime.",
            "live_signal": str(health_module.get("evidence", "")).strip()
            or "Health and related modules still surface warning-driven hydration gaps in local verification.",
            "exact_files": [
                "jarvis/service.py",
                "jarvis/health_dashboard.py",
                "jarvis/command_center_index.py",
                "tests/test_command_center_service_surface.py",
            ],
            "proof_routes": ["/health-center", "/api/health/module", "/progress-center"],
            "next_slice": "Repair the missing or warning-prone runtime sources so module payloads stay healthy without falling back to sparse hydration language.",
        },
    ]

    return {
        "summary": f"{len(items)} concrete Level 3 slice(s) still need closure before the working-app base can be called done.",
        "item_count": len(items),
        "open_count": len(items),
        "useful_module_count": int(progress_dashboard.get("counts", {}).get("useful", 0) or 0),
        "wired_module_count": int(progress_dashboard.get("counts", {}).get("wired", 0) or 0),
        "branch": branch,
        "route": "/progress-center#level3-checklist",
        "route_label": "Open Remaining Level 3 Checklist",
        "api_path": "/api/progress/module",
        "items": items,
    }


def _home_overview(
    *,
    generated_at: str,
    brief_preview: dict[str, Any],
    needs_cockpit: dict[str, Any],
    mission_task_board: dict[str, Any],
    agent_ops_roster: dict[str, Any],
    failure_recovery: dict[str, Any],
    progress_dashboard: dict[str, Any],
    activity_feed: list[dict[str, Any]],
    hosted_deployment: dict[str, Any],
) -> dict[str, Any]:
    mission_counts = dict(mission_task_board.get("counts") or {})
    agent_counts = dict(agent_ops_roster.get("counts") or {})
    progress_counts = dict(progress_dashboard.get("counts") or {})
    top_need = dict((needs_cockpit.get("items") or [None])[0] or {})
    next_mission = dict((mission_task_board.get("items") or [None])[0] or {})
    active_agent = dict((agent_ops_roster.get("items") or [None])[0] or {})
    recent_signal = dict(activity_feed[0]) if activity_feed else {}
    dirty_count = int(failure_recovery.get("dirty_count", 0) or 0)
    integration_issue_count = int(failure_recovery.get("integration_issue_count", 0) or 0)
    pending_approval_count = int(failure_recovery.get("pending_approval_count", 0) or 0)
    open_mission_count = int(mission_counts.get("now", 0) or 0) + int(mission_counts.get("next", 0) or 0) + int(mission_counts.get("blocked", 0) or 0)
    system_label = "Stable"
    system_class = "accepted"
    system_summary = "No active recovery bottlenecks surfaced in the home overview."
    if integration_issue_count or pending_approval_count or dirty_count:
        system_label = "Needs Attention"
        system_class = "regressed" if integration_issue_count else "artifact"
        system_summary = (
            f"{integration_issue_count} integration issue(s), "
            f"{pending_approval_count} pending approval gate(s), "
            f"and {dirty_count} dirty working-tree item(s) are shaping the current home posture."
        )

    actions: list[dict[str, Any]] = []

    primary_top_need_action = dict(top_need.get("primary_action") or {})
    top_need_endpoint = str(primary_top_need_action.get("endpoint", "")).strip()
    if top_need_endpoint:
        actions.append(
            {
                "label": str(primary_top_need_action.get("label", "")).strip() or "Handle Top Need",
                "detail": str(top_need.get("detail", "")).strip() or "Act on the highest-priority surfaced need.",
                "endpoint": top_need_endpoint,
                "method": str(primary_top_need_action.get("method", "POST")).strip() or "POST",
                "body": primary_top_need_action.get("body"),
                "needs_key": str(top_need.get("need_key", "")).strip(),
                "route": str(top_need.get("route", "")).strip() or "/command-center",
                "route_label": str(top_need.get("route_label", "")).strip() or "Open Top Need",
            }
        )
    else:
        actions.append(
            {
                "label": str(top_need.get("route_label", "")).strip() or "Open Top Need",
                "route": str(top_need.get("route", "")).strip() or "/command-center",
                "detail": str(top_need.get("detail", "")).strip() or "Inspect the highest-priority surfaced need.",
            }
        )

    mission_id = str(next_mission.get("mission_id", "")).strip()
    mission_lane = str(next_mission.get("lane", "")).strip().lower()
    mission_status = str(next_mission.get("status", "")).strip().lower()
    if mission_id and mission_lane != "now" and mission_status != "completed":
        actions.append(
            {
                "label": "Move Mission to Now",
                "detail": str(next_mission.get("next_step", "")).strip() or "Advance the next visible mission into the active lane.",
                "endpoint": f"/api/missions/{mission_id}/status",
                "method": "POST",
                "body": {
                    "status": "active",
                    "note": "Advanced from the command center home action rail.",
                },
                "route": "/mission-board",
                "route_label": "Open Mission Board",
            }
        )
    else:
        actions.append(
            {
                "label": "Open Mission Board",
                "route": "/mission-board",
                "detail": str(next_mission.get("next_step", "")).strip() or "Review the next visible mission lane.",
            }
        )

    actions.extend(
        [
            {
                "label": "Open Daily Brief",
                "route": "/briefing-center",
                "detail": str(brief_preview.get("headline", "")).strip() or "Open the day briefing surface.",
            },
            {
                "label": "Open Activity Feed",
                "route": "/activity-center",
                "detail": str(recent_signal.get("title", "")).strip() or "Inspect the latest recent activity signal.",
            },
        ]
    )

    action_result = {
        "label": "Next Likely Change",
        "status_class": system_class,
        "summary": str(top_need.get("title", "")).strip() or "No immediate home action is queued.",
        "detail": (
            str(top_need.get("detail", "")).strip()
            or str(next_mission.get("next_step", "")).strip()
            or system_summary
        ),
        "route": str(top_need.get("route", "")).strip() or "/command-center",
        "route_label": str(top_need.get("route_label", "")).strip() or "Open Top Need",
        "activity_bridge": {
            "entry_type": "home-action-preview",
            "title": str(top_need.get("title", "")).strip() or "Home action preview",
            "detail": (
                str(top_need.get("detail", "")).strip()
                or str(next_mission.get("next_step", "")).strip()
                or system_summary
            ),
            "result": system_label.lower(),
            "result_summary": "Home action preview seeded from the current top-need posture.",
        },
    }

    return {
        "day_label": generated_at.split("T", 1)[0] if generated_at else "",
        "headline": str(brief_preview.get("headline", "")).strip() or "JARVIS home overview is live.",
        "summary": str(brief_preview.get("briefing_text", "")).strip() or "No home summary is available yet.",
        "priority_count": int(needs_cockpit.get("total", 0) or 0),
        "active_agent_count": int(agent_counts.get("running", 0) or 0),
        "open_mission_count": open_mission_count,
        "recent_activity_count": len(activity_feed[:8]),
        "useful_module_count": int(progress_counts.get("useful", 0) or 0),
        "hosted_url": str(hosted_deployment.get("hosted_url", "")).strip() or "https://jarvis.teambinion.org",
        "hosted_summary": str(hosted_deployment.get("summary", "")).strip() or "Hosted edge posture not captured yet.",
        "top_need": {
            "title": str(top_need.get("title", "")).strip() or "Nothing urgent right now.",
            "detail": str(top_need.get("detail", "")).strip() or "No active need is currently surfaced.",
            "route": str(top_need.get("route", "")).strip() or "/command-center",
        },
        "next_mission": {
            "title": str(next_mission.get("title", "")).strip() or "No mission is currently prioritized.",
            "detail": str(next_mission.get("next_step", "")).strip() or str(next_mission.get("brief", "")).strip() or "No mission detail captured yet.",
            "route": "/mission-board",
        },
        "active_agent": {
            "title": str(active_agent.get("name", "")).strip() or "No visible agent activity.",
            "detail": " / ".join(
                part
                for part in [
                    str(active_agent.get("assignment", "")).strip(),
                    str(active_agent.get("status", "")).strip(),
                    str(active_agent.get("last_activity", "")).strip(),
                ]
                if part
            ) or "No current agent posture detail captured.",
            "route": "/agent-ops-center",
        },
        "system_state": {
            "label": system_label,
            "status_class": system_class,
            "detail": system_summary,
            "route": "/recovery-center" if (integration_issue_count or pending_approval_count) else "/progress-center",
        },
        "actions": actions,
        "action_result": action_result,
    }


def _core_modules(
    lane_progress: dict[str, Any],
    brief_preview: dict[str, Any],
    mission_task_board: dict[str, Any],
    agent_ops_roster: dict[str, Any],
    seam_tracker: dict[str, Any],
) -> dict[str, Any]:
    def status_meta(status: str) -> tuple[str, str]:
        normalized = str(status or "").strip()
        mapping = {
            "Idea": ("idea", "steady"),
            "Mocked": ("mocked", "steady"),
            "Stubbed": ("stubbed", "artifact"),
            "Wired": ("wired", "artifact"),
            "Useful": ("useful", "accepted"),
            "Durable": ("durable", "accepted"),
            "Compounding": ("compounding", "accepted"),
        }
        return mapping.get(normalized, (normalized.lower() or "wired", "steady"))

    recent_commits = list(lane_progress.get("recent_commits") or [])
    latest_commit = recent_commits[0] if recent_commits else "No recent module seam commit recorded yet."
    items = [
        {
            "module_id": "daily-brief",
            "title": "Daily Brief",
            "status": "Useful",
            "screen_path": "/briefing-center",
            "screen_label": "Open Daily Brief Center",
            "screen_kind": "dedicated route",
            "api_path": "/api/briefing/module",
            "api_label": "Daily Brief Module API",
            "roadmap_level": "Level 3",
            "summary": "Daily Brief now has a dedicated app module route with live briefing text, today-board posture, and open-loop follow-through actions.",
            "what_became_real": "Daily Brief is now a standalone app module instead of only a shell packet and preview panel.",
            "remains_partial": "Deeper briefing-specific action loops, richer continuity capture, and broader module drill-ins still need follow-on slices.",
            "evidence": "Dedicated /briefing-center route now sits on top of live briefing, today-board, and open-loop APIs.",
        },
        {
            "module_id": "chronicle",
            "title": "Chronicle",
            "status": "Useful",
            "screen_path": "/chronicle-center",
            "screen_label": "Open Chronicle Center",
            "screen_kind": "dedicated route",
            "api_path": "/api/chronicle/module",
            "api_label": "Chronicle Status API",
            "roadmap_level": "Level 3",
            "summary": "Chronicle now has a dedicated app module route with live devotional, capture, continuity, and bridge posture.",
            "what_became_real": "Chronicle is now a standalone app module instead of a shell-only packet.",
            "remains_partial": "Richer study surfaces and broader external handoff continuity still need follow-on slices.",
            "evidence": "Dedicated /chronicle-center route now sits on top of live devotional, capture, timeline, and Chronicle bridge APIs.",
        },
        {
            "module_id": "huddle",
            "title": "Huddle",
            "status": "Useful",
            "screen_path": "/huddle-center",
            "screen_label": "Open Huddle Center",
            "screen_kind": "dedicated route",
            "api_path": "/api/huddle/module",
            "api_label": "Huddle API",
            "roadmap_level": "Level 3",
            "summary": "Huddle now has a dedicated app module route with live standups, runtime posture, dossiers, and idea capture.",
            "what_became_real": "Huddle is now a standalone app module instead of a shell-only mission-control path.",
            "remains_partial": "Broader decision workflows and richer cross-route continuity review still need follow-on slices.",
            "evidence": "Dedicated /huddle-center route now sits on top of live huddle, party-mode, dossiers, and idea APIs.",
        },
        {
            "module_id": "health",
            "title": "Health",
            "status": "Useful",
            "screen_path": "/health-center",
            "screen_label": "Open Health Center",
            "screen_kind": "dedicated route",
            "api_path": "/api/health/module",
            "api_label": "Health Drift API",
            "roadmap_level": "Level 3",
            "summary": "Health now has a dedicated app module route with live drift, baseline, objective, and triage posture.",
            "what_became_real": "Health is now a standalone app module instead of a storyboard-only surface.",
            "remains_partial": "Richer health workflows and deeper longitudinal review still need follow-on slices.",
            "evidence": "Dedicated /health-center route now sits on top of live health APIs.",
        },
        {
            "module_id": "navigation",
            "title": "Navigation",
            "status": "Useful",
            "screen_path": "/navigation-center",
            "screen_label": "Open Navigation Center",
            "screen_kind": "dedicated route",
            "api_path": "/api/navigation/module",
            "api_label": "Navigation Module API",
            "roadmap_level": "Level 3",
            "summary": "Navigation now has a dedicated app module route with persisted route state and live route-preview intelligence.",
            "what_became_real": "Navigation is now a standalone app module instead of only the shared shell surface.",
            "remains_partial": "Cross-surface continuity and stronger route auditability still need follow-on slices.",
            "evidence": "Dedicated /navigation-center route now sits on top of persisted navigation state and live route-preview APIs.",
        },
        {
            "module_id": "publish",
            "title": "Publish",
            "status": "Useful",
            "screen_path": "/publish",
            "screen_label": "Open Publish Module",
            "screen_kind": "dedicated route",
            "api_path": "/api/publish/module",
            "api_label": "Publishing Status API",
            "roadmap_level": "Level 3",
            "summary": "Publishing now has a dedicated module route with launch, project, calendar, social, and revenue posture inside the JARVIS app shell.",
            "what_became_real": "Publish is now a standalone app module route instead of a backend-only or shared-workspace seam.",
            "remains_partial": "Cross-launch continuity, broader publishing workflows, and deeper drill-ins still need follow-on slices.",
            "evidence": "Dedicated /publish route now sits on top of live publishing APIs.",
        },
        {
            "module_id": "catalyst",
            "title": "Catalyst",
            "status": "Useful",
            "screen_path": "/catalyst/view/home",
            "screen_label": "Open Catalyst Workspace",
            "screen_kind": "workspace route",
            "api_path": "/api/catalyst-overview",
            "api_label": "Catalyst Overview API",
            "roadmap_level": "Level 3",
            "summary": "Catalyst already has route-backed workspace pages and live overview data inside the JARVIS shell family.",
            "what_became_real": "Catalyst is now a real navigable workspace with page routes and live overview context.",
            "remains_partial": "Cross-workspace continuity and tighter command-center integration can still improve from here.",
            "evidence": "Catalyst workspace pages are route-backed under /catalyst/view/*.",
        },
        {
            "module_id": "settings-permissions",
            "title": "Settings & Permissions",
            "status": "Useful",
            "screen_path": "/settings-center",
            "screen_label": "Open Settings Center",
            "screen_kind": "dedicated route",
            "api_path": "/api/settings/module",
            "api_label": "Settings Module API",
            "roadmap_level": "Level 3",
            "summary": "Settings now has a dedicated app module route with live voice, location, account, and permissions posture.",
            "what_became_real": "Settings & Permissions is now a standalone app module instead of only a shell packet with scattered APIs behind it.",
            "remains_partial": "Richer family identity edits and deeper connector continuity still need follow-on slices.",
            "evidence": "Dedicated /settings-center route now sits on top of live voice, location, account, identity, and personalization APIs.",
        },
        {
            "module_id": "agent-operations",
            "title": "Agent Operations",
            "status": "Useful",
            "screen_path": "/agent-ops-center",
            "screen_label": "Open Agent Ops Center",
            "screen_kind": "dedicated route",
            "api_path": "/api/agent-ops/module",
            "api_label": "Agent Ops Module API",
            "roadmap_level": "Level 3",
            "summary": "Agent operations now has a dedicated module route with live roster posture, runtime summary, and queue-run controls.",
            "what_became_real": "Agent operations is now represented as a standalone app module instead of only command-center and hierarchy/workspace surfaces.",
            "remains_partial": "Richer assignment mutation, deeper per-agent review workflows, and broader ops continuity still need follow-on slices.",
            "evidence": "Dedicated /agent-ops-center route now sits on top of live roster, scheduler, registry, and runtime APIs.",
        },
        {
            "module_id": "failure-recovery",
            "title": "Failure & Recovery",
            "status": "Useful",
            "screen_path": "/recovery-center",
            "screen_label": "Open Recovery Center",
            "screen_kind": "dedicated route",
            "api_path": "/api/recovery/module",
            "api_label": "Recovery Module API",
            "roadmap_level": "Level 3",
            "summary": "Failure & Recovery now has a dedicated module route with live recovery posture, recent failure signals, and approval-gated recovery actions.",
            "what_became_real": "Failure & Recovery is now represented as a standalone app module instead of only command-center and progress-dashboard summaries.",
            "remains_partial": "Broader self-healing depth, richer recovery planning, and broader cross-module recovery continuity still need follow-on slices.",
            "evidence": "Dedicated /recovery-center route now sits on top of live supervision, approval queue, activity, and failure-recovery data.",
        },
        {
            "module_id": "progress",
            "title": "Progress",
            "status": "Useful",
            "screen_path": "/progress-center",
            "screen_label": "Open Progress Center",
            "screen_kind": "dedicated route",
            "api_path": "/api/progress/module",
            "api_label": "Progress Module API",
            "roadmap_level": "Level 3",
            "summary": "Progress now has a dedicated module route with live readiness rows, seam posture, lane state, and failure evidence.",
            "what_became_real": "Progress is now represented as a standalone app module instead of only a command-center panel.",
            "remains_partial": "Richer route-to-route progress actions, deeper per-module mutation flows, and broader persistence still need follow-on slices.",
            "evidence": "Dedicated /progress-center route now sits on top of live progress dashboard, seam tracker, lane posture, and failure-recovery data.",
        },
    ]
    counts = {
        "Idea": sum(1 for item in items if item["status"] == "Idea"),
        "Mocked": sum(1 for item in items if item["status"] == "Mocked"),
        "Stubbed": sum(1 for item in items if item["status"] == "Stubbed"),
        "Wired": sum(1 for item in items if item["status"] == "Wired"),
        "Useful": sum(1 for item in items if item["status"] == "Useful"),
        "Durable": sum(1 for item in items if item["status"] == "Durable"),
        "Compounding": sum(1 for item in items if item["status"] == "Compounding"),
    }
    enriched_items = []
    for item in items:
        status_label, status_class = status_meta(item["status"])
        enriched = dict(item)
        enriched["status_label"] = status_label
        enriched["status_class"] = status_class
        enriched_items.append(enriched)
    return {
        "summary": f"{counts['Useful']} useful, {counts['Wired']} wired, {counts['Stubbed']} stubbed core module(s) across the visible Level 3 app base.",
        "item_count": len(enriched_items),
        "counts": counts,
        "items": enriched_items,
    }


def _seam_tracker(
    lane_progress: dict[str, Any],
    registry: dict[str, Any],
    surfaces: list[dict[str, Any]],
    mission_task_board: dict[str, Any],
) -> dict[str, Any]:
    branch = str(lane_progress.get("branch", "") or "").strip() or "unknown branch"
    head = str(lane_progress.get("head", "") or "").strip() or "unknown head"
    dirty_count = int(lane_progress.get("dirty_count", 0) or 0)
    recent_commits = [str(item).strip() for item in list(lane_progress.get("recent_commits") or []) if str(item).strip()]
    surface_paths = [str(item.get("path", "") or "").strip() for item in surfaces if str(item.get("path", "") or "").strip()]
    primary_surface = surface_paths[0] if surface_paths else "/command-center"
    commit_posture = "clean head" if dirty_count == 0 else f"{dirty_count} local changes still need reconciliation"
    agent_count = int(registry.get("agent_count", 0) or 0)
    domain_count = len([item for item in list(registry.get("domains") or []) if str(item).strip()])
    mission_items = [item for item in list(mission_task_board.get("items") or []) if isinstance(item, dict)]

    def related_missions_for(module: str) -> list[dict[str, Any]]:
        module_key = str(module or "").strip().lower()
        results: list[dict[str, Any]] = []
        for mission in mission_items:
            lane = str(mission.get("lane", "")).strip().lower()
            if lane == "completed":
                continue
            domain = str(mission.get("primary_domain", "")).strip().lower()
            title = str(mission.get("title", "")).strip()
            if not title:
                continue
            matched = False
            if module_key in {"mission board", "activity feed", "agent operations", "progress", "failure & recovery", "command center/home"}:
                matched = True
            elif module_key == "publish" and domain in {"communications", "content"}:
                matched = True
            elif module_key == "chronicle" and domain in {"formation"}:
                matched = True
            elif module_key == "navigation" and domain in {"weather", "travel"}:
                matched = True
            elif module_key == "health" and domain in {"health", "family"}:
                matched = True
            elif module_key == "daily brief" and domain in {"general", "family"}:
                matched = True
            if matched:
                results.append(
                    {
                        "mission_id": str(mission.get("mission_id", "")).strip(),
                        "title": title,
                        "lane": str(mission.get("lane", "")).strip() or "next",
                        "route": "/mission-board",
                    }
                )
            if len(results) >= 3:
                break
        return results

    seams = [
        {
            "name": "Command Center Working Base",
            "status": "Useful",
            "status_class": "accepted",
            "roadmap_areas": ["Level 3", "Command Center/Home"],
            "module": "Command Center/Home",
            "maturity": "Useful",
            "substrate": [
                "supervision snapshot",
                "approval snapshot",
                "activity feed",
                "detail inspector",
            ],
            "branch": branch,
            "worktree": "primary worktree",
            "surface_path": primary_surface,
            "what_became_real": "The app now exposes a single command-center route with live needs, memory, daily brief, activity, registry, progress, and inspectable detail state.",
            "remains_partial": "Mission board, module drill-ins, and persistent seam storage still need dedicated Level 3 routes.",
            "related_missions": related_missions_for("Command Center/Home"),
            "tests": [
                "tests/test_command_center_index.py",
                "tests/test_command_center_service_surface.py",
            ],
            "commit_status": recent_commits[0] if recent_commits else commit_posture,
        },
        {
            "name": "Agent Roster Operations Surface",
            "status": "Wired",
            "status_class": "steady",
            "roadmap_areas": ["Level 3", "Agent Roster/Ops"],
            "module": "Agent Operations",
            "maturity": "Wired",
            "substrate": [
                "agent registry contract",
                "authority stages",
                "command-center registry panel",
            ],
            "branch": branch,
            "worktree": "primary worktree",
            "surface_path": "/command-center",
            "what_became_real": f"The command center now surfaces {agent_count} registered agent contracts across {domain_count} domain lane(s) with live maturity, authority, and seeded task-agent metadata.",
            "remains_partial": "Command-center roster continuity still needs deeper last-activity drill-ins and stronger mission-linked assignment context.",
            "related_missions": related_missions_for("Agent Operations"),
            "tests": [
                "tests/test_command_center_index.py",
            ],
            "commit_status": commit_posture,
        },
        {
            "name": "Agent Operations Module Standalone Surface",
            "status": "Useful",
            "status_class": "accepted",
            "roadmap_areas": ["Level 3", "Agent Roster/Ops", "Core Modules"],
            "module": "Agent Operations",
            "maturity": "Useful",
            "substrate": [
                "agent roster contract",
                "runtime posture",
                "scheduler status",
                "queue-run control",
            ],
            "branch": branch,
            "worktree": "primary worktree",
            "surface_path": "/agent-ops-center",
            "what_became_real": "Agent operations now has a dedicated route with live core and task-agent roster posture, selected-agent detail, mission-linked assignment editing, per-agent outcome review, queue-run controls, and task-agent promotion or retirement controls inside the app shell.",
            "remains_partial": "Broader route-to-route ops continuity still needs follow-on slices.",
            "related_missions": related_missions_for("Agent Operations"),
            "tests": [
                "tests/test_command_center_index.py",
                "tests/test_command_center_service_surface.py",
            ],
            "commit_status": recent_commits[0] if recent_commits else commit_posture,
        },
        {
            "name": "Supervision Snapshot Standalone Surface",
            "status": "Useful",
            "status_class": "accepted",
            "roadmap_areas": ["Level 3", "Supervision Snapshot"],
            "module": "Supervision Snapshot",
            "maturity": "Useful",
            "substrate": [
                "git lane posture",
                "approval attention model",
                "integration status model",
                "memory review cues",
            ],
            "branch": branch,
            "worktree": "primary worktree",
            "surface_path": "/supervision-snapshot",
            "what_became_real": "The supervision snapshot now uses the newer app-module surface family with live lane posture, attention detail, and direct continuity actions inside the app shell.",
            "remains_partial": "Deeper supervision mutation, broader lane recovery controls, and richer linked-module continuity still need follow-on slices.",
            "tests": [
                "tests/test_command_center_index.py",
                "tests/test_command_center_service_surface.py",
            ],
            "commit_status": recent_commits[0] if recent_commits else commit_posture,
        },
        {
            "name": "Approval Queue Standalone Surface",
            "status": "Useful",
            "status_class": "accepted",
            "roadmap_areas": ["Level 3", "Approval Queue"],
            "module": "Approval Queue",
            "maturity": "Useful",
            "substrate": [
                "approval queue",
                "decision history model",
                "trust zone metadata",
                "approval action controls",
            ],
            "branch": branch,
            "worktree": "primary worktree",
            "surface_path": "/approval-queue",
            "what_became_real": "The approval queue now uses the newer app-module surface family with live request detail, decision history, and direct review actions inside the app shell.",
            "remains_partial": "Broader approval authoring flows, deeper trust-zone drill-ins, and richer linked-module continuity still need follow-on slices.",
            "tests": [
                "tests/test_command_center_index.py",
                "tests/test_command_center_service_surface.py",
            ],
            "commit_status": recent_commits[0] if recent_commits else commit_posture,
        },
        {
            "name": "Failure Recovery Module Standalone Surface",
            "status": "Useful",
            "status_class": "accepted",
            "roadmap_areas": ["Level 3", "Failure & Recovery", "Core Modules"],
            "module": "Failure & Recovery",
            "maturity": "Useful",
            "substrate": [
                "supervision snapshot",
                "approval queue",
                "activity feed",
                "recovery action model",
            ],
            "branch": branch,
            "worktree": "primary worktree",
            "surface_path": "/recovery-center",
            "what_became_real": "Failure and recovery now has a dedicated route with recovery detail, pending approval gates, direct recovery-gate approval and execution actions, a durable retry, stabilization, and auto-remediation journal, and visible continuity into Approval Queue, Supervision Snapshot, Activity Feed, Progress, and Command Center.",
            "remains_partial": "Broader self-healing depth and deeper non-approval execution planning still need follow-on slices.",
            "tests": [
                "tests/test_command_center_index.py",
                "tests/test_command_center_service_surface.py",
            ],
            "commit_status": recent_commits[0] if recent_commits else commit_posture,
        },
        {
            "name": "Mission Task Board Standalone Surface",
            "status": "Useful",
            "status_class": "accepted",
            "roadmap_areas": ["Level 3", "Mission/Task Board"],
            "module": "Mission Board",
            "maturity": "Useful",
            "substrate": [
                "mission dossier store",
                "task agent store",
                "mission lane model",
                "mission status mutation",
            ],
            "branch": branch,
            "worktree": "primary worktree",
            "surface_path": "/mission-board",
            "what_became_real": "The mission board now has a dedicated route with lane-based mission visibility, selected mission detail, mission authoring, mission editing, mission workspace review, handoff authoring, seam linkage, and per-agent work-state controls inside the app shell.",
            "remains_partial": "Mission edit flows and seam linkage are now real at the first pass, but they still need deeper breadth and richer linkage coverage in later slices.",
            "related_missions": related_missions_for("Mission Board"),
            "tests": [
                "tests/test_command_center_index.py",
                "tests/test_command_center_service_surface.py",
            ],
            "commit_status": recent_commits[0] if recent_commits else commit_posture,
        },
        {
            "name": "Activity Feed Standalone Surface",
            "status": "Useful",
            "status_class": "accepted",
            "roadmap_areas": ["Level 3", "Activity Feed"],
            "module": "Activity Feed",
            "maturity": "Useful",
            "substrate": [
                "audit log",
                "activity event model",
                "action journal",
                "related route inference",
            ],
            "branch": branch,
            "worktree": "primary worktree",
            "surface_path": "/activity-center",
            "what_became_real": "The activity stream now has a dedicated route with event drill-ins, journal context, and direct jumps into related app surfaces.",
            "remains_partial": "Richer audit filters, broader event mutation, and deeper cross-surface continuity still need follow-on slices.",
            "related_missions": related_missions_for("Activity Feed"),
            "tests": [
                "tests/test_command_center_index.py",
                "tests/test_command_center_service_surface.py",
            ],
            "commit_status": recent_commits[0] if recent_commits else commit_posture,
        },
        {
            "name": "Seam Tracker Control Surface",
            "status": "Wired",
            "status_class": "steady",
            "roadmap_areas": ["Level 3", "Progress Dashboard", "Seam Tracker"],
            "module": "Progress",
            "maturity": "Wired",
            "substrate": [
                "lane progress snapshot",
                "branch/head posture",
                "recent seam commits",
            ],
            "branch": branch,
            "worktree": "primary worktree",
            "surface_path": "/command-center",
            "what_became_real": "Structured seam records are now inspectable inside the command center with branch, worktree, maturity, tests, and commit posture in one place.",
            "remains_partial": "Seam entries are still branch-scoped local records; durable persistence and mission linkage come in a later Level 3 slice.",
            "related_missions": related_missions_for("Progress"),
            "tests": [
                "tests/test_command_center_index.py",
                "tests/test_command_center_service_surface.py",
            ],
            "commit_status": commit_posture,
        },
        {
            "name": "Progress Module Standalone Surface",
            "status": "Useful",
            "status_class": "accepted",
            "roadmap_areas": ["Level 3", "Progress", "Core Modules"],
            "module": "Progress",
            "maturity": "Useful",
            "substrate": [
                "progress dashboard model",
                "seam tracker snapshot",
                "lane and failure posture",
            ],
            "branch": branch,
            "worktree": "primary worktree",
            "surface_path": "/progress-center",
            "what_became_real": "Progress now has its own dedicated route and module payload, instead of relying only on the command-center panel.",
            "remains_partial": "The progress module still needs richer route-to-route actions, deeper per-module mutation flows, and broader persistence.",
            "related_missions": related_missions_for("Progress"),
            "tests": [
                "tests/test_command_center_service_surface.py",
            ],
            "commit_status": recent_commits[0] if recent_commits else commit_posture,
        },
        {
            "name": "Daily Brief Module Standalone Surface",
            "status": "Useful",
            "status_class": "accepted",
            "roadmap_areas": ["Level 3", "Daily Brief", "Core Modules"],
            "module": "Daily Brief",
            "maturity": "Useful",
            "substrate": [
                "briefing text payload",
                "today board model",
                "open-loop action flow",
            ],
            "branch": branch,
            "worktree": "primary worktree",
            "surface_path": "/briefing-center",
            "what_became_real": "Daily Brief now has its own dedicated route and module payload, instead of relying only on the shell packet and command-center preview.",
            "remains_partial": "The daily brief module still needs deeper briefing workflows, broader continuity capture, and richer drill-ins beyond the current open-loop action flow.",
            "tests": [
                "tests/test_command_center_service_surface.py",
            ],
            "commit_status": recent_commits[0] if recent_commits else commit_posture,
        },
        {
            "name": "Navigation Module Standalone Surface",
            "status": "Useful",
            "status_class": "accepted",
            "roadmap_areas": ["Level 3", "Navigation", "Core Modules"],
            "module": "Navigation",
            "maturity": "Useful",
            "substrate": [
                "navigation state model",
                "route preview intelligence",
                "dedicated navigation route",
            ],
            "branch": branch,
            "worktree": "primary worktree",
            "surface_path": "/navigation-center",
            "what_became_real": "Navigation now has its own dedicated route and module payload, instead of relying only on the shared shell and Apple-side route APIs.",
            "remains_partial": "The navigation module still needs richer continuity, stronger route audit trails, and broader cross-surface resume behavior.",
            "tests": [
                "tests/test_command_center_service_surface.py",
            ],
            "commit_status": recent_commits[0] if recent_commits else commit_posture,
        },
        {
            "name": "Core Modules Command Surface",
            "status": "Wired",
            "status_class": "steady",
            "roadmap_areas": ["Level 3", "Core Modules", "Navigation"],
            "module": "Core Modules",
            "maturity": "Wired",
            "substrate": [
                "module registry",
                "screen/api proof paths",
                "status and maturity mapping",
            ],
            "branch": branch,
            "worktree": "primary worktree",
            "surface_path": "/command-center",
            "what_became_real": "The command center now exposes a structured Core Modules surface with direct screen paths, API proof paths, readiness states, and inspectable module detail.",
            "remains_partial": "Several modules still share shell packets or workspace routes instead of having dedicated standalone screens.",
            "tests": [
                "tests/test_command_center_index.py",
                "tests/test_command_center_service_surface.py",
            ],
            "commit_status": commit_posture,
        },
        {
            "name": "Publish Module Standalone Surface",
            "status": "Useful",
            "status_class": "accepted",
            "roadmap_areas": ["Level 3", "Publish", "Core Modules"],
            "module": "Publish",
            "maturity": "Useful",
            "substrate": [
                "publishing status model",
                "launch control payload",
                "dedicated publish route",
            ],
            "branch": branch,
            "worktree": "primary worktree",
            "surface_path": "/publish",
            "what_became_real": "Publish now has its own dedicated route and module payload, instead of relying on shared workspace navigation or backend-only APIs.",
            "remains_partial": "The publishing module still needs deeper review workflows, richer history, and broader launch orchestration.",
            "tests": [
                "tests/test_command_center_service_surface.py",
            ],
            "commit_status": recent_commits[0] if recent_commits else commit_posture,
        },
        {
            "name": "Chronicle Module Standalone Surface",
            "status": "Useful",
            "status_class": "accepted",
            "roadmap_areas": ["Level 3", "Chronicle", "Core Modules"],
            "module": "Chronicle",
            "maturity": "Useful",
            "substrate": [
                "chronicle status model",
                "continuity and timeline payload",
                "dedicated chronicle route",
            ],
            "branch": branch,
            "worktree": "primary worktree",
            "surface_path": "/chronicle-center",
            "what_became_real": "Chronicle now has its own dedicated route and module payload, instead of hiding behind the shell chronicle packet.",
            "remains_partial": "The Chronicle module still needs richer study workflows and deeper handoff continuity beyond devotional, capture, timeline, and review posture.",
            "tests": [
                "tests/test_command_center_service_surface.py",
            ],
            "commit_status": recent_commits[0] if recent_commits else commit_posture,
        },
        {
            "name": "Huddle Module Standalone Surface",
            "status": "Useful",
            "status_class": "accepted",
            "roadmap_areas": ["Level 3", "Huddle", "Core Modules"],
            "module": "Huddle",
            "maturity": "Useful",
            "substrate": [
                "huddle status model",
                "standup and runtime payload",
                "dedicated huddle route",
            ],
            "branch": branch,
            "worktree": "primary worktree",
            "surface_path": "/huddle-center",
            "what_became_real": "Huddle now has its own dedicated route and module payload, instead of hiding behind the shell mission-control packet.",
            "remains_partial": "The huddle module still needs richer review workflows and deeper continuity actions beyond standups, dossiers, and idea capture.",
            "tests": [
                "tests/test_command_center_service_surface.py",
            ],
            "commit_status": recent_commits[0] if recent_commits else commit_posture,
        },
        {
            "name": "Settings Module Standalone Surface",
            "status": "Useful",
            "status_class": "accepted",
            "roadmap_areas": ["Level 3", "Settings", "Permissions", "Core Modules"],
            "module": "Settings & Permissions",
            "maturity": "Useful",
            "substrate": [
                "voice settings store",
                "location settings store",
                "account and permissions payload",
            ],
            "branch": branch,
            "worktree": "primary worktree",
            "surface_path": "/settings-center",
            "what_became_real": "Settings & Permissions now has its own dedicated route and module payload, instead of relying only on the shell packet and scattered APIs.",
            "remains_partial": "The settings module still needs richer identity workflows and deeper connector continuity.",
            "tests": [
                "tests/test_command_center_service_surface.py",
            ],
            "commit_status": recent_commits[0] if recent_commits else commit_posture,
        },
        {
            "name": "Health Module Standalone Surface",
            "status": "Useful",
            "status_class": "accepted",
            "roadmap_areas": ["Level 3", "Health", "Core Modules"],
            "module": "Health",
            "maturity": "Useful",
            "substrate": [
                "health status model",
                "drift and objectives payload",
                "dedicated health route",
            ],
            "branch": branch,
            "worktree": "primary worktree",
            "surface_path": "/health-center",
            "what_became_real": "Health now has its own dedicated route and module payload, instead of relying on a storyboard-backed desktop mockup.",
            "remains_partial": "The health module still needs broader longitudinal workflows and deeper action loops beyond triage and drift posture.",
            "tests": [
                "tests/test_command_center_service_surface.py",
            ],
            "commit_status": recent_commits[0] if recent_commits else commit_posture,
        },
    ]
    seam_summary = SeamTrackerStore(DEFAULT_AUDIT_ROOT).summary(limit=6)
    persisted_by_name = {
        str(item.get("name", "")).strip(): dict(item)
        for item in list(seam_summary.get("records") or [])
        if isinstance(item, dict) and str(item.get("name", "")).strip()
    }
    for item in seams:
        persisted = persisted_by_name.get(str(item.get("name", "")).strip())
        if not persisted:
            continue
        item["status"] = str(persisted.get("status") or item.get("status") or "Wired").strip() or "Wired"
        item["status_class"] = str(persisted.get("status_class") or item.get("status_class") or "steady").strip() or "steady"
        item["maturity"] = str(persisted.get("maturity") or item.get("maturity") or item.get("status") or "Wired").strip() or "Wired"
        operator_note = str(persisted.get("operator_note") or "").strip()
        if operator_note:
            item["operator_note"] = operator_note
        linked_mission = dict(persisted.get("linked_mission") or {})
        if str(linked_mission.get("mission_id", "")).strip():
            existing_ids = {
                str(mission.get("mission_id", "")).strip()
                for mission in list(item.get("related_missions") or [])
                if isinstance(mission, dict)
            }
            if str(linked_mission.get("mission_id", "")).strip() not in existing_ids:
                item["related_missions"] = [linked_mission, *list(item.get("related_missions") or [])][:3]
        item["seam_state_saved_at"] = str(persisted.get("saved_at", "")).strip()
        item["seam_state_actor"] = str(persisted.get("actor", "")).strip()

    counts = {
        "Useful": sum(1 for item in seams if item["status"] == "Useful"),
        "Wired": sum(1 for item in seams if item["status"] == "Wired"),
        "Durable": sum(1 for item in seams if item["status"] == "Durable"),
        "Compounding": sum(1 for item in seams if item["status"] == "Compounding"),
    }
    return {
        "summary": f"{counts['Useful']} useful seam(s), {counts['Wired']} wired seam(s), {counts['Durable']} durable seam(s), branch {branch}, head {head}.",
        "item_count": len(seams),
        "counts": counts,
        "items": seams,
        "persistence": seam_summary,
    }


def build_command_center_index() -> dict[str, Any]:
    approval_snapshot = build_approval_queue_snapshot()
    supervision_snapshot = build_supervision_snapshot()
    lane = dict(supervision_snapshot.get("lane") or {})
    return_brief = dict(supervision_snapshot.get("return_brief") or {})
    what_needs_me = list(supervision_snapshot.get("what_needs_me") or [])[:6]
    pending_approvals = list(approval_snapshot.get("pending") or [])[:6]
    memory = dict(supervision_snapshot.get("memory") or {})
    activity_feed = _activity_items()
    registry = _registry_status()
    failure_recovery = _failure_recovery(
        supervision_snapshot=supervision_snapshot,
        approval_snapshot=approval_snapshot,
        activity_feed=activity_feed,
    )
    brief_preview = _brief_preview(
        supervision_snapshot=supervision_snapshot,
        activity_feed=activity_feed,
    )
    timeline_preview = _timeline_preview(
        approval_snapshot=approval_snapshot,
        supervision_snapshot=supervision_snapshot,
        activity_feed=activity_feed,
    )
    open_loop_inspector = _open_loop_inspector(
        approval_snapshot=approval_snapshot,
        supervision_snapshot=supervision_snapshot,
        activity_feed=activity_feed,
    )
    notification_preview = _notification_preview(
        supervision_snapshot=supervision_snapshot,
        approval_snapshot=approval_snapshot,
        activity_feed=activity_feed,
    )
    needs_cockpit = _needs_me_cockpit(
        supervision_snapshot=supervision_snapshot,
        approval_snapshot=approval_snapshot,
        open_loop_inspector=open_loop_inspector,
        notification_preview=notification_preview,
        failure_recovery=failure_recovery,
    )
    needs_motion = _needs_motion(
        needs_cockpit=needs_cockpit,
        activity_feed=activity_feed,
    )
    action_journal = _action_journal(
        approval_snapshot=approval_snapshot,
        activity_feed=activity_feed,
    )
    mission_task_board = _mission_task_board()
    agent_ops_roster = _agent_ops_roster()
    detail_inspector = _detail_inspector(
        approval_snapshot=approval_snapshot,
        open_loop_inspector=open_loop_inspector,
        notification_preview=notification_preview,
        activity_feed=activity_feed,
    )

    surfaces = [
        {
            "title": "Approval Queue",
            "path": "/approval-queue",
            "api": "/api/approval/module",
            "kind": "final product functionality",
            "summary": f"{approval_snapshot.get('pending_count', 0)} pending approvals, {approval_snapshot.get('history_count', 0)} recent decisions.",
        },
        {
            "title": "Supervision Snapshot",
            "path": "/supervision-snapshot",
            "api": "/api/supervision/module",
            "kind": "final product functionality",
            "summary": str((supervision_snapshot.get("return_brief") or {}).get("summary", "")),
        },
        {
            "title": "Health Desktop",
            "path": "/health-desktop",
            "api": "/api/status",
            "kind": "temporary demo or proof surface",
            "summary": "Served health storyboard route backed by the current local app shell.",
        },
        {
            "title": "Implementation Outline",
            "path": "/implementation-outline",
            "api": "/api/open-loops",
            "kind": "temporary demo or proof surface",
            "summary": "Roadmap and implementation checklist surface for the current lane.",
        },
        {
            "title": "Mission API",
            "path": "/api/missions",
            "api": "/api/missions",
            "kind": "final product functionality",
            "summary": mission_task_board["summary"],
        },
        {
            "title": "Mission Board",
            "path": "/mission-board",
            "api": "/api/mission-board/module",
            "kind": "final product functionality",
            "summary": mission_task_board["summary"],
        },
        {
            "title": "Activity Feed",
            "path": "/activity-center",
            "api": "/api/activity/module",
            "kind": "final product functionality",
            "summary": f"{len(activity_feed)} recent activity event(s) and {int(action_journal.get('count', 0) or 0)} action journal item(s).",
        },
    ]
    seam_tracker = _seam_tracker(
        lane_progress={
            "branch": str(lane.get("branch", "")),
            "head": str(lane.get("head", "")),
            "dirty_count": int(lane.get("dirty_count", 0) or 0),
            "recent_commits": list(lane.get("recent_commits") or []),
        },
        registry=registry,
        surfaces=surfaces,
        mission_task_board=mission_task_board,
    )
    core_modules = _core_modules(
        lane_progress={
            "return_brief_summary": str(return_brief.get("summary", "")),
            "recent_commits": list(lane.get("recent_commits") or []),
        },
        brief_preview=brief_preview,
        mission_task_board=mission_task_board,
        agent_ops_roster=agent_ops_roster,
        seam_tracker=seam_tracker,
    )
    progress_dashboard = _progress_dashboard(
        lane_progress={
            "branch": str(lane.get("branch", "")),
            "head": str(lane.get("head", "")),
            "dirty_count": int(lane.get("dirty_count", 0) or 0),
            "recent_commits": list(lane.get("recent_commits") or []),
        },
        seam_tracker=seam_tracker,
        mission_task_board=mission_task_board,
        agent_ops_roster=agent_ops_roster,
        failure_recovery=failure_recovery,
    )
    level3_checklist = _level3_checklist(
        progress_dashboard=progress_dashboard,
        seam_tracker=seam_tracker,
        core_modules=core_modules,
        lane_progress={
            "branch": str(lane.get("branch", "")),
            "dirty_count": int(lane.get("dirty_count", 0) or 0),
        },
        failure_recovery=failure_recovery,
    )
    hosted_deployment = _hosted_deployment()
    home_overview = _home_overview(
        generated_at=_now_iso(),
        brief_preview=brief_preview,
        needs_cockpit=needs_cockpit,
        mission_task_board=mission_task_board,
        agent_ops_roster=agent_ops_roster,
        failure_recovery=failure_recovery,
        progress_dashboard=progress_dashboard,
        activity_feed=activity_feed,
        hosted_deployment=hosted_deployment,
    )

    json_endpoints = [
        {
            "title": "System Status",
            "path": "/api/status",
            "summary": "Connector and service health snapshot.",
        },
        {
            "title": "Pending Approvals",
            "path": "/api/approvals",
            "summary": "Runtime approval store list for active requests.",
        },
        {
            "title": "Recent Activity",
            "path": "/api/activity",
            "summary": "Recent runtime activity feed for observability.",
        },
        {
            "title": "Open Loops",
            "path": "/api/open-loops",
            "summary": "Actor-oriented open loop view.",
        },
        {
            "title": "Missions",
            "path": "/api/missions",
            "summary": "Mission/task board source for active workstreams.",
        },
        {
            "title": "Agent Registry",
            "path": "/api/agent-registry",
            "summary": "Registry contract snapshot for current agents.",
        },
        {
            "title": "Supervision Contracts",
            "path": "/api/agent-supervision/contracts",
            "summary": "Live supervision contract definitions and boundaries.",
        },
    ]

    return {
        "generated_at": _now_iso(),
        "branch": str(lane.get("branch", "")),
        "head": str(lane.get("head", "")),
        "lane_progress": {
            "branch": str(lane.get("branch", "")),
            "head": str(lane.get("head", "")),
            "dirty_count": int(lane.get("dirty_count", 0) or 0),
            "recent_commits": list(lane.get("recent_commits") or []),
            "dirty_sample": list(lane.get("dirty_sample") or []),
            "return_brief_summary": str(return_brief.get("summary", "")),
            "what_needs_me_count": int(return_brief.get("what_needs_me_count", 0) or 0),
        },
        "what_needs_me": what_needs_me,
        "needs_cockpit": needs_cockpit,
        "needs_motion": needs_motion,
        "pending_approvals": pending_approvals,
        "activity_feed": activity_feed,
        "registry": registry,
        "agent_ops_roster": agent_ops_roster,
        "core_modules": core_modules,
        "progress_dashboard": progress_dashboard,
        "seam_tracker": seam_tracker,
        "level3_checklist": level3_checklist,
        "failure_recovery": failure_recovery,
        "hosted_deployment": hosted_deployment,
        "home_overview": home_overview,
        "brief_preview": brief_preview,
        "timeline_preview": timeline_preview,
        "open_loop_inspector": open_loop_inspector,
        "action_journal": action_journal,
        "mission_task_board": mission_task_board,
        "detail_inspector": detail_inspector,
        "notification_preview": notification_preview,
        "memory": {
            "entry_count": int(memory.get("entry_count", 0) or 0),
            "proposal_count": int(memory.get("proposal_count", 0) or 0),
            "fact_count": int(memory.get("fact_count", 0) or 0),
            "latest_entry_titles": list(memory.get("latest_entry_titles") or []),
            "pending_proposals": list(memory.get("pending_proposals") or []),
        },
        "surface_count": len(surfaces),
        "surfaces": surfaces,
        "json_endpoints": json_endpoints,
        "proof_paths": {
            "approval_queue": "/approval-queue",
            "supervision_snapshot": "/supervision-snapshot",
            "health_desktop": "/health-desktop",
            "implementation_outline": "/implementation-outline",
            "supervision_snapshot_json": "/api/supervision-snapshot",
            "approval_queue_json": "/api/approval-queue/snapshot",
            "command_center_json": "/api/command-center",
            "briefing_json": "/api/briefing?actor=Chris",
            "open_loops_json": "/api/open-loops?actor=Chris",
            "missions_json": "/api/missions",
            "assistant_notifications_json": "/api/assistant-core/notifications?actor=Chris",
            "agent_registry_json": "/api/agent-registry",
            "agent_supervision_contracts_json": "/api/agent-supervision/contracts",
        },
    }


def render_command_center_index_html(payload: dict[str, Any]) -> str:
    def esc(value: Any) -> str:
        return html.escape(str(value))

    def surface_cards(items: list[dict[str, Any]]) -> str:
        return "".join(
            f"""
            <article class="surface-card">
              <div class="eyebrow">{esc(item['kind'])}</div>
              <h3>{esc(item['title'])}</h3>
              <p>{esc(item['summary'])}</p>
              <div class="link-row">
                <a href="{esc(item['path'])}">Open surface</a>
                <a href="{esc(item['api'])}">Open JSON</a>
              </div>
            </article>
            """
            for item in items
        )

    def endpoint_rows(items: list[dict[str, Any]]) -> str:
        return "".join(
            f"""
            <li>
              <strong>{esc(item['title'])}</strong>
              <span>{esc(item['summary'])}</span>
              <code>{esc(item['path'])}</code>
            </li>
            """
            for item in items
        )

    def needs_rows(cockpit: dict[str, Any]) -> str:
        items = list(cockpit.get("items") or [])
        if not items:
            return "<li class='empty'>Nothing urgent right now.</li>"
        def action_button(item: dict[str, Any]) -> str:
            primary_action = dict(item.get("primary_action") or {})
            endpoint = str(primary_action.get("endpoint", "")).strip()
            if not endpoint:
                return ""
            method = str(primary_action.get("method", "POST")).strip() or "POST"
            body = primary_action.get("body")
            body_attr = f" data-body={json.dumps(body)!r}" if body is not None else ""
            needs_key = str(item.get("need_key", "")).strip()
            key_attr = f' data-needs-key="{esc(needs_key)}"' if needs_key else ""
            label = esc(primary_action.get("label", "Act"))
            return f'<button type="button" data-endpoint="{esc(endpoint)}" data-method="{esc(method)}"{key_attr}{body_attr}>{label}</button>'
        return "".join(
            f"""
            <li class="needs-action">
              <strong>{esc(item.get('title', ''))}</strong>
              <span>{esc(item.get('detail', ''))}</span>
              <code>{esc(item.get('urgency', 'normal'))} · {esc(", ".join(item.get('sources', []) or []))}</code>
              {f"<span>{esc(item.get('row_state_summary', ''))}</span>" if str(item.get('row_state_summary', '')).strip() else ''}
              <div class="action-row">
                {action_button(item)}
                {f'<button type="button" data-needs-index="{index}">Inspect</button>' if list(item.get('focus_targets') or []) else ''}
              </div>
              <div class="link-row">
                <span>{esc(item.get('action_hint', 'Inspect this item from the command center.'))}</span>
                <a href="{esc(item.get('route', '/command-center'))}">{esc(item.get('route_label', 'Open command center'))}</a>
              </div>
            </li>
            """
            for index, item in enumerate(items)
        )

    def needs_motion_rows(needs_motion: dict[str, Any]) -> str:
        entries = list(needs_motion.get("entries") or [])
        if not entries:
            return "<li class='empty'>No recent need motion captured yet.</li>"
        summary_rows = "".join(
            [
                f"<li><strong>Total</strong><span>{esc(needs_motion.get('count', 0))} recent motion item(s)</span></li>",
                f"<li><strong>Active Queue</strong><span>{esc(needs_motion.get('active_count', 0))} live queue motion item(s)</span></li>",
                f"<li><strong>Signals</strong><span>{esc(needs_motion.get('signal_count', 0))} runtime signal item(s)</span></li>",
            ]
        )
        entry_rows = "".join(
            f"""
            <li>
              <strong>{esc(item.get('title', 'Need motion'))}</strong>
              <span>{esc(item.get('kind', 'motion'))} / {esc(item.get('status', 'observed'))}</span>
              <span>{esc(item.get('detail', 'Recent triage motion.'))}</span>
              {f"<span>Source: {esc(item.get('source_kind', ''))} / {esc(item.get('source_label', ''))}</span>" if str(item.get('source_kind', '')).strip() or str(item.get('source_label', '')).strip() else ''}
              {f"<span>Transition: {esc(item.get('transition', ''))}</span>" if str(item.get('transition', '')).strip() else ''}
              {f"<span>Queue State: {esc(item.get('queue_state', ''))}</span>" if str(item.get('queue_state', '')).strip() else ''}
              {f"<span>Evidence: {esc(item.get('evidence', ''))}</span>" if str(item.get('evidence', '')).strip() else ''}
              <div class="action-row">
                <button type="button" data-motion-index="{index}">Inspect Proof</button>
                {f'<button type="button" data-needs-key-inspect="{esc(item.get("need_key", ""))}">Inspect Need</button>' if str(item.get('need_key', '')).strip() else ''}
                {" ".join(f'<a href="{esc(link.get("href", "#"))}">{esc(link.get("label", "Open Link"))}</a>' for link in list(item.get("evidence_links") or []) if str(link.get("href", "")).strip())}
              </div>
              <code>{esc(item.get('timestamp', ''))}</code>
            </li>
            """
            for index, item in enumerate(entries)
        )
        return summary_rows + entry_rows

    def approval_rows(items: list[dict[str, Any]]) -> str:
        if not items:
            return "<li class='empty'>No pending approvals right now.</li>"
        rows = []
        for item in items:
            request_id = str(item.get("request_id", "") or "")
            actions = dict(item.get("actions") or {})
            if request_id:
                actions.setdefault("approve", f"/api/approvals/{request_id}/approve")
                actions.setdefault("reject", f"/api/approvals/{request_id}/reject")
                actions.setdefault("cancel", f"/api/approvals/{request_id}/cancel")
                actions.setdefault("execute", f"/api/approvals/{request_id}/execute")
            rows.append(
                f"""
                <li class="needs-action">
                  <strong>{esc(item.get('title', ''))}</strong>
                  <span>{esc(item.get('description', ''))}</span>
                  <code>{esc(item.get('risk_tier', ''))} · {esc(item.get('agent_label', ''))}</code>
                  <div class="action-row">
                    <button type="button" data-endpoint="{esc(actions.get('approve', ''))}" data-method="POST">Approve</button>
                    <button type="button" data-endpoint="{esc(actions.get('reject', ''))}" data-method="POST" data-body='{{"reason":"Need a safer plan first"}}'>Reject</button>
                    <button type="button" data-endpoint="{esc(actions.get('cancel', ''))}" data-method="POST">Cancel</button>
                    <button type="button" data-endpoint="{esc(actions.get('execute', ''))}" data-method="POST">Execute</button>
                  </div>
                </li>
                """
            )
        return "".join(rows)

    def memory_rows(memory: dict[str, Any]) -> str:
        latest_titles = list(memory.get("latest_entry_titles") or [])
        pending_proposals = list(memory.get("pending_proposals") or [])
        latest_display = ", ".join(str(item) for item in latest_titles if item) or "No recent memory entries."
        proposal_display = ", ".join(str(item) for item in pending_proposals if item) or "No pending memory proposals."
        return "".join(
            [
                f"<li><strong>Entries</strong><span>{esc(memory.get('entry_count', 0))} stored entries</span></li>",
                f"<li><strong>Proposals</strong><span>{esc(memory.get('proposal_count', 0))} total proposals</span></li>",
                f"<li><strong>Facts</strong><span>{esc(memory.get('fact_count', 0))} profile facts</span></li>",
                f"<li><strong>Latest Titles</strong><span>{esc(latest_display)}</span></li>",
                f"<li><strong>Pending Proposals</strong><span>{esc(proposal_display)}</span></li>",
            ]
        )

    def activity_rows(items: list[dict[str, Any]]) -> str:
        if not items:
            return "<li class='empty'>No recent runtime activity yet.</li>"
        rows = []
        for item in items:
            meta = " · ".join(filter(None, [str(item.get("entry_type", "")), str(item.get("timestamp", ""))]))
            detail_bits = [str(item.get("subtitle", "")), str(item.get("result", ""))]
            detail = " · ".join(bit for bit in detail_bits if bit)
            rows.append(
                f"""
                <li>
                  <strong>{esc(item.get('title', ''))}</strong>
                  <span>{esc(detail or 'No detail captured.')}</span>
                  <code>{esc(meta)}</code>
                </li>
                """
            )
        return "".join(rows)

    def registry_rows(registry: dict[str, Any]) -> str:
        if registry.get("registry_error"):
            return f"<li class='empty'>Registry unavailable: {esc(registry.get('registry_error', ''))}</li>"
        sample_contracts = list(registry.get("sample_contracts") or [])
        contract_display = "; ".join(
            f"{item.get('label', item.get('agent_id', ''))} [{item.get('authority_stage', '')}]"
            for item in sample_contracts
        ) or "No sample contracts."
        domains_display = ", ".join(str(item) for item in registry.get("domains", []) if item) or "None"
        stages_display = ", ".join(str(item) for item in registry.get("authority_stages", []) if item) or "None"
        return "".join(
            [
                f"<li><strong>Agents</strong><span>{esc(registry.get('agent_count', 0))} registered agents</span></li>",
                f"<li><strong>Domains</strong><span>{esc(domains_display)}</span></li>",
                f"<li><strong>Authority Stages</strong><span>{esc(stages_display)}</span></li>",
                f"<li><strong>Sample Contracts</strong><span>{esc(contract_display)}</span></li>",
            ]
        )

    def lane_progress_rows(lane_progress: dict[str, Any]) -> str:
        recent_commits = list(lane_progress.get("recent_commits") or [])
        dirty_sample = list(lane_progress.get("dirty_sample") or [])
        recent_display = "; ".join(str(item) for item in recent_commits if item) or "No recent commits captured."
        dirty_display = "; ".join(str(item) for item in dirty_sample if item) or "Working tree is clean."
        return "".join(
            [
                f"<li><strong>Return Brief</strong><span>{esc(lane_progress.get('return_brief_summary', 'No current summary.'))}</span></li>",
                f"<li><strong>Needs Me Count</strong><span>{esc(lane_progress.get('what_needs_me_count', 0))} live items</span></li>",
                f"<li><strong>Dirty Files</strong><span>{esc(lane_progress.get('dirty_count', 0))} current changes in the lane</span></li>",
                f"<li><strong>Recent Seams</strong><span>{esc(recent_display)}</span></li>",
                f"<li><strong>Dirty Sample</strong><span>{esc(dirty_display)}</span></li>",
            ]
        )

    def failure_recovery_rows(failure_recovery: dict[str, Any]) -> str:
        failing_integrations = list(failure_recovery.get("failing_integrations") or [])
        recent_failures = list(failure_recovery.get("recent_failures") or [])
        action_items = list(failure_recovery.get("action_items") or [])
        integrations_display = "; ".join(
            f"{item.get('name', 'integration')}: {item.get('detail', '')}"
            for item in failing_integrations
        ) or "No integration failures surfaced."
        recent_display = "; ".join(
            f"{item.get('title', 'Runtime failure')} ({item.get('timestamp', 'no timestamp')})"
            for item in recent_failures
        ) or "No recent runtime failures detected."
        action_display = "; ".join(
            f"{item.get('title', '')}: {item.get('detail', '')}"
            for item in action_items
        ) or "No immediate recovery actions needed."
        return "".join(
            [
                f"<li><strong>Integration Issues</strong><span>{esc(failure_recovery.get('integration_issue_count', 0))} current issue(s)</span></li>",
                f"<li><strong>Pending Approvals</strong><span>{esc(failure_recovery.get('pending_approval_count', 0))} gated recovery item(s)</span></li>",
                f"<li><strong>Recent Failures</strong><span>{esc(failure_recovery.get('recent_failure_count', 0))} signal(s) detected</span></li>",
                f"<li><strong>Integration Detail</strong><span>{esc(integrations_display)}</span></li>",
                f"<li><strong>Recent Failure Detail</strong><span>{esc(recent_display)}</span></li>",
                f"<li><strong>Recovery Actions</strong><span>{esc(action_display)}</span></li>",
            ]
        )

    def home_overview_rows(home_overview: dict[str, Any], level3_checklist: dict[str, Any]) -> str:
        top_need = dict(home_overview.get("top_need") or {})
        next_mission = dict(home_overview.get("next_mission") or {})
        active_agent = dict(home_overview.get("active_agent") or {})
        system_state = dict(home_overview.get("system_state") or {})
        actions = list(home_overview.get("actions") or [])
        checklist_route = str(level3_checklist.get("route", "")).strip() or "/progress-center#level3-checklist"
        checklist_label = str(level3_checklist.get("route_label", "")).strip() or "Open Remaining Level 3 Checklist"
        checklist_api = str(level3_checklist.get("api_path", "")).strip() or "/api/progress/module"
        def home_action_control(item: dict[str, Any]) -> str:
            endpoint = str(item.get("endpoint", "")).strip()
            if endpoint:
                method = str(item.get("method", "POST")).strip() or "POST"
                body = item.get("body")
                body_attr = f" data-body={json.dumps(body)!r}" if body is not None else ""
                needs_key = str(item.get("needs_key", "")).strip()
                key_attr = f' data-needs-key="{esc(needs_key)}"' if needs_key else ""
                route = str(item.get("route", "")).strip()
                route_label = str(item.get("route_label", "")).strip() or "Open Surface"
                route_attr = f' data-home-route="{esc(route)}"' if route else ""
                route_label_attr = f' data-home-route-label="{esc(route_label)}"' if route else ""
                fallback_link = f"<a href=\"{esc(route)}\">{esc(route_label)}</a>" if route else ""
                return (
                    f"<button type=\"button\" data-home-action=\"1\" data-endpoint=\"{esc(endpoint)}\" data-method=\"{esc(method)}\"{key_attr}{route_attr}{route_label_attr}{body_attr}>"
                    f"{esc(item.get('label', 'Act'))}</button>{fallback_link}"
                )
            return f"<a href=\"{esc(item.get('route', '/command-center'))}\">{esc(item.get('label', 'Open'))}</a>"

        action_buttons = "".join(home_action_control(item) for item in actions[:4]) or "<a href=\"/command-center\">Refresh Home</a>"
        action_summaries = "".join(
            (
                f"<li><strong>{esc(item.get('label', 'Open'))}</strong>"
                f"<span>{esc(item.get('detail', 'Open the related home surface.'))}</span>"
                f"{('<code>' + esc(item.get('endpoint', '')) + '</code>') if str(item.get('endpoint', '')).strip() else ''}</li>"
            )
            for item in actions[:4]
        )
        return "".join(
            [
                f"<li><strong>Today</strong><span>{esc(home_overview.get('day_label', '')) or 'No day label captured.'}</span></li>",
                f"<li><strong>Headline</strong><span>{esc(home_overview.get('headline', 'No home headline yet.'))}</span></li>",
                f"<li><strong>Top Need</strong><span>{esc(top_need.get('title', 'Nothing urgent right now.'))}</span><span>{esc(top_need.get('detail', ''))}</span><code>{esc(top_need.get('route', '/command-center'))}</code></li>",
                f"<li><strong>Next Mission</strong><span>{esc(next_mission.get('title', 'No mission queued.'))}</span><span>{esc(next_mission.get('detail', ''))}</span><code>{esc(next_mission.get('route', '/mission-board'))}</code></li>",
                f"<li><strong>Active Agent</strong><span>{esc(active_agent.get('title', 'No active agent surfaced.'))}</span><span>{esc(active_agent.get('detail', ''))}</span><code>{esc(active_agent.get('route', '/agent-ops-center'))}</code></li>",
                f"<li><strong>System State</strong><span>{esc(system_state.get('label', 'Stable'))}</span><span>{esc(system_state.get('detail', 'No system summary captured yet.'))}</span><code class=\"history-chip history-chip-{esc(system_state.get('status_class', 'steady'))}\">{esc(system_state.get('label', 'stable'))}</code></li>",
                f"<li><strong>Home Counts</strong><span>{esc(home_overview.get('priority_count', 0))} priorities · {esc(home_overview.get('active_agent_count', 0))} active agents · {esc(home_overview.get('open_mission_count', 0))} open missions · {esc(home_overview.get('recent_activity_count', 0))} recent activity items · {esc(home_overview.get('useful_module_count', 0))} useful module lanes</span></li>",
                f"<li><strong>Hosted Edge</strong><span>{esc(home_overview.get('hosted_summary', 'Hosted edge posture not captured yet.'))}</span><div class='link-row'><a href=\"{esc(home_overview.get('hosted_url', 'https://jarvis.teambinion.org'))}\">{esc(home_overview.get('hosted_url', 'https://jarvis.teambinion.org'))}</a></div></li>",
                f"<li><strong>Level 3 Checklist</strong><span>{esc(level3_checklist.get('summary', 'Open the remaining Level 3 checklist in the dedicated progress route.'))}</span><div class='link-row'><a href=\"{esc(checklist_route)}\">{esc(checklist_label)}</a><a href=\"{esc(checklist_api)}\">Open Progress API</a></div></li>",
                f"<li><strong>Focus Actions</strong><div class='link-row'>{action_buttons}</div></li>",
                action_summaries,
            ]
        )

    def hosted_deployment_rows(hosted_deployment: dict[str, Any]) -> str:
        public_routes = [str(item).strip() for item in list(hosted_deployment.get("public_routes") or []) if str(item).strip()]
        proof_files = [str(item).strip() for item in list(hosted_deployment.get("proof_files") or []) if str(item).strip()]
        route_display = " · ".join(public_routes[:3]) or "No hosted routes discovered."
        file_display = " | ".join(proof_files) or "No deploy proof files captured."
        return "".join(
            [
                f"<li><strong>Status</strong><span>{esc(hosted_deployment.get('summary', 'Hosted deployment posture not captured yet.'))}</span><code class=\"history-chip history-chip-{esc(hosted_deployment.get('status_class', 'steady'))}\">{esc(hosted_deployment.get('status_label', 'wired'))}</code></li>",
                f"<li><strong>Hosted URL</strong><span>{esc(hosted_deployment.get('hosted_url', 'https://jarvis.teambinion.org'))}</span></li>",
                f"<li><strong>Deploy Mode</strong><span>{esc(hosted_deployment.get('deploy_mode', 'unknown'))}</span><span>{esc(hosted_deployment.get('remote_detail', ''))}</span></li>",
                f"<li><strong>Edge</strong><span>{esc(hosted_deployment.get('edge_provider', 'unknown edge'))}</span><span>{esc(route_display)}</span></li>",
                f"<li><strong>Deploy Proof</strong><span>{esc(file_display)}</span><span>{esc(hosted_deployment.get('next_action', 'No deploy next action recorded yet.'))}</span></li>",
            ]
        )

    def home_action_result_rows(action_result: dict[str, Any]) -> str:
        route = str(action_result.get("route", "")).strip()
        route_label = str(action_result.get("route_label", "")).strip() or "Open Related Surface"
        route_row = f"<div class='link-row'><a href=\"{esc(route)}\">{esc(route_label)}</a></div>" if route else ""
        return "".join(
            [
                f"<li><strong>Action</strong><span>{esc(action_result.get('label', 'No home action recorded yet.'))}</span></li>",
                f"<li><strong>Summary</strong><span>{esc(action_result.get('summary', 'No home result summary captured yet.'))}</span><code class=\"history-chip history-chip-{esc(action_result.get('status_class', 'steady'))}\">{esc(action_result.get('status_class', 'steady'))}</code></li>",
                f"<li><strong>What Changed</strong><span>{esc(action_result.get('detail', 'No home action result detail captured yet.'))}</span>{route_row}</li>",
            ]
        )

    def seam_tracker_rows(seam_tracker: dict[str, Any]) -> str:
        counts = dict(seam_tracker.get("counts") or {})
        items = list(seam_tracker.get("items") or [])
        count_summary = " · ".join(
            f"{value} {key.lower()}"
            for key, value in counts.items()
            if int(value or 0) > 0
        ) or "No seam counts recorded yet."
        rows = [
            f"<li><strong>Summary</strong><span>{esc(seam_tracker.get('summary', 'No seam tracker summary yet.'))}</span></li>",
            f"<li><strong>Counts</strong><span>{esc(count_summary)}</span></li>",
        ]
        for index, item in enumerate(items):
            rows.append(
                "<li class='needs-action'>"
                f"<strong>{esc(item.get('name', 'Seam'))}</strong>"
                f"<span>{esc(item.get('what_became_real', 'No seam outcome recorded yet.'))}</span>"
                f"<code class=\"history-chip history-chip-{esc(item.get('status_class', 'steady'))}\">{esc(item.get('status', 'Wired'))}</code>"
                f"<code>{esc(item.get('module', 'Progress'))} · {esc(item.get('maturity', 'Wired'))}</code>"
                f"<span>{esc(item.get('commit_status', 'No commit posture recorded.'))}</span>"
                f"<div class='action-row'><button type='button' data-detail-kind='seam' data-detail-index='{index}'>Inspect Seam</button></div>"
                "</li>"
            )
        return "".join(rows)

    def progress_dashboard_rows(board: dict[str, Any]) -> str:
        counts = dict(board.get("counts") or {})
        items = list(board.get("items") or [])
        count_summary = " · ".join(
            f"{value} {key}"
            for key, value in counts.items()
            if int(value or 0) > 0
        ) or "No progress readiness counts recorded yet."
        rows = [
            f"<li><strong>Summary</strong><span>{esc(board.get('summary', 'No progress dashboard summary yet.'))}</span></li>",
            f"<li><strong>Readiness Counts</strong><span>{esc(count_summary)}</span></li>",
        ]
        for index, item in enumerate(items):
            rows.append(
                "<li class='needs-action'>"
                f"<strong>{esc(item.get('module', 'Progress Module'))}</strong>"
                f"<span>{esc(item.get('summary', 'No readiness summary captured yet.'))}</span>"
                f"<code class=\"history-chip history-chip-{esc(item.get('status_class', 'steady'))}\">{esc(item.get('status', 'Wired'))}</code>"
                f"<code>{esc(item.get('roadmap_level', 'Level 3'))} · {esc(item.get('status_label', 'wired'))}</code>"
                f"<span>{esc(item.get('evidence', 'No evidence captured yet.'))}</span>"
                f"<div class='action-row'><button type='button' data-detail-kind='progress' data-detail-index='{index}'>Inspect Progress</button></div>"
                "</li>"
            )
        return "".join(rows)

    def core_modules_rows(board: dict[str, Any]) -> str:
        counts = dict(board.get("counts") or {})
        items = list(board.get("items") or [])
        count_summary = " · ".join(
            f"{value} {key.lower()}"
            for key, value in counts.items()
            if int(value or 0) > 0
        ) or "No core module readiness counts recorded yet."
        rows = [
            f"<li><strong>Summary</strong><span>{esc(board.get('summary', 'No core modules summary yet.'))}</span></li>",
            f"<li><strong>Module Counts</strong><span>{esc(count_summary)}</span></li>",
        ]
        for index, item in enumerate(items):
            rows.append(
                "<li class='needs-action'>"
                f"<strong>{esc(item.get('title', 'Module'))}</strong>"
                f"<span>{esc(item.get('summary', 'No module summary captured yet.'))}</span>"
                f"<code class=\"history-chip history-chip-{esc(item.get('status_class', 'steady'))}\">{esc(item.get('status', 'Wired'))}</code>"
                f"<code>{esc(item.get('screen_kind', 'screen'))} · {esc(item.get('roadmap_level', 'Level 3'))}</code>"
                f"<span>{esc(item.get('evidence', 'No module evidence captured yet.'))}</span>"
                f"<div class='action-row'><a href='{esc(item.get('screen_path', '/command-center'))}'>Open Module</a><a href='{esc(item.get('api_path', '/api/command-center'))}'>Open API</a><button type='button' data-detail-kind='module' data-detail-index='{index}'>Inspect Module</button></div>"
                "</li>"
            )
        return "".join(rows)

    def mission_task_board_rows(board: dict[str, Any]) -> str:
        counts = dict(board.get("counts") or {})
        items = list(board.get("items") or [])
        count_summary = " · ".join(
            f"{key} {int(value or 0)}"
            for key, value in counts.items()
        ) or "No mission counts recorded yet."
        rows = [
            f"<li><strong>Summary</strong><span>{esc(board.get('summary', 'No mission board summary yet.'))}</span></li>",
            f"<li><strong>Lane Counts</strong><span>{esc(count_summary)}</span></li>",
        ]
        for index, item in enumerate(items):
            rows.append(
                "<li class='needs-action'>"
                f"<strong>{esc(item.get('title', 'Mission'))}</strong>"
                f"<span>{esc(item.get('brief', 'No mission brief captured yet.'))}</span>"
                f"<code class=\"history-chip history-chip-{esc(item.get('lane_class', 'steady'))}\">{esc(item.get('lane', 'next'))}</code>"
                f"<code>{esc(item.get('primary_domain', 'general'))} · {esc(item.get('owner_agent', 'jarvis-orchestrator'))}</code>"
                f"<span>{esc(item.get('next_step', 'Review mission brief'))}</span>"
                f"<div class='action-row'><button type='button' data-detail-kind='mission' data-detail-index='{index}'>Inspect Mission</button></div>"
                "</li>"
            )
        return "".join(rows)

    def agent_ops_roster_rows(roster: dict[str, Any]) -> str:
        counts = dict(roster.get("counts") or {})
        items = list(roster.get("items") or [])
        count_summary = " · ".join(
            f"{key} {int(value or 0)}"
            for key, value in counts.items()
        ) or "No agent counts recorded yet."
        rows = [
            f"<li><strong>Summary</strong><span>{esc(roster.get('summary', 'No agent roster summary yet.'))}</span></li>",
            f"<li><strong>Roster Counts</strong><span>{esc(count_summary)}</span></li>",
        ]
        for index, item in enumerate(items):
            rows.append(
                "<li class='needs-action'>"
                f"<strong>{esc(item.get('name', 'Agent'))}</strong>"
                f"<span>{esc(item.get('purpose', 'No purpose recorded.'))}</span>"
                f"<code class=\"history-chip history-chip-{esc(item.get('status_class', 'steady'))}\">{esc(item.get('status', 'unknown'))}</code>"
                f"<code class=\"history-chip history-chip-{esc(item.get('maturity_class', 'steady'))}\">{esc(item.get('maturity', 'Wired'))}</code>"
                f"<code>{esc(item.get('domain', 'general'))} · {esc(item.get('assignment', 'unassigned'))}</code>"
                f"<span>{esc(item.get('last_activity', 'not recorded'))}</span>"
                f"<div class='action-row'><button type='button' data-detail-kind='agent' data-detail-index='{index}'>Inspect Agent</button></div>"
                "</li>"
            )
        return "".join(rows)

    def brief_preview_rows(brief_preview: dict[str, Any]) -> str:
        supporting_lines = list(brief_preview.get("supporting_lines") or [])
        support_display = " ; ".join(str(item) for item in supporting_lines if item) or "No supporting lines captured yet."
        rss_sources = list(brief_preview.get("rss_sources") or [])
        rss_display = ", ".join(str(item) for item in rss_sources if item) or "No live news sources attached."
        return "".join(
            [
                f"<li><strong>Actor</strong><span>{esc(brief_preview.get('actor', 'Chris'))}</span></li>",
                f"<li><strong>Headline</strong><span>{esc(brief_preview.get('headline', 'No briefing headline yet.'))}</span></li>",
                f"<li><strong>Supporting Lines</strong><span>{esc(support_display)}</span></li>",
                f"<li><strong>Memory Context</strong><span>{esc(brief_preview.get('memory_entry_count', 0))} memory entries informing this preview</span></li>",
                f"<li><strong>Live News</strong><span>{esc('on' if brief_preview.get('live_news') else 'off')} · {esc(brief_preview.get('rss_articles', 0))} article(s)</span></li>",
                f"<li><strong>Sources</strong><span>{esc(rss_display)}</span></li>",
            ]
        )

    def timeline_preview_rows(timeline_preview: dict[str, Any]) -> str:
        summary = dict(timeline_preview.get("summary") or {})
        items = list(timeline_preview.get("items") or [])
        recent_motion = list(timeline_preview.get("recent_motion") or [])
        motion_display = "; ".join(str(item) for item in recent_motion if item) or "No recent motion captured."
        item_rows = "".join(
            f"""
            <li class="needs-action">
              <strong>{esc(item.get('title', ''))}</strong>
              <span>{esc(item.get('summary', 'JARVIS surfaced a live open-loop item.'))}</span>
              <code>{esc(item.get('domain', 'general'))} / {esc(item.get('status', ''))}</code>
            </li>
            """
            for item in items
        ) or "<li class='empty'>No seeded timeline items yet.</li>"
        return "".join(
            [
                f"<li><strong>Waiting On You</strong><span>{esc(summary.get('waiting_on_you', 0))} open item(s)</span></li>",
                f"<li><strong>Needs Revisit</strong><span>{esc(summary.get('needs_revisit', 0))} surfaced item(s)</span></li>",
                f"<li><strong>Recent Motion</strong><span>{esc(summary.get('recent_motion_count', 0))} timeline signal(s)</span></li>",
                f"<li><strong>Seeded Timeline</strong><span>Hydrates into actionable open-loop items when the live API is available.</span></li>",
                item_rows,
                f"<li><strong>Recent Motion Detail</strong><span>{esc(motion_display)}</span></li>",
            ]
        )

    def open_loop_inspector_rows(open_loop_inspector: dict[str, Any]) -> str:
        summary = dict(open_loop_inspector.get("summary") or {})
        items = list(open_loop_inspector.get("items") or [])
        proactive_surface = list(open_loop_inspector.get("proactive_surface") or [])
        task_lanes = list(open_loop_inspector.get("task_lanes") or [])
        item_rows = "".join(
            f"""
            <li class="needs-action">
              <strong>{esc(item.get('title', 'Open loop'))}</strong>
              <span>{esc(item.get('summary', 'JARVIS surfaced a live open-loop item.'))}</span>
              <code>{esc(item.get('domain', 'general'))} / {esc(item.get('status', 'open'))} / {esc(item.get('owner_agent', 'JARVIS'))}</code>
              <span>{esc(item.get('next_action', 'No next action captured.'))}</span>
              <span>Review by: {esc(item.get('next_review_at', 'not scheduled'))}</span>
              <span>Autonomy: {esc((item.get('auto_execution') or {}).get('summary', 'Review required.'))}</span>
              <div class="action-row">
                <button type="button" data-detail-kind="open-loop" data-detail-index="{index}">Inspect</button>
              </div>
            </li>
            """
            for index, item in enumerate(items)
        ) or "<li class='empty'>No seeded open-loop items yet.</li>"
        proactive_display = "; ".join(
            f"{item.get('title', 'Open loop')}: {item.get('proactive_reason', '')}"
            for item in proactive_surface
        ) or "No immediate resurfacing items."
        lane_display = "; ".join(
            f"{item.get('owner_agent', 'JARVIS')} / {item.get('domain', 'general')}: {item.get('approval_threshold', {}).get('summary', '')}"
            for item in task_lanes
        ) or "No task lanes captured."
        return "".join(
            [
                f"<li><strong>Total</strong><span>{esc(summary.get('total', 0))} open loop(s)</span></li>",
                f"<li><strong>Waiting On You</strong><span>{esc(summary.get('waiting_on_you', 0))} current item(s)</span></li>",
                f"<li><strong>Needs Revisit</strong><span>{esc(summary.get('needs_revisit', 0))} resurfaced item(s)</span></li>",
                f"<li><strong>Proactive Surface</strong><span>{esc(proactive_display)}</span></li>",
                f"<li><strong>Task Lanes</strong><span>{esc(lane_display)}</span></li>",
                item_rows,
            ]
        )

    def detail_inspector_rows(detail_inspector: dict[str, Any]) -> str:
        actions = list(detail_inspector.get("available_actions") or [])
        evidence_lines = list(detail_inspector.get("evidence_lines") or [])
        decision_history = list(detail_inspector.get("decision_history") or [])
        recent_trace = list(detail_inspector.get("recent_trace") or [])
        item_timeline = list(detail_inspector.get("item_timeline") or [])
        selected_timeline_event = dict(detail_inspector.get("selected_timeline_event") or {})
        selected_timeline_event_detail = dict(detail_inspector.get("selected_timeline_event_detail") or {})
        motion_proof_sections = list(detail_inspector.get("motion_proof_sections") or [])
        motion_proof_panels = list(detail_inspector.get("motion_proof_panels") or [])
        motion_proof_excerpts = list(detail_inspector.get("motion_proof_excerpts") or [])
        motion_proof_artifacts = list(detail_inspector.get("motion_proof_artifacts") or [])
        motion_artifact_focus_sections = list(detail_inspector.get("motion_artifact_focus_sections") or [])
        motion_artifact_focus_title = str(detail_inspector.get("motion_artifact_focus_title") or "No localized artifact focus selected.")
        motion_artifact_focus_summary = str(detail_inspector.get("motion_artifact_focus_summary") or "Use Motion Proof Artifacts to focus a more exact in-page proof block.")
        motion_artifact_focus_posture_summary = str(detail_inspector.get("motion_artifact_focus_posture_summary") or "No localized artifact posture captured yet.")
        motion_artifact_focus_title_lower = motion_artifact_focus_title.lower()
        motion_artifact_focus_posture_badge_label = str(
            detail_inspector.get("motion_artifact_focus_posture_badge_label")
            or (
                "approval posture"
                if "approval" in motion_artifact_focus_title_lower
                else "inbox posture"
                if "notification" in motion_artifact_focus_title_lower
                else "workflow posture"
                if "open-loop" in motion_artifact_focus_title_lower
                else "artifact posture"
            )
        )
        motion_artifact_focus_posture_badge_class = str(
            detail_inspector.get("motion_artifact_focus_posture_badge_class")
            or (
                "approval"
                if "approval" in motion_artifact_focus_title_lower
                else "notification"
                if "notification" in motion_artifact_focus_title_lower
                else "open-loop"
                if "open-loop" in motion_artifact_focus_title_lower
                else "artifact"
            )
        )
        motion_artifact_focus_posture_state_label = str(
            detail_inspector.get("motion_artifact_focus_posture_state_label")
            or (
                "approved"
                if ("approval" in motion_artifact_focus_title_lower and "approved" in str(detail_inspector.get("last_decision_summary") or "").lower())
                else "rejected"
                if ("approval" in motion_artifact_focus_title_lower and any(token in str(detail_inspector.get("last_decision_summary") or "").lower() for token in ("rejected", "denied", "failed")))
                else "awaiting consent"
                if ("approval" in motion_artifact_focus_title_lower and str(detail_inspector.get("status") or "").lower() in {"pending", "queued", "waiting", "needs-review"})
                else "opened"
                if ("notification" in motion_artifact_focus_title_lower and str(detail_inspector.get("status") or "").lower() in {"opened", "read", "handled"})
                else "needs triage"
                if ("notification" in motion_artifact_focus_title_lower and str(detail_inspector.get("status") or "").lower() in {"new", "queued", "pending", "unread"})
                else "delivery issue"
                if ("notification" in motion_artifact_focus_title_lower and str(detail_inspector.get("status") or "").lower() in {"failed", "error"})
                else "resolved"
                if ("open-loop" in motion_artifact_focus_title_lower and str(detail_inspector.get("status") or "").lower() in {"resolved", "complete", "completed", "done", "closed"})
                else "blocked"
                if ("open-loop" in motion_artifact_focus_title_lower and str(detail_inspector.get("status") or "").lower() in {"blocked", "failed", "error", "stalled"})
                else "waiting"
                if ("open-loop" in motion_artifact_focus_title_lower and str(detail_inspector.get("status") or "").lower() in {"pending", "queued", "waiting"})
                else "steady"
            )
        )
        motion_artifact_focus_posture_state_class = str(
            detail_inspector.get("motion_artifact_focus_posture_state_class")
            or (
                "recovered"
                if motion_artifact_focus_posture_state_label in {"approved", "opened", "resolved"}
                else "regressed"
                if motion_artifact_focus_posture_state_label in {"rejected", "delivery issue", "blocked"}
                else "pending"
                if motion_artifact_focus_posture_state_label in {"awaiting consent", "needs triage", "waiting"}
                else "steady"
            )
        )
        motion_artifact_focus_posture_hint = str(
            detail_inspector.get("motion_artifact_focus_posture_hint")
            or (
                "Review the approval proof and use the inline request controls when you are ready to decide."
                if motion_artifact_focus_posture_state_label == "awaiting consent"
                else "Approval posture looks recovered; execute only if the returned proof still matches intent."
                if motion_artifact_focus_posture_state_label == "approved"
                else "Approval posture regressed; inspect the rejection proof before retrying."
                if motion_artifact_focus_posture_state_label == "rejected"
                else "Open the notification or ignore it to clear this inbox pressure."
                if motion_artifact_focus_posture_state_label == "needs triage"
                else "Notification posture looks healthy; use the stored proof if you need the exact payload."
                if motion_artifact_focus_posture_state_label == "opened"
                else "Notification delivery regressed; inspect the proof payload before trusting this alert."
                if motion_artifact_focus_posture_state_label == "delivery issue"
                else "This workflow is waiting; use the artifact actions or timeline proof to move it forward."
                if motion_artifact_focus_posture_state_label == "waiting"
                else "This workflow is blocked; inspect the localized proof and mutation rows before taking the next step."
                if motion_artifact_focus_posture_state_label == "blocked"
                else "This record looks recovered; verify the exact proof snapshot if you need stronger confirmation."
                if motion_artifact_focus_posture_state_label == "resolved"
                else "Use the localized proof blocks below for the next exact-record move."
            )
        )
        motion_artifact_focus_posture_outcome_line = str(
            detail_inspector.get("motion_artifact_focus_posture_outcome_line")
            or "No localized artifact action outcome captured yet."
        )
        motion_artifact_focus_posture_outcome_index = detail_inspector.get("motion_artifact_focus_posture_outcome_index")
        motion_artifact_focus_posture_snapshot_cue = str(detail_inspector.get("motion_artifact_focus_posture_snapshot_cue") or "")
        motion_artifact_focus_posture_suggested_action = dict(detail_inspector.get("motion_artifact_focus_posture_suggested_action") or {})
        motion_artifact_focus_posture_snapshot_action = dict(detail_inspector.get("motion_artifact_focus_posture_snapshot_action") or {})
        motion_artifact_focus_posture_snapshot_reason = str(detail_inspector.get("motion_artifact_focus_posture_snapshot_reason") or "")
        motion_artifact_focus_posture_snapshot_reason_target = dict(detail_inspector.get("motion_artifact_focus_posture_snapshot_reason_target") or {})
        motion_artifact_focus_posture_snapshot_reason_focus = dict(detail_inspector.get("motion_artifact_focus_posture_snapshot_reason_focus") or {})
        motion_artifact_focus_delta_summary = str(detail_inspector.get("motion_artifact_focus_delta_summary") or "No localized artifact mutation captured yet.")
        motion_artifact_focus_delta_sections = list(detail_inspector.get("motion_artifact_focus_delta_sections") or [])
        motion_artifact_focus_excerpts = list(detail_inspector.get("motion_artifact_focus_excerpts") or [])
        motion_artifact_focus_proof_compare_summary = str(detail_inspector.get("motion_artifact_focus_proof_compare_summary") or "No localized artifact proof comparison captured yet.")
        motion_artifact_focus_proof_compare_rows = list(detail_inspector.get("motion_artifact_focus_proof_compare_rows") or [])
        motion_artifact_focus_history_summary = str(detail_inspector.get("motion_artifact_focus_history_summary") or "No localized artifact action history captured yet.")
        motion_artifact_focus_history_meta = str(detail_inspector.get("motion_artifact_focus_history_meta") or "")
        motion_artifact_focus_history_rows = list(detail_inspector.get("motion_artifact_focus_history_rows") or [])
        motion_artifact_focus_history_note = str(detail_inspector.get("motion_artifact_focus_history_note") or "")
        motion_artifact_focus_actions = list(detail_inspector.get("motion_artifact_focus_actions") or [])
        action_display = ", ".join(str(item.get("label", item.get("id", ""))) for item in actions if item) or "No direct actions attached."
        evidence_display = "; ".join(str(item) for item in evidence_lines if item) or "No evidence captured yet."
        decision_display = "; ".join(
            f"{item.get('status', 'unknown')} / {item.get('resolution', 'unclassified')} by {item.get('actor', '-')} at {item.get('when', 'unknown time')}"
            for item in decision_history
        ) or "No prior decision history captured."
        trace_display = "; ".join(
            f"{item.get('title', 'Activity')} ({item.get('timestamp', 'no timestamp')}): {item.get('detail', '')}"
            for item in recent_trace
        ) or "No recent trace captured."
        timeline_display = "; ".join(
            f"{item.get('timestamp', 'no timestamp')} · {item.get('kind', 'event')} · {item.get('title', 'Timeline item')} · {item.get('detail', '')}"
            for item in item_timeline
        ) or "No per-item timeline captured yet."
        timeline_buttons = "".join(
            f'<button type="button" data-timeline-index="{index}">{esc(item.get("kind", "event"))}: {esc(item.get("title", "Timeline item"))}</button>'
            for index, item in enumerate(item_timeline)
        ) or "<span>No timeline events available.</span>"
        selected_timeline_display = (
            f"{selected_timeline_event.get('timestamp', 'no timestamp')} · "
            f"{selected_timeline_event.get('kind', 'event')} · "
            f"{selected_timeline_event.get('title', 'Timeline item')} · "
            f"{selected_timeline_event.get('detail', 'No timeline event detail available.')}"
            if selected_timeline_event
            else "No timeline event selected."
        )
        event_evidence_display = "; ".join(str(item) for item in selected_timeline_event_detail.get("evidence_lines", []) if item) or "No event-specific evidence captured yet."
        event_fields_display = "; ".join(str(item) for item in selected_timeline_event_detail.get("related_fields", []) if item) or "No related fields attached."
        event_actions_display = ", ".join(str(item) for item in selected_timeline_event_detail.get("next_actions", []) if item) or "No follow-on actions suggested."
        event_evidence_links = "".join(
            f'<a href="{esc(item.get("href", "#"))}">{esc(item.get("label", item.get("href", "Link")))}</a>'
            for item in selected_timeline_event_detail.get("evidence_links", [])
            if item
        ) or "<span>No direct evidence links available.</span>"
        event_preview_sections = list(selected_timeline_event_detail.get("preview_sections") or [])
        event_preview_kind = str(selected_timeline_event_detail.get("preview_kind") or "generic")
        event_preview_title = str(selected_timeline_event_detail.get("preview_title") or "Inline Preview")
        event_preview_summary = str(selected_timeline_event_detail.get("preview_summary") or "No inline evidence preview available.")
        decision_history_summary = str(selected_timeline_event_detail.get("decision_history_summary") or "")
        approval_review_summary = str(selected_timeline_event_detail.get("approval_review_summary") or "")
        approval_review_fields = list(selected_timeline_event_detail.get("approval_review_fields") or [])
        approval_posture_fields = list(selected_timeline_event_detail.get("approval_posture_fields") or [])
        consequence_fields = list(selected_timeline_event_detail.get("consequence_fields") or [])
        guidance_lines = list(selected_timeline_event_detail.get("next_actions") or [])
        notification_snapshot = str(selected_timeline_event_detail.get("notification_snapshot") or "")
        guidance_display = (
            "<div class='preview-subsection'><strong>Operator Guidance</strong>"
            + "".join(
                f"<div class='preview-row'><strong>Next</strong><span>{esc(item)}</span></div>"
                for item in guidance_lines
                if item
            )
            + "</div>"
        ) if guidance_lines else ""
        def preview_rows(items: list[dict[str, Any]], default_label: str, value_tag: str) -> str:
            return "".join(
                f"<div class='preview-row'><strong>{esc(item.get('label', default_label))}</strong><{value_tag}>{esc(item.get('value', ''))}</{value_tag}></div>"
                for item in items
                if item
            )
        def preview_link_row(items: list[dict[str, Any]]) -> str:
            links = "".join(
                f'<a href="{esc(item.get("href", "#"))}">{esc(item.get("label", item.get("href", "Link")))}</a>'
                for item in items
                if item
            )
            return f"<div class='link-row'>{links}</div>" if links else ""
        def default_preview_row(title: str, summary: str) -> str:
            return f"<div><strong>{esc(title)}</strong><span>{esc(summary)}</span></div>"
        motion_proof_display = "".join(
            f"<div class='preview-row'><strong>{esc(item.get('label', 'Motion Proof'))}</strong><span>{esc(item.get('value', ''))}</span></div>"
            for item in motion_proof_sections
            if item
        ) or "<span>No localized motion proof snapshot available.</span>"
        motion_proof_panel_display = "".join(
            (
                f"<div class='preview-subsection'><strong>{esc(item.get('title', 'Motion Proof View'))}</strong>"
                f"<span>{esc(item.get('summary', 'No localized motion-proof view attached.'))}</span>"
                f"{preview_rows(list(item.get('rows') or []), 'Detail', 'span')}"
                f"{preview_link_row(list(item.get('links') or []))}"
                f"</div>"
            )
            for item in motion_proof_panels
            if item
        ) or "<div class='preview-subsection'><span>No motion-proof-specific view available.</span></div>"
        motion_proof_excerpt_display = "".join(
            f"<div class='preview-row'><strong>Excerpt</strong><code>{esc(str(item))}</code></div>"
            for item in motion_proof_excerpts
            if item
        ) or "<div class='preview-subsection'><span>No exact motion-proof excerpts attached.</span></div>"
        motion_proof_artifact_display = "".join(
            (
                f"<div class='preview-subsection'><strong>{esc(item.get('label', 'Proof Artifact'))}</strong>"
                f"<span>{esc(item.get('summary', 'No artifact summary attached.'))}</span>"
                f"{f'<div class=\"action-row\"><button type=\"button\" data-motion-artifact-index=\"{index}\">Inspect In-Page</button></div>' if item.get('focus_kind') else ''}"
                f"{preview_link_row([{'label': item.get('link_label', item.get('label', 'Open Artifact')), 'href': item.get('href', '#')}])}"
                f"</div>"
            )
            for index, item in enumerate(motion_proof_artifacts)
            if item
        ) or "<div class='preview-subsection'><span>No exact motion-proof artifacts attached.</span></div>"
        motion_artifact_focus_action_buttons = "".join(
            f'<button type="button" data-endpoint="{esc(item.get("endpoint", ""))}"'
            f' data-method="{esc(item.get("method", "POST"))}"'
            f'{f" data-body={json.dumps(item.get("body", ""))!r}" if item.get("body") else ""}>'
            f'{esc(item.get("label", item.get("action", "Act")))}</button>'
            for item in motion_artifact_focus_actions
            if str(item.get("endpoint", "")).strip()
        )
        motion_artifact_focus_history_display = "".join(
            (
                f"<div class='preview-row'><strong>{esc(item.get('label', 'Artifact Action History'))}</strong>"
                f"{('<code class=\"history-chip history-chip-' + esc(item.get('badge_class', 'artifact')) + '\">' + esc(item.get('badge', '')) + '</code>') if item.get('badge') else ''}"
                f"{('<code class=\"history-chip history-chip-' + esc(item.get('trend_class', 'steady')) + '\">' + esc(item.get('trend', '')) + '</code>') if item.get('trend') else ''}"
                f"{('<code class=\"history-chip history-chip-' + esc(item.get('last_revisited_lane_class', 'steady')) + '\">' + esc(item.get('last_revisited_lane_label', '')) + '</code>') if item.get('last_revisited_lane_label') else ''}"
                f"<span>{esc(item.get('value', ''))}</span>"
                f"{('<span>' + esc(item.get('last_revisited_lane_summary', '')) + '</span>') if item.get('last_revisited_lane_summary') else ''}"
                f"{f'<button type=\"button\" data-motion-artifact-history-index=\"{index}\">Inspect Action</button>' if item.get('jumpable') else ''}"
                f"</div>"
            )
            for index, item in enumerate(motion_artifact_focus_history_rows)
            if item
        ) or "<span>No localized artifact action history rows captured yet.</span>"
        motion_artifact_focus_posture_suggested_action_label = str(
            motion_artifact_focus_posture_suggested_action.get("label")
            or motion_artifact_focus_posture_suggested_action.get("summary")
            or "No direct next move suggested."
        )
        motion_artifact_focus_posture_suggested_action_button = (
            f'<button type="button" data-endpoint="{esc(str(motion_artifact_focus_posture_suggested_action.get("endpoint", "")))}"'
            f' data-method="{esc(str(motion_artifact_focus_posture_suggested_action.get("method", "POST")))}"'
            f'{f" data-body={json.dumps(motion_artifact_focus_posture_suggested_action.get("body", ""))!r}" if motion_artifact_focus_posture_suggested_action.get("body") else ""}>'
            f'{esc(str(motion_artifact_focus_posture_suggested_action.get("label", "Suggested Next")))}'
            f"</button>"
        ) if str(motion_artifact_focus_posture_suggested_action.get("endpoint", "")).strip() else ""
        motion_artifact_focus_posture_snapshot_action_label = str(
            motion_artifact_focus_posture_snapshot_action.get("label")
            or motion_artifact_focus_posture_snapshot_action.get("summary")
            or "No reopened next move suggested."
        )
        motion_artifact_focus_posture_snapshot_action_button = (
            f'<button type="button" data-endpoint="{esc(str(motion_artifact_focus_posture_snapshot_action.get("endpoint", "")))}"'
            f' data-method="{esc(str(motion_artifact_focus_posture_snapshot_action.get("method", "POST")))}"'
            f'{f" data-body={json.dumps(motion_artifact_focus_posture_snapshot_action.get("body", ""))!r}" if motion_artifact_focus_posture_snapshot_action.get("body") else ""}>'
            f'{esc(str(motion_artifact_focus_posture_snapshot_action.get("label", "Reopened Next")))}'
            f"</button>"
        ) if str(motion_artifact_focus_posture_snapshot_action.get("endpoint", "")).strip() else ""
        motion_artifact_focus_posture_snapshot_return_button = (
            '<button type="button" data-motion-artifact-snapshot-return="1">Return to Reopened Proof</button>'
            if motion_artifact_focus_posture_snapshot_reason_target
            else ""
        )
        motion_artifact_focus_posture_snapshot_reason_button = (
            '<button type="button" data-motion-artifact-snapshot-reason="1">Inspect Why</button>'
            if motion_artifact_focus_posture_snapshot_reason_target else ""
        )
        motion_artifact_focus_posture_snapshot_focus_actions = (
            "<div class='action-row'>"
            + "".join(
                (
                    f'<button type="button" data-motion-artifact-history-index="{esc(str(item.get("history_index", "")))}">{esc(str(item.get("label", "Inspect Action")))}</button>'
                    if item.get("kind") == "history"
                    else f'<button type="button" data-timeline-index="{esc(str(item.get("timeline_event_index", "")))}">{esc(str(item.get("label", "Inspect Timeline Event")))}</button>'
                )
                for item in list(motion_artifact_focus_posture_snapshot_reason_focus.get("action_buttons") or [])
                if item
            )
            + "</div>"
        ) if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("action_buttons") else ""
        motion_artifact_focus_posture_snapshot_focus_summary = (
            f"<span>{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('pivot_summary', '')))}</span>"
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("pivot_summary")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_path = (
            f"<code class=\"history-chip history-chip-{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('active_path_class', 'steady')))}\">{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('active_path_label', 'proof focus')))}</code>"
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("active_path_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_path_summary = (
            f"<span>{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('active_path_summary', '')))}</span>"
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("active_path_summary")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_target = (
            f"<span>{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('active_target_label', '')))}</span>"
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("active_target_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_context = (
            f"<div class='preview-row'><strong>Current Proof Context</strong><span>{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('context_summary', '')))}</span></div>"
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("context_summary")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_context_selection_target = (
            f"<span>{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('context_selection_target', '')))}</span>"
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("context_selection_target")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_context_selection = (
            f"<div class='preview-row'><strong>Active Context Pivot</strong><code class=\"history-chip history-chip-{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('context_selection_class', 'steady')))}\">{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('context_selection_label', 'proof lane active')))}</code>{motion_artifact_focus_posture_snapshot_focus_context_selection_target}</div>"
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("context_selection_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_context_selection_actions = (
            "<div class='action-row'>"
            + "".join(
                (
                    f'<button type="button" data-motion-artifact-snapshot-target-artifact-index="{esc(str(item.get("motion_artifact_index", "")))}">{esc(str(item.get("label", "Open Anchored Artifact")))}</button>'
                    if item.get("kind") == "artifact"
                    else f'<button type="button" data-motion-artifact-snapshot-target-timeline-index="{esc(str(item.get("timeline_event_index", "")))}">{esc(str(item.get("label", "Open Anchored Timeline")))}</button>'
                )
                for item in list(motion_artifact_focus_posture_snapshot_reason_focus.get("context_selection_buttons") or [])
                if item
            )
            + "</div>"
        ) if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("context_selection_buttons") else ""
        motion_artifact_focus_posture_snapshot_focus_context_selection_confirmation = (
            f"<div class='preview-row'><strong>Anchor Follow State</strong><code class=\"history-chip history-chip-{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('context_selection_confirmation_class', 'steady')))}\">{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('context_selection_confirmation_label', 'anchor ready')))}</code></div>"
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("context_selection_confirmation_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_context_selection_confirmation_actions = (
            '<div class="action-row"><button type="button" data-motion-artifact-snapshot-return="1">Return to Proof Lane</button></div>'
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("context_selection_confirmation_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_confirmation = (
            f"<div class='preview-row'><strong>Proof Lane Restored</strong><code class=\"history-chip history-chip-{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_confirmation_class', 'steady')))}\">{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_confirmation_label', 'proof lane restored')))}</code>{f'<code class=\"history-chip history-chip-' + esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_origin_class', 'artifact'))) + '\">' + esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_origin_label', 'latest outcome'))) + '</code>' if motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_origin_label') else ''}{f'<code class=\"history-chip history-chip-' + esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_lane_class', 'steady'))) + '\">' + esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_lane_label', 'proof lane'))) + '</code>' if motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_lane_label') else ''}<span>{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_confirmation_summary', '')))}</span></div>"
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_confirmation_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason = (
            f"<span>{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason', '')))}</span>"
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_button = (
            f"<button type=\"button\" data-motion-artifact-snapshot-reason=\"1\">{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_button_label', 'Inspect Reopened Evidence')))}</button>"
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_button_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_source = (
            f"<button type=\"button\" class=\"history-chip history-chip-{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_source_class', 'artifact')))}\" data-motion-artifact-snapshot-reason=\"1\">{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_source_label', 'stored evidence')))}</button>"
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_source_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_active = (
            f"<div class='preview-row'><strong>Evidence Focus State</strong><code class=\"history-chip history-chip-{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_active_class', 'steady')))}\">{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_active_label', 'stored evidence active')))}</code><span>{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_active_summary', '')))}</span>{f'<span>' + esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_active_target', ''))) + '</span>' if motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_active_target') else ''}</div>"
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_active_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_active_selection = (
            f"<div class='preview-row'><strong>Evidence Pivot State</strong><code class=\"history-chip history-chip-{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_active_selection_class', 'steady')))}\">{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_active_selection_label', 'evidence target active')))}</code><span>{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_active_selection_summary', '')))}</span></div>"
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_active_selection_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed = (
            f"<div class='preview-row'><strong>Evidence Focus Restored</strong><code class=\"history-chip history-chip-{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_class', 'steady')))}\">{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_label', 'stored evidence resumed')))}</code><span>{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_summary', '')))}</span></div>"
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_active = (
            f"<div class='preview-row'><strong>Restored Evidence State</strong><code class=\"history-chip history-chip-{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_active_class', 'steady')))}\">{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_active_label', 'restored evidence active')))}</code><span>{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_active_summary', '')))}</span></div>"
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_active_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_active_selection = (
            f"<div class='preview-row'><strong>Restored Evidence Target</strong><code class=\"history-chip history-chip-{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_active_selection_class', 'steady')))}\">{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_active_selection_label', 'restored evidence target active')))}</code><span>{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_active_selection_summary', '')))}</span></div>"
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_active_selection_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return = (
            f"<div class='preview-row'><strong>Restored Evidence Lane Resumed</strong><code class=\"history-chip history-chip-{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_class', 'steady')))}\">{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_label', 'restored evidence lane resumed')))}</code><span>{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_summary', '')))}</span></div>"
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_active = (
            f"<div class='preview-row'><strong>Resumed Evidence Focus State</strong><code class=\"history-chip history-chip-{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_active_class', 'steady')))}\">{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_active_label', 'resumed evidence active')))}</code><span>{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_active_summary', '')))}</span></div>"
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_active_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_active_selection = (
            f"<div class='preview-row'><strong>Resumed Evidence Target</strong><code class=\"history-chip history-chip-{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_active_selection_class', 'steady')))}\">{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_active_selection_label', 'resumed evidence target active')))}</code><span>{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_active_selection_summary', '')))}</span></div>"
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_active_selection_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return = (
            f"<div class='preview-row'><strong>Resumed Evidence Lane Restored</strong><code class=\"history-chip history-chip-{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_class', 'steady')))}\">{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_label', 'resumed evidence lane restored')))}</code><span>{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_summary', '')))}</span></div>"
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_active = (
            f"<div class='preview-row'><strong>Resumed Restored Evidence State</strong><code class=\"history-chip history-chip-{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_active_class', 'steady')))}\">{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_active_label', 'resumed restored evidence active')))}</code><span>{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_active_summary', '')))}</span></div>"
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_active_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_active_selection = (
            f"<div class='preview-row'><strong>Resumed Restored Evidence Target</strong><code class=\"history-chip history-chip-{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_active_selection_class', 'steady')))}\">{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_active_selection_label', 'resumed restored evidence target active')))}</code><span>{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_active_selection_summary', '')))}</span></div>"
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_active_selection_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return = (
            f"<div class='preview-row'><strong>Resumed Restored Evidence Lane Resumed</strong><code class=\"history-chip history-chip-{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_class', 'steady')))}\">{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_label', 'resumed restored evidence lane resumed')))}</code><span>{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_summary', '')))}</span></div>"
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_active = (
            f"<div class='preview-row'><strong>Resumed Restored Evidence Focus State</strong><code class=\"history-chip history-chip-{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_active_class', 'steady')))}\">{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_active_label', 'resumed restored evidence focus active')))}</code><span>{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_active_summary', '')))}</span></div>"
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_active_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_active_selection = (
            f"<div class='preview-row'><strong>Resumed Restored Focus Target</strong><code class=\"history-chip history-chip-{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_active_selection_class', 'steady')))}\">{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_active_selection_label', 'resumed restored focus target active')))}</code><span>{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_active_selection_summary', '')))}</span></div>"
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_active_selection_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return = (
            f"<div class='preview-row'><strong>Resumed Restored Focus Lane Restored</strong><code class=\"history-chip history-chip-{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_class', 'steady')))}\">{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_label', 'resumed restored focus lane restored')))}</code><span>{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_summary', '')))}</span></div>"
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return = (
            f"<div class='preview-row'><strong>Resumed Restored Focus Return Confirmed</strong><code class=\"history-chip history-chip-{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_class', 'steady')))}\">{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_label', 'resumed restored focus return confirmed')))}</code><span>{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_summary', '')))}</span></div>"
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_active = (
            f"<div class='preview-row'><strong>Confirmed Resumed Restored Focus Target</strong><code class=\"history-chip history-chip-{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_active_class', 'steady')))}\">{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_active_label', 'confirmed resumed restored focus target active')))}</code><span>{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_active_summary', '')))}</span></div>"
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_active_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return = (
            f"<div class='preview-row'><strong>Confirmed Resumed Restored Focus Restored</strong><code class=\"history-chip history-chip-{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_class', 'steady')))}\">{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_label', 'confirmed resumed restored focus restored')))}</code><span>{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_summary', '')))}</span></div>"
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_return_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_active = (
            f"<div class='preview-row'><strong>Reopened Confirmed Restored Focus Target</strong><code class=\"history-chip history-chip-{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_active_class', 'steady')))}\">{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_active_label', 'reopened confirmed restored focus target active')))}</code><span>{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_active_summary', '')))}</span></div>"
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_return_active_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return = (
            f"<div class='preview-row'><strong>Reopened Confirmed Restored Focus Restored</strong><code class=\"history-chip history-chip-{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_return_class', 'steady')))}\">{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_return_label', 'reopened confirmed restored focus restored')))}</code><span>{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_return_summary', '')))}</span></div>"
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_return_return_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_active = (
            f"<div class='preview-row'><strong>Reopened Reopened Confirmed Focus Target</strong><code class=\"history-chip history-chip-{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_return_active_class', 'steady')))}\">{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_return_active_label', 'reopened reopened confirmed focus target active')))}</code><span>{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_return_active_summary', '')))}</span></div>"
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_return_return_active_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return = (
            f"<div class='preview-row'><strong>Reopened Reopened Confirmed Focus Restored</strong><code class=\"history-chip history-chip-{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_return_return_class', 'steady')))}\">{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_return_return_label', 'reopened reopened confirmed focus restored')))}</code><span>{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_return_return_summary', '')))}</span></div>"
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_return_return_return_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_active = (
            f"<div class='preview-row'><strong>Reopened Reopened Reopened Confirmed Focus Target</strong><code class=\"history-chip history-chip-{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_return_return_active_class', 'steady')))}\">{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_return_return_active_label', 'reopened reopened reopened confirmed focus target active')))}</code><span>{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_return_return_active_summary', '')))}</span></div>"
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_return_return_return_active_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return = (
            f"<div class='preview-row'><strong>Reopened Reopened Reopened Confirmed Focus Restored</strong><code class=\"history-chip history-chip-{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_class', 'steady')))}\">{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_label', 'reopened reopened reopened confirmed focus restored')))}</code><span>{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_summary', '')))}</span></div>"
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_return_return_return_return_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_active = (
            f"<div class='preview-row'><strong>Reopened Reopened Reopened Reopened Confirmed Focus Target</strong><code class=\"history-chip history-chip-{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_active_class', 'steady')))}\">{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_active_label', 'reopened reopened reopened reopened confirmed focus target active')))}</code><span>{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_active_summary', '')))}</span></div>"
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_return_return_return_return_active_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_return = (
            f"<div class='preview-row'><strong>Reopened Reopened Reopened Reopened Confirmed Focus Restored</strong><code class=\"history-chip history-chip-{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_class', 'steady')))}\">{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_label', 'reopened reopened reopened reopened confirmed focus restored')))}</code><span>{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_summary', '')))}</span></div>"
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_return_active = (
            f"<div class='preview-row'><strong>Reopened Reopened Reopened Reopened Reopened Confirmed Focus Target</strong><code class=\"history-chip history-chip-{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_active_class', 'steady')))}\">{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_active_label', 'reopened reopened reopened reopened reopened confirmed focus target active')))}</code><span>{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_active_summary', '')))}</span></div>"
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_active_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_return_return = (
            f"<div class='preview-row'><strong>Reopened Reopened Reopened Reopened Reopened Confirmed Focus Restored</strong><code class=\"history-chip history-chip-{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_class', 'steady')))}\">{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_label', 'reopened reopened reopened reopened reopened confirmed focus restored')))}</code><span>{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_summary', '')))}</span></div>"
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return = (
            f"<div class='preview-row'><strong>Reopened Reopened Reopened Reopened Reopened Reopened Confirmed Focus Restored</strong><code class=\"history-chip history-chip-{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_class', 'steady')))}\">{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_label', 'reopened reopened reopened reopened reopened reopened confirmed focus restored')))}</code><span>{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_summary', '')))}</span></div>"
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_actions = (
            "<div class='action-row'>"
            + "".join(
                (
                    f'<button type="button" data-motion-artifact-snapshot-target-artifact-index="{esc(str(item.get("motion_artifact_index", "")))}">{esc(str(item.get("label", "Reopen Reopened Reopened Reopened Reopened Reopened Reopened Confirmed Focus Artifact")))}</button>'
                    if item.get("kind") == "artifact"
                    else f'<button type="button" data-motion-artifact-snapshot-target-timeline-index="{esc(str(item.get("timeline_event_index", "")))}">{esc(str(item.get("label", "Reopen Reopened Reopened Reopened Reopened Reopened Reopened Confirmed Focus Timeline")))}</button>'
                )
                for item in list(motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_buttons") or [])
                if item
            )
            + "</div>"
        ) if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_buttons") else ""
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_active = (
            f"<div class='preview-row'><strong>Reopened Reopened Reopened Reopened Reopened Reopened Confirmed Focus Target</strong><code class=\"history-chip history-chip-{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_active_class', 'steady')))}\">{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_active_label', 'reopened reopened reopened reopened reopened reopened confirmed focus target active')))}</code><span>{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_active_summary', '')))}</span></div>"
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_active_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_active_actions = (
            '<div class="action-row"><button type="button" data-motion-artifact-snapshot-reopened-reopened-reopened-reopened-reopened-reopened-confirmed-resumed-restored-focus-return="1">Return to Reopened Reopened Reopened Reopened Reopened Reopened Confirmed Focus</button></div>'
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_active_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_actions = (
            "<div class='action-row'>"
            + "".join(
                (
                    f'<button type="button" data-motion-artifact-snapshot-target-artifact-index="{esc(str(item.get("motion_artifact_index", "")))}">{esc(str(item.get("label", "Reopen Reopened Reopened Reopened Reopened Reopened Confirmed Focus Artifact")))}</button>'
                    if item.get("kind") == "artifact"
                    else f'<button type="button" data-motion-artifact-snapshot-target-timeline-index="{esc(str(item.get("timeline_event_index", "")))}">{esc(str(item.get("label", "Reopen Reopened Reopened Reopened Reopened Reopened Confirmed Focus Timeline")))}</button>'
                )
                for item in list(motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_buttons") or [])
                if item
            )
            + "</div>"
        ) if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_buttons") else ""
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_active = (
            f"<div class='preview-row'><strong>Reopened Reopened Reopened Reopened Reopened Reopened Reopened Confirmed Focus Target</strong><code class=\"history-chip history-chip-{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_active_class', 'steady')))}\">{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_active_label', 'reopened reopened reopened reopened reopened reopened reopened confirmed focus target active')))}</code><span>{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_active_summary', '')))}</span></div>"
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_active_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return = (
            f"<div class='preview-row'><strong>Reopened Reopened Reopened Reopened Reopened Reopened Reopened Confirmed Focus Restored</strong><code class=\"history-chip history-chip-{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_class', 'steady')))}\">{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_label', 'reopened reopened reopened reopened reopened reopened reopened confirmed focus restored')))}</code><span>{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_summary', '')))}</span></div>"
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_actions = (
            "<div class='action-row'>"
            + "".join(
                (
                    f'<button type="button" data-motion-artifact-snapshot-target-artifact-index="{esc(str(item.get("motion_artifact_index", "")))}">{esc(str(item.get("label", "Reopen Reopened Reopened Reopened Reopened Reopened Reopened Reopened Confirmed Focus Artifact")))}</button>'
                    if item.get("kind") == "artifact"
                    else f'<button type="button" data-motion-artifact-snapshot-target-timeline-index="{esc(str(item.get("timeline_event_index", "")))}">{esc(str(item.get("label", "Reopen Reopened Reopened Reopened Reopened Reopened Reopened Reopened Confirmed Focus Timeline")))}</button>'
                )
                for item in list(motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_buttons") or [])
                if item
            )
            + "</div>"
        ) if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_buttons") else ""
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_active = (
            f"<div class='preview-row'><strong>Reopened Reopened Reopened Reopened Reopened Reopened Reopened Reopened Confirmed Focus Target</strong><code class=\"history-chip history-chip-{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_active_class', 'steady')))}\">{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_active_label', 'reopened reopened reopened reopened reopened reopened reopened reopened confirmed focus target active')))}</code><span>{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_active_summary', '')))}</span></div>"
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_active_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_active_actions = (
            '<div class="action-row"><button type="button" data-motion-artifact-snapshot-reopened-reopened-reopened-reopened-reopened-reopened-reopened-reopened-confirmed-resumed-restored-focus-return="1">Return to Reopened Reopened Reopened Reopened Reopened Reopened Reopened Reopened Confirmed Focus</button></div>'
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_active_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return = (
            f"<div class='preview-row'><strong>Reopened Reopened Reopened Reopened Reopened Reopened Reopened Reopened Confirmed Focus Restored</strong><code class=\"history-chip history-chip-{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_class', 'steady')))}\">{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_label', 'reopened reopened reopened reopened reopened reopened reopened reopened confirmed focus restored')))}</code><span>{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_summary', '')))}</span></div>"
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_actions = (
            "<div class='action-row'>"
            + "".join(
                (
                    f'<button type="button" data-motion-artifact-snapshot-target-artifact-index="{esc(str(item.get("motion_artifact_index", "")))}">{esc(str(item.get("label", "Reopen Reopened Reopened Reopened Reopened Reopened Reopened Reopened Confirmed Focus Artifact")))}</button>'
                    if item.get("kind") == "artifact"
                    else f'<button type="button" data-motion-artifact-snapshot-target-timeline-index="{esc(str(item.get("timeline_event_index", "")))}">{esc(str(item.get("label", "Reopen Reopened Reopened Reopened Reopened Reopened Reopened Reopened Confirmed Focus Timeline")))}</button>'
                )
                for item in list(motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_buttons") or [])
                if item
            )
            + "</div>"
        ) if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_buttons") else ""
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active = (
            f"<div class='preview-row'><strong>Reopened Reopened Reopened Reopened Reopened Reopened Reopened Reopened Reopened Confirmed Focus Target</strong><code class=\"history-chip history-chip-{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_class', 'steady')))}\">{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_label', 'reopened reopened reopened reopened reopened reopened reopened reopened reopened confirmed focus target active')))}</code><span>{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_summary', '')))}</span></div>"
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_actions = (
            '<div class="action-row"><button type="button" data-motion-artifact-snapshot-reopened-reopened-reopened-reopened-reopened-reopened-reopened-reopened-reopened-confirmed-resumed-restored-focus-return="1">Return to Reopened Reopened Reopened Reopened Reopened Reopened Reopened Reopened Reopened Confirmed Focus</button></div>'
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return = (
            f"<div class='preview-row'><strong>Reopened Reopened Reopened Reopened Reopened Reopened Reopened Reopened Reopened Confirmed Focus Restored</strong><code class=\"history-chip history-chip-{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_class', 'steady')))}\">{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_label', 'reopened reopened reopened reopened reopened reopened reopened reopened reopened confirmed focus restored')))}</code><span>{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_summary', '')))}</span></div>"
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_actions = (
            "<div class='action-row'>"
            + "".join(
                (
                    f'<button type="button" data-motion-artifact-snapshot-target-artifact-index="{esc(str(item.get("motion_artifact_index", "")))}">{esc(str(item.get("label", "Reopen Reopened Reopened Reopened Reopened Reopened Reopened Reopened Reopened Confirmed Focus Artifact")))}</button>'
                    if item.get("kind") == "artifact"
                    else f'<button type="button" data-motion-artifact-snapshot-target-timeline-index="{esc(str(item.get("timeline_event_index", "")))}">{esc(str(item.get("label", "Reopen Reopened Reopened Reopened Reopened Reopened Reopened Reopened Reopened Confirmed Focus Timeline")))}</button>'
                )
                for item in list(motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_buttons") or [])
                if item
            )
            + "</div>"
        ) if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_buttons") else ""
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active = (
            f"<div class='preview-row'><strong>Reopened Reopened Reopened Reopened Reopened Reopened Reopened Reopened Reopened Reopened Confirmed Focus Target</strong><code class=\"history-chip history-chip-{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_class', 'steady')))}\">{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_label', 'reopened reopened reopened reopened reopened reopened reopened reopened reopened reopened confirmed focus target active')))}</code><span>{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_summary', '')))}</span></div>"
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_actions = (
            '<div class="action-row"><button type="button" data-motion-artifact-snapshot-reopened-reopened-reopened-reopened-reopened-reopened-reopened-reopened-reopened-reopened-confirmed-resumed-restored-focus-return="1">Return to Reopened Reopened Reopened Reopened Reopened Reopened Reopened Reopened Reopened Reopened Confirmed Focus</button></div>'
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return = (
            f"<div class='preview-row'><strong>Reopened Reopened Reopened Reopened Reopened Reopened Reopened Reopened Reopened Reopened Confirmed Focus Restored</strong><code class=\"history-chip history-chip-{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_class', 'steady')))}\">{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_label', 'reopened reopened reopened reopened reopened reopened reopened reopened reopened reopened confirmed focus restored')))}</code><span>{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_summary', '')))}</span></div>"
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_actions = (
            "<div class='action-row'>"
            + "".join(
                (
                    f'<button type="button" data-motion-artifact-snapshot-target-artifact-index="{esc(str(item.get("motion_artifact_index", "")))}">{esc(str(item.get("label", "Reopen Reopened Reopened Reopened Reopened Reopened Reopened Reopened Reopened Reopened Confirmed Focus Artifact")))}</button>'
                    if item.get("kind") == "artifact"
                    else f'<button type="button" data-motion-artifact-snapshot-target-timeline-index="{esc(str(item.get("timeline_event_index", "")))}">{esc(str(item.get("label", "Reopen Reopened Reopened Reopened Reopened Reopened Reopened Reopened Reopened Reopened Confirmed Focus Timeline")))}</button>'
                )
                for item in list(motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_buttons") or [])
                if item
            )
            + "</div>"
        ) if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_buttons") else ""
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_restored_target = (
            f"<div class='preview-row'><strong>Reopened Reopened Reopened Reopened Reopened Reopened Reopened Reopened Reopened Reopened Confirmed Focus Restored Target</strong><code class=\"history-chip history-chip-{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_class', 'steady')))}\">{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_label', 'reopened reopened reopened reopened reopened reopened reopened reopened reopened reopened restored target pending')))}</code><span>{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_summary', '')))}</span></div>"
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_label") and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_last_followed = (
            f"<div class='preview-row'><strong>Last Followed Restored Target</strong><code class=\"history-chip history-chip-{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('restored_target_last_followed_class', 'steady')))}\">{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('restored_target_last_followed_label', '')))}</code><span>{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('restored_target_last_followed_summary', '')))}</span></div>"
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("restored_target_last_followed_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_restored_target_actions = (
            "<div class='action-row'>"
            + "".join(
                (
                    f'<button type="button" data-motion-artifact-snapshot-target-artifact-index="{esc(str(item.get("motion_artifact_index", "")))}">Follow Restored Target Artifact</button>'
                    if item.get("kind") == "artifact"
                    else f'<button type="button" data-motion-artifact-snapshot-target-timeline-index="{esc(str(item.get("timeline_event_index", "")))}">Follow Restored Target Timeline</button>'
                )
                for item in list(motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_buttons") or [])
                if item
            )
            + "</div>"
        ) if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_label") and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_buttons") else ""
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active = (
            f"<div class='preview-row'><strong>Reopened Reopened Reopened Reopened Reopened Reopened Reopened Reopened Reopened Reopened Reopened Confirmed Focus Target</strong><code class=\"history-chip history-chip-{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_class', 'steady')))}\">{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_label', 'reopened reopened reopened reopened reopened reopened reopened reopened reopened reopened reopened confirmed focus target active')))}</code><span>{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_summary', '')))}</span></div>"
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_restored_target_actions = (
            '<div class="action-row"><button type="button" data-motion-artifact-snapshot-restored-target-return="1">Return to Restored Target Proof</button></div>'
            if motion_artifact_focus_posture_snapshot_reason_focus
            and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_label")
            and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_actions = (
            '<div class="action-row"><button type="button" data-motion-artifact-snapshot-reopened-reopened-reopened-reopened-reopened-reopened-reopened-reopened-reopened-reopened-reopened-confirmed-resumed-restored-focus-return="1">Return to Reopened Reopened Reopened Reopened Reopened Reopened Reopened Reopened Reopened Reopened Reopened Confirmed Focus</button></div>'
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_active_actions = (
            '<div class="action-row"><button type="button" data-motion-artifact-snapshot-reopened-reopened-reopened-reopened-reopened-reopened-reopened-confirmed-resumed-restored-focus-return="1">Return to Reopened Reopened Reopened Reopened Reopened Reopened Reopened Confirmed Focus</button></div>'
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_active_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_return_active_actions = (
            '<div class="action-row"><button type="button" data-motion-artifact-snapshot-reopened-reopened-reopened-reopened-reopened-confirmed-resumed-restored-focus-return="1">Return to Reopened Reopened Reopened Reopened Reopened Confirmed Focus</button></div>'
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_active_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_return_actions = (
            "<div class='action-row'>"
            + "".join(
                (
                    f'<button type="button" data-motion-artifact-snapshot-target-artifact-index="{esc(str(item.get("motion_artifact_index", "")))}">{esc(str(item.get("label", "Reopen Reopened Reopened Reopened Reopened Confirmed Focus Artifact")))}</button>'
                    if item.get("kind") == "artifact"
                    else f'<button type="button" data-motion-artifact-snapshot-target-timeline-index="{esc(str(item.get("timeline_event_index", "")))}">{esc(str(item.get("label", "Reopen Reopened Reopened Reopened Reopened Confirmed Focus Timeline")))}</button>'
                )
                for item in list(motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_buttons") or [])
                if item
            )
            + "</div>"
        ) if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_buttons") else ""
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_active_actions = (
            '<div class="action-row"><button type="button" data-motion-artifact-snapshot-reopened-reopened-reopened-reopened-confirmed-resumed-restored-focus-return="1">Return to Reopened Reopened Reopened Reopened Confirmed Focus</button></div>'
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_return_return_return_return_active_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_actions = (
            "<div class='action-row'>"
            + "".join(
                (
                    f'<button type="button" data-motion-artifact-snapshot-target-artifact-index="{esc(str(item.get("motion_artifact_index", "")))}">{esc(str(item.get("label", "Reopen Reopened Reopened Reopened Confirmed Focus Artifact")))}</button>'
                    if item.get("kind") == "artifact"
                    else f'<button type="button" data-motion-artifact-snapshot-target-timeline-index="{esc(str(item.get("timeline_event_index", "")))}">{esc(str(item.get("label", "Reopen Reopened Reopened Reopened Confirmed Focus Timeline")))}</button>'
                )
                for item in list(motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_return_return_return_return_buttons") or [])
                if item
            )
            + "</div>"
        ) if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_return_return_return_return_buttons") else ""
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_active_actions = (
            '<div class="action-row"><button type="button" data-motion-artifact-snapshot-reopened-reopened-reopened-confirmed-resumed-restored-focus-return="1">Return to Reopened Reopened Reopened Confirmed Focus</button></div>'
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_return_return_return_active_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_actions = (
            "<div class='action-row'>"
            + "".join(
                (
                    f'<button type="button" data-motion-artifact-snapshot-target-artifact-index="{esc(str(item.get("motion_artifact_index", "")))}">{esc(str(item.get("label", "Reopen Reopened Reopened Confirmed Focus Artifact")))}</button>'
                    if item.get("kind") == "artifact"
                    else f'<button type="button" data-motion-artifact-snapshot-target-timeline-index="{esc(str(item.get("timeline_event_index", "")))}">{esc(str(item.get("label", "Reopen Reopened Reopened Confirmed Focus Timeline")))}</button>'
                )
                for item in list(motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_return_return_return_buttons") or [])
                if item
            )
            + "</div>"
        ) if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_return_return_return_buttons") else ""
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_active_actions = (
            '<div class="action-row"><button type="button" data-motion-artifact-snapshot-reopened-reopened-confirmed-resumed-restored-focus-return="1">Return to Reopened Reopened Confirmed Focus</button></div>'
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_return_return_active_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_actions = (
            "<div class='action-row'>"
            + "".join(
                (
                    f'<button type="button" data-motion-artifact-snapshot-target-artifact-index="{esc(str(item.get("motion_artifact_index", "")))}">{esc(str(item.get("label", "Reopen Reopened Confirmed Focus Artifact")))}</button>'
                    if item.get("kind") == "artifact"
                    else f'<button type="button" data-motion-artifact-snapshot-target-timeline-index="{esc(str(item.get("timeline_event_index", "")))}">{esc(str(item.get("label", "Reopen Reopened Confirmed Focus Timeline")))}</button>'
                )
                for item in list(motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_return_return_buttons") or [])
                if item
            )
            + "</div>"
        ) if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_return_return_buttons") else ""
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_active_actions = (
            '<div class="action-row"><button type="button" data-motion-artifact-snapshot-reopened-confirmed-resumed-restored-focus-return="1">Return to Reopened Confirmed Restored Focus</button></div>'
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_return_active_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_actions = (
            "<div class='action-row'>"
            + "".join(
                (
                    f'<button type="button" data-motion-artifact-snapshot-target-artifact-index="{esc(str(item.get("motion_artifact_index", "")))}">{esc(str(item.get("label", "Reopen Confirmed Restored Focus Artifact")))}</button>'
                    if item.get("kind") == "artifact"
                    else f'<button type="button" data-motion-artifact-snapshot-target-timeline-index="{esc(str(item.get("timeline_event_index", "")))}">{esc(str(item.get("label", "Reopen Confirmed Restored Focus Timeline")))}</button>'
                )
                for item in list(motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_return_buttons") or [])
                if item
            )
            + "</div>"
        ) if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_return_buttons") else ""
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_active_actions = (
            '<div class="action-row"><button type="button" data-motion-artifact-snapshot-confirmed-resumed-restored-focus-return="1">Return to Confirmed Resumed Restored Focus</button></div>'
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_active_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_actions = (
            "<div class='action-row'>"
            + "".join(
                (
                    f'<button type="button" data-motion-artifact-snapshot-target-artifact-index="{esc(str(item.get("motion_artifact_index", "")))}">{esc(str(item.get("label", "Open Confirmed Resumed Restored Focus Artifact")))}</button>'
                    if item.get("kind") == "artifact"
                    else f'<button type="button" data-motion-artifact-snapshot-target-timeline-index="{esc(str(item.get("timeline_event_index", "")))}">{esc(str(item.get("label", "Open Confirmed Resumed Restored Focus Timeline")))}</button>'
                )
                for item in list(motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_buttons") or [])
                if item
            )
            + "</div>"
        ) if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_return_buttons") else ""
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_active = (
            f"<div class='preview-row'><strong>Resumed Restored Focus Restored Target</strong><code class=\"history-chip history-chip-{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_active_class', 'steady')))}\">{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_active_label', 'resumed restored focus restored target active')))}</code><span>{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_return_return_active_summary', '')))}</span></div>"
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_active_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_actions = (
            "<div class='action-row'>"
            + "".join(
                (
                    f'<button type="button" data-motion-artifact-snapshot-target-artifact-index="{esc(str(item.get("motion_artifact_index", "")))}">{esc(str(item.get("label", "Reopen Resumed Restored Focus Artifact")))}</button>'
                    if item.get("kind") == "artifact"
                    else f'<button type="button" data-motion-artifact-snapshot-target-timeline-index="{esc(str(item.get("timeline_event_index", "")))}">{esc(str(item.get("label", "Reopen Resumed Restored Focus Timeline")))}</button>'
                )
                for item in list(motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_buttons") or [])
                if item
            )
            + "</div>"
        ) if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_return_buttons") else ""
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_active_selection_actions = (
            '<div class="action-row"><button type="button" data-motion-artifact-snapshot-resumed-restored-focus-return="1">Return to Resumed Restored Focus</button></div>'
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_active_selection_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_active_actions = (
            "<div class='action-row'>"
            + "".join(
                (
                    f'<button type="button" data-motion-artifact-snapshot-target-artifact-index="{esc(str(item.get("motion_artifact_index", "")))}">{esc(str(item.get("label", "Open Resumed Restored Focus Artifact")))}</button>'
                    if item.get("kind") == "artifact"
                    else f'<button type="button" data-motion-artifact-snapshot-target-timeline-index="{esc(str(item.get("timeline_event_index", "")))}">{esc(str(item.get("label", "Open Resumed Restored Focus Timeline")))}</button>'
                )
                for item in list(motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_active_buttons") or [])
                if item
            )
            + "</div>"
        ) if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_active_buttons") else ""
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_active_selection_actions = (
            '<div class="action-row"><button type="button" data-motion-artifact-snapshot-resumed-restored-return="1">Return to Resumed Restored Evidence</button></div>'
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_active_selection_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_active_actions = (
            "<div class='action-row'>"
            + "".join(
                (
                    f'<button type="button" data-motion-artifact-snapshot-target-artifact-index="{esc(str(item.get("motion_artifact_index", "")))}">{esc(str(item.get("label", "Open Resumed Restored Evidence Artifact")))}</button>'
                    if item.get("kind") == "artifact"
                    else f'<button type="button" data-motion-artifact-snapshot-target-timeline-index="{esc(str(item.get("timeline_event_index", "")))}">{esc(str(item.get("label", "Open Resumed Restored Evidence Timeline")))}</button>'
                )
                for item in list(motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_active_buttons") or [])
                if item
            )
            + "</div>"
        ) if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_active_buttons") else ""
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_active_selection_actions = (
            '<div class="action-row"><button type="button" data-motion-artifact-snapshot-resumed-return="1">Return to Resumed Evidence</button></div>'
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_active_selection_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_active_actions = (
            "<div class='action-row'>"
            + "".join(
                (
                    f'<button type="button" data-motion-artifact-snapshot-target-artifact-index="{esc(str(item.get("motion_artifact_index", "")))}">{esc(str(item.get("label", "Open Resumed Evidence Artifact")))}</button>'
                    if item.get("kind") == "artifact"
                    else f'<button type="button" data-motion-artifact-snapshot-target-timeline-index="{esc(str(item.get("timeline_event_index", "")))}">{esc(str(item.get("label", "Open Resumed Evidence Timeline")))}</button>'
                )
                for item in list(motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_active_buttons") or [])
                if item
            )
            + "</div>"
        ) if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_active_buttons") else ""
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_actions = (
            f"<div class='action-row'>{f'<button type=\"button\" class=\"history-chip history-chip-' + esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_source_class', 'artifact'))) + '\" data-motion-artifact-snapshot-restored-reason=\"1\">' + esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_source_label', 'stored evidence'))) + '</button>' if motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_source_label') else ''}{f'<button type=\"button\" data-motion-artifact-snapshot-restored-reason=\"1\">' + esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_button_label', 'Inspect Resumed Evidence'))) + '</button>' if motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_button_label') else ''}</div>"
            if motion_artifact_focus_posture_snapshot_reason_focus
            and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_label")
            and (
                motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_source_label")
                or motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_button_label")
            )
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_actions = (
            f"<div class='action-row'>{f'<button type=\"button\" class=\"history-chip history-chip-' + esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_source_class', 'artifact'))) + '\" data-motion-artifact-snapshot-restored-reason=\"1\">' + esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_source_label', 'stored evidence'))) + '</button>' if motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_source_label') else ''}{f'<button type=\"button\" data-motion-artifact-snapshot-restored-reason=\"1\">' + esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_button_label', 'Inspect Resumed Evidence'))) + '</button>' if motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_button_label') else ''}</div>"
            if motion_artifact_focus_posture_snapshot_reason_focus
            and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_label")
            and (
                motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_source_label")
                or motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_button_label")
            )
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_actions = (
            f"<div class='action-row'>{f'<button type=\"button\" class=\"history-chip history-chip-' + esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_source_class', 'artifact'))) + '\" data-motion-artifact-snapshot-resumed-restored-reason=\"1\">' + esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_source_label', 'stored evidence'))) + '</button>' if motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_source_label') else ''}{f'<button type=\"button\" data-motion-artifact-snapshot-resumed-restored-reason=\"1\">' + esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_button_label', 'Inspect Resumed Restored Evidence'))) + '</button>' if motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_resumed_return_return_button_label') else ''}</div>"
            if motion_artifact_focus_posture_snapshot_reason_focus
            and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_return_label")
            and (
                motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_source_label")
                or motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_return_return_button_label")
            )
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_active_selection_actions = (
            '<div class="action-row"><button type="button" data-motion-artifact-snapshot-restored-return="1">Return to Restored Evidence</button></div>'
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_active_selection_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_active_actions = (
            "<div class='action-row'>"
            + "".join(
                (
                    f'<button type="button" data-motion-artifact-snapshot-target-artifact-index="{esc(str(item.get("motion_artifact_index", "")))}">{esc(str(item.get("label", "Open Restored Evidence Artifact")))}</button>'
                    if item.get("kind") == "artifact"
                    else f'<button type="button" data-motion-artifact-snapshot-target-timeline-index="{esc(str(item.get("timeline_event_index", "")))}">{esc(str(item.get("label", "Open Restored Evidence Timeline")))}</button>'
                )
                for item in list(motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_active_buttons") or [])
                if item
            )
            + "</div>"
        ) if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_active_buttons") else ""
        motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_actions = (
            f"<div class='action-row'>{f'<button type=\"button\" class=\"history-chip history-chip-' + esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_source_class', 'artifact'))) + '\" data-motion-artifact-snapshot-restored-reason=\"1\">' + esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_source_label', 'stored evidence'))) + '</button>' if motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_source_label') else ''}{f'<button type=\"button\" data-motion-artifact-snapshot-restored-reason=\"1\">' + esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_button_label', 'Inspect Reopened Evidence'))) + '</button>' if motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_reason_button_label') else ''}</div>"
            if motion_artifact_focus_posture_snapshot_reason_focus
            and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_resumed_label")
            and (
                motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_source_label")
                or motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_button_label")
            )
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_active_selection_actions = (
            '<div class="action-row"><button type="button" data-motion-artifact-snapshot-return="1">Return to Evidence Focus</button></div>'
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_active_selection_label")
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_return_reason_active_actions = (
            "<div class='action-row'>"
            + "".join(
                (
                    f'<button type="button" data-motion-artifact-snapshot-target-artifact-index="{esc(str(item.get("motion_artifact_index", "")))}">{esc(str(item.get("label", "Open Evidence Artifact")))}</button>'
                    if item.get("kind") == "artifact"
                    else f'<button type="button" data-motion-artifact-snapshot-target-timeline-index="{esc(str(item.get("timeline_event_index", "")))}">{esc(str(item.get("label", "Open Evidence Timeline")))}</button>'
                )
                for item in list(motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_active_buttons") or [])
                if item
            )
            + "</div>"
        ) if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_reason_active_buttons") else ""
        motion_artifact_focus_posture_snapshot_focus_return_confirmation_actions = (
            f'<div class="action-row"><button type="button" data-motion-artifact-history-index="{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_index", "")))}">{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_label", "Reopen Latest Outcome")))}</button>{motion_artifact_focus_posture_snapshot_focus_return_reason}{motion_artifact_focus_posture_snapshot_focus_return_reason_source}{motion_artifact_focus_posture_snapshot_focus_return_reason_button}</div>'
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_confirmation_label") and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_index") is not None
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_context_actions = (
            "<div class='action-row'>"
            + "".join(
                (
                    f'<button type="button" data-motion-artifact-snapshot-reason="1">{esc(str(item.get("active_label") if item.get("active") else item.get("label", "Open Proof Lane")))}</button>'
                    if item.get("kind") == "proof"
                    else f'<button type="button" data-motion-artifact-history-index="{esc(str(item.get("history_index", "")))}">{esc(str(item.get("active_label") if item.get("active") else item.get("label", "Inspect Action")))}</button>'
                    if item.get("kind") == "history"
                    else f'<button type="button" data-timeline-index="{esc(str(item.get("timeline_event_index", "")))}">{esc(str(item.get("active_label") if item.get("active") else item.get("label", "Open Chronology Lane")))}</button>'
                    if item.get("kind") == "timeline"
                    else f'<button type="button" data-motion-artifact-snapshot-target-artifact-index="{esc(str(item.get("motion_artifact_index", "")))}">{esc(str(item.get("active_label") if item.get("active") else item.get("label", "Inspect Exact Artifact")))}</button>'
                    if item.get("kind") == "artifact"
                    else f'<button type="button" data-motion-artifact-snapshot-target-timeline-index="{esc(str(item.get("timeline_event_index", "")))}">{esc(str(item.get("active_label") if item.get("active") else item.get("label", "Inspect Matching Timeline")))}</button>'
                )
                for item in list(motion_artifact_focus_posture_snapshot_reason_focus.get("context_buttons") or [])
                if item
            )
            + "</div>"
        ) if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("context_buttons") else ""
        motion_artifact_focus_posture_snapshot_focus_return_action = (
            f"<div class='action-row'>"
            f"{f'<code class=\"history-chip history-chip-' + esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_origin_class', 'artifact'))) + '\">' + esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_origin_label', 'latest outcome'))) + '</code>' if motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_origin_label') else ''}"
            f"<button type=\"button\" data-motion-artifact-history-index=\"{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_index', '')))}\">{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('return_history_label', 'Reopen Latest Outcome')))}</button>"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_source}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_button}"
            f"</div>"
            if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("return_history_index") is not None
            else ""
        )
        motion_artifact_focus_posture_snapshot_focus_target_actions = (
            "<div class='action-row'>"
            + "".join(
                (
                    f'<button type="button" data-motion-artifact-snapshot-target-artifact-index="{esc(str(item.get("motion_artifact_index", "")))}">{esc(str(item.get("label", "Inspect Exact Artifact")))}</button>'
                    if item.get("kind") == "artifact"
                    else f'<button type="button" data-motion-artifact-snapshot-target-timeline-index="{esc(str(item.get("timeline_event_index", "")))}">{esc(str(item.get("label", "Inspect Matching Timeline")))}</button>'
                )
                for item in list(motion_artifact_focus_posture_snapshot_reason_focus.get("active_target_buttons") or [])
                if item
            )
            + "</div>"
        ) if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("active_target_buttons") else ""
        motion_artifact_focus_posture_snapshot_focus_pivots = (
            "<div class='action-row'>"
            + "".join(
                (
                    f'<button type="button" data-motion-artifact-history-index="{esc(str(item.get("history_index", "")))}">{esc(str(item.get("label", "Open Mutation")))}</button>'
                    if item.get("kind") == "history"
                    else f'<button type="button" data-timeline-index="{esc(str(item.get("timeline_event_index", "")))}">{esc(str(item.get("label", "Open Chronology")))}</button>'
                )
                for item in list(motion_artifact_focus_posture_snapshot_reason_focus.get("pivot_buttons") or [])
                if item
            )
            + "</div>"
        ) if motion_artifact_focus_posture_snapshot_reason_focus and motion_artifact_focus_posture_snapshot_reason_focus.get("pivot_buttons") else ""
        motion_artifact_focus_posture_display = (
            f"<div class='preview-row'><strong>Current Posture</strong>"
            f"{('<code class=\"history-chip history-chip-' + esc(motion_artifact_focus_posture_badge_class) + '\">' + esc(motion_artifact_focus_posture_badge_label) + '</code>') if motion_artifact_focus_posture_badge_label else ''}"
            f"{('<code class=\"history-chip history-chip-' + esc(motion_artifact_focus_posture_state_class) + '\">' + esc(motion_artifact_focus_posture_state_label) + '</code>') if motion_artifact_focus_posture_state_label else ''}"
            f"<code>{esc(motion_artifact_focus_posture_summary)}</code>"
            f"{f'<span>{esc(motion_artifact_focus_posture_hint)}</span>' if motion_artifact_focus_posture_hint else ''}"
            f"{f'<span>{esc(motion_artifact_focus_posture_outcome_line)}</span>' if motion_artifact_focus_posture_outcome_line else ''}"
            f"{f'<span>{esc(motion_artifact_focus_posture_snapshot_cue)}</span>' if motion_artifact_focus_posture_snapshot_cue else ''}"
            f"{f'<span>Suggested next: {esc(motion_artifact_focus_posture_suggested_action_label)}</span>' if motion_artifact_focus_posture_suggested_action else ''}"
            f"{motion_artifact_focus_posture_suggested_action_button}"
            f"{f'<span>Reopened next: {esc(motion_artifact_focus_posture_snapshot_action_label)}</span>' if motion_artifact_focus_posture_snapshot_action else ''}"
            f"{f'<span>Why reopened next: {esc(motion_artifact_focus_posture_snapshot_reason)}</span>' if motion_artifact_focus_posture_snapshot_reason else ''}"
            f"{motion_artifact_focus_posture_snapshot_return_button}"
            f"{motion_artifact_focus_posture_snapshot_reason_button}"
            f"{motion_artifact_focus_posture_snapshot_action_button}"
            f"{f'<button type=\"button\" data-motion-artifact-history-index=\"{esc(str(motion_artifact_focus_posture_outcome_index))}\">Inspect Last Action</button>' if motion_artifact_focus_posture_outcome_index is not None else ''}"
            f"</div>"
        )
        motion_artifact_focus_posture_snapshot_focus_display = (
            f"<div class='preview-subsection'><strong>{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('title', 'Reopened Proof Focus')))}</strong>"
            f"<span>{esc(str(motion_artifact_focus_posture_snapshot_reason_focus.get('summary', 'No reopened proof focus selected yet.')))}</span>"
            f"{motion_artifact_focus_posture_snapshot_focus_path}"
            f"{motion_artifact_focus_posture_snapshot_focus_summary}"
            f"{motion_artifact_focus_posture_snapshot_focus_path_summary}"
            f"{motion_artifact_focus_posture_snapshot_focus_target}"
            f"{motion_artifact_focus_posture_snapshot_focus_context}"
            f"{motion_artifact_focus_posture_snapshot_focus_context_selection}"
            f"{motion_artifact_focus_posture_snapshot_focus_context_selection_actions}"
            f"{motion_artifact_focus_posture_snapshot_focus_context_selection_confirmation}"
            f"{motion_artifact_focus_posture_snapshot_focus_context_selection_confirmation_actions}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_confirmation}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_confirmation_actions}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_active}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_active_selection}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_active}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_active_selection}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_active}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_active_selection}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_active}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_active_selection}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_active}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_active_selection}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_active}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_active}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_active}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_active}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_active}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_return}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_return_active}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_return_return}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_actions}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_active}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_actions}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_active}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_active_actions}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_actions}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_actions}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_actions}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_actions}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_actions}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_actions}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_restored_target}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_last_followed}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_restored_target_actions}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_restored_target_actions}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_active}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_active_actions}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_actions}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_return_active_actions}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_return_actions}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_active_actions}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_return_actions}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_active_actions}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_return_actions}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_active_actions}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_return_actions}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_active_actions}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_return_actions}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_active_actions}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_return_actions}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_active}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_return_actions}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_active_selection_actions}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_active_actions}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_return_actions}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_active_selection_actions}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_active_actions}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_active_selection_actions}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_active_actions}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_actions}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_return_return_actions}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_active_selection_actions}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_active_actions}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_resumed_actions}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_active_selection_actions}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_reason_active_actions}"
            f"{motion_artifact_focus_posture_snapshot_focus_context_actions}"
            f"{motion_artifact_focus_posture_snapshot_focus_return_action}"
            f"{motion_artifact_focus_posture_snapshot_focus_target_actions}"
            f"{motion_artifact_focus_posture_snapshot_focus_pivots}"
            f"{preview_rows(list(motion_artifact_focus_posture_snapshot_reason_focus.get('rows') or []), 'Proof Focus', 'span') if motion_artifact_focus_posture_snapshot_reason_focus else '<span>No reopened proof focus selected yet.</span>'}"
            f"{motion_artifact_focus_posture_snapshot_focus_actions}"
            f"</div>"
        )
        motion_artifact_focus_display = (
            f"<div class='preview-subsection'><strong>{esc(motion_artifact_focus_title)}</strong>"
            f"<span>{esc(motion_artifact_focus_summary)}</span>"
            f"{motion_artifact_focus_posture_display}"
            f"{motion_artifact_focus_posture_snapshot_focus_display}"
            f"{preview_rows(motion_artifact_focus_sections, 'Artifact Detail', 'span') if motion_artifact_focus_sections else '<span>No localized artifact detail captured yet.</span>'}"
            f"<div class='preview-subsection'><strong>Artifact Mutation</strong><span>{esc(motion_artifact_focus_delta_summary)}</span>"
            f"{preview_rows(motion_artifact_focus_delta_sections, 'Artifact Mutation', 'span') if motion_artifact_focus_delta_sections else '<span>No localized artifact mutation rows captured yet.</span>'}"
            f"</div>"
            f"<div class='preview-subsection'><strong>Artifact Proof Excerpts</strong>"
            f"{''.join(f'<div class=\"preview-row\"><strong>Excerpt</strong><code>{esc(str(item))}</code></div>' for item in motion_artifact_focus_excerpts if item) if motion_artifact_focus_excerpts else '<span>No localized artifact proof excerpts captured yet.</span>'}"
            f"</div>"
            f"<div class='preview-subsection'><strong>Artifact Proof Compare</strong><span>{esc(motion_artifact_focus_proof_compare_summary)}</span>"
            f"{preview_rows(motion_artifact_focus_proof_compare_rows, 'Artifact Proof Compare', 'span') if motion_artifact_focus_proof_compare_rows else '<span>No localized artifact proof comparison rows captured yet.</span>'}"
            f"</div>"
            f"<div class='preview-subsection'><strong>Artifact Recent Actions</strong><span>{esc(motion_artifact_focus_history_summary)}</span>"
            f"{f'<span>{esc(motion_artifact_focus_history_meta)}</span>' if motion_artifact_focus_history_meta else ''}"
            f"{motion_artifact_focus_history_display}"
            f"{f'<span>{esc(motion_artifact_focus_history_note)}</span>' if motion_artifact_focus_history_note else ''}"
            f"</div>"
            f"{f'<div class=\"action-row\">{motion_artifact_focus_action_buttons}</div>' if motion_artifact_focus_action_buttons else ''}"
            f"</div>"
        )
        event_action_buttons = "".join(
            (
                f'<button type="button" data-endpoint="{esc(item.get("endpoint", ""))}"'
                f' data-method="{esc(item.get("method", "POST"))}"'
                f'{f" data-body={json.dumps(item.get("body", ""))!r}" if item.get("body") else ""}>'
                f'{esc(item.get("label", item.get("action", "Act")))}</button>'
            )
            if str(item.get("endpoint", "")).strip()
            else f'<button type="button" data-event-action="{esc(item.get("action", ""))}">{esc(item.get("label", item.get("action", "Act")))}</button>'
            for item in selected_timeline_event_detail.get("action_buttons", [])
            if item
        ) or "<span>No direct event actions available.</span>"
        if event_preview_kind == "decision":
            decision_rows = preview_rows(event_preview_sections, "Decision", "code")
            decision_review_fields = preview_rows(approval_review_fields, "Field", "span")
            decision_preview_buttons = "".join(
                (
                    f'<button type="button" data-endpoint="{esc(item.get("endpoint", ""))}"'
                    f' data-method="{esc(item.get("method", "POST"))}"'
                    f'{f" data-body={json.dumps(item.get("body", ""))!r}" if item.get("body") else ""}>'
                    f'{esc(item.get("label", item.get("action", "Act")))}</button>'
                )
                if str(item.get("endpoint", "")).strip()
                else f'<button type="button" data-event-action="{esc(item.get("action", ""))}">{esc(item.get("label", item.get("action", "Act")))}</button>'
                for item in selected_timeline_event_detail.get("action_buttons", [])
                if item
            )
            event_preview_display = (
                f"<div class='preview-pane'><strong>{esc(event_preview_title)}</strong><span>{esc(event_preview_summary)}</span>"
                f"{decision_rows or default_preview_row(event_preview_title, event_preview_summary)}"
            )
            if decision_review_fields:
                event_preview_display += f"<div class='preview-subsection'><strong>Approval Review Fields</strong>{decision_review_fields}</div>"
            if approval_posture_fields:
                event_preview_display += (
                    "<div class='preview-subsection'><strong>Consent &amp; Readiness</strong>"
                    + preview_rows(approval_posture_fields, "Status", "span")
                    + "</div>"
                )
            if consequence_fields:
                event_preview_display += (
                    "<div class='preview-subsection'><strong>What Changed</strong>"
                    + preview_rows(consequence_fields, "Change", "span")
                    + "</div>"
                )
            if guidance_display:
                event_preview_display += guidance_display
            if decision_history_summary:
                event_preview_display += f"<div class='preview-subsection'><strong>Recent Approval History</strong><span>{esc(decision_history_summary)}</span></div>"
            if approval_review_summary:
                event_preview_display += f"<div class='preview-subsection'><strong>Approval Review Block</strong><span>{esc(approval_review_summary)}</span></div>"
            if decision_preview_buttons:
                event_preview_display += f"<div class='preview-subsection'><strong>Approval Controls</strong><div class='action-row'>{decision_preview_buttons}</div></div>"
            event_preview_display += "</div>"
        elif event_preview_kind == "notification":
            event_preview_display = preview_rows(event_preview_sections, "Notification", "span") or default_preview_row(event_preview_title, event_preview_summary)
            if notification_snapshot:
                event_preview_display += f"<div class='preview-subsection'><strong>Surfaced Snapshot</strong><span>{esc(notification_snapshot)}</span></div>"
            if guidance_display:
                event_preview_display += guidance_display
        elif event_preview_kind == "trace":
            event_preview_display = preview_rows(event_preview_sections, "Trace", "code") or default_preview_row(event_preview_title, event_preview_summary)
            if guidance_display:
                event_preview_display += guidance_display
        elif event_preview_kind == "open-loop":
            event_preview_display = preview_rows(event_preview_sections, "Open loop", "span") or default_preview_row(event_preview_title, event_preview_summary)
            if guidance_display:
                event_preview_display += guidance_display
        else:
            event_preview_display = preview_rows(event_preview_sections, "Preview", "span") or default_preview_row(event_preview_title, event_preview_summary)
        return "".join(
            [
                f"<li><strong>Selected Item</strong><span>{esc(detail_inspector.get('title', 'No item selected'))}</span></li>",
                f"<li><strong>Source</strong><span>{esc(detail_inspector.get('source_kind', 'none'))}</span></li>",
                f"<li><strong>Summary</strong><span>{esc(detail_inspector.get('summary', 'Select an item to inspect.'))}</span></li>",
                f"<li><strong>Owner</strong><span>{esc(detail_inspector.get('owner_agent', 'command-center'))}</span></li>",
                f"<li><strong>Status</strong><span>{esc(detail_inspector.get('domain', 'general'))} / {esc(detail_inspector.get('status', 'idle'))}</span></li>",
                f"<li><strong>Why Now</strong><span>{esc(detail_inspector.get('why_now', 'No current selection.'))}</span></li>",
                f"<li><strong>Next Action</strong><span>{esc(detail_inspector.get('next_action', 'Choose a surfaced item.'))}</span></li>",
                f"<li><strong>Review By</strong><span>{esc(detail_inspector.get('next_review_at', 'not scheduled'))}</span></li>",
                f"<li><strong>Autonomy</strong><span>{esc(detail_inspector.get('autonomy_summary', 'No active item selected.'))}</span></li>",
                f"<li><strong>Evidence</strong><span>{esc(evidence_display)}</span></li>",
                f"<li><strong>Last Decision</strong><span>{esc(detail_inspector.get('last_decision_summary', 'No prior decision attached.'))}</span></li>",
                f"<li><strong>Motion Proof Summary</strong><span>{esc(detail_inspector.get('motion_proof_summary', 'No motion-specific proof selected.'))}</span></li>",
                f"<li><strong>Motion Proof Source</strong><span>{esc(detail_inspector.get('motion_proof_source', 'No motion-specific proof source attached.'))}</span></li>",
                f"<li><strong>Motion Proof Snapshot</strong><div class='preview-subsection'>{motion_proof_display}</div></li>",
                f"<li><strong>Motion Proof View</strong>{motion_proof_panel_display}</li>",
                f"<li><strong>Motion Proof Excerpts</strong><div class='preview-subsection'>{motion_proof_excerpt_display}</div></li>",
                f"<li><strong>Motion Proof Artifacts</strong>{motion_proof_artifact_display}</li>",
                f"<li><strong>Motion Artifact Focus</strong>{motion_artifact_focus_display}</li>",
                f"<li><strong>Change Summary</strong><span>{esc(detail_inspector.get('change_summary', 'No action diff captured yet.'))}</span></li>",
                f"<li><strong>Action Result</strong><span>{esc(detail_inspector.get('action_result_summary', 'No action result captured yet.'))}</span></li>",
                f"<li><strong>Why Changed</strong><span>{esc(detail_inspector.get('change_evidence_summary', 'No post-action evidence captured yet.'))}</span></li>",
                f"<li><strong>Field Deltas</strong><span>{esc(detail_inspector.get('field_delta_summary', 'No field deltas captured yet.'))}</span></li>",
                f"<li><strong>Contract Deltas</strong><span>{esc(detail_inspector.get('contract_delta_summary', 'No contract deltas captured yet.'))}</span></li>",
                f"<li><strong>Derived Deltas</strong><span>{esc(detail_inspector.get('derived_delta_summary', 'No derived deltas captured yet.'))}</span></li>",
                f"<li><strong>Timeline &amp; History</strong><span>{esc(timeline_display)}</span><div class='action-row'>{timeline_buttons}</div></li>",
                f"<li><strong>Selected Timeline Event</strong><span>{esc(selected_timeline_display)}</span></li>",
                f"<li><strong>Timeline Event Evidence</strong><span>{esc(event_evidence_display)}</span></li>",
                f"<li><strong>Timeline Event Links</strong><span>{event_evidence_links}</span></li>",
                f"<li><strong>Timeline Event Preview</strong><div class='preview-pane'><strong>{esc(event_preview_title)}</strong><span>{esc(event_preview_summary)}</span>{event_preview_display}</div></li>",
                f"<li><strong>Timeline Event Fields</strong><span>{esc(event_fields_display)}</span></li>",
                f"<li><strong>Timeline Event Next Actions</strong><span>{esc(event_actions_display)}</span><div class='action-row'>{event_action_buttons}</div></li>",
                f"<li><strong>Decision History</strong><span>{esc(decision_display)}</span></li>",
                f"<li><strong>Recent Trace</strong><span>{esc(trace_display)}</span></li>",
                f"<li><strong>Available Actions</strong><span>{esc(action_display)}</span></li>",
            ]
        )

    def action_journal_rows(action_journal: dict[str, Any]) -> str:
        operator_count = int(action_journal.get("operator_count", 0) or 0)
        autonomous_count = int(action_journal.get("autonomous_count", 0) or 0)
        entries = list(action_journal.get("entries") or [])
        if not entries:
            return "<li class='empty'>No recent actions recorded yet.</li>"
        summary_rows = "".join(
            [
                f"<li><strong>Total</strong><span>{esc(action_journal.get('count', 0))} recent action(s)</span></li>",
                f"<li><strong>Operator</strong><span>{esc(operator_count)} operator-driven item(s)</span></li>",
                f"<li><strong>Autonomous</strong><span>{esc(autonomous_count)} autonomous/runtime item(s)</span></li>",
            ]
        )
        entry_rows = "".join(
            f"""
            <li>
              <strong>{esc(item.get('title', 'Recent action'))}</strong>
              <span>{esc(item.get('kind', 'activity'))} / {esc(item.get('status', 'observed'))}</span>
              <span>{esc(item.get('detail', 'Recent runtime activity.'))}</span>
              <span>Related: {esc(item.get('related_kind', 'activity'))} / {esc(item.get('related_label', 'Recent action'))}</span>
              <div class="action-row">
                <button type="button" data-detail-kind="journal" data-detail-index="{index}">Inspect</button>
                {f'<button type="button" data-jump-kind="journal-related" data-jump-index="{index}">Jump to Related</button>' if str(item.get('related_kind', '')).strip() and str(item.get('related_kind', '')).strip() != 'activity' else ''}
              </div>
              <code>{esc(item.get('timestamp', ''))}</code>
            </li>
            """
            for index, item in enumerate(entries)
        )
        return summary_rows + entry_rows

    def notification_preview_rows(notification_preview: dict[str, Any]) -> str:
        summary = dict(notification_preview.get("summary") or {})
        items = list(notification_preview.get("items") or [])
        recent_events = list(notification_preview.get("recent_events") or [])
        event_display = "; ".join(str(item) for item in recent_events if item) or "No recent event signals captured."
        item_rows = "".join(
            f"""
            <li class="needs-action">
              <strong>{esc(item.get('title', ''))}</strong>
              <span>{esc(item.get('why_this_surfaced_now', 'JARVIS surfaced this for operator review.'))}</span>
              <code>{esc(item.get('status', ''))} / {esc(item.get('priority_class', ''))}</code>
              <div class="action-row">
                <button type="button" data-detail-kind="notification" data-detail-index="{index}">Inspect</button>
              </div>
            </li>
            """
            for index, item in enumerate(items)
        ) or "<li class='empty'>No seeded notifications yet.</li>"
        return "".join(
            [
                f"<li><strong>Total Inbox</strong><span>{esc(summary.get('total', 0))} surfaced item(s)</span></li>",
                f"<li><strong>Unread</strong><span>{esc(summary.get('unread', 0))} unread item(s)</span></li>",
                f"<li><strong>Event Signals</strong><span>{esc(summary.get('event_signals', 0))} recent event signal(s)</span></li>",
                f"<li><strong>Seeded Notifications</strong><span>Hydrates into actionable inbox items when the live API is available.</span></li>",
                item_rows,
                f"<li><strong>Recent Events</strong><span>{esc(event_display)}</span></li>",
            ]
        )

    raw_json = esc(json.dumps(payload, indent=2))
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>JARVIS Command Center Index</title>
  <style>
    :root {{
      --bg: #040b12;
      --bg-2: #081520;
      --panel: rgba(10, 18, 29, 0.9);
      --panel-strong: rgba(8, 16, 26, 0.96);
      --panel-2: rgba(17, 29, 44, 0.88);
      --line: rgba(132, 181, 222, 0.14);
      --line-strong: rgba(132, 181, 222, 0.24);
      --text: #eef7fc;
      --muted: #90a7ba;
      --cyan: #72d9de;
      --blue: #8cb8ff;
      --green: #76d6a1;
      --font-ui: "SF Pro Display", "Segoe UI", sans-serif;
      --font-mono: "SF Mono", "JetBrains Mono", monospace;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      background:
        radial-gradient(circle at top left, rgba(114, 217, 222, 0.16), transparent 22%),
        radial-gradient(circle at top right, rgba(140, 184, 255, 0.16), transparent 20%),
        radial-gradient(circle at 50% 100%, rgba(118, 214, 161, 0.08), transparent 28%),
        linear-gradient(180deg, #07111b 0%, var(--bg) 48%, #02070d 100%);
      color: var(--text);
      font-family: var(--font-ui);
    }}
    body::before {{
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      background:
        linear-gradient(135deg, rgba(255,255,255,0.025), transparent 36%),
        radial-gradient(circle at 20% 20%, rgba(114, 217, 222, 0.06), transparent 18%);
      opacity: 0.9;
    }}
    .shell {{ position: relative; width: min(1340px, calc(100% - 32px)); margin: 0 auto; padding: 24px 0 56px; }}
    .topbar {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
      margin-bottom: 18px;
      padding: 14px 18px;
      border: 1px solid var(--line);
      border-radius: 22px;
      background: rgba(7, 14, 23, 0.72);
      backdrop-filter: blur(18px);
      box-shadow: 0 16px 44px rgba(0, 0, 0, 0.22);
    }}
    .topbar-brand {{
      display: flex;
      flex-direction: column;
      gap: 4px;
      min-width: 0;
    }}
    .topbar-brand strong {{
      font-size: 0.82rem;
      letter-spacing: 0.18em;
      text-transform: uppercase;
      color: var(--cyan);
    }}
    .topbar-brand span {{
      color: var(--muted);
      font-size: 0.95rem;
      line-height: 1.45;
    }}
    .topbar-links {{
      display: flex;
      flex-wrap: wrap;
      justify-content: flex-end;
      gap: 10px;
    }}
    .hero, .panel {{
      border: 1px solid var(--line);
      border-radius: 28px;
      background: linear-gradient(180deg, rgba(10, 18, 29, 0.96), rgba(7, 13, 22, 0.94));
      box-shadow: 0 24px 72px rgba(0, 0, 0, 0.28);
      backdrop-filter: blur(18px);
    }}
    .hero {{
      display: grid;
      grid-template-columns: minmax(0, 1.4fr) minmax(320px, 0.86fr);
      gap: 18px;
      padding: 26px;
    }}
    .hero-copy h1 {{ margin: 0; font-size: clamp(2.4rem, 4vw, 4rem); line-height: 0.95; letter-spacing: -0.05em; }}
    .hero-copy p {{ margin: 14px 0 0; color: var(--muted); max-width: 68ch; line-height: 1.68; font-size: 1.02rem; }}
    .eyebrow {{
      display: inline-flex;
      align-items: center;
      gap: 9px;
      padding: 7px 10px;
      border-radius: 999px;
      border: 1px solid rgba(118, 215, 223, 0.26);
      color: var(--cyan);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      background: rgba(118, 215, 223, 0.07);
    }}
    .eyebrow::before {{
      content: "";
      width: 8px;
      height: 8px;
      border-radius: 999px;
      background: currentColor;
      box-shadow: 0 0 16px currentColor;
    }}
    .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 14px; margin-top: 22px; }}
    .stat {{
      padding: 18px;
      border-radius: 20px;
      border: 1px solid var(--line);
      background:
        linear-gradient(180deg, rgba(17, 29, 44, 0.92), rgba(10, 18, 29, 0.98)),
        radial-gradient(circle at top right, rgba(140, 184, 255, 0.14), transparent 35%);
    }}
    .stat span {{
      display: block;
      margin-bottom: 8px;
      color: var(--muted);
      font-size: 0.78rem;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    .stat strong {{ display: block; margin-bottom: 4px; font-size: 1.55rem; line-height: 1.05; }}
    .stat small {{ color: var(--muted); font-size: 0.88rem; }}
    .hero-side {{
      display: grid;
      gap: 14px;
      align-content: start;
    }}
    .hero-note {{
      padding: 18px;
      border-radius: 22px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.03);
    }}
    .hero-note strong,
    .section-label {{
      display: block;
      margin-bottom: 8px;
      color: var(--muted);
      font-size: 0.78rem;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    .hero-note p {{
      margin: 0;
      line-height: 1.6;
      color: var(--text);
    }}
    .hero-note ul {{
      margin-top: 10px;
    }}
    .command-dock {{
      display: grid;
      gap: 10px;
    }}
    .command-dock a {{
      justify-content: space-between;
      border-radius: 18px;
      padding: 12px 14px;
      background: rgba(255,255,255,0.04);
    }}
    .command-dock a span {{
      color: var(--muted);
      font-size: 0.88rem;
    }}
    .glance-grid {{
      display: grid;
      grid-template-columns: minmax(0, 1.15fr) minmax(280px, 0.85fr);
      gap: 18px;
      margin-top: 18px;
    }}
    .layout {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 18px;
      margin-top: 18px;
    }}
    .panel {{ padding: 22px; }}
    .panel h2 {{ margin: 0 0 12px; font-size: 1.25rem; letter-spacing: -0.03em; }}
    .panel p {{ color: var(--muted); line-height: 1.58; }}
    .panel-head {{
      display: flex;
      justify-content: space-between;
      align-items: end;
      gap: 14px;
      margin-bottom: 14px;
    }}
    .panel-head h2,
    .panel-head p {{
      margin: 0;
    }}
    .surface-grid {{ display: grid; gap: 14px; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); }}
    .surface-card {{
      border: 1px solid var(--line);
      border-radius: 22px;
      background: linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.02));
      padding: 18px;
      transition: transform 120ms ease, border-color 120ms ease, background 120ms ease;
    }}
    .surface-card:hover {{
      transform: translateY(-2px);
      border-color: var(--line-strong);
      background: linear-gradient(180deg, rgba(114, 217, 222, 0.08), rgba(255,255,255,0.03));
    }}
    .surface-card h3 {{ margin: 8px 0; }}
    .surface-card p {{ margin: 0; color: var(--muted); line-height: 1.55; }}
    .link-row {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 14px; }}
    .history-chip {{
      display: inline-flex;
      align-items: center;
      margin-right: 8px;
      padding: 4px 8px;
      border-radius: 999px;
      border: 1px solid var(--line);
      font-size: 11px;
      letter-spacing: 0.02em;
    }}
    .history-chip-approval {{ background: rgba(118, 215, 223, 0.14); color: #9de9ef; }}
    .history-chip-notification {{ background: rgba(255, 214, 102, 0.16); color: #ffe296; }}
    .history-chip-open-loop {{ background: rgba(144, 238, 144, 0.14); color: #b8f5b8; }}
    .history-chip-recovered {{ background: rgba(144, 238, 144, 0.14); color: #b8f5b8; }}
    .history-chip-regressed {{ background: rgba(255, 130, 130, 0.16); color: #ffb3b3; }}
    .history-chip-shifted {{ background: rgba(255, 214, 102, 0.16); color: #ffe296; }}
    .history-chip-first-seen {{ background: rgba(143, 185, 255, 0.14); color: #b6d3ff; }}
    .history-chip-pending {{ background: rgba(255, 214, 102, 0.16); color: #ffe296; }}
    .history-chip-steady {{ background: rgba(149, 170, 187, 0.16); color: #d7e2ea; }}
    a {{
      display: inline-flex;
      align-items: center;
      gap: 10px;
      padding: 10px 14px;
      border-radius: 999px;
      border: 1px solid var(--line);
      color: var(--text);
      text-decoration: none;
      background: rgba(255,255,255,0.035);
    }}
    a:hover {{ border-color: var(--line-strong); background: rgba(118, 215, 223, 0.08); }}
    ul {{ list-style: none; padding: 0; margin: 0; display: grid; gap: 10px; }}
    li {{ padding: 13px 14px; border-radius: 16px; border: 1px solid var(--line); background: rgba(255,255,255,0.03); }}
    li strong {{ display: block; margin-bottom: 4px; }}
    li span {{ color: var(--muted); display: block; }}
    .action-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 10px;
    }}
    button {{
      border: 1px solid var(--line);
      background: linear-gradient(135deg, rgba(114, 217, 222, 0.15), rgba(140, 184, 255, 0.12));
      color: var(--text);
      border-radius: 999px;
      padding: 10px 13px;
      font: inherit;
      cursor: pointer;
    }}
    button:hover {{ background: linear-gradient(135deg, rgba(114, 217, 222, 0.24), rgba(140, 184, 255, 0.18)); }}
    .status-note {{
      margin-top: 12px;
      color: var(--muted);
      min-height: 1.2em;
    }}
    code, pre {{
      font-family: var(--font-mono);
      background: rgba(3, 10, 18, 0.82);
      border: 1px solid rgba(143, 185, 255, 0.16);
      border-radius: 12px;
      padding: 10px 12px;
      display: block;
      overflow-x: auto;
    }}
    pre {{ margin: 0; }}
    .empty {{ color: var(--muted); }}
    @media (max-width: 1100px) {{
      .hero,
      .glance-grid,
      .layout {{
        grid-template-columns: 1fr;
      }}
    }}
    @media (max-width: 760px) {{
      .shell {{ width: min(100% - 20px, 100%); }}
      .topbar {{
        align-items: flex-start;
        flex-direction: column;
      }}
      .topbar-links {{
        justify-content: flex-start;
      }}
      .hero {{
        padding: 22px;
      }}
      .hero-copy h1 {{
        font-size: clamp(2rem, 10vw, 3rem);
      }}
    }}
  </style>
</head>
<body>
  <main class="shell">
    <header class="topbar">
      <div class="topbar-brand">
        <strong>JARVIS Command Chamber</strong>
        <span>Live operating shell for approvals, agents, health, activity continuity, and Level 3 proof surfaces.</span>
      </div>
      <div class="topbar-links">
        <a href="{esc(payload['proof_paths']['command_center_json'])}">Index JSON <span>{esc(payload['proof_paths']['command_center_json'])}</span></a>
        <a href="{esc(payload['proof_paths']['supervision_snapshot'])}">Supervision <span>{esc(payload['proof_paths']['supervision_snapshot'])}</span></a>
        <a href="{esc(payload['proof_paths']['approval_queue'])}">Approvals <span>{esc(payload['proof_paths']['approval_queue'])}</span></a>
      </div>
    </header>
    <section class="hero">
      <div class="hero-copy">
        <div class="eyebrow">Level 3 Operating Surface</div>
        <h1>JARVIS Command Center Index</h1>
        <p>This is the live front door for the current app-facing product. It keeps the real approval queue, supervision state, health agents, continuity feeds, and proof routes visible in one chamber instead of flattening them into static mockups.</p>
        <div class="stats">
          <div class="stat">
            <span>Branch</span>
            <strong>{esc(payload['branch'])}</strong>
            <small>Canonical GitHub push source</small>
          </div>
          <div class="stat">
            <span>Head</span>
            <strong>{esc(payload['head'])}</strong>
            <small>Current local truth</small>
          </div>
          <div class="stat">
            <span>Served surfaces</span>
            <strong>{esc(payload['surface_count'])}</strong>
            <small>Live routes with payloads</small>
          </div>
          <div class="stat">
            <span>Needs me</span>
            <strong>{esc(payload['needs_cockpit']['total'])}</strong>
            <small>Immediate operator pull</small>
          </div>
        </div>
      </div>
      <aside class="hero-side">
        <div class="hero-note">
          <strong>Continuity is live</strong>
          <p>Approvals, recovery motion, open loops, health, and agent operations all stay linked to the same product state instead of living as isolated screens.</p>
          <ul>
            <li><strong>Activity continuity</strong><span>Real mutations flow back into the shared activity stream.</span></li>
            <li><strong>Health + agents</strong><span>Helen Cho, health agents, and roster surfaces remain directly reachable.</span></li>
          </ul>
        </div>
        <div class="hero-note">
          <div class="section-label">Command Dock</div>
          <div class="command-dock">
            <a href="{esc(payload['proof_paths']['briefing_json'])}"><strong>Daily Brief JSON</strong><span>{esc(payload['proof_paths']['briefing_json'])}</span></a>
            <a href="{esc(payload['proof_paths']['missions_json'])}"><strong>Mission Board JSON</strong><span>{esc(payload['proof_paths']['missions_json'])}</span></a>
            <a href="{esc(payload['proof_paths']['assistant_notifications_json'])}"><strong>Notification Feed JSON</strong><span>{esc(payload['proof_paths']['assistant_notifications_json'])}</span></a>
          </div>
        </div>
      </aside>
    </section>
    <section class="glance-grid">
      <section class="panel">
        <div class="panel-head">
          <div>
            <h2>Today at a Glance</h2>
            <p>Real home overview state, current checklist continuity, and the last action that changed the day plan.</p>
          </div>
        </div>
        <ul id="home-overview">{home_overview_rows(payload['home_overview'], payload.get('level3_checklist', {}))}</ul>
        <div class="panel-head" style="margin-top: 18px;">
          <div>
            <h2>Last Home Action</h2>
            <p>Most recent stateful home mutation rendered straight from the current payload.</p>
          </div>
        </div>
        <ul id="home-action-result">{home_action_result_rows(payload['home_overview'].get('action_result', {}))}</ul>
      </section>
      <section class="panel">
        <div class="panel-head">
          <div>
            <h2>Open Now</h2>
            <p>Jump into the live routes that already carry real payloads, agents, and interaction surfaces.</p>
          </div>
        </div>
        <div class="surface-grid">{surface_cards(payload['surfaces'])}</div>
      </section>
    </section>
    <div class="layout">
      <section class="panel">
        <div class="panel-head">
          <div>
            <h2>Needs Me Now</h2>
            <p>Seeded and live operator demand, preserved as a real cockpit instead of a cosmetic queue.</p>
          </div>
        </div>
        <ul id="needs-list">{needs_rows(payload['needs_cockpit'])}</ul>
      </section>
      <section class="panel">
        <div class="panel-head">
          <div>
            <h2>Recent Need Motion</h2>
            <p>Transitions, reassignment, and changes in urgency reflected back into shared continuity.</p>
          </div>
        </div>
        <ul id="needs-motion">{needs_motion_rows(payload['needs_motion'])}</ul>
      </section>
      <section class="panel">
        <div class="panel-head">
          <div>
            <h2>Command Center Actions</h2>
            <p>Live supervision and approval actions stay executable from the shell.</p>
          </div>
        </div>
        <ul id="approval-actions">{approval_rows(payload['pending_approvals'])}</ul>
        <p class="status-note" id="status-note">This panel hydrates from the live supervision and approval endpoints when opened through the app.</p>
      </section>
    </div>
    <div class="layout">
      <section class="panel">
        <h2>Memory Inspector</h2>
        <ul id="memory-inspector">{memory_rows(payload['memory'])}</ul>
      </section>
      <section class="panel">
        <h2>Agent Roster &amp; Ops</h2>
        <ul id="agent-ops-roster">{agent_ops_roster_rows(payload['agent_ops_roster'])}</ul>
      </section>
      <section class="panel">
        <h2>Daily Brief Preview</h2>
        <ul id="brief-preview">{brief_preview_rows(payload['brief_preview'])}</ul>
      </section>
      <section class="panel">
        <h2>Task &amp; Workstream Timeline</h2>
        <ul id="timeline-preview">{timeline_preview_rows(payload['timeline_preview'])}</ul>
      </section>
      <section class="panel">
        <h2>Mission &amp; Task Board</h2>
        <ul id="mission-task-board">{mission_task_board_rows(payload['mission_task_board'])}</ul>
      </section>
      <section class="panel">
        <h2>Core Modules</h2>
        <ul id="core-modules">{core_modules_rows(payload['core_modules'])}</ul>
      </section>
      <section class="panel">
        <h2>Open-Loop Inspector</h2>
        <ul id="open-loop-inspector">{open_loop_inspector_rows(payload['open_loop_inspector'])}</ul>
      </section>
      <section class="panel">
        <h2>Item Detail</h2>
        <ul id="detail-inspector">{detail_inspector_rows(payload['detail_inspector'])}</ul>
      </section>
      <section class="panel">
        <h2>Action Journal</h2>
        <ul id="action-journal">{action_journal_rows(payload['action_journal'])}</ul>
      </section>
      <section class="panel">
        <h2>Notification &amp; Event Feed</h2>
        <ul id="notification-preview">{notification_preview_rows(payload['notification_preview'])}</ul>
      </section>
      <section class="panel">
        <h2>Activity Feed</h2>
        <ul id="activity-feed">{activity_rows(payload['activity_feed'])}</ul>
      </section>
      <section class="panel">
        <h2>Lane Progress</h2>
        <ul id="lane-progress">{lane_progress_rows(payload['lane_progress'])}</ul>
      </section>
      <section class="panel">
        <h2>Progress Dashboard</h2>
        <ul id="progress-dashboard">{progress_dashboard_rows(payload['progress_dashboard'])}</ul>
      </section>
      <section class="panel">
        <h2>Seam Tracker</h2>
        <ul id="seam-tracker">{seam_tracker_rows(payload['seam_tracker'])}</ul>
      </section>
      <section class="panel">
        <h2>Failure &amp; Recovery</h2>
        <ul id="failure-recovery">{failure_recovery_rows(payload['failure_recovery'])}</ul>
      </section>
      <section class="panel">
        <h2>Hosted Edge</h2>
        <ul id="hosted-deployment">{hosted_deployment_rows(payload.get('hosted_deployment', {}))}</ul>
      </section>
      <section class="panel">
        <h2>Agent Registry</h2>
        <ul id="agent-registry">{registry_rows(payload['registry'])}</ul>
      </section>
      <section class="panel">
        <h2>Actionable JSON</h2>
        <ul>{endpoint_rows(payload['json_endpoints'])}</ul>
      </section>
      <section class="panel">
        <h2>Linked Proof Paths</h2>
        <ul>
          <li><strong>Command Center JSON</strong><code>{esc(payload['proof_paths']['command_center_json'])}</code></li>
          <li><strong>Supervision Snapshot JSON</strong><code>{esc(payload['proof_paths']['supervision_snapshot_json'])}</code></li>
          <li><strong>Approval Queue JSON</strong><code>{esc(payload['proof_paths']['approval_queue_json'])}</code></li>
          <li><strong>Briefing JSON</strong><code>{esc(payload['proof_paths']['briefing_json'])}</code></li>
          <li><strong>Open Loops JSON</strong><code>{esc(payload['proof_paths']['open_loops_json'])}</code></li>
          <li><strong>Missions JSON</strong><code>{esc(payload['proof_paths']['missions_json'])}</code></li>
          <li><strong>Assistant Notifications JSON</strong><code>{esc(payload['proof_paths']['assistant_notifications_json'])}</code></li>
        </ul>
      </section>
    </div>
    <section class="panel" style="margin-top: 18px;">
      <h2>Raw Index JSON</h2>
      <pre>{raw_json}</pre>
    </section>
  </main>
  <script>
    const initialCommandCenterPayload = {raw_json};
    const statusNote = document.getElementById("status-note");
    const homeOverview = document.getElementById("home-overview");
    const homeActionResult = document.getElementById("home-action-result");
    const needsList = document.getElementById("needs-list");
    const needsMotion = document.getElementById("needs-motion");
    const approvalActions = document.getElementById("approval-actions");
    const memoryInspector = document.getElementById("memory-inspector");
    const agentOpsRoster = document.getElementById("agent-ops-roster");
    const briefPreview = document.getElementById("brief-preview");
    const timelinePreview = document.getElementById("timeline-preview");
    const missionTaskBoard = document.getElementById("mission-task-board");
    const coreModules = document.getElementById("core-modules");
    const progressDashboard = document.getElementById("progress-dashboard");
    const openLoopInspector = document.getElementById("open-loop-inspector");
    const detailInspector = document.getElementById("detail-inspector");
    const actionJournal = document.getElementById("action-journal");
    const notificationPreview = document.getElementById("notification-preview");
    const activityFeed = document.getElementById("activity-feed");
    const agentRegistry = document.getElementById("agent-registry");
    const laneProgress = document.getElementById("lane-progress");
    const seamTracker = document.getElementById("seam-tracker");
    const failureRecovery = document.getElementById("failure-recovery");
    let latestCommandCenterPayload = initialCommandCenterPayload;
    let latestSupervisionPayload = {{}};
    let latestApprovalsPayload = {{}};
    let latestOpenLoopsPayload = {{}};
    let latestNotificationsPayload = {{}};
    let latestActivityPayload = [];
    let latestNeedsActionStates = {{}};
    let recentLocalActions = [];
    let recentNeedsMotion = [];
    let recentMotionArtifactActions = [];
    let latestHomeActionResult = (initialCommandCenterPayload.home_overview && initialCommandCenterPayload.home_overview.action_result) || null;
    let currentDetailSelection = {{ kind: "open-loop", index: 0 }};
    let currentTimelineEventIndex = null;
    let currentMotionArtifactIndex = null;
    let latestChangeSummary = "No action diff captured yet.";
    let pendingActionContext = null;

    function esc(text) {{
      return String(text)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
    }}

    function approvalItemHtml(item) {{
      const requestId = String(item.request_id || "");
      const actions = Object.assign({{}}, item.actions || {{}});
      if (requestId) {{
        actions.approve ||= `/api/approvals/${{requestId}}/approve`;
        actions.reject ||= `/api/approvals/${{requestId}}/reject`;
        actions.cancel ||= `/api/approvals/${{requestId}}/cancel`;
        actions.execute ||= `/api/approvals/${{requestId}}/execute`;
      }}
      return `
        <li class="needs-action">
          <strong>${{esc(item.title || "")}}</strong>
          <span>${{esc(item.description || "")}}</span>
          <code>${{esc(item.risk_tier || "")}} · ${{esc(item.agent_label || "")}}</code>
          <div class="action-row">
            <button type="button" data-endpoint="${{esc(actions.approve || "")}}" data-method="POST">Approve</button>
            <button type="button" data-endpoint="${{esc(actions.reject || "")}}" data-method="POST" data-body='{{"reason":"Need a safer plan first"}}'>Reject</button>
            <button type="button" data-endpoint="${{esc(actions.cancel || "")}}" data-method="POST">Cancel</button>
            <button type="button" data-endpoint="${{esc(actions.execute || "")}}" data-method="POST">Execute</button>
          </div>
        </li>`;
    }}

    function buildNeedsCockpit(supervision, approvals, openLoops, notifications, activity) {{
      const queue = new Map();
      const urgencyScore = (level) => {{
        switch (String(level || "").trim().toLowerCase()) {{
          case "critical": return 4;
          case "high": return 3;
          case "medium": return 2;
          case "normal": return 1;
          case "low": return 0;
          default: return 1;
        }}
      }};
      const normalizedKey = (title, source) => `${{String(title || "").trim().toLowerCase().replaceAll(/\\s+/g, " ") || "untitled"}}::${{String(source || "").trim().toLowerCase() || "general"}}`;
      const addNeed = ({{ title, detail, urgency, source, route, routeLabel, actionHint, focusTargets = [], primaryAction = null }}) => {{
        const cleanedTitle = String(title || "").trim();
        if (!cleanedTitle) return;
        const key = normalizedKey(cleanedTitle, source);
        const candidateScore = urgencyScore(urgency);
        const existing = queue.get(key);
        if (!existing) {{
          queue.set(key, {{
            need_key: key,
            title: cleanedTitle,
            detail: String(detail || "").trim() || "Needs operator review.",
            urgency: String(urgency || "normal").trim().toLowerCase() || "normal",
            urgency_score: candidateScore,
            sources: [String(source || "general").trim() || "general"],
            route: String(route || "/command-center").trim() || "/command-center",
            route_label: String(routeLabel || "Open command center").trim() || "Open command center",
            action_hint: String(actionHint || "").trim() || "Inspect this item from the command center.",
            focus_targets: Array.isArray(focusTargets) ? focusTargets.filter(Boolean) : [],
            primary_action: primaryAction || null,
          }});
          return;
        }}
        const sourceLabel = String(source || "general").trim() || "general";
        if (!existing.sources.includes(sourceLabel)) existing.sources.push(sourceLabel);
        if (candidateScore > Number(existing.urgency_score || 0)) {{
          existing.urgency = String(urgency || "normal").trim().toLowerCase() || "normal";
          existing.urgency_score = candidateScore;
          existing.route = String(route || existing.route || "").trim() || existing.route;
          existing.route_label = String(routeLabel || existing.route_label || "").trim() || existing.route_label;
          existing.action_hint = String(actionHint || existing.action_hint || "").trim() || existing.action_hint;
          if (Array.isArray(focusTargets) && focusTargets.length) existing.focus_targets = focusTargets.filter(Boolean);
          if (primaryAction) existing.primary_action = primaryAction;
        }}
        if (detail && String(detail).length > String(existing.detail || "").length) {{
          existing.detail = String(detail).trim();
        }}
      }};

      const needs = Array.isArray(supervision.what_needs_me) ? supervision.what_needs_me : [];
      needs.slice(0, 6).forEach((item) => {{
        const title = String(item.title || "").trim();
        const detail = String(item.detail || "").trim();
        const joined = `${{title}} ${{detail}}`.toLowerCase();
        addNeed({{
          title,
          detail,
          urgency: ["urgent", "high", "approval", "blocked", "review"].some((token) => joined.includes(token)) ? "high" : "normal",
          source: "supervision",
          route: "/supervision-snapshot",
          routeLabel: "Open supervision",
          actionHint: "Inspect the supervision snapshot for full return-brief context.",
          focusTargets: ["open-loop", "journal"],
        }});
      }});

      const pending = Array.isArray(approvals.pending) ? approvals.pending : [];
      pending.slice(0, 6).forEach((item) => {{
        const riskTier = String(item.risk_tier || "").trim().toLowerCase();
        const requestId = String(item.request_id || "").trim();
        const actions = Object.assign({{}}, item.actions || {{}});
        addNeed({{
          title: item.title || "Pending approval",
          detail: item.description || "Approval queue needs review.",
          urgency: riskTier === "high" ? "critical" : ["medium", "elevated"].includes(riskTier) ? "high" : "normal",
          source: "approval",
          route: "/approval-queue",
          routeLabel: "Open approval queue",
          actionHint: "Approve, reject, cancel, or execute from the approval queue.",
          focusTargets: ["open-loop", "journal"],
          primaryAction: (requestId || actions.approve) ? {{
            label: "Approve",
            endpoint: String(actions.approve || (requestId ? `/api/approvals/${{requestId}}/approve` : "")).trim(),
            method: "POST",
          }} : null,
        }});
      }});

      const openLoopItems = Array.isArray(openLoops.items) ? openLoops.items : [];
      openLoopItems.slice(0, 6).forEach((item) => {{
        const status = String(item.status || "").trim().toLowerCase();
        const itemId = String(item.item_id || "").trim();
        const domain = String(item.domain || "").trim();
        const availableActions = Array.isArray(item.available_actions) ? item.available_actions : [];
        const firstAction = availableActions.length ? availableActions[0] : null;
        const actionId = String((firstAction && firstAction.id) || "").trim();
        addNeed({{
          title: item.title || "Open loop needs review",
          detail: item.summary || item.next_action || "Open-loop review needed.",
          urgency: ["pending", "needs-me", "waiting"].includes(status) ? "high" : "normal",
          source: "open-loop",
          route: "/command-center",
          routeLabel: "Inspect open loop",
          actionHint: item.next_action || "Inspect this open loop from the command center.",
          focusTargets: ["open-loop"],
          primaryAction: (itemId && domain && actionId) ? {{
            label: firstAction.label || actionId,
            endpoint: "/api/open-loops/action",
            method: "POST",
            body: {{
              actor: "Chris",
              domain,
              item_id: itemId,
              action: actionId,
            }},
          }} : null,
        }});
      }});

      const notificationItems = Array.isArray(notifications.items) ? notifications.items : [];
      notificationItems.slice(0, 6).forEach((item) => {{
        const priorityClass = String(item.priority_class || "").trim().toLowerCase();
        const notificationId = String(item.notification_id || "").trim();
        const actions = Object.assign({{}}, item.actions || {{}});
        addNeed({{
          title: item.title || "Notification surfaced",
          detail: item.why_this_surfaced_now || item.status || "Notification needs review.",
          urgency: priorityClass === "high" ? "high" : "normal",
          source: "notification",
          route: "/command-center",
          routeLabel: "Inspect notification",
          actionHint: "Open or ignore the surfaced notification from the command center.",
          focusTargets: ["notification", "journal"],
          primaryAction: (notificationId || actions.open) ? {{
            label: "Open",
            endpoint: String(actions.open || (notificationId ? `/api/assistant-core/notifications/${{notificationId}}` : "")).trim(),
            method: "POST",
            body: {{ actor: "Chris", status: "opened" }},
          }} : null,
        }});
      }});

      const integrations = Array.isArray(supervision.integrations) ? supervision.integrations.filter((item) => item && item.ok === false) : [];
      integrations.slice(0, 4).forEach((item) => {{
        addNeed({{
          title: `Repair ${{item.name || "integration"}}`,
          detail: item.detail || "Integration failure surfaced.",
          urgency: "critical",
          source: "failure",
          route: "/supervision-snapshot",
          routeLabel: "Open recovery view",
          actionHint: "Inspect failure and recovery posture before retrying related actions.",
          focusTargets: ["journal", "open-loop"],
        }});
      }});

      const activityItems = Array.isArray(activity) ? activity : [];
      const recentFailures = activityItems.filter((item) => {{
        const haystack = [item.title, item.detail, item.subtitle, item.result, item.result_summary, item.entry_type]
          .map((part) => String(part || "").toLowerCase())
          .join(" ");
        return ["fail", "error", "recover", "rollback", "blocked"].some((token) => haystack.includes(token));
      }}).slice(0, 4);
      recentFailures.forEach((item) => {{
        addNeed({{
          title: item.title || "Recent failure surfaced",
          detail: item.detail || item.timestamp || "Runtime failure needs review.",
          urgency: "high",
          source: "failure",
          route: "/command-center",
          routeLabel: "Inspect failure trace",
          actionHint: "Review the command-center detail surfaces and recent trace before acting.",
          focusTargets: ["journal", "open-loop"],
        }});
      }});

      const items = Array.from(queue.values())
        .sort((left, right) => (Number(right.urgency_score || 0) - Number(left.urgency_score || 0))
          || (Number((right.sources || []).length || 0) - Number((left.sources || []).length || 0))
          || String(left.title || "").localeCompare(String(right.title || "")))
        .slice(0, 8);
      return {{
        total: items.length,
        critical_count: items.filter((item) => item.urgency === "critical").length,
        high_count: items.filter((item) => item.urgency === "high").length,
        approval_count: items.filter((item) => Array.isArray(item.sources) && item.sources.includes("approval")).length,
        failure_count: items.filter((item) => Array.isArray(item.sources) && item.sources.includes("failure")).length,
        notification_count: items.filter((item) => Array.isArray(item.sources) && item.sources.includes("notification")).length,
        headline: items.length ? String(items[0].title || "") : "Nothing urgent right now.",
        items,
      }};
    }}

    function applyNeedsActionState(cockpit) {{
      const items = cockpit && Array.isArray(cockpit.items) ? cockpit.items : [];
      const mergedItems = items.map((item) => {{
        const needKey = String(item.need_key || "").trim();
        const localState = needKey ? latestNeedsActionStates[needKey] : null;
        if (!localState) return item;
        return Object.assign({{}}, item, {{
          row_state_summary: String(localState.summary || "").trim(),
          row_state_status: String(localState.status || "").trim(),
          row_state_retired: Boolean(localState.retired),
          row_state_posture: String(localState.posture || "").trim(),
          row_state_follow_up: String(localState.follow_up || "").trim(),
        }});
      }});
      const activeItems = mergedItems.filter((item) => !item.row_state_retired);
      const retiredItems = mergedItems.filter((item) => item.row_state_retired);
      return Object.assign({{}}, cockpit || {{}}, {{
        items: activeItems,
        retired_items: retiredItems,
      }});
    }}

    function reconcileNeedsActionState(cockpit) {{
      const items = cockpit && Array.isArray(cockpit.items) ? cockpit.items : [];
      const itemByKey = new Map(
        items
          .map((item) => [String((item && item.need_key) || "").trim(), item])
          .filter(([key]) => Boolean(key))
      );
      for (const [needKey, localState] of Object.entries(latestNeedsActionStates || {{}})) {{
        const liveItem = itemByKey.get(String(needKey || "").trim()) || null;
        if (!liveItem) {{
          if (localState && (localState.retired || localState.status === "reopened" || localState.status === "resurfaced")) {{
            delete latestNeedsActionStates[needKey];
          }}
          continue;
        }}
        if (localState && localState.retired) {{
          recordNeedMotion({{
            kind: "resurfaced",
            title: String(liveItem.title || needKey || "triage item").trim(),
            status: "resurfaced",
            detail: "Returned to the active triage queue after a recent handled state.",
            need_key: needKey,
            action_kind: "resurface",
            action_label: "Live Reconcile",
            action_summary: "A fresh hydrate brought this need back into the active queue.",
            before_state: "retired",
            after_state: needMotionQueueState(liveItem, "resurfaced"),
          }});
          latestNeedsActionStates[needKey] = Object.assign({{}}, localState, {{
            status: "resurfaced",
            summary: `Live need resurfaced: ${{String(liveItem.title || needKey || "triage item").trim()}}`,
            retired: false,
            posture: "Returned to the active triage queue after a recent handled state.",
            follow_up: String(localState.follow_up || liveItem.action_hint || "Inspect the live need again from the command center.").trim(),
          }});
          continue;
        }}
        if (localState && localState.status === "reopened") {{
          delete latestNeedsActionStates[needKey];
        }}
      }}
      return applyNeedsActionState(cockpit);
    }}

    function needsNowHtml(cockpit) {{
      const mergedCockpit = reconcileNeedsActionState(cockpit);
      const items = mergedCockpit && Array.isArray(mergedCockpit.items) ? mergedCockpit.items : [];
      const retiredItems = mergedCockpit && Array.isArray(mergedCockpit.retired_items) ? mergedCockpit.retired_items : [];
      const primaryActionButton = (item) => {{
        const primaryAction = item && item.primary_action ? item.primary_action : null;
        const endpoint = String((primaryAction && primaryAction.endpoint) || "").trim();
        if (!endpoint) return "";
        const method = String((primaryAction && primaryAction.method) || "POST").trim() || "POST";
        const body = primaryAction && primaryAction.body
          ? ` data-body='${{JSON.stringify(primaryAction.body).replaceAll("'", "&#39;")}}'`
          : "";
        const needsKey = String(item.need_key || "").trim();
        const keyAttr = needsKey ? ` data-needs-key="${{esc(needsKey)}}"` : "";
        return `<button type="button" data-endpoint="${{esc(endpoint)}}" data-method="${{esc(method)}}"${{keyAttr}}${{body}}>${{esc((primaryAction && primaryAction.label) || "Act")}}</button>`;
      }};
      const activeDisplay = items.length ? items.map((item) => `
        <li class="needs-action">
          <strong>${{esc(item.title || "")}}</strong>
          <span>${{esc(item.detail || "")}}</span>
          <code>${{esc(item.urgency || "normal")}} · ${{esc(Array.isArray(item.sources) ? item.sources.join(", ") : "")}}</code>
          ${{item.row_state_summary ? `<span>${{esc(item.row_state_summary)}}</span>` : ""}}
          <div class="action-row">
            ${{primaryActionButton(item)}}
            ${{Array.isArray(item.focus_targets) && item.focus_targets.length ? `<button type="button" data-needs-index="${{esc(items.indexOf(item))}}">Inspect</button>` : ""}}
          </div>
          <div class="link-row">
            <span>${{esc(item.action_hint || "Inspect this item from the command center.")}}</span>
            <a href="${{esc(item.route || "/command-center")}}">${{esc(item.route_label || "Open command center")}}</a>
          </div>
        </li>`).join("") : "";
      const retiredDisplay = retiredItems.length
        ? retiredItems.map((item) => `
          <li>
            <strong>${{esc(item.title || "Handled item")}}</strong>
            <span>Handled moments ago.</span>
            <code>${{esc(item.row_state_summary || "Action succeeded.")}}</code>
            ${{item.row_state_posture ? `<span>Handled posture: ${{esc(item.row_state_posture)}}</span>` : ""}}
            <div class="action-row">
              ${{Array.isArray(item.focus_targets) && item.focus_targets.length ? `<button type="button" data-needs-key-inspect="${{esc(item.need_key || "")}}">Inspect Outcome</button>` : ""}}
              <button type="button" data-needs-reopen="${{esc(item.need_key || "")}}">Reopen</button>
            </div>
            <div class="link-row">
              <span>${{esc(item.row_state_follow_up || item.action_hint || "Inspect the latest outcome from the command center.")}}</span>
              <a href="${{esc(item.route || "/command-center")}}">${{esc(item.route_label || "Open command center")}}</a>
            </div>
          </li>`).join("")
        : "";
      if (!activeDisplay && !retiredDisplay) {{
        return "<li class='empty'>Nothing urgent right now.</li>";
      }}
      return activeDisplay + retiredDisplay;
    }}

    function memoryItemHtml(memory) {{
      const latestTitles = Array.isArray(memory.latest_entry_titles) ? memory.latest_entry_titles.filter(Boolean) : [];
      const pendingProposals = Array.isArray(memory.pending_proposals) ? memory.pending_proposals.filter(Boolean) : [];
      const latestDisplay = latestTitles.length ? latestTitles.join(", ") : "No recent memory entries.";
      const proposalDisplay = pendingProposals.length ? pendingProposals.join(", ") : "No pending memory proposals.";
      return [
        `<li><strong>Entries</strong><span>${{esc(memory.entry_count || 0)}} stored entries</span></li>`,
        `<li><strong>Proposals</strong><span>${{esc(memory.proposal_count || 0)}} total proposals</span></li>`,
        `<li><strong>Facts</strong><span>${{esc(memory.fact_count || 0)}} profile facts</span></li>`,
        `<li><strong>Latest Titles</strong><span>${{esc(latestDisplay)}}</span></li>`,
        `<li><strong>Pending Proposals</strong><span>${{esc(proposalDisplay)}}</span></li>`,
      ].join("");
    }}

    function buildVisibleActivityEntries(activity) {{
      const localEntries = (Array.isArray(recentLocalActions) ? recentLocalActions : []).map((item) => ({{
        entry_type: item.entry_type || item.kind || "local-action",
        title: item.title || "Recent local action",
        detail: item.detail || item.related_label || "Local action recorded in the command center.",
        subtitle: item.related_label || item.related_kind || "",
        result: item.status || "ok",
        result_summary: item.result_summary || item.action_summary || "",
        why_now: item.why_now || "",
        timestamp: item.timestamp || "",
      }}));
      const liveEntries = Array.isArray(activity) ? activity : [];
      const hasDurableHomeAction = liveEntries.some((item) => String((item && item.entry_type) || "").trim() === "home-action");
      const hasDurableOperatorAction = liveEntries.some((item) => String((item && item.entry_type) || "").trim() === "operator-action");
      const filteredLocalEntries = hasDurableHomeAction
        ? localEntries.filter((item) => String(item.entry_type || "").trim() !== "home-action")
        : localEntries;
      const fullyFilteredLocalEntries = hasDurableOperatorAction
        ? filteredLocalEntries.filter((item) => String(item.entry_type || "").trim() !== "local-action")
        : filteredLocalEntries;
      return [...fullyFilteredLocalEntries, ...liveEntries]
        .sort((left, right) => String(right.timestamp || "").localeCompare(String(left.timestamp || "")))
        .slice(0, 8);
    }}

    async function recordHomeActionEvent(payload) {{
      try {{
        const response = await fetch("/api/activity/home-action", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify(payload || {{}}),
        }});
        if (!response.ok) return false;
        await response.json().catch(() => ({{}}));
        return true;
      }} catch (_error) {{
        return false;
      }}
    }}

    function sharedActivityRouteFor(endpoint, detail) {{
      const endpointText = String(endpoint || "").trim().toLowerCase();
      const sourceKind = String((detail && detail.source_kind) || "").trim().toLowerCase();
      if (endpointText.includes("/api/approvals/") || sourceKind === "approval") return "/approval-queue";
      if (endpointText.includes("/api/missions/") || sourceKind === "mission") return "/mission-board";
      if (endpointText.includes("/api/assistant-core/notifications/") || sourceKind === "notification") return "/command-center";
      if (endpointText.includes("/api/open-loops/action") || sourceKind === "open-loop") return "/command-center";
      return "/command-center";
    }}

    function sharedActivityKindFor(endpoint, detail) {{
      const endpointText = String(endpoint || "").trim().toLowerCase();
      const sourceKind = String((detail && detail.source_kind) || "").trim().toLowerCase();
      if (endpointText.includes("/api/approvals/") || sourceKind === "approval") return "approval";
      if (endpointText.includes("/api/missions/") || sourceKind === "mission") return "mission";
      if (endpointText.includes("/api/assistant-core/notifications/") || sourceKind === "notification") return "notification";
      if (endpointText.includes("/api/open-loops/action") || sourceKind === "open-loop") return "open-loop";
      return "activity";
    }}

    async function recordOperatorActionEvent(payload) {{
      try {{
        const response = await fetch("/api/activity/operator-action", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify(payload || {{}}),
        }});
        if (!response.ok) return false;
        await response.json().catch(() => ({{}}));
        return true;
      }} catch (_error) {{
        return false;
      }}
    }}

    function activityItemHtml(items) {{
      if (!Array.isArray(items) || !items.length) {{
        return "<li class='empty'>No recent runtime activity yet.</li>";
      }}
      return items.map((item) => {{
        const meta = [item.entry_type || "", item.timestamp || ""].filter(Boolean).join(" · ");
        const detail = [item.why_now || item.subtitle || item.domain || "", item.result_summary || item.result || ""]
          .filter(Boolean)
          .join(" · ");
        const title = item.detail || item.action || item.output_preview || item.title || item.entry_type || "activity";
        return `<li><strong>${{esc(title)}}</strong><span>${{esc(detail || "No detail captured.")}}</span><code>${{esc(meta)}}</code></li>`;
      }}).join("");
    }}

    function buildNeedsMotion(cockpit, activity) {{
      const entries = [];
      const activeItems = cockpit && Array.isArray(cockpit.items) ? cockpit.items : [];
      for (const item of activeItems.slice(0, 5)) {{
        entries.push({{
          kind: "active",
          title: String(item.title || "").trim() || "Active need",
          status: String(item.urgency || "").trim() || "normal",
          detail: String(item.detail || item.action_hint || "").trim() || "JARVIS surfaced this need for operator review.",
          timestamp: "live queue",
          need_key: String(item.need_key || "").trim(),
          source_kind: "need",
          source_label: String(item.title || item.need_key || "").trim() || "Active need",
          queue_state: [
            String(item.urgency || "").trim(),
            Array.isArray(item.sources) ? item.sources.join(", ") : "",
          ].filter(Boolean).join(" / ") || "active",
          transition: "observed -> active",
          evidence_links: [
            {{ label: "Command Center", href: "/command-center" }},
            {{
              label: Array.isArray(item.sources) && item.sources.includes("approval") ? "Open approval queue" : "Open open loops JSON",
              href: Array.isArray(item.sources) && item.sources.includes("approval") ? "/approval-queue" : "/api/open-loops?actor=Chris",
            }},
          ],
          evidence: [
            String(item.urgency || "").trim(),
            Array.isArray(item.sources) ? item.sources.join(", ") : "",
            String(item.route_label || "").trim(),
          ].filter(Boolean).join(" / "),
        }});
      }}
      const activityItems = Array.isArray(activity) ? activity : [];
      for (const item of activityItems) {{
        const haystack = [
          item.title || "",
          item.subtitle || "",
          item.result || "",
          item.entry_type || "",
        ].join(" ").toLowerCase();
        if (!["approval", "review", "fail", "error", "blocked", "notification"].some((token) => haystack.includes(token))) continue;
        entries.push({{
          kind: "signal",
          title: String(item.title || "").trim() || "Recent signal",
          status: String(item.entry_type || "").trim() || "activity",
          detail: String(item.result || item.subtitle || "").trim() || "Recent runtime activity may have changed triage posture.",
          timestamp: String(item.timestamp || "").trim() || "recent activity",
          need_key: "",
          source_kind: "activity",
          source_label: String(item.subtitle || item.title || "").trim() || "Recent activity",
          source_entry_type: String(item.entry_type || "").trim() || "activity",
          queue_state: String(item.entry_type || "").trim() || "signal",
          transition: "runtime signal -> review",
          evidence_links: [
            {{ label: "Activity JSON", href: "/api/activity" }},
            {{ label: "Command Center", href: "/command-center" }},
          ],
          evidence: [
            String(item.entry_type || "").trim(),
            String(item.subtitle || "").trim(),
            String(item.timestamp || "").trim(),
          ].filter(Boolean).join(" / "),
        }});
        if (entries.length >= 8) break;
      }}
      const localEntries = Array.isArray(recentNeedsMotion) ? recentNeedsMotion : [];
      return {{
        count: [...localEntries, ...entries].slice(0, 8).length,
        active_count: entries.filter((item) => item.kind === "active").length,
        signal_count: entries.filter((item) => item.kind === "signal").length,
        entries: [...localEntries, ...entries].slice(0, 8),
      }};
    }}

    function needsMotionHtml(motion) {{
      const entries = motion && Array.isArray(motion.entries) ? motion.entries : [];
      if (!entries.length) {{
        return "<li class='empty'>No recent need motion captured yet.</li>";
      }}
      const summaryRows = [
        `<li><strong>Total</strong><span>${{esc(motion.count || 0)}} recent motion item(s)</span></li>`,
        `<li><strong>Active Queue</strong><span>${{esc(motion.active_count || 0)}} live queue motion item(s)</span></li>`,
        `<li><strong>Signals</strong><span>${{esc(motion.signal_count || 0)}} runtime signal item(s)</span></li>`,
      ].join("");
      const entryRows = entries.map((item) => `
        <li>
          <strong>${{esc(item.title || "Need motion")}}</strong>
          <span>${{esc(item.kind || "motion")}} / ${{esc(item.status || "observed")}}</span>
          <span>${{esc(item.detail || "Recent triage motion.")}}</span>
          ${{String(item.source_kind || "").trim() || String(item.source_label || "").trim() ? `<span>Source: ${{esc(item.source_kind || "")}} / ${{esc(item.source_label || "")}}</span>` : ""}}
          ${{String(item.transition || "").trim() ? `<span>Transition: ${{esc(item.transition || "")}}</span>` : ""}}
          ${{String(item.queue_state || "").trim() ? `<span>Queue State: ${{esc(item.queue_state || "")}}</span>` : ""}}
          ${{String(item.evidence || "").trim() ? `<span>Evidence: ${{esc(item.evidence || "")}}</span>` : ""}}
          <div class="action-row">
            <button type="button" data-motion-index="${{esc(entries.indexOf(item))}}">Inspect Proof</button>
            ${{String(item.need_key || "").trim() ? `<button type="button" data-needs-key-inspect="${{esc(item.need_key || "")}}">Inspect Need</button>` : ""}}
            ${{Array.isArray(item.evidence_links) ? item.evidence_links.map((link) => `<a href="${{esc(link.href || "#")}}">${{esc(link.label || "Open Link")}}</a>`).join(" ") : ""}}
          </div>
          <code>${{esc(item.timestamp || "")}}</code>
        </li>`).join("");
      return summaryRows + entryRows;
    }}

    function currentNeedsMotion() {{
      return buildNeedsMotion(currentNeedsCockpit(), Array.isArray(latestActivityPayload) ? latestActivityPayload : []);
    }}

    function needMotionContext(needKey) {{
      const normalizedKey = String(needKey || "").trim();
      if (!normalizedKey) return null;
      const cockpit = currentNeedsCockpit();
      const candidates = [
        ...(Array.isArray(cockpit.items) ? cockpit.items : []),
        ...(Array.isArray(cockpit.retired_items) ? cockpit.retired_items : []),
      ];
      return candidates.find((item) => String((item && item.need_key) || "").trim() === normalizedKey) || null;
    }}

    function findJournalIndexForMotion(item) {{
      const entries = buildActionJournalEntries(latestApprovalsPayload || {{}}, Array.isArray(latestActivityPayload) ? latestActivityPayload : []);
      const title = String((item && item.title) || "").trim().toLowerCase();
      const detail = String((item && item.detail) || "").trim().toLowerCase();
      const timestamp = String((item && item.timestamp) || "").trim();
      const sourceKind = String((item && item.source_kind) || "").trim().toLowerCase();
      const sourceLabel = String((item && item.source_label) || "").trim().toLowerCase();
      const sourceEntryType = String((item && item.source_entry_type) || "").trim().toLowerCase();
      if (sourceKind === "activity") {{
        const exactActivityIndex = entries.findIndex((entry) => {{
          const entryKind = String((entry && entry.kind) || "").trim().toLowerCase();
          const entryDetail = String((entry && entry.detail) || "").trim().toLowerCase();
          const entryTitle = String((entry && entry.title) || "").trim().toLowerCase();
          const entryRelated = String((entry && entry.related_label) || "").trim().toLowerCase();
          const entryTimestamp = String((entry && entry.timestamp) || "").trim();
          return (!sourceEntryType || entryKind === sourceEntryType)
            && (!sourceLabel || entryDetail === sourceLabel || entryRelated === sourceLabel || entryTitle === sourceLabel)
            && (!timestamp || !entryTimestamp || entryTimestamp === timestamp);
        }});
        if (exactActivityIndex >= 0) return exactActivityIndex;
      }}
      return entries.findIndex((entry) => {{
        const entryTitle = String((entry && entry.title) || "").trim().toLowerCase();
        const entryDetail = String((entry && entry.detail) || "").trim().toLowerCase();
        const entryTimestamp = String((entry && entry.timestamp) || "").trim();
        return Boolean(title) && entryTitle === title
          && (!detail || entryDetail === detail || entryDetail.includes(detail) || detail.includes(entryDetail))
          && (!timestamp || !entryTimestamp || entryTimestamp === timestamp);
      }});
    }}

    function jumpToNeedMotion(index) {{
      const motion = currentNeedsMotion();
      const item = (motion && Array.isArray(motion.entries) ? motion.entries : [])[Number(index)] || null;
      const motionArtifacts = (detail, motionItem) => {{
        const artifacts = [];
        const requestId = String((detail && (detail.request_id || detail.item_id)) || "").trim();
        const domain = String((detail && detail.domain) || "").trim();
        const notificationId = String((detail && detail.notification_id) || "").trim();
        const sourceKind = String((detail && detail.source_kind) || "").trim();
        if (requestId && sourceKind === "open-loop") {{
          artifacts.push({{
            label: "Open-Loop Record",
            link_label: "Open Open-Loop JSON",
            href: "/api/open-loops?actor=Chris",
            summary: `Open-loop item ${{requestId}}${{domain ? ` in ${{domain}}` : ""}} is the exact live record behind this motion.`,
            focus_kind: "open-loop",
          }});
        }}
        if (notificationId) {{
          artifacts.push({{
            label: "Notification Record",
            link_label: "Open Notification JSON",
            href: `/api/assistant-core/notifications/${{notificationId}}`,
            summary: `Notification ${{notificationId}} is the exact inbox artifact behind this motion.`,
            focus_kind: "notification",
          }});
        }}
        if (requestId && (sourceKind === "open-loop" || String((motionItem && motionItem.source_label) || "").toLowerCase().includes("approval"))) {{
          artifacts.push({{
            label: "Approval Queue Record",
            link_label: "Open Approval Queue Snapshot",
            href: "/api/approval-queue/snapshot",
            summary: `Approval request ${{requestId}} is represented in the approval queue proof surface for this motion.`,
            focus_kind: "approval",
          }});
        }}
        if (!artifacts.length && Array.isArray(motionItem && motionItem.evidence_links)) {{
          return motionItem.evidence_links.map((link) => ({{
            label: String((link && link.label) || "Proof Artifact").trim() || "Proof Artifact",
            link_label: String((link && link.label) || "Open Artifact").trim() || "Open Artifact",
            href: String((link && link.href) || "#").trim() || "#",
            summary: "Fallback artifact link captured directly from the motion row.",
            focus_kind: "",
          }}));
        }}
        return artifacts;
      }};
      if (!item) {{
        const fallback = selectedDetail();
        fallback.change_summary = "Recent Need Motion selection could not be resolved.";
        fallback.change_evidence_summary = "The requested motion entry was not available in the current motion snapshot.";
        return fallback;
      }}
      const needKey = String(item.need_key || "").trim();
      if (needKey) {{
        const needContext = needMotionContext(needKey);
        const detail = jumpToNeedContextByKey(needKey);
        detail.change_summary = "Focused proof context from Recent Need Motion.";
        detail.change_evidence_summary = `Resolved from motion transition: ${{item.transition || item.title || "need motion"}}.`;
        detail.motion_proof_summary = `Motion row "${{item.title || "need motion"}}" resolved to live need context via ${{item.transition || "observed transition"}}.`;
        detail.motion_proof_source = `${{item.source_kind || "need"}} / ${{item.source_label || item.title || needKey}}`;
        detail.motion_proof_sections = [
          {{ label: "Motion Kind", value: String(item.kind || "motion") }},
          {{ label: "Transition", value: String(item.transition || "observed transition") }},
          {{ label: "Before State", value: String(item.before_state || "observed") }},
          {{ label: "After State", value: String(item.after_state || item.queue_state || "active") }},
          {{ label: "Action Cause", value: String(item.action_label || item.action_kind || "No explicit action recorded") }},
          {{ label: "Domain Consequence", value: String(item.consequence_summary || "No domain-specific consequence recorded") }},
          {{ label: "Queue State", value: String(item.queue_state || "active") }},
          {{ label: "Need Source", value: String(item.source_label || item.title || needKey) }},
        ];
        detail.motion_proof_panels = [
          {{
            title: "Live Need Snapshot",
            summary: "Current triage context for the need that this motion row resolved into.",
            rows: [
              {{ label: "Urgency", value: String((needContext && needContext.urgency) || item.status || "normal") }},
              {{ label: "Source Mix", value: Array.isArray(needContext && needContext.sources) ? needContext.sources.join(", ") : String(item.source_label || item.source_kind || "need") }},
              {{ label: "Before Queue State", value: String(item.before_state || "observed") }},
              {{ label: "After Queue State", value: String(item.after_state || item.queue_state || "active") }},
              {{ label: "Action Summary", value: String(item.action_summary || item.detail || "No explicit action summary recorded.") }},
              {{ label: "Domain Consequence", value: String(item.consequence_summary || "No domain-specific consequence recorded") }},
              {{ label: "Action Hint", value: String((needContext && needContext.action_hint) || detail.next_action || "Inspect the command-center context.") }},
              {{ label: "Focus Targets", value: Array.isArray(needContext && needContext.focus_targets) ? needContext.focus_targets.join(", ") : String(detail.source_kind || "open-loop") }},
            ],
            links: [
              {{ label: String((needContext && needContext.route_label) || "Open command center"), href: String((needContext && needContext.route) || "/command-center") }},
            ],
          }},
        ];
        detail.motion_proof_excerpts = [
          `Need title: ${{String((needContext && needContext.title) || detail.title || item.title || needKey).trim()}}`,
          `Need detail: ${{String((needContext && needContext.detail) || detail.why_now || detail.summary || "No live need detail captured.").trim()}}`,
          `Queue transition: ${{String(item.before_state || "observed").trim()}} -> ${{String(item.after_state || item.queue_state || "active").trim()}}`,
          `Action cause: ${{String(item.action_label || item.action_kind || "No explicit action recorded").trim()}}`,
          `Domain consequence: ${{String(item.consequence_summary || "No domain-specific consequence recorded").trim()}}`,
          `Need action hint: ${{String((needContext && needContext.action_hint) || detail.next_action || "Inspect the command-center context.").trim()}}`,
        ];
        detail.motion_proof_artifacts = motionArtifacts(detail, item);
        return detail;
      }}
      const journalIndex = findJournalIndexForMotion(item);
      if (journalIndex >= 0) {{
        currentDetailSelection = {{ kind: "journal", index: journalIndex }};
        const detail = journalDetailAt(journalIndex);
        const relatedContextLine = Array.isArray(detail.evidence_lines)
          ? detail.evidence_lines.find((line) => String(line || "").startsWith("Related context: "))
          : "";
        detail.change_summary = "Focused journal proof from Recent Need Motion.";
        detail.change_evidence_summary = `Resolved from motion signal: ${{item.title || "recent signal"}}.`;
        detail.motion_proof_summary = `Motion row "${{item.title || "recent signal"}}" matched the local journal/activity proof stream.`;
        detail.motion_proof_source = `${{item.source_kind || "activity"}} / ${{item.source_label || item.title || "recent signal"}}`;
        detail.motion_proof_sections = [
          {{ label: "Motion Kind", value: String(item.kind || "motion") }},
          {{ label: "Transition", value: String(item.transition || "runtime signal") }},
          {{ label: "Before State", value: String(item.before_state || "runtime signal") }},
          {{ label: "After State", value: String(item.after_state || item.queue_state || "review") }},
          {{ label: "Action Cause", value: String(item.action_label || item.action_kind || "Signal-driven review") }},
          {{ label: "Domain Consequence", value: String(item.consequence_summary || "Signal requested review of this context") }},
          {{ label: "Signal Source", value: String(item.source_label || item.title || "recent signal") }},
          {{ label: "Signal Type", value: String(item.source_entry_type || item.status || "activity") }},
        ];
        detail.motion_proof_panels = [
          {{
            title: "Signal Proof Snapshot",
            summary: "Recent runtime or journal signal that drove this motion-proof jump.",
            rows: [
              {{ label: "Journal Kind", value: String(detail.domain || item.source_entry_type || "activity") }},
              {{ label: "Recorded Status", value: String(detail.status || item.status || "observed") }},
              {{ label: "Before Queue State", value: String(item.before_state || "runtime signal") }},
              {{ label: "After Queue State", value: String(item.after_state || item.queue_state || "review") }},
              {{ label: "Action Summary", value: String(item.action_summary || item.detail || "Signal-driven review without a direct action endpoint.") }},
              {{ label: "Domain Consequence", value: String(item.consequence_summary || "Signal requested review of this context") }},
              {{ label: "Related Context", value: String(relatedContextLine || item.source_label || item.title || "Recent activity").replace("Related context: ", "") }},
              {{ label: "Signal Time", value: String(item.timestamp || detail.next_review_at || "recent activity") }},
            ],
            links: [
              {{ label: "Activity JSON", href: "/api/activity" }},
            ],
          }},
        ];
        detail.motion_proof_excerpts = [
          `Journal title: ${{String(detail.title || item.title || "Recent action").trim()}}`,
          `Journal detail: ${{String(detail.summary || detail.change_evidence_summary || item.detail || "Recent runtime activity.").trim()}}`,
          `Queue transition: ${{String(item.before_state || "runtime signal").trim()}} -> ${{String(item.after_state || item.queue_state || "review").trim()}}`,
          `Action cause: ${{String(item.action_label || item.action_kind || "Signal-driven review").trim()}}`,
          `Domain consequence: ${{String(item.consequence_summary || "Signal requested review of this context").trim()}}`,
          `Journal relation: ${{String(relatedContextLine || item.source_label || item.title || "Recent activity").replace("Related context: ", "").trim()}}`,
        ];
        detail.motion_proof_artifacts = motionArtifacts(detail, item);
        return detail;
      }}
      const fallback = selectedDetail();
      fallback.change_summary = `No exact proof context found for "${{item.title || "motion entry"}}".`;
      fallback.change_evidence_summary = `Motion transition was ${{item.transition || item.kind || "observed"}}.`;
      fallback.motion_proof_summary = `Motion row "${{item.title || "motion entry"}}" could not be matched to a more exact proof target.`;
      fallback.motion_proof_source = `${{item.source_kind || "unknown"}} / ${{item.source_label || item.title || "untyped motion"}}`;
      fallback.motion_proof_sections = [
        {{ label: "Motion Kind", value: String(item.kind || "motion") }},
        {{ label: "Transition", value: String(item.transition || item.kind || "observed") }},
        {{ label: "Before State", value: String(item.before_state || "observed") }},
        {{ label: "After State", value: String(item.after_state || item.queue_state || item.status || "observed") }},
        {{ label: "Action Cause", value: String(item.action_label || item.action_kind || "No explicit action recorded") }},
        {{ label: "Domain Consequence", value: String(item.consequence_summary || "No domain-specific consequence recorded") }},
        {{ label: "Fallback Source", value: String(item.source_label || item.title || "untyped motion") }},
      ];
      fallback.motion_proof_panels = [
        {{
          title: "Fallback Motion Snapshot",
          summary: "No exact detail target was found; use the captured motion evidence to keep investigating.",
          rows: [
            {{ label: "Entry Kind", value: String(item.kind || "motion") }},
            {{ label: "Observed State", value: String(item.status || item.queue_state || "observed") }},
            {{ label: "Before Queue State", value: String(item.before_state || "observed") }},
            {{ label: "After Queue State", value: String(item.after_state || item.queue_state || item.status || "observed") }},
            {{ label: "Action Summary", value: String(item.action_summary || item.detail || "No explicit action summary recorded.") }},
            {{ label: "Domain Consequence", value: String(item.consequence_summary || "No domain-specific consequence recorded") }},
            {{ label: "Transition", value: String(item.transition || item.kind || "observed") }},
            {{ label: "Timestamp", value: String(item.timestamp || "recent motion") }},
          ],
          links: Array.isArray(item.evidence_links) ? item.evidence_links : [],
        }},
      ];
      fallback.motion_proof_excerpts = [
        `Fallback title: ${{String(item.title || "motion entry").trim()}}`,
        `Fallback detail: ${{String(item.detail || item.evidence || "No exact proof target was found.").trim()}}`,
        `Queue transition: ${{String(item.before_state || "observed").trim()}} -> ${{String(item.after_state || item.queue_state || item.status || "observed").trim()}}`,
        `Action cause: ${{String(item.action_label || item.action_kind || "No explicit action recorded").trim()}}`,
        `Domain consequence: ${{String(item.consequence_summary || "No domain-specific consequence recorded").trim()}}`,
        `Fallback timestamp: ${{String(item.timestamp || "recent motion").trim()}}`,
      ];
      fallback.motion_proof_artifacts = motionArtifacts(fallback, item);
      return fallback;
    }}

    function jumpToMotionArtifact(index) {{
      const detail = jumpToNeedMotion(index);
      const artifacts = detail && Array.isArray(detail.motion_proof_artifacts) ? detail.motion_proof_artifacts : [];
      const preferred = artifacts.find((item) => String((item && item.focus_kind) || "").trim()) || null;
      const timeline = Array.isArray(detail && detail.item_timeline) ? detail.item_timeline : [];
      const focusKind = String((preferred && preferred.focus_kind) || "").trim();
      if (focusKind) {{
        const artifactTimelineIndex = timeline.findIndex((item) => {{
          const itemKind = String((item && item.kind) || "").trim();
          if (focusKind === "approval") return itemKind === "decision";
          if (focusKind === "notification") return itemKind === "notification";
          if (focusKind === "open-loop") return itemKind === "open-loop";
          return false;
        }});
        if (artifactTimelineIndex >= 0) currentTimelineEventIndex = artifactTimelineIndex;
      }}
      const focusSections = [];
      const focusActions = [];
      if (focusKind === "approval") {{
        const approvalContext = detail.approval_review_context || {{}};
        const latestDecision = Array.isArray(detail.decision_history) && detail.decision_history.length ? detail.decision_history[0] : null;
        const requestId = String(approvalContext.request_id || detail.request_id || detail.item_id || "").trim();
        detail.motion_artifact_focus_title = "Approval Artifact Focus";
        detail.motion_artifact_focus_summary = "Localized approval proof derived from the exact request record behind this motion.";
        focusSections.push(
          {{ label: "Request ID", value: String(approvalContext.request_id || detail.request_id || detail.item_id || "not attached") }},
          {{ label: "Risk Tier", value: String(approvalContext.risk_tier || detail.status || "pending") }},
          {{ label: "Decision", value: latestDecision ? `${{latestDecision.status || "unknown"}} / ${{latestDecision.resolution || "unclassified"}}` : String(detail.last_decision_summary || "No prior decision attached.") }},
          {{ label: "Review Detail", value: String(approvalContext.description || detail.summary || "Pending approval needs operator review.") }},
        );
        if (requestId) {{
          focusActions.push(
            {{ endpoint: `/api/approvals/${{requestId}}/approve`, method: "POST", label: "Approve Request" }},
            {{ endpoint: `/api/approvals/${{requestId}}/reject`, method: "POST", body: {{ reason: "Need a safer plan first" }}, label: "Reject Request" }},
            {{ endpoint: `/api/approvals/${{requestId}}/execute`, method: "POST", label: "Execute Request" }},
          );
        }}
      }} else if (focusKind === "notification") {{
        const notificationId = String(detail.notification_id || "").trim();
        const actions = Object.assign({{}}, detail.notification_actions || {{}});
        const openEndpoint = String(actions.open || (notificationId ? `/api/assistant-core/notifications/${{notificationId}}` : "")).trim();
        const ignoreEndpoint = String(actions.ignore || (notificationId ? `/api/assistant-core/notifications/${{notificationId}}` : "")).trim();
        detail.motion_artifact_focus_title = "Notification Artifact Focus";
        detail.motion_artifact_focus_summary = "Localized notification proof derived from the surfaced inbox record behind this motion.";
        focusSections.push(
          {{ label: "Notification ID", value: String(detail.notification_id || "not attached") }},
          {{ label: "Status", value: String(detail.status || "unknown") }},
          {{ label: "Priority", value: Array.isArray(detail.evidence_lines) && detail.evidence_lines.length > 1 ? String(detail.evidence_lines[1] || "normal").replace("Priority class: ", "") : "normal" }},
          {{ label: "Why Surfaced", value: String(detail.why_now || detail.summary || "No surfaced reason captured.") }},
        );
        if (openEndpoint) focusActions.push({{ endpoint: openEndpoint, method: "POST", body: {{ actor: "Chris", status: "opened" }}, label: "Open Notification" }});
        if (ignoreEndpoint) focusActions.push({{ endpoint: ignoreEndpoint, method: "POST", body: {{ actor: "Chris", status: "ignored" }}, label: "Ignore Notification" }});
      }} else if (focusKind === "open-loop") {{
        detail.motion_artifact_focus_title = "Open-Loop Artifact Focus";
        detail.motion_artifact_focus_summary = "Localized open-loop proof derived from the exact live work item behind this motion.";
        focusSections.push(
          {{ label: "Item ID", value: String(detail.item_id || "not attached") }},
          {{ label: "Domain", value: String(detail.domain || "general") }},
          {{ label: "Owner Agent", value: String(detail.owner_agent || "JARVIS") }},
          {{ label: "Next Review", value: String(detail.next_review_at || "not scheduled") }},
        );
      }} else {{
        detail.motion_artifact_focus_title = "Artifact Focus";
        detail.motion_artifact_focus_summary = "No localized artifact-specific focus block was derived for this motion.";
      }}
      const postureBadge = motionArtifactPostureBadge(detail);
      const postureStateBadge = motionArtifactPostureStateBadge(detail);
      detail.motion_artifact_focus_posture_summary = motionArtifactPostureSummary(detail);
      detail.motion_artifact_focus_posture_badge_label = String((postureBadge && postureBadge.label) || "artifact posture").trim() || "artifact posture";
      detail.motion_artifact_focus_posture_badge_class = String((postureBadge && postureBadge.className) || "artifact").trim() || "artifact";
      detail.motion_artifact_focus_posture_state_label = String((postureStateBadge && postureStateBadge.label) || "steady").trim() || "steady";
      detail.motion_artifact_focus_posture_state_class = String((postureStateBadge && postureStateBadge.className) || "steady").trim() || "steady";
      detail.motion_artifact_focus_posture_hint = motionArtifactPostureHint(detail);
      detail.motion_artifact_focus_sections = focusSections;
      detail.motion_artifact_focus_delta_summary = "No localized artifact mutation captured yet.";
      detail.motion_artifact_focus_delta_sections = [];
      detail.motion_artifact_focus_excerpts = [];
      detail.motion_artifact_focus_proof_compare_summary = "No localized artifact proof comparison captured yet.";
      detail.motion_artifact_focus_proof_compare_rows = [];
      detail.motion_artifact_focus_history_summary = "No localized artifact action history captured yet.";
      detail.motion_artifact_focus_history_meta = "";
      detail.motion_artifact_focus_history_rows = [];
      detail.motion_artifact_focus_history_note = "";
      detail.motion_artifact_focus_posture_snapshot_action = null;
      detail.motion_artifact_focus_posture_snapshot_reason = "";
      detail.motion_artifact_focus_posture_snapshot_reason_target = null;
      detail.motion_artifact_focus_posture_snapshot_reason_focus = null;
      detail.motion_artifact_focus_actions = focusActions;
      detail.motion_proof_summary = `${{detail.motion_proof_summary || "Motion proof selected."}} In-page artifact focus applied${{focusKind ? ` for ${{focusKind}} proof.` : "."}}`;
      detail.change_summary = "Focused localized motion-proof artifact in the shared inspector.";
      detail.change_evidence_summary = preferred
        ? `Localized proof artifact: ${{preferred.label || preferred.focus_kind || "artifact"}}.`
        : "No localized artifact focus was available for this motion row.";
      applyMotionArtifactHistory(detail);
      return detail;
    }}

    function motionArtifactFocusValueMap(detail) {{
      const rows = detail && Array.isArray(detail.motion_artifact_focus_sections) ? detail.motion_artifact_focus_sections : [];
      return rows.reduce((acc, item) => {{
        const label = String((item && item.label) || "").trim();
        if (label) acc[label] = String((item && item.value) || "").trim();
        return acc;
      }}, {{}});
    }}

    function motionArtifactFocusKind(detail) {{
      const title = String((detail && detail.motion_artifact_focus_title) || "").trim().toLowerCase();
      if (title.includes("approval")) return "approval";
      if (title.includes("notification")) return "notification";
      if (title.includes("open-loop")) return "open-loop";
      return String((detail && detail.source_kind) || "").trim().toLowerCase() || "artifact";
    }}

    function motionArtifactPostureSummary(detail) {{
      const focusKind = motionArtifactFocusKind(detail);
      if (focusKind === "approval") {{
        const status = String((detail && detail.status) || "unknown").trim();
        const outcome = String((detail && detail.last_decision_summary) || "no recorded decision").trim();
        return `Approval posture: ${{status}} / ${{outcome}}`;
      }}
      if (focusKind === "notification") {{
        const status = String((detail && detail.status) || "unknown").trim();
        const whyNow = String((detail && detail.why_now) || "no surfaced reason").trim();
        return `Inbox posture: ${{status}} / ${{whyNow}}`;
      }}
      if (focusKind === "open-loop") {{
        const status = String((detail && detail.status) || "unknown").trim();
        const nextAction = String((detail && detail.next_action) || "no next action").trim();
        return `Workflow posture: ${{status}} / ${{nextAction}}`;
      }}
      return "No localized artifact posture captured yet.";
    }}

    function motionArtifactPostureBadge(detail) {{
      const focusKind = motionArtifactFocusKind(detail);
      if (focusKind === "approval") {{
        return {{ label: "approval posture", className: "approval" }};
      }}
      if (focusKind === "notification") {{
        return {{ label: "inbox posture", className: "notification" }};
      }}
      if (focusKind === "open-loop") {{
        return {{ label: "workflow posture", className: "open-loop" }};
      }}
      return {{ label: "artifact posture", className: "artifact" }};
    }}

    function motionArtifactPostureStateBadge(detail) {{
      const focusKind = motionArtifactFocusKind(detail);
      const status = String((detail && detail.status) || "").trim().toLowerCase();
      const decision = String((detail && detail.last_decision_summary) || "").trim().toLowerCase();
      if (focusKind === "approval") {{
        if (decision.includes("approved") || decision.includes("allow") || decision.includes("executed")) {{
          return {{ label: "approved", className: "recovered" }};
        }}
        if (decision.includes("rejected") || decision.includes("denied") || decision.includes("failed")) {{
          return {{ label: "rejected", className: "regressed" }};
        }}
        if (["pending", "queued", "waiting", "needs-review"].includes(status)) {{
          return {{ label: "awaiting consent", className: "pending" }};
        }}
        return {{ label: "review steady", className: "steady" }};
      }}
      if (focusKind === "notification") {{
        if (["opened", "read", "handled"].includes(status)) {{
          return {{ label: "opened", className: "recovered" }};
        }}
        if (["failed", "error"].includes(status)) {{
          return {{ label: "delivery issue", className: "regressed" }};
        }}
        if (["new", "queued", "pending", "unread"].includes(status)) {{
          return {{ label: "needs triage", className: "pending" }};
        }}
        return {{ label: "inbox steady", className: "steady" }};
      }}
      if (focusKind === "open-loop") {{
        if (["resolved", "complete", "completed", "done", "closed"].includes(status)) {{
          return {{ label: "resolved", className: "recovered" }};
        }}
        if (["blocked", "failed", "error", "stalled"].includes(status)) {{
          return {{ label: "blocked", className: "regressed" }};
        }}
        if (["pending", "queued", "waiting"].includes(status)) {{
          return {{ label: "waiting", className: "pending" }};
        }}
        return {{ label: "in motion", className: "steady" }};
      }}
      return {{ label: "steady", className: "steady" }};
    }}

    function motionArtifactPostureHint(detail, context = null) {{
      const result = context && typeof context === "object" ? Object.assign({{}}, context.result || {{}}) : {{}};
      const errorText = String((context && context.error) || "").trim();
      const actionLabel = String((context && context.actionLabel) || "").trim().toLowerCase();
      const focusKind = motionArtifactFocusKind(detail);
      if (errorText) {{
        if (focusKind === "approval") {{
          return `Approval action failed just now: ${{errorText}}. Inspect the localized proof and decide whether to retry or reject.`;
        }}
        if (focusKind === "notification") {{
          return `Notification action failed just now: ${{errorText}}. Inspect the proof payload before retrying this inbox action.`;
        }}
        if (focusKind === "open-loop") {{
          return `Workflow action failed just now: ${{errorText}}. Inspect the localized proof and mutation rows before trying again.`;
        }}
        return `Localized artifact action failed just now: ${{errorText}}. Inspect the proof blocks below before trying again.`;
      }}
      if (focusKind === "approval" && (actionLabel.includes("approve") || actionLabel.includes("reject") || actionLabel.includes("execute") || String(result.resolution || result.outcome || "").trim())) {{
        if (actionLabel.includes("execute")) {{
          return "Approval executed just now; confirm the returned proof and any consequence rows before leaving this record.";
        }}
        if (String(result.resolution || result.outcome || "").trim().toLowerCase().includes("allow") || actionLabel.includes("approve")) {{
          return "Approval moved just now; review the returned proof and use Execute Request if the exact record still matches intent.";
        }}
        if (String(result.resolution || result.outcome || "").trim().toLowerCase().includes("reject") || actionLabel.includes("reject")) {{
          return "Approval rejection recorded just now; inspect the proof and decide whether this request needs a safer follow-up plan.";
        }}
      }}
      if (focusKind === "notification" && (actionLabel.includes("open") || actionLabel.includes("ignore") || String(result.status || result.result || "").trim())) {{
        if (actionLabel.includes("ignore") || String(result.status || result.result || "").trim().toLowerCase().includes("ignored")) {{
          return "Notification was cleared just now; use the stored proof if you need to confirm why this inbox item was dismissed.";
        }}
        return "Notification posture changed just now; inspect the returned proof if you need the exact inbox payload.";
      }}
      if (focusKind === "open-loop" && (actionLabel || String(result.status || result.result || result.action || "").trim())) {{
        return "Workflow posture changed just now; review the mutation and proof rows before choosing the next exact-record move.";
      }}
      const stateBadge = motionArtifactPostureStateBadge(detail);
      const stateLabel = String((stateBadge && stateBadge.label) || "").trim().toLowerCase();
      if (stateLabel === "awaiting consent") {{
        return "Review the approval proof and use the inline request controls when you are ready to decide.";
      }}
      if (stateLabel === "approved") {{
        return "Approval posture looks recovered; execute only if the returned proof still matches intent.";
      }}
      if (stateLabel === "rejected") {{
        return "Approval posture regressed; inspect the rejection proof before retrying.";
      }}
      if (stateLabel === "needs triage") {{
        return "Open the notification or ignore it to clear this inbox pressure.";
      }}
      if (stateLabel === "opened") {{
        return "Notification posture looks healthy; use the stored proof if you need the exact payload.";
      }}
      if (stateLabel === "delivery issue") {{
        return "Notification delivery regressed; inspect the proof payload before trusting this alert.";
      }}
      if (stateLabel === "waiting") {{
        return "This workflow is waiting; use the artifact actions or timeline proof to move it forward.";
      }}
      if (stateLabel === "blocked") {{
        return "This workflow is blocked; inspect the localized proof and mutation rows before taking the next step.";
      }}
      if (stateLabel === "resolved") {{
        return "This record looks recovered; verify the exact proof snapshot if you need stronger confirmation.";
      }}
      return "Use the localized proof blocks below for the next exact-record move.";
    }}

    function motionArtifactPostureSuggestedAction(detail) {{
      const actions = detail && Array.isArray(detail.motion_artifact_focus_actions) ? detail.motion_artifact_focus_actions : [];
      const stateBadge = motionArtifactPostureStateBadge(detail);
      const stateLabel = String((stateBadge && stateBadge.label) || "").trim().toLowerCase();
      const pickAction = (pattern) => actions.find((item) => String((item && item.label) || "").toLowerCase().includes(pattern)) || null;
      if (stateLabel === "awaiting consent") {{
        return pickAction("approve") || {{ label: "Approve Request", summary: "Best next move: resolve this approval posture." }};
      }}
      if (stateLabel === "approved") {{
        return pickAction("execute") || pickAction("approve") || {{ label: "Execute Request", summary: "Best next move: execute if the returned proof still matches intent." }};
      }}
      if (stateLabel === "rejected") {{
        return pickAction("reject") || {{ label: "Review Rejection", summary: "Best next move: inspect the rejection proof before changing course." }};
      }}
      if (stateLabel === "needs triage") {{
        return pickAction("open") || {{ label: "Open Notification", summary: "Best next move: open the inbox item and inspect the localized payload." }};
      }}
      if (stateLabel === "opened") {{
        return pickAction("ignore") || pickAction("open") || {{ label: "Review Notification", summary: "Best next move: confirm whether this inbox item still needs attention." }};
      }}
      if (stateLabel === "waiting") {{
        return {{ label: String((detail && detail.next_action) || "Review Workflow").trim() || "Review Workflow", summary: "Best next move: use the exact workflow guidance below." }};
      }}
      if (stateLabel === "blocked") {{
        return {{ label: "Inspect Workflow Proof", summary: "Best next move: inspect the localized workflow proof before retrying." }};
      }}
      return actions[0] || null;
    }}

    function motionArtifactSnapshotSuggestedAction(detail, entry) {{
      const actions = detail && Array.isArray(detail.motion_artifact_focus_actions) ? detail.motion_artifact_focus_actions : [];
      const focusKind = motionArtifactFocusKind(detail);
      const outcomeLabel = String((entry && entry.outcome) || "").trim().toLowerCase();
      const actionLabel = String((entry && entry.action_label) || "").trim().toLowerCase();
      const pickAction = (pattern) => actions.find((item) => String((item && item.label) || "").toLowerCase().includes(pattern)) || null;
      if (focusKind === "approval") {{
        if (outcomeLabel === "failed") {{
          return pickAction(actionLabel.includes("reject") ? "reject" : actionLabel.includes("execute") ? "execute" : "approve")
            || pickAction("approve")
            || pickAction("reject")
            || {{ label: "Review Approval Failure", summary: "Reopened next move: inspect the failed approval proof before retrying consent or execution." }};
        }}
        if (outcomeLabel.includes("approved") || outcomeLabel.includes("allow")) {{
          return pickAction("execute")
            || pickAction("approve")
            || {{ label: "Execute Request", summary: "Reopened next move: execute only if the stored approval proof still matches intent." }};
        }}
        if (outcomeLabel.includes("rejected") || outcomeLabel.includes("deny")) {{
          return pickAction("reject")
            || {{ label: "Review Rejection", summary: "Reopened next move: inspect the stored rejection proof before changing course." }};
        }}
      }}
      if (focusKind === "notification") {{
        if (outcomeLabel === "failed") {{
          return pickAction("open")
            || {{ label: "Review Notification Failure", summary: "Reopened next move: inspect the stored inbox failure proof before retrying." }};
        }}
        if (outcomeLabel.includes("ignored")) {{
          return pickAction("open")
            || {{ label: "Reopen Notification", summary: "Reopened next move: reopen the inbox item if the stored dismissal proof no longer looks right." }};
        }}
        if (outcomeLabel.includes("opened")) {{
          return pickAction("ignore")
            || pickAction("open")
            || {{ label: "Clear Notification", summary: "Reopened next move: clear the inbox item if the stored opened proof already answered the need." }};
        }}
      }}
      if (focusKind === "open-loop") {{
        if (outcomeLabel === "failed") {{
          return {{ label: "Inspect Workflow Proof", summary: "Reopened next move: inspect the stored workflow failure proof before retrying." }};
        }}
        if (actions.length) {{
          return Object.assign({{}}, actions[0], {{
            summary: "Reopened next move: continue from the stored workflow outcome if this exact record still needs action.",
          }});
        }}
        return {{ label: String((detail && detail.next_action) || "Review Workflow").trim() || "Review Workflow", summary: "Reopened next move: use the stored workflow proof and next-action guidance together." }};
      }}
      return motionArtifactPostureSuggestedAction(detail);
    }}

    function motionArtifactSnapshotActionReason(detail, entry) {{
      const focusKind = motionArtifactFocusKind(detail);
      const excerpts = entry && Array.isArray(entry.motion_artifact_focus_excerpts) ? entry.motion_artifact_focus_excerpts : [];
      const compareRows = entry && Array.isArray(entry.motion_artifact_focus_proof_compare_rows) ? entry.motion_artifact_focus_proof_compare_rows : [];
      const excerptText = String(excerpts.find((item) => String(item || "").trim()) || "").trim();
      const compareText = (() => {{
        const row = compareRows.find((item) => item && String(item.value || "").trim());
        if (!row) return "";
        return `${{String(row.label || "Proof").trim()}}: ${{String(row.value || "").trim()}}`.trim();
      }})();
      const proofText = excerptText || compareText || String((entry && entry.motion_artifact_focus_proof_compare_summary) || "").trim() || String((entry && entry.change_evidence_summary) || "").trim();
      if (!proofText) return "";
      if (focusKind === "approval") {{
        return `Approval proof behind this follow-up: ${{proofText}}`;
      }}
      if (focusKind === "notification") {{
        return `Inbox proof behind this follow-up: ${{proofText}}`;
      }}
      if (focusKind === "open-loop") {{
        return `Workflow proof behind this follow-up: ${{proofText}}`;
      }}
      return `Stored proof behind this follow-up: ${{proofText}}`;
    }}

    function motionArtifactSnapshotReasonTarget(detail, entry) {{
      const focusKind = motionArtifactFocusKind(detail);
      const excerpts = entry && Array.isArray(entry.motion_artifact_focus_excerpts) ? entry.motion_artifact_focus_excerpts : [];
      const compareRows = entry && Array.isArray(entry.motion_artifact_focus_proof_compare_rows) ? entry.motion_artifact_focus_proof_compare_rows : [];
      const rawHistoryIndex = entry && entry.history_index;
      const rawTimelineEventIndex = entry && entry.timeline_event_index;
      const historyIndex = Number.isInteger(rawHistoryIndex) ? rawHistoryIndex : null;
      const timelineEventIndex = Number.isInteger(rawTimelineEventIndex) ? rawTimelineEventIndex : null;
      const timelineEventTitle = String((entry && entry.timeline_event_title) || "").trim();
      const excerptIndex = excerpts.findIndex((item) => String(item || "").trim());
      if (excerptIndex >= 0) {{
        return {{
          kind: "excerpt",
          index: excerptIndex,
          history_index: historyIndex,
          timeline_event_index: timelineEventIndex,
          timeline_event_title: timelineEventTitle,
          title: focusKind === "approval"
            ? "Reopened Approval Proof Focus"
            : focusKind === "notification"
              ? "Reopened Inbox Proof Focus"
              : focusKind === "open-loop"
                ? "Reopened Workflow Proof Focus"
                : "Reopened Proof Focus",
          summary: "Focused the exact stored proof excerpt behind this reopened next move.",
        }};
      }}
      const compareIndex = compareRows.findIndex((item) => item && String(item.value || "").trim());
      if (compareIndex >= 0) {{
        return {{
          kind: "compare",
          index: compareIndex,
          history_index: historyIndex,
          timeline_event_index: timelineEventIndex,
          timeline_event_title: timelineEventTitle,
          title: focusKind === "approval"
            ? "Reopened Approval Proof Focus"
            : focusKind === "notification"
              ? "Reopened Inbox Proof Focus"
              : focusKind === "open-loop"
                ? "Reopened Workflow Proof Focus"
                : "Reopened Proof Focus",
          summary: "Focused the exact stored proof comparison row behind this reopened next move.",
        }};
      }}
      return null;
    }}

    function focusMotionArtifactSnapshotReason(detail) {{
      const target = detail && detail.motion_artifact_focus_posture_snapshot_reason_target && typeof detail.motion_artifact_focus_posture_snapshot_reason_target === "object"
        ? detail.motion_artifact_focus_posture_snapshot_reason_target
        : null;
      if (!target) return detail;
      const excerpts = detail && Array.isArray(detail.motion_artifact_focus_excerpts) ? detail.motion_artifact_focus_excerpts : [];
      const compareRows = detail && Array.isArray(detail.motion_artifact_focus_proof_compare_rows) ? detail.motion_artifact_focus_proof_compare_rows : [];
      const pivotSummaryForButtons = (buttons) => {{
        if (!Array.isArray(buttons) || !buttons.length) return "";
        return `Pivot breadcrumbs: ${{buttons.map((item) => String(item && item.breadcrumb || "").trim()).filter(Boolean).join(" ; ")}}`;
      }};
      const pivotButtonsForActions = (buttons) => {{
        if (!Array.isArray(buttons) || !buttons.length) return [];
        return buttons.map((item) => {{
          if (!item || typeof item !== "object") return null;
          if (item.kind === "history") {{
            return {{
              kind: "history",
              history_index: Number(item.history_index),
              label: "Open Mutation",
            }};
          }}
          if (item.kind === "timeline") {{
            return {{
              kind: "timeline",
              timeline_event_index: Number(item.timeline_event_index),
              label: "Open Chronology",
            }};
          }}
          return null;
        }}).filter(Boolean);
      }};
      if (target.kind === "excerpt") {{
        const excerpt = String(excerpts[Number(target.index)] || "").trim();
        if (excerpt) {{
          const actionButtons = [];
          if (Number.isInteger(target.history_index)) {{
            actionButtons.push({{
              kind: "history",
              history_index: Number(target.history_index),
              label: "Inspect Action",
              breadcrumb: "proof -> action snapshot -> mutation",
            }});
          }}
          if (Number.isInteger(target.timeline_event_index)) {{
            actionButtons.push({{
              kind: "timeline",
              timeline_event_index: Number(target.timeline_event_index),
              label: String(target.timeline_event_title || "").trim() ? `Inspect Timeline Event: ${{String(target.timeline_event_title || "").trim()}}` : "Inspect Timeline Event",
              breadcrumb: "proof -> timeline event -> chronology",
            }});
          }}
          detail.motion_artifact_focus_posture_snapshot_reason_focus = {{
            title: String(target.title || "Reopened Proof Focus").trim() || "Reopened Proof Focus",
            summary: String(target.summary || "Focused the stored proof excerpt behind this reopened next move.").trim() || "Focused the stored proof excerpt behind this reopened next move.",
            active_path_label: "proof focus",
            active_path_class: "first-seen",
            active_path_summary: "Active path: reopened proof focus.",
            return_history_reason_active_label: "",
            return_history_reason_active_class: "steady",
            return_history_reason_active_summary: "",
            return_history_reason_active_target: "",
            return_history_reason_active_buttons: [],
            return_history_reason_active_selection_label: "",
            return_history_reason_active_selection_class: "steady",
            return_history_reason_active_selection_summary: "",
            return_history_reason_resumed_label: "",
            return_history_reason_resumed_class: "steady",
            return_history_reason_resumed_summary: "",
            return_history_reason_resumed_active_label: "",
            return_history_reason_resumed_active_class: "steady",
            return_history_reason_resumed_active_summary: "",
            return_history_reason_resumed_active_buttons: [],
            return_history_reason_resumed_active_selection_label: "",
            return_history_reason_resumed_active_selection_class: "steady",
            return_history_reason_resumed_active_selection_summary: "",
            return_history_reason_resumed_return_label: "",
            return_history_reason_resumed_return_class: "steady",
            return_history_reason_resumed_return_summary: "",
            return_history_reason_resumed_return_button_label: "",
            return_history_reason_resumed_return_active_label: "",
            return_history_reason_resumed_return_active_class: "steady",
            return_history_reason_resumed_return_active_summary: "",
            return_history_reason_resumed_return_active_buttons: [],
            return_history_reason_resumed_return_active_selection_label: "",
            return_history_reason_resumed_return_active_selection_class: "steady",
            return_history_reason_resumed_return_active_selection_summary: "",
            return_history_reason_resumed_return_return_label: "",
            return_history_reason_resumed_return_return_class: "steady",
            return_history_reason_resumed_return_return_summary: "",
            return_history_reason_resumed_return_return_button_label: "",
            return_history_reason_resumed_return_return_active_label: "",
            return_history_reason_resumed_return_return_active_class: "steady",
            return_history_reason_resumed_return_return_active_summary: "",
            return_history_reason_resumed_return_return_active_buttons: [],
            return_history_reason_resumed_return_return_active_selection_label: "",
            return_history_reason_resumed_return_return_active_selection_class: "steady",
            return_history_reason_resumed_return_return_active_selection_summary: "",
            return_history_reason_resumed_return_return_return_label: "",
            return_history_reason_resumed_return_return_return_class: "steady",
            return_history_reason_resumed_return_return_return_summary: "",
            return_history_reason_resumed_return_return_return_active_label: "",
            return_history_reason_resumed_return_return_return_active_class: "steady",
            return_history_reason_resumed_return_return_return_active_summary: "",
            return_history_reason_resumed_return_return_return_active_buttons: [],
            return_history_reason_resumed_return_return_return_active_selection_label: "",
            return_history_reason_resumed_return_return_return_active_selection_class: "steady",
            return_history_reason_resumed_return_return_return_active_selection_summary: "",
            return_history_reason_resumed_return_return_return_return_label: "",
            return_history_reason_resumed_return_return_return_return_class: "steady",
            return_history_reason_resumed_return_return_return_return_summary: "",
            return_history_reason_resumed_return_return_return_return_buttons: [],
            return_history_reason_resumed_return_return_return_return_return_label: "",
            return_history_reason_resumed_return_return_return_return_return_class: "steady",
            return_history_reason_resumed_return_return_return_return_return_summary: "",
            return_history_reason_resumed_return_return_return_return_return_buttons: [],
            return_history_reason_resumed_return_return_return_return_return_active_label: "",
            return_history_reason_resumed_return_return_return_return_return_active_class: "steady",
            return_history_reason_resumed_return_return_return_return_return_active_summary: "",
            return_history_reason_resumed_return_return_return_return_return_return_label: "",
            return_history_reason_resumed_return_return_return_return_return_return_class: "steady",
            return_history_reason_resumed_return_return_return_return_return_return_summary: "",
            return_history_reason_resumed_return_return_return_return_return_return_buttons: [],
            return_history_reason_resumed_return_return_return_return_return_return_active_label: "",
            return_history_reason_resumed_return_return_return_return_return_return_active_class: "steady",
            return_history_reason_resumed_return_return_return_return_return_return_active_summary: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_label: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_class: "steady",
            return_history_reason_resumed_return_return_return_return_return_return_return_summary: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_buttons: [],
            return_history_reason_resumed_return_return_return_return_return_return_return_active_label: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_active_class: "steady",
            return_history_reason_resumed_return_return_return_return_return_return_return_active_summary: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_label: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_class: "steady",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_summary: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_buttons: [],
            return_history_reason_resumed_return_return_return_return_return_return_return_return_active_label: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_active_class: "steady",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_active_summary: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_label: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_class: "steady",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_summary: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_buttons: [],
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_buttons: [],
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_active_label: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_active_class: "steady",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_active_summary: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_label: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_class: "steady",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_summary: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_buttons: [],
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_label: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_class: "steady",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_summary: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_buttons: [],
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_label: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_class: "steady",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_summary: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_buttons: [],
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_label: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_class: "steady",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_summary: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_buttons: [],
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_label: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_class: "steady",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_summary: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_label: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_class: "steady",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_summary: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_label: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_class: "steady",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_summary: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_buttons: [],
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_buttons: [],
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_label: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_class: "steady",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_summary: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_label: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_class: "steady",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_summary: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_active_label: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_active_class: "steady",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_active_summary: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_active_label: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_active_class: "steady",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_active_summary: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_active_label: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_active_class: "steady",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_active_summary: "",
            return_history_reason_resumed_return_return_return_return_active_label: "",
            return_history_reason_resumed_return_return_return_return_active_class: "steady",
            return_history_reason_resumed_return_return_return_return_active_summary: "",
            context_summary: "",
            context_buttons: [],
            context_selection_label: "",
            context_selection_class: "steady",
            context_selection_target: "",
            context_selection_buttons: [],
            context_selection_confirmation_label: "",
            context_selection_confirmation_class: "steady",
            return_confirmation_label: "",
            return_confirmation_class: "steady",
            return_confirmation_summary: "",
            return_summary: "",
            return_history_index: null,
            return_history_label: "",
            return_history_reason: "",
            return_history_reason_button_label: "",
            return_history_reason_source_label: "",
            return_history_reason_source_class: "artifact",
            return_history_origin_label: "",
            return_history_origin_class: "artifact",
            return_history_lane_label: "",
            return_history_lane_class: "steady",
            pivot_summary: pivotSummaryForButtons(actionButtons),
            pivot_buttons: pivotButtonsForActions(actionButtons),
            rows: [
              {{ label: "Source", value: "Artifact Proof Excerpts" }},
              {{ label: "Excerpt", value: excerpt }},
            ],
            action_buttons: actionButtons,
          }};
        }}
        return detail;
      }}
      if (target.kind === "compare") {{
        const row = compareRows[Number(target.index)] || null;
        if (row && String(row.value || "").trim()) {{
          const actionButtons = [];
          if (Number.isInteger(target.history_index)) {{
            actionButtons.push({{
              kind: "history",
              history_index: Number(target.history_index),
              label: "Inspect Action",
              breadcrumb: "proof -> action snapshot -> mutation",
            }});
          }}
          if (Number.isInteger(target.timeline_event_index)) {{
            actionButtons.push({{
              kind: "timeline",
              timeline_event_index: Number(target.timeline_event_index),
              label: String(target.timeline_event_title || "").trim() ? `Inspect Timeline Event: ${{String(target.timeline_event_title || "").trim()}}` : "Inspect Timeline Event",
              breadcrumb: "proof -> timeline event -> chronology",
            }});
          }}
          detail.motion_artifact_focus_posture_snapshot_reason_focus = {{
            title: String(target.title || "Reopened Proof Focus").trim() || "Reopened Proof Focus",
            summary: String(target.summary || "Focused the stored proof comparison row behind this reopened next move.").trim() || "Focused the stored proof comparison row behind this reopened next move.",
            active_path_label: "proof focus",
            active_path_class: "first-seen",
            active_path_summary: "Active path: reopened proof focus.",
            return_history_reason_active_label: "",
            return_history_reason_active_class: "steady",
            return_history_reason_active_summary: "",
            return_history_reason_active_target: "",
            return_history_reason_active_buttons: [],
            return_history_reason_active_selection_label: "",
            return_history_reason_active_selection_class: "steady",
            return_history_reason_active_selection_summary: "",
            return_history_reason_resumed_label: "",
            return_history_reason_resumed_class: "steady",
            return_history_reason_resumed_summary: "",
            return_history_reason_resumed_active_label: "",
            return_history_reason_resumed_active_class: "steady",
            return_history_reason_resumed_active_summary: "",
            return_history_reason_resumed_active_buttons: [],
            return_history_reason_resumed_active_selection_label: "",
            return_history_reason_resumed_active_selection_class: "steady",
            return_history_reason_resumed_active_selection_summary: "",
            return_history_reason_resumed_return_label: "",
            return_history_reason_resumed_return_class: "steady",
            return_history_reason_resumed_return_summary: "",
            return_history_reason_resumed_return_button_label: "",
            return_history_reason_resumed_return_active_label: "",
            return_history_reason_resumed_return_active_class: "steady",
            return_history_reason_resumed_return_active_summary: "",
            return_history_reason_resumed_return_active_buttons: [],
            return_history_reason_resumed_return_active_selection_label: "",
            return_history_reason_resumed_return_active_selection_class: "steady",
            return_history_reason_resumed_return_active_selection_summary: "",
            return_history_reason_resumed_return_return_label: "",
            return_history_reason_resumed_return_return_class: "steady",
            return_history_reason_resumed_return_return_summary: "",
            return_history_reason_resumed_return_return_button_label: "",
            return_history_reason_resumed_return_return_active_label: "",
            return_history_reason_resumed_return_return_active_class: "steady",
            return_history_reason_resumed_return_return_active_summary: "",
            return_history_reason_resumed_return_return_active_buttons: [],
            return_history_reason_resumed_return_return_active_selection_label: "",
            return_history_reason_resumed_return_return_active_selection_class: "steady",
            return_history_reason_resumed_return_return_active_selection_summary: "",
            return_history_reason_resumed_return_return_return_label: "",
            return_history_reason_resumed_return_return_return_class: "steady",
            return_history_reason_resumed_return_return_return_summary: "",
            return_history_reason_resumed_return_return_return_active_label: "",
            return_history_reason_resumed_return_return_return_active_class: "steady",
            return_history_reason_resumed_return_return_return_active_summary: "",
            return_history_reason_resumed_return_return_return_active_buttons: [],
            return_history_reason_resumed_return_return_return_active_selection_label: "",
            return_history_reason_resumed_return_return_return_active_selection_class: "steady",
            return_history_reason_resumed_return_return_return_active_selection_summary: "",
            return_history_reason_resumed_return_return_return_return_label: "",
            return_history_reason_resumed_return_return_return_return_class: "steady",
            return_history_reason_resumed_return_return_return_return_summary: "",
            return_history_reason_resumed_return_return_return_return_buttons: [],
            return_history_reason_resumed_return_return_return_return_return_label: "",
            return_history_reason_resumed_return_return_return_return_return_class: "steady",
            return_history_reason_resumed_return_return_return_return_return_summary: "",
            return_history_reason_resumed_return_return_return_return_return_buttons: [],
            return_history_reason_resumed_return_return_return_return_return_active_label: "",
            return_history_reason_resumed_return_return_return_return_return_active_class: "steady",
            return_history_reason_resumed_return_return_return_return_return_active_summary: "",
            return_history_reason_resumed_return_return_return_return_return_return_label: "",
            return_history_reason_resumed_return_return_return_return_return_return_class: "steady",
            return_history_reason_resumed_return_return_return_return_return_return_summary: "",
            return_history_reason_resumed_return_return_return_return_return_return_buttons: [],
            return_history_reason_resumed_return_return_return_return_return_return_active_label: "",
            return_history_reason_resumed_return_return_return_return_return_return_active_class: "steady",
            return_history_reason_resumed_return_return_return_return_return_return_active_summary: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_label: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_class: "steady",
            return_history_reason_resumed_return_return_return_return_return_return_return_summary: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_buttons: [],
            return_history_reason_resumed_return_return_return_return_return_return_return_active_label: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_active_class: "steady",
            return_history_reason_resumed_return_return_return_return_return_return_return_active_summary: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_label: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_class: "steady",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_summary: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_buttons: [],
            return_history_reason_resumed_return_return_return_return_return_return_return_return_active_label: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_active_class: "steady",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_active_summary: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_label: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_class: "steady",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_summary: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_buttons: [],
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_buttons: [],
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_active_label: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_active_class: "steady",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_active_summary: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_label: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_class: "steady",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_summary: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_buttons: [],
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_label: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_class: "steady",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_summary: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_buttons: [],
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_label: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_class: "steady",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_summary: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_buttons: [],
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_label: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_class: "steady",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_summary: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_buttons: [],
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_label: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_class: "steady",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_summary: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_label: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_class: "steady",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_summary: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_buttons: [],
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_buttons: [],
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_label: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_class: "steady",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_summary: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_label: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_class: "steady",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_summary: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_active_label: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_active_class: "steady",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_active_summary: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_active_label: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_active_class: "steady",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_active_summary: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_active_label: "",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_active_class: "steady",
            return_history_reason_resumed_return_return_return_return_return_return_return_return_return_active_summary: "",
            return_history_reason_resumed_return_return_return_return_active_label: "",
            return_history_reason_resumed_return_return_return_return_active_class: "steady",
            return_history_reason_resumed_return_return_return_return_active_summary: "",
            context_summary: "",
            context_buttons: [],
            context_selection_label: "",
            context_selection_class: "steady",
            context_selection_target: "",
            context_selection_buttons: [],
            context_selection_confirmation_label: "",
            context_selection_confirmation_class: "steady",
            return_confirmation_label: "",
            return_confirmation_class: "steady",
            return_confirmation_summary: "",
            return_summary: "",
            return_history_index: null,
            return_history_label: "",
            return_history_reason: "",
            return_history_reason_button_label: "",
            return_history_reason_source_label: "",
            return_history_reason_source_class: "artifact",
            return_history_origin_label: "",
            return_history_origin_class: "artifact",
            return_history_lane_label: "",
            return_history_lane_class: "steady",
            pivot_summary: pivotSummaryForButtons(actionButtons),
            pivot_buttons: pivotButtonsForActions(actionButtons),
            rows: [
              {{ label: "Source", value: "Artifact Proof Compare" }},
              {{ label: String(row.label || "Proof Row").trim() || "Proof Row", value: String(row.value || "").trim() }},
            ],
            action_buttons: actionButtons,
          }};
        }}
      }}
      return detail;
    }}

    function motionArtifactSnapshotPathMeta(pathKind) {{
      if (pathKind === "mutation") {{
        return {{
          label: "mutation lane",
          className: "shifted",
          summary: "Active path: reopened mutation lane.",
        }};
      }}
      if (pathKind === "chronology") {{
        return {{
          label: "chronology lane",
          className: "recovered",
          summary: "Active path: reopened chronology lane.",
        }};
      }}
      return {{
        label: "proof focus",
        className: "first-seen",
        summary: "Active path: reopened proof focus.",
      }};
    }}

    function motionArtifactSnapshotTargetLabel(detail, pathKind = "proof") {{
      const valueMap = motionArtifactFocusValueMap(detail);
      const focusKind = motionArtifactFocusKind(detail);
      const pathLabel = pathKind === "mutation" ? "mutation lane" : pathKind === "chronology" ? "chronology lane" : "proof focus";
      if (focusKind === "approval") {{
        const requestId = String(valueMap["Request ID"] || detail.request_id || detail.item_id || "not attached").trim();
        return `Active target: ${{pathLabel}} for approval request ${{requestId}}.`;
      }}
      if (focusKind === "notification") {{
        const notificationId = String(valueMap["Notification ID"] || detail.notification_id || detail.item_id || "not attached").trim();
        return `Active target: ${{pathLabel}} for inbox item ${{notificationId}}.`;
      }}
      if (focusKind === "open-loop") {{
        const itemId = String(valueMap["Item ID"] || detail.item_id || "not attached").trim();
        return `Active target: ${{pathLabel}} for workflow item ${{itemId}}.`;
      }}
      return `Active target: ${{pathLabel}} for the current localized record.`;
    }}

    function motionArtifactSnapshotRecordLabel(detail) {{
      const valueMap = motionArtifactFocusValueMap(detail);
      const focusKind = motionArtifactFocusKind(detail);
      if (focusKind === "approval") {{
        const requestId = String(valueMap["Request ID"] || detail.request_id || detail.item_id || "not attached").trim();
        return `approval request ${{requestId}}`;
      }}
      if (focusKind === "notification") {{
        const notificationId = String(valueMap["Notification ID"] || detail.notification_id || detail.item_id || "not attached").trim();
        return `inbox item ${{notificationId}}`;
      }}
      if (focusKind === "open-loop") {{
        const itemId = String(valueMap["Item ID"] || detail.item_id || "not attached").trim();
        return `workflow item ${{itemId}}`;
      }}
      return "the current localized record";
    }}

    function motionArtifactSnapshotReturnSummary(detail) {{
      const rows = detail && Array.isArray(detail.motion_artifact_focus_history_rows) ? detail.motion_artifact_focus_history_rows : [];
      const latestRow = rows[0] && typeof rows[0] === "object" ? rows[0] : null;
      const latestBadge = String((latestRow && latestRow.badge) || "").trim();
      const latestOutcome = motionArtifactSnapshotReturnOutcome(detail);
      const focusKind = motionArtifactFocusKind(detail);
      const originMeta = motionArtifactSnapshotReturnOriginMeta(detail);
      const originLabel = String((originMeta && originMeta.label) || "").trim().toLowerCase();
      const recordLabel = motionArtifactSnapshotRecordLabel(detail);
      if (focusKind === "approval") {{
        if (latestOutcome === "failed") {{
          return latestBadge
            ? `Approval failure proof resumed for ${{recordLabel}} after ${{latestBadge}}.`
            : `Approval failure proof resumed for ${{recordLabel}}.`;
        }}
        if (originLabel === "approval mutation") {{
          return latestBadge
            ? `Approval mutation resumed for ${{recordLabel}} after ${{latestBadge}}.`
            : `Approval mutation resumed for ${{recordLabel}}.`;
        }}
        return latestBadge
          ? `Approval proof resumed for ${{recordLabel}} after ${{latestBadge}}.`
          : `Approval proof resumed for ${{recordLabel}}.`;
      }}
      if (focusKind === "notification") {{
        if (latestOutcome === "opened") {{
          return latestBadge
            ? `Inbox opened proof resumed for ${{recordLabel}} after ${{latestBadge}}.`
            : `Inbox opened proof resumed for ${{recordLabel}}.`;
        }}
        if (latestOutcome === "failed") {{
          return latestBadge
            ? `Inbox failure proof resumed for ${{recordLabel}} after ${{latestBadge}}.`
            : `Inbox failure proof resumed for ${{recordLabel}}.`;
        }}
        return latestBadge
          ? `Inbox proof resumed for ${{recordLabel}} after ${{latestBadge}}.`
          : `Inbox proof resumed for ${{recordLabel}}.`;
      }}
      if (focusKind === "open-loop") {{
        if (latestOutcome === "failed" && originLabel === "workflow chronology") {{
          return latestBadge
            ? `Workflow failure chronology resumed for ${{recordLabel}} after ${{latestBadge}}.`
            : `Workflow failure chronology resumed for ${{recordLabel}}.`;
        }}
        if (originLabel === "workflow chronology") {{
          return latestBadge
            ? `Workflow chronology resumed for ${{recordLabel}} after ${{latestBadge}}.`
            : `Workflow chronology resumed for ${{recordLabel}}.`;
        }}
        if (latestOutcome === "failed") {{
          return latestBadge
            ? `Workflow failure proof resumed for ${{recordLabel}} after ${{latestBadge}}.`
            : `Workflow failure proof resumed for ${{recordLabel}}.`;
        }}
        return latestBadge
          ? `Workflow proof resumed for ${{recordLabel}} after ${{latestBadge}}.`
          : `Workflow proof resumed for ${{recordLabel}}.`;
      }}
      return latestBadge
        ? `Localized proof resumed for ${{recordLabel}} after ${{latestBadge}}.`
        : `Localized proof resumed for ${{recordLabel}}.`;
    }}

    function motionArtifactSnapshotTargetButtons(detail) {{
      const buttons = [];
      if (Number.isInteger(currentMotionArtifactIndex)) {{
        buttons.push({{
          kind: "artifact",
          motion_artifact_index: currentMotionArtifactIndex,
          label: "Inspect Exact Artifact",
        }});
      }}
      const target = detail && detail.motion_artifact_focus_posture_snapshot_reason_target && typeof detail.motion_artifact_focus_posture_snapshot_reason_target === "object"
        ? detail.motion_artifact_focus_posture_snapshot_reason_target
        : null;
      if (target && Number.isInteger(target.timeline_event_index)) {{
        buttons.push({{
          kind: "timeline",
          timeline_event_index: Number(target.timeline_event_index),
          label: "Inspect Matching Timeline",
        }});
      }}
      return buttons;
    }}

    function motionArtifactSnapshotReturnOriginMeta(detail) {{
      const target = detail && detail.motion_artifact_focus_posture_snapshot_reason_target && typeof detail.motion_artifact_focus_posture_snapshot_reason_target === "object"
        ? detail.motion_artifact_focus_posture_snapshot_reason_target
        : null;
      const focusKind = motionArtifactFocusKind(detail);
      if (focusKind === "approval") {{
        return target && target.kind === "compare"
          ? {{ label: "approval mutation", className: "approval" }}
          : {{ label: "approval proof", className: "approval" }};
      }}
      if (focusKind === "notification") {{
        return {{ label: "inbox proof", className: "notification" }};
      }}
      if (focusKind === "open-loop") {{
        return target && target.kind === "compare"
          ? {{ label: "workflow chronology", className: "open-loop" }}
          : {{ label: "workflow proof", className: "open-loop" }};
      }}
      return {{ label: "latest outcome", className: "artifact" }};
    }}

    function motionArtifactSnapshotReturnOutcome(detail) {{
      const rows = detail && Array.isArray(detail.motion_artifact_focus_history_rows) ? detail.motion_artifact_focus_history_rows : [];
      const latestRow = rows[0] && typeof rows[0] === "object" ? rows[0] : null;
      const badge = String((latestRow && latestRow.badge) || "").trim().toLowerCase();
      if (badge.includes("/")) {{
        return badge.split("/").pop().trim();
      }}
      return "";
    }}

    function motionArtifactSnapshotReturnActionLabel(originMeta, detail) {{
      const label = String((originMeta && originMeta.label) || "").trim().toLowerCase();
      const outcome = motionArtifactSnapshotReturnOutcome(detail);
      if (label === "approval mutation") return outcome === "failed" ? "Reopen Approval Failure Proof" : "Reopen Approval Mutation";
      if (label === "approval proof") return "Reopen Approval Proof";
      if (label === "inbox proof") return outcome === "opened" ? "Reopen Inbox Opened Proof" : outcome === "failed" ? "Reopen Inbox Failure Proof" : "Reopen Inbox Proof";
      if (label === "workflow chronology") return outcome === "failed" ? "Reopen Workflow Failure Chronology" : "Reopen Workflow Chronology";
      if (label === "workflow proof") return outcome === "failed" ? "Reopen Workflow Failure Proof" : "Reopen Workflow Proof";
      return "Reopen Latest Outcome";
    }}

    function motionArtifactSnapshotReturnActionReason(originMeta, detail) {{
      const label = String((originMeta && originMeta.label) || "").trim().toLowerCase();
      const outcome = motionArtifactSnapshotReturnOutcome(detail);
      const recordLabel = motionArtifactSnapshotRecordLabel(detail);
      if (label === "approval mutation") return outcome === "failed" ? `Reopens the stored approval failure proof for ${{recordLabel}}.` : `Reopens the stored approval mutation for ${{recordLabel}}.`;
      if (label === "approval proof") return `Reopens the stored approval proof for ${{recordLabel}}.`;
      if (label === "inbox proof") return outcome === "opened" ? `Reopens the stored inbox-opened proof for ${{recordLabel}}.` : outcome === "failed" ? `Reopens the stored inbox failure proof for ${{recordLabel}}.` : `Reopens the stored inbox proof for ${{recordLabel}}.`;
      if (label === "workflow chronology") return outcome === "failed" ? `Reopens the stored workflow failure chronology for ${{recordLabel}}.` : `Reopens the stored workflow chronology for ${{recordLabel}}.`;
      if (label === "workflow proof") return outcome === "failed" ? `Reopens the stored workflow failure proof for ${{recordLabel}}.` : `Reopens the stored workflow proof for ${{recordLabel}}.`;
      return `Reopens the latest stored outcome for ${{recordLabel}}.`;
    }}

    function motionArtifactSnapshotReturnReasonButtonLabel(detail) {{
      const target = detail && detail.motion_artifact_focus_posture_snapshot_reason_target && typeof detail.motion_artifact_focus_posture_snapshot_reason_target === "object"
        ? detail.motion_artifact_focus_posture_snapshot_reason_target
        : null;
      if (!target) return "";
      if (target.kind === "excerpt") return "Inspect Reopened Proof Excerpt";
      if (target.kind === "compare") return "Inspect Reopened Proof Compare";
      return "Inspect Reopened Evidence";
    }}

    function motionArtifactSnapshotReturnReasonSourceMeta(detail) {{
      const target = detail && detail.motion_artifact_focus_posture_snapshot_reason_target && typeof detail.motion_artifact_focus_posture_snapshot_reason_target === "object"
        ? detail.motion_artifact_focus_posture_snapshot_reason_target
        : null;
      if (!target) return {{ label: "", className: "artifact" }};
      if (target.kind === "excerpt") return {{ label: "proof excerpt", className: "first-seen" }};
      if (target.kind === "compare") return {{ label: "proof compare", className: "approval" }};
      if (Number.isInteger(target.timeline_event_index)) return {{ label: "chronology evidence", className: "open-loop" }};
      return {{ label: "stored evidence", className: "artifact" }};
    }}

    function motionArtifactSnapshotReasonActiveMeta(detail) {{
      const sourceMeta = motionArtifactSnapshotReturnReasonSourceMeta(detail);
      const label = String((sourceMeta && sourceMeta.label) || "").trim().toLowerCase();
      if (label === "proof excerpt") {{
        return {{
          label: "excerpt proof active",
          className: "first-seen",
          summary: "The reopened proof pane is now anchored on the stored proof excerpt.",
        }};
      }}
      if (label === "proof compare") {{
        return {{
          label: "compare proof active",
          className: "approval",
          summary: "The reopened proof pane is now anchored on the stored proof compare row.",
        }};
      }}
      if (label === "chronology evidence") {{
        return {{
          label: "chronology evidence active",
          className: "open-loop",
          summary: "The reopened proof pane is now anchored on the linked chronology evidence.",
        }};
      }}
      return {{
        label: "stored evidence active",
        className: String((sourceMeta && sourceMeta.className) || "artifact").trim() || "artifact",
        summary: "The reopened proof pane is now anchored on the stored evidence behind this lane.",
      }};
    }}

    function motionArtifactSnapshotReasonActiveTarget(detail) {{
      return `Anchored evidence: ${{motionArtifactSnapshotRecordLabel(detail)}}.`;
    }}

    function motionArtifactSnapshotReasonActiveButtons(detail) {{
      const buttons = [];
      const targetButtons = motionArtifactSnapshotTargetButtons(detail);
      for (const item of targetButtons) {{
        if (!item || typeof item !== "object") continue;
        if (item.kind === "artifact" && Number.isInteger(item.motion_artifact_index)) {{
          buttons.push({{
            kind: "artifact",
            motion_artifact_index: Number(item.motion_artifact_index),
            label: "Open Evidence Artifact",
          }});
        }} else if (item.kind === "timeline" && Number.isInteger(item.timeline_event_index)) {{
          buttons.push({{
            kind: "timeline",
            timeline_event_index: Number(item.timeline_event_index),
            label: "Open Evidence Timeline",
          }});
        }}
      }}
      return buttons;
    }}

    function motionArtifactSnapshotReasonSelectionMeta(targetKind, detail) {{
      const recordLabel = motionArtifactSnapshotRecordLabel(detail);
      if (targetKind === "artifact") {{
        return {{
          label: "evidence artifact active",
          className: "accepted",
          summary: `Following the evidence artifact for ${{recordLabel}}.`,
        }};
      }}
      if (targetKind === "timeline") {{
        return {{
          label: "evidence timeline active",
          className: "recovered",
          summary: `Following the evidence timeline for ${{recordLabel}}.`,
        }};
      }}
      return {{
        label: "",
        className: "steady",
        summary: "",
      }};
    }}

    function motionArtifactSnapshotReasonResumeMeta(detail) {{
      const target = detail && detail.motion_artifact_focus_posture_snapshot_reason_target && typeof detail.motion_artifact_focus_posture_snapshot_reason_target === "object"
        ? detail.motion_artifact_focus_posture_snapshot_reason_target
        : null;
      const recordLabel = motionArtifactSnapshotRecordLabel(detail);
      if (target && target.kind === "excerpt") {{
        return {{
          label: "excerpt proof resumed",
          className: "first-seen",
          summary: `Restored the stored proof excerpt for ${{recordLabel}}.`,
        }};
      }}
      if (target && target.kind === "compare") {{
        return {{
          label: "compare proof resumed",
          className: "approval",
          summary: `Restored the stored proof compare row for ${{recordLabel}}.`,
        }};
      }}
      if (target && Number.isInteger(target.timeline_event_index)) {{
        return {{
          label: "chronology evidence resumed",
          className: "open-loop",
          summary: `Restored the linked chronology evidence for ${{recordLabel}}.`,
        }};
      }}
      return {{
        label: "stored evidence resumed",
        className: "artifact",
        summary: `Restored the stored evidence for ${{recordLabel}}.`,
      }};
    }}

    function motionArtifactSnapshotReasonResumedActiveMeta(detail) {{
      const sourceMeta = motionArtifactSnapshotReturnReasonSourceMeta(detail);
      const recordLabel = motionArtifactSnapshotRecordLabel(detail);
      const label = String((sourceMeta && sourceMeta.label) || "").trim().toLowerCase();
      if (label === "proof excerpt") {{
        return {{
          label: "restored excerpt active",
          className: "first-seen",
          summary: `The restored evidence row reopened the stored proof excerpt for ${{recordLabel}}.`,
        }};
      }}
      if (label === "proof compare") {{
        return {{
          label: "restored compare active",
          className: "approval",
          summary: `The restored evidence row reopened the stored proof compare row for ${{recordLabel}}.`,
        }};
      }}
      if (label === "chronology evidence") {{
        return {{
          label: "restored chronology active",
          className: "open-loop",
          summary: `The restored evidence row reopened the linked chronology evidence for ${{recordLabel}}.`,
        }};
      }}
      return {{
        label: "restored evidence active",
        className: String((sourceMeta && sourceMeta.className) || "artifact").trim() || "artifact",
        summary: `The restored evidence row reopened the stored evidence for ${{recordLabel}}.`,
      }};
    }}

    function motionArtifactSnapshotReasonResumedActiveButtons(detail) {{
      const buttons = [];
      const targetButtons = motionArtifactSnapshotTargetButtons(detail);
      for (const item of targetButtons) {{
        if (!item || typeof item !== "object") continue;
        if (item.kind === "artifact" && Number.isInteger(item.motion_artifact_index)) {{
          buttons.push({{
            kind: "artifact",
            motion_artifact_index: Number(item.motion_artifact_index),
            label: "Open Restored Evidence Artifact",
          }});
        }} else if (item.kind === "timeline" && Number.isInteger(item.timeline_event_index)) {{
          buttons.push({{
            kind: "timeline",
            timeline_event_index: Number(item.timeline_event_index),
            label: "Open Restored Evidence Timeline",
          }});
        }}
      }}
      return buttons;
    }}

    function motionArtifactSnapshotReasonResumedSelectionMeta(targetKind, detail) {{
      const recordLabel = motionArtifactSnapshotRecordLabel(detail);
      if (targetKind === "artifact") {{
        return {{
          label: "restored evidence artifact active",
          className: "accepted",
          summary: `Following the restored evidence artifact for ${{recordLabel}}.`,
        }};
      }}
      if (targetKind === "timeline") {{
        return {{
          label: "restored evidence timeline active",
          className: "recovered",
          summary: `Following the restored evidence timeline for ${{recordLabel}}.`,
        }};
      }}
      return {{
        label: "",
        className: "steady",
        summary: "",
      }};
    }}

    function motionArtifactSnapshotReasonResumedReturnMeta(detail, selectionLabel) {{
      const resumed = motionArtifactSnapshotReasonResumeMeta(detail);
      const recordLabel = motionArtifactSnapshotRecordLabel(detail);
      const selection = String(selectionLabel || "").trim().toLowerCase();
      const resumedLabel = String((resumed && resumed.label) || "stored evidence resumed").trim() || "stored evidence resumed";
      if (selection.includes("timeline")) {{
        return {{
          label: "restored evidence lane resumed",
          className: "recovered",
          summary: `Resumed ${{resumedLabel}} for ${{recordLabel}} after returning from the restored evidence timeline.`,
        }};
      }}
      if (selection.includes("artifact")) {{
        return {{
          label: "restored evidence lane resumed",
          className: "accepted",
          summary: `Resumed ${{resumedLabel}} for ${{recordLabel}} after returning from the restored evidence artifact.`,
        }};
      }}
      return {{
        label: "restored evidence lane resumed",
        className: String((resumed && resumed.className) || "steady").trim() || "steady",
        summary: `Resumed ${{resumedLabel}} for ${{recordLabel}}.`,
      }};
    }}

    function motionArtifactSnapshotReasonResumedReturnButtonLabel(detail) {{
      const sourceMeta = motionArtifactSnapshotReturnReasonSourceMeta(detail);
      const label = String((sourceMeta && sourceMeta.label) || "").trim().toLowerCase();
      if (label === "proof excerpt") {{
        return "Inspect Resumed Excerpt";
      }}
      if (label === "proof compare") {{
        return "Inspect Resumed Compare";
      }}
      if (label === "chronology evidence") {{
        return "Inspect Resumed Chronology";
      }}
      return "Inspect Resumed Evidence";
    }}

    function motionArtifactSnapshotReasonResumedReturnActiveMeta(detail) {{
      const sourceMeta = motionArtifactSnapshotReturnReasonSourceMeta(detail);
      const recordLabel = motionArtifactSnapshotRecordLabel(detail);
      const label = String((sourceMeta && sourceMeta.label) || "").trim().toLowerCase();
      if (label === "proof excerpt") {{
        return {{
          label: "resumed excerpt active",
          className: "first-seen",
          summary: `The resumed evidence row reopened the stored proof excerpt for ${{recordLabel}}.`,
        }};
      }}
      if (label === "proof compare") {{
        return {{
          label: "resumed compare active",
          className: "approval",
          summary: `The resumed evidence row reopened the stored proof compare row for ${{recordLabel}}.`,
        }};
      }}
      if (label === "chronology evidence") {{
        return {{
          label: "resumed chronology active",
          className: "open-loop",
          summary: `The resumed evidence row reopened the linked chronology evidence for ${{recordLabel}}.`,
        }};
      }}
      return {{
        label: "resumed evidence active",
        className: String((sourceMeta && sourceMeta.className) || "artifact").trim() || "artifact",
        summary: `The resumed evidence row reopened the stored evidence for ${{recordLabel}}.`,
      }};
    }}

    function motionArtifactSnapshotReasonResumedReturnActiveButtons(detail) {{
      const buttons = [];
      const targetButtons = motionArtifactSnapshotTargetButtons(detail);
      for (const item of targetButtons) {{
        if (!item || typeof item !== "object") continue;
        if (item.kind === "artifact" && Number.isInteger(item.motion_artifact_index)) {{
          buttons.push({{
            kind: "artifact",
            motion_artifact_index: Number(item.motion_artifact_index),
            label: "Open Resumed Evidence Artifact",
          }});
        }} else if (item.kind === "timeline" && Number.isInteger(item.timeline_event_index)) {{
          buttons.push({{
            kind: "timeline",
            timeline_event_index: Number(item.timeline_event_index),
            label: "Open Resumed Evidence Timeline",
          }});
        }}
      }}
      return buttons;
    }}

    function motionArtifactSnapshotReasonResumedReturnSelectionMeta(targetKind, detail) {{
      const recordLabel = motionArtifactSnapshotRecordLabel(detail);
      if (targetKind === "artifact") {{
        return {{
          label: "resumed evidence artifact active",
          className: "accepted",
          summary: `Following the resumed evidence artifact for ${{recordLabel}}.`,
        }};
      }}
      if (targetKind === "timeline") {{
        return {{
          label: "resumed evidence timeline active",
          className: "recovered",
          summary: `Following the resumed evidence timeline for ${{recordLabel}}.`,
        }};
      }}
      return {{
        label: "",
        className: "steady",
        summary: "",
      }};
    }}

    function motionArtifactSnapshotReasonResumedReturnReturnSelectionMeta(targetKind, detail) {{
      const recordLabel = motionArtifactSnapshotRecordLabel(detail);
      if (targetKind === "artifact") {{
        return {{
          label: "resumed restored evidence artifact active",
          className: "accepted",
          summary: `Following the resumed restored evidence artifact for ${{recordLabel}}.`,
        }};
      }}
      if (targetKind === "timeline") {{
        return {{
          label: "resumed restored evidence timeline active",
          className: "recovered",
          summary: `Following the resumed restored evidence timeline for ${{recordLabel}}.`,
        }};
      }}
      return {{
        label: "",
        className: "steady",
        summary: "",
      }};
    }}

    function motionArtifactSnapshotReasonResumedReturnReturnMeta(detail, selectionLabel) {{
      const resumed = motionArtifactSnapshotReasonResumeMeta(detail);
      const recordLabel = motionArtifactSnapshotRecordLabel(detail);
      const selection = String(selectionLabel || "").trim().toLowerCase();
      const resumedLabel = String((resumed && resumed.label) || "stored evidence resumed").trim() || "stored evidence resumed";
      if (selection.includes("timeline")) {{
        return {{
          label: "resumed evidence lane restored",
          className: "recovered",
          summary: `Restored ${{resumedLabel}} for ${{recordLabel}} after returning from the resumed evidence timeline.`,
        }};
      }}
      if (selection.includes("artifact")) {{
        return {{
          label: "resumed evidence lane restored",
          className: "accepted",
          summary: `Restored ${{resumedLabel}} for ${{recordLabel}} after returning from the resumed evidence artifact.`,
        }};
      }}
      return {{
        label: "resumed evidence lane restored",
        className: String((resumed && resumed.className) || "steady").trim() || "steady",
        summary: `Restored ${{resumedLabel}} for ${{recordLabel}}.`,
      }};
    }}

    function motionArtifactSnapshotReasonResumedReturnReturnActiveMeta(detail) {{
      const sourceMeta = motionArtifactSnapshotReturnReasonSourceMeta(detail);
      const recordLabel = motionArtifactSnapshotRecordLabel(detail);
      const label = String((sourceMeta && sourceMeta.label) || "").trim().toLowerCase();
      if (label === "proof excerpt") {{
        return {{
          label: "resumed restored excerpt active",
          className: "first-seen",
          summary: `The resumed restored row reopened the stored proof excerpt for ${{recordLabel}}.`,
        }};
      }}
      if (label === "proof compare") {{
        return {{
          label: "resumed restored compare active",
          className: "approval",
          summary: `The resumed restored row reopened the stored proof compare row for ${{recordLabel}}.`,
        }};
      }}
      if (label === "chronology evidence") {{
        return {{
          label: "resumed restored chronology active",
          className: "open-loop",
          summary: `The resumed restored row reopened the linked chronology evidence for ${{recordLabel}}.`,
        }};
      }}
      return {{
        label: "resumed restored evidence active",
        className: String((sourceMeta && sourceMeta.className) || "artifact").trim() || "artifact",
        summary: `The resumed restored row reopened the stored evidence for ${{recordLabel}}.`,
      }};
    }}

    function motionArtifactSnapshotReasonResumedReturnReturnReturnMeta(detail, selectionLabel) {{
      const resumedReturnReturnActive = motionArtifactSnapshotReasonResumedReturnReturnActiveMeta(detail);
      const recordLabel = motionArtifactSnapshotRecordLabel(detail);
      const selection = String(selectionLabel || "").trim().toLowerCase();
      const resumedLabel = String((resumedReturnReturnActive && resumedReturnReturnActive.label) || "resumed restored evidence active").trim() || "resumed restored evidence active";
      if (selection.includes("timeline")) {{
        return {{
          label: "resumed restored evidence lane resumed",
          className: "recovered",
          summary: `Resumed ${{resumedLabel}} for ${{recordLabel}} after returning from the resumed restored evidence timeline.`,
        }};
      }}
      if (selection.includes("artifact")) {{
        return {{
          label: "resumed restored evidence lane resumed",
          className: "accepted",
          summary: `Resumed ${{resumedLabel}} for ${{recordLabel}} after returning from the resumed restored evidence artifact.`,
        }};
      }}
      return {{
        label: "resumed restored evidence lane resumed",
        className: String((resumedReturnReturnActive && resumedReturnReturnActive.className) || "steady").trim() || "steady",
        summary: `Resumed ${{resumedLabel}} for ${{recordLabel}}.`,
      }};
    }}

    function motionArtifactSnapshotReasonResumedReturnReturnButtonLabel(detail) {{
      const sourceMeta = motionArtifactSnapshotReturnReasonSourceMeta(detail);
      const label = String((sourceMeta && sourceMeta.label) || "").trim().toLowerCase();
      if (label === "proof excerpt") {{
        return "Inspect Resumed Restored Excerpt";
      }}
      if (label === "proof compare") {{
        return "Inspect Resumed Restored Compare";
      }}
      if (label === "chronology evidence") {{
        return "Inspect Resumed Restored Chronology";
      }}
      return "Inspect Resumed Restored Evidence";
    }}

    function motionArtifactSnapshotReasonResumedReturnReturnReturnActiveMeta(detail) {{
      const sourceMeta = motionArtifactSnapshotReturnReasonSourceMeta(detail);
      const recordLabel = motionArtifactSnapshotRecordLabel(detail);
      const label = String((sourceMeta && sourceMeta.label) || "").trim().toLowerCase();
      if (label === "proof excerpt") {{
        return {{
          label: "resumed restored excerpt focus active",
          className: "first-seen",
          summary: `The resumed restored lane is now following the stored proof excerpt for ${{recordLabel}}.`,
        }};
      }}
      if (label === "proof compare") {{
        return {{
          label: "resumed restored compare focus active",
          className: "approval",
          summary: `The resumed restored lane is now following the stored proof compare row for ${{recordLabel}}.`,
        }};
      }}
      if (label === "chronology evidence") {{
        return {{
          label: "resumed restored chronology focus active",
          className: "open-loop",
          summary: `The resumed restored lane is now following the linked chronology evidence for ${{recordLabel}}.`,
        }};
      }}
      return {{
        label: "resumed restored evidence focus active",
        className: String((sourceMeta && sourceMeta.className) || "artifact").trim() || "artifact",
        summary: `The resumed restored lane is now following the stored evidence for ${{recordLabel}}.`,
      }};
    }}

    function motionArtifactSnapshotReasonResumedReturnReturnReturnActiveButtons(detail) {{
      const buttons = [];
      const targetButtons = motionArtifactSnapshotTargetButtons(detail);
      for (const item of targetButtons) {{
        if (!item || typeof item !== "object") continue;
        if (item.kind === "artifact" && Number.isInteger(item.motion_artifact_index)) {{
          buttons.push({{
            kind: "artifact",
            motion_artifact_index: Number(item.motion_artifact_index),
            label: "Open Resumed Restored Focus Artifact",
          }});
        }} else if (item.kind === "timeline" && Number.isInteger(item.timeline_event_index)) {{
          buttons.push({{
            kind: "timeline",
            timeline_event_index: Number(item.timeline_event_index),
            label: "Open Resumed Restored Focus Timeline",
          }});
        }}
      }}
      return buttons;
    }}

    function motionArtifactSnapshotReasonResumedReturnReturnReturnSelectionMeta(targetKind, detail) {{
      const recordLabel = motionArtifactSnapshotRecordLabel(detail);
      if (targetKind === "artifact") {{
        return {{
          label: "resumed restored focus artifact active",
          className: "accepted",
          summary: `Following the resumed restored focus artifact for ${{recordLabel}}.`,
        }};
      }}
      if (targetKind === "timeline") {{
        return {{
          label: "resumed restored focus timeline active",
          className: "recovered",
          summary: `Following the resumed restored focus timeline for ${{recordLabel}}.`,
        }};
      }}
      return {{
        label: "",
        className: "steady",
        summary: "",
      }};
    }}

    function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnMeta(detail, selectionLabel) {{
      const resumedReturnReturnReturnActive = motionArtifactSnapshotReasonResumedReturnReturnReturnActiveMeta(detail);
      const recordLabel = motionArtifactSnapshotRecordLabel(detail);
      const selection = String(selectionLabel || "").trim().toLowerCase();
      const resumedLabel = String((resumedReturnReturnReturnActive && resumedReturnReturnReturnActive.label) || "resumed restored evidence focus active").trim() || "resumed restored evidence focus active";
      if (selection.includes("timeline")) {{
        return {{
          label: "resumed restored focus lane restored",
          className: "recovered",
          summary: `Restored ${{resumedLabel}} for ${{recordLabel}} after returning from the resumed restored focus timeline.`,
        }};
      }}
      if (selection.includes("artifact")) {{
        return {{
          label: "resumed restored focus lane restored",
          className: "accepted",
          summary: `Restored ${{resumedLabel}} for ${{recordLabel}} after returning from the resumed restored focus artifact.`,
        }};
      }}
      return {{
        label: "resumed restored focus lane restored",
        className: String((resumedReturnReturnReturnActive && resumedReturnReturnReturnActive.className) || "steady").trim() || "steady",
        summary: `Restored ${{resumedLabel}} for ${{recordLabel}}.`,
      }};
    }}

    function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnMeta(detail, selectionLabel, sourceLabel) {{
      const recordLabel = motionArtifactSnapshotRecordLabel(detail);
      const restoredFocusLabel = String(selectionLabel || "").trim() || "resumed restored focus active";
      const source = String(sourceLabel || "").trim().toLowerCase();
      if (source.includes("timeline")) {{
        return {{
          label: "resumed restored focus return confirmed",
          className: "recovered",
          summary: `Returned from the resumed restored focus timeline to ${{restoredFocusLabel}} for ${{recordLabel}}.`,
        }};
      }}
      if (source.includes("artifact")) {{
        return {{
          label: "resumed restored focus return confirmed",
          className: "accepted",
          summary: `Returned from the resumed restored focus artifact to ${{restoredFocusLabel}} for ${{recordLabel}}.`,
        }};
      }}
      return {{
        label: "resumed restored focus return confirmed",
        className: "steady",
        summary: `Returned to ${{restoredFocusLabel}} for ${{recordLabel}}.`,
      }};
    }}

    function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnButtons(detail, sourceLabel) {{
      const buttons = [];
      const source = String(sourceLabel || "").trim().toLowerCase();
      const targetButtons = motionArtifactSnapshotTargetButtons(detail);
      for (const item of targetButtons) {{
        if (!item || typeof item !== "object") continue;
        if (source.includes("artifact") && item.kind === "artifact" && Number.isInteger(item.motion_artifact_index)) {{
          buttons.push({{
            kind: "artifact",
            motion_artifact_index: Number(item.motion_artifact_index),
            label: "Open Confirmed Resumed Restored Focus Artifact",
          }});
          break;
        }}
        if (source.includes("timeline") && item.kind === "timeline" && Number.isInteger(item.timeline_event_index)) {{
          buttons.push({{
            kind: "timeline",
            timeline_event_index: Number(item.timeline_event_index),
            label: "Open Confirmed Resumed Restored Focus Timeline",
          }});
          break;
        }}
      }}
      return buttons;
    }}

    function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnSelectionMeta(targetKind, detail) {{
      const recordLabel = motionArtifactSnapshotRecordLabel(detail);
      if (targetKind === "artifact") {{
        return {{
          label: "confirmed resumed restored focus artifact active",
          className: "accepted",
          summary: `Following the confirmed resumed-restored focus artifact for ${{recordLabel}}.`,
        }};
      }}
      if (targetKind === "timeline") {{
        return {{
          label: "confirmed resumed restored focus timeline active",
          className: "recovered",
          summary: `Following the confirmed resumed-restored focus timeline for ${{recordLabel}}.`,
        }};
      }}
      return {{
        label: "",
        className: "steady",
        summary: "",
      }};
    }}

    function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnMeta(detail, sourceLabel) {{
      const recordLabel = motionArtifactSnapshotRecordLabel(detail);
      const source = String(sourceLabel || "").trim().toLowerCase();
      if (source.includes("timeline")) {{
        return {{
          label: "confirmed resumed restored focus restored",
          className: "recovered",
          summary: `Restored the confirmed resumed-restored focus timeline for ${{recordLabel}}.`,
        }};
      }}
      if (source.includes("artifact")) {{
        return {{
          label: "confirmed resumed restored focus restored",
          className: "accepted",
          summary: `Restored the confirmed resumed-restored focus artifact for ${{recordLabel}}.`,
        }};
      }}
      return {{
        label: "confirmed resumed restored focus restored",
        className: "steady",
        summary: `Restored the confirmed resumed-restored focus context for ${{recordLabel}}.`,
      }};
    }}

    function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnButtons(detail, sourceLabel) {{
      const buttons = [];
      const source = String(sourceLabel || "").trim().toLowerCase();
      const targetButtons = motionArtifactSnapshotTargetButtons(detail);
      for (const item of targetButtons) {{
        if (!item || typeof item !== "object") continue;
        if (source.includes("artifact") && item.kind === "artifact" && Number.isInteger(item.motion_artifact_index)) {{
          buttons.push({{
            kind: "artifact",
            motion_artifact_index: Number(item.motion_artifact_index),
            label: "Reopen Confirmed Restored Focus Artifact",
          }});
          break;
        }}
        if (source.includes("timeline") && item.kind === "timeline" && Number.isInteger(item.timeline_event_index)) {{
          buttons.push({{
            kind: "timeline",
            timeline_event_index: Number(item.timeline_event_index),
            label: "Reopen Confirmed Restored Focus Timeline",
          }});
          break;
        }}
      }}
      return buttons;
    }}

    function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnSelectionMeta(targetKind, detail) {{
      const recordLabel = motionArtifactSnapshotRecordLabel(detail);
      if (targetKind === "artifact") {{
        return {{
          label: "reopened confirmed restored focus artifact active",
          className: "accepted",
          summary: `Following the reopened confirmed restored focus artifact for ${{recordLabel}}.`,
        }};
      }}
      if (targetKind === "timeline") {{
        return {{
          label: "reopened confirmed restored focus timeline active",
          className: "recovered",
          summary: `Following the reopened confirmed restored focus timeline for ${{recordLabel}}.`,
        }};
      }}
      return {{
        label: "",
        className: "steady",
        summary: "",
      }};
    }}

    function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnMeta(detail, sourceLabel) {{
      const recordLabel = motionArtifactSnapshotRecordLabel(detail);
      const source = String(sourceLabel || "").trim().toLowerCase();
      if (source.includes("timeline")) {{
        return {{
          label: "reopened confirmed restored focus restored",
          className: "recovered",
          summary: `Restored the reopened confirmed restored focus timeline for ${{recordLabel}}.`,
        }};
      }}
      if (source.includes("artifact")) {{
        return {{
          label: "reopened confirmed restored focus restored",
          className: "accepted",
          summary: `Restored the reopened confirmed restored focus artifact for ${{recordLabel}}.`,
        }};
      }}
      return {{
        label: "reopened confirmed restored focus restored",
        className: "steady",
        summary: `Restored the reopened confirmed restored focus context for ${{recordLabel}}.`,
      }};
    }}

    function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnMeta(detail, sourceLabel) {{
      const recordLabel = motionArtifactSnapshotRecordLabel(detail);
      const source = String(sourceLabel || "").trim().toLowerCase();
      if (source.includes("timeline")) {{
        return {{
          label: "reopened reopened confirmed focus restored",
          className: "recovered",
          summary: `Restored the reopened reopened confirmed focus timeline for ${{recordLabel}}.`,
        }};
      }}
      if (source.includes("artifact")) {{
        return {{
          label: "reopened reopened confirmed focus restored",
          className: "accepted",
          summary: `Restored the reopened reopened confirmed focus artifact for ${{recordLabel}}.`,
        }};
      }}
      return {{
        label: "reopened reopened confirmed focus restored",
        className: "steady",
        summary: `Restored the reopened reopened confirmed focus context for ${{recordLabel}}.`,
      }};
    }}

    function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnButtons(detail, sourceLabel) {{
      const buttons = [];
      const source = String(sourceLabel || "").trim().toLowerCase();
      const targetButtons = motionArtifactSnapshotTargetButtons(detail);
      for (const item of targetButtons) {{
        if (!item || typeof item !== "object") continue;
        if (source.includes("artifact") && item.kind === "artifact" && Number.isInteger(item.motion_artifact_index)) {{
          buttons.push({{
            kind: "artifact",
            motion_artifact_index: Number(item.motion_artifact_index),
            label: "Reopen Reopened Reopened Confirmed Focus Artifact",
          }});
          break;
        }}
        if (source.includes("timeline") && item.kind === "timeline" && Number.isInteger(item.timeline_event_index)) {{
          buttons.push({{
            kind: "timeline",
            timeline_event_index: Number(item.timeline_event_index),
            label: "Reopen Reopened Reopened Confirmed Focus Timeline",
          }});
          break;
        }}
      }}
      return buttons;
    }}

    function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnSelectionMeta(targetKind, detail) {{
      const recordLabel = motionArtifactSnapshotRecordLabel(detail);
      if (targetKind === "artifact") {{
        return {{
          label: "reopened reopened confirmed focus artifact active",
          className: "accepted",
          summary: `Following the reopened reopened confirmed focus artifact for ${{recordLabel}}.`,
        }};
      }}
      if (targetKind === "timeline") {{
        return {{
          label: "reopened reopened confirmed focus timeline active",
          className: "recovered",
          summary: `Following the reopened reopened confirmed focus timeline for ${{recordLabel}}.`,
        }};
      }}
      return {{
        label: "",
        className: "steady",
        summary: "",
      }};
    }}

    function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnSelectionMeta(targetKind, detail) {{
      const recordLabel = motionArtifactSnapshotRecordLabel(detail);
      if (targetKind === "artifact") {{
        return {{
          label: "reopened reopened reopened confirmed focus artifact active",
          className: "accepted",
          summary: `Following the reopened reopened reopened confirmed focus artifact for ${{recordLabel}}.`,
        }};
      }}
      if (targetKind === "timeline") {{
        return {{
          label: "reopened reopened reopened confirmed focus timeline active",
          className: "recovered",
          summary: `Following the reopened reopened reopened confirmed focus timeline for ${{recordLabel}}.`,
        }};
      }}
      return {{
        label: "",
        className: "steady",
        summary: "",
      }};
    }}

    function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnMeta(detail, sourceLabel) {{
      const recordLabel = motionArtifactSnapshotRecordLabel(detail);
      const source = String(sourceLabel || "").trim().toLowerCase();
      if (source.includes("timeline")) {{
        return {{
          label: "reopened reopened reopened confirmed focus restored",
          className: "recovered",
          summary: `Restored the reopened reopened reopened confirmed focus timeline for ${{recordLabel}}.`,
        }};
      }}
      if (source.includes("artifact")) {{
        return {{
          label: "reopened reopened reopened confirmed focus restored",
          className: "accepted",
          summary: `Restored the reopened reopened reopened confirmed focus artifact for ${{recordLabel}}.`,
        }};
      }}
      return {{
        label: "reopened reopened reopened confirmed focus restored",
        className: "steady",
        summary: `Restored the reopened reopened reopened confirmed focus context for ${{recordLabel}}.`,
      }};
    }}

    function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnButtons(detail, sourceLabel) {{
      const buttons = [];
      const source = String(sourceLabel || "").trim().toLowerCase();
      const targetButtons = motionArtifactSnapshotTargetButtons(detail);
      for (const item of targetButtons) {{
        if (!item || typeof item !== "object") continue;
        if (source.includes("artifact") && item.kind === "artifact" && Number.isInteger(item.motion_artifact_index)) {{
          buttons.push({{
            kind: "artifact",
            motion_artifact_index: Number(item.motion_artifact_index),
            label: "Reopen Reopened Reopened Reopened Confirmed Focus Artifact",
          }});
          break;
        }}
        if (source.includes("timeline") && item.kind === "timeline" && Number.isInteger(item.timeline_event_index)) {{
          buttons.push({{
            kind: "timeline",
            timeline_event_index: Number(item.timeline_event_index),
            label: "Reopen Reopened Reopened Reopened Confirmed Focus Timeline",
          }});
          break;
        }}
      }}
      return buttons;
    }}

    function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnSelectionMeta(targetKind, detail) {{
      const recordLabel = motionArtifactSnapshotRecordLabel(detail);
      if (targetKind === "artifact") {{
        return {{
          label: "reopened reopened reopened reopened confirmed focus artifact active",
          className: "accepted",
          summary: `Following the reopened reopened reopened reopened confirmed focus artifact for ${{recordLabel}}.`,
        }};
      }}
      if (targetKind === "timeline") {{
        return {{
          label: "reopened reopened reopened reopened confirmed focus timeline active",
          className: "recovered",
          summary: `Following the reopened reopened reopened reopened confirmed focus timeline for ${{recordLabel}}.`,
        }};
      }}
      return {{
        label: "",
        className: "steady",
        summary: "",
      }};
    }}

    function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnMeta(detail, sourceLabel) {{
      const recordLabel = motionArtifactSnapshotRecordLabel(detail);
      const source = String(sourceLabel || "").trim().toLowerCase();
      if (source.includes("timeline")) {{
        return {{
          label: "reopened reopened reopened reopened confirmed focus restored",
          className: "recovered",
          summary: `Restored the reopened reopened reopened reopened confirmed focus timeline for ${{recordLabel}}.`,
        }};
      }}
      if (source.includes("artifact")) {{
        return {{
          label: "reopened reopened reopened reopened confirmed focus restored",
          className: "accepted",
          summary: `Restored the reopened reopened reopened reopened confirmed focus artifact for ${{recordLabel}}.`,
        }};
      }}
      return {{
        label: "reopened reopened reopened reopened confirmed focus restored",
        className: "steady",
        summary: `Restored the reopened reopened reopened reopened confirmed focus context for ${{recordLabel}}.`,
      }};
    }}

    function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnButtons(detail, sourceLabel) {{
      const buttons = [];
      const source = String(sourceLabel || "").trim().toLowerCase();
      const targetButtons = motionArtifactSnapshotTargetButtons(detail);
      for (const item of targetButtons) {{
        if (!item || typeof item !== "object") continue;
        if (source.includes("artifact") && item.kind === "artifact" && Number.isInteger(item.motion_artifact_index)) {{
          buttons.push({{
            kind: "artifact",
            motion_artifact_index: Number(item.motion_artifact_index),
            label: "Reopen Reopened Reopened Reopened Reopened Confirmed Focus Artifact",
          }});
          break;
        }}
        if (source.includes("timeline") && item.kind === "timeline" && Number.isInteger(item.timeline_event_index)) {{
          buttons.push({{
            kind: "timeline",
            timeline_event_index: Number(item.timeline_event_index),
            label: "Reopen Reopened Reopened Reopened Reopened Confirmed Focus Timeline",
          }});
          break;
        }}
      }}
      return buttons;
    }}

    function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnSelectionMeta(targetKind, detail) {{
      const recordLabel = motionArtifactSnapshotRecordLabel(detail);
      if (targetKind === "artifact") {{
        return {{
          label: "reopened reopened reopened reopened reopened confirmed focus artifact active",
          className: "accepted",
          summary: `Following the reopened reopened reopened reopened reopened confirmed focus artifact for ${{recordLabel}}.`,
        }};
      }}
      if (targetKind === "timeline") {{
        return {{
          label: "reopened reopened reopened reopened reopened confirmed focus timeline active",
          className: "recovered",
          summary: `Following the reopened reopened reopened reopened reopened confirmed focus timeline for ${{recordLabel}}.`,
        }};
      }}
      return {{
        label: "",
        className: "steady",
        summary: "",
      }};
    }}

    function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnSelectionMeta(targetKind, detail) {{
      const recordLabel = motionArtifactSnapshotRecordLabel(detail);
      if (targetKind === "artifact") {{
        return {{
          label: "reopened reopened reopened reopened reopened reopened confirmed focus artifact active",
          className: "accepted",
          summary: `Following the reopened reopened reopened reopened reopened reopened confirmed focus artifact for ${{recordLabel}}.`,
        }};
      }}
      if (targetKind === "timeline") {{
        return {{
          label: "reopened reopened reopened reopened reopened reopened confirmed focus timeline active",
          className: "recovered",
          summary: `Following the reopened reopened reopened reopened reopened reopened confirmed focus timeline for ${{recordLabel}}.`,
        }};
      }}
      return {{
        label: "",
        className: "steady",
        summary: "",
      }};
    }}

    function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnSelectionMeta(targetKind, detail) {{
      const recordLabel = motionArtifactSnapshotRecordLabel(detail);
      if (targetKind === "artifact") {{
        return {{
          label: "reopened reopened reopened reopened reopened reopened reopened confirmed focus artifact active",
          className: "accepted",
          summary: `Following the reopened reopened reopened reopened reopened reopened reopened confirmed focus artifact for ${{recordLabel}}.`,
        }};
      }}
      if (targetKind === "timeline") {{
        return {{
          label: "reopened reopened reopened reopened reopened reopened reopened confirmed focus timeline active",
          className: "recovered",
          summary: `Following the reopened reopened reopened reopened reopened reopened reopened confirmed focus timeline for ${{recordLabel}}.`,
        }};
      }}
      return {{
        label: "",
        className: "steady",
        summary: "",
      }};
    }}

    function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnMeta(detail, sourceLabel) {{
      const recordLabel = motionArtifactSnapshotRecordLabel(detail);
      const source = String(sourceLabel || "").trim().toLowerCase();
      if (source.includes("timeline")) {{
        return {{
          label: "reopened reopened reopened reopened reopened confirmed focus restored",
          className: "recovered",
          summary: `Restored the reopened reopened reopened reopened reopened confirmed focus timeline for ${{recordLabel}}.`,
        }};
      }}
      if (source.includes("artifact")) {{
        return {{
          label: "reopened reopened reopened reopened reopened confirmed focus restored",
          className: "accepted",
          summary: `Restored the reopened reopened reopened reopened reopened confirmed focus artifact for ${{recordLabel}}.`,
        }};
      }}
      return {{
        label: "reopened reopened reopened reopened reopened confirmed focus restored",
        className: "steady",
        summary: `Restored the reopened reopened reopened reopened reopened confirmed focus context for ${{recordLabel}}.`,
      }};
    }}

    function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnMeta(detail, sourceLabel) {{
      const recordLabel = motionArtifactSnapshotRecordLabel(detail);
      const source = String(sourceLabel || "").trim().toLowerCase();
      if (source.includes("timeline")) {{
        return {{
          label: "reopened reopened reopened reopened reopened reopened confirmed focus restored",
          className: "recovered",
          summary: `Restored the reopened reopened reopened reopened reopened reopened confirmed focus timeline for ${{recordLabel}}.`,
        }};
      }}
      if (source.includes("artifact")) {{
        return {{
          label: "reopened reopened reopened reopened reopened reopened confirmed focus restored",
          className: "accepted",
          summary: `Restored the reopened reopened reopened reopened reopened reopened confirmed focus artifact for ${{recordLabel}}.`,
        }};
      }}
      return {{
        label: "reopened reopened reopened reopened reopened reopened confirmed focus restored",
        className: "steady",
        summary: `Restored the reopened reopened reopened reopened reopened reopened confirmed focus context for ${{recordLabel}}.`,
      }};
    }}

    function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnMeta(detail, sourceLabel) {{
      const recordLabel = motionArtifactSnapshotRecordLabel(detail);
      const source = String(sourceLabel || "").trim().toLowerCase();
      if (source.includes("timeline")) {{
        return {{
          label: "reopened reopened reopened reopened reopened reopened reopened confirmed focus restored",
          className: "recovered",
          summary: `Restored the reopened reopened reopened reopened reopened reopened reopened confirmed focus timeline for ${{recordLabel}}.`,
        }};
      }}
      if (source.includes("artifact")) {{
        return {{
          label: "reopened reopened reopened reopened reopened reopened reopened confirmed focus restored",
          className: "accepted",
          summary: `Restored the reopened reopened reopened reopened reopened reopened reopened confirmed focus artifact for ${{recordLabel}}.`,
        }};
      }}
      return {{
        label: "reopened reopened reopened reopened reopened reopened reopened confirmed focus restored",
        className: "steady",
        summary: `Restored the reopened reopened reopened reopened reopened reopened reopened confirmed focus context for ${{recordLabel}}.`,
      }};
    }}

    function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnMeta(detail, sourceLabel) {{
      const recordLabel = motionArtifactSnapshotRecordLabel(detail);
      const source = String(sourceLabel || "").trim().toLowerCase();
      if (source.includes("timeline")) {{
        return {{
          label: "reopened reopened reopened reopened reopened reopened reopened reopened confirmed focus restored",
          className: "recovered",
          summary: `Restored the reopened reopened reopened reopened reopened reopened reopened reopened confirmed focus timeline for ${{recordLabel}}.`,
        }};
      }}
      if (source.includes("artifact")) {{
        return {{
          label: "reopened reopened reopened reopened reopened reopened reopened reopened confirmed focus restored",
          className: "accepted",
          summary: `Restored the reopened reopened reopened reopened reopened reopened reopened reopened confirmed focus artifact for ${{recordLabel}}.`,
        }};
      }}
      return {{
        label: "reopened reopened reopened reopened reopened reopened reopened reopened confirmed focus restored",
        className: "steady",
        summary: `Restored the reopened reopened reopened reopened reopened reopened reopened reopened confirmed focus context for ${{recordLabel}}.`,
      }};
    }}

    function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnButtons(detail, sourceLabel) {{
      const buttons = [];
      const source = String(sourceLabel || "").trim().toLowerCase();
      const targetButtons = motionArtifactSnapshotTargetButtons(detail);
      for (const item of targetButtons) {{
        if (!item || typeof item !== "object") continue;
        if (source.includes("artifact") && item.kind === "artifact" && Number.isInteger(item.motion_artifact_index)) {{
          buttons.push({{
            kind: "artifact",
            motion_artifact_index: Number(item.motion_artifact_index),
            label: "Reopen Reopened Reopened Reopened Reopened Reopened Reopened Reopened Confirmed Focus Artifact",
          }});
          break;
        }}
        if (source.includes("timeline") && item.kind === "timeline" && Number.isInteger(item.timeline_event_index)) {{
          buttons.push({{
            kind: "timeline",
            timeline_event_index: Number(item.timeline_event_index),
            label: "Reopen Reopened Reopened Reopened Reopened Reopened Reopened Reopened Confirmed Focus Timeline",
          }});
          break;
        }}
      }}
      return buttons;
    }}

    function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnSelectionMeta(targetKind, detail) {{
      const recordLabel = motionArtifactSnapshotRecordLabel(detail);
      if (targetKind === "artifact") {{
        return {{
          label: "reopened reopened reopened reopened reopened reopened reopened reopened reopened confirmed focus artifact active",
          className: "accepted",
          summary: `Following the reopened reopened reopened reopened reopened reopened reopened reopened reopened confirmed focus artifact for ${{recordLabel}}.`,
        }};
      }}
      if (targetKind === "timeline") {{
        return {{
          label: "reopened reopened reopened reopened reopened reopened reopened reopened reopened confirmed focus timeline active",
          className: "recovered",
          summary: `Following the reopened reopened reopened reopened reopened reopened reopened reopened reopened confirmed focus timeline for ${{recordLabel}}.`,
        }};
      }}
      return {{
        label: "",
        className: "steady",
        summary: "",
      }};
    }}

    function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnSelectionMeta(targetKind, detail) {{
      const recordLabel = motionArtifactSnapshotRecordLabel(detail);
      if (targetKind === "artifact") {{
        return {{
          label: "reopened reopened reopened reopened reopened reopened reopened reopened reopened reopened confirmed focus artifact active",
          className: "accepted",
          summary: `Following the reopened reopened reopened reopened reopened reopened reopened reopened reopened reopened confirmed focus artifact for ${{recordLabel}}.`,
        }};
      }}
      if (targetKind === "timeline") {{
        return {{
          label: "reopened reopened reopened reopened reopened reopened reopened reopened reopened reopened confirmed focus timeline active",
          className: "recovered",
          summary: `Following the reopened reopened reopened reopened reopened reopened reopened reopened reopened reopened confirmed focus timeline for ${{recordLabel}}.`,
        }};
      }}
      return {{
        label: "",
        className: "steady",
        summary: "",
      }};
    }}

    function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnSelectionMeta(targetKind, detail) {{
      const recordLabel = motionArtifactSnapshotRecordLabel(detail);
      if (targetKind === "artifact") {{
        return {{
          label: "reopened reopened reopened reopened reopened reopened reopened reopened reopened reopened reopened confirmed focus artifact active",
          className: "accepted",
          summary: `Following the reopened reopened reopened reopened reopened reopened reopened reopened reopened reopened reopened confirmed focus artifact for ${{recordLabel}}.`,
        }};
      }}
      if (targetKind === "timeline") {{
        return {{
          label: "reopened reopened reopened reopened reopened reopened reopened reopened reopened reopened reopened confirmed focus timeline active",
          className: "recovered",
          summary: `Following the reopened reopened reopened reopened reopened reopened reopened reopened reopened reopened reopened confirmed focus timeline for ${{recordLabel}}.`,
        }};
      }}
      return {{
        label: "",
        className: "steady",
        summary: "",
      }};
    }}

    function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnSelectionMeta(targetKind, detail) {{
      const recordLabel = motionArtifactSnapshotRecordLabel(detail);
      if (targetKind === "artifact") {{
        return {{
          label: "reopened reopened reopened reopened reopened reopened reopened reopened confirmed focus artifact active",
          className: "accepted",
          summary: `Following the reopened reopened reopened reopened reopened reopened reopened reopened confirmed focus artifact for ${{recordLabel}}.`,
        }};
      }}
      if (targetKind === "timeline") {{
        return {{
          label: "reopened reopened reopened reopened reopened reopened reopened reopened confirmed focus timeline active",
          className: "recovered",
          summary: `Following the reopened reopened reopened reopened reopened reopened reopened reopened confirmed focus timeline for ${{recordLabel}}.`,
        }};
      }}
      return {{
        label: "",
        className: "steady",
        summary: "",
      }};
    }}

    function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnButtons(detail, sourceLabel) {{
      const buttons = [];
      const source = String(sourceLabel || "").trim().toLowerCase();
      const targetButtons = motionArtifactSnapshotTargetButtons(detail);
      for (const item of targetButtons) {{
        if (!item || typeof item !== "object") continue;
        if (source.includes("artifact") && item.kind === "artifact" && Number.isInteger(item.motion_artifact_index)) {{
          buttons.push({{
            kind: "artifact",
            motion_artifact_index: Number(item.motion_artifact_index),
            label: "Reopen Reopened Reopened Reopened Reopened Reopened Reopened Reopened Confirmed Focus Artifact",
          }});
          break;
        }}
        if (source.includes("timeline") && item.kind === "timeline" && Number.isInteger(item.timeline_event_index)) {{
          buttons.push({{
            kind: "timeline",
            timeline_event_index: Number(item.timeline_event_index),
            label: "Reopen Reopened Reopened Reopened Reopened Reopened Reopened Reopened Confirmed Focus Timeline",
          }});
          break;
        }}
      }}
      return buttons;
    }}

    function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnButtons(detail, sourceLabel) {{
      const buttons = [];
      const source = String(sourceLabel || "").trim().toLowerCase();
      const targetButtons = motionArtifactSnapshotTargetButtons(detail);
      for (const item of targetButtons) {{
        if (!item || typeof item !== "object") continue;
        if (source.includes("artifact") && item.kind === "artifact" && Number.isInteger(item.motion_artifact_index)) {{
          buttons.push({{
            kind: "artifact",
            motion_artifact_index: Number(item.motion_artifact_index),
            label: "Reopen Reopened Reopened Reopened Reopened Reopened Reopened Confirmed Focus Artifact",
          }});
          break;
        }}
        if (source.includes("timeline") && item.kind === "timeline" && Number.isInteger(item.timeline_event_index)) {{
          buttons.push({{
            kind: "timeline",
            timeline_event_index: Number(item.timeline_event_index),
            label: "Reopen Reopened Reopened Reopened Reopened Reopened Reopened Confirmed Focus Timeline",
          }});
          break;
        }}
      }}
      return buttons;
    }}

    function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnButtons(detail, sourceLabel) {{
      const buttons = [];
      const source = String(sourceLabel || "").trim().toLowerCase();
      const targetButtons = motionArtifactSnapshotTargetButtons(detail);
      for (const item of targetButtons) {{
        if (!item || typeof item !== "object") continue;
        if (source.includes("artifact") && item.kind === "artifact" && Number.isInteger(item.motion_artifact_index)) {{
          buttons.push({{
            kind: "artifact",
            motion_artifact_index: Number(item.motion_artifact_index),
            label: "Reopen Reopened Reopened Reopened Reopened Reopened Confirmed Focus Artifact",
          }});
          break;
        }}
        if (source.includes("timeline") && item.kind === "timeline" && Number.isInteger(item.timeline_event_index)) {{
          buttons.push({{
            kind: "timeline",
            timeline_event_index: Number(item.timeline_event_index),
            label: "Reopen Reopened Reopened Reopened Reopened Reopened Confirmed Focus Timeline",
          }});
          break;
        }}
      }}
      return buttons;
    }}

    function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnButtons(detail, sourceLabel) {{
      const buttons = [];
      const source = String(sourceLabel || "").trim().toLowerCase();
      const targetButtons = motionArtifactSnapshotTargetButtons(detail);
      for (const item of targetButtons) {{
        if (!item || typeof item !== "object") continue;
        if (source.includes("artifact") && item.kind === "artifact" && Number.isInteger(item.motion_artifact_index)) {{
          buttons.push({{
            kind: "artifact",
            motion_artifact_index: Number(item.motion_artifact_index),
            label: "Reopen Reopened Confirmed Focus Artifact",
          }});
          break;
        }}
        if (source.includes("timeline") && item.kind === "timeline" && Number.isInteger(item.timeline_event_index)) {{
          buttons.push({{
            kind: "timeline",
            timeline_event_index: Number(item.timeline_event_index),
            label: "Reopen Reopened Confirmed Focus Timeline",
          }});
          break;
        }}
      }}
      return buttons;
    }}

    function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnMeta(detail, sourceLabel) {{
      const recordLabel = motionArtifactSnapshotRecordLabel(detail);
      const source = String(sourceLabel || "").trim().toLowerCase();
      if (source.includes("timeline")) {{
        return {{
          label: "reopened reopened reopened reopened reopened reopened reopened reopened reopened confirmed focus restored",
          className: "recovered",
          summary: `Restored the reopened reopened reopened reopened reopened reopened reopened reopened reopened confirmed focus timeline for ${{recordLabel}}.`,
        }};
      }}
      if (source.includes("artifact")) {{
        return {{
          label: "reopened reopened reopened reopened reopened reopened reopened reopened reopened confirmed focus restored",
          className: "accepted",
          summary: `Restored the reopened reopened reopened reopened reopened reopened reopened reopened reopened confirmed focus artifact for ${{recordLabel}}.`,
        }};
      }}
      return {{
        label: "reopened reopened reopened reopened reopened reopened reopened reopened reopened confirmed focus restored",
        className: "steady",
        summary: `Restored the reopened reopened reopened reopened reopened reopened reopened reopened reopened confirmed focus context for ${{recordLabel}}.`,
      }};
    }}

    function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnButtons(detail, sourceLabel) {{
      const buttons = [];
      const source = String(sourceLabel || "").trim().toLowerCase();
      const targetButtons = motionArtifactSnapshotTargetButtons(detail);
      for (const item of targetButtons) {{
        if (!item || typeof item !== "object") continue;
        if (source.includes("artifact") && item.kind === "artifact" && Number.isInteger(item.motion_artifact_index)) {{
          buttons.push({{
            kind: "artifact",
            motion_artifact_index: Number(item.motion_artifact_index),
            label: "Reopen Reopened Reopened Reopened Reopened Reopened Reopened Reopened Reopened Confirmed Focus Artifact",
          }});
          break;
        }}
        if (source.includes("timeline") && item.kind === "timeline" && Number.isInteger(item.timeline_event_index)) {{
          buttons.push({{
            kind: "timeline",
            timeline_event_index: Number(item.timeline_event_index),
            label: "Reopen Reopened Reopened Reopened Reopened Reopened Reopened Reopened Reopened Confirmed Focus Timeline",
          }});
          break;
        }}
      }}
      return buttons;
    }}

    function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnMeta(detail, sourceLabel) {{
      const recordLabel = motionArtifactSnapshotRecordLabel(detail);
      const source = String(sourceLabel || "").trim().toLowerCase();
      if (source.includes("timeline")) {{
        return {{
          label: "reopened reopened reopened reopened reopened reopened reopened reopened reopened reopened confirmed focus restored",
          className: "recovered",
          summary: `Restored the reopened reopened reopened reopened reopened reopened reopened reopened reopened reopened confirmed focus timeline for ${{recordLabel}}.`,
        }};
      }}
      if (source.includes("artifact")) {{
        return {{
          label: "reopened reopened reopened reopened reopened reopened reopened reopened reopened reopened confirmed focus restored",
          className: "accepted",
          summary: `Restored the reopened reopened reopened reopened reopened reopened reopened reopened reopened reopened confirmed focus artifact for ${{recordLabel}}.`,
        }};
      }}
      return {{
        label: "reopened reopened reopened reopened reopened reopened reopened reopened reopened reopened confirmed focus restored",
        className: "steady",
        summary: `Restored the reopened reopened reopened reopened reopened reopened reopened reopened reopened reopened confirmed focus context for ${{recordLabel}}.`,
      }};
    }}

    function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnButtons(detail, sourceLabel) {{
      const buttons = [];
      const source = String(sourceLabel || "").trim().toLowerCase();
      const targetButtons = motionArtifactSnapshotTargetButtons(detail);
      for (const item of targetButtons) {{
        if (!item || typeof item !== "object") continue;
        if (source.includes("artifact") && item.kind === "artifact" && Number.isInteger(item.motion_artifact_index)) {{
          buttons.push({{
            kind: "artifact",
            motion_artifact_index: Number(item.motion_artifact_index),
            label: "Reopen Reopened Reopened Reopened Reopened Reopened Reopened Reopened Reopened Reopened Confirmed Focus Artifact",
          }});
          break;
        }}
        if (source.includes("timeline") && item.kind === "timeline" && Number.isInteger(item.timeline_event_index)) {{
          buttons.push({{
            kind: "timeline",
            timeline_event_index: Number(item.timeline_event_index),
            label: "Reopen Reopened Reopened Reopened Reopened Reopened Reopened Reopened Reopened Reopened Confirmed Focus Timeline",
          }});
          break;
        }}
      }}
      return buttons;
    }}

    function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnButtons(detail) {{
      const buttons = [];
      const targetButtons = motionArtifactSnapshotTargetButtons(detail);
      for (const item of targetButtons) {{
        if (!item || typeof item !== "object") continue;
        if (item.kind === "artifact" && Number.isInteger(item.motion_artifact_index)) {{
          buttons.push({{
            kind: "artifact",
            motion_artifact_index: Number(item.motion_artifact_index),
            label: "Reopen Resumed Restored Focus Artifact",
          }});
        }} else if (item.kind === "timeline" && Number.isInteger(item.timeline_event_index)) {{
          buttons.push({{
            kind: "timeline",
            timeline_event_index: Number(item.timeline_event_index),
            label: "Reopen Resumed Restored Focus Timeline",
          }});
        }}
      }}
      return buttons;
    }}

    function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnSelectionMeta(targetKind, detail) {{
      const recordLabel = motionArtifactSnapshotRecordLabel(detail);
      if (targetKind === "artifact") {{
        return {{
          label: "resumed restored focus restored artifact active",
          className: "accepted",
          summary: `Following the restored resumed-restored focus artifact for ${{recordLabel}}.`,
        }};
      }}
      if (targetKind === "timeline") {{
        return {{
          label: "resumed restored focus restored timeline active",
          className: "recovered",
          summary: `Following the restored resumed-restored focus timeline for ${{recordLabel}}.`,
        }};
      }}
      return {{
        label: "",
        className: "steady",
        summary: "",
      }};
    }}

    function motionArtifactSnapshotReasonResumedReturnReturnActiveButtons(detail) {{
      const buttons = [];
      const targetButtons = motionArtifactSnapshotTargetButtons(detail);
      for (const item of targetButtons) {{
        if (!item || typeof item !== "object") continue;
        if (item.kind === "artifact" && Number.isInteger(item.motion_artifact_index)) {{
          buttons.push({{
            kind: "artifact",
            motion_artifact_index: Number(item.motion_artifact_index),
            label: "Open Resumed Restored Evidence Artifact",
          }});
        }} else if (item.kind === "timeline" && Number.isInteger(item.timeline_event_index)) {{
          buttons.push({{
            kind: "timeline",
            timeline_event_index: Number(item.timeline_event_index),
            label: "Open Resumed Restored Evidence Timeline",
          }});
        }}
      }}
      return buttons;
    }}

    function motionArtifactSnapshotReturnLaneMeta(originMeta) {{
      const label = String((originMeta && originMeta.label) || "").trim().toLowerCase();
      if (label.includes("mutation")) {{
        return {{ label: "mutation lane", className: "approval" }};
      }}
      if (label.includes("chronology")) {{
        return {{ label: "chronology lane", className: "open-loop" }};
      }}
      if (label.includes("proof")) {{
        return {{ label: "proof lane", className: "first-seen" }};
      }}
      return {{ label: "", className: "steady" }};
    }}

    function motionArtifactSnapshotCurrentPathKind(detail) {{
      const focus = detail && detail.motion_artifact_focus_posture_snapshot_reason_focus && typeof detail.motion_artifact_focus_posture_snapshot_reason_focus === "object"
        ? detail.motion_artifact_focus_posture_snapshot_reason_focus
        : null;
      const label = String((focus && focus.active_path_label) || "").trim().toLowerCase();
      if (label.includes("mutation")) return "mutation";
      if (label.includes("chronology")) return "chronology";
      return "proof";
    }}

    function jumpBackToMotionArtifactSnapshotProof() {{
      const currentDetail = selectedDetail();
      const pathKind = motionArtifactSnapshotCurrentPathKind(currentDetail);
      const detail = applyMotionArtifactSnapshotPath(currentDetail, pathKind === "proof" ? "proof" : pathKind);
      const focus = detail && detail.motion_artifact_focus_posture_snapshot_reason_focus && typeof detail.motion_artifact_focus_posture_snapshot_reason_focus === "object"
        ? detail.motion_artifact_focus_posture_snapshot_reason_focus
        : null;
      if (focus) {{
        const returnOrigin = motionArtifactSnapshotReturnOriginMeta(detail);
        const returnLane = motionArtifactSnapshotReturnLaneMeta(returnOrigin);
        const returnReasonSource = motionArtifactSnapshotReturnReasonSourceMeta(detail);
        const returnReasonResume = motionArtifactSnapshotReasonResumeMeta(detail);
        focus.return_summary = motionArtifactSnapshotReturnSummary(detail);
        focus.return_history_index = Number.isInteger(detail.motion_artifact_focus_posture_outcome_index)
          ? Number(detail.motion_artifact_focus_posture_outcome_index)
          : null;
        focus.return_history_label = focus.return_history_index !== null
          ? motionArtifactSnapshotReturnActionLabel(returnOrigin, detail)
          : "";
        focus.return_history_reason = focus.return_history_index !== null
          ? motionArtifactSnapshotReturnActionReason(returnOrigin, detail)
          : "";
        focus.return_history_reason_button_label = focus.return_history_index !== null
          ? motionArtifactSnapshotReturnReasonButtonLabel(detail)
          : "";
        focus.return_history_reason_source_label = focus.return_history_index !== null
          ? String((returnReasonSource && returnReasonSource.label) || "").trim()
          : "";
        focus.return_history_reason_source_class = focus.return_history_index !== null
          ? String((returnReasonSource && returnReasonSource.className) || "artifact").trim() || "artifact"
          : "artifact";
        focus.return_history_origin_label = focus.return_history_index !== null
          ? String((returnOrigin && returnOrigin.label) || "latest outcome").trim() || "latest outcome"
          : "";
        focus.return_history_origin_class = String((returnOrigin && returnOrigin.className) || "artifact").trim() || "artifact";
        focus.return_history_lane_label = focus.return_history_index !== null
          ? String((returnLane && returnLane.label) || "").trim()
          : "";
        focus.return_history_lane_class = focus.return_history_index !== null
          ? String((returnLane && returnLane.className) || "steady").trim() || "steady"
          : "steady";
        focus.return_confirmation_label = "proof lane restored";
        focus.return_confirmation_class = "accepted";
        focus.return_confirmation_summary = `Restored reopened proof context for ${{motionArtifactSnapshotRecordLabel(detail)}}.`;
        focus.return_history_reason_resumed_label = String((returnReasonResume && returnReasonResume.label) || "").trim();
        focus.return_history_reason_resumed_class = String((returnReasonResume && returnReasonResume.className) || "steady").trim() || "steady";
        focus.return_history_reason_resumed_summary = String((returnReasonResume && returnReasonResume.summary) || "").trim();
      }}
      detail.change_summary = "Returned to the reopened proof focus from the confirmed target view.";
      detail.change_evidence_summary = String((detail.motion_artifact_focus_posture_snapshot_reason_focus || {{}}).active_target_label || "Returned to the reopened proof focus for the current localized record.").trim();
      return detail;
    }}

    function jumpToMotionArtifactSnapshotRestoredReason(mode) {{
      const currentDetail = selectedDetail();
      const currentFocus = currentDetail && currentDetail.motion_artifact_focus_posture_snapshot_reason_focus && typeof currentDetail.motion_artifact_focus_posture_snapshot_reason_focus === "object"
        ? currentDetail.motion_artifact_focus_posture_snapshot_reason_focus
        : null;
      const restoredSelectionLabel = String((currentFocus && currentFocus.return_history_reason_resumed_active_selection_label) || "").trim();
      const resumedReturnLabel = String((currentFocus && currentFocus.return_history_reason_resumed_return_label) || "").trim();
      const resumedReturnSelectionLabel = String((currentFocus && currentFocus.return_history_reason_resumed_return_active_selection_label) || "").trim();
      const resumedReturnReturnLabel = String((currentFocus && currentFocus.return_history_reason_resumed_return_return_label) || "").trim();
      const resumedReturnReturnSelectionLabel = String((currentFocus && currentFocus.return_history_reason_resumed_return_return_active_selection_label) || "").trim();
      const resumedReturnReturnReturnSelectionLabel = String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_active_selection_label) || "").trim();
      const resumedReturnReturnReturnReturnActiveLabel = String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_return_active_label) || "").trim();
      const confirmedResumedRestoredFocusActiveLabel = String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_return_return_active_label) || "").trim();
      const reopenedConfirmedResumedRestoredFocusActiveLabel = String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_return_return_return_active_label) || "").trim();
      const reopenedReopenedConfirmedFocusActiveLabel = String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_return_return_return_return_active_label) || "").trim();
      const reopenedReopenedReopenedConfirmedFocusActiveLabel = String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_return_return_return_return_return_active_label) || "").trim();
      const reopenedReopenedReopenedReconfirmedFocusActiveLabel = String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_active_label) || "").trim();
      const reopenedReopenedReopenedReopenedReconfirmedFocusActiveLabel = String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_active_label) || "").trim();
      const reopenedReopenedReopenedReopenedReopenedReconfirmedFocusActiveLabel = String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_active_label) || "").trim();
      const reopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusActiveLabel = String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_active_label) || "").trim();
      const reopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusActiveLabel = String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_active_label) || "").trim();
      const reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusActiveLabel = String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_label) || "").trim();
      const reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusActiveLabel = String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_label) || "").trim();
      const lastFollowedTargetLabel = String((currentFocus && currentFocus.active_target_label) || "").trim();
      const detail = applyMotionArtifactSnapshotPath(currentDetail, "proof");
      const focus = detail && detail.motion_artifact_focus_posture_snapshot_reason_focus && typeof detail.motion_artifact_focus_posture_snapshot_reason_focus === "object"
        ? detail.motion_artifact_focus_posture_snapshot_reason_focus
        : null;
      if (focus) {{
        const returnReasonResume = motionArtifactSnapshotReasonResumeMeta(detail);
        const resumedActive = motionArtifactSnapshotReasonResumedActiveMeta(detail);
        const resumedButtons = motionArtifactSnapshotReasonResumedActiveButtons(detail);
        const resumedReturn = motionArtifactSnapshotReasonResumedReturnMeta(detail, restoredSelectionLabel);
        const resumedReturnButtonLabel = motionArtifactSnapshotReasonResumedReturnButtonLabel(detail);
        const resumedReturnActive = motionArtifactSnapshotReasonResumedReturnActiveMeta(detail);
        const resumedReturnActiveButtons = motionArtifactSnapshotReasonResumedReturnActiveButtons(detail);
        const resumedReturnReturn = motionArtifactSnapshotReasonResumedReturnReturnMeta(detail, resumedReturnSelectionLabel);
        const resumedReturnReturnButtonLabel = motionArtifactSnapshotReasonResumedReturnReturnButtonLabel(detail);
        const resumedReturnReturnActive = motionArtifactSnapshotReasonResumedReturnReturnActiveMeta(detail);
        const resumedReturnReturnActiveButtons = motionArtifactSnapshotReasonResumedReturnReturnActiveButtons(detail);
        const resumedReturnReturnReturn = motionArtifactSnapshotReasonResumedReturnReturnReturnMeta(detail, resumedReturnReturnSelectionLabel);
        const resumedReturnReturnReturnActive = motionArtifactSnapshotReasonResumedReturnReturnReturnActiveMeta(detail);
        const resumedReturnReturnReturnActiveButtons = motionArtifactSnapshotReasonResumedReturnReturnReturnActiveButtons(detail);
        const resumedReturnReturnReturnReturn = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnMeta(detail, resumedReturnReturnReturnSelectionLabel);
        const resumedReturnReturnReturnReturnReturn = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnMeta(detail, resumedReturnReturnReturnSelectionLabel, resumedReturnReturnReturnReturnActiveLabel);
        const resumedReturnReturnReturnReturnReturnButtons = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnButtons(detail, resumedReturnReturnReturnReturnActiveLabel);
        const resumedReturnReturnReturnReturnReturnReturn = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnMeta(detail, confirmedResumedRestoredFocusActiveLabel);
        const resumedReturnReturnReturnReturnReturnReturnButtons = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnButtons(detail, confirmedResumedRestoredFocusActiveLabel);
        const resumedReturnReturnReturnReturnReturnReturnReturn = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnMeta(detail, reopenedConfirmedResumedRestoredFocusActiveLabel);
        const resumedReturnReturnReturnReturnReturnReturnReturnButtons = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnButtons(detail, reopenedConfirmedResumedRestoredFocusActiveLabel);
        const resumedReturnReturnReturnReturnReturnReturnReturnReturn = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnMeta(detail, reopenedReopenedConfirmedFocusActiveLabel);
        const resumedReturnReturnReturnReturnReturnReturnReturnReturnButtons = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnButtons(detail, reopenedReopenedConfirmedFocusActiveLabel);
        const resumedReturnReturnReturnReturnReturnReturnReturnReturnReturn = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnMeta(detail, reopenedReopenedReopenedConfirmedFocusActiveLabel);
        const resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnButtons = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnButtons(detail, reopenedReopenedReopenedConfirmedFocusActiveLabel);
      const resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturn = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnMeta(detail, reopenedReopenedReopenedReconfirmedFocusActiveLabel);
      const resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnButtons = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnButtons(detail, reopenedReopenedReopenedReconfirmedFocusActiveLabel);
      const resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturn = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnMeta(detail, reopenedReopenedReopenedReopenedReconfirmedFocusActiveLabel);
      const resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnButtons = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnButtons(detail, reopenedReopenedReopenedReopenedReconfirmedFocusActiveLabel);
      const resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturn = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnMeta(detail, reopenedReopenedReopenedReopenedReopenedReconfirmedFocusActiveLabel);
      const resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnButtons = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnButtons(detail, reopenedReopenedReopenedReopenedReopenedReconfirmedFocusActiveLabel);
      const resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturn = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnMeta(detail, reopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusActiveLabel);
      const resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnButtons = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnButtons(detail, reopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusActiveLabel);
      const resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturn = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnMeta(detail, reopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusActiveLabel);
      const resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnButtons = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnButtons(detail, reopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusActiveLabel);
      const resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturn = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnMeta(detail, reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusActiveLabel);
      const resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnButtons = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnButtons(detail, reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusActiveLabel);
      const resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturn = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnMeta(detail, reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusActiveLabel);
      const resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnButtons = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnButtons(detail, reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusActiveLabel);
        const resumedReturnReturnReturnReturnButtons = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnButtons(detail);
        focus.return_history_reason_resumed_label = String((returnReasonResume && returnReasonResume.label) || "").trim();
        focus.return_history_reason_resumed_class = String((returnReasonResume && returnReasonResume.className) || "steady").trim() || "steady";
        focus.return_history_reason_resumed_summary = String((returnReasonResume && returnReasonResume.summary) || "").trim();
        focus.return_history_reason_resumed_active_label = String((resumedActive && resumedActive.label) || "").trim();
        focus.return_history_reason_resumed_active_class = String((resumedActive && resumedActive.className) || "steady").trim() || "steady";
        focus.return_history_reason_resumed_active_summary = String((resumedActive && resumedActive.summary) || "").trim();
        focus.return_history_reason_resumed_active_buttons = resumedButtons;
        focus.return_history_reason_resumed_return_label = restoredSelectionLabel
          ? String((resumedReturn && resumedReturn.label) || "").trim()
          : "";
        focus.return_history_reason_resumed_return_class = restoredSelectionLabel
          ? String((resumedReturn && resumedReturn.className) || "steady").trim() || "steady"
          : "steady";
        focus.return_history_reason_resumed_return_summary = restoredSelectionLabel
          ? String((resumedReturn && resumedReturn.summary) || "").trim()
          : "";
        focus.return_history_reason_resumed_return_button_label = restoredSelectionLabel
          ? String(resumedReturnButtonLabel || "").trim()
          : "";
        focus.return_history_reason_resumed_return_active_label = resumedReturnLabel
          ? String((resumedReturnActive && resumedReturnActive.label) || "").trim()
          : "";
        focus.return_history_reason_resumed_return_active_class = resumedReturnLabel
          ? String((resumedReturnActive && resumedReturnActive.className) || "steady").trim() || "steady"
          : "steady";
        focus.return_history_reason_resumed_return_active_summary = resumedReturnLabel
          ? String((resumedReturnActive && resumedReturnActive.summary) || "").trim()
          : "";
        focus.return_history_reason_resumed_return_active_buttons = resumedReturnLabel
          ? resumedReturnActiveButtons
          : [];
        focus.return_history_reason_resumed_return_active_selection_label = "";
        focus.return_history_reason_resumed_return_active_selection_class = "steady";
        focus.return_history_reason_resumed_return_active_selection_summary = "";
        focus.return_history_reason_resumed_return_return_label = resumedReturnSelectionLabel
          ? String((resumedReturnReturn && resumedReturnReturn.label) || "").trim()
          : "";
        focus.return_history_reason_resumed_return_return_class = resumedReturnSelectionLabel
          ? String((resumedReturnReturn && resumedReturnReturn.className) || "steady").trim() || "steady"
          : "steady";
        focus.return_history_reason_resumed_return_return_summary = resumedReturnSelectionLabel
          ? String((resumedReturnReturn && resumedReturnReturn.summary) || "").trim()
          : "";
        focus.return_history_reason_resumed_return_return_button_label = resumedReturnSelectionLabel
          ? String(resumedReturnReturnButtonLabel || "").trim()
          : "";
        focus.return_history_reason_resumed_return_return_active_label = resumedReturnReturnLabel
          ? String((resumedReturnReturnActive && resumedReturnReturnActive.label) || "").trim()
          : "";
        focus.return_history_reason_resumed_return_return_active_class = resumedReturnReturnLabel
          ? String((resumedReturnReturnActive && resumedReturnReturnActive.className) || "steady").trim() || "steady"
          : "steady";
        focus.return_history_reason_resumed_return_return_active_summary = resumedReturnReturnLabel
          ? String((resumedReturnReturnActive && resumedReturnReturnActive.summary) || "").trim()
          : "";
        focus.return_history_reason_resumed_return_return_active_buttons = resumedReturnReturnLabel
          ? resumedReturnReturnActiveButtons
          : [];
        focus.return_history_reason_resumed_return_return_return_label = resumedReturnReturnSelectionLabel && ["resumed-restored-return", "resumed-restored-reason", "resumed-restored-focus-return"].includes(String(mode || "").trim())
          ? String((resumedReturnReturnReturn && resumedReturnReturnReturn.label) || "").trim()
          : "";
        focus.return_history_reason_resumed_return_return_return_class = resumedReturnReturnSelectionLabel && ["resumed-restored-return", "resumed-restored-reason", "resumed-restored-focus-return"].includes(String(mode || "").trim())
          ? String((resumedReturnReturnReturn && resumedReturnReturnReturn.className) || "steady").trim() || "steady"
          : "steady";
        focus.return_history_reason_resumed_return_return_return_summary = resumedReturnReturnSelectionLabel && ["resumed-restored-return", "resumed-restored-reason", "resumed-restored-focus-return"].includes(String(mode || "").trim())
          ? String((resumedReturnReturnReturn && resumedReturnReturnReturn.summary) || "").trim()
          : "";
        focus.return_history_reason_resumed_return_return_return_active_label = String(mode || "").trim() === "resumed-restored-reason"
          ? String((resumedReturnReturnReturnActive && resumedReturnReturnReturnActive.label) || "").trim()
          : "";
        focus.return_history_reason_resumed_return_return_return_active_class = String(mode || "").trim() === "resumed-restored-reason"
          ? String((resumedReturnReturnReturnActive && resumedReturnReturnReturnActive.className) || "steady").trim() || "steady"
          : "steady";
        focus.return_history_reason_resumed_return_return_return_active_summary = String(mode || "").trim() === "resumed-restored-reason"
          ? String((resumedReturnReturnReturnActive && resumedReturnReturnReturnActive.summary) || "").trim()
          : "";
        focus.return_history_reason_resumed_return_return_return_active_buttons = String(mode || "").trim() === "resumed-restored-reason"
          ? resumedReturnReturnReturnActiveButtons
          : [];
        focus.return_history_reason_resumed_return_return_return_return_label = resumedReturnReturnReturnSelectionLabel && String(mode || "").trim() === "resumed-restored-focus-return"
          ? String((resumedReturnReturnReturnReturn && resumedReturnReturnReturnReturn.label) || "").trim()
          : "";
        focus.return_history_reason_resumed_return_return_return_return_class = resumedReturnReturnReturnSelectionLabel && String(mode || "").trim() === "resumed-restored-focus-return"
          ? String((resumedReturnReturnReturnReturn && resumedReturnReturnReturnReturn.className) || "steady").trim() || "steady"
          : "steady";
        focus.return_history_reason_resumed_return_return_return_return_summary = resumedReturnReturnReturnSelectionLabel && String(mode || "").trim() === "resumed-restored-focus-return"
          ? String((resumedReturnReturnReturnReturn && resumedReturnReturnReturnReturn.summary) || "").trim()
          : "";
        focus.return_history_reason_resumed_return_return_return_return_buttons = resumedReturnReturnReturnSelectionLabel && String(mode || "").trim() === "resumed-restored-focus-return"
          ? resumedReturnReturnReturnReturnButtons
          : [];
        focus.return_history_reason_resumed_return_return_return_return_return_label = resumedReturnReturnReturnSelectionLabel && String(mode || "").trim() === "resumed-restored-focus-return"
          ? String((resumedReturnReturnReturnReturnReturn && resumedReturnReturnReturnReturnReturn.label) || "").trim()
          : "";
        focus.return_history_reason_resumed_return_return_return_return_return_class = resumedReturnReturnReturnSelectionLabel && String(mode || "").trim() === "resumed-restored-focus-return"
          ? String((resumedReturnReturnReturnReturnReturn && resumedReturnReturnReturnReturnReturn.className) || "steady").trim() || "steady"
          : "steady";
        focus.return_history_reason_resumed_return_return_return_return_return_summary = resumedReturnReturnReturnSelectionLabel && String(mode || "").trim() === "resumed-restored-focus-return"
          ? String((resumedReturnReturnReturnReturnReturn && resumedReturnReturnReturnReturnReturn.summary) || "").trim()
          : "";
        focus.return_history_reason_resumed_return_return_return_return_return_buttons = resumedReturnReturnReturnSelectionLabel && String(mode || "").trim() === "resumed-restored-focus-return"
          ? resumedReturnReturnReturnReturnReturnButtons
          : [];
        focus.return_history_reason_resumed_return_return_return_return_return_return_label = confirmedResumedRestoredFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"
          ? String((resumedReturnReturnReturnReturnReturnReturn && resumedReturnReturnReturnReturnReturnReturn.label) || "").trim()
          : "";
        focus.return_history_reason_resumed_return_return_return_return_return_return_class = confirmedResumedRestoredFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"
          ? String((resumedReturnReturnReturnReturnReturnReturn && resumedReturnReturnReturnReturnReturnReturn.className) || "steady").trim() || "steady"
          : "steady";
        focus.return_history_reason_resumed_return_return_return_return_return_return_summary = confirmedResumedRestoredFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"
          ? String((resumedReturnReturnReturnReturnReturnReturn && resumedReturnReturnReturnReturnReturnReturn.summary) || "").trim()
          : "";
        focus.return_history_reason_resumed_return_return_return_return_return_return_buttons = confirmedResumedRestoredFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"
          ? resumedReturnReturnReturnReturnReturnReturnButtons
          : [];
        focus.return_history_reason_resumed_return_return_return_return_return_return_return_label = reopenedConfirmedResumedRestoredFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"
          ? String((resumedReturnReturnReturnReturnReturnReturnReturn && resumedReturnReturnReturnReturnReturnReturnReturn.label) || "").trim()
          : "";
        focus.return_history_reason_resumed_return_return_return_return_return_return_return_class = reopenedConfirmedResumedRestoredFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"
          ? String((resumedReturnReturnReturnReturnReturnReturnReturn && resumedReturnReturnReturnReturnReturnReturnReturn.className) || "steady").trim() || "steady"
          : "steady";
        focus.return_history_reason_resumed_return_return_return_return_return_return_return_summary = reopenedConfirmedResumedRestoredFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"
          ? String((resumedReturnReturnReturnReturnReturnReturnReturn && resumedReturnReturnReturnReturnReturnReturnReturn.summary) || "").trim()
          : "";
        focus.return_history_reason_resumed_return_return_return_return_return_return_return_buttons = reopenedConfirmedResumedRestoredFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"
          ? resumedReturnReturnReturnReturnReturnReturnReturnButtons
          : [];
        focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_label = reopenedReopenedConfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"
          ? String((resumedReturnReturnReturnReturnReturnReturnReturnReturn && resumedReturnReturnReturnReturnReturnReturnReturnReturn.label) || "").trim()
          : "";
        focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_class = reopenedReopenedConfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"
          ? String((resumedReturnReturnReturnReturnReturnReturnReturnReturn && resumedReturnReturnReturnReturnReturnReturnReturnReturn.className) || "steady").trim() || "steady"
          : "steady";
        focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_summary = reopenedReopenedConfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"
          ? String((resumedReturnReturnReturnReturnReturnReturnReturnReturn && resumedReturnReturnReturnReturnReturnReturnReturnReturn.summary) || "").trim()
          : "";
        focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_buttons = reopenedReopenedConfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"
          ? resumedReturnReturnReturnReturnReturnReturnReturnReturnButtons
          : [];
        focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_label = reopenedReopenedReopenedConfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"
          ? String((resumedReturnReturnReturnReturnReturnReturnReturnReturnReturn && resumedReturnReturnReturnReturnReturnReturnReturnReturnReturn.label) || "").trim()
          : "";
        focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_class = reopenedReopenedReopenedConfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"
          ? String((resumedReturnReturnReturnReturnReturnReturnReturnReturnReturn && resumedReturnReturnReturnReturnReturnReturnReturnReturnReturn.className) || "steady").trim() || "steady"
          : "steady";
        focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_summary = reopenedReopenedReopenedConfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"
          ? String((resumedReturnReturnReturnReturnReturnReturnReturnReturnReturn && resumedReturnReturnReturnReturnReturnReturnReturnReturnReturn.summary) || "").trim()
          : "";
        focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_buttons = reopenedReopenedReopenedConfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"
          ? resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnButtons
          : [];
        focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_label = reopenedReopenedReopenedReconfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"
          ? String((resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturn && resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturn.label) || "").trim()
          : "";
        focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_class = reopenedReopenedReopenedReconfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"
          ? String((resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturn && resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturn.className) || "steady").trim() || "steady"
          : "steady";
        focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_summary = reopenedReopenedReopenedReconfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"
          ? String((resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturn && resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturn.summary) || "").trim()
          : "";
        focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_buttons = reopenedReopenedReopenedReconfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"
          ? resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnButtons
          : [];
        focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_label = reopenedReopenedReopenedReopenedReconfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"
          ? String((resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturn && resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturn.label) || "").trim()
          : "";
        focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_class = reopenedReopenedReopenedReopenedReconfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"
          ? String((resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturn && resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturn.className) || "steady").trim() || "steady"
          : "steady";
        focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_summary = reopenedReopenedReopenedReopenedReconfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"
          ? String((resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturn && resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturn.summary) || "").trim()
          : "";
        focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_buttons = reopenedReopenedReopenedReopenedReconfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"
          ? resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnButtons
          : [];
        focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_label = reopenedReopenedReopenedReopenedReopenedReconfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"
          ? String((resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturn && resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturn.label) || "").trim()
          : "";
        focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_class = reopenedReopenedReopenedReopenedReopenedReconfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"
          ? String((resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturn && resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturn.className) || "steady").trim() || "steady"
          : "steady";
        focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_summary = reopenedReopenedReopenedReopenedReopenedReconfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"
          ? String((resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturn && resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturn.summary) || "").trim()
          : "";
        focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_buttons = reopenedReopenedReopenedReopenedReopenedReconfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"
          ? resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnButtons
          : [];
        focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_label = reopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"
          ? String((resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturn && resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturn.label) || "").trim()
          : "";
        focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_class = reopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"
          ? String((resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturn && resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturn.className) || "steady").trim() || "steady"
          : "steady";
        focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_summary = reopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"
          ? String((resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturn && resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturn.summary) || "").trim()
          : "";
        focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_buttons = reopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"
          ? resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnButtons
          : [];
        focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_label = reopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"
          ? String((resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturn && resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturn.label) || "").trim()
          : "";
        focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_class = reopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"
          ? String((resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturn && resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturn.className) || "steady").trim() || "steady"
          : "steady";
        focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_summary = reopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"
          ? String((resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturn && resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturn.summary) || "").trim()
          : "";
        focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_buttons = reopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"
          ? resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnButtons
          : [];
        focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_label = reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"
          ? String((resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturn && resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturn.label) || "").trim()
          : "";
        focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_class = reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"
          ? String((resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturn && resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturn.className) || "steady").trim() || "steady"
          : "steady";
        focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_summary = reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"
          ? String((resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturn && resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturn.summary) || "").trim()
          : "";
        focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_buttons = reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"
          ? resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnButtons
          : [];
        focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_label = reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"
          ? String((resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturn && resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturn.label) || "").trim()
          : "";
        focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_class = reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"
          ? String((resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturn && resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturn.className) || "steady").trim() || "steady"
          : "steady";
        focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_summary = reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"
          ? String((resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturn && resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturn.summary) || "").trim()
          : [];
        focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_label = reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"
          ? String((resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturn && resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturn.label) || "").trim()
          : "";
        focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_class = reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"
          ? String((resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturn && resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturn.className) || "steady").trim() || "steady"
          : "steady";
        focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_summary = reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"
          ? String((resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturn && resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturn.summary) || "").trim()
          : "";
        focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_buttons = reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"
          ? resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnButtons
          : [];
        focus.restored_target_last_followed_label = lastFollowedTargetLabel && String(mode || "").trim() === "resumed-restored-focus-return"
          ? lastFollowedTargetLabel
          : "";
        focus.restored_target_last_followed_class = focus.restored_target_last_followed_label
          ? "accepted"
          : "steady";
        focus.restored_target_last_followed_summary = focus.restored_target_last_followed_label
          ? "Last followed from restored target proof: " + focus.restored_target_last_followed_label + "."
          : "";
      }}
      const restoredReasonMode = String(mode || "restored-reason").trim();
      detail.change_summary = restoredReasonMode === "restored-return"
        ? "Returned to the restored evidence lane."
        : restoredReasonMode === "resumed-return"
        ? "Returned to the resumed evidence lane."
        : restoredReasonMode === "resumed-restored-return"
        ? "Returned to the resumed restored evidence lane."
        : restoredReasonMode === "resumed-restored-focus-return"
        ? "Returned to the resumed restored focus lane."
        : restoredReasonMode === "resumed-restored-reason"
        ? "Focused resumed restored evidence from the resumed restored proof row."
        : "Focused restored evidence from the reopened proof resume row.";
      detail.change_evidence_summary = restoredReasonMode === "restored-reason"
        ? String((detail.motion_artifact_focus_posture_snapshot_reason_focus || {{}}).return_history_reason_resumed_summary || "Focused the restored stored evidence from the reopened proof resume row.").trim()
        : restoredReasonMode === "resumed-restored-reason"
        ? String((detail.motion_artifact_focus_posture_snapshot_reason_focus || {{}}).return_history_reason_resumed_return_return_return_summary || "Focused the resumed restored stored evidence from the resumed restored proof row.").trim()
        : restoredReasonMode === "resumed-restored-focus-return"
        ? String((detail.motion_artifact_focus_posture_snapshot_reason_focus || {{}}).restored_target_last_followed_summary || (detail.motion_artifact_focus_posture_snapshot_reason_focus || {{}}).return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_summary || (detail.motion_artifact_focus_posture_snapshot_reason_focus || {{}}).return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_summary || (detail.motion_artifact_focus_posture_snapshot_reason_focus || {{}}).return_history_reason_resumed_return_return_return_RETURN_returnRETURN_returnRETURN_returnSUMMARY || (detail.motion_artifact_focus_posture_snapshot_reason_focus || {{}}).return_history_reason_resumed_return_returnRETURN_returnRETURN_returnSUMMARY || (detail.motion_artifact_focus_posture_snapshot_reason_focus || {{}}).return_history_reason_resumed_return_returnRETURN_returnSUMMARY || "Returned to the resumed restored focus lane.").trim()
        : detail.change_summary;
      if (restoredReasonMode === "resumed-restored-focus-return" && String((detail.motion_artifact_focus_posture_snapshot_reason_focus || {{}}).restored_target_last_followed_label || "").trim()) {{
        detail.action_result_summary = String(detail.action_result_summary || "Returned from the followed restored target into the persistent proof lane.").trim();
        recordMotionArtifactHistory(detail, {{
          actionLabel: "Return to Restored Target Proof",
          historyButtons: Array.isArray((detail.motion_artifact_focus_posture_snapshot_reason_focus || {{}}).return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_buttons)
            ? (detail.motion_artifact_focus_posture_snapshot_reason_focus || {{}}).return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_buttons
            : [],
          result: {{
            status: "returned",
            detail: detail.change_evidence_summary,
          }},
        }});
        applyMotionArtifactHistory(detail);
        detail.motion_artifact_focus_history_note = `Recent round-trip: ${{String(detail.change_evidence_summary || "Returned to restored target proof.").trim()}}`;
      }}
      return detail;
    }}

    function motionArtifactSnapshotContextSummary(detail) {{
      const focus = detail && detail.motion_artifact_focus_posture_snapshot_reason_focus && typeof detail.motion_artifact_focus_posture_snapshot_reason_focus === "object"
        ? detail.motion_artifact_focus_posture_snapshot_reason_focus
        : null;
      const laneLabel = String((focus && focus.active_path_label) || "proof focus").trim() || "proof focus";
      const originLabel = String((focus && focus.return_history_origin_label) || "latest outcome").trim() || "latest outcome";
      const outcome = motionArtifactSnapshotReturnOutcome(detail);
      const targetLabel = String((focus && focus.active_target_label) || motionArtifactSnapshotRecordLabel(detail) || "the current localized record").trim();
      return `Current proof context: ${{laneLabel}} / ${{originLabel}} / ${{outcome || "updated"}} / ${{targetLabel}}.`;
    }}

    function motionArtifactSnapshotContextButtons(detail) {{
      const focus = detail && detail.motion_artifact_focus_posture_snapshot_reason_focus && typeof detail.motion_artifact_focus_posture_snapshot_reason_focus === "object"
        ? detail.motion_artifact_focus_posture_snapshot_reason_focus
        : null;
      if (!focus) return [];
      const target = detail && detail.motion_artifact_focus_posture_snapshot_reason_target && typeof detail.motion_artifact_focus_posture_snapshot_reason_target === "object"
        ? detail.motion_artifact_focus_posture_snapshot_reason_target
        : null;
      const buttons = [];
      const laneLabel = String((focus.active_path_label || "proof focus")).trim().toLowerCase();
      if (laneLabel.includes("mutation") && Number.isInteger(focus.return_history_index)) {{
        buttons.push({{
          kind: "history",
          history_index: Number(focus.return_history_index),
          label: "Open Mutation Lane",
          active: true,
          active_label: "Open Mutation Lane (Current)",
        }});
      }} else if (laneLabel.includes("chronology") && target && Number.isInteger(target.timeline_event_index)) {{
        buttons.push({{
          kind: "timeline",
          timeline_event_index: Number(target.timeline_event_index),
          label: "Open Chronology Lane",
          active: true,
          active_label: "Open Chronology Lane (Current)",
        }});
      }} else {{
        buttons.push({{
          kind: "proof",
          label: "Open Proof Lane",
          active: true,
          active_label: "Open Proof Lane (Current)",
        }});
      }}
      if (Number.isInteger(focus.return_history_index)) {{
        buttons.push({{
          kind: "history",
          history_index: Number(focus.return_history_index),
          label: String(focus.return_history_label || "Reopen Latest Outcome").trim() || "Reopen Latest Outcome",
        }});
      }}
      const targetButtons = Array.isArray(focus.active_target_buttons) ? focus.active_target_buttons : [];
      const artifactButton = targetButtons.find((item) => item && item.kind === "artifact");
      if (artifactButton && Number.isInteger(artifactButton.motion_artifact_index)) {{
        buttons.push({{
          kind: "artifact",
          motion_artifact_index: Number(artifactButton.motion_artifact_index),
          label: String(artifactButton.label || "Inspect Exact Artifact").trim() || "Inspect Exact Artifact",
        }});
      }} else {{
        const timelineButton = targetButtons.find((item) => item && item.kind === "timeline");
        if (timelineButton && Number.isInteger(timelineButton.timeline_event_index)) {{
          buttons.push({{
            kind: "target-timeline",
            timeline_event_index: Number(timelineButton.timeline_event_index),
            label: String(timelineButton.label || "Inspect Matching Timeline").trim() || "Inspect Matching Timeline",
          }});
        }}
      }}
      return buttons;
    }}

    function motionArtifactSnapshotContextSelection(detail) {{
      const focus = detail && detail.motion_artifact_focus_posture_snapshot_reason_focus && typeof detail.motion_artifact_focus_posture_snapshot_reason_focus === "object"
        ? detail.motion_artifact_focus_posture_snapshot_reason_focus
        : null;
      if (!focus) return null;
      const laneLabel = String((focus.active_path_label || "proof focus")).trim().toLowerCase();
      const recordLabel = motionArtifactSnapshotRecordLabel(detail);
      const targetSummary = `Anchored to ${{recordLabel}}.`;
      if (laneLabel.includes("mutation")) {{
        return {{ label: "mutation lane active", className: "steady", target: targetSummary }};
      }}
      if (laneLabel.includes("chronology")) {{
        return {{ label: "chronology lane active", className: "accepted", target: targetSummary }};
      }}
      return {{ label: "proof lane active", className: "first-seen", target: targetSummary }};
    }}

    function motionArtifactSnapshotContextSelectionButtons(detail) {{
      const focus = detail && detail.motion_artifact_focus_posture_snapshot_reason_focus && typeof detail.motion_artifact_focus_posture_snapshot_reason_focus === "object"
        ? detail.motion_artifact_focus_posture_snapshot_reason_focus
        : null;
      if (!focus) return [];
      const laneLabel = String((focus.active_path_label || "proof focus")).trim().toLowerCase();
      const targetButtons = Array.isArray(focus.active_target_buttons) ? focus.active_target_buttons : [];
      const artifactButton = targetButtons.find((item) => item && item.kind === "artifact" && Number.isInteger(item.motion_artifact_index));
      const timelineButton = targetButtons.find((item) => item && item.kind === "timeline" && Number.isInteger(item.timeline_event_index));
      const buttons = [];
      if (laneLabel.includes("chronology") && timelineButton) {{
        buttons.push({{
          kind: "timeline",
          timeline_event_index: Number(timelineButton.timeline_event_index),
          label: "Open Anchored Timeline",
        }});
      }}
      if (artifactButton) {{
        buttons.push({{
          kind: "artifact",
          motion_artifact_index: Number(artifactButton.motion_artifact_index),
          label: "Open Anchored Artifact",
        }});
      }}
      if (!buttons.length && timelineButton) {{
        buttons.push({{
          kind: "timeline",
          timeline_event_index: Number(timelineButton.timeline_event_index),
          label: "Open Anchored Timeline",
        }});
      }}
      return buttons;
    }}

    function applyMotionArtifactSnapshotPath(detail, pathKind = "proof") {{
      const target = detail && detail.motion_artifact_focus_posture_snapshot_reason_target && typeof detail.motion_artifact_focus_posture_snapshot_reason_target === "object"
        ? detail.motion_artifact_focus_posture_snapshot_reason_target
        : null;
      if (!target) return detail;
      focusMotionArtifactSnapshotReason(detail);
      const focus = detail && detail.motion_artifact_focus_posture_snapshot_reason_focus && typeof detail.motion_artifact_focus_posture_snapshot_reason_focus === "object"
        ? detail.motion_artifact_focus_posture_snapshot_reason_focus
        : null;
      if (!focus) return detail;
      const meta = motionArtifactSnapshotPathMeta(pathKind);
      const reasonActiveMeta = motionArtifactSnapshotReasonActiveMeta(detail);
      const reasonActiveTarget = motionArtifactSnapshotReasonActiveTarget(detail);
      const reasonActiveButtons = motionArtifactSnapshotReasonActiveButtons(detail);
      focus.active_path_label = String((meta && meta.label) || "proof focus").trim() || "proof focus";
      focus.active_path_class = String((meta && meta.className) || "first-seen").trim() || "first-seen";
      focus.active_path_summary = String((meta && meta.summary) || "Active path: reopened proof focus.").trim() || "Active path: reopened proof focus.";
      focus.return_history_reason_active_label = pathKind === "proof" && Number.isInteger(focus.return_history_index)
        ? String((reasonActiveMeta && reasonActiveMeta.label) || "").trim()
        : "";
      focus.return_history_reason_active_class = pathKind === "proof" && Number.isInteger(focus.return_history_index)
        ? String((reasonActiveMeta && reasonActiveMeta.className) || "steady").trim() || "steady"
        : "steady";
      focus.return_history_reason_active_summary = pathKind === "proof" && Number.isInteger(focus.return_history_index)
        ? String((reasonActiveMeta && reasonActiveMeta.summary) || "").trim()
        : "";
      focus.return_history_reason_active_target = pathKind === "proof" && Number.isInteger(focus.return_history_index)
        ? String(reasonActiveTarget || "").trim()
        : "";
      focus.return_history_reason_active_buttons = pathKind === "proof" && Number.isInteger(focus.return_history_index)
        ? reasonActiveButtons
        : [];
      focus.return_history_reason_active_selection_label = "";
      focus.return_history_reason_active_selection_class = "steady";
      focus.return_history_reason_active_selection_summary = "";
      focus.return_history_reason_resumed_label = "";
      focus.return_history_reason_resumed_class = "steady";
      focus.return_history_reason_resumed_summary = "";
      focus.return_history_reason_resumed_active_label = "";
      focus.return_history_reason_resumed_active_class = "steady";
      focus.return_history_reason_resumed_active_summary = "";
      focus.return_history_reason_resumed_active_buttons = [];
      focus.return_history_reason_resumed_active_selection_label = "";
      focus.return_history_reason_resumed_active_selection_class = "steady";
      focus.return_history_reason_resumed_active_selection_summary = "";
      focus.return_history_reason_resumed_return_label = "";
      focus.return_history_reason_resumed_return_class = "steady";
      focus.return_history_reason_resumed_return_summary = "";
      focus.return_history_reason_resumed_return_button_label = "";
      focus.return_history_reason_resumed_return_active_label = "";
      focus.return_history_reason_resumed_return_active_class = "steady";
      focus.return_history_reason_resumed_return_active_summary = "";
      focus.return_history_reason_resumed_return_active_buttons = [];
      focus.return_history_reason_resumed_return_active_selection_label = "";
      focus.return_history_reason_resumed_return_active_selection_class = "steady";
      focus.return_history_reason_resumed_return_active_selection_summary = "";
      focus.return_history_reason_resumed_return_return_label = "";
      focus.return_history_reason_resumed_return_return_class = "steady";
      focus.return_history_reason_resumed_return_return_summary = "";
      focus.return_history_reason_resumed_return_return_button_label = "";
      focus.return_history_reason_resumed_return_return_active_label = "";
      focus.return_history_reason_resumed_return_return_active_class = "steady";
      focus.return_history_reason_resumed_return_return_active_summary = "";
      focus.return_history_reason_resumed_return_return_active_buttons = [];
      focus.return_history_reason_resumed_return_return_active_selection_label = "";
      focus.return_history_reason_resumed_return_return_active_selection_class = "steady";
      focus.return_history_reason_resumed_return_return_active_selection_summary = "";
      focus.return_history_reason_resumed_return_return_return_label = "";
      focus.return_history_reason_resumed_return_return_return_class = "steady";
      focus.return_history_reason_resumed_return_return_return_summary = "";
      focus.return_history_reason_resumed_return_return_return_active_label = "";
      focus.return_history_reason_resumed_return_return_return_active_class = "steady";
      focus.return_history_reason_resumed_return_return_return_active_summary = "";
      focus.return_history_reason_resumed_return_return_return_active_buttons = [];
      focus.return_history_reason_resumed_return_return_return_active_selection_label = "";
      focus.return_history_reason_resumed_return_return_return_active_selection_class = "steady";
      focus.return_history_reason_resumed_return_return_return_active_selection_summary = "";
      focus.return_history_reason_resumed_return_return_return_return_label = "";
      focus.return_history_reason_resumed_return_return_return_return_class = "steady";
      focus.return_history_reason_resumed_return_return_return_return_summary = "";
      focus.return_history_reason_resumed_return_return_return_return_buttons = [];
      focus.return_history_reason_resumed_return_return_return_return_return_label = "";
      focus.return_history_reason_resumed_return_return_return_return_return_class = "steady";
      focus.return_history_reason_resumed_return_return_return_return_return_summary = "";
      focus.return_history_reason_resumed_return_return_return_return_return_buttons = [];
      focus.return_history_reason_resumed_return_return_return_return_return_active_label = "";
      focus.return_history_reason_resumed_return_return_return_return_return_active_class = "steady";
      focus.return_history_reason_resumed_return_return_return_return_return_active_summary = "";
      focus.return_history_reason_resumed_return_return_return_return_return_return_label = "";
      focus.return_history_reason_resumed_return_return_return_return_return_return_class = "steady";
      focus.return_history_reason_resumed_return_return_return_return_return_return_summary = "";
      focus.return_history_reason_resumed_return_return_return_return_return_return_buttons = [];
      focus.return_history_reason_resumed_return_return_return_return_return_return_active_label = "";
      focus.return_history_reason_resumed_return_return_return_return_return_return_active_class = "steady";
      focus.return_history_reason_resumed_return_return_return_return_return_return_active_summary = "";
      focus.return_history_reason_resumed_return_return_return_return_return_return_return_label = "";
      focus.return_history_reason_resumed_return_return_return_return_return_return_return_class = "steady";
      focus.return_history_reason_resumed_return_return_return_return_return_return_return_summary = "";
      focus.return_history_reason_resumed_return_return_return_return_return_return_return_buttons = [];
      focus.return_history_reason_resumed_return_return_return_return_return_return_return_active_label = "";
      focus.return_history_reason_resumed_return_return_return_return_return_return_return_active_class = "steady";
      focus.return_history_reason_resumed_return_return_return_return_return_return_return_active_summary = "";
      focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_label = "";
      focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_class = "steady";
      focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_summary = "";
      focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_buttons = [];
      focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_active_label = "";
      focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_active_class = "steady";
      focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_active_summary = "";
      focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_label = "";
      focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_class = "steady";
      focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_summary = "";
      focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_buttons = [];
      focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_buttons = [];
      focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_active_label = "";
      focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_active_class = "steady";
      focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_active_summary = "";
      focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_label = "";
      focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_class = "steady";
      focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_summary = "";
      focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_buttons = [];
      focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_label = "";
      focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_class = "steady";
      focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_summary = "";
      focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_buttons = [];
      focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_label = "";
      focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_class = "steady";
      focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_summary = "";
      focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_buttons = [];
      focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_label = "";
      focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_class = "steady";
      focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_summary = "";
      focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_buttons = [];
      focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_label = "";
      focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_class = "steady";
      focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_summary = "";
      focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_label = "";
      focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_class = "steady";
      focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_summary = "";
      focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_buttons = [];
      focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_buttons = [];
      focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_label = "";
      focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_class = "steady";
      focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_summary = "";
      focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_active_label = "";
      focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_active_class = "steady";
      focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_active_summary = "";
      focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_active_label = "";
      focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_active_class = "steady";
      focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_active_summary = "";
      focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_active_label = "";
      focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_active_class = "steady";
      focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_active_summary = "";
      focus.return_history_reason_resumed_return_return_return_return_active_label = "";
      focus.return_history_reason_resumed_return_return_return_return_active_class = "steady";
      focus.return_history_reason_resumed_return_return_return_return_active_summary = "";
      focus.active_target_label = motionArtifactSnapshotTargetLabel(detail, pathKind);
      focus.active_target_buttons = motionArtifactSnapshotTargetButtons(detail);
      focus.context_summary = motionArtifactSnapshotContextSummary(detail);
      focus.context_buttons = motionArtifactSnapshotContextButtons(detail);
      const contextSelection = motionArtifactSnapshotContextSelection(detail);
      focus.context_selection_label = String((contextSelection && contextSelection.label) || "").trim();
      focus.context_selection_class = String((contextSelection && contextSelection.className) || "steady").trim() || "steady";
      focus.context_selection_target = String((contextSelection && contextSelection.target) || "").trim();
      focus.context_selection_buttons = motionArtifactSnapshotContextSelectionButtons(detail);
      focus.context_selection_confirmation_label = "";
      focus.context_selection_confirmation_class = "steady";
      focus.return_confirmation_label = "";
      focus.return_confirmation_class = "steady";
      focus.return_confirmation_summary = "";
      focus.return_summary = pathKind === "proof"
        ? String(focus.return_summary || "").trim()
        : "";
      focus.return_history_index = pathKind === "proof" && Number.isInteger(focus.return_history_index)
        ? Number(focus.return_history_index)
        : null;
      focus.return_history_label = pathKind === "proof" && focus.return_history_index !== null
        ? String(focus.return_history_label || "Reopen Latest Outcome").trim() || "Reopen Latest Outcome"
        : "";
      focus.return_history_reason = pathKind === "proof" && focus.return_history_index !== null
        ? String(focus.return_history_reason || "").trim()
        : "";
      focus.return_history_reason_button_label = pathKind === "proof" && focus.return_history_index !== null
        ? String(focus.return_history_reason_button_label || "").trim()
        : "";
      focus.return_history_reason_source_label = pathKind === "proof" && focus.return_history_index !== null
        ? String(focus.return_history_reason_source_label || "").trim()
        : "";
      focus.return_history_reason_source_class = pathKind === "proof" && focus.return_history_index !== null
        ? String(focus.return_history_reason_source_class || "artifact").trim() || "artifact"
        : "artifact";
      focus.return_history_origin_label = pathKind === "proof" && focus.return_history_index !== null
        ? String(focus.return_history_origin_label || "latest outcome").trim() || "latest outcome"
        : "";
      focus.return_history_origin_class = pathKind === "proof" && focus.return_history_index !== null
        ? String(focus.return_history_origin_class || "artifact").trim() || "artifact"
        : "artifact";
      focus.return_history_lane_label = pathKind === "proof" && focus.return_history_index !== null
        ? String(focus.return_history_lane_label || "").trim()
        : "";
      focus.return_history_lane_class = pathKind === "proof" && focus.return_history_index !== null
        ? String(focus.return_history_lane_class || "steady").trim() || "steady"
        : "steady";
      return detail;
    }}

    function jumpToMotionArtifactSnapshotTargetArtifact(index, source = "", historyIndex = null) {{
      const currentDetail = selectedDetail();
      const pathKind = motionArtifactSnapshotCurrentPathKind(currentDetail);
      const currentFocus = currentDetail && currentDetail.motion_artifact_focus_posture_snapshot_reason_focus && typeof currentDetail.motion_artifact_focus_posture_snapshot_reason_focus === "object"
        ? currentDetail.motion_artifact_focus_posture_snapshot_reason_focus
        : null;
      const restoredActive = Boolean(String((currentFocus && currentFocus.return_history_reason_resumed_active_label) || "").trim());
      const resumedReturnActive = Boolean(String((currentFocus && currentFocus.return_history_reason_resumed_return_active_label) || "").trim());
      const resumedReturnReturnActive = Boolean(String((currentFocus && currentFocus.return_history_reason_resumed_return_return_active_label) || "").trim());
      const resumedReturnReturnReturnActive = Boolean(String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_active_label) || "").trim());
      const resumedReturnReturnReturnReturnReturnActive = Boolean(String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_return_return_label) || "").trim());
      const resumedReturnReturnReturnReturnReturnReturnActive = Boolean(String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_return_return_return_label) || "").trim());
      const resumedReturnReturnReturnReturnReturnReturnReturnActive = Boolean(String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_return_return_return_return_label) || "").trim());
      const resumedReturnReturnReturnReturnReturnReturnReturnReturnActive = Boolean(String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_return_return_return_return_return_label) || "").trim());
      const resumedReturnReturnReturnReturnReturnReturnReturnReturnActiveSelection = Boolean(String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_return_return_return_return_return_label) || "").trim());
      const resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnActive = Boolean(String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_label) || "").trim());
      const resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnActive = Boolean(String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_label) || "").trim());
      const resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnActive = Boolean(String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_label) || "").trim());
      const resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnActive = Boolean(String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_label) || "").trim());
      const resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnActive = Boolean(String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_label) || "").trim());
      const resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnActive = Boolean(String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_label) || "").trim());
      const resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnActive = Boolean(String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_label) || "").trim());
      const resumedReturnReturnReturnReturnReturnActive = Boolean(String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_return_return_label) || "").trim());
      const resumedReturnReturnReturnReturnReturnReturnActive = Boolean(String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_return_return_return_label) || "").trim());
      const resumedReturnReturnActive = Boolean(String((currentFocus && currentFocus.return_history_reason_resumed_return_return_active_label) || "").trim());
      const resumedReturnReturnReturnActive = Boolean(String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_active_label) || "").trim());
      const resumedReturnReturnReturnReturnReturnActive = Boolean(String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_return_return_label) || "").trim());
      const reasonTarget = currentDetail && currentDetail.motion_artifact_focus_posture_snapshot_reason_target && typeof currentDetail.motion_artifact_focus_posture_snapshot_reason_target === "object"
        ? Object.assign({{}}, currentDetail.motion_artifact_focus_posture_snapshot_reason_target)
        : null;
      const reasonText = String((currentDetail && currentDetail.motion_artifact_focus_posture_snapshot_reason) || "").trim();
      const snapshotAction = currentDetail && currentDetail.motion_artifact_focus_posture_snapshot_action && typeof currentDetail.motion_artifact_focus_posture_snapshot_action === "object"
        ? Object.assign({{}}, currentDetail.motion_artifact_focus_posture_snapshot_action)
        : null;
      currentMotionArtifactIndex = Number(index) || 0;
      const detail = jumpToMotionArtifact(index);
      detail.motion_artifact_focus_posture_snapshot_reason = reasonText;
      detail.motion_artifact_focus_posture_snapshot_action = snapshotAction;
      detail.motion_artifact_focus_posture_snapshot_reason_target = reasonTarget;
      applyMotionArtifactSnapshotPath(detail, pathKind);
      if (detail.motion_artifact_focus_posture_snapshot_reason_focus && typeof detail.motion_artifact_focus_posture_snapshot_reason_focus === "object") {{
        const evidenceSelection = motionArtifactSnapshotReasonSelectionMeta("artifact", detail);
        detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_active_selection_label = String((evidenceSelection && evidenceSelection.label) || "").trim();
        detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_active_selection_class = String((evidenceSelection && evidenceSelection.className) || "steady").trim() || "steady";
        detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_active_selection_summary = String((evidenceSelection && evidenceSelection.summary) || "").trim();
        if (restoredActive) {{
          const restoredSelection = motionArtifactSnapshotReasonResumedSelectionMeta("artifact", detail);
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_active_selection_label = String((restoredSelection && restoredSelection.label) || "").trim();
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_active_selection_class = String((restoredSelection && restoredSelection.className) || "steady").trim() || "steady";
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_active_selection_summary = String((restoredSelection && restoredSelection.summary) || "").trim();
        }}
        if (resumedReturnActive) {{
          const resumedTargetSelection = motionArtifactSnapshotReasonResumedReturnSelectionMeta("artifact", detail);
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_active_selection_label = String((resumedTargetSelection && resumedTargetSelection.label) || "").trim();
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_active_selection_class = String((resumedTargetSelection && resumedTargetSelection.className) || "steady").trim() || "steady";
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_active_selection_summary = String((resumedTargetSelection && resumedTargetSelection.summary) || "").trim();
        }}
        if (resumedReturnReturnActive) {{
          const resumedRestoredTargetSelection = motionArtifactSnapshotReasonResumedReturnReturnSelectionMeta("artifact", detail);
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_active_selection_label = String((resumedRestoredTargetSelection && resumedRestoredTargetSelection.label) || "").trim();
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_active_selection_class = String((resumedRestoredTargetSelection && resumedRestoredTargetSelection.className) || "steady").trim() || "steady";
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_active_selection_summary = String((resumedRestoredTargetSelection && resumedRestoredTargetSelection.summary) || "").trim();
        }}
        if (resumedReturnReturnReturnActive) {{
          const resumedRestoredFocusSelection = motionArtifactSnapshotReasonResumedReturnReturnReturnSelectionMeta("artifact", detail);
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_active_selection_label = String((resumedRestoredFocusSelection && resumedRestoredFocusSelection.label) || "").trim();
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_active_selection_class = String((resumedRestoredFocusSelection && resumedRestoredFocusSelection.className) || "steady").trim() || "steady";
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_active_selection_summary = String((resumedRestoredFocusSelection && resumedRestoredFocusSelection.summary) || "").trim();
        }}
        if (Boolean(String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_return_label) || "").trim())) {{
          const resumedRestoredFocusRestoredSelection = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnSelectionMeta("artifact", detail);
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_active_label = String((resumedRestoredFocusRestoredSelection && resumedRestoredFocusRestoredSelection.label) || "").trim();
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_active_class = String((resumedRestoredFocusRestoredSelection && resumedRestoredFocusRestoredSelection.className) || "steady").trim() || "steady";
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_active_summary = String((resumedRestoredFocusRestoredSelection && resumedRestoredFocusRestoredSelection.summary) || "").trim();
        }}
        if (resumedReturnReturnReturnReturnReturnActive) {{
          const confirmedResumedRestoredFocusSelection = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnSelectionMeta("artifact", detail);
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_active_label = String((confirmedResumedRestoredFocusSelection && confirmedResumedRestoredFocusSelection.label) || "").trim();
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_active_class = String((confirmedResumedRestoredFocusSelection && confirmedResumedRestoredFocusSelection.className) || "steady").trim() || "steady";
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_active_summary = String((confirmedResumedRestoredFocusSelection && confirmedResumedRestoredFocusSelection.summary) || "").trim();
        }}
        if (resumedReturnReturnReturnReturnReturnReturnActive) {{
          const reopenedConfirmedResumedRestoredFocusSelection = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnSelectionMeta("artifact", detail);
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_active_label = String((reopenedConfirmedResumedRestoredFocusSelection && reopenedConfirmedResumedRestoredFocusSelection.label) || "").trim();
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_active_class = String((reopenedConfirmedResumedRestoredFocusSelection && reopenedConfirmedResumedRestoredFocusSelection.className) || "steady").trim() || "steady";
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_active_summary = String((reopenedConfirmedResumedRestoredFocusSelection && reopenedConfirmedResumedRestoredFocusSelection.summary) || "").trim();
        }}
        if (resumedReturnReturnReturnReturnReturnReturnReturnActive) {{
          const reopenedReopenedConfirmedFocusSelection = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnSelectionMeta("artifact", detail);
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_active_label = String((reopenedReopenedConfirmedFocusSelection && reopenedReopenedConfirmedFocusSelection.label) || "").trim();
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_active_class = String((reopenedReopenedConfirmedFocusSelection && reopenedReopenedConfirmedFocusSelection.className) || "steady").trim() || "steady";
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_active_summary = String((reopenedReopenedConfirmedFocusSelection && reopenedReopenedConfirmedFocusSelection.summary) || "").trim();
        }}
        if (resumedReturnReturnReturnReturnReturnReturnReturnReturnActive) {{
          const reopenedReopenedConfirmedFocusRestored = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnMeta(
            detail,
            String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_return_return_return_return_active_label) || "").trim(),
          );
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_label = String((reopenedReopenedConfirmedFocusRestored && reopenedReopenedConfirmedFocusRestored.label) || "").trim();
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_class = String((reopenedReopenedConfirmedFocusRestored && reopenedReopenedConfirmedFocusRestored.className) || "steady").trim() || "steady";
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_summary = String((reopenedReopenedConfirmedFocusRestored && reopenedReopenedConfirmedFocusRestored.summary) || "").trim();
        }}
        if (resumedReturnReturnReturnReturnReturnReturnReturnReturnActiveSelection) {{
          const reopenedReopenedReopenedConfirmedFocusSelection = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnSelectionMeta("artifact", detail);
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_active_label = String((reopenedReopenedReopenedConfirmedFocusSelection && reopenedReopenedReopenedConfirmedFocusSelection.label) || "").trim();
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_active_class = String((reopenedReopenedReopenedConfirmedFocusSelection && reopenedReopenedReopenedConfirmedFocusSelection.className) || "steady").trim() || "steady";
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_active_summary = String((reopenedReopenedReopenedConfirmedFocusSelection && reopenedReopenedReopenedConfirmedFocusSelection.summary) || "").trim();
        }}
        if (Boolean(String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_label) || "").trim())) {{
          const reopenedReopenedReopenedReconfirmedFocusSelection = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnSelectionMeta("artifact", detail);
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_active_label = String((reopenedReopenedReopenedReconfirmedFocusSelection && reopenedReopenedReopenedReconfirmedFocusSelection.label) || "").trim();
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_active_class = String((reopenedReopenedReopenedReconfirmedFocusSelection && reopenedReopenedReopenedReconfirmedFocusSelection.className) || "steady").trim() || "steady";
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_active_summary = String((reopenedReopenedReopenedReconfirmedFocusSelection && reopenedReopenedReopenedReconfirmedFocusSelection.summary) || "").trim();
        }}
        if (resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnActive) {{
          const reopenedReopenedReopenedReopenedReconfirmedFocusSelection = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnSelectionMeta("artifact", detail);
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_active_label = String((reopenedReopenedReopenedReopenedReconfirmedFocusSelection && reopenedReopenedReopenedReopenedReconfirmedFocusSelection.label) || "").trim();
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_active_class = String((reopenedReopenedReopenedReopenedReconfirmedFocusSelection && reopenedReopenedReopenedReopenedReconfirmedFocusSelection.className) || "steady").trim() || "steady";
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_active_summary = String((reopenedReopenedReopenedReopenedReconfirmedFocusSelection && reopenedReopenedReopenedReopenedReconfirmedFocusSelection.summary) || "").trim();
        }}
        if (resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnActive) {{
          const reopenedReopenedReopenedReopenedReopenedReconfirmedFocusSelection = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnSelectionMeta("artifact", detail);
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_active_label = String((reopenedReopenedReopenedReopenedReopenedReconfirmedFocusSelection && reopenedReopenedReopenedReopenedReopenedReconfirmedFocusSelection.label) || "").trim();
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_active_class = String((reopenedReopenedReopenedReopenedReopenedReconfirmedFocusSelection && reopenedReopenedReopenedReopenedReopenedReconfirmedFocusSelection.className) || "steady").trim() || "steady";
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_active_summary = String((reopenedReopenedReopenedReopenedReopenedReconfirmedFocusSelection && reopenedReopenedReopenedReopenedReopenedReconfirmedFocusSelection.summary) || "").trim();
        }}
        if (resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnActive) {{
          const reopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnSelectionMeta("artifact", detail);
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_active_label = String((reopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection && reopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection.label) || "").trim();
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_active_class = String((reopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection && reopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection.className) || "steady").trim() || "steady";
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_active_summary = String((reopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection && reopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection.summary) || "").trim();
        }}
        if (resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnActive) {{
          const reopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnSelectionMeta("artifact", detail);
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_active_label = String((reopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection && reopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection.label) || "").trim();
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_active_class = String((reopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection && reopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection.className) || "steady").trim() || "steady";
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_active_summary = String((reopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection && reopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection.summary) || "").trim();
        }}
        if (resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnActive) {{
          const reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnSelectionMeta("artifact", detail);
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_label = String((reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection && reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection.label) || "").trim();
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_class = String((reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection && reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection.className) || "steady").trim() || "steady";
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_summary = String((reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection && reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection.summary) || "").trim();
        }}
        if (resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnActive) {{
          const reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnSelectionMeta("artifact", detail);
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_label = String((reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection && reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection.label) || "").trim();
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_class = String((reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection && reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection.className) || "steady").trim() || "steady";
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_summary = String((reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection && reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection.summary) || "").trim();
        }}
        if (resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnActive) {{
          const reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnSelectionMeta("artifact", detail);
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_label = String((reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection && reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection.label) || "").trim();
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_class = String((reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection && reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection.className) || "steady").trim() || "steady";
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_summary = String((reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection && reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection.summary) || "").trim();
        }}
        detail.motion_artifact_focus_posture_snapshot_reason_focus.context_selection_confirmation_label = "anchored artifact active";
        detail.motion_artifact_focus_posture_snapshot_reason_focus.context_selection_confirmation_class = "accepted";
      }}
      detail.change_summary = "Confirmed the reopened proof target artifact in the shared inspector.";
        detail.change_evidence_summary = String((detail.motion_artifact_focus_posture_snapshot_reason_focus || {{}}).active_target_label || "Confirmed the localized artifact target from the reopened proof pane.").trim();
        if (String(source || "").trim() === "round-trip-history-artifact") {{
          detail.motion_artifact_focus_history_note = `Round-trip reopen result: artifact lane active for ${{String((detail.motion_artifact_focus_posture_snapshot_reason_focus || {{}}).active_target_label || motionArtifactSnapshotRecordLabel(detail) || "the current localized record").trim()}}.`;
          detail.motion_artifact_focus_round_trip_history_index = Number.isInteger(Number(historyIndex)) ? Number(historyIndex) : null;
          stampMotionArtifactHistoryRevisit(detail, historyIndex, "artifact");
          applyMotionArtifactHistory(detail);
        }}
        return detail;
      }}

    function motionArtifactPriority(detail) {{
      const evidenceLines = detail && Array.isArray(detail.evidence_lines) ? detail.evidence_lines : [];
      const priorityLine = evidenceLines.find((item) => String(item || "").toLowerCase().includes("priority class:"));
      return priorityLine ? String(priorityLine).replace("Priority class:", "").trim() || "normal" : "normal";
    }}

    function motionArtifactDomainRows(before, after, context = null) {{
      const focusKind = motionArtifactFocusKind(after) || motionArtifactFocusKind(before);
      const result = context && typeof context === "object" ? Object.assign({{}}, context.result || {{}}) : {{}};
      const rows = [];
      const pushIfChanged = (label, left, right) => {{
        const beforeValue = String(left || "").trim();
        const afterValue = String(right || "").trim();
        if (beforeValue !== afterValue) {{
          rows.push({{ label, value: `${{beforeValue || "none"}} -> ${{afterValue || "none"}}` }});
        }}
      }};
      if (focusKind === "approval") {{
        pushIfChanged("Approval Status", before.status, after.status);
        pushIfChanged("Decision Record", before.last_decision_summary, after.last_decision_summary);
        pushIfChanged(
          "Decision Count",
          String(Array.isArray(before.decision_history) ? before.decision_history.length : 0),
          String(Array.isArray(after.decision_history) ? after.decision_history.length : 0),
        );
        pushIfChanged(
          "Review Detail",
          before && before.approval_review_context ? before.approval_review_context.description : "",
          after && after.approval_review_context ? after.approval_review_context.description : "",
        );
        const payloadResolution = String(result.resolution || result.outcome || "").trim();
        if (payloadResolution) rows.push({{ label: "Approval Outcome", value: payloadResolution }});
      }} else if (focusKind === "notification") {{
        pushIfChanged("Notification Status", before.status, after.status);
        pushIfChanged("Priority Class", motionArtifactPriority(before), motionArtifactPriority(after));
        pushIfChanged("Surfaced Reason", before.why_now, after.why_now);
        const payloadStatus = String(result.status || result.result || "").trim();
        if (payloadStatus) rows.push({{ label: "Notification Outcome", value: payloadStatus }});
      }} else if (focusKind === "open-loop") {{
        pushIfChanged("Workflow Status", before.status, after.status);
        pushIfChanged("Next Action", before.next_action, after.next_action);
        pushIfChanged("Next Review", before.next_review_at, after.next_review_at);
        pushIfChanged(
          "Timeline Depth",
          String(Array.isArray(before.item_timeline) ? before.item_timeline.length : 0),
          String(Array.isArray(after.item_timeline) ? after.item_timeline.length : 0),
        );
      }}
      return rows;
    }}

    function motionArtifactProofExcerpts(before, after, context = null) {{
      const focusKind = motionArtifactFocusKind(after) || motionArtifactFocusKind(before);
      const result = context && typeof context === "object" ? Object.assign({{}}, context.result || {{}}) : {{}};
      const errorText = String((context && context.error) || "").trim();
      const excerpts = [];
      if (errorText) excerpts.push(`Failure detail: ${{errorText}}`);
      if (focusKind === "approval") {{
        const latestDecision = Array.isArray(after.decision_history) && after.decision_history.length ? after.decision_history[0] : null;
        const payloadStatus = String(result.status || result.result || "").trim();
        const payloadResolution = String(result.resolution || result.outcome || "").trim();
        const payloadRequest = String(result.request_id || result.item_id || after.request_id || "").trim();
        const payloadDetail = String(result.detail || result.reason || result.message || "").trim();
        if (payloadStatus) excerpts.push(`Approval payload status: ${{payloadStatus}}`);
        if (payloadResolution) excerpts.push(`Approval payload resolution: ${{payloadResolution}}`);
        if (payloadRequest) excerpts.push(`Approval request: ${{payloadRequest}}`);
        if (payloadDetail) excerpts.push(`Approval detail: ${{payloadDetail}}`);
        if (latestDecision) excerpts.push(`Approval history: ${{latestDecision.status || "unknown"}} / ${{latestDecision.resolution || "unclassified"}} by ${{latestDecision.actor || "-"}} at ${{latestDecision.when || "unknown time"}}`);
      }} else if (focusKind === "notification") {{
        const payloadStatus = String(result.status || result.result || "").trim();
        const payloadItem = String(result.notification_id || result.item_id || after.notification_id || "").trim();
        const payloadActor = String(result.actor || "").trim();
        const payloadDetail = String(result.detail || result.reason || result.message || "").trim();
        if (payloadStatus) excerpts.push(`Notification payload status: ${{payloadStatus}}`);
        if (payloadItem) excerpts.push(`Notification item: ${{payloadItem}}`);
        if (payloadActor) excerpts.push(`Notification actor: ${{payloadActor}}`);
        if (payloadDetail) excerpts.push(`Notification detail: ${{payloadDetail}}`);
        excerpts.push(`Notification state: ${{String(after.status || "unknown").trim() || "unknown"}} / ${{motionArtifactPriority(after)}}`);
      }} else if (focusKind === "open-loop") {{
        const record = result && result.record && typeof result.record === "object" ? result.record : {{}};
        const nestedRecord = record && record.record && typeof record.record === "object" ? record.record : {{}};
        const recordStatus = String(record.status || record.result || record.resolution || nestedRecord.status || nestedRecord.result || nestedRecord.resolution || "").trim();
        const recordDetail = String(record.detail || record.reason || record.message || nestedRecord.detail || nestedRecord.reason || nestedRecord.message || "").trim();
        const actionName = String(result.action || "").trim();
        const itemId = String(result.item_id || after.item_id || "").trim();
        const domain = String(result.domain || after.domain || "").trim();
        const snapshotCount = Array.isArray(result && result.open_loops && result.open_loops.items) ? result.open_loops.items.length : 0;
        if (actionName) excerpts.push(`Open-loop action: ${{actionName}}`);
        if (itemId) excerpts.push(`Open-loop item: ${{itemId}}`);
        if (domain) excerpts.push(`Open-loop domain: ${{domain}}`);
        if (recordStatus) excerpts.push(`Open-loop record status: ${{recordStatus}}`);
        if (recordDetail) excerpts.push(`Open-loop record detail: ${{recordDetail}}`);
        if (snapshotCount) excerpts.push(`Open-loop snapshot count: ${{snapshotCount}}`);
      }}
      if (!excerpts.length) excerpts.push("No localized artifact proof excerpts captured yet.");
      return excerpts;
    }}

    function motionArtifactProofCompareRows(before, after, context = null) {{
      const focusKind = motionArtifactFocusKind(after) || motionArtifactFocusKind(before);
      const result = context && typeof context === "object" ? Object.assign({{}}, context.result || {{}}) : {{}};
      const rows = [];
      const pushProof = (label, left, right) => {{
        const beforeValue = String(left || "").trim();
        const afterValue = String(right || "").trim();
        if (!beforeValue && !afterValue) return;
        rows.push({{ label, value: `${{beforeValue || "none"}} -> ${{afterValue || "none"}}` }});
      }};
      if (focusKind === "approval") {{
        const beforeDecision = Array.isArray(before.decision_history) && before.decision_history.length ? before.decision_history[0] : null;
        const afterDecision = Array.isArray(after.decision_history) && after.decision_history.length ? after.decision_history[0] : null;
        pushProof(
          "Approval Payload Resolution",
          "",
          String(result.resolution || result.outcome || "").trim(),
        );
        pushProof(
          "Approval History Proof",
          beforeDecision ? `${{beforeDecision.status || "unknown"}} / ${{beforeDecision.resolution || "unclassified"}} by ${{beforeDecision.actor || "-"}} at ${{beforeDecision.when || "unknown time"}}` : "",
          afterDecision ? `${{afterDecision.status || "unknown"}} / ${{afterDecision.resolution || "unclassified"}} by ${{afterDecision.actor || "-"}} at ${{afterDecision.when || "unknown time"}}` : "",
        );
        pushProof(
          "Approval Detail Proof",
          before && before.approval_review_context ? before.approval_review_context.description : "",
          String(result.detail || result.reason || result.message || (after && after.approval_review_context ? after.approval_review_context.description : "") || "").trim(),
        );
      }} else if (focusKind === "notification") {{
        pushProof("Notification Payload Status", "", String(result.status || result.result || "").trim());
        pushProof(
          "Notification State Proof",
          `${{String(before.status || "").trim() || "unknown"}} / ${{motionArtifactPriority(before)}}`,
          `${{String(after.status || "").trim() || "unknown"}} / ${{motionArtifactPriority(after)}}`,
        );
        pushProof(
          "Notification Detail Proof",
          String(before.why_now || "").trim(),
          String(result.detail || result.reason || result.message || after.why_now || "").trim(),
        );
      }} else if (focusKind === "open-loop") {{
        const record = result && result.record && typeof result.record === "object" ? result.record : {{}};
        const nestedRecord = record && record.record && typeof record.record === "object" ? record.record : {{}};
        pushProof("Open-Loop Action Proof", "", String(result.action || "").trim());
        pushProof(
          "Open-Loop Record Status",
          String(before.status || "").trim(),
          String(record.status || record.result || record.resolution || nestedRecord.status || nestedRecord.result || nestedRecord.resolution || after.status || "").trim(),
        );
        pushProof(
          "Open-Loop Record Detail",
          String(before.next_action || "").trim(),
          String(record.detail || record.reason || record.message || nestedRecord.detail || nestedRecord.reason || nestedRecord.message || after.next_action || "").trim(),
        );
      }}
      if (!rows.length) rows.push({{ label: "Artifact Proof Compare", value: "No localized artifact proof comparison captured yet." }});
      return rows;
    }}

    function motionArtifactProofCompareSummary(before, after, context = null) {{
      const rows = motionArtifactProofCompareRows(before, after, context);
      if (rows.length === 1 && String((rows[0] && rows[0].label) || "").trim() === "Artifact Proof Compare") {{
        return String(rows[0].value || "No localized artifact proof comparison captured yet.");
      }}
      return rows.map((item) => `${{item.label || "Proof"}}: ${{item.value || ""}}`).join("; ");
    }}

    function motionArtifactHistoryKey(detail) {{
      const kind = motionArtifactFocusKind(detail);
      if (kind === "approval") {{
        const requestId = String((detail && ((detail.approval_review_context || {{}}).request_id || detail.request_id || detail.item_id)) || "").trim();
        return requestId ? `approval:${{requestId}}` : "";
      }}
      if (kind === "notification") {{
        const notificationId = String((detail && detail.notification_id) || "").trim();
        return notificationId ? `notification:${{notificationId}}` : "";
      }}
      if (kind === "open-loop") {{
        const domain = String((detail && detail.domain) || "").trim();
        const itemId = String((detail && detail.item_id) || "").trim();
        return domain && itemId ? `open-loop:${{domain}}:${{itemId}}` : "";
      }}
      return "";
    }}

    function motionArtifactHistoryRows(detail) {{
      const artifactKey = motionArtifactHistoryKey(detail);
      if (!artifactKey) return [];
      const entries = (Array.isArray(recentMotionArtifactActions) ? recentMotionArtifactActions : [])
        .filter((item) => String((item && item.artifact_key) || "").trim() === artifactKey)
        .slice(0, 2);
      return entries.map((item, index) => {{
        const previous = entries[index + 1] || null;
        const actionKind = String((item && item.action_kind) || "artifact").trim().toLowerCase() || "artifact";
        const currentOutcome = String((item && item.outcome) || "").trim().toLowerCase();
        const previousOutcome = String((previous && previous.outcome) || "").trim().toLowerCase();
        const currentDetail = String((item && item.detail) || "").trim().toLowerCase();
        const previousDetail = String((previous && previous.detail) || "").trim().toLowerCase();
        let trend = "first seen";
        if (previous) {{
          if (currentOutcome === "failed" && previousOutcome !== "failed") {{
            trend = actionKind === "approval" ? "approval regressed" : actionKind === "notification" ? "inbox regressed" : actionKind === "open-loop" ? "workflow regressed" : "regressed";
          }} else if (currentOutcome !== "failed" && previousOutcome === "failed") {{
            trend = actionKind === "approval" ? "approval recovered" : actionKind === "notification" ? "inbox recovered" : actionKind === "open-loop" ? "workflow recovered" : "recovered";
          }} else if (currentOutcome === previousOutcome && currentDetail === previousDetail) {{
            trend = actionKind === "approval" ? "approval steady" : actionKind === "notification" ? "inbox steady" : actionKind === "open-loop" ? "workflow steady" : "steady";
          }} else {{
            trend = actionKind === "approval" ? "approval shifted" : actionKind === "notification" ? "inbox shifted" : actionKind === "open-loop" ? "workflow shifted" : "shifted";
          }}
        }} else {{
          trend = actionKind === "approval" ? "approval first seen" : actionKind === "notification" ? "inbox first seen" : actionKind === "open-loop" ? "workflow first seen" : "first seen";
        }}
        return {{
          label: index === 0 ? "Most Recent" : "Previous",
          timestamp: String(item.timestamp || "recent").trim(),
          badge: `${{String(item.action_kind || "artifact").trim() || "artifact"}} / ${{String(item.outcome || "updated").trim() || "updated"}}`,
          badge_class: actionKind || "artifact",
          trend_class: trend.includes("recovered")
            ? "recovered"
            : trend.includes("regressed")
              ? "regressed"
              : trend.includes("shifted")
                ? "shifted"
                : trend.includes("first seen")
                  ? "first-seen"
                  : "steady",
          trend,
          value: `${{String(item.timestamp || "recent").trim()}} · ${{String(item.action_label || "Action").trim()}} · ${{String(item.outcome || "updated").trim()}} · ${{String(item.detail || "No detail captured.").trim()}}`,
          jumpable: true,
          history_buttons: Array.isArray(item.history_buttons) ? item.history_buttons.slice(0, 2) : [],
          last_revisited_lane_label: String(item.last_revisited_lane_label || "").trim(),
          last_revisited_lane_class: String(item.last_revisited_lane_class || "steady").trim() || "steady",
          last_revisited_lane_summary: String(item.last_revisited_lane_summary || "").trim(),
        }};
      }});
    }}

    function stampMotionArtifactHistoryRevisit(detail, historyIndex, laneKind) {{
      const artifactKey = motionArtifactHistoryKey(detail);
      const normalizedIndex = Number(historyIndex);
      if (!artifactKey || !Number.isInteger(normalizedIndex)) return;
      const laneLabel = laneKind === "timeline" ? "timeline lane revisited" : "artifact lane revisited";
      const laneSummary = laneKind === "timeline"
        ? `Last revisited lane: timeline lane reopened for ${{String((detail.motion_artifact_focus_posture_snapshot_reason_focus || {{}}).active_target_label || motionArtifactSnapshotRecordLabel(detail) || "the current localized record").trim()}}.`
        : `Last revisited lane: artifact lane reopened for ${{String((detail.motion_artifact_focus_posture_snapshot_reason_focus || {{}}).active_target_label || motionArtifactSnapshotRecordLabel(detail) || "the current localized record").trim()}}.`;
      recentMotionArtifactActions = (Array.isArray(recentMotionArtifactActions) ? recentMotionArtifactActions : []).map((item) => {{
        if (String((item && item.artifact_key) || "").trim() !== artifactKey) return item;
        const sameEntry = ((Array.isArray(recentMotionArtifactActions) ? recentMotionArtifactActions : []).filter((candidate) => String((candidate && candidate.artifact_key) || "").trim() === artifactKey).slice(0, 2))[normalizedIndex];
        if (!sameEntry || String((item && item.timestamp) || "").trim() !== String((sameEntry && sameEntry.timestamp) || "").trim()) return item;
        return Object.assign({{}}, item, {{
          last_revisited_lane_label: laneLabel,
          last_revisited_lane_class: "accepted",
          last_revisited_lane_summary: laneSummary,
        }});
      }});
    }}

    function applyMotionArtifactHistory(detail) {{
      const rows = motionArtifactHistoryRows(detail);
      const latestRow = rows[0] || null;
      const counts = rows.reduce((acc, item) => {{
        const badgeClass = String((item && item.badge_class) || "artifact").trim() || "artifact";
        acc[badgeClass] = Number(acc[badgeClass] || 0) + 1;
        return acc;
      }}, {{}});
      const countSummary = Object.entries(counts).map(([key, value]) => `${{value}} ${{key}}`).join(" · ");
      const summaryDomain = String((((rows[0] || {{}}).badge_class) || "artifact")).trim() || "artifact";
      const comparisonHint = !rows.length
        ? ""
        : !rows[1]
          ? (summaryDomain === "approval"
              ? "No previous approval snapshot yet."
              : summaryDomain === "notification"
                ? "No previous inbox snapshot yet."
                : summaryDomain === "open-loop"
                  ? "No previous workflow snapshot yet."
                  : "No previous localized action snapshot yet.")
          : (String((rows[0] && rows[0].trend) || "").includes("steady")
              ? (summaryDomain === "approval"
                  ? "Same approval snapshot as previous."
                  : summaryDomain === "notification"
                    ? "Same inbox snapshot as previous."
                    : summaryDomain === "open-loop"
                      ? "Same workflow snapshot as previous."
                      : "Same as previous localized snapshot.")
              : (summaryDomain === "approval"
                  ? "Approval snapshot changed since previous."
                  : summaryDomain === "notification"
                    ? "Inbox snapshot changed since previous."
                    : summaryDomain === "open-loop"
                      ? "Workflow snapshot changed since previous."
                      : "Changed since previous localized snapshot."));
      detail.motion_artifact_focus_history_rows = rows;
      detail.motion_artifact_focus_history_summary = rows.length
        ? `Showing ${{rows.length}} recent localized action result${{rows.length === 1 ? "" : "s"}} for this exact record${{rows[0] && rows[0].trend ? `; latest trend: ${{rows[0].trend}}` : ""}}.`
        : "No localized artifact action history captured yet.";
      detail.motion_artifact_focus_history_meta = rows.length ? `Recent outcome mix: ${{countSummary}}. ${{comparisonHint}}` : "";
      detail.motion_artifact_focus_history_note = "";
      const postureBadge = motionArtifactPostureBadge(detail);
      const postureStateBadge = motionArtifactPostureStateBadge(detail);
      detail.motion_artifact_focus_posture_summary = motionArtifactPostureSummary(detail);
      detail.motion_artifact_focus_posture_badge_label = String((postureBadge && postureBadge.label) || "artifact posture").trim() || "artifact posture";
      detail.motion_artifact_focus_posture_badge_class = String((postureBadge && postureBadge.className) || "artifact").trim() || "artifact";
      detail.motion_artifact_focus_posture_state_label = String((postureStateBadge && postureStateBadge.label) || "steady").trim() || "steady";
      detail.motion_artifact_focus_posture_state_class = String((postureStateBadge && postureStateBadge.className) || "steady").trim() || "steady";
      detail.motion_artifact_focus_posture_hint = motionArtifactPostureHint(detail);
      detail.motion_artifact_focus_posture_outcome_line = latestRow
        ? `Last localized action: ${{String(latestRow.badge || "artifact / updated").trim()}} at ${{String(latestRow.timestamp || "recent").trim()}}.`
        : "No localized artifact action outcome captured yet.";
      detail.motion_artifact_focus_posture_outcome_index = latestRow ? 0 : null;
      detail.motion_artifact_focus_posture_snapshot_cue = "";
      detail.motion_artifact_focus_posture_suggested_action = motionArtifactPostureSuggestedAction(detail);
      detail.motion_artifact_focus_posture_snapshot_action = null;
      detail.motion_artifact_focus_posture_snapshot_reason = "";
      detail.motion_artifact_focus_posture_snapshot_reason_target = null;
      detail.motion_artifact_focus_posture_snapshot_reason_focus = null;
      return detail;
    }}

    function recordMotionArtifactHistory(detail, context = null) {{
      const artifactKey = motionArtifactHistoryKey(detail);
      if (!artifactKey) return [];
      const result = context && typeof context === "object" ? Object.assign({{}}, context.result || {{}}) : {{}};
      const errorText = String((context && context.error) || "").trim();
      const actionKind = motionArtifactFocusKind(detail) || "artifact";
      const entry = {{
        artifact_key: artifactKey,
        timestamp: new Date().toISOString(),
        action_kind: actionKind,
        action_label: String((context && context.actionLabel) || "Artifact action").trim(),
        outcome: errorText
          ? "failed"
          : String(result.status || result.result || result.resolution || result.outcome || "updated").trim(),
        detail: errorText
          ? `Action failed before refresh: ${{errorText}}`
          : String(result.detail || result.reason || result.message || detail.change_evidence_summary || "Artifact action updated the focused record.").trim(),
        action_result_summary: String(detail.action_result_summary || actionResultSummary(context || {{}})).trim(),
        change_evidence_summary: String(detail.change_evidence_summary || "").trim(),
        timeline_event_index: Number.isInteger(currentTimelineEventIndex) ? currentTimelineEventIndex : null,
        timeline_event_title: String((((detail || {{}}).selected_timeline_event || {{}}).title || "").trim(),
        motion_artifact_focus_excerpts: Array.isArray(detail.motion_artifact_focus_excerpts) ? detail.motion_artifact_focus_excerpts.slice(0, 8) : [],
        motion_artifact_focus_proof_compare_summary: String(detail.motion_artifact_focus_proof_compare_summary || "").trim(),
        motion_artifact_focus_proof_compare_rows: Array.isArray(detail.motion_artifact_focus_proof_compare_rows) ? detail.motion_artifact_focus_proof_compare_rows.slice(0, 8) : [],
        history_buttons: Array.isArray((context && context.historyButtons)) ? context.historyButtons.slice(0, 2) : [],
      }};
      recentMotionArtifactActions = [
        entry,
        ...(Array.isArray(recentMotionArtifactActions) ? recentMotionArtifactActions : []).filter((item) => String((item && item.artifact_key) || "").trim() !== artifactKey || String((item && item.timestamp) || "").trim() !== entry.timestamp),
      ].slice(0, 8);
      return motionArtifactHistoryRows(detail);
    }}

    function jumpToMotionArtifactHistory(index) {{
      const detail = Number.isInteger(currentMotionArtifactIndex) ? jumpToMotionArtifact(currentMotionArtifactIndex) : selectedDetail();
      const artifactKey = motionArtifactHistoryKey(detail);
      if (!artifactKey) return detail;
      const entries = (Array.isArray(recentMotionArtifactActions) ? recentMotionArtifactActions : [])
        .filter((item) => String((item && item.artifact_key) || "").trim() === artifactKey)
        .slice(0, 2);
      const entry = entries[Number(index)] || null;
      if (!entry) return detail;
      currentTimelineEventIndex = Number.isInteger(entry.timeline_event_index) ? entry.timeline_event_index : currentTimelineEventIndex;
      detail.motion_artifact_focus_excerpts = Array.isArray(entry.motion_artifact_focus_excerpts) ? entry.motion_artifact_focus_excerpts.slice(0, 8) : [];
      detail.motion_artifact_focus_proof_compare_summary = String(entry.motion_artifact_focus_proof_compare_summary || detail.motion_artifact_focus_proof_compare_summary || "").trim() || "No localized artifact proof comparison captured yet.";
      detail.motion_artifact_focus_proof_compare_rows = Array.isArray(entry.motion_artifact_focus_proof_compare_rows) ? entry.motion_artifact_focus_proof_compare_rows.slice(0, 8) : [];
      applyMotionArtifactHistory(detail);
      detail.motion_artifact_focus_history_note = `Focused localized action snapshot from ${{String(entry.timestamp || "recent history").trim()}}${{String(entry.timeline_event_title || "").trim() ? ` for timeline event ${{String(entry.timeline_event_title || "").trim()}}` : ""}}.`;
      detail.motion_artifact_focus_round_trip_history_index = null;
      if (String(entry.last_revisited_lane_summary || "").trim()) {{
        detail.motion_artifact_focus_history_note += ` ${{String(entry.last_revisited_lane_summary || "").trim()}}`;
      }}
      const focusKind = motionArtifactFocusKind(detail);
      const outcomeLabel = String(entry.outcome || "").trim().toLowerCase();
      const cueEvidence = String(entry.motion_artifact_focus_proof_compare_summary || entry.change_evidence_summary || "").trim();
      detail.motion_artifact_focus_posture_snapshot_cue = outcomeLabel === "failed"
        ? (focusKind === "approval"
            ? `Reopened approval failure cue: ${{String(entry.badge || "approval / failed").trim()}}. ${{cueEvidence || "Inspect the localized approval proof comparison for the exact failure context."}}`
            : focusKind === "notification"
              ? `Reopened inbox failure cue: ${{String(entry.badge || "notification / failed").trim()}}. ${{cueEvidence || "Inspect the localized notification proof comparison for the exact failure context."}}`
              : focusKind === "open-loop"
                ? `Reopened workflow failure cue: ${{String(entry.badge || "open-loop / failed").trim()}}. ${{cueEvidence || "Inspect the localized workflow proof comparison for the exact failure context."}}`
                : `Reopened failure cue: ${{String(entry.badge || "artifact / failed").trim()}}. ${{cueEvidence || "Inspect the localized proof comparison for the exact failure context."}}`)
        : (focusKind === "approval"
            ? `Reopened approval outcome cue: ${{String(entry.badge || "approval / updated").trim()}}. ${{cueEvidence || "Inspect the localized approval proof comparison for the exact returned delta."}}`
            : focusKind === "notification"
              ? `Reopened inbox outcome cue: ${{String(entry.badge || "notification / updated").trim()}}. ${{cueEvidence || "Inspect the localized notification proof comparison for the exact returned delta."}}`
              : focusKind === "open-loop"
                ? `Reopened workflow outcome cue: ${{String(entry.badge || "open-loop / updated").trim()}}. ${{cueEvidence || "Inspect the localized workflow proof comparison for the exact returned delta."}}`
                : `Reopened outcome cue: ${{String(entry.badge || "artifact / updated").trim()}}. ${{cueEvidence || "Inspect the localized proof comparison for the exact returned delta."}}`);
      detail.motion_artifact_focus_posture_snapshot_action = motionArtifactSnapshotSuggestedAction(detail, entry);
      detail.motion_artifact_focus_posture_snapshot_reason = motionArtifactSnapshotActionReason(detail, entry);
      detail.motion_artifact_focus_posture_snapshot_reason_target = motionArtifactSnapshotReasonTarget(detail, Object.assign({{}}, entry, {{ history_index: Number(index) || 0 }}));
      applyMotionArtifactSnapshotPath(detail, "mutation");
      detail.action_result_summary = String(entry.action_result_summary || detail.action_result_summary || "No action result captured yet.").trim();
      detail.change_evidence_summary = String(entry.change_evidence_summary || detail.change_evidence_summary || "No post-action evidence captured yet.").trim();
      detail.change_summary = "Focused a recent localized artifact action from the in-pane history strip.";
      return detail;
    }}

    function jumpToMotionArtifactSnapshotTimeline(index) {{
      const currentDetail = Number.isInteger(currentMotionArtifactIndex) ? jumpToMotionArtifact(currentMotionArtifactIndex) : selectedDetail();
      const reasonTarget = currentDetail && currentDetail.motion_artifact_focus_posture_snapshot_reason_target && typeof currentDetail.motion_artifact_focus_posture_snapshot_reason_target === "object"
        ? Object.assign({{}}, currentDetail.motion_artifact_focus_posture_snapshot_reason_target)
        : null;
      const reasonText = String((currentDetail && currentDetail.motion_artifact_focus_posture_snapshot_reason) || "").trim();
      const snapshotAction = currentDetail && currentDetail.motion_artifact_focus_posture_snapshot_action && typeof currentDetail.motion_artifact_focus_posture_snapshot_action === "object"
        ? Object.assign({{}}, currentDetail.motion_artifact_focus_posture_snapshot_action)
        : null;
      currentTimelineEventIndex = Number(index) || 0;
      const detail = Number.isInteger(currentMotionArtifactIndex) ? jumpToMotionArtifact(currentMotionArtifactIndex) : selectedDetail();
      detail.motion_artifact_focus_posture_snapshot_reason = reasonText;
      detail.motion_artifact_focus_posture_snapshot_action = snapshotAction;
      detail.motion_artifact_focus_posture_snapshot_reason_target = reasonTarget;
      applyMotionArtifactSnapshotPath(detail, "chronology");
      detail.change_summary = "Focused reopened proof chronology from the proof pivot strip.";
      return detail;
    }}

    function jumpToMotionArtifactSnapshotTargetTimeline(index, source = "", historyIndex = null) {{
      const currentDetail = selectedDetail();
      const currentFocus = currentDetail && currentDetail.motion_artifact_focus_posture_snapshot_reason_focus && typeof currentDetail.motion_artifact_focus_posture_snapshot_reason_focus === "object"
        ? currentDetail.motion_artifact_focus_posture_snapshot_reason_focus
        : null;
      const restoredActive = Boolean(String((currentFocus && currentFocus.return_history_reason_resumed_active_label) || "").trim());
      const resumedReturnActive = Boolean(String((currentFocus && currentFocus.return_history_reason_resumed_return_active_label) || "").trim());
      const resumedReturnReturnActive = Boolean(String((currentFocus && currentFocus.return_history_reason_resumed_return_return_active_label) || "").trim());
      const resumedReturnReturnReturnActive = Boolean(String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_active_label) || "").trim());
      const resumedReturnReturnReturnReturnReturnActive = Boolean(String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_return_return_label) || "").trim());
      const resumedReturnReturnReturnReturnReturnReturnActive = Boolean(String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_return_return_return_label) || "").trim());
      const resumedReturnReturnReturnReturnReturnReturnReturnActive = Boolean(String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_return_return_return_return_label) || "").trim());
      const resumedReturnReturnReturnReturnReturnReturnReturnReturnActive = Boolean(String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_return_return_return_return_return_label) || "").trim());
      const resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnActive = Boolean(String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_label) || "").trim());
      const resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnActive = Boolean(String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_label) || "").trim());
      const resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnActive = Boolean(String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_label) || "").trim());
      const resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnActive = Boolean(String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_label) || "").trim());
      const resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnActive = Boolean(String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_label) || "").trim());
      const resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnActive = Boolean(String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_label) || "").trim());
      const reasonTarget = currentDetail && currentDetail.motion_artifact_focus_posture_snapshot_reason_target && typeof currentDetail.motion_artifact_focus_posture_snapshot_reason_target === "object"
        ? Object.assign({{}}, currentDetail.motion_artifact_focus_posture_snapshot_reason_target)
        : null;
      const reasonText = String((currentDetail && currentDetail.motion_artifact_focus_posture_snapshot_reason) || "").trim();
      const snapshotAction = currentDetail && currentDetail.motion_artifact_focus_posture_snapshot_action && typeof currentDetail.motion_artifact_focus_posture_snapshot_action === "object"
        ? Object.assign({{}}, currentDetail.motion_artifact_focus_posture_snapshot_action)
        : null;
      currentTimelineEventIndex = Number(index) || 0;
      const detail = Number.isInteger(currentMotionArtifactIndex) ? jumpToMotionArtifact(currentMotionArtifactIndex) : selectedDetail();
      detail.motion_artifact_focus_posture_snapshot_reason = reasonText;
      detail.motion_artifact_focus_posture_snapshot_action = snapshotAction;
      detail.motion_artifact_focus_posture_snapshot_reason_target = reasonTarget;
      applyMotionArtifactSnapshotPath(detail, "chronology");
      if (detail.motion_artifact_focus_posture_snapshot_reason_focus && typeof detail.motion_artifact_focus_posture_snapshot_reason_focus === "object") {{
        const evidenceSelection = motionArtifactSnapshotReasonSelectionMeta("timeline", detail);
        detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_active_selection_label = String((evidenceSelection && evidenceSelection.label) || "").trim();
        detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_active_selection_class = String((evidenceSelection && evidenceSelection.className) || "steady").trim() || "steady";
        detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_active_selection_summary = String((evidenceSelection && evidenceSelection.summary) || "").trim();
        if (restoredActive) {{
          const restoredSelection = motionArtifactSnapshotReasonResumedSelectionMeta("timeline", detail);
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_active_selection_label = String((restoredSelection && restoredSelection.label) || "").trim();
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_active_selection_class = String((restoredSelection && restoredSelection.className) || "steady").trim() || "steady";
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_active_selection_summary = String((restoredSelection && restoredSelection.summary) || "").trim();
        }}
        if (resumedReturnActive) {{
          const resumedTargetSelection = motionArtifactSnapshotReasonResumedReturnSelectionMeta("timeline", detail);
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_active_selection_label = String((resumedTargetSelection && resumedTargetSelection.label) || "").trim();
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_active_selection_class = String((resumedTargetSelection && resumedTargetSelection.className) || "steady").trim() || "steady";
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_active_selection_summary = String((resumedTargetSelection && resumedTargetSelection.summary) || "").trim();
        }}
        if (resumedReturnReturnActive) {{
          const resumedRestoredTargetSelection = motionArtifactSnapshotReasonResumedReturnReturnSelectionMeta("timeline", detail);
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_active_selection_label = String((resumedRestoredTargetSelection && resumedRestoredTargetSelection.label) || "").trim();
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_active_selection_class = String((resumedRestoredTargetSelection && resumedRestoredTargetSelection.className) || "steady").trim() || "steady";
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_active_selection_summary = String((resumedRestoredTargetSelection && resumedRestoredTargetSelection.summary) || "").trim();
        }}
        if (resumedReturnReturnReturnActive) {{
          const resumedRestoredFocusSelection = motionArtifactSnapshotReasonResumedReturnReturnReturnSelectionMeta("timeline", detail);
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_active_selection_label = String((resumedRestoredFocusSelection && resumedRestoredFocusSelection.label) || "").trim();
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_active_selection_class = String((resumedRestoredFocusSelection && resumedRestoredFocusSelection.className) || "steady").trim() || "steady";
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_active_selection_summary = String((resumedRestoredFocusSelection && resumedRestoredFocusSelection.summary) || "").trim();
        }}
        if (Boolean(String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_return_label) || "").trim())) {{
          const resumedRestoredFocusRestoredSelection = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnSelectionMeta("timeline", detail);
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_active_label = String((resumedRestoredFocusRestoredSelection && resumedRestoredFocusRestoredSelection.label) || "").trim();
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_active_class = String((resumedRestoredFocusRestoredSelection && resumedRestoredFocusRestoredSelection.className) || "steady").trim() || "steady";
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_active_summary = String((resumedRestoredFocusRestoredSelection && resumedRestoredFocusRestoredSelection.summary) || "").trim();
        }}
        if (resumedReturnReturnReturnReturnReturnActive) {{
          const confirmedResumedRestoredFocusSelection = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnSelectionMeta("timeline", detail);
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_active_label = String((confirmedResumedRestoredFocusSelection && confirmedResumedRestoredFocusSelection.label) || "").trim();
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_active_class = String((confirmedResumedRestoredFocusSelection && confirmedResumedRestoredFocusSelection.className) || "steady").trim() || "steady";
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_active_summary = String((confirmedResumedRestoredFocusSelection && confirmedResumedRestoredFocusSelection.summary) || "").trim();
        }}
        if (resumedReturnReturnReturnReturnReturnReturnActive) {{
          const reopenedConfirmedResumedRestoredFocusSelection = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnSelectionMeta("timeline", detail);
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_active_label = String((reopenedConfirmedResumedRestoredFocusSelection && reopenedConfirmedResumedRestoredFocusSelection.label) || "").trim();
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_active_class = String((reopenedConfirmedResumedRestoredFocusSelection && reopenedConfirmedResumedRestoredFocusSelection.className) || "steady").trim() || "steady";
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_active_summary = String((reopenedConfirmedResumedRestoredFocusSelection && reopenedConfirmedResumedRestoredFocusSelection.summary) || "").trim();
        }}
        if (resumedReturnReturnReturnReturnReturnReturnReturnActive) {{
          const reopenedReopenedConfirmedFocusSelection = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnSelectionMeta("timeline", detail);
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_active_label = String((reopenedReopenedConfirmedFocusSelection && reopenedReopenedConfirmedFocusSelection.label) || "").trim();
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_active_class = String((reopenedReopenedConfirmedFocusSelection && reopenedReopenedConfirmedFocusSelection.className) || "steady").trim() || "steady";
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_active_summary = String((reopenedReopenedConfirmedFocusSelection && reopenedReopenedConfirmedFocusSelection.summary) || "").trim();
        }}
        if (resumedReturnReturnReturnReturnReturnReturnReturnReturnActive) {{
          const reopenedReopenedConfirmedFocusRestored = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnMeta(
            detail,
            String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_return_return_return_return_active_label) || "").trim(),
          );
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_label = String((reopenedReopenedConfirmedFocusRestored && reopenedReopenedConfirmedFocusRestored.label) || "").trim();
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_class = String((reopenedReopenedConfirmedFocusRestored && reopenedReopenedConfirmedFocusRestored.className) || "steady").trim() || "steady";
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_summary = String((reopenedReopenedConfirmedFocusRestored && reopenedReopenedConfirmedFocusRestored.summary) || "").trim();
        }}
        if (resumedReturnReturnReturnReturnReturnReturnReturnReturnActive) {{
          const reopenedReopenedReopenedConfirmedFocusSelection = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnSelectionMeta("timeline", detail);
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_active_label = String((reopenedReopenedReopenedConfirmedFocusSelection && reopenedReopenedReopenedConfirmedFocusSelection.label) || "").trim();
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_active_class = String((reopenedReopenedReopenedConfirmedFocusSelection && reopenedReopenedReopenedConfirmedFocusSelection.className) || "steady").trim() || "steady";
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_active_summary = String((reopenedReopenedReopenedConfirmedFocusSelection && reopenedReopenedReopenedConfirmedFocusSelection.summary) || "").trim();
        }}
        if (Boolean(String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_label) || "").trim())) {{
          const reopenedReopenedReopenedReconfirmedFocusSelection = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnSelectionMeta("timeline", detail);
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_active_label = String((reopenedReopenedReopenedReconfirmedFocusSelection && reopenedReopenedReopenedReconfirmedFocusSelection.label) || "").trim();
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_active_class = String((reopenedReopenedReopenedReconfirmedFocusSelection && reopenedReopenedReopenedReconfirmedFocusSelection.className) || "steady").trim() || "steady";
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_active_summary = String((reopenedReopenedReopenedReconfirmedFocusSelection && reopenedReopenedReopenedReconfirmedFocusSelection.summary) || "").trim();
        }}
        if (resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnActive) {{
          const reopenedReopenedReopenedReopenedReconfirmedFocusSelection = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnSelectionMeta("timeline", detail);
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_active_label = String((reopenedReopenedReopenedReopenedReconfirmedFocusSelection && reopenedReopenedReopenedReopenedReconfirmedFocusSelection.label) || "").trim();
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_active_class = String((reopenedReopenedReopenedReopenedReconfirmedFocusSelection && reopenedReopenedReopenedReopenedReconfirmedFocusSelection.className) || "steady").trim() || "steady";
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_active_summary = String((reopenedReopenedReopenedReopenedReconfirmedFocusSelection && reopenedReopenedReopenedReopenedReconfirmedFocusSelection.summary) || "").trim();
        }}
        if (resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnActive) {{
          const reopenedReopenedReopenedReopenedReopenedReconfirmedFocusSelection = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnSelectionMeta("timeline", detail);
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_active_label = String((reopenedReopenedReopenedReopenedReopenedReconfirmedFocusSelection && reopenedReopenedReopenedReopenedReopenedReconfirmedFocusSelection.label) || "").trim();
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_active_class = String((reopenedReopenedReopenedReopenedReopenedReconfirmedFocusSelection && reopenedReopenedReopenedReopenedReopenedReconfirmedFocusSelection.className) || "steady").trim() || "steady";
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_active_summary = String((reopenedReopenedReopenedReopenedReopenedReconfirmedFocusSelection && reopenedReopenedReopenedReopenedReopenedReconfirmedFocusSelection.summary) || "").trim();
        }}
        if (resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnActive) {{
          const reopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnSelectionMeta("timeline", detail);
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_active_label = String((reopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection && reopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection.label) || "").trim();
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_active_class = String((reopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection && reopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection.className) || "steady").trim() || "steady";
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_active_summary = String((reopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection && reopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection.summary) || "").trim();
        }}
        if (resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnActive) {{
          const reopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnSelectionMeta("timeline", detail);
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_active_label = String((reopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection && reopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection.label) || "").trim();
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_active_class = String((reopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection && reopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection.className) || "steady").trim() || "steady";
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_active_summary = String((reopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection && reopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection.summary) || "").trim();
        }}
        if (resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnActive) {{
          const reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnSelectionMeta("timeline", detail);
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_label = String((reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection && reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection.label) || "").trim();
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_class = String((reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection && reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection.className) || "steady").trim() || "steady";
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_summary = String((reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection && reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection.summary) || "").trim();
        }}
        if (resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnActive) {{
          const reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnSelectionMeta("timeline", detail);
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_label = String((reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection && reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection.label) || "").trim();
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_class = String((reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection && reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection.className) || "steady").trim() || "steady";
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_summary = String((reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection && reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection.summary) || "").trim();
        }}
        if (resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnActive) {{
          const reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnSelectionMeta("timeline", detail);
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_label = String((reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection && reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection.label) || "").trim();
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_class = String((reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection && reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection.className) || "steady").trim() || "steady";
          detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_summary = String((reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection && reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection.summary) || "").trim();
        }}
        detail.motion_artifact_focus_posture_snapshot_reason_focus.context_selection_confirmation_label = "anchored timeline active";
        detail.motion_artifact_focus_posture_snapshot_reason_focus.context_selection_confirmation_class = "accepted";
      }}
      detail.change_summary = "Confirmed the reopened proof target timeline in the shared inspector.";
        detail.change_evidence_summary = String((detail.motion_artifact_focus_posture_snapshot_reason_focus || {{}}).active_target_label || "Confirmed the matching timeline target from the reopened proof pane.").trim();
        if (String(source || "").trim() === "round-trip-history-timeline") {{
          detail.motion_artifact_focus_history_note = `Round-trip reopen result: timeline lane active for ${{String((detail.motion_artifact_focus_posture_snapshot_reason_focus || {{}}).active_target_label || motionArtifactSnapshotRecordLabel(detail) || "the current localized record").trim()}}.`;
          detail.motion_artifact_focus_round_trip_history_index = Number.isInteger(Number(historyIndex)) ? Number(historyIndex) : null;
          stampMotionArtifactHistoryRevisit(detail, historyIndex, "timeline");
          applyMotionArtifactHistory(detail);
        }}
        return detail;
      }}

    function motionArtifactDeltaSections(before, after, context = null) {{
      const beforeMap = motionArtifactFocusValueMap(before);
      const afterMap = motionArtifactFocusValueMap(after);
      const rows = motionArtifactDomainRows(before, after, context);
      const labels = Array.from(new Set([...Object.keys(beforeMap), ...Object.keys(afterMap)]));
      const genericRows = labels.reduce((acc, label) => {{
        const left = String(beforeMap[label] || "").trim();
        const right = String(afterMap[label] || "").trim();
        if (left !== right) {{
          acc.push({{ label, value: `${{left || "none"}} -> ${{right || "none"}}` }});
        }}
        return acc;
      }}, []);
      genericRows.forEach((item) => {{
        const label = String((item && item.label) || "").trim();
        if (!label || rows.some((existing) => String((existing && existing.label) || "").trim() === label)) return;
        rows.push(item);
      }});
      const result = context && typeof context === "object" ? Object.assign({{}}, context.result || {{}}) : {{}};
      const actionLabel = String((context && context.actionLabel) || "").trim();
      const errorText = String((context && context.error) || "").trim();
      if (actionLabel) {{
        rows.unshift({{ label: "Action Trigger", value: actionLabel }});
      }}
      if (errorText) {{
        rows.push({{ label: "Mutation Status", value: `Action failed before localized mutation completed: ${{errorText}}` }});
      }} else if (rows.length && Object.keys(result).length) {{
        rows.push({{ label: "Mutation Status", value: "Localized artifact focus refreshed after the action result returned." }});
      }}
      if (!rows.length) {{
        rows.push({{ label: "Artifact Mutation", value: "No localized artifact field changes captured yet." }});
      }}
      return rows;
    }}

    function motionArtifactDeltaSummary(before, after, context = null) {{
      const rows = motionArtifactDeltaSections(before, after, context);
      const meaningfulRows = rows.filter((item) => String((item && item.label) || "").trim() !== "Action Trigger");
      if (!meaningfulRows.length) return "No localized artifact mutation captured yet.";
      if (meaningfulRows.length === 1 && String((meaningfulRows[0] && meaningfulRows[0].label) || "").trim() === "Artifact Mutation") {{
        return String(meaningfulRows[0].value || "No localized artifact mutation captured yet.");
      }}
      return meaningfulRows.map((item) => `${{item.label || "Change"}}: ${{item.value || ""}}`).join("; ");
    }}

    function needMotionQueueState(context, overrideStatus = "") {{
      const statusText = String(overrideStatus || "").trim();
      if (statusText) return statusText;
      if (!context || typeof context !== "object") return "observed";
      return [
        String(context.urgency || "").trim(),
        Array.isArray(context.sources) ? context.sources.join(", ") : "",
      ].filter(Boolean).join(" / ") || "active";
    }}

    function recordNeedMotion(entry) {{
      if (!entry || typeof entry !== "object") return;
      const needKey = String(entry.need_key || "").trim();
      const context = needMotionContext(needKey);
      const beforeState = String(entry.before_state || "").trim() || needMotionQueueState(context);
      const afterState = String(entry.after_state || "").trim() || String(entry.status || "").trim() || needMotionQueueState(context);
      const evidence = String(entry.evidence || "").trim() || (context
        ? [
            String(context.urgency || "").trim(),
            Array.isArray(context.sources) ? context.sources.join(", ") : "",
            String(context.route_label || "").trim(),
          ].filter(Boolean).join(" / ")
        : "");
      const evidenceLinks = Array.isArray(entry.evidence_links) && entry.evidence_links.length
        ? entry.evidence_links
        : (context
          ? [
              {{ label: "Command Center", href: "/command-center" }},
              {{
                label: Array.isArray(context.sources) && context.sources.includes("approval") ? "Open approval queue" : "Inspect live need",
                href: Array.isArray(context.sources) && context.sources.includes("approval") ? "/approval-queue" : "/api/open-loops?actor=Chris",
              }},
            ]
          : [{{ label: "Command Center", href: "/command-center" }}]);
      const sourceKind = String(entry.source_kind || "").trim() || (needKey ? "need" : "");
      const sourceLabel = String(entry.source_label || "").trim() || (context ? String(context.title || needKey || "").trim() : "");
      recentNeedsMotion = [
        Object.assign({{
          timestamp: new Date().toISOString(),
          evidence,
          evidence_links: evidenceLinks,
          source_kind: sourceKind,
          source_label: sourceLabel,
          action_kind: String(entry.action_kind || "").trim(),
          action_label: String(entry.action_label || "").trim(),
          action_summary: String(entry.action_summary || "").trim(),
          consequence_summary: String(entry.consequence_summary || "").trim(),
          before_state: beforeState,
          after_state: afterState,
          queue_state: afterState,
          transition: `${{beforeState}} -> ${{afterState}}`,
        }}, entry),
        ...((Array.isArray(recentNeedsMotion) ? recentNeedsMotion : []).filter((item) => String(item.timestamp || "").trim() !== String(entry.timestamp || "").trim())),
      ].slice(0, 8);
    }}

    function refreshNeedsMotionPanel(cockpit = null, activity = null) {{
      if (!needsMotion) return;
      const resolvedCockpit = cockpit || buildNeedsCockpit(
        latestSupervisionPayload || {{}},
        latestApprovalsPayload || {{}},
        latestOpenLoopsPayload || {{}},
        latestNotificationsPayload || {{}},
        Array.isArray(latestActivityPayload) ? latestActivityPayload : [],
      );
      const resolvedActivity = Array.isArray(activity) ? activity : (Array.isArray(latestActivityPayload) ? latestActivityPayload : []);
      needsMotion.innerHTML = needsMotionHtml(buildNeedsMotion(resolvedCockpit, resolvedActivity));
      attachActionHandlers();
    }}

    function registryItemHtml(snapshot) {{
      if (!snapshot || snapshot.registry_error) {{
        return `<li class="empty">Registry unavailable: ${{esc((snapshot && snapshot.registry_error) || "unknown error")}}</li>`;
      }}
      const domains = Array.isArray(snapshot.domains) && snapshot.domains.length ? snapshot.domains.join(", ") : "None";
      const stages = Array.isArray(snapshot.authority_stages) && snapshot.authority_stages.length ? snapshot.authority_stages.join(", ") : "None";
      const sampleContracts = Array.isArray(snapshot.sample_contracts) && snapshot.sample_contracts.length
        ? snapshot.sample_contracts.map((item) => `${{item.label || item.agent_id || ""}} [${{item.authority_stage || ""}}]`).join("; ")
        : "No sample contracts.";
      return [
        `<li><strong>Agents</strong><span>${{esc(snapshot.agent_count || 0)}} registered agents</span></li>`,
        `<li><strong>Domains</strong><span>${{esc(domains)}}</span></li>`,
        `<li><strong>Authority Stages</strong><span>${{esc(stages)}}</span></li>`,
        `<li><strong>Sample Contracts</strong><span>${{esc(sampleContracts)}}</span></li>`,
      ].join("");
    }}

    function laneProgressHtml(snapshot) {{
      const lane = snapshot.lane || {{}};
      const brief = snapshot.return_brief || {{}};
      const recentDisplay = Array.isArray(lane.recent_commits) && lane.recent_commits.length
        ? lane.recent_commits.filter(Boolean).join("; ")
        : "No recent commits captured.";
      const dirtyDisplay = Array.isArray(lane.dirty_sample) && lane.dirty_sample.length
        ? lane.dirty_sample.filter(Boolean).join("; ")
        : "Working tree is clean.";
      return [
        `<li><strong>Return Brief</strong><span>${{esc(brief.summary || "No current summary.")}}</span></li>`,
        `<li><strong>Needs Me Count</strong><span>${{esc(brief.what_needs_me_count || 0)}} live items</span></li>`,
        `<li><strong>Dirty Files</strong><span>${{esc(lane.dirty_count || 0)}} current changes in the lane</span></li>`,
        `<li><strong>Recent Seams</strong><span>${{esc(recentDisplay)}}</span></li>`,
        `<li><strong>Dirty Sample</strong><span>${{esc(dirtyDisplay)}}</span></li>`,
      ].join("");
    }}

    function seamTrackerHtml(board) {{
      const counts = board && board.counts && typeof board.counts === "object" ? board.counts : {{}};
      const items = board && Array.isArray(board.items) ? board.items : [];
      const countSummary = Object.entries(counts).map(([key, value]) => `${{value}} ${{String(key || "").toLowerCase()}}`).join(" · ") || "No seam counts recorded yet.";
      const rows = [
        `<li><strong>Summary</strong><span>${{esc((board && board.summary) || "No seam tracker summary yet.")}}</span></li>`,
        `<li><strong>Counts</strong><span>${{esc(countSummary)}}</span></li>`,
      ];
      items.forEach((item, index) => {{
        rows.push(
          `<li class="needs-action"><strong>${{esc(item.name || "Seam")}}</strong><span>${{esc(item.what_became_real || "No seam outcome recorded yet.")}}</span><code class="history-chip history-chip-${{esc(item.status_class || "steady")}}">${{esc(item.status || "Wired")}}</code><code>${{esc(item.module || "Progress")}} · ${{esc(item.maturity || "Wired")}}</code><span>${{esc(item.commit_status || "No commit posture recorded.")}}</span><div class="action-row"><button type="button" data-detail-kind="seam" data-detail-index="${{esc(String(index))}}">Inspect Seam</button></div></li>`
        );
      }});
      return rows.join("");
    }}

    function progressDashboardHtml(board) {{
      const counts = board && board.counts && typeof board.counts === "object" ? board.counts : {{}};
      const items = board && Array.isArray(board.items) ? board.items : [];
      const countSummary = Object.entries(counts)
        .filter(([, value]) => Number(value || 0) > 0)
        .map(([key, value]) => `${{value}} ${{key}}`)
        .join(" · ") || "No progress readiness counts recorded yet.";
      const rows = [
        `<li><strong>Summary</strong><span>${{esc((board && board.summary) || "No progress dashboard summary yet.")}}</span></li>`,
        `<li><strong>Readiness Counts</strong><span>${{esc(countSummary)}}</span></li>`,
      ];
      items.forEach((item, index) => {{
        rows.push(
          `<li class="needs-action"><strong>${{esc(item.module || "Progress Module")}}</strong><span>${{esc(item.summary || "No readiness summary captured yet.")}}</span><code class="history-chip history-chip-${{esc(item.status_class || "steady")}}">${{esc(item.status || "Wired")}}</code><code>${{esc(item.roadmap_level || "Level 3")}} · ${{esc(item.status_label || "wired")}}</code><span>${{esc(item.evidence || "No evidence captured yet.")}}</span><div class="action-row"><button type="button" data-detail-kind="progress" data-detail-index="${{esc(String(index))}}">Inspect Progress</button></div></li>`
        );
      }});
      return rows.join("");
    }}

    function coreModulesHtml(board) {{
      const counts = board && board.counts && typeof board.counts === "object" ? board.counts : {{}};
      const items = board && Array.isArray(board.items) ? board.items : [];
      const countSummary = Object.entries(counts)
        .filter(([, value]) => Number(value || 0) > 0)
        .map(([key, value]) => `${{value}} ${{String(key || "").toLowerCase()}}`)
        .join(" · ") || "No core module readiness counts recorded yet.";
      const rows = [
        `<li><strong>Summary</strong><span>${{esc((board && board.summary) || "No core modules summary yet.")}}</span></li>`,
        `<li><strong>Module Counts</strong><span>${{esc(countSummary)}}</span></li>`,
      ];
      items.forEach((item, index) => {{
        rows.push(
          `<li class="needs-action"><strong>${{esc(item.title || "Module")}}</strong><span>${{esc(item.summary || "No module summary captured yet.")}}</span><code class="history-chip history-chip-${{esc(item.status_class || "steady")}}">${{esc(item.status || "Wired")}}</code><code>${{esc(item.screen_kind || "screen")}} · ${{esc(item.roadmap_level || "Level 3")}}</code><span>${{esc(item.evidence || "No module evidence captured yet.")}}</span><div class="action-row"><a href="${{esc(item.screen_path || "/command-center")}}">Open Module</a><a href="${{esc(item.api_path || "/api/command-center")}}">Open API</a><button type="button" data-detail-kind="module" data-detail-index="${{esc(String(index))}}">Inspect Module</button></div></li>`
        );
      }});
      return rows.join("");
    }}

    function missionTaskBoardHtml(board) {{
      const counts = board && board.counts && typeof board.counts === "object" ? board.counts : {{}};
      const items = board && Array.isArray(board.items) ? board.items : [];
      const countSummary = Object.entries(counts).map(([key, value]) => `${{key}} ${{value}}`).join(" · ") || "No mission counts recorded yet.";
      const rows = [
        `<li><strong>Summary</strong><span>${{esc((board && board.summary) || "No mission board summary yet.")}}</span></li>`,
        `<li><strong>Lane Counts</strong><span>${{esc(countSummary)}}</span></li>`,
      ];
      items.forEach((item, index) => {{
        rows.push(
          `<li class="needs-action"><strong>${{esc(item.title || "Mission")}}</strong><span>${{esc(item.brief || "No mission brief captured yet.")}}</span><code class="history-chip history-chip-${{esc(item.lane_class || "steady")}}">${{esc(item.lane || "next")}}</code><code>${{esc(item.primary_domain || "general")}} · ${{esc(item.owner_agent || "jarvis-orchestrator")}}</code><span>${{esc(item.next_step || "Review mission brief")}}</span><div class="action-row"><button type="button" data-detail-kind="mission" data-detail-index="${{esc(String(index))}}">Inspect Mission</button></div></li>`
        );
      }});
      return rows.join("");
    }}

    function agentOpsRosterHtml(roster) {{
      const counts = roster && roster.counts && typeof roster.counts === "object" ? roster.counts : {{}};
      const items = roster && Array.isArray(roster.items) ? roster.items : [];
      const countSummary = Object.entries(counts).map(([key, value]) => `${{key}} ${{value}}`).join(" · ") || "No agent counts recorded yet.";
      const rows = [
        `<li><strong>Summary</strong><span>${{esc((roster && roster.summary) || "No agent roster summary yet.")}}</span></li>`,
        `<li><strong>Roster Counts</strong><span>${{esc(countSummary)}}</span></li>`,
      ];
      items.forEach((item, index) => {{
        rows.push(
          `<li class="needs-action"><strong>${{esc(item.name || "Agent")}}</strong><span>${{esc(item.purpose || "No purpose recorded.")}}</span><code class="history-chip history-chip-${{esc(item.status_class || "steady")}}">${{esc(item.status || "unknown")}}</code><code class="history-chip history-chip-${{esc(item.maturity_class || "steady")}}">${{esc(item.maturity || "Wired")}}</code><code>${{esc(item.domain || "general")}} · ${{esc(item.assignment || "unassigned")}}</code><span>${{esc(item.last_activity || "not recorded")}}</span><div class="action-row"><button type="button" data-detail-kind="agent" data-detail-index="${{esc(String(index))}}">Inspect Agent</button></div></li>`
        );
      }});
      return rows.join("");
    }}

    function failureRecoveryHtml(supervision, approvals, activity) {{
      const integrations = Array.isArray(supervision.integrations) ? supervision.integrations.filter((item) => item && item.ok === false) : [];
      const activityItems = Array.isArray(activity) ? activity : [];
      const recentFailures = activityItems.filter((item) => {{
        const haystack = [item.title, item.detail, item.subtitle, item.result, item.result_summary, item.entry_type]
          .map((part) => String(part || "").toLowerCase())
          .join(" ");
        return ["fail", "error", "recover", "rollback", "blocked"].some((token) => haystack.includes(token));
      }}).slice(0, 5);
      const lane = supervision.lane || {{}};
      const pendingCount = Number(approvals.pending_count || (Array.isArray(approvals.pending) ? approvals.pending.length : 0) || 0);
      const integrationDisplay = integrations.length
        ? integrations.map((item) => `${{item.name || "integration"}}: ${{item.detail || "Integration needs review."}}`).join("; ")
        : "No integration failures surfaced.";
      const recentDisplay = recentFailures.length
        ? recentFailures.map((item) => `${{item.title || item.detail || item.entry_type || "Runtime failure"}} (${{item.timestamp || "no timestamp"}})`).join("; ")
        : "No recent runtime failures detected.";
      const actionItems = [];
      if (pendingCount) actionItems.push(`Approval queue needs review: ${{pendingCount}} pending approval item(s) are waiting in /approval-queue.`);
      integrations.slice(0, 3).forEach((item) => actionItems.push(`Repair ${{item.name || "integration"}}: ${{item.detail || "Integration needs review."}}`));
      if (Number(lane.dirty_count || 0)) actionItems.push(`Lane has unreconciled local residue: ${{lane.dirty_count || 0}} working-tree change(s) are still present in the current lane.`);
      const actionDisplay = actionItems.length ? actionItems.join("; ") : "Recovery posture is stable: no active integration failures or approval bottlenecks are currently surfaced.";
      return [
        `<li><strong>Integration Issues</strong><span>${{esc(integrations.length)}} current issue(s)</span></li>`,
        `<li><strong>Pending Approvals</strong><span>${{esc(pendingCount)}} gated recovery item(s)</span></li>`,
        `<li><strong>Recent Failures</strong><span>${{esc(recentFailures.length)}} signal(s) detected</span></li>`,
        `<li><strong>Integration Detail</strong><span>${{esc(integrationDisplay)}}</span></li>`,
        `<li><strong>Recent Failure Detail</strong><span>${{esc(recentDisplay)}}</span></li>`,
        `<li><strong>Recovery Actions</strong><span>${{esc(actionDisplay)}}</span></li>`,
      ].join("");
    }}

    function homeOverviewHtml(homeOverviewPayload, level3ChecklistPayload) {{
      const payload = homeOverviewPayload && typeof homeOverviewPayload === "object" ? homeOverviewPayload : {{}};
      const level3Checklist = level3ChecklistPayload && typeof level3ChecklistPayload === "object" ? level3ChecklistPayload : {{}};
      const topNeed = payload.top_need && typeof payload.top_need === "object" ? payload.top_need : {{}};
      const nextMission = payload.next_mission && typeof payload.next_mission === "object" ? payload.next_mission : {{}};
      const activeAgent = payload.active_agent && typeof payload.active_agent === "object" ? payload.active_agent : {{}};
      const systemState = payload.system_state && typeof payload.system_state === "object" ? payload.system_state : {{}};
      const actions = Array.isArray(payload.actions) ? payload.actions.slice(0, 4) : [];
      const checklistRoute = String(level3Checklist.route || "").trim() || "/progress-center#level3-checklist";
      const checklistLabel = String(level3Checklist.route_label || "Open Remaining Level 3 Checklist").trim() || "Open Remaining Level 3 Checklist";
      const checklistApi = String(level3Checklist.api_path || "").trim() || "/api/progress/module";

      function homeActionControl(item) {{
        const endpoint = String(item.endpoint || "").trim();
        if (endpoint) {{
          const method = String(item.method || "POST").trim() || "POST";
          const bodyAttr = typeof item.body === "undefined" ? "" : ` data-body='${{esc(JSON.stringify(item.body))}}'`;
          const keyValue = String(item.needs_key || "").trim();
          const keyAttr = keyValue ? ` data-needs-key="${{esc(keyValue)}}"` : "";
          const route = String(item.route || "").trim();
          const routeLabel = String(item.route_label || "Open Surface").trim() || "Open Surface";
          const routeAttr = route ? ` data-home-route="${{esc(route)}}"` : "";
          const routeLabelAttr = route ? ` data-home-route-label="${{esc(routeLabel)}}"` : "";
          const fallbackLink = route ? `<a href="${{esc(route)}}">${{esc(routeLabel)}}</a>` : "";
          return `<button type="button" data-home-action="1" data-endpoint="${{esc(endpoint)}}" data-method="${{esc(method)}}"${{keyAttr}}${{routeAttr}}${{routeLabelAttr}}${{bodyAttr}}>${{esc(item.label || "Act")}}</button>${{fallbackLink}}`;
        }}
        return `<a href="${{esc(item.route || "/command-center")}}">${{esc(item.label || "Open")}}</a>`;
      }}

      const actionButtons = actions.map((item) => homeActionControl(item)).join("") || `<a href="/command-center">Refresh Home</a>`;
      const actionSummaries = actions.map((item) => {{
        const endpoint = String(item.endpoint || "").trim();
        return `<li><strong>${{esc(item.label || "Open")}}</strong><span>${{esc(item.detail || "Open the related home surface.")}}</span>${{endpoint ? `<code>${{esc(endpoint)}}</code>` : ""}}</li>`;
      }}).join("");
      return [
        `<li><strong>Today</strong><span>${{esc(payload.day_label || "") || "No day label captured."}}</span></li>`,
        `<li><strong>Headline</strong><span>${{esc(payload.headline || "No home headline yet.")}}</span></li>`,
        `<li><strong>Top Need</strong><span>${{esc(topNeed.title || "Nothing urgent right now.")}}</span><span>${{esc(topNeed.detail || "")}}</span><code>${{esc(topNeed.route || "/command-center")}}</code></li>`,
        `<li><strong>Next Mission</strong><span>${{esc(nextMission.title || "No mission queued.")}}</span><span>${{esc(nextMission.detail || "")}}</span><code>${{esc(nextMission.route || "/mission-board")}}</code></li>`,
        `<li><strong>Active Agent</strong><span>${{esc(activeAgent.title || "No active agent surfaced.")}}</span><span>${{esc(activeAgent.detail || "")}}</span><code>${{esc(activeAgent.route || "/agent-ops-center")}}</code></li>`,
        `<li><strong>System State</strong><span>${{esc(systemState.label || "Stable")}}</span><span>${{esc(systemState.detail || "No system summary captured yet.")}}</span><code class="history-chip history-chip-${{esc(systemState.status_class || "steady")}}">${{esc(systemState.label || "stable")}}</code></li>`,
        `<li><strong>Home Counts</strong><span>${{esc(payload.priority_count || 0)}} priorities · ${{esc(payload.active_agent_count || 0)}} active agents · ${{esc(payload.open_mission_count || 0)}} open missions · ${{esc(payload.recent_activity_count || 0)}} recent activity items · ${{esc(payload.useful_module_count || 0)}} useful module lanes</span></li>`,
        `<li><strong>Hosted Edge</strong><span>${{esc(payload.hosted_summary || "Hosted edge posture not captured yet.")}}</span><div class="link-row"><a href="${{esc(payload.hosted_url || "https://jarvis.teambinion.org")}}">${{esc(payload.hosted_url || "https://jarvis.teambinion.org")}}</a></div></li>`,
        `<li><strong>Level 3 Checklist</strong><span>${{esc(level3Checklist.summary || "Open the remaining Level 3 checklist in the dedicated progress route.")}}</span><div class="link-row"><a href="${{esc(checklistRoute)}}">${{esc(checklistLabel)}}</a><a href="${{esc(checklistApi)}}">Open Progress API</a></div></li>`,
        `<li><strong>Focus Actions</strong><div class="link-row">${{actionButtons}}</div></li>`,
        actionSummaries,
      ].join("");
    }}

    function hostedDeploymentHtml(hostedPayload) {{
      const payload = hostedPayload && typeof hostedPayload === "object" ? hostedPayload : {{}};
      const publicRoutes = Array.isArray(payload.public_routes) ? payload.public_routes.filter(Boolean) : [];
      const proofFiles = Array.isArray(payload.proof_files) ? payload.proof_files.filter(Boolean) : [];
      const routeDisplay = publicRoutes.length ? publicRoutes.slice(0, 3).join(" · ") : "No hosted routes discovered.";
      const fileDisplay = proofFiles.length ? proofFiles.join(" | ") : "No deploy proof files captured.";
      return [
        `<li><strong>Status</strong><span>${{esc(payload.summary || "Hosted deployment posture not captured yet.")}}</span><code class="history-chip history-chip-${{esc(payload.status_class || "steady")}}">${{esc(payload.status_label || "wired")}}</code></li>`,
        `<li><strong>Hosted URL</strong><span>${{esc(payload.hosted_url || "https://jarvis.teambinion.org")}}</span></li>`,
        `<li><strong>Deploy Mode</strong><span>${{esc(payload.deploy_mode || "unknown")}}</span><span>${{esc(payload.remote_detail || "")}}</span></li>`,
        `<li><strong>Edge</strong><span>${{esc(payload.edge_provider || "unknown edge")}}</span><span>${{esc(routeDisplay)}}</span></li>`,
        `<li><strong>Deploy Proof</strong><span>${{esc(fileDisplay)}}</span><span>${{esc(payload.next_action || "No deploy next action recorded yet.")}}</span></li>`,
      ].join("");
    }}

    function homeActionResultHtml(resultPayload) {{
      const payload = resultPayload && typeof resultPayload === "object" ? resultPayload : {{}};
      const route = String(payload.route || "").trim();
      const routeLabel = String(payload.route_label || "Open Related Surface").trim() || "Open Related Surface";
      const routeRow = route ? `<div class="link-row"><a href="${{esc(route)}}">${{esc(routeLabel)}}</a></div>` : "";
      return [
        `<li><strong>Action</strong><span>${{esc(payload.label || "No home action recorded yet.")}}</span></li>`,
        `<li><strong>Summary</strong><span>${{esc(payload.summary || "No home result summary captured yet.")}}</span><code class="history-chip history-chip-${{esc(payload.status_class || "steady")}}">${{esc(payload.status_class || "steady")}}</code></li>`,
        `<li><strong>What Changed</strong><span>${{esc(payload.detail || "No home action result detail captured yet.")}}</span>${{routeRow}}</li>`,
      ].join("");
    }}

    function briefPreviewHtml(payload) {{
      const supporting = Array.isArray(payload.supporting_lines) ? payload.supporting_lines.filter(Boolean).join(" ; ") : "";
      const rssSources = Array.isArray(payload.rss_sources) ? payload.rss_sources.filter(Boolean).join(", ") : "";
      return [
        `<li><strong>Actor</strong><span>${{esc(payload.actor || "Chris")}}</span></li>`,
        `<li><strong>Headline</strong><span>${{esc(payload.headline || "No briefing headline yet.")}}</span></li>`,
        `<li><strong>Supporting Lines</strong><span>${{esc(supporting || "No supporting lines captured yet.")}}</span></li>`,
        `<li><strong>Memory Context</strong><span>${{esc(payload.memory_entry_count || 0)}} memory entries informing this preview</span></li>`,
        `<li><strong>Live News</strong><span>${{esc(payload.live_news ? "on" : "off")}} · ${{esc(payload.rss_articles || 0)}} article(s)</span></li>`,
        `<li><strong>Sources</strong><span>${{esc(rssSources || "No live news sources attached.")}}</span></li>`,
      ].join("");
    }}

    function timelinePreviewHtml(openLoops) {{
      const summary = openLoops.summary || {{}};
      const items = Array.isArray(openLoops.items) ? openLoops.items.slice(0, 5) : [];
      const motion = items.map((item) => item.title || item.summary || item.kind || "timeline item").filter(Boolean);
      const motionDisplay = motion.length ? motion.join("; ") : "No recent motion captured.";
      const itemRows = items.length
        ? items.map((item) => {{
            const itemId = String(item.item_id || "");
            const domain = String(item.domain || "");
            const actions = Array.isArray(item.available_actions) ? item.available_actions.slice(0, 4) : [];
            const buttons = itemId && domain && actions.length
              ? `
                <div class="action-row">
                  ${{actions.map((action) => {{
                    const actionId = String(action.id || "");
                    const label = String(action.label || actionId || "Act");
                    const body = JSON.stringify({{ actor: "Chris", domain, item_id: itemId, action: actionId }});
                    return `<button type="button" data-endpoint="/api/open-loops/action" data-method="POST" data-body='${{body.replaceAll("'", "&#39;")}}'>${{esc(label)}}</button>`;
                  }}).join("")}}
                </div>
              `
              : "";
            return `
              <li class="needs-action">
                <strong>${{esc(item.title || "Timeline item")}}</strong>
                <span>${{esc(item.summary || "JARVIS surfaced a live open-loop item.")}}</span>
                <code>${{esc(item.domain || "general")}} / ${{esc(item.status || "")}}</code>
                ${{buttons}}
              </li>
            `;
          }}).join("")
        : "<li class='empty'>No live timeline items yet.</li>";
      return [
        `<li><strong>Waiting On You</strong><span>${{esc((summary.waiting_on_you ?? 0))}} open item(s)</span></li>`,
        `<li><strong>Needs Revisit</strong><span>${{esc((summary.needs_revisit ?? 0))}} surfaced item(s)</span></li>`,
        `<li><strong>Recent Motion</strong><span>${{esc(motion.length)}} timeline signal(s)</span></li>`,
        `<li><strong>Live Timeline</strong><span>Use the inline work controls when items are available.</span></li>`,
        itemRows,
        `<li><strong>Recent Motion Detail</strong><span>${{esc(motionDisplay)}}</span></li>`,
      ].join("");
    }}

    function openLoopInspectorHtml(openLoops) {{
      const summary = openLoops.summary || {{}};
      const queueItems = Array.isArray(openLoops.items) ? openLoops.items.slice(0, 5) : [];
      const proactive = Array.isArray(openLoops.proactive_surface) ? openLoops.proactive_surface.slice(0, 4) : [];
      const lanes = Array.isArray(openLoops.task_lanes) ? openLoops.task_lanes.slice(0, 4) : [];
      const renderTaskActions = (item) => {{
        const actions = Array.isArray(item.available_actions) ? item.available_actions.slice(0, 4) : [];
        const itemId = String(item.item_id || "");
        const domain = String(item.domain || "");
        if (!itemId || !domain || !actions.length) return `<div class="empty">No direct action available yet.</div>`;
        return `<div class="action-row">${{actions.map((action) => {{
          const actionId = String(action.id || "");
          const label = String(action.label || actionId || "Act");
          const body = JSON.stringify({{ actor: "Chris", domain, item_id: itemId, action: actionId }});
          return `<button type="button" data-endpoint="/api/open-loops/action" data-method="POST" data-body='${{body.replaceAll("'", "&#39;")}}'>${{esc(label)}}</button>`;
        }}).join("")}}</div>`;
      }};
      const queueDisplay = queueItems.length
        ? queueItems.map((item) => `
          <li class="needs-action">
            <strong>${{esc(item.title || item.kind || "Open loop")}}</strong>
            <span>${{esc(item.domain || "general")}} · ${{esc(item.status || "open")}} · ${{esc(item.owner_agent || "JARVIS")}}</span>
            <span>${{esc(item.next_action || "No next action captured.")}}</span>
            <span>Review by: ${{esc(item.next_review_at || "not scheduled")}}</span>
            <span>Autonomy: ${{esc((item.auto_execution || {{}}).summary || "Review required.")}}</span>
            <div class="action-row">
              <button type="button" data-detail-kind="open-loop" data-detail-index="${{esc(queueItems.indexOf(item))}}">Inspect</button>
            </div>
            ${{renderTaskActions(item)}}
          </li>
        `).join("")
        : "<li class='empty'>No live open-loop items yet.</li>";
      const proactiveDisplay = proactive.length
        ? proactive.map((item) => `<li><strong>${{esc(item.title || "Open loop")}}</strong><span>${{esc(item.proactive_reason || item.summary || "")}}</span></li>`).join("")
        : "<li class='empty'>No immediate resurfacing items.</li>";
      const laneDisplay = lanes.length
        ? lanes.map((item) => `<li><strong>${{esc(item.owner_agent || "JARVIS")}}</strong><span>${{esc(item.domain || "general")}} · ${{esc(item.lane || "")}}</span><span>${{esc(((item.approval_threshold || {{}}).summary) || "Review required.")}}</span></li>`).join("")
        : "<li class='empty'>No task lanes captured.</li>";
      return [
        `<li><strong>Total</strong><span>${{esc(summary.total ?? 0)}} open loop(s)</span></li>`,
        `<li><strong>Waiting On You</strong><span>${{esc(summary.waiting_on_you ?? 0)}} current item(s)</span></li>`,
        `<li><strong>Queued</strong><span>${{esc(summary.staged ?? 0)}} staged item(s)</span></li>`,
        `<li><strong>Needs Revisit</strong><span>${{esc(summary.needs_revisit ?? 0)}} resurfaced item(s)</span></li>`,
        `<li><strong>Deferred</strong><span>${{esc(summary.hidden_deferred ?? 0)}} hidden deferred item(s)</span></li>`,
        `<li><strong>Queue</strong><span>Use the inline open-loop controls when items are available.</span></li>`,
        queueDisplay,
        `<li><strong>Proactive Surface</strong><span>Items being resurfaced before they slip.</span></li>`,
        proactiveDisplay,
        `<li><strong>Task Lanes</strong><span>Owner lanes and approval thresholds.</span></li>`,
        laneDisplay,
      ].join("");
    }}

    function detailInspectorHtml(detail) {{
      const actions = Array.isArray(detail.available_actions) ? detail.available_actions : [];
      const evidenceLines = Array.isArray(detail.evidence_lines) ? detail.evidence_lines.filter(Boolean) : [];
      const decisionHistory = Array.isArray(detail.decision_history) ? detail.decision_history : [];
      const recentTrace = Array.isArray(detail.recent_trace) ? detail.recent_trace : [];
      const itemTimeline = Array.isArray(detail.item_timeline) ? detail.item_timeline : [];
      const selectedTimelineEvent = detail.selected_timeline_event || null;
      const selectedTimelineEventDetail = detail.selected_timeline_event_detail || null;
      const actionDisplay = actions.length ? actions.map((item) => item.label || item.id || "Act").join(", ") : "No direct actions attached.";
      const evidenceDisplay = evidenceLines.length ? evidenceLines.join("; ") : "No evidence captured yet.";
      const decisionDisplay = decisionHistory.length
        ? decisionHistory.map((item) => `${{item.status || "unknown"}} / ${{item.resolution || "unclassified"}} by ${{item.actor || "-"}} at ${{item.when || "unknown time"}}`).join("; ")
        : "No prior decision history captured.";
      const traceDisplay = recentTrace.length
        ? recentTrace.map((item) => `${{item.title || "Activity"}} (${{item.timestamp || "no timestamp"}}): ${{item.detail || ""}}`).join("; ")
        : "No recent trace captured.";
      const timelineDisplay = itemTimeline.length
        ? itemTimeline.map((item) => `${{item.timestamp || "no timestamp"}} · ${{item.kind || "event"}} · ${{item.title || "Timeline item"}} · ${{item.detail || ""}}`).join("; ")
        : "No per-item timeline captured yet.";
      const timelineButtons = itemTimeline.length
        ? `<div class="action-row">${{itemTimeline.map((item, index) => `<button type="button" data-timeline-index="${{esc(index)}}">${{esc((item.kind || "event") + ": " + (item.title || "Timeline item"))}}</button>`).join("")}}</div>`
        : `<span>No timeline events available.</span>`;
      const selectedTimelineDisplay = selectedTimelineEvent
        ? `${{selectedTimelineEvent.timestamp || "no timestamp"}} · ${{selectedTimelineEvent.kind || "event"}} · ${{selectedTimelineEvent.title || "Timeline item"}} · ${{selectedTimelineEvent.detail || "No timeline event detail available."}}`
        : "No timeline event selected.";
      const eventEvidenceDisplay = selectedTimelineEventDetail && Array.isArray(selectedTimelineEventDetail.evidence_lines) && selectedTimelineEventDetail.evidence_lines.length
        ? selectedTimelineEventDetail.evidence_lines.join("; ")
        : "No event-specific evidence captured yet.";
      const eventEvidenceLinks = selectedTimelineEventDetail && Array.isArray(selectedTimelineEventDetail.evidence_links) && selectedTimelineEventDetail.evidence_links.length
        ? `<span>${{selectedTimelineEventDetail.evidence_links.map((item) => `<a href="${{esc(item.href || "#")}}">${{esc(item.label || item.href || "Link")}}</a>`).join(" ")}}</span>`
        : `<span>No direct evidence links available.</span>`;
      const eventPreviewSections = selectedTimelineEventDetail && Array.isArray(selectedTimelineEventDetail.preview_sections)
        ? selectedTimelineEventDetail.preview_sections
        : [];
      const eventPreviewKind = selectedTimelineEventDetail && selectedTimelineEventDetail.preview_kind
        ? String(selectedTimelineEventDetail.preview_kind)
        : "generic";
      const eventPreviewTitle = selectedTimelineEventDetail && selectedTimelineEventDetail.preview_title
        ? String(selectedTimelineEventDetail.preview_title)
        : "Inline Preview";
      const eventPreviewSummary = selectedTimelineEventDetail && selectedTimelineEventDetail.preview_summary
        ? String(selectedTimelineEventDetail.preview_summary)
        : "No inline evidence preview available.";
      const decisionHistorySummary = selectedTimelineEventDetail && selectedTimelineEventDetail.decision_history_summary
        ? String(selectedTimelineEventDetail.decision_history_summary)
        : "";
      const approvalReviewSummary = selectedTimelineEventDetail && selectedTimelineEventDetail.approval_review_summary
        ? String(selectedTimelineEventDetail.approval_review_summary)
        : "";
      const approvalReviewFields = selectedTimelineEventDetail && Array.isArray(selectedTimelineEventDetail.approval_review_fields)
        ? selectedTimelineEventDetail.approval_review_fields
        : [];
      const approvalPostureFields = selectedTimelineEventDetail && Array.isArray(selectedTimelineEventDetail.approval_posture_fields)
        ? selectedTimelineEventDetail.approval_posture_fields
        : [];
      const consequenceFields = selectedTimelineEventDetail && Array.isArray(selectedTimelineEventDetail.consequence_fields)
        ? selectedTimelineEventDetail.consequence_fields
        : [];
      const guidanceLines = selectedTimelineEventDetail && Array.isArray(selectedTimelineEventDetail.next_actions)
        ? selectedTimelineEventDetail.next_actions
        : [];
      const notificationSnapshot = selectedTimelineEventDetail && selectedTimelineEventDetail.notification_snapshot
        ? String(selectedTimelineEventDetail.notification_snapshot)
        : "";
      const guidanceDisplay = guidanceLines.length
        ? `<div class="preview-subsection"><strong>Operator Guidance</strong>${{guidanceLines.map((item) => `<div class="preview-row"><strong>Next</strong><span>${{esc(item || "")}}</span></div>`).join("")}}</div>`
        : "";
      const previewRows = (items, defaultLabel, valueTag = "span") => items.map((item) => `<div class="preview-row"><strong>${{esc(item.label || defaultLabel)}}</strong><${{valueTag}}>${{esc(item.value || "")}}</${{valueTag}}>`).join("");
      const defaultPreviewDisplay = `<div><strong>${{esc(eventPreviewTitle)}}</strong><span>${{esc(eventPreviewSummary)}}</span></div>`;
      const eventActionButtons = selectedTimelineEventDetail && Array.isArray(selectedTimelineEventDetail.action_buttons) && selectedTimelineEventDetail.action_buttons.length
        ? `<div class="action-row">${{selectedTimelineEventDetail.action_buttons.map((item) => {{
            const endpoint = String(item.endpoint || "").trim();
            const method = String(item.method || "POST").trim();
            const body = item.body ? ` data-body='${{JSON.stringify(item.body).replaceAll("'", "&#39;")}}'` : "";
            if (endpoint) {{
              return `<button type="button" data-endpoint="${{esc(endpoint)}}" data-method="${{esc(method)}}"${{body}}>${{esc(item.label || item.action || "Act")}}</button>`;
            }}
            return `<button type="button" data-event-action="${{esc(item.action || "")}}">${{esc(item.label || item.action || "Act")}}</button>`;
          }}).join("")}}</div>`
        : `<span>No direct event actions available.</span>`;
      let eventPreviewDisplay = defaultPreviewDisplay;
      if (eventPreviewSections.length) {{
        if (eventPreviewKind === "decision") {{
          const decisionRows = previewRows(eventPreviewSections, "Decision", "code");
          const decisionReviewFields = previewRows(approvalReviewFields, "Field", "span");
          const decisionPreviewButtons = selectedTimelineEventDetail && Array.isArray(selectedTimelineEventDetail.action_buttons) && selectedTimelineEventDetail.action_buttons.length
            ? `<div class="action-row">${{selectedTimelineEventDetail.action_buttons.map((item) => {{
                const endpoint = String(item.endpoint || "").trim();
                const method = String(item.method || "POST").trim();
                const body = item.body ? ` data-body='${{JSON.stringify(item.body).replaceAll("'", "&#39;")}}'` : "";
                if (endpoint) {{
                  return `<button type="button" data-endpoint="${{esc(endpoint)}}" data-method="${{esc(method)}}"${{body}}>${{esc(item.label || item.action || "Act")}}</button>`;
                }}
                return `<button type="button" data-event-action="${{esc(item.action || "")}}">${{esc(item.label || item.action || "Act")}}</button>`;
              }}).join("")}}</div>`
            : "";
          eventPreviewDisplay = `<div class="preview-pane"><strong>${{esc(eventPreviewTitle)}}</strong><span>${{esc(eventPreviewSummary)}}</span>${{decisionRows || defaultPreviewDisplay}}`;
          if (decisionReviewFields) eventPreviewDisplay += `<div class="preview-subsection"><strong>Approval Review Fields</strong>${{decisionReviewFields}}</div>`;
          if (approvalPostureFields.length) eventPreviewDisplay += `<div class="preview-subsection"><strong>Consent &amp; Readiness</strong>${{previewRows(approvalPostureFields, "Status", "span")}}</div>`;
          if (consequenceFields.length) eventPreviewDisplay += `<div class="preview-subsection"><strong>What Changed</strong>${{previewRows(consequenceFields, "Change", "span")}}</div>`;
          if (guidanceDisplay) eventPreviewDisplay += guidanceDisplay;
          if (decisionHistorySummary) eventPreviewDisplay += `<div class="preview-subsection"><strong>Recent Approval History</strong><span>${{esc(decisionHistorySummary)}}</span></div>`;
          if (approvalReviewSummary) eventPreviewDisplay += `<div class="preview-subsection"><strong>Approval Review Block</strong><span>${{esc(approvalReviewSummary)}}</span></div>`;
          if (decisionPreviewButtons) eventPreviewDisplay += `<div class="preview-subsection"><strong>Approval Controls</strong>${{decisionPreviewButtons}}</div>`;
          eventPreviewDisplay += `</div>`;
        }} else if (eventPreviewKind === "notification") {{
          eventPreviewDisplay = previewRows(eventPreviewSections, "Notification", "span");
          if (notificationSnapshot) eventPreviewDisplay += `<div class="preview-subsection"><strong>Surfaced Snapshot</strong><span>${{esc(notificationSnapshot)}}</span></div>`;
          if (guidanceDisplay) eventPreviewDisplay += guidanceDisplay;
        }} else if (eventPreviewKind === "trace") {{
          eventPreviewDisplay = previewRows(eventPreviewSections, "Trace", "code");
          if (guidanceDisplay) eventPreviewDisplay += guidanceDisplay;
        }} else if (eventPreviewKind === "open-loop") {{
          eventPreviewDisplay = previewRows(eventPreviewSections, "Open loop", "span");
          if (guidanceDisplay) eventPreviewDisplay += guidanceDisplay;
        }} else {{
          eventPreviewDisplay = previewRows(eventPreviewSections, "Preview", "span");
        }}
      }}
      const eventFieldsDisplay = selectedTimelineEventDetail && Array.isArray(selectedTimelineEventDetail.related_fields) && selectedTimelineEventDetail.related_fields.length
        ? selectedTimelineEventDetail.related_fields.join("; ")
        : "No related fields attached.";
      const eventActionsDisplay = selectedTimelineEventDetail && Array.isArray(selectedTimelineEventDetail.next_actions) && selectedTimelineEventDetail.next_actions.length
        ? selectedTimelineEventDetail.next_actions.join(", ")
        : "No follow-on actions suggested.";
      const motionProofSections = detail && Array.isArray(detail.motion_proof_sections) ? detail.motion_proof_sections : [];
      const motionProofPanels = detail && Array.isArray(detail.motion_proof_panels) ? detail.motion_proof_panels : [];
      const motionProofExcerpts = detail && Array.isArray(detail.motion_proof_excerpts) ? detail.motion_proof_excerpts : [];
      const motionProofArtifacts = detail && Array.isArray(detail.motion_proof_artifacts) ? detail.motion_proof_artifacts : [];
      const motionArtifactFocusSections = detail && Array.isArray(detail.motion_artifact_focus_sections) ? detail.motion_artifact_focus_sections : [];
      const motionArtifactFocusTitle = detail && detail.motion_artifact_focus_title ? String(detail.motion_artifact_focus_title) : "No localized artifact focus selected.";
      const motionArtifactFocusSummary = detail && detail.motion_artifact_focus_summary ? String(detail.motion_artifact_focus_summary) : "Use Motion Proof Artifacts to focus a more exact in-page proof block.";
      const motionArtifactFocusPostureSummary = detail && detail.motion_artifact_focus_posture_summary ? String(detail.motion_artifact_focus_posture_summary) : "No localized artifact posture captured yet.";
      const motionArtifactFocusPostureBadgeLabel = detail && detail.motion_artifact_focus_posture_badge_label ? String(detail.motion_artifact_focus_posture_badge_label) : "artifact posture";
      const motionArtifactFocusPostureBadgeClass = detail && detail.motion_artifact_focus_posture_badge_class ? String(detail.motion_artifact_focus_posture_badge_class) : "artifact";
      const motionArtifactFocusPostureStateLabel = detail && detail.motion_artifact_focus_posture_state_label ? String(detail.motion_artifact_focus_posture_state_label) : "steady";
      const motionArtifactFocusPostureStateClass = detail && detail.motion_artifact_focus_posture_state_class ? String(detail.motion_artifact_focus_posture_state_class) : "steady";
      const motionArtifactFocusPostureHint = detail && detail.motion_artifact_focus_posture_hint ? String(detail.motion_artifact_focus_posture_hint) : "Use the localized proof blocks below for the next exact-record move.";
      const motionArtifactFocusPostureOutcomeLine = detail && detail.motion_artifact_focus_posture_outcome_line ? String(detail.motion_artifact_focus_posture_outcome_line) : "No localized artifact action outcome captured yet.";
      const motionArtifactFocusPostureOutcomeIndex = detail && Number.isInteger(detail.motion_artifact_focus_posture_outcome_index) ? Number(detail.motion_artifact_focus_posture_outcome_index) : null;
      const motionArtifactFocusPostureSnapshotCue = detail && detail.motion_artifact_focus_posture_snapshot_cue ? String(detail.motion_artifact_focus_posture_snapshot_cue) : "";
      const motionArtifactFocusPostureSuggestedAction = detail && detail.motion_artifact_focus_posture_suggested_action && typeof detail.motion_artifact_focus_posture_suggested_action === "object" ? detail.motion_artifact_focus_posture_suggested_action : null;
      const motionArtifactFocusPostureSnapshotAction = detail && detail.motion_artifact_focus_posture_snapshot_action && typeof detail.motion_artifact_focus_posture_snapshot_action === "object" ? detail.motion_artifact_focus_posture_snapshot_action : null;
      const motionArtifactFocusPostureSnapshotReason = detail && detail.motion_artifact_focus_posture_snapshot_reason ? String(detail.motion_artifact_focus_posture_snapshot_reason) : "";
      const motionArtifactFocusPostureSnapshotReasonTarget = detail && detail.motion_artifact_focus_posture_snapshot_reason_target && typeof detail.motion_artifact_focus_posture_snapshot_reason_target === "object" ? detail.motion_artifact_focus_posture_snapshot_reason_target : null;
      const motionArtifactFocusPostureSnapshotReasonFocus = detail && detail.motion_artifact_focus_posture_snapshot_reason_focus && typeof detail.motion_artifact_focus_posture_snapshot_reason_focus === "object" ? detail.motion_artifact_focus_posture_snapshot_reason_focus : null;
      const motionArtifactFocusDeltaSummary = detail && detail.motion_artifact_focus_delta_summary ? String(detail.motion_artifact_focus_delta_summary) : "No localized artifact mutation captured yet.";
      const motionArtifactFocusDeltaSections = detail && Array.isArray(detail.motion_artifact_focus_delta_sections) ? detail.motion_artifact_focus_delta_sections : [];
      const motionArtifactFocusExcerpts = detail && Array.isArray(detail.motion_artifact_focus_excerpts) ? detail.motion_artifact_focus_excerpts : [];
      const motionArtifactFocusProofCompareSummary = detail && detail.motion_artifact_focus_proof_compare_summary ? String(detail.motion_artifact_focus_proof_compare_summary) : "No localized artifact proof comparison captured yet.";
      const motionArtifactFocusProofCompareRows = detail && Array.isArray(detail.motion_artifact_focus_proof_compare_rows) ? detail.motion_artifact_focus_proof_compare_rows : [];
      const motionArtifactFocusHistorySummary = detail && detail.motion_artifact_focus_history_summary ? String(detail.motion_artifact_focus_history_summary) : "No localized artifact action history captured yet.";
      const motionArtifactFocusHistoryMeta = detail && detail.motion_artifact_focus_history_meta ? String(detail.motion_artifact_focus_history_meta) : "";
      const motionArtifactFocusHistoryRows = detail && Array.isArray(detail.motion_artifact_focus_history_rows) ? detail.motion_artifact_focus_history_rows : [];
      const motionArtifactFocusHistoryNote = detail && detail.motion_artifact_focus_history_note ? String(detail.motion_artifact_focus_history_note) : "";
      const motionArtifactFocusRoundTripHistoryIndex = detail && Number.isInteger(detail.motion_artifact_focus_round_trip_history_index) ? Number(detail.motion_artifact_focus_round_trip_history_index) : null;
      const motionArtifactFocusActions = detail && Array.isArray(detail.motion_artifact_focus_actions) ? detail.motion_artifact_focus_actions : [];
      const motionProofDisplay = motionProofSections.length
        ? `<div class="preview-subsection">${{motionProofSections.map((item) => `<div class="preview-row"><strong>${{esc(item.label || "Motion Proof")}}</strong><span>${{esc(item.value || "")}}</span></div>`).join("")}}</div>`
        : `<div class="preview-subsection"><span>No localized motion proof snapshot available.</span></div>`;
      const motionProofPanelDisplay = motionProofPanels.length
        ? motionProofPanels.map((item) => `
          <div class="preview-subsection">
            <strong>${{esc(item.title || "Motion Proof View")}}</strong>
            <span>${{esc(item.summary || "No localized motion-proof view attached.")}}</span>
            ${{previewRows(Array.isArray(item.rows) ? item.rows : [], "Detail")}}
            ${{Array.isArray(item.links) && item.links.length ? `<div class="link-row">${{item.links.map((link) => `<a href="${{esc(link.href || "#")}}">${{esc(link.label || link.href || "Link")}}</a>`).join("")}}</div>` : ""}}
          </div>`).join("")
        : `<div class="preview-subsection"><span>No motion-proof-specific view available.</span></div>`;
      const motionProofExcerptDisplay = motionProofExcerpts.length
        ? `<div class="preview-subsection">${{motionProofExcerpts.map((item) => `<div class="preview-row"><strong>Excerpt</strong><code>${{esc(String(item || ""))}}</code></div>`).join("")}}</div>`
        : `<div class="preview-subsection"><span>No exact motion-proof excerpts attached.</span></div>`;
      const motionProofArtifactDisplay = motionProofArtifacts.length
        ? motionProofArtifacts.map((item) => `
          <div class="preview-subsection">
            <strong>${{esc(item.label || "Proof Artifact")}}</strong>
            <span>${{esc(item.summary || "No artifact summary attached.")}}</span>
            ${{String(item.focus_kind || "").trim() ? `<div class="action-row"><button type="button" data-motion-artifact-index="${{esc(String(motionProofArtifacts.indexOf(item)))}}">Inspect In-Page</button></div>` : ""}}
            <div class="link-row"><a href="${{esc(item.href || "#")}}">${{esc(item.link_label || item.label || "Open Artifact")}}</a></div>
          </div>`).join("")
        : `<div class="preview-subsection"><span>No exact motion-proof artifacts attached.</span></div>`;
      const motionArtifactFocusActionButtons = motionArtifactFocusActions.length
        ? motionArtifactFocusActions.map((item) => {{
            const endpoint = String(item.endpoint || "").trim();
            const method = String(item.method || "POST").trim();
            const body = item.body ? ` data-body='${{JSON.stringify(item.body).replaceAll("'", "&#39;")}}'` : "";
            return endpoint ? `<button type="button" data-endpoint="${{esc(endpoint)}}" data-method="${{esc(method)}}"${{body}}>${{esc(item.label || item.action || "Act")}}</button>` : "";
          }}).join("")
        : "";
      const motionArtifactFocusSuggestedActionButton = motionArtifactFocusPostureSuggestedAction && String(motionArtifactFocusPostureSuggestedAction.endpoint || "").trim()
        ? `<button type="button" data-endpoint="${{esc(String(motionArtifactFocusPostureSuggestedAction.endpoint || ""))}}" data-method="${{esc(String(motionArtifactFocusPostureSuggestedAction.method || "POST"))}}"${{motionArtifactFocusPostureSuggestedAction.body ? ` data-body='${{JSON.stringify(motionArtifactFocusPostureSuggestedAction.body).replaceAll("'", "&#39;")}}'` : ""}}>${{esc(String(motionArtifactFocusPostureSuggestedAction.label || "Suggested Next"))}}</button>`
        : "";
      const motionArtifactFocusSnapshotActionButton = motionArtifactFocusPostureSnapshotAction && String(motionArtifactFocusPostureSnapshotAction.endpoint || "").trim()
        ? `<button type="button" data-endpoint="${{esc(String(motionArtifactFocusPostureSnapshotAction.endpoint || ""))}}" data-method="${{esc(String(motionArtifactFocusPostureSnapshotAction.method || "POST"))}}"${{motionArtifactFocusPostureSnapshotAction.body ? ` data-body='${{JSON.stringify(motionArtifactFocusPostureSnapshotAction.body).replaceAll("'", "&#39;")}}'` : ""}}>${{esc(String(motionArtifactFocusPostureSnapshotAction.label || "Reopened Next"))}}</button>`
        : "";
      const motionArtifactFocusSnapshotReturnButton = motionArtifactFocusPostureSnapshotReasonTarget ? `<button type="button" data-motion-artifact-snapshot-return="1">Return to Reopened Proof</button>` : "";
      const motionArtifactFocusSnapshotReasonButton = motionArtifactFocusPostureSnapshotReasonTarget ? `<button type="button" data-motion-artifact-snapshot-reason="1">Inspect Why</button>` : "";
      const motionArtifactFocusSnapshotReasonFocusDisplay = motionArtifactFocusPostureSnapshotReasonFocus
        : `<div class="preview-subsection"><span>No reopened proof focus selected yet.</span></div>`;
      const motionArtifactFocusDisplay = `<div class="preview-subsection"><strong>${{esc(motionArtifactFocusTitle)}}</strong><span>${{esc(motionArtifactFocusSummary)}}</span><div class="preview-row"><strong>Current Posture</strong>${{motionArtifactFocusPostureBadgeLabel ? `<code class="history-chip history-chip-${{esc(motionArtifactFocusPostureBadgeClass)}}">${{esc(motionArtifactFocusPostureBadgeLabel)}}</code>` : ""}}${{motionArtifactFocusPostureStateLabel ? `<code class="history-chip history-chip-${{esc(motionArtifactFocusPostureStateClass)}}">${{esc(motionArtifactFocusPostureStateLabel)}}</code>` : ""}}<code>${{esc(motionArtifactFocusPostureSummary)}}</code><span>${{esc(motionArtifactFocusPostureHint)}}</span><span>${{esc(motionArtifactFocusPostureOutcomeLine)}}</span>${{motionArtifactFocusPostureSnapshotCue ? `<span>${{esc(motionArtifactFocusPostureSnapshotCue)}}</span>` : ""}}${{motionArtifactFocusPostureSuggestedAction ? `<span>Suggested next: ${{esc(String(motionArtifactFocusPostureSuggestedAction.label || motionArtifactFocusPostureSuggestedAction.summary || "No direct next move suggested."))}}</span>` : ""}}${{motionArtifactFocusSuggestedActionButton}}${{motionArtifactFocusPostureSnapshotAction ? `<span>Reopened next: ${{esc(String(motionArtifactFocusPostureSnapshotAction.label || motionArtifactFocusPostureSnapshotAction.summary || "No reopened next move suggested."))}}</span>` : ""}}${{motionArtifactFocusPostureSnapshotReason ? `<span>Why reopened next: ${{esc(motionArtifactFocusPostureSnapshotReason)}}</span>` : ""}}${{motionArtifactFocusSnapshotReturnButton}}${{motionArtifactFocusSnapshotReasonButton}}${{motionArtifactFocusSnapshotActionButton}}${{Number.isInteger(motionArtifactFocusPostureOutcomeIndex) ? `<button type="button" data-motion-artifact-history-index="${{esc(String(motionArtifactFocusPostureOutcomeIndex))}}">Inspect Last Action</button>` : ""}}</div>${{motionArtifactFocusSnapshotReasonFocusDisplay}}${{motionArtifactFocusSections.length ? previewRows(motionArtifactFocusSections, "Artifact Detail") : "<span>No localized artifact detail captured yet.</span>"}}<div class="preview-subsection"><strong>Artifact Mutation</strong><span>${{esc(motionArtifactFocusDeltaSummary)}}</span>${{motionArtifactFocusDeltaSections.length ? previewRows(motionArtifactFocusDeltaSections, "Artifact Mutation") : "<span>No localized artifact mutation rows captured yet.</span>"}}</div><div class="preview-subsection"><strong>Artifact Proof Excerpts</strong>${{motionArtifactFocusExcerpts.length ? motionArtifactFocusExcerpts.map((item) => `<div class="preview-row"><strong>Excerpt</strong><code>${{esc(String(item || ""))}}</code></div>`).join("") : "<span>No localized artifact proof excerpts captured yet.</span>"}}</div><div class="preview-subsection"><strong>Artifact Proof Compare</strong><span>${{esc(motionArtifactFocusProofCompareSummary)}}</span>${{motionArtifactFocusProofCompareRows.length ? previewRows(motionArtifactFocusProofCompareRows, "Artifact Proof Compare") : "<span>No localized artifact proof comparison rows captured yet.</span>"}}</div><div class="preview-subsection"><strong>Artifact Recent Actions</strong><span>${{esc(motionArtifactFocusHistorySummary)}}</span>${{motionArtifactFocusHistoryMeta ? `<span>${{esc(motionArtifactFocusHistoryMeta)}}</span>` : ""}}${{motionArtifactFocusHistoryRows.length ? motionArtifactFocusHistoryRows.map((item, index) => `<div class="preview-row"><strong>${{esc(item.label || "Artifact Action History")}}</strong>${{item.badge ? `<code class="history-chip history-chip-${{esc(String(item.badge_class || "artifact"))}}">${{esc(String(item.badge || ""))}}</code>` : ""}}${{item.trend ? `<code class="history-chip history-chip-${{esc(String(item.trend_class || "steady"))}}">${{esc(String(item.trend || ""))}}</code>` : ""}}${{item.last_revisited_lane_label ? `<code class="history-chip history-chip-${{esc(String(item.last_revisited_lane_class || "steady"))}}">${{esc(String(item.last_revisited_lane_label || ""))}}</code>` : ""}}<span>${{esc(item.value || "")}}</span>${{item.last_revisited_lane_summary ? `<span>${{esc(String(item.last_revisited_lane_summary || ""))}}</span>` : ""}}${{item.jumpable ? `<button type="button" data-motion-artifact-history-index="${{esc(String(index))}}">Inspect Action</button>` : ""}}${{Array.isArray(item.history_buttons) && item.history_buttons.length ? item.history_buttons.map((button) => button && button.kind === "artifact" ? `<button type="button" data-motion-artifact-snapshot-history-target-artifact-index="${{esc(String(button.motion_artifact_index || ""))}}" data-motion-artifact-snapshot-history-origin-index="${{esc(String(index))}}">Reopen Round-Trip Artifact</button>` : button && button.kind === "timeline" ? `<button type="button" data-motion-artifact-snapshot-history-target-timeline-index="${{esc(String(button.timeline_event_index || ""))}}" data-motion-artifact-snapshot-history-origin-index="${{esc(String(index))}}">Reopen Round-Trip Timeline</button>` : "").join("") : ""}}</div>`).join("") : "<span>No localized artifact action history rows captured yet.</span>"}}${{motionArtifactFocusHistoryNote ? `<span>${{esc(motionArtifactFocusHistoryNote)}}</span>` : ""}}${{motionArtifactFocusRoundTripHistoryIndex !== null ? `<div class="action-row"><button type="button" data-motion-artifact-round-trip-history-return-index="${{esc(String(motionArtifactFocusRoundTripHistoryIndex))}}">Return to Round-Trip History</button></div>` : ""}}</div>${{motionArtifactFocusActionButtons ? `<div class="action-row">${{motionArtifactFocusActionButtons}}</div>` : ""}}</div>`;
      return [
        `<li><strong>Selected Item</strong><span>${{esc(detail.title || "No item selected")}}</span></li>`,
        `<li><strong>Source</strong><span>${{esc(detail.source_kind || "none")}}</span></li>`,
        `<li><strong>Summary</strong><span>${{esc(detail.summary || "Select an item to inspect.")}}</span></li>`,
        `<li><strong>Owner</strong><span>${{esc(detail.owner_agent || "command-center")}}</span></li>`,
        `<li><strong>Status</strong><span>${{esc(detail.domain || "general")}} / ${{esc(detail.status || "idle")}}</span></li>`,
        `<li><strong>Why Now</strong><span>${{esc(detail.why_now || "No current selection.")}}</span></li>`,
        `<li><strong>Next Action</strong><span>${{esc(detail.next_action || "Choose a surfaced item.")}}</span></li>`,
        `<li><strong>Review By</strong><span>${{esc(detail.next_review_at || "not scheduled")}}</span></li>`,
        `<li><strong>Autonomy</strong><span>${{esc(detail.autonomy_summary || "No active item selected.")}}</span></li>`,
        `<li><strong>Evidence</strong><span>${{esc(evidenceDisplay)}}</span></li>`,
        `<li><strong>Last Decision</strong><span>${{esc(detail.last_decision_summary || "No prior decision attached.")}}</span></li>`,
        `<li><strong>Motion Proof Summary</strong><span>${{esc(detail.motion_proof_summary || "No motion-specific proof selected.")}}</span></li>`,
        `<li><strong>Motion Proof Source</strong><span>${{esc(detail.motion_proof_source || "No motion-specific proof source attached.")}}</span></li>`,
        `<li><strong>Motion Proof Snapshot</strong>${{motionProofDisplay}}</li>`,
        `<li><strong>Motion Proof View</strong>${{motionProofPanelDisplay}}</li>`,
        `<li><strong>Motion Proof Excerpts</strong>${{motionProofExcerptDisplay}}</li>`,
        `<li><strong>Motion Proof Artifacts</strong>${{motionProofArtifactDisplay}}</li>`,
        `<li><strong>Motion Artifact Focus</strong>${{motionArtifactFocusDisplay}}</li>`,
        `<li><strong>Change Summary</strong><span>${{esc(detail.change_summary || "No action diff captured yet.")}}</span></li>`,
        `<li><strong>Action Result</strong><span>${{esc(detail.action_result_summary || "No action result captured yet.")}}</span></li>`,
        `<li><strong>Why Changed</strong><span>${{esc(detail.change_evidence_summary || "No post-action evidence captured yet.")}}</span></li>`,
        `<li><strong>Field Deltas</strong><span>${{esc(detail.field_delta_summary || "No field deltas captured yet.")}}</span></li>`,
        `<li><strong>Contract Deltas</strong><span>${{esc(detail.contract_delta_summary || "No contract deltas captured yet.")}}</span></li>`,
        `<li><strong>Derived Deltas</strong><span>${{esc(detail.derived_delta_summary || "No derived deltas captured yet.")}}</span></li>`,
        `<li><strong>Timeline &amp; History</strong><span>${{esc(timelineDisplay)}}</span>${{timelineButtons}}</li>`,
        `<li><strong>Selected Timeline Event</strong><span>${{esc(selectedTimelineDisplay)}}</span></li>`,
        `<li><strong>Timeline Event Evidence</strong><span>${{esc(eventEvidenceDisplay)}}</span></li>`,
        `<li><strong>Timeline Event Links</strong>${{eventEvidenceLinks}}</li>`,
        `<li><strong>Timeline Event Preview</strong><div class="preview-pane"><strong>${{esc(eventPreviewTitle)}}</strong><span>${{esc(eventPreviewSummary)}}</span>${{eventPreviewDisplay}}</div></li>`,
        `<li><strong>Timeline Event Fields</strong><span>${{esc(eventFieldsDisplay)}}</span></li>`,
        `<li><strong>Timeline Event Next Actions</strong><span>${{esc(eventActionsDisplay)}}</span>${{eventActionButtons}}</li>`,
        `<li><strong>Decision History</strong><span>${{esc(decisionDisplay)}}</span></li>`,
        `<li><strong>Recent Trace</strong><span>${{esc(traceDisplay)}}</span></li>`,
        `<li><strong>Available Actions</strong><span>${{esc(actionDisplay)}}</span></li>`,
      ].join("");
    }}

    function actionJournalHtml(entries) {{
      const rows = Array.isArray(entries) ? entries.slice(0, 10) : [];
      if (!rows.length) return "<li class='empty'>No recent actions recorded yet.</li>";
      const operatorCount = rows.filter((item) => ["approval-history", "local-action"].includes(String(item.kind || ""))).length;
      const autonomousCount = rows.length - operatorCount;
      const summaryRows = [
        `<li><strong>Total</strong><span>${{esc(rows.length)}} recent action(s)</span></li>`,
        `<li><strong>Operator</strong><span>${{esc(operatorCount)}} operator-driven item(s)</span></li>`,
        `<li><strong>Autonomous</strong><span>${{esc(autonomousCount)}} autonomous/runtime item(s)</span></li>`,
      ].join("");
      const entryRows = rows.map((item, index) => `
        <li>
          <strong>${{esc(item.title || "Recent action")}}</strong>
          <span>${{esc(item.kind || "activity")}} / ${{esc(item.status || "observed")}}</span>
          <span>${{esc(item.detail || "Recent runtime activity.")}}</span>
          <span>Related: ${{esc(item.related_kind || "activity")}} / ${{esc(item.related_label || item.title || "Recent action")}}</span>
          <div class="action-row">
            <button type="button" data-detail-kind="journal" data-detail-index="${{esc(index)}}">Inspect</button>
            ${{String(item.related_kind || "").trim() && String(item.related_kind || "").trim() !== "activity" ? `<button type="button" data-jump-kind="journal-related" data-jump-index="${{esc(index)}}">Jump to Related</button>` : ""}}
          </div>
          <code>${{esc(item.timestamp || "")}}</code>
        </li>
      `).join("");
      return summaryRows + entryRows;
    }}

    function contractDeltaSummary(before, after) {{
      const deltas = [];
      const track = [
        ["status", before.status, after.status],
        ["next_action", before.next_action, after.next_action],
        ["next_review_at", before.next_review_at, after.next_review_at],
        ["last_decision_summary", before.last_decision_summary, after.last_decision_summary],
      ];
      for (const [name, left, right] of track) {{
        if ((left || "") !== (right || "")) deltas.push(`${{name}}: ${{left || "none"}} -> ${{right || "none"}}`);
      }}
      const beforeDecisionCount = Array.isArray(before.decision_history) ? before.decision_history.length : 0;
      const afterDecisionCount = Array.isArray(after.decision_history) ? after.decision_history.length : 0;
      if (beforeDecisionCount !== afterDecisionCount) {{
        deltas.push(`decision_history_count: ${{beforeDecisionCount}} -> ${{afterDecisionCount}}`);
      }}
      return deltas.length ? deltas.join("; ") : "No contract deltas captured yet.";
    }}

    function derivedDeltaSummary(before, after) {{
      const deltas = [];
      const beforeTraceCount = Array.isArray(before.recent_trace) ? before.recent_trace.length : 0;
      const afterTraceCount = Array.isArray(after.recent_trace) ? after.recent_trace.length : 0;
      const beforeTimelineCount = Array.isArray(before.item_timeline) ? before.item_timeline.length : 0;
      const afterTimelineCount = Array.isArray(after.item_timeline) ? after.item_timeline.length : 0;
      if (beforeTraceCount !== afterTraceCount) {{
        deltas.push(`recent_trace_count: ${{beforeTraceCount}} -> ${{afterTraceCount}}`);
      }}
      if (beforeTimelineCount !== afterTimelineCount) {{
        deltas.push(`item_timeline_count: ${{beforeTimelineCount}} -> ${{afterTimelineCount}}`);
      }}
      if ((before.why_now || "") !== (after.why_now || "")) {{
        deltas.push(`why_now: ${{before.why_now || "none"}} -> ${{after.why_now || "none"}}`);
      }}
      return deltas.length ? deltas.join("; ") : "No derived deltas captured yet.";
    }}

    function fieldDeltaSummary(before, after) {{
      const deltas = [];
      const contractSummary = contractDeltaSummary(before, after);
      const derivedSummary = derivedDeltaSummary(before, after);
      if (contractSummary !== "No contract deltas captured yet.") deltas.push(contractSummary);
      if (derivedSummary !== "No derived deltas captured yet.") deltas.push(derivedSummary);
      return deltas.length ? deltas.join("; ") : "No field deltas captured yet.";
    }}

    function buildItemTimeline(entries) {{
      const rows = (Array.isArray(entries) ? entries : []).filter((item) => item && (item.title || item.detail || item.timestamp));
      return rows.sort((left, right) => String(left.timestamp || "").localeCompare(String(right.timestamp || "")));
    }}

    function selectedTimelineEventForDetail(detail) {{
      const itemTimeline = Array.isArray((detail || {{}}).item_timeline) ? detail.item_timeline : [];
      if (!itemTimeline.length) return null;
      const maxIndex = itemTimeline.length - 1;
      const index = Number.isInteger(currentTimelineEventIndex) ? Math.min(Math.max(currentTimelineEventIndex, 0), maxIndex) : maxIndex;
      currentTimelineEventIndex = index;
      return itemTimeline[index] || itemTimeline[maxIndex] || null;
    }}

    function selectedTimelineEventDetailForDetail(detail, event) {{
      if (!event) return null;
      const evidenceLines = [
        `Selected from ${{detail.source_kind || "detail"}}`,
        `Event kind: ${{event.kind || "event"}}`,
        `Event timestamp: ${{event.timestamp || "no timestamp"}}`,
      ];
      const relatedFields = [
        `status=${{detail.status || "idle"}}`,
        `next_action=${{detail.next_action || "none"}}`,
        `review_by=${{detail.next_review_at || "not scheduled"}}`,
      ];
      const nextActions = [];
      const actionButtons = [];
      const evidenceLinks = [];
      const previewSections = [];
      let previewKind = "generic";
      let previewTitle = "Inline Preview";
      let previewSummary = detail.summary || "No inline evidence preview available.";
      if (String(event.kind || "") === "decision") nextActions.push("Review approval posture");
      if (String(event.kind || "") === "trace") nextActions.push("Inspect runtime trace context");
      if (String(event.kind || "") === "notification") nextActions.push("Review surfaced notification");
      if (String(event.kind || "") === "open-loop") nextActions.push("Inspect open-loop action options");
      if (String(event.kind || "") === "decision") actionButtons.push({{ action: "show-approval-context", label: "Show Approval Context" }});
      if (String(event.kind || "") === "trace") actionButtons.push({{ action: "show-activity-context", label: "Show Activity Context" }});
      if (String(event.kind || "") === "notification") actionButtons.push({{ action: "show-notification-context", label: "Show Notification Context" }});
      if (String(event.kind || "") === "open-loop") actionButtons.push({{ action: "show-open-loop-context", label: "Show Open-Loop Context" }});
      if (String(event.kind || "") === "decision" && String(detail.request_id || "").trim()) {{
        const requestId = String(detail.request_id || "").trim();
        actionButtons.push({{ endpoint: `/api/approvals/${{requestId}}/approve`, method: "POST", label: "Approve Request" }});
        actionButtons.push({{ endpoint: `/api/approvals/${{requestId}}/reject`, method: "POST", body: {{ reason: "Need a safer plan first" }}, label: "Reject Request" }});
        actionButtons.push({{ endpoint: `/api/approvals/${{requestId}}/execute`, method: "POST", label: "Execute Request" }});
      }}
      if (String(event.kind || "") === "notification" && String(detail.notification_id || "").trim()) {{
        const notificationId = String(detail.notification_id || "").trim();
        const actions = Object.assign({{}}, detail.notification_actions || {{}});
        const openEndpoint = String(actions.open || `/api/assistant-core/notifications/${{notificationId}}`).trim();
        const ignoreEndpoint = String(actions.ignore || `/api/assistant-core/notifications/${{notificationId}}`).trim();
        actionButtons.push({{ endpoint: openEndpoint, method: "POST", body: {{ actor: "Chris", status: "opened" }}, label: "Open Notification" }});
        actionButtons.push({{ endpoint: ignoreEndpoint, method: "POST", body: {{ actor: "Chris", status: "ignored" }}, label: "Ignore Notification" }});
      }}
      if (String(event.kind || "") === "open-loop" && String(detail.item_id || "").trim() && String(detail.domain || "").trim()) {{
        const domain = String(detail.domain || "").trim();
        const itemId = String(detail.item_id || "").trim();
        const availableActions = Array.isArray(detail.available_actions) ? detail.available_actions : [];
        availableActions.slice(0, 3).forEach((item) => {{
          const actionId = String(item.id || "").trim();
          if (!actionId) return;
          actionButtons.push({{
            endpoint: "/api/open-loops/action",
            method: "POST",
            body: {{ actor: "Chris", domain, item_id: itemId, action: actionId }},
            label: item.label || actionId,
          }});
        }});
      }}
      if (String(event.kind || "") === "decision") {{
        previewKind = "decision";
        previewTitle = "Approval Decision Pane";
        previewSummary = "Approval-specific context for the selected decision event.";
        evidenceLinks.push({{ href: "/approval-queue", label: "Approval Queue" }});
        evidenceLinks.push({{ href: "/api/approval-queue/snapshot", label: "Approval Queue JSON" }});
        previewSections.push({{ label: "Decision Resolution", value: event.detail || "No decision detail captured." }});
        previewSections.push({{ label: "Last Decision", value: detail.last_decision_summary || "No prior decision attached." }});
        previewSections.push({{ label: "Decision Count", value: String(Array.isArray(detail.decision_history) ? detail.decision_history.length : 0) }});
        previewSections.push({{ label: "Request ID", value: String(detail.request_id || "not attached") }});
        const latestDecision = Array.isArray(detail.decision_history) && detail.decision_history.length ? detail.decision_history[0] : null;
        const latestDecisionStatus = latestDecision ? String(latestDecision.status || "").toLowerCase() : "";
        const latestDecisionResolution = latestDecision ? String(latestDecision.resolution || "").toLowerCase() : "";
        previewSections.push({{ label: "Decision Actor", value: latestDecision ? String(latestDecision.actor || "-") : "-" }});
        previewSections.push({{ label: "Decision Time", value: latestDecision ? String(latestDecision.when || "unknown time") : "unknown time" }});
        const decisionHistorySummary = Array.isArray(detail.decision_history) && detail.decision_history.length
          ? detail.decision_history.map((item) => `${{item.status || "unknown"}} / ${{item.resolution || "unclassified"}} by ${{item.actor || "-"}}`).join("; ")
          : "No approval history captured.";
        const approvalContext = detail.approval_review_context || {{}};
        const approvalReviewSummary = [
          `request=${{approvalContext.request_id || detail.request_id || "not attached"}}`,
          `risk=${{approvalContext.risk_tier || detail.status || "pending"}}`,
          `agent=${{approvalContext.agent_label || detail.owner_agent || "approval-queue"}}`,
          `detail=${{approvalContext.description || detail.summary || "Pending approval needs operator review."}}`,
        ].join("; ");
        const approvalReviewFields = [
          {{ label: "Request", value: String(approvalContext.request_id || detail.request_id || "not attached") }},
          {{ label: "Risk Tier", value: String(approvalContext.risk_tier || detail.status || "pending") }},
          {{ label: "Agent", value: String(approvalContext.agent_label || detail.owner_agent || "approval-queue") }},
          {{ label: "Review Detail", value: String(approvalContext.description || detail.summary || "Pending approval needs operator review.") }},
          {{ label: "Next Operator Move", value: String(detail.next_action || "Review approval posture") }},
        ];
        const hasExecuteAction = actionButtons.some((item) => String(item.label || "").toLowerCase().includes("execute") || String(item.endpoint || "").includes("/execute"));
        const approvalPostureFields = [
          {{
            label: "Consent Posture",
            value: latestDecisionStatus.includes("reject") || latestDecisionResolution.includes("reject") || latestDecisionResolution.includes("deny")
              ? "Consent withheld; a safer plan is required before execution."
              : ((latestDecisionStatus.includes("approve") || latestDecisionResolution.includes("allow"))
                ? "Operator consent recorded for this request."
                : "Awaiting explicit operator consent."),
          }},
          {{
            label: "Execution Readiness",
            value: latestDecisionStatus.includes("executed")
              ? "Execution has already been recorded for this request."
              : (((latestDecisionStatus.includes("approve") || latestDecisionResolution.includes("allow")) && hasExecuteAction)
                ? "Execution can be triggered directly from this decision pane."
                : (hasExecuteAction
                  ? "Execution is available once consent posture is confirmed."
                  : "No direct execution control is attached to this request yet.")),
          }},
          {{
            label: "Outcome State",
            value: latestDecision
              ? `Latest outcome: ${{detail.last_decision_summary || `${{latestDecision.status || "unknown"}} by ${{latestDecision.actor || "-"}}`}}`
              : "No prior approval outcome has been recorded yet.",
          }},
        ];
        const consequenceFields = Array.isArray(detail.approval_consequence_fields) && detail.approval_consequence_fields.length
          ? detail.approval_consequence_fields
          : [
          {{
            label: "Result",
            value: String(detail.action_result_summary || "No action result captured yet."),
          }},
          {{
            label: "Summary",
            value: String(detail.change_summary || "No action diff captured yet."),
          }},
          {{
            label: "Evidence",
            value: String(detail.change_evidence_summary || "No post-action evidence captured yet."),
          }},
        ];
        const consequenceGuidance = Array.isArray(detail.approval_guidance_lines) && detail.approval_guidance_lines.length
          ? detail.approval_guidance_lines
          : nextActions;
        return {{
          evidence_lines: evidenceLines,
          evidence_links: evidenceLinks,
          preview_kind: previewKind,
          preview_title: previewTitle,
          preview_summary: previewSummary,
          preview_sections: previewSections,
          decision_history_summary: decisionHistorySummary,
          approval_review_summary: approvalReviewSummary,
          approval_review_fields: approvalReviewFields,
          approval_posture_fields: approvalPostureFields,
          consequence_fields: consequenceFields,
          next_actions: consequenceGuidance,
          related_fields: relatedFields,
          action_buttons: actionButtons,
        }};
      }}
      if (String(event.kind || "") === "trace") {{
        previewKind = "trace";
        previewTitle = "Runtime Trace Pane";
        previewSummary = "Compact runtime evidence for the selected trace event.";
        evidenceLinks.push({{ href: "/api/activity", label: "Activity JSON" }});
        evidenceLinks.push({{ href: "/command-center", label: "Command Center" }});
        previewSections.push({{ label: "Trace Detail", value: event.detail || "No trace detail captured." }});
        previewSections.push({{ label: "Recent Trace Count", value: String(Array.isArray(detail.recent_trace) ? detail.recent_trace.length : 0) }});
        previewSections.push({{ label: "Runtime Status", value: detail.status || "unknown" }});
        const traceNextActions = traceGuidance(detail, event);
        return {{
          evidence_lines: evidenceLines,
          evidence_links: evidenceLinks,
          preview_kind: previewKind,
          preview_title: previewTitle,
          preview_summary: previewSummary,
          preview_sections: previewSections,
          related_fields: relatedFields,
          next_actions: traceNextActions,
          action_buttons: actionButtons,
        }};
      }}
      if (String(event.kind || "") === "notification") {{
        previewKind = "notification";
        previewTitle = "Notification Snapshot Pane";
        previewSummary = "Compact surfaced-notification context for the selected notification event.";
        evidenceLinks.push({{ href: "/api/assistant-core/notifications?actor=Chris", label: "Notifications JSON" }});
        evidenceLinks.push({{ href: "/command-center", label: "Command Center" }});
        previewSections.push({{ label: "Notification Status", value: detail.status || "unknown" }});
        previewSections.push({{ label: "Why Surfaced", value: detail.why_now || "No surfaced reason captured." }});
        previewSections.push({{ label: "Owner", value: detail.owner_agent || "notification-feed" }});
        previewSections.push({{ label: "Notification ID", value: String(detail.notification_id || "not attached") }});
        previewSections.push({{ label: "Suggested Action", value: detail.next_action || "Open or ignore this surfaced notification." }});
        previewSections.push({{ label: "Priority Hint", value: Array.isArray(detail.evidence_lines) && detail.evidence_lines.length ? String(detail.evidence_lines[1] || "normal") : "normal" }});
        const notificationSnapshotText = [
          `status=${{detail.status || "unknown"}}`,
          `owner=${{detail.owner_agent || "notification-feed"}}`,
          `next=${{detail.next_action || "Open or ignore this surfaced notification."}}`,
        ].join("; ");
        const notificationNextActions = notificationGuidance(detail);
        return {{
          evidence_lines: evidenceLines,
          evidence_links: evidenceLinks,
          preview_kind: previewKind,
          preview_title: previewTitle,
          preview_summary: previewSummary,
          preview_sections: previewSections,
          notification_snapshot: notificationSnapshotText,
          related_fields: relatedFields,
          next_actions: notificationNextActions,
          action_buttons: actionButtons,
        }};
      }}
      if (String(event.kind || "") === "open-loop") {{
        previewKind = "open-loop";
        previewTitle = "Open-Loop Snapshot Pane";
        previewSummary = "Compact open-loop execution context for the selected open-loop event.";
        evidenceLinks.push({{ href: "/api/open-loops?actor=Chris", label: "Open Loops JSON" }});
        evidenceLinks.push({{ href: "/command-center", label: "Command Center" }});
        previewSections.push({{ label: "Open-Loop Summary", value: detail.summary || "No open-loop summary captured." }});
        previewSections.push({{ label: "Available Actions", value: String(Array.isArray(detail.available_actions) ? detail.available_actions.length : 0) }});
        previewSections.push({{ label: "Autonomy", value: detail.autonomy_summary || "No autonomy summary captured." }});
        const openLoopNextActions = openLoopGuidance(detail);
        return {{
          evidence_lines: evidenceLines,
          evidence_links: evidenceLinks,
          preview_kind: previewKind,
          preview_title: previewTitle,
          preview_summary: previewSummary,
          preview_sections: previewSections,
          related_fields: relatedFields,
          next_actions: openLoopNextActions,
          action_buttons: actionButtons,
        }};
      }}
      if (!evidenceLinks.length) evidenceLinks.push({{ href: "/api/command-center", label: "Command Center JSON" }});
      if (!previewSections.length) previewSections.push({{ label: "Preview", value: detail.summary || "No inline evidence preview available." }});
      if (!nextActions.length) nextActions.push(detail.next_action || "Inspect related item context");
      return {{
        evidence_lines: evidenceLines,
        evidence_links: evidenceLinks,
        preview_kind: previewKind,
        preview_title: previewTitle,
        preview_summary: previewSummary,
        preview_sections: previewSections,
        related_fields: relatedFields,
        next_actions: nextActions,
        action_buttons: actionButtons,
      }};
    }}

    function performEventAction(action) {{
      if (action === "show-approval-context" || action === "show-open-loop-context") {{
        currentDetailSelection = {{ kind: "open-loop", index: (currentDetailSelection || {{}}).kind === "open-loop" ? Number((currentDetailSelection || {{}}).index || 0) : 0 }};
        currentTimelineEventIndex = null;
        setDetailInspector(selectedDetail());
        return;
      }}
      if (action === "show-notification-context") {{
        currentDetailSelection = {{ kind: "notification", index: (currentDetailSelection || {{}}).kind === "notification" ? Number((currentDetailSelection || {{}}).index || 0) : 0 }};
        currentTimelineEventIndex = null;
        setDetailInspector(selectedDetail());
        return;
      }}
      if (action === "show-activity-context") {{
        if (activityFeed) activityFeed.scrollIntoView({{ behavior: "smooth", block: "center" }});
        if (statusNote) statusNote.textContent = "Activity context is highlighted in the Activity Feed panel.";
      }}
    }}

    function approvalConsentPosture(detail) {{
      const summary = String((detail && detail.last_decision_summary) || "").toLowerCase();
      if (summary.includes("reject") || summary.includes("deny")) return "Consent withheld";
      if (summary.includes("approve") || summary.includes("allow")) return "Consent recorded";
      return "Awaiting explicit operator consent";
    }}

    function approvalExecutionReadiness(detail) {{
      const summary = String((detail && detail.last_decision_summary) || "").toLowerCase();
      const actions = Array.isArray((detail && detail.available_actions) || []) ? detail.available_actions : [];
      const hasExecute = actions.some((item) => String((item && item.id) || "").trim().toLowerCase() === "execute");
      if (summary.includes("executed")) return "Execution already recorded";
      if ((summary.includes("approve") || summary.includes("allow")) && hasExecute) return "Execution ready from this cockpit";
      if (hasExecute) return "Execution available once consent is confirmed";
      return "No direct execution control attached";
    }}

    function approvalOutcomeState(detail) {{
      const summary = String((detail && detail.last_decision_summary) || "").trim();
      return summary ? `Latest outcome: ${{summary}}` : "No prior approval outcome recorded";
    }}

    function approvalActionKind(context) {{
      const endpoint = String((context && context.endpoint) || "").toLowerCase();
      if (endpoint.includes("/approve")) return "approve";
      if (endpoint.includes("/reject")) return "reject";
      if (endpoint.includes("/execute")) return "execute";
      if (endpoint.includes("/cancel")) return "cancel";
      return "refresh";
    }}

    function approvalConsequenceFields(before, after, context) {{
      const actionKind = approvalActionKind(context);
      const result = (context && context.result) || {{}};
      const beforeConsent = approvalConsentPosture(before);
      const afterConsent = approvalConsentPosture(after);
      const beforeReadiness = approvalExecutionReadiness(before);
      const afterReadiness = approvalExecutionReadiness(after);
      const beforeOutcome = approvalOutcomeState(before);
      const afterOutcome = approvalOutcomeState(after);
      const errorText = String((context && context.error) || "").trim();
      const hasPostureShift = beforeConsent !== afterConsent || beforeReadiness !== afterReadiness || beforeOutcome !== afterOutcome;
      const payloadStatus = String(result.status || result.result || "").trim();
      const payloadResolution = String(result.resolution || result.outcome || "").trim();
      const payloadRequestId = String(result.request_id || result.item_id || "").trim();
      const payloadReason = String(result.detail || result.reason || result.message || "").trim();
      const actionLabel = {{
        approve: "Approve action",
        reject: "Reject action",
        execute: "Execute action",
        cancel: "Cancel action",
        refresh: "Refresh action",
      }}[actionKind] || "Operator action";
      if (errorText) {{
        return [
          {{ label: "Action", value: actionLabel }},
          {{ label: "Failure State", value: `Action failed: ${{errorText}}` }},
          {{ label: "Payload Status", value: payloadStatus || "No status returned" }},
          {{ label: "Consent Shift", value: `Stable: ${{afterConsent}}` }},
          {{ label: "Outcome Shift", value: `Stable: ${{afterOutcome}}` }},
        ];
      }}
      if (!hasPostureShift) {{
        return [
          {{ label: "Action", value: actionLabel }},
          {{ label: "Change Mode", value: "No posture shift detected" }},
          {{ label: "Payload Status", value: payloadStatus || "No status returned" }},
          {{ label: "Payload Resolution", value: payloadResolution || "No resolution returned" }},
          {{ label: "Consent Shift", value: `Stable: ${{afterConsent}}` }},
          {{ label: "Readiness Shift", value: `Stable: ${{afterReadiness}}` }},
          {{ label: "Outcome Shift", value: `Stable: ${{afterOutcome}}` }},
        ];
      }}
      const fields = [
        {{ label: "Action", value: actionLabel }},
        {{ label: "Consent Shift", value: beforeConsent === afterConsent ? `Stable: ${{afterConsent}}` : `${{beforeConsent}} -> ${{afterConsent}}` }},
        {{ label: "Readiness Shift", value: beforeReadiness === afterReadiness ? `Stable: ${{afterReadiness}}` : `${{beforeReadiness}} -> ${{afterReadiness}}` }},
        {{ label: "Outcome Shift", value: beforeOutcome === afterOutcome ? `Stable: ${{afterOutcome}}` : `${{beforeOutcome}} -> ${{afterOutcome}}` }},
      ];
      if (payloadStatus) fields.push({{ label: "Payload Status", value: payloadStatus }});
      if (payloadResolution) fields.push({{ label: "Payload Resolution", value: payloadResolution }});
      if (payloadRequestId) fields.push({{ label: "Payload Request", value: payloadRequestId }});
      if (payloadReason) fields.push({{ label: "Payload Detail", value: payloadReason }});
      return fields;
    }}

    function approvalReasonPrescription(payloadReason, actionKind) {{
      const reason = String(payloadReason || "").trim();
      const reasonLower = reason.toLowerCase();
      if (!reason) return "";
      if (reasonLower.includes("allow resolution")) return "Returned approval detail confirms allow resolution; execution can proceed when ready.";
      if (reasonLower.includes("safer plan")) return "Returned detail requires a safer plan before this approval path should continue.";
      if (reasonLower.includes("missing prerequisite") || reasonLower.includes("prerequisite")) return "Returned detail indicates a missing prerequisite; satisfy that dependency before retrying.";
      if (reasonLower.includes("already approved")) return "Returned detail indicates consent was already recorded; confirm whether execution is the real next step.";
      if (reasonLower.includes("already executed")) return "Returned detail indicates execution already happened; verify downstream evidence instead of repeating the action.";
      if (reasonLower.includes("deny") || reasonLower.includes("reject")) return "Returned detail confirms consent is withheld; revise the plan before asking again.";
      if (actionKind === "approve") return `Returned approval detail: ${{reason}}`;
      if (actionKind === "execute") return `Execution detail: ${{reason}}`;
      if (actionKind === "reject") return `Use the returned reason as the remediation path: ${{reason}}`;
      return `Returned detail: ${{reason}}`;
    }}

    function approvalRemediationGuidance(before, after, context) {{
      const result = (context && context.result) || {{}};
      const actionKind = approvalActionKind(context);
      const errorText = String((context && context.error) || "").trim();
      const payloadStatus = String(result.status || result.result || "").trim().toLowerCase();
      const payloadResolution = String(result.resolution || result.outcome || "").trim().toLowerCase();
      const payloadReason = String(result.detail || result.reason || result.message || "").trim();
      const beforeConsent = approvalConsentPosture(before);
      const afterConsent = approvalConsentPosture(after);
      const beforeReadiness = approvalExecutionReadiness(before);
      const afterReadiness = approvalExecutionReadiness(after);
      const beforeOutcome = approvalOutcomeState(before);
      const afterOutcome = approvalOutcomeState(after);
      const hasPostureShift = beforeConsent !== afterConsent || beforeReadiness !== afterReadiness || beforeOutcome !== afterOutcome;
      if (errorText) {{
        return [
          "Inspect the returned failure detail before retrying this approval action.",
          approvalReasonPrescription(payloadReason, actionKind) || "Collect a safer plan or missing prerequisite before retrying.",
        ];
      }}
      if (!hasPostureShift) {{
        return [
          "No approval posture changed; confirm whether this request was already in the intended state.",
          approvalReasonPrescription(payloadReason, actionKind) || "Check the approval queue snapshot for current request state before repeating the action.",
        ];
      }}
      if (actionKind === "reject" || payloadStatus.includes("reject") || payloadResolution.includes("reject") || payloadResolution.includes("deny")) {{
        return [
          "Consent is now withheld; prepare a safer plan before attempting execution again.",
          approvalReasonPrescription(payloadReason, "reject") || "Capture the reason for rejection in the approval context.",
        ];
      }}
      if (actionKind === "execute" || payloadStatus.includes("execut") || payloadResolution.includes("execut")) {{
        return [
          "Execution has advanced; verify downstream runtime evidence and activity traces next.",
          approvalReasonPrescription(payloadReason, "execute") || "Review activity and open-loop state to confirm completion.",
        ];
      }}
      if (actionKind === "approve" || payloadStatus.includes("approv") || payloadResolution.includes("allow")) {{
        return [
          "Consent is now recorded; execution can proceed when the request is ready.",
          approvalReasonPrescription(payloadReason, "approve") || "Use the execution control when you want JARVIS to act on this approval.",
        ];
      }}
      return [
        "Review the updated approval posture before taking another action.",
        approvalReasonPrescription(payloadReason, actionKind) || "Use the approval queue and command center context to decide the next step.",
      ];
    }}

    function notificationGuidance(detail) {{
      const status = String((detail && detail.status) || "").trim().toLowerCase();
      const reason = String((detail && detail.why_now) || "").trim();
      if (status.includes("unseen") || status.includes("unread")) {{
        return [
          "Open the notification to acknowledge and inspect the surfaced context.",
          reason ? `Why it surfaced: ${{reason}}` : "Review the surfaced notification before dismissing it.",
        ];
      }}
      if (status.includes("ignored")) {{
        return [
          "This notification has already been ignored; confirm that no follow-up is needed.",
          reason ? `Ignored context: ${{reason}}` : "Use the notification feed if you need to resurface it later.",
        ];
      }}
      return [
        "Review the surfaced notification and decide whether to open or ignore it.",
        reason ? `Why it surfaced: ${{reason}}` : "Use the inline inbox controls when you are ready to act.",
      ];
    }}

    function openLoopGuidance(detail) {{
      const actionCount = Array.isArray((detail && detail.available_actions) || []) ? detail.available_actions.length : 0;
      const autonomy = String((detail && detail.autonomy_summary) || "").trim();
      const nextAction = String((detail && detail.next_action) || "").trim();
      if (actionCount > 0) {{
        return [
          nextAction || "Use the inline open-loop actions to move this workstream forward.",
          autonomy ? `Autonomy posture: ${{autonomy}}` : "Review the autonomy posture before choosing an action.",
        ];
      }}
      return [
        nextAction || "Inspect the open-loop context to decide the next step.",
        autonomy ? `Autonomy posture: ${{autonomy}}` : "No autonomy posture is attached yet; inspect the queue and related context.",
      ];
    }}

    function traceGuidance(detail, event) {{
      const traceCount = Array.isArray((detail && detail.recent_trace) || []) ? detail.recent_trace.length : 0;
      const status = String((detail && detail.status) || "").trim();
      const traceDetail = String((event && event.detail) || "").trim();
      return [
        traceDetail ? `Inspect runtime trace context for ${{traceDetail}}.` : "Inspect the latest runtime trace context.",
        traceCount > 1
          ? `There are ${{traceCount}} recent trace signals to compare for drift or recovery progress.`
          : (status ? `Current runtime status is ${{status}}; verify whether the trace matches the expected system posture.` : "Verify whether this trace reflects the current runtime posture."),
      ];
    }}

    function actionResultSummary(context) {{
      const result = (context && context.result) || {{}};
      const pieces = [];
      if (context && context.endpoint) pieces.push(`endpoint ${{context.endpoint}}`);
      const status = String(result.status || result.result || "").trim();
      if (status) pieces.push(`result=${{status}}`);
      const resolution = String(result.resolution || result.outcome || "").trim();
      if (resolution) pieces.push(`resolution=${{resolution}}`);
      const requestId = String(result.request_id || result.item_id || "").trim();
      if (requestId) pieces.push(`item=${{requestId}}`);
      return pieces.length ? pieces.join(" · ") : "Action completed but returned no structured summary.";
    }}

    function needsActionState(endpoint, payload, currentState) {{
      const baseState = Object.assign({{}}, currentState || {{}});
      const endpointText = String(endpoint || "").toLowerCase();
      const payloadStatus = String((payload && (payload.status || payload.result)) || "").trim().toLowerCase();
      const payloadResolution = String((payload && (payload.resolution || payload.outcome)) || "").trim().toLowerCase();
      const payloadDetail = String((payload && (payload.detail || payload.message || payload.reason)) || "").trim();
      const requestId = String((payload && (payload.request_id || payload.item_id)) || "").trim();

      if (endpointText.includes("/api/approvals/")) {{
        const approvalOutcome = payloadResolution || payloadStatus || "updated";
        const approvalSummaryBits = [`Approval updated: ${{approvalOutcome}}`];
        if (requestId) approvalSummaryBits.push(`request=${{requestId}}`);
        if (payloadDetail) approvalSummaryBits.push(payloadDetail);
        const shouldRetire = ["approved", "approve", "allow", "rejected", "reject", "denied", "deny", "cancelled", "canceled", "executed", "complete", "completed"].some((token) => approvalOutcome.includes(token) || payloadStatus.includes(token));
        const approvalPosture = shouldRetire
          ? (approvalOutcome.includes("execut") ? "Execution moved beyond the active approval queue." : "Consent posture is now closed out of active approval triage.")
          : "Approval still needs attention in the active queue.";
        const approvalFollowUp = shouldRetire
          ? "Inspect the approval queue or item timeline to confirm downstream execution posture."
          : "Inspect the approval queue to finish the remaining consent decision.";
        return Object.assign(baseState, {{
          status: "success",
          summary: approvalSummaryBits.join(" · "),
          retired: shouldRetire,
          posture: approvalPosture,
          follow_up: approvalFollowUp,
          domain_kind: "approval",
          consequence_summary: shouldRetire
            ? `Approval consequence: ${{approvalOutcome}} closed active approval triage.`
            : `Approval consequence: ${{approvalOutcome}} still needs operator review.`,
        }});
      }}

      if (endpointText.includes("/api/assistant-core/notifications/")) {{
        const notificationOutcome = payloadStatus || payloadResolution || "updated";
        const notificationSummaryBits = [`Notification updated: ${{notificationOutcome}}`];
        if (payloadDetail) notificationSummaryBits.push(payloadDetail);
        const shouldRetire = ["opened", "ignored", "dismissed", "read"].some((token) => notificationOutcome.includes(token));
        const notificationPosture = shouldRetire
          ? "Notification is no longer waiting in the active surfaced inbox lane."
          : "Notification still needs inbox review.";
        const notificationFollowUp = shouldRetire
          ? "Inspect the notification snapshot or related detail pane to confirm the updated inbox state."
          : "Inspect the surfaced notification and decide whether to open or dismiss it.";
        return Object.assign(baseState, {{
          status: "success",
          summary: notificationSummaryBits.join(" · "),
          retired: shouldRetire,
          posture: notificationPosture,
          follow_up: notificationFollowUp,
          domain_kind: "notification",
          consequence_summary: shouldRetire
            ? `Notification consequence: ${{notificationOutcome}} cleared the surfaced inbox item.`
            : `Notification consequence: ${{notificationOutcome}} still needs inbox review.`,
        }});
      }}

      if (endpointText.includes("/api/open-loops/action")) {{
        const actionName = String((payload && payload.action) || payloadStatus || payloadResolution || "acted").trim().toLowerCase();
        const domain = String((payload && payload.domain) || "").trim().toLowerCase();
        const record = payload && payload.record && typeof payload.record === "object" ? payload.record : {{}};
        const nestedRecord = record && record.record && typeof record.record === "object" ? record.record : {{}};
        const recordStatus = String(record.status || record.result || record.resolution || record.outcome || nestedRecord.status || nestedRecord.result || nestedRecord.resolution || nestedRecord.outcome || "").trim().toLowerCase();
        const recordDetail = String(record.detail || record.message || record.reason || nestedRecord.detail || nestedRecord.message || nestedRecord.reason || "").trim();
        const openLoopItems = Array.isArray(payload && payload.open_loops && payload.open_loops.items) ? payload.open_loops.items : [];
        const hasLiveOpenLoopSnapshot = Array.isArray(openLoopItems) && openLoopItems.length > 0;
        const stillVisible = hasLiveOpenLoopSnapshot
          ? openLoopItems.some((item) =>
              String((item && item.item_id) || "").trim() === requestId
              && String((item && item.domain) || "").trim().toLowerCase() === domain
            )
          : true;
        const shouldRetire = hasLiveOpenLoopSnapshot ? !stillVisible : Boolean(baseState.retired);
        const openLoopSummaryBits = [`Open loop updated: ${{actionName || "acted"}}`];
        if (domain) openLoopSummaryBits.push(`domain=${{domain}}`);
        if (requestId) openLoopSummaryBits.push(`item=${{requestId}}`);
        if (recordStatus) openLoopSummaryBits.push(`status=${{recordStatus}}`);
        if (payloadDetail) openLoopSummaryBits.push(payloadDetail);
        else if (recordDetail) openLoopSummaryBits.push(recordDetail);
        if (hasLiveOpenLoopSnapshot) {{
          openLoopSummaryBits.push(
            shouldRetire ? "No longer in active open loops." : "Still active in open loops."
          );
        }}
        const openLoopPosture = shouldRetire
          ? "This work item left the active open-loop queue."
          : "This work item still needs active open-loop review.";
        const openLoopFollowUp = shouldRetire
          ? "Inspect the item timeline or related journal context to confirm the new workstream posture."
          : "Inspect the open-loop detail to decide the next workstream move.";
        return Object.assign(baseState, {{
          status: "success",
          summary: openLoopSummaryBits.join(" · "),
          retired: shouldRetire,
          posture: openLoopPosture,
          follow_up: openLoopFollowUp,
          domain_kind: "open-loop",
          consequence_summary: shouldRetire
            ? `Open-loop consequence: ${{actionName || "acted"}} removed the item from active open loops.`
            : `Open-loop consequence: ${{actionName || "acted"}} kept the item active in open loops.`,
        }});
      }}

      return Object.assign(baseState, {{
        status: "success",
        summary: `Action succeeded: ${{actionResultSummary({{ endpoint, result: payload }})}}`,
        retired: Boolean(baseState.retired),
        domain_kind: "generic",
        consequence_summary: `Generic consequence: ${{actionResultSummary({{ endpoint, result: payload }})}}`,
      }});
    }}

    function changeEvidenceSummary(before, after, context) {{
      const changed = [];
      if ((before.status || "") !== (after.status || "")) changed.push("status changed");
      if ((before.last_decision_summary || "") !== (after.last_decision_summary || "")) changed.push("decision summary changed");
      if ((before.next_action || "") !== (after.next_action || "")) changed.push("next action changed");
      if ((before.next_review_at || "") !== (after.next_review_at || "")) changed.push("review timing changed");
      if ((before.decision_history || []).length !== (after.decision_history || []).length) changed.push("decision history length changed");
      if ((before.recent_trace || []).length !== (after.recent_trace || []).length) changed.push("recent trace length changed");
      if (changed.length) return changed.join("; ");
      const endpoint = context && context.endpoint ? `after ${{context.endpoint}}` : "after refresh";
      return `No visible tracked fields changed ${{endpoint}}.`;
    }}

    function summarizeDetailDiff(before, after, context) {{
      const changes = [];
      if ((before.status || "") !== (after.status || "")) {{
        changes.push(`status: ${{before.status || "unknown"}} -> ${{after.status || "unknown"}}`);
      }}
      if ((before.last_decision_summary || "") !== (after.last_decision_summary || "")) {{
        changes.push(`decision: ${{before.last_decision_summary || "none"}} -> ${{after.last_decision_summary || "none"}}`);
      }}
      if ((before.next_action || "") !== (after.next_action || "")) {{
        changes.push(`next action updated to ${{after.next_action || "none"}}`);
      }}
      if ((before.next_review_at || "") !== (after.next_review_at || "")) {{
        changes.push(`review time: ${{before.next_review_at || "none"}} -> ${{after.next_review_at || "none"}}`);
      }}
      if (!changes.length) {{
        const endpoint = context && context.endpoint ? ` after ${{context.endpoint}}` : "";
        return `Refreshed${{endpoint}}; no visible detail fields changed yet.`;
      }}
      return changes.join("; ");
    }}

    function notificationPreviewHtml(payload) {{
      const summary = payload.summary || {{}};
      const items = Array.isArray(payload.items) ? payload.items.slice(0, 5) : [];
      const recentEvents = items
        .map((item) => item.title || item.why_this_surfaced_now || "notification")
        .filter(Boolean);
      const eventDisplay = recentEvents.length ? recentEvents.join("; ") : "No recent event signals captured.";
      const itemRows = items.length
        ? items.map((item) => {{
            const notificationId = String(item.notification_id || "");
            const actions = Object.assign({{}}, item.actions || {{}});
            if (notificationId) {{
              actions.open ||= `/api/assistant-core/notifications/${{notificationId}}`;
              actions.ignore ||= `/api/assistant-core/notifications/${{notificationId}}`;
            }}
            const buttons = notificationId
              ? `
                <div class="action-row">
                  <button type="button" data-endpoint="${{esc(actions.open || "")}}" data-method="POST" data-body='{{"actor":"Chris","status":"opened"}}'>Open</button>
                  <button type="button" data-endpoint="${{esc(actions.ignore || "")}}" data-method="POST" data-body='{{"actor":"Chris","status":"ignored"}}'>Ignore</button>
                </div>
              `
              : "";
            return `
              <li class="needs-action">
                <strong>${{esc(item.title || "Notification")}}</strong>
                <span>${{esc(item.why_this_surfaced_now || "JARVIS surfaced this for operator review.")}}</span>
                <code>${{esc(item.status || "")}} / ${{esc(item.priority_class || "")}}</code>
                <div class="action-row">
                  <button type="button" data-detail-kind="notification" data-detail-index="${{esc(items.indexOf(item))}}">Inspect</button>
                </div>
                ${{buttons}}
              </li>
            `;
          }}).join("")
        : "<li class='empty'>No live notifications yet.</li>";
      return [
        `<li><strong>Total Inbox</strong><span>${{esc((summary.total ?? 0))}} surfaced item(s)</span></li>`,
        `<li><strong>Unread</strong><span>${{esc((summary.unread ?? 0))}} unread item(s)</span></li>`,
        `<li><strong>Event Signals</strong><span>${{esc(recentEvents.length)}} recent event signal(s)</span></li>`,
        `<li><strong>Live Notifications</strong><span>Use the inline inbox controls when items are available.</span></li>`,
        itemRows,
        `<li><strong>Recent Events</strong><span>${{esc(eventDisplay)}}</span></li>`,
      ].join("");
    }}

    function openLoopDetailAt(index) {{
      const payload = latestOpenLoopsPayload || {{}};
      const items = Array.isArray(payload.items) ? payload.items : [];
      const item = items[Number(index)] || null;
      if (!item) {{
        return {{
          source_kind: "none",
          title: "No item selected",
          summary: "Select an open loop or notification to inspect deeper detail.",
          domain: "general",
          status: "idle",
          owner_agent: "command-center",
          next_action: "Choose a surfaced item.",
          next_review_at: "not scheduled",
          autonomy_summary: "No active item selected.",
          available_actions: [],
          why_now: "The detail inspector activates when JARVIS has a live item to inspect.",
          evidence_lines: ["No evidence captured because no live item is currently selected."],
          decision_history: [],
          item_timeline: [],
          last_decision_summary: "No prior decision attached.",
          action_result_summary: "No action result captured yet.",
          change_evidence_summary: "No post-action evidence captured yet.",
          recent_trace: [],
        }};
      }}
      const domain = item.domain || "general";
      const title = item.title || item.kind || "Open loop";
      const approvalsPayload = latestApprovalsPayload || {{}};
      const approvalHistory = Array.isArray(approvalsPayload.history) ? approvalsPayload.history : [];
      const pendingApprovals = Array.isArray(approvalsPayload.pending) ? approvalsPayload.pending : [];
      const matchingHistory = approvalHistory.filter((decision) => {{
        const requestId = String(item.item_id || "");
        return (requestId && String(decision.request_id || "") === requestId)
          || String(decision.title || "").toLowerCase().includes(String(title).toLowerCase());
      }}).slice(0, 3).map((decision) => ({{
        request_id: decision.request_id || item.item_id || "",
        status: decision.status || "unknown",
        actor: decision.approved_by || decision.actor_id || "-",
        when: decision.approved_at || decision.executed_at || decision.requested_at || "unknown time",
        resolution: ((decision.supervision_decision || {{}}).resolution) || "unclassified",
      }}));
      const matchingPending = pendingApprovals.find((candidate) => {{
        const requestId = String(item.item_id || "").trim();
        const candidateId = String(candidate.request_id || "").trim();
        const candidateTitle = String(candidate.title || "").trim().toLowerCase();
        return (requestId && candidateId === requestId)
          || (candidateTitle && String(title).toLowerCase().includes(candidateTitle))
          || (candidateTitle && candidateTitle.includes(String(title).toLowerCase()));
      }}) || null;
      const lastDecision = matchingHistory[0] || null;
      const trace = (Array.isArray(latestActivityPayload) ? latestActivityPayload : []).filter((activity) => {{
        const activityTitle = String(activity.title || "").toLowerCase();
        const activitySubtitle = String(activity.subtitle || "").toLowerCase();
        return activityTitle.includes(String(title).toLowerCase()) || activitySubtitle.includes(String(domain).toLowerCase());
      }}).slice(0, 3).map((activity) => ({{
        title: activity.title || "Activity",
        detail: activity.subtitle || activity.result || "Recent activity signal.",
        timestamp: activity.timestamp || "",
      }}));
      const itemTimeline = buildItemTimeline([
        {{
          kind: "open-loop",
          title,
          detail: item.summary || item.next_action || "Open loop surfaced for review.",
          timestamp: item.updated_at || item.created_at || item.next_review_at || "",
        }},
        ...matchingHistory.map((decision) => ({{
          kind: "decision",
          title: decision.status || "decision",
          detail: `${{decision.resolution || "unclassified"}} by ${{decision.actor || "-"}}`,
          timestamp: decision.when || "",
        }})),
        ...trace.map((activity) => ({{
          kind: "trace",
          title: activity.title || "Activity",
          detail: activity.detail || "Recent activity signal.",
          timestamp: activity.timestamp || "",
        }})),
      ]);
      return {{
        source_kind: "open-loop",
        item_id: item.item_id || "",
        request_id: item.item_id || "",
        title,
        summary: item.summary || "JARVIS surfaced a live open-loop item.",
        domain,
        status: item.status || "open",
        owner_agent: item.owner_agent || "JARVIS",
        next_action: item.next_action || "No next action captured.",
        next_review_at: item.next_review_at || "not scheduled",
        autonomy_summary: ((item.auto_execution || {{}}).summary) || "Review required.",
        available_actions: Array.isArray(item.available_actions) ? item.available_actions : [],
        why_now: item.summary || item.next_action || "JARVIS surfaced this open loop for review.",
        evidence_lines: [
          `Owner agent: ${{item.owner_agent || "JARVIS"}}`,
          `Review schedule: ${{item.next_review_at || "not scheduled"}}`,
          `Autonomy posture: ${{((item.auto_execution || {{}}).summary) || "Review required."}}`,
        ],
        decision_history: matchingHistory,
        item_timeline: itemTimeline,
        approval_review_context: matchingPending ? {{
          request_id: matchingPending.request_id || item.item_id || "",
          risk_tier: matchingPending.risk_tier || item.status || "pending",
          agent_label: matchingPending.agent_label || item.owner_agent || "approval-queue",
          description: matchingPending.description || item.summary || "Pending approval needs operator review.",
        }} : {{}},
        last_decision_summary: lastDecision
          ? `${{lastDecision.status || "unknown"}} by ${{lastDecision.actor || "-"}}`
          : "No prior decision attached.",
        action_result_summary: "No action result captured yet.",
        change_evidence_summary: "No post-action evidence captured yet.",
        recent_trace: trace,
      }};
    }}

    function notificationDetailAt(index) {{
      const payload = latestNotificationsPayload || {{}};
      const items = Array.isArray(payload.items) ? payload.items : [];
      const item = items[Number(index)] || null;
      if (!item) return openLoopDetailAt(-1);
      const title = item.title || "Notification";
      const trace = (Array.isArray(latestActivityPayload) ? latestActivityPayload : []).filter((activity) => {{
        const activityTitle = String(activity.title || "").toLowerCase();
        return activityTitle.includes(String(title).toLowerCase());
      }}).slice(0, 3).map((activity) => ({{
        title: activity.title || "Activity",
        detail: activity.subtitle || activity.result || "Recent activity signal.",
        timestamp: activity.timestamp || "",
      }}));
      const itemTimeline = buildItemTimeline([
        {{
          kind: "notification",
          title,
          detail: item.why_this_surfaced_now || "Notification surfaced for operator review.",
          timestamp: item.updated_at || item.created_at || "",
        }},
        ...trace.map((activity) => ({{
          kind: "trace",
          title: activity.title || "Activity",
          detail: activity.detail || "Recent activity signal.",
          timestamp: activity.timestamp || "",
        }})),
      ]);
      return {{
        source_kind: "notification",
        notification_id: item.notification_id || "",
        notification_actions: Object.assign({{}}, item.actions || {{}}),
        title,
        summary: item.why_this_surfaced_now || "JARVIS surfaced this for operator review.",
        domain: "assistant-core",
        status: item.status || "unseen",
        owner_agent: "notification-feed",
        next_action: "Open or ignore this surfaced notification.",
        next_review_at: "now",
        autonomy_summary: "Operator review required before the notification is cleared.",
        available_actions: [
          {{ id: "open", label: "Open" }},
          {{ id: "ignore", label: "Ignore" }},
        ],
        why_now: item.why_this_surfaced_now || "Recent runtime pressure surfaced this notification.",
        evidence_lines: [
          `Notification status: ${{item.status || "unseen"}}`,
          `Priority class: ${{item.priority_class || "normal"}}`,
          "Operator review is required before this surfaced notification is cleared.",
        ],
        decision_history: [],
        item_timeline: itemTimeline,
        last_decision_summary: "No prior approval decision attached.",
        action_result_summary: "No action result captured yet.",
        change_evidence_summary: "No post-action evidence captured yet.",
        recent_trace: trace,
      }};
    }}

    function findOpenLoopIndexForJournalEntry(item) {{
      const payload = latestOpenLoopsPayload || {{}};
      const items = Array.isArray(payload.items) ? payload.items : [];
      const relatedLabel = String(item.related_label || item.title || "").trim().toLowerCase();
      const title = String(item.title || "").trim().toLowerCase();
      return items.findIndex((candidate) => {{
        const parts = [
          candidate.title,
          candidate.kind,
          candidate.summary,
          candidate.next_action,
          candidate.item_id,
        ].map((value) => String(value || "").trim().toLowerCase()).filter(Boolean);
        return parts.some((part) => (
          (relatedLabel && (part.includes(relatedLabel) || relatedLabel.includes(part)))
          || (title && (part.includes(title) || title.includes(part)))
        ));
      }});
    }}

    function findNotificationIndexForJournalEntry(item) {{
      const payload = latestNotificationsPayload || {{}};
      const items = Array.isArray(payload.items) ? payload.items : [];
      const relatedLabel = String(item.related_label || item.title || "").trim().toLowerCase();
      const title = String(item.title || "").trim().toLowerCase();
      return items.findIndex((candidate) => {{
        const parts = [
          candidate.title,
          candidate.why_this_surfaced_now,
          candidate.notification_id,
        ].map((value) => String(value || "").trim().toLowerCase()).filter(Boolean);
        return parts.some((part) => (
          (relatedLabel && (part.includes(relatedLabel) || relatedLabel.includes(part)))
          || (title && (part.includes(title) || title.includes(part)))
        ));
      }});
    }}

    function findOpenLoopIndexForNeed(item) {{
      const payload = latestOpenLoopsPayload || {{}};
      const items = Array.isArray(payload.items) ? payload.items : [];
      const title = String(item.title || "").trim().toLowerCase();
      const detail = String(item.detail || "").trim().toLowerCase();
      return items.findIndex((candidate) => {{
        const parts = [
          candidate.title,
          candidate.kind,
          candidate.summary,
          candidate.next_action,
          candidate.item_id,
          candidate.domain,
        ].map((value) => String(value || "").trim().toLowerCase()).filter(Boolean);
        return parts.some((part) => (
          (title && (part.includes(title) || title.includes(part)))
          || (detail && (part.includes(detail) || detail.includes(part)))
        ));
      }});
    }}

    function findNotificationIndexForNeed(item) {{
      const payload = latestNotificationsPayload || {{}};
      const items = Array.isArray(payload.items) ? payload.items : [];
      const title = String(item.title || "").trim().toLowerCase();
      const detail = String(item.detail || "").trim().toLowerCase();
      return items.findIndex((candidate) => {{
        const parts = [
          candidate.title,
          candidate.why_this_surfaced_now,
          candidate.notification_id,
          candidate.status,
        ].map((value) => String(value || "").trim().toLowerCase()).filter(Boolean);
        return parts.some((part) => (
          (title && (part.includes(title) || title.includes(part)))
          || (detail && (part.includes(detail) || detail.includes(part)))
        ));
      }});
    }}

    function findJournalIndexForNeed(item) {{
      const entries = buildActionJournalEntries(latestApprovalsPayload || {{}}, Array.isArray(latestActivityPayload) ? latestActivityPayload : []);
      const title = String(item.title || "").trim().toLowerCase();
      const detail = String(item.detail || "").trim().toLowerCase();
      return entries.findIndex((entry) => {{
        const parts = [
          entry.title,
          entry.detail,
          entry.related_label,
          entry.kind,
          entry.status,
        ].map((value) => String(value || "").trim().toLowerCase()).filter(Boolean);
        return parts.some((part) => (
          (title && (part.includes(title) || title.includes(part)))
          || (detail && (part.includes(detail) || detail.includes(part)))
        ));
      }});
    }}

    function jumpToNeedContext(index) {{
      const cockpit = currentNeedsCockpit();
      const item = (Array.isArray(cockpit.items) ? cockpit.items : [])[Number(index)] || null;
      return focusNeedItem(item);
    }}

    function currentNeedsCockpit() {{
      return reconcileNeedsActionState(buildNeedsCockpit(
        latestSupervisionPayload || {{}},
        latestApprovalsPayload || {{}},
        latestOpenLoopsPayload || {{}},
        latestNotificationsPayload || {{}},
        Array.isArray(latestActivityPayload) ? latestActivityPayload : [],
      ));
    }}

    function currentSeamTracker() {{
      return (latestCommandCenterPayload && latestCommandCenterPayload.seam_tracker && typeof latestCommandCenterPayload.seam_tracker === "object")
        ? latestCommandCenterPayload.seam_tracker
        : {{}};
    }}

    function currentProgressDashboard() {{
      return (latestCommandCenterPayload && latestCommandCenterPayload.progress_dashboard && typeof latestCommandCenterPayload.progress_dashboard === "object")
        ? latestCommandCenterPayload.progress_dashboard
        : {{}};
    }}

    function currentCoreModules() {{
      return (latestCommandCenterPayload && latestCommandCenterPayload.core_modules && typeof latestCommandCenterPayload.core_modules === "object")
        ? latestCommandCenterPayload.core_modules
        : {{}};
    }}

    function currentMissionTaskBoard() {{
      return (latestCommandCenterPayload && latestCommandCenterPayload.mission_task_board && typeof latestCommandCenterPayload.mission_task_board === "object")
        ? latestCommandCenterPayload.mission_task_board
        : {{}};
    }}

    function currentAgentOpsRoster() {{
      return (latestCommandCenterPayload && latestCommandCenterPayload.agent_ops_roster && typeof latestCommandCenterPayload.agent_ops_roster === "object")
        ? latestCommandCenterPayload.agent_ops_roster
        : {{}};
    }}

    function agentDetailAt(index) {{
      const roster = currentAgentOpsRoster();
      const item = (Array.isArray(roster.items) ? roster.items : [])[Number(index)] || null;
      if (!item) return openLoopDetailAt(-1);
      const missionRoles = Array.isArray(item.mission_roles) ? item.mission_roles.filter(Boolean) : [];
      return {{
        source_kind: "agent-ops-roster",
        title: item.name || "Agent",
        summary: item.purpose || "No purpose recorded.",
        domain: item.domain || "general",
        status: item.status || "unknown",
        owner_agent: item.agent_id || "agent",
        next_action: item.attention_reason || `Inspect ${{String(item.assignment || "assignment").trim()}} lane readiness.`,
        next_review_at: item.last_activity || "not scheduled",
        autonomy_summary: `Agent maturity: ${{String(item.maturity || "Wired").trim()}} / authority: ${{String(item.authority_stage || "draft").trim()}}.`,
        available_actions: [],
        why_now: item.attention_reason || roster.summary || "Current agent runtime posture from registry and kernel state.",
        evidence_lines: [
          `Assignment: ${{String(item.assignment || "unassigned").trim()}}`,
          `Module: ${{String(item.module || "general").trim()}}`,
          `Heartbeat: ${{String(item.heartbeat_status || "unknown").trim()}}`,
          `Mission roles: ${{missionRoles.join(", ") || "none recorded"}}`,
          `Authority stage: ${{String(item.authority_stage || "draft").trim()}}`,
        ],
        last_decision_summary: item.purpose || "No agent summary recorded.",
        recent_trace: [
          `Domain: ${{String(item.domain || "general").trim()}}`,
          `Last activity: ${{String(item.last_activity || "not recorded").trim()}}`,
          `Attention: ${{String(item.attention_reason || "none recorded").trim()}}`,
        ],
        item_timeline: recentNeedsMotion.slice(0, 3),
        change_summary: `Inspected agent ops record: ${{String(item.name || "agent").trim()}}.`,
        change_evidence_summary: String(item.attention_reason || item.last_activity || "No further agent ops evidence captured.").trim(),
      }};
    }}

    function missionDetailAt(index) {{
      const board = currentMissionTaskBoard();
      const item = (Array.isArray(board.items) ? board.items : [])[Number(index)] || null;
      if (!item) return openLoopDetailAt(-1);
      const selectedAgents = Array.isArray(item.selected_agents) ? item.selected_agents.filter(Boolean) : [];
      const taskAgents = Array.isArray(item.task_agent_labels) ? item.task_agent_labels.filter(Boolean) : [];
      return {{
        source_kind: "mission-task-board",
        title: item.title || "Mission",
        summary: item.brief || "No mission brief captured yet.",
        domain: item.primary_domain || "general",
        status: item.status || "active",
        owner_agent: item.owner_agent || "jarvis-orchestrator",
        next_action: item.next_step || "Review mission brief",
        next_review_at: item.updated_at || "not scheduled",
        autonomy_summary: `Mission lane: ${{String(item.lane || "next").trim()}} with ${{Number(item.active_count || 0)}} active subtask(s).`,
        available_actions: [],
        why_now: item.what_became_real || board.summary || "Current mission posture from the mission store.",
        evidence_lines: [
          `Mission ID: ${{String(item.mission_id || "not recorded").trim()}}`,
          `Lane: ${{String(item.lane || "next").trim()}}`,
          `Selected agents: ${{selectedAgents.join(", ") || "none assigned"}}`,
          `Task agents: ${{taskAgents.join(", ") || "none staged"}}`,
          `Subtasks: ${{Number(item.subtask_count || 0)}} total / ${{Number(item.active_count || 0)}} active / ${{Number(item.blocked_count || 0)}} blocked / ${{Number(item.completed_count || 0)}} completed`,
        ],
        last_decision_summary: item.what_became_real || "No mission decision summary captured.",
        recent_trace: [
          `Primary domain: ${{String(item.primary_domain || "general").trim()}}`,
          `Owner agent: ${{String(item.owner_agent || "jarvis-orchestrator").trim()}}`,
          `Remaining partial: ${{String(item.remains_partial || "none recorded").trim()}}`,
        ],
        item_timeline: recentNeedsMotion.slice(0, 3),
        change_summary: `Inspected mission board item: ${{String(item.title || "mission").trim()}}.`,
        change_evidence_summary: String(item.remains_partial || item.next_step || "No remaining mission detail captured.").trim(),
      }};
    }}

    function seamDetailAt(index) {{
      const tracker = currentSeamTracker();
      const item = (Array.isArray(tracker.items) ? tracker.items : [])[Number(index)] || null;
      if (!item) return openLoopDetailAt(-1);
      const roadmapAreas = Array.isArray(item.roadmap_areas) ? item.roadmap_areas.filter(Boolean) : [];
      const substrate = Array.isArray(item.substrate) ? item.substrate.filter(Boolean) : [];
      const tests = Array.isArray(item.tests) ? item.tests.filter(Boolean) : [];
      return {{
        source_kind: "seam-tracker",
        title: item.name || "Seam",
        summary: item.what_became_real || "No seam outcome recorded yet.",
        domain: item.module || "progress",
        status: item.status || "wired",
        owner_agent: "command-center",
        next_action: item.remains_partial || "No follow-up captured.",
        next_review_at: item.commit_status || "not scheduled",
        autonomy_summary: `Seam maturity: ${{String(item.maturity || item.status || "Wired").trim()}}.`,
        available_actions: [],
        why_now: item.commit_status || tracker.summary || "Current seam posture from the working lane.",
        evidence_lines: [
          `Roadmap areas: ${{roadmapAreas.join(", ") || "not tagged"}}`,
          `Substrate: ${{substrate.join(", ") || "not tagged"}}`,
          `Branch/worktree: ${{String(item.branch || "unknown branch").trim()}} / ${{String(item.worktree || "unknown worktree").trim()}}`,
          `Commit posture: ${{String(item.commit_status || "not recorded").trim()}}`,
          `Tests: ${{tests.join(", ") || "no tests recorded"}}`,
        ],
        last_decision_summary: item.what_became_real || "No seam decision captured.",
        recent_trace: [
          `Visible module: ${{String(item.module || "Progress").trim()}}`,
          `Surface path: ${{String(item.surface_path || "/command-center").trim()}}`,
          `Remaining partial: ${{String(item.remains_partial || "none recorded").trim()}}`,
        ],
        item_timeline: recentNeedsMotion.slice(0, 3),
        change_summary: `Inspected seam tracker item: ${{String(item.name || "seam").trim()}}.`,
        change_evidence_summary: String(item.remains_partial || item.commit_status || "No remaining seam detail captured.").trim(),
      }};
    }}

    function progressDetailAt(index) {{
      const board = currentProgressDashboard();
      const item = (Array.isArray(board.items) ? board.items : [])[Number(index)] || null;
      if (!item) return openLoopDetailAt(-1);
      const readinessCounts = board && board.counts && typeof board.counts === "object"
        ? Object.entries(board.counts).map(([key, value]) => `${{key}}=${{value}}`).join(", ")
        : "none recorded";
      return {{
        source_kind: "progress-dashboard",
        title: item.module || "Progress Module",
        summary: item.summary || "No progress readiness summary captured yet.",
        domain: "progress",
        status: item.status || "wired",
        owner_agent: "command-center",
        next_action: `Advance ${{String(item.module || "this module").trim()}} beyond ${{String(item.status_label || "wired").trim()}} readiness.`,
        next_review_at: "next command-center slice",
        autonomy_summary: `Roadmap level: ${{String(item.roadmap_level || "Level 3").trim()}}.`,
        available_actions: [],
        why_now: item.evidence || board.summary || "Current Level 3 progress posture from the live lane.",
        evidence_lines: [
          `Readiness label: ${{String(item.status_label || "wired").trim()}}`,
          `Roadmap level: ${{String(item.roadmap_level || "Level 3").trim()}}`,
          `Evidence: ${{String(item.evidence || "not recorded").trim()}}`,
          `Dashboard counts: ${{readinessCounts || "none recorded"}}`,
        ],
        last_decision_summary: item.summary || "No progress decision captured.",
        recent_trace: [
          `Module: ${{String(item.module || "Progress Module").trim()}}`,
          `Status: ${{String(item.status || "Wired").trim()}}`,
          `Evidence source: ${{String(item.evidence || "not recorded").trim()}}`,
        ],
        item_timeline: recentNeedsMotion.slice(0, 3),
        change_summary: `Inspected progress dashboard item: ${{String(item.module || "progress module").trim()}}.`,
        change_evidence_summary: String(item.evidence || item.summary || "No progress evidence captured yet.").trim(),
      }};
    }}

    function moduleDetailAt(index) {{
      const board = currentCoreModules();
      const item = (Array.isArray(board.items) ? board.items : [])[Number(index)] || null;
      if (!item) return openLoopDetailAt(-1);
      return {{
        source_kind: "core-modules",
        title: item.title || "Module",
        summary: item.what_became_real || item.summary || "No module summary captured yet.",
        domain: "modules",
        status: item.status || "wired",
        owner_agent: "command-center",
        next_action: item.remains_partial || "No follow-up captured.",
        next_review_at: item.api_path || "not scheduled",
        autonomy_summary: `Module readiness: ${{String(item.status_label || item.status || "wired").trim()}}.`,
        available_actions: [],
        why_now: item.evidence || board.summary || "Current module posture from the command center.",
        evidence_lines: [
          `Screen path: ${{String(item.screen_path || "/command-center").trim()}}`,
          `Screen kind: ${{String(item.screen_kind || "screen").trim()}}`,
          `API path: ${{String(item.api_path || "/api/command-center").trim()}}`,
          `Roadmap level: ${{String(item.roadmap_level || "Level 3").trim()}}`,
        ],
        last_decision_summary: item.what_became_real || "No module decision captured.",
        recent_trace: [
          `Visible module: ${{String(item.title || "Module").trim()}}`,
          `Evidence: ${{String(item.evidence || "not recorded").trim()}}`,
          `Remaining partial: ${{String(item.remains_partial || "none recorded").trim()}}`,
        ],
        item_timeline: recentNeedsMotion.slice(0, 3),
        change_summary: `Inspected core module: ${{String(item.title || "module").trim()}}.`,
        change_evidence_summary: String(item.remains_partial || item.evidence || item.summary || "No module evidence captured yet.").trim(),
      }};
    }}

    function focusNeedItem(item) {{
      if (!item) {{
        const fallback = selectedDetail();
        fallback.change_summary = "Needs Me Now selection could not be resolved.";
        fallback.change_evidence_summary = "The requested triage item was not available in the current cockpit snapshot.";
        return fallback;
      }}
      const focusTargets = Array.isArray(item.focus_targets) ? item.focus_targets : [];
      for (const target of focusTargets) {{
        if (target === "notification") {{
          const notificationIndex = findNotificationIndexForNeed(item);
          if (notificationIndex >= 0) {{
            currentDetailSelection = {{ kind: "notification", index: notificationIndex }};
            const detail = notificationDetailAt(notificationIndex);
            detail.change_summary = "Focused notification context from Needs Me Now.";
            detail.change_evidence_summary = `Resolved from triage item: ${{item.title || "notification"}}.`;
            return detail;
          }}
        }}
        if (target === "open-loop") {{
          const openLoopIndex = findOpenLoopIndexForNeed(item);
          if (openLoopIndex >= 0) {{
            currentDetailSelection = {{ kind: "open-loop", index: openLoopIndex }};
            const detail = openLoopDetailAt(openLoopIndex);
            detail.change_summary = "Focused open-loop context from Needs Me Now.";
            detail.change_evidence_summary = `Resolved from triage item: ${{item.title || "open loop"}}.`;
            return detail;
          }}
        }}
        if (target === "journal") {{
          const journalIndex = findJournalIndexForNeed(item);
          if (journalIndex >= 0) {{
            currentDetailSelection = {{ kind: "journal", index: journalIndex }};
            const detail = journalDetailAt(journalIndex);
            detail.change_summary = "Focused action journal context from Needs Me Now.";
            detail.change_evidence_summary = `Resolved from triage item: ${{item.title || "journal item"}}.`;
            return detail;
          }}
        }}
      }}
      const fallback = selectedDetail();
      fallback.change_summary = `No live detail target found for "${{item.title || "selected need"}}".`;
      fallback.change_evidence_summary = `Tried focus targets: ${{focusTargets.join(", ") || "none"}}.`;
      return fallback;
    }}

    function jumpToNeedContextByKey(needKey) {{
      const normalizedKey = String(needKey || "").trim();
      const cockpit = currentNeedsCockpit();
      const candidates = [
        ...(Array.isArray(cockpit.items) ? cockpit.items : []),
        ...(Array.isArray(cockpit.retired_items) ? cockpit.retired_items : []),
      ];
      const item = candidates.find((entry) => String((entry && entry.need_key) || "").trim() === normalizedKey) || null;
      return focusNeedItem(item);
    }}

    function selectedDetail() {{
      if ((currentDetailSelection || {{}}).kind === "agent") {{
        return agentDetailAt((currentDetailSelection || {{}}).index || 0);
      }}
      if ((currentDetailSelection || {{}}).kind === "mission") {{
        return missionDetailAt((currentDetailSelection || {{}}).index || 0);
      }}
      if ((currentDetailSelection || {{}}).kind === "seam") {{
        return seamDetailAt((currentDetailSelection || {{}}).index || 0);
      }}
      if ((currentDetailSelection || {{}}).kind === "progress") {{
        return progressDetailAt((currentDetailSelection || {{}}).index || 0);
      }}
      if ((currentDetailSelection || {{}}).kind === "module") {{
        return moduleDetailAt((currentDetailSelection || {{}}).index || 0);
      }}
      if ((currentDetailSelection || {{}}).kind === "journal") {{
        return journalDetailAt((currentDetailSelection || {{}}).index || 0);
      }}
      if ((currentDetailSelection || {{}}).kind === "notification") {{
        return notificationDetailAt((currentDetailSelection || {{}}).index || 0);
      }}
      return openLoopDetailAt((currentDetailSelection || {{}}).index || 0);
    }}

    function journalDetailAt(index) {{
      const entries = buildActionJournalEntries(latestApprovalsPayload || {{}}, Array.isArray(latestActivityPayload) ? latestActivityPayload : []);
      const item = entries[Number(index)] || null;
      if (!item) return openLoopDetailAt(-1);
      const relatedKind = String(item.related_kind || "").trim();
      const relatedLabel = String(item.related_label || item.title || "").trim();
      return {{
        source_kind: "action-journal",
        title: item.title || "Recent action",
        summary: item.detail || "Recent action journal entry.",
        domain: item.kind || "activity",
        status: item.status || "observed",
        owner_agent: ["approval-history", "local-action", "home-action", "operator-action"].includes(String(item.kind || "")) ? "operator" : "runtime",
        next_action: "Inspect linked queue or follow-on surfaces if more action is needed.",
        next_review_at: item.timestamp || "not scheduled",
        autonomy_summary: ["approval-history", "local-action", "home-action", "operator-action"].includes(String(item.kind || "")) ? "Operator action recorded." : "Autonomous/runtime activity recorded.",
        available_actions: [],
        why_now: item.detail || "Recent action journal entry.",
        evidence_lines: [
          `Journal kind: ${{item.kind || "activity"}}`,
          `Recorded status: ${{item.status || "observed"}}`,
          `Related context: ${{relatedKind || "activity"}} / ${{relatedLabel || "Recent action"}}`,
        ],
        decision_history: [],
        item_timeline: buildItemTimeline([
          {{
            kind: "journal",
            title: item.title || "Recent action",
            detail: item.detail || "Recent runtime activity.",
            timestamp: item.timestamp || "",
          }},
          {{
            kind: "relation",
            title: relatedLabel || "Related context",
            detail: relatedKind ? `Related ${{relatedKind}} context available.` : "No explicit related context available.",
            timestamp: item.timestamp || "",
          }},
        ]),
        last_decision_summary: "See journal row for latest outcome.",
        change_summary: `Journal entry selected for inspection${{relatedKind ? `; related ${{relatedKind}} context available.` : "."}}`,
        action_result_summary: item.status || "observed",
        change_evidence_summary: item.detail || "Recent action journal entry.",
        field_delta_summary: "Journal entries do not compute field deltas.",
        contract_delta_summary: "Journal entries do not compute contract deltas.",
        derived_delta_summary: "Journal entries do not compute derived deltas.",
        recent_trace: [
          {{
            title: item.title || "Recent action",
            detail: item.detail || "Recent runtime activity.",
            timestamp: item.timestamp || "",
          }},
        ],
      }};
    }}

    function jumpToRelatedFromJournal(index) {{
      const entries = buildActionJournalEntries(latestApprovalsPayload || {{}}, Array.isArray(latestActivityPayload) ? latestActivityPayload : []);
      const item = entries[Number(index)] || null;
      if (!item) {{
        currentDetailSelection = {{ kind: "journal", index: Number(index) || 0 }};
        return journalDetailAt(index);
      }}
      const relatedKind = String(item.related_kind || "").trim();
      if (relatedKind === "notification") {{
        const relatedIndex = findNotificationIndexForJournalEntry(item);
        if (relatedIndex >= 0) {{
          currentDetailSelection = {{ kind: "notification", index: relatedIndex }};
          const detail = notificationDetailAt(relatedIndex);
          detail.change_summary = "Jumped from Action Journal into related notification context.";
          detail.change_evidence_summary = `Resolved from journal relation: ${{item.related_label || item.title || "Notification"}}.`;
          return detail;
        }}
      }}
      if (relatedKind === "open-loop") {{
        const relatedIndex = findOpenLoopIndexForJournalEntry(item);
        if (relatedIndex >= 0) {{
          currentDetailSelection = {{ kind: "open-loop", index: relatedIndex }};
          const detail = openLoopDetailAt(relatedIndex);
          detail.change_summary = "Jumped from Action Journal into related open-loop context.";
          detail.change_evidence_summary = `Resolved from journal relation: ${{item.related_label || item.title || "Open loop"}}.`;
          return detail;
        }}
      }}
      currentDetailSelection = {{ kind: "journal", index: Number(index) || 0 }};
      const detail = journalDetailAt(index);
      detail.change_summary = `No live related item found for ${{relatedKind || "activity"}} context.`;
      detail.change_evidence_summary = `Journal relation was ${{item.related_label || item.title || "unspecified"}}.`;
      return detail;
    }}

    function setDetailInspector(detail) {{
      if (!detailInspector) return;
      const selectedTimelineEvent = selectedTimelineEventForDetail(detail);
      const selectedTimelineEventDetail = selectedTimelineEventDetailForDetail(detail, selectedTimelineEvent);
      const payload = Object.assign(
        {{}},
        detail || {{}},
        {{
          selected_timeline_event: selectedTimelineEvent,
          selected_timeline_event_detail: selectedTimelineEventDetail,
          change_summary: (detail && detail.change_summary) || latestChangeSummary || "No action diff captured yet.",
          action_result_summary: (detail && detail.action_result_summary) || "No action result captured yet.",
          change_evidence_summary: (detail && detail.change_evidence_summary) || "No post-action evidence captured yet.",
          field_delta_summary: (detail && detail.field_delta_summary) || "No field deltas captured yet.",
          contract_delta_summary: (detail && detail.contract_delta_summary) || "No contract deltas captured yet.",
          derived_delta_summary: (detail && detail.derived_delta_summary) || "No derived deltas captured yet.",
        }},
      );
      detailInspector.innerHTML = detailInspectorHtml(payload);
      attachActionHandlers();
    }}

    function buildActionJournalEntries(approvals, activity) {{
      const approvalHistory = Array.isArray((approvals || {{}}).history) ? approvals.history : [];
      const approvalEntries = approvalHistory.slice(0, 4).map((item) => ({{
        kind: "approval-history",
        title: item.title || "Approval history entry",
        status: item.status || "unknown",
        detail: ((item.supervision_decision || {{}}).resolution) || item.approved_by || "Recent approval decision.",
        timestamp: item.approved_at || item.executed_at || item.requested_at || "",
        related_kind: "open-loop",
        related_label: item.title || "Related open loop",
      }}));
      const activityEntries = (Array.isArray(activity) ? activity : []).slice(0, 4).map((item) => ({{
        kind: item.entry_type || "activity",
        title: item.title || "Recent activity",
        status: item.result || "observed",
        detail: item.subtitle || "Recent runtime activity.",
        timestamp: item.timestamp || "",
        related_kind: item.subtitle ? "open-loop" : "activity",
        related_label: item.subtitle || item.title || "Related activity",
      }}));
      const localEntries = Array.isArray(recentLocalActions) ? recentLocalActions : [];
      return [...localEntries, ...approvalEntries, ...activityEntries]
        .sort((left, right) => String(right.timestamp || "").localeCompare(String(left.timestamp || "")));
    }}

    async function hydratePanels(options = {{}}) {{
      try {{
        const [commandCenterResponse, supervisionResponse, approvalResponse, activityResponse, registryResponse, briefingResponse, openLoopsResponse, notificationsResponse] = await Promise.all([
          fetch("/api/command-center"),
          fetch("/api/supervision-snapshot"),
          fetch("/api/approval-queue/snapshot"),
          fetch("/api/activity"),
          fetch("/api/agent-registry"),
          fetch("/api/briefing?actor=Chris"),
          fetch("/api/open-loops?actor=Chris"),
          fetch("/api/assistant-core/notifications?actor=Chris"),
        ]);
        const commandCenterPayload = await commandCenterResponse.json();
        const supervision = await supervisionResponse.json();
        const approvals = await approvalResponse.json();
        const activity = await activityResponse.json();
        const registryPayload = await registryResponse.json();
        const briefingPayload = await briefingResponse.json();
        const openLoopsPayload = await openLoopsResponse.json();
        const notificationsPayload = await notificationsResponse.json();
        latestCommandCenterPayload = commandCenterPayload || latestCommandCenterPayload || {{}};
        latestSupervisionPayload = supervision || {{}};
        latestApprovalsPayload = approvals || {{}};
        latestOpenLoopsPayload = openLoopsPayload || {{}};
        latestNotificationsPayload = notificationsPayload || {{}};
        latestActivityPayload = Array.isArray(activity) ? activity : [];
        if (homeOverview) {{
          homeOverview.innerHTML = homeOverviewHtml((commandCenterPayload || {{}}).home_overview || {{}}, (commandCenterPayload || {{}}).level3_checklist || {{}});
          attachActionHandlers();
        }}
        const liveCockpit = buildNeedsCockpit(
          supervision || {{}},
          approvals || {{}},
          openLoopsPayload || {{}},
          notificationsPayload || {{}},
          Array.isArray(activity) ? activity : [],
        );
        if (needsList) {{
          needsList.innerHTML = needsNowHtml(liveCockpit);
        }}
        refreshNeedsMotionPanel(liveCockpit, Array.isArray(activity) ? activity : []);
        if (missionTaskBoard) {{
          missionTaskBoard.innerHTML = missionTaskBoardHtml((commandCenterPayload || {{}}).mission_task_board || {{}});
        }}
        if (coreModules) {{
          coreModules.innerHTML = coreModulesHtml((commandCenterPayload || {{}}).core_modules || {{}});
        }}
        if (agentOpsRoster) {{
          agentOpsRoster.innerHTML = agentOpsRosterHtml((commandCenterPayload || {{}}).agent_ops_roster || {{}});
        }}
        if (progressDashboard) {{
          progressDashboard.innerHTML = progressDashboardHtml((commandCenterPayload || {{}}).progress_dashboard || {{}});
        }}
        const hostedDeployment = document.getElementById("hosted-deployment");
        if (hostedDeployment) {{
          hostedDeployment.innerHTML = hostedDeploymentHtml((commandCenterPayload || {{}}).hosted_deployment || {{}});
        }}
        if (approvalActions) {{
          const pending = Array.isArray(approvals.pending) ? approvals.pending : [];
          approvalActions.innerHTML = pending.length
            ? pending.map((item) => approvalItemHtml(item)).join("")
            : "<li class='empty'>No pending approvals right now.</li>";
          attachActionHandlers();
        }}
        if (memoryInspector) {{
          memoryInspector.innerHTML = memoryItemHtml(supervision.memory || {{}});
        }}
        if (briefPreview) {{
          const briefingText = String(briefingPayload.briefing || "").trim();
          const segments = briefingText
            ? briefingText.split(/\n+/).map((line) => line.trim()).filter(Boolean)
            : [];
          briefPreview.innerHTML = briefPreviewHtml({{
            actor: briefingPayload.actor || "Chris",
            headline: segments[0] || String((supervision.return_brief || {{}}).summary || "No briefing headline yet."),
            supporting_lines: segments.slice(1, 4),
            memory_entry_count: (supervision.memory || {{}}).entry_count || 0,
            live_news: Boolean(briefingPayload.live_news),
            rss_articles: Number(briefingPayload.rss_articles || 0),
            rss_sources: Array.isArray(briefingPayload.rss_sources) ? briefingPayload.rss_sources : [],
          }});
        }}
        if (timelinePreview) {{
          timelinePreview.innerHTML = timelinePreviewHtml(openLoopsPayload || {{}});
          attachActionHandlers();
        }}
        if (openLoopInspector) {{
          openLoopInspector.innerHTML = openLoopInspectorHtml(openLoopsPayload || {{}});
          attachActionHandlers();
        }}
        if (notificationPreview) {{
          notificationPreview.innerHTML = notificationPreviewHtml(notificationsPayload || {{}});
          attachActionHandlers();
        }}
        if (actionJournal) {{
          actionJournal.innerHTML = actionJournalHtml(buildActionJournalEntries(approvals, Array.isArray(activity) ? activity : []));
          attachActionHandlers();
        }}
        let afterDetail = selectedDetail();
        if (Number.isInteger(currentMotionArtifactIndex)) {{
          afterDetail = jumpToMotionArtifact(currentMotionArtifactIndex);
        }}
        if (pendingActionContext) {{
          const beforeDetail = pendingActionContext.beforeDetail || {{}};
          latestChangeSummary = summarizeDetailDiff(beforeDetail, afterDetail, pendingActionContext);
          afterDetail.action_result_summary = actionResultSummary(pendingActionContext);
          afterDetail.change_evidence_summary = changeEvidenceSummary(beforeDetail, afterDetail, pendingActionContext);
          afterDetail.approval_consequence_fields = approvalConsequenceFields(beforeDetail, afterDetail, pendingActionContext);
          afterDetail.approval_guidance_lines = approvalRemediationGuidance(beforeDetail, afterDetail, pendingActionContext);
          afterDetail.motion_artifact_focus_delta_summary = motionArtifactDeltaSummary(beforeDetail, afterDetail, pendingActionContext);
          afterDetail.motion_artifact_focus_delta_sections = motionArtifactDeltaSections(beforeDetail, afterDetail, pendingActionContext);
          afterDetail.motion_artifact_focus_excerpts = motionArtifactProofExcerpts(beforeDetail, afterDetail, pendingActionContext);
          afterDetail.motion_artifact_focus_proof_compare_summary = motionArtifactProofCompareSummary(beforeDetail, afterDetail, pendingActionContext);
          afterDetail.motion_artifact_focus_proof_compare_rows = motionArtifactProofCompareRows(beforeDetail, afterDetail, pendingActionContext);
          afterDetail.motion_artifact_focus_posture_hint = motionArtifactPostureHint(afterDetail, pendingActionContext);
          recordMotionArtifactHistory(afterDetail, pendingActionContext);
          applyMotionArtifactHistory(afterDetail);
          afterDetail.field_delta_summary = fieldDeltaSummary(beforeDetail, afterDetail);
          afterDetail.contract_delta_summary = contractDeltaSummary(beforeDetail, afterDetail);
          afterDetail.derived_delta_summary = derivedDeltaSummary(beforeDetail, afterDetail);
          pendingActionContext = null;
        }}
        const payloadHomeActionResult = (((commandCenterPayload || {{}}).home_overview || {{}}).action_result) || null;
        const actionResultOverride = options && options.homeActionResultOverride && typeof options.homeActionResultOverride === "object"
          ? options.homeActionResultOverride
          : null;
        if (actionResultOverride) {{
          latestHomeActionResult = Object.assign({{}}, actionResultOverride, {{
            summary: String(actionResultOverride.summary || actionResultOverride.label || "Home action completed.").trim(),
            detail: String(actionResultOverride.detail || latestChangeSummary || "Home action refreshed the current day posture.").trim(),
            route: String(actionResultOverride.route || "").trim(),
            route_label: String(actionResultOverride.route_label || "Open Related Surface").trim() || "Open Related Surface",
          }});
        }} else if (!latestHomeActionResult || String(latestHomeActionResult.source || "").trim() !== "live-home-action") {{
          latestHomeActionResult = payloadHomeActionResult;
        }}
        setDetailInspector(afterDetail);
        if (homeActionResult) {{
          homeActionResult.innerHTML = homeActionResultHtml(latestHomeActionResult || payloadHomeActionResult || {{}});
        }}
        if (activityFeed) {{
          activityFeed.innerHTML = activityItemHtml(buildVisibleActivityEntries(Array.isArray(activity) ? activity : []));
        }}
        if (agentRegistry) {{
          const registrySnapshot = {{
            agent_count: registryPayload.agent_count || registryPayload.core_agents || 0,
            domains: Array.isArray((registryPayload.contract || {{}}).domains) ? registryPayload.contract.domains : [],
            authority_stages: Array.isArray((registryPayload.contract || {{}}).authority_stages) ? registryPayload.contract.authority_stages : [],
            sample_contracts: Array.isArray(registryPayload.agents)
              ? registryPayload.agents.slice(0, 6).map((item) => ({{
                  label: item.label || item.agent_id || "",
                  agent_id: item.agent_id || "",
                  authority_stage: item.authority_stage || "",
                }}))
              : [],
            registry_error: "",
          }};
          agentRegistry.innerHTML = registryItemHtml(registrySnapshot);
        }}
        if (laneProgress) {{
          laneProgress.innerHTML = laneProgressHtml(supervision);
        }}
        if (seamTracker) {{
          seamTracker.innerHTML = seamTrackerHtml((commandCenterPayload || {{}}).seam_tracker || {{}});
        }}
        if (failureRecovery) {{
          failureRecovery.innerHTML = failureRecoveryHtml(supervision, approvals, Array.isArray(activity) ? activity : []);
        }}
        const statusOverride = String((options && options.statusNoteOverride) || "").trim();
        if (statusNote) statusNote.textContent = statusOverride || "Hydrated from /api/supervision-snapshot, /api/approval-queue/snapshot, /api/activity, /api/agent-registry, /api/briefing?actor=Chris, /api/open-loops?actor=Chris, and /api/assistant-core/notifications?actor=Chris.";
      }} catch (error) {{
        if (statusNote) statusNote.textContent = `Hydrate failed: ${{String(error)}}`;
      }}
    }}

    function attachActionHandlers() {{
      for (const button of document.querySelectorAll("button[data-endpoint]")) {{
        button.onclick = async () => {{
          const endpoint = button.getAttribute("data-endpoint");
          const method = button.getAttribute("data-method") || "POST";
          const needsKey = button.getAttribute("data-needs-key") || "";
          const isHomeAction = button.getAttribute("data-home-action") === "1";
          const actionLabel = String(button.textContent || "").trim() || "Inline Action";
          const rawBody = button.getAttribute("data-body");
          const beforeDetail = selectedDetail();
          pendingActionContext = {{ endpoint, beforeDetail, actionLabel, motionArtifactIndex: Number.isInteger(currentMotionArtifactIndex) ? currentMotionArtifactIndex : null }};
          if (statusNote) statusNote.textContent = `Calling ${{endpoint}}...`;
          try {{
            const response = await fetch(endpoint, {{
              method,
              headers: rawBody ? {{ "Content-Type": "application/json" }} : undefined,
              body: rawBody || undefined,
            }});
            const payload = await response.json().catch(() => ({{}}));
            if (!response.ok) {{
              throw new Error(payload.detail || `HTTP ${{response.status}}`);
            }}
            pendingActionContext = Object.assign({{}}, pendingActionContext || {{}}, {{ result: payload }});
            if (needsKey) {{
              latestNeedsActionStates[needsKey] = needsActionState(
                endpoint,
                payload,
                latestNeedsActionStates[needsKey] || null,
              );
              const needState = latestNeedsActionStates[needsKey] || {{}};
              recordNeedMotion({{
                kind: Boolean(needState.retired) ? "handled" : "updated",
                title: beforeDetail.title || "Need action",
                status: String(needState.status || payload.status || payload.result || "success"),
                detail: String(needState.summary || `Action succeeded: ${{endpoint}}`).trim(),
                need_key: needsKey,
                action_kind: method.toUpperCase() === "POST" ? "endpoint-action" : String(method || "action").toLowerCase(),
                action_label: actionLabel,
                action_summary: actionResultSummary({{ endpoint, result: payload }}),
                consequence_summary: String(needState.consequence_summary || needState.summary || `Action succeeded: ${{endpoint}}`).trim(),
                before_state: needMotionQueueState(needMotionContext(needsKey)),
                after_state: Boolean(needState.retired)
                  ? "retired"
                  : needMotionQueueState(needMotionContext(needsKey), String(needState.status || payload.status || payload.result || "updated")),
              }});
            }}
            const homeActionRecorded = isHomeAction
              ? await recordHomeActionEvent({{
                  actor: "Chris",
                  domain: "command-center",
                  action: actionLabel,
                  status: String(payload.status || payload.result || "ok"),
                  detail: `Action succeeded: ${{endpoint}}`,
                  why_now: latestChangeSummary || `Command center home action completed through ${{endpoint}}.`,
                  result_summary: `Home action result: ${{String(payload.status || payload.result || "ok")}}`,
                  route: button.getAttribute("data-home-route") || "/command-center",
                  route_label: button.getAttribute("data-home-route-label") || "Open Related Surface",
                  succeeded: true,
                }})
              : false;
            const operatorActionRecorded = !isHomeAction
              ? await recordOperatorActionEvent({{
                  actor: "Chris",
                  domain: "command-center",
                  action: actionLabel,
                  title: beforeDetail.title || actionLabel,
                  status: String(payload.status || payload.result || "ok"),
                  detail: `Action succeeded: ${{endpoint}}`,
                  why_now: latestChangeSummary || beforeDetail.summary || `Command center operator action completed through ${{endpoint}}.`,
                  result_summary: `Operator action result: ${{String(payload.status || payload.result || "ok")}}`,
                  route: sharedActivityRouteFor(endpoint, beforeDetail),
                  route_label: beforeDetail.route_label || "Open Related Surface",
                  related_kind: sharedActivityKindFor(endpoint, beforeDetail),
                  related_label: beforeDetail.title || "Related action target",
                  succeeded: true,
                }})
              : false;
            if ((isHomeAction && !homeActionRecorded) || (!isHomeAction && !operatorActionRecorded)) {{
              recentLocalActions = [
                {{
                  kind: "local-action",
                  entry_type: isHomeAction ? "home-action" : "local-action",
                  title: beforeDetail.title || "Operator action",
                  status: String(payload.status || payload.result || "ok"),
                  detail: String(endpoint || "") || "Inline command center action",
                  result_summary: isHomeAction
                    ? `Home action result: ${{String(payload.status || payload.result || "ok")}}`
                    : `Local action result: ${{String(payload.status || payload.result || "ok")}}`,
                  timestamp: new Date().toISOString(),
                  related_kind: beforeDetail.source_kind === "notification" ? "notification" : "open-loop",
                  related_label: beforeDetail.title || "Related action target",
                }},
                ...recentLocalActions,
              ].slice(0, 6);
            }}
            await hydratePanels({{
              homeActionResultOverride: isHomeAction ? {{
                source: "live-home-action",
                label: actionLabel,
                status_class: "accepted",
                summary: String(payload.status || payload.result || "ok"),
                detail: `Action succeeded: ${{endpoint}}`,
                route: button.getAttribute("data-home-route") || "",
                route_label: button.getAttribute("data-home-route-label") || "Open Related Surface",
              }} : null,
              statusNoteOverride: isHomeAction
                ? `Home refreshed: ${{String((((latestCommandCenterPayload || {{}}).home_overview || {{}}).headline) || (((latestCommandCenterPayload || {{}}).home_overview || {{}}).summary) || actionLabel).trim()}}`
                : `Success: ${{endpoint}}`,
            }});
          }} catch (error) {{
            const errorText = String(error);
            pendingActionContext = Object.assign({{}}, pendingActionContext || {{}}, {{ error: errorText }});
            latestChangeSummary = `Action failed before refresh: ${{errorText}}`;
            if (isHomeAction) {{
              const homeActionRecorded = await recordHomeActionEvent({{
                actor: "Chris",
                domain: "command-center",
                action: actionLabel,
                status: "failed",
                detail: `Action failed: ${{errorText}}`,
                why_now: `Command center home action failed before refresh: ${{errorText}}`,
                result_summary: "Home action failed before the command-center refresh completed.",
                route: button.getAttribute("data-home-route") || "/command-center",
                route_label: button.getAttribute("data-home-route-label") || "Open Related Surface",
                succeeded: false,
              }});
              latestHomeActionResult = {{
                source: "live-home-action",
                label: actionLabel,
                status_class: "regressed",
                summary: "failed",
                detail: `Action failed: ${{errorText}}`,
                route: button.getAttribute("data-home-route") || "",
                route_label: button.getAttribute("data-home-route-label") || "Open Related Surface",
              }};
              if (homeActionResult) {{
                homeActionResult.innerHTML = homeActionResultHtml(latestHomeActionResult);
              }}
              if (!homeActionRecorded) {{
                recentLocalActions = [
                  {{
                    kind: "local-action",
                    entry_type: "home-action",
                    title: actionLabel || "Home action",
                    status: "failed",
                    detail: `Action failed: ${{errorText}}`,
                    result_summary: "Home action failed before the command-center refresh completed.",
                    timestamp: new Date().toISOString(),
                    related_kind: "activity",
                    related_label: button.getAttribute("data-home-route-label") || "Related surface",
                  }},
                  ...recentLocalActions,
                ].slice(0, 6);
              }}
              if (activityFeed) {{
                activityFeed.innerHTML = activityItemHtml(buildVisibleActivityEntries(Array.isArray(latestActivityPayload) ? latestActivityPayload : []));
              }}
            }} else {{
              const operatorActionRecorded = await recordOperatorActionEvent({{
                actor: "Chris",
                domain: "command-center",
                action: actionLabel,
                title: beforeDetail.title || actionLabel,
                status: "failed",
                detail: `Action failed: ${{errorText}}`,
                why_now: `Command center operator action failed before refresh: ${{errorText}}`,
                result_summary: "Operator action failed before the command-center refresh completed.",
                route: sharedActivityRouteFor(endpoint, beforeDetail),
                route_label: beforeDetail.route_label || "Open Related Surface",
                related_kind: sharedActivityKindFor(endpoint, beforeDetail),
                related_label: beforeDetail.title || "Related action target",
                succeeded: false,
              }});
              if (!operatorActionRecorded) {{
                recentLocalActions = [
                  {{
                    kind: "local-action",
                    entry_type: "local-action",
                    title: beforeDetail.title || "Operator action",
                    status: "failed",
                    detail: `Action failed: ${{errorText}}`,
                    result_summary: "Operator action failed before the command-center refresh completed.",
                    timestamp: new Date().toISOString(),
                    related_kind: beforeDetail.source_kind === "notification" ? "notification" : "open-loop",
                    related_label: beforeDetail.title || "Related action target",
                  }},
                  ...recentLocalActions,
                ].slice(0, 6);
              }}
            }}
            if (needsKey) {{
              latestNeedsActionStates[needsKey] = {{
                status: "failed",
                summary: `Action failed: ${{errorText}}`,
              }};
              recordNeedMotion({{
                kind: "failed",
                title: beforeDetail.title || "Need action",
                status: "failed",
                detail: `Action failed: ${{errorText}}`,
                need_key: needsKey,
                action_kind: "endpoint-failure",
                action_label: actionLabel,
                action_summary: `Endpoint failed: ${{endpoint}}`,
                consequence_summary: `Failure consequence: action did not move the live queue state.`,
                before_state: needMotionQueueState(needMotionContext(needsKey)),
                after_state: "failed",
              }});
              if (needsList) {{
                needsList.innerHTML = needsNowHtml(buildNeedsCockpit(
                  latestSupervisionPayload || {{}},
                  latestApprovalsPayload || {{}},
                  latestOpenLoopsPayload || {{}},
                  latestNotificationsPayload || {{}},
                  Array.isArray(latestActivityPayload) ? latestActivityPayload : [],
                ));
                attachActionHandlers();
              }}
              refreshNeedsMotionPanel();
            }}
            const failedDetail = beforeDetail || selectedDetail();
            failedDetail.action_result_summary = `failed · endpoint ${{endpoint}}`;
            failedDetail.change_evidence_summary = `Action failed before refresh: ${{errorText}}`;
            failedDetail.approval_consequence_fields = approvalConsequenceFields(beforeDetail || {{}}, failedDetail, pendingActionContext);
            failedDetail.approval_guidance_lines = approvalRemediationGuidance(beforeDetail || {{}}, failedDetail, pendingActionContext);
            failedDetail.motion_artifact_focus_delta_summary = motionArtifactDeltaSummary(beforeDetail || {{}}, failedDetail, pendingActionContext);
            failedDetail.motion_artifact_focus_delta_sections = motionArtifactDeltaSections(beforeDetail || {{}}, failedDetail, pendingActionContext);
            failedDetail.motion_artifact_focus_excerpts = motionArtifactProofExcerpts(beforeDetail || {{}}, failedDetail, pendingActionContext);
            failedDetail.motion_artifact_focus_proof_compare_summary = motionArtifactProofCompareSummary(beforeDetail || {{}}, failedDetail, pendingActionContext);
            failedDetail.motion_artifact_focus_proof_compare_rows = motionArtifactProofCompareRows(beforeDetail || {{}}, failedDetail, pendingActionContext);
            failedDetail.motion_artifact_focus_posture_hint = motionArtifactPostureHint(failedDetail, pendingActionContext);
            recordMotionArtifactHistory(failedDetail, pendingActionContext);
            applyMotionArtifactHistory(failedDetail);
            setDetailInspector(failedDetail);
            pendingActionContext = null;
            if (statusNote) statusNote.textContent = `Action failed: ${{String(error)}}`;
          }}
        }};
      }}
      for (const button of document.querySelectorAll("button[data-detail-kind]")) {{
        button.onclick = () => {{
          const kind = button.getAttribute("data-detail-kind") || "";
          const index = button.getAttribute("data-detail-index") || "0";
          currentDetailSelection = {{ kind, index: Number(index) || 0 }};
          currentTimelineEventIndex = null;
          currentMotionArtifactIndex = null;
          if (kind === "agent") {{
            setDetailInspector(agentDetailAt(index));
            return;
          }}
          if (kind === "mission") {{
            setDetailInspector(missionDetailAt(index));
            return;
          }}
          if (kind === "seam") {{
            setDetailInspector(seamDetailAt(index));
            return;
          }}
          if (kind === "progress") {{
            setDetailInspector(progressDetailAt(index));
            return;
          }}
          if (kind === "module") {{
            setDetailInspector(moduleDetailAt(index));
            return;
          }}
          if (kind === "journal") {{
            setDetailInspector(journalDetailAt(index));
            return;
          }}
          if (kind === "notification") {{
            setDetailInspector(notificationDetailAt(index));
            return;
          }}
          setDetailInspector(openLoopDetailAt(index));
        }};
      }}
      for (const button of document.querySelectorAll("button[data-jump-kind='journal-related']")) {{
        button.onclick = () => {{
          const index = button.getAttribute("data-jump-index") || "0";
          currentTimelineEventIndex = null;
          currentMotionArtifactIndex = null;
          setDetailInspector(jumpToRelatedFromJournal(index));
        }};
      }}
      for (const button of document.querySelectorAll("button[data-needs-index]")) {{
        button.onclick = () => {{
          const index = button.getAttribute("data-needs-index") || "0";
          currentTimelineEventIndex = null;
          currentMotionArtifactIndex = null;
          setDetailInspector(jumpToNeedContext(index));
          if (statusNote) statusNote.textContent = "Focused selected Needs Me Now item in the shared detail inspector.";
        }};
      }}
      for (const button of document.querySelectorAll("button[data-needs-key-inspect]")) {{
        button.onclick = () => {{
          const needKey = button.getAttribute("data-needs-key-inspect") || "";
          currentTimelineEventIndex = null;
          currentMotionArtifactIndex = null;
          setDetailInspector(jumpToNeedContextByKey(needKey));
          if (statusNote) statusNote.textContent = "Focused handled Needs Me Now outcome in the shared detail inspector.";
        }};
      }}
      for (const button of document.querySelectorAll("button[data-motion-index]")) {{
        button.onclick = () => {{
          const index = button.getAttribute("data-motion-index") || "0";
          currentTimelineEventIndex = null;
          currentMotionArtifactIndex = null;
          setDetailInspector(jumpToNeedMotion(index));
          if (statusNote) statusNote.textContent = "Focused selected Recent Need Motion proof in the shared detail inspector.";
        }};
      }}
      for (const button of document.querySelectorAll("button[data-motion-artifact-index]")) {{
        button.onclick = () => {{
          const index = button.getAttribute("data-motion-artifact-index") || "0";
          currentMotionArtifactIndex = Number(index) || 0;
          setDetailInspector(jumpToMotionArtifact(index));
          if (statusNote) statusNote.textContent = "Focused localized motion-proof artifact in the shared detail inspector.";
        }};
      }}
      for (const button of document.querySelectorAll("button[data-motion-artifact-history-index]")) {{
        button.onclick = () => {{
          const index = button.getAttribute("data-motion-artifact-history-index") || "0";
          setDetailInspector(jumpToMotionArtifactHistory(index));
          if (statusNote) statusNote.textContent = "Focused selected localized artifact action from the in-pane history strip.";
        }};
      }}
      for (const button of document.querySelectorAll("button[data-motion-artifact-snapshot-reason]")) {{
        button.onclick = () => {{
          setDetailInspector(applyMotionArtifactSnapshotPath(selectedDetail(), "proof"));
          if (statusNote) statusNote.textContent = "Focused the stored proof behind the reopened next move.";
        }};
      }}
      for (const button of document.querySelectorAll("button[data-motion-artifact-snapshot-restored-reason]")) {{
        button.onclick = () => {{
          setDetailInspector(jumpToMotionArtifactSnapshotRestoredReason("restored-reason"));
          if (statusNote) statusNote.textContent = "Focused restored evidence from the reopened proof resume row.";
        }};
      }}
      for (const button of document.querySelectorAll("button[data-motion-artifact-snapshot-resumed-restored-reason]")) {{
        button.onclick = () => {{
          setDetailInspector(jumpToMotionArtifactSnapshotRestoredReason("resumed-restored-reason"));
          if (statusNote) statusNote.textContent = "Focused resumed restored evidence from the resumed restored proof row.";
        }};
      }}
      for (const button of document.querySelectorAll("button[data-motion-artifact-snapshot-restored-return]")) {{
        button.onclick = () => {{
          setDetailInspector(jumpToMotionArtifactSnapshotRestoredReason("restored-return"));
          if (statusNote) statusNote.textContent = "Returned to the restored evidence lane.";
        }};
      }}
      for (const button of document.querySelectorAll("button[data-motion-artifact-snapshot-resumed-return]")) {{
        button.onclick = () => {{
          setDetailInspector(jumpToMotionArtifactSnapshotRestoredReason("resumed-return"));
          if (statusNote) statusNote.textContent = "Returned to the resumed evidence lane.";
        }};
      }}
      for (const button of document.querySelectorAll("button[data-motion-artifact-snapshot-resumed-restored-return]")) {{
        button.onclick = () => {{
          setDetailInspector(jumpToMotionArtifactSnapshotRestoredReason("resumed-restored-return"));
          if (statusNote) statusNote.textContent = "Returned to the resumed restored evidence lane.";
        }};
      }}
      for (const button of document.querySelectorAll("button[data-motion-artifact-snapshot-resumed-restored-focus-return]")) {{
        button.onclick = () => {{
          setDetailInspector(jumpToMotionArtifactSnapshotRestoredReason("resumed-restored-focus-return"));
          if (statusNote) statusNote.textContent = "Returned to the resumed restored focus lane.";
        }};
      }}
      for (const button of document.querySelectorAll("button[data-motion-artifact-snapshot-confirmed-resumed-restored-focus-return]")) {{
        button.onclick = () => {{
          setDetailInspector(jumpToMotionArtifactSnapshotRestoredReason("resumed-restored-focus-return"));
          if (statusNote) statusNote.textContent = "Returned to the confirmed resumed restored focus lane.";
        }};
      }}
      for (const button of document.querySelectorAll("button[data-motion-artifact-snapshot-reopened-confirmed-resumed-restored-focus-return]")) {{
        button.onclick = () => {{
          setDetailInspector(jumpToMotionArtifactSnapshotRestoredReason("resumed-restored-focus-return"));
          if (statusNote) statusNote.textContent = "Returned to the reopened confirmed restored focus lane.";
        }};
      }}
      for (const button of document.querySelectorAll("button[data-motion-artifact-snapshot-reopened-reopened-confirmed-resumed-restored-focus-return]")) {{
        button.onclick = () => {{
          setDetailInspector(jumpToMotionArtifactSnapshotRestoredReason("resumed-restored-focus-return"));
          if (statusNote) statusNote.textContent = "Returned to the reopened reopened confirmed restored focus lane.";
        }};
      }}
      for (const button of document.querySelectorAll("button[data-motion-artifact-snapshot-reopened-reopened-reopened-confirmed-resumed-restored-focus-return]")) {{
        button.onclick = () => {{
          setDetailInspector(jumpToMotionArtifactSnapshotRestoredReason("resumed-restored-focus-return"));
          if (statusNote) statusNote.textContent = "Returned to the reopened reopened reopened confirmed restored focus lane.";
        }};
      }}
      for (const button of document.querySelectorAll("button[data-motion-artifact-snapshot-reopened-reopened-reopened-reopened-confirmed-resumed-restored-focus-return]")) {{
        button.onclick = () => {{
          setDetailInspector(jumpToMotionArtifactSnapshotRestoredReason("resumed-restored-focus-return"));
          if (statusNote) statusNote.textContent = "Returned to the reopened reopened reopened reopened confirmed restored focus lane.";
        }};
      }}
      for (const button of document.querySelectorAll("button[data-motion-artifact-snapshot-reopened-reopened-reopened-reopened-reopened-confirmed-resumed-restored-focus-return]")) {{
        button.onclick = () => {{
          setDetailInspector(jumpToMotionArtifactSnapshotRestoredReason("resumed-restored-focus-return"));
          if (statusNote) statusNote.textContent = "Returned to the reopened reopened reopened reopened reopened confirmed restored focus lane.";
        }};
      }}
      for (const button of document.querySelectorAll("button[data-motion-artifact-snapshot-reopened-reopened-reopened-reopened-reopened-reopened-confirmed-resumed-restored-focus-return]")) {{
        button.onclick = () => {{
          setDetailInspector(jumpToMotionArtifactSnapshotRestoredReason("resumed-restored-focus-return"));
          if (statusNote) statusNote.textContent = "Returned to the reopened reopened reopened reopened reopened reopened confirmed restored focus lane.";
        }};
      }}
      for (const button of document.querySelectorAll("button[data-motion-artifact-snapshot-reopened-reopened-reopened-reopened-reopened-reopened-reopened-confirmed-resumed-restored-focus-return]")) {{
        button.onclick = () => {{
          setDetailInspector(jumpToMotionArtifactSnapshotRestoredReason("resumed-restored-focus-return"));
          if (statusNote) statusNote.textContent = "Returned to the reopened reopened reopened reopened reopened reopened reopened confirmed restored focus lane.";
        }};
      }}
      for (const button of document.querySelectorAll("button[data-motion-artifact-snapshot-reopened-reopened-reopened-reopened-reopened-reopened-reopened-reopened-confirmed-resumed-restored-focus-return]")) {{
        button.onclick = () => {{
          setDetailInspector(jumpToMotionArtifactSnapshotRestoredReason("resumed-restored-focus-return"));
          if (statusNote) statusNote.textContent = "Returned to the reopened reopened reopened reopened reopened reopened reopened reopened confirmed restored focus lane.";
        }};
      }}
      for (const button of document.querySelectorAll("button[data-motion-artifact-snapshot-reopened-reopened-reopened-reopened-reopened-reopened-reopened-reopened-reopened-confirmed-resumed-restored-focus-return]")) {{
        button.onclick = () => {{
          setDetailInspector(jumpToMotionArtifactSnapshotRestoredReason("resumed-restored-focus-return"));
          if (statusNote) statusNote.textContent = "Returned to the reopened reopened reopened reopened reopened reopened reopened reopened reopened confirmed restored focus lane.";
        }};
      }}
      for (const button of document.querySelectorAll("button[data-motion-artifact-snapshot-reopened-reopened-reopened-reopened-reopened-reopened-reopened-reopened-reopened-reopened-confirmed-resumed-restored-focus-return]")) {{
        button.onclick = () => {{
          setDetailInspector(jumpToMotionArtifactSnapshotRestoredReason("resumed-restored-focus-return"));
          if (statusNote) statusNote.textContent = "Returned to the reopened reopened reopened reopened reopened reopened reopened reopened reopened reopened confirmed restored focus lane.";
        }};
      }}
      for (const button of document.querySelectorAll("button[data-motion-artifact-snapshot-reopened-reopened-reopened-reopened-reopened-reopened-reopened-reopened-reopened-reopened-reopened-confirmed-resumed-restored-focus-return]")) {{
        button.onclick = () => {{
          const detail = jumpToMotionArtifactSnapshotRestoredReason("resumed-restored-focus-return");
          setDetailInspector(detail);
          if (statusNote) statusNote.textContent = String((((detail || {{}}).motion_artifact_focus_posture_snapshot_reason_focus || {{}}).return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_summary) || "Returned to the reopened reopened reopened reopened reopened reopened reopened reopened reopened reopened reopened confirmed restored focus lane.").trim();
        }};
      }}
      for (const button of document.querySelectorAll("button[data-motion-artifact-snapshot-return]")) {{
        button.onclick = () => {{
          setDetailInspector(jumpBackToMotionArtifactSnapshotProof());
          if (statusNote) statusNote.textContent = "Returned to the reopened proof focus.";
        }};
      }}
      for (const button of document.querySelectorAll("button[data-motion-artifact-snapshot-timeline-index]")) {{
        button.onclick = () => {{
          const index = button.getAttribute("data-motion-artifact-snapshot-timeline-index") || "0";
          setDetailInspector(jumpToMotionArtifactSnapshotTimeline(index));
          if (statusNote) statusNote.textContent = "Focused reopened proof chronology from the proof pivot strip.";
        }};
      }}
      for (const button of document.querySelectorAll("button[data-motion-artifact-snapshot-target-artifact-index]")) {{
        button.onclick = () => {{
          const index = button.getAttribute("data-motion-artifact-snapshot-target-artifact-index") || "0";
          const detail = jumpToMotionArtifactSnapshotTargetArtifact(index);
          setDetailInspector(detail);
          if (statusNote) statusNote.textContent = String((((detail || {{}}).motion_artifact_focus_posture_snapshot_reason_focus || {{}}).active_target_label) || "Confirmed the reopened proof target artifact in the shared inspector.").trim();
        }};
      }}
      for (const button of document.querySelectorAll("button[data-motion-artifact-snapshot-history-target-artifact-index]")) {{
        button.onclick = () => {{
          const index = button.getAttribute("data-motion-artifact-snapshot-history-target-artifact-index") || "0";
          const originIndex = button.getAttribute("data-motion-artifact-snapshot-history-origin-index") || "";
          const detail = jumpToMotionArtifactSnapshotTargetArtifact(index, "round-trip-history-artifact", originIndex);
          setDetailInspector(detail);
          if (statusNote) statusNote.textContent = String((detail || {{}}).motion_artifact_focus_history_note || (((detail || {{}}).motion_artifact_focus_posture_snapshot_reason_focus || {{}}).active_target_label) || "Round-trip reopen result: artifact lane active.").trim();
        }};
      }}
      for (const button of document.querySelectorAll("button[data-motion-artifact-snapshot-target-timeline-index]")) {{
        button.onclick = () => {{
          const index = button.getAttribute("data-motion-artifact-snapshot-target-timeline-index") || "0";
          const detail = jumpToMotionArtifactSnapshotTargetTimeline(index);
          setDetailInspector(detail);
          if (statusNote) statusNote.textContent = String((((detail || {{}}).motion_artifact_focus_posture_snapshot_reason_focus || {{}}).active_target_label) || "Confirmed the reopened proof target timeline in the shared inspector.").trim();
        }};
      }}
      for (const button of document.querySelectorAll("button[data-motion-artifact-snapshot-history-target-timeline-index]")) {{
        button.onclick = () => {{
          const index = button.getAttribute("data-motion-artifact-snapshot-history-target-timeline-index") || "0";
          const originIndex = button.getAttribute("data-motion-artifact-snapshot-history-origin-index") || "";
          const detail = jumpToMotionArtifactSnapshotTargetTimeline(index, "round-trip-history-timeline", originIndex);
          setDetailInspector(detail);
          if (statusNote) statusNote.textContent = String((detail || {{}}).motion_artifact_focus_history_note || (((detail || {{}}).motion_artifact_focus_posture_snapshot_reason_focus || {{}}).active_target_label) || "Round-trip reopen result: timeline lane active.").trim();
        }};
      }}
      for (const button of document.querySelectorAll("button[data-motion-artifact-round-trip-history-return-index]")) {{
        button.onclick = () => {{
          const index = button.getAttribute("data-motion-artifact-round-trip-history-return-index") || "0";
          const detail = jumpToMotionArtifactHistory(index);
          setDetailInspector(detail);
          if (statusNote) statusNote.textContent = "Returned to the originating round-trip history row.";
        }};
      }}
      for (const button of document.querySelectorAll("button[data-motion-artifact-snapshot-restored-target-return]")) {{
        button.onclick = () => {{
          const detail = jumpToMotionArtifactSnapshotRestoredReason("resumed-restored-focus-return");
          setDetailInspector(detail);
          if (statusNote) statusNote.textContent = "Returned to the persistent restored target proof row.";
        }};
      }}
      for (const button of document.querySelectorAll("button[data-needs-reopen]")) {{
        button.onclick = () => {{
          const needKey = button.getAttribute("data-needs-reopen") || "";
          if (!needKey) return;
          latestNeedsActionStates[needKey] = {{
            status: "reopened",
            summary: "Reopened for operator review.",
            retired: false,
          }};
          recordNeedMotion({{
            kind: "reopened",
            title: needKey,
            status: "reopened",
            detail: "Reopened for operator review.",
            need_key: needKey,
            action_kind: "reopen",
            action_label: "Reopen",
            action_summary: "Moved a handled need back into active operator review.",
            consequence_summary: "Reopen consequence: the need returned to active operator review.",
            before_state: "retired",
            after_state: "reopened",
          }});
          if (needsList) {{
            needsList.innerHTML = needsNowHtml(buildNeedsCockpit(
              latestSupervisionPayload || {{}},
              latestApprovalsPayload || {{}},
              latestOpenLoopsPayload || {{}},
              latestNotificationsPayload || {{}},
              Array.isArray(latestActivityPayload) ? latestActivityPayload : [],
            ));
            attachActionHandlers();
          }}
          refreshNeedsMotionPanel();
          if (statusNote) statusNote.textContent = "Reopened handled triage item for review.";
        }};
      }}
      for (const button of document.querySelectorAll("button[data-timeline-index]")) {{
        button.onclick = () => {{
          const index = Number(button.getAttribute("data-timeline-index") || "0");
          currentTimelineEventIndex = Number.isFinite(index) ? index : null;
          currentMotionArtifactIndex = null;
          setDetailInspector(selectedDetail());
        }};
      }}
      for (const button of document.querySelectorAll("button[data-event-action]")) {{
        button.onclick = () => {{
          const action = button.getAttribute("data-event-action") || "";
          performEventAction(action);
        }};
      }}
    }}

    attachActionHandlers();
    hydratePanels();
  </script>
</body>
</html>
"""
