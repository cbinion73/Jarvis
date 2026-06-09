"""
GAP-2: Verify that AgentScheduler._tick() drives the event fabric autonomously,
not only when an HTTP consumer calls background_agent_status.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, call


def _make_scheduler(tmp_path: Path):
    from jarvis.scheduler import AgentScheduler, AgentWorkQueue

    runtime = MagicMock()
    runtime.agent_registry.list.return_value = []
    runtime.background_cycle.return_value = {"scheduler": {}}

    queue = AgentWorkQueue(tmp_path / "queue.jsonl")

    class _NullStore:
        def load(self):
            return {"agents": {}}
        def save(self, payload):
            pass

    return AgentScheduler(runtime, queue, _NullStore()), runtime


def test_tick_calls_background_cycle(tmp_path) -> None:
    """A single _tick() must invoke runtime.background_cycle exactly once."""
    scheduler, runtime = _make_scheduler(tmp_path)
    scheduler._tick()
    runtime.background_cycle.assert_called_once()


def test_tick_background_cycle_exception_does_not_propagate(tmp_path) -> None:
    """A background_cycle failure must not kill the scheduler loop."""
    scheduler, runtime = _make_scheduler(tmp_path)
    runtime.background_cycle.side_effect = RuntimeError("fabric exploded")
    # Should not raise
    scheduler._tick()


def test_tick_missing_background_cycle_is_safe(tmp_path) -> None:
    """If the runtime has no background_cycle (e.g. a stub), _tick() still completes."""
    scheduler, runtime = _make_scheduler(tmp_path)
    del runtime.background_cycle  # simulate absent attribute
    scheduler._tick()


def test_tick_called_per_schedule_loop_iteration(tmp_path) -> None:
    """_schedule_loop fires _tick; confirm background_cycle accumulates over N iterations."""
    scheduler, runtime = _make_scheduler(tmp_path)
    # Simulate 3 manual ticks (as the daemon thread would)
    for _ in range(3):
        scheduler._tick()
    assert runtime.background_cycle.call_count == 3
