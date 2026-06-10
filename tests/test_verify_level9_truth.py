from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import verify_level9_truth


SESSION_STATE_SAMPLE = """# JARVIS Session State

## Current Maturity Placement

| Level | Current realistic state | Target for Level 9 program |
|---|---:|---:|
| Level 2: Unified Command Product | >95% | Maintain >95% |
| Level 5: Ambient Household Intelligence | ~70% | >95% |

## External Blockers

- Home Assistant: future integration hub
- Provider credentials: Google and Weather

# Master Level 9 Completion Plan
"""


class VerifyLevel9TruthTests(unittest.TestCase):
    def test_parse_session_state_extracts_levels_and_blockers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "JARVIS-SESSION-STATE.md"
            path.write_text(SESSION_STATE_SAMPLE, encoding="utf-8")

            levels, blockers = verify_level9_truth.parse_session_state(path)

        self.assertEqual(len(levels), 2)
        self.assertEqual(levels[0].level, "Level 2: Unified Command Product")
        self.assertEqual(levels[1].percent_text, "~70%")
        self.assertEqual(
            blockers,
            [
                "Home Assistant: future integration hub",
                "Provider credentials: Google and Weather",
            ],
        )

    def test_build_truth_report_surfaces_seeded_data_findings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs").mkdir()
            (root / "artifacts" / "qa").mkdir(parents=True)
            (root / "artifacts" / "generated").mkdir(parents=True)
            (root / "data" / "family").mkdir(parents=True)

            session_state = root / "docs" / "JARVIS-SESSION-STATE.md"
            session_state.write_text(SESSION_STATE_SAMPLE, encoding="utf-8")
            (root / "data" / "family" / "drafts.json").write_text(
                json.dumps(
                    [
                        {
                            "audience": "Troop parents",
                            "body": "Indoor backup update",
                        }
                    ]
                ),
                encoding="utf-8",
            )

            (root / "artifacts" / "qa" / "jarvis-platform-report.json").write_text(
                json.dumps({"summary": {"passed": 3, "failed": 1}, "failures": ["route crash"]}),
                encoding="utf-8",
            )
            (root / "artifacts" / "qa" / "jarvis-provider-layer-report.json").write_text(
                json.dumps({"summary": {"passed": 1, "failed": 0, "warned": 1}, "failures": []}),
                encoding="utf-8",
            )

            with patch.object(
                verify_level9_truth,
                "_git_truth",
                return_value={"branch_status": "## main", "head": "abc123", "dirty": False, "status_excerpt": []},
            ), patch.object(
                verify_level9_truth,
                "_build_deployment_context",
                return_value={"label": "Local dev", "data_path": str(root / "data"), "note": "local", "in_docker": False},
            ):
                report = verify_level9_truth.build_truth_report(root, session_state)

        self.assertEqual(report["no_fake_data_audit"]["status"], "warn")
        self.assertEqual(len(report["no_fake_data_audit"]["seed_findings"]), 1)
        self.assertEqual(report["no_fake_data_audit"]["runtime_exposed_findings"], [])
        self.assertEqual(len(report["no_fake_data_audit"]["filtered_at_read_findings"]), 1)
        self.assertNotIn("fake-data:data/family/drafts.json:0", report["proof_ledger"]["unresolved_failures"])
        self.assertEqual(report["proof_ledger"]["platform_e2e"]["summary"]["failed"], 1)
        self.assertEqual(report["channel_truth"]["deployed"]["status"], "unverified")

    def test_main_writes_machine_readable_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs").mkdir()
            (root / "artifacts" / "qa").mkdir(parents=True)
            session_state = root / "docs" / "JARVIS-SESSION-STATE.md"
            session_state.write_text(SESSION_STATE_SAMPLE, encoding="utf-8")
            output = root / "artifacts" / "qa" / "level9-truth-report.json"

            with patch.object(
                verify_level9_truth,
                "_git_truth",
                return_value={"branch_status": "## main", "head": "abc123", "dirty": False, "status_excerpt": []},
            ), patch.object(
                verify_level9_truth,
                "_build_deployment_context",
                return_value={"label": "Local dev", "data_path": str(root / "data"), "note": "local", "in_docker": False},
            ), patch.object(
                verify_level9_truth.sys,
                "argv",
                [
                    "verify_level9_truth.py",
                    "--repo-root",
                    str(root),
                    "--session-state",
                    str(session_state),
                    "--output",
                    str(output),
                ],
            ):
                code = verify_level9_truth.main()

            payload = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertEqual(payload["source_of_truth"], "docs/JARVIS-SESSION-STATE.md")
        self.assertEqual(len(payload["scorecard"]), 2)
        self.assertEqual(payload["scorecard"][0]["owner"], "Codex autonomous run")


if __name__ == "__main__":
    unittest.main()
