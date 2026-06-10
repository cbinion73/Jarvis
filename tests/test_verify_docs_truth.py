from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts import verify_docs_truth


SESSION_STATE = """# JARVIS Session State

Overall placement: solid Level 4, partial Level 5.
`JARVIS-SESSION-STATE.md` is the authoritative execution document.
"""

MATURITY_MODEL_OK = """# JARVIS Maturity Model

JARVIS status:

- >95% complete, but no longer the frontier.

JARVIS status:

- ~90% complete, but not yet closed under the current Level 9 completion contract.

Honest overall placement: solid Level 4, partial Level 5. `docs/JARVIS-SESSION-STATE.md` is the authoritative source for current percentages, active execution order, and what is or is not closed today.
"""

ROADMAP_OK = """# Roadmap

If planning documents disagree about current execution status, maturity
placement, or what should be worked next, `docs/JARVIS-SESSION-STATE.md` wins.
This roadmap remains the long-horizon strategy document.
"""

CHECKLIST_OK = """# Checklist

Docs conflict on whether Level 3 is complete.
Documentation truth
"""

LEVEL3_EXIT_OK = """# Exit Report

This report is historical evidence.
It is not the current source of truth for JARVIS maturity placement.
"""


class VerifyDocsTruthTests(unittest.TestCase):
    def _write_docs(self, root: Path, *, maturity_model: str = MATURITY_MODEL_OK, level3_exit: str = LEVEL3_EXIT_OK) -> None:
        docs = root / "docs"
        docs.mkdir()
        (docs / "JARVIS-SESSION-STATE.md").write_text(SESSION_STATE, encoding="utf-8")
        (docs / "JARVIS-MATURITY-MODEL.md").write_text(maturity_model, encoding="utf-8")
        (docs / "JARVIS-CIVILIZATION-SCALE-MASTER-ROADMAP.md").write_text(ROADMAP_OK, encoding="utf-8")
        (docs / "JARVIS-LEVEL9-COMPREHENSIVE-CHECKLIST.md").write_text(CHECKLIST_OK, encoding="utf-8")
        (docs / "JARVIS-LEVEL3-EXIT-REPORT.md").write_text(level3_exit, encoding="utf-8")

    def test_verify_docs_truth_passes_for_aligned_docs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_docs(root)

            failures = verify_docs_truth.verify_docs_truth(root)

        self.assertEqual(failures, [])

    def test_verify_docs_truth_flags_stale_maturity_claims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_docs(
                root,
                maturity_model=MATURITY_MODEL_OK + "\n- current primary level\n- entering this level\n",
            )

            failures = verify_docs_truth.verify_docs_truth(root)

        self.assertTrue(any("stale phrase" in failure for failure in failures))

    def test_verify_docs_truth_flags_unconditional_exit_report_completion_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_docs(
                root,
                level3_exit=LEVEL3_EXIT_OK + "\n**Level 3 is COMPLETE.**\n",
            )

            failures = verify_docs_truth.verify_docs_truth(root)

        self.assertTrue(any("unconditional current completion claim" in failure for failure in failures))


if __name__ == "__main__":
    unittest.main()
