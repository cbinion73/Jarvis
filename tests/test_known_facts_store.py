from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jarvis.known_facts import DriftEvent, KnownFactsStore, MemoryFact, _now_iso


class KnownFactsStoreTests(unittest.TestCase):
    def test_replays_fact_index_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = KnownFactsStore(root=Path(tmp) / "memory")
            fact = MemoryFact(
                fact_id="fact-1",
                domain="projects",
                actor_id="chris",
                key="current_focus",
                value="Advance Level 9 substrate",
                confidence=1.0,
                source="user_stated",
                created_at=_now_iso(),
                updated_at=_now_iso(),
                expires_at="",
                tags=["priority"],
                last_surfaced_at="",
                surface_count=0,
                confirmed=True,
            )

            store.set_fact(fact)
            store._index_path("projects").write_text("", encoding="utf-8")
            store._index_log_path("projects").write_text("", encoding="utf-8")

            replayed = store.get_fact("chris", "projects", "current_focus")

            self.assertIsNotNone(replayed)
            self.assertEqual(replayed.fact_id, "fact-1")
            self.assertEqual(replayed.value, "Advance Level 9 substrate")

    def test_replays_drift_event_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = KnownFactsStore(root=Path(tmp) / "memory")
            drift = DriftEvent(
                drift_id="drift-1",
                actor_id="chris",
                domain="priorities",
                description="Execution is drifting from stated priorities",
                stated_priority="Advance Level 9 substrate",
                observed_reality="Low-value admin work is consuming the day",
                detected_at=_now_iso(),
                severity="moderate",
                acknowledged=False,
                resolved=False,
                resolved_at="",
            )

            store.log_drift(drift)
            store._drift_path("drift-1").write_text("", encoding="utf-8")
            store._drift_log_path("drift-1").write_text("", encoding="utf-8")

            acknowledged = store.acknowledge_drift("drift-1")
            replayed = store._read_drift("drift-1")

            self.assertTrue(acknowledged)
            self.assertIsNotNone(replayed)
            self.assertTrue(replayed.acknowledged)
            self.assertFalse(replayed.resolved)

    def test_replays_active_drift_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = KnownFactsStore(root=Path(tmp) / "memory")
            drift = DriftEvent(
                drift_id="drift-2",
                actor_id="chris",
                domain="projects",
                description="Focus is fragmented",
                stated_priority="Advance substrate work",
                observed_reality="Interrupted by lower-priority tasks",
                detected_at=_now_iso(),
                severity="gentle",
                acknowledged=False,
                resolved=False,
                resolved_at="",
            )

            store.log_drift(drift)
            store._drift_path("drift-2").write_text("", encoding="utf-8")
            store._drift_log_path("drift-2").write_text("", encoding="utf-8")

            active = store.get_active_drift("chris")

            self.assertEqual(len(active), 1)
            self.assertEqual(active[0].drift_id, "drift-2")
            self.assertEqual(active[0].domain, "projects")


if __name__ == "__main__":
    unittest.main()
