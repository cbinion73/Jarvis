from __future__ import annotations

import asyncio
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI

import jarvis.apple_api as apple_api
from jarvis.audit import AuditLog, ProgressFocusStore


class _StubRuntime:
    def get_actor(self, actor_name: str):
        return SimpleNamespace(user_id=str(actor_name or "Chris").strip().lower() or "chris", display_name=actor_name)


class AppleHealthCheckInTests(unittest.TestCase):
    def setUp(self) -> None:
        self._cwd = Path.cwd()
        self._tmpdir = tempfile.TemporaryDirectory()
        os.chdir(self._tmpdir.name)
        self._original_audit_root = apple_api._ACTIVITY_AUDIT_ROOT
        apple_api._ACTIVITY_AUDIT_ROOT = Path("data/logs")
        self.app = FastAPI()
        apple_api._register_apple_api(self.app, _StubRuntime())

    def tearDown(self) -> None:
        apple_api._ACTIVITY_AUDIT_ROOT = self._original_audit_root
        os.chdir(self._cwd)
        self._tmpdir.cleanup()

    def _route(self, path: str, method: str):
        for route in self.app.router.routes:
            if getattr(route, "path", None) == path and method.upper() in getattr(route, "methods", set()):
                return route.endpoint
        raise AssertionError(f"Could not find route {method} {path}")

    def test_apple_health_checkin_persists_store_activity_and_progress(self) -> None:
        post = self._route("/api/apple/health/checkins", "POST")
        get = self._route("/api/apple/health/checkins", "GET")
        summary = self._route("/api/apple/health/summary", "GET")

        response = asyncio.run(
            post(
                {
                    "actor": "chris",
                    "actor_id": "chris",
                    "symptoms": "Sore throat watch",
                    "note": "Saving from the native phone health lane.",
                    "energy_level": 5,
                    "sleep_hours": 6.5,
                    "stress_level": 4,
                    "source": "test-apple-health",
                }
            )
        )
        listing = asyncio.run(get(actor="chris"))
        snapshot = asyncio.run(summary(actor="chris"))

        self.assertTrue(response["ok"])
        self.assertEqual(response["data"]["status"], "recorded")
        self.assertEqual(response["data"]["checkin"]["symptoms"], "Sore throat watch")
        self.assertEqual(listing["data"]["count"], 1)
        self.assertEqual(snapshot["data"]["manual_checkin_count"], 1)

        recent = AuditLog(Path("data/logs")).list_recent(limit=4, entry_type="operator-action")
        self.assertEqual(recent[0]["action"], "Save Apple Health Check-In")
        self.assertEqual(recent[0]["related_kind"], "health-checkin")

        focus = ProgressFocusStore(Path("data/logs")).summary(limit=4)
        self.assertEqual(focus["latest"]["module"], "Health")


if __name__ == "__main__":
    unittest.main()
