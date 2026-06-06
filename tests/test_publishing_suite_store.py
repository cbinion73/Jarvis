from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jarvis.publishing_suite import (
    ContentCalendarItem,
    LokiAgent,
    PublishingProject,
    PublishingStore,
    RevenueStream,
    RobbieRobertsonAgent,
    SocialPost,
    StanLeeAgent,
)


class PublishingSuiteStoreTests(unittest.TestCase):
    def test_replays_writing_sessions_from_append_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = PublishingStore(root=Path(tmp))
            project = PublishingProject(
                project_id="proj-1",
                project_type="book",
                title="Level 9",
                status="draft",
                platform="amazon_kdp",
                created_at="2026-06-02T12:00:00+00:00",
                updated_at="2026-06-02T12:00:00+00:00",
            )
            store.save_project(project)
            agent = StanLeeAgent(store)

            agent.track_writing_session(750, "proj-1", notes="Strong chapter progress")
            agent._sessions_path.write_text("", encoding="utf-8")

            status = agent.get_manuscript_status()

            self.assertEqual(len(status), 1)
            self.assertEqual(status[0]["total_words"], 750)
            self.assertEqual(status[0]["session_count"], 1)

    def test_replays_projects_and_revenue_from_append_logs_when_snapshots_are_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = PublishingStore(root=Path(tmp))
            project = PublishingProject(
                project_id="proj-1",
                project_type="book",
                title="Level 9",
                status="draft",
                platform="amazon_kdp",
                created_at="2026-06-02T12:00:00+00:00",
                updated_at="2026-06-02T12:00:00+00:00",
            )
            revenue = RevenueStream(
                stream_id="rev-1",
                stream_type="book_royalty",
                source="Amazon",
                project_id="proj-1",
                monthly_estimate=99.0,
            )

            store.save_project(project)
            store.save_revenue_stream(revenue)
            store._projects_path.write_text("", encoding="utf-8")
            store._revenue_path.write_text("", encoding="utf-8")

            loaded_project = store.get_project("proj-1")
            loaded_revenue = store.list_revenue_streams(active_only=False)

            self.assertIsNotNone(loaded_project)
            assert loaded_project is not None
            self.assertEqual(loaded_project.title, "Level 9")
            self.assertEqual(len(loaded_revenue), 1)
            self.assertEqual(loaded_revenue[0].monthly_estimate, 99.0)

    def test_replays_posts_and_calendar_from_append_logs_when_snapshots_are_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = PublishingStore(root=Path(tmp))
            post = SocialPost(
                post_id="post-1",
                platform="linkedin",
                content="Launch post",
                status="scheduled",
            )
            item = ContentCalendarItem(
                item_id="item-1",
                title="Launch day post",
                content_type="social_post",
                platform="linkedin",
                planned_date="2026-06-02",
            )

            store.save_social_post(post)
            store.save_calendar_item(item)
            store._posts_path.write_text("", encoding="utf-8")
            store._calendar_path.write_text("", encoding="utf-8")

            posts = store.list_posts()
            calendar = store.list_calendar_items()

            self.assertEqual(len(posts), 1)
            self.assertEqual(posts[0].content, "Launch post")
            self.assertEqual(len(calendar), 1)
            self.assertEqual(calendar[0].title, "Launch day post")

    def test_replays_checklists_from_append_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = PublishingStore(root=Path(tmp))
            agent = RobbieRobertsonAgent(store)
            project = PublishingProject(
                project_id="proj-1",
                project_type="book",
                title="Level 9",
                status="draft",
                platform="amazon_kdp",
                created_at="2026-06-02T12:00:00+00:00",
                updated_at="2026-06-02T12:00:00+00:00",
            )
            store.save_project(project)
            agent.track_kdp_checklist("proj-1", "manuscript_final", True)
            agent._checklist_path.write_text("", encoding="utf-8")

            checklist = agent.get_publishing_checklist(project)

            completed = {item["step"]: item["completed"] for item in checklist}
            self.assertTrue(completed["manuscript_final"])

    def test_replays_launch_plans_from_append_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = PublishingStore(root=Path(tmp))
            project = PublishingProject(
                project_id="proj-1",
                project_type="book",
                title="Level 9",
                status="draft",
                platform="amazon_kdp",
                created_at="2026-06-02T12:00:00+00:00",
                updated_at="2026-06-02T12:00:00+00:00",
            )
            store.save_project(project)
            agent = LokiAgent(store)
            plan = agent.build_launch_plan(project)
            agent._launch_plans_path.write_text("", encoding="utf-8")

            loaded = agent._load_plans()

            self.assertIn("proj-1", loaded)
            self.assertEqual(loaded["proj-1"]["plan_id"], plan["plan_id"])


if __name__ == "__main__":
    unittest.main()
