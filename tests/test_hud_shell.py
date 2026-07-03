"""The HUD is the flagship experience served at the root route."""

from __future__ import annotations

import unittest

from jarvis.jarvis_theme_hud import render_hud_shell


class _Cfg:
    your_name = "Chris"


class _Runtime:
    config = _Cfg()


class HudShellTests(unittest.TestCase):
    def setUp(self) -> None:
        self.html = render_hud_shell(_Runtime())

    def test_renders_complete_document_with_user_name(self) -> None:
        self.assertIn("<!DOCTYPE html>", self.html)
        self.assertIn("</html>", self.html)
        self.assertIn("Chris", self.html)
        self.assertNotIn("__USER_NAME__", self.html)

    def test_core_and_stage_structure_present(self) -> None:
        for marker in (
            'class="core-orb"',          # the arc-reactor core
            'id="stream"',               # conversation stage
            'id="input"',                # composer
            'id="constellation"',        # live agent constellation
            'id="needs-list"',           # needs-you panel
            'id="missions-list"',        # missions panel
            'data-state="ambient"',      # state-driven core
        ):
            self.assertIn(marker, self.html, marker)

    def test_wired_to_real_endpoints_only(self) -> None:
        # Every data source is a real route — the never-fake-it contract.
        for endpoint in (
            "/api/respond",
            "/api/command-center",
            "/api/briefing/module",
            "/ws/events",
        ):
            self.assertIn(endpoint, self.html, endpoint)

    def test_escape_hatches_to_prior_shells(self) -> None:
        # Chris evaluates the redesign; the old experiences stay one click away.
        self.assertIn('href="/glass"', self.html)
        self.assertIn('href="/command-center"', self.html)

    def test_no_fstring_escape_corruption(self) -> None:
        # Guard against the documented f-string disease: JS regex/string
        # escapes must survive rendering intact.
        self.assertIn(r"replace(/\s*I've been paying attention", self.html)
        self.assertNotIn("{__", self.html)


if __name__ == "__main__":
    unittest.main()
