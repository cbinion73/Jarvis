from __future__ import annotations

import unittest
from types import SimpleNamespace

from jarvis.render_pages import render_catalyst_workspace_page


class _StubRuntime:
    def catalyst_overview(self) -> dict:
        return {
            "counts": {
                "signals": 4,
                "email_triage": 1,
                "meeting_extractions": 2,
                "briefings": 3,
                "drafts": 1,
                "project_briefs": 2,
                "implementation_plans": 1,
                "hypotheses": 2,
            },
            "top_signals": [
                {
                    "title": "Roadmap drift risk",
                    "source": "Watcher",
                    "tags": ["governance"],
                    "timestamp": "2026-06-01T08:00:00Z",
                }
            ],
            "portfolio": {
                "mission": "Build the governed household intelligence layer.",
                "lanes": [{"title": "Governance", "status": "active", "description": "Keep approval and trust posture aligned."}],
            },
            "portfolio_lanes": [
                {
                    "label": "Family Operations",
                    "status": "active",
                    "description": "Projects that reduce friction and improve daily life.",
                }
            ],
            "active_work": [
                {
                    "title": "Trust-zone schemas",
                    "summary": "Tighten governance boundaries before the next deploy.",
                    "domain": "governance",
                    "status": "active",
                    "updated_at": "2026-06-01T08:00:00Z",
                }
            ],
            "connectors": [
                {
                    "label": "Manual Capture",
                    "status": "local",
                    "notes": "Text-first workflow capture is live.",
                },
                {
                    "label": "Gmail",
                    "status": "disconnected",
                    "notes": "No Gmail account is currently connected.",
                },
            ],
            "latest_runs": {
                "briefing": {
                    "title": "Morning package for stewardship queue",
                    "timestamp": "2026-06-01T08:00:00Z",
                }
            },
            "live_workspace": {
                "available": True,
                "live": True,
                "projects": {
                    "items": [
                        {
                            "title": "Trust Zone Refresh",
                            "description": "Stage the next governed contract slice.",
                            "status": "active",
                            "updatedAt": "2026-06-01T08:00:00Z",
                        }
                    ]
                },
                "tasks": {
                    "items": [
                        {
                            "title": "Review schema lane",
                            "description": "Confirm the trust posture before handoff.",
                            "status": "next",
                            "due": "Today 10:00 AM",
                        }
                    ]
                },
                "calendar": {"items": [{"summary": "Family sync", "start": "2026-06-01T10:00:00Z"}]},
                "email": {"items": [{"subject": "Approval request", "from": "Sam Wilson"}]},
            },
        }

    def google_workspace_summary(self) -> dict:
        return {
            "accounts": [
                {
                    "account": {"owner_display_name": "Chris", "label": "Primary Gmail"},
                    "emails": [{"subject": "Approval request", "from": "Sam Wilson"}],
                    "calendar_events": [{"summary": "Morning sync", "start": "2026-06-01T09:00:00Z"}],
                    "gmail_error": "",
                    "calendar_error": "",
                    "counts": {"unread_emails": 1, "upcoming_events": 1},
                }
            ]
        }

    def family_calendar_summary(self) -> dict:
        return {
            "counts": {"upcoming_events": 1},
            "calendar": {"label": "Family Shared Calendar"},
            "events": [{"summary": "Scout planning", "start": "2026-06-01T12:00:00Z"}],
            "configured": True,
            "detail": "Family shared calendar is connected.",
        }

    def account_registry_snapshot(self) -> dict:
        return {
            "accounts": [
                {
                    "label": "Primary Gmail",
                    "owner_display_name": "Chris",
                    "provider": "google",
                    "status": "connected",
                }
            ]
        }

    household = SimpleNamespace(users={})


class CatalystWorkspacePageTests(unittest.TestCase):
    def test_home_page_is_route_backed_and_mockup_shaped(self) -> None:
        html = render_catalyst_workspace_page(_StubRuntime(), "home")

        self.assertIn("Catalyst Desktop Experience", html)
        self.assertIn("Catalyst Operations Command Center", html)
        self.assertIn("Trust-zone schemas", html)
        self.assertIn("Morning package for stewardship queue", html)
        self.assertNotIn("Q2 Board Pack Workflow", html)

    def test_projects_page_renders_live_workspace_project_records(self) -> None:
        html = render_catalyst_workspace_page(_StubRuntime(), "projects")

        self.assertIn("Workflow Builder Studio", html)
        self.assertIn("Trust Zone Refresh", html)
        self.assertIn("Family Operations", html)

    def test_tasks_page_renders_live_workspace_task_records(self) -> None:
        html = render_catalyst_workspace_page(_StubRuntime(), "tasks")

        self.assertIn("Live Agent Execution Board", html)
        self.assertIn("Review schema lane", html)
        self.assertIn("Morning sync", html)

    def test_reports_page_renders_live_reporting_deck(self) -> None:
        html = render_catalyst_workspace_page(_StubRuntime(), "reports")

        self.assertIn("Catalyst Reporting Deck", html)
        self.assertIn("Roadmap drift risk", html)
        self.assertIn("Approval request", html)


if __name__ == "__main__":
    unittest.main()
