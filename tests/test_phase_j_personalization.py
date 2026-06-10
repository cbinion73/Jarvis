"""Phase J: Personalization completions.

J3 – AdaptationContextBuilder drives different real cards per actor/mode/season.
J4 – Child tutoring auto-creates parent review approval on boundary redirect or frustration.
J5 – Doctor packet includes health_state (conditions, medications, targets).
"""
from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# FastAPI stub — same complete class-based pattern.
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

from jarvis.adaptation import AdaptationContextBuilder, AdaptationContext


# ── J3: AdaptationContextBuilder drives different cards ────────────────────────

class TestJ3AdaptationContextBuilder(unittest.TestCase):
    """J3: Different actors/modes/seasons produce genuinely different guidance cards."""

    def setUp(self):
        self.builder = AdaptationContextBuilder()

    def _build(self, **kwargs) -> AdaptationContext:
        base = {
            "actor": "chris",
            "season": "fall",
            "household_mode": "normal",
            "calendar_event_count": 0,
            "energy_level": "moderate",
            "sleep_quality": "good",
            "mood": "good",
        }
        base.update(kwargs)
        return self.builder.build(**base)

    def test_crisis_vs_normal_mode_tone_differs(self):
        crisis = self._build(household_mode="crisis")
        normal = self._build(household_mode="normal")
        self.assertNotEqual(crisis.tone, normal.tone,
                            "crisis and normal modes should have different tones")

    def test_crisis_mode_higher_urgency_floor(self):
        crisis = self._build(household_mode="crisis")
        normal = self._build(household_mode="normal")
        self.assertGreater(crisis.urgency_floor, normal.urgency_floor,
                           "crisis mode should have higher urgency floor than normal")

    def test_heavy_calendar_pressure(self):
        heavy = self._build(calendar_event_count=5)
        light = self._build(calendar_event_count=0)
        self.assertEqual(heavy.calendar_pressure, "heavy")
        self.assertEqual(light.calendar_pressure, "light")

    def test_high_stress_signals(self):
        stressed = self._build(stress_signals=["deadline", "conflict", "overdue"])
        relaxed = self._build()
        self.assertEqual(stressed.stress_level, "high")
        self.assertNotEqual(stressed.stress_level, relaxed.stress_level)

    def test_health_focus_when_low_energy(self):
        depleted = self._build(energy_level="depleted")
        self.assertTrue(depleted.health_focus)

    def test_health_focus_off_normal_energy(self):
        normal = self._build(energy_level="moderate")
        self.assertFalse(normal.health_focus)

    def test_faith_focus_with_active_study(self):
        faith = self._build(faith_active=True, current_study_theme="Psalm 23")
        self.assertTrue(faith.faith_focus)

    def test_season_summer_themes(self):
        summer = self._build(season="summer")
        self.assertIn("summer", summer.season)
        self.assertTrue(len(summer.season_themes) > 0)

    def test_guidance_card_differs_by_person(self):
        """guidance_card_differs_by_person() correctly identifies differences."""
        ctx_a = self._build(actor="chris", household_mode="crisis", energy_level="depleted")
        ctx_b = self._build(actor="sarah", household_mode="normal", energy_level="moderate")
        result = self.builder.guidance_card_differs_by_person(
            actor_a="chris", ctx_a=ctx_a,
            actor_b="sarah", ctx_b=ctx_b,
        )
        self.assertTrue(result["differs"],
                        f"Cards should differ between crisis/depleted and normal/moderate but got: {result}")
        self.assertGreater(len(result["differences"]), 0)

    def test_same_inputs_same_card(self):
        """Same inputs produce identical cards."""
        ctx_a = self._build()
        ctx_b = self._build()
        self.assertEqual(ctx_a.tone, ctx_b.tone)
        self.assertEqual(ctx_a.stress_level, ctx_b.stress_level)

    def test_guidance_card_endpoint_in_service(self):
        """J3: /api/adaptation/guidance-card endpoint exists in service.py."""
        service_path = Path(__file__).parent.parent / "jarvis" / "service.py"
        src = service_path.read_text(encoding="utf-8")
        self.assertIn('"/api/adaptation/guidance-card"', src)


# ── J4: Child tutoring auto-creates parent review ─────────────────────────────

class TestJ4TutoringParentReview(unittest.TestCase):
    """J4: Boundary redirect or high frustration auto-creates parent review approval."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _make_tutoring_store(self):
        from jarvis.tutoring import TutoringStore
        store_root = self.root / "tutoring"
        store_root.mkdir(parents=True, exist_ok=True)
        return TutoringStore(root=store_root)

    def _make_tutoring_support(self, store):
        from jarvis.tutoring import TutoringSupport
        config = MagicMock()
        config.load_json_profile.return_value = {
            "policyNotes": [],
            "parentViewNotes": [],
            "children": {
                "Zara": {
                    "blockedTopics": ["confidential", "adult content"],
                    "studySupports": ["math"],
                    "notes": [],
                    "allowedModules": ["child-tutor"],
                    "forbiddenModules": ["executive-work"],
                    "parentVisibility": "summary-only",
                }
            },
            "adultKeywords": ["thermo", "confidential"],
            "boundaryNotes": [],
        }
        openai_client = MagicMock()
        openai_client.prompt_text.return_value = (
            "Reply: Good question! Let's think through this step by step.\n"
            "Parent Summary: Child asked for homework help.\n"
            "Encouragement: Keep trying!\n"
            "Follow Up: Can you explain your first step?"
        )
        support = TutoringSupport(config=config, openai_client=openai_client, store=store)
        return support

    def _child_actor(self, name: str = "Zara"):
        actor = MagicMock()
        actor.display_name = name
        actor.permissions = "child"
        actor.priorities = []  # prevents MagicMock from leaking into subject_label
        return actor

    def test_boundary_redirect_creates_approval(self):
        store = self._make_tutoring_store()
        support = self._make_tutoring_support(store)
        child = self._child_actor()

        created_approvals = []

        class _MockApprovalStore:
            def __init__(self, root): pass
            def add(self, req):
                created_approvals.append(req)

        with patch("jarvis.audit.ApprovalStore", _MockApprovalStore):
            # "confidential" is in adultKeywords → should trigger boundary redirect
            session = support.tutoring_turn(child, "Show me the confidential documents")

        self.assertEqual(session["boundary_status"], "redirected")
        self.assertEqual(len(created_approvals), 1)
        self.assertIn("child_tutoring_action", created_approvals[0].action_class)

    def test_high_frustration_creates_approval(self):
        store = self._make_tutoring_store()
        support = self._make_tutoring_support(store)
        child = self._child_actor()

        # Force frustration signal to "high"
        created_approvals = []

        class _MockApprovalStore:
            def __init__(self, root): pass
            def add(self, req):
                created_approvals.append(req)

        with patch("jarvis.audit.ApprovalStore", _MockApprovalStore):
            with patch.object(support, "_infer_frustration", return_value="high"):
                session = support.tutoring_turn(child, "Help me with my math homework")

        self.assertEqual(len(created_approvals), 1)
        self.assertIn("frustration", created_approvals[0].rationale.lower())

    def test_normal_session_no_approval(self):
        store = self._make_tutoring_store()
        support = self._make_tutoring_support(store)
        child = self._child_actor()

        created_approvals = []

        class _MockApprovalStore:
            def __init__(self, root): pass
            def add(self, req):
                created_approvals.append(req)

        with patch("jarvis.audit.ApprovalStore", _MockApprovalStore):
            session = support.tutoring_turn(child, "Help me understand fractions")

        # Normal session: no boundary redirect, low frustration → no approval
        self.assertNotEqual(session["boundary_status"], "redirected")
        if session["frustration_signal"] not in ("high", "critical"):
            self.assertEqual(len(created_approvals), 0)

    def test_approval_store_failure_does_not_break_tutoring(self):
        """J4: If approval creation fails, tutoring session still completes."""
        store = self._make_tutoring_store()
        support = self._make_tutoring_support(store)
        child = self._child_actor()

        class _BrokenApprovalStore:
            def __init__(self, root): pass
            def add(self, req): raise RuntimeError("DB unavailable")

        with patch("jarvis.audit.ApprovalStore", _BrokenApprovalStore):
            session = support.tutoring_turn(child, "Show me confidential things")
        # Session must succeed even if approval store fails
        self.assertIn("session_id", session)


# ── J5: Doctor packet includes health_state ────────────────────────────────────

class TestJ5DoctorPacket(unittest.TestCase):
    """J5: build_doctor_packet() includes health_state (conditions, medications, targets)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "health"

    def tearDown(self):
        self.tmp.cleanup()

    def _make_store(self):
        from jarvis.health_loop import HealthLoopStore
        return HealthLoopStore(root=self.root)

    def _seed_checkin(self, store):
        store.add_checkin(
            actor="chris",
            date="2026-06-01",
            mood="good",
            energy="moderate",
            sleep_quality="good",
            sleep_hours=7.5,
            hydration_oz=64.0,
            three_moves=["Exercise", "Read", "Code"],
            gratitude="Family",
            notes="Feeling fine",
        )

    def test_doctor_packet_includes_health_context(self):
        store = self._make_store()
        self._seed_checkin(store)

        health_state = {
            "medical_history": {
                "known_conditions": [{"name": "Hypertension"}, {"name": "Prediabetes"}],
                "medications": [{"name": "Lisinopril"}, {"name": "Metformin"}],
                "allergies": ["Penicillin"],
            },
            "health_targets": {"systolic_bp": 120, "weight_lbs": 180},
        }

        with patch("jarvis.longevity_council.load_health_state", return_value=health_state):
            packet = store.build_doctor_packet("chris", days=7)

        self.assertEqual(packet["source"], "live")
        self.assertIn("health_context", packet)
        ctx = packet["health_context"]
        self.assertIn("Hypertension", ctx["known_conditions"])
        self.assertIn("Lisinopril", ctx["current_medications"])
        self.assertIn("Penicillin", ctx["allergies"])
        self.assertIn("systolic_bp", ctx.get("health_targets", {}))

    def test_doctor_packet_health_unavailable_still_returns_live(self):
        """If health_state load fails, packet still returns with health_context unavailable."""
        store = self._make_store()
        self._seed_checkin(store)

        with patch("jarvis.longevity_council.load_health_state", side_effect=RuntimeError("state missing")):
            packet = store.build_doctor_packet("chris", days=7)

        self.assertEqual(packet["source"], "live")
        self.assertIn("health_context", packet)
        self.assertEqual(packet["health_context"]["source"], "unavailable")

    def test_doctor_packet_no_checkins_returns_unavailable(self):
        store = self._make_store()
        packet = store.build_doctor_packet("chris", days=7)
        self.assertEqual(packet["source"], "unavailable")
        self.assertIn("reason", packet)


if __name__ == "__main__":
    unittest.main()
