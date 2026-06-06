from __future__ import annotations

import unittest

from jarvis.command_center_index import (
    build_command_center_index,
    render_command_center_index_html,
)


class CommandCenterIndexTests(unittest.TestCase):
    def test_build_index_collects_live_surface_inventory(self) -> None:
        payload = build_command_center_index()

        self.assertGreaterEqual(payload["surface_count"], 4)
        self.assertEqual(payload["proof_paths"]["approval_queue"], "/approval-queue")
        self.assertEqual(payload["proof_paths"]["supervision_snapshot"], "/supervision-snapshot")
        self.assertIn("pending_approvals", payload)
        self.assertIn("memory", payload)
        self.assertIn("entry_count", payload["memory"])
        self.assertIn("activity_feed", payload)
        self.assertIn("registry", payload)
        self.assertIn("agent_ops_roster", payload)
        self.assertIn("items", payload["agent_ops_roster"])
        self.assertIn("core_modules", payload)
        self.assertIn("items", payload["core_modules"])
        self.assertIn("progress_dashboard", payload)
        self.assertIn("items", payload["progress_dashboard"])
        self.assertIn("seam_tracker", payload)
        self.assertIn("items", payload["seam_tracker"])
        self.assertIn("level3_checklist", payload)
        self.assertIn("items", payload["level3_checklist"])
        self.assertIn("lane_progress", payload)
        self.assertIn("failure_recovery", payload)
        self.assertIn("action_items", payload["failure_recovery"])
        self.assertIn("hosted_deployment", payload)
        self.assertEqual(payload["hosted_deployment"]["hosted_url"], "https://jarvis.teambinion.org")
        self.assertIn("deploy/deploy.sh", payload["hosted_deployment"]["proof_files"])
        self.assertIn("home_overview", payload)
        self.assertIn("headline", payload["home_overview"])
        self.assertIn("actions", payload["home_overview"])
        self.assertGreaterEqual(len(payload["home_overview"]["actions"]), 2)
        self.assertIn("action_result", payload["home_overview"])
        self.assertIn("activity_bridge", payload["home_overview"]["action_result"])
        self.assertEqual(payload["home_overview"]["hosted_url"], "https://jarvis.teambinion.org")
        self.assertIn("brief_preview", payload)
        self.assertIn("headline", payload["brief_preview"])
        self.assertIn("timeline_preview", payload)
        self.assertIn("items", payload["timeline_preview"])
        self.assertIn("open_loop_inspector", payload)
        self.assertIn("items", payload["open_loop_inspector"])
        self.assertIn("task_lanes", payload["open_loop_inspector"])
        self.assertIn("action_journal", payload)
        self.assertIn("entries", payload["action_journal"])
        self.assertIn("mission_task_board", payload)
        self.assertIn("items", payload["mission_task_board"])
        self.assertIn("detail_inspector", payload)
        self.assertIn("title", payload["detail_inspector"])
        self.assertIn("notification_preview", payload)
        self.assertIn("items", payload["notification_preview"])
        self.assertIn("needs_cockpit", payload)
        self.assertIn("items", payload["needs_cockpit"])
        self.assertIn("needs_motion", payload)
        self.assertIn("entries", payload["needs_motion"])
        self.assertTrue(
            all("focus_targets" in item for item in payload["needs_cockpit"]["items"])
            if payload["needs_cockpit"]["items"]
            else True
        )
        self.assertTrue(
            all("need_key" in item for item in payload["needs_cockpit"]["items"])
            if payload["needs_cockpit"]["items"]
            else True
        )
        self.assertTrue(
            all("primary_action" in item for item in payload["needs_cockpit"]["items"])
            if payload["needs_cockpit"]["items"]
            else True
        )
        self.assertIn("dirty_count", payload["lane_progress"])
        self.assertIn("recent_commits", payload["lane_progress"])
        self.assertGreaterEqual(payload["seam_tracker"]["item_count"], 3)
        self.assertGreaterEqual(payload["mission_task_board"]["item_count"], 1)
        self.assertGreaterEqual(payload["agent_ops_roster"]["item_count"], 1)
        self.assertGreaterEqual(payload["core_modules"]["item_count"], 10)
        self.assertGreaterEqual(payload["progress_dashboard"]["item_count"], 5)
        self.assertGreaterEqual(payload["level3_checklist"]["item_count"], 5)
        self.assertTrue(any(item["title"] == "Durable Seam and Progress Persistence" for item in payload["level3_checklist"]["items"]))
        self.assertTrue(any(item["title"] == "Daily Brief" and item["screen_path"] == "/briefing-center" for item in payload["core_modules"]["items"]))
        self.assertTrue(any(item["title"] == "Progress" and item["screen_path"] == "/progress-center" for item in payload["core_modules"]["items"]))
        self.assertTrue(any(item["title"] == "Navigation" and item["screen_path"] == "/navigation-center" for item in payload["core_modules"]["items"]))
        self.assertTrue(any(item["title"] == "Publish" and item["screen_path"] == "/publish" for item in payload["core_modules"]["items"]))
        self.assertTrue(any(item["title"] == "Chronicle" and item["screen_path"] == "/chronicle-center" for item in payload["core_modules"]["items"]))
        self.assertTrue(any(item["title"] == "Huddle" and item["screen_path"] == "/huddle-center" for item in payload["core_modules"]["items"]))
        self.assertTrue(any(item["title"] == "Health" and item["screen_path"] == "/health-center" for item in payload["core_modules"]["items"]))
        self.assertTrue(any(item["title"] == "Settings & Permissions" and item["screen_path"] == "/settings-center" for item in payload["core_modules"]["items"]))
        self.assertTrue(any(item["title"] == "Agent Operations" and item["screen_path"] == "/agent-ops-center" for item in payload["core_modules"]["items"]))
        self.assertTrue(any(item["title"] == "Failure & Recovery" and item["screen_path"] == "/recovery-center" for item in payload["core_modules"]["items"]))
        self.assertEqual(payload["proof_paths"]["command_center_json"], "/api/command-center")
        self.assertEqual(payload["proof_paths"]["agent_registry_json"], "/api/agent-registry")
        self.assertEqual(payload["proof_paths"]["briefing_json"], "/api/briefing?actor=Chris")
        self.assertEqual(payload["proof_paths"]["open_loops_json"], "/api/open-loops?actor=Chris")
        self.assertEqual(payload["proof_paths"]["missions_json"], "/api/missions")
        self.assertEqual(payload["proof_paths"]["assistant_notifications_json"], "/api/assistant-core/notifications?actor=Chris")
        self.assertTrue(any(item["title"] == "Approval Queue" and item["api"] == "/api/approval/module" for item in payload["surfaces"]))
        self.assertTrue(any(item["title"] == "Supervision Snapshot" and item["api"] == "/api/supervision/module" for item in payload["surfaces"]))
        self.assertTrue(any(item["title"] == "Mission API" for item in payload["surfaces"]))
        self.assertTrue(any(item["title"] == "Mission Board" and item["path"] == "/mission-board" for item in payload["surfaces"]))
        self.assertTrue(any(item["title"] == "Activity Feed" and item["path"] == "/activity-center" for item in payload["surfaces"]))
        self.assertTrue(any(item["path"] == "/api/open-loops" for item in payload["json_endpoints"]))
        self.assertTrue(any(item["path"] == "/api/missions" for item in payload["json_endpoints"]))

    def test_render_index_exposes_live_routes_and_categories(self) -> None:
        html = render_command_center_index_html(
            {
                "generated_at": "2026-06-03T12:00:00+00:00",
                "branch": "codex/apple-native-command-surface",
                "head": "abc1234",
                "what_needs_me": [{"title": "Approve local rollout", "detail": "high request"}],
                "needs_cockpit": {
                    "total": 3,
                    "critical_count": 1,
                    "high_count": 2,
                    "approval_count": 1,
                    "failure_count": 1,
                    "notification_count": 1,
                    "headline": "Approve local rollout",
                    "items": [
                        {
                            "need_key": "approve local rollout::approval",
                            "title": "Approve local rollout",
                            "detail": "Queue needs review",
                            "urgency": "critical",
                            "sources": ["approval", "supervision"],
                            "route": "/approval-queue",
                            "route_label": "Open approval queue",
                            "action_hint": "Approve, reject, cancel, or execute from the approval queue.",
                            "focus_targets": ["open-loop", "journal"],
                            "primary_action": {
                                "label": "Approve",
                                "endpoint": "/api/approvals/req-1/approve",
                                "method": "POST",
                            },
                        },
                        {
                            "need_key": "repair google-calendar::failure",
                            "title": "Repair google-calendar",
                            "detail": "Token refresh failed",
                            "urgency": "critical",
                            "sources": ["failure"],
                            "route": "/supervision-snapshot",
                            "route_label": "Open recovery view",
                            "action_hint": "Inspect failure and recovery posture before retrying related actions.",
                            "focus_targets": ["journal", "open-loop"],
                            "primary_action": {},
                        },
                    ],
                },
                "needs_motion": {
                    "count": 2,
                    "active_count": 1,
                    "signal_count": 1,
                    "entries": [
                        {
                            "kind": "active",
                            "title": "Approve local rollout",
                            "status": "critical",
                            "detail": "Queue needs review",
                            "timestamp": "live queue",
                            "need_key": "approve local rollout::approval",
                            "source_kind": "need",
                            "source_label": "Approve local rollout",
                            "queue_state": "critical / approval, supervision",
                            "transition": "observed -> active",
                            "evidence_links": [
                                {"label": "Command Center", "href": "/command-center"},
                                {"label": "Open approval queue", "href": "/approval-queue"},
                            ],
                            "evidence": "critical / approval, supervision / Open approval queue",
                        },
                        {
                            "kind": "signal",
                            "title": "Calendar sync failure",
                            "status": "audit",
                            "detail": "Token refresh failed",
                            "timestamp": "2026-06-03T12:00:00+00:00",
                            "need_key": "",
                            "source_kind": "activity",
                            "source_label": "calendar",
                            "source_entry_type": "audit",
                            "queue_state": "audit",
                            "transition": "runtime signal -> review",
                            "evidence_links": [
                                {"label": "Activity JSON", "href": "/api/activity"},
                                {"label": "Command Center", "href": "/command-center"},
                            ],
                            "evidence": "audit / calendar / 2026-06-03T12:00:00+00:00",
                        },
                    ],
                },
                "pending_approvals": [
                    {
                        "request_id": "req-1",
                        "title": "Approve local rollout",
                        "description": "Queue needs review",
                        "risk_tier": "high",
                        "agent_label": "Scout",
                    }
                ],
                "approval_history": [
                    {
                        "request_id": "req-1",
                        "title": "Approve local rollout",
                        "status": "approved",
                        "approved_by": "Chris",
                        "approved_at": "2026-06-03T11:40:00+00:00",
                        "actor_id": "Chris",
                        "supervision_decision": {"resolution": "allow"},
                    }
                ],
                "memory": {
                    "entry_count": 4,
                    "proposal_count": 2,
                    "fact_count": 3,
                    "latest_entry_titles": ["Morning oversight note"],
                    "pending_proposals": ["Queue posture update"],
                },
                "home_overview": {
                    "day_label": "2026-06-03",
                    "headline": "Approve local rollout",
                    "summary": "Approve local rollout. Top need: Approve local rollout - high request",
                    "priority_count": 3,
                    "active_agent_count": 4,
                    "open_mission_count": 2,
                    "recent_activity_count": 2,
                    "useful_module_count": 2,
                    "top_need": {
                        "title": "Approve local rollout",
                        "detail": "Queue needs review",
                        "route": "/approval-queue",
                    },
                    "next_mission": {
                        "title": "Keep the family ahead of tomorrow morning weather",
                        "detail": "Check rainfall timing",
                        "route": "/mission-board",
                    },
                    "active_agent": {
                        "title": "Heimdall",
                        "detail": "ops / running / 2026-06-03T11:58:00+00:00",
                        "route": "/agent-ops-center",
                    },
                    "system_state": {
                        "label": "Needs Attention",
                        "status_class": "artifact",
                        "detail": "1 integration issue(s), 1 pending approval gate(s), and 0 dirty working-tree item(s) are shaping the current home posture.",
                        "route": "/recovery-center",
                    },
                    "actions": [
                        {
                            "label": "Approve Request",
                            "endpoint": "/api/approvals/req-1/approve",
                            "method": "POST",
                            "needs_key": "approve local rollout::approval",
                            "route": "/approval-queue",
                            "route_label": "Open approval queue",
                            "detail": "Queue needs review",
                        },
                        {
                            "label": "Move Mission to Now",
                            "endpoint": "/api/missions/weather-family/status",
                            "method": "POST",
                            "body": {"status": "active", "note": "Advanced from the command center home action rail."},
                            "route": "/mission-board",
                            "route_label": "Open Mission Board",
                            "detail": "Check rainfall timing",
                        },
                        {"label": "Open Daily Brief", "route": "/briefing-center", "detail": "Approve local rollout"},
                        {"label": "Open Activity Feed", "route": "/activity-center", "detail": "Queued approval surfaced"},
                    ],
                    "action_result": {
                        "label": "Next Likely Change",
                        "status_class": "artifact",
                        "summary": "Approve local rollout",
                        "detail": "Queue needs review",
                        "route": "/approval-queue",
                        "route_label": "Open approval queue",
                        "activity_bridge": {
                            "entry_type": "home-action-preview",
                            "title": "Approve local rollout",
                            "detail": "Queue needs review",
                            "result": "needs attention",
                            "result_summary": "Home action preview seeded from the current top-need posture.",
                        },
                    },
                },
                "activity_feed": [
                    {
                        "entry_type": "assistant-action",
                        "timestamp": "2026-06-03T12:00:00+00:00",
                        "title": "Queued approval surfaced",
                        "subtitle": "approvals",
                        "result": "pending",
                    },
                    {
                        "entry_type": "runtime-failure",
                        "timestamp": "2026-06-03T12:05:00+00:00",
                        "title": "Calendar sync failure",
                        "subtitle": "google-calendar",
                        "result": "error",
                    }
                ],
                "registry": {
                    "agent_count": 6,
                    "domains": ["health", "household"],
                    "authority_stages": ["observe", "sandbox_live"],
                    "registry_error": "",
                    "sample_contracts": [
                        {"label": "Scout", "agent_id": "scout", "authority_stage": "observe"}
                    ],
                },
                "agent_ops_roster": {
                    "summary": "2 running, 1 blocked, 1 needing attention across 4 visible agent(s).",
                    "item_count": 2,
                    "counts": {"running": 1, "blocked": 1, "attention": 0},
                    "items": [
                        {
                            "agent_id": "ambient-router",
                            "name": "Heimdall",
                            "purpose": "Maintain the front-door JARVIS shell.",
                            "domain": "core",
                            "status": "running",
                            "status_class": "accepted",
                            "assignment": "request routing",
                            "last_activity": "2026-06-03T12:00:00+00:00",
                            "module": "core",
                            "maturity": "Durable",
                            "maturity_class": "accepted",
                        },
                        {
                            "agent_id": "watchtower",
                            "name": "Watchtower",
                            "purpose": "Surface only meaningful household anomalies.",
                            "domain": "household",
                            "status": "blocked",
                            "status_class": "regressed",
                            "assignment": "household alerts",
                            "last_activity": "2026-06-03T11:00:00+00:00",
                            "module": "household",
                            "maturity": "Wired",
                            "maturity_class": "steady",
                        },
                    ],
                },
                "lane_progress": {
                    "branch": "codex/apple-native-command-surface",
                    "head": "abc1234",
                    "dirty_count": 2,
                    "recent_commits": ["8d7399f feat: add command center registry panel"],
                    "dirty_sample": [" M jarvis/service.py"],
                    "return_brief_summary": "1 approval pending, 0 integration issues, 2 memory proposals, 6 registered agents",
                    "what_needs_me_count": 1,
                },
                "seam_tracker": {
                    "summary": "1 useful seam(s), 1 wired seam(s), branch codex/apple-native-command-surface, head abc1234.",
                    "item_count": 2,
                    "counts": {"Useful": 1, "Wired": 1},
                    "items": [
                        {
                            "name": "Command Center Working Base",
                            "status": "Useful",
                            "status_class": "accepted",
                            "module": "Command Center/Home",
                            "maturity": "Useful",
                            "what_became_real": "Live command center route with seeded operator surfaces.",
                            "commit_status": "8d7399f feat: add command center registry panel",
                        },
                        {
                            "name": "Seam Tracker Control Surface",
                            "status": "Wired",
                            "status_class": "steady",
                            "module": "Progress",
                            "maturity": "Wired",
                            "what_became_real": "Structured seams now render inside the command center.",
                            "commit_status": "2 local changes still need reconciliation",
                        },
                    ],
                },
                "progress_dashboard": {
                    "summary": "2 useful, 2 wired, 0 durable, 0 compounding modules in the visible Level 3 base.",
                    "item_count": 4,
                    "counts": {"useful": 2, "wired": 2, "durable": 0, "compounding": 0},
                    "items": [
                        {
                            "module": "Command Center/Home",
                            "roadmap_level": "Level 3",
                            "status": "Useful",
                            "status_label": "useful",
                            "status_class": "accepted",
                            "summary": "Live route with needs, memory, activity, missions, seams, and agent operations.",
                            "evidence": "8d7399f feat: add command center registry panel",
                        },
                        {
                            "module": "Agent Operations",
                            "roadmap_level": "Level 3",
                            "status": "Useful",
                            "status_label": "useful",
                            "status_class": "accepted",
                            "summary": "2 running agent(s), 1 blocked, 0 needing attention.",
                            "evidence": "2 running, 1 blocked, 1 needing attention across 4 visible agent(s).",
                        },
                        {
                            "module": "Mission Board",
                            "roadmap_level": "Level 3",
                            "status": "Useful",
                            "status_label": "useful",
                            "status_class": "accepted",
                            "summary": "1 now, 1 next, 0 blocked, 0 completed.",
                            "evidence": "1 now, 1 next, 0 blocked, 0 completed mission lane(s).",
                        },
                        {
                            "module": "Progress",
                            "roadmap_level": "Level 3",
                            "status": "Wired",
                            "status_label": "wired",
                            "status_class": "steady",
                            "summary": "1 useful seam(s), 1 wired seam(s), 0 durable seam(s).",
                            "evidence": "1 useful seam(s), 1 wired seam(s), branch codex/apple-native-command-surface, head abc1234.",
                        },
                    ],
                },
                "failure_recovery": {
                    "integration_issue_count": 1,
                    "recent_failure_count": 1,
                    "pending_approval_count": 1,
                    "dirty_count": 2,
                    "failing_integrations": [
                        {"name": "google-calendar", "detail": "Token refresh failed"}
                    ],
                    "recent_failures": [
                        {"title": "Calendar sync failure", "detail": "error", "timestamp": "2026-06-03T12:05:00+00:00"}
                    ],
                    "action_items": [
                        {"title": "Repair google-calendar", "detail": "Token refresh failed"}
                    ],
                },
                "surfaces": [
                    {"title": "Approval Queue", "path": "/approval-queue"},
                    {"title": "Mission Board", "path": "/mission-board"},
                    {"title": "Activity Feed", "path": "/activity-center"},
                ],
                "brief_preview": {
                    "actor": "Chris",
                    "headline": "1 approval pending, 0 integration issues, 2 memory proposals, 6 registered agents",
                    "supporting_lines": [
                        "Top need: Approve local rollout - high request",
                        "Recent motion: Queued approval surfaced; Calendar sync failure",
                    ],
                    "memory_entry_count": 4,
                    "live_news": True,
                    "rss_articles": 3,
                    "rss_sources": ["AP", "Reuters"],
                    "briefing_text": "Line one\n\nLine two",
                },
                "timeline_preview": {
                    "summary": {
                        "waiting_on_you": 1,
                        "needs_revisit": 1,
                        "recent_motion_count": 2,
                    },
                    "items": [
                        {
                            "item_id": "req-1",
                            "title": "Approve local rollout",
                            "domain": "approvals",
                            "status": "high",
                            "lane": "Scout",
                            "summary": "Queue needs review",
                            "available_actions": [
                                {"id": "approve", "label": "Approve"},
                                {"id": "reject", "label": "Reject"},
                            ],
                        },
                        {
                            "item_id": "follow-up-1",
                            "title": "Approve local rollout",
                            "domain": "approval",
                            "status": "needs-me",
                            "lane": "command-center",
                            "summary": "high request",
                            "available_actions": [],
                        },
                    ],
                    "recent_motion": ["Queued approval surfaced", "Calendar sync failure"],
                },
                "mission_task_board": {
                    "summary": "1 now, 1 next, 0 blocked, 0 completed mission lane(s).",
                    "item_count": 2,
                    "counts": {"now": 1, "next": 1, "blocked": 0, "completed": 0},
                    "items": [
                        {
                            "mission_id": "mission-1",
                            "title": "Keep the family ahead of tomorrow morning weather",
                            "brief": "Translate live weather into practical guidance and family-safe next actions.",
                            "lane": "now",
                            "lane_class": "artifact",
                            "primary_domain": "weather",
                            "owner_agent": "jarvis-orchestrator",
                            "next_step": "Collect live evidence",
                        },
                        {
                            "mission_id": "mission-2",
                            "title": "Design the sculpture fabrication plan",
                            "brief": "Turn workshop intent into a reviewable build path.",
                            "lane": "next",
                            "lane_class": "steady",
                            "primary_domain": "workshop",
                            "owner_agent": "jarvis-orchestrator",
                            "next_step": "Review mission brief",
                        },
                    ],
                },
                "core_modules": {
                    "summary": "7 useful, 4 wired, 1 stubbed core module(s) across the visible Level 3 app base.",
                    "item_count": 12,
                    "counts": {"Useful": 7, "Wired": 4, "Stubbed": 1},
                    "items": [
                        {
                            "module_id": "daily-brief",
                            "title": "Daily Brief",
                            "status": "Useful",
                            "status_label": "useful",
                            "status_class": "accepted",
                            "screen_path": "/briefing-center",
                            "screen_kind": "dedicated route",
                            "roadmap_level": "Level 3",
                            "api_path": "/api/briefing/module",
                            "summary": "Daily Brief now has a dedicated app module route with live briefing text, today-board posture, and open-loop follow-through actions.",
                            "what_became_real": "Daily Brief is now a standalone app module.",
                            "remains_partial": "Deeper briefing-specific action loops still need follow-on slices.",
                            "evidence": "Dedicated /briefing-center route now sits on top of live briefing, today-board, and open-loop APIs.",
                        },
                        {
                            "module_id": "progress",
                            "title": "Progress",
                            "status": "Useful",
                            "status_label": "useful",
                            "status_class": "accepted",
                            "screen_path": "/progress-center",
                            "screen_kind": "dedicated route",
                            "roadmap_level": "Level 3",
                            "api_path": "/api/progress/module",
                            "summary": "Progress now has a dedicated module route with live readiness rows, seam posture, lane state, and failure evidence.",
                            "what_became_real": "Progress is now represented as a standalone app module.",
                            "remains_partial": "Richer progress actions and broader persistence still need follow-on slices.",
                            "evidence": "Dedicated /progress-center route now sits on top of live progress dashboard and seam data.",
                        },
                        {
                            "module_id": "chronicle",
                            "title": "Chronicle",
                            "status": "Useful",
                            "status_label": "useful",
                            "status_class": "accepted",
                            "screen_path": "/chronicle-center",
                            "screen_kind": "dedicated route",
                            "roadmap_level": "Level 3",
                            "api_path": "/api/chronicle/module",
                            "summary": "Chronicle now has a dedicated app module route with live devotional, capture, continuity, and bridge posture.",
                            "what_became_real": "Chronicle is now a standalone app module.",
                            "remains_partial": "Richer Chronicle workflows still need follow-on slices.",
                            "evidence": "Dedicated /chronicle-center route now sits on top of live Chronicle APIs.",
                        },
                        {
                            "module_id": "huddle",
                            "title": "Huddle",
                            "status": "Useful",
                            "status_label": "useful",
                            "status_class": "accepted",
                            "screen_path": "/huddle-center",
                            "screen_kind": "dedicated route",
                            "roadmap_level": "Level 3",
                            "api_path": "/api/huddle/module",
                            "summary": "Huddle now has a dedicated app module route with live standups, runtime posture, dossiers, and idea capture.",
                            "what_became_real": "Huddle is now a standalone app module.",
                            "remains_partial": "Richer huddle workflows still need follow-on slices.",
                            "evidence": "Dedicated /huddle-center route now sits on top of live huddle APIs.",
                        },
                        {
                            "module_id": "health",
                            "title": "Health",
                            "status": "Useful",
                            "status_label": "useful",
                            "status_class": "accepted",
                            "screen_path": "/health-center",
                            "screen_kind": "dedicated route",
                            "roadmap_level": "Level 3",
                            "api_path": "/api/health/module",
                            "summary": "Health now has a dedicated app module route with live drift, baseline, objective, and triage posture.",
                            "what_became_real": "Health is now a standalone app module.",
                            "remains_partial": "Richer health workflows still need follow-on slices.",
                            "evidence": "Dedicated /health-center route now sits on top of live health APIs.",
                        },
                        {
                            "module_id": "navigation",
                            "title": "Navigation",
                            "status": "Useful",
                            "status_label": "useful",
                            "status_class": "accepted",
                            "screen_path": "/navigation-center",
                            "screen_kind": "dedicated route",
                            "roadmap_level": "Level 3",
                            "api_path": "/api/navigation/module",
                            "summary": "Navigation now has a dedicated app module route with persisted route state and live route-preview intelligence.",
                            "what_became_real": "Navigation is now a standalone app module.",
                            "remains_partial": "Richer route continuity still needs follow-on slices.",
                            "evidence": "Dedicated /navigation-center route now sits on top of live navigation APIs.",
                        },
                        {
                            "module_id": "catalyst",
                            "title": "Catalyst",
                            "status": "Useful",
                            "status_label": "useful",
                            "status_class": "accepted",
                            "screen_path": "/catalyst/view/home",
                            "screen_kind": "workspace route",
                            "roadmap_level": "Level 3",
                            "api_path": "/api/catalyst-overview",
                            "summary": "Catalyst already has route-backed workspace pages and live overview data.",
                            "what_became_real": "Catalyst is a real navigable workspace.",
                            "remains_partial": "Cross-workspace continuity can still improve.",
                            "evidence": "Catalyst workspace pages are route-backed under /catalyst/view/*.",
                        },
                        {
                            "module_id": "publish",
                            "title": "Publish",
                            "status": "Useful",
                            "status_label": "useful",
                            "status_class": "accepted",
                            "screen_path": "/publish",
                            "screen_kind": "dedicated route",
                            "roadmap_level": "Level 3",
                            "api_path": "/api/publish/module",
                            "summary": "Publishing now has a dedicated module route with launch, project, calendar, social, and revenue posture.",
                            "what_became_real": "Publish is now a standalone app module route.",
                            "remains_partial": "Broader publishing workflows still need follow-on slices.",
                            "evidence": "Dedicated /publish route now sits on top of live publishing APIs.",
                        },
                        {
                            "module_id": "agent-operations",
                            "title": "Agent Operations",
                            "status": "Useful",
                            "status_label": "useful",
                            "status_class": "accepted",
                            "screen_path": "/agent-ops-center",
                            "screen_kind": "dedicated route",
                            "roadmap_level": "Level 3",
                            "api_path": "/api/agent-ops/module",
                            "summary": "Agent operations now has a dedicated module route with live roster posture, runtime summary, and queue-run controls.",
                            "what_became_real": "Agent operations is now represented as a standalone app module.",
                            "remains_partial": "Richer assignment mutation and deeper per-agent review workflows still need follow-on slices.",
                            "evidence": "Dedicated /agent-ops-center route now sits on top of live roster, scheduler, registry, and runtime APIs.",
                        },
                        {
                            "module_id": "failure-recovery",
                            "title": "Failure & Recovery",
                            "status": "Useful",
                            "status_label": "useful",
                            "status_class": "accepted",
                            "screen_path": "/recovery-center",
                            "screen_kind": "dedicated route",
                            "roadmap_level": "Level 3",
                            "api_path": "/api/recovery/module",
                            "summary": "Failure & Recovery now has a dedicated module route with live recovery posture, recent failure signals, and approval-gated recovery actions.",
                            "what_became_real": "Failure & Recovery is now represented as a standalone app module.",
                            "remains_partial": "Deeper automated remediation and richer retry workflows still need follow-on slices.",
                            "evidence": "Dedicated /recovery-center route now sits on top of live supervision, approval queue, activity, and failure-recovery data.",
                        },
                        {
                            "module_id": "settings-permissions",
                            "title": "Settings & Permissions",
                            "status": "Useful",
                            "status_label": "useful",
                            "status_class": "accepted",
                            "screen_path": "/settings-center",
                            "screen_kind": "dedicated route",
                            "roadmap_level": "Level 3",
                            "api_path": "/api/settings/module",
                            "summary": "Settings now has a dedicated app module route with live voice, location, account, and permissions posture.",
                            "what_became_real": "Settings & Permissions is now a standalone app module.",
                            "remains_partial": "Broader permissions drill-ins and richer save flows still need follow-on slices.",
                            "evidence": "Dedicated /settings-center route now sits on top of live settings and permissions APIs.",
                        },
                    ],
                },
                "open_loop_inspector": {
                    "summary": {
                        "total": 2,
                        "waiting_on_you": 1,
                        "staged": 1,
                        "needs_revisit": 1,
                        "hidden_deferred": 0,
                    },
                    "items": [
                        {
                            "item_id": "req-1",
                            "title": "Approve local rollout",
                            "domain": "approvals",
                            "status": "pending",
                            "owner_agent": "Scout",
                            "summary": "Queue needs review",
                            "next_action": "Resolve approval posture for approve local rollout.",
                            "next_review_at": "2026-06-03T16:00:00+00:00",
                            "auto_execution": {"summary": "Manual approval required before execution."},
                            "available_actions": [
                                {"id": "approve", "label": "Approve"},
                                {"id": "reject", "label": "Reject"},
                            ],
                        }
                    ],
                    "proactive_surface": [
                        {
                            "title": "Approve local rollout",
                            "proactive_reason": "high request",
                        }
                    ],
                    "task_lanes": [
                        {
                            "owner_agent": "Scout",
                            "domain": "approvals",
                            "lane": "Queue needs review",
                            "approval_threshold": {"summary": "Manual approval required before execution."},
                        }
                    ],
                },
                "detail_inspector": {
                    "source_kind": "open-loop",
                    "title": "Approve local rollout",
                    "summary": "Queue needs review",
                    "domain": "approvals",
                    "status": "pending",
                    "owner_agent": "Scout",
                    "next_action": "Resolve approval posture for approve local rollout.",
                    "next_review_at": "2026-06-03T16:00:00+00:00",
                    "autonomy_summary": "Manual approval required before execution.",
                    "available_actions": [
                        {"id": "approve", "label": "Approve"},
                        {"id": "reject", "label": "Reject"},
                    ],
                    "why_now": "Queue needs review",
                    "evidence_lines": [
                        "Owner agent: Scout",
                        "Review schedule: 2026-06-03T16:00:00+00:00",
                        "Autonomy posture: Manual approval required before execution.",
                    ],
                    "decision_history": [
                        {
                            "status": "approved",
                            "actor": "Chris",
                            "when": "2026-06-03T11:40:00+00:00",
                            "resolution": "allow",
                        }
                    ],
                    "approval_review_context": {
                        "request_id": "req-1",
                        "risk_tier": "high",
                        "agent_label": "Scout",
                        "description": "Allow local rollout for health workflow recovery.",
                    },
                    "last_decision_summary": "approved by Chris",
                    "change_summary": "No action diff captured yet.",
                    "action_result_summary": "No action result captured yet.",
                    "change_evidence_summary": "No post-action evidence captured yet.",
                    "field_delta_summary": "No field deltas captured yet.",
                    "contract_delta_summary": "No contract deltas captured yet.",
                    "derived_delta_summary": "No derived deltas captured yet.",
                    "item_timeline": [
                        {
                            "kind": "open-loop",
                            "title": "Approve local rollout",
                            "detail": "Queue needs review",
                            "timestamp": "2026-06-03T10:30:00+00:00",
                        },
                        {
                            "kind": "decision",
                            "title": "approved",
                            "detail": "allow by Chris",
                            "timestamp": "2026-06-03T11:40:00+00:00",
                        },
                        {
                            "kind": "trace",
                            "title": "Queued approval surfaced",
                            "detail": "approvals",
                            "timestamp": "2026-06-03T12:00:00+00:00",
                        },
                    ],
                    "selected_timeline_event": {
                        "kind": "decision",
                        "title": "approved",
                        "detail": "allow by Chris",
                        "timestamp": "2026-06-03T11:40:00+00:00",
                    },
                    "selected_timeline_event_detail": {
                        "evidence_lines": [
                            "Selected from open-loop",
                            "Event kind: decision",
                            "Event timestamp: 2026-06-03T11:40:00+00:00",
                        ],
                        "evidence_links": [
                            {
                                "href": "/api/approval-queue/snapshot",
                                "label": "Approval Queue JSON",
                            },
                            {
                                "href": "/command-center",
                                "label": "Command Center",
                            },
                        ],
                        "preview_title": "Approval Decision Pane",
                        "preview_summary": "Compact approval review context for the selected decision event.",
                        "preview_kind": "decision",
                        "preview_sections": [
                            {
                                "label": "Decision Resolution",
                                "value": "allow",
                            },
                            {
                                "label": "Last Decision",
                                "value": "approved by Chris",
                            },
                            {
                                "label": "Decision Count",
                                "value": "1",
                            },
                            {
                                "label": "Request ID",
                                "value": "req-1",
                            },
                            {
                                "label": "Decision Actor",
                                "value": "Chris",
                            },
                            {
                                "label": "Decision Time",
                                "value": "2026-06-03T11:40:00+00:00",
                            },
                            {
                                "label": "Suggested Action",
                                "value": "Resolve approval posture for approve local rollout.",
                            },
                            {
                                "label": "Priority Hint",
                                "value": "Priority class: high",
                            },
                        ],
                        "decision_history_summary": "approved / allow by Chris",
                        "approval_review_summary": "request=req-1; risk=high; agent=Scout; detail=Allow local rollout for health workflow recovery.",
                        "approval_review_fields": [
                            {
                                "label": "Request",
                                "value": "req-1",
                            },
                            {
                                "label": "Risk Tier",
                                "value": "high",
                            },
                            {
                                "label": "Agent",
                                "value": "Scout",
                            },
                            {
                                "label": "Review Detail",
                                "value": "Allow local rollout for health workflow recovery.",
                            },
                            {
                                "label": "Next Operator Move",
                                "value": "Resolve approval posture for approve local rollout.",
                            },
                        ],
                        "approval_posture_fields": [
                            {
                                "label": "Consent Posture",
                                "value": "Operator consent recorded for this request.",
                            },
                            {
                                "label": "Execution Readiness",
                                "value": "Execution can be triggered directly from this decision pane.",
                            },
                            {
                                "label": "Outcome State",
                                "value": "Latest outcome: approved by Chris",
                            },
                        ],
                        "consequence_fields": [
                            {
                                "label": "Action",
                                "value": "Approve action",
                            },
                            {
                                "label": "Consent Shift",
                                "value": "Awaiting explicit operator consent -> Consent recorded",
                            },
                            {
                                "label": "Readiness Shift",
                                "value": "Execution available once consent is confirmed -> Execution ready from this cockpit",
                            },
                            {
                                "label": "Outcome Shift",
                                "value": "No prior approval outcome recorded -> Latest outcome: approved by Chris",
                            },
                            {
                                "label": "Payload Status",
                                "value": "approved",
                            },
                            {
                                "label": "Payload Resolution",
                                "value": "allow",
                            },
                            {
                                "label": "Payload Request",
                                "value": "req-1",
                            },
                            {
                                "label": "Payload Detail",
                                "value": "Approval returned an allow resolution.",
                            },
                        ],
                        "related_fields": [
                            "status=pending",
                            "next_action=Resolve approval posture for approve local rollout.",
                            "review_by=2026-06-03T16:00:00+00:00",
                        ],
                        "next_actions": [
                            "Consent is now recorded; execution can proceed when the request is ready.",
                            "Returned approval detail confirms allow resolution; execution can proceed when ready.",
                        ],
                        "action_buttons": [
                            {
                                "action": "show-approval-context",
                                "label": "Show Approval Context",
                            },
                            {
                                "endpoint": "/api/approvals/req-1/approve",
                                "method": "POST",
                                "label": "Approve Request",
                            },
                            {
                                "endpoint": "/api/approvals/req-1/reject",
                                "method": "POST",
                                "body": {"reason": "Need a safer plan first"},
                                "label": "Reject Request",
                            },
                            {
                                "endpoint": "/api/approvals/req-1/execute",
                                "method": "POST",
                                "label": "Execute Request",
                            },
                        ],
                    },
                    "recent_trace": [
                        {
                            "title": "Queued approval surfaced",
                            "detail": "approvals",
                            "timestamp": "2026-06-03T12:00:00+00:00",
                        }
                    ],
                },
                "action_journal": {
                    "count": 2,
                    "operator_count": 1,
                    "autonomous_count": 1,
                    "entries": [
                        {
                            "kind": "approval-history",
                            "title": "Approve local rollout",
                            "status": "approved",
                            "detail": "allow",
                            "timestamp": "2026-06-03T11:40:00+00:00",
                            "related_kind": "open-loop",
                            "related_label": "Approve local rollout",
                        },
                        {
                            "kind": "assistant-action",
                            "title": "Queued approval surfaced",
                            "status": "pending",
                            "detail": "approvals",
                            "timestamp": "2026-06-03T12:00:00+00:00",
                            "related_kind": "open-loop",
                            "related_label": "approvals",
                        },
                    ],
                },
                "notification_preview": {
                    "summary": {
                        "total": 2,
                        "unread": 2,
                        "event_signals": 2,
                    },
                    "items": [
                        {
                            "notification_id": "note-1",
                            "title": "Approve local rollout",
                            "status": "unseen",
                            "priority_class": "normal",
                            "why_this_surfaced_now": "high request",
                            "actions": {
                                "open": "/api/assistant-core/notifications/note-1",
                                "ignore": "/api/assistant-core/notifications/note-1",
                            },
                        },
                        {
                            "notification_id": "note-2",
                            "title": "Approve local rollout",
                            "status": "surfaced",
                            "priority_class": "high",
                            "why_this_surfaced_now": "Queue needs review",
                            "actions": {
                                "open": "/api/assistant-core/notifications/note-2",
                                "ignore": "/api/assistant-core/notifications/note-2",
                            },
                        },
                    ],
                    "recent_events": ["Queued approval surfaced", "Calendar sync failure"],
                },
                "surface_count": 4,
                "surfaces": [
                    {
                        "title": "Approval Queue",
                        "path": "/approval-queue",
                        "api": "/api/approval/module",
                        "kind": "final product functionality",
                        "summary": "2 pending approvals, 1 recent decisions.",
                    },
                    {
                        "title": "Supervision Snapshot",
                        "path": "/supervision-snapshot",
                        "api": "/api/supervision/module",
                        "kind": "final product functionality",
                        "summary": "1 approval pending.",
                    },
                    {
                        "title": "Mission Board",
                        "path": "/mission-board",
                        "api": "/api/mission-board/module",
                        "kind": "final product functionality",
                        "summary": "1 now, 1 next, 0 blocked, 0 completed mission lane(s).",
                    },
                    {
                        "title": "Activity Feed",
                        "path": "/activity-center",
                        "api": "/api/activity/module",
                        "kind": "final product functionality",
                        "summary": "2 recent activity event(s) and 2 action journal item(s).",
                    },
                ],
                "json_endpoints": [
                    {"title": "Open Loops", "path": "/api/open-loops", "summary": "Actor-oriented open loop view."},
                    {"title": "Missions", "path": "/api/missions", "summary": "Mission/task board source for active workstreams."}
                ],
                "proof_paths": {
                    "approval_queue": "/approval-queue",
                    "supervision_snapshot": "/supervision-snapshot",
                    "command_center_json": "/api/command-center",
                    "supervision_snapshot_json": "/api/supervision-snapshot",
                    "approval_queue_json": "/api/approval-queue/snapshot",
                    "briefing_json": "/api/briefing?actor=Chris",
                    "open_loops_json": "/api/open-loops?actor=Chris",
                    "missions_json": "/api/missions",
                    "assistant_notifications_json": "/api/assistant-core/notifications?actor=Chris",
                    "agent_registry_json": "/api/agent-registry",
                    "agent_supervision_contracts_json": "/api/agent-supervision/contracts",
                },
            }
        )

        self.assertIn("JARVIS Command Center Index", html)
        self.assertIn("/approval-queue", html)
        self.assertIn("/api/approval/module", html)
        self.assertIn("/supervision-snapshot", html)
        self.assertIn("/api/supervision/module", html)
        self.assertIn("final product functionality", html)
        self.assertIn("/api/open-loops", html)
        self.assertIn("/api/missions", html)
        self.assertIn("Approve local rollout", html)
        self.assertIn("Today at a Glance", html)
        self.assertIn("Last Home Action", html)
        self.assertIn("Hosted Edge", html)
        self.assertIn("https://jarvis.teambinion.org", html)
        self.assertIn("/progress-center#level3-checklist", html)
        self.assertIn("Open Remaining Level 3 Checklist", html)
        self.assertIn("Keep the family ahead of tomorrow morning weather", html)
        self.assertIn("Heimdall", html)
        self.assertIn("Needs Attention", html)
        self.assertIn("Approve Request", html)
        self.assertIn("/api/approvals/req-1/approve", html)
        self.assertIn('data-home-action="1"', html)
        self.assertIn("data-home-route=", html)
        self.assertIn("Move Mission to Now", html)
        self.assertIn("/api/missions/weather-family/status", html)
        self.assertIn("homeActionResult.innerHTML = homeActionResultHtml", html)
        self.assertIn("Next Likely Change", html)
        self.assertIn("buildVisibleActivityEntries", html)
        self.assertIn("/api/activity/home-action", html)
        self.assertIn("/api/activity/operator-action", html)
        self.assertIn("const hasDurableHomeAction = liveEntries.some", html)
        self.assertIn("const hasDurableOperatorAction = liveEntries.some", html)
        self.assertIn("recordHomeActionEvent", html)
        self.assertIn("recordOperatorActionEvent", html)
        self.assertIn('entry_type: isHomeAction ? "home-action" : "local-action"', html)
        self.assertIn("Home action result:", html)
        self.assertIn("homeOverview.innerHTML = homeOverviewHtml", html)
        self.assertIn("Home refreshed:", html)
        self.assertIn("Open Mission Board", html)
        self.assertIn("Command Center Actions", html)
        self.assertIn("Memory Inspector", html)
        self.assertIn("Agent Roster &amp; Ops", html)
        self.assertIn("Heimdall", html)
        self.assertIn("Inspect Agent", html)
        self.assertIn("Morning oversight note", html)
        self.assertIn("Queue posture update", html)
        self.assertIn("Daily Brief Preview", html)
        self.assertIn("Top need: Approve local rollout - high request", html)
        self.assertIn("AP, Reuters", html)
        self.assertIn("Task &amp; Workstream Timeline", html)
        self.assertIn("Mission &amp; Task Board", html)
        self.assertIn("Keep the family ahead of tomorrow morning weather", html)
        self.assertIn("Inspect Mission", html)
        self.assertIn("Core Modules", html)
        self.assertIn("Daily Brief", html)
        self.assertIn("Chronicle", html)
        self.assertIn("Navigation", html)
        self.assertIn("Publish", html)
        self.assertIn("Huddle", html)
        self.assertIn("Health", html)
        self.assertIn("Inspect Module", html)
        self.assertIn("/briefing-center", html)
        self.assertIn("/api/briefing/module", html)
        self.assertIn("/progress-center", html)
        self.assertIn("/api/progress/module", html)
        self.assertIn("/chronicle-center", html)
        self.assertIn("/api/chronicle/module", html)
        self.assertIn("/navigation-center", html)
        self.assertIn("/api/navigation/module", html)
        self.assertIn("/publish", html)
        self.assertIn("/api/publish/module", html)
        self.assertIn("Settings &amp; Permissions", html)
        self.assertIn("/settings-center", html)
        self.assertIn("/api/settings/module", html)
        self.assertIn("/huddle-center", html)
        self.assertIn("/api/huddle/module", html)
        self.assertIn("/health-center", html)
        self.assertIn("/api/health/module", html)
        self.assertIn("/api/catalyst-overview", html)
        self.assertIn("Progress Dashboard", html)
        self.assertIn("Agent Operations", html)
        self.assertIn("Inspect Progress", html)
        self.assertIn("Seam Tracker", html)
        self.assertIn("Command Center Working Base", html)
        self.assertIn("Inspect Seam", html)
        self.assertIn("Recent Motion Detail", html)
        self.assertIn('/api/open-loops/action', html)
        self.assertIn('const body = JSON.stringify({ actor: "Chris", domain, item_id: itemId, action: actionId });', html)
        self.assertIn("Use the inline work controls when items are available.", html)
        self.assertIn("Open-Loop Inspector", html)
        self.assertIn("Item Detail", html)
        self.assertIn("Action Journal", html)
        self.assertIn("operator-driven item(s)", html)
        self.assertIn("autonomous/runtime item(s)", html)
        self.assertIn("Related: open-loop / Approve local rollout", html)
        self.assertIn("Jump to Related", html)
        self.assertIn("Selected Item", html)
        self.assertIn("Why Now", html)
        self.assertIn("Evidence", html)
        self.assertIn("Last Decision", html)
        self.assertIn("Motion Proof Summary", html)
        self.assertIn("Motion Proof Source", html)
        self.assertIn("Motion Proof Snapshot", html)
        self.assertIn("Motion Proof View", html)
        self.assertIn("Motion Proof Excerpts", html)
        self.assertIn("Motion Proof Artifacts", html)
        self.assertIn("Motion Artifact Focus", html)
        self.assertIn("Artifact Mutation", html)
        self.assertIn("Artifact Proof Excerpts", html)
        self.assertIn("Artifact Proof Compare", html)
        self.assertIn("Artifact Recent Actions", html)
        self.assertIn("Current Posture", html)
        self.assertIn("Inspect Action", html)
        self.assertIn("approval /", html)
        self.assertIn("approval first seen", html)
        self.assertIn("approval posture", html)
        self.assertIn("awaiting consent", html)
        self.assertIn("history-chip-approval", html)
        self.assertIn("history-chip-pending", html)
        self.assertIn("Review the approval proof and use the inline request controls when you are ready to decide.", html)
        self.assertIn("Last localized action:", html)
        self.assertIn("Inspect Last Action", html)
        self.assertIn("Reopened approval outcome cue:", html)
        self.assertIn("Suggested next:", html)
        self.assertIn("Reopened next:", html)
        self.assertIn("Why reopened next:", html)
        self.assertIn("Inspect Why", html)
        self.assertIn("Reopened Proof Focus", html)
        self.assertIn("Inspect Timeline Event:", html)
        self.assertIn("Pivot breadcrumbs:", html)
        self.assertIn("history-chip-first-seen", html)
        self.assertIn("Recent outcome mix:", html)
        self.assertIn("No previous approval snapshot yet.", html)
        self.assertIn("Approval posture:", html)
        self.assertIn("Inspect In-Page", html)
        self.assertIn("Change Summary", html)
        self.assertIn("Action Result", html)
        self.assertIn("Why Changed", html)
        self.assertIn("Field Deltas", html)
        self.assertIn("Contract Deltas", html)
        self.assertIn("Derived Deltas", html)
        self.assertIn("Timeline &amp; History", html)
        self.assertIn("Selected Timeline Event", html)
        self.assertIn("Timeline Event Evidence", html)
        self.assertIn("Timeline Event Links", html)
        self.assertIn("Timeline Event Preview", html)
        self.assertIn("Timeline Event Fields", html)
        self.assertIn("Timeline Event Next Actions", html)
        self.assertIn("Show Activity Context", html)
        self.assertIn("No direct event actions available.", html)
        self.assertIn("Decision History", html)
        self.assertIn("Recent Trace", html)
        self.assertIn("Available Actions", html)
        self.assertIn("Owner agent: Scout", html)
        self.assertIn("No action diff captured yet.", html)
        self.assertIn("No action result captured yet.", html)
        self.assertIn("No post-action evidence captured yet.", html)
        self.assertIn("No localized artifact mutation captured yet.", html)
        self.assertIn("No localized artifact mutation rows captured yet.", html)
        self.assertIn("No localized artifact proof excerpts captured yet.", html)
        self.assertIn("No localized artifact proof comparison captured yet.", html)
        self.assertIn("No localized artifact proof comparison rows captured yet.", html)
        self.assertIn("No localized artifact action history captured yet.", html)
        self.assertIn("No localized artifact action history rows captured yet.", html)
        self.assertIn("No field deltas captured yet.", html)
        self.assertIn("No contract deltas captured yet.", html)
        self.assertIn("No derived deltas captured yet.", html)
        self.assertIn("2026-06-03T10:30:00+00:00 · open-loop · Approve local rollout · Queue needs review", html)
        self.assertIn("2026-06-03T12:00:00+00:00 · trace · Queued approval surfaced · approvals", html)
        self.assertIn("Selected from open-loop; Event kind: decision; Event timestamp: 2026-06-03T11:40:00+00:00", html)
        self.assertIn("Approval Queue JSON", html)
        self.assertIn("/api/approval-queue/snapshot", html)
        self.assertIn("Approval Decision Pane", html)
        self.assertIn("Compact approval review context for the selected decision event.", html)
        self.assertIn("Decision Resolution", html)
        self.assertIn("Last Decision", html)
        self.assertIn("Decision Count", html)
        self.assertIn("Request ID", html)
        self.assertIn("Decision Actor", html)
        self.assertIn("Decision Time", html)
        self.assertIn("Suggested Action", html)
        self.assertIn("Priority Hint", html)
        self.assertIn("Approval Review Fields", html)
        self.assertIn("Consent &amp; Readiness", html)
        self.assertIn("What Changed", html)
        self.assertIn("Operator Guidance", html)
        self.assertIn("Consent Posture", html)
        self.assertIn("Execution Readiness", html)
        self.assertIn("Outcome State", html)
        self.assertIn("Action", html)
        self.assertIn("Consent Shift", html)
        self.assertIn("Readiness Shift", html)
        self.assertIn("Outcome Shift", html)
        self.assertIn("Payload Status", html)
        self.assertIn("Payload Resolution", html)
        self.assertIn("Payload Request", html)
        self.assertIn("Payload Detail", html)
        self.assertIn("Request", html)
        self.assertIn("Risk Tier", html)
        self.assertIn("Review Detail", html)
        self.assertIn("Next Operator Move", html)
        self.assertIn("Operator consent recorded for this request.", html)
        self.assertIn("Execution can be triggered directly from this decision pane.", html)
        self.assertIn("Latest outcome: approved by Chris", html)
        self.assertIn("Approve action", html)
        self.assertIn("Awaiting explicit operator consent -&gt; Consent recorded", html)
        self.assertIn("Execution available once consent is confirmed -&gt; Execution ready from this cockpit", html)
        self.assertIn("No prior approval outcome recorded -&gt; Latest outcome: approved by Chris", html)
        self.assertIn("approved", html)
        self.assertIn("allow", html)
        self.assertIn("req-1", html)
        self.assertIn("Approval returned an allow resolution.", html)
        self.assertIn("Recent Approval History", html)
        self.assertIn("Approval Review Block", html)
        self.assertIn("Approval Controls", html)
        self.assertIn("request=req-1; risk=high; agent=Scout; detail=Allow local rollout for health workflow recovery.", html)
        self.assertIn("approvals", html)
        self.assertIn("status=pending; next_action=Resolve approval posture for approve local rollout.; review_by=2026-06-03T16:00:00+00:00", html)
        self.assertIn("Consent is now recorded; execution can proceed when the request is ready.", html)
        self.assertIn("Returned approval detail confirms allow resolution; execution can proceed when ready.", html)
        self.assertIn("Show Approval Context", html)
        self.assertIn("Approve Request", html)
        self.assertIn("Reject Request", html)
        self.assertIn("Execute Request", html)
        self.assertIn("approved by Chris", html)
        self.assertIn("approved / allow by Chris at 2026-06-03T11:40:00+00:00", html)
        self.assertIn("Queued approval surfaced (2026-06-03T12:00:00+00:00): approvals", html)
        self.assertIn("approval-history / approved", html)
        self.assertIn('data-detail-kind="journal"', html)
        self.assertIn("Review by:", html)
        self.assertIn("Autonomy:", html)
        self.assertIn("Use the inline open-loop controls when items are available.", html)
        self.assertIn('data-detail-kind="open-loop"', html)
        self.assertIn('data-detail-kind="notification"', html)
        self.assertIn("Notification &amp; Event Feed", html)
        self.assertIn("Live Notifications", html)
        self.assertIn("/api/assistant-core/notifications/note-1", html)
        self.assertIn('"status":"opened"', html)
        self.assertIn('"status":"ignored"', html)
        self.assertIn("Activity Feed", html)
        self.assertIn("Queued approval surfaced", html)
        self.assertIn("Lane Progress", html)
        self.assertIn("Recent Seams", html)
        self.assertIn("M jarvis/service.py", html)
        self.assertIn("Failure &amp; Recovery", html)
        self.assertIn("Calendar sync failure", html)
        self.assertIn("Repair google-calendar", html)
        self.assertIn("Agent Registry", html)
        self.assertIn("health, household", html)
        self.assertIn("Scout [observe]", html)
        self.assertIn("/api/approvals/req-1/approve", html)
        self.assertIn('memoryInspector.innerHTML = memoryItemHtml', html)
        self.assertIn('briefPreview.innerHTML = briefPreviewHtml', html)
        self.assertIn('timelinePreview.innerHTML = timelinePreviewHtml', html)
        self.assertIn('openLoopInspector.innerHTML = openLoopInspectorHtml', html)
        self.assertIn('let afterDetail = selectedDetail();', html)
        self.assertIn('let currentMotionArtifactIndex = null;', html)
        self.assertIn('if (Number.isInteger(currentMotionArtifactIndex)) {', html)
        self.assertIn('afterDetail = jumpToMotionArtifact(currentMotionArtifactIndex);', html)
        self.assertIn('setDetailInspector(afterDetail);', html)
        self.assertIn('detailInspector.innerHTML = detailInspectorHtml', html)
        self.assertIn('actionJournal.innerHTML = actionJournalHtml(buildActionJournalEntries(approvals, Array.isArray(activity) ? activity : []));', html)
        self.assertIn('attachActionHandlers();', html)
        self.assertIn('return journalDetailAt((currentDetailSelection || {}).index || 0);', html)
        self.assertIn('Related context: ${relatedKind || "activity"} / ${relatedLabel || "Recent action"}', html)
        self.assertIn('function jumpToRelatedFromJournal(index)', html)
        self.assertIn('currentDetailSelection = { kind: "open-loop", index: relatedIndex };', html)
        self.assertIn('detail.change_summary = "Jumped from Action Journal into related open-loop context.";', html)
        self.assertIn('button[data-jump-kind=\'journal-related\']', html)
        self.assertIn('let currentDetailSelection = { kind: "open-loop", index: 0 };', html)
        self.assertIn('let latestChangeSummary = "No action diff captured yet.";', html)
        self.assertIn('latestChangeSummary = summarizeDetailDiff(beforeDetail, afterDetail, pendingActionContext);', html)
        self.assertIn('afterDetail.action_result_summary = actionResultSummary(pendingActionContext);', html)
        self.assertIn('afterDetail.change_evidence_summary = changeEvidenceSummary(beforeDetail, afterDetail, pendingActionContext);', html)
        self.assertIn('afterDetail.motion_artifact_focus_delta_summary = motionArtifactDeltaSummary(beforeDetail, afterDetail, pendingActionContext);', html)
        self.assertIn('afterDetail.motion_artifact_focus_delta_sections = motionArtifactDeltaSections(beforeDetail, afterDetail, pendingActionContext);', html)
        self.assertIn('afterDetail.motion_artifact_focus_excerpts = motionArtifactProofExcerpts(beforeDetail, afterDetail, pendingActionContext);', html)
        self.assertIn('afterDetail.motion_artifact_focus_proof_compare_summary = motionArtifactProofCompareSummary(beforeDetail, afterDetail, pendingActionContext);', html)
        self.assertIn('afterDetail.motion_artifact_focus_proof_compare_rows = motionArtifactProofCompareRows(beforeDetail, afterDetail, pendingActionContext);', html)
        self.assertIn('recordMotionArtifactHistory(afterDetail, pendingActionContext);', html)
        self.assertIn('applyMotionArtifactHistory(afterDetail);', html)
        self.assertIn('afterDetail.field_delta_summary = fieldDeltaSummary(beforeDetail, afterDetail);', html)
        self.assertIn('afterDetail.contract_delta_summary = contractDeltaSummary(beforeDetail, afterDetail);', html)
        self.assertIn('afterDetail.derived_delta_summary = derivedDeltaSummary(beforeDetail, afterDetail);', html)
        self.assertIn('const itemTimeline = Array.isArray(detail.item_timeline) ? detail.item_timeline : [];', html)
        self.assertIn('const selectedTimelineEvent = detail.selected_timeline_event || null;', html)
        self.assertIn('const selectedTimelineEventDetail = detail.selected_timeline_event_detail || null;', html)
        self.assertIn('function buildItemTimeline(entries)', html)
        self.assertIn('function selectedTimelineEventForDetail(detail)', html)
        self.assertIn('function selectedTimelineEventDetailForDetail(detail, event)', html)
        self.assertIn('function performEventAction(action)', html)
        self.assertIn('function approvalConsentPosture(detail)', html)
        self.assertIn('function approvalExecutionReadiness(detail)', html)
        self.assertIn('function approvalOutcomeState(detail)', html)
        self.assertIn('function approvalActionKind(context)', html)
        self.assertIn('function approvalConsequenceFields(before, after, context)', html)
        self.assertIn('function approvalReasonPrescription(payloadReason, actionKind)', html)
        self.assertIn('function approvalRemediationGuidance(before, after, context)', html)
        self.assertIn('function notificationGuidance(detail)', html)
        self.assertIn('function openLoopGuidance(detail)', html)
        self.assertIn('function traceGuidance(detail, event)', html)
        self.assertIn('const errorText = String((context && context.error) || "").trim();', html)
        self.assertIn('const hasPostureShift = beforeConsent !== afterConsent || beforeReadiness !== afterReadiness || beforeOutcome !== afterOutcome;', html)
        self.assertIn('const payloadStatus = String(result.status || result.result || "").trim();', html)
        self.assertIn('const payloadResolution = String(result.resolution || result.outcome || "").trim();', html)
        self.assertIn('const payloadRequestId = String(result.request_id || result.item_id || "").trim();', html)
        self.assertIn('const payloadReason = String(result.detail || result.reason || result.message || "").trim();', html)
        self.assertIn('label: "Failure State"', html)
        self.assertIn('label: "Change Mode"', html)
        self.assertIn('label: "Payload Status"', html)
        self.assertIn('label: "Payload Resolution"', html)
        self.assertIn('label: "Payload Request"', html)
        self.assertIn('label: "Payload Detail"', html)
        self.assertIn('"No posture shift detected"', html)
        self.assertIn('evidence_links: evidenceLinks,', html)
        self.assertIn('preview_title: previewTitle,', html)
        self.assertIn('preview_summary: previewSummary,', html)
        self.assertIn('preview_kind: previewKind,', html)
        self.assertIn('preview_sections: previewSections,', html)
        self.assertIn('if (eventPreviewKind === "decision")', html)
        self.assertIn('else if (eventPreviewKind === "notification")', html)
        self.assertIn('else if (eventPreviewKind === "trace")', html)
        self.assertIn('else if (eventPreviewKind === "open-loop")', html)
        self.assertIn('decision_history_summary: decisionHistorySummary,', html)
        self.assertIn('approval_review_summary: approvalReviewSummary,', html)
        self.assertIn('approval_review_fields: approvalReviewFields,', html)
        self.assertIn('approval_posture_fields: approvalPostureFields,', html)
        self.assertIn('consequence_fields: consequenceFields,', html)
        self.assertIn('notification_snapshot: notificationSnapshotText,', html)
        self.assertIn('const approvalReviewFields = selectedTimelineEventDetail && Array.isArray(selectedTimelineEventDetail.approval_review_fields)', html)
        self.assertIn('const approvalPostureFields = selectedTimelineEventDetail && Array.isArray(selectedTimelineEventDetail.approval_posture_fields)', html)
        self.assertIn('const consequenceFields = selectedTimelineEventDetail && Array.isArray(selectedTimelineEventDetail.consequence_fields)', html)
        self.assertIn('const guidanceLines = selectedTimelineEventDetail && Array.isArray(selectedTimelineEventDetail.next_actions)', html)
        self.assertIn('const notificationNextActions = notificationGuidance(detail);', html)
        self.assertIn('const openLoopNextActions = openLoopGuidance(detail);', html)
        self.assertIn('const traceNextActions = traceGuidance(detail, event);', html)
        self.assertIn('function buildNeedsCockpit(supervision, approvals, openLoops, notifications, activity)', html)
        self.assertIn('function buildNeedsMotion(cockpit, activity)', html)
        self.assertIn('function currentNeedsMotion()', html)
        self.assertIn('function needMotionContext(needKey)', html)
        self.assertIn('function needMotionQueueState(context, overrideStatus = "")', html)
        self.assertIn('function currentAgentOpsRoster() {', html)
        self.assertIn('function agentDetailAt(index) {', html)
        self.assertIn('function agentOpsRosterHtml(roster) {', html)
        self.assertIn('function currentMissionTaskBoard() {', html)
        self.assertIn('function missionDetailAt(index) {', html)
        self.assertIn('function missionTaskBoardHtml(board) {', html)
        self.assertIn('function currentSeamTracker() {', html)
        self.assertIn('function currentCoreModules() {', html)
        self.assertIn('function moduleDetailAt(index) {', html)
        self.assertIn('function coreModulesHtml(board) {', html)
        self.assertIn('function currentProgressDashboard() {', html)
        self.assertIn('function progressDetailAt(index) {', html)
        self.assertIn('function progressDashboardHtml(board) {', html)
        self.assertIn('function seamDetailAt(index) {', html)
        self.assertIn('function findJournalIndexForMotion(item)', html)
        self.assertIn('function jumpToNeedMotion(index)', html)
        self.assertIn('const motionArtifacts = (detail, motionItem) => {', html)
        self.assertIn('function jumpToMotionArtifact(index) {', html)
        self.assertIn('pendingActionContext = { endpoint, beforeDetail, actionLabel, motionArtifactIndex: Number.isInteger(currentMotionArtifactIndex) ? currentMotionArtifactIndex : null };', html)
        self.assertIn('detail.motion_artifact_focus_title = "Approval Artifact Focus";', html)
        self.assertIn('detail.motion_artifact_focus_title = "Notification Artifact Focus";', html)
        self.assertIn('detail.motion_artifact_focus_title = "Open-Loop Artifact Focus";', html)
        self.assertIn('detail.motion_artifact_focus_sections = focusSections;', html)
        self.assertIn('detail.motion_artifact_focus_delta_summary = "No localized artifact mutation captured yet.";', html)
        self.assertIn('detail.motion_artifact_focus_delta_sections = [];', html)
        self.assertIn('detail.motion_artifact_focus_excerpts = [];', html)
        self.assertIn('detail.motion_artifact_focus_proof_compare_summary = "No localized artifact proof comparison captured yet.";', html)
        self.assertIn('detail.motion_artifact_focus_proof_compare_rows = [];', html)
        self.assertIn('detail.motion_artifact_focus_history_summary = "No localized artifact action history captured yet.";', html)
        self.assertIn('detail.motion_artifact_focus_history_meta = "";', html)
        self.assertIn('detail.motion_artifact_focus_history_rows = [];', html)
        self.assertIn('detail.motion_artifact_focus_history_note = "";', html)
        self.assertIn('detail.motion_artifact_focus_actions = focusActions;', html)
        self.assertIn('function motionArtifactFocusValueMap(detail)', html)
        self.assertIn('function motionArtifactFocusKind(detail)', html)
        self.assertIn('function motionArtifactPostureSummary(detail)', html)
        self.assertIn('function motionArtifactPostureBadge(detail)', html)
        self.assertIn('function motionArtifactPostureStateBadge(detail)', html)
        self.assertIn('function motionArtifactPostureHint(detail, context = null)', html)
        self.assertIn('function motionArtifactPostureSuggestedAction(detail)', html)
        self.assertIn('function motionArtifactSnapshotSuggestedAction(detail, entry)', html)
        self.assertIn('function motionArtifactSnapshotActionReason(detail, entry)', html)
        self.assertIn('function motionArtifactSnapshotReasonTarget(detail, entry)', html)
        self.assertIn('function focusMotionArtifactSnapshotReason(detail)', html)
        self.assertIn('function motionArtifactSnapshotPathMeta(pathKind)', html)
        self.assertIn('function motionArtifactSnapshotTargetLabel(detail, pathKind = "proof")', html)
        self.assertIn('function motionArtifactSnapshotTargetButtons(detail)', html)
        self.assertIn('function motionArtifactSnapshotCurrentPathKind(detail)', html)
        self.assertIn('function applyMotionArtifactSnapshotPath(detail, pathKind = "proof")', html)
        self.assertIn('function jumpBackToMotionArtifactSnapshotProof()', html)
        self.assertIn('function jumpToMotionArtifactSnapshotTargetArtifact(index, source = "", historyIndex = null)', html)
        self.assertIn('function jumpToMotionArtifactSnapshotTimeline(index)', html)
        self.assertIn('function jumpToMotionArtifactSnapshotTargetTimeline(index, source = "", historyIndex = null)', html)
        self.assertIn('const pivotSummaryForButtons = (buttons) => {', html)
        self.assertIn('const pivotButtonsForActions = (buttons) => {', html)
        self.assertIn('function motionArtifactPriority(detail)', html)
        self.assertIn('function motionArtifactDomainRows(before, after, context = null)', html)
        self.assertIn('function motionArtifactProofExcerpts(before, after, context = null)', html)
        self.assertIn('function motionArtifactProofCompareRows(before, after, context = null)', html)
        self.assertIn('function motionArtifactProofCompareSummary(before, after, context = null)', html)
        self.assertIn('function motionArtifactHistoryKey(detail)', html)
        self.assertIn('function motionArtifactHistoryRows(detail)', html)
        self.assertIn('last_revisited_lane_label: String(item.last_revisited_lane_label || "").trim(),', html)
        self.assertIn('last_revisited_lane_summary: String(item.last_revisited_lane_summary || "").trim(),', html)
        self.assertIn('function stampMotionArtifactHistoryRevisit(detail, historyIndex, laneKind) {', html)
        self.assertIn('function applyMotionArtifactHistory(detail)', html)
        self.assertIn('function recordMotionArtifactHistory(detail, context = null)', html)
        self.assertIn('function jumpToMotionArtifactHistory(index)', html)
        self.assertIn('let recentMotionArtifactActions = [];', html)
        self.assertIn('actionLabel: "Return to Restored Target Proof",', html)
        self.assertIn('historyButtons: Array.isArray((detail.motion_artifact_focus_posture_snapshot_reason_focus || {}).return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_buttons)', html)
        self.assertIn('status: "returned",', html)
        self.assertIn("Inspect Seam", html)
        self.assertIn('detail.motion_artifact_focus_history_note = `Recent round-trip: ${String(detail.change_evidence_summary || "Returned to restored target proof.").trim()}`;', html)
        self.assertIn('history_buttons: Array.isArray(item.history_buttons) ? item.history_buttons.slice(0, 2) : [],', html)
        self.assertIn('Reopen Round-Trip Artifact', html)
        self.assertIn('Reopen Round-Trip Timeline', html)
        self.assertIn('data-motion-artifact-snapshot-history-target-artifact-index', html)
        self.assertIn('data-motion-artifact-snapshot-history-target-timeline-index', html)
        self.assertIn('data-motion-artifact-snapshot-history-origin-index', html)
        self.assertIn('detail.motion_artifact_focus_history_note = `Round-trip reopen result: artifact lane active for ${String((detail.motion_artifact_focus_posture_snapshot_reason_focus || {}).active_target_label || motionArtifactSnapshotRecordLabel(detail) || "the current localized record").trim()}.`;', html)
        self.assertIn('detail.motion_artifact_focus_history_note = `Round-trip reopen result: timeline lane active for ${String((detail.motion_artifact_focus_posture_snapshot_reason_focus || {}).active_target_label || motionArtifactSnapshotRecordLabel(detail) || "the current localized record").trim()}.`;', html)
        self.assertIn('detail.motion_artifact_focus_round_trip_history_index = Number.isInteger(Number(historyIndex)) ? Number(historyIndex) : null;', html)
        self.assertIn('stampMotionArtifactHistoryRevisit(detail, historyIndex, "artifact");', html)
        self.assertIn('stampMotionArtifactHistoryRevisit(detail, historyIndex, "timeline");', html)
        self.assertIn('applyMotionArtifactHistory(detail);', html)
        self.assertIn('data-motion-artifact-round-trip-history-return-index', html)
        self.assertIn('artifact lane revisited', html)
        self.assertIn('timeline lane revisited', html)
        self.assertIn('Last revisited lane: artifact lane reopened for', html)
        self.assertIn('Last revisited lane: timeline lane reopened for', html)
        self.assertIn('badge: `${String(item.action_kind || "artifact").trim() || "artifact"} / ${String(item.outcome || "updated").trim() || "updated"}`', html)
        self.assertIn('badge_class: actionKind || "artifact",', html)
        self.assertIn('trend_class: trend.includes("recovered")', html)
        self.assertIn('action_kind: actionKind,', html)
        self.assertIn('const actionKind = motionArtifactFocusKind(detail) || "artifact";', html)
        self.assertIn('let trend = "first seen";', html)
        self.assertIn('trend = actionKind === "approval" ? "approval regressed" : actionKind === "notification" ? "inbox regressed" : actionKind === "open-loop" ? "workflow regressed" : "regressed";', html)
        self.assertIn('trend = actionKind === "approval" ? "approval recovered" : actionKind === "notification" ? "inbox recovered" : actionKind === "open-loop" ? "workflow recovered" : "recovered";', html)
        self.assertIn('trend = actionKind === "approval" ? "approval steady" : actionKind === "notification" ? "inbox steady" : actionKind === "open-loop" ? "workflow steady" : "steady";', html)
        self.assertIn('trend = actionKind === "approval" ? "approval shifted" : actionKind === "notification" ? "inbox shifted" : actionKind === "open-loop" ? "workflow shifted" : "shifted";', html)
        self.assertIn('trend = actionKind === "approval" ? "approval first seen" : actionKind === "notification" ? "inbox first seen" : actionKind === "open-loop" ? "workflow first seen" : "first seen";', html)
        self.assertIn('const counts = rows.reduce((acc, item) => {', html)
        self.assertIn('const countSummary = Object.entries(counts).map(([key, value]) => `${value} ${key}`).join(" · ");', html)
        self.assertIn('const comparisonHint = !rows.length', html)
        self.assertIn('const summaryDomain = String((((rows[0] || {}).badge_class) || "artifact")).trim() || "artifact";', html)
        self.assertIn('return `Approval posture: ${status} / ${outcome}`;', html)
        self.assertIn('return `Inbox posture: ${status} / ${whyNow}`;', html)
        self.assertIn('return `Workflow posture: ${status} / ${nextAction}`;', html)
        self.assertIn('return { label: "approval posture", className: "approval" };', html)
        self.assertIn('return { label: "inbox posture", className: "notification" };', html)
        self.assertIn('return { label: "workflow posture", className: "open-loop" };', html)
        self.assertIn('return { label: "awaiting consent", className: "pending" };', html)
        self.assertIn('return { label: "opened", className: "recovered" };', html)
        self.assertIn('return { label: "blocked", className: "regressed" };', html)
        self.assertIn('return "Review the approval proof and use the inline request controls when you are ready to decide.";', html)
        self.assertIn('return "This workflow is blocked; inspect the localized proof and mutation rows before taking the next step.";', html)
        self.assertIn('return "Approval moved just now; review the returned proof and use Execute Request if the exact record still matches intent.";', html)
        self.assertIn('return "Notification was cleared just now; use the stored proof if you need to confirm why this inbox item was dismissed.";', html)
        self.assertIn('return `Approval action failed just now: ${errorText}. Inspect the localized proof and decide whether to retry or reject.`;', html)
        self.assertIn('"No previous approval snapshot yet."', html)
        self.assertIn('"No previous inbox snapshot yet."', html)
        self.assertIn('"No previous workflow snapshot yet."', html)
        self.assertIn('"Same approval snapshot as previous."', html)
        self.assertIn('"Same inbox snapshot as previous."', html)
        self.assertIn('"Same workflow snapshot as previous."', html)
        self.assertIn('"Approval snapshot changed since previous."', html)
        self.assertIn('"Inbox snapshot changed since previous."', html)
        self.assertIn('"Workflow snapshot changed since previous."', html)
        self.assertIn('detail.motion_artifact_focus_history_meta = rows.length ? `Recent outcome mix: ${countSummary}. ${comparisonHint}` : "";', html)
        self.assertIn('detail.motion_artifact_focus_posture_summary = motionArtifactPostureSummary(detail);', html)
        self.assertIn('detail.motion_artifact_focus_posture_badge_label = String((postureBadge && postureBadge.label) || "artifact posture").trim() || "artifact posture";', html)
        self.assertIn('detail.motion_artifact_focus_posture_badge_class = String((postureBadge && postureBadge.className) || "artifact").trim() || "artifact";', html)
        self.assertIn('detail.motion_artifact_focus_posture_state_label = String((postureStateBadge && postureStateBadge.label) || "steady").trim() || "steady";', html)
        self.assertIn('detail.motion_artifact_focus_posture_state_class = String((postureStateBadge && postureStateBadge.className) || "steady").trim() || "steady";', html)
        self.assertIn('detail.motion_artifact_focus_posture_hint = motionArtifactPostureHint(detail);', html)
        self.assertIn('detail.motion_artifact_focus_posture_outcome_line = latestRow', html)
        self.assertIn('detail.motion_artifact_focus_posture_outcome_index = latestRow ? 0 : null;', html)
        self.assertIn('detail.motion_artifact_focus_posture_snapshot_cue = "";', html)
        self.assertIn('detail.motion_artifact_focus_posture_suggested_action = motionArtifactPostureSuggestedAction(detail);', html)
        self.assertIn('detail.motion_artifact_focus_posture_snapshot_action = null;', html)
        self.assertIn('detail.motion_artifact_focus_posture_snapshot_reason = "";', html)
        self.assertIn('detail.motion_artifact_focus_posture_snapshot_reason_target = null;', html)
        self.assertIn('detail.motion_artifact_focus_posture_snapshot_reason_focus = null;', html)
        self.assertIn('timestamp: String(item.timestamp || "recent").trim(),', html)
        self.assertIn('afterDetail.motion_artifact_focus_posture_hint = motionArtifactPostureHint(afterDetail, pendingActionContext);', html)
        self.assertIn('Showing ${rows.length} recent localized action result${rows.length === 1 ? "" : "s"} for this exact record${rows[0] && rows[0].trend ? `; latest trend: ${rows[0].trend}` : ""}.', html)
        self.assertIn('.history-chip-approval {', html)
        self.assertIn('.history-chip-pending {', html)
        self.assertIn('.history-chip-first-seen {', html)
        self.assertIn('detail.change_summary = "Focused a recent localized artifact action from the in-pane history strip.";', html)
        self.assertIn('timeline_event_index: Number.isInteger(currentTimelineEventIndex) ? currentTimelineEventIndex : null,', html)
        self.assertIn('timeline_event_title: String((((detail || {}).selected_timeline_event || {}).title || "").trim(),', html)
        self.assertIn('currentTimelineEventIndex = Number.isInteger(entry.timeline_event_index) ? entry.timeline_event_index : currentTimelineEventIndex;', html)
        self.assertIn('for timeline event ${String(entry.timeline_event_title || "").trim()}', html)
        self.assertIn('Approval Payload Resolution', html)
        self.assertIn('Approval History Proof', html)
        self.assertIn('Notification Payload Status', html)
        self.assertIn('Notification State Proof', html)
        self.assertIn('Open-Loop Record Status', html)
        self.assertIn('Open-Loop Record Detail', html)
        self.assertIn('function motionArtifactDeltaSections(before, after, context = null)', html)
        self.assertIn('function motionArtifactDeltaSummary(before, after, context = null)', html)
        self.assertIn('Approval payload resolution:', html)
        self.assertIn('Notification payload status:', html)
        self.assertIn('Open-loop record status:', html)
        self.assertIn('No localized artifact proof excerpts captured yet.', html)
        self.assertIn('rows.push({ label: "Approval Outcome", value: payloadResolution });', html)
        self.assertIn('rows.push({ label: "Notification Outcome", value: payloadStatus });', html)
        self.assertIn('pushIfChanged("Decision Record", before.last_decision_summary, after.last_decision_summary);', html)
        self.assertIn('pushIfChanged("Notification Status", before.status, after.status);', html)
        self.assertIn('pushIfChanged("Workflow Status", before.status, after.status);', html)
        self.assertIn('rows.push({ label: "Mutation Status", value: "Localized artifact focus refreshed after the action result returned." });', html)
        self.assertIn('rows.push({ label: "Artifact Mutation", value: "No localized artifact field changes captured yet." });', html)
        self.assertIn('detail.motion_proof_panels = [', html)
        self.assertIn('detail.motion_proof_excerpts = [', html)
        self.assertIn('detail.motion_proof_artifacts = motionArtifacts(detail, item);', html)
        self.assertIn('focus_kind: "approval",', html)
        self.assertIn('focus_kind: "notification",', html)
        self.assertIn('focus_kind: "open-loop",', html)
        self.assertIn('action_kind: String(entry.action_kind || "").trim(),', html)
        self.assertIn('action_label: String(entry.action_label || "").trim(),', html)
        self.assertIn('action_summary: String(entry.action_summary || "").trim(),', html)
        self.assertIn('consequence_summary: String(entry.consequence_summary || "").trim(),', html)
        self.assertIn('before_state: beforeState,', html)
        self.assertIn('after_state: afterState,', html)
        self.assertIn('function needsMotionHtml(motion)', html)
        self.assertIn('function recordNeedMotion(entry)', html)
        self.assertIn('function refreshNeedsMotionPanel(cockpit = null, activity = null)', html)
        self.assertIn('function needsNowHtml(cockpit)', html)
        self.assertIn('function jumpToNeedContext(index)', html)
        self.assertIn('function jumpToNeedContextByKey(needKey)', html)
        self.assertIn('function applyNeedsActionState(cockpit)', html)
        self.assertIn('function reconcileNeedsActionState(cockpit)', html)
        self.assertIn('function currentNeedsCockpit()', html)
        self.assertIn('function focusNeedItem(item)', html)
        self.assertIn('const primaryActionButton = (item) =>', html)
        self.assertIn('const guidanceDisplay = guidanceLines.length', html)
        self.assertIn('const previewRows = (items, defaultLabel, valueTag = "span") =>', html)
        self.assertIn('const eventActionButtons = selectedTimelineEventDetail && Array.isArray(selectedTimelineEventDetail.action_buttons) && selectedTimelineEventDetail.action_buttons.length', html)
        self.assertIn('function needsActionState(endpoint, payload, currentState)', html)
        self.assertIn('Approval updated:', html)
        self.assertIn('Notification updated:', html)
        self.assertIn('Open loop updated:', html)
        self.assertIn('Needs Me Now', html)
        self.assertIn('Recent Need Motion', html)
        self.assertIn('Inspect Proof', html)
        self.assertIn('Inspect Need', html)
        self.assertIn('Live Need Snapshot', html)
        self.assertIn('Signal Proof Snapshot', html)
        self.assertIn('Fallback Motion Snapshot', html)
        self.assertIn('Need title:', html)
        self.assertIn('Journal detail:', html)
        self.assertIn('Queue transition:', html)
        self.assertIn('Action cause:', html)
        self.assertIn('Action Cause', html)
        self.assertIn('Action Summary', html)
        self.assertIn('Domain consequence:', html)
        self.assertIn('Domain Consequence', html)
        self.assertIn('Open Open-Loop JSON', html)
        self.assertIn('Open Approval Queue Snapshot', html)
        self.assertIn('Open Notification JSON', html)
        self.assertIn('Request ID', html)
        self.assertIn('Notification ID', html)
        self.assertIn('Item ID', html)
        self.assertIn('Open Notification', html)
        self.assertIn('Ignore Notification', html)
        self.assertIn('data-motion-artifact-index=', html)
        self.assertIn('currentMotionArtifactIndex = Number(index) || 0;', html)
        self.assertIn('Approval Status', html)
        self.assertIn('Decision Record', html)
        self.assertIn('Decision Count', html)
        self.assertIn('Approval Outcome', html)
        self.assertIn('Notification Status', html)
        self.assertIn('Priority Class', html)
        self.assertIn('Surfaced Reason', html)
        self.assertIn('Notification Outcome', html)
        self.assertIn('Workflow Status', html)
        self.assertIn('Timeline Depth', html)
        self.assertIn('failedDetail.motion_artifact_focus_delta_summary = motionArtifactDeltaSummary(beforeDetail || {}, failedDetail, pendingActionContext);', html)
        self.assertIn('failedDetail.motion_artifact_focus_delta_sections = motionArtifactDeltaSections(beforeDetail || {}, failedDetail, pendingActionContext);', html)
        self.assertIn('failedDetail.motion_artifact_focus_excerpts = motionArtifactProofExcerpts(beforeDetail || {}, failedDetail, pendingActionContext);', html)
        self.assertIn('failedDetail.motion_artifact_focus_proof_compare_summary = motionArtifactProofCompareSummary(beforeDetail || {}, failedDetail, pendingActionContext);', html)
        self.assertIn('failedDetail.motion_artifact_focus_proof_compare_rows = motionArtifactProofCompareRows(beforeDetail || {}, failedDetail, pendingActionContext);', html)
        self.assertIn('failedDetail.motion_artifact_focus_posture_hint = motionArtifactPostureHint(failedDetail, pendingActionContext);', html)
        self.assertIn('recordMotionArtifactHistory(failedDetail, pendingActionContext);', html)
        self.assertIn('applyMotionArtifactHistory(failedDetail);', html)
        self.assertIn('data-motion-artifact-history-index=', html)
        self.assertIn('data-motion-artifact-history-index="${esc(String(motionArtifactFocusPostureOutcomeIndex))}"', html)
        self.assertIn('const outcomeLabel = String(entry.outcome || "").trim().toLowerCase();', html)
        self.assertIn('const cueEvidence = String(entry.motion_artifact_focus_proof_compare_summary || entry.change_evidence_summary || "").trim();', html)
        self.assertIn('const focusKind = motionArtifactFocusKind(detail);', html)
        self.assertIn('Reopened approval failure cue:', html)
        self.assertIn('Reopened inbox outcome cue:', html)
        self.assertIn('Reopened workflow outcome cue:', html)
        self.assertIn('detail.motion_artifact_focus_posture_snapshot_action = motionArtifactSnapshotSuggestedAction(detail, entry);', html)
        self.assertIn('detail.motion_artifact_focus_posture_snapshot_reason = motionArtifactSnapshotActionReason(detail, entry);', html)
        self.assertIn('detail.motion_artifact_focus_posture_snapshot_reason_target = motionArtifactSnapshotReasonTarget(detail, Object.assign({}, entry, { history_index: Number(index) || 0 }));', html)
        self.assertIn('history_index: historyIndex,', html)
        self.assertIn('timeline_event_index: timelineEventIndex,', html)
        self.assertIn('action_buttons: actionButtons,', html)
        self.assertIn('breadcrumb: "proof -> action snapshot -> mutation",', html)
        self.assertIn('breadcrumb: "proof -> timeline event -> chronology",', html)
        self.assertIn('pivot_summary: pivotSummaryForButtons(actionButtons),', html)
        self.assertIn('pivot_buttons: pivotButtonsForActions(actionButtons),', html)
        self.assertIn('active_path_label: "proof focus",', html)
        self.assertIn('active_path_class: "first-seen",', html)
        self.assertIn('active_path_summary: "Active path: reopened proof focus.",', html)
        self.assertIn('focus.active_target_label = motionArtifactSnapshotTargetLabel(detail, pathKind);', html)
        self.assertIn('return `Approval proof behind this follow-up: ${proofText}`;', html)
        self.assertIn('return `Inbox proof behind this follow-up: ${proofText}`;', html)
        self.assertIn('return `Workflow proof behind this follow-up: ${proofText}`;', html)
        self.assertIn('summary: "Focused the exact stored proof excerpt behind this reopened next move."', html)
        self.assertIn('summary: "Focused the exact stored proof comparison row behind this reopened next move."', html)
        self.assertIn('return pickAction("execute")', html)
        self.assertIn('return pickAction("open")', html)
        self.assertIn('return { label: "Inspect Workflow Proof", summary: "Reopened next move: inspect the stored workflow failure proof before retrying." };', html)
        self.assertIn('button[data-motion-artifact-snapshot-reason]', html)
        self.assertIn('setDetailInspector(applyMotionArtifactSnapshotPath(selectedDetail(), "proof"));', html)
        self.assertIn('Focused the stored proof behind the reopened next move.', html)
        self.assertIn('Inspect Timeline Event: ${String(target.timeline_event_title || "").trim()}', html)
        self.assertIn('data-timeline-index="${esc(index)}"', html)
        self.assertIn('Pivot breadcrumbs: ${buttons.map((item) => String(item && item.breadcrumb || "").trim()).filter(Boolean).join(" ; ")}', html)
        self.assertIn('label: "Open Mutation",', html)
        self.assertIn('label: "Open Chronology",', html)
        self.assertIn('return {', html)
        self.assertIn('label: "mutation lane",', html)
        self.assertIn('label: "chronology lane",', html)
        self.assertIn('summary: "Active path: reopened mutation lane.",', html)
        self.assertIn('summary: "Active path: reopened chronology lane.",', html)
        self.assertIn('const pathLabel = pathKind === "mutation" ? "mutation lane" : pathKind === "chronology" ? "chronology lane" : "proof focus";', html)
        self.assertIn('return `Active target: ${pathLabel} for approval request ${requestId}.`;', html)
        self.assertIn('return `Active target: ${pathLabel} for inbox item ${notificationId}.`;', html)
        self.assertIn('return `Active target: ${pathLabel} for workflow item ${itemId}.`;', html)
        self.assertIn('function motionArtifactSnapshotRecordLabel(detail)', html)
        self.assertIn('return `approval request ${requestId}`;', html)
        self.assertIn('return `inbox item ${notificationId}`;', html)
        self.assertIn('return `workflow item ${itemId}`;', html)
        self.assertIn('function motionArtifactSnapshotReturnSummary(detail)', html)
        self.assertIn('const latestOutcome = motionArtifactSnapshotReturnOutcome(detail);', html)
        self.assertIn('Approval failure proof resumed for ${recordLabel} after ${latestBadge}.', html)
        self.assertIn('Approval mutation resumed for ${recordLabel} after ${latestBadge}.', html)
        self.assertIn('Inbox opened proof resumed for ${recordLabel} after ${latestBadge}.', html)
        self.assertIn('Inbox failure proof resumed for ${recordLabel} after ${latestBadge}.', html)
        self.assertIn('Workflow failure chronology resumed for ${recordLabel} after ${latestBadge}.', html)
        self.assertIn('Workflow chronology resumed for ${recordLabel} after ${latestBadge}.', html)
        self.assertIn('Workflow failure proof resumed for ${recordLabel} after ${latestBadge}.', html)
        self.assertIn('buttons.push({', html)
        self.assertIn('motion_artifact_index: currentMotionArtifactIndex,', html)
        self.assertIn('label: "Inspect Exact Artifact",', html)
        self.assertIn('label: "Inspect Matching Timeline",', html)
        self.assertIn('if (label.includes("mutation")) return "mutation";', html)
        self.assertIn('if (label.includes("chronology")) return "chronology";', html)
        self.assertIn('focus.active_path_label = String((meta && meta.label) || "proof focus").trim() || "proof focus";', html)
        self.assertIn('focus.active_path_class = String((meta && meta.className) || "first-seen").trim() || "first-seen";', html)
        self.assertIn('focus.active_path_summary = String((meta && meta.summary) || "Active path: reopened proof focus.").trim() || "Active path: reopened proof focus.";', html)
        self.assertIn('const reasonActiveMeta = motionArtifactSnapshotReasonActiveMeta(detail);', html)
        self.assertIn('const reasonActiveTarget = motionArtifactSnapshotReasonActiveTarget(detail);', html)
        self.assertIn('focus.return_history_reason_active_label = pathKind === "proof" && Number.isInteger(focus.return_history_index)', html)
        self.assertIn('focus.return_history_reason_active_class = pathKind === "proof" && Number.isInteger(focus.return_history_index)', html)
        self.assertIn('focus.return_history_reason_active_summary = pathKind === "proof" && Number.isInteger(focus.return_history_index)', html)
        self.assertIn('focus.return_history_reason_active_target = pathKind === "proof" && Number.isInteger(focus.return_history_index)', html)
        self.assertIn('focus.return_history_reason_active_buttons = pathKind === "proof" && Number.isInteger(focus.return_history_index)', html)
        self.assertIn('focus.return_history_reason_active_selection_label = "";', html)
        self.assertIn('focus.return_history_reason_active_selection_class = "steady";', html)
        self.assertIn('focus.return_history_reason_active_selection_summary = "";', html)
        self.assertIn('return_summary: "",', html)
        self.assertIn('return_history_index: null,', html)
        self.assertIn('return_history_label: "",', html)
        self.assertIn('return_history_reason: "",', html)
        self.assertIn('return_history_reason_button_label: "",', html)
        self.assertIn('return_history_reason_source_label: "",', html)
        self.assertIn('return_history_reason_source_class: "artifact",', html)
        self.assertIn('return_history_reason_active_label: "",', html)
        self.assertIn('return_history_reason_active_class: "steady",', html)
        self.assertIn('return_history_reason_active_summary: "",', html)
        self.assertIn('return_history_reason_active_target: "",', html)
        self.assertIn('return_history_reason_active_buttons: [],', html)
        self.assertIn('return_history_reason_active_selection_label: "",', html)
        self.assertIn('return_history_reason_active_selection_class: "steady",', html)
        self.assertIn('return_history_reason_active_selection_summary: "",', html)
        self.assertIn('return_history_reason_resumed_label: "",', html)
        self.assertIn('return_history_reason_resumed_class: "steady",', html)
        self.assertIn('return_history_reason_resumed_summary: "",', html)
        self.assertIn('return_history_reason_resumed_active_label: "",', html)
        self.assertIn('return_history_reason_resumed_active_class: "steady",', html)
        self.assertIn('return_history_reason_resumed_active_summary: "",', html)
        self.assertIn('return_history_reason_resumed_active_buttons: [],', html)
        self.assertIn('return_history_reason_resumed_active_selection_label: "",', html)
        self.assertIn('return_history_reason_resumed_active_selection_class: "steady",', html)
        self.assertIn('return_history_reason_resumed_active_selection_summary: "",', html)
        self.assertIn('return_history_origin_label: "",', html)
        self.assertIn('return_history_origin_class: "artifact",', html)
        self.assertIn('return_history_lane_label: "",', html)
        self.assertIn('return_history_lane_class: "steady",', html)
        self.assertIn('context_summary: "",', html)
        self.assertIn('context_buttons: [],', html)
        self.assertIn('context_selection_label: "",', html)
        self.assertIn('context_selection_class: "steady",', html)
        self.assertIn('context_selection_target: "",', html)
        self.assertIn('context_selection_buttons: [],', html)
        self.assertIn('context_selection_confirmation_label: "",', html)
        self.assertIn('context_selection_confirmation_class: "steady",', html)
        self.assertIn('return_confirmation_label: "",', html)
        self.assertIn('return_confirmation_class: "steady",', html)
        self.assertIn('return_confirmation_summary: "",', html)
        self.assertIn('function motionArtifactSnapshotReturnOriginMeta(detail)', html)
        self.assertIn('function motionArtifactSnapshotReturnOutcome(detail)', html)
        self.assertIn('function motionArtifactSnapshotReturnActionLabel(originMeta, detail)', html)
        self.assertIn('function motionArtifactSnapshotReturnActionReason(originMeta, detail)', html)
        self.assertIn('function motionArtifactSnapshotReturnReasonButtonLabel(detail)', html)
        self.assertIn('function motionArtifactSnapshotReturnReasonSourceMeta(detail)', html)
        self.assertIn('function motionArtifactSnapshotReasonActiveMeta(detail)', html)
        self.assertIn('function motionArtifactSnapshotReasonActiveTarget(detail)', html)
        self.assertIn('function motionArtifactSnapshotReasonActiveButtons(detail)', html)
        self.assertIn('function motionArtifactSnapshotReasonSelectionMeta(targetKind, detail)', html)
        self.assertIn('function motionArtifactSnapshotReasonResumeMeta(detail)', html)
        self.assertIn('function motionArtifactSnapshotReasonResumedActiveMeta(detail)', html)
        self.assertIn('function motionArtifactSnapshotReasonResumedActiveButtons(detail)', html)
        self.assertIn('function motionArtifactSnapshotReasonResumedReturnActiveButtons(detail)', html)
        self.assertIn('function motionArtifactSnapshotReasonResumedReturnSelectionMeta(targetKind, detail)', html)
        self.assertIn('function motionArtifactSnapshotReasonResumedSelectionMeta(targetKind, detail)', html)
        self.assertIn('function motionArtifactSnapshotReturnLaneMeta(originMeta)', html)
        self.assertIn('function motionArtifactSnapshotContextSummary(detail)', html)
        self.assertIn('function motionArtifactSnapshotContextButtons(detail)', html)
        self.assertIn('function motionArtifactSnapshotContextSelection(detail)', html)
        self.assertIn('function motionArtifactSnapshotContextSelectionButtons(detail)', html)
        self.assertIn('Current proof context: ${laneLabel} / ${originLabel} / ${outcome || "updated"} / ${targetLabel}.', html)
        self.assertIn('label: "approval mutation", className: "approval"', html)
        self.assertIn('label: "inbox proof", className: "notification"', html)
        self.assertIn('label: "workflow chronology", className: "open-loop"', html)
        self.assertIn('return badge.split("/").pop().trim();', html)
        self.assertIn('if (label === "approval mutation") return outcome === "failed" ? "Reopen Approval Failure Proof" : "Reopen Approval Mutation";', html)
        self.assertIn('if (label === "approval proof") return "Reopen Approval Proof";', html)
        self.assertIn('if (label === "inbox proof") return outcome === "opened" ? "Reopen Inbox Opened Proof" : outcome === "failed" ? "Reopen Inbox Failure Proof" : "Reopen Inbox Proof";', html)
        self.assertIn('if (label === "workflow chronology") return outcome === "failed" ? "Reopen Workflow Failure Chronology" : "Reopen Workflow Chronology";', html)
        self.assertIn('if (label === "workflow proof") return outcome === "failed" ? "Reopen Workflow Failure Proof" : "Reopen Workflow Proof";', html)
        self.assertIn('if (label === "approval mutation") return outcome === "failed" ? `Reopens the stored approval failure proof for ${recordLabel}.` : `Reopens the stored approval mutation for ${recordLabel}.`;', html)
        self.assertIn('if (label === "workflow chronology") return outcome === "failed" ? `Reopens the stored workflow failure chronology for ${recordLabel}.` : `Reopens the stored workflow chronology for ${recordLabel}.`;', html)
        self.assertIn('if (target.kind === "excerpt") return "Inspect Reopened Proof Excerpt";', html)
        self.assertIn('if (target.kind === "compare") return "Inspect Reopened Proof Compare";', html)
        self.assertIn('if (target.kind === "excerpt") return { label: "proof excerpt", className: "first-seen" };', html)
        self.assertIn('if (target.kind === "compare") return { label: "proof compare", className: "approval" };', html)
        self.assertIn('if (Number.isInteger(target.timeline_event_index)) return { label: "chronology evidence", className: "open-loop" };', html)
        self.assertIn('label: "excerpt proof active",', html)
        self.assertIn('summary: "The reopened proof pane is now anchored on the stored proof excerpt.",', html)
        self.assertIn('label: "compare proof active",', html)
        self.assertIn('summary: "The reopened proof pane is now anchored on the stored proof compare row.",', html)
        self.assertIn('label: "chronology evidence active",', html)
        self.assertIn('summary: "The reopened proof pane is now anchored on the linked chronology evidence.",', html)
        self.assertIn('return `Anchored evidence: ${motionArtifactSnapshotRecordLabel(detail)}.`;', html)
        self.assertIn('label: "Open Evidence Artifact",', html)
        self.assertIn('label: "Open Evidence Timeline",', html)
        self.assertIn('label: "evidence artifact active",', html)
        self.assertIn('summary: `Following the evidence artifact for ${recordLabel}.`,', html)
        self.assertIn('label: "evidence timeline active",', html)
        self.assertIn('summary: `Following the evidence timeline for ${recordLabel}.`,', html)
        self.assertIn('label: "excerpt proof resumed",', html)
        self.assertIn('summary: `Restored the stored proof excerpt for ${recordLabel}.`,', html)
        self.assertIn('label: "compare proof resumed",', html)
        self.assertIn('summary: `Restored the stored proof compare row for ${recordLabel}.`,', html)
        self.assertIn('label: "chronology evidence resumed",', html)
        self.assertIn('summary: `Restored the linked chronology evidence for ${recordLabel}.`,', html)
        self.assertIn('label: "restored excerpt active",', html)
        self.assertIn('summary: `The restored evidence row reopened the stored proof excerpt for ${recordLabel}.`,', html)
        self.assertIn('label: "restored compare active",', html)
        self.assertIn('summary: `The restored evidence row reopened the stored proof compare row for ${recordLabel}.`,', html)
        self.assertIn('label: "restored chronology active",', html)
        self.assertIn('summary: `The restored evidence row reopened the linked chronology evidence for ${recordLabel}.`,', html)
        self.assertIn('label: "Open Restored Evidence Artifact",', html)
        self.assertIn('label: "Open Restored Evidence Timeline",', html)
        self.assertIn('label: "restored evidence artifact active",', html)
        self.assertIn('summary: `Following the restored evidence artifact for ${recordLabel}.`,', html)
        self.assertIn('label: "restored evidence timeline active",', html)
        self.assertIn('summary: `Following the restored evidence timeline for ${recordLabel}.`,', html)
        self.assertIn('label: "restored evidence lane resumed",', html)
        self.assertIn('summary: `Resumed ${resumedLabel} for ${recordLabel} after returning from the restored evidence artifact.`,', html)
        self.assertIn('summary: `Resumed ${resumedLabel} for ${recordLabel} after returning from the restored evidence timeline.`,', html)
        self.assertIn('return "Inspect Resumed Excerpt";', html)
        self.assertIn('return "Inspect Resumed Compare";', html)
        self.assertIn('return "Inspect Resumed Chronology";', html)
        self.assertIn('return "Inspect Resumed Evidence";', html)
        self.assertIn('label: "resumed excerpt active",', html)
        self.assertIn('summary: `The resumed evidence row reopened the stored proof excerpt for ${recordLabel}.`,', html)
        self.assertIn('label: "resumed compare active",', html)
        self.assertIn('summary: `The resumed evidence row reopened the stored proof compare row for ${recordLabel}.`,', html)
        self.assertIn('label: "resumed chronology active",', html)
        self.assertIn('summary: `The resumed evidence row reopened the linked chronology evidence for ${recordLabel}.`,', html)
        self.assertIn('return { label: "mutation lane", className: "approval" };', html)
        self.assertIn('return { label: "chronology lane", className: "open-loop" };', html)
        self.assertIn('return { label: "proof lane", className: "first-seen" };', html)
        self.assertIn('focus.return_summary = motionArtifactSnapshotReturnSummary(detail);', html)
        self.assertIn('focus.return_history_index = Number.isInteger(detail.motion_artifact_focus_posture_outcome_index)', html)
        self.assertIn('focus.return_history_label = focus.return_history_index !== null', html)
        self.assertIn('focus.return_history_reason = focus.return_history_index !== null', html)
        self.assertIn('focus.return_history_reason_button_label = focus.return_history_index !== null', html)
        self.assertIn('focus.return_history_reason_source_label = focus.return_history_index !== null', html)
        self.assertIn('focus.return_history_reason_source_class = focus.return_history_index !== null', html)
        self.assertIn('motionArtifactSnapshotReturnActionLabel(returnOrigin, detail)', html)
        self.assertIn('motionArtifactSnapshotReturnActionReason(returnOrigin, detail)', html)
        self.assertIn('motionArtifactSnapshotReturnReasonButtonLabel(detail)', html)
        self.assertIn('motionArtifactSnapshotReturnReasonSourceMeta(detail)', html)
        self.assertIn('focus.return_history_origin_label = focus.return_history_index !== null', html)
        self.assertIn('focus.return_history_origin_class = String((returnOrigin && returnOrigin.className) || "artifact").trim() || "artifact";', html)
        self.assertIn('const returnLane = motionArtifactSnapshotReturnLaneMeta(returnOrigin);', html)
        self.assertIn('focus.return_history_lane_label = focus.return_history_index !== null', html)
        self.assertIn('focus.return_history_lane_class = focus.return_history_index !== null', html)
        self.assertIn('focus.return_summary = pathKind === "proof"', html)
        self.assertIn('focus.return_history_index = pathKind === "proof" && Number.isInteger(focus.return_history_index)', html)
        self.assertIn('focus.return_history_label = pathKind === "proof" && focus.return_history_index !== null', html)
        self.assertIn('focus.return_history_reason = pathKind === "proof" && focus.return_history_index !== null', html)
        self.assertIn('focus.return_history_reason_button_label = pathKind === "proof" && focus.return_history_index !== null', html)
        self.assertIn('focus.return_history_reason_source_label = pathKind === "proof" && focus.return_history_index !== null', html)
        self.assertIn('focus.return_history_reason_source_class = pathKind === "proof" && focus.return_history_index !== null', html)
        self.assertIn('focus.return_history_origin_label = pathKind === "proof" && focus.return_history_index !== null', html)
        self.assertIn('focus.return_history_origin_class = pathKind === "proof" && focus.return_history_index !== null', html)
        self.assertIn('focus.return_history_lane_label = pathKind === "proof" && focus.return_history_index !== null', html)
        self.assertIn('focus.return_history_lane_class = pathKind === "proof" && focus.return_history_index !== null', html)
        self.assertIn('focus.context_buttons = motionArtifactSnapshotContextButtons(detail);', html)
        self.assertIn('focus.context_selection_label = String((contextSelection && contextSelection.label) || "").trim();', html)
        self.assertIn('focus.context_selection_class = String((contextSelection && contextSelection.className) || "steady").trim() || "steady";', html)
        self.assertIn('focus.context_selection_target = String((contextSelection && contextSelection.target) || "").trim();', html)
        self.assertIn('focus.context_selection_buttons = motionArtifactSnapshotContextSelectionButtons(detail);', html)
        self.assertIn('focus.context_selection_confirmation_label = "";', html)
        self.assertIn('focus.context_selection_confirmation_class = "steady";', html)
        self.assertIn('focus.return_confirmation_label = "";', html)
        self.assertIn('focus.return_confirmation_class = "steady";', html)
        self.assertIn('focus.return_confirmation_summary = "";', html)
        self.assertIn('focus.return_history_reason_resumed_label = "";', html)
        self.assertIn('focus.return_history_reason_resumed_class = "steady";', html)
        self.assertIn('focus.return_history_reason_resumed_summary = "";', html)
        self.assertIn('focus.return_history_reason_resumed_active_label = "";', html)
        self.assertIn('focus.return_history_reason_resumed_active_class = "steady";', html)
        self.assertIn('focus.return_history_reason_resumed_active_summary = "";', html)
        self.assertIn('focus.return_history_reason_resumed_active_buttons = [];', html)
        self.assertIn('focus.return_history_reason_resumed_active_selection_label = "";', html)
        self.assertIn('focus.return_history_reason_resumed_active_selection_class = "steady";', html)
        self.assertIn('focus.return_history_reason_resumed_active_selection_summary = "";', html)
        self.assertIn('focus.return_history_reason_resumed_return_label = "";', html)
        self.assertIn('focus.return_history_reason_resumed_return_class = "steady";', html)
        self.assertIn('focus.return_history_reason_resumed_return_summary = "";', html)
        self.assertIn('focus.return_history_reason_resumed_return_button_label = "";', html)
        self.assertIn('focus.return_history_reason_resumed_return_active_label = "";', html)
        self.assertIn('focus.return_history_reason_resumed_return_active_class = "steady";', html)
        self.assertIn('focus.return_history_reason_resumed_return_active_summary = "";', html)
        self.assertIn('focus.return_history_reason_resumed_return_active_buttons = [];', html)
        self.assertIn('focus.return_history_reason_resumed_return_active_selection_label = "";', html)
        self.assertIn('focus.return_history_reason_resumed_return_active_selection_class = "steady";', html)
        self.assertIn('focus.return_history_reason_resumed_return_active_selection_summary = "";', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_label = "";', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_class = "steady";', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_summary = "";', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_button_label = "";', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_active_label = "";', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_active_class = "steady";', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_active_summary = "";', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_active_buttons = [];', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_active_selection_label = "";', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_active_selection_class = "steady";', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_active_selection_summary = "";', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_label = "";', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_class = "steady";', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_summary = "";', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_active_label = "";', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_active_class = "steady";', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_active_summary = "";', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_active_buttons = [];', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_active_selection_label = "";', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_active_selection_class = "steady";', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_active_selection_summary = "";', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_label = "";', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_class = "steady";', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_summary = "";', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_buttons = [];', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_label = "";', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_class = "steady";', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_summary = "";', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_buttons = [];', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_active_label = "";', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_active_class = "steady";', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_active_summary = "";', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_label = "";', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_class = "steady";', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_summary = "";', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_buttons = [];', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_active_label = "";', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_active_class = "steady";', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_active_summary = "";', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_return_label = "";', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_return_class = "steady";', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_return_summary = "";', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_return_buttons = [];', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_return_active_label = "";', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_return_active_class = "steady";', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_return_active_summary = "";', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_label = "";', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_class = "steady";', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_summary = "";', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_buttons = [];', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_active_label = "";', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_active_class = "steady";', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_active_summary = "";', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_label = "";', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_class = "steady";', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_summary = "";', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_buttons = [];', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_active_label = "";', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_active_class = "steady";', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_active_summary = "";', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_active_label = "";', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_active_class = "steady";', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_active_summary = "";', html)
        self.assertIn('label: "Open Mutation Lane"', html)
        self.assertIn('active_label: "Open Mutation Lane (Current)"', html)
        self.assertIn('label: "Open Chronology Lane"', html)
        self.assertIn('active_label: "Open Chronology Lane (Current)"', html)
        self.assertIn('active_label: "Open Proof Lane (Current)"', html)
        self.assertIn('const targetSummary = `Anchored to ${recordLabel}.`;', html)
        self.assertIn('label: "Open Anchored Timeline",', html)
        self.assertIn('label: "Open Anchored Artifact",', html)
        self.assertIn('return { label: "mutation lane active", className: "steady", target: targetSummary };', html)
        self.assertIn('return { label: "chronology lane active", className: "accepted", target: targetSummary };', html)
        self.assertIn('return { label: "proof lane active", className: "first-seen", target: targetSummary };', html)
        self.assertIn('focus.active_target_buttons = motionArtifactSnapshotTargetButtons(detail);', html)
        self.assertIn('detail.motion_artifact_focus_posture_snapshot_reason = reasonText;', html)
        self.assertIn('detail.motion_artifact_focus_posture_snapshot_action = snapshotAction;', html)
        self.assertIn('detail.change_summary = "Focused reopened proof chronology from the proof pivot strip.";', html)
        self.assertIn('detail.change_summary = "Confirmed the reopened proof target artifact in the shared inspector.";', html)
        self.assertIn('detail.change_summary = "Confirmed the reopened proof target timeline in the shared inspector.";', html)
        self.assertIn('const evidenceSelection = motionArtifactSnapshotReasonSelectionMeta("artifact", detail);', html)
        self.assertIn('const evidenceSelection = motionArtifactSnapshotReasonSelectionMeta("timeline", detail);', html)
        self.assertIn('detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_active_selection_label = String((evidenceSelection && evidenceSelection.label) || "").trim();', html)
        self.assertIn('detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_active_selection_class = String((evidenceSelection && evidenceSelection.className) || "steady").trim() || "steady";', html)
        self.assertIn('detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_active_selection_summary = String((evidenceSelection && evidenceSelection.summary) || "").trim();', html)
        self.assertIn('const restoredSelection = motionArtifactSnapshotReasonResumedSelectionMeta("artifact", detail);', html)
        self.assertIn('const restoredSelection = motionArtifactSnapshotReasonResumedSelectionMeta("timeline", detail);', html)
        self.assertIn('const resumedTargetSelection = motionArtifactSnapshotReasonResumedReturnSelectionMeta("artifact", detail);', html)
        self.assertIn('const resumedTargetSelection = motionArtifactSnapshotReasonResumedReturnSelectionMeta("timeline", detail);', html)
        self.assertIn('const resumedRestoredTargetSelection = motionArtifactSnapshotReasonResumedReturnReturnSelectionMeta("artifact", detail);', html)
        self.assertIn('const resumedRestoredTargetSelection = motionArtifactSnapshotReasonResumedReturnReturnSelectionMeta("timeline", detail);', html)
        self.assertIn('const resumedRestoredFocusSelection = motionArtifactSnapshotReasonResumedReturnReturnReturnSelectionMeta("artifact", detail);', html)
        self.assertIn('const resumedRestoredFocusSelection = motionArtifactSnapshotReasonResumedReturnReturnReturnSelectionMeta("timeline", detail);', html)
        self.assertIn('const resumedRestoredFocusRestoredSelection = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnSelectionMeta("artifact", detail);', html)
        self.assertIn('const resumedRestoredFocusRestoredSelection = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnSelectionMeta("timeline", detail);', html)
        self.assertIn('const confirmedResumedRestoredFocusSelection = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnSelectionMeta("artifact", detail);', html)
        self.assertIn('const confirmedResumedRestoredFocusSelection = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnSelectionMeta("timeline", detail);', html)
        self.assertIn('detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_active_selection_label = String((restoredSelection && restoredSelection.label) || "").trim();', html)
        self.assertIn('detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_active_selection_class = String((restoredSelection && restoredSelection.className) || "steady").trim() || "steady";', html)
        self.assertIn('detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_active_selection_summary = String((restoredSelection && restoredSelection.summary) || "").trim();', html)
        self.assertIn('detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_active_selection_label = String((resumedTargetSelection && resumedTargetSelection.label) || "").trim();', html)
        self.assertIn('detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_active_selection_class = String((resumedTargetSelection && resumedTargetSelection.className) || "steady").trim() || "steady";', html)
        self.assertIn('detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_active_selection_summary = String((resumedTargetSelection && resumedTargetSelection.summary) || "").trim();', html)
        self.assertIn('detail.motion_artifact_focus_posture_snapshot_reason_focus.context_selection_confirmation_label = "anchored artifact active";', html)
        self.assertIn('detail.motion_artifact_focus_posture_snapshot_reason_focus.context_selection_confirmation_label = "anchored timeline active";', html)
        self.assertIn('focus.return_confirmation_label = "proof lane restored";', html)
        self.assertIn('focus.return_confirmation_summary = `Restored reopened proof context for ${motionArtifactSnapshotRecordLabel(detail)}.`;', html)
        self.assertIn('const returnReasonResume = motionArtifactSnapshotReasonResumeMeta(detail);', html)
        self.assertIn('focus.return_history_reason_resumed_label = String((returnReasonResume && returnReasonResume.label) || "").trim();', html)
        self.assertIn('focus.return_history_reason_resumed_class = String((returnReasonResume && returnReasonResume.className) || "steady").trim() || "steady";', html)
        self.assertIn('focus.return_history_reason_resumed_summary = String((returnReasonResume && returnReasonResume.summary) || "").trim();', html)
        self.assertIn('focus.return_history_reason_resumed_active_label = String((resumedActive && resumedActive.label) || "").trim();', html)
        self.assertIn('focus.return_history_reason_resumed_active_class = String((resumedActive && resumedActive.className) || "steady").trim() || "steady";', html)
        self.assertIn('focus.return_history_reason_resumed_active_summary = String((resumedActive && resumedActive.summary) || "").trim();', html)
        self.assertIn('focus.return_history_reason_resumed_active_buttons = resumedButtons;', html)
        self.assertIn('const resumedReturn = motionArtifactSnapshotReasonResumedReturnMeta(detail, restoredSelectionLabel);', html)
        self.assertIn('const resumedReturnButtonLabel = motionArtifactSnapshotReasonResumedReturnButtonLabel(detail);', html)
        self.assertIn('const resumedReturnActive = motionArtifactSnapshotReasonResumedReturnActiveMeta(detail);', html)
        self.assertIn('const resumedReturnActiveButtons = motionArtifactSnapshotReasonResumedReturnActiveButtons(detail);', html)
        self.assertIn('const resumedReturnSelectionLabel = String((currentFocus && currentFocus.return_history_reason_resumed_return_active_selection_label) || "").trim();', html)
        self.assertIn('const resumedReturnReturnLabel = String((currentFocus && currentFocus.return_history_reason_resumed_return_return_label) || "").trim();', html)
        self.assertIn('const resumedReturnReturnSelectionLabel = String((currentFocus && currentFocus.return_history_reason_resumed_return_return_active_selection_label) || "").trim();', html)
        self.assertIn('const resumedReturnReturnReturnSelectionLabel = String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_active_selection_label) || "").trim();', html)
        self.assertIn('const resumedReturnReturnReturnReturnActiveLabel = String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_return_active_label) || "").trim();', html)
        self.assertIn('const confirmedResumedRestoredFocusActiveLabel = String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_return_return_active_label) || "").trim();', html)
        self.assertIn('const reopenedConfirmedResumedRestoredFocusActiveLabel = String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_return_return_return_active_label) || "").trim();', html)
        self.assertIn('const reopenedReopenedConfirmedFocusActiveLabel = String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_return_return_return_return_active_label) || "").trim();', html)
        self.assertIn('const reopenedReopenedReopenedConfirmedFocusActiveLabel = String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_return_return_return_return_return_active_label) || "").trim();', html)
        self.assertIn('const reopenedReopenedReopenedReconfirmedFocusActiveLabel = String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_active_label) || "").trim();', html)
        self.assertIn('const reopenedReopenedReopenedReopenedReconfirmedFocusActiveLabel = String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_active_label) || "").trim();', html)
        self.assertIn('const resumedReturnReturn = motionArtifactSnapshotReasonResumedReturnReturnMeta(detail, resumedReturnSelectionLabel);', html)
        self.assertIn('const resumedReturnReturnButtonLabel = motionArtifactSnapshotReasonResumedReturnReturnButtonLabel(detail);', html)
        self.assertIn('const resumedReturnReturnActive = motionArtifactSnapshotReasonResumedReturnReturnActiveMeta(detail);', html)
        self.assertIn('const resumedReturnReturnActiveButtons = motionArtifactSnapshotReasonResumedReturnReturnActiveButtons(detail);', html)
        self.assertIn('const resumedReturnReturnReturn = motionArtifactSnapshotReasonResumedReturnReturnReturnMeta(detail, resumedReturnReturnSelectionLabel);', html)
        self.assertIn('const resumedReturnReturnReturnActive = motionArtifactSnapshotReasonResumedReturnReturnReturnActiveMeta(detail);', html)
        self.assertIn('const resumedReturnReturnReturnActiveButtons = motionArtifactSnapshotReasonResumedReturnReturnReturnActiveButtons(detail);', html)
        self.assertIn('const resumedReturnReturnReturnReturn = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnMeta(detail, resumedReturnReturnReturnSelectionLabel);', html)
        self.assertIn('const resumedReturnReturnReturnReturnReturn = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnMeta(detail, resumedReturnReturnReturnSelectionLabel, resumedReturnReturnReturnReturnActiveLabel);', html)
        self.assertIn('const resumedReturnReturnReturnReturnReturnButtons = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnButtons(detail, resumedReturnReturnReturnReturnActiveLabel);', html)
        self.assertIn('const resumedReturnReturnReturnReturnReturnReturn = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnMeta(detail, confirmedResumedRestoredFocusActiveLabel);', html)
        self.assertIn('const resumedReturnReturnReturnReturnReturnReturnButtons = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnButtons(detail, confirmedResumedRestoredFocusActiveLabel);', html)
        self.assertIn('const resumedReturnReturnReturnReturnReturnReturnReturn = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnMeta(detail, reopenedConfirmedResumedRestoredFocusActiveLabel);', html)
        self.assertIn('const resumedReturnReturnReturnReturnReturnReturnReturnButtons = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnButtons(detail, reopenedConfirmedResumedRestoredFocusActiveLabel);', html)
        self.assertIn('const resumedReturnReturnReturnReturnReturnReturnReturnReturn = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnMeta(detail, reopenedReopenedConfirmedFocusActiveLabel);', html)
        self.assertIn('const resumedReturnReturnReturnReturnReturnReturnReturnReturnButtons = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnButtons(detail, reopenedReopenedConfirmedFocusActiveLabel);', html)
        self.assertIn('const resumedReturnReturnReturnReturnReturnReturnReturnReturnReturn = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnMeta(detail, reopenedReopenedReopenedConfirmedFocusActiveLabel);', html)
        self.assertIn('const resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnButtons = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnButtons(detail, reopenedReopenedReopenedConfirmedFocusActiveLabel);', html)
        self.assertIn('const resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturn = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnMeta(detail, reopenedReopenedReopenedReconfirmedFocusActiveLabel);', html)
        self.assertIn('const resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnButtons = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnButtons(detail, reopenedReopenedReopenedReconfirmedFocusActiveLabel);', html)
        self.assertIn('const resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturn = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnMeta(detail, reopenedReopenedReopenedReopenedReconfirmedFocusActiveLabel);', html)
        self.assertIn('const resumedReturnReturnReturnReturnButtons = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnButtons(detail);', html)
        self.assertIn('focus.return_history_reason_resumed_return_label = restoredSelectionLabel', html)
        self.assertIn('focus.return_history_reason_resumed_return_class = restoredSelectionLabel', html)
        self.assertIn('focus.return_history_reason_resumed_return_summary = restoredSelectionLabel', html)
        self.assertIn('focus.return_history_reason_resumed_return_button_label = restoredSelectionLabel', html)
        self.assertIn('focus.return_history_reason_resumed_return_active_label = resumedReturnLabel', html)
        self.assertIn('focus.return_history_reason_resumed_return_active_class = resumedReturnLabel', html)
        self.assertIn('focus.return_history_reason_resumed_return_active_summary = resumedReturnLabel', html)
        self.assertIn('focus.return_history_reason_resumed_return_active_buttons = resumedReturnLabel', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_label = resumedReturnSelectionLabel', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_class = resumedReturnSelectionLabel', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_summary = resumedReturnSelectionLabel', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_button_label = resumedReturnSelectionLabel', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_active_label = resumedReturnReturnLabel', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_active_class = resumedReturnReturnLabel', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_active_summary = resumedReturnReturnLabel', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_active_buttons = resumedReturnReturnLabel', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_label = resumedReturnReturnSelectionLabel && ["resumed-restored-return", "resumed-restored-reason", "resumed-restored-focus-return"].includes(String(mode || "").trim())', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_class = resumedReturnReturnSelectionLabel && ["resumed-restored-return", "resumed-restored-reason", "resumed-restored-focus-return"].includes(String(mode || "").trim())', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_summary = resumedReturnReturnSelectionLabel && ["resumed-restored-return", "resumed-restored-reason", "resumed-restored-focus-return"].includes(String(mode || "").trim())', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_active_label = String(mode || "").trim() === "resumed-restored-reason"', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_active_class = String(mode || "").trim() === "resumed-restored-reason"', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_active_summary = String(mode || "").trim() === "resumed-restored-reason"', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_active_buttons = String(mode || "").trim() === "resumed-restored-reason"', html)
        self.assertIn('detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_active_selection_label = String((resumedRestoredFocusSelection && resumedRestoredFocusSelection.label) || "").trim();', html)
        self.assertIn('detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_active_selection_class = String((resumedRestoredFocusSelection && resumedRestoredFocusSelection.className) || "steady").trim() || "steady";', html)
        self.assertIn('detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_active_selection_summary = String((resumedRestoredFocusSelection && resumedRestoredFocusSelection.summary) || "").trim();', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_label = resumedReturnReturnReturnSelectionLabel && String(mode || "").trim() === "resumed-restored-focus-return"', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_class = resumedReturnReturnReturnSelectionLabel && String(mode || "").trim() === "resumed-restored-focus-return"', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_summary = resumedReturnReturnReturnSelectionLabel && String(mode || "").trim() === "resumed-restored-focus-return"', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_buttons = resumedReturnReturnReturnSelectionLabel && String(mode || "").trim() === "resumed-restored-focus-return"', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_label = resumedReturnReturnReturnSelectionLabel && String(mode || "").trim() === "resumed-restored-focus-return"', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_class = resumedReturnReturnReturnSelectionLabel && String(mode || "").trim() === "resumed-restored-focus-return"', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_summary = resumedReturnReturnReturnSelectionLabel && String(mode || "").trim() === "resumed-restored-focus-return"', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_buttons = resumedReturnReturnReturnSelectionLabel && String(mode || "").trim() === "resumed-restored-focus-return"', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_label = confirmedResumedRestoredFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_class = confirmedResumedRestoredFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_summary = confirmedResumedRestoredFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_buttons = confirmedResumedRestoredFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_return_label = reopenedConfirmedResumedRestoredFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_return_class = reopenedConfirmedResumedRestoredFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_return_summary = reopenedConfirmedResumedRestoredFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_return_buttons = reopenedConfirmedResumedRestoredFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_label = reopenedReopenedConfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_class = reopenedReopenedConfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_summary = reopenedReopenedConfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_buttons = reopenedReopenedConfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_label = reopenedReopenedReopenedConfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_class = reopenedReopenedReopenedConfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_summary = reopenedReopenedReopenedConfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_buttons = reopenedReopenedReopenedConfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_label = reopenedReopenedReopenedReconfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_class = reopenedReopenedReopenedReconfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_summary = reopenedReopenedReopenedReconfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_buttons = reopenedReopenedReopenedReconfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_label = reopenedReopenedReopenedReopenedReconfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_class = reopenedReopenedReopenedReopenedReconfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_summary = reopenedReopenedReopenedReopenedReconfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"', html)
        self.assertIn('function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnButtons(detail, sourceLabel) {', html)
        self.assertIn('function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnSelectionMeta(targetKind, detail) {', html)
        self.assertIn('function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnSelectionMeta(targetKind, detail) {', html)
        self.assertIn('function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnMeta(detail, sourceLabel) {', html)
        self.assertIn('function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnMeta(detail, sourceLabel) {', html)
        self.assertIn('function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnMeta(detail, sourceLabel) {', html)
        self.assertIn('function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnButtons(detail, sourceLabel) {', html)
        self.assertIn('function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnSelectionMeta(targetKind, detail) {', html)
        self.assertIn('function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnMeta(detail, sourceLabel) {', html)
        self.assertIn('function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnButtons(detail, sourceLabel) {', html)
        self.assertIn('function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnSelectionMeta(targetKind, detail) {', html)
        self.assertIn('function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnSelectionMeta(targetKind, detail) {', html)
        self.assertIn('function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnButtons(detail, sourceLabel) {', html)
        self.assertIn('function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnButtons(detail, sourceLabel) {', html)
        self.assertIn('const resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnButtons = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnButtons(detail, reopenedReopenedReopenedReopenedReconfirmedFocusActiveLabel);', html)
        self.assertIn('const reopenedReopenedReopenedReopenedReopenedReconfirmedFocusActiveLabel = String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_active_label) || "").trim();', html)
        self.assertIn('const resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturn = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnMeta(detail, reopenedReopenedReopenedReopenedReopenedReconfirmedFocusActiveLabel);', html)
        self.assertIn('const resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnButtons = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnButtons(detail, reopenedReopenedReopenedReopenedReopenedReconfirmedFocusActiveLabel);', html)
        self.assertIn('const reopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusActiveLabel = String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_active_label) || "").trim();', html)
        self.assertIn('const resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturn = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnMeta(detail, reopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusActiveLabel);', html)
        self.assertIn('const resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnButtons = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnButtons(detail, reopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusActiveLabel);', html)
        self.assertIn('const reopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusActiveLabel = String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_active_label) || "").trim();', html)
        self.assertIn('const resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturn = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnMeta(detail, reopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusActiveLabel);', html)
        self.assertIn('const resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnButtons = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnButtons(detail, reopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusActiveLabel);', html)
        self.assertIn('const reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusActiveLabel = String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_label) || "").trim();', html)
        self.assertIn('const resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturn = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnMeta(detail, reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusActiveLabel);', html)
        self.assertIn('const resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnButtons = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnButtons(detail, reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusActiveLabel);', html)
        self.assertIn('const reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusActiveLabel = String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_label) || "").trim();', html)
        self.assertIn('const resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturn = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnMeta(detail, reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusActiveLabel);', html)
        self.assertIn('const resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnButtons = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnButtons(detail, reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusActiveLabel);', html)
        self.assertIn('function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnSelectionMeta(targetKind, detail) {', html)
        self.assertIn('const resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnActive = Boolean(String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_label) || "").trim());', html)
        self.assertIn('const resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnActive = Boolean(String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_label) || "").trim());', html)
        self.assertIn('const resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnActive = Boolean(String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_label) || "").trim());', html)
        self.assertIn('const resumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnActive = Boolean(String((currentFocus && currentFocus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_label) || "").trim());', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_buttons = reopenedReopenedReopenedReopenedReconfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_label = reopenedReopenedReopenedReopenedReopenedReconfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_class = reopenedReopenedReopenedReopenedReopenedReconfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_summary = reopenedReopenedReopenedReopenedReopenedReconfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_buttons = reopenedReopenedReopenedReopenedReopenedReconfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_label = reopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_class = reopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_summary = reopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_buttons = reopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_label = reopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_class = reopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_summary = reopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_buttons = reopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_label = reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_class = reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_summary = reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_buttons = reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"', html)
        self.assertIn('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_label', html)
        self.assertIn('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_class', html)
        self.assertIn('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_summary', html)
        self.assertIn('focus.restored_target_last_followed_label = lastFollowedTargetLabel && String(mode || "").trim() === "resumed-restored-focus-return"', html)
        self.assertIn('focus.restored_target_last_followed_summary = focus.restored_target_last_followed_label', html)
        self.assertIn('restored_target_last_followed_summary || (detail.motion_artifact_focus_posture_snapshot_reason_focus || {}).return_history_reason_resumed_return_return_return_return', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_label = reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_class = reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_summary = reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"', html)
        self.assertIn('focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_buttons = reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusActiveLabel && String(mode || "").trim() === "resumed-restored-focus-return"', html)
        self.assertIn('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_label', html)
        self.assertIn('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_class', html)
        self.assertIn('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_label', html)
        self.assertIn('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_class', html)
        self.assertIn('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_summary', html)
        self.assertIn('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_label', html)
        self.assertIn('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_summary', html)
        self.assertIn('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_buttons', html)
        self.assertIn('label: "Reopen Reopened Reopened Reopened Reopened Reopened Reopened Reopened Reopened Confirmed Focus Artifact",', html)
        self.assertIn('label: "Reopen Reopened Reopened Reopened Reopened Reopened Reopened Reopened Reopened Confirmed Focus Timeline",', html)
        self.assertIn('detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_label = String((reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection && reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection.label) || "").trim();', html)
        self.assertIn('detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_class = String((reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection && reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection.className) || "steady").trim() || "steady";', html)
        self.assertIn('detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_summary = String((reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection && reopenedReopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection.summary) || "").trim();', html)
        self.assertIn('detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_active_label = String((reopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection && reopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection.label) || "").trim();', html)
        self.assertIn('detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_active_class = String((reopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection && reopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection.className) || "steady").trim() || "steady";', html)
        self.assertIn('detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_active_summary = String((reopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection && reopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection.summary) || "").trim();', html)
        self.assertIn('detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_active_label = String((reopenedReopenedReopenedReopenedReopenedReconfirmedFocusSelection && reopenedReopenedReopenedReopenedReopenedReconfirmedFocusSelection.label) || "").trim();', html)
        self.assertIn('detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_active_class = String((reopenedReopenedReopenedReopenedReopenedReconfirmedFocusSelection && reopenedReopenedReopenedReopenedReopenedReconfirmedFocusSelection.className) || "steady").trim() || "steady";', html)
        self.assertIn('detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_active_summary = String((reopenedReopenedReopenedReopenedReopenedReconfirmedFocusSelection && reopenedReopenedReopenedReopenedReopenedReconfirmedFocusSelection.summary) || "").trim();', html)
        self.assertIn('label: "Reopen Reopened Reopened Reopened Reopened Reopened Confirmed Focus Artifact",', html)
        self.assertIn('label: "Reopen Reopened Reopened Reopened Reopened Reopened Confirmed Focus Timeline",', html)
        self.assertIn('label: "Reopen Reopened Reopened Reopened Reopened Reopened Reopened Confirmed Focus Artifact",', html)
        self.assertIn('label: "Reopen Reopened Reopened Reopened Reopened Reopened Reopened Confirmed Focus Timeline",', html)
        self.assertIn('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_buttons', html)
        self.assertIn('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_label', html)
        self.assertIn('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_class', html)
        self.assertIn('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_summary', html)
        self.assertIn('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_buttons', html)
        self.assertIn('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_label', html)
        self.assertIn('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_class', html)
        self.assertIn('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_summary', html)
        self.assertIn('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_buttons', html)
        self.assertIn('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_active_label', html)
        self.assertIn('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_active_class', html)
        self.assertIn('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_active_summary', html)
        self.assertIn('detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_active_label = String((reopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection && reopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection.label) || "").trim();', html)
        self.assertIn('detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_active_class = String((reopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection && reopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection.className) || "steady").trim() || "steady";', html)
        self.assertIn('detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_active_summary = String((reopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection && reopenedReopenedReopenedReopenedReopenedReopenedReopenedConfirmedFocusSelection.summary) || "").trim();', html)
        self.assertIn('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_active_label', html)
        self.assertIn('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_active_class', html)
        self.assertIn('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_active_summary', html)
        self.assertIn('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_active_label', html)
        self.assertIn('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_active_class', html)
        self.assertIn('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_active_summary', html)
        self.assertIn('detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_active_label = String((reopenedReopenedReopenedReconfirmedFocusSelection && reopenedReopenedReopenedReconfirmedFocusSelection.label) || "").trim();', html)
        self.assertIn('detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_active_class = String((reopenedReopenedReopenedReconfirmedFocusSelection && reopenedReopenedReopenedReconfirmedFocusSelection.className) || "steady").trim() || "steady";', html)
        self.assertIn('detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_return_active_summary = String((reopenedReopenedReopenedReconfirmedFocusSelection && reopenedReopenedReopenedReconfirmedFocusSelection.summary) || "").trim();', html)
        self.assertIn('detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_active_label = String((reopenedReopenedReopenedConfirmedFocusSelection && reopenedReopenedReopenedConfirmedFocusSelection.label) || "").trim();', html)
        self.assertIn('detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_active_class = String((reopenedReopenedReopenedConfirmedFocusSelection && reopenedReopenedReopenedConfirmedFocusSelection.className) || "steady").trim() || "steady";', html)
        self.assertIn('detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_active_summary = String((reopenedReopenedReopenedConfirmedFocusSelection && reopenedReopenedReopenedConfirmedFocusSelection.summary) || "").trim();', html)
        self.assertIn('detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_active_label = String((resumedRestoredFocusRestoredSelection && resumedRestoredFocusRestoredSelection.label) || "").trim();', html)
        self.assertIn('detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_active_class = String((resumedRestoredFocusRestoredSelection && resumedRestoredFocusRestoredSelection.className) || "steady").trim() || "steady";', html)
        self.assertIn('detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_active_summary = String((resumedRestoredFocusRestoredSelection && resumedRestoredFocusRestoredSelection.summary) || "").trim();', html)
        self.assertIn('detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_active_label = String((confirmedResumedRestoredFocusSelection && confirmedResumedRestoredFocusSelection.label) || "").trim();', html)
        self.assertIn('detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_active_class = String((confirmedResumedRestoredFocusSelection && confirmedResumedRestoredFocusSelection.className) || "steady").trim() || "steady";', html)
        self.assertIn('detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_active_summary = String((confirmedResumedRestoredFocusSelection && confirmedResumedRestoredFocusSelection.summary) || "").trim();', html)
        self.assertIn('detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_active_label = String((reopenedConfirmedResumedRestoredFocusSelection && reopenedConfirmedResumedRestoredFocusSelection.label) || "").trim();', html)
        self.assertIn('detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_active_class = String((reopenedConfirmedResumedRestoredFocusSelection && reopenedConfirmedResumedRestoredFocusSelection.className) || "steady").trim() || "steady";', html)
        self.assertIn('detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_active_summary = String((reopenedConfirmedResumedRestoredFocusSelection && reopenedConfirmedResumedRestoredFocusSelection.summary) || "").trim();', html)
        self.assertIn('detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_active_label = String((reopenedReopenedConfirmedFocusSelection && reopenedReopenedConfirmedFocusSelection.label) || "").trim();', html)
        self.assertIn('detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_active_class = String((reopenedReopenedConfirmedFocusSelection && reopenedReopenedConfirmedFocusSelection.className) || "steady").trim() || "steady";', html)
        self.assertIn('detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_active_summary = String((reopenedReopenedConfirmedFocusSelection && reopenedReopenedConfirmedFocusSelection.summary) || "").trim();', html)
        self.assertIn('detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_label = String((reopenedReopenedConfirmedFocusRestored && reopenedReopenedConfirmedFocusRestored.label) || "").trim();', html)
        self.assertIn('detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_class = String((reopenedReopenedConfirmedFocusRestored && reopenedReopenedConfirmedFocusRestored.className) || "steady").trim() || "steady";', html)
        self.assertIn('detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_return_return_return_return_return_return_summary = String((reopenedReopenedConfirmedFocusRestored && reopenedReopenedConfirmedFocusRestored.summary) || "").trim();', html)
        self.assertIn('function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnMeta(detail, sourceLabel) {', html)
        self.assertIn('function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnMeta(detail, sourceLabel) {', html)
        self.assertIn('function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnMeta(detail, sourceLabel) {', html)
        self.assertIn('function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnButtons(detail, sourceLabel) {', html)
        self.assertIn('function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnSelectionMeta(targetKind, detail) {', html)
        self.assertIn('function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnButtons(detail, sourceLabel) {', html)
        self.assertIn('function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnSelectionMeta(targetKind, detail) {', html)
        self.assertIn('detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_active_selection_label = String((resumedRestoredTargetSelection && resumedRestoredTargetSelection.label) || "").trim();', html)
        self.assertIn('detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_active_selection_class = String((resumedRestoredTargetSelection && resumedRestoredTargetSelection.className) || "steady").trim() || "steady";', html)
        self.assertIn('detail.motion_artifact_focus_posture_snapshot_reason_focus.return_history_reason_resumed_return_return_active_selection_summary = String((resumedRestoredTargetSelection && resumedRestoredTargetSelection.summary) || "").trim();', html)
        self.assertIn('function motionArtifactSnapshotReasonResumedReturnReturnButtonLabel(detail) {', html)
        self.assertIn('function motionArtifactSnapshotReasonResumedReturnReturnReturnMeta(detail, selectionLabel) {', html)
        self.assertIn('function motionArtifactSnapshotReasonResumedReturnReturnReturnActiveMeta(detail) {', html)
        self.assertIn('function motionArtifactSnapshotReasonResumedReturnReturnReturnActiveButtons(detail) {', html)
        self.assertIn('function motionArtifactSnapshotReasonResumedReturnReturnReturnSelectionMeta(targetKind, detail) {', html)
        self.assertIn('function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnMeta(detail, selectionLabel) {', html)
        self.assertIn('function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnMeta(detail, selectionLabel, sourceLabel) {', html)
        self.assertIn('function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnButtons(detail, sourceLabel) {', html)
        self.assertIn('function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnSelectionMeta(targetKind, detail) {', html)
        self.assertIn('function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnMeta(detail, sourceLabel) {', html)
        self.assertIn('function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnButtons(detail, sourceLabel) {', html)
        self.assertIn('function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnMeta(detail, sourceLabel) {', html)
        self.assertIn('function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnButtons(detail, sourceLabel) {', html)
        self.assertIn('function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnSelectionMeta(targetKind, detail) {', html)
        self.assertIn('function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnSelectionMeta(targetKind, detail) {', html)
        self.assertIn('function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnMeta(detail, sourceLabel) {', html)
        self.assertIn('function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnSelectionMeta(targetKind, detail) {', html)
        self.assertIn('function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnButtons(detail, sourceLabel) {', html)
        self.assertIn('function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnButtons(detail) {', html)
        self.assertIn('function motionArtifactSnapshotReasonResumedReturnReturnReturnReturnSelectionMeta(targetKind, detail) {', html)
        self.assertIn('label: "Open Resumed Evidence Artifact",', html)
        self.assertIn('label: "Open Resumed Evidence Timeline",', html)
        self.assertIn('label: "Open Resumed Restored Evidence Artifact",', html)
        self.assertIn('label: "Open Resumed Restored Evidence Timeline",', html)
        self.assertIn('label: "Open Resumed Restored Focus Artifact",', html)
        self.assertIn('label: "Open Resumed Restored Focus Timeline",', html)
        self.assertIn('label: "Reopen Resumed Restored Focus Artifact",', html)
        self.assertIn('label: "Reopen Resumed Restored Focus Timeline",', html)
        self.assertIn('label: "Open Confirmed Resumed Restored Focus Artifact",', html)
        self.assertIn('label: "Open Confirmed Resumed Restored Focus Timeline",', html)
        self.assertIn('label: "Reopen Confirmed Restored Focus Artifact",', html)
        self.assertIn('label: "Reopen Confirmed Restored Focus Timeline",', html)
        self.assertIn('label: "Reopen Reopened Confirmed Focus Artifact",', html)
        self.assertIn('label: "Reopen Reopened Confirmed Focus Timeline",', html)
        self.assertIn('label: "Reopen Reopened Reopened Reopened Reopened Confirmed Focus Artifact",', html)
        self.assertIn('label: "Reopen Reopened Reopened Reopened Reopened Confirmed Focus Timeline",', html)
        self.assertIn('reopened reopened reopened reopened reopened confirmed focus artifact active', html)
        self.assertIn('reopened reopened reopened reopened reopened confirmed focus timeline active', html)
        self.assertIn('return_history_reason_resumed_return_return_return_return_return_return_active_label = String((reopenedConfirmedResumedRestoredFocusSelection && reopenedConfirmedResumedRestoredFocusSelection.label) || "").trim();', html)
        self.assertIn('return_history_reason_resumed_return_return_return_return_return_active_label = String((confirmedResumedRestoredFocusSelection && confirmedResumedRestoredFocusSelection.label) || "").trim();', html)
        self.assertIn('detail.change_summary = "Returned to the reopened proof focus from the confirmed target view.";', html)
        self.assertIn('const restoredReasonMode = String(mode || "restored-reason").trim();', html)
        self.assertIn('detail.change_summary = restoredReasonMode === "restored-return"', html)
        self.assertIn(': "Focused restored evidence from the reopened proof resume row.";', html)
        self.assertIn('detail.change_evidence_summary = String((detail.motion_artifact_focus_posture_snapshot_reason_focus || {}).active_target_label || "Confirmed the localized artifact target from the reopened proof pane.").trim();', html)
        self.assertIn('detail.change_evidence_summary = String((detail.motion_artifact_focus_posture_snapshot_reason_focus || {}).active_target_label || "Confirmed the matching timeline target from the reopened proof pane.").trim();', html)
        self.assertIn('detail.change_evidence_summary = String((detail.motion_artifact_focus_posture_snapshot_reason_focus || {}).active_target_label || "Returned to the reopened proof focus for the current localized record.").trim();', html)
        self.assertIn('return pickAction("approve") || { label: "Approve Request", summary: "Best next move: resolve this approval posture." };', html)
        self.assertIn('return pickAction("open") || { label: "Open Notification", summary: "Best next move: open the inbox item and inspect the localized payload." };', html)
        self.assertIn('setDetailInspector(jumpToMotionArtifactHistory(index));', html)
        self.assertIn('applyMotionArtifactSnapshotPath(detail, "mutation");', html)
        self.assertIn('setDetailInspector(applyMotionArtifactSnapshotPath(selectedDetail(), "proof"));', html)
        self.assertIn('button[data-motion-artifact-snapshot-restored-reason]', html)
        self.assertIn('button[data-motion-artifact-snapshot-resumed-restored-reason]', html)
        self.assertIn('setDetailInspector(jumpToMotionArtifactSnapshotRestoredReason("restored-reason"));', html)
        self.assertIn('setDetailInspector(jumpToMotionArtifactSnapshotRestoredReason("resumed-restored-reason"));', html)
        self.assertIn('button[data-motion-artifact-snapshot-restored-return]', html)
        self.assertIn('button[data-motion-artifact-snapshot-resumed-return]', html)
        self.assertIn('button[data-motion-artifact-snapshot-resumed-restored-return]', html)
        self.assertIn('button[data-motion-artifact-snapshot-resumed-restored-focus-return]', html)
        self.assertIn('button[data-motion-artifact-snapshot-confirmed-resumed-restored-focus-return]', html)
        self.assertIn('button[data-motion-artifact-snapshot-reopened-confirmed-resumed-restored-focus-return]', html)
        self.assertIn('button[data-motion-artifact-snapshot-reopened-reopened-confirmed-resumed-restored-focus-return]', html)
        self.assertIn('button[data-motion-artifact-snapshot-reopened-reopened-reopened-confirmed-resumed-restored-focus-return]', html)
        self.assertIn('button[data-motion-artifact-snapshot-reopened-reopened-reopened-reopened-confirmed-resumed-restored-focus-return]', html)
        self.assertIn('button[data-motion-artifact-snapshot-reopened-reopened-reopened-reopened-reopened-confirmed-resumed-restored-focus-return]', html)
        self.assertIn('button[data-motion-artifact-snapshot-reopened-reopened-reopened-reopened-reopened-reopened-confirmed-resumed-restored-focus-return]', html)
        self.assertIn('button[data-motion-artifact-snapshot-reopened-reopened-reopened-reopened-reopened-reopened-reopened-confirmed-resumed-restored-focus-return]', html)
        self.assertIn('button[data-motion-artifact-snapshot-reopened-reopened-reopened-reopened-reopened-reopened-reopened-reopened-confirmed-resumed-restored-focus-return]', html)
        self.assertIn('button[data-motion-artifact-snapshot-reopened-reopened-reopened-reopened-reopened-reopened-reopened-reopened-reopened-confirmed-resumed-restored-focus-return]', html)
        self.assertIn('button[data-motion-artifact-snapshot-reopened-reopened-reopened-reopened-reopened-reopened-reopened-reopened-reopened-reopened-confirmed-resumed-restored-focus-return]', html)
        self.assertIn('button[data-motion-artifact-snapshot-reopened-reopened-reopened-reopened-reopened-reopened-reopened-reopened-reopened-reopened-reopened-confirmed-resumed-restored-focus-return]', html)
        self.assertIn('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_summary) || "Returned to the reopened reopened reopened reopened reopened reopened reopened reopened reopened reopened reopened confirmed restored focus lane."', html)
        self.assertIn('reopened reopened reopened reopened reopened reopened reopened reopened confirmed focus restored', html)
        self.assertIn('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_label', html)
        self.assertIn('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_summary', html)
        self.assertIn('label: "Reopen Reopened Reopened Reopened Reopened Reopened Reopened Reopened Confirmed Focus Artifact",', html)
        self.assertIn('label: "Reopen Reopened Reopened Reopened Reopened Reopened Reopened Reopened Confirmed Focus Timeline",', html)
        self.assertIn('Returned to the reopened reopened reopened reopened reopened reopened reopened reopened confirmed restored focus lane.', html)
        self.assertIn('Returned to the reopened reopened reopened reopened reopened reopened reopened reopened reopened confirmed restored focus lane.', html)
        self.assertIn('Returned to the reopened reopened reopened reopened reopened reopened reopened reopened reopened reopened confirmed restored focus lane.', html)
        self.assertIn('Returned to the reopened reopened reopened reopened reopened reopened reopened reopened reopened reopened reopened confirmed restored focus lane.', html)
        self.assertIn('active_target_label) || "Confirmed the reopened proof target artifact in the shared inspector."', html)
        self.assertIn('active_target_label) || "Confirmed the reopened proof target timeline in the shared inspector."', html)
        self.assertIn('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_summary', html)
        self.assertIn('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_buttons', html)
        self.assertIn('label: "Reopen Reopened Reopened Reopened Reopened Reopened Reopened Reopened Confirmed Focus Artifact",', html)
        self.assertIn('label: "Reopen Reopened Reopened Reopened Reopened Reopened Reopened Reopened Confirmed Focus Timeline",', html)
        self.assertIn('return_history_reason_resumed_return_return_return_return_return_return_return_return_buttons', html)
        self.assertIn('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_buttons', html)
        self.assertIn('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_buttons', html)
        self.assertIn('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_active_label', html)
        self.assertIn('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_active_class', html)
        self.assertIn('return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_active_summary', html)
        self.assertIn('const reopenedReopenedReopenedReopenedReconfirmedFocusSelection = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnSelectionMeta("artifact", detail);', html)
        self.assertIn('const reopenedReopenedReopenedReopenedReconfirmedFocusSelection = motionArtifactSnapshotReasonResumedReturnReturnReturnReturnReturnReturnReturnReturnReturnReturnSelectionMeta("timeline", detail);', html)
        self.assertIn('reopened reopened reopened confirmed focus artifact active', html)
        self.assertIn('Returned to the reopened reopened reopened reopened reopened reopened reopened confirmed restored focus lane.', html)
        self.assertIn('button[data-motion-artifact-snapshot-return]', html)
        self.assertIn('setDetailInspector(jumpBackToMotionArtifactSnapshotProof());', html)
        self.assertIn('Returned to the restored evidence lane.', html)
        self.assertIn('Returned to the resumed evidence lane.', html)
        self.assertIn('Returned to the resumed restored evidence lane.', html)
        self.assertIn('Returned to the resumed restored focus lane.', html)
        self.assertIn('Focused resumed restored evidence from the resumed restored proof row.', html)
        self.assertIn('restored_target_last_followed_summary || (detail.motion_artifact_focus_posture_snapshot_reason_focus || {}).return_history_reason_resumed_return_return_return_return', html)
        self.assertIn('Returned to the reopened proof focus.', html)
        self.assertIn('setDetailInspector(jumpToMotionArtifactSnapshotRestoredReason("restored-return"));', html)
        self.assertIn('setDetailInspector(jumpToMotionArtifactSnapshotRestoredReason("resumed-return"));', html)
        self.assertIn('setDetailInspector(jumpToMotionArtifactSnapshotRestoredReason("resumed-restored-return"));', html)
        self.assertIn('setDetailInspector(jumpToMotionArtifactSnapshotRestoredReason("resumed-restored-focus-return"));', html)
        self.assertIn('Returned to the reopened reopened reopened reopened reopened reopened confirmed restored focus lane.', html)
        self.assertIn('Returned to the confirmed resumed restored focus lane.', html)
        self.assertIn('Returned to the reopened confirmed restored focus lane.', html)
        self.assertIn('Returned to the reopened reopened confirmed restored focus lane.', html)
        self.assertIn('Returned to the reopened reopened reopened confirmed restored focus lane.', html)
        self.assertIn('Returned to the reopened reopened reopened reopened confirmed restored focus lane.', html)
        self.assertIn('Returned to the reopened reopened reopened reopened reopened confirmed restored focus lane.', html)
        self.assertIn('data-motion-artifact-snapshot-return="1">Return to Reopened Proof</button>', html)
        self.assertIn('button[data-motion-artifact-snapshot-timeline-index]', html)
        self.assertIn('setDetailInspector(jumpToMotionArtifactSnapshotTimeline(index));', html)
        self.assertIn('Focused reopened proof chronology from the proof pivot strip.', html)
        self.assertIn('button[data-motion-artifact-snapshot-target-artifact-index]', html)
        self.assertIn('button[data-motion-artifact-snapshot-target-timeline-index]', html)
        self.assertIn('const detail = jumpToMotionArtifactSnapshotTargetArtifact(index);', html)
        self.assertIn('const detail = jumpToMotionArtifactSnapshotTargetTimeline(index);', html)
        self.assertIn('button[data-motion-artifact-snapshot-history-target-artifact-index]', html)
        self.assertIn('button[data-motion-artifact-snapshot-history-target-timeline-index]', html)
        self.assertIn('button[data-motion-artifact-round-trip-history-return-index]', html)
        self.assertIn('if (kind === "agent") {', html)
        self.assertIn('setDetailInspector(agentDetailAt(index));', html)
        self.assertIn('if (kind === "mission") {', html)
        self.assertIn('setDetailInspector(missionDetailAt(index));', html)
        self.assertIn('if (kind === "seam") {', html)
        self.assertIn('if (kind === "progress") {', html)
        self.assertIn('if (kind === "module") {', html)
        self.assertIn('setDetailInspector(moduleDetailAt(index));', html)
        self.assertIn('setDetailInspector(progressDetailAt(index));', html)
        self.assertIn('setDetailInspector(seamDetailAt(index));', html)
        self.assertIn('coreModules.innerHTML = coreModulesHtml((commandCenterPayload || {}).core_modules || {});', html)
        self.assertIn('progressDashboard.innerHTML = progressDashboardHtml((commandCenterPayload || {}).progress_dashboard || {});', html)
        self.assertIn('const originIndex = button.getAttribute("data-motion-artifact-snapshot-history-origin-index") || "";', html)
        self.assertIn('const detail = jumpToMotionArtifactSnapshotTargetArtifact(index, "round-trip-history-artifact", originIndex);', html)
        self.assertIn('const detail = jumpToMotionArtifactSnapshotTargetTimeline(index, "round-trip-history-timeline", originIndex);', html)
        self.assertIn('const detail = jumpToMotionArtifactHistory(index);', html)
        self.assertIn('setDetailInspector(detail);', html)
        self.assertIn('Confirmed the reopened proof target artifact in the shared inspector.', html)
        self.assertIn('Confirmed the reopened proof target timeline in the shared inspector.', html)
        self.assertIn('Round-trip reopen result: artifact lane active.', html)
        self.assertIn('Round-trip reopen result: timeline lane active.', html)
        self.assertIn('Returned to the originating round-trip history row.', html)
        self.assertIn('Fallback timestamp:', html)
        self.assertIn('Before State', html)
        self.assertIn('After State', html)
        self.assertIn('Source:', html)
        self.assertIn('Transition:', html)
        self.assertIn('Queue State:', html)
        self.assertIn('Evidence:', html)
        self.assertIn('Activity JSON', html)
        self.assertIn('data-needs-index="0"', html)
        self.assertIn('data-needs-key="approve local rollout::approval"', html)
        self.assertIn('data-endpoint="/api/approvals/req-1/approve"', html)
        self.assertIn('/approval-queue', html)
        self.assertIn('Open approval queue', html)
        self.assertIn('Action succeeded:', html)
        self.assertIn('Action failed:', html)
        self.assertIn('Handled moments ago.', html)
        self.assertIn('Handled posture:', html)
        self.assertIn('Inspect Outcome', html)
        self.assertIn('Live need resurfaced:', html)
        self.assertIn('Returned to the active triage queue after a recent handled state.', html)
        self.assertIn('retired: shouldRetire', html)
        self.assertIn('No longer in active open loops.', html)
        self.assertIn('Still active in open loops.', html)
        self.assertIn('data-needs-key-inspect=', html)
        self.assertIn('data-needs-reopen=', html)
        self.assertIn('Reopened for operator review.', html)
        self.assertIn('Reopened handled triage item for review.', html)
        self.assertIn('Focused handled Needs Me Now outcome in the shared detail inspector.', html)
        self.assertIn('Focused selected Recent Need Motion proof in the shared detail inspector.', html)
        self.assertIn('Motion row "', html)
        self.assertIn('Motion Kind', html)
        self.assertIn('Signal Source', html)
        self.assertIn('live queue', html)
        self.assertIn('need / Approve local rollout', html)
        self.assertIn('observed -&gt; active', html)
        self.assertIn('critical / approval, supervision', html)
        self.assertIn('critical / approval, supervision / Open approval queue', html)
        self.assertIn('Open approval queue', html)
        self.assertIn('Inspect the approval queue or item timeline to confirm downstream execution posture.', html)
        self.assertIn('Inspect the notification snapshot or related detail pane to confirm the updated inbox state.', html)
        self.assertIn('Inspect the item timeline or related journal context to confirm the new workstream posture.', html)
        self.assertIn('Focused selected Needs Me Now item in the shared detail inspector.', html)
        self.assertIn('Approval Review Fields', html)
        self.assertIn('Consent &amp; Readiness', html)
        self.assertIn('What Changed', html)
        self.assertIn('Operator Guidance', html)
        self.assertIn('Approval Controls', html)
        self.assertIn('Why it surfaced:', html)
        self.assertIn('Use the inline open-loop actions to move this workstream forward.', html)
        self.assertIn('Inspect runtime trace context for ${traceDetail}.', html)
        self.assertIn('afterDetail.approval_consequence_fields = approvalConsequenceFields(beforeDetail, afterDetail, pendingActionContext);', html)
        self.assertIn('afterDetail.approval_guidance_lines = approvalRemediationGuidance(beforeDetail, afterDetail, pendingActionContext);', html)
        self.assertIn('pendingActionContext = Object.assign({}, pendingActionContext || {}, { error: errorText });', html)
        self.assertIn('latestChangeSummary = `Action failed before refresh: ${errorText}`;', html)
        self.assertIn('failedDetail.action_result_summary = `failed · endpoint ${endpoint}`;', html)
        self.assertIn('failedDetail.change_evidence_summary = `Action failed before refresh: ${errorText}`;', html)
        self.assertIn('failedDetail.approval_consequence_fields = approvalConsequenceFields(beforeDetail || {}, failedDetail, pendingActionContext);', html)
        self.assertIn('failedDetail.approval_guidance_lines = approvalRemediationGuidance(beforeDetail || {}, failedDetail, pendingActionContext);', html)
        self.assertIn('Recent Approval History', html)
        self.assertIn('Surfaced Snapshot', html)
        self.assertIn('previewSections.push({ label: "Decision Actor"', html)
        self.assertIn('previewSections.push({ label: "Decision Time"', html)
        self.assertIn('previewSections.push({ label: "Suggested Action"', html)
        self.assertIn('previewSections.push({ label: "Priority Hint"', html)
        self.assertIn('endpoint: `/api/approvals/${requestId}/approve`', html)
        self.assertIn('endpoint: openEndpoint, method: "POST", body: { actor: "Chris", status: "opened" }, label: "Open Notification"', html)
        self.assertIn('endpoint: "/api/open-loops/action"', html)
        self.assertIn('item_timeline_count: ${beforeTimelineCount} -> ${afterTimelineCount}', html)
        self.assertIn('selected_timeline_event: selectedTimelineEvent,', html)
        self.assertIn('selected_timeline_event_detail: selectedTimelineEventDetail,', html)
        self.assertIn('button[data-timeline-index]', html)
        self.assertIn('button[data-event-action]', html)
        self.assertIn('currentTimelineEventIndex = null;', html)
        self.assertIn('recentLocalActions = [', html)
        self.assertIn('related_kind: beforeDetail.source_kind === "notification" ? "notification" : "open-loop",', html)
        self.assertIn('setDetailInspector(journalDetailAt(index));', html)
        self.assertIn('setDetailInspector(jumpToRelatedFromJournal(index));', html)
        self.assertIn('setDetailInspector(selectedDetail());', html)
        self.assertIn('performEventAction(action);', html)
        self.assertIn('currentDetailSelection = { kind, index: Number(index) || 0 };', html)
        self.assertIn('latestApprovalsPayload = approvals || {};', html)
        self.assertIn('latestActivityPayload = Array.isArray(activity) ? activity : [];', html)
        self.assertIn('button[data-detail-kind]', html)
        self.assertIn('notificationPreview.innerHTML = notificationPreviewHtml', html)
        self.assertIn('activityFeed.innerHTML = activityItemHtml', html)
        self.assertIn('agentRegistry.innerHTML = registryItemHtml', html)
        self.assertIn('laneProgress.innerHTML = laneProgressHtml', html)
        self.assertIn('failureRecovery.innerHTML = failureRecoveryHtml', html)
        self.assertIn('/agent-ops-center', html)
        self.assertIn('/api/agent-ops/module', html)
        self.assertIn('/recovery-center', html)
        self.assertIn('/api/recovery/module', html)
        self.assertIn('/mission-board', html)
        self.assertIn('/api/mission-board/module', html)
        self.assertIn('/activity-center', html)
        self.assertIn('/api/activity/module', html)
        self.assertIn('/api/agent-registry', html)
        self.assertIn('/api/activity', html)
        self.assertIn('/api/briefing?actor=Chris', html)
        self.assertIn('/api/open-loops?actor=Chris', html)
        self.assertIn('/api/assistant-core/notifications?actor=Chris', html)
        self.assertIn('hydratePanels()', html)

    def test_render_index_persists_deepest_restored_target_row(self) -> None:
        payload = build_command_center_index()
        detail = payload["detail_inspector"]
        focus = detail.setdefault("motion_artifact_focus_posture_snapshot_reason_focus", {})
        focus["return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_label"] = (
            "reopened reopened reopened reopened reopened reopened reopened reopened reopened reopened confirmed focus restored"
        )
        focus["return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_class"] = "accepted"
        focus["return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_summary"] = (
            "Restored the reopened reopened reopened reopened reopened reopened reopened reopened reopened reopened confirmed focus artifact for the seeded record."
        )
        focus["return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_buttons"] = [
            {
                "kind": "artifact",
                "motion_artifact_index": 0,
                "label": "Reopen Reopened Reopened Reopened Reopened Reopened Reopened Reopened Reopened Reopened Confirmed Focus Artifact",
            }
        ]
        focus["return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_label"] = (
            "reopened reopened reopened reopened reopened reopened reopened reopened reopened reopened reopened confirmed focus artifact active"
        )
        focus["return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_class"] = "accepted"
        focus["return_history_reason_resumed_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_return_active_summary"] = (
            "Following the reopened reopened reopened reopened reopened reopened reopened reopened reopened reopened reopened confirmed focus artifact for the seeded record."
        )
        focus["restored_target_last_followed_label"] = (
            "reopened reopened reopened reopened reopened reopened reopened reopened reopened reopened reopened confirmed focus artifact active"
        )
        focus["restored_target_last_followed_class"] = "accepted"
        focus["restored_target_last_followed_summary"] = (
            "Last followed from restored target proof: reopened reopened reopened reopened reopened reopened reopened reopened reopened reopened reopened confirmed focus artifact active."
        )
        detail["motion_artifact_focus_history_summary"] = (
            "Showing 1 recent localized action result for this exact record; latest trend: workflow shifted."
        )
        detail["motion_artifact_focus_history_meta"] = (
            "Recent outcome mix: 1 open-loop. No previous localized action snapshot yet."
        )
        detail["motion_artifact_focus_history_rows"] = [
            {
                "label": "Most Recent",
                "badge": "open-loop / returned",
                "badge_class": "open-loop",
                "trend": "workflow shifted",
                "trend_class": "shifted",
                "last_revisited_lane_label": "artifact lane revisited",
                "last_revisited_lane_class": "accepted",
                "last_revisited_lane_summary": (
                    "Last revisited lane: artifact lane reopened for reopened reopened reopened reopened reopened reopened reopened reopened reopened reopened reopened confirmed focus artifact active."
                ),
                "value": (
                    "recent history · Return to Restored Target Proof · returned · "
                    "Last followed from restored target proof: reopened reopened reopened reopened reopened reopened reopened reopened reopened reopened reopened confirmed focus artifact active."
                ),
                "history_buttons": [
                    {
                        "kind": "artifact",
                        "motion_artifact_index": 0,
                        "label": "Reopen Reopened Reopened Reopened Reopened Reopened Reopened Reopened Reopened Reopened Confirmed Focus Artifact",
                    }
                ],
                "jumpable": True,
            }
        ]
        detail["motion_artifact_focus_history_note"] = (
            "Round-trip reopen result: artifact lane active for reopened reopened reopened reopened reopened reopened reopened reopened reopened reopened reopened confirmed focus artifact active."
        )
        detail["motion_artifact_focus_round_trip_history_index"] = 0

        html = render_command_center_index_html(payload)

        self.assertIn("Reopened Reopened Reopened Reopened Reopened Reopened Reopened Reopened Reopened Reopened Confirmed Focus Restored Target", html)
        self.assertIn(
            "reopened reopened reopened reopened reopened reopened reopened reopened reopened reopened reopened confirmed focus artifact active",
            html,
        )
        self.assertIn(
            "Restored the reopened reopened reopened reopened reopened reopened reopened reopened reopened reopened confirmed focus artifact for the seeded record.",
            html,
        )
        self.assertIn('data-motion-artifact-snapshot-target-artifact-index="0"', html)
        self.assertIn("Follow Restored Target Artifact", html)
        self.assertIn('data-motion-artifact-snapshot-restored-target-return="1"', html)
        self.assertIn("Return to Restored Target Proof", html)
        self.assertIn('button[data-motion-artifact-snapshot-restored-target-return]', html)
        self.assertIn('Returned to the persistent restored target proof row.', html)
        self.assertIn("Last Followed Restored Target", html)
        self.assertIn(
            "Last followed from restored target proof: reopened reopened reopened reopened reopened reopened reopened reopened reopened reopened reopened confirmed focus artifact active.",
            html,
        )
        self.assertIn("Return to Restored Target Proof", html)
        self.assertIn("open-loop / returned", html)
        self.assertIn("workflow shifted", html)
        self.assertIn("artifact lane revisited", html)
        self.assertIn(
            "Last revisited lane: artifact lane reopened for reopened reopened reopened reopened reopened reopened reopened reopened reopened reopened reopened confirmed focus artifact active.",
            html,
        )
        self.assertIn("Reopen Round-Trip Artifact", html)
        self.assertIn('data-motion-artifact-snapshot-history-origin-index="${esc(String(index))}"', html)
        self.assertIn("Return to Round-Trip History", html)
        self.assertIn(
            "Round-trip reopen result: artifact lane active for reopened reopened reopened reopened reopened reopened reopened reopened reopened reopened reopened confirmed focus artifact active.",
            html,
        )


if __name__ == "__main__":
    unittest.main()
