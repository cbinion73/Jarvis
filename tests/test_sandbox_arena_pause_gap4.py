"""
GAP-4: enqueue_self_improvement_sandbox_job must refuse to enqueue if the
sandbox arena (system.agent-sandbox, or job.arena_id) is paused or suspended.

Tests verify:
- Enqueue accepted when arena is active
- Enqueue refused (accepted=False) when arena status is "paused"
- Enqueue refused (accepted=False) when arena status is "suspended"
- Refusal message names the arena and its status
- arena_id and arena_status are present in the refusal response
- Job-level arena_id override is respected over the default
- Enqueue proceeds normally when arena does not exist (no arena registry entry)
- system.agent-sandbox arena is bootstrapped in trust store
"""
from __future__ import annotations

import unittest
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


def _make_runtime(arena_status: str | None = "active", arena_id: str = "system.agent-sandbox"):
    """Build a minimal runtime mock with a controllable trust_support."""
    rt = MagicMock()
    rt._sandbox_lock = __import__("threading").Lock()
    rt._sandbox_futures = {}
    rt._sandbox_queue_state.return_value = {"queued": 0}

    job = {
        "job_id": "job-1",
        "title": "Test mutation",
        "status": "pending",
        "mutation_route": {"route": "sandbox/worktree-only"},
        "review_level": "review-before-code-change",
        "job_type": "self_improvement",
    }
    rt.self_improvement_store.get_job.return_value = deepcopy(job)
    rt.self_improvement_store.get_active_run.return_value = None
    rt.self_improvement_store.upsert_job.return_value = None
    rt.catalyst_support.transition_work_item.return_value = None

    def _get_arena(aid):
        if aid == arena_id and arena_status is not None:
            return {"arena_id": aid, "status": arena_status}
        return None

    rt.trust_support.get_resource_arena.side_effect = _get_arena
    return rt, job


class TestEnqueueArena(unittest.TestCase):

    def _enqueue(self, rt, job_id="job-1", actor="chris"):
        from jarvis.runtime import JarvisRuntime
        return JarvisRuntime.enqueue_self_improvement_sandbox_job(rt, actor, job_id)

    def test_accepted_when_arena_active(self):
        rt, _ = _make_runtime(arena_status="active")
        executor = MagicMock()
        executor.submit.return_value = MagicMock(done=lambda: False)
        rt._sandbox_executor = executor

        result = self._enqueue(rt)
        self.assertTrue(result["ok"])
        self.assertTrue(result["accepted"])

    def test_refused_when_arena_paused(self):
        rt, _ = _make_runtime(arena_status="paused")
        result = self._enqueue(rt)
        self.assertTrue(result["ok"])
        self.assertFalse(result["accepted"])
        self.assertIn("paused", result["message"])
        self.assertEqual(result["arena_status"], "paused")

    def test_refused_when_arena_suspended(self):
        rt, _ = _make_runtime(arena_status="suspended")
        result = self._enqueue(rt)
        self.assertTrue(result["ok"])
        self.assertFalse(result["accepted"])
        self.assertIn("suspended", result["message"])
        self.assertEqual(result["arena_status"], "suspended")

    def test_refusal_message_names_arena(self):
        rt, _ = _make_runtime(arena_status="paused")
        result = self._enqueue(rt)
        self.assertIn("system.agent-sandbox", result["message"])
        self.assertEqual(result["arena_id"], "system.agent-sandbox")

    def test_job_arena_id_overrides_default(self):
        rt, job = _make_runtime(arena_status="paused", arena_id="custom.sandbox")
        job["arena_id"] = "custom.sandbox"
        rt.self_improvement_store.get_job.return_value = deepcopy(job)
        result = self._enqueue(rt)
        self.assertFalse(result["accepted"])
        self.assertEqual(result["arena_id"], "custom.sandbox")

    def test_proceeds_when_arena_not_registered(self):
        rt, _ = _make_runtime(arena_status=None)
        executor = MagicMock()
        executor.submit.return_value = MagicMock(done=lambda: False)
        rt._sandbox_executor = executor

        result = self._enqueue(rt)
        # No arena → should fall through to normal enqueue
        self.assertTrue(result["ok"])
        self.assertTrue(result["accepted"])

    def test_no_submit_when_arena_paused(self):
        rt, _ = _make_runtime(arena_status="paused")
        result = self._enqueue(rt)
        rt._sandbox_executor.submit.assert_not_called()

    def test_arena_status_present_in_refusal(self):
        for status in ("paused", "suspended"):
            with self.subTest(status=status):
                rt, _ = _make_runtime(arena_status=status)
                result = self._enqueue(rt)
                self.assertIn("arena_status", result)
                self.assertEqual(result["arena_status"], status)


class TestSandboxArenaBootstrap(unittest.TestCase):

    def test_system_agent_sandbox_arena_bootstrapped(self):
        """The system.agent-sandbox arena must be registered in the trust store."""
        import tempfile, os
        from pathlib import Path
        from jarvis.trust import TrustStore, TrustSupport

        with tempfile.TemporaryDirectory() as tmpdir:
            orig_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                store = TrustStore(Path(tmpdir))
                ts = TrustSupport(store=store, default_owner_principal="chris")
                ts.bootstrap_defaults()
                arena = ts.get_resource_arena("system.agent-sandbox")
                self.assertIsNotNone(arena, "system.agent-sandbox arena should be bootstrapped")
                self.assertEqual(str(arena.get("status", "")).strip(), "active")
                self.assertEqual(str(arena.get("resource_type", "")).strip(), "self_improvement_sandbox")
            finally:
                os.chdir(orig_cwd)


if __name__ == "__main__":
    unittest.main()
