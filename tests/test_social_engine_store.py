from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jarvis.social_engine import ContentPost, LaunchSchedule, LokiAgent, SocialEngagement, SocialEngineStore


class SocialEngineStoreTests(unittest.TestCase):
    def test_replays_posts_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = SocialEngineStore(root=Path(tmp))
            post = ContentPost(
                post_id="post-1",
                project_id="proj-1",
                platform="instagram",
                content_type="image",
                caption="Launch soon",
            )

            store.save_post(post)
            store._posts_path.write_text("", encoding="utf-8")
            store._posts_log_path.write_text("", encoding="utf-8")

            loaded = store.get_post("post-1")

            self.assertIsNotNone(loaded)
            assert loaded is not None
            self.assertEqual(loaded.caption, "Launch soon")

    def test_replays_schedules_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = SocialEngineStore(root=Path(tmp))
            schedule = LaunchSchedule(
                schedule_id="sched-1",
                project_id="proj-1",
                phase="launch_week",
                start_date="2026-06-02",
                end_date="2026-06-09",
            )

            store.save_schedule(schedule)
            store._schedules_path.write_text("", encoding="utf-8")
            store._schedules_log_path.write_text("", encoding="utf-8")

            loaded = store.get_schedule("sched-1")

            self.assertIsNotNone(loaded)
            assert loaded is not None
            self.assertEqual(loaded.phase, "launch_week")

    def test_replays_engagement_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = SocialEngineStore(root=Path(tmp))
            snap = SocialEngagement(
                snapshot_id="snap-1",
                project_id="proj-1",
                platform="linkedin",
                captured_at="2026-06-02T12:00:00+00:00",
                total_engagement=42,
            )

            store.save_engagement(snap)
            store._engagement_path.write_text("", encoding="utf-8")
            store._engagement_log_path.write_text("", encoding="utf-8")

            loaded = store.list_engagement(project_id="proj-1")

            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0].total_engagement, 42)

    def test_replays_launch_strategies_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = SocialEngineStore(root=Path(tmp))
            agent = LokiAgent(store)

            strategy = agent.build_launch_strategy(
                project_id="proj-1",
                book_title="Level 9",
                launch_date="2026-07-01",
                author_bio="Chris builds resilient systems.",
                key_themes=["autonomy", "execution"],
            )
            agent._strategies_path.write_text("", encoding="utf-8")
            agent._strategies_log_path.write_text("", encoding="utf-8")

            loaded = agent._load_strategies()

            self.assertIn("proj-1", loaded)
            self.assertEqual(loaded["proj-1"]["strategy_id"], strategy["strategy_id"])


if __name__ == "__main__":
    unittest.main()
