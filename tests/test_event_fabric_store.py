from __future__ import annotations

import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from jarvis.event_fabric import DurableEventStore, EventEnvelope
from jarvis.models import AttentionDisposition, TriggerType


def _event(*, event_id: str = "evt-1", occurred_at: datetime | None = None) -> EventEnvelope:
    now = occurred_at or datetime(2026, 6, 2, 12, 0, tzinfo=UTC)
    return EventEnvelope(
        event_id=event_id,
        trigger_type=TriggerType.SIGNAL,
        topic="weather change",
        source="weather-engine",
        occurred_at=now.isoformat(),
        available_at=now.isoformat(),
        status="pending",
        lane="weather",
        urgency=6,
        attention_hint=AttentionDisposition.STAGED,
        dedupe_key="storm-risk:family",
        target_agents=["storm"],
        payload={"changed_fields": ["forecast"]},
    )


class EventFabricStoreTests(unittest.TestCase):
    def test_event_store_replays_projection_from_append_only_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = DurableEventStore(Path(tmp) / "state")
            event = _event()

            published = store.publish(event, dedupe_window_seconds=0)
            self.assertIsNotNone(published)
            store.mark_processed(
                event.event_id,
                [{"agent_id": "storm", "attention": "staged"}],
                processed_at=datetime(2026, 6, 2, 12, 5, tzinfo=UTC),
            )

            store.events_path.unlink()

            reloaded = DurableEventStore(Path(tmp) / "state")
            events = reloaded.list_events()

            self.assertEqual(len(events), 1)
            self.assertEqual(events[0].event_id, event.event_id)
            self.assertEqual(events[0].status, "processed")
            self.assertEqual(events[0].wake_count, 1)
            self.assertTrue(reloaded.events_path.exists())

    def test_event_store_replays_from_state_log_when_log_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = DurableEventStore(Path(tmp) / "state")
            event = _event(event_id="evt-3")

            published = store.publish(event, dedupe_window_seconds=0)
            self.assertIsNotNone(published)
            store.mark_processed(
                event.event_id,
                [{"agent_id": "storm", "attention": "staged"}],
                processed_at=datetime(2026, 6, 2, 12, 5, tzinfo=UTC),
            )

            store.log_path.write_text("", encoding="utf-8")
            store.events_path.unlink()

            reloaded = DurableEventStore(Path(tmp) / "state")
            events = reloaded.list_events()

            self.assertEqual(len(events), 1)
            self.assertEqual(events[0].event_id, event.event_id)
            self.assertEqual(events[0].status, "processed")
            self.assertEqual(events[0].wake_count, 1)

    def test_event_store_summary_reports_state_log_as_truth_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = DurableEventStore(Path(tmp) / "state")
            event = _event(event_id="evt-2")

            store.publish(event, dedupe_window_seconds=0)
            summary = store.summary(limit=5)

            self.assertEqual(summary["truth_source"], "event_bus_state_log.jsonl")
            self.assertEqual(summary["total_events"], 1)
            self.assertEqual(summary["pending_events"], 1)
            self.assertGreaterEqual(summary["log_records"], 1)


if __name__ == "__main__":
    unittest.main()
