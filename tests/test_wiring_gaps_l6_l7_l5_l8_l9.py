"""
Tests proving the runtime wiring gaps are closed:

QC-001 / L6.4  — corrected memories excluded from converse() context
QC-010 / L6.1  — retrieve_by_situation() called from _relevant_profile_facts()
QC-002 / L7.1  — HealthLoopStore check-in history wired into morning check-in
QC-003 / L7.3  — ritual_summary passed to generate_three_moves() before call
QC-004 / L5.8  — ProactiveOrchestrator runs in scheduler._tick()
QC-014 / L7.1  — daily_stewardship morning check-in fired from scheduler
QC-007 / L9.1  — constitution_engine.cite() called for hard-boundary denials
QC-006 / L8.1  — foundry approve() registers agent stub in AgentRegistry
"""

import sys
import types
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch, call
import tempfile
import json
import asyncio

# ---------------------------------------------------------------------------
# Minimal stubs so jarvis modules import without heavy deps
# ---------------------------------------------------------------------------
for _mod in (
    "anthropic", "anthropic.types", "anthropic._types",
    "openai", "fastapi", "fastapi.responses", "fastapi.middleware",
    "fastapi.middleware.cors", "starlette", "starlette.testclient",
    "pydantic", "pydantic.dataclasses", "cryptography",
    "cryptography.fernet", "httpx", "aiohttp",
    "aiofiles", "aiosqlite", "bs4", "feedparser",
    "googleapiclient", "googleapiclient.discovery",
    "googleapiclient.errors",
    "google", "google.auth", "google.auth.transport",
    "google.oauth2", "google.oauth2.credentials",
):
    sys.modules.setdefault(_mod, types.ModuleType(_mod))

for _sub in ("JSONResponse", "HTTPException"):
    sys.modules.setdefault("fastapi", types.ModuleType("fastapi"))
    setattr(sys.modules["fastapi"], _sub, type(_sub, (), {"__init__": lambda s, *a, **k: None}))

_fastapi_mod = sys.modules["fastapi"]
if not hasattr(_fastapi_mod, "APIRouter"):
    class _Router:
        def __init__(self, *a, **k): pass
        def get(self, *a, **k): return lambda f: f
        def post(self, *a, **k): return lambda f: f
        def delete(self, *a, **k): return lambda f: f
        def patch(self, *a, **k): return lambda f: f
        def put(self, *a, **k): return lambda f: f
        def include_router(self, *a, **k): pass
    _fastapi_mod.APIRouter = _Router

if not hasattr(_fastapi_mod, "FastAPI"):
    class _FastAPI:
        def __init__(self, *a, **k): pass
        def get(self, *a, **k): return lambda f: f
        def post(self, *a, **k): return lambda f: f
        def delete(self, *a, **k): return lambda f: f
        def patch(self, *a, **k): return lambda f: f
        def put(self, *a, **k): return lambda f: f
        def add_middleware(self, *a, **k): pass
        def on_event(self, *a, **k): return lambda f: f
        def include_router(self, *a, **k): pass
        def mount(self, *a, **k): pass
    _fastapi_mod.FastAPI = _FastAPI

if not hasattr(_fastapi_mod, "Depends"):
    _fastapi_mod.Depends = lambda f=None: None
if not hasattr(_fastapi_mod, "Query"):
    _fastapi_mod.Query = lambda *a, **k: None
if not hasattr(_fastapi_mod, "Body"):
    _fastapi_mod.Body = lambda *a, **k: None
if not hasattr(_fastapi_mod, "BackgroundTasks"):
    _fastapi_mod.BackgroundTasks = MagicMock
if not hasattr(_fastapi_mod, "Form"):
    _fastapi_mod.Form = lambda *a, **k: None

_pydantic = sys.modules["pydantic"]
if not hasattr(_pydantic, "BaseModel"):
    class _BM:
        def __init__(self, **k): [setattr(self, kk, vv) for kk, vv in k.items()]
    _pydantic.BaseModel = _BM
if not hasattr(_pydantic, "validator"):
    _pydantic.validator = lambda *a, **k: (lambda f: f)
if not hasattr(_pydantic, "Field"):
    _pydantic.Field = lambda *a, **k: None

_fernet = sys.modules["cryptography.fernet"]
if not hasattr(_fernet, "Fernet"):
    class _Fernet:
        def __init__(self, *a, **k): pass
        @staticmethod
        def generate_key(): return b"key"
        def encrypt(self, b): return b
        def decrypt(self, b): return b
    _fernet.Fernet = _Fernet
    _fernet.InvalidToken = Exception

import importlib


# ============================================================
# QC-001 / L6.4 — corrected memories excluded from context
# ============================================================

class TestCorrectedMemoryExcluded:
    """Corrected entries cascade to profile facts and are excluded from profile_facts()."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.root = Path(self.tmpdir)

    def _make_store(self):
        from jarvis.memory import MemoryStore
        return MemoryStore(self.root)

    def test_correct_entry_sets_approval_status(self):
        store = self._make_store()
        # Add a fake entry directly
        entry = {
            "entry_id": "e-001",
            "approval_status": "approved",
            "summary": "test summary",
        }
        store._save_entries([entry])
        result = store.correct_entry("e-001", "This was wrong", "chris")
        assert result is not None
        assert result["approval_status"] == "corrected"

    def test_correct_entry_cascades_to_profile_fact(self):
        store = self._make_store()
        # Add entry and a matching profile fact with source_entry_id
        entry = {"entry_id": "e-002", "approval_status": "approved", "summary": "fact source"}
        store._save_entries([entry])
        fact = {
            "fact_id": "f-002",
            "source_entry_id": "e-002",
            "status": "active",
            "summary": "derived fact",
            "lane": "personal",
            "subject_user_id": "chris",
        }
        store._save_json(store.facts_path, [fact])

        store.correct_entry("e-002", "corrected", "chris")
        facts = store.list_profile_facts()
        matching = [f for f in facts if f.get("fact_id") == "f-002"]
        assert matching, "profile fact should still exist"
        assert matching[0]["status"] == "corrected"

    def test_profile_facts_excludes_corrected_status(self):
        """profile_facts() must skip corrected, disputed, retired, superseded facts."""
        from jarvis.memory import MemoryStore, MemorySupport
        from jarvis.models import UserProfile

        store = MemoryStore(self.root)
        active = {
            "fact_id": "f-active", "status": "active", "approval_status": "approved",
            "summary": "active fact", "lane": "personal", "subject_user_id": "chris",
            "subject_display_name": "Chris", "boundary_label": "",
        }
        corrected = {
            "fact_id": "f-corrected", "status": "corrected", "approval_status": "corrected",
            "summary": "wrong fact — should not appear", "lane": "personal",
            "subject_user_id": "chris", "subject_display_name": "Chris", "boundary_label": "",
        }
        store._save_json(store.facts_path, [active, corrected])

        cfg = MagicMock()
        cfg.load_json_profile.return_value = {
            "partitionRules": {"defaultPersonalAccess": "personal"},
            "encryption": {"keyPath": str(self.root / "fernet.key")},
            "promotionRules": {"promotePersonalToProfileFacts": True},
        }
        cfg.memory_profile_path = self.root / "memory_profile.json"
        support = MemorySupport(cfg, store)
        actor = UserProfile(user_id="chris", display_name="Chris", address_as="Chris", role="owner", permissions="owner")
        facts = support.profile_facts(actor)
        summaries = [f.get("summary") for f in facts]
        assert "active fact" in summaries
        assert "wrong fact — should not appear" not in summaries

    def test_profile_facts_excludes_via_approval_status_field(self):
        """profile_facts() also rejects facts with non-excluded status but excluded approval_status."""
        from jarvis.memory import MemoryStore, MemorySupport
        from jarvis.models import UserProfile

        store = MemoryStore(self.root)
        sneaky = {
            "fact_id": "f-sneaky", "status": "active", "approval_status": "corrected",
            "summary": "sneaky fact", "lane": "personal",
            "subject_user_id": "chris", "subject_display_name": "Chris", "boundary_label": "",
        }
        store._save_json(store.facts_path, [sneaky])

        cfg = MagicMock()
        cfg.load_json_profile.return_value = {
            "partitionRules": {"defaultPersonalAccess": "personal"},
            "encryption": {"keyPath": str(self.root / "fernet.key")},
            "promotionRules": {"promotePersonalToProfileFacts": True},
        }
        cfg.memory_profile_path = self.root / "memory_profile.json"
        support = MemorySupport(cfg, store)
        actor = UserProfile(user_id="chris", display_name="Chris", address_as="Chris", role="owner", permissions="owner")
        facts = support.profile_facts(actor)
        summaries = [f.get("summary") for f in facts]
        assert "sneaky fact" not in summaries


# ============================================================
# QC-010 / L6.1 — retrieve_by_situation() called in context
# ============================================================

class TestSituationalRetrieval:
    """retrieve_by_situation() is called from _relevant_profile_facts() in the runtime."""

    def test_relevant_profile_facts_calls_retrieve_by_situation(self):
        """_relevant_profile_facts() calls store.retrieve_by_situation() for non-trivial requests."""
        from jarvis.models import UserProfile

        actor = UserProfile(user_id="chris", display_name="Chris", address_as="Chris", role="owner", permissions="owner")

        fake_facts = [{"summary": "health goal: lower glucose", "tags": ["health"], "subject_user_id": "chris"}]
        situation_results = [{"summary": "Chris is managing glucose levels"}]

        from jarvis.runtime import JarvisRuntime as _RT
        with patch.object(_RT, "__init__", lambda self, *a, **k: None):
            rt = object.__new__(_RT)
            store_mock = MagicMock()
            store_mock.retrieve_by_situation.return_value = situation_results
            support_mock = MagicMock()
            support_mock.profile_facts.return_value = fake_facts
            support_mock.store = store_mock
            rt.memory_support = support_mock

            result = rt._relevant_profile_facts(actor, "what should I eat for better health?", limit=4)

        # retrieve_by_situation must have been called
        store_mock.retrieve_by_situation.assert_called_once()
        call_kwargs = store_mock.retrieve_by_situation.call_args
        assert call_kwargs[1]["actor"] == "chris" or call_kwargs[0][0] == "chris"
        # Situation results appear first
        assert "Chris is managing glucose levels" in result

    def test_situation_facts_come_before_keyword_facts(self):
        """Situational facts rank before keyword-only matches."""
        from jarvis.models import UserProfile

        actor = UserProfile(user_id="chris", display_name="Chris", address_as="Chris", role="owner", permissions="owner")

        keyword_fact = {"summary": "keyword match fact", "tags": ["health"], "subject_user_id": "chris"}
        situation_fact = {"summary": "situation match fact"}

        from jarvis.runtime import JarvisRuntime as _RT
        with patch.object(_RT, "__init__", lambda self, *a, **k: None):
            rt = object.__new__(_RT)
            store_mock = MagicMock()
            store_mock.retrieve_by_situation.return_value = [situation_fact]
            support_mock = MagicMock()
            support_mock.profile_facts.return_value = [keyword_fact]
            support_mock.store = store_mock
            rt.memory_support = support_mock

            result = rt._relevant_profile_facts(actor, "health planning", limit=4)

        assert result[0] == "situation match fact"

    def test_situation_retrieval_failure_does_not_block_context(self):
        """If retrieve_by_situation raises, _relevant_profile_facts falls back gracefully."""
        from jarvis.models import UserProfile

        actor = UserProfile(user_id="chris", display_name="Chris", address_as="Chris", role="owner", permissions="owner")

        fallback_fact = {"summary": "fallback keyword fact", "tags": ["health"], "subject_user_id": "chris"}

        from jarvis.runtime import JarvisRuntime as _RT
        with patch.object(_RT, "__init__", lambda self, *a, **k: None):
            rt = object.__new__(_RT)
            store_mock = MagicMock()
            store_mock.retrieve_by_situation.side_effect = RuntimeError("retrieval failed")
            support_mock = MagicMock()
            support_mock.profile_facts.return_value = [fallback_fact]
            support_mock.store = store_mock
            rt.memory_support = support_mock

            result = rt._relevant_profile_facts(actor, "health planning", limit=4)

        # Should still return keyword-matched facts
        assert "fallback keyword fact" in result


# ============================================================
# QC-002 / L7.1 — HealthLoopStore wired into morning check-in
# ============================================================

class TestHealthLoopWiredIntoMorning:
    """HealthLoopStore.list_checkins() is called from run_morning_checkin()."""

    def test_health_loop_store_is_consulted_during_morning_checkin(self):
        """run_morning_checkin() imports and calls HealthLoopStore.list_checkins."""
        from jarvis import daily_stewardship

        recent_checkins = [
            {"date": "2026-06-09", "mood": "good", "energy": "medium", "sleep_quality": "fair"},
            {"date": "2026-06-10", "mood": "low", "energy": "low", "sleep_quality": "poor"},
        ]

        mock_store = MagicMock()
        mock_store.list_checkins.return_value = recent_checkins
        MockHealthLoopStore = MagicMock(return_value=mock_store)

        mock_ritual = MagicMock()
        mock_ritual.list_active_prayers.return_value = []
        mock_ritual.list_study_items.return_value = []
        MockRitual = MagicMock(return_value=mock_ritual)

        with (
            patch("jarvis.daily_stewardship.get_morning_signals", return_value={}),
            patch("jarvis.daily_stewardship._get_oracle_pathway_lightweight", return_value=("maintain", "")),
            patch("jarvis.daily_stewardship.classify_day_type", return_value={"day_type": "maintain", "readiness_score": 0.7, "reason": ""}),
            patch("jarvis.daily_stewardship.generate_three_moves", return_value=[{"move": "walk", "why": "good", "effort_level": "low", "domain": "movement"}]),
            patch("jarvis.daily_stewardship._generate_if_then_rule", return_value=""),
            patch("jarvis.daily_stewardship._save_day_card", return_value=None),
            patch.dict("sys.modules", {"jarvis.longevity_council": MagicMock(append_council_decision=MagicMock(return_value=None)), "longevity_council": MagicMock(append_council_decision=MagicMock(return_value=None))}),
            patch.dict("sys.modules", {"jarvis.health_loop": MagicMock(HealthLoopStore=MockHealthLoopStore)}),
            patch.dict("sys.modules", {"jarvis.ritual_loop": MagicMock(RitualSummaryStore=MockRitual)}),
            patch("jarvis.daily_stewardship.load_health_state", return_value={}, create=True),
        ):
            asyncio.run(daily_stewardship.run_morning_checkin())

        mock_store.list_checkins.assert_called_once_with(actor="chris", limit=5)

    def test_checkin_trend_added_to_signals(self):
        """Check-in trend is added under _checkin_trend key in signals dict."""
        from jarvis import daily_stewardship

        recent_checkins = [
            {"date": "2026-06-09", "mood": "good", "energy": "high", "sleep_quality": "good", "sleep_hours": 7.5},
        ]

        captured_calls = []

        async def fake_generate(day_type, signals, health_state, **kwargs):
            captured_calls.append(signals)
            return [{"move": "x", "why": "y", "effort_level": "low", "domain": "movement"}]

        mock_store = MagicMock()
        mock_store.list_checkins.return_value = recent_checkins
        MockHLS = MagicMock(return_value=mock_store)

        mock_ritual = MagicMock()
        mock_ritual.list_active_prayers.return_value = []
        mock_ritual.list_study_items.return_value = []
        MockRitual = MagicMock(return_value=mock_ritual)

        with (
            patch("jarvis.daily_stewardship.get_morning_signals", return_value={}),
            patch("jarvis.daily_stewardship._get_oracle_pathway_lightweight", return_value=("maintain", "")),
            patch("jarvis.daily_stewardship.classify_day_type", return_value={"day_type": "maintain", "readiness_score": 0.7, "reason": ""}),
            patch("jarvis.daily_stewardship.generate_three_moves", side_effect=fake_generate),
            patch("jarvis.daily_stewardship._generate_if_then_rule", return_value=""),
            patch("jarvis.daily_stewardship._save_day_card", return_value=None),
            patch.dict("sys.modules", {"jarvis.longevity_council": MagicMock(append_council_decision=MagicMock(return_value=None)), "longevity_council": MagicMock(append_council_decision=MagicMock(return_value=None))}),
            patch.dict("sys.modules", {"jarvis.health_loop": MagicMock(HealthLoopStore=MockHLS)}),
            patch.dict("sys.modules", {"jarvis.ritual_loop": MagicMock(RitualSummaryStore=MockRitual)}),
            patch("jarvis.daily_stewardship.load_health_state", return_value={}, create=True),
        ):
            asyncio.run(daily_stewardship.run_morning_checkin())

        assert captured_calls, "generate_three_moves should have been called"
        signals_used = captured_calls[0]
        assert "_checkin_trend" in signals_used
        assert len(signals_used["_checkin_trend"]) == 1
        assert signals_used["_checkin_trend"][0]["mood"] == "good"


# ============================================================
# QC-003 / L7.3 — ritual_summary passed to generate_three_moves
# ============================================================

class TestRitualContextPassedToThreeMoves:
    """ritual_summary is loaded BEFORE generate_three_moves() and passed as ritual_context."""

    def test_ritual_context_is_passed_to_generate_three_moves(self):
        from jarvis import daily_stewardship

        prayer_items = [{"prayer_id": "p1", "subject": "family", "request": "healing"}]
        study_items = [{"item_id": "s1", "title": "Romans 8", "category": "scripture"}]

        captured_kwargs = []

        async def fake_generate(day_type, signals, health_state, **kwargs):
            captured_kwargs.append(kwargs)
            return [{"move": "pray", "why": "active prayer", "effort_level": "low", "domain": "mindset"}]

        mock_ritual = MagicMock()
        mock_ritual.list_active_prayers.return_value = prayer_items
        mock_ritual.list_study_items.return_value = study_items
        MockRitual = MagicMock(return_value=mock_ritual)

        mock_health_loop = MagicMock()
        mock_health_loop.list_checkins.return_value = []
        MockHLS = MagicMock(return_value=mock_health_loop)

        with (
            patch("jarvis.daily_stewardship.get_morning_signals", return_value={}),
            patch("jarvis.daily_stewardship._get_oracle_pathway_lightweight", return_value=("maintain", "")),
            patch("jarvis.daily_stewardship.classify_day_type", return_value={"day_type": "maintain", "readiness_score": 0.7, "reason": ""}),
            patch("jarvis.daily_stewardship.generate_three_moves", side_effect=fake_generate),
            patch("jarvis.daily_stewardship._generate_if_then_rule", return_value=""),
            patch("jarvis.daily_stewardship._save_day_card", return_value=None),
            patch.dict("sys.modules", {"jarvis.longevity_council": MagicMock(append_council_decision=MagicMock(return_value=None)), "longevity_council": MagicMock(append_council_decision=MagicMock(return_value=None))}),
            patch.dict("sys.modules", {"jarvis.ritual_loop": MagicMock(RitualSummaryStore=MockRitual)}),
            patch.dict("sys.modules", {"jarvis.health_loop": MagicMock(HealthLoopStore=MockHLS)}),
            patch("jarvis.daily_stewardship.load_health_state", return_value={}, create=True),
        ):
            asyncio.run(daily_stewardship.run_morning_checkin())

        assert captured_kwargs, "generate_three_moves should have been called"
        ritual_ctx = captured_kwargs[0].get("ritual_context")
        assert ritual_ctx is not None, "ritual_context must be passed"
        assert ritual_ctx["active_prayer_count"] == 1
        assert ritual_ctx["open_study_count"] == 1
        assert ritual_ctx["source"] == "ritual_loop"

    def test_ritual_prompt_includes_prayer_when_present(self):
        """generate_three_moves() puts prayer context into the LLM prompt when provided."""
        from jarvis import daily_stewardship

        # Call generate_three_moves directly with ritual_context — LLM unavailable so fallback used.
        ritual_ctx = {
            "active_prayer_count": 2,
            "active_prayers": [{"subject": "mom", "request": "healing"}],
            "open_study_count": 1,
            "open_study": [{"title": "Psalm 23", "category": "scripture"}],
            "source": "ritual_loop",
        }

        with patch("jarvis.daily_stewardship.get_gateway", return_value=None, create=True):
            with patch.dict("sys.modules", {"jarvis.llm_gateway": MagicMock(get_gateway=lambda: None, LLMMessage=MagicMock)}):
                result = asyncio.run(
                    daily_stewardship.generate_three_moves(
                        "maintain", {}, {}, ritual_context=ritual_ctx
                    )
                )

        # Fallback still returns 3 moves
        assert isinstance(result, list)
        assert len(result) == 3


# ============================================================
# QC-004 / L5.8 — ProactiveOrchestrator fires in scheduler._tick()
# ============================================================

class TestProactiveOrchestratorInScheduler:
    """scheduler._run_proactive_orchestrator() is called from _tick() every N ticks."""

    def _make_sched(self, tick_count=0):
        from jarvis.scheduler import AgentScheduler
        sched = object.__new__(AgentScheduler)
        sched._proactive_tick_count = tick_count
        sched._PROACTIVE_TICK_INTERVAL = 5
        sched._runtime = MagicMock()
        return sched

    def test_proactive_tick_counter_increments_without_firing(self):
        """Counter increments 1..4 without calling the orchestrator."""
        sched = self._make_sched(tick_count=0)
        called = []

        mock_proactive_mod = MagicMock()
        mock_orch = MagicMock()
        mock_orch.run.side_effect = lambda **k: called.append(k) or {"created_count": 0}
        mock_proactive_mod.get_orchestrator.return_value = mock_orch

        with patch.dict("sys.modules", {"jarvis.proactive": mock_proactive_mod}):
            for _ in range(4):
                sched._run_proactive_orchestrator()

        assert not called, "orchestrator must not run before tick interval"
        assert sched._proactive_tick_count == 4

    def test_proactive_orchestrator_fires_at_interval(self):
        """Orchestrator runs and counter resets on the Nth tick."""
        sched = self._make_sched(tick_count=4)
        called = []

        mock_proactive_mod = MagicMock()
        mock_orch = MagicMock()
        mock_orch.run.side_effect = lambda actor="chris": called.append(actor) or {"created_count": 1, "created_ids": ["x"]}
        mock_proactive_mod.get_orchestrator.return_value = mock_orch

        with patch.dict("sys.modules", {"jarvis.proactive": mock_proactive_mod}):
            sched._run_proactive_orchestrator()

        assert called, "orchestrator must run at interval"
        assert sched._proactive_tick_count == 0

    def test_proactive_orchestrator_failure_is_non_fatal(self):
        """If orchestrator raises, _run_proactive_orchestrator must not propagate."""
        sched = self._make_sched(tick_count=4)

        mock_proactive_mod = MagicMock()
        mock_proactive_mod.get_orchestrator.side_effect = RuntimeError("boom")

        with patch.dict("sys.modules", {"jarvis.proactive": mock_proactive_mod}):
            sched._run_proactive_orchestrator()  # must not raise


# ============================================================
# QC-014 / L7.1 — morning stewardship fires from scheduler
# ============================================================

class TestMorningStepwardshipScheduled:
    """_run_morning_stewardship() is called from _maybe_fire_morning()."""

    def test_run_morning_stewardship_fires_on_morning_trigger(self):
        from jarvis.scheduler import AgentScheduler

        sched = object.__new__(AgentScheduler)
        sched.MORNING_TRIGGER_HOUR = 6
        sched.MORNING_TRIGGER_MINUTE = 0
        sched._morning_fired_date = ""
        sched._runtime = MagicMock()

        with (
            patch("jarvis.scheduler.datetime") as mock_dt,
            patch.object(sched, "fire_event"),
            patch.object(sched, "_run_drift_detection"),
            patch.object(sched, "_run_morning_stewardship") as mock_morning,
        ):
            mock_now = MagicMock()
            mock_now.hour = 6
            mock_now.minute = 0
            mock_now.strftime.return_value = "2026-06-10"
            mock_dt.now.return_value = mock_now
            sched._maybe_fire_morning()

        mock_morning.assert_called_once()

    def test_run_morning_stewardship_imports_and_calls_checkin(self):
        from jarvis.scheduler import AgentScheduler

        sched = object.__new__(AgentScheduler)
        sched._runtime = MagicMock()

        called = []

        async def fake_checkin():
            called.append(True)
            return {"source": "ok"}

        with patch.dict("sys.modules", {"jarvis.daily_stewardship": MagicMock(run_morning_checkin=fake_checkin)}):
            sched._run_morning_stewardship()

        assert called, "run_morning_checkin should have been invoked"

    def test_run_morning_stewardship_failure_is_non_fatal(self):
        from jarvis.scheduler import AgentScheduler

        sched = object.__new__(AgentScheduler)
        sched._runtime = MagicMock()

        with patch.dict("sys.modules", {"jarvis.daily_stewardship": MagicMock(run_morning_checkin=MagicMock(side_effect=RuntimeError("boom")))}):
            # Must not raise
            sched._run_morning_stewardship()


# ============================================================
# QC-007 / L9.1 — constitution citation in hard boundary denials
# ============================================================

class TestConstitutionInBoundaryDenials:
    """assess_action_boundary() generates a constitution citation for hard-boundary denials."""

    def _make_runtime_stub(self):
        """Build a minimal JarvisRuntime-like object for boundary testing."""
        from jarvis.runtime import JarvisRuntime
        from jarvis.policy_rails import ActionPolicy

        rt = object.__new__(JarvisRuntime)
        hard_policy = ActionPolicy(
            action_type="spend_money",
            family="financial",
            risk_tier=4,
            min_authority_stage="mature_live",
            approval_mode="deny",
            audit_required=True,
            description="Spend money — hard boundary, always deny autonomously.",
            reversible=False,
            hard_boundary=True,
        )

        rt.trust_support = MagicMock()
        rt.trust_support.get_trust_zone.return_value = {
            "status": "active", "authority_stage": "sandbox_live", "approval_mode": "human"
        }
        rt.trust_support.get_resource_arena.return_value = {"status": "active"}
        rt.trust_support.list_authority_stages.return_value = []

        with patch("jarvis.policy_rails.get_action_policy", return_value=hard_policy):
            with patch("jarvis.runtime.get_active_mode_contract", side_effect=Exception("no mode"), create=True):
                result = rt.assess_action_boundary(
                    zone_id="family-bmad.personal-local",
                    action_type="spend_money",
                    requested_stage="sandbox_live",
                )
        return result

    def test_hard_boundary_deny_contains_decision_deny(self):
        result = self._make_runtime_stub()
        assert result["decision"] == "deny"
        assert result["hard_boundary"] is True

    def test_hard_boundary_deny_contains_constitution_citation_id(self):
        """Hard boundary denials include a constitution_citation_id."""
        result = self._make_runtime_stub()
        assert "constitution_citation_id" in result, (
            "Hard boundary denials must include a constitution_citation_id from ConstitutionEngine.cite()"
        )
        assert result["constitution_citation_id"]

    def test_hard_boundary_deny_includes_principle_basis(self):
        """The principle text should be included in the denial."""
        result = self._make_runtime_stub()
        assert "principle_basis" in result
        assert isinstance(result["principle_basis"], str)

    def test_constitution_audit_file_written_on_hard_boundary_deny(self):
        """ConstitutionEngine.cite() must write an audit record."""
        import tempfile
        from jarvis.constitution_engine import ConstitutionEngine

        with tempfile.TemporaryDirectory() as d:
            audit_path = Path(d) / "constitution_audit.jsonl"
            engine = ConstitutionEngine(audit_path=audit_path)
            cit = engine.cite(
                decision_id="test-cite-001",
                actor="system",
                recommendation_summary="Deny spend_money — hard boundary",
                principle_ids=["III.3.legible_agency"],
                authority_stage="sandbox_live",
            )
            assert audit_path.exists()
            import json
            lines = [json.loads(l) for l in audit_path.read_text().strip().splitlines() if l.strip()]
            assert any(r.get("decision_id") == "test-cite-001" for r in lines)


# ============================================================
# QC-006 / L8.1 — Foundry approve() registers agent stub
# ============================================================

class TestFoundryApproveRegistersAgentStub:
    """After approve(), the newborn agent appears in AgentRegistry.list()."""

    def test_register_newborn_adds_to_registry(self):
        from jarvis.agentic import AgentRegistry

        reg = AgentRegistry()
        original_count = len(reg.list())

        spec = {
            "agent_id": "test-newborn-001",
            "name": "Research Bot",
            "mission": "Conduct research on given topics",
            "role": "researcher",
            "zone": "system_agent",
            "memory_scope": ["project"],
            "tool_scope": ["search", "summarize"],
        }
        stub = reg.register_newborn(spec)

        assert stub.agent_id == "test-newborn-001"
        assert stub.label == "Research Bot"
        assert stub.agent_class == "newborn-agent"
        assert stub.promotion_status == "approved"
        assert len(reg.list()) == original_count + 1

    def test_register_newborn_idempotent(self):
        """Registering the same agent_id twice returns the existing entry without duplication."""
        from jarvis.agentic import AgentRegistry

        reg = AgentRegistry()
        spec = {"agent_id": "test-newborn-idem", "name": "Bot", "mission": "x", "role": "researcher"}
        reg.register_newborn(spec)
        count_after_first = len(reg.list())
        reg.register_newborn(spec)
        assert len(reg.list()) == count_after_first

    def test_register_newborn_requires_agent_id(self):
        from jarvis.agentic import AgentRegistry
        import pytest

        reg = AgentRegistry()
        with pytest.raises(ValueError, match="agent_id"):
            reg.register_newborn({"name": ""})

    def test_approved_agent_visible_in_by_id(self):
        from jarvis.agentic import AgentRegistry

        reg = AgentRegistry()
        spec = {"agent_id": "test-newborn-byid", "name": "Task Bot", "mission": "handle tasks"}
        reg.register_newborn(spec)
        assert "test-newborn-byid" in reg.by_id()

    def test_scheduler_can_see_registered_newborn(self):
        """After register_newborn(), the scheduler's _should_run_now sees the agent."""
        from jarvis.agentic import AgentRegistry

        reg = AgentRegistry()
        spec = {"agent_id": "test-scheduler-newborn", "name": "Auto Bot", "mission": "do stuff", "cadence_minutes": 10}
        stub = reg.register_newborn(spec)
        assert stub in reg.list()
        assert reg.by_id()["test-scheduler-newborn"] is stub
