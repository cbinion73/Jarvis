"""The scheduler must consume APPROVED work items.

The agent work lifecycle used to stall at APPROVED: agents dreamed,
researched, and proposed autonomously, Chris approved — and nothing
called start_implementing(). These tests pin the consumer loop:
approved items get an implementation kickoff, implementing items
accumulate one increment per cycle, and after enough increments the
item moves to TRACKING with an honest no-metrics-yet note.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from jarvis.agent_work import (
    STATUS_APPROVED,
    STATUS_IMPLEMENTING,
    STATUS_TRACKING,
    AgentWorkStore,
)
from jarvis.scheduler import AgentScheduler


def _make_store(tmpdir: str) -> AgentWorkStore:
    store = AgentWorkStore("test-agent", base_dir=Path(tmpdir) / "test-agent")
    item = store.dream_idea(
        title="Sell a JARVIS deployment guide",
        idea="Package the deployment playbook as a paid guide.",
        domain="passive-income",
    )
    store.advance_to_research(item.work_id, "Demand exists; comparable guides sell.")
    store.submit_proposal(item.work_id, "Write and sell the guide. Effort ~20h.")
    store.mark_approved(item.work_id, approved_by="Chris")
    return store


def _scheduler() -> AgentScheduler:
    sched = AgentScheduler.__new__(AgentScheduler)  # skip __init__ machinery
    sched._work_advance_tick_count = 0
    return sched


class _FakeGateway:
    def __init__(self, reply: str | None = None) -> None:
        self.calls: list[str] = []
        self.reply = reply if reply is not None else (
            "1. Outline the guide\n2. Draft chapter one\n\n"
            "First deliverable: a full guide outline with twelve sections, "
            "covering setup, hardening, deployment, and rollback in enough "
            "detail that each section can be drafted independently next."
        )

    def simple_complete(self, prompt: str, max_tokens: int = 512, task_type: str = "converse") -> str:
        self.calls.append(prompt)
        return self.reply


class ApprovedWorkConsumerTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.store = _make_store(self._tmp.name)
        self.sched = _scheduler()
        self.gateway = _FakeGateway()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _run_cycle(self) -> None:
        # Force the interval gate open, then run one consumer pass.
        self.sched._work_advance_tick_count = self.sched._WORK_ADVANCE_TICK_INTERVAL - 1
        with mock.patch("jarvis.scheduler._get_gateway", return_value=self.gateway), \
                mock.patch("jarvis.agent_work.get_all_stores", return_value={"test-agent": self.store}):
            self.sched._advance_approved_work()

    def test_approved_item_moves_to_implementing_with_kickoff(self) -> None:
        self._run_cycle()
        item = self.store.all_items()[0]
        self.assertEqual(item.status, STATUS_IMPLEMENTING)
        self.assertIn("Implementation kickoff", item.implementation)
        self.assertIn("guide outline", item.implementation)

    def test_implementing_item_accumulates_increments(self) -> None:
        self._run_cycle()  # approved -> implementing
        self._run_cycle()  # increment 1
        self._run_cycle()  # increment 2
        item = self.store.all_items()[0]
        self.assertEqual(item.status, STATUS_IMPLEMENTING)
        self.assertEqual(item.implementation.count("### Increment"), 2)

    def test_item_moves_to_tracking_after_enough_increments(self) -> None:
        cycles_to_tracking = 1 + self.sched._WORK_IMPLEMENTATION_INCREMENTS + 1
        for _ in range(cycles_to_tracking):
            self._run_cycle()
        item = self.store.all_items()[0]
        self.assertEqual(item.status, STATUS_TRACKING)
        # The tracking note must be honest: no fabricated effectiveness.
        self.assertEqual(item.effectiveness_score, 0.0)
        self.assertIn("not yet collected", item.metrics)

    def test_thin_gateway_reply_does_not_advance_item(self) -> None:
        self.gateway.reply = "ok"
        self._run_cycle()
        item = self.store.all_items()[0]
        self.assertEqual(item.status, STATUS_APPROVED)
        self.assertEqual(item.implementation, "")

    def test_no_gateway_means_no_advancement(self) -> None:
        self.sched._work_advance_tick_count = self.sched._WORK_ADVANCE_TICK_INTERVAL - 1
        with mock.patch("jarvis.scheduler._get_gateway", return_value=None), \
                mock.patch("jarvis.agent_work.get_all_stores", return_value={"test-agent": self.store}):
            self.sched._advance_approved_work()
        item = self.store.all_items()[0]
        self.assertEqual(item.status, STATUS_APPROVED)

    def test_interval_gate_prevents_every_tick_execution(self) -> None:
        self.sched._work_advance_tick_count = 0
        with mock.patch("jarvis.scheduler._get_gateway", return_value=self.gateway), \
                mock.patch("jarvis.agent_work.get_all_stores", return_value={"test-agent": self.store}):
            self.sched._advance_approved_work()  # tick 1 of 10 — gate closed
        self.assertEqual(self.store.all_items()[0].status, STATUS_APPROVED)
        self.assertEqual(self.gateway.calls, [])

    def test_prompts_forbid_faking_external_actions(self) -> None:
        self._run_cycle()
        self.assertTrue(self.gateway.calls)
        self.assertIn("Needs Chris", self.gateway.calls[0])


if __name__ == "__main__":
    unittest.main()
