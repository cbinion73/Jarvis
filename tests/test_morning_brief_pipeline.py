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
