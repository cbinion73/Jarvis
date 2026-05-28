import SwiftUI
import JarvisKit

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
        // Live Activity — start showing in Dynamic Island
        LiveActivityManager.shared.start()

        // HealthKit
        await HealthSyncManager.shared.requestPermissionsAndSync()

        // Presence — both WiFi and geofencing
        WiFiPresenceMonitor.shared.start()
        GeofenceManager.shared.requestPermission()
        GeofenceManager.shared.startMonitoring()

        // WatchConnectivity
        _ = WatchSessionManager.shared

        // EventKit — calendar + reminders
        await EventKitSyncManager.shared.syncAll()

        // Now Playing observer
        _ = NowPlayingManager.shared

        // Sound Analysis — start listening for household alerts
        SoundAnalysisManager.shared.startListening()

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
        WiFiPresenceMonitor.shared.refresh()
        Task { await EventKitSyncManager.shared.syncAll() }
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
