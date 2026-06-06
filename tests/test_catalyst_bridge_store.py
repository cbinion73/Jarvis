from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jarvis.catalyst_bridge import CatalystBridge, CatalystContext


class CatalystBridgeStoreTests(unittest.TestCase):
    def test_replays_pending_handoffs_and_context_from_logs_when_snapshots_are_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            context = CatalystContext(
                context_id="ctx-1",
                source="jarvis",
                context_type="briefing",
                title="Morning Handoff",
                body="Body",
                structured_data={"priorities": ["One"]},
                actor_id="chris",
                created_at="2026-06-02T12:00:00+00:00",
                expires_at="2026-06-03T12:00:00+00:00",
            )

            with patch.object(CatalystBridge, "ROOT", root):
                bridge = CatalystBridge()
                bridge._persist_context(context)
                bridge._enqueue_handoff(context)

                bridge._pending_path.write_text("", encoding="utf-8")
                bridge._context_path(context.context_id).write_text("", encoding="utf-8")

                pending = bridge.get_pending_handoffs()
                recent = bridge.get_recent_contexts(limit=1)

                self.assertEqual(len(pending), 1)
                self.assertEqual(pending[0].context_id, "ctx-1")
                self.assertEqual(len(recent), 1)
                self.assertEqual(recent[0].title, "Morning Handoff")


if __name__ == "__main__":
    unittest.main()
