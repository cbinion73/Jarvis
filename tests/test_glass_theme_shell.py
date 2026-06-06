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

        self.assertIn("Open Desktop Experience", html)
        self.assertIn("onclick=\"openHealthDesktopExperience()\"", html)
        self.assertIn("function openHealthDesktopExperience()", html)
        self.assertIn("window.open('/health-desktop', '_blank', 'noopener');", html)


if __name__ == "__main__":
    unittest.main()
