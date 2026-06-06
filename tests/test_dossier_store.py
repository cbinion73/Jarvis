from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jarvis.dossier import Dossier, DossierStore


class DossierStoreTests(unittest.TestCase):
    def test_replays_dossiers_from_state_log_when_snapshot_is_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = DossierStore(base_dir=Path(tmp))
            dossier = Dossier(
                dossier_id="dossier-1",
                work_id="work-1",
                agent_id="agent-1",
                title="Test Dossier",
                executive_summary="Summary",
            )

            store.save(dossier)
            store._path.write_text("", encoding="utf-8")
            store._log_path.write_text("", encoding="utf-8")

            replayed = DossierStore(base_dir=Path(tmp))
            loaded = replayed.get("dossier-1")

            self.assertIsNotNone(loaded)
            assert loaded is not None
            self.assertEqual(loaded.title, "Test Dossier")
            self.assertEqual(loaded.executive_summary, "Summary")


if __name__ == "__main__":
    unittest.main()
