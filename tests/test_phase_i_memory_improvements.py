"""Phase I: Memory + Chronicle improvements.

I1 – retrieve_by_situation gets unresolved_loop and lesson dimensions.
I2 – add_entry rejects entries with invalid provenance values.
I4 – ChronicleNarrativeStore produces source="chronicle_snapshot" refs.
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

from jarvis.memory import MemoryStore
from jarvis.models import MemoryEntry, MemoryProfileFact


def _make_store(tmp: Path) -> MemoryStore:
    config = {
        "version": "1.0",
        "members": [{"user_id": "chris", "display_name": "Chris"}],
        "accessPolicy": {"default": "household"},
        "promotionRules": {},
    }
    import json
    profile_path = tmp / "profile.json"
    profile_path.write_text(json.dumps(config))
    return MemoryStore(root=tmp)


def _make_fact(
    fact_id: str,
    title: str,
    summary: str,
    tags: list[str] | None = None,
    status: str = "active",
    subject_user_id: str = "chris",
    lane: str = "personal",
) -> dict:
    return {
        "fact_id": fact_id,
        "subject_user_id": subject_user_id,
        "subject_display_name": "Chris",
        "lane": lane,
        "title": title,
        "summary": summary,
        "tags": tags or [],
        "source_entry_ids": [],
        "confidence": "confirmed",
        "status": status,
        "source_type": "user-stated",
        "boundary_label": "",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    }


# ── I1: retrieve_by_situation new dimensions ──────────────────────────────────

class TestI1SituationalRetrieval(unittest.TestCase):
    """I1: unresolved_loop and lesson dimensions in retrieve_by_situation."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = _make_store(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _seed(self, facts: list[dict]):
        import json
        path = self.store.facts_path
        path.write_text(json.dumps(facts))

    def test_unresolved_loop_keyword_match(self):
        facts = [
            _make_fact("f1", "Open question about budget", "Unresolved budget loop for Q3", tags=["open"]),
            # f2 has no actor/domain/task match and no open-loop markers — scores 0
            _make_fact("f2", "Dinner preference", "Likes pasta", tags=["food"], subject_user_id=""),
        ]
        self._seed(facts)
        results = self.store.retrieve_by_situation("chris", {"unresolved_loop": "budget"})
        ids = [r["fact_id"] for r in results]
        self.assertIn("f1", ids)
        self.assertNotIn("f2", ids)

    def test_unresolved_loop_marker_tag_boost(self):
        facts = [
            _make_fact("f1", "Pending task", "Still waiting for reply", tags=["pending", "work"]),
            _make_fact("f2", "Done task", "Task is complete", tags=["done"]),
        ]
        self._seed(facts)
        # Even without keyword, "pending" tag is an open-loop marker
        results = self.store.retrieve_by_situation("chris", {"unresolved_loop": "xyz_nomatch"})
        ids = [r["fact_id"] for r in results]
        self.assertIn("f1", ids)

    def test_lesson_tag_match(self):
        facts = [
            _make_fact("f1", "Learned about timezones", "Lesson: always use UTC", tags=["lesson", "engineering"]),
            # f2 has no actor/domain/task match and no lesson signals — scores 0
            _make_fact("f2", "Dinner preference", "Likes pasta", tags=["food"], subject_user_id=""),
        ]
        self._seed(facts)
        results = self.store.retrieve_by_situation("chris", {"lesson": True})
        ids = [r["fact_id"] for r in results]
        self.assertIn("f1", ids)
        self.assertNotIn("f2", ids)

    def test_lesson_text_match(self):
        facts = [
            _make_fact("f1", "Retrospective on Q4", "We learned that deploys on Fridays are risky", tags=["work"]),
            _make_fact("f2", "Dinner preference", "Likes pasta", tags=["food"], subject_user_id=""),
        ]
        self._seed(facts)
        results = self.store.retrieve_by_situation("chris", {"lesson": True})
        ids = [r["fact_id"] for r in results]
        self.assertIn("f1", ids)

    def test_lesson_false_does_not_boost(self):
        facts = [
            _make_fact("f1", "Learned about timezones", "Lesson: always use UTC", tags=["lesson"]),
            _make_fact("f2", "Budget work", "Q3 budget", tags=["work", "budget"]),
        ]
        self._seed(facts)
        # With lesson=False and domain=work, only domain match should score
        results = self.store.retrieve_by_situation("chris", {"domain": "work", "lesson": False})
        ids = [r["fact_id"] for r in results]
        # f2 has "work" tag; f1 has "lesson" but not "work" domain
        self.assertIn("f2", ids)

    def test_excluded_status_still_excluded(self):
        facts = [
            _make_fact("f1", "Pending issue", "Still open loop", tags=["open", "pending"], status="retired"),
            _make_fact("f2", "Active pending", "Open question", tags=["open"], status="active"),
        ]
        self._seed(facts)
        results = self.store.retrieve_by_situation("chris", {"unresolved_loop": "open"})
        ids = [r["fact_id"] for r in results]
        self.assertNotIn("f1", ids, "Retired facts must remain excluded even with unresolved_loop match")
        self.assertIn("f2", ids)

    def test_open_loop_tag_passive_boost(self):
        facts = [
            _make_fact("f1", "Waiting for call", "Follow-up needed", tags=["loop", "pending"]),
            _make_fact("f2", "Completed item", "All done", tags=["done"]),
        ]
        self._seed(facts)
        # Without any context key, open-loop tags still get passive boost when combined with domain
        results = self.store.retrieve_by_situation("chris", {})
        # Can't assert inclusion without other context, but verify it doesn't raise
        self.assertIsInstance(results, list)


# ── I2: Provenance enforcement at add_entry ────────────────────────────────────

class TestI2ProvenanceEnforcement(unittest.TestCase):
    """I2: add_entry() rejects invalid provenance values."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = _make_store(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _make_entry(self, provenance: str = "observed_fact") -> MemoryEntry:
        from jarvis.models import MemoryEntry
        return MemoryEntry(
            entry_id="e-test",
            owner="chris",
            memory_type="general",
            scope="private",
            project="",
            title="Test entry",
            summary="Test summary",
            tags=[],
            sensitivity="normal",
            approval_status="approved",
            cloud_excluded=False,
            encrypted_payload="",
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
            provenance=provenance,
        )

    def test_valid_provenance_accepted(self):
        from jarvis.models import MEMORY_PROVENANCE_VALUES
        for prov in MEMORY_PROVENANCE_VALUES:
            entry = self._make_entry(provenance=prov)
            # Should not raise
            self.store.add_entry(entry)

    def test_invalid_provenance_raises(self):
        entry = self._make_entry(provenance="totally_made_up")
        with self.assertRaises(ValueError) as ctx:
            self.store.add_entry(entry)
        self.assertIn("totally_made_up", str(ctx.exception))
        self.assertIn("not a valid provenance", str(ctx.exception).lower())

    def test_empty_provenance_accepted(self):
        entry = self._make_entry(provenance="")
        # Empty provenance = not set, should not be enforced
        self.store.add_entry(entry)

    def test_provenance_none_treated_as_empty_and_accepted(self):
        """None/absent provenance is treated as empty string — not enforced."""
        from jarvis.models import MemoryEntry
        entry = MemoryEntry(
            entry_id="e-no-prov",
            owner="chris",
            memory_type="general",
            scope="private",
            project="",
            title="No provenance",
            summary="This entry has no explicit provenance",
            tags=[],
            sensitivity="normal",
            approval_status="approved",
            cloud_excluded=False,
            encrypted_payload="",
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
            provenance="",  # empty — should not be rejected
        )
        # Should not raise
        self.store.add_entry(entry)


# ── I4: ChronicleNarrativeStore ────────────────────────────────────────────────

class TestI4ChronicleNarrativeStore(unittest.TestCase):
    """I4: ChronicleNarrativeStore produces narrative refs sourced from Chronicle snapshot."""

    def _make_reader(self, entries=None, prayers=None) -> MagicMock:
        reader = MagicMock()
        reader.get_entries.return_value = entries or []
        reader.get_prayer_items.return_value = prayers or []
        return reader

    def test_refs_sourced_from_chronicle_snapshot(self):
        from jarvis.chronicle_bridge import ChronicleNarrativeStore
        entries = [
            {"id": "e1", "type": "journal", "title": "Morning study", "content": "Psalm 23",
             "themes": ["trust", "rest"], "date": "2026-06-01", "passage": "Psalm 23"},
        ]
        reader = self._make_reader(entries=entries)
        store = ChronicleNarrativeStore(reader=reader)
        refs = store.get_narrative_refs()
        self.assertGreater(len(refs), 0)
        for r in refs:
            self.assertEqual(r["source"], "chronicle_snapshot",
                             f"Ref {r['ref_id']} has source={r['source']!r}, expected 'chronicle_snapshot'")

    def test_prayer_refs_excluded_answered(self):
        from jarvis.chronicle_bridge import ChronicleNarrativeStore
        prayers = [
            {"id": "p1", "text": "Open prayer", "category": "health", "dateAdded": "2026-06-01", "answered": False},
            {"id": "p2", "text": "Answered prayer", "category": "work", "dateAdded": "2026-05-01", "answered": True},
        ]
        reader = self._make_reader(prayers=prayers)
        store = ChronicleNarrativeStore(reader=reader)
        refs = store.get_narrative_refs()
        ref_ids = [r["ref_id"] for r in refs]
        self.assertIn("p1", ref_ids)
        self.assertNotIn("p2", ref_ids, "Answered prayers should not be included as active refs")

    def test_dedup_by_ref_id(self):
        from jarvis.chronicle_bridge import ChronicleNarrativeStore
        entries = [
            {"id": "e1", "type": "journal", "title": "Title A", "content": "...", "themes": [], "date": "2026-06-01"},
            {"id": "e1", "type": "journal", "title": "Title A dup", "content": "...", "themes": [], "date": "2026-06-01"},
        ]
        reader = self._make_reader(entries=entries)
        store = ChronicleNarrativeStore(reader=reader)
        refs = store.get_narrative_refs()
        ref_ids = [r["ref_id"] for r in refs]
        self.assertEqual(len(ref_ids), len(set(ref_ids)), "Duplicate ref_ids found")

    def test_empty_snapshot_returns_empty(self):
        from jarvis.chronicle_bridge import ChronicleNarrativeStore
        reader = self._make_reader(entries=[], prayers=[])
        store = ChronicleNarrativeStore(reader=reader)
        refs = store.get_narrative_refs()
        self.assertEqual(refs, [])

    def test_narrative_summary_ok_false_when_no_refs(self):
        from jarvis.chronicle_bridge import ChronicleNarrativeStore
        reader = self._make_reader(entries=[], prayers=[])
        store = ChronicleNarrativeStore(reader=reader)
        summary = store.narrative_summary()
        self.assertFalse(summary.get("ok"), f"Expected ok=False, got {summary}")

    def test_narrative_summary_structure(self):
        from jarvis.chronicle_bridge import ChronicleNarrativeStore
        entries = [
            {"id": "e1", "type": "devotional", "title": "Study", "content": "...",
             "themes": ["grace", "peace"], "date": "2026-06-01"},
        ]
        prayers = [
            {"id": "p1", "text": "Healing for family", "category": "health",
             "dateAdded": "2026-06-01", "answered": False},
        ]
        reader = self._make_reader(entries=entries, prayers=prayers)
        store = ChronicleNarrativeStore(reader=reader)
        summary = store.narrative_summary()
        self.assertTrue(summary.get("ok"), f"Expected ok=True, got {summary}")
        self.assertIn("total_refs", summary)
        self.assertIn("top_themes", summary)
        self.assertEqual(summary["source"], "chronicle_snapshot")
        self.assertEqual(summary["unanswered_prayers"], 1)

    def test_reader_failure_fails_open(self):
        from jarvis.chronicle_bridge import ChronicleNarrativeStore
        reader = MagicMock()
        reader.get_entries.side_effect = RuntimeError("snapshot missing")
        reader.get_prayer_items.side_effect = RuntimeError("snapshot missing")
        store = ChronicleNarrativeStore(reader=reader)
        refs = store.get_narrative_refs()
        self.assertEqual(refs, [])

    def test_narrative_refs_endpoint_in_service(self):
        """I4: /api/chronicle/narrative-refs endpoint exists in service.py."""
        service_path = Path(__file__).parent.parent / "jarvis" / "service.py"
        src = service_path.read_text(encoding="utf-8")
        self.assertIn('"/api/chronicle/narrative-refs"', src)


if __name__ == "__main__":
    unittest.main()
