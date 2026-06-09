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

    def test_render_glass_shell_wires_command_runtime_controls(self) -> None:
        html = render_glass_shell(self.runtime)

        self.assertIn('id="command-refresh-button"', html)
        self.assertIn('id="command-live-button"', html)
        self.assertIn('id="command-runtime-note"', html)
        self.assertIn("function refreshCommandDesktop()", html)
        self.assertIn("function refreshCommandLiveSignal()", html)
        self.assertIn("function commandApplyOpenLoopAction(", html)
        self.assertIn("function commandApplyApprovalAction(", html)
        self.assertIn("function commandCompleteTask(", html)
        self.assertIn("function commandOpenCommandRoute(", html)
        self.assertIn("function commandRunNamedAction(", html)
        self.assertIn("/api/open-loops?actor=Chris&limit=12", html)
        self.assertIn("/api/apple/health/summary", html)
        self.assertIn("/api/activity/operator-action", html)
        self.assertIn("Open Recovery Loop", html)
        self.assertIn("Schedule Family Time", html)

    def test_render_glass_shell_wires_needs_you_runtime_controls(self) -> None:
        html = render_glass_shell(self.runtime)

        self.assertIn('id="needs-runtime-note"', html)
        self.assertIn("function refreshNotificationCenter()", html)
        self.assertIn("function needsApplyOpenLoopAction(", html)
        self.assertIn("function needsApplyApprovalAction(", html)
        self.assertIn("function needsApplyNotificationAction(", html)
        self.assertIn("function needsDecisionMode(", html)
        self.assertIn("function needsOptimizeTiming()", html)
        self.assertIn("/api/assistant-core/notifications?actor=", html)
        self.assertIn("/api/open-loops?actor=", html)
        self.assertIn("/api/activity/module", html)
        self.assertIn("/api/activity/operator-action", html)
        self.assertIn("Needs You is live and connected.", html)

    def test_render_glass_shell_wires_legacy_runtime_controls(self) -> None:
        html = render_glass_shell(self.runtime)

        self.assertIn('id="legacy-hero-overline"', html)
        self.assertIn('id="legacy-hero-title"', html)
        self.assertIn('id="legacy-hero-copy"', html)
        self.assertIn('id="legacy-hero-button"', html)
        self.assertIn('id="legacy-runtime-note"', html)
        self.assertIn('id="legacy-thread-points"', html)
        self.assertIn('id="legacy-archive-points"', html)
        self.assertIn('id="legacy-synthesis-points"', html)
        self.assertIn('id="legacy-voice-thread"', html)
        self.assertIn("function renderLegacyDesktop(", html)
        self.assertIn("legacyRuntimeNote(", html)
        self.assertIn("function openChronicleEntryCard(", html)
        self.assertIn("function openChroniclePrayerCard(", html)
        self.assertIn("data-entry=", html)
        self.assertIn("data-prayer=", html)
        self.assertIn("/api/chronicle/module", html)
        self.assertIn("/api/chronicle/recent", html)
        self.assertIn("/api/chronicle/context", html)
        self.assertIn("/api/chronicle/patterns", html)
        self.assertIn("/api/chronicle/quick-capture", html)
        self.assertIn("/api/chronicle/write-entry", html)
        self.assertIn("/api/chronicle/update-prayer", html)

    def test_render_glass_shell_wires_faith_runtime_controls(self) -> None:
        html = render_glass_shell(self.runtime)

        self.assertIn('id="faith-runtime-note"', html)
        self.assertIn('id="faith-hero-overline"', html)
        self.assertIn('id="faith-journal-actions"', html)
        self.assertIn('id="faith-voice-context"', html)
        self.assertIn("function refreshFaithDesktop()", html)
        self.assertIn("function renderFaithDesktop(", html)
        self.assertIn("function faithSelectJournalEntry(", html)
        self.assertIn("function faithMarkPrayerPrayed(", html)
        self.assertIn("function faithMarkPrayerAnswered(", html)
        self.assertIn("/api/faith/module", html)
        self.assertIn("/api/faith/chat", html)
        self.assertIn("/api/chronicle/update-prayer", html)
        self.assertIn("Faith is live and connected.", html)

    def test_render_glass_shell_wires_agents_runtime_controls(self) -> None:
        html = render_glass_shell(self.runtime)

        self.assertIn('id="agents-refresh-button"', html)
        self.assertIn('id="agents-runtime-note"', html)
        self.assertIn("function refreshAgentsDesktop(", html)
        self.assertIn("function agentsApplyApprovalAction(", html)
        self.assertIn("function agentsApplyWorkAction(", html)
        self.assertIn("function agentsApplyRuntimeControl(", html)
        self.assertIn("function agentsOpenRoute(", html)
        self.assertIn("/api/agents/module", html)
        self.assertIn("/api/agents/roster", html)
        self.assertIn("/api/agent-runtime/control", html)
        self.assertIn("/api/agent-runtime/heartbeat", html)
        self.assertIn("/api/agent-work/approve/", html)
        self.assertIn("/api/agent-work/reject/", html)

    def test_render_glass_shell_wires_intel_runtime_controls(self) -> None:
        html = render_glass_shell(self.runtime)

        self.assertIn('id="intel-refresh-button"', html)
        self.assertIn('id="intel-runtime-note"', html)
        self.assertIn("function refreshIntelDesktop(", html)
        self.assertIn("function intelTeachAction(", html)
        self.assertIn("function intelOpenRoute(", html)
        self.assertIn("function intelRecordAction(", html)
        self.assertIn("/api/intel/module", html)
        self.assertIn("/api/activity/operator-action", html)
        self.assertIn("Open Lane", html)
        self.assertIn("Open Context", html)
        self.assertIn("Open Route", html)

    def test_render_glass_shell_wires_catalyst_runtime_controls(self) -> None:
        html = render_glass_shell(self.runtime)

        self.assertIn('id="catalyst-refresh-button"', html)
        self.assertIn('id="catalyst-runtime-note"', html)
        self.assertIn('id="catalyst-builder-actions"', html)
        self.assertIn('id="catalyst-voice-input"', html)
        self.assertIn("function refreshCatalystDesktop(", html)
        self.assertIn("function renderCatalystModule(", html)
        self.assertIn("function catalystHandleAction(", html)
        self.assertIn("function catalystSendVoicePrompt(", html)
        self.assertIn("/api/catalyst/module", html)
        self.assertIn("/api/apple/catalyst/progress-focus", html)
        self.assertIn("/api/apple/catalyst/approvals/{request_id}/approve", html)
        self.assertIn("/api/apple/catalyst/recovery-cases/{case_id}/execute", html)
        self.assertIn("/api/apple/catalyst/agents/{agent_id}/queue-run", html)
        self.assertIn("/api/activity/operator-action", html)

    def test_render_glass_shell_wires_forge_runtime_controls(self) -> None:
        html = render_glass_shell(self.runtime)

        self.assertIn('id="forge-runtime-note"', html)
        self.assertIn("Refresh Forge", html)
        self.assertIn("function refreshForgeDesktop(", html)
        self.assertIn("function forgeRenderModule(", html)
        self.assertIn('id="forge-factor-list"', html)
        self.assertIn('id="forge-stage-cad"', html)
        self.assertIn('id="forge-environment-row"', html)
        self.assertIn("/api/forge/module", html)
        self.assertIn("/api/forge/wow/status", html)
        self.assertIn("/api/forge/convert/format", html)
        self.assertIn("/api/forge/convert/repair", html)
        self.assertIn("/api/forge/convert/scale", html)

    def test_render_glass_shell_wires_workshop_runtime_controls(self) -> None:
        html = render_glass_shell(self.runtime)

        self.assertIn('id="workshop-runtime-note"', html)
        self.assertIn("function refreshWorkshopDesktop(", html)
        self.assertIn("function renderWorkshopModule(", html)
        self.assertIn("function workshopHandleAction(", html)
        self.assertIn("function workshopOpenRoute(", html)
        self.assertIn("/api/workshop/module", html)
        self.assertIn("/api/home/tasks", html)
        self.assertIn("/api/open-loops/action", html)
        self.assertIn("/api/workshop/projects", html)
        self.assertIn("/api/workshop/jobs", html)
        self.assertIn("/api/workshop/materials", html)
        self.assertIn("/api/activity/operator-action", html)

    def test_render_glass_shell_wires_publishing_runtime_controls(self) -> None:
        html = render_glass_shell(self.runtime)

        self.assertIn('id="pub-runtime-note"', html)
        self.assertIn('id="publish-refresh-button"', html)
        self.assertIn("function refreshPublishingDesktop(", html)
        self.assertIn("function renderPublishModule(", html)
        self.assertIn("function publishCreateDraftProject(", html)
        self.assertIn("function publishCompleteChecklistStep(", html)
        self.assertIn("function publishCreateCalendarItem(", html)
        self.assertIn("function publishCreateSocialPost(", html)
        self.assertIn("function publishGenerateLaunchPlan(", html)
        self.assertIn("function publishOpenRoute(", html)
        self.assertIn("/api/publish/module", html)
        self.assertIn("/api/publishing/projects", html)
        self.assertIn("/api/publishing/checklist/step", html)
        self.assertIn("/api/publishing/calendar", html)
        self.assertIn("/api/publishing/social/posts", html)
        self.assertIn("/api/publishing/launch-plan", html)
        self.assertIn("/api/activity/operator-action", html)
        self.assertIn("Quick Draft Project", html)

    def test_render_glass_shell_wires_desktop_card_sequence_controller(self) -> None:
        html = render_glass_shell(self.runtime)

        self.assertIn("function initDesktopCardSequences()", html)
        self.assertIn("function desktopSequenceBoardNodes(", html)
        self.assertIn("function openDesktopCardSequenceModal(", html)
        self.assertIn("desktop-sequence-inplace-active .desktop-sequence-card", html)
        self.assertIn("desktop-sequence-board.desktop-sequence-board-hidden", html)
        self.assertIn("data-sequence-view", html)
        self.assertIn("Each numbered Daily Brief card is now its own in-experience page", html)
        self.assertIn("Each numbered Social Media card is now its own in-experience page", html)
        self.assertIn("Each numbered Calendar card is now its own in-experience page", html)
        self.assertIn("if (name === 'command') name = 'chat';", html)


if __name__ == "__main__":
    unittest.main()
