from __future__ import annotations

import os
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jarvis.catalyst import CatalystStore, CatalystSupport


class _FakeConfig:
    catalyst_profile_path = Path("household/jarvis_catalyst_profile.example.json")

    def load_json_profile(self, _path: Path, default: dict) -> dict:
        return default


class _FakeOpenAIClient:
    def prompt_text(self, _prompt: str, _content: str, *, max_output_tokens: int) -> str:
        return (
            "Opportunities:\n"
            "- Reduce recurring subscriptions\n"
            "- Revisit one high-friction task\n\n"
            "Risks:\n"
            "- The week stays noisy\n"
            "- Follow-up gets delayed\n\n"
            "Recommended Focus:\n"
            "- Audit subscriptions\n"
        )


class CatalystProactiveRuntimeHygieneTests(unittest.TestCase):
    def setUp(self) -> None:
        self._cwd = Path.cwd()
        self._tmp = tempfile.TemporaryDirectory()
        self._runtime_root = Path(self._tmp.name) / "runtime"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_seed_reads_continue_when_runtime_store_is_empty(self) -> None:
        seed_path = self._cwd / "data" / "catalyst" / "proactive_surfacing_runs.json"
        seed_records = json.loads(seed_path.read_text(encoding="utf-8"))
        if not seed_records:
            self.skipTest("No tracked Catalyst proactive seed records are present")

        with patch.dict(os.environ, {"JARVIS_CATALYST_RUNTIME_ROOT": str(self._runtime_root)}):
            store = CatalystStore(Path("data") / "catalyst")
            records = store.list_records(store.proactive_path, limit=len(seed_records))

        self.assertEqual(records, list(reversed(seed_records)))

    def test_proactive_surfacing_appends_to_runtime_path_and_preserves_payload_shape(self) -> None:
        seed_path = self._cwd / "data" / "catalyst" / "proactive_surfacing_runs.json"
        seed_before = seed_path.read_text(encoding="utf-8")

        with patch.dict(os.environ, {"JARVIS_CATALYST_RUNTIME_ROOT": str(self._runtime_root)}):
            store = CatalystStore(Path("data") / "catalyst")
            support = CatalystSupport(_FakeConfig(), _FakeOpenAIClient(), store)
            result = support.proactive_surfacing(
                actor="Chris",
                horizon="today",
                context="clean-tree regression",
            )

        expected_keys = {
            "run_id",
            "actor",
            "horizon",
            "opportunities",
            "risks",
            "recommended_focus",
            "raw_output",
            "timestamp",
        }
        self.assertEqual(set(result), expected_keys)
        self.assertEqual(result["actor"], "Chris")
        self.assertEqual(result["horizon"], "today")
        self.assertTrue(result["run_id"])

        runtime_path = self._runtime_root / "proactive_surfacing_runs.json"
        self.assertTrue(runtime_path.exists())
        runtime_records = json.loads(runtime_path.read_text(encoding="utf-8"))
        self.assertEqual(runtime_records[-1]["run_id"], result["run_id"])
        self.assertEqual(runtime_records[-1]["actor"], "Chris")

        self.assertEqual(seed_path.read_text(encoding="utf-8"), seed_before)

    def test_proactive_surfacing_does_not_change_git_status(self) -> None:
        before = subprocess.run(
            ["git", "status", "--short"],
            check=True,
            capture_output=True,
            text=True,
            cwd=self._cwd,
        ).stdout

        with patch.dict(os.environ, {"JARVIS_CATALYST_RUNTIME_ROOT": str(self._runtime_root)}):
            store = CatalystStore(Path("data") / "catalyst")
            support = CatalystSupport(_FakeConfig(), _FakeOpenAIClient(), store)
            support.proactive_surfacing(
                actor="Chris",
                horizon="today",
                context="clean-tree regression",
            )

        after = subprocess.run(
            ["git", "status", "--short"],
            check=True,
            capture_output=True,
            text=True,
            cwd=self._cwd,
        ).stdout
        self.assertEqual(after, before)

    def test_absolute_source_catalyst_root_writes_to_ignored_runtime_state(self) -> None:
        seed_path = self._cwd / "data" / "catalyst" / "proactive_surfacing_runs.json"
        seed_before = seed_path.read_text(encoding="utf-8")
        runtime_path = self._cwd / "data" / "state" / "catalyst" / "proactive_surfacing_runs.json"

        before = subprocess.run(
            ["git", "status", "--short"],
            check=True,
            capture_output=True,
            text=True,
            cwd=self._cwd,
        ).stdout
        try:
            store = CatalystStore(self._cwd / "data" / "catalyst")
            support = CatalystSupport(_FakeConfig(), _FakeOpenAIClient(), store)
            result = support.proactive_surfacing(
                actor="Chris",
                horizon="today",
                context="absolute clean-tree regression",
            )

            self.assertEqual(store.proactive_path, runtime_path)
            self.assertTrue(runtime_path.exists())
            runtime_records = json.loads(runtime_path.read_text(encoding="utf-8"))
            self.assertEqual(runtime_records[-1]["run_id"], result["run_id"])
            self.assertEqual(seed_path.read_text(encoding="utf-8"), seed_before)

            check_ignore = subprocess.run(
                ["git", "check-ignore", "-q", str(runtime_path.relative_to(self._cwd))],
                cwd=self._cwd,
            )
            self.assertEqual(check_ignore.returncode, 0)

            after = subprocess.run(
                ["git", "status", "--short"],
                check=True,
                capture_output=True,
                text=True,
                cwd=self._cwd,
            ).stdout
            self.assertEqual(after, before)
        finally:
            if runtime_path.exists():
                runtime_path.unlink()
            for directory in [runtime_path.parent, runtime_path.parent.parent]:
                if directory.exists() and not any(directory.iterdir()):
                    directory.rmdir()


if __name__ == "__main__":
    unittest.main()
