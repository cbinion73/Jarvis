from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jarvis.growth_intelligence import GrowthStore, HealthLog, LearningItem, WorldSignal


class GrowthStoreTests(unittest.TestCase):
    def test_replays_learning_from_append_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = GrowthStore(root=Path(tmp) / "growth")
            items = [
                LearningItem(
                    item_id="learn-1",
                    title="Study signal routing",
                    item_type="article",
                    topic="systems",
                    status="in_progress",
                    source="user_stated",
                    notes="Understanding how ambient interventions should route.",
                )
            ]

            store.save_learning(items)
            store._learning_path.write_text("", encoding="utf-8")

            replayed = store.load_learning()

            self.assertEqual(len(replayed), 1)
            self.assertEqual(replayed[0].item_id, "learn-1")
            self.assertEqual(replayed[0].title, "Study signal routing")

    def test_replays_signals_from_append_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = GrowthStore(root=Path(tmp) / "growth")
            signal = WorldSignal(
                signal_id="signal-1",
                title="Local policy change",
                signal_type="news",
                topic="community",
                summary="A new local policy may affect scouts.",
                source="briefing",
                detected_at="2026-06-02T12:00:00+00:00",
            )

            store.append_signal(signal)
            store._signals_path.write_text("", encoding="utf-8")

            replayed = store.load_signals()

            self.assertEqual(len(replayed), 1)
            self.assertEqual(replayed[0].signal_id, "signal-1")
            self.assertEqual(replayed[0].title, "Local policy change")

    def test_replays_health_log_from_append_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = GrowthStore(root=Path(tmp) / "growth")
            entry = HealthLog(
                log_id="health-1",
                actor_id="chris",
                date="2026-06-02",
                activity_type="walk",
                duration_minutes=45,
                intensity="moderate",
                notes="Strong recovery day.",
                steps=6200,
                calories_active=320,
                heart_rate_avg=104,
            )

            store.append_health_log(entry)
            store._health_path.write_text("", encoding="utf-8")

            replayed = store.load_health_log("chris")

            self.assertEqual(len(replayed), 1)
            self.assertEqual(replayed[0].actor_id, "chris")
            self.assertEqual(replayed[0].date, "2026-06-02")


if __name__ == "__main__":
    unittest.main()
