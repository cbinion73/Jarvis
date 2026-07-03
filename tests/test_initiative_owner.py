"""Active missions must make progress between conversations.

Missions previously only moved when Chris talked to Jarvis. The
initiative-owner loop reviews the least-recently-touched active mission
on a slow cadence and either files the next concrete work item into the
existing approval pipeline, or honestly records that the mission is
waiting or looks complete. These tests pin that behavior — including
the trust boundaries: no auto-approval, no auto-closing, one open work
thread per mission, no advancement without a gateway.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from jarvis.agent_work import AgentWorkStore
from jarvis.scheduler import AgentScheduler


def _mission(mission_id: str = "mission-abc123", **overrides) -> dict:
    base = {
        "mission_id": mission_id,
        "title": "Launch the JARVIS deployment guide",
        "status": "active",
        "brief": "Turn the deployment playbook into a paid guide and launch it.",
        "updated_at": "2026-07-01T00:00:00+00:00",
        "created_at": "2026-06-01T00:00:00+00:00",
        "follow_ups": [],
        "evidence": [{"title": "Kickoff", "summary": "Mission created from conversation."}],
    }
    base.update(overrides)
    return base


class _FakeMissionSupport:
    def __init__(self, missions: list[dict]) -> None:
        self.missions = missions
        self.notes: list[tuple[str, str]] = []

    def list_missions(self, *, include_completed: bool = True, limit: int = 20, actor: str = "") -> list[dict]:
        return list(self.missions)

    def update_mission_details(self, mission_id: str, *, note: str = "", **_: object) -> dict:
        self.notes.append((mission_id, note))
        return {"mission_id": mission_id}


class _FakeGateway:
    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.prompts: list[str] = []

    def simple_complete(self, prompt: str, max_tokens: int = 512, task_type: str = "converse") -> str:
        self.prompts.append(prompt)
        return self.reply


class InitiativeOwnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.store = AgentWorkStore("mission-owner", base_dir=Path(self._tmp.name) / "mission-owner")
        self.support = _FakeMissionSupport([_mission()])
        self.sched = AgentScheduler.__new__(AgentScheduler)
        self.sched._initiative_tick_count = 0

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _run_cycle(self, gateway) -> None:
        self.sched._initiative_tick_count = self.sched._INITIATIVE_TICK_INTERVAL - 1
        self.sched._runtime = mock.Mock(mission_support=self.support)
        with mock.patch("jarvis.scheduler._get_gateway", return_value=gateway), \
                mock.patch("jarvis.agent_work.get_work_store", return_value=self.store):
            self.sched._review_active_initiatives()

    def test_next_reply_files_proposed_work_item(self) -> None:
        gateway = _FakeGateway(
            "NEXT: Draft the guide outline | Produce a complete chapter-level outline "
            "of the deployment guide so writing can start. This is the first concrete "
            "artifact the launch depends on. First step: outline all twelve chapters."
        )
        self._run_cycle(gateway)
        items = self.store.all_items()
        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item.status, "proposed")
        self.assertEqual(item.title, "Draft the guide outline")
        self.assertIn("mission:mission-abc123", item.tags)
        self.assertIn("chapter-level outline", item.proposal)
        # The dossier gets an evidence note pointing at the filed item.
        self.assertEqual(len(self.support.notes), 1)
        self.assertIn("approval queue", self.support.notes[0][1])

    def test_open_work_item_blocks_stacking_another(self) -> None:
        gateway = _FakeGateway("NEXT: Draft the guide outline | Outline the guide.")
        self._run_cycle(gateway)
        self._run_cycle(gateway)
        self.assertEqual(len(self.store.all_items()), 1)
        self.assertEqual(len(gateway.prompts), 1)  # second cycle skipped the review

    def test_waiting_reply_records_note_without_filing_work(self) -> None:
        gateway = _FakeGateway("WAITING: Blocked on Chris choosing the sales platform.")
        self._run_cycle(gateway)
        self.assertEqual(self.store.all_items(), [])
        self.assertEqual(len(self.support.notes), 1)
        self.assertIn("waiting", self.support.notes[0][1])

    def test_done_reply_flags_for_chris_without_closing(self) -> None:
        gateway = _FakeGateway("DONE: The guide shipped and the launch posts are live.")
        self._run_cycle(gateway)
        self.assertEqual(self.store.all_items(), [])
        self.assertEqual(len(self.support.notes), 1)
        note = self.support.notes[0][1]
        self.assertIn("not auto-closing", note.lower())
        # Mission status is untouched — only Chris closes missions.
        self.assertEqual(self.support.missions[0]["status"], "active")

    def test_unparseable_reply_does_nothing(self) -> None:
        gateway = _FakeGateway("I think this mission is going great!")
        self._run_cycle(gateway)
        self.assertEqual(self.store.all_items(), [])
        self.assertEqual(self.support.notes, [])

    def test_no_gateway_means_no_review(self) -> None:
        self._run_cycle(None)
        self.assertEqual(self.store.all_items(), [])
        self.assertEqual(self.support.notes, [])

    def test_non_active_missions_are_ignored(self) -> None:
        self.support.missions = [_mission(status="paused")]
        gateway = _FakeGateway("NEXT: Something | Anything.")
        self._run_cycle(gateway)
        self.assertEqual(self.store.all_items(), [])
        self.assertEqual(gateway.prompts, [])

    def test_review_prompt_forbids_invented_progress(self) -> None:
        gateway = _FakeGateway("WAITING: blocked.")
        self._run_cycle(gateway)
        self.assertTrue(gateway.prompts)
        self.assertIn("Never invent progress", gateway.prompts[0])


if __name__ == "__main__":
    unittest.main()
