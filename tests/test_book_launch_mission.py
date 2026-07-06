"""Jarvis as book-launch project/marketing manager, Ghostwritr as writer.

Trust boundary under test: marketing assets are always staged for approval
(action_type="social_post", MEDIUM tier, never auto-approves) and never
implied as published — there is no live social/press API. Book matching
never fabricates a link to Ghostwritr when the bridge is unavailable or no
real title is mentioned.
"""

from __future__ import annotations

import unittest
from unittest import mock

from jarvis.approvals import AUTO_APPROVE_TIMEOUTS, RiskTier
from jarvis.book_launch import BookBrief, propose_launch_assets
from jarvis.missions import MissionSupport
from jarvis.runtime import JarvisRuntime


class _FakeBook:
    def __init__(self, slug, title, current_stage="EDITING", stages_complete=3, total_stages=8):
        self.slug = slug
        self.title = title
        self.current_stage = current_stage
        self.stages_complete = stages_complete
        self.total_stages = total_stages


class _FakeQueue:
    def __init__(self) -> None:
        self.submitted: list = []

    def submit(self, request) -> str:
        self.submitted.append(request)
        return request.request_id


def _brief(slug: str = "my-book", title: str = "My Book") -> BookBrief:
    return BookBrief(
        slug=slug,
        title=title,
        subtitle="",
        workflow_type="NONFICTION",
        book_status="DRAFT",
        current_stage="EDITING",
        promise="Helps readers do X.",
        outline_summary="",
    )


class _FakeMissionSupportForLookup:
    """Duck-typed stand-in exposing only what find_mission_by_ghostwritr_slug uses."""

    def __init__(self, missions: list) -> None:
        self._missions = missions

    def list_missions(self, *, include_completed: bool = True, limit: int = 500) -> list:
        return list(self._missions)


class MissionLookupTests(unittest.TestCase):
    def test_finds_linked_mission(self) -> None:
        fake = _FakeMissionSupportForLookup([{
            "mission_id": "mission-abc123",
            "title": "My Book: book launch",
            "status": "active",
            "updated_at": "2026-01-01T00:00:00+00:00",
            "memory_snapshot": {"ghostwritr": {"system": "ghostwritr", "slug": "my-book"}},
        }])
        found = MissionSupport.find_mission_by_ghostwritr_slug(fake, "my-book")
        self.assertIsNotNone(found)
        self.assertEqual(found["mission_id"], "mission-abc123")

    def test_returns_none_when_no_mission_linked(self) -> None:
        fake = _FakeMissionSupportForLookup([{
            "mission_id": "mission-other",
            "status": "active",
            "updated_at": "2026-01-01T00:00:00+00:00",
            "memory_snapshot": {},
        }])
        self.assertIsNone(MissionSupport.find_mission_by_ghostwritr_slug(fake, "nonexistent"))

    def test_empty_slug_returns_none(self) -> None:
        fake = _FakeMissionSupportForLookup([])
        self.assertIsNone(MissionSupport.find_mission_by_ghostwritr_slug(fake, ""))
        self.assertIsNone(MissionSupport.find_mission_by_ghostwritr_slug(fake, None))


class ProposeLaunchAssetsTests(unittest.TestCase):
    def test_stages_single_social_post_request(self) -> None:
        queue = _FakeQueue()
        assets = {
            "twitter": ["Post 1", "Post 2"],
            "linkedin": ["LI post"],
            "press_release": "Press release body.",
            "emails": ["Email 1"],
            "amazon_copy": {"description": "..."},
        }
        proposal = propose_launch_assets(
            queue,
            actor_id="chris",
            agent_id="jarvis-companion",
            brief=_brief(),
            assets=assets,
            trigger="pre_launch",
        )
        self.assertEqual(len(queue.submitted), 1)
        request = queue.submitted[0]
        self.assertEqual(request.action_type, "social_post")
        self.assertEqual(request.risk_tier, RiskTier.MEDIUM)
        self.assertEqual(request.payload["assets"], assets)
        self.assertEqual(request.payload["book_slug"], "my-book")
        self.assertIn("cannot publish", request.description)
        self.assertEqual(proposal["object_kind"], "marketing_assets_proposal")
        self.assertEqual(proposal["book_title"], "My Book")
        self.assertEqual(
            set(proposal["platforms"]),
            {"twitter", "linkedin", "press_release", "emails", "amazon_copy"},
        )
        self.assertEqual(proposal["twitter_preview"], "Post 1")
        self.assertEqual(proposal["status"], "pending_approval")

    def test_never_auto_approves(self) -> None:
        queue = _FakeQueue()
        propose_launch_assets(
            queue,
            actor_id="chris",
            agent_id="jarvis-companion",
            brief=_brief(),
            assets={"twitter": ["Post"]},
        )
        request = queue.submitted[0]
        self.assertEqual(request.status, "pending")
        self.assertIsNone(AUTO_APPROVE_TIMEOUTS[RiskTier(request.risk_tier)])

    def test_omits_empty_platforms(self) -> None:
        queue = _FakeQueue()
        proposal = propose_launch_assets(
            queue,
            actor_id="chris",
            agent_id="jarvis-companion",
            brief=_brief(),
            assets={"twitter": [], "linkedin": ["LI post"], "press_release": ""},
        )
        self.assertEqual(proposal["platforms"], ["linkedin"])

    def test_twitter_preview_extracts_text_from_dict_shaped_posts(self) -> None:
        # _generate_twitter returns list[dict] (e.g. {"type": "TEASER", "text": "..."}),
        # not plain strings -- the preview must show the text, not a dict repr.
        queue = _FakeQueue()
        proposal = propose_launch_assets(
            queue,
            actor_id="chris",
            agent_id="jarvis-companion",
            brief=_brief(),
            assets={"twitter": [{"type": "TEASER", "text": "Check out my new book!"}]},
        )
        self.assertEqual(proposal["twitter_preview"], "Check out my new book!")


class TriggerRegexTests(unittest.TestCase):
    def test_book_launch_keyword_regex(self) -> None:
        self.assertTrue(JarvisRuntime._BOOK_LAUNCH_KEYWORD_RE.search(
            "I want Jarvis to manage my book launch"
        ))
        self.assertTrue(JarvisRuntime._BOOK_LAUNCH_KEYWORD_RE.search(
            "draft launch assets for my manuscript"
        ))
        self.assertFalse(JarvisRuntime._BOOK_LAUNCH_KEYWORD_RE.search(
            "what's the weather like today"
        ))

    def test_marketing_asset_regex(self) -> None:
        self.assertTrue(JarvisRuntime._MARKETING_ASSET_RE.search(
            "draft social posts for my book"
        ))
        self.assertTrue(JarvisRuntime._MARKETING_ASSET_RE.search(
            "generate launch assets for Deep Work"
        ))
        self.assertFalse(JarvisRuntime._MARKETING_ASSET_RE.search(
            "remind me to call the dentist"
        ))

    def test_book_launch_status_regex(self) -> None:
        self.assertTrue(JarvisRuntime._BOOK_LAUNCH_STATUS_RE.search(
            "how's my book launch going"
        ))
        self.assertTrue(JarvisRuntime._BOOK_LAUNCH_STATUS_RE.search(
            "status on the launch"
        ))
        self.assertFalse(JarvisRuntime._BOOK_LAUNCH_STATUS_RE.search(
            "draft a press release"
        ))


class ResolveGhostwritrBookMatchTests(unittest.TestCase):
    """_resolve_ghostwritr_book_match never touches self, so it can be
    exercised directly off the class without building a full JarvisRuntime."""

    def test_returns_none_when_bridge_unavailable(self) -> None:
        with mock.patch("jarvis.ghostwritr_bridge.get_ghostwritr_bridge", return_value=None):
            result = JarvisRuntime._resolve_ghostwritr_book_match(None, "manage my book launch")
        self.assertIsNone(result)

    def test_never_fabricates_a_match(self) -> None:
        bridge = mock.MagicMock()
        bridge.get_active_books.return_value = [_FakeBook("real-book", "Real Book Title")]
        with mock.patch("jarvis.ghostwritr_bridge.get_ghostwritr_bridge", return_value=bridge):
            result = JarvisRuntime._resolve_ghostwritr_book_match(
                None, "manage my totally unrelated project"
            )
        self.assertIsNone(result)

    def test_finds_real_title_mention(self) -> None:
        bridge = mock.MagicMock()
        bridge.get_active_books.return_value = [_FakeBook("real-book", "Real Book Title")]
        with mock.patch("jarvis.ghostwritr_bridge.get_ghostwritr_bridge", return_value=bridge):
            result = JarvisRuntime._resolve_ghostwritr_book_match(
                None, "I want Jarvis to manage the launch of Real Book Title"
            )
        self.assertIsNotNone(result)
        _found_bridge, found_book = result
        self.assertEqual(found_book.slug, "real-book")

    def test_handles_bridge_exceptions_gracefully(self) -> None:
        bridge = mock.MagicMock()
        bridge.get_active_books.side_effect = RuntimeError("db down")
        with mock.patch("jarvis.ghostwritr_bridge.get_ghostwritr_bridge", return_value=bridge):
            result = JarvisRuntime._resolve_ghostwritr_book_match(None, "manage my book launch")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
