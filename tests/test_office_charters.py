from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

from jarvis.office_charters import (
    CHARTER_VERSION,
    OFFICE_NAMES,
    all_office_briefs,
    charter_for_duty,
    office_charter,
    onboarding_brief,
)


ROOT = Path(__file__).resolve().parents[1]


class OfficeCharterTests(unittest.TestCase):
    def test_all_four_charters_are_complete_and_versioned(self) -> None:
        briefs = all_office_briefs()
        self.assertEqual(set(briefs), set(OFFICE_NAMES))
        required = {
            "purpose",
            "owns",
            "inputs",
            "outputs",
            "must_not",
            "done_when",
            "heartbeat",
            "handoff",
        }
        for name, payload in briefs.items():
            charter = payload["charter"]
            self.assertEqual(charter["office"], name)
            self.assertEqual(charter["charter_version"], CHARTER_VERSION)
            self.assertTrue(required.issubset(charter))
            self.assertIn("working ON JARVIS", payload["onboarding_brief"])

    def test_duties_map_to_separate_accountable_offices(self) -> None:
        self.assertEqual(charter_for_duty("analysis")["office"], "architect")
        self.assertEqual(charter_for_duty("implementation")["office"], "build")
        self.assertEqual(charter_for_duty("review")["office"], "qa")

    def test_unknown_office_and_duty_fail_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "office must be one of"):
            office_charter("release-wizard")
        with self.assertRaisesRegex(ValueError, "No office charter"):
            charter_for_duty("merge")

    def test_onboarding_brief_contains_authority_and_handoff(self) -> None:
        brief = onboarding_brief("qa")
        self.assertIn("You own:", brief)
        self.assertIn("You must not:", brief)
        self.assertIn("Heartbeat:", brief)
        self.assertIn("Handoff:", brief)
        self.assertIn("Definition of done:", brief)

    def test_cli_returns_copy_ready_briefs_for_all_offices(self) -> None:
        completed = subprocess.run(
            ["python3", "scripts/jarvis_build_office.py", "office-brief", "all"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        )
        payload = json.loads(completed.stdout)
        self.assertEqual(set(payload), set(OFFICE_NAMES))
        self.assertIn("JARVIS Orchestration Office", payload["orchestration"]["onboarding_brief"])
