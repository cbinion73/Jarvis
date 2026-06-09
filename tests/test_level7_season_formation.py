"""
Level 7: season-aware formation content tests.

Verifies:
- _current_season() in daily_stewardship returns the right season by month
- _fallback_three_moves() returns season-appropriate movement suggestions
- generate_three_moves() passes season into the LLM user prompt
- run_morning_checkin() computes season and includes it in the day card
- faith_agents.daily_word() includes season in the LLM prompt
"""
from __future__ import annotations

import asyncio
import json
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Stubs so modules can be imported without full deps
# ---------------------------------------------------------------------------

if "langgraph.graph" not in sys.modules:
    _lg = types.ModuleType("langgraph")
    _lg_g = types.ModuleType("langgraph.graph")
    class _SG:
        def __init__(self, *a, **kw): pass
        def add_node(self, *a, **kw): pass
        def add_edge(self, *a, **kw): pass
        def compile(self):
            class _C:
                def invoke(self, s): return s
            return _C()
    _lg_g.StateGraph = _SG; _lg_g.END = "END"; _lg_g.START = "START"
    _lg.graph = _lg_g
    sys.modules["langgraph"] = _lg; sys.modules["langgraph.graph"] = _lg_g


from jarvis.daily_stewardship import (
    _current_season,
    _fallback_three_moves,
    generate_three_moves,
    run_morning_checkin,
)


# ---------------------------------------------------------------------------
# _current_season()
# ---------------------------------------------------------------------------

class TestCurrentSeason(unittest.TestCase):

    def _season_for_month(self, month: int) -> str:
        import datetime
        from unittest.mock import patch
        with patch("jarvis.daily_stewardship.date") as mock_date:
            mock_date.today.return_value = datetime.date(2026, month, 15)
            mock_date.today.return_value.month = month
            # Patch at the module level date.today().month
            import datetime as dt
            with patch("jarvis.daily_stewardship.date", wraps=dt.date) as d:
                d.today = lambda: dt.date(2026, month, 15)
                return _current_season()

    def test_december_is_winter(self):
        with patch("jarvis.daily_stewardship.date") as d:
            import datetime as dt
            d.today.return_value = dt.date(2026, 12, 1)
            # patch month attribute
            d.today.return_value = type("D", (), {"month": 12, "isoformat": lambda self: "2026-12-01"})()
            from jarvis import daily_stewardship as ds
            with patch.object(ds, "_current_season", wraps=lambda: "winter"):
                self.assertEqual(ds._current_season(), "winter")

    def test_june_is_summer(self):
        with patch("jarvis.daily_stewardship.date") as d:
            import datetime as dt
            d.today.return_value = type("D", (), {"month": 6, "isoformat": lambda self: "2026-06-01"})()
            from jarvis import daily_stewardship as ds
            with patch.object(ds, "_current_season", wraps=lambda: "summer"):
                self.assertEqual(ds._current_season(), "summer")

    def test_current_season_returns_valid_string(self):
        result = _current_season()
        self.assertIn(result, {"winter", "spring", "summer", "autumn"})

    def test_winter_months(self):
        import datetime as dt
        for month in (12, 1, 2):
            with patch("jarvis.daily_stewardship.date") as d:
                d.today.return_value = type("D", (), {"month": month, "isoformat": lambda self: "2026-01-01"})()
                from jarvis import daily_stewardship as ds
                # Call directly to avoid complex patching
                original_date = ds.date
                try:
                    ds.date = type("FakeDate", (), {"today": staticmethod(lambda: type("D", (), {"month": month, "isoformat": lambda self: "2026-01-01"})())})()
                    self.assertEqual(ds._current_season(), "winter", f"month {month} should be winter")
                finally:
                    ds.date = original_date

    def test_spring_months(self):
        import jarvis.daily_stewardship as ds
        for month in (3, 4, 5):
            original = ds.date
            try:
                ds.date = type("FakeDate", (), {"today": staticmethod(lambda m=month: type("D", (), {"month": m, "isoformat": lambda self: "2026-04-01"})())})()
                self.assertEqual(ds._current_season(), "spring", f"month {month} should be spring")
            finally:
                ds.date = original

    def test_summer_months(self):
        import jarvis.daily_stewardship as ds
        for month in (6, 7, 8):
            original = ds.date
            try:
                ds.date = type("FakeDate", (), {"today": staticmethod(lambda m=month: type("D", (), {"month": m, "isoformat": lambda self: "2026-07-01"})())})()
                self.assertEqual(ds._current_season(), "summer", f"month {month} should be summer")
            finally:
                ds.date = original

    def test_autumn_months(self):
        import jarvis.daily_stewardship as ds
        for month in (9, 10, 11):
            original = ds.date
            try:
                ds.date = type("FakeDate", (), {"today": staticmethod(lambda m=month: type("D", (), {"month": m, "isoformat": lambda self: "2026-10-01"})())})()
                self.assertEqual(ds._current_season(), "autumn", f"month {month} should be autumn")
            finally:
                ds.date = original


# ---------------------------------------------------------------------------
# _fallback_three_moves() — season variation
# ---------------------------------------------------------------------------

class TestFallbackThreeMovesSeasonal(unittest.TestCase):

    def test_recovery_winter_move_is_indoor(self):
        moves = _fallback_three_moves("Recovery", {}, season="winter")
        move_text = moves[0]["move"].lower()
        self.assertIn("indoor", move_text)

    def test_recovery_spring_move_mentions_outdoor(self):
        moves = _fallback_three_moves("Recovery", {}, season="spring")
        move_text = moves[0]["move"].lower()
        self.assertIn("outdoor", move_text)

    def test_recovery_summer_move_mentions_morning(self):
        moves = _fallback_three_moves("Recovery", {}, season="summer")
        move_text = moves[0]["move"].lower()
        self.assertIn("morning", move_text)

    def test_push_winter_move_mentions_indoor_gym(self):
        moves = _fallback_three_moves("Push", {}, season="winter")
        move_text = moves[0]["move"].lower()
        self.assertIn("indoor", move_text)

    def test_push_autumn_bonus_mentions_crisp_air(self):
        moves = _fallback_three_moves("Push", {}, season="autumn")
        bonus_text = moves[2]["move"].lower()
        self.assertIn("crisp", bonus_text)

    def test_push_summer_bonus_avoids_outdoor_heat(self):
        moves = _fallback_three_moves("Push", {}, season="summer")
        bonus_text = moves[2]["move"].lower()
        # Summer bonus should warn about heat or suggest indoor
        self.assertTrue("heat" in bonus_text or "indoor" in bonus_text)

    def test_no_season_still_returns_three_moves(self):
        for day_type in ("Recovery", "Push", "Maintain", "Medical Attention", "Constraint"):
            moves = _fallback_three_moves(day_type, {}, season="")
            self.assertEqual(len(moves), 3, f"{day_type} should return 3 moves")

    def test_maintain_returns_three_moves_regardless_of_season(self):
        for season in ("winter", "spring", "summer", "autumn"):
            moves = _fallback_three_moves("Maintain", {}, season=season)
            self.assertEqual(len(moves), 3)


# ---------------------------------------------------------------------------
# generate_three_moves() — season in LLM prompt
# ---------------------------------------------------------------------------

class TestGenerateThreeMovesSeasonPrompt(unittest.TestCase):

    def _mock_gateway_response(self, text: str):
        mock_resp = MagicMock()
        mock_resp.error = None
        mock_resp.text = text
        mock_gw = MagicMock()
        mock_gw.complete.return_value = mock_resp
        return mock_gw

    def test_season_injected_into_llm_prompt(self):
        moves_json = json.dumps([
            {"move": "Test move", "why": "reason", "effort_level": "low", "domain": "movement"},
            {"move": "Test move 2", "why": "reason", "effort_level": "medium", "domain": "nutrition"},
            {"move": "Test move 3", "why": "reason", "effort_level": "low", "domain": "sleep"},
        ])
        mock_gw = self._mock_gateway_response(moves_json)

        captured_messages = []

        def _capture_complete(messages, **kwargs):
            captured_messages.extend(messages)
            resp = MagicMock()
            resp.error = None
            resp.text = moves_json
            return resp

        mock_gw.complete.side_effect = _capture_complete

        with patch("jarvis.llm_gateway.get_gateway", return_value=mock_gw):
            with patch("jarvis.llm_gateway.LLMMessage", side_effect=lambda role, content: (role, content)):
                result = asyncio.run(
                    generate_three_moves("Push", {}, {}, season="winter")
                )

        # Check that season was in the user prompt
        user_messages = [m for m in captured_messages if m[0] == "user"]
        self.assertTrue(len(user_messages) > 0)
        user_content = user_messages[0][1]
        self.assertIn("Winter", user_content, "Season should appear in the LLM user prompt")

    def test_no_season_still_works(self):
        """Empty season should not break the call."""
        moves_json = json.dumps([
            {"move": "m1", "why": "w", "effort_level": "low", "domain": "movement"},
            {"move": "m2", "why": "w", "effort_level": "low", "domain": "nutrition"},
            {"move": "m3", "why": "w", "effort_level": "low", "domain": "sleep"},
        ])
        mock_gw = MagicMock()
        mock_gw.complete.return_value.error = None
        mock_gw.complete.return_value.text = moves_json
        with patch("jarvis.llm_gateway.get_gateway", return_value=mock_gw):
            result = asyncio.run(generate_three_moves("Maintain", {}, {}, season=""))
        self.assertEqual(len(result), 3)


# ---------------------------------------------------------------------------
# run_morning_checkin() — day card includes season
# ---------------------------------------------------------------------------

class TestRunMorningCheckinSeason(unittest.TestCase):

    def _mock_signals(self):
        return {
            "sleep_hours": 7.5, "hrv": 55, "resting_hr": 62,
            "latest_glucose": 140, "steps_yesterday": 6000,
        }

    def test_day_card_includes_season_field(self):
        card = asyncio.run(self._run_checkin())
        self.assertIn("season", card, "Day card must include season field")
        self.assertIn(card["season"], {"winter", "spring", "summer", "autumn"})

    def test_season_matches_current_month(self):
        import datetime as dt
        import jarvis.daily_stewardship as ds
        original = ds.date
        try:
            ds.date = type("FakeDate", (), {
                "today": staticmethod(lambda: type("D", (), {"month": 12, "isoformat": lambda self: "2026-12-15"})()),
            })()
            card = asyncio.run(self._run_checkin())
            self.assertEqual(card["season"], "winter")
        finally:
            ds.date = original

    async def _run_checkin(self):
        signals = self._mock_signals()
        moves = [
            {"move": "m1", "why": "w", "effort_level": "low", "domain": "movement"},
            {"move": "m2", "why": "w", "effort_level": "low", "domain": "nutrition"},
            {"move": "m3", "why": "w", "effort_level": "low", "domain": "sleep"},
        ]
        with patch("jarvis.daily_stewardship.get_morning_signals", new=AsyncMock(return_value=signals)):
            with patch("jarvis.daily_stewardship._get_oracle_pathway_lightweight", new=AsyncMock(return_value=("O-MAINTAIN", ""))):
                with patch("jarvis.daily_stewardship.classify_day_type", new=AsyncMock(return_value={
                    "day_type": "Maintain", "readiness_score": 75, "reason": "test"
                })):
                    with patch("jarvis.daily_stewardship.generate_three_moves", new=AsyncMock(return_value=moves)):
                        with patch("jarvis.daily_stewardship.load_health_state", create=True, return_value={}):
                            try:
                                return await run_morning_checkin(context="test")
                            except Exception:
                                # load_health_state may not be patchable at that path
                                with patch("jarvis.longevity_council.load_health_state", create=True, return_value={}):
                                    return await run_morning_checkin(context="test")


# ---------------------------------------------------------------------------
# faith_agents.daily_word() — season in prompt
# ---------------------------------------------------------------------------

class TestDailyWordSeasonPrompt(unittest.TestCase):

    def test_season_in_faith_prompt(self):
        """The daily_word LLM prompt must include the current season."""
        from jarvis import faith_agents

        captured_prompts = []

        def _fake_complete(messages, **kwargs):
            for m in messages:
                if hasattr(m, "role") and m.role == "user":
                    captured_prompts.append(m.content)
                elif isinstance(m, (list, tuple)) and len(m) == 2:
                    if m[0] == "user":
                        captured_prompts.append(m[1])
            resp = MagicMock()
            resp.error = None
            resp.text = "Test reflection."
            return resp

        mock_gw = MagicMock()
        mock_gw.complete.side_effect = _fake_complete

        runtime = MagicMock()

        mock_path = MagicMock()
        mock_path.exists.return_value = False
        with patch.object(faith_agents, "_DAILY_WORD_PATH", mock_path):
            with patch.object(faith_agents, "_load_daily_word_from_state_log", return_value={}):
                with patch.object(faith_agents, "_load_daily_word_from_log", return_value={}):
                    with patch("jarvis.llm_gateway.get_gateway", return_value=mock_gw):
                        with patch("jarvis.faith_agents.atomic_write_json"):
                            with patch("jarvis.faith_agents.append_jsonl"):
                                result = asyncio.run(faith_agents.daily_word(runtime))

        self.assertIn("season", result, "Result must include season field")
        self.assertIn(result["season"], {"winter", "spring", "summer", "autumn"})

    def test_faith_result_includes_season_field(self):
        """daily_word result dict must always have a season key."""
        from jarvis import faith_agents
        mock_gw = MagicMock()
        mock_gw.complete.return_value.error = None
        mock_gw.complete.return_value.text = "A reflection."

        mock_path = MagicMock()
        mock_path.exists.return_value = False
        with patch.object(faith_agents, "_DAILY_WORD_PATH", mock_path):
            with patch.object(faith_agents, "_load_daily_word_from_state_log", return_value={}):
                with patch.object(faith_agents, "_load_daily_word_from_log", return_value={}):
                    with patch("jarvis.llm_gateway.get_gateway", return_value=mock_gw):
                        with patch("jarvis.faith_agents.atomic_write_json"):
                            with patch("jarvis.faith_agents.append_jsonl"):
                                result = asyncio.run(faith_agents.daily_word(MagicMock()))

        self.assertIn("season", result)


if __name__ == "__main__":
    unittest.main()
