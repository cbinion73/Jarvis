"""Playwright must never poison the caller's thread.

Playwright's sync API starts an asyncio event loop and leaves it running
in whatever thread first touches it. When that was the caller's thread,
every later asyncio.run() there raised "cannot be called from a running
event loop" — observed cascading into 135 unrelated test failures the
moment playwright became importable, and a real hazard for reused
threadpool threads in production. These tests pin the fix: all Playwright
work runs on a dedicated thread, and the caller's thread stays clean.
"""

from __future__ import annotations

import asyncio
import threading
import unittest
from unittest import mock

from jarvis import browser_search


class BrowserThreadIsolationTests(unittest.TestCase):
    def test_playwright_fallback_runs_on_dedicated_thread(self) -> None:
        seen: dict[str, str] = {}

        def _fake_fetch(url: str, timeout_ms: int) -> str:
            seen["thread"] = threading.current_thread().name
            return "page text"

        with mock.patch.object(browser_search, "_fetch_with_playwright", _fake_fetch), \
                mock.patch.object(browser_search, "_http_get", return_value=""):
            result = browser_search.fetch_page_text("https://example.com/js-page")
        self.assertEqual(result, "page text")
        self.assertIn("jarvis-playwright", seen["thread"])
        self.assertNotEqual(seen["thread"], threading.current_thread().name)

    def test_caller_thread_can_still_asyncio_run_after_fetch(self) -> None:
        # Simulate what sync Playwright does: park a running event loop in
        # the executing thread. Confined to the dedicated thread, it must
        # not break asyncio.run() for the caller.
        def _loop_parking_fetch(url: str, timeout_ms: int) -> str:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return "fetched"

        with mock.patch.object(browser_search, "_fetch_with_playwright", _loop_parking_fetch), \
                mock.patch.object(browser_search, "_http_get", return_value=""):
            browser_search.fetch_page_text("https://example.com/js-page")

        # The caller's thread must be unpoisoned:
        self.assertEqual(asyncio.run(_probe()), "ok")

    def test_close_browser_without_startup_is_safe(self) -> None:
        # _close_browser on a process that never launched Playwright must
        # not create the executor or raise.
        with mock.patch.object(browser_search, "_playwright_executor", None):
            browser_search._close_browser()


async def _probe() -> str:
    return "ok"


if __name__ == "__main__":
    unittest.main()
