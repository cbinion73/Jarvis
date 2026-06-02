import SwiftUI
import JarvisKit
#if canImport(AppIntents)
import AppIntents
#endif

@main
struct JarvisPhoneApp: App {

    @UIApplicationDelegateAdaptor(AppDelegate.self) var appDelegate
    @Environment(\.scenePhase) private var scenePhase

    init() {
        JARVISEnvironment.current = .production
    }

    var body: some Scene {
        WindowGroup {
            RootTabView()
                .task { await startupSequence() }
                .onChange(of: scenePhase) { _, phase in
                    if phase == .active { Task { await foregroundRefresh() } }
                }
        }
    }

    // MARK: - Startup

    private func startupSequence() async {
        await refreshAppShortcuts()

        // Live Activity — start showing in Dynamic Island
        LiveActivityManager.shared.start()

        // Presence uses existing permissions only. Do not trigger location
        // permission prompts during app startup.
        WiFiPresenceMonitor.shared.start()
        GeofenceManager.shared.startMonitoring()

        // WatchConnectivity
        _ = WatchSessionManager.shared

        // Now Playing observer
        _ = NowPlayingManager.shared

        // Load briefing, push to Watch + widgets + Live Activity
        if let packet = try? await AppleAPIClient.shared.fetchBriefing() {
            WatchSessionManager.shared.sendBriefing(packet)
            writeSharedData(packet: packet)
            LiveActivityManager.shared.updateFromBriefing(
                mode: packet.mode,
                needsCount: packet.needsItems.count
            )
        }
    }

    // MARK: - Foreground refresh

    private func foregroundRefresh() async {
        await refreshAppShortcuts()
        await MainActor.run {
            VoiceConversationLaunchCenter.shared.refreshFromStore()
        }
        WiFiPresenceMonitor.shared.refresh()
    }

    private func refreshAppShortcuts() async {
        #if canImport(AppIntents)
        if #available(iOS 16.0, *) {
            JarvisShortcuts.updateAppShortcutParameters()
            print("[JARVIS Siri] App Shortcuts refreshed.")
        }
        #endif
    }

    // MARK: - Write to App Group (feeds widgets + complications)

    private func writeSharedData(packet: BriefingPacket) {
        let wx = WeatherManager.shared
        SharedDataWriter.write(
            greeting:    packet.greeting,
            mode:        packet.mode,
            needsCount:  packet.needsItems.count,
            briefItems:  packet.briefingItems.prefix(6).map {
                ["text": $0.text, "priority": $0.priority]
            },
            weatherTemp: wx.current?.tempString   ?? "",
            weatherCond: wx.current?.condition    ?? "",
            weatherKey:  wx.current?.visualKey    ?? "clear_day"
        )
    }
}
