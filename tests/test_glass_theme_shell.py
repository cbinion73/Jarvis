from __future__ import annotations

import unittest
from types import SimpleNamespace

from jarvis.jarvis_theme_glass import render_glass_shell


class GlassThemeShellTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runtime = SimpleNamespace(config=SimpleNamespace(your_name="Chris"))

    def test_render_glass_shell_includes_safe_area_command_bar_spacing(self) -> None:
        html = render_glass_shell(self.runtime)

        self.assertIn("--bar-safe-h: 150px;", html)
        self.assertIn("padding-bottom: calc(var(--bar-safe-h) + env(safe-area-inset-bottom, 0px));", html)
        self.assertIn("@media (max-width: 1440px), (max-height: 940px)", html)
        self.assertIn("--bar-safe-h: 166px;", html)
        self.assertIn("padding: 8px 24px calc(12px + env(safe-area-inset-bottom, 0px));", html)

    def test_render_glass_shell_exposes_health_desktop_launcher(self) -> None:
        html = render_glass_shell(self.runtime)

        self.assertIn("Open full desktop page", html)
        self.assertIn("onclick=\"openHealthDesktopExperience()\"", html)
        self.assertIn("function openHealthDesktopExperience()", html)
        self.assertIn("window.open('/health-desktop', '_blank', 'noopener');", html)

    def test_render_glass_shell_wires_daily_brief_runtime_controls(self) -> None:
        html = render_glass_shell(self.runtime)

        self.assertIn("id=\"dailybrief-actor-select\"", html)
        self.assertIn("id=\"dailybrief-refresh-button\"", html)
        self.assertIn("id=\"dailybrief-livebrief-button\"", html)
        self.assertIn("id=\"dailybrief-runtime-note\"", html)
        self.assertIn("function refreshDailyBriefDesktop(", html)
        self.assertIn("function refreshDailyBriefLivePacket(", html)
        self.assertIn("function dailyBriefApplyOpenLoopAction(", html)
        self.assertIn("function dailyBriefApplyApprovalAction(", html)
        self.assertIn("function dailyBriefCompleteTask(", html)
        self.assertIn("/api/briefing/module?actor=", html)
        self.assertIn("/api/briefing/live?actor=", html)
        self.assertIn("/api/open-loops/action", html)
        self.assertIn("/api/apple/health/summary", html)
        self.assertIn("/api/activity/operator-action", html)

    def test_render_glass_shell_wires_desktop_card_sequence_controller(self) -> None:
        html = render_glass_shell(self.runtime)

        self.assertIn("function initDesktopCardSequences()", html)
        self.assertIn("function ensureDesktopCardFocusOverlay()", html)
        self.assertIn("function openDesktopCardSequenceModal(", html)
        self.assertIn("data-sequence-view", html)
        self.assertIn("Each numbered Daily Brief card opens as its own focused page", html)
        self.assertIn("Each numbered Social Media card opens as a focused page", html)
        self.assertIn("Each numbered Calendar card opens as a focused page", html)
        self.assertIn("if (name === 'command') name = 'chat';", html)


if __name__ == "__main__":
    unittest.main()
