from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ArchitectOfficeCliTests(unittest.TestCase):
    def test_cli_help_works(self) -> None:
        result = subprocess.run(
            ["python3", "-m", "architect_office", "review", "--help"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("usage: python3 -m architect_office review", result.stdout)
        self.assertIn("--phase", result.stdout)
        self.assertIn("--report", result.stdout)

    def test_review_command_writes_output(self) -> None:
        report_path = ROOT / "artifacts" / "build-reports" / "sample-build-office-report.md"
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "review.md"
            result = subprocess.run(
                [
                    "python3",
                    "-m",
                    "architect_office",
                    "review",
                    "--phase",
                    "phase-1-companion-spine",
                    "--report",
                    str(report_path),
                    "--output",
                    str(output),
                    "--repo-root",
                    str(ROOT),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0)
            self.assertTrue(output.exists())
            text = output.read_text(encoding="utf-8")
            self.assertIn("# Architecture Office Review", text)
            self.assertIn("Needs Rework", text)


if __name__ == "__main__":
    unittest.main()
