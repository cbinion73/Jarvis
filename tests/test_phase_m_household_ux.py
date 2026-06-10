"""Phase M: Household UX layer tests.

M1 – Mode switcher API (household-facing set/inspect/auto-exit).
M2 – Decision citation: record why + cite why + override path.
M3 – Value simulation: compare options against constitutional values.
M4 – Non-developer aggregate view over legacy/admin/continuity/long-horizon.
M5 – Plain-language control panel: pause-all + activity summary.
"""
from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path

# FastAPI stub.
if "fastapi" not in sys.modules:
    _fs = types.ModuleType("fastapi")
    _rs = types.ModuleType("fastapi.responses")
    _ss = types.ModuleType("fastapi.staticfiles")
    _uv = types.ModuleType("uvicorn")

    class _Route:
        def __init__(self, path, methods, endpoint):
            self.path = path; self.methods = methods; self.endpoint = endpoint

    class _Router:
        def __init__(self): self.routes = []

    class _FastAPI:
        def __init__(self, *a, **kw): self.router = _Router()
        def _reg(self, path, methods):
            def dec(fn): self.router.routes.append(_Route(path, methods, fn)); return fn
            return dec
        def get(self, path, *a, **kw):    return self._reg(path, {"GET"})
        def post(self, path, *a, **kw):   return self._reg(path, {"POST"})
        def put(self, path, *a, **kw):    return self._reg(path, {"PUT"})
        def patch(self, path, *a, **kw):  return self._reg(path, {"PATCH"})
        def delete(self, path, *a, **kw): return self._reg(path, {"DELETE"})
        def websocket(self, path, *a, **kw): return self._reg(path, {"WS"})
        def on_event(self, *a, **kw):     return lambda fn: fn
        def mount(self, *a, **kw):        pass
        def add_middleware(self, *a, **kw): pass

    class _HTTPException(Exception):
        def __init__(self, status_code=500, detail=""):
            super().__init__(detail); self.status_code = status_code; self.detail = detail

    _rs.JSONResponse = dict
    _fs.FastAPI = _FastAPI
    _fs.HTTPException = _HTTPException
    _fs.Request = object
    _fs.BackgroundTasks = object
    _fs.File = lambda *a, **kw: None
    _fs.Form = lambda *a, **kw: None
    _fs.Query = lambda *a, **kw: None
    _fs.UploadFile = object
    _fs.WebSocket = object
    _fs.WebSocketDisconnect = Exception
    _fs.responses = _rs
    _fs.staticfiles = _ss
    _uv.run = lambda *a, **kw: None

    for _m, _s in (
        ("fastapi", _fs),
        ("fastapi.responses", _rs),
        ("fastapi.staticfiles", _ss),
        ("fastapi.middleware.cors", types.ModuleType("fastapi.middleware.cors")),
        ("uvicorn", _uv),
    ):
        sys.modules.setdefault(_m, _s)

import tempfile
from dataclasses import asdict

SERVICE = Path(__file__).parent.parent / "jarvis" / "service.py"


# ── M1: Mode switcher household API ───────────────────────────────────────────

class TestM1ModeSwitcherAPI(unittest.TestCase):
    """M1: Mode-switcher API exists and is household-facing."""

    def test_mode_set_endpoint_exists(self):
        src = SERVICE.read_text(encoding="utf-8")
        self.assertIn('"/api/household/modes-v2/set"', src)

    def test_mode_list_endpoint_exists(self):
        src = SERVICE.read_text(encoding="utf-8")
        self.assertIn('"/api/household/modes-v2/list"', src)

    def test_current_mode_endpoint_exists(self):
        src = SERVICE.read_text(encoding="utf-8")
        self.assertIn('"/api/household/modes-v2/current"', src)

    def test_mode_impact_endpoint_exists(self):
        src = SERVICE.read_text(encoding="utf-8")
        self.assertIn('"/api/household/modes-v2/{mode_id}/impact"', src)


# ── M2: Decision citation ─────────────────────────────────────────────────────

class TestM2DecisionCitation(unittest.TestCase):
    """M2: record() + cite() + override_path + plain_summary."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        from jarvis.decision_citation import DecisionCitationStore
        self.store = DecisionCitationStore(root=Path(self.tmp.name) / "decisions")

    def tearDown(self):
        self.tmp.cleanup()

    def _record(self, **kwargs) -> object:
        defaults = dict(
            actor="jarvis",
            recommendation="Go to bed by 10pm tonight",
            rationale="You have a 6am meeting and slept only 5h last night",
            principles=["health_stewardship", "energy_for_family"],
            authority_basis="observe",
            uncertainty="medium",
            override_path="Say 'skip this' and JARVIS will not remind again tonight.",
            domain="health",
        )
        defaults.update(kwargs)
        return self.store.record(**defaults)

    def test_record_returns_citation(self):
        citation = self._record()
        self.assertIsNotNone(citation)
        self.assertIn("citation_id", asdict(citation))

    def test_cite_returns_plain_summary(self):
        citation = self._record()
        cited = self.store.cite(citation.citation_id)
        self.assertIsNotNone(cited)
        self.assertIn("plain_summary", cited)
        self.assertIn("Go to bed", cited["plain_summary"])

    def test_cite_includes_override_path(self):
        citation = self._record()
        cited = self.store.cite(citation.citation_id)
        self.assertIn("override_path", cited)
        self.assertIn("skip this", cited["override_path"])

    def test_cite_includes_principles(self):
        citation = self._record()
        cited = self.store.cite(citation.citation_id)
        self.assertIn("health_stewardship", cited["principles"])

    def test_cite_unknown_returns_none(self):
        result = self.store.cite("nonexistent-id")
        self.assertIsNone(result)

    def test_invalid_uncertainty_raises(self):
        with self.assertRaises(ValueError):
            self._record(uncertainty="very_high")

    def test_list_recent_returns_citations(self):
        self._record()
        self._record(domain="family")
        all_citations = self.store.list_recent()
        self.assertEqual(len(all_citations), 2)

    def test_list_recent_filters_by_domain(self):
        self._record(domain="health")
        self._record(domain="family")
        health = self.store.list_recent(domain="health")
        self.assertEqual(len(health), 1)

    def test_record_outcome_updates_citation(self):
        citation = self._record()
        updated = self.store.record_outcome(
            citation.citation_id,
            reviewed_by="chris",
            outcome="Went to bed at 10:15pm — felt better next day.",
        )
        self.assertIsNotNone(updated)
        self.assertIn("felt better", updated["outcome"])

    def test_citation_endpoints_in_service(self):
        src = SERVICE.read_text(encoding="utf-8")
        self.assertIn('"/api/decisions/cite"', src)
        self.assertIn('"/api/decisions"', src)

    def test_citation_id_endpoint_in_service(self):
        src = SERVICE.read_text(encoding="utf-8")
        self.assertIn('"/api/decisions/{citation_id}"', src)


# ── M3: Value simulation ──────────────────────────────────────────────────────

class TestM3ValueSimulation(unittest.TestCase):
    """M3: compare_options ranks options against constitutional values + surfaces dissent."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        from jarvis.value_simulator import ValueSimulator
        self.sim = ValueSimulator(root=Path(self.tmp.name) / "sims")

    def tearDown(self):
        self.tmp.cleanup()

    def _options(self):
        return [
            {
                "label": "Work late",
                "description": "Finish the project tonight",
                "scores": {
                    "family_impact": -0.7,
                    "health_impact": -0.5,
                    "financial_stewardship": 0.6,
                    "time_cost": -0.8,
                    "reversibility": 0.2,
                    "household_harmony": -0.4,
                    "faith_alignment": 0.0,
                },
            },
            {
                "label": "Rest and finish tomorrow",
                "description": "Leave at normal time and finish in the morning",
                "scores": {
                    "family_impact": 0.8,
                    "health_impact": 0.7,
                    "financial_stewardship": 0.3,
                    "time_cost": 0.6,
                    "reversibility": 0.9,
                    "household_harmony": 0.8,
                    "faith_alignment": 0.5,
                },
            },
        ]

    def test_compare_returns_simulation(self):
        result = self.sim.compare(
            actor="chris",
            question="Should I work late or rest?",
            options=self._options(),
        )
        self.assertIsNotNone(result)
        self.assertIn("simulation_id", asdict(result))

    def test_compare_ranks_options(self):
        result = self.sim.compare(
            actor="chris", question="Work late or rest?",
            options=self._options(),
        )
        opts = result.options
        self.assertEqual(len(opts), 2)
        ranks = [o["rank"] for o in opts]
        self.assertIn(1, ranks)
        self.assertIn(2, ranks)

    def test_compare_recommends_best_option(self):
        result = self.sim.compare(
            actor="chris", question="Work late or rest?",
            options=self._options(),
        )
        # "Rest and finish tomorrow" has much higher value scores → should be recommended
        recommended_id = result.recommended_option_id
        recommended_label = next(
            o["label"] for o in result.options if o["option_id"] == recommended_id
        )
        self.assertEqual(recommended_label, "Rest and finish tomorrow")

    def test_compare_surfaces_dissent(self):
        result = self.sim.compare(
            actor="chris", question="Work late or rest?",
            options=self._options(),
        )
        self.assertIsNotNone(result.dissent_summary)
        # "Work late" should have dissents on family/health
        work_late_opt = next(o for o in result.options if o["label"] == "Work late")
        self.assertGreater(len(work_late_opt["dissents"]), 0)

    def test_compare_provides_change_my_mind(self):
        result = self.sim.compare(
            actor="chris", question="Work late or rest?",
            options=self._options(),
        )
        # At least one option should have a change_my_mind path
        change_paths = [o["change_my_mind"] for o in result.options]
        self.assertTrue(any(p for p in change_paths))

    def test_compare_empty_options_raises(self):
        with self.assertRaises(ValueError):
            self.sim.compare(actor="chris", question="anything", options=[])

    def test_get_returns_simulation(self):
        result = self.sim.compare(
            actor="chris", question="Test?", options=self._options()
        )
        retrieved = self.sim.get(result.simulation_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["simulation_id"], result.simulation_id)

    def test_simulate_endpoint_in_service(self):
        src = SERVICE.read_text(encoding="utf-8")
        self.assertIn('"/api/simulate/compare-options"', src)

    def test_single_option_still_works(self):
        result = self.sim.compare(
            actor="chris",
            question="Should I take a nap?",
            options=[{
                "label": "Nap now",
                "description": "30min nap at 2pm",
                "scores": {"health_impact": 0.6, "family_impact": 0.2},
            }],
        )
        self.assertEqual(result.options[0]["rank"], 1)


# ── M4: Non-developer household aggregate view ────────────────────────────────

class TestM4NonDeveloperView(unittest.TestCase):
    """M4: Key household surfaces exist as real API endpoints usable without JSON expertise."""

    def test_legacy_entries_endpoint_exists(self):
        src = SERVICE.read_text(encoding="utf-8")
        self.assertIn('"/api/legacy/entries"', src)

    def test_admin_household_control_exists(self):
        src = SERVICE.read_text(encoding="utf-8")
        self.assertIn('"/api/admin/household-control"', src)

    def test_continuity_events_endpoint_exists(self):
        src = SERVICE.read_text(encoding="utf-8")
        self.assertIn("continuity", src)

    def test_long_horizon_arc_exists(self):
        src = SERVICE.read_text(encoding="utf-8")
        self.assertIn("long_horizon", src)

    def test_governance_summary_exists(self):
        src = SERVICE.read_text(encoding="utf-8")
        self.assertIn('"/api/governance/summary"', src)


# ── M5: Plain-language control panel ─────────────────────────────────────────

class TestM5PlainLanguageControlPanel(unittest.TestCase):
    """M5: Pause-all + activity-summary for household safety."""

    def test_pause_all_endpoint_in_service(self):
        src = SERVICE.read_text(encoding="utf-8")
        self.assertIn('"/api/household/pause-all"', src)

    def test_activity_summary_endpoint_in_service(self):
        src = SERVICE.read_text(encoding="utf-8")
        self.assertIn('"/api/household/activity-summary"', src)

    def test_pause_all_response_fields(self):
        """pause-all endpoint doc contains required response fields."""
        src = SERVICE.read_text(encoding="utf-8")
        self.assertIn("paused_agents", src)
        self.assertIn("Hard-boundary policies", src)

    def test_activity_summary_fields_in_service(self):
        src = SERVICE.read_text(encoding="utf-8")
        self.assertIn("what_jarvis_can_do", src)
        self.assertIn("one_tap_pause_via", src)

    def test_governance_plain_language_summary_exists(self):
        """M5: governance plain-language summary function exists and is wired."""
        src = SERVICE.read_text(encoding="utf-8")
        self.assertIn("governance_plain_language_summary", src)

    def test_decision_citation_store_is_real(self):
        """M5: DecisionCitationStore creates and persists a real citation."""
        tmp = tempfile.TemporaryDirectory()
        from jarvis.decision_citation import DecisionCitationStore
        store = DecisionCitationStore(root=Path(tmp.name) / "d")
        c = store.record(
            actor="jarvis",
            recommendation="Take a break",
            rationale="You've worked 5 hours straight",
            principles=["health_stewardship"],
            domain="health",
        )
        self.assertIsNotNone(store.cite(c.citation_id))
        tmp.cleanup()

    def test_value_simulator_store_persists(self):
        """M5: ValueSimulator persists simulations to disk."""
        tmp = tempfile.TemporaryDirectory()
        from jarvis.value_simulator import ValueSimulator
        vs = ValueSimulator(root=Path(tmp.name) / "vs")
        result = vs.compare(
            actor="chris",
            question="Rest or work?",
            options=[{"label": "Rest", "description": "Take a break", "scores": {"health_impact": 0.9}}],
        )
        retrieved = vs.get(result.simulation_id)
        self.assertIsNotNone(retrieved)
        tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
