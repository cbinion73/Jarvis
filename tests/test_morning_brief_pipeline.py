"""Tests for the Morning Brief pipeline (Magic Moment 1)."""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

import pytest

from jarvis.morning_brief_pipeline import (
    MorningBriefResult,
    _gather_agent_health,
    _gather_git_activity,
    _gather_memory_entries,
    _gather_profile_facts,
    _gather_workstreams,
    _hours_since,
    generate_morning_brief,
)


class TestGatherGitActivity:
    def test_returns_dict_with_available_key(self):
        result = _gather_git_activity(24)
        assert "available" in result
        assert "commits" in result
        assert "count" in result

    def test_commits_have_required_fields(self):
        result = _gather_git_activity(24)
        if result["available"] and result["commits"]:
            for c in result["commits"]:
                assert "hash" in c
                assert "message" in c

    def test_count_matches_commits_length(self):
        result = _gather_git_activity(24)
        assert result["count"] == len(result["commits"])


class TestGatherMemoryEntries:
    def test_returns_dict_with_required_keys(self, tmp_path):
        mem_dir = tmp_path / "memory"
        mem_dir.mkdir()
        (mem_dir / "entries.json").write_text(json.dumps([
            {"entry_id": "1", "owner": "Chris", "subject_user_id": "chris",
             "title": "Test memory", "summary": "Summary", "created_at": "2026-06-10T10:00:00+00:00",
             "memory_type": "personal"},
        ]))
        with patch("jarvis.morning_brief_pipeline._DATA_ROOT", tmp_path):
            result = _gather_memory_entries("chris")
        assert result["available"] is True
        assert result["total_count"] == 1
        assert result["recent"][0]["title"] == "Test memory"

    def test_filters_to_actor(self, tmp_path):
        mem_dir = tmp_path / "memory"
        mem_dir.mkdir()
        (mem_dir / "entries.json").write_text(json.dumps([
            {"owner": "Chris", "subject_user_id": "chris", "title": "Chris entry", "summary": "", "created_at": "", "memory_type": "personal"},
            {"owner": "Rebekah", "subject_user_id": "rebekah", "title": "Rebekah entry", "summary": "", "created_at": "", "memory_type": "personal"},
        ]))
        with patch("jarvis.morning_brief_pipeline._DATA_ROOT", tmp_path):
            result = _gather_memory_entries("chris")
        assert result["total_count"] == 1
        assert result["recent"][0]["title"] == "Chris entry"

    def test_missing_file_returns_unavailable(self, tmp_path):
        with patch("jarvis.morning_brief_pipeline._DATA_ROOT", tmp_path):
            result = _gather_memory_entries("chris")
        assert result["available"] is False


class TestGatherAgentHealth:
    def test_parses_background_state(self, tmp_path):
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "background_state.json").write_text(json.dumps({
            "last_tick_at": "2026-06-10T22:00:00+00:00",
            "active_mode": "dawn-protocol",
            "quiet_hours_active": False,
            "agents": {
                "scout": {"state": "running", "health_status": "ok"},
                "builder": {"state": "blocked", "health_status": "blocked", "attention_required": True},
            },
        }))
        with patch("jarvis.morning_brief_pipeline._DATA_ROOT", tmp_path):
            result = _gather_agent_health()
        assert result["available"] is True
        assert result["active_mode"] == "dawn-protocol"
        assert result["total_agents"] == 2
        assert result["degraded_count"] == 1
        assert result["degraded"][0]["name"] == "builder"

    def test_missing_file_returns_unavailable(self, tmp_path):
        with patch("jarvis.morning_brief_pipeline._DATA_ROOT", tmp_path):
            result = _gather_agent_health()
        assert result["available"] is False


class TestHoursSince:
    def test_recent_timestamp(self):
        from datetime import datetime, timezone, timedelta
        one_hour_ago = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        hours = _hours_since(one_hour_ago)
        assert hours is not None
        assert 0.9 < hours < 1.1

    def test_empty_string_returns_none(self):
        assert _hours_since("") is None

    def test_invalid_string_returns_none(self):
        assert _hours_since("not-a-date") is None


class TestGenerateMorningBrief:
    def test_returns_morning_brief_result(self):
        result = generate_morning_brief("Chris")
        assert isinstance(result, MorningBriefResult)

    def test_result_has_all_sections(self):
        result = generate_morning_brief("Chris")
        assert result.greeting
        assert isinstance(result.what_changed, list)
        assert isinstance(result.what_matters, list)
        assert isinstance(result.what_is_waiting, list)
        assert isinstance(result.while_you_were_away, list)
        assert isinstance(result.may_have_forgotten, list)
        assert isinstance(result.jarvis_prepared, list)
        assert result.recommendation
        assert isinstance(result.truth_labels, dict)

    def test_greeting_contains_actor_name(self):
        result = generate_morning_brief("Chris")
        assert "Chris" in result.greeting

    def test_sections_are_non_empty(self):
        result = generate_morning_brief("Chris")
        # At minimum there are fallback entries in each section
        assert len(result.what_changed) >= 1
        assert len(result.what_matters) >= 1
        assert len(result.what_is_waiting) >= 1
        assert len(result.while_you_were_away) >= 1
        assert len(result.may_have_forgotten) >= 1
        assert len(result.jarvis_prepared) >= 1

    def test_truth_labels_present(self):
        result = generate_morning_brief("Chris")
        assert "git_activity" in result.truth_labels
        assert "memory" in result.truth_labels
        assert "health_data" in result.truth_labels

    def test_asdict_serializable(self):
        result = generate_morning_brief("Chris")
        d = asdict(result)
        serialized = json.dumps(d)
        assert len(serialized) > 100

    def test_git_activity_appears_when_commits_exist(self):
        result = generate_morning_brief("Chris")
        # In the real repo there are commits — should appear in what_changed or prepared
        all_text = " ".join(result.what_changed + result.jarvis_prepared)
        # Either commits were found or honest "no commits" message
        assert "commit" in all_text.lower() or "jarvis" in all_text.lower()

    @patch("jarvis.morning_brief_pipeline._gather_obsidian_support")
    @patch("jarvis.morning_brief_pipeline._gather_family_calendar_support")
    @patch("jarvis.morning_brief_pipeline._gather_google_workspace_support")
    def test_truth_labels_use_dynamic_support_posture(
        self,
        mock_google_support,
        mock_family_calendar,
        mock_obsidian_support,
    ):
        mock_google_support.return_value = {
            "available": True,
            "default_status": {
                "libraries_ready": True,
                "credentials_file_present": True,
                "token_present": True,
            },
            "client_secret": {"present": True, "path": "config/google_client_secret.json"},
            "account_count": 1,
            "recorded_connected_count": 1,
            "usable_connected_count": 1,
            "gmail_error_count": 0,
            "calendar_error_count": 0,
            "unread_email_count": 4,
            "upcoming_event_count": 2,
            "accounts": [],
            "usable_accounts": [],
            "gmail_errors": [],
            "calendar_errors": [],
        }
        mock_family_calendar.return_value = {
            "available": True,
            "summary": {"configured": True, "counts": {"upcoming_events": 3}},
            "connected": True,
            "event_count": 3,
        }
        mock_obsidian_support.return_value = {
            "available": True,
            "status": {"enabled": True, "detail": "Obsidian vault is available for local retrieval."},
            "enabled": True,
        }

        result = generate_morning_brief("Chris")

        assert result.truth_labels["email"] == "live — Gmail returned 4 unread items"
        assert result.truth_labels["calendar"] == "live — Google Calendar returned 2 upcoming events"
        assert result.truth_labels["obsidian_context"] == "local — Obsidian vault is available for local retrieval"
        assert any(
            "Calendar pressure: connected Google Calendar returned 2 upcoming events for planning." in item
            for item in result.what_matters
        )
        assert any("Inbox pressure: connected Gmail returned 4 unread items." in item for item in result.what_is_waiting)
        assert any("System pressure:" in item for item in result.what_is_waiting)
        assert "Google Calendar not connected" not in " ".join(result.may_have_forgotten)

    @patch("jarvis.morning_brief_pipeline._gather_obsidian_support")
    @patch("jarvis.morning_brief_pipeline._gather_family_calendar_support")
    @patch("jarvis.morning_brief_pipeline._gather_google_workspace_support")
    def test_connected_but_empty_labels_are_plain(
        self,
        mock_google_support,
        mock_family_calendar,
        mock_obsidian_support,
    ):
        mock_google_support.return_value = {
            "available": True,
            "default_status": {
                "libraries_ready": True,
                "credentials_file_present": True,
                "token_present": True,
            },
            "client_secret": {"present": True, "path": "config/google_client_secret.json"},
            "account_count": 1,
            "recorded_connected_count": 1,
            "usable_connected_count": 1,
            "gmail_error_count": 0,
            "calendar_error_count": 0,
            "unread_email_count": 0,
            "upcoming_event_count": 0,
            "accounts": [],
            "usable_accounts": [],
            "gmail_errors": [],
            "calendar_errors": [],
        }
        mock_family_calendar.return_value = {
            "available": True,
            "summary": {"configured": True, "counts": {"upcoming_events": 0}},
            "connected": True,
            "event_count": 0,
        }
        mock_obsidian_support.return_value = {
            "available": True,
            "status": {"enabled": False, "detail": "Obsidian vault is disabled in this runtime."},
            "enabled": False,
        }

        result = generate_morning_brief("Chris")

        assert result.truth_labels["email"] == "connected-but-empty — Gmail is connected but no unread inbox items were retrieved"
        assert result.truth_labels["calendar"] == "connected-but-empty — calendar support is connected but no upcoming events were retrieved"
        assert "Inbox pressure: connected Gmail did not return unread items for this brief." in result.what_is_waiting
        assert "did not retrieve any upcoming events" in " ".join(result.may_have_forgotten)

    @patch("jarvis.morning_brief_pipeline._gather_obsidian_support")
    @patch("jarvis.morning_brief_pipeline._gather_family_calendar_support")
    @patch("jarvis.morning_brief_pipeline._gather_google_workspace_support")
    @patch("jarvis.morning_brief_pipeline._gather_agent_health")
    @patch("jarvis.morning_brief_pipeline._gather_git_activity")
    @patch("jarvis.morning_brief_pipeline._gather_open_loops_raw")
    def test_recommendation_uses_credential_guidance_when_google_support_is_blocked(
        self,
        mock_open_loops,
        mock_git,
        mock_agents,
        mock_google_support,
        mock_family_calendar,
        mock_obsidian_support,
    ):
        mock_git.return_value = {"available": True, "commits": [], "count": 0}
        mock_agents.return_value = {
            "available": True,
            "agents": {},
            "degraded": [],
            "blocked": [],
            "active_mode": "",
            "degraded_count": 0,
            "running_count": 0,
            "total_agents": 0,
            "quiet_hours_active": False,
            "last_tick_at": "",
        }
        mock_open_loops.return_value = {"available": True, "loops": [], "count": 0}
        mock_google_support.return_value = {
            "available": True,
            "default_status": {
                "libraries_ready": True,
                "credentials_file_present": False,
                "token_present": False,
            },
            "client_secret": {"present": False, "path": "config/google_client_secret.json"},
            "account_count": 0,
            "recorded_connected_count": 0,
            "usable_connected_count": 0,
            "gmail_error_count": 0,
            "calendar_error_count": 0,
            "unread_email_count": 0,
            "upcoming_event_count": 0,
            "accounts": [],
            "usable_accounts": [],
            "gmail_errors": [],
            "calendar_errors": [],
        }
        mock_family_calendar.return_value = {
            "available": True,
            "summary": {"configured": False, "detail": "Family shared calendar is not configured."},
            "connected": False,
            "event_count": 0,
        }
        mock_obsidian_support.return_value = {
            "available": True,
            "status": {"enabled": False, "detail": "Obsidian vault is disabled in this runtime."},
            "enabled": False,
        }

        result = generate_morning_brief("Chris")

        assert result.recommendation == (
            "Restore the Google OAuth client file at config/google_client_secret.json so JARVIS can inspect Gmail and Calendar support honestly."
        )
        assert result.recommendation_action == {
            "action_kind": "direct_route",
            "title": "Review Google signal posture",
            "detail": "Settings Center shows the current Google Workspace credential posture and the next recovery seam.",
            "route": "/settings-center",
            "route_label": "Open Settings Center",
            "truth_note": "This opens the current settings surface. It does not connect Gmail or Calendar by itself.",
        }
        assert result.truth_labels["email"] == "degraded — Google bridge is ready but config/google_client_secret.json is missing"
        assert result.truth_labels["calendar"] == "degraded — calendar support is ready but config/google_client_secret.json is missing"
        assert result.what_is_waiting[0] == (
            "Inbox pressure is limited: degraded — Google bridge is ready but config/google_client_secret.json is missing."
        )

    @patch("jarvis.morning_brief_pipeline._gather_obsidian_support")
    @patch("jarvis.morning_brief_pipeline._gather_family_calendar_support")
    @patch("jarvis.morning_brief_pipeline._gather_google_workspace_support")
    def test_family_calendar_live_signal_surfaces_without_google_events(
        self,
        mock_google_support,
        mock_family_calendar,
        mock_obsidian_support,
    ):
        mock_google_support.return_value = {
            "available": True,
            "default_status": {
                "libraries_ready": True,
                "credentials_file_present": True,
                "token_present": False,
            },
            "client_secret": {"present": True, "path": "config/google_client_secret.json"},
            "account_count": 0,
            "recorded_connected_count": 0,
            "usable_connected_count": 0,
            "gmail_error_count": 0,
            "calendar_error_count": 0,
            "unread_email_count": 0,
            "upcoming_event_count": 0,
            "accounts": [],
            "usable_accounts": [],
            "gmail_errors": [],
            "calendar_errors": [],
        }
        mock_family_calendar.return_value = {
            "available": True,
            "summary": {"configured": True, "counts": {"upcoming_events": 5}},
            "connected": True,
            "event_count": 5,
        }
        mock_obsidian_support.return_value = {
            "available": True,
            "status": {"enabled": True, "detail": "Obsidian vault is available for local retrieval."},
            "enabled": True,
        }

        result = generate_morning_brief("Chris")

        assert result.truth_labels["calendar"] == "live — family shared calendar returned 5 upcoming events"
        assert any("Family calendar has 5 upcoming events loaded for planning." == item for item in result.what_matters)

    @patch("jarvis.morning_brief_pipeline._gather_obsidian_support")
    @patch("jarvis.morning_brief_pipeline._gather_family_calendar_support")
    @patch("jarvis.morning_brief_pipeline._gather_google_workspace_support")
    def test_google_calendar_live_signal_surfaces_in_what_matters(
        self,
        mock_google_support,
        mock_family_calendar,
        mock_obsidian_support,
    ):
        mock_google_support.return_value = {
            "available": True,
            "default_status": {
                "libraries_ready": True,
                "credentials_file_present": True,
                "token_present": True,
            },
            "client_secret": {"present": True, "path": "config/google_client_secret.json"},
            "account_count": 1,
            "recorded_connected_count": 1,
            "usable_connected_count": 1,
            "gmail_error_count": 0,
            "calendar_error_count": 0,
            "unread_email_count": 0,
            "upcoming_event_count": 3,
            "accounts": [],
            "usable_accounts": [],
            "gmail_errors": [],
            "calendar_errors": [],
        }
        mock_family_calendar.return_value = {
            "available": True,
            "summary": {"configured": True, "counts": {"upcoming_events": 1}},
            "connected": True,
            "event_count": 1,
        }
        mock_obsidian_support.return_value = {
            "available": True,
            "status": {"enabled": True, "detail": "Obsidian vault is available for local retrieval."},
            "enabled": True,
        }

        result = generate_morning_brief("Chris")

        assert result.truth_labels["calendar"] == "live — Google Calendar returned 3 upcoming events"
        assert any(
            item
            == "Calendar pressure: connected Google Calendar returned 3 upcoming events for planning. This is count-level context, not event interpretation."
            for item in result.what_matters
        )
        assert not any("Family calendar has 1 upcoming event loaded for planning." == item for item in result.what_matters)

    @patch("jarvis.morning_brief_pipeline._gather_obsidian_support")
    @patch("jarvis.morning_brief_pipeline._gather_family_calendar_support")
    @patch("jarvis.morning_brief_pipeline._gather_google_workspace_support")
    @patch("jarvis.morning_brief_pipeline._gather_open_loops_raw")
    @patch("jarvis.morning_brief_pipeline._gather_agent_health")
    @patch("jarvis.morning_brief_pipeline._gather_git_activity")
    def test_waiting_layer_distinguishes_inbox_and_open_loop_pressure(
        self,
        mock_git,
        mock_agents,
        mock_open_loops,
        mock_google_support,
        mock_family_calendar,
        mock_obsidian_support,
    ):
        mock_git.return_value = {"available": True, "commits": [], "count": 0}
        mock_agents.return_value = {
            "available": True,
            "agents": {},
            "degraded": [],
            "blocked": [],
            "active_mode": "",
            "degraded_count": 0,
            "running_count": 0,
            "total_agents": 0,
            "quiet_hours_active": False,
            "last_tick_at": "",
        }
        mock_google_support.return_value = {
            "available": True,
            "default_status": {
                "libraries_ready": True,
                "credentials_file_present": True,
                "token_present": True,
            },
            "client_secret": {"present": True, "path": "config/google_client_secret.json"},
            "account_count": 1,
            "recorded_connected_count": 1,
            "usable_connected_count": 1,
            "gmail_error_count": 0,
            "calendar_error_count": 0,
            "unread_email_count": 6,
            "upcoming_event_count": 0,
            "accounts": [],
            "usable_accounts": [],
            "gmail_errors": [],
            "calendar_errors": [],
        }
        mock_family_calendar.return_value = {
            "available": True,
            "summary": {"configured": False, "detail": "Family shared calendar is not configured."},
            "connected": False,
            "event_count": 0,
        }
        mock_obsidian_support.return_value = {
            "available": True,
            "status": {"enabled": False, "detail": "Obsidian vault is disabled in this runtime."},
            "enabled": False,
        }
        mock_open_loops.return_value = {
            "available": True,
            "count": 2,
            "summary": {
                "total": 2,
                "waiting_on_you": 1,
                "needs_revisit": 1,
            },
            "loops": [
                {"title": "Approve household budget draft", "domain": "approvals", "kind": "approval"},
                {"title": "Review trailer storage notes", "domain": "catalyst", "kind": "signal"},
            ],
        }

        result = generate_morning_brief("Chris")

        assert result.what_is_waiting == [
            "Inbox pressure: connected Gmail returned 6 unread items. This is waiting pressure, not thread understanding.",
            'System pressure: 2 recorded open loops need follow-through — 1 waiting on you and 1 due for revisit. Top recorded item: "Approve household budget draft".',
        ]
        assert "1 open loop is waiting on you, and 1 needs a revisit." in result.what_matters
        assert result.recommendation == "Connected Gmail shows 6 unread items. Clear inbox pressure before opening new work."
        assert result.recommendation_action == {
            "action_kind": "direct_route",
            "title": "Review inbox pressure",
            "detail": "Email Center is the current live inbox surface for unread, waiting, and draft-safe follow-through.",
            "route": "/email-center",
            "route_label": "Open Email Center",
            "truth_note": "This opens the current inbox surface. It does not mean replies were drafted or sent.",
        }

    @patch("jarvis.morning_brief_pipeline._gather_obsidian_support")
    @patch("jarvis.morning_brief_pipeline._gather_family_calendar_support")
    @patch("jarvis.morning_brief_pipeline._gather_google_workspace_support")
    @patch("jarvis.morning_brief_pipeline._gather_agent_health")
    @patch("jarvis.morning_brief_pipeline._gather_git_activity")
    @patch("jarvis.morning_brief_pipeline._gather_open_loops_raw")
    def test_recommendation_action_uses_bounded_handoff_when_only_open_loop_pressure_exists(
        self,
        mock_open_loops,
        mock_git,
        mock_agents,
        mock_google_support,
        mock_family_calendar,
        mock_obsidian_support,
    ):
        mock_git.return_value = {"available": True, "commits": [], "count": 0}
        mock_agents.return_value = {
            "available": True,
            "agents": {},
            "degraded": [],
            "blocked": [],
            "active_mode": "",
            "degraded_count": 0,
            "running_count": 0,
            "total_agents": 0,
            "quiet_hours_active": False,
            "last_tick_at": "",
        }
        mock_open_loops.return_value = {
            "available": True,
            "count": 5,
            "loops": [
                {"title": "Approve household budget draft", "domain": "approvals", "kind": "approval"},
                {"title": "Review trailer storage notes", "domain": "catalyst", "kind": "signal"},
            ],
        }
        mock_google_support.return_value = {
            "available": True,
            "default_status": {
                "libraries_ready": True,
                "credentials_file_present": True,
                "token_present": True,
            },
            "client_secret": {"present": True, "path": "config/google_client_secret.json"},
            "account_count": 1,
            "recorded_connected_count": 1,
            "usable_connected_count": 1,
            "gmail_error_count": 0,
            "calendar_error_count": 0,
            "unread_email_count": 0,
            "upcoming_event_count": 0,
            "accounts": [],
            "usable_accounts": [],
            "gmail_errors": [],
            "calendar_errors": [],
        }
        mock_family_calendar.return_value = {
            "available": True,
            "summary": {"configured": False, "detail": "Family shared calendar is not configured."},
            "connected": False,
            "event_count": 0,
        }
        mock_obsidian_support.return_value = {
            "available": True,
            "status": {"enabled": False, "detail": "Obsidian vault is disabled in this runtime."},
            "enabled": False,
        }

        result = generate_morning_brief("Chris")

        assert result.recommendation == (
            "Clear 5 open loops before starting new work. Resolution rate matters more than throughput."
        )
        assert result.recommendation_action == {
            "action_kind": "bounded_request",
            "title": "Stage follow-through in Mission Board",
            "detail": "Mission Board is the current bounded review and intake surface for recorded follow-through pressure.",
            "route": "/mission-board",
            "route_label": "Open Mission Board",
            "truth_note": "This is a bounded handoff into the review surface, not direct completion of those open loops.",
        }

    @patch("jarvis.morning_brief_pipeline._gather_obsidian_support")
    @patch("jarvis.morning_brief_pipeline._gather_family_calendar_support")
    @patch("jarvis.morning_brief_pipeline._gather_google_workspace_support")
    @patch("jarvis.morning_brief_pipeline._gather_agent_health")
    @patch("jarvis.morning_brief_pipeline._gather_git_activity")
    @patch("jarvis.morning_brief_pipeline._gather_open_loops_raw")
    def test_recommendation_prefers_decisive_inbox_handoff_when_inbox_calendar_and_open_loop_pressure_stack(
        self,
        mock_open_loops,
        mock_git,
        mock_agents,
        mock_google_support,
        mock_family_calendar,
        mock_obsidian_support,
    ):
        mock_git.return_value = {"available": True, "commits": [], "count": 0}
        mock_agents.return_value = {
            "available": True,
            "agents": {},
            "degraded": [],
            "blocked": [],
            "active_mode": "",
            "degraded_count": 0,
            "running_count": 0,
            "total_agents": 0,
            "quiet_hours_active": False,
            "last_tick_at": "",
        }
        mock_open_loops.return_value = {
            "available": True,
            "count": 4,
            "summary": {
                "total": 4,
                "waiting_on_you": 3,
                "needs_revisit": 1,
            },
            "loops": [
                {"title": "Approve household budget draft", "domain": "approvals", "kind": "approval"},
                {"title": "Review trailer storage notes", "domain": "catalyst", "kind": "signal"},
            ],
        }
        mock_google_support.return_value = {
            "available": True,
            "default_status": {
                "libraries_ready": True,
                "credentials_file_present": True,
                "token_present": True,
            },
            "client_secret": {"present": True, "path": "config/google_client_secret.json"},
            "account_count": 1,
            "recorded_connected_count": 1,
            "usable_connected_count": 1,
            "gmail_error_count": 0,
            "calendar_error_count": 0,
            "unread_email_count": 6,
            "upcoming_event_count": 2,
            "accounts": [],
            "usable_accounts": [],
            "gmail_errors": [],
            "calendar_errors": [],
        }
        mock_family_calendar.return_value = {
            "available": True,
            "summary": {"configured": False, "detail": "Family shared calendar is not configured."},
            "connected": False,
            "event_count": 0,
        }
        mock_obsidian_support.return_value = {
            "available": True,
            "status": {"enabled": True, "detail": "Obsidian vault is available for local retrieval."},
            "enabled": True,
        }

        result = generate_morning_brief("Chris")

        assert result.recommendation == (
            "Connected Gmail shows 6 unread items, your calendar already has 2 upcoming events, and 3 open loops are already waiting on you. "
            "Start with inbox pressure before staging more follow-through."
        )
        assert result.recommendation_action == {
            "action_kind": "direct_route",
            "title": "Review stacked inbox pressure first",
            "detail": "Email Center is the most precise current first surface when inbox, calendar, and open-loop pressure are all active at once.",
            "route": "/email-center",
            "route_label": "Open Email Center",
            "truth_note": "This opens the inbox surface first. It does not interpret thread meaning or resolve calendar and open-loop pressure by itself.",
        }

    @patch("jarvis.morning_brief_pipeline._gather_obsidian_support")
    @patch("jarvis.morning_brief_pipeline._gather_family_calendar_support")
    @patch("jarvis.morning_brief_pipeline._gather_google_workspace_support")
    @patch("jarvis.morning_brief_pipeline._gather_open_loops_raw")
    @patch("jarvis.morning_brief_pipeline._gather_agent_health")
    @patch("jarvis.morning_brief_pipeline._gather_git_activity")
    def test_open_loop_pressure_stays_more_useful_without_claiming_thread_understanding(
        self,
        mock_git,
        mock_agents,
        mock_open_loops,
        mock_google_support,
        mock_family_calendar,
        mock_obsidian_support,
    ):
        mock_git.return_value = {"available": True, "commits": [], "count": 0}
        mock_agents.return_value = {
            "available": True,
            "agents": {},
            "degraded": [],
            "blocked": [],
            "active_mode": "",
            "degraded_count": 0,
            "running_count": 0,
            "total_agents": 0,
            "quiet_hours_active": False,
            "last_tick_at": "",
        }
        mock_open_loops.return_value = {
            "available": True,
            "count": 4,
            "summary": {
                "total": 4,
                "waiting_on_you": 3,
                "needs_revisit": 1,
            },
            "loops": [
                {"title": "Approve household budget draft", "domain": "approvals", "kind": "approval"},
                {"title": "Review trailer storage notes", "domain": "catalyst", "kind": "signal"},
            ],
        }
        mock_google_support.return_value = {
            "available": True,
            "default_status": {
                "libraries_ready": True,
                "credentials_file_present": True,
                "token_present": True,
            },
            "client_secret": {"present": True, "path": "config/google_client_secret.json"},
            "account_count": 1,
            "recorded_connected_count": 1,
            "usable_connected_count": 1,
            "gmail_error_count": 0,
            "calendar_error_count": 0,
            "unread_email_count": 0,
            "upcoming_event_count": 0,
            "accounts": [],
            "usable_accounts": [],
            "gmail_errors": [],
            "calendar_errors": [],
        }
        mock_family_calendar.return_value = {
            "available": True,
            "summary": {"configured": False, "detail": "Family shared calendar is not configured."},
            "connected": False,
            "event_count": 0,
        }
        mock_obsidian_support.return_value = {
            "available": True,
            "status": {"enabled": True, "detail": "Obsidian vault is available for local retrieval."},
            "enabled": True,
        }

        result = generate_morning_brief("Chris")

        assert result.what_is_waiting[1] == (
            'System pressure: 4 recorded open loops need follow-through — 3 waiting on you and 1 due for revisit. Top recorded item: "Approve household budget draft".'
        )
        assert "3 open loops are waiting on you, and 1 needs a revisit." in result.what_matters
        assert (
            "Obsidian local context is available if you want to ground today's follow-through in prior notes. "
            "This brief did not open or recall any specific note."
        ) in result.may_have_forgotten

    @patch("jarvis.morning_brief_pipeline._gather_obsidian_support")
    @patch("jarvis.morning_brief_pipeline._gather_family_calendar_support")
    @patch("jarvis.morning_brief_pipeline._gather_google_workspace_support")
    @patch("jarvis.morning_brief_pipeline._gather_open_loops_raw")
    @patch("jarvis.morning_brief_pipeline._gather_agent_health")
    @patch("jarvis.morning_brief_pipeline._gather_git_activity")
    def test_recommendation_action_stays_narrative_when_no_single_truthful_surface_exists(
        self,
        mock_git,
        mock_agents,
        mock_open_loops,
        mock_google_support,
        mock_family_calendar,
        mock_obsidian_support,
    ):
        mock_git.return_value = {"available": True, "commits": [], "count": 0}
        mock_agents.return_value = {
            "available": True,
            "agents": {},
            "degraded": [],
            "blocked": [],
            "active_mode": "",
            "degraded_count": 0,
            "running_count": 0,
            "total_agents": 0,
            "quiet_hours_active": False,
            "last_tick_at": "",
        }
        mock_open_loops.return_value = {"available": True, "loops": [], "count": 0}
        mock_google_support.return_value = {
            "available": True,
            "default_status": {
                "libraries_ready": True,
                "credentials_file_present": True,
                "token_present": True,
            },
            "client_secret": {"present": True, "path": "config/google_client_secret.json"},
            "account_count": 1,
            "recorded_connected_count": 1,
            "usable_connected_count": 1,
            "gmail_error_count": 0,
            "calendar_error_count": 0,
            "unread_email_count": 0,
            "upcoming_event_count": 1,
            "accounts": [],
            "usable_accounts": [],
            "gmail_errors": [],
            "calendar_errors": [],
        }
        mock_family_calendar.return_value = {
            "available": True,
            "summary": {"configured": False, "detail": "Family shared calendar is not configured."},
            "connected": False,
            "event_count": 0,
        }
        mock_obsidian_support.return_value = {
            "available": True,
            "status": {"enabled": True, "detail": "Obsidian vault is available for local retrieval."},
            "enabled": True,
        }

        result = generate_morning_brief("Chris")

        assert result.recommendation == (
            "Use the live brief signals you already have before expanding scope. "
            "Resolve the top open loop, then check whether the connected calendar context changes today's priorities."
        )
        assert result.recommendation_action == {
            "action_kind": "narrative_only",
            "title": "No single next surface is staged",
            "detail": "This recommendation combines brief signals, so JARVIS is staying narrative instead of pretending there is one precise handoff target.",
            "truth_note": "No direct route or saved object was staged for this recommendation in the current runtime path.",
        }

    @patch("jarvis.morning_brief_pipeline._gather_autonomy_catch_up")
    @patch("jarvis.morning_brief_pipeline._gather_outcome_catch_up")
    @patch("jarvis.morning_brief_pipeline._gather_research_catch_up")
    @patch("jarvis.morning_brief_pipeline._gather_mission_catch_up")
    @patch("jarvis.morning_brief_pipeline._gather_assistant_activity_traces")
    @patch("jarvis.morning_brief_pipeline._gather_open_loops_raw")
    @patch("jarvis.morning_brief_pipeline._gather_agent_health")
    @patch("jarvis.morning_brief_pipeline._gather_git_activity")
    def test_while_you_were_away_distinguishes_completed_and_staged_state(
        self,
        mock_git,
        mock_agents,
        mock_open_loops,
        mock_activity,
        mock_mission_catch_up,
        mock_research_catch_up,
        mock_outcome_catch_up,
        mock_autonomy_catch_up,
    ):
        mock_git.return_value = {"available": True, "commits": [], "count": 0}
        mock_agents.return_value = {
            "available": True,
            "agents": {},
            "degraded": [],
            "blocked": [],
            "active_mode": "",
            "degraded_count": 0,
            "running_count": 0,
            "total_agents": 0,
            "quiet_hours_active": False,
            "last_tick_at": "",
        }
        mock_open_loops.return_value = {"available": True, "loops": [], "count": 0}
        mock_activity.return_value = {
            "available": True,
            "recent_count": 1,
            "recent": [
                {
                    "timestamp": "2026-06-28T11:00:00+00:00",
                    "detail": "Recorded delegation review updated.",
                    "result_summary": "Delegation report was stored for review.",
                }
            ],
        }
        mock_mission_catch_up.return_value = {
            "available": True,
            "recent_dossier_count": 1,
            "recent_report_count": 1,
            "recent_reports": [{"report_id": "r-1", "mission_id": "mission-1", "title": "Review contractor packet"}],
            "staged_mission_count": 0,
            "staged_missions": [],
        }
        mock_research_catch_up.return_value = {
            "available": True,
            "recent_task_count": 1,
            "recent_synthesis_count": 1,
            "recent_evidence_only_count": 0,
            "recent_tasks": [],
        }
        mock_outcome_catch_up.return_value = {
            "available": True,
            "recent_count": 2,
            "recent": [],
        }
        mock_autonomy_catch_up.return_value = {
            "available": True,
            "recent_state_count": 1,
            "local_proof_count": 1,
            "planned_only_count": 0,
            "recent_states": [],
        }

        result = generate_morning_brief("Chris")

        assert result.while_you_were_away == [
            "Delegation catch-up: 1 delegation report completed with inspectable output.",
            "Research catch-up: 1 task synthesis update recorded from attached evidence only.",
            "Outcome review: 2 explicit artifact outcome records captured.",
            "Autonomy proof: 1 local follow-through proof packet recorded. This is local proof only, not broad autonomous execution.",
        ]
        assert result.truth_labels["delegation_trace"] == "recorded"
        assert result.truth_labels["research_trace"] == "recorded"
        assert result.truth_labels["outcome_trace"] == "recorded"
        assert result.truth_labels["autonomy_trace"] == "recorded"
        assert result.recommendation == (
            "Review the recorded catch-up outputs before opening new work. "
            "They represent inspectable completed state, not just staged plans."
        )
        assert result.recommendation_action == {
            "action_kind": "direct_route",
            "title": "Inspect latest delegation report",
            "detail": "Review contractor packet is a real completed delegation output and can be opened directly.",
            "route": "/mission-board/delegation-report/mission-1/r-1?return_to=%2Fbriefing-center",
            "route_label": "Open Delegation Report",
            "truth_note": "This opens a recorded delegation report. It does not imply any new delegated work ran beyond the stored output.",
        }

    @patch("jarvis.morning_brief_pipeline._gather_autonomy_catch_up")
    @patch("jarvis.morning_brief_pipeline._gather_outcome_catch_up")
    @patch("jarvis.morning_brief_pipeline._gather_research_catch_up")
    @patch("jarvis.morning_brief_pipeline._gather_mission_catch_up")
    @patch("jarvis.morning_brief_pipeline._gather_assistant_activity_traces")
    @patch("jarvis.morning_brief_pipeline._gather_open_loops_raw")
    @patch("jarvis.morning_brief_pipeline._gather_agent_health")
    @patch("jarvis.morning_brief_pipeline._gather_git_activity")
    def test_catch_up_recommendation_falls_back_to_family_route_when_no_real_object_id_exists(
        self,
        mock_git,
        mock_agents,
        mock_open_loops,
        mock_activity,
        mock_mission_catch_up,
        mock_research_catch_up,
        mock_outcome_catch_up,
        mock_autonomy_catch_up,
    ):
        mock_git.return_value = {"available": True, "commits": [], "count": 0}
        mock_agents.return_value = {
            "available": True,
            "agents": {},
            "degraded": [],
            "blocked": [],
            "active_mode": "",
            "degraded_count": 0,
            "running_count": 0,
            "total_agents": 0,
            "quiet_hours_active": False,
            "last_tick_at": "",
        }
        mock_open_loops.return_value = {"available": True, "loops": [], "count": 0}
        mock_activity.return_value = {"available": True, "recent_count": 0, "recent": []}
        mock_mission_catch_up.return_value = {
            "available": True,
            "recent_dossier_count": 1,
            "recent_report_count": 1,
            "recent_reports": [{"title": "Report without id"}],
            "staged_mission_count": 0,
            "staged_missions": [],
        }
        mock_research_catch_up.return_value = {
            "available": True,
            "recent_task_count": 0,
            "recent_synthesis_count": 0,
            "recent_evidence_only_count": 0,
            "recent_tasks": [],
        }
        mock_outcome_catch_up.return_value = {
            "available": True,
            "recent_count": 0,
            "recent": [],
        }
        mock_autonomy_catch_up.return_value = {
            "available": True,
            "recent_state_count": 0,
            "local_proof_count": 0,
            "planned_only_count": 0,
            "recent_states": [],
        }

        result = generate_morning_brief("Chris")

        assert result.recommendation == (
            "Review the recorded catch-up outputs before opening new work. "
            "They represent inspectable completed state, not just staged plans."
        )
        assert result.recommendation_action == {
            "action_kind": "direct_route",
            "title": "Review recorded catch-up",
            "detail": "Activity Center is the shared readable surface for recent recorded continuity across delegation, outcomes, research, and autonomy traces.",
            "route": "/activity-center",
            "route_label": "Open Activity Center",
            "truth_note": "This opens recorded continuity. Planned-only state still remains distinct from completed work.",
        }

    @patch("jarvis.morning_brief_pipeline._gather_autonomy_catch_up")
    @patch("jarvis.morning_brief_pipeline._gather_outcome_catch_up")
    @patch("jarvis.morning_brief_pipeline._gather_research_catch_up")
    @patch("jarvis.morning_brief_pipeline._gather_mission_catch_up")
    @patch("jarvis.morning_brief_pipeline._gather_assistant_activity_traces")
    @patch("jarvis.morning_brief_pipeline._gather_open_loops_raw")
    @patch("jarvis.morning_brief_pipeline._gather_agent_health")
    @patch("jarvis.morning_brief_pipeline._gather_git_activity")
    def test_while_you_were_away_keeps_planned_only_and_empty_states_plain(
        self,
        mock_git,
        mock_agents,
        mock_open_loops,
        mock_activity,
        mock_mission_catch_up,
        mock_research_catch_up,
        mock_outcome_catch_up,
        mock_autonomy_catch_up,
    ):
        mock_git.return_value = {"available": True, "commits": [], "count": 0}
        mock_agents.return_value = {
            "available": True,
            "agents": {},
            "degraded": [],
            "blocked": [],
            "active_mode": "",
            "degraded_count": 0,
            "running_count": 0,
            "total_agents": 0,
            "quiet_hours_active": False,
            "last_tick_at": "",
        }
        mock_open_loops.return_value = {"available": True, "loops": [], "count": 0}
        mock_activity.return_value = {"available": True, "recent_count": 0, "recent": []}
        mock_mission_catch_up.return_value = {
            "available": True,
            "recent_dossier_count": 2,
            "recent_report_count": 0,
            "recent_reports": [],
            "staged_mission_count": 2,
            "staged_missions": [{"title": "Mission A"}, {"title": "Mission B"}],
        }
        mock_research_catch_up.return_value = {
            "available": True,
            "recent_task_count": 0,
            "recent_synthesis_count": 0,
            "recent_evidence_only_count": 0,
            "recent_tasks": [],
        }
        mock_outcome_catch_up.return_value = {
            "available": True,
            "recent_count": 0,
            "recent": [],
        }
        mock_autonomy_catch_up.return_value = {
            "available": True,
            "recent_state_count": 0,
            "local_proof_count": 0,
            "planned_only_count": 0,
            "recent_states": [],
        }

        result = generate_morning_brief("Chris")

        assert result.while_you_were_away == [
            "Mission staging: 2 mission workspaces refreshed with prepared next steps. This is staged work, not completed execution.",
            "No inspectable delegation, research, outcome, or autonomy traces were recorded in this runtime. Current catch-up is limited to staged mission state and other explicitly logged surfaces.",
        ]
        assert result.truth_labels["delegation_trace"] == "planned-only"
        assert result.truth_labels["research_trace"] == "empty — no recent research-task traces are visible"
        assert result.truth_labels["outcome_trace"] == "empty — no recent artifact outcome traces are visible"
        assert result.truth_labels["autonomy_trace"] == "empty — no recent autonomy traces are visible"

    @patch("jarvis.morning_brief_pipeline._gather_autonomy_catch_up")
    @patch("jarvis.morning_brief_pipeline._gather_outcome_catch_up")
    @patch("jarvis.morning_brief_pipeline._gather_research_catch_up")
    @patch("jarvis.morning_brief_pipeline._gather_mission_catch_up")
    @patch("jarvis.morning_brief_pipeline._gather_assistant_activity_traces")
    @patch("jarvis.morning_brief_pipeline._gather_open_loops_raw")
    @patch("jarvis.morning_brief_pipeline._gather_agent_health")
    @patch("jarvis.morning_brief_pipeline._gather_git_activity")
    def test_while_you_were_away_keeps_assistant_activity_when_room_remains(
        self,
        mock_git,
        mock_agents,
        mock_open_loops,
        mock_activity,
        mock_mission_catch_up,
        mock_research_catch_up,
        mock_outcome_catch_up,
        mock_autonomy_catch_up,
    ):
        mock_git.return_value = {"available": True, "commits": [], "count": 0}
        mock_agents.return_value = {
            "available": True,
            "agents": {},
            "degraded": [],
            "blocked": [],
            "active_mode": "",
            "degraded_count": 0,
            "running_count": 0,
            "total_agents": 0,
            "quiet_hours_active": False,
            "last_tick_at": "",
        }
        mock_open_loops.return_value = {"available": True, "loops": [], "count": 0}
        mock_activity.return_value = {
            "available": True,
            "recent_count": 1,
            "recent": [{"result_summary": "Review note recorded."}],
        }
        mock_mission_catch_up.return_value = {
            "available": True,
            "recent_dossier_count": 0,
            "recent_report_count": 0,
            "recent_reports": [],
            "staged_mission_count": 0,
            "staged_missions": [],
        }
        mock_research_catch_up.return_value = {
            "available": True,
            "recent_task_count": 0,
            "recent_synthesis_count": 0,
            "recent_evidence_only_count": 0,
            "recent_tasks": [],
        }
        mock_outcome_catch_up.return_value = {
            "available": True,
            "recent_count": 0,
            "recent": [],
        }
        mock_autonomy_catch_up.return_value = {
            "available": True,
            "recent_state_count": 0,
            "local_proof_count": 0,
            "planned_only_count": 0,
            "recent_states": [],
        }

        result = generate_morning_brief("Chris")

        assert result.while_you_were_away == [
            "Recorded assistant activity: 1 assistant action logged. Latest: Review note recorded.",
            "No inspectable delegation, research, outcome, or autonomy traces were recorded in this runtime. Current catch-up is limited to staged mission state and other explicitly logged surfaces.",
        ]
