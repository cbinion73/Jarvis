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


class _BriefingRuntime:
    def __init__(self) -> None:
        self._open_loops = [
            {
                "item_id": "loop-1",
                "domain": "family",
                "kind": "message-draft",
                "title": "Review family follow-up draft",
                "summary": "Pepper staged a note that still needs your decision.",
                "status": "pending",
                "actor": "Chris",
                "timestamp": "2026-06-06T02:15:00Z",
                "task_lane": "household-home",
                "owner_agent": "Pepper",
                "available_actions": ["approve", "defer-1d", "surface-now"],
                "proactive_reason": "This is still blocking the family lane.",
                "next_action": "Approve or defer the note before the first handoff block.",
            }
        ]

    def get_actor(self, actor_name: str):
        normalized = str(actor_name or "Chris").strip() or "Chris"
        return SimpleNamespace(user_id=normalized.lower(), display_name=normalized.title())

    def chamber_home_snapshot(self, actor_name: str) -> dict:
        return {
            "briefing_items": [
                {
                    "id": "brief-1",
                    "text": "The next move is already staged in your family lane.",
                    "agent": "JARVIS",
                    "timestamp": "2026-06-06T06:55:00Z",
                }
            ],
            "working_items": [],
            "needs_items": [],
            "drift_items": [],
            "greeting": "Good morning, Chris.",
            "mode": "morning",
            "generated_at": "2026-06-06T06:55:00Z",
        }

    def chamber_home_aggregate(self, actor_name: str, **_: object) -> dict:
        return {"command_items": []}

    def unified_open_loops(self, actor_name: str, limit: int = 6) -> dict:
        items = [dict(item) for item in self._open_loops[:limit]]
        return {
            "items": items,
            "summary": {
                "total": len(items),
            },
        }

    def apply_open_loop_action(
        self,
        actor_name: str,
        *,
        domain: str,
        item_id: str,
        action: str,
        until: str = "",
        note: str = "",
    ) -> dict:
        for item in self._open_loops:
            if item["item_id"] != item_id or item["domain"] != domain:
                continue
            if action == "defer-1d":
                item["status"] = "deferred"
                item["available_actions"] = ["surface-now"]
            elif action == "surface-now":
                item["status"] = "pending"
                item["available_actions"] = ["approve", "defer-1d"]
            elif action == "approve":
                self._open_loops = [entry for entry in self._open_loops if entry["item_id"] != item_id]
            else:
                raise ValueError("Unsupported action.")
            return {
                "ok": True,
                "actor": actor_name,
                "domain": domain,
                "item_id": item_id,
                "action": action,
                "record": {
                    "status": item.get("status", "completed") if action != "approve" else "approved",
                    "note": note,
                    "until": until,
                },
                "open_loops": self.unified_open_loops(actor_name, limit=18),
            }
        raise KeyError("Open-loop item not found.")


class AppleBriefingOpenLoopTests(unittest.TestCase):
    def setUp(self) -> None:
        self._cwd = Path.cwd()
        self._tmpdir = tempfile.TemporaryDirectory()
        os.chdir(self._tmpdir.name)
        self._original_audit_root = apple_api._ACTIVITY_AUDIT_ROOT
        apple_api._ACTIVITY_AUDIT_ROOT = Path("data/logs")
        self.runtime = _BriefingRuntime()
        self.app = FastAPI()
        apple_api._register_apple_api(self.app, self.runtime)

    def tearDown(self) -> None:
        apple_api._ACTIVITY_AUDIT_ROOT = self._original_audit_root
        os.chdir(self._cwd)
        self._tmpdir.cleanup()

    def _route(self, path: str, method: str):
        for route in self.app.router.routes:
            if getattr(route, "path", None) == path and method.upper() in getattr(route, "methods", set()):
                return route.endpoint
        raise AssertionError(f"Could not find route {method} {path}")

    def test_apple_briefing_includes_open_loop_items(self) -> None:
        response = asyncio.run(self._route("/api/apple/briefing", "GET")(actor="chris"))
        self.assertTrue(response["ok"])
        payload = response["data"]
        self.assertEqual(len(payload["open_loop_items"]), 1)
        self.assertEqual(payload["open_loop_items"][0]["item_id"], "loop-1")
        self.assertEqual(payload["open_loop_items"][0]["available_actions"], ["approve", "defer-1d", "surface-now"])

    def test_apple_briefing_open_loop_action_persists_activity_and_progress(self) -> None:
        action = self._route("/api/apple/briefing/open-loops/{item_id}/action", "POST")
        response = asyncio.run(
            action(
                "loop-1",
                {
                    "actor": "chris",
                    "domain": "family",
                    "action": "defer-1d",
                    "title": "Review family follow-up draft",
                    "summary": "Pepper staged a note that still needs your decision.",
                    "note": "Push this to tomorrow's Daily Brief sweep.",
                },
            )
        )

        self.assertTrue(response["ok"])
        payload = response["data"]
        self.assertEqual(payload["status"], "recorded")
        self.assertEqual(payload["performed_action"], "defer-1d")
        self.assertEqual(payload["focus"]["module"], "Daily Brief")
        self.assertEqual(payload["open_loop"]["status"], "deferred")
        self.assertEqual(payload["open_loop_count"], 1)

        recent = AuditLog(Path("data/logs")).list_recent(limit=4, entry_type="operator-action")
        self.assertEqual(recent[0]["action"], "Apple Daily Brief Defer 1D")
        self.assertEqual(recent[0]["related_kind"], "daily-brief-open-loop")
        self.assertEqual(recent[0]["related_route"], "/briefing-center")

        focus = ProgressFocusStore(Path("data/logs")).summary(limit=4)
        self.assertEqual(focus["latest"]["module"], "Daily Brief")


if __name__ == "__main__":
    unittest.main()
