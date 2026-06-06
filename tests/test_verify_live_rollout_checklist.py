from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from scripts import verify_live_rollout_checklist


class VerifyLiveRolloutChecklistTests(unittest.TestCase):
    def _run_main(self, path: Path) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        original_argv = verify_live_rollout_checklist.sys.argv
        verify_live_rollout_checklist.sys.argv = [
            "verify_live_rollout_checklist.py",
            str(path),
        ]
        try:
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = verify_live_rollout_checklist.main()
        finally:
            verify_live_rollout_checklist.sys.argv = original_argv
        return code, stdout.getvalue(), stderr.getvalue()

    def test_accepts_complete_rollout_checklist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            checklist = Path(tmp) / "rollout.md"
            checklist.write_text(
                "\n".join(
                    [
                        "# Live Feature Rollout Checklist",
                        "",
                        "```bash",
                        "python3 scripts/verify_live_rollout_checklist.py docs/live-feature-rollout-checklist.md",
                        "python3 scripts/test_verify_apple_contracts.py",
                        "swift test --package-path JarvisApple",
                        "```",
                        "",
                        "## Backend Contract",
                        "- ok",
                        "## Web Behavior",
                        "- ok",
                        "## Phone Surface",
                        "- ok",
                        "## Intentional Permission Flow",
                        "- ok",
                        "## Device Verification",
                        "- ok",
                        "## Rollout Notes",
                        "- Feature:",
                        "- Branch:",
                        "- Server / environment:",
                        "- Proof artifacts:",
                        "- Follow-up risks:",
                    ]
                ),
                encoding="utf-8",
            )

            code, stdout, stderr = self._run_main(checklist)

        self.assertEqual(code, 0)
        self.assertIn("rollout checklist verified", stdout)
        self.assertEqual(stderr, "")

    def test_reports_missing_permission_and_rollout_sections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            checklist = Path(tmp) / "rollout.md"
            checklist.write_text(
                "\n".join(
                    [
                        "# Live Feature Rollout Checklist",
                        "",
                        "```bash",
                        "python3 scripts/verify_live_rollout_checklist.py docs/live-feature-rollout-checklist.md",
                        "python3 scripts/test_verify_apple_contracts.py",
                        "swift test --package-path JarvisApple",
                        "```",
                        "",
                        "## Backend Contract",
                        "- ok",
                        "## Web Behavior",
                        "- ok",
                        "## Phone Surface",
                        "- ok",
                        "## Device Verification",
                        "- ok",
                    ]
                ),
                encoding="utf-8",
            )

            code, stdout, stderr = self._run_main(checklist)

        self.assertEqual(code, 1)
        self.assertEqual(stdout, "")
        self.assertIn("## Intentional Permission Flow", stderr)
        self.assertIn("## Rollout Notes", stderr)
        self.assertIn("- Feature:", stderr)
        self.assertIn("- Proof artifacts:", stderr)


if __name__ == "__main__":
    unittest.main()
