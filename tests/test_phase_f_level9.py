"""Phase F: Level 9 capstone tests.

Covers F1-F7 rows from JARVIS-LEVEL9-COMPREHENSIVE-CHECKLIST.md.

F1: Runtime constitution — citations, recommendations, wrap-decision
F2: Household modes — Level 9 modes drive different priorities/agents/rituals/autonomy
F3: Value simulation — multi-dimensional scoring, comparison, dissent
F4: Legacy archive — permission gating, provenance, correction/dispute
F5: Long-horizon reviews — arc summary showing prior lessons changed guidance
F6: Household admin — non-developer controls, permission enforcement
F7: Personnel/device continuity — step-based workflows for membership changes

Scenario proofs:
  - crisis_day: mode drives reduced autonomy, critical alerts only
  - sabbath: monitor ceiling, agents suspended, rituals suppressed
  - child_role_change: step-based workflow tracks child→adult promotion
  - health_recovery: value simulation routes toward rest over work
  - legacy_recall: permission gate blocks child from adults_only content
"""
from __future__ import annotations

import sys
import types
import tempfile
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# FastAPI stub (same pattern across the test suite)
# ---------------------------------------------------------------------------

def _install_fastapi_stub() -> None:
    if "fastapi" in sys.modules:
        return
    fa = types.ModuleType("fastapi")
    fa.FastAPI = object  # type: ignore[attr-defined]
    fa.HTTPException = Exception  # type: ignore[attr-defined]
    fa.Request = object  # type: ignore[attr-defined]
    fa.Response = object  # type: ignore[attr-defined]
    sys.modules["fastapi"] = fa
    sys.modules["fastapi.responses"] = types.ModuleType("fastapi.responses")
    sys.modules["fastapi.responses"].JSONResponse = object  # type: ignore
    sys.modules["fastapi.middleware"] = types.ModuleType("fastapi.middleware")
    sys.modules["fastapi.middleware.cors"] = types.ModuleType("fastapi.middleware.cors")
    sys.modules["fastapi.middleware.cors"].CORSMiddleware = object  # type: ignore

_install_fastapi_stub()


# ===========================================================================
# F1: Constitution engine
# ===========================================================================

class TestConstitutionEngine:
    def _engine(self, tmp: Path):
        from jarvis.constitution_engine import ConstitutionEngine
        return ConstitutionEngine(audit_path=tmp / "audit.jsonl")

    def test_cite_returns_citation_with_principle(self, tmp_path: Path) -> None:
        engine = self._engine(tmp_path)
        citation = engine.cite(
            decision_id="test-001",
            actor="chris",
            recommendation_summary="Consolidate three task lanes",
            principle_ids=["III.1.mandate_first"],
            authority_stage="sandbox_live",
        )
        assert citation.decision_id == "test-001"
        assert "III.1.mandate_first" in citation.principle_ids
        assert citation.authority_stage == "sandbox_live"
        assert citation.source == "constitution_engine"

    def test_cite_invalid_principle_falls_back_to_legible_agency(self, tmp_path: Path) -> None:
        engine = self._engine(tmp_path)
        citation = engine.cite(
            decision_id="test-002",
            actor="chris",
            recommendation_summary="Test fallback",
            principle_ids=["FAKE.principle"],
            authority_stage="suggest",
        )
        assert "III.3.legible_agency" in citation.principle_ids

    def test_cite_includes_authority_basis_description(self, tmp_path: Path) -> None:
        engine = self._engine(tmp_path)
        citation = engine.cite(
            decision_id="test-003",
            actor="chris",
            recommendation_summary="Suggest task merge",
            authority_stage="suggest",
        )
        assert "suggestion" in citation.authority_basis.lower() or "suggest" in citation.authority_basis.lower()

    def test_make_recommendation_includes_citation(self, tmp_path: Path) -> None:
        engine = self._engine(tmp_path)
        rec = engine.make_recommendation(
            actor="chris",
            summary="Merge sprint lanes",
            detail="Three active lanes create cognitive overhead.",
            domain="work",
            principle_ids=["III.1.mandate_first", "II.2.broad_delegation"],
            authority_stage="sandbox_live",
            confidence=0.8,
        )
        assert rec.recommendation_id
        assert rec.citation.principle_ids
        assert rec.confidence == 0.8
        assert rec.domain == "work"

    def test_make_recommendation_confidence_clamped(self, tmp_path: Path) -> None:
        engine = self._engine(tmp_path)
        rec = engine.make_recommendation(
            actor="chris", summary="x", detail="y", domain="health",
            confidence=2.5,
        )
        assert rec.confidence == 1.0

    def test_wrap_decision_adds_citation_field(self, tmp_path: Path) -> None:
        engine = self._engine(tmp_path)
        decision = {"action": "archive_old_tasks", "count": 12}
        wrapped = engine.wrap_decision(
            decision,
            actor="chris",
            principle_ids=["III.5.review_after_action"],
            authority_stage="sandbox_live",
        )
        assert "constitutional_citation" in wrapped
        assert wrapped["action"] == "archive_old_tasks"
        assert wrapped["constitutional_citation"]["authority_stage"] == "sandbox_live"

    def test_principle_reference_card_returns_all_principles(self, tmp_path: Path) -> None:
        from jarvis.constitution_engine import CONSTITUTIONAL_PRINCIPLES
        engine = self._engine(tmp_path)
        card = engine.principle_reference_card()
        assert card["principle_count"] == len(CONSTITUTIONAL_PRINCIPLES)
        assert "authority_stages" in card
        assert "uncertainty_levels" in card

    def test_audit_file_written(self, tmp_path: Path) -> None:
        engine = self._engine(tmp_path)
        engine.cite(
            decision_id="audit-test",
            actor="chris",
            recommendation_summary="Test audit",
        )
        assert (tmp_path / "audit.jsonl").exists()


# ===========================================================================
# F2: Household modes (Level 9)
# ===========================================================================

class TestHouseholdModes:
    def _mgr(self, tmp: Path):
        from jarvis.household_modes import Level9ModeManager
        return Level9ModeManager(root=tmp / "modes")

    def test_default_mode_is_normal(self, tmp_path: Path) -> None:
        mgr = self._mgr(tmp_path)
        status = mgr.get_status()
        assert status["current_mode"] == "normal"
        assert status["source"] == "live"

    def test_set_mode_changes_current(self, tmp_path: Path) -> None:
        mgr = self._mgr(tmp_path)
        result = mgr.set_mode("travel", "chris", reason="Flying to Denver", permission_level="admin")
        assert result["ok"] is True
        assert mgr.get_status()["current_mode"] == "travel"

    def test_crisis_mode_has_reduced_autonomy(self, tmp_path: Path) -> None:
        mgr = self._mgr(tmp_path)
        mgr.set_mode("crisis", "chris", permission_level="admin")
        status = mgr.get_status()
        assert status["autonomy_ceiling"] == "suggest"
        assert status["notification_level"] == "critical_only"

    def test_sabbath_mode_has_monitor_ceiling(self, tmp_path: Path) -> None:
        mgr = self._mgr(tmp_path)
        mgr.set_mode("sabbath", "chris", permission_level="admin")
        status = mgr.get_status()
        assert status["autonomy_ceiling"] == "monitor"
        assert status["notification_level"] == "critical_only"

    def test_sabbath_mode_tts_disabled(self, tmp_path: Path) -> None:
        from jarvis.household_modes import LEVEL9_MODES
        mode = LEVEL9_MODES["sabbath"]
        assert mode.tts_enabled is False

    def test_invalid_mode_raises_value_error(self, tmp_path: Path) -> None:
        mgr = self._mgr(tmp_path)
        with pytest.raises(ValueError):
            mgr.set_mode("fake_mode", "chris", permission_level="admin")

    def test_get_behavior_impact_returns_full_contract(self, tmp_path: Path) -> None:
        mgr = self._mgr(tmp_path)
        impact = mgr.get_behavior_impact("crisis")
        assert impact["mode_id"] == "crisis"
        assert "priority_domains" in impact
        assert "suspended_agents" in impact

    def test_list_modes_returns_all_nine(self, tmp_path: Path) -> None:
        mgr = self._mgr(tmp_path)
        modes = mgr.list_modes()
        assert len(modes) == 9
        expected = {"normal", "travel", "crisis", "sabbath", "school", "health_recovery", "guest", "sprint", "emergency"}
        assert set(modes.keys()) == expected

    def test_mode_history_records_transitions(self, tmp_path: Path) -> None:
        mgr = self._mgr(tmp_path)
        mgr.set_mode("travel", "chris", permission_level="admin")
        mgr.set_mode("normal", "chris", permission_level="admin")
        history = mgr.mode_history()
        assert len(history) >= 2

    def test_check_action_permitted_crisis_blocks_financial(self, tmp_path: Path) -> None:
        mgr = self._mgr(tmp_path)
        result = mgr.check_action_permitted("financial", "crisis")
        assert result["approval_required"] is True


# ===========================================================================
# F3: Value simulation
# ===========================================================================

class TestValueSimulation:
    def _engine(self, tmp: Path):
        from jarvis.value_simulation import ValueSimulationEngine
        return ValueSimulationEngine(root=tmp / "vs")

    def _make_option(self, engine, label: str, all_score: float):
        dims = {d: {"score": all_score, "explanation": "test", "confidence": 0.8, "time_horizon": "immediate"}
                for d in ["time", "money", "health", "faith", "family", "risk", "opportunity", "reputation", "long_term"]}
        return engine.score_option(option_id=label, label=label, description="", dimension_inputs=dims)

    def test_score_option_produces_total(self, tmp_path: Path) -> None:
        engine = self._engine(tmp_path)
        opt = self._make_option(engine, "option_a", 0.8)
        assert -1.0 <= opt.total_score <= 1.0
        assert opt.recommendation_strength in ("strong", "moderate", "weak", "neutral", "against")

    def test_simulate_recommends_higher_scoring_option(self, tmp_path: Path) -> None:
        engine = self._engine(tmp_path)
        good = self._make_option(engine, "good", 0.8)
        bad = self._make_option(engine, "bad", -0.5)
        sim = engine.simulate(
            actor="chris",
            question="Should I do A or B?",
            options=[good, bad],
            dissent="Could argue the opposite.",
        )
        assert sim.recommended_option_id == "good"

    def test_simulate_requires_at_least_one_option(self, tmp_path: Path) -> None:
        engine = self._engine(tmp_path)
        with pytest.raises(ValueError):
            engine.simulate(actor="chris", question="q", options=[])

    def test_simulate_persists_and_retrievable(self, tmp_path: Path) -> None:
        engine = self._engine(tmp_path)
        opt = self._make_option(engine, "only", 0.5)
        sim = engine.simulate(actor="chris", question="test persist", options=[opt])
        retrieved = engine.get(sim.simulation_id)
        assert retrieved is not None
        assert retrieved["simulation_id"] == sim.simulation_id

    def test_compare_summary_shows_ranked_options(self, tmp_path: Path) -> None:
        engine = self._engine(tmp_path)
        good = self._make_option(engine, "good", 0.9)
        bad = self._make_option(engine, "bad", 0.1)
        sim = engine.simulate(actor="chris", question="pick one", options=[good, bad])
        summary = engine.compare_summary(sim.simulation_id)
        assert summary["recommended"] == "good"
        ranks = [o["label"] for o in summary["options_ranked"]]
        assert ranks[0] == "good"

    def test_list_recent_filters_by_actor(self, tmp_path: Path) -> None:
        engine = self._engine(tmp_path)
        opt = self._make_option(engine, "x", 0.5)
        engine.simulate(actor="chris", question="chris q", options=[opt])
        engine.simulate(actor="sarah", question="sarah q", options=[opt])
        chris_sims = engine.list_recent("chris")
        assert all(s["actor"] == "chris" for s in chris_sims)

    def test_dissent_and_uncertainty_stored(self, tmp_path: Path) -> None:
        engine = self._engine(tmp_path)
        opt = self._make_option(engine, "a", 0.6)
        sim = engine.simulate(
            actor="chris", question="q", options=[opt],
            dissent="A valid dissent view",
            uncertainty="We don't know the long-term effect",
        )
        retrieved = engine.get(sim.simulation_id)
        assert retrieved["dissent"] == "A valid dissent view"
        assert "long-term" in retrieved["uncertainty"]

    def test_score_negative_option_is_against(self, tmp_path: Path) -> None:
        engine = self._engine(tmp_path)
        opt = self._make_option(engine, "risky", -0.8)
        assert opt.recommendation_strength == "against"


# ===========================================================================
# F4: Legacy archive
# ===========================================================================

class TestLegacyArchive:
    def _store(self, tmp: Path):
        from jarvis.legacy_archive import LegacyArchiveStore
        return LegacyArchiveStore(root=tmp / "legacy")

    def test_add_entry_persists(self, tmp_path: Path) -> None:
        store = self._store(tmp_path)
        entry = store.add_entry(
            entry_type="story",
            title="The Night We Got Lost",
            content="On a camping trip in 2023...",
            date="2023-08-15",
            actor="chris",
        )
        assert entry.entry_id
        assert entry.entry_type == "story"
        assert entry.status == "active"

    def test_list_entries_permission_gate_blocks_adults_only_from_family(self, tmp_path: Path) -> None:
        store = self._store(tmp_path)
        store.add_entry(
            entry_type="decision", title="Public entry", content="x",
            date="2024-01-01", actor="chris", permission_level="family",
        )
        store.add_entry(
            entry_type="decision", title="Adults only entry", content="y",
            date="2024-01-01", actor="chris", permission_level="adults_only",
        )
        family_entries = store.list_entries(actor_permission="family")
        titles = [e["title"] for e in family_entries]
        assert "Public entry" in titles
        assert "Adults only entry" not in titles

    def test_list_entries_adults_see_adults_only(self, tmp_path: Path) -> None:
        store = self._store(tmp_path)
        store.add_entry(
            entry_type="lesson", title="Adult lesson", content="z",
            date="2024-01-01", actor="chris", permission_level="adults_only",
        )
        entries = store.list_entries(actor_permission="adults_only")
        assert any(e["title"] == "Adult lesson" for e in entries)

    def test_correct_entry_changes_status(self, tmp_path: Path) -> None:
        store = self._store(tmp_path)
        entry = store.add_entry(
            entry_type="milestone", title="First steps", content="content",
            date="2020-03-01", actor="chris",
        )
        result = store.correct_entry(entry.entry_id, "chris", "The date was March 3, not March 1.")
        assert result["status"] == "corrected"
        assert "March 3" in result["correction_note"]

    def test_dispute_entry_changes_status(self, tmp_path: Path) -> None:
        store = self._store(tmp_path)
        entry = store.add_entry(
            entry_type="story", title="Disputed story", content="x",
            date="2021-01-01", actor="chris",
        )
        result = store.dispute_entry(entry.entry_id, "sarah", "I remember it differently.")
        assert result["status"] == "disputed"

    def test_create_bundle_links_entries(self, tmp_path: Path) -> None:
        store = self._store(tmp_path)
        e1 = store.add_entry(entry_type="story", title="Story 1", content="a", date="2023-01-01", actor="chris")
        e2 = store.add_entry(entry_type="milestone", title="Milestone 1", content="b", date="2023-06-01", actor="chris")
        bundle = store.create_bundle(
            title="2023 Highlights",
            description="Best of 2023",
            theme="family_growth",
            actor="chris",
            entry_ids=[e1.entry_id, e2.entry_id],
        )
        assert bundle.bundle_id
        assert len(bundle.entry_ids) == 2

    def test_export_bundle_includes_full_entries(self, tmp_path: Path) -> None:
        store = self._store(tmp_path)
        e = store.add_entry(entry_type="ritual", title="Evening prayer", content="content", date="2024-01-01", actor="chris")
        bundle = store.create_bundle(title="Rituals", description="d", theme="faith", actor="chris", entry_ids=[e.entry_id])
        export = store.export_bundle(bundle.bundle_id, "chris")
        assert export["export_type"] == "legacy_bundle"
        assert export["entry_count"] == 1
        assert export["entries"][0]["entry_id"] == e.entry_id

    def test_invalid_entry_type_raises(self, tmp_path: Path) -> None:
        store = self._store(tmp_path)
        with pytest.raises(ValueError):
            store.add_entry(entry_type="fake_type", title="t", content="c", date="2024-01-01", actor="chris")


# ===========================================================================
# F5: Long-horizon reviews
# ===========================================================================

class TestLongHorizonReviews:
    def _store(self, tmp: Path):
        from jarvis.long_horizon import LongHorizonStore
        return LongHorizonStore(root=tmp / "horizon")

    def test_create_review_persists(self, tmp_path: Path) -> None:
        store = self._store(tmp_path)
        review = store.create_review(
            actor="chris",
            cadence="monthly",
            period_label="2026-05",
            period_start="2026-05-01",
            period_end="2026-05-31",
            overall_narrative="Solid month.",
            key_lesson="Rest is productive.",
        )
        assert review.review_id
        assert review.cadence == "monthly"
        assert review.status == "draft"

    def test_complete_review_changes_status(self, tmp_path: Path) -> None:
        store = self._store(tmp_path)
        review = store.create_review(
            actor="chris", cadence="monthly", period_label="2026-04",
            period_start="2026-04-01", period_end="2026-04-30",
        )
        result = store.complete_review(review.review_id, "chris")
        assert result["status"] == "complete"
        assert result["completed_at"]

    def test_arc_summary_requires_completed_reviews(self, tmp_path: Path) -> None:
        store = self._store(tmp_path)
        result = store.get_arc_summary("chris", "monthly")
        assert result["source"] == "unavailable"

    def test_arc_summary_shows_lessons(self, tmp_path: Path) -> None:
        store = self._store(tmp_path)
        for month in ["2026-01", "2026-02", "2026-03"]:
            review = store.create_review(
                actor="chris", cadence="monthly", period_label=month,
                period_start=f"{month}-01", period_end=f"{month}-28",
                key_lesson=f"Lesson from {month}",
                what_changed_guidance=f"Changed behavior after {month}",
            )
            store.complete_review(review.review_id, "chris")
        arc = store.get_arc_summary("chris", "monthly")
        assert arc["period_count"] == 3
        assert len(arc["key_lessons"]) == 3
        assert arc["source"] == "live"

    def test_arc_summary_identifies_persistent_drift(self, tmp_path: Path) -> None:
        store = self._store(tmp_path)
        for month in ["2026-01", "2026-02"]:
            review = store.create_review(
                actor="chris", cadence="monthly", period_label=month,
                period_start=f"{month}-01", period_end=f"{month}-28",
                domain_reviews=[{
                    "domain": "health",
                    "current_state": "ok",
                    "progress_since_last": "same",
                    "lessons_applied": [],
                    "drift_flags": ["exercise_missed"],
                    "forward_intentions": [],
                    "domain_score": 5,
                    "confidence": 0.7,
                }],
            )
            store.complete_review(review.review_id, "chris")
        arc = store.get_arc_summary("chris", "monthly")
        assert "exercise_missed" in arc["persistent_drift_flags"]

    def test_domain_trend_tracks_scores(self, tmp_path: Path) -> None:
        store = self._store(tmp_path)
        for month, score in [("2026-01", 6), ("2026-02", 7)]:
            store.create_review(
                actor="chris", cadence="monthly", period_label=month,
                period_start=f"{month}-01", period_end=f"{month}-28",
                domain_reviews=[{
                    "domain": "health",
                    "current_state": "improving",
                    "progress_since_last": "better",
                    "lessons_applied": [],
                    "drift_flags": [],
                    "forward_intentions": [],
                    "domain_score": score,
                    "confidence": 0.8,
                }],
            )
        trend = store.get_domain_trend("chris", "health", "monthly")
        assert trend["data_points"] == 2
        assert trend["source"] == "live"

    def test_prior_review_id_linked_to_previous(self, tmp_path: Path) -> None:
        store = self._store(tmp_path)
        r1 = store.create_review(
            actor="chris", cadence="monthly", period_label="2026-01",
            period_start="2026-01-01", period_end="2026-01-31",
        )
        store.complete_review(r1.review_id, "chris")
        r2 = store.create_review(
            actor="chris", cadence="monthly", period_label="2026-02",
            period_start="2026-02-01", period_end="2026-02-28",
        )
        assert r2.prior_review_id == r1.review_id


# ===========================================================================
# F6: Household admin
# ===========================================================================

class TestHouseholdAdmin:
    def _store(self, tmp: Path):
        from jarvis.household_admin import HouseholdAdminStore
        return HouseholdAdminStore(root=tmp / "admin")

    def test_what_can_i_do_admin(self, tmp_path: Path) -> None:
        store = self._store(tmp_path)
        result = store.what_can_i_do("admin")
        assert "set_mode" in result["capabilities"]
        assert "manage_permissions" in result["capabilities"]
        assert result["source"] == "live"

    def test_what_can_i_do_child_is_limited(self, tmp_path: Path) -> None:
        store = self._store(tmp_path)
        result = store.what_can_i_do("child")
        assert "manage_permissions" not in result["capabilities"]
        assert "view_mode" in result["capabilities"]

    def test_register_device_requires_admin(self, tmp_path: Path) -> None:
        store = self._store(tmp_path)
        with pytest.raises(PermissionError):
            store.register_device(
                display_name="Kid iPad",
                device_type="tablet",
                owner="emma",
                permission_level="child",
                actor="emma",
                actor_level="child",
            )

    def test_register_device_succeeds_for_admin(self, tmp_path: Path) -> None:
        store = self._store(tmp_path)
        device = store.register_device(
            display_name="Chris Phone",
            device_type="phone",
            owner="chris",
            permission_level="admin",
            actor="chris",
            actor_level="admin",
        )
        assert device.device_id
        assert device.status == "active"

    def test_revoke_device_changes_status(self, tmp_path: Path) -> None:
        store = self._store(tmp_path)
        device = store.register_device(
            display_name="Old Tablet", device_type="tablet", owner="chris",
            permission_level="adult", actor="chris", actor_level="admin",
        )
        result = store.revoke_device(device.device_id, "chris", "admin")
        assert result["status"] == "revoked"

    def test_grant_permission_persists(self, tmp_path: Path) -> None:
        store = self._store(tmp_path)
        result = store.grant_permission(
            member="sarah",
            permission_level="adult",
            actor="chris",
            actor_level="admin",
            reason="Married household admin",
        )
        assert result["ok"] is True
        perm = store.get_permission("sarah")
        assert perm["permission_level"] == "adult"

    def test_default_permission_is_guest(self, tmp_path: Path) -> None:
        store = self._store(tmp_path)
        perm = store.get_permission("unknown_person")
        assert perm["permission_level"] == "guest"

    def test_audit_log_written_on_admin_actions(self, tmp_path: Path) -> None:
        store = self._store(tmp_path)
        store.register_device(
            display_name="Audit Test Device", device_type="phone", owner="chris",
            permission_level="adult", actor="chris", actor_level="admin",
        )
        audit = store.get_audit_summary("admin")
        assert len(audit) >= 1
        assert any("device_registered" == e.get("event") for e in audit)


# ===========================================================================
# F7: Continuity
# ===========================================================================

class TestContinuity:
    def _store(self, tmp: Path):
        from jarvis.continuity import ContinuityStore
        return ContinuityStore(root=tmp / "continuity")

    def test_member_joined_creates_event_with_steps(self, tmp_path: Path) -> None:
        store = self._store(tmp_path)
        event = store.member_joined(
            member_name="Sarah",
            role="spouse",
            actor="chris",
            initial_permission="adult",
        )
        assert event.event_type == "member_joined"
        assert event.status == "pending"
        assert len(event.steps_remaining) > 0
        assert "Sarah" in event.description

    def test_device_added_creates_event(self, tmp_path: Path) -> None:
        store = self._store(tmp_path)
        event = store.device_added(
            device_name="iPhone 16",
            device_type="phone",
            owner="chris",
            actor="chris",
        )
        assert event.event_type == "device_added"
        assert event.steps_remaining

    def test_role_changed_child_to_adult_includes_extra_steps(self, tmp_path: Path) -> None:
        store = self._store(tmp_path)
        event = store.role_changed(
            subject="Emma",
            old_role="child",
            new_role="adult",
            actor="chris",
            reason="Turned 18",
        )
        steps_text = " ".join(event.steps_remaining)
        assert "adult" in steps_text.lower() or "access" in steps_text.lower()

    def test_advance_step_moves_to_in_progress(self, tmp_path: Path) -> None:
        store = self._store(tmp_path)
        event = store.member_joined(
            member_name="Guest",
            role="guest",
            actor="chris",
        )
        first_step = event.steps_remaining[0]
        updated = store.advance_step(event.event_id, "chris", first_step)
        assert updated["status"] == "in_progress"
        assert first_step in updated["steps_completed"]
        assert first_step not in updated["steps_remaining"]

    def test_advance_all_steps_completes_event(self, tmp_path: Path) -> None:
        store = self._store(tmp_path)
        event = store.device_departed(
            device_name="Old Phone",
            owner="chris",
            actor="chris",
        )
        for step in list(event.steps_remaining):
            result = store.advance_step(event.event_id, "chris", step)
        assert result["status"] == "complete"
        assert result["restricted_data_cleared"] is True

    def test_fail_event_marks_as_failed(self, tmp_path: Path) -> None:
        store = self._store(tmp_path)
        event = store.member_departed(
            member_name="Old Guest",
            actor="chris",
        )
        result = store.fail_event(event.event_id, "chris", "Could not archive memory safely")
        assert result["status"] == "failed"
        assert "archive" in result["failure_reason"]

    def test_memory_migrated_creates_audit_trail(self, tmp_path: Path) -> None:
        store = self._store(tmp_path)
        event = store.memory_migrated(
            from_context="old_phone",
            to_context="new_phone",
            actor="chris",
            reason="Device replaced",
        )
        assert event.event_type == "memory_migrated"
        assert "old_phone" in event.description

    def test_list_events_filters_by_type(self, tmp_path: Path) -> None:
        store = self._store(tmp_path)
        store.member_joined(member_name="Person A", role="guest", actor="chris")
        store.device_added(device_name="Device B", device_type="tablet", owner="chris", actor="chris")
        member_events = store.list_events(event_type="member_joined")
        assert all(e["event_type"] == "member_joined" for e in member_events)


# ===========================================================================
# Scenario proofs
# ===========================================================================

class TestScenarioProofs:
    """End-to-end scenario tests proving Level 9 behavior."""

    def test_crisis_day_scenario(self, tmp_path: Path) -> None:
        """Crisis mode: reduced autonomy, urgent tone, critical alerts only."""
        from jarvis.household_modes import Level9ModeManager
        mgr = Level9ModeManager(root=tmp_path / "modes")
        mgr.set_mode("crisis", "chris", reason="Medical emergency", permission_level="admin")
        status = mgr.get_status()
        assert status["autonomy_ceiling"] == "suggest"
        assert status["tone"] == "urgent"
        assert status["notification_level"] == "critical_only"
        impact = mgr.get_behavior_impact("crisis")
        assert "workshop" in impact["suspended_agents"] or "workshop-copilot" in impact["suspended_agents"]

    def test_sabbath_scenario(self, tmp_path: Path) -> None:
        """Sabbath mode: monitor ceiling, faith rituals surfaced, work suppressed."""
        from jarvis.household_modes import Level9ModeManager, LEVEL9_MODES
        mgr = Level9ModeManager(root=tmp_path / "modes")
        mgr.set_mode("sabbath", "chris", reason="Sabbath observance", permission_level="admin")
        sabbath = LEVEL9_MODES["sabbath"]
        assert sabbath.autonomy_ceiling == "monitor"
        assert "work" in sabbath.suppress_domains
        assert any("prayer" in r or "devotional" in r for r in sabbath.suggested_rituals)

    def test_child_formation_legacy_recall(self, tmp_path: Path) -> None:
        """Legacy archive: child cannot see adults_only content."""
        from jarvis.legacy_archive import LegacyArchiveStore
        store = LegacyArchiveStore(root=tmp_path / "legacy")
        store.add_entry(
            entry_type="decision", title="Adult financial decision",
            content="Details only for adults", date="2024-01-01",
            actor="chris", permission_level="adults_only",
        )
        store.add_entry(
            entry_type="story", title="Family trip story",
            content="We went to the park", date="2024-06-01",
            actor="chris", permission_level="family",
        )
        child_view = store.list_entries(actor_permission="family")
        titles = [e["title"] for e in child_view]
        assert "Family trip story" in titles
        assert "Adult financial decision" not in titles

    def test_health_recovery_simulation_prefers_rest(self, tmp_path: Path) -> None:
        """Value simulation: health_recovery context scores rest > work."""
        from jarvis.value_simulation import ValueSimulationEngine
        engine = ValueSimulationEngine(root=tmp_path / "vs")

        rest_dims = {
            "time": {"score": 0.5, "explanation": "short", "confidence": 0.8, "time_horizon": "1-year"},
            "money": {"score": 0.0, "explanation": "neutral", "confidence": 0.7, "time_horizon": "immediate"},
            "health": {"score": 0.9, "explanation": "healing", "confidence": 0.9, "time_horizon": "immediate"},
            "faith": {"score": 0.7, "explanation": "trust", "confidence": 0.8, "time_horizon": "immediate"},
            "family": {"score": 0.6, "explanation": "present", "confidence": 0.8, "time_horizon": "immediate"},
            "risk": {"score": 0.6, "explanation": "low risk", "confidence": 0.9, "time_horizon": "immediate"},
            "opportunity": {"score": -0.1, "explanation": "slight delay", "confidence": 0.6, "time_horizon": "1-year"},
            "reputation": {"score": 0.0, "explanation": "neutral", "confidence": 0.5, "time_horizon": "immediate"},
            "long_term": {"score": 0.8, "explanation": "recovery matters", "confidence": 0.8, "time_horizon": "5-year"},
        }
        work_dims = {
            "time": {"score": -0.3, "explanation": "draining", "confidence": 0.8, "time_horizon": "immediate"},
            "money": {"score": 0.6, "explanation": "income", "confidence": 0.7, "time_horizon": "immediate"},
            "health": {"score": -0.9, "explanation": "worsens condition", "confidence": 0.9, "time_horizon": "immediate"},
            "faith": {"score": -0.2, "explanation": "stress", "confidence": 0.7, "time_horizon": "immediate"},
            "family": {"score": -0.5, "explanation": "absent", "confidence": 0.8, "time_horizon": "immediate"},
            "risk": {"score": -0.7, "explanation": "high risk to health", "confidence": 0.9, "time_horizon": "immediate"},
            "opportunity": {"score": 0.4, "explanation": "maintains momentum", "confidence": 0.6, "time_horizon": "1-year"},
            "reputation": {"score": 0.3, "explanation": "shows dedication", "confidence": 0.5, "time_horizon": "immediate"},
            "long_term": {"score": -0.8, "explanation": "burnout risk", "confidence": 0.8, "time_horizon": "5-year"},
        }
        rest_opt = engine.score_option(option_id="rest", label="Rest and recover", description="", dimension_inputs=rest_dims)
        work_opt = engine.score_option(option_id="work", label="Push through work", description="", dimension_inputs=work_dims)
        sim = engine.simulate(actor="chris", question="Work or rest?", options=[rest_opt, work_opt])
        assert sim.recommended_option_id == "rest"

    def test_long_arc_shows_lessons_changed_guidance(self, tmp_path: Path) -> None:
        """Long-horizon: arc summary shows how prior lessons changed current guidance."""
        from jarvis.long_horizon import LongHorizonStore
        store = LongHorizonStore(root=tmp_path / "horizon")
        lessons = [
            ("2025-10", "Sleep is non-negotiable", "Started protecting sleep time"),
            ("2025-11", "Delegate more aggressively", "Moved three tasks to other owners"),
            ("2025-12", "Family time cannot be optimized away", "Protected Sunday as family day"),
        ]
        for month, lesson, change in lessons:
            r = store.create_review(
                actor="chris", cadence="monthly", period_label=month,
                period_start=f"{month}-01", period_end=f"{month}-30",
                key_lesson=lesson, what_changed_guidance=change,
            )
            store.complete_review(r.review_id, "chris")
        arc = store.get_arc_summary("chris", "monthly")
        assert arc["period_count"] == 3
        assert any("Sleep" in l for l in arc["key_lessons"])
        assert any("family" in g.lower() for g in arc["guidance_changes"])
